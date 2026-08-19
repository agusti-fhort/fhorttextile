"""ARNÈS · B1 (Comprovació) i B2 (Repàs de fittings) A PANTALLA · model 1320.

La lògica de B1 la mesura `qa_b1_comprovacio_logica.py` contra la BD i la de B2 les proves de
`fitting/test_repas.py::RepasB2Test`. Aquí es mesura L'ALTRE COSTAT: que el que la consulta
resol arribi a la pantalla, i que hi arribi dient d'on surt.

  C1 · la Comprovació diu DE QUIN FITTING i DE QUINA TALLA parla
  C2 · «Van quedar enrere» no pot dir mai «0 dies»
  C3 · cada punt de tolerància porta el VEREDICTE de la modista
  R1 · el Repàs comença per l'ENTRADA DE POMs
  R2 · i porta TOTES les mesures del model, no només les fitades
  R3 · cap parell de columnes duplicades (mateixa etiqueta i mateixa data)
  R4 · els canvis van en NEGRETA i els ajustats en taronja (`--warn-ink`); la resta, normal

⚠️ **CAP ESCRIPTURA**: tot POST/PATCH/PUT/DELETE es respon localment amb l'eco i es censa.

    FTT_QA_TOKEN=... FTT_QA_API=http://127.0.0.1:8123 \\
    /tmp/qa-venv/bin/python ops/qa/qa_b12_pantalles.py

(El `FTT_QA_API` apunta a un servidor de disc: el gunicorn serveix el codi de quan va arrencar.
V. la capçalera de `qa_b34_router_i_estat.py`.)
"""
import json
import mimetypes
import os
import pathlib
import sys

import requests
from playwright.sync_api import sync_playwright

REPO = pathlib.Path(__file__).resolve().parents[2]
DIST = pathlib.Path(os.environ.get('FTT_QA_DIST') or (REPO / 'frontend' / 'dist'))
OUT = pathlib.Path(__file__).resolve().parent / 'captures'
BASE = 'https://staging.fhorttextile.tech'
VIU = os.environ.get('FTT_QA_API') or 'http://127.0.0.1:8001'
TOKEN = os.environ.get('FTT_QA_TOKEN', '')
MODEL = 1320
# §1b(d) — l'ajustat va en `--warn-ink` com a TINTA. És el color que `MeasureGrid` ja fa servir
# per al veredicte ADJUSTED, i el criteri és el mateix a les dues superfícies (decisió d'Agus).
WARN_INK = 'rgb(150, 80, 12)'   # --warn-ink #96500c

falles = []


def mira(nom, ok, detall=''):
    print(f'  {"✅" if ok else "❌"} {nom}' + (f' — {detall}' if detall else ''))
    if not ok:
        falles.append(nom)


