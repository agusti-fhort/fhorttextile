"""F2.2-final · captures dels controls que ara pinta el VOCABULARI, contra el servei VIU.

⚠️ **AQUÍ L'API NO POT ANAR MOCKADA**, i és tota la gràcia. La resta de scripts d'aquesta
carpeta serveixen `/api/` des de fixtures perquè volen aïllar el CSS; aquest tram fa
exactament el contrari: el que s'ha de veure és que les píndoles i els desplegables surten
d'allò que el BACKEND DESPLEGAT contesta. Amb fixtures, la foto sortiria bé fins i tot amb
el gunicorn vell — que és precisament el mode de fallada que la llei d'infra descriu.

Com se serveix, doncs:

  · el bundle (`/`, `/assets/*`, …) surt de `frontend/dist` per `page.route` — nginx hi té
    `auth_basic` i no cal cap credencial per llegir el disc;
  · tota crida a `/api/` es reenvia a `http://127.0.0.1:8001` (el gunicorn viu) amb el
    `Host` del tenant i el token per capçalera.

EL TOKEN NECESSITA EL CLAIM `tenant_schema` (si no, el middleware no resol el tenant) i **no
s'imprimeix mai**: entra per variable d'entorn i es queda al procés.

`page.route` corre l'ÚLTIM handler registrat PRIMER i `route.continue_()` se'n va a xarxa
saltant-se els anteriors: per això aquí hi ha UN SOL handler que decideix a dins.

    FTT_QA_TOKEN=... venv/bin/python ops/qa/qa_f22_vocabulari_captures.py
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

#: (nom, ruta, què s'hi ha de veure, accions). Triades perquè PINTEN VOCABULARI, no perquè
#: siguin boniques: cada una és un control que fins avui es dibuixava des d'una constant del
#: client.
#:
#: ⚠️ LES `accions` NO SÓN COSMÈTICA. Dues d'aquestes pantalles amaguen darrere d'una porta
#: justament els controls que aquest tram toca: els chips de construcció i fit de Size Library
#: no existeixen fins que hi ha un target triat, i el pas 2 del wizard —les tres files de
#: píndoles d'eixos— està BLOQUEJAT fins que s'ha triat un client. Fotografiar-les sense obrir
#: la porta donaria cinc captures verdes que no ensenyen res del que s'ha canviat.
PANTALLES = [
    ('01_models_filtre_fase', '/models',
     'select de fase → fases_model', []),
    ('02_fitting_sessions', '/fittings',
     'dues files de píndoles → fases_model + estats_sessio_fitting', []),
    ('03_grading_rule_sets', '/poms/grading',
     'pills de target → /targets/, en display_order i amb franja d\'edat', []),
    ('04_size_library', '/size-library',
     'target → construcció → fit, els tres de useEixos', [('click', 'text=Dona')]),
    ('05_model_wizard', '/models/nou',
     'pas 2: les tres files de píndoles d\'eixos, del catàleg de la BD',
     [('tria_client', ''), ('click', 'button:has-text("Spring/Summer")'),
      ('click', 'button:has-text("Següent")')]),
]


def main():
    if not TOKEN:
        sys.exit('Falta FTT_QA_TOKEN (no s\'imprimeix enlloc; passa\'l per entorn).')
    if not DIST.exists():
        sys.exit(f'No hi ha bundle a {DIST} — cal `npm run build`.')
    OUT.mkdir(exist_ok=True)
    sess = requests.Session()

    def handler(route, request):
        url = request.url
        cami = url.split(BASE, 1)[-1].split('?')[0] if url.startswith(BASE) else url

        # ── /api/ → EL SERVEI VIU (no fixtures: v. la capçalera) ──────────────
        if cami.startswith('/api/'):
            try:
                r = sess.request(
                    request.method, VIU + url.split(BASE, 1)[-1],
                    headers={'Host': HOST_TENANT, 'Authorization': f'Bearer {TOKEN}',
                             'Content-Type': request.header_value('content-type') or 'application/json'},
                    data=request.post_data_buffer, timeout=30)
                route.fulfill(status=r.status_code, body=r.content,
                              headers={'content-type': r.headers.get('content-type', 'application/json')})
            except Exception as e:  # una crida caiguda no ha de matar la sessió sencera
                route.fulfill(status=502, body=f'{{"error": "{e}"}}',
                              headers={'content-type': 'application/json'})
            return

        # ── la resta → el bundle del disc ─────────────────────────────────────
        rel = cami.lstrip('/')
        f = DIST / rel
        if not f.is_file():
            f = DIST / 'index.html'          # SPA: qualsevol ruta és index.html
        route.fulfill(status=200, body=f.read_bytes(),
                      headers={'content-type': mimetypes.guess_type(f.name)[0] or 'text/html'})

    with sync_playwright() as p:
        nav = p.chromium.launch()
        ctx = nav.new_context(viewport={'width': 1600, 'height': 1000})
        pag = ctx.new_page()
        pag.route('**/*', handler)
        pag.goto(BASE + '/', wait_until='domcontentloaded')
        # `fhort.lang` és la clau de l'idioma; el token va a `access_token`.
        pag.evaluate("([t]) => { localStorage.setItem('access_token', t);"
                     " localStorage.setItem('fhort.lang', 'ca') }", [TOKEN])
        for nom, ruta, què, accions in PANTALLES:
            pag.goto(BASE + ruta, wait_until='networkidle')
            pag.evaluate("() => localStorage.setItem('fhort.lang', 'ca')")
            pag.wait_for_timeout(1500)
            for gest, sel in accions:
                try:
                    if gest == 'click':
                        pag.locator(sel).first.click()
                    elif gest == 'tria_client':
                        # ⚠️ NO el primer `select` de la pàgina: aquell és el de l'IDIOMA, que
                        # viu a la capçalera i surt abans al DOM. Triar-lo posava la interfície
                        # en castellà i deixava el wizard igual de tancat. El del client és el
                        # següent, i el seu primer `option` és el placeholder «Tria un client…».
                        pag.locator('select').nth(1).select_option(index=1)
                    pag.wait_for_timeout(1200)
                except Exception as e:
                    print(f'  ⚠️  {nom}: {gest} {sel} no ha anat ({e})')
            desti = OUT / f'f22_{nom}.png'
            pag.screenshot(path=str(desti), full_page=True)
            print(f'✓ {desti.name:38} {ruta:22} {què}')
        nav.close()


if __name__ == '__main__':
    main()
