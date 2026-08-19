"""SET-2/F1 · CONCERN 1 — EL CONTRACTE D'ESCRIPTURA SAP DIR LA PEÇA (2026-08-17).

Substrat: `docs/diagnosis/DIAGNOSI_F1_ESCRIPTURA_GARMENT.md`. F1 és l'últim tram de la
família de predicats de `garment` colats: F5/F5+/F7 van tancar les LECTURES i la poda;
aquí es tanca **l'ESCRIPTURA**. Aquest fitxer cobreix la PRIMERA porta, que és
prerequisit de totes les altres: `BaseMeasurementSerializer`.

**El defecte**: `Meta.fields` no declarava `garment`, o sigui que DRF el descartava del
payload. `validate()` SÍ que el consultava des de T5 —i `filterset_fields` ja l'exposava
en lectura—, però `attrs` no en podia portar cap valor. Efecte doble, i tots dos muts:

  · una fila de la peça 02 **NEIXIA A LA MARE**;
  · i si la mare ja hi era, el guard la denunciava com a **duplicada (400 FALS)**.

Crear una mesura per peça era, per tant, **impossible per API** — encara que la pantalla
ho oferís.

⚠️ **LLEI S27** — un camp fora de `Meta.fields` passa `manage.py check` VERD i falla en
runtime (cas `customer_language`). Per això aquests tests **EXERCEIXEN** el serializer amb
crides reals i no miren `Meta` per introspecció.

⚠️ AQUÍ NO HI HA `comportes_garment_alcades`, i és a posta: les comportes
`*_garment_gate_set2` **ja no existeixen** (migració `0084_set2_12_retirada_comportes_garment`),
el `DROP CONSTRAINT IF EXISTS` és un no-op, i el `savepoint_rollback` del `finally`
s'enduria els fixtures d'aquest fitxer.
"""
import datetime

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase

from fhort.models_app.models import BaseMeasurement, Model
from fhort.models_app.serializers import BaseMeasurementSerializer
from fhort.pom.models import POMMaster

MARE = ''
SEGONA = '02'


class BaseF1(TenantTestCase):
    """Fixture comuna: un model amb una mesura a la MARE i una peça `02` viva."""

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
        self.model = Model.objects.create(
            codi_intern='TST-F1', codi_tenant='TST', any=2026, sequencial=1,
            temporada='SS26', size_run_model='S·M·L', base_size_label='M',
        )
        self.user = get_user_model().objects.create_user(
            username='f1@test.cat', email='f1@test.cat', password='x')

    def _mesura(self, garment=MARE, valor=100.0, nom='A', activa=True):
        return BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=valor, ordre=1,
            nom_fitxa=nom, garment=garment, is_active=activa)


