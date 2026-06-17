"""Clona un Model a un model de QA dedicat per provar Size Check sense tocar el golden.

Reutilitzable:
    python manage.py clone_model_for_qa --schema fhort --source 162 --assignee a.devant@fhort.cat
    python manage.py clone_model_for_qa --schema fhort --source 162 --assignee a.devant@fhort.cat --recreate

- Reusa grading_rule_set (FK compartida), clona BaseMeasurements, deixa que el signal creï
  el SizeFitting (cal responsable), crea GradingVersion activa + grading, i afegeix una
  tasca size_check assignada perquè surti al Kanban.
- Idempotent: si ja existeix un clon QA del mateix source/customer, NO en crea un segon
  (retorna el pk). --recreate purga el clon previ (children PROTECT inclosos) i en fa un de nou.
- Verifica al final que el grading del clon és IDÈNTIC al de l'origen (mateix ruleset/base).
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django_tenants.utils import schema_context

QA_TAG = '[QA-SC]'   # marca al nom_prenda per identificar els clons de QA


def _differ(a, b):
    if a is None or b is None:
        return a is not b
    return abs(float(a) - float(b)) > 1e-6


class Command(BaseCommand):
    help = "Clona un Model a un model de QA per a Size Check (reusa ruleset, clona base, grading, tasca)."

    def add_arguments(self, parser):
        parser.add_argument('--schema', required=True, help='Schema del tenant (ex: fhort)')
        parser.add_argument('--source', type=int, default=162, help='pk del Model origen (def: 162)')
        parser.add_argument('--assignee', required=True,
                            help='username o email del tècnic (responsable del model + assignee de la tasca)')
        parser.add_argument('--recreate', action='store_true',
                            help='Si ja existeix un clon QA, el purga i en crea un de nou.')

    def handle(self, *args, **o):
        with schema_context(o['schema']):
            self._run(o)

    @transaction.atomic
    def _run(self, o):
        from fhort.models_app.models import Model, BaseMeasurement, ModelGradingRule
        from fhort.fitting.models import SizeFitting, GradingVersion, GradedSpec
        from fhort.pom.services import generate_graded_specs
        from fhort.tasks.models import ModelTask, TaskType
        from fhort.accounts.models import UserProfile

        src = Model.objects.filter(pk=o['source']).first()
        if not src:
            raise CommandError(f"Model origen {o['source']} no existeix.")

        prof = (UserProfile.objects.filter(user__username=o['assignee']).first()
                or UserProfile.objects.filter(user__email=o['assignee']).first())
        if not prof:
            raise CommandError(f"Tècnic {o['assignee']!r} no trobat (UserProfile).")

        # --- Guard idempotent ---
        existing = list(Model.objects.filter(customer=src.customer, nom_prenda__startswith=QA_TAG))
        if existing:
            if not o['recreate']:
                self.stdout.write(self.style.WARNING(
                    f"Ja existeix clon QA: pk={existing[0].pk} codi={existing[0].codi_intern}. "
                    f"Usa --recreate per refer-lo."))
                return
            for m in existing:
                old_pk = m.pk
                self._purge(m)
                self.stdout.write(f"Clon QA previ purgat: pk={old_pk}")

        # --- 1) Clona el Model (codi auto-generat pel signal: codi_intern buit) ---
        clone = Model.objects.get(pk=src.pk)
        clone.pk = None
        clone.id = None
        clone.codi_intern = ''        # → generate_model_code el regenera (+ sequencial + codi_tenant)
        clone.codi_tenant = ''
        clone.nom_prenda = f"{QA_TAG} {src.nom_prenda or src.codi_intern}"
        clone.measurements_version = 1
        clone.responsable = prof      # imprescindible: sync_size_fitting crea el SF si hi ha responsable
        clone.fase_actual = 'Proto'
        clone.estat = 'Nou'
        for f in ('consumption_started_at', 'data_objectiu', 'design_freeze_at', 'design_freeze_by'):
            if hasattr(clone, f):
                setattr(clone, f, None)
        clone.save()   # reusa grading_rule_set/size_system/garment_type per valor de FK; signal crea SF 'Proto'
        self.stdout.write(f"Model clon: pk={clone.pk} codi={clone.codi_intern} ruleset={clone.grading_rule_set_id} "
                          f"size_run={clone.size_run_model!r} base={clone.base_size_label!r}")

        # --- 2) Clona BaseMeasurements (ABANS del grading: el motor llegeix la base) ---
        n_bm = 0
        for bm in BaseMeasurement.objects.filter(model=src):
            bm.pk = None; bm.id = None
            bm.model = clone
            bm.save()      # F1 registra creació (model nou, no auditoria del golden)
            n_bm += 1
        self.stdout.write(f"BaseMeasurements clonades: {n_bm}")

        # --- 3) ModelGradingRule: 162 en té 0 → clon gradua pel ruleset compartit. ---
        n_mgr = ModelGradingRule.objects.filter(model=src).count()
        for r in ModelGradingRule.objects.filter(model=src):
            r.pk = None; r.id = None; r.model = clone; r.save()
        self.stdout.write(f"ModelGradingRule origen={n_mgr} (clonades={n_mgr}); ruleset reusat={clone.grading_rule_set_id}")

        # --- 4) SizeFitting (creat pel signal) + GradingVersion activa + grading ---
        sf = SizeFitting.objects.filter(model=clone).order_by('numero').first()
        if sf is None:   # defensa: si el signal no l'hagués creat
            sf = SizeFitting.objects.create(model=clone, numero=1, codi=f"{clone.codi_intern}-SF1",
                                            tipus='Proto', estat='Pendent', base_tancada=False, creat_per=prof)
        gv = GradingVersion.objects.create(size_fitting=sf, version_number=1, is_active=True, nom='QA inicial')
        n_specs = generate_graded_specs(sf.pk)
        self.stdout.write(f"SizeFitting pk={sf.pk} ({sf.tipus}) + GradingVersion v1 pk={gv.pk} + grading specs={n_specs}")

        # --- 5) Tasca size_check assignada (perquè surti al Kanban) ---
        tt = TaskType.objects.filter(code='size_check').first()
        if tt is None:
            raise CommandError("TaskType 'size_check' no existeix (l'ha de crear l'Agus).")
        task, _ = ModelTask.objects.get_or_create(
            model=clone, task_type=tt, defaults={'status': 'Pending', 'assignee': prof})
        self.stdout.write(f"Tasca size_check: pk={task.pk} status={task.status} assignee={task.assignee_id}")

        # --- 6) Verificació d'equivalència de grading vs l'origen (mateix ruleset/base) ---
        src_sf = SizeFitting.objects.filter(model=src).first()
        src_gv = (GradingVersion.objects.filter(size_fitting=src_sf, is_active=True)
                  .order_by('-version_number').first()) if src_sf else None

        def specmap(g):
            return {(s['pom_id'], s['size_label']): s['graded_value_cm']
                    for s in GradedSpec.objects.filter(grading_version=g, is_active=True)
                    .values('pom_id', 'size_label', 'graded_value_cm')} if g else {}

        clone_specs = specmap(gv)
        src_specs = specmap(src_gv)
        diffs = [(k, src_specs.get(k), clone_specs.get(k))
                 for k in sorted(set(clone_specs) | set(src_specs))
                 if _differ(clone_specs.get(k), src_specs.get(k))]
        if not diffs:
            self.stdout.write(self.style.SUCCESS(
                f"grading equivalent ✓ ({len(clone_specs)} specs idèntics a l'origen pk={src.pk})"))
        else:
            self.stdout.write(self.style.WARNING(f"grading DIFEREIX en {len(diffs)}/{len(set(clone_specs)|set(src_specs))} specs:"))
            for (pom_id, size), sv, cv in diffs[:20]:
                self.stdout.write(f"   pom={pom_id} talla={size}: origen={sv} clon={cv}")

        self.stdout.write(self.style.SUCCESS(
            f"OK · clon QA pk={clone.pk} codi={clone.codi_intern} llest per a QA de Size Check."))

    def _purge(self, model):
        """Esborra un clon QA i els seus fills (incloent FKs PROTECT) en ordre segur."""
        from fhort.models_app.models import BaseMeasurement, SizeCheck, SizeCheckLine, MeasurementChangeLog
        from fhort.fitting.models import SizeFitting, GradingVersion, GradedSpec, PieceFitting
        from fhort.tasks.models import ModelTask
        SizeCheckLine.objects.filter(size_check__model=model).delete()
        SizeCheck.objects.filter(model=model).delete()
        sf_ids = list(SizeFitting.objects.filter(model=model).values_list('pk', flat=True))
        GradedSpec.objects.filter(grading_version__size_fitting_id__in=sf_ids).delete()
        GradingVersion.objects.filter(size_fitting_id__in=sf_ids).delete()
        PieceFitting.objects.filter(model=model).delete()
        SizeFitting.objects.filter(model=model).delete()
        MeasurementChangeLog.objects.filter(model=model).delete()
        BaseMeasurement.objects.filter(model=model).delete()
        ModelTask.objects.filter(model=model).delete()
        model.delete()
