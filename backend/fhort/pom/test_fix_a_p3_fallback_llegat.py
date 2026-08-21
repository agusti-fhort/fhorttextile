"""FIX-A/PAS-3 · ELS DOS FALLBACKS AL CAMP LLEGAT, RETIRATS ALHORA.

Substrat: `DIAGNOSI_PRE_SPRINTS_STAGING_2026-08-21.md` §1.3 · `DIAGNOSI_BUGS_PROD_837` §A.5·1.

── EL FORAT ─────────────────────────────────────────────────────────────────────────────
El camp `increment` és el LLEGAT: el poblava la materialització des del joc de regles i CAP
superfície d'edició no el tocava mai. Es fossilitzava amb el valor del dia que la regla va
néixer. Dos nodes hi queien quan `increment_base` era NULL:

    ① pom/services.py       `_apply_rule`, branca LINEAR      → Escalat (GradedSpec)
    ② pom/grading_utils.py  `increment_de_l_aresta`           → `propaga_ancoratges`, i d'aquí
                                                                la PRESA i la derivació de base

I s'hi arribava per la porta de casa: buidar el camp «Δ base» a la pantalla de Graduació envia
`increment_base: null` i **passa la validació si la regla té break**. Es desava amb 200 OK, la
cel·la es veia buida, i el motor graduava amb el delta del joc antic.

② no tenia el guard `increment_base is not None` a sobre —el decideix el cridador—, de manera
que **arreglar-ne un de sol hauria fet dir coses diferents a Escalat i a la presa sobre la
MATEIXA regla**, i en silenci. Per això aquest fitxer mesura els dos junts, sempre.

── LA LLEI ARA ─────────────────────────────────────────────────────────────────────────
La D2, la mateixa de sempre: **regla incompleta = cel·la ABSENT**. Mai un delta fantasma, mai
un FIXED fabricat. És exactament el que ja regia la regla que no existeix i el STEP sense
valors; el que canvia és que la LINEAR sense delta base hi entra també.
"""
import datetime

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase

from fhort.pom.grading_utils import (ReglaSenseDeltaError, desnivell_entre_talles,
                                     increment_de_l_aresta, propaga_ancoratges)
from fhort.pom.services import _apply_rule

RUN = ['XXS', 'XS', 'S', 'M', 'L', 'XL', 'XXL', '3XL']
BASE_IDX = 2          # 'S'
BASE_VAL = 100.0


class _Regla:
    """Regla en memòria. Cap ORM, cap BD: aquests nodes són funcions PURES i s'han de poder
    mesurar com a tals."""
    def __init__(self, **kw):
        self.pom_id = 42
        self.pom = None
        self.logica = 'LINEAR'
        self.increment = None
        self.increment_base = None
        self.increment_break = None
        self.talla_break_label = None
        self.valors_step = None
        for k, v in kw.items():
            setattr(self, k, v)


def _corba_escalat(regla):
    out = {}
    for i, lab in enumerate(RUN):
        v, _gt = _apply_rule(regla, BASE_VAL, i - BASE_IDX, i, BASE_IDX,
                             size_run=RUN, warnings=[])
        out[lab] = None if v is None else round(float(v), 2)
    return out


def _corba_presa(regla, warnings=None):
    crua = propaga_ancoratges(regla, 'S', BASE_VAL, RUN, warnings=warnings,
                              run_sistema=RUN, base_label='S')
    return {k: (None if v is None else round(float(v), 2)) for k, v in crua.items()}


