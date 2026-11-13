# 0001: Run The Studio as a Claude artifact

Status: Accepted · 2026-11-13

## Context
The Studio needs an AI coach, saved data on phone and laptop, and access to local repos, at $0. A normal web app would need a hosted backend, an AI API key (paid) and auth.

## Decision
Build it as one self-contained HTML page published as a Claude artifact, using the artifact capabilities: `sample` for Claude, `db` for storage in Shawn's account, and `mcp` host servers for laptop files.

## Alternatives considered
- React app on Cloudflare with an AI API: costs money for the AI and needs auth and a database.
- A Claude Project with instructions: no structured data, no board, no sync.

## Consequences
- $0, no deployment, works on any device signed in to Claude.
- AI use counts toward the Claude plan's limits; rate limits are possible.
- The page cannot call outside websites or run code; Claude Code covers git and GitHub.
- Depends on Claude's artifact platform. Everything important also lives as Markdown in this repo, so it survives platform changes.
