"""P5-FIX — A (rebateig net) + B (fusió amb esborrat acotat) al schema `fhort`.

    DELTA_APPLY=0 ./venv/bin/python manage.py shell < p5fix_fusio.py   # dry-run
    DELTA_APPLY=1 ./venv/bin/python manage.py shell < p5fix_fusio.py   # aplica

Autorització d'Agus (2026-07-24) amb 5 condicions. Compliment:
  1. Només files de P5 → verificat per BLOC DE PK (no hi ha cap camp de data als models).
     Si alguna fila cau fora del bloc → SystemExit dins l'atòmic → rollback.
  2. Bessona exacta (tupla completa) per a CADA fila, comprovada DINS l'atòmic.
  3. Un sol transaction.atomic: esborrat → actiu=False → assert de l'invariant.
  4. Foto prèvia ja escrita a DIAGNOSI_CENS §P5-FIX i commitada abans d'executar.
  5. Dry-run → informe → apply.
"""
import os
from django.db import transaction, connection
from django_tenants.utils import schema_context
from fhort.pom.models import POMMaster, GradingRule, GarmentPOMMap, CustomerPOMAlias

APPLY = os.environ.get('DELTA_APPLY') == '1'
print(f'\n{"="*78}\n  P5-FIX (A+B) a `fhort` — MODE: {"APPLY" if APPLY else "DRY-RUN"}\n{"="*78}')


class Rollback(Exception):
    pass


# (pom_global, pk supervivent, codi nou del supervivent, pk perdedor, àlies a rebatejar)
CAS_A = ('LOSPOM-558', 563, 'GCI', 736, ('GL', 'GCI'))
CAS_B = [('POM-025', 297, 'H11L', 740, None),
         ('LOSPOM-681', 686, 'H11S', 739, None)]

