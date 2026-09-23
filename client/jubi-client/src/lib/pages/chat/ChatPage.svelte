<script lang="ts">
	import { goto } from "$app/navigation";
	import { page } from "$app/state";
	import ChatHeader from "./ChatHeader.svelte";
	import MessageContainer from "../../components/chat/MessageContainer.svelte";
	import ChatFooter from "./ChatFooter.svelte";
	import { sendMessage, fetchHistory, createThread } from "$lib/api/chat";
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

	// URL is the source of truth for the active thread (?t=<thread_id>).
	// lastLoaded guards against clobbering optimistic messages right after
	// we create a thread and update the URL mid-send.
	const activeThreadId = $derived(page.url.searchParams.get('t') ?? '');
	let lastLoaded = $state<string | null>(null);

	// Load history whenever the URL switches to a different thread
	$effect(() => {
		const t = activeThreadId;
		if (t === lastLoaded) return;
		lastLoaded = t;
		messages = [];
		contextUsed = null;
		streamingMsgId = null;
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
				if (event.type === 'message' && event.content) {
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
				updateMessage(assistantId, `Error: ${error.message}`);
			},
			onComplete: (id: string) => {
				const msg = messages.find((m) => m.id === assistantId);
				if (msg) msg.timestamp = new Date(); // real finish time
				isStreaming = false;
				streamingMsgId = null;
				sessions.refresh(); // sidebar picks up new/updated session
			}
		});
	}
</script>
<div class="flex h-full w-full flex-col overflow-hidden">
	<div class="chat-header shrink-0 text-white p-4 shadow-lg z-10">
  		<ChatHeader />
  	</div>
	<div class="chat-messages relative min-h-0 flex-1 bg-background">
  		<MessageContainer {messages} />
	</div>
	<div class="chat-footer shrink-0 mt-auto bg-background px-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))] sm:px-4">
  		<ChatFooter
			onSend={handleSendMessage}
			disabled={isStreaming}
			tokenUsage={contextUsed === null ? undefined : contextUsed / contextLimit * 100}
		/>
	</div>
</div>
