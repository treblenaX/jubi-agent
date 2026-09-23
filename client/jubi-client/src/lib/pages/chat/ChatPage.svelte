<script lang="ts">
	import ChatHeader from "./ChatHeader.svelte";
	import MessageContainer from "../../components/chat/MessageContainer.svelte";
	import ChatFooter from "./ChatFooter.svelte";
	import { sendMessage, fetchHistory, getOrCreateThreadId } from "$lib/api/chat";

	interface ChatMessage {
		id: string;
		role: 'user' | 'assistant';
		content: string;
		timestamp?: Date;
	}

	// Chat state (single source of truth for the page)
	let messages = $state<ChatMessage[]>([]);
	let chatMode = $state<'auto' | 'agent' | 'manual'>('auto');
	let threadId = $state<string>('');
	let isStreaming = $state(false);
	let tokenUsage = $state(52);
	let streamingMsgId = $state<string | null>(null);
	let pendingContent = '';

	// Initialize thread + load history on mount ($effect runs client-side only)
	$effect(() => {
		if (threadId) return;
		threadId = getOrCreateThreadId();
		fetchHistory(threadId).then((history) => {
			if (history.length > 0) messages = history;
		});
	});

	function updateMessage(msgId: string, content: string) {
		const msg = messages.find((m) => m.id === msgId);
		if (msg) msg.content = content;
	}

	// Send message handler: optimistic UI, then stream from orchestrator
	async function handleSendMessage(content: string) {
		if (!content.trim() || isStreaming) return;

		// 1. User message + assistant placeholder
		messages.push({ id: crypto.randomUUID(), role: 'user', content, timestamp: new Date() });
		const assistantId = crypto.randomUUID();
		streamingMsgId = assistantId;
		pendingContent = '';
		messages.push({ id: assistantId, role: 'assistant', content: '', timestamp: new Date() });
		isStreaming = true;

		await sendMessage(content, {
			threadId: threadId,
			onEvent: (event) => {
				if (event.type === 'message' && event.content) {
					pendingContent += event.content;
					updateMessage(assistantId, pendingContent);
				} else if (event.type === 'error' && event.error) {
					updateMessage(assistantId, `Error: ${event.error}`);
				}
			},
			onError: (error: Error) => {
				console.error('Chat error:', error);
				updateMessage(assistantId, `Error: ${error.message}`);
			},
			onComplete: (id: string, usage?: number) => {
				isStreaming = false;
				streamingMsgId = null;
				if (typeof usage === 'number') tokenUsage = usage;
			}
		});
	}
</script>
<div class="flex h-full w-full flex-col overflow-hidden">
	<div class="chat-header shrink-0 text-white p-4 shadow-lg z-10">
  		<ChatHeader chatMode={chatMode} />
  	</div>
	<div class="chat-messages relative min-h-0 flex-1 bg-background">
  		<MessageContainer {messages} />
	</div>
	<div class="chat-footer shrink-0 mt-auto bg-background px-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))] sm:px-4">
  		<ChatFooter
			onSend={handleSendMessage}
			disabled={isStreaming}
			tokenUsage={tokenUsage}
			mode={chatMode}
			onModeChange={(m) => (chatMode = m)}
		/>
	</div>
</div>