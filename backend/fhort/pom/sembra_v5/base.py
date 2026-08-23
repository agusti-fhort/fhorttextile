"""LA FORMA COMUNA DE LES SET COMANDES DE LA SEMBRA v5.

El brief exigeix que **totes** siguin iguals en quatre coses, i per això viuen aquí i no
copiades set vegades:

  · **dry-run per defecte** (`--no-dry-run` per escriure), amb `set_rollback` al final;
  · **idempotents** — la segona passada ha de donar 0 canvis, i el report ho ha de poder dir;
  · **guarda de recompte exacte dins de l'`atomic()`**, i **abort** si el real ≠ l'esperat;
  · **report** amb esperat vs real de cada xifra, i les excepcions al davant.

🔑 **L'ESPERAT ÉS DEL BRIEF, I EL BRIEF PARLA DE PROD.** Les xifres declarades a `ESPERAT` són
les que Agus va escriure al brief; staging té una altra història (el cens del 22/08 ho diu:
1 joc i cap condemnat, 25 famílies de lletra i cap `CAT-*`). Per això la divergència **no és
un error de la comanda**: és exactament el que el brief mana reportar al davant. La regla:

  · en **DRY-RUN** una divergència es reporta i la correguda segueix —el dry-run és
    l'instrument de mesura, i aturar-lo a la primera xifra amagaria la resta del cens—;
  · en **ESCRIPTURA** una divergència ATURA dins de l'`atomic()`, i llavors o es corregeix la
    causa o l'operador declara la xifra mesurada amb `--espera NOM=N`, que és un acte humà i
    consta al report.
"""
from contextlib import contextmanager

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django_tenants.utils import schema_context

from . import corpus


class ComandaV5(BaseCommand):
    #: `{nom de la xifra: valor esperat}` — el que el brief declara. Buit = no en declara cap.
    ESPERAT = {}
    #: Passos que la comanda escriu, per al rètol de capçalera.
    PAS = ''

    def add_arguments(self, parser):
        parser.add_argument('--no-dry-run', action='store_true',
                            help='Escriu. Sense això, tot es fa i es desfà (dry-run).')
        parser.add_argument('--xlsx', default=None,
                            help='Camí del corpus r2. Per defecte, els dos camins del brief.')
        parser.add_argument('--espera', action='append', default=[], metavar='NOM=N',
                            help='Declara la xifra REAL d\'aquest entorn per a una guarda.')
        self.arguments_propis(parser)

    def arguments_propis(self, parser):
        """Els arguments que només té aquesta comanda."""

    # ── Report ────────────────────────────────────────────────────────────────────────────
    def _prepara(self, opts):
        self.dry = not opts['no_dry_run']
        self.excepcions = []
        self.guardes = []
        self.declarat = {}
        for e in opts['espera']:
            if '=' not in e:
                raise CommandError(f'--espera {e!r}: la forma és NOM=N.')
            nom, _, n = e.partition('=')
            self.declarat[nom.strip()] = int(n)

    def excepcio(self, txt):
        self.excepcions.append(txt)

    def guarda(self, nom, real):
        """Registra una xifra i la contrasta amb l'esperada. Retorna el real, sempre."""
        esperat = self.declarat.get(nom, self.ESPERAT.get(nom))
        self.guardes.append((nom, real, esperat, nom in self.declarat))
        return real

    def diu(self, txt=''):
        self.stdout.write(txt)

    @contextmanager
    def transacciona(self, schema):
        """`schema_context` + `atomic`, amb el rollback del dry-run i l'abort de les guardes.

        L'abort va **dins** de l'`atomic()` a posta: una guarda que peti ha de deixar la BD
        exactament com era, no a mitges.
        """
        with schema_context(schema), transaction.atomic():
            yield
            dolentes = [g for g in self.guardes if g[2] is not None and g[1] != g[2]]
            if dolentes and not self.dry:
                transaction.set_rollback(True)
                detall = ' · '.join(f'{n}: esperat {e}, real {r}' for n, r, e, _ in dolentes)
                raise CommandError(
                    f'GUARDA DE RECOMPTE: {detall}\n'
                    '   La sembra no escriu amb una xifra que no és la declarada. O es '
                    'corregeix la causa, o es declara la mesurada amb --espera NOM=N.')
            if self.dry:
                transaction.set_rollback(True)

    # ── El guió ───────────────────────────────────────────────────────────────────────────
    def handle(self, *args, **opts):
        self._prepara(opts)
        cap = 'DRY-RUN (rollback al final)' if self.dry else '🔴 ESCRIVINT'
        self.diu(self.style.WARNING(f'=== SEMBRA v5 · {self.PAS} · {cap} ==='))
        sha, poms, families, alies = corpus.carrega(opts['xlsx'])
        self.corpus = {'sha': sha, 'poms': poms, 'families': families, 'alies': alies}
        self.diu(f'   corpus r2 verificat · sha256 {sha[:16]}… · '
                 f'{len(poms)} POMs · {len(families)} famílies · {len(alies)} àlies\n')

        self.corre(opts)

        self.diu('\n── GUARDES DE RECOMPTE ──')
        for nom, real, esperat, declarat in self.guardes:
            if esperat is None:
                self.diu(f'   · {nom}: {real}   (el brief no en declara cap)')
            elif real == esperat:
                marca = ' (declarat a --espera)' if declarat else ''
                self.diu(self.style.SUCCESS(f'   ✅ {nom}: {real} = esperat{marca}'))
            else:
                self.diu(self.style.ERROR(
                    f'   🚨 {nom}: real {real} ≠ esperat {esperat} — PREMISSA DEL BRIEF QUE '
                    'NO ES CONFIRMA'))
        if self.excepcions:
            self.diu(f'\n── EXCEPCIONS ({len(self.excepcions)}) ──')
            for e in self.excepcions:
                self.diu(self.style.ERROR(f'   · {e}'))
        self.diu(self.style.SUCCESS(f'\n=== FI · {self.PAS} · {cap} ===' ))

    def corre(self, opts):
        raise NotImplementedError
