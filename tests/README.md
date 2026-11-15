# Browser tests

Each script opens `src/index.html` in Chromium with a fake database, a fake Claude and (for S5, S12, S14 and S16) a fake laptop file server, then clicks through a slice's main journeys. Nothing touches your real data or uses your Claude plan.

| Script | Slice | Checks |
| --- | --- | --- |
| `s1.py` | S1 · Projects board: drafts to review and last Claude Code session | 52 |
| `s3.py` | S3 · AI triage and inbox | 27 |
| `s4.py` | S4 · Discover coach with auto-interview | 85 |
| `s5.py` | S5 · Phase-appropriate views | 94 |
| `s6.py` | S6 · AI drafts | 49 |
| `s7.py` | S7 · Tracked-changes approval | 46 |
| `s9.py` | S9 · Rendered Mermaid diagrams | 37 |
| `s10.py` | S10 · Claude Code handoff | 58 |
| `s12.py` | S12 · Claude Code prompt per slice | 82 |
| `s14.py` | S14 · Ship checklist, feedback and changelog | 107 |
| `s16.py` | S16 · Build monitor with progress sync | 26 |
| `s18.py` | S18 · Case study from a shipped project | 95 |
| `s19.py` | S19 · Archive projects off the board | 49 |

## Run

```
pip install playwright
python -m playwright install chromium
python tests/s4.py
```

Each script prints its checks (or `FAIL` lines) and any page errors. Screenshots go to `tests/out/`, which git ignores. Set `CHROME` to a Chrome path to use your own browser instead of Playwright's.

`s9.py` uses the real Mermaid, loaded from jsDelivr. To run it without a connection, unpack the same package (`npm pack mermaid@12.3.0`, then `tar -xzf mermaid-12.3.0.tgz`) and set `MERMAID_DIR` to its `package` folder.

The `fx_*` files are sample repo files that `s16.py` feeds to the fake file server.
