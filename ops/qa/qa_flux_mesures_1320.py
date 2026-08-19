"""QA · els tres defectes del carril de Mesures (Agus 09/08, 4a tanda).

  D1 · «Mesurar prenda» refusava un model amb run, talla base, mesures i graduació. La taula de
       talles (GradingVersion + GradedSpec) no la generava ningú del FLUX: l'únic que cridava
       `generar-grading` era el botó **Propagar**. Ara la genera `gravar-pom`, que és el moment
       en què existeixen les tres coses alhora (regles, run i mesures base).
  D2 · Stepper §6 a les quatre portes: FET amb `--ok-bg` + ✓, disponible normal, bloquejat tènue
       i AMB EL MOTIU escrit.
  D3 · L'ordre de les files és dada de l'usuari: `gravar-pom` no el desava (tot a `ordre=0`) i el
       lector del carril el llençava amb un sort alfabètic per codi.

⚠️ Aquest guió ESCRIU (crida `gravar-pom` de debò): sense escriure no hi ha res a mesurar, perquè
el defecte ÉS del camí d'escriptura. Va contra el 1320, que és el banc que l'Agus ha demanat.

    FTT_QA_TOKEN=... /tmp/qa-venv/bin/python ops/qa/qa_flux_mesures_1320.py
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
HOST = os.environ.get('FTT_QA_HOST', 'fhorttextile.tech')
TOKEN = os.environ.get('FTT_QA_TOKEN', '')
MODEL = int(os.environ.get('FTT_QA_MODEL', '1320'))

resultats = []


def comprova(nom, cond, detall=''):
    resultats.append((bool(cond), nom, detall))
    print(f'{"✓" if cond else "✗"} {nom}' + (f'  — {detall}' if detall else ''))


def api(sess, metode, cami, **kw):
    return sess.request(metode, VIU + cami,
                        headers={'Host': HOST, 'Authorization': f'Bearer {TOKEN}',
                                 'Content-Type': 'application/json'}, timeout=60, **kw)


def d1_d3_backend(sess):
    """Els dos defectes de FLUX es mesuren a l'API: són del camí d'escriptura, no de la pell."""
    print('\n── D1 · la taula de talles la genera el FLUX ' + '─' * 34)
    taula = api(sess, 'GET', f'/api/v1/models/{MODEL}/grading-status/').json()
    comprova('el model té regles i run (les precondicions de graduar)', taula.get('te_regles'))

    # El carril envia les files EN ORDRE. Aquí es reenvien INVERTIDES a posta: si l'ordre es desa,
    # la relectura ha de tornar-les invertides; si es llença, tornaran alfabètiques com sempre.
    files = api(sess, 'GET', f'/api/v1/models/{MODEL}/base-measurements/').json()
    rows = files.get('rows') or files.get('results') or files
    if not isinstance(rows, list) or not rows:
        comprova('BLOQUEJANT: no s\'ha pogut llegir la taula del carril', False, str(files)[:200])
        return None
    ordre_original = [r.get('pom_code') or r.get('codi_client') for r in rows]

    invertit = list(reversed(rows))
    payload = {'measurements': [{
        'pom_id': r.get('pom_id') or r.get('pom'),
        'base_value_cm': r.get('base_value_cm'),
        'capa': r.get('capa') or 'exterior',
        'instancia': r.get('instancia') or '',
        'nom_fitxa': r.get('nom_fitxa') or '',
    } for r in invertit]}
    res = api(sess, 'POST', f'/api/v1/models/{MODEL}/gravar-pom/', data=json.dumps(payload))
    comprova('`gravar-pom` respon 200', res.status_code == 200, res.text[:150])
    cos = res.json() if res.status_code == 200 else {}
    tt = cos.get('taula_talles') or {}
    comprova('…i GENERA la taula de talles en el mateix acte',
             isinstance(tt.get('specs'), int) and tt['specs'] > 0, json.dumps(tt))

    estat = api(sess, 'GET', f'/api/v1/models/{MODEL}/grading-status/').json()
    comprova('«Mesurar prenda» ja no està bloquejat (té taula)', estat.get('te_taula'),
             f"te_taula={estat.get('te_taula')} · te_mesures={estat.get('te_mesures')}")

    print('\n── D3 · l\'ordre manual es DESA i es RESPECTA ' + '─' * 34)
    rellegit = api(sess, 'GET', f'/api/v1/models/{MODEL}/base-measurements/').json()
    rows2 = rellegit.get('rows') or rellegit.get('results') or rellegit
    ordre_nou = [r.get('pom_code') or r.get('codi_client') for r in rows2]
    comprova('el carril torna les files en l\'ordre DESAT, no alfabètic',
             ordre_nou == list(reversed(ordre_original)),
             f'{ordre_nou[:5]} … (esperat {list(reversed(ordre_original))[:5]})')
    comprova('i l\'ordre NO és el codi alfabètic',
             ordre_nou != sorted(x for x in ordre_nou if x), sorted(x for x in ordre_nou if x)[:5])
    # Es deixa el banc com estava: es torna a desar en l'ordre original.
    tornada = {'measurements': [{
        'pom_id': r.get('pom_id') or r.get('pom'),
        'base_value_cm': r.get('base_value_cm'),
        'capa': r.get('capa') or 'exterior',
        'instancia': r.get('instancia') or '',
        'nom_fitxa': r.get('nom_fitxa') or '',
    } for r in rows]}
    api(sess, 'POST', f'/api/v1/models/{MODEL}/gravar-pom/', data=json.dumps(tornada))
    print('· banc restaurat a l\'ordre original')
    return True


def d2_stepper(sess):
    print('\n── D2 · el stepper de les quatre portes ' + '─' * 38)

    def handler(route, request):
        url = request.url
        cami = url.split(BASE, 1)[-1].split('?')[0] if url.startswith(BASE) else url
        if cami.startswith('/api/'):
            if request.method != 'GET':
                route.fulfill(status=200, body=request.post_data or '{}',
                              headers={'content-type': 'application/json'})
                return
            r = api(sess, 'GET', url.split(BASE, 1)[-1])
            route.fulfill(status=r.status_code, body=r.content,
                          headers={'content-type': r.headers.get('content-type', 'application/json')})
            return
        f = DIST / cami.lstrip('/')
        if not f.is_file():
            f = DIST / 'index.html'
        route.fulfill(status=200, body=f.read_bytes(),
                      headers={'content-type': mimetypes.guess_type(f.name)[0] or 'text/html'})

    with sync_playwright() as p:
        nav = p.chromium.launch()
        pag = nav.new_context(viewport={'width': 1700, 'height': 1150}).new_page()
        pag.route('**/*', handler)
        pag.goto(BASE + '/', wait_until='domcontentloaded')
        pag.evaluate("([t]) => { localStorage.setItem('access_token', t);"
                     " localStorage.setItem('fhort.lang', 'ca') }", [TOKEN])
        pag.goto(BASE + f'/models/{MODEL}?tab=Mesures', wait_until='networkidle')
        pag.wait_for_timeout(4000)

        # El VERD del pas fet es mesura pel color COMPUTAT, no per una classe: l'estil és en línia
        # i comparar-ne la cadena seria comparar la implementació, no el que es veu.
        estat = pag.evaluate("""() => {
          const px = (c) => { const d=document.createElement('div'); d.style.background=c
                              document.body.appendChild(d)
                              const v=getComputedStyle(d).backgroundColor; d.remove(); return v }
          const ok = px(getComputedStyle(document.documentElement).getPropertyValue('--ok-bg').trim())
          const out = {}
          for (const b of document.querySelectorAll('button')) {
            const txt = (b.innerText || '').trim()
            if (!txt) continue
            out[txt] = { verd: getComputedStyle(b).backgroundColor === ok,
                         blocat: b.disabled, title: b.title || '' }
          }
          return out
        }""")
        def busca(frag):
            for k, v in estat.items():
                if frag.lower() in k.lower():
                    return k, v
            return None, None

        _, pom = busca('Editar POM')
        _, grad = busca('Graduació')
        _, presa = busca('Mesurar')
        comprova('«Editar POM» es pinta FET (verd)', pom and pom['verd'], str(pom))
        comprova('«Graduació» es pinta FET (verd)', grad and grad['verd'], str(grad))
        comprova('«Mesurar prenda» ja NO està bloquejat (hi ha taula)',
                 presa and not presa['blocat'], str(presa))
        pag.screenshot(path=str(OUT / 'flux_01_stepper.png'), full_page=True)
        nav.close()


def main():
    if not TOKEN:
        sys.exit('Falta FTT_QA_TOKEN')
    if not DIST.exists():
        sys.exit(f'No hi ha bundle a {DIST}')
    OUT.mkdir(exist_ok=True)
    sess = requests.Session()
    if d1_d3_backend(sess):
        d2_stepper(sess)
    mal = [r for r in resultats if not r[0]]
    print('\n' + '=' * 76)
    print(f'{len(resultats) - len(mal)}/{len(resultats)} comprovacions OK')
    for _, nom, detall in mal:
        print(f'  ✗ {nom} — {detall}')
    sys.exit(1 if mal else 0)


if __name__ == '__main__':
    main()
