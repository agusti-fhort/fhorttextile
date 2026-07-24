"""P2 — NEWBORN fill-holes (part ADDITIVA, sense crear cap POM nou).

    DELTA_APPLY=0 ./venv/bin/python manage.py shell < p2_newborn_fillholes.py   # dry-run
    DELTA_APPLY=1 ./venv/bin/python manage.py shell < p2_newborn_fillholes.py   # aplica

Font: docs/diagnosis/GRADING_SOURCES_LOSAN.md §TANDA 11 (màster NEWBORN).
Llei: **el màster OMPLE FORATS, MAI sobreescriu.**
  · POM del màster que ja és regla i COINCIDEIX  → NO-OP
  · POM del màster que ja és regla i DIVERGEIX   → NO s'escriu, va a l'informe
  · POM del màster que NO és regla               → s'afegeix, LINEAR pur (cap break)
  · Codi del màster sense POM al diccionari      → NO es crea res: va a l'informe amb el
    veredicte de la condició d'entrada (conflicte real dins d'un sol contenidor o no).
"""
import os
from decimal import Decimal
from django.db import transaction, connection
from django_tenants.utils import schema_context
from fhort.pom.models import GradingRuleSet, GradingRule, CustomerPOMAlias, SizeDefinition

APPLY = os.environ.get('DELTA_APPLY') == '1'
print(f'\n{"="*78}\n  P2 · NEWBORN FILL-HOLES — MODE: {"APPLY" if APPLY else "DRY-RUN"}\n{"="*78}')


class Rollback(Exception):
    pass


TOP = {'B': 1.0, 'C': 1.0, 'C3': 0.0, 'D': 1.0, 'E': 1.0, 'K2': 1.0, 'K': 0.3, 'K1': 0.2,
       'L3': 0.3, 'L4': 0.3, 'L5': 0.0, 'BJ': 0.2, 'A1': 0.5, 'A2': 0.5, 'H6': 0.5,
       'GL': 1.5, 'GS': 0.3, 'H': 0.5, 'G5': 0.0, 'H4': 0.0, 'H11L': 0.3}
BOT = {'C': 1.0, 'C4': 1.0, 'C1': 1.0, 'D': 1.0, 'D1': 1.0, 'D22': 1.7, 'D2': 0.5, 'D20': 0.5}
#: RETINGUT: `S44` resol a POMMaster `S` (*Front armhole along seam*), que el cens va marcar com a
#: MAL CABLEJAT (hi pengen alhora `S22`=BELT HEIGHT i `S44`=FRONT MOTIVE LOCATION). Sembrar-hi
#: 0.3 donaria a l'armhole la graduació d'una localització de motiu. Va a l'informe, no a la BD.
RETINGUTS_MISWIRE = {'S44': 0.3}
#: Codis del màster SENSE POM al diccionari → no es toquen aquí (informe + decisió).
PENDENTS = {
    'TOP-DRESS': {'D11H': 0.0, 'D11W': 0.5, 'GAL': 0.0, 'GAS': 0.1, 'MT': 1.5, 'MD': 3.0},
    'BOTTOM': {'D11W': 0.5, 'FL': 0.5, 'FS': 0.5, 'T1W': 0.7, 'T2W': 0.7, 'T1H': 1.5,
               'T2H': 1.9, 'ML': 3.7, 'MS': 1.5, 'MB': 2.5, 'MO': 3.5},
}
CONTENIDORS = [('LOS New Born Knit — Tops', TOP), ('LOS New Born Knit — Bottoms', BOT),
               ('LOS New Born Knit — Onepieces', TOP)]

divergencies = []
afegides = []

with schema_context('los'):
    alias = {a.client_code: a.pom for a in CustomerPOMAlias.objects.select_related('pom').all()}
    try:
        with transaction.atomic():
            for nom, taula in CONTENIDORS:
                rs = GradingRuleSet.objects.get(nom=nom)
                base = SizeDefinition.objects.filter(size_system=rs.size_system, etiqueta='00/01').first()
                exist = {r.pom_id: r for r in rs.regles.select_related('pom')}
                abans = rs.regles.count()
                print(f'\n── {nom} ── (base={base.etiqueta if base else "?"}, {abans} regles abans)')
                n_new = n_ok = n_div = 0
                for codi, val in taula.items():
                    p = alias.get(codi)
                    if not p:
                        continue
                    r = exist.get(p.pk)
                    if r:
                        real = float(r.increment_base if r.increment_base is not None else r.increment)
                        if abs(real - val) < 0.001:
                            n_ok += 1
                        else:
                            n_div += 1
                            divergencies.append((nom, codi, p.codi_client, val, real))
                        continue
                    n_new += 1
                    afegides.append((nom, codi, p.codi_client, val))
                    print(f'    + {codi:6} → POM {p.codi_client:12} LINEAR pur {val}')
                    if APPLY:
                        GradingRule.objects.create(
                            rule_set=rs, pom=p, talla_base=base, logica='LINEAR',
                            increment=Decimal(str(val)), increment_base=Decimal(str(val)),
                            increment_break=None, talla_break_label=None, actiu=True)
                despres = GradingRule.objects.filter(rule_set=rs).count()
                print(f'    coincideixen={n_ok} · divergeixen={n_div} (NO tocades) · noves={n_new}')
                print(f'    regles: {abans} → {despres}  {"✔ creixement net" if despres >= abans else "✘ SUBSTITUCIÓ"}')
                assert despres >= abans, 'INVARIANT TRENCAT: substitució en comptes de creixement'

            print('\n── AUDITORIA SQL ' + '─' * 60)
            with connection.cursor() as cur:
                cur.execute("""SELECT rs.nom, count(*) FROM pom_gradingrule r
                               JOIN pom_gradingruleset rs ON rs.id = r.rule_set_id
                               WHERE rs.nom LIKE 'LOS New Born%%' GROUP BY rs.nom ORDER BY 1""")
                for n, c in cur.fetchall():
                    print(f'  {n:34} {c} regles')
                cur.execute("SELECT count(*) FROM pom_gradingrule")
                print(f'  TOTAL GradingRule al tenant: {cur.fetchone()[0]}')
            if not APPLY:
                raise Rollback
    except Rollback:
        print('\n' + '=' * 78 + '\n  DRY-RUN → ROLLBACK. Cap canvi persistit.\n' + '=' * 78)
    else:
        if APPLY:
            print('\n' + '=' * 78 + '\n  APPLY → COMMIT.\n' + '=' * 78)

print(f'\n>>> RESUM: {len(afegides)} regles noves · {len(divergencies)} divergències a informe')
for d in divergencies:
    print(f'    DIV {d[0][:28]:28} {d[1]:6} POM {d[2]:10} màster={d[3]} BD={d[4]}')
