# The Studio

Read docs/PRD.md, docs/design.md and docs/adr/ before changing anything.

## Stack
- One self-contained HTML file: `src/index.html`. Vanilla JS, no build step, no framework.
- Runs as a Claude artifact on claude.ai. Capabilities: `db` (owner-only rules), `sample` (ask Claude), and from S16 `mcp` with `host:filesystem`.
- Fonts: Schibsted Grotesk and JetBrains Mono from Google Fonts. No other network calls are possible from the page.

## Where changes happen
- The app is published from a claude.ai conversation. A change made only in this repo does not reach the live app until it is republished there.
- If you (Claude Code) change `src/index.html`, say so clearly at the end of the session so it gets republished.

## Studio protocol (every slice)
1. Work on one slice from `docs/stories.md` at a time.
2. When it is built, mark it `- [~]` (built, needs checking on a phone); Shawn marks it `- [x]` after checking.
3. Add an entry at the top of `docs/progress.md`: date, slice ID and title, commit hash, what was built, tests, what to check, next slice.
4. Commit as `feat(S#): <title>`.

## Rules
- Follow docs/design.md exactly: colour has one meaning each; no uppercase labels above headings; radius 0 on panels, 2px on controls; mono only for data.
- Every new screen needs its loading, empty and error states.
- $0 only: no paid services, no API keys.
- Stop and flag anything that conflicts with the PRD or an ADR.
