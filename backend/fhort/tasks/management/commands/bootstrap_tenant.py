"""
Management command: bootstrap_tenant
P-BOOT — un tenant nou neix VIU: se li copia el catàleg des d'un tenant origen.

    manage.py bootstrap_tenant <schema> --from fhort [--dry-run]

Un schema acabat de provisionar (django-tenants, `auto_create_schema`) neix amb les
TAULES però sense CATÀLEG: només `TaskType` (14, migració tasks/0025) i el self-`Customer`
(tasks/0020) hi neixen sols. Tota la resta —catàlegs-fulla inclosos— està buida.
Vegeu `docs/diagnosis/DIAGNOSI_PBOOT_CENS_COPIA.md`.

ON VIU AQUESTA COMANDA I PER QUÈ
`tasks` ja depèn de `pom` (`GarmentTypeItem.garment_type → pom.GarmentType`) i d'`accounts`
(`TimeSeed.updated_by → accounts.UserProfile`). Posar-la aquí no crea cap import nou en la
direcció contrària. NO va a `backoffice`: és app SHARED (public) i no ha de conèixer el
detall del catàleg d'un tenant (llei DUES FACTURACIONS SEPARADES / fronteres d'app).

LLEIS QUE APLICA
- **Idempotent-additiva.** `update_or_create` per clau natural. MAI `delete`.
- **Remapeig de FK per clau natural entre schemes**, mai per pk: els pks difereixen entre
  schemes. Es manté un mapa `pk_origen → pk_destí` per model (patró `load_map_inline`, no
  `clone_model_for_qa`, que reusa FK per valor i només val intra-schema).
- **FK a entitat del tenant origen NO viatgen** (`customer`, `updated_by`, `modified_by_id`):
  queden NULL, i es reporta **quantes** (no en silenci).
- **`TaskType` NO es copia** (neix sol). `TaskTimeEstimate.task_type` es re-resol per `code`
  al destí (llei G9: la referència canònica és el slug, mai el pk). `TimeSeed.key` ja és un
  string amb el `code`.
- **Welford net**: de `TaskTimeEstimate` només viatja `estimated_minutes`; `n`/`mean_minutes`/
  `m2` són història d'ús del tenant origen i neixen a zero.
- **Auto-FK en 2 passades** (`SizeSystem.parent`, `GradingRuleSet.parent_version`,
  `SizingProfile.parent_profile`): es creen amb `parent=NULL` i es resolen al final.
- **M2M** (`SizeSystem.targets`, `GarmentType.targets_recomanats`, `GradingRuleSet.targets`)
  es copien remapejant, després de la 1a passada.

En acabar verd: propaga la identitat (D7) i tanca `onboarding → actiu` (DC-6).
Si alguna peça falla: el tenant es queda en `onboarding`, es reporta què falta i se surt
amb codi != 0. La comanda és re-executable (idempotent), així que el tenant és reprenible.
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django_tenants.utils import schema_context, get_tenant_model

# Estratègies de resolució de FK:
MAP = 'map'          # remapejar via el mapa pk_origen → pk_destí del model relacionat
NULL = 'null'        # FK a entitat del tenant origen: no viatja
DEFER = 'defer'      # auto-FK: NULL a la 1a passada, resolta a la 2a
NATURAL = 'natural'  # resoldre al destí per clau natural (el model NO es copia)


def _spec():
    """Ordre topològic (cens B5 + els 7 catàlegs-fulla, verificats buits en un tenant verge)."""
    from fhort.pom.models import (
        BodyMeasurementISO, POMCategory, GarmentGroup, Target, FitType, ConstructionType,
        SizeSystem, SizeDefinition, POMGlobal, GarmentTypeGlobal, GarmentType, POMMaster,
        GradingRuleSet, GarmentPOMMap, GradingRule, SizingProfile,
    )
    from fhort.tasks.models import GarmentTypeItem, TaskTimeEstimate, TimeSeed, TaskType

    return [
        # (model, clau natural, {camp_fk: estratègia}, m2m, transform)
        (BodyMeasurementISO, ('codi_intern',), {}, (), None),
        (POMCategory,        ('codi',), {}, (), None),
        (GarmentGroup,       ('codi',), {}, (), None),
        (Target,             ('codi',), {}, (), None),
        (FitType,            ('codi',), {}, (), None),
        (ConstructionType,   ('codi',), {}, (), None),
        (SizeSystem,         ('codi',), {'parent': DEFER}, ('targets',), None),
        (SizeDefinition,     ('size_system', 'etiqueta'), {}, (), None),
        (POMGlobal,          ('codi',), {}, (), None),
        (GarmentTypeGlobal,  ('codi',), {}, (), None),
        # codi_client: 19/19 distints a fhort. No hi ha constraint (cens: "sense clau natural").
        (GarmentType,        ('codi_client',), {}, ('targets_recomanats',), None),
        # CORRECCIÓ AL CENS: pom_global NO és 1:1 (126 distints / 170 files). La clau és codi_client.
        (POMMaster,          ('codi_client',), {}, (), None),
        (GradingRuleSet,     ('nom',), {'customer': NULL, 'parent_version': DEFER}, ('targets',), None),
        (GarmentTypeItem,    ('garment_type', 'code'), {}, (), None),
        (GarmentPOMMap,      ('garment_type_item', 'pom'), {}, (), None),
        (GradingRule,        ('rule_set', 'pom'), {}, (), None),
        # (GradingException) — jubilada G6/1a: model retirat, 0 files. No hi ha res a copiar.
        (SizingProfile,      ('target', 'garment_type', 'construction', 'fit_type',
                              'size_system', 'version'),
                             {'customer': NULL, 'modified_by_id': NULL, 'parent_profile': DEFER},
                             (), None),
        (TaskTimeEstimate,   ('garment_type_item', 'task_type'),
                             {'task_type': (NATURAL, TaskType, 'code')}, (), 'welford_zero'),
        (TimeSeed,           ('scope', 'key'), {'updated_by': NULL}, (), None),
    ]


class Piece:
    """Comptadors d'una peça."""
    def __init__(self, name):
        self.name, self.created, self.updated, self.skipped, self.nulled = name, 0, 0, 0, 0


