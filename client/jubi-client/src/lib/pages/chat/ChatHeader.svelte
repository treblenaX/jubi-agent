<script lang="ts">
  import type { ComponentProps } from "svelte";
  let chatMode: "auto" | "agent" | "manual" = $state("auto");
</script>

<div class="flex items-center justify-between">
  <!-- Jubi Logo/Title -->
  <h1 class="text-xl font-bold flex items-center gap-2">
    <span>Jubi</span>
    <span class="text-sm font-normal text-purple-200">Multi-Agent Harness</span>
  </h1>

  <!-- Mode selector for chat -->
  <div class="flex items-center gap-2">
    <select
      value={chatMode}
      onchange={(e) => chatMode = e.target.value as "auto" | "agent" | "manual"}
      class="bg-purple-800/50 text-white text-xs rounded px-2 py-1 border border-purple-400/30 focus:outline-none focus:ring-2 focus:ring-purple-400"
    >
      <option value="auto">Auto</option>
      <option value="agent">Agent</option>
      <option value="manual">Manual</option>
    </select>
  </div>
</div>