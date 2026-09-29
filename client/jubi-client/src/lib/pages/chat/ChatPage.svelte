<script lang="ts">
	import { goto } from "$app/navigation";
	import { page } from "$app/state";
	import { fade } from "svelte/transition";
	import ChatHeader from "./ChatHeader.svelte";
	import MessageContainer from "../../components/chat/MessageContainer.svelte";
	import ChatFooter from "./ChatFooter.svelte";
	import Chatbox from "../../components/chat/Chatbox.svelte";
	import DispatchPanel from "../../components/chat/DispatchPanel.svelte";
	import { sendMessage, fetchHistory, createThread, fetchTranscript, type ChatMessage, type TimelineEntry } from "$lib/api/chat";
	import { getSettings } from "$lib/api/settings";
	import { sessions } from "$lib/stores/sessions.svelte";

	// Chat state (single source of truth for the page)
	let messages = $state<ChatMessage[]>([]);
	let isStreaming = $state(false);
	let contextUsed = $state<number | null>(null);
	let contextLimit = $state(16384);
	let streamingMsgId = $state<string | null>(null);
	// Subagent transcripts keyed by subagent name ("coder"/"researcher").
	// Grows live during a dispatch (polled); refetched on history load so the
	// panel survives refresh (sandbox files persist server-side).
	let transcripts = $state<Record<string, string>>({});
	let pollTimer: ReturnType<typeof setInterval> | null = null;
	let runningDispatch = $state<{ subagent: string } | null>(null);
	// Per-subagent dispatch metadata for the dispatch panel + activity lines:
	// when the dispatch started (epoch ms) and whether it is still running.
	let dispatchMeta = $state<Record<string, { ts: number; running: boolean }>>({});
	// Right-side dispatch panel (toggle: header icon or Ctrl+G)
	let dispatchPanelOpen = $state(false);
	// Thoughts <details> default state (settings → thoughts_expanded)
	let thoughtsExpanded = $state(true);
	// True once a live turn happened this page-session; the recovered
	// "Subagent chats" section only shows on freshly loaded threads.
	let liveTurnHappened = $state(false);

	// Load the thoughts-expanded setting now and whenever the settings panel saves
	$effect(() => {
		const reload = () =>
			void getSettings().then((s) => {
				if (s && typeof s.thoughts_expanded === 'boolean') thoughtsExpanded = s.thoughts_expanded;
			});
		reload();
		window.addEventListener('jubi-settings-changed', reload);
		return () => window.removeEventListener('jubi-settings-changed', reload);
	});

	function stopPolling() {
		if (pollTimer) {
			clearInterval(pollTimer);
			pollTimer = null;
		}
		runningDispatch = null;
	}

	function startPolling(tid: string, subagent: string) {
		stopPolling();
		// Set AFTER stopPolling — it nulls runningDispatch. (Pre-existing bug:
		// the caller used to set it before startPolling, so the dispatch-finish
		// branch in tool_result never saw it and never ran.)
		runningDispatch = { subagent };
		const tick = async () => {
			const text = await fetchTranscript(tid, subagent);
			if (text !== null) transcripts[subagent] = text;
		};
		void tick();
		pollTimer = setInterval(tick, 2000);
	}

	// Recover persisted dispatch transcripts after a refresh (no live feed).
	// Only the latest run per subagent is kept server-side (-latest.md).
	async function loadTranscripts(tid: string) {
		const names = ['coder', 'researcher'];
		const found = await Promise.all(
			names.map(async (n) => [n, await fetchTranscript(tid, n)] as const)
		);
		for (const [n, text] of found) {
			if (text !== null) transcripts[n] = text;
		}
	}

	// URL is the source of truth for the active thread (?t=<thread_id>).
	// lastLoaded guards against clobbering optimistic messages right after
	// we create a thread and update the URL mid-send.
	const activeThreadId = $derived(page.url.searchParams.get('t') ?? '');
	let lastLoaded = $state<string | null>(null);

	// Landing/home view shows while the conversation is empty. Once the first
	// message is sent (or history loads), messages.length > 0 and the normal
	// chat layout takes over.
	const isHome = $derived(messages.length === 0);

	// True when the loaded thread has recovered transcripts to show (refresh path)
	const showRecovered = $derived(!isStreaming && !liveTurnHappened);

	// Load history whenever the URL switches to a different thread
	$effect(() => {
		const t = activeThreadId;
		if (t === lastLoaded) return;
		lastLoaded = t;
		messages = [];
		contextUsed = null;
		streamingMsgId = null;
		transcripts = {};
		dispatchMeta = {};
		liveTurnHappened = false;
		stopPolling();
		if (!t) return;
		fetchHistory(t).then(({ messages: history, contextUsed: used, contextLimit: limit }) => {
			if (page.url.searchParams.get('t') !== t) return; // stale response
			if (history.length > 0) messages = history;
			if (typeof used === 'number') contextUsed = used;
			if (typeof limit === 'number') contextLimit = limit;
			void loadTranscripts(t); // recover dispatch transcripts after refresh
		});
	});

	function updateMessage(msgId: string, content: string) {
		const msg = messages.find((m) => m.id === msgId);
		if (msg) msg.content = content;
	}

	// Append a token to the timeline, extending the previous entry of the same
	// kind so contiguous thinking/text stays one block.
	function tlAppendText(msg: ChatMessage, kind: 'thinking' | 'text', token: string) {
		if (!msg.timeline) msg.timeline = [];
		const last = msg.timeline[msg.timeline.length - 1];
		if (last && last.kind === kind) last.text = (last.text ?? '') + token;
		else msg.timeline.push({ kind, text: token });
	}

	// Send message handler: optimistic UI, then stream from orchestrator
	async function handleSendMessage(content: string) {
		if (!content.trim() || isStreaming) return;

		// Resolve thread: use active one, or create + reflect in URL
		let tid = activeThreadId;
		if (!tid) {
			tid = await createThread();
			lastLoaded = tid; // effect must not wipe the optimistic messages below
			await goto(`/?t=${tid}`);
		}

		// 1. User message + assistant placeholder
		messages.push({ id: crypto.randomUUID(), role: 'user', content, timestamp: new Date() });
		const assistantId = crypto.randomUUID();
		streamingMsgId = assistantId;
		transcripts = {};
		stopPolling();
		messages.push({ id: assistantId, role: 'assistant', content: '', timestamp: new Date(), timeline: [] });
		liveTurnHappened = true;
		isStreaming = true;

		await sendMessage(content, {
			threadId: tid,
			onEvent: (event) => {
				const msg = messages.find((m) => m.id === assistantId);
				if (!msg) return;
				if (event.thinking) tlAppendText(msg, 'thinking', event.thinking);
				if (event.type === 'tool_call' && event.tool_name) {
					// task dispatches read as "dispatch → coder" — the milestone line
					let label = event.tool_name;
					let subagent: string | undefined;
					try {
						const args = JSON.parse(event.tool_args ?? '{}');
						if (event.tool_name === 'task' && args.subagent_type) {
							label = `dispatch → ${args.subagent_type}`;
							subagent = args.subagent_type;
						}
					} catch { /* label stays tool name */ }
					if (!msg.timeline) msg.timeline = [];
					const ts = Date.now();
					msg.timeline.push({
						kind: 'tool',
						node: event.node ?? 'agent',
						label,
						args: (event.tool_args ?? '').slice(0, 100),
						status: 'running',
						subagent,
						ts
					});
					// Dispatch started: poll the subagent transcript for the panel
					if (subagent && tid) {
						dispatchMeta[subagent] = { ts, running: true };
						startPolling(tid, subagent); // also sets runningDispatch
					}
				} else if (event.type === 'tool_result') {
					// Close the most recent running tool entry (results arrive in order)
					const open = [...(msg.timeline ?? [])]
						.reverse()
						.find((e) => e.kind === 'tool' && e.status === 'running');
					if (open) {
						open.status = 'done';
						open.result = (event.tool_result ?? '').replace(/\s+/g, ' ').trim().slice(0, 140);
						// Dispatch finished: stop polling, fetch the final transcript
						if (runningDispatch && open.subagent === runningDispatch.subagent) {
							const { subagent } = runningDispatch;
							if (dispatchMeta[subagent]) dispatchMeta[subagent].running = false;
							stopPolling();
							fetchTranscript(tid, subagent).then((text) => {
								if (text !== null) transcripts[subagent] = text;
							});
						}
					}
				} else if (event.type === 'message' && event.content) {
					tlAppendText(msg, 'text', event.content);
					msg.content += event.content; // keep content in sync for history compat
				} else if (event.type === 'context') {
					if (typeof event.contextUsed === 'number') contextUsed = event.contextUsed;
					if (typeof event.contextLimit === 'number') contextLimit = event.contextLimit;
				} else if (event.type === 'error' && event.error) {
					tlAppendText(msg, 'text', `Error: ${event.error}`);
					msg.content = `Error: ${event.error}`;
				}
			},
			onError: (error: Error) => {
				console.error('Chat error:', error);
				stopPolling();
				const msg = messages.find((m) => m.id === assistantId);
				if (msg) {
					tlAppendText(msg, 'text', `Error: ${error.message}`);
					msg.content = `Error: ${error.message}`;
				}
			},
			onComplete: (id: string) => {
				const msg = messages.find((m) => m.id === id);
				if (msg) msg.timestamp = new Date(); // real finish time
				isStreaming = false;
				streamingMsgId = null;
				stopPolling();
				sessions.refresh(); // sidebar picks up new/updated session
			}
		});
	}
	// Ctrl+G (or Cmd+G) toggles the dispatch panel
	$effect(() => {
		const onKey = (e: KeyboardEvent) => {
			if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'g') {
				e.preventDefault(); // browser find-next
				dispatchPanelOpen = !dispatchPanelOpen;
			}
		};
		window.addEventListener('keydown', onKey);
		return () => window.removeEventListener('keydown', onKey);
	});
