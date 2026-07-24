"""DELTA IDEMPOTENT — diccionari v3 de LOSAN (schemas `los` i `fhort`).

Ús:
    DELTA_APPLY=0 ./venv/bin/python manage.py shell < delta_diccionari_v3.py   # dry-run (defecte)
    DELTA_APPLY=1 ./venv/bin/python manage.py shell < delta_diccionari_v3.py   # aplica

Disseny:
  · Idempotent: cada pas comprova l'estat objectiu abans d'escriure; re-executar-lo no fa res.
  · Atòmic per schema: tot dins `transaction.atomic()`. En dry-run s'executa el MATEIX camí de
    codi i es fa ROLLBACK al final (no és una simulació: és l'operació real, desfeta).
  · Mai esborrar-i-recarregar: només UPDATE conservant pk i FK (llei del fil).
  · Comporta de noms: el pas 4 NOMÉS escriu quan el nom del POM coincideix als dos schemas.
    Els que no coincideixen queden a REVISIÓ (veure DIAGNOSI_CENS §P0).
"""
import os, re
from django.db import transaction, connection
from django_tenants.utils import schema_context
from fhort.pom.models import POMMaster, POMGlobal, CustomerPOMAlias
from fhort.tasks.models import Customer

APPLY = os.environ.get('DELTA_APPLY') == '1'
MODE = 'APPLY' if APPLY else 'DRY-RUN'
print(f'\n{"="*78}\n  DELTA DICCIONARI v3 — MODE: {MODE}\n{"="*78}')


class Rollback(Exception):
    """Senyal de fi de dry-run: força el rollback de l'atòmic."""


def norm(s):
    s = (s or '').upper().replace('&', ' AND ')
    return ' '.join(re.sub(r'[^A-Z0-9]+', ' ', s).split())


# ── PAS 1 · REBATEJOS (només schema `los`) ───────────────────────────────────────────────
# Clau d'ancoratge: pom_global.codi (estable), NO el pk ni el codi_client actual.
# ORDRE CRÍTIC: GL→GCI ha d'anar ABANS de SL→GL (allibera el codi `GL`).
# (pom_global, codi_client nou, àlies antic, àlies nou, etiqueta)
REBATEJOS = [
    ('LOSPOM-558', 'GCI',  'GL',   'GCI',  'Cuff Inner'),
    ('LOSPOM-559', 'GCH',  'GN',   'GCH',  'Cuff Height'),
    ('LOSPOM-560', 'GCD',  'GM',   'GCD',  'Cuff Difference'),
    ('LOSPOM-680', 'GS',   'G.3',  'GS',   'Sleeve length SHORT (era G.3)'),
    ('LOSPOM-681', 'H11S', 'H.12', 'H11S', 'Sleeve opening SHORT (era H.12) — `H12` es manté com a sinònim'),
    ('POM-020',    'GL',   'G',    'GL',   'Sleeve length LONG (era SL/G) — requereix GL alliberat'),
    ('POM-025',    'H11L', 'H11',  'H11L', 'Sleeve opening LONG (era SL OP/H11)'),
]


def pas1_rebatejos():
    print('\n── PAS 1 · REBATEJOS DE CLIENT_CODE (schema los) ' + '─' * 30)
    fets = saltats = 0
    for glob, nou, al_antic, al_nou, etiq in REBATEJOS:
        p = POMMaster.objects.filter(pom_global__codi=glob).first()
        if not p:
            print(f'  ✘ {glob}: POMMaster inexistent — SALTAT')
            continue
        a = CustomerPOMAlias.objects.filter(pom=p, client_code=al_antic).first()
        ja = (p.codi_client == nou and a is None
              and CustomerPOMAlias.objects.filter(pom=p, client_code=al_nou).exists())
        if ja:
            print(f'  ═ {glob}: ja és {nou!r} — idempotent, res a fer')
            saltats += 1
            continue
        altres = list(CustomerPOMAlias.objects.filter(pom=p)
                      .exclude(client_code=al_antic).values_list('client_code', flat=True))
        print(f'  → {glob} ({etiq})')
        print(f'      POMMaster pk={p.pk} {p.codi_client!r} → {nou!r}  '
              f'(maps={p.garment_maps.count()}, regles={p.regles_grading.count()} — cap FK es mou)')
        print(f'      àlies {al_antic!r} → {al_nou!r}' + (f'  · es mantenen intactes: {altres}' if altres else ''))
        if APPLY:
            POMMaster.objects.filter(pk=p.pk).update(codi_client=nou)
            if a:
                CustomerPOMAlias.objects.filter(pk=a.pk).update(client_code=al_nou)
        fets += 1
    print(f'  RESUM pas 1: {fets} rebatejos, {saltats} ja fets')
    return fets


