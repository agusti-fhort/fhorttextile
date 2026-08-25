"""M5-DIA · EL RETROACTIU A LA CARA — QA de pantalla sobre el bundle REAL i el backend REAL.

El retroactiu és una escriptura silenciosa: no hi ha cap gest, cap toast i cap transició. La
manera de saber que ha anat bé **no és el log del script** —que diu el que el script creu— sinó
mirar què dibuixa el producte per a un model que ha rebut la seva R1 sense que ningú l'hagi obert.

Tres superfícies, que són les tres on la volta es veu:
  · **el BOARD** — el model hi és, a la seva columna, amb el xip de la darrera volta;
  · **la FITXA** — el Pla de treball el pinta PER VOLTES, amb el contenidor «R1» que no hi era;
  · **el REGISTRE** — la volta hi surt amb les seves dates.

I dues mesures NEGATIVES, que són les de la FASE 2 (les excepcions retirades):
  · **cap barra de progrés global** enlloc (M2 · CODA-BIS ①);
  · el model **no cau a la 4a columna** per no tenir volta (M3 · CODA C1) — ara en té.

⚠️ **AQUEST FUM NO ESCRIU RES.** És una lectura pura sobre models que ja existeixen: no obre
voltes, no transiciona cap tasca, no entrega res. **Mai el 1383, mai un model real** — treballa
sobre `QA-M1-0005`, que és del banc sintètic.

    setsid nohup venv/bin/gunicorn fhort.wsgi:application \\
        --chdir /var/www/ftt-m5/backend --bind 127.0.0.1:8151 --workers 2 --timeout 60 &
    cd frontend && npm run build
    /tmp/qa-venv/bin/python ops/qa/qa_m5_retroactiu_pantalla.py

Captures a `ops/qa/captures/m5_*.png`. Codi de sortida 1 si alguna mesura falla.
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
BACKEND = os.environ.get('BACKEND', 'http://127.0.0.1:8151')

#: 🔑 DOS INTÈRPRETS: Playwright viu a `/tmp/qa-venv` i Django al venv del backend.
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
from fhort.tasks.models import ModelTask, Ronda
with schema_context('fhort'):
    m = Model.objects.get(codi_intern='QA-M1-0005')
    r1 = Ronda.objects.get(model=m, seq=1)
    # PRECONDICIÓ C4a del board: només els PLANIFICATS hi entren. El retroactiu no planifica res
    # (i no ho ha de fer), o sigui que sense això el model no surt al board i la mesura sortiria
    # verda sense mesurar res. És l'única escriptura del fum, i és de PLANIFICACIÓ, no de volta.
    ModelTask.objects.filter(model=m, planned_start__isnull=True).update(
        planned_start=timezone.now())
    perfil = UserProfile.objects.order_by('pk').first()
    token = str(TenantTokenObtainPairSerializer.get_token(perfil.user).access_token)
    sortida = {
        'model': m.pk, 'codi': m.codi_intern, 'estat': m.estat, 'token': token,
        'ronda_id': r1.pk, 'oberta_el': r1.oberta_el.isoformat(),
        'tancada_el': r1.tancada_el.isoformat() if r1.tancada_el else None,
        'entregues': int(hasattr(r1, 'entrega')),
        'tasques': r1.tasques.count(),
        'pre_llei': Model.objects.filter(model_tasks__isnull=False, rondes__isnull=True)
                    .distinct().count(),
    }
print('@@' + json.dumps(sortida))
'''

ok, ko = [], []


def bootstrap():
    r = subprocess.run([str(VENV_BACKEND), '-c', _BOOTSTRAP], capture_output=True, text=True,
                       cwd=str(REPO / 'backend'))
    linia = next((l for l in r.stdout.splitlines() if l.startswith('@@')), None)
    if linia is None:
        raise SystemExit(f'no he pogut arrencar amb {VENV_BACKEND}:\n{r.stderr[-2000:]}')
    return json.loads(linia[2:])


def bolca(etiqueta, cos):
    if os.environ.get('M5_DEBUG'):
        print(f'\n----- {etiqueta} -----\n{cos[:4000]}\n----- fi -----\n')


def crit(nom, cond, detall=''):
    (ok if cond else ko).append(nom)
    print(f"  {'OK  ' if cond else 'FAIL'} {nom}{(' · ' + str(detall)) if detall else ''}")


def fes_handler(token):
    def handler(route):
        req = route.request
        if not req.url.startswith(BASE):       # el webfont d'icones ve de CDN: passa
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
    token, codi = a['token'], a['codi']
    print(f"bundle={DIST} · backend={BACKEND} · model {codi} (pk {a['model']}) · "
          f"R1 pk {a['ronda_id']}\n")

    # ── 0 · LA BD, ABANS DE MIRAR CAP PANTALLA ──────────────────────────────────────────────
    print('── 0 · el substrat ──')
    crit('el model retroactiu té la seva R1', a['ronda_id'] is not None)
    crit('…OBERTA (FIT-1: cap Entrega fabricada)',
         a['tancada_el'] is None and a['entregues'] == 0, (a['tancada_el'], a['entregues']))
    crit('…que ha adoptat les seves 2 tasques', a['tasques'] == 2, a['tasques'])
    crit("…amb la data del PASSAT, no la d'avui", a['oberta_el'].startswith('2026-08-24'),
         a['oberta_el'])
    crit('🚨 i a tot el tenant NO queda cap model PRE-LLEI', a['pre_llei'] == 0, a['pre_llei'])

    with sync_playwright() as p:
        navegador = p.chromium.launch()
        ctx = navegador.new_context(base_url=BASE, ignore_https_errors=True,
                                    viewport={'width': 1440, 'height': 1000})
        pagina = ctx.new_page()
        errors = []
        pagina.on('pageerror', lambda e: errors.append(str(e)))
        pagina.route('**/*', fes_handler(token))
        pagina.add_init_script(f"localStorage.setItem('access_token', {json.dumps(token)});"
                               "localStorage.setItem('fhort.lang', 'ca')")

        # ── A · LA FITXA: el Pla de treball ara és PER VOLTES ───────────────────────────────
        print('\n── A · la fitxa: la R1 que ningú no va obrir ──')
        pagina.goto(f"{BASE}/models/{a['model']}?tab=Dashboard", wait_until='networkidle',
                    timeout=60000)
        pagina.wait_for_timeout(2500)
        cos = pagina.inner_text('body')
        bolca('m5_fitxa', cos)
        pagina.screenshot(path=str(CAPTURES / 'm5_a1_fitxa_r1_retroactiva.png'), full_page=True)
        crit('la pantalla no peta (cap error de React)',
             not [e for e in errors if 'Minified React error' in e
                  or 'before initialization' in e], errors[:1])
        crit('🚨 el Pla de treball el pinta PER VOLTES: hi ha el contenidor «RONDA 1»',
             'RONDA 1' in cos.upper(), [l for l in cos.splitlines() if 'RONDA' in l.upper()][:3])
        crit('…i les dues tasques hi són a dins',
             'Definició POM' in cos and 'Fitxa tècnica' in cos)
        crit('✅ FASE 2 ① · cap barra de progrés global («n/m tasques fetes»)',
             'tasques fetes' not in cos, [l for l in cos.splitlines() if 'tasques fetes' in l])
        crit('…i el temps acumulat sobre el model segueix dit',
             'Temps acumulat sobre el model' in cos)
        crit('«+ Nova ronda» s\'ofereix (el model ja té volta)', '+ Nova ronda' in cos)

        # ── B · EL REGISTRE: la volta, amb les seves dates ─────────────────────────────────
        print('\n── B · el registre d\'activitat ──')
        pagina.goto(f"{BASE}/models/{a['model']}?tab=Registre d'activitat",
                    wait_until='networkidle', timeout=60000)
        pagina.wait_for_timeout(2500)
        cos = pagina.inner_text('body')
        bolca('m5_registre', cos)
        pagina.screenshot(path=str(CAPTURES / 'm5_b1_registre.png'), full_page=True)
        crit('🚨 el registre ensenya la volta', 'RONDA 1' in cos.upper() or 'R1' in cos,
             [l for l in cos.splitlines() if 'RONDA' in l.upper()][:3])
        crit('…amb la data del PASSAT (24/08), no la d\'avui',
             '24/08' in cos, [l for l in cos.splitlines() if '/08' in l][:4])

        # ── C · EL BOARD: on cau, i que NO cau a «Entregats» ───────────────────────────────
        print('\n── C · el board ──')
        pagina.goto(f'{BASE}/', wait_until='networkidle', timeout=60000)
        pagina.wait_for_timeout(3000)
        cos = pagina.inner_text('body')
        bolca('m5_board', cos)
        pagina.screenshot(path=str(CAPTURES / 'm5_c1_board.png'), full_page=True)
        crit('el model retroactiu és al board', codi in cos,
             [l for l in cos.splitlines() if codi in l][:2])
        crit('…amb el xip de la seva volta', 'volta oberta' in cos)

        # 🔒 MESURAT PER DINS de la columna, no al `body`: al body hi són tots i la mesura
        # sortiria verda digués el que digués la columna.
        def columna(nom):
            return pagina.locator(
                f"xpath=//span[normalize-space()='{nom}']/ancestor::div[2]").first.inner_text()
        entregats = columna('Entregats')
        crit('🚨 FASE 2 ② · NO cau a «Entregats» (la seva volta és OBERTA i sense entrega)',
             codi not in entregats, entregats.replace('\n', ' · ')[:160])
        crit('…i sí que és a una columna de FEINA',
             any(codi in columna(c) for c in ('Pendents', 'En curs', 'Pausats')),
             [c for c in ('Pendents', 'En curs', 'Pausats') if codi in columna(c)])

        # ── D · LA COLUMNA «ESTAT» DE /models (FASE 3 · 🚩4) ───────────────────────────────
        print('\n── D · /models: la columna «Estat» ja no pinta un guió ──')
        pagina.goto(f'{BASE}/models', wait_until='networkidle', timeout=60000)
        pagina.wait_for_timeout(2500)
        cos = pagina.inner_text('body')
        bolca('m5_models', cos)
        pagina.screenshot(path=str(CAPTURES / 'm5_d1_columna_estat.png'), full_page=True)
        crit('la nota «pendent del Kanban» ja no hi és',
             'pendent del Kanban' not in cos and 'Estat comercial' not in cos)
        crit('🚨 la columna diu l\'estat del cicle amb paraules', 'Nou' in cos,
             [l for l in cos.splitlines() if l.strip() == 'Nou'][:2])
        crit('…i cap estat inventat fora dels tres d\'M3',
             not any(x in cos for x in ('EnCurs', 'EnRevisio', 'Tancat')))

        navegador.close()


if __name__ == '__main__':
    main()
    print(f'\n{len(ok)} OK · {len(ko)} FAIL')
    if ko:
        print('FALLEN: ' + ' | '.join(ko))
    sys.exit(1 if ko else 0)
