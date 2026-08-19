"""TRAM SEMBRA v4 · MODE ADDITIU — el catàleg canònic sobre un schema que JA en té un de vell.

`sembra_cataleg_v4` va néixer per a terreny verge (staging es va buidar abans). A PROD no hi ha
buidat: el catàleg vell (533 POMMaster a `fhort`) es queda **intacte al costat** com a arxiu mort
fins que cada model reconstrueixi la seva relació. Aquest guió és el germà additiu; **NO toca el
verge**, que és història i el va fer servir staging.

LA DIFICULTAT REAL, i per què no n'hi ha prou amb «match per codi»: el catàleg vell fa servir
**el mateix espai de codis** que el canònic, perquè al món vell el `codi_client` del POMMaster
era la nomenclatura de Brownie. Dels 142 codis del corpus, 69 ja existeixen a `fhort` — i només
30 són **el mateix POM**. Els altres 39 són el mateix codi per a una cota DIFERENT
(`A` = «FRONT WIDTH LOCATION» al vell, «1/2 chest width» al canònic). Enllaçar-los per codi
fusionaria dues cotes distintes i penjaria la regla de graduació canònica a la cota equivocada
de 37 POMs amb dades vives. Per això:

    CAP FUSIÓ AUTOMÀTICA. Es reutilitza NOMÉS quan codi i nom coincideixen; si el codi xoca amb
    una cota diferent, es REPORTA i es deixa estar (política `conservadora`), o s'aparta el vell
    amb el sufix `-ANTIC` per deixar el codi lliure al canònic (política `aparta-vells`), que és
    una decisió d'Agus i mai el defecte.

IDEMPOTENT: `get_or_create` per codi/àlies/regla. Córrer-lo dos cops no duplica res.
DRY-RUN per defecte (`--no-dry-run` escriu). El corpus viatja amb el repo (`ops/sembra_v4`).

    python manage.py sembra_cataleg_v4_additiu                      # DRY-RUN conservador
    python manage.py sembra_cataleg_v4_additiu --politica=aparta-vells
    python manage.py sembra_cataleg_v4_additiu --no-dry-run
"""
import csv
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django_tenants.utils import schema_context

from fhort.pom.management.commands.seed_brownie_ruleset import forma_de_la_regla
from fhort.pom.models import (CustomerPOMAlias, GradingRule, GradingRuleSet, POMCategory,
                              POMMaster, SizeSystem)
from fhort.tasks.models import Customer

# El corpus viatja amb el repo. El guió verge apunta a `/var/www/ftt-staging/ops/sembra_v4`, que
# és la ruta de la màquina d'staging i NO existeix a PROD: aquí es deriva de BASE_DIR i es pot
# sobreescriure amb --corpus.
CORPUS_DEFECTE = Path(settings.BASE_DIR).parent / 'ops' / 'sembra_v4'
TENANT = 'fhort'
CUSTOMER_CODI = 'BRW'
SIZE_SYSTEM = 'ALPHA_EU_W'
RULESET = 'BRW-CATALEG-v3'
DELTES = ('d_xxs_xs', 'd_xs_s', 'd_s_m', 'd_m_l')
SUFIX_ANTIC = '-ANTIC'


def _norm(s):
    """Nom comparable: sense majúscules, espais ni puntuació. `Centre`/`Center` NO s'igualen a
    posta — una diferència d'ortografia pot amagar una cota diferent i qui ho ha de dir és una
    persona, no una heurística."""
    return re.sub(r'[^a-z0-9]', '', (s or '').lower())


