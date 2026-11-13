# 0002: Read repo progress through a local file server in the Claude desktop app

Status: Accepted · 2026-11-13 · Amended by 0003 (commits now come from git's reflog; `edit_file` added for Mark done)

## Context
The Build monitor must show what Claude Code did in a repo. The page can't call GitHub, and the claude.ai GitHub Integration is read-only for chats and projects, not usable by a page.

## Decision
Run `@modelcontextprotocol/server-filesystem` in the Claude desktop app, allowed on `C:\Projects` only, and call it from The Studio as `host:filesystem` with read-only tools (`list_allowed_directories`, `read_text_file`). The Studio reads `docs/stories.md` and `docs/progress.md`; each progress entry records its commit hash because the server can't run git.

## Evidence
Test on 2026-11-13: read `C:\Projects\mafia\PRD.md` (14,471 characters) in 438 ms. The first call took 13 s (permission prompt and server start).

## Alternatives considered
- GitHub connector with write tools: none available.
- A git MCP server: extra setup for little gain; commit hashes in progress.md are enough.
- Paste-only updates: kept as the fallback.

## Consequences
- Sync works only in the desktop app and only for the owner. The phone shows the last snapshot with its time.
- The first sync of a session needs a "Connecting to your laptop" state.
