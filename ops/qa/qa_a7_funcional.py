"""A7 · PROVA FUNCIONAL REAL del wizard partit, contra el SERVEI VIU.

No és una captura: és un GEST i la seva conseqüència. El brief del bloc B ho demana amb
aquestes paraules — «completar 2→3→4 contra el ZZ-TEST, verificar persistència + viatge del
blau + reobrir amb “Canviar”»— i una foto no pot respondre'n cap dels tres.

QUÈ FA, sobre `FTT-SS26-0001` (model 1319 de `fhort`, l'ítem 19 amb GarmentPOMMap ZZ-TEST):

  1. llegeix per API l'estat de partida (peça · talles · graduació);
  2. obre el Resum, prem «Canviar» al subespai TALLES i comprova que passa a ACTUAL
     (`--sel` + filet d'or) i que **el seu desar és l'únic blau de la columna**;
  3. CANVIA LA TALLA BASE i desa;
  4. torna a llegir per API i comprova que **el canvi ha persistit** i que la PEÇA i la
     GRADUACIÓ **no s'han mogut** — que és el que fa segur partir el desat: `update-step2`
     només escriu el que li ve al payload;
  5. recarrega la pantalla i comprova que el subespai torna a estar FET amb el valor nou
     fixat i visible, i que el blau ha viatjat al pas que queda pendent;
  6. deixa el model **com estava** (restaura la talla base d'origen).

Surt amb codi 1 si cap comprovació falla.

    FTT_QA_TOKEN=… venv/bin/python ops/qa/qa_a7_funcional.py
"""
import mimetypes
import os
import pathlib
import sys

import requests
from playwright.sync_api import sync_playwright

REPO = pathlib.Path(__file__).resolve().parents[2]
DIST = REPO / 'frontend' / 'dist'
OUT = pathlib.Path(__file__).resolve().parent / 'captures'
BASE = 'https://staging.fhorttextile.tech'
VIU = 'http://127.0.0.1:8001'
HOST_TENANT = os.environ.get('FTT_QA_HOST', 'fhorttextile.tech')
TOKEN = os.environ.get('FTT_QA_TOKEN', '')
MODEL = int(os.environ.get('FTT_QA_MODEL', '1319'))

ko = 0


def comprova(què, condicio, detall=''):
    global ko
    if condicio:
        print(f'  ✓ {què}')
    else:
        ko += 1
        print(f'  ✗ {què}   {detall}')


def api(sess, metode, cami, **kw):
    r = sess.request(metode, VIU + cami,
                     headers={'Host': HOST_TENANT, 'Authorization': f'Bearer {TOKEN}',
                              'Content-Type': 'application/json'}, timeout=30, **kw)
    return r


