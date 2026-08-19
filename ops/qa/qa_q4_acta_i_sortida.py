"""Q4 — LA FITXA D'UNA SESSIÓ TANCADA ÉS UNA ACTA, I «GRAVAR I TORNAR» TORNA D'ON VENIES.

Captura 13:13 (fittings/148): la fitxa d'una sessió Tancada sortia amb la capçalera «Gravar el
fitting» i el badge «Tancada · només lectura» —dos estats a la mateixa vista—, amb les
observacions encara editables i el botó de pujar imatges. I s'hi havia arribat prement «Gravar i
tornar» des de Mesures, que no és d'on es venia.

Aquest fum corre sobre el bundle REAL de `frontend/dist` amb les respostes reals de l'API
(`qa_q4_fixture.json`) i comprova, EN ELS TRES IDIOMES:

  1. ACTA NETA · la fitxa d'una sessió Tancada no diu «Gravar el fitting», no té cap `textarea`,
     cap `input[type=file]` ni cap botó d'acció (gravar · descartar · afegir imatges), i sí que
     té els quatre blocs de lectura (Canvis · Observacions · Imatges · taula);
  2. ORDRE · les files de la taula de la fitxa surten en l'ordre del model (el mateix que serveix
     `piece-fittings/<id>/`, que és el que Q3 ordena) i els CODIS són els del model (`nom_fitxa`);
  3. PDF · el full (`/fittings/<s>/full/<m>`) porta les MATEIXES files, en el mateix ordre;
  4. SORTIDA · amb la sessió VIVA, «Gravar i tornar» deixa la persona a `?tab=Mesures` del model,
     sense `fitting_session` a la URL — no a la fitxa del fitting.

⚠️ El pas 4 fa servir la MATEIXA sessió amb `estat` forçat a 'Oberta' al fixture (i les respostes
de `close`/`seal` estubejades): és una comprovació de NAVEGACIÓ, no d'escriptura. Qui verifica
l'escriptura és `qa_q34_presa_reconciliada.py`, que corre contra l'API de debò.

    backend/venv/bin/python ../ops/qa/qa_q4_fixture.py 149
    /tmp/qa-venv/bin/python  ops/qa/qa_q4_acta_i_sortida.py
"""
import copy
import json
import mimetypes
import pathlib
import sys

from playwright.sync_api import sync_playwright

REPO = pathlib.Path(__file__).resolve().parents[2]
DIST = REPO / 'frontend' / 'dist'
FIXTURE = pathlib.Path(__file__).resolve().parent / 'qa_q4_fixture.json'
BASE = 'https://staging.fhorttextile.tech'

DADES = json.loads(FIXTURE.read_text()) if FIXTURE.is_file() else None
BUIT = {'count': 0, 'results': [], 'next': None, 'previous': None}
PERFIL = {'id': 1, 'username': 'qa', 'nom_complet': 'QA', 'rol_nom': 'admin',
          'capabilities': ['configure', 'EXECUTE_TASKS', 'CLOSE_GATES'], 'idioma': 'ca'}

#: `fitting.save.title` (el títol d'ACCIÓ que no pot sortir a una acta) i `fitting.save.title_acta`.
TITOL_ACCIO = {'ca': 'Gravar el fitting', 'es': 'Grabar el fitting', 'en': 'Save fitting'}
TITOL_ACTA = {'ca': 'Fitxa del fitting', 'es': 'Ficha del fitting', 'en': 'Fitting record'}
#: `fitting.save.{changes,observations,images}`
BLOCS = {
    'ca': ['Canvis', 'Observacions', 'Imatges'],
    'es': ['Cambios', 'Observaciones', 'Imágenes'],
    'en': ['Changes', 'Observations', 'Images'],
}
#: `fitting.save.save_and_back`
GRAVAR_I_TORNAR = {'ca': 'Gravar i tornar', 'es': 'Guardar y volver', 'en': 'Save and go back'}


