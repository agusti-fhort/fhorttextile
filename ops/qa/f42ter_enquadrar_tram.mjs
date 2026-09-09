// F4.2-TER · seleccionar un tram l'ENQUADRA. Mesura la càmera abans i després.
import { spawn } from 'node:child_process'
import { writeFileSync, readFileSync } from 'node:fs'
const SP='/tmp/claude-0/-var-www/73d9d192-aca1-4077-9ee4-088e632fd07a/scratchpad'
const OUT=process.argv[2]||SP
const TOK=readFileSync(`${SP}/tok.txt`,'utf8').trim()
const CHROME='/root/.cache/ms-playwright/chromium_headless_shell-1234/chrome-headless-shell-linux64/chrome-headless-shell'
const BASE='http://127.0.0.1:5199'
const chrome=spawn(CHROME,['--remote-debugging-port=9335','--no-sandbox','--disable-gpu','--window-size=1600,1000','--hide-scrollbars','about:blank'],{stdio:['ignore','ignore','pipe']})
const sleep=ms=>new Promise(r=>setTimeout(r,ms))
async function wsUrl(){for(let i=0;i<40;i++){try{const r=await fetch('http://127.0.0.1:9335/json/version');return (await r.json()).webSocketDebuggerUrl}catch{await sleep(250)}}throw new Error('no CDP')}
let id=0
const rpc=(ws,m,p={},s)=>new Promise((res,rej)=>{const mid=++id
  const on=ev=>{const x=JSON.parse(ev.data); if(x.id!==mid)return; ws.removeEventListener('message',on); x.error?rej(new Error(m+': '+JSON.stringify(x.error))):res(x.result)}
  ws.addEventListener('message',on); ws.send(JSON.stringify({id:mid,method:m,params:p,sessionId:s}))})
const log=[]; const say=s=>{console.log(s);log.push(s)}
try{
  const ws=new WebSocket(await wsUrl()); await new Promise(r=>ws.addEventListener('open',r))
  const {targetId}=await rpc(ws,'Target.createTarget',{url:'about:blank'})
  const {sessionId}=await rpc(ws,'Target.attachToTarget',{targetId,flatten:true})
  const S=(m,p)=>rpc(ws,m,p,sessionId)
  await S('Page.enable'); await S('Runtime.enable')
  await S('Emulation.setDeviceMetricsOverride',{width:1600,height:1000,deviceScaleFactor:1,mobile:false})
  const ev=async e=>{const r=await S('Runtime.evaluate',{expression:e,awaitPromise:true,returnByValue:true}); if(r.exceptionDetails) throw new Error(r.exceptionDetails.text+' '+(r.exceptionDetails.exception?.description||'')); return r.result.value}

  // 🚨 CAPTURA D'UN LLENÇ QUE HA CANVIAT DESPRÉS DEL PRIMER PINTAT.
  // `chrome-headless-shell --disable-gpu` torna el fotograma de compositor VELL: la
  // pantalla és correcta i la imatge menteix. Mesurat: amb la càmera ja moguda i
  // `layer.draw()` cridat a mà, la captura seguia sortint 99,87 % blanca. Un canvi de mida
  // invalida la capa i obliga a recompondre. Sense això, aquest fum reportaria un llenç
  // buit i faria «arreglar» un bug que no existeix.
  const capta = async (fitxer) => {
    await S('Emulation.setDeviceMetricsOverride',{width:1601,height:1000,deviceScaleFactor:1,mobile:false})
    await sleep(350)
    await S('Emulation.setDeviceMetricsOverride',{width:1600,height:1000,deviceScaleFactor:1,mobile:false})
    await sleep(800)
    const sh=await S('Page.captureScreenshot',{format:'png'})
    writeFileSync(fitxer, Buffer.from(sh.data,'base64'))
    return fitxer
  }

  await S('Page.navigate',{url:BASE+'/'}); await sleep(1500)
  await ev(`localStorage.setItem('access_token',${JSON.stringify(TOK)});localStorage.setItem('fhort.lang','ca');'ok'`)
  await S('Page.navigate',{url:`${BASE}/models/1383/patro/taller`}); await sleep(8000)

  // El DELANTERO: 16 trams, i és on hi ha els replecs de 17 mm — el cas que el sostre
  // de zoom ha de protegir.
  await ev(`(()=>{const b=[...document.querySelectorAll('button')].filter(e=>/837\\.DELANTERO/.test(e.textContent));b[0].click();return 1})()`)
  await sleep(4000)

  // La càmera abans: es llegeix de la transformació real de l'Stage de Konva.
  const cam = () => ev(`(()=>{const c=document.querySelector('canvas');
    const st=window.Konva&&Konva.stages&&Konva.stages[Konva.stages.length-1];
    return st?{zoom:+st.scaleX().toFixed(4),x:+st.x().toFixed(1),y:+st.y().toFixed(1)}:null})()`)

  const abans = await cam()
  say(`càmera abans:  ${JSON.stringify(abans)}`)

  const fila = await ev(`(()=>{const s=[...document.querySelectorAll('select')]
    .filter(x=>(x.getAttribute('aria-label')||'').startsWith('Rol del tram'));
    return {n:s.length, mides:[...document.querySelectorAll('select')]
      .filter(x=>(x.getAttribute('aria-label')||'').startsWith('Rol del tram'))
      .map(x=>x.closest('div[style]')?.textContent.slice(0,14))}})()`)
  say(`files del DELANTERO: ${JSON.stringify(fila)}`)

  // Passar-hi PER SOBRE no ha de moure la càmera.
  await ev(`(()=>{const s=[...document.querySelectorAll('select')]
    .filter(x=>(x.getAttribute('aria-label')||'').startsWith('Rol del tram'))[1];
    s.closest('div[style]').dispatchEvent(new MouseEvent('mouseenter',{bubbles:true}));return 1})()`)
  await sleep(900)
  const perSobre = await cam()
  const quiet = JSON.stringify(perSobre) === JSON.stringify(abans)
  say('camera despres de PASSAR-HI PER SOBRE: ' + JSON.stringify(perSobre)
      + '  -> ' + (quiet ? 'NO SHA MOGUT OK' : 'SHA MOGUT FALLA'))

  // CLICAR el tram 2 (un replec de 1,7 cm): ha d'enquadrar, amb sostre.
  await ev(`(()=>{const s=[...document.querySelectorAll('select')]
    .filter(x=>(x.getAttribute('aria-label')||'').startsWith('Rol del tram'))[1];
    s.closest('div[style]').click();return 1})()`)
  await sleep(1400)
  const petit = await cam()
  say(`càmera després de CLICAR el tram de 1,7 cm: ${JSON.stringify(petit)}`)
  await capta(`${OUT}/ter_01_tram_petit_enquadrat.png`)

  // I un tram gros (el 15, la vora de 62,7 cm).
  await ev(`(()=>{const s=[...document.querySelectorAll('select')]
    .filter(x=>(x.getAttribute('aria-label')||'').startsWith('Rol del tram'))[15];
    s.closest('div[style]').click();return 1})()`)
  await sleep(1400)
  const gros = await cam()
  say(`càmera després de CLICAR la vora de 62,7 cm: ${JSON.stringify(gros)}`)
  await capta(`${OUT}/ter_02_tram_gros_enquadrat.png`)

  // Tornar a clicar el MATEIX: ja es veu sencer → la càmera NO s'ha de moure.
  await ev(`(()=>{const s=[...document.querySelectorAll('select')]
    .filter(x=>(x.getAttribute('aria-label')||'').startsWith('Rol del tram'))[15];
    s.closest('div[style]').click();return 1})()`)
  await sleep(1400)
  const altre = await cam()
  say(`re-clic sobre el que JA ES VEU: ${JSON.stringify(altre)}`)

  // ── LA SEGONA LLISTA: els TRAMS DECLARATS de Relacions ────────────────────
  // El brief demana les dues llistes, i és la mateixa pregunta: «ensenya'm aquest tram».
  const trDecl = await ev(`(()=>{const h=[...document.querySelectorAll('*')]
    .find(e=>/^TRAMS DECLARATS/i.test(e.textContent||'') && e.children.length<3);
    if(!h) return 'sense secció';
    const cont=h.closest('div'); return cont? 'secció trobada':'sense contenidor'})()`)
  say(`trams declarats: ${trDecl}`)
  const abansDecl = await cam()
  const clicDecl = await ev(`(()=>{
    // Les files de tram declarat porten el títol de reanomenar; s'hi clica el contenidor.
    const b=[...document.querySelectorAll('button')]
      .filter(x=>(x.getAttribute('title')||'').match(/Reanomena|Rename|Renombra/i));
    if(!b.length) return 'sense files declarades';
    const fila=b[0].closest('div[style]').parentElement.parentElement;
    fila.click(); return 'clicada'})()`)
  say(`clic sobre un tram declarat: ${clicDecl}`)
  await sleep(1500)
  const despresDecl = await cam()
  say(`càmera: ${JSON.stringify(abansDecl)} → ${JSON.stringify(despresDecl)}`
      + (JSON.stringify(abansDecl)===JSON.stringify(despresDecl) ? '  (no s ha mogut)' : '  ENQUADRAT OK'))
  await capta(`${OUT}/ter_03_tram_declarat_enquadrat.png`)

  say(`sostre respectat? zoom del tram petit (${petit.zoom}) <= zoom que cabria la TAPETA`)
  writeFileSync(`${OUT}/smoke_ter.log`, log.join('\n')+'\n')
}catch(e){console.error('SMOKE FALLIT:',e.message);process.exitCode=1}finally{chrome.kill()}
