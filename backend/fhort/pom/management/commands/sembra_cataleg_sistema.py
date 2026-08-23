"""S2 · ELS 165 POMs DEL v5 — el catàleg GLOBAL de sistema.

Els 165 codis del full `CATALEG` entren com a `POMGlobal`: el vocabulari canònic de la casa,
amb el «com es mesura» sencer (punt A, punt B, referència, scope, zona, unitat) i les dues
toleràncies. L'estat surt de la columna `ESTAT SEMBRA` — 161 ACTIU i 4 INACTIU.

🔑 **`--schema` ÉS OBLIGATORI I ES POT REPETIR, i no és un caprici.** `POMGlobal` viu a
`public` **i** es replica a cada tenant (`settings.py:53-55`), perquè la FK
`POMMaster.pom_global` es resol DINS del schema del tenant. Sembrar només `public` deixaria S3
sense res a què lligar; per això el destí es declara i mai es dedueix:

    manage.py sembra_cataleg_sistema --schema public --schema fhort

🔒 **EL PRINCIPI DELS PANYS** (tren del 22/08): es crea el que falta i **no es reescriu res**
del que ja hi és. Un camp local que difereix del r2 es REPORTA i es deixa com està; només
`--overwrite-from-xlsx` el toca, i llavors la reescriptura consta al report. És literal del
brief, i val per a TOTS els camps —també per a `notes`—: aquest catàleg el poden haver editat
mans humanes des de la sembra anterior.

⚖️ **LLEI DE MOTOR @girth.** Els 4 INACTIU són els contorns (`A1` chest girth, `A2` underbust,
`C2` hip, `D11` leg opening): entren al catàleg com a vocabulari i **sense cap regla de
graduació**. Aquesta comanda no crea ni toca cap `GradingRule` — cap del tram no ho fa.

✅ **LES QUATRE COLUMNES DEL FORAT JA S'ESCRIUEN** (`Pos.` → `display_order`, `Règim`,
`Ancoratge`, `Capa` → `capa_defecte`), gràcies al pre-tren `pom/0081` que Agus va autoritzar el
23/08. Del forat només hi queden `FONT DEF.` i `Origen` —provenença del document, no dada del
POM—, que es reporten a cada correguda i no s'aboquen enlloc.

    manage.py sembra_cataleg_sistema --schema public --schema fhort                # DRY-RUN
    manage.py sembra_cataleg_sistema --schema public --schema fhort --no-dry-run   # escriu
"""
from fhort.pom.models import POMGlobal
from fhort.pom.sembra_v5 import corpus
from fhort.pom.sembra_v5.base import ComandaV5

#: `camp del model` → `clau del corpus`. L'ORDRE és el de la fitxa i entra al report.
CAMPS = (
    ('nom_en', 'nom_en'), ('nom_ca', 'nom_ca'), ('nom_es', 'nom_es'),
    ('categoria', 'familia'), ('unitat', 'unitat'), ('actiu', 'actiu'),
    ('start_point', 'start_point'), ('end_point', 'end_point'),
    ('reference_point', 'reference_point'), ('scope', 'scope'),
    ('body_section', 'body_section'),
    ('tol_prod_cm', 'tol_prod_cm'), ('tol_samp_cm', 'tol_samp_cm'),
    ('notes', 'nota'),
    # Les quatre del pre-tren `pom/0081` (23/08). `Capa` va a `capa_defecte`: el catàleg
    # PROPOSA la capa, no la decideix (la decideix la pertinença).
    ('display_order', 'posicio'), ('regim', 'regim'), ('ancoratge', 'ancoratge'),
    ('capa_defecte', 'capa'),
)


class Command(ComandaV5):
    help = 'S2 · sembra els 165 POMs del v5 com a `POMGlobal` (catàleg de sistema).'
    PAS = 'S2 · catàleg de sistema'
    ESPERAT = {'POMs del corpus': 165, 'POMs ACTIU': 161, 'POMs INACTIU': 4}

    def arguments_propis(self, parser):
        parser.add_argument('--schema', action='append', default=[], required=True,
                            help='Schema destí. Es pot repetir (p. ex. public i fhort).')
        parser.add_argument('--overwrite-from-xlsx', action='store_true',
                            help='Reescriu els camps que difereixen del r2.')

    def corre(self, opts):
        poms = self.corpus['poms']
        self.guarda('POMs del corpus', len(poms))
        self.guarda('POMs ACTIU', sum(1 for p in poms if p['actiu']))
        self.guarda('POMs INACTIU', sum(1 for p in poms if not p['actiu']))

        for schema in opts['schema']:
            self._un_schema(schema, poms, opts['overwrite_from_xlsx'])

        self.diu('\n   🚨 columnes del r2 SENSE CAMP al model — no sembrades, no inventades:')
        for col, per_que in corpus.COLUMNES_SENSE_DESTI.items():
            self.diu(f'      · {col}: {per_que}')

    def _un_schema(self, schema, poms, overwrite):
        creats = iguals = divergents = reescrits = 0
        self.diu(f'\n   ── schema `{schema}` ──')
        with self.transacciona(schema):
            for p in poms:
                volgut = {camp: p[clau] for camp, clau in CAMPS}
                volgut['notes'] = volgut['notes'] or ''
                pg = POMGlobal.objects.filter(codi=p['codi']).first()
                if pg is None:
                    POMGlobal.objects.create(codi=p['codi'], **volgut)
                    creats += 1
                    continue
                delta = {c: (getattr(pg, c), v) for c, v in volgut.items()
                         if getattr(pg, c) != v}
                if not delta:
                    iguals += 1
                    continue
                if overwrite:
                    for c, (_vell, nou) in delta.items():
                        setattr(pg, c, nou)
                    pg.save(update_fields=list(delta))
                    reescrits += 1
                    self.excepcio(f'🔓 [{schema}] {p["codi"]}: REESCRIT — '
                                  + ' · '.join(f'{c}' for c in delta))
                else:
                    divergents += 1
                    self.excepcio(f'🔒 [{schema}] {p["codi"]}: difereix del r2 i NO es toca — '
                                  + ' · '.join(f'{c}: BD {v!r} vs r2 {n!r}'
                                               for c, (v, n) in delta.items()))

            self.guarda(f'[{schema}] POMGlobal creats', creats)
            self.guarda(f'[{schema}] POMGlobal ja iguals (idempotència)', iguals)
            self.guarda(f'[{schema}] POMGlobal divergents del r2', divergents)
            self.guarda(f'[{schema}] POMGlobal reescrits', reescrits)
            total = POMGlobal.objects.count()
            self.guarda(f'[{schema}] POMGlobal al schema (tots, també els de fora del v5)',
                        total)
            fora = POMGlobal.objects.exclude(
                codi__in=[p['codi'] for p in poms]).count()
            self.guarda(f'[{schema}] POMGlobal FORA del v5 (no tocats)', fora)

        self.diu(f'      creats {creats} · iguals {iguals} · divergents {divergents} '
                 f'· reescrits {reescrits} · fora del v5 {fora}')
