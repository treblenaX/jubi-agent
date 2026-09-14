# USER.md - User Model

Store stable user preferences and profile facts as directives that can guide future sessions.

Use one directive per entry:

```md
<!-- observed: YYYY-MM-DD | status: active -->

- Prefer concise progress updates during implementation work.
```

- Begin each directive with an imperative such as `Always`, `Never`, or `Prefer`.
- Record the observation date and either `active` or `superseded` on the metadata line.
- When a preference changes, mark the old entry `superseded` and rewrite the active directive in place. Never append a contradictory active directive.
- Keep stable communication style, relationships, and active-project context here. Put durable non-profile facts and decisions in `MEMORY.md`.
- Save this file at the workspace root as `USER.md`. It loads every session with a separate 4,000-character budget.

## Directives

<!-- observed: 2026-09-14 | status: active -->

- Prefer a collaborative, "familiar-like" relationship where Jubi learns from and adapts to the user's specific habits and thought processes.

<!-- observed: 2026-09-14 | status: active -->

- Always rebase the current branch onto `origin/main` before creating or updating any Pull Requests to ensure a clean, conflict-free history.

<!-- observed: 2026-09-14 | status: active -->

- When raising or updating a Pull Request, always perform a "Two-Step Verification":
    1. **Local Verification**: Run `git merge origin/main` locally to ensure there are no merge conflicts.
    2. **Remote Verification**: After pushing, run `gh pr view <number> --json mergeable` to confirm the status is `true`.
