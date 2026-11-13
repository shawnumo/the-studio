# Progress log

Newest first. One entry per slice session. The Studio reads this file.

## 2026-11-13 · S4 · Discover coach with auto-interview
- Built: Discover now opens on a coach chat (Claude's default tier, streamed, with Stop). When the idea is vague, or you tap Interview me, Claude interviews you one question at a time: a blue banner shows the question count and the reason, with Back to free chat (Esc). Questions with obvious answers show tappable choices (keys 1 to 5 on desktop) and the message box doubles as the Other field; answered questions fold into a list with Change. When the interview ends, or when you ask, Claude sums up and drafts a one-liner and an idea score that you approve with Use this one-liner and Use these scores, which also tick those checklist items. The side panel (Outputs tab on a phone) shows the idea score, one-liner, what the coach knows, next step and checklist. Each project's chat is saved to your account. When a chat nears the 256 KB a saved chat can hold, The Studio asks before trimming the oldest messages (Not now is fine until it's full, then sending waits for a trim); the coach's notes keep what they said. The browser tests now live in tests/ (s3.py, s4.py, s16.py; see tests/README.md).
- Tests: tests/s4.py, 84 checks with a mocked, streaming Claude and mocked storage: interview start, banner, choices by key and tap, typed answers, Change, Esc to free chat, draft and use, rate-limit error and retry, Stop, reload, a long chat that asks before trimming and blocks sending when full, no-Claude view, 1440, 1024, 390 and 360 wide, light and dark. tests/s3.py (27) and tests/s16.py (26) re-run. No script errors.
- Check on your phone: open a project in Discover, tap Interview me, answer a few questions by tapping, open Outputs, then ask for the one-liner and use it.
- Next: S5 · Phase-appropriate views

## 2026-11-13 · S3 · AI triage and inbox
- Built: every new capture is scored by Claude (quick tier) on the six Discover rubric rows from the Build Framework, with reasoning, tags and a working title. The verdict follows the framework's rules: Killed on 1 for Pain or Free to run, Promising on 3 or more on every row, otherwise Park. The inbox has All, Promising, Park and Killed tabs, a detail pane with editable 1 to 5 scores, a verdict you can override, and Promote, Keep and Discard. Promoting names the project from Claude's title, attaches the triage to Discover and ticks the rubric checklist item when every row is 3 or more. One button triages older captures in batches. An About you note tells Claude what you want to learn. Errors are explained by cause, and focus now survives re-renders for keyboard use.
- Tests: 27 browser checks with a mocked Claude: batch call on the quick tier, kill rule, score edits and overrides, pending state, keep, promote, rate limit and not-allowed errors, no-Claude view, 390 and 1440 wide, light and dark. S16 checks (26 passed), S0 flow and the bottom-bar check re-run. No script errors.
- Check on your phone: capture an idea, watch it get triaged, open it and change one score.
- Next: S4 · Discover coach with auto-interview

## 2026-11-13 · S17 · Light theme that follows the device
- Built: a light palette that switches on when the device (or the Claude app) is in light mode. Same colour meanings; darker shades for amber, blue, green and red text, and a deeper amber for markers so they stay visible. Icons take their colours from the theme. Also fixed the mobile bottom bar floating up on short pages.
- Tests: every text colour pair checked for contrast (all pass AA; markers 3:1); light screenshots at 1440 × 900 and 390 × 844; S16 checks (26 passed) and the S0 flow re-run in dark mode. No script errors.
- Check on your phone: switch the phone between light and dark mode; The Studio should follow.
- Next: S3 · AI triage and inbox

## 2026-11-13 · S16 · Fixes from the phone check
- Built: each slice row on mobile shows its last commit and date under the title; commit dates now include the time. Slice rows open and close (tap on mobile, click or Enter on desktop) to list every commit that mentions the slice, with hash, date, time and message. The check note in the callout and the log entries are no longer cut off.
- Tests: S16 browser checks re-run (26 passed), plus expand and collapse at 1440 × 900 and 390 × 844, by mouse, tap and keyboard. No script errors.
- Check on your phone: open the Build tab, check the hash, date and time under S0, then tap S16 to see its commits.
- Next: S3 · AI triage and inbox

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
