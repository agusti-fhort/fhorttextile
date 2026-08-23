"""QA DE PANTALLA · l'edició al catàleg de POMs i la LLEI de la nomenclatura (22/08).

## Per què aquest fum i no la pantalla viva

La QA de navegador contra staging vol un JWT que l'agent no pot emetre (provat el 21/08 per
dos camins). El camí que SÍ que executa el codi de debò és el de `qa_f4bis_columna_breaks.py`:
servir el **bundle REAL de `frontend/dist`** —el mateix que nginx publica— i stubejar `/api/`
sencera des del procés. El component, el CSS i els tokens són els de producció; el que es
fabrica és NOMÉS el payload.

## Què mesura, i per què aquests tres POMs

El payload porta tres files que són els tres graons de la llei d'Agus, i cadascuna existeix
per delatar una manera diferent de trencar-la:

    QA-SD   lligat al global, amb codi i nom PROPIS   → ha de sortir `QA-SD`, MAI `LOSPOM-548`
    QA-NU   lligat al global i SENSE res propi        → ha de sortir el global (últim recurs)
    QA-TO   tenant-only, sense global                 → ha de sortir el seu, i mai buit

🚨 La primera és el defecte que l'Agus va veure. Si algú torna a posar el global davant del
tenant, aquesta fila ho canta a la llista I a la fitxa alhora.

## I l'edició

Que el botó hi és, que obre el formulari amb els valors QUE LA FITXA ENSENYA (no els camps
crus: per a un POM lligat, el «com es mesura» que es veu és el del global i és el que el
copy-on-write conservarà), que l'avís de separació surt NOMÉS per als lligats, i que desar
envia **només el que ha canviat** — enviar `codi_client` sense que ningú l'hagi tocat
separaria POMs per desar una nota.

## Ús

    /tmp/qa-venv/bin/python ops/qa/qa_sobirania_cataleg_pantalla.py

Codi de sortida 1 si algun estat no es pinta. Captures a `ops/qa/captures/sobirania_*.png`.
"""
import json
import mimetypes
import pathlib
import sys

from playwright.sync_api import sync_playwright

REPO = pathlib.Path(__file__).resolve().parents[2]
DIST = REPO / 'frontend' / 'dist'
OUT = pathlib.Path(__file__).resolve().parent / 'captures'
BASE = 'https://staging.fhorttextile.tech'

#: Els PATCH que la pantalla envia, per poder-los mesurar (el punt del test de «només el
#: que ha canviat»: un cop de vista a la fitxa no ho pot dir).
PATCHES = []

#: El rol que `/me/` declara. La segona passada el baixa a `technician` per comprovar que els
#: botons d'escriptura DESAPAREIXEN: des del 22/08 les quatre escriptures d'aquesta pantalla
#: demanen CONFIGURE al servidor, i una porta que es veu oberta i torna 403 és pitjor que una
#: porta que no hi és. Llista d'un element perquè `_stub` la llegeixi per referència.
ROL = ['admin']


