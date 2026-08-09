"""BLOC B · captures de les sis pantalles del CAMÍ DEL MODEL, contra el SERVEI VIU.

Mateix arnès que `qa_a4_garment_types.py`: el bundle surt de `frontend/dist` i tota crida a
`/api/` es reenvia al gunicorn de `127.0.0.1:8001` amb el `Host` del tenant. Amb fixtures la
foto sortiria bé fins i tot amb el backend vell, i el que s'ha de veure és el que el backend
DESPLEGAT contesta.

UN SOL FITXER PER A SIS TRAMS, i no sis còpies del mateix arnès: el que canvia entre trams és
la llista d'estats, no la manera de fotografiar-los. `FTT_QA_TRAM=a6` en tria un.

DOS TENANTS A POSTA per a la llista (A5). El banc de proves del bloc (`FTT-SS26-0001`) viu a
`fhort`, i `fhort` té UN SOL MODEL: amb ell es veuen les capçaleres i els estats buits, però no
l'ellipsis ni l'ordenació ni una graella de debò. `los` en té 51 i és on la llista s'ensenya
plena. Cap dels dos és una fixture: els dos són dades vives.

    FTT_QA_TOKEN=… [FTT_QA_HOST=…] [FTT_QA_TRAM=a5] venv/bin/python ops/qa/qa_blocb_captures.py

⚠️ LES ICONES SURTEN BUIDES A LES CAPTURES i no és un defecte de la pantalla: Tabler entra per
webfont des d'un CDN i aquest arnès intercepta `**/*`. Al navegador de debò hi són.
"""
import mimetypes
import os
import pathlib
import sys

import requests
from playwright.sync_api import sync_playwright

REPO = pathlib.Path(__file__).resolve().parents[2]
DIST = REPO / 'frontend' / 'dist'
OUT = pathlib.Path(__file__).resolve().parent / 'captures'
BASE = 'https://staging.fhorttextile.tech'
VIU = 'http://127.0.0.1:8001'
HOST_TENANT = os.environ.get('FTT_QA_HOST', 'fhorttextile.tech')
TRAM = os.environ.get('FTT_QA_TRAM', 'a5')
PREFIX = os.environ.get('FTT_QA_PREFIX', TRAM)
TOKEN = os.environ.get('FTT_QA_TOKEN', '')

#: UN ESTAT PER CAPTURA.
#: EL BANC DE PROVES del bloc: `FTT-SS26-0001` a `fhort` (ítem 19, GarmentPOMMap ZZ-TEST).
MODEL = os.environ.get('FTT_QA_MODEL', '1319')

#: UN ESTAT PER CAPTURA, per tram.
TRAMS = {
    'a5': [
        ('01_llista', '/models',
         'menu de pantalla + comptador amb cerca + graella canonica amb capcaleres', []),
        ('02_ordenada', '/models',
         'ordenacio per la columna MODEL (la icona de la capcalera passa a --gold)',
         [('click', 'th:has-text("MODEL")')]),
        ('03_cerca_buit', '/models?search=zzzz-no-existeix',
         'estat buit de la cerca: frase tenue en cursiva, mai caixa muda', []),
        ('04_acabats', '/models?vista=acabats',
         'la vista ACABATS: criteri de domini pendent, escrit i sense inventar cap fila', []),
        ('05_nou_model', '/models',
         'accio composta «Nou model ▾» amb estil de MENU (ni boto ni blau)',
         [('click', 'button:has-text("Nou model")')]),
        ('06_filtres', '/models',
         'el panell de filtres avancats, obert des del menu de pantalla',
         [('click', 'button:has-text("Filtres")')]),
    ],
    'a6': [
        ('01_dashboard', f'/models/{MODEL}',
         'menu de pantalla amb els 9 destins + Watchpoints a la dreta; identitat sobre fons', []),
        ('02_molla_4_segments', f'/models/{MODEL}?tab=Escalat',
         'el molla de pa a QUATRE segments: Tenant > Models > NOM > Seccio', []),
        ('03_accions', f'/models/{MODEL}',
         'Accions ▾ en secundari i Eliminar amb vora (mai plena en repos)',
         [('click', 'button:has-text("Accions")')]),
    ],
    'a7': [
        ('01_resum', f'/models/{MODEL}?tab=Resum',
         'dos contenidors 1fr/1fr: Informacio (pas 1) i Definicio del model (passos 2-3-4)', []),
        ('02_info_editant', f'/models/{MODEL}?tab=Resum',
         'pas 1 EN EDICIO IN-SITU, al mateix lloc on despres es llegeix',
         [('click', 'button:has-text("Editar")')]),
        ('03_talles_obert', f'/models/{MODEL}?tab=Resum',
         'subespai TALLES obert: --sel + filet d\'or, i el SEU desar es l\'unic blau',
         [('click', 'div:has(> span:text-is("Talles")) button:has-text("Canviar")')]),
        ('04_peca_obert', f'/models/{MODEL}?tab=Resum',
         'subespai PECA obert amb el navegador de peces (el mateix component del wizard)',
         [('click', 'div:has(> span:text-is("Peça")) button:has-text("Canviar")')]),
    ],
    'a8': [
        ('01_mesures', f'/models/{MODEL}?tab=Mesures',
         'tab Mesures en consulta: germanes en tabs amb subratllat d\'or i portes de la casa', []),
    ],
    'a10': [
        ('01_comprovacio', f'/models/{MODEL}?tab=Mesures',
         'Comprovacio: consulta pura, ZERO blaus, seccions plegables',
         [('click', 'button:has-text("Comprovació")')]),
        ('02_repas', f'/models/{MODEL}?tab=Mesures',
         'la germana Repas, amb el mateix llenguatge de tabs',
         [('click', 'button:has-text("Repàs")')]),
    ],
    # ── CODA (retocs d'Agus vistos a pantalla real) ───────────────────────────────────────
    'coda': [
        ('01_fons_pagina', '/models',
         'retoc 4 · el fons de pagina passa de --gray-l (gris fred) a --bg-page (blanc calid)', []),
        ('02_definicio_pom', f'/models/{MODEL}?tab=Mesures&mode=entry',
         'retocs 1+2+3 · carril de talla base CENTRAT · «Gravar POM» BLAU · «Descartar» terciaria',
         [('click', 'text=Introduir manualment')]),
    ],
}
PANTALLES = TRAMS[TRAM]



