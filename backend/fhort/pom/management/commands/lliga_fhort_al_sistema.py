"""S3 · EL LLIGAM — cada POM VIU del tenant, al seu global de sistema.

⚖️ **EL CATÀLEG MANA** (decisió d'Agus del 23/08, tancament final). El mapa `Codi Brownie →
codi de sistema` del r2 és un **document aprovat per la Montse**, i amb `--el-cataleg-mana` cap
guarda de nom el barra: el full diu quin és el canònic i el full guanya. Les **dues úniques
excepcions** —`N → N5` i `RW → R7`, mesurades el 23/08 i confirmades com a mesures DIFERENTS—
viuen a `EXCEPCIONS_DEL_MAPA` i queden fora sempre.

Sense el flag, el lligam vol **DUES coincidències alhora, i mai una de sola** (la llei que
regia fins al tancament final):

    (1) CODI      — el mapa `codi Brownie → codi de sistema` del full ALIES_BROWNIE; o, si el
                    full no el mapa, que el codi del POM SIGUI un codi del v5;
    (2) NOM       — que el nom del POM al tenant i el `Nom EN` del v5 siguin **el mateix nom
                    normalitzat** (sense accents, sense majúscules, sense puntuació).

🚨 **PER QUÈ EL NOM, I NO NOMÉS EL CODI.** Mesurat el 23/08 als dos entorns: **dels 105 codis
que el full mapa, 16 apunten a un POM que es diu una altra cosa** — `N` («Motive placement»)
cap a `N5` («Reflective band height»), `RW` («Welt height») cap a `R7` («Pocket topstitch»).
Lligar-los pel codi sol hauria posat el canònic equivocat en silenci. I al revés: dels 16 POMs
vius amb un codi que el v5 també fa servir, **cap no vol dir el mateix** (el `M` del tenant és
*Leg opening*; el del v5, *Neck width*), i per això el codi propi tampoc lliga tot sol.

Els dos casos es **REPORTEN amb els dos noms al davant** i no es lliguen. Qui els hagi de
resoldre —la criba fina— ho farà al FULL, que és on viu el destí, i no endevinant aquí.

🔒 **LA SOBIRANIA MANA, I ES MIRA PRIMER.** Un POM amb `separat_de_global` no el toca ningú —
és el pany del 22/08. Un POM que ja té `pom_global` cap a un ALTRE global **es REPORTA i no es
mou**: moure'l seria exactament la contaminació que el TRAM A va curar.

🔑 **NOMÉS ELS VIUS.** L'arxiu (`actiu=False`, llei S44) es compta i es deixa com és: un POM
jubilat no necessita cap canònic i re-lligar-lo reescriuria història.

⚠️ Aquesta comanda **exigeix que S2 ja hagi escrit al mateix schema** (la FK es resol dins del
schema del tenant). En dry-run, si els globals encara no hi són, ho diu i segueix comptant;
escrivint, ATURA.

    manage.py lliga_fhort_al_sistema --schema fhort                # DRY-RUN
    manage.py lliga_fhort_al_sistema --schema fhort --no-dry-run   # escriu
"""
import re
import unicodedata

from django.core.management.base import CommandError

from fhort.pom.models import POMGlobal, POMMaster
from fhort.pom.sembra_v5 import corpus
from fhort.pom.sembra_v5.base import ComandaV5


#: 🚨 ELS DOS APARELLAMENTS DEL FULL QUE NO SÓN LA MATEIXA MESURA. Mesurat el 23/08 i
#: confirmat per Agus: `N` («Motive placement») i `N5` («Reflective band height») són coses
#: diferents, i `RW` («Welt height») i `R7` («Pocket topstitch») també. Amb `--el-cataleg-mana`
#: el full és autoritat per a TOTS els altres aparellaments; aquests dos queden **sempre fora**
#: i es reporten. La llista és curta a posta: si algun dia n'hi ha un tercer, es MESURA i
#: s'afegeix aquí, no es descobreix a la fitxa d'un client.
EXCEPCIONS_DEL_MAPA = {'N': 'N5', 'RW': 'R7'}