def pom(pk, codi_client, nom_client, *, global_codi=None, com=None, categoria=1):
    """Una fila de `/api/v1/poms/` amb la forma EXACTA de `POMMasterSerializer`.

    El resolutor del backend ja ha fet la seva feina quan el payload surt: `pom_code`,
    `name_en`, `abbreviation` i el «com es mesura» hi arriben RESOLTS. Aquí es reprodueix
    el resultat de la llei, que és el que la pantalla ha de pintar.
    """
    com = com or {}
    te_propi = bool(codi_client)
    return {
        'id': pk, 'codi_client': codi_client, 'nom_client': nom_client,
        'categoria': categoria, 'actiu': True, 'notes': '', 'pendent_revisio': False,
        'pom_global': 77 if global_codi else None,
        'pom_global_codi': global_codi, 'pom_global_nom': 'FRONT ARMHOLE' if global_codi else None,
        # ── els camps RESOLTS (llei: àlies > tenant > global) ──
        'pom_code': codi_client or global_codi or '',
        'name_en': nom_client or ('FRONT ARMHOLE' if global_codi else ''),
        'name_cat': nom_client or ('SISA DAVANTERA' if global_codi else ''),
        'abbreviation': codi_client or ('FR AH' if global_codi else ''),
        'categoria_nom': 'Tors',
        'tolerancia_default_minus': '0.60', 'tolerancia_default_plus': '0.60',
        'separat_de_global': '', 'separat_at': None, 'origen_import': '',
        **{c: com.get(c, '') for c in (
            'unitat', 'start_point', 'end_point', 'reference_point',
            'scope', 'orientation', 'state', 'line', 'body_section')},
        **{c: None for c in ('applies_woven', 'applies_knit', 'applies_swim',
                             'tol_prod_cm', 'tol_samp_cm', 'iso_ref',
                             'descripcio_en', 'descripcio_ca',
                             'body_measure_iso_codi', 'body_measure_iso_nom')},
        '_te_propi': te_propi,
    }


COM_DEL_GLOBAL = {
    'unitat': 'cm', 'start_point': 'Shoulder point', 'end_point': 'Underarm point',
    'reference_point': 'Along the armhole seam', 'scope': 'FULL', 'orientation': 'CURVED',
    'state': 'FLAT', 'line': 'ALONG CURVE', 'body_section': 'FRONT',
}

POMS = [
    # ① EL DEFECTE D'AGUS: lligat, però amb nomenclatura pròpia. Mana la seva.
    pom(101, 'QA-SD', 'Sisa davantera QA', global_codi='LOSPOM-548', com=COM_DEL_GLOBAL),
    # ② lligat i sense res propi: el global és l'ÚLTIM recurs, i aquí és l'únic que hi ha.
    pom(102, '', '', global_codi='LOSPOM-548', com=COM_DEL_GLOBAL),
    # ③ tenant-only, amb el «com es mesura» informat AL TENANT (el forat del tram 3).
    pom(103, 'QA-TO', 'Mesura pròpia QA',
        com={'unitat': 'cm', 'start_point': "De l'espatlla", 'scope': 'HALF'}),
]

_CATS = {'count': 1, 'next': None, 'previous': None,
         'results': [{'id': 1, 'codi': 'TORS', 'nom_ca': 'Tors', 'nom_en': 'Upper body',
                      'display_order': 1, 'actiu': True}]}

_VOCAB = {
    'unitats_pom': [{'codi': c, 'etiqueta': c} for c in ('cm', 'inch')],
    'scopes_pom': [{'codi': c, 'etiqueta': c} for c in ('HALF', 'FULL', 'CALCULATED')],
    'orientacions_pom': [{'codi': c, 'etiqueta': c} for c in
                         ('HORIZONTAL', 'VERTICAL', 'CIRCUMFERENCE', 'CURVED', 'DIAGONAL')],
    'estats_pom': [{'codi': c, 'etiqueta': c} for c in
                   ('FLAT', 'RELAXED', 'STRETCHED', 'ON_BODY')],
    'linies_pom': [{'codi': c, 'etiqueta': c} for c in
                   ('STRAIGHT', 'CURVED', 'ALONG CURVE', 'ANGLED')],
    'seccions_cos_pom': [{'codi': c, 'etiqueta': c} for c in
                         ('FRONT', 'BACK', 'SIDE', 'SLEEVE', 'BOTH', 'HEAD')],
    'regims_graduacio': [], 'fases_model': [], 'estats_model': [], 'fases_tasca': [],
}


