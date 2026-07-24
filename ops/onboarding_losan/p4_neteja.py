"""P4 — NETEJA (schema `los`). Idempotent, atòmic, dry-run per defecte.

    DELTA_APPLY=0 ./venv/bin/python manage.py shell < p4_neteja.py   # dry-run (defecte)
    DELTA_APPLY=1 ./venv/bin/python manage.py shell < p4_neteja.py   # aplica

Cinc operacions, totes SOFT (cap DELETE):
  1. Ruleset residual id=55 → el seu únic model a grading_rule_set=NULL + Watchpoint
     GRADING_PENDENT; el ruleset a actiu=False.
  2. SizeSystem GIRL_LOS_03 → actiu=False.
  3. GarmentTypeItem.name → nom humà EN derivat del `code` (els 62 són buits).
  4. SizingProfile per BABY_BOY i BABY_UNISEX × 3 rulesets New Born (mirall del BABY_GIRL).
  5. Els 4 GarmentGroup buits → actiu=False.
"""
import os
from django.db import transaction, connection
from django_tenants.utils import schema_context
from fhort.pom.models import (GradingRuleSet, SizeSystem, SizingProfile, GarmentGroup,
                              GarmentType, Target, ConstructionType, FitType)
from fhort.tasks.models import GarmentTypeItem, Customer
from fhort.models_app.models import Model, Watchpoint

APPLY = os.environ.get('DELTA_APPLY') == '1'
print(f'\n{"="*78}\n  P4 · NETEJA — MODE: {"APPLY" if APPLY else "DRY-RUN"}\n{"="*78}')


class Rollback(Exception):
    pass


WP_TEXT = ('GRADING_PENDENT — el contenidor residual «LOSAN IBERIA SA · Newborn · LOS Baby 3-36M» '
           's\'ha desactivat (P4, 2026-07-24). Aquest model queda sense graduació, igual que els '
           'seus 24 germans del mateix parell (baby_dress × BABY_LOS_01), a l\'espera de font.')

#: Excepció de titularització: `t_shirt` → «T-Shirt» (el títol pla donaria «T Shirt»).
NOM_EXCEPCIONS = {'t_shirt': 'T-Shirt'}


def nom_huma(code):
    if code in NOM_EXCEPCIONS:
        return NOM_EXCEPCIONS[code]
    return ' '.join(w.capitalize() for w in code.split('_'))


def p4_1_residual():
    print('\n── 1 · Ruleset residual (id=55) ' + '─' * 46)
    rs = GradingRuleSet.objects.filter(nom='LOSAN IBERIA SA · Newborn · LOS Baby 3-36M').first()
    if not rs:
        print('  ✘ no trobat — SALTAT')
        return
    models = list(Model.objects.filter(grading_rule_set=rs))
    print(f'  ruleset pk={rs.pk} actiu={rs.actiu} regles={rs.regles.count()} models={len(models)}')
    for m in models:
        ja = Watchpoint.objects.filter(model=m, text__startswith='GRADING_PENDENT').exists()
        print(f'    model pk={m.pk} codi={getattr(m, "codi", "?")} → grading_rule_set=NULL'
              f' + Watchpoint{" (ja existeix)" if ja else ""}')
        if APPLY:
            Model.objects.filter(pk=m.pk).update(grading_rule_set=None)
            if not ja:
                Watchpoint.objects.create(model=m, text=WP_TEXT, estat='open',
                                          dades={'codi': 'GRADING_PENDENT', 'origen': 'P4-2026-07-24'})
    if rs.actiu:
        print(f'  ruleset → actiu=False (soft, MAI delete; les {rs.regles.count()} regles es conserven)')
        if APPLY:
            GradingRuleSet.objects.filter(pk=rs.pk).update(actiu=False)
    else:
        print('  ═ ruleset ja inactiu')


def p4_2_girl03():
    print('\n── 2 · SizeSystem GIRL_LOS_03 ' + '─' * 48)
    s = SizeSystem.objects.filter(codi='GIRL_LOS_03').first()
    if not s:
        print('  ✘ no trobat — SALTAT')
        return
    us = (GradingRuleSet.objects.filter(size_system=s).count(),
          SizingProfile.objects.filter(size_system=s).count(),
          Model.objects.filter(size_system=s).count())
    print(f'  pk={s.pk} actiu={s.actiu} · rulesets={us[0]} profiles={us[1]} models={us[2]}')
    if any(us):
        print('  ⛔ STOP: té ús real — NO es desactiva (contradiu el cens).')
        raise SystemExit('P4.2 avortat')
    if s.actiu:
        print('  → actiu=False (soft). Les 9 SizeDefinition es conserven.')
        if APPLY:
            SizeSystem.objects.filter(pk=s.pk).update(actiu=False)
    else:
        print('  ═ ja inactiu')