class SerializerAcceptaLEixTest(BaseF1):
    """CONCERN 1 · El contracte d'escriptura de `BaseMeasurement` ha de saber dir la peça.

    LLEI S27 — aquests dos tests EXERCEIXEN el serializer (no miren `Meta.fields` per
    introspecció): un camp que no és a `fields` passa `manage.py check` verd i falla en
    runtime, que és exactament com va entrar el cas `customer_language`.
    """

    def test_una_fila_nova_de_la_PECA_neix_amb_el_seu_eix_i_no_a_la_mare(self):
        """🔴 EL VERMELL: sense `garment` a `Meta.fields`, DRF el descarta i la fila
        neix a la MARE. Ningú peta —es desa una fila perfectament vàlida— i la mesura
        de la peça 02 simplement no existeix."""
        ser = BaseMeasurementSerializer(data={
            'model': self.model.id, 'pom': self.pom.id,
            'capa': 'exterior', 'instancia': '', 'garment': SEGONA,
            'base_value_cm': '42.00', 'origen': 'TEMPLATE', 'nom_fitxa': 'CH',
        })
        self.assertTrue(ser.is_valid(), ser.errors)
        bm = ser.save(created_by=self.user)
        self.assertEqual(
            bm.garment, SEGONA,
            'La fila de la peça 02 ha nascut a la MARE: el serializer ha descartat '
            "l'eix perquè no és a Meta.fields.")

    def test_crear_la_germana_de_la_peca_amb_la_MARE_viva_no_es_un_duplicat(self):
        """🔴 EL 400 FALS: amb la mare viva, `validate()` comparava contra `garment=''`
        (l'`attrs` no en podia portar cap altre valor) i denunciava com a duplicada una
        fila d'UNA ALTRA PEÇA. El camí de crear mesures per peça quedava tancat al
        BACKEND encara que la pantalla l'oferís."""
        self._mesura(garment=MARE)
        ser = BaseMeasurementSerializer(data={
            'model': self.model.id, 'pom': self.pom.id,
            'capa': 'exterior', 'instancia': '', 'garment': SEGONA,
            'base_value_cm': '42.00', 'origen': 'TEMPLATE', 'nom_fitxa': 'CH',
        })
        self.assertTrue(
            ser.is_valid(),
            f'400 FALS: la mare no és un duplicat de la peça 02 → {ser.errors}')
        self.assertEqual(ser.save(created_by=self.user).garment, SEGONA)

    def test_el_duplicat_de_DEBO_dins_de_la_MATEIXA_peca_segueix_barrat(self):
        """El guard no s'ha d'afluixar: dues files amb els QUATRE eixos iguals segueixen
        sent un duplicat, i el 400 aquí és el CORRECTE (clau única de la BD:
        `(model, pom, capa, instancia, garment)`).

        📌 LA FORMA DE L'ERROR HA CANVIAT DE LLOC, i val la pena dir-ho: amb només 4 de
        les 5 columnes exposades, DRF no podia construir el seu `UniqueTogetherValidator`
        i l'únic guard era el `validate()` d'aquest serializer, que denunciava a
        `errors['instancia']`. En completar el conjunt, DRF el genera sol i respon a
        `non_field_errors` ABANS d'arribar a `validate()`. La LLEI és la mateixa i el
        rebuig també; el que es prova aquí és el rebuig, no on cau la cadena.
        Cap consumidor del front hi depenia (els camins de presa fan `.catch(() => {})`).
        """
        self._mesura(garment=SEGONA)
        ser = BaseMeasurementSerializer(data={
            'model': self.model.id, 'pom': self.pom.id,
            'capa': 'exterior', 'instancia': '', 'garment': SEGONA,
            'base_value_cm': '50.00', 'nom_fitxa': 'CH',
        })
        self.assertFalse(ser.is_valid(), 'un duplicat real ha de ser rebutjat')
        self.assertIn('únic', str(ser.errors), f'el motiu ha de dir-ho: {ser.errors}')

    def test_moure_una_fila_de_CAPA_segueix_funcionant_amb_un_PATCH_parcial(self):
        """🚧 REGRESSIÓ D'AQUEST CANVI, i per això té banc propi.

        Completar el conjunt únic activa el `UniqueTogetherValidator` de DRF, que és un
        validador de SERIALITZADOR: entra a tota escriptura, també a les PARCIALS. El camí
        viu `presaPortes.onIdentitat` (moure una mesura de capa des de la graella) és un
        `PATCH {capa}` i prou — si el validador exigís els altres quatre camps al payload,
        aquest gest quedaria trencat amb un 400 sobre una escriptura que abans passava.
        """
        bm = self._mesura(garment=SEGONA)
        ser = BaseMeasurementSerializer(bm, data={'capa': 'folre'}, partial=True)
        self.assertTrue(ser.is_valid(), f'PATCH parcial trencat: {ser.errors}')
        desada = ser.save()
        self.assertEqual(desada.capa, 'folre')
        self.assertEqual(desada.garment, SEGONA, "el PATCH no ha de moure la fila de peça")

    def test_qui_no_diu_lEIX_segueix_rebent_la_MARE(self):
        """La compatibilitat, que és la meitat del contracte: el client que no en diu res
        —el 100% dels d'abans d'aquest tram— ha de seguir escrivint a la mare."""
        ser = BaseMeasurementSerializer(data={
            'model': self.model.id, 'pom': self.pom.id,
            'capa': 'exterior', 'instancia': '', 'base_value_cm': '10.00',
            'nom_fitxa': 'CH',
        })
        self.assertTrue(ser.is_valid(), ser.errors)
        self.assertEqual(ser.save(created_by=self.user).garment, MARE)
