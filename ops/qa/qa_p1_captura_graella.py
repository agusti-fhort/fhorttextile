"""CAPTURA · P1 · LA GRAELLA DEL PAS 3, CONTRA EL SERVEI VIU (bundle desplegat + gunicorn).

Què ha de demostrar la foto: que **el 100% actual segueix intacte** després de canviar la clau
de fila de la graella. No pot ensenyar la Brumà —tres files del mateix POM— perquè el pas 2
encara no ofereix el columnat d'instància: això és P2, i fins llavors la UI no pot arribar-hi
(la porta és oberta per API, no per pantalla). Fotografiar-ho amb un muntatge seria ensenyar
una cosa que la persona no pot fer.

Es fotografia el camí de sempre, i el gest que el canvi de `key` posava en risc: **teclejar
una cel·la**. Si la clau no fos estable, React desmuntaria l'input i el número no hi quedaria.

Dues fases perquè els mòduls viuen a venvs diferents (playwright a `/tmp/qa-venv`, Django al
venv del backend):

    cd backend && ./venv/bin/python ../ops/qa/qa_p1_captura_graella.py --prepara
    /tmp/qa-venv/bin/python ops/qa/qa_p1_captura_graella.py

⚠️ ESCRIU UNA `ImportSession` I PUJA UN FITXER A MEDIA, i prou: la passejada s'atura al pas 3 i
NO confirma mai, o sigui que cap `BaseMeasurement` del model 1320 es toca. La sessió queda com
a runa de wizard, que és exactament el que hi deixa una persona que tanca el modal a mig camí.

⚠️ Les icones surten buides a la captura (Tabler entra per webfont d'un CDN i aquí es
serveix tot des del disc). Al navegador de debò hi són.
"""
import json
import mimetypes
import os
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
OUT = pathlib.Path(__file__).resolve().parent / 'captures'
ESTAT = pathlib.Path('/tmp/qa_p1_captura.json')
XLSX = pathlib.Path('/tmp/qa_p1_bruma.xlsx')
#: El model de la CAPTURA: `BRW-FW27-0001` «BRUMA», verge (0 mesures). Es tria verge a posta:
#: amb mesures, el tab Mesures entra en CONSULTA i l'única porta cap a l'import és «Mesurar
#: prenda», que és un GEST (obre la tasca i li engega el rellotge). Una captura no ha de moure
#: el domini de ningú. Verge, la pantalla ensenya la gènesi i la porta hi és sense cap gest.
MODEL_ID = int(os.environ.get('FTT_QA_MODEL', '1323'))
#: D'on surten els CODIS del document: un model amb taula viva del mateix tenant. Els POMMaster
#: són del tenant, no del model, o sigui que el pas 2 els aparella igual.
MODEL_CODIS = int(os.environ.get('FTT_QA_MODEL_CODIS', '1320'))
BASE = 'https://staging.fhorttextile.tech'
VIU = 'http://127.0.0.1:8001'
HOST_TENANT = os.environ.get('FTT_QA_HOST', 'fhorttextile.tech')
#: QUIN CAS ES FOTOGRAFIA. `normal` = el camí de sempre (P1: el 100% actual, intacte).
#: `bruma` = tres files del MATEIX POM en tres instàncies (P2+P3: el cas real que ho motiva
#: tot). El segon només és assolible des que el pas 2 ofereix el columnat d'instància.
CAS = os.environ.get('FTT_QA_CAS', 'normal')


