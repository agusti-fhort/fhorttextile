"""§8b-quater · EL CROM ENGANXAT, MESURAT (Agus 09/08).

L'ordre: «TOP BAR + MENÚ DE PANTALLA fixos en scroll, com un sol bloc enganxat. Top bar al
Shell, menú a ui/PageMenu.jsx — un sol lloc cadascun. Fons --panel opac, filet inferior --line,
z-index sobre contingut i sota modals. Verifica a una pantalla llarga i una curta.»

**PER QUÈ ES MESURA I NO ES LLEGEIX** (§8d, i la lliçó del bloc A). `position: sticky` és el cas
de manual d'una propietat que llegint el codi sembla correcta i al navegador no fa res:

  · si un avantpassat té `overflow` diferent de `visible`, l'ancoratge passa a ser AQUELL
    scrollport — i si aquell no es desplaça mai, l'element no s'enganxa i ningú no ho veu;
  · l'element només es pot moure DINS del seu contenidor: si el contenidor fa la seva mateixa
    alçada, el recorregut és zero i el sticky és decoratiu;
  · el `top` ancora la CAIXA DE MARGE, no la caixa de vora: amb un `margin-top` negatiu —que és
    justament el que treu la barra dels 24px de padding del `<main>`— la barra s'atura on no toca.

Les tres coses són invisibles al fitxer. Per això aquest script llegeix
`getBoundingClientRect()` DESPRÉS D'HAVER FET SCROLL DE DEBÒ, que és l'única prova que hi ha.

QUÈ COMPROVA, a cada pantalla:
  1. abans de desplaçar-se, la top bar i el menú es toquen (cap forat, cap solapament);
  2. després de desplaçar-se 1200px, TOTS DOS segueixen exactament al mateix lloc;
  3. el menú s'atura exactament sota la top bar (`--chrome-top`);
  4. el fons del menú i el de la top bar són OPACS (alfa 1) — un fons translúcid deixaria
     transparentar el contingut que hi passa per sota, que és el defecte que la norma evita;
  5. el filet inferior de la top bar és `--line`;
  6. la z del bloc queda per sobre del contingut i per SOTA del menú lateral (100) i dels
     modals (150, `components/ui/overlay.js`);
  7. el contingut passa PER SOTA: al punt just sota el menú, `elementFromPoint` retorna el menú
     (o un fill seu) i no la fila de la llista que hi ha darrere.

    FTT_QA_TOKEN=... /tmp/qa-venv/bin/python ops/qa/qa_8bquater_crom.py

⚠️ **CAL CÓRRER-LO TAMBÉ CONTRA UN TENANT POBLAT.** Amb `fhort` (UN model), `/models` no
desborda ni amb la finestra baixa, i llavors la pantalla «llarga» no prova el desplaçament —
diu «no desborda» i passa. El tenant `los` en té 51 i és el que ho posa a prova de debò:

    FTT_QA_HOST=los.fhorttextile.tech FTT_QA_TOKEN=<token amb tenant_schema=los> \\
        /tmp/qa-venv/bin/python ops/qa/qa_8bquater_crom.py
"""
import mimetypes
import os
import pathlib
import sys

import requests
from playwright.sync_api import sync_playwright

REPO = pathlib.Path(__file__).resolve().parents[2]
DIST = REPO / 'frontend' / 'dist'
BASE = 'https://staging.fhorttextile.tech'
VIU = 'http://127.0.0.1:8001'
HOST_TENANT = os.environ.get('FTT_QA_HOST', 'fhorttextile.tech')
TOKEN = os.environ.get('FTT_QA_TOKEN', '')

#: Una LLARGA (la llista canònica, que sempre desborda) i una CURTA (mestre-detall que sovint
#: cap a la finestra). La curta és la que destapa el cas que ningú prova: sense recorregut,
#: `sticky` no s'ha de moure NI DESPLAÇAR-SE MALAMENT.
PANTALLES = [
    ('LLARGA · /models', '/models'),
    ('CURTA · /garment-types', '/garment-types'),
    # Lot comercial (S2). `/clients` és on la seva llista té més files; `/comercial/comandes` és
    # el cas de barra amb NOMÉS la fletxa (sense seccions ni acció primària), que és el que la
    # §8b.2 descriu i el que no s'havia mesurat enlloc.
    ('LLARGA · /clients', '/clients'),
    ('CURTA · /comercial/comandes', '/comercial/comandes'),
    # Lot tècnic (S1).
    # ⚠️ AQUESTA ESTÀ GATEJADA PER CAPACITAT (`define_tasks`/`configure`). Amb un usuari que no
    # les té —el del tenant `los`, per exemple— la pantalla pinta l'estat «sense accés» i **no
    # munta cap menú de pantalla**, i l'arnès ho dona com a incompliment. No ho és: és la
    # pantalla dient la veritat. S'ha de mesurar amb `fhort`, que és on l'usuari hi té dret.
    ('LLARGA · /planificacio', '/planificacio'),
]

