"""S1 browser test: the Projects board, with drafts to review and the last Claude Code session on each row.
Mocked db (with a one-time pass over older drafts), mocked Claude (a streamed draft) and mocked repo snapshots."""
import asyncio, json, os, re, time
from pathlib import Path
from playwright.async_api import async_playwright
HERE = Path(__file__).resolve().parent
URL = (HERE.parent / 'src' / 'index.html').as_uri()
OUT = str(HERE / 'out') + os.sep            # screenshots land in tests/out/
os.makedirs(OUT, exist_ok=True)
LAUNCH = {'executable_path': os.environ['CHROME']} if os.environ.get('CHROME') else {}   # optional: your own Chrome

NOW = int(time.time() * 1000)
DAY = 86400000
TODAY = time.strftime('%Y-%m-%d')
YESTERDAY = time.strftime('%Y-%m-%d', time.localtime(time.time() - 86400))

PRD = "# Matchbook\n\nFor Saturday 5-a-side players.\n\n## Problem\n- Goals get disputed in WhatsApp\n- Nobody keeps a season table\n\n## Goals (v1)\n1. Captains log goals live\n2. Everyone sees the season table\n\n## Non-goals\n- Player accounts\n"
PRD_DRAFT = "# Matchbook\n\nFor Saturday 5-a-side players, who argue over who scored.\n\n## Problem\n- Goals get disputed in WhatsApp\n\n## Goals (v1)\n1. Captains log goals and assists live\n2. Everyone sees the season table\n3. Both captains confirm the result\n\n## Non-goals\n- Player accounts\n"
NFRS = "# NFRs\n\n- Cost: $0\n- Reach: phones\n"
NFRS_DRAFT = "# NFRs\n\n- Cost: $0 on free tiers\n- Reach: phones\n- Speed: the board shows in 2 s\n"
STORIES_DRAFT = "# User stories\n\n## Must\n- [ ] S1 · Join a game with a room code\n"
ARCH_DRAFT = "# Architecture\n\nTier 1: one static page on Cloudflare Pages, with Firebase for auth and data.\n\n## Stack\n- Vanilla JS\n- Firebase Spark plan\n"

def draft(text, base, at):
    return {'text': text, 'at': at, 'basedOn': 1, 'cut': False, 'base': base, 'decisions': {}}

SNAP_SIWES = {
    'repo': 'C:\\Projects\\siwes', 'repoName': 'siwes', 'via': 'laptop', 'at': NOW - 3600000, 'marks': {}, 'branch': 'main',
    'slices': [{'id': 'S1', 'title': 'Sign in', 'status': 'done', 'group': 'Must', 'raw': '- [x] S1 · Sign in'},
               {'id': 'S2', 'title': 'Daily log', 'status': 'done', 'group': 'Must', 'raw': '- [x] S2 · Daily log'},
               {'id': 'S3', 'title': 'Weekly report', 'status': 'check', 'group': 'Must', 'raw': '- [~] S3 · Weekly report'},
               {'id': 'S4', 'title': 'Supervisor sign-off', 'status': 'todo', 'group': 'Must', 'raw': '- [ ] S4 · Supervisor sign-off'}],
    'log': [{'date': TODAY, 'id': 'S3', 'title': 'Weekly report', 'built': 'The weekly report.', 'tests': '12 passed', 'check': 'Open week 3.', 'next': 'S4', 'commit': ''},
            {'date': YESTERDAY, 'id': 'S2', 'title': 'Daily log', 'built': 'Daily log.', 'tests': '8 passed', 'check': '', 'next': 'S3', 'commit': ''}],
    'commits': [{'hash': 'a1b2c3d', 'subject': 'feat(S3): weekly report', 'at': NOW - 300000},
                {'hash': 'b2c3d4e', 'subject': 'feat(S2): daily log', 'at': NOW - DAY - 3600000}]
}
# The newest entry is from yesterday, but its slice's commit is older: show the day only
SNAP_OLD = {
    'repo': 'C:\\Projects\\old', 'repoName': 'old', 'via': 'paste', 'at': NOW - 2 * DAY, 'marks': {}, 'branch': '',
    'slices': [{'id': 'S2', 'title': 'Export', 'status': 'todo', 'group': '', 'raw': '- [ ] S2 · Export'}],
    'log': [{'date': YESTERDAY, 'id': 'S2', 'title': 'Export to CSV, with every column the coach asked for', 'built': 'x', 'tests': '', 'check': '', 'next': '', 'commit': ''}],
    'commits': [{'hash': 'c3d4e5f', 'subject': 'feat(S2): start export', 'at': NOW - 3 * DAY}]
}

