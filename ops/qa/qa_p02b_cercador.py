"""P0.2b — el desplegable del cercador de POM sortia TALLAT.

Causa: anava `position:absolute` dins del cercador, i el cercador viu dins del contenidor
`overflow-x:auto` que fa scrollar la taula. Un avantpassat amb overflow ≠ `visible` retalla els
fills posicionats **encara que portin z-index alt** — és clipping, no apilament.

Aquest fum comprova el que la regla d'Agus demana: que surti **sencer**, per sobre de la taula,
amb tots els resultats visibles i scroll propi si no hi caben. I ho comprova a les tres
situacions que el trencaven:

  1. taula CURTA (poques files)
  2. taula LLARGA (el contenidor scrolla de debò)
  3. el cercador A PROP DEL FINAL DE LA FINESTRA (finestra baixa)

En els tres casos la llista ha de quedar DINS del viewport i no retallada pel contenidor.

    /tmp/qa-venv/bin/python ops/qa/qa_p02b_cercador.py
"""
import json
import mimetypes
import pathlib
import sys

from playwright.sync_api import sync_playwright

REPO = pathlib.Path(__file__).resolve().parents[2]
DIST = REPO / 'frontend' / 'dist'
DIR = pathlib.Path(__file__).resolve().parent
FIXTURE = DIR / 'qa_p02_fixture.json'
CERCA = DIR / '_poms_cerca.json'
BASE = 'https://staging.fhorttextile.tech'

for f in (FIXTURE, CERCA):
    if not f.is_file():
        sys.exit(f'✗ falta {f.name} — genera els fixtures amb qa_p02_fixture.py')

DADES = json.loads(FIXTURE.read_text())
POMS = json.loads(CERCA.read_text())
MID = DADES['_model_id']
TAULA = f'/api/v1/models/{MID}/taula-mesures/'
BUIT = {'count': 0, 'results': [], 'next': None, 'previous': None}
PERFIL = {'id': 1, 'username': 'qa', 'nom_complet': 'QA', 'rol_nom': 'admin',
          'capabilities': ['configure', 'EXECUTE_TASKS', 'CLOSE_GATES'], 'idioma': 'ca'}


def fes_handler(files_extra=0):
    """`files_extra` clona files de la taula per fabricar la taula LLARGA."""
    dades = dict(DADES)
    if files_extra:
        base = DADES[TAULA]
        rows = list(base.get('rows') or [])
        clons = []
        for i in range(files_extra):
            r = dict(rows[i % max(1, len(rows))])
            r['id'] = 900000 + i
            clons.append(r)
        dades[TAULA] = {**base, 'rows': rows + clons}

    def _handler(route):
        url = route.request.url
        path = url.split(BASE, 1)[-1].split('?')[0] if BASE in url else url.split('?')[0]
        if '/api/' in path:
            if path == '/api/v1/poms/cerca/':
                cos = POMS
            else:
                cos = dades.get(path)
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


def prova(ctx, titol, files_extra, viewport):
    page = ctx.new_page()
    page.set_viewport_size(viewport)
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.route('**/*', fes_handler(files_extra))
    page.add_init_script("localStorage.setItem('access_token','qa');"
                         "localStorage.setItem('fhort.lang','ca');")
    page.goto(f'{BASE}/models/{MID}?tab=Mesures&mode=entry',
              wait_until='networkidle', timeout=45000)
    page.wait_for_timeout(1600)

    problemes = []
    camp = page.get_by_placeholder('Codi o nom', exact=False)
    if camp.count() == 0:
        camp = page.locator('input[placeholder]').last
    camp.first.scroll_into_view_if_needed()
    camp.first.fill('ch')
    page.wait_for_timeout(1200)

    # La llista: el descendent de <body> que porta les files de resultats.
    llista = page.locator('body > div').filter(has_text='CATÀLEG').last
    if llista.count() == 0 or not llista.is_visible():
        llista = page.locator('div').filter(has_text='CATÀLEG').last

    caixa = llista.bounding_box()
    if not caixa:
        problemes.append(f'{titol}: la llista no es veu')
        page.close()
        return problemes

    vw, vh = viewport['width'], viewport['height']
    # (1) DINS del viewport, sencera
    if caixa['y'] < -1 or caixa['y'] + caixa['height'] > vh + 1:
        problemes.append(f'{titol}: la llista surt del viewport '
                         f'(y={caixa["y"]:.0f} h={caixa["height"]:.0f} vh={vh})')
    if caixa['x'] < -1 or caixa['x'] + caixa['width'] > vw + 1:
        problemes.append(f'{titol}: la llista surt del viewport per l\'ample')

    # (2) NO retallada per cap avantpassat amb overflow: amb el portal, el seu pare és el body.
    pare_ok = llista.evaluate('el => el.parentElement === document.body')
    if not pare_ok:
        problemes.append(f'{titol}: la llista NO penja del body — un avantpassat la pot retallar')

    # (3) tots els resultats abastables: o hi caben, o la llista scrolla ella mateixa.
    abastable = llista.evaluate(
        'el => el.scrollHeight <= el.clientHeight + 1'
        ' || ["auto","scroll"].includes(getComputedStyle(el).overflowY)')
    if not abastable:
        problemes.append(f'{titol}: hi ha resultats fora d\'abast (ni hi caben ni scrolla)')

    n = llista.evaluate('el => el.querySelectorAll("div").length')
    if not problemes:
        print(f'  ✓ {titol}: sencera dins del viewport, penjada del body, '
              f'{caixa["height"]:.0f}px d\'alçada, {n} nodes')
    if errors:
        problemes.append(f'{titol}: error de pàgina → {errors[0][:120]}')
    page.close()
    return problemes


def main():
    if not DIST.is_dir():
        print(f'✗ no hi ha bundle a {DIST}'); return 1
    fallides = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(base_url=BASE, ignore_https_errors=True)
        fallides += prova(ctx, 'taula CURTA', 0, {'width': 1600, 'height': 1200})
        fallides += prova(ctx, 'taula LLARGA', 40, {'width': 1600, 'height': 1200})
        fallides += prova(ctx, 'finestra BAIXA (cercador arran del final)', 40,
                          {'width': 1400, 'height': 560})
        b.close()

    print()
    if fallides:
        print(f'✗ {len(fallides)} problema(es):')
        for f in fallides:
            print(f'   · {f}')
        return 1
    print('✓ P0.2b verd')
    return 0


if __name__ == '__main__':
    sys.exit(main())
