"""ARNÈS · SET-2/T7 B3+B4 · LA SUPERFÍCIE DE PECES AMB DUES PRENDES VIVES · model 1320.

El contracte de la porta (POST/PATCH/DELETE) el mesuren les proves de
`test_set2_t2bis_modelgarment.py::LaPortaDescripturaTest`. Aquí es mesura L'ALTRE COSTAT: que
la pantalla la faci servir, i que amb DUES peces digui de quina parla a cada lloc.

  B3.1 · dues targetes: la mare i la 02, cadascuna amb la seva capçalera
  B3.2 · el fantasma «Afegir peça» hi és, i s'obre en formulari amb el CODI proposat
  B3.3 · el focus va al NOM, no al codi (el gest mínim és batejar)
  B3.4 · el llapis és VIU a totes dues targetes (ja no és inert)
  B3.5 · els «Canviar» d'una peça no-mare ja no estan apagats
  B3.6 · la peça que hereta ho DIU, i el valor efectiu hi és igualment
  B3.7 · l'esborrat és secundari i viu DINS de la targeta, mai a la mare

⚠️ **LES COMPORTES DE MESURA, INTACTES I DEMOSTRAT**: aquest arnès deixa passar cap a la BD
NOMÉS les escriptures a `/peces/`. Qualsevol altre POST/PATCH/PUT/DELETE es respon localment
amb l'eco i es CENSA a la sortida — o sigui que si la pantalla intentés escriure una mesura de
la 02, aquí es veuria i no arribaria enlloc. Crear un `ModelGarment` és legítim; escriure
mesures de la 02 no ho serà fins al #12, i que les taules de la 02 surtin BUIDES és l'estat
correcte.

    FTT_QA_TOKEN=... FTT_QA_API=http://127.0.0.1:8123 FTT_QA_DIST=<build de scratch> \\
    /tmp/qa-venv/bin/python ops/qa/qa_t7_b3b4_peces.py

(El `FTT_QA_API` apunta a un servidor de DISC: el gunicorn serveix el codi de quan va arrencar
—v. la capçalera de `qa_b34_router_i_estat.py`— i `npm run build` sobre `frontend/dist` ÉS un
desplegament en aquest muntatge, per això el `FTT_QA_DIST` de scratch.)
"""
import mimetypes
import os
import pathlib
import sys

import requests
from playwright.sync_api import sync_playwright

REPO = pathlib.Path(__file__).resolve().parents[2]
DIST = pathlib.Path(os.environ.get('FTT_QA_DIST') or (REPO / 'frontend' / 'dist'))
OUT = pathlib.Path(__file__).resolve().parent / 'captures'
BASE = 'https://staging.fhorttextile.tech'
VIU = os.environ.get('FTT_QA_API') or 'http://127.0.0.1:8001'
TOKEN = os.environ.get('FTT_QA_TOKEN', '')
MODEL = 1320

#: L'ÚNICA vora on aquest arnès deixa escriure. La resta es responen localment i es censen.
VORA_ESCRIVIBLE = f'/api/v1/models/{MODEL}/peces/'

falles = []


def mira(nom, ok, detall=''):
    print(f'  {"✅" if ok else "❌"} {nom}' + (f' — {detall}' if detall else ''))
    if not ok:
        falles.append(nom)


