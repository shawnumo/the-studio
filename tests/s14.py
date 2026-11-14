"""S14 browser test: Ship's launch checklist, feedback and backlog, the changelog, the Shipped list and the next version,
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
REPO = 'C:\\Projects\\siwes-logbook'
SHIP_AT = int(datetime.datetime(2026, 11, 5, 12).timestamp() * 1000)   # when the shipped project's v1.0.0 went out

PROGRESS = """# Progress log

Newest first.

## 2026-11-12 · S3 · Weekly view
- Built: seven-day grid; empty days are flagged.
- Tests: 31 passed
- Check on your phone: open this week.
- Next: S4 · Supervisor signs off the week

## 2026-11-08 · S2 · Daily entry
- Built: entry form saves every 2 seconds; a reload keeps the draft.
- Tests: 24 passed

## 2026-11-03 · S1 · Sign-in
- Built: matric number plus password; a wrong format shows an inline error.
- Tests: 15 passed

## 2026-10-30 · S0 · Walking skeleton
- Built: Vite app live on Cloudflare Pages, CI green.
- Tests: 3 passed
"""
FILES = {
    REPO + '\\docs\\stories.md': "# siwes · slices\n\n## Must\n- [x] S0 · Walking skeleton\n- [x] S1 · Sign-in\n- [x] S2 · Daily entry\n- [x] S3 · Weekly view\n",
    REPO + '\\docs\\progress.md': PROGRESS, REPO + '\\.git\\HEAD': 'ref: refs/heads/main\n', REPO + '\\CLAUDE.md': '# siwes\n\n## Commands\n- Test: `npm test`\n',
}
DRAFT = "## [1.0.0] - 2026-11-14\n### Added\n- Sign in with your matric number and password.\n- Log each day's work; it saves as you type.\n- See your week at a glance, with missing days flagged."
DRAFT2 = "## [1.0.0] - 2026-11-14\n### Added\n- Sign in, log your days and see your week."

def entry(date, sid, title, built):
    return {'date': date, 'id': sid, 'title': title, 'built': built, 'tests': '9 passed', 'check': '', 'next': '', 'commit': ''}

def proj(name, phase='ship', **kw):
    done = {k: True for k in ['discover', 'define', 'design', 'build', 'ship'][:['discover', 'define', 'design', 'build', 'ship'].index(phase)]}
    return {'name': name, 'phase': phase, 'completed': done, 'checks': {}, 'oneLiner': 'For SIWES students, who lose daily logs, an app that keeps them.', '__ago': DAY, **kw}

SEED = {
    'projects/pl': proj('SIWES logbook', repo=REPO, liveUrl='https://siwes.pages.dev'),
    # shipped on Nov 5, with feedback and a backlog
    'projects/pdone': {**proj('Mafia', repo='C:\\Projects\\mafia', liveUrl='https://mafia-game.pages.dev/'), 'completed': {k: True for k in ['discover', 'define', 'design', 'build', 'ship']},
                       'version': '1.0.0', 'versions': [{'v': '1.0.0', 'at': SHIP_AT, 'url': 'https://mafia-game.pages.dev/'}],
                       'feedback': [{'id': 'f1', 'who': 'Dami', 'text': 'Night phase timer is too short for six players', 'at': SHIP_AT + DAY, 'bl': 'b1'},
                                    {'id': 'f2', 'who': '', 'text': 'Loved the role reveal', 'at': SHIP_AT + 2 * DAY, 'bl': ''}],
                       'backlog': [{'id': 'b1', 'text': 'Let the host set the night timer', 'who': 'Dami', 'from': 'f1', 'at': SHIP_AT + DAY}],
                       'launch': [{'id': 'l0', 't': 'The live URL opens on a phone over mobile data', 'g': 'launch', 'done': True}]},
    'syncs/pdone': {'repo': 'C:\\Projects\\mafia', 'repoName': 'mafia', 'via': 'laptop', 'at': NOW - DAY, 'slices': [], 'marks': {}, 'branch': 'main', 'commits': [],
                    'log': [entry('2026-11-10', 'S9', 'Host settings', 'host can set the night timer'), entry('2026-11-07', 'S8', 'Rejoin', 'players rejoin after a dropped connection'),
                            entry('2026-11-05', 'S7', 'Launch fixes', 'last fixes before launch'), entry('2026-11-04', 'S6', 'Roles', 'role reveal animation')]},
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
  window.__store = S0; window.__remote = (k, d) => { S0[k] = d; persist(); notify(k); };   // a write from another device
  window.__clip = null; window.__clipFail = false;
  Object.defineProperty(navigator, 'clipboard', {configurable:true, value:{writeText: async t => { if (window.__clipFail) throw new Error('denied'); window.__clip = t; }}});
  window.__calls = []; window.__replies = []; window.__mode = 'ok'; window.__seen = [];
  const sample = (input, opts) => new Promise((resolve, reject) => {
    window.__calls.push({input: JSON.parse(JSON.stringify(input))});
    if (window.__mode !== 'ok'){ const code = window.__mode; window.__mode = 'ok'; setTimeout(() => reject({code, message:'mock'}), 30); return; }
    const full = window.__replies.length ? window.__replies.shift() : 'Okay.\n<studio>{"mode":"chat"}</studio>';
    let i = 0; const step = window.__step || 20, tick = window.__tick || 6;
    opts.onText && opts.onText({text:'Thinking...', delta:''});
    const t = setInterval(() => {
      i = Math.min(full.length, i + step);
      opts.onText && opts.onText({text: full.slice(0, i), delta: ''});
      const live = document.querySelector('#cl-live'); if (live) window.__seen.push(live.innerText);
      if (i >= full.length){ clearInterval(t); resolve({text: full}); }
    }, tick);
    if (opts.signal) opts.signal.addEventListener('abort', () => { clearInterval(t); reject({code:'aborted'}); });
  });
  sample.json = () => Promise.reject({code:'unavailable'});
  const FILES = %FILES%;
  window.__files = FILES; window.__mcp = []; window.__host = %HOST%; window.__fail = null;
  const mcp = {
    async listTools(){ return {servers: window.__host === 'listed' ? [{server:'host:filesystem', authStatus:'unknown', tools:[{name:'read_text_file', description:''},{name:'edit_file', description:''}]}] : []}; },
    async callTool(server, tool, input){
      window.__mcp.push({tool, input});
      if (window.__host !== 'listed') throw {code:'server_not_connected', message:'no host'};
      if (window.__fail){ const f = window.__fail; window.__fail = null; throw f; }
      const text = FILES[input.path];
      if (text === undefined) throw {code:'tool_error', message:"ENOENT: no such file or directory, open '" + input.path + "'"};
      if (tool === 'read_text_file'){ let t = text; if (input.tail) t = t.split('\n').slice(-input.tail).join('\n'); return {content:[{type:'text', text:t}], payload:{content:t}}; }
      throw {code:'not_in_manifest', message:'no'};
    },
    watchTool(){ return () => {}; }, async invalidate(){}
  };
  window.claude = { use: async n => n === 'db' ? db : n === 'sample' ? sample : n === 'mcp' ? mcp : null };
})();
"""

