"""Fum de MUNTATGE del ModelSheet — la porta que el build no és.

## Per què existeix

El 31/07 el sprint G1/G2 va passar amb `manage.py check` net, `npm run build` verd i 11
tests de backend en verd, i el ModelSheet petava en obrir-se a QUALSEVOL model:

    ReferenceError: Cannot access 'ke' before initialization

Un `useEffect` col·locat AMUNT llegia dos `useState` declarats 100 línies més avall. L'array
de dependències d'un hook **s'avalua a cada render**, o sigui que la referència queia dins la
zona morta temporal i el component sencer moria.

Cap dels tres controls ho podia veure:
  · `npm run build` no EXECUTA res — Rollup empaqueta, no renderitza (la mateixa lliçó que ja
    hi ha escrita a `frontend/eslint.config.js` sobre W4/T5: «un verd de build no és un verd
    de producte»).
  · els tests de backend proven el contracte de l'API, no el muntatge del component;
  · el projecte no té runner de tests de JS (cap `test` a package.json, cap vitest/jest), o
    sigui que no hi havia cap lloc on una prova de render pogués viure.

Això ho tanca pel camí més barat que de debò executa el codi: obrir el bundle REAL al
navegador i mirar si el component arriba a pintar-se.

## Què comprova (i què no)

Comprova NOMÉS que el ModelSheet es MUNTA: cap `ReferenceError`, cap pantalla d'error de
l'AppErrorBoundary, i el codi del model visible al DOM. L'API va stubejada amb formes
mínimes a posta — la classe de defecte que caça es dispara durant el render, abans que cap
dada arribi, i dependre de dades reals faria el fum fràgil sense fer-lo més sensible.

NO és un test funcional: no valida el gest de Graduació ni la propagació. Per a això hi ha
els tests de backend i la QA manual.

## Ús

    python3 -m venv /tmp/qa-venv && /tmp/qa-venv/bin/pip install playwright
    /tmp/qa-venv/bin/playwright install chromium-headless-shell
    /tmp/qa-venv/bin/python ops/qa/qa_mount_modelsheet.py            # models per defecte
    /tmp/qa-venv/bin/python ops/qa/qa_mount_modelsheet.py 164 165 182

Surt amb codi 1 si algun model no munta → es pot encadenar a un gate.

## Paranys pagats (v. la nota d'e2e del vault)

  · UN SOL handler de `page.route`: l'últim registrat corre primer i `continue_()` se salta
    els anteriors, o sigui que els stubs d'API han d'anar A DINS del catch-all.
  · Es serveix `frontend/dist` del disc, que és exactament el que nginx publica: així el fum
    mira el MATEIX bundle que veurà la persona, no una compilació de test.
  · No cal token real: l'API va stubejada sencera (el gunicorn viu rebutja els tokens
    encunyats des del shell, i aquí no fa cap falta).
"""
import json
import mimetypes
import pathlib
import re
import sys

from playwright.sync_api import sync_playwright

REPO = pathlib.Path(__file__).resolve().parents[2]
DIST = REPO / 'frontend' / 'dist'
BASE = 'https://staging.fhorttextile.tech'
MODELS_PER_DEFECTE = [164, 165]

#: Formes mínimes. Només han de ser prou per fer arribar el component al render.
_MODEL = {
    'id': 0, 'codi_intern': 'QA-MOUNT-0001', 'nom_prenda': 'QA',
    'temporada': 'FW26', 'any': 2026, 'estat': 'Nou', 'fase': 'Proto',
    'size_run_model': 'S·M·L', 'base_size_label': 'M', 'fit_type': 'Regular',
    'target': 'WOMAN', 'construction': 'WOVEN', 'grading_rule_set': None,
    'garment_type_item': None, 'customer': None, 'measurements_version': 1,
    'tipologia': 'MARCA',
}
_TAULA = {
    'model_id': 0, 'codi_intern': 'QA-MOUNT-0001', 'base_size': 'M',
    'size_run': ['S', 'M', 'L'], 'size_run_complet': ['S', 'M', 'L'],
    'sizes_amb_dades': ['M'], 'deltes': {}, 'rows': [], 'total_poms': 0, 'tancat': False,
    'graduacio': {'font': None, 'es_proposta': False, 'rule_set_id': None,
                  'rule_set_nom': None, 'fit_model': 'Regular'},
}
_STATUS = {'te_dades_propagades': False, 'segellada': False, 'version_number': None,
           'estalitud': None, 'te_regles': False}
_PERFIL = {'id': 1, 'username': 'qa', 'nom_complet': 'QA', 'rol_nom': 'admin',
           'capabilities': ['EXECUTE_TASKS', 'CLOSE_GATES'], 'idioma': 'ca'}


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


def _handler(route):
    path = route.request.url.split(BASE, 1)[-1].split('?')[0]
    if path.startswith('/api/'):
        route.fulfill(status=200, content_type='application/json',
                      body=json.dumps(_stub(path)))
        return
    f = DIST / (path.lstrip('/') or 'index.html')
    if not f.is_file():
        f = DIST / 'index.html'          # fallback de SPA
    route.fulfill(status=200, body=f.read_bytes(),
                  content_type=mimetypes.guess_type(str(f))[0] or 'text/html')


def comprova(model_ids):
    if not DIST.is_dir():
        print(f'✗ no hi ha bundle a {DIST} — fes `npm run build` primer')
        return list(model_ids)

    fallen = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for mid in model_ids:
            ctx = browser.new_context(base_url=BASE, ignore_https_errors=True)
            page = ctx.new_page()
            errors = []
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.route('**/*', _handler)
            page.add_init_script("localStorage.setItem('access_token','qa')")

            page.goto(f'{BASE}/models/{mid}?tab=Mesures&mode=entry',
                      wait_until='networkidle', timeout=45000)
            page.wait_for_timeout(1200)

            body = page.inner_text('body')
            tdz = [e for e in errors if 'before initialization' in e]
            pantalla_error = ('error inesperat' in body.lower()
                              or 'unexpected error' in body.lower())
            muntat = _MODEL['codi_intern'] in body

            if tdz:
                print(f'  ✗ model {mid}: TDZ → {tdz[0][:100]}')
                fallen.append(mid)
            elif pantalla_error:
                print(f'  ✗ model {mid}: pantalla d\'error de l\'AppErrorBoundary')
                fallen.append(mid)
            elif not muntat:
                print(f'  ✗ model {mid}: el component no ha arribat a pintar-se')
                fallen.append(mid)
            else:
                extra = f' (altres errors de consola: {len(errors)})' if errors else ''
                print(f'  ✓ model {mid}: munta{extra}')
            ctx.close()
        browser.close()
    return fallen


if __name__ == '__main__':
    ids = [int(a) for a in sys.argv[1:]] or MODELS_PER_DEFECTE
    print(f'== fum de muntatge del ModelSheet · bundle {DIST} ==')
    fallen = comprova(ids)
    print()
    if fallen:
        print(f'✗ NO munten: {fallen}')
        sys.exit(1)
    print(f'✓ els {len(ids)} models munten')
