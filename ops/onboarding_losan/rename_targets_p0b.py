"""P0b — RENAME DE TARGETS al vocabulari real de LOSAN (10 targets amb gènere).

    DELTA_APPLY=0 ./venv/bin/python manage.py shell < rename_targets_p0b.py   # dry-run (defecte)
    DELTA_APPLY=1 ./venv/bin/python manage.py shell < rename_targets_p0b.py   # aplica

⚠️ NO EXECUTAR ABANS QUE EL CANVI DE CODI ESTIGUI DESPLEGAT.
   Aquest script només mou DADES. El vocabulari també viu hardcoded a:
     · backend/fhort/pom/models.py  → Target.CODI_CHOICES
     · frontend/src/components/grading/gradingAxes.js → TARGETS
     · frontend/src/i18n/{ca,en,es}.json → claus target_<CODI>
     · backend/fhort/pom/seed_data/{losan_ss27,losan_grading_v3}.py i 2 management commands
   Si la BD es renombra sense el codi, el wizard es queda SENSE targets seleccionables
   (TARGETS és una llista hardcoded que el frontend itera). Vegeu DIAGNOSI_CENS §P0b.

Decisions preses (Agus, 2026-07-24):
  · BABY_UNISEX → NEWBORN_UNISEX (opció b: es manté un target unisex propi de nadó).
  · Abast: els TRES schemas (public/fhort/los) — Target és catàleg compartit.

Disseny:
  · Rename PUR: cap alta, cap baixa, cap pk tocada. Només UPDATE de valors literals.
  · Un sol transaction.atomic() per a TOTS els schemas: o hi entren tots o cap.
  · Ordre A→B→C→D amb codis temporals `_TMP_*`, perquè `BABY_BOY`/`BABY_GIRL` són alhora
    origen (→NEWBORN_*) i destí (←TODDLER_*) i un rename directe se sobreescriuria a mig camí.
  · Idempotent: si el codi vell ja no hi és i el nou sí, el pas se salta.
  · Dry-run = mateix camí de codi + ROLLBACK final.
"""
import os
from django.db import transaction, connection
from django_tenants.utils import schema_context
from fhort.pom.models import Target, SizeSystem, GradingRuleSet, SizingProfile

APPLY = os.environ.get('DELTA_APPLY') == '1'
SCHEMAS = ['public', 'fhort', 'los']
print(f'\n{"="*78}\n  P0b · RENAME DE TARGETS — MODE: {"APPLY" if APPLY else "DRY-RUN"}\n{"="*78}')


class Rollback(Exception):
    """Senyal de fi de dry-run."""


# ── Taula de conversió, en l'ordre EXACTE d'execució ─────────────────────────────────────
# `BABY_UNISEX` no col·lisiona amb res, però passa pel temporal igualment: la família
# baby/newborn es mou sencera amb el mateix patró (una excepció «perquè aquesta no cal»
# és exactament el lloc on s'esmuny un error).
PASSOS = [
    ('A · aparcar la família nadó als temporals', [
        ('BABY_BOY',    '_TMP_BABY_BOY'),
        ('BABY_GIRL',   '_TMP_BABY_GIRL'),
        ('BABY_UNISEX', '_TMP_BABY_UNISEX'),
    ]),
    ('B · toddler passa a ser baby', [
        ('TODDLER_BOY',  'BABY_BOY'),
        ('TODDLER_GIRL', 'BABY_GIRL'),
    ]),
    ('C · els temporals baixen a newborn', [
        ('_TMP_BABY_BOY',    'NEWBORN_BOY'),
        ('_TMP_BABY_GIRL',   'NEWBORN_GIRL'),
        ('_TMP_BABY_UNISEX', 'NEWBORN_UNISEX'),
    ]),
    ('D · kids', [
        ('BOY',  'KID_BOY'),
        ('GIRL', 'KID_GIRL'),
    ]),
]
#: Codis finals esperats (els 10 de LOSAN + els 3 del sistema que NO es toquen).
FINALS = {'MAN', 'WOMAN', 'TEEN_BOY', 'TEEN_GIRL', 'KID_BOY', 'KID_GIRL',
          'BABY_BOY', 'BABY_GIRL', 'NEWBORN_BOY', 'NEWBORN_GIRL', 'NEWBORN_UNISEX'}
INTACTES = {'UNISEX_ADULT', 'MATERNITY'}
#: Tots els valors d'origen legítims (per al guard de valors desconeguts).
ORIGENS = {o for _, parells in PASSOS for o, _ in parells} | FINALS | INTACTES


def te_models_app():
    """`public` no té la taula de models_app (app només de tenant)."""
    with connection.cursor() as cur:
        cur.execute("SELECT to_regclass(%s)", [f'{connection.schema_name}.models_app_model'])
        return cur.fetchone()[0] is not None


