<script lang="ts">
  import { onMount } from "svelte";
  import { goto } from "$app/navigation";
  import { page } from "$app/state";
  import { HugeiconsIcon } from "@hugeicons/svelte";
  import { PlusSignIcon, Cancel01Icon } from "@hugeicons/core-free-icons";
  import { API_URL } from "$lib/constants";
  import { sessions } from "$lib/stores/sessions.svelte";
  import { deleteThread } from "$lib/api/chat";

  let { children } = $props();

  // StatusDot state - init false/null to avoid flash on first render
  let apiUp = $state(false);
  let model = $state<{ connected: boolean; name: string; error: string | null } | null>(null);
  let showHealthModal: boolean = $state(false);

  // Active thread comes from the URL (?t=<thread_id>) — same source as ChatPage
  const activeThreadId = $derived(page.url.searchParams.get('t') ?? '');

  async function checkConnection() {
    try {
      const response = await fetch(API_URL + '/health', {
        method: 'GET',
        cache: 'no-store' // Ensure we don't cache the health check response
      });
      apiUp = response.ok;
      model = response.ok ? ((await response.json()).model ?? null) : null;
    } catch (_error) {
      console.log('API health check failed:', _error instanceof Error ? _error.message : 'Unknown error');
      apiUp = false;
      model = null;
    }
  }

  // green: API + model up · yellow: API up, model down · red: API down
  const dotClass = $derived(
    apiUp ? (model?.connected ? 'bg-constructive' : 'bg-warning') : 'bg-destructive'
  );
  const dotTitle = $derived(
    apiUp
      ? model?.connected
        ? 'API and model healthy'
        : 'API up — model not connected'
      : 'API connection lost'
  );

  async function handleDelete(event: MouseEvent, threadId: string) {
    event.stopPropagation();
    try {
      await deleteThread(threadId); // server: checkpoints + metadata
      sessions.remove(threadId);
      if (threadId === activeThreadId) goto('/');
    } catch (err) {
      console.error('Failed to delete session:', err);
    }
  }

  onMount(() => {
    checkConnection();
    sessions.refresh();
    const interval = setInterval(checkConnection, 10000);
    return () => clearInterval(interval);
  });
</script>

