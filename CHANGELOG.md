# Changelog

Every release of The Studio, newest first.

## [2.0.0] - 2026-11-15
### Added
- Capture ideas the moment they come, with C on a laptop or a bottom sheet on a phone. Captures save straight to your Claude account.
- A projects board that shows what needs you first, a grid of projects across the five phases, and an inbox. Claude's drafts waiting for review come first, then anything waiting on a phone check.
- Claude scores every new capture against the six Discover rubric rows, with reasoning, tags and a working title. It gives a verdict of Promising, Park or Killed. You can edit the scores, override the verdict, and Promote, Keep or Discard each idea. One button scores older captures in batches.
- A Discover coach chat that interviews you one question at a time when your idea is vague, or when you ask. It then drafts a one-liner and an idea score for you to approve.
- Define and Design open on their documents: PRD, user stories and NFRs in Define, and Architecture and numbered decision records in Design. Documents are written in Markdown, save as you type, and are kept in your account.
- Draft with Claude writes any Define or Design document from your coach chat, your project facts and your saved documents, with TBD lines where something is missing. Nothing you saved changes until you choose to use the draft.
- Tracked-changes review for Claude's drafts of documents you've already saved. Accept or reject each change, undo any decision, accept all, or discard the draft. Each change comes with a short explanation.
- Mermaid diagrams in your documents are drawn as real diagrams, with a Source tab, Copy source, light and dark colours, and full-screen pinch-to-zoom on a phone.
- A Handoff page that gathers your saved documents into one prompt for Claude Code, with the project folder and branch included. The framework now sets the app up in the first Build slice (S0), inside the repo folder.
- A Build monitor that reads your repo in the Claude desktop app. It shows each slice with its status, last commit and date, plus the progress log. It also flags slices waiting on you, with Mark done. Your phone shows the last synced snapshot.
- A ready-to-paste Claude Code prompt for every slice that isn't done, with its story and acceptance criteria.
- A real Ship stage with a launch checklist, including a full security check. You can remove checks, restore the defaults or add your own.
- Feedback tracking: note what real users said, turn it into a backlog item with To backlog, and have the backlog feed the next version's planning.
- A changelog for each version, written from the work you did.
- A Case study for shipped projects in three versions: a portfolio page, a technical write-up, and a short summary for a CV or LinkedIn. Each can be copied as Markdown.
- Archive for projects. Archived projects leave the board without anything being deleted, and appear in a collapsed Archived group in Shipped. You can restore them to where they were.
- A light theme that follows your device's setting.
- Shortcuts: C, N, B, I, 1–9 and ?.
- Clear messages for first run, loading, offline, and saving in this browser only.

### Changed
- Published over the old Build Studio link. Your existing projects carry over.

### Fixed
- The mobile bottom bar no longer floats up on short pages.
- Slice rows on a phone now show their last commit and date, and open to list every commit that mentions the slice.
- Check notes and log entries are no longer cut off.
