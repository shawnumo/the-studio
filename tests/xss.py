"""Security test: every stored text field holds a script payload and every link field a javascript: URL.
Visits every screen at desktop and phone width, opens its tabs and toggles, and checks that no payload runs,
no injected element appears and no javascript: link is drawn. Mocked db (the same mock as s19.py), no Claude."""
import asyncio, json, os, time
from pathlib import Path
from playwright.async_api import async_playwright
HERE = Path(__file__).resolve().parent
URL = (HERE.parent / 'src' / 'index.html').as_uri()
LAUNCH = {'executable_path': os.environ['CHROME']} if os.environ.get('CHROME') else {}   # optional: your own Chrome

NOW = int(time.time() * 1000); DAY = 86400000
P = '"\'><img src=x onerror="window.__xss=(window.__xss||[]).concat(location.hash)">'
JS = 'javascript:window.__xss=(window.__xss||[]).concat("js-link")'
ALL = ['discover', 'define', 'design', 'build', 'ship']
DOC = f"# {P}\n\n{P} [click]({JS}) **{P}** `{P}`\n\n- [ ] {P}\n- [x] {P}\n\n| {P} | b |\n|---|---|\n| {P} | x |\n\n> {P}\n\n```mermaid\ngraph TD; A[\"{P}\"]\n```\n"
sl = lambda i, t, st='todo': {'id': i, 'title': t, 'status': st, 'group': 'Must', 'raw': f'- [ ] {i} · {t}', 'story': P, 'crit': [P]}
ent = {'date': '2026-11-10', 'id': 'S1', 'title': P, 'built': P, 'tests': P + ' 9 passed', 'check': P, 'next': P, 'commit': 'abc1234 ' + P}
PROJ = {'name': P, 'phase': 'ship', 'completed': {k: True for k in ALL[:4]}, 'checks': {}, 'oneLiner': P, 'nextStep': P, 'liveUrl': JS, 'repo': 'C:\\Projects\\' + P, 'branch': P,
        'version': '1.0.0', 'feedback': [{'id': 'f1', 'who': P, 'text': P, 'at': NOW, 'bl': ''}], 'backlog': [{'id': 'b1', 'text': P, 'who': P, 'at': NOW, 'from': ''}],
        'changelog': {'v': '1.0.0', 'text': DOC, 'at': NOW, 'by': 'claude'}, 'cases': {'portfolio': {'text': DOC, 'at': NOW, 'by': 'claude', 'v': P}, 'summary': {'text': DOC, 'at': NOW, 'by': 'you', 'v': '1.0.0'}},
        'versions': [{'v': P, 'at': NOW - DAY, 'url': JS}], 'launch': [{'id': 'l0', 'g': 'launch', 't': P, 'done': False}],
        'outputs': {'discover': {'friction': DOC, 'validation': DOC, 'oneLiner': P, 'ideas': [{'title': P, 'pitch': P, 'picked': True, 'scores': {}}]}, 'ship': {'launch': DOC}},
        'triage': {'verdict': 'park', 'reasoning': P, 'tags': [P], 'scores': {}}, 'handoff': {'at': NOW, 'branch': P, 'files': [P]}, '__ago': DAY}