SEED = {
    # Pre-S1 project: a PRD draft waiting for review, but no summary on the record yet (the one-time pass finds it)
    'projects/pd': {'name': 'Matchbook', 'phase': 'define', 'completed': {'discover': True}, 'checks': {'define': [True, False, False, False]}, '__ago': 5 * DAY},
    'docs/pd~prd': {'pid': 'pd', 'phase': 'define', 'key': 'prd', 'text': PRD, 'draft': draft(PRD_DRAFT, PRD, NOW - 2 * DAY), '__ago': 2 * DAY},
    # Two drafts, already summarised on the record (as S1 writes it)
    'projects/pm': {'name': 'Mafia v2', 'phase': 'define', 'completed': {'discover': True}, 'checks': {}, '__ago': 3 * DAY,
                    'drafts': {'pm~stories': {'key': 'stories', 'phase': 'define', 'name': 'user stories', 'at': NOW - 3 * DAY, 'review': False, 'n': 0, 'left': 0},
                               'pm~nfrs': {'key': 'nfrs', 'phase': 'define', 'name': 'NFRs', 'at': NOW - DAY, 'review': True, 'n': 2, 'left': 2}}},
    'docs/pm~stories': {'pid': 'pm', 'phase': 'define', 'key': 'stories', 'text': '', 'draft': draft(STORIES_DRAFT, '', NOW - 3 * DAY), '__ago': 3 * DAY},
    'docs/pm~nfrs': {'pid': 'pm', 'phase': 'define', 'key': 'nfrs', 'text': NFRS, 'draft': draft(NFRS_DRAFT, NFRS, NOW - DAY), '__ago': DAY},
    # Build, synced: a slice waiting on a phone check, last session today
    'projects/pb': {'name': 'SIWES logbook', 'phase': 'build', 'completed': {'discover': True, 'define': True, 'design': True}, 'checks': {}, 'repo': 'C:\\Projects\\siwes', '__ago': 2 * DAY},
    'syncs/pb': SNAP_SIWES,
    # Design, most recent activity, no drafts and no repo
    'projects/pc': {'name': 'Hall registration', 'phase': 'design', 'completed': {'discover': True, 'define': True}, 'checks': {'design': [True, False, False]}, '__ago': 3600000},
    # A folder set but never synced
    'projects/pe': {'name': 'Bus tracker', 'phase': 'build', 'completed': {'discover': True, 'define': True, 'design': True}, 'checks': {}, 'repo': 'C:\\Projects\\bus', '__ago': 6 * DAY},
    # Synced from a pasted update: the session shows its day only
    'projects/pf': {'name': 'Old app', 'phase': 'build', 'completed': {'discover': True, 'define': True, 'design': True}, 'checks': {}, 'repo': 'C:\\Projects\\old', '__ago': 7 * DAY},
    'syncs/pf': SNAP_OLD,
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
    where(a, op, v){ window.__wheres.push([col, a, op, v]); return query(col, [a, op, v]); },
    onSnapshot(cb, err){ subs.push({col, f, cb}); setTimeout(() => cb(snapQ(col, f)), 30); return () => {}; },
    async get(){
      if (col === 'docs') window.__gets.push(f ? f[2] : '*');
      if (col === 'docs' && window.__docsGetFail) throw {code:'unavailable', message:'mock'};
      return snapQ(col, f);
    }
  });
  const db = { collection(col){ return Object.assign(query(col, null), {
    doc(id){ const k = col + '/' + id; return {
      async set(d){ window.__writes.push(k); S0[k] = JSON.parse(JSON.stringify(d)); persist(); setTimeout(()=>notify(k), 20); },
      async get(){ return snapD(k); },
      onSnapshot(cb, err){ dsubs.push({k, cb}); setTimeout(() => cb(snapD(k)), 40); return () => {}; },
      async delete(){ window.__dels.push(k); delete S0[k]; persist(); setTimeout(()=>notify(k), 20); } }; }
  }); } };
  window.__store = S0; window.__calls = []; window.__writes = []; window.__dels = []; window.__wheres = []; window.__gets = []; window.__replies = []; window.__mode = 'ok';
  window.__docsGetFail = %GETFAIL%;
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
      if (i >= full.length){ clearInterval(t); resolve({text: full, truncated: false}); }
    }, tick);
    if (opts.signal) opts.signal.addEventListener('abort', () => { clearInterval(t); reject({code:'aborted', text: full.slice(0, i)}); });
  });
  sample.json = (input, opts) => { window.__calls.push({input, json:true}); return new Promise(r => setTimeout(() => r([]), 40)); };
  const mcp = { async listTools(){ return {servers:[]}; }, async callTool(){ throw {code:'server_not_connected', message:'no host'}; }, watchTool(){ return () => {}; }, async invalidate(){} };
  window.claude = { use: async n => n === 'db' ? (window.__noDb ? null : db) : n === 'sample' ? sample : n === 'mcp' ? mcp : null };
})();
"""


def mock(seed=SEED, getfail=False):
    return MOCK.replace('%SEED%', json.dumps(seed)).replace('%GETFAIL%', json.dumps(getfail))


async def store(pg, k):
    return await pg.evaluate(f'window.__store[{json.dumps(k)}]')


async def needs(pg):
    return await pg.eval_on_selector_all('.needs li', '''els => els.map(li => ({
        text: li.querySelector('.what a').innerText, meta: li.querySelector('.what > span').innerText.replace(/\\s+/g, ' ').trim(),
        href: li.querySelector('.what a').getAttribute('href'), first: li.classList.contains('first'),
        btn: (li.querySelector('.btn.primary') || li.querySelector('.open') || {}).innerText || ''}))''')


async def row(pg, name):   # the desktop grid row for a project: [name cell text, session line, now cell text]
    return await pg.evaluate('''name => { const tr = [...document.querySelectorAll('table.grid tbody tr')].find(r => r.querySelector('th a') && r.querySelector('th a').innerText === name);
        if (!tr) return null; const s = tr.querySelector('th .sess'), n = tr.querySelector('td.now');
        return {sess: s ? s.innerText.replace(/\\s+/g, ' ').trim() : '', title: s ? s.getAttribute('title') : '', now: n ? n.innerText.replace(/\\s+/g, ' ').trim() : ''}; }''', name)


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
        await d.goto(URL + '#board'); await d.wait_for_selector('.needs li', timeout=8000)

        # 1. The board before and after the one-time pass over older drafts
        first = await needs(d)
        ok('board up: one Needs you item per active project', len(first) == 6)
        ok('before the pass: the pre-S1 draft is not known yet', not any('PRD draft' in n['text'] for n in first))
        await d.wait_for_timeout(2600)
        ok('one-time pass: reads each project\'s documents once, after the board is up', sorted(await d.evaluate('window.__gets')) == sorted(['pd', 'pm', 'pb', 'pc', 'pe', 'pf']))
        pdrec = await store(d, 'projects/pd')
        ok('one-time pass: the PRD draft is summarised on its project (no text kept)', pdrec.get('drafts', {}).get('pd~prd') == {'key': 'prd', 'phase': 'define', 'name': 'PRD', 'at': NOW - 2 * DAY, 'review': True, 'n': 4, 'left': 4})
        ok('one-time pass: projects already right aren\'t rewritten', 'projects/pm' not in await d.evaluate('window.__writes') and 'projects/pb' not in await d.evaluate('window.__writes'))
        ok('one-time pass: remembered in settings', (await store(d, 'settings/board') or {}).get('drafts') == 1)

        # 2. Needs you: drafts first, then a slice to check, then the rest by last activity
        n = await needs(d)
        ok('order: drafts, then the phone check, then the rest by last activity', [x['meta'].split(' · ')[0] for x in n] == ['Matchbook', 'Mafia v2', 'SIWES logbook', 'Hall registration', 'Old app', 'Bus tracker'])
        ok('draft item: canvas wording, change count in blue, Start review as the one primary button',
           n[0]['text'] == 'Review the PRD draft Claude wrote' and n[0]['meta'] == 'Matchbook · Define · 4 tracked changes' and n[0]['first'] and n[0]['btn'] == 'Start review'
           and await d.locator('.needs .btn.primary').count() == 1
           and await d.eval_on_selector('.needs li.first .cl', 'e => getComputedStyle(e).color') == 'rgb(127, 178, 240)')
        ok('two drafts in one project: one item, both named, opens the oldest', n[1]['text'] == 'Review 2 drafts Claude wrote' and n[1]['meta'] == 'Mafia v2 · Define · user stories and NFRs'
           and n[1]['href'] == '#p-pm-define' and n[1]['btn'] == 'Open')
        ok('slice check comes next, unchanged', n[2]['text'] == 'Check S3 on your phone' and n[2]['meta'] == 'SIWES logbook · Build · slices 2/4')
        ok('others keep their next step', n[3]['text'] == 'Pick the lightest architecture on the ladder' and n[3]['href'] == '#p-pc')

        # 3. Projects grid: the Now cell and the last Claude Code session under the name
        r = await row(d, 'Matchbook'); r2 = await row(d, 'Mafia v2')
        ok('Now cell: a waiting draft is the next step', r['now'].endswith('PRD draft to review') and r2['now'].endswith('2 drafts to review'))
        r = await row(d, 'SIWES logbook')
        ok('session line: slice and its commit time, today', re.fullmatch(r'Claude Code · S3 · today \d\d:\d\d', r['sess']) is not None and 'Weekly report' in r['title'])
        ok('session line: ID and time in mono, 12px meta colour', await d.evaluate('''() => { const s = [...document.querySelectorAll('table.grid th .sess')].find(x => x.innerText.includes('S3'));
            const m = [...s.querySelectorAll('.mono')]; const cs = getComputedStyle(s);
            return m.length === 2 && getComputedStyle(m[0]).fontFamily.includes('JetBrains') && cs.fontSize === '12px' && cs.color === 'rgb(134, 139, 146)'; }'''))
        ok('session line: a commit older than the entry gives the day only', (await row(d, 'Old app'))['sess'] == 'Claude Code · S2 · yesterday')
        ok('session line: folder set but never synced', (await row(d, 'Bus tracker'))['sess'] == 'Claude Code · not synced yet')
        ok('session line: none without a repo', (await row(d, 'Hall registration'))['sess'] == '')
        nolog = await d.evaluate('''() => { const p = proj("pe"); S.syncs.pe = {log:[], commits:[], slices:[]}; const h = sessLine(p); delete S.syncs.pe; return h; }''')
        ok('session line: synced but no progress entries', 'no sessions logged yet' in nolog)
        ok('desktop 1440: no sideways scroll', await d.evaluate('document.documentElement.scrollWidth <= innerWidth'))
        await d.screenshot(path=OUT + 's1-board-1440-dark.png', full_page=True)

        # 4. Start review opens the draft's phase and document, with the Changes tab on a laptop
        await d.click('.needs li.first .btn.primary'); await d.wait_for_selector('.rbar', timeout=8000); await d.wait_for_timeout(200)
        ok('Start review: lands in Define on the PRD review', await d.evaluate('location.hash') == '#p-pd-define' and await d.get_attribute('.doctabs [data-tab="prd"]', 'aria-selected') == 'true')
        ok('Start review: Changes tab open beside it', await d.get_attribute('.stabs [data-tab="changes"]', 'aria-selected') == 'true')
        await d.click('.rnav [data-act="accept"]'); await d.wait_for_timeout(1200)
        ok('accepting a change updates the summary', (await store(d, 'projects/pd'))['drafts']['pd~prd']['left'] == 3)
        await d.evaluate('location.hash = "#board"'); await d.wait_for_selector('.needs li', timeout=4000); await d.wait_for_timeout(150)
        n = await needs(d)
        ok('half-reviewed: Finish reviewing, changes left, Continue review', n[0]['text'] == 'Finish reviewing the PRD draft' and n[0]['meta'] == 'Matchbook · Define · 3 of 4 changes left' and n[0]['btn'] == 'Continue review')
        await d.click('.needs li.first .btn.primary'); await d.wait_for_selector('.rbar', timeout=4000)
        await d.click('.rbar [data-act="acceptall"]'); await d.wait_for_timeout(150)
        await d.click('.rbar [data-act="finishreview"]'); await d.wait_for_timeout(1200)
        ok('finish review: the draft leaves the summary', (await store(d, 'projects/pd'))['drafts'] == {})
        await d.evaluate('location.hash = "#board"'); await d.wait_for_selector('.needs li', timeout=4000); await d.wait_for_timeout(150)
        n = await needs(d)
        ok('after review: Mafia v2 leads; Matchbook is back to its next step', n[0]['meta'].startswith('Mafia v2') and any(x['text'] == 'Draft the PRD and user stories' and x['meta'].startswith('Matchbook') for x in n)
           and (await row(d, 'Matchbook'))['now'].endswith('Draft the PRD and user stories'))

        # 5. Two drafts: the oldest (a new document) opens first; using it leaves the other
        await d.click('.needs li.first .btn.primary'); await d.wait_for_timeout(500)
        ok('oldest draft first: the user stories, as a new document', await d.evaluate('location.hash') == '#p-pm-define' and await d.get_attribute('.doctabs [data-tab="stories"]', 'aria-selected') == 'true'
           and await d.locator('[data-act="usedraft"]').count() >= 1)
        await d.click('[data-act="usedraft"] >> nth=0'); await d.wait_for_timeout(1200)
        rec = await store(d, 'projects/pm')
        ok('used draft leaves the summary; the other stays, counted from the document', list(rec['drafts'].keys()) == ['pm~nfrs'] and rec['drafts']['pm~nfrs']['n'] == 2)
        await d.evaluate('location.hash = "#board"'); await d.wait_for_selector('.needs li', timeout=4000); await d.wait_for_timeout(150)
        n = await needs(d)
        ok('one draft left: Review the NFRs draft', n[0]['text'] == 'Review the NFRs draft Claude wrote' and n[0]['meta'] == 'Mafia v2 · Define · 2 tracked changes')

        # 6. Claude drafting: shown on the board while it streams, then the draft takes the project's item
        await d.evaluate(f'window.__replies.push({json.dumps(ARCH_DRAFT)}); window.__tick = 120; window.__step = 8')
        await d.evaluate('location.hash = "#p-pc"'); await d.wait_for_selector('.doctabs', timeout=6000); await d.wait_for_timeout(300)
        await d.click('.docbody [data-act="draftdoc"] >> nth=0'); await d.wait_for_timeout(300)
        await d.evaluate('location.hash = "#board"'); await d.wait_for_selector('.needs li', timeout=4000)
        hall = [x for x in await needs(d) if x['meta'].startswith('Hall registration')][0]
        ok('board while Claude drafts: blue note on the project\'s item', 'Claude is drafting the architecture…' in hall['meta'])
        await d.evaluate('window.__tick = 6; window.__step = 400')
        await d.wait_for_function('document.querySelector(".needs li.first") && document.querySelector(".needs li.first").innerText.includes("architecture")', timeout=15000)
        await d.wait_for_timeout(1200)
        n = await needs(d)
        ok('new draft lands: Read the architecture draft, first (newest activity)', n[0]['text'] == 'Read the architecture draft Claude wrote' and n[0]['meta'] == 'Hall registration · Design · new document' and n[0]['btn'] == 'Read draft')
        ok('new draft summarised on its project', (await store(d, 'projects/pc'))['drafts'].get('pc~architecture', {}).get('review') is False)

        # 7. Keyboard: the first link opens the draft
        await d.focus('.needs li.first .what a'); await d.keyboard.press('Enter'); await d.wait_for_timeout(400)
        ok('keyboard: Enter on the first item opens the draft', await d.evaluate('location.hash') == '#p-pc-design' and await d.get_attribute('.doctabs [data-tab="architecture"]', 'aria-selected') == 'true')

        # 8. A project row lands in its current phase (S1 criterion 2)
        await d.evaluate('location.hash = "#board"'); await d.wait_for_selector('table.grid', timeout=4000)
        await d.click('table.grid tbody th a >> text=SIWES logbook'); await d.wait_for_timeout(300)
        ok('row: opens the project in its current phase', await d.evaluate('location.hash') == '#p-pb' and 'Build' in await d.inner_text('.ptabs [aria-current="step"]'))
        await ctx.close()

        # 9. A fresh page after the pass: no second pass, the board reads the summaries
        cx = await b.new_context(viewport={'width': 1440, 'height': 900}, color_scheme='light')
        k = await cx.new_page(); k.on('pageerror', lambda e: errs.append('light: ' + str(e)))
        seeded = dict(SEED); seeded['settings/board'] = {'drafts': 1, 'at': NOW}
        # a stale summary: says the Hall architecture has a draft, but the document has none
        seeded['projects/pc'] = dict(SEED['projects/pc'], drafts={'pc~architecture': {'key': 'architecture', 'phase': 'design', 'name': 'architecture', 'at': NOW - DAY, 'review': True, 'n': 3, 'left': 3}})
        seeded['docs/pc~architecture'] = {'pid': 'pc', 'phase': 'design', 'key': 'architecture', 'text': '# Architecture\n\nTier 1.\n', '__ago': DAY}
        await k.add_init_script(mock(seeded))
        await k.goto(URL + '#board'); await k.wait_for_selector('.needs li', timeout=8000); await k.wait_for_timeout(2600)
        ok('after the pass: no document reads on the board', await k.evaluate('window.__gets') == [] and await k.evaluate('window.__wheres.filter(w => w[0] === "docs").length') == 0)
        n = await needs(k)
        ok('summaries drive the board (here, one stale)', n[0]['meta'] == 'Hall registration · Design · 3 tracked changes' and n[1]['meta'].startswith('Mafia v2'))
        ok('light: change count in light blue', await k.eval_on_selector('.needs li.first .cl', 'e => getComputedStyle(e).color') == 'rgb(31, 95, 174)')
        await k.screenshot(path=OUT + 's1-board-1440-light.png', full_page=True)
        await k.click('.needs li.first .btn.primary'); await k.wait_for_timeout(1500)
        ok('stale summary: opening the documents corrects it', (await store(k, 'projects/pc'))['drafts'] == {} and await k.locator('.rbar').count() == 0)
        await k.evaluate('location.hash = "#board"'); await k.wait_for_selector('.needs li', timeout=4000); await k.wait_for_timeout(150)
        ok('stale summary: gone from the board', not any(x['meta'].startswith('Hall registration') and 'tracked' in x['meta'] for x in await needs(k)))
        # another device finishes a review: its summary arrives and the board follows
        await k.evaluate('window.__remote("projects/pm", {...window.__store["projects/pm"], drafts:{}, updatedAt:Date.now()})'); await k.wait_for_timeout(300)
        ok('another device clears a draft: the board follows', not any(x['meta'].startswith('Mafia v2') and 'NFRs' in x['meta'] for x in await needs(k)))
        await cx.close()

        # 10. The one-time pass fails: the board still works, and it's tried again next time
        cx = await b.new_context(viewport={'width': 1440, 'height': 900})
        k = await cx.new_page(); k.on('pageerror', lambda e: errs.append('getfail: ' + str(e)))
        await k.add_init_script(mock(getfail=True))
        await k.goto(URL + '#board'); await k.wait_for_selector('.needs li', timeout=8000); await k.wait_for_timeout(2600)
        ok('pass fails: board intact, nothing remembered, no error shown', await k.locator('.needs li').count() == 6 and not await store(k, 'settings/board') and await k.locator('.banner.err').count() == 0)
        await cx.close()

        # 11. This browser only (no account db): drafts read straight from the saved documents
        cx = await b.new_context(viewport={'width': 1440, 'height': 900})
        k = await cx.new_page(); k.on('pageerror', lambda e: errs.append('local: ' + str(e)))
        local = {'projects': {'pd': {'name': 'Matchbook', 'phase': 'define', 'completed': {'discover': True}, 'checks': {}, 'updatedAt': NOW}},
                 'captures': {}, 'docs': {'pd~prd': {'pid': 'pd', 'phase': 'define', 'key': 'prd', 'text': PRD, 'draft': draft(PRD_DRAFT, PRD, NOW - DAY), 'updatedAt': NOW}}}
        await k.add_init_script('window.__noDb = true; if (!window.name){ window.name = "seeded"; localStorage.setItem("the-studio-v2", %s); }' % json.dumps(json.dumps(local)))
        await k.add_init_script(mock())
        await k.goto(URL + '#board'); await k.wait_for_selector('.needs li', timeout=8000); await k.wait_for_timeout(300)
        n = await needs(k)
        ok('this browser only: the draft shows from the document itself', n[0]['text'] == 'Review the PRD draft Claude wrote' and n[0]['meta'] == 'Matchbook · Define · 4 tracked changes')
        await cx.close()

        # 12. Empty board (S1 criterion 3): the capture box and a way to start a project
        cx = await b.new_context(viewport={'width': 1440, 'height': 900})
        k = await cx.new_page(); k.on('pageerror', lambda e: errs.append('empty: ' + str(e)))
        await k.add_init_script(mock({}))
        await k.goto(URL + '#board'); await k.wait_for_selector('h2', timeout=8000); await k.wait_for_timeout(400)
        ok('empty board: Capture and New project, first-run text', await k.is_visible('.needs [data-act="capture"]') and await k.is_visible('.needs [data-act="newproject"]') and 'Nothing needs you yet' in await k.inner_text('main'))
        await k.click('.needs [data-act="capture"]'); await k.wait_for_timeout(200)
        ok('empty board: Capture opens the capture box with the cursor in it', await k.evaluate('document.activeElement && document.activeElement.id') == 'cap-text')
        await cx.close()

        # 13. 1024 wide
        cx = await b.new_context(viewport={'width': 1024, 'height': 768})
        k = await cx.new_page(); k.on('pageerror', lambda e: errs.append('1024: ' + str(e)))
        await k.add_init_script(mock())
        await k.goto(URL + '#board'); await k.wait_for_selector('.needs li', timeout=8000); await k.wait_for_timeout(2600)
        ok('1024: no page-level sideways scroll; session line visible', await k.evaluate('document.documentElement.scrollWidth <= innerWidth') and await k.locator('table.grid th .sess').count() == 3)
        await k.screenshot(path=OUT + 's1-board-1024.png')
        await cx.close()

        # 14. Phones: drafts first, tap a row to review, the session line on each synced row
        for (wd, ht, scheme) in [(390, 844, 'dark'), (360, 800, 'light')]:
            tag = f'{wd}'
            mc = await b.new_context(viewport={'width': wd, 'height': ht}, color_scheme=scheme, has_touch=True, is_mobile=True)
            m = await mc.new_page(); m.on('pageerror', lambda e, t=tag: errs.append(t + ': ' + str(e)))
            await m.add_init_script(mock())
            await m.goto(URL + '#board'); await m.wait_for_selector('.needs li', timeout=8000); await m.wait_for_timeout(2600)
            n = await needs(m)
            ok(f'{tag}: draft first, row 44px or taller', n[0]['text'] == 'Review the PRD draft Claude wrote' and min(await m.eval_on_selector_all('.needs li', 'els => els.map(e => e.getBoundingClientRect().height)')) >= 44)
            sess = await m.eval_on_selector_all('.mrows .sess', 'els => els.map(e => e.innerText.replace(/\\s+/g, " ").trim())')
            ok(f'{tag}: session line under the name on phone rows', any(re.fullmatch(r'Claude Code · S3 · today \d\d:\d\d', s) for s in sess) and 'Claude Code · not synced yet' in sess and len(sess) == 3)
            ok(f'{tag}: no sideways scroll', await m.evaluate('document.documentElement.scrollWidth <= innerWidth'))
            await m.screenshot(path=OUT + f's1-board-{tag}-{scheme}.png', full_page=True)
            box = await m.eval_on_selector('.needs li.first', 'e => { const r = e.getBoundingClientRect(); return [r.right - 20, r.top + r.height / 2]; }')
            await m.touchscreen.tap(box[0], box[1]); await m.wait_for_timeout(600)
            ok(f'{tag}: tapping the row opens the review on the document tab', await m.evaluate('location.hash') == '#p-pd-define' and await m.locator('.chg [data-act="accept"]').count() == 4
               and await m.get_attribute('.btabs [data-tab="doc"]', 'aria-selected') == 'true')
            await mc.close()

        await b.close()
        passed = sum(1 for _, c in checks if c)
        print(f'{passed}/{len(checks)} passed')
        for nm, c in checks:
            if not c: print('  FAILED:', nm)
        print('page errors:', errs or 'none')

asyncio.run(main())
