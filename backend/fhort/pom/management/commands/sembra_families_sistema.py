"""S1 · LES 14 FAMÍLIES DEL SISTEMA — el catàleg de la casa, a `public`.

El v5 tanca la taxonomia en **14 famílies** amb lletra pròpia, i les sembra com a catàleg de
SISTEMA: viuen a `public`, bilingües, amb l'ordre del full.

🔑 **LA FAMÍLIA ÉS DEL TENANT; el sistema només la PROPOSA.** Per això aquesta comanda **no
toca cap schema de tenant** —no té `--schema` i no en pot rebre cap—: qui remapa els POMs de
`fhort` és S5, i el que fa és una decisió del tenant, no una còpia d'aquí. Les 15 famílies de
sector que ja viuen a `public` (vocabulari anglès, 0 POMs) es reporten i **no es toquen**: el
brief autoritza exactament una supressió a tot el tram, i és la de les `CAT-*` buides (S5).

🔒 **EL PRINCIPI DELS PANYS** (tren del 22/08): es crea el que falta; el que ja existeix amb un
text diferent es **REPORTA i no es toca**, llevat de `--overwrite-from-xlsx`, que ho fa constar.

⚠️ **`POMCategory` no té `nom_es`.** El brief ja ho preveu («/ES si el model en té»): les
famílies van en CA i EN, i el castellà no s'inventa ni s'aboca enlloc.

    manage.py sembra_families_sistema                # DRY-RUN
    manage.py sembra_families_sistema --no-dry-run   # escriu a `public`
"""
from fhort.pom.models import POMCategory
from fhort.pom.sembra_v5.base import ComandaV5

#: Els camps que la sembra governa. `nom_es` no hi és perquè el model no en té (v. docstring).
CAMPS = ('nom_ca', 'nom_en', 'display_order')


class Command(ComandaV5):
    help = 'S1 · sembra les 14 famílies del v5 com a catàleg de SISTEMA (schema `public`).'
    PAS = 'S1 · famílies del sistema'
    ESPERAT = {'famílies del corpus': 14}

    def arguments_propis(self, parser):
        parser.add_argument('--overwrite-from-xlsx', action='store_true',
                            help='Reescriu el text de les famílies que ja existeixen.')

    def corre(self, opts):
        families = self.corpus['families']
        self.guarda('famílies del corpus', len(families))

        creades, iguals, diferents, reescrites = 0, 0, 0, 0
        with self.transacciona('public'):
            for f in families:
                volgut = {'nom_ca': f['nom_ca'], 'nom_en': f['nom_en'],
                          'display_order': int(f['ordre'])}
                cat = POMCategory.objects.filter(codi=f['codi']).first()
                if cat is None:
                    POMCategory.objects.create(codi=f['codi'], actiu=True, **volgut)
                    creades += 1
                    continue
                delta = {c: (getattr(cat, c), volgut[c]) for c in CAMPS
                         if getattr(cat, c) != volgut[c]}
                if not delta:
                    iguals += 1
                    continue
                if opts['overwrite_from_xlsx']:
                    for c, (_vell, nou) in delta.items():
                        setattr(cat, c, nou)
                    cat.save(update_fields=list(delta))
                    reescrites += 1
                    self.excepcio(f'🔓 {f["codi"]}: REESCRITA — ' + ' · '.join(
                        f'{c}: {v!r} → {n!r}' for c, (v, n) in delta.items()))
                else:
                    diferents += 1
                    self.excepcio(f'🔒 {f["codi"]}: existeix amb un altre text i NO es toca — '
                                  + ' · '.join(f'{c}: BD {v!r} vs r2 {n!r}'
                                               for c, (v, n) in delta.items()))

            self.guarda('famílies creades', creades)
            self.guarda('famílies ja iguals (idempotència)', iguals)
            self.guarda('famílies amb text divergent', diferents)
            self.guarda('famílies reescrites', reescrites)

            # El terreny que hi ha al voltant: es diu, no es toca.
            alienes = (POMCategory.objects.exclude(codi__in=[f['codi'] for f in families])
                       .order_by('codi'))
            self.guarda('famílies de `public` alienes al v5', alienes.count())
            for c in alienes:
                if c.poms.exists():
                    self.excepcio(f'família aliena {c.codi!r} amb {c.poms.count()} POMs '
                                  '— NO es toca (la supressió del tram és la de S5)')

        self.diu(f'   creades {creades} · iguals {iguals} · divergents {diferents} '
                 f'· reescrites {reescrites}')
        self.diu(f'   alienes a `public` (no tocades): {alienes.count()} '
                 f'{sorted(alienes.values_list("codi", flat=True))}')
        self.diu('   ⚠️  `POMCategory` no té `nom_es`: les famílies van en CA i EN.')
