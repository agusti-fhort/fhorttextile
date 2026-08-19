"""Reconstrueix l'estadística Welford (TaskTimeEstimate) des dels timers reals.

PER QUÈ. `record_actual_time` és incremental i append-only: el que hi entra no en surt. Els
trams zombis (timers oberts setmanes i tancats en reobrir la tasca) hi van deixar mostres de
45.000 minuts, i cel·les senceres van quedar amb mitjanes de 9-13 h que `effective_minutes`
serveix al planificador com si fossin temps reals. Tancar els trams a zero no ho desfà: cal
refer el càlcul.

SEMÀNTICA — F3.1 (05/08/2026) · LA LLEI D-3: **UNA TASCA = UNA MOSTRA.**

  · Una MOSTRA = el TOTAL d'una `ModelTask` (`Sum(minuts)` dels seus trams sans), **un sol cop**.
  · Reobrir o rectificar **ACTUALITZA** aquella mostra; no n'afegeix una de nova. Una tasca
    tancada disset vegades és una peça feta, no disset peces fetes.
  · Cada **RONDA** és una mostra INDEPENDENT, i cada **correcció** també — i això surt sol de la
    regla de dalt, sense cap cas especial: són `ModelTask` diferents (F1.1 · S-20).
  · El temps **DECLARAT** (`origen='declarat'`) compta igual que el mesurat: una tasca externa
    és feina feta, i que el rellotge no hi arribi no la fa menys real.
  · Es descarta la mostra si `x <= 0` o si el model no té `garment_type_item`.

QUÈ HI HAVIA ABANS, i per què això no és un ajust sinó una correcció. El corpus es construïa per
TRANSICIÓ →Done: com que `Done→InProgress` és permesa (rectificació), cada re-tancament hi
deixava una mostra nova amb el total acumulat d'aquell moment. El resultat és que les tasques
que es reobren —les que costen— pesaven tantes vegades com s'havien reobert, i sempre amb el
número més alt. L'estadística no mesurava quant costa fer una peça: mesurava quantes vegades
s'havia tancat, i ho feia passar per temps.

LÍMIT CONEGUT — l'atribució no és reproduïble. La clau de cel·la surt de
`model.garment_type_item_id`, que és MUTABLE i del qual no es desa el valor històric. Si un
model ha canviat de variant, la seva mostra va entrar en una cel·la i el recompute la posarà a
l'actual. Això NO és una repetició fidel del passat: és una re-derivació sota l'atribució
d'AVUI (que és la que el planificador farà servir demà). A `fhort` se'n veu el rastre: hi ha
cel·les amb `n > 0` i cap transició →Done que hi apunti.

Ús:  manage.py recompute_welford [--tenant SCHEMA] [--apply] [--sense-orfes]
`--sense-orfes` NO és una decisió presa: és la simulació que serveix per prendre-la (v. §orfes).
Per defecte DRY-RUN. Les cel·les que ja quadren NO es toquen — i que quadrin és el test de
correcció de gratis: si el recompute no reprodueix les cel·les sanes, el recompute és dolent.
"""
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from django_tenants.utils import get_tenant_model, schema_context

from fhort.tasks.services_i import MAX_MINUTS_TRAM, WELFORD_MIN_SAMPLES, tram_compta


def es_tram_orfe(tram, task):
    """🚩 TROBALLA DEL TRAM T · un rellotge que va córrer sol.

    Fins a T2, les quatre targetes externes (`design_review`, `design_clarify`, `pattern_hand`,
    `audit`) cridaven `open-task` en prémer «Iniciar». Allò posava la tasca En curs i obria un
    `TimerEntrada` MESURAT — però una tasca externa es fa FORA de l'eina: no hi ha pantalla on
    treballar ni cap batec que sostingui el rellotge. El tram corria fins que algú el pausava,
    o fins que el guard el matava.

    Un tram MESURAT sobre una tasca EXTERNA és, per definició, un d'aquests: la feina externa
    només es pot declarar, mai mesurar. No és temps mal mesurat: és temps que no s'ha mesurat.
    """
    return (task.task_type.tipus == 'Externa-lliure'
            and tram.origen != 'declarat')


