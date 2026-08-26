"""FASE A — fum de PANTALLA de l'interruptor `FTT_PATTERNS_ENABLED`.

## Què prova

Que l'entrada «Patró» del menú de model apareix o no segons el bundle, i que la resta del
menú no es mou. Es corre contra els TRES builds que la fase declara:

    ABSENT  → present   (la xarxa de seguretat: cap entorn perd patrons per descuit)
    true    → present
    false   → ABSENT del menú, i `/models/:id/patro/taller` rebota a l'arrel

## Per què l'asserció compara BUILDS i no una llista d'etiquetes

El primer intent portava els noms de les seccions escrits en català i va donar vermell als
TRES casos alhora —senyal que el defecte era la sonda i no el producte—: el menú es pinta en
l'idioma que el detector del navegador tria, i allà deia `Summary`, `Grading`, `Pattern`. Una
llista d'etiquetes escrita a mà, doncs, mesura l'idioma del headless i no el flag.

El que es compara ara és el menú d'un build contra el d'un altre. Això és, a més, EXACTAMENT
la propietat que la fase promet —«el flag no toca res més»—: entre `true` i `false` la
diferència ha de ser d'UNA entrada, i entre `absent` i `true`, de CAP.

## Per què així

És el patró de `qa_mount_modelsheet.py`: es serveix el bundle REAL del disc i s'stubeja `/api/`
sencera des del procés. No cal JWT (el gunicorn viu rebutja els tokens encunyats des del shell)
i el que es pinta és el component real amb el seu CSS real.

La diferència amb aquell fum és que aquí no n'hi ha prou amb UN bundle: el flag és de BUILD, o
sigui que el que es compara són tres `dist/` diferents. Per això els directoris entren per
argument en lloc de sortir de `REPO/frontend/dist`.

⚠️ El que això NO prova: el pany del backend. Aquí l'API va stubejada i sempre respon 200 —
el 404 del servidor es mesura per HTTP contra un gunicorn propi (v. l'acta de la fase).

## Ús

    /tmp/qa-venv/bin/python ops/qa/qa_fase_a_flag_patterns.py \
        absent=/ruta/dist_absent true=/ruta/dist_true false=/ruta/dist_false

Codi de sortida 1 si algun cas no diu el que ha de dir.
"""
import json
import mimetypes
import pathlib
import re
import sys

from playwright.sync_api import sync_playwright

BASE = 'https://staging.fhorttextile.tech'
MODEL_ID = 1383

#: L'entrada del menú que el flag governa, en els tres idiomes que la casa serveix.
ETIQUETES_PATRO = ('Patró', 'Pattern', 'Patrón')

_MODEL = {
    'id': MODEL_ID, 'codi_intern': 'QA-FLAG-0001', 'nom_prenda': 'QA',
    'temporada': 'FW26', 'any': 2026, 'estat': 'Nou', 'fase': 'Proto',
    'size_run_model': 'S·M·L', 'base_size_label': 'M', 'fit_type': 'Regular',
    'target': 'WOMAN', 'construction': 'WOVEN', 'grading_rule_set': None,
    'garment_type_item': None, 'customer': None, 'measurements_version': 1,
    'tipologia': 'MARCA',
}
_TAULA = {
    'model_id': MODEL_ID, 'codi_intern': 'QA-FLAG-0001', 'base_size': 'M',
    'size_run': ['S', 'M', 'L'], 'size_run_complet': ['S', 'M', 'L'],
    'sizes_amb_dades': ['M'], 'deltes': {}, 'rows': [], 'total_poms': 0, 'tancat': False,
    'graduacio': {'font': None, 'es_proposta': False, 'rule_set_id': None,
                  'rule_set_nom': None, 'fit_model': 'Regular'},
}
_STATUS = {'te_dades_propagades': False, 'segellada': False, 'version_number': None,
           'estalitud': None, 'te_regles': False}
_PERFIL = {'id': 1, 'profile_id': 1, 'username': 'qa', 'nom_complet': 'QA',
           'rol_nom': 'admin', 'color_avatar': '#888888', 'idioma': 'ca',
           'capabilities': ['execute_tasks', 'define_tasks', 'schedule_fittings',
                            'close_gates', 'configure', 'view_team_tasks',
                            'manage_users', 'comercial'],
           'tenant': {'schema_name': 'fhort', 'nom': 'QA'}}


def _stub(path):
    if '/taula-mesures/' in path:
        return _TAULA
    if '/grading-status/' in path:
        return _STATUS
    if re.search(r'/models/\d+/$', path):
        return _MODEL
    if re.search(r'/(me|perfil)/', path):
        return _PERFIL
    return {'count': 0, 'results': [], 'next': None, 'previous': None}


