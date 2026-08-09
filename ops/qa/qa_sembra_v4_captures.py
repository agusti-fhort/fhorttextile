"""TRAM SEMBRA v4 · captures de `/poms` i `/poms/grading` contra el servei VIU.

Mateix arnès que `qa_f22_vocabulari_captures.py` (i pel mateix motiu): el bundle surt de
`frontend/dist` i **tota crida a `/api/` es reenvia al gunicorn viu**. Amb fixtures la foto
sortiria bé encara que la sembra no hi fos, que és justament el que s'ha de demostrar aquí.

El token necessita el claim `tenant_schema` i **no s'imprimeix mai**: entra per entorn.

    FTT_QA_TOKEN=... venv/bin/python ops/qa/qa_sembra_v4_captures.py
"""
import mimetypes
import os
import pathlib
import sys

import requests
from playwright.sync_api import sync_playwright

REPO = pathlib.Path(__file__).resolve().parents[2]
DIST = REPO / 'frontend' / 'dist'
OUT = pathlib.Path(__file__).resolve().parent / 'captures'
BASE = 'https://staging.fhorttextile.tech'
VIU = 'http://127.0.0.1:8001'
HOST_TENANT = os.environ.get('FTT_QA_HOST', 'fhorttextile.tech')
TOKEN = os.environ.get('FTT_QA_TOKEN', '')

PANTALLES = [
    ('01_cataleg_poms', '/poms',
     '142 POMs canònics repartits en 25 famílies', []),
    ('02_grading', '/poms/grading',
     'BRW-CATALEG-v3 amb 142 regles sobre ALPHA_EU_W', []),
]


def main():
    if not TOKEN:
        sys.exit("Falta FTT_QA_TOKEN (no s'imprimeix enlloc; passa'l per entorn).")
    if not DIST.exists():
        sys.exit(f'No hi ha bundle a {DIST}.')
    OUT.mkdir(exist_ok=True)
    sess = requests.Session()

    def handler(route, request):
        url = request.url
        cami = url.split(BASE, 1)[-1].split('?')[0] if url.startswith(BASE) else url
        if cami.startswith('/api/'):
            try:
                r = sess.request(
                    request.method, VIU + url.split(BASE, 1)[-1],
                    headers={'Host': HOST_TENANT, 'Authorization': f'Bearer {TOKEN}',
                             'Content-Type': request.header_value('content-type')
                                             or 'application/json'},
                    data=request.post_data_buffer, timeout=30)
                route.fulfill(status=r.status_code, body=r.content,
                              headers={'content-type': r.headers.get('content-type',
                                                                     'application/json')})
            except Exception as e:
                route.fulfill(status=502, body=f'{{"error": "{e}"}}',
                              headers={'content-type': 'application/json'})
            return
        f = DIST / cami.lstrip('/')
        if not f.is_file():
            f = DIST / 'index.html'
        route.fulfill(status=200, body=f.read_bytes(),
                      headers={'content-type': mimetypes.guess_type(f.name)[0] or 'text/html'})

    with sync_playwright() as p:
        nav = p.chromium.launch()
        ctx = nav.new_context(viewport={'width': 1600, 'height': 1000})
        pag = ctx.new_page()
        pag.route('**/*', handler)
        pag.goto(BASE + '/', wait_until='domcontentloaded')
        pag.evaluate("([t]) => { localStorage.setItem('access_token', t);"
                     " localStorage.setItem('fhort.lang', 'ca') }", [TOKEN])
        for nom, ruta, què, accions in PANTALLES:
            pag.goto(BASE + ruta, wait_until='networkidle')
            pag.wait_for_timeout(2000)
            for gest, sel in accions:
                try:
                    pag.locator(sel).first.click()
                    pag.wait_for_timeout(1200)
                except Exception as e:
                    print(f'  ⚠️  {nom}: {sel} no ha anat ({e})')
            desti = OUT / f'sembra_v4_{nom}.png'
            pag.screenshot(path=str(desti), full_page=True)
            print(f'✓ {desti.name:34} {ruta:16} {què}')
        nav.close()


if __name__ == '__main__':
    main()
