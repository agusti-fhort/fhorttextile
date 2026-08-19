"""SET-2/F1 + Q1-bis · CONCERN 2 — L'ESCALAT ESCRIU A LA FILA DE LA PEÇA, AMB LA SEVA LLEI.

Substrat: `docs/diagnosis/DIAGNOSI_F1_ESCRIPTURA_GARMENT.md` (Q2 · Q4 · Q5).
Germà d'`test_c4_escriptura_germanes.py`, que va tancar el mateix defecte per als eixos
`capa`/`instancia`. Aquí entra el tercer, i porta dues coses que **han d'anar juntes**:

  · **F1 — SOBRE QUINA FILA S'ESCRIU.** `_write_base` feia
    `get_or_create(model, pom, capa, instancia)`, i amb una peça i la mare compartint POM
    això casa amb DUES files → `MultipleObjectsReturned` → **500**. Mesurat a staging:
    POM 962 del model 1379 i POM 904 del 1320. La diagnosi el va INFERIR sense escriure;
    aquest banc el REPRODUEIX.

  · **Q1-bis — QUINA LLEI S'APLICA.** La vista llegia `_load_grading_rules(model)`, que
    serveix la regla de la **PEÇA MARE** per contracte declarat (`pom/services.py:774`).
    `propaga_ancoratges` en deriva la nova base, o sigui que amb la llei de la mare la 02
    es propagava amb un increment que no és seu.

🚨 **PER QUÈ AL MATEIX TRAM.** Mentre el 500 hi era, TAPAVA el defecte de la llei. Tancar
F1 sol hauria convertit un error sorollós en **un valor mal calculat i mut**. És la llei
S42 girada: *tancar una escriptura ARMA el seu lector*. El test
`test_la_peca_es_propaga_amb_LA_SEVA_llei` és el que ho vigila, i **només prova res perquè
el banc sembra una divergència de debò**: la 02 té regla PRÒPIA amb un delta diferent del
de la mare. Amb dues regles iguals, aquest test passaria amb el defecte viu.

⚠️ AQUÍ NO HI HA `comportes_garment_alcades` ni `comportes_alcades`, i és a posta: les
comportes `*_garment_gate_set2` **ja no existeixen** (migració
`0084_set2_12_retirada_comportes_garment`), el `DROP CONSTRAINT IF EXISTS` és un no-op i el
`savepoint_rollback` del `finally` s'enduria els fixtures d'aquest fitxer.
"""
import datetime

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.accounts.models import UserProfile
from fhort.models_app.models import (BaseMeasurement, MeasurementChangeLog, Model,
                                     ModelGradingOverride, ModelGradingRule)
from fhort.pom.models import MeasurementLayer, POMMaster, SizeDefinition, SizeSystem

EXTERIOR = MeasurementLayer.SLUG_DEFECTE
MARE = ''
SEGONA = '02'


class BaseEscalatF1(TenantTestCase):
    """Un model amb run XS·S·M (base S) i el MATEIX POM viu a la mare i a la peça 02."""

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Test Tenant'
        tenant.tipologia = 'MARCA'
        tenant.codi_tenant = 'TST'
        tenant.vat_number = 'X0000000X'
        tenant.tipus_client = 'STANDARD'
        tenant.gratis_fins = datetime.date(2030, 1, 1)
        return tenant

    def setUp(self):
        self.pom = POMMaster.objects.create(codi_client='CH', nom_client='Pit')
        self.ss = SizeSystem.objects.create(codi='SS_F1', nom='SS F1', base_unit='ALPHA')
        for i, et in enumerate(['XS', 'S', 'M']):
            SizeDefinition.objects.create(size_system=self.ss, etiqueta=et, ordre=i)
        self.model = Model.objects.create(
            codi_intern='TST-F1W', codi_tenant='TST', any=2027, sequencial=7,
            temporada='FW27', size_system=self.ss,
            size_run_model='XS·S·M', base_size_label='S')
        self.user, _ = get_user_model().objects.get_or_create(
            username='qa_f1', defaults={'email': 'qa@f1.test'})
        self.perfil, _ = UserProfile.objects.get_or_create(
            user=self.user, defaults={'nom_complet': 'QA F1', 'rol_nom': 'QA'})

    def _req(self, body):
        r = APIRequestFactory().post('/x/', body, format='json')
        force_authenticate(r, user=self.user)
        return r

    def _dues_peces(self, valor_mare=100.0, valor_segona=100.0, segona_activa=True):
        """LA FORMA EXACTA DEL POM 962 AL MODEL 1379: dues files idèntiques en capa i
        instància, diferents NOMÉS en peça. És l'única forma que col·lapsa el lookup curt."""
        self.mare = BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=valor_mare,
            nom_fitxa='CH', garment=MARE)
        self.segona = BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=valor_segona,
            nom_fitxa='CH', garment=SEGONA, is_active=segona_activa)

    def _valors(self):
        return {bm.garment: float(bm.base_value_cm) for bm in BaseMeasurement.objects.filter(
            model=self.model, pom=self.pom)}

    def _sf(self, delta_mare=2.0, delta_segona=None):
        """SizeFitting + regles residents. `generate_graded_specs` refusa un model sense cap.

        `delta_segona` sembra la DIVERGÈNCIA de Q1-bis: una llei pròpia de la peça 02 amb un
        increment diferent del de la mare. Sense això el banc de la llei és CEC.
        """
        ModelGradingRule.objects.get_or_create(
            model=self.model, pom=self.pom, garment=MARE,
            defaults={'logica': 'LINEAR', 'increment': delta_mare,
                      'increment_base': delta_mare, 'actiu': True})
        if delta_segona is not None:
            ModelGradingRule.objects.get_or_create(
                model=self.model, pom=self.pom, garment=SEGONA,
                defaults={'logica': 'LINEAR', 'increment': delta_segona,
                          'increment_base': delta_segona, 'actiu': True})
        from fhort.fitting.models import SizeFitting
        sf, _ = SizeFitting.objects.get_or_create(
            model=self.model, numero=1,
            defaults={'codi': 'SF-F1', 'tipus': 'SizeSet', 'estat': 'Pendent',
                      'creat_per': self.perfil})
        return sf


