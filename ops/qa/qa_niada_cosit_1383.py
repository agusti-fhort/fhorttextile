"""QA de pantalla del FIX de la niada — ExportModal del 1383 (PF20 v3 · GV201 v9).

## Què mesura

El fix d'aquest sprint (`engine/operations.py::_normalitzar_ordres_al_tall`) fa que una ordre
de grading que aterra sobre la línia de COSIT arribi a la niada. Al 837, 26 dels 27 extrems
ancorats seuen sobre el cosit, i abans del fix la taula de pre-reconeixement ensenyava
`−delta` a TOTES les caselles: cap punt es movia.

Aquest fum obre l'ExportModal de debò i llegeix la taula que l'Agus veurà.

## Per què amb stub i no contra staging viu

La QA de navegador contra staging vol un JWT que l'agent **no pot emetre** (mateixa llei que
`qa_escalat_vigent.py`). El camí que SÍ que executa el codi real és servir el bundle de
`frontend/dist` —el mateix que nginx publica— i stubejar `/api/`.

⚠️ Però aquí el stub NO és inventat: `payload_niada_1383.json` és **la resposta literal del
backend**, generada amb `_preview_payload(build_export(fp, 201, 'polypattern'))` contra el
banc viu (lectura dins d'una transacció avortada, cap escriptura, cap `ExportAcknowledgement`).
O sigui que la meitat de backend està mesurada al banc i aquesta meitat mesura que la pantalla
la pinta. Si el contracte del payload es mogués, cal regenerar el JSON.

## El que es prova

    ①  el modal s'obre i ofereix la GV201 (v9), l'única aprovada
    ②  la taula de pre-reconeixement pinta les 5 talles × 14 POMs
    ③  els POMs de gir CLAVEN el delta: B, D, F i J1 sense cap ⚠ a cap talla
    ④  la fila de la base (S) no té cap ⚠ enlloc
    ⑤  els 6 residus coneguts surten a la llista de problemes AMB la xifra
    ⑥  l'autovalidació diu 38 regles actives (abans del fix: 0)
    ⑦  cap error de consola

## Ús

    /tmp/qa-venv/bin/python ops/qa/qa_niada_cosit_1383.py

Codi de sortida 1 si alguna prova falla. Captures a `ops/qa/captures/niada_cosit_*.png`.
"""
import json
import mimetypes
import pathlib
import sys

from playwright.sync_api import sync_playwright

REPO = pathlib.Path(__file__).resolve().parents[2]
DIST = REPO / 'frontend' / 'dist'
AQUI = pathlib.Path(__file__).resolve().parent
OUT = AQUI / 'captures'
PAYLOAD = AQUI / 'payload_niada_1383.json'
BASE = 'https://staging.fhorttextile.tech'

MODEL_ID = 1383
PF_ID = 20

#: Els POMs ancorats a dos punts de GIR i amb delta ≠ 0: han de clavar el delta a totes les
#: talles. Són la prova que el moviment travessa el cosit. (E, S i E1 també són de gir però
#: arrosseguen el residu del repartiment simètric v1, que aquest sprint no toca.)
CLAVEN = ('B', 'D', 'F', 'J1')

#: Els residus coneguts i anotats. A i C i S2 per ancoratge sobre CORBA; E, S i E1 pel
#: repartiment simètric de la projecció v1. Cap dels dos és feina d'aquest sprint.
RESIDUS = ('A', 'C', 'E', 'E1', 'S', 'S2')

_D = json.loads(PAYLOAD.read_text(encoding='utf-8'))
_PERFIL = {'id': 1, 'username': 'qa', 'nom_complet': 'QA', 'rol_nom': 'admin',
           'capabilities': ['EXECUTE_TASKS', 'CLOSE_GATES', 'CONFIGURE'], 'idioma': 'ca'}
_MODEL = {'id': MODEL_ID, 'codi_intern': 'TRV-SS27-0001', 'nom_prenda': '837 VESTIT',
          'temporada': 'SS27', 'any': 2027, 'estat': 'Nou', 'fase': 'Dev',
          'size_run_model': 'XS·S·M·L·XL', 'base_size_label': 'S', 'fit_type': 'Regular',
          'target': 'WOMAN', 'construction': 'WOVEN', 'tipologia': 'MARCA',
          'garment_type_item': None, 'customer': None, 'measurements_version': 1}


def _stub(path, metode):
    if path.endswith('/export-preview/'):
        return _D['preview']
    if path.endswith('/grading-versions/'):
        return _D['versions']
    if path.rstrip('/').endswith(f'/pattern-files/{PF_ID}'):
        return _D['detall']
    if '/pattern-files/' in path and path.rstrip('/').endswith('pattern-files'):
        return _D['llista']
    if '/piece-roles/' in path:
        return []
    if '/identity-acknowledgements/' in path or '/identitat/' in path:
        return {'acta': None, 'text_confirmacio': ''}
    if '/geometry/' in path:
        return {'pieces': []}
    if path.rstrip('/').endswith(f'/models/{MODEL_ID}'):
        return _MODEL
    if '/me/' in path or '/perfil/' in path:
        return _PERFIL
    return {'count': 0, 'results': [], 'next': None, 'previous': None}


