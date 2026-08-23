"""TRAM SEMBRA v4 — el catàleg canònic (142), els àlies de Brownie (94) i el seu grading (142).

Corpus: `ops/sembra_v4/*.csv` (UTF-8, separador `;`). Tres passos, una sola transacció:

  1  SEMBRA_1_canonic  → 25 `POMCategory` + 142 `POMMaster`   (el catàleg de la casa)
  2a SEMBRA_2a         → 94 `CustomerPOMAlias` de Brownie      (la seva nomenclatura)
  3  SEMBRA_1_canonic  → 142 `GradingRule` a `BRW-CATALEG-v3`  (els 4 Δ del mateix full)

`SEMBRA_2b` (17 codis ambigus, 45 files) **NO ES SEMBRA**: decisió d'Agus (D-31.27) — és corpus
del matcher, no àlies. Un codi ambigu sembrat com a àlies univoc donaria la feina per feta.

🔑 **UN RULESET PER CLIENT MENTRE EL CLIENT NO DIFERENCIÏ** (llei Agus 05/08, full MATCHER):
tot el grading de Brownie va a `BRW-CATALEG-v3`, que ja existeix i és buit. El CSV no declara
cap agrupació perquè no n'hi ha cap a declarar.

⚠️ **LA COLUMNA `trenca` NO ES TRANSCRIU: ES TRADUEIX.** El full anomena l'ÚLTIMA talla del Δ
petit; el motor ancora a la PRIMERA del Δ gran. La forma surt dels quatre Δ via
`forma_de_la_regla` (F4) — la MATEIXA funció que ja fa servir `seed_brownie_ruleset`, importada
i no recopiada. Transcriure `trenca` desplaçaria les 98 regles amb break una talla sencera.

Cap fila inventada: una fila que no valida es REPORTA i queda fora, mai s'adapta. Els duplicats
han de petar contra `uniq_pommaster_codi_client_ci` / `uniq_customer_client_code`, no colar-se.

    python manage.py sembra_cataleg_v4                # DRY-RUN
    python manage.py sembra_cataleg_v4 --no-dry-run   # escriu
"""
import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django_tenants.utils import schema_context

from fhort.pom.management.commands.seed_brownie_ruleset import (NOMS_DEL_JOC, forma_de_la_regla,
                                                                resol_el_joc)
from fhort.pom.models import (CustomerPOMAlias, GradingRule, GradingRuleSet, POMCategory,
                              POMMaster, SizeSystem)
from fhort.tasks.models import Customer

CORPUS = Path('/var/www/ftt-staging/ops/sembra_v4')
TENANT = 'fhort'
CUSTOMER_CODI = 'BRW'
SIZE_SYSTEM = 'ALPHA_EU_W'
#: El nom CANÒNIC del joc. La resolució en viu NO passa per aquí: va per `NOMS_DEL_JOC`
#: (pany P3), perquè aquest nom és exactament el que el rebateig de PROD ja no fa servir.
RULESET = 'BRW-CATALEG-v3'
DELTES = ('d_xxs_xs', 'd_xs_s', 'd_s_m', 'd_m_l')


def _llegeix(nom):
    with open(CORPUS / nom, encoding='utf-8') as f:
        return list(csv.DictReader(f, delimiter=';'))


