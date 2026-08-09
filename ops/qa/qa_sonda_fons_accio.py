"""SONDA C2 · fons DAURAT PLE i fons BLAU en elements CLICABLES, ruta per ruta.

L'auditoria de computats mesura VORES i MIDES; el que la coda C2 afirma és sobre el FONS,
i una afirmació que l'arnès no mira no és una mesura. Aquesta sonda reutilitza la mateixa
maquinària (mateix DIST, mateix token, mateix bloqueig d'escriptures) i només canvia el JS:

  · GOLD  = fons rgb(194,122,42) en un element clicable → el que la coda ha d'haver matat.
  · BLAU  = fons rgb(43,101,194) → el que la §5.1 dona a UNA primària per pantalla.

Es compta NOMÉS el clicable (button/a/[role=button]/[onclick]): el daurat de selecció, els
xips, les barres i els punts de color es queden i no són el subjecte de la coda.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import qa_auditoria_computats as Q  # noqa: E402

from playwright.sync_api import sync_playwright  # noqa: E402
import requests  # noqa: E402
import mimetypes  # noqa: E402

JS = r"""
() => {
  const GOLD = 'rgb(194, 122, 42)', BLAU = 'rgb(43, 101, 194)';
  const out = { gold: [], blau: [] };
  const txt = el => (el.textContent || '').trim().slice(0, 40) || `<${el.tagName.toLowerCase()}>`;
  for (const el of document.querySelectorAll('body *')) {
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') continue;
    const r = el.getBoundingClientRect();
    if (r.width <= 0 || r.height <= 0) continue;
    const clicable = el.tagName === 'BUTTON' || el.tagName === 'A'
      || el.getAttribute('role') === 'button' || typeof el.onclick === 'function'
      || cs.cursor === 'pointer';
    if (!clicable) continue;
    if (cs.backgroundColor === GOLD) out.gold.push(txt(el));
    if (cs.backgroundColor === BLAU) out.blau.push(txt(el));
  }
  return out;
}
"""


def main():
    if not Q.TOKEN:
        sys.exit('Falta FTT_QA_TOKEN.')
    sess = requests.Session()
    bloquejades = []

    def handler(route, request):
        url = request.url
        cami = url.split(Q.BASE, 1)[-1].split('?')[0] if url.startswith(Q.BASE) else url
        if cami.startswith('/api/'):
            if Q._es_escriptura(request.method, cami):
                bloquejades.append(f'{request.method} {cami}')
                route.fulfill(status=200, body=Q._cos_substitut(sess, cami),
                              headers={'content-type': 'application/json'})
                return
            try:
                r = sess.request(request.method, Q.VIU + url.split(Q.BASE, 1)[-1],
                                 headers={'Host': Q.HOST_TENANT,
                                          'Authorization': f'Bearer {Q.TOKEN}',
                                          'Content-Type': 'application/json'},
                                 data=request.post_data_buffer, timeout=30)
                route.fulfill(status=r.status_code, body=r.content,
                              headers={'content-type': r.headers.get('content-type', 'application/json')})
            except Exception as e:
                route.fulfill(status=502, body=f'{{"error":"{e}"}}',
                              headers={'content-type': 'application/json'})
            return
        f = Q.DIST / cami.lstrip('/')
        if not f.is_file():
            f = Q.DIST / 'index.html'
        route.fulfill(status=200, body=f.read_bytes(),
                      headers={'content-type': mimetypes.guess_type(f.name)[0] or 'text/html'})

    Q._comprova_sessio(sess, 'abans de començar')
    total_gold = 0
    with sync_playwright() as p:
        nav = p.chromium.launch()
        ctx = nav.new_context(viewport={'width': 1600, 'height': 1000})
        pag = ctx.new_page()
        pag.route('**/*', handler)
        pag.goto(Q.BASE + '/', wait_until='domcontentloaded')
        pag.evaluate("([t]) => { localStorage.setItem('access_token', t);"
                     " localStorage.setItem('fhort.lang','ca') }", [Q.TOKEN])
        for entrada in Q.PANTALLES:
            nom, ruta = entrada[0], entrada[1]
            senyal = entrada[2] if len(entrada) > 2 else None
            pag.goto(Q.BASE + ruta, wait_until='networkidle')
            pag.wait_for_timeout(1800)
            if senyal and pag.locator(senyal).count() == 0:
                print(f'{nom:38} 🛑 SENYAL ABSENT — no mesurat')
                continue
            d = pag.evaluate(JS)
            total_gold += len(d['gold'])
            marca = '🔴' if d['gold'] else ('  ' if len(d['blau']) <= 1 else '⚠️ ')
            print(f'{marca} {nom:38} daurat={len(d["gold"])}  blau={len(d["blau"])}'
                  + (f'  → {d["blau"]}' if d['blau'] else ''))
            for g in d['gold']:
                print(f'      🔴 DAURAT PLE CLICABLE: «{g}»')
        nav.close()
    Q._comprova_sessio(sess, "just després de l'última mesura")
    print(f'\n──── {total_gold} accions amb daurat ple ────')
    # El daurat clicable que quedi NO és automàticament un incompliment: la selecció, els xips
    # i els toggles es queden per ordre d'Agus. La sonda els ENSENYA amb el seu text perquè es
    # puguin classificar un a un al report; el veredicte no el dona el recompte.
    sys.exit(0)


main()
