"""FUM DE PANTALLA · EL WIZARD D'IMPORTACIÓ PINTA ELS NOMS A DUES LÍNIES (F1/T1 · 26/08).

## Què prova, i per què amb el bundle real

El wizard ensenyava codis pelats («B ·», «BF ·», «BT ·»). El desplegable del catàleg JA rebia
`nom_ca`/`nom_en` RESOLTS del backend i el front només llegia `nom_client` —el camp CRU del
tenant, buit a **103 dels 144 POMs actius** de `fhort`—. Això és un canvi de DIBUIX: cap dada
es mou, i per tant cap test de backend el veu.

🚨 EL BANC ÉS LA POBLACIÓ MAJORITÀRIA REAL: els POMs stubejats tenen `nom_client` BUIT i el nom
al catàleg global. Amb el camp ple, el defecte no es reprodueix i el fum donaria verd sense
mesurar res.

Patró de `qa_f4quater_lectura.py`: bundle REAL de `frontend/dist` + payload stubejat.

    /tmp/qa-venv/bin/python ops/qa/qa_f1_wizard_noms.py

Sortida 1 si una fila del desplegable es queda sense nom. Captures a `captures/f1_*.png`.
"""
import json
import mimetypes
import pathlib
import re
import sys

from playwright.sync_api import sync_playwright

REPO = pathlib.Path(__file__).resolve().parents[2]
DIST = REPO / 'frontend' / 'dist'
OUT = pathlib.Path(__file__).resolve().parent / 'captures'
BASE = 'https://staging.fhorttextile.tech'
MODEL_ID = 9996
RUN = ['XS', 'S', 'M']
TOKEN = 'qa-sessio-f1'

#: 🚨 LA FORMA DELS 103: `nom_client` BUIT, el nom viu al GLOBAL i arriba per `nom_en`/`nom_ca`.
#: Són els codis exactes del símptoma de la formació (POMs 906/908/907 de `fhort`).
CERCA = {
    'results': [
        {'id': 906, 'seccio': 'casa', 'codi_client': 'B', 'nom_client': '',
         'nom_en': 'Foot width', 'nom_ca': 'Ample de peu', 'categoria_nom': '',
         'nivell': 'cataleg', 'client_code': '', 'client_name_en': '', 'client_name_local': ''},
        {'id': 908, 'seccio': 'casa', 'codi_client': 'BF', 'nom_client': '',
         'nom_en': 'Foot length', 'nom_ca': 'Llarg de peu', 'categoria_nom': '',
         'nivell': 'cataleg', 'client_code': '', 'client_name_en': '', 'client_name_local': ''},
        {'id': 907, 'seccio': 'casa', 'codi_client': 'BT', 'nom_client': '',
         'nom_en': 'Leg opening girth', 'nom_ca': 'Contorn de boca de camal',
         'categoria_nom': '', 'nivell': 'cataleg',
         'client_code': '', 'client_name_en': '', 'client_name_local': ''},
    ],
    'count': 3, 'truncat': False,
    'seccions': {'client': {'count': 0, 'mostrats': 0}, 'casa': {'count': 3, 'mostrats': 3}},
}

_MODEL = {
    'id': MODEL_ID, 'codi_intern': 'QA-F1-0001', 'nom_prenda': 'QA wizard noms',
    'temporada': 'FW26', 'any': 2026, 'estat': 'Nou', 'fase': 'Proto',
    'size_run_model': '·'.join(RUN), 'base_size_label': 'S', 'fit_type': 'Regular',
    'target': 'WOMAN', 'construction': 'WOVEN', 'grading_rule_set': None,
    'grading_rule_set_nom': '', 'garment_type_item': None, 'customer': 1,
    'measurements_version': 1, 'tipologia': 'MARCA', 'garment_type_nom': 'Pantaló',
    # El gate del tab (`ModelSheet:1249`) vol `pomReady`; sense ell la pantalla es queda a
    # «Mesures encara no disponibles» i el selector de les tres targetes no arriba a muntar.
    'pom_task_done': True,
}
_PERFIL = {'id': 1, 'username': 'qa', 'nom_complet': 'QA', 'rol_nom': 'admin',
           'capabilities': ['EXECUTE_TASKS', 'CLOSE_GATES', 'CONFIGURE'], 'idioma': 'ca'}