def fes_handler(viva=False):
    dades = copy.deepcopy(DADES)
    sid = dades['_session_id']
    if viva:
        dades[f'/api/v1/fitting-sessions/{sid}/']['estat'] = 'Oberta'
        dades[f'/api/v1/fitting-sessions/{sid}/']['estat_display'] = 'Oberta'

    def handler(route):
        req = route.request
        url = req.url
        path = url.split(BASE, 1)[-1].split('?')[0] if BASE in url else url.split('?')[0]
        if '/api/' in path:
            if req.method in ('POST', 'PATCH', 'PUT'):
                # Escriptures ESTUBEJADES: el fum no toca la BD. `seal` ha de dir 'Tancada' o el
                # front s'atura amb «no s'ha pogut segellar» (i tindria raó).
                cos = {'estat': 'Tancada'} if path.endswith('/seal/') else {'task_id': 999, 'id': 1}
                route.fulfill(status=200, content_type='application/json', body=json.dumps(cos))
                return
            cos = dades.get(path)
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
    return handler


def obre(ctx, ruta, lang, handler, espera=2200):
    page = ctx.new_page()
    errors, consola = [], []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('console', lambda m: consola.append(m.text) if m.type == 'error' else None)
    page.route('**/*', handler)
    page.add_init_script("localStorage.setItem('access_token','qa');"
                         f"localStorage.setItem('fhort.lang','{lang}');")
    page.goto(f'{BASE}{ruta}', wait_until='networkidle', timeout=45000)
    page.wait_for_timeout(espera)
    return page, errors, consola


