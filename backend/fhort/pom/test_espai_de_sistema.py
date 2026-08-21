"""Motor en ESPAI DE SISTEMA (llei S24b, 2026-07-22).

L'ordre i la distància entre talles els mana el SizeSystem. El run del model és un
subconjunt, potencialment NO CONTIGU, que mai els redefineix.

Aquests tests ataquen `_apply_rule` directament amb el referent que li prepara
`escala_del_model`: `size_run` = run del SISTEMA, i `size_idx`/`base_idx` = posicions dins
d'aquest. Purs, sense BD.

Referència: DIAGNOSI_ORDRE_RUN_MODEL_2026-07-22.md (cas real: model 166, run 'XS·S·L·XXS·M').

⚠️ FIX-A/PAS-1c (2026-08-21) — AQUEST FITXER TENIA TRES PROVES DEL RÈGIM «LINEAR CLÀSSIC»
(`increment=3` sense `increment_base`), que és el camp LLEGAT. El motor hi queia per fallback;
des del FIX A ja no, i una regla sense delta base no gradua (llei D2 de cel·la absent).

Les tres no s'esborren: **la geometria que protegien —el SIGNE i la DISTÀNCIA en espai de
sistema— és la raó de ser del fitxer i no ha canviat gens**. Passen al camp canònic, que és on
totes tres tenien ja la seva bessona (`test_linear_canonic_identic`,
`test_linear_compta_DOS_passos_de_S_a_L`). El règim llegat, retirat, té ara prova PRÒPIA a
`ReglaIncompletaTest`: ha de dir que NO gradua.

🚨 I una lliçó que val la pena deixar escrita. `test_linear_identic` **no va petar** amb el fix:
comparava dues taules i totes dues van passar a estar plenes de `None` alhora. Un test
d'IGUALTAT no veu una retirada — igual que el golden que mesurava models inexistents i donava
un md5 perfectament estable. Ara compara i, a més, **exigeix que hi hagi xifres**.
"""
from types import SimpleNamespace

from django.test import SimpleTestCase

from fhort.pom.services import _apply_rule

SISTEMA = ['XXS', 'XS', 'S', 'M', 'L', 'XL', 'XXL', '3XL']   # ALPHA_EU_W
BASE_VAL = 100.0


def _rule(**kw):
    base = dict(logica=None, increment=None, increment_base=None, increment_break=None,
                talla_break_label=None, valors_step=None, pom=None, pom_id=1)
    base.update(kw)
    return SimpleNamespace(**base)


def _taula(rule, run_model, base='S', sistema=SISTEMA):
    """Gradua `run_model` en espai de sistema — el que fa `generate_graded_specs`."""
    pos = {e: i for i, e in enumerate(sistema)}
    base_idx = pos[base]
    out = {}
    for label in sorted(run_model, key=lambda l: pos[l]):
        i = pos[label]
        val, _ = _apply_rule(rule, BASE_VAL, i - base_idx, i, base_idx,
                             size_run=sistema, warnings=[])
        out[label] = val
    return out


class RobustesaALOrdreTest(SimpleTestCase):
    """Q2 — un run desordenat ha de donar EXACTAMENT el mateix que el canònic: en espai de
    sistema l'ordre de la llista del model ja no vol dir res."""

    DESORDENAT = ['XS', 'S', 'L', 'XXS', 'M']     # el run real del 166 a PROD
    CANONIC = ['XXS', 'XS', 'S', 'M', 'L']

    def test_linear_identic(self):
        rule = _rule(logica='LINEAR', increment_base=3)
        taula = _taula(rule, self.DESORDENAT)
        # 🚨 LA GUARDA CONTRA EL BUIT: sense això, dues taules totes a `None` són «idèntiques»
        # i el test dona verd sobre un motor que no gradua res. V. la nota de la capçalera.
        self.assertTrue(all(v is not None for v in taula.values()), taula)
        self.assertEqual(taula, _taula(rule, self.CANONIC))

    def test_linear_canonic_identic(self):
        rule = _rule(logica='LINEAR', increment_base=3)
        self.assertEqual(_taula(rule, self.DESORDENAT), _taula(rule, self.CANONIC))

    def test_linear_amb_break_identic(self):
        rule = _rule(logica='LINEAR', increment_base=3, increment_break=6,
                     talla_break_label='L')
        self.assertEqual(_taula(rule, self.DESORDENAT), _taula(rule, self.CANONIC))

    def test_step_identic(self):
        rule = _rule(logica='STEP', valors_step={'XXS': 2, 'XS': 2, 'M': 3, 'L': 3})
        taula = _taula(rule, self.DESORDENAT)
        self.assertTrue(all(v is not None for v in taula.values()), taula)   # v. la capçalera
        self.assertEqual(taula, _taula(rule, self.CANONIC))

    def test_el_signe_ja_no_s_inverteix(self):
        """El símptoma concret de la diagnosi: amb el run apendat, la XXS graduava 106 (com
        si fos DUES talles per SOBRE de la base) en comptes de 94."""
        rule = _rule(logica='LINEAR', increment_base=3)
        taula = _taula(rule, self.DESORDENAT)
        self.assertEqual(taula['XXS'], 94.0)
        self.assertEqual(taula['M'], 103.0)
        self.assertEqual(taula['L'], 106.0)

    def test_break_ja_no_atrapa_les_talles_petites(self):
        """Amb break a L i run apendat, la XXS acumulava l'increment extrem tres vegades
        (112) perquè quedava DESPRÉS de la L a la llista."""
        rule = _rule(logica='LINEAR', increment_base=3, increment_break=6,
                     talla_break_label='L')
        taula = _taula(rule, self.DESORDENAT)
        self.assertEqual(taula['XXS'], 94.0)
        self.assertEqual(taula['L'], 109.0)