def _stub(path):
    if '/pom-categories/' in path:
        return _CATS
    if '/vocabulari/' in path:
        return _VOCAB
    if '/us/' in path:
        return {'us': {'items': 0, 'families': 0, 'grups': 0, 'models': 0, 'rules': 0},
                'pot_esborrar': True, 'motiu': 'No s\'usa enlloc.', 'de_sistema': False,
                'observat': {'capes': [], 'instancies': []}, 'cascada': []}
    if '/customer-pom-aliases/' in path:
        return {'count': 0, 'results': [], 'next': None, 'previous': None}
    if '/poms/' in path:
        return {'count': len(POMS), 'next': None, 'previous': None,
                'results': [{k: v for k, v in p.items() if k != '_te_propi'} for p in POMS]}
    if '/translate/pom/' in path:
        return {'traduccions': {}}
    if '/me/' in path or '/perfil/' in path:
        return {'id': 1, 'username': 'qa', 'rol_nom': ROL[0],
                'capabilities': (['configure', 'execute_tasks'] if ROL[0] == 'admin'
                                 else ['execute_tasks'])}
    return {'count': 0, 'results': [], 'next': None, 'previous': None}


def _handler(route):
    url = route.request.url
    # El catch-all deixa passar el que NO és nostre: la fulla d'icones Tabler ve d'un CDN i
    # servint-li `index.html` com a CSS el bundle es queda sense cap glif.
    if not url.startswith(BASE):
        route.continue_()
        return
    path = url.split(BASE, 1)[-1].split('?')[0]
    if path.startswith('/api/'):
        if route.request.method == 'PATCH':
            PATCHES.append((path, json.loads(route.request.post_data or '{}')))
            pk = int(path.rstrip('/').split('/')[-1])
            fila = next(p for p in POMS if p['id'] == pk)
            route.fulfill(status=200, content_type='application/json', body=json.dumps(
                {k: v for k, v in fila.items() if k != '_te_propi'}))
            return
        route.fulfill(status=200, content_type='application/json',
                      body=json.dumps(_stub(path)))
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
                                  viewport={'width': 1500, 'height': 1000})
        page = ctx.new_page()
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.route('**/*', _handler)
        page.add_init_script("localStorage.setItem('access_token','qa');"
                             "localStorage.setItem('fhort.lang','ca')")

        page.goto(f'{BASE}/poms', wait_until='networkidle', timeout=45000)
        page.wait_for_timeout(1200)
        cos = page.inner_text('body')
        prova('el catàleg munta', 'QA-SD' in cos, cos[:200])
        prova('cap error de consola', not errors, errors[:1])
        page.screenshot(path=str(OUT / 'sobirania_llista.png'), full_page=True)

        # ── LA LLEI, A LA LLISTA ──────────────────────────────────────────────────────
        #
        # ⚠️ PER FILA, MAI CONTRA EL COS SENCER. El primer intent va fer `'LOSPOM-548' not in
        # cos` i va sortir vermell **amb el producte correcte**: la fila ② (lligada i sense res
        # propi) l'ha d'ensenyar, perquè és exactament el cas de l'últim recurs. Una asserció
        # que llegeix tota la pàgina no pot distingir «hi surt on toca» de «hi surt on no
        # toca», i el mateix li va passar a `FR AH` de la fitxa.
        fila_sd = page.locator('button:has-text("Sisa davantera QA")').first
        fila_to = page.locator('button:has-text("Mesura pròpia QA")').first
        txt_sd = fila_sd.inner_text()
        prova('🚨 el POM lligat amb codi propi ensenya EL SEU, no el global',
              'QA-SD' in txt_sd and 'LOSPOM-548' not in txt_sd, repr(txt_sd))
        prova('el POM sense res propi cau al global (últim recurs)',
              'LOSPOM-548' in cos, 'cap fila ensenya el global')
        prova('el POM tenant-only ensenya el seu codi', 'QA-TO' in fila_to.inner_text())

        # ── LA FITXA DEL LLIGAT ───────────────────────────────────────────────────────
        fila_sd.click()
        page.wait_for_timeout(500)
        # La fitxa és la SEGONA meitat del `split`: la llista i la fitxa comparteixen `body`.
        panell = page.locator('div[style*="grid"] > div').nth(1)
        fitxa = panell.inner_text()
        prova('la fitxa del lligat diu la nomenclatura de la CASA',
              'QA-SD' in fitxa and 'FR AH' not in fitxa and 'LOSPOM-548' not in fitxa,
              repr(fitxa[:300]))
        prova('i el «com es mesura» que hereta del global',
              'Shoulder point' in fitxa, repr(fitxa[-400:]))

        # ── L'EDICIÓ ──────────────────────────────────────────────────────────────────
        prova('hi ha el botó d\'editar', page.locator('button:has-text("Editar")').count() > 0)
        page.click('button:has-text("Editar")')
        page.wait_for_timeout(400)
        page.screenshot(path=str(OUT / 'sobirania_edicio_lligat.png'), full_page=True)

        vals = [e.input_value() for e in page.locator('section input[type=text]').all()]
        prova('el formulari neix amb el que la FITXA ensenyava, no buit',
              'Sisa davantera QA' in vals and 'QA-SD' in vals and 'Shoulder point' in vals,
              str(vals))
        cos_ed = panell.inner_text()
        prova('🚨 avisa que el POM ES SEPARARÀ (està lligat al global)',
              'SEPARA' in cos_ed.upper(), cos_ed[:300])
        seleccions = page.locator('section select').all_inner_texts()
        prova('els selects porten el vocabulari de la font única',
              any('CIRCUMFERENCE' in s for s in seleccions), str(seleccions)[:250])

        # canvia NOMÉS el nom i desa
        nom = page.locator('section input[type=text]').nth(0)
        nom.fill('Sisa del davant')
        page.click('button:has-text("Desar canvis")')
        page.wait_for_timeout(700)
        prova('desar envia NOMÉS el que ha canviat',
              len(PATCHES) == 1 and set(PATCHES[0][1]) == {'nom_client'}, str(PATCHES))
        prova('i no envia `pom_global` (la separació no és un camp del formulari)',
              all('pom_global' not in b for _, b in PATCHES), str(PATCHES))

        # ── EL TENANT-ONLY JA POT DIR COM ES MESURA ───────────────────────────────────
        fila_to.click()
        page.wait_for_timeout(500)
        f3 = panell.inner_text()
        prova('🚨 un POM tenant-only informat NO diu «no lligat» al camp que té valor',
              "De l'espatlla" in f3, f3[-500:])
        page.click('button:has-text("Editar")')
        page.wait_for_timeout(400)
        cos3 = panell.inner_text()
        prova('i editant-lo NO surt l\'avís de separació (no té de què separar-se)',
              'SEPARA' not in cos3.upper(), cos3[:300])
        page.screenshot(path=str(OUT / 'sobirania_edicio_propi.png'), full_page=True)

        # ── 🔴 LA SEGONA PASSADA: UN TÈCNIC NO VEU LES PORTES ─────────────────────────
        ROL[0] = 'technician'
        page.goto(f'{BASE}/poms', wait_until='networkidle', timeout=45000)
        page.wait_for_timeout(1200)
        fila_sd2 = page.locator('button:has-text("Sisa davantera QA")').first
        fila_sd2.click()
        page.wait_for_timeout(500)
        for etiqueta in ('Editar', 'Esborrar', 'Desactivar', 'Nou POM'):
            prova(f'un tècnic NO veu «{etiqueta}»',
                  page.locator(f'button:has-text("{etiqueta}")').count() == 0)
        prova('…però SÍ que llegeix la fitxa sencera',
              'Shoulder point' in page.locator('div[style*="grid"] > div').nth(1).inner_text())
        page.screenshot(path=str(OUT / 'sobirania_tecnic.png'), full_page=True)

        browser.close()

    print(f'\n  {len(ok)} verds · {len(fallits)} vermells')
    for f in fallits:
        print(f'    ✗ {f}')
    return 1 if fallits else 0


if __name__ == '__main__':
    sys.exit(main())
