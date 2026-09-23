<script lang="ts">
	import Chatbox from "../../components/chat/Chatbox.svelte";

	interface Props {
		onSend?: (content: string) => void;
		disabled?: boolean;
		tokenUsage?: number;   // Context used, percent (0-100); undefined = unknown
	}

	let { onSend = () => {}, disabled = false, tokenUsage }: Props = $props();
</script>

<div class="chat-input p-4 border-t">
	<Chatbox {tokenUsage} {disabled} onSend={onSend} />
</div>