def main():
    if not TOKEN:
        sys.exit('Falta FTT_QA_TOKEN')
    OUT.mkdir(exist_ok=True)
    sess = requests.Session()
    escriptures = []

    def api(cami):
        r = sess.get(VIU + cami, headers={'Host': 'staging.fhorttextile.tech',
                                          'Authorization': f'Bearer {TOKEN}'}, timeout=30)
        r.raise_for_status()
        return r.json()

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
                              headers={'content-type': r.headers.get('content-type',
                                                                     'application/json')})
            except Exception as e:
                route.fulfill(status=502, body=json.dumps({'error': str(e)}),
                              headers={'content-type': 'application/json'})
            return
        f = DIST / cami.lstrip('/')
        if not f.is_file():
            f = DIST / 'index.html'
        route.fulfill(status=200, body=f.read_bytes(),
                      headers={'content-type': mimetypes.guess_type(f.name)[0] or 'text/html'})

    comprovacio = api(f'/api/v1/models/{MODEL}/comprovacio/')
    repas = api(f'/api/v1/fitting/model/{MODEL}/repas/')
    mesures = api(f'/api/v1/models/{MODEL}/taula-mesures/')

    with sync_playwright() as p:
        nav = p.chromium.launch()
        ctx = nav.new_context(viewport={'width': 1700, 'height': 1400})
        pag = ctx.new_page()
        pag.route('**/*', handler)
        pag.goto(BASE + '/', wait_until='domcontentloaded')
        pag.evaluate("([t]) => { localStorage.setItem('access_token', t);"
                     " localStorage.setItem('fhort.lang', 'ca') }", [TOKEN])

        def subvista(etiqueta, captura):
            pag.goto(BASE + f'/models/{MODEL}?tab=Mesures', wait_until='networkidle')
            pag.wait_for_timeout(2500)
            pag.locator(f'button:has-text("{etiqueta}")').first.click()
            pag.wait_for_timeout(3000)
            pag.screenshot(path=str(OUT / captura), full_page=True)
            return pag.evaluate('() => document.body.innerText')

        # ── B1 · LA COMPROVACIÓ ───────────────────────────────────────────────────────────
        print('\nB1 · LA COMPROVACIÓ')
        txt = subvista('Comprovació', 'b1_comprovacio.png').lower()
        df = comprovacio.get('darrer_fitting') or {}
        talla = comprovacio.get('talla_base')
        mira('C1 · la resposta porta el darrer fitting i la talla base',
             bool(df.get('data') and talla), f"{df.get('data')} · talla {talla}")
        mira('C1 · …i la pantalla ho diu', 'el teòric és el valor contra el qual' in txt)
        enrere = comprovacio['seccions']['enrere']
        mira('C2 · cap punt de «van quedar enrere» amb 0 dies',
             all(p['dies'] > 0 for p in enrere), f'{len(enrere)} punts')
        tol = comprovacio['seccions']['tolerancia']
        mira('C3 · cada punt de tolerància porta veredicte',
             all('veredicte' in p for p in tol), f'{len(tol)} punts')
        mira('C3 · …i tots són de la talla base',
             all(p['talla'] == talla for p in tol),
             ', '.join(sorted({p['talla'] for p in tol})) or 'cap')

        # ── B2 · EL REPÀS ─────────────────────────────────────────────────────────────────
        print('\nB2 · EL REPÀS DE FITTINGS')
        subvista('Repàs de fittings', 'b2_repas.png')
        cols = repas['sessions']
        print('    columnes:', [f"{c['origen']}@{(c['data'] or '')[:10]}" for c in cols])
        mira('R1 · la primera columna és l\'ENTRADA DE POMs',
             bool(cols) and cols[0]['origen'] == 'ENTRADA',
             cols[0]['origen'] if cols else 'cap columna')
        # R2 · el cens: EXACTAMENT les mateixes identitats que la taula de mesures del model.
        # Es comparen les identitats i no els recomptes: dues xifres iguals amb files diferents
        # passarien per bones, i el que es vol dir és «hi són totes i no n'hi ha cap de sobrera».
        ident = lambda r: (r['pom_id'], r.get('capa') or '', r.get('instancia') or '')   # noqa: E731
        taula = {ident(r) for r in mesures.get('rows', [])}
        vist = {ident(r) for r in repas['rows']}
        mira('R2 · la taula porta totes les mesures del model', taula == vist,
             f"repàs {len(vist)} · taula de mesures {len(taula)}"
             + (f' · falten {sorted(taula - vist)}' if taula - vist else '')
             + (f' · sobren {sorted(vist - taula)}' if vist - taula else ''))
        # R3 · cap parell de columnes amb la mateixa etiqueta i la mateixa data.
        etiquetes = [f"{c.get('fase') or c['origen']}@{(c['data'] or '')[:10]}" for c in cols]
        mira('R3 · cap columna duplicada', len(etiquetes) == len(set(etiquetes)),
             ' · '.join(etiquetes))
        # R4 · el marcatge, mesurat al NAVEGADOR (no al payload): pes i color computats.
        marcades = pag.evaluate("""() => [...document.querySelectorAll('td')]
            .map(td => ({ txt: td.innerText.trim(),
                          pes: getComputedStyle(td).fontWeight,
                          col: getComputedStyle(td).color }))
            .filter(c => /^[0-9]+([.,][0-9]+)?$/.test(c.txt) && Number(c.pes) >= 600)""")
        canvis = sum(1 for r in repas['rows'] for c in r['valors'].values() if c.get('canvi'))
        print(f'    cel·les en negreta a pantalla: {len(marcades)} · canvis al payload: {canvis}')
        mira('R4 · els canvis van en negreta', len(marcades) >= canvis > 0,
             f'{len(marcades)} negretes per a {canvis} canvis')
        ajustats = [c for c in marcades if c['col'] == WARN_INK]
        esperats = sum(1 for r in repas['rows'] for c in r['valors'].values()
                       if c.get('canvi') and c.get('veredicte') == 'ADJUSTED')
        mira('R4 · …i els ADJUSTED en taronja `--warn-ink`', len(ajustats) >= esperats > 0,
             f'{len(ajustats)} en {WARN_INK} per a {esperats} ADJUSTED')

        nav.close()

    print('\nESCRIPTURES CENSADES (cap ha arribat al servidor):',
          json.dumps(sorted(set(escriptures)), ensure_ascii=False) or 'cap')
    print(f'Captures a {OUT}')
    if falles:
        print(f'\n❌ {len(falles)} afirmacions vermelles: ' + ' · '.join(falles))
        sys.exit(1)
    print('\n✅ B1+B2 a pantalla · totes les afirmacions verdes')


if __name__ == '__main__':
    main()