class WriteBaseResolLaFilaDeLaPecaTest(BaseEscalatF1):
    """El punt únic d'escriptura de la base, exercit directament."""

    def test_write_base_amb_una_germana_de_peca_NO_pot_petar(self):
        """🔴 EL 500 REPRODUÏT — la forma exacta del POM 962 al 1379."""
        from fhort.models_app.views import _write_base
        self._dues_peces()
        _write_base(self.model, self.pom, 55.0, self.user, 'test', garment=SEGONA)
        self.assertEqual(len(self._valors()), 2, 'no ha de néixer cap fila nova')

    def test_write_base_escriu_a_la_PECA_i_deixa_la_mare_INTACTA(self):
        """El dany silenciós de sota el 500: amb el desempat a l'atzar, ajustar la peça 02
        movia el valor de la MARE."""
        from fhort.models_app.views import _write_base
        self._dues_peces()
        _write_base(self.model, self.pom, 55.0, self.user, 'test', garment=SEGONA)
        self.assertEqual(self._valors(), {MARE: 100.0, SEGONA: 55.0})

    def test_qui_no_diu_lEIX_escriu_a_la_MARE(self):
        """La compatibilitat: cap cridador antic no canvia de destí."""
        from fhort.models_app.views import _write_base
        self._dues_peces()
        _write_base(self.model, self.pom, 77.0, self.user, 'test')
        self.assertEqual(self._valors(), {MARE: 77.0, SEGONA: 100.0})

    def test_una_germana_PODADA_no_fa_petar_ni_es_duplica(self):
        """🚨 PER QUÈ `is_active` NO ÉS AL LOOKUP — el cas del model 1320 (POM 904), on la
        fila de la peça 02 està PODADA.

        La diagnosi deia que **una poda no cura el 500** (amb el lookup curt, una fila
        inactiva segueix col·lapsant el `get_or_create`) i d'aquí es podria llegir que el
        lookup ha de filtrar `is_active`. **No pot.** La clau única de la BD és
        `(model, pom, capa, instancia, garment)` i NO inclou `is_active`: amb la fila de la
        peça podada, un lookup amb `is_active=True` no la trobaria i intentaria CREAR-NE una
        segona amb la mateixa clau → `IntegrityError`. Un 500 canviat per un altre.

        La clau sencera ja garanteix com a màxim UNA fila (verificat contra la BD: 0 claus
        de 5 columnes amb més d'una fila), o sigui que **l'eix sol cura el 500**.
        """
        from fhort.models_app.views import _write_base
        self._dues_peces(segona_activa=False)
        _write_base(self.model, self.pom, 33.0, self.user, 'test', garment=SEGONA)
        self.assertEqual(self._valors(), {MARE: 100.0, SEGONA: 33.0})
        self.assertEqual(
            BaseMeasurement.objects.filter(model=self.model, pom=self.pom).count(), 2,
            'un lookup amb is_active hauria intentat duplicar la clau única')


