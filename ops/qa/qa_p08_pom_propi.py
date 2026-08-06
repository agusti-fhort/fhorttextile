"""P0.8 — el gest «Crear POM propi del model», a pantalla.

La vàlvula per al que el catàleg del client no té (commits 50-52 · `ba60e9ef` per al camp
d'origen). Aquesta QA recorre el gest sencer sobre el bundle REAL de `frontend/dist`, amb el
model **169** (BRW-FW26-0007) — **MAI el MILEY**.

## Què comprova

  1. cerca sense resultat → el cercador ho diu i ofereix l'acció de crear;
  2. l'acció s'obre i porta el TEXT CERCAT com a nom;
  3. la COL·LISIÓ de nomenclatura es diu amb el motiu («EK» ja és Neck width…) i no deixa
     confirmar;
  4. amb el codi net, confirmar tanca el gest i la fila neix;
  5. els tres idiomes, F5, consola neta.

## La frontera d'aquest fum, dita clara

L'API va ESTUBEJADA amb respostes reals: el `409` és el cos LITERAL que el backend viu va
tornar a la prova transaccional del model 169 (`NOMENCLATURA_OCUPADA` · «EK» ja és Neck
width), i el `201` té la forma real de la vista. El fum prova **el GEST**, no el servidor:
el servidor ja està verificat contra la BD dins d'un `atomic` que es desfà (commit 55), i
provar-lo aquí exigiria una credencial real al navegador. Sí que es comprova que la ruta
existeix al backend DESPLEGAT (401 sense credencial = viva), que és la lliçó del 06/08.

    backend/venv/bin/python ../ops/qa/qa_p02_fixture.py 169 ../ops/qa/qa_p08_fixture.json
    /tmp/qa-venv/bin/python  ops/qa/qa_p08_pom_propi.py
"""
import json
import mimetypes
import pathlib
import sys
import urllib.error
import urllib.request

from playwright.sync_api import sync_playwright

REPO = pathlib.Path(__file__).resolve().parents[2]
DIST = REPO / 'frontend' / 'dist'
# FIXTURE PROPI: P0.2 i P0.6 esperen el 1302 i aquest fum el 169. Compartir-lo els
# deixava en vermell cada cop que es regenerava per a l'altre.
FIXTURE = pathlib.Path(__file__).resolve().parent / 'qa_p08_fixture.json'
BASE = 'https://staging.fhorttextile.tech'
BACKEND_VIU = 'http://127.0.0.1:8001'

if not FIXTURE.is_file():
    sys.exit(f'✗ falta {FIXTURE.name} — genera\'l amb '
         f'`qa_p02_fixture.py 169 ops/qa/qa_p08_fixture.json`')
DADES = json.loads(FIXTURE.read_text())
MID = DADES['_model_id']
if MID == 1308:
    sys.exit('✗ el fixture és del MILEY (1308). Regenera\'l amb un model de proves: 169.')

BUIT = {'count': 0, 'results': [], 'next': None, 'previous': None}
PERFIL = {'id': 1, 'username': 'qa', 'nom_complet': 'QA', 'rol_nom': 'admin',
          'capabilities': ['configure', 'EXECUTE_TASKS', 'CLOSE_GATES'], 'idioma': 'ca'}

CERCA = 'sequins'          # el cas real: el catàleg de Brownie no en té cap
CODI_XOC = 'EK'            # ja és «Neck width» al catàleg d'aquest client
CODI_NET = 'SEQ H'
# El cos LITERAL del backend viu (prova transaccional del model 169, commit 55).
XOC_409 = {'codi': 'NOMENCLATURA_OCUPADA', 'nomenclatura': CODI_XOC, 'pom_id': 301,
           'pom_nom': 'Neck width',
           'message': f'«{CODI_XOC}» ja és Neck width al catàleg d\'aquest client.'}
OK_201 = {'pom_id': 99001, 'id': 99001, 'codi_client': CODI_NET,
          'nom_client': 'Height sequins piece', 'client_code': CODI_NET}

ETIQUETES = {
    # `manual` = `model_measurements.manual_title`: el panell de Definició POM neix al SELECTOR
    # (manual · importar · copiar) i la taula —amb el seu cercador al peu— no existeix fins que
    # se'n tria una. Sense aquest clic el fum buscava un input que encara no s'havia pintat.
    'ca': {'crear': 'Crear POM propi', 'cap': 'Cap resultat', 'manual': 'Introduir manualment'},
    'es': {'crear': 'Crear POM propio', 'cap': 'Ningún resultado', 'manual': 'Introducir manualmente'},
    'en': {'crear': 'Create model-owned POM', 'cap': 'No results', 'manual': 'Enter manually'},
}