class RunNoContiguTest(SimpleTestCase):
    """Q2 — la distància la mana el sistema: un client que no fabrica la M no fa que la L
    estigui més a prop de la S."""

    RUN = ['XS', 'S', 'L']        # sense M

    def test_linear_compta_DOS_passos_de_S_a_L(self):
        rule = _rule(logica='LINEAR', increment_base=3)
        taula = _taula(rule, self.RUN)
        self.assertEqual(taula, {'XS': 97.0, 'S': 100.0, 'L': 106.0})

    def test_linear_compta_DOS_passos_tambe_amb_break_avall(self):
        """La bessona de sobre amb el relleu a l'altra banda: la distància no depèn del break."""
        rule = _rule(logica='LINEAR', increment_base=3, increment_break=3,
                     talla_break_label='XS')
        self.assertEqual(_taula(rule, self.RUN)['L'], 106.0)

    def test_break_a_la_talla_que_el_model_NO_fabrica(self):
        """El llindar és un concepte del SISTEMA: un break a M s'aplica encara que el model
        no fabriqui la M, perquè el camí cap a L la travessa."""
        rule = _rule(logica='LINEAR', increment_base=3, increment_break=6,
                     talla_break_label='M')
        taula = _taula(rule, self.RUN)
        # S→M creua el break (6) i M→L també (6) = 112.
        self.assertEqual(taula['L'], 112.0)
        self.assertEqual(taula['XS'], 97.0)

    def test_step_necessita_el_delta_de_la_talla_TRAVESSADA(self):
        """CRITERI DOCUMENTAT (S24b): el camí es recorre sobre les talles del SISTEMA, i per
        tant STEP necessita el delta de la M encara que el model no la fabriqui.

        🚨 QUÈ PASSA QUAN FALTA — CONTRACTE CANVIAT PEL TRAM E (Agus, 2026-08-21). Aquí
        s'asseria `None` (cel·la absent, llei D2). Ara la cel·la surt amb **el valor de la talla
        base**, marcada en vermell a la superfície i apuntada a la llista de treball manual. El
        que aquest test protegeix segueix intacte i és l'altra meitat: **el motor no col·lapsa
        el camí ni el gradua sense el delta que li falta** —106.0 (el resultat amb la M
        informada) segueix sent el número prohibit— i el warning segueix nomenant la M, que és
        la talla que s'ha d'anar a buscar."""
        rule = _rule(logica='STEP', valors_step={'XS': 2, 'L': 3})   # falta la M
        warnings = []
        marques = []
        val, _ = _apply_rule(rule, BASE_VAL, 2, 4, 2, size_run=SISTEMA, warnings=warnings,
                             marques=marques)
        self.assertEqual(val, BASE_VAL)
        self.assertNotEqual(val, 106.0, 'no pot col·lapsar el camí ni inventar el delta que falta')
        self.assertEqual(len(warnings), 1)
        self.assertIn('M', warnings[0])
        self.assertEqual(marques, [{'pom_id': 1, 'pom_codi': 1, 'talla': 'L', 'falta': 'M'}])

    def test_step_amb_el_delta_de_la_talla_travessada_SI_calcula(self):
        rule = _rule(logica='STEP', valors_step={'XS': 2, 'M': 3, 'L': 3})
        taula = _taula(rule, self.RUN)
        self.assertEqual(taula, {'XS': 98.0, 'S': 100.0, 'L': 106.0})


