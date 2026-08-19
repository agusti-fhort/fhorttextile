"""ARNÈS · SET-2/T8 · EL BOTÓ D'IMPORTAR, ENCÈS A LES FILLES · model 1320.

L'altra meitat del tram: el domini ja el mesura `qa_t8_import_per_prenda.py` (contra dades
vives i amb rollback). Aquí es mesura **la pantalla**, i les dues coses que el brief hi
demanava:

  T8.1 · el botó «Importar taula» de la fila superior de la `02` **ja no està apagat**
         (B9 el va deixar `disabled` amb el motiu al `title`; era l'últim pas del tram)
  T8.2 · obrir-lo des de la `02` porta el wizard amb la PRENDA COM A FET —«Important a:
         Pantaló»— i **sense preguntar-la enlloc**
  T8.3 · a la mare el rètol NO surt (a un model d'una sola peça seria soroll dir
         «important a la peça principal» quan no n'hi ha cap altra)

⚠️ **CAP ESCRIPTURA POT SORTIR D'AQUÍ, i està demostrat a la sortida.** El tab de Mesures en
mode entrada és un GEST que escriu al domini, o sigui que aquest arnès **barra TOTS els
POST/PATCH/PUT/DELETE** —no n'hi ha cap de legítim per a la seva pregunta— i els censa. Si la
llista de barrades surt buida, millor; si no, es veu què s'ha aturat. Cap crida de cribratge
(que és de pagament) hi arriba: l'arnès s'atura a la pantalla d'adjuntar el document.

    FTT_QA_TOKEN=... FTT_QA_API=http://127.0.0.1:8001 \\
    /tmp/qa-venv/bin/python ops/qa/qa_t8_boto_import_peca.py
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
    barrades = []

    def handler(route, request):
        url = request.url
        cami = url.split(BASE, 1)[-1] if url.startswith(BASE) else url
        net = cami.split('?')[0]
        if net.startswith('/api/'):
            if request.method != 'GET':
                barrades.append(f'{request.method} {net}')
                route.fulfill(status=200, body=request.post_data or '{}',
                              headers={'content-type': 'application/json'})
                return
            try:
                r = sess.request('GET', VIU + cami, headers=caps, timeout=30)
                route.fulfill(status=r.status_code, body=r.content,
                              headers={'content-type': r.headers.get('content-type',
                                                                     'application/json')})
            except Exception as e:                                    # noqa: BLE001
                route.fulfill(status=500, body=str(e))
            return
        rel = net.lstrip('/') or 'index.html'
        fitxer = DIST / rel
        if not fitxer.is_file():
            fitxer = DIST / 'index.html'
        tipus = mimetypes.guess_type(str(fitxer))[0] or 'text/html'
        route.fulfill(status=200, body=fitxer.read_bytes(), headers={'content-type': tipus})

    with sync_playwright() as p:
        nav = p.chromium.launch()
        pag = nav.new_page(viewport={'width': 1440, 'height': 1600})
        pag.route('**/*', handler)
        pag.goto(BASE, wait_until='domcontentloaded')
        pag.evaluate("([t]) => { localStorage.setItem('access_token', t);"
                     " localStorage.setItem('fhort.lang', 'ca') }", [TOKEN])
        pag.goto(f'{BASE}/models/{MODEL}?tab=Mesures&mode=entry', wait_until='networkidle')
        pag.wait_for_timeout(2500)

        botons = pag.get_by_role('button', name='Importar taula')
        n = botons.count()
        mira('T8.1a · un botó «Importar taula» per contenidor', n >= 2, f'{n} botons')
        apagats = [i for i in range(n) if botons.nth(i).is_disabled()]
        mira('T8.1b · cap apagat (el `disabled` de B9 ha marxat)', not apagats,
             f'apagats: {apagats}' if apagats else 'tots vius')
        pag.screenshot(path=str(OUT / 't8_1_botons.png'), full_page=True)

        # ── T8.2 · el DARRER contenidor és la 02: obrir-hi l'import ─────────────────────
        if n >= 2:
            botons.nth(n - 1).click()
            pag.wait_for_timeout(1200)
            cos = pag.locator('body').inner_text()
            mira('T8.2a · el wizard diu la prenda com un fet', 'Important a:' in cos,
                 [l for l in cos.splitlines() if 'Important a' in l][:1])
            mira('T8.2b · i la diu pel NOM', 'Pantaló' in cos.split('Important a:')[-1][:60],
                 cos.split('Important a:')[-1][:40].replace('\n', ' ').strip())
            # I NO LA PREGUNTA. El criteri no pot ser «cap `select` a la pàgina» —el full de
            # model en té de seus, fora del wizard— sinó **cap desplegable que ofereixi
            # triar una prenda**: cap `option` amb el nom o el codi d'una peça.
            opcions = pag.locator('select option').all_inner_texts()
            ofereix_peces = [o for o in opcions if 'Pantaló' in o or o.strip() in ('02', '03')]
            mira('T8.2c · el wizard NO pregunta la peça (cap opció de prenda enlloc)',
                 not ofereix_peces, f'{len(opcions)} opcions; sospitoses: {ofereix_peces}')
            pag.screenshot(path=str(OUT / 't8_2_wizard_02.png'), full_page=True)

        # ── T8.3 · a la mare, el rètol no surt ─────────────────────────────────────────
        pag.goto(f'{BASE}/models/{MODEL}?tab=Mesures&mode=entry', wait_until='networkidle')
        pag.wait_for_timeout(2500)
        botons = pag.get_by_role('button', name='Importar taula')
        if botons.count():
            botons.nth(0).click()
            pag.wait_for_timeout(1200)
            mira('T8.3 · a la mare no hi ha rètol de prenda',
                 'Important a:' not in pag.locator('body').inner_text())
            pag.screenshot(path=str(OUT / 't8_3_wizard_mare.png'), full_page=True)

        nav.close()

    print(f'\nESCRIPTURES BARRADES (cap n\'ha arribat a la BD): {barrades or "cap"}')
    print('✅ ARNÈS VERD' if not falles else f'❌ ARNÈS VERMELL: {falles}')
    return 0 if not falles else 1


if __name__ == '__main__':
    sys.exit(main())