def normalitza(nom):
    """El nom, reduït al que dues fonts han de compartir per ser el MATEIX nom.

    Sense accents, sense majúscules, sense puntuació i amb els espais col·lapsats: «BACK
    NECKLINE WIDTH» i «Back neckline width» són el mateix nom, i «Pocket mouth width» i
    «Pocket opening width» no ho són. La normalització **no interpreta sinònims a posta**: el
    dia que dos noms hagin de voler dir el mateix, això es declara al FULL i no aquí.
    """
    net = unicodedata.normalize('NFKD', nom or '').encode('ascii', 'ignore').decode()
    net = net.lower().replace('&', ' and ')
    return ' '.join(re.sub(r'[^a-z0-9]+', ' ', net).split())


class Command(ComandaV5):
    help = 'S3 · lliga els POMs vius del tenant al `POMGlobal` de sistema del seu codi v5.'
    PAS = 'S3 · lligam al sistema'

    def arguments_propis(self, parser):
        parser.add_argument('--schema', required=True,
                            help='Schema del tenant (sense default: pany P2 del 22/08).')
        parser.add_argument('--el-cataleg-mana', action='store_true',
                            help='El mapa del r2 és autoritat: el nom divergent no barra el '
                                 f'lligam (excepte {sorted(EXCEPCIONS_DEL_MAPA)}).')

    def corre(self, opts):
        mapa = corpus.mapa_brownie(self.corpus['alies'])
        noms_v5 = {p['codi']: p['nom_en'] for p in self.corpus['poms']}
        schema = opts['schema']

        lligats = ja_lligats = sobirans = divergents = sense_codi = sense_global = 0
        nom_divergent_mapa = nom_divergent_propi = per_codi_propi = 0
        per_autoritat = excepcio_mesurada = 0
        desti_de = {}

        with self.transacciona(schema):
            vius = list(POMMaster.objects.filter(actiu=True).order_by('codi_client'))
            self.guarda('POMs VIUS al tenant', len(vius))
            self.guarda('POMs d\'ARXIU (actiu=False, no tocats)',
                        POMMaster.objects.filter(actiu=False).count())
            globals_per_codi = {g.codi: g for g in POMGlobal.objects.all()}

            for p in vius:
                codi = p.codi_client
                # (1) LA CORRESPONDÈNCIA DE CODI — el full primer, el codi propi després.
                sistema, via = mapa.get(codi), 'full'
                if sistema is None and codi in noms_v5:
                    sistema, via = codi, 'codi propi'
                if sistema is None:
                    sense_codi += 1
                    self.excepcio(f'{codi!r} ({p.nom_client}): cap codi del v5 li correspon '
                                  '(ni pel full ni pel seu propi codi). NO es lliga.')
                    continue

                # (2) EL NOM — i és la meitat que atura els paranys mesurats el 23/08.
                if (via == 'full' and EXCEPCIONS_DEL_MAPA.get(codi) == sistema):
                    excepcio_mesurada += 1
                    self.excepcio(
                        f'⛔ {codi!r} → {sistema!r}: EXCEPCIÓ MESURADA — el full els aparella '
                        f'però no són la mateixa mesura (tenant {p.nom_client!r} vs v5 '
                        f'{noms_v5[sistema]!r}). Fora sempre, també amb --el-cataleg-mana.')
                    continue
                divergeix = normalitza(p.nom_client) != normalitza(noms_v5[sistema])
                # ⚖️ El catàleg mana: es compta, es diu… i **se segueix avall a lligar**. El
                # `continue` de sota és només per als que NO es lliguen.
                if divergeix and via == 'full' and opts['el_cataleg_mana']:
                    per_autoritat += 1
                    self.excepcio(
                        f'⚖️ {codi!r} → {sistema!r}: el nom divergeix ({p.nom_client!r} vs '
                        f'{noms_v5[sistema]!r}) i el CATÀLEG MANA — es lliga.')
                elif divergeix:
                    if via == 'full':
                        nom_divergent_mapa += 1
                        self.excepcio(
                            f'🚨 {codi!r} → {sistema!r}: el full els aparella però es diuen '
                            f'coses diferents (tenant {p.nom_client!r} vs v5 '
                            f'{noms_v5[sistema]!r}). NO es lliga: el codi sol no basta.')
                    else:
                        nom_divergent_propi += 1
                        self.excepcio(
                            f'🚨 {codi!r}: el v5 REUTILITZA aquest codi per a una altra mesura '
                            f'(tenant {p.nom_client!r} vs v5 {noms_v5[sistema]!r}). NO es '
                            'lliga: seria el canònic equivocat.')
                    continue

                desti_de.setdefault(sistema, []).append(codi)
                if via == 'codi propi':
                    per_codi_propi += 1
                    self.excepcio(f'🚩 {codi!r}: el full no el mapa, però el codi I el nom '
                                  f'coincideixen amb el v5 ({noms_v5[sistema]!r}) — es lliga '
                                  'per les dues coincidències.')

                if p.separat_de_global:
                    sobirans += 1
                    self.excepcio(f'🔒 {codi!r}: SOBIRÀ (separat_de_global='
                                  f'{p.separat_de_global!r}) — no es toca mai.')
                    continue

                gl = globals_per_codi.get(sistema)
                if gl is None:
                    sense_global += 1
                    self.excepcio(f'{codi!r} → {sistema!r}: el `POMGlobal` no és a `{schema}` '
                                  '(S2 encara no hi ha escrit).')
                    continue

                if p.pom_global_id == gl.id:
                    ja_lligats += 1
                elif p.pom_global_id is None:
                    p.pom_global = gl
                    p.save(update_fields=['pom_global'])
                    lligats += 1
                else:
                    divergents += 1
                    self.excepcio(
                        f'🚨 {codi!r}: ja apunta a {p.pom_global.codi!r} i el r2 diu '
                        f'{sistema!r} — es REPORTA i NO es mou (contaminació del TRAM A).')

            self.guarda('lligams NOUS', lligats)
            self.guarda('lligams ja fets (idempotència)', ja_lligats)
            self.guarda('…dels quals, lligats pel CODI PROPI + nom', per_codi_propi)
            self.guarda('POMs sobirans respectats', sobirans)
            self.guarda('POMs amb lligam divergent (reportats, no moguts)', divergents)
            self.guarda('POMs sense cap codi del v5', sense_codi)
            self.guarda('POMs lligats per AUTORITAT DEL CATÀLEG (nom divergent)', per_autoritat)
            self.guarda('excepcions mesurades fora sempre (N, RW)', excepcio_mesurada)
            self.guarda('POMs que el FULL mapa però amb NOM divergent', nom_divergent_mapa)
            self.guarda('POMs amb codi HOMÒNIM i nom divergent', nom_divergent_propi)
            self.guarda('POMs amb el global absent al schema', sense_global)

            compartits = {s: c for s, c in desti_de.items() if len(c) > 1}
            self.guarda('globals amb MÉS D\'UN POM del tenant', len(compartits))
            for s, c in sorted(compartits.items()):
                self.excepcio(f'global {s!r} el reclamen {len(c)} POMs del tenant: {c}')

            if sense_global and not self.dry:
                raise CommandError(
                    f'{sense_global} POMs sense el seu `POMGlobal` a `{schema}`: corre abans '
                    f'`sembra_cataleg_sistema --schema {schema} --no-dry-run`.')

        self.diu(f'   lligats {lligats} (codi propi {per_codi_propi} · per autoritat '
                 f'{per_autoritat}) · ja lligats {ja_lligats} · sobirans {sobirans} · '
                 f'lligam divergent {divergents} · sense codi {sense_codi} · nom divergent '
                 f'{nom_divergent_mapa} (full) + {nom_divergent_propi} (homònim) · '
                 f'excepcions {excepcio_mesurada} · global absent {sense_global}')
