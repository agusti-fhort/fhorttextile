"""WATCHPOINTS de compleció per als models minusinformats (sprint WIZARD-COMPLET, Fase D.2).

Després del backfill (D.1), els camps NO derivables que segueixen buits (essencialment `grading_rule_set`,
que NO es pot inventar) es marquen amb un WATCHPOINT DE SISTEMA OBERT perquè cap model quedi buit «en
silenci»: l'equip veu què cal completar i ho fa editant el model pel wizard (pas 4).

Reutilitza la MAQUINÀRIA EXISTENT de watchpoint de config incompleta (NO en crea una de paral·lela):
  • `services.model_config_missing(m)` → la llista EXACTA de camps de config que falten.
  • Watchpoint de SISTEMA = `task IS NULL` + `dades` (llista de claus) + `created_by IS NULL`
    (mateixa convenció que el watchpoint d'import viu, models_app/models.py:938).
  • El signal `_update_import_watchpoint` (signals.py) ja el manté sincronitzat i el RESOL SOL quan el
    model es completa (post_save). Aquí només TAPEM EL FORAT: creem el watchpoint als models que en
    necessiten un i encara no en tenen (creats per wizard/clone/legacy, no per import).

Distinció respectada: watchpoint = FLAG HUMÀ/PERSISTENT (Watchpoint row), NO una alerta computada de
tolerància. IDEMPOTENT: si ja hi ha un watchpoint de sistema OBERT per al model, no en crea un altre.
DRY-RUN per defecte; `--commit` per escriure. Tenant-scoped (default fhort).

    python manage.py flag_incomplete_models --schema fhort              # dry-run
    python manage.py flag_incomplete_models --schema fhort --commit     # escriu
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django_tenants.utils import schema_context


class Command(BaseCommand):
    help = 'Crea watchpoints de sistema (oberts) als models amb config incompleta que no en tenen. Dry-run per defecte.'

    def add_arguments(self, parser):
        parser.add_argument('--schema', default='fhort', help='Schema del tenant (default: fhort).')
        parser.add_argument('--commit', action='store_true',
                            help='Escriu a la BD. Sense això: dry-run (default).')
        parser.add_argument('--dry-run', action='store_true',
                            help='No-op explícit (el dry-run ja és el comportament per defecte).')

    def handle(self, *args, **opts):
        with schema_context(opts['schema']):
            self._run(opts['commit'] and not opts['dry_run'], opts['schema'])

    def _run(self, commit, schema):
        from fhort.models_app.models import Model, Watchpoint
        from fhort.models_app.services import model_config_missing

        # Etiquetes CA de reserva (el front re-renderitza per clau des de `dades` en l'idioma del lector).
        LABELS = {
            'garment_type_item': 'tipologia de la peça',
            'base_size': 'talla base',
            'size_run': 'run de talles',
            'grading_rule_set': 'graduació (joc de regles)',
        }
        today = timezone.now().date().isoformat()

        def wp_exists(model_id):
            # Mateixa convenció que l'import: un sol watchpoint de sistema obert per model.
            return Watchpoint.objects.filter(
                model_id=model_id, task__isnull=True, dades__isnull=False, estat='open').exists()

        rows = []       # (codi_intern, missing, accio)
        n_create = n_have = n_ok = 0

        @transaction.atomic
        def execute():
            nonlocal n_create, n_have, n_ok
            sp = transaction.savepoint()

            for m in Model.objects.order_by('id'):
                missing = model_config_missing(m)
                if not missing:
                    n_ok += 1
                    continue
                if wp_exists(m.id):
                    rows.append((m.codi_intern, ','.join(missing), 'ja-té-watchpoint'))
                    n_have += 1
                    continue
                labels = ', '.join(LABELS.get(k, k) for k in missing)
                text = (f"Migració wizard graduació ({today}): cal completar la configuració editant el "
                        f"model pel wizard (pas 4). Camps pendents: {labels}.")
                Watchpoint.objects.create(
                    model=m, task=None, created_by=None,
                    dades=missing, text=text, estat='open')
                rows.append((m.codi_intern, ','.join(missing), 'watchpoint-creat'))
                n_create += 1

            if commit:
                transaction.savepoint_commit(sp)
            else:
                transaction.savepoint_rollback(sp)

        execute()

        mode = 'COMMIT' if commit else 'DRY-RUN'
        self.stdout.write(f"\n=== flag_incomplete_models [{mode}] · schema={schema} ===")
        self.stdout.write(f"\n{'MODEL':<20} {'CAMPS PENDENTS':<28} ACCIÓ")
        self.stdout.write('-' * 78)
        for codi, miss, acc in rows:
            self.stdout.write(f"{codi:<20} {miss:<28} {acc}")
        self.stdout.write('-' * 78)
        self.stdout.write(
            f"TOTALS: watchpoints-creats={n_create} · ja-tenien={n_have} · complets={n_ok} · "
            f"models={n_create + n_have + n_ok}")
        if not commit:
            self.stdout.write("\n(dry-run: cap escriptura; tot revertit al savepoint. Afegeix --commit per escriure.)")