def mock(host='listed', seed=None):
    return MOCK.replace('%SEED%', json.dumps(SEED if seed is None else seed)).replace('%FILES%', json.dumps(FILES)).replace('%HOST%', json.dumps(host))

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
        async def P(pg, k='pl'):
            return await pg.evaluate(f'window.__store["projects/{k}"]')

        # ---------- Desktop 1440, dark, in the Claude app ----------
        ctx = await b.new_context(viewport={'width': 1440, 'height': 900}, color_scheme='dark')
        d = await ctx.new_page(); d.on('pageerror', lambda e: errs.append('desk: ' + str(e)))
        await d.add_init_script(mock())
        await d.goto(URL + '#p-pl'); await d.wait_for_selector('.shipmain .lsec', timeout=8000); await d.wait_for_timeout(750)

        # Launch checklist
        ok('Ship opens on the exit checklist, then the launch checklist', await d.evaluate('(() => { const s = [...document.querySelectorAll(".shipmain section")].map(x => x.querySelector("h2") && x.querySelector("h2").textContent); return s[0] === "Exit checklist" && s[1] === "Launch checklist"; })()'))
        ok('header shows the version', 'version 1.0.0' in await d.inner_text('.top.ph .tt'))
        first = d.locator('.shipmain .checks.big input[data-check="0"]')
        ok('"The launch checklist passes" ticks itself, and says so', await first.is_disabled() and 'Ticks itself when every launch check is ticked.' in await d.inner_text('.shipmain .checks.big'))
        ok('default list: 8 launch and 13 security checks', await d.locator('.lchecks[aria-label="Launch checks"] li').count() == 8 and await d.locator('.lchecks[aria-label="Security checks"] li').count() == 13)
        lc = await d.inner_text('.lsec:has(#lc-h)')
        ok('security checks: secrets, npm audit, headers, data rules, NDPA, GitHub', all(s in lc for s in ['No secrets in the repo, its git history', 'npm audit', 'Content-Security-Policy', 'reach only their own data', 'Nigeria Data Protection Act', 'Dependabot']))
        ok('nothing saved until a check changes', (await P(d)).get('launch') is None)
        await d.screenshot(path=OUT + 's14-desk.png')

        await d.click('label:has(input[data-launch="l0"])'); await d.wait_for_timeout(750)
        p = await P(d)
        ok('ticking saves the whole list once', len(p['launch']) == 21 and [x['done'] for x in p['launch'] if x['id'] == 'l0'] == [True])
        ok('focus stays on the ticked check', await d.evaluate('document.activeElement && document.activeElement.dataset.launch === "l0"'))
        await d.keyboard.press('Tab'); await d.keyboard.press('Tab'); await d.keyboard.press('Space'); await d.wait_for_timeout(750)
        ok('keyboard: Tab to the next check and Space ticks it', [x['done'] for x in (await P(d))['launch'] if x['id'] == 'l1'] == [True])
        for lid in await d.eval_on_selector_all('input[data-launch]:not(:checked)', 'els => els.map(e => e.dataset.launch)'):
            await d.click(f'label:has(input[data-launch="{lid}"])'); await d.wait_for_timeout(30)
        await d.wait_for_timeout(750)
        ok('every check ticked: the exit item ticks itself', (await P(d))['checks']['ship'][0] is True and await first.is_checked() and '1/3' in await d.inner_text('.shipmain .lsec .sechead'))
        await d.click('label:has(input[data-launch="s4"])'); await d.wait_for_timeout(750)
        ok('one unticked: the exit item unticks', (await P(d))['checks']['ship'][0] is False and not await first.is_checked())

        await d.click('[data-act="rmlaunch"][data-id="s1"]'); await d.wait_for_timeout(750)
        p = await P(d)
        ok('remove a default check', len(p['launch']) == 20 and not any(x['id'] == 's1' for x in p['launch']) and 'Check removed.' in await toast(d))
        ok('focus moves to the next check', await d.evaluate('document.activeElement && document.activeElement.dataset.launch === "s2"'))
        ok('a link puts it back', 'Put back the 1 default check you removed' in await d.inner_text('.lsec:has(#lc-h)'))
        await d.click('[data-act="resetlaunch"]'); await d.wait_for_timeout(750)
        ids = [x['id'] for x in (await P(d))['launch']]
        ok('put back, in its place, ticks kept', len(ids) == 21 and ids.index('s1') == ids.index('s0') + 1 and [x['done'] for x in (await P(d))['launch'] if x['id'] == 's0'] == [True])
        await d.fill('#al-security', 'Rate-limit the feedback form'); await d.press('#al-security', 'Enter'); await d.wait_for_timeout(750)
        p = await P(d)
        ok('add your own security check', p['launch'][-1]['t'] == 'Rate-limit the feedback form' and p['launch'][-1]['g'] == 'security' and await d.input_value('#al-security') == ''
           and await d.evaluate('document.activeElement.id') == 'al-security' and 'Rate-limit the feedback form' in await d.inner_text('.lchecks[aria-label="Security checks"]'))
        await d.click('#al-launch'); await d.keyboard.type('Custom domain points at the app')
        await d.evaluate("window.__remote('captures/x1', {text:'from my phone', status:'new', createdAt:Date.now()}); 0"); await d.wait_for_timeout(750)
        ok('a re-render from another device keeps a half-typed check', await d.input_value('#al-launch') == 'Custom domain points at the app' and await d.evaluate('document.activeElement.id') == 'al-launch')
        await d.fill('#al-launch', '')

        # Feedback and backlog
        await d.fill('#fb-who', 'Tobi, hostel B'); await d.fill('#fb-text', 'I want to export the week as a PDF for my supervisor')
        await d.click('#fbForm [type="submit"]'); await d.wait_for_timeout(750)
        p = await P(d)
        ok('feedback saved with who and when', p['feedback'][0]['who'] == 'Tobi, hostel B' and p['feedback'][0]['text'].startswith('I want to export') and await d.input_value('#fb-text') == '')
        await d.fill('#fb-text', 'The sign-in button is hard to tap'); await d.press('#fb-text', 'Control+Enter'); await d.wait_for_timeout(750)
        ok('Ctrl+Enter adds feedback, newest first', (await P(d))['feedback'][0]['text'] == 'The sign-in button is hard to tap' and await d.locator('.fblist li').count() == 2)
        await d.click('#fbForm [type="submit"]'); await d.wait_for_timeout(200)
        ok('empty feedback is not added', len((await P(d))['feedback']) == 2 and await d.evaluate('document.activeElement.id') == 'fb-text')
        ok('feedback row: text, who and date, To backlog', 'Tobi, hostel B · ' in await d.inner_text('.fblist') and await d.locator('.fblist [data-act="tobacklog"]').count() == 2)
        fid = (await P(d))['feedback'][1]['id']
        await d.click(f'[data-act="tobacklog"][data-id="{fid}"]'); await d.wait_for_timeout(750)
        p = await P(d)
        ok('To backlog makes a backlog item from it', len(p['backlog']) == 1 and p['backlog'][0]['text'].startswith('I want to export') and p['backlog'][0]['who'] == 'Tobi, hostel B' and 'Added to the backlog.' in await toast(d))
        ok('the feedback row says In backlog', await d.locator('.fblist .inbl').count() == 1 and 'From Tobi, hostel B' in await d.inner_text('.blsec'))
        bid = p['backlog'][0]['id']
        await d.fill(f'#bl-{bid}', 'Export the week as a PDF'); await d.wait_for_timeout(900)
        ok('a backlog item is edited in place', (await P(d))['backlog'][0]['text'] == 'Export the week as a PDF')
        await d.fill('#bl-new', 'Dark mode'); await d.press('#bl-new', 'Enter'); await d.wait_for_timeout(750)
        ok('add straight to the backlog', [x['text'] for x in (await P(d))['backlog']] == ['Export the week as a PDF', 'Dark mode'])
        await d.click(f'[data-act="rmbacklog"][data-id="{bid}"]'); await d.wait_for_timeout(750)
        ok('removing it from the backlog frees the feedback again', len((await P(d))['backlog']) == 1 and await d.locator('.fblist [data-act="tobacklog"]').count() == 2)
        await d.click(f'[data-act="tobacklog"][data-id="{fid}"]'); await d.wait_for_timeout(200)
        f2 = (await P(d))['feedback'][0]['id']
        await d.click(f'[data-act="rmfeedback"][data-id="{f2}"]'); await d.wait_for_timeout(750)
        ok('remove feedback', len((await P(d))['feedback']) == 1)
        await d.screenshot(path=OUT + 's14-desk-feedback.png', full_page=True)

        # Changelog, before the log is read
        cl = d.locator('.clsec')
        ok('changelog: says the progress log is unread, with Sync now', "docs/progress.md hasn't been read yet." in await cl.inner_text() and await d.locator('.clsec [data-act="sync"]').is_visible())
        ok('changelog: Draft waits for the log; writing it yourself works', await d.locator('[data-act="draftcl"]').is_disabled() and 'once that' in await cl.inner_text() and await d.locator('[data-act="writecl"]').is_enabled())
        await d.evaluate("window.__fail = {code:'server_unavailable', message:'x'}; 0")
        await d.click('.clsec [data-act="sync"]'); await d.wait_for_timeout(400)
        ok('changelog: a failed read says so', "Couldn't read the repo." in await cl.inner_text())
        await d.click('.clsec [data-act="sync"]'); await d.wait_for_timeout(600)
        ok('changelog: Sync now reads 4 entries', '4 progress entries, read just now.' in await cl.inner_text() and await d.locator('[data-act="draftcl"]').is_enabled())

        await d.evaluate(f'window.__tick = 25; window.__step = 12; window.__replies.push({json.dumps(DRAFT)})')
        n0 = len(await d.evaluate('window.__calls'))
        await d.click('[data-act="draftcl"]'); await d.wait_for_timeout(250)
        ok('drafting: a blue panel and the entry streaming in', 'Claude is writing the v1.0.0 entry' in await cl.inner_text() and await d.locator('.clsec .ai').count() == 1 and await d.locator('#cl-live[aria-busy="true"]').count() == 1)
        await d.wait_for_selector('#cl-text', timeout=8000); await d.wait_for_timeout(200)
        seen = await d.evaluate('window.__seen')
        ok('drafting: the entry rendered while it streamed', any('Sign in with your matric' in s for s in seen))
        ask = json.dumps((await d.evaluate('window.__calls'))[n0]['input'])
        ok('Claude gets the log, newest first, without test counts', 'Built: seven-day grid' in ask and ask.index('Weekly view') < ask.index('Walking skeleton') and '31 passed' not in ask)
        ok('Claude gets the shape and the first-release rule', '## [1.0.0] - ' in ask and 'This is the first release.' in ask and 'Never invent features' in ask)
        p = await P(d)
        ok('the draft is saved with the version, by Claude', p['changelog']['v'] == '1.0.0' and p['changelog']['by'] == 'claude' and p['changelog']['text'] == DRAFT)
        ok('the entry shows as Drafted by Claude, editable', 'Drafted by Claude' in await cl.inner_text() and await d.input_value('#cl-text') == DRAFT and 'is ready' in await toast(d))

        await d.click('[data-act="copycl"]'); await d.wait_for_timeout(200)
        cp = await d.evaluate('window.__clip')
        ok('Copy prompt: Claude Code adds the entry, commits and pushes', cp.startswith('Add the v1.0.0 entry below to CHANGELOG.md in SIWES logbook.\nWork in C:\\Projects\\siwes-logbook on branch main.')
           and 'create it with the heading "# Changelog"' in cp and "git commit -m 'docs: changelog for v1.0.0'" in cp and 'git push origin main' in cp and cp.rstrip().endswith('missing days flagged.'))
        ok('Copy prompt: a toast names the folder', 'Copied the v1.0.0 changelog prompt. Paste it into Claude Code in C:\\Projects\\siwes-logbook.' in await toast(d))

        await d.click('#cl-text'); await d.keyboard.press('Control+End'); await d.keyboard.type('\n- Works offline.'); await d.wait_for_timeout(900)
        p = await P(d)
        ok('editing saves as you type and marks it yours', p['changelog']['text'].endswith('- Works offline.') and p['changelog']['by'] == 'you')
        await d.evaluate("window.__remote('captures/x2', {text:'another', status:'new', createdAt:Date.now()}); 0"); await d.wait_for_timeout(750)
        ok('a re-render keeps the caret in the entry', await d.evaluate('document.activeElement.id') == 'cl-text' and await d.evaluate('document.activeElement.selectionStart') == len(p['changelog']['text']))
        await d.click('.clsec h2'); await d.wait_for_timeout(400)
        ok('the entry says Edited by you', 'Edited by you' in await cl.inner_text())
        n1 = len(await d.evaluate('window.__calls'))
        await d.click('.clacts [data-act="draftcl"]'); await d.wait_for_timeout(200)
        ok('Draft again asks before replacing your edits', 'Replace your edited entry with a new draft from Claude?' in await cl.inner_text() and len(await d.evaluate('window.__calls')) == n1)
        await d.click('[data-act="keepcl"]'); await d.wait_for_timeout(200)
        ok('Keep mine keeps it', (await P(d))['changelog']['text'].endswith('- Works offline.') and 'Replace your edited' not in await cl.inner_text())
        await d.evaluate("window.__mode = 'rate_limited'; 0")
        await d.click('.clacts [data-act="draftcl"]'); await d.wait_for_timeout(150); await d.click('.gate [data-act="draftcl"]'); await d.wait_for_timeout(400)
        ok("Claude couldn't answer: says so, the entry is kept", "Claude couldn't write the changelog." in await cl.inner_text() and (await P(d))['changelog']['text'].endswith('- Works offline.') and await d.locator('.errbox [data-act="draftcl"]').count() == 1)
        await d.evaluate(f'window.__tick = 40; window.__step = 4; window.__replies.push({json.dumps(DRAFT2)})')
        await d.click('.errbox [data-act="draftcl"]'); await d.wait_for_timeout(200)
        ok('drafting again over an entry says it stays until the new one is ready', 'Your current entry stays as it is' in await cl.inner_text())
        await d.click('[data-act="stopcl"]'); await d.wait_for_timeout(750)
        ok('Stop keeps nothing', 'Stopped. Nothing was kept.' in await toast(d) and (await P(d))['changelog']['text'].endswith('- Works offline.'))
        await d.evaluate(f'window.__tick = 6; window.__step = 40; window.__replies.push({json.dumps(DRAFT2)})')
        await d.click('.clacts [data-act="draftcl"]'); await d.wait_for_timeout(150); await d.click('.gate [data-act="draftcl"]')
        await d.wait_for_selector('#cl-text', timeout=8000); await d.wait_for_timeout(750)
        ok('Draft again replaces it once you say so', (await P(d))['changelog']['text'] == DRAFT2 and (await P(d))['changelog']['by'] == 'claude')

        await d.evaluate(REFUSE)
        await d.click('[data-act="copycl"]'); await d.wait_for_timeout(750)
        ok('refused copy: a sheet with the prompt selected', await d.locator('.sheet[aria-labelledby="cf-h"]').is_visible() and 'Prompt for the v1.0.0 changelog' in await d.inner_text('.sheet') and await d.evaluate(SELECTED))
        ok('refused copy: no stale Copied toast', await d.query_selector('.toast') is None)
        await d.screenshot(path=OUT + 's14-desk-refused.png')
        await d.evaluate(ALLOW)
        await d.click('[data-act="copyfailagain"]'); await d.wait_for_timeout(200)
        ok('the sheet copies, then closes', (await d.evaluate('window.__clip') or '').startswith('Add the v1.0.0 entry') and await d.query_selector('.sheet') is None)

        # Offline: write it yourself
        await d.evaluate("window.dispatchEvent(new Event('offline')); 0"); await d.wait_for_timeout(200)
        ok("offline: Draft again is gone; the entry can still be edited and copied", await d.locator('.clacts [data-act="draftcl"]').count() == 0 and await d.locator('#cl-text').is_editable() and await d.locator('[data-act="copycl"]').is_enabled())
        await d.evaluate("window.dispatchEvent(new Event('online')); 0"); await d.wait_for_timeout(200)

        # Release: version and live URL
        ok('release: live URL with Open, the version, no versions yet', await d.locator('.pside .liverow a[href="https://siwes.pages.dev"]').count() == 1 and await d.input_value('#p-ver') == '1.0.0'
           and 'Finishing Ship records the version' in await d.inner_text('.pside'))
        await d.screenshot(path=OUT + 's14-desk-changelog.png', full_page=True)

        # Finish Ship
        for lid in await d.eval_on_selector_all('input[data-launch]:not(:checked)', 'els => els.map(e => e.dataset.launch)'):   # s1 came back unticked, plus the new check
            await d.click(f'label:has(input[data-launch="{lid}"])'); await d.wait_for_timeout(30)
        await d.click('.shipmain .checks li:nth-child(2) label'); await d.click('.shipmain .checks li:nth-child(3) label'); await d.wait_for_timeout(750)
        fin = d.locator('.shipmain [data-act="finish"]')
        ok('everything ticked: Finish Ship is the primary button', 'primary' in (await fin.get_attribute('class')) and (await P(d))['checks']['ship'] == [True, True, True])
        await fin.click(); await d.wait_for_timeout(500)
        p = await P(d)
        ok('finishing records v1.0.0 with the date and live URL', p['completed']['ship'] is True and p['versions'][0]['v'] == '1.0.0' and p['versions'][0]['url'] == 'https://siwes.pages.dev' and abs(p['versions'][0]['at'] - NOW) < 10 * 60000)
        ok('then lands on Shipped, with a toast', d.url.endswith('#shipped') and 'Shipped v1.0.0.' in await toast(d))

        # The Shipped list
        rows = d.locator('table.ships tbody tr')
        ok('Shipped lists both, newest first', await rows.count() == 2 and 'SIWES logbook' in await rows.nth(0).inner_text() and 'Mafia' in await rows.nth(1).inner_text())
        r1 = await rows.nth(1).inner_text()
        ok('a row: version, date, live URL, feedback and backlog counts', 'v1.0.0' in r1 and 'Nov 5' in r1 and 'mafia-game.pages.dev' in r1 and r1.split('\t')[-2:] == ['2', '1'])
        ok('the rail marks Shipped', await d.locator('.rail a[href="#shipped"][aria-current="page"]').count() == 1)
        ok('shipped projects leave the board and the rail list', 'SIWES logbook' not in await d.inner_text('.rail .plist'))
        await d.screenshot(path=OUT + 's14-desk-shipped.png')

        # A shipped project: keep taking feedback, then start the next version
        await d.click('table.ships a[href="#p-pdone-ship"]'); await d.wait_for_selector('.shipbar', timeout=5000)
        ok('a shipped project says so, with Start v1.1.0', 'v1.0.0 shipped on Nov 5' in await d.inner_text('.shipbar') and await d.locator('[data-act="asknextv"]').inner_text() == 'Start v1.1.0'
           and 'version 1.0.0 · shipped' in await d.inner_text('.top.ph .tt'))
        ok('the rail still marks Shipped', await d.locator('.rail a[href="#shipped"][aria-current="page"]').count() == 1)
        ok('a list saved before keeps its checks', await d.locator('input[data-launch]').count() == 1)
        await d.fill('#fb-text', 'Can we vote by tapping a name?'); await d.click('#fbForm [type="submit"]'); await d.wait_for_timeout(750)
        ok('feedback after shipping is saved', len((await P(d, 'pdone'))['feedback']) == 3)
        ok("v1.0.0's own changelog reads every entry", await d.evaluate('versionLog(proj("pdone")).map(e => e.id).join()') == 'S9,S8,S7,S6' and '4 progress entries, read' in await d.inner_text('.clsec'))
        ok("the next version's version numbers", await d.evaluate('[bumpVer("1.0.0"), bumpVer("1.0"), bumpVer("2"), bumpVer("2.0-beta3"), bumpVer("beta")].join()') == '1.1.0,1.1,3,2.0-beta4,beta.1')
        await d.click('[data-act="asknextv"]'); await d.wait_for_timeout(200)
        ok('Start asks first and says what stays', 'Start v1.1.0 in Define?' in await d.inner_text('.shipbar') and 'Feedback, the backlog, your documents and the repo stay' in await d.inner_text('.shipbar')
           and await d.evaluate('document.activeElement.dataset.act') == 'nextv')
        await d.click('[data-act="cancelnextv"]'); await d.wait_for_timeout(150)
        ok('Cancel changes nothing', (await P(d, 'pdone'))['phase'] == 'ship' and await d.locator('[data-act="asknextv"]').count() == 1)
        await d.click('[data-act="asknextv"]'); await d.click('[data-act="nextv"]'); await d.wait_for_timeout(600)
        p = await P(d, 'pdone')
        ok('v1.1.0 starts in Define', p['version'] == '1.1.0' and p['phase'] == 'define' and d.url.endswith('#p-pdone-define') and 'v1.1.0 starts in Define.' in await toast(d))
        ok('checklists from Define to Ship start fresh; Discover stays done', p['completed'] == {'discover': True} and not any(p['checks']['ship']) and not any(x['done'] for x in p['launch']) and p['changelog'] is None)
        ok('feedback, backlog and the version history stay', len(p['feedback']) == 3 and len(p['backlog']) == 1 and p['versions'][0]['v'] == '1.0.0')
        ok('it is back on the board and the rail, off Shipped', 'Mafia' in await d.inner_text('.rail .plist') and await d.evaluate('shippedList().map(p => p.id).join()') == 'pl')
        ok('v1.1.0: the changelog reads only what came after v1.0.0', await d.evaluate('versionLog(proj("pdone")).map(e => e.id).join()') == 'S9,S8'
           and 'Previous version: 1.0.0, shipped 2026-11-05.' in await d.evaluate('changelogAsk(proj("pdone"), versionLog(proj("pdone")))'))

        # The Define coach and the drafts read the backlog
        await d.wait_for_selector('#coach-input', timeout=5000)
        n2 = len(await d.evaluate('window.__calls'))
        await d.fill('#coach-input', 'What should v1.1 include?'); await d.press('#coach-input', 'Enter'); await d.wait_for_timeout(800)
        cc = json.dumps((await d.evaluate('window.__calls'))[n2:])
        ok('the Define coach reads the backlog and the version', "Backlog from real users' feedback" in cc and 'Let the host set the night timer (from Dami)' in cc and 'Version being planned: 1.1.0 (v1.0.0 shipped 2026-11-05)' in cc)
        dp = await d.evaluate('draftPrompt(proj("pdone"), "define", docRec("pdone", "define", "stories"))')
        ok('the stories draft reads it and keeps the IDs', 'Let the host set the night timer' in dp and 'This is a new version: keep every existing story with its ID' in dp)
        dp2 = await d.evaluate('draftPrompt({...proj("pl"), backlog:[]}, "define", docRec("pl", "define", "stories"))')
        ok('a project with no backlog gets none of that', 'Backlog from real users' not in dp2 and 'This is a new version' not in dp2)

        # Reload: everything persisted
        await d.wait_for_timeout(750); dbsnap = await d.evaluate('localStorage.getItem("__mockdb")')
        r = await ctx.new_page(); r.on('pageerror', lambda e: errs.append('reload: ' + str(e)))
        await r.add_init_script('if (!window.name){ window.name = "seeded"; localStorage.setItem("__mockdb", %s); }' % json.dumps(dbsnap))
        await r.add_init_script(mock('none'))
        await r.goto(URL + '#p-pl-ship'); await r.wait_for_selector('.shipmain .lsec', timeout=8000); await r.wait_for_timeout(750)
        ok('after a reload: ticks, feedback, backlog and the changelog are there', await r.locator('input[data-launch]:checked').count() == 22 and await r.locator('.fblist li').count() == 1
           and await r.input_value('#cl-text') == DRAFT2 and 'v1.0.0 shipped' in await r.inner_text('.shipbar'))
        ok('after a reload without the file server: no Sync now, the snapshot still counts', await r.locator('.clsec [data-act="sync"]').count() == 0 and '4 progress entries' in await r.inner_text('.clsec'))
        await r.close()

        # ---------- Empty Shipped list ----------
        e = await b.new_context(viewport={'width': 1440, 'height': 900})
        ep = await e.new_page(); ep.on('pageerror', lambda x: errs.append('empty: ' + str(x)))
        await ep.add_init_script(mock('none', seed={'projects/pl': SEED['projects/pl']}))
        await ep.goto(URL + '#shipped'); await ep.wait_for_selector('h1', timeout=5000); await ep.wait_for_timeout(750)
        ok('empty Shipped: says what lands there', 'Nothing shipped yet' in await ep.inner_text('main') and await ep.locator('table.ships').count() == 0)
        await e.close()

        # ---------- 1024, light ----------
        cx = await b.new_context(viewport={'width': 1024, 'height': 768}, color_scheme='light')
        k = await cx.new_page(); k.on('pageerror', lambda x: errs.append('1024: ' + str(x)))
        await k.add_init_script(mock('none'))
        await k.goto(URL + '#p-pdone'); await k.wait_for_selector('.shipbar', timeout=8000); await k.wait_for_timeout(750)
        ok('1024 light: no sideways scroll', await k.evaluate('document.documentElement.scrollWidth <= innerWidth'))
        ok('1024 light: the tab bar is a phone thing', not await k.locator('.btabs').is_visible())
        await k.screenshot(path=OUT + 's14-1024-light.png', full_page=True)
        await k.goto(URL + '#shipped'); await k.wait_for_timeout(750)
        await k.screenshot(path=OUT + 's14-1024-shipped.png')
        await cx.close()

        # ---------- Phones: 390 dark and 360 light ----------
        for wd, ht, scheme, tag in [(390, 844, 'dark', 'm390'), (360, 800, 'light', 'm360')]:
            mc = await b.new_context(viewport={'width': wd, 'height': ht}, color_scheme=scheme, has_touch=True, is_mobile=True)
            m = await mc.new_page(); m.on('pageerror', lambda x, t=tag: errs.append(t + ': ' + str(x)))
            await m.add_init_script(mock('none'))
            await m.goto(URL + '#p-pl'); await m.wait_for_selector('.shipmain', timeout=8000); await m.wait_for_timeout(750)
            tabs = m.locator('.btabs[aria-label="Ship views"] [role="tab"]')
            ok(f'{tag}: Launch, Feedback and Changelog tabs', await tabs.count() == 3 and 'Launch 0/21' in await tabs.nth(0).inner_text())
            ok(f'{tag}: Launch shows the checklists and the release details', await m.locator('#lc-h').is_visible() and await m.locator('#xc-h').is_visible() and await m.locator('#p-live').is_visible() and not await m.locator('#fb-h').is_visible() and not await m.locator('#cl-h').is_visible())
            xb = await m.locator('[data-act="rmlaunch"]').first.bounding_box(); lb = await m.locator('.lchecks label').first.bounding_box()
            ok(f'{tag}: 44 px targets', xb['height'] >= 44 and xb['width'] >= 44 and lb['height'] >= 44)
            ok(f'{tag}: no sideways scroll', await m.evaluate('document.documentElement.scrollWidth <= innerWidth'))
            await m.screenshot(path=OUT + f's14-{tag}-launch.png')
            await m.locator('label:has(input[data-launch="l0"])').tap(); await m.wait_for_timeout(250)
            ok(f'{tag}: tapping a check ticks it', 'Launch 1/21' in await tabs.nth(0).inner_text())
            await tabs.nth(1).tap(); await m.wait_for_timeout(200)
            ok(f'{tag}: Feedback shows feedback and the backlog only', await m.locator('#fb-h').is_visible() and await m.locator('#bl-h').is_visible() and not await m.locator('#lc-h').is_visible() and not await m.locator('.pside').is_visible())
            await m.locator('#fb-text').fill('Works well on my Tecno'); await m.locator('#fbForm [type="submit"]').tap(); await m.wait_for_timeout(750)
            await m.locator('[data-act="tobacklog"]').first.tap(); await m.wait_for_timeout(750)
            ok(f'{tag}: add feedback and send it to the backlog', 'Works well on my Tecno' in await m.inner_text('.fblist') and await m.locator('.bllist li').count() == 1)
            fb = await m.locator('#fbForm [type="submit"]').bounding_box()
            ok(f'{tag}: the Add button is a full-width touch target', fb['height'] >= 44 and fb['width'] >= wd - 60)
            await m.screenshot(path=OUT + f's14-{tag}-feedback.png')
            await tabs.nth(2).tap(); await m.wait_for_timeout(200)
            ok(f'{tag}: Changelog shows only the changelog, and why Draft waits', await m.locator('#cl-h').is_visible() and not await m.locator('#fb-h').is_visible() and 'Sync runs in the Claude desktop app' in await m.inner_text('.clsec'))
            await m.locator('[data-act="writecl"]').tap(); await m.wait_for_timeout(750)
            ok(f'{tag}: write it yourself starts from the shape', (await m.input_value('#cl-text')).startswith('## [1.0.0] - ') and await m.evaluate('document.activeElement.id') == 'cl-text')
            await m.screenshot(path=OUT + f's14-{tag}-changelog.png')
            await m.goto(URL + '#board'); await m.wait_for_timeout(750)
            sl = m.locator('a.shiplink')
            ok(f'{tag}: the board links to Shipped', await sl.is_visible() and '1' in await sl.inner_text() and (await sl.bounding_box())['height'] >= 44)
            await sl.tap(); await m.wait_for_timeout(750)
            ok(f'{tag}: Shipped as rows', await m.locator('.mrows li').count() == 1 and 'mafia-game.pages.dev · 2 feedback · 1 in backlog' in await m.inner_text('.mrows'))
            ok(f'{tag}: no sideways scroll on Shipped', await m.evaluate('document.documentElement.scrollWidth <= innerWidth'))
            await m.screenshot(path=OUT + f's14-{tag}-shipped.png')
            await mc.close()

        for n, c in checks: print(('PASS ' if c else 'FAIL ') + n)
        print(f'{sum(c for _, c in checks)}/{len(checks)} passed')
        print('ERRORS', errs)
        await b.close()

asyncio.run(main())
