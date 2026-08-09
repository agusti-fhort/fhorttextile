"""DIFF DE LAYOUT · el mateix bundle abans i després d'un canvi al bastiment.

**PER QUÈ EXISTEIX.** `qa_auditoria_computats.py` mesura COLORS i MIDES DE LLETRA; `qa_bidireccional`
compara elements concrets contra la maqueta. **Cap de les dues veu si una pàgina s'ha mogut.** Un
canvi al `<main>` del Shell —passar-lo a `display: flex`, per exemple— toca les 27 rutes alhora i
no canvia cap color ni cap mida de lletra: si desplacés el contingut, les tres eines donarien verd.

Aquest script pren una FOTO GEOMÈTRICA de cada ruta (alçada del document, nombre d'elements
visibles, i la caixa dels primers fills del `<main>`), la desa a un JSON, i la compara amb una
foto anterior. No sap què és «correcte»: sap dir **què s'ha mogut**, que és exactament el que
falta per poder afirmar «zero risc» en comptes de deduir-ho.

    # 1) abans del canvi, amb el bundle vell:
    FTT_QA_TOKEN=… /tmp/qa-venv/bin/python ops/qa/qa_diff_layout.py abans.json
    # 2) fas el canvi + npm run build
    # 3) després:
    FTT_QA_TOKEN=… /tmp/qa-venv/bin/python ops/qa/qa_diff_layout.py despres.json abans.json
"""
import json
import mimetypes
import os
import pathlib
import sys

import requests
from playwright.sync_api import sync_playwright

REPO = pathlib.Path(__file__).resolve().parents[2]
DIST = REPO / 'frontend' / 'dist'
BASE = 'https://staging.fhorttextile.tech'
VIU = 'http://127.0.0.1:8001'
HOST_TENANT = os.environ.get('FTT_QA_HOST', 'fhorttextile.tech')
TOKEN = os.environ.get('FTT_QA_TOKEN', '')

sys.path.insert(0, str(REPO / 'ops' / 'qa'))
from qa_auditoria_computats import PANTALLES  # noqa: E402  (la MATEIXA llista, mai una còpia)

#: Quant es pot moure una cosa sense que sigui un moviment. Mig píxel: per sota d'això és
#: arrodoniment de subpíxel del navegador, no layout.
TOL = 0.5

JS = """
() => {
  const main = document.querySelector('main');
  if (!main) return { falta: 'main' };
  const fills = [...main.children].slice(0, 6).map((n, i) => {
    const r = n.getBoundingClientRect();
    return { i, tag: n.tagName.toLowerCase(),
             top: Math.round(r.top * 10) / 10, left: Math.round(r.left * 10) / 10,
             w: Math.round(r.width * 10) / 10, h: Math.round(r.height * 10) / 10 };
  });
  const rM = main.getBoundingClientRect();
  return {
    doc: document.documentElement.scrollHeight,
    nodes: document.querySelectorAll('body *').length,
    main: { top: Math.round(rM.top * 10) / 10, w: Math.round(rM.width * 10) / 10,
            h: Math.round(rM.height * 10) / 10 },
    fills,
  };
}
"""


def main():
    if not TOKEN:
        sys.exit('Falta FTT_QA_TOKEN.')
    sortida = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path('layout.json')
    anterior = json.loads(pathlib.Path(sys.argv[2]).read_text()) if len(sys.argv) > 2 else None
    sess = requests.Session()

    r = sess.get(VIU + '/api/v1/me/', headers={'Host': HOST_TENANT,
                                               'Authorization': f'Bearer {TOKEN}'}, timeout=15)
    if r.status_code != 200:
        sys.exit(f'🛑 LA SESSIÓ NO ÉS VÀLIDA: /me/ → {r.status_code} (v. la 2a tapadora).')

    def handler(route, request):
        url = request.url
        cami = url.split(BASE, 1)[-1].split('?')[0] if url.startswith(BASE) else url
        if cami.startswith('/api/'):
            try:
                rr = sess.request(request.method, VIU + url.split(BASE, 1)[-1],
                                  headers={'Host': HOST_TENANT, 'Authorization': f'Bearer {TOKEN}',
                                           'Content-Type': 'application/json'},
                                  data=request.post_data_buffer, timeout=30)
                route.fulfill(status=rr.status_code, body=rr.content,
                              headers={'content-type': rr.headers.get('content-type', 'application/json')})
            except Exception as e:
                route.fulfill(status=502, body=f'{{"error":"{e}"}}',
                              headers={'content-type': 'application/json'})
            return
        f = DIST / cami.lstrip('/')
        if not f.is_file():
            f = DIST / 'index.html'
        route.fulfill(status=200, body=f.read_bytes(),
                      headers={'content-type': mimetypes.guess_type(f.name)[0] or 'text/html'})

    foto, moguts = {}, []
    with sync_playwright() as p:
        nav = p.chromium.launch()
        ctx = nav.new_context(viewport={'width': 1600, 'height': 900})
        pag = ctx.new_page()
        pag.route('**/*', handler)
        pag.goto(BASE + '/', wait_until='domcontentloaded')
        pag.evaluate("([t]) => { localStorage.setItem('access_token', t);"
                     " localStorage.setItem('fhort.lang','ca') }", [TOKEN])
        # La tupla de `PANTALLES` té 2 o 3 elements: el tercer és el SENYAL de pantalla que la
        # sessió de patrons hi va afegir (opcional). Aquí només calen els dos primers, però es
        # desempaqueta amb estrella perquè el dia que en tingui quatre això no torni a petar.
        for nom, ruta, *_ in PANTALLES:
            pag.goto(BASE + ruta, wait_until='networkidle')
            pag.wait_for_timeout(1200)
            foto[nom] = pag.evaluate(JS)
        nav.close()

    sortida.write_text(json.dumps(foto, indent=1, ensure_ascii=False))
    print(f'Foto de {len(foto)} rutes → {sortida}')

    if anterior is None:
        return
    print('\n── DIFERÈNCIES ────────────────────────────────────────────────')
    for nom, ara in foto.items():
        abans = anterior.get(nom)
        if not abans:
            print(f'  · {nom}: NOU (no era a la foto anterior)')
            continue
        # Una ruta FORA del Shell no té `<main>`: no és comparable, i dir-ho és més honest que
        # petar o que comptar-la com a «sense moviment».
        if ara.get('falta') or abans.get('falta'):
            print(f"  ⚠️  {nom}: sense `<main>` (ruta fora del Shell) — no comparable")
            continue
        linies = []
        if abs(ara.get('doc', 0) - abans.get('doc', 0)) > TOL:
            linies.append(f"alçada del document {abans['doc']} → {ara['doc']}")
        if ara.get('nodes') != abans.get('nodes'):
            linies.append(f"nodes {abans['nodes']} → {ara['nodes']}")
        for k in ('top', 'w', 'h'):
            if abs(ara['main'][k] - abans['main'][k]) > TOL:
                linies.append(f"main.{k} {abans['main'][k]} → {ara['main'][k]}")
        for a, b in zip(abans.get('fills', []), ara.get('fills', [])):
            for k in ('top', 'left', 'w', 'h'):
                if abs(a[k] - b[k]) > TOL:
                    linies.append(f"fill[{a['i']}] {a['tag']}.{k} {a[k]} → {b[k]}")
        if linies:
            moguts.append(nom)
            print(f'  🔴 {nom}')
            for x in linies:
                print(f'       {x}')
    print(f'\n──────── {len(moguts)} rutes amb moviment (de {len(foto)}) ────────')
    sys.exit(1 if moguts else 0)


main()
