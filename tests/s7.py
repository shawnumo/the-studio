"""S7 browser test: tracked-changes review, with a mocked db and a mocked Claude (streaming drafts, JSON reasons)."""
import asyncio, json, os, time
from pathlib import Path
from playwright.async_api import async_playwright
HERE = Path(__file__).resolve().parent
URL = (HERE.parent / 'src' / 'index.html').as_uri()
OUT = str(HERE / 'out') + os.sep            # screenshots land in tests/out/
os.makedirs(OUT, exist_ok=True)
LAUNCH = {'executable_path': os.environ['CHROME']} if os.environ.get('CHROME') else {}   # optional: your own Chrome

BASE = """# Matchbook

For Saturday 5-a-side players.

## Problem
- Goals get disputed in WhatsApp
- Nobody keeps a season table

## Goals (v1)
1. Captains log goals live
2. Everyone sees the season table

## Constraints
| NFR | Requirement |
| --- | --- |
| Cost | $0 |
| Reach | Phones |

## Non-goals
- Player accounts
"""
DRAFT = """# Matchbook

For Saturday 5-a-side players, who argue over who scored.

## Problem
- Goals get disputed in WhatsApp

## Goals (v1)
1. Captains log goals and assists live
2. Everyone sees the season table
3. Both captains confirm the result

## Constraints
| NFR | Requirement |
| --- | --- |
| Cost | $0 on free tiers |
| Reach | Phones |

## Non-goals
- Player accounts

## Open questions
- TBD: who confirms when a captain is missing"""
KINDS = ['Reworded', 'Removed', 'Reworded', 'Added', 'Reworded', 'Added']
SECTIONS = ['Matchbook', 'Problem', 'Goals (v1)', 'Goals (v1)', 'Constraints', 'Open questions']
REASONS = [{'n': i + 1, 'why': w} for i, w in enumerate(['You said "they argue over who scored."', 'Not from the chat; check it.', 'You said assists count too.',
                                                         'You said "both captains confirm."', 'Fills a gap: the cost limit.', 'Fills a gap: an open question.'])]
ADR1 = "# 0001: Use Firebase\n\nStatus: Proposed · 2026-11-10\n\n## Context\n\nWe need auth and a database on a free tier.\n\n## Decision\n\nFirebase Spark plan.\n"
ADR1B = "# 0001: Use Firebase\n\nStatus: Accepted · 2026-11-13\n\n## Context\n\nWe need auth and a database on a free tier.\n\n## Decision\n\nFirebase Spark plan, with Firestore.\n"

