# 0003: Read commits from git's own files, and let The Studio mark slices done

Status: Accepted · 2026-11-13 · Amends 0002

## Context
0002 had Claude Code write each slice's commit hash into `docs/progress.md`, because the file server can't run git. In practice the hash only exists after the commit, so every slice needed a second commit just to record it (S0 did exactly that). Separately, the Build monitor design has a Mark done button, which needs one small write to `docs/stories.md`.

## Decision
- The Studio reads `.git/HEAD` for the branch and the last 80 lines of `.git/logs/HEAD` (the reflog) for recent commits. A slice's commit is the newest one whose message mentions its ID, as in `feat(S#): ...`. The `Commit:` line in progress entries becomes optional.
- The manifest for `host:filesystem` is `read_text_file` and `edit_file`. `edit_file` is used only for Mark done: it changes one line of `docs/stories.md` from `[~]` to `[x]`. The Claude app asks before each write.
- On the phone, Mark done is saved with the snapshot and written to the repo the next time Shawn presses Write it on the laptop.
- The Stop hook checks the latest `feat(S#)` commit has its progress entry and stories line, instead of checking for a hash.

## Consequences
- One commit per slice again. The protocol in CLAUDE.md says to commit code and docs together.
- The reflog is local: commits made on another machine and pulled show as one pull entry. Fine for one person on one laptop.
- Author emails in the reflog are never stored in The Studio's snapshot.