def t_instancia(lang):
    """El títol del modal de posicions, per idioma (`instancia.modal_titol`)."""
    return {'ca': 'Posició i combinacions', 'es': 'Posición y combinaciones',
            'en': 'Position and combinations'}.get(lang, 'Posició i combinacions')


def fes_handler(estat):
    """`estat` acumula què s'ha demanat, per poder afirmar-ho després."""
    def _handler(route):
        req = route.request
        url = req.url
        path = url.split(BASE, 1)[-1].split('?')[0] if BASE in url else url.split('?')[0]
        if '/api/' in path:
            if path.endswith('/pom-propi/') and req.method == 'POST':
                cos = json.loads(req.post_data or '{}')
                estat['posts'].append(cos)
                xoc = (cos.get('nomenclatura') or '').strip().upper() == CODI_XOC
                route.fulfill(status=409 if xoc else 201, content_type='application/json',
                              body=json.dumps(XOC_409 if xoc else OK_201, ensure_ascii=False))
                return
            if path.endswith('/poms/cerca/'):
                estat['cerques'].append(url)
                route.fulfill(status=200, content_type='application/json',
                              body=json.dumps({'results': []}))   # 0 resultats, que és el cas
                return
            cos = DADES.get(path)
            if cos is None:
                cos = ({'task_id': 999} if path.endswith('/open-task/')
                       else (PERFIL if ('/me/' in path or '/perfil/' in path) else BUIT))
            route.fulfill(status=200, content_type='application/json',
                          body=json.dumps(cos, ensure_ascii=False))
            return
        f = DIST / (path.lstrip('/') or 'index.html')
        if not f.is_file():
            f = DIST / 'index.html'
        route.fulfill(status=200, body=f.read_bytes(),
                      content_type=mimetypes.guess_type(str(f))[0] or 'text/html')
    return _handler


