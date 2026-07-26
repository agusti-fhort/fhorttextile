"""LLEI BEACH (2026-07-26) — una talla que el sistema no coneix no tomba tot l'import.

Incident PROD: import d'una fitxa sobre un model NEWBORN (sistema que acaba a 18/24). El
document portava a més la columna 24M-36M (una talla BABY, canònic 24/36). El guard
`talles_desconegudes` bloquejava el pas 5 sencer amb un 422.

Llei:
  · columna NO-base fora del sistema  → es DESCARTA (l'import escriu les conegudes),
    s'apunta a `descartades` i NO va a `bloqueigs`.
  · talla BASE fora del sistema        → BLOQUEIG (corrupció real): va a `bloqueigs` amb
    tipus 'talles_desconegudes' i la derivació retorna [].

Es prova `derive_rules_from_fitxa` directament (pur, però toca ORM per SizeDefinition/POMMaster),
que és l'origen ÚNIC del veredicte que després consumeix `import_session_confirmar_view`.
"""
from fhort.models_app.tests_sembra_grading import _BaseSembraTest
from fhort.pom.grading_utils import derive_rules_from_fitxa


class BeachColumnesDescartadesTest(_BaseSembraTest):
    PREFIX = 'BEACH'

    def setUp(self):
        super().setUp()
        # Sistema NEWBORN-com: acaba a 18/24; 24/36 (=24M-36M) NO hi és.
        self.ss = self._size_system(
            'NEWBORN', talles=('00/01', '01/03', '03/06', '06/09', '09/12', '12/18', '18/24'))
        self.base = '00/01'
        # Dues POMs amb valors LINEAR nets sobre el run conegut del document.
        self.p1 = self._pom('AMPLE')
        self.p2 = self._pom('LLARG')

    def _valors(self, extra_col=None):
        """Valors {pom_id: {etiqueta: cm}} amb un delta uniforme. `extra_col`=(etiqueta, cm)
        afegeix una columna extra a TOTES les POMs (simula la columna d'un altre sistema)."""
        run = ['00/01', '01/03', '03/06']
        v = {}
        for pid, base_cm in ((self.p1.id, 20.0), (self.p2.id, 30.0)):
            fila = {et: base_cm + i * 2.0 for i, et in enumerate(run)}
            if extra_col:
                fila[extra_col[0]] = extra_col[1]
            v[pid] = fila
        return v

    # ── NO-base desconeguda → DESCARTA i continua ──────────────────────────────────
    def test_columna_no_base_fora_del_sistema_es_descarta_i_deriva(self):
        avisos, bloqueigs, descartades = [], [], []
        specs = derive_rules_from_fitxa(
            run_document=['00/01', '01/03', '03/06', '24M-36M'],
            base_size=self.base,
            valors=self._valors(extra_col=('24M-36M', 99.0)),
            confirmed_pom_ids=[self.p1.id, self.p2.id],
            size_system=self.ss, avisos=avisos, bloqueigs=bloqueigs, descartades=descartades)
        # La columna d'un altre sistema es descarta, NO bloqueja.
        self.assertEqual(descartades, ['24M-36M'])
        self.assertEqual(bloqueigs, [])
        # I la derivació segueix: s'han derivat regles per les dues POMs del run conegut.
        self.assertEqual(len(specs), 2)

    def test_descartades_es_acumula_sense_esborrar_res(self):
        """L'out-param `descartades` és append-only, com `avisos`/`bloqueigs`."""
        descartades = ['PREVI']
        derive_rules_from_fitxa(
            run_document=['00/01', '01/03', '03/06', '24M-36M'],
            base_size=self.base, valors=self._valors(extra_col=('24M-36M', 99.0)),
            confirmed_pom_ids=[self.p1.id], size_system=self.ss,
            avisos=[], bloqueigs=[], descartades=descartades)
        self.assertEqual(descartades, ['PREVI', '24M-36M'])

    # ── BASE desconeguda → BLOQUEIG intacte ────────────────────────────────────────
    def test_talla_base_fora_del_sistema_bloqueja(self):
        avisos, bloqueigs, descartades = [], [], []
        specs = derive_rules_from_fitxa(
            run_document=['24M-36M', '01/03', '03/06'],
            base_size='24M-36M',   # base que el sistema NO coneix → corrupció real
            valors={self.p1.id: {'24M-36M': 20.0, '01/03': 22.0, '03/06': 24.0}},
            confirmed_pom_ids=[self.p1.id],
            size_system=self.ss, avisos=avisos, bloqueigs=bloqueigs, descartades=descartades)
        self.assertEqual(specs, [])
        self.assertTrue(any(b['tipus'] == 'talles_desconegudes' for b in bloqueigs))
        # La base bloqueja; NO s'ha registrat com a descartada (no s'importa res).
        self.assertEqual(descartades, [])

    # ── Sense desconegudes → cap descartada, deriva normal ─────────────────────────
    def test_sense_columnes_estranyes_no_descarta_res(self):
        avisos, bloqueigs, descartades = [], [], []
        specs = derive_rules_from_fitxa(
            run_document=['00/01', '01/03', '03/06'],
            base_size=self.base, valors=self._valors(),
            confirmed_pom_ids=[self.p1.id, self.p2.id],
            size_system=self.ss, avisos=avisos, bloqueigs=bloqueigs, descartades=descartades)
        self.assertEqual(descartades, [])
        self.assertEqual(bloqueigs, [])
        self.assertEqual(len(specs), 2)
