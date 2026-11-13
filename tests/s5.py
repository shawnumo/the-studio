"""S5 browser test: phase-appropriate views, with a mocked db (collections, doc and where() subscriptions),
a mocked streaming Claude and a mocked laptop file server."""
import asyncio, json, os
from pathlib import Path
from playwright.async_api import async_playwright
HERE = Path(__file__).resolve().parent
URL = (HERE.parent / 'src' / 'index.html').as_uri()
OUT = str(HERE / 'out') + os.sep            # screenshots land in tests/out/
os.makedirs(OUT, exist_ok=True)
LAUNCH = {'executable_path': os.environ['CHROME']} if os.environ.get('CHROME') else {}   # optional: your own Chrome

PRD = """# Matchbook

For Saturday 5-a-side players, who argue over **who scored**, Matchbook lets captains log goals live. See [the group](https://example.com/group) and `npm run dev`. Not a [link](javascript:alert(1)).

## Goals (v1)
1. Captains log goals and assists live
2. Everyone sees the season table

## Must stories
- [x] S1 · Log a goal
- [~] S2 · Season table
- [ ] S3 · Confirm a match
  - nested detail
  - another detail

| NFR | Requirement |
| --- | --- |
| Cost | $0 on free tiers |
| Reachability | Works on MTN data |

> Keep v1 to goals and assists.

<script>window.__xss = 1</script>

```js
const x = "<b>not bold</b>";
```

---

Done."""
ADR1 = "# 0001: Use Firebase\n\nStatus: Accepted · 2026-11-10\n\n## Context\n\nWe need auth and a database on a free tier.\n\n## Decision\n\nFirebase Spark plan.\n"
STORIES_REPO = "# Matchbook · slices\r\n\r\n## Must\r\n- [ ] S1 · Log a goal\r\n- [ ] S2 · Season table\r\n"
ARCH_REPO = "# Architecture\n\nA static PWA on Cloudflare Pages with Firebase for auth and data.\n"

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
  window.__store = S0; window.__calls = []; window.__writes = []; window.__dels = []; window.__wheres = []; window.__replies = []; window.__seen = [];
  window.__remote = (k, d) => { S0[k] = d; persist(); notify(k); };   // a write from another device
  const sample = (input, opts) => new Promise((resolve, reject) => {
    window.__calls.push({input: JSON.parse(JSON.stringify(input)), opts: {modelTier: opts.modelTier, cache: opts.cache}});
    const full = window.__replies.length ? window.__replies.shift() : 'Okay.\n<studio>{"mode":"chat"}</studio>';
    let i = 0;
    opts.onText && opts.onText({text:'Thinking...', delta:''});
    const t = setInterval(() => {
      i = Math.min(full.length, i + 20);
      opts.onText && opts.onText({text: full.slice(0, i), delta: ''});
      if (i >= full.length){ clearInterval(t); resolve({text: full, truncated: false}); }
    }, 6);
    if (opts.signal) opts.signal.addEventListener('abort', () => { clearInterval(t); reject({code:'aborted', text: full.slice(0, i)}); });
  });
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

SEED = {
    'projects/pd': {'name': 'Matchbook', 'phase': 'define', 'completed': {'discover': True}, 'checks': {'define': [False, False, False, False]}, 'oneLiner': 'For Saturday 5-a-side players, who argue over who scored, Matchbook lets captains log goals live, unlike the WhatsApp tally.', 'repo': 'C:\\Projects\\matchbook', 'source': None, 'triage': {'scores': {'pain': 5, 'access': 5, 'scope': 3, 'cost': 4, 'learning': 5, 'motivation': 4}, 'verdict': 'promising', 'reasoning': '', 'tags': [], 'at': 1, 'from': 'coach'}, '__ago': 3600000},
    'chats/pd': {'messages': [], 'notes': {'who': 'A fixed group of 12 Saturday players', 'struggle': 'Goals posted in WhatsApp get disputed'}, 'free': False, 'trimmed': 0, 'updatedAt': 5},
    'docs/pd~prd': {'pid': 'pd', 'phase': 'define', 'key': 'prd', 'text': PRD, '__ago': 7200000},
    'projects/pg': {'name': 'Hall registration', 'phase': 'design', 'completed': {'discover': True, 'define': True}, 'checks': {'design': [False, False, False]}, 'oneLiner': '', 'repo': 'C:\\Projects\\hall', '__ago': 7200000},
    'docs/pg~prd': {'pid': 'pg', 'phase': 'define', 'key': 'prd', 'text': '# Hall registration\n\nStudents register for halls without queues.', '__ago': 86400000},
    'docs/pg~adr-a1': {'pid': 'pg', 'phase': 'design', 'key': 'adr-a1', 'kind': 'adr', 'n': 1, 'text': ADR1, '__ago': 86400000},
    'projects/ps': {'name': 'Mafia', 'phase': 'ship', 'completed': {'discover': True, 'define': True, 'design': True, 'build': True}, 'checks': {}, 'oneLiner': '', '__ago': 86400000 * 3},
    'projects/pb': {'name': 'Bundle splitter', 'phase': 'build', 'completed': {'discover': True, 'define': True, 'design': True}, 'checks': {}, '__ago': 86400000 * 4},
    'projects/px': {'name': 'Saturday idea', 'phase': 'discover', 'completed': {}, 'checks': {}, '__ago': 86400000 * 5},
}
FILES = {'C:\\Projects\\matchbook\\docs\\stories.md': STORIES_REPO, 'C:\\Projects\\hall\\docs\\architecture.md': ARCH_REPO}


