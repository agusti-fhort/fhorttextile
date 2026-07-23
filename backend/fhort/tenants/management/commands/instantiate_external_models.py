"""
Management command: instantiate_external_models
Federació v2 (P3) — instancia al Studio, com a EXTERN, els models canònics del Brand.

    manage.py instantiate_external_models --brand LOS --studio FTT [--limit N] [--commit]

LA LLEI: l'EXTERN neix amb IDENTITAT + CONFIGURACIÓ, mai amb feina. Viatgen codi_intern,
nom, any, temporada, sequencial (del Brand — P2 el fa inofensiu per al comptador local) i
els 4 camps de CONFIG_KEYS resolts per CLAU NATURAL contra el catàleg del Studio. NO
viatgen mesures, regles de grading, fitxes, fittings ni tasques: la feina es fa al Studio i
neix a zero (el signal sync_size_fitting crea la SF buida; el watchpoint es recalcula).

DISCIPLINA CROSS-SCHEMA: es llegeix el Brand com a DICTS dins schema_context i se surt del
context amb la llista tancada — mai un objecte ORM viu (Bandera 3 de la diagnosi). L'escriptura
al Studio és amb Model.objects.create() (NO bulk_create) perquè els signals s'han de disparar.

EL VINCLE MANA: la instanciació NOMÉS opera si existeix un TenantLink ACTIU entre les parts.
Aturat o revocat → el pont està tancat i el command no fa res (el token governa el pont).

IDEMPOTENT per codi_intern: si el model ja existeix al Studio, es SALTA (mai s'actualitza).
Sense --commit és DRY-RUN (default): calcula i informa, no escriu.
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django_tenants.utils import schema_context

from fhort.tenants.models import Client, TenantLink


class Command(BaseCommand):
    help = 'Instancia al Studio, com a EXTERN, els models del Brand (gated per TenantLink actiu).'

    def add_arguments(self, parser):
        parser.add_argument('--brand', required=True, help='codi_tenant del Brand (origen canònic).')
        parser.add_argument('--studio', required=True, help='codi_tenant del Studio (destí).')
        parser.add_argument('--limit', type=int, default=None, help='Màxim de models a llegir (assaig).')
        parser.add_argument('--commit', action='store_true', help='Escriu de debò. Sense flag = DRY-RUN.')

    def handle(self, *args, **options):
        brand, studio = options['brand'], options['studio']
        limit, commit = options['limit'], options['commit']

        # (a) El vincle mana: només amb TenantLink ACTIU entre les parts.
        link = TenantLink.objects.filter(
            brand_codi_tenant=brand, studio_codi_tenant=studio).first()
        if link is None:
            raise CommandError(
                f'No hi ha cap TenantLink entre brand={brand} i studio={studio}. Cal sembrar-lo.')
        if not link.es_viu():
            raise CommandError(
                f'El TenantLink {brand}↔{studio} no és ACTIU (estat={link.estat}). El pont està tancat.')

        brand_client = Client.objects.filter(codi_tenant=brand).first()
        studio_client = Client.objects.filter(codi_tenant=studio).first()
        if brand_client is None:
            raise CommandError(f"No existeix cap tenant amb codi_tenant='{brand}'.")
        if studio_client is None:
            raise CommandError(f"No existeix cap tenant amb codi_tenant='{studio}'.")

        # (b) Llegir el Brand com a DICTS (mai ORM viu fora del context). NOMÉS els models que
        # el Brand ha ASSIGNAT a aquest Studio (studio_assignat). El pont obert no basta.
        total_brand, n_assignats, rows = self._read_brand(brand_client.schema_name, studio, limit)

        # (c-d) Resoldre i (opcionalment) crear al Studio.
        report = self._write_studio(studio_client.schema_name, brand, rows, commit)

        # (e) Informe final.
        self._print_report(brand, studio, commit, total_brand, n_assignats, len(rows), report)

    # ── (b) lectura del Brand ──────────────────────────────────────────────────
    def _read_brand(self, brand_schema, studio, limit):
        from fhort.models_app.models import Model
        rows = []
        with schema_context(brand_schema):
            total_brand = Model.objects.count()
            assignats = Model.objects.filter(studio_assignat=studio)
            n_assignats = assignats.count()
            qs = (assignats
                  .select_related('garment_type_item__garment_type', 'size_system', 'grading_rule_set')
                  .order_by('sequencial', 'codi_intern'))
            if limit:
                qs = qs[:limit]
            for m in qs:
                gti = m.garment_type_item
                rows.append({
                    'codi_intern': m.codi_intern,
                    'nom_prenda': m.nom_prenda,
                    'any': m.any,
                    'temporada': m.temporada,
                    'sequencial': m.sequencial,
                    'fit_type': m.fit_type,
                    'base_size_label': m.base_size_label,
                    'size_run_model': m.size_run_model,
                    # claus naturals del catàleg (per resoldre al Studio):
                    'gti_code': gti.code if gti else None,
                    'gti_gt_codi': (gti.garment_type.codi_client
                                    if gti and gti.garment_type_id else None),
                    'size_system_codi': m.size_system.codi if m.size_system_id else None,
                    'grs_nom': m.grading_rule_set.nom if m.grading_rule_set_id else None,
                })
        return total_brand, n_assignats, rows

    # ── (c-d) escriptura al Studio ─────────────────────────────────────────────
    def _write_studio(self, studio_schema, brand, rows, commit):
        from fhort.models_app.models import Model
        from fhort.pom.models import GarmentType, GradingRuleSet, SizeSystem
        from fhort.tasks.models import Customer, GarmentTypeItem

        creats, saltats = [], []
        unmatched = {'garment_type_item': [], 'size_system': [], 'grading_rule_set': []}

        with schema_context(studio_schema):
            customer = Customer.objects.filter(codi=brand).first()
            if customer is None:
                raise CommandError(
                    f"Al Studio no existeix cap Customer amb codi='{brand}'. No es crea "
                    f"(decisió): sembra'l abans o revisa el vincle.")

            def _crea_tots():
                for r in rows:
                    if Model.objects.filter(codi_intern=r['codi_intern']).exists():
                        saltats.append(r['codi_intern'])
                        continue

                    # Resolució per clau natural. Els no-aparellats NO bloquegen: NULL + informe.
                    gti = None
                    if r['gti_code']:
                        gt = (GarmentType.objects.filter(codi_client=r['gti_gt_codi']).first()
                              if r['gti_gt_codi'] else None)
                        if gt is not None:
                            gti = GarmentTypeItem.objects.filter(
                                garment_type=gt, code=r['gti_code']).first()
                        if gti is None:
                            unmatched['garment_type_item'].append(
                                f"{r['gti_gt_codi']}/{r['gti_code']}")

                    size_system = None
                    if r['size_system_codi']:
                        size_system = SizeSystem.objects.filter(codi=r['size_system_codi']).first()
                        if size_system is None:
                            unmatched['size_system'].append(r['size_system_codi'])

                    grs = None
                    if r['grs_nom']:
                        grs = GradingRuleSet.objects.filter(nom=r['grs_nom']).first()
                        if grs is None:
                            unmatched['grading_rule_set'].append(r['grs_nom'])

                    if commit:
                        Model.objects.create(
                            codi_intern=r['codi_intern'],
                            customer=customer,
                            codi_tenant=customer.codi,
                            any=r['any'],
                            temporada=r['temporada'],
                            sequencial=r['sequencial'],
                            origen=Model.ORIGEN_EXTERN,
                            nom_prenda=r['nom_prenda'],
                            fit_type=r['fit_type'] or 'Regular',
                            base_size_label=r['base_size_label'],
                            size_run_model=r['size_run_model'],
                            garment_type_item=gti,
                            size_system=size_system,
                            grading_rule_set=grs,
                        )
                    creats.append(r['codi_intern'])

            if commit:
                with transaction.atomic():
                    _crea_tots()
            else:
                _crea_tots()

        return {'creats': creats, 'saltats': saltats, 'unmatched': unmatched}

    # ── (e) informe ────────────────────────────────────────────────────────────
    def _print_report(self, brand, studio, commit, total_brand, n_assignats, n_llegits, report):
        mode = 'COMMIT' if commit else 'DRY-RUN'
        verb = 'creats' if commit else 'a crear'
        self.stdout.write(f"\n[{mode}] instantiate_external_models {brand} → {studio}")
        # N models al Brand, dels quals M assignats a aquest Studio: N-M existeixen però NO
        # viatgen (és el cas correcte — sense assignació, cap traspàs).
        self.stdout.write(f"  models al Brand   : {total_brand} · assignats a {studio}: {n_assignats}")
        self.stdout.write(f"  llegits (assignats): {n_llegits}")
        self.stdout.write(f"  {verb:<17}: {len(report['creats'])}")
        self.stdout.write(f"  saltats (ja hi són): {len(report['saltats'])}")

        um = report['unmatched']
        total_um = sum(len(v) for v in um.values())
        if total_um:
            self.stdout.write(self.style.WARNING(
                f"  config NO aparellada: {total_um} referència/es (el model es crea amb el camp NULL)"))
            for tipus, codis in um.items():
                if codis:
                    unics = sorted(set(codis))
                    mostra = ', '.join(unics[:10]) + (' …' if len(unics) > 10 else '')
                    self.stdout.write(f"    · {tipus}: {len(unics)} → {mostra}")
        else:
            self.stdout.write("  config NO aparellada: 0")

        if not commit:
            self.stdout.write(self.style.NOTICE("\n  (DRY-RUN: no s'ha escrit res. Afegeix --commit per crear.)"))
        else:
            self.stdout.write(self.style.SUCCESS(f"\n  Fet: {len(report['creats'])} models EXTERN creats al Studio {studio}."))
