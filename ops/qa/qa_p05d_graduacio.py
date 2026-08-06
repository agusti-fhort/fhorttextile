"""P0.5d — LA GRADUACIÓ ÉS UNA SUPERFÍCIE PRÒPIA.

Decisió d'Agus (06/08, a pantalla): graduar no és la taula de Gravar POM amb quatre columnes
més. Aquest fum corre sobre el bundle REAL de `frontend/dist` amb les respostes reals de
l'API (`qa_p05d_fixture.py`, lectura pura) i comprova:

  1. `?tab=Mesures&mode=graduacio` obre la SUPERFÍCIE (no la taula de mesures ni el calaix);
  2. la capçalera de context diu model · joc assignat · talla base · run;
  3. hi ha una fila per mesura, amb el VALOR DE TALLA BASE ENGANXAT AL NOM;
  4. les quatre columnes de regla (RÈGIM · DELTA · DELTA BREAK · TALLA BREAK) són EDITABLES,
     i les files que el joc resol arriben PLENES mentre que la resta arriben buides;
  5. 🔴 LA LLIÇÓ DEL 31/07: en carregar, «Gravar Graduació» està DESACTIVAT i la pantalla diu
     que no hi ha cap fila tocada. Tocar-ne UNA n'activa el botó i el comptador diu 1 —no 29—,
     que és la promesa que només s'envia el que s'ha tocat;
  6. Definició POM (`?mode=entry`) ja NO ensenya les quatre columnes (P0.5d.4);
  7. els tres idiomes, amb consola neta i cap error de pàgina.

QUÈ NO COMPROVA: què desa de debò «Gravar Graduació». Aquí l'API va estubejada i comprovar
l'escriptura amb stubs seria provar-se un mateix — això es verifica contra la BD amb
`backend/scripts_tmp/p05d_anti3107.py`, que corre les crides reals dins d'un atomic que es
desfà i compta les regles residents per `origen`.

    backend/venv/bin/python ../ops/qa/qa_p05d_fixture.py
    /tmp/qa-venv/bin/python  ops/qa/qa_p05d_graduacio.py
"""
import json
import mimetypes
import pathlib
import sys

from playwright.sync_api import sync_playwright

REPO = pathlib.Path(__file__).resolve().parents[2]
DIST = REPO / 'frontend' / 'dist'
FIXTURE = pathlib.Path(__file__).resolve().parent / 'qa_p05d_fixture.json'
BASE = 'https://staging.fhorttextile.tech'

if not FIXTURE.is_file():
    sys.exit(f"✗ falta {FIXTURE.name} — genera'l amb qa_p05d_fixture.py")
DADES = json.loads(FIXTURE.read_text())
MID = DADES['_model_id']
TAULA = DADES[f'/api/v1/models/{MID}/taula-mesures/']
FILES = TAULA['rows']
PLENES = [r for r in FILES if r.get('logica')]
MODEL = DADES[f'/api/v1/models/{MID}/']

BUIT = {'count': 0, 'results': [], 'next': None, 'previous': None}
PERFIL = {'id': 1, 'username': 'qa', 'nom_complet': 'QA', 'rol_nom': 'admin',
          'capabilities': ['configure', 'EXECUTE_TASKS', 'CLOSE_GATES'], 'idioma': 'ca'}

#: Capçaleres de les quatre columnes de regla, per idioma. Literals de `i18n/{ca,en,es}.json`:
#: `fitting.grid.regime` · `editable_table.col.{delta,delta_break,talla_break}`.
COLS = {
    'ca': ['RÈGIM', 'DELTA', 'DELTA BREAK', 'TALLA BREAK'],
    'es': ['RÉGIMEN', 'DELTA', 'DELTA BREAK', 'TALLA BREAK'],
    'en': ['REGIME', 'DELTA', 'DELTA BREAK', 'BREAK SIZE'],
}
#: `graduacio.superficie.gravar`
GRAVAR = {'ca': 'Gravar Graduació', 'es': 'Grabar Graduación', 'en': 'Save grading'}