</script>

<div class="flex h-full w-full flex-col overflow-hidden">
	{#if isHome}
		<!-- Landing / Home view: centered prompt + chatbox, no header -->
		<div class="home flex flex-1 flex-col items-center justify-center gap-4 px-6 text-center">
			<div class="max-w-lg space-y-4">
				<h1
					class="text-3xl font-bold tracking-tight text-foreground"
					style="font-family: var(--font-heading)"
				>
					What should we do?
				</h1>
				<p class="text-sm text-muted-foreground">
					Type a prompt to start a new conversation, or continue an existing thread.
				</p>
			</div>
			<Chatbox
				placeholder="Ask, Search or Chat..."
				disabled={isStreaming}
				onSend={handleSendMessage}
			/>
		</div>
	{:else}
		<div class="chat-header shrink-0 text-white p-4 shadow-lg z-10">
			<ChatHeader
				dispatchOpen={dispatchPanelOpen}
				dispatchRunning={!!runningDispatch}
				onToggleDispatch={() => (dispatchPanelOpen = !dispatchPanelOpen)}
			/>
		</div>
		<div class="chat-messages relative min-h-0 flex-1 bg-background">
			<MessageContainer {messages} {transcripts} {thoughtsExpanded} {showRecovered} />
			<DispatchPanel
				open={dispatchPanelOpen}
				{transcripts}
				{dispatchMeta}
				onClose={() => (dispatchPanelOpen = false)}
			/>
		</div>
		<div
			class="chat-footer shrink-0 mt-auto bg-background px-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))] sm:px-4"
		>
			<ChatFooter
				onSend={handleSendMessage}
				disabled={isStreaming}
				tokenUsage={contextUsed === null ? undefined : contextUsed / contextLimit * 100}
			/>
		</div>
	{/if}
</div>

<style>
	.home :global(.chat-input) {
		padding: 0;
	}
</style>
