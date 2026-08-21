"""H · LA TAULA DE MESURES DE TALLA BASE A LA FITXA TÈCNICA — captures + export PDF.

Patró de `qa_s45_captures.py`: el bundle surt de `frontend/dist` al DISC i l'API es proxya a
127.0.0.1:8001 amb el Host del tenant, o l'`auth_basic` d'nginx torna un 401 i la captura surt
en blanc (verd fals).

⚠️ AQUESTA QA ESCRIU: obrir l'editor pren el LOCK i inserir una taula dispara l'autosave
(debounce 2 s). S'obren `.ftt` que JA existeixen als dos models de banc, mai `/models/:id/fitxa`
(que resol-o-CREA i materialitza tasca).

    FTT_QA_TOKEN=… /tmp/qa-venv/bin/python qa_h_taula_base.py
"""
import mimetypes
import os
import pathlib

import requests
from playwright.sync_api import sync_playwright

REPO = pathlib.Path('/var/www/ftt-staging')
DIST = REPO / 'frontend' / 'dist'
OUT = REPO / 'ops' / 'qa' / 'captures' / 'h_taula_base'
BASE = 'https://staging.fhorttextile.tech'
VIU = 'http://127.0.0.1:8001'
HOST_TENANT = 'staging.fhorttextile.tech'
TOKEN = os.environ['FTT_QA_TOKEN']

# (etiqueta, model, fitxer .ftt, quantes peces)
CASOS = [('1383_una_peca', 1383, 873, 1), ('1379_multipeca', 1379, 865, 2)]

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
                data=request.post_data_buffer, timeout=60)
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
    ctx = nav.new_context(viewport={'width': 1700, 'height': 1100}, accept_downloads=True)
    pag = ctx.new_page()
    pag.on('pageerror', lambda e: errors.append(str(e)))
    pag.route('**/*', handler)
    pag.goto(BASE + '/', wait_until='domcontentloaded')
    pag.evaluate("([t]) => { localStorage.setItem('access_token', t);"
                 " localStorage.setItem('fhort.lang', 'ca') }", [TOKEN])

    for nom, model, fitxer, npeces in CASOS:
        print(f'\n── {nom} · model {model} · .ftt {fitxer}')
        pag.goto(f'{BASE}/models/{model}/ftt/{fitxer}', wait_until='networkidle')
        pag.wait_for_timeout(4000)
        pag.screenshot(path=str(OUT / f'{nom}_0_editor.png'), full_page=False)

        # El contenidor «Taules» neix tancat.
        try:
            pag.get_by_text('Taules', exact=True).first.click()
            pag.wait_for_timeout(900)
        except Exception as e:
            print(f'   ⚠ obrir Taules: {e}')
        pag.screenshot(path=str(OUT / f'{nom}_1_panell.png'), full_page=False)

        # ORDRE DEL PANELL: la base ha de sortir PRIMERA de cada grup de peça.
        etiquetes = pag.evaluate(
            "() => [...document.querySelectorAll('button')].map(b => b.innerText.trim())"
            ".filter(x => ['Mesures talla base','Fitting','Escalat','Size set',"
            "'Notes del fitting'].includes(x))")
        print(f'   ordre al panell: {etiquetes}')

        botons = pag.get_by_role('button', name='Mesures talla base')
        print(f'   entrades «Mesures talla base»: {botons.count()} (esperades {npeces})')
        for i in range(botons.count()):
            botons.nth(i).click()
            pag.wait_for_timeout(2500)
        pag.wait_for_timeout(2500)
        pag.screenshot(path=str(OUT / f'{nom}_2_inserida.png'), full_page=False)

        # LA TAULA AL DOCUMENT, tal com el renderitzador la construeix.
        info = pag.evaluate("""() => {
          const t = window.__fttDebugTaules; return t ? t() : null }""")
        if info:
            print('   debug:', info)

        # EXPORT PDF — el mateix `renderPageToDataURL` que pinta el llenç.
        try:
            with pag.expect_download(timeout=90000) as dl:
                pag.get_by_role('button', name='Exportar PDF').first.click()
            d = dl.value
            desti = OUT / f'{nom}.pdf'
            d.save_as(str(desti))
            print(f'   ✓ PDF → {desti.name} ({desti.stat().st_size} bytes)')
        except Exception as e:
            print(f'   ⚠ export PDF: {e}')
        pag.wait_for_timeout(1500)

    nav.close()

print('\nerrors de pàgina:', errors or 'cap')
