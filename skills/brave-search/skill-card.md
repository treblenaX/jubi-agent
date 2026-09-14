## Description:

Web search and content extraction via Brave Search API. Use for searching documentation, facts, or any web content. Lightweight, no browser required.

This skill is ready for commercial/non-commercial use.

## Publisher:

[steipete](https://clawhub.ai/user/steipete)

### License/Terms of Use:

MIT

## Use Case:

Developers and agents use this skill to search the web, retrieve search result titles, links, and snippets, and optionally extract readable page content as markdown for documentation, facts, or current web information.

### Deployment Geography for Use:

Global

## Known Risks and Mitigations:

Risk: Search queries and requested URLs may be sent from the agent environment to Brave and third-party sites.

Mitigation: Avoid secrets, private hostnames, localhost, cloud metadata addresses, intranet URLs, and sensitive internal content when using this skill.

Risk: The page extraction command can fetch arbitrary URLs from the agent environment.

Mitigation: Review URLs before execution and restrict use to public, expected destinations until URL validation and clearer disclosure are added.

Risk: The documentation says Brave Search API is used, while the scanner notes the Brave usage is misstated.

Mitigation: Verify the actual Brave access path and terms before relying on the skill in managed or commercial environments.

## Reference(s):

- [ClawHub Skill Page](https://clawhub.ai/steipete/skills/brave-search)
- [Publisher Profile](https://clawhub.ai/user/steipete)
- [Brave Search](https://search.brave.com/)

## Skill Output:

**Output Type(s):** [text, markdown, shell commands, guidance]

**Output Format:** [Plain text search results with optional markdown page content]

**Output Parameters:** [1D]

**Other Properties Related to Output:** [Search output includes result title, link, and snippet; extracted page content is truncated by the skill when fetched through search with content.]

## Skill Version(s):

1.0.1 (source: server release metadata; package.json reports 1.0.0)

## Ethical Considerations:

Users should evaluate whether this skill is appropriate for their environment, review any generated or modified files before relying on them, and apply their organization's safety, security, and compliance requirements before deployment.
