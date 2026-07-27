"""Xarxa de seguretat del guard de tasca oblidada.

El guard viu al navegador: als 30 min avisa, i sense resposta auto-pausa. Però el navegador
és un testimoni que desapareix — pestanya tancada, portàtil abaixat, sessió morta. En aquests
casos NINGÚ no pausa i el timer corre tota la nit: el temps real del model i l'estadística
Welford queden contaminats, que és exactament el que el guard havia d'evitar.

Aquesta comanda és el segon cinturó, no una segona política:
  - MATEIXA via: `transition_task(..., 'Paused', ...)`. Cap màquina d'estats paral·lela.
  - MATEIXA marca: `auto='cron_40min'` al log, perquè digui la veritat sobre qui ha pausat.
  - MAI Done: el Stop és humà. La tasca queda pausada i represa-ble.

Llindar 40 min > els 30 del navegador a posta: així el camí normal és sempre el del modal (que
dóna 3 min a la persona per dir-hi la seva) i el cron només recull el que aquell no ha pogut
tancar. Es mesura des de `last_heartbeat`, o des d'`inici` si no n'hi ha hagut mai cap.

Ús:  manage.py pausa_tasques_oblidades [--dry-run] [--tenant SCHEMA] [--minuts N]
Idempotent: un cop pausada, la tasca ja no té tram obert i la següent passada no la veu.

CRONTAB (NO instal·lada — decisió d'Agus al deploy). Cada 5 min:
  */5 * * * * cd /var/www/ftt-staging/backend && /ruta/al/venv/bin/python manage.py \\
      pausa_tasques_oblidades >> /var/log/ftt/guard_tasques.log 2>&1
"""
import logging

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django_tenants.utils import get_tenant_model, schema_context

logger = logging.getLogger(__name__)

LLINDAR_MINUTS = 40


class Command(BaseCommand):
    help = ('Auto-pausa els trams oberts sense senyal de vida des de fa massa estona '
            '(xarxa de seguretat del guard de tasca oblidada).')

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Informa del que faria, sense escriure res.')
        parser.add_argument('--tenant', type=str, default=None,
                            help='Schema del tenant a processar (per defecte: tots).')
        parser.add_argument('--minuts', type=int, default=LLINDAR_MINUTS,
                            help=f'Llindar en minuts (per defecte {LLINDAR_MINUTS}). '
                                 'Baixar-lo és la via per al QA a staging.')

    def handle(self, *args, **options):
        from fhort.tasks.models import ModelTask, TimerEntrada
        from fhort.tasks.services_c import transition_task, TransitionError

        dry_run, minuts = options['dry_run'], options['minuts']
        if minuts < 1:
            raise CommandError('--minuts ha de ser >= 1.')

        TenantModel = get_tenant_model()
        tenants = TenantModel.objects.exclude(schema_name='public')
        if options['tenant']:
            tenants = tenants.filter(schema_name=options['tenant'])
            if not tenants.exists():
                raise CommandError(f"Tenant '{options['tenant']}' no trobat.")

        total_pausades = 0
        for tenant in tenants:
            with schema_context(tenant.schema_name):
                ara = timezone.now()
                oberts = (TimerEntrada.objects
                          .filter(fi__isnull=True, actiu=True, model_task__status='InProgress')
                          .select_related('model_task', 'model_task__task_type', 'tecnic')
                          .order_by('inici'))
                pausades = 0
                for timer in oberts:
                    # El segell és l'últim senyal de vida; sense cap batec, val l'obertura del
                    # tram. Una tasca oberta i mai confirmada ha de vèncer igual que una altra.
                    segell = timer.last_heartbeat or timer.inici
                    edat = (ara - segell).total_seconds() / 60
                    if edat <= minuts:
                        continue
                    task = timer.model_task
                    if dry_run:
                        self.stdout.write(
                            f'  [dry-run] {tenant.schema_name} · task={task.pk} '
                            f'({task.task_type.code}) tecnic={timer.tecnic_id} '
                            f'sense senyal fa {edat:.0f} min')
                        pausades += 1
                        continue
                    try:
                        # MATEIXA porta que el kanban i que el modal. El tècnic que hi consta és
                        # el propietari del tram: `auto` és el que impedeix que el log digui
                        # que la pausa la va fer ell.
                        transition_task(task, 'Paused', timer.tecnic, auto='cron_40min')
                    except TransitionError as e:
                        # Cursa amb el navegador: si el tècnic acaba de pausar-la, ja no és
                        # InProgress. No és un error del guard; el tram ja està tancat.
                        logger.info('guard cron: transició no aplicada tenant=%s task=%s: %s',
                                    tenant.schema_name, task.pk, e)
                        continue
                    pausades += 1
                    logger.info('guard cron: auto-pausada tenant=%s task=%s tipus=%s tecnic=%s '
                                'sense senyal fa %.0f min (llindar %s)',
                                tenant.schema_name, task.pk, task.task_type.code,
                                timer.tecnic_id, edat, minuts)

                # Anomalia ANOTADA, no tocada (fora d'scope): una tasca En curs sense cap tram
                # obert no la pot recollir aquest guard —no hi ha segell des d'on comptar— i és
                # senyal d'una fuita de timer aigües amunt.
                orfes = (ModelTask.objects
                         .filter(status='InProgress')
                         .exclude(timers__fi__isnull=True, timers__actiu=True)
                         .count())
                if pausades or orfes:
                    self.stdout.write(
                        f'{tenant.schema_name}: {pausades} auto-pausada/es'
                        + (f' · ⚠ {orfes} En curs sense tram obert (no tocades)' if orfes else ''))
                total_pausades += pausades

        mode = ' (dry-run)' if dry_run else ''
        self.stdout.write(self.style.SUCCESS(
            f'Guard de tasca oblidada{mode}: {total_pausades} auto-pausada/es '
            f'(llindar {minuts} min).'))