class EscalatAjustarTallaPerPecaTest(BaseEscalatF1):
    """La vista sencera: `escalat_ajustar_talla_view` amb dues peces vives."""

    def test_ajustar_la_talla_base_de_la_peca_no_peta_i_no_toca_la_mare(self):
        """🔴 EL SÍMPTOMA DEL TRAM, a la seva vora HTTP: 500 abans, 200 ara."""
        from fhort.models_app.views import escalat_ajustar_talla_view
        self._dues_peces()
        self._sf()
        resp = escalat_ajustar_talla_view(self._req({
            'pom_id': self.pom.id, 'talla': 'S', 'valor': 44.0,
            'capa': EXTERIOR, 'instancia': '', 'garment': SEGONA,
        }), self.model.id)
        self.assertEqual(resp.status_code, 200, getattr(resp, 'data', None))
        self.assertEqual(self._valors(), {MARE: 100.0, SEGONA: 44.0},
                         "la base que s'ha de moure és la de la peça, no la de la mare")

    def test_qui_no_diu_la_peca_segueix_ajustant_la_MARE(self):
        """La compatibilitat de la vora HTTP: el client d'abans d'aquest tram no es mou."""
        from fhort.models_app.views import escalat_ajustar_talla_view
        self._dues_peces()
        self._sf()
        resp = escalat_ajustar_talla_view(self._req({
            'pom_id': self.pom.id, 'talla': 'S', 'valor': 44.0,
            'capa': EXTERIOR, 'instancia': '',
        }), self.model.id)
        self.assertEqual(resp.status_code, 200, getattr(resp, 'data', None))
        self.assertEqual(self._valors(), {MARE: 44.0, SEGONA: 100.0})

    def test_les_linies_de_la_resposta_porten_la_clau_de_LA_PECA(self):
        """Q5 · LA SUPERFÍCIE DE RESPONSE LITERAL. `linies` es construeix sense serializer i
        el seu `id` és `{clau}:{talla}`; `MeasureGrid` hi indexa el buffer de cel·les. Amb
        l'eix cuit a `''`, el refresc d'una fila de la 02 no arribava mai a la seva cel·la:
        l'escriptura es feia, la corba es re-derivava i la pantalla es quedava amb el valor
        vell fins a recarregar. Sense error i sense res a la xarxa que ho digués."""
        from fhort.models_app.views import escalat_ajustar_talla_view
        self._dues_peces()
        self._sf()
        resp = escalat_ajustar_talla_view(self._req({
            'pom_id': self.pom.id, 'talla': 'S', 'valor': 44.0,
            'capa': EXTERIOR, 'instancia': '', 'garment': SEGONA,
        }), self.model.id)
        ids = [l['id'] for l in resp.data['linies']]
        self.assertTrue(
            all(i.startswith(f'{self.pom.id}|{EXTERIOR}||{SEGONA}:') for i in ids),
            f"l'id ha de ser `{{clau}}:{{talla}}` de LA PEÇA ajustada: {ids}")

    def test_loverride_i_el_registre_van_a_la_PECA(self):
        """Els altres dos destins d'escriptura de la vista. El `MeasurementChangeLog` és
        APPEND-ONLY: una fila mal atribuïda aquí no es pot corregir mai."""
        from fhort.models_app.views import escalat_ajustar_talla_view
        self._dues_peces()
        self._sf()   # cap regla per a la 02 → hereta la de la mare, però és LINEAR i propaga
        # STEP a la peça: força la branca d'OVERRIDE puntual (la que escriu Override + log).
        ModelGradingRule.objects.update_or_create(
            model=self.model, pom=self.pom, garment=SEGONA,
            defaults={'logica': 'STEP', 'increment': 0, 'actiu': True})
        resp = escalat_ajustar_talla_view(self._req({
            'pom_id': self.pom.id, 'talla': 'M', 'valor': 61.0,
            'capa': EXTERIOR, 'instancia': '', 'garment': SEGONA,
        }), self.model.id)
        self.assertEqual(resp.status_code, 200, getattr(resp, 'data', None))
        self.assertEqual(
            list(ModelGradingOverride.objects.filter(model=self.model)
                 .values_list('garment', flat=True)),
            [SEGONA], "l'override ha de néixer a la peça, no a la mare")
        self.assertEqual(
            list(MeasurementChangeLog.objects.filter(model=self.model, context='manual')
                 .values_list('garment', flat=True)),
            [SEGONA], 'el registre append-only ha de dir de quina peça parlava')

    def test_la_peca_es_propaga_amb_LA_SEVA_llei(self):
        """🚨 Q1-bis · EL TEST QUE NOMÉS PROVA RES AMB DIVERGÈNCIA SEMBRADA.

        La mare gradua a +2/talla i la peça 02 a +10/talla. S'ancora la talla M de la 02 a
        60: `propaga_ancoratges` ha de derivar la base (S) amb el delta de LA PEÇA, no amb
        el de la mare. Amb la llei de la mare la base sortiria 58; amb la seva, 50.

        Mentre `_write_base` petava, aquest defecte quedava TAPAT pel 500. Aquest assert és
        el que impedeix que tancar F1 el deixi viu i mut.
        """
        from fhort.models_app.views import escalat_ajustar_talla_view
        self._dues_peces()
        self._sf(delta_mare=2.0, delta_segona=10.0)
        resp = escalat_ajustar_talla_view(self._req({
            'pom_id': self.pom.id, 'talla': 'M', 'valor': 60.0,
            'capa': EXTERIOR, 'instancia': '', 'garment': SEGONA,
        }), self.model.id)
        self.assertEqual(resp.status_code, 200, getattr(resp, 'data', None))
        self.assertTrue(resp.data['propagat'], resp.data)
        self.segona.refresh_from_db()
        self.assertEqual(
            float(self.segona.base_value_cm), 50.0,
            'la base s\'ha derivat amb el delta de la MARE (+2 → 58) en comptes del de la '
            'peça (+10 → 50): la vista encara llegeix _load_grading_rules')
