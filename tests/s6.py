"""S6 browser test: AI drafts, with a mocked db, a mocked streaming Claude and a mocked laptop file server."""
import asyncio, json, os
from pathlib import Path
from playwright.async_api import async_playwright
HERE = Path(__file__).resolve().parent
URL = (HERE.parent / 'src' / 'index.html').as_uri()
OUT = str(HERE / 'out') + os.sep            # screenshots land in tests/out/
os.makedirs(OUT, exist_ok=True)
LAUNCH = {'executable_path': os.environ['CHROME']} if os.environ.get('CHROME') else {}   # optional: your own Chrome

PRD = "# Matchbook\n\nFor Saturday 5-a-side players. Captains log goals.\n\n## Goals\n1. Log goals live\n"
ADR1 = "# 0001: Use Firebase\n\nStatus: Accepted · 2026-11-10\n\n## Context\n\nWe need auth and a database on a free tier.\n\n## Decision\n\nFirebase Spark plan.\n"

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

B = lambda d: '\n<studio>' + json.dumps(d) + '</studio>'
DN = {"users": "Captains and 12 players", "scope": "Log goals and assists live; season table", "nongoals": "Player accounts", "musts": "", "nfrs": "", "open": ""}
CHAT = {'messages': [
    {'id': 'm1', 'role': 'user', 'text': 'Interview me about what v1 should do.', 'at': 1},
    {'id': 'm2', 'role': 'coach', 'text': "Let's pin down the scope first.", 'at': 2, 'meta': {'mode': 'interview', 'reason': '', 'q': {'n': 1, 'of': 3, 'text': 'Who confirms a match result?'}, 'choices': ['Both captains', 'The referee'], 'done': False, 'oneliner': '', 'scores': None}},
    {'id': 'm3', 'role': 'user', 'text': 'Both captains', 'at': 3, 'choice': True},
    {'id': 'm4', 'role': 'coach', 'text': 'Here is what I learned: captains log goals live and both confirm the result. No player accounts in v1.', 'at': 4, 'meta': {'mode': 'chat', 'reason': '', 'q': None, 'choices': [], 'done': False, 'oneliner': '', 'scores': None}}],
    'notes': DN, 'free': False, 'trimmed': 0, 'updatedAt': 4}
SEED = {
    'projects/pd': {'name': 'Matchbook', 'phase': 'define', 'completed': {'discover': True}, 'checks': {'define': [False, False, False, False]}, 'oneLiner': 'For Saturday 5-a-side players, who argue over who scored, Matchbook lets captains log goals live, unlike the WhatsApp tally.', 'repo': 'C:\\Projects\\matchbook', 'triage': {'scores': {'pain': 5, 'access': 5, 'scope': 3, 'cost': 4, 'learning': 5, 'motivation': 4}, 'verdict': 'promising', 'reasoning': '', 'tags': [], 'at': 1, 'from': 'coach'}, '__ago': 3600000},
    'chats/pd': {'messages': [], 'notes': {'who': 'A fixed group of 12 Saturday players'}, 'free': False, 'trimmed': 0, 'updatedAt': 5},
    'chats/pd~define': CHAT,
    'docs/pd~prd': {'pid': 'pd', 'phase': 'define', 'key': 'prd', 'text': PRD, '__ago': 7200000},
    'projects/pg': {'name': 'Hall registration', 'phase': 'design', 'completed': {'discover': True, 'define': True}, 'checks': {'design': [False, False, False]}, 'oneLiner': '', 'repo': 'C:\\Projects\\hall', '__ago': 7200000},
    'docs/pg~prd': {'pid': 'pg', 'phase': 'define', 'key': 'prd', 'text': '# Hall registration\n\nStudents register for halls without queues.', '__ago': 86400000},
    'docs/pg~adr-a1': {'pid': 'pg', 'phase': 'design', 'key': 'adr-a1', 'kind': 'adr', 'n': 1, 'text': ADR1, '__ago': 86400000},
    'projects/pn': {'name': 'Quiet one', 'phase': 'define', 'completed': {'discover': True}, 'checks': {}, 'oneLiner': '', '__ago': 86400000},
}
FILES = {}


def mock(host='listed'):
    return MOCK.replace('%FILES%', json.dumps(FILES)).replace('%SEED%', json.dumps(SEED)).replace('%HOST%', json.dumps(host))


