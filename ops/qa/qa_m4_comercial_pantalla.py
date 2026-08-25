"""M4 · EL NUMERAL I EL DESBORDAMENT — QA DE PANTALLA sobre el bundle REAL i el backend REAL.

`build verd ≠ front viu`, i el fum HTTP prova el PAYLOAD, no el que es dibuixa. Això munta el
bundle de `frontend/dist` i el fa parlar amb el **gunicorn del worktree** (mai
`ftt-staging.service`, que serveix un ALTRE arbre). Mateixa forma que `qa_m3_cicle_pantalla.py`.

Dues pantalles, que són les dues cares d'M4:
  · **La fitxa de COMANDA** — el numeral de voltes (FIT-5) s'hi veu i s'hi EDITA.
  · **La SAFATA d'albaranables** — la volta desbordada hi surt agrupada, marcada i amb el perquè
    (FIT-12). La safata viu dins d'un albarà DRAFT: el banc en fabrica un de sintètic.

⚠️ **AQUEST FUM ESCRIU**, i només sobre el banc `[QA-M4]`: edita el numeral de la seva comanda
sintètica i el torna a deixar com estava. **Mai el 1383, mai un model o una comanda reals.**

    cd backend && venv/bin/python ../ops/qa/banc_m4_desbordament.py --remunta
    setsid nohup venv/bin/gunicorn fhort.wsgi:application \\
        --chdir /var/www/ftt-m4/backend --bind 127.0.0.1:8141 --workers 2 --timeout 60 &
    cd frontend && npm run build
    /tmp/qa-venv/bin/python ops/qa/qa_m4_comercial_pantalla.py

Captures a `ops/qa/captures/m4_*.png`. Codi de sortida 1 si alguna mesura falla.
"""
import json
import mimetypes
import os
import pathlib
import subprocess
import sys
import urllib.error
import urllib.request

from playwright.sync_api import sync_playwright

REPO = pathlib.Path(__file__).resolve().parents[2]
DIST = REPO / 'frontend' / 'dist'
CAPTURES = REPO / 'ops' / 'qa' / 'captures'
BASE = 'https://staging.fhorttextile.tech'
BACKEND = os.environ.get('BACKEND', 'http://127.0.0.1:8141')

#: 🔑 DOS INTÈRPRETS: Playwright viu a `/tmp/qa-venv` i Django al venv del backend. El token i
#: els pk del banc es demanen al venv de Django per subprocés (lliçó d'M2).
VENV_BACKEND = REPO / 'backend' / 'venv' / 'bin' / 'python'

_BOOTSTRAP = r'''
import json, os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fhort.settings')
django.setup()
from django_tenants.utils import schema_context
from fhort.accounts.models import UserProfile
from fhort.auth_jwt import TenantTokenObtainPairSerializer
from fhort.commerce.models import DeliveryNote
from fhort.models_app.models import Model
from fhort.tasks.models import Ronda
with schema_context('fhort'):
    banc = {m.codi_intern: m.pk
            for m in Model.objects.filter(codi_intern__startswith='QA-M4-')}
    r3 = Ronda.objects.filter(model__codi_intern='QA-M4-0001', seq=3).first()
    linia = r3.linia_comanda if r3 else None
    draft = DeliveryNote.objects.filter(
        status='DRAFT', notes='[QA-M4] esborrany del banc de desbordament').first()
    perfil = UserProfile.objects.order_by('pk').first()
    # 🚨 El claim `tenant_schema` l'estampa AQUEST serializer llegint l'schema ACTIU.
    token = str(TenantTokenObtainPairSerializer.get_token(perfil.user).access_token)
    # ⚠️ TOT es resol DINS del `schema_context`. Fora, el `search_path` torna a `public` i
    # `linia.order` peta amb «relation commerce_salesorder does not exist» — mesurat.
    sortida = {
        'banc': banc, 'token': token,
        'comanda': linia.order_id if linia else None,
        'comanda_num': linia.order.document_number if linia else None,
        'linia': linia.pk if linia else None,
        'numeral': linia.rounds_included if linia else None,
        'draft': draft.pk if draft else None,
    }
print('@@' + json.dumps(sortida))
'''

