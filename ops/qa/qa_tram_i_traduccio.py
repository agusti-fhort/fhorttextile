"""TRAM ⓘ — la ⓘ parlant, a pantalla.

Contra la SPA construïda (`frontend/dist`) i el backend viu de staging, amb el patró de la casa:
`dist` servit pel `route`, l'API en proxy cap a gunicorn amb Bearer, i **cap escriptura** —tot
POST/PATCH/PUT/DELETE es respon localment amb l'eco del cos. La taula de mesures escriu al domini
en obrir-se segons el mode i aquesta QA no hi ha de deixar rastre.

Què mira, a banda de la captura:
  · quantes vegades es crida `/api/v1/translate/pom/` per pintar la pantalla (ha de ser POC),
  · quants POMs porta cada crida (ha de ser MOLTS: el lot),
  · quantes en calen en TORNAR a la pantalla (`goto` és una RECÀRREGA sencera: la cache de
    sessió viu en memòria i mor amb la pàgina, o sigui que aquí se n'espera una altra — el que
    NO ha de passar és que en calguin més d'una),
  · i que la ⓘ, oberta, digui una cosa DIFERENT del nom que ja es llegeix.

    FTT_QA_TOKEN=... /tmp/qa-venv/bin/python ops/qa/qa_tram_i_traduccio.py <model_id>
"""
import json
import mimetypes
import os
import pathlib
import sys

import requests
from playwright.sync_api import sync_playwright

DIST = pathlib.Path(__file__).resolve().parents[2] / 'frontend' / 'dist'
OUT = pathlib.Path(__file__).resolve().parent / 'captures'
BASE = 'https://staging.fhorttextile.tech'
VIU = 'http://127.0.0.1:8001'
TOKEN = os.environ.get('FTT_QA_TOKEN', '')
MODEL = sys.argv[1] if len(sys.argv) > 1 else '1320'


def main():
    if not TOKEN:
        sys.exit('Falta FTT_QA_TOKEN')
    OUT.mkdir(exist_ok=True)
    sess = requests.Session()
    escriptures = []
    crides_traduccio = []

    def handler(route, request):
        url = request.url
        cami = url.split(BASE, 1)[-1].split('?')[0] if url.startswith(BASE) else url
        if cami.startswith('/api/'):
            if request.method != 'GET':
                escriptures.append(f'{request.method} {cami}')
                route.fulfill(status=200, body=request.post_data or '{}',
                              headers={'content-type': 'application/json'})
                return
            if cami == '/api/v1/translate/pom/':
                q = url.split('?', 1)[1] if '?' in url else ''
                ids = [p for p in q.split('&') if p.startswith('pom_ids=')]
                n = len(ids[0].split('=', 1)[1].split(',')) if ids else 0
                crides_traduccio.append({'n_poms': n, 'q': q})
            try:
                r = sess.get(VIU + url.split(BASE, 1)[-1],
                             headers={'Host': 'staging.fhorttextile.tech',
                                      'Authorization': f'Bearer {TOKEN}'}, timeout=30)
                route.fulfill(status=r.status_code, body=r.content,
                              headers={'content-type': r.headers.get('content-type', 'application/json')})
            except Exception as e:
                route.fulfill(status=502, body=json.dumps({'error': str(e)}),
                              headers={'content-type': 'application/json'})
            return
        f = DIST / cami.lstrip('/')
        if not f.is_file():
            f = DIST / 'index.html'
        route.fulfill(status=200, body=f.read_bytes(),
                      headers={'content-type': mimetypes.guess_type(f.name)[0] or 'text/html'})

    with sync_playwright() as p:
        nav = p.chromium.launch()
        ctx = nav.new_context(viewport={'width': 1700, 'height': 1100})
        pag = ctx.new_page()
        pag.route('**/*', handler)
        pag.goto(BASE + '/', wait_until='domcontentloaded')
        pag.evaluate("([t]) => { localStorage.setItem('access_token', t);"
                     " localStorage.setItem('fhort.lang', 'ca') }", [TOKEN])
        pag.goto(f'{BASE}/models/{MODEL}?tab=Mesures', wait_until='networkidle')
        pag.wait_for_timeout(4000)
        pag.screenshot(path=str(OUT / 'tram_i_00_taula.png'), full_page=True)

        infos = pag.locator('button[data-info-traduccio="1"]')
        n_info = infos.count()
        print(f'ⓘ a la taula: {n_info}')

        text_info = None
        if n_info:
            infos.first.click()
            pag.wait_for_timeout(600)
            pag.screenshot(path=str(OUT / 'tram_i_01_info_oberta.png'), full_page=True)
            tip = pag.locator('[role="tooltip"]')
            if tip.count():
                text_info = tip.first.inner_text().strip()
            # I la fila on viu, retallada: la ⓘ és de 12px i a pàgina sencera no es llegeix.
            fila = infos.first.locator('xpath=ancestor::tr[1]')
            try:
                fila.screenshot(path=str(OUT / 'tram_i_02_fila.png'))
            except Exception as e:
                print(f'  ⚠️ retall de fila: {e}')
        print(f'TEXT de la ⓘ oberta: {text_info!r}')

        crides_1a = len(crides_traduccio)
        # ⚠️ `goto` RECARREGA la pàgina: la cache de sessió (de mòdul) es perd i se n'espera UNA
        # de nova, servida ja per la cache del SERVIDOR sense tocar el proveïdor. Provar la cache
        # de sessió de debò vol navegar per dins de la SPA; això ja ho cobreix el banc de
        # `traduccioPomCua.test.js`, que és on la regla viu.
        pag.goto(f'{BASE}/models/{MODEL}?tab=Resum', wait_until='networkidle')
        pag.wait_for_timeout(1500)
        pag.goto(f'{BASE}/models/{MODEL}?tab=Mesures', wait_until='networkidle')
        pag.wait_for_timeout(3000)
        crides_2a = len(crides_traduccio) - crides_1a

        print(json.dumps({
            'crides_translate_1a_visita': crides_1a,
            'poms_per_crida': [c['n_poms'] for c in crides_traduccio[:crides_1a]],
            'crides_translate_2a_visita': crides_2a,
            'escriptures_bloquejades': escriptures,
        }, ensure_ascii=False, indent=2))
        nav.close()

    print('\nCaptures a', OUT)


if __name__ == '__main__':
    main()
