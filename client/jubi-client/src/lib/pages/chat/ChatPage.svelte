<script lang="ts">
	import { goto } from "$app/navigation";
	import { page } from "$app/state";
	import { fade } from "svelte/transition";
	import ChatHeader from "./ChatHeader.svelte";
	import MessageContainer from "../../components/chat/MessageContainer.svelte";
	import ChatFooter from "./ChatFooter.svelte";
	import Chatbox from "../../components/chat/Chatbox.svelte";
	import { sendMessage, fetchHistory, createThread, fetchTranscript, type ActivityItem } from "$lib/api/chat";
	import type { ChatMessage } from "$lib/api/chat";
	import { sessions } from "$lib/stores/sessions.svelte";

	// Chat state (single source of truth for the page)
	let messages = $state<ChatMessage[]>([]);
	let isStreaming = $state(false);
	let contextUsed = $state<number | null>(null);
	let contextLimit = $state(16384);
	let streamingMsgId = $state<string | null>(null);
	let pendingContent = '';
	let pendingThinking = '';
	// Live tool-activity feed for the in-flight turn (cleared per send/thread)
	let activity = $state<ActivityItem[]>([]);
	// Subagent transcripts keyed by activity index (polled while a dispatch runs)
	let transcripts = $state<Record<number, string>>({});
	let pollTimer: ReturnType<typeof setInterval> | null = null;
	let runningDispatch: { idx: number; subagent: string } | null = null;

	function stopPolling() {
		if (pollTimer) {
			clearInterval(pollTimer);
			pollTimer = null;
		}
		runningDispatch = null;
	}

	function startPolling(tid: string, subagent: string, idx: number) {
		stopPolling();
		const tick = async () => {
			const text = await fetchTranscript(tid, subagent);
			if (text !== null) transcripts[idx] = text;
		};
		void tick();
		pollTimer = setInterval(tick, 2000);
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

	// Load history whenever the URL switches to a different thread
	$effect(() => {
		const t = activeThreadId;
		if (t === lastLoaded) return;
		lastLoaded = t;
		messages = [];
		contextUsed = null;
		streamingMsgId = null;
		activity = [];
		transcripts = {};
		stopPolling();
		if (!t) return;
		fetchHistory(t).then(({ messages: history, contextUsed: used, contextLimit: limit }) => {
			if (page.url.searchParams.get('t') !== t) return; // stale response
			if (history.length > 0) messages = history;
			if (typeof used === 'number') contextUsed = used;
			if (typeof limit === 'number') contextLimit = limit;
		});
	});

	function updateMessage(msgId: string, content: string) {
		const msg = messages.find((m) => m.id === msgId);
		if (msg) msg.content = content;
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
		pendingContent = '';
		pendingThinking = '';
		activity = [];
		transcripts = {};
		stopPolling();
		messages.push({ id: assistantId, role: 'assistant', content: '', timestamp: new Date() });
		isStreaming = true;

		await sendMessage(content, {
			threadId: tid,
			onEvent: (event) => {
				if (event.thinking) {
					pendingThinking += event.thinking;
					const msg = messages.find((m) => m.id === assistantId);
					if (msg) msg.thinking = pendingThinking;
				}
				if (event.type === 'tool_call' && event.tool_name) {
					// task dispatches read as "dispatch → coder" — the milestone line
					let label = event.tool_name;
					try {
						const args = JSON.parse(event.tool_args ?? '{}');
						if (event.tool_name === 'task' && args.subagent_type) {
							label = `dispatch → ${args.subagent_type}`;
						}
					} catch { /* label stays tool name */ }
					const idx = activity.push({
						node: event.node ?? 'agent',
						tool: label,
						args: (event.tool_args ?? '').slice(0, 100),
						status: 'running'
					}) - 1;
					// Dispatch started: poll the subagent transcript for the panel
					if (label.startsWith('dispatch → ') && tid) {
						runningDispatch = { idx, subagent: label.slice('dispatch → '.length) };
						startPolling(tid, runningDispatch.subagent, idx);
					}
				} else if (event.type === 'tool_result') {
					// Close the most recent running entry (tool results arrive in order)
					let closeIdx = -1;
					for (let i = activity.length - 1; i >= 0; i--) {
						if (activity[i].status === 'running') {
							closeIdx = i;
							break;
						}
					}
					if (closeIdx >= 0) {
						activity[closeIdx].status = 'done';
						activity[closeIdx].result = (event.tool_result ?? '').replace(/\s+/g, ' ').trim().slice(0, 140);
						// Dispatch finished: stop polling, fetch the final transcript
						if (runningDispatch?.idx === closeIdx) {
							const { subagent, idx } = runningDispatch;
							stopPolling();
							fetchTranscript(tid, subagent).then((text) => {
								if (text !== null) transcripts[idx] = text;
							});
						}
					}
				} else if (event.type === 'message' && event.content) {
					pendingContent += event.content;
					updateMessage(assistantId, pendingContent);
				} else if (event.type === 'context') {
					if (typeof event.contextUsed === 'number') contextUsed = event.contextUsed;
					if (typeof event.contextLimit === 'number') contextLimit = event.contextLimit;
				} else if (event.type === 'error' && event.error) {
					updateMessage(assistantId, `Error: ${event.error}`);
				}
			},
			onError: (error: Error) => {
				console.error('Chat error:', error);
				stopPolling();
				updateMessage(assistantId, `Error: ${error.message}`);
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
			<ChatHeader />
		</div>
		<div class="chat-messages relative min-h-0 flex-1 bg-background">
			<MessageContainer {messages} {activity} {transcripts} />
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
