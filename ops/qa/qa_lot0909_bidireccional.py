"""LOT 09/09 · AUDITORIA DE COMPUTATS + BIDIRECCIONAL de les pantalles del lot.

Mesura, no llegeix. Dues coses en una correguda i contra el MATEIX bundle:

  1. AUDITORIA DE COMPUTATS — per a cada pantalla del lot, `getComputedStyle` de cada vora
     visible i de cada badge/píndola/rètol, contra la paleta i els sostres de NORMA_LAYOUT.
     Reusa el JS i les taules de `qa_auditoria_computats` (una sola definició de què és
     conforme; dues divergirien el dia que la NORMA canviï).
  2. BIDIRECCIONAL — la llista d'encàrrecs contra `NORMA_LLISTA_canonica.html`, element per
     element i amb valors computats a les DUES bandes. La direcció maqueta→pantalla no pot
     trobar invencions per construcció, o sigui que també es fa pantalla→maqueta.

🛑 SENYAL OBLIGATORI. Cada cas porta el seu `data-ftt-screen`, i sense ell NO ES MESURA: es
crida. Una pantalla que no s'ha muntat dona zero incompliments, i zero és exactament el que
volem veure — és la tapadora que aquesta casa ja ha pagat dues vegades.

🔒 CAP ESCRIPTURA, amb UNA excepció declarada: `close-bulk` amb `cancel_pending:false` és la
PASSADA SECA del tancament en lot, i és condició per veure el diàleg (sense la seva resposta el
modal es queda a «Comptant…» i el botó apagat, o sigui que mesuraríem un estat de càrrega
creient que mesurem la confirmació). Que no escriu està verificat contra la BD: els WO segueixen
OPEN i amb 0 DEDUCTIONs després de cridar-la. Qualsevol altra escriptura es bloqueja i es diu.

    FTT_QA_TOKEN=... FTT_QA_DIST=/tmp/dist-qa0909 \
      /tmp/qa-venv/bin/python ops/qa/qa_lot0909_bidireccional.py
"""
import collections
import json
import mimetypes
import os
import pathlib
import sys

import requests
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from qa_auditoria_computats import (  # noqa: E402
    JS, VORES_OK, CROM, NEGRE, BASE, VIU, HOST_TENANT, _comprova_sessio,
)

REPO = pathlib.Path(__file__).resolve().parents[2]
DIST = pathlib.Path(os.environ.get('FTT_QA_DIST') or (REPO / 'frontend' / 'dist'))
MAQ = REPO / 'ops' / 'maquetes'
TOKEN = os.environ.get('FTT_QA_TOKEN', '')

#: Model amb comanda, numeral 2 i R3 FORA DE COMANDA — el banc del xip de FIT-12.
MODEL_FIT12 = 1497

#: (nom, ruta, senyal, gestos)
#: Els gestos van per TEXT o per ARIA a posta: són el que un humà veu, no una classe interna.
PANTALLES = [
    ('L1 · Encàrrecs · llista (OBERTS, el defecte)', '/comercial/encarrecs',
     '[data-ftt-screen="encarrecs-llista"]', []),
    ('L2 · Encàrrecs · llista · safata TANCATS', '/comercial/encarrecs?status=CLOSED',
     '[data-ftt-screen="encarrecs-llista"]', []),
    ('L3 · Encàrrecs · llista · amb SELECCIÓ (barra + fila triada)', '/comercial/encarrecs',
     '[data-ftt-screen="encarrecs-llista"]',
     [('click', 'tbody tr:first-child input[type="checkbox"]')]),
    ('L4 · Encàrrecs · llista · CERCA activa', '/comercial/encarrecs?search=desborda&status=TOTES',
     '[data-ftt-screen="encarrecs-llista"]', []),
    ('D1 · Encàrrec · detall', '/comercial/encarrecs/42',
     '[data-ftt-screen="encarrec-detall"]', []),
    (f'R1 · Pla de treball · contenidors de ronda (model {MODEL_FIT12})',
     f'/models/{MODEL_FIT12}', '[data-ftt-screen="pla-treball"]', []),
    ('M1 · Diàleg · tancament en LOT (després de la passada seca)', '/comercial/encarrecs',
     '[data-ftt-screen="modal-tancament-en-lot"]',
     [('click', 'tbody tr:first-child input[type="checkbox"]'),
      ('click', 'button:has-text("Tancar seleccionats")')]),
]