def ruta_viva(path, metode='POST'):
    req = urllib.request.Request(f'{BACKEND_VIU}{path}', method=metode, data=b'{}',
                                 headers={'Host': 'staging.fhorttextile.tech',
                                          'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except OSError as e:
        return f'sense resposta ({e})'


def main():
    if not DIST.is_dir():
        print(f'✗ no hi ha bundle a {DIST}'); return 1
    fallides = []

    # ── 0 · LA RUTA, AL BACKEND QUE SERVEIX ────────────────────────────────────
    codi = ruta_viva(f'/api/v1/models/{MID}/pom-propi/')
    if codi == 404:
        fallides.append(f'pom-propi/ → 404 al backend VIU: el procés desplegat no té la ruta '
                        f'(cal `systemctl restart ftt-staging`)')
    else:
        print(f'  ✓ 0 · la ruta pom-propi/ és VIVA al backend desplegat (HTTP {codi})')

    with sync_playwright() as pw:
        b = pw.chromium.launch()
        for lang, lit in ETIQUETES.items():
            estat = {'posts': [], 'cerques': []}
            ctx = b.new_context(base_url=BASE, ignore_https_errors=True,
                                viewport={'width': 1600, 'height': 1200})
            page = ctx.new_page()
            errors, consola = [], []
            page.on('pageerror', lambda e: errors.append(str(e)))
            # El 409 de la col·lisió el provoca AQUEST fum a posta, i el navegador el registra
            # com a recurs fallit. No és soroll de l'aplicació: és la prova. S'exclou pel codi,
            # no per silenciar la consola sencera —qualsevol altre error segueix fent caure el fum.
            page.on('console', lambda m: consola.append(m.text)
                    if (m.type == 'error' and '409' not in m.text) else None)
            page.route('**/*', fes_handler(estat))
            page.add_init_script("localStorage.setItem('access_token','qa');"
                                 f"localStorage.setItem('fhort.lang','{lang}');")
            page.goto(f'{BASE}/models/{MID}?tab=Mesures&mode=entry',
                      wait_until='networkidle', timeout=45000)
            page.wait_for_timeout(2200)

            # ── 0b · sortir del SELECTOR: la taula (i el seu cercador) neix aquí ─
            manual = page.locator(f'text={lit["manual"]}')
            if manual.count() == 0:
                fallides.append(f'{lang} · no hi ha «{lit["manual"]}» al selector de Definició POM')
                ctx.close(); continue
            manual.first.click()
            page.wait_for_timeout(2500)

            # ── 1 · el cercador, sense resultat ────────────────────────────────
            # EL CERCADOR: l'únic input amb `placeholder` que NO és del carril ni de la
            # nomenclatura. Buscar-lo pel text del placeholder no serveix —diu «codi o nom…»
            # i canvia amb l'idioma—; buscar-lo per posició, tampoc: n'hi ha 29 de carril
            # al davant. L'estructura és el que aguanta.
            camp = page.locator('input[placeholder]:not([data-carril]):not([data-nomen])').last
            camp.click(); camp.fill(CERCA)
            page.wait_for_timeout(1400)

            cos = page.inner_text('body')
            te_cap = lit['cap'].split()[0].lower() in cos.lower()
            accio = page.locator(f'text={lit["crear"]}')
            if accio.count() == 0:
                fallides.append(f'{lang} · cap acció «{lit["crear"]}» amb 0 resultats')
                ctx.close(); continue
            print(f'  ✓ 1 · {lang} · 0 resultats · avís={te_cap} · l\'acció hi és')

            # ── 2 · s'obre i porta el text cercat ──────────────────────────────
            # ── 1b · PER TECLAT: `↓` marca l'acció i `Enter` la dispara (cua post-QA).
            # Era un `div` amb `onMouseDown`: només ratolí. Es prova amb el teclat i prou —si
            # el camí de teclat no hi és, el fum cau aquí i no pel clic.
            page.keyboard.press('ArrowDown')
            page.wait_for_timeout(300)
            marcada = page.locator('button[aria-selected="true"]')
            if marcada.count() == 0:
                fallides.append(f'{lang} · `↓` no marca l\'acció de crear')
            page.keyboard.press('Enter')
            page.wait_for_timeout(900)
            if page.locator('[role="dialog"]').count() == 0:
                fallides.append(f'{lang} · `Enter` no obre el gest de crear (només ratolí)')
            else:
                print(f'  ✓ 1b · {lang} · ↓ marca i Enter obre · sense ratolí')
            valors = page.eval_on_selector_all(
                'input', "els => els.map(e => e.value).filter(Boolean)")
            if not any(CERCA in (v or '').lower() for v in valors):
                fallides.append(f'{lang} · el text cercat NO arriba al gest (valors: {valors})')
            else:
                print(f'  ✓ 2 · {lang} · el text cercat hi arriba com a nom')

            # ── 3 · COL·LISIÓ, amb el motiu ────────────────────────────────────
            camps = page.locator('[role="dialog"] input')
            n = camps.count()
            if n < 2:
                fallides.append(f'{lang} · el gest no ofereix nom + nomenclatura ({n} camps)')
                ctx.close(); continue
            camps.nth(1).fill(CODI_XOC)
            page.keyboard.press('Enter')
            page.wait_for_timeout(1200)
            cos = page.inner_text('body')
            if 'Neck width' not in cos:
                fallides.append(f'{lang} · la col·lisió NO diu amb què xoca')
            elif page.locator('[role="dialog"]').count() == 0:
                fallides.append(f'{lang} · la col·lisió ha deixat confirmar (el gest s\'ha tancat)')
            else:
                print(f'  ✓ 3 · {lang} · col·lisió dita amb el motiu, i no deixa confirmar')

            # ── 4 · codi net → es confirma ─────────────────────────────────────
            camps.nth(1).fill(CODI_NET)
            page.keyboard.press('Enter')
            page.wait_for_timeout(1500)
            if page.locator('[role="dialog"]').count() != 0:
                fallides.append(f'{lang} · amb codi NET el gest no s\'ha tancat')
            else:
                enviats = [p.get('nomenclatura') for p in estat['posts']]
                print(f'  ✓ 4 · {lang} · confirmat · POSTs enviats: {enviats}')

            # ── 4b · ESC tanca el modal de POSICIONS (mateixa cua) ────────────
            mes = page.locator('button:has-text("＋")')
            if mes.count():
                mes.first.click(); page.wait_for_timeout(700)
                obert_abans = page.locator('text=' + t_instancia(lang)).count() > 0
                page.keyboard.press('Escape'); page.wait_for_timeout(600)
                if obert_abans and page.locator('text=' + t_instancia(lang)).count() > 0:
                    fallides.append(f'{lang} · `Esc` NO tanca el modal de posicions')
                else:
                    print(f'  ✓ 4b · {lang} · Esc tanca el modal de posicions')

            # ── 5 · F5 i consola ───────────────────────────────────────────────
            page.reload(wait_until='networkidle')
            page.wait_for_timeout(1800)
            if errors:
                fallides.append(f'{lang} · error de pàgina: {errors[0][:150]}')
            if consola:
                fallides.append(f'{lang} · consola bruta: {consola[0][:150]}')
            # El cercador ha de portar el model, que és el que fa que la cerca sigui del CLIENT.
            if estat['cerques'] and not any(f'model={MID}' in u for u in estat['cerques']):
                fallides.append(f'{lang} · la cerca NO porta ?model= (cercaria el catàleg del tenant)')
            ctx.close()
        b.close()

    print()
    if fallides:
        print('✗ FALLIDES')
        for f in fallides:
            print(f'  · {f}')
        return 1
    print('✓ P0.8 verd · el gest de crear POM propi, als 3 idiomes')
    return 0


if __name__ == '__main__':
    sys.exit(main())
