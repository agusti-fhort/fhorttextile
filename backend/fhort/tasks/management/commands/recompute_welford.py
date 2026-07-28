"""Reconstrueix l'estadística Welford (TaskTimeEstimate) des dels timers reals.

PER QUÈ. `record_actual_time` és incremental i append-only: el que hi entra no en surt. Els
trams zombis (timers oberts setmanes i tancats en reobrir la tasca) hi van deixar mostres de
45.000 minuts, i cel·les senceres van quedar amb mitjanes de 9-13 h que `effective_minutes`
serveix al planificador com si fossin temps reals. Tancar els trams a zero no ho desfà: cal
refer el càlcul.

SEMÀNTICA — VERIFICADA CONTRA EL CODI, NO ASSUMIDA (`services_i.py:19`, `services_c.py:274`):

  · Una MOSTRA = el TOTAL de la tasca (`Sum(minuts)` de tots els seus timers), no un tram.
  · `record_actual_time` es crida a CADA transició →Done. Com que `Done→InProgress` és una
    transició permesa (rectificació), una tasca reoberta i re-tancada aporta una mostra NOVA,
    amb el total acumulat d'aquell moment. Comprovat contra les dades: a `fhort`, `n` de cada
    cel·la quadra amb el nombre de transicions →Done, no amb el de tasques Done.
  · Es descarta la mostra si `x <= 0` o si el model no té `garment_type_item`.

Per això la mostra d'una transició →Done a l'instant T es reconstrueix com la suma dels timers
JA TANCATS en aquell moment (`fi <= T`): és exactament el que `Sum('minuts')` veia (els trams
encara oberts tenen `minuts` NULL i no sumen).

LÍMIT CONEGUT — l'atribució no és reproduïble. La clau de cel·la surt de
`model.garment_type_item_id`, que és MUTABLE i del qual no es desa el valor històric. Si un
model ha canviat de variant, la seva mostra va entrar en una cel·la i el recompute la posarà a
l'actual. Això NO és una repetició fidel del passat: és una re-derivació sota l'atribució
d'AVUI (que és la que el planificador farà servir demà). A `fhort` se'n veu el rastre: hi ha
cel·les amb `n > 0` i cap transició →Done que hi apunti.

Ús:  manage.py recompute_welford [--tenant SCHEMA] [--apply]
Per defecte DRY-RUN. Les cel·les que ja quadren NO es toquen — i que quadrin és el test de
correcció de gratis: si el recompute no reprodueix les cel·les sanes, el recompute és dolent.
"""
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django_tenants.utils import get_tenant_model, schema_context

from fhort.tasks.services_i import MAX_MINUTS_TRAM, WELFORD_MIN_SAMPLES, tram_compta


def _mostres_de_la_cella(item_id, task_type_id, tasques):
    """Mostres (cronològiques) que la cel·la (item, task_type) hauria rebut, amb la regla
    d'higiene aplicada: els trams impossibles no compten com a temps treballat."""
    from fhort.tasks.models import TaskTransition

    mostres = []
    for task in tasques:
        trams = [t for t in task.timers.all() if tram_compta(t)]
        for tr in TaskTransition.objects.filter(model_task=task, to_status='Done').order_by('at'):
            # El que `Sum('minuts')` veia en aquell instant: els trams ja tancats.
            x = sum((t.minuts or 0) for t in trams if t.fi <= tr.at)
            if x > 0:                      # `record_actual_time` descarta x<=0
                mostres.append((tr.at, Decimal(x)))
    mostres.sort(key=lambda m: m[0])
    return [x for _, x in mostres]


# La BD quantitza en DESAR (mean_minutes 2 decimals, m2 4), i la crida següent re-llegeix el
# valor ja quantitzat. Però DINS d'una crida el càlcul va a precisió plena: `record_actual_time`
# fa servir la mitjana NOVA sense arrodonir per obtenir delta2. Arrodonir-la abans d'usar-la
# desviava la m2 i marcava com a «corregides» cel·les sanes. L'ordre importa: calcular, i
# quantitzar només allò que es desa.
Q_MEAN = Decimal('0.01')
Q_M2 = Decimal('0.0001')


def _welford(mostres):
    """Mateixa recurrència que `record_actual_time`, en el mateix ordre i amb el mateix
    round-trip per BD: si les mostres són les mateixes, el resultat ha de ser IDÈNTIC.
    Que les cel·les sanes de `fhort` hi quadrin és el test de correcció d'aquest command."""
    n, mean, m2 = 0, Decimal('0'), Decimal('0')
    for x in mostres:
        n += 1
        delta = x - mean
        mean_nova = mean + (delta / n)          # precisió plena dins de la crida
        m2 = (m2 + (delta * (x - mean_nova))).quantize(Q_M2)
        mean = mean_nova.quantize(Q_MEAN)       # quantitzat en desar, com fa la BD
    return n, mean, m2


