"""QA de la COLUMNA «BREAKS» amb xips d'interval (F4-BIS) — els 6 estats del mockup.

## Per què aquest fum i no la pantalla viva

La QA de navegador contra staging vol un JWT que l'agent **no pot emetre** (el classificador
de permisos denega `RefreshToken.for_user`, provat el 21/08 per dos camins). Els dos tokens
que queden al disc són de juliol i del 6 d'agost: caducats.

El camí que SÍ que executa el codi de debò és el de `qa_mount_modelsheet.py`: servir el
**bundle REAL de `frontend/dist`** —el mateix que nginx publica— i stubejar `/api/` sencera
des del procés. No cal token, i el que es pinta és el component real amb el seu CSS real. El
que aquí es stubeja és NOMÉS el payload de `taula-mesures`: la columna, el component, els
tokens i el bundle són els de producció.

⚠️ El que això NO prova: que el servidor accepti el payload. La porta `valida_breaks` ja té
banc propi (`fhort.pom.test_tram_f_intervals`) i la QA d'staging del tram F la va exercir per
la vista real. Aquí es prova la MEITAT QUE FALTAVA: que la pantalla dibuixi els sis estats i
que el solapament no es pugui construir amb els controls.

## Els sis estats (mockup `docs/ordres/proposta_ux_intervals_mesures.html`)

    ①  LINEAR sense relleu ................ només [+]
    ②  break d'1 tram DESAT ............... xip «M → XL +3» (convenció de MOTOR, sense volta)
    ③  dos intervals ...................... dos xips + [+]
    ④  un xip EN EDICIÓ ................... dos selectors + Δ + ✓/✕
    ⑤  al màxim (3) ....................... tres xips + «màx. 3», i el [+] desapareix
    ⑥  FIXED .............................. columna inerta

## Ús

    /tmp/qa-venv/bin/python ops/qa/qa_f4bis_columna_breaks.py

Codi de sortida 1 si algun estat no es pinta o si el solapament es pot teclejar.
Captures a `ops/qa/captures/f4bis_*.png`.
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
MODEL_ID = 9999
RUN = ['XS', 'S', 'M', 'L', 'XL']


def fila(n, codi, nom, base, logica, ib=None, brk=None, lbl=None, breaks=None):
    """Una fila de `taula-mesures` amb la forma exacta de `models_app/views.py:2150`."""
    return {
        'id': n, 'pom_id': n, 'pom_code': codi, 'capa': 'exterior', 'instancia': '',
        'garment': '', 'nom_fitxa': '', 'nom_canonic_model': nom, 'nom_traduit_model': '',
        'nom_en': nom, 'nom_ca': nom, 'abbreviation': codi, 'base_value_cm': base,
        'is_key': False, 'origen': 'MANUAL', 'notes': '', 'graded': {},
        'logica': logica, 'increment_base': ib, 'increment_break': brk,
        'talla_break_label': lbl, 'breaks': breaks or [],
        'step_base_copiada': [], 'regla_origen': 'MANUAL', 'regla_es_resident': True,
    }


#: Els sis estats, en l'ordre del mockup i amb les seves xifres.
ROWS = [
    fila(1, 'EK', 'Neck width', 22, 'LINEAR', ib=0),                          # ①
    fila(2, 'A', '1/2 chest width', 44, 'LINEAR', ib=2, brk=3, lbl='M'),      # ②  ← LLEGAT
    fila(3, 'D', 'Bottom width', 59, 'LINEAR', ib=1.5, breaks=[               # ③
        {'inici': 'S', 'final': 'L', 'delta': 3},
        {'inici': 'XL', 'final': 'XL', 'delta': 4}]),
    fila(4, 'J', '1/2 Bicep width', 16.6, 'LINEAR', ib=0.3),                  # ④  ← s'hi clica
    fila(5, 'I', 'Sleeve length', 43.5, 'LINEAR', ib=0.2, breaks=[            # ⑤
        {'inici': 'XS', 'final': 'S', 'delta': 0.5},
        {'inici': 'M', 'final': 'L', 'delta': 1},
        {'inici': 'XL', 'final': 'XL', 'delta': 1.5}]),
    fila(6, 'G1', 'Bottom finish height', 2, 'FIXED'),                        # ⑥
    # ⑦ (21/08) LA REGLA DEL SILENCI · LINEAR amb break llegat que repeteix el general: mut.
    # És la forma de les 8 files del banc que van fer saltar el passi visual d'Agus.
    fila(7, 'E5', 'Sleeve opening', 12, 'LINEAR', ib=0, brk=0, lbl='M'),
    # I una FIXED amb residus llegats: la columna calla i la dada es queda a la BD.
    fila(8, 'U', 'Under placket', 4, 'FIXED', ib=0, brk=0, lbl='M'),
]

_MODEL = {
    'id': MODEL_ID, 'codi_intern': 'QA-F4BIS-0001', 'nom_prenda': 'QA breaks',
    'temporada': 'FW26', 'any': 2026, 'estat': 'Nou', 'fase': 'Proto',
    'size_run_model': '·'.join(RUN), 'base_size_label': 'S', 'fit_type': 'Regular',
    'target': 'WOMAN', 'construction': 'WOVEN', 'grading_rule_set': 1,
    'grading_rule_set_nom': 'QA', 'garment_type_item': None, 'customer': None,
    'measurements_version': 1, 'tipologia': 'MARCA',
}
_TAULA = {
    'model_id': MODEL_ID, 'codi_intern': 'QA-F4BIS-0001', 'base_size': 'S',
    'size_run': RUN, 'size_run_complet': RUN,
    # El run del SISTEMA: és el que la columna ha d'oferir als pickers (llei S24b).
    'run_sistema': RUN,
    'sizes_amb_dades': ['S'], 'deltes': {}, 'rows': ROWS, 'total_poms': len(ROWS),
    'tancat': False,
    'graduacio': {'font': 'model', 'es_proposta': False, 'rule_set_id': 1,
                  'rule_set_nom': 'QA', 'fit_model': 'Regular'},
}
_PERFIL = {'id': 1, 'username': 'qa', 'nom_complet': 'QA', 'rol_nom': 'admin',
           'capabilities': ['EXECUTE_TASKS', 'CLOSE_GATES', 'CONFIGURE'], 'idioma': 'ca'}

# ── LA SEGONA SUPERFÍCIE D'AUTORIA: «Generar regles» (el joc del catàleg) ────────────────────
# Mateixes sis formes de regla que a Graduació: el que s'hi comprova és que la columna sigui LA
# MATEIXA i no una còpia que s'hi assembli.
_SIZE_SYSTEM = {
    'id': 1, 'codi': 'QA_RUN', 'nom': 'QA run', 'actiu': True,
    'talles': [{'id': i + 1, 'etiqueta': e, 'ordre': i} for i, e in enumerate(RUN)],
}


def regla(n, codi, nom, logica, ib=None, brk=None, lbl=None, breaks=None):
    return {
        'id': n, 'pom': n, 'pom_codi': codi, 'pom_abbreviation': codi,
        'pom_nom': nom, 'pom_nom_en': nom, 'logica': logica, 'increment_base': ib,
        'increment': None, 'increment_break': brk, 'talla_break_label': lbl,
        'breaks': breaks or [], 'valors_step': None, 'rule_set': 1, 'actiu': True,
    }


_JOC = {
    'id': 1, 'nom': 'QA-F4BIS', 'codi': 'QA-F4BIS', 'actiu': True, 'is_system_default': False,
    'size_system': 1, 'applies_to': [], 'targets_codis': [], 'construction_codi': None,
    'fit_type_codi': None, 'garment_group_codi': None, 'n_regles': 8,
    'regles': [
        regla(1, 'EK', 'Neck width', 'LINEAR', ib=0),
        regla(2, 'A', '1/2 chest width', 'LINEAR', ib=2, brk=3, lbl='M'),      # LLEGAT
        regla(3, 'D', 'Bottom width', 'LINEAR', ib=1.5, breaks=[
            {'inici': 'S', 'final': 'L', 'delta': 3},
            {'inici': 'XL', 'final': 'XL', 'delta': 4}]),
        regla(4, 'J', '1/2 Bicep width', 'LINEAR', ib=0.3),
        regla(5, 'I', 'Sleeve length', 'LINEAR', ib=0.2, breaks=[
            {'inici': 'XS', 'final': 'S', 'delta': 0.5},
            {'inici': 'M', 'final': 'L', 'delta': 1},
            {'inici': 'XL', 'final': 'XL', 'delta': 1.5}]),
        regla(6, 'G1', 'Bottom finish height', 'FIXED'),
        regla(7, 'E5', 'Sleeve opening', 'LINEAR', ib=0, brk=0, lbl='M'),
        regla(8, 'U', 'Under placket', 'FIXED', ib=0, brk=0, lbl='M'),
    ],
}
# ⚠️ LA FORMA LA MANA `elementsDe`: el vocabulari és `{<clau>: [...]}`, no `{elements: [...]}`.
# Amb la clau equivocada `regimsAutorables` queda buit i el desplegable només ofereix el règim
# que la fila ja porta — que és exactament el que va fer petar la prova ⑧ la primera vegada.
_VOCAB = {'regims_graduacio': [{'codi': c, 'autorable': True, 'nom': c}
                               for c in ('LINEAR', 'STEP', 'FIXED')]}


def _stub(path):
    if '/grading-rule-sets/' in path:
        return {'count': 1, 'results': [_JOC], 'next': None, 'previous': None}
    if '/size-systems/' in path:
        return {'count': 1, 'results': [_SIZE_SYSTEM], 'next': None, 'previous': None}
    if '/taula-mesures/' in path:
        return _TAULA
    if '/grading-status/' in path:
        return {'te_dades_propagades': False, 'segellada': False, 'version_number': None,
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
    # ⚠️ EL CATCH-ALL S'HA DE DEIXAR PASSAR EL QUE NO ÉS NOSTRE. La fulla d'icones Tabler ve
    # d'un CDN (`index.html:8`), i servint-li `index.html` com a CSS el bundle es queda SENSE
    # cap glif: els [+], ✓ i ✕ desapareixen de les captures i els botons només-icona es
    # queden sense caixa. Va passar a la primera correguda.
    if not url.startswith(BASE):
        route.continue_()
        return
    path = url.split(BASE, 1)[-1].split('?')[0]
    if path.startswith('/api/'):
        route.fulfill(status=200, content_type='application/json',
                      body=json.dumps(_stub(path)))
        return
    f = DIST / (path.lstrip('/') or 'index.html')
    if not f.is_file():
        f = DIST / 'index.html'
    route.fulfill(status=200, body=f.read_bytes(),
                  content_type=mimetypes.guess_type(str(f))[0] or 'text/html')


def _col_breaks(page):
    """L'índex (1-based) de la columna «Breaks» a la taula que hi ha a pantalla.

    Es dedueix de la CAPÇALERA i no es fixa a mà: les dues superfícies tenen ordres de columna
    diferents —a «Generar regles» l'última cel·la és el botó d'inactivar, no els xips— i un
    índex escrit a mà hauria mesurat la columna equivocada donant verd igualment.
    """
    caps = page.locator('thead th').all_inner_texts()
    for i, c in enumerate(caps):
        if 'BREAK' in c.upper():
            return i + 1
    raise AssertionError(f'cap columna «Breaks» a la capçalera: {caps}')


def _cel_la(page, codi):
    """La cel·la «Breaks» de la fila d'un POM."""
    return page.locator(
        f'tbody tr:has(td:text-is("{codi}")) td:nth-child({_col_breaks(page)})')


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
                                  viewport={'width': 1500, 'height': 900})
        page = ctx.new_page()
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.route('**/*', _handler)
        page.add_init_script(
            "localStorage.setItem('access_token','qa');"
            "localStorage.setItem('fhort.lang','ca')")

        page.goto(f'{BASE}/models/{MODEL_ID}?tab=Mesures&mode=graduacio',
                  wait_until='networkidle', timeout=45000)
        page.wait_for_timeout(1200)

        cos = page.inner_text('body')
        prova('la superfície munta', 'QA-F4BIS-0001' in cos or 'Neck width' in cos, cos[:160])
        prova('cap error de consola', not errors, errors[:1])

        # ── LES DUES COLUMNES VELLES HAN MARXAT ─────────────────────────────────────────────
        caps = page.locator('thead th').all_inner_texts()
        prova('la capçalera diu «Breaks»', any('BREAK' in c.upper() for c in caps), caps)
        prova('«Talla break» ja no hi és',
              not any('TALLA BREAK' in c.upper() for c in caps), caps)
        prova('són 8 columnes, no 9', len(caps) == 8, len(caps))

        # ── ① LINEAR sense relleu: només [+] ────────────────────────────────────────────────
        c1 = _cel_la(page, 'EK')
        prova('① sense relleu: cap xip i un [+]',
              c1.locator('span:has(button)').count() == 0
              and c1.locator('button:not([disabled])').count() == 1)
        c1.screenshot(path=OUT / 'f4bis_1_sense_relleu.png')

        # ── ② EL BREAK D'1 TRAM ES PINTA COM A INTERVAL SENCER ──────────────────────────────
        # 🚨 L'ETIQUETA NO ES DESPLAÇA: la BD desa `M` (convenció de MOTOR) i el xip diu `M`.
        # Amb el desplaçament de document diria `S` i mouria la corba una talla sencera.
        t2 = _cel_la(page, 'A').inner_text().replace('\n', ' ').strip()
        prova('② break d\'1 tram → «M → XL +3»',
              'M' in t2 and 'XL' in t2 and '+3' in t2 and '→' in t2, t2)
        prova('② l\'inici NO s\'ha desplaçat a S', not re.match(r'^S\s*→', t2), t2)
        _cel_la(page, 'A').screenshot(path=OUT / 'f4bis_2_break_llegat.png')

        # ── ③ DOS INTERVALS ────────────────────────────────────────────────────────────────
        t3 = _cel_la(page, 'D').inner_text().replace('\n', ' ')
        prova('③ dos xips: «S → L +3» i «XL → XL +4»',
              'S' in t3 and 'L' in t3 and '+3' in t3 and '+4' in t3, t3)
        # Estat 4 del mockup: inici=final es pinta AMB fletxa igualment (gramàtica única).
        prova('③ inici=final porta fletxa igualment («XL → XL»)',
              t3.count('→') == 2, t3)
        _cel_la(page, 'D').screenshot(path=OUT / 'f4bis_3_dos_intervals.png')

        # ── ⑤ AL MÀXIM: tres xips, «màx. 3» i cap [+] ──────────────────────────────────────
        c5 = _cel_la(page, 'I')
        t5 = c5.inner_text().replace('\n', ' ')
        prova('⑤ al màxim: el rètol «màx. 3» hi és', 'màx. 3' in t5, t5)
        prova('⑤ al màxim: el [+] ha desaparegut',
              c5.locator('button[title*="Afegir"]').count() == 0, t5)
        c5.screenshot(path=OUT / 'f4bis_5_maxim.png')

        # ── ⑥ FIXED: COLUMNA BUIDA DEL TOT ─────────────────────────────────────────────────
        # ⚠️ CONTRACTE ACTUALITZAT (Agus, 21/08). Aquí s'asseia que el [+] hi era APAGAT, que és
        # el que dibuixava el mockup. La regla del silenci el retira: sota un règim que no
        # gradua la columna calla sencera —ni xips ni [+]—, perquè un control apagat en una
        # fila que no té res a dir només convida a preguntar-se què hi fa.
        c6 = _cel_la(page, 'G1')
        prova('⑥ FIXED: cap xip i cap [+] — la columna calla sencera',
              c6.locator('button').count() == 0 and c6.inner_text().strip() == '',
              c6.inner_html()[:160])
        c6.screenshot(path=OUT / 'f4bis_6_fixed.png')

        # ── ④ EDICIÓ INLINE + LA IMPOSSIBILITAT DE SOLAPAR ─────────────────────────────────
        # S'obre a la fila D, que JA té dos intervals: així el que els selectors ofereixen es
        # pot contrastar amb el que queda lliure de debò.
        _cel_la(page, 'D').locator('button[title*="Afegir"]').click()
        page.wait_for_timeout(250)
        c4 = _cel_la(page, 'D')
        sels = c4.locator('select')
        prova('④ l\'edició inline obre DOS selectors i un Δ',
              sels.count() == 2 and c4.locator('input').count() == 1, sels.count())

        # 🚨 LA PROVA QUE MÉS IMPORTA: amb S→L i XL→XL ocupats, l'única talla lliure és XS.
        opcions_inici = sels.nth(0).locator('option').all_inner_texts()
        prova('🚨 l\'inici NOMÉS ofereix talles lliures (XS)',
              opcions_inici == ['XS'], opcions_inici)
        opcions_final = sels.nth(1).locator('option').all_inner_texts()
        prova('🚨 el final s\'atura abans del tram ocupat (XS)',
              opcions_final == ['XS'], opcions_final)
        c4.screenshot(path=OUT / 'f4bis_4_edicio_inline.png')

        # El ✓ està apagat mentre no hi hagi Δ: un interval a mitges no entra a la regla.
        conf = c4.locator('button[title*="Confirmar"]')
        prova('④ el ✓ està apagat sense Δ', conf.first.is_disabled())
        c4.locator('input').first.fill('0,8')
        page.wait_for_timeout(150)
        prova('④ amb Δ, el ✓ s\'encén', not _cel_la(page, 'D').locator(
            'button[title*="Confirmar"]').first.is_disabled())
        _cel_la(page, 'D').locator('button[title*="Confirmar"]').first.click()
        page.wait_for_timeout(250)
        t4 = _cel_la(page, 'D').inner_text().replace('\n', ' ')
        prova('④ confirmat: el tercer xip hi és («XS → XS +0.8»)',
              '+0.8' in t4 and t4.count('→') == 3, t4)
        prova('④ i ara la fila és al màxim: apareix «màx. 3»', 'màx. 3' in t4, t4)

        # ── LA FILA SENCERA, per al report ─────────────────────────────────────────────────
        page.locator('table').first.screenshot(path=OUT / 'f4bis_0_taula_sencera.png')

        # ── TREURE UN XIP ──────────────────────────────────────────────────────────────────
        _cel_la(page, 'D').locator('button[title*="Treure"]').first.click()
        page.wait_for_timeout(250)
        t7 = _cel_la(page, 'D').inner_text().replace('\n', ' ')
        prova('el ✕ treu el xip i torna a sortir el [+]',
              t7.count('→') == 2 and 'màx. 3' not in t7, t7)

        # ── ⑧ DESAR UN FIXED NETEJA EL RELLEU · el PAYLOAD, no només la pantalla ───────────
        # El fum captura el cos del POST: sense això es podria comprovar que la columna calla i
        # no que la neteja arriba a viatjar, que és la meitat que de debò treu el fòssil.
        pagats = []
        page.route('**/regim/', lambda r: (pagats.append(r.request.post_data),
                                           r.fulfill(status=200, content_type='application/json',
                                                     body='{}')))
        fila_d = page.locator('tbody tr:has(td:text-is("D"))')
        fila_d.locator('select').first.select_option('FIXED')
        page.wait_for_timeout(200)
        page.get_by_role('button', name='Gravar').first.click()
        page.wait_for_timeout(700)
        cos_env = pagats[0] if pagats else ''
        prova('⑧ desar un FIXED envia la NETEJA (breaks buits + llegats a null)',
              '"breaks":[]' in cos_env and '"increment_break":null' in cos_env
              and '"talla_break_label":null' in cos_env, cos_env or '(cap POST)')
        page.unroute('**/regim/')
        page.reload(wait_until='networkidle')
        page.wait_for_timeout(900)

        # ── ⑦ LA REGLA DEL SILENCI ─────────────────────────────────────────────────────────
        c7 = _cel_la(page, 'E5')
        prova('⑦ LINEAR amb break llegat MUT (+0 sobre general 0): cap xip, però el [+] hi és',
              '→' not in c7.inner_text()
              and c7.locator('button[title*="Afegir"]').count() == 1, c7.inner_text())
        c7.screenshot(path=OUT / 'f4bis_10_llegat_mut.png')
        cU = _cel_la(page, 'U')
        prova('⑦ FIXED amb residus llegats: la columna calla sencera',
              cU.locator('button').count() == 0 and cU.inner_text().strip() == '',
              cU.inner_html()[:160])

        # ══ LA SEGONA SUPERFÍCIE: «Generar regles» ═════════════════════════════════════════
        # 🔑 La prova no és que «també funcioni»: és que sigui LA MATEIXA COLUMNA. Les dues
        # taules tenen amplades, capçaleres i estat propis, i el precedent de la casa és que
        # dues còpies que s'assemblen se separen el mateix dia.
        page.goto(f'{BASE}/poms/grading', wait_until='networkidle', timeout=45000)
        page.wait_for_timeout(900)
        # El joc s'obre pel botó «Editar» de la seva fila (`Fila`, :1265), no pel nom.
        page.get_by_role('button', name='Editar').first.click()
        page.wait_for_timeout(700)

        caps2 = page.locator('thead th').all_inner_texts()
        prova('«Generar regles»: la capçalera diu «Breaks»',
              any('BREAK' in c.upper() for c in caps2), caps2)
        prova('«Generar regles»: «Δ break» i «Talla break» han marxat',
              not any('TALLA BREAK' in c.upper() for c in caps2) and len(caps2) == 7, caps2)

        t2b = _cel_la(page, 'A').inner_text().replace('\n', ' ')
        prova('«Generar regles»: el break d\'1 tram també es pinta «M → XL +3»',
              'M' in t2b and 'XL' in t2b and '+3' in t2b and '→' in t2b, t2b)
        t5b = _cel_la(page, 'I').inner_text().replace('\n', ' ')
        prova('«Generar regles»: al màxim surt «màx. 3» i cap [+]',
              'màx. 3' in t5b
              and _cel_la(page, 'I').locator('button[title*="Afegir"]').count() == 0, t5b)
        c6b = _cel_la(page, 'G1')
        prova('«Generar regles»: FIXED també calla sencera',
              c6b.locator('button').count() == 0 and c6b.inner_text().strip() == '',
              c6b.inner_html()[:160])

        # El solapament, també impossible aquí: amb S→L i XL→XL ocupats només queda XS.
        _cel_la(page, 'D').locator('button[title*="Afegir"]').click()
        page.wait_for_timeout(250)
        sels2 = _cel_la(page, 'D').locator('select')
        prova('🚨 «Generar regles»: l\'inici només ofereix les talles lliures (XS)',
              sels2.nth(0).locator('option').all_inner_texts() == ['XS'],
              sels2.nth(0).locator('option').all_inner_texts())
        page.locator('table').first.screenshot(path=OUT / 'f4bis_7_generar_regles.png')

        ctx.close()
        browser.close()

    print()
    print(f'  captures a {OUT}')
    if fallits:
        print(f'✗ {len(fallits)} de {len(ok) + len(fallits)}: {fallits}')
        return 1
    print(f'✓ {len(ok)}/{len(ok)} — els sis estats es pinten i el solapament no es pot teclejar')
    return 0


if __name__ == '__main__':
    sys.exit(main())
