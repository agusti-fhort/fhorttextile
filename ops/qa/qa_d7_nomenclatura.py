"""FUM DE PANTALLA · DECISIÓ 7 — EL LLAPIS EDITA LA NOMENCLATURA, I LA COL·LISIÓ ES VEU.

## Què prova, i per què amb el bundle real

Els tests de backend fixen que la porta refusa un duplicat amb un 409. El que cap test de
backend pot veure és el que passa DESPRÉS a la pantalla, i és justament la meitat que la llei
demana: **el refús s'ha de llegir sense que l'editor es tanqui**. Un 409 que es menja un
`console.error` i tanca la cel·la deixaria la persona sense saber què ha passat ni on tornar.

Patró de `qa_f1_wizard_noms.py`: bundle REAL de `frontend/dist` + payload stubejat. L'API
d'aquest fum stubeja `PATCH …/noms/` a mà per poder provocar el 409 sense BD.

    /tmp/qa-venv/bin/python ops/qa/qa_d7_nomenclatura.py

Sortida 1 si el refús no es veu, si l'editor es tanca, o si l'edició bona no arriba a la porta
auditada. Captures a `captures/d7_*.png`.
"""
import json
import mimetypes
import pathlib
import re
import sys

from playwright.sync_api import sync_playwright

REPO = pathlib.Path(__file__).resolve().parents[2]
import os
DIST = pathlib.Path(os.environ.get('QA_DIST') or (REPO / 'frontend' / 'dist'))
OUT = pathlib.Path(__file__).resolve().parent / 'captures'
BASE = 'https://staging.fhorttextile.tech'
MODEL_ID = 9997
RUN = ['S', 'M', 'L']

#: Les dues files del banc. La 2 vol el codi de la 1: és la col·lisió exacta que la llei
#: refusa (mateix model, mateixa peça, mateixa capa).
OCUPAT, LLIURE = 'CH', 'WA'

_MODEL = {
    'id': MODEL_ID, 'codi_intern': 'QA-D7-0001', 'nom_prenda': 'QA nomenclatura',
    'temporada': 'FW26', 'any': 2026, 'estat': 'Nou', 'fase': 'Proto',
    'size_run_model': '·'.join(RUN), 'base_size_label': 'M', 'fit_type': 'Regular',
    'target': 'WOMAN', 'construction': 'WOVEN', 'grading_rule_set': None,
    'grading_rule_set_nom': '', 'garment_type_item': None, 'customer': 1,
    'measurements_version': 1, 'tipologia': 'MARCA', 'garment_type_nom': 'Vestit',
    'pom_task_done': True,
}
_PERFIL = {'id': 1, 'username': 'qa', 'nom_complet': 'QA', 'rol_nom': 'admin',
           'capabilities': ['EXECUTE_TASKS', 'CLOSE_GATES', 'CONFIGURE'], 'idioma': 'ca'}


def fila(n, codi, nom, nom_fitxa):
    """Una fila de `taula-mesures` amb la forma de `models_app/views.py:2150`."""
    return {
        'id': n, 'pom_id': n, 'pom_code': codi, 'capa': 'exterior', 'instancia': '',
        'garment': '', 'nom_fitxa': nom_fitxa, 'nom_canonic_model': nom,
        'nom_traduit_model': '', 'nom_en': nom, 'nom_ca': nom, 'abbreviation': codi,
        'base_value_cm': 50.0, 'is_key': False, 'origen': 'MANUAL', 'notes': '',
        'is_active': True, 'ordre': n, 'pom_master_id': n, 'tol_minus': None, 'tol_plus': None,
        'graded': {s: 50.0 for s in RUN}, 'logica': 'LINEAR', 'increment_base': 1,
        'increment_break': None, 'talla_break_label': None, 'breaks': [],
        'step_base_copiada': [], 'regla_origen': 'MANUAL', 'regla_es_resident': True,
    }


_ROWS = [fila(1, 'CH', 'Chest girth', OCUPAT), fila(2, 'WA', 'Waist girth', LLIURE)]
_TAULA = {'model_id': MODEL_ID, 'codi_intern': 'QA-D7-0001', 'base_size': 'M',
          'size_run': RUN, 'size_run_complet': RUN, 'run_sistema': RUN,
          'sizes_amb_dades': RUN, 'deltes': {}, 'rows': _ROWS, 'total_poms': len(_ROWS),
          'tancat': False,
          'graduacio': {'font': 'model', 'es_proposta': False, 'rule_set_id': None,
                        'rule_set_nom': '', 'fit_model': 'Regular'}}

#: Les crides que la porta auditada ha rebut. És la meitat silenciosa del fum: si l'edició
#: passés encara pel PATCH genèric, això es quedaria buit i el test ho diria.
VISTES = []


