# search-web SKILL.md

## Description
A fallback search skill. It attempts to use the Brave Search MCP tool if available; otherwise, it falls back to the default `web_search` tool.

## Implementation Logic
1.  **Discovery**: Search for available tools using `tool_search` with the query `brave`.
2.  **Selection**:
    *   If a tool with a name containing `brave` and `search` is found (e.g., `brave_search:search`), select it as the `primary_tool`.
    *   Otherwise, set `primary_tool` to `null`.
3.  **Execution**:
    *   If `primary_tool` is not `null`:
        *   Attempt to call `primary_tool` with the provided `query`.
        *   If successful, return the results.
        *   If the call fails (error, timeout, etc.), log the error and proceed to the **Fallback**.
    *   **Fallback**:
        *   Call the default `web_search` tool with the `query`.
        *   Return the results from `web_search`.

## Usage
`search-web(query: string)`