def p4_3_noms():
    print('\n── 3 · GarmentTypeItem.name ' + '─' * 50)
    buits = GarmentTypeItem.objects.filter(name='').order_by('garment_type__grup', 'code')
    print(f'  items amb name buit: {buits.count()} / {GarmentTypeItem.objects.count()}')
    for it in buits:
        n = nom_huma(it.code)
        print(f'    {it.code:20} → {n!r}')
        if APPLY:
            GarmentTypeItem.objects.filter(pk=it.pk).update(name=n)
    if not buits.exists():
        print('  ═ tots ja tenen nom — idempotent')


def p4_4_profiles():
    print('\n── 4 · SizingProfile per BABY_BOY i BABY_UNISEX ' + '─' * 31)
    ref = list(SizingProfile.objects.filter(target__codi='BABY_GIRL',
                                            garment_type__codi_client='NEWBORN')
               .select_related('garment_type', 'construction', 'fit_type', 'size_system',
                               'grading_rule_set', 'customer'))
    print(f'  perfils de referència (BABY_GIRL × New Born): {len(ref)}')
    if not ref:
        print('  ⛔ STOP: cap perfil de referència — no invento eixos.')
        raise SystemExit('P4.4 avortat')
    fets = saltats = 0
    for codi in ['BABY_BOY', 'BABY_UNISEX']:
        tg = Target.objects.filter(codi=codi).first()
        if not tg:
            print(f'  ✘ target {codi} inexistent — SALTAT')
            continue
        for p in ref:
            ja = SizingProfile.objects.filter(
                target=tg, garment_type=p.garment_type, construction=p.construction,
                fit_type=p.fit_type, size_system=p.size_system,
                grading_rule_set=p.grading_rule_set).exists()
            if ja:
                saltats += 1
                continue
            print(f'    + {codi:12} × {p.grading_rule_set.nom}')
            if APPLY:
                SizingProfile.objects.create(
                    target=tg, garment_type=p.garment_type, construction=p.construction,
                    fit_type=p.fit_type, size_system=p.size_system,
                    grading_rule_set=p.grading_rule_set, customer=p.customer,
                    is_default=p.is_default, version=p.version,
                    notes='P4 2026-07-24 — mirall del perfil BABY_GIRL equivalent')
            fets += 1
    print(f'  RESUM: {fets} perfils nous, {saltats} ja existents')


def p4_5_grups():
    print('\n── 5 · GarmentGroup buits ' + '─' * 52)
    for g in GarmentGroup.objects.filter(actiu=True).order_by('codi'):
        nt = GarmentType.objects.filter(grup=g.codi).count()
        ni = GarmentTypeItem.objects.filter(garment_type__grup=g.codi).count()
        nrs = GradingRuleSet.objects.filter(garment_group=g).count()
        if nt or ni or nrs:
            continue
        print(f'  → {g.codi:14} ({g.nom}) buit: types={nt} items={ni} rulesets={nrs} · actiu=False')
        if APPLY:
            GarmentGroup.objects.filter(pk=g.pk).update(actiu=False)
    if not GarmentGroup.objects.filter(actiu=False).exists() and not APPLY:
        pass


def auditoria():
    print('\n── AUDITORIA SQL DIRECTA ' + '─' * 53)
    with connection.cursor() as cur:
        cur.execute("SELECT actiu, count(*) FROM pom_gradingruleset GROUP BY actiu ORDER BY 1")
        print('  GradingRuleSet per actiu:', dict(cur.fetchall()))
        cur.execute("SELECT actiu, count(*) FROM pom_sizesystem GROUP BY actiu ORDER BY 1")
        print('  SizeSystem per actiu:    ', dict(cur.fetchall()))
        cur.execute("SELECT actiu, count(*) FROM pom_garmentgroup GROUP BY actiu ORDER BY 1")
        print('  GarmentGroup per actiu:  ', dict(cur.fetchall()))
        cur.execute("SELECT count(*) FROM tasks_garmenttypeitem WHERE name = ''")
        print('  GarmentTypeItem sense nom:', cur.fetchone()[0])
        cur.execute("SELECT count(*) FROM pom_sizingprofile")
        print('  SizingProfile totals:    ', cur.fetchone()[0])
        cur.execute("SELECT count(*) FROM models_app_model WHERE grading_rule_set_id IS NULL")
        print('  Models sense grading:    ', cur.fetchone()[0])
        cur.execute("SELECT count(*) FROM models_app_watchpoint WHERE text LIKE 'GRADING_PENDENT%'")
        print('  Watchpoints GRADING_PENDENT:', cur.fetchone()[0])


try:
    with transaction.atomic():
        with schema_context('los'):
            p4_1_residual()
            p4_2_girl03()
            p4_3_noms()
            p4_4_profiles()
            p4_5_grups()
            auditoria()
        if not APPLY:
            raise Rollback
except Rollback:
    print('\n' + '=' * 78 + '\n  DRY-RUN acabat → ROLLBACK. Cap canvi persistit.\n' + '=' * 78)
else:
    if APPLY:
        print('\n' + '=' * 78 + '\n  APPLY acabat → COMMIT.\n' + '=' * 78)
