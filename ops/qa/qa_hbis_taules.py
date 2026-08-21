"""H-bis · LES CINC TAULES DE LA FITXA amb la columna de nomenclatura — captures + export PDF.

Ordre d'Agus del 21/08: LAYER · POM · NOM a totes, sense tolerància a la de base, i captures
de les quatre taules del 1383. El 1383 **no té cap sessió TANCADA** (159 Oberta, 158 Anul·lada),
o sigui que allà Fitting i Notes no tenen font i el panell les ha de mostrar TANCADES amb el
motiu: les seves captures surten dels models que sí que en tenen (1379 · sessió 155, i 1320 ·
sessió 152, que a més és l'únic del corpus amb àlies de client i per tant l'únic on es veu que
el codi imprès és el del CLIENT i no el de la casa).

Patró de `qa_h_taula_base.py`: el bundle surt de `frontend/dist` al DISC i l'API es proxya a
127.0.0.1:8001 amb el Host del tenant, o l'`auth_basic` d'nginx torna un 401 i la captura surt
en blanc (verd fals).

⚠️ AQUESTA QA ESCRIU: obrir l'editor pren el LOCK i inserir una taula dispara l'autosave
(debounce 2 s). S'obren `.ftt` que JA existeixen, mai `/models/:id/fitxa` (que resol-o-CREA i
materialitza tasca).

    FTT_QA_TOKEN=… /tmp/qa-venv/bin/python ops/qa/qa_hbis_taules.py
"""
import mimetypes
import os
import pathlib
import subprocess

import requests
from playwright.sync_api import sync_playwright

REPO = pathlib.Path('/var/www/ftt-staging')
DIST = REPO / 'frontend' / 'dist'
OUT = REPO / 'ops' / 'qa' / 'captures' / 'hbis_taules'
BASE = 'https://staging.fhorttextile.tech'
VIU = 'http://127.0.0.1:8001'
HOST_TENANT = 'staging.fhorttextile.tech'
TOKEN = os.environ['FTT_QA_TOKEN']

TOTES = ['Mesures talla base', 'Fitting', 'Escalat', 'Size set', 'Notes del fitting']
# (etiqueta, model, fitxer .ftt, taules que hi ha d'haver OBERTES)
# ⚠️ CAP dels vuit `.ftt` del 1383 (866-873) és al DISC —només l'export
# `TRV-SS27-0001_fitxa_v1.pdf`—, o sigui que l'editor l'obre BUIT i les taules s'hi insereixen
# sobre un document nou. Les captures són igual de vàlides (el que es mira és la taula), però
# no és un round-trip: v. el cens obert de l'acta.
# El 1320 obre el 770 i NO el 771: aquell és el fixture de regressió dels `kind` retirats que
# H va deixar, i inserir-hi res el deixaria de ser.
CASOS = [
    ('1383', 1383, 873, ['Mesures talla base', 'Escalat', 'Size set']),
    ('1379', 1379, 865, TOTES),
    ('1320', 1320, 770, TOTES),
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

    for nom, model, fitxer, obertes in CASOS:
        print(f'\n── {nom} · model {model} · .ftt {fitxer}')
        pag.goto(f'{BASE}/models/{model}/ftt/{fitxer}', wait_until='networkidle')
        pag.wait_for_timeout(4000)

        try:
            pag.get_by_text('Taules', exact=True).first.click()
            pag.wait_for_timeout(900)
        except Exception as e:
            print(f'   ⚠ obrir Taules: {e}')
        pag.screenshot(path=str(OUT / f'{nom}_0_panell.png'), full_page=False)

        # LES PORTES: quines taules ofereix el panell i quines diu que no tenen font.
        estat = pag.evaluate(
            "([totes]) => [...document.querySelectorAll('button')]"
            ".filter(b => totes.includes(b.innerText.trim()))"
            ".map(b => [b.innerText.trim(), !b.disabled])", [TOTES])
        print(f'   panell: {estat}')
        tancades = sorted({e[0] for e in estat if not e[1]})
        esperades_tancades = sorted(set(TOTES) - set(obertes))
        print(f'   tancades: {tancades} · esperades: {esperades_tancades}'
              + ('  ✓' if tancades == esperades_tancades else '  ✗'))

        # INSERIR-LES TOTES, una a una i amb captura per taula.
        for taula in obertes:
            botons = pag.get_by_role('button', name=taula, exact=True)
            n = botons.count()
            print(f'   · «{taula}»: {n} entrada/es al panell')
            for i in range(n):
                try:
                    botons.nth(i).click()
                    pag.wait_for_timeout(2500)
                except Exception as e:
                    print(f'     ⚠ {e}')
            pag.wait_for_timeout(1500)
            clau = taula.lower().replace(' ', '_').replace('·', '')
            pag.screenshot(path=str(OUT / f'{nom}_1_{clau}.png'), full_page=False)

        # EXPORT PDF — el mateix `renderPageToDataURL` que pinta el llenç, i per tant
        # «PDF == live» hi és per CONSTRUCCIÓ; el que la captura verifica és que no peti.
        try:
            with pag.expect_download(timeout=120000) as dl:
                pag.get_by_role('button', name='Exportar PDF').first.click()
            d = dl.value
            desti = OUT / f'{nom}.pdf'
            d.save_as(str(desti))
            print(f'   ✓ PDF → {desti.name} ({desti.stat().st_size} bytes)')
            subprocess.run(['pdftoppm', '-png', '-r', '110', str(desti),
                            str(OUT / f'{nom}_pdf')], check=False)
        except Exception as e:
            print(f'   ⚠ export PDF: {e}')
        pag.wait_for_timeout(1500)

    nav.close()

print('\nerrors de pàgina:', errors or 'cap')
print(f'captures a {OUT}')