D_PRD = "# Matchbook: PRD\n\n## One-liner\nFor Saturday 5-a-side players, who argue over who scored, Matchbook lets captains log goals live, unlike the WhatsApp tally.\n\n## Problem\n- Goals posted in WhatsApp get disputed\n\n## Goals (v1)\n1. Captains log goals live\n2. Both captains confirm the result\n\n## Non-goals (v1)\n- Player accounts\n\n## Success metric\nTBD: how many matches a month should be logged\n\n## Open questions\n- TBD: who confirms when a captain is missing\n"
D_PRD2 = D_PRD.replace('Both captains confirm the result', 'Both captains confirm, then it locks')
D_STORIES = "Here's the draft:\n\n```markdown\n# Matchbook · stories\n\n## Must\n- [ ] S1 · Log a goal\n  As a captain, I want to log a goal live, so that nobody argues later.\n  - Given a match is on, when I tap a player, then a goal is added\n- [ ] S2 · Confirm a match\n  As a captain, I want to confirm the result, so that it locks.\n\n## Should\n- [ ] S3 · Season table\n```"
D_NFRS = "# Matchbook: NFRs\n\nWhat v1 must hold to.\n\n| NFR | Requirement | How we'll check |\n| --- | --- | --- |\n| Cost | $0 on free tiers | No paid service |\n| Reachability | Works on MTN data | Test on a phone |\n"
D_ADR = "# 0002: Use Cloudflare Pages\n\nStatus: Proposed · 2026-11-13\n\n## Context\nStatic hosting.\n\n## Decision\nCloudflare Pages.\n\n## Alternatives considered\n- Netlify: fine too, but no reason to switch\n\n## Consequences\nFree, global.\n"
D_ARCH = "# Hall registration: architecture\n\n## Tier\nA static PWA plus Firebase.\n\n## Context diagram\n```mermaid\nflowchart LR\n  Student --> App --> Firebase\n```\n"
D_LONG = "# Long\n\n" + ("A long paragraph that keeps going. " * 60)
C_READY = "I can draft the PRD and the user stories now." + B({"mode": "chat", "notes": DN, "ready": ["prd", "stories", "bogus"]})
C_READY2 = "The NFRs are clear enough to draft too." + B({"mode": "chat", "notes": DN, "ready": ["nfrs"]})


