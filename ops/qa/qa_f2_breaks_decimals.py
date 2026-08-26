"""FUM DE PANTALLA · EL Δ D'UN BREAK ACCEPTA DECIMALS (F2/T2 · 26/08).

## Per què això no es pot provar amb un test de unitat

`num.test.js` ja prova que `parseNum('0,75')` i `parseNum('0.75')` donen 0.75. Però el defecte
**no era la funció**: era que l'input es repintava amb el número que en sortia, o sigui que
`Number('1.')` → `1` esborrava el separador sota els dits i el decimal no s'hi podia escriure
mai. Això només es veu **teclejant tecla a tecla contra el component real**, que és el que fa
aquest fum.

Es reusa el patró de `qa_f4quater_lectura.py`: la QA de navegador contra staging vol un JWT que
l'agent no pot emetre, així que se serveix el bundle REAL de `frontend/dist` i s'stubeja el
payload. El component, el CSS i els tokens són els de producció.

    /tmp/qa-venv/bin/python ops/qa/qa_f2_breaks_decimals.py

Sortida 1 si el camp no reté un separador decimal. Captures a `ops/qa/captures/f2_*.png`.
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
MODEL_ID = 9997
#: Les etiquetes venen de `i18n/ca.json` (`grading.intervals.*`) i es declaren aquí perquè el
#: dia que canviïn, el fum caigui amb un missatge que ho digui — i no amb un valor estrany.
AFEGIR_INTERVAL = 'Afegir un interval de graduació'
DELTA_INTERVAL = 'Δ de l\u2019interval'
CONFIRMAR_INTERVAL = 'Confirmar l\u2019interval'
RUN = ['XS', 'S', 'M', 'L', 'XL']


def fila(n, codi, nom, base, logica, ib=None, breaks=None):
    return {
        'id': n, 'pom_id': n, 'pom_code': codi, 'capa': 'exterior', 'instancia': '',
        'garment': '', 'nom_fitxa': '', 'nom_canonic_model': nom, 'nom_traduit_model': '',
        'nom_en': nom, 'nom_ca': nom, 'abbreviation': codi, 'base_value_cm': base,
        'is_key': False, 'origen': 'MANUAL', 'notes': '', 'graded': {s: base for s in RUN},
        'logica': logica, 'increment_base': ib, 'increment_break': None,
        'talla_break_label': None, 'breaks': breaks or [],
        'step_base_copiada': [], 'regla_origen': 'MANUAL', 'regla_es_resident': True,
    }


# Una LINEAR amb Δ general i sense relleu: la columna «Breaks» hi és editable i buida, que és
# on es prem «+» per obrir un xip nou.
ROWS = [fila(1, 'A', '1/2 chest width', 44, 'LINEAR', ib=2)]

_MODEL = {
    'id': MODEL_ID, 'codi_intern': 'QA-F2-0001', 'nom_prenda': 'QA breaks decimals',
    'temporada': 'FW26', 'any': 2026, 'estat': 'Nou', 'fase': 'Proto',
    'size_run_model': '·'.join(RUN), 'base_size_label': 'S', 'fit_type': 'Regular',
    'target': 'WOMAN', 'construction': 'WOVEN', 'grading_rule_set': 1,
    'grading_rule_set_nom': 'QA', 'garment_type_item': None, 'customer': None,
    'measurements_version': 1, 'tipologia': 'MARCA',
}
_TAULA = {
    'model_id': MODEL_ID, 'codi_intern': 'QA-F2-0001', 'base_size': 'S',
    'size_run': RUN, 'size_run_complet': RUN, 'run_sistema': RUN,
    'sizes_amb_dades': RUN, 'deltes': {}, 'rows': ROWS, 'total_poms': len(ROWS),
    'tancat': False,
    'graduacio': {'font': 'model', 'es_proposta': False, 'rule_set_id': 1,
                  'rule_set_nom': 'QA', 'fit_model': 'Regular'},
}
_PERFIL = {'id': 1, 'username': 'qa', 'nom_complet': 'QA', 'rol_nom': 'admin',
           'capabilities': ['EXECUTE_TASKS', 'CLOSE_GATES', 'CONFIGURE'], 'idioma': 'ca'}
_VOCAB = {'regims_graduacio': [{'codi': c, 'autorable': True, 'nom': c}
                               for c in ('LINEAR', 'STEP', 'FIXED')]}


def _stub(path):
    if '/taula-mesures/' in path:
        return _TAULA
    if '/vocabulari/' in path or 'regims_graduacio' in path:
        return _VOCAB
    if '/peces/' in path:
        return {'peces': []}
    if '/grading-status/' in path:
        return {'te_dades_propagades': True, 'segellada': False, 'version_number': 1,
                'estalitud': None, 'te_regles': True}
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
                                  viewport={'width': 1700, 'height': 950})
        page = ctx.new_page()
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.route('**/*', _handler)
        page.add_init_script(
            "localStorage.setItem('access_token','qa');"
            "localStorage.setItem('fhort.lang','ca')")

        print('\n▸ GRADUACIÓ DEL MODEL · columna «Breaks» (`EditorIntervals`)')
        page.goto(f'{BASE}/models/{MODEL_ID}?tab=Mesures&mode=graduacio',
                  wait_until='networkidle', timeout=45000)
        page.wait_for_timeout(1500)
        cos = page.inner_text('body')
        prova('la superfície munta', '1/2 chest width' in cos or 'QA-F2' in cos, cos[:200])
        page.screenshot(path=str(OUT / 'f2_00_graduacio.png'), full_page=False)

        # ⚠️ ES LOCALITZA PER `aria-label`, MAI PER `.first` D'UN SELECTOR AMPLE. La primera
        # correguda agafava `input[inputmode="decimal"]` i queia sobre el camp Δ BASE de la
        # mateixa fila —que ja porta el 2 del payload— i teclejar-hi «0,75» donava «0,752»: un
        # vermell que semblava del defecte i era de la SONDA. És la lliçó que
        # `qa_f4quater_lectura.py` ja porta escrita sobre l'índex de columna.
        afegeix = page.get_by_label(AFEGIR_INTERVAL)
        prova('hi ha el gest d\'afegir un interval', afegeix.count() > 0,
              f'{afegeix.count()} candidats')
        if afegeix.count() == 0:
            browser.close()
            return 1
        afegeix.first.click()
        page.wait_for_timeout(400)

        delta = page.get_by_label(DELTA_INTERVAL)
        prova('el camp Δ de l\'interval s\'obre', delta.count() == 1,
              f'{delta.count()} camps amb aquesta etiqueta')
        if delta.count() != 1:
            page.screenshot(path=str(OUT / 'f2_ERR_camp.png'))
            browser.close()
            return 1
        prova('el camp Δ neix BUIT (i no amb el Δ base de la fila)', delta.input_value() == '',
              f'«{delta.input_value()}»')

        # ── EL CAS DEL DEFECTE: tecla a tecla, amb COMA ─────────────────────────────────
        delta.click()
        delta.press_sequentially('0,75', delay=60)
        v_coma = delta.input_value()
        prova('amb COMA el camp reté «0,75»', v_coma == '0,75', f'valor real: «{v_coma}»')
        page.screenshot(path=str(OUT / 'f2_01_coma.png'))

        # ── I amb PUNT ──────────────────────────────────────────────────────────────────
        delta.fill('')
        delta.press_sequentially('0.75', delay=60)
        v_punt = delta.input_value()
        prova('amb PUNT el camp reté «0.75»', v_punt == '0.75', f'valor real: «{v_punt}»')
        page.screenshot(path=str(OUT / 'f2_02_punt.png'))

        # ── EL BLUR NORMALITZA A L'IDIOMA (R2) ──────────────────────────────────────────
        page.keyboard.press('Tab')
        page.wait_for_timeout(300)
        v_blur = delta.input_value()
        prova('al blur es normalitza a l\'idioma (ca → coma)', v_blur == '0,75',
              f'valor real: «{v_blur}»')

        # ── I EL ✓ S'HABILITA: el número existeix per al confirm ────────────────────────
        confirma = page.get_by_label(CONFIRMAR_INTERVAL)
        habilitat = confirma.count() > 0 and confirma.first.is_enabled()
        prova('el ✓ de confirmar està habilitat amb un Δ decimal', habilitat)
        page.screenshot(path=str(OUT / 'f2_03_confirmable.png'))
        prova('cap error de consola', not errors, errors[:1])
        browser.close()

    print(f'\n{len(ok)} ✓ · {len(fallits)} ✗')
    if fallits:
        print('FALLITS: ' + ' · '.join(fallits))
    return 1 if fallits else 0


if __name__ == '__main__':
    sys.exit(main())
