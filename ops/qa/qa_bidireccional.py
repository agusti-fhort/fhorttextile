"""BIDIRECCIONAL MESURADA · maqueta ↔ pantalla, element per element, amb valors COMPUTATS.

⚠️ **PER QUÈ EXISTEIX.** La bidireccional era un procediment de LECTURA: obrir la maqueta, obrir
el JSX, comparar. Així es va donar per bona una selecció `--sel`+daurada on la maqueta diu, amb
el comentari escrit al costat, `.tg.on{background:var(--ok-bg)…} /* esmena Agus: inclòs = verd */`.
Llegir dos fitxers i creure que diuen el mateix no és verificar-ho.

Aquest script fa la comparació **contra valors computats de les dues bandes**:

  · obre la MAQUETA (fitxer local, `file://`) i, per a cada selector d'interès, en llegeix
    `getComputedStyle` — el color, la mida, el pes, el radi que el navegador realment pinta;
  · obre la PANTALLA (bundle de `frontend/dist` + API viva) i llegeix el mateix de l'element
    equivalent;
  · imprimeix les dues columnes UNA AL COSTAT DE L'ALTRA i marca les que no casen.

Cap dels dos costats s'escriu a mà: si la maqueta canvia, la referència canvia sola.

    FTT_QA_TOKEN=... /tmp/qa-venv/bin/python ops/qa/qa_bidireccional.py
"""
import mimetypes
import os
import pathlib
import sys

import requests
from playwright.sync_api import sync_playwright

REPO = pathlib.Path(__file__).resolve().parents[2]
DIST = REPO / 'frontend' / 'dist'
MAQ = REPO / 'ops' / 'maquetes'
BASE = 'https://staging.fhorttextile.tech'
VIU = 'http://127.0.0.1:8001'
HOST_TENANT = os.environ.get('FTT_QA_HOST', 'fhorttextile.tech')
TOKEN = os.environ.get('FTT_QA_TOKEN', '')

#: Les propietats que decideixen si dos elements «són el mateix» a ull.
PROPS = ['backgroundColor', 'color', 'vora', 'fontSize', 'fontWeight',
         'fontStyle', 'borderTopLeftRadius', 'textTransform']

