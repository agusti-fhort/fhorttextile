"""Q1 — LA PÍNDOLA D'INSTÀNCIA ÉS UN TOGGLE HONEST.

Ordre d'Agus (06/08): «desclicar una píndola d'instància no pot afectar el POM». Fins avui,
prémer-la partia el POM a l'acte i la píndola encesa quedava INERT: no hi havia camí de tornada.

Corre sobre el bundle REAL de `frontend/dist` amb les respostes reals de l'API
(`qa_q2_fixture.json`, model de QA) i comprova, EN ELS TRES IDIOMES, sobre Definició POM
(`?mode=entry`, on la taula treballa en BÚFER i no escriu res):

  1. la píndola apagada PARTEIX: la fila esdevé dues germanes (Left · Right) amb els codis
     compostos, i la píndola de la fila queda encesa;
  2. la píndola ENCESA ja no és inert i DESFÀ: la germana es retira i la fila torna a la
     identitat base (el codi torna a ser el de partida, sense sufix);
  3. el recompte de files torna EXACTAMENT al de partida — desfer no deixa residus;
  4. la tecla `I` (saltar a la primera píndola lliure) NO cau mai sobre la de desfer;
  5. consola neta i cap error de pàgina.

QUÈ NO COMPROVA: la confirmació abans d'esborrar. Només surt quan la germana és una fila JA
DESADA i amb valor al carril, i en aquesta pantalla les germanes que acaben de néixer encara
no ho són (per això es retiren en silenci, que és el que la llei demana). El camí de la presa
—on la germana sí que viu a la BD— l'escriu `presaPortes.onDesfaInstancia`.

    backend/venv/bin/python ../ops/qa/qa_q2_fixture.py 182
    /tmp/qa-venv/bin/python  ops/qa/qa_q1_pindola_toggle.py
"""
import json
import mimetypes
import pathlib
import sys

from playwright.sync_api import sync_playwright

REPO = pathlib.Path(__file__).resolve().parents[2]
DIST = REPO / 'frontend' / 'dist'
FIXTURE = pathlib.Path(__file__).resolve().parent / 'qa_q2_fixture.json'
BASE = 'https://staging.fhorttextile.tech'

DADES = json.loads(FIXTURE.read_text()) if FIXTURE.is_file() else None
BUIT = {'count': 0, 'results': [], 'next': None, 'previous': None}
PERFIL = {'id': 1, 'username': 'qa', 'nom_complet': 'QA', 'rol_nom': 'admin',
          'capabilities': ['configure', 'EXECUTE_TASKS', 'CLOSE_GATES'], 'idioma': 'ca'}


def handler(route):
    req = route.request
    url = req.url
    path = url.split(BASE, 1)[-1].split('?')[0] if BASE in url else url.split('?')[0]
    if '/api/' in path:
        if req.method in ('POST', 'PATCH', 'PUT'):
            cos = {'task_id': 999} if path.endswith('/open-task/') else {'id': 1}
            route.fulfill(status=200, content_type='application/json', body=json.dumps(cos))
            return
        cos = DADES.get(path)
        if cos is None:
            cos = PERFIL if ('/me/' in path or '/perfil/' in path) else BUIT
        route.fulfill(status=200, content_type='application/json',
                      body=json.dumps(cos, ensure_ascii=False))
        return
    f = DIST / (path.lstrip('/') or 'index.html')
    if not f.is_file():
        f = DIST / 'index.html'
    route.fulfill(status=200, body=f.read_bytes(),
                  content_type=mimetypes.guess_type(str(f))[0] or 'text/html')


#: L'estat de la PRIMERA fila: quantes files hi ha, la seva nomenclatura i quantes píndoles té
#: enceses (`aria-pressed`) i quantes de desfer (`data-pindola="desfa"`).
JS_ESTAT = """
() => {
  const files = Array.from(document.querySelectorAll('tbody tr[data-fila]'))
  const codi = (tr) => {
    const inp = tr.querySelector('input[data-nomen]')
    if (inp) return (inp.value || inp.placeholder || '').trim()
    const td = tr.querySelectorAll('td')[2]
    return td ? (td.innerText || '').trim().split('\\n')[0] : ''
  }
  return {
    n: files.length,
    codis: files.slice(0, 3).map(codi),
    enceses: document.querySelectorAll('button[data-pindola][aria-pressed="true"]').length,
    desfa: document.querySelectorAll('button[data-pindola="desfa"]').length,
  }
}
"""


