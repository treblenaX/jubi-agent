<script lang="ts">
	import Chatbox from "../../components/chat/Chatbox.svelte";
	
	// State variables for chat input functionality
	let tokenUsage = $state(52);
	let userValue = $state('');
	let isStreaming = $state(false);
	
	// Handle message send (placeholder - connect to actual API)
	const handleSend = async (content: string) => {
		if (!content.trim() || isStreaming) return;
		
		// TODO: Implement actual send logic
		console.log('Sending message:', content);
	};
	
	// Handle input value change
	const onValueChange = (value: string) => {
		userValue = value;
	};
</script>

<div class="chat-input p-4 border-t">
	<Chatbox
		bind:tokenUsage={tokenUsage}
		value={userValue}
		mode="auto"
		disabled={isStreaming}
		onSend={handleSend}
		onValueChange={onValueChange}
	/>
</div>
