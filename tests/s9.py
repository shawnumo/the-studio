"""S9 browser test: Mermaid diagrams in documents, with a mocked db, a mocked streaming Claude and a stubbed clipboard.
Mermaid itself is real. It loads from jsDelivr, or from a local copy of the same package when MERMAID_DIR points at it
(an unpacked mermaid-12.3.0 npm package: npm pack mermaid@12.3.0, then tar -xzf; MERMAID_DIR is its "package" folder)."""
import asyncio, json, os, re, time
from pathlib import Path
from playwright.async_api import async_playwright
HERE = Path(__file__).resolve().parent
URL = (HERE.parent / 'src' / 'index.html').as_uri()
OUT = str(HERE / 'out') + os.sep            # screenshots land in tests/out/
os.makedirs(OUT, exist_ok=True)
LAUNCH = {'executable_path': os.environ['CHROME']} if os.environ.get('CHROME') else {}   # optional: your own Chrome
CDN = 'https://cdn.jsdelivr.net/npm/mermaid@12.3.0/'
ENTRY = CDN + 'dist/mermaid.esm.min.mjs'
LOCAL = Path(os.environ['MERMAID_DIR']) if os.environ.get('MERMAID_DIR') else None

NOW = int(time.time() * 1000)
DAY = 86400000
FLOW = "flowchart LR\n  S[Student] --> A[Hall app]\n  P[Porter] --> A\n  A --> F[(Firebase)]"
ERD = "erDiagram\n  ROOM ||--o{ STUDENT : holds\n  STUDENT ||--o{ CHECKIN : makes"
STATE = "stateDiagram-v2\n  [*] --> Booked\n  Booked --> CheckedIn\n  CheckedIn --> [*]"
BROKEN = "flowchart LR\n  A --> B -->"
FIXED = "flowchart LR\n  A --> B --> C"
ARCH = f"# Architecture\n\n## Context diagram\n\n```mermaid\n{FLOW}\n```\n\n## Data\n\n```mermaid\n{ERD}\n```\n\n## Check-in\n\n```mermaid\n{STATE}\n```\n"
ADR = f"# 0001: Use Firebase\n\nStatus: Proposed\n\n## Context\n\n```mermaid\n{BROKEN}\n```\n"
RV_BASE = f"# Architecture\n\nTier 1.\n\n```mermaid\n{FLOW}\n```\n\n## Data\n\n```mermaid\n{ERD}\n```\n"
RV_DRAFT = f"# Architecture\n\nTier 1, a static page.\n\n```mermaid\n{FLOW}\n```\n\n## Data\n\n```mermaid\nerDiagram\n  ROOM ||--o{{ STUDENT : holds\n```\n"
ARCH_DRAFT = f"# Architecture\n\nTier 1: one static page.\n\n## Context diagram\n\n```mermaid\n{FLOW}\n```\n\n## Hosting and cost\n- Cloudflare Pages\n"

def doc(pid, key, text, phase='design', **kw):
    return {'pid': pid, 'phase': phase, 'key': key, 'text': text, '__ago': DAY, **kw}

SEED = {
    'projects/pd': {'name': 'Hall registration', 'phase': 'design', 'completed': {'discover': True, 'define': True}, 'checks': {}, '__ago': 3600000},
    'docs/pd~prd': doc('pd', 'prd', "# Hall registration\n\nNo diagrams here.\n", 'define'),
    'docs/pd~architecture': doc('pd', 'architecture', ARCH),
    'docs/pd~adr-a1': doc('pd', 'adr-a1', ADR, kind='adr', n=1),
    'projects/pr': {'name': 'Review me', 'phase': 'design', 'completed': {'discover': True, 'define': True}, 'checks': {}, '__ago': DAY},
    'docs/pr~architecture': doc('pr', 'architecture', RV_BASE, draft={'text': RV_DRAFT, 'at': NOW - 600000, 'basedOn': 1, 'cut': False, 'base': RV_BASE, 'decisions': {}}),
    'projects/pn': {'name': 'New one', 'phase': 'design', 'completed': {'discover': True, 'define': True}, 'checks': {}, '__ago': 2 * DAY},
}