class Command(BaseCommand):
    help = 'TRAM SEMBRA v4 · catàleg canònic (142) + àlies Brownie (94) + grading (142).'

    def add_arguments(self, parser):
        parser.add_argument('--no-dry-run', action='store_true')
        parser.add_argument('--schema', default=TENANT)

    def handle(self, *args, **opts):
        dry = not opts['no_dry_run']
        cap = 'DRY-RUN (rollback al final)' if dry else 'ESCRIVINT'
        self.stdout.write(self.style.WARNING(f'=== SEMBRA v4 · {cap} ===\n'))

        canonic = _llegeix('SEMBRA_1_canonic.csv')
        alies = _llegeix('SEMBRA_2a_alies_brownie_univocs.csv')
        excepcions = []

        with schema_context(opts['schema']), transaction.atomic():
            # ── Terreny: ha d'estar buit (el buidat és un pas previ, no d'aquest guió) ────
            if POMMaster.objects.exists():
                raise CommandError(
                    f'{POMMaster.objects.count()} POMMaster vius: la sembra no s\'executa '
                    'sobre un catàleg poblat (els duplicats han de petar, no fusionar-se).')

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
            # 🔒 PANY P3 (22/08): el joc es resol per la llista de noms coneguts, no pel
            # literal `RULESET` —que la BD de PROD ja ha rebatejat a «GRADING BROWNIE 2026».
            # Aquesta comanda no en crea cap en cap cas: si no el troba, ATURA.
            rs = resol_el_joc(brw)
            if not rs:
                raise CommandError(
                    f'Cap GradingRuleSet de {CUSTOMER_CODI} amb cap dels noms coneguts '
                    f'{list(NOMS_DEL_JOC)} (ni per `nom` ni per `codi_sistema`). La sembra no '
                    f'en crea cap: afegeix el nom viu a NOMS_DEL_JOC.')
            if rs.regles.exists():
                raise CommandError(f'{rs.nom!r} (pk={rs.id}) ja té {rs.regles.count()} regles.')
            self.stdout.write(f'  ruleset {rs.id} {rs.nom!r} · run {run} · base {base.etiqueta!r}\n')

            # ── PAS 1 · categories + catàleg canònic ──────────────────────────────────
            # La `seccio` és el rètol de la família; el `🆕` és anotació del full (marca les
            # famílies noves del v4), no part del nom — es reporta i no entra a la BD.
            cats, ordre = {}, 0
            for r in canonic:
                fam, sec = r['familia'].strip(), r['seccio'].strip()
                if fam in cats:
                    continue
                ordre += 1
                net = sec.replace('🆕', '').strip()
                if net != sec:
                    excepcions.append(f'seccio {sec!r}: `🆕` (anotació del full) no desat')
                cats[fam] = POMCategory.objects.create(
                    codi=fam, nom_ca=net, descripcio='', display_order=ordre, actiu=True)

            poms = {}
            for i, r in enumerate(canonic, 2):
                codi, nom = r['codi'].strip(), r['nom_en'].strip()
                if not codi or not nom:
                    excepcions.append(f'SEMBRA_1 línia {i}: codi o nom buit → FORA')
                    continue
                poms[codi] = POMMaster.objects.create(
                    codi_client=codi, nom_client=nom, categoria=cats[r['familia'].strip()],
                    pom_global=None, actiu=True, pendent_revisio=False, notes='')

            self.stdout.write(f'  1  POMCategory creades: {len(cats)}')
            self.stdout.write(f'  1  POMMaster creats:    {len(poms)}')

            # ── PAS 2a · els àlies de Brownie ─────────────────────────────────────────
            # `capa_proposta` NO es desa: `CustomerPOMAlias` no té camp de capa (ni l'ha de
            # tenir — la capa és del VALOR, no del vocabulari). `instancia_proposta` tampoc:
            # el model desa DELIBERADAMENT només que és una repetició (`es_instancia`), no
            # QUINA — auto-triar-la seria inventar la dada que el document no porta.
            n_alies = n_inst = 0
            for i, r in enumerate(alies, 2):
                cc, canon = r['client_code'].strip(), r['pom_canonic'].strip()
                if not cc:
                    excepcions.append(f'SEMBRA_2a línia {i}: client_code buit → FORA')
                    continue
                if canon not in poms:
                    excepcions.append(
                        f'SEMBRA_2a línia {i} ({cc}): pom_canonic {canon!r} no és al '
                        'catàleg canònic → FORA')
                    continue
                # ⚠️ **`descripcions_cobertes` NO ÉS UN NOM: ÉS UNA LLISTA** (QA Agus 09/08).
                #
                # La columna del full diu quines redaccions del document cobreix aquest codi, i
                # en porta diverses separades per `;`. Anava sencera a `description_en`, que és
                # el camp de PRESENTACIÓ: és el que `nomenclatura.alies_per_pom` serveix com a
                # `client_name_en` i el que el carril de mesures pinta com a nom de la fila. Per
                # això la fila del POM «A» del model 1320 es llegia
                #   «1/2 chest width (armpit to armpit); 1/2 front chest width (armpit to armpit)»
                # —totes les possibilitats del matcher concatenades— en comptes del nom de la
                # cota. Sis àlies de Brownie van quedar així.
                #
                # Una llista de candidats no es pot triar per la persona ni per nosaltres: la
                # que mana quan no hi ha UNA redacció del client és la CANÒNICA, i deixar el
                # camp buit és exactament el que la fa manar (la presentació ja fa el fallback).
                # Quan la columna porta una sola redacció, aquella SÍ que és el nom del client.
                desc = r['descripcions_cobertes'].strip()
                if ';' in desc:
                    excepcions.append(f'SEMBRA_2a línia {i} ({cc}): `descripcions_cobertes` porta '
                                      f'{desc.count(";") + 1} redaccions → àlies SENSE '
                                      'description_en (mana el nom canònic)')
                    desc = ''
                if len(desc) > 200:
                    excepcions.append(f'SEMBRA_2a línia {i} ({cc}): descripció de {len(desc)} '
                                      'caràcters (max 200) → FORA')
                    continue
                es_inst = bool(r['instancia_proposta'].strip())
                CustomerPOMAlias.objects.create(
                    customer=brw, pom=poms[canon], client_code=cc, description_en=desc,
                    es_instancia=es_inst, origen='DICCIONARI', pendent_revisio=False)
                n_alies += 1
                n_inst += int(es_inst)
            self.stdout.write(f'  2a CustomerPOMAlias creats: {n_alies} '
                              f'(dels quals es_instancia=True: {n_inst})')

            # ── PAS 3 · el grading, DERIVAT dels quatre Δ ─────────────────────────────
            n_reg, formes = 0, {}
            for i, r in enumerate(canonic, 2):
                codi = r['codi'].strip()
                if codi not in poms:
                    continue
                try:
                    deltes = [Decimal(r[k].strip().replace(',', '.')) for k in DELTES]
                except (InvalidOperation, AttributeError):
                    excepcions.append(f'SEMBRA_1 línia {i} ({codi}): Δ il·legibles → SENSE REGLA')
                    continue
                forma = forma_de_la_regla(deltes, run)
                if forma is None:
                    excepcions.append(f'SEMBRA_1 línia {i} ({codi}): {[str(d) for d in deltes]} '
                                      'no té forma canònica (més d\'un esglaó) → SENSE REGLA')
                    continue
                GradingRule.objects.create(
                    rule_set=rs, pom=poms[codi], talla_base=base,
                    talla_base_label=base.etiqueta, valors_step=None, talla_break_pos=None,
                    actiu=True, **forma)
                n_reg += 1
                clau = forma['logica'] + ('+BREAK' if forma['increment_break'] is not None else '')
                formes[clau] = formes.get(clau, 0) + 1

                # Contrast amb la columna `trenca` del full (ha de ser la talla ANTERIOR).
                full, der = r['trenca'].strip(), forma['talla_break_label']
                if der is not None:
                    if full not in run or run[run.index(full) + 1] != der:
                        excepcions.append(
                            f'{codi}: el full diu break a {full!r} i dels Δ en surt {der!r} '
                            '(no és la talla següent) — sembrat el DERIVAT')
                elif full not in ('—', '-', ''):
                    excepcions.append(f'{codi}: el full diu break a {full!r} però els Δ no en '
                                      'donen cap — sembrat SENSE break')

            self.stdout.write(f'  3  GradingRule creades:     {n_reg}  {formes}')

            if dry:
                transaction.set_rollback(True)
                self.stdout.write(self.style.WARNING('\n⚠️  DRY-RUN: rollback fet.'))

        self.stdout.write(f'\n── EXCEPCIONS ({len(excepcions)}) ──')
        for e in excepcions:
            self.stdout.write(self.style.ERROR(f'   · {e}'))
        if not excepcions:
            self.stdout.write('   cap: les 142 + 94 + 142 files han entrat senceres.')
        self.stdout.write(self.style.SUCCESS(f'\n=== FI ({cap}) ==='))