def main():
    if not TOKEN:
        sys.exit('Falta FTT_QA_TOKEN (passa\'l per entorn; no s\'imprimeix enlloc).')
    if not DIST.exists():
        sys.exit(f'No hi ha bundle a {DIST} — cal `npm run build`.')
    OUT.mkdir(exist_ok=True)
    sess = requests.Session()

    def handler(route, request):
        url = request.url
        cami = url.split(BASE, 1)[-1].split('?')[0] if url.startswith(BASE) else url
        if cami.startswith('/api/'):
            try:
                r = sess.request(
                    request.method, VIU + url.split(BASE, 1)[-1],
                    headers={'Host': HOST_TENANT, 'Authorization': f'Bearer {TOKEN}',
                             'Content-Type': request.header_value('content-type') or 'application/json'},
                    data=request.post_data_buffer, timeout=30)
                route.fulfill(status=r.status_code, body=r.content,
                              headers={'content-type': r.headers.get('content-type', 'application/json')})
            except Exception as e:
                route.fulfill(status=502, body=f'{{"error": "{e}"}}',
                              headers={'content-type': 'application/json'})
            return
        f = DIST / cami.lstrip('/')
        if not f.is_file():
            f = DIST / 'index.html'
        route.fulfill(status=200, body=f.read_bytes(),
                      headers={'content-type': mimetypes.guess_type(f.name)[0] or 'text/html'})

    with sync_playwright() as p:
        nav = p.chromium.launch()
        ctx = nav.new_context(viewport={'width': 1600, 'height': 1000})
        pag = ctx.new_page()
        pag.route('**/*', handler)
        pag.goto(BASE + '/', wait_until='domcontentloaded')
        pag.evaluate("([t]) => { localStorage.setItem('access_token', t);"
                     " localStorage.setItem('fhort.lang', 'ca') }", [TOKEN])
        for nom, ruta, què, accions in PANTALLES:
            pag.goto(BASE + ruta, wait_until='networkidle')
            pag.wait_for_timeout(1600)
            for gest in accions:
                try:
                    if gest[0] == 'click':
                        pag.locator(gest[1]).first.click()
                    elif gest[0] == 'fill':
                        pag.locator(gest[1]).first.fill(gest[2])
                    pag.wait_for_timeout(900)
                except Exception as e:
                    print(f'  ⚠️  {nom}: {gest[0]} {gest[1]} no ha anat ({e})')
            desti = OUT / f'{PREFIX}_{nom}.png'
            pag.screenshot(path=str(desti), full_page=True)
            print(f'✓ {desti.name:34} {ruta:34} {què}')
        nav.close()


if __name__ == '__main__':
    main()
