"""M3 · EL CICLE DE VIDA DEL MODEL — QA DE PANTALLA sobre el bundle REAL i el backend REAL.

`build verd ≠ front viu`, i el fum HTTP prova el PAYLOAD, no el que es dibuixa. Això munta el
bundle de `frontend/dist` i el fa parlar amb el **gunicorn del worktree** (mai
`ftt-staging.service`, que serveix un ALTRE arbre). Mateixa forma que `qa_m2_cara_pantalla.py`.

🚨 **EL FLUX ESTRELLA ES PREM DE DEBÒ**: obrir «Accions», triar «Tancar model», rebre l'avís de
la volta oberta, escriure el destinatari i confirmar. És l'única manera de veure que el 409
arriba a la pantalla com una PREGUNTA i no com un toast d'error vermell.

⚠️ **AQUEST FUM ESCRIU**, i només sobre el banc `[QA-M1]`. **Mai el 1383, mai un model real.**
Consumeix la volta oberta del `QA-M1-0004`: remunta el banc abans de tornar-hi.

    cd backend && venv/bin/python ../ops/qa/banc_m1_rondes.py --remunta
    setsid nohup venv/bin/gunicorn fhort.wsgi:application \\
        --chdir /var/www/ftt-m3cv/backend --bind 127.0.0.1:8131 --workers 2 --timeout 60 &
    cd frontend && npm run build
    /tmp/qa-venv/bin/python ops/qa/qa_m3_cicle_pantalla.py

Captures a `ops/qa/captures/m3_*.png`. Codi de sortida 1 si alguna mesura falla.
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
BACKEND = os.environ.get('BACKEND', 'http://127.0.0.1:8131')

#: 🔑 DOS INTÈRPRETS: Playwright viu a `/tmp/qa-venv` i Django al venv del backend. El token i
#: els pk del banc es demanen al venv de Django per subprocés (lliçó d'M2).
VENV_BACKEND = REPO / 'backend' / 'venv' / 'bin' / 'python'

_BOOTSTRAP = r'''
import json, os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fhort.settings')
django.setup()
from django.utils import timezone
from django_tenants.utils import schema_context
from fhort.accounts.models import UserProfile
from fhort.auth_jwt import TenantTokenObtainPairSerializer
from fhort.models_app.models import Model
from fhort.tasks.models import ModelTask
with schema_context('fhort'):
    banc = {m.codi_intern: m.pk
            for m in Model.objects.filter(codi_intern__startswith='QA-M1-')}
    # PRECONDICIÓ C4a del board: «només els PLANIFICATS hi existeixen». El banc fabrica la feina
    # pels gestos de treball, que no planifiquen: sense això, cap model del banc entra al board
    # i les mesures del board sortirien verdes sense mesurar res.
    ModelTask.objects.filter(model_id__in=list(banc.values()),
                             planned_start__isnull=True).update(planned_start=timezone.now())
    perfil = UserProfile.objects.order_by('pk').first()
    # 🚨 El claim `tenant_schema` l'estampa AQUEST serializer llegint l'schema ACTIU.
    token = str(TenantTokenObtainPairSerializer.get_token(perfil.user).access_token)
print('@@' + json.dumps({'banc': banc, 'token': token}))
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
    if os.environ.get('M3_DEBUG'):
        print(f'\n----- {etiqueta} -----\n{cos[:3000]}\n----- fi -----\n')


def crit(nom, cond, detall=''):
    (ok if cond else ko).append(nom)
    print(f"  {'OK  ' if cond else 'FAIL'} {nom}{(' · ' + str(detall)) if detall else ''}")


def crida_api(cami, *, token, cos=None):
    """Una crida DIRECTA al backend, fora del navegador. La fa servir la mesura de la 4a
    columna per executar l'ACTE d'entrega entre dues lectures de la pantalla: el gest té porta
    pròpia a la fitxa (M2) i pitjar-lo aquí hauria mesurat aquell diàleg, no la columna."""
    dades = json.dumps(cos).encode() if cos is not None else None
    r = urllib.request.Request(BACKEND + cami, data=dades,
                               method='POST' if cos is not None else 'GET')
    r.add_header('Host', 'staging.fhorttextile.tech')
    r.add_header('Content-Type', 'application/json')
    r.add_header('Authorization', 'Bearer ' + token)
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            return json.loads(resp.read() or b'null')
    except urllib.error.HTTPError as e:
        return json.loads(e.read() or b'null')


def fes_handler(token):
    def handler(route):
        req = route.request
        # El que no és del nostre origen, PASSA: el webfont d'icones i les tipografies vénen de
        # CDN i, interceptant-ho tot, la captura sortiria sense cap icona (lliçó d'M2).
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

    arrencada = bootstrap()
    banc, token = arrencada['banc'], arrencada['token']
    if 'QA-M1-0004' not in banc:
        raise SystemExit('Falta el banc: corre `banc_m1_rondes.py --remunta`.')
    amb_volta = banc['QA-M1-0004']     # R1 tancada + R2 OBERTA → el flux estrella
    del_cataleg = banc['QA-M1-0001']   # R1 OBERTA amb feina viva → la via del catàleg (CODA)
    tot_fet = banc['QA-M1-0002']       # tot Done amb la volta OBERTA → el cas de la captura D1
    print(f'bundle={DIST} · backend={BACKEND} · banc {sorted(banc)}\n')

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

        # ── A · EL FLUX ESTRELLA: tancar un model AMB LA VOLTA OBERTA ───────────────────────
        print('── A · tancar model amb ronda oberta (FIT-10) ──')
        pagina.goto(f'{BASE}/models/{amb_volta}?tab=Dashboard', wait_until='networkidle',
                    timeout=60000)
        pagina.wait_for_timeout(2000)
        crit('la pantalla no peta (cap error de React)',
             not [e for e in errors if 'Minified React error' in e
                  or 'before initialization' in e], errors[:1])

        pagina.get_by_role('button', name='Accions').first.click()
        pagina.wait_for_timeout(400)
        pagina.screenshot(path=str(CAPTURES / 'm3_a1_menu_accions.png'))
        menu = pagina.inner_text('body')
        bolca('m3_menu', menu)
        crit('el menú Accions ofereix «Tancar model»', 'Tancar model' in menu)
        crit('…i NO ofereix «Reobrir» ni «Jubilar» en un model obert',
             'Reobrir model' not in menu and 'Jubilar model' not in menu)

        pagina.get_by_text('Tancar model').first.click()
        pagina.wait_for_timeout(600)
        pagina.screenshot(path=str(CAPTURES / 'm3_a2_dialeg_motiu.png'))
        dialeg = pagina.inner_text('body')
        crit('el diàleg demana el MOTIU, amb les dues vies d\'FIT-10',
             'Acabat (decisió interna)' in dialeg and 'Tret de catàleg' in dialeg)
        crit('…i encara no demana res d\'entrega', 'Destinatari' not in dialeg)

        # 🚨 Primera confirmació: el servidor ha de respondre 409 i la pantalla ha de convertir-lo
        # en una PREGUNTA, no en un toast vermell.
        pagina.get_by_role('button', name='Tancar', exact=True).first.click()
        pagina.wait_for_timeout(1500)
        pagina.screenshot(path=str(CAPTURES / 'm3_a3_avis_ronda_oberta.png'))
        avis = pagina.inner_text('body')
        bolca('m3_avis', avis)
        crit('🚨 el 409 arriba com a PREGUNTA i diu QUINA volta és',
             'R2 està oberta' in avis, [l for l in avis.splitlines() if 'oberta' in l][:2])
        # ⚠️ La comparació va SENSE CAIXA: el rètol del camp el pinta el CSS en MAJÚSCULES
        # (`Row`, `text-transform`) i `inner_text` torna el text ja transformat — el mateix
        # parany que va fer mentir el fum d'M2 amb les capçaleres de columna.
        avis_min = avis.lower()
        crit('…i el diàleg passa a demanar el destinatari de l\'entrega',
             'destinatari' in avis_min and "confirmar l'entrega i tancar" in avis_min)
        crit('…amb el model encara OBERT (res s\'ha tocat)', 'Acabat' not in
             pagina.inner_text('header') if pagina.locator('header').count() else True)

        pagina.locator('input[type="text"], input:not([type])').last.fill('QA · Brumà SL')
        pagina.wait_for_timeout(200)
        pagina.get_by_role('button', name="Confirmar l'entrega i tancar").first.click()
        pagina.wait_for_timeout(2500)
        pagina.screenshot(path=str(CAPTURES / 'm3_a4_tancat.png'), full_page=True)

        # ── B · LA FITXA D'UN MODEL ACABAT ─────────────────────────────────────────────────
        print('\n── B · la fitxa del model ACABAT ──')
        pagina.goto(f'{BASE}/models/{amb_volta}?tab=Dashboard', wait_until='networkidle',
                    timeout=60000)
        pagina.wait_for_timeout(2500)
        cos = pagina.inner_text('body')
        pagina.screenshot(path=str(CAPTURES / 'm3_b1_fitxa_acabada.png'), full_page=True)
        bolca('m3_fitxa_acabada', cos)
        crit('el BANNER d\'estat hi és i diu el motiu', 'Acabat' in cos
             and 'decisió interna' in cos.lower() or 'aquest model es consulta' in cos.lower())
        crit('…i diu que per treballar-hi cal reobrir', 'reobre' in cos.lower())
        transport = pagina.locator("xpath=//button[@title='Iniciar' or @title='Pausar' "
                                   "or @title='Finalitzar']")
        crit('el TRANSPORT de les tasques se\'n va (no s\'apaga: desapareix)',
             transport.count() == 0, transport.count())
        crit('…i «+ Nova ronda» tampoc s\'ofereix', '+ Nova ronda' not in cos)
        crit('la volta i la seva feina segueixen CONSULTABLES', 'RONDA 2' in cos.upper())

        pagina.get_by_role('button', name='Accions').first.click()
        pagina.wait_for_timeout(400)
        menu = pagina.inner_text('body')
        pagina.screenshot(path=str(CAPTURES / 'm3_b2_menu_acabat.png'))
        crit('el menú ara ofereix «Jubilar» i «Reobrir», i no «Tancar»',
             'Jubilar model' in menu and 'Reobrir model' in menu
             and 'Tancar model' not in menu)
        pagina.keyboard.press('Escape')

        # ── B-bis · LA VIA DEL CATÀLEG: tancar SENSE entregar (CODA) ───────────────────────
        print('\n── B-bis · tret de catàleg: es tanca sense declarar cap entrega ──')
        pagina.goto(f'{BASE}/models/{del_cataleg}?tab=Dashboard', wait_until='networkidle',
                    timeout=60000)
        pagina.wait_for_timeout(2000)
        pagina.get_by_role('button', name='Accions').first.click()
        pagina.wait_for_timeout(400)
        pagina.get_by_text('Tancar model').first.click()
        pagina.wait_for_timeout(600)
        # ⚠️ El selector va per l'OPCIÓ i no per `select` a seques: la pàgina en té dos (el
        # d'idioma de la barra és el primer del DOM) i Playwright agafava aquell.
        pagina.select_option("select:has(option[value='tret_de_cataleg'])", 'tret_de_cataleg')
        pagina.wait_for_timeout(200)
        pagina.get_by_role('button', name='Tancar', exact=True).first.click()
        pagina.wait_for_timeout(1800)
        pagina.screenshot(path=str(CAPTURES / 'm3_b3_avis_tret_de_cataleg.png'))
        avis = pagina.inner_text('body')
        avis_min = avis.lower()
        bolca('m3_avis_tret', avis)
        crit('🔒 l\'avís de la via del catàleg diu que NO es declararà cap entrega',
             'sense declarar cap entrega' in avis_min,
             [l for l in avis.splitlines() if 'entrega' in l.lower()][:2])
        crit('…i NO demana destinatari (no s\'envia res a ningú)', 'destinatari' not in avis_min)
        pagina.get_by_role('button', name='Tancar la volta i el model').first.click()
        pagina.wait_for_timeout(2500)
        pagina.goto(f'{BASE}/models/{del_cataleg}?tab=Dashboard', wait_until='networkidle',
                    timeout=60000)
        pagina.wait_for_timeout(2500)
        cos = pagina.inner_text('body')
        pagina.screenshot(path=str(CAPTURES / 'm3_b4_tret_de_cataleg_tancat.png'), full_page=True)
        crit('el model queda ACABAT i el banner ho diu amb el motiu del client',
             'Tret de catàleg' in cos, [l for l in cos.splitlines() if 'catàleg' in l][:2])
        crit('…la volta hi és TANCADA i sense cap línia d\'entrega',
             'Tancada' in cos and 'Entrega ' not in cos,
             [l for l in cos.splitlines() if 'Entrega' in l][:2])

        # ── C · LA LLISTA: tres vistes, tres filtres exactes ───────────────────────────────
        print('\n── C · les vistes de /models ──')
        pagina.goto(f'{BASE}/models?vista=acabats', wait_until='networkidle', timeout=60000)
        pagina.wait_for_timeout(2500)
        cos = pagina.inner_text('body')
        pagina.screenshot(path=str(CAPTURES / 'm3_c1_llista_acabats.png'), full_page=True)
        bolca('m3_llista_acabats', cos)
        crit('la vista «acabats» ja NO és un buit amb el motiu escrit',
             'QA-M1-0004' in cos, [l for l in cos.splitlines() if 'QA-M1' in l][:3])

        pagina.goto(f'{BASE}/models', wait_until='networkidle', timeout=60000)
        pagina.wait_for_timeout(2500)
        cos = pagina.inner_text('body')
        pagina.screenshot(path=str(CAPTURES / 'm3_c2_llista_curs.png'), full_page=True)
        crit('…i la vista per defecte ja no l\'ensenya', 'QA-M1-0004' not in cos)
        crit('els altres models del banc hi segueixen', 'QA-M1-0002' in cos)

        # ── D · EL BOARD ───────────────────────────────────────────────────────────────────
        print('\n── D · el board del Dashboard (FASE 4) ──')
        pagina.goto(f'{BASE}/', wait_until='networkidle', timeout=60000)
        pagina.wait_for_timeout(3000)
        cos = pagina.inner_text('body')
        pagina.screenshot(path=str(CAPTURES / 'm3_d1_board.png'), full_page=True)
        bolca('m3_board', cos)
        crit('la 4a columna es diu «Entregats»', 'Entregats' in cos)
        crit('el model ACABAT ha sortit del board', 'QA-M1-0004' not in cos)
        crit('i les targetes porten el xip de la darrera volta',
             'volta oberta' in cos or 'entregada' in cos or 'tancada' in cos,
             [l for l in cos.splitlines() if l.strip().startswith('R')][:3])

        # 🔒 CODA — LA COLUMNA, MESURADA PER DINS. `QA-M1-0002` és el cas de la captura D1: tot
        # Done amb la volta OBERTA. Abans queia a «Entregats»; ara ha de ser a una columna de
        # feina. Es mira DINS del contenidor de cada columna i no al `body` sencer: al body hi
        # són tots i la mesura sortiria verda digués el que digués.
        def columna(nom):
            return pagina.locator(
                f"xpath=//span[normalize-space()='{nom}']/ancestor::div[2]").first.inner_text()
        entregats, pendents = columna('Entregats'), columna('Pendents')
        crit('🔒 tot Done amb la volta OBERTA ja NO és a «Entregats»',
             'QA-M1-0002' not in entregats, entregats.replace('\n', ' · ')[:160])
        crit('…i sí que és a una columna de FEINA, amb el xip que ho explica',
             'QA-M1-0002' in pendents and 'volta oberta' in pendents,
             pendents.replace('\n', ' · ')[:160])

        # 🔒 …I ARA L'ACTE. El MATEIX model, abans i després d'informar l'entrega: si la columna
        # fos un recompte de tasques no es mouria (els comptadors no canvien —ja era tot Done—),
        # i es mou. És la mesura que diu que la 4a columna és un FET i no una aritmètica.
        r = crida_api(f'/api/v1/models/{tot_fet}/rondes/', token=token)
        oberta = next((x for x in r if x.get('tancada_el') is None), None)
        crit('el model de la mesura arriba amb la volta oberta', oberta is not None)
        crida_api(f"/api/v1/rondes/{oberta['id']}/entrega/", token=token,
                  cos={'destinatari': 'QA · pantalla', 'descripcio': 'mesura de la 4a columna'})
        pagina.goto(f'{BASE}/', wait_until='networkidle', timeout=60000)
        pagina.wait_for_timeout(3000)
        pagina.screenshot(path=str(CAPTURES / 'm3_d2_board_entregat.png'), full_page=True)
        entregats = columna('Entregats')
        crit('🔒 en informar l\'ENTREGA, el mateix model passa a «Entregats»',
             'QA-M1-0002' in entregats and 'entregada' in entregats,
             entregats.replace('\n', ' · ')[:160])

        navegador.close()

    print(f'\n{len(ok)} OK · {len(ko)} FAIL · captures a {CAPTURES}')
    if ko:
        print('FALLEN: ' + ', '.join(ko))
    return 1 if ko else 0


if __name__ == '__main__':
    raise SystemExit(main())
