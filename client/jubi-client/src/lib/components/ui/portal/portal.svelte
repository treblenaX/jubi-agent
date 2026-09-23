<script lang="ts">
	import type { Snippet } from "svelte";

	interface Props {
		children?: Snippet;
		disabled?: boolean;
		hydrateId?: string;
	}

	let { children, disabled = false, hydrateId }: Props = $props();
</script>

{#if !disabled}
	<div class="portal-root" data-portal={hydrateId}>
		{@render children?.()}
	</div>
{/if}