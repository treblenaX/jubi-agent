<script lang="ts">
  import * as Message from "$lib/components/ui/message";
  import * as Avatar from "$lib/components/ui/avatar";
  import * as Bubble from "$lib/components/ui/bubble";

  import Chatbox from "./Chatbox.svelte";

  import { sendMessage, getOrCreateThreadId } from "$lib/api/chat";

  // Messages state
  let messages = $state<Array<{id: string, role: 'user' | 'assistant', content: string, timestamp?: Date}>>([]);
  
  // Streaming state
  let isStreaming = $state(false);
  let pendingAssistantMsg = $state('');
  let streamingMsgId = $state<string | null>(null);
  
  // Thread persistence
  let currentThreadId = $state<string | null>(null);

  // Mode selector (kept for future agent selection)
  let chatMode = 'auto' as 'auto' | 'agent' | 'manual';
  let tokenUsage = 52;

  // Initialize thread ID on mount
  $effect(() => {
    if (!currentThreadId) {
      currentThreadId = getOrCreateThreadId();
    }
  });

  // Handle user input change
  let userValue = "";

  const handleSend = async (content: string) => {
    if (!content.trim() || isStreaming) return;

    // 1. Add user message immediately
    messages.push({ id: crypto.randomUUID(), role: 'user', content, timestamp: new Date() });

    // 2. Prepare assistant placeholder
    const assistantId = crypto.randomUUID();
    streamingMsgId = assistantId;
    pendingAssistantMsg = '';
    messages.push({ id: assistantId, role: 'assistant', content: '', timestamp: new Date() });
    isStreaming = true;

    // 3. Stream from orchestrator agent
    await sendMessage(content, {
      threadId: currentThreadId,
      onEvent: (event) => handleStreamEvent(event),
      onError: (err) => {
        console.error('Chat error:', err);
        // Show error in UI
        if (streamingMsgId) {
          messages[streamingMsgId] = { ...messages[streamingMsgId], content: `Error: ${err.message}` };
        }
      },
      onComplete: (threadId, tokenUsage = 52) => {
        currentThreadId = threadId;
        isStreaming = false;
        streamingMsgId = null;
        // Update token usage from API response
        if (tokenUsage !== undefined) {
          tokenUsage = tokenUsage as number;
        }
      }
    });
  };

  const handleStreamEvent = (event: any) => {
    switch (event.type) {
      case 'message':
        if (event.content) {
          pendingAssistantMsg += event.content;
          updateMessage(streamingMsgId!, pendingAssistantMsg);
        }
        break;
      case 'tool_call':
        // Optional: show tool call indicator
        console.log('Tool called:', event.tool_name);
        break;
      case 'tool_result':
        // Optional: show tool result
        console.log('Tool result:', event.tool_result);
        break;
      case 'error':
        if (streamingMsgId) {
          messages[streamingMsgId] = { ...messages[streamingMsgId], content: `Error: ${event.error}` };
        }
        isStreaming = false;
        streamingMsgId = null;
        break;
      case 'done':
        isStreaming = false;
        streamingMsgId = null;
        break;
    }
  };

  const updateMessage = (msgId: string, content: string) => {
    const msgIndex = messages.findIndex(m => m.id === msgId);
    if (msgIndex !== -1) {
      messages[msgIndex] = { ...messages[msgIndex], content };
    }
  };

  // Fetch history on mount
  $effect(() => {
    if (!currentThreadId || isStreaming) return;
    fetchHistory();
  });

  const fetchHistory = async () => {
    try {
      const res = await fetch(`/api/v1/chat?thread_id=${encodeURIComponent(currentThreadId)}`);
      if (res.ok) {
        const data = await res.json();
        messages = (data.messages || []).map((m: any) => ({
          id: m.id || crypto.randomUUID(),
          role: m.role as 'user' | 'assistant',
          content: m.content || '',
          timestamp: new Date(m.timestamp || Date.now())
        }));
      }
    } catch (err) {
      console.warn('Failed to load history:', err);
    }
  };
</script>

<div class="chat-container overflow-y-auto flex flex-col">
  <div class="flex-1 overflow-y-auto p-4 space-y-6">
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
              <Bubble.Content>{message.content}</Bubble.Content>
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
