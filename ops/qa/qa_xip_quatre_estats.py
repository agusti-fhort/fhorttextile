"""Verificació dels TRES ESTATS del xip commutable (`ui/Xip`) + l'anell de focus de TECLAT.

QA Agus 09/08. Tres superfícies: Size Library (restriccions d'un run), Graduació (capes de
relació d'un joc) i Garment Types (que NO usa aquest control i serveix de contrast).

⚠️ **AIXÒ ÉS UNA MESURA, NO UNA MIRADA.** El defecte que va motivar-ho —el filet fosc en
DESCLICAR— no es distingeix d'un anell de focus a ull nu, i durant una estona la hipòtesi va
ser justament aquesta. El que el va separar va ser llegir `getComputedStyle` als quatre
moments: `outline` era `none` sempre, i el que canviava era `border-color`. Per això aquest
guió imprimeix els valors calculats i no només fa captures.

Cap escriptura: tot POST/PATCH/PUT/DELETE es respon localment amb l'eco del cos, o sigui que
la QA NO toca el domini. El bundle surt de `frontend/dist` i els GET de `/api/` van al gunicorn
viu (127.0.0.1:8001) amb el `Host` del tenant — v. la memòria de l'e2e de staging.

    FTT_QA_TOKEN=... QA_OBRE='button:has-text("Editar")||button:has-text("Relacions")' \
        venv/bin/python ops/qa/qa_xip_quatre_estats.py
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
HOST_TENANT = 'staging.fhorttextile.tech'
TOKEN = os.environ.get('FTT_QA_TOKEN', '')

SONDA = """([sel, i]) => {
  const b = document.querySelectorAll(sel)[i]
  if (!b) return null
  const s = getComputedStyle(b)
  return {t: b.textContent.trim().slice(0,20), on: b.getAttribute('aria-pressed'),
          foc: b === document.activeElement, fv: b.matches(':focus-visible'),
          outline: s.outlineStyle + ' ' + s.outlineWidth + ' ' + s.outlineColor,
          vora: s.borderWidth + ' ' + s.borderColor, fons: s.backgroundColor, tinta: s.color}
}"""


def handler_factory(sess):
    def handler(route, request):
        url = request.url
        cami = url.split(BASE, 1)[-1].split('?')[0] if url.startswith(BASE) else url
        if cami.startswith('/api/'):
            if request.method in ('PATCH', 'PUT', 'POST', 'DELETE'):
                route.fulfill(status=200, body=request.post_data or '{}',
                              headers={'content-type': 'application/json'})
                return
            try:
                r = sess.request(request.method, VIU + url.split(BASE, 1)[-1],
                                 headers={'Host': HOST_TENANT, 'Authorization': f'Bearer {TOKEN}'},
                                 timeout=30)
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
    return handler


def prova(pag, titol, ruta, obre, salta, prefix):
    print(f'\n########## {titol}  ({ruta})')
    pag.goto(BASE + ruta, wait_until='networkidle')
    pag.wait_for_timeout(2200)
    for sel in obre:
        try:
            pag.locator(sel).first.click()
            pag.wait_for_timeout(1500)
        except Exception as e:
            print(f'  ⚠️ no s\'ha pogut obrir amb {sel}: {e}')
    S = 'button[aria-pressed]'
    n = pag.locator(S).count()
    idx = next((i for i in range(salta, n)
                if pag.locator(S).nth(i).get_attribute('aria-pressed') == 'false'
                and pag.locator(S).nth(i).is_enabled()), None)
    if idx is None:
        print(f'  ⚠️ cap xip commutable ({n} amb aria-pressed)')
        return
    xip = pag.locator(S).nth(idx)
    print('  REPÒS      :', pag.evaluate(SONDA, [S, idx]))
    xip.hover(); pag.wait_for_timeout(350)
    print('  HOVER      :', pag.evaluate(SONDA, [S, idx]))
    xip.click(); pag.wait_for_timeout(900)
    print('  SELECCIONAT:', pag.evaluate(SONDA, [S, idx]))
    pag.screenshot(path=str(OUT / f'{prefix}_seleccionat.png'), full_page=True)
    xip.click(); pag.wait_for_timeout(900)
    pag.mouse.move(4, 4); pag.wait_for_timeout(300)
    d = pag.evaluate(SONDA, [S, idx])
    print('  DESCLICAT  :', d)
    pag.screenshot(path=str(OUT / f'{prefix}_desclicat.png'), full_page=True)
    # FOCUS DE TECLAT: l'anell d'or ha de sortir (i només aquí).
    pag.evaluate("([s,i]) => document.querySelectorAll(s)[i].blur()", [S, idx])
    pag.keyboard.press('Tab')
    pag.evaluate("([s,i]) => document.querySelectorAll(s)[i].focus({focusVisible:true})", [S, idx])
    pag.wait_for_timeout(300)
    print('  FOCUS TECLA:', pag.evaluate(SONDA, [S, idx]))
    caixa = xip.bounding_box()
    if caixa:
        pag.screenshot(path=str(OUT / f'{prefix}_zoom.png'), clip={
            'x': max(0, caixa['x'] - 30), 'y': max(0, caixa['y'] - 25),
            'width': min(600, caixa['width'] + 300), 'height': caixa['height'] + 50})


def main():
    if not TOKEN:
        sys.exit('Falta FTT_QA_TOKEN')
    OUT.mkdir(exist_ok=True)
    sess = requests.Session()
    with sync_playwright() as p:
        nav = p.chromium.launch()
        ctx = nav.new_context(viewport={'width': 1600, 'height': 1000})
        pag = ctx.new_page()
        pag.route('**/*', handler_factory(sess))
        pag.goto(BASE + '/', wait_until='domcontentloaded')
        pag.evaluate("([t]) => { localStorage.setItem('access_token', t);"
                     " localStorage.setItem('fhort.lang', 'ca') }", [TOKEN])
        prova(pag, 'SIZE LIBRARY · restriccions', '/size-library', [], 2, 'v_sizelib')
        prova(pag, 'GRADUACIÓ · capes de relació', '/poms/grading',
              [s for s in os.environ.get('QA_OBRE', '').split('||') if s], 0, 'v_grading')
        prova(pag, 'GARMENT TYPES · pills de grup', '/garment-types', [], 0, 'v_gtypes')
        nav.close()


if __name__ == '__main__':
    main()
