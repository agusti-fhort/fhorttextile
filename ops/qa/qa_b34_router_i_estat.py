"""ARNÈS · B3 (el router de la tasca) i B4 (l'estat de les quatre portes) · model 1320.

⚠️ **CAP ESCRIPTURA.** Tot POST/PATCH/PUT/DELETE es respon localment amb l'eco del cos i es
censa. És la llei d'aquest banc: entrar al tab Mesures amb una tasca és un GEST que escriu al
domini (obre tasques, pot crear sessions de fitting), i l'Agus hi és treballant. L'arnès mesura
ON ATERRA la pantalla, no què desa.

B3 · EL TIPUS DE TASCA DECIDEIX EL MODE
  Entrar per `?tab=Mesures&task_id=<id>` aterrava SEMPRE a la superfície de treball, i sense
  sessió de fitting el `CheckMeasureEditor` cau a la font `check` — el carril d'entrada de POMs.
  O sigui: entrar per una tasca «Mesurar prenda» obria la pantalla de DEFINIR POMs amb el
  rellotge de mesurar la peça corrent al damunt.

    R1 · «Mesurar prenda» (`size_check`) → SESSIÓ DE FITTING, mai el carril
    R2 · «Definició POM» (`pom`)         → CARRIL D'ENTRADA
    R3 · i el rellotge corre al mode correcte: la tasca que es consumeix és la de la URL, i
         és la que queda registrada per pausar-se en sortir

B4 · LES QUATRE PORTES DIUEN ON ETS
    E1 · les quatre porten un FET del backend (`grading-status`), i cap es queda muda
    E2 · el que diu el stepper i el que diu el Dashboard COINCIDEIXEN quan els dos parlen

Les afirmacions es llegeixen a la pantalla real (el bundle del disc, `frontend/dist`) contra
l'API del gunicorn desplegat, amb el mateix reenviament que `qa_carril_mesures_1320.py`.

    FTT_QA_TOKEN=... /tmp/qa-venv/bin/python ops/qa/qa_b34_router_i_estat.py
"""
import json
import mimetypes
import os
import pathlib
import sys

import requests
from playwright.sync_api import sync_playwright

REPO = pathlib.Path(__file__).resolve().parents[2]
DIST = pathlib.Path(os.environ.get('FTT_QA_DIST') or (REPO / 'frontend' / 'dist'))
OUT = pathlib.Path(__file__).resolve().parent / 'captures'
BASE = 'https://staging.fhorttextile.tech'
# L'API. Per defecte el gunicorn desplegat; `FTT_QA_API` el reapunta a un servidor propi.
#
# ⚠️ EL GUNICORN SERVEIX EL CODI DE QUAN VA ARRENCAR. Mesurar un canvi de backend contra el
# servei desplegat sense reiniciar-lo mesura el codi VELL —i reiniciar-lo, amb una altra sessió
# treballant, li publica la feina a mig fer. La sortida és un servidor de disc a un altre port:
#
#     backend/venv/bin/python manage.py runserver 127.0.0.1:8123 --noreload   # (des de backend/)
#     FTT_QA_API=http://127.0.0.1:8123 FTT_QA_DIST=<el teu build> … qa_b34_router_i_estat.py
#
# El `Host:` del tenant es continua enviant igual: és per on django-tenants resol l'esquema.
VIU = os.environ.get('FTT_QA_API') or 'http://127.0.0.1:8001'
TOKEN = os.environ.get('FTT_QA_TOKEN', '')
MODEL = 1320

falles = []


def mira(nom, ok, detall=''):
    print(f'  {"✅" if ok else "❌"} {nom}' + (f' — {detall}' if detall else ''))
    if not ok:
        falles.append(nom)


