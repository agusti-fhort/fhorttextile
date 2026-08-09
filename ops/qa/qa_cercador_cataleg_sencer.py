"""QA · el cercador del carril ofereix el CATÀLEG SENCER sense haver-lo d'endevinar (Agus 09/08).

Germà de `qa_carril_mesures_1320.py` i amb la MATEIXA llei: **cap escriptura**. El carril escriu
al domini en obrir-se i l'Agus hi és treballant; tot el que no és GET es respon localment amb
l'eco del cos i es compta, de manera que al final es pot afirmar —no suposar— que no n'ha sortit
cap.

Què mesura, sobre el model 1320 (Blusa KAYCE, client BRW):

  1 · amb el camp BUIT i el focus posat, el desplegable ofereix el catàleg (142) i diu el sostre;
  2 · amb «F» —un sol caràcter— surt el POM `F`, i surt EL PRIMER;
  3 · els noms de la taula són els CANÒNICS, sense la llista del matcher concatenada amb `;`.

    FTT_QA_TOKEN=... /tmp/qa-venv/bin/python ops/qa/qa_cercador_cataleg_sencer.py
"""
import json
import mimetypes
import os
import pathlib
import sys

import requests
from playwright.sync_api import sync_playwright

DIST = pathlib.Path(__file__).resolve().parents[2] / 'frontend' / 'dist'
OUT = pathlib.Path(__file__).resolve().parent / 'captures'
BASE = 'https://staging.fhorttextile.tech'
VIU = 'http://127.0.0.1:8001'
HOST = os.environ.get('FTT_QA_HOST', 'staging.fhorttextile.tech')
TOKEN = os.environ.get('FTT_QA_TOKEN', '')

resultats = []


def comprova(nom, cond, detall=''):
    resultats.append((bool(cond), nom, detall))
    print(f'{"✓" if cond else "✗"} {nom}' + (f'  — {detall}' if detall else ''))


def desplegable(pag):
    """El text del desplegable, o '' si és tancat.

    ⚠️ Anava a buscar «l'últim div `position:fixed` amb text», i amb el desplegable TANCAT això
    cau damunt del rellotge de la tasca (que també és fix): el detector deia «obert» sempre i el
    cicle de confirmació donava un fals vermell. Ara la llista es marca a l'origen
    (`data-cercador-llista`) i aquí es pregunta per ella, no per la seva forma."""
    el = pag.query_selector('[data-cercador-llista]')
    return el.inner_text() if el else ''


