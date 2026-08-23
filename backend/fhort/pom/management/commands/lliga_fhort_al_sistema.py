"""S3 · EL LLIGAM — cada POM VIU del tenant, al seu global de sistema.

Fins avui els 144 POMs de `fhort` són **orfes**: `pom_global = NULL` a tots (cens del 22/08).
Aquest pas els lliga al `POMGlobal` del v5 que els correspon, i el mapa surt del r2:

    codi del POM al tenant  ──(full ALIES_BROWNIE)──▶  codi de sistema  ──▶  POMGlobal.codi

🚨 **I NOMÉS AQUEST MAPA. «EL CODI JA ÉS UN CODI v5» ÉS UN PARANY, I ESTÀ MESURAT.** Els dos
vocabularis fan servir les mateixes lletres per a mesures DIFERENTS: el `E2` del tenant és
*Across front width* i el `E2` del v5 és *Shoulder forward*; el `M` del tenant és *Leg opening*
i el del v5, *Neck width*. Dels 16 POMs vius amb un codi que el v5 també fa servir, **cap dels
16 vol dir el mateix** (mesurat el 23/08, i és per això que el r2 mapa `EK → M` i `E4 → E2`).
Lligar-los per coincidència de lletra hauria posat 16 POMs sota el canònic equivocat, en
silenci i amb totes les guardes en verd. Un POM que el mapa no cobreix **no s'endevina**: es
reporta i es queda orfe.

🔒 **LA SOBIRANIA MANA, I ES MIRA PRIMER.** Un POM amb `separat_de_global` no el toca ningú —
és el pany del 22/08, i vol dir que el tenant ha decidit que aquell POM ja no parla amb el
canònic. Un POM que ja té `pom_global` cap a un ALTRE global **es REPORTA i no es mou**: moure'l
seria exactament la contaminació que el TRAM A va curar.

🔑 **NOMÉS ELS VIUS.** L'arxiu (`actiu=False`, llei S44) es compta i es deixa com és: un POM
jubilat no necessita cap canònic i re-lligar-lo reescriuria història.

⚠️ Aquesta comanda **exigeix que S2 ja hagi escrit al mateix schema** (la FK es resol dins del
schema del tenant). En dry-run, si els globals encara no hi són, ho diu i segueix comptant;
escrivint, ATURA.

    manage.py lliga_fhort_al_sistema --schema fhort                # DRY-RUN
    manage.py lliga_fhort_al_sistema --schema fhort --no-dry-run   # escriu
"""
from django.core.management.base import CommandError

from fhort.pom.models import POMGlobal, POMMaster
from fhort.pom.sembra_v5 import corpus
from fhort.pom.sembra_v5.base import ComandaV5


class Command(ComandaV5):
    help = 'S3 · lliga els POMs vius del tenant al `POMGlobal` de sistema del seu codi v5.'
    PAS = 'S3 · lligam al sistema'

    def arguments_propis(self, parser):
        parser.add_argument('--schema', required=True,
                            help='Schema del tenant (sense default: pany P2 del 22/08).')

    def corre(self, opts):
        mapa = corpus.mapa_brownie(self.corpus['alies'])
        noms_v5 = {p['codi']: p['nom_en'] for p in self.corpus['poms']}
        schema = opts['schema']

        lligats = ja_lligats = sobirans = divergents = sense_desti = sense_global = 0
        homonims = 0
        desti_de = {}

        with self.transacciona(schema):
            vius = list(POMMaster.objects.filter(actiu=True).order_by('codi_client'))
            self.guarda('POMs VIUS al tenant', len(vius))
            self.guarda('POMs d\'ARXIU (actiu=False, no tocats)',
                        POMMaster.objects.filter(actiu=False).count())
            globals_per_codi = {g.codi: g for g in POMGlobal.objects.all()}

            for p in vius:
                codi = p.codi_client
                sistema = mapa.get(codi)
                if sistema is None:
                    sense_desti += 1
                    if codi in noms_v5:
                        homonims += 1
                        # El nom es MESURA abans de dir que difereix: si algun dia coincideix,
                        # el cas deixa de ser un parany i passa a ser un candidat — i llavors
                        # el que toca és afegir-lo al full, no endevinar-lo aquí.
                        mateix = (p.nom_client.strip().lower()
                                  == noms_v5[codi].strip().lower())
                        if mateix:
                            self.excepcio(
                                f'🚩 {codi!r}: el full no el mapa, però el v5 té aquest codi '
                                f'amb el MATEIX nom ({p.nom_client!r}) — candidat a lligar. '
                                'NO es lliga: el destí el declara el full.')
                        else:
                            self.excepcio(
                                f'🚨 {codi!r}: el full no el mapa, i el v5 REUTILITZA aquest '
                                f'codi per a una altra mesura (tenant {p.nom_client!r} vs v5 '
                                f'{noms_v5[codi]!r}). NO es lliga: seria el canònic '
                                'equivocat.')
                    else:
                        self.excepcio(f'{codi!r} ({p.nom_client}): cap codi Brownie al r2 el '
                                      'mapa. NO es lliga.')
                    continue
                desti_de.setdefault(sistema, []).append(codi)

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
            self.guarda('POMs sobirans respectats', sobirans)
            self.guarda('POMs amb lligam divergent (reportats, no moguts)', divergents)
            self.guarda('POMs sense destí al v5', sense_desti)
            self.guarda('…dels quals, codi HOMÒNIM d\'un codi v5 amb una altra mesura',
                        homonims)
            self.guarda('POMs amb el global absent al schema', sense_global)

            compartits = {s: c for s, c in desti_de.items() if len(c) > 1}
            self.guarda('globals amb MÉS D\'UN POM del tenant', len(compartits))
            for s, c in sorted(compartits.items()):
                self.excepcio(f'global {s!r} el reclamen {len(c)} POMs del tenant: {c}')

            if sense_global and not self.dry:
                raise CommandError(
                    f'{sense_global} POMs sense el seu `POMGlobal` a `{schema}`: corre abans '
                    f'`sembra_cataleg_sistema --schema {schema} --no-dry-run`.')

        self.diu(f'   lligats {lligats} · ja lligats {ja_lligats} · sobirans {sobirans} '
                 f'· divergents {divergents} · sense destí {sense_desti} '
                 f'(homònims {homonims}) · global absent {sense_global}')
