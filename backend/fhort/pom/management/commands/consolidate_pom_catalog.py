"""Consolidació del catàleg POM LOSAN — PAS 4B (gate 4A validat).

3 fases (concern separat, --phase): `fusio` · `translate` · `maps`. --dry-run per defecte.
Config validada a `fhort/pom/seed_data/consolidate_pom_los.py` + CSV de traduccions.
Idempotent. Motor NO tocat. Els 72 prims sense àlies LOS queden INTACTES.

    python manage.py consolidate_pom_catalog --phase fusio               # DRY-RUN
    python manage.py consolidate_pom_catalog --phase fusio --no-dry-run
    python manage.py consolidate_pom_catalog --phase translate [--no-dry-run]
    python manage.py consolidate_pom_catalog --phase maps [--no-dry-run]
"""
import csv
import re
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction, IntegrityError

from django_tenants.utils import schema_context
from fhort.pom.models import POMMaster, POMGlobal, CustomerPOMAlias
from fhort.tasks.models import Customer, GarmentTypeItem
from fhort.pom.models import GarmentPOMMap
from fhort.pom.seed_data import consolidate_pom_los as CFG

SEED_DIR = Path(__file__).resolve().parents[2] / 'seed_data'


def variants(a):
    out = [a, a.replace('.', ''),
           re.sub(r'^([A-Z]+)(\d)', r'\1.\2', a),
           re.sub(r'^([A-Z])([A-Z]+)(\d)', r'\1.\2\3', a)]
    s = []
    for x in out:
        if x not in s:
            s.append(x)
    return s


