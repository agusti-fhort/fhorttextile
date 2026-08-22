"""QA de la SUB-PESTANYA «VIGENT» de l'Escalat — la corba del model té vista pròpia.

## El defecte que això mesura

`/models/<id>` → Escalat prometia «consulta de l'escalat vigent» i obria la PRESA. I la presa
no és la corba: les seves teòriques són un CLON congelat de la `GradingVersion` que hi havia
quan es va obrir (`utils/cellaEscalat`: `teorica = presa.teoric ?? vigent`). Amb una presa de
la v6 viva, la columna «Mesura» ensenyava la v6 mentre el model ja anava per la v9 — i el
teòric vigent NOMÉS es podia veure creant una presa NOVA, o sigui escrivint al domini per
poder mirar.

## Per què aquest fum i no la pantalla viva

La QA de navegador contra staging vol un JWT que l'agent **no pot emetre** (v.
`qa_f4bis_columna_breaks.py`). El camí que SÍ que executa el codi de debò és servir el bundle
REAL de `frontend/dist` —el mateix que nginx publica— i stubejar `/api/` sencera. No cal
token, i el que es pinta és el component real amb el seu CSS real.

⚠️ El que això NO prova: que el backend serveixi el vigent. Això ja està MESURAT contra el banc
1383 viu (`taula-mesures` → `grading_version_number: 9` i la F a 110,5·110,5·112,5·114,5·115,5),
i per això el stub d'aquí porta EXACTAMENT aquelles xifres: si el contracte del payload es
mogués, aquest fum seguiria verd i la pantalla mentiria — la meitat que el cobreix és el banc
del backend, no aquest fitxer.

## El que es prova

    ①  «Vigent» és la PRIMERA sub-pestanya i s'obre per defecte
    ②  la F diu la corba de la v9 (110,5 · 110,5 · 112,5 · 114,5 · 115,5)
    ③  al «Vigent» NO hi ha columna «Fit actual» (una casella per talla, no dues)
    ④  el racó de la dreta diu la versió VIGENT (v9), i no la de la presa
    ⑤  ni l'avís de presa rància ni cap gest d'escriptura: consultar no crea res
    ⑥  «Presa» segueix INTACTA: la v6, el seu banner de rància i la columna «Fit actual»

## Ús

    /tmp/qa-venv/bin/python ops/qa/qa_escalat_vigent.py

Codi de sortida 1 si alguna prova falla. Captures a `ops/qa/captures/escalat_vigent_*.png`.
"""
import json
import mimetypes
import pathlib
import sys

from playwright.sync_api import sync_playwright

REPO = pathlib.Path(__file__).resolve().parents[2]
DIST = REPO / 'frontend' / 'dist'
OUT = pathlib.Path(__file__).resolve().parent / 'captures'
BASE = 'https://staging.fhorttextile.tech'
MODEL_ID = 9999
RUN = ['XS', 'S', 'M', 'L', 'XL']
BASE_SIZE = 'S'

# ── LA CORBA VIGENT (v9) · les xifres MESURADES al banc 1383 el 21/08 ────────────────────────
# F: LINEAR amb Δ general 0 i dos intervals (M→L +2 · XL→XL +1). És la regla que Agus va
# gravar per la porta dels intervals; la corba que en surt és la que la sub-pestanya ha de dir.
F_VIGENT = {'XS': 110.5, 'S': 110.5, 'M': 112.5, 'L': 114.5, 'XL': 115.5}
# ── LA MATEIXA FILA A LA PRESA (v6) · la foto congelada, que NO s'ha de re-derivar mai ──────
# Δ 1 pla: la corba que hi havia abans dels intervals. Cap xifra coincideix amb la v9 fora de
# la base — si la pantalla es confongués de font, es veuria a l'acte.
F_PRESA = {'XS': 109.5, 'S': 110.5, 'M': 111.5, 'L': 112.5, 'XL': 113.5}

CLAU_F = '9|exterior||'      # `pom.identitat.clau_mesura(9, 'exterior', '', '')`


def fila(n, codi, nom, base, graded, logica='LINEAR', ib=None, breaks=None):
    """Una fila de `taula-mesures` amb la forma exacta de `models_app/views.py:2147`."""
    return {
        'id': n, 'pom_id': n, 'pom_code': codi, 'capa': 'exterior', 'instancia': '',
        'garment': '', 'clau': f'{n}|exterior||', 'nom_fitxa': '',
        'nom_canonic_model': nom, 'nom_traduit_model': '', 'nom_en': nom, 'nom_ca': nom,
        'abbreviation': codi, 'base_value_cm': base, 'is_key': False, 'origen': 'MANUAL',
        'notes': '', 'graded': graded,
        'logica': logica, 'increment_base': ib, 'increment_break': None,
        'talla_break_label': None, 'breaks': breaks or [],
        'step_base_copiada': [], 'regla_origen': 'MANUAL', 'regla_es_resident': True,
    }


