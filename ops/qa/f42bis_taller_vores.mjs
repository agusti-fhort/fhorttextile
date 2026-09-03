// F4.2-BIS · SMOKE AMB ULLS. CDP cru contra el chrome-headless-shell de playwright
// (Node 22 ja porta WebSocket). No mesura una maqueta: obre el Taller REAL del 1383
// servit pel worktree i mira què hi ha pintat.
import { spawn } from 'node:child_process'
import { writeFileSync, readFileSync } from 'node:fs'

const SP = '/tmp/claude-0/-var-www/73d9d192-aca1-4077-9ee4-088e632fd07a/scratchpad'
const OUT = process.argv[2] || SP
const TOK = readFileSync(`${SP}/tok.txt`, 'utf8').trim()
const CHROME = '/root/.cache/ms-playwright/chromium_headless_shell-1234/chrome-headless-shell-linux64/chrome-headless-shell'
const BASE = 'http://127.0.0.1:5199'

const chrome = spawn(CHROME, [
  '--remote-debugging-port=9333', '--no-sandbox', '--disable-gpu',
  '--window-size=1600,1000', '--hide-scrollbars', 'about:blank',
], { stdio: ['ignore', 'ignore', 'pipe'] })

const sleep = ms => new Promise(r => setTimeout(r, ms))

async function wsUrl() {
  for (let i = 0; i < 40; i++) {
    try {
      const r = await fetch('http://127.0.0.1:9333/json/version')
      return (await r.json()).webSocketDebuggerUrl
    } catch { await sleep(250) }
  }
  throw new Error('no CDP')
}

let id = 0
function rpc(ws, method, params = {}, sessionId) {
  return new Promise((res, rej) => {
    const mid = ++id
    const on = ev => {
      const m = JSON.parse(ev.data)
      if (m.id !== mid) return
      ws.removeEventListener('message', on)
      m.error ? rej(new Error(method + ': ' + JSON.stringify(m.error))) : res(m.result)
    }
    ws.addEventListener('message', on)
    ws.send(JSON.stringify({ id: mid, method, params, sessionId }))
  })
}

const log = []
const say = s => { console.log(s); log.push(s) }

