# Browser tests

Each script opens `src/index.html` in Chromium with a fake database, a fake Claude and (for S16) a fake laptop file server, then clicks through a slice's main journeys. Nothing touches your real data or uses your Claude plan.

| Script | Slice | Checks |
| --- | --- | --- |
| `s3.py` | S3 · AI triage and inbox | 27 |
| `s4.py` | S4 · Discover coach with auto-interview | 84 |
| `s16.py` | S16 · Build monitor with progress sync | 26 |

## Run

```
pip install playwright
python -m playwright install chromium
python tests/s4.py
```

Each script prints its checks (or `FAIL` lines) and any page errors. Screenshots go to `tests/out/`, which git ignores. Set `CHROME` to a Chrome path to use your own browser instead of Playwright's.

The `fx_*` files are sample repo files that `s16.py` feeds to the fake file server.
