"""ARNÈS · el break és de la REGLA (Agus, 10/08). Tres coses mesurades contra el servei viu.

Què va passar i què es mesura aquí. La barra «Talles que cobreix» de la pantalla d'un joc de
regles era CLICABLE, i cada clic escrivia `talla_break_label` a TOTES les regles amb Δ break
alhora —98, al catàleg de Brownie— sense dir-ho i sense confirmació. S'ha retirat el gest, el
break ha baixat a un picker PER FILA, i al lloc que ocupava l'escopeta hi ha ara el selector del
SISTEMA DE TALLES del joc, que fins avui no es podia triar des d'aquesta pantalla.

  V1 · L'ESCOPETA JA NO HI ÉS       les talles de la barra no són clicables i cap clic escriu
  V2 · EL BREAK ÉS PER FILA         canviar el d'UNA regla no toca cap de les altres
  V3 · EL SELECTOR MANA LES OPCIONS el picker ofereix les talles del sistema del joc, i el
                                    selector va obert o tancat segons si el joc té regles

L'arnès va contra el BUNDLE DEL DISC (`frontend/dist` — cal `npm run build`) i l'API real del
gunicorn desplegat, amb el mateix reenviament que `qa_a3_grading_rules.py`. Les afirmacions no
es llegeixen a la pantalla: es RE-LLEGEIXEN PER API després de desar, que és l'única manera de
saber què ha tocat de debò (una pantalla pot pintar bé i haver escrit malament).

⚠️ NO TOCA EL JOC 219 (`GRADING BROWNIE 2026`). Es munta el seu propi banc `ZZ-QA-BREAK-*` i el
desmunta al final, passi el que passi. V. `qa_break_per_regla_banc.py`.

⚠️ Les icones surten buides a les captures: Tabler entra per CDN i aquí tot el que no és `/api/`
se serveix del disc. Al navegador de debò hi són (mateixa nota que A3).

    /tmp/qa-venv/bin/python ops/qa/qa_break_per_regla.py
"""
import json
import mimetypes
import os
import pathlib
import subprocess
import sys

import requests
from playwright.sync_api import sync_playwright

REPO = pathlib.Path(__file__).resolve().parents[2]
DIST = REPO / 'frontend' / 'dist'
OUT = pathlib.Path(__file__).resolve().parent / 'captures'
BANC = pathlib.Path(__file__).resolve().parent / 'qa_break_per_regla_banc.py'
PY_DJANGO = REPO / 'backend' / 'venv' / 'bin' / 'python'
BASE = 'https://staging.fhorttextile.tech'
VIU = 'http://127.0.0.1:8001'
HOST_TENANT = os.environ.get('FTT_QA_HOST', 'staging.fhorttextile.tech')

RESULTATS = []


def comprova(etiqueta, ok, detall=''):
    RESULTATS.append((etiqueta, bool(ok)))
    print(f'  {"✓" if ok else "✗"} {etiqueta}' + (f'   → {detall}' if detall else ''))
    return bool(ok)


def django(*args):
    """Un script Django al venv del backend. `check=True`: si el banc peta, l'arnès no segueix."""
    r = subprocess.run([str(PY_DJANGO), str(BANC), *args], capture_output=True, text=True,
                       cwd=str(REPO), env={**os.environ, 'DJANGO_SETTINGS_MODULE': 'fhort.settings'})
    if r.returncode != 0:
        sys.exit(f'BANC ({" ".join(args)}) ha fallat:\n{r.stderr}')
    return json.loads(r.stdout.strip().splitlines()[-1])


def mint_token():
    """El token amb el claim `tenant_schema`. NO S'IMPRIMEIX MAI (ni aquí ni al resum)."""
    codi = (
        "import django; django.setup()\n"
        "from django.contrib.auth import get_user_model\n"
        "from rest_framework_simplejwt.tokens import AccessToken\n"
        "from fhort.auth_jwt import TENANT_CLAIM\n"
        "from django_tenants.utils import schema_context\n"
        "with schema_context('fhort'):\n"
        "    U = get_user_model()\n"
        "    u = U.objects.filter(email='a.devant@fhort.cat').first() "
        "or U.objects.filter(is_superuser=True).first()\n"
        "    tok = AccessToken.for_user(u)\n"
        "    tok[TENANT_CLAIM] = 'fhort'\n"
        "    print(str(tok))\n")
    r = subprocess.run([str(PY_DJANGO), '-c', codi], capture_output=True, text=True,
                       cwd=str(REPO / 'backend'),
                       env={**os.environ, 'DJANGO_SETTINGS_MODULE': 'fhort.settings'})
    if r.returncode != 0:
        sys.exit(f'No s\'ha pogut mintar el token:\n{r.stderr}')
    return r.stdout.strip().splitlines()[-1]