def mock(host='listed'):
    return MOCK.replace('%FILES%', json.dumps(FILES)).replace('%SEED%', json.dumps(SEED)).replace('%HOST%', json.dumps(host))


B = lambda d: '\n<studio>' + json.dumps(d) + '</studio>'
DNOTES = {"users": "Captains and 12 players", "scope": "Log goals and assists live; season table", "nongoals": "", "musts": "", "nfrs": "", "open": ""}
RD1 = "Let's pin down the scope first." + B({"mode": "interview", "reason": "the PRD doesn't say who confirms a match", "question": {"n": 1, "of": 4, "text": "Who confirms a match result?"}, "choices": ["Both captains", "The referee", "Nobody"], "notes": DNOTES})
RD2 = "Both captains it is." + B({"mode": "interview", "reason": "", "question": {"n": 2, "of": 4, "text": "Does v1 need player accounts?"}, "choices": ["No, names only", "Yes"], "notes": dict(DNOTES, nongoals="Player accounts")})
RG1 = "A static PWA plus Firebase is the lightest fit." + B({"mode": "chat", "notes": {"tier": "Static PWA plus hosted backend", "stack": "", "data": "", "hosting": "", "decisions": "", "open": ""}})


async def boxes(pg, *sels):
    return await pg.evaluate('(s) => s.map(x => { const e = document.querySelector(x); if (!e || !e.offsetParent) return null; const r = e.getBoundingClientRect(); return {x:r.x, y:r.y, w:r.width, h:r.height, b:r.bottom}; })', list(sels))


