"""S3 browser test: mocked artifact db and a mocked Claude (sample)."""
import asyncio, json
from playwright.async_api import async_playwright
import os
from pathlib import Path
HERE = Path(__file__).resolve().parent
URL = (HERE.parent / 'src' / 'index.html').as_uri()
OUT = str(HERE / 'out') + os.sep            # screenshots land in tests/out/
os.makedirs(OUT, exist_ok=True)
LAUNCH = {'executable_path': os.environ['CHROME']} if os.environ.get('CHROME') else {}   # optional: your own Chrome

MOCK = r"""
(() => {
  const store = {}; const subs = [];
  const snap = col => { const docs = Object.keys(store).filter(k => k.startsWith(col + '/')).map(k => ({id:k.split('/')[1], exists:true, data:()=>store[k]})); return {docs, metadata:{fromCache:false}}; };
  const notify = col => subs.filter(s => s.col === col).forEach(s => s.cb(snap(col)));
  const db = { collection(col){ return {
    onSnapshot(cb){ subs.push({col, cb}); setTimeout(() => cb(snap(col)), 30); return () => {}; },
    doc(id){ const k = col + '/' + id; return { async set(d){ store[k] = JSON.parse(JSON.stringify(d)); setTimeout(()=>notify(col), 20); }, async delete(){ delete store[k]; setTimeout(()=>notify(col), 20); } }; }
  }; } };
  const now = Date.now();
  store['projects/pmafia'] = {name:'Mafia', phase:'ship', completed:{discover:true, define:true, design:true, build:true}, checks:{}, createdAt:now-86400000*40, updatedAt:now-86400000*3};
  store['captures/c1'] = {text:'Tracking 5-a-side goals and assists in the WhatsApp group after every Saturday game', createdAt:now-7200000, device:'phone', status:'new'};
  store['captures/c2'] = {text:'An app that predicts exam questions from past papers', createdAt:now-86400000, device:'phone', status:'new'};
  store['captures/c3'] = {text:'Splitting data bundle costs with roommates every month', createdAt:now-86400000*2, device:'laptop', status:'new'};
  window.__store = store; window.__calls = []; window.__mode = 'ok'; window.__delay = 0;
  const answer = text => /WhatsApp/.test(text) ? {s:[5,5,3,4,5,3], t:'Saturday stats tracker', r:'It happens every week and the players are easy to reach. Scope is the risk: keep v1 to goals and assists.', tags:['sports','data','weekly']}
    : /exam/.test(text) ? {s:[3,4,2,1,3,3], t:'Exam question predictor', r:'Predicting questions needs paid models or data. Free to run is 1, so it is killed.', tags:['study','ml']}
    : /bundle/.test(text) ? {s:[3,4,4,5,2,2], t:'Data bundle splitter', r:'Real but small pain; little to learn.', tags:['money','roommates']}
    : {s:[3,3,4,5,4,3], t:'New idea', r:'Plausible; needs more detail about who feels it.', tags:['idea']};
  const sample = async (input, opts) => ({text:'x', truncated:false});
  sample.json = async (input, opts) => {
    window.__calls.push({input, opts});
    if (window.__delay) await new Promise(r => setTimeout(r, window.__delay));
    if (window.__mode !== 'ok') throw {code: window.__mode, message: 'mock'};
    const items = input.split('\n').filter(l => l.startsWith('{"id"')).map(l => JSON.parse(l));
    const keys = ['pain','access','scope','cost','learning','motivation'];
    return items.map(it => { const a = answer(it.text); return {id: it.id, scores: Object.fromEntries(keys.map((k, i) => [k, a.s[i]])), reasoning: a.r, tags: a.tags, title: a.t}; });
  };
  sample.limits = async () => ({maxPromptBytes:262144});
  window.claude = { use: async n => n === 'db' ? db : n === 'sample' ? (window.__noSample ? null : sample) : null };
})();
"""

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(**LAUNCH)
        errs, checks = [], []
        def ok(name, cond): checks.append((name, bool(cond)))
        rows = lambda pg: pg.eval_on_selector_all('.ilist .irows li', 'els => els.map(e => e.innerText.replace(/\\s+/g, " "))')

        d = await b.new_page(viewport={'width':1440,'height':900}); d.on('pageerror', lambda e: errs.append('desk: ' + str(e)))
        await d.add_init_script(MOCK)
        await d.goto(URL + '#inbox'); await d.wait_for_selector('.ilist', timeout=8000); await d.wait_for_timeout(300)
        ok('untriaged shown with batch button', 'Triage 3 with Claude' in await d.inner_text('.top'))
        await d.click('[data-act="triageall"]'); await d.wait_for_timeout(400)
        calls = await d.evaluate('window.__calls')
        ok('one batch call on quick tier', len(calls) == 1 and calls[0]['opts'].get('modelTier') == 'quick' and sum(1 for l in calls[0]['input'].split('\n') if l.startswith('{"id"')) == 3)
        ok('prompt carries rubric rule and about text', 'killed if pain or cost is 1' in calls[0]['input'] and 'sports analytics' in calls[0]['input'])
        r = await rows(d)
        ok('verdicts and totals', any('WhatsApp' in x and 'Promising' in x and '25/30' in x for x in r) and any('exam' in x and 'Killed' in x for x in r) and any('bundle' in x and 'Park' in x for x in r))
        ok('killed row struck through', await d.eval_on_selector('.irows li.killed .tx', 'e => getComputedStyle(e).textDecorationLine') == 'line-through')
        await d.click('[data-act="ifilter"][data-f="killed"]'); await d.wait_for_timeout(100)
        ok('killed filter', len(await rows(d)) == 1)
        await d.click('[data-act="ifilter"][data-f="all"]'); await d.wait_for_timeout(100)
        await d.click('.irows a[href="#c-c1"]'); await d.wait_for_timeout(200)
        det = await d.inner_text('.idetail')
        ok('detail shows reasoning, tags, total, verdict', "It happens every week" in det and 'Tags: sports, data, weekly' in det and '25/30' in det.replace('\n', ''))
        ok('promising pressed', await d.get_attribute('.vseg [data-v="promising"]', 'aria-pressed') == 'true')
        await d.screenshot(path=OUT + 's3-desk.png')
        # change Pain to 1 -> killed, Claude's value shown
        await d.click('[data-act="score"][data-k="pain"][data-v="1"]'); await d.wait_for_timeout(150)
        det = await d.inner_text('.idetail')
        ok('score edit kills', await d.get_attribute('.vseg [data-v="killed"]', 'aria-pressed') == 'true' and 'Killed because Pain is 1' in det and 'Claude: 5' in det)
        ok('row marked edited', any('edited by you' in x for x in await rows(d)))
        # override to promising, then follow the scores
        await d.click('.vseg [data-v="promising"]'); await d.wait_for_timeout(150)
        ok('override', 'You set this; the scores say Killed' in await d.inner_text('.idetail'))
        await d.click('[data-act="verdict"][data-v=""]'); await d.wait_for_timeout(150)
        ok('follow scores', await d.get_attribute('.vseg [data-v="killed"]', 'aria-pressed') == 'true')
        # put Pain back to Claude's 5 -> edits cleared
        await d.click('[data-act="score"][data-k="pain"][data-v="5"]'); await d.wait_for_timeout(150)
        st = await d.evaluate("window.__store['captures/c1']")
        ok('back to Claude clears edits', 'you' not in st)
        # keyboard: score buttons keep focus
        await d.focus('[data-act="score"][data-k="scope"][data-v="4"]'); await d.keyboard.press('Enter'); await d.wait_for_timeout(100)
        ok('keyboard focus kept', await d.evaluate('document.activeElement.dataset.k + document.activeElement.dataset.v') == 'scope4')
        await d.focus('[data-act="score"][data-k="scope"][data-v="3"]'); await d.keyboard.press('Enter'); await d.wait_for_timeout(100)
        # new capture triages itself, pending state first
        await d.evaluate('window.__delay = 700')
        await d.keyboard.press('Escape'); await d.evaluate('document.activeElement.blur()')
        await d.keyboard.press('c'); await d.fill('#cap-text', 'Hostel washing machines are always taken; nobody knows when one frees up'); await d.keyboard.press('Control+Enter')
        await d.wait_for_timeout(250)
        ok('pending state', any('Claude is triaging' in x for x in await rows(d)))
        await d.wait_for_timeout(900)
        ok('new capture triaged', any('washing' in x and 'Promising' in x for x in await rows(d)))
        await d.evaluate('window.__delay = 0')
        # keep
        await d.click('.irows a[href="#c-c3"]'); await d.wait_for_timeout(150)
        await d.click('[data-act="keep"]'); await d.wait_for_timeout(150)
        ok('keep', (await d.evaluate("window.__store['captures/c3'].status")) == 'kept' and any('bundle' in x and 'kept' in x for x in await rows(d)))
        # errors
        await d.evaluate("window.__mode = 'rate_limited'")
        await d.click('.irows a[href="#c-c2"]'); await d.wait_for_timeout(150)
        await d.click('[data-act="retriage"]'); await d.wait_for_timeout(200)
        ok('rate limited shown', 'usage limit' in await d.inner_text('.errbox'))
        await d.screenshot(path=OUT + 's3-error.png')
        await d.evaluate("window.__mode = 'not_granted'")
        await d.click('.errbox [data-act="retriage"]'); await d.wait_for_timeout(200)
        txt = await d.inner_text('main')
        ok('not_granted turns triage off', 'triage is off' in txt and 'with Claude' not in await d.inner_text('.top'))
        # about you
        await d.click('[data-act="about"]'); await d.wait_for_timeout(100)
        await d.fill('#about-text', 'I want to learn realtime and payments.')
        await d.click('#aboutForm [type="submit"]'); await d.wait_for_timeout(150)
        ok('about saved', (await d.evaluate("window.__store['settings/about'].text")) == 'I want to learn realtime and payments.')
        # promote carries the triage
        await d.evaluate("window.__mode = 'ok'")
        await d.click('.irows a[href="#c-c1"]'); await d.wait_for_timeout(150)
        await d.click('[data-act="promote"]'); await d.wait_for_timeout(400)
        pj = await d.evaluate("Object.values(window.__store).find(x => x.source === 'c1')")
        ok('promoted with title, triage and ticked checklist', pj and pj['name'] == 'Saturday stats tracker' and pj['triage']['verdict'] == 'promising' and pj['checks']['discover'][2] is True)
        ok('discover shows triage', "from Claude's triage in the inbox" in await d.inner_text('main') and 'Idea score' in await d.inner_text('main'))
        await d.screenshot(path=OUT + 's3-promoted.png')

        # mobile, light mode
        m = await b.new_page(viewport={'width':390,'height':844}, has_touch=True, is_mobile=True, color_scheme='light'); m.on('pageerror', lambda e: errs.append('mob: ' + str(e)))
        await m.add_init_script(MOCK)
        await m.goto(URL + '#inbox'); await m.wait_for_selector('.ilist', timeout=8000); await m.wait_for_timeout(300)
        await m.click('[data-act="triageall"]'); await m.wait_for_timeout(400)
        ok('mobile list only', await m.query_selector('.idetail') is None)
        await m.screenshot(path=OUT + 's3-m-list.png')
        await m.tap('.irows a[href="#c-c2"]'); await m.wait_for_timeout(250)
        ok('mobile detail with back', await m.is_visible('a[aria-label="Back to inbox"]') and 'Killed because Free to run is 1' in await m.inner_text('.idetail'))
        ok('no sideways scroll', await m.evaluate('document.documentElement.scrollWidth') == 390)
        await m.screenshot(path=OUT + 's3-m-detail.png', full_page=True)
        await m.goto(URL + '#board'); await m.wait_for_timeout(300)
        ok('board inbox rows show verdicts', 'Killed' in await m.evaluate('document.querySelector("#h-inbox").closest("section").innerText'))
        await m.screenshot(path=OUT + 's3-m-board.png')

        # no Claude in this view
        n = await b.new_page(viewport={'width':1440,'height':900}); n.on('pageerror', lambda e: errs.append('noclaude: ' + str(e)))
        await n.add_init_script(MOCK); await n.add_init_script('window.__noSample = true;')
        await n.goto(URL + '#c-c1'); await n.wait_for_selector('.idetail', timeout=8000); await n.wait_for_timeout(300)
        ok('no Claude explained', 'open in Claude' in await n.inner_text('.idetail'))

        for nme, c in checks: print(('PASS ' if c else 'FAIL ') + nme)
        print('ERRORS', errs)
        await b.close()
asyncio.run(main())
