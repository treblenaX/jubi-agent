<script lang="ts">
  import * as Message from "$lib/components/ui/message";
  import * as Bubble from "$lib/components/ui/bubble";
  import { renderMarkdown } from "$lib/utils/markdown";

  interface ChatMessage {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    thinking?: string;
    timestamp?: Date;
  }

  // Presentational: messages are owned by ChatPage
  let { messages }: { messages: ChatMessage[] } = $props();

  // Auto-scroll: pin to bottom while streaming; don't yank if user scrolled up
  let containerEl = $state<HTMLElement | undefined>(undefined);
  let lastCount = 0;

  $effect(() => {
    // Track message count + last message content (streaming updates retrigger this)
    const count = messages.length;
    const _lastContent = messages[count - 1]?.content ?? '';
    const _lastThinking = messages[count - 1]?.thinking ?? ''; // thinking growth also retriggers scroll
    const el = containerEl;
    if (!el) return;

    const isNewMessage = count !== lastCount;
    lastCount = count;
    const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 150;
    if (isNewMessage || nearBottom) {
      el.scrollTop = el.scrollHeight;
    }
  });
</script>

<div class="chat-container h-full overflow-y-auto" bind:this={containerEl}>
  <div class="p-4 space-y-6">
    {#if messages.length === 0}
      <!-- Welcome message -->
      <Message.Root>
        <Message.Content>
          <Message.Header>Jubi</Message.Header>
          <Bubble.Root variant="muted">
            <Bubble.Content>
              Hello! I'm Jubi, your assistant. How can I help you today?
            </Bubble.Content>
          </Bubble.Root>
        </Message.Content>
      </Message.Root>
    {:else}
      <!-- Message list -->
      {#each messages as message (message.id)}
        <Message.Root align={message.role === 'user' ? 'end' : 'start'}>
          <Message.Content>
            {#if message.thinking}
              <details class="thinking-block" open={message.content === ''}>
                <summary>Thoughts</summary>
                <div class="thinking-body md-body">{@html renderMarkdown(message.thinking)}</div>
              </details>
            {/if}
            <Message.Header>{message.role === 'user' ? 'You' : 'Jubi'}</Message.Header>
            <Bubble.Root variant={message.role === 'user' ? '' : 'muted'}>
              <Bubble.Content>
                {#if message.role === 'assistant' && message.content === ''}
                  <!-- Still thinking: no content streamed yet -->
                  <span class="shimmer">Thinking…</span>
                {:else}
                  <div class="md-body">{@html renderMarkdown(message.content)}</div>
                {/if}
              </Bubble.Content>
            </Bubble.Root>
            {#if message.timestamp}
              <Message.Footer>
                {message.timestamp.toDateString() === new Date().toDateString()
                  ? message.timestamp.toLocaleTimeString()
                  : message.timestamp.toLocaleString()}
              </Message.Footer>
            {/if}
          </Message.Content>
        </Message.Root>
      {/each}
    {/if}
  </div>
</div>

<style>
  .thinking-block summary {
    cursor: pointer;
    font-size: 0.75rem;
    color: var(--muted-foreground);
    user-select: none;
  }
  .thinking-body {
    max-height: 12rem;
    overflow-y: auto;
    margin-top: 0.375rem;
    padding: 0.375rem 0.625rem;
    border-left: 2px solid var(--border);
    font-size: 0.75rem;
    line-height: 1.4;
    color: var(--muted-foreground);
  }

  /* Markdown rendering ({@html} content needs :global under the wrapper) */
  .md-body :global(p) {
    margin: 0.25rem 0;
  }
  .md-body :global(p:first-child),
  .md-body :global(*:first-child) {
    margin-top: 0;
  }
  .md-body :global(p:last-child),
  .md-body :global(*:last-child) {
    margin-bottom: 0;
  }
  .md-body :global(ul),
  .md-body :global(ol) {
    margin: 0.25rem 0;
    padding-left: 1.25rem;
  }
  .md-body :global(code) {
    font-family: var(--font-mono);
    font-size: 0.85em;
    background: color-mix(in oklab, var(--muted) 80%, transparent);
    padding: 0.1rem 0.3rem;
    border-radius: calc(var(--radius) - 6px);
  }
  .md-body :global(pre) {
    margin: 0.375rem 0;
    padding: 0.5rem 0.75rem;
    border-radius: calc(var(--radius) - 4px);
    background: var(--muted);
    overflow-x: auto;
  }
  .md-body :global(pre code) {
    background: transparent;
    padding: 0;
    font-size: 0.8rem;
  }
  .md-body :global(h1),
  .md-body :global(h2),
  .md-body :global(h3),
  .md-body :global(h4) {
    font-weight: 600;
    margin: 0.5rem 0 0.25rem;
  }
  .md-body :global(a) {
    color: var(--primary);
    text-decoration: underline;
  }
  .md-body :global(blockquote) {
    margin: 0.375rem 0;
    padding-left: 0.625rem;
    border-left: 2px solid var(--border);
    color: var(--muted-foreground);
  }
  .md-body :global(table) {
    border-collapse: collapse;
    margin: 0.375rem 0;
    font-size: 0.85em;
  }
  .md-body :global(th),
  .md-body :global(td) {
    border: 1px solid var(--border);
    padding: 0.2rem 0.5rem;
    text-align: left;
  }
  .md-body :global(hr) {
    border-color: var(--border);
    margin: 0.5rem 0;
  }
</style>
