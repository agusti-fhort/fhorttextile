"""V4-CENS · tots els models dels dos tenants, i què arrossega cadascun (READ-ONLY).

Es corre així (no escriu MAI res):
    backend/venv/bin/python manage.py shell < scripts_tmp/v4_cens_models.py

Per què existeix: abans de decidir què s'esborra a staging, cal veure QUÈ hi ha i, sobretot,
SEPARAR els models que aguanten el corpus estadístic de temps (D-3: `TimerEntrada` amb minuts
imputats, i les tasques albaranades/facturades que en depenen) dels que no arrosseguen res.
Esborrar els primers buida el corpus del Welford i de `lookup_estimated_minutes`; esborrar els
segons no costa res a ningú.

Columnes: id · ref · nom · client · #mesures actives · #regles residents · #sessions de fitting
· #tasques · #tasques amb temps · minuts imputats · albarà/factura · meritat (SaaS).
"""
from django_tenants.utils import schema_context
from django.db.models import Sum

from fhort.models_app.models import Model, BaseMeasurement, ModelGradingRule, ConsumptionRecord
from fhort.fitting.models import FittingSession
from fhort.tasks.models import ModelTask, TimerEntrada

TENANTS = ('fhort', 'los')


def cens(schema):
    with schema_context(schema):
        files = []
        for m in Model.objects.select_related('customer').order_by('id'):
            tasques = ModelTask.objects.filter(model=m)
            trams = TimerEntrada.objects.filter(model_task__model=m)
            minuts = trams.aggregate(s=Sum('minuts'))['s'] or 0
            amb_temps = (trams.filter(minuts__gt=0)
                         .values('model_task_id').distinct().count())
            albara = ModelTask.objects.filter(
                model=m, delivery_note_lines__isnull=False).exists()
            emes = ModelTask.objects.filter(
                model=m,
                delivery_note_lines__delivery_note__status__in=['ISSUED', 'INVOICED']).exists()
            files.append({
                'id': m.id,
                'ref': m.codi_intern,
                'nom': (m.nom_prenda or '')[:24],
                'client': getattr(m.customer, 'codi', None) or '—',
                'mesures': BaseMeasurement.objects.filter(model=m, is_active=True).count(),
                'regles': ModelGradingRule.objects.filter(model=m).count(),
                'sessions': FittingSession.objects.filter(model=m).count(),
                'tasques': tasques.count(),
                'amb_temps': amb_temps,
                'minuts': minuts,
                'albara': 'EMÈS' if emes else ('sí' if albara else '—'),
                'meritat': 'sí' if (m.consumption_started_at
                                    or ConsumptionRecord.objects.filter(model=m).exists()) else '—',
            })
        return files


def pinta(schema, files):
    # EL TALL QUE DECIDEIX: un model «aguanta el corpus» si té minuts imputats o va en albarà.
    corpus = [f for f in files if f['minuts'] > 0 or f['albara'] != '—']
    nets = [f for f in files if f not in corpus]
    print(f'\n{"═" * 118}\nTENANT «{schema}» · {len(files)} models '
          f'· {len(corpus)} aguanten el corpus de temps · {len(nets)} nets\n{"═" * 118}')
    cap = (f'{"id":>5} {"ref":22} {"nom":24} {"cli":5} {"mes":>4} {"regl":>5} {"fit":>4} '
           f'{"tsq":>4} {"c/t":>4} {"min":>6} {"albarà":7} {"merit":6}')
    for titol, grup in (('🛑 AGUANTEN EL CORPUS DE TEMPS (D-3)', corpus), ('NETS', nets)):
        print(f'\n── {titol} · {len(grup)} models {"─" * 40}')
        if not grup:
            print('   (cap)')
            continue
        print(cap)
        for f in grup:
            print(f'{f["id"]:>5} {f["ref"]:22} {f["nom"]:24} {f["client"]:5} {f["mesures"]:>4} '
                  f'{f["regles"]:>5} {f["sessions"]:>4} {f["tasques"]:>4} {f["amb_temps"]:>4} '
                  f'{f["minuts"]:>6} {f["albara"]:7} {f["meritat"]:6}')
        print(f'{"TOTAL":>5} {"":22} {"":24} {"":5} '
              f'{sum(f["mesures"] for f in grup):>4} {sum(f["regles"] for f in grup):>5} '
              f'{sum(f["sessions"] for f in grup):>4} {sum(f["tasques"] for f in grup):>4} '
              f'{sum(f["amb_temps"] for f in grup):>4} {sum(f["minuts"] for f in grup):>6}')
    return corpus, nets


tot = {}
for schema in TENANTS:
    tot[schema] = pinta(schema, cens(schema))

print(f'\n{"═" * 118}\nRESUM\n{"═" * 118}')
for schema, (corpus, nets) in tot.items():
    print(f'{schema:8} models={len(corpus) + len(nets):>3} · corpus={len(corpus):>3} '
          f'(minuts={sum(f["minuts"] for f in corpus)}) · nets={len(nets):>3}')
