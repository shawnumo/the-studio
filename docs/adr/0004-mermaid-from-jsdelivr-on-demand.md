# 0004: Draw diagrams with Mermaid from jsDelivr, loaded only when needed

Status: Accepted · 2026-11-13

## Context
S9 draws the Mermaid blocks in documents: context diagrams, ERDs and state machines. The page can't call outside sites, but the artifact's content security policy lets it load scripts from a few CDNs, and the PRD names jsDelivr for Mermaid. Mermaid is large, and Shawn often uses The Studio on mobile data.

## Decision
- Use Mermaid 12.3.0, pinned, from `https://cdn.jsdelivr.net/npm/mermaid@12.3.0/dist/mermaid.esm.min.mjs` (the modular build).
- Load it with `import()` only when a document on screen has a ```` ```mermaid ```` block. The board and documents without diagrams never load it.
- Run it in strict mode, so text in a diagram can't run scripts. Take its colours from the theme's CSS tokens, and draw each source once per theme.
- If it can't load, show the source with the reason and Try again. A retry asks for a fresh URL, because the browser remembers a failed import.

## Alternatives considered
- The single-file build (`mermaid.min.js`): 1.6 MB compressed, against about 0.75 MB for a flowchart with the modular build (measured on 13 Nov).
- cdnjs: allowed too, but the PRD names jsDelivr.
- Diagrams drawn by Claude, or kept as images in the repo: a Claude call every time, or no longer editable as text.

## Consequences
- The first diagram on a device downloads about 0.75 MB; after that the browser's cache serves it.
- Diagrams need a connection the first time. Offline, the source shows instead.
- Upgrading Mermaid means changing the pinned version in `src/index.html` and re-running `tests/s9.py`.
- `tests/s9.py` needs Mermaid: from jsDelivr, or from a local copy of the npm package (`MERMAID_DIR`).