#: Taula BUIDA: és el que fa que `MeasuresEntryPanel` es quedi al SELECTOR, que és on hi ha el
#: gest «Importar taula».
_TAULA = {'model_id': MODEL_ID, 'codi_intern': 'QA-F1-0001', 'base_size': 'S',
          'size_run': RUN, 'size_run_complet': RUN, 'run_sistema': RUN, 'sizes_amb_dades': [],
          'deltes': {}, 'rows': [], 'total_poms': 0, 'tancat': False,
          'graduacio': {'font': 'model', 'es_proposta': False, 'rule_set_id': None,
                        'rule_set_nom': '', 'fit_model': 'Regular'}}
_CRIBRATGE = {'token': TOKEN, 'run_talles_document': RUN, 'header': {}, 'fulls': ['Full1'],
              'full': 'Full1'}
_TALLES = {'ready': True, 'errors': [], 'no_aparellades': [],
           'system_labels': RUN, 'base_size_label': 'S',
           'talla_mapping': [{'document': s, 'model': s} for s in RUN]}
#: Les files del pas 2 — amb el `pom_nom` RESOLT, que és el que F1 fa servir al backend.
_EXTRACCIO = {
    'poms_extrets': [{
        'codi_fitxa': 'B', 'descripcio': '', 'pom_master_id': 906, 'pom_codi': 'B',
        'pom_nom': 'Foot width', 'match_type': 'exact', 'confidence': 'HIGH',
        'values': {s: 10 for s in RUN}, 'tol_minus': None, 'tol_plus': None,
        'seccio': None, 'actiu': True, 'ordre': 0, 'weak_suggestion': None,
        'weak_suggestion_codi': None, 'many_to_one': False,
    }],
    'header': {}, 'base_size': 'S', 'sizes': RUN, 'grading_status': {}, 'avisos': [],
    'fulls': ['Full1'], 'full': 'Full1', 'proposta_peces': None,
    'suggested_valors_mode': 'absoluts',
}


