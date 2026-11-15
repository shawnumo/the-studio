# The Studio · slices

The Studio reads this file. One line per slice: status box, ID, a middle dot, then the title.
`[ ]` to do · `[~]` built, check it on your phone · `[x]` done

Build order is riskiest first. Full stories and acceptance criteria are in the PRD.

## Must
- [x] S0 · Walking skeleton: board, capture, projects saved to your account, published
- [x] S2 · Quick capture from any screen (C on desktop, sheet on mobile)
- [x] S8 · Phase checklists, finish gate and progress on the board
- [x] S16 · Build monitor with progress sync from the repo
- [x] S3 · AI triage and inbox
- [x] S4 · Discover coach with auto-interview
- [x] S5 · Phase-appropriate views
- [x] S6 · AI drafts
- [x] S7 · Tracked-changes approval
- [x] S1 · Projects board: drafts to review and last Claude Code session on each row
- [x] S10 · Claude Code handoff

## Should
- [x] S9 · Rendered Mermaid diagrams
- [x] S12 · Claude Code prompt per slice
- [x] S14 · Ship checklist, feedback and changelog
- [x] S15 · Keyboard shortcuts (C, N, B, I, 1–9, ?, E, and A, R, J, K, U in a review)
- [x] S17 · Follow the device's light or dark theme

## Could
- [x] S18 · Case study from a shipped project
  As Shawn, I want Claude to draft a portfolio case study from a shipped project so I can show what I built without writing it up from scratch.
  - Given a shipped project, when I open the Case study tab in Ship (beside Changelog) and choose Draft with Claude, then Claude writes it as it streams in, with Stop, from the saved PRD, architecture and ADRs, the progress log, the versions, the live URL and the feedback.
  - Given missing facts (who used it, numbers, what I'd do differently), when Claude drafts, then it writes TBD: lines instead of inventing them.
  - Given a draft, when I edit it, then it saves to my account, and Draft again asks before replacing my edits.
  - Given a case study, when I choose Copy, then I get it as Markdown; on a phone it's a full-screen tab with Copy at the bottom.
- [x] S19 · Archive projects off the board
  As Shawn, I want to archive a project I've stopped or finished with so the board, the rail and Shipped show only live work.
  - Given any project, when I choose Archive in its side panel and confirm, then it leaves the board, the rail's project list and Shipped at once, and nothing in it is deleted.
  - Given archived projects, when I open the Archived group at the foot of Shipped, then each one shows its phase or version and when it was archived, with Restore.
  - Given an archived project, when I restore it, then it goes back where it was: the board in its phase, or Shipped if it had shipped.
  - Given a link to an archived project, when I open it, then it opens with a banner that says it's archived, with Restore.
