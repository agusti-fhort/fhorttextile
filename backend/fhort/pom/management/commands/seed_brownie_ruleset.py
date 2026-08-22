"""F4 · El ruleset ÚNIC de Brownie: BRW-CATALEG-v3 (deltes del full CATALEG).

**UN RULESET PER CLIENT MENTRE EL CLIENT NO DIFERENCIÏ** (llei Agus 05/08, full MATCHER).
Brownie comparteix grading entre woven i knit; se'n declararà un de nou el dia que diferenciï
per CONSTRUCCIÓ o FIT, mai per peça ni perquè hagin entrat POMs nous.

Els rulesets vells (RS146-149 al brief; a staging, els 115 i 124 de Brownie) es queden com a
LLEGAT i **no s'esborren**: un model que encara els fa servir ha de poder seguir graduant.

🔑 **LA FORMA DE LA REGLA ES DERIVA DELS VALORS, MAI DE LA CAPÇALERA** (full MATCHER, i el
cas real que ho justifica: FS/FS2/FS3/FS4/FT deien break a XS i era a S). La columna LÒGICA
del full diu «LINEAR+BREAK» tant per a 2·3·3·3 com per a 1·1·1,5·1,5, i el relleu no cau al
mateix lloc. Aquí es llegeixen els quatre Δ i es dedueix.

⚠️ **`talla_break_label` NO ÉS LA TALLA ON EL FULL DIU QUE HI HA EL BREAK.** El full anomena
l'ÚLTIMA talla del delta petit («break a S» per a 0,5·0,5·1·1); el motor ancora a la PRIMERA
talla del delta gran (`increment_de_l_aresta`: l'aresta pren `increment_break` quan el seu
extrem exterior ja ha arribat al llindar). Per a 0,5·0,5·1·1 això és **M**, no S. Traduir-ho
malament desplaça tota la graduació una talla, i és exactament l'error que el full
denunciava. Es dedueix, no es transcriu.

Idempotent (`update_or_create` per rule_set+pom). --dry-run per defecte.

🔒 PANY P3 (22/08): el JOC es resol per la llista `NOMS_DEL_JOC` (+ `codi_sistema`), mai per un
literal. El rebateig a «GRADING BROWNIE 2026» feia que el lookup per `nom='BRW-CATALEG-v3'` no
el trobés i en fabriqués un SEGON amb 142 regles. Sense cap coincidència s'ABORTA; crear-lo
exigeix `--create-ruleset`.

    python manage.py seed_brownie_ruleset                # DRY-RUN
    python manage.py seed_brownie_ruleset --no-dry-run   # escriu
"""
from decimal import Decimal
from pathlib import Path

import openpyxl
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django_tenants.utils import schema_context

from fhort.pom.models import (CustomerPOMAlias, GradingRule, GradingRuleSet, SizeSystem)
from fhort.tasks.models import Customer

XLSX = Path('/var/www/ftt-staging/docs/BROWNIE_CATALEG_POM_v3.xlsx')
CUSTOMER_CODI = 'BRW'
TENANT = 'fhort'
SIZE_SYSTEM = 'ALPHA_EU_W'
NOM = 'BRW-CATALEG-v3'

#: 🔒 PANY P3 (TREN DE PANYS, 22/08) — ELS NOMS CONEGUTS DEL MATEIX JOC, en ordre.
#:
#: 🚨 EL CAS. A PROD el joc es va REBATEJAR a «GRADING BROWNIE 2026» i el nom antic va quedar
#: al `codi_sistema`. Amb el lookup per `nom='BRW-CATALEG-v3'`, un `update_or_create` no el
#: trobava i en fabricava un SEGON, buit, al costat del viu — i tot seguit hi sembrava les 142
#: regles. Dos jocs amb el mateix contingut i cap manera de saber quin mana.
#:
#: Llei S44 (`DECISIONS_snapshot_2026-08-22.md`): **la clau d'idempotència d'una sembra no pot
#: ser un camp que la migració mateixa rebateja.** Mentre el `nom` sigui la clau, la llista de
#: noms coneguts (+ el `codi_sistema` de reserva) és el fallback, i no trobar-ne cap és una
#: RESPOSTA: s'ABORTA. Crear-lo, només amb `--create-ruleset` explícit.
NOMS_DEL_JOC = ('GRADING BROWNIE 2026', 'BRW-CATALEG-v3')