def foto(schema):
    """Recompte de referències a target, per taula. Ha de ser IDÈNTIC abans i després."""
    with schema_context(schema):
        f = {
            'Target': Target.objects.count(),
            'SizeSystem.targets': SizeSystem.targets.through.objects.count(),
            'GradingRuleSet.targets': GradingRuleSet.targets.through.objects.count(),
            'SizingProfile.target': SizingProfile.objects.filter(target__isnull=False).count(),
        }
        if te_models_app():
            with connection.cursor() as cur:
                cur.execute("SELECT count(*) FROM models_app_model WHERE target IS NOT NULL AND target <> ''")
                f['Model.target'] = cur.fetchone()[0]
        return f


def guard_valors(schema):
    """STOP si algun valor de target NO està cobert pel mapeig — mai inventar-ne cap."""
    with schema_context(schema):
        desconeguts = set(Target.objects.exclude(codi__in=ORIGENS).values_list('codi', flat=True))
        if te_models_app():
            with connection.cursor() as cur:
                cur.execute("SELECT DISTINCT target FROM models_app_model "
                            "WHERE target IS NOT NULL AND target <> ''")
                desconeguts |= {r[0] for r in cur.fetchall()} - ORIGENS
        if desconeguts:
            raise SystemExit(f'⛔ STOP · {schema}: valors de target FORA del mapeig: {sorted(desconeguts)}')
        # Els temporals no poden existir abans de començar (residu d'una execució avortada).
        residus = set(Target.objects.filter(codi__startswith='_TMP_').values_list('codi', flat=True))
        if residus:
            raise SystemExit(f'⛔ STOP · {schema}: hi ha temporals residuals: {sorted(residus)} '
                             f'— una execució anterior es va quedar a mig camí. Revisar a mà.')


def renombra(schema):
    total_t = total_m = 0
    with schema_context(schema):
        hi_ha_models = te_models_app()
        for titol, parells in PASSOS:
            linies = []
            for antic, nou in parells:
                t = Target.objects.filter(codi=antic).first()
                if not t:
                    if Target.objects.filter(codi=nou).exists():
                        linies.append(f'      ═ {antic} → {nou}: ja fet')
                    continue
                n_m = 0
                if hi_ha_models:
                    with connection.cursor() as cur:
                        cur.execute("SELECT count(*) FROM models_app_model WHERE target = %s", [antic])
                        n_m = cur.fetchone()[0]
                linias_extra = (f' · Model.target={n_m}' if hi_ha_models else '')
                linies.append(f'      → {antic:16} → {nou:16} (Target pk={t.pk}{linias_extra})')
                if APPLY:
                    Target.objects.filter(pk=t.pk).update(codi=nou)
                    if hi_ha_models and n_m:
                        with connection.cursor() as cur:
                            cur.execute("UPDATE models_app_model SET target = %s WHERE target = %s",
                                        [nou, antic])
                total_t += 1
                total_m += n_m
            if linies:
                print(f'    PAS {titol}')
                for l in linies:
                    print(l)
    return total_t, total_m


try:
    with transaction.atomic():
        abans = {}
        for sch in SCHEMAS:
            guard_valors(sch)
            abans[sch] = foto(sch)
        print('\n── FOTO PRÈVIA ' + '─' * 62)
        for sch in SCHEMAS:
            print(f'  {sch:8} {abans[sch]}')

        print('\n── RENAME ' + '─' * 67)
        for sch in SCHEMAS:
            print(f'\n  ▸ schema {sch}')
            t, m = renombra(sch)
            print(f'    resum: {t} Target.codi · {m} Model.target')

        print('\n── FOTO POSTERIOR (ha de coincidir fila a fila) ' + '─' * 30)
        ok = True
        for sch in SCHEMAS:
            despres = foto(sch)
            igual = despres == abans[sch]
            ok &= igual
            print(f'  {sch:8} {despres}   {"✔" if igual else "✘ DIVERGEIX"}')
        if not ok:
            raise SystemExit('⛔ STOP · el recompte de referències ha canviat — rollback.')

        print('\n── AUDITORIA SQL DIRECTA ' + '─' * 53)
        for sch in SCHEMAS:
            with schema_context(sch):
                with connection.cursor() as cur:
                    cur.execute("SELECT codi FROM pom_target ORDER BY display_order, codi")
                    codis = [r[0] for r in cur.fetchall()]
                    print(f'  {sch:8} Target.codi = {codis}')
                    if te_models_app():
                        cur.execute("SELECT target, count(*) FROM models_app_model "
                                    "WHERE target IS NOT NULL AND target <> '' GROUP BY target ORDER BY 2 DESC")
                        print(f'  {"":8} Model.target = {dict(cur.fetchall())}')

        if not APPLY:
            raise Rollback
except Rollback:
    print('\n' + '=' * 78)
    print('  DRY-RUN acabat → ROLLBACK. Cap canvi persistit.')
    print('=' * 78)
else:
    if APPLY:
        print('\n' + '=' * 78)
        print('  APPLY acabat → COMMIT.')
        print('  SEGÜENT: verificar a la UI que els 10 targets surten a TotesLesSuperfícies')
        print('  (ModelWizard · GradingRuleSets/TargetPills · SizingProfileSelector · CascadeSelector)')
        print('  i que cap mostra encara BOY/GIRL/TODDLER_*/BABY_* amb el significat antic.')
        print('=' * 78)
