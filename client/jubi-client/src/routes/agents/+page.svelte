<script lang="ts">
  // Jubi multi-agent architecture overview.
  // Orchestrator delegates to Coder and Researcher subagents (deepagents).
  const agents = [
    {
      id: 'orchestrator',
      name: 'Orchestrator',
      role: 'Plans tasks and delegates to subagents',
      color: '#7c4dff',
      position: { x: 400, y: 110 }
    },
    {
      id: 'coder',
      name: 'Coder',
      role: 'Code generation & editing',
      color: '#00bcd4',
      position: { x: 200, y: 330 }
    },
    {
      id: 'researcher',
      name: 'Researcher',
      role: 'Deep research & analysis',
      color: '#ff9800',
      position: { x: 600, y: 330 }
    }
  ];

  const connections = [
    { from: 'orchestrator', to: 'coder' },
    { from: 'orchestrator', to: 'researcher' }
  ];

  // Resolve edges to coordinates up front — no template gymnastics.
  const nodeRadius = 44;
  const edges = connections.flatMap((c) => {
    const from = agents.find((a) => a.id === c.from);
    const to = agents.find((a) => a.id === c.to);
    if (!from || !to) return [];
    const dx = to.position.x - from.position.x;
    const dy = to.position.y - from.position.y;
    const len = Math.hypot(dx, dy);
    return [
      {
        x1: from.position.x + (dx / len) * nodeRadius,
        y1: from.position.y + (dy / len) * nodeRadius,
        x2: to.position.x - (dx / len) * (nodeRadius + 10),
        y2: to.position.y - (dy / len) * (nodeRadius + 10)
      }
    ];
  });
</script>

<div class="mx-auto flex h-full max-w-3xl flex-col gap-6">
  <header>
    <h1 class="text-2xl font-bold tracking-tight text-foreground">Jubi Agents</h1>
    <p class="mt-1 text-sm text-muted-foreground">
      Multi-agent architecture — the orchestrator delegates work to specialized subagents.
    </p>
  </header>

  <!-- Graph -->
  <div class="rounded-lg border border-border bg-card p-4">
    <svg
      class="w-full"
      viewBox="0 0 800 440"
      preserveAspectRatio="xMidYMid meet"
      aria-label="Agent delegation graph"
    >
      <defs>
        <marker
          id="arrowhead"
          markerWidth="10"
          markerHeight="7"
          refX="9"
          refY="3.5"
          orient="auto"
        >
          <polygon points="0 0, 10 3.5, 0 7" fill="var(--muted-foreground)" />
        </marker>
      </defs>

      {#each edges as edge (edge.x1 + '-' + edge.x2)}
        <line
          x1={edge.x1}
          y1={edge.y1}
          x2={edge.x2}
          y2={edge.y2}
          stroke="var(--muted-foreground)"
          stroke-width="2"
          marker-end="url(#arrowhead)"
        />
      {/each}

      {#each agents as agent (agent.id)}
        <g role="img" aria-label={`${agent.name}: ${agent.role}`}>
          <circle
            cx={agent.position.x}
            cy={agent.position.y}
            r={nodeRadius}
            fill={agent.color}
            fill-opacity="0.15"
            stroke={agent.color}
            stroke-width="2"
          />
          <text
            x={agent.position.x}
            y={agent.position.y + 5}
            text-anchor="middle"
            fill="var(--foreground)"
            font-size="15"
            font-weight="600"
          >
            {agent.name}
          </text>
          <text
            x={agent.position.x}
            y={agent.position.y + nodeRadius + 22}
            text-anchor="middle"
            fill="var(--muted-foreground)"
            font-size="13"
          >
            {agent.role}
          </text>
        </g>
      {/each}
    </svg>
  </div>

  <!-- Agent details -->
  <div class="grid gap-3 sm:grid-cols-3">
    {#each agents as agent (agent.id)}
      <div class="rounded-lg border border-border bg-card p-4">
        <div class="flex items-center gap-2">
          <span class="h-2.5 w-2.5 rounded-full" style:background={agent.color}></span>
          <span class="text-sm font-semibold text-foreground">{agent.name}</span>
        </div>
        <p class="mt-1.5 text-xs text-muted-foreground">{agent.role}</p>
      </div>
    {/each}
  </div>
</div>