SEED = {
    'projects/px': PROJ,
    'projects/pv': {**PROJ, 'completed': {k: True for k in ALL}, 'versions': [{'v': '1.0.0', 'at': NOW - DAY, 'url': JS}]},
    'projects/pa': {**PROJ, 'archived': True, 'archivedAt': NOW - DAY},
    'captures/cx': {'text': P, 'createdAt': NOW - 3600000, 'device': 'phone', 'status': 'new', 'triage': {'tags': [P], 'verdict': 'park', 'reasoning': P, 'scores': {}}},
    'chats/px': {'messages': [{'id': 'm1', 'role': 'user', 'text': P, 'at': NOW - 5000}, {'id': 'm2', 'role': 'coach', 'text': DOC, 'at': NOW - 4000, 'meta': {'q': {'n': 1, 'of': 5, 'text': P}, 'choices': [P], 'reason': P}}],
                 'notes': {'who': P, 'struggle': P, 'current': P}, 'free': False, 'trimmed': 0, 'updatedAt': NOW},
    'chats/px~define': {'messages': [{'id': 'm1', 'role': 'user', 'text': P, 'at': NOW}], 'notes': {}, 'updatedAt': NOW},
    'docs/px~prd': {'pid': 'px', 'phase': 'define', 'key': 'prd', 'text': DOC, 'draft': {'text': DOC.replace('**', '__') + '\n\n' + P + ' added', 'at': NOW, 'basedOn': 1, 'cut': False, 'base': DOC, 'decisions': {}}, '__ago': DAY},
    'docs/px~stories': {'pid': 'px', 'phase': 'define', 'key': 'stories', 'text': DOC, '__ago': DAY},
    'docs/px~architecture': {'pid': 'px', 'phase': 'design', 'key': 'architecture', 'text': DOC, '__ago': DAY},
    'docs/px~adr-a1': {'pid': 'px', 'phase': 'design', 'key': 'adr-a1', 'kind': 'adr', 'n': 1, 'text': DOC, '__ago': DAY},
    'syncs/px': {'repo': 'C:\\Projects\\x', 'repoName': P, 'via': 'laptop', 'at': NOW - 3600000, 'branch': P, 'marks': {}, 'claude': {'found': True, 'cmds': P},
                 'slices': [sl('S1', P, 'done'), sl('S2', P, 'check'), sl('S3', P)], 'log': [ent], 'commits': [{'hash': 'abc1234', 'subject': 'feat(S1): ' + P, 'at': NOW - 7200000}]},
}
MOCK = (HERE / 's19.py').read_text(encoding='utf-8').split('MOCK = r"""')[1].split('"""')[0]
CHECK = '''(() => ({ran: window.__xss || [], imgs: document.querySelectorAll('img[src="x"]').length, onerr: document.querySelectorAll('[onerror]').length,
  js: [...document.querySelectorAll('a[href]')].filter(a => /^\\s*javascript:/i.test(a.getAttribute('href'))).length}))()'''
ROUTES = ['#board', '#inbox', '#c-cx', '#shipped', '#p-px-discover', '#p-px-define', '#p-px-design', '#p-px-build', '#p-px-ship', '#p-px-handoff', '#p-pv-ship', '#p-pa']
TOGGLES = ['.btabs [role="tab"]', '.stabs [role="tab"]', '.doctabs [role="tab"]', '.csseg button', '[data-act="togglearch"]', '[data-act="adr"]', '[data-act="dgview"]', '[data-act="sdet"]', '.disc']


async def main():
    async with async_playwright() as pw:
        b = await pw.chromium.launch(**LAUNCH)
        errs, checks = [], []
        def ok(name, cond):
            checks.append((name, bool(cond)))
            if not cond: print('FAIL (so far) ' + name, flush=True)
        for (w, h), tag in [((1440, 900), 'desktop'), ((390, 844), 'phone')]:
            ctx = await b.new_context(viewport={'width': w, 'height': h}, is_mobile=tag == 'phone', has_touch=tag == 'phone')
            pg = await ctx.new_page(); pg.on('pageerror', lambda e, t=tag: errs.append(t + ': ' + str(e)))
            await pg.add_init_script(MOCK.replace('%SEED%', json.dumps(SEED)))
            await pg.goto(URL + '#board'); await pg.wait_for_timeout(700)
            ok(f'{tag}: the payload is on screen as plain text', 'onerror=' in await pg.inner_text('body'))
            for r in ROUTES:
                await pg.goto(URL + r); await pg.wait_for_timeout(600)
                bad = []
                async def look(where):
                    x = await pg.evaluate(CHECK)
                    if x['ran'] or x['imgs'] or x['onerr'] or x['js']: bad.append((where, x))
                await look('opened')
                for sel in TOGGLES:   # every tab and toggle on the screen
                    for i in range(min(await pg.locator(sel).count(), 6)):
                        el = pg.locator(sel).nth(i)
                        if await el.is_visible():
                            try: await el.click(timeout=1500)
                            except Exception: pass
                            await pg.wait_for_timeout(120); await look(f'{sel}[{i}]')
                ok(f'{tag} {r}: no script runs, nothing injected, no javascript: link', not bad)
                if bad: print('  ', bad[:2])
            await pg.keyboard.press('?'); await pg.wait_for_timeout(200)
            x = await pg.evaluate(CHECK)
            ok(f'{tag}: the shortcuts sheet too', not (x['ran'] or x['imgs'] or x['onerr'] or x['js']))
            await ctx.close()
        for n, c in checks: print(('PASS ' if c else 'FAIL ') + n)
        print(f'{sum(c for _, c in checks)}/{len(checks)} passed')
        print('ERRORS', errs)
        await b.close()

asyncio.run(main())
