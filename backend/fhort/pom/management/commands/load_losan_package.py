"""load_losan_package — FASE C del PAQUET LOSAN.

Carrega el paquet LOSAN (generat per `export_losan_package`) a un schema de tenant destí,
resolent totes les FK per CLAU NATURAL, create-if-missing i idempotent (2a passada = 0 canvis).
Dry-run per defecte (fa rollback); `--apply` per escriure de debò.

Llei operativa (gate FASE A/B):
  - El paquet MANA sobre l'estat (actualitza camps en col·lisió) però MAI fa delete.
  - Create-if-missing sobre EXACTAMENT les mateixes claus naturals que fa servir `bootstrap_tenant`,
    per conviure amb el que el bootstrap ja hagi posat.
  - R4: el tenant porta un self-Customer codi=LOS; cap mode tenant-native al motor.
  - Llei de resolució del POM: pom_global.codi preferent, codi_client de reserva, guarda d'ambigüitat.

FK circulars/diferides (patró DEFER de bootstrap): SizeSystem.parent, GarmentTypeItem.{base_size_
definition, grading_rule_set} i els M2M/scope-nodes es resolen en una 2a passada, quan tot hi és.
Referències que apunten fora de l'àmbit LOS (p.ex. un default de grading_rule_set d'un altre client)
es resolen si existeixen al destí i, si no, es deixen a NULL amb avís (no bloquegen).
"""
import json
import os

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django_tenants.utils import schema_context

from fhort.pom.models import (
    POMGlobal, POMMaster, CustomerPOMAlias, GarmentGroup, GarmentType, GarmentPOMMap,
    ItemBaseMeasurement, SizeSystem, SizeDefinition, GradingRuleSet, RuleSetScopeNode,
    GradingRule, SizingProfile, Target, FitType, ConstructionType, POMCategory,
)
from fhort.tasks.models import Customer, GarmentTypeItem
from fhort.models_app.ftt_models import DocumentTemplate

CUSTOMER_CODI = 'LOS'


class _Rollback(Exception):
    pass


class Stats:
    def __init__(self):
        self.created = 0
        self.updated = 0
        self.unchanged = 0

    def add(self, status):
        setattr(self, status, getattr(self, status) + 1)

    def __str__(self):
        return f'created={self.created} updated={self.updated} unchanged={self.unchanged}'