# ══════════════════ FASE 1 · el document i el token (venv del backend) ══════════════════
def prepara():
    sys.path.insert(0, str(REPO / 'backend'))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fhort.settings')
    import django
    django.setup()
    from django.contrib.auth import get_user_model
    from django_tenants.utils import schema_context
    from rest_framework_simplejwt.tokens import AccessToken
    from openpyxl import Workbook

    with schema_context('fhort'):
        from fhort.models_app.models import BaseMeasurement, Model
        model = Model.objects.get(id=MODEL_ID)
        run = [s.strip() for s in (model.size_run_model or '').replace(';', '·').split('·')
               if s.strip()]
        font = Model.objects.get(id=MODEL_CODIS)
        # Codis REALS del model: així el pas 2 els aparella sol i la graella surt plena. Un
        # document inventat deixaria totes les files sense match i la foto no ensenyaria res.
        vives = (BaseMeasurement.objects.filter(model=font, garment='', is_active=True)
                 .select_related('pom').order_by('ordre')[:6])
        codis = [(bm.pom.codi_client or '', bm.pom.nom_client or '', float(bm.base_value_cm or 0))
                 for bm in vives]
        if CAS == 'bruma':
            # LA FITXA DE LA BRUMÀ, amb un codi REAL del catàleg: tres files que parlen del
            # MATEIX POM —«at the top», «at the bottom», «stretched out»— amb 30, 31 i 40. La
            # primera s'aparella sola; les altres dues les resol la persona, que és el gest.
            base_codi = codis[0][0]
            codis = [(base_codi, 'at the top', 30.0),
                     (f'{base_codi}{base_codi}', 'at the bottom', 31.0),
                     (f'{base_codi}1', 'stretched out', 40.0)]
        user = get_user_model().objects.filter(profile__isnull=False).order_by('id').first()
        # ⚠️ EL TOKEN VA SEGELLAT AMB L'SCHEMA (`fhort/auth_jwt.py`): un `AccessToken.for_user`
        # pelat no porta el claim `tenant_schema`, i `TenantJWTAuthentication` el rebutja →
        # la SPA cau a la pantalla de login i la captura seria del formulari d'entrar.
        from fhort.auth_jwt import TENANT_CLAIM
        from django.db import connection
        _t = AccessToken.for_user(user)
        _t[TENANT_CLAIM] = connection.schema_name
        token = str(_t)

    wb = Workbook()
    ws = wb.active
    ws.append(['POM', 'DESCRIPTION'] + run)
    i_base = run.index(model.base_size_label) if model.base_size_label in run else 0
    for codi, nom, valor in codis:
        ws.append([codi, nom] + [round(valor + (i - i_base) * 1.0, 1) for i in range(len(run))])
    wb.save(XLSX)

    ESTAT.write_text(json.dumps({'token': token, 'xlsx': str(XLSX), 'run': run, 'cas': CAS,
                                 'base': model.base_size_label, 'codis': [c[0] for c in codis]}))
    print(f'✓ document {XLSX} · {len(codis)} files · run={run} base={model.base_size_label!r}')
    print(f'✓ estat a {ESTAT} (conté un token; és /tmp i no es commita)')


