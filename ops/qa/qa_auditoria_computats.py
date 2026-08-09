"""AUDITORIA DE COMPUTATS · les 4 pantalles del bloc A (§8d: «la conformitat ES MESURA»).

Agus ha vist a pantalla LÍNIES NEGRES on la norma mana `--line` (#e8e5e0) i etiquetes/badges
per sobre de la mida de caption. Aquest script no mira el codi: mira el que el NAVEGADOR
COMPUTA, que és l'única cosa que Agus veu.

QUÈ MESURA, per a cada element visible de cada pantalla:
  · VORES — `getComputedStyle().border{Top,Right,Bottom,Left}Color` de tota vora amb amplada
    > 0 i estil ≠ none. Qualsevol color que no sigui de la paleta ratificada s'informa; i el
    que és `rgb(29,29,27)` (== --text-main == currentColor) es marca com a **VAR NO RESOLTA**,
    perquè és exactament el que passa quan un `var()` d'una vora no existeix: la declaració
    esdevé invàlida al càlcul i `border-color` cau al seu inicial, que és `currentColor`.
  · MIDES — `fontSize` de tot element que faci de badge (radi de píndola), de capçalera de
    llista/etiqueta (majúscules amb tracking) o de caption. La norma hi mana 10px.

No toca res: imprimeix la taula i surt amb codi 1 si hi ha cap incompliment.

    FTT_QA_TOKEN=... /tmp/qa-venv/bin/python ops/qa/qa_auditoria_computats.py
"""
import collections
import mimetypes
import os
import pathlib
import sys

import requests
from playwright.sync_api import sync_playwright

REPO = pathlib.Path(__file__).resolve().parents[2]
# El bundle a mesurar. Per defecte el desplegat (`frontend/dist`), que és el que Agus veu.
# `FTT_QA_DIST` el reapunta a un outDir de proves: amb tres sessions escrivint alhora, aquí
# `npm run build` DESPLEGA, i mesurar un canvi propi no pot obligar a publicar el codi a mig
# fer de ningú altre.
DIST = pathlib.Path(os.environ.get('FTT_QA_DIST') or (REPO / 'frontend' / 'dist'))
BASE = 'https://staging.fhorttextile.tech'
VIU = 'http://127.0.0.1:8001'
HOST_TENANT = os.environ.get('FTT_QA_HOST', 'fhorttextile.tech')
TOKEN = os.environ.get('FTT_QA_TOKEN', '')

PANTALLES = [
    ('A1 · Catàleg de POMs', '/poms'),
    ('A2 · Size Library', '/size-library'),
    ('A3 · Grading Rules', '/poms/grading'),
    ('A4 · Garment Types', '/garment-types'),
    # ── BLOC B · el camí del model ────────────────────────────────────────────────────────
    ('A5 · Models', '/models'),
    ('A6 · Dashboard del model', '/models/1319'),
    ('A7 · Resum · wizard partit', '/models/1319?tab=Resum'),
    ('A8 · Mesures', '/models/1319?tab=Mesures'),
    ('A10 · Comprovació', '/models/1319?tab=Mesures'),
    # ── PART B · LOT TÈCNIC (S1) ─────────────────────────────────────────────────────────
    # ⚠️ Les pantalles ja conformades es queden a la llista i no en surten mai: quan la NORMA
    # canvia —i el §8b-quater l'ha canviada— la mesura s'ha de tornar a passar per sobre de
    # tot el que ja estava tancat. És el segon forat que el bloc A va deixar passar.
    ('B1 · Desenvolupament (home)', '/'),
    ('B2 · Planificació', '/planificacio'),
    ('B3 · Fittings', '/fittings'),
    ('B4 · Documents', '/disseny/documents'),
    ('B5 · Fitxa tècnica (porta)', '/fitxa-tecnica'),
    ('B6 · Configuració general', '/configuracio/general'),
    ('B7 · Usuaris i rols', '/configuracio/usuaris'),
    ('B8 · Calendari d\'empresa', '/configuracio/calendari'),
    # ── AMPLIACIÓ DE LOT (Agus 09/08): la secció SISTEMA sencera ─────────────────────────
    ('B9 · Catàleg de tasques', '/task-types'),
    ('B10 · El meu perfil', '/perfil'),
    ('B11 · Recursos', '/recursos'),
    ('B12 · Safata d\'encàrrecs', '/encarrecs'),
    ('B13 · Configuració inicial', '/onboarding'),
    ('B14 · Import massiu', '/models/importar-colleccio'),
    # ── PART B · LOT FITXA TÈCNICA + PATRONS (S2) ────────────────────────────────────────
    # ⚠️ LES TRES SÓN PANTALLES AMB LLENÇ, i el llenç NO ENTRA al perímetre (ordre d'Agus:
    # «crom, MAI llenç»). Que hi surtin igualment és a posta: el que es mesura és la CLOSCA
    # —barres d'eines, panells laterals, modals, botons— i el llenç no aporta ni vores del
    # DOM ni text amb `fontSize` computat, perquè és un `<canvas>`: un sol node opac per a
    # l'auditor. O sigui que la mesura d'aquestes rutes és, literalment, la del crom.
    # El 3r element és el SENYAL: el selector que ha d'existir perquè la mesura valgui. V. el
    # bloc de `senyal` al bucle — les tres pantalles poden muntar-se «a mitges» sense fallar.
    ('C1 · Editor .ftt', '/models/1319/ftt/758', '[data-ftt-screen="ftt-editor"]'),
    ('C2 · Patró (tab del model)', '/models/1319?tab=Patr%C3%B3', '[data-ftt-screen="patro-tab"]'),
    ('C3 · Taller de patró', '/models/1319/patro/taller', '[data-ftt-screen="taller-patro"]'),
    # 🛑 SizeMapSetup NO TÉ RUTA: el seu `export default` no el munta ningú (v. el report). El
    # que SÍ que és viu és el seu `Wizard`, que munta `SizeAuthoringDrawer` des de la Size
    # Library — i s'audita allà, no aquí. Posar-hi una ruta inventada hauria mesurat un 404.
]