class Command(BaseCommand):
    help = 'Consolida el catàleg POM LOSAN (fusio/translate/maps).'

    def add_arguments(self, parser):
        parser.add_argument('--phase', required=True, choices=['fusio', 'translate', 'maps'])
        parser.add_argument('--no-dry-run', action='store_true')
        parser.add_argument('--schema', default=CFG.TENANT)

    def handle(self, *args, **opts):
        self.dry = not opts['no_dry_run']
        head = 'DRY-RUN' if self.dry else 'ESCRIVINT'
        phase = opts['phase']
        self.stdout.write(self.style.WARNING(f'=== consolidate_pom_catalog · {phase} · {head} ==='))
        try:
            with schema_context(opts['schema']), transaction.atomic():
                self.los = Customer.objects.get(codi=CFG.CUSTOMER_CODI)
                {'fusio': self._fusio, 'translate': self._translate, 'maps': self._maps}[phase]()
                if self.dry:
                    transaction.set_rollback(True)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'STOP · {type(e).__name__}: {e}'))
            raise
        self.stdout.write(self.style.SUCCESS(f'=== FET ({head}) ==='))

    def _prim_by_alias_or_codi(self, code):
        """Resol un prim LOS a partir d'un codi CSV: àlies LOS primer, després codi del prim."""
        for v in variants(code):
            a = CustomerPOMAlias.objects.filter(customer=self.los, client_code=v, pom__isnull=False).first()
            if a:
                return a.pom
        for v in variants(code):
            m = POMMaster.objects.filter(codi_client=v).first()
            if m:
                return m
        return None

    # ── FASE FUSIÓ ───────────────────────────────────────────────────────────
    def _fusio(self):
        moved_total = coll_total = fused = 0
        for codi, dest_codi, nomg in CFG.FUSIONS:
            dest = POMMaster.objects.filter(codi_client=dest_codi, pom_global__isnull=False).first()
            if not dest or dest.garment_maps.count() == 0:
                raise CommandError(f'Destí canònic ric no vàlid: {dest_codi}')
            prims = [m for m in POMMaster.objects.filter(codi_client=codi, pom_global__isnull=True)
                     if m.garment_maps.count() == 0 and nomg in m.nom_client.upper()
                     and CustomerPOMAlias.objects.filter(customer=self.los, pom=m).exists()]
            if not prims:
                self.stdout.write(f'  [{codi}→{dest_codi}] cap prim (ja fusionat?) — skip')
                continue
            for prim in prims:
                mv, cl = self._fuse_one(prim, dest)
                moved_total += mv
                coll_total += cl
                fused += 1
        self.stdout.write(f'\n  RESUM fusió: {fused} prims fusionats · {moved_total} refs mogudes · '
                          f'{coll_total} col·lisions (deixades al prim)')

    def _fuse_one(self, prim, dest):
        # (S'executa sempre; en dry-run l'outer atomic fa rollback → detecta col·lisions de veritat.)
        moved = coll = 0
        details = []
        # re-apuntar CustomerPOMAlias (conserva client_code). Unique (customer,client_code) intacte.
        moved += CustomerPOMAlias.objects.filter(pom=prim).update(pom=dest)
        # moure refs de mesura via .update() per fila (evita save() — MeasurementChangeLog és
        # append-only — i respecta unique: IntegrityError = col·lisió → es queda al prim).
        for rel in CFG.FUSIO_MOVE_RELS:
            for obj in list(getattr(prim, rel).all()):
                try:
                    with transaction.atomic():
                        type(obj).objects.filter(pk=obj.pk).update(pom=dest)
                    moved += 1
                except IntegrityError:
                    coll += 1
        # esborrar GradedSpec (output pur del motor, regenerable)
        for rel in CFG.FUSIO_DELETE_RELS:
            n = getattr(prim, rel).count()
            if n:
                getattr(prim, rel).all().delete()
                details.append(f'{rel}✗{n}')
        # desactivar prim (regles_grading PROTECT; s'esborren al PAS 3)
        rg = prim.regles_grading.count()
        POMMaster.objects.filter(pk=prim.pk).update(actiu=False)
        self.stdout.write(f'  [id{prim.id} {prim.codi_client!r} "{prim.nom_client[:22]}"] → {dest.codi_client} · '
                          f'mogudes={moved} coll={coll} {" ".join(details)} regles_grading={rg} → actiu=False')
        return moved, coll

    # ── FASE TRANSLATE ───────────────────────────────────────────────────────
    def _translate(self):
        rows = list(csv.DictReader(open(SEED_DIR / CFG.CSV_TRAD, encoding='utf-8')))
        done = 0
        no_prim = []
        seen = set()
        for r in rows:
            code = r['codi'].strip()
            prim = self._prim_by_alias_or_codi(code)
            # només prims LOS traduïbles: sense pom_global o amb el nostre LOSPOM-
            if (not prim or prim.id in seen
                    or not CustomerPOMAlias.objects.filter(customer=self.los, pom=prim).exists()
                    or (prim.pom_global_id and not prim.pom_global.codi.startswith('LOSPOM-'))
                    or prim.garment_maps.count() > 0):
                no_prim.append(code)
                continue
            seen.add(prim.id)
            en = r['descripcio_en_fitxa'].strip()
            ca = r['traduccio_ca'].strip()
            gcodi = f'LOSPOM-{prim.id}'
            if not self.dry:
                pg, _ = POMGlobal.objects.get_or_create(
                    codi=gcodi, defaults={'nom_en': en, 'nom_ca': ca, 'categoria': 'LOSAN'})
                pg.nom_en, pg.nom_ca, pg.categoria = en, ca, 'LOSAN'
                pg.save(update_fields=['nom_en', 'nom_ca', 'categoria'])
                prim.pom_global = pg
                prim.save(update_fields=['pom_global'])
            done += 1
            self.stdout.write(f'  [{code}] → prim id{prim.id} {prim.codi_client!r} · ca="{ca}"')
        # prims COMPLETAR sense traducció
        fus_ids = self._fusion_prim_ids()
        prims = [m for m in POMMaster.objects.filter(pom_global__isnull=True)
                 if m.garment_maps.count() == 0
                 and CustomerPOMAlias.objects.filter(customer=self.los, pom=m).exists()]
        completar = [m for m in prims if m.id not in fus_ids]
        sense = [f'{m.codi_client}(id{m.id})' for m in completar if m.id not in seen]
        self.stdout.write(f'\n  RESUM translate: {done} traduïts · {len(no_prim)} files CSV sense prim · '
                          f'{len(sense)} prims COMPLETAR SENSE traducció (pendents gate)')
        self.stdout.write(f'  CSV sense prim aplicable: {no_prim}')
        self.stdout.write(f'  COMPLETAR sense traducció: {sense}')

    def _fusion_prim_ids(self):
        ids = set()
        for codi, _dest, nomg in CFG.FUSIONS:
            for m in POMMaster.objects.filter(codi_client=codi):
                if nomg in m.nom_client.upper() and CustomerPOMAlias.objects.filter(customer=self.los, pom=m).exists():
                    ids.add(m.id)
        return ids

    # ── FASE MAPS ────────────────────────────────────────────────────────────
    def _maps(self):
        self.stdout.write('  ⚠ vault GRADING_SOURCES_LOSAN.md ABSENT en aquest host → només '
                          'els exemples explícits del brief; la resta queda PENDENT.')
        created = 0
        for code, items in CFG.MAPS_EXPLICIT:
            prim = self._prim_by_alias_or_codi(code)
            if not prim:
                self.stdout.write(f'  [{code}] prim inexistent — skip')
                continue
            for it_code in items:
                it = GarmentTypeItem.objects.filter(code=it_code).first()
                if not it:
                    self.stdout.write(f'  [{code}] item {it_code} inexistent — skip')
                    continue
                if not self.dry:
                    _, c = GarmentPOMMap.objects.get_or_create(
                        garment_type_item=it, pom=prim,
                        defaults={'obligatori': False, 'is_key': False, 'nivell': 'O',
                                  'pendent_revisio': True})
                else:
                    c = not GarmentPOMMap.objects.filter(garment_type_item=it, pom=prim).exists()
                created += int(bool(c))
                self.stdout.write(f'  [{code}] id{prim.id} {prim.codi_client!r} → {it_code} '
                                  f'· {"CREAT" if c else "ja existeix"}')
        # pendents (tots els COMPLETAR no mapats aquí)
        self.stdout.write(f'\n  RESUM maps: {created} GarmentPOMMap creats (exemples explícits). '
                          f'La resta de COMPLETAR queda PENDENT del vault (informe).')