ok, ko = [], []


def bootstrap():
    r = subprocess.run([str(VENV_BACKEND), '-c', _BOOTSTRAP], capture_output=True, text=True,
                       cwd=str(REPO / 'backend'))
    linia = next((l for l in r.stdout.splitlines() if l.startswith('@@')), None)
    if linia is None:
        raise SystemExit(f'no he pogut emetre el JWT amb {VENV_BACKEND}:\n{r.stderr[-2000:]}')
    return json.loads(linia[2:])


def bolca(etiqueta, cos):
    if os.environ.get('M4_DEBUG'):
        print(f'\n----- {etiqueta} -----\n{cos[:4000]}\n----- fi -----\n')


def crit(nom, cond, detall=''):
    (ok if cond else ko).append(nom)
    print(f"  {'OK  ' if cond else 'FAIL'} {nom}{(' · ' + str(detall)) if detall else ''}")


def fes_handler(token):
    def handler(route):
        req = route.request
        # El que no és del nostre origen, PASSA: el webfont d'icones ve de CDN i, interceptant-ho
        # tot, la captura sortiria sense cap icona (lliçó d'M2).
        if not req.url.startswith(BASE):
            route.continue_()
            return
        cami = req.url.split(BASE, 1)[-1]
        if cami.startswith('/api/'):
            dades = req.post_data_buffer if req.method in ('POST', 'PATCH', 'PUT') else None
            r = urllib.request.Request(BACKEND + cami, data=dades, method=req.method)
            r.add_header('Host', 'staging.fhorttextile.tech')
            r.add_header('Content-Type', 'application/json')
            r.add_header('Authorization', 'Bearer ' + token)
            try:
                with urllib.request.urlopen(r, timeout=60) as resp:
                    route.fulfill(status=resp.status, content_type='application/json',
                                  body=resp.read())
            except urllib.error.HTTPError as e:
                route.fulfill(status=e.code, content_type='application/json', body=e.read())
            except Exception as e:                            # noqa: BLE001
                route.fulfill(status=502, content_type='application/json',
                              body=json.dumps({'error': str(e)}).encode())
            return
        f = DIST / (cami.split('?')[0].lstrip('/') or 'index.html')
        if not f.is_file():
            f = DIST / 'index.html'                           # fallback d'SPA
        route.fulfill(status=200, body=f.read_bytes(),
                      content_type=mimetypes.guess_type(str(f))[0] or 'text/html')
    return handler