# ══════════════════ FASE 2 · la passejada (venv de playwright) ══════════════════
def captura():
    import requests
    from playwright.sync_api import sync_playwright

    dist = REPO / 'frontend' / 'dist'
    if not dist.exists():
        sys.exit(f'No hi ha bundle a {dist} — cal `npm run build`.')
    estat = json.loads(ESTAT.read_text())
    token = estat['token']
    OUT.mkdir(exist_ok=True)
    sess = requests.Session()

    def handler(route, request):
        url = request.url
        cami = url.split(BASE, 1)[-1].split('?')[0] if url.startswith(BASE) else url
        if cami.startswith('/api/'):
            try:
                caps = {'Host': HOST_TENANT, 'Authorization': f'Bearer {token}'}
                ct = request.header_value('content-type')
                if ct:
                    caps['Content-Type'] = ct
                if cami.endswith('/import-sessions/cribratge/'):
                    # ⚠️ LA PUJADA NO POT VIATJAR PEL COS CAPTURAT. El `multipart` que el
                    # navegador construeix arriba aquí com a buffer i el reenviament el fa
                    # malbé: el backend rep un zip invàlid i `openpyxl` peta amb un 500 que NO
                    # és de l'aplicació sinó de l'arnès. Es re-emet la mateixa petició amb el
                    # fitxer de debò i els mateixos camps que el wizard envia.
                    caps.pop('Content-Type', None)
                    with open(estat['xlsx'], 'rb') as fx:
                        r = sess.post(VIU + url.split(BASE, 1)[-1], headers=caps,
                                      files={'document': (pathlib.Path(estat['xlsx']).name, fx,
                                             'application/vnd.openxmlformats-officedocument.'
                                             'spreadsheetml.sheet')},
                                      data={'model_id': str(MODEL_ID),
                                            'garment_type_item_code': '', 'garment': ''},
                                      timeout=300)
                    route.fulfill(status=r.status_code, body=r.content,
                                  headers={'content-type': r.headers.get('content-type',
                                                                         'application/json')})
                    return
                r = sess.request(request.method, VIU + url.split(BASE, 1)[-1], headers=caps,
                                 data=request.post_data_buffer, timeout=300)
                if r.status_code >= 400:
                    # Una passejada muda no serveix de res: si el backend diu que no, es diu.
                    cos = (request.post_data_buffer or b'')[:500].decode('utf8', 'replace')
                    print(f'  ⚠️  {request.method} {cami} → {r.status_code} {r.text[:300]}')
                    print(f'      cos enviat: {cos}')
                route.fulfill(status=r.status_code, body=r.content,
                              headers={'content-type': r.headers.get('content-type', 'application/json')})
            except Exception as e:
                route.fulfill(status=502, body=json.dumps({'error': str(e)}),
                              headers={'content-type': 'application/json'})
            return
        f = dist / cami.lstrip('/')
        if not f.is_file():
            f = dist / 'index.html'
        route.fulfill(status=200, body=f.read_bytes(),
                      headers={'content-type': mimetypes.guess_type(f.name)[0] or 'text/html'})

    def foto(pag, nom, què):
        desti = OUT / f'p1_{nom}.png'
        pag.screenshot(path=str(desti), full_page=True)
        print(f'✓ {desti.name:28} {què}')

    with sync_playwright() as p:
        nav = p.chromium.launch()
        ctx = nav.new_context(viewport={'width': 1600, 'height': 1100})
        pag = ctx.new_page()
        pag.route('**/*', handler)
        pag.goto(BASE + '/', wait_until='domcontentloaded')
        pag.evaluate("([t]) => { localStorage.setItem('access_token', t);"
                     " localStorage.setItem('fhort.lang', 'ca') }", [token])

        pag.goto(f'{BASE}/models/{MODEL_ID}?tab=Mesures', wait_until='networkidle')
        pag.wait_for_timeout(2000)
        # ⚠️ AQUEST CLIC ÉS UN GEST, NO UNA VISTA: obre la tasca «Definició POM» del model i li
        # engega el rellotge. És l'ÚNICA porta d'entrada al wizard —la targeta d'import viu dins
        # del panell d'entrada— i per això la captura va a un model VERGE de QA i amb acta
        # (decisió d'Agus, 14/08). Res del domini de mesures s'hi toca: la passejada no confirma.
        iniciar = pag.get_by_role('button', name='Iniciar Definició POM').first
        if iniciar.count():
            iniciar.click()
            pag.wait_for_timeout(3000)
        # El model 1320 ja té mesures: el tab entra en CONSULTA, no en gènesi, i la porta de
        # l'import és el botó de la peça («Importar taula»), no la targeta de la pantalla verge.
        porta = pag.get_by_text('Importar de fitxa tècnica').first
        if not porta.count():
            porta = pag.get_by_role('button', name='Importar taula').first
        porta.click()
        pag.wait_for_timeout(1200)
        pag.locator('input[type="file"]').first.set_input_files(estat['xlsx'])
        pag.wait_for_timeout(600)
        pag.get_by_role('button', name='Analitzar talles').click()
        pag.wait_for_timeout(4000)
        foto(pag, f'{CAS}_01_talles', 'pas 1 · les columnes del document aparellades')

        pag.get_by_role('button', name='Continuar → POMs').click()
        pag.wait_for_timeout(12000)
        if CAS == 'bruma':
            # LES DUES FILES QUE NO S'HAN APARELLAT SOLES: la persona les vincula al MATEIX POM
            # que la primera. Fins a P2 això era una col·lisió («Un POM no pot ser dues files»).
            base_codi = estat['codis'][0]
            # P2-ter · EL GEST SENCER DINS DEL PANELL: cercador → instància → fet. Les píndoles
            # ja no són a la fila (la fila INFORMA), o sigui que la passejada ha de fer el que
            # farà la persona: obrir, triar POM, triar instància i tancar amb «Fet».
            for i, pindola in ((1, 'Bottom'), (2, 'Extended')):
                pag.get_by_text('canvia el vincle').nth(i).click()
                pag.wait_for_timeout(900)
                pag.get_by_placeholder('Tria un POM del catàleg…').first.fill(base_codi)
                pag.wait_for_timeout(1600)
                if i == 1:
                    foto(pag, f'{CAS}_02a_cercador',
                         'el cercador amb les DUES poblacions: catàleg del client i de la casa')
                pag.locator(f'button:text-matches("^{base_codi} ·")').first.click()
                pag.wait_for_timeout(900)
                pag.locator('button[aria-pressed]', has_text=pindola).first.click()
                pag.wait_for_timeout(500)
                if i == 1:
                    foto(pag, f'{CAS}_02b_panell',
                         'el panell complet: vincle fet + INSTÀNCIA en format de mesures + Fet')
                pag.get_by_role('button', name='Fet').first.click()
                pag.wait_for_timeout(700)
        foto(pag, f'{CAS}_02_poms', 'pas 2 · files NETES: la instància al nom, cap píndola')

        pag.get_by_role('button', name='Continuar → Mesures').click()
        pag.wait_for_timeout(3000)
        foto(pag, f'{CAS}_03_graella', 'pas 3 · LA GRAELLA amb la clau de fila nova')

        # EL GEST QUE EL CANVI DE `key` POSAVA EN RISC: teclejar.
        cel = pag.locator('input[type="number"]').nth(1)
        cel.click()
        cel.fill('99.9')
        pag.wait_for_timeout(700)
        valor = cel.input_value()
        foto(pag, f'{CAS}_04_teclejat', f'la cel·la teclejada reté el valor ({valor})')
        print(('✅' if valor == '99.9' else '❌') + f' el valor teclejat hi queda: {valor!r}')
        ctx.close(); nav.close()
        return 0 if valor == '99.9' else 1


if __name__ == '__main__':
    sys.exit(prepara() or 0 if '--prepara' in sys.argv else captura())