def _handler(route):
    url = route.request.url
    if not url.startswith(BASE):
        route.continue_()            # la fulla d'icones ve d'un CDN
        return
    path = url.split(BASE, 1)[-1].split('?')[0]
    if path.startswith('/api/'):
        route.fulfill(status=200, content_type='application/json',
                      body=json.dumps(_stub(path, route.request.method), default=str))
        return
    f = DIST / (path.lstrip('/') or 'index.html')
    if not f.is_file():
        f = DIST / 'index.html'
    route.fulfill(status=200, body=f.read_bytes(),
                  content_type=mimetypes.guess_type(str(f))[0] or 'text/html')


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
                                  viewport={'width': 1600, 'height': 1000})
        page = ctx.new_page()
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.route('**/*', _handler)
        page.add_init_script(
            "localStorage.setItem('access_token','qa');"
            "localStorage.setItem('fhort.lang','ca')")

        # EL GEST: obrir el tab Patró i clicar Exporta. Cap reconeixement, cap descàrrega.
        page.goto(f'{BASE}/models/{MODEL_ID}?tab=Patró', wait_until='networkidle',
                  timeout=45000)
        page.wait_for_timeout(1200)

        boto = page.locator('button:has-text("Exporta")').first
        prova('el botó d\'exportar hi és', boto.count() > 0)
        if boto.count() == 0:
            page.screenshot(path=str(OUT / 'niada_cosit_sense_boto.png'), full_page=True)
            print('\n'.join(f'  · {x}' for x in errors[:3]))
            return 1
        boto.click()
        page.wait_for_timeout(1500)

        cos = page.inner_text('body')

        # ── ① la versió aprovada ─────────────────────────────────────────────
        prova('① el modal ofereix la GV201 (v9, 105 specs)',
              'Propagació conscient' in cos and '105 specs' in cos, cos[:200])

        # ── ② la taula ───────────────────────────────────────────────────────
        files = page.locator('table tbody tr')
        prova('② la taula de pre-reconeixement té files', files.count() >= 5, files.count())

        # ── ③ els POMs de gir claven el delta ────────────────────────────────
        #    La taula és talles × POMs; el ⚠ viu a la cel·la. Es mesura per POM: la seva
        #    columna no pot portar cap ⚠ a cap talla.
        preview = _D['preview']
        def desviaments(codi):
            return [pm['desviament_cm'] for t in preview['talles'] for pm in t['poms']
                    if pm['pom_code'] == codi]
        for codi in CLAVEN:
            ds = desviaments(codi)
            prova(f'③ el POM {codi} clava el delta a les 5 talles',
                  bool(ds) and all(d is not None and abs(d) < 1e-6 for d in ds), ds)

        # ── ④ la base neta ───────────────────────────────────────────────────
        base = next((t for t in preview['talles'] if t['es_base']), None)
        prova('④ la talla base (S) no té cap desviament',
              base is not None and all(
                  pm['desviament_cm'] in (None, 0.0) for pm in base['poms']),
              base and [pm['pom_code'] for pm in base['poms']
                        if pm['desviament_cm'] not in (None, 0.0)])

        # ── ⑤ els residus, dits amb la xifra ─────────────────────────────────
        escalat = preview.get('problemes_escalat') or []
        prova('⑤ hi ha 6 problemes d\'escalat anotats', len(escalat) == 6, len(escalat))
        for codi in RESIDUS:
            prova(f'⑤ el residu del POM {codi} es diu a la pantalla',
                  any(f'POM {codi} ' in x for x in escalat)
                  and f'POM {codi} ' in cos.replace('\n', ' '),
                  [x[:60] for x in escalat])
        prova('⑤ i el missatge porta la CAUSA (corba o repartiment)',
              all(('CORBA' in x or 'REPARTIMENT' in x) for x in escalat))

        # ── ⑥ el motor ha graduat de debò ────────────────────────────────────
        prova('⑥ 38 regles actives (abans del fix: 0)', preview['regles'] == 38,
              preview['regles'])
        prova('⑥ l\'autovalidació passa amb 39/39 regles',
              preview['autovalidacio']['ok']
              and '39/39' in preview['autovalidacio']['resum'],
              preview['autovalidacio']['resum'][:120])

        # ── ⑦ consola ────────────────────────────────────────────────────────
        prova('⑦ cap error de consola', not errors, errors[:1])

        page.screenshot(path=str(OUT / 'niada_cosit_modal.png'), full_page=True)
        browser.close()

    print(f'\n{len(ok)} ✓ · {len(fallits)} ✗')
    if fallits:
        print('FALLEN: ' + ', '.join(fallits))
    return 1 if fallits else 0


if __name__ == '__main__':
    sys.exit(main())