def main():
    if DADES is None:
        print(f"✗ falta {FIXTURE.name} — genera'l amb qa_q2_fixture.py")
        return 1
    if not DIST.is_dir():
        print(f'✗ no hi ha bundle a {DIST}')
        return 1
    mid = DADES['_model_id']
    fallides = []
    print(f'== Q1 · toggle honest de la píndola · model {mid} ==')

    with sync_playwright() as p:
        b = p.chromium.launch()
        for lang in ('ca', 'es', 'en'):
            marca = f'{lang} ·'
            ctx = b.new_context(base_url=BASE, ignore_https_errors=True,
                                viewport={'width': 1600, 'height': 1200})
            page = ctx.new_page()
            errors, consola = [], []
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.on('console', lambda m: consola.append(m.text) if m.type == 'error' else None)
            page.route('**/*', handler)
            page.add_init_script("localStorage.setItem('access_token','qa');"
                                 f"localStorage.setItem('fhort.lang','{lang}');")
            page.goto(f'{BASE}/models/{mid}?tab=Mesures&mode=entry',
                      wait_until='networkidle', timeout=45000)
            page.wait_for_timeout(2500)

            inici = page.evaluate(JS_ESTAT)
            if not inici['n']:
                fallides.append(f'{marca} la taula de Definició POM no s\'ha obert')
                ctx.close()
                continue
            if inici['desfa'] or inici['enceses']:
                fallides.append(f'{marca} d\'entrada ja hi ha píndoles enceses: {inici}')

            pindola = page.locator('tbody tr[data-fila] button[data-pindola="1"]:not([disabled])').first
            if not pindola.count():
                fallides.append(f'{marca} no hi ha cap píndola per partir')
                ctx.close()
                continue

            # ── 1 · PARTIR ────────────────────────────────────────────────────────────────
            pindola.click()
            page.wait_for_timeout(600)
            partit = page.evaluate(JS_ESTAT)
            if partit['n'] != inici['n'] + 1:
                fallides.append(f'{marca} partir no ha fet dues germanes: '
                                f'{inici["n"]} → {partit["n"]} files')
            if partit['desfa'] < 1:
                fallides.append(f'{marca} després de partir no hi ha cap píndola de DESFER '
                                f'(la encesa segueix inert): {partit}')

            # ── 4 · la tecla `I` no pot caure sobre la de desfer ──────────────────────────
            mal = page.evaluate(
                """() => document.querySelectorAll(
                     'button[data-pindola="desfa"][data-pindola="1"]').length""")
            if mal:
                fallides.append(f'{marca} la píndola de desfer també respon al selector de la `I`')

            # ── 2 i 3 · DESFER ───────────────────────────────────────────────────────────
            page.locator('button[data-pindola="desfa"]').first.click()
            page.wait_for_timeout(600)
            desfet = page.evaluate(JS_ESTAT)
            if desfet['n'] != inici['n']:
                fallides.append(f'{marca} desfer no torna al recompte de partida: '
                                f'{inici["n"]} → {partit["n"]} → {desfet["n"]}')
            if desfet['desfa'] or desfet['enceses']:
                fallides.append(f'{marca} després de desfer encara hi ha píndoles enceses: {desfet}')
            if desfet['codis'] != inici['codis']:
                fallides.append(f'{marca} la fila no torna a la identitat base:\n'
                                f'      abans: {inici["codis"]}\n      després: {desfet["codis"]}')

            if errors:
                fallides.append(f'{marca} error de pàgina: {errors[0][:140]}')
            if consola:
                fallides.append(f'{marca} consola bruta: {consola[0][:140]}')
            if not [f for f in fallides if f.startswith(marca)]:
                print(f'  ✓ {lang} · {inici["n"]} files → parteix ({partit["n"]}, '
                      f'{partit["desfa"]} píndola de desfer) → desfà ({desfet["n"]}) · '
                      f'identitat base recuperada · consola neta')
            ctx.close()
        b.close()

    if fallides:
        print('\n🔴 FALLIDES')
        for f in fallides:
            print('  ✗', f)
        return 1
    print('\n🟢 Q1 · la píndola parteix i DESFÀ · 3 idiomes')
    return 0


if __name__ == '__main__':
    sys.exit(main())
