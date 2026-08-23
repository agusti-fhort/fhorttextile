"""S7 · LA FINESTRA DE GRADUACIÓ — tallar FKs inertes i arxivar els jocs condemnats.

**NOMÉS PROD.** La comanda no ho dedueix de cap bandera d'entorn: **ho mesura**.

🚨 **I A STAGING NO ÉS UN NO-OP SENCER, contra el que el brief dona per fet.** Sí que ho és la
meitat (b): el cens del 22/08 ja va mesurar que aquí hi ha **un sol `GradingRuleSet` i és el
supervivent** —cap condemnat, res a arxivar—. Però la meitat (a) **sí que trobaria feina**: tres
models (1320, 1322, 1383) tenen FK al joc supervivent i les seves residents la fan inerta. Per
això, quan **no hi ha cap condemnat**, tallar FKs exigeix `--talla-fk-sense-condemna`: la
FASE C del brief corre S1→S6 i S7 no hi entra, i un tall silenciós a staging seria feina que
ningú ha demanat.

Dues coses, i cap `DELETE`:

  (a) **tallar la FK `grading_rule_set`** dels models que en tenen una d'INERTA — inerta vol
      dir que les regles RESIDENTS ja cobreixen tot el que el contenidor cobriria, i per tant
      tallar-la no perd **cap cel·la**;
  (b) **`actiu=False` als jocs condemnats** — tots menys el supervivent, que es resol **pel
      NOM** (pany P3 del 22/08: `NOMS_DEL_JOC`, mai per pk, que ja ha divergit).

🚨 **LA COBERTURA ES RE-MESURA, NO ES CONFIA.** El brief dona 25 models amb «=0 mesurat» del
cens del 22/08. Aquesta comanda **torna a comptar** model per model, a la BD que tingui al
davant i en el moment de tallar, i **ATURA sencera** si algun en té més de 0: entre el cens i
la finestra hi ha dies, i una resident esborrada al mig convertiria un tall inert en una
graduació perduda. El predicat és el contra-test de C7-bis:

    cel·les que NOMÉS el contenidor cobriria =
        { (pom, peça) mesurats al model : el contenidor els cobreix
                                          i cap resident (pròpia o de la mare) no ho fa }

🔒 **LA FRONTERA G6 NO ES TOCA.** `SizingProfile`, `GarmentTypeItem` i `GradingVersion` es
**compten i es reporten** —els 14 jocs buits amb apuntadors queden arxivats amb els apuntadors
intactes, literal del brief— i no els toca ni una escriptura.

    manage.py finestra_graduacio --schema fhort                # DRY-RUN (a staging: no-op)
    manage.py finestra_graduacio --schema fhort --no-dry-run
"""
from django.core.management.base import CommandError

from fhort.pom.management.commands.seed_brownie_ruleset import NOMS_DEL_JOC
from fhort.pom.models import GradingRule, GradingRuleSet
from fhort.pom.sembra_v5.base import ComandaV5


