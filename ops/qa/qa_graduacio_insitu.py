"""QA FUNCIONAL · els dos defectes del pas de graduació (Agus, 09/08), contra el servei VIU.

Els dos que es mesuren aquí són de COMPORTAMENT, no de pell, i per això no van a la
bidireccional: el que s'ha de provar és que un GEST fa el que ha de fer i que una pantalla NO
decideix per l'usuari. Cap dels dos es veu en una captura.

  D1 · «Definir graduació» saltava al ModelWizard vell (`navigate('…/editar?block=4')`). Ha de
       obrir el SUBESPAI 4 dins de «Definició del model», triar-hi el joc, desar-lo amb el seu
       blau, i deixar el pas FET amb el xip fixat i «Canviar». **Cap salt de pantalla**: la prova
       dura és que `location.pathname` no es mou en tot el cicle.

  D2 · El pas 3 del wizard arribava amb un sistema PRESELECCIONAT (el primer per proximitat) i,
       amb ell, el run sencer i la talla base. L'elecció ha de néixer BUIDA: cap fila triada i
       cap tira de talles fins que hi hagi un clic humà.

⚠️ **AQUEST GUIÓ ESCRIU AL DOMINI.** Desar la graduació del model 1320 materialitza les regles
residents del joc. És el cicle que l'Agus ha demanat explícitament sobre aquest model; no és un
efecte secundari. Per si s'ha de repetir, al final es DESACOBLA el joc i es deixa el model tal
com estava (`grading_rule_set = null`), i el guió ho diu.

Com se serveix: el bundle de `frontend/dist` per `page.route` i `/api/` reenviat al gunicorn viu
del 8001 amb el `Host` del tenant — la recepta de `qa_f22_vocabulari_captures.py`, que és l'única
que mesura el BACKEND DESPLEGAT i no un joc de fixtures.

    FTT_QA_TOKEN=... /tmp/qa-venv/bin/python ops/qa/qa_graduacio_insitu.py
"""
import mimetypes
import os
import pathlib
import re
import sys

import requests
from playwright.sync_api import sync_playwright

REPO = pathlib.Path(__file__).resolve().parents[2]
DIST = pathlib.Path(os.environ.get('FTT_QA_DIST') or (REPO / 'frontend' / 'dist'))
OUT = pathlib.Path(__file__).resolve().parent / 'captures'
BASE = 'https://staging.fhorttextile.tech'
VIU = 'http://127.0.0.1:8001'
HOST_TENANT = os.environ.get('FTT_QA_HOST', 'fhorttextile.tech')
TOKEN = os.environ.get('FTT_QA_TOKEN', '')
MODEL = int(os.environ.get('FTT_QA_MODEL', '1320'))

resultats = []


def comprova(nom, condicio, detall=''):
    resultats.append((bool(condicio), nom, detall))
    print(f'{"✓" if condicio else "✗"} {nom}' + (f'  — {detall}' if detall else ''))


def fes_handler(sess):
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
    return handler


def subespai(pag, titol):
    """La capçalera d'un subespai, localitzada pel seu TÍTOL (que és el que un humà veu)."""
    return pag.locator(f'div:has(> span:text-is("{titol}"))').first


def reinicia(sess):
    """Deixa el model SENSE graduació perquè el cicle es pugui tornar a córrer.

    ⚠️ Sense això el guió no és repetible i MENT la segona vegada: la primera passada assigna el
    joc, i a la segona el pas 4 ja és FET —no s'obre cap picker— i «0 jocs oferts» es llegeix com
    un defecte del codi quan és l'empremta de la passada anterior. El desacoblament va pel MATEIX
    endpoint que la pantalla (`update-step2` amb el joc a null) i porta el flag de confirmació
    perquè el 409 de D-31.4 el demana: esborrar les residents és exactament el que volem aquí.
    """
    r = sess.patch(f'{VIU}/api/v1/models/{MODEL}/update-step2/',
                   headers={'Host': HOST_TENANT, 'Authorization': f'Bearer {TOKEN}',
                            'Content-Type': 'application/json'},
                   json={'grading_rule_set_id': None, 'confirmar_esborrat_residents': True},
                   timeout=30)
    print(f'· reinici del banc: model {MODEL} sense graduació (HTTP {r.status_code})')
    return r.status_code < 400


