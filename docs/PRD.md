# The Studio v2: PRD (snapshot, 2026-11-13)

Source of truth with full acceptance criteria, NFRs and screens: https://claude.ai/artifact/TaqRxcnyLvmWs7spbZiHby

**One-liner:** For a solo student builder juggling two or three projects, The Studio takes ideas from a passing thought to a shipped app. It runs each one through the five-phase framework with an AI coach that interviews you, drafts the documents and tracks progress, so ideas don't get lost in scattered chats and notes.

## Problem
- Ideas arrive at random times and get lost before they're evaluated.
- Planning stalls because scaffolding, requirements and architecture feel like one huge decision.
- AI help lives in scattered chats; nothing turns those conversations into durable project docs.
- v1 crammed everything onto one screen, looked generic and broke on mobile.

## User
Shawn: a software engineering student in Lagos building solo on a $0 budget with Claude Code. Uses phone and laptop equally; 2–3 projects in progress.

## Goals (v2)
1. Capture an idea in seconds from anywhere, and let AI triage it.
2. See every active project's phase, progress and next step at a glance.
3. Work each phase in the view that suits it.
4. The AI drafts every framework artifact; Shawn approves through tracked changes.
5. Hand finished docs to Claude Code in one step.

## Non-goals (v2)
Teams or sharing · command palette or terminal styling · running code inside The Studio · direct GitHub writes · cross-project analytics.

## Success metric
Shawn's next real project goes from capture to Ship entirely inside The Studio.

## Constraints
- $0: AI on the Claude plan via the artifact's ask-Claude capability; data in the artifact database.
- The page can't call outside sites; libraries only from approved CDNs.
- Every AI call carries its own context (memoryless).
- Storage: 256 KiB per document, 25,000 documents.
- Repo access only through the local file server in the Claude desktop app (ADR 0002).

## Must stories
S1 board · S2 quick capture · S3 AI triage and inbox · S4 Discover coach with auto-interview · S5 phase-appropriate views · S6 AI drafts · S7 tracked-changes approval · S8 checklists and progress · S10 Claude Code handoff · S16 Build monitor with progress sync. Status in docs/stories.md.

## Should
S9 rendered diagrams · S12 prompt per slice · S14 Ship checklist · S15 keyboard shortcuts.

## Open question
When a chat gets long, summarise the oldest messages automatically, or ask first?
