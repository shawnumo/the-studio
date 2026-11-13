# The Studio

Read docs/PRD.md, docs/design.md and docs/adr/ before changing anything.

## Stack
- One self-contained HTML file: `src/index.html`. Vanilla JS, no build step, no framework.
- Runs as a Claude artifact on claude.ai. Capabilities: `db` (owner-only rules), `sample` (ask Claude), and `mcp` with `host:filesystem` (`read_text_file`, `edit_file`) for repo sync.
- Fonts: Schibsted Grotesk and JetBrains Mono from Google Fonts. No other network calls are possible from the page.

## Where changes happen
- The app is published from a claude.ai conversation. A change made only in this repo does not reach the live app until it is republished there.
- If you (Claude Code) change `src/index.html`, say so clearly at the end of the session so it gets republished.
- The setup prompt inside `src/index.html` embeds `.claude/hooks/studio-check.cjs`, `.claude/settings.json` and the Studio protocol section below. After changing any of them, run `python tools/embed_setup.py` so the prompt matches.

## Studio protocol (every slice)
The Studio reads `docs/stories.md`, `docs/progress.md`, `.git/HEAD` and `.git/logs/HEAD` from this folder. Keep the formats exact.

1. Work on one slice from `docs/stories.md` at a time, in the order listed.
2. When it's built and tested, change its line to `- [~]` (built, check it on a phone). Only Shawn marks `- [x]`; The Studio does it when he presses Mark done.
3. Add an entry at the top of `docs/progress.md`, under the intro:
   ```
   ## YYYY-MM-DD · S# · Title
   - Built: what changed, in a sentence or two
   - Tests: what ran and the result, e.g. 31 passed
   - Check on your phone: what Shawn should try
   - Next: S# · title of the next slice
   ```
4. Commit the code and both docs together as `feat(S#): <title>`. The Studio reads commit hashes from git, so no Commit line is needed.
5. The Stop hook in `.claude/hooks/studio-check.cjs` won't let you end a turn while the last commit is `feat(S#)` and steps 2–4 aren't done for that slice.
6. End the session with a Studio update block. Shawn pastes it into The Studio when it can't reach this folder (on his phone, say):
   ```
   Studio update · the-studio
   - [~] S# · Title
   ## YYYY-MM-DD · S# · Title
   - Built: …
   - Tests: …
   - Check on your phone: …
   - Next: …
   ```

## Rules
- Follow docs/design.md exactly: colour has one meaning each; no uppercase labels above headings; radius 0 on panels, 2px on controls; mono only for data.
- Every new screen needs its loading, empty and error states.
- $0 only: no paid services, no API keys.
- Stop and flag anything that conflicts with the PRD or an ADR.
