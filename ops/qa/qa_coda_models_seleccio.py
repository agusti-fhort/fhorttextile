"""CODA /models · EL GEST DE CONJUNT, MESURAT (no descrit).

Agus, mirant `/models`, va demanar dues coses:

  1 · el checkbox «selecciona-ho tot» va **A LA CAPÇALERA** de la taula (columna `chk`, com la
      graella canònica) — fora la línia solta de sota;
  2 · **recuperar el component existent de selecció ampliada** («els N de la pàgina o tots els M
      del filtre?») i muntar-lo, sense fer-ne cap de nou.

Els dos punts són el mateix defecte vist per dues cares: el gest vivia SOTA la taula i la seva
resposta —la banda de conjunt, que ja existia des de C2b— es pintava A SOBRE, a set-centes
píxels de distància; i al tenant on Agus mira només hi ha un model, de manera que la banda no
apareixia MAI. Un control i la seva conseqüència separats així no són una conversa.

QUÈ MESURA (contra el bundle i el servei VIU, sense escriure res al domini — marcar caselles
no és cap crida):

  A · la capçalera de la columna `chk` porta el control, i és el PRIMER `th`;
  B · no queda CAP checkbox de la llista fora de la taula (la línia solta és morta);
  C · el control té TRES estats: una fila triada el deixa INDETERMINAT, no buit;
  D · prémer-lo tria tota la pàgina **i la banda de conjunt apareix**, amb la pregunta sencera
      («N d'aquesta pàgina» + «Seleccionar els M del filtre»);
  E · la banda és ADJACENT a la taula: el gest i la resposta a la mateixa mirada;
  F · acceptar el conjunt canvia la banda («M seleccionats del filtre» + «Desmarca-ho tot»), i
      desmarcar-ho torna la pantalla a zero;
  G · quan el filtre CAP en una pàgina, la banda no apareix — no hi ha cap pregunta a fer.

Els literals NO s'escriuen aquí: es llegeixen de `frontend/src/i18n/ca.json`, que és qui els
mana. Un text copiat a mà a l'arnès deixa de casar el dia que algú el retoca, i llavors el que
falla és la mesura, no la pantalla.

    FTT_QA_TOKEN=… FTT_QA_HOST=los.fhorttextile.tech /tmp/qa-venv/bin/python \
        ops/qa/qa_coda_models_seleccio.py
"""
import json
import mimetypes
import os
import pathlib
import re
import sys

import requests
from playwright.sync_api import sync_playwright

REPO = pathlib.Path(__file__).resolve().parents[2]
# Mateix motiu que a `qa_auditoria_computats.py`: aquí `npm run build` DESPLEGA, i mesurar un
# canvi propi no pot obligar a publicar el codi a mig fer d'una altra sessió.
DIST = pathlib.Path(os.environ.get('FTT_QA_DIST') or (REPO / 'frontend' / 'dist'))
I18N = REPO / 'frontend' / 'src' / 'i18n' / 'ca.json'
BASE = 'https://staging.fhorttextile.tech'
VIU = 'http://127.0.0.1:8001'
HOST_TENANT = os.environ.get('FTT_QA_HOST', 'fhorttextile.tech')
TOKEN = os.environ.get('FTT_QA_TOKEN', '')
PAGE_SIZE = 25   # el de `Models.jsx`

ko = 0


def comprova(què, condicio, detall=''):
    global ko
    if condicio:
        print(f'  ✓ {què}')
    else:
        ko += 1
        print(f'  ✗ {què}   {detall}')


def literal(clau, **vars):
    """El text tal com el mana `ca.json`, amb les seves interpolacions resoltes."""
    node = json.loads(I18N.read_text())
    for tros in clau.split('.'):
        node = node[tros]
    for k, v in vars.items():
        node = node.replace('{{' + k + '}}', str(v))
    return node