class Command(BaseCommand):
    help = 'SEMBRA v4 ADDITIVA · catàleg canònic sobre un schema amb catàleg vell. Dry-run per defecte.'

    def add_arguments(self, p):
        p.add_argument('--no-dry-run', action='store_true')
        p.add_argument('--schema', default=TENANT)
        p.add_argument('--corpus', default=str(CORPUS_DEFECTE))
        p.add_argument('--politica', choices=('conservadora', 'aparta-vells'), default='conservadora')

    def handle(self, *a, **o):
        dry = not o['no_dry_run']
        corpus = Path(o['corpus'])
        if not corpus.is_dir():
            raise CommandError(f'Corpus inexistent: {corpus}')
        rd = lambda n: list(csv.DictReader(open(corpus / n, encoding='utf-8'), delimiter=';'))
        canonic, alies = rd('SEMBRA_1_canonic.csv'), rd('SEMBRA_2a_alies_brownie_univocs.csv')

        cap = 'DRY-RUN (rollback al final)' if dry else 'ESCRIVINT'
        self.stdout.write(self.style.WARNING(
            f'=== SEMBRA v4 ADDITIVA · {cap} · politica={o["politica"]} ===\n'
            f'    corpus: {corpus}\n'))

        conflictes, apartats, notes = [], [], []
        with schema_context(o['schema']), transaction.atomic():
            brw = Customer.objects.filter(codi=CUSTOMER_CODI).first()
            if not brw:
                raise CommandError(f'Customer {CUSTOMER_CODI} no existeix.')
            ss = SizeSystem.objects.filter(codi=SIZE_SYSTEM).first()
            if not ss or not ss.talles.exists():
                raise CommandError(f'SizeSystem {SIZE_SYSTEM} inexistent o sense talles.')
            talles = list(ss.talles.order_by('ordre'))
            base, run = talles[0], [t.etiqueta for t in talles]

            # El joc s'identifica pel CODI ESTABLE (`codi_sistema`), no pel `nom`: el nom és
            # de PRESENTACIÓ i canvia (el 19/08 va passar a «GRADING BROWNIE 2026»). Buscar-lo
            # pel nom feia que, un cop rebatejat, la segona passada no el trobés i en creés un
            # de nou amb les 142 regles duplicades — la idempotència moria amb el rebateig.
            # Es neix amb `codi_sistema` poblat perquè la clau existeixi des del primer dia.
            rs = (GradingRuleSet.objects.filter(codi_sistema=RULESET, customer=brw).first()
                  or GradingRuleSet.objects.filter(nom=RULESET, customer=brw).first())
            rs_nou = rs is None
            if rs_nou:
                rs = GradingRuleSet.objects.create(
                    nom=RULESET, codi_sistema=RULESET, customer=brw, size_system=ss)
            notes.append(f'GradingRuleSet {RULESET}: {"CREAT" if rs_nou else "ja existia"} '
                         f'(id={rs.id}, {rs.regles.count()} regles)')

            # ── PAS 1 · categories (codis del corpus; no xoquen amb les 28 velles) ──────
            cats, n_cat_nova = {}, 0
            for i, r in enumerate(canonic, 2):
                fam, sec = r['familia'].strip(), r['seccio'].strip().replace('🆕', '').strip()
                if fam in cats:
                    continue
                c, fet = POMCategory.objects.get_or_create(
                    codi=fam, defaults={'nom_ca': sec, 'descripcio': '',
                                        'display_order': len(cats) + 1, 'actiu': True})
                cats[fam] = c
                n_cat_nova += int(fet)

            # ── PAS 2 · el catàleg canònic, codi a codi ────────────────────────────────
            vius = {p.codi_client.strip().upper(): p for p in POMMaster.objects.all()}
            poms, n_nou, n_reutil = {}, 0, 0
            for i, r in enumerate(canonic, 2):
                codi, nom = r['codi'].strip(), r['nom_en'].strip()
                if not codi or not nom:
                    conflictes.append(f'SEMBRA_1 línia {i}: codi o nom buit → FORA')
                    continue
                vell = vius.get(codi.upper())
                if vell is not None and _norm(vell.nom_client) == _norm(nom):
                    poms[codi] = vell               # el MATEIX POM: es reutilitza, no es duplica
                    n_reutil += 1
                    continue
                if vell is not None:
                    if o['politica'] == 'conservadora':
                        conflictes.append(
                            f'{codi}: el codi ja és de POMMaster #{vell.id} '
                            f'«{vell.nom_client[:40]}» i el canònic és «{nom[:40]}» → NO sembrat')
                        continue
                    nou_codi = f'{codi}{SUFIX_ANTIC}'
                    if nou_codi.upper() in vius or len(nou_codi) > 30:
                        conflictes.append(f'{codi}: no es pot apartar ({nou_codi} ocupat o massa llarg)')
                        continue
                    vell.codi_client = nou_codi
                    vell.save(update_fields=['codi_client'])
                    vius[nou_codi.upper()] = vell
                    apartats.append(f'#{vell.id} «{vell.nom_client[:38]}»: {codi} → {nou_codi}')
                p, fet = POMMaster.objects.get_or_create(
                    codi_client=codi,
                    defaults={'nom_client': nom, 'categoria': cats[r['familia'].strip()],
                              'pom_global': None, 'actiu': True, 'pendent_revisio': False,
                              'notes': ''})
                poms[codi] = p
                n_nou += int(fet)

            # ── PAS 3 · els àlies de Brownie ───────────────────────────────────────────
            n_ali, n_ali_ok, n_ali_x = 0, 0, 0
            for i, r in enumerate(alies, 2):
                cc, canon = r['client_code'].strip(), r['pom_canonic'].strip()
                if not cc:
                    conflictes.append(f'SEMBRA_2a línia {i}: client_code buit → FORA')
                    continue
                if canon not in poms:
                    conflictes.append(f'SEMBRA_2a línia {i} ({cc}): el canònic {canon!r} no és al '
                                      'catàleg (xoc no resolt) → àlies FORA')
                    continue
                desc = r['descripcions_cobertes'].strip()
                if ';' in desc or len(desc) > 200:
                    desc = ''
                viu = CustomerPOMAlias.objects.filter(customer=brw, client_code=cc).first()
                if viu:
                    if viu.pom_id == poms[canon].id:
                        n_ali_ok += 1
                    else:
                        n_ali_x += 1
                        conflictes.append(
                            f'ÀLIES {cc}: ja existeix i apunta a #{viu.pom_id} '
                            f'«{viu.pom.nom_client[:34]}»; el corpus el vol a {canon} '
                            f'#{poms[canon].id} → NO re-apuntat')
                    continue
                CustomerPOMAlias.objects.create(
                    customer=brw, pom=poms[canon], client_code=cc, description_en=desc,
                    es_instancia=bool(r['instancia_proposta'].strip()), origen='DICCIONARI',
                    pendent_revisio=False)
                n_ali += 1

            # ── PAS 4 · el grading, derivat dels quatre Δ ──────────────────────────────
            n_reg, n_reg_ja, formes = 0, 0, {}
            for i, r in enumerate(canonic, 2):
                codi = r['codi'].strip()
                if codi not in poms:
                    continue
                try:
                    deltes = [Decimal(r[k].strip().replace(',', '.')) for k in DELTES]
                except (InvalidOperation, AttributeError):
                    conflictes.append(f'{codi}: Δ il·legibles → SENSE REGLA')
                    continue
                forma = forma_de_la_regla(deltes, run)
                if forma is None:
                    conflictes.append(f'{codi}: {[str(d) for d in deltes]} no té forma canònica '
                                      '(més d\'un esglaó) → SENSE REGLA')
                    continue
                _, fet = GradingRule.objects.get_or_create(
                    rule_set=rs, pom=poms[codi],
                    defaults=dict(talla_base=base, talla_base_label=base.etiqueta,
                                  valors_step=None, talla_break_pos=None, actiu=True, **forma))
                n_reg += int(fet)
                n_reg_ja += int(not fet)
                if fet:
                    clau = forma['logica'] + ('+BREAK' if forma['increment_break'] is not None else '')
                    formes[clau] = formes.get(clau, 0) + 1

            self.stdout.write(f'  1  POMCategory        : {n_cat_nova} creades · '
                              f'{len(cats) - n_cat_nova} ja existien')
            self.stdout.write(f'  2  POMMaster canònics : {n_nou} creats · {n_reutil} reutilitzats '
                              f'(mateix codi I mateix nom) · {len(canonic) - len(poms)} sense sembrar')
            self.stdout.write(f'  2  vells apartats     : {len(apartats)}')
            self.stdout.write(f'  3  CustomerPOMAlias   : {n_ali} creats · {n_ali_ok} ja correctes · '
                              f'{n_ali_x} apunten a un altre POM (intactes)')
            self.stdout.write(f'  4  GradingRule        : {n_reg} creades · {n_reg_ja} ja existien  {formes}')
            self.stdout.write(f'\n  CATÀLEG CANÒNIC PRESENT: {len(poms)}/{len(canonic)}')
            self.stdout.write(f'  catàleg total al schema: {POMMaster.objects.count()} POMMaster')

            if dry:
                transaction.set_rollback(True)
                self.stdout.write(self.style.WARNING('\n⚠️  DRY-RUN: rollback fet.'))

        for n in notes:
            self.stdout.write(f'   · {n}')
        if apartats:
            self.stdout.write(f'\n── VELLS APARTATS ({len(apartats)}) ──')
            for x in apartats:
                self.stdout.write(f'   · {x}')
        self.stdout.write(f'\n── CONFLICTES / EXCEPCIONS ({len(conflictes)}) ──')
        for c in conflictes:
            self.stdout.write(self.style.ERROR(f'   · {c}'))
        self.stdout.write(self.style.SUCCESS(f'\n=== FI ({cap}) ==='))