async def idle(pg):
    await pg.wait_for_function('!document.querySelector("#coach-live")', timeout=8000); await pg.wait_for_timeout(60)


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(**LAUNCH)
        errs, checks = [], []

        def ok(name, cond):
            checks.append((name, bool(cond)))
            print(('PASS ' if cond else 'FAIL ') + name)

        # ---------- Desktop 1440, dark, in the Claude desktop app (file server listed) ----------
        ctx = await b.new_context(viewport={'width': 1440, 'height': 900}, color_scheme='dark')
        d = await ctx.new_page(); d.on('pageerror', lambda e: errs.append('desk: ' + str(e)))
        await d.add_init_script(mock('listed'))
        await d.goto(URL + '#p-pd'); await d.wait_for_selector('.doc h1', timeout=8000); await d.wait_for_timeout(250)

        # 1. Define opens on its document
        ok('define: documents are the main view', await d.is_visible('.pmain.docmain') and await d.query_selector('.pmain.coach') is None)
        tabs = await d.eval_on_selector_all('.doctabs button', 'els => els.map(e => [e.innerText.trim(), e.getAttribute("aria-selected")])')
        ok('define: doc tabs PRD, User stories, NFRs; PRD selected', [t[0] for t in tabs] == ['PRD', 'User stories', 'NFRs'] and tabs[0][1] == 'true')
        ok('define: the docs query is by project', ['docs', 'pid', '==', 'pd'] in await d.evaluate('window.__wheres'))
        doc = d.locator('article.doc')
        ok('render: headings', (await doc.locator('h1').inner_text()) == 'Matchbook' and await doc.locator('h2').count() == 2)
        ok('render: bold, inline code and a safe link', await doc.locator('strong').first.inner_text() == 'who scored' and await doc.locator('code').first.inner_text() == 'npm run dev'
           and await doc.locator('a[href="https://example.com/group"][target="_blank"]').count() == 1 and await doc.locator('a[href^="javascript"]').count() == 0)
        ok('render: ordered list, task boxes, nested list', await doc.locator('ol > li').count() == 2 and await doc.locator('li.task').count() == 3
           and await doc.locator('.tb.x').count() == 1 and await doc.locator('.tb.w').count() == 1 and await doc.locator('li.task ul > li').count() == 2)
        ok('render: table', await doc.locator('table thead th').count() == 2 and await doc.locator('table tbody tr').count() == 2 and 'MTN data' in await doc.locator('table').inner_text())
        ok('render: quote, code block, rule', await doc.locator('blockquote').count() == 1 and '<b>not bold</b>' in await doc.locator('pre code').inner_text() and await doc.locator('hr').count() == 1)
        ok('render: raw HTML stays text', await d.evaluate('window.__xss === undefined') and await d.query_selector('article.doc script') is None and '<script>' in await doc.inner_text())
        ok('doc: path, edited time, Edit and Import', 'docs/PRD.md' in await d.inner_text('.dtools') and 'Edited 2 h ago' in await d.inner_text('.dmeta')
           and await d.is_visible('.dtools [data-act="editdoc"]') and await d.is_visible('.dtools [data-act="importdoc"]'))
        bx = await boxes(d, '.docmain', '.dside', '.sidecoach .compose')
        ok('desktop: coach beside the document, 340-420 wide', bx[0] and bx[1] and bx[1]['x'] >= bx[0]['x'] + bx[0]['w'] - 1 and 340 <= bx[1]['w'] <= 420 and abs(bx[1]['y'] - bx[0]['y']) < 2)
        ok('desktop: composer in view', bx[2] and bx[2]['b'] <= 900)
        ok('desktop: no sideways scroll', await d.evaluate('document.documentElement.scrollWidth <= innerWidth'))
        stabs = await d.eval_on_selector_all('.stabs button', 'els => els.map(e => [e.innerText.trim(), e.getAttribute("aria-selected")])')
        ok('side panel: Coach and Checklist tabs, Coach first', stabs[0] == ['Coach', 'true'] and stabs[1][0].startswith('Checklist') and '0/4' in stabs[1][0])
        side = await d.inner_text('.sidecoach')
        ok('coach: Define intro, placeholder', "I'm your Define coach" in side and await d.get_attribute('#coach-input', 'placeholder') == 'Ask about scope, stories or NFRs')
        await d.screenshot(path=OUT + 's5-define-desk.png')

        # 2. The Define coach interviews beside the document
        await d.evaluate(f'window.__replies.push({json.dumps(RD1)}, {json.dumps(RD2)})')
        await d.click('.sidecoach [data-act="interview"]')
        await d.wait_for_selector('.sidecoach .ibar', timeout=5000); await idle(d)
        c0 = (await d.evaluate('window.__calls'))[0]
        first = c0['input'][0]['content']
        ok('coach call: default tier, Define prompt', c0['opts'] == {'modelTier': 'default', 'cache': False} and first.startswith('You are the Define coach'))
        ok('coach call: carries the PRD, one-liner and Discover notes', '--- docs/PRD.md ---' in first and 'Season table' in first and 'Matchbook lets captains' in first
           and 'A fixed group of 12' in first and '--- docs/nfrs.md ---\n(not written yet)' in first)
        ok('coach call: Define checklist and notes block', 'Define exit checklist' in first and '"musts":""' in first and first.rstrip().endswith('Interview me about what v1 should do.'))
        ok('coach: interview banner and choices in the side panel', 'Claude is interviewing you' in await d.inner_text('.sidecoach .ibar') and await d.locator('.sidecoach .choices button').count() == 3)
        ok('coach: document still the main view', await d.is_visible('article.doc h1'))
        st = await d.evaluate('window.__store')
        ok('coach: saved to its own chat', len(st.get('chats/pd~define', {}).get('messages', [])) == 2 and st['chats/pd']['messages'] == [] and st['chats/pd~define']['notes']['users'])
        await d.evaluate('document.activeElement && document.activeElement.blur()')
        await d.keyboard.press('1')
        await d.wait_for_function('document.querySelector(".sidecoach .qset legend") && document.querySelector(".sidecoach .qset legend").innerText.startsWith("2.")', timeout=5000); await idle(d)
        ok('coach: number key answers in the side panel', 'Both captains' in await d.inner_text('.sidecoach dl.qa'))
        m = await d.evaluate('(() => { const e = document.querySelector(".sidecoach .msgs"); return [e.scrollTop + e.clientHeight, e.scrollHeight, getComputedStyle(e).overflowY]; })()')
        ok('coach: side panel scrolls itself, at the latest message', m[2] == 'auto' and m[0] >= m[1] - 4)
        ok('page itself does not scroll', await d.evaluate('window.scrollY === 0 && document.documentElement.scrollHeight <= innerHeight + 1'))

        # 3. Checklist tab
        await d.click('.stabs [data-tab="checklist"]'); await d.wait_for_timeout(100)
        ok('checklist tab: checklist shown, coach hidden', await d.is_visible('.sidelist') and await d.is_hidden('.sidecoach') and await d.locator('.sidelist .checks li').count() == 4)
        sl = await d.inner_text('.sidelist')
        ok('checklist tab: goal, next step, coach notes, project, folder', 'Pin down exactly what v1 does' in sl and 'Next step' in sl and 'Captains and 12 players' in sl and 'Player accounts' in sl
           and await d.input_value('#p-repo3') == 'C:\\Projects\\matchbook')
        await d.click('.sidelist .checks li:first-child label'); await d.wait_for_timeout(900)
        ok('checklist tab: tick saves', (await d.evaluate('window.__store["projects/pd"].checks.define'))[0] is True and '1/4' in await d.inner_text('.stabs [data-tab="checklist"]'))
        await d.click('.stabs [data-tab="coach"]'); await d.wait_for_timeout(150)
        m = await d.evaluate('(() => { const e = document.querySelector(".sidecoach .msgs"); return [e.scrollTop + e.clientHeight, e.scrollHeight]; })()')
        ok('coach tab again: back at the latest message', await d.is_visible('.sidecoach') and m[0] >= m[1] - 4)

        # 4. Edit the PRD (E), autosave, a remote echo doesn't clobber typing, Esc
        await d.evaluate('document.activeElement && document.activeElement.blur()')
        await d.keyboard.press('e'); await d.wait_for_timeout(100)
        ok('E opens the editor with the Markdown, focused', await d.is_visible('#doc-editor') and await d.evaluate('document.activeElement.id') == 'doc-editor'
           and (await d.input_value('#doc-editor')).startswith('# Matchbook'))
        await d.evaluate('(() => { const e = document.querySelector("#doc-editor"); e.setSelectionRange(e.value.length, e.value.length); })()')
        await d.keyboard.type('\n\n## Added by test\n\nFirst line.')
        await d.evaluate("window.__remote('docs/pd~prd', Object.assign({}, window.__store['docs/pd~prd'], {text:'stale copy', updatedAt:1}))")
        await d.keyboard.type(' Second.')
        await d.wait_for_timeout(1000)
        sv = await d.evaluate('window.__store["docs/pd~prd"]')
        ok('autosave within a second, typing kept over a stale echo', 'First line. Second.' in sv['text'] and sv['pid'] == 'pd' and 'First line. Second.' in await d.input_value('#doc-editor'))
        ok('status says saved', 'Saved' in await d.inner_text('[data-status]'))
        await d.keyboard.press('Escape'); await d.wait_for_timeout(150)
        ok('Esc leaves the editor; focus on Edit', await d.query_selector('#doc-editor') is None and 'Added by test' in await d.inner_text('article.doc h2:last-of-type')
           and await d.evaluate('document.activeElement.dataset.act') == 'editdoc')
        # Reload. Chrome sometimes drops a page's last localStorage writes when it reloads, so a fresh page gets the mock db's copy instead.
        await d.wait_for_timeout(300); snap = await d.evaluate('localStorage.getItem("__mockdb")')
        await d.close()
        d = await ctx.new_page(); d.on('pageerror', lambda e: errs.append('desk: ' + str(e)))
        await d.add_init_script('if (!window.name){ window.name = "seeded"; localStorage.setItem("__mockdb", %s); }' % json.dumps(snap))
        await d.add_init_script(mock('listed'))
        await d.goto(URL + '#p-pd'); await d.wait_for_selector('.doc h1', timeout=8000)
        ok('reload: the edit is kept', 'Second.' in await d.inner_text('article.doc'))

        # 5. An empty document, written here
        await d.click('.doctabs [data-tab="nfrs"]'); await d.wait_for_timeout(100)
        e = await d.inner_text('.dempty')
        ok('empty doc: teaches what goes in it', 'No NFRs yet' in e and 'Cost and Reachability' in e and 'import docs/nfrs.md from your repo' in ' '.join(e.split())
           and await d.is_visible('.dempty .btn.primary[data-act="editdoc"]'))
        await d.click('.dempty [data-act="editdoc"]'); await d.wait_for_timeout(80)
        ok('Start writing: empty editor, focused', await d.evaluate('document.activeElement.id') == 'doc-editor' and await d.input_value('#doc-editor') == '')
        await d.keyboard.type('# NFRs\n\n- Cost: $0')
        await d.wait_for_timeout(900)
        n = await d.evaluate('window.__store["docs/pd~nfrs"]')
        ok('new doc saved with project, phase and key', n and n['pid'] == 'pd' and n['phase'] == 'define' and n['key'] == 'nfrs' and n['text'].startswith('# NFRs'))
        await d.click('.dtools [data-act="donedit"]'); await d.wait_for_timeout(100)
        ok('Done shows it rendered', (await d.inner_text('article.doc h1')) == 'NFRs')

        # 6. Import from the repo
        await d.click('.doctabs [data-tab="stories"]'); await d.wait_for_timeout(100)
        await d.click('.dempty [data-act="importdoc"]'); await d.wait_for_selector('#impForm', timeout=2000)
        ok('import sheet: folder from the project, Import', await d.input_value('#imp-repo') == 'C:\\Projects\\matchbook' and (await d.inner_text('#impForm button[type=submit]')) == 'Import')
        await d.click('#impForm button[type=submit]'); await d.wait_for_selector('#impForm', state='detached', timeout=4000); await d.wait_for_timeout(700)
        calls = await d.evaluate('window.__mcpCalls')
        ok('import: reads docs/stories.md from the folder', calls[-1] == {'tool': 'read_text_file', 'input': {'path': 'C:\\Projects\\matchbook\\docs\\stories.md'}})
        sd = await d.evaluate('window.__store["docs/pd~stories"]')
        ok('import: saved, line endings normalised, source noted', sd and '\r' not in sd['text'] and sd['text'].startswith('# Matchbook · slices') and sd['imported']['path'] == 'docs/stories.md'
           and 'Imported from docs/stories.md' in await d.inner_text('.dmeta') and await d.locator('article.doc li.task').count() == 2)
        await d.click('.doctabs [data-tab="nfrs"]'); await d.wait_for_timeout(100)
        await d.click('.dtools [data-act="importdoc"]'); await d.wait_for_selector('#impForm')
        ok('import over a doc: asks to replace', "Replace with the repo's copy" in await d.inner_text('#impForm') and 'replaces the NFRs saved in The Studio' in await d.inner_text('#impForm'))
        await d.click('#impForm button[type=submit]'); await d.wait_for_selector('#impForm .inline-err', timeout=3000)
        ok('import: missing file explained, doc unchanged', "There's no docs/nfrs.md in C:\\Projects\\matchbook." in await d.inner_text('#impForm .inline-err')
           and (await d.evaluate('window.__store["docs/pd~nfrs"].text')).startswith('# NFRs'))
        await d.keyboard.press('Escape'); await d.wait_for_timeout(100)
        ok('Esc closes the sheet', await d.query_selector('#impForm') is None)

        # 7. Design: architecture and decisions
        await d.goto(URL + '#p-pg'); await d.wait_for_selector('.doctabs', timeout=8000); await d.wait_for_timeout(250)
        tabs = await d.eval_on_selector_all('.doctabs button', 'els => els.map(e => e.innerText.split(/\\s+/).join(" ").trim())')
        ok('design: tabs Architecture and Decisions with a count', tabs == ['Architecture', 'Decisions 1'])
        ok('design: architecture empty state', 'No Architecture yet' in await d.inner_text('.dempty') and "I'm your Design coach" in await d.inner_text('.sidecoach'))
        await d.evaluate('window.__delay = 3200')
        await d.click('.dempty [data-act="importdoc"]'); await d.wait_for_selector('#impForm')
        await d.click('#impForm button[type=submit]'); await d.wait_for_timeout(2900)
        ok('import: slow first read says it is connecting', 'Connecting to your laptop' in await d.inner_text('#impForm') and await d.is_disabled('#impForm button[type=submit]'))
        await d.wait_for_selector('#impForm', state='detached', timeout=4000); await d.wait_for_timeout(200)
        ok('import: architecture in', 'Cloudflare Pages' in await d.inner_text('article.doc'))
        await d.click('.doctabs [data-tab="adr"]'); await d.wait_for_timeout(100)
        row = await d.inner_text('.adrlist li:first-child')
        ok('decisions: list with number, title, status', '0001' in row and 'Use Firebase' in row and 'Accepted' in row and await d.is_hidden('.dtools [data-act="importdoc"]'))
        await d.click('.dtools [data-act="newadr"]'); await d.wait_for_timeout(120)
        v = await d.input_value('#doc-editor')
        ok('New ADR: numbered template, caret after the number', v.startswith('# 0002: \n\nStatus: Proposed · ') and '## Alternatives considered' in v and await d.evaluate('document.activeElement.selectionStart') == 8)
        await d.keyboard.type('Use Cloudflare Pages'); await d.wait_for_timeout(900)
        a2 = [x for k, x in (await d.evaluate('window.__store')).items() if k.startswith('docs/pg~adr-') and x.get('n') == 2]
        ok('New ADR saved as ADR 2', len(a2) == 1 and a2[0]['kind'] == 'adr' and a2[0]['text'].startswith('# 0002: Use Cloudflare Pages'))
        ok('ADR path from its title', 'docs/adr/0002-use-cloudflare-pages.md' in await d.inner_text('.dtools'))
        await d.click('.dtools [data-act="donedit"]'); await d.click('[data-act="closeadr"]'); await d.wait_for_timeout(100)
        ok('decisions: two rows, new one proposed', await d.locator('.adrlist li').count() == 2 and 'Proposed' in await d.inner_text('.adrlist li:nth-child(2)') and 'Decisions 2' in ' '.join((await d.inner_text('.doctabs')).split()))
        await d.click('.adrlist li:nth-child(2) button'); await d.click('.dtools [data-act="askdeladr"]')
        ok('delete ADR asks first', 'for good?' in await d.inner_text('.dtools'))
        await d.click('.dtools [data-act="deladr"]'); await d.wait_for_timeout(300)
        ok('delete ADR: gone from the list and the store', await d.locator('.adrlist li').count() == 1 and not [k for k in (await d.evaluate('Object.keys(window.__store)')) if k.startswith('docs/pg~adr-') and k != 'docs/pg~adr-a1'])
        await d.evaluate(f'window.__replies.push({json.dumps(RG1)})')
        await d.fill('#coach-input', 'Which tier fits?'); await d.keyboard.press('Enter'); await d.wait_for_timeout(200); await idle(d)
        g = (await d.evaluate('window.__calls'))[-1]['input'][0]['content']
        ok('design coach: reads the Define docs, architecture and ADRs', g.startswith('You are the Design coach') and 'Students register for halls' in g and '--- docs/architecture.md ---' in g
           and '--- docs/adr/0001-use-firebase.md ---' in g and '"tier":""' in g and 'Which tier fits?' in g)
        ok('design coach: own chat and notes', len((await d.evaluate('window.__store["chats/pg~design"]'))['messages']) == 2 and 'lightest fit' in await d.inner_text('.sidecoach'))
        await d.screenshot(path=OUT + 's5-design-desk.png')

        # 8. Ship opens on its checklist; Build stays the monitor; Discover stays the chat
        await d.goto(URL + '#p-ps'); await d.wait_for_selector('.shipmain', timeout=8000)
        ok('ship: checklist is the main view', await d.locator('.pmain .checks.big li').count() == 3 and await d.locator('.pside .checks').count() == 0 and 'Exit checklist' in await d.inner_text('.shipmain'))
        await d.click('.shipmain .checks li:first-child label'); await d.wait_for_timeout(800)
        ok('ship: tick saves', (await d.evaluate('window.__store["projects/ps"].checks.ship'))[0] is True)
        await d.fill('#p-live', 'https://mafia.pages.dev'); await d.click('.shipmain h2'); await d.wait_for_timeout(800)
        ok('ship: live URL saved, Open link', (await d.evaluate('window.__store["projects/ps"].liveUrl')) == 'https://mafia.pages.dev' and await d.locator('.liverow a[href="https://mafia.pages.dev"]').count() == 1)
        ok('ship: no sideways scroll, page layout', await d.evaluate('document.documentElement.scrollWidth <= innerWidth') and await d.query_selector('.app.fixed') is None)
        await d.screenshot(path=OUT + 's5-ship-desk.png')
        await d.goto(URL + '#p-pb'); await d.wait_for_timeout(300)
        ok('build: still the monitor', 'Connect this project to its repo' in await d.inner_text('.pmain'))
        await d.goto(URL + '#p-px'); await d.wait_for_selector('.coach .msgs[data-ready]', timeout=8000)
        ok('discover: still the conversation', await d.is_visible('.pmain.coach') and await d.query_selector('.docmain') is None)
        await d.goto(URL + '#p-px-define'); await d.wait_for_selector('.docmain', timeout=8000); await d.click('.stabs [data-tab="checklist"]')
        ok('a later phase: documents open, checklist says it comes later', 'This phase comes later' in await d.inner_text('.sidelist') and await d.is_visible('.docmain'))

        # 9. Deleting a project deletes its documents and chats
        await d.goto(URL + '#p-pg'); await d.wait_for_selector('.doctabs'); await d.click('.stabs [data-tab="checklist"]')
        await d.click('.sidelist [data-act="askdelete"]'); await d.click('.sidelist [data-act="delete"]'); await d.wait_for_timeout(400)
        keys = await d.evaluate('Object.keys(window.__store)')
        ok('delete project: docs and phase chats go too', not [k for k in keys if k.startswith('docs/pg') or k.startswith('chats/pg') or k == 'projects/pg'])
        await ctx.close()

        # ---------- Loading, slow, error, no Claude, no file server ----------
        cx = await b.new_context(viewport={'width': 1440, 'height': 900})
        h = await cx.new_page(); h.on('pageerror', lambda e: errs.append('hang: ' + str(e)))
        await h.add_init_script(mock('none')); await h.add_init_script('window.__docsHang = true; window.__noSample = true;')
        await h.goto(URL + '#p-pd'); await h.wait_for_selector('.docmain', timeout=8000); await h.wait_for_timeout(300)
        ok('loading: shapes while documents load', await h.locator('.docbody [aria-busy="true"] .sk').count() >= 5)
        ok('no Claude: the coach says it is off', 'The coach is off here' in await h.inner_text('.sidecoach'))
        await h.wait_for_timeout(10300)
        ok('slow: says the documents cannot be reached yet', "can't be reached yet" in await h.inner_text('.docbody'))
        await cx.close()
        cx = await b.new_context(viewport={'width': 1440, 'height': 900})
        f = await cx.new_page(); f.on('pageerror', lambda e: errs.append('fail: ' + str(e)))
        await f.add_init_script(mock('none')); await f.add_init_script('window.__docsFail = true;')
        await f.goto(URL + '#p-pd'); await f.wait_for_selector('.docbody .errbox', timeout=8000)
        ok('error: documents cannot be loaded', "These documents can't be loaded" in await f.inner_text('.docbody .errbox'))
        await cx.close()
        cx = await b.new_context(viewport={'width': 1440, 'height': 900})
        w = await cx.new_page(); w.on('pageerror', lambda e: errs.append('web: ' + str(e)))
        await w.add_init_script(mock('none'))
        await w.goto(URL + '#p-pd'); await w.wait_for_selector('.doc h1', timeout=8000)
        ok('no file server: no Import button', await w.query_selector('[data-act="importdoc"]') is None)
        await w.click('.doctabs [data-tab="stories"]')
        ok('no file server: empty state says where import works', 'Open The Studio in the Claude desktop app on your laptop' in await w.inner_text('.dempty'))
        await cx.close()

        # ---------- This browser only (no db) ----------
        cx = await b.new_context(viewport={'width': 1440, 'height': 900})
        lo = await cx.new_page(); lo.on('pageerror', lambda e: errs.append('local: ' + str(e)))
        await lo.add_init_script(mock('none')); await lo.add_init_script("""window.__noDb = true; if (!localStorage.getItem('the-studio-v2')) localStorage.setItem('the-studio-v2', JSON.stringify({projects:{pl:{name:'Local one', phase:'define', completed:{discover:true}, checks:{}, createdAt:1, updatedAt:1}}, captures:{}}));""")
        await lo.goto(URL + '#p-pl'); await lo.wait_for_selector('.dempty', timeout=8000)
        await lo.click('.dempty [data-act="editdoc"]'); await lo.keyboard.type('# Local PRD'); await lo.wait_for_timeout(900)
        await lo.keyboard.type(' v2'); await lo.wait_for_timeout(900)
        ls = await lo.evaluate('JSON.parse(localStorage.getItem("the-studio-v2")).docs')
        ok('this browser only: the document saves locally', ls and ls['pl~prd']['text'] == '# Local PRD v2' and await lo.input_value('#doc-editor') == '# Local PRD v2')
        await cx.close()

        # ---------- 1024 desktop ----------
        cx = await b.new_context(viewport={'width': 1024, 'height': 768})
        k = await cx.new_page(); k.on('pageerror', lambda e: errs.append('1024: ' + str(e)))
        await k.add_init_script(mock('listed'))
        await k.goto(URL + '#p-pd'); await k.wait_for_selector('.doc h1', timeout=8000); await k.wait_for_timeout(200)
        bx = await boxes(k, '.docmain', '.dside', '.sidecoach .compose')
        ok('1024: coach still beside the document', bx[1]['x'] >= bx[0]['x'] + bx[0]['w'] - 1 and bx[1]['w'] >= 340 and bx[0]['w'] >= 420 and bx[2]['b'] <= 768)
        ok('1024: no sideways scroll', await k.evaluate('document.documentElement.scrollWidth <= innerWidth'))
        await k.screenshot(path=OUT + 's5-define-1024.png')
        await cx.close()

        # ---------- Light, desktop ----------
        cx = await b.new_context(viewport={'width': 1440, 'height': 900}, color_scheme='light')
        l = await cx.new_page(); l.on('pageerror', lambda e: errs.append('light: ' + str(e)))
        await l.add_init_script(mock('listed'))
        await l.goto(URL + '#p-pd'); await l.wait_for_selector('.doc h1', timeout=8000); await l.wait_for_timeout(200)
        ok('light: follows the device', await l.evaluate('getComputedStyle(document.body).backgroundColor') == 'rgb(246, 245, 242)')
        await l.screenshot(path=OUT + 's5-define-desk-light.png')
        await cx.close()

        # ---------- Phones: 390 and 360, dark and light ----------
        for (wd, ht, scheme) in [(390, 844, 'dark'), (360, 800, 'light')]:
            tag = f'{wd}'
            mc = await b.new_context(viewport={'width': wd, 'height': ht}, color_scheme=scheme, has_touch=True, is_mobile=True)
            m = await mc.new_page(); m.on('pageerror', lambda e, t=tag: errs.append(t + ': ' + str(e)))
            await m.add_init_script(mock('none'))
            await m.goto(URL + '#p-pd'); await m.wait_for_selector('.doc h1', timeout=8000); await m.wait_for_timeout(250)
            vt = await m.eval_on_selector_all('.btabs.b3 button', 'els => els.map(e => [e.innerText.trim(), e.getAttribute("aria-selected"), e.getBoundingClientRect().height])')
            ok(f'{tag}: Document, Coach, Checklist tabs; Document first', [x[0] for x in vt] == ['Document', 'Coach', 'Checklist'] and vt[0][1] == 'true' and all(x[2] >= 44 for x in vt))
            ok(f'{tag}: document full screen, side panel hidden', await m.is_visible('.docmain') and await m.is_hidden('.dside') and await m.is_hidden('.stabs'))
            hs = await m.eval_on_selector_all('.doctabs button, .dtools .btn', 'els => els.filter(e => e.offsetParent).map(e => e.getBoundingClientRect().height)')
            ok(f'{tag}: doc tabs and buttons 44px or more', hs and min(hs) >= 44)
            ok(f'{tag}: no sideways scroll on the document', await m.evaluate('document.documentElement.scrollWidth <= innerWidth'))
            await m.screenshot(path=OUT + f's5-define-{tag}-{scheme}.png')
            await m.tap('.btabs [data-tab="coach"]'); await m.wait_for_timeout(150)
            cb = await boxes(m, '.sidecoach .compose')
            ok(f'{tag}: Coach is one tap away; composer above the bottom bar', await m.is_visible('.sidecoach') and await m.is_hidden('.docmain') and cb[0] and cb[0]['b'] <= ht - 72 + 1)
            ok(f'{tag}: no sideways scroll on the coach', await m.evaluate('document.documentElement.scrollWidth <= innerWidth'))
            await m.screenshot(path=OUT + f's5-coach-{tag}-{scheme}.png')
            await m.tap('.btabs [data-tab="checklist"]'); await m.wait_for_timeout(150)
            ok(f'{tag}: Checklist tab', await m.is_visible('.sidelist') and await m.is_hidden('.sidecoach') and await m.locator('.sidelist .checks li').count() == 4)
            await m.goto(URL + '#p-pg'); await m.wait_for_selector('.doctabs', timeout=8000); await m.wait_for_timeout(150)
            ok(f'{tag}: another project opens on its document', await m.is_visible('.docmain') and await m.get_attribute('.btabs [data-tab="doc"]', 'aria-selected') == 'true')
            await m.goto(URL + '#p-pd'); await m.wait_for_selector('.doc h1', timeout=8000)
            await m.tap('.dtools [data-act="editdoc"]'); await m.wait_for_timeout(150)
            ok(f'{tag}: edit on a phone', await m.is_visible('#doc-editor') and await m.evaluate('document.documentElement.scrollWidth <= innerWidth'))
            await m.tap('.dtools [data-act="donedit"]')
            await m.goto(URL + '#p-ps'); await m.wait_for_selector('.shipmain', timeout=8000); await m.wait_for_timeout(150)
            ok(f'{tag}: ship checklist first, rows 44px or more', await m.evaluate('(() => { const a = document.querySelector(".shipmain .checks"), b = document.querySelector(".pside"); return a.getBoundingClientRect().top < b.getBoundingClientRect().top; })()')
               and min(await m.eval_on_selector_all('.shipmain .checks label', 'els => els.map(e => e.getBoundingClientRect().height)')) >= 44
               and await m.evaluate('document.documentElement.scrollWidth <= innerWidth'))
            await m.screenshot(path=OUT + f's5-ship-{tag}-{scheme}.png')
            await mc.close()

        await b.close()
        passed = sum(1 for _, c in checks if c)
        print(f'{passed}/{len(checks)} passed')
        for nm, c in checks:
            if not c: print('  FAILED:', nm)
        print('page errors:', errs or 'none')

asyncio.run(main())
