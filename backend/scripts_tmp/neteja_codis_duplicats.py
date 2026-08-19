"""Pla de neteja dels POMs ORFES del catàleg — EN SEC per defecte.

    backend/venv/bin/python manage.py tenant_command shell --schema=fhort \
        < scripts_tmp/neteja_codis_duplicats.py          # dry-run: NO escriu res
    APLICA=1 ... (mateixa comanda)                        # escriu (NOMÉS amb l'Agus davant)

────────────────────────────────────────────────────────────────────────────────────────────
QUÈ HA PASSAT, I QUÈ NO

El cens de `POMMaster.codi_client` dona 12 codis repetits, i la primera lectura («12 duplicats
a netejar») és FALSA. La majoria són el mateix codi de la CASA fet servir per un POM de Brownie
i un de Losan —`C1`, `E4`, `E7`, `J1`, `S`, `S2`, `U`, `U1`— i això NO és cap error: la
nomenclatura de cada client viu a `CustomerPOMAlias` i la unicitat del domini és
`(customer, client_code)`. Dos clients poden dir `U1` a coses diferents; és el cas normal.

EL DANY REAL SÓN ELS ORFES: POMs sense CAP àlies. No pertanyen al catàleg de ningú, i per tant:
  · el cercador nou (que resol contra els àlies del client) NO els troba;
  · la validació de col·lisió NO els veu;
  · les mesures que ja hi apunten segueixen funcionant, perquè apunten per `pom_id`.

Els va crear el camí d'import (`extraction_views.py:1901`), que agafava el codi del document
tal qual sense mirar el catàleg del client. És exactament el forat que el tram del 06/08 tanca
per als camins nous; això d'aquí és el rastre que va deixar abans.

LA REPARACIÓ, doncs, NO és esborrar res: és DONAR-LOS EL SEU ÀLIES al catàleg del client que
els fa servir, amb un codi que no xoqui. Cap `BaseMeasurement` es toca, cap POM es fusiona, cap
`pom_id` es reapunta. Si algun dia dos POMs resulten ser la mateixa mesura, fusionar-los és una
altra decisió i un altre tram (v. `consolidate_pom_los.py`, que ja sap fer-ho).
────────────────────────────────────────────────────────────────────────────────────────────
"""
import os

from django.db import transaction
from django.db.models import Count

from fhort.models_app.models import BaseMeasurement
from fhort.pom.models import CustomerPOMAlias, POMMaster
from fhort.pom.nomenclatura import colisio_de_codi

APLICA = os.environ.get('APLICA') == '1'


def codi_lliure(customer_id, base):
    """Un codi que no xoqui amb res del catàleg d'aquest client.

    Es prova el codi tal qual i, si ja significa una altra cosa, se li afegeix un sufix. NO es
    tria mai en silenci un codi ocupat: aquest script existeix precisament per no repetir
    l'error que el va crear.
    """
    xoc, _ = colisio_de_codi(customer_id, base)
    if xoc is None:
        return base, None
    for i in range(2, 30):
        cand = f'{base}-{i}'
        if colisio_de_codi(customer_id, cand)[0] is None:
            return cand, xoc
    return None, xoc


print('═' * 92)
print('PLA DE NETEJA · POMs ORFES DEL CATÀLEG' + ('   ⚠️  APLICANT' if APLICA else '   · EN SEC (no escriu res)'))
print('═' * 92)

# ── 1 · el cens honest: quants dels 12 «duplicats» ho són de debò ────────────────────────────
dups = (POMMaster.objects.values('codi_client')
        .annotate(n=Count('id')).filter(n__gt=1).order_by('codi_client'))
convivencia, sospitosos = [], []
for d in dups:
    poms = list(POMMaster.objects.filter(codi_client=d['codi_client']).order_by('id'))
    clients = [set(CustomerPOMAlias.objects.filter(pom=p).values_list('customer_id', flat=True))
               for p in poms]
    if all(c for c in clients) and not set.intersection(*clients):
        convivencia.append(d['codi_client'])
    else:
        sospitosos.append(d['codi_client'])

