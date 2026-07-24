"""P3 FORM — breaks Woman Tops (id=53) + sostres de Woman Bottoms Alpha.

Regla d'or (DECISIONS.md, confirmada per Agus):
  · 2a columna ≠ 0 → ritme nou des de 2XL      → talla_break_label='2XL'
  · 2a columna = 0 → SOSTRE (pla)              → talla_break_label='3XL'  (off-by-one)
El `increment_base` (1a columna) NO es toca: si divergeix del màster, s'informa i se salta.
"""
import os
from decimal import Decimal
from django.db import transaction, connection
from django_tenants.utils import schema_context
from fhort.pom.models import GradingRuleSet, GradingRule, CustomerPOMAlias

APPLY = os.environ.get('DELTA_APPLY') == '1'
print(f'\n{"="*78}\n  P3 · FORM — MODE: {"APPLY" if APPLY else "DRY-RUN"}\n{"="*78}')
class Rollback(Exception): pass

# màster WOMAN TOP/DRESS REGULAR: codi → (col1, col2)
TOPS = {'K2':(1.2,0.4),'K':(0.4,0.2),'K1':(0.2,0.0),'L3':(0.5,0.0),'L4':(0.5,0.0),'L5':(0.2,0.0),
        'BJ':(0.5,0.7),'A1':(0.8,0.4),'A2':(0.8,0.4),'B':(3.0,3.0),'C3':(1.0,1.0),'C':(3.0,3.0),
        'D':(3.0,3.0),'E':(3.0,3.0),'H6':(1.0,1.5),'GL':(1.0,0.0),'GS':(0.5,0.0),'H':(1.0,1.5),
        'H11L':(0.3,0.2),'H11S':(1.0,1.5),'M':(1.5,1.0)}
# Woman Bottoms Alpha — sostres del màster: creix fins a M i després pla → label 'L'
ALPHA_SOSTRE = {'D22':0.0,'ML':0.0,'D11RH':0.0,'D11RM':0.0,'D11RL':0.0}

canvis, divs = [], []
with schema_context('los'):
    alias = {a.client_code: a.pom_id for a in CustomerPOMAlias.objects.all()}
    try:
        with transaction.atomic():
            print('\n── LOS Woman Knit — Tops (id=53) ' + '─' * 44)
            rs = GradingRuleSet.objects.get(nom='LOS Woman Knit — Tops')
            per_pom = {r.pom_id: r for r in rs.regles.select_related('pom')}
            for codi, (c1, c2) in TOPS.items():
                pid = alias.get(codi)
                r = per_pom.get(pid) if pid else None
                if not r: continue
                real = float(r.increment_base if r.increment_base is not None else r.increment)
                if abs(real - c1) > 0.001:
                    divs.append(('Tops', codi, r.pom.codi_client, c1, real)); continue
                lbl = '3XL' if c2 == 0 else '2XL'
                tipus = 'SOSTRE' if c2 == 0 else 'ritme nou'
                if r.talla_break_label == lbl and r.increment_break is not None and float(r.increment_break) == c2:
                    print(f'    ═ {codi:5} ja fet'); continue
                print(f'    → {codi:5} POM {r.pom.codi_client:10} base={c1} break={c2} label={lbl!r} ({tipus})')
                canvis.append(('Tops', codi, lbl, c2))
                if APPLY:
                    GradingRule.objects.filter(pk=r.pk).update(
                        increment_break=Decimal(str(c2)), talla_break_label=lbl)
            print('\n── LOS Woman Woven — Bottoms (Alpha) ' + '─' * 40)
            rsa = GradingRuleSet.objects.filter(nom='LOS Woman Woven — Bottoms (Alpha)').first()
            if not rsa:
                print('    ✘ no existeix')
            else:
                for r in rsa.regles.select_related('pom'):
                    if r.pom.codi_client not in ALPHA_SOSTRE: continue
                    if r.talla_break_label == 'L' and r.increment_break is not None: 
                        print(f'    ═ {r.pom.codi_client} ja fet'); continue
                    print(f"    → {r.pom.codi_client:8} base={r.increment_base} break=0 label='L' (SOSTRE: creix fins a M)")
                    canvis.append(('Alpha', r.pom.codi_client, 'L', 0.0))
                    if APPLY:
                        GradingRule.objects.filter(pk=r.pk).update(
                            increment_break=Decimal('0'), talla_break_label='L')
            print('\n── AUDITORIA ' + '─' * 64)
            with connection.cursor() as cur:
                cur.execute("""SELECT rs.nom, count(*) FILTER (WHERE r.talla_break_label IS NOT NULL)
                               FROM pom_gradingrule r JOIN pom_gradingruleset rs ON rs.id=r.rule_set_id
                               WHERE rs.nom LIKE 'LOS Woman%%' GROUP BY rs.nom ORDER BY 1""")
                for n, c in cur.fetchall(): print(f'  {n:40} regles amb break: {c}')
                cur.execute("SELECT count(*) FROM pom_gradingrule"); print(f'  TOTAL GradingRule: {cur.fetchone()[0]}')
            if not APPLY: raise Rollback
    except Rollback:
        print('\n' + '='*78 + '\n  DRY-RUN → ROLLBACK.\n' + '='*78)
    else:
        if APPLY: print('\n' + '='*78 + '\n  APPLY → COMMIT.\n' + '='*78)
print(f'\n>>> {len(canvis)} regles amb FORM · {len(divs)} saltades per divergència de col1')
for d in divs: print(f'    DIV {d[0]} {d[1]:5} POM {d[2]:10} màster={d[3]} BD={d[4]}')
