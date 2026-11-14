"""S12 browser test: a Claude Code prompt per slice, with a mocked db, a mocked laptop file server and a stubbed clipboard."""
import asyncio, json, os, time
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

# docs/stories.md in the shape the stories draft and the handoff write, with Windows line endings
STORIES = """# siwes-logbook · slices

## Must
- [x] S0 · Walking skeleton
  - Given the repo folder, when Claude Code runs `npm create vite@latest .`, then the app is set up there, not in a subfolder
  - Given a push to main, when CI runs, then it's green and the empty page is live
- [x] S1 · Sign in with a matric number
  As a student, I want to sign in with my matric number, so that my entries are mine.
  - Given a valid matric number and password, when I sign in, then I see this week
- [~] S3 · See the week at a glance
  As a student, I want to see my week, so that I spot missing days.
  - Given a week with two empty days, when I open it, then both are flagged
- [ ] S4 · Supervisor signs off the week
  As a supervisor, I want to sign off a student's week, so that the logbook is approved
    on time.
  - Given a week with seven entries, when I press Sign off, then the week is locked
    and the student sees who signed it.
  - Given a week with a missing day, when I press Sign off, then I'm asked to confirm first
  - Given I'm offline, when I sign off, then it's saved and sent when I'm back online
- [ ] S5 · Export the week's entries as a PDF

Build order is riskiest first.

## Should
- [ ] S9 · Supervisor comments
  - Given an entry, when the supervisor comments, then the student is notified
""".replace('\n', '\r\n')
PROGRESS = "# Progress log\n\nNewest first.\n\n## 2026-11-12 · S3 · Weekly view\n- Built: seven-day grid.\n- Tests: 31 passed\n- Check on your phone: open this week.\n- Next: S4 · Supervisor signs off the week\n"
A, B, C = '1' * 40, '2' * 40, '3' * 40
REFLOG = f"{A} {B} Shawn <s@example.com> {NOW // 1000 - 7200} +0100\tcommit: feat(S1): sign in with matric number\n{B} {C} Shawn <s@example.com> {NOW // 1000 - 3600} +0100\tcommit: feat(S3): weekly view\n"
CLAUDE = "# SIWES logbook\n\nRead docs/PRD.md before changing anything.\n\n## Stack\n- Vite and React on Cloudflare Pages\n\n## Commands\n- Install: `npm install`\n- Dev: `npm run dev`\n- Test: `npm test`\n- Deploy: TBD\n\n## Studio protocol (every slice)\nThe Studio reads things.\n\n## Rules\n- $0 only\n"
CLAUDE_TBD = "# Tracker\n\n## Commands\nTBD: Claude Code fills this in from the repo (install, dev, test, deploy), one line each. The Studio copies them into every slice prompt.\n\n## Rules\n- $0 only\n"
STUDIO_STORIES = (HERE / 'fx_stories.md').read_text(encoding='utf-8')
STUDIO_CLAUDE = (HERE.parent / 'CLAUDE.md').read_text(encoding='utf-8')
PLAIN = "# Plain · slices\n\n## Must\n- [x] S0 · Walking skeleton\n- [ ] S1 · First screen\n"

FILES = {
    REPO + '\\docs\\stories.md': STORIES, REPO + '\\docs\\progress.md': PROGRESS,
    REPO + '\\.git\\HEAD': 'ref: refs/heads/dev\r\n', REPO + '\\.git\\logs\\HEAD': REFLOG, REPO + '\\CLAUDE.md': CLAUDE.replace('\n', '\r\n'),
    'C:\\Projects\\the-studio\\docs\\stories.md': STUDIO_STORIES, 'C:\\Projects\\the-studio\\CLAUDE.md': STUDIO_CLAUDE,
    'C:\\Projects\\plain\\docs\\stories.md': PLAIN,                                               # no CLAUDE.md at all
    'C:\\Projects\\tracker\\docs\\stories.md': PLAIN, 'C:\\Projects\\tracker\\CLAUDE.md': CLAUDE_TBD,   # Commands still TBD
}