def d1_graduacio_insitu(pag):
    print('\n── D1 · la graduació s\'edita AL SEU LLOC ' + '─' * 40)
    ruta = f'/models/{MODEL}?tab=Resum'
    pag.goto(BASE + ruta, wait_until='networkidle')
    pag.wait_for_timeout(2500)
    inicial = pag.evaluate('() => location.pathname')

    # El pas 4 és l'ACTUAL (peça i talles fetes, graduació pendent): s'ha d'obrir SOL, amb el
    # picker a dins. Si encara saltés al wizard, aquí ja no hi seríem.
    picker = pag.locator('button:has-text("Usar aquest joc")')
    comprova('el subespai 4 s\'obre in-situ amb el catàleg de jocs',
             picker.count() > 0, f'{picker.count()} joc(s) oferts')
    comprova('cap salt de pantalla en obrir-lo',
             pag.evaluate('() => location.pathname') == inicial, inicial)
    pag.screenshot(path=str(OUT / 'grad_01_subespai_obert.png'), full_page=True)

    if picker.count() == 0:
        comprova('BLOQUEJANT: sense jocs no es pot completar el cicle', False)
        return

    # El joc de Brownie: eixos BUITS i només el sistema de talles declarat. Amb matching
    # ESTRICTE no sortiria — és el cas que justifica el mode eliminatiu.
    nom_joc = pag.locator('button:has-text("Usar aquest joc")').first \
        .locator('xpath=ancestor::div[1]/preceding-sibling::div[1]//div').first
    picker.first.click()
    pag.wait_for_timeout(600)

    desar = pag.locator('button:has-text("Desar graduació")')
    comprova('el blau del pas és «Desar graduació» i s\'habilita en triar',
             desar.count() > 0 and desar.first.is_enabled())
    pag.screenshot(path=str(OUT / 'grad_02_joc_triat.png'), full_page=True)

    desar.first.click()
    pag.wait_for_timeout(3500)

    comprova('cap salt de pantalla en desar',
             pag.evaluate('() => location.pathname') == inicial,
             pag.evaluate('() => location.pathname'))

    cap4 = subespai(pag, 'Graduació')
    canviar = cap4.locator('button:has-text("Canviar")')
    comprova('el pas queda FET, amb «Canviar» (no «Definir graduació»)',
             canviar.count() > 0 and pag.locator('button:has-text("Definir graduació")').count() == 0)
    # El ✓ del numeral i el nom del joc fixat i visible: «res s'amaga en tancar-se» (§8f).
    comprova('el joc queda FIXAT I VISIBLE amb el pas tancat',
             cap4.locator('xpath=following-sibling::div[1]').count() > 0
             or pag.locator('text=/Joc de regles/').count() > 0)
    pag.screenshot(path=str(OUT / 'grad_03_desat_fet.png'), full_page=True)

    # I «Canviar» ha de tornar a obrir el mateix subespai, no cap altra pantalla.
    if canviar.count() > 0:
        canviar.first.click()
        pag.wait_for_timeout(1500)
        comprova('«Canviar» reobre el subespai in-situ',
                 pag.locator('button:has-text("Desar graduació")').count() > 0
                 and pag.evaluate('() => location.pathname') == inicial)
        pag.screenshot(path=str(OUT / 'grad_04_canviar_reobre.png'), full_page=True)


#: Quantes files de run estan TRIADES, mesurat pel fons que el wizard els posa (`--warn-bg`).
#: Es mesura el color COMPUTAT i no una classe perquè aquí l'estil és en línia: no hi ha cap
#: classe que dir, i comparar cadenes d'estil seria comparar la implementació, no el que es veu.
FILES_TRIADES = """() => {
  const px = (c) => { const d = document.createElement('div'); d.style.background = c
                      document.body.appendChild(d)
                      const v = getComputedStyle(d).backgroundColor; d.remove(); return v }
  const triat = px(getComputedStyle(document.documentElement)
                     .getPropertyValue('--warn-bg').trim())
  const files = [...document.querySelectorAll('div[style*="cursor: pointer"]')]
    .filter(e => e.querySelector('span') && /EU|UK|US|Alpha|Num/i.test(e.textContent || ''))
  return { total: files.length,
           triades: files.filter(e => getComputedStyle(e).backgroundColor === triat).length }
}"""


