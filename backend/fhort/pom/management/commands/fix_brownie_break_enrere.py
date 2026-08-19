"""Break de BRW-CATALEG-v3: retrocedeix UNA posició al size run (Agus, 05/08/2026).

🔴 ERROR D'ORIGEN de la sembra del catàleg v3, confirmat contra
`docs/BROWNIE_CATALEG_POM_v3.xlsx`. NO és una regressió: cap commit havia tocat mai
`talla_break_label`; les etiquetes són així des que es va sembrar el ruleset.

EL PROBLEMA. El motor indexa cada aresta pel seu extrem EXTERIOR — el més llunyà de la
talla base (`grading_utils.increment_de_l_aresta`, llei documentada allà). Amb base S
(índex 2 del run XXS·XS·S·M·L·XL·XXL·3XL) els exteriors de les quatre primeres arestes
són 0 · 1 · 3 · 4. Perquè l'aresta XS→S prengui `increment_break`, el break ha de ser a
l'índex 1 = XS. Estava a S (índex 2), i per això l'aresta XS→S prenia `increment_base`:

    POM A (1/2 chest width)   full: 2 · 3 · 3 · 3
                            actual: 2 · 2 · 3 · 3     ← desplaçat una posició

LA CORRECCIÓ. Totes les etiquetes retrocedeixen una posició: S → XS, M → S.

⚠️ DEGENERACIÓ. Com que l'exterior mai val 2, per a les regles de patró
[ib, ib, brk, brk] les etiquetes S i M donen EXACTAMENT el mateix resultat. Les 12
regles a M (i les seves 480 residents) no canvien de corba: només s'alinea el nom amb
el del full, que ja les anomena «BREAK A S». Les 65 a S (2.600 residents) sí que canvien.

Contraprova contra el full (unió per codi, 54 regles): 25 passen de NO a OK, 29 eren
ambigües i segueixen OK, i CAP no empitjora.

⚠️⚠️ AQUESTA COMANDA NO ÉS IDEMPOTENT, i no pot ser-ho: un cop corregida, hi ha
etiquetes 'S' LEGÍTIMES (les que venien de 'M'), i tornar-la a passar les desplaçaria
a 'XS'. Per això exigeix la distribució EXACTA d'origen abans d'escriure i es nega si
no la troba. Executar-la dues vegades és un error que la comanda ha d'impedir, no una
possibilitat que hagi de tolerar.

    python manage.py fix_brownie_break_enrere                # DRY-RUN
    python manage.py fix_brownie_break_enrere --no-dry-run   # aplica + verifica
"""
from collections import Counter

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django_tenants.utils import schema_context

from fhort.pom.models import GradingRuleSet, GradingRule
from fhort.models_app.models import ModelGradingRule
from fhort.pom.seed_data import consolidate_pom_los as CFG

RULESET_NOM = 'BRW-CATALEG-v3'
ENRERE = {'S': 'XS', 'M': 'S'}

# Distribució EXACTA esperada abans d'escriure. És el guard contra la doble passada.
ESPERAT_RULESET = {'S': 65, 'M': 12, None: 37}
ESPERAT_RESIDENTS = {'S': 2600, 'M': 480, None: 1480}


def _dist(qs):
    return dict(Counter(qs.values_list('talla_break_label', flat=True)))


class Command(BaseCommand):
    help = ('Retrocedeix una posició talla_break_label a BRW-CATALEG-v3 i a les seves '
            'regles residents (S→XS, M→S).')

    def add_arguments(self, parser):
        parser.add_argument('--no-dry-run', action='store_true')
        parser.add_argument('--schema', default=CFG.TENANT)

    def handle(self, *args, **opts):
        dry = not opts['no_dry_run']
        head = 'DRY-RUN' if dry else 'ESCRIVINT'
        self.stdout.write(self.style.WARNING(f'=== fix_brownie_break_enrere · {head} ==='))

        with schema_context(opts['schema']), transaction.atomic():
            rs = GradingRuleSet.objects.filter(nom=RULESET_NOM)
            if rs.count() != 1:
                raise CommandError(f'Ruleset ambigu o inexistent: {RULESET_NOM!r} (n={rs.count()})')
            rs = rs.first()

            regles = GradingRule.objects.filter(rule_set=rs)
            residents = ModelGradingRule.objects.filter(model__grading_rule_set=rs, actiu=True)

            d_rs, d_res = _dist(regles), _dist(residents)
            self.stdout.write(f'\n[{RULESET_NOM}] id={rs.id}')
            self.stdout.write(f'   ABANS · ruleset   : {d_rs}')
            self.stdout.write(f'   ABANS · residents : {d_res}')

            # GUARD DUR — la doble passada desplaçaria les etiquetes legítimes.
            if d_rs != ESPERAT_RULESET or d_res != ESPERAT_RESIDENTS:
                raise CommandError(
                    'Distribució inesperada: aquesta comanda NO és idempotent i només pot '
                    f'córrer sobre l\'estat d\'origen.\n  ruleset esperat   {ESPERAT_RULESET}\n'
                    f'  ruleset trobat    {d_rs}\n  residents esperat {ESPERAT_RESIDENTS}\n'
                    f'  residents trobat  {d_res}\n'
                    'Si ja s\'ha aplicat, NO la tornis a passar.')

            # Els ids es fixen ABANS de qualsevol escriptura: fer-ho en dues passades
            # (S→XS i després M→S) desplaçaria dues vegades les que acaben d'arribar a S.
            plans = []
            for old, new in ENRERE.items():
                plans.append((old, new,
                              list(regles.filter(talla_break_label=old).values_list('id', flat=True)),
                              list(residents.filter(talla_break_label=old).values_list('id', flat=True))))

            for old, new, ids_rs, ids_res in plans:
                self.stdout.write(f'   {old!r} → {new!r} : ruleset={len(ids_rs)} · residents={len(ids_res)}')

            if not dry:
                tot_rs = tot_res = 0
                for old, new, ids_rs, ids_res in plans:
                    tot_rs += GradingRule.objects.filter(id__in=ids_rs).update(talla_break_label=new)
                    tot_res += ModelGradingRule.objects.filter(id__in=ids_res).update(
                        talla_break_label=new)

                d_rs2, d_res2 = _dist(regles), _dist(residents)
                self.stdout.write(self.style.SUCCESS(
                    f'\n   ACTUALITZADES · ruleset={tot_rs} · residents={tot_res}'))
                self.stdout.write(f'   DESPRÉS · ruleset   : {d_rs2}')
                self.stdout.write(f'   DESPRÉS · residents : {d_res2}')

                esperat_rs = {'XS': 65, 'S': 12, None: 37}
                esperat_res = {'XS': 2600, 'S': 480, None: 1480}
                if d_rs2 != esperat_rs or d_res2 != esperat_res:
                    raise CommandError(
                        f'Verificació FALLIDA. Rollback.\n  esperat {esperat_rs} / {esperat_res}\n'
                        f'  trobat  {d_rs2} / {d_res2}')
                self.stdout.write(self.style.SUCCESS('   VERIFICACIÓ: distribució correcta.'))
            else:
                transaction.set_rollback(True)
                self.stdout.write('\n  (dry-run: rollback, res tocat)')

        self.stdout.write(self.style.SUCCESS('=== FET ==='))