def api(sess, token, cami):
    """Lectura directa del backend desplegat — el que hi ha DESAT, no el que la pantalla pinta."""
    r = sess.get(VIU + cami, headers={'Host': HOST_TENANT, 'Authorization': f'Bearer {token}'},
                 timeout=30)
    r.raise_for_status()
    return r.json()


def foto_regles(sess, token, joc_id):
    """{id: (Δbase, Δbreak, talla_break)} — la forma que ha de quedar CONGELADA fila a fila."""
    d = api(sess, token, f'/api/v1/grading-rule-sets/{joc_id}/')
    return {r['id']: (r['increment_base'], r['increment_break'], r['talla_break_label'])
            for r in d['regles']}


def obre_joc(pag, nom):
    """De la llista a la pantalla del joc, pel cercador (que és com s'hi arriba de debò)."""
    pag.goto(BASE + '/poms/grading', wait_until='networkidle')
    pag.wait_for_timeout(1200)
    pag.locator('input[placeholder*="cerca"]').first.fill(nom)
    pag.wait_for_timeout(600)
    pag.locator('button:has-text("Editar")').first.click()
    pag.wait_for_timeout(1200)


def main():
    if not DIST.exists():
        sys.exit(f'No hi ha bundle a {DIST} — cal `npm run build`.')
    OUT.mkdir(exist_ok=True)

    print('── BANC ──')
    banc = django('--crea')
    for k, j in banc.items():
        print(f'  {j["nom"]:20} id={j["id"]:<5} {j["sistema"]:14} {len(j["regles"])} regles')
    token = mint_token()
    sess = requests.Session()

    def handler(route, request):
        url = request.url
        cami = url.split(BASE, 1)[-1].split('?')[0] if url.startswith(BASE) else url
        if cami.startswith('/api/'):
            try:
                r = sess.request(
                    request.method, VIU + url.split(BASE, 1)[-1],
                    headers={'Host': HOST_TENANT, 'Authorization': f'Bearer {token}',
                             'Content-Type': request.header_value('content-type') or 'application/json'},
                    data=request.post_data_buffer, timeout=30)
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

    try:
        with sync_playwright() as p:
            nav = p.chromium.launch()
            ctx = nav.new_context(viewport={'width': 1600, 'height': 1100})
            pag = ctx.new_page()
            pag.route('**/*', handler)
            pag.goto(BASE + '/', wait_until='domcontentloaded')
            pag.evaluate("([t]) => { localStorage.setItem('access_token', t);"
                         " localStorage.setItem('fhort.lang', 'ca') }", [token])

            # ── V1 · L'ESCOPETA JA NO HI ÉS ──────────────────────────────────────────────
            print('\n── V1 · l\'escopeta ──')
            alpha = banc['alpha']
            abans = foto_regles(sess, token, alpha['id'])
            obre_joc(pag, 'ZZ-QA-BREAK-ALPHA')
            pag.screenshot(path=str(OUT / 'break_01_pantalla_joc.png'), full_page=True)

            # La barra és el bloc que porta el rètol «Talles que cobreix». Les seves talles han
            # de ser text, no controls: si hi queda cap `<button>`, l'escopeta hi és encara.
            barra = pag.locator('div', has=pag.locator(
                'span:text-is("Talles que cobreix")')).last
            etiquetes = [e.strip() for e in barra.locator('span[title]').all_inner_texts()]
            botons_talla = 0
            for et in alpha['talles']:
                botons_talla += barra.locator(f'button:text-is("{et}")').count()
            comprova('cap talla de la barra és un botó', botons_talla == 0,
                     f'{botons_talla} botons trobats')
            comprova('la barra segueix ensenyant les 8 talles del sistema',
                     all(any(t in e for e in etiquetes) for t in alpha['talles']),
                     f'{len(etiquetes)} etiquetes')

            # I la prova de foc: clicar-hi a sobre no ha de deixar cap edició pendent ni escriure.
            barra.locator('span[title]').nth(4).click(force=True)   # la talla «L» de la barra
            pag.wait_for_timeout(500)
            desar = pag.locator('button:has-text("Gravar regles")').first
            comprova('clicar una talla no deixa cap edició pendent',
                     desar.is_disabled() if desar.count() else True)
            comprova('clicar una talla no ha escrit res a la BD',
                     foto_regles(sess, token, alpha['id']) == abans)

            # ── V2 · EL BREAK ÉS PER FILA ────────────────────────────────────────────────
            print('\n── V2 · canviar el break d\'UNA regla ──')
            files = pag.locator('table tbody tr')
            pickers = pag.locator('table tbody tr select[aria-label="Talla break"]')
            comprova('cada fila té el seu picker de talla break',
                     pickers.count() == files.count() == 6,
                     f'{pickers.count()} pickers / {files.count()} files')
            # Les 2 files sense Δ break el tenen TANCAT: un ancoratge sense increment no diu res.
            tancats = sum(1 for i in range(pickers.count()) if pickers.nth(i).is_disabled())
            comprova('les 2 regles sense Δ break tenen el picker tancat', tancats == 2,
                     f'{tancats} tancats')
            # Les opcions són les del sistema del joc (8 talles) + el buit.
            opcions = pickers.first.locator('option').all_inner_texts()
            comprova('les opcions són les talles d\'ALPHA_EU_W + el buit',
                     [o.strip() for o in opcions] == ['—'] + alpha['talles'], f'{opcions}')

            # El gest: UNA fila, de S a L.
            pickers.first.select_option('L')
            pag.wait_for_timeout(300)
            pag.locator('button:has-text("Gravar regles")').first.click()
            pag.wait_for_timeout(2000)

            despres = foto_regles(sess, token, alpha['id'])
            canviades = [i for i in abans if abans[i] != despres.get(i)]
            comprova('exactament UNA regla ha canviat', len(canviades) == 1,
                     f'{len(canviades)} canviades: {canviades}')
            if len(canviades) == 1:
                i = canviades[0]
                comprova('la que ha canviat ho ha fet a L (i només el break)',
                         despres[i][2] == 'L' and despres[i][:2] == abans[i][:2],
                         f'{abans[i]} → {despres[i]}')
            intactes = [i for i in abans if i not in canviades]
            comprova('les altres 5 regles són BYTE A BYTE les d\'abans',
                     all(abans[i] == despres[i] for i in intactes), f'{len(intactes)} intactes')
            pag.screenshot(path=str(OUT / 'break_02_una_fila_canviada.png'), full_page=True)

            # ── V3 · EL SELECTOR DEL SISTEMA DE TALLES ───────────────────────────────────
            print('\n── V3 · el selector del sistema ──')
            selector = pag.locator('select#joc-run-barra')
            comprova('el selector existeix a la barra (abans no hi era enlloc)',
                     selector.count() == 1)
            comprova('apunta al sistema del joc',
                     selector.first.input_value() == str(
                         api(sess, token, f'/api/v1/grading-rule-sets/{alpha["id"]}/')['size_system']))
            comprova('amb regles va TANCAT', selector.first.is_disabled())
            motiu = pag.locator('text=/No es pot canviar en un conjunt amb regles/')
            comprova('i el motiu és VISIBLE, no un `title` amagat',
                     motiu.count() > 0 and motiu.first.is_visible())

            # Les opcions del picker surten del SISTEMA DEL JOC: al joc numèric, talles numèriques.
            num = banc['num']
            obre_joc(pag, 'ZZ-QA-BREAK-NUM')
            op_num = [o.strip() for o in pag.locator(
                'table tbody tr select[aria-label="Talla break"]').first.locator(
                'option').all_inner_texts()]
            comprova('al joc NUMERIC_EU_W el picker ofereix les SEVES talles',
                     op_num == ['—'] + num['talles'], f'{op_num}')
            pag.screenshot(path=str(OUT / 'break_03_sistema_numeric.png'), full_page=True)

            # I en un joc SENSE regles el selector va obert i canviar-lo canvia les talles.
            obre_joc(pag, 'ZZ-QA-BREAK-BUIT')
            sel_buit = pag.locator('select#joc-run-barra').first
            comprova('sense regles el selector va OBERT', not sel_buit.is_disabled())
            sel_buit.select_option(label='NUMERIC_EU_W · Numeric EU — Women')
            pag.wait_for_timeout(2500)
            desat = api(sess, token, f'/api/v1/grading-rule-sets/{banc["buit"]["id"]}/')
            comprova('el canvi s\'ha DESAT (no només pintat)',
                     desat['size_system_codi'] == 'NUMERIC_EU_W', desat['size_system_codi'])
            barra2 = pag.locator('div', has=pag.locator(
                'span:text-is("Talles que cobreix")')).last
            et2 = ' '.join(barra2.locator('span[title]').all_inner_texts())
            comprova('i la barra ja ensenya les talles noves',
                     all(t in et2 for t in num['talles']) and 'XXS' not in et2)
            pag.screenshot(path=str(OUT / 'break_04_selector_canviat.png'), full_page=True)

            nav.close()
    finally:
        # PASSI EL QUE PASSI. Un banc que sobreviu a una passada avortada contamina la següent.
        print('\n── DESMUNTATGE ──')
        print(f'  {django("--esborra")}')

    ok = sum(1 for _, v in RESULTATS if v)
    print(f'\n{"=" * 60}\n{ok}/{len(RESULTATS)} comprovacions verdes')
    for etiqueta, v in RESULTATS:
        if not v:
            print(f'   ✗ {etiqueta}')
    print(f'captures a {OUT}')
    sys.exit(0 if ok == len(RESULTATS) else 1)


if __name__ == '__main__':
    main()
