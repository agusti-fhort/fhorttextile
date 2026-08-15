"""ARNÈS · P1 · LA GRAELLA PARLA PER FILA — la cadena sencera amb el payload que el front
emet ARA, contra dades vives i amb rollback · model 1320.

El guard de `node --test` defensa la lògica de la graella i el de Django defensa el backend.
El que NO cobreix cap dels dos és la JUNTURA: que el payload que `taulaMesures.js` construeix
avui sigui exactament el que les vistes reals saben llegir. Això és el que es mesura aquí, i
per això les mesures d'aquest fitxer es construeixen amb les MATEIXES regles que
`construeixMesures`/`construeixBaseValues` (mateix ordre, mateixes claus, cel·les buides
omeses) i no amb una imitació còmoda.

EL CAS és el real: fitxa BROWNIE BRUMA/RUFFLES. B «at the top» 30 · BB «at the bottom» 31 ·
B1 «stretched out» 40 — el MATEIX POM en tres instàncies. Es mesura, en aquest ordre:

  A · PAS 2 — les tres files es resolen al mateix POM sense que el detector cridi col·lisió,
      i la identitat que la persona ha triat queda desada a la fila.
  B · PAS 3 — el payload amb `ordre` es desa amb els eixos HERETATS de la fila (no del cos).
  C · PREVIEW — `base_values` en forma de LLISTA torna `clau='ordre'` i una graduació per
      fila; amb l'objecte d'abans, les tres files n'haurien compartit una.
  D · PAS 5 — al disc hi ha TRES files amb 30, 31 i 40. Amb la cadena vella n'hi hauria tres
      amb el mateix número, sense error i sense avís.
  E · NO-REGRESSIÓ — el mateix camí amb UN POM PER FILA i el payload d'avui (sense `ordre`)
      escriu exactament el que escrivia.

⚠️ **TOT DINS D'UNA TRANSACCIÓ QUE SEMPRE ES DESFÀ.** Crida les vistes reals contra el tenant
viu; la darrera línia de cada bloc és un `savepoint_rollback` i al final es re-compta la BD i
s'exigeix que el cens sigui idèntic al d'abans. Si aquesta última comprovació no surt verda,
el resultat NO s'ha de creure.

    cd backend && python ../ops/qa/qa_p1_graella_per_fila.py
"""
import os
import pathlib
import sys
import uuid

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fhort.settings')

import django  # noqa: E402
django.setup()

from django.db import transaction  # noqa: E402
from django_tenants.utils import schema_context  # noqa: E402
from rest_framework.test import APIRequestFactory, force_authenticate  # noqa: E402

MODEL_ID = 1320
MARE = ''
BRUMA = [(0, 'B', 'at the top', '', 30.0),
         (1, 'BB', 'at the bottom', 'bottom', 31.0),
         (2, 'B1', 'stretched out', 'extended', 40.0)]

_ok = True


def diu(etiqueta, valor, esperat):
    global _ok
    verd = valor == esperat
    _ok = _ok and verd
    print(f'  {"✅" if verd else "❌"} {etiqueta}: {valor!r}' + ('' if verd else f'  (esperat {esperat!r})'))


def nota(etiqueta, valor):
    print(f'  ·  {etiqueta}: {valor!r}')


def cens(model_id):
    """La foto de la BD que ha de sobreviure intacta a tot aquest arnès."""
    from fhort.models_app.models import BaseMeasurement, ModelGradingRule, Model
    m = Model.objects.get(id=model_id)
    return {
        'mesures': sorted(BaseMeasurement.objects.filter(model_id=model_id)
                          .values_list('id', 'pom_id', 'capa', 'instancia', 'garment',
                                       'base_value_cm', 'origen', 'is_active')),
        'regles': sorted(ModelGradingRule.objects.filter(model_id=model_id)
                         .values_list('id', 'pom_id', 'garment', 'logica')),
        'joc': m.grading_rule_set_id,
        'base': m.base_size_label,
        'run': m.size_run_model,
    }


def mesures_com_el_front(files, run, taula, amb_ordre=True):
    """El payload del pas 3 amb les MATEIXES regles que `taulaMesures.construeixMesures`:
    fila per fila, talla per talla, cel·les buides omeses, i `ordre` additiu al costat del
    `pom_master_id` de sempre. `amb_ordre=False` és el front d'abans de P1."""
    out = []
    for f in files:
        for et in run:
            v = taula.get(f['ordre'], {}).get(et)
            if v in (None, ''):
                continue
            m = {'pom_master_id': f['pom_master_id'], 'talla_label': et, 'valor': float(v)}
            if amb_ordre:
                m = {'ordre': f['ordre'], **m}
            out.append(m)
    return out


