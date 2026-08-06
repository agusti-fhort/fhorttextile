"""P0.7 — EL DEFECTE DEL TAB MESURES ÉS SEMPRE LA CONSULTA.

Contracte d'Agus (06/08): entrar al tab Mesures és entrar a la consulta —amb dades, sense,
carregant o amb error—. L'edició només s'obre per gest explícit: el botó ① «Editar POM»,
`?mode=entry` a la URL, o una tasca entrant (`?task_id=`).

## El defecte que tanca

Càrrega FREDA de `/models/1308?tab=Mesures`, sense cap paràmetre, i sortia Definició POM amb
píndoles i «Gravar POM». La causa no era la URL sinó `pomGenesisOpen`: n'hi havia prou que la
tasca `pom` del model estigués En curs o **Paused** perquè el gate d'entrada obrís l'edició. Al
MILEY la `pom` fa dies que està Paused, i per això el tab no s'havia pogut consultar mai més.

Per això aquest fum va amb el fixture del **1308** i **amb les seves tasques reals**
(`qa_p03_fixture.py` les captura): amb la llista de tasques buida el defecte no es reprodueix, i
un fum que no el reprodueix no el vigila.

## El camí que prova — el d'Agus, no un d'equivalent

  1. càrrega FREDA amb `?tab=Mesures` × 3 (context nou cada vegada, no navegació interna)
  2. F5 × 3 sobre la mateixa pàgina
  3. entrada des de la LLISTA de models (navegació interna, sense `?tab=`)
  4. canviar de tab i tornar
  5. el camí feliç: prémer ① «Editar POM» SÍ que obre l'edició

    backend/venv/bin/python ../ops/qa/qa_p03_fixture.py 1308
    /tmp/qa-venv/bin/python  ops/qa/qa_p07_tab_mesures_consulta.py
"""
import json
import mimetypes
import pathlib
import sys

from playwright.sync_api import sync_playwright

REPO = pathlib.Path(__file__).resolve().parents[2]
DIST = REPO / 'frontend' / 'dist'
FIXTURE = pathlib.Path(__file__).resolve().parent / 'qa_p03_fixture.json'
BASE = 'https://staging.fhorttextile.tech'

if not FIXTURE.is_file():
    sys.exit(f'✗ falta {FIXTURE.name} — genera\'l amb qa_p03_fixture.py 1308')
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
            # `open-task` ha de tornar un `task_id`: és el que fa que el botó ① entri de debò.
            # Amb el BUIT genèric el gest es quedava a mig camí i el fum acusava el producte
            # d'un defecte que era seu.
            if path.endswith('/open-task/'):
                cos = {'task_id': 999}
            else:
                cos = PERFIL if ('/me/' in path or '/perfil/' in path) else BUIT
        route.fulfill(status=200, content_type='application/json',
                      body=json.dumps(cos, ensure_ascii=False))
        return
    f = DIST / (path.lstrip('/') or 'index.html')
    if not f.is_file():
        f = DIST / 'index.html'
    route.fulfill(status=200, body=f.read_bytes(),
                  content_type=mimetypes.guess_type(str(f))[0] or 'text/html')


def estat(page):
    """CONSULTA vs EDICIO, pel que la persona veu: el commutador de subvista o les píndoles."""
    consulta = page.locator('button:has-text("Taula de mesures")').count() > 0
    edicio = page.locator('button[data-pindola]').count() > 0
    return 'CONSULTA' if (consulta and not edicio) else ('EDICIO' if edicio else '?')


def nova(b, errors, consola):
    ctx = b.new_context(base_url=BASE, ignore_https_errors=True,
                        viewport={'width': 1600, 'height': 1200})
    page = ctx.new_page()
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('console', lambda m: consola.append(m.text) if m.type == 'error' else None)
    page.route('**/*', handler)
    page.add_init_script("localStorage.setItem('access_token','qa');"
                         "localStorage.setItem('fhort.lang','ca');")
    return ctx, page