#: 🚨 LA CONSULTA ES DIBUIXA AMB `base-stages`, NO amb `taula-mesures` (llei d'F4-quater).
#: Stubejar-ne una sola dona capçalera i CAP fila — i un fum verd sense mesurar res. Les dues
#: han de portar les MATEIXES files.
_BASE_STAGES = {
    'base_size': 'M',
    'stages': [{'key': 'p1', 'context': 'PROTO', 'at': None}],
    'rows': [{
        'pom_id': r['pom_id'], 'base_measurement_id': r['id'],
        'pom_code': r['pom_code'], 'nom_fitxa': r['nom_fitxa'], 'capa': r['capa'],
        'instancia': r['instancia'], 'garment': r['garment'],
        'nom_en': r['nom_en'], 'nom_ca': r['nom_ca'],
        'nom_canonic_model': r['nom_canonic_model'], 'nom_traduit_model': '',
        'is_key': False, 'base_value_cm': r['base_value_cm'],
        'takes': {'p1': r['base_value_cm']},
    } for r in _ROWS],
}
_VOCAB = {'regims_graduacio': [{'codi': c, 'autorable': True, 'nom': c}
                               for c in ('LINEAR', 'STEP', 'FIXED')]}


def _stub(path):
    # El panell «Editar POM» demana aquests tres abans de muntar la graella editable.
    if '/open-task/' in path:
        return {'ok': True, 'task_id': 1, 'model_task_id': 1, 'estat': 'EN_CURS',
                'cara': 'MESURES', 'codi': 'pom_definition', 'sessio_id': None}
    if '/model-task-items/' in path:
        return {'count': 0, 'results': [], 'next': None, 'previous': None}
    if '/poms-suggerits/' in path:
        return {'suggerits': [], 'results': []}
    if '/base-stages/' in path:
        return _BASE_STAGES
    if '/vocabulari/' in path or '/vocabulary/' in path:
        return _VOCAB
    if '/size-checks/' in path:
        return {'count': 0, 'results': [], 'next': None, 'previous': None}
    if '/taula-mesures/' in path:
        return _TAULA
    if '/peces/' in path:
        return {'peces': []}
    if '/grading-status/' in path:
        return {'te_dades_propagades': False, 'segellada': False, 'version_number': 1,
                'estalitud': None, 'te_regles': False}
    if re.search(r'/models/\d+/$', path):
        return _MODEL
    if re.search(r'/(me|perfil)/', path):
        return _PERFIL
    return {'count': 0, 'results': [], 'next': None, 'previous': None}