with schema_context('fhort'):
    try:
        with transaction.atomic():
            r0, m0, p0 = (GradingRule.objects.count(), GarmentPOMMap.objects.count(),
                          POMMaster.objects.count())
            print(f'\nFOTO PRÈVIA · GradingRule={r0} GarmentPOMMap={m0} POMMaster={p0}')

            # Bloc de pk creat per P5 (condició 1)
            blk_r = set(sorted(GradingRule.objects.values_list('pk', flat=True))[-78:])
            blk_m = set(sorted(GarmentPOMMap.objects.values_list('pk', flat=True))[-69:])

            # ── A ──
            glob, g_pk, nou, p_pk, al = CAS_A
            G, P = POMMaster.objects.get(pk=g_pk), POMMaster.objects.get(pk=p_pk)
            nr, nm = GradingRule.objects.filter(pom=P).count(), GarmentPOMMap.objects.filter(pom=P).count()
            print(f'\n── A · {glob} (rebateig NET) ' + '─' * 44)
            if nr or nm:
                raise SystemExit(f'⛔ el perdedor pk={p_pk} NO és buit ({nr}r/{nm}m) — no és el cas A')
            print(f'  supervriu pk={G.pk} {G.codi_client!r} → {nou!r} '
                  f'({GradingRule.objects.filter(pom=G).count()}r/{GarmentPOMMap.objects.filter(pom=G).count()}m intactes)')
            print(f'  àlies {al[0]!r} → {al[1]!r}')
            print(f'  perdedor pk={P.pk} {P.codi_client!r} (0r/0m) → actiu=False')
            if APPLY:
                POMMaster.objects.filter(pk=G.pk).update(codi_client=nou)
                CustomerPOMAlias.objects.filter(pom=G, client_code=al[0]).update(client_code=al[1])
                POMMaster.objects.filter(pk=P.pk).update(actiu=False)

            # ── B ──
            esborrades_r = esborrats_m = 0
            for glob, g_pk, nou, p_pk, _ in CAS_B:
                G, P = POMMaster.objects.get(pk=g_pk), POMMaster.objects.get(pk=p_pk)
                print(f'\n── B · {glob} (FUSIÓ) ' + '─' * 50)
                print(f'  supervriu pk={G.pk} {G.codi_client!r} → {nou!r}')
                # bessones del supervivent
                twin_r = {r.rule_set_id: (r.logica, r.increment, r.increment_base, r.increment_break,
                                          r.talla_break_label, r.actiu)
                          for r in GradingRule.objects.filter(pom=G)}
                twin_m = {m.garment_type_item_id: (m.obligatori, m.is_key, m.nivell, m.ordre)
                          for m in GarmentPOMMap.objects.filter(pom=G)}
                for r in GradingRule.objects.filter(pom=P):
                    if r.pk not in blk_r:
                        raise SystemExit(f'⛔ COND.1 regla pk={r.pk} FORA del bloc de P5 — rollback')
                    t = (r.logica, r.increment, r.increment_base, r.increment_break,
                         r.talla_break_label, r.actiu)
                    if twin_r.get(r.rule_set_id) != t:
                        raise SystemExit(f'⛔ COND.2 regla pk={r.pk} SENSE bessona exacta — rollback')
                for m in GarmentPOMMap.objects.filter(pom=P):
                    if m.pk not in blk_m:
                        raise SystemExit(f'⛔ COND.1 map pk={m.pk} FORA del bloc de P5 — rollback')
                    if twin_m.get(m.garment_type_item_id) != (m.obligatori, m.is_key, m.nivell, m.ordre):
                        raise SystemExit(f'⛔ COND.2 map pk={m.pk} SENSE bessona exacta — rollback')
                nr = GradingRule.objects.filter(pom=P).count()
                nm = GarmentPOMMap.objects.filter(pom=P).count()
                print(f'  ✔ cond.1 (bloc de pk) i cond.2 (bessona exacta) verificades per a {nr}r + {nm}m')
                print(f'  perdedor pk={P.pk} {P.codi_client!r}: s\'esborren {nr} regles i {nm} maps → actiu=False')
                esborrades_r += nr; esborrats_m += nm
                if APPLY:
                    GradingRule.objects.filter(pom=P).delete()
                    GarmentPOMMap.objects.filter(pom=P).delete()
                    POMMaster.objects.filter(pk=G.pk).update(codi_client=nou)
                    POMMaster.objects.filter(pk=P.pk).update(actiu=False)

            # ── invariant DINS l'atòmic (condició 3) ──
            inv = GradingRule.objects.filter(pom__actiu=False).count()
            print(f'\n── INVARIANT (dins l\'atòmic) · regles a POM actiu=False: {inv}')
            if APPLY and inv != 0:
                raise SystemExit('⛔ INVARIANT TRENCAT — rollback total')
            r1, m1 = GradingRule.objects.count(), GarmentPOMMap.objects.count()
            print(f'  GradingRule {r0} → {r1} (−{r0-r1}) · GarmentPOMMap {m0} → {m1} (−{m0-m1})')
            if APPLY:
                assert r0 - r1 == esborrades_r and m0 - m1 == esborrats_m, 'recompte no quadra'

            print('\n── AUDITORIA SQL ' + '─' * 60)
            with connection.cursor() as cur:
                cur.execute("""SELECT g.codi, m.id, m.codi_client, m.actiu,
                               (SELECT count(*) FROM pom_gradingrule r WHERE r.pom_id=m.id),
                               (SELECT count(*) FROM pom_garmentpommap p WHERE p.pom_id=m.id)
                               FROM pom_pommaster m JOIN pom_pomglobal g ON g.id=m.pom_global_id
                               WHERE g.codi IN ('POM-025','LOSPOM-681','LOSPOM-558')
                               ORDER BY g.codi, m.id""")
                for row in cur.fetchall():
                    print(f'  {row[0]:12} pk={row[1]:<5} codi={row[2]!r:8} actiu={row[3]!s:5} regles={row[4]:<3} maps={row[5]}')
                cur.execute("""SELECT count(*) FROM pom_gradingrule r JOIN pom_pommaster m
                               ON m.id=r.pom_id WHERE m.actiu=false""")
                print(f'  regles a POM inactiu: {cur.fetchone()[0]}')
            if not APPLY:
                raise Rollback
    except Rollback:
        print('\n' + '=' * 78 + '\n  DRY-RUN → ROLLBACK. Cap canvi persistit.\n' + '=' * 78)
    else:
        if APPLY:
            print('\n' + '=' * 78 + '\n  APPLY → COMMIT.\n' + '=' * 78)