class Command(BaseCommand):
    help = 'Copia el catàleg d\'un tenant origen a un tenant nou perquè neixi operatiu.'

    def add_arguments(self, parser):
        parser.add_argument('schema', type=str, help='Schema del tenant destí.')
        parser.add_argument('--from', dest='source', type=str, default='fhort',
                            help='Schema del tenant origen (default: fhort).')
        parser.add_argument('--dry-run', action='store_true',
                            help='Recompte del que faria, sense escriure res.')

    # ------------------------------------------------------------------ utils

    def _concrete(self, model):
        """Camps concrets a copiar (sense pk, sense M2M). FK → attname (`x_id`)."""
        return [f for f in model._meta.fields if not f.primary_key]

    def _read_source(self, model, source):
        """Llegeix les files de l'origen com a dicts {field_name: valor|pk_origen}."""
        with schema_context(source):
            rows = []
            for obj in model.objects.all().order_by('pk'):
                row = {'__pk__': obj.pk}
                for f in self._concrete(model):
                    row[f.name] = getattr(obj, f.attname) if f.is_relation else getattr(obj, f.name)
                rows.append(row)
            # M2M i les claus naturals que travessen FK necessiten els valors naturals de
            # l'origen: es resolen més avall via els mapes, així que aquí n'hi ha prou amb els pks.
            return rows

    def _read_m2m(self, model, field, source):
        with schema_context(source):
            return {o.pk: list(getattr(o, field).values_list('pk', flat=True))
                    for o in model.objects.all()}

    def _natural_lookup(self, source, model, attr):
        """{pk_origen: valor_natural} per a models que NO es copien (p.ex. TaskType.code)."""
        with schema_context(source):
            return dict(model.objects.values_list('pk', attr))

    # ------------------------------------------------------------------ còpia

    def _copy_piece(self, model, key_fields, fk_strat, m2m_fields, transform,
                    source, maps, natural_cache, deferred):
        p = Piece(model.__name__)
        rows = self._read_source(model, source)
        if not rows:
            return p, []

        # Pre-càrrega dels lookups naturals dels models no copiats.
        for fname, strat in fk_strat.items():
            if isinstance(strat, tuple) and strat[0] == NATURAL:
                _, rel_model, attr = strat
                natural_cache.setdefault(rel_model, self._natural_lookup(source, rel_model, attr))

        pending_parents = []
        for row in rows:
            src_pk = row['__pk__']
            values, skip = {}, None

            # `values` es construeix SEMPRE amb `attname` ('x_id' per a les FK): és el que
            # update_or_create espera quan es passen pks en lloc d'instàncies.
            for f in self._concrete(model):
                name, att = f.name, f.attname
                strat = fk_strat.get(name, MAP if f.is_relation else None)

                if not f.is_relation:
                    # `modified_by_id` de SizingProfile NO és una FK declarada: és un enter amb
                    # l'id d'un UserProfile del tenant origen. Sense aquest guard viatjaria.
                    if strat is NULL:
                        if row[name] is not None:
                            p.nulled += 1
                        values[att] = None
                    else:
                        values[att] = row[name]
                    continue

                old = row[name]
                if strat is NULL:
                    if old is not None:
                        p.nulled += 1
                    values[att] = None
                elif strat is DEFER:
                    if old is not None:
                        pending_parents.append((src_pk, name, old))
                    values[att] = None
                elif isinstance(strat, tuple) and strat[0] == NATURAL:
                    if old is None:
                        values[att] = None
                        continue
                    _, rel_model, attr = strat
                    nat = natural_cache[rel_model].get(old)
                    dst = rel_model.objects.filter(**{attr: nat}).first() if nat else None
                    if dst is None:
                        skip = f"{name}: {rel_model.__name__}({attr}={nat!r}) no existeix al destí"
                        break
                    values[att] = dst.pk
                else:  # MAP
                    if old is None:
                        values[att] = None
                        continue
                    rel = f.related_model
                    new = maps.get(rel, {}).get(old)
                    if new is None:
                        skip = f"{name}: {rel.__name__} pk={old} no s'ha copiat"
                        break
                    values[att] = new

            if skip:
                p.skipped += 1
                self.stdout.write(self.style.WARNING(f"    [skip] {model.__name__} pk={src_pk}: {skip}"))
                continue

            if transform == 'welford_zero':
                values['n'], values['mean_minutes'], values['m2'] = 0, 0, 0

            lookup = {}
            for k in key_fields:
                att = model._meta.get_field(k).attname
                lookup[att] = values.pop(att)

            obj, created = model.objects.update_or_create(**lookup, defaults=values)
            maps.setdefault(model, {})[src_pk] = obj.pk
            p.created += int(created)
            p.updated += int(not created)

        if pending_parents:
            deferred.append((model, pending_parents))

        # M2M: després que totes les files existeixin.
        for field in m2m_fields:
            rel_model = model._meta.get_field(field).related_model
            src_m2m = self._read_m2m(model, field, source)
            for src_pk, rel_pks in src_m2m.items():
                dst_pk = maps.get(model, {}).get(src_pk)
                if dst_pk is None:
                    continue
                new_rel = [maps[rel_model][r] for r in rel_pks if r in maps.get(rel_model, {})]
                if new_rel:
                    getattr(model.objects.get(pk=dst_pk), field).set(new_rel)

        return p, pending_parents

    def _resolve_deferred(self, deferred, maps):
        total = 0
        for model, pending in deferred:
            for src_pk, field, old_parent_pk in pending:
                dst_pk = maps[model].get(src_pk)
                new_parent = maps[model].get(old_parent_pk)
                if dst_pk is None or new_parent is None:
                    continue
                model.objects.filter(pk=dst_pk).update(**{f'{field}_id': new_parent})
                total += 1
        return total

    # ------------------------------------------------------------------ D7+DC-6

    def _close_onboarding(self, client):
        from fhort.tasks.models import Customer
        # D7 — identitat canònica: el self-Customer neix amb codi=codi_tenant (tasks/0020);
        # li propaguem el codi_global (el ganxo del registre global cross-tenant).
        self_cu = Customer.objects.filter(is_self=True).first()
        if self_cu and self_cu.codi_global != client.codi_tenant:
            self_cu.codi_global = client.codi_tenant
            self_cu.save(update_fields=['codi_global'])
        return self_cu

    # ------------------------------------------------------------------ handle

    def handle(self, *args, **options):
        schema, source, dry = options['schema'], options['source'], options['dry_run']
        if schema == 'public':
            raise CommandError("El schema 'public' no és un tenant.")
        if schema == source:
            raise CommandError('Origen i destí no poden ser el mateix schema.')

        TenantModel = get_tenant_model()
        client = TenantModel.objects.filter(schema_name=schema).first()
        if client is None:
            raise CommandError(f"Tenant '{schema}' no existeix.")
        if not TenantModel.objects.filter(schema_name=source).exists():
            raise CommandError(f"Tenant origen '{source}' no existeix.")

        self.stdout.write(f"\n{'[DRY-RUN] ' if dry else ''}bootstrap_tenant: "
                          f"{source} → {schema} ({client.codi_tenant})\n")

        maps, natural_cache, deferred, pieces = {}, {}, [], []
        ok = True

        try:
            with transaction.atomic():
                with schema_context(schema):
                    for model, key, fks, m2m, tr in _spec():
                        p, _ = self._copy_piece(model, key, fks, m2m, tr,
                                                source, maps, natural_cache, deferred)
                        pieces.append(p)
                        extra = f" · {p.nulled} FK d'entitat → NULL" if p.nulled else ''
                        skip = f" · {p.skipped} saltats" if p.skipped else ''
                        self.stdout.write(
                            f"  {p.name:22} {p.created:>5} creats  {p.updated:>5} actualitzats{extra}{skip}")
                        if p.skipped:
                            ok = False

                    n_def = self._resolve_deferred(deferred, maps)
                    self.stdout.write(f"  {'(auto-FK 2a passada)':22} {n_def:>5} resoltes")

                    if ok and not dry:
                        self._close_onboarding(client)

                if ok and not dry:
                    # public: tancar onboarding → actiu (DC-6)
                    client.onboarding_complet = True
                    client.estat = 'actiu'
                    client.save(update_fields=['onboarding_complet', 'estat'])

                if dry:
                    transaction.set_rollback(True)
        except Exception as e:
            raise CommandError(f'bootstrap fallit: {e}')

        total_c = sum(p.created for p in pieces)
        total_u = sum(p.updated for p in pieces)
        total_n = sum(p.nulled for p in pieces)
        total_s = sum(p.skipped for p in pieces)
        self.stdout.write(
            f"\n{'[DRY-RUN] ' if dry else ''}Total: {total_c} creats, {total_u} actualitzats, "
            f"{total_n} FK d'entitat a NULL, {total_s} saltats.")

        if not ok:
            self.stdout.write(self.style.ERROR(
                f"\nEl tenant es queda en '{client.estat}'. Corregeix i re-executa "
                f"(la comanda és idempotent)."))
            raise CommandError('bootstrap incomplet: hi ha peces saltades.')

        if dry:
            self.stdout.write(self.style.WARNING('\n[DRY-RUN] res escrit; estat sense tocar.'))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"\nTenant '{schema}' operatiu: estat={client.estat}, onboarding_complet=True."))
