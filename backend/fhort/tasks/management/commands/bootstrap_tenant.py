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

# ---------------------------------------------------------------------------
# F3 P-FREE-SEED (B2) — blocs de sembra seleccionables des del backoffice.
# Cada bloc agrupa peces de `_spec()` per NOM de model. SEED_BLOCK_DEPS és el graf
# de dependències DE SELECCIÓ: seleccionar un bloc n'arrossega la clausura (p.ex.
# demanar 'grading' arrossega base + garments + size_systems + pom_masters, perquè
# GradingRule.pom→POMMaster, .talla_base→SizeDefinition, .rule_set→GradingRuleSet).
# L'ordre REAL de còpia el fixa _spec() (topològic); aquí només es decideix QUINES
# peces hi entren. Les claus han de coincidir amb backoffice.SeedProfile.Bloc.
SEED_BLOCKS = {
    'base':            ['BodyMeasurementISO', 'POMCategory', 'GarmentGroup', 'Target',
                        'FitType', 'ConstructionType', 'POMGlobal', 'GarmentTypeGlobal'],
    'size_systems':    ['SizeSystem', 'SizeDefinition'],
    'garments':        ['GarmentType', 'GarmentTypeItem'],
    'pom_masters':     ['POMMaster', 'GarmentPOMMap'],
    'grading':         ['GradingRuleSet', 'GradingRule'],
    'sizing_profiles': ['SizingProfile'],
    'time_seeds':      ['TaskTimeEstimate', 'TimeSeed'],
}
SEED_BLOCK_DEPS = {
    'base':            set(),
    'size_systems':    {'base'},
    'garments':        {'base'},
    'pom_masters':     {'base', 'garments'},
    'grading':         {'base', 'size_systems', 'pom_masters', 'garments'},
    # SizingProfile.grading_rule_set és PROTECT i NO nullable: un perfil de mesures
    # exigeix un ruleset de grading al schema. Dependència DURA → arrossega grading.
    'sizing_profiles': {'base', 'garments', 'size_systems', 'grading'},
    'time_seeds':      {'base', 'garments'},
}
GRADING_BLOCK = 'grading'


def seed_block_closure(blocks):
    """Clausura transitiva de dependències de selecció. Falla fort si un bloc no existeix."""
    seen, stack = set(), list(blocks)
    while stack:
        b = stack.pop()
        if b in seen:
            continue
        if b not in SEED_BLOCK_DEPS:
            raise CommandError(f"Bloc de sembra desconegut: {b!r}. Vàlids: {sorted(SEED_BLOCK_DEPS)}")
        seen.add(b)
        stack.extend(SEED_BLOCK_DEPS[b] - seen)
    return seen


def models_for_blocks(blocks):
    """Conjunt de noms de model coberts per un conjunt de blocs (ja en clausura)."""
    names = set()
    for b in blocks:
        names.update(SEED_BLOCKS[b])
    return names


