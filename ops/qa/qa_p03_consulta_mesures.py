"""P0.3 — la CONSULTA «Taula de mesures» ensenya els valors del model.

## El defecte que tanca

Agus, 06/08 10:01 (MILEY · BRW-SS26-0003): valors entrats i gravats a «Definició POM», visibles
allà. La consulta «Taula de mesures» ensenyava les 12 files CORRECTES i les columnes TALLA BASE
i BASE VIGENT **totes a «—»**.

Les files arribaven i els valors no perquè venien de dues bandes diferents: les files de
`base-stages/` (que llegeix `BaseMeasurement`) i els valors de les línies d'un `SizeCheck`
(`line.valor_real` / `line.valor_teoric`). El MILEY té 12 mesures amb valor i **zero SizeCheck**,
o sigui que cap línia casava i les dues columnes queien a null.

El mode `presa` («Mesurar prenda») SÍ ha de llegir el check: allà el carril porta la presa
d'avui i la base vigent és el testimoni congelat contra el qual es compara. El que no s'aguanta
és que la CONSULTA —que no pren res— depengui d'un check obert.

## Què comprova

Sobre el bundle REAL de `frontend/dist` (el mateix que nginx publica) amb les respostes REALS
de l'API (`qa_p03_fixture.py`, lectura pura):

  1. la consulta MUNTA (cap `pageerror`, cap AppErrorBoundary) i pinta les 12 files;
  2. el carril TALLA BASE ensenya els 12 valors del model, no «—»;
  3. BASE VIGENT ensenya els mateixos (en consulta són la mateixa cosa: `BaseMeasurement`);
  4. F5 × 2 — els valors hi segueixen (no és un artefacte del primer muntatge);
  5. consola neta.

CONTROL LÒGIC: el mapatge VELL es recalcula aquí mateix sobre el MATEIX fixture i s'imprimeix
el que hauria donat (tot None). No és un control sobre el bundle vell —reconstruir-lo voldria
dir redesplegar staging dues vegades, i l'Agus hi està treballant— però demostra que el fum no
passaria abans del fix.

## Ús

    backend/venv/bin/python ../ops/qa/qa_p03_fixture.py 1308
    /tmp/qa-venv/bin/python ops/qa/qa_p03_consulta_mesures.py

Surt amb codi 1 si alguna comprovació falla.
"""
import json
import mimetypes
import pathlib
import sys

from playwright.sync_api import sync_playwright

REPO = pathlib.Path(__file__).resolve().parents[2]
DIST = REPO / 'frontend' / 'dist'
# Per defecte el fixture del MILEY; `qa_p03_cicle.py` hi passa el del seu model de prova.
FIXTURE = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else (
    pathlib.Path(__file__).resolve().parent / 'qa_p03_fixture.json')
BASE = 'https://staging.fhorttextile.tech'

if not FIXTURE.is_file():
    sys.exit(f'✗ falta {FIXTURE.name} — genera\'l amb qa_p03_fixture.py')
DADES = json.loads(FIXTURE.read_text())
MID = DADES['_model_id']
BUIT = {'count': 0, 'results': [], 'next': None, 'previous': None}
PERFIL = {'id': 1, 'username': 'qa', 'nom_complet': 'QA', 'rol_nom': 'admin',
          'capabilities': ['configure', 'EXECUTE_TASKS', 'CLOSE_GATES'], 'idioma': 'ca'}


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


def files_de_taula(page):
    """Per cada fila del cos: la llista de textos de les seves cel·les."""
    return page.eval_on_selector_all(
        'table tbody tr',
        "rows => rows.map(tr => Array.from(tr.querySelectorAll('td'))"
        "                            .map(td => td.innerText.trim()))")


def main():
    if not DIST.is_dir():
        print(f'✗ no hi ha bundle a {DIST}'); return 1

    bs = DADES[f'/api/v1/models/{MID}/base-stages/']
    esperats = sorted(r['base_value_cm'] for r in bs['rows']
                      if r.get('base_value_cm') is not None)
    n_files = len(bs['rows'])
    checks = DADES.get('/api/v1/size-checks/', BUIT)
    n_checks = checks.get('count', 0)
    print(f'· model {MID} · base_size={bs.get("base_size")!r} · files={n_files} '
          f'· valors a BD={len(esperats)} · size_checks={n_checks}')

    # ── CONTROL LÒGIC: què hauria donat el mapatge VELL sobre aquest mateix fixture ──
    lines = []
    for r in (checks.get('results') or []):
        lines += r.get('lines', []) if isinstance(r, dict) else []
    vells = [next((l.get('valor_real') for l in lines
                   if l.get('base_measurement_id') == r.get('base_measurement_id')), None)
             for r in bs['rows']]
    print(f'· control · el mapatge VELL (line.valor_real) hauria donat '
          f'{sum(1 for v in vells if v is not None)}/{n_files} valors → la resta, «—»')

    fallides = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(base_url=BASE, ignore_https_errors=True,
                            viewport={'width': 1600, 'height': 1200})
        page = ctx.new_page()
        errors, consola = [], []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.on('console', lambda m: consola.append(m.text) if m.type == 'error' else None)
        page.route('**/*', handler)
        page.add_init_script("localStorage.setItem('access_token','qa');"
                             "localStorage.setItem('fhort.lang','ca');")
        # SENSE `mode=entry`: això és la CONSULTA, que és la pantalla del defecte.
        page.goto(f'{BASE}/models/{MID}?tab=Mesures', wait_until='networkidle', timeout=45000)
        page.wait_for_timeout(2000)

        for volta in range(3):          # muntatge + F5 × 2
            etiqueta = 'muntatge' if volta == 0 else f'F5 #{volta}'
            if volta:
                page.reload(wait_until='networkidle')
                page.wait_for_timeout(1800)

            files = files_de_taula(page)
            if len(files) != n_files:
                fallides.append(f'{etiqueta} · files a la taula: {len(files)}, esperades {n_files}')
                continue

            # Els valors, llegits de les cel·les: es normalitza a float el que ho sigui.
            vistos = []
            for cels in files:
                for c in cels:
                    net = c.replace(',', '.').strip()
                    try:
                        vistos.append(float(net))
                    except ValueError:
                        pass
            falten = [v for v in esperats if vistos.count(v) < 1]
            if falten:
                fallides.append(f'{etiqueta} · NO surten a la taula els valors {falten}')
            else:
                # BASE VIGENT + TALLA BASE porten el mateix número en consulta → cada valor
                # ha de sortir com a mínim DUES vegades. Si només hi és un cop, una de les
                # dues columnes segueix a «—».
                un_sol_cop = [v for v in esperats if vistos.count(v) < 2]
                if un_sol_cop:
                    fallides.append(f'{etiqueta} · només UNA de les dues columnes porta '
                                    f'valor per a {un_sol_cop}')
                else:
                    print(f'  ✓ {etiqueta} · {n_files} files · TALLA BASE i BASE VIGENT amb '
                          f'els {len(esperats)} valors del model')

        if errors:
            fallides.append(f'error de pàgina: {errors[0][:160]}')
        else:
            print('  ✓ cap error de pàgina')
        if consola:
            fallides.append(f'consola bruta ({len(consola)}): {consola[0][:160]}')
        else:
            print('  ✓ consola neta')
        b.close()

    if fallides:
        print('\n✗ FALLIDES')
        for f in fallides:
            print(f'  · {f}')
        return 1
    print('\n✓ la consulta ensenya la base del model, i hi segueix després de F5')
    return 0


if __name__ == '__main__':
    sys.exit(main())
