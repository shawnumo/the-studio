"""S16 browser test: mocked artifact db + mocked host:filesystem MCP server."""
import asyncio, json
from playwright.async_api import async_playwright
import os
from pathlib import Path
HERE = Path(__file__).resolve().parent
URL = (HERE.parent / 'src' / 'index.html').as_uri()
OUT = str(HERE / 'out') + os.sep            # screenshots land in tests/out/
os.makedirs(OUT, exist_ok=True)
LAUNCH = {'executable_path': os.environ['CHROME']} if os.environ.get('CHROME') else {}   # optional: your own Chrome

STORIES = open(HERE / 'fx_stories.md').read().replace('\n', '\r\n')
PROGRESS = open(HERE / 'fx_progress.md').read().replace('\n', '\r\n')
REFLOG = open(HERE / 'fx_reflog.txt').read()

MOCK = r"""
(() => {
  const FILES = %FILES%;
  const store = {}; const subs = [];
  const snap = col => { const docs = Object.keys(store).filter(k => k.startsWith(col + '/')).map(k => ({id:k.split('/')[1], exists:true, data:()=>store[k]})); return {docs, metadata:{fromCache:false}}; };
  const notify = col => subs.filter(s => s.col === col).forEach(s => s.cb(snap(col)));
  const db = { collection(col){ return {
    onSnapshot(cb){ subs.push({col, cb}); setTimeout(() => cb(snap(col)), 30); return () => {}; },
    doc(id){ const k = col + '/' + id; return { async set(d){ store[k] = JSON.parse(JSON.stringify(d)); setTimeout(()=>notify(col), 20); }, async delete(){ delete store[k]; setTimeout(()=>notify(col), 20); } }; }
  }; } };
  const now = Date.now();
  store['projects/pstudio'] = {name:'The Studio', phase:'build', completed:{discover:true, define:true, design:true}, checks:{}, repo:'C:\\Projects\\the-studio', liveUrl:'https://claude.ai/artifact/58eAFcowX6ge7VZ1v3vunK', createdAt:now-86400000*2, updatedAt:now-86400000};
  store['projects/pmafia'] = {name:'Mafia', phase:'ship', completed:{discover:true, define:true, design:true, build:true}, checks:{}, createdAt:now-86400000*40, updatedAt:now-86400000*3};
  store['projects/phall'] = {name:'Hall registration', phase:'design', completed:{discover:true, define:true}, checks:{design:[true,false,false]}, nextStep:'Pick Firebase or Supabase', createdAt:now-86400000*9, updatedAt:now-86400000*5};
  window.__store = store; window.__files = FILES; window.__calls = [];
  window.__host = %HOST%; window.__delay = 0; window.__fail = null; window.__payloadString = false;
  const mcp = {
    async listTools(server){ return {servers: window.__host === 'listed' ? [{server:'host:filesystem', authStatus:'unknown', tools:[{name:'read_text_file', description:''},{name:'edit_file', description:''}]}] : []}; },
    async callTool(server, tool, input){
      window.__calls.push({tool, input});
      if (window.__host !== 'listed') throw {code:'server_not_connected', message:'no host'};
      if (window.__delay){ const d = window.__delay; window.__delay = 0; await new Promise(r => setTimeout(r, d)); }
      if (window.__fail){ const f = window.__fail; window.__fail = null; throw f; }
      const text = FILES[input.path];
      if (text === undefined) throw {code:'tool_error', message:"ENOENT: no such file or directory, open '" + input.path + "'"};
      if (tool === 'read_text_file'){
        let t = text; if (input.tail){ t = t.split('\n').slice(-input.tail).join('\n'); }
        return window.__payloadString ? {content:[{type:'text', text:t}], payload:t} : {content:[{type:'text', text:t}], structuredContent:{content:t}, payload:{content:t}};
      }
      if (tool === 'edit_file'){
        let t = text;
        for (const e of input.edits){ if (!t.includes(e.oldText)) throw {code:'tool_error', message:'Could not find exact match for edit'}; t = t.replace(e.oldText, e.newText); }
        FILES[input.path] = t; return {content:[{type:'text', text:'diff'}], payload:'diff'};
      }
      throw {code:'not_in_manifest', message:'no'};
    },
    watchTool(){ return () => {}; }, async invalidate(){}
  };
  window.claude = { use: async n => n === 'db' ? db : n === 'mcp' ? mcp : null };
})();
"""

