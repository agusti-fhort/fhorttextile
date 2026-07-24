"""P2b (altes autoritzades + àmbit baby_dress) + P1 (Woman Bottoms Alpha).

    DELTA_APPLY=0 ./venv/bin/python manage.py shell < p1_p2b_altes.py   # dry-run
    DELTA_APPLY=1 ./venv/bin/python manage.py shell < p1_p2b_altes.py   # aplica

Autoritzacions d'Agus (2026-07-24), totes amb conflicte real verificat:
  · D11H/D11W · T1W/T1H · T2W/T2H · ML/MS/MB/MO · FL/FS · MD  → altes netes
  · GAL/GAS NO (la llei és «un model concret ho exigeix», no el màster en abstracte)
  · baby_dress entra a l'àmbit d'Onepieces (24 dels seus models ja hi apunten per FK)
  · Woman Bottoms Alpha: 10 POMs del màster + 15 HERETATS del numèric id=54, marcats

⚠️ PROVINENÇA — el camp demanat no existeix:
   `GradingRuleSet.origen` té choices tancats (CANONICAL/CLIENT_RUN/IMPORT): afegir
   `HERETAT_NUMERIC` seria canvi de codi, impossible des de PROD. `GradingRule` no té
   cap camp de provinença, i `Watchpoint` exigeix FK a Model (no es pot penjar d'un
   ruleset). Solució adoptada: el ruleset queda `origen=CLIENT_RUN` (és cert) i el
   préstec es fa visible amb un **Watchpoint als 30 models repuntats** que llista els
   15 POMs heretats. És l'únic ancoratge que el model de dades permet avui.
"""
import os
from decimal import Decimal
from django.db import transaction, connection
from django_tenants.utils import schema_context
from fhort.pom.models import (GradingRuleSet, GradingRule, POMMaster, POMGlobal, CustomerPOMAlias,
                              SizeDefinition, SizeSystem, SizingProfile, GarmentGroup, GarmentType,
                              Target, ConstructionType, FitType, RuleSetScopeNode)
from fhort.tasks.models import Customer, GarmentTypeItem
from fhort.models_app.models import Model, Watchpoint

APPLY = os.environ.get('DELTA_APPLY') == '1'
print(f'\n{"="*78}\n  P2b + P1 — MODE: {"APPLY" if APPLY else "DRY-RUN"}\n{"="*78}')


class Rollback(Exception):
    pass


# ── A · ALTES DE POM (LOSPOM-688…) ───────────────────────────────────────────────────────
ALTES = [
    ('LOSPOM-688', 'D11H', 'HIP LOCATION FROM HPS'),
    ('LOSPOM-689', 'D11W', 'HIP LOCATION FROM WAIST'),
    ('LOSPOM-690', 'T1W', 'FRONT RISE FROM WAIST'),
    ('LOSPOM-691', 'T1H', 'FRONT RISE FROM HPS'),
    ('LOSPOM-692', 'T2W', 'BACK RISE FROM WAIST'),
    ('LOSPOM-693', 'T2H', 'BACK RISE FROM HPS'),
    ('LOSPOM-694', 'ML', 'TOTAL LENGTH LONG'),
    ('LOSPOM-695', 'MS', 'TOTAL LENGTH SHORT'),
    ('LOSPOM-696', 'MB', 'TOTAL LENGTH BODY'),
    ('LOSPOM-697', 'MO', 'TOTAL LENGTH OVERALL'),
    ('LOSPOM-698', 'FL', 'LEG OPENING LONG'),
    ('LOSPOM-699', 'FS', 'LEG OPENING SHORT'),
    ('LOSPOM-700', 'MD', 'TOTAL LENGTH DRESS'),
]

# ── B · P2b: sembra dels codis nous als contenidors NEWBORN ──────────────────────────────
P2B = {
    'LOS New Born Knit — Tops': {'D11H': 0.0, 'D11W': 0.5},
    'LOS New Born Knit — Onepieces': {'D11H': 0.0, 'D11W': 0.5, 'MD': 3.0},
    'LOS New Born Knit — Bottoms': {'D11W': 0.5, 'T1W': 0.7, 'T2W': 0.7, 'T1H': 1.5,
                                    'T2H': 1.9, 'ML': 3.7, 'MS': 1.5, 'MB': 2.5, 'MO': 3.5},
}

# ── C · P1: Woman Bottoms Alpha (part LINEAR; el sostre és P3) ────────────────────────────
ALPHA_MASTER = {'WA': 3.0, 'HI PA': 3.0, 'THI': 2.1, 'D22': 0.5, 'KNE': 0.7,
                'FL': 0.5, 'FS': 2.1, 'RI FR': 1.0, 'RI BK': 1.2, 'ML': 0.5, 'MS': 1.0,
                'D11RH': 0.5, 'D11RM': 0.5, 'D11RL': 0.5}
