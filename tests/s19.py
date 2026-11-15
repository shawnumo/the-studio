"""S19 browser test: archive projects off the board and restore them, with a mocked db and a mocked Claude."""
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
ALL = ['discover', 'define', 'design', 'build', 'ship']
def short(ts):   # what shortDate() shows in en-US
    d = datetime.datetime.fromtimestamp(ts / 1000); return d.strftime('%b ') + str(d.day)

SEED = {
    'projects/pa': {'name': 'SIWES logbook', 'phase': 'build', 'completed': {k: True for k in ALL[:3]}, 'checks': {'build': [True, False, False, False]}, 'nextStep': 'Supervisor sign-off', 'oneLiner': '', '__ago': DAY},
    'projects/pb': {'name': 'Hall registration', 'phase': 'define', 'completed': {'discover': True}, 'checks': {}, 'oneLiner': '', '__ago': 2 * DAY},
    'projects/pc': {'name': 'Budget app', 'phase': 'discover', 'completed': {}, 'checks': {}, 'oneLiner': '', '__ago': 3 * DAY},
    'projects/pdone': {'name': 'Mafia', 'phase': 'ship', 'completed': {k: True for k in ALL}, 'checks': {}, 'oneLiner': '', 'version': '1.0.0',
                       'versions': [{'v': '1.0.0', 'at': SHIP_AT, 'url': 'https://mafia-game.pages.dev/'}], 'liveUrl': 'https://mafia-game.pages.dev/', '__ago': 4 * DAY},
    'projects/parch': {'name': 'Old idea', 'phase': 'design', 'completed': {'discover': True, 'define': True}, 'checks': {}, 'oneLiner': '', 'archived': True, 'archivedAt': NOW - 3 * DAY, '__ago': 3 * DAY},
}
SEED_ONLY_ARCHIVED = {'projects/parch': SEED['projects/parch']}

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
  Object.defineProperty(navigator, 'clipboard', {configurable:true, value:{writeText: async t => { window.__clip = t; }}});
  const sample = () => Promise.reject({code:'unavailable'}); sample.json = sample;
  const mcp = { async listTools(){ return {servers: []}; }, async callTool(){ throw {code:'tool_error', message:'ENOENT'}; }, watchTool(){ return () => {}; }, async invalidate(){} };
  window.claude = { use: async n => n === 'db' ? db : n === 'sample' ? sample : n === 'mcp' ? mcp : null };
})();
"""
def mock(seed=None):
    return MOCK.replace('%SEED%', json.dumps(SEED if seed is None else seed))


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
        async def P(pg, k):
            return await pg.evaluate(f'window.__store["projects/{k}"]')
        async def rail(pg):
            return await pg.inner_text('.rail .plist')
        async def focused(pg):
            return await pg.evaluate('(() => { const e = document.activeElement; return e ? (e.dataset.act || e.id || e.tagName) : ""; })()')
        today = short(NOW)

        # ---------- Desktop 1440, dark ----------
        ctx = await b.new_context(viewport={'width': 1440, 'height': 900}, color_scheme='dark', locale='en-US')
        d = await ctx.new_page(); d.on('pageerror', lambda e: errs.append('desk: ' + str(e)))
        await d.add_init_script(mock())
        await d.goto(URL + '#board'); await d.wait_for_selector('#h-needs', timeout=8000); await d.wait_for_timeout(400)
        main_t = await d.inner_text('main')
        ok('an archived project is off the board and the rail', 'SIWES logbook' in main_t and 'Old idea' not in main_t and 'Old idea' not in await rail(d) and 'SIWES logbook' in await rail(d))

        # Archive from Build's side panel: confirm, then stay
        await d.goto(URL + '#p-pa'); await d.wait_for_selector('.pside [data-act="askarchive"]', timeout=8000); await d.wait_for_timeout(200)
        ok('Archive sits beside Delete project', await d.locator('.pside .projacts [data-act="askarchive"]').is_visible() and await d.locator('.pside .projacts [data-act="askdelete"]').is_visible()
           and 'ghost' in await d.locator('.pside [data-act="askarchive"]').get_attribute('class'))
        await d.click('.pside [data-act="askarchive"]'); await d.wait_for_timeout(150)
        g = d.locator('.pside .gate')
        ok('Archive asks first: what it does, nothing deleted', await g.is_visible() and 'Archive SIWES logbook?' in await g.inner_text() and 'It leaves the board and the project list.' in await g.inner_text()
           and 'Nothing in it is deleted' in await g.inner_text() and await focused(d) == 'archive')
        await d.click('[data-act="cancelarch"]'); await d.wait_for_timeout(150)
        ok('Keep it: no change, focus back on Archive', await d.locator('.pside .gate').count() == 0 and await focused(d) == 'askarchive' and not (await P(d, 'pa')).get('archived'))
        await d.click('.pside [data-act="askarchive"]'); await d.wait_for_timeout(150)
        await d.click('.pside .gate [data-act="archive"]'); await d.wait_for_timeout(300)
        ban = d.locator('.banner.arch')
        ok('you stay on the project, with the Archived banner and Restore', await d.evaluate('location.hash') == '#p-pa' and await ban.is_visible()
           and f'Archived on {today}. It\'s off the board, and nothing in it was deleted.' in await ban.inner_text() and await focused(d) == 'restore')
        ok('a toast says so', "Archived SIWES logbook. It's off the board; Restore brings it back." in await toast(d))
        ok('it leaves the rail at once; the rail marks Shipped', 'SIWES logbook' not in await rail(d) and await d.locator('.rail a[href="#shipped"][aria-current="page"]').count() == 1)
        ok('the side panel offers Restore in place of Archive', await d.locator('.pside [data-act="restore"]').is_visible() and await d.locator('.pside [data-act="askarchive"]').count() == 0)
        await d.wait_for_timeout(750); p = await P(d, 'pa')
        ok('saved: archived with the time, nothing else changed', p['archived'] is True and abs(p['archivedAt'] - int(time.time() * 1000)) < 60000 and p['checks']['build'][:2] == [True, False]
           and p['nextStep'] == 'Supervisor sign-off' and p['phase'] == 'build')

        await d.goto(URL + '#board'); await d.wait_for_selector('#h-needs', timeout=5000); await d.wait_for_timeout(200)
        main_t = await d.inner_text('main')
        ok('the board drops it, Needs you too', 'SIWES logbook' not in main_t and await d.inner_text('#h-needs .n') == '2')
        await d.click('#h-needs'); await d.keyboard.press('1'); await d.wait_for_timeout(250)
        ok('board number keys skip it', await d.evaluate('location.hash') not in ('#p-pa', '#board') and (await d.evaluate('location.hash')).startswith('#p-'))

        # The Archived group at the foot of Shipped
        await d.goto(URL + '#shipped'); await d.wait_for_selector('.archsec', timeout=5000); await d.wait_for_timeout(200)
        tg = d.locator('[data-act="togglearch"]')
        ok('Shipped keeps its table; Archived sits below it, collapsed, with a count', await d.locator('table.ships').is_visible() and ' '.join((await tg.inner_text()).split()) == 'Archived 2'
           and await tg.get_attribute('aria-expanded') == 'false' and not await d.locator('#arch-list').is_visible()
           and await d.evaluate('document.querySelector("table.ships").compareDocumentPosition(document.querySelector(".archsec")) & Node.DOCUMENT_POSITION_FOLLOWING') > 0)
        await tg.click(); await d.wait_for_timeout(150)
        rows = d.locator('#arch-list li')
        r0, r1 = await rows.nth(0).inner_text(), await rows.nth(1).inner_text()
        ok('open: newest first, each with its phase and when it was archived', await tg.get_attribute('aria-expanded') == 'true' and await rows.count() == 2
           and 'SIWES logbook' in r0 and 'Build' in r0 and f'Archived {today}' in r0 and 'Old idea' in r1 and 'Design' in r1 and f'Archived {short(NOW - 3 * DAY)}' in r1)
        ok('the toggle keeps focus; Enter closes it', await focused(d) == 'togglearch')
        await d.keyboard.press('Enter'); await d.wait_for_timeout(150)
        ok('keyboard: closed again', await tg.get_attribute('aria-expanded') == 'false')
        await d.keyboard.press('Enter'); await d.wait_for_timeout(150)
        await d.click('[aria-label="Restore SIWES logbook"]'); await d.wait_for_timeout(300)
        ok('Restore from the group: back on the board in its phase', 'Restored SIWES logbook to the board, in Build.' in await toast(d) and ' '.join((await tg.inner_text()).split()) == 'Archived 1'
           and 'SIWES logbook' in await rail(d) and await focused(d) == 'togglearch')
        await d.wait_for_timeout(750)
        ok('saved: not archived any more', (await P(d, 'pa'))['archived'] is False and (await P(d, 'pa'))['archivedAt'] == 0)
        await d.goto(URL + '#board'); await d.wait_for_timeout(300)
        ok('the board has it again', 'SIWES logbook' in await d.inner_text('main'))

        # A shipped project: archive from Ship's side panel, restore from the banner
        await d.goto(URL + '#p-pdone'); await d.wait_for_selector('.pside [data-act="askarchive"]', timeout=5000)
        await d.click('.pside [data-act="askarchive"]'); await d.wait_for_timeout(150)
        ok('a shipped project: it leaves the Shipped list', 'It leaves the Shipped list.' in await d.inner_text('.pside .gate'))
        await d.click('.pside .gate [data-act="archive"]'); await d.wait_for_timeout(300)
        ok("its banner says it's off the Shipped list", "It's off the Shipped list, and nothing in it was deleted." in await d.inner_text('.banner.arch'))
        await d.goto(URL + '#shipped'); await d.wait_for_selector('.archsec', timeout=5000); await d.wait_for_timeout(200)
        ok('the group stays open between visits', await d.get_attribute('[data-act="togglearch"]', 'aria-expanded') == 'true')
        ok('Shipped: nothing shipped now, Mafia in Archived with its version', 'Nothing shipped yet' in await d.inner_text('main') and 'v1.0.0 · shipped' in await d.inner_text('#arch-list li:first-child')
           and ' '.join((await d.locator('[data-act="togglearch"]').inner_text()).split()) == 'Archived 2')
        await d.click('#arch-list a[href="#p-pdone"]'); await d.wait_for_timeout(300)
        ok('its link opens it, banner and all', await d.evaluate('location.hash') == '#p-pdone' and await d.locator('.banner.arch').is_visible())
        await d.click('.banner.arch [data-act="restore"]'); await d.wait_for_timeout(300)
        ok('Restore from the banner: back to Shipped', 'Restored Mafia to Shipped.' in await toast(d) and await d.locator('.banner.arch').count() == 0 and await d.locator('.pside [data-act="askarchive"]').is_visible())
        await d.goto(URL + '#shipped'); await d.wait_for_timeout(300)
        ok('Shipped lists it again', 'Mafia' in await d.inner_text('table.ships'))

        # A link to an archived project in Design: the fixed document layout still fits
        await d.goto(URL + '#p-parch'); await d.wait_for_selector('.banner.arch', timeout=5000); await d.wait_for_timeout(300)
        ok('a link to an archived project opens it with the banner', 'Archived on' in await d.inner_text('.banner.arch') and await d.locator('.pbody.docp').is_visible())
        ok('the document layout still fits the window', await d.evaluate('document.querySelector(".pbody.docp").getBoundingClientRect().bottom <= innerHeight + 1 && document.documentElement.scrollHeight <= innerHeight + 1'))
        await d.screenshot(path=OUT + 's19-desk-archived-doc.png')
        await d.click('.stabs [data-tab="checklist"]'); await d.wait_for_timeout(200)
        ok('Define and Design: Restore in the Checklist panel, beside Delete', await d.locator('.sidelist [data-act="restore"]').is_visible() and await d.locator('.sidelist [data-act="askdelete"]').is_visible())
        await d.click('.banner.arch [data-act="restore"]'); await d.wait_for_timeout(300)
        ok('restored: back on the board in Design', 'Restored Old idea to the board, in Design.' in await toast(d) and 'Old idea' in await rail(d))

        # Define: archive from the Checklist panel; the handoff shows the banner too
        await d.goto(URL + '#p-pb'); await d.wait_for_selector('.stabs', timeout=5000)
        await d.click('.stabs [data-tab="checklist"]'); await d.wait_for_timeout(200)
        await d.click('.sidelist [data-act="askarchive"]'); await d.wait_for_timeout(150)
        await d.click('.sidelist .gate [data-act="archive"]'); await d.wait_for_timeout(300)
        ok('Define: archived from the Checklist panel', await d.locator('.banner.arch').is_visible() and 'Hall registration' not in await rail(d))
        await d.goto(URL + '#p-pb-handoff'); await d.wait_for_timeout(400)
        ok('the handoff of an archived project shows the banner', await d.locator('.banner.arch').is_visible())
        await d.evaluate("window.dispatchEvent(new Event('offline')); 0"); await d.wait_for_timeout(150)
        ok('offline: both banners', await d.locator('.banner').count() == 2 and "You're offline" in await d.inner_text('main'))
        await d.evaluate("window.dispatchEvent(new Event('online')); 0"); await d.wait_for_timeout(150)
        await d.goto(URL + '#p-pc'); await d.wait_for_timeout(400)
        ok('Discover: Archive beside Delete project', await d.locator('.pside .projacts [data-act="askarchive"]').count() == 1 and await d.locator('.pside .projacts [data-act="askdelete"]').count() == 1)

        # Another device archives a project: the board drops it live
        await d.goto(URL + '#board'); await d.wait_for_selector('#h-needs', timeout=5000); await d.wait_for_timeout(300)
        cur = await P(d, 'pc')
        await d.evaluate("(c => window.__remote('projects/pc', Object.assign({}, c, {archived:true, archivedAt:Date.now()})))(%s)" % json.dumps(cur)); await d.wait_for_timeout(300)
        ok('archived on another device: gone from the board at once', 'Budget app' not in await d.inner_text('main') and 'Budget app' not in await rail(d))

        # Reload: archived stays archived
        await d.wait_for_timeout(750); dbsnap = await d.evaluate('localStorage.getItem("__mockdb")')
        r = await ctx.new_page(); r.on('pageerror', lambda e: errs.append('reload: ' + str(e)))
        await r.add_init_script('if (!window.name){ window.name = "seeded"; localStorage.setItem("__mockdb", %s); }' % json.dumps(dbsnap))
        await r.add_init_script(mock())
        await r.goto(URL + '#shipped'); await r.wait_for_selector('.archsec', timeout=8000); await r.wait_for_timeout(300)
        await r.click('[data-act="togglearch"]'); await r.wait_for_timeout(150)
        txt = await r.inner_text('#arch-list')
        ok('after a reload: both archived projects are in the group', await r.locator('#arch-list li').count() == 2 and 'Hall registration' in txt and 'Define' in txt and 'Budget app' in txt and 'Discover' in txt)
        for k in ['Hall registration', 'Budget app']:
            await r.click(f'[aria-label="Restore {k}"]'); await r.wait_for_timeout(250)
        ok('nothing archived: a hint says how, no toggle', await r.locator('[data-act="togglearch"]').count() == 0 and 'Archived projects land here. Archive one from its side panel' in await r.inner_text('.archsec'))
        await r.close()
        await ctx.close()

        # ---------- 1024, light ----------
        cx = await b.new_context(viewport={'width': 1024, 'height': 768}, color_scheme='light', locale='en-US')
        k = await cx.new_page(); k.on('pageerror', lambda x: errs.append('1024: ' + str(x)))
        await k.add_init_script(mock())
        await k.goto(URL + '#shipped'); await k.wait_for_selector('.archsec', timeout=8000); await k.wait_for_timeout(300)
        await k.click('[data-act="togglearch"]'); await k.wait_for_timeout(150)
        ok('1024 light: the group fits, no sideways scroll', await k.evaluate('document.documentElement.scrollWidth <= innerWidth') and await k.locator('#arch-list [data-act="restore"]').is_visible())
        await k.screenshot(path=OUT + 's19-1024-light.png', full_page=True)
        await k.goto(URL + '#p-parch-design'); await k.wait_for_selector('.banner.arch', timeout=5000); await k.wait_for_timeout(200)
        ok('1024 light: the banner fits', await k.evaluate('document.documentElement.scrollWidth <= innerWidth') and await k.locator('.banner.arch [data-act="restore"]').is_visible())
        await cx.close()

        # ---------- Phones: 390 dark and 360 light ----------
        for wd, ht, scheme, tag in [(390, 844, 'dark', 'm390'), (360, 800, 'light', 'm360')]:
            mc = await b.new_context(viewport={'width': wd, 'height': ht}, color_scheme=scheme, has_touch=True, is_mobile=True, locale='en-US')
            m = await mc.new_page(); m.on('pageerror', lambda x, t=tag: errs.append(t + ': ' + str(x)))
            await m.add_init_script(mock())
            await m.goto(URL + '#board'); await m.wait_for_selector('#h-needs', timeout=8000); await m.wait_for_timeout(300)
            sl = m.locator('.shiplink')
            ok(f'{tag}: the board links to Shipped and says how many are archived', await sl.is_visible() and 'Shipped · 1 archived' in (await sl.inner_text()).replace('\n', ' '))
            await sl.tap(); await m.wait_for_selector('.archsec', timeout=5000); await m.wait_for_timeout(200)
            await m.locator('[data-act="togglearch"]').tap(); await m.wait_for_timeout(200)
            tb = await m.locator('[data-act="togglearch"]').bounding_box(); rb = await m.locator('#arch-list [data-act="restore"]').bounding_box()
            ok(f'{tag}: the group opens; 44 px targets; no sideways scroll', await m.locator('#arch-list').is_visible() and tb['height'] >= 44 and rb['height'] >= 44
               and await m.evaluate('document.documentElement.scrollWidth <= innerWidth'))
            await m.screenshot(path=OUT + f's19-{tag}-shipped.png', full_page=True)
            await m.locator('#arch-list a').tap(); await m.wait_for_timeout(300)
            bb = await m.locator('.banner.arch [data-act="restore"]').bounding_box()
            ok(f'{tag}: an archived project opens with the banner; Restore is 44 px', await m.locator('.banner.arch').is_visible() and bb['height'] >= 44
               and await m.evaluate('document.documentElement.scrollWidth <= innerWidth'))
            await m.screenshot(path=OUT + f's19-{tag}-archived.png')
            await m.goto(URL + '#p-pa'); await m.wait_for_timeout(400)
            await m.locator('.btabs [data-tab="log"], .btabs [data-tab="slices"]').count()
            await m.goto(URL + '#p-pdone'); await m.wait_for_selector('.pside [data-act="askarchive"]', state='attached', timeout=5000); await m.wait_for_timeout(200)
            ab = m.locator('.pside [data-act="askarchive"]')
            await ab.scroll_into_view_if_needed()
            ok(f'{tag}: Ship: Archive on the Launch tab, 44 px', await ab.is_visible() and (await ab.bounding_box())['height'] >= 44)
            await ab.tap(); await m.wait_for_timeout(200)
            await m.locator('.pside .gate [data-act="archive"]').tap(); await m.wait_for_timeout(300)
            ok(f'{tag}: archived from the phone', await m.locator('.banner.arch').is_visible() and (await P(m, 'pdone'))['archived'] is True)
            await mc.close()

        # Every project archived and no captures: the first-run board still leads to them
        oc = await b.new_context(viewport={'width': 390, 'height': 844}, has_touch=True, is_mobile=True, locale='en-US')
        o = await oc.new_page(); o.on('pageerror', lambda x: errs.append('only: ' + str(x)))
        await o.add_init_script(mock(SEED_ONLY_ARCHIVED))
        await o.goto(URL + '#board'); await o.wait_for_timeout(700)
        ok('only archived projects: the first-run board links to Shipped', await o.locator('.shiplink').is_visible() and '1 archived' in await o.inner_text('.shiplink'))
        await oc.close()

        for n, c in checks: print(('PASS ' if c else 'FAIL ') + n)
        print(f'{sum(c for _, c in checks)}/{len(checks)} passed')
        print('ERRORS', errs)
        await b.close()

asyncio.run(main())
