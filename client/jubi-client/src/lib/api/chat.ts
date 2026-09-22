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
  timestamp: Date;
}

export interface StreamEvent {
  type: 'message' | 'tool_call' | 'tool_result' | 'error' | 'done';
  node?: string;           // LangGraph node name (orchestrator, coder, researcher)
  content?: string;        // Assistant message chunk
  tool_name?: string;      // Tool being called
  tool_args?: Record<string, any>;
  tool_result?: string;    // Tool output
  error?: string;
  done?: boolean;
}

export interface ChatMessageResponse {
  messages: ChatMessage[];
  status: string;
  token_usage?: number;    // Token usage percentage (0-100)
}

export interface ChatOptions {
  threadId?: string;
  onEvent: (event: StreamEvent) => void;
  onError: (error: Error) => void;
  onComplete: (threadId: string, tokenUsage?: number) => void;
}

// Base API URL - server routes at /chat (no /api/v1 prefix)
const BASE_URL = import.meta.env.VITE_API_URL || '/';

/**
 * Normalize LangGraph stream updates to our StreamEvent format
 */
function normalizeEvent(update: Record<string, any>): StreamEvent {
  const event: StreamEvent = { type: 'message', content: '' };
  
  // Handle LangGraph update structure
  for (const [node, payload] of Object.entries(update)) {
    if (!payload) continue;
    
    const messages = payload.messages || [];
    for (const msg of messages) {
      if (!msg || !msg.content) continue;
      
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
      const createRes = await fetch(`${BASE_URL}/threads`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      
      if (createRes.ok) {
        const data = await createRes.json();
        threadId = data.thread_id;
      } else {
        throw new Error(`Failed to create thread: ${createRes.status}`);
      }
    } catch (err) {
      options.onError(err as Error);
      abortController.abort();
      return;
    }
  }
  
  // Fetch messages history before streaming
  try {
    const historyRes = await fetch(`${BASE_URL}/chat?thread_id=${encodeURIComponent(threadId)}`, {
      headers: { 'Accept': 'application/json' }
    });

    if (historyRes.ok) {
      const data: ChatMessageResponse = await historyRes.json();
      // Convert to ChatMessage[] for UI
      const messages: ChatMessage[] = (data.messages || []).map((m: any) => ({
        id: m.id || crypto.randomUUID(),
        role: m.role as 'user' | 'assistant',
        content: m.content || '',
        timestamp: new Date(m.timestamp || Date.now())
      }));

      // Update parent UI via event or callback if available
      window.dispatchEvent(new CustomEvent('chat:messages-updated', {
        detail: { messages, tokenUsage: data.token_usage }
      }));
    }
  } catch (err) {
    console.warn('Failed to load history:', err);
  }
  
   // Stream response from orchestrator (GET with query params)
   const response = await fetch(`${BASE_URL}/chat?content=${encodeURIComponent(content)}&thread_id=${encodeURIComponent(threadId)}`, {
     method: 'GET',
     headers: {
       'Accept': 'text/event-stream'
     },
     signal: abortController.signal,
     // Disable duplex for SSE (browser handles it)
     duplex: 'half' as const
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
      
      // Parse SSE events
      const lines = buffer.split('\n').filter(line => line.trim());
      buffer = '';  // Reset buffer after parsing
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const event = normalizeEvent(JSON.parse(line.slice(6)));
            options.onEvent(event);
            
            // Check for completion
            if (event.done || event.type === 'error') {
              options.onComplete(threadId);
              break;
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
  } finally {
    // Cleanup
    reader.releaseLock();
  }
}

/**
 * Get current thread ID from localStorage or generate new one (client-side only)
 */
export function getOrCreateThreadId(): string {
  if (typeof window === 'undefined') {
    // SSR fallback - generate random ID
    return `thread-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  let threadId = localStorage.getItem('jubi_thread_id');

  if (!threadId) {
    const timestamp = Date.now().toString();
    threadId = `thread-${timestamp}`;
    localStorage.setItem('jubi_thread_id', threadId);
  }

  return threadId;
}

/**
 * Clear current thread (start new chat)
 */
export function clearThread(): void {
  localStorage.removeItem('jubi_thread_id');
}
