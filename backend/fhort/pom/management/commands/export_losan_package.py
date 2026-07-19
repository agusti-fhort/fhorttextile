"""export_losan_package — FASE B del PAQUET LOSAN.

Fotografia l'àmbit LOS del tenant `fhort` en un paquet de fitxers versionats per CLAU NATURAL
(codis, mai pk) + un manifest amb els recomptes REALS i el sha256 de cada fitxer. Read-only sobre
les dades: només escriu els fitxers del paquet.

Gate FASE A (2026-07-19) ratificat:
  R2 · clau natural del POM = `pom_global.codi` (codi_client de reserva, mai clau).
  R3 · O1 — CustomerPOMAlias viatja SENCERA (196), penjada del self-Customer LOS.
  R4 · self-Customer codi=LOS dins el tenant (cap adaptació tenant-native del motor).
  R5 · origen dels rulesets es manté CLIENT_RUN.
  R6 · el deute NO puja: s'exclou el ruleset legacy (origen IS NULL, grs 104) + les seves regles;
       els 4 SizingProfile customer=NULL sobre 104 són de fhort → NO viatgen.
  R9 · capçalera LOSAN (DocumentTemplate + logo) dins el paquet.

Nota de disseny (self-consistència d'FK): el conjunt de POMMaster exportat és la UNIÓ dels POMs
referenciats per àlies ∪ regles exportades ∪ TOTS els GarmentPOMMap ∪ ItemBaseMeasurement, perquè
cap FK del paquet quedi penjada. Amb l'exclusió de grs 104 això dona 0 regles sobre POM inactiu.
"""
import hashlib
import json
import os
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django_tenants.utils import schema_context

from fhort.pom.models import (
    POMGlobal, POMMaster, CustomerPOMAlias, GarmentGroup, GarmentType, GarmentPOMMap,
    ItemBaseMeasurement, SizeSystem, SizeDefinition, GradingRuleSet, RuleSetScopeNode,
    GradingRule, SizingProfile,
)
from fhort.tasks.models import Customer, GarmentTypeItem
from fhort.models_app.ftt_models import DocumentTemplate

CUSTOMER_CODI = 'LOS'


def _d(v):
    """Serialitza Decimal com a str (preserva precisió); passa la resta tal qual."""
    if isinstance(v, Decimal):
        return str(v)
    return v


