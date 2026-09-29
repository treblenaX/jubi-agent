<script lang="ts">
  import * as Message from "$lib/components/ui/message";
  import * as Bubble from "$lib/components/ui/bubble";
  import { renderMarkdown } from "$lib/utils/markdown";
  import type { ChatMessage } from "$lib/api/chat";

  // Presentational: messages + transcripts are owned by ChatPage
  let {
    messages,
    transcripts,
    thoughtsExpanded = true,
    showRecovered = false
  }: {
    messages: ChatMessage[];
    transcripts?: Record<string, string>;
    thoughtsExpanded?: boolean;
    showRecovered?: boolean;
  } = $props();

  // Auto-scroll: pin to bottom while streaming; don't yank if user scrolled up
  let containerEl = $state<HTMLElement | undefined>(undefined);
  let lastCount = 0;

  $effect(() => {
    // Track message count + last message content (streaming updates retrigger this)
    const count = messages.length;
    const last = messages[count - 1];
    const _lastContent = last?.content ?? '';
    const _lastThinking = last?.thinking ?? ''; // thinking growth also retriggers scroll
    // Timeline growth (thinking/tool/text entries) and transcript polls also retrigger
    const tl = last?.timeline;
    const _tlLen = tl?.length ?? 0;
    const _tlLast = tl?.[tl.length - 1]?.text?.length ?? 0;
    const _txCount = transcripts ? Object.keys(transcripts).length : 0;
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
            <Message.Header>{message.role === 'user' ? 'You' : 'Jubi'}</Message.Header>
            {#if message.timeline}
              <!-- Chronological timeline: thoughts, tool/dispatch lines, text -->
              {#each message.timeline as e, i (i)}
                {#if e.kind === 'thinking' && e.text}
                  <details class="thinking-block" open={thoughtsExpanded}>
                    <summary>Thoughts</summary>
                    <div class="thinking-body md-body">{@html renderMarkdown(e.text)}</div>
                  </details>
                {:else if e.kind === 'tool'}
                  <div class="activity-line">
                    {#if e.status === 'running'}
                      <span class="live-dot" aria-label="running"></span>
                    {:else}
                      <span class="glyph">✓</span>
                    {/if}
                    {#if e.ts}
                      <span class="ts">{new Date(e.ts).toLocaleTimeString([], { hour12: false })}</span>
                    {/if}
                    <span class="node">{e.node}</span>
                    <span class="tool">{e.label}</span>
                    {#if e.result}
                      <span class="result">→ {e.result}</span>
                    {:else if e.args}
                      <span class="args">{e.args}</span>
                    {/if}
                  </div>
                  {#if e.subagent && transcripts?.[e.subagent]}
                    <!-- Subagent chat panel: polled transcript of the dispatch -->
                    <details class="transcript" open={e.status === 'running'}>
                      <summary>subagent chat {e.status === 'running' ? '· live' : ''}</summary>
                      <pre>{transcripts[e.subagent]}</pre>
                    </details>
                  {/if}
                {:else if e.kind === 'text' && e.text}
                  <Bubble.Root variant="muted">
                    <Bubble.Content>
                      <div class="md-body">{@html renderMarkdown(e.text)}</div>
                    </Bubble.Content>
                  </Bubble.Root>
                {/if}
              {/each}
              {#if !message.timeline.some((e) => e.kind === 'text')}
                <!-- Still working: nothing final streamed yet -->
                <Bubble.Root variant="muted">
                  <Bubble.Content><span class="shimmer">Thinking…</span></Bubble.Content>
                </Bubble.Root>
              {/if}
            {:else}
              {#if message.thinking}
                <details class="thinking-block" open={thoughtsExpanded}>
                  <summary>Thoughts</summary>
                  <div class="thinking-body md-body">{@html renderMarkdown(message.thinking)}</div>
                </details>
              {/if}
              <Bubble.Root variant={message.role === 'user' ? 'default' : 'muted'}>
                <Bubble.Content>
                  {#if message.role === 'assistant' && message.content === ''}
                    <!-- Still thinking: no content streamed yet -->
                    <span class="shimmer">Thinking…</span>
                  {:else}
                    <div class="md-body">{@html renderMarkdown(message.content)}</div>
                  {/if}
                </Bubble.Content>
              </Bubble.Root>
            {/if}
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

    {#if showRecovered && transcripts && Object.keys(transcripts).length > 0}
      <!-- Recovered dispatch transcripts after a refresh (no live feed) -->
      <div class="activity-feed" aria-live="polite">
        <div class="activity-title">Subagent chats · last dispatch</div>
        {#each Object.entries(transcripts) as [name, text] (name)}
          <details class="transcript">
            <summary>dispatch → {name}</summary>
            <pre>{text}</pre>
          </details>
        {/each}
      </div>
    {/if}
  </div>
</div>

<style>
  /* Live activity feed: one monospace line per tool call/result */
  .activity-feed {
    display: grid;
    gap: 0.25rem;
    padding-left: 0.625rem;
    border-left: 2px solid var(--border);
    font-family: var(--font-mono);
    font-size: 0.72rem;
    color: var(--muted-foreground);
  }
  .activity-title {
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--muted-foreground);
  }
  .activity-line {
    display: flex;
    align-items: baseline;
    gap: 0.4rem;
    min-width: 0;
  }
  .glyph {
    color: var(--constructive);
  }
  /* Pulsing dot: a dispatch/tool call is in flight */
  .live-dot {
    width: 0.45rem;
    height: 0.45rem;
    border-radius: 9999px;
    background: var(--primary);
    animation: dot-pulse 1.2s ease-in-out infinite;
    flex-shrink: 0;
    align-self: center;
  }
  .ts {
    color: var(--muted-foreground);
    font-variant-numeric: tabular-nums;
    flex-shrink: 0;
  }
  .node {
    color: var(--primary);
    flex-shrink: 0;
  }
  .tool {
    color: var(--foreground);
    flex-shrink: 0;
  }
  .args,
  .result {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 30rem;
  }
  /* Subagent chat panel under a dispatch line */
  .transcript {
    margin: 0.15rem 0 0.35rem 1.35rem;
  }
  .transcript summary {
    cursor: pointer;
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--muted-foreground);
    user-select: none;
  }
  .transcript pre {
    margin: 0.35rem 0 0;
    padding: 0.375rem 0.625rem;
    max-height: 16rem;
    overflow-y: auto;
    border-left: 2px solid var(--border);
    font-size: 0.68rem;
    line-height: 1.45;
    white-space: pre-wrap;
    word-break: break-word;
    color: var(--muted-foreground);
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