def main():
    if DADES is None:
        print(f"✗ falta {FIXTURE.name} — genera'l amb qa_q4_fixture.py")
        return 1
    if not DIST.is_dir():
        print(f'✗ no hi ha bundle a {DIST}')
        return 1

    sid, mid, pid = DADES['_session_id'], DADES['_model_id'], DADES['_piece_id']
    graella = DADES[f'/api/v1/piece-fittings/{pid}/']
    base = (graella['model'].get('base_size_label') or '').strip()
    # L'ordre que l'API serveix (Q3) és l'ordre que la pantalla i el paper han de pintar.
    ordre_api = [(l['nom_fitxa'] or l['codi']) for l in graella['lines'] if l['size_label'] == base]

    fallides = []
    print(f'== Q4 · acta i sortida · sessió {sid} · model {mid} · {len(ordre_api)} mesures ==')
    print(f'  ordre de l\'API: {ordre_api}')

    with sync_playwright() as p:
        b = p.chromium.launch()
        for lang in ('ca', 'es', 'en'):
            ctx = b.new_context(base_url=BASE, ignore_https_errors=True,
                                viewport={'width': 1600, 'height': 1200})
            marca = f'{lang} ·'

            # ── 1 · ACTA NETA ─────────────────────────────────────────────────────────────
            page, errors, consola = obre(ctx, f'/fittings/{sid}', lang, fes_handler())
            cos = page.inner_text('body')
            if TITOL_ACCIO[lang] in cos:
                fallides.append(f'{marca} l\'acta encara porta el títol d\'acció '
                                f'«{TITOL_ACCIO[lang]}»')
            if TITOL_ACTA[lang] not in cos:
                fallides.append(f'{marca} l\'acta no es diu «{TITOL_ACTA[lang]}»')
            n_textarea = page.evaluate("() => document.querySelectorAll('textarea').length")
            n_file = page.evaluate("() => document.querySelectorAll('input[type=file]').length")
            n_input = page.evaluate(
                "() => document.querySelectorAll('input:not([type=file])').length")
            if n_textarea:
                fallides.append(f'{marca} l\'acta té {n_textarea} textarea editable')
            if n_file:
                fallides.append(f'{marca} l\'acta encara ofereix pujar imatges')
            if n_input:
                fallides.append(f'{marca} l\'acta té {n_input} camps de text editables')
            falten = [x for x in BLOCS[lang] if x not in cos]
            if falten:
                fallides.append(f'{marca} a l\'acta hi falten els blocs {falten}')

            # ── 2 · ORDRE I CODIS DEL MODEL ───────────────────────────────────────────────
            # La taula de lectura de la dreta pinta la identitat de la fila en columnes pròpies
            # (règim, capa, nomenclatura…). No se'n fixa cap índex: de cada fila s'agafa la
            # PRIMERA cel·la que digui una de les nomenclatures que l'API serveix. Si la
            # pantalla en pintés una altra —o cap—, la fila cauria i el fum ho diria.
            vist = page.evaluate(
                """(codis) => {
                     const t = Array.from(document.querySelectorAll('table'))
                       .sort((a,b) => b.querySelectorAll('tbody tr').length
                                    - a.querySelectorAll('tbody tr').length)[0]
                     if (!t) return []
                     const jocs = new Set(codis)
                     return Array.from(t.querySelectorAll('tbody tr')).map(tr => {
                       for (const td of tr.querySelectorAll('td')) {
                         for (const tros of (td.innerText || '').split('\\n')) {
                           const s = tros.trim()
                           if (jocs.has(s)) return s
                         }
                       }
                       return ''
                     }).filter(Boolean)
                   }""", ordre_api)
            if vist and vist != ordre_api:
                fallides.append(f'{marca} la taula de l\'acta no segueix l\'ordre del model\n'
                                f'      pantalla: {vist}\n      api: {ordre_api}')
            if not vist:
                fallides.append(f'{marca} la taula de l\'acta surt buida')

            if errors:
                fallides.append(f'{marca} error de pàgina (acta): {errors[0][:140]}')
            if consola:
                fallides.append(f'{marca} consola bruta (acta): {consola[0][:140]}')
            page.close()

            # ── 3 · EL PDF ────────────────────────────────────────────────────────────────
            page, errors, consola = obre(ctx, f'/fittings/{sid}/full/{mid}', lang, fes_handler())
            files_pdf = page.evaluate(
                """() => Array.from(document.querySelectorAll('table tbody tr'))
                     .map(tr => (tr.querySelectorAll('td')[2] || {}).innerText || '')
                     .map(s => s.trim()).filter(Boolean)""")
            if files_pdf != ordre_api:
                fallides.append(f'{marca} el PDF no porta les mateixes files/ordre\n'
                                f'      pdf: {files_pdf}\n      api: {ordre_api}')
            if errors:
                fallides.append(f'{marca} error de pàgina (PDF): {errors[0][:140]}')
            if consola:
                fallides.append(f'{marca} consola bruta (PDF): {consola[0][:140]}')
            page.close()

            # ── 4 · LA SORTIDA DE «GRAVAR I TORNAR» ───────────────────────────────────────
            page, errors, consola = obre(
                ctx, f'/models/{mid}?tab=Mesures&fitting_session={sid}', lang,
                fes_handler(viva=True), espera=3000)
            boto = page.locator('button', has_text=GRAVAR_I_TORNAR[lang]).first
            if not boto.count():
                fallides.append(f'{marca} no hi ha «{GRAVAR_I_TORNAR[lang]}» a la superfície de presa')
            else:
                boto.click()
                page.wait_for_timeout(2500)
                url = page.url
                if 'fitting_session' in url:
                    fallides.append(f'{marca} després de gravar la URL encara porta la sessió: {url}')
                if f'/models/{mid}' not in url or 'tab=Mesures' not in url:
                    fallides.append(f'{marca} «Gravar i tornar» no cau al tab Mesures del model: {url}')
                if '/fittings/' in url:
                    fallides.append(f'{marca} «Gravar i tornar» porta a la fitxa del fitting: {url}')
            if errors:
                fallides.append(f'{marca} error de pàgina (sortida): {errors[0][:140]}')
            if consola:
                fallides.append(f'{marca} consola bruta (sortida): {consola[0][:140]}')
            page.close()

            if not [f for f in fallides if f.startswith(marca)]:
                print(f'  ✓ {lang} · acta neta ({len(vist)} files en ordre) · PDF idèntic · '
                      f'sortida al tab Mesures · consola neta')
            ctx.close()
        b.close()

    if fallides:
        print('\n🔴 FALLIDES')
        for f in fallides:
            print('  ✗', f)
        return 1
    print('\n🟢 Q4 · acta neta · ordre del model · PDF idèntic · sortida correcta · 3 idiomes')
    return 0


if __name__ == '__main__':
    sys.exit(main())