async def wait_draft(pg, key_sel='#dp-h, #rv-h'):   # a new document's draft, or (S7) a review of a saved one
    await pg.wait_for_selector(key_sel, timeout=8000); await pg.wait_for_timeout(80)


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(**LAUNCH)
        errs, checks = [], []

        def ok(name, cond):
            checks.append((name, bool(cond)))
            print(('PASS ' if cond else 'FAIL ') + name)

        ctx = await b.new_context(viewport={'width': 1440, 'height': 900}, color_scheme='dark')
        d = await ctx.new_page(); d.on('pageerror', lambda e: errs.append('desk: ' + str(e)))
        await d.add_init_script(mock('listed'))
        await d.goto(URL + '#p-pd'); await d.wait_for_selector('.doc h1', timeout=8000); await d.wait_for_timeout(250)

        # 1. Draft the PRD over a saved version
        ok('PRD: Draft with Claude in the toolbar', await d.is_visible('.dtools [data-act="draftdoc"]') and (await d.inner_text('.dtools [data-act="draftdoc"]')) == 'Draft with Claude')
        await d.evaluate(f'window.__tick = 25; window.__step = 14; window.__replies.push({json.dumps(D_PRD)})')
        await d.click('.dtools [data-act="draftdoc"]')
        await d.wait_for_selector('#draft-live', timeout=3000)
        ok('drafting: panel, Stop, tab says drafting', 'Claude is drafting the PRD' in await d.inner_text('.dpanel') and await d.is_visible('.dtools [data-act="stopdraft"]')
           and 'drafting…' in await d.inner_text('.doctabs [data-tab="prd"]'))
        ok('drafting: the saved PRD is untouched', (await d.evaluate('window.__store["docs/pd~prd"].text')) == PRD)
        await wait_draft(d)
        seen = await d.evaluate('window.__seen')
        ok('drafting: streams into the page', any('Matchbook: PRD' in s for s in seen) and any(len(s) < len(D_PRD) - 50 for s in seen if s.strip()))
        c = (await d.evaluate('window.__calls'))[-1]
        pr = c['input']
        ok('draft call: one prompt, default tier, no cache', isinstance(pr, str) and c['opts'] == {'modelTier': 'default', 'cache': False} and pr.startswith('You are drafting docs/PRD.md'))
        ok('draft prompt: project facts and both coaches\' notes', 'Matchbook lets captains log goals live' in pr and 'A fixed group of 12' in pr and 'Not in v1: Player accounts' in pr and '26/30' in pr)
        ok('draft prompt: the chat, with the coach\'s questions', 'Builder: Both captains' in pr and '(asks) Who confirms a match result?' in pr and 'both confirm the result' in pr)
        ok('draft prompt: revises the saved version', '--- docs/PRD.md (current) ---\n' + PRD.strip() in pr and 'Revise it' in pr)
        ok('draft prompt: other docs, shape and the TBD rule', '--- docs/stories.md ---\n(not written yet)' in pr and 'Non-goals (v1)' in pr and 'starts with "TBD:"' in pr and 'Never invent' in pr)
        st = await d.evaluate('window.__store["docs/pd~prd"]')
        ok('draft saved beside the text, text unchanged', st['draft']['text'] == D_PRD.strip() and st['text'] == PRD and st['draft']['basedOn'])
        pnl = await d.inner_text('.rbar')
        ok('a saved PRD\'s draft opens as a review (S7): TBD count, saved version safe', "Claude's draft:" in pnl and '2 TBD lines' in pnl and 'changes only as you accept' in pnl
           and await d.is_visible('.rbar [data-act="acceptall"]'))
        ok('review shown, tab counts the changes', await d.locator('.doc.review .chg').count() >= 1 and 'change' in await d.inner_text('.doctabs [data-tab="prd"]'))
        await d.click('.rbar [data-act="acceptall"]'); await d.click('.rbar [data-act="finishreview"]'); await d.wait_for_timeout(300)
        st = await d.evaluate('window.__store["docs/pd~prd"]')
        ok('Accept all, then Finish: it becomes the saved PRD', st['text'].strip() == D_PRD.strip() and 'draft' not in st and "Reviewed Claude's draft just now" in await d.inner_text('.dmeta')
           and 'change' not in await d.inner_text('.doctabs [data-tab="prd"]') and await d.query_selector('.rbar') is None)
        await d.screenshot(path=OUT + 's6-prd-used.png')

        # 2. Stories from scratch; the reply is wrapped in a fence with a note
        await d.click('.doctabs [data-tab="stories"]'); await d.wait_for_timeout(100)
        ok('empty doc after a chat: Draft with Claude is the primary action', await d.is_visible('.dempty .btn.primary[data-act="draftdoc"]') and not await d.is_visible('.dempty .btn.primary[data-act="editdoc"]'))
        await d.evaluate(f'window.__tick = 6; window.__step = 30; window.__replies.push({json.dumps(D_STORIES)})')
        await d.click('.dempty [data-act="draftdoc"]'); await wait_draft(d)
        pr = (await d.evaluate('window.__calls'))[-1]['input']
        ok('stories prompt: the PRD he just approved, the stories shape', '--- docs/PRD.md ---\n# Matchbook: PRD' in pr and '- [ ] S1 · <short title>' in pr and "There's no saved version" in pr)
        dr = (await d.evaluate('window.__store["docs/pd~stories"]'))['draft']['text']
        ok('reply cleaned: no note, no fence', dr.startswith('# Matchbook · stories') and not dr.rstrip().endswith('```') and "Here's the draft" not in dr)
        ok('new doc: nothing saved until used', 'Nothing is saved until you use it' in await d.inner_text('.dpanel') and await d.query_selector('.vseg') is None
           and (await d.evaluate('window.__store["docs/pd~stories"].text')) == '')
        await d.click('.dpanel [data-act="usedraft"][data-edit="1"]'); await d.wait_for_timeout(150)
        ok('Use and edit: the editor opens on the draft', await d.evaluate('document.activeElement.id') == 'doc-editor' and (await d.input_value('#doc-editor')).startswith('# Matchbook · stories'))
        await d.keyboard.press('Escape'); await d.wait_for_timeout(300)
        ok('stories render as slice lines', await d.locator('article.doc li.task').count() == 3 and (await d.evaluate('window.__store["docs/pd~stories"].text')).startswith('# Matchbook · stories'))

        # 3. A failed draft, then Try again, then Discard
        await d.click('.doctabs [data-tab="nfrs"]'); await d.wait_for_timeout(100)
        await d.evaluate("window.__mode = 'rate_limited'")
        await d.click('.dempty [data-act="draftdoc"]'); await d.wait_for_selector('.docbody .errbox', timeout=3000)
        ok('failed draft: explained, with Try again', "Claude couldn't draft the NFRs." in await d.inner_text('.docbody .errbox') and 'usage limit' in await d.inner_text('.docbody .errbox'))
        await d.evaluate(f'window.__replies.push({json.dumps(D_NFRS)})')
        await d.click('.docbody .errbox [data-act="draftdoc"]'); await wait_draft(d)
        ok('Try again drafts it', await d.query_selector('.docbody .errbox') is None and await d.locator('article.doc table tbody tr').count() == 2)
        await d.click('.dpanel [data-act="discarddraft"]'); await d.wait_for_timeout(300)
        ok('Discard: back to empty, nothing stored', await d.is_visible('.dempty') and 'draft' not in (await d.evaluate('window.__store["docs/pd~nfrs"]') or {}))

        # 4. Stop part-way keeps nothing
        await d.evaluate(f'window.__tick = 40; window.__step = 6; window.__replies.push({json.dumps(D_LONG)})')
        await d.click('.dempty [data-act="draftdoc"]'); await d.wait_for_timeout(500)
        await d.click('.dtools [data-act="stopdraft"]'); await d.wait_for_timeout(250)
        ok('Stop: nothing kept', await d.query_selector('#draft-live') is None and await d.is_visible('.dempty') and 'Stopped' in await d.inner_text('.toast')
           and 'draft' not in (await d.evaluate('window.__store["docs/pd~nfrs"]') or {}))
        await d.evaluate('window.__tick = 6; window.__step = 30')

        # 5. Editing the saved version after a draft warns before using it
        await d.click('.doctabs [data-tab="prd"]'); await d.wait_for_timeout(100)
        await d.evaluate(f'window.__replies.push({json.dumps(D_PRD2)})')
        await d.click('.dtools [data-act="draftdoc"]'); await wait_draft(d)
        await d.evaluate("window.__remote('docs/pd~prd', Object.assign({}, window.__store['docs/pd~prd'], {text: window.__store['docs/pd~prd'].text + '\\nA line of mine.', updatedAt: Date.now() + 5000}))")
        await d.wait_for_timeout(400)
        ok('edited since the draft: the review says so', 'You edited the saved version after Claude drafted this' in await d.inner_text('.rbar'))
        await d.click('.rbar [data-act="rejectrest"]'); await d.wait_for_timeout(300)
        ok('discard keeps his edit', 'A line of mine.' in (await d.evaluate('window.__store["docs/pd~prd"].text')))

        # 6. The coach offers drafts; only the latest offer shows
        await d.evaluate(f'window.__replies.push({json.dumps(C_READY)})')
        await d.fill('#coach-input', 'Can you draft the PRD and the stories?'); await d.keyboard.press('Enter')
        await d.wait_for_selector('.sidecoach .offer', timeout=5000); await d.wait_for_timeout(100)
        cp = (await d.evaluate('window.__calls'))[-1]['input'][0]['content']
        ok('coach prompt: ready in the block and what it means', '"ready":[]}</studio>' in cp and 'ready: the documents you could draft now from what you know (prd, stories, nfrs)' in cp and "Don't write whole documents in the chat" in cp)
        btns = await d.eval_on_selector_all('.sidecoach .offer button', 'els => els.map(e => e.innerText)')
        ok('offer: one button per document it named, unknown keys dropped', btns == ['Draft the PRD', 'Draft the user stories'])
        ok('offer saved with the reply', (await d.evaluate('window.__store["chats/pd~define"].messages.slice(-1)[0].meta.ready')) == ['prd', 'stories', 'bogus'][:2])
        await d.evaluate(f'window.__replies.push({json.dumps(C_READY2)})')
        await d.fill('#coach-input', 'And the NFRs?'); await d.keyboard.press('Enter')
        await d.wait_for_function('document.querySelectorAll(".sidecoach .offer").length === 1 && document.querySelector(".sidecoach .offer").innerText.includes("NFRs")', timeout=5000)
        ok('only the latest offer shows', await d.locator('.sidecoach .offer').count() == 1)
        await d.evaluate(f'window.__replies.push({json.dumps(D_NFRS)})')
        await d.click('.sidecoach .offer [data-act="draftdoc"]'); await wait_draft(d)
        ok('offer: drafts that document and shows it', (await d.get_attribute('.doctabs [data-tab="nfrs"]', 'aria-selected')) == 'true' and 'NFRs' in await d.inner_text('article.doc h1'))
        ok('offer: then points to the draft', 'Open the draft of the NFRs' in await d.inner_text('.sidecoach .offer'))
        await d.screenshot(path=OUT + 's6-define-desk.png')

        # 7. Design: ADRs and architecture
        await d.goto(URL + '#p-pg'); await d.wait_for_selector('.doctabs', timeout=8000); await d.wait_for_timeout(200)
        await d.click('.doctabs [data-tab="adr"]'); await d.wait_for_timeout(100)
        await d.evaluate(f'window.__replies.push({json.dumps(D_ADR)})')
        await d.click('.dtools [data-act="draftdoc"][data-k="adr"]'); await wait_draft(d)
        pr = (await d.evaluate('window.__calls'))[-1]['input']
        ok('Draft an ADR: a new ADR 0002', pr.startswith('You are drafting docs/adr/0002-untitled.md') and 'One decision only: the most recent decision' in pr and "There's no saved version" in pr)
        ok('ADR prompt: Define docs and earlier ADRs', 'Students register for halls' in pr and '--- docs/adr/0001-use-firebase.md ---' in pr)
        await d.click('.dpanel .btn.primary'); await d.wait_for_timeout(200); await d.click('[data-act="closeadr"]'); await d.wait_for_timeout(100)
        ok('ADR used: listed with its title', 'Use Cloudflare Pages' in await d.inner_text('.adrlist li:nth-child(2)') and 'Proposed' in await d.inner_text('.adrlist li:nth-child(2)'))
        await d.click('.adrlist li:first-child button'); await d.click('.dtools [data-act="draftdoc"]'); await d.wait_for_timeout(50)
        await d.wait_for_selector('#dp-h, #rv-h', timeout=8000)
        pr = (await d.evaluate('window.__calls'))[-1]['input']
        ok('redrafting ADR 0001 keeps its decision and current text', 'One decision only: "Use Firebase"' in pr and '--- docs/adr/0001-use-firebase.md (current) ---' in pr)
        await d.click('.rbar [data-act="rejectrest"]'); await d.click('[data-act="closeadr"]')
        await d.click('.doctabs [data-tab="architecture"]'); await d.wait_for_timeout(100)
        await d.evaluate(f'window.__replies.push({json.dumps(D_ARCH)})')
        await d.click('.dempty [data-act="draftdoc"]'); await wait_draft(d)
        pr = (await d.evaluate('window.__calls'))[-1]['input']
        ok('architecture prompt: Define docs, ADRs, the tier ladder', '--- docs/PRD.md ---\n# Hall registration' in pr and '0002-use-cloudflare-pages.md' in pr and 'static page or PWA' in pr)
        ok('architecture draft keeps its diagram source', 'flowchart LR' in await d.inner_text('article.doc pre'))
        await d.screenshot(path=OUT + 's6-design-desk.png')

        # 8. A waiting draft survives a reload (a fresh page gets the mock db's copy)
        await d.wait_for_timeout(300); snap = await d.evaluate('localStorage.getItem("__mockdb")')
        await d.close()
        d = await ctx.new_page(); d.on('pageerror', lambda e: errs.append('desk: ' + str(e)))
        await d.add_init_script('if (!window.name){ window.name = "seeded"; localStorage.setItem("__mockdb", %s); }' % json.dumps(snap))
        await d.add_init_script(mock('listed'))
        await d.goto(URL + '#p-pg'); await d.wait_for_selector('.doctabs', timeout=8000); await d.wait_for_timeout(250)
        ok('reload: the draft still waits', 'draft' in await d.inner_text('.doctabs [data-tab="architecture"]') and "Claude's draft" in await d.inner_text('.dpanel'))
        await ctx.close()

        # 9. No chat yet, and no Claude
        cx = await b.new_context(viewport={'width': 1440, 'height': 900})
        q = await cx.new_page(); q.on('pageerror', lambda e: errs.append('quiet: ' + str(e)))
        await q.add_init_script(mock('none'))
        await q.goto(URL + '#p-pn'); await q.wait_for_selector('.dempty', timeout=8000)
        ok('no chat yet: Start writing first, Draft with Claude offered', await q.is_visible('.dempty .btn.primary[data-act="editdoc"]') and await q.is_visible('.dempty [data-act="draftdoc"]'))
        await cx.close()
        cx = await b.new_context(viewport={'width': 1440, 'height': 900})
        q = await cx.new_page(); q.on('pageerror', lambda e: errs.append('noclaude: ' + str(e)))
        await q.add_init_script(mock('none')); await q.add_init_script('window.__noSample = true;')
        await q.goto(URL + '#p-pd'); await q.wait_for_selector('.doc h1', timeout=8000); await q.wait_for_timeout(200)
        ok('no Claude: no draft buttons', await q.query_selector('[data-act="draftdoc"]') is None)
        await q.click('.doctabs [data-tab="nfrs"]')
        ok('no Claude: Start writing is the primary action', await q.is_visible('.dempty .btn.primary[data-act="editdoc"]'))
        await cx.close()

        # 10. Phones: the offer switches to the document as it's drafted
        for (wd, ht, scheme) in [(390, 844, 'dark'), (360, 800, 'light')]:
            tag = f'{wd}'
            mc = await b.new_context(viewport={'width': wd, 'height': ht}, color_scheme=scheme, has_touch=True, is_mobile=True)
            m = await mc.new_page(); m.on('pageerror', lambda e, t=tag: errs.append(t + ': ' + str(e)))
            await m.add_init_script(mock('none'))
            await m.goto(URL + '#p-pd'); await m.wait_for_selector('.doc h1', timeout=8000); await m.wait_for_timeout(200)
            await m.tap('.btabs [data-tab="coach"]'); await m.wait_for_timeout(100)
            await m.evaluate(f'window.__replies.push({json.dumps(C_READY)})')
            await m.fill('#coach-input', 'Draft them please'); await m.tap('.compose [type=submit]')
            await m.wait_for_selector('.sidecoach .offer', timeout=5000); await m.wait_for_timeout(100)
            hs = await m.eval_on_selector_all('.sidecoach .offer .btn', 'els => els.map(e => e.getBoundingClientRect().height)')
            ok(f'{tag}: offer buttons 44px or more', hs and min(hs) >= 44 and await m.evaluate('document.documentElement.scrollWidth <= innerWidth'))
            await m.screenshot(path=OUT + f's6-offer-{tag}-{scheme}.png')
            await m.evaluate(f'window.__tick = 25; window.__step = 14; window.__replies.push({json.dumps(D_STORIES)})')
            await m.tap('.sidecoach .offer [data-k="stories"]'); await m.wait_for_timeout(150)
            ok(f'{tag}: tapping it opens the document as Claude writes', await m.is_visible('.docmain') and await m.is_hidden('.dside') and await m.is_visible('#draft-live'))
            await wait_draft(m)
            hs = await m.eval_on_selector_all('.dpanel .btn', 'els => els.map(e => e.getBoundingClientRect().height)')
            ok(f'{tag}: draft actions 44px or more, no sideways scroll', min(hs) >= 44 and await m.evaluate('document.documentElement.scrollWidth <= innerWidth'))
            await m.screenshot(path=OUT + f's6-draft-{tag}-{scheme}.png')
            await m.tap('.dpanel .btn.primary'); await m.wait_for_timeout(200)
            ok(f'{tag}: used on a phone', await m.locator('article.doc li.task').count() == 3)
            await mc.close()

        await b.close()
        passed = sum(1 for _, c in checks if c)
        print(f'{passed}/{len(checks)} passed')
        for nm, c in checks:
            if not c: print('  FAILED:', nm)
        print('page errors:', errs or 'none')

asyncio.run(main())
