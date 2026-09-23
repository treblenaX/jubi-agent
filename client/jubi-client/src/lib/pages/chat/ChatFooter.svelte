<script lang="ts">
	import Chatbox from "../../components/chat/Chatbox.svelte";

	interface Props {
		onSend?: (content: string) => void;
		disabled?: boolean;
		tokenUsage?: number;
		mode?: "auto" | "agent" | "manual";
		onModeChange?: (mode: "auto" | "agent" | "manual") => void;
	}

	let { onSend = () => {}, disabled = false, tokenUsage = 52, mode = "auto", onModeChange = () => {} }: Props = $props();
</script>

<div class="chat-input p-4 border-t">
	<Chatbox
		{tokenUsage}
		{mode}
		{disabled}
		onSend={onSend}
		onModeChange={onModeChange}
	/>
</div>