"""P0.6 — les QUATRE accions del tab Mesures: ordre, cos i on porten.

El tab Mesures és de CONSULTA, i a dalt hi ha les quatre vies d'entrada a les seves
superfícies, en ordre de flux de treball (Agus, 06/08):

    ① Editar POM · ② Graduació · ③ Mesurar prenda · ④ Propagar

Què comprova, sobre el bundle REAL de `frontend/dist` amb les respostes reals de l'API
(`qa_p02_fixture.py`, lectura pura):

  1. hi són els QUATRE i en AQUEST ordre;
  2. tenen FONS BLANC (anaven transparents i es fonien amb el crema de la pàgina);
  3. els tres idiomes, amb els literals que toquen a cadascun;
  4. F5: hi segueixen, en el mateix ordre;
  5. consola neta i cap error de pàgina.

QUÈ NO COMPROVA: on porta cada botó de debò. Això depèn del circuit de tasca del servidor
(`open-task`, el modal de tres cares, el rellotge) i aquí l'API va estubejada — provar-ho
amb stubs seria provar-se un mateix. Va al report, verificat a mà.

    backend/venv/bin/python ../ops/qa/qa_p02_fixture.py     # el fixture es comparteix
    /tmp/qa-venv/bin/python  ops/qa/qa_p06_botons_mesures.py
"""
import json
import mimetypes
import pathlib
import sys

from playwright.sync_api import sync_playwright

REPO = pathlib.Path(__file__).resolve().parents[2]
DIST = REPO / 'frontend' / 'dist'
FIXTURE = pathlib.Path(__file__).resolve().parent / 'qa_p02_fixture.json'
BASE = 'https://staging.fhorttextile.tech'

if not FIXTURE.is_file():
    sys.exit(f'✗ falta {FIXTURE.name} — genera\'l amb qa_p02_fixture.py')
DADES = json.loads(FIXTURE.read_text())
MID = DADES['_model_id']
BUIT = {'count': 0, 'results': [], 'next': None, 'previous': None}
PERFIL = {'id': 1, 'username': 'qa', 'nom_complet': 'QA', 'rol_nom': 'admin',
          'capabilities': ['configure', 'EXECUTE_TASKS', 'CLOSE_GATES'], 'idioma': 'ca'}

#: L'ORDRE és el contracte d'aquesta pantalla. Literals de `i18n/{ca,en,es}.json`:
#: `model_sheet.edit_pom` · `graduacio.button` · `presa.titol` · `grading_propagate.button`
ESPERATS = {
    'ca': ['Editar POM', 'Graduació', 'Mesurar prenda', 'Propagar'],
    'es': ['Editar POM', 'Graduación', 'Medir prenda', 'Propagar'],
    'en': ['Edit POM', 'Grading', 'Measure garment', 'Propagate'],
}


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


def accions(page, noms):
    """Els botons de LA BARRA D'ACCIONS, en l'ordre del DOM, amb el fons calculat.

    S'acota al contenidor del darrer botó i NO es busca per tot el document: en anglès la
    pestanya «Escalat» també es diu «Grading» (`model_sheet.tab_grading`), i una cerca global
    se l'enduia com si fos una acció. El fum ha de mirar la barra, no el nom.
    """
    return page.evaluate(
        """(noms) => {
             const ultim = noms[noms.length - 1]
             const b = Array.from(document.querySelectorAll('button'))
               .find(x => x.innerText.trim().startsWith(ultim))
             if (!b) return []
             return Array.from(b.parentElement.querySelectorAll(':scope > button'))
               .map(x => ({ txt: x.innerText.trim(),
                            bg: getComputedStyle(x).backgroundColor }))
           }""", noms)


def main():
    if not DIST.is_dir():
        print(f'✗ no hi ha bundle a {DIST}'); return 1
    fallides = []

    with sync_playwright() as p:
        b = p.chromium.launch()
        for lang, esperats in ESPERATS.items():
            ctx = b.new_context(base_url=BASE, ignore_https_errors=True,
                                viewport={'width': 1600, 'height': 1200})
            page = ctx.new_page()
            errors, consola = [], []
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.on('console', lambda m: consola.append(m.text) if m.type == 'error' else None)
            page.route('**/*', handler)
            page.add_init_script("localStorage.setItem('access_token','qa');"
                                 f"localStorage.setItem('fhort.lang','{lang}');")
            # SENSE `mode=entry`: el tab en CONSULTA, que és on viuen les quatre accions.
            page.goto(f'{BASE}/models/{MID}?tab=Mesures', wait_until='networkidle', timeout=45000)
            page.wait_for_timeout(2000)

            for volta in (0, 1):        # muntatge + F5
                etiqueta = 'muntatge' if volta == 0 else 'F5'
                if volta:
                    page.reload(wait_until='networkidle')
                    page.wait_for_timeout(1800)

                trobats = accions(page, esperats)
                ordre = [x['txt'] for x in trobats]
                if ordre != esperats:
                    fallides.append(f'{lang} · {etiqueta} · ordre {ordre}, esperat {esperats}')
                    continue
                # Fons BLANC: `--white` = #ffffff. `transparent`/`rgba(0,0,0,0)` és el defecte
                # d'abans, que és exactament el que es volia matar.
                grisos = [x['txt'] for x in trobats
                          if x['bg'].replace(' ', '') not in ('rgb(255,255,255)', '#ffffff')]
                if grisos:
                    fallides.append(f'{lang} · {etiqueta} · sense fons blanc: '
                                    f'{[(x["txt"], x["bg"]) for x in trobats if x["txt"] in grisos]}')
                else:
                    print(f'  ✓ {lang} · {etiqueta} · {ordre} · fons blanc')

            if errors:
                fallides.append(f'{lang} · error de pàgina: {errors[0][:140]}')
            if consola:
                fallides.append(f'{lang} · consola bruta: {consola[0][:140]}')
            ctx.close()
        b.close()

    print()
    if fallides:
        print('✗ FALLIDES')
        for f in fallides:
            print(f'  · {f}')
        return 1
    print('✓ els 4 botons, en ordre i amb cos, als 3 idiomes i després de F5')
    return 0


if __name__ == '__main__':
    sys.exit(main())
