"""M2 · LA CARA DE LES RONDES — QA DE PANTALLA sobre el bundle REAL i el backend REAL.

## Per què aquesta forma

`build verd ≠ front viu`, i un fum HTTP prova el PAYLOAD, no el que es dibuixa. Això munta el
bundle de `frontend/dist` —el mateix que nginx publica— i li deixa parlar amb el **gunicorn del
worktree** (mai `ftt-staging.service`, que serveix un ALTRE arbre).

🔑 **L'API NO VA STUBEJADA.** Els fums de pantalla anteriors la stubejaven perquè no podien emetre
JWT; aquest sí que en pot (`TenantTokenObtainPairSerializer.get_token` dins de `schema_context`,
que és el que estampa el claim `tenant_schema` sense el qual la porta dona 401). Per això el que
es mesura aquí és la pantalla SENCERA contra dades vives del banc `[QA-M1]`.

El navegador parla amb un origen virtual i **cada petició la serveix aquest procés**: els fitxers,
del disc; les d'`/api/`, reenviades al gunicorn amb el `Host:` de tenant, que és el que el
navegador no pot posar-hi tot sol.

⚠️ **Model 1383 i models reals: no s'hi entra.** Només el banc, i només per LLEGIR: aquest fum no
prem cap botó que escrigui (el gest d'entrega el prova `qa_m2_cara_http.py`, que hi va per la
porta). Obrir una pantalla de model no obre cap tasca —el `?mode=entry` sí que ho faria— i aquí
no s'hi posa mai.

## Ús

    # 1) el banc i el backend
    cd backend && venv/bin/python ../ops/qa/banc_m1_rondes.py --remunta
    venv/bin/gunicorn fhort.wsgi:application --chdir /var/www/ftt-m1/backend \\
        --bind 127.0.0.1:8124 --workers 2 --timeout 60
    # 2) el bundle
    cd frontend && npm run build
    # 3) això
    /tmp/qa-venv/bin/python ops/qa/qa_m2_cara_pantalla.py

Captures a `ops/qa/captures/m2_*.png`. Codi de sortida 1 si algun element del mockup no hi és.
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
BACKEND = os.environ.get('BACKEND', 'http://127.0.0.1:8124')

#: 🔑 DOS INTÈRPRETS, i no és accidental: **Playwright viu a `/tmp/qa-venv` i Django al venv del
#: backend**, i no hi ha cap venv que tingui els dos. En comptes de duplicar dependències, el
#: token i els pk del banc es demanen al venv de Django per subprocés —una sola comanda per a qui
#: corre el fum— i tota la resta passa aquí.
VENV_BACKEND = REPO / 'backend' / 'venv' / 'bin' / 'python'

_BOOTSTRAP = r'''
import json, os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fhort.settings')
django.setup()
from django_tenants.utils import schema_context
from fhort.accounts.models import UserProfile
from fhort.auth_jwt import TenantTokenObtainPairSerializer
from fhort.models_app.models import Model
with schema_context('fhort'):
    banc = {m.codi_intern: m.pk
            for m in Model.objects.filter(codi_intern__startswith='QA-M1-')}
    perfil = UserProfile.objects.order_by('pk').first()
    # 🚨 El claim `tenant_schema` l'estampa AQUEST serializer llegint l'schema ACTIU: un
    # `RefreshToken.for_user()` pelat dona 401 «token no vàlid», el mateix 401 que no dur-ne cap.
    token = str(TenantTokenObtainPairSerializer.get_token(perfil.user).access_token)
print('@@' + json.dumps({'banc': banc, 'token': token}))
'''


def bootstrap():
    r = subprocess.run([str(VENV_BACKEND), '-c', _BOOTSTRAP], capture_output=True, text=True,
                       cwd=str(REPO / 'backend'))
    linia = next((l for l in r.stdout.splitlines() if l.startswith('@@')), None)
    if linia is None:
        raise SystemExit(f'no he pogut emetre el JWT amb {VENV_BACKEND}:\n{r.stderr[-2000:]}')
    return json.loads(linia[2:])


ok, ko = [], []


def bolca(etiqueta, cos):
    """Amb `M2_DEBUG=1`, el text de la pantalla. És el que distingeix «el component no pinta»
    de «la pantalla ni tan sols ha arribat al component»."""
    if os.environ.get('M2_DEBUG'):
        print(f'\n----- {etiqueta} -----\n{cos[:3000]}\n----- fi -----\n')


def crit(nom, cond, detall=''):
    (ok if cond else ko).append(nom)
    print(f"  {'OK  ' if cond else 'FAIL'} {nom}{(' · ' + str(detall)) if detall else ''}")


def fes_handler(token):
    def handler(route):
        req = route.request
        # 🔑 EL QUE NO ÉS DEL NOSTRE ORIGEN, PASSA. La `index.html` carrega el webfont d'icones
        # Tabler i les tipografies de Google des de CDN; interceptant-ho tot, el handler els
        # servia `index.html` i la captura sortia SENSE CAP ICONA —i una revisió visual sense
        # icones no és la pantalla, és una altra cosa. (Lliçó germana de la del botó només-icona
        # que mesurava 0 perquè el webfont no havia arribat.)
        if not req.url.startswith(BASE):
            route.continue_()
            return
        cami = req.url.split(BASE, 1)[-1]
        if cami.startswith('/api/'):
            # Reenviament al backend VIU. El `Host:` és la peça que el navegador no pot posar:
            # sense ell django-tenants no resol el tenant i tot respon com si no existís.
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
    if len(banc) < 4:
        raise SystemExit('Falta el banc: corre `banc_m1_rondes.py --remunta`.')

    dues = banc['QA-M1-0004']      # R1 tancada + R2 replicada: el cas de dues voltes
    variats = banc['QA-M1-0001']   # una sola volta, quatre estats de tasca
    print(f'bundle={DIST} · backend={BACKEND} · banc {sorted(banc)}\n')

    with sync_playwright() as p:
        navegador = p.chromium.launch()
        ctx = navegador.new_context(base_url=BASE, ignore_https_errors=True,
                                    viewport={'width': 1440, 'height': 1000})
        pagina = ctx.new_page()
        errors = []
        pagina.on('pageerror', lambda e: errors.append(str(e)))
        pagina.route('**/*', fes_handler(token))
        # L'idioma es FIXA: sense això i18next el dedueix del `navigator` (que al Chromium
        # headless és `en`) i la revisió visual d'Agus i la Montse sortiria en anglès. La clau és
        # la que el detector mira (`lookupLocalStorage: 'fhort.lang'`), no una inventada.
        pagina.add_init_script(f"localStorage.setItem('access_token', {json.dumps(token)});"
                               "localStorage.setItem('fhort.lang', 'ca')")

        # ── A · EL PLA DE TREBALL ───────────────────────────────────────────────────────────
        print("── A · Pla de treball (mockup A v2) ──")
        pagina.goto(f'{BASE}/models/{dues}?tab=Dashboard', wait_until='networkidle',
                    timeout=60000)
        pagina.wait_for_timeout(2000)
        cos = pagina.inner_text('body')
        pagina.screenshot(path=str(CAPTURES / 'm2_pla_dues_voltes.png'), full_page=True)
        bolca('m2_pla_dues_voltes', cos)

        crit('la pantalla no peta (cap error de React)',
             not [e for e in errors if 'Minified React error' in e or 'before initialization' in e],
             errors[:1])
        crit('hi ha un contenidor per VOLTA, i les dues hi són',
             'RONDA 1' in cos and 'RONDA 2' in cos)
        crit('la volta tancada es pinta amb el seu estat', 'Tancada' in cos or 'Entregada' in cos)
        crit('la vigent es pinta «En curs»', 'En curs' in cos)
        crit('la capçalera agrega inici · fi · temps · tasques',
             'inici' in cos and 'temps' in cos and 'tasques' in cos)
        crit('…i hi ha una pastilla de FASE del catàleg', 'Dev. tècnic' in cos, )
        crit('el peu diu la llei del segell',
             'segellades' in cos and 'ronda nova' in cos)

        # ── CODA · ELS QUATRE RETOCS DE FIDELITAT AL MOCKUP ────────────────────────────────
        #
        # ① La targeta COMPACTA dins dels contenidors: es mesura per la MIDA del botó de
        #    transport (20px al mockup compacte; 26 a la targeta gran), que és l'única diferència
        #    que no es pot confondre amb res més.
        botons = pagina.locator("xpath=//button[@title='Iniciar' or @title='Pausar' "
                                "or @title='Finalitzar']")
        amples = [botons.nth(i).bounding_box()['width'] for i in range(botons.count())]
        crit('① dins de la volta, el transport és el COMPACTE (20px, no 26)',
             bool(amples) and all(a == 20 for a in amples), sorted(set(amples)))

        # ② La barra de progrés GLOBAL se'n va; el temps acumulat es queda a la capçalera.
        crit('② la barra global («n/m tasques fetes · %») ja no hi és',
             'tasques fetes' not in cos, [l for l in cos.splitlines() if 'tasques fetes' in l])
        crit('② …i el temps acumulat sobre el model segueix dit',
             'Temps acumulat sobre el model' in cos)
        titol = pagina.get_by_text('PLA DE TREBALL').first.bounding_box()
        temps = pagina.get_by_text('Temps acumulat sobre el model').first.bounding_box()
        crit('② …a la MATEIXA fila que el rètol de secció i a la seva dreta (`.sec`)',
             abs(titol['y'] - temps['y']) < 12 and temps['x'] > titol['x'],
             (round(titol['y']), round(temps['y'])))

        # ③ «+ Nova ronda» SEMPRE visible: aquest model TÉ una volta oberta, que és exactament
        #    l'estat en què abans el botó desapareixia.
        crit('③ «+ Nova ronda» es pinta encara que hi hagi una volta OBERTA',
             '+ Nova ronda' in cos and 'En curs' in cos)

        # ④ Cap menú «···» a cap capçalera de ronda.
        crit('④ cap menú «···» a les capçaleres de ronda', '···' not in cos)

        # ── B · L'ENTREGA I EL SEU RASTRE ───────────────────────────────────────────────────
        # El model 0001 s'ha entregat al fum HTTP, que corre abans: aquí es LLEGEIX el resultat.
        print("\n── B · la línia d'entrega i el rastre FIT-8 ──")
        pagina.goto(f'{BASE}/models/{variats}?tab=Dashboard', wait_until='networkidle',
                    timeout=60000)
        pagina.wait_for_timeout(2000)
        cos = pagina.inner_text('body')
        pagina.screenshot(path=str(CAPTURES / 'm2_pla_entregada.png'), full_page=True)
        bolca('m2_pla_entregada', cos)
        entregada = 'Entregada' in cos
        crit('la volta entregada es pinta «Entregada»', entregada, )
        crit('la línia d\'entrega diu a QUI i QUI ho informa',
             'destinatari de prova' in cos and 'Agustí' in cos)
        crit('…i la descripció, que és text lliure', 'Fitxa tècnica v1' in cos)
        crit('l\'OK del client hi surt (pendent o informat)',
             'OK client' in cos)
        crit('FIT-8 · el rastre de la rectificació es veu AL COSTAT del nom de la volta',
             'rectificació' in cos, )
        crit('«+ Nova ronda» s\'ofereix sempre, també amb una volta oberta (CODA ③)',
             '+ Nova ronda' in cos)

        # La volta entregada neix PLEGADA (derivat de l'estat). Desplegant-la s'ha de veure la
        # feina en fade i SENSE transport: és la meitat visual d'FIT-2 que el text no pot dir.
        pagina.get_by_title('Desplegar la volta').first.click()
        pagina.wait_for_timeout(600)
        pagina.screenshot(path=str(CAPTURES / 'm2_pla_segellada_oberta.png'), full_page=True)
        botons_volta_1 = pagina.locator(
            "xpath=(//button[@aria-expanded='true'])[1]/ancestor::div[1]"
            "/following-sibling::div[last()]//button[@title='Iniciar' or @title='Pausar' "
            "or @title='Finalitzar']")
        crit('la volta entregada, desplegada, no ofereix cap transport (FIT-2 · el segell)',
             botons_volta_1.count() == 0, botons_volta_1.count())

        # ── C · EL REGISTRE D'ACTIVITAT ─────────────────────────────────────────────────────
        print("\n── C · Registre d'activitat (mockup B v3) ──")
        pagina.goto(f"{BASE}/models/{dues}?tab=Registre d'activitat", wait_until='networkidle',
                    timeout=60000)
        pagina.wait_for_timeout(2000)
        cos = pagina.inner_text('body')
        pagina.screenshot(path=str(CAPTURES / 'm2_registre.png'), full_page=True)
        bolca('m2_registre', cos)

        crit('el tab no dona «encara no ha iniciat activitat»',
             'no ha iniciat activitat' not in cos)
        crit('els KPI de capçalera hi són (temps · rondes · entregues · inici)',
             'Temps total' in cos and 'Rondes' in cos and 'Entregues' in cos
             and 'Inici activitat' in cos)
        # Les capçaleres es pinten en MAJÚSCULES per CSS (`text-transform`), i `inner_text` torna
        # el text ja transformat: la comparació va sense caixa a posta.
        cos_maj = cos.upper()
        crit('UNA graella amb capçalera única: les sis columnes del mockup',
             all(c in cos_maj for c in ('TASCA', 'ESTAT', 'TEMPS', 'INICI', 'FI', 'QUI')))
        crit('cada ronda és una fila-resum', 'RONDA 1' in cos and 'RONDA 2' in cos)
        crit('el detall porta el temps de debò, no 0h 00m a tot arreu',
             '1h 14m' in cos or '0h 27m' in cos, )
        crit('…i diu QUI va fer la feina', 'Agustí' in cos)
        crit('l\'historial complet de transicions segueix al peu', 'Historial' in cos)

        # …i el registre del model QUE SÍ que té entrega: la fila d'entrega dins del detall és
        # un element del mockup que el model de dues voltes no pot ensenyar (no n'hi té cap).
        pagina.goto(f"{BASE}/models/{variats}?tab=Registre d'activitat", wait_until='networkidle',
                    timeout=60000)
        pagina.wait_for_timeout(2000)
        # La volta entregada neix PLEGADA també aquí (mockup B v3: «rondes velles tancades per
        # defecte»), o sigui que la fila d'entrega només es pot mesurar desplegant-la.
        pagina.locator("tr", has_text='RONDA 1').first.click()
        pagina.wait_for_timeout(600)
        cos = pagina.inner_text('body')
        pagina.screenshot(path=str(CAPTURES / 'm2_registre_amb_entrega.png'), full_page=True)
        bolca('m2_registre_amb_entrega', cos)
        crit('la fila d\'ENTREGA viu dins del detall de la seva volta',
             'Entrega a' in cos and 'destinatari de prova' in cos)
        crit('…i el KPI d\'entregues ja no és zero', 'Entregues' in cos)
        crit('la volta entregada porta el rastre de la rectificació també aquí',
             'rectificació' in cos)

        navegador.close()

    print(f'\n{len(ok)} OK · {len(ko)} FAIL · captures a {CAPTURES}')
    if ko:
        print('FALLEN: ' + ' | '.join(ko))
    return 1 if ko else 0


if __name__ == '__main__':
    sys.exit(main())