<div class="flex h-screen w-full overflow-hidden bg-background text-foreground">
  <!-- Sidebar Container -->
  <aside class="flex h-full w-64 flex-col border-r border-border bg-card">
      <!-- Top App Title Header -->
      <div class="flex h-16 items-center justify-between px-6 border-b border-border">
        <span class="text-xl font-bold tracking-tight text-primary">Jubi</span>

        <!-- StatusDot aligned right -->
        <span
          class={`status-dot ${dotClass} w-2 h-2 rounded-full cursor-pointer`}
          role="button"
          tabindex="0"
          title={dotTitle}
          onclick={() => showHealthModal = true}
          onkeydown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              showHealthModal = true;
            }
          }}
        ></span>
      </div>

    <!-- Modal -->
    {#if showHealthModal}
      <div class="modal-overlay" role="dialog" aria-modal="true" aria-labelledby="health-modal-title" tabindex="0" onclick={() => showHealthModal = false} onkeydown={(e) => { if (e.key === 'Escape') showHealthModal = false; }}>
        <div class="modal-content">
          <div class="modal-header">
            <h3 id="health-modal-title">API Health Check Endpoint</h3>
            <button class="close-btn" aria-label="Close modal" onclick={() => showHealthModal = false}>✕</button>
          </div>
          <div class="modal-body">
            <p>The status dot checks connectivity to:</p>
            <code class="endpoint-code">{API_URL}/health</code>
            <div class="health-grid">
              <span class="health-label">API</span>
              <span class={apiUp ? 'health-ok' : 'health-bad'}>
                {apiUp ? 'Connected' : 'Unreachable'}
              </span>
              <span class="health-label">Model</span>
              <span class="health-value">{model?.name ?? '—'}</span>
              <span class="health-label">Model status</span>
              <span class={!apiUp || !model?.connected ? 'health-bad' : 'health-ok'}>
                {apiUp ? (model?.connected ? 'Connected' : 'Not connected') : 'Unknown'}
              </span>
            </div>
            {#if apiUp && model && !model.connected}
              <p class="health-error">{model.error}</p>
            {/if}
            <p class="modal-note">This endpoint returns HTTP 200 when the backend is running and healthy.</p>
          </div>
        </div>
      </div>
    {/if}

    <!-- New Chat -->
    <div class="px-4 pt-4">
      <button
        class="flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
        onclick={() => goto('/')}
      >
        <HugeiconsIcon icon={PlusSignIcon} size={20} strokeWidth={1.5} class="h-5 w-5" />
        <span>New Chat</span>
      </button>
    </div>

    <!-- Session List -->
    <nav class="flex-1 space-y-1 px-4 py-4 overflow-y-auto">
      {#each sessions.list as session (session.thread_id)}
        <div
          class={`group relative flex items-center rounded-md text-sm transition-colors ${
            session.thread_id === activeThreadId
              ? 'bg-accent text-accent-foreground'
              : 'text-muted-foreground hover:bg-accent/50'
          }`}
        >
          <button
            class="flex-1 truncate px-3 py-2 text-left font-medium"
            title={session.title || 'New chat'}
            onclick={() => goto(`/?t=${session.thread_id}`)}
          >
            {session.title || 'New chat'}
          </button>
          <button
            class="absolute right-1.5 rounded p-1 opacity-0 transition-opacity hover:text-destructive focus-visible:opacity-100 group-hover:opacity-100"
            aria-label={`Delete session: ${session.title || 'New chat'}`}
            onclick={(e) => handleDelete(e, session.thread_id)}
          >
            <HugeiconsIcon icon={Cancel01Icon} size={14} strokeWidth={1.5} />
          </button>
        </div>
      {:else}
        <p class="px-3 py-2 text-xs text-muted-foreground">No sessions yet</p>
      {/each}
    </nav>
  </aside>
  <!-- Primary Page View Content Area -->
  <main class="flex-1 overflow-y-auto bg-background p-8">
    {@render children?.()}
  </main>
</div>

<style>
  /* Modal styles (previously lived in a deleted external css file) */
  .modal-overlay {
    position: fixed;
    inset: 0;
    z-index: 50;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgb(0 0 0 / 60%);
  }
  .modal-content {
    width: 22rem;
    max-width: calc(100vw - 2rem);
    padding: 1rem 1.25rem;
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    background: var(--card);
    color: var(--card-foreground);
    box-shadow: 0 10px 30px rgb(0 0 0 / 35%);
  }
  .modal-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 0.5rem;
  }
  .modal-header h3 {
    font-size: 0.95rem;
    font-weight: 600;
  }
  .close-btn {
    color: var(--muted-foreground);
  }
  .close-btn:hover {
    color: var(--destructive);
  }
  .modal-body {
    display: grid;
    gap: 0.375rem;
    font-size: 0.85rem;
    color: var(--muted-foreground);
  }
  .endpoint-code {
    display: block;
    padding: 0.25rem 0.5rem;
    border-radius: calc(var(--radius) - 4px);
    background: var(--muted);
    color: var(--foreground);
    font-family: var(--font-mono);
    font-size: 0.75rem;
    word-break: break-all;
  }
  .health-grid {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 0.25rem 0.75rem;
    margin-top: 0.25rem;
  }
  .health-value {
    color: var(--foreground);
  }
  .health-ok {
    color: var(--constructive);
    font-weight: 500;
  }
  .health-bad {
    color: var(--destructive);
    font-weight: 500;
  }
  .health-error {
    padding: 0.375rem 0.5rem;
    border: 1px solid color-mix(in oklab, var(--destructive) 35%, transparent);
    border-radius: calc(var(--radius) - 4px);
    background: color-mix(in oklab, var(--destructive) 10%, transparent);
    color: var(--destructive);
    font-size: 0.75rem;
    word-break: break-word;
  }
  .modal-note {
    font-size: 0.75rem;
  }
</style>