def main():
    if not TOKEN:
        sys.exit('Falta FTT_QA_TOKEN')
    OUT.mkdir(exist_ok=True)
    sess = requests.Session()
    caps = {'Host': 'staging.fhorttextile.tech', 'Authorization': f'Bearer {TOKEN}'}
    escriptures_barrades, escriptures_passades = [], []

    def handler(route, request):
        url = request.url
        cami = url.split(BASE, 1)[-1] if url.startswith(BASE) else url
        net = cami.split('?')[0]
        if net.startswith('/api/'):
            if request.method != 'GET' and not net.startswith(VORA_ESCRIVIBLE):
                escriptures_barrades.append(f'{request.method} {net}')
                route.fulfill(status=200, body=request.post_data or '{}',
                              headers={'content-type': 'application/json'})
                return
            if request.method != 'GET':
                escriptures_passades.append(f'{request.method} {net}')
            try:
                r = sess.request(request.method, VIU + cami, headers={
                    **caps, 'Content-Type': request.headers.get('content-type', 'application/json'),
                }, data=request.post_data, timeout=30)
                route.fulfill(status=r.status_code, body=r.content,
                              headers={'content-type': r.headers.get('content-type', 'application/json')})
            except Exception as e:                                    # noqa: BLE001
                route.fulfill(status=500, body=str(e))
            return
        # El bundle surt del DIST que s'indiqui; la resta de rutes cauen a l'index (SPA).
        rel = net.lstrip('/') or 'index.html'
        fitxer = DIST / rel
        if not fitxer.is_file():
            fitxer = DIST / 'index.html'
        tipus = mimetypes.guess_type(str(fitxer))[0] or 'text/html'
        route.fulfill(status=200, body=fitxer.read_bytes(), headers={'content-type': tipus})

    with sync_playwright() as p:
        nav = p.chromium.launch()
        pag = nav.new_page(viewport={'width': 1440, 'height': 1400})
        pag.route('**/*', handler)
        # La clau és `access_token` (v. `store/auth.js`) i s'ha d'escriure amb un ORIGEN ja
        # carregat: per això la primera visita és només per tenir-lo.
        pag.goto(BASE, wait_until='domcontentloaded')
        pag.evaluate("([t]) => { localStorage.setItem('access_token', t);"
                     " localStorage.setItem('fhort.lang', 'ca') }", [TOKEN])
        pag.goto(f'{BASE}/models/{MODEL}?tab=Resum', wait_until='networkidle')
        pag.wait_for_timeout(2000)

        # ── B3.1 · DUES TARGETES ──────────────────────────────────────────────────────────
        targetes = pag.locator('section[id^="peca-"]')
        n = targetes.count()
        mira('B3.1 dues targetes de prenda', n == 2, f'{n} targeta/es')
        ancles = [targetes.nth(i).get_attribute('id') for i in range(n)]
        mira('B3.1 la mare primera i la 02 darrere', ancles == ['peca-base', 'peca-02'], str(ancles))

        # ── B1c · LA TARGETA ÉS COMPACTA (correcció d'Agus a pantalla, 12/08) ────────────
        # El que es va desplegar feia ~450 px per targeta: cada apartat ocupava un BLOC amb
        # sub-rètols en línies pròpies. Amb dues prendes ja no en cabia una a pantalla, i la
        # pila de targetes existeix justament per poder-les comparar d'un cop d'ull.
        #
        # ⚠️ ES MESURA, NO ES MIRA. Una captura demostra que "es veu bé" el dia que es pren; un
        # llindar en píxels torna a fallar el dia que algú hi torni a posar un bloc.
        #
        # 🚩 EL LLINDAR ÉS 250 I NO 190, I EL MOTIU S'HA DE SABER. Mesurat a quatre amplades:
        #   1280 → 181 · 175    (una columna: la graella d'auto-fit encara no es parteix)
        #   1440 → 239 · 218    ← L'ÚNICA BANDA DOLENTA
        #   1680 → 181 · 175
        #   1920 → 181 · 175
        # A 1440 la graella JA fa dues columnes però cadascuna es queda a ~540 px, i les dues
        # files més llargues (els chips + «Buttoned Tops · Blusa», i el run de cinc talles)
        # passen a dues línies. No és que la compactació falli —és el `minmax(min(100%,520px))`
        # de §8f, que parteix massa aviat—. Pujar-lo a ~620 px mataria la banda, però mou un
        # BREAKPOINT RATIFICAT i això és decisió d'Agus, no d'aquest arnès.
        altures = [targetes.nth(i).bounding_box()['height'] for i in range(n)]
        mira('B1c cada targeta és PRIMA (≤ 250 px, i ≤ 190 fora de la banda de 1440)',
             all(h <= 250 for h in altures), ' · '.join(f'{h:.0f}px' for h in altures))
        files_per_targeta = [targetes.nth(i).locator('> div').count() for i in range(n)]
        mira('B1c tres files per targeta + capçalera', all(f == 4 for f in files_per_targeta),
             str(files_per_targeta))
        # I la prova que importa de debò: les DUES targetes i el fantasma, en una pantalla.
        # El llindar és 900 px —l'alçada d'un portàtil corrent— i NO l'alçada del viewport
        # d'aquest arnès, que és alta a posta perquè les captures `full_page` surtin senceres.
        fant = pag.locator('button:has-text("Afegir peça")').first
        caixa = fant.bounding_box()
        baix = caixa['y'] + caixa['height']
        mira('B1c les dues targetes i el fantasma caben en una pantalla de portàtil (900 px)',
             baix <= 900, f'el fantasma acaba a {baix:.0f}px')

        # ── B3.6 · LA PEÇA QUE HERETA HO DIU, i el valor efectiu hi és ────────────────────
        text02 = targetes.nth(1).inner_text().lower() if n == 2 else ''
        mira('B3.6 la 02 diu que hereta', 'hereta del model' in text02)
        mira('B3.6 i el valor efectiu hi és igualment', 'xxs·xs·s·m·l' in text02, text02[:60])

        # ── B3.4/B3.5/B3.7 · ELS GESTOS JA NO SÓN INERTS ─────────────────────────────────
        llapis = pag.locator('button[title="Reanomenar"]')
        mira('B3.4 un llapis per targeta', llapis.count() == 2, f'{llapis.count()}')
        mira('B3.4 i cap dels dos és inert', all(
            llapis.nth(i).is_enabled() for i in range(llapis.count())))
        papereres = pag.locator('button[title="Esborrar peça"]')
        mira('B3.7 la paperera NOMÉS a la 02 (la mare no té fila)', papereres.count() == 1,
             f'{papereres.count()}')
        canviar02 = targetes.nth(1).locator('button:has-text("Canviar")') if n == 2 else None
        mira('B3.5 els dos «Canviar» de la 02 són vius',
             canviar02 is not None and canviar02.count() == 2
             and all(canviar02.nth(i).is_enabled() for i in range(canviar02.count())),
             f'{canviar02.count() if canviar02 else 0} botons')
        pag.screenshot(path=str(OUT / 't7_b3_01_dues_peces.png'), full_page=True)

        # ── B3.2/B3.3 · EL FANTASMA ──────────────────────────────────────────────────────
        fantasma = pag.locator('button:has-text("Afegir peça")')
        mira('B3.2 el fantasma hi és', fantasma.count() >= 1)
        fantasma.first.click()
        pag.wait_for_timeout(400)
        codi = pag.locator('input').nth(0)
        mira('B3.2 el codi ve proposat i és el següent del màxim',
             codi.input_value() == '03', codi.input_value())
        enfocat = pag.evaluate('document.activeElement?.placeholder || ""')
        mira('B3.3 el focus va al NOM', 'Pantaló' in enfocat or 'Caputxa' in enfocat, enfocat)
        pag.screenshot(path=str(OUT / 't7_b3_02_fantasma_obert.png'), full_page=True)

        # ── EL 409 DEL CODI DUPLICAT, TAL COM ARRIBA ─────────────────────────────────────
        codi.fill('02')
        pag.locator('section button:has-text("Afegir peça")').last.click()
        pag.wait_for_timeout(900)
        cos = pag.locator('body').inner_text().lower()
        mira('B3.2 el 409 de codi duplicat es diu amb el text del servidor',
             'ja té una peça amb el codi' in cos)
        pag.screenshot(path=str(OUT / 't7_b3_03_codi_duplicat_409.png'), full_page=True)

        # ── EL 400 DEL CODI BUIT ─────────────────────────────────────────────────────────
        codi.fill('')
        pag.wait_for_timeout(300)
        afegir = pag.locator('section button:has-text("Afegir peça")').last
        mira('B3.2 amb el codi buit el botó no promet res', afegir.is_disabled())

        # ── L'EDITOR DE TALLES D'UNA PEÇA ────────────────────────────────────────────────
        pag.locator('button:has-text("Cancel·lar")').last.click()
        pag.wait_for_timeout(300)
        targetes.nth(1).locator('button:has-text("Canviar")').first.click()
        pag.wait_for_timeout(1200)
        mira('B3.5 l\'editor de talles s\'obre DINS de la targeta de la 02',
             targetes.nth(1).locator('button:has-text("Desar talles")').count() == 1)
        pag.screenshot(path=str(OUT / 't7_b3_04_editor_talles_peca.png'), full_page=True)

        # ── L'ESBORRAT ──────────────────────────────────────────────────────────────────
        pag.locator('button:has-text("Cancel·lar")').last.click()
        pag.wait_for_timeout(400)
        papereres.first.click()
        pag.wait_for_timeout(500)
        mira('B3.7 el diàleg d\'esborrat diu de quina peça parla',
             'peça:' in pag.locator('body').inner_text().lower())
        pag.screenshot(path=str(OUT / 't7_b3_05_esborrar_dialeg.png'), full_page=True)

        nav.close()

    print(f'\n  Escriptures DEIXADES PASSAR (només /peces/): {escriptures_passades or "cap"}')
    print(f'  Escriptures BARRADES (comportes de mesura): {escriptures_barrades or "cap"}')
    fora = [e for e in escriptures_passades if VORA_ESCRIVIBLE not in e]
    mira('COMPORTES · cap escriptura fora de /peces/', not fora, str(fora))

    print(f'\n{"❌ FALLES: " + ", ".join(falles) if falles else "✅ tot verd"}')
    return 1 if falles else 0


if __name__ == '__main__':
    sys.exit(main())