def main():
    if not DIST.is_dir():
        print(f'✗ no hi ha bundle a {DIST}'); return 1

    tasques = DADES.get('/api/v1/model-task-items/', {})
    files = tasques.get('results', tasques if isinstance(tasques, list) else [])
    pom = next((r for r in files if r.get('task_type_code') == 'pom'), None)
    print(f'· model {MID} · tasca pom = {pom.get("status") if pom else "CAP"} '
          f'· {len(files)} tasques')
    if not pom or pom.get('status') not in ('InProgress', 'Paused'):
        print('  ⚠️ la tasca `pom` NO està oberta ni pausada: aquest fum NO reprodueix el '
              'defecte del 06/08 i el seu verd no vol dir res. Recaptura el fixture d\'un '
              'model que la tingui.')

    fallides, errors, consola = [], [], []
    with sync_playwright() as b_ctx:
        b = b_ctx.chromium.launch()

        # ── 1 · CÀRREGA FREDA × 3 (context nou: ni cache ni estat de React) ────────
        for volta in (1, 2, 3):
            ctx, page = nova(b, errors, consola)
            page.goto(f'{BASE}/models/{MID}?tab=Mesures', wait_until='networkidle', timeout=45000)
            page.wait_for_timeout(2200)
            e = estat(page)
            if e != 'CONSULTA':
                fallides.append(f'càrrega freda #{volta} → {e}')
            else:
                print(f'  ✓ 1 · càrrega freda #{volta} · CONSULTA')
            ctx.close()

        # ── 2 · F5 × 3 sobre la mateixa pàgina ─────────────────────────────────────
        ctx, page = nova(b, errors, consola)
        page.goto(f'{BASE}/models/{MID}?tab=Mesures', wait_until='networkidle', timeout=45000)
        page.wait_for_timeout(2000)
        for volta in (1, 2, 3):
            page.reload(wait_until='networkidle')
            page.wait_for_timeout(2000)
            e = estat(page)
            if e != 'CONSULTA':
                fallides.append(f'F5 #{volta} → {e}')
        if not any('F5' in f for f in fallides):
            print('  ✓ 2 · F5 × 3 · CONSULTA')

        # ── 3 · canviar de tab i tornar ────────────────────────────────────────────
        for altre in ('Escalat', 'Tasques'):
            page.get_by_role('button', name=altre, exact=True).first.click()
            page.wait_for_timeout(1200)
            page.get_by_role('button', name='Mesures', exact=True).first.click()
            page.wait_for_timeout(1800)
            e = estat(page)
            if e != 'CONSULTA':
                fallides.append(f'tornant de {altre} → {e}')
        if not any('tornant' in f for f in fallides):
            print('  ✓ 3 · Mesures → Escalat/Tasques → Mesures · CONSULTA')

        # ── 4 · EL CAMÍ FELIÇ: el botó ① SÍ que obre l'edició ──────────────────────
        page.get_by_role('button', name='Editar POM', exact=True).first.click()
        page.wait_for_timeout(2200)
        # El senyal de contracte és que la CONSULTA ha marxat. Buscar les píndoles seria buscar
        # una dada del diccionari que aquest fixture no porta, i el fum acusaria el producte
        # d'una cosa que és seva.
        surt_de_consulta = estat(page) != 'CONSULTA'
        if not surt_de_consulta:
            fallides.append('«Editar POM» ja no treu de la consulta')
        else:
            print('  ✓ 4 · «Editar POM» · surt de la consulta (els botons segueixen funcionant)')

        # ── 5 · entrada SENSE ?tab= (navegació interna / llista de models) ─────────
        ctx2, page2 = nova(b, errors, consola)
        page2.goto(f'{BASE}/models/{MID}', wait_until='networkidle', timeout=45000)
        page2.wait_for_timeout(2000)
        page2.get_by_role('button', name='Mesures', exact=True).first.click()
        page2.wait_for_timeout(2000)
        e = estat(page2)
        if e != 'CONSULTA':
            fallides.append(f'entrant sense ?tab= i clicant Mesures → {e}')
        else:
            print('  ✓ 5 · sense ?tab=, clicant la pestanya · CONSULTA')
        ctx2.close()
        ctx.close()
        b.close()

    if errors:
        fallides.append(f'error de pàgina: {errors[0][:160]}')
    else:
        print('  ✓ cap error de pàgina')
    if consola:
        fallides.append(f'consola bruta ({len(consola)}): {consola[0][:160]}')
    else:
        print('  ✓ consola neta')

    print()
    if fallides:
        print('✗ FALLIDES')
        for f in fallides:
            print(f'  · {f}')
        return 1
    print('✓ el tab Mesures obre SEMPRE la consulta, i només els gestos explícits obren l\'edició')
    return 0


if __name__ == '__main__':
    sys.exit(main())