def handler(route):
    url = route.request.url
    path = url.split(BASE, 1)[-1].split('?')[0] if BASE in url else url.split('?')[0]
    if '/api/' in path:
        cos = DADES.get(path)
        if cos is None:
            cos = PERFIL if ('/me/' in path or '/perfil/' in path) else BUIT
        route.fulfill(status=200, content_type='application/json',
                      body=json.dumps(cos, ensure_ascii=False))
        return
    f = DIST / (path.lstrip('/') or 'index.html')
    if not f.is_file():
        f = DIST / 'index.html'
    route.fulfill(status=200, body=f.read_bytes(),
                  content_type=mimetypes.guess_type(str(f))[0] or 'text/html')


def obre(ctx, ruta, lang):
    page = ctx.new_page()
    errors, consola = [], []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('console', lambda m: consola.append(m.text) if m.type == 'error' else None)
    page.route('**/*', handler)
    page.add_init_script("localStorage.setItem('access_token','qa');"
                         f"localStorage.setItem('fhort.lang','{lang}');")
    page.goto(f'{BASE}{ruta}', wait_until='networkidle', timeout=45000)
    page.wait_for_timeout(2200)
    return page, errors, consola


def capcaleres(page):
    return page.evaluate(
        """() => Array.from(document.querySelectorAll('th'))
                   .map(x => x.innerText.trim().toUpperCase()).filter(Boolean)""")