class Command(ComandaV5):
    help = 'S7 · talla les FK de graduació inertes i arxiva els jocs condemnats (PROD).'
    PAS = 'S7 · finestra de graduació'
    #: Del brief, i són de PROD. A staging divergeixen i el report ho canta.
    ESPERAT = {'models amb FK de graduació tallada': 25, 'jocs arxivats': 27}

    def arguments_propis(self, parser):
        parser.add_argument('--schema', required=True,
                            help='Schema del tenant (sense default: pany P2 del 22/08).')
        parser.add_argument('--talla-fk-sense-condemna', action='store_true',
                            help='Permet tallar FKs en un entorn sense cap joc condemnat.')

    def corre(self, opts):
        from fhort.models_app.models import BaseMeasurement, Model, ModelGradingRule

        tallats = inerts = perillosos = arxivats = ja_inactius = preexistents = 0
        with self.transacciona(opts['schema']):
            jocs = list(GradingRuleSet.objects.order_by('pk'))
            self.guarda('GradingRuleSet al tenant', len(jocs))

            # ── (a) les FK inertes ────────────────────────────────────────────────────────
            supervivents = [j for j in jocs
                            if j.nom in NOMS_DEL_JOC or j.codi_sistema in NOMS_DEL_JOC]
            self.guarda('jocs SUPERVIVENTS (resolts pel nom)', len(supervivents))
            if jocs and not supervivents:
                raise CommandError(
                    f'Cap joc amb els noms coneguts {list(NOMS_DEL_JOC)}: arxivar-los «tots '
                    'menys el supervivent» els arxivaria TOTS. La finestra ATURA (pany P3).')
            vius = {j.pk for j in supervivents}
            condemnats = [j for j in jocs if j.pk not in vius]
            self.guarda('jocs CONDEMNATS al tenant', len(condemnats))

            amb_fk = list(Model.objects.filter(grading_rule_set__isnull=False)
                          .select_related('grading_rule_set').order_by('pk'))
            self.guarda('models amb FK a un joc', len(amb_fk))
            if amb_fk and not condemnats and not opts['talla_fk_sense_condemna']:
                self.excepcio(
                    f'🚨 {len(amb_fk)} models tenen FK a un joc i NO hi ha cap condemnat: en '
                    'aquest entorn S7 no és el no-op que el brief dona per fet. No es talla '
                    'res sense --talla-fk-sense-condemna (la FASE C corre S1→S6).')
                amb_fk = []

            for m in amb_fk:
                mesurats = set(BaseMeasurement.objects.filter(model=m)
                               .values_list('pom_id', 'garment').distinct())
                resident = set(ModelGradingRule.objects
                               .filter(model_id=m.id, actiu=True)
                               .values_list('pom_id', 'garment'))
                mares = {pid for (pid, g) in resident if g == ''}
                contenidor = set(GradingRule.objects
                                 .filter(rule_set_id=m.grading_rule_set_id, actiu=True)
                                 .values_list('pom_id', flat=True))

                def coberta(pid, g):
                    """La cel·la que quedaria després de tallar: regla pròpia, o de la mare."""
                    return (pid, g) in resident or pid in mares

                if mares:
                    # ⚖️ C7: amb residents a la mare, el motor NO llegeix el contenidor. No hi
                    # ha res a perdre; el que no cobreixin les residents ja és absent avui.
                    nomes_contenidor = set()
                    absents = {(pid, g) for (pid, g) in mesurats if not coberta(pid, g)}
                    if absents:
                        preexistents += len(absents)
                        self.excepcio(
                            f'ℹ️ model {m.pk} {m.codi_intern!r}: {len(absents)} cel·les '
                            'absents ABANS de la finestra (la mare té residents, o sigui que '
                            'el contenidor ja era lletra morta). No les crea el tall.')
                else:
                    nomes_contenidor = {(pid, g) for (pid, g) in mesurats
                                        if pid in contenidor and not coberta(pid, g)}
                if nomes_contenidor:
                    perillosos += 1
                    self.excepcio(
                        f'🚨 model {m.pk} {m.codi_intern!r}: {len(nomes_contenidor)} cel·les que '
                        f'NOMÉS el contenidor {m.grading_rule_set.nom!r} cobreix — tallar la '
                        'FK les perdria. La finestra NO continua.')
                    continue
                inerts += 1
                m.grading_rule_set = None
                m.save(update_fields=['grading_rule_set'])
                tallats += 1

            if perillosos and not self.dry:
                raise CommandError(
                    f'{perillosos} models amb cobertura que només el contenidor dona: la '
                    'finestra ATURA sencera (cap tall, cap arxivat). El número del brief es '
                    'RE-MESURA, i avui no surt.')
            if perillosos:
                self.excepcio(
                    f'🚨 {perillosos} models farien perdre cel·les: ESCRIVINT, la finestra '
                    'ATURA sencera. En dry-run segueix per poder llegir la resta del cens.')

            self.guarda('models amb FK de graduació tallada', tallats)
            self.guarda('cel·les absents PREEXISTENTS (no les crea el tall)',
                        preexistents)

            # ── (b) els jocs condemnats ───────────────────────────────────────────────────
            for j in condemnats:
                if not j.actiu:
                    ja_inactius += 1
                    continue
                j.actiu = False
                j.save(update_fields=['actiu'])
                arxivats += 1
                self.excepcio(f'📦 joc {j.pk} {j.nom!r} → actiu=False (cap DELETE).')

            self.guarda('jocs arxivats', arxivats)
            self.guarda('jocs que ja eren inactius (idempotència)', ja_inactius)

            # ── La frontera G6: es compta i no es toca ────────────────────────────────────
            self._frontera(vius)

            if not amb_fk and not condemnats:
                self.diu('   ℹ️  cap FK a tallar i cap joc a arxivar: en aquest entorn S7 és '
                         'un NO-OP de debò.')

        self.diu(f'   FK tallades {tallats} (inertes {inerts}) · jocs arxivats {arxivats} '
                 f'· ja inactius {ja_inactius}')

    def _frontera(self, vius):
        """Els apuntadors de G6: recompte al report, cap escriptura."""
        from fhort.pom.models import SizingProfile
        from fhort.tasks.models import GarmentTypeItem

        sp = SizingProfile.objects.filter(grading_rule_set__isnull=False)
        gti = GarmentTypeItem.objects.filter(grading_rule_set__isnull=False)
        self.guarda('SizingProfile amb joc (no tocats)', sp.count())
        self.guarda('SizingProfile cap a un joc ARXIVAT', sp.exclude(
            grading_rule_set_id__in=vius).count())
        self.guarda('GarmentTypeItem amb joc (no tocats)', gti.count())
        self.guarda('GarmentTypeItem cap a un joc ARXIVAT', gti.exclude(
            grading_rule_set_id__in=vius).count())
