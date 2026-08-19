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

#: 🔒 L'EXCEPCIÓ ÚNICA DEL PRODUCTE (Agus, 09/08 · NORMA_LAYOUT §1 · Acció): **la porta d'entrada
#: va en daurat ple**. Allà encara no s'és dins del producte, s'és davant de la MARCA: el botó
#: d'entrar no competeix amb cap altra acció de la pantalla i el daurat hi fa de logo.
#:
#: L'exclusió és per PREFIX DE RUTA i porta el MOTIU a dins perquè la sonda l'hagi de DIR cada
#: correguda. Una exclusió que només fa que el número baixi és pitjor que no tenir-la: el zero
#: que en surt ja no distingeix «no hi ha daurat» de «n'hi ha i no el mires». Aquí el daurat
#: d'aquestes rutes es compta igual, s'imprimeix igual, i el que canvia és NOMÉS el veredicte.
EXCEPCIONS = {
    '/login': 'porta d\'entrada · territori de MARCA (§1 · Acció, Agus 09/08)',
    '/entrar': 'porta d\'entrada · territori de MARCA (§1 · Acció, Agus 09/08)',
    '/reset-password': 'porta d\'entrada · territori de MARCA (§1 · Acció, Agus 09/08)',
}


def excepcio(ruta):
    """El motiu escrit si la ruta és una excepció ratificada; `None` si no ho és."""
    return next((m for p, m in EXCEPCIONS.items() if ruta.split('?')[0].startswith(p)), None)


#: Les portes NO són a `PANTALLES` (l'arnès mesura el producte amb sessió), o sigui que
#: l'exclusió de dalt no arribaria a disparar-se mai i l'excepció quedaria escrita i no
#: verificada. Aquestes es mesuren a part, en un context sense token. El reset demana `uid` i
#: `token` a la ruta: amb valors inventats la pantalla es munta igual i cau a l'estat `invalid`,
#: que és **precisament** un dels dos botons daurats que hi ha d'haver.
EXCEPCIONS_MESURABLES = [
    ('/login', EXCEPCIONS['/login']),
    ('/entrar', EXCEPCIONS['/entrar']),
    ('/reset-password/xx/yy', EXCEPCIONS['/reset-password']),
]
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
            motiu = excepcio(ruta)
            if not motiu:
                total_gold += len(d['gold'])
            marca = '🔒' if motiu else ('🔴' if d['gold'] else ('  ' if len(d['blau']) <= 1 else '⚠️ '))
            print(f'{marca} {nom:38} daurat={len(d["gold"])}  blau={len(d["blau"])}'
                  + (f'  → {d["blau"]}' if d['blau'] else ''))
            if motiu:
                # L'exclusió es DIU, no se silencia: qui llegeixi el zero de baix ha de poder
                # saber quines rutes hi han entrat per excepció i amb quin motiu ratificat.
                print(f'      🔒 EXCEPCIÓ RATIFICADA — {motiu}')
                continue
            for g in d['gold']:
                print(f'      🔴 DAURAT PLE CLICABLE: «{g}»')
        # ── LES PORTES, MESURADES DE DEBÒ ────────────────────────────────────────────────
        # Una excepció declarada i no mesurada seria un permís, no una mesura: el dia que algú
        # torni el blau aquí, res no ho diria. Es mesuren en un context NET (sense token al
        # localStorage) perquè amb sessió vàlida `/login` rebota al taulell i mesuraríem el
        # taulell creient que mesurem la porta — la primera tapadora, un altre cop.
        ctx_net = nav.new_context(viewport={'width': 1600, 'height': 1000})
        pag_net = ctx_net.new_page()
        pag_net.route('**/*', handler)
        for ruta, motiu in EXCEPCIONS_MESURABLES:
            pag_net.goto(Q.BASE + ruta, wait_until='networkidle')
            pag_net.wait_for_timeout(1200)
            d = pag_net.evaluate(JS)
            ok = '🔒' if d['gold'] and not d['blau'] else '🔴'
            print(f'{ok} PORTA {ruta:32} daurat={len(d["gold"])}  blau={len(d["blau"])}')
            print(f'      🔒 EXCEPCIÓ RATIFICADA — {motiu}')
            if not d['gold'] or d['blau']:
                print('      🔴 …però la pantalla NO la compleix: la porta ha de dur daurat ple '
                      'i cap blau. O s\'ha revertit sense voler, o la §1 ha canviat.')
        nav.close()
    Q._comprova_sessio(sess, "just després de l'última mesura")
    print(f'\n──── {total_gold} accions amb daurat ple ────')
    # El daurat clicable que quedi NO és automàticament un incompliment: la selecció, els xips
    # i els toggles es queden per ordre d'Agus. La sonda els ENSENYA amb el seu text perquè es
    # puguin classificar un a un al report; el veredicte no el dona el recompte.
    sys.exit(0)


main()