#: La paleta que la NORMA_LAYOUT §1 permet en una VORA, en rgb() tal com el navegador el computa.
VORES_OK = {
    'rgb(232, 229, 224)': '--line',
    'rgb(240, 238, 234)': '--line-soft',
    'rgb(224, 200, 160)': '--gold-border',
    'rgb(194, 122, 42)': '--gold',
    'rgb(46, 125, 50)': '--ok',
    'rgb(180, 35, 24)': '--err',
    'rgb(255, 153, 66)': '--warn-state',
    'rgb(43, 101, 194)': '--accio',
    'rgb(255, 255, 255)': '--panel/--white',
    'rgb(247, 245, 242)': '--sel',
    'rgb(251, 250, 248)': '--bg-page',
    # Una vora transparent és una DECISIÓ (el botó terciari en reserva el gruix per no
    # saltar en fer hover), no un color fora de paleta.
    'rgba(0, 0, 0, 0)': 'transparent (reserva de gruix)',
}
#: CROM DEL SISTEMA — **NOMÉS el menú lateral**. §8b: «el menú lateral NO ES TOCA». S'informa
#: perquè consti, però no compta com a incompliment de la pantalla: no és seu.
#:
#: ⚠️ LA LLISTA S'ESCURÇA (part B · §8b-quater). Hi havia també `rgb(228, 228, 226)` (#e4e4e2) i
#: `rgb(224, 213, 197)` (--border), i eren de la TOP BAR, que ara ja ha passat conformitat i no
#: en fa servir cap. Deixar-los aquí era pitjor que inútil: qualsevol PANTALLA que els pintés
#: quedava absolta per una excepció que ja no li pertocava — i va passar (`ui/Card`, quatre
#: vores a `/fittings`, donades per bones com a «crom del sistema»). Una excepció que sobreviu
#: al seu motiu és una tapadora.
CROM = {'rgb(232, 232, 232)'}
#: El negre de --text-main en una vora NO és una decisió: és `currentColor`, i per tant una
#: `var()` que no ha resolt. Es marca a part perquè la causa arrel és diferent.
NEGRE = 'rgb(29, 29, 27)'