MOCK = r"""
(() => {
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
    where(a, op, v){ return query(col, [a, op, v]); },
    onSnapshot(cb, err){ subs.push({col, f, cb}); setTimeout(() => cb(snapQ(col, f)), 30); return () => {}; },
    async get(){ return snapQ(col, f); }
  });
  const db = { collection(col){ return Object.assign(query(col, null), {
    doc(id){ const k = col + '/' + id; return {
      async set(d){ S0[k] = JSON.parse(JSON.stringify(d)); persist(); setTimeout(()=>notify(k), 20); },
      async get(){ return snapD(k); },
      onSnapshot(cb, err){ dsubs.push({k, cb}); setTimeout(() => cb(snapD(k)), 40); return () => {}; },
      async delete(){ delete S0[k]; persist(); setTimeout(()=>notify(k), 20); } }; }
  }); } };
  window.__store = S0; window.__replies = []; window.__clip = null;
  Object.defineProperty(navigator, 'clipboard', {configurable:true, value:{writeText: async t => { window.__clip = t; }}});
  const sample = (input, opts) => new Promise((resolve, reject) => {
    const full = window.__replies.length ? window.__replies.shift() : 'Okay.';
    let i = 0; const step = window.__step || 20, tick = window.__tick || 6;
    opts.onText && opts.onText({text:'Thinking...', delta:''});
    const t = setInterval(() => {
      i = Math.min(full.length, i + step);
      opts.onText && opts.onText({text: full.slice(0, i), delta: ''});
      if (i >= full.length){ clearInterval(t); resolve({text: full, truncated: false}); }
    }, tick);
    if (opts.signal) opts.signal.addEventListener('abort', () => { clearInterval(t); reject({code:'aborted'}); });
  });
  sample.json = () => new Promise(r => setTimeout(() => r([]), 40));
  const mcp = { async listTools(){ return {servers:[]}; }, async callTool(){ throw {code:'server_not_connected'}; }, watchTool(){ return () => {}; }, async invalidate(){} };
  window.claude = { use: async n => n === 'db' ? db : n === 'sample' ? sample : n === 'mcp' ? mcp : null };
})();
"""


def mock():
    return MOCK.replace('%SEED%', json.dumps(SEED))


async def serve_mermaid(page, state):
    """Route jsDelivr: count requests; serve the local copy when MERMAID_DIR is set; refuse while state['down'] is True."""
    async def route(r):
        state['reqs'].append(r.request.url)
        if state.get('down'): return await r.abort()
        if not LOCAL: return await r.continue_()
        f = LOCAL / r.request.url[len(CDN):].split('?')[0]
        if not f.is_file(): return await r.fulfill(status=404, body='')
        await r.fulfill(status=200, body=f.read_bytes(), headers={'content-type': 'text/javascript', 'access-control-allow-origin': '*'})
    await page.route(CDN + '**', route)


async def figs(pg):
    return await pg.eval_on_selector_all('.dgm', '''fs => fs.map(f => ({svg: !!f.querySelector('.dgpic svg'), err: !!f.querySelector('.errbox'), load: !!f.querySelector('.dgload'),
        tab: (f.querySelector('.dgtabs [aria-selected="true"]') || {}).innerText, src: (f.querySelector('pre.dgsrc code') || {}).innerText}))''')