# ── PAS 2 · ALTES v3 — NOMÉS el grup net D11R* (la resta descartada per decisió d'Agus) ──
ALTES = [
    ('LOSPOM-685', 'D11RH', 'HIGH RISE'),
    ('LOSPOM-686', 'D11RM', 'MID RISE'),
    ('LOSPOM-687', 'D11RL', 'LOW RISE'),
]
DESCARTATS = ['GAL/GAS (naixement mandrós)', 'FL/FS (sense diferenciació real)',
              'MT/MD/ML/MS/MB/MO (l\'abast del contenidor ho resol)',
              'GL/GS/H11L/H11S (resolts com a REBATEIG al pas 1)',
              'D11H/D11W (diferit a P2: condició d\'entrada)']


def pas2_altes():
    print('\n── PAS 2 · ALTES NOVES v3 ' + '─' * 52)
    for d in DESCARTATS:
        print(f'  ⊘ descartat: {d}')
    self_c = Customer.objects.get(is_self=True)
    fets = saltats = 0
    for glob, codi, nom in ALTES:
        if POMMaster.objects.filter(codi_client=codi).exists():
            print(f'  ═ {codi}: ja existeix — idempotent, res a fer')
            saltats += 1
            continue
        print(f'  + {codi} ({nom}) → POMGlobal {glob} + POMMaster + àlies del self LOS (pk={self_c.pk})')
        if APPLY:
            g, _ = POMGlobal.objects.get_or_create(
                codi=glob, defaults=dict(nom_en=nom, nom_ca='', nom_es='', categoria='LOSAN',
                                         unitat='cm', actiu=True))
            m = POMMaster.objects.create(
                pom_global=g, codi_client=codi, nom_client=nom, actiu=True,
                pendent_revisio=False, origen_import='diccionari v3 P0 2026-07-24')
            CustomerPOMAlias.objects.create(
                customer=self_c, pom=m, client_code=codi, description_en=nom,
                origen='DICCIONARI', pendent_revisio=False)
        fets += 1
    print(f'  RESUM pas 2: {fets} altes, {saltats} ja existents')
    return fets


# ── PASSOS 3+4 · pom_global a `fhort` ────────────────────────────────────────────────────
# Mateixa operació física (omplir pom_global on és NULL); es reporten separats.
PARELLS_NOTACIO = {'C13': 'C.13', 'E9': 'E.9', 'SR6': 'S.R6', 'SR7': 'S.R7'}  # fhort → los
# Rebatejos històrics del pas 1: `fhort` conserva els codis vells. Sense aquest mapa, una
# re-execució no aparellaria aquests codis i els comptaria com a «sense contrapart» (només
# afecta el REPORT — l'escriptura ja és idempotent —, però amaga files a l'informe).
REBATEJATS_HIST = {'GL': 'GCI', 'GN': 'GCH', 'GM': 'GCD', 'G.3': 'GS', 'H.12': 'H11S',
                   'H12': 'H11S', 'G': 'GL', 'H11': 'H11L'}


def foto_los():
    """Foto del diccionari de `los` PRE-rebateig: client_code → (pom_global.codi, nom).

    S'ha de capturar ABANS del pas 1, perquè els rebatejos canvien les claus (`H11`→`H11L`,
    `G`→`GL`…) mentre que `fhort` conserva els codis vells. El `pom_global` no es mou, així que
    la foto segueix sent vàlida per a l'aparellament."""
    with schema_context('los'):
        c = Customer.objects.get(is_self=True)
        return {a.client_code: (a.pom.pom_global.codi if a.pom.pom_global_id else None, a.pom.nom_client)
                for a in CustomerPOMAlias.objects.filter(customer=c).select_related('pom', 'pom__pom_global')}


