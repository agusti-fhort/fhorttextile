"""ARNÈS · SET-2/T8 · L'IMPORT PER PRENDA, CONTRA DADES VIVES I AMB ROLLBACK · model 1320.

El banc és el 1320 (`BRW-FW26-0001`, Blusa KAYCE) del tenant `fhort`, que és l'únic model del
corpus amb DUES prendes vives: la mare i la `02` (Pantaló). El document que s'hi importa és el
més hostil que hi ha: **la taula de la pròpia mare**, POM a POM. Si l'eix no travessés el
pipeline, l'import cauria damunt de les 28 files vives de la mare i les convertiria en
`IMPORTED` sense que ningú petés — el gènere de dany que aquest sprint persegueix.

Es mesura, en aquest ordre:

  A · IMPORT A LA `02` — les files neixen amb `garment='02'` i la mare queda BYTE A BYTE com
      estava (valor, origen i estat de les 28). El joc de regles de la mare tampoc es mou.
  B · CONTROL, IMPORT A LA MARE — el mateix document sense prenda al context es comporta com
      abans del tram: les files de la mare s'actualitzen i la `02` no rep res.
  C · LA PODA NO TRAVESSA — importar a la `02` un document que NO menciona els POMs de la mare
      no els proposa per podar (el 409 `poms_no_mencionats` parla només de la prenda).

⚠️ **TOT DINS D'UNA TRANSACCIÓ QUE SEMPRE ES DESFÀ.** Aquest arnès escriu de veritat —crida les
vistes reals, no una imitació— i per això la darrera línia de cada bloc és un
`savepoint_rollback`. Res del que fa arriba a quedar-se: al final es re-compta la BD i s'exigeix
que el cens sigui idèntic al d'abans. Si aquesta última comprovació no surt verda, l'arnès ho
diu en clar i el resultat NO s'ha de creure.

    cd backend && python ../ops/qa/qa_t8_import_per_prenda.py
"""
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fhort.settings')

import django  # noqa: E402
django.setup()

from django.db import transaction  # noqa: E402
from django_tenants.utils import schema_context  # noqa: E402
from rest_framework.test import APIRequestFactory, force_authenticate  # noqa: E402

MODEL_ID = 1320
SEGONA = '02'
MARE = ''

_ok = True


def diu(etiqueta, valor, esperat):
    global _ok
    verd = valor == esperat
    _ok = _ok and verd
    print(f'  {"✅" if verd else "❌"} {etiqueta}: {valor!r}' + ('' if verd else f'  (esperat {esperat!r})'))


def cens(model_id):
    """La foto de la BD que ha de sobreviure intacta a tot aquest arnès."""
    from fhort.models_app.models import BaseMeasurement, ModelGradingRule, Model
    m = Model.objects.get(id=model_id)
    return {
        'mesures': sorted(BaseMeasurement.objects
                          .filter(model_id=model_id)
                          .values_list('id', 'pom_id', 'garment', 'base_value_cm',
                                       'origen', 'is_active')),
        'regles': sorted(ModelGradingRule.objects.filter(model_id=model_id)
                         .values_list('id', 'pom_id', 'garment', 'logica')),
        'joc': m.grading_rule_set_id,
        'base': m.base_size_label,
        'run': m.size_run_model,
    }