def _fes_handler(dist):
    def handler(route):
        path = route.request.url.split(BASE, 1)[-1].split('?')[0]
        if path.startswith('/api/'):
            route.fulfill(status=200, content_type='application/json',
                          body=json.dumps(_stub(path)))
            return
        f = dist / (path.lstrip('/') or 'index.html')
        if not f.is_file():
            f = dist / 'index.html'          # fallback de SPA
        route.fulfill(status=200, body=f.read_bytes(),
                      content_type=mimetypes.guess_type(str(f))[0] or 'text/html')
    return handler


def _obre(browser, dist, url):
    ctx = browser.new_context(base_url=BASE, ignore_https_errors=True)
    page = ctx.new_page()
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.route('**/*', _fes_handler(dist))
    page.add_init_script("localStorage.setItem('access_token','qa')")
    page.goto(url, wait_until='networkidle', timeout=45000)
    page.wait_for_timeout(1200)
    return ctx, page, errors


def _pindoles(page):
    """Els textos del menú de pantalla del model (`ui/PageMenu`)."""
    return [t.strip() for t in page.eval_on_selector_all(
        'button, a', 'els => els.map(e => e.textContent)') if t and t.strip()]


def mesura(browser, nom, dist):
    """El menú i el destí de la ruta del taller, per a un build. Cap judici aquí."""
    dist = pathlib.Path(dist)
    if not (dist / 'index.html').is_file():
        print(f'  ✗ {nom}: no hi ha bundle a {dist}')
        return None

    ctx, page, errors = _obre(browser, dist, f'{BASE}/models/{MODEL_ID}')
    body = page.inner_text('body')
    menu = _pindoles(page)
    ctx.close()
    if 'QA-FLAG-0001' not in body:
        print(f'  ✗ {nom}: el ModelSheet no ha arribat a pintar-se')
        return None

    ctx, page, _ = _obre(browser, dist, f'{BASE}/models/{MODEL_ID}/patro/taller')
    ruta = page.url.split(BASE, 1)[-1]
    ctx.close()

    te_patro = any(t in ETIQUETES_PATRO for t in menu)
    print(f'  · {nom}: {len(menu)} entrades · «Patró» = {te_patro} · /patro/taller → {ruta}')
    if errors:
        print(f'    ! {len(errors)} errors de consola → {errors[0][:90]}')
    return {'menu': menu, 'ruta': ruta, 'te_patro': te_patro}


def judica(m):
    """Les assercions de la fase, totes sobre les mesures ja preses."""
    ok = True

    def diu(condicio, text):
        nonlocal ok
        print(('  ✓ ' if condicio else '  ✗ ') + text)
        ok = ok and condicio

    ruta_taller = f'/models/{MODEL_ID}/patro/taller'

    diu(m['true']['te_patro'], 'true: «Patró» ÉS al menú')
    diu(m['true']['ruta'] == ruta_taller, 'true: /patro/taller s\'obre')

    # A3-bis · la xarxa de seguretat: sense declarar res, res no es perd.
    diu(m['absent']['menu'] == m['true']['menu'],
        'ABSENT: el menú és idèntic al de true (cap entrada perduda per descuit)')
    diu(m['absent']['ruta'] == ruta_taller, 'ABSENT: /patro/taller s\'obre')

    diu(not m['false']['te_patro'], 'false: «Patró» NO és al menú')
    diu(m['false']['ruta'] == '/', 'false: /patro/taller rebota a l\'arrel')

    # I el que de debò importa: que no s'endugui res més per davant.
    perdudes = [t for t in m['true']['menu'] if t not in m['false']['menu']]
    diu(len(perdudes) == 1 and perdudes[0] in ETIQUETES_PATRO,
        f'false: el flag es queda UNA entrada i és la de patrons → {perdudes}')
    guanyades = [t for t in m['false']['menu'] if t not in m['true']['menu']]
    diu(not guanyades, f'false: no n\'apareix cap de nova → {guanyades}')
    return ok


if __name__ == '__main__':
    casos = dict(a.split('=', 1) for a in sys.argv[1:])
    if set(casos) != {'absent', 'true', 'false'}:
        print(__doc__)
        sys.exit(2)
    print('== FASE A · fum de pantalla del flag de patrons ==')
    mesures = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for nom in ('absent', 'true', 'false'):
            print(f'-- build «{nom}» ({casos[nom]})')
            mesures[nom] = mesura(browser, nom, casos[nom])
        browser.close()
    print()
    if any(v is None for v in mesures.values()):
        print('✗ algun build no s\'ha pogut mesurar')
        sys.exit(1)
    if not judica(mesures):
        print('\n✗ el flag NO diu el que ha de dir')
        sys.exit(1)
    print('\n✓ els tres builds diuen el que han de dir')