MOCK = r"""
(() => {
  const FILES = %FILES%;
  const S0 = {}; const subs = []; const dsubs = [];
  const saved = localStorage.getItem('__mockdb');
  if (saved) Object.assign(S0, JSON.parse(saved));
  else {
    const now = Date.now(), seed = %SEED%;
    for (const [k, v] of Object.entries(seed)){ S0[k] = v; if (v.__ago !== undefined){ v.updatedAt = now - v.__ago; v.createdAt = now - v.__ago - 1000; delete v.__ago; } }
  }
  const inCol = col => Object.keys(S0).filter(k => k.split('/')[0] === col && k.split('/').length === 2).sort();
  const match = (d, f) => !f || (f[1] === '==' && d[f[0]] === f[2]);
  const snapQ = (col, f) => { const docs = inCol(col).filter(k => match(S0[k], f)).map(k => ({id:k.split('/')[1], exists:true, data:()=>S0[k]})); return {docs, size:docs.length, empty:!docs.length, metadata:{fromCache:false, hasPendingWrites:false}}; };
  const snapD = k => ({id:k.split('/')[1], exists:k in S0, data:()=>S0[k], metadata:{fromCache:false, hasPendingWrites:false}});
  const notify = k => { const col = k.split('/')[0]; subs.filter(s => s.col === col).forEach(s => s.cb(snapQ(col, s.f))); dsubs.filter(s => s.k === k).forEach(s => s.cb(snapD(k))); };
  const persist = () => localStorage.setItem('__mockdb', JSON.stringify(S0));
  const query = (col, f) => ({
    where(a, op, v){ window.__wheres.push([col, a, op, v]); return query(col, [a, op, v]); },
    onSnapshot(cb, err){
      if (col === 'docs' && window.__docsFail){ setTimeout(() => err && err({code:'invalid_argument', message:'mock'}), 30); return () => {}; }
      if (col === 'docs' && window.__docsHang) return () => {};
      subs.push({col, f, cb}); setTimeout(() => cb(snapQ(col, f)), 30); return () => {};
    },
    async get(){ return snapQ(col, f); }
  });
  const db = { collection(col){ return Object.assign(query(col, null), {
    doc(id){ const k = col + '/' + id; return {
      async set(d){ window.__writes.push(k); S0[k] = JSON.parse(JSON.stringify(d)); persist(); setTimeout(()=>notify(k), 20); },
      async get(){ return snapD(k); },
      onSnapshot(cb, err){ dsubs.push({k, cb}); setTimeout(() => cb(snapD(k)), 40); return () => {}; },
      async delete(){ window.__dels.push(k); delete S0[k]; persist(); setTimeout(()=>notify(k), 20); } }; }
  }); } };
  window.__store = S0; window.__calls = []; window.__writes = []; window.__dels = []; window.__wheres = []; window.__replies = []; window.__seen = []; window.__mode = 'ok';
  window.__remote = (k, d) => { S0[k] = d; persist(); notify(k); };   // a write from another device
  const sample = (input, opts) => new Promise((resolve, reject) => {
    window.__calls.push({input: JSON.parse(JSON.stringify(input)), opts: {modelTier: opts.modelTier, cache: opts.cache}});
    if (window.__mode !== 'ok'){ const code = window.__mode; window.__mode = 'ok'; setTimeout(() => reject({code, message:'mock'}), 30); return; }
    const full = window.__replies.length ? window.__replies.shift() : 'Okay.\n<studio>{"mode":"chat"}</studio>';
    let i = 0; const step = window.__step || 20, tick = window.__tick || 6;
    opts.onText && opts.onText({text:'Thinking...', delta:''});
    const t = setInterval(() => {
      i = Math.min(full.length, i + step);
      opts.onText && opts.onText({text: full.slice(0, i), delta: ''});
      const live = document.querySelector('#draft-live'); if (live) window.__seen.push(live.innerText);
      if (i >= full.length){ clearInterval(t); resolve({text: full, truncated: !!window.__cut}); }
    }, tick);
    if (opts.signal) opts.signal.addEventListener('abort', () => { clearInterval(t); reject({code:'aborted', text: full.slice(0, i)}); });
  });
  sample.json = (input, opts) => {
    window.__calls.push({input, opts:{modelTier:opts && opts.modelTier, cache:opts && opts.cache}, json:true});
    if (window.__jsonMode !== 'ok'){ const code = window.__jsonMode; window.__jsonMode = 'ok'; return new Promise((_, rej) => setTimeout(() => rej({code, message:'mock'}), 30)); }
    const v = window.__jsonReplies.length ? window.__jsonReplies.shift() : [];
    return new Promise(r => setTimeout(() => r(v), window.__jsonDelay || 40));
  };
  window.__jsonReplies = []; window.__jsonMode = 'ok';
  window.__host = %HOST%; window.__delay = 0; window.__mcpCalls = [];
  const mcp = {
    async listTools(server){ return {servers: window.__host === 'listed' ? [{server:'host:filesystem', tools:[{name:'read_text_file'},{name:'edit_file'}]}] : []}; },
    async callTool(server, tool, input){
      window.__mcpCalls.push({tool, input});
      if (window.__host !== 'listed') throw {code:'server_not_connected', message:'no host'};
      if (window.__delay){ const d = window.__delay; window.__delay = 0; await new Promise(r => setTimeout(r, d)); }
      const text = FILES[input.path];
      if (text === undefined) throw {code:'tool_error', message:"ENOENT: no such file or directory, open '" + input.path + "'"};
      return {content:[{type:'text', text}], payload:{content:text}};
    },
    watchTool(){ return () => {}; }, async invalidate(){}
  };
  window.claude = { use: async n => n === 'db' ? (window.__noDb ? null : db) : n === 'sample' ? (window.__noSample ? null : sample) : n === 'mcp' ? mcp : null };
})();
"""