def main():
    global ko
    if not TOKEN:
        sys.exit('Falta FTT_QA_TOKEN.')
    if not DIST.exists():
        sys.exit(f'No hi ha bundle a {DIST} — cal construir-lo.')
    sess = requests.Session()

    cens = sess.get(VIU + '/api/v1/models/?page_size=1',
                    headers={'Host': HOST_TENANT, 'Authorization': f'Bearer {TOKEN}'},
                    timeout=30).json()['count']
    n_pagina = min(cens, PAGE_SIZE)
    hi_ha_pregunta = cens > PAGE_SIZE
    print(f'\nTENANT {HOST_TENANT} · {cens} models · {n_pagina} a la pàgina · '
          f'{"HI HA" if hi_ha_pregunta else "NO hi ha"} pregunta de conjunt a fer')

    def handler(route, request):
        url = request.url
        cami = url.split(BASE, 1)[-1].split('?')[0] if url.startswith(BASE) else url
        if cami.startswith('/api/'):
            try:
                r = sess.request(request.method, VIU + url.split(BASE, 1)[-1],
                                 headers={'Host': HOST_TENANT, 'Authorization': f'Bearer {TOKEN}',
                                          'Content-Type': 'application/json'},
                                 data=request.post_data_buffer, timeout=30)
                route.fulfill(status=r.status_code, body=r.content,
                              headers={'content-type': r.headers.get('content-type', 'application/json')})
            except Exception as e:
                route.fulfill(status=502, body=f'{{"error":"{e}"}}',
                              headers={'content-type': 'application/json'})
            return
        f = DIST / cami.lstrip('/')
        if not f.is_file():
            f = DIST / 'index.html'
        route.fulfill(status=200, body=f.read_bytes(),
                      headers={'content-type': mimetypes.guess_type(f.name)[0] or 'text/html'})

    with sync_playwright() as p:
        nav = p.chromium.launch()
        pag = nav.new_context(viewport={'width': 1600, 'height': 1200}).new_page()
        pag.route('**/*', handler)
        pag.goto(BASE + '/', wait_until='domcontentloaded')
        pag.evaluate("([t]) => { localStorage.setItem('access_token', t);"
                     " localStorage.setItem('fhort.lang','ca') }", [TOKEN])
        pag.goto(BASE + '/models', wait_until='networkidle')
        pag.wait_for_timeout(2000)

        capChk = pag.locator('table thead th:first-child input[type="checkbox"]')
        filaChk = pag.locator('table tbody tr td:first-child input[type="checkbox"]')

        # ── A · el control és a la CAPÇALERA de la columna chk ────────────────────────
        print('\nA · EL GEST VIU A LA CAPÇALERA DE LA SEVA COLUMNA')
        comprova('el primer `th` de la taula porta el checkbox de conjunt', capChk.count() == 1,
                 f'n={capChk.count()}')
        comprova(f'hi ha una casella per fila ({n_pagina} files)', filaChk.count() == n_pagina,
                 f'n={filaChk.count()}')
        if capChk.count():
            # El de capçalera i el de fila són EL MATEIX control: si divergeixen, la columna
            # ensenya dos objectes diferents fent la mateixa cosa.
            mida = capChk.evaluate('el => { const s = getComputedStyle(el);'
                                   ' return [s.width, s.height, s.accentColor] }')
            midaF = filaChk.first.evaluate('el => { const s = getComputedStyle(el);'
                                           ' return [s.width, s.height, s.accentColor] }')
            comprova('capçalera i fila són el MATEIX control (mida i accent)', mida == midaF,
                     f'cap={mida} fila={midaF}')
            comprova('el seu accent és --gold (#c27a2a)',
                     mida[2] == 'rgb(194, 122, 42)', mida[2])

        # ── B · la línia solta de sota és MORTA ───────────────────────────────────────
        print('\nB · CAP CHECKBOX DE LA LLISTA FORA DE LA TAULA')
        forats = pag.evaluate(
            "() => [...document.querySelectorAll('main input[type=checkbox]')]"
            "        .filter(el => !el.closest('table'))"
            "        .map(el => (el.closest('label') || el.parentElement).innerText.trim())")
        comprova('no queda cap casella de selecció fora de la taula', forats == [], str(forats))

        # ── C · el tercer estat ───────────────────────────────────────────────────────
        print('\nC · EL CONTROL TÉ TRES ESTATS, NO DOS')
        estat = lambda: capChk.evaluate('el => [el.checked, el.indeterminate]')
        comprova('de partida: buit i no indeterminat', estat() == [False, False], str(estat()))
        filaChk.first.click()
        pag.wait_for_timeout(300)
        if n_pagina > 1:
            comprova('amb UNA fila triada passa a INDETERMINAT (no buit, no ple)',
                     estat() == [False, True], str(estat()))
        else:
            # Amb una sola fila, triar-la ÉS triar la pàgina: aquí el tercer estat no existeix,
            # i exigir-l'hi seria demanar a la pantalla que digués una cosa falsa.
            comprova('amb la ÚNICA fila triada la capçalera queda PLENA (no hi ha parcial)',
                     estat() == [True, False], str(estat()))
        filaChk.first.click()
        pag.wait_for_timeout(300)
        comprova('en desmarcar-la torna a buit', estat() == [False, False], str(estat()))

        # ── D · el gest i la seva resposta ────────────────────────────────────────────
        print('\nD · PRÉMER-LO TRIA LA PÀGINA — I OBRE LA PREGUNTA')
        banda = pag.locator(f'div:has(> button:text-is("{literal("models_list.clear_selection")}")),'
                            f'div:has(> button:text-is("{literal("models_list.select_all_filter", n=cens)}"))')
        comprova('abans del gest no hi ha banda de conjunt', banda.count() == 0, f'n={banda.count()}')
        capChk.click()
        pag.wait_for_timeout(500)
        comprova('la capçalera queda PLENA', estat() == [True, False], str(estat()))
        triades = filaChk.evaluate_all('els => els.filter(e => e.checked).length')
        comprova(f'les {n_pagina} files de la pàgina queden triades', triades == n_pagina, f'n={triades}')

        if not hi_ha_pregunta:
            # ── G · sense pregunta, cap banda ─────────────────────────────────────────
            print('\nG · EL FILTRE CAP EN UNA PÀGINA → NO HI HA RES A PREGUNTAR')
            comprova('la banda de conjunt NO apareix', banda.count() == 0, f'n={banda.count()}')
            nav.close()
            print(f'\n──────── {ko} comprovacions fallides ────────')
            sys.exit(1 if ko else 0)

        comprova('LA BANDA DE SELECCIÓ AMPLIADA APAREIX', banda.count() == 1, f'n={banda.count()}')
        if banda.count() != 1:
            nav.close()
            print(f'\n──────── {ko} comprovacions fallides ────────')
            sys.exit(1)
        txt = banda.inner_text()
        comprova('diu quants n\'hi ha D\'AQUESTA PÀGINA',
                 literal('models_list.selected_page', n=n_pagina) in txt, repr(txt))
        comprova('i ofereix TOTS ELS DEL FILTRE',
                 literal('models_list.select_all_filter', n=cens) in txt, repr(txt))

        # ── E · adjacència: el gest i la resposta, a la mateixa mirada ────────────────
        print('\nE · LA RESPOSTA ÉS AL COSTAT DEL GEST')
        forat = pag.evaluate(
            "([b]) => { const t = document.querySelector('table');"
            " return t.getBoundingClientRect().top - b.getBoundingClientRect().bottom }",
            [banda.element_handle()])
        comprova(f'la banda toca la taula ({forat:.0f}px de separació, ≤ 24)', forat <= 24,
                 f'{forat:.0f}px')

        # ── F · acceptar el conjunt, i desfer-lo ──────────────────────────────────────
        print('\nF · ACCEPTAR EL CONJUNT, I DESFER-LO')
        pag.locator(f'button:text-is("{literal("models_list.select_all_filter", n=cens)}")').click()
        pag.wait_for_timeout(500)
        txt = banda.inner_text()
        comprova(f'la banda passa a dir «tots els {cens} del filtre»',
                 literal('models_list.selected_all_filter', n=cens) in txt, repr(txt))
        comprova('i ofereix desmarcar-ho tot',
                 literal('models_list.clear_selection') in txt, repr(txt))
        comprova('la capçalera segueix PLENA', estat() == [True, False], str(estat()))
        # Excloure'n una: el conjunt és «tots MENYS aquests» → indeterminat, no buit.
        filaChk.first.click()
        pag.wait_for_timeout(400)
        comprova('excloure\'n una deixa la capçalera INDETERMINADA', estat() == [False, True],
                 str(estat()))
        comprova(f'i la banda descompta l\'exclosa ({cens - 1})',
                 literal('models_list.selected_all_filter', n=cens - 1) in banda.inner_text(),
                 repr(banda.inner_text()))
        pag.locator(f'button:text-is("{literal("models_list.clear_selection")}")').click()
        pag.wait_for_timeout(500)
        comprova('desmarcar-ho tot tanca la banda', banda.count() == 0, f'n={banda.count()}')
        comprova('i buida la capçalera', estat() == [False, False], str(estat()))
        triades = filaChk.evaluate_all('els => els.filter(e => e.checked).length')
        comprova('cap fila queda triada', triades == 0, f'n={triades}')

        nav.close()

    print(f'\n──────── {ko} comprovacions fallides ────────')
    sys.exit(1 if ko else 0)


if __name__ == '__main__':
    main()
