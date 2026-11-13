# The Studio

A personal workspace that runs every project through the five-phase Build Framework (Discover → Define → Design → Build → Ship), with Claude coaching each phase.

- **Live:** https://claude.ai/artifact/58eAFcowX6ge7VZ1v3vunK (private to Shawn; open it in the Claude desktop app for repo sync)
- **Screens:** https://claude.ai/artifact/TUiuZvdvSz2HYGnZLCkRRh
- **Full PRD (source of truth):** https://claude.ai/artifact/TaqRxcnyLvmWs7spbZiHby

## How this repo works

The Studio runs as a Claude artifact. It is built in a claude.ai conversation and published from there; this repo keeps the source and the framework docs so the build is versioned and The Studio can track its own progress.

```
src/index.html        the whole app (one file), as published
docs/PRD.md           snapshot of the PRD
docs/stories.md       slices with status (The Studio reads this)
docs/progress.md      one entry per slice session (The Studio reads this)
docs/design.md        colours, type, spacing, rules
docs/adr/             decisions
CLAUDE.md             rules for any Claude Code session in this repo
```

## Commit after each slice

```
git add -A
git commit -m "feat(S0): walking skeleton"
git push
```

Then add the commit hash to that slice's entry in `docs/progress.md`.