ROWS = [
    fila(3, 'A', '1/2 chest width', 44, {'XS': 42, 'S': 44, 'M': 46, 'L': 48, 'XL': 50}, ib=2),
    fila(9, 'F', 'Front length', 110.5, F_VIGENT, ib=0,
         breaks=[{'inici': 'M', 'final': 'L', 'delta': 2},
                 {'inici': 'XL', 'final': 'XL', 'delta': 1}]),
]

_TAULA = {
    'model_id': MODEL_ID, 'codi_intern': 'QA-VIGENT-0001', 'base_size': BASE_SIZE,
    'size_run': RUN, 'size_run_complet': RUN, 'run_sistema': RUN,
    'sizes_amb_dades': RUN, 'deltes': {}, 'rows': ROWS, 'total_poms': len(ROWS),
    'tancat': False,
    # 🔑 LA VERSIÓ VE D'AQUÍ, no de la presa: el «Vigent» ha de saber dir de quina corba parla
    # encara que no hi hagi hagut mai cap presa. `taula-mesures` els emet des de T4.
    'grading_version_number': 9,
    'grading_version_data': '2026-08-21T20:24:56.542062+00:00',
    'graduacio': {'font': 'model', 'es_proposta': False, 'rule_set_id': 1,
                  'rule_set_nom': 'QA', 'fit_model': 'Regular'},
}

# La PRESA: viva, nascuda de la v6, amb la vigent a la v9 → banner de rància al seu sub-tab.
_PRESA = {
    'presa_oberta': True, 'presa_tancada': False, 'piece_fitting_id': 1,
    'grading_version': {'id': 6, 'num': 6},
    'grading_version_vigent': {'id': 9, 'num': 9},
    'session': {'id': 1, 'data': '2026-08-16', 'fase': 'Proto', 'estat': 'En curs',
                'responsable': 'QA'},
    'base_size': BASE_SIZE,
    'preses': {f'{CLAU_F}:{talla}': {'teoric': v, 'real': None, 'desviacio': None, 'estat': ''}
               for talla, v in F_PRESA.items()},
    'resum': {'n_preses': 0, 'n_linies': 5, 'talles_amb_presa': [],
              'decidides_base': 0, 'pendents_base': 1},
}

_MODEL = {
    'id': MODEL_ID, 'codi_intern': 'QA-VIGENT-0001', 'nom_prenda': 'QA vigent',
    'temporada': 'FW26', 'any': 2026, 'estat': 'Nou', 'fase': 'Proto',
    'size_run_model': '·'.join(RUN), 'base_size_label': BASE_SIZE, 'fit_type': 'Regular',
    'target': 'WOMAN', 'construction': 'WOVEN', 'grading_rule_set': 1,
    'grading_rule_set_nom': 'QA', 'garment_type_item': None, 'customer': None,
    'measurements_version': 1, 'tipologia': 'MARCA',
}
_PERFIL = {'id': 1, 'username': 'qa', 'nom_complet': 'QA', 'rol_nom': 'admin',
           'capabilities': ['EXECUTE_TASKS', 'CLOSE_GATES', 'CONFIGURE'], 'idioma': 'ca'}


def _stub(path):
    if '/taula-mesures/' in path:
        return _TAULA
    if '/presa/' in path:
        return _PRESA
    if '/peces/' in path:
        return {'peces': []}
    if '/grading-status/' in path:
        return {'te_dades_propagades': True, 'segellada': False, 'version_number': 9,
                'te_regles': True}
    if path.rstrip('/').endswith(f'/models/{MODEL_ID}'):
        return _MODEL
    if '/me/' in path or '/perfil/' in path:
        return _PERFIL
    return {'count': 0, 'results': [], 'next': None, 'previous': None}


def _handler(route):
    url = route.request.url
    if not url.startswith(BASE):
        route.continue_()          # la fulla d'icones ve d'un CDN: v. l'acta del f4bis
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