DN = {"users": "Captains and 12 players", "scope": "Log goals and assists live", "nongoals": "Player accounts", "musts": "", "nfrs": "", "open": ""}
CHAT = {'messages': [
    {'id': 'm1', 'role': 'user', 'text': 'Interview me about what v1 should do.', 'at': 1},
    {'id': 'm2', 'role': 'coach', 'text': 'Who confirms a result?', 'at': 2, 'meta': {'mode': 'interview', 'reason': '', 'q': {'n': 1, 'of': 2, 'text': 'Who confirms a match result?'}, 'choices': [], 'done': False, 'oneliner': '', 'scores': None}},
    {'id': 'm3', 'role': 'user', 'text': 'Both captains confirm. Assists count too.', 'at': 3}],
    'notes': DN, 'free': False, 'trimmed': 0, 'updatedAt': 4}
SEED = {
    'projects/pd': {'name': 'Matchbook', 'phase': 'define', 'completed': {'discover': True}, 'checks': {'define': [False, False, False, False]}, 'oneLiner': 'For Saturday 5-a-side players.', '__ago': 3600000},
    'chats/pd~define': CHAT,
    'docs/pd~prd': {'pid': 'pd', 'phase': 'define', 'key': 'prd', 'text': BASE, '__ago': 7200000},
    'projects/pg': {'name': 'Hall registration', 'phase': 'design', 'completed': {'discover': True, 'define': True}, 'checks': {'design': [False, False, False]}, 'oneLiner': '', '__ago': 7200000},
    'docs/pg~adr-a1': {'pid': 'pg', 'phase': 'design', 'key': 'adr-a1', 'kind': 'adr', 'n': 1, 'text': ADR1, '__ago': 86400000},
    # a project whose PRD already has a draft waiting for review (for the phone checks)
    'projects/pr': {'name': 'Review me', 'phase': 'define', 'completed': {'discover': True}, 'checks': {}, 'oneLiner': '', '__ago': 3600000},
    'docs/pr~prd': {'pid': 'pr', 'phase': 'define', 'key': 'prd', 'text': BASE, 'draft': {'text': DRAFT, 'at': int(time.time() * 1000) - 600000, 'basedOn': 1, 'cut': False, 'base': BASE, 'decisions': {}}, '__ago': 7200000},
}
FILES = {}


def mock(host='none'):
    return MOCK.replace('%FILES%', json.dumps(FILES)).replace('%SEED%', json.dumps(SEED)).replace('%HOST%', json.dumps(host))


