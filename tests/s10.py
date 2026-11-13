"""S10 browser test: Claude Code handoff, with a mocked db, mocked documents and chats, and a stubbed clipboard."""
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
REPO = 'C:\\Projects\\hall-registration'

PRD = "# Hall registration\n\nFor students checking in to halls of residence.\n\n## Problem\n- Check-in week means a two-hour queue\n"
STORIES = "# Hall registration · slices\n\n## Must\n- [ ] S1 · Sign in with a matric number\n- [ ] S2 · Pick a room\n- [ ] S3 · Porter's check-in list\n\n## Should\n- [ ] S9 · Room swaps\n"
NFRS = "# NFRs\n\n| NFR | Requirement |\n| --- | --- |\n| Cost | $0 |\n| Reach | Phones on 3G |\n"
ARCH = "# Architecture\n\nTier 1, chosen in ADR 0001.\n\n## Stack\n- Static page on Cloudflare Pages\n- Firebase Spark: auth and Firestore\n\n### Data\n- rooms, students, check-ins\n\n## Hosting\n- Cloudflare Pages free plan\n\n## Context diagram\nStudents and porters use one web app.\n"
ADR1 = "# 0001: Host on Cloudflare\n\nStatus: Accepted · 2026-11-12\n\n## Decision\n\nCloudflare Pages.\n"
ADR2 = "# 0002: Backend\n\nStatus: Proposed\n\n## Context\n\nWe need auth.\n\n## Decision\n\nFirebase.\n"
ADR2_DRAFT = "# 0002: Backend\n\nStatus: Accepted\n\n## Context\n\nWe need auth.\n\n## Decision\n\nFirebase Spark plan.\n"
ARCH_NOSTACK = "# Architecture\n\nOne SvelteKit app.\n\n## Data\n- notes\n"
BIG = "# Big PRD\n\n" + ("- A long requirement line that keeps going to make this document large enough.\n" * 1500)

def doc(pid, key, text, phase='define', **kw):
    return {'pid': pid, 'phase': phase, 'key': key, 'text': text, '__ago': DAY, **kw}

