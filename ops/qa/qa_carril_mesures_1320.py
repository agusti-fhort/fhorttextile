"""QA a pantalla del carril de mesures del model 1320 (Blusa KAYCE).

⚠️ CAP ESCRIPTURA: tot POST/PATCH/PUT/DELETE es respon localment amb l'eco del cos. El carril
és una superfície que ESCRIU AL DOMINI en obrir-se segons el mode, i l'Agus hi és treballant
ara mateix: la QA no hi pot deixar rastre.
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


def main():
    if not TOKEN:
        sys.exit('Falta FTT_QA_TOKEN')
    OUT.mkdir(exist_ok=True)
    sess = requests.Session()
    escriptures = []

    def handler(route, request):
        url = request.url
        cami = url.split(BASE, 1)[-1].split('?')[0] if url.startswith(BASE) else url
        if cami.startswith('/api/'):
            if request.method != 'GET':
                escriptures.append(f'{request.method} {cami}')
                route.fulfill(status=200, body=request.post_data or '{}',
                              headers={'content-type': 'application/json'})
                return
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
        pag.goto(BASE + '/models/1320?tab=Mesures', wait_until='networkidle')
        pag.wait_for_timeout(3500)
        pag.screenshot(path=str(OUT / 'carril_00_taula.png'), full_page=True)

        # El NOM de la primera fila: ha de ser el canònic, no la llista del matcher.
        noms = pag.evaluate("""() => [...document.querySelectorAll('td')]
              .map(td => td.innerText.trim()).filter(t => t.length > 6 && t.length < 90).slice(0, 14)""")
        print('TEXTOS de la taula:', json.dumps(noms, ensure_ascii=False)[:700])

        # El cercador viu al mode d'edició. Les escriptures que aquest gest dispara queden
        # totes interceptades pel handler (v. la capçalera): no en surt cap.
        for etiqueta in ('Editar POM',):
            try:
                pag.locator(f'button:has-text("{etiqueta}")').first.click()
                pag.wait_for_timeout(2500)
            except Exception as e:
                print(f'  ⚠️ {etiqueta}: {e}')
        pag.screenshot(path=str(OUT / 'carril_00b_edicio.png'), full_page=True)

        # EL CERCADOR: escriure «F» (un sol caràcter) ha d'oferir el POM F.
        camp = pag.locator('input[placeholder]').filter(
            has_not=pag.locator('[disabled]'))
        n = camp.count()
        print(f'inputs amb placeholder: {n}')
        for i in range(n):
            ph = (camp.nth(i).get_attribute('placeholder') or '')
            print(f'   [{i}] {ph[:60]!r}')
        idx = int(os.environ.get('QA_INPUT', '-1'))
        if idx >= 0:
            camp.nth(idx).click()
            camp.nth(idx).fill('F')
            pag.wait_for_timeout(1400)
            pag.screenshot(path=str(OUT / 'carril_01_cerca_F.png'), full_page=True)
            llista = pag.evaluate("""() => {
                const c = [...document.body.querySelectorAll('div')]
                  .filter(d => d.style && d.style.position === 'fixed' && d.innerText.length > 3)
                return c.length ? c[c.length - 1].innerText.split('\\n').slice(0, 18) : []
            }""")
            print('DESPLEGABLE amb «F»:', json.dumps(llista, ensure_ascii=False))
        print('\nESCRIPTURES interceptades (cap ha sortit):', escriptures or 'cap')
        nav.close()


if __name__ == '__main__':
    main()