#: (tram, què és, fitxer de maqueta, selector a la maqueta, gestos a la MAQUETA,
#:  ruta, gestos a la PANTALLA, selector a la pantalla)
#: Els selectors de pantalla van per TEXT o per ARIA a posta: són el que un humà veu, no una
#: classe interna. Els gestos són el que cal fer, a CADA banda, per arribar a l'estat que es
#: compara — sense ells `.tg.on` no existeix ni a la maqueta (les pastilles les pinta el seu JS).
CASOS = [
    # ── A2 · Size Library ────────────────────────────────────────────────────────────────
    ('A2', 'capa de restricció TRIADA (inclusió)', 'maqueta_size_library_v3.html',
     '.tg.on', [('click', '.run >> nth=0')],
     '/size-library', [('click', 'button:has-text("Alpha EU — Women")'),
                       ('click', 'div:has(> span:text-is("Target")) button:has-text("Woman") >> nth=0')],
     'div:has(> span:text-is("Target")) button[aria-pressed="true"]'),
    ('A2', 'capa de restricció NO triada', 'maqueta_size_library_v3.html',
     '.tg:not(.on)', [('click', '.run >> nth=0')],
     '/size-library', [('click', 'button:has-text("Alpha EU — Women")')],
     'div:has(> span:text-is("Target")) button[aria-pressed="false"]'),
    ('A2', 'fila del run SELECCIONADA («on soc»)', 'maqueta_size_library_v3.html',
     '.run.on', [],
     '/size-library', [('click', 'button:has-text("Alpha EU — Women")')],
     'button[aria-current="true"]'),
    ('A2', 'capçalera de secció de la fitxa', 'maqueta_size_library_v3.html',
     '.sec .h', [],
     '/size-library', [('click', 'button:has-text("Alpha EU — Women")')],
     'div:has(> span:text-is("Restriccions"))'),
    ('A2', 'estat buit («no declarat»)', 'maqueta_size_library_v3.html',
     '.kv .v.buit', [],
     '/size-library', [('click', 'button:has-text("Alpha EU — Women")')],
     'text=/no vol dir/'),
    ('A2', 'rètol de camp de la fitxa', 'maqueta_size_library_v3.html',
     '.kv .k', [],
     '/size-library', [('click', 'button:has-text("Alpha EU — Women")')], 'text=Target'),
    # ── A3 · Grading Rules ───────────────────────────────────────────────────────────────
    ('A3', 'capa de relació TRIADA (inclusió)', 'maqueta_grading_rules_v4.html',
     '.tg.on', [('click', 'button:has-text("Editar") >> nth=0'), ('click', '.tab >> nth=1')],
     '/poms/grading', [('fill', 'input[placeholder*="cerca"]', 'ZZ'),
                       ('click', 'button:has-text("Editar")'),
                       ('click', 'button:has-text("Relacions")'),
                       ('click', 'div:has(> div > span:text-is("Target")) button:has-text("Woman") >> nth=0')],
     'div:has(> div > span:text-is("Target")) button[aria-pressed="true"]'),
    ('A3', 'capa de relació NO triada', 'maqueta_grading_rules_v4.html',
     '.tg:not(.on)', [('click', 'button:has-text("Editar") >> nth=0'), ('click', '.tab >> nth=1')],
     '/poms/grading', [('fill', 'input[placeholder*="cerca"]', 'ZZ'),
                       ('click', 'button:has-text("Editar")'),
                       ('click', 'button:has-text("Relacions")')],
     'div:has(> div > span:text-is("Target")) button[aria-pressed="false"]'),
    ('A3', 'capçalera de bloc de relació', 'maqueta_grading_rules_v4.html',
     '.rblk .h', [('click', 'button:has-text("Editar") >> nth=0'), ('click', '.tab >> nth=1')],
     '/poms/grading', [('fill', 'input[placeholder*="cerca"]', 'ZZ'),
                       ('click', 'button:has-text("Editar")'),
                       ('click', 'button:has-text("Relacions")')],
     'div:has(> span:text-is("Construcció"))'),
    ('A3', 'capçalera de columna de la taula', 'maqueta_grading_rules_v4.html',
     'th', [('click', 'button:has-text("Editar") >> nth=0')],
     '/poms/grading', [('fill', 'input[placeholder*="cerca"]', 'ZZ'),
                       ('click', 'button:has-text("Editar")')],
     'th:has-text("RÈGIM")'),
    ('A3', 'capçalera de llista', 'maqueta_grading_rules_v4.html',
     '.lhead span', [],
     '/poms/grading', [], 'text=JOC DE REGLES'),
    ('A3', 'tab germana ACTIVA', 'maqueta_grading_rules_v4.html',
     '.tab.on', [('click', 'button:has-text("Editar") >> nth=0')],
     '/poms/grading', [('fill', 'input[placeholder*="cerca"]', 'ZZ'),
                       ('click', 'button:has-text("Editar")')],
     'button[aria-current="true"]'),
    ('A3', 'nom del joc a la capçalera', 'maqueta_grading_rules_v4.html',
     '.shead .t', [('click', 'button:has-text("Editar") >> nth=0')],
     '/poms/grading', [('fill', 'input[placeholder*="cerca"]', 'ZZ'),
                       ('click', 'button:has-text("Editar")')],
     'span:text-is("ZZ-TEST · Chino BOTTOMS regular")'),
    # ── A1 · Catàleg de POMs ─────────────────────────────────────────────────────────────
    ('A1', 'fila SELECCIONADA («on soc»)', 'maqueta_cataleg_poms_v3.html',
     '.pom.on', [('click', '.pom >> nth=0')],
     '/poms', [], 'button[aria-current="true"]'),
    ('A1', 'capçalera de categoria', 'maqueta_cataleg_poms_v3.html',
     '.cat', [],
     '/poms', [], 'div[style*="sticky"] >> nth=0'),
]

JS_UN = """
(el) => {
  const cs = getComputedStyle(el);
  const out = {};
  for (const p of %s) { if (p !== 'vora') out[p] = cs[p]; }
  // LA VORA, NOMÉS ON N'HI HA: un costat de gruix 0 computa `currentColor` i no és res que
  // ningú vegi. Es resumeixen els quatre costats amb gruix > 0 i estil != none.
  const v = [];
  for (const b of ['Top', 'Right', 'Bottom', 'Left']) {
    const w = parseFloat(cs['border' + b + 'Width']);
    if (w > 0 && cs['border' + b + 'Style'] !== 'none') v.push(b[0] + w + ':' + cs['border' + b + 'Color']);
  }
  out.vora = v.length ? v.join(' ') : '—';
  out.__txt = (el.textContent || '').trim().slice(0, 24);
  return out;
}
""" % PROPS


