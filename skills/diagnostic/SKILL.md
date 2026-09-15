# SKILL.md - OpenClaw Diagnostic Skill

## Description
A generalized diagnostic utility for auditing the OpenClaw provider ecosystem. It inspects `openclaw.json` to ensure providers are correctly registered and validates that the necessary environment variables (API keys) are present in the system environment.

## Usage

### Manual Execution
Run the script from the terminal to generate a system readiness report:

```bash
python3 /home/ec/.openclaw/workspace/skills/openclaw-diagnostic-skill/diagnostic_audit.py
```

### Automated Execution
The agent should invoke this skill via `exec` when troubleshooting:
1.  Tool failures (e.g., "provider not found" or "authentication error").
2.  New tool integrations that are not responding as expected.
3.  Configuration changes that have resulted in unexpected behavior.

## Troubleshooting Logic
The skill audits three critical layers:
1.  **Provider Registration:** Checks if the provider is declared in `models.providers` within `openclaw.json`.
2.  **Configuration Integrity:** Ensures each registered provider has mandatory fields (like `api` or `baseUrl`).
3.  **Secret Availability:** Verifies that the expected API keys (e.g., `BRAVE_API_KEY`) are actually exported in the shell environment.

## Actionable Outputs
The tool provides clear status indicators:
- `[OK]`: Configuration is valid.
- `[!]`: A configuration field or environment variable is missing.
- `[CRITICAL]`: A fundamental part of the provider system is missing.

If web search or provider issues are detected, users should run:
`openclaw configure --section web`
