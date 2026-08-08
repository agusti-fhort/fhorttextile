"""A3 · captures de GRADING RULES contra el SERVEI VIU (bundle del disc + API real).

Mateix arnès que `qa_f22_vocabulari_captures.py`, i pel mateix motiu: el que s'ha de veure és
que la llista, els règims i les capes de relació surten del que el BACKEND DESPLEGAT contesta.
Amb fixtures la foto sortiria bé fins i tot amb el gunicorn vell.

  · el bundle (`/`, `/assets/*`) surt de `frontend/dist` — cal `npm run build` abans;
  · tota crida a `/api/` es reenvia a `http://127.0.0.1:8001` amb el `Host` del tenant.

EL TOKEN NECESSITA EL CLAIM `tenant_schema` i no s'imprimeix mai.

    FTT_QA_TOKEN=... venv/bin/python ops/qa/qa_a3_grading_rules.py
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

#: UN ESTAT PER CAPTURA. El banc de proves és el joc `ZZ-TEST-CHINO` (5 regles: 4 LINEAR + 1
#: STEP) sobre el run ALPHA_EU_W; la resta de jocs de `fhort` són buits, i això també s'ha de
#: veure (badge SENSE REGLES, «no declarat» a la columna de relacions).
PANTALLES = [
    ('01_llista', '/poms/grading',
     'la LLISTA: comptador+cerca, filtres de vista, columnes, «no declarat» i «sense origen»',
     []),
    ('02_llista_cerca', '/poms/grading',
     'la cerca filtra i el primer número del comptador ÉS el resultat',
     [('fill', 'input[placeholder*="cerca"]', 'ZZ')]),
    ('03_joc_regles', '/poms/grading',
     'pantalla del joc, tab «Talles i regles»: barra de talles, règims i Δ per regla',
     [('fill', 'input[placeholder*="cerca"]', 'ZZ'), ('click', 'button:has-text("Editar")')]),
    ('04_joc_relacions', '/poms/grading',
     'tab «Relacions»: Target multi · Construcció/Fit/Grup UN sol valor · NO DECLARAT',
     [('fill', 'input[placeholder*="cerca"]', 'ZZ'), ('click', 'button:has-text("Editar")'),
      ('click', 'button:has-text("Relacions")')]),
    ('05_relacions_declarades', '/poms/grading',
     'una capa marcada = VERD (esmena Agus) i la previsualització ho diu amb paraules',
     [('fill', 'input[placeholder*="cerca"]', 'ZZ'), ('click', 'button:has-text("Editar")'),
      ('click', 'button:has-text("Relacions")'), ('click', 'button:has-text("Woman")'),
      ('click', 'button:has-text("Woven")')]),
    ('06_joc_buit', '/poms/grading',
     'un joc SENSE REGLES: el badge i l\'estat buit amb paraules, no una taula muda',
     [('fill', 'input[placeholder*="cerca"]', 'LOS Man Knit'), ('click', 'button:has-text("Editar")')]),
    ('07_jubilats_buit', '/poms/grading',
     'la vista «Jubilats»: a `fhort` no n\'hi ha cap, i es diu',
     [('click', 'button:has-text("Jubilats")')]),
]


def main():
    if not TOKEN:
        sys.exit('Falta FTT_QA_TOKEN (passa\'l per entorn; no s\'imprimeix enlloc).')
    if not DIST.exists():
        sys.exit(f'No hi ha bundle a {DIST} — cal `npm run build`.')
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
                             'Content-Type': request.header_value('content-type') or 'application/json'},
                    data=request.post_data_buffer, timeout=30)
                route.fulfill(status=r.status_code, body=r.content,
                              headers={'content-type': r.headers.get('content-type', 'application/json')})
            except Exception as e:
                route.fulfill(status=502, body=f'{{"error": "{e}"}}',
                              headers={'content-type': 'application/json'})
            return
        rel = cami.lstrip('/')
        f = DIST / rel
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
            pag.wait_for_timeout(1500)
            for gest in accions:
                try:
                    if gest[0] == 'click':
                        pag.locator(gest[1]).first.click()
                    elif gest[0] == 'fill':
                        pag.locator(gest[1]).first.fill(gest[2])
                    pag.wait_for_timeout(900)
                except Exception as e:
                    print(f'  ⚠️  {nom}: {gest[0]} {gest[1]} no ha anat ({e})')
            desti = OUT / f'a3_{nom}.png'
            pag.screenshot(path=str(desti), full_page=True)
            print(f'✓ {desti.name:34} {ruta:16} {què}')
        nav.close()


if __name__ == '__main__':
    main()