async def store(pg, k):
    return await pg.evaluate(f'window.__store[{json.dumps(k)}]')


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(**LAUNCH)
        errs, checks = [], []

        def ok(name, cond):
            checks.append((name, bool(cond)))
            print(('PASS ' if cond else 'FAIL ') + name)

        ctx = await b.new_context(viewport={'width': 1440, 'height': 900}, color_scheme='dark')
        d = await ctx.new_page(); d.on('pageerror', lambda e: errs.append('desk: ' + str(e)))
        await d.add_init_script(mock())
        await d.goto(URL + '#p-pd'); await d.wait_for_selector('.doc h1', timeout=8000); await d.wait_for_timeout(250)

        # 1. A draft of a saved document opens as tracked changes
        await d.evaluate(f'window.__replies.push({json.dumps(DRAFT)}); window.__jsonReplies.push({json.dumps(REASONS)})')
        await d.click('.dtools [data-act="draftdoc"]')
        await d.wait_for_selector('.rbar', timeout=8000); await d.wait_for_timeout(300)
        bar = await d.inner_text('.rbar')
        ok('review: six changes, none decided, saved PRD untouched', "Claude's draft: 6 changes" in bar and '0 accepted · 0 rejected · 6 left' in bar and 'changes only as you accept' in bar
           and (await store(d, 'docs/pd~prd'))['text'] == BASE)
        ok('review: TBD lines counted', 'The draft has 1 TBD line' in bar)
        kinds = await d.eval_on_selector_all('.doc.review .chg .kind', 'els => els.map(e => e.innerText)')
        secs = await d.eval_on_selector_all('.doc.review .chg .chm', 'els => els.map(e => (e.innerText.split("in ")[1] || "").trim())')
        ok('changes: a line or paragraph each, with kind and section', kinds == KINDS and secs == SECTIONS)
        ok('reworded line: added words highlighted inside it', 'who argue over who scored' in await d.inner_text('#chg-0 ins') and await d.locator('#chg-0 .dl').count() == 0)
        ok('removed line struck through', 'Nobody keeps a season table' in await d.inner_text('#chg-1 .dl'))
        ok('changed table row shown both ways; the table after it keeps its columns', '$0 on free tiers' in await d.inner_text('#chg-4 .il') and '$0' in await d.inner_text('#chg-4 .dl')
           and 'Reach' in await d.inner_text('.doc.review .nohead table tbody'))
        ok('unchanged text still rendered around the changes', await d.locator('.doc.review > h2').count() >= 3 and 'Player accounts' in await d.inner_text('.doc.review'))
        stabs = await d.eval_on_selector_all('.stabs button', 'els => els.map(e => [e.innerText.split(/\\s+/).join(" "), e.getAttribute("aria-selected")])')
        ok('side panel: Changes tab first and open', stabs[0] == ['Changes 6', 'true'] and len(stabs) == 3 and await d.locator('.sidechanges .crow').count() == 6)
        ok('tab and toolbar', '6 changes' in ' '.join((await d.inner_text('.doctabs [data-tab="prd"]')).split()) and 'Change 1 of 6' in ' '.join((await d.inner_text('.rnav')).split())
           and await d.locator('.chg.cur').count() == 1 and await d.get_attribute('.chg.cur', 'id') == 'chg-0')
        await d.wait_for_selector('#chg-0 .why', timeout=4000)
        jc = [c for c in await d.evaluate('window.__calls') if c.get('json')][-1]
        ok('reasons: one quick call with the changes and the chat', jc['opts'] == {'modelTier': 'quick', 'cache': False} and '"n":6' in jc['input'] and 'Assists count too' in jc['input'] and 'Reply with only a JSON array' in jc['input'])
        ok('reasons: shown under each change', 'they argue over who scored' in await d.inner_text('#chg-0 .why') and 'check it' in await d.inner_text('#chg-1 .why')
           and (await store(d, 'docs/pd~prd'))['draft']['reasons'])
        ok('desktop: no sideways scroll', await d.evaluate('document.documentElement.scrollWidth <= innerWidth'))
        await d.screenshot(path=OUT + 's7-review-desk.png')

        # 2. Keys: accept, reject, move, undo
        await d.evaluate('document.activeElement && document.activeElement.blur()')
        await d.keyboard.press('a'); await d.wait_for_timeout(800)
        t = (await store(d, 'docs/pd~prd'))['text']
        ok('A accepts: saved at once, only that change', 'players, who argue over who scored.' in t and 'Nobody keeps a season table' in t and 'Captains log goals live' in t)
        ok('A moves to the next change', await d.get_attribute('.chg.cur', 'id') == 'chg-1' and 'Change 2 of 6' in ' '.join((await d.inner_text('.rnav')).split()) and 'Accepted' in await d.inner_text('#chg-0 .dec'))
        await d.keyboard.press('r'); await d.wait_for_timeout(700)
        ok('R rejects: the saved text keeps the line', 'Nobody keeps a season table' in (await store(d, 'docs/pd~prd'))['text'] and 'Rejected' in await d.inner_text('#chg-1 .dec')
           and await d.get_attribute('.chg.cur', 'id') == 'chg-2')
        await d.keyboard.press('j'); await d.keyboard.press('k'); await d.keyboard.press('k'); await d.wait_for_timeout(100)
        ok('J and K move through the changes', await d.get_attribute('.chg.cur', 'id') == 'chg-1')
        await d.keyboard.press('u'); await d.wait_for_timeout(700)
        ok('U undoes a decision', await d.locator('#chg-1 [data-act="accept"]').count() == 1 and 'Rejected' not in await d.inner_text('#chg-1'))
        ok('counts follow', '1 accepted · 0 rejected · 5 left' in await d.inner_text('.rbar') and 'Changes 5' in ' '.join((await d.inner_text('.stabs')).split()))

        # 3. The list in the side panel: tick and cross on each change
        await d.click('.sidechanges .crow:nth-child(4) [data-act="accept"]'); await d.wait_for_timeout(700)
        ok('side list: tick accepts that change', '3. Both captains confirm the result' in (await store(d, 'docs/pd~prd'))['text'] and 'Accepted' in await d.inner_text('.sidechanges .crow:nth-child(4)'))
        await d.click('.sidechanges .crow:nth-child(5) [data-act="reject"]'); await d.wait_for_timeout(300)
        ok('side list: cross rejects it', 'Rejected' in await d.inner_text('.sidechanges .crow:nth-child(5)') and '| Cost | $0 |' in (await store(d, 'docs/pd~prd'))['text'])
        await d.click('.sidechanges .crow:nth-child(3) .cgo'); await d.wait_for_timeout(150)
        ok('side list: a row jumps to its change', await d.get_attribute('.chg.cur', 'id') == 'chg-2' and 'cur' in (await d.get_attribute('.sidechanges .crow:nth-child(3)', 'class')))
        await d.click('#chg-0 [data-act="undochange"]'); await d.wait_for_timeout(700)
        ok('undo an accepted change: the saved text goes back exactly', 'For Saturday 5-a-side players.\n' in (await store(d, 'docs/pd~prd'))['text'] and '3. Both captains' in (await store(d, 'docs/pd~prd'))['text'])

        # 4. Only the changes, then back
        await d.click('.rbar [data-act="ronly"]'); await d.wait_for_timeout(100)
        ok('only the changes: a line of context, gaps marked', await d.locator('.doc.review.only .chg').count() == 6 and await d.locator('.doc.review.only .gap').count() >= 1 and await d.locator('.doc.review.only > h2').count() == 0)
        await d.click('.rbar [data-act="ronly"]')

        # 5. Accept all, then finish
        await d.click('.rbar [data-act="acceptall"]'); await d.wait_for_timeout(700)
        t = (await store(d, 'docs/pd~prd'))['text']
        ok('Accept all: every undecided change applied, rejected one kept', 'who argue over who scored' in t and 'Nobody keeps' not in t and '| Cost | $0 |' in t and 'Open questions' in t)
        ok('all decided: Finish review, undo still possible', 'All 6 decided: 5 accepted, 1 rejected' in await d.inner_text('.rbar') and await d.is_visible('.rbar .btn.primary[data-act="finishreview"]') and await d.locator('.doc.review [data-act="undochange"]').count() == 6)
        await d.click('.rbar [data-act="finishreview"]'); await d.wait_for_timeout(700)
        st = await store(d, 'docs/pd~prd')
        ok('finished: draft gone, text kept, noted', 'draft' not in st and st['text'] == t and "Reviewed Claude's draft just now: 5 of 6 changes accepted" in await d.inner_text('.dmeta')
           and await d.query_selector('.sidechanges') is None and (await d.get_attribute('.stabs [data-tab="coach"]', 'aria-selected')) == 'true')

        # 6. A change on another device mid-review: the review follows the saved text; Discard keeps it
        await d.evaluate(f'window.__replies.push({json.dumps(DRAFT)}); window.__jsonMode = "rate_limited"')
        await d.click('.dtools [data-act="draftdoc"]'); await d.wait_for_selector('.rbar', timeout=8000); await d.wait_for_timeout(300)
        ok('reasons failing: said so, with Try again', "Claude's reasons couldn't be loaded" in await d.inner_text('.rbar'))
        await d.evaluate(f'window.__jsonReplies.push({json.dumps(REASONS[:2])})')
        await d.click('.rbar [data-act="askwhy"]'); await d.wait_for_timeout(400)
        ok('Try again gets them', await d.locator('.doc.review .why').count() >= 1)
        cur = await store(d, 'docs/pd~prd')
        await d.evaluate("window.__remote('docs/pd~prd', Object.assign({}, window.__store['docs/pd~prd'], {text: window.__store['docs/pd~prd'].text + '\\nA line from my phone.', updatedAt: Date.now() + 5000, editedAt: Date.now() + 5000}))")
        await d.wait_for_timeout(400)
        ok('saved text changed elsewhere: changes shown against it', 'You edited the saved version after Claude drafted this' in await d.inner_text('.rbar'))
        await d.click('.rbar [data-act="rejectrest"]'); await d.wait_for_timeout(700)
        st = await store(d, 'docs/pd~prd')
        ok('Discard the draft: saved text as it was', 'draft' not in st and st['text'].endswith('A line from my phone.') and 'Draft discarded' in await d.inner_text('.toast'))

        # 7. An ADR
        await d.goto(URL + '#p-pg'); await d.wait_for_selector('.doctabs', timeout=8000)
        await d.click('.doctabs [data-tab="adr"]'); await d.click('.adrlist li:first-child button')
        await d.evaluate(f'window.__replies.push({json.dumps(ADR1B)}); window.__jsonReplies.push([])')
        await d.click('.dtools [data-act="draftdoc"]'); await d.wait_for_selector('.rbar', timeout=8000); await d.wait_for_timeout(200)
        ok('ADR: reviewed the same way', "Claude's draft: 2 changes" in await d.inner_text('.rbar') and 'review' in await d.inner_text('.doctabs [data-tab="adr"]'))
        await d.click('.rbar [data-act="acceptall"]'); await d.click('.rbar [data-act="finishreview"]'); await d.wait_for_timeout(600)
        ok('ADR: accepted text saved', (await store(d, 'docs/pg~adr-a1'))['text'].strip() == ADR1B.strip())
        await d.click('[data-act="closeadr"]')
        ok('ADR list shows the new status', 'Accepted' in await d.inner_text('.adrlist li:first-child'))
        await ctx.close()

        # 8. 1024 wide
        cx = await b.new_context(viewport={'width': 1024, 'height': 768})
        k = await cx.new_page(); k.on('pageerror', lambda e: errs.append('1024: ' + str(e)))
        await k.add_init_script(mock())
        await k.goto(URL + '#p-pr'); await k.wait_for_selector('.rbar', timeout=8000); await k.wait_for_timeout(200)
        ok('1024: review fits, no sideways scroll', await k.evaluate('document.documentElement.scrollWidth <= innerWidth') and await k.is_visible('.rnav [data-act="accept"]'))
        await k.screenshot(path=OUT + 's7-review-1024.png')
        await cx.close()

        # 9. Phones: the whole list of changes, each with its own tick and cross
        for (wd, ht, scheme) in [(390, 844, 'dark'), (360, 800, 'light')]:
            tag = f'{wd}'
            mc = await b.new_context(viewport={'width': wd, 'height': ht}, color_scheme=scheme, has_touch=True, is_mobile=True)
            m = await mc.new_page(); m.on('pageerror', lambda e, t=tag: errs.append(t + ': ' + str(e)))
            await m.add_init_script(mock())
            await m.goto(URL + '#p-pr'); await m.wait_for_selector('.rbar', timeout=8000); await m.wait_for_timeout(250)
            ok(f'{tag}: every change listed at once, with context', await m.locator('.doc.review.only .chg').count() == 6 and await m.locator('.doc.review .ctx').count() >= 4)
            hs = await m.eval_on_selector_all('.chg .chbtns .btn', 'els => els.map(e => e.getBoundingClientRect().height)')
            ok(f'{tag}: a tick and a cross on each, 44px or more', len(hs) == 12 and min(hs) >= 44)
            ok(f'{tag}: no desktop toolbar, no sideways scroll', await m.is_hidden('.rnav') and await m.evaluate('document.documentElement.scrollWidth <= innerWidth'))
            await m.screenshot(path=OUT + f's7-review-{tag}-{scheme}.png', full_page=True)
            await m.tap('#chg-2 [data-act="accept"]'); await m.wait_for_timeout(700)
            ok(f'{tag}: tick accepts that one, others stay', 'Captains log goals and assists live' in (await store(m, 'docs/pr~prd'))['text'] and await m.locator('.chg [data-act="accept"]').count() == 5)
            ub = await m.eval_on_selector_all('#chg-2 [data-act="undochange"]', 'els => els.map(e => e.getBoundingClientRect().height)')
            ok(f'{tag}: Undo is big enough to tap', ub and ub[0] >= 44)
            await m.tap('.rbar [data-act="ronly"]'); await m.wait_for_timeout(150)
            ok(f'{tag}: whole document view keeps the ticks and crosses', await m.locator('.doc.review:not(.only) .chg [data-act="accept"]').count() == 5 and await m.evaluate('document.documentElement.scrollWidth <= innerWidth'))
            await mc.close()

        await b.close()
        passed = sum(1 for _, c in checks if c)
        print(f'{passed}/{len(checks)} passed')
        for nm, c in checks:
            if not c: print('  FAILED:', nm)
        print('page errors:', errs or 'none')

asyncio.run(main())