SEED = {
    'projects/ph': {'name': 'Hall registration', 'phase': 'design', 'completed': {'discover': True, 'define': True}, 'checks': {'design': [True, False, False]},
                    'oneLiner': 'For students checking in to halls, an app that replaces the paper queue.', 'repo': REPO, '__ago': 3600000},
    'docs/ph~prd': doc('ph', 'prd', PRD), 'docs/ph~stories': doc('ph', 'stories', STORIES), 'docs/ph~nfrs': doc('ph', 'nfrs', NFRS),
    'docs/ph~architecture': doc('ph', 'architecture', ARCH, 'design'),
    'docs/ph~adr-a1': doc('ph', 'adr-a1', ADR1, 'design', kind='adr', n=1),
    'docs/ph~adr-a2': doc('ph', 'adr-a2', ADR2, 'design', kind='adr', n=2, draft={'text': ADR2_DRAFT, 'at': NOW - 600000, 'basedOn': 1, 'cut': False, 'base': ADR2, 'decisions': {}}),
    'chats/ph~design': {'messages': [], 'notes': {'stack': 'Not this one', 'hosting': ''}, 'free': False, 'trimmed': 0, 'updatedAt': 1},
    # nothing saved yet
    'projects/pn': {'name': 'Empty idea', 'phase': 'design', 'completed': {'discover': True, 'define': True}, 'checks': {}, '__ago': 2 * DAY},
    # stack from the Design coach's notes; a draft that was never used; a long document
    'projects/pq': {'name': 'Notes app', 'phase': 'design', 'completed': {'discover': True, 'define': True}, 'checks': {}, 'repo': 'C:\\Projects\\notes', '__ago': 3 * DAY},
    'docs/pq~architecture': doc('pq', 'architecture', ARCH_NOSTACK, 'design'),
    'docs/pq~stories': doc('pq', 'stories', '', draft={'text': STORIES, 'at': NOW - DAY, 'basedOn': 0, 'cut': False, 'base': '', 'decisions': {}}),
    'docs/pq~prd': doc('pq', 'prd', BIG),
    'chats/pq~design': {'messages': [], 'notes': {'stack': 'SvelteKit with TypeScript', 'hosting': 'Cloudflare Pages'}, 'free': False, 'trimmed': 0, 'updatedAt': 1},
    # Build without a repo folder
    'projects/pb': {'name': 'Bus tracker', 'phase': 'build', 'completed': {'discover': True, 'define': True, 'design': True}, 'checks': {}, '__ago': 4 * DAY},
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
    onSnapshot(cb, err){
      if (col === 'docs' && window.__docsFail){ setTimeout(() => err && err({code:'invalid_argument', message:'mock'}), 30); return () => {}; }
      if (col === 'docs' && window.__docsHang) return () => {};
      subs.push({col, f, cb}); setTimeout(() => cb(snapQ(col, f)), 30); return () => {};
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
  window.__store = S0; window.__docsFail = %FAIL%; window.__docsHang = %HANG%;
  window.__clip = null; window.__clipFail = false;
  Object.defineProperty(navigator, 'clipboard', {configurable:true, value:{writeText: async t => { if (window.__clipFail) throw new Error('denied'); window.__clip = t; }}});
  const sample = () => Promise.reject({code:'unavailable'}); sample.json = sample;
  const mcp = { async listTools(){ return {servers:[]}; }, async callTool(){ throw {code:'server_not_connected'}; }, watchTool(){ return () => {}; }, async invalidate(){} };
  window.claude = { use: async n => n === 'db' ? db : n === 'sample' ? sample : n === 'mcp' ? mcp : null };
})();
"""


def mock(fail=False, hang=False):
    return MOCK.replace('%SEED%', json.dumps(SEED)).replace('%FAIL%', json.dumps(fail)).replace('%HANG%', json.dumps(hang))


async def store(pg, k):
    return await pg.evaluate(f'window.__store[{json.dumps(k)}]')


async def rows(pg):
    return await pg.eval_on_selector_all('table.hfiles tbody tr', '''trs => trs.map(tr => ({path: tr.querySelector('.fp').innerText, from: tr.querySelector('.from').innerText,
        status: tr.querySelector('.st').innerText, warn: tr.querySelector('.st').classList.contains('warn'),
        on: tr.querySelector('input').checked, off: tr.querySelector('input').disabled}))''')


def block(prompt, path):   # one file's text inside the prompt
    m = re.search(r'^--- ' + re.escape(path) + r' ---\n(.*?)\n--- end of ' + re.escape(path) + ' ---$', prompt, re.S | re.M)
    return m.group(1) if m else None


async def prompt(pg):
    return await pg.eval_on_selector('#handoff-text', 'e => e.value')


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

        # 1. Ways in: Design's side panel
        await d.goto(URL + '#p-ph-design'); await d.wait_for_selector('.doctabs', timeout=8000); await d.wait_for_timeout(300)
        ok('Design side panel: Hand off to Claude Code', await d.locator('.sidelist a[href="#p-ph-handoff"]').count() == 1)
        # The framework: Design ends with an empty repo; S0 sets the app up in that folder, with Vite unless the architecture says otherwise
        ok('Design checklist: ends with an empty repo, not a scaffold', 'Repo created: a folder under C:\\Projects with git and a GitHub remote' in await d.text_content('.sidelist')
           and 'Repo scaffolded' not in await d.text_content('.sidelist'))
        fw = await d.evaluate('() => [docCoachContext(proj("ph"), emptyChat(), 0, "design"), DRAFT_SPEC.stories(proj("ph")), DRAFT_SPEC.architecture(proj("ph"))]')
        ok('Design coach: the app is set up in S0, in the same folder, with Vite', "The app itself is set up in Build's first slice, S0 · Walking skeleton: in that same folder, never a subfolder, with Vite (`npm create vite@latest .`)" in fw[0]
           and 'repo scaffolded' not in fw[0])
        ok('drafts: stories start with S0; the architecture\'s Stack ends with the set-up command', 'The first Must line is always "- [ ] S0 · Walking skeleton"' in fw[1] and 'Then number the stories S1' in fw[1]
           and 'ending with the command that sets the app up in the repo folder: `npm create vite@latest .`' in fw[2])
        await d.evaluate('location.hash = "#p-ph-handoff"'); await d.wait_for_selector('table.hfiles', timeout=8000); await d.wait_for_timeout(200)

        # 2. The page and its files
        ok('page: title, project link, state; project highlighted in the rail', await d.inner_text('.hhead h1') == 'Handoff to Claude Code' and await d.inner_text('.hhead .crumb') == 'Hall registration'
           and await d.inner_text('.hhead .hstate') == "In Design · Design isn't finished yet" and 'Hall registration' in await d.inner_text('.plist a[aria-current="page"]'))
        r = await rows(d)
        ok('files: approved docs, ADRs by file name, then the generated files', [x['path'] for x in r] == ['docs/PRD.md', 'docs/stories.md', 'docs/nfrs.md', 'docs/architecture.md',
           'docs/adr/0001-host-on-cloudflare.md', 'docs/adr/0002-backend.md', 'CLAUDE.md', '.claude/settings.json', '.claude/hooks/studio-check.cjs', 'docs/progress.md'])
        ok('files: where each comes from', [x['from'] for x in r] == ['Define', 'Define', 'Define', 'Design', 'Design', 'Design', 'Generated', 'Generated', 'Generated', 'Generated'])
        ok('status: approved, Musts counted', r[0]['status'] == 'Approved' and r[1]['status'] == 'Approved · 3 Musts' and r[6]['status'] == 'Stack, commands, Studio protocol' and r[9]['status'] == 'Empty log')
        ok('a doc with a draft waiting: unticked, amber marker, changes not reviewed', r[5]['status'] == '2 changes not reviewed' and r[5]['warn'] and not r[5]['on']
           and all(x['on'] for i, x in enumerate(r) if i != 5))
        ok('size per file and in total', await d.locator('table.hfiles td.sz').first.inner_text() != '' and re.fullmatch(r'9 files · [\d.]+ KB', ' '.join((await d.inner_text('#handoff-size')).split())) is not None)

        # 3. The prompt
        pr = await prompt(d)
        ok('prompt: names the folder and the branch', pr.startswith('You\'re taking over the build of "Hall registration" from The Studio.\nWork in C:\\Projects\\hall-registration on branch main.'))
        ok('prompt: stops if the folder is not a repo with a remote', "If it isn't, stop and tell me; don't create one." in pr)
        ok('prompt: keeps slice marks, an existing log and other CLAUDE.md sections', 'keep the [x] and [~] marks' in pr and 'Never replace a progress log' in pr and 'keep its other sections' in pr and 'add this Stop hook and keep everything else' in pr)
        ok('prompt: commit, push, Studio update', 'Commit as "docs: handoff from The Studio" and push to main.' in pr and 'End with a Studio update block' in pr)
        ok('prompt: each document exactly as saved', block(pr, 'docs/PRD.md') == PRD.strip() and block(pr, 'docs/stories.md') == STORIES.strip() and block(pr, 'docs/adr/0001-host-on-cloudflare.md') == ADR1.strip())
        ok('prompt: the unticked draft stays out', 'docs/adr/0002-backend.md' not in pr and 'Firebase Spark plan' not in pr)
        hook = block(pr, '.claude/hooks/studio-check.cjs'); sett = block(pr, '.claude/settings.json')
        ok('prompt: the Stop hook and its settings', hook and 'The Studio protocol check, run by Claude Code as a Stop hook.' in hook and sett and json.loads(sett)['hooks']['Stop'])
        ok('prompt: an empty progress log', block(pr, 'docs/progress.md') == '# Progress log\n\nNewest first. One entry per slice session. The Studio reads this file.')
        cm = block(pr, 'CLAUDE.md') or ''
        ok('CLAUDE.md: name, one-liner, what to read first', cm.startswith('# Hall registration\n\nFor students checking in to halls, an app that replaces the paper queue.\n\nRead docs/PRD.md, docs/stories.md, docs/nfrs.md, docs/architecture.md and docs/adr/ before changing anything.'))
        ok('CLAUDE.md: stack and hosting from the architecture doc', '## Stack\n- Static page on Cloudflare Pages\n- Firebase Spark: auth and Firestore\n\n### Data\n- rooms, students, check-ins\n\n### Hosting\n- Cloudflare Pages free plan\n\n## Commands' in cm and 'Not this one' not in cm)
        ok('CLAUDE.md: Commands left for Claude Code, then the protocol and rules', 'TBD: Claude Code fills this in from the repo' in cm and '## Studio protocol (every slice)' in cm and 'Studio update · hall-registration' in cm
           and '- $0 only: no paid services, no API keys.' in cm and 'Meet docs/nfrs.md' in cm and 'conflicts with the PRD or an ADR' in cm)
        ok('CLAUDE.md: S0 sets the app up in this folder with Vite, keeping the docs', '## Setting up the app (S0)\n- S0 · Walking skeleton sets the app up in this folder, never in a subfolder: `npm create vite@latest .`' in cm
           and 'Keep docs/, CLAUDE.md and .claude/ as they are.' in cm and cm.index('## Setting up the app (S0)') < cm.index('## Studio protocol'))
        ok('prompt fits in one paste: no long-prompt warning', await d.locator('.hprompt .notice').count() == 0)

        # 4. Ticking and unticking
        await d.check('#hsel-5'); await d.wait_for_timeout(150)
        pr = await prompt(d)
        ok('ticking the drafted ADR sends its saved version, not the draft', block(pr, 'docs/adr/0002-backend.md') == ADR2.strip() and 'Status: Accepted\n\n## Context' not in pr and '10 files' in await d.inner_text('#handoff-size'))
        await d.uncheck('#hsel-5'); await d.wait_for_timeout(100)
        for i in range(5): await d.uncheck(f'#hsel-{i}')
        await d.wait_for_timeout(150)
        ok('no document ticked: Copy waits, with the reason', await d.is_disabled('.hprompt [data-act="copyhandoff"]') and await d.inner_text('.hprompt .handoff-block') == 'Tick at least one document to hand off.')
        ok('CLAUDE.md follows the ticks', 'Read docs/' not in (block(await prompt(d), 'CLAUDE.md') or 'Read docs/'))
        for i in range(5): await d.check(f'#hsel-{i}')
        await d.wait_for_timeout(150)
        await d.focus('#hsel-0'); await d.keyboard.press('Space'); await d.wait_for_timeout(150)
        ok('keyboard: Space toggles a file and focus stays on it', not await d.is_checked('#hsel-0') and await d.evaluate('document.activeElement.id') == 'hsel-0')
        await d.keyboard.press('Space'); await d.wait_for_timeout(150)

        # 5. Folder and branch
        await d.fill('#h-branch', 'dev'); await d.wait_for_timeout(150)
        pr = await prompt(d)
        ok('branch: the prompt follows as you type', 'on branch dev.' in pr and 'push to dev.' in pr and await d.inner_text('.hsteps .hbranch') == 'dev' and await d.evaluate('document.activeElement.id') == 'h-branch')
        await d.fill('#h-branch', 'my branch'); await d.wait_for_timeout(150)
        ok('branch: a name git won\'t take is caught', await d.is_disabled('.hprompt [data-act="copyhandoff"]') and 'branch name' in await d.inner_text('.hprompt .handoff-block'))
        await d.fill('#h-branch', 'main'); await d.fill('#h-repo', ''); await d.wait_for_timeout(150)
        ok('folder: required', await d.is_disabled('.hprompt [data-act="copyhandoff"]') and await d.inner_text('.hprompt .handoff-block') == 'Enter the folder on your laptop that Claude Code will work in.')
        await d.fill('#h-repo', 'projects/hall'); await d.wait_for_timeout(150)
        ok('folder: a full path', 'full path' in await d.inner_text('.hprompt .handoff-block'))
        await d.fill('#h-repo', REPO); await d.wait_for_timeout(900)
        ok('folder and branch saved to the project (the Build monitor reads the same folder)', (await store(d, 'projects/ph'))['repo'] == REPO and (await store(d, 'projects/ph'))['branch'] == 'main'
           and await d.is_enabled('.hprompt [data-act="copyhandoff"]'))

        # 6. Copy
        await d.click('.hprompt [data-act="copyhandoff"]'); await d.wait_for_timeout(900)
        clip = await d.evaluate('window.__clip')
        ok('Copy: the whole prompt goes to the clipboard', clip == await prompt(d) and clip.count('--- end of ') == 9)
        rec = (await store(d, 'projects/ph')).get('handoff') or {}
        ok('Copy: remembered on the project', len(rec.get('files', [])) == 9 and rec.get('branch') == 'main' and rec.get('at', 0) > NOW)
        ok('Copy: toast and last-copied line', 'Copied: 9 files. Paste it into Claude Code in C:\\Projects\\hall-registration.' in await d.inner_text('.toast')
           and re.search(r'Last copied today \d\d:\d\d · 9 files to main', ' '.join((await d.inner_text('.hprompt')).split())) is not None)
        await d.evaluate('window.__clipFail = true; window.__exec = document.execCommand; document.execCommand = () => false; 0')   # both ways of copying refused
        await d.click('.hprompt [data-act="copyhandoff"]'); await d.wait_for_timeout(300)
        ok('Copy refused: says so and selects the prompt', "Couldn't copy" in await d.inner_text('.toast') and await d.evaluate('document.activeElement.id') == 'handoff-text'
           and await d.evaluate('(e => e.selectionEnd - e.selectionStart)(document.activeElement)') == len(clip))
        await d.evaluate('window.__clipFail = false; document.execCommand = window.__exec; 0')
        ok('desktop 1440: no sideways scroll; one primary button', await d.evaluate('document.documentElement.scrollWidth <= innerWidth') and await d.locator('.btn.primary:visible').count() == 1)
        await d.screenshot(path=OUT + 's10-handoff-1440-dark.png')

        # 7. Finishing Design opens the handoff; Build then says it was handed off
        await d.evaluate('location.hash = "#p-ph-design"'); await d.wait_for_selector('.doctabs', timeout=4000)
        await d.click('.stabs [data-tab="checklist"]'); await d.wait_for_timeout(150)
        await d.click('.sidelist [data-act="finish"]'); await d.wait_for_timeout(150)
        await d.click('.sidelist [data-act="finish"][data-force="1"]'); await d.wait_for_timeout(500)
        ok('Finish Design: on to Build, and the handoff opens', await d.evaluate('location.hash') == '#p-ph-handoff' and (await store(d, 'projects/ph'))['phase'] == 'build'
           and await d.inner_text('.hhead .hstate') == 'Design done · ready for Build')
        await d.evaluate('location.hash = "#p-ph"'); await d.wait_for_timeout(400)
        main = ' '.join((await d.inner_text('main')).split())
        ok('Build: says it was handed off and what to do next', re.search(r'Handed off to Claude Code today \d\d:\d\d\. When it has pushed, sync from the Claude desktop app on your laptop, or paste its Studio update\.', main) is not None)
        ok('Build: Hand off the docs again, beside the folder', await d.locator('a[href="#p-ph-handoff"]').count() >= 1 and 'Hand off the docs again' in main)
        await d.evaluate('location.hash = "#p-pb"'); await d.wait_for_timeout(400)
        ok('Build with no folder yet: points to the handoff', 'Coming from Design? Hand off the approved docs' in ' '.join((await d.inner_text('main')).split()))

        # 8. Empty, and the stack from the coach's notes
        await d.evaluate('location.hash = "#p-pn-handoff"'); await d.wait_for_selector('table.hfiles', timeout=4000); await d.wait_for_timeout(200)
        r = await rows(d)
        ok('nothing saved: says what to do, documents greyed out', 'Nothing to hand off yet.' in await d.inner_text('.pmain .notice') and all(x['off'] and x['status'] == 'Nothing saved yet' for x in r[:4])
           and await d.is_disabled('.hprompt [data-act="copyhandoff"]') and await d.inner_text('.hprompt .handoff-block') == 'Save at least one document in Define or Design first.')
        await d.evaluate('location.hash = "#p-pq-handoff"'); await d.wait_for_selector('table.hfiles', timeout=4000); await d.wait_for_timeout(400)
        r = await rows(d); pr = await prompt(d)
        ok('a draft never used: nothing to send', r[1]['path'] == 'docs/stories.md' and r[1]['off'] and r[1]['status'] == "Claude's draft isn't used yet")
        ok('stack from the Design coach when the architecture has none', '## Stack\n- SvelteKit with TypeScript\n- Cloudflare Pages\n' in (block(pr, 'CLAUDE.md') or ''))
        ok('a long prompt is flagged', 'This is a long prompt' in await d.inner_text('.hprompt .notice'))
        await ctx.close()

        # 9. Loading and error
        for (fail, hang, tag) in [(False, True, 'loading'), (True, False, 'error')]:
            cx = await b.new_context(viewport={'width': 1440, 'height': 900})
            k = await cx.new_page(); k.on('pageerror', lambda e, t=tag: errs.append(t + ': ' + str(e)))
            await k.add_init_script(mock(fail=fail, hang=hang))
            await k.goto(URL + '#p-ph-handoff'); await k.wait_for_selector('.hhead', timeout=8000); await k.wait_for_timeout(500)
            if hang:
                ok('loading: shapes, Copy waits', await k.locator('.pmain [aria-busy="true"] .skrow').count() == 5 and await k.is_disabled('.hprompt [data-act="copyhandoff"]'))
            else:
                ok('error: says the documents can\'t be loaded, Copy waits', "These documents can't be loaded." in await k.inner_text('.pmain .errbox') and await k.is_disabled('.hprompt [data-act="copyhandoff"]'))
            await cx.close()

        # 10. 1024 and light
        cx = await b.new_context(viewport={'width': 1024, 'height': 768}, color_scheme='light')
        k = await cx.new_page(); k.on('pageerror', lambda e: errs.append('1024: ' + str(e)))
        await k.add_init_script(mock())
        await k.goto(URL + '#p-ph-handoff'); await k.wait_for_selector('table.hfiles', timeout=8000); await k.wait_for_timeout(300)
        ok('1024 light: no sideways scroll; Copy visible', await k.evaluate('document.documentElement.scrollWidth <= innerWidth') and await k.is_visible('.hprompt [data-act="copyhandoff"]'))
        await k.screenshot(path=OUT + 's10-handoff-1024-light.png', full_page=True)
        await cx.close()

        # 11. Phones: a full-screen sheet with Copy at the bottom
        for (wd, ht, scheme) in [(390, 844, 'dark'), (360, 800, 'light')]:
            tag = f'{wd}'
            mc = await b.new_context(viewport={'width': wd, 'height': ht}, color_scheme=scheme, has_touch=True, is_mobile=True)
            m = await mc.new_page(); m.on('pageerror', lambda e, t=tag: errs.append(t + ': ' + str(e)))
            await m.add_init_script(mock())
            await m.goto(URL + '#p-ph-handoff'); await m.wait_for_selector('table.hfiles', timeout=8000); await m.wait_for_timeout(300)
            ok(f'{tag}: no bottom nav, Copy fixed at the bottom, no sideways scroll', await m.locator('.mnav').count() == 0 and await m.is_visible('.hbar [data-act="copyhandoff"]')
               and not await m.is_visible('.hprompt [data-act="copyhandoff"]') and await m.evaluate('document.documentElement.scrollWidth <= innerWidth')
               and await m.eval_on_selector('.hbar', 'e => Math.round(e.getBoundingClientRect().bottom) === innerHeight'))
            hs = await m.eval_on_selector_all('table.hfiles .hcb', 'els => els.map(e => e.getBoundingClientRect().height)')
            ok(f'{tag}: file rows with 44px tick targets, status under the path', min(hs) >= 44 and await m.is_hidden('table.hfiles thead') and await m.is_hidden('table.hfiles td.from'))
            await m.screenshot(path=OUT + f's10-handoff-{tag}-{scheme}.png')
            await m.tap('label.hcb:has(#hsel-2)', position={'x': 6, 'y': 6}); await m.wait_for_timeout(200)   # the corner of its 44px target, not the box itself
            ok(f'{tag}: tapping near a tick toggles it', not await m.is_checked('#hsel-2') and 'docs/nfrs.md ---' not in await prompt(m))
            await m.tap('.hbar [data-act="copyhandoff"]'); await m.wait_for_timeout(500)
            ok(f'{tag}: Copy from the bottom bar', (await m.evaluate('window.__clip') or '').startswith('You\'re taking over the build of "Hall registration"'))
            await m.tap('.hhead a.mob-only'); await m.wait_for_timeout(300)
            ok(f'{tag}: back goes to the project', await m.evaluate('location.hash') == '#p-ph' and await m.locator('.mnav').count() == 1)
            await mc.close()

        await b.close()
        passed = sum(1 for _, c in checks if c)
        print(f'{passed}/{len(checks)} passed')
        for nm, c in checks:
            if not c: print('  FAILED:', nm)
        print('page errors:', errs or 'none')

asyncio.run(main())