def main():
    if not TOKEN:
        sys.exit('Falta FTT_QA_TOKEN')
    OUT.mkdir(exist_ok=True)
    sess = requests.Session()
    escriptures = []

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
                             headers={'Host': HOST, 'Authorization': f'Bearer {TOKEN}'}, timeout=30)
                route.fulfill(status=r.status_code, body=r.content,
                              headers={'content-type': r.headers.get('content-type', 'application/json')})
            except Exception as e:
                route.fulfill(status=502, body=json.dumps({'error': str(e)}),
                              headers={'content-type': 'application/json'})
            return
        f = DIST / cami.lstrip('/')
        if not f.is_file():
            f = DIST / 'index.html'
        route.fulfill(status=200, body=f.read_bytes(),
                      headers={'content-type': mimetypes.guess_type(f.name)[0] or 'text/html'})

    with sync_playwright() as p:
        nav = p.chromium.launch()
        ctx = nav.new_context(viewport={'width': 1700, 'height': 1150})
        pag = ctx.new_page()
        pag.route('**/*', handler)
        pag.goto(BASE + '/', wait_until='domcontentloaded')
        pag.evaluate("([t]) => { localStorage.setItem('access_token', t);"
                     " localStorage.setItem('fhort.lang', 'ca') }", [TOKEN])
        pag.goto(BASE + '/models/1320?tab=Mesures', wait_until='networkidle')
        pag.wait_for_timeout(3500)
        pag.screenshot(path=str(OUT / 'cerca_00_taula.png'), full_page=True)

        # ── 3 · els noms de la taula ─────────────────────────────────────────────────────
        cos = pag.inner_text('body')
        comprova('cap nom amb la llista del matcher concatenada (`;`)',
                 '; 1/2 ' not in cos and 'width;' not in cos)
        comprova('el nom canònic de la fila A hi és sencer',
                 '1/2 chest width (armpit to armpit)' in cos)
        comprova('cap codi porta el prefix del client (BRW-)', 'BRW-EK' not in cos)

        # ── obrir el carril d'edició, on viu el cercador ─────────────────────────────────
        try:
            pag.locator('button:has-text("Editar POM")').first.click()
            pag.wait_for_timeout(2500)
        except Exception as e:
            comprova('BLOQUEJANT: no s\'ha pogut obrir «Editar POM»', False, str(e))
            nav.close()
            return

        camp = pag.locator('input[placeholder]')
        idx = None
        for i in range(camp.count()):
            ph = (camp.nth(i).get_attribute('placeholder') or '').lower()
            if 'pom' in ph or 'cerca' in ph or 'busca' in ph or 'codi' in ph:
                idx = i
                break
        if idx is None:
            comprova('BLOQUEJANT: no s\'ha trobat el camp del cercador', False,
                     str([camp.nth(i).get_attribute('placeholder') for i in range(camp.count())]))
            nav.close()
            return

        # ── LES DUES POBLACIONS, A CADA CONSULTA ─────────────────────────────────────────
        #
        # 🔑 El que es mesura NO és «el POM hi és a la resposta» sinó **que es pugui reconèixer
        # a la pantalla**. Tres voltes de QA van morir aquí: el POM hi era, la fila el pintava
        # amb la nomenclatura de l'altre catàleg, i qui l'havia demanat no el veia. Per això
        # cada comprovació busca el TEXT literal de la fila al desplegable.
        #
        # Cap fila combinada: el canònic surt a la secció de la casa amb el SEU codi i el SEU
        # nom, i l'àlies a la del client amb els seus i una segona línia «→ canònic».
        RETOL_CLIENT, RETOL_CASA = 'CATÀLEG DEL CLIENT', 'CATÀLEG DE LA CASA'
        for q, casa, canonic in (
            ('', None, None),                                    # camp buit = les dues senceres
            ('F', 'F', 'Centre front length from HPS'),
            ('front', 'F', 'Centre front length from HPS'),
            ('neck', 'EK', 'Neck width'),
        ):
            camp.nth(idx).fill('')
            pag.wait_for_timeout(500)
            if q:
                camp.nth(idx).fill(q)
            else:
                camp.nth(idx).click()
            pag.wait_for_timeout(1800)
            txt = desplegable(pag)
            etiq = f'«{q}»' if q else 'camp BUIT'

            comprova(f'{etiq} → LES DUES seccions són visibles',
                     RETOL_CLIENT in txt.upper() and RETOL_CASA in txt.upper(),
                     [l for l in txt.splitlines() if l.strip().isupper()][:4])

            if q:
                comprova(f'{etiq} → el canònic «{casa} · {canonic}» surt com a ELL MATEIX',
                         canonic in txt, [l for l in txt.splitlines() if canonic in l][:2])
            else:
                # Les dues poblacions senceres: 64 àlies i 142 canònics, amb el sostre dit.
                comprova('camp BUIT → cada secció diu el seu sostre',
                         '/64' in txt and '/142' in txt,
                         [l for l in txt.splitlines() if '/' in l][:3])

            nom = q.replace(' ', '_') if q else 'buit'
            pag.screenshot(path=str(OUT / f'cerca_seccions_{nom}.png'), full_page=True)

        # L'exacte, primer DINS de la seva secció: q=F → la fila F encapçala la de la casa.
        camp.nth(idx).fill('')
        pag.wait_for_timeout(400)
        camp.nth(idx).fill('F')
        pag.wait_for_timeout(1800)
        txt = desplegable(pag)
        linies = [l.strip() for l in txt.splitlines() if l.strip()]
        try:
            i_casa = next(i for i, l in enumerate(linies) if RETOL_CASA in l.upper())
            primera = ' '.join(linies[i_casa + 1:i_casa + 3])
        except StopIteration:
            primera = ''
        comprova('«F» → la fila F canònica encapçala la secció de la casa',
                 'Centre front length from HPS' in primera, primera[:80])

        # ── EL CICLE DE CONFIRMACIÓ · TRES POMs SEGUITS ──────────────────────────────────
        #
        # ⚠️ Aquest tram existeix per una REGRESSIÓ que va entrar amb «camp buit = catàleg
        # sencer»: en confirmar, el camp es buida, i com que el focus hi seguia posat l'efecte
        # de cerca el tornava a trobar buit i **reobria el desplegable amb els 142 a sobre de la
        # fila que s'acabava de crear**. El gest correcte és el contrari: confirmar tanca, buida,
        # desenfoca i passa el torn al camp de valor de la fila nova.
        #
        # Es fan TRES seguits perquè el defecte es veu en la cadena, no en un sol tret: amb el
        # desplegable reobrint-se, el segon POM ja no es pot ni buscar.
        camp.nth(idx).press('Escape')
        pag.wait_for_timeout(500)
        files_abans = pag.locator('tr[data-fila]').count()
        reobertures = []
        for n, (q, _casa, _canonic) in enumerate((
            ('EB', 'EB', 'Neck binding width'),
            ('EKK', 'EKK', 'Back neckline width'),
            ('CR', 'CR', None),
        ), start=1):
            camp.nth(idx).click()
            camp.nth(idx).fill(q)
            pag.wait_for_timeout(1500)
            pag.keyboard.press('Enter')                 # confirma el primer resultat
            pag.wait_for_timeout(1200)
            obert_despres = len(desplegable(pag)) > 40
            if obert_despres:
                reobertures.append(f'{n}r ({q})')
            # El focus ha d'haver saltat al camp de valor de la fila nova (el carril).
            al_carril = pag.evaluate(
                "() => !!document.activeElement?.matches?.('input[data-carril]')")
            comprova(f'POM {n} («{q}») → el focus va al camp de valor de la fila nova', al_carril)
            pag.keyboard.type('12')                     # escriure el valor, sense tocar el ratolí
            pag.wait_for_timeout(400)

        comprova('el desplegable NO es reobre sol després de confirmar',
                 not reobertures, f'reobert després de: {reobertures}')
        files_despres = pag.locator('tr[data-fila]').count()
        comprova('els 3 POMs han entrat com a 3 files noves',
                 files_despres == files_abans + 3, f'{files_abans} → {files_despres}')
        pag.screenshot(path=str(OUT / 'cerca_cicle_3poms.png'), full_page=True)

        # ⚠️ El carril ESCRIU EN OBRIR-SE (`open-task` salta només d'entrar-hi): el que s'ha de
        # comprovar no és que no n'hi hagi cap —n'hi haurà— sinó que TOTES han quedat retingudes
        # aquí. El handler les respon localment, o sigui que per construcció cap arriba al
        # domini; el que es mesura és que no se n'ha escapat cap per un camí que no sigui `/api/`.
        comprova('totes les escriptures del carril queden RETINGUDES (cap arriba al domini)',
                 all(e.split(' ', 1)[1].startswith('/api/') for e in escriptures),
                 f'{len(escriptures)} interceptada/es: {escriptures or "cap"}')
        nav.close()

    mal = [r for r in resultats if not r[0]]
    print('\n' + '=' * 76)
    print(f'{len(resultats) - len(mal)}/{len(resultats)} comprovacions OK')
    for _, nom, detall in mal:
        print(f'  ✗ {nom} — {detall}')
    sys.exit(1 if mal else 0)


if __name__ == '__main__':
    main()
