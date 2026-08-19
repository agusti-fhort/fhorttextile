"""ARNÈS · DIAGNOSI dels fixes 1·2·3 del bloc S36 (ESCALAT · FAMÍLIES · PAUSATS).

⚠️ **CAP ESCRIPTURA.** Mateixa llei que `qa_b34_router_i_estat.py`: tot POST/PATCH/PUT/DELETE
es respon localment amb l'eco del cos i es censa. Aquesta sonda MESURA, no toca res.

Què mesura, i per què cada afirmació és un NÚMERO i no una captura:
  1 · ESCALAT · el bloc «Regla de graduació» — fons de les cel·les de la regla (crema o no) i
      amplada de cada columna de la regla. Una captura demostra com es veia el dia que es va
      prendre; una amplada en píxels es pot comparar demà.
  2 · CONSULTA DE MESURES · vista Famílies — mida de lletra COMPUTADA dels textos interiors.
      El defecte que es busca és heretar els 16px del document en comptes de `--fs-body` (12px).
  3 · DASHBOARD · les quatre columnes del tauler — `borderLeftWidth` computat de cadascuna.

    FTT_QA_TOKEN=... /tmp/qa-venv/bin/python ops/qa/qa_s2_fixes_diagnosi.py
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

    with sync_playwright() as p:
        nav = p.chromium.launch()
        ctx = nav.new_context(viewport={'width': 1700, 'height': 1100})
        pag = ctx.new_page()
        pag.route('**/*', handler)
        pag.goto(BASE + '/', wait_until='domcontentloaded')
        pag.evaluate("([t]) => { localStorage.setItem('access_token', t);"
                     " localStorage.setItem('fhort.lang', 'ca') }", [TOKEN])

        def obre(url, captura, espera=3500):
            pag.goto(BASE + url, wait_until='networkidle')
            pag.wait_for_timeout(espera)
            pag.screenshot(path=str(OUT / captura), full_page=True)

        # ── 3 · DASHBOARD · la vora de les quatre columnes ────────────────────────────────
        print('\n3 · DASHBOARD · les quatre columnes del tauler')
        obre('/', 's2fix_3_dashboard.png')
        cols = pag.evaluate("""() => {
            const noms = ['Pendents', 'En curs', 'Pausats', 'Fets']
            const out = []
            for (const n of noms) {
              const cap = [...document.querySelectorAll('span')]
                .find(s => s.textContent.trim() === n)
              if (!cap) { out.push({ nom: n, trobat: false }); continue }
              const col = cap.closest('div').parentElement   // capçalera → contenidor
              const cs = getComputedStyle(col)
              const r = col.getBoundingClientRect()
              out.push({ nom: n, trobat: true, x: Math.round(r.x), w: Math.round(r.width),
                         left: cs.borderLeftWidth, right: cs.borderRightWidth,
                         top: cs.borderTopWidth, bottom: cs.borderBottomWidth,
                         colorL: cs.borderLeftColor })
            }
            return out
        }""")
        for c in cols:
            print('   ', c)
        # I LA TARGETA DE DINS, que és qui de debò es quedava sense vora esquerra: Pausats és
        # l'única columna amb targetes, i per això el forat es llegia com si fos del contenidor.
        targetes = pag.evaluate("""() => [...document.querySelectorAll('button')]
            .filter(b => /tasques$/m.test(b.innerText.trim()))
            .slice(0, 3)
            .map(b => { const cs = getComputedStyle(b)
              return { txt: b.innerText.trim().split('\\n')[0].slice(0, 22),
                       left: `${cs.borderLeftWidth} ${cs.borderLeftColor}`,
                       right: `${cs.borderRightWidth} ${cs.borderRightColor}`,
                       top: `${cs.borderTopWidth} ${cs.borderTopColor}`,
                       ombra: cs.boxShadow } })""")
        print('    targetes de model:')
        for c in targetes:
            print('      ', c)

        # ── 1 · ESCALAT · el bloc de la regla ─────────────────────────────────────────────
        print('\n1 · ESCALAT · bloc «Regla de graduació»')
        obre(f'/models/{MODEL}?tab=Escalat', 's2fix_1_escalat.png', 5000)
        regla = pag.evaluate("""() => {
            const ths = [...document.querySelectorAll('th')]
            const cap = ths.find(x => /Regla de graduaci/i.test(x.textContent))
            if (!cap) return { trobat: false, ths: ths.slice(0, 12).map(x => x.textContent.trim()) }
            const taula = cap.closest('table')
            const files = [...taula.querySelectorAll('thead tr')]
            const sub = [...files[1].querySelectorAll('th')].map(x => ({
              txt: x.textContent.trim(),
              w: Math.round(x.getBoundingClientRect().width),
              bg: getComputedStyle(x).backgroundColor,
            }))
            const primera = taula.querySelector('tbody tr')
            const tds = [...primera.querySelectorAll('td')].map(x => ({
              txt: x.textContent.trim().slice(0, 14),
              w: Math.round(x.getBoundingClientRect().width),
              bg: getComputedStyle(x).backgroundColor,
            }))
            const grup = [...files[0].querySelectorAll('th')].map(x => ({
              txt: x.textContent.trim(), span: x.colSpan, rows: x.rowSpan }))
            return { trobat: true, capBg: getComputedStyle(cap).backgroundColor, grup, sub, tds }
        }""")
        if not regla.get('trobat'):
            print('    ❌ capçalera de la regla NO trobada:', regla.get('ths'))
        else:
            print('    capçalera de grup, fons:', regla['capBg'])
            print('    fila 1 de capçalera (grups):')
            for g in regla['grup']:
                print(f"       {g['txt'][:34]!r:<36} colSpan={g['span']} rowSpan={g['rows']}")
            print('    fila 2 (columnes):')
            for s in regla['sub']:
                print(f"       {s['txt'][:22]!r:<24} w={s['w']:<5} bg={s['bg']}")
            print('    primera fila de dades:')
            for d in regla['tds'][:8]:
                print(f"       {d['txt']!r:<16} w={d['w']:<5} bg={d['bg']}")

        # ── 2 · CONSULTA DE MESURES · la vista Famílies ───────────────────────────────────
        print('\n2 · CONSULTA DE MESURES · vista Famílies')
        obre(f'/models/{MODEL}?tab=Mesures', 's2fix_2_mesures.png', 4000)
        pag.evaluate("""() => {
            const b = [...document.querySelectorAll('button')]
              .find(x => /Comprovaci/i.test(x.textContent))
            if (b) b.click()
        }""")
        pag.wait_for_timeout(3000)
        pag.screenshot(path=str(OUT / 's2fix_2_families.png'), full_page=True)
        fam = pag.evaluate("""() => {
            const caps = [...document.querySelectorAll('span')]
              .filter(s => /Fam[ií]lies de mesura/i.test(s.textContent))
            if (!caps.length) return { trobat: false }
            const sec = caps[0].closest('div')
            const arrel = sec.parentElement
            const mostra = (sel, n) => [...arrel.querySelectorAll(sel)].slice(0, n).map(e => ({
              txt: e.textContent.trim().slice(0, 20),
              fs: getComputedStyle(e).fontSize,
            }))
            return {
              trobat: true,
              docBody: getComputedStyle(document.body).fontSize,
              taula: [...arrel.querySelectorAll('table')].slice(0, 1)
                .map(e => getComputedStyle(e).fontSize),
              th: mostra('th', 5),
              td: mostra('td', 6),
            }
        }""")
        print('    ', json.dumps(fam, ensure_ascii=False, indent=2)[:1400])

        # El mateix mesurat a la resta del panell, per contrast.
        altres = pag.evaluate("""() => {
            const out = {}
            const b = [...document.querySelectorAll('button')]
              .find(x => /Bloquegen l'enviament/i.test(x.textContent))
            if (b) out.seccio = getComputedStyle(b).fontSize
            const h = [...document.querySelectorAll('h2')]
              .find(x => /Comprovaci/i.test(x.textContent))
            if (h) out.titol = getComputedStyle(h).fontSize
            const nums = [...document.querySelectorAll('b')]
              .filter(x => /^\\d+$/.test(x.textContent.trim()))
              .map(x => ({ n: x.textContent.trim(), fs: getComputedStyle(x).fontSize }))
            out.kpis = nums.slice(0, 4)
            return out
        }""")
        print('    contrast:', altres)

        print('\nCENS D ESCRIPTURES:', escriptures or 'cap')
        nav.close()


if __name__ == '__main__':
    main()
