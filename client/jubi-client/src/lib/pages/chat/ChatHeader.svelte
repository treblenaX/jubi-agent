<script lang="ts">
  let chatMode: "auto" | "agent" | "manual" = $state("auto");
</script>

<div class="flex items-center justify-end">
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
