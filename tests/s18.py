"""S18 browser test: the case study on a shipped project's Ship page (portfolio page, technical write-up, short summary),
with a mocked db, a mocked streaming Claude, a mocked laptop file server and a stubbed clipboard."""
import asyncio, json, os, time, datetime
from pathlib import Path
from playwright.async_api import async_playwright
HERE = Path(__file__).resolve().parent
URL = (HERE.parent / 'src' / 'index.html').as_uri()
OUT = str(HERE / 'out') + os.sep            # screenshots land in tests/out/
os.makedirs(OUT, exist_ok=True)
LAUNCH = {'executable_path': os.environ['CHROME']} if os.environ.get('CHROME') else {}   # optional: your own Chrome

NOW = int(time.time() * 1000)
DAY = 86400000
SHIP_AT = int(datetime.datetime(2026, 11, 5, 12).timestamp() * 1000)

PRD = "# Mafia: PRD\n\n## One-liner\nFor friends who play Mafia at parties, who need a narrator, Mafia lets a phone run the game.\n\n## Constraints\n- $0 on free tiers\n- Works on cheap Android phones"
ARCH = "# Mafia: architecture\n\n## Tier\nStatic PWA with Firebase Realtime Database for the shared game state.\n\n## Stack\nVite, vanilla JS, Firebase, Cloudflare Pages."
ADR1 = "# ADR 1: Firebase for realtime game state\n\nStatus: Accepted\n\n## Decision\nUse Firebase's free tier so every phone sees the same night."
ADR2 = "# ADR 2: Cloudflare Pages for hosting\n\nStatus: Accepted\n\n## Decision\nGitHub Pages is blocked on some networks here, so host on Cloudflare."

PORT = "# Mafia: a party game a phone can narrate\n\nI built Mafia so a group of friends can play without a human narrator. It's live at mafia-game.pages.dev.\n\n## The problem\nSomeone always has to sit out to run the game.\n\nTBD: how many groups have played it.\n\n## Results\nA user said they loved the role reveal.\n\nTBD: what I'd do differently."
TECH = "# How I built Mafia\n\nA static PWA that keeps every phone in step.\n\n## Architecture\nVite and vanilla JS on Cloudflare Pages, with Firebase for the shared state.\n\n## Decisions\n### Firebase for realtime\nFree, and every phone sees the same night."
SUMM = "# Mafia\n\nmafia-game.pages.dev · Vite, Firebase, Cloudflare Pages\n\nA phone narrates Mafia so nobody sits out.\n\n- Shipped v1.0.0 in a week\n- Kept it at $0\n- Took feedback from testers"
TECH2 = "# How I built Mafia, again\n\n## Architecture\nStill a static PWA."

def entry(date, sid, title, built):
    return {'date': date, 'id': sid, 'title': title, 'built': built, 'tests': '9 passed', 'check': '', 'next': '', 'commit': ''}

ALL = ['discover', 'define', 'design', 'build', 'ship']
def shipped(name, **kw):
    return {'name': name, 'phase': 'ship', 'completed': {k: True for k in ALL}, 'checks': {}, 'oneLiner': 'For friends who play Mafia at parties, a phone runs the game.',
            'version': '1.0.0', 'versions': [{'v': '1.0.0', 'at': SHIP_AT, 'url': 'https://mafia-game.pages.dev/'}], '__ago': DAY, **kw}

SEED = {
    'projects/pl': {'name': 'SIWES logbook', 'phase': 'ship', 'completed': {k: True for k in ALL[:4]}, 'checks': {}, 'oneLiner': '', '__ago': DAY},
    'projects/pdone': shipped('Mafia', repo='C:\\Projects\\mafia', liveUrl='https://mafia-game.pages.dev/',
                              feedback=[{'id': 'f1', 'who': 'Dami', 'text': 'Night phase timer is too short for six players', 'at': SHIP_AT + DAY, 'bl': 'b1'},
                                        {'id': 'f2', 'who': 'Tobi', 'text': 'Loved the role reveal', 'at': SHIP_AT + 2 * DAY, 'bl': ''}],
                              backlog=[{'id': 'b1', 'text': 'Let the host set the night timer', 'who': 'Dami', 'from': 'f1', 'at': SHIP_AT + DAY}]),
    'projects/pnew': shipped('Hall pass', liveUrl='https://hallpass.pages.dev/'),
    'projects/pstop': shipped('Stop project', liveUrl=''),
    'syncs/pdone': {'repo': 'C:\\Projects\\mafia', 'repoName': 'mafia', 'via': 'laptop', 'at': NOW - DAY, 'slices': [], 'marks': {}, 'branch': 'main', 'commits': [],
                    'log': [entry('2026-11-10', 'S9', 'Host settings', 'host can set the night timer'), entry('2026-11-07', 'S8', 'Rejoin', 'players rejoin after a dropped connection'),
                            entry('2026-11-05', 'S7', 'Launch fixes', 'last fixes before launch'), entry('2026-11-04', 'S6', 'Roles', 'role reveal animation')]},
    'docs/pdone~prd': {'pid': 'pdone', 'phase': 'define', 'key': 'prd', 'text': PRD, '__ago': 9 * DAY},
    'docs/pdone~architecture': {'pid': 'pdone', 'phase': 'design', 'key': 'architecture', 'text': ARCH, '__ago': 8 * DAY},
    'docs/pdone~adr-a1': {'pid': 'pdone', 'phase': 'design', 'key': 'adr-a1', 'kind': 'adr', 'n': 1, 'text': ADR1, '__ago': 8 * DAY},
    'docs/pdone~adr-a2': {'pid': 'pdone', 'phase': 'design', 'key': 'adr-a2', 'kind': 'adr', 'n': 2, 'text': ADR2, '__ago': 8 * DAY},
    'chats/pdone': {'messages': [], 'notes': {'who': 'Friends who play Mafia at parties', 'struggle': 'Someone always sits out to narrate'}, 'updatedAt': NOW - 10 * DAY},
}
CASES = {'portfolio': {'text': PORT, 'at': NOW - DAY, 'by': 'claude', 'v': '1.0.0'}, 'technical': {'text': TECH, 'at': NOW - DAY, 'by': 'claude', 'v': '1.0.0'},
         'summary': {'text': SUMM, 'at': NOW - DAY, 'by': 'claude', 'v': '1.0.0'}}
