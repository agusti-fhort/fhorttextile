"""
crea_sizing_profiles — declara ÀMBIT de catàleg: «aquesta família aplica a aquest target amb
aquesta construcció i aquest fit, sobre aquesta escala».

Per què existeix: la compatibilitat target↔família del wizard es llegeix de `SizingProfile`
(`pom/views.py:121-132` → `garment_type-s/?target=`). Una família sense perfil per a un target
és una família INVISIBLE al pas Peça. Fins avui no hi havia cap manera de declarar-ho: no hi ha
endpoint de creació de `SizingProfile` (les rutes de `tasks/urls.py:165-167` són totes GET) i els
únics creadors eren l'import de size-map i comandes de seed d'un cas concret.

Des de C3 (`pom/0045`) el perfil pot néixer SENSE graduació: declarar àmbit ja no obliga a
inventar-se un joc de regles. `--grading-rule-set` és opcional i és el que converteix el perfil en
un SUGGERIMENT (el wizard de model el llegeix per proposar graduació).

IDEMPOTENT: la clau és la combinació dels 5 eixos (target, família, construcció, fit, escala). Si
ja existeix un perfil per a la combinació, no en crea cap altre i no toca el que hi ha —
els perfils existents amb ruleset són suggeriments legítims i no es degraden mai.

DRY-RUN PER DEFECTE: sense `--apply` no escriu res; ensenya exactament què faria.

Exemples:
  # el forat de la dessuadora (àmbit pur, sense graduació)
  python manage.py crea_sizing_profiles --target WOMAN --familia SWEATSHIRTS_MIDLAYERS \\
      --construccio KNIT --fit REGULAR --size-system ALPHA_EU_W
  python manage.py crea_sizing_profiles ... --apply

  # diversos targets d'un cop, amb suggeriment de graduació
  python manage.py crea_sizing_profiles --target WOMAN,MAN --familia KNIT_SWEATERS \\
      --construccio KNIT --fit REGULAR --size-system ALPHA_EU_W --grading-rule-set 79 --apply
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django_tenants.utils import schema_context


class Command(BaseCommand):
    help = ("Crea SizingProfiles (àmbit de catàleg target×família×construcció×fit×escala). "
            "Idempotent; dry-run per defecte.")

    def add_arguments(self, parser):
        parser.add_argument('--schema', default='fhort',
                            help='Schema del tenant on escriure (default: fhort).')
        parser.add_argument('--target', required=True,
                            help="Codi/s de Target, separats per comes (p.ex. WOMAN o WOMAN,MAN).")
        parser.add_argument('--familia', required=True,
                            help="`codi_client` del GarmentType (p.ex. SWEATSHIRTS_MIDLAYERS).")
        parser.add_argument('--construccio', required=True,
                            help="Codi de ConstructionType (WOVEN/KNIT/STRETCH_KNIT/TECHNICAL).")
        parser.add_argument('--fit', required=True,
                            help="Codi de FitType (REGULAR/SLIM/...).")
        parser.add_argument('--size-system', required=True,
                            help="Codi de SizeSystem: l'escala on viu la combinació (NOT NULL).")
        parser.add_argument('--grading-rule-set', default=None,
                            help="OPCIONAL: id del GradingRuleSet a suggerir. Sense això, el "
                                 "perfil declara àmbit i prou (C3).")
        parser.add_argument('--apply', action='store_true',
                            help="Escriu de veritat. Sense aquest flag és una simulació.")

    def handle(self, *args, **options):
        schema = options['schema']
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"crea_sizing_profiles · schema={schema} · "
            f"{'APLICANT' if options['apply'] else 'DRY-RUN (res no s escriu)'}"))
        with schema_context(schema):
            self._run(options)

    def _run(self, o):
        from fhort.pom.models import (ConstructionType, FitType, GarmentType, GradingRuleSet,
                                      SizeSystem, SizingProfile, Target)

        familia = GarmentType.objects.filter(codi_client=o['familia']).first()
        if familia is None:
            raise CommandError(f"GarmentType codi_client={o['familia']!r} no existeix.")
        construccio = ConstructionType.objects.filter(codi=o['construccio']).first()
        if construccio is None:
            raise CommandError(f"ConstructionType codi={o['construccio']!r} no existeix.")
        fit = FitType.objects.filter(codi=o['fit']).first()
        if fit is None:
            raise CommandError(f"FitType codi={o['fit']!r} no existeix.")
        size_system = SizeSystem.objects.filter(codi=o['size_system']).first()
        if size_system is None:
            raise CommandError(f"SizeSystem codi={o['size_system']!r} no existeix.")

        rule_set = None
        if o['grading_rule_set']:
            rule_set = GradingRuleSet.objects.filter(pk=o['grading_rule_set']).first()
            if rule_set is None:
                raise CommandError(f"GradingRuleSet id={o['grading_rule_set']!r} no existeix.")
            # Coherència d'escala: suggerir regles d'un altre sistema de talles no vol dir res.
            if rule_set.size_system_id and rule_set.size_system_id != size_system.id:
                raise CommandError(
                    f"El ruleset «{rule_set.nom}» és del sistema {rule_set.size_system_id} i el "
                    f"perfil del {size_system.id}: un suggeriment d'una altra escala no aplica.")

        codis = [c.strip() for c in o['target'].split(',') if c.strip()]
        targets = []
        for codi in codis:
            tg = Target.objects.filter(codi=codi).first()
            if tg is None:
                raise CommandError(f"Target codi={codi!r} no existeix.")
            targets.append(tg)

        self.stdout.write(
            f"  família={familia.codi_client} · construcció={construccio.codi} · fit={fit.codi} · "
            f"escala={size_system.codi} · graduació="
            f"{rule_set.nom if rule_set else '— (àmbit pur)'}")

        creats, existents = [], []
        with transaction.atomic():
            for tg in targets:
                # Clau d'idempotència = els 5 eixos. El ruleset NO hi entra: dos perfils per a la
                # mateixa combinació serien ambigüitat de cascada (R20), no riquesa.
                existent = SizingProfile.objects.filter(
                    target=tg, garment_type=familia, construction=construccio,
                    fit_type=fit, size_system=size_system,
                ).first()
                if existent is not None:
                    existents.append((tg.codi, existent))
                    self.stdout.write(self.style.WARNING(
                        f"  = {tg.codi}: ja existeix (perfil {existent.id}, graduació="
                        f"{existent.grading_rule_set_id or '—'}). No es toca."))
                    continue

                if o['apply']:
                    nou = SizingProfile.objects.create(
                        target=tg, garment_type=familia, construction=construccio,
                        fit_type=fit, size_system=size_system, grading_rule_set=rule_set,
                        is_default=True,
                    )
                    creats.append((tg.codi, nou.id))
                    self.stdout.write(self.style.SUCCESS(f"  + {tg.codi}: perfil {nou.id} creat."))
                else:
                    creats.append((tg.codi, None))
                    self.stdout.write(self.style.SUCCESS(f"  + {tg.codi}: es crearia."))

            if not o['apply']:
                transaction.set_rollback(True)

        self.stdout.write(self.style.MIGRATE_HEADING(
            f"  → {len(creats)} {'creats' if o['apply'] else 'a crear'} · "
            f"{len(existents)} ja existents"))
        if not o['apply'] and creats:
            self.stdout.write("  (torna-hi amb --apply per escriure-ho)")