JS = r"""
() => {
  const vores = {}, mides = [];
  const visible = (el, cs) => cs.display !== 'none' && cs.visibility !== 'hidden'
      && el.getBoundingClientRect().width > 0 && el.getBoundingClientRect().height > 0;
  const camI = (el) => {
    const parts = [];
    for (let n = el; n && n !== document.body && parts.length < 4; n = n.parentElement) {
      parts.unshift(n.tagName.toLowerCase() + (n.className && typeof n.className === 'string'
        ? '.' + n.className.trim().split(/\s+/).slice(0, 2).join('.') : ''));
    }
    return parts.join(' > ');
  };
  for (const el of document.querySelectorAll('body *')) {
    const cs = getComputedStyle(el);
    if (!visible(el, cs)) continue;
    for (const b of ['Top', 'Right', 'Bottom', 'Left']) {
      const w = parseFloat(cs['border' + b + 'Width']);
      if (!w || cs['border' + b + 'Style'] === 'none') continue;
      const c = cs['border' + b + 'Color'];
      (vores[c] = vores[c] || { n: 0, ex: [] }).n++;
      if (vores[c].ex.length < 3) vores[c].ex.push(camI(el) + ' [' + (el.textContent || '').trim().slice(0, 28) + ']');
    }
    const fs = parseFloat(cs.fontSize);
    const radi = parseFloat(cs.borderRadius);
    const clicable = el.tagName === 'BUTTON' || el.tagName === 'A' || el.tagName === 'SELECT';
    // BADGE = píndola que NO es clica (diu un estat). PÍNDOLA DE NAVEGACIÓ/XIP = píndola que
    // SÍ es clica. No són el mateix rol i la norma no els dona la mateixa mida: el badge va a
    // caption (10px, §1/§2) i la píndola del menú de pantalla va a cos (12px, §8b).
    const esBadge = radi >= 100 && !clicable && parseFloat(cs.paddingLeft) > 0 && el.children.length === 0;
    const esPindola = radi >= 100 && clicable && el.children.length === 0;
    const esRetol = cs.textTransform === 'uppercase' && parseFloat(cs.letterSpacing) > 0
      && el.children.length === 0;
    if ((esBadge || esPindola || esRetol) && (el.textContent || '').trim()) {
      mides.push({ tipus: esBadge ? 'badge' : esPindola ? 'píndola' : 'rètol', fs,
                   sostre: esPindola ? 12 : 10,
                   txt: (el.textContent || '').trim().slice(0, 32), cam: camI(el) });
    }
  }
  return { vores, mides };
}
"""


def _comprova_sessio(sess, quan):
    """🚨 TANCA LA SEGONA TAPADORA: **el token caduca a mitja correguda.**

    Quan passa, l'app cau a `/login` i l'arnès segueix mesurant — una altra pantalla, sense
    dir-ho. Ho hem vist les tres sessions de la part B el mateix dia: una passada de la
    bidireccional va donar «0 desviacions» amb els QUINZE casos morts, i un sondeig d'una altra
    sessió va donar cinc rutes «netes» seguides amb 66 nodes cadascuna.

    L'assercció va ABANS i DESPRÉS: abans perquè un token ja mort no arribi a produir cap
    número, i després perquè el número que s'acaba de donar només val si la sessió seguia viva
    quan es va prendre l'última mesura. **Un verd amb la sessió caiguda no és un verd feble: és
    un verd d'una altra cosa.**
    """
    try:
        r = sess.get(VIU + '/api/v1/me/', headers={'Host': HOST_TENANT,
                                                   'Authorization': f'Bearer {TOKEN}'}, timeout=15)
    except Exception as e:
        sys.exit(f'🛑 SESSIÓ NO COMPROVABLE ({quan}): {e}')
    if r.status_code != 200:
        sys.exit(f'🛑 LA SESSIÓ NO ÉS VÀLIDA ({quan}): /me/ → {r.status_code}. '
                 'El token ha caducat o no val per a aquest tenant; qualsevol número '
                 "d'aquesta correguda seria d'una altra pantalla (v. la 2a tapadora).")