def mock(host):
    files = {
        'C:\\Projects\\the-studio\\docs\\stories.md': STORIES,
        'C:\\Projects\\the-studio\\docs\\progress.md': PROGRESS,
        'C:\\Projects\\the-studio\\.git\\HEAD': 'ref: refs/heads/main\r\n',
        'C:\\Projects\\the-studio\\.git\\logs\\HEAD': REFLOG,
        'C:\\Projects\\mafia\\README.md': '# Mafia',
    }
    return MOCK.replace('%FILES%', json.dumps(files)).replace('%HOST%', json.dumps(host))


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(**LAUNCH)
        errs = []; checks = []
        def ok(name, cond): checks.append((name, bool(cond)))

        # ---------- Desktop, Claude app with the file server ----------
        d = await b.new_page(viewport={'width':1440,'height':900})
        d.on('pageerror', lambda e: errs.append('desk: ' + str(e)))
        await d.add_init_script(mock('listed'))
        await d.add_init_script("window.__delay = 3200;")
        await d.goto(URL + '#p-pstudio')
        await d.wait_for_timeout(2900)
        bar = await d.inner_text('.syncbar')
        ok('slow first call shows Connecting', 'Connecting to your laptop' in bar)
        await d.screenshot(path=OUT + 's16-connecting.png')
        await d.wait_for_selector('table.slices', timeout=6000)
        await d.wait_for_timeout(200)
        bar = await d.inner_text('.syncbar')
        ok('synced bar', 'Read from your repo' in bar and 'the-studio · main' in bar)
        rows = await d.eval_on_selector_all('table.slices tbody tr:not(.grp)', 'els => els.map(e => e.innerText.replace(/\\s+/g, " "))')
        ok('slice count', len(rows) == 15)
        s0 = next(r for r in rows if r.startswith('S0'))
        ok('S0 done with commit from reflog', 'Done' in s0 and '70fd6cf' in s0)
        ok('S2 check', any(r.startswith('S2') and 'Check on your phone' in r for r in rows))
        ok('S16 next', any(r.startswith('S16') and 'Next' in r for r in rows))
        log = await d.inner_text('.logsec')
        ok('log entries', 'Walking skeleton' in log and 'Sync test' in log)
        ok('no email stored', 'example.com' not in json.dumps(await d.evaluate('window.__store')))
        ok('callout lists 3 checks', '3 slices are built' in await d.inner_text('.callout'))
        await d.screenshot(path=OUT + 's16-desk.png', full_page=True)

        # Mark S2 done -> edit_file on the laptop, then resync
        await d.click('.callout [data-id="S2"]')
        await d.wait_for_timeout(500)
        calls = await d.evaluate('window.__calls.filter(c => c.tool === "edit_file")')
        ok('edit_file called with exact line', calls and calls[0]['input']['edits'][0]['oldText'].startswith('- [~] S2 ·') and calls[0]['input']['edits'][0]['newText'].startswith('- [x] S2 ·'))
        rows = await d.eval_on_selector_all('table.slices tbody tr:not(.grp)', 'els => els.map(e => e.innerText.replace(/\\s+/g, " "))')
        ok('S2 done after resync', any(r.startswith('S2') and 'Done' in r for r in rows))

        # Board: needs-you text and slice counts
        await d.goto(URL + '#board'); await d.wait_for_timeout(500)
        needs = await d.inner_text('.needs')
        ok('board next step from slices', 'Check S8, S15 on your phone' in needs and 'slices 2/15' in needs)
        await d.screenshot(path=OUT + 's16-board.png')

        # Error: file server not running
        await d.goto(URL + '#p-pstudio'); await d.wait_for_timeout(300)
        await d.evaluate("window.__fail = {code:'server_not_connected', message:'x'}")
        await d.click('.syncbar [data-act="sync"]'); await d.wait_for_timeout(300)
        bar = await d.inner_text('.syncbar')
        ok('server_not_connected error keeps snapshot', "Couldn't read the repo" in bar and 'snapshot from' in bar)
        await d.screenshot(path=OUT + 's16-error.png')

        # Missing docs/stories.md -> setup prompt
        await d.goto(URL + '#p-pmafia-build'); await d.wait_for_timeout(300)
        ok('connect form shown', await d.is_visible('#p-repo'))
        await d.fill('#p-repo', '"C:\\Projects\\mafia\\"')
        await d.click('.slicesec [data-act="sync"]'); await d.wait_for_timeout(400)
        bar = await d.inner_text('.syncbar')
        ok('missing file explained', "no docs/stories.md in C:\\Projects\\mafia" in bar)
        await d.screenshot(path=OUT + 's16-missing.png')
        await d.click('.syncbar [data-act="setup"]'); await d.wait_for_timeout(200)
        prompt = await d.input_value('#setup-text')
        ok('setup prompt has hook, settings, protocol', 'studio-check.cjs' in prompt and '"Stop"' in prompt and 'Studio update · mafia' in prompt and '${CLAUDE_PROJECT_DIR}' in prompt)
        await d.screenshot(path=OUT + 's16-setup.png')
        await d.keyboard.press('Escape')

        # Jump a project to Build
        await d.goto(URL + '#p-phall-build'); await d.wait_for_timeout(300)
        await d.click('[data-act="jump"]'); await d.wait_for_timeout(300)
        st = await d.evaluate("window.__store['projects/phall']")
        ok('jump moves phase', st['phase'] == 'build' and st['completed'].get('design') is True)

        # ---------- Phone: no file server ----------
        m = await b.new_page(viewport={'width':390,'height':844}, has_touch=True, is_mobile=True)
        m.on('pageerror', lambda e: errs.append('mob: ' + str(e)))
        await m.add_init_script(mock('none'))
        # seed a snapshot as if synced earlier from the laptop
        await m.add_init_script("""(() => { const s = window.__store; })();""")
        await m.goto(URL + '#p-pstudio')
        await m.wait_for_timeout(500)
        txt = await m.inner_text('main')
        ok('phone without snapshot explains', 'Sync runs when The Studio is open in the Claude desktop app' in txt)
        # paste an update
        await m.click('.syncbar [data-act="paste"]'); await m.wait_for_timeout(150)
        await m.fill('#paste-text', 'nothing useful here'); await m.click('#pasteForm [type="submit"]'); await m.wait_for_timeout(150)
        ok('paste error shown', "Couldn't find any slice lines" in await m.inner_text('.sheet'))
        upd = open(HERE / 'fx_update.txt').read()
        await m.fill('#paste-text', upd); await m.click('#pasteForm [type="submit"]'); await m.wait_for_timeout(150)
        prev = await m.inner_text('.sheet')
        ok('paste preview', 'S16 built' in prev and '1 new' in prev and '41 passed' in prev)
        await m.screenshot(path=OUT + 's16-m-paste.png')
        await m.click('[data-act="applypaste"]'); await m.wait_for_timeout(300)
        txt = await m.inner_text('main')
        ok('pasted snapshot shown', 'From a pasted update' in txt and 'S16' in txt)
        await m.screenshot(path=OUT + 's16-m-slices.png', full_page=True)
        # mark done on the phone
        await m.click('.callout [data-act="markdone"]'); await m.wait_for_timeout(300)
        snap = await m.evaluate("window.__store['syncs/pstudio']")
        ok('phone mark stored', 'S16' in (snap.get('marks') or {}))
        await m.click('.btabs [data-tab="log"]'); await m.wait_for_timeout(150)
        await m.screenshot(path=OUT + 's16-m-log.png', full_page=True)
        ok('log tab shows log, hides slices', await m.is_visible('.logsec') and not await m.is_visible('.slicesec'))
        # now the same data reaches a laptop: switch host on and write marks
        await m.evaluate("window.__host = 'listed'; detectHost();"); await m.wait_for_timeout(300)
        await m.click('.btabs [data-tab="slices"]'); await m.wait_for_timeout(500)
        files = await m.evaluate('window.__files')
        # auto-sync ran on host detection (project open) and replaced the pasted snapshot
        await m.screenshot(path=OUT + 's16-m-after.png', full_page=True)
        notice = await m.query_selector('.notice')
        ok('pending mark notice after laptop sync', notice is not None and 'S16' in await notice.inner_text())
        await m.click('[data-act="writemarks"]'); await m.wait_for_timeout(500)
        calls = await m.evaluate('window.__calls.filter(c => c.tool === "edit_file")')
        ok('writemarks edits the S16 line', len(calls) == 1 and calls[0]['input']['edits'][0]['oldText'].startswith('- [ ] S16') and calls[0]['input']['edits'][0]['newText'].startswith('- [x] S16'))

        # payload as plain string variant
        d2 = await b.new_page(viewport={'width':1024,'height':768})
        d2.on('pageerror', lambda e: errs.append('d2: ' + str(e)))
        await d2.add_init_script(mock('listed')); await d2.add_init_script('window.__payloadString = true;')
        await d2.goto(URL + '#p-pstudio'); await d2.wait_for_selector('table.slices', timeout=5000)
        ok('string payload parses', '70fd6cf' in await d2.inner_text('table.slices'))
        await d2.screenshot(path=OUT + 's16-1024.png')

        for n, c in checks: print(('PASS ' if c else 'FAIL ') + n)
        print('ERRORS', errs)
        await b.close()
asyncio.run(main())
