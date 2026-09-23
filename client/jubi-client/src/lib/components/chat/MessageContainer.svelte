<script lang="ts">
  import * as Message from "$lib/components/ui/message";
  import * as Bubble from "$lib/components/ui/bubble";

  interface ChatMessage {
    id: string;
    role: 'user' | 'assistant';
    content: string;
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
          <Message.Header>Olivia</Message.Header>
          <Bubble.Root variant="muted">
            <Bubble.Content>
              Hello! I'm Olivia, your Jubi assistant. How can I help you today?
            </Bubble.Content>
          </Bubble.Root>
        </Message.Content>
      </Message.Root>
    {:else}
      <!-- Message list -->
      {#each messages as message (message.id)}
        <Message.Root align={message.role === 'user' ? 'end' : 'start'}>
          <Message.Content>
            <Message.Header>{message.role === 'user' ? 'You' : 'Olivia'}</Message.Header>
            <Bubble.Root variant={message.role === 'user' ? '' : 'muted'}>
              <Bubble.Content>
                {#if message.role === 'assistant' && message.content === ''}
                  <!-- Still thinking: no content streamed yet -->
                  <span class="shimmer">Thinking…</span>
                {:else}
                  {message.content}
                {/if}
              </Bubble.Content>
            </Bubble.Root>
            {#if message.timestamp}
              <Message.Footer>
                <div>
                  Read <span class="font-normal">{message.timestamp.toLocaleTimeString()}</span>
                </div>
              </Message.Footer>
            {/if}
          </Message.Content>
        </Message.Root>
      {/each}
    {/if}
  </div>
</div>