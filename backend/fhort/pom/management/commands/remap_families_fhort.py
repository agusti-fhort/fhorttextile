"""S5 · EL REMAPATGE — els POMs vius del tenant, a les 14 famílies del v5.

Cada POM VIU lligat al catàleg de sistema (S3) rep la família que el r2 li dona a la columna
`Fam.`. I la rep **per aquest camí i no per cap altre**.

🚨 **EL «MAPA 23→14 DE LLETRES» NO EXISTEIX COM A FUNCIÓ, I EL FULL HO DIU.** La columna
«Prefixos de codi que hi viuen» del full FAMILIES reparteix el prefix `I` entre TRES famílies
(`I` màniga, `F` llargs del cos, `T` tirants) i `U` entre dues. Un mapa lletra→lletra hauria
d'escollir, i escollir seria endevinar. La família d'un POM és la de la seva FILA al r2 —dada
per POM, no per lletra—, i per això aquest pas depèn de S3: sense lligam no hi ha fila.

🔑 **L'ARXIU NO ES REESCRIU.** Només `actiu=True`. Un POM jubilat (llei S44) conserva la
família que tenia: la seva família és la del dia que va morir, i reescriure-la falsejaria
l'històric que la pantalla d'inactius ensenya.

🔒 **LES 14 FAMÍLIES AL TENANT, AMB EL PRINCIPI DELS PANYS.** Es crea la que falta; la que ja
existeix amb el mateix codi **conserva el seu text** i la diferència es reporta —les lletres
del v5 ja existeixen a `fhort` amb els rètols de la v4, i reescriure'ls sense dir-ho seria
exactament el que el tren de panys va tancar—. `--overwrite-from-xlsx` els posa al dia i ho fa
constar.

☠️ **L'ÚNICA SUPRESSIÓ DE TOT EL TRAM: les `CAT-*` BUIDES.** I amb guarda, perquè
`POMMaster.categoria` és **`SET_NULL`**: esborrar una categoria amb POMs a dins no peta —els
deixa orfes en silenci—. Per això la candidata a esborrar és **la que té 0 POMs mesurats en el
moment real**, mai la que la llista diu que hauria d'estar buida. Una `CAT-*` amb POMs
(`CAT-UB` amb l'arxiu, p. ex.) es reporta i **es queda**: mor amb l'arxiu, no aquí.

    manage.py remap_families_fhort --schema fhort                # DRY-RUN
    manage.py remap_families_fhort --schema fhort --no-dry-run   # escriu
"""
from fhort.pom.models import POMCategory, POMMaster
from fhort.pom.sembra_v5.base import ComandaV5

PREFIX_MORT = 'CAT-'


class Command(ComandaV5):
    help = 'S5 · remapa els POMs vius del tenant a les 14 famílies del v5.'
    PAS = 'S5 · remapatge de famílies'
    #: Les xifres del brief. Són de PROD; a staging divergiran i el report ho dirà.
    ESPERAT = {'CAT-* buides esborrades': 12}

    def arguments_propis(self, parser):
        parser.add_argument('--schema', required=True,
                            help='Schema del tenant (sense default: pany P2 del 22/08).')
        parser.add_argument('--overwrite-from-xlsx', action='store_true',
                            help='Posa al dia el text de les 14 famílies del tenant.')

    def corre(self, opts):
        families = {f['codi']: f for f in self.corpus['families']}
        fam_del_pom = {p['codi']: p['familia'] for p in self.corpus['poms']}

        moguts = iguals = sense_fila = 0
        with self.transacciona(opts['schema']):
            # ── Les 14 al tenant ──────────────────────────────────────────────────────────
            cats, creades, divergents, reescrites = {}, 0, 0, 0
            for codi, f in families.items():
                volgut = {'nom_ca': f['nom_ca'], 'nom_en': f['nom_en'],
                          'display_order': int(f['ordre'])}
                cat = POMCategory.objects.filter(codi=codi).first()
                if cat is None:
                    cat = POMCategory.objects.create(codi=codi, actiu=True, **volgut)
                    creades += 1
                else:
                    delta = {c: (getattr(cat, c), v) for c, v in volgut.items()
                             if getattr(cat, c) != v}
                    if delta and opts['overwrite_from_xlsx']:
                        for c, (_v, n) in delta.items():
                            setattr(cat, c, n)
                        cat.save(update_fields=list(delta))
                        reescrites += 1
                        self.excepcio(f'🔓 família {codi!r}: REESCRITA — {list(delta)}')
                    elif delta:
                        divergents += 1
                        self.excepcio(f'🔒 família {codi!r}: el tenant la té amb un altre text '
                                      'i NO es toca — ' + ' · '.join(
                                          f'{c}: BD {v!r} vs r2 {n!r}'
                                          for c, (v, n) in delta.items()))
                cats[codi] = cat
            self.guarda('famílies del v5 creades al tenant', creades)
            self.guarda('famílies del v5 amb text divergent (no tocades)', divergents)
            self.guarda('famílies del v5 reescrites', reescrites)

            # ── Els POMs vius ─────────────────────────────────────────────────────────────
            vius = (POMMaster.objects.filter(actiu=True)
                    .select_related('pom_global', 'categoria').order_by('codi_client'))
            self.guarda('POMs VIUS al tenant', vius.count())
            for p in vius:
                codi_v5 = p.pom_global.codi if p.pom_global_id else None
                fam = fam_del_pom.get(codi_v5) if codi_v5 else None
                if fam is None:
                    sense_fila += 1
                    self.excepcio(f'{p.codi_client!r}: sense fila al r2 (no lligat per S3) — '
                                  f'conserva la família '
                                  f'{p.categoria.codi if p.categoria_id else None!r}.')
                    continue
                if p.categoria_id == cats[fam].id:
                    iguals += 1
                    continue
                p.categoria = cats[fam]
                p.save(update_fields=['categoria'])
                moguts += 1
            self.guarda('POMs remapats', moguts)
            self.guarda('POMs ja a la seva família (idempotència)', iguals)
            self.guarda('POMs vius sense fila al r2 (conserven família)', sense_fila)
            self.guarda("POMs d'ARXIU (no tocats)",
                        POMMaster.objects.filter(actiu=False).count())

            # ── L'única supressió ─────────────────────────────────────────────────────────
            mortes = POMCategory.objects.filter(codi__startswith=PREFIX_MORT).order_by('codi')
            buides = [c for c in mortes if not c.poms.exists()]
            amb_poms = [c for c in mortes if c.poms.exists()]
            self.guarda(f'{PREFIX_MORT}* al tenant', mortes.count())
            self.guarda('CAT-* buides esborrades', len(buides))
            for c in amb_poms:
                self.excepcio(f'☠️ {c.codi!r} té {c.poms.count()} POMs: NO s\'esborra '
                              '(`SET_NULL` els deixaria orfes en silenci).')
            for c in buides:
                c.delete()

            # El que el remapatge deixa buit i el brief NO autoritza a esborrar.
            orfes = [c.codi for c in POMCategory.objects.order_by('codi')
                     if not c.poms.exists() and c.codi not in families
                     and not c.codi.startswith(PREFIX_MORT)]
            self.guarda('famílies velles que queden BUIDES (no esborrades)', len(orfes))
            if orfes:
                self.excepcio(f'famílies buides després del remapatge, NO esborrades (el brief '
                              f'només autoritza les {PREFIX_MORT}*): {orfes}')

        self.diu(f'   remapats {moguts} · ja hi eren {iguals} · sense fila {sense_fila} '
                 f'· famílies creades {creades} · {PREFIX_MORT}* esborrades {len(buides)}')