class NodePurTest(TenantTestCase):
    """Els dos nodes, un a un, sense passar per cap vista."""

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Test Tenant'
        tenant.tipologia = 'MARCA'
        tenant.codi_tenant = 'TST'
        tenant.vat_number = 'X0000000X'
        tenant.tipus_client = 'STANDARD'
        tenant.gratis_fins = datetime.date(2030, 1, 1)
        return tenant

    # ── ② increment_de_l_aresta ───────────────────────────────────────────────
    def test_l_aresta_ALCA_quan_no_hi_ha_delta_base(self):
        """⬅️ EL DEFECTE: aquí hi havia `return float(rule.increment)` → 2.0 per pas."""
        regla = _Regla(increment=2.0)          # llegat poblat, canònic buit
        with self.assertRaises(ReglaSenseDeltaError):
            increment_de_l_aresta(regla, RUN, BASE_IDX, 2, 3)

    def test_l_aresta_NO_alca_quan_la_regla_es_completa(self):
        regla = _Regla(increment=9.9, increment_base=0.5)
        self.assertEqual(increment_de_l_aresta(regla, RUN, BASE_IDX, 2, 3), 0.5)

    def test_el_llegat_NO_pinta_res_quan_hi_ha_delta_base(self):
        """La prova que el fix no ha canviat el camí bo: `increment=9.9` és soroll."""
        amb_llegat = _Regla(increment=9.9, increment_base=0.5)
        sense_llegat = _Regla(increment=None, increment_base=0.5)
        self.assertEqual(_corba_escalat(amb_llegat), _corba_escalat(sense_llegat))

    def test_el_desnivell_deixa_pujar_l_excepcio(self):
        """`desnivell_entre_talles` només suma arestes: no ha de tapar res."""
        with self.assertRaises(ReglaSenseDeltaError):
            desnivell_entre_talles(_Regla(increment=2.0), RUN, BASE_IDX, BASE_IDX, 5)

    # ── ① _apply_rule ─────────────────────────────────────────────────────────
    def test_apply_rule_deixa_la_cel_la_ABSENT_i_ho_diu(self):
        avisos = []
        v, gt = _apply_rule(_Regla(increment=2.0), BASE_VAL, 1, 3, BASE_IDX,
                            size_run=RUN, warnings=avisos)
        self.assertIsNone(v)                    # ⬅️ EL DEFECTE: abans valia 102.0
        self.assertEqual(gt, 'LINEAR')
        self.assertEqual(len(avisos), 1)
        self.assertIn('increment_base', avisos[0])

    def test_la_talla_BASE_tampoc_no_emet(self):
        """Cap rescat per la base: una regla sense llei no en té ni a la seva pròpia talla.
        Emetre-hi el valor base seria fabricar un FIXED — el que va deixar el model 163 amb
        225 specs a delta 0 i 200 OK."""
        v, _ = _apply_rule(_Regla(increment=2.0), BASE_VAL, 0, BASE_IDX, BASE_IDX,
                           size_run=RUN, warnings=[])
        self.assertIsNone(v)

    def test_FIXED_i_ZERO_no_queden_tocats(self):
        """No entren mai a la branca canònica ni a la LINEAR: el fix no els pot arribar."""
        v, gt = _apply_rule(_Regla(logica='FIXED', increment=7.0), BASE_VAL, 1, 3, BASE_IDX,
                            size_run=RUN, warnings=[])
        self.assertEqual((v, gt), (BASE_VAL, 'FIXED'))
        v, gt = _apply_rule(_Regla(logica='ZERO'), BASE_VAL, 1, 3, BASE_IDX,
                            size_run=RUN, warnings=[])
        self.assertEqual((v, gt), (0.0, 'ZERO'))

    def test_STEP_segueix_amb_la_seva_llei(self):
        regla = _Regla(logica='STEP', increment=5.0, valors_step={'M': 1.0})
        v, gt = _apply_rule(regla, BASE_VAL, 1, 3, BASE_IDX, size_run=RUN, warnings=[])
        self.assertEqual((round(v, 2), gt), (101.0, 'STEP'))

    # ── ⑀ propaga_ancoratges ──────────────────────────────────────────────────
    def test_la_presa_NO_deriva_cap_valor_i_ho_diu(self):
        avisos = []
        corba = _corba_presa(_Regla(increment=2.0), warnings=avisos)
        self.assertEqual(set(corba.values()), {None})   # ⬅️ abans: 96.0 … 112.0
        self.assertEqual(len(avisos), 1)
        self.assertIn('increment_base', avisos[0])

    def test_la_presa_segueix_derivant_quan_la_regla_es_completa(self):
        corba = _corba_presa(_Regla(increment=9.9, increment_base=0.5))
        self.assertEqual(corba['M'], 100.5)
        self.assertEqual(corba['XS'], 99.5)


class ElsDosAlhoraTest(NodePurTest):
    """🔑 LA PROVA QUE JUSTIFICA EL SPRINT: cap règim pot fer divergir Escalat de la presa.

    Aquesta classe és el bessó del BLOC C d'`ops/qa/banc_paritat_1383.py`. Hi és per DUPLICAT
    a posta: el banc mesura staging i corre a mà; això corre a cada suite. Si algun dia algú
    toca un dels dos nodes i no l'altre, un dels dos ho ha de veure.
    """

    CASOS = [
        ('LINEAR · ib=NULL · llegat 2.00  (EL CAS DEL FIX A)', dict(increment=2.0)),
        ('LINEAR · ib=NULL · llegat NULL', dict(increment=None)),
        ('LINEAR · ib=0.50 · llegat 2.00', dict(increment=2.0, increment_base=0.5)),
        ('LINEAR · ib=0.50 · brk=1.50 · break M',
         dict(increment=9.9, increment_base=0.5, increment_break=1.5, talla_break_label='M')),
        ('LINEAR · ib=0.50 · brk=1.50 · break XS (extrem petit, S10)',
         dict(increment=9.9, increment_base=0.5, increment_break=1.5, talla_break_label='XS')),
    ]

    def test_escalat_i_presa_diuen_SEMPRE_el_mateix(self):
        for nom, kw in self.CASOS:
            with self.subTest(cas=nom):
                regla = _Regla(**kw)
                self.assertEqual(_corba_escalat(regla), _corba_presa(regla))

    def test_i_els_dos_regims_incomplets_donen_ABSENT_als_dos_costats(self):
        for nom, kw in self.CASOS[:2]:
            with self.subTest(cas=nom):
                regla = _Regla(**kw)
                self.assertEqual(set(_corba_escalat(regla).values()), {None})
                self.assertEqual(set(_corba_presa(regla).values()), {None})
