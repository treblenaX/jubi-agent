/**
 * Chat API Client for Jubi Multi-Agent Harness
 * 
 * Handles SSE streaming from orchestrator agent.
 * Designed to be scalable: works with any agent (orchestrator, coder, researcher)
 */

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  thinking?: string;
  timestamp?: Date;
}

export interface StreamEvent {
  type: 'message' | 'tool_call' | 'tool_result' | 'error' | 'done' | 'context';
  node?: string;           // LangGraph node name (orchestrator, coder, researcher)
  content?: string;        // Assistant message chunk
  thinking?: string;       // Model reasoning (additional_kwargs.reasoning_content)
  tool_name?: string;      // Tool being called
  tool_args?: Record<string, any>;
  tool_result?: string;    // Tool output
  error?: string;
  done?: boolean;
  contextUsed?: number;    // Orchestrator context tokens used
  contextLimit?: number;   // Orchestrator context window (num_ctx)
}

export interface ChatMessageResponse {
  messages: ChatMessage[];
  status: string;
  context?: { used: number; limit: number } | null;
}

export interface ChatOptions {
  threadId?: string;
  onEvent: (event: StreamEvent) => void;
  onError: (error: Error) => void;
  onComplete: (threadId: string, tokenUsage?: number) => void;
}

// Base API URL - server routes at /chat (no /api/v1 prefix)
const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:2024';

/**
 * Normalize LangGraph stream updates to our StreamEvent format
 */
function normalizeEvent(update: Record<string, any>): StreamEvent {
  // Live thinking delta (token-level, from the "messages" stream mode)
  if (update.thinking !== undefined) {
    return { type: 'message', content: '', thinking: update.thinking };
  }

  // Context usage event (emitted after the stream finishes)
  if (update.context) {
    return {
      type: 'context',
      contextUsed: update.context.used,
      contextLimit: update.context.limit
    };
  }

  const event: StreamEvent = { type: 'message', content: '' };
  
  // Handle LangGraph update structure
  for (const [node, payload] of Object.entries(update)) {
    if (!payload) continue;
    
    const messages = payload.messages || [];
    for (const msg of messages) {
      if (!msg || (!msg.content && !msg.thinking)) continue;
      if (msg.thinking) event.thinking = msg.thinking;
      
      // Determine event type based on message properties
      const kind = msg.type || 'ai';
      const isToolCall = Array.isArray(msg.tool_calls);
      const isError = msg.content.startsWith('Error') || msg.content.includes('error');
      
      if (isError) {
        event.type = 'error';
        event.error = msg.content;
      } else if (isToolCall) {
        event.type = 'tool_call';
        event.node = node;
        for (const tc of msg.tool_calls) {
          event.tool_name = tc.name;
          event.tool_args = JSON.stringify(tc.args);
        }
      } else if (kind === 'ai') {
        event.type = 'message';
        event.content = msg.content;
        event.node = node;
      } else if (msg.content.startsWith('Result:')) {
        event.type = 'tool_result';
        event.tool_result = msg.content.replace('Result:', '').trim();
        event.node = node;
      }
      
      // Break after first message per node (simplified for streaming)
      break; 
    }
    
    if (event.type !== 'message') break;
  }
  
  return event;
}

/**
 * Fetch messages history for a thread (used for initial load / thread switch)
 */
export async function fetchHistory(
  threadId: string
): Promise<{ messages: ChatMessage[]; contextUsed?: number; contextLimit?: number }> {
  try {
    const res = await fetch(`${BASE_URL}/chat?thread_id=${encodeURIComponent(threadId)}`, {
      headers: { 'Accept': 'application/json' }
    });
    if (!res.ok) return { messages: [] };
    const data: ChatMessageResponse = await res.json();
    const messages = (data.messages || []).map((m: any) => ({
      id: m.id || crypto.randomUUID(),
      role: (m.role || (m.type === 'human' ? 'user' : 'assistant')) as 'user' | 'assistant',
      content: m.content || '',
      // Server-provided timestamp (message_stamps table); undefined if absent
      timestamp: m.timestamp ? new Date(m.timestamp) : undefined,
      thinking: m.thinking
    }));
    return {
      messages,
      contextUsed: data.context?.used,
      contextLimit: data.context?.limit
    };
  } catch (err) {
    console.warn('Failed to load history:', err);
    return { messages: [] };
  }
}

/**
 * Create a new conversation thread on the server (id generation only —
 * no LLM call; the metadata row is created lazily on the first message).
 */
export async function createThread(): Promise<string> {
  const res = await fetch(`${BASE_URL}/threads`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
  });
  if (!res.ok) {
    throw new Error(`Failed to create thread: ${res.status}`);
  }
  const data = await res.json();
  return data.thread_id;
}

/**
 * Delete a thread: server removes checkpoints + writes + metadata row.
 */
export async function deleteThread(threadId: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/threads/${encodeURIComponent(threadId)}`, {
    method: 'DELETE'
  });
  if (!res.ok) {
    throw new Error(`Failed to delete thread: ${res.status}`);
  }
}

/**
 * Send a message and stream the response from orchestrator agent
 */
export async function sendMessage(
  content: string,
  options: ChatOptions
): Promise<void> {
  const abortController = new AbortController();
  
  // Create thread if no thread_id provided
  let threadId = options.threadId;
  if (!threadId) {
    try {
      threadId = await createThread();
    } catch (err) {
      options.onError(err as Error);
      abortController.abort();
      return;
    }
  }
  
  // Stream response from orchestrator (POST with JSON body)
   const response = await fetch(`${BASE_URL}/chat`, {
     method: 'POST',
     headers: {
       'Content-Type': 'application/json',
       'Accept': 'text/event-stream'
     },
     body: JSON.stringify({ content, thread_id: threadId }),
     signal: abortController.signal,
   });
  
  if (!response.ok || !response.body) {
    const err = new Error(`Failed to stream response: ${response.status}`);
    options.onError(err);
    abortController.abort();
    return;
  }
  
  // Read SSE stream
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();

      if (done) break;
      
      buffer += decoder.decode(value, { stream: true });
      
      // Parse SSE events - handle partial lines
      const lines = buffer.split('\n');
      buffer = lines.pop() || ''; // Keep incomplete line in buffer
      
      for (const line of lines) {
        const trimmed = line.trim();
        if (trimmed.startsWith('data: ')) {
          try {
            const event = normalizeEvent(JSON.parse(trimmed.slice(6)));
            options.onEvent(event);
            
            // Check for completion
            if (event.done || event.type === 'error') {
              options.onComplete(threadId);
              return;
            }
          } catch (parseErr) {
            console.warn('Failed to parse SSE event:', parseErr);
          }
        }
      }
      
      // Check for abort signal
      if (abortController.signal.aborted) {
        break;
      }
    }
    options.onComplete(threadId);
  } finally {
    // Cleanup
    reader.releaseLock();
  }
}

