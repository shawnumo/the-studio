"""S4 browser test: Discover coach with a mocked db (doc subscriptions) and a mocked, streaming Claude."""
import asyncio, json, sys
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
  const store = window.__seed ? JSON.parse(window.__seed) : null;
  const S0 = store || {}; const subs = []; const dsubs = [];
  const snapC = col => { const docs = Object.keys(S0).filter(k => k.split('/')[0] === col && k.split('/').length === 2).map(k => ({id:k.split('/')[1], exists:true, data:()=>S0[k]})); return {docs, metadata:{fromCache:false}}; };
  const snapD = k => ({id:k.split('/')[1], exists:k in S0, data:()=>S0[k], metadata:{fromCache:false, hasPendingWrites:false}});
  const notify = k => { const col = k.split('/')[0]; subs.filter(s => s.col === col).forEach(s => s.cb(snapC(col))); dsubs.filter(s => s.k === k).forEach(s => s.cb(snapD(k))); };
  const db = { collection(col){ return {
    onSnapshot(cb){ subs.push({col, cb}); setTimeout(() => cb(snapC(col)), 30); return () => {}; },
    doc(id){ const k = col + '/' + id; return {
      async set(d){ window.__writes.push(k); S0[k] = JSON.parse(JSON.stringify(d)); localStorage.setItem('__mockdb', JSON.stringify(S0)); setTimeout(()=>notify(k), 20); },
      async get(){ return snapD(k); },
      onSnapshot(cb, err){ dsubs.push({k, cb}); setTimeout(() => cb(snapD(k)), 40); return () => {}; },
      async delete(){ delete S0[k]; localStorage.setItem('__mockdb', JSON.stringify(S0)); setTimeout(()=>notify(k), 20); } }; }
  }; } };
  const saved = localStorage.getItem('__mockdb');
  if (saved) Object.assign(S0, JSON.parse(saved));
  else {
    const now = Date.now();
    S0['projects/p5'] = {name:'Saturday stats tracker', phase:'discover', completed:{}, checks:{discover:[false,false,true]}, oneLiner:'', source:'c1', createdAt:now-3600000, updatedAt:now-3600000,
      triage:{scores:{pain:5,access:5,scope:3,cost:4,learning:5,motivation:3}, verdict:'promising', reasoning:'It happens every week and the players are easy to reach.', tags:['sports'], at:now-3600000}};
    S0['projects/p2'] = {name:'Bundle splitter', phase:'discover', completed:{}, checks:{}, oneLiner:'', createdAt:now-7200000, updatedAt:now-7200000};
    S0['captures/c1'] = {text:'Tracking 5-a-side goals and assists in the WhatsApp group after every Saturday game', createdAt:now-7200000, device:'phone', status:'promoted', projectId:'p5'};
  }
  window.__store = S0; window.__calls = []; window.__writes = []; window.__seen = []; window.__mode = 'ok'; window.__replies = [];
  const sample = (input, opts) => new Promise((resolve, reject) => {
    window.__calls.push({input: JSON.parse(JSON.stringify(input)), opts: {modelTier: opts.modelTier, cache: opts.cache, signal: !!opts.signal}});
    if (window.__mode !== 'ok'){ setTimeout(() => reject({code: window.__mode, message: 'mock'}), 30); return; }
    const full = window.__replies.length ? window.__replies.shift() : 'Okay.\n<studio>{"mode":"chat"}</studio>';
    let i = 0; const step = window.__step || 14, tick = window.__tick || 6;
    opts.onText && opts.onText({text:'Thinking...', delta:''});
    const t = setInterval(() => {
      i = Math.min(full.length, i + step);
      opts.onText && opts.onText({text: full.slice(0, i), delta: ''});
      const live = document.querySelector('#coach-live'); if (live) window.__seen.push(live.innerText);
      if (i >= full.length){ clearInterval(t); resolve({text: full, truncated: false}); }
    }, tick);
    if (opts.signal) opts.signal.addEventListener('abort', () => { clearInterval(t); reject({code:'aborted', message:'stopped', text: full.slice(0, i)}); });
  });
  sample.json = async () => { throw {code:'upstream_error'}; };
  window.claude = { use: async n => n === 'db' ? db : n === 'sample' ? (window.__noSample ? null : sample) : null };
})();
"""
B = lambda d: '\n<studio>' + json.dumps(d) + '</studio>'
NOTES = {"who": "A fixed group of 10 to 12 Saturday 5-a-side players", "struggle": "Goals and assists posted in WhatsApp get disputed", "current": "", "app": "", "evidence": "", "risks": ""}
R1 = "Saturday stats are a real weekly pain, and your players are easy to reach. A few quick questions so we build the right thing." + B({"mode": "interview", "reason": "“something better” could mean five different apps", "question": {"n": 1, "of": 5, "text": "Who records the stats during a match?"}, "choices": ["One person on the sideline", "Each player, after the match", "The two captains", "Nobody; we argue later"], "notes": NOTES, "done": False, "oneliner": "", "scores": None})
R2 = "Captains it is: two people you trust." + B({"mode": "interview", "reason": "need to know what the record must settle", "question": {"n": 2, "of": 5, "text": "What exactly gets disputed most?"}, "choices": [], "notes": dict(NOTES, current="The captains post a tally in WhatsApp"), "done": False, "oneliner": "", "scores": None})
R3 = "So who scored is the core record." + B({"mode": "interview", "reason": "", "question": {"n": 3, "of": 5, "text": "Would players check a season table?"}, "choices": ["Yes, every week", "Only at season end", "Not sure"], "notes": NOTES, "done": False, "oneliner": "", "scores": None})
R4 = "Here's what I learned. Your group of 12 plays every Saturday, the captains keep the tally, and who scored is what gets argued about. It looks worth two weeks: the pain is weekly and you can reach every user. Scope is the risk, so keep v1 to goals and assists. Want to keep refining?" + "\n<studio>\n```json\n" + json.dumps({"mode": "chat", "reason": "", "question": None, "choices": [], "notes": dict(NOTES, app="Shared match log the captains confirm"), "done": True, "oneliner": "For Saturday 5-a-side players, who argue over who scored, Matchbook lets captains log goals and assists live, unlike the WhatsApp tally.", "scores": {"pain": 5, "access": 5, "scope": 3, "cost": 4, "learning": 5, "motivation": 4}}) + "\n```\n</studio>"
RNOBLOCK = "Sure. A season table needs every match logged, so start with one match screen."
RLONG = ("This is a long answer that keeps going so you can stop it halfway through. " * 12) + B({"mode": "chat", "notes": NOTES})

async def idle(pg):
    await pg.wait_for_function('!document.querySelector("#coach-live")', timeout=8000); await pg.wait_for_timeout(50)

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(**LAUNCH)
        errs, checks = [], []
        def ok(name, cond):
            checks.append((name, bool(cond)))
            if not cond: print('FAIL', name)
        ctx = await b.new_context(viewport={'width': 1440, 'height': 900}, color_scheme='dark')
        d = await ctx.new_page(); d.on('pageerror', lambda e: errs.append('desk: ' + str(e)))
        await d.add_init_script(MOCK)
        await d.goto(URL + '#p-p5'); await d.wait_for_selector('.coach .msgs[data-ready]', timeout=8000); await d.wait_for_timeout(200)
        main_t = await d.inner_text('main')
        ok('intro and capture quote', "I'm your Discover coach" in main_t and 'Your capture' in main_t and 'WhatsApp group' in main_t)
        ok('aside: idea score from inbox', 'Idea score' in main_t and '25' in await d.inner_text('#is-h') and "from Claude's triage in the inbox" in main_t)
        ok('aside: one-liner hint and empty notes', 'Not written yet' in main_t and 'Nothing yet' in main_t)
        ok('no interview banner yet', await d.query_selector('.ibar') is None)
        ok('composer label', (await d.inner_text('.compose label')) == 'Message the coach')

        # 1. Interview me
        await d.evaluate(f'window.__replies.push({json.dumps(R1)})')
        await d.click('.msgs [data-act="interview"]')
        await d.wait_for_selector('#coach-live', timeout=3000)
        ok('stop button while streaming', await d.query_selector('[data-act="stopcoach"]') is not None)
        await d.wait_for_selector('.ibar', timeout=5000); await d.wait_for_timeout(150)
        seen = await d.evaluate('window.__seen')
        ok('streamed text visible, block never shown', any('weekly pain' in s for s in seen) and not any('<studio' in s or '"mode"' in s or 'studio>' in s for s in seen))
        calls = await d.evaluate('window.__calls')
        c0 = calls[0]
        ok('call: messages array, default tier, no cache, signal', isinstance(c0['input'], list) and c0['opts'] == {'modelTier': 'default', 'cache': False, 'signal': True})
        first = c0['input'][0]['content']
        ok('call: context carries capture, triage, rubric, format', 'You are the Discover coach' in first and 'WhatsApp group' in first and '25/30' in first and 'killed if pain or cost is 1' in first and '<studio>' in first and first.rstrip().endswith('Interview me about this idea.'))
        ok('call: about text included', 'sports analytics' in first)
        bar = await d.inner_text('.ibar')
        ok('banner: interviewing, question count, reason, way back', 'Claude is interviewing you' in bar and 'Question 1 of about 5' in ' '.join(bar.split()) and 'five different apps' in bar and 'Back to free chat' in bar)
        ok('question as legend', (await d.inner_text('.qset legend')) == '1. Who records the stats during a match?')
        ok('four choices with keys', len(await d.query_selector_all('.choices button')) == 4 and (await d.inner_text('.choices button:nth-child(3) kbd')) == '3')
        ok('composer becomes Other field', (await d.inner_text('.compose label')) == 'Or answer in your own words')
        ok('notes in aside', 'A fixed group of 10 to 12' in await d.inner_text('.pside'))
        ok('reaction text shown, no block', 'weekly pain' in await d.inner_text('.msgs') and 'studio' not in await d.inner_text('.msgs'))
        st = await d.evaluate('window.__store["chats/p5"]')
        ok('chat saved to db', st and len(st['messages']) == 2 and st['messages'][1]['meta']['q']['text'].startswith('Who records') and st['notes']['who'])

        # 2. Pick a choice with the keyboard
        await d.evaluate(f'window.__replies.push({json.dumps(R2)})')
        await d.focus('body'); await d.evaluate('document.activeElement && document.activeElement.blur()')
        await d.keyboard.press('3')
        await d.wait_for_function('document.querySelector(".qset legend") && document.querySelector(".qset legend").innerText.startsWith("2.")', timeout=5000)
        qa = await d.inner_text('dl.qa')
        ok('answered question collapses into list', 'Who records the stats' in qa and 'The two captains' in qa and 'Change' in qa)
        ok('open question: no choices, label Your answer', await d.query_selector('.choices') is None and (await d.inner_text('.compose label')) == 'Your answer')
        ok('a choice leaves focus off the composer', await d.evaluate('document.activeElement.id') != 'coach-input')
        ok('first reaction kept above the list', 'weekly pain' in await d.inner_text('.msgs'))

        # 3. Type an answer, Enter to send
        await d.evaluate(f'window.__replies.push({json.dumps(R3)})')
        await d.click('#coach-input'); await d.keyboard.type('Who scored, mostly. Assists less.')
        await d.keyboard.press('Enter')
        await d.wait_for_function('document.querySelector(".qset legend") && document.querySelector(".qset legend").innerText.startsWith("3.")', timeout=5000)
        ok('two answered rows', len(await d.query_selector_all('dl.qa div')) == 2)
        ok('composer cleared and focused after send', await d.evaluate('document.activeElement.id') == 'coach-input' and await d.input_value('#coach-input') == '')
        msgs = (await d.evaluate('window.__calls'))[2]['input']
        ok('history alternates, starts with user', [m['role'] for m in msgs] == ['user', 'assistant', 'user', 'assistant', 'user'] and msgs[-1]['content'] == 'Who scored, mostly. Assists less.')
        ok('history carries short blocks', '<studio>' in msgs[1]['content'] and '"question"' in msgs[1]['content'] and '"notes"' not in msgs[1]['content'])
        ok('reaction shown with the next question', 'core record' in await d.inner_text('.msgs'))

        # 4. Change an answer
        await d.click('dl.qa div:first-child [data-act="change"]')
        ok('change prefills composer', (await d.input_value('#coach-input')).startswith('Change my answer to "Who records the stats during a match?": ') and await d.evaluate('document.activeElement.id') == 'coach-input')
        await d.keyboard.type('the referee')
        await d.evaluate('window.__replies.push(%s)' % json.dumps("Noted: the referee keeps the record." + B({"mode": "interview", "reason": "", "question": {"n": 3, "of": 5, "text": "Would players check a season table?"}, "choices": ["Yes, every week", "Only at season end", "Not sure"], "notes": NOTES, "done": False, "oneliner": "", "scores": None})))
        await d.keyboard.press('Enter'); await idle(d)
        ok('correction not filed as an answer', 'the referee' not in await d.inner_text('dl.qa') and 'the referee' in await d.inner_text('.msgs') and (await d.inner_text('.qset legend')).startswith('3.'))

        # 5. Esc back to free chat
        await d.evaluate('document.activeElement.blur()')
        await d.keyboard.press('Escape'); await d.wait_for_timeout(150)
        ok('Esc leaves the interview', await d.query_selector('.ibar') is None and await d.query_selector('.choices') is None)
        ok('pending question kept as text', 'Would players check a season table?' in await d.inner_text('.msgs'))
        ok('pending question marked skipped', (await d.evaluate('S.chats.p5.messages.slice(-1)[0].meta.skipped')) is True)
        ok('Interview me offered again', await d.query_selector('.compose [data-act="interview"]') is not None and (await d.inner_text('.compose label')) == 'Message the coach')
        await d.wait_for_timeout(100)
        ok('free flag saved', (await d.evaluate('window.__store["chats/p5"]'))['free'] is True)

        # 6. Reply without a block is shown as chat; next prompt says free chat
        await d.evaluate(f'window.__replies.push({json.dumps(RNOBLOCK)})')
        await d.fill('#coach-input', 'Should v1 have a season table?'); await d.keyboard.press('Enter')
        await d.wait_for_function('document.querySelectorAll(".msgs .msg.cl").length && document.querySelector(".msgs").innerText.includes("one match screen")', timeout=5000)
        await idle(d)
        last_call = (await d.evaluate('window.__calls'))[-1]['input'][0]['content']
        ok('free message not filed as an answer', 'Should v1 have a season table?' not in await d.inner_text('dl.qa') and len(await d.query_selector_all('dl.qa div')) == 2)
        ok('prompt says free chat', 'He has switched to free chat' in last_call)

        # 7. Draft on request: one-liner and scores
        await d.evaluate(f'window.__replies.push({json.dumps(R4)})')
        await d.fill('#coach-input', 'Draft the one-liner and score it.'); await d.keyboard.press('Enter')
        await d.wait_for_selector('.draft', timeout=5000)
        dr = await d.inner_text('.draft')
        ok('draft card: one-liner and score', 'Matchbook lets captains' in dr and '26/30' in dr and 'Promising' in dr)
        ok('summary shown', 'Here\'s what I learned' in await d.inner_text('.msgs'))
        await d.click('[data-act="useone"]'); await d.wait_for_timeout(700)
        pr = await d.evaluate('window.__store["projects/p5"]')
        ok('one-liner saved and checklist ticked', pr['oneLiner'].startswith('For Saturday') and pr['checks']['discover'][0] is True)
        ok('used state shown', 'Saved to the project' in await d.inner_text('.draft'))
        await d.click('[data-act="usescores"]'); await d.wait_for_timeout(700)
        pr = await d.evaluate('window.__store["projects/p5"]')
        ok('scores saved from the interview', pr['triage']['from'] == 'coach' and pr['triage']['scores']['motivation'] == 4 and pr['triage']['verdict'] == 'promising' and pr['checks']['discover'][2] is True)
        side = await d.inner_text('.pside')
        ok('aside follows', 'from the interview' in side and 'Matchbook' in await d.input_value('#p-one') and 'Shared match log' in side)
        await d.screenshot(path=OUT + 's4-desk-done.png', full_page=False)

        # 8. Error then retry
        await d.evaluate('window.__mode = "rate_limited"')
        await d.fill('#coach-input', 'What about assists?'); await d.keyboard.press('Enter')
        await d.wait_for_selector('.msgs .errbox', timeout=3000)
        ok('error explained', 'usage limit' in await d.inner_text('.msgs .errbox'))
        await d.evaluate('window.__mode = "ok"; window.__replies.push("Assists can wait for v2." + %s)' % json.dumps(B({"mode": "chat", "notes": NOTES})))
        await d.click('[data-act="retrycoach"]')
        await d.wait_for_function('document.querySelector(".msgs").innerText.includes("Assists can wait")', timeout=5000)
        await idle(d)
        ok('retry answers the same message', await d.query_selector('.msgs .errbox') is None and (await d.evaluate('window.__calls'))[-1]['input'][-1]['content'].endswith('What about assists?'))

        # 9. Stop mid-stream
        await d.evaluate('window.__tick = 40; window.__step = 8; window.__replies.push(%s)' % json.dumps(RLONG))
        await d.fill('#coach-input', 'Tell me everything.'); await d.keyboard.press('Enter')
        await d.wait_for_timeout(500)
        await d.click('[data-act="stopcoach"]'); await d.wait_for_timeout(200)
        t = await d.inner_text('.msgs')
        ok('stopped reply kept and labelled', 'Stopped' in t and 'long answer' in t and await d.query_selector('#coach-live') is None)
        await d.evaluate('window.__tick = 6; window.__step = 14')
        await d.screenshot(path=OUT + 's4-desk-stopped.png')

        # 10. Reload: chat comes back from the db
        await d.wait_for_timeout(1500)   # let Chrome flush the mock db's localStorage before the reload
        snap = await d.evaluate('localStorage.getItem("__mockdb")')
        ok('mock db saved before the reload', bool(snap))
        # Chrome sometimes drops a page's last localStorage writes when it reloads, so a fresh page gets the mock db's copy instead.
        await d.close()
        d = await ctx.new_page(); d.on('pageerror', lambda e: errs.append('desk: ' + str(e)))
        await d.add_init_script('if (!window.name){ window.name = "seeded"; localStorage.setItem("__mockdb", %s); }' % json.dumps(snap))
        await d.add_init_script(MOCK)
        await d.goto(URL + '#p-p5'); await d.wait_for_selector('.coach .msgs[data-ready]', timeout=8000); await d.wait_for_timeout(300)
        t = await d.inner_text('.msgs')
        ok('chat restored after reload', 'Matchbook' in t and 'The two captains' in t and 'Stopped' in t)
        ok('latest message in view above the composer', await d.evaluate('(() => { const b = document.querySelector(".msgs").lastElementChild.getBoundingClientRect(); return b.bottom <= document.querySelector(".compose").getBoundingClientRect().top + 1 && b.bottom > 100; })()'))
        ok('composer sticks to the bottom', await d.evaluate('Math.round(document.querySelector(".compose").getBoundingClientRect().bottom) === innerHeight'))

        # 11. A long chat asks before trimming
        n0 = await d.evaluate('S.chats.p5.messages.length')
        add = lambda k: d.evaluate('''k => { const c = S.chats.p5; for (let i = 0; i < k; i++) c.messages.push({id:"x"+c.messages.length, role:c.messages.length % 2 ? "coach" : "user", text:"word ".repeat(300), at:Date.now()}); saveChat("p5"); render(); return chatBytes(c); }''', k)
        size = await add(118); await d.wait_for_timeout(200)
        ok('nothing trimmed without asking', await d.evaluate('S.chats.p5.messages.length') == n0 + 118 and not (await d.evaluate('window.__store["chats/p5"]')).get('trimmed'))
        ask = await d.inner_text('.trimask')
        ok('asks once the chat is getting full', 180000 < size < 220000 and 'getting full' in ask and 'Not now' in ask and await d.is_enabled('#coach-input'))
        await d.click('[data-act="trimlater"]')
        ok('Not now hides the question', await d.query_selector('.trimask') is None)
        size = await add(30); await d.wait_for_timeout(200)
        ask = await d.inner_text('.trimask')
        ok('full chat: must trim, sending blocked', size >= 220000 and 'This chat is full' in ask and 'Not now' not in ask and await d.is_disabled('#coach-input') and await d.is_disabled('.compose [type="submit"]') and await d.query_selector('.compose [data-act="interview"]') is None)
        await d.screenshot(path=OUT + 's4-full.png')
        cut = await d.evaluate('trimCount(S.chats.p5)')
        await d.click('[data-act="trimchat"]'); await d.wait_for_timeout(300)
        stc = await d.evaluate('window.__store["chats/p5"]')
        ok('trim after OK: oldest gone, under the keep size', stc['trimmed'] == cut and len(json.dumps(stc).encode()) <= 145000 and stc['messages'][-1]['id'] == 'x%d' % (n0 + 147) and await d.query_selector('.trimask') is None)
        ok('trim note shown, chat usable again', 'trimmed to keep the chat small' in await d.inner_text('.msgs') and await d.is_enabled('#coach-input'))
        await d.screenshot(path=OUT + 's4-trim.png')

        # 12. Project without capture or triage
        await d.goto(URL + '#p-p2'); await d.wait_for_selector('.coach .msgs[data-ready]', timeout=8000)
        t = await d.inner_text('main')
        ok('plain project: intro without capture, not scored', 'Your capture' not in t and 'Not scored yet' in t)

        # 13. Claude unavailable
        nos = await ctx.new_page(); nos.on('pageerror', lambda e: errs.append('nosample: ' + str(e)))
        await nos.add_init_script('window.__noSample = true;'); await nos.add_init_script(MOCK)
        await nos.goto(URL + '#p-p2'); await nos.wait_for_selector('.coach .msgs[data-ready]', timeout=8000); await nos.wait_for_timeout(300)
        ok('no Claude: coach off, composer disabled', 'The coach is off here' in await nos.inner_text('.msgs') and await nos.is_disabled('#coach-input'))
        await nos.close()

        # 14. Mobile, light and dark
        for scheme in ['dark', 'light']:
            for w, h in [(390, 844), (360, 800)]:
                mc = await b.new_context(viewport={'width': w, 'height': h}, color_scheme=scheme, has_touch=True, is_mobile=True)
                m = await mc.new_page(); m.on('pageerror', lambda e: errs.append('mob: ' + str(e)))
                await m.add_init_script(MOCK)
                await m.goto(URL + '#p-p5'); await m.wait_for_selector('.coach .msgs[data-ready]', timeout=8000); await m.wait_for_timeout(200)
                await m.evaluate('localStorage.clear()')
                await m.evaluate(f'window.__replies.push({json.dumps(R1)})')
                await m.click('.msgs [data-act="interview"]')
                await m.wait_for_selector('.choices', timeout=5000); await m.wait_for_timeout(200)
                tag = f'{scheme}-{w}'
                ok(f'{tag}: tabs Coach and Outputs', (await m.inner_text('.btabs')).split() == ['Coach', 'Outputs'])
                ok(f'{tag}: mobile banner', 'Interview' in await m.inner_text('.ibar') and 'Free chat' in await m.inner_text('.ibar') and await m.is_hidden('.ibar .why'))
                ok(f'{tag}: no sideways scroll', await m.evaluate('document.documentElement.scrollWidth <= innerWidth'))
                ok(f'{tag}: choices 56px tall', await m.evaluate('Math.round(document.querySelector(".choices button").getBoundingClientRect().height) >= 56'))
                ok(f'{tag}: composer above bottom bar', await m.evaluate('Math.round(document.querySelector(".compose").getBoundingClientRect().bottom) <= Math.round(document.querySelector(".mnav").getBoundingClientRect().top) + 1'))
                ok(f'{tag}: outputs hidden on Coach tab', await m.is_hidden('.pside'))
                await m.screenshot(path=OUT + f's4-m-{tag}.png')
                if w == 390:
                    await m.click('.choices button:nth-child(1)'); await m.wait_for_timeout(600)
                    ok(f'{tag}: tap a choice sends it', 'One person on the sideline' in await m.inner_text('.msgs'))
                    await m.click('[data-act="dtab"][data-tab="outputs"]'); await m.wait_for_timeout(150)
                    ok(f'{tag}: Outputs tab shows score and notes', await m.is_hidden('.coach') and 'Idea score' in await m.inner_text('.pside') and 'What the coach knows' in await m.inner_text('.pside'))
                    await m.screenshot(path=OUT + f's4-m-{tag}-outputs.png', full_page=True)
                    await m.click('[data-act="dtab"][data-tab="coach"]')
                await mc.close()

        # desktop light screenshot mid-interview
        lc = await b.new_context(viewport={'width': 1440, 'height': 900}, color_scheme='light')
        l = await lc.new_page(); l.on('pageerror', lambda e: errs.append('light: ' + str(e)))
        await l.add_init_script(MOCK)
        await l.goto(URL + '#p-p5'); await l.wait_for_selector('.coach .msgs[data-ready]', timeout=8000)
        await l.evaluate('localStorage.clear()')
        await l.evaluate(f'window.__replies.push({json.dumps(R1)}, {json.dumps(R2)})')
        await l.click('.msgs [data-act="interview"]'); await l.wait_for_selector('.choices', timeout=5000)
        await l.click('.choices button:nth-child(3)'); await l.wait_for_function('document.querySelector(".qset legend") && document.querySelector(".qset legend").innerText.startsWith("2.")', timeout=5000)
        await l.wait_for_timeout(200)
        await l.screenshot(path=OUT + 's4-desk-light.png')
        await l.set_viewport_size({'width': 1024, 'height': 768}); await l.wait_for_timeout(200)
        ok('1024: no sideways scroll', await l.evaluate('document.documentElement.scrollWidth <= innerWidth'))
        await l.screenshot(path=OUT + 's4-desk-1024.png')
        await lc.close()

        # desktop dark mid-interview for review
        dc = await b.new_context(viewport={'width': 1440, 'height': 900}, color_scheme='dark')
        k = await dc.new_page(); k.on('pageerror', lambda e: errs.append('dark: ' + str(e)))
        await k.add_init_script(MOCK)
        await k.goto(URL + '#p-p5'); await k.wait_for_selector('.coach .msgs[data-ready]', timeout=8000)
        await k.evaluate('localStorage.clear()')
        await k.evaluate(f'window.__replies.push({json.dumps(R1)}, {json.dumps(R2)}, {json.dumps(R3)})')
        await k.click('.msgs [data-act="interview"]'); await k.wait_for_selector('.choices', timeout=5000)
        await k.click('.choices button:nth-child(3)'); await k.wait_for_function('document.querySelector(".qset legend") && document.querySelector(".qset legend").innerText.startsWith("2.")', timeout=5000); await idle(k)
        await k.fill('#coach-input', 'Who scored, mostly.'); await k.keyboard.press('Enter')
        await k.wait_for_function('document.querySelector(".qset legend") && document.querySelector(".qset legend").innerText.startsWith("3.")', timeout=5000)
        await k.wait_for_timeout(200)
        await k.screenshot(path=OUT + 's4-desk-dark.png')
        await dc.close()

        await b.close()
        passed = sum(1 for _, c in checks if c)
        print(f'{passed}/{len(checks)} passed')
        for n, c in checks:
            if not c: print('  FAILED:', n)
        print('page errors:', errs or 'none')

asyncio.run(main())