def pas34_pom_global(L):
    print('\n── PASSOS 3+4 · REPARAR pom_global=NULL a `fhort` ' + '─' * 29)
    print('  (aparellament fet sobre la foto de `los` PRE-rebateig — els codis vells de fhort hi consten)')

    fets = revisio = ja_ok = conflicte = 0
    rev_detall, conf_detall = [], []
    with schema_context('fhort'):
        cf = Customer.objects.get(codi='LOS')
        for a in (CustomerPOMAlias.objects.filter(customer=cf)
                  .select_related('pom', 'pom__pom_global').order_by('client_code')):
            # ORDRE: el mapa històric MANA. `fhort` conserva el codi vell amb el significat vell;
            # si el mateix codi existeix ara a `los` amb un altre significat (cas `GL`, que ha
            # passat de CUFF OPENING INNER a Sleeve length), comparar-los seria un fals conflicte.
            cc = a.client_code
            code_los = REBATEJATS_HIST.get(cc) or (cc if cc in L else PARELLS_NOTACIO.get(cc))
            if not code_los or code_los not in L:
                continue
            glob_los, nom_los = L[code_los]
            p = a.pom
            if p.pom_global_id is not None:
                if p.pom_global.codi == glob_los:
                    ja_ok += 1
                else:
                    conflicte += 1
                    conf_detall.append((a.client_code, p.codi_client, p.pom_global.codi, glob_los,
                                        p.nom_client, nom_los))
                continue
            if glob_los is None:
                continue
            # COMPORTA DE NOMS: només escrivim si els dos schemas anomenen igual la mesura.
            if norm(p.nom_client) != norm(nom_los):
                revisio += 1
                rev_detall.append((a.client_code, p.codi_client, p.nom_client, nom_los, glob_los))
                continue
            g = POMGlobal.objects.filter(codi=glob_los).first()
            if not g:
                revisio += 1
                rev_detall.append((a.client_code, p.codi_client, p.nom_client,
                                   f'(POMGlobal {glob_los} inexistent a fhort)', glob_los))
                continue
            if APPLY:
                POMMaster.objects.filter(pk=p.pk).update(pom_global=g)
            fets += 1

    print(f'  ✔ REPARATS (nom idèntic als dos schemas): {fets}')
    print(f'  ═ ja coincidien: {ja_ok}')
    print(f'  ⚠ A REVISIÓ (nom diferent → NO tocats): {revisio}')
    for r in rev_detall:
        print(f'      {r[0]:8} fhort={r[1]:12} {r[2][:34]!r:36} ≠ los {r[3][:34]!r} ({r[4]})')
    print(f'  ⛔ CONFLICTES (fhort ja té un global DIFERENT → NO tocats): {conflicte}')
    for c_ in conf_detall:
        print(f'      {c_[0]:8} fhort={c_[1]:10} {c_[2]:12} {c_[4][:30]!r}')
        print(f'      {"":8} los  ={"":10} {c_[3]:12} {c_[5][:30]!r}')
    return fets


# ── PAS 5 · accessoris — deute anotat, no s'executa ──────────────────────────────────────
def pas5():
    print('\n── PAS 5 · VOCABULARI D\'ACCESSORIS ' + '─' * 43)
    print('  ⏸ NO se sembra a `los` (cap item d\'ACCESSORIES té maps ni models). Deute anotat.')


# ── AUDITORIA per SQL directe (no confiar en el missatge de l'ORM) ───────────────────────
def auditoria():
    print('\n── AUDITORIA (SELECT directe, post-operació) ' + '─' * 34)
    with schema_context('los'):
        with connection.cursor() as cur:
            cur.execute("""
                SELECT g.codi, m.codi_client, m.id
                FROM pom_pommaster m JOIN pom_pomglobal g ON g.id = m.pom_global_id
                WHERE g.codi IN ('LOSPOM-558','LOSPOM-559','LOSPOM-560') ORDER BY g.codi""")
            print('  los · POMMaster dels 3 rebatejos:', cur.fetchall())
            cur.execute("""
                SELECT a.client_code, m.codi_client FROM pom_customerpomalias a
                JOIN pom_pommaster m ON m.id = a.pom_id
                JOIN pom_pomglobal g ON g.id = m.pom_global_id
                WHERE g.codi IN ('LOSPOM-558','LOSPOM-559','LOSPOM-560') ORDER BY a.client_code""")
            print('  los · àlies dels 3 rebatejos:  ', cur.fetchall())
    with schema_context('fhort'):
        with connection.cursor() as cur:
            cur.execute("""
                SELECT count(*) FILTER (WHERE m.pom_global_id IS NULL),
                       count(*) FILTER (WHERE m.pom_global_id IS NOT NULL), count(*)
                FROM pom_customerpomalias a
                JOIN pom_pommaster m ON m.id = a.pom_id
                JOIN tasks_customer c ON c.id = a.customer_id
                WHERE c.codi = 'LOS'""")
            n_null, n_ok, n_tot = cur.fetchone()
            print(f'  fhort · àlies LOS: POMMaster amb global={n_ok} · SENSE global={n_null} · total={n_tot}')
            cur.execute("SELECT count(*) FROM pom_pommaster WHERE pom_global_id IS NULL")
            print(f'  fhort · POMMaster sense global a TOT el schema: {cur.fetchone()[0]}')


# ── EXECUCIÓ ─────────────────────────────────────────────────────────────────────────────
L_PRE = foto_los()          # ← abans de qualsevol escriptura
print(f'  [foto] diccionari de `los` pre-rebateig: {len(L_PRE)} client_code')

try:
    with transaction.atomic():
        with schema_context('los'):
            pas1_rebatejos()
            pas2_altes()
        pas34_pom_global(L_PRE)
        pas5()
        auditoria()
        if not APPLY:
            raise Rollback
except Rollback:
    print('\n' + '=' * 78)
    print('  DRY-RUN acabat → ROLLBACK executat. Cap canvi persistit a la BD.')
    print('=' * 78)
else:
    if APPLY:
        print('\n' + '=' * 78)
        print('  APPLY acabat → COMMIT. Torna a executar en dry-run per verificar idempotència.')
        print('=' * 78)
