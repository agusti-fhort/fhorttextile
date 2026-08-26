"""M4 · EL NUMERAL I EL DESBORDAMENT — FUM HTTP contra el backend VIU del worktree.

⚠️ **AQUEST SCRIPT ESCRIU**, i escriu sobre el banc `[QA-M4]` i **només** sobre ell: edita el
numeral de la seva comanda sintètica. **Mai el 1383, mai el golden 162, mai una comanda real.**
Per remuntar-lo: `venv/bin/python ../ops/qa/banc_m4_desbordament.py --remunta`.

🔑 **PER QUÈ UN FUM HTTP I NO NOMÉS ELS TESTS.** Un test corre dins del procés i amb el seu propi
client; el que no prova és **la porta**: la ruta, el gate de capability, el codi HTTP i el fet que
el codi del disc sigui el que el servidor serveix. Un 200 al disc i un 400 a l'usuari són l'estat
normal quan el gunicorn és ranci ([[ftt-400-linear-zero-era-el-proces]]).

    # 1) el banc i el backend del WORKTREE (mai `ftt-staging.service`)
    cd backend && venv/bin/python ../ops/qa/banc_m4_desbordament.py --remunta
    setsid nohup venv/bin/gunicorn fhort.wsgi:application \\
        --chdir /var/www/ftt-m4/backend --bind 127.0.0.1:8141 --workers 2 --timeout 60 &
    # 2) això
    venv/bin/python ../ops/qa/qa_m4_comercial_http.py
"""
import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                + '/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fhort.settings')

import django  # noqa: E402

django.setup()

from django_tenants.utils import schema_context                        # noqa: E402

from fhort.accounts.models import UserProfile                          # noqa: E402
from fhort.auth_jwt import TenantTokenObtainPairSerializer             # noqa: E402
from fhort.models_app.models import Model                              # noqa: E402
from fhort.tasks.models import Ronda                                   # noqa: E402

BASE = os.environ.get('BASE', 'http://127.0.0.1:8141')
HOST = 'staging.fhorttextile.tech'
TENANT = 'fhort'

ok, ko = [], []


def crit(nom, cond, detall=''):
    (ok if cond else ko).append(nom)
    print(f"  {'OK  ' if cond else 'FAIL'} {nom}{(' · ' + str(detall)) if detall else ''}")


def crida(metode, cami, cos=None, token=None):
    """(status, dades). Un 4xx NO és una excepció aquí: és una resposta que es mesura."""
    dades = json.dumps(cos).encode() if cos is not None else None
    r = urllib.request.Request(BASE + cami, data=dades, method=metode)
    r.add_header('Host', HOST)
    r.add_header('Content-Type', 'application/json')
    if token:
        r.add_header('Authorization', 'Bearer ' + token)
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            return resp.status, json.loads(resp.read() or b'null')
    except urllib.error.HTTPError as e:
        cru = e.read()
        try:
            return e.code, json.loads(cru or b'null')
        except json.JSONDecodeError:
            return e.code, {'_cru': cru[:200].decode('utf-8', 'replace')}


