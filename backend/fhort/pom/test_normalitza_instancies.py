"""LA MIGRACIÓ DE NORMALITZACIÓ — les quatre lleis d'Agus (26/08), provades una a una.

  1. TOTES les taules amb `instancia`, no només les del diccionari.
  2. GUARDA DE COL·LISIÓ: si el slug canònic ja el té una altra fila de la mateixa clau,
     AVORTA i llista. No tria.
  3. IDEMPOTENT i amb recompte declarat.
  4. El vocabulari que no és de la casa NO es toca.

Aquesta migració viatja al mini-tren i s'aplicarà a PROD sobre una població que encara no s'ha
comptat: el que aquí no estigui provat, allà no ho vigilarà ningú.
"""
from django.apps import apps as registre
from django_tenants.test.cases import TenantTestCase

from fhort.pom.normalitza_instancies import (ColisioDeNormalitzacio, _models_amb_instancia,
                                             aplica, planifica)


class CoberturaDeTaulesTest(TenantTestCase):

    def test_LLEI_1_hi_entren_totes_les_taules_amb_instancia(self):
        # 🚨 La llista NO és escrita a mà: surt del registre de models. Una llista a mà es
        # queda enrere el dia que algú afegeixi la columna a una taula nova, i aquella taula es
        # quedaria amb els slugs vells mentre la resta del sistema en fa servir de nous —
        # trencant les claus creuades (GradedSpec, PieceFittingLine…).
        etiquetes = {m._meta.label for m in _models_amb_instancia(registre)}
        for esperada in ['models_app.BaseMeasurement', 'models_app.MeasurementChangeLog',
                         'models_app.ModelGradingOverride', 'models_app.SizeCheckLine',
                         'models_app.POMPlacement', 'fitting.GradedSpec',
                         'fitting.PieceFittingLine', 'fitting.POMAlert',
                         'pom.GarmentPOMMap', 'pom.GarmentTypePOMMap',
                         'pom.GarmentGroupPOMMap', 'pom.ItemBaseMeasurement']:
            self.assertIn(esperada, etiquetes)
        self.assertEqual(len(etiquetes), 12)


class _Banc(TenantTestCase):
    """Un model amb POM i les germanes que calguin, per fabricar els casos."""

    def setUp(self):
        from fhort.models_app.models import BaseMeasurement, Model
        from fhort.pom.models import POMMaster
        self.BM = BaseMeasurement
        self.pom = POMMaster.objects.create(codi_client='NRM', nom_client='Normalitza')
        self.model = Model.objects.create(
            codi_intern='TST-NRM', codi_tenant='TST', any=2027, sequencial=91,
            temporada='FW27', size_run_model='XS·S·M', base_size_label='S')

    def _canvis_de(self, canvis, etiqueta):
        """Els canvis d'UN model.

        🔑 Crear una `BaseMeasurement` amb instància n'escriu TAMBÉ una a
        `MeasurementChangeLog` (el senyal que registra l'escriptura), o sigui que el recompte
        TOTAL no és un per fila creada. Assertar el total feia que el banc digués «2 != 1» amb
        el producte funcionant. Es compta per model, que és el que es vol dir.
        """
        return [c for c in canvis if c[0] == etiqueta]

    def _fila(self, instancia, valor=10):
        # ⚠️ `nom_fitxa` NO és opcional aquí: la invariant de BD `instancia_exigeix_nom` no
        # admet una germana sense nom, i sense això el banc peta amb un `CheckViolation` que no
        # té res a veure amb el que es vol provar.
        return self.BM.objects.create(model=self.model, pom=self.pom, capa='exterior',
                                      instancia=instancia, garment='', base_value_cm=valor,
                                      nom_fitxa=f'NRM-{instancia}')