def main():
    with schema_context('fhort'):
        from django.contrib.auth import get_user_model
        from fhort.models_app.extraction_views import import_session_confirmar_view
        from fhort.models_app.models import (BaseMeasurement, ImportSession, Model,
                                             ModelGarment, ModelGradingRule)

        model = Model.objects.get(id=MODEL_ID)
        peca = ModelGarment.objects.get(model=model, codi=SEGONA)
        user = get_user_model().objects.filter(profile__isnull=False).order_by('id').first()
        print(f'BANC · model {MODEL_ID} {model.codi_intern} «{model.nom_prenda}» · '
              f'peça {SEGONA} «{peca.nom}» · usuari {user.username}')

        abans = cens(MODEL_ID)
        vives = list(BaseMeasurement.objects.filter(model=model, garment=MARE, is_active=True,
                                                    base_value_cm__isnull=False)
                     .select_related('pom').order_by('ordre')[:8])
        run = [s.strip() for s in (model.size_run_model or '').replace(';', '·').split('·')
               if s.strip()]
        base = (model.base_size_label or '').strip()
        print(f'       run={run} base={base!r} · {len(abans["mesures"])} files a la taula '
              f'({sum(1 for r in abans["mesures"] if r[2] == MARE)} de la mare) · '
              f'{len(vives)} POMs al «document»')

        def sessio(garment, poms):
            """La sessió tal com el pas 4 la deixaria: el document ÉS la taula de la mare."""
            mesures = []
            for bm in poms:
                for i, et in enumerate(run):
                    mesures.append({'pom_master_id': bm.pom_id, 'talla_label': et,
                                    'valor': float(bm.base_value_cm) + i * 1.0})
            return ImportSession.objects.create(
                estat='MESURES_OK', model=model, garment=garment,
                poms_extrets=[{'codi_fitxa': bm.pom.codi_client or '',
                               'descripcio': bm.pom.nom_client or '',
                               'pom_master_id': bm.pom_id, 'actiu': True} for bm in poms],
                run_conciliat={'talla_mapping': [{'document': et, 'model': et} for et in run]},
                resultat={'mesures': mesures,
                          'extraccio': {'sizes': run, 'base_size': base}})

        def confirma(s, **body):
            req = APIRequestFactory().post(
                f'/api/v1/import-sessions/{s.token}/confirmar/', body, format='json')
            force_authenticate(req, user=user)
            return import_session_confirmar_view(req, s.token)

        # ══ A · IMPORT A LA 02 ════════════════════════════════════════════════════════
        print('\nA · IMPORT A LA PRENDA 02 (el document és la taula de la mare)')
        sid = transaction.savepoint()
        try:
            res = confirma(sessio(SEGONA, vives), poda_choice='conservar',
                           manual_choice='sobreescriure', container_choice='no_container')
            diu('estat del confirm', res.status_code, 201)
            if res.status_code != 201:
                print('    ', res.data)
            diu('prenda del resum', res.data.get('garment'), SEGONA)
            diu('nom de la prenda', res.data.get('garment_nom'), peca.nom)
            diu('files noves a la 02',
                BaseMeasurement.objects.filter(model=model, garment=SEGONA,
                                               origen='IMPORTED').count(), len(vives))
            # LA MARE, BYTE A BYTE.
            mare_ara = sorted(BaseMeasurement.objects.filter(model=model, garment=MARE)
                              .values_list('id', 'pom_id', 'base_value_cm', 'origen', 'is_active'))
            mare_abans = sorted((r[0], r[1], r[3], r[4], r[5]) for r in abans['mesures']
                                if r[2] == MARE)
            diu('la mare, intacta (id·pom·valor·origen·estat)', mare_ara, mare_abans)
            diu('el joc de regles de la mare', Model.objects.get(id=MODEL_ID).grading_rule_set_id,
                abans['joc'])
            diu('regles residents de la mare',
                ModelGradingRule.objects.filter(model=model, garment=MARE).count(),
                sum(1 for r in abans['regles'] if r[2] == MARE))
            diu('regles residents noves a la 02',
                ModelGradingRule.objects.filter(model=model, garment=SEGONA).exists(), True)
        finally:
            transaction.savepoint_rollback(sid)

        # ══ B · CONTROL: IMPORT A LA MARE ═════════════════════════════════════════════
        print('\nB · CONTROL · EL MATEIX DOCUMENT A LA MARE (comportament d\'abans del tram)')
        sid = transaction.savepoint()
        try:
            res = confirma(sessio(MARE, vives), poda_choice='conservar',
                           manual_choice='sobreescriure', container_choice='no_container')
            diu('estat del confirm', res.status_code, 201)
            if res.status_code != 201:
                print('    ', res.data)
            diu('prenda del resum', res.data.get('garment'), MARE)
            diu('les files de la mare, actualitzades',
                BaseMeasurement.objects.filter(model=model, garment=MARE,
                                               origen='IMPORTED').count(), len(vives))
            diu('cap fila nova a la 02',
                BaseMeasurement.objects.filter(model=model, garment=SEGONA,
                                               origen='IMPORTED').count(), 0)
        finally:
            transaction.savepoint_rollback(sid)

        # ══ C · LA PODA NO TRAVESSA LA FRONTERA ═══════════════════════════════════════
        print('\nC · LA PODA · un document que no menciona els POMs de la mare')
        sid = transaction.savepoint()
        try:
            # Sense `poda_choice`: si el confirm mirés TOT el model, els POMs vius de la
            # mare sortirien proposats per podar amb un 409. (El `container_choice` SÍ que
            # s'hi passa: la tria del contenidor és una altra llei i té el seu propi 409;
            # sense ella el que sortiria és aquella pregunta i no la que aquí es mesura.)
            res = confirma(sessio(SEGONA, vives), container_choice='no_container')
            diu('cap 409 de poda (la mare no és candidata)', res.status_code, 201)
            if res.status_code == 409:
                print(f'     → 409 {res.data.get("tipus")!r}: {res.data.get("n")} POM(s) '
                      f'de {res.data.get("garment_nom")!r}')
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
