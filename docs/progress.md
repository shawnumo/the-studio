# Progress log

Newest first. One entry per slice session. The Studio reads this file.

## 2026-11-13 · S16 · Build monitor with progress sync from the repo
- Built: the Build tab is now the build monitor. In the Claude desktop app it reads docs/stories.md, docs/progress.md, .git/HEAD and the last commits from git's reflog in the project's folder, when you open the project and when you press Sync now (or S). It shows slices with status, last commit and date, the progress log, and a callout for slices waiting on you with Mark done, which writes [x] into stories.md after the Claude app asks. Each sync is saved to your account, so the phone shows the last snapshot and its time. On the phone, Mark done is kept until you press Write it on the laptop. Also: paste a Studio update (read by a parser, not Claude: the block has a fixed format, so it's instant and exact), a setup prompt for other repos, connecting, failed, missing-file and no-file-server states, Needs you and the board following the slices for projects in Build, and "Move the project to Build" on later phase tabs. Claude Code side: Stop hook (.claude/hooks/studio-check.cjs and .claude/settings.json), the protocol in CLAUDE.md, ADR 0003.
- Tests: 26 browser checks with mocked storage and a mocked file server at 1440×900, 1024×768, 390×844 and 360×800: sync, slow first call, Mark done write, errors by code, missing file, setup prompt, paste update, phone marks, log tab. S0 flow re-run. Stop hook run against 8 git scenarios. No script errors.
- Check on your phone: on the laptop, open The Studio project in the desktop app, go to Build (press Move the project to Build if it's in an earlier phase), set the folder to C:\Projects\the-studio and press Sync now, allowing the file server when the app asks. Then open the project on your phone over mobile data: you should see the same slices and the snapshot time.
- Next: S3 · AI triage and inbox

## 2026-11-13 · S0 · Walking skeleton
- Commit: 38ddc60
- Built: board with Needs you, the five-phase project grid and the inbox; capture (C on desktop, bottom sheet on mobile) saving straight to your Claude account; new project; promote or discard a capture; project page with phase tabs, editable next step, one-liner and exit checklist with the inline finish gate. First-run, loading, offline and "saving in this browser only" states. Shortcuts C, N, B, I, 1–9 and ?. Published over the old Build Studio link; existing projects carried over.
- Tests: browser run with mocked storage at 1440×900 and 390×844; capture by keyboard, promote, checklist tick and finish gate exercised; no script errors.
- Check on your phone: open the link over mobile data, capture something, then see it appear on the laptop.
- Next: S16 progress sync.

## 2026-11-13 · Design · Sync test
- Commit: n/a
- Built: a test page that read C:\Projects\mafia\PRD.md through host:filesystem in the Claude desktop app.
- Tests: 14,471 characters in 438 ms; first call 13 s (permission prompt and server start).
- Next: S0.