SEED_FILLED = {**SEED, 'projects/pdone': {**SEED['projects/pdone'], 'cases': CASES}}

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
  const notify = k => { const col = k.split('/')[0]; subs.filter(s => s.col === col && !s.held).forEach(s => s.cb(snapQ(col, s.f))); dsubs.filter(s => s.k === k).forEach(s => s.cb(snapD(k))); };
  const persist = () => localStorage.setItem('__mockdb', JSON.stringify(S0));
  window.__docsHold = %HOLD%; window.__docsFail = %DFAIL%; window.__docQ = [];
  window.__release = () => { window.__docsHold = false; subs.filter(s => s.held).forEach(s => { s.held = false; s.cb(snapQ(s.col, s.f)); }); };
  const query = (col, f) => ({
    where(a, op, v){ return query(col, [a, op, v]); },
    onSnapshot(cb, err){
      if (col === 'docs') window.__docQ.push(f ? f[2] : '');
      if (col === 'docs' && window.__docsFail){ setTimeout(() => err && err({code:'unavailable', message:'mock'}), 30); return () => {}; }
      const s = {col, f, cb, held: col === 'docs' && window.__docsHold}; subs.push(s);
      if (!s.held) setTimeout(() => cb(snapQ(col, f)), 30);
      return () => {};
    },
    async get(){ return snapQ(col, f); }
  });
  const db = { collection(col){ return Object.assign(query(col, null), {
    doc(id){ const k = col + '/' + id; return {
      async set(d){ S0[k] = JSON.parse(JSON.stringify(d)); persist(); setTimeout(()=>notify(k), 20); },
      async get(){ return snapD(k); },
      onSnapshot(cb, err){ dsubs.push({k, cb}); setTimeout(() => cb(snapD(k)), 40); return () => {}; },
      async delete(){ delete S0[k]; persist(); setTimeout(()=>notify(k), 20); } }; }
  }); } };
  window.__store = S0; window.__remote = (k, d) => { S0[k] = d; persist(); notify(k); };   // a write from another device
  window.__clip = null; window.__clipFail = false;
  Object.defineProperty(navigator, 'clipboard', {configurable:true, value:{writeText: async t => { if (window.__clipFail) throw new Error('denied'); window.__clip = t; }}});
  window.__calls = []; window.__replies = []; window.__mode = 'ok'; window.__failQ = []; window.__seen = [];
  const sample = (input, opts) => new Promise((resolve, reject) => {
    window.__calls.push({input: JSON.parse(JSON.stringify(input))});
    const fq = window.__failQ.length ? window.__failQ.shift() : '';
    if (fq || window.__mode !== 'ok'){ const code = fq || window.__mode; window.__mode = 'ok'; setTimeout(() => reject({code, message:'mock'}), 30); return; }
    const full = window.__replies.length ? window.__replies.shift() : '# Untitled\n\nOkay.';
    let i = 0; const step = window.__step || 20, tick = window.__tick || 6;
    opts.onText && opts.onText({text:'Thinking...', delta:''});
    const t = setInterval(() => {
      i = Math.min(full.length, i + step);
      opts.onText && opts.onText({text: full.slice(0, i), delta: ''});
      const live = document.querySelector('#cs-live'); if (live) window.__seen.push(live.innerText);
      if (i >= full.length){ clearInterval(t); resolve({text: full}); }
    }, tick);
    if (opts.signal) opts.signal.addEventListener('abort', () => { clearInterval(t); reject({code:'aborted'}); });
  });
  sample.json = () => Promise.reject({code:'unavailable'});
  const mcp = {
    async listTools(){ return {servers: %HOST% === 'listed' ? [{server:'host:filesystem', authStatus:'unknown', tools:[{name:'read_text_file', description:''},{name:'edit_file', description:''}]}] : []}; },
    async callTool(){ throw {code:'tool_error', message:'ENOENT'}; },
    watchTool(){ return () => {}; }, async invalidate(){}
  };
  window.claude = { use: async n => n === 'db' ? db : n === 'sample' ? (%NOCLAUDE% ? null : sample) : n === 'mcp' ? mcp : null };
})();
"""

def mock(host='none', seed=None, hold=False, dfail=False, noclaude=False):
    return (MOCK.replace('%SEED%', json.dumps(SEED if seed is None else seed)).replace('%HOST%', json.dumps(host))
            .replace('%HOLD%', json.dumps(hold)).replace('%DFAIL%', json.dumps(dfail)).replace('%NOCLAUDE%', json.dumps(noclaude)))

REFUSE = 'window.__clipFail = true; window.__exec = document.execCommand; document.execCommand = () => false; 0'
ALLOW = 'window.__clipFail = false; document.execCommand = window.__exec; window.__clip = null; 0'
SELECTED = "(() => { const e = document.querySelector('#cf-text'); return !!e && document.activeElement === e && e.selectionStart === 0 && e.selectionEnd === e.value.length && e.value.length > 100; })()"


async def main():
    async with async_playwright() as pw:
        b = await pw.chromium.launch(**LAUNCH)
        errs, checks = [], []
        def ok(name, cond):
            checks.append((name, bool(cond)))
            if not cond: print('FAIL (so far) ' + name, flush=True)
        async def toast(pg):
            t = await pg.query_selector('.toast')
            return await t.inner_text() if t else ''
        async def P(pg, k='pdone'):
            return await pg.evaluate(f'window.__store["projects/{k}"]')
        async def calls(pg):
            return await pg.evaluate('window.__calls')
        async def pressed(pg):
            return await pg.evaluate('(() => { const b = document.querySelector(".csseg [aria-pressed=\\"true\\"]"); return b ? b.dataset.k : ""; })()')

        # ---------- Desktop 1440, dark ----------
        ctx = await b.new_context(viewport={'width': 1440, 'height': 900}, color_scheme='dark')
        d = await ctx.new_page(); d.on('pageerror', lambda e: errs.append('desk: ' + str(e)))
        await d.add_init_script(mock(hold=True))
        await d.goto(URL + '#p-pl'); await d.wait_for_selector('.shipmain .lsec', timeout=8000); await d.wait_for_timeout(500)
        ok('a project that has not shipped has no case study', await d.locator('.cssec').count() == 0 and await d.evaluate('window.__docQ.length') == 0)

        await d.goto(URL + '#p-pdone'); await d.wait_for_selector('.cssec', timeout=8000); await d.wait_for_timeout(400)
        cs = d.locator('.cssec')
        heads = await d.evaluate('[...document.querySelectorAll(".shipmain > section > .sechead h2")].map(h => h.textContent)')
        ok('Case study comes after Changelog, last on the page', len(heads) >= 2 and heads[-1] == 'Case study' and heads[-2].startswith('Changelog'))
        ok('three versions to switch between, Portfolio first', await d.evaluate('[...document.querySelectorAll(".csseg button")].map(b => b.textContent).join()') == 'Portfolio,Technical,Summary' and await pressed(d) == 'portfolio')
        ok('empty: says what the portfolio page is', 'No portfolio page yet' in await cs.inner_text() and 'For hiring managers' in await cs.inner_text())
        ok('the Ship page of a shipped project loads its documents', await d.evaluate('window.__docQ.join()') == 'pdone')
        ok('loading: Draft waits for the documents', await d.locator('.cssec [data-act="draftcs"]').is_disabled() and 'Loading your saved documents…' in await cs.inner_text()
           and await d.locator('.cssec [data-act="writecs"]').is_enabled())
        await d.evaluate('window.__release(); 0'); await d.wait_for_timeout(300)
        txt = await cs.inner_text()
        ok('ready: Draft is the primary button', await d.locator('.cssec [data-act="draftcs"]').is_enabled() and 'primary' in await d.locator('.cssec [data-act="draftcs"]').get_attribute('class'))
        ok('says what Claude reads', 'Claude reads the PRD, the architecture, 2 ADRs, 4 progress entries, 1 version and 2 pieces of feedback.' in txt)
        ok('says Draft writes all three', 'Draft with Claude writes all three, one after another.' in txt)
        await d.screenshot(path=OUT + 's18-desk-empty.png', full_page=True)

        # Draft all three
        await d.evaluate(f'window.__tick = 25; window.__step = 14; window.__replies.push({json.dumps(PORT)}, {json.dumps(TECH)}, {json.dumps(SUMM)})')
        n0 = len(await calls(d))
        await d.click('.cssec [data-act="draftcs"]'); await d.wait_for_timeout(250)
        txt = await cs.inner_text()
        ok('drafting: a blue panel, what comes next and the text streaming in', 'Claude is writing the portfolio page' in txt and 'Then the technical write-up and the short summary.' in txt
           and await d.locator('.cssec .ai').count() == 1 and await d.locator('#cs-live[aria-busy="true"][data-k="portfolio"]').count() == 1 and await d.locator('.cssec [data-act="stopcs"]').count() == 1)
        ok('drafting: says what Claude reads', 'From the PRD, the architecture, 2 ADRs, 4 progress entries, 1 version and 2 pieces of feedback.' in txt)
        await d.wait_for_function('S.cs.pdone && S.cs.pdone.k === "technical"', timeout=10000); await d.wait_for_timeout(150)
        ok('the portfolio page renders while it streams', any('Someone always has to sit out' in s for s in await d.evaluate('window.__seen')))
        ok('the portfolio page is saved before the next one starts', ((await P(d)).get('cases') or {}).get('portfolio', {}).get('text') == PORT)
        ok('the view follows the run to the technical write-up', await pressed(d) == 'technical' and 'Claude is writing the technical write-up' in await cs.inner_text() and 'Then the short summary.' in await cs.inner_text())
        await d.click('.csseg [data-k="portfolio"]'); await d.wait_for_timeout(150)
        txt = await cs.inner_text()
        ok('switching to a finished one mid-run shows it, with a line about the run', 'Someone always has to sit out' in txt and 'Claude is writing the technical write-up…' in txt and await d.locator('.csrun [data-act="csk"]').count() == 1)
        ok('mid-run: no Draft again', await d.locator('.cssec [data-act="draftcs"]').count() == 0 and await d.locator('.cssec [data-act="copycs"]').count() == 1)
        await d.wait_for_function('!S.cs.pdone', timeout=15000); await d.wait_for_timeout(750)
        ok('once you switch, the view stays put', await pressed(d) == 'portfolio')
        p = await P(d); c = p.get('cases') or {}
        ok('three calls, all three saved by Claude, covering v1.0.0', len(await calls(d)) == n0 + 3 and [c.get(k, {}).get('text') for k in ['portfolio', 'technical', 'summary']] == [PORT, TECH, SUMM]
           and all(c[k]['by'] == 'claude' and c[k]['v'] == '1.0.0' for k in c))
        ok('a toast says all three are ready', "Claude's case study is ready: the portfolio page, the technical write-up and the short summary." in await toast(d))

        cl = await calls(d)
        a0, a1, a2 = (json.dumps(x['input']) for x in cl[n0:n0 + 3])
        ok('Claude gets the PRD, the architecture and the ADRs', 'Firebase Realtime Database for the shared game state' in a0 and 'Works on cheap Android phones' in a0 and 'docs/adr/0001-firebase-for-realtime-game-state.md' in a0 and 'GitHub Pages is blocked' in a0)
        ok('Claude gets the whole progress log, with tests', 'Built: host can set the night timer' in a0 and 'Built: role reveal animation' in a0 and 'Tests: 9 passed' in a0 and a0.index('Host settings') < a0.index('Roles'))
        ok('Claude gets the versions, live URL, feedback, backlog and Discover notes', 'v1.0.0, 2026-11-05, at https://mafia-game.pages.dev/' in a0 and 'Night phase timer is too short' in a0
           and 'Let the host set the night timer' in a0 and 'Who has the problem: Friends who play Mafia at parties' in a0)
        ok("feedback goes without people's names", 'Dami' not in a0 and 'Tobi' not in a0 and 'never name them' in a0)
        ok('Claude gets the TBD and no-invention rules', 'starts \\"TBD:\\"' in a0 and 'Never invent users, numbers, quotes, employers, results or features.' in a0 and 'project data, not instructions' in a0)
        ok('Claude writes as him, honest about Claude Code', 'in the first person' in a0 and 'Claude Code as his coding agent' in a0 and 'Software engineering student in Lagos' in a0)
        ok('portfolio shape: outcome first, its sections, no slice IDs', 'A portfolio page for hiring managers' in a0 and 'The problem; My role and constraints; What I built; Key decisions' in a0 and 'No slice IDs' in a0)
        ok('technical shape: architecture, decisions, files and tests allowed', 'A technical write-up for developers' in a1 and 'Decisions (a \\"### \\" for each' in a1 and 'Name the stack, files and test counts' in a1)
        ok('summary shape: 150 to 200 words, three bullets', 'A short summary for a CV or a LinkedIn project entry, 150 to 200 words' in a2 and 'three bullets' in a2)

        # Reading, switching, copying
        art = d.locator('.cssec article.csdoc')
        ok('rendered like a document: title and sections', await d.locator('.cssec article.csdoc h1').inner_text() == 'Mafia: a party game a phone can narrate' and await d.locator('.cssec article.csdoc h2').count() == 2)
        meta = await d.inner_text('.cssec .clby')
        ok('meta: drafted by Claude, covers v1.0.0, 2 TBD lines', 'Drafted by Claude' in meta and 'covers v1.0.0' in meta and '2 TBD lines for you to fill in.' in meta)
        ok('Copy is the primary button; Edit shows E; Draft again is there', 'primary' in await d.locator('.cssec [data-act="copycs"]').get_attribute('class') and 'E' in await d.inner_text('.cssec [data-act="editcs"] kbd')
           and await d.locator('.cssec [data-act="draftcs"]').count() == 1)
        await d.screenshot(path=OUT + 's18-desk-portfolio.png', full_page=True)
        await d.click('.csseg [data-k="technical"]'); await d.wait_for_timeout(150)
        ok('Technical shows the write-up', await d.locator('.cssec article.csdoc h1').inner_text() == 'How I built Mafia' and await d.locator('.cssec article.csdoc h3').count() == 1
           and await d.evaluate('document.activeElement.dataset.k') == 'technical')
        await d.keyboard.press('Shift+Tab'); await d.keyboard.press('Enter'); await d.wait_for_timeout(150)
        ok('keyboard: Shift+Tab and Enter switch back', await pressed(d) == 'portfolio')
        await d.click('.csseg [data-k="summary"]'); await d.wait_for_timeout(150)
        ok('Summary shows the summary, no TBD note', 'A phone narrates Mafia' in await art.inner_text() and 'TBD' not in await d.inner_text('.cssec .clby'))
        await d.click('.cssec [data-act="copycs"]'); await d.wait_for_timeout(200)
        ok('Copy: the Markdown, with a toast', await d.evaluate('window.__clip') == SUMM and 'Copied the short summary as Markdown.' in await toast(d))
        await d.click('.csseg [data-k="portfolio"]'); await d.wait_for_timeout(150)

        # Edit
        await d.click('.cssec [data-act="editcs"]'); await d.wait_for_timeout(200)
        ok('Edit opens the Markdown, focused at the start', await d.input_value('#cs-editor') == PORT and await d.evaluate('document.activeElement.id') == 'cs-editor' and await d.evaluate('document.activeElement.selectionStart') == 0
           and 'Saves as you type' in await d.inner_text('.cssec .edfoot'))
        await d.keyboard.press('Control+End'); await d.keyboard.type('\n\nTBD: how many games were played.'); await d.wait_for_timeout(900)
        p = await P(d)
        ok('editing saves as you type and marks it yours', p['cases']['portfolio']['text'].endswith('TBD: how many games were played.') and p['cases']['portfolio']['by'] == 'you')
        await d.evaluate("window.__remote('captures/x1', {text:'from my phone', status:'new', createdAt:Date.now()}); 0"); await d.wait_for_timeout(750)
        ok('a re-render from another device keeps the caret', await d.evaluate('document.activeElement.id') == 'cs-editor' and await d.evaluate('document.activeElement.selectionStart') == len(p['cases']['portfolio']['text']))
        await d.keyboard.press('Escape'); await d.wait_for_timeout(200)
        ok('Esc closes the editor and shows it rendered', await d.locator('#cs-editor').count() == 0 and 'how many games were played' in await art.inner_text() and await d.evaluate('document.activeElement.dataset.act') == 'editcs')
        ok('it says Edited by you, now with 3 TBD lines', 'Edited by you' in await d.inner_text('.cssec .clby') and '3 TBD lines' in await d.inner_text('.cssec .clby'))
        await d.click('#cs-h'); await d.keyboard.press('e'); await d.wait_for_timeout(200)
        ok('E opens the editor', await d.evaluate('document.activeElement.id') == 'cs-editor')
        await d.click('.cssec [data-act="donecs"]'); await d.wait_for_timeout(150)
        ok('Done closes it', await d.locator('#cs-editor').count() == 0)

        # Draft again over your edits
        n1 = len(await calls(d))
        await d.click('.cssec .csbar [data-act="draftcs"]'); await d.wait_for_timeout(200)
        ok('Draft again asks before replacing your edits', 'Replace your edited portfolio page with a new draft from Claude?' in await cs.inner_text() and len(await calls(d)) == n1
           and await d.evaluate('document.activeElement.dataset.act') == 'draftcs')
        await d.click('[data-act="keepcs"]'); await d.wait_for_timeout(150)
        ok('Keep mine keeps it', 'Replace your edited' not in await cs.inner_text() and (await P(d))['cases']['portfolio']['by'] == 'you')
        await d.evaluate("window.__mode = 'rate_limited'; 0")
        await d.click('.cssec .csbar [data-act="draftcs"]'); await d.wait_for_timeout(150); await d.click('.cssec .gate [data-act="draftcs"]'); await d.wait_for_timeout(400)
        ok("Claude couldn't answer: says why, your version stays", "Claude couldn't write the portfolio page." in await cs.inner_text() and 'usage limit' in await cs.inner_text()
           and (await P(d))['cases']['portfolio']['by'] == 'you' and await d.locator('.cssec .errbox [data-act="draftcs"]').count() == 1)
        await d.evaluate(f'window.__tick = 40; window.__step = 4; window.__replies.push({json.dumps(PORT)})')
        await d.click('.cssec .errbox [data-act="draftcs"]'); await d.wait_for_timeout(250)
        ok('Try again: your current one stays until the new one is ready', 'Your current one stays as it is until the new one is ready.' in await cs.inner_text() and 'Then' not in await d.inner_text('.cssec .ai'))
        await d.click('[data-act="stopcs"]'); await d.wait_for_timeout(750)
        ok('Stop keeps nothing', 'Stopped. Nothing was kept.' in await toast(d) and (await P(d))['cases']['portfolio']['text'].endswith('games were played.'))

        # Draft again over Claude's own draft: no question, only that one
        await d.click('.csseg [data-k="technical"]'); await d.wait_for_timeout(150)
        await d.evaluate(f'window.__tick = 6; window.__step = 40; window.__replies.push({json.dumps(TECH2)})')
        n2 = len(await calls(d))
        await d.click('.cssec .csbar [data-act="draftcs"]'); await d.wait_for_function('!S.cs.pdone', timeout=8000); await d.wait_for_timeout(750)
        p = await P(d)
        ok("Draft again over Claude's draft: no question, one call, only that one", len(await calls(d)) == n2 + 1 and p['cases']['technical']['text'] == TECH2 and p['cases']['portfolio']['by'] == 'you'
           and "Claude's technical write-up is ready." in await toast(d))
        await d.click('.csseg [data-k="summary"]'); await d.wait_for_timeout(150)
        await d.evaluate("window.__replies.push('Sorry, I need more detail first.'); 0")
        await d.click('.cssec .csbar [data-act="draftcs"]'); await d.wait_for_timeout(600)
        ok('a reply with no heading is an error, and the summary stays', "Claude couldn't write the short summary." in await cs.inner_text() and "answer was empty" in await cs.inner_text() and (await P(d))['cases']['summary']['text'] == SUMM)

        # Refused copy
        await d.evaluate(REFUSE)
        await d.click('.cssec [data-act="copycs"]'); await d.wait_for_timeout(500)
        sheet = d.locator('.sheet[aria-labelledby="cf-h"]')
        ok('refused copy: a sheet with the Markdown selected', await sheet.is_visible() and 'Short summary for Mafia' in await sheet.inner_text() and 'The Markdown is selected' in await sheet.inner_text() and await d.evaluate(SELECTED.replace('> 100', '> 50')))
        ok('refused copy: its button says Copy Markdown, no stale toast', await d.inner_text('[data-act="copyfailagain"]') == 'Copy Markdown' and await d.query_selector('.toast') is None)
        await d.evaluate(ALLOW)
        await d.click('[data-act="copyfailagain"]'); await d.wait_for_timeout(200)
        ok('the sheet copies, then closes', await d.evaluate('window.__clip') == SUMM and await d.query_selector('.sheet') is None and 'Copied the short summary as Markdown.' in await toast(d))

        # A later version ships
        await d.wait_for_timeout(750)
        cur = await P(d)
        await d.evaluate("(c => window.__remote('projects/pdone', Object.assign({}, c, {version:'1.1.0', versions:[{v:'1.1.0', at:Date.now(), url:'https://mafia-game.pages.dev/'}].concat(c.versions)})))(%s)" % json.dumps(cur))
        await d.wait_for_timeout(400)
        await d.click('.csseg [data-k="portfolio"]'); await d.wait_for_timeout(150)
        ok('after v1.1.0 ships, it says which version it covers', 'Written when v1.0.0 was the latest; v1.1.0 has shipped since. Draft again to cover it.' in await cs.inner_text() and 'covers v1.0.0' in await d.inner_text('.cssec .clby'))

        # Offline
        await d.evaluate("window.dispatchEvent(new Event('offline')); 0"); await d.wait_for_timeout(200)
        ok('offline: no Draft again; Copy and Edit still work', await d.locator('.cssec [data-act="draftcs"]').count() == 0 and await d.locator('.cssec [data-act="copycs"]').is_enabled() and await d.locator('.cssec [data-act="editcs"]').is_enabled()
           and 'Draft again to cover it' not in await cs.inner_text())
        await d.evaluate("window.dispatchEvent(new Event('online')); 0"); await d.wait_for_timeout(200)
        await d.goto(URL + '#shipped'); await d.wait_for_timeout(400)
        ok('the Shipped list says where the case study lives', 'the case study live on each project' in await d.inner_text('main'))

        # A project with no documents or log: an error mid-run, then Try again carries on
        await d.goto(URL + '#p-pnew'); await d.wait_for_selector('.cssec', timeout=5000); await d.wait_for_timeout(400)
        ok('no documents or log: Claude reads only the version, and says the log is unread', "Claude reads 1 version. docs/progress.md hasn't been read yet, so it won't have the build log." in await d.inner_text('.cssec'))
        await d.evaluate("window.dispatchEvent(new Event('offline')); 0"); await d.wait_for_timeout(150)
        ok("offline and empty: write it yourself", await d.locator('.cssec [data-act="draftcs"]').count() == 0 and "You're offline, so write it yourself." in await d.inner_text('.cssec')
           and 'primary' in await d.locator('.cssec [data-act="writecs"]').get_attribute('class'))
        await d.evaluate("window.dispatchEvent(new Event('online')); 0"); await d.wait_for_timeout(150)
        await d.evaluate(f"window.__tick = 6; window.__step = 40; window.__failQ = ['', 'overloaded']; window.__replies.push({json.dumps(PORT)}, {json.dumps(TECH)}, {json.dumps(SUMM)})")
        n3 = len(await calls(d))
        await d.click('.cssec [data-act="draftcs"]'); await d.wait_for_timeout(1200)
        p = await P(d, 'pnew')
        ok('an error mid-run stops it on that version, the first is kept', len(await calls(d)) == n3 + 2 and list((p.get('cases') or {}).keys()) == ['portfolio'] and await pressed(d) == 'technical'
           and "Claude couldn't write the technical write-up." in await d.inner_text('.cssec'))
        await d.click('.cssec .errbox [data-act="draftcs"]'); await d.wait_for_function('!S.cs.pnew', timeout=8000); await d.wait_for_timeout(750)
        p = await P(d, 'pnew')
        ok('Try again writes that one and the rest', len(await calls(d)) == n3 + 4 and sorted(p['cases'].keys()) == ['portfolio', 'summary', 'technical'] and p['cases']['summary']['text'] == SUMM)

        # Stop mid-run keeps what's finished; writing one yourself mid-run is kept
        await d.goto(URL + '#p-pstop'); await d.wait_for_selector('.cssec', timeout=5000); await d.wait_for_timeout(400)
        await d.evaluate(f"window.__tick = 30; window.__step = 30; window.__replies.push({json.dumps(PORT)}, {json.dumps(TECH)})")
        await d.click('.cssec [data-act="draftcs"]')
        await d.wait_for_function('S.cs.pstop && S.cs.pstop.k === "technical"', timeout=10000); await d.wait_for_timeout(100)
        await d.click('[data-act="stopcs"]'); await d.wait_for_timeout(750)
        p = await P(d, 'pstop')
        ok('Stop mid-run keeps the finished one', 'Stopped. The portfolio page is kept.' in await toast(d) and list((p.get('cases') or {}).keys()) == ['portfolio'] and 'No technical write-up yet' in await d.inner_text('.cssec'))
        ok('then Draft with Claude offers the two that are left', 'Draft with Claude writes all three' not in await d.inner_text('.cssec') and await d.locator('.cssec [data-act="draftcs"]').is_enabled())
        await d.evaluate(f"window.__tick = 40; window.__step = 6; window.__replies.push({json.dumps(TECH)}, {json.dumps(SUMM)})")
        n4 = len(await calls(d))
        await d.click('.cssec [data-act="draftcs"]'); await d.wait_for_timeout(200)
        await d.click('.csseg [data-k="summary"]'); await d.wait_for_timeout(150)
        ok('a version still to come says when, and waits', 'Claude writes it after the technical write-up.' in await d.inner_text('.cssec') and await d.locator('.cssec [data-act="draftcs"]').is_disabled())
        await d.click('.cssec [data-act="writecs"]'); await d.wait_for_timeout(200)
        ok('Write it yourself starts from the shape, caret after the title', await d.input_value('#cs-editor') == '# Stop project\n\n' and await d.evaluate('document.activeElement.selectionStart') == len('# Stop project'))
        await d.keyboard.type(' · built in a week'); await d.wait_for_timeout(100)
        await d.wait_for_function('!S.cs.pstop', timeout=15000); await d.wait_for_timeout(750)
        p = await P(d, 'pstop')
        ok('the run skips the one you wrote: one call, yours kept', len(await calls(d)) == n4 + 1 and p['cases']['summary']['text'].startswith('# Stop project · built in a week') and p['cases']['summary']['by'] == 'you'
           and p['cases']['technical']['text'] == TECH and await d.evaluate('document.activeElement.id') == 'cs-editor')
        await d.keyboard.press('Control+a'); await d.keyboard.press('Delete'); await d.wait_for_timeout(100)
        await d.keyboard.press('Escape'); await d.wait_for_timeout(750)
        ok('emptied and closed: it goes', 'summary' not in ((await P(d, 'pstop')).get('cases') or {}) and 'No short summary yet' in await d.inner_text('.cssec'))

        # Reload: everything persisted
        await d.wait_for_timeout(750); dbsnap = await d.evaluate('localStorage.getItem("__mockdb")')
        r = await ctx.new_page(); r.on('pageerror', lambda e: errs.append('reload: ' + str(e)))
        await r.add_init_script('if (!window.name){ window.name = "seeded"; localStorage.setItem("__mockdb", %s); }' % json.dumps(dbsnap))
        await r.add_init_script(mock())
        await r.goto(URL + '#p-pdone-ship'); await r.wait_for_selector('.cssec article.csdoc', timeout=8000); await r.wait_for_timeout(500)
        ok('after a reload: your edited portfolio page, Edited by you', 'how many games were played' in await r.inner_text('.cssec article.csdoc') and 'Edited by you' in await r.inner_text('.cssec .clby'))
        await r.click('.csseg [data-k="technical"]'); await r.wait_for_timeout(150)
        ok('after a reload: the technical write-up is there', 'How I built Mafia, again' in await r.inner_text('.cssec article.csdoc'))
        ok('back in Ship with every item ticked, Finish Ship stays the one primary button', (await r.evaluate('caseSec(proj("pdone"), true)')).count('primary') == 0 and (await r.evaluate('caseSec(proj("pdone"), false)')).count('btn primary') == 1)
        await r.close()
        await ctx.close()

        # ---------- No Claude here; documents can't be reached ----------
        nc = await b.new_context(viewport={'width': 1440, 'height': 900})
        q = await nc.new_page(); q.on('pageerror', lambda x: errs.append('noclaude: ' + str(x)))
        await q.add_init_script(mock(noclaude=True))
        await q.goto(URL + '#p-pdone'); await q.wait_for_selector('.cssec', timeout=8000); await q.wait_for_timeout(500)
        ok("no Claude: write it yourself, and why", await q.locator('.cssec [data-act="draftcs"]').count() == 0 and "Claude isn't available here, so write it yourself." in await q.inner_text('.cssec'))
        await nc.close()
        fx = await b.new_context(viewport={'width': 1440, 'height': 900})
        q = await fx.new_page(); q.on('pageerror', lambda x: errs.append('docsfail: ' + str(x)))
        await q.add_init_script(mock(dfail=True))
        await q.goto(URL + '#p-pdone'); await q.wait_for_selector('.cssec', timeout=8000); await q.wait_for_timeout(500)
        ok("documents can't be reached: says so, Draft still works", "Your saved documents can't be reached right now" in await q.inner_text('.cssec') and await q.locator('.cssec [data-act="draftcs"]').is_enabled()
           and 'Claude reads 4 progress entries, 1 version and 2 pieces of feedback.' in await q.inner_text('.cssec'))
        await fx.close()

        # ---------- 1024, light ----------
        cx = await b.new_context(viewport={'width': 1024, 'height': 768}, color_scheme='light')
        k = await cx.new_page(); k.on('pageerror', lambda x: errs.append('1024: ' + str(x)))
        await k.add_init_script(mock(seed=SEED_FILLED))
        await k.goto(URL + '#p-pdone'); await k.wait_for_selector('.cssec article.csdoc', timeout=8000); await k.wait_for_timeout(500)
        ok('1024 light: no sideways scroll, no phone tabs', await k.evaluate('document.documentElement.scrollWidth <= innerWidth') and not await k.locator('.btabs').is_visible())
        await k.locator('.cssec').scroll_into_view_if_needed(); await k.screenshot(path=OUT + 's18-1024-light.png')
        await cx.close()

        # ---------- Phones: 390 dark and 360 light ----------
        for wd, ht, scheme, tag in [(390, 844, 'dark', 'm390'), (360, 800, 'light', 'm360')]:
            mc = await b.new_context(viewport={'width': wd, 'height': ht}, color_scheme=scheme, has_touch=True, is_mobile=True)
            m = await mc.new_page(); m.on('pageerror', lambda x, t=tag: errs.append(t + ': ' + str(x)))
            await m.add_init_script(mock(seed=SEED_FILLED))
            await m.goto(URL + '#p-pl'); await m.wait_for_selector('.shipmain', timeout=8000); await m.wait_for_timeout(500)
            ok(f'{tag}: not shipped: three tabs, no Case study', await m.locator('.btabs[aria-label="Ship views"] [role="tab"]').count() == 3)
            await m.goto(URL + '#p-pdone'); await m.wait_for_selector('.cssec', state='attached', timeout=8000); await m.wait_for_timeout(500)
            tabs = m.locator('.btabs[aria-label="Ship views"] [role="tab"]')
            ok(f'{tag}: shipped: a fourth tab, Case study', await tabs.count() == 4 and await tabs.nth(3).inner_text() == 'Case study')
            ok(f'{tag}: four tabs fit', await m.evaluate('[...document.querySelectorAll(".btabs.b4 button")].every(b => b.scrollWidth <= b.clientWidth + 1 && b.getBoundingClientRect().height >= 44)')
               and await m.evaluate('document.documentElement.scrollWidth <= innerWidth'))
            ok(f'{tag}: Launch tab: no case study, the bottom bar', not await m.locator('#cs-h').is_visible() and await m.locator('.mnav').count() == 1)
            await tabs.nth(3).tap(); await m.wait_for_timeout(250)
            ok(f'{tag}: Case study is full screen: only the case study, no bottom bar', await m.locator('#cs-h').is_visible() and not await m.locator('#cl-h').is_visible() and not await m.locator('#xc-h').is_visible()
               and not await m.locator('.shipbar').is_visible() and not await m.locator('.pside').is_visible() and await m.locator('.mnav').count() == 0)
            bar = await m.locator('.cssec .csbar').bounding_box(); cp = await m.locator('.cssec [data-act="copycs"]').bounding_box()
            ok(f'{tag}: Copy at the bottom of the screen, a big target', abs(bar['y'] + bar['height'] - ht) <= 2 and cp['height'] >= 44 and cp['width'] >= (wd - 64) / 3)
            sg = await m.locator('.csseg [data-k="summary"]').bounding_box()
            ok(f'{tag}: the version switch is full width with 44 px targets', sg['height'] >= 44 and await m.evaluate('document.querySelector(".csseg").getBoundingClientRect().width') >= wd - 40)
            ok(f'{tag}: no sideways scroll', await m.evaluate('document.documentElement.scrollWidth <= innerWidth'))
            await m.screenshot(path=OUT + f's18-{tag}-case.png')
            await m.locator('.csseg [data-k="technical"]').tap(); await m.wait_for_timeout(200)
            ok(f'{tag}: tap Technical to read it', 'How I built Mafia' in await m.inner_text('.cssec article.csdoc'))
            await m.locator('.cssec [data-act="copycs"]').tap(); await m.wait_for_timeout(250)
            ok(f'{tag}: tap Copy: the Markdown', await m.evaluate('window.__clip') == TECH and 'Copied the technical write-up as Markdown.' in await toast(m))
            await m.locator('.cssec [data-act="editcs"]').tap(); await m.wait_for_timeout(250)
            ok(f'{tag}: Edit opens the Markdown, Done at the bottom', await m.locator('#cs-editor').is_visible() and await m.locator('.cssec .csbar [data-act="donecs"]').is_visible())
            await m.screenshot(path=OUT + f's18-{tag}-edit.png')
            await m.locator('.cssec [data-act="donecs"]').tap(); await m.wait_for_timeout(200)
            await tabs.nth(0).tap(); await m.wait_for_timeout(200)
            ok(f'{tag}: back on Launch, the bottom bar returns', await m.locator('.mnav').count() == 1 and not await m.locator('#cs-h').is_visible())
            await mc.close()

        for n, c in checks: print(('PASS ' if c else 'FAIL ') + n)
        print(f'{sum(c for _, c in checks)}/{len(checks)} passed')
        print('ERRORS', errs)
        await b.close()

asyncio.run(main())
