<script lang="ts">
	import { fly } from "svelte/transition";

	// Right-side dispatch monitor. Renders the latest transcript per subagent
	// (server keeps only -latest.md) with live/running state + dispatch time.
	// Transcript text is owned by ChatPage (polled during a dispatch).
	let {
		open,
		transcripts,
		dispatchMeta = {},
		onClose
	}: {
		open: boolean;
		transcripts: Record<string, string>;
		dispatchMeta?: Record<string, { ts: number; running: boolean }>;
		onClose: () => void;
	} = $props();

	const names = ['coder', 'researcher'];

	const fmtTime = (ts?: number) =>
		ts ? new Date(ts).toLocaleTimeString([], { hour12: false }) : '';
</script>

{#if open}
	<aside class="dispatch-panel" transition:fly={{ x: 60, duration: 180 }}>
		<header class="panel-head">
			<span class="panel-title">Subagent dispatches</span>
			<button class="close-btn" onclick={onClose} aria-label="Close dispatch panel">✕</button>
		</header>

		{#each names as name (name)}
			{@const text = transcripts[name]}
			{@const meta = dispatchMeta[name]}
			<section class="dispatch">
				<div class="dispatch-head">
					{#if meta?.running}
						<span class="live-dot" aria-label="running"></span>
					{/if}
					<span class="name">{name}</span>
					{#if meta?.ts}
						<span class="ts">{fmtTime(meta.ts)}</span>
					{/if}
					<span class="state" class:running={meta?.running}>
						{meta?.running ? 'running' : text ? 'done' : 'idle'}
					</span>
				</div>
				{#if text}
					<pre>{text}</pre>
				{:else}
					<p class="empty">No dispatch yet in this thread.</p>
				{/if}
			</section>
		{/each}
	</aside>
{/if}

<style>
	.dispatch-panel {
		position: absolute;
		top: 0;
		right: 0;
		bottom: 0;
		width: 20rem;
		max-width: 85vw;
		z-index: 20;
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
		overflow-y: auto;
		padding: 0.875rem;
		background: var(--card);
		border-left: 1px solid var(--border);
		box-shadow: -0.5rem 0 1.5rem rgb(0 0 0 / 0.25);
	}
	.panel-head {
		display: flex;
		align-items: center;
		justify-content: space-between;
	}
	.panel-title {
		font-size: 0.7rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: var(--muted-foreground);
	}
	.close-btn {
		color: var(--muted-foreground);
		font-size: 0.8rem;
		line-height: 1;
		padding: 0.25rem 0.4rem;
		border-radius: 0.25rem;
		cursor: pointer;
	}
	.close-btn:hover {
		color: var(--foreground);
		background: var(--accent);
	}
	.dispatch {
		border-left: 2px solid var(--border);
		padding-left: 0.625rem;
	}
	.dispatch-head {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		font-family: var(--font-mono);
		font-size: 0.72rem;
	}
	.name {
		color: var(--primary);
		font-weight: 600;
	}
	.ts {
		color: var(--muted-foreground);
		font-variant-numeric: tabular-nums;
	}
	.state {
		margin-left: auto;
		font-size: 0.62rem;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		color: var(--muted-foreground);
	}
	.state.running {
		color: var(--primary);
	}
	.live-dot {
		width: 0.45rem;
		height: 0.45rem;
		border-radius: 9999px;
		background: var(--primary);
		animation: dot-pulse 1.2s ease-in-out infinite;
		flex-shrink: 0;
	}
	.dispatch pre {
		margin: 0.35rem 0 0;
		padding: 0.375rem 0.5rem;
		max-height: 18rem;
		overflow-y: auto;
		font-size: 0.66rem;
		line-height: 1.45;
		white-space: pre-wrap;
		word-break: break-word;
		color: var(--muted-foreground);
		background: color-mix(in srgb, var(--muted) 45%, transparent);
		border-radius: 0.375rem;
	}
	.empty {
		margin: 0.35rem 0 0;
		font-size: 0.68rem;
		color: var(--muted-foreground);
		font-style: italic;
	}
	@keyframes dot-pulse {
		0%,
		100% {
			opacity: 1;
			transform: scale(1);
		}
		50% {
			opacity: 0.35;
			transform: scale(0.75);
		}
	}
</style>