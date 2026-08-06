"""Fum del tram W2 — el pas 2 (navegador de tres columnes) i el pas 3 (proximitat).

## Per què existeix

`npm run build` no EXECUTA res: empaqueta. El defecte que aquest tram podia introduir —un
component nou muntat dins d'una pàgina de 950 línies plena de hooks— és exactament el que un
verd de build no veu (v. `qa_mount_modelsheet.py`, mateixa lliçó, mateix projecte).

Obre el bundle REAL de `frontend/dist` (el mateix que nginx publica) i comprova el que la
maqueta_wizard_model_v1 fixa:

  1. el pas 2 MUNTA i pinta les tres columnes amb els seus recomptes;
  2. la CASCADA respon: clicar un grup omple famílies, clicar una família omple ítems;
  3. la CERCA acota i el comptador ho diu;
  4. res queda amagat: els nodes sense coincidències s'ATENUEN i segueixen clicables;
  5. el pas 3 ordena per PROXIMITAT amb el run del client davant i CAP sistema amagat;
  6. consola neta i els tres idiomes.

Les dades venen de `qa_w2_fixture.json`, capturat de l'API REAL amb `qa_w2_fixture.py`: les
formes són les del producte, no les que li aniria bé al fum.

## Ús

    backend/venv/bin/python ops/qa/qa_w2_fixture.py     # captura les dades (no van a git)
    /tmp/qa-venv/bin/python  ops/qa/qa_w2_wizard.py     # corre el fum

El `qa_w2_fixture.json` NO es commiteja: és un bolcat del catàleg viu del tenant, es regenera
en segons, i el que ha de viure a git és com obtenir-lo, no la còpia d'un dia concret.
"""
import json
import mimetypes
import pathlib
import sys

from playwright.sync_api import sync_playwright

REPO = pathlib.Path(__file__).resolve().parents[2]
DIST = REPO / 'frontend' / 'dist'
FIXTURE = pathlib.Path(__file__).resolve().parent / 'qa_w2_fixture.json'
BASE = 'https://staging.fhorttextile.tech'

if not FIXTURE.is_file():
    sys.exit(f'✗ falta {FIXTURE.name} — genera\'l primer:\n'
             f'    backend/venv/bin/python ops/qa/qa_w2_fixture.py')
DADES = json.loads(FIXTURE.read_text())
BUIT = {'count': 0, 'results': [], 'next': None, 'previous': None}
PERFIL = {'id': 1, 'username': 'qa', 'nom_complet': 'QA', 'rol_nom': 'admin',
          'capabilities': ['configure', 'EXECUTE_TASKS'], 'idioma': 'ca'}


def _stub(path):
    if path in DADES:
        return DADES[path]
    if '/customers/' in path and path.rstrip('/').split('/')[-1].isdigit():
        return DADES.get('/api/v1/customers/7/', {})
    if '/me/' in path or '/perfil/' in path:
        return PERFIL
    if '/next-ref/' in path:
        return {'ref': 'BRW-FW26-0001', 'codi_intern': 'BRW-FW26-0001'}
    return BUIT


def _handler(route):
    url = route.request.url
    path = url.split(BASE, 1)[-1].split('?')[0] if BASE in url else url.split('?')[0]
    if '/api/' in path:
        route.fulfill(status=200, content_type='application/json',
                      body=json.dumps(_stub(path), ensure_ascii=False))
        return
    f = DIST / (path.lstrip('/') or 'index.html')
    if not f.is_file():
        f = DIST / 'index.html'
    route.fulfill(status=200, body=f.read_bytes(),
                  content_type=mimetypes.guess_type(str(f))[0] or 'text/html')