def main():
    if not TOKEN:
        sys.exit("Falta FTT_QA_TOKEN.")
    if not DIST.exists():
        sys.exit(f'No hi ha bundle a {DIST} — cal `npm run build`.')
    sess = requests.Session()

    def handler(route, request):
        url = request.url
        cami = url.split(BASE, 1)[-1].split('?')[0] if url.startswith(BASE) else url
        if cami.startswith('/api/'):
            try:
                r = sess.request(request.method, VIU + url.split(BASE, 1)[-1],
                                 headers={'Host': HOST_TENANT, 'Authorization': f'Bearer {TOKEN}',
                                          'Content-Type': 'application/json'},
                                 data=request.post_data_buffer, timeout=30)
                route.fulfill(status=r.status_code, body=r.content,
                              headers={'content-type': r.headers.get('content-type', 'application/json')})
            except Exception as e:
                route.fulfill(status=502, body=f'{{"error":"{e}"}}',
                              headers={'content-type': 'application/json'})
            return
        f = DIST / cami.lstrip('/')
        if not f.is_file():
            f = DIST / 'index.html'
        route.fulfill(status=200, body=f.read_bytes(),
                      headers={'content-type': mimetypes.guess_type(f.name)[0] or 'text/html'})

    _comprova_sessio(sess, 'abans de començar')
    incompliments = 0
    with sync_playwright() as p:
        nav = p.chromium.launch()
        ctx = nav.new_context(viewport={'width': 1600, 'height': 1000})
        pag = ctx.new_page()
        pag.route('**/*', handler)
        pag.goto(BASE + '/', wait_until='domcontentloaded')
        pag.evaluate("([t]) => { localStorage.setItem('access_token', t);"
                     " localStorage.setItem('fhort.lang','ca') }", [TOKEN])
        for entrada in PANTALLES:
            nom, ruta = entrada[0], entrada[1]
            senyal = entrada[2] if len(entrada) > 2 else None
            pag.goto(BASE + ruta, wait_until='networkidle')
            pag.wait_for_timeout(1800)
            print(f'\n═══ {nom}  ({ruta}) ═══   [url={pag.url}]')
            # 🚨 LA QUARTA TAPADORA, APLICADA A LA LLISTA DE RUTES. Una pantalla que no s'ha
            # muntat no dona incompliments: en dona ZERO, i zero és el que volem veure. Aquí
            # ha estat REPRODUÏT, no imaginat: `/models/:id/ftt/<id-inexistent>` NO falla —
            # l'editor es munta en mode consulta— i `?tab=<qualsevol>` cau al tab per defecte
            # sense dir res. Els dos casos mesuren una pantalla diferent de la que anomenen i
            # la donen per conforme.
            # El `senyal` és opcional a posta (els casos que no en porten es comporten com
            # sempre), però on hi és, MANA: sense ell no es mesura, es CRIDA. I és un
            # `data-ftt-screen`, no un text ni un `nth`: un literal deixa de casar el dia que
            # es tradueix, i una posició, el dia que algú posa un element al davant.
            if senyal and pag.locator(senyal).count() == 0:
                incompliments += 1
                print(f'    🛑 SENYAL ABSENT ({senyal}) — la pantalla NO s\'ha muntat.')
                print('       No es mesura: un verd aquí voldria dir «no hi havia res a mirar».')
                continue
            d = pag.evaluate(JS)
            print('  VORES')
            for color, info in sorted(d['vores'].items(), key=lambda kv: -kv[1]['n']):
                if color in VORES_OK:
                    print(f'    ✓ {color:24} ×{info["n"]:<4} {VORES_OK[color]}')
                elif color == NEGRE:
                    incompliments += 1
                    print(f'    🔴 {color:24} ×{info["n"]:<4} VAR NO RESOLTA (currentColor)')
                    for e in info['ex']:
                        print(f'         · {e}')
                elif color in CROM:
                    print(f'    ·  {color:24} ×{info["n"]:<4} crom del sistema (top bar / menú lateral, §8b)')
                else:
                    incompliments += 1
                    print(f'    ⚠️  {color:24} ×{info["n"]:<4} FORA DE PALETA')
                    for e in info['ex']:
                        print(f'         · {e}')
            grans = [m for m in d['mides'] if m['fs'] > m['sostre']]
            print(f'  MIDES · {len(d["mides"])} badges/píndoles/rètols · {len(grans)} per sobre del sostre')
            per = collections.Counter((m['tipus'], m['fs']) for m in grans)
            for (tipus, fs), n in sorted(per.items(), key=lambda kv: -kv[1]):
                incompliments += 1
                ex = next(m for m in grans if m['tipus'] == tipus and m['fs'] == fs)
                print(f'    🔴 {tipus:6} {fs:.0f}px ×{n:<4} p.ex. «{ex["txt"]}»  {ex["cam"]}')
        nav.close()
    _comprova_sessio(sess, "just després de l'última mesura")
    print(f'\n──────── {incompliments} incompliments ────────')
    sys.exit(1 if incompliments else 0)


if __name__ == '__main__':
    main()