def main():
    if not DIST.is_dir():
        raise SystemExit(f'no hi ha bundle a {DIST} — fes `npm run build` primer')
    CAPTURES.mkdir(parents=True, exist_ok=True)

    a = bootstrap()
    if 'QA-M4-0001' not in a['banc'] or not a['comanda'] or not a['draft']:
        raise SystemExit('Falta el banc: corre `banc_m4_desbordament.py --remunta`.')
    token = a['token']
    print(f"bundle={DIST} · backend={BACKEND} · banc {sorted(a['banc'])} · "
          f"comanda {a['comanda_num']} · draft {a['draft']}\n")

    with sync_playwright() as p:
        navegador = p.chromium.launch()
        ctx = navegador.new_context(base_url=BASE, ignore_https_errors=True,
                                    viewport={'width': 1440, 'height': 1000})
        pagina = ctx.new_page()
        errors = []
        pagina.on('pageerror', lambda e: errors.append(str(e)))
        pagina.route('**/*', fes_handler(token))
        # L'idioma es FIXA: sense això i18next el dedueix del `navigator` (al Chromium headless,
        # `en`) i la revisió visual sortiria en anglès.
        pagina.add_init_script(f"localStorage.setItem('access_token', {json.dumps(token)});"
                               "localStorage.setItem('fhort.lang', 'ca')")

        # ── A · LA FITXA DE COMANDA: el numeral hi és i s'hi edita (FIT-5) ──────────────────
        print('── A · el numeral a la fitxa de comanda ──')
        pagina.goto(f"{BASE}/comercial/comandes/{a['comanda']}", wait_until='networkidle',
                    timeout=60000)
        pagina.wait_for_timeout(2000)
        cos = pagina.inner_text('body')
        bolca('m4_comanda', cos)
        pagina.screenshot(path=str(CAPTURES / 'm4_a1_comanda_numeral.png'), full_page=True)
        crit('la pantalla no peta (cap error de React)',
             not [e for e in errors if 'Minified React error' in e
                  or 'before initialization' in e], errors[:1])
        # ⚠️ SENSE CAIXA: els rètols de columna els pinta el CSS en MAJÚSCULES i `inner_text`
        # torna el text ja transformat (el parany que va fer mentir el fum d'M2).
        crit('la taula de línies té la columna del numeral', 'voltes incl' in cos.lower(),
             [l for l in cos.splitlines() if 'oltes' in l][:2])

        cel = pagina.locator("input[type='number'][placeholder='Sense límit']")
        crit('…i la cel·la és EDITABLE, amb el valor del banc', cel.count() >= 1
             and cel.first.input_value() == str(a['numeral']),
             (cel.count(), cel.count() and cel.first.input_value()))

        # L'EDICIÓ DE DEBÒ: escriure i sortir del camp (save-on-blur), i tornar-ho a deixar.
        cel.first.fill('4')
        pagina.keyboard.press('Tab')
        pagina.wait_for_timeout(1800)
        cos = pagina.inner_text('body')
        pagina.screenshot(path=str(CAPTURES / 'm4_a2_numeral_desat.png'))
        crit('desar-lo dona el missatge d\'èxit de la casa',
             'numeral de voltes actualitzat' in cos.lower(),
             [l for l in cos.splitlines() if 'umeral' in l][:2])
        cel = pagina.locator("input[type='number'][placeholder='Sense límit']")
        crit('…i el valor nou hi queda', cel.first.input_value() == '4',
             cel.first.input_value())

        cel.first.fill(str(a['numeral']))
        pagina.keyboard.press('Tab')
        pagina.wait_for_timeout(1800)
        crit('el banc queda com estava (numeral 2)',
             pagina.locator("input[type='number'][placeholder='Sense límit']")
             .first.input_value() == str(a['numeral']))

        # ── B · LA SAFATA: la volta desbordada, agrupada i marcada (FIT-12) ─────────────────
        print('\n── B · la safata agrupa i marca la volta ──')
        pagina.goto(f"{BASE}/comercial/albarans/{a['draft']}", wait_until='networkidle',
                    timeout=60000)
        pagina.wait_for_timeout(2000)
        pagina.screenshot(path=str(CAPTURES / 'm4_b1_albara_esborrany.png'), full_page=True)

        boto = pagina.get_by_role('button', name='Afegir ítems')
        crit('l\'albarà DRAFT ofereix obrir la safata', boto.count() >= 1, boto.count())
        boto.first.click()
        pagina.wait_for_timeout(2500)
        pagina.screenshot(path=str(CAPTURES / 'm4_b2_safata_per_volta.png'), full_page=True)
        # El modal té scroll propi (`maxHeight: 85vh`) i el bloc que interessa és a baix de tot.
        # Sense això la captura de lliurament talla la R3 rere la barra enganxada dels botons, i
        # el «perquè» —que és la meitat del que FIT-12 demana ensenyar— no hi surt mai.
        # `scroll_into_view_if_needed` NO en té prou: el xip ja hi és «visible» a mitges i
        # Playwright el dona per bo. El que cal és empènyer el CONTENIDOR del modal fins al
        # final, que és qui té l'`overflowY`.
        pagina.evaluate(
            "() => { const d = [...document.querySelectorAll('div')]"
            ".find(e => e.scrollHeight > e.clientHeight + 40 && e.clientHeight > 300);"
            " if (d) d.scrollTop = d.scrollHeight; }")
        pagina.wait_for_timeout(600)
        pagina.screenshot(path=str(CAPTURES / 'm4_b3_ronda_desbordada.png'))
        safata = pagina.inner_text('body')
        bolca('m4_safata', safata)

        crit('la safata s\'obre amb el bloc del model del banc', 'QA-M4-0001' in safata,
             [l for l in safata.splitlines() if 'QA-M4' in l][:3])
        crit('…i els ítems surten AGRUPATS PER VOLTA (R1 · R2 · R3)',
             all(f'R{n}' in safata for n in (1, 2, 3)),
             [l for l in safata.splitlines() if l.strip().startswith('R')][:6])
        crit('🚨 la R3 hi surt marcada FORA DE COMANDA',
             'fora de comanda' in safata.lower(),
             [l for l in safata.splitlines() if 'fora de comanda' in l.lower()][:2])
        crit('…amb el PERQUÈ sencer: el numeral passat i quina comanda el fixava',
             f"n>{a['numeral']}" in safata and a['comanda_num'] in safata,
             [l for l in safata.splitlines() if 'n>' in l][:2])
        # La data va en format de la casa (dd/mm/aaaa) i amb el LOCALE de l'app: un
        # `toLocaleDateString()` pelat pintava 8/25/2026 al Chromium headless.
        import re as _re
        dates = [l for l in safata.splitlines() if '→' in l and _re.search(r'\d{2}/\d{2}/\d{4}', l)]
        crit('…i amb les DATES de la volta (inici → fi, «oberta» si encara ho és), '
             'en format de la casa', 'oberta' in safata.lower() and len(dates) >= 3, dates[:3])
        crit('el model SENSE comanda hi és i NO porta cap marca de desbordament',
             'QA-M4-0002' in safata
             and safata.lower().count('fora de comanda') == 1,
             safata.lower().count('fora de comanda'))

        # 🔒 MESURAT PER DINS, no al `body` sencer: al body hi són tots dos models i la mesura
        # sortiria verda digués el que digués la caixa de cada un.
        bloc_sense = pagina.locator(
            "xpath=//div[contains(., 'QA-M4-0002') and not(.//div[contains(., 'QA-M4-0001')])]"
        ).last
        crit('🔒 el bloc del model sense comanda no diu «fora de comanda» per dins',
             'fora de comanda' not in bloc_sense.inner_text().lower(),
             bloc_sense.inner_text().replace('\n', ' · ')[:160])

        # ── C · LA CARA DEL TÈCNIC NO CANVIA (FIT-12) ──────────────────────────────────────
        print('\n── C · el Pla de treball del tècnic, intacte ──')
        pagina.keyboard.press('Escape')
        pagina.goto(f"{BASE}/models/{a['banc']['QA-M4-0001']}?tab=Dashboard",
                    wait_until='networkidle', timeout=60000)
        pagina.wait_for_timeout(2500)
        cos = pagina.inner_text('body')
        pagina.screenshot(path=str(CAPTURES / 'm4_c1_cara_tecnic.png'), full_page=True)
        bolca('m4_tecnic', cos)
        crit('la fitxa del model amb la volta desbordada no peta',
             not [e for e in errors if 'Minified React error' in e], errors[:1])
        crit('la R3 hi és, com una volta qualsevol', 'RONDA 3' in cos.upper()
             or 'R3' in cos, [l for l in cos.splitlines() if '3' in l][:3])
        crit('🚨 …i EN CAP LLOC hi diu res del desbordament',
             'fora de comanda' not in cos.lower() and 'numeral' not in cos.lower()
             and a['comanda_num'] not in cos,
             [l for l in cos.splitlines() if 'comanda' in l.lower()][:3])

        navegador.close()


if __name__ == '__main__':
    main()
    print(f'\n{len(ok)} OK · {len(ko)} FAIL')
    if ko:
        print('FALLEN: ' + ' | '.join(ko))
    sys.exit(1 if ko else 0)