def main():
    with schema_context('fhort'):
        from django.contrib.auth import get_user_model
        from fhort.models_app.extraction_views import (
            import_session_confirmar_view, import_session_grading_preview_view,
            import_session_mesures_view, import_session_poms_view)
        from fhort.models_app.models import BaseMeasurement, ImportSession, Model
        from fhort.pom.models import POMMaster

        model = Model.objects.get(id=MODEL_ID)
        user = get_user_model().objects.filter(profile__isnull=False).order_by('id').first()
        run = [s.strip() for s in (model.size_run_model or '').replace(';', '·').split('·')
               if s.strip()]
        base = (model.base_size_label or '').strip()
        # El POM del document: un de VIU a la taula de la mare, per no inventar catàleg.
        bm0 = (BaseMeasurement.objects.filter(model=model, garment=MARE, is_active=True)
               .select_related('pom').order_by('ordre').first())
        pom = bm0.pom
        print(f'BANC · model {MODEL_ID} {model.codi_intern} «{model.nom_prenda}» · '
              f'usuari {user.username} · run={run} base={base!r}')
        print(f'       POM del document: #{pom.id} {pom.codi_client} «{pom.nom_client}» '
              f'(viu a la taula de la mare)')

        abans = cens(MODEL_ID)
        i_base = run.index(base) if base in run else 0

        def sessio(files):
            return ImportSession.objects.create(
                token=uuid.uuid4(), estat='POMS', model=model, garment=MARE,
                poms_extrets=[{'codi_fitxa': c, 'descripcio': d, 'pom_master_id': None,
                               'values': {}, 'actiu': False, 'ordre': o}
                              for o, c, d in files],
                run_conciliat={'talla_mapping': [{'document': et, 'model': et} for et in run]},
                resultat={'extraccio': {'sizes': run, 'base_size': base}})

        def crida(vista, s, cos, metode='patch', sufix='poms'):
            f = APIRequestFactory()
            req = getattr(f, metode)(f'/api/v1/import-sessions/{s.token}/{sufix}/', cos,
                                     format='json')
            force_authenticate(req, user=user)
            return vista(req, token=str(s.token)) if metode != 'post' or sufix != 'confirmar' \
                else vista(req, s.token)

        def taula_de(files_valors):
            """{ordre: {talla: valor}} com la graella: base al seu lloc i ±1 a la resta."""
            return {o: {et: v + (i - i_base) * 1.0 for i, et in enumerate(run)}
                    for o, v in files_valors.items()}

        # ══ A+B+C+D · LA BRUMÀ, LA CADENA SENCERA ═════════════════════════════════════
        print('\nA · PAS 2 — tres files, un POM, tres instàncies')
        sid = transaction.savepoint()
        try:
            s = sessio([(o, c, d) for o, c, d, _i, _v in BRUMA])
            res = crida(import_session_poms_view, s, {
                'poms_confirmats': [],
                'resolucions': [{'ordre': o, 'accio': 'vincula', 'pom_master_id': pom.id,
                                 'instancia': inst} for o, _c, _d, inst, _v in BRUMA],
            })
            diu('el pas 2 no crida col·lisió', res.status_code, 200)
            if res.status_code != 200:
                print('    ', getattr(res, 'data', None))
            s.refresh_from_db()
            files = sorted(s.poms_extrets, key=lambda f: f['ordre'])
            diu('la identitat queda a la fila', [f.get('instancia') for f in files],
                [inst for _o, _c, _d, inst, _v in BRUMA])

            print('\nB · PAS 3 — el payload del front, amb `ordre`')
            taula = taula_de({o: v for o, _c, _d, _i, v in BRUMA})
            payload = mesures_com_el_front(files, run, taula)
            res = crida(import_session_mesures_view, s, {'mesures': payload,
                                                         'valors_mode': 'absoluts'},
                        sufix='mesures')
            diu('el pas 3 desa', res.status_code, 200)
            diu('valors desats', res.data.get('n_valors'), len(run) * 3)
            s.refresh_from_db()
            desades = [(m['ordre'], m.get('instancia'), m['valor'])
                       for m in s.resultat['mesures'] if m['talla_label'] == base]
            diu('els eixos els hereta de la FILA', sorted(desades),
                [(0, '', 30.0), (1, 'bottom', 31.0), (2, 'extended', 40.0)])

            print('\nC · PREVIEW — `base_values` en llista')
            res = crida(import_session_grading_preview_view, s,
                        {'base_values': [{'ordre': o, 'valor': v} for o, _c, _d, _i, v in BRUMA]},
                        metode='post', sufix='grading-preview')
            if res.status_code == 200:
                diu('respon per FILA', res.data.get('clau'), 'ordre')
                diu('una graduació per fila', sorted(res.data.get('grading') or {}),
                    ['0', '1', '2'])
            else:
                nota('preview no avaluable (el model no gradua ara mateix)',
                     (res.status_code, (res.data or {}).get('error')))

            print('\nD · PAS 5 — el disc')
            res = crida(import_session_confirmar_view, s,
                        {'container_choice': 'no_container', 'poda_choice': 'conservar',
                         'manual_choice': 'sobreescriure'}, metode='post', sufix='confirmar')
            diu('el confirm desa', res.status_code, 201)
            if res.status_code != 201:
                print('    ', getattr(res, 'data', None))
            al_disc = {(bm.capa, bm.instancia): bm.base_value_cm
                       for bm in BaseMeasurement.objects.filter(model=model, garment=MARE,
                                                                pom=pom, origen='IMPORTED')}
            diu('TRES files, TRES valors', al_disc,
                {('exterior', ''): 30.0, ('exterior', 'bottom'): 31.0,
                 ('exterior', 'extended'): 40.0})
        finally:
            transaction.savepoint_rollback(sid)

        # ══ E · NO-REGRESSIÓ ══════════════════════════════════════════════════════════
        print('\nE · NO-REGRESSIÓ — un POM per fila i el payload d\'ABANS de P1 (sense `ordre`)')
        sid = transaction.savepoint()
        try:
            s = sessio([(0, pom.codi_client or 'X', pom.nom_client or '')])
            res = crida(import_session_poms_view, s, {
                'poms_confirmats': [],
                'resolucions': [{'ordre': 0, 'accio': 'vincula', 'pom_master_id': pom.id}]})
            diu('el pas 2 resol', res.status_code, 200)
            s.refresh_from_db()
            files = sorted(s.poms_extrets, key=lambda f: f['ordre'])
            payload = mesures_com_el_front(files, run, taula_de({0: 55.0}), amb_ordre=False)
            diu('el payload és el literal d\'avui', sorted(payload[0]),
                ['pom_master_id', 'talla_label', 'valor'])
            crida(import_session_mesures_view, s, {'mesures': payload,
                                                   'valors_mode': 'absoluts'}, sufix='mesures')
            s.refresh_from_db()
            res = crida(import_session_confirmar_view, s,
                        {'container_choice': 'no_container', 'poda_choice': 'conservar',
                         'manual_choice': 'sobreescriure'}, metode='post', sufix='confirmar')
            diu('el confirm desa', res.status_code, 201)
            if res.status_code != 201:
                print('    ', getattr(res, 'data', None))
            fila = BaseMeasurement.objects.filter(model=model, garment=MARE, pom=pom,
                                                  origen='IMPORTED').first()
            diu('una sola fila, a la identitat de sempre',
                (fila.capa, fila.instancia, fila.base_value_cm), ('exterior', '', 55.0))
        finally:
            transaction.savepoint_rollback(sid)

        # ══ F · P2-bis · LA INSTÀNCIA COMPOSTA TRAVESSA ═══════════════════════════════
        print('\nF · P2-bis — una instància COMPOSTA (`left-relaxed`) de punta a punta')
        sid = transaction.savepoint()
        try:
            # Les píndoles creuen els dos eixos i n'emeten UN slug compost per la porta única
            # (`composaInstancia`). El que aquí es mesura és que la cadena no el parteixi ni el
            # reordeni pel camí: el que la persona tria al pas 2 ha de ser el que hi ha al disc.
            s = sessio([(0, 'B', 'left relaxed'), (1, 'BB', 'right relaxed')])
            res = crida(import_session_poms_view, s, {
                'poms_confirmats': [],
                'resolucions': [
                    {'ordre': 0, 'accio': 'vincula', 'pom_master_id': pom.id,
                     'instancia': 'left-relaxed'},
                    {'ordre': 1, 'accio': 'vincula', 'pom_master_id': pom.id,
                     'instancia': 'right-relaxed'},
                ]})
            diu('el pas 2 accepta les compostes', res.status_code, 200)
            s.refresh_from_db()
            files = sorted(s.poms_extrets, key=lambda f: f['ordre'])
            payload = mesures_com_el_front(files, run, taula_de({0: 60.0, 1: 61.0}))
            crida(import_session_mesures_view, s, {'mesures': payload,
                                                   'valors_mode': 'absoluts'}, sufix='mesures')
            s.refresh_from_db()
            res = crida(import_session_confirmar_view, s,
                        {'container_choice': 'no_container', 'poda_choice': 'conservar',
                         'manual_choice': 'sobreescriure'}, metode='post', sufix='confirmar')
            diu('el confirm desa', res.status_code, 201)
            if res.status_code != 201:
                print('    ', getattr(res, 'data', None))
            diu('el slug compost arriba SENCER i sense reordenar',
                {(bm.capa, bm.instancia): bm.base_value_cm
                 for bm in BaseMeasurement.objects.filter(model=model, garment=MARE, pom=pom,
                                                          origen='IMPORTED')},
                {('exterior', 'left-relaxed'): 60.0, ('exterior', 'right-relaxed'): 61.0})
        finally:
            transaction.savepoint_rollback(sid)

        # ══ EL ROLLBACK, DEMOSTRAT ════════════════════════════════════════════════════
        print('\nROLLBACK')
        diu('la BD ha tornat exactament on era', cens(MODEL_ID), abans)

    print('\n' + ('✅ ARNÈS VERD' if _ok else '❌ ARNÈS VERMELL'))
    return 0 if _ok else 1


if __name__ == '__main__':
    # Tot l'arnès viu dins d'UNA transacció que no es confirma mai: cap escriptura d'aquest
    # fitxer pot sobreviure ni que el procés mori a mig camí.
    try:
        with transaction.atomic():
            codi = main()
            transaction.set_rollback(True)
    except Exception:
        raise
    sys.exit(codi)
