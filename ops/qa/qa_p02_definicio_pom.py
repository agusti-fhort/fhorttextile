"""P0.2 — per què les columnes d'INSTÀNCIA no es pinten a «Definició POM».

Prova A/B sobre el bundle REAL de `frontend/dist`, amb les dades reals del model de prova
(`qa_p02_fixture.py`; MAI el MILEY):

  A · diccionari SA (HTTP 200)        → hi han de ser les columnes d'instància (POSICIÓ · ESTAT)
  B · diccionari CAIGUT (HTTP 500)    → què passa avui, i què ha de passar després del fix

La regla d'Agus (06/08): **si el diccionari no carrega, la pantalla HO DIU. Mai amagar el bloc
en silenci.** El cas B és, doncs, la prova del fix: no n'hi ha prou que les columnes no hi
siguin — hi ha d'haver un avís visible.

    /tmp/qa-venv/bin/python ops/qa/qa_p02_definicio_pom.py
"""
import json
import mimetypes
import pathlib
import sys

from playwright.sync_api import sync_playwright

REPO = pathlib.Path(__file__).resolve().parents[2]
DIST = REPO / 'frontend' / 'dist'
FIXTURE = pathlib.Path(__file__).resolve().parent / 'qa_p02_fixture.json'
BASE = 'https://staging.fhorttextile.tech'

if not FIXTURE.is_file():
    sys.exit(f'✗ falta {FIXTURE.name} — genera\'l amb qa_p02_fixture.py')
DADES = json.loads(FIXTURE.read_text())
MID = DADES['_model_id']
BUIT = {'count': 0, 'results': [], 'next': None, 'previous': None}
PERFIL = {'id': 1, 'username': 'qa', 'nom_complet': 'QA', 'rol_nom': 'admin',
          'capabilities': ['configure', 'EXECUTE_TASKS', 'CLOSE_GATES'], 'idioma': 'ca'}
DICC = '/api/v1/mesures/diccionari/'


def fes_handler(dicc_ok=True):
    def _handler(route):
        url = route.request.url
        path = url.split(BASE, 1)[-1].split('?')[0] if BASE in url else url.split('?')[0]
        if '/api/' in path:
            if path == DICC and not dicc_ok:
                # El cas B: el vocabulari no arriba. 500, que és el que un backend caigut fa.
                route.fulfill(status=500, content_type='application/json',
                              body=json.dumps({'detail': 'boom'}))
                return
            cos = DADES.get(path)
            if cos is None:
                cos = PERFIL if ('/me/' in path or '/perfil/' in path) else BUIT
            route.fulfill(status=200, content_type='application/json',
                          body=json.dumps(cos, ensure_ascii=False))
            return
        f = DIST / (path.lstrip('/') or 'index.html')
        if not f.is_file():
            f = DIST / 'index.html'
        route.fulfill(status=200, body=f.read_bytes(),
                      content_type=mimetypes.guess_type(str(f))[0] or 'text/html')
    return _handler


def _capcaleres(page):
    """El text de les capçaleres de la taula, en minúscules."""
    caps = page.locator('table thead')
    return caps.first.inner_text().lower() if caps.count() else ''


def obre(ctx, dicc_ok):
    page = ctx.new_page()
    errors, consola = [], []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('console', lambda m: consola.append(m.text) if m.type == 'error' else None)
    page.route('**/*', fes_handler(dicc_ok))
    page.add_init_script("localStorage.setItem('access_token','qa');"
                         "localStorage.setItem('fhort.lang','ca');")
    page.goto(f'{BASE}/models/{MID}?tab=Mesures&mode=entry',
              wait_until='networkidle', timeout=45000)
    page.wait_for_timeout(1800)
    return page, errors, consola


def main():
    if not DIST.is_dir():
        print(f'✗ no hi ha bundle a {DIST}'); return 1

    eixos = [e for e in DADES[DICC]['eixos']]
    noms_eix = [e['nom_ca'] for e in eixos]
    fallides = []

    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(base_url=BASE, ignore_https_errors=True,
                            viewport={'width': 1600, 'height': 1200})

        # ── A · diccionari SA ──────────────────────────────────────────────
        page, errs, cons = obre(ctx, dicc_ok=True)
        # Les capçaleres de la TAULA, no el cos sencer: l'avís del cas B anomena «Posició» i
        # «Estat» per explicar què falta, i buscar-les al body donava per bones unes columnes
        # que no hi eren.
        low = _capcaleres(page)
        trobats = [n for n in noms_eix if n.lower() in low]
        if len(trobats) == len(noms_eix):
            print(f'  ✓ A · amb diccionari SA hi són les columnes d\'instància: {trobats}')
        else:
            fallides.append(f'A · amb diccionari SA FALTEN columnes: '
                            f'esperades {noms_eix}, trobades {trobats}')
        if errs:
            fallides.append(f'A · error de pàgina: {errs[0][:140]}')
        page.close()

        # ── B · diccionari CAIGUT ──────────────────────────────────────────
        page, errs, cons = obre(ctx, dicc_ok=False)
        low_b = _capcaleres(page)
        presents_b = [n for n in noms_eix if n.lower() in low_b]
        cos_b = page.inner_text('body')

        # Un avís visible: qualsevol d'aquestes marques, buscades al COS de la pàgina (l'avís
        # viu sobre la taula, no a la capçalera de columnes que mira `low_b`).
        marques = ['vocabulari', 'diccionari', 'no s\'ha pogut carregar', 'reintenta']
        avis = [m for m in marques if m in cos_b.lower()]

        print(f'  · B · amb diccionari CAIGUT · columnes presents: {presents_b or "cap"} '
              f'· avís: {avis or "CAP"}')
        if not avis:
            fallides.append('B · el diccionari cau i la pantalla NO ho diu '
                            '(el bloc desapareix en silenci) — regla d\'Agus 06/08')
        if presents_b:
            fallides.append(f'B · amb el diccionari caigut la capçalera encara anuncia {presents_b}')
        if errs:
            fallides.append(f'B · error de pàgina: {errs[0][:140]}')
        page.close()
        b.close()

    print()
    if fallides:
        print(f'✗ {len(fallides)} problema(es):')
        for f in fallides:
            print(f'   · {f}')
        return 1
    print('✓ P0.2 verd')
    return 0


if __name__ == '__main__':
    sys.exit(main())