async def wait_svgs(pg, n, timeout=30000):
    await pg.wait_for_function(f'document.querySelectorAll(".dgm .dgpic svg").length >= {n}', timeout=timeout)


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(**LAUNCH)
        errs, checks = [], []

        def ok(name, cond):
            checks.append((name, bool(cond)))
            print(('PASS ' if cond else 'FAIL ') + name)

        ctx = await b.new_context(viewport={'width': 1440, 'height': 900}, color_scheme='dark')
        d = await ctx.new_page(); d.on('pageerror', lambda e: errs.append('desk: ' + str(e)))
        st = {'reqs': []}; await serve_mermaid(d, st)
        await d.add_init_script(mock())

        # 1. Mermaid loads only when a document on screen has a diagram
        await d.goto(URL + '#board'); await d.wait_for_selector('.needs li', timeout=8000); await d.wait_for_timeout(500)
        await d.evaluate('location.hash = "#p-pd-define"'); await d.wait_for_selector('.doc h1', timeout=8000); await d.wait_for_timeout(500)
        ok('board and a document without diagrams: Mermaid not loaded', st['reqs'] == [])
        await d.evaluate('location.hash = "#p-pd-design"'); await d.wait_for_selector('.dgm', timeout=8000)
        ok('loading: shapes while Mermaid loads', await d.locator('.dgm .dgload[aria-busy="true"]').count() >= 1)
        await wait_svgs(d, 3)
        f = await figs(d)
        ok('three diagrams drawn: flowchart, ERD, state', len(f) == 3 and all(x['svg'] and x['tab'] == 'Diagram' for x in f))
        ok('pinned version, modular build only, from jsDelivr', st['reqs'][0] == ENTRY and all(u.startswith(CDN + 'dist/') for u in st['reqs']) and not any(u.endswith('/mermaid.min.js') for u in st['reqs']))
        th = await d.evaluate('''() => { const r = document.querySelector('.dgm .node rect, .dgm .node path, .dgm .node polygon'), t = document.querySelector('.dgm .nodeLabel, .dgm .node text, .dgm text');
            const cs = getComputedStyle(document.documentElement); return [getComputedStyle(r).fill, cs.getPropertyValue('--raised').trim(), getComputedStyle(r).stroke, getComputedStyle(t).fontFamily]; }''')
        ok('theme: boxes in the raised tone, grey outlines, Schibsted Grotesk', th[0] == 'rgb(27, 30, 34)' and th[1] == '#1B1E22' and th[2] in ('rgb(74, 80, 89)',) and 'Schibsted' in th[3])
        ok('no stray Mermaid elements left on the page', await d.evaluate('[...document.querySelectorAll("[id^=dg], [id^=ddg]")].every(e => e.closest(".dgm, .dgfull"))'))
        ok('diagram fits the document width', await d.evaluate('[...document.querySelectorAll(".dgm")].every(f => f.querySelector("svg").getBoundingClientRect().width <= f.getBoundingClientRect().width + 1)'))
        await d.screenshot(path=OUT + 's9-diagrams-1440-dark.png')

        # 2. Source and Copy
        drawn = await d.evaluate('S.dgN')
        await d.click('.dgm >> nth=0 >> [data-act="dgview"][data-v="src"]'); await d.wait_for_timeout(150)
        f = await figs(d)
        ok('Source tab: the exact Mermaid source', f[0]['tab'] == 'Source' and f[0]['src'] == FLOW and not f[0]['svg'] and f[1]['svg'])
        ok('keyboard focus stays on the tab', await d.evaluate('document.activeElement.dataset.v') == 'src')
        await d.click('.dgm >> nth=0 >> [data-act="dgcopy"]'); await d.wait_for_timeout(200)
        ok('Copy source: the source, and a toast', await d.evaluate('window.__clip') == FLOW and 'Diagram source copied.' in await d.inner_text('.toast'))
        await d.keyboard.press('Shift+Tab'); await d.keyboard.press('Shift+Tab'); await d.keyboard.press('Enter'); await d.wait_for_timeout(150)
        ok('keyboard: back to Diagram, drawn from memory (no redraw)', (await figs(d))[0]['svg'] and await d.evaluate('S.dgN') == drawn)
        await d.click('.dgm .dgpic >> nth=0'); await d.wait_for_timeout(150)
        ok('desktop: clicking a diagram opens nothing', await d.locator('.dgfull').count() == 0)

        # 3. Invalid Mermaid, then fixed
        await d.click('.doctabs [data-tab="adr"]'); await d.wait_for_timeout(200); await d.click('.adrlist [data-act="openadr"]')
        await d.wait_for_selector('.dgm .errbox', timeout=20000)
        f = await figs(d)
        ok('invalid Mermaid: the error next to the source', f[0]['err'] and f[0]['src'] == BROKEN and "Mermaid couldn't draw this." in await d.inner_text('.dgm .errbox')
           and len((await d.inner_text('.dgm .dgerr')).strip()) > 5)
        ok('invalid Mermaid: no error graphic left anywhere else', 'Syntax error in text' not in await d.evaluate('[...document.body.children].filter(e => !e.closest("#root")).map(e => e.innerText).join(" ")'))
        await d.click('.dtools [data-act="editdoc"]'); await d.wait_for_selector('#doc-editor')
        await d.fill('#doc-editor', ADR.replace(BROKEN, FIXED)); await d.click('.dtools [data-act="donedit"]')
        await wait_svgs(d, 1, 20000)
        ok('fixing the source draws it', (await figs(d))[0]['svg'] and not (await figs(d))[0]['err'])

        # 4. Tracked changes: a changed diagram is reviewed as source; unchanged ones are drawn
        await d.evaluate('location.hash = "#p-pr-design"'); await d.wait_for_selector('.rbar', timeout=8000); await wait_svgs(d, 1, 20000); await d.wait_for_timeout(300)
        ok('review: the changed diagram shows as source', await d.locator('.doc.review .chg pre').count() >= 1 and await d.locator('.doc.review .chg .dgm').count() == 0
           and 'ROOM ||--o{ STUDENT : holds' in await d.evaluate('[...document.querySelectorAll(".doc.review .chg pre")].map(e => e.innerText).join(" ")'))
        ok('review: the unchanged diagram is drawn', await d.locator('.doc.review > .dgm .dgpic svg, .doc.review .dgm .dgpic svg').count() == 1)

        # 5. A draft streaming in shows diagrams as code, then draws them when it lands
        await d.evaluate(f'window.__replies.push({json.dumps(ARCH_DRAFT)}); window.__tick = 60; window.__step = 12')
        await d.evaluate('location.hash = "#p-pn-design"'); await d.wait_for_selector('.docbody [data-act="draftdoc"]', timeout=8000)
        await d.click('.docbody [data-act="draftdoc"] >> nth=0')
        await d.wait_for_function('document.querySelector("#draft-live") && document.querySelector("#draft-live").innerText.includes("flowchart LR")', timeout=10000)
        ok('streaming draft: diagram shown as code, not drawn', await d.locator('#draft-live .dgm').count() == 0 and await d.locator('#draft-live pre').count() >= 1)
        await d.wait_for_selector('[data-act="usedraft"]', timeout=15000); await wait_svgs(d, 1, 20000)
        ok('landed draft: its diagram is drawn', await d.locator('.doc .dgm .dgpic svg').count() == 1)

        # 6. Switching to light draws again in light colours
        await d.evaluate('location.hash = "#p-pd-design"'); await d.wait_for_selector('.doctabs', timeout=8000)
        await d.click('.doctabs [data-tab="architecture"]'); await wait_svgs(d, 3, 20000)
        n0 = await d.evaluate('S.dgN')
        await d.emulate_media(color_scheme='light'); await d.wait_for_timeout(300); await wait_svgs(d, 3, 20000)
        await d.wait_for_function('S.dgN >= %d' % (n0 + 3), timeout=20000); await d.wait_for_timeout(200)
        fill = await d.evaluate('getComputedStyle(document.querySelector(".dgm .node rect, .dgm .node path, .dgm .node polygon")).fill')
        ok('light theme: drawn again in the light tones', fill == 'rgb(255, 255, 255)')
        await d.screenshot(path=OUT + 's9-diagrams-1440-light.png')
        await ctx.close()

        # 7. Mermaid can't load: the source, why, and Try again
        cx = await b.new_context(viewport={'width': 1440, 'height': 900})
        k = await cx.new_page(); k.on('pageerror', lambda e: errs.append('noload: ' + str(e)))
        st2 = {'reqs': [], 'down': True}; await serve_mermaid(k, st2)
        await k.add_init_script(mock())
        await k.goto(URL + '#p-pd-design'); await k.wait_for_selector('.dgm .notice', timeout=15000)
        f = await figs(k)
        ok("can't load: says so, shows every source, Try again", all(x['src'] for x in f) and len(f) == 3 and "The diagram can't be drawn right now." in await k.inner_text('.dgm .notice')
           and 'jsDelivr' in await k.inner_text('.dgm .notice') and await k.locator('.dgm [data-act="dgretry"]').count() == 3)
        st2['down'] = False
        await k.click('.dgm [data-act="dgretry"] >> nth=0'); await wait_svgs(k, 3, 30000)
        ok('Try again: all three drawn, from a fresh URL', all(x['svg'] for x in await figs(k)) and any(u.startswith(ENTRY + '?retry=') for u in st2['reqs']))
        await cx.close()

        # 8. 1024
        cx = await b.new_context(viewport={'width': 1024, 'height': 768})
        k = await cx.new_page(); k.on('pageerror', lambda e: errs.append('1024: ' + str(e)))
        await serve_mermaid(k, {'reqs': []}); await k.add_init_script(mock())
        await k.goto(URL + '#p-pd-design'); await wait_svgs(k, 3)
        ok('1024: no sideways scroll', await k.evaluate('document.documentElement.scrollWidth <= innerWidth'))
        await k.screenshot(path=OUT + 's9-diagrams-1024.png')
        await cx.close()

        # 9. Phones: fits the width; tap opens full screen; pinch, drag, reset, close
        for (wd, ht, scheme) in [(390, 844, 'dark'), (360, 800, 'light')]:
            tag = f'{wd}'
            mc = await b.new_context(viewport={'width': wd, 'height': ht}, color_scheme=scheme, has_touch=True, is_mobile=True)
            m = await mc.new_page(); m.on('pageerror', lambda e, t=tag: errs.append(t + ': ' + str(e)))
            await serve_mermaid(m, {'reqs': []}); await m.add_init_script(mock())
            await m.goto(URL + '#p-pd-design'); await wait_svgs(m, 3); await m.wait_for_timeout(200)
            ok(f'{tag}: diagrams fit the width, no sideways scroll', await m.evaluate('[...document.querySelectorAll(".dgm svg")].every(s => s.getBoundingClientRect().right <= innerWidth)')
               and await m.evaluate('document.documentElement.scrollWidth <= innerWidth'))
            hs = await m.eval_on_selector_all('.dgm >> nth=0 >> .dgtabs button', 'els => els.map(e => e.getBoundingClientRect().height)')
            ok(f'{tag}: 44px tabs; Tap to zoom', min(hs) >= 44 and await m.is_visible('.dgm .dghint'))
            await m.screenshot(path=OUT + f's9-diagram-{tag}-{scheme}.png')
            await m.tap('.dgm .dgpic >> nth=0'); await m.wait_for_selector('.dgfull', timeout=4000)
            ok(f'{tag}: tap opens the diagram full screen', await m.is_visible('.dgfull #dgstage svg') and await m.evaluate('document.activeElement.id') == 'dgf-close')
            await m.screenshot(path=OUT + f's9-diagram-full-{tag}-{scheme}.png')
            await m.evaluate('''() => { const st = document.getElementById('dgstage'), r = st.getBoundingClientRect();
                const ev = (type, id, x, y) => st.dispatchEvent(new PointerEvent(type, {pointerId:id, pointerType:'touch', isPrimary:id === 1, clientX:r.left + x, clientY:r.top + y, bubbles:true}));
                ev('pointerdown', 1, 100, 200); ev('pointerdown', 2, 160, 200); ev('pointermove', 2, 220, 200); ev('pointerup', 2, 220, 200); ev('pointerup', 1, 100, 200); }''')
            z = await m.evaluate('[S.zoom.s, document.getElementById("dginner").style.transform]')
            ok(f'{tag}: pinch zooms in', abs(z[0] - 2) < 0.01 and 'scale(2)' in z[1])
            before = await m.evaluate('[S.zoom.x, S.zoom.y]')
            await m.evaluate('''() => { const st = document.getElementById('dgstage'), r = st.getBoundingClientRect();
                const ev = (type, x, y) => st.dispatchEvent(new PointerEvent(type, {pointerId:5, pointerType:'touch', isPrimary:true, clientX:r.left + x, clientY:r.top + y, bubbles:true}));
                ev('pointerdown', 50, 50); ev('pointermove', 90, 80); ev('pointerup', 90, 80); }''')
            after = await m.evaluate('[S.zoom.x, S.zoom.y, S.zoom.s]')
            ok(f'{tag}: drag moves it, same zoom', abs(after[0] - before[0] - 40) < 0.01 and abs(after[1] - before[1] - 30) < 0.01 and abs(after[2] - 2) < 0.01)
            await m.tap('.dgfull [data-act="dgreset"]'); await m.wait_for_timeout(100)
            ok(f'{tag}: Reset', 'scale(1)' in await m.evaluate('document.getElementById("dginner").style.transform'))
            await m.tap('#dgf-close'); await m.wait_for_timeout(200)
            ok(f'{tag}: Close goes back to the document', await m.locator('.dgfull').count() == 0 and await m.locator('.dgm svg').count() == 3)
            await mc.close()

        await b.close()
        passed = sum(1 for _, c in checks if c)
        print(f'{passed}/{len(checks)} passed')
        for nm, c in checks:
            if not c: print('  FAILED:', nm)
        print('page errors:', errs or 'none')

asyncio.run(main())