def main():
    if not TOKEN:
        sys.exit('Falta FTT_QA_TOKEN')
    OUT.mkdir(exist_ok=True)
    sess = requests.Session()
    escriptures = []

    def api(cami):
        r = sess.get(VIU + cami, headers={'Host': 'staging.fhorttextile.tech',
                                          'Authorization': f'Bearer {TOKEN}'}, timeout=30)
        r.raise_for_status()
        return r.json()

    def handler(route, request):
        url = request.url
        cami = url.split(BASE, 1)[-1].split('?')[0] if url.startswith(BASE) else url
        if cami.startswith('/api/'):
            if request.method != 'GET':
                escriptures.append(f'{request.method} {cami}')
                route.fulfill(status=200, body=request.post_data or '{}',
                              headers={'content-type': 'application/json'})
                return
            try:
                r = sess.get(VIU + url.split(BASE, 1)[-1],
                             headers={'Host': 'staging.fhorttextile.tech',
                                      'Authorization': f'Bearer {TOKEN}'}, timeout=30)
                route.fulfill(status=r.status_code, body=r.content,
                              headers={'content-type': r.headers.get('content-type',
                                                                     'application/json')})
            except Exception as e:
                route.fulfill(status=502, body=json.dumps({'error': str(e)}),
                              headers={'content-type': 'application/json'})
            return
        f = DIST / cami.lstrip('/')
        if not f.is_file():
            f = DIST / 'index.html'
        route.fulfill(status=200, body=f.read_bytes(),
                      headers={'content-type': mimetypes.guess_type(f.name)[0] or 'text/html'})

    # ── Les tasques del model, per saber quin task_id és de quin tipus ────────────────────
    tasques = api(f'/api/v1/model-task-items/?model={MODEL}')
    files = tasques.get('results') or tasques
    per_codi = {t['task_type_code']: t for t in files}
    print('\nTASQUES del model:', {c: (t['id'], t['status']) for c, t in per_codi.items()})
    estat = api(f'/api/v1/models/{MODEL}/grading-status/')
    print('GRADING-STATUS:', {k: v for k, v in estat.items() if k.startswith('te_')})

    with sync_playwright() as p:
        nav = p.chromium.launch()
        ctx = nav.new_context(viewport={'width': 1700, 'height': 1100})
        pag = ctx.new_page()
        pag.route('**/*', handler)
        pag.goto(BASE + '/', wait_until='domcontentloaded')
        pag.evaluate("([t]) => { localStorage.setItem('access_token', t);"
                     " localStorage.setItem('fhort.lang', 'ca') }", [TOKEN])

        def obre(url, captura):
            pag.goto(BASE + url, wait_until='networkidle')
            pag.wait_for_timeout(3500)
            pag.screenshot(path=str(OUT / captura), full_page=True)
            return pag.evaluate("() => document.body.innerText")

        # ── B4 · les quatre portes ────────────────────────────────────────────────────────
        print('\nB4 · EL STEPPER DE LES QUATRE PORTES')
        obre(f'/models/{MODEL}?tab=Mesures', 'b4_stepper.png')
        portes = pag.evaluate("""() => [...document.querySelectorAll('button')]
            .filter(b => /Editar POM|Graduaci|Mesurar prenda|Propagar/i.test(b.innerText))
            .map(b => ({ text: b.innerText.trim().split('\\n')[0],
                         color: getComputedStyle(b).color,
                         fons: getComputedStyle(b).backgroundColor,
                         check: !!b.querySelector('.ti-check') }))""")
        for b in portes:
            print(f"    {b['text']:<18} check={b['check']!s:<5} color={b['color']}")
        mira('B4/E1 · les quatre portes hi són', len(portes) >= 4, f'{len(portes)} trobades')
        # Un FET del backend a cada porta: cap dels quatre camps pot faltar.
        for camp in ('te_mesures', 'te_regles', 'te_taula', 'te_presa', 'te_propagacio'):
            mira(f'B4/E1 · `{camp}` el diu el backend', camp in estat)
        # E2 · el que el backend afirma i el que la porta pinta han de coincidir.
        esperats = {'Editar POM': estat.get('te_mesures'), 'Graduaci': estat.get('te_regles'),
                    'Mesurar prenda': estat.get('te_presa'), 'Propagar': estat.get('te_propagacio')}
        for etiqueta, fet in esperats.items():
            b = next((x for x in portes if etiqueta.lower() in x['text'].lower()), None)
            if b is None:
                mira(f'B4/E2 · porta «{etiqueta}»', False, 'no trobada')
                continue
            mira(f'B4/E2 · «{etiqueta}» pinta FET={fet}', b['check'] == bool(fet),
                 f"check={b['check']}")
        # I contra el Dashboard: la tasca Feta i la porta verda han de dir el mateix.
        parelles = [('pom', 'te_mesures'), ('size_check', 'te_presa'), ('grading', 'te_regles')]
        for codi, camp in parelles:
            tk = per_codi.get(codi)
            if not tk:
                continue
            coincideix = (tk['status'] == 'Done') == bool(estat.get(camp))
            mira(f'B4/E2 · «{codi}» Kanban({tk["status"]}) ↔ stepper({estat.get(camp)})',
                 coincideix,
                 'divergeixen: la feina i el fet no diuen el mateix (mira'
                 ' la diagnosi §B4)' if not coincideix else '')

        # ── B3 · els dos camins d'entrada ─────────────────────────────────────────────────
        print('\nB3 · EL ROUTER DE LA TASCA')
        # R2 · «Definició POM» → el carril d'entrada.
        tk_pom = per_codi.get('pom')
        if tk_pom:
            txt = obre(f'/models/{MODEL}?tab=Mesures&task_id={tk_pom["id"]}', 'b3_pom.png')
            carril = 'Gravar POM' in txt or 'Definició POM' in txt
            mira('B3/R2 · una tasca `pom` aterra al CARRIL', carril)

        # R1 · «Mesurar prenda» → la sessió de fitting, MAI el carril.
        tk_sc = per_codi.get('size_check')
        if tk_sc:
            txt = obre(f'/models/{MODEL}?tab=Mesures&task_id={tk_sc["id"]}', 'b3_size_check.png')
            # El que separa les dues pantalles, no un títol que totes dues comparteixen. La de
            # POMs porta «Gravar POM»; la de fitting porta la capçalera de la SESSIÓ, la columna
            # de VEREDICTE i la sortida «Gravar i tornar».
            #
            # ⚠️ Es compara en minúscules: els encapçalaments del sistema van en majúscules per
            # `text-transform`, i `innerText` retorna el text TAL COM ES VEU, no el del DOM.
            # Buscar-hi 'Veredicte' no troba mai el 'VEREDICTE' que hi ha a la pantalla.
            baix = txt.lower()
            es_carril = 'gravar pom' in baix
            marques = [m for m in ('sessió de fitting', 'veredicte', 'gravar i tornar')
                       if m in baix]
            mira('B3/R1 · «Mesurar prenda» NO aterra al carril de POMs', not es_carril)
            mira('B3/R1 · …i sí a la superfície de presa', len(marques) >= 2,
                 ' · '.join(marques) or 'cap marca de la pantalla de fitting')

        nav.close()

    print('\nESCRIPTURES CENSADES (cap ha arribat al servidor):',
          json.dumps(sorted(set(escriptures)), ensure_ascii=False) or 'cap')
    print(f'Captures a {OUT}')
    if falles:
        print(f'\n❌ {len(falles)} afirmacions vermelles: ' + ' · '.join(falles))
        sys.exit(1)
    print('\n✅ B3+B4 · totes les afirmacions verdes')


if __name__ == '__main__':
    main()
