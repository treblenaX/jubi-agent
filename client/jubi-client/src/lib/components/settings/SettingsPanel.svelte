<script lang="ts">
  import {
    getSettings,
    updateSettings,
    fetchModels,
    type JubiSettings
  } from "$lib/api/settings";

  let { open = $bindable(false) }: { open?: boolean } = $props();

  let settings = $state<JubiSettings | null>(null);
  let models = $state<string[]>([]);
  let ollamaUp = $state(true);
  let saving = $state(false);
  let error = $state("");
  let saved = $state(false);

  const NUM_CTX_OPTIONS = [8192, 16384, 32768, 65536];

  // Load current settings + model list whenever the panel opens
  $effect(() => {
    if (open) void load();
  });

  async function load() {
    error = "";
    saved = false;
    try {
      const [s, m] = await Promise.all([getSettings(), fetchModels()]);
      settings = s;
      models = m.models;
      ollamaUp = m.connected;
    } catch (e) {
      error = e instanceof Error ? e.message : "Failed to load settings";
    }
  }

  async function save() {
    if (!settings) return;
    saving = true;
    error = "";
    saved = false;
    try {
      settings = await updateSettings({
        model: settings.model,
        num_ctx: settings.num_ctx,
        compaction_enabled: settings.compaction_enabled,
        compaction_mode: settings.compaction_mode,
        compaction_trigger_fraction: settings.compaction_trigger_fraction,
        compaction_keep_messages: settings.compaction_keep_messages
      });
      saved = true; // server rebuilt the agent with the new settings
    } catch (e) {
      error = e instanceof Error ? e.message : "Failed to save settings";
    } finally {
      saving = false;
    }
  }

  // Token equivalent of the trigger % at the selected context window
  const triggerTokens = $derived(
    settings
      ? Math.round(settings.compaction_trigger_fraction * settings.num_ctx)
      : 0
  );
</script>

{#if open}
  <div
    class="settings-overlay"
    role="dialog"
    aria-modal="true"
    aria-labelledby="settings-title"
    tabindex="0"
    onclick={() => (open = false)}
    onkeydown={(e) => {
      if (e.key === 'Escape') open = false;
    }}
  >
    <div class="settings-card" onclick={(e) => e.stopPropagation()} role="presentation">
      <div class="settings-header">
        <h3 id="settings-title">Settings</h3>
        <button class="close-btn" aria-label="Close settings" onclick={() => (open = false)}>✕</button>
      </div>

      {#if settings}
        <!-- Model -->
        <div class="field">
          <label for="set-model">Model</label>
          {#if ollamaUp}
            <select id="set-model" bind:value={settings.model}>
              {#each models as m (m)}
                <option value={m}>{m}</option>
              {/each}
              {#if !models.includes(settings.model)}
                <option value={settings.model}>{settings.model} (current)</option>
              {/if}
            </select>
          {:else}
            <input id="set-model" type="text" bind:value={settings.model} />
            <p class="hint">Ollama unreachable — enter model name manually</p>
          {/if}
        </div>

        <!-- Context window -->
        <div class="field">
          <label for="set-num-ctx">Context window</label>
          <select id="set-num-ctx" bind:value={settings.num_ctx}>
            {#each NUM_CTX_OPTIONS as n (n)}
              <option value={n}>{n.toLocaleString()} tokens</option>
            {/each}
          </select>
        </div>

        <!-- Compaction -->
        <div class="field">
          <label class="checkbox-label" for="set-compaction">
            <input id="set-compaction" type="checkbox" bind:checked={settings.compaction_enabled} />
            Compact conversation when context fills up
          </label>
        </div>

        {#if settings.compaction_enabled}
          <div class="field indented">
            <label for="set-mode">Compaction mode</label>
            <select id="set-mode" bind:value={settings.compaction_mode}>
              <option value="state_doc">State document (plan.md)</option>
              <option value="summary">Conversation summary</option>
            </select>
            <label for="set-trigger">
              Trigger: {Math.round(settings.compaction_trigger_fraction * 100)}% of window
              <span class="hint">≈ {triggerTokens.toLocaleString()} tokens</span>
            </label>
            <input
              id="set-trigger"
              type="range"
              min="10"
              max="95"
              step="5"
              bind:value={() => Math.round(settings!.compaction_trigger_fraction * 100),
                (v) => (settings!.compaction_trigger_fraction = v / 100)}
            />
            <label for="set-keep">Keep last messages</label>
            <input
              id="set-keep"
              type="number"
              min="1"
              max="200"
              bind:value={settings.compaction_keep_messages}
            />
          </div>
        {/if}

        <div class="settings-footer">
          <span class="status" class:ok={saved}>
            {#if saved}✓ Saved — agent rebuilt{:else}&nbsp;{/if}
          </span>
          <button class="save-btn" disabled={saving} onclick={save}>
            {saving ? "Saving…" : "Save"}
          </button>
        </div>

        {#if error}
          <p class="error" role="alert">{error}</p>
        {/if}
      {:else}
        <p class="hint">Loading settings…</p>
      {/if}
    </div>
  </div>
{/if}

<style>
  .settings-overlay {
    position: fixed;
    inset: 0;
    z-index: 50;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgb(0 0 0 / 60%);
  }
  .settings-card {
    width: 24rem;
    max-width: calc(100vw - 2rem);
    max-height: calc(100vh - 4rem);
    overflow-y: auto;
    padding: 1rem 1.25rem;
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    background: var(--card);
    color: var(--card-foreground);
    box-shadow: 0 10px 30px rgb(0 0 0 / 35%);
  }
  .settings-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 0.75rem;
  }
  .settings-header h3 {
    font-size: 0.95rem;
    font-weight: 600;
  }
  .close-btn {
    color: var(--muted-foreground);
  }
  .close-btn:hover {
    color: var(--destructive);
  }
  .field {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    margin-bottom: 0.875rem;
  }
  .field.indented {
    margin-left: 1.5rem;
  }
  .field label {
    font-size: 0.8rem;
    color: var(--muted-foreground);
  }
  .checkbox-label {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.85rem;
    color: var(--foreground);
    cursor: pointer;
  }
  select,
  input[type='text'],
  input[type='number'] {
    padding: 0.375rem 0.5rem;
    border: 1px solid var(--border);
    border-radius: calc(var(--radius) - 2px);
    background: var(--background);
    color: var(--foreground);
    font-size: 0.85rem;
  }
  input[type='range'] {
    accent-color: var(--primary);
  }
  .hint {
    font-size: 0.7rem;
    color: var(--muted-foreground);
  }
  .settings-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-top: 0.5rem;
  }
  .status {
    font-size: 0.75rem;
    color: transparent;
  }
  .status.ok {
    color: var(--constructive);
  }
  .save-btn {
    padding: 0.375rem 1rem;
    border: none;
    border-radius: calc(var(--radius) - 2px);
    background: var(--primary);
    color: var(--primary-foreground);
    font-size: 0.85rem;
    font-weight: 500;
    cursor: pointer;
  }
  .save-btn:disabled {
    opacity: 0.6;
    cursor: wait;
  }
  .error {
    margin-top: 0.5rem;
    padding: 0.375rem 0.5rem;
    border: 1px solid color-mix(in oklab, var(--destructive) 35%, transparent);
    border-radius: calc(var(--radius) - 4px);
    background: color-mix(in oklab, var(--destructive) 10%, transparent);
    color: var(--destructive);
    font-size: 0.75rem;
    word-break: break-word;
  }
</style>