def _obre(ctx, ruta, idioma='ca'):
    page = ctx.new_page()
    errors, consola = [], []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('console', lambda m: consola.append(f'{m.type}: {m.text}') if m.type == 'error' else None)
    page.route('**/*', _handler)
    # La clau de l'idioma és `fhort.lang` (i18n/index.js: `lookupLocalStorage`), no la
    # `i18nextLng` per defecte d'i18next. Amb la clau equivocada tot sortia en anglès i les
    # comprovacions de text en català passaven de llarg sense dir res.
    page.add_init_script(
        "localStorage.setItem('access_token','qa');"
        f"localStorage.setItem('fhort.lang','{idioma}');")
    page.goto(f'{BASE}{ruta}', wait_until='networkidle', timeout=45000)
    page.wait_for_timeout(900)
    return page, errors, consola


NEXT = {'ca': 'Següent', 'es': 'Siguiente', 'en': 'Next'}


def _al_pas_2(page, idioma='ca'):
    """El pas 2 s'hi arriba pel GEST, no per URL: `?block=` només el llegeix el mode encastat.

    De passada, això fa passar el fum pel gate del pas 1 de Sessió 2 (client + temporada), que
    és qui decideix si «Següent» es pot prémer.
    """
    # El PRIMER `select` de la pàgina és el canviador d'idioma, no el de client: es tria pel
    # contingut (el que porta BRW a les opcions), que és l'únic que no depèn de l'ordre del DOM.
    sel = None
    for i in range(page.locator('select').count()):
        s = page.locator('select').nth(i)
        if 'BRW' in s.inner_html():
            sel = s
            break
    if sel is None:
        raise AssertionError('no s\'ha trobat el selector de client amb BRW')
    sel.select_option(index=[o.strip() for o in sel.inner_text().split('\n')].index(
        next(o.strip() for o in sel.inner_text().split('\n') if o.strip().startswith('BRW'))))
    page.get_by_text('FW', exact=True).first.click()          # temporada
    page.wait_for_timeout(300)
    page.get_by_role('button', name=NEXT[idioma], exact=False).click()
    page.wait_for_timeout(900)


def _columnes(page):
    """Les tres columnes del finder: els fills directes de la graella de 3 columnes.

    Es localitza per l'estil en línia perquè el component no porta cap `data-testid` i el fum
    no és motiu per afegir-n'hi: clicar «la família» sense acotar la columna acabava picant la
    fila del GRUP, que sovint es diu igual.
    """
    graella = page.locator('div[style*="grid-template-columns: 1fr 1fr 1fr"]').first
    return [graella.locator('> div').nth(i) for i in range(3)]