def _gestos(pag, gestos):
    for g in gestos:
        try:
            if g[0] == 'click':
                pag.locator(g[1]).first.click()
            elif g[0] == 'fill':
                pag.locator(g[1]).first.fill(g[2])
            pag.wait_for_timeout(600)
        except Exception:
            pass


def _mesura(pag, sel):
    """Els selectors van per TEXT o per ARIA a posta: és el que un humà veu, no una classe."""
    try:
        loc = pag.locator(sel).first
        if loc.count() == 0:
            return None
        return loc.evaluate(JS_UN)
    except Exception:
        return None


def _prep_pagina(pag, handler):
    pag.route('**/*', handler)


def main():
    if not TOKEN:
        sys.exit('Falta FTT_QA_TOKEN.')
    if not DIST.exists():
        sys.exit('Cal `npm run build`.')
    sess = requests.Session()

    def handler(route, request):
        url = request.url
        cami = url.split(BASE, 1)[-1].split('?')[0] if url.startswith(BASE) else url
        if cami.startswith('/api/'):
            try:
                r = sess.request(request.method, VIU + url.split(BASE, 1)[-1],
                                 headers={'Host': HOST_TENANT, 'Authorization': f'Bearer {TOKEN}',
                                          'Content-Type': 'application/json'},
                                 data=request.post_data_buffer, timeout=30)
                route.fulfill(status=r.status_code, body=r.content,
                              headers={'content-type': r.headers.get('content-type', 'application/json')})
            except Exception as e:
                route.fulfill(status=502, body=f'{{"error":"{e}"}}',
                              headers={'content-type': 'application/json'})
            return
        f = DIST / cami.lstrip('/')
        if not f.is_file():
            f = DIST / 'index.html'
        route.fulfill(status=200, body=f.read_bytes(),
                      headers={'content-type': mimetypes.guess_type(f.name)[0] or 'text/html'})

    desviacions = 0
    with sync_playwright() as p:
        nav = p.chromium.launch()
        # ── banda MAQUETA: fitxer local, sense cap intercepció ────────────────────────────
        maq_ctx = nav.new_context(viewport={'width': 1600, 'height': 1000})
        maq_pag = maq_ctx.new_page()
        maq_cache = {}

        def llegeix_maqueta(fitxer, sel, gestos_maq):
            clau = (fitxer, tuple(map(tuple, gestos_maq)))
            if maq_cache.get('clau') != clau:
                maq_pag.goto((MAQ / fitxer).as_uri(), wait_until='networkidle')
                maq_pag.wait_for_timeout(500)
                _gestos(maq_pag, gestos_maq)
                maq_cache['clau'] = clau
            return _mesura(maq_pag, sel)

        # ── banda PANTALLA: bundle del disc + API viva ────────────────────────────────────
        ctx = nav.new_context(viewport={'width': 1600, 'height': 1000})
        pag = ctx.new_page()
        _prep_pagina(pag, handler)
        pag.goto(BASE + '/', wait_until='domcontentloaded')
        pag.evaluate("([t]) => { localStorage.setItem('access_token', t);"
                     " localStorage.setItem('fhort.lang','ca') }", [TOKEN])

        tram_actual = None
        for tram, què, fitxer, sel_maq, gestos_maq, ruta, gestos, sel_pant in CASOS:
            if tram != tram_actual:
                print(f'\n═══════ {tram} ═══════')
                tram_actual = tram
            m = llegeix_maqueta(fitxer, sel_maq, gestos_maq)

            pant = None
            if sel_pant:
                pag.goto(BASE + ruta, wait_until='networkidle')
                pag.wait_for_timeout(1400)
                _gestos(pag, gestos)
                pant = _mesura(pag, sel_pant)

            print(f'\n  · {què}   [maqueta `{sel_maq}`]')
            if m is None:
                print('      ⚠️  la maqueta no té aquest element — cas a revisar')
                continue
            if pant is None:
                print('      ⚠️  NO MESURAT a la pantalla (estat no assolible amb les dades vives)')
                continue
            for prop in PROPS:
                a, b = m.get(prop), pant.get(prop)
                if a == b:
                    continue
                # el radi de píndola i el pes es comparen igual; la resta és senyal
                desviacions += 1
                print(f'      🔴 {prop:22} maqueta={a!r:26} pantalla={b!r}')
            else:
                pass
            if all(m.get(x) == pant.get(x) for x in PROPS):
                print('      ✓ casa a totes les propietats mesurades')
        nav.close()
    print(f'\n──────── {desviacions} desviacions mesurades ────────')
    sys.exit(1 if desviacions else 0)


if __name__ == '__main__':
    main()
