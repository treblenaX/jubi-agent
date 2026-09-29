<script lang="ts">
  let {
    dispatchOpen = false,
    dispatchRunning = false,
    onToggleDispatch
  }: {
    dispatchOpen?: boolean;
    dispatchRunning?: boolean;
    onToggleDispatch?: () => void;
  } = $props();

  let chatMode: "auto" | "agent" | "manual" = $state("auto");
</script>

<div class="flex items-center justify-end gap-2">
  <!-- Subagent dispatch panel toggle (Ctrl+G); pulsing dot while a dispatch runs -->
  <button
    class="dispatch-toggle"
    class:active={dispatchOpen}
    onclick={onToggleDispatch}
    title="Subagent dispatches (Ctrl+G)"
    aria-label="Toggle subagent dispatch panel"
    aria-pressed={dispatchOpen}
  >
    <!-- panel-right icon -->
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
    >
      <rect width="18" height="18" x="3" y="3" rx="2" />
      <path d="M15 3v18" />
    </svg>
    {#if dispatchRunning}
      <span class="live-dot" aria-label="dispatch running"></span>
    {/if}
  </button>

  <!-- Mode selector for chat -->
  <div class="flex items-center gap-2">
    <select
      value={chatMode}
      onchange={(e) => chatMode = e.currentTarget.value as "auto" | "agent" | "manual"}
      class="bg-purple-800/50 text-white text-xs rounded px-2 py-1 border border-purple-400/30 focus:outline-none focus:ring-2 focus:ring-purple-400"
    >
      <option value="auto">Auto</option>
      <option value="agent">Agent</option>
      <option value="manual">Manual</option>
    </select>
  </div>
</div>

<style>
  .dispatch-toggle {
    position: relative;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 1.75rem;
    height: 1.75rem;
    border-radius: 0.375rem;
    color: rgb(255 255 255 / 0.75);
    background: rgb(255 255 255 / 0.08);
    border: 1px solid rgb(255 255 255 / 0.15);
    cursor: pointer;
    transition: background 120ms ease, color 120ms ease;
  }
  .dispatch-toggle:hover {
    background: rgb(255 255 255 / 0.18);
    color: #fff;
  }
  .dispatch-toggle.active {
    background: rgb(255 255 255 / 0.25);
    color: #fff;
  }
  .live-dot {
    position: absolute;
    top: -0.2rem;
    right: -0.2rem;
    width: 0.5rem;
    height: 0.5rem;
    border-radius: 9999px;
    background: #4ade80;
    animation: header-dot-pulse 1.2s ease-in-out infinite;
  }
  @keyframes header-dot-pulse {
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