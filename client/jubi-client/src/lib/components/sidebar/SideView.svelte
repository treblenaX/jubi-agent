<script lang="ts">
  import { onMount } from "svelte";
  import { HugeiconsIcon } from "@hugeicons/svelte";
  import {
    Home01Icon,
    Chart01Icon,
    UserGroupIcon,
    Settings02Icon,
    HelpCircleIcon,
  } from "@hugeicons/core-free-icons";
	import { API_URL } from "$lib/constants";

  let { children, navigationItems = [] } = $props();

  // StatusDot state - init undefined to avoid flash on first render
  let isConnected: boolean = $state(false);
  let showHealthModal: boolean = $state(false);
  let tokenUsage = $state(52);

  async function checkConnection() {
    try {
      const response = await fetch(API_URL + '/health', {
        method: 'GET',
        cache: 'no-store' // Ensure we don't cache the health check response
      });
      isConnected = response.ok;
    } catch (_error) {
      console.log('API health check failed:', _error?.message || 'Unknown error');
      isConnected = false;
    }
  }

  onMount(() => {
    checkConnection();
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
          class={`status-dot ${isConnected ? 'bg-constructive' : 'bg-destructive'} w-2 h-2 rounded-full cursor-pointer`}
          role="button"
          tabindex="0"
          title={isConnected ? 'API is healthy' : 'API connection lost'}
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
            <p class="modal-note">This endpoint returns HTTP 200 when the backend is running and healthy.</p>
          </div>
        </div>
      </div>
    {/if}

    <!-- Main Navigation Items -->
    <nav class="flex-1 space-y-1 px-4 py-4 overflow-y-auto">
      {#each navigationItems as item}
        <a
          href={item.href}
          class="flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
        >
          <!-- Target internal icon structures with uniform formatting classes -->
          <HugeiconsIcon
            icon={item.iconRaw || Home01Icon}
            size={20}
            strokeWidth={1.5}
            class="h-5 w-5 flex items-center justify-center"
          />
          <span>{item.name}</span>
        </a>
      {/each}

      <!-- Additional static navigation items -->
      <a
        href="/dashboard"
        class="flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
      >
        <HugeiconsIcon
          icon={Home01Icon}
          size={20}
          strokeWidth={1.5}
          class="h-5 w-5 flex items-center justify-center"
        />
        <span>Dashboard</span>
      </a>

      <a
        href="/analytics"
        class="flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
      >
        <HugeiconsIcon
          icon={Chart01Icon}
          size={20}
          strokeWidth={1.5}
          class="h-5 w-5 flex items-center justify-center"
        />
        <span>Analytics</span>
      </a>

      <a
        href="/users"
        class="flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
      >
        <HugeiconsIcon
          icon={UserGroupIcon}
          size={20}
          strokeWidth={1.5}
          class="h-5 w-5 flex items-center justify-center"
        />
        <span>Users</span>
      </a>

      <a
        href="/settings"
        class="flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
      >
        <HugeiconsIcon
          icon={Settings02Icon}
          size={20}
          strokeWidth={1.5}
          class="h-5 w-5 flex items-center justify-center"
        />
        <span>Settings</span>
      </a>

      <!-- Bottom Sidebar Footer (Profile / Support) -->
      <div class="border-t border-border p-4">
        <a
          href="/support"
          class="flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
        >
          <HugeiconsIcon
            icon={HelpCircleIcon}
            size={20}
            strokeWidth={1.5}
            class="h-5 w-5 flex items-center justify-center"
          />
          <span>Help & Support</span>
        </a>
      </div>
    </nav>
  </aside>
  <!-- Primary Page View Content Area -->
  <main class="flex-1 overflow-y-auto bg-background p-8">
    {@render children?.()}
  </main>
</div>
