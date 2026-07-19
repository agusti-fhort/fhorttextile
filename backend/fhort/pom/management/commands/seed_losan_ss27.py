"""Sembra LOSAN SS27 — Fase 1 · FASE B (B1 catàleg v2 + B2 size libraries + B3 contenidors).

IDEMPOTENT (get_or_create/update per CLAU NATURAL) · --dry-run per defecte · tot dins una
sola transaction.atomic() (rollback total si res falla o si és dry-run). Les DADES viuen a
`fhort/pom/seed_data/losan_ss27.py` (config versionable separat; anti-patró seed_brownie).

    python manage.py seed_losan_ss27                 # DRY-RUN (no escriu)
    python manage.py seed_losan_ss27 --no-dry-run    # escriu
    python manage.py seed_losan_ss27 --schema fhort  # (default fhort)

NO toca: POM-maps dels items moguts · rulesets 104/111 · GIRL_LOS_02/_03 (neteja = command
a part) · GIRL_LOS_01 / MAN_LOS_01 (ja correctes) · canònic/BRW/FTT.
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django_tenants.utils import schema_context

from fhort.pom.models import (GarmentGroup, GarmentType, SizeSystem, SizeDefinition,
                              GradingRuleSet, FitType, Target)
from fhort.tasks.models import GarmentTypeItem, Customer
from fhort.pom.seed_data import losan_ss27 as CFG


class Command(BaseCommand):
    help = 'Sembra LOSAN SS27 (Fase 1 B): catàleg v2 + size libraries + contenidors grading.'

    def add_arguments(self, parser):
        parser.add_argument('--no-dry-run', action='store_true',
                            help='Escriu a BD. Sense aquest flag, només simula (dry-run).')
        parser.add_argument('--schema', default=CFG.TENANT,
                            help=f'Schema tenant (default {CFG.TENANT}).')

    def handle(self, *args, **opts):
        dry = not opts['no_dry_run']
        schema = opts['schema']
        self.log = []
        head = 'DRY-RUN (cap escriptura)' if dry else 'ESCRIVINT'
        self.stdout.write(self.style.WARNING(f'=== seed_losan_ss27 · schema={schema} · {head} ==='))

        try:
            with schema_context(schema), transaction.atomic():
                self._b1_catalog()
                self._b2_size_libraries()
                self._b3_containers()
                self._counts()
                if dry:
                    transaction.set_rollback(True)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'STOP · {type(e).__name__}: {e}'))
            raise

        for line in self.log:
            self.stdout.write(line)
        self.stdout.write(self.style.SUCCESS(
            f'\n=== FET ({head}) — {"res escrit, revisa el pla" if dry else "canvis aplicats"} ==='))

    # ── B1 ──────────────────────────────────────────────────────────────────
    def _b1_catalog(self):
        self.log.append('\n── BLOC B1 · Catàleg v2 ──')
        # 1. Grups
        for codi, nom in CFG.NEW_GROUPS:
            g, created = GarmentGroup.objects.get_or_create(codi=codi, defaults={'nom': nom})
            self.log.append(f'  [group] {codi} · {"CREAT" if created else "ja existeix"}')
        # 2+5. Types
        for codi_client, nom_client, grup in CFG.NEW_TYPES:
            t, created = GarmentType.objects.get_or_create(
                codi_client=codi_client,
                defaults={'nom_client': nom_client, 'nom_en': nom_client, 'grup': grup, 'actiu': True})
            self.log.append(f'  [type]  {codi_client} (grup {grup}) · {"CREAT" if created else "ja existeix"}')
        # 3. Moviments d'items
        for code, type_codi, compl in CFG.ITEM_MOVES:
            it = GarmentTypeItem.objects.filter(code=code).first()
            if not it:
                raise CommandError(f'Item a moure NO existeix: {code}')
            dest = GarmentType.objects.get(codi_client=type_codi)
            before = it.garment_type.codi_client if it.garment_type_id else '?'
            npoms = it.pom_maps.count()
            it.garment_type = dest
            it.complexity_order = compl
            it.save(update_fields=['garment_type', 'complexity_order'])
            self.log.append(f'  [move]  {code}: {before} → {type_codi} (compl {compl}) · POMs intactes={npoms}')
        # 4+5+6. Items nous
        for code, name, type_codi, compl in CFG.NEW_ITEMS:
            dest = GarmentType.objects.get(codi_client=type_codi)
            it, created = GarmentTypeItem.objects.get_or_create(
                garment_type=dest, code=code,
                defaults={'name': name, 'complexity_order': compl})
            self.log.append(f'  [item]  {type_codi}/{code} ("{name}") · {"CREAT" if created else "ja existeix"}')
        # 7. Desactivar types buits
        for codi in CFG.DEACTIVATE_TYPES_WHEN_EMPTY:
            t = GarmentType.objects.filter(codi_client=codi).first()
            if not t:
                self.log.append(f'  [deact] {codi}: no existeix (skip)'); continue
            n = t.items.count()
            if n == 0:
                if t.actiu:
                    t.actiu = False
                    t.save(update_fields=['actiu'])
                    self.log.append(f'  [deact] {codi}: BUIT → actiu=False')
                else:
                    self.log.append(f'  [deact] {codi}: ja actiu=False (skip)')
            else:
                self.log.append(f'  [deact] {codi}: TÉ {n} items → NO desactivat (guard)')

    # ── B2 ──────────────────────────────────────────────────────────────────
    def _b2_size_libraries(self):
        self.log.append('\n── BLOC B2 · Size libraries ──')
        for s in CFG.SIZE_SYSTEMS:
            sys_obj, created = SizeSystem.objects.get_or_create(
                codi=s['codi'],
                defaults={'nom': s['nom'], 'base_unit': s['base_unit'],
                          'customer_codi': CFG.CUSTOMER_CODI, 'actiu': True, 'norma_ref': ''})
            # targets M2M idempotent
            tgts = list(Target.objects.filter(codi__in=s['targets']))
            missing = set(s['targets']) - {t.codi for t in tgts}
            if missing:
                raise CommandError(f'Targets inexistents per {s["codi"]}: {missing}')
            sys_obj.targets.set(tgts)
            # talles
            n_new = 0
            for ordre, etiqueta in enumerate(s['sizes'], start=1):
                sd, sd_created = SizeDefinition.objects.get_or_create(
                    size_system=sys_obj, etiqueta=etiqueta,
                    defaults={'ordre': ordre, 'valor_numeric': None})
                if not sd_created and sd.ordre != ordre:
                    sd.ordre = ordre
                    sd.save(update_fields=['ordre'])
                n_new += int(sd_created)
            self.log.append(
                f'  [system] {s["codi"]} · {"CREAT" if created else "ja existeix"} · '
                f'targets={",".join(s["targets"])} · {len(s["sizes"])} talles ({n_new} noves)')

    # ── B3 ──────────────────────────────────────────────────────────────────
    def _b3_containers(self):
        self.log.append('\n── BLOC B3 · Contenidors de grading (identitat + forma; sense regles) ──')
        los = Customer.objects.filter(codi=CFG.CUSTOMER_CODI).first()
        if not los:
            raise CommandError(f'Customer {CFG.CUSTOMER_CODI} no existeix.')
        fit = FitType.objects.filter(codi=CFG.FIT_TYPE_CODI).first()
        if not fit:
            raise CommandError(f'FitType {CFG.FIT_TYPE_CODI} no existeix.')

        mon = dict(CFG.EXISTING_SYSTEM_MON)
        mon.update({s['codi']: s['mon'] for s in CFG.SIZE_SYSTEMS})

        for ss_codi, item_code, forma, font in CFG.CONTAINERS:
            ss = SizeSystem.objects.filter(codi=ss_codi).first()
            if not ss:
                raise CommandError(f'SizeSystem {ss_codi} no existeix (contenidor {item_code}).')
            item = GarmentTypeItem.objects.filter(code=item_code).first()
            if not item:
                raise CommandError(f'GarmentTypeItem {item_code} no existeix (contenidor {ss_codi}).')
            nom = f'LOS {mon.get(ss_codi, ss_codi)} {item_code} SS27'
            rs, created = GradingRuleSet.objects.get_or_create(
                customer=los, size_system=ss, garment_type_item=item, fit_type=fit,
                origen=GradingRuleSet.ORIGEN_CLIENT_RUN,
                defaults={'nom': nom, 'actiu': True})
            self.log.append(
                f'  [container] {nom} · {"CREAT" if created else "ja existeix"} · '
                f'forma="{forma}" · font="{font}" · regles={rs.regles.count()}')

    # ── recomptes ─────────────────────────────────────────────────────────────
    def _counts(self):
        self.log.append('\n── RECOMPTES (dins la transacció) ──')
        # GarmentType.grup és CharField (codi de GarmentGroup), no FK → grups amb contingut =
        # grups referenciats per algun type actiu.
        grups_amb_types = set(GarmentType.objects.filter(actiu=True).values_list('grup', flat=True))
        amb_contingut = GarmentGroup.objects.filter(codi__in=grups_amb_types).count()
        self.log.append(f'  GarmentGroup amb contingut (types actius)={amb_contingut} '
                        f'(total {GarmentGroup.objects.count()})')
        self.log.append(f'  GarmentType total={GarmentType.objects.count()} '
                        f'actius={GarmentType.objects.filter(actiu=True).count()}')
        self.log.append(f'  GarmentTypeItem total={GarmentTypeItem.objects.count()}')
        self.log.append(f'  SizeSystem total={SizeSystem.objects.count()}')
        self.log.append(f'  GradingRuleSet total={GradingRuleSet.objects.count()} '
                        f'CLIENT_RUN LOS={GradingRuleSet.objects.filter(origen=GradingRuleSet.ORIGEN_CLIENT_RUN, customer__codi=CFG.CUSTOMER_CODI).count()}')
