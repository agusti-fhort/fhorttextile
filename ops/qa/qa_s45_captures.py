"""S45 · CAPTURES DE LES SUPERFÍCIES DEL BLOC 3+D — READ-ONLY.

⚠️ NO PREM CAP BOTÓ QUE ESCRIGUI. Ni «Mesurar prenda», ni «Mesurar set», ni «Propagar», ni
«Usar» al picker. Obre adreces de LECTURA i fotografia.

El bundle surt del DISC i l'API es proxya a 127.0.0.1:8001 amb el Host del tenant — el patró
de `qa_f22_vocabulari_captures.py`: així l'`auth_basic` de nginx no hi entra.

    FTT_QA_TOKEN=… /tmp/qa-venv/bin/python qa_s45.py
"""
import mimetypes
import os
import pathlib
import sys

import requests
from playwright.sync_api import sync_playwright

REPO = pathlib.Path('/var/www/ftt-staging')
DIST = REPO / 'frontend' / 'dist'
OUT = REPO / 'ops' / 'qa' / 'captures' / 's45'
BASE = 'https://staging.fhorttextile.tech'
VIU = 'http://127.0.0.1:8001'
HOST_TENANT = 'staging.fhorttextile.tech'
TOKEN = os.environ['FTT_QA_TOKEN']
MODEL = 1383

PANTALLES = [
    ('g1g2g3_graduacio',     f'/models/{MODEL}?tab=Mesures&mode=graduacio', 'G1·G2·G3 — Graduació', []),
    ('g2g4_mesures',         f'/models/{MODEL}?tab=Mesures',                'G2·G4 — Mesures', []),
    ('g5_fitting_viva',      '/fittings/159',                               'G5 — sessió VIVA', []),
    ('g5_fitting_segellada', '/fittings/155',                               'G5 — sessió SEGELLADA', []),
    ('g5_escalat',           f'/models/{MODEL}?tab=Escalat',                'G5 — Escalat (control)', []),
    ('c_picker_jocs',        f'/models/{MODEL}?tab=Resum',                  'C — picker de jocs',
     [('click_last', "button:has-text('Canviar')")]),
    ('d_cataleg_poms',       '/poms',                                       'D — catàleg de POMs', []),
    ('d_form_nou_pom',       '/poms',                                       'D — formulari «Nou POM»',
     [('click', "text=Nou POM")]),
]

sess = requests.Session()


def handler(route, request):
    url = request.url
    cami = url.split(BASE, 1)[-1].split('?')[0] if url.startswith(BASE) else url
    if cami.startswith('/api/') or cami.startswith('/media/'):
        try:
            r = sess.request(
                request.method, VIU + url.split(BASE, 1)[-1],
                headers={'Host': HOST_TENANT, 'Authorization': f'Bearer {TOKEN}',
                         'Content-Type': request.header_value('content-type') or 'application/json'},
                data=request.post_data_buffer, timeout=30)
            route.fulfill(status=r.status_code, body=r.content,
                          headers={'content-type': r.headers.get('content-type', 'application/json')})
        except Exception as e:
            route.fulfill(status=502, body=f'{{"error": "{e}"}}',
                          headers={'content-type': 'application/json'})
        return
    f = DIST / cami.lstrip('/')
    if not f.is_file():
        f = DIST / 'index.html'
    route.fulfill(status=200, body=f.read_bytes(),
                  headers={'content-type': mimetypes.guess_type(f.name)[0] or 'text/html'})


OUT.mkdir(parents=True, exist_ok=True)
errors = []
with sync_playwright() as p:
    nav = p.chromium.launch(args=['--no-sandbox'])
    ctx = nav.new_context(viewport={'width': 1600, 'height': 1100})
    pag = ctx.new_page()
    pag.on('pageerror', lambda e: errors.append(str(e)))
    pag.route('**/*', handler)
    pag.goto(BASE + '/', wait_until='domcontentloaded')
    pag.evaluate("([t]) => { localStorage.setItem('access_token', t);"
                 " localStorage.setItem('fhort.lang', 'ca') }", [TOKEN])
    for nom, ruta, etiqueta, accions in PANTALLES:
        pag.goto(BASE + ruta, wait_until='networkidle')
        pag.wait_for_timeout(2500)
        for gest, sel in accions:
            try:
                loc = pag.locator(sel)
                (loc.last if gest == 'click_last' else loc.first).click()
                pag.wait_for_timeout(2500)
            except Exception as e:
                print(f'      ⚠ {gest} {sel}: {e}')
        pag.screenshot(path=str(OUT / f'{nom}.png'), full_page=True)
        print(f'  ✓ {etiqueta:<26} → {nom}.png')
    nav.close()

if errors:
    print('\n  ✗ ERRORS DE PÀGINA:')
    for e in errors[:10]:
        print(f'      {e}')
    sys.exit(1)
print('\n  ✓ cap error de pàgina')