class EscalaDelModelTest(SimpleTestCase):
    """Guards previs de `escala_del_model`: el que el motor refusa abans de calcular res."""

    def _model(self, run, base, talles=SISTEMA):
        ss = SimpleNamespace(
            codi='ALPHA_EU_W',
            talles=SimpleNamespace(order_by=lambda _f: [
                SimpleNamespace(etiqueta=e, ordre=i) for i, e in enumerate(talles)
            ]),
        )
        return SimpleNamespace(codi_intern='TST-1', size_run_model=run,
                               base_size_label=base, size_system=ss)

    def test_normalitza_l_ordre_en_memoria(self):
        from fhort.pom.services import escala_del_model
        run, sistema, pos, base_idx = escala_del_model(self._model('XS·S·L·XXS·M', 'S'))
        self.assertEqual(run, ['XXS', 'XS', 'S', 'M', 'L'])
        self.assertEqual(sistema, SISTEMA)
        self.assertEqual(base_idx, 2)
        self.assertEqual(pos('L'), 4)

    def test_conserva_el_forat_del_run_no_contigu(self):
        from fhort.pom.services import escala_del_model
        run, _, _, _ = escala_del_model(self._model('L·XS·S', 'S'))
        self.assertEqual(run, ['XS', 'S', 'L'])

    def test_etiqueta_fora_del_sistema_peta_amb_missatge_clar(self):
        from fhort.pom.services import escala_del_model
        with self.assertRaises(ValueError) as cm:
            escala_del_model(self._model('XS·S·5XL', 'S'))
        self.assertIn('5XL', str(cm.exception))

    def test_base_fora_del_run_peta(self):
        from fhort.pom.services import escala_del_model
        with self.assertRaises(ValueError):
            escala_del_model(self._model('XS·S·L', 'XL'))

    def test_sistema_sense_talles_peta(self):
        from fhort.pom.services import escala_del_model
        with self.assertRaises(ValueError):
            escala_del_model(self._model('XS·S', 'S', talles=[]))

    def test_pont_canonic_2xl(self):
        """El run pot dir 2XL on el sistema diu XXL: es reconeix i s'ordena, i l'etiqueta
        que es conserva és la del MODEL (és la que va a GradedSpec.size_label)."""
        from fhort.pom.services import escala_del_model
        run, _, pos, _ = escala_del_model(self._model('2XL·S·L', 'S'))
        self.assertEqual(run, ['S', 'L', '2XL'])
        self.assertEqual(pos('2XL'), 6)


class ReglaIncompletaTest(SimpleTestCase):
    """FIX-A/PAS-3 — EL RÈGIM QUE S'HA RETIRAT, amb prova pròpia.

    El «LINEAR clàssic» (`increment` sol, sense `increment_base`) era el camp LLEGAT: el poblava
    la materialització des del joc i cap superfície d'edició no el tocava, o sigui que es
    fossilitzava. Graduar-hi volia dir graduar amb el delta del joc del dia que la regla va
    néixer. Ara no gradua: llei D2 de cel·la absent, la mateixa que ja regia la regla que no
    existeix i el STEP sense valors.

    Aquests tres tests són el que queda d'aquell règim, i han de dir que NO hi és.
    """

    RUN = ['XS', 'S', 'L']

    def test_el_llegat_sol_NO_gradua(self):
        taula = _taula(_rule(logica='LINEAR', increment=3), self.RUN)
        self.assertEqual(set(taula.values()), {None}, taula)

    def test_i_ho_diu_amb_un_avis_que_nomena_el_camp(self):
        avisos = []
        val, gt = _apply_rule(_rule(logica='LINEAR', increment=3), BASE_VAL, 1, 3, 2,
                              size_run=SISTEMA, warnings=avisos)
        self.assertIsNone(val)
        self.assertEqual(gt, 'LINEAR')
        self.assertIn('increment_base', avisos[0])

    def test_amb_delta_base_el_llegat_no_pinta_res(self):
        """El control: `increment` divergent no mou ni una xifra quan hi ha forma canònica.
        És la garantia que el backfill del PAS 2 no podia canviar cap cel·la."""
        amb = _rule(logica='LINEAR', increment=99, increment_base=3)
        sense = _rule(logica='LINEAR', increment=None, increment_base=3)
        self.assertEqual(_taula(amb, self.RUN), _taula(sense, self.RUN))