def main():
    if not DIST.is_dir():
        print(f'✗ no hi ha bundle a {DIST} — fes `npm run build` primer'); return 1

    fallides = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(base_url=BASE, ignore_https_errors=True,
                                  viewport={'width': 1400, 'height': 1100})

        # ── 1..4 · EL PAS 2 ────────────────────────────────────────────────
        page, errors, consola = _obre(ctx, '/models/nou')
        _al_pas_2(page)
        body = page.inner_text('body')

        tdz = [e for e in errors if 'before initialization' in e]
        if tdz:
            fallides.append(f'TDZ al pas 2: {tdz[0][:120]}')
        if 'error inesperat' in body.lower() or 'unexpected error' in body.lower():
            fallides.append('pantalla d\'error de l\'AppErrorBoundary al pas 2')

        # (1) les tres columnes, pels seus títols. `inner_text()` torna el text RENDERITZAT i
        # aquests labels van amb `text-transform: uppercase`: la comparació ha de ser insensible
        # a majúscules o falla per una raó que no té res a veure amb el producte.
        low = body.lower()
        for titol in ('grup', 'família', 'item'):
            if titol not in low:
                fallides.append(f'falta la columna «{titol}» al pas 2')

        # el text de la maqueta i el comptador
        if 'filtra per descarte' not in low:
            fallides.append('falta el títol «Filtra per descarte…»')
        if 'peces al catàleg' not in body:
            fallides.append('falta el comptador «N peces al catàleg»')

        total_items = DADES['/api/v1/garment-type-items/']['count']
        if f'{total_items} peces al catàleg' not in body:
            fallides.append(f'el comptador no diu {total_items} (diu una altra cosa)')
        else:
            print(f'  ✓ comptador correcte: {total_items} peces al catàleg')

        # (2) la cascada respon: grup → família → ítem
        grups = DADES['/api/v1/garment-groups/']['results']
        fams = DADES['/api/v1/garment-types/']['results']
        grup_amb_fam = next((g for g in grups if any(f['grup'] == g['codi'] for f in fams)), None)
        if grup_amb_fam is None:
            fallides.append('el fixture no té cap grup amb famílies — fum no concloent')
        else:
            col_grup, col_fam, col_item = _columnes(page)
            col_grup.get_by_role('button', name=grup_amb_fam['codi'], exact=False).first.click()
            page.wait_for_timeout(400)
            b2 = page.inner_text('body')
            fam0 = next(f for f in fams if f['grup'] == grup_amb_fam['codi'])
            nom_fam = fam0.get('nom_ca') or fam0.get('nom_client') or fam0.get('nom_en')
            if nom_fam and nom_fam not in b2:
                fallides.append(f'clicar el grup {grup_amb_fam["codi"]} no ha omplert famílies')
            else:
                print(f'  ✓ grup → família ({grup_amb_fam["codi"]} → {nom_fam})')

                col_fam.get_by_role('button', name=nom_fam, exact=False).first.click()
                page.wait_for_timeout(400)
                b3 = col_item.inner_text()
                its = [i for i in DADES['/api/v1/garment-type-items/']['results']
                       if i['garment_type'] == fam0['id']]
                if its and (its[0].get('name') or '') not in b3:
                    fallides.append(f'clicar la família {nom_fam} no ha omplert ítems')
                elif its:
                    print(f'  ✓ família → ítem ({nom_fam} → {its[0]["name"]})')
                    if 'POMs' not in b3:
                        fallides.append('la columna d\'ítems no mostra el recompte de POMs')

        # (3) la cerca acota i (4) el que no encaixa s'atenua però no desapareix
        page.get_by_placeholder('Cerca peça', exact=False).fill('zzzz-no-existeix')
        page.wait_for_timeout(500)
        b4 = page.inner_text('body')
        if f'0 de {total_items} peces encaixen' not in b4:
            fallides.append('la cerca sense coincidències no ho diu al comptador')
        else:
            print('  ✓ cerca sense coincidències: «0 de N peces encaixen»')
        if grup_amb_fam and grup_amb_fam['codi'] not in b4:
            fallides.append('CAP AMAGAT trencat: un grup ha desaparegut amb la cerca')
        else:
            print('  ✓ cap amagat: els grups segueixen a la llista amb 0 coincidències')

        if consola:
            fallides.append(f'consola bruta al pas 2: {consola[0][:120]}')
        else:
            print('  ✓ consola neta al pas 2')

        # ── 5 · EL PAS 3 · PROXIMITAT, CAP AMAGAT ──────────────────────────
        # El pas 3 vol un target: es tria la píndola «Dona» (WOMAN) i s'hi baixa pel gest.
        page.get_by_placeholder('Cerca peça', exact=False).fill('')
        page.wait_for_timeout(300)
        page.get_by_role('button', name='Dona', exact=False).first.click()
        page.wait_for_timeout(400)
        page.get_by_role('button', name='Següent', exact=False).click()
        page.wait_for_timeout(1200)
        b5 = page.inner_text('body')

        sist = [s for s in DADES['/api/v1/size-systems/']['results'] if s.get('talles')]
        woman = [s for s in sist if 'WOMAN' in (s.get('target_codis') or [])]
        altres = [s for s in sist if 'WOMAN' not in (s.get('target_codis') or [])]
        print(f'  · sistemes amb talles: {len(sist)} · amb target WOMAN: {len(woman)} '
              f'· la resta: {len(altres)}')

        # (a) CAP AMAGAT: hi han de ser TOTS, també els que no declaren WOMAN — que és
        #     exactament el que el filtre d'abans feia desaparèixer.
        perduts = [s['codi'] for s in sist if s['codi'] not in b5]
        if perduts:
            fallides.append(f'pas 3 · {len(perduts)} sistemes amagats: {perduts[:5]}')
        else:
            print(f'  ✓ pas 3 · cap amagat: hi son els {len(sist)} sistemes amb talles '
                  f'(inclosos els {len(altres)} que no declaren WOMAN)')

        # (b) PROXIMITAT: el run de BRW ha d'anar DAVANT dels canonics de WOMAN, i els
        #     canonics davant del run d'un altre client.
        def pos(codi):
            return b5.find(codi)

        brw = [s for s in woman if s.get('customer_codi') == 'BRW']
        canon = [s for s in woman if not s.get('customer_codi')]
        altre_client = [s for s in woman if s.get('customer_codi') and s.get('customer_codi') != 'BRW']
        if not brw:
            print('  ! el fixture no te cap run WOMAN de BRW — l\'ordre del client no es pot provar')
        else:
            p_brw = pos(brw[0]['codi'])
            if canon and not all(p_brw < pos(c['codi']) for c in canon):
                fallides.append(f'pas 3 · el run de BRW ({brw[0]["codi"]}) no va davant dels canonics')
            elif altre_client and not all(pos(c['codi']) < pos(a['codi'])
                                          for c in canon for a in altre_client):
                fallides.append('pas 3 · un canonic no va davant del run d\'un altre client')
            else:
                ordre = sorted([s for s in woman], key=lambda s: pos(s['codi']))
                print('  ✓ pas 3 · proximitat: ' + ' › '.join(
                    f'{s["codi"]}[{s.get("customer_codi") or "canonic"}]' for s in ordre))

        # (c) l'etiqueta del run de client, que es la que la maqueta demana
        if brw and 'Run de client' not in b5:
            fallides.append('pas 3 · falta l\'etiqueta «Run de client»')
        elif brw:
            print('  ✓ pas 3 · etiqueta «Run de client · BRW» present')

        page.close()

        # ── 6 · ELS TRES IDIOMES ───────────────────────────────────────────
        esperat = {'ca': 'Filtra per descarte', 'es': 'Filtra por descarte',
                   'en': 'Filter by discarding'}
        for idioma, text in esperat.items():
            pg, errs, cons = _obre(ctx, '/models/nou', idioma)
            _al_pas_2(pg, idioma)
            b = pg.inner_text('body')
            if text.lower() not in b.lower():
                fallides.append(f'i18n {idioma}: no surt «{text}»')
            elif cons:
                fallides.append(f'i18n {idioma}: consola bruta → {cons[0][:100]}')
            else:
                print(f'  ✓ {idioma}: «{text}» · consola neta')
            pg.close()

        # ── F5 sobre el pas 2 ──────────────────────────────────────────────
        pg, errs, cons = _obre(ctx, '/models/nou')
        _al_pas_2(pg)
        pg.reload(wait_until='networkidle')
        pg.wait_for_timeout(1000)
        # Després d'F5 el wizard torna al pas 1 (l'estat viu a React, no a la URL): el que es
        # comprova és que TORNA A MUNTAR sense petar i que s'hi pot tornar a baixar al pas 2.
        _al_pas_2(pg)
        if 'filtra per descarte' not in pg.inner_text('body').lower():
            fallides.append('després d\'F5 el pas 2 no torna a muntar')
        elif errs:
            fallides.append(f'F5: error de pàgina → {errs[0][:120]}')
        else:
            print('  ✓ F5: el pas 2 torna a muntar, sense errors')
        pg.close()

        browser.close()

    print()
    if fallides:
        print(f'✗ {len(fallides)} problema(es):')
        for f in fallides:
            print(f'   · {f}')
        return 1
    print('✓ fum W2 verd')
    return 0


if __name__ == '__main__':
    sys.exit(main())
