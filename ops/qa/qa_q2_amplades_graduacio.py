"""Q2 — LA GRADUACIÓ I LA CONSULTA, COSTAT A COSTAT, MESURADES.

Ordre d'Agus (06/08, captura 13:04): la pantalla de Graduació havia perdut la família — un forat
enorme entre la columna `#` i CAPA. La verificació que la comanda demana és UNA i literal:
les mateixes amplades de columna, mesurades per COMPUTED STYLE, a les dues pantalles.

Corre sobre el bundle REAL de `frontend/dist` amb les respostes reals de l'API
(`qa_q2_fixture.json`, lectura pura, model 169) i compara:

  · el bloc d'identitat i el carril, per POSICIÓ (`#` · CAPA · POM · NOM · TALLA BASE): les
    cinc primeres columnes de totes dues taules són les mateixes i han de caure al mateix lloc;
  · les quatre columnes de REGLA, per NOM (a la consulta van de lectura i a la Graduació són
    editables, però l'amplada és de la família);
  · que la columna `#` no s'endugui l'espai sobrant (era el forat: taula a `width:100%` amb
    totes les altres columnes fixades).

    backend/venv/bin/python ../ops/qa/qa_q2_fixture.py 169
    /tmp/qa-venv/bin/python  ops/qa/qa_q2_amplades_graduacio.py
"""
import json
import mimetypes
import pathlib
import sys

from playwright.sync_api import sync_playwright

REPO = pathlib.Path(__file__).resolve().parents[2]
DIST = REPO / 'frontend' / 'dist'
FIXTURE = pathlib.Path(__file__).resolve().parent / 'qa_q2_fixture.json'
BASE = 'https://staging.fhorttextile.tech'

#: Tolerància en px. És 1 i no 0 perquè el navegador arrodoneix subpíxels a cada cel·la; una
#: diferència real d'amplada (les de la captura eren de desenes de px) no s'hi amaga.
TOL = 1.0

#: Les CINC primeres columnes són les mateixes a les dues taules i van per POSICIÓ.
IDENTITAT = ['#', 'CAPA', 'POM', 'NOM', 'TALLA BASE']

DADES = json.loads(FIXTURE.read_text()) if FIXTURE.is_file() else None
PERFIL = {'id': 1, 'username': 'qa', 'nom_complet': 'QA', 'rol_nom': 'admin',
          'capabilities': ['configure', 'EXECUTE_TASKS', 'CLOSE_GATES'], 'idioma': 'ca'}
BUIT = {'count': 0, 'results': [], 'next': None, 'previous': None}


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


#: L'amplada REAL de cada columna: la del `th` de la primera fila de capçalera de la taula que
#: té més files (les dues pantalles en tenen una de sola, però ModelSheet en pot pintar d'altres
#: a la vora). Es mesura amb `getBoundingClientRect`, que és el computed de veritat.
JS_COLS = """
() => {
  const taules = Array.from(document.querySelectorAll('table'))
  if (!taules.length) return null
  const t = taules.sort((a, b) =>
    b.querySelectorAll('tbody tr').length - a.querySelectorAll('tbody tr').length)[0]
  const fila = t.querySelector('thead tr')
  if (!fila) return null
  return Array.from(fila.children).map(th => ({
    nom: (th.innerText || '').trim().split('\\n')[0].toUpperCase(),
    ample: Math.round(th.getBoundingClientRect().width * 10) / 10,
  }))
}
"""


def obre(ctx, ruta, lang='ca'):
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


def main():
    if DADES is None:
        print(f"✗ falta {FIXTURE.name} — genera'l amb qa_q2_fixture.py")
        return 1
    if not DIST.is_dir():
        print(f'✗ no hi ha bundle a {DIST}')
        return 1
    mid = DADES['_model_id']
    fallides = []
    print(f'== Q2 · amplades Graduació ↔ consulta · model {mid} ==')

    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(base_url=BASE, ignore_https_errors=True,
                            viewport={'width': 1600, 'height': 1200})

        pg_c, err_c, con_c = obre(ctx, f'/models/{mid}?tab=Mesures')
        cols_c = pg_c.evaluate(JS_COLS)
        pg_g, err_g, con_g = obre(ctx, f'/models/{mid}?tab=Mesures&mode=graduacio')
        cols_g = pg_g.evaluate(JS_COLS)

        if not cols_c or not cols_g:
            print(f'✗ no s\'ha trobat la taula (consulta={bool(cols_c)} graduació={bool(cols_g)})')
            return 1

        print('  consulta : ' + ' · '.join(f'{c["nom"] or "—"}={c["ample"]}' for c in cols_c))
        print('  graduació: ' + ' · '.join(f'{c["nom"] or "—"}={c["ample"]}' for c in cols_g))

        # ── 1 · el bloc d'identitat i el carril, per POSICIÓ ──────────────────────────────
        for i, etiqueta in enumerate(IDENTITAT):
            if i >= len(cols_c) or i >= len(cols_g):
                fallides.append(f'columna {i} ({etiqueta}) — una de les dues taules no la té')
                continue
            a, g = cols_c[i]['ample'], cols_g[i]['ample']
            if abs(a - g) > TOL:
                fallides.append(f'{etiqueta} (posició {i}): consulta {a}px · graduació {g}px '
                                f'(Δ {round(g - a, 1)}px)')

        # ── 2 · el forat: `#` no es pot endur l'espai sobrant ─────────────────────────────
        # A la captura, `#` era la columna més ampla de la taula. Aquí es demana el mínim
        # honest: que no sigui més ampla que la del NOM, que és la que porta text de debò.
        if cols_g[0]['ample'] > cols_g[3]['ample']:
            fallides.append(f'la columna # de la Graduació ({cols_g[0]["ample"]}px) és més ampla '
                            f'que la del NOM ({cols_g[3]["ample"]}px): torna a haver-hi el forat')

        # ── 3 · les quatre de la regla, per NOM ──────────────────────────────────────────
        per_nom_c = {c['nom']: c['ample'] for c in cols_c}
        for c in cols_g:
            if c['nom'] in per_nom_c and c['nom'] not in ('', '#'):
                if abs(per_nom_c[c['nom']] - c['ample']) > TOL:
                    fallides.append(f'{c["nom"]}: consulta {per_nom_c[c["nom"]]}px · '
                                    f'graduació {c["ample"]}px')

        for etiqueta, errs, cons in (('consulta', err_c, con_c), ('graduació', err_g, con_g)):
            if errs:
                fallides.append(f'{etiqueta} · error de pàgina: {errs[0][:140]}')
            if cons:
                fallides.append(f'{etiqueta} · consola bruta: {cons[0][:140]}')

        pg_c.close()
        pg_g.close()
        ctx.close()
        b.close()

    if fallides:
        print('\n🔴 FALLIDES')
        for f in fallides:
            print('  ✗', f)
        return 1
    print('\n🟢 Q2 · mateixes amplades a les dues pantalles · consola neta')
    return 0


if __name__ == '__main__':
    sys.exit(main())