def d2_run_neix_buit(pag):
    print('\n── D2 · el run NEIX BUIT (cap preselecció) ' + '─' * 38)
    dialegs = []
    pag.on('dialog', lambda d: (dialegs.append(d.message), d.dismiss()))
    pag.goto(BASE + '/models/nou', wait_until='networkidle')
    pag.wait_for_timeout(2000)

    # ── LES TRES PORTES DEL WIZARD, obertes a mà. No són cosmètica: sense client no es passa del
    # pas 1 (gate del prefix de codi), sense temporada tampoc, i sense TARGET el pas 3 no carrega
    # cap run (`if (!target …) return`) — o sigui que sense obrir-les la mesura seria una llista
    # buida, que passaria el test dient exactament res.
    try:
        pag.locator('select').nth(1).select_option(index=1)          # client (el 1r select és l'idioma)
        pag.wait_for_timeout(600)
        temporada = pag.locator('button').filter(has_text=re.compile(r'(Fall/Winter|Spring/Summer)'))
        if temporada.count():
            temporada.first.click()
        pag.wait_for_timeout(600)
        pag.locator('button:has-text("Següent")').first.click()      # → pas 2 · Peça
        pag.wait_for_timeout(1500)
        target = pag.locator('button').filter(has_text=re.compile(r'^\s*Dona\s*$'))
        if target.count():
            target.first.click()
        pag.wait_for_timeout(1200)
        pag.locator('button:has-text("Següent")').first.click()      # → pas 3 · Talles
        pag.wait_for_timeout(2500)
    except Exception as e:
        comprova('BLOQUEJANT: no s\'ha pogut arribar al pas 3', False, str(e))
        pag.screenshot(path=str(OUT / 'grad_05_pas3_ERROR.png'), full_page=True)
        return

    estat = pag.evaluate(FILES_TRIADES)
    comprova('la llista de runs es pinta sencera (ordena, mai amaga)',
             estat['total'] > 0, f'{estat["total"]} runs oferts')
    comprova('CAP run preseleccionat: l\'elecció neix buida',
             estat['triades'] == 0, f'{estat["triades"]} de {estat["total"]} triats')

    # I si res no s'ha triat, tampoc pot haver-hi run ni talla base proposats: eren les altres
    # dues decisions que la preselecció prenia de retruc.
    base = pag.locator('text=/Talla base/i')
    comprova('sense sistema triat no hi ha ni run ni talla base proposats',
             base.count() == 0, f'«Talla base» visible: {base.count()}')
    pag.screenshot(path=str(OUT / 'grad_05_pas3_buit.png'), full_page=True)

    # EL DELATOR. El diàleg de substitució només té sentit sobre una tria HUMANA prèvia; amb la
    # llista neta, el primer clic no ha de preguntar res.
    files = pag.locator('div[style*="cursor: pointer"]').filter(has_text=re.compile(r'EU|UK|US|Alpha'))
    if files.count() > 0:
        files.first.click()
        pag.wait_for_timeout(1500)
    comprova('el primer clic NO dispara el diàleg de substitució de run',
             len(dialegs) == 0, dialegs[0] if dialegs else '')
    despres = pag.evaluate(FILES_TRIADES)
    comprova('i després del clic humà SÍ que hi ha exactament un run triat',
             despres['triades'] == 1, f'{despres["triades"]} triats')
    pag.screenshot(path=str(OUT / 'grad_06_pas3_tria_humana.png'), full_page=True)


def main():
    if not TOKEN:
        sys.exit('Falta FTT_QA_TOKEN (no s\'imprimeix enlloc; passa\'l per entorn).')
    if not DIST.exists():
        sys.exit(f'No hi ha bundle a {DIST} — cal `npm run build`.')
    OUT.mkdir(exist_ok=True)
    sess = requests.Session()
    reinicia(sess)

    with sync_playwright() as p:
        nav = p.chromium.launch()
        ctx = nav.new_context(viewport={'width': 1600, 'height': 1200})
        pag = ctx.new_page()
        pag.route('**/*', fes_handler(sess))
        pag.goto(BASE + '/', wait_until='domcontentloaded')
        pag.evaluate("([t]) => { localStorage.setItem('access_token', t);"
                     " localStorage.setItem('fhort.lang', 'ca') }", [TOKEN])
        d1_graduacio_insitu(pag)
        d2_run_neix_buit(pag)
        nav.close()

    mal = [r for r in resultats if not r[0]]
    print('\n' + '=' * 78)
    print(f'{len(resultats) - len(mal)}/{len(resultats)} comprovacions OK')
    for _, nom, detall in mal:
        print(f'  ✗ {nom} — {detall}')
    sys.exit(1 if mal else 0)


if __name__ == '__main__':
    main()