#: BIDIRECCIONAL · (què és, selector maqueta, selector pantalla, gestos, props?)
#: `props` és opcional i acota QUÈ es compara quan les propietats per defecte no volen dir res
#: en aquell element. En un `<input type=checkbox>`, per exemple, `color` i `fontSize` són
#: herència que no pinta res —el que el dibuixa és `accentColor` i la seva caixa—, i comparar-los
#: donava tres desviacions que no ho eren. Acotar no és amagar: el que s'hi posa és el que
#: DECIDEIX si els dos elements són el mateix a ull.
#: La maqueta és `NORMA_LLISTA_canonica.html`, que és la referència de la §8e per a QUALSEVOL
#: llista canònica: no és «la maqueta d'encàrrecs» (no n'hi ha cap) sinó la LLEI de la forma.
BIDI = [
    # ⚠️ `th.c-nom` de la maqueta porta també `.sorted` (`th.sorted{color:var(--ink)}`), o sigui
    # que comparar-lo amb una capçalera QUALSEVOL de la pantalla és comparar dos estats
    # diferents. Es mesuren els dos, cadascun contra el seu igual.
    ('capçalera de columna · en repòs', 'thead th:not(.sorted)',
     'thead th:not([aria-sort])', []),
    ('capçalera de columna · ORDENANT', 'thead th.sorted',
     'thead th[aria-sort]', []),
    ('cel·la del NOM (dada reina)', 'tbody td.c-nom',
     'tbody tr:first-child td:nth-child(3)', []),
    ('cel·la secundària (col·lecció)', 'tbody td.c-col',
     'tbody tr:first-child td:nth-child(4)', []),
    ('caixa de la llista', '.listbox', 'table >> xpath=..', []),
    ('casella de fila', 'tbody td.c-chk input.chk',
     'tbody tr:first-child input[type="checkbox"]', [],
     ['accentColor', 'width', 'height']),
    ('fila TRIADA («on soc»)', 'tbody tr.on td:first-child',
     'tbody tr:first-child td:first-child',
     [('click', 'tbody tr:first-child input[type="checkbox"]')]),
    ('badge neutre', '.b.neutral', 'tbody tr:first-child td:nth-child(5) span', []),
]

#: El que el JS LLEGEIX de cada element…
PROPS_JS = ['backgroundColor', 'color', 'fontSize', 'fontWeight', 'textTransform',
            'borderTopLeftRadius', 'whiteSpace', 'accentColor', 'width', 'height']
#: …i el que es COMPARA per defecte. `width`/`height` NO hi són: depenen del contingut i del
#: nombre de columnes, i entre dos documents diferents (la maqueta té onze columnes i dades
#: inventades; la pantalla en té set i les de staging) no diuen res. Comparar-los donava deu
#: desviacions que no eren de crom sinó d'amplada de text. Es demanen cas per cas, on sí que
#: decideixen — la caixa d'una casella, per exemple, que la maqueta declara a 14×14.
PROPS = [p for p in PROPS_JS if p not in ('width', 'height')]
# S'avalua SOBRE L'ELEMENT, no sobre el document: els selectors de pantalla van per TEXT
# (`:has-text`) a posta —és el que un humà veu, no una classe interna— i això és sintaxi de
# Playwright que `document.querySelector` no entén.
JS_UN = """(el) => {
  const cs = getComputedStyle(el);
  const o = {};
  for (const p of %s) o[p] = cs[p];
  o.vora = cs.borderBottomWidth + ' ' + cs.borderBottomStyle + ' ' + cs.borderBottomColor;
  o.shadow = cs.boxShadow;
  return o;
}""" % json.dumps(PROPS_JS)