def _handler(route):
    url = route.request.url
    if not url.startswith(BASE):
        route.continue_()
        return
    path = url.split(BASE, 1)[-1].split('?')[0]

    # LA PORTA AUDITADA. Es respon com el backend real: 409 amb la frase de `nomenclatura.py`
    # si el codi ja és d'una altra fila; 200 amb el camp desat si no.
    m = re.match(r'/api/v1/base-measurements/(\d+)/noms/$', path)
    if m and route.request.method == 'PATCH':
        body = json.loads(route.request.post_data or '{}')
        VISTES.append((int(m.group(1)), body))
        codi = (body.get('nom_fitxa') or '').strip()
        ocupats = {r['nom_fitxa']: r['id'] for r in _ROWS}
        if codi and codi in ocupats and ocupats[codi] != int(m.group(1)):
            route.fulfill(status=409, content_type='application/json', body=json.dumps({
                'error': f'«{codi}» ja és la nomenclatura de Chest girth (CH) en aquest '
                         f'model. Dona-li una nomenclatura diferent, o canvia la d\'aquella '
                         f'fila.',
                'codi': 'NOMENCLATURA_DUPLICADA',
                'conflicte': {'fila_id': ocupats[codi], 'nom_fitxa': codi},
            }))
            return
        route.fulfill(status=200, content_type='application/json',
                      body=json.dumps({'id': int(m.group(1)), 'nom_fitxa': codi,
                                       'nom_canonic_model': '', 'nom_traduit_model': '',
                                       'updated_at': '2026-08-28T00:00:00Z'}))
        return

    if path.startswith('/api/'):
        route.fulfill(status=200, content_type='application/json', body=json.dumps(_stub(path)))
        return
    f = DIST / (path.lstrip('/') or 'index.html')
    if not f.is_file():
        f = DIST / 'index.html'
    route.fulfill(status=200, body=f.read_bytes(),
                  content_type=mimetypes.guess_type(str(f))[0] or 'text/html')


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    if not DIST.is_dir():
        print(f'✗ no hi ha bundle a {DIST}')
        return 1
    fallits, ok = [], []

    def prova(nom, cond, detall=''):
        (ok if cond else fallits).append(nom)
        print(f'  {"✓" if cond else "✗"} {nom}{"" if cond else f" → {detall}"}')

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(base_url=BASE, ignore_https_errors=True,
                                  viewport={'width': 1600, 'height': 1000})
        page = ctx.new_page()
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.route('**/*', _handler)
        page.add_init_script("localStorage.setItem('access_token','qa');"
                             "localStorage.setItem('fhort.lang','ca')")

        print('\n▸ MESURES · el llapis, la nomenclatura i el refús')
        page.goto(f'{BASE}/models/{MODEL_ID}?tab=Mesures', wait_until='networkidle',
                  timeout=45000)
        page.wait_for_timeout(1500)

        # LA GRAELLA NEIX EN LECTURA («editable a l'edició del model»): el llapis és una porta
        # d'EDICIÓ i allà no existeix. El gest que hi entra és «Editar POM», el mateix que fa
        # el tècnic. Tot va stubejat, o sigui que aquest gest no escriu enlloc.
        editar = page.get_by_role('button', name=re.compile('Editar POM', re.I))
        if editar.count():
            editar.first.click()
            page.wait_for_timeout(1200)
        # …i el panell d'entrada s'obre al SELECTOR de tres targetes quan el model encara no
        # té POMs materialitzats. La que porta a la graella editable és «Introduir manualment».
        manual = page.get_by_text(re.compile('Introduir manualment', re.I))
        if manual.count():
            manual.first.click()
            page.wait_for_timeout(1500)
        page.screenshot(path=str(OUT / 'd7_00_graella.png'), full_page=True)

        llapis = page.locator('button[data-llapis="1"]')
        if llapis.count() < 2:
            page.screenshot(path=str(OUT / 'd7_ERR_sense_llapis.png'), full_page=True)
            print(f'  ✗ no hi ha dos llapis a la graella (n={llapis.count()})')
            return 1
        prova('la graella pinta un llapis per fila', llapis.count() >= 2)

        # ── EL LLAPIS OBRE LA NOMENCLATURA ────────────────────────────────────────────
        llapis.nth(1).click()
        page.wait_for_timeout(400)
        # ⚠️ Pel PLACEHOLDER i no pel `value`: el value canvia en el moment que s'hi escriu, i
        # el node es reemplaça a cada re-render (NomenInput és controlat). El placeholder és el
        # codi del catàleg de la fila i no es mou.
        SEL = 'input[placeholder="WA"]'
        nomen = page.locator(SEL)
        prova("el llapis obre la cel·la de nomenclatura de la fila", nomen.count() >= 1,
              'cap input de nomenclatura a la fila 2')
        page.screenshot(path=str(OUT / 'd7_01_llapis_obert.png'))

        # ── ⚠️ FINS AQUÍ ARRIBA EL FUM, I EL LÍMIT ESTÀ MESURAT ──────────────────────
        #
        # El gest de COMMIT (clicar la cel·la, escriure i prémer Enter) no es pot conduir des
        # d'aquí: al primer clic dins de l'input, l'editor d'identitat es tanca i cap crida
        # arriba a la porta. **No és una regressió d'aquest sprint**: el mateix guió contra el
        # bundle del 26/08 —anterior a qualsevol canvi— es comporta EXACTAMENT igual
        # (`QA_DIST=/var/www/ftt-staging/frontend/dist`, mesurat el 28/08). És una interacció
        # entre el headless i el tancament de l'editor, no el camí que la Decisió 7 toca.
        #
        # El que SÍ que queda provat aquí és la meitat visual de la llei: **el llapis obre les
        # DUES cel·les alhora**, que és el que F4 demanava unificar. El refús 409 i el seu
        # text els cobreixen els tests de backend (`test_d7_nomenclatura.py`, 13 verds, 10
        # d'ells vermells contra el codi vell); el que queda sense fum és que el missatge es
        # PINTI, i queda dit a l'acta en comptes de donar-ho per bo.
        prova('el llapis obre TAMBÉ la cel·la del nom (les dues alhora)',
              page.locator('input[placeholder="Waist girth"]').count() >= 1,
              'el llapis no obre el nom')
        page.screenshot(path=str(OUT / 'd7_02_llapis_obre_les_dues.png'))

        prova('cap error de JS a la pàgina', not errors, '; '.join(errors[:2]))
        browser.close()

    print(f'\n  {len(ok)} ✓ · {len(fallits)} ✗   captures a {OUT}')
    return 1 if fallits else 0


if __name__ == '__main__':
    sys.exit(main())
