"""Backfill de taxonomia MINUSINFORMADA als models existents (sprint WIZARD-COMPLET, Fase D.1).

Omple NOMÉS camps DERIVABLES de forma segura (denormalitzacions pures), mai inventa un valor que
requereixi criteri humà:

  • garment_group  ← garment_type.grup → GarmentGroup.codi   (idèntic a _resolve_garment_def i al
    que el wizard ja fa en crear; l'import el deixava NULL → aquest és el forat que tanca).

NO toca `grading_rule_set`: `Model.grading_rule_set` i `GarmentTypeItem.grading_rule_set` són punters
DESACOBLATS a posta (assignar-lo materialitzaria regles residents = inventar graduació). Els models
sense graduació es queden així (estat vàlid) i els marca `flag_incomplete_models` (watchpoint).

Idempotent: un model que ja té garment_group es SALTA. Tenant-scoped (default fhort). DRY-RUN per
defecte (auditoria SELECT abans/després impresa); `--commit` per escriure. Tot ORM, cap SQL cru.

    python manage.py backfill_model_taxonomy --schema fhort              # dry-run
    python manage.py backfill_model_taxonomy --schema fhort --commit     # escriu
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django_tenants.utils import schema_context


class Command(BaseCommand):
    help = 'Backfill de garment_group derivat (garment_type.grup) als models existents. Dry-run per defecte.'

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
        from fhort.models_app.models import Model
        from fhort.pom.models import GarmentGroup

        # Auditoria ABANS (SELECT).
        total = Model.objects.count()
        null_before = Model.objects.filter(garment_group__isnull=True).count()

        rows = []       # (codi_intern, grup_string, resultat)
        n_fill = n_skip = n_nogrp = n_notype = 0

        @transaction.atomic
        def execute():
            nonlocal n_fill, n_skip, n_nogrp, n_notype
            sp = transaction.savepoint()

            qs = (Model.objects.select_related('garment_type', 'garment_group')
                  .order_by('id'))
            for m in qs:
                if m.garment_group_id is not None:
                    n_skip += 1
                    continue
                if not m.garment_type_id or not (m.garment_type.grup or '').strip():
                    rows.append((m.codi_intern, m.garment_type.grup if m.garment_type_id else '(sense type)', 'sense-grup-al-type'))
                    n_notype += 1
                    continue
                grup = m.garment_type.grup
                grp = GarmentGroup.objects.filter(codi=grup).first()
                if grp is None:
                    rows.append((m.codi_intern, grup, 'grup-NO-existeix-com-GarmentGroup'))
                    n_nogrp += 1
                    continue
                m.garment_group = grp
                m.save(update_fields=['garment_group'])
                rows.append((m.codi_intern, grup, f'omplert → {grp.codi}'))
                n_fill += 1

            if commit:
                transaction.savepoint_commit(sp)
            else:
                transaction.savepoint_rollback(sp)

        execute()

        # Auditoria DESPRÉS (SELECT) — en dry-run reflecteix l'estat REAL (revertit), no el simulat.
        null_after = Model.objects.filter(garment_group__isnull=True).count()

        mode = 'COMMIT' if commit else 'DRY-RUN'
        self.stdout.write(f"\n=== backfill_model_taxonomy [{mode}] · schema={schema} ===")
        self.stdout.write(f"\n{'MODEL':<20} {'GRUP (type)':<16} RESULTAT")
        self.stdout.write('-' * 70)
        for codi, grup, res in rows:
            self.stdout.write(f"{codi:<20} {str(grup):<16} {res}")
        self.stdout.write('-' * 70)
        self.stdout.write(
            f"TOTALS: omplerts={n_fill} · ja-tenien={n_skip} · sense-grup-al-type={n_notype} · "
            f"grup-inexistent={n_nogrp} · models={total}")
        self.stdout.write(
            f"AUDIT garment_group NULL: abans={null_before} · "
            f"{'després=' + str(null_after) if commit else 'després(simulat)=' + str(null_before - n_fill)}")
        if not commit:
            self.stdout.write("\n(dry-run: cap escriptura; tot revertit al savepoint. Afegeix --commit per escriure.)")