def _mesura(pagina, selector):
    """Valors computats del PRIMER element que casa, o None si no n'hi ha cap."""
    loc = pagina.locator(selector).first
    try:
        if loc.count() == 0:
            return None
    except Exception:
        return None
    try:
        return loc.evaluate(JS_UN)
    except Exception:
        return None


def _es_passada_seca(request):
    """La passada seca del lot: POST close-bulk amb `cancel_pending` fals. No escriu res."""
    if not request.url.endswith('/close-bulk/'):
        return False
    try:
        return json.loads(request.post_data or '{}').get('cancel_pending') is False
    except Exception:
        return False


def main():
    if not TOKEN:
        sys.exit('Falta FTT_QA_TOKEN.')
    if not DIST.exists():
        sys.exit(f'No hi ha bundle a {DIST} — cal `npm run build` (o `--outDir`).')
    print(f'BUNDLE MESURAT : {DIST}')
    print(f'MAQUETA        : {MAQ / "NORMA_LLISTA_canonica.html"}\n')

    sess = requests.Session()
    bloquejades, deixades = [], []

    def handler(route, request):
        url = request.url
        cami = url.split(BASE, 1)[-1].split('?')[0] if url.startswith(BASE) else url
        if cami.startswith('/api/'):
            escriu = request.method not in ('GET', 'HEAD', 'OPTIONS')
            if escriu and not _es_passada_seca(request):
                bloquejades.append(f'{request.method} {cami}')
                route.fulfill(status=200, body='{}',
                              headers={'content-type': 'application/json'})
                return
            if escriu:
                deixades.append(f'{request.method} {cami} (passada seca)')
            try:
                r = sess.request(request.method, VIU + url.split(BASE, 1)[-1],
                                 headers={'Host': HOST_TENANT, 'Authorization': f'Bearer {TOKEN}',
                                          'Content-Type': 'application/json'},
                                 data=request.post_data_buffer, timeout=30)
                route.fulfill(status=r.status_code, body=r.content,
                              headers={'content-type': r.headers.get('content-type', 'application/json')})
            except Exception as e:
                route.fulfill(status=502, body=json.dumps({'error': str(e)}),
                              headers={'content-type': 'application/json'})
            return
        f = DIST / cami.lstrip('/')
        if not f.is_file():
            f = DIST / 'index.html'
        route.fulfill(status=200, body=f.read_bytes(),
                      headers={'content-type': mimetypes.guess_type(f.name)[0] or 'text/html'})

    _comprova_sessio(sess, 'abans de començar')
    casos = desviacions = 0

    with sync_playwright() as p:
        nav = p.chromium.launch()
        ctx = nav.new_context(viewport={'width': 1600, 'height': 1000})
        pag = ctx.new_page()
        pag.route('**/*', handler)
        pag.goto(BASE + '/', wait_until='domcontentloaded')
        pag.evaluate("([t]) => { localStorage.setItem('access_token', t);"
                     " localStorage.setItem('fhort.lang','ca') }", [TOKEN])

        # ── 1 · AUDITORIA DE COMPUTATS ──────────────────────────────────────────────────
        print('╔══ 1 · AUDITORIA DE COMPUTATS ' + '═' * 46)
        for nom, ruta, senyal, gestos in PANTALLES:
            pag.goto(BASE + ruta, wait_until='networkidle')
            pag.wait_for_timeout(1500)
            for g in gestos:
                try:
                    pag.locator(g[1]).first.click(timeout=8000)
                    pag.wait_for_timeout(1200)
                except Exception as e:
                    print(f'\n═══ {nom} ═══\n    🛑 GEST FALLIT ({g[1]}): {str(e)[:90]}')
            print(f'\n═══ {nom}  ({ruta}) ═══')
            casos += 1
            if pag.locator(senyal).count() == 0:
                desviacions += 1
                print(f'    🛑 SENYAL ABSENT ({senyal}) — la pantalla NO s\'ha muntat.')
                print('       No es mesura: un verd aquí voldria dir «no hi havia res a mirar».')
                continue
            d = pag.evaluate(JS)
            fora = 0
            for color, info in sorted(d['vores'].items(), key=lambda kv: -kv[1]['n']):
                if color in VORES_OK:
                    continue
                if color == NEGRE:
                    fora += 1; desviacions += 1
                    print(f'    🔴 {color:24} ×{info["n"]:<4} VAR NO RESOLTA (currentColor)')
                    for e in info['ex']:
                        print(f'         · {e}')
                elif color in CROM:
                    print(f'    ·  {color:24} ×{info["n"]:<4} crom del sistema (§8b)')
                else:
                    fora += 1; desviacions += 1
                    print(f'    ⚠️  {color:24} ×{info["n"]:<4} FORA DE PALETA')
                    for e in info['ex']:
                        print(f'         · {e}')
            grans = [m for m in d['mides'] if m['fs'] > m['sostre']]
            print(f'    VORES: {len(d["vores"])} colors · {fora} fora de paleta'
                  f'   ·   MIDES: {len(d["mides"])} elements · {len(grans)} per sobre del sostre')
            for (tipus, fs), n in sorted(collections.Counter(
                    (m['tipus'], m['fs']) for m in grans).items(), key=lambda kv: -kv[1]):
                desviacions += 1
                ex = next(m for m in grans if m['tipus'] == tipus and m['fs'] == fs)
                print(f'    🔴 {tipus:8} {fs:.0f}px ×{n:<3} p.ex. «{ex["txt"]}»  {ex["cam"]}')

        # ── 2 · BIDIRECCIONAL ───────────────────────────────────────────────────────────
        print('\n╔══ 2 · BIDIRECCIONAL · llista d\'encàrrecs ↔ NORMA_LLISTA_canonica ' + '═' * 11)
        maq = ctx.new_page()
        maq.goto((MAQ / 'NORMA_LLISTA_canonica.html').as_uri(), wait_until='networkidle')
        maq.wait_for_timeout(400)
        for cas in BIDI:
            que, selm, selp, gestos = cas[0], cas[1], cas[2], cas[3]
            props = cas[4] if len(cas) > 4 else (['vora', 'shadow'] + PROPS)
            casos += 1
            vm = _mesura(maq, selm)
            pag.goto(BASE + '/comercial/encarrecs', wait_until='networkidle')
            pag.wait_for_timeout(1500)
            if pag.locator('[data-ftt-screen="encarrecs-llista"]').count() == 0:
                desviacions += 1
                print(f'\n  ── {que}\n     🛑 SENYAL ABSENT — no es mesura.')
                continue
            for g in gestos:
                try:
                    pag.locator(g[1]).first.click(timeout=8000); pag.wait_for_timeout(600)
                except Exception:
                    pass
            vp = _mesura(pag, selp)
            print(f'\n  ── {que}')
            if vm is None or vp is None:
                desviacions += 1
                banda = 'MAQUETA' if vm is None else 'PANTALLA'
                print(f'     🛑 ELEMENT ABSENT a la {banda} ({selm if vm is None else selp})')
                continue
            for k in props:
                a, b = vm.get(k), vp.get(k)
                if a == b:
                    print(f'     ✓ {k:22} {str(a)[:44]}')
                else:
                    desviacions += 1
                    print(f'     ✗ {k:22} maqueta={str(a)[:32]!r:36} pantalla={str(b)[:32]!r}')
        nav.close()

    _comprova_sessio(sess, "just després de l'última mesura")
    print('\n' + '═' * 78)
    print(f'RESULTAT · {casos} casos mesurats · {desviacions} desviacions')
    print(f'ESCRIPTURES BLOQUEJADES ({len(bloquejades)}): '
          f'{sorted(set(bloquejades)) or "cap"}')
    print(f'ESCRIPTURES DEIXADES PASSAR ({len(deixades)}): '
          f'{sorted(set(deixades)) or "cap"}   ← només la passada seca, que no escriu')
    return 0 if desviacions == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