ALPHA_NOM = 'LOS Woman Woven — Bottoms (Alpha)'
WP_ALPHA = ('BOTTOMS_ALPHA_POMS_SENSE_FONT_PROPIA — aquest model s\'ha repuntat a '
            f'«{ALPHA_NOM}». 14 POMs vénen del màster WOMAN BOTTOM ALFA; els altres 15 '
            '({poms}) són un PRÉSTEC CONSCIENT del contenidor numèric «LOS Woman Woven — Bottoms»: '
            'majoritàriament ferratges i butxaques amb FIXED inc=0, probablement invariants '
            'd\'escala, però SENSE font pròpia verificada. Revisar quan arribi el màster.')
WP_MAN = ('MAN_ALPHA_BOTTOMS_SENSE_FONT — aquest model té size_system alfa (MAN_LOS_01) però el seu '
          'contenidor de graduació és numèric (MAN_NUM_LOS_01). No es corregeix perquè el màster MAN '
          'no ha arribat. Conegut i deliberat (Z5 del cens 2026-07-24).')

nou_poms, noves_regles, wp_creats = [], [], 0

with schema_context('los'):
    self_c = Customer.objects.get(is_self=True)
    try:
        with transaction.atomic():
            # ── A ──
            print('\n── A · ALTES DE POM ' + '─' * 57)
            for glob, codi, nom in ALTES:
                if POMMaster.objects.filter(codi_client=codi).exists():
                    print(f'  ═ {codi:6} ja existeix')
                    continue
                print(f'  + {codi:6} {glob:12} {nom}')
                nou_poms.append(codi)
                if APPLY:
                    g, _ = POMGlobal.objects.get_or_create(
                        codi=glob, defaults=dict(nom_en=nom, nom_ca='', nom_es='',
                                                 categoria='LOSAN', unitat='cm', actiu=True))
                    m = POMMaster.objects.create(pom_global=g, codi_client=codi, nom_client=nom,
                                                 actiu=True, pendent_revisio=False,
                                                 origen_import='màster v3 P1/P2b 2026-07-24')
                    CustomerPOMAlias.objects.create(customer=self_c, pom=m, client_code=codi,
                                                    description_en=nom, origen='DICCIONARI')
            print(f'  RESUM: {len(nou_poms)} POMs nous')

            alias = {a.client_code: a.pom for a in CustomerPOMAlias.objects.select_related('pom').all()}

            # ── B ──
            print('\n── B · P2b: sembra als contenidors NEWBORN ' + '─' * 34)
            for nom_rs, taula in P2B.items():
                rs = GradingRuleSet.objects.get(nom=nom_rs)
                base = SizeDefinition.objects.get(size_system=rs.size_system, etiqueta='00/01')
                abans = rs.regles.count()
                for codi, val in taula.items():
                    p = alias.get(codi)
                    if not p:
                        print(f'    ⚠️ {codi} sense POM (dry-run: encara no creat)')
                        continue
                    if GradingRule.objects.filter(rule_set=rs, pom=p).exists():
                        print(f'    ═ {codi} ja hi és'); continue
                    print(f'    + {codi:6} → {val} (LINEAR pur)')
                    noves_regles.append((nom_rs, codi))
                    if APPLY:
                        GradingRule.objects.create(rule_set=rs, pom=p, talla_base=base,
                                                   logica='LINEAR', increment=Decimal(str(val)),
                                                   increment_base=Decimal(str(val)), actiu=True)
                print(f'  {nom_rs}: {abans} → {GradingRule.objects.filter(rule_set=rs).count()}')

            # baby_dress dins l'àmbit d'Onepieces
            rs45 = GradingRuleSet.objects.get(nom='LOS New Born Knit — Onepieces')
            it_bd = GarmentTypeItem.objects.get(code='baby_dress')
            if RuleSetScopeNode.objects.filter(rule_set=rs45, garment_type_item=it_bd).exists():
                print('  ═ baby_dress ja és a l\'àmbit d\'Onepieces')
            else:
                print(f'  + scope ITEM baby_dress (pk={it_bd.pk}) → Onepieces')
                if APPLY:
                    RuleSetScopeNode.objects.create(rule_set=rs45, node_type='ITEM',
                                                    garment_type_item=it_bd)

            # ── C ──
            print('\n── C · P1: Woman Bottoms Alpha ' + '─' * 46)
            rs54 = GradingRuleSet.objects.get(nom='LOS Woman Woven — Bottoms')
            ss_alpha = SizeSystem.objects.get(codi='WOMAN_LOS_01')
            base_s = SizeDefinition.objects.get(size_system=ss_alpha, etiqueta='S')
            heretats = [r for r in rs54.regles.select_related('pom')
                        if r.pom.codi_client not in {'WA', 'HI PA', 'THI', 'D22', 'KNE',
                                                     'LEG OP', 'RI FR', 'RI BK', 'M-M79'}]
            print(f'  POMs del màster: {len(ALPHA_MASTER)} · heretats del numèric: {len(heretats)}')

            alpha = GradingRuleSet.objects.filter(nom=ALPHA_NOM).first()
            if alpha:
                print(f'  ═ ruleset ja existeix (pk={alpha.pk})')
            else:
                print(f'  + ruleset «{ALPHA_NOM}»')
                if APPLY:
                    alpha = GradingRuleSet.objects.create(
                        nom=ALPHA_NOM, origen='CLIENT_RUN', customer=self_c,
                        size_system=ss_alpha, garment_group=GarmentGroup.objects.get(codi='BOTTOMS'),
                        construction=ConstructionType.objects.get(codi='WOVEN'),
                        fit_type=FitType.objects.get(codi='REGULAR'), actiu=True,
                        is_system_default=False, version_number=1)
                    alpha.targets.set([Target.objects.get(codi='WOMAN')])
            if APPLY and alpha:
                for codi, val in ALPHA_MASTER.items():
                    p = alias.get(codi) or POMMaster.objects.filter(codi_client=codi).first()
                    if not p:
                        raise SystemExit(f'⛔ POM {codi} no resolt — avortat')
                    if not GradingRule.objects.filter(rule_set=alpha, pom=p).exists():
                        GradingRule.objects.create(rule_set=alpha, pom=p, talla_base=base_s,
                                                   logica='LINEAR', increment=Decimal(str(val)),
                                                   increment_base=Decimal(str(val)), actiu=True)
                for r in heretats:
                    if not GradingRule.objects.filter(rule_set=alpha, pom=r.pom).exists():
                        GradingRule.objects.create(rule_set=alpha, pom=r.pom, talla_base=base_s,
                                                   logica=r.logica, increment=r.increment,
                                                   increment_base=r.increment_base,
                                                   increment_break=None, actiu=True)
                # perfil que l'exposa
                if not SizingProfile.objects.filter(target__codi='WOMAN', grading_rule_set=alpha).exists():
                    SizingProfile.objects.create(
                        target=Target.objects.get(codi='WOMAN'),
                        garment_type=GarmentType.objects.get(codi_client='TAILORED_PANTS'),
                        construction=ConstructionType.objects.get(codi='WOVEN'),
                        fit_type=FitType.objects.get(codi='REGULAR'), size_system=ss_alpha,
                        grading_rule_set=alpha, customer=self_c, is_default=False, version=1,
                        notes='P1 2026-07-24 — exposa el contenidor Alpha')
                # repuntar els 30 + watchpoint
                poms_her = ', '.join(sorted(r.pom.codi_client for r in heretats))
                ms = list(Model.objects.filter(size_system=ss_alpha, grading_rule_set=rs54))
                for m in ms:
                    Model.objects.filter(pk=m.pk).update(grading_rule_set=alpha)
                    if not Watchpoint.objects.filter(model=m, text__startswith='BOTTOMS_ALPHA').exists():
                        Watchpoint.objects.create(model=m, text=WP_ALPHA.format(poms=poms_her),
                                                  estat='open',
                                                  dades={'codi': 'BOTTOMS_ALPHA_POMS_SENSE_FONT_PROPIA',
                                                         'poms_heretats': sorted(r.pom.codi_client for r in heretats)})
                        wp_creats += 1
                print(f'  regles Alpha: {GradingRule.objects.filter(rule_set=alpha).count()} · '
                      f'models repuntats: {len(ms)} · watchpoints: {wp_creats}')
            # watchpoint MAN
            mm = list(Model.objects.filter(size_system__codi='MAN_LOS_01',
                                           grading_rule_set__nom='LOS Man Woven — Bottoms'))
            print(f'  watchpoint MAN_ALPHA_BOTTOMS_SENSE_FONT sobre {len(mm)} models (grading NO tocat)')
            if APPLY:
                for m in mm:
                    if not Watchpoint.objects.filter(model=m, text__startswith='MAN_ALPHA').exists():
                        Watchpoint.objects.create(model=m, text=WP_MAN, estat='open',
                                                  dades={'codi': 'MAN_ALPHA_BOTTOMS_SENSE_FONT'})

            print('\n── AUDITORIA SQL ' + '─' * 60)
            with connection.cursor() as cur:
                for q, et in [("SELECT count(*) FROM pom_pommaster", 'POMMaster'),
                              ("SELECT count(*) FROM pom_gradingrule", 'GradingRule'),
                              ("SELECT count(*) FROM pom_gradingruleset WHERE actiu", 'RuleSets actius'),
                              ("SELECT count(*) FROM pom_sizingprofile", 'SizingProfile'),
                              ("SELECT count(*) FROM models_app_model WHERE grading_rule_set_id IS NULL", 'models sense grading'),
                              ("SELECT count(*) FROM models_app_watchpoint", 'Watchpoints')]:
                    cur.execute(q); print(f'  {et:22} {cur.fetchone()[0]}')
            if not APPLY:
                raise Rollback
    except Rollback:
        print('\n' + '=' * 78 + '\n  DRY-RUN → ROLLBACK.\n' + '=' * 78)
    else:
        if APPLY:
            print('\n' + '=' * 78 + '\n  APPLY → COMMIT.\n' + '=' * 78)
