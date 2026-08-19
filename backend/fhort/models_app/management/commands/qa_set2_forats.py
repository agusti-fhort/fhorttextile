"""SET-2 · omple els FORATS de cobertura del banc de paritat del motor.

PER QUÈ EXISTEIX. La QA de paritat de T4 compara cel·la a cel·la la sortida del motor abans
i després de tocar-lo. Una paritat només prova els camins que el corpus RECORRE: el cens del
model viu (1320) va donar LINEAR 98 (totes amb break) i FIXED 44, i **zero STEP i zero
overrides**. O sigui que `_apply_rule` a la branca STEP (`pom/services.py:1028-1057`) i
`_load_model_overrides` (`:778`, `:812`) quedaven FORA de la comparació: es podien trencar
sense que el golden se n'assabentés.

Aquest command no afegeix VOLUM, afegeix CAMINS. Un clon amb el mateix perfil que l'origen no
aporta res a una paritat; el que hi aporta és una regla que recorre una branca que ningú més
recorre.

ELS DOS FORATS QUE TAPA:

  1 · **Una regla STEP que TAMBÉ porta `increment_base` i break.** No és un caprici: és el cas
      que el motor tracta a part i que ja ha mossegat. `pom/services.py:1014` diu «STEP NO
      gradua canònic encara que `increment_base` estigui poblat» — o sigui que el guard ha de
      fer caure aquesta regla a la branca STEP i **ignorar** el break. Una regla STEP neta no
      provaria el guard; aquesta sí.

  2 · **Dos `ModelGradingOverride`**, un per sobre i un per sota de la talla base, perquè
      `_load_model_overrides` indexa per tupla i T4 l'ha de fer créixer. Amb zero overrides,
      aquelles dues línies no les cobria cap cel·la del golden.

REPRODUÏBLE A POSTA. La referència de paritat ha de poder tornar-se a construir d'aquí a mesos
per qualsevol sessió, sense dependre d'un script efímer: aquest command i
`clone_model_for_qa --tag '[QA-SET2]'` són la recepta sencera, i estan tots dos al repo.

Ús:
    python manage.py qa_set2_forats --schema fhort --model 1321
    python manage.py qa_set2_forats --schema fhort --model 1321 --dry-run

⚠️ NOMÉS sobre un model de QA: es nega a tocar cap model que no porti la marca al nom.
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django_tenants.utils import schema_context

MARCA_QA = '[QA-'


class Command(BaseCommand):
    help = "Afegeix a un model de QA els camins de motor que el banc de paritat no cobreix (STEP + overrides)."

    def add_arguments(self, parser):
        parser.add_argument('--schema', required=True)
        parser.add_argument('--model', type=int, required=True, help='pk del model de QA')
        parser.add_argument('--dry-run', action='store_true',
                            help='Diu què faria i no escriu res.')

    def handle(self, *args, **o):
        with schema_context(o['schema']):
            self._run(o)

    @transaction.atomic
    def _run(self, o):
        from fhort.models_app.models import (BaseMeasurement, Model,
                                             ModelGradingOverride, ModelGradingRule)
        from fhort.fitting.models import GradingVersion, SizeFitting
        from fhort.pom.services import generate_graded_specs

        model = Model.objects.filter(pk=o['model']).first()
        if not model:
            raise CommandError(f"Model {o['model']} no existeix.")
        # El guard que impedeix que això toqui producció. La marca la posa
        # `clone_model_for_qa --tag`, i sense ella aquest command no fa res.
        if MARCA_QA not in (model.nom_prenda or ''):
            raise CommandError(
                f"El model {model.pk} ({model.codi_intern}) NO porta la marca {MARCA_QA!r} al "
                f"nom_prenda: aquest command només toca bancs de QA.")

        run = [s for s in (model.size_run_model or '').split('·') if s]
        base = model.base_size_label
        if base not in run:
            raise CommandError(f"La talla base {base!r} no és al run {run}.")
        base_idx = run.index(base)
        if base_idx == 0 or base_idx == len(run) - 1:
            raise CommandError(
                f"La base {base!r} és a un extrem del run: no es pot cobrir override per sobre "
                f"I per sota. Cal un model amb la base al mig.")

        # ── FORAT 1 · la regla STEP amb increment_base i break ────────────────────────────
        # Es tria una regla existent i es converteix: així la seva `pom` ja té mesura base
        # (si no en tingués, el motor no n'emetria cap cel·la i el forat seguiria obert).
        poms_amb_base = set(
            BaseMeasurement.objects.filter(model=model, is_active=True)
            .values_list('pom_id', flat=True))
        regla = (ModelGradingRule.objects
                 .filter(model=model, pom_id__in=poms_amb_base)
                 .exclude(logica='STEP').order_by('pom_id').first())
        if regla is None:
            raise CommandError('Cap regla amb mesura base per convertir a STEP.')

        # Deltes per etiqueta: cada talla que NO és la base porta el delta del seu tram.
        # Valors deliberadament IRREGULARS — un STEP uniforme donaria els mateixos números
        # que un LINEAR i no distingiria si el motor s'equivoca de branca.
        valors_step = {}
        for i, label in enumerate(run):
            if i == base_idx:
                continue
            valors_step[label] = 0.7 if i < base_idx else 1.3 if i == base_idx + 1 else 2.1

        # ── FORAT 2 · dos overrides, un a cada banda de la base ───────────────────────────
        # ⚠️ ELS EIXOS SURTEN DE LA FILA BASE, NO D'UN DEFAULT. El motor adreça l'override amb
        # la identitat SENCERA — `(pom_id, capa, instancia, size_label)`, `services.py:252` —
        # de manera que un override escrit amb `instancia=''` sobre un POM la base del qual és
        # 'relaxed' NO CASA MAI: no peta, simplement no s'aplica, i el banc es queda amb el
        # forat obert creient que el tapa. Va passar a la primera passada d'aquest command
        # (POM 920, base `instancia='relaxed'`), i és el mateix mode de fallada silenciosa que
        # tot aquest sprint persegueix.
        bm_ovr = (BaseMeasurement.objects
                  .filter(model=model, is_active=True)
                  .exclude(pom_id=regla.pom_id).order_by('pom_id').first())
        if bm_ovr is None:
            raise CommandError('Cal una segona mesura base per penjar-hi els overrides.')
        pom_ovr = bm_ovr
        talles_ovr = (run[base_idx - 1], run[base_idx + 1])

        if o['dry_run']:
            self.stdout.write(
                f"DRY-RUN · model {model.pk} ({model.codi_intern})\n"
                f"  STEP      → regla pk={regla.pk} pom={regla.pom_id} "
                f"(era {regla.logica}) valors_step={valors_step}\n"
                f"  OVERRIDES → pom={pom_ovr.pom_id} capa={bm_ovr.capa!r} "
                f"instancia={bm_ovr.instancia!r} talles={talles_ovr}\n")
            return

        regla.logica = 'STEP'
        regla.valors_step = valors_step
        # Es DEIXEN poblats a posta: són el parany que el guard de `services.py:1014` ha
        # d'ignorar. Si algú el trenca, aquestes cel·les canvien i el golden ho crida.
        if regla.increment_base is None:
            regla.increment_base = regla.increment or 1
        if not regla.talla_break_label:
            regla.talla_break_label = run[base_idx + 1]
            regla.increment_break = (regla.increment_base or 1)
        regla.save(update_fields=['logica', 'valors_step', 'increment_base',
                                  'talla_break_label', 'increment_break', 'updated_at'])

        creats = []
        for i, talla in enumerate(talles_ovr):
            ovr, _ = ModelGradingOverride.objects.update_or_create(
                model=model, pom_id=pom_ovr.pom_id, size_label=talla,
                capa=bm_ovr.capa, instancia=bm_ovr.instancia, garment=bm_ovr.garment,
                defaults={'value_cm': 40.0 + i, 'motiu': 'QA SET-2 · cobertura de paritat'},
            )
            creats.append((talla, ovr.value_cm))

        # Els specs es regeneren perquè el golden llegeixi el món nou.
        sf = SizeFitting.objects.filter(model=model).order_by('numero').first()
        gv = GradingVersion.objects.filter(size_fitting=sf, is_active=True).first()
        n = generate_graded_specs(sf.pk) if (sf and gv) else 0

        self.stdout.write(self.style.SUCCESS(
            f"OK · model {model.pk} ({model.codi_intern})\n"
            f"  STEP      : regla pk={regla.pk} pom={regla.pom_id} valors_step={valors_step} "
            f"break={regla.talla_break_label} increment_base={regla.increment_base}\n"
            f"  OVERRIDES : pom={pom_ovr.pom_id} {creats}\n"
            f"  specs regenerats: {n}"))
