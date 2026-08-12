"""ARNÈS · PRED-1 · el Repàs compta PER PRENDA (model 1320).

⚠️ **CAP ESCRIPTURA.** Tot POST/PATCH/PUT/DELETE es respon localment amb l'eco del cos i es
censa. La consulta de Mesures és lectura, però la llei d'aquest banc no depèn de la sort.

EL SUBJECTE QUE ES FIXA (i que ha d'haver-se vist VERMELL abans del canvi):

  P1 · el recompte viu DINS del contenidor de la prenda, no fora de tots
  P2 · CONTRAPÈS — cap contenidor pinta el recompte DEL MODEL quan el seu és un altre.
       Al 1320 el model en compta 2 i cap de les dues prendes en té 2 (1 i 1): el rètol
       d'avui diu «2 sessions fetes» a una pantalla on cap prenda n'ensenya dues. Aquest és
       el vermell, i és dada VIVA, no un cas inventat.
  P3 · el número quadra amb el payload: columnes d'esdeveniment amb `valor_real` a les files
       d'aquesta prenda (l'ENTRADA DE POMs no hi compta mai)
  P4 · RES NO DESAPAREIX — la UNIÓ de les columnes que compten les prendes és exactament el
       joc de columnes d'esdeveniment del model. Partir el número no pot perdre cap fitting.

⚠️ EL CONTROL D'UNA SOLA PRENDA NO ES POT MESURAR AQUÍ, i és la mateixa limitació que B2b va
deixar escrita: al corpus viu de `fhort` els models amb mesures (1320, 1322) tenen tots dos
DUES peces. El control «amb una prenda el número és el de sempre» viu al banc pur
(`utils/repasPerPeca.test.js`), que és on es pot construir el cas.

    FTT_QA_TOKEN=... /tmp/qa-venv/bin/python ops/qa/qa_s2_repas_per_prenda.py

`FTT_QA_DIST` apunta al bundle que es mesura (per veure el vermell: el `dist` desplegat).
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
VIU = os.environ.get('FTT_QA_API') or 'http://127.0.0.1:8001'
TOKEN = os.environ.get('FTT_QA_TOKEN', '')
MODEL = int(os.environ.get('FTT_QA_MODEL', '1320'))

falles = []


def mira(nom, ok, detall=''):
    print(f'  {"✅" if ok else "❌"} {nom}' + (f' — {detall}' if detall else ''))
    if not ok:
        falles.append(nom)


def esperat_per_prenda(payload):
    """El recompte que la pantalla HAURIA de dir, calculat del payload cru.

    Mateixa llei que `utils/repasPerPeca.js`, re-implementada a posta: si l'arnès importés la
    funció del front, mesuraria que el codi és igual a ell mateix.
    """
    fora = {}
    for fila in payload.get('rows', []):
        g = fila.get('garment') or ''
        for sessio in payload.get('sessions', []):
            if sessio.get('origen') == 'ENTRADA':
                continue
            cel = (fila.get('valors') or {}).get(str(sessio['id']))
            if cel and cel.get('valor_real') is not None:
                fora.setdefault(g, set()).add(str(sessio['id']))
    return {g: len(v) for g, v in fora.items()}


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

    payload = api(f'/api/v1/fitting/model/{MODEL}/repas/')
    esperat = esperat_per_prenda(payload)
    columnes = [c['origen'] for c in payload['sessions']]
    total_model = len([c for c in payload['sessions'] if c['origen'] != 'ENTRADA'])
    print(f'\nPAYLOAD · talla={payload["talla"]} · columnes={columnes}')
    print(f'  recompte DEL MODEL (el d\'abans): {total_model}')
    print(f'  recompte PER PRENDA (l\'esperat): {esperat}')
    peces = api(f'/api/v1/models/{MODEL}/peces/')['peces']
    print('  bases de talla per prenda:',
          {p['codi'] or '(mare)': p['base_size_label']['etiqueta'] for p in peces})

    with sync_playwright() as p:
        nav = p.chromium.launch()
        ctx = nav.new_context(viewport={'width': 1700, 'height': 1100})
        pag = ctx.new_page()
        pag.route('**/*', handler)
        pag.goto(BASE + '/', wait_until='domcontentloaded')
        pag.evaluate("([t]) => { localStorage.setItem('access_token', t);"
                     " localStorage.setItem('fhort.lang', 'ca') }", [TOKEN])
        pag.goto(BASE + f'/models/{MODEL}?tab=Mesures', wait_until='networkidle')
        pag.wait_for_timeout(3500)
        # La subvista «Repàs de fittings» del commutador de consulta.
        pag.evaluate("""() => {
            const b = [...document.querySelectorAll('button')]
              .find(x => /Rep[àa]s de fittings/i.test(x.textContent))
            if (b) b.click()
        }""")
        pag.wait_for_timeout(3000)
        pag.screenshot(path=str(OUT / 's2pred1_repas.png'), full_page=True)

        # El recompte, llegit DINS de cada contenidor (`data-peca` és el marcador estable).
        dins = pag.evaluate(r"""() => {
            const out = {}
            for (const c of document.querySelectorAll('[data-peca]')) {
              // Singular I plural: el rètol és `count_one`/`count_other` («1 sessió feta»).
              // Una regex que només miri el plural torna `null` a tota prenda amb un sol
              // fitting, que és justament el cas normal des que el número és per prenda.
              const m = c.innerText.match(/(\d+)\s+sessi(?:ó feta|ons fetes)/)
              out[c.getAttribute('data-peca')] = m ? Number(m[1]) : null
            }
            return out
        }""")
        # …i el que encara viu FORA de tots els contenidors.
        fora = pag.evaluate(r"""() => {
            const dins = [...document.querySelectorAll('[data-peca]')]
            const tots = [...document.querySelectorAll('span, p, h3, div')]
              .filter(e => /\d+\s+sessi(ó feta|ons fetes)/.test(e.textContent)
                           && e.children.length === 0)
            const orfes = tots.filter(e => !dins.some(c => c.contains(e)))
            return orfes.map(e => e.textContent.trim())
        }""")
        print(f'\n  recompte DINS de cada contenidor: {dins}')
        print(f'  recompte FORA de tot contenidor:  {fora or "cap"}')

        mira('P1 · el recompte viu DINS del contenidor', bool(dins) and all(
            v is not None for v in dins.values()), str(dins))
        mira('P1b · …i ja no en queda cap FORA', not fora, str(fora))
        # P2 · el contrapès que trenca la coincidència: NO es mira que els números siguin
        # diferents entre ells (al 1320 tots dos són 1), sinó que cap contenidor pinti el
        # número DEL MODEL quan el seu és un altre. Això és el que un recompte model-wide no
        # pot complir mai, i és el vermell que s'ha vist.
        impostors = {codi: n for codi, n in dins.items()
                     if esperat.get(codi, 0) != total_model and n == total_model}
        mira('P2 · CONTRAPÈS · cap contenidor pinta el recompte DEL MODEL',
             not impostors,
             f'model={total_model} · pantalla={dins} · esperat={esperat}')
        for codi, n in dins.items():
            mira(f'P3 · el número de «{codi or "mare"}» quadra amb el payload',
                 n == esperat.get(codi, 0), f'pantalla={n} · payload={esperat.get(codi, 0)}')
        # P4 · partir el número no pot perdre cap fitting: la unió del que compten les prendes
        # ha de ser el joc sencer de columnes d'esdeveniment del model.
        union = set()
        for fila in payload.get('rows', []):
            for sessio in payload.get('sessions', []):
                if sessio.get('origen') == 'ENTRADA':
                    continue
                cel = (fila.get('valors') or {}).get(str(sessio['id']))
                if cel and cel.get('valor_real') is not None:
                    union.add(str(sessio['id']))
        totes = {str(c['id']) for c in payload['sessions'] if c['origen'] != 'ENTRADA'}
        mira('P4 · RES NO DESAPAREIX · la unió de les prendes és el joc del model',
             union == totes, f'unió={sorted(union)} · model={sorted(totes)}')
        print('  ⚠️  el control d\'UNA prenda no és mesurable en aquest corpus '
              '(1320 i 1322 tenen dues peces): viu al banc `utils/repasPerPeca.test.js`')

        print('\nCENS D ESCRIPTURES:', escriptures or 'cap')
        nav.close()

    print('\n' + ('❌ ' + ' · '.join(falles) if falles else '✅ PRED-1 · totes verdes'))
    sys.exit(1 if falles else 0)


if __name__ == '__main__':
    main()