class Command(BaseCommand):
    help = "Carrega el paquet LOSAN a un schema destí (dry-run per defecte; --apply per escriure)."

    def add_arguments(self, parser):
        parser.add_argument('--schema-target', required=True, help='Schema del tenant destí.')
        parser.add_argument('--package-dir', default=None, help='Directori del paquet.')
        parser.add_argument('--apply', action='store_true', help='Escriu de debò (default dry-run).')
        parser.add_argument('--verbose', action='store_true')

    # ── util ────────────────────────────────────────────────────────────────
    def _load(self, name):
        with open(os.path.join(self.pkg, name), encoding='utf-8') as fh:
            return json.load(fh)

    def _coerce(self, model, k, v):
        """Normalitza el valor JSON al tipus Python del camp (Decimal-com-str, etc.) perquè la
        detecció de canvis compari like-with-like i la 2a passada doni 0 canvis de debò.
        Les FK (valor = instància/None) es deixen tal qual."""
        try:
            field = model._meta.get_field(k)
        except Exception:
            return v
        if field.is_relation or v is None:
            return v
        try:
            return field.to_python(v)
        except Exception:
            return v

    def _upsert(self, model, lookup, defaults, stats):
        """Create-if-missing per `lookup`; si existeix, actualitza només els camps que canvien.
        Retorna (obj, status). MAI delete."""
        defaults = {k: self._coerce(model, k, v) for k, v in defaults.items()}
        obj = model.objects.filter(**lookup).first()
        if obj is None:
            obj = model(**lookup)
            for k, v in defaults.items():
                setattr(obj, k, v)
            obj.save()
            stats.add('created')
            return obj, 'created'
        changed = False
        for k, v in defaults.items():
            if getattr(obj, k) != v:
                setattr(obj, k, v)
                changed = True
        if changed:
            obj.save()
            stats.add('updated')
            return obj, 'updated'
        stats.add('unchanged')
        return obj, 'unchanged'

    def _warn(self, msg):
        self.warnings.append(msg)

    # ── resolució de POM (llei de resolució) ─────────────────────────────────
    def _resolve_pom(self, key):
        if not key:
            return None
        codi_global = key.get('pom_global')
        codi_client = key.get('codi_client')
        if codi_global:
            qs = POMMaster.objects.filter(pom_global__codi=codi_global)
            if qs.count() > 1 and codi_client:
                qs = qs.filter(codi_client=codi_client)
            pom = qs.order_by('id').first()
            if pom:
                return pom
        if codi_client:
            qs = POMMaster.objects.filter(codi_client=codi_client)
            n = qs.count()
            if n == 0:
                return None
            if n > 1:
                self._warn(f'POM ambigu per codi_client={codi_client} ({n} candidats) → saltat')
                return None
            return qs.first()
        return None

    def _resolve_gti(self, key):
        if not key:
            return None
        gt = GarmentType.objects.filter(codi_client=key['garment_type']).first()
        if not gt:
            return None
        return GarmentTypeItem.objects.filter(garment_type=gt, code=key['code']).first()

    def _resolve_sizedef(self, key):
        if not key:
            return None
        return SizeDefinition.objects.filter(size_system__codi=key['size_system'],
                                             etiqueta=key['etiqueta']).first()

    # ── càrrega ───────────────────────────────────────────────────────────
    def handle(self, *args, **opts):
        target = opts['schema_target']
        self.apply = opts['apply']
        self.verbose = opts['verbose']
        self.warnings = []
        self.pkg = opts['package_dir'] or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
            'pom', 'seed_data', 'losan_package')
        if not os.path.isdir(self.pkg):
            raise CommandError(f'Paquet no trobat: {self.pkg}')
        manifest = self._load('manifest.json')

        report = {}
        try:
            with schema_context(target), transaction.atomic():
                report = self._run_all()
                if not self.apply:
                    raise _Rollback()
        except _Rollback:
            pass

        # ── informe ──────────────────────────────────────────────────────
        mode = 'APPLY' if self.apply else 'DRY-RUN (rollback)'
        self.stdout.write(self.style.SUCCESS(f'load_losan_package · schema={target} · {mode}'))
        self.stdout.write(f"  paquet: commit={manifest.get('commit')} source={manifest.get('source_schema')}")
        for layer, st in report.items():
            self.stdout.write(f'  {layer:<22} {st}')
        if self.warnings:
            self.stdout.write(self.style.WARNING(f'  avisos ({len(self.warnings)}):'))
            for w in self.warnings[:40]:
                self.stdout.write(f'    - {w}')
            if len(self.warnings) > 40:
                self.stdout.write(f'    … +{len(self.warnings) - 40} més')
        total_c = sum(s.created for s in report.values())
        total_u = sum(s.updated for s in report.values())
        self.stdout.write(self.style.SUCCESS(
            f'  TOTAL created={total_c} updated={total_u} '
            f'(idempotent si 2a passada dona created=0 updated=0)'))

    def _run_all(self):
        rep = {}
        rep['customer'] = self._load_customer()
        rep['pom_globals'] = self._load_pom_globals()
        rep['pom_masters'] = self._load_pom_masters()
        rep['pom_aliases'] = self._load_aliases()
        rep['catalog'] = self._load_catalog()          # items sense defaults FK (diferits)
        rep['size_systems'] = self._load_size_systems()
        rep['pom_maps'] = self._load_pom_maps()
        rep['rulesets'] = self._load_rulesets()
        rep['rules'] = self._load_rules()
        rep['profiles'] = self._load_profiles()
        rep['document_templates'] = self._load_document_templates()
        rep['item_defaults'] = self._backfill_item_defaults()  # 2a passada
        return rep

    def _load_customer(self):
        s = Stats()
        row = self._load('01_customer.json')['rows'][0]
        defaults = {
            'nom': row['nom'], 'active': row['active'], 'is_self': row['is_self'],
            'rao_social': row['rao_social'], 'nif': row['nif'],
            'adreca_linia1': row['adreca_linia1'], 'adreca_linia2': row['adreca_linia2'],
            'ciutat': row['ciutat'], 'codi_postal': row['codi_postal'], 'pais': row['pais'],
            'email_facturacio': row['email_facturacio'], 'condicions_pagament': row['condicions_pagament'],
            'descompte_pct': row['descompte_pct'], 'persona_contacte': row['persona_contacte'],
            'telefon_contacte': row['telefon_contacte'], 'tax_regime': row['tax_regime'],
            'vat_number': row['vat_number'], 'payment_method': row['payment_method'],
        }
        cust, _ = self._upsert(Customer, {'codi': row['codi']}, defaults, s)
        # logo (només a --apply; escriure binari és efecte lateral)
        if self.apply and row.get('logo_asset') and str(row['logo_asset']).startswith('assets/'):
            asset = os.path.join(self.pkg, row['logo_asset'])
            if os.path.exists(asset) and not cust.logo:
                with open(asset, 'rb') as fh:
                    cust.logo.save(os.path.basename(row['logo']), ContentFile(fh.read()), save=True)
            elif not os.path.exists(asset):
                self._warn(f"logo asset absent: {row['logo_asset']}")
        return s

    def _load_pom_globals(self):
        s = Stats()
        for r in self._load('02_pom_globals.json')['rows']:
            d = {k: r[k] for k in r if k not in ('codi', 'body_measure_iso')}
            self._upsert(POMGlobal, {'codi': r['codi']}, d, s)
        return s

    def _load_pom_masters(self):
        s = Stats()
        for r in self._load('03_pom_masters.json')['rows']:
            pg = POMGlobal.objects.filter(codi=r['pom_global']).first() if r['pom_global'] else None
            if r['pom_global'] and not pg:
                self._warn(f"POMMaster {r['codi_client']}: pom_global {r['pom_global']} absent → NULL")
            cat = POMCategory.objects.filter(codi=r['categoria']).first() if r.get('categoria') else None
            defaults = {
                'pom_global': pg, 'nom_client': r['nom_client'], 'categoria': cat,
                'notes': r['notes'], 'actiu': r['actiu'], 'pendent_revisio': r['pendent_revisio'],
                'origen_import': r['origen_import'],
                'tolerancia_default_minus': r['tolerancia_default_minus'],
                'tolerancia_default_plus': r['tolerancia_default_plus'],
            }
            # lookup per la mateixa llei de resolució (evita duplicar sobre bootstrap)
            existing = self._resolve_pom(r['key'])
            if existing:
                lookup = {'pk': existing.pk}
            elif r['pom_global']:
                lookup = {'pom_global__codi': r['pom_global'], 'codi_client': r['codi_client']}
                if not POMMaster.objects.filter(**lookup).exists():
                    lookup = None  # forçar create amb codi_client
            else:
                lookup = None
            if lookup:
                self._upsert(POMMaster, lookup, {**defaults, 'codi_client': r['codi_client']}, s)
            else:
                obj = POMMaster(codi_client=r['codi_client'], **defaults)
                obj.save()
                s.add('created')
        return s

    def _load_aliases(self):
        s = Stats()
        cust = Customer.objects.get(codi=CUSTOMER_CODI)
        for r in self._load('04_pom_aliases.json')['rows']:
            pom = self._resolve_pom(r['pom'])
            if not pom:
                self._warn(f"àlies {r['client_code']}: POM {r['pom']} no resolt → saltat")
                continue
            defaults = {
                'pom': pom, 'client_description': r['client_description'],
                'description_en': r['description_en'], 'description_local': r['description_local'],
                'language': r['language'], 'origen': r['origen'], 'pendent_revisio': r['pendent_revisio'],
            }
            self._upsert(CustomerPOMAlias, {'customer': cust, 'client_code': r['client_code']}, defaults, s)
        return s

    def _load_catalog(self):
        s = Stats()
        cat = self._load('05_garment_catalog.json')
        for g in cat['groups']:
            self._upsert(GarmentGroup, {'codi': g['codi']}, {'nom': g['nom'], 'actiu': g['actiu']}, s)
        for t in cat['types']:
            from fhort.pom.models import GarmentTypeGlobal
            gtg = (GarmentTypeGlobal.objects.filter(codi=t['garment_type_global']).first()
                   if t['garment_type_global'] else None)
            d = {'nom_client': t['nom_client'], 'grup': t['grup'], 'actiu': t['actiu'],
                 'nom_en': t['nom_en'], 'nom_ca': t['nom_ca'], 'nom_es': t['nom_es'],
                 'is_system': t['is_system'], 'construccio_habitual': t['construccio_habitual'],
                 'descripcio': t['descripcio'], 'garment_type_global': gtg}
            self._upsert(GarmentType, {'codi_client': t['codi_client']}, d, s)
        # items SENSE base_size_definition/grading_rule_set (diferits a 2a passada)
        for it in cat['items']:
            gt = GarmentType.objects.filter(codi_client=it['garment_type']).first()
            if not gt:
                self._warn(f"item {it['garment_type']}/{it['code']}: GarmentType absent → saltat")
                continue
            self._upsert(GarmentTypeItem, {'garment_type': gt, 'code': it['code']},
                         {'complexity_order': it['complexity_order']}, s)
        return s

    def _load_size_systems(self):
        s = Stats()
        data = self._load('07_size_systems.json')
        # 1a passada: sistemes sense parent
        for ss in data['size_systems']:
            self._upsert(SizeSystem, {'codi': ss['codi']},
                         {'nom': ss['nom'], 'actiu': ss['actiu'], 'customer_codi': ss['customer_codi']}, s)
        # targets M2M + parent (diferit)
        for ss in data['size_systems']:
            obj = SizeSystem.objects.get(codi=ss['codi'])
            tset = list(Target.objects.filter(codi__in=ss['targets']))
            if set(obj.targets.values_list('codi', flat=True)) != set(ss['targets']):
                obj.targets.set(tset)
            if ss.get('parent'):
                p = SizeSystem.objects.filter(codi=ss['parent']).first()
                if p and obj.parent_id != p.id:
                    obj.parent = p
                    obj.save(update_fields=['parent'])
        for sd in data['size_definitions']:
            ssobj = SizeSystem.objects.filter(codi=sd['size_system']).first()
            if not ssobj:
                self._warn(f"sizedef {sd['size_system']}/{sd['etiqueta']}: system absent → saltat")
                continue
            d = {'ordre': sd['ordre'], 'valor_numeric': sd['valor_numeric'],
                 'body_height_cm': sd['body_height_cm'], 'body_bust_cm': sd['body_bust_cm'],
                 'body_waist_cm': sd['body_waist_cm'], 'body_hip_cm': sd['body_hip_cm'],
                 'age_months_min': sd['age_months_min'], 'age_months_max': sd['age_months_max']}
            self._upsert(SizeDefinition, {'size_system': ssobj, 'etiqueta': sd['etiqueta']}, d, s)
        return s

    def _load_pom_maps(self):
        s = Stats()
        data = self._load('06_pom_maps.json')
        for m in data['garment_pom_maps']:
            gti = self._resolve_gti(m['garment_type_item'])
            pom = self._resolve_pom(m['pom'])
            if not (gti and pom):
                self._warn(f"pommap {m['garment_type_item']}→{m['pom']}: no resolt → saltat")
                continue
            d = {'obligatori': m['obligatori'], 'is_key': m['is_key'], 'nivell': m['nivell'],
                 'ordre': m['ordre'], 'pendent_revisio': m['pendent_revisio']}
            self._upsert(GarmentPOMMap, {'garment_type_item': gti, 'pom': pom}, d, s)
        for ib in data['item_base_measurements']:
            gti = self._resolve_gti(ib['garment_type_item'])
            pom = self._resolve_pom(ib['pom'])
            if not (gti and pom):
                self._warn(f"itembase {ib['garment_type_item']}→{ib['pom']}: no resolt → saltat")
                continue
            self._upsert(ItemBaseMeasurement, {'garment_type_item': gti, 'pom': pom},
                         {'base_value_cm': ib['base_value_cm'], 'nom_fitxa': ib['nom_fitxa']}, s)
        return s

    def _load_rulesets(self):
        s = Stats()
        cust = Customer.objects.get(codi=CUSTOMER_CODI)
        data = self._load('08_rulesets.json')
        for r in data['rulesets']:
            ss = SizeSystem.objects.filter(codi=r['size_system']).first() if r['size_system'] else None
            grp = GarmentGroup.objects.filter(codi=r['garment_group']).first() if r['garment_group'] else None
            gti = self._resolve_gti(r['garment_type_item'])
            con = ConstructionType.objects.filter(codi=r['construction']).first() if r['construction'] else None
            fit = FitType.objects.filter(codi=r['fit_type']).first() if r['fit_type'] else None
            tgt = Target.objects.filter(codi=r['target_legacy']).first() if r['target_legacy'] else None
            d = {'origen': r['origen'], 'actiu': r['actiu'], 'customer': cust,
                 'size_system': ss, 'garment_group': grp, 'garment_type_item': gti,
                 'construction': con, 'fit_type': fit, 'target': tgt,
                 'version_number': r['version_number'], 'codi_sistema': r['codi_sistema'],
                 'pendents_vincular': r['pendents_vincular']}
            obj, _ = self._upsert(GradingRuleSet, {'nom': r['nom']}, d, s)
            want = set(r['targets'])
            if set(obj.targets.values_list('codi', flat=True)) != want:
                obj.targets.set(list(Target.objects.filter(codi__in=want)))
        # scope nodes (create-if-missing per rule_set+node)
        for sn in data['scope_nodes']:
            rs = GradingRuleSet.objects.filter(nom=sn['rule_set']).first()
            if not rs:
                self._warn(f"scopenode: ruleset {sn['rule_set']} absent → saltat")
                continue
            grp = GarmentGroup.objects.filter(codi=sn['garment_group']).first() if sn['garment_group'] else None
            gt = GarmentType.objects.filter(codi_client=sn['garment_type']).first() if sn['garment_type'] else None
            gti = self._resolve_gti(sn['garment_type_item'])
            lookup = {'rule_set': rs, 'node_type': sn['node_type'],
                      'garment_group': grp, 'garment_type': gt, 'garment_type_item': gti}
            self._upsert(RuleSetScopeNode, lookup, {}, s)
        return s

    def _load_rules(self):
        s = Stats()
        for r in self._load('09_rules.json')['rows']:
            rs = GradingRuleSet.objects.filter(nom=r['rule_set']).first()
            pom = self._resolve_pom(r['pom'])
            tb = self._resolve_sizedef(r['talla_base'])
            if not (rs and pom and tb):
                self._warn(f"regla {r['rule_set']}/{r['pom']}: no resolt (rs={bool(rs)} pom={bool(pom)} tb={bool(tb)}) → saltat")
                continue
            d = {'talla_base': tb, 'logica': r['logica'], 'increment': r['increment'],
                 'valors_step': r['valors_step'], 'increment_base': r['increment_base'],
                 'increment_break': r['increment_break'], 'talla_break_label': r['talla_break_label'],
                 'actiu': r['actiu']}
            self._upsert(GradingRule, {'rule_set': rs, 'pom': pom}, d, s)
        return s

    def _load_profiles(self):
        s = Stats()
        cust = Customer.objects.get(codi=CUSTOMER_CODI)
        for r in self._load('10_profiles.json')['rows']:
            tgt = Target.objects.filter(codi=r['target']).first()
            gt = GarmentType.objects.filter(codi_client=r['garment_type']).first()
            con = ConstructionType.objects.filter(codi=r['construction']).first()
            fit = FitType.objects.filter(codi=r['fit_type']).first()
            ss = SizeSystem.objects.filter(codi=r['size_system']).first()
            rs = GradingRuleSet.objects.filter(nom=r['grading_rule_set']).first()
            if not all([tgt, gt, con, fit, ss, rs]):
                self._warn(f"profile {r['target']}/{r['garment_type']}: FK no resolta → saltat")
                continue
            # grading_rule_set forma part de la IDENTITAT: 3 profiles NEWBORN comparteixen la
            # tupla wizard i només es distingeixen pel ruleset (desambiguació per scope d'item,
            # R7). Sense això el destí perdria 2 dels 18 profiles.
            lookup = {'target': tgt, 'garment_type': gt, 'construction': con,
                      'fit_type': fit, 'size_system': ss, 'version': r['version'],
                      'grading_rule_set': rs}
            d = {'customer': cust, 'is_default': r['is_default'], 'notes': r['notes']}
            self._upsert(SizingProfile, lookup, d, s)
        return s

    def _load_document_templates(self):
        s = Stats()
        for r in self._load('11_document_templates.json')['rows']:
            d = {'descripcio': r['descripcio'], 'metadata_schema': r['metadata_schema'],
                 'is_sample': r['is_sample'], 'origen': r['origen'], 'actiu': r['actiu']}
            obj, _ = self._upsert(DocumentTemplate, {'nom': r['nom']}, d, s)
            if self.apply and r.get('fitxer_asset') and str(r['fitxer_asset']).startswith('assets/') and not obj.fitxer_template:
                asset = os.path.join(self.pkg, r['fitxer_asset'])
                if os.path.exists(asset):
                    with open(asset, 'rb') as fh:
                        obj.fitxer_template.save(os.path.basename(r['fitxer_template']), ContentFile(fh.read()), save=True)
        return s

    def _backfill_item_defaults(self):
        """2a passada: base_size_definition + grading_rule_set dels items (resolve-if-present)."""
        s = Stats()
        for it in self._load('05_garment_catalog.json')['items']:
            if not it.get('base_size_definition') and not it.get('grading_rule_set'):
                continue
            gt = GarmentType.objects.filter(codi_client=it['garment_type']).first()
            obj = GarmentTypeItem.objects.filter(garment_type=gt, code=it['code']).first() if gt else None
            if not obj:
                continue
            changed = False
            bsd = self._resolve_sizedef(it['base_size_definition']) if it.get('base_size_definition') else None
            if it.get('base_size_definition') and not bsd:
                self._warn(f"item {it['garment_type']}/{it['code']}: base_size_definition fora d'àmbit → NULL")
            if bsd and obj.base_size_definition_id != bsd.id:
                obj.base_size_definition = bsd
                changed = True
            if it.get('grading_rule_set'):
                rs = GradingRuleSet.objects.filter(nom=it['grading_rule_set']).first()
                if not rs:
                    self._warn(f"item {it['garment_type']}/{it['code']}: grading_rule_set '{it['grading_rule_set']}' fora d'àmbit → NULL")
                elif obj.grading_rule_set_id != rs.id:
                    obj.grading_rule_set = rs
                    changed = True
            if changed:
                obj.save()
                s.add('updated')
            else:
                s.add('unchanged')
        return s