def _stub(path):
    if '/poms/cerca/' in path:
        return CERCA
    if '/import-sessions/cribratge/' in path:
        return _CRIBRATGE
    if '/talles/' in path:
        return _TALLES
    if '/extraccio/' in path:
        return _EXTRACCIO
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
                                  viewport={'width': 1500, 'height': 1000})
        page = ctx.new_page()
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.route('**/*', _handler)
        page.add_init_script(
            "localStorage.setItem('access_token','qa');"
            "localStorage.setItem('fhort.lang','ca')")

        print('\n▸ WIZARD D\'IMPORTACIÓ · desplegable «tria\'n un del catàleg»')
        page.goto(f'{BASE}/models/{MODEL_ID}?tab=Mesures', wait_until='networkidle',
                  timeout=45000)
        page.wait_for_timeout(1200)

        # «Editar POM» → `editing='Mesures'`, i amb la taula VERGE `MeasuresEntryPanel` cau al
        # SELECTOR de les tres targetes, que és on viu el gest d'importar. Amb `pom_task_done`
        # sol, la pantalla es queda a la CONSULTA (que és el comportament correcte del producte:
        # un model definit s'obre per llegir-lo, no per re-mesurar-lo).
        editar = page.get_by_role('button', name=re.compile('editar pom', re.I))
        if editar.count() == 0:
            editar = page.get_by_text(re.compile(r'^Editar POM$', re.I))
        prova('hi ha el gest «Editar POM»', editar.count() > 0)
        if editar.count():
            editar.first.click()
            page.wait_for_timeout(1200)

        # Selector → «Importar taula»
        importa = page.get_by_text(re.compile(r'^Importar', re.I))
        prova('el selector ofereix «Importar taula»', importa.count() > 0,
              '· cos: ' + repr(page.inner_text('body')[-700:]))
        if importa.count() == 0:
            page.screenshot(path=str(OUT / 'f1_ERR_selector.png'), full_page=True)
            browser.close()
            return 1
        importa.first.click()
        page.wait_for_timeout(600)

        # Pas 1 — el fitxer. El contingut és indiferent: el cribratge està stubejat.
        page.locator('input[type="file"]').first.set_input_files({
            'name': 'taula.xlsx', 'mimeType':
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'buffer': b'PK\x03\x04qa'})
        page.wait_for_timeout(800)
        # El pas 1 té DOS gestos, no un: primer «Analitzar talles» (el cribratge, que és qui
        # obre la sessió i proposa l'aparellament) i després «Continuar» (que el confirma i
        # dispara l'extracció). Amb un de sol el wizard es queda al pas 1 amb el fitxer posat.
        analitza = page.get_by_role('button', name=re.compile('analitzar', re.I))
        prova('el pas 1 ofereix «Analitzar talles»', analitza.count() > 0)
        if analitza.count():
            analitza.first.click()
            page.wait_for_timeout(1500)
        cont = page.get_by_role('button', name=re.compile('continu', re.I))
        prova('el pas 1 ofereix «Continuar» un cop aparellades les talles', cont.count() > 0,
              '· cos: ' + repr(page.inner_text('body')[-400:]))
        if cont.count():
            cont.first.click()
            page.wait_for_timeout(1800)
        prova('s\'arriba al pas 2', 'Foot width' in page.inner_text('body'),
              '· cos: ' + repr(page.inner_text('body')[-900:]))
        page.screenshot(path=str(OUT / 'f1_00_pas2.png'))

        # El desplegable del catàleg
        afegeix = page.get_by_role('button', name=re.compile('cat.leg', re.I))
        prova('hi ha «Afegir POM del catàleg»', afegeix.count() > 0)
        if afegeix.count() == 0:
            page.screenshot(path=str(OUT / 'f1_ERR_addpom.png'))
            browser.close()
            return 1
        afegeix.first.click()
        page.wait_for_timeout(1200)

        # ── EL QUE ES MESURA: cada fila diu CODI + NOM, i el nom no és el `nom_client` buit ──
        # Les files del desplegable: els botons que porten un dels codis del catàleg stubejat.
        # ⚠️ La llista ha d'incloure'ls TOTS TRES — amb un patró parcial, la fila que en queda
        # fora no es mesura i el seu nom podria faltar sense que res cantés.
        files = page.locator('button').filter(
            has_text=re.compile(r'Foot width|Foot length|Leg opening girth'))
        prova('el desplegable pinta les TRES files del catàleg', files.count() == 3,
              f'{files.count()} files')
        # ⚠️ ES MESURA DINS DEL DESPLEGABLE, no al `body`. «Foot width» també surt a la llista
        # de files del pas 2 (hi arriba per `pom_nom`, que és la meitat BACKEND de F1), o sigui
        # que contra el cos sencer la prova del nom canònic passava fins i tot amb el front
        # vell — un fals verd amb el defecte viu a la pantalla.
        text = '\n'.join(files.all_inner_texts())
        for codi, en, ca in [('B', 'Foot width', 'Ample de peu'),
                             ('BF', 'Foot length', 'Llarg de peu'),
                             ('BT', 'Leg opening girth', 'Contorn de boca de camal')]:
            prova(f'«{codi}» diu el nom canònic ({en})', en in text)
            prova(f'«{codi}» diu el nom d\'usuari a la 2a línia ({ca})', ca in text)
        # I EL SÍMPTOMA, dit sobre cada fila: cap pot quedar-se amb el codi i el punt volat i
        # res al darrere. Es mesura fila a fila i no sobre el text ajuntat — sobre l'ajuntat,
        # amb les files buides el patró no hi és i la prova passaria per absència.
        pelades = [t for t in files.all_inner_texts()
                   if not re.search(r'·\s*\S', t)]
        prova('cap fila es queda amb el codi pelat («B · »)', not pelades, pelades)
        page.screenshot(path=str(OUT / 'f1_01_dues_linies.png'))
        prova('cap error de consola', not errors, errors[:1])
        browser.close()

    print(f'\n{len(ok)} ✓ · {len(fallits)} ✗')
    if fallits:
        print('FALLITS: ' + ' · '.join(fallits))
    return 1 if fallits else 0


if __name__ == '__main__':
    sys.exit(main())