def _fila_f(page):
    # Pel NOM i no pel codi: la cel·la del POM porta markup a dins (el bateig editable) i
    # `text-is("F")` no hi casa. El nom és únic a la taula i no depèn de com es pinti el codi.
    return page.locator('tbody tr:has-text("Front length")').first


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

        # EL GEST D'AGUS: obrir Escalat i prou. Cap presa nova, cap escriptura.
        page.goto(f'{BASE}/models/{MODEL_ID}?tab=Escalat',
                  wait_until='networkidle', timeout=45000)
        page.wait_for_timeout(1200)

        cos = page.inner_text('body')
        prova('la superfície munta', 'Front length' in cos or 'QA-VIGENT-0001' in cos, cos[:200])
        prova('cap error de consola', not errors, errors[:1])

        # ── ① «VIGENT» ÉS LA PRIMERA I S'OBRE PER DEFECTE ──────────────────────────────────
        # Els sub-tabs són `<button aria-current>` dins d'un div (v. `ui/SubTabs`): no hi ha
        # `nav` ni `role=tablist` on agafar-se. El que els identifica és el rètol.
        tabs = [x.strip() for x in page.locator('button').all_inner_texts()]
        # `startswith`: el sub-tab de Decisió porta el badge enganxat al rètol («…\n1»).
        subtabs = [x.split('\n')[0] for x in tabs
                   if x.split('\n')[0] in ('Vigent', 'Presa', 'Decisió talla base')]
        prova('① les tres sub-pestanyes, i «Vigent» PRIMERA',
              subtabs[:3] == ['Vigent', 'Presa', 'Decisió talla base'], subtabs)

        # ── ③ CAP COLUMNA «FIT ACTUAL» AL VIGENT ──────────────────────────────────────────
        caps = [c.strip() for c in page.locator('thead th').all_inner_texts()]
        prova('③ cap columna «Fit actual» al Vigent',
              not any('FIT ACTUAL' in c.upper() for c in caps), caps)
        # ⚠️ Les capçaleres es pinten en VERSALETES per CSS i `inner_text` torna el text
        # RENDERITZAT: comparar amb «Vigent» tal com s'escriu al JSON no hi casa mai.
        prova('③ la columna de talla es diu «Vigent»',
              any(c.strip().upper() == 'VIGENT' for c in caps), caps)
        # Una casella per talla i no dues: hi ha d'haver EXACTAMENT una subcapçalera «Vigent»
        # per talla del run. Comptar-les diu el mateix que el colspan i no depèn de quina
        # capçalera casa amb quin text (les de grup porten el nom de la talla i una ★).
        n_vigent = sum(1 for c in caps if c.strip().upper() == 'VIGENT')
        prova('③ una sola columna per talla (5 subcapçaleres «Vigent»)',
              n_vigent == len(RUN), n_vigent)

        # ── ② LA F DIU LA CORBA DE LA v9 ──────────────────────────────────────────────────
        text_f = _fila_f(page).inner_text().replace('\n', ' ')
        falten = [f'{v}' for v in F_VIGENT.values() if f'{v}' not in text_f.replace(',', '.')]
        prova('② la F diu 110,5 · 110,5 · 112,5 · 114,5 · 115,5 (v9)', not falten,
              f'falten {falten} · fila: {text_f[:160]}')
        prova('② i NO diu cap xifra de la presa v6',
              not any(f'{v}' in text_f.replace(',', '.')
                      for v in (109.5, 111.5, 113.5)), text_f[:160])

        # ── ④ EL RACÓ DE LA DRETA DIU LA VERSIÓ VIGENT ────────────────────────────────────
        prova('④ el racó diu v9 (la vigent), no v6', 'v9' in cos and 'v6' not in cos,
              [x for x in ('v6', 'v9') if x in cos])

        # ── ⑤ CONSULTAR NO CREA RES NI AVISA DE CAP RANCIESA ──────────────────────────────
        prova('⑤ cap avís de presa rància al Vigent',
              'graduació v6' not in cos and 'vigent del model és' not in cos, cos[:200])
        prova('⑤ cap casella editable a la taula',
              page.locator('tbody input').count() == 0,
              page.locator('tbody input').count())
        page.locator('table').first.screenshot(path=OUT / 'escalat_vigent_1_taula.png')
        page.screenshot(path=OUT / 'escalat_vigent_0_pantalla.png')

        # ── ⑥ «PRESA»: INTACTA ────────────────────────────────────────────────────────────
        page.locator('button:text-is("Presa")').first.click()
        page.wait_for_timeout(700)
        cos2 = page.inner_text('body')
        caps2 = [c.strip() for c in page.locator('thead th').all_inner_texts()]
        prova('⑥ la Presa torna a tenir «Fit actual»',
              any('FIT ACTUAL' in c.upper() for c in caps2), caps2)
        text_f2 = _fila_f(page).inner_text().replace('\n', ' ').replace(',', '.')
        prova('⑥ la Presa ensenya la teòrica de la v6 (111.5 · 112.5 · 113.5)',
              all(f'{v}' in text_f2 for v in (111.5, 112.5, 113.5)), text_f2[:160])
        prova('⑥ i el seu banner de rància hi torna a ser',
              'v6' in cos2 and 'v9' in cos2, [x for x in ('v6', 'v9') if x in cos2])
        page.screenshot(path=OUT / 'escalat_vigent_2_presa.png')

        prova('cap error de consola en tot el recorregut', not errors, errors[:1])
        browser.close()

    print(f'\n  {len(ok)} ✓ · {len(fallits)} ✗')
    if fallits:
        print('  FALLEN:', ' · '.join(fallits))
    return 1 if fallits else 0


if __name__ == '__main__':
    sys.exit(main())