print(f"\n1 · {dups.count()} codis de casa repetits")
print(f"    · {len(convivencia)} són CONVIVÈNCIA legítima (clients diferents, cap àlies compartit):")
print(f"      {', '.join(convivencia) or '—'}")
print(f"    · {len(sospitosos)} tenen algun POM sense àlies o amb àlies del mateix client:")
print(f"      {', '.join(sospitosos) or '—'}")

# ── 2 · els orfes, que és el que de debò s'ha de reparar ─────────────────────────────────────
orfes = [p for p in POMMaster.objects.filter(actiu=True).order_by('id')
         if not CustomerPOMAlias.objects.filter(pom=p).exists()]
print(f"\n2 · POMs ACTIUS SENSE CAP ÀLIES (orfes del catàleg): {len(orfes)}")

# Només es pot reparar el que té mesures vives: elles diuen de quin client és el POM. Un orfe
# sense cap mesura no té ningú que el reclami i no s'inventa: es llista i s'espera decisió.
plan, sense_amo = [], []
for p in orfes:
    bms = (BaseMeasurement.objects.filter(pom=p, is_active=True)
           .select_related('model').order_by('model_id'))
    customers = {b.model.customer_id for b in bms if b.model.customer_id}
    if len(customers) == 1:
        cid = customers.pop()
        nou, xoc = codi_lliure(cid, p.codi_client)
        plan.append((p, cid, nou, xoc, list(bms)))
    else:
        sense_amo.append((p, bms.count(), customers))

print(f"    · {len(plan)} tenen mesures vives d'UN SOL client → es poden reparar")
print(f"    · {len(sense_amo)} no (cap mesura, o mesures de més d'un client) → decisió humana")

print('\n' + '─' * 92)
print('3 · EL QUE ES FARIA (una fila = un àlies nou; cap mesura es toca)')
print('─' * 92)
for p, cid, nou, xoc, bms in plan:
    from fhort.tasks.models import Customer
    cust = Customer.objects.filter(pk=cid).values_list('codi', flat=True).first() or f'#{cid}'
    motiu = f'  ⚠️ «{p.codi_client}» ja és «{xoc.nom_client}» → s\'usa «{nou}»' if xoc else ''
    print(f"  pom={p.id:4} «{p.nom_client[:40]}»")
    print(f"        → CustomerPOMAlias({cust}, client_code='{nou}', origen='MODEL', pendent_revisio=True){motiu}")
    print(f"        mesures que el fan servir (NO es toquen): "
          f"{', '.join(f'{b.model.codi_intern}#{b.id}' for b in bms[:4])}")

if sense_amo:
    print('\n' + '─' * 92)
    print('4 · SENSE AMO CLAR — no es toquen, es llisten per decidir')
    print('─' * 92)
    for p, n, cs in sense_amo:
        print(f"  pom={p.id:4} «{p.nom_client[:44]}» · mesures_vives={n} · customers={cs or 'cap'}")

# ── l'escriptura, si i només si algú l'ha demanat explícitament ──────────────────────────────
print('\n' + '═' * 92)
if not APLICA:
    print(f"EN SEC. {len(plan)} àlies es crearien. Cap escriptura feta.")
    print("Per aplicar-ho, amb l'Agus davant:  APLICA=1 <mateixa comanda>")
else:
    with transaction.atomic():
        fets = 0
        for p, cid, nou, _x, _b in plan:
            if nou is None:
                continue
            CustomerPOMAlias.objects.create(
                customer_id=cid, pom=p, client_code=nou,
                description_en=p.nom_client, origen='MODEL', pendent_revisio=True)
            fets += 1
    print(f"APLICAT: {fets} àlies creats. Cap BaseMeasurement ni cap POM tocat.")
print('═' * 92)