LINE = 'rgb(232, 229, 224)'   # --line

JS = """
() => {
  const top = document.querySelector('header');
  const menu = document.querySelector('[data-ftt-pagemenu]');
  if (!top || !menu) return { falta: !top ? 'top bar' : 'menú de pantalla' };
  // EL BLOC DE CROM és el pare de la top bar: és ell qui s'enganxa, i qui hi ha a dins són la
  // top bar i el forat on el menú es teletransporta (§8b-quater). Abans s'hi mesurava el
  // CONTENIDOR DEL MENÚ dins de la pàgina, que és on vivia la implementació amb `:has()`.
  const bloc = top.parentElement;
  const csT = getComputedStyle(top), csM = getComputedStyle(menu), csH = getComputedStyle(bloc);
  const dinsDelBloc = bloc.contains(menu);
  const rT = top.getBoundingClientRect(), rM = menu.getBoundingClientRect();
  // Qui hi ha al punt just sota la vora inferior del menú, al mig de l'amplada del menú:
  // si el contingut hi passa per DAVANT, aquí no hi surt el menú.
  const sota = document.elementFromPoint(rM.left + rM.width / 2, rM.top + rM.height / 2);
  return {
    topDalt: rT.top, topBaix: rT.bottom, topAlt: rT.height,
    menuDalt: rM.top, menuBaix: rM.bottom, menuAlt: rM.height,
    posBloc: csH.position, topBloc: csH.top, zBloc: csH.zIndex, dinsDelBloc,
    posTop: csT.position, zTop: csT.zIndex,
    bgTop: csT.backgroundColor, bgMenu: csM.backgroundColor,
    filetTop: csT.borderBottomColor, filetTopAmpl: csT.borderBottomWidth,
    filetMenu: csM.borderBottomColor,
    chromeTop: getComputedStyle(document.documentElement).getPropertyValue('--chrome-top'),
    tapa: !!(sota && (sota === menu || menu.contains(sota))),
    scrollY: window.scrollY,
    docAlt: document.documentElement.scrollHeight,
    finestra: window.innerHeight,
  };
}
"""


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

    incompliments = []

    def mal(pant, què):
        incompliments.append(f'{pant} · {què}')
        print(f'      🔴 {què}')

    with sync_playwright() as p:
        nav = p.chromium.launch()
        # FINESTRA BAIXA A POSTA (520px). Amb 900px, `/models` del banc —que té UN model— fa
        # exactament l'alçada de la finestra i no desborda: la prova hauria passat sense provar
        # RES, que és la manera més silenciosa de donar un verd fals. El bloc enganxat ha de
        # funcionar a qualsevol alçada de finestra, i una de baixa és la que el posa a prova.
        ctx = nav.new_context(viewport={'width': 1600, 'height': 520})
        pag = ctx.new_page()
        pag.route('**/*', handler)
        pag.goto(BASE + '/', wait_until='domcontentloaded')
        pag.evaluate("([t]) => { localStorage.setItem('access_token', t);"
                     " localStorage.setItem('fhort.lang','ca') }", [TOKEN])

        for nom, ruta in PANTALLES:
            print(f'\n═══════ {nom} ═══════')
            pag.goto(BASE + ruta, wait_until='networkidle')
            pag.wait_for_timeout(1500)
            a = pag.evaluate(JS)
            if a.get('falta'):
                mal(nom, f"la pantalla no munta {a['falta']}")
                continue

            chrome = float((a['chromeTop'] or '56px').replace('px', '').strip() or 56)
            print(f"      · --chrome-top = {chrome}px · doc {a['docAlt']}px / finestra {a['finestra']}px")

            # (1) EN REPÒS: el menú comença exactament on acaba la top bar.
            if abs(a['menuDalt'] - a['topBaix']) > 1:
                mal(nom, f"en repòs hi ha {a['menuDalt'] - a['topBaix']:.1f}px entre la top bar "
                         f"(baix {a['topBaix']:.1f}) i el menú (dalt {a['menuDalt']:.1f})")
            else:
                print(f"      ✓ en repòs es toquen (top bar baix {a['topBaix']:.1f} = menú dalt {a['menuDalt']:.1f})")

            # (2)(3) DESPRÉS DE DESPLAÇAR-SE.
            desplaçable = a['docAlt'] - a['finestra']
            # `mouse.wheel` no desplaçava res (scrollY quedava a 0 amb 146px disponibles):
            # el desplaçament el fa el DOCUMENT i el cursor sintètic no hi arribava. `scrollTo`
            # sobre la finestra és el mateix gest que fa l'usuari amb la barra, i sí que es mesura.
            pag.evaluate('() => window.scrollTo(0, 1200)')
            pag.wait_for_timeout(700)
            b = pag.evaluate(JS)
            print(f"      · scrollY = {b['scrollY']:.0f}px (recorregut disponible {max(0, desplaçable)}px)")

            if b['scrollY'] < 1:
                print('      ⚠️  la pantalla no desborda: el bloc no es pot posar a prova aquí '
                      '(el que SÍ es comprova és que en repòs no s\'ha mogut de lloc)')
                if abs(b['topDalt'] - a['topDalt']) > 1 or abs(b['menuDalt'] - a['menuDalt']) > 1:
                    mal(nom, 'sense desplaçament, el bloc s\'ha mogut igualment')
            else:
                if abs(b['topDalt']) > 1:
                    mal(nom, f"la top bar s'ha desplaçat: dalt = {b['topDalt']:.1f} (esperat 0)")
                else:
                    print('      ✓ la top bar es queda enganxada a dalt')
                if abs(b['menuDalt'] - chrome) > 1:
                    mal(nom, f"el menú s'atura a {b['menuDalt']:.1f}px i la norma el vol a "
                             f"{chrome:.1f}px (= sota la top bar)")
                else:
                    print(f"      ✓ el menú s'atura exactament sota la top bar ({b['menuDalt']:.1f}px)")
                if not b['tapa']:
                    mal(nom, 'el contingut NO passa per sota del menú (hi ha alguna cosa al davant)')
                else:
                    print('      ✓ el contingut hi passa per sota (el menú és qui tapa)')

            # (4) OPACITAT. `rgba(…, 0.x)` o `transparent` deixarien veure el contingut.
            for etiqueta, color in (('top bar', b['bgTop']), ('menú', b['bgMenu'])):
                if 'rgba' in color or color == 'transparent':
                    mal(nom, f'el fons de la {etiqueta} NO és opac: {color}')
            if 'rgba' not in b['bgTop'] and 'rgba' not in b['bgMenu']:
                print(f"      ✓ fons opacs (top bar {b['bgTop']} · menú {b['bgMenu']})")

            # (5) FILET.
            if b['filetTop'] != LINE:
                mal(nom, f"el filet inferior de la top bar és {b['filetTop']} i la norma diu --line ({LINE})")
            else:
                print(f"      ✓ filet inferior de la top bar = --line ({b['filetTopAmpl']})")
            if b['filetMenu'] != LINE:
                mal(nom, f"el filet inferior del menú és {b['filetMenu']} i la norma diu --line ({LINE})")

            # (6) Z.
            z = b['zBloc']
            print(f"      · z del bloc de crom: {z} · sidebar 100 · modals 150")
            try:
                z_i = int(z)
                if not 0 < z_i < 100:
                    mal(nom, f'la z del bloc no queda sobre el contingut i sota el sidebar/modals ({z})')
            except ValueError:
                mal(nom, f'z-index del bloc sense valor numèric ({z})')

            if b['posBloc'] != 'sticky':
                mal(nom, f"el bloc de crom no és sticky ({b['posBloc']})")
            # ⚠️ I QUE SIGUIN DE DEBÒ UN SOL BLOC: el menú ha de ser DINS del mateix element
            # enganxat que la top bar. Enganxar-les per separat també les deixaria quietes, però
            # com a dues coses — i és el que l'ordre d'Agus descarta.
            if not b['dinsDelBloc']:
                mal(nom, 'el menú de pantalla NO és dins del bloc enganxat: són dues coses, '
                         'no un sol bloc')

    print(f'\n──────── {len(incompliments)} incompliments ────────')
    for i in incompliments:
        print(f'  · {i}')
    sys.exit(1 if incompliments else 0)


if __name__ == '__main__':
    main()