class Command(BaseCommand):
    help = 'Reconstrueix n/mean/m2 de TaskTimeEstimate des dels timers reals (higiene inclosa).'

    def add_arguments(self, parser):
        parser.add_argument('--tenant', type=str, default=None,
                            help='Schema del tenant (per defecte: tots).')
        parser.add_argument('--apply', action='store_true',
                            help='Escriu a BD. Sense el flag: dry-run.')

    def handle(self, *args, **options):
        from fhort.tasks.models import ModelTask, TaskTimeEstimate

        aplica = options['apply']
        tenants = get_tenant_model().objects.exclude(schema_name='public')
        if options['tenant']:
            tenants = tenants.filter(schema_name=options['tenant'])
            if not tenants.exists():
                raise CommandError(f"Tenant '{options['tenant']}' no trobat.")

        self.stdout.write(f'{"APPLY" if aplica else "DRY-RUN"} · higiene: trams > '
                          f'{MAX_MINUTS_TRAM:,} min exclosos de la mostra\n')

        for tenant in tenants.order_by('schema_name'):
            with schema_context(tenant.schema_name):
                # Univers de claus: tota cel·la existent + tota combinació amb feina tancada
                # (l'atribució d'avui pot demanar cel·les que encara no existeixen).
                claus = set(TaskTimeEstimate.objects.values_list(
                    'garment_type_item_id', 'task_type_id'))
                claus |= set(ModelTask.objects
                             .filter(transitions__to_status='Done',
                                     model__garment_type_item__isnull=False)
                             .values_list('model__garment_type_item_id', 'task_type_id'))

                celles = {(c.garment_type_item_id, c.task_type_id): c
                          for c in TaskTimeEstimate.objects.select_related('task_type')}
                canvis, sanes, novas, sense_proves = [], 0, [], []

                for item_id, tt_id in sorted(claus):
                    tasques = list(ModelTask.objects
                                   .filter(model__garment_type_item_id=item_id, task_type_id=tt_id)
                                   .prefetch_related('timers'))
                    n, mean, m2 = _welford(_mostres_de_la_cella(item_id, tt_id, tasques))
                    cella = celles.get((item_id, tt_id))
                    if cella is None:
                        if n:
                            novas.append((item_id, tt_id, n, mean, m2))
                        continue
                    # SENSE PROVES VIVES. Esborrar una ModelTask s'emporta timers i transicions en
                    # CASCADE; si d'aquella combinació no en queda cap tasca, la cel·la és l'ÚNIC
                    # rastre que sobreviu de la feina que la va omplir. Posar-la a zero no seria
                    # recomputar: seria deduir absència de l'absència de proves. Mateixa llei que
                    # la data-op — es treu la mentida, mai la traça. I aquí no hi ha mentida: sense
                    # mostres no hi ha res a higienitzar.
                    if not tasques and cella.n:
                        sense_proves.append(cella)
                        continue
                    if cella.n == n and cella.mean_minutes == mean and cella.m2 == m2:
                        sanes += 1
                    else:
                        canvis.append((cella, n, mean, m2))

                self.stdout.write(self.style.MIGRATE_HEADING(
                    f'── {tenant.schema_name}: {len(canvis)} cel·la/es a corregir · '
                    f'{sanes} ja quadren (verificades) · {len(novas)} sense fila'))

                if canvis:
                    self.stdout.write(
                        f'   {"cel·la":<28}{"n":>10}{"mitjana (min)":>22}{"m2":>20}')
                    for cella, n, mean, m2 in canvis:
                        etq = f'item={cella.garment_type_item_id} {cella.task_type.code}'
                        self.stdout.write(
                            f'   {etq:<28}{cella.n:>5} → {n:<3}'
                            f'{float(cella.mean_minutes):>10,.1f} → {float(mean):<9,.1f}'
                            f'{float(cella.m2):>10,.0f} → {float(m2):<9,.0f}')
                for item_id, tt_id, n, mean, m2 in novas:
                    self.stdout.write(f'   NOVA item={item_id} task_type={tt_id}: '
                                      f'n={n} mean={float(mean):,.1f}')
                if sense_proves:
                    self.stdout.write(self.style.WARNING(
                        f'   ⚠ {len(sense_proves)} cel·la/es sense cap tasca supervivent — '
                        f'NO tocades (últim rastre d\'aquella feina):'))
                    for c in sense_proves:
                        avis = ' · JA MANA sobre el planificador' if c.n >= WELFORD_MIN_SAMPLES else ''
                        self.stdout.write(f'     item={c.garment_type_item_id} {c.task_type.code}: '
                                          f'n={c.n} mean={float(c.mean_minutes):,.1f}{avis}')

                if not aplica:
                    self.stdout.write('   (dry-run: res escrit)\n')
                    continue

                with transaction.atomic():
                    for cella, n, mean, m2 in canvis:
                        cella.n, cella.mean_minutes, cella.m2 = n, mean, m2
                        cella.save(update_fields=['n', 'mean_minutes', 'm2'])
                    for item_id, tt_id, n, mean, m2 in novas:
                        TaskTimeEstimate.objects.create(
                            garment_type_item_id=item_id, task_type_id=tt_id,
                            n=n, mean_minutes=mean, m2=m2)
                self.stdout.write(self.style.SUCCESS(
                    f'   escrites: {len(canvis)} corregides + {len(novas)} creades\n'))
