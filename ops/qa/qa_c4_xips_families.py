"""FUM DE PANTALLA · ELS XIPS D'INSTÀNCIA ES DESBLOQUEGEN ENTRE FAMÍLIES (C4 · 26/08).

## Què prova, i per què amb el bundle real

La llei de famílies (Agus, 26/08) diu **excloents DINS de família, combinables ENTRE totes**.
Fins avui sis dels deu slugs de posició no tenien família i per tant s'excloïen amb tot: prémer
«Top» apagava «Left». **No s'ha construït cap UI nova** — el mecanisme dels xips ja hi era i
llegeix `subeix` del diccionari; el que canvia és la DADA que el diccionari publica.

🚨 EL DICCIONARI D'AQUEST FUM NO ESTÀ ESCRIT A MÀ: és el payload REAL que
`GET /api/v1/mesures/diccionari/` emet des del backend nou (`ops/qa/_diccionari_families.json`,
generat contra el schema `fhort`). Amb un stub escrit a ull, el fum provaria la meva idea del
contracte i no el contracte.

Patró de `qa_f4quater_lectura.py` / `qa_f1_wizard_noms.py`: bundle REAL de `frontend/dist` +
payload stubejat, perquè la QA de navegador vol un JWT que l'agent no pot emetre.

    /tmp/qa-venv/bin/python ops/qa/qa_c4_xips_families.py

Sortida 1 si dues famílies s'exclouen o si una família no s'exclou dins seu.
Captures a `ops/qa/captures/c4_*.png`.
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
MODEL_ID = 9995
RUN = ['XS', 'S', 'M']
TOKEN = 'qa-sessio-c4'

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
    'id': MODEL_ID, 'codi_intern': 'QA-C4-0001', 'nom_prenda': 'QA xips families',
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
_TAULA = {'model_id': MODEL_ID, 'codi_intern': 'QA-C4-0001', 'base_size': 'S',
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


DICCIONARI = json.loads(r'''{
 "capes": [
  {
   "slug": "exterior",
   "nom_en": "Shell",
   "nom_ca": "Exterior",
   "nom_es": "Exterior",
   "is_system": true,
   "pendent_revisio": false,
   "display_order": 1
  },
  {
   "slug": "folre",
   "nom_en": "Lining",
   "nom_ca": "Folre",
   "nom_es": "Forro",
   "is_system": true,
   "pendent_revisio": false,
   "display_order": 2
  },
  {
   "slug": "entretela",
   "nom_en": "Interfacing",
   "nom_ca": "Entretela",
   "nom_es": "Entretela",
   "is_system": true,
   "pendent_revisio": false,
   "display_order": 3
  },
  {
   "slug": "farciment",
   "nom_en": "Padding",
   "nom_ca": "Farciment",
   "nom_es": "Relleno / Guata",
   "is_system": true,
   "pendent_revisio": false,
   "display_order": 4
  },
  {
   "slug": "reforc",
   "nom_en": "Underlining",
   "nom_ca": "Reforç",
   "nom_es": "Refuerzo",
   "is_system": true,
   "pendent_revisio": false,
   "display_order": 5
  },
  {
   "slug": "fornitura",
   "nom_en": "Trim",
   "nom_ca": "Fornitura",
   "nom_es": "Fornitura",
   "is_system": true,
   "pendent_revisio": false,
   "display_order": 6
  }
 ],
 "eixos": [
  {
   "clau": "POSICIO",
   "nom_en": "Position",
   "nom_ca": "Posició",
   "nom_es": "Posición"
  },
  {
   "clau": "ESTAT",
   "nom_en": "State",
   "nom_ca": "Estat",
   "nom_es": "Estado"
  }
 ],
 "subeixos": [
  "PECA",
  "BANDA",
  "VERTICALITAT",
  "COSTURA",
  "LINIA",
  "ESTAT"
 ],
 "instancies": {
  "POSICIO": [
   {
    "slug": "left",
    "nom_en": "Left",
    "nom_ca": "Esquerra",
    "nom_es": "Izquierda",
    "is_system": true,
    "pendent_revisio": false,
    "display_order": 1,
    "eix": "POSICIO",
    "sufix": "L",
    "subeix": "BANDA"
   },
   {
    "slug": "right",
    "nom_en": "Right",
    "nom_ca": "Dreta",
    "nom_es": "Derecha",
    "is_system": true,
    "pendent_revisio": false,
    "display_order": 2,
    "eix": "POSICIO",
    "sufix": "R",
    "subeix": "BANDA"
   },
   {
    "slug": "top",
    "nom_en": "Top",
    "nom_ca": "Superior",
    "nom_es": "Superior",
    "is_system": true,
    "pendent_revisio": false,
    "display_order": 3,
    "eix": "POSICIO",
    "sufix": "T",
    "subeix": "VERTICALITAT"
   },
   {
    "slug": "bottom",
    "nom_en": "Bottom",
    "nom_ca": "Inferior",
    "nom_es": "Inferior",
    "is_system": true,
    "pendent_revisio": false,
    "display_order": 4,
    "eix": "POSICIO",
    "sufix": "BM",
    "subeix": "VERTICALITAT"
   },
   {
    "slug": "cf",
    "nom_en": "CF",
    "nom_ca": "CF",
    "nom_es": "CF",
    "is_system": true,
    "pendent_revisio": false,
    "display_order": 5,
    "eix": "POSICIO",
    "sufix": "CF",
    "subeix": "LINIA"
   },
   {
    "slug": "cb",
    "nom_en": "CB",
    "nom_ca": "CB",
    "nom_es": "CB",
    "is_system": true,
    "pendent_revisio": false,
    "display_order": 6,
    "eix": "POSICIO",
    "sufix": "CB",
    "subeix": "LINIA"
   },
   {
    "slug": "side",
    "nom_en": "Side seam",
    "nom_ca": "Costura lateral",
    "nom_es": "Costura lateral",
    "is_system": true,
    "pendent_revisio": false,
    "display_order": 7,
    "eix": "POSICIO",
    "sufix": "S",
    "subeix": "COSTURA"
   },
   {
    "slug": "waistband_seam",
    "nom_en": "Waistband seam",
    "nom_ca": "Costura de cinturilla",
    "nom_es": "Costura de pretina",
    "is_system": true,
    "pendent_revisio": false,
    "display_order": 8,
    "eix": "POSICIO",
    "sufix": "",
    "subeix": "COSTURA"
   },
   {
    "slug": "front",
    "nom_en": "Front",
    "nom_ca": "Front",
    "nom_es": "Front",
    "is_system": true,
    "pendent_revisio": false,
    "display_order": 9,
    "eix": "POSICIO",
    "sufix": "F",
    "subeix": "PECA"
   },
   {
    "slug": "back",
    "nom_en": "Back",
    "nom_ca": "Back",
    "nom_es": "Back",
    "is_system": true,
    "pendent_revisio": false,
    "display_order": 10,
    "eix": "POSICIO",
    "sufix": "B",
    "subeix": "PECA"
   }
  ],
  "ESTAT": [
   {
    "slug": "relaxed",
    "nom_en": "Relaxed",
    "nom_ca": "Relaxada",
    "nom_es": "Relajada",
    "is_system": true,
    "pendent_revisio": false,
    "display_order": 1,
    "eix": "ESTAT",
    "sufix": "",
    "subeix": "ESTAT"
   },
   {
    "slug": "extended",
    "nom_en": "Extended",
    "nom_ca": "Estirada",
    "nom_es": "Estirada",
    "is_system": true,
    "pendent_revisio": false,
    "display_order": 2,
    "eix": "ESTAT",
    "sufix": "",
    "subeix": "ESTAT"
   }
  ]
 },
 "regles": {
  "sufix_separador": "",
  "sufix_ordre": "base+sufix",
  "capa_al_codi": false,
  "instancia_separador": "-",
  "instancia_unica": ""
 }
}''')


def _stub(path):
    if '/mesures/diccionari/' in path:
        return DICCIONARI
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

        # ── OBRIR EL PANELL DE RESOLUCIÓ, que és on viu `ColumnatIdentitat` ────────────
        canvia = page.get_by_text(re.compile(r'canvia el vincle', re.I))
        prova('la fila ofereix «canvia el vincle»', canvia.count() > 0,
              '· cos: ' + repr(page.inner_text('body')[-500:]))
        if canvia.count() == 0:
            page.screenshot(path=str(OUT / 'c4_ERR_panell.png'), full_page=True)
            browser.close()
            return 1
        canvia.first.click()
        page.wait_for_timeout(900)
        page.screenshot(path=str(OUT / 'c4_00_columnat.png'))

        def xip(nom):
            """Un xip pel seu TEXT exacte, mai per posició.

            ⚠️ NO per `get_by_role(name=...)`: l'`aria-label` d'aquestes píndoles és una FRASE
            («Marca aquesta mesura com a Left», `instancia.tip_aquesta`) i no l'etiqueta, i
            l'aria-label mana sobre el nom accessible. Buscar-hi «Left» no trobava res i el fum
            deia que faltaven els dotze xips **quan hi eren tots** — un vermell de la sonda.
            """
            return page.locator('button').filter(
                has_text=re.compile(rf'^{re.escape(nom)}$'))

        def ences(nom):
            return xip(nom).first.get_attribute('aria-pressed') == 'true'

        # Els deu xips de posició i els dos d'estat hi han de ser tots.
        tots = ['Left', 'Right', 'Top', 'Bottom', 'CF', 'CB', 'Side seam', 'Waistband seam',
                'Front', 'Back', 'Relaxed', 'Extended']
        falten = [n for n in tots if xip(n).count() == 0]
        prova('hi són els 12 xips del vocabulari', not falten, f'falten: {falten}')
        if falten:
            page.screenshot(path=str(OUT / 'c4_ERR_xips.png'), full_page=True)
            browser.close()
            return 1

        # ══ 1 · COMBINABLES ENTRE FAMÍLIES ════════════════════════════════════════════════
        xip('Front').first.click(); page.wait_for_timeout(250)
        xip('Left').first.click(); page.wait_for_timeout(250)
        prova('Front + Left CONVIUEN (peça + banda)', ences('Front') and ences('Left'),
              f"Front={ences('Front')} Left={ences('Left')}")
        page.screenshot(path=str(OUT / 'c4_01_front_left.png'))

        # 🚨 EL SÍMPTOMA DE LA FORMACIÓ: «Top» apagava «Left» perquè no tenia família.
        xip('Top').first.click(); page.wait_for_timeout(250)
        prova('Top NO apaga Left ni Front (verticalitat és família pròpia)',
              ences('Top') and ences('Left') and ences('Front'),
              f"Top={ences('Top')} Left={ences('Left')} Front={ences('Front')}")

        # `side seam` afegible a qualsevol: la COSTURA és família pròpia i no binomial.
        xip('Side seam').first.click(); page.wait_for_timeout(250)
        prova('Side seam s\'afegeix sense apagar res',
              ences('Side seam') and ences('Top') and ences('Left') and ences('Front'),
              f"Side={ences('Side seam')} Top={ences('Top')} Left={ences('Left')}")

        # La LÍNIA és família PRÒPIA i no és la peça: `front` + `cf` és redundant i LEGAL.
        xip('CF').first.click(); page.wait_for_timeout(250)
        prova('CF conviu amb Front (la línia NO és la peça; la redundància és legal)',
              ences('CF') and ences('Front'), f"CF={ences('CF')} Front={ences('Front')}")

        xip('Relaxed').first.click(); page.wait_for_timeout(250)
        prova('l\'estat es creua amb les cinc famílies de posició',
              ences('Relaxed') and ences('CF') and ences('Side seam') and ences('Top')
              and ences('Left') and ences('Front'))
        page.screenshot(path=str(OUT / 'c4_02_sis_families.png'))

        # ══ 2 · EXCLOENTS DINS DE FAMÍLIA ═════════════════════════════════════════════════
        xip('Back').first.click(); page.wait_for_timeout(250)
        prova('Back apaga Front (mateixa família PEÇA)', ences('Back') and not ences('Front'))
        xip('Right').first.click(); page.wait_for_timeout(250)
        prova('Right apaga Left (BANDA)', ences('Right') and not ences('Left'))
        xip('Bottom').first.click(); page.wait_for_timeout(250)
        prova('Bottom apaga Top (VERTICALITAT)', ences('Bottom') and not ences('Top'))
        xip('Waistband seam').first.click(); page.wait_for_timeout(250)
        prova('Waistband seam apaga Side seam (COSTURA)',
              ences('Waistband seam') and not ences('Side seam'))
        xip('CB').first.click(); page.wait_for_timeout(250)
        prova('CB apaga CF (LÍNIA)', ences('CB') and not ences('CF'))
        xip('Extended').first.click(); page.wait_for_timeout(250)
        prova('Extended apaga Relaxed (ESTAT)', ences('Extended') and not ences('Relaxed'))
        # …i els sis substituts segueixen tots encesos alhora: cap família n'ha apagat una altra.
        prova('les SIS famílies conviuen després de substituir-les totes',
              all(ences(n) for n in ['Back', 'Right', 'Bottom', 'Waistband seam', 'CB',
                                     'Extended']))
        page.screenshot(path=str(OUT / 'c4_03_substituides.png'))

        # ══ 3 · L'ORDRE CANÒNIC, A LA PANTALLA ════════════════════════════════════════════
        # El rètol de la fila diu la instància composta; ha de sortir en l'ordre de la llei.
        cos = page.inner_text('body')
        prova('el rètol compon en ordre canònic (peça abans que banda)',
              'Back · Right' in cos, '· no s\'hi ha trobat «Back · Right»')

        prova('cap error de consola', not errors, errors[:1])
        browser.close()

    print(f'\n{len(ok)} ✓ · {len(fallits)} ✗')
    if fallits:
        print('FALLITS: ' + ' · '.join(fallits))
    return 1 if fallits else 0


if __name__ == '__main__':
    sys.exit(main())