def _instant_de_tancament(task):
    """Quan es va donar per feta. Ordena el corpus, i l'ordre importa perquè Welford no és
    commutatiu en la m2. L'última →Done mana (una tasca reoberta compta per l'últim cop que es
    va tancar); sense transicions, `finished_at`."""
    from fhort.tasks.models import TaskTransition

    ultima = (TaskTransition.objects.filter(model_task=task, to_status='Done')
              .order_by('-at').values_list('at', flat=True).first())
    return ultima or task.finished_at


def _mostres_de_la_cella(item_id, task_type_id, tasques, *, sense_orfes=False):
    """Mostres de la cel·la (item, task_type) sota la llei D-3: **una tasca, una mostra**.

    El total és el d'AVUI —tots els trams sans de la tasca— i no el que es veia en el moment
    de tancar-la: una tasca que es reobre i s'hi treballa més val el que ha costat sencera, no
    el que semblava costar el primer cop. Això és el que vol dir «reobrir ACTUALITZA la mostra».

    `sense_orfes` simula el corpus sense els rellotges orfes (v. `es_tram_orfe`). No és una
    decisió presa: és el número que serveix per prendre-la.
    """
    mostres = []
    for task in tasques:
        # Sense cap →Done la tasca no ha produït res encara: no és una mostra, és feina en curs.
        quan = _instant_de_tancament(task)
        if quan is None:
            continue
        trams = [t for t in task.timers.all()
                 if tram_compta(t) and not (sense_orfes and es_tram_orfe(t, task))]
        x = sum((t.minuts or 0) for t in trams)
        if x > 0:                          # `record_actual_time` descarta x<=0
            mostres.append((quan, Decimal(x)))
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
        parser.add_argument('--sense-orfes', action='store_true',
                            help='Simula el corpus SENSE els rellotges orfes de les externes '
                                 '(v. §orfes del docstring). Serveix per decidir, no decideix.')


    # ── ELS TRES INFORMES DEL DRY-RUN ────────────────────────────────────────
    # No són decoració: són el que permet mirar el delta abans d'escriure'l. El brief de F3.1
    # demana el punt de parada aquí a posta, i un informe que no digui QUÈ canvia i PER QUÈ no
    # serviria per aturar-se amb criteri.

    def _delta_per_tipus(self, canvis, novas):
        """El delta AGREGAT per TaskType: és on es veu si el que es mou és el que esperàvem."""
        from collections import defaultdict

        per_tipus = defaultdict(lambda: {'celles': 0, 'n_vell': 0, 'n_nou': 0,
                                         'mean_vell': Decimal('0'), 'mean_nou': Decimal('0')})
        for cella, n, mean, _m2 in canvis:
            d = per_tipus[cella.task_type.code]
            d['celles'] += 1
            d['n_vell'] += cella.n
            d['n_nou'] += n
            d['mean_vell'] += cella.mean_minutes * cella.n     # ponderada per mostres
            d['mean_nou'] += mean * n
        if not per_tipus:
            return
        self.stdout.write('\n   DELTA PER TIPUS DE TASCA')
        self.stdout.write(f'   {"tipus":<16}{"cel·les":>9}{"n":>16}{"mitjana ponderada":>28}')
        for code in sorted(per_tipus):
            d = per_tipus[code]
            mv = float(d['mean_vell'] / d['n_vell']) if d['n_vell'] else 0.0
            mn = float(d['mean_nou'] / d['n_nou']) if d['n_nou'] else 0.0
            fletxa = '↓' if mn < mv else ('↑' if mn > mv else '=')
            self.stdout.write(
                f'   {code:<16}{d["celles"]:>9}{d["n_vell"]:>8} → {d["n_nou"]:<5}'
                f'{mv:>14,.1f} → {mn:<9,.1f} {fletxa}')
        if novas:
            self.stdout.write(f'   (+ {len(novas)} cel·la/es noves, sense valor previ a comparar)')

    def _mostres_duplicades(self):
        """Les tasques que la semàntica vella comptava més d'un cop: tantes mostres com
        vegades s'havien tancat. Són exactament les que el canvi arregla."""
        from django.db.models import Count

        from fhort.tasks.models import ModelTask

        repetides = (ModelTask.objects
                     .annotate(tancaments=Count('transitions',
                                                filter=Q(transitions__to_status='Done')))
                     .filter(tancaments__gt=1)
                     .select_related('task_type', 'model')
                     .order_by('-tancaments')[:20])
        files = list(repetides)
        if not files:
            self.stdout.write('\n   MOSTRES DUPLICADES: cap tasca tancada més d\'un cop.')
            return
        total = (ModelTask.objects
                 .annotate(t=Count('transitions', filter=Q(transitions__to_status='Done')))
                 .filter(t__gt=1).count())
        self.stdout.write(f'\n   MOSTRES DUPLICADES · {total} tasca/ques tancades més d\'un cop '
                          f'(abans: 1 mostra per tancament · ara: 1 per tasca)')
        for t in files:
            minuts = sum((x.minuts or 0) for x in t.timers.all() if tram_compta(x))
            self.stdout.write(f'     tasca {t.pk:<5} {t.task_type.code:<14} '
                              f'model {t.model_id:<5} · {t.tancaments:>2} tancaments → 1 mostra '
                              f'· total {minuts:,} min')
        if total > len(files):
            self.stdout.write(f'     … i {total - len(files)} més')

    def _rellotges_orfes(self):
        """🚩 Els trams MESURATS sobre tasques EXTERNES: rellotges que van córrer sols.

        Es compten A PART i NO es toquen. Excloure'ls del corpus és el més probable —no són
        feina mesurada, són una porta que obria un rellotge sense pantalla— però és decisió
        d'Agus, i `--sense-orfes` existeix per poder-la prendre amb el número al davant.
        """
        from fhort.tasks.models import TimerEntrada

        orfes = [t for t in TimerEntrada.objects
                 .filter(model_task__task_type__tipus='Externa-lliure')
                 .exclude(origen='declarat')
                 .select_related('model_task', 'model_task__task_type')]
        sans = [t for t in orfes if tram_compta(t)]
        minuts = sum((t.minuts or 0) for t in sans)
        if not orfes:
            self.stdout.write('\n   RELLOTGES ORFES: cap.')
            return
        self.stdout.write(self.style.WARNING(
            f'\n   ⚠ RELLOTGES ORFES · {len(orfes)} tram/s mesurats sobre tasques EXTERNES '
            f'({len(sans)} dins d\'higiene, {minuts:,} min)'))
        self.stdout.write('     Una tasca externa es fa FORA de l\'eina: aquests trams són de '
                          'les portes que obrien rellotge sense pantalla (arreglat a T2).')
        per_code = {}
        for t in sans:
            c = t.model_task.task_type.code
            per_code.setdefault(c, [0, 0])
            per_code[c][0] += 1
            per_code[c][1] += (t.minuts or 0)
        for code in sorted(per_code):
            n, m = per_code[code]
            self.stdout.write(f'     {code:<18}{n:>4} tram/s · {m:>8,} min')
        self.stdout.write('     → DECISIÓ D\'AGUS. `--sense-orfes` simula el corpus sense ells.')

    def handle(self, *args, **options):
        from fhort.tasks.models import ModelTask, TaskTimeEstimate

        aplica, sense_orfes = options['apply'], options['sense_orfes']
        tenants = get_tenant_model().objects.exclude(schema_name='public')
        if options['tenant']:
            tenants = tenants.filter(schema_name=options['tenant'])
            if not tenants.exists():
                raise CommandError(f"Tenant '{options['tenant']}' no trobat.")

        self.stdout.write(f'{"APPLY" if aplica else "DRY-RUN"} · llei D-3: UNA TASCA = UNA '
                          f'MOSTRA · higiene: trams > {MAX_MINUTS_TRAM:,} min fora'
                          + (' · SENSE ORFES (simulació)' if sense_orfes else '') + '\n')

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
                    n, mean, m2 = _welford(_mostres_de_la_cella(
                        item_id, tt_id, tasques, sense_orfes=sense_orfes))
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

                self._delta_per_tipus(canvis, novas)
                self._mostres_duplicades()
                self._rellotges_orfes()

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