def main():
    if not DIST.is_dir():
        print(f'✗ no hi ha bundle a {DIST}')
        return 1
    fallides = []
    print(f'== P0.5d · superfície de Graduació · model {MID} '
          f'({len(FILES)} files · {len(PLENES)} plenes · {len(FILES) - len(PLENES)} buides) ==')

    with sync_playwright() as p:
        b = p.chromium.launch()
        for lang in ('ca', 'es', 'en'):
            ctx = b.new_context(base_url=BASE, ignore_https_errors=True,
                                viewport={'width': 1600, 'height': 1200})

            # ── 1 · la superfície s'obre per la seva adreça ────────────────────────────────
            page, errors, consola = obre(ctx, f'/models/{MID}?tab=Mesures&mode=graduacio', lang)

            gravar = page.locator('button', has_text=GRAVAR[lang]).first
            if not gravar.count():
                fallides.append(f'{lang} · no hi ha «{GRAVAR[lang]}»: la superfície no s\'obre')
                ctx.close()
                continue

            # ── 2 · capçalera de context ───────────────────────────────────────────────────
            cos = page.inner_text('body')
            manca = [q for q in (MODEL.get('codi_intern'), MODEL.get('grading_rule_set_nom'),
                                 TAULA.get('base_size')) if q and q not in cos]
            if manca:
                fallides.append(f'{lang} · la capçalera de context no diu: {manca}')

            # ── 3 · una fila per mesura, amb el valor de talla base enganxat al nom ────────
            n_files = page.evaluate("() => document.querySelectorAll('tbody tr').length")
            if n_files != len(FILES):
                fallides.append(f'{lang} · files {n_files}, esperades {len(FILES)}')
            ambvalor = next((r for r in FILES if r.get('base_value_cm') is not None), None)
            if ambvalor and f"{ambvalor['base_value_cm']} cm" not in cos:
                fallides.append(f'{lang} · el valor de talla base no surt enganxat al nom '
                                f'({ambvalor["base_value_cm"]} cm)')

            # ── 4 · les quatre columnes de regla, i EDITABLES ──────────────────────────────
            caps = capcaleres(page)
            falten = [c for c in COLS[lang] if c not in caps]
            if falten:
                fallides.append(f'{lang} · falten columnes de regla {falten} · hi ha {caps}')
            n_sel = page.evaluate("() => document.querySelectorAll('tbody select').length")
            n_inp = page.evaluate("() => document.querySelectorAll('tbody input').length")
            # 2 selects (règim · talla break) i 2 inputs (delta · delta break) per fila.
            if n_sel < len(FILES) * 2 or n_inp < len(FILES) * 2:
                fallides.append(f'{lang} · controls editables insuficients: '
                                f'{n_sel} selects / {n_inp} inputs per a {len(FILES)} files')

            # les plenes arriben amb règim; les buides, sense
            plens = page.evaluate(
                """() => Array.from(document.querySelectorAll('tbody tr'))
                     .filter(tr => { const s = tr.querySelector('select'); return s && s.value })
                     .length""")
            if plens != len(PLENES):
                fallides.append(f'{lang} · files amb règim {plens}, esperades {len(PLENES)}')

            # ── 5 · 🔴 LA LLIÇÓ DEL 31/07 ─────────────────────────────────────────────────
            if not gravar.is_disabled():
                fallides.append(f'{lang} · «{GRAVAR[lang]}» arriba ACTIU sense haver tocat res '
                                f'— una passada per la pantalla no ha de poder desar res')
            # tocar UNA fila: el delta de la primera
            page.evaluate(
                """() => {
                     const i = document.querySelector('tbody input:not([disabled])')
                     const set = Object.getOwnPropertyDescriptor(
                       window.HTMLInputElement.prototype, 'value').set
                     set.call(i, '3.5')
                     i.dispatchEvent(new Event('input', { bubbles: true }))
                   }""")
            page.wait_for_timeout(500)
            if gravar.is_disabled():
                fallides.append(f'{lang} · tocar una fila no activa «{GRAVAR[lang]}»')
            # El comptador que hi ha al costat del botó ha de dir 1 —no el total de files—:
            # és la promesa de la llei feta visible («només s'enviarà el que has tocat»).
            estat = page.evaluate(
                """(txt) => {
                     const b = Array.from(document.querySelectorAll('button'))
                       .find(x => x.innerText.trim() === txt)
                     const s = b && b.parentElement.querySelector('span')
                     return s ? s.innerText.trim() : ''
                   }""", GRAVAR[lang])
            if '1' not in estat:
                fallides.append(f'{lang} · el comptador no diu 1 després de tocar UNA fila: '
                                f'«{estat}»')
            if str(len(FILES)) in estat:
                fallides.append(f'{lang} · el comptador diu {len(FILES)} (el total de files) '
                                f'després de tocar-ne UNA: «{estat}»')

            if errors:
                fallides.append(f'{lang} · error de pàgina: {errors[0][:140]}')
            if consola:
                fallides.append(f'{lang} · consola bruta: {consola[0][:140]}')
            if not [f for f in fallides if f.startswith(f'{lang} ·')]:
                print(f'  ✓ {lang} · superfície · {n_files} files · {plens} amb règim · '
                      f'{len(COLS[lang])} columnes editables · comptador «{estat}» · consola neta')
            page.close()

            # ── 6 · P0.5d.4 · Definició POM ja no ensenya les columnes de graduació ────────
            page, errors2, consola2 = obre(ctx, f'/models/{MID}?tab=Mesures&mode=entry', lang)
            caps_pom = capcaleres(page)
            intruses = [c for c in COLS[lang] if c in caps_pom]
            if intruses:
                fallides.append(f'{lang} · Definició POM encara ensenya {intruses} (P0.5d.4)')
            else:
                print(f'  ✓ {lang} · Definició POM · cap columna de graduació')

            if errors2:
                fallides.append(f'{lang} · Definició POM · error de pàgina: {errors2[0][:140]}')
            page.close()
            ctx.close()
        b.close()

    print()
    if fallides:
        print('✗ FALLIDES')
        for f in fallides:
            print(f'  · {f}')
        return 1
    print('✓ P0.5d verd · la superfície s\'obre, edita i guarda el botó fins que es toca res')
    return 0


if __name__ == '__main__':
    sys.exit(main())
