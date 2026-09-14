# SKILL.md - Web Search Diagnostic Tool

## Description
A specialized diagnostic utility designed to troubleshoot failures in the `web_search` tool. It audits the `openclaw.json` configuration and checks for the presence of necessary API environment variables.

## Usage

### Manual Execution
Run the script directly from the terminal to see a formatted report:

```bash
python3 /home/ec/.openclaw/workspace/skills/diagnostic-web-search/web_search_diag.py
```

### Automated Execution
The agent can invoke this script via `exec` when a user reports that web searching is not working.

## Troubleshooting Logic
The tool checks for three critical failure points:
1.  **Configuration Integrity:** Is `openclaw.json` valid and present?
2.  **Provider Registration:** Is a search provider (e.g., Brave, Serper) defined in `models.providers`?
3.  **Environment Readiness:** Are the required API keys (e.g., `BRAVE_API_KEY`) exported in the current environment?

## Actionable Fixes Provided
- Instructions for updating `openclaw.json` to enable the tool.
- URLs for obtaining missing API keys.
- Commands for exporting environment variables.
