<script lang="ts">
	import ChatHeader from "./ChatHeader.svelte";
	import MessageContainer from "../../components/chat/MessageContainer.svelte";
	import ChatFooter from "./ChatFooter.svelte";
	import { sendMessage } from "$lib/api/chat";

	// State variables for chat functionality
	let chatMode = $state<'auto' | 'agent' | 'manual'>('auto');
	let threadId = $state<string>('');
	let isStreaming = $state(false);

	// Initialize thread ID on mount (client-side only)
	$effect(() => {
		if (!threadId) {
			threadId = localStorage.getItem('jubi_thread_id') || `thread-${Date.now()}`;
			localStorage.setItem('jubi_thread_id', threadId);
		}
	});

	// Handle streaming events
	function onEvent(event: any) {
		console.log('Event:', event);
	}

	function onComplete() {
		isStreaming = false;
	}

	function onError(error: Error) {
		console.error('Chat error:', error);
		isStreaming = false;
	}

	// Send message handler
	async function handleSendMessage(content: string) {
		if (!content.trim()) return;

		isStreaming = true;
		await sendMessage(content, {
			threadId: threadId,
			onEvent,
			onError,
			onComplete
		});
	}

</script>
<div class="flex flex-col w-screen">
	<div class="chat-header text-white p-4 shadow-lg z-10">
  		<ChatHeader chatMode={chatMode} />
  	</div>
	<div class="chat-messages relative min-h-0 flex-1 bg-background">
  		<MessageContainer onSendMessage={handleSendMessage} isStreaming={isStreaming} />
	</div>
	<div class="chat-footer shrink-0 mt-auto bg-background px-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))] sm:px-4">
  		<ChatFooter onSendMessage={handleSendMessage} />
	</div>
</div>