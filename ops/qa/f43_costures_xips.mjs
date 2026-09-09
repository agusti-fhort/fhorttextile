// F4.3 · FUM AMB ULLS: la targeta de proposta amb els xips nous, i el checklist.
import { spawn } from 'node:child_process'
import { writeFileSync, readFileSync } from 'node:fs'
const SP='/tmp/claude-0/-var-www/73d9d192-aca1-4077-9ee4-088e632fd07a/scratchpad'
const OUT=process.argv[2]||SP
const TOK=readFileSync(`${SP}/tok.txt`,'utf8').trim()
const CHROME='/root/.cache/ms-playwright/chromium_headless_shell-1234/chrome-headless-shell-linux64/chrome-headless-shell'
const BASE='http://127.0.0.1:5199'
const chrome=spawn(CHROME,['--remote-debugging-port=9337','--no-sandbox','--disable-gpu','--window-size=1600,1000','--hide-scrollbars','about:blank'],{stdio:['ignore','ignore','pipe']})
const sleep=ms=>new Promise(r=>setTimeout(r,ms))
async function wsUrl(){for(let i=0;i<40;i++){try{const r=await fetch('http://127.0.0.1:9337/json/version');return (await r.json()).webSocketDebuggerUrl}catch{await sleep(250)}}throw new Error('no CDP')}
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
  await S('Page.enable');await S('Runtime.enable')
  await S('Emulation.setDeviceMetricsOverride',{width:1600,height:1000,deviceScaleFactor:1,mobile:false})
  const ev=async e=>{const r=await S('Runtime.evaluate',{expression:e,awaitPromise:true,returnByValue:true}); if(r.exceptionDetails) throw new Error(r.exceptionDetails.text+' '+(r.exceptionDetails.exception?.description||'')); return r.result.value}
  // El llenç canvia després del primer pintat: cal forçar compositor abans de capturar
  // (llei apresa a F4.2-TER — sense això la captura torna el fotograma vell).
  const capta = async (f) => {
    await S('Emulation.setDeviceMetricsOverride',{width:1601,height:1000,deviceScaleFactor:1,mobile:false}); await sleep(350)
    await S('Emulation.setDeviceMetricsOverride',{width:1600,height:1000,deviceScaleFactor:1,mobile:false}); await sleep(800)
    const sh=await S('Page.captureScreenshot',{format:'png'}); writeFileSync(f,Buffer.from(sh.data,'base64')); return f }

  await S('Page.navigate',{url:BASE+'/'}); await sleep(1500)
  await ev(`localStorage.setItem('access_token',${JSON.stringify(TOK)});localStorage.setItem('fhort.lang','ca');'ok'`)
  await S('Page.navigate',{url:`${BASE}/models/1383/patro/taller`}); await sleep(8000)
  say('pantalla: ' + await ev(`document.querySelector('[data-ftt-screen="taller-patro"]')?'TALLER':'?'`))

  // «Buscar propostes» — el motor corre quan algú ho demana.
  const bt = await ev(`(()=>{const b=[...document.querySelectorAll('button')].find(x=>/Buscar propostes/i.test(x.textContent));if(!b)return 'sense boto';b.click();return 'clicat'})()`)
  say('buscar propostes: ' + bt)
  await sleep(6000)

  const estat = await ev(`(()=>{const t=document.body.innerText;
    return {
      teCataleg: /cat.leg espera aquesta parella/i.test(t),
      teChecklist: /El cat.leg n.esperaria/i.test(t),
      teBloc: /Proposa el cosit sencer/i.test(t),
      propostes: (t.match(/COSTURES PROPOSADES \\((\\d+)\\)/)||[])[1],
      mostra: (t.match(/cat.leg espera aquesta parella[^\\n]*/i)||[''])[0].slice(0,150),
      checklist: (t.match(/El cat.leg n.esperaria[^\\n]*/i)||[''])[0]
    }})()`)
  say('estat: ' + JSON.stringify(estat))
  // Portar el xip del catàleg a la vista: viu al peu del desglòs de la primera targeta.
  await ev(`(()=>{const el=[...document.querySelectorAll('li,span,p')]
    .find(e=>/cat.leg espera aquesta parella/i.test(e.textContent||'') && e.children.length===0);
    if(el) el.scrollIntoView({block:'center'});
    return el? 'centrat':'no trobat'})()`)
  await sleep(1200)
  say('captura: ' + await capta(`${OUT}/f43_01_targeta_amb_xips.png`))
}catch(e){console.error('SMOKE FALLIT:',e.message);process.exitCode=1}
finally{ writeFileSync(`${OUT}/smoke_f43.log`, log.join('\n')+'\n'); chrome.kill() }