def seed_block_counts(source='fhort'):
    """Comptadors reals del tenant origen per bloc de sembra (F3 B4/B5).

    Retorna {block: {'total': n, 'deps': [...], 'models': {ModelName: count}}}. Viu
    AQUÍ (tasks) perquè és l'únic lloc que coneix el catàleg; el backoffice (SHARED)
    hi delega sense importar cap model de tenant. Llegeix des del schema origen.
    """
    spec_models = {row[0].__name__: row[0] for row in _spec()}
    out = {}
    with schema_context(source):
        for block, names in SEED_BLOCKS.items():
            models, total = {}, 0
            for nm in names:
                m = spec_models.get(nm)
                c = m.objects.count() if m is not None else 0
                models[nm] = c
                total += c
            out[block] = {
                'total': total,
                'deps': sorted(SEED_BLOCK_DEPS.get(block, set())),
                'models': models,
            }
    return out


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
        parser.add_argument('--profile', dest='profile', type=int, default=None,
                            help='ID d\'un backoffice.SeedProfile: sembra NOMÉS els blocs '
                                 'seleccionats (+ dependències). Sense --profile: tot el catàleg.')

    # ------------------------------------------------------------------ utils

    def _concrete(self, model):
        """Camps concrets a copiar (sense pk, sense M2M). FK → attname (`x_id`)."""
        return [f for f in model._meta.fields if not f.primary_key]

    def _read_source(self, model, source, filter_kwargs=None):
        """Llegeix les files de l'origen com a dicts {field_name: valor|pk_origen}.

        `filter_kwargs` restringeix la font (F3: gate de grading — només rulesets
        origen=CANONICAL, i les regles que hi pengen). None = totes les files.
        """
        with schema_context(source):
            qs = model.objects.all()
            if filter_kwargs:
                qs = qs.filter(**filter_kwargs)
            rows = []
            for obj in qs.order_by('pk'):
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
                    source, maps, natural_cache, deferred, source_filters=None):
        p = Piece(model.__name__)
        rows = self._read_source(model, source, (source_filters or {}).get(model))
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
                        # F3: en sembra selectiva, una FK NULLABLE cap a un bloc no
                        # seleccionat no és un error: l'enllaç opcional no es pobla
                        # (p.ex. GarmentTypeItem.grading_rule_set en un Free sense
                        # grading). Només és skip dur si la FK és obligatòria (i llavors
                        # la clausura de blocs hauria d'haver-la arrossegada abans).
                        if f.null:
                            p.nulled += 1
                            values[att] = None
                            continue
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

        # ---- F3 P-FREE-SEED: selecció per perfil (blocs + gate de grading) -----
        # El SeedProfile viu a backoffice (SHARED/public); es llegeix des de public,
        # ABANS d'obrir el schema_context del destí.
        selected_models, source_filters = None, {}
        prof_label = ''
        if options['profile'] is not None:
            from fhort.backoffice.models import SeedProfile
            profile = SeedProfile.objects.filter(pk=options['profile']).first()
            if profile is None:
                raise CommandError(f"SeedProfile id={options['profile']} no existeix.")
            if not profile.blocks:
                raise CommandError(f"El perfil '{profile.nom}' no selecciona cap bloc.")
            closure = seed_block_closure(profile.blocks)
            selected_models = models_for_blocks(closure)
            prof_label = f" · perfil '{profile.nom}' → blocs {sorted(closure)}"

            # Gate de grading (llei RUN-CLIENT, A3): al flux automàtic només viatja
            # grading CANONICAL. Si el perfil el demana i cap ruleset de l'origen és
            # CANONICAL → error clar, cap còpia (mai còpia silenciosa de NULL/CLIENT_RUN).
            if GRADING_BLOCK in closure:
                from fhort.pom.models import GradingRuleSet, GradingRule
                with schema_context(source):
                    n_canon = GradingRuleSet.objects.filter(
                        origen=GradingRuleSet.ORIGEN_CANONICAL).count()
                if n_canon == 0:
                    raise CommandError(
                        f"El perfil '{profile.nom}' demana grading però l'origen '{source}' "
                        f"no té cap GradingRuleSet amb origen=CANONICAL (classifica'ls amb "
                        f"`set_grading_origen`). No es copia cap ruleset.")
                source_filters[GradingRuleSet] = {'origen': GradingRuleSet.ORIGEN_CANONICAL}
                source_filters[GradingRule] = {'rule_set__origen': GradingRuleSet.ORIGEN_CANONICAL}

        self.stdout.write(f"\n{'[DRY-RUN] ' if dry else ''}bootstrap_tenant: "
                          f"{source} → {schema} ({client.codi_tenant}){prof_label}\n")

        spec = [row for row in _spec()
                if selected_models is None or row[0].__name__ in selected_models]

        maps, natural_cache, deferred, pieces = {}, {}, [], []
        ok = True

        try:
            with transaction.atomic():
                with schema_context(schema):
                    for model, key, fks, m2m, tr in spec:
                        p, _ = self._copy_piece(model, key, fks, m2m, tr,
                                                source, maps, natural_cache, deferred,
                                                source_filters)
                        pieces.append(p)
                        extra = f" · {p.nulled} FK d'entitat → NULL" if p.nulled else ''
                        skip = f" · {p.skipped} saltats" if p.skipped else ''
                        self.stdout.write(
                            f"  {p.name:22} {p.created:>5} creats  {p.updated:>5} actualitzats{extra}{skip}")
                        if p.skipped:
                            ok = False

                    n_def = self._resolve_deferred(deferred, maps)
                    self.stdout.write(f"  {'(auto-FK 2a passada)':22} {n_def:>5} resoltes")

                    # S12 — pas ESPECIAL (no és peça de _spec): la Template FTT és file-backed a
                    # media, i _spec copia files de BD; per això es GENERA per codi i es pack-eja a
                    # la media del tenant. Idempotent (regenera el fitxer). Respecta --dry-run.
                    if dry:
                        self.stdout.write(f"  {'Template FTT (mestra)':22} {'(generaria .fttpt)'}")
                    else:
                        from fhort.models_app.master_template import seed_master_template
                        _, created = seed_master_template()
                        self.stdout.write(
                            f"  {'Template FTT (mestra)':22} "
                            f"{(1 if created else 0):>5} creats  {(0 if created else 1):>5} actualitzats")

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
