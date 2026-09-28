<script lang="ts">
  // Jubi tool inventory — ground truth from server/app/graph/graph.py.
  // Status: "wired" = attached to an agent · "built" = implemented, not
  // attached · "proposed" = roadmap (see docs/HORIZON_DESIGN.md SPEC-13).
  type Status = 'wired' | 'built' | 'proposed';

  interface Tool {
    name: string;
    purpose: string;
    status: Status;
  }
  interface AgentTools {
    agent: string;
    color: string;
    tools: Tool[];
  }

  const groups: AgentTools[] = [
    {
      agent: 'Orchestrator',
      color: '#7c4dff',
      tools: [
        { name: 'task', purpose: 'Dispatch a work order to a subagent', status: 'wired' },
        { name: 'list_project', purpose: 'List files in the sandbox', status: 'wired' },
        { name: 'read_project_file', purpose: 'Read a sandbox file (read-only peek)', status: 'wired' },
        { name: 'ls / glob / read_file', purpose: 'deepagents backend FS tools', status: 'wired' }
      ]
    },
    {
      agent: 'Coder',
      color: '#00bcd4',
      tools: [
        { name: 'read_project_file', purpose: 'Read a sandbox file', status: 'wired' },
        { name: 'write_project_file', purpose: 'Create/overwrite a sandbox file', status: 'wired' },
        { name: 'edit_project_file', purpose: 'Exact text replacement in a file', status: 'wired' },
        { name: 'list_project', purpose: 'List files in the sandbox', status: 'wired' },
        { name: 'run_shell', purpose: 'Run an allowlisted shell command', status: 'wired' },
        { name: 'run_tests', purpose: 'Run the sandbox test suite', status: 'wired' }
      ]
    },
    {
      agent: 'Researcher',
      color: '#ff9800',
      tools: [
        { name: 'web_search', purpose: 'Search the web', status: 'wired' },
        { name: 'fetch_url', purpose: 'Fetch and extract a URL', status: 'wired' },
        { name: 'read_project_file', purpose: 'Read a sandbox file', status: 'wired' },
        { name: 'list_project', purpose: 'List files in the sandbox', status: 'wired' }
      ]
    },
    {
      agent: 'Built but not wired',
      color: '#9e9e9e',
      tools: [
        { name: 'grep_project', purpose: 'Regex search across sandbox files', status: 'built' },
        { name: 'query_database', purpose: 'SQL query tool (scaffolding)', status: 'built' }
      ]
    }
  ];

  // Roadmap, priority order. Tool hygiene rule: max 6 tools per agent —
  // adding one means swapping one out (SPEC-13).
  const proposed: Tool[] = [
    { name: 'git_status + git_diff', purpose: 'P0 — orchestrator reviews diffs, not whole files; core of the review gate', status: 'proposed' },
    { name: 'run_python', purpose: 'P0 — one-shot script exec; cheap real verification (fabrication antidote)', status: 'proposed' },
    { name: 'run_tests (shaped)', purpose: 'P0 — return failing test names + first error line; full log to file', status: 'proposed' },
    { name: 'lint', purpose: 'P1 — ruff check on changed files', status: 'proposed' },
    { name: 'http_request', purpose: 'P2 — call and inspect HTTP APIs', status: 'proposed' }
  ];

  const statusStyle: Record<Status, string> = {
    wired: 'bg-constructive/15 text-constructive',
    built: 'bg-warning/15 text-warning',
    proposed: 'bg-muted text-muted-foreground'
  };
</script>

<div class="mx-auto flex h-full max-w-3xl flex-col gap-6 overflow-y-auto">
  <header>
    <h1 class="text-2xl font-bold tracking-tight text-foreground">Jubi Tools</h1>
    <p class="mt-1 text-sm text-muted-foreground">
      Tool inventory per agent. Hygiene rule: max 6 tools per agent — add one, swap one.
    </p>
  </header>

  {#each groups as group (group.agent)}
    <section class="rounded-lg border border-border bg-card p-4">
      <div class="flex items-center gap-2">
        <span class="h-2.5 w-2.5 rounded-full" style:background={group.color}></span>
        <h2 class="text-sm font-semibold text-foreground">{group.agent}</h2>
        <span class="ml-auto text-xs text-muted-foreground">{group.tools.length} tools</span>
      </div>
      <ul class="mt-3 grid gap-2">
        {#each group.tools as tool (tool.name)}
          <li class="flex items-start justify-between gap-3 rounded-md border border-border/60 px-3 py-2">
            <div class="min-w-0">
              <code class="text-xs font-semibold text-foreground">{tool.name}</code>
              <p class="mt-0.5 text-xs text-muted-foreground">{tool.purpose}</p>
            </div>
            <span class={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium ${statusStyle[tool.status]}`}>
              {tool.status}
            </span>
          </li>
        {/each}
      </ul>
    </section>
  {/each}

  <section class="rounded-lg border border-border bg-card p-4">
    <div class="flex items-center gap-2">
      <span class="h-2.5 w-2.5 rounded-full bg-primary"></span>
      <h2 class="text-sm font-semibold text-foreground">Proposed additions</h2>
      <span class="ml-auto text-xs text-muted-foreground">{proposed.length} items</span>
    </div>
    <ul class="mt-3 grid gap-2">
      {#each proposed as tool (tool.name)}
        <li class="flex items-start justify-between gap-3 rounded-md border border-border/60 px-3 py-2">
          <div class="min-w-0">
            <code class="text-xs font-semibold text-foreground">{tool.name}</code>
            <p class="mt-0.5 text-xs text-muted-foreground">{tool.purpose}</p>
          </div>
          <span class={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium ${statusStyle[tool.status]}`}>
            {tool.status}
          </span>
        </li>
      {/each}
    </ul>
  </section>
</div>