def resol_el_joc(customer, noms=NOMS_DEL_JOC):
    """El `GradingRuleSet` d'aquest client que respon a QUALSEVOL dels noms coneguts, o `None`.

    Primer pels `nom`, en ordre de preferència; després pel `codi_sistema`, que és on el
    rebateig va deixar el nom antic. `None` vol dir ABORTAR, mai crear-ne un en silenci.
    """
    for nom in noms:
        rs = GradingRuleSet.objects.filter(nom=nom, customer=customer).first()
        if rs is not None:
            return rs
    return GradingRuleSet.objects.filter(codi_sistema__in=noms, customer=customer).first()


def forma_de_la_regla(deltas: list, run: list[str]) -> dict | None:
    """Els quatre Δ del full → la forma canònica de la regla. `None` si no és graduable.

    `deltas` són els increments de les ARESTES XXS→XS, XS→S, S→M, M→L; `run`, les etiquetes
    del sistema ordenades, amb la talla base a la posició 0.

    Tres formes possibles i cap més:
      · tot zero            → FIXED (la mesura no gradua).
      · tot igual i no zero → LINEAR uniforme, sense break.
      · un sol esglaó       → LINEAR amb break. `increment_base` és el tram petit,
                              `increment_break` el gran, i l'ancoratge és la talla on el
                              tram gran COMENÇA (v. l'avís de la capçalera).

    Un patró amb més d'un esglaó (0,5 · 1 · 1,5 · 2) no té forma canònica i torna `None`:
    seria STEP, i el full no en declara cap. Val més no sembrar-la que aplanar-la.
    """
    if any(d is None for d in deltas):
        return None
    ds = [float(d) for d in deltas]

    if len(set(ds)) == 1:
        if ds[0] == 0:
            # FIXED amb `increment_base` a None A POSTA: el motor entra a la branca canònica
            # quan `increment_base` no és None, i per a una mesura que no gradua volem la
            # branca FIXED, que torna el valor base i prou.
            return {'logica': GradingRule.LOGICA_FIXED, 'increment': Decimal('0'),
                    'increment_base': None, 'increment_break': None,
                    'talla_break_label': None}
        return {'logica': GradingRule.LOGICA_LINEAR, 'increment': Decimal(str(ds[0])),
                'increment_base': Decimal(str(ds[0])), 'increment_break': None,
                'talla_break_label': None}

    k = next(i for i in range(1, len(ds)) if ds[i] != ds[0])
    if not (all(x == ds[0] for x in ds[:k]) and all(x == ds[k] for x in ds[k:])):
        return None                                   # més d'un esglaó → no és canònica

    # L'aresta `k` va de run[k] a run[k+1]; amb la base a 0, el seu extrem exterior és k+1.
    # El motor hi aplica `increment_break` quan k+1 >= break_idx → break_idx = k+1.
    if k + 1 >= len(run):
        return None
    return {'logica': GradingRule.LOGICA_LINEAR,
            'increment': Decimal(str(ds[0])),
            'increment_base': Decimal(str(ds[0])),
            'increment_break': Decimal(str(ds[k])),
            'talla_break_label': run[k + 1]}