def main():
    global ko
    if not TOKEN:
        sys.exit('Falta FTT_QA_TOKEN.')
    if not DIST.exists():
        sys.exit('Cal `npm run build`.')
    OUT.mkdir(exist_ok=True)
    sess = requests.Session()

    abans = api(sess, 'GET', f'/api/v1/models/{MODEL}/').json()
    base0 = abans.get('base_size_label')
    run0 = (abans.get('size_run_model') or '').split('·')
    item0 = abans.get('garment_type_item')
    grs0 = abans.get('grading_rule_set')
    print(f'\nESTAT DE PARTIDA · peça={item0} · sistema={abans.get("size_system")} '
          f'· run={"·".join(run0)} · base={base0} · joc={grs0}')
    # La talla nova ha de ser una ALTRA del mateix run: així el gest és real i el guard
    # «la base ha de ser dins del run» segueix satisfet.
    novaBase = next((l for l in run0 if l and l != base0), None)
    if not novaBase:
        sys.exit('El model del banc no té prou talles al run per fer la prova.')
    print(f'GEST: talla base {base0} → {novaBase}\n')

    def handler(route, request):
        url = request.url
        cami = url.split(BASE, 1)[-1].split('?')[0] if url.startswith(BASE) else url
        if cami.startswith('/api/'):
            try:
                r = sess.request(request.method, VIU + url.split(BASE, 1)[-1],
                                 headers={'Host': HOST_TENANT, 'Authorization': f'Bearer {TOKEN}',
                                          'Content-Type': request.header_value('content-type') or 'application/json'},
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

        # ── 1 · el Resum, amb els dos contenidors ─────────────────────────────────────
        pag.goto(f'{BASE}/models/{MODEL}?tab=Resum', wait_until='networkidle')
        pag.wait_for_timeout(2000)
        print('1 · EL RESUM OBERT')
        comprova('hi ha els dos contenidors (Informació · Definició del model)',
                 pag.locator('text=Informació').count() > 0
                 and pag.locator('text=Definició del model').count() > 0)
        blausInicials = pag.locator('button[style*="rgb(43, 101, 194)"]').count()
        comprova('el blau és del pas PENDENT (Graduació), no dels que ja estan fets',
                 pag.locator('button:has-text("Definir graduació")').count() == 1)

        # ── 2 · «Canviar» al subespai TALLES → passa a ACTUAL ─────────────────────────
        print('\n2 · «CANVIAR» AL SUBESPAI TALLES')
        pag.locator('div:has(> span:text-is("Talles")) button:has-text("Canviar")').first.click()
        pag.wait_for_timeout(1500)
        capcalera = pag.locator('div:has(> span:text-is("Talles"))').first
        estil = capcalera.evaluate('el => { const c = getComputedStyle(el);'
                                   ' return { bg: c.backgroundColor, filet: c.boxShadow } }')
        comprova('la capçalera passa a --sel (#f7f5f2)', estil['bg'] == 'rgb(247, 245, 242)', estil['bg'])
        comprova("porta el filet d'or a l'esquerra", 'rgb(194, 122, 42)' in estil['filet'], estil['filet'])
        comprova('el seu desar hi és («Desar talles»)',
                 pag.locator('button:has-text("Desar talles")').count() == 1)
        blaus = pag.locator('div:has-text("Definició del model") button[style*="rgb(43, 101, 194)"]')
        comprova('EL SEU DESAR ÉS L\'ÚNIC BLAU de la columna de treball',
                 pag.locator('button:has-text("Desar talles")').count() == 1
                 and pag.locator('button:has-text("Definir graduació")').first
                        .evaluate('el => getComputedStyle(el).backgroundColor') != 'rgb(43, 101, 194)',
                 f'blaus={blaus.count()}')
        pag.screenshot(path=str(OUT / 'a7_f1_talles_actual.png'), full_page=True)

        # ── 3 · canvi de talla base + desar ───────────────────────────────────────────
        print(f'\n3 · CANVI DE TALLA BASE ({base0} → {novaBase}) I DESAR')
        pag.locator(f'button:text-is("{novaBase}")').last.click()
        pag.wait_for_timeout(400)
        pag.locator('button:has-text("Desar talles")').first.click()
        pag.wait_for_timeout(2500)

        # ── 4 · persistència, i que NO s'ha mogut res més ─────────────────────────────
        print('\n4 · PERSISTÈNCIA (API viva, no estat de pantalla)')
        despres = api(sess, 'GET', f'/api/v1/models/{MODEL}/').json()
        comprova(f'la talla base desada és {novaBase}',
                 despres.get('base_size_label') == novaBase, despres.get('base_size_label'))
        comprova('el run NO ha canviat',
                 (despres.get('size_run_model') or '') == (abans.get('size_run_model') or ''),
                 despres.get('size_run_model'))
        comprova('la PEÇA no s\'ha mogut (un PATCH de talles no toca el pas 2)',
                 despres.get('garment_type_item') == item0, despres.get('garment_type_item'))
        comprova('la GRADUACIÓ no s\'ha mogut (ni el joc ni les seves regles)',
                 despres.get('grading_rule_set') == grs0, despres.get('grading_rule_set'))

        # ── 5 · reobrir: FET amb el valor NOU fixat i visible ─────────────────────────
        print('\n5 · REOBRIR — l\'elecció queda FIXADA I VISIBLE')
        pag.goto(f'{BASE}/models/{MODEL}?tab=Resum', wait_until='networkidle')
        pag.wait_for_timeout(2000)
        xip = pag.locator(f'button:has-text("{novaBase} · base")').first
        comprova(f'el xip «{novaBase} · base» hi és, en verd d\'inclusió', xip.count() > 0)
        if xip.count():
            c = xip.evaluate('el => { const s = getComputedStyle(el);'
                             ' return { bg: s.backgroundColor, ink: s.color } }')
            comprova('el xip fixat va en --ok-bg / --ok',
                     c['bg'] == 'rgb(233, 243, 234)' and c['ink'] == 'rgb(46, 125, 50)', str(c))
        comprova('el subespai torna a oferir «Canviar» (i no el formulari)',
                 pag.locator('div:has(> span:text-is("Talles")) button:has-text("Canviar")').count() == 1)
        comprova('el blau ha tornat al pas pendent (Graduació)',
                 pag.locator('button:has-text("Definir graduació")').first
                    .evaluate('el => getComputedStyle(el).backgroundColor') == 'rgb(43, 101, 194)')
        pag.screenshot(path=str(OUT / 'a7_f2_talles_fet_nou.png'), full_page=True)
        nav.close()

    # ── 6 · el banc de proves queda com estava ────────────────────────────────────────
    print('\n6 · RESTAURACIÓ DEL BANC DE PROVES')
    r = api(sess, 'PATCH', f'/api/v1/models/{MODEL}/update-step2/', json={'base_size': base0})
    tornat = api(sess, 'GET', f'/api/v1/models/{MODEL}/').json()
    comprova(f'la talla base torna a ser {base0}',
             tornat.get('base_size_label') == base0, f'{r.status_code} {tornat.get("base_size_label")}')

    print(f'\n──────── {ko} comprovacions fallides ────────')
    sys.exit(1 if ko else 0)


if __name__ == '__main__':
    main()