class NormalitzacioTest(_Banc):

    def test_reordena_el_slug_a_l_ordre_canonic(self):
        f = self._fila('extended-right')
        canvis, saltades = aplica(registre, 'test')
        f.refresh_from_db()
        self.assertEqual(f.instancia, 'right-extended')
        self.assertEqual(len(self._canvis_de(canvis, 'models_app.BaseMeasurement')), 1)
        # …i el registre d'escriptura que el senyal ha deixat també s'ha normalitzat: és
        # exactament la llei 1 d'Agus (totes les taules, o les claus creuades es trenquen).
        self.assertEqual(len(self._canvis_de(canvis, 'models_app.MeasurementChangeLog')), 1)

    def test_el_que_JA_es_canonic_no_es_toca(self):
        f = self._fila('front-left')
        canvis, _ = aplica(registre, 'test')
        f.refresh_from_db()
        self.assertEqual(f.instancia, 'front-left')
        self.assertEqual(canvis, [])

    def test_LLEI_3_es_IDEMPOTENT(self):
        self._fila('extended-right')
        primera, _ = aplica(registre, 'test')
        self.assertTrue(primera)
        segona, _ = aplica(registre, 'test')
        self.assertEqual(segona, [], 'la segona correguda no ha de tocar res')

    def test_LLEI_4_el_vocabulari_que_no_es_de_la_casa_NO_es_toca(self):
        # Una instància que s'hagi creat un tenant no té ordre canònic: reordenar-la seria
        # inventar-li una posició i canviar-li la clau a algú.
        f = self._fila('sleeve2-left')
        canvis, saltades = aplica(registre, 'test')
        f.refresh_from_db()
        self.assertEqual(f.instancia, 'sleeve2-left')
        self.assertEqual(canvis, [])
        # Dues saltades: la fila i el seu registre d'escriptura. Cap de les dues es toca.
        self.assertTrue(saltades)
        for s in saltades:
            self.assertIn('sleeve2', s[3])

    def test_un_slug_SIMPLE_no_hi_entra(self):
        f = self._fila('left')
        canvis, _ = aplica(registre, 'test')
        f.refresh_from_db()
        self.assertEqual(f.instancia, 'left')
        self.assertEqual(canvis, [])


class GuardaDeColisioTest(_Banc):

    def test_LLEI_2_amb_COL·LISIO_AVORTA_i_no_escriu_res(self):
        # 🚨 EL CAS: una `right-extended` i una `extended-right` convivint a la mateixa clau.
        # Fusionar dues germanes és una decisió de domini i no la pren una migració.
        vella = self._fila('extended-right', valor=10)
        ja_hi_es = self._fila('right-extended', valor=99)
        with self.assertRaises(ColisioDeNormalitzacio) as ctx:
            aplica(registre, 'test')
        vella.refresh_from_db(); ja_hi_es.refresh_from_db()
        self.assertEqual(vella.instancia, 'extended-right', 'no s\'havia d\'escriure res')
        self.assertEqual(ja_hi_es.base_value_cm, 99, 'l\'ocupant no s\'ha de tocar mai')
        # El missatge ha de DIR quines files, o qui el llegeixi a PROD no en podrà fer res.
        self.assertIn('extended-right', str(ctx.exception))
        self.assertIn(str(ja_hi_es.pk), str(ctx.exception))

    def test_la_colisio_es_veu_al_PLA_abans_d_escriure(self):
        self._fila('extended-right')
        self._fila('right-extended', valor=99)
        canvis, colisions, _saltades = planifica(registre)
        self.assertEqual(self._canvis_de(canvis, 'models_app.BaseMeasurement'), [])
        self.assertEqual(len(colisions), 1)

    def test_sense_UNIQUE_no_hi_ha_colisio_possible(self):
        # `MeasurementChangeLog` és un LOG i no té unique: dues files amb la mateixa instància
        # hi són legítimes i no poden col·lidir mai. Les escriu el SENYAL en crear les dues
        # germanes de sobre — no cal fabricar-les a mà (i el camp `valor_nou` és NOT NULL).
        from fhort.models_app.models import MeasurementChangeLog
        self._fila('extended-right', valor=10)
        self._fila('right-extended', valor=99)
        self.assertEqual(
            MeasurementChangeLog.objects.filter(instancia__contains='-').count(), 2)
        canvis, colisions, _ = planifica(registre)
        # La col·lisió és de la taula amb UNIQUE; el log s'hi normalitza sense problema.
        self.assertEqual(len(self._canvis_de(canvis, 'models_app.MeasurementChangeLog')), 1)
        self.assertTrue(all(c[0] == 'models_app.BaseMeasurement' for c in colisions))


class CanariTest(_Banc):

    def test_el_canari_atura_si_la_poblacio_no_es_la_censada(self):
        # És el que protegeix la correguda controlada: a staging se n'esperaven 4.
        self._fila('extended-right')
        with self.assertRaises(ColisioDeNormalitzacio) as ctx:
            aplica(registre, 'test', esperades=4)
        self.assertIn('4', str(ctx.exception))

    def test_amb_el_numero_bo_passa(self):
        self._fila('extended-right')
        # 2: la germana i el registre que el senyal n'ha deixat (llei 1: totes les taules).
        canvis, _ = aplica(registre, 'test', esperades=2)
        self.assertEqual(len(canvis), 2)