class Command(BaseCommand):
    help = "Exporta l'àmbit LOS del tenant a un paquet versionat per clau natural + manifest."

    def add_arguments(self, parser):
        parser.add_argument('--schema', default='fhort', help='Schema origen (default fhort).')
        parser.add_argument('--out', default=None,
                            help='Directori de sortida (default fhort/pom/seed_data/losan_package).')
        parser.add_argument('--commit', default='', help="Rev git d'origen per al manifest.")
        parser.add_argument('--indent', type=int, default=2)

    # ── helpers de clau natural ────────────────────────────────────────────
    def _pom_key(self, pom):
        """R2 — clau natural del POM: pom_global.codi si n'hi ha, codi_client de reserva."""
        if pom is None:
            return None
        return {
            'pom_global': pom.pom_global.codi if pom.pom_global_id else None,
            'codi_client': pom.codi_client,
        }

    def _gti_key(self, gti):
        if gti is None:
            return None
        return {'garment_type': gti.garment_type.codi_client, 'code': gti.code}

    def _sizedef_key(self, sd):
        if sd is None:
            return None
        return {'size_system': sd.size_system.codi, 'etiqueta': sd.etiqueta}

    # ── escriptura + hash ──────────────────────────────────────────────────
    def _write(self, out_dir, name, payload, indent):
        path = os.path.join(out_dir, name)
        data = json.dumps(payload, ensure_ascii=False, indent=indent, sort_keys=False)
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(data)
        sha = hashlib.sha256(data.encode('utf-8')).hexdigest()
        return {'file': name, 'count': payload.get('count'), 'sha256': sha}

    def _copy_asset(self, fieldfile, assets_dir):
        """Copia el binari d'un FileField/ImageField al paquet. Retorna (name, asset_rel)."""
        if not fieldfile:
            return None, None
        name = fieldfile.name
        base = os.path.basename(name)
        os.makedirs(assets_dir, exist_ok=True)
        try:
            fieldfile.open('rb')
            raw = fieldfile.read()
            fieldfile.close()
        except Exception as exc:  # fitxer absent al storage
            return name, f'MISSING:{exc}'
        with open(os.path.join(assets_dir, base), 'wb') as fh:
            fh.write(raw)
        return name, f'assets/{base}'

    def handle(self, *args, **opts):
        schema = opts['schema']
        indent = opts['indent']
        base_dir = opts['out'] or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
            'pom', 'seed_data', 'losan_package')
        out_dir = base_dir
        assets_dir = os.path.join(out_dir, 'assets')
        os.makedirs(out_dir, exist_ok=True)

        with schema_context(schema):
            try:
                los = Customer.objects.get(codi=CUSTOMER_CODI)
            except Customer.DoesNotExist:
                raise CommandError(f'Customer {CUSTOMER_CODI} no existeix al schema {schema}.')

            manifest_layers = []

            # ── 01 · Customer (self-Customer LOS, R4) ──────────────────────
            logo_name, logo_asset = self._copy_asset(los.logo, assets_dir)
            customer_row = {
                'codi': los.codi, 'nom': los.nom, 'active': los.active, 'is_self': True,
                'codi_global': los.codi_global,
                'logo': logo_name, 'logo_asset': logo_asset,
                'rao_social': los.rao_social, 'nif': los.nif,
                'adreca_linia1': los.adreca_linia1, 'adreca_linia2': los.adreca_linia2,
                'ciutat': los.ciutat, 'codi_postal': los.codi_postal, 'pais': los.pais,
                'email_facturacio': los.email_facturacio,
                'condicions_pagament': los.condicions_pagament,
                'descompte_pct': _d(los.descompte_pct),
                'persona_contacte': los.persona_contacte, 'telefon_contacte': los.telefon_contacte,
                'tax_regime': los.tax_regime, 'vat_number': los.vat_number,
                'payment_method': los.payment_method,
            }
            manifest_layers.append(self._write(out_dir, '01_customer.json',
                                                {'layer': 'customer', 'count': 1, 'rows': [customer_row]}, indent))

            # ── conjunt exportat (self-consistent) ─────────────────────────
            # R6: rulesets exportats = customer LOS EXCEPTE el legacy (origen IS NULL, grs 104).
            exported_rs = list(GradingRuleSet.objects.filter(customer=los)
                               .exclude(origen__isnull=True).order_by('nom'))
            rs_ids = [r.id for r in exported_rs]

            alias_pom_ids = set(CustomerPOMAlias.objects.filter(customer=los)
                                .exclude(pom__isnull=True).values_list('pom_id', flat=True))
            rule_pom_ids = set(GradingRule.objects.filter(rule_set_id__in=rs_ids)
                               .values_list('pom_id', flat=True))
            map_pom_ids = set(GarmentPOMMap.objects.values_list('pom_id', flat=True))
            item_pom_ids = set(ItemBaseMeasurement.objects.values_list('pom_id', flat=True))
            pom_ids = alias_pom_ids | rule_pom_ids | map_pom_ids | item_pom_ids
            poms = list(POMMaster.objects.filter(id__in=pom_ids)
                        .select_related('pom_global', 'categoria').order_by('codi_client', 'id'))

            # ── 02 · POMGlobal (referenciats pels POMMaster exportats) ─────
            global_codes = sorted({p.pom_global.codi for p in poms if p.pom_global_id})
            pglobals = POMGlobal.objects.filter(codi__in=global_codes).order_by('codi')
            g_rows = []
            for g in pglobals:
                g_rows.append({
                    'codi': g.codi, 'nom_en': g.nom_en, 'nom_ca': g.nom_ca, 'nom_es': g.nom_es,
                    'categoria': g.categoria, 'descripcio_en': g.descripcio_en,
                    'descripcio_ca': g.descripcio_ca, 'unitat': g.unitat, 'actiu': g.actiu,
                    'abbreviation': g.abbreviation, 'start_point': g.start_point,
                    'end_point': g.end_point, 'reference_point': g.reference_point,
                    'scope': g.scope, 'orientation': g.orientation, 'state': g.state, 'line': g.line,
                    'body_section': g.body_section, 'is_key': g.is_key,
                    'tol_prod_cm': _d(g.tol_prod_cm), 'tol_samp_cm': _d(g.tol_samp_cm),
                    'applies_woven': g.applies_woven, 'applies_knit': g.applies_knit,
                    'applies_swim': g.applies_swim, 'notes': g.notes, 'iso_ref': g.iso_ref,
                    'body_measure_iso': (g.body_measure_iso.codi_intern if g.body_measure_iso_id else None),
                })
            lospom = sum(1 for r in g_rows if r['codi'].startswith('LOSPOM-'))
            manifest_layers.append(self._write(out_dir, '02_pom_globals.json',
                {'layer': 'pom_globals', 'count': len(g_rows), 'lospom_subcount': lospom, 'rows': g_rows}, indent))

            # ── 03 · POMMaster ─────────────────────────────────────────────
            m_rows = []
            for p in poms:
                m_rows.append({
                    'key': self._pom_key(p),
                    'pom_global': p.pom_global.codi if p.pom_global_id else None,
                    'codi_client': p.codi_client, 'nom_client': p.nom_client,
                    'categoria': (p.categoria.codi if p.categoria_id else None),
                    'notes': p.notes, 'actiu': p.actiu, 'pendent_revisio': p.pendent_revisio,
                    'origen_import': p.origen_import,
                    'tolerancia_default_minus': _d(p.tolerancia_default_minus),
                    'tolerancia_default_plus': _d(p.tolerancia_default_plus),
                })
            manifest_layers.append(self._write(out_dir, '03_pom_masters.json',
                {'layer': 'pom_masters', 'count': len(m_rows), 'rows': m_rows}, indent))

            # ── 04 · CustomerPOMAlias (SENCERA, R3-O1) ─────────────────────
            a_rows = []
            for a in CustomerPOMAlias.objects.filter(customer=los).select_related('pom', 'pom__pom_global').order_by('client_code'):
                a_rows.append({
                    'customer': los.codi, 'client_code': a.client_code,
                    'pom': self._pom_key(a.pom),
                    'client_description': a.client_description, 'description_en': a.description_en,
                    'description_local': a.description_local, 'language': a.language,
                    'origen': a.origen, 'pendent_revisio': a.pendent_revisio,
                })
            manifest_layers.append(self._write(out_dir, '04_pom_aliases.json',
                {'layer': 'pom_aliases', 'count': len(a_rows), 'rows': a_rows}, indent))

            # ── 05 · Catàleg (groups + types + items) ──────────────────────
            grp_rows = [{'codi': g.codi, 'nom': g.nom, 'actiu': g.actiu}
                        for g in GarmentGroup.objects.all().order_by('codi')]
            type_rows = []
            for t in GarmentType.objects.select_related('garment_type_global').all().order_by('codi_client'):
                type_rows.append({
                    'codi_client': t.codi_client, 'nom_client': t.nom_client, 'grup': t.grup,
                    'actiu': t.actiu, 'nom_en': t.nom_en, 'nom_ca': t.nom_ca, 'nom_es': t.nom_es,
                    'is_system': t.is_system, 'construccio_habitual': t.construccio_habitual,
                    'descripcio': t.descripcio,
                    'garment_type_global': (t.garment_type_global.codi if t.garment_type_global_id else None),
                })
            item_rows = []
            for it in GarmentTypeItem.objects.select_related('garment_type', 'base_size_definition',
                                                             'base_size_definition__size_system',
                                                             'grading_rule_set').all().order_by('garment_type__codi_client', 'code'):
                item_rows.append({
                    'garment_type': it.garment_type.codi_client, 'code': it.code,
                    'complexity_order': it.complexity_order,
                    'base_size_definition': self._sizedef_key(it.base_size_definition),
                    'grading_rule_set': (it.grading_rule_set.nom if it.grading_rule_set_id else None),
                })
            manifest_layers.append(self._write(out_dir, '05_garment_catalog.json',
                {'layer': 'garment_catalog',
                 'count': len(grp_rows) + len(type_rows) + len(item_rows),
                 'groups_count': len(grp_rows), 'types_count': len(type_rows), 'items_count': len(item_rows),
                 'groups': grp_rows, 'types': type_rows, 'items': item_rows}, indent))

            # ── 06 · GarmentPOMMap + ItemBaseMeasurement ───────────────────
            map_rows = []
            for m in GarmentPOMMap.objects.select_related('garment_type_item', 'garment_type_item__garment_type',
                                                          'pom', 'pom__pom_global').all().order_by('garment_type_item_id', 'ordre'):
                map_rows.append({
                    'garment_type_item': self._gti_key(m.garment_type_item), 'pom': self._pom_key(m.pom),
                    'obligatori': m.obligatori, 'is_key': m.is_key, 'nivell': m.nivell,
                    'ordre': m.ordre, 'pendent_revisio': m.pendent_revisio,
                })
            ib_rows = []
            for ib in ItemBaseMeasurement.objects.select_related('garment_type_item', 'garment_type_item__garment_type',
                                                                'pom', 'pom__pom_global').all().order_by('garment_type_item_id', 'pom_id'):
                ib_rows.append({
                    'garment_type_item': self._gti_key(ib.garment_type_item), 'pom': self._pom_key(ib.pom),
                    'base_value_cm': _d(ib.base_value_cm), 'nom_fitxa': ib.nom_fitxa,
                })
            manifest_layers.append(self._write(out_dir, '06_pom_maps.json',
                {'layer': 'pom_maps', 'count': len(map_rows) + len(ib_rows),
                 'garment_pom_maps_count': len(map_rows), 'item_base_measurements_count': len(ib_rows),
                 'garment_pom_maps': map_rows, 'item_base_measurements': ib_rows}, indent))

            # ── 07 · SizeSystem LOS + SizeDefinition + targets ─────────────
            ss_qs = SizeSystem.objects.filter(customer_codi=CUSTOMER_CODI).prefetch_related('targets', 'talles').order_by('codi')
            ss_rows, def_rows = [], []
            for ss in ss_qs:
                ss_rows.append({
                    'codi': ss.codi, 'nom': ss.nom, 'actiu': ss.actiu,
                    'customer_codi': ss.customer_codi,
                    'targets': sorted(ss.targets.values_list('codi', flat=True)),
                    'parent': (ss.parent.codi if ss.parent_id else None),
                })
                for sd in ss.talles.all().order_by('ordre'):
                    def_rows.append({
                        'size_system': ss.codi, 'etiqueta': sd.etiqueta, 'ordre': sd.ordre,
                        'valor_numeric': _d(sd.valor_numeric),
                        'body_height_cm': _d(sd.body_height_cm), 'body_bust_cm': _d(sd.body_bust_cm),
                        'body_waist_cm': _d(sd.body_waist_cm), 'body_hip_cm': _d(sd.body_hip_cm),
                        'age_months_min': sd.age_months_min, 'age_months_max': sd.age_months_max,
                    })
            manifest_layers.append(self._write(out_dir, '07_size_systems.json',
                {'layer': 'size_systems', 'count': len(ss_rows) + len(def_rows),
                 'size_systems_count': len(ss_rows), 'size_definitions_count': len(def_rows),
                 'size_systems': ss_rows, 'size_definitions': def_rows}, indent))

            # ── 08 · GradingRuleSet + RuleSetScopeNode ─────────────────────
            rs_rows = []
            for r in GradingRuleSet.objects.filter(id__in=rs_ids).select_related(
                    'garment_group', 'size_system', 'garment_type_item',
                    'garment_type_item__garment_type', 'construction', 'fit_type', 'target'
            ).prefetch_related('targets').order_by('nom'):
                rs_rows.append({
                    'nom': r.nom, 'origen': r.origen, 'actiu': r.actiu,
                    'customer': los.codi,
                    'size_system': (r.size_system.codi if r.size_system_id else None),
                    'garment_group': (r.garment_group.codi if r.garment_group_id else None),
                    'garment_type_item': self._gti_key(r.garment_type_item),
                    'construction': (r.construction.codi if r.construction_id else None),
                    'fit_type': (r.fit_type.codi if r.fit_type_id else None),
                    'target_legacy': (r.target.codi if r.target_id else None),
                    'targets': sorted(r.targets.values_list('codi', flat=True)),
                    'version_number': r.version_number, 'codi_sistema': r.codi_sistema,
                    'pendents_vincular': r.pendents_vincular,
                })
            sn_rows = []
            for sn in RuleSetScopeNode.objects.filter(rule_set_id__in=rs_ids).select_related(
                    'rule_set', 'garment_group', 'garment_type', 'garment_type_item',
                    'garment_type_item__garment_type').order_by('rule_set__nom'):
                sn_rows.append({
                    'rule_set': sn.rule_set.nom, 'node_type': sn.node_type,
                    'garment_group': (sn.garment_group.codi if sn.garment_group_id else None),
                    'garment_type': (sn.garment_type.codi_client if sn.garment_type_id else None),
                    'garment_type_item': self._gti_key(sn.garment_type_item),
                })
            manifest_layers.append(self._write(out_dir, '08_rulesets.json',
                {'layer': 'rulesets', 'count': len(rs_rows) + len(sn_rows),
                 'rulesets_count': len(rs_rows), 'scope_nodes_count': len(sn_rows),
                 'rulesets': rs_rows, 'scope_nodes': sn_rows}, indent))

            # ── 09 · GradingRule ───────────────────────────────────────────
            gr_rows = []
            for gr in GradingRule.objects.filter(rule_set_id__in=rs_ids).select_related(
                    'rule_set', 'pom', 'pom__pom_global', 'talla_base', 'talla_base__size_system'
            ).order_by('rule_set__nom', 'pom__codi_client'):
                gr_rows.append({
                    'rule_set': gr.rule_set.nom, 'pom': self._pom_key(gr.pom),
                    'talla_base': self._sizedef_key(gr.talla_base), 'logica': gr.logica,
                    'increment': _d(gr.increment), 'valors_step': gr.valors_step,
                    'increment_base': _d(gr.increment_base), 'increment_break': _d(gr.increment_break),
                    'talla_break_label': gr.talla_break_label, 'actiu': gr.actiu,
                })
            manifest_layers.append(self._write(out_dir, '09_rules.json',
                {'layer': 'rules', 'count': len(gr_rows), 'rows': gr_rows}, indent))

            # ── 10 · SizingProfile (customer LOS) ──────────────────────────
            sp_rows = []
            for sp in SizingProfile.objects.filter(customer=los).select_related(
                    'target', 'garment_type', 'construction', 'fit_type', 'size_system', 'grading_rule_set'
            ).order_by('target__display_order', 'garment_type__codi_client'):
                sp_rows.append({
                    'target': sp.target.codi, 'garment_type': sp.garment_type.codi_client,
                    'construction': sp.construction.codi, 'fit_type': sp.fit_type.codi,
                    'size_system': sp.size_system.codi, 'grading_rule_set': sp.grading_rule_set.nom,
                    'customer': los.codi, 'is_default': sp.is_default, 'version': sp.version,
                    'notes': sp.notes,
                })
            manifest_layers.append(self._write(out_dir, '10_profiles.json',
                {'layer': 'profiles', 'count': len(sp_rows), 'rows': sp_rows}, indent))

            # ── 11 · DocumentTemplate (capçalera, R9) ──────────────────────
            dt_rows = []
            for dt in DocumentTemplate.objects.all().order_by('nom'):
                f_name, f_asset = self._copy_asset(dt.fitxer_template, assets_dir)
                dt_rows.append({
                    'nom': dt.nom, 'descripcio': dt.descripcio,
                    'fitxer_template': f_name, 'fitxer_asset': f_asset,
                    'metadata_schema': dt.metadata_schema, 'is_sample': dt.is_sample,
                    'origen': dt.origen, 'actiu': dt.actiu,
                })
            manifest_layers.append(self._write(out_dir, '11_document_templates.json',
                {'layer': 'document_templates', 'count': len(dt_rows), 'rows': dt_rows}, indent))

            # ── manifest ───────────────────────────────────────────────────
            manifest = {
                'package': 'losan',
                'source_schema': schema,
                'commit': opts['commit'],
                'customer_codi': CUSTOMER_CODI,
                'design': {
                    'pom_natural_key': 'pom_global.codi | codi_client (R2)',
                    'rulesets_scope': 'customer=LOS excloent origen IS NULL (grs 104 legacy, R6)',
                    'pom_masters_scope': 'unió self-consistent: aliases ∪ rules ∪ ALL garment_pom_maps ∪ item_base_measurements',
                },
                'gate_qa_targets': {
                    'aliases': 196, 'lospom_globals': 149, 'pom_masters_gate_estimate': 197,
                    'garment_type_items': 62, 'garment_types_active': 17, 'garment_groups': 12,
                    'garment_pom_maps': 1748, 'item_base_measurements': 37,
                    'size_systems': 11, 'size_definitions': 86,
                    'rulesets': 18, 'rules': 390, 'profiles': 18, 'rules_on_inactive_pom': 0,
                },
                'layers': manifest_layers,
            }
            man_data = json.dumps(manifest, ensure_ascii=False, indent=indent)
            with open(os.path.join(out_dir, 'manifest.json'), 'w', encoding='utf-8') as fh:
                fh.write(man_data)

        # ── informe a stdout ───────────────────────────────────────────────
        self.stdout.write(self.style.SUCCESS(f'Paquet LOSAN exportat a {out_dir}'))
        for lay in manifest_layers:
            self.stdout.write(f"  {lay['file']:<30} count={lay['count']}  {lay['sha256'][:12]}")