def main():
    with schema_context(TENANT):
        banc = {m.codi_intern: m for m in Model.objects.filter(codi_intern__startswith='QA-M4-')}
        if 'QA-M4-0001' not in banc:
            raise SystemExit('Falta el banc: corre `banc_m4_desbordament.py --remunta`.')
        amb = banc['QA-M4-0001']
        sense = banc['QA-M4-0002']
        r3 = Ronda.objects.get(model=amb, seq=3)
        linia = r3.linia_comanda
        comanda = linia.order
        customer_id = amb.customer_id
        perfil = UserProfile.objects.order_by('pk').first()
        # El claim `tenant_schema` l'estampa AQUEST serializer llegint l'schema ACTIU: un
        # `RefreshToken.for_user()` pelat dona el MATEIX 401 que no dur-ne cap (lliçó d'M1).
        token = str(TenantTokenObtainPairSerializer.get_token(perfil.user).access_token)

    print(f'BASE={BASE} · Host={HOST} · banc {sorted(banc)} · comanda '
          f'{comanda.document_number} · línia {linia.pk}\n')

    # ── 0 · LES PORTES ──────────────────────────────────────────────────────────────────────
    print('── 0 · les portes ──')
    st, _ = crida('GET', f'/api/v1/commerce/order-lines/{linia.pk}/')
    crit('sense token la línia de comanda contesta 401', st == 401, st)
    st, _ = crida('GET', f'/api/v1/commerce/delivery-notes/billable/?customer={customer_id}')
    crit('sense token la safata contesta 401', st == 401, st)

    # ── 1 · FIT-5 · EL NUMERAL VIU A LA LÍNIA DE COMANDA I S'HI EDITA ────────────────────────
    print('\n── 1 · FIT-5 · el numeral, a la comanda ──')
    st, cos = crida('GET', f'/api/v1/commerce/order-lines/{linia.pk}/', token=token)
    crit('la línia serveix `rounds_included`', st == 200 and 'rounds_included' in (cos or {}),
         (st, list((cos or {}).keys())))
    crit('…i val el del banc (2)', (cos or {}).get('rounds_included') == 2,
         (cos or {}).get('rounds_included'))

    st, cos = crida('PATCH', f'/api/v1/commerce/order-lines/{linia.pk}/',
                    {'rounds_included': 4}, token=token)
    crit('el numeral s\'EDITA per la porta (200)', st == 200
         and (cos or {}).get('rounds_included') == 4, (st, (cos or {}).get('rounds_included')))

    st, cos = crida('PATCH', f'/api/v1/commerce/order-lines/{linia.pk}/',
                    {'rounds_included': None}, token=token)
    crit('buidar-lo és «sense límit» (null), no 0', st == 200
         and (cos or {}).get('rounds_included') is None, (st, (cos or {}).get('rounds_included')))

    st, cos = crida('PATCH', f'/api/v1/commerce/order-lines/{linia.pk}/',
                    {'rounds_included': 2}, token=token)
    crit('i es torna a deixar com el banc (2)', st == 200
         and (cos or {}).get('rounds_included') == 2, (st, (cos or {}).get('rounds_included')))

    st, cos = crida('PATCH', f'/api/v1/commerce/order-lines/{linia.pk}/',
                    {'unit_price': '999.00'}, token=token)
    with schema_context(TENANT):
        linia.refresh_from_db()
    crit('la IRREVERSIBILITAT de B3b segueix sencera: el preu no es mou',
         str(linia.unit_price) == '120.00', linia.unit_price)

    # ── 2 · FIT-12 · EL VEREDICTE, I QUE NO ES RECALCULA ────────────────────────────────────
    print('\n── 2 · FIT-12 · el veredicte és una foto ──')
    with schema_context(TENANT):
        r3.refresh_from_db()
    crit('la R3 del model amb comanda és FORA DE COMANDA', r3.fora_de_comanda is True)
    crit('…amb el numeral de l\'obertura (2) i la seva línia',
         r3.numeral_vigent == 2 and r3.linia_comanda_id == linia.pk,
         (r3.numeral_vigent, r3.linia_comanda_id))
    crit('pujar i baixar el numeral per la porta NO ha reescrit la R3',
         r3.fora_de_comanda is True and r3.numeral_vigent == 2)
    with schema_context(TENANT):
        crit('cap volta del model SENSE comanda desborda',
             not Ronda.objects.filter(model=sense, fora_de_comanda=True).exists())

    # ── 3 · LA CARA DEL TÈCNIC NO CANVIA ────────────────────────────────────────────────────
    print('\n── 3 · el tècnic no veu res (FIT-12) ──')
    st, cos = crida('GET', f'/api/v1/models/{amb.pk}/rondes/', token=token)
    voltes = cos if isinstance(cos, list) else []
    crit('la porta de voltes del tècnic respon 200 amb les 3 voltes',
         st == 200 and len(voltes) == 3, (st, len(voltes)))
    fuita = [c for c in ('fora_de_comanda', 'linia_comanda', 'numeral_vigent')
             if any(c in v for v in voltes)]
    crit('…i NO en serveix cap camp del desbordament', not fuita, fuita)

    # ── 4 · LA SAFATA D'ALBARANABLES, AGRUPADA PER VOLTA ────────────────────────────────────
    print('\n── 4 · la safata agrupa per volta ──')
    st, cos = crida('GET', f'/api/v1/commerce/delivery-notes/billable/?customer={customer_id}',
                    token=token)
    grups = (cos or {}).get('groups') or []
    crit('la safata respon 200', st == 200, st)
    bloc = next((g for g in grups if g['model'].get('id') == amb.pk), None)
    crit('hi ha el bloc del model amb comanda', bloc is not None)
    if bloc is None:
        return
    crit('el bloc porta l\'índex de voltes ordenat',
         [r['seq'] for r in bloc.get('rondes', [])] == [1, 2, 3],
         [r['seq'] for r in bloc.get('rondes', [])])
    r3_cap = next((r for r in bloc['rondes'] if r['seq'] == 3), None)
    crit('la R3 hi surt marcada FORA DE COMANDA',
         bool(r3_cap and r3_cap['fora_de_comanda']), r3_cap)
    crit('…amb el perquè sencer: numeral i comanda',
         bool(r3_cap and r3_cap['numeral_vigent'] == 2
              and r3_cap['comanda'] == comanda.document_number),
         r3_cap and (r3_cap['numeral_vigent'], r3_cap['comanda']))
    crit('…i amb les DATES que FIT-12 demana (inici; fi null perquè és oberta)',
         bool(r3_cap and r3_cap['oberta_el'] and r3_cap['tancada_el'] is None),
         r3_cap and (r3_cap['oberta_el'], r3_cap['tancada_el']))

    items_r3 = [i for i in bloc['items'] if (i.get('ronda') or {}).get('seq') == 3]
    crit('les TASQUES de la R3 hi són, amb la volta enganxada', len(items_r3) >= 1,
         len(items_r3))
    crit('cap preu de volta calculat: la tasca proposa el preu del seu WO',
         all(i['proposed_price'] == '120.00' for i in items_r3),
         [i['proposed_price'] for i in items_r3])

    bloc_sense = next((g for g in grups if g['model'].get('id') == sense.pk), None)
    crit('el model SENSE comanda també s\'agrupa per volta…', bloc_sense is not None
         and len(bloc_sense.get('rondes', [])) == 3,
         bloc_sense and len(bloc_sense.get('rondes', [])))
    crit('…i cap de les seves voltes surt marcada',
         bool(bloc_sense) and not any(r['fora_de_comanda'] for r in bloc_sense['rondes']))

    # ── 5 · CAP ALBARÀ AUTOMÀTIC ────────────────────────────────────────────────────────────
    print('\n── 5 · albaranar segueix sent gest humà ──')
    with schema_context(TENANT):
        from fhort.commerce.models import DeliveryNote
        abans = DeliveryNote.objects.count()
    crida('GET', f'/api/v1/commerce/delivery-notes/billable/?customer={customer_id}', token=token)
    with schema_context(TENANT):
        despres = DeliveryNote.objects.count()
    crit('llegir la safata NO crea cap albarà', abans == despres, (abans, despres))


if __name__ == '__main__':
    main()
    print(f'\n{len(ok)} OK · {len(ko)} FAIL')
    if ko:
        print('FALLEN: ' + ' | '.join(ko))
    sys.exit(1 if ko else 0)