def snap(repo, slices, **kw):
    return {'repo': repo, 'repoName': repo.split('\\')[-1], 'via': 'laptop', 'at': NOW - 3600000, 'slices': slices, 'marks': {}, 'branch': 'main', 'log': [], 'commits': [], **kw}

def sl(i, title, status='todo', group='Must', **kw):
    return {'id': i, 'title': title, 'status': status, 'group': group, 'raw': f'- [{ {"todo": " ", "check": "~", "done": "x"}[status] }] {i} · {title}', **kw}

def proj(name, repo='', **kw):
    return {'name': name, 'phase': 'build', 'completed': {'discover': True, 'define': True, 'design': True}, 'checks': {}, 'repo': repo, '__ago': DAY, **kw}

SEED = {
    'projects/pl': proj('SIWES logbook', REPO, liveUrl='https://siwes.example.pages.dev'),
    'projects/ps': proj('The Studio', 'C:\\Projects\\the-studio'),
    'projects/pn': proj('Plain app', 'C:\\Projects\\plain'),
    'projects/pt': proj('Tracker', 'C:\\Projects\\tracker'),
    # a snapshot from before S12: no story, criteria or commands in it
    'projects/pold': proj('Old snapshot'),
    'syncs/pold': snap('C:\\Projects\\old', [sl('S0', 'Walking skeleton', 'done'), sl('S2', 'Daily entry')]),
    # every slice done
    'projects/pdone': proj('All done'),
    'syncs/pdone': snap('C:\\Projects\\done', [sl('S0', 'Walking skeleton', 'done', story='', crit=[]), sl('S1', 'Sign in', 'done', story='', crit=[])], claude={'found': True, 'cmds': '- Test: `npm test`'}),
    # synced on the laptop earlier; the phone shows this snapshot
    'projects/pm': proj('Phone project', 'C:\\Projects\\phone'),
    'syncs/pm': snap('C:\\Projects\\phone', [
        sl('S0', 'Walking skeleton', 'done', story='', crit=['Given a push, when CI runs, then it is green']),
        sl('S1', 'Log a daily entry', story='As a student, I want to log my day, so that my logbook fills itself.',
           crit=['Given today, when I type an entry, then it saves within a second', 'Given no signal, when I save, then it is kept and sent later', 'Given yesterday was missed, when I open the app, then it says so']),
        sl('S2', 'Weekly view')], claude={'found': True, 'cmds': '- Install: `npm install`\n- Test: `npm test`'}),
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
  window.__store = S0; window.__clip = null; window.__clipFail = false;
  Object.defineProperty(navigator, 'clipboard', {configurable:true, value:{writeText: async t => { if (window.__clipFail) throw new Error('denied'); window.__clip = t; }}});
  const sample = () => Promise.reject({code:'unavailable'}); sample.json = sample;
  const FILES = %FILES%;
  window.__files = FILES; window.__calls = []; window.__host = %HOST%; window.__delay = 0; window.__fail = null;
  const mcp = {
    async listTools(){ return {servers: window.__host === 'listed' ? [{server:'host:filesystem', authStatus:'unknown', tools:[{name:'read_text_file', description:''},{name:'edit_file', description:''}]}] : []}; },
    async callTool(server, tool, input){
      window.__calls.push({tool, input});
      if (window.__host !== 'listed') throw {code:'server_not_connected', message:'no host'};
      if (window.__delay){ const d = window.__delay; window.__delay = 0; await new Promise(r => setTimeout(r, d)); }
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

def mock(host='listed'):
    return MOCK.replace('%SEED%', json.dumps(SEED)).replace('%FILES%', json.dumps(FILES)).replace('%HOST%', json.dumps(host))

REFUSE = 'window.__clipFail = true; window.__exec = document.execCommand; document.execCommand = () => false; 0'   # both ways of copying refused
ALLOW = 'window.__clipFail = false; document.execCommand = window.__exec; window.__clip = null; 0'
SELECTED = "(() => { const e = document.querySelector('#sp-text'); return !!e && document.activeElement === e && e.selectionStart === 0 && e.selectionEnd === e.value.length && e.value.length > 200; })()"


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(**LAUNCH)
        errs, checks = [], []
        def ok(name, cond):
            checks.append((name, bool(cond)))
        async def toast(pg):
            t = await pg.query_selector('.toast')
            return await t.inner_text() if t else ''
        async def clip(pg):
            return await pg.evaluate('window.__clip')
        async def stored(pg, k):
            return await pg.evaluate(f'window.__store[{json.dumps(k)}]')

        # ---------- Desktop 1440, dark, the Claude app with the file server ----------
        ctx = await b.new_context(viewport={'width': 1440, 'height': 900}, color_scheme='dark')
        d = await ctx.new_page(); d.on('pageerror', lambda e: errs.append('desk: ' + str(e)))
        await d.add_init_script(mock())
        await d.add_init_script('window.__delay = 1500;')
        await d.goto(URL + '#p-pl')
        await d.wait_for_selector('.slicesec[aria-busy="true"]', timeout=5000)
        ok('loading: skeleton rows and no prompt link while the first sync runs', await d.query_selector('.sp-next') is None)
        await d.wait_for_selector('table.slices', timeout=8000); await d.wait_for_timeout(300)

        reads = [c['input']['path'] for c in await d.evaluate('window.__calls') if c['tool'] == 'read_text_file']
        ok('sync reads CLAUDE.md with read_text_file', REPO + '\\CLAUDE.md' in reads)
        sn = await stored(d, 'syncs/pl')
        s = {x['id']: x for x in sn['slices']}
        ok('story kept, a wrapped story line joined', s['S4']['story'] == "As a supervisor, I want to sign off a student's week, so that the logbook is approved on time.")
        ok('criteria kept, a wrapped criterion joined', len(s['S4']['crit']) == 3 and s['S4']['crit'][0] == 'Given a week with seven entries, when I press Sign off, then the week is locked and the student sees who signed it.')
        ok('S0 has criteria and no story', s['S0']['story'] == '' and len(s['S0']['crit']) == 2)
        ok('an unindented line ends a slice: S5 has none', s['S5']['story'] == '' and s['S5']['crit'] == [])
        ok('Should slices keep theirs too', s['S9']['group'] == 'Should' and len(s['S9']['crit']) == 1)
        ok('CRLF lines parse clean', not any('\r' in c for x in sn['slices'] for c in x['crit'] + [x['story'], x['title']]))
        ok('commands from CLAUDE.md, TBD lines kept as written', sn.get('claude') == {'found': True, 'cmds': '- Install: `npm install`\n- Dev: `npm run dev`\n- Test: `npm test`\n- Deploy: TBD'})
        ok('slice statuses and commits unchanged', s['S3']['status'] == 'check' and s['S1']['status'] == 'done' and 'feat(S3)' in await d.inner_text('table.slices'))

        link = d.locator('.sechead .sp-next')
        ok('header link names the next slice, as on the canvas', await link.is_visible() and (await link.inner_text()).strip() == 'Copy prompt for S4')
        col = await link.evaluate('e => getComputedStyle(e).color')
        ok('header link in text 2 at 13 px', col == 'rgb(163, 167, 173)' and await link.evaluate('e => getComputedStyle(e).fontSize') == '13px')
        await d.screenshot(path=OUT + 's12-desk.png')

        await link.click(); await d.wait_for_timeout(200)
        pr = await clip(d)
        ok('Copy: a prompt reaches the clipboard', bool(pr))
        ok('prompt: opens with the slice, the project, the folder and the branch from git',
           pr.startswith('Build S4 · Supervisor signs off the week in SIWES logbook.\nWork in C:\\Projects\\siwes-logbook on branch dev. Read CLAUDE.md first'))
        ok('prompt: the slice line, its story and every criterion',
           "The slice, from docs/stories.md:\n- [ ] S4 · Supervisor signs off the week\n  As a supervisor, I want to sign off a student's week, so that the logbook is approved on time.\n  - Given a week with seven entries, when I press Sign off, then the week is locked and the student sees who signed it.\n  - Given a week with a missing day" in pr
           and "  - Given I'm offline, when I sign off, then it's saved and sent when I'm back online\n" in pr)
        ok('prompt: the commands from CLAUDE.md', 'Commands, from CLAUDE.md:\n- Install: `npm install`\n- Dev: `npm run dev`\n- Test: `npm test`\n- Deploy: TBD\n' in pr)
        ok('prompt: ask first, then build', '1. Before you write code, read the code S4 touches and ask me anything that would change the build. Say first if it needs anything the repo' in pr
           and '2. Build only S4 and meet every acceptance criterion. Every new screen needs its loading, empty and error states.' in pr)
        ok('prompt: the whole suite runs', 'run the whole test suite, not just the new tests' in pr)
        ok('prompt: the protocol with the exact commit and push', "mark S4 [~] in docs/stories.md and add its entry at the top of docs/progress.md" in pr
           and "   git commit -m 'feat(S4): Supervisor signs off the week'\n   git push origin dev\n" in pr)
        ok('prompt: Studio update block, phone check and the rules', 'Studio update block from CLAUDE.md and tell me what to check on my phone' in pr and pr.rstrip().endswith('Only I mark [x].'))
        ok('prompt: nothing missing or doubled', 'undefined' not in pr and 'null' not in pr and '\n\n\n' not in pr and pr.endswith('\n') and len(pr) < 3000)
        ok('toast names the folder', await toast(d) == 'Copied the S4 prompt. Paste it into Claude Code in C:\\Projects\\siwes-logbook.')
        ok('focus stays on the link', await d.evaluate('document.activeElement && document.activeElement.classList.contains("sp-next")'))
        ok('no hidden copy field left behind', await d.evaluate('document.querySelectorAll("textarea[aria-hidden]").length') == 0)

        # Keyboard: Enter on the link
        await d.evaluate('window.__clip = null; 0')
        await link.focus(); await d.keyboard.press('Enter'); await d.wait_for_timeout(200)
        ok('keyboard: Enter copies the same prompt', await clip(d) == pr)

        # Open S4: story, criteria, commits, Copy prompt
        await d.click('button.disc[data-id="S4"]'); await d.wait_for_timeout(200)
        det = await d.inner_text('#sd-S4')
        ok('open row: story and criteria under a sentence-case heading', 'Story and acceptance criteria' in det and 'so that the logbook is approved on time.' in det
           and await d.locator('#sd-S4 ul.scrit li').count() == 3)
        ok('open row: commits, then Copy prompt with what it carries', 'No commits mention S4 yet.' in det and 'With its criteria and the commands in CLAUDE.md.' in det
           and await d.locator('#sd-S4 [data-act="copyprompt"]').is_visible())
        await d.screenshot(path=OUT + 's12-desk-open.png')
        await d.evaluate('window.__clip = null; 0')
        await d.click('#sd-S4 [data-act="copyprompt"]'); await d.wait_for_timeout(200)
        ok('open row: Copy prompt copies the same prompt', await clip(d) == pr)

        # S3 is built and waiting for a phone check
        await d.click('button.disc[data-id="S3"]'); await d.wait_for_timeout(200)
        ok('built slice: its commit in the open row', 'feat(S3): weekly view' in await d.inner_text('#sd-S3'))
        await d.click('#sd-S3 [data-act="copyprompt"]'); await d.wait_for_timeout(200)
        p3 = await clip(d)
        ok('built slice: the prompt says it is waiting for the phone check', p3.startswith("Continue S3 · See the week at a glance in SIWES logbook. It's marked [~]") and '- [~] S3 · See the week at a glance' in p3
           and "2. Check what's built against every acceptance criterion and fix what falls short. Build nothing beyond S3." in p3 and "git commit -m 'feat(S3): See the week at a glance'" in p3)

        # S1 is done: criteria, no prompt
        await d.click('button.disc[data-id="S1"]'); await d.wait_for_timeout(200)
        ok('done slice: criteria shown, no Copy prompt', 'Given a valid matric number' in await d.inner_text('#sd-S1') and await d.locator('#sd-S1 [data-act="copyprompt"]').count() == 0)

        # S5 has no story or criteria in docs/stories.md
        await d.click('button.disc[data-id="S5"]'); await d.wait_for_timeout(200)
        ok('no criteria: the open row says where the prompt sends Claude Code', 'No story or criteria under S5 in docs/stories.md. Its prompt asks Claude Code to read them in docs/PRD.md.' in await d.inner_text('#sd-S5'))
        ok('no criteria: the hint promises only the commands', 'With the commands in CLAUDE.md.' in await d.inner_text('#sd-S5') and 'its criteria' not in await d.inner_text('#sd-S5'))
        await d.click('#sd-S5 [data-act="copyprompt"]'); await d.wait_for_timeout(200)
        p5 = await clip(d)
        ok('no criteria: the prompt points to the PRD and says to ask', "- [ ] S5 · Export the week's entries as a PDF\n\ndocs/stories.md has no acceptance criteria for S5. Read its story in docs/PRD.md first. If the PRD has none either, ask me for them before you build." in p5)
        ok("an apostrophe in a title can't break the quoted commit message", "git commit -m 'feat(S5): Export the week\u2019s entries as a PDF'" in p5)
        await d.screenshot(path=OUT + 's12-desk-rows.png', full_page=True)

        # Refused copy: a sheet with the prompt selected
        await d.evaluate(REFUSE)
        await link.click(); await d.wait_for_timeout(300)
        sheet = d.locator('.sheet[aria-labelledby="sp-h"]')
        ok('refused copy: a sheet opens with the prompt', await sheet.is_visible() and await d.input_value('#sp-text') == pr and 'Prompt for S4' in await sheet.inner_text())
        ok("refused copy: says so, with the prompt selected", "Couldn't copy it." in await sheet.inner_text() and await d.evaluate(SELECTED))
        ok('refused copy: an earlier Copied toast is cleared', await d.query_selector('.toast') is None)
        ok('refused copy: no hidden copy field left behind', await d.evaluate('document.querySelectorAll("textarea[aria-hidden]").length') == 0)
        await d.screenshot(path=OUT + 's12-desk-refused.png')
        await d.click('[data-act="copyslice"]'); await d.wait_for_timeout(200)
        ok('refused again: stays open and selected, with a toast', await sheet.is_visible() and await d.evaluate(SELECTED) and 'press Ctrl+C' in await toast(d))
        await d.evaluate(ALLOW)
        await d.click('[data-act="copyslice"]'); await d.wait_for_timeout(200)
        ok('the sheet copies, then closes', await clip(d) == pr and await d.query_selector('.sheet') is None and 'Copied the S4 prompt' in await toast(d))
        # the clipboard API refused, the old way works
        await d.evaluate('window.__clipFail = true; window.__exec = document.execCommand; document.execCommand = () => { window.__execText = document.activeElement && document.activeElement.value; return true; }; 0')
        await link.click(); await d.wait_for_timeout(200)
        ok('fallback copy: a hidden field holds the prompt, no sheet', await d.evaluate('window.__execText') == pr and await d.query_selector('.sheet') is None and 'Copied the S4 prompt' in await toast(d))
        ok('fallback copy: the hidden field is removed again', await d.evaluate('document.querySelectorAll("textarea[aria-hidden]").length') == 0)
        await d.evaluate(ALLOW)

        # Sync fails: the snapshot's prompt still works
        await d.evaluate("window.__fail = {code:'server_unavailable', message:'x'}; 0")
        await d.click('.syncbar [data-act="sync"]'); await d.wait_for_timeout(300)
        ok('sync error: the bar says so and keeps the snapshot', "Couldn't read the repo" in await d.inner_text('.syncbar'))
        await link.click(); await d.wait_for_timeout(200)
        ok('sync error: the prompt still carries the criteria and commands', await clip(d) == pr)
        await d.screenshot(path=OUT + 's12-desk-error.png')

        # A pasted update keeps what the last sync read
        await d.click('.syncbar [data-act="paste"]'); await d.wait_for_timeout(150)
        await d.fill('#paste-text', 'Studio update · siwes-logbook\n- [~] S4 · Supervisor signs off the week\n## 2026-11-14 · S4 · Sign-off\n- Built: supervisors sign off a week.\n- Tests: 12 passed\n- Check on your phone: sign off a week.\n- Next: S5 · PDF export')
        await d.click('#pasteForm [type="submit"]'); await d.wait_for_timeout(150)
        await d.click('[data-act="applypaste"]'); await d.wait_for_timeout(300)
        sn = await stored(d, 'syncs/pl'); s = {x['id']: x for x in sn['slices']}
        ok('paste: S4 built, its story and criteria kept', s['S4']['status'] == 'check' and len(s['S4']['crit']) == 3 and s['S4']['story'].startswith('As a supervisor'))
        ok('paste: the commands kept', sn['via'] == 'paste' and 'npm test' in sn['claude']['cmds'])
        ok('paste: the header link moves to S5', (await link.inner_text()).strip() == 'Copy prompt for S5')

        # The board and the handoff
        ok('handoff CLAUDE.md says the commands feed the prompts', 'The Studio copies them into every slice prompt.' in await d.evaluate('claudeMd(proj("pl"), [])'))

        # The Studio's own repo: no criteria in stories.md; commands from its real CLAUDE.md
        await d.goto(URL + '#p-ps'); await d.wait_for_selector('table.slices', timeout=5000); await d.wait_for_timeout(300)
        ok("The Studio's repo: header link for S16", (await link.inner_text()).strip() == 'Copy prompt for S16')
        await link.click(); await d.wait_for_timeout(200)
        ps = await clip(d)
        ok("The Studio's repo: the prompt points to the PRD", 'docs/stories.md has no acceptance criteria for S16. Read its story in docs/PRD.md first.' in ps)
        ok("The Studio's repo: the test command from its CLAUDE.md", 'Commands, from CLAUDE.md:\n- Install: `pip install playwright`' in ps and 'for f in tests/s*.py; do python "$f"; done' in ps)

        # No CLAUDE.md in the repo
        await d.goto(URL + '#p-pn'); await d.wait_for_selector('table.slices', timeout=5000); await d.wait_for_timeout(300)
        ok('no CLAUDE.md: the sync still works', "Couldn't read" not in await d.inner_text('.syncbar') and (await stored(d, 'syncs/pn'))['claude'] == {'found': False, 'cmds': ''})
        await d.click('button.disc[data-id="S1"]'); await d.wait_for_timeout(200)
        ok('no CLAUDE.md: the open row warns, with the setup prompt', "There's no CLAUDE.md in the repo, so the prompt tells Claude Code to stop." in await d.inner_text('#sd-S1') and await d.locator('#sd-S1 [data-act="setup"]').is_visible())
        await d.click('#sd-S1 [data-act="copyprompt"]'); await d.wait_for_timeout(200)
        ok('no CLAUDE.md: the prompt says to stop first', "There's no CLAUDE.md in this folder, so the Studio protocol and its Stop hook may be missing. Stop and tell me before you build." in await clip(d))
        await d.screenshot(path=OUT + 's12-desk-noclaude.png')
        await d.click('#sd-S1 [data-act="setup"]'); await d.wait_for_timeout(200)
        su = await d.input_value('#setup-text')
        ok('setup prompt: criteria under each slice line', 'indented two spaces under it, the slice\'s story and acceptance criteria' in su and '- [ ] S1 · <title>\n  As a <user>, I want <goal>, so that <reason>.\n  - Given …, when …, then …' in su)
        ok('setup prompt: a Commands section, and the protocol reads it', '"## Commands" section' in su and 'the Commands section of `CLAUDE.md`, `.git/HEAD`' in su)
        await d.keyboard.press('Escape'); await d.wait_for_timeout(100)

        # CLAUDE.md with its Commands still TBD
        await d.goto(URL + '#p-pt'); await d.wait_for_selector('table.slices', timeout=5000); await d.wait_for_timeout(300)
        await link.click(); await d.wait_for_timeout(200)
        ok('TBD commands: the prompt asks Claude Code to fill them in', 'CLAUDE.md has no commands yet. Find the ones to install, run, test and deploy, write them into its Commands section, and commit that with this slice.' in await clip(d))
        await d.click('button.disc[data-id="S1"]'); await d.wait_for_timeout(200)
        ok('TBD commands: the open row says so', 'CLAUDE.md has no commands yet' in await d.inner_text('#sd-S1'))

        # A snapshot from before S12
        await d.goto(URL + '#p-pold'); await d.wait_for_selector('table.slices', timeout=5000); await d.wait_for_timeout(200)
        await d.click('button.disc[data-id="S2"]'); await d.wait_for_timeout(200)
        od = await d.inner_text('#sd-S2')
        ok("old snapshot: the row says the next sync reads them", "The next sync on your laptop reads S2's story and criteria from docs/stories.md." in od and 'The commands come from CLAUDE.md after the next laptop sync.' in od)
        await link.click(); await d.wait_for_timeout(200)
        po = await clip(d)
        ok('old snapshot: the prompt sends Claude Code to the files', 'Work in C:\\Projects\\old on branch main.' in po and 'Its story and acceptance criteria are under that line in docs/stories.md, or in docs/PRD.md.' in po
           and "Commands: use the ones in CLAUDE.md's Commands section." in po)

        # Every slice done: nothing to copy in the header
        await d.goto(URL + '#p-pdone'); await d.wait_for_selector('table.slices', timeout=5000); await d.wait_for_timeout(200)
        ok('every slice done: no header link', await d.query_selector('.sp-next') is None)

        # Reload with the file server gone: the saved snapshot still makes the prompt
        await d.wait_for_timeout(300); dbsnap = await d.evaluate('localStorage.getItem("__mockdb")')
        r = await ctx.new_page(); r.on('pageerror', lambda e: errs.append('reload: ' + str(e)))
        await r.add_init_script('if (!window.name){ window.name = "seeded"; localStorage.setItem("__mockdb", %s); }' % json.dumps(dbsnap))
        await r.add_init_script(mock('none'))
        await r.goto(URL + '#p-pl'); await r.wait_for_selector('table.slices', timeout=5000); await r.wait_for_timeout(300)
        await r.click('button.disc[data-id="S4"]'); await r.wait_for_timeout(200)
        ok('after a reload: the saved criteria show', await r.locator('#sd-S4 ul.scrit li').count() == 3)
        await r.click('#sd-S4 [data-act="copyprompt"]'); await r.wait_for_timeout(200)
        rp = await r.evaluate('window.__clip')
        ok('after a reload: the prompt is whole', rp.startswith("Continue S4 · Supervisor signs off the week in SIWES logbook. It's marked [~]") and 'Commands, from CLAUDE.md:' in rp and 'Given a week with a missing day' in rp)
        await r.close()

        # ---------- 1024, light ----------
        cx = await b.new_context(viewport={'width': 1024, 'height': 768}, color_scheme='light')
        k = await cx.new_page(); k.on('pageerror', lambda e: errs.append('1024: ' + str(e)))
        await k.add_init_script(mock('none'))
        await k.goto(URL + '#p-pm'); await k.wait_for_selector('table.slices', timeout=5000); await k.wait_for_timeout(300)
        kl = k.locator('.sechead .sp-next')
        ok('1024 light: the link in light text 2', await kl.is_visible() and await kl.evaluate('e => getComputedStyle(e).color') == 'rgb(74, 79, 86)')
        await k.click('button.disc[data-id="S1"]'); await k.wait_for_timeout(200)
        ok('1024 light: no sideways scroll on the page', await k.evaluate('document.documentElement.scrollWidth <= innerWidth'))
        await k.screenshot(path=OUT + 's12-1024-light.png')

        # ---------- Phones: 390 dark and 360 light, no file server ----------
        for wd, ht, scheme, tag in [(390, 844, 'dark', 'm390'), (360, 800, 'light', 'm360')]:
            mc = await b.new_context(viewport={'width': wd, 'height': ht}, color_scheme=scheme, has_touch=True, is_mobile=True)
            m = await mc.new_page(); m.on('pageerror', lambda e, t=tag: errs.append(t + ': ' + str(e)))
            await m.add_init_script(mock('none'))
            await m.goto(URL + '#p-pm'); await m.wait_for_selector('.mslices', timeout=5000); await m.wait_for_timeout(300)
            ok(f'{tag}: the header link stays on the laptop layout', not await m.locator('.sp-next').is_visible())
            await m.locator('.mslices button.mrow[data-id="S1"]').tap(); await m.wait_for_timeout(250)
            det = m.locator('.mslices .msd')
            ok(f'{tag}: tapping a slice shows its story and criteria', 'so that my logbook fills itself.' in await det.inner_text() and await m.locator('.msd ul.scrit li').count() == 3)
            btn = m.locator('.msd [data-act="copyprompt"]')
            bb = await btn.bounding_box()
            ok(f'{tag}: Copy prompt is a 44 px target', bb and bb['height'] >= 44 and bb['width'] >= wd - 100)
            ok(f'{tag}: no sideways scroll', await m.evaluate('document.documentElement.scrollWidth <= innerWidth'))
            await m.screenshot(path=OUT + f's12-{tag}.png', full_page=True)
            await btn.tap(); await m.wait_for_timeout(250)
            mp = await m.evaluate('window.__clip')
            ok(f'{tag}: Copy prompt copies the slice prompt', mp.startswith('Build S1 · Log a daily entry in Phone project.\nWork in C:\\Projects\\phone on branch main.') and '  - Given no signal, when I save, then it is kept and sent later\n' in mp and '- Test: `npm test`' in mp)
            ok(f'{tag}: a toast says where to paste it', 'Copied the S1 prompt' in await toast(m))
            await m.evaluate(REFUSE)
            await m.locator('.msd [data-act="copyprompt"]').tap(); await m.wait_for_timeout(300)
            ok(f'{tag}: refused copy opens the sheet, selected', await m.locator('.sheet').is_visible() and await m.evaluate(SELECTED))
            fb = await m.locator('[data-act="copyslice"]').bounding_box()
            ok(f'{tag}: the sheet fits and its button is a touch target', fb and fb['height'] >= 44 and await m.evaluate('document.documentElement.scrollWidth <= innerWidth'))
            await m.screenshot(path=OUT + f's12-{tag}-refused.png')
            await mc.close()

        for n, c in checks: print(('PASS ' if c else 'FAIL ') + n)
        print(f'{sum(c for _, c in checks)}/{len(checks)} passed')
        print('ERRORS', errs)
        await b.close()

asyncio.run(main())