class Command(BaseCommand):
    help = f'F4 · Sembra el ruleset únic {NOM} amb els deltes del full CATALEG.'

    def add_arguments(self, parser):
        parser.add_argument('--no-dry-run', action='store_true')
        parser.add_argument('--schema', default=TENANT)
        parser.add_argument('--xlsx', default=str(XLSX))
        parser.add_argument('--create-ruleset', action='store_true',
                            help='Crea el joc si cap dels noms coneguts (NOMS_DEL_JOC) el troba. '
                                 'Sense el flag, no trobar-lo ATURA la sembra: crear-lo a cegues '
                                 'en fabricaria un SEGON al costat del viu si s\'ha rebatejat.')

    def handle(self, *args, **opts):
        dry = not opts['no_dry_run']
        head = 'DRY-RUN (cap escriptura)' if dry else 'ESCRIVINT'
        self.stdout.write(self.style.WARNING(
            f'=== seed_brownie_ruleset · {NOM} · {head} ==='))

        ws = openpyxl.load_workbook(Path(opts['xlsx']), data_only=True)['CATALEG']
        files = []
        for r in ws.iter_rows(min_row=2, values_only=True):
            codi, nom, logica = r[0], r[1], r[3]
            if codi is None or (nom is None and logica is None):
                continue
            if str(codi).startswith(('Groc', 'Verd', 'Rosa')):
                continue
            files.append((str(codi).strip(), str(logica).strip(), [r[4], r[5], r[6], r[7]]))

        creades = actualitzades = 0
        pendents, sense_pom, sense_forma, linies = [], [], [], []

        with schema_context(opts['schema']), transaction.atomic():
            brw = Customer.objects.filter(codi=CUSTOMER_CODI).first()
            if not brw:
                raise CommandError(f'Customer {CUSTOMER_CODI} no existeix.')
            ss = SizeSystem.objects.filter(codi=SIZE_SYSTEM).first()
            if not ss:
                raise CommandError(f'SizeSystem {SIZE_SYSTEM} no existeix.')
            talles = list(ss.talles.order_by('ordre'))
            if not talles:
                raise CommandError(f'SizeSystem {SIZE_SYSTEM} sense talles.')
            base, run = talles[0], [t.etiqueta for t in talles]

            # 🔒 EL PANY P3: el joc es RESOL pels noms coneguts, no per un literal que la BD
            # ja ha rebatejat. I si no en surt cap, s'atura: mai un segon joc en silenci.
            rs = resol_el_joc(brw)
            rs_creat = False
            if rs is None:
                if not opts['create_ruleset']:
                    raise CommandError(
                        f'Cap GradingRuleSet de {CUSTOMER_CODI} amb cap dels noms coneguts '
                        f'{list(NOMS_DEL_JOC)} (ni per `nom` ni per `codi_sistema`). NO se\'n '
                        f'crea cap: si el joc viu amb un altre nom, crear-lo aquí en fabricaria '
                        f'un SEGON amb {len(files)} regles al costat del bo. Afegeix el nom viu '
                        f'a NOMS_DEL_JOC, o passa --create-ruleset si de debò no existeix.')
                rs = GradingRuleSet.objects.create(
                    nom=NOM, customer=brw, size_system=ss,
                    origen=GradingRuleSet.ORIGEN_CLIENT_RUN, actiu=True, codi_sistema=NOM)
                rs_creat = True
            # Un joc que ja existeix NO es reescriu (ni `origen`, ni `actiu`, ni `size_system`):
            # la sembra hi posa REGLES, no li redefineix la identitat.
            self.stdout.write(f'  ruleset {rs.id} · {"CREAT" if rs_creat else "ja existia"} '
                              f'({rs.nom!r}) · run {run} · base {base.etiqueta!r}\n')

            al = {a.client_code: a for a in
                  CustomerPOMAlias.objects.filter(customer=brw).select_related('pom')}

            for codi, logica, deltas in files:
                if logica == 'PENDENT':
                    # El full no en dona Δ: la mesura existeix al catàleg però encara no se
                    # sap com gradua. Una regla inventada aquí seria pitjor que cap regla.
                    pendents.append(codi)
                    continue
                a = al.get(codi)
                if not a or not a.pom_id:
                    sense_pom.append(codi)
                    continue
                forma = forma_de_la_regla(deltas, run)
                if forma is None:
                    sense_forma.append((codi, deltas))
                    continue

                _, creada = GradingRule.objects.update_or_create(
                    rule_set=rs, pom=a.pom,
                    defaults={'talla_base': base, 'valors_step': None, 'actiu': True,
                              'talla_break_pos': None, **forma},
                )
                creades += int(creada)
                actualitzades += int(not creada)
                brk = (f' break={forma["increment_break"]}@{forma["talla_break_label"]}'
                       if forma['increment_break'] is not None else '')
                linies.append(f'  {codi:5} pom {a.pom_id:4} {forma["logica"]:6} '
                              f'base={forma["increment_base"]}{brk}   (full: {logica} · '
                              f'{" · ".join(str(d) for d in deltas)})')

            if dry:
                transaction.set_rollback(True)

        for l in linies:
            self.stdout.write(l)

        self.stdout.write(f'\n── RECOMPTE ──\n'
                          f'  regles creades: {creades} · actualitzades: {actualitzades}')
        self.stdout.write(f'\n── PENDENT al full (sense Δ, cap regla): {len(pendents)} ──\n'
                          f'  {", ".join(pendents)}')
        if sense_pom:
            self.stdout.write(self.style.ERROR(
                f'\n── SENSE POM (cal F1 abans): {len(sense_pom)} ──\n  {", ".join(sense_pom)}'))
        if sense_forma:
            self.stdout.write(self.style.ERROR(
                f'\n── SENSE FORMA CANÒNICA (més d\'un esglaó): {len(sense_forma)} ──'))
            for codi, d in sense_forma:
                self.stdout.write(f'  {codi}: {d}')

        self.stdout.write(self.style.SUCCESS(f'\n=== FET ({head}) ==='))