try {
  const ws = new WebSocket(await wsUrl())
  await new Promise(r => ws.addEventListener('open', r))
  const { targetId } = await rpc(ws, 'Target.createTarget', { url: 'about:blank' })
  const { sessionId } = await rpc(ws, 'Target.attachToTarget', { targetId, flatten: true })
  const S = (m, p) => rpc(ws, m, p, sessionId)
  await S('Page.enable'); await S('Runtime.enable')
  await S('Emulation.setDeviceMetricsOverride',
    { width: 1600, height: 1000, deviceScaleFactor: 1, mobile: false })

  const evalJs = async (expr) => {
    const r = await S('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true })
    if (r.exceptionDetails) throw new Error(r.exceptionDetails.text + ' ' + (r.exceptionDetails.exception?.description || ''))
    return r.result.value
  }

  // El token, abans de qualsevol navegació de l'app: el client el llegeix de localStorage.
  await S('Page.navigate', { url: BASE + '/' }); await sleep(1500)
  await evalJs(`localStorage.setItem('access_token', ${JSON.stringify(TOK)}); localStorage.setItem('fhort.lang','ca'); 'ok'`)

  await S('Page.navigate', { url: `${BASE}/models/1383/patro/taller` })
  await sleep(7000)

  const titol = await evalJs(`document.querySelector('[data-ftt-screen="taller-patro"]') ? 'TALLER' : document.body.innerText.slice(0,120)`)
  say(`pantalla: ${titol}`)

  // 1 · Triar la peça CUELLO a la llista de peces.
  // La peça es tria amb un <button> (PieceList.jsx:24). Apuntar a «qualsevol node amb el
  // text» clicava un contenidor sense handler i el fum donava per triada una peça que no
  // ho estava — la sonda mentint, no la pantalla.
  const triat = await evalJs(`(() => {
    const b = [...document.querySelectorAll('button')]
      .filter(e => /837\\.CUELLO/.test(e.textContent));
    if (!b.length) return 'NO TROBADA';
    b[0].click(); return 'clicada';
  })()`)
  say(`tria de peça 837.CUELLO: ${triat}`)
  await sleep(3500)

  // 2 · El panell de rols de vora ha d'haver aparegut amb les seves files.
  const panell = await evalJs(`(() => {
    const t = document.body.innerText;
    return {
      teTitol: /Rols de vora/i.test(t),
      files: [...document.querySelectorAll('select')].filter(s =>
        (s.getAttribute('aria-label')||'').startsWith('Rol del tram')).length,
      opcions: [...document.querySelectorAll('select')].filter(s =>
        (s.getAttribute('aria-label')||'').startsWith('Rol del tram'))
        .map(s => [...s.options].map(o=>o.textContent)),
      seleccionat: [...document.querySelectorAll('select')].filter(s =>
        (s.getAttribute('aria-label')||'').startsWith('Rol del tram')).map(s=>s.value),
    };
  })()`)
  say(`panell: ${JSON.stringify(panell)}`)

  // 3 · Assenyalar la PRIMERA fila → el llenç l'ha d'encendre i escriure-hi la mida.
  await evalJs(`(() => {
    const s = [...document.querySelectorAll('select')].find(x =>
      (x.getAttribute('aria-label')||'').startsWith('Rol del tram'));
    const fila = s.closest('div[style]');
    fila.dispatchEvent(new MouseEvent('mouseenter', {bubbles:true}));
    fila.click();
    return 'ok';
  })()`)
  await sleep(1800)

  const capsa = await evalJs(`(() => {
    const c = document.querySelector('canvas');
    if (!c) return null; const r = c.getBoundingClientRect();
    return {x:Math.round(r.x), y:Math.round(r.y), w:Math.round(r.width), h:Math.round(r.height)};
  })()`)
  say(`canvas: ${JSON.stringify(capsa)}`)

  const shot = await S('Page.captureScreenshot', { format: 'png' })
  writeFileSync(`${OUT}/smoke_taller_vora_illuminada.png`, Buffer.from(shot.data, 'base64'))
  say(`captura: ${OUT}/smoke_taller_vora_illuminada.png`)

  // 4 · ACCEPTA-TOTS + GRAVA sobre el CUELLO (2 trams, el cas petit).
  const accepta = await evalJs(`(() => {
    const b = [...document.querySelectorAll('button')].find(x => /Accepta les/i.test(x.textContent));
    if (!b) return 'sense botó accepta';
    b.click(); return b.textContent.trim();
  })()`)
  say(`accepta-tots: ${accepta}`)
  await sleep(1200)
  const grava = await evalJs(`(() => {
    const b = [...document.querySelectorAll('button')].find(x => /Grava els trams/i.test(x.textContent));
    if (!b) return 'sense botó grava';
    if (b.disabled) return 'BOTÓ DESACTIVAT (res per gravar)';
    b.click(); return 'clicat';
  })()`)
  say(`grava: ${grava}`)
  await sleep(4000)

  const despres = await evalJs(`(() => {
    const t = document.body.innerText;
    const m = t.match(/(\\d+) dits ·/);
    return { resum: m ? m[0] : '(sense resum)', teLandmarks: /Punts derivats/.test(t) };
  })()`)
  say(`després de gravar: ${JSON.stringify(despres)}`)

  const shot2 = await S('Page.captureScreenshot', { format: 'png' })
  writeFileSync(`${OUT}/smoke_taller_despres_de_gravar.png`, Buffer.from(shot2.data, 'base64'))
  say(`captura 2: ${OUT}/smoke_taller_despres_de_gravar.png`)

  writeFileSync(`${OUT}/smoke_taller.log`, log.join('\n') + '\n')
} catch (e) {
  console.error('SMOKE FALLIT:', e.message)
  process.exitCode = 1
} finally {
  chrome.kill()
}
