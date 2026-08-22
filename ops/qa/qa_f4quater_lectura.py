"""QA DE LA PRESENTACIÓ UNIFICADA DELS BREAKS EN LECTURA (F4-QUATER).

## Què prova, i per què amb el bundle real

L'sprint substitueix les DUES columnes (`Δ break` + `Talla break`) per UNA de sola amb la frase
d'interval a **totes** les superfícies de lectura. Això és un canvi de DIBUIX: cap valor no es
mou, i per tant el banc de motor (`banc_paritat_1383.py`) hi dona verd digui el que digui la
pantalla. El que pot trencar-se aquí només es veu MIRANT, i és exactament el que va fer saltar
el passi visual del 21/08.

Es reusa el patró de `qa_f4bis_columna_breaks.py` (i abans `qa_mount_modelsheet.py`): la QA de
navegador contra staging vol un JWT que l'agent **no pot emetre**, així que se serveix el
**bundle REAL de `frontend/dist`** —el mateix que nginx publica— i s'stubeja només el payload.
El component, el CSS i els tokens són els de producció.

⚠️ El que això NO prova: la fitxa (Q8b). El seu builder viu dins de `TechSheetEditor.jsx` amb
Konva i React a sobre i no es pot muntar des d'aquí; la seva meitat comprovable té dos bancs
propis —`taulesQ8.test.js` (la frase, els noms de camp, la regla del silenci) i
`ops/qa/q8_taules_fitxa.mjs` (el pressupost de mil·límetres contra un payload real del
servidor)—. Queda dit al report.

## Les dues superfícies i les tres captures d'Agus

    Mesures-consulta ....  /models/<id>?tab=Mesures   → `CheckMeasureEditor readOnly`
    Escalat ..............  /models/<id>/escalat       → `PropagatedEditor`

## Ús

    /tmp/qa-venv/bin/python ops/qa/qa_f4quater_lectura.py

Codi de sortida 1 si alguna superfície no diu la frase o si en queda cap rastre de les dues
columnes velles. Captures a `ops/qa/captures/f4quater_*.png`.
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
MODEL_ID = 9998
RUN = ['XS', 'S', 'M', 'L', 'XL']


def fila(n, codi, nom, base, logica, ib=None, brk=None, lbl=None, breaks=None):
    """Una fila de `taula-mesures` amb la forma exacta de `models_app/views.py:2150`."""
    graded = {s: base for s in RUN}
    return {
        'id': n, 'pom_id': n, 'pom_code': codi, 'capa': 'exterior', 'instancia': '',
        'garment': '', 'nom_fitxa': '', 'nom_canonic_model': nom, 'nom_traduit_model': '',
        'nom_en': nom, 'nom_ca': nom, 'abbreviation': codi, 'base_value_cm': base,
        'is_key': False, 'origen': 'MANUAL', 'notes': '', 'graded': graded,
        'logica': logica, 'increment_base': ib, 'increment_break': brk,
        'talla_break_label': lbl, 'breaks': breaks or [],
        'step_base_copiada': [], 'regla_origen': 'MANUAL', 'regla_es_resident': True,
    }


#: Les formes que l'sprint ha de saber dir. Són les del banc 1383 i les del 1384.
ROWS = [
    # ① LINEAR sense relleu → «—»
    fila(1, 'EK', 'Neck width', 22, 'LINEAR', ib=1),
    # ② EL BREAK LLEGAT (les 21 regles vives del banc 1383). La BD desa `M`; el motor gradua
    #    `M..XL` amb +3. La frase ha de dir `M→XL +3` — MAI `S→…`, que seria la volta de
    #    document i mouria la corba una talla sencera a l'ull de qui la llegeix.
    fila(2, 'A', '1/2 chest width', 44, 'LINEAR', ib=2, brk=3, lbl='M'),
    # ③ DOS INTERVALS EXPLÍCITS (la forma del 1384)
    fila(3, 'D', 'Bottom width', 59, 'LINEAR', ib=1.5, breaks=[
        {'inici': 'S', 'final': 'L', 'delta': 3},
        {'inici': 'XL', 'final': 'XL', 'delta': 4}]),
    # ④ TRES INTERVALS — el cas on el pressupost d'amplada mana i les superfícies divergeixen
    #    A POSTA: la consulta els lletreja tots, l'Escalat en diu un i compta la resta.
    fila(4, 'I', 'Sleeve length', 43.5, 'LINEAR', ib=0.2, breaks=[
        {'inici': 'XS', 'final': 'S', 'delta': 0.5},
        {'inici': 'M', 'final': 'L', 'delta': 1},
        {'inici': 'XL', 'final': 'XL', 'delta': 1.5}]),
    # ⑤ REGLA DEL SILENCI ① — FIXED amb break residual: les VUIT files del banc 1383.
    fila(5, 'G1', 'Bottom finish height', 2, 'FIXED', ib=0, brk=0, lbl='M'),
    # ⑥ REGLA DEL SILENCI ② — el llegat que repeteix el Δ general no trenca res.
    fila(6, 'E5', 'Sleeve opening', 12, 'LINEAR', ib=2, brk=2, lbl='M'),
    # ⑦ Δ NEGATIU: el signe és la meitat de la xifra.
    fila(7, 'B', 'Back length', 62, 'LINEAR', ib=1, breaks=[
        {'inici': 'L', 'final': 'XL', 'delta': -1.5}]),
    # ⑧ 🚨 LA F DEL BANC 1383, AMB ELS SEUS DOS INTERVALS REALS (pk=13396, llegits de la BD).
    #    És el cas exacte de les captures d'Agus de les 22:16: Δ general 0, `M→L +2` i `XL→XL +1`.
    #    Amb la forma vella —sostre + comptador— aquesta fila es pintava `M→L +2,0 +1` i era
    #    INDISTINGIBLE de la mateixa regla amb el segon tram a +3. Aquí es fixa que ara es
    #    diuen les dues coses, cadascuna a la seva línia, i que la segona porta EL SEU Δ.
    fila(8, 'F', 'Front length', 110.5, 'LINEAR', ib=0, breaks=[
        {'inici': 'M', 'final': 'L', 'delta': 2},
        {'inici': 'XL', 'final': 'XL', 'delta': 1}]),
]

_MODEL = {
    'id': MODEL_ID, 'codi_intern': 'QA-F4QUATER-0001', 'nom_prenda': 'QA lectura breaks',
    'temporada': 'FW26', 'any': 2026, 'estat': 'Nou', 'fase': 'Proto',
    'size_run_model': '·'.join(RUN), 'base_size_label': 'S', 'fit_type': 'Regular',
    'target': 'WOMAN', 'construction': 'WOVEN', 'grading_rule_set': 1,
    'grading_rule_set_nom': 'QA', 'garment_type_item': None, 'customer': None,
    'measurements_version': 1, 'tipologia': 'MARCA',
}
_TAULA = {
    'model_id': MODEL_ID, 'codi_intern': 'QA-F4QUATER-0001', 'base_size': 'S',
    'size_run': RUN, 'size_run_complet': RUN, 'run_sistema': RUN,
    'sizes_amb_dades': RUN, 'deltes': {}, 'rows': ROWS, 'total_poms': len(ROWS),
    'tancat': False,
    'graduacio': {'font': 'model', 'es_proposta': False, 'rule_set_id': 1,
                  'rule_set_nom': 'QA', 'fit_model': 'Regular'},
}
# ── LA FONT DE LES FILES DE LA CONSULTA ─────────────────────────────────────────────────────
# 🚨 LA CONSULTA NO ES DIBUIXA AMB `taula-mesures`: les FILES surten de `base-stages` i la REGLA
# se'ls ajunta des de `taula-mesures` per la clau `(pom, garment)` (`checkSource.load` +
# `reglaPerPom`). Stubejar només `taula-mesures` pinta la capçalera i CAP fila — que és el que
# va passar a la primera correguda, i que hauria donat verd a totes les proves de capçalera
# sense haver mesurat ni una cel·la.
_BASE_STAGES = {
    'base_size': 'S',
    'stages': [{'key': 'p1', 'context': 'PROTO', 'at': None}],
    'rows': [{
        'pom_id': r['pom_id'], 'base_measurement_id': r['pom_id'],
        'pom_code': r['pom_code'], 'nom_fitxa': '', 'capa': r['capa'],
        'instancia': r['instancia'], 'garment': r['garment'],
        'nom_en': r['nom_en'], 'nom_ca': r['nom_ca'],
        'nom_canonic_model': '', 'nom_traduit_model': '',
        'is_key': False, 'base_value_cm': r['base_value_cm'],
        'takes': {'p1': r['base_value_cm']},
    } for r in ROWS],
}

_PERFIL = {'id': 1, 'username': 'qa', 'nom_complet': 'QA', 'rol_nom': 'admin',
           'capabilities': ['EXECUTE_TASKS', 'CLOSE_GATES', 'CONFIGURE'], 'idioma': 'ca'}
_VOCAB = {'regims_graduacio': [{'codi': c, 'autorable': True, 'nom': c}
                               for c in ('LINEAR', 'STEP', 'FIXED')]}


def _stub(path):
    if '/base-stages/' in path:
        return _BASE_STAGES
    if '/taula-mesures/' in path:
        return _TAULA
    if '/size-checks/' in path:
        return {'count': 0, 'results': [], 'next': None, 'previous': None}
    if '/grading-status/' in path:
        return {'te_dades_propagades': True, 'segellada': False, 'version_number': 1,
                'estalitud': None, 'te_regles': True}
    if '/vocabulari/' in path or 'regims_graduacio' in path:
        return _VOCAB
    if '/peces/' in path:
        return {'peces': []}
    if re.search(r'/models/\d+/$', path):
        return _MODEL
    if re.search(r'/(me|perfil)/', path):
        return _PERFIL
    return {'count': 0, 'results': [], 'next': None, 'previous': None}


def _handler(route):
    url = route.request.url
    # El catch-all deixa passar el que no és nostre (la fulla d'icones Tabler ve d'un CDN;
    # servint-li `index.html` com a CSS el bundle es queda sense glifs — v. F4-BIS).
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


def _caps(page):
    return [c.strip() for c in page.locator('thead th').all_inner_texts()]


def _idx_breaks(page):
    """L'índex (1-based) de la columna «Breaks», deduït de la CAPÇALERA i mai escrit a mà.

    ⚠️ ES BUSCA DINS DE LA FILA DE `thead` QUE LA CONTÉ, no sobre tots els `th` de la taula.
    L'Escalat porta una PRIMERA fila de grups («POMS DEFINITS · REGLA DE GRADUACIÓ · MESURES PER
    TALLA») que la consulta no té: comptant `th` en pla, l'índex sortia desplaçat de tres i la
    prova mesurava una columna de mesures —i, com que allà hi ha xifres, no petava: donava
    vermell dient «44.0», que és el símptoma d'un índex equivocat, no d'un dibuix equivocat.
    """
    for fila in page.locator('thead tr').all():
        cel_les = [c.strip().upper() for c in fila.locator('th').all_inner_texts()]
        if 'BREAKS' in cel_les:
            return cel_les.index('BREAKS') + 1
    raise AssertionError(f'cap columna «Breaks» a la capçalera: {_caps(page)}')


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    if not DIST.is_dir():
        print(f'✗ no hi ha bundle a {DIST} — fes `npm run build` primer')
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

        # ══ SUPERFÍCIE ① · MESURES-CONSULTA ════════════════════════════════════════════════
        print('\n▸ MESURES-CONSULTA (`CheckMeasureEditor readOnly` → `EditableTable`)')
        page.goto(f'{BASE}/models/{MODEL_ID}?tab=Mesures',
                  wait_until='networkidle', timeout=45000)
        page.wait_for_timeout(1500)

        cos = page.inner_text('body')
        prova('la superfície munta', 'Neck width' in cos or 'QA-F4QUATER' in cos, cos[:160])
        prova('cap error de consola', not errors, errors[:1])

        caps = _caps(page)
        prova('la capçalera diu «Breaks»', any(c.upper() == 'BREAKS' for c in caps), caps)
        prova('«Talla break» ja no hi és',
              not any('TALLA BREAK' in c.upper() for c in caps), caps)
        prova('«Delta break» ja no hi és',
              not any('DELTA BREAK' in c.upper() or 'Δ BREAK' in c.upper() for c in caps), caps)

        # ⚠️ LA FILA ES BUSCA PEL TEXT DE LA SEVA CEL·LA DE POM, NO AMB `td:text-is()`: la cel·la
        # del codi porta controls i espais al voltant a les dues superfícies i el selector exacte
        # no hi casa mai (hi va perdre una correguda). Es compara el text ja retallat.
        def cel(codi):
            i = _idx_breaks(page)
            files = page.locator('tbody tr')
            for k in range(files.count()):
                tds = files.nth(k).locator('td')
                if any(t.strip() == codi for t in tds.all_inner_texts()[:4]):
                    return tds.nth(i - 1)
            raise AssertionError(f'cap fila amb el POM «{codi}»')

        def txt(codi):
            return cel(codi).inner_text().replace('\n', ' ').strip()

        # Les LÍNIES d'una cel·la de «Breaks», que és el que aquest tram estableix: un tram per
        # línia. Es llegeixen dels `<span>` fills (consulta i Escalat apilen igual) i, si no
        # n'hi ha, del text partit per salts — així la prova val encara que el vestit canviï.
        def linies(codi):
            c = cel(codi)
            fills = c.locator('span > span')
            if fills.count():
                return [x.strip() for x in fills.all_inner_texts() if x.strip()]
            return [x.strip() for x in c.inner_text().split('\n') if x.strip()]

        # 🚨 LA PROVA QUE MÉS IMPORTA: el llegat es diu en convenció de MOTOR.
        t2 = txt('A')
        prova('② el break llegat diu «M→XL +3»',
              'M' in t2 and 'XL' in t2 and '+3' in t2 and '→' in t2, t2)
        prova('🚨 ② l\'inici NO s\'ha desplaçat a S (la volta de document ha mort)',
              not re.match(r'^S\s*→', t2), t2)

        prova('③ dos intervals → DUES línies, mai una frase amb « · »',
              len(linies('D')) == 2 and '·' not in txt('D'), linies('D'))

        t4 = txt('I')
        prova('④ tres intervals: la consulta els diu TOTS TRES', len(linies('I')) == 3, t4)
        prova('④ …i cap línia porta un comptador: el que segueix el rang és sempre un Δ',
              all(re.fullmatch(r'\S+ [+\-−][\d.,]+', l) for l in linies('I')), linies('I'))

        prova('⑤ REGLA DEL SILENCI · FIXED amb residu llegat → «—»', txt('G1') == '—', txt('G1'))
        prova('⑥ REGLA DEL SILENCI · llegat = Δ general → «—»', txt('E5') == '—', txt('E5'))
        prova('① sense relleu → «—»', txt('EK') == '—', txt('EK'))
        prova('⑦ el Δ negatiu porta el seu signe',
              any('-1.5' in l or '−1.5' in l for l in linies('B')), linies('B'))

        # ── 🚨 ⑧ LA F D'AGUS: UN TRAM PER LÍNIA, I EL SEGON AMB EL SEU RANG ────────────────
        lf = linies('F')
        prova('🚨 ⑧ la F diu DUES línies, no una frase concatenada', len(lf) == 2, lf)
        prova('🚨 ⑧ el 1r tram porta el seu rang i el seu Δ', lf and lf[0] == 'M→L +2', lf)
        prova('🚨 ⑧ el 2n tram porta EL SEU RANG (no un comptador «+1» solt)',
              len(lf) > 1 and lf[1] == 'XL +1', lf)
        prova('🚨 ⑧ el rang d\'una talla sola va SENSE fletxa a lectura',
              len(lf) > 1 and '→' not in lf[1], lf)

        page.screenshot(path=OUT / 'f4quater_1_mesures_consulta.png', full_page=False)

        # ══ SUPERFÍCIE ② · ESCALAT ═════════════════════════════════════════════════════════
        print('\n▸ ESCALAT (`PropagatedEditor` → `escalatRuleLeadCols`)')
        errors.clear()
        page.goto(f'{BASE}/models/{MODEL_ID}/escalat', wait_until='networkidle', timeout=45000)
        page.wait_for_timeout(1800)

        cos = page.inner_text('body')
        prova('la superfície munta', 'Neck width' in cos or 'Sleeve length' in cos, cos[:160])
        prova('cap error de consola', not errors, errors[:1])

        caps = _caps(page)
        prova('la capçalera diu «Breaks»', any(c.upper() == 'BREAKS' for c in caps), caps)
        prova('«Talla break» ja no hi és',
              not any('TALLA BREAK' in c.upper() for c in caps), caps)
        prova('«Δ break» ja no hi és',
              not any(c.upper().replace(' ', '') in ('ΔBREAK', 'DELTABREAK') for c in caps), caps)

        t2 = txt('A')
        prova('② el break llegat diu «M→XL +3»', '→' in t2 and 'M' in t2 and 'XL' in t2, t2)
        prova('🚨 ② l\'inici NO s\'ha desplaçat a S', not re.match(r'^S\s*→', t2), t2)

        # 🚨 CAP SOSTRE, TAMPOC AQUÍ. Abans l'Escalat en deia UN i comptava la resta (`+2`), i
        # aquell `+2` era un comptador amb la gramàtica d'un Δ. Apilats hi caben tots tres
        # sense reclamar ni un píxel: l'amplada la mana la línia més llarga, no la suma.
        prova('④ tres intervals: l\'Escalat també els diu TOTS TRES', len(linies('I')) == 3,
              linies('I'))
        prova('④ …i cap línia porta un comptador', 
              all(re.fullmatch(r'\S+ [+\-−][\d.,]+', l) for l in linies('I')), linies('I'))
        lf = linies('F')
        prova('🚨 ⑧ la F d\'Agus, també apilada i amb el rang del 2n tram',
              len(lf) == 2 and '→' in lf[0] and '→' not in lf[1] and lf[1].endswith('1,0'), lf)

        prova('⑤ REGLA DEL SILENCI · FIXED amb residu llegat → «—»', txt('G1') == '—', txt('G1'))
        prova('⑥ REGLA DEL SILENCI · llegat = Δ general → «—»', txt('E5') == '—', txt('E5'))

        page.screenshot(path=OUT / 'f4quater_2_escalat.png', full_page=False)
        browser.close()

    print(f'\n{len(ok)} verdes · {len(fallits)} vermelles')
    if fallits:
        print('  ✗ ' + '\n  ✗ '.join(fallits))
    return 1 if fallits else 0


if __name__ == '__main__':
    sys.exit(main())
