"""SET-2/T2-bis — `ModelGarment`: l'entitat que D5 pressuposava, i la seva resolució en UN punt.

Aquest fitxer és, amb el docstring de `garment_views`, EL CONTRACTE que T7 Fase B llegirà. Un
brief no es re-verifica; un test sí.

QUÈ ES FIXA AQUÍ, i cada cosa pel seu motiu:
  · D3 · LA MARE NO TÉ FILA. La comporta CHECK ho impedeix a Postgres, no a un formulari:
    materialitzar-la duplicaria la font de veritat (el run i la talla base de la mare ja
    viuen als camps de `Model`) i obriria la pregunta «quin dels dos mana» a cada lectura.
  · D5 · NULL VOL DIR «HERETA», i el predicat és `is None`, no la falsedat. Amb `or` —tal com
    la frase `garment.X or model.X` es llegeix literalment— una peça no podria mai declarar un
    valor buit distint del de la mare.
  · EL CONTRACTE de `GET /models/<id>/peces/`: valor EFECTIU + flag d'herència PER CAMP. Els
    dos camps calen: `heretat` diu D'ON VE el valor, no si n'hi ha. Una pantalla que editi una
    peça ha de poder distingir «hereta S·M·L» de «declara S·M·L».
"""
import datetime

from django.contrib.auth import get_user_model
from django.db import IntegrityError, connection, transaction
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.models_app.garment_views import peces_del_model_view
from fhort.models_app.models import Model, ModelGarment
from fhort.models_app.services_garment import GARMENT_MARE, valor_efectiu
from fhort.pom.models import GradingRuleSet, SizeDefinition, SizeSystem


class _T2bisBase(TenantTestCase):

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
        self.user = get_user_model().objects.create(username='t2bis')
        self.ss = SizeSystem.objects.create(codi='SS_ALFA', nom='Alfa', base_unit='ALPHA')
        for i, et in enumerate(['S', 'M', 'L']):
            SizeDefinition.objects.create(size_system=self.ss, etiqueta=et, ordre=i)
        self.ss_mesos = SizeSystem.objects.create(codi='SS_MESOS', nom='Mesos', base_unit='ALPHA')
        self.rs = GradingRuleSet.objects.create(nom='RS mare')
        self.model = Model.objects.create(
            codi_intern='TST-T2BIS', codi_tenant='TST', any=2026, sequencial=1,
            nom_prenda='Pijama', size_system=self.ss, grading_rule_set=self.rs,
            size_run_model='S·M·L', base_size_label='M',
        )
        self.factory = APIRequestFactory()

    def _peces(self):
        req = self.factory.get('/peces/')
        force_authenticate(req, user=self.user)
        return peces_del_model_view(req, self.model.id).data


class LaMareNoTeFilaTest(_T2bisBase):
    """D3, escrita a Postgres."""

    def test_una_peca_amb_codi_buit_es_REFUSADA_per_la_base_de_dades(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            ModelGarment.objects.create(model=self.model, codi=GARMENT_MARE)

    def test_dues_peces_amb_el_mateix_codi_al_mateix_model_es_refusen(self):
        ModelGarment.objects.create(model=self.model, codi='02')
        with self.assertRaises(IntegrityError), transaction.atomic():
            ModelGarment.objects.create(model=self.model, codi='02')

    def test_un_model_sense_peces_NO_en_te_cap_fila(self):
        """El 100% del corpus d'avui. La mare no s'ha materialitzat enlloc."""
        self.assertEqual(ModelGarment.objects.filter(model=self.model).count(), 0)

    def test_qui_refusa_el_codi_buit_es_LA_COMPORTA_i_no_una_altra_cosa(self):
        """EL CONTROL QUE TRENCA LA COINCIDÈNCIA, i el primer intent de veure'l vermell no
        valia: retirar la comporta amb un `ALTER TABLE` des de fora del test no fa res, perquè
        l'esquema del tenant es crea i es destrueix a cada correguda. La prova ha de retirar-la
        DINS, en un savepoint que sempre es desfà.

        Sense això, el test de sobre és compatible amb un món on el codi buit el refusa
        qualsevol altra cosa (una validació de Django, la unicitat, un `default`) — i llavors
        D3 no estaria escrita a Postgres, que és on ha d'estar.
        """
        sid = transaction.savepoint()
        try:
            with connection.cursor() as cur:
                cur.execute(
                    f'ALTER TABLE "{connection.schema_name}"."models_app_modelgarment" '
                    f'DROP CONSTRAINT "models_app_modelgarment_codi_no_buit"')
            # Amb la comporta fora, la fila de la mare ENTRA: la protecció era la comporta.
            peca = ModelGarment.objects.create(model=self.model, codi=GARMENT_MARE)
            self.assertEqual(peca.codi, GARMENT_MARE)
        finally:
            transaction.savepoint_rollback(sid)


class LaResolucioEsPerNULLITAT_NoPerFalsedatTest(_T2bisBase):
    """D5, i el punt on `or` i `is None` divergeixen."""

    def test_NULL_hereta_del_model(self):
        peca = ModelGarment.objects.create(model=self.model, codi='02')

        self.assertEqual(valor_efectiu(self.model, peca, 'size_run_model'), 'S·M·L')
        self.assertEqual(valor_efectiu(self.model, peca, 'base_size_label'), 'M')
        self.assertEqual(valor_efectiu(self.model, peca, 'size_system'), self.ss)
        self.assertEqual(valor_efectiu(self.model, peca, 'grading_rule_set'), self.rs)

    def test_un_valor_propi_MANA_sobre_el_del_model(self):
        """El cas de domini que D4 declara: una calceta per mesos dins d'un model per talla
        alfa. Si l'override no manés, el motor la graduaria amb una escala que no és la seva."""
        peca = ModelGarment.objects.create(
            model=self.model, codi='02', size_system=self.ss_mesos,
            size_run_model='3M·6M·9M', base_size_label='6M')

        self.assertEqual(valor_efectiu(self.model, peca, 'size_system'), self.ss_mesos)
        self.assertEqual(valor_efectiu(self.model, peca, 'size_run_model'), '3M·6M·9M')
        self.assertEqual(valor_efectiu(self.model, peca, 'base_size_label'), '6M')

    def test_una_CADENA_BUIDA_declarada_NO_cau_al_model(self):
        """🔑 EL PIN QUE SEPARA `is None` DE `or`, i és el motiu pel qual el predicat no és el
        de la frase del brief. Una peça que declara «cap run» ha de poder dir-ho: amb `or`,
        `''` és fals i el valor de la mare tornaria per la porta del darrere, de manera que la
        peça quedaria muda i el motor li aplicaria una escala que ningú li ha assignat."""
        peca = ModelGarment.objects.create(model=self.model, codi='02', size_run_model='')

        self.assertEqual(valor_efectiu(self.model, peca, 'size_run_model'), '')

    def test_la_MARE_torna_sempre_els_valors_del_model(self):
        self.assertEqual(valor_efectiu(self.model, None, 'size_run_model'), 'S·M·L')
        self.assertEqual(valor_efectiu(self.model, None, 'size_system'), self.ss)


class ElContracteDeLendpointTest(_T2bisBase):
    """El que T7 Fase B llegirà. Si això canvia, la pantalla es trenca."""

    def test_un_model_duna_sola_prenda_torna_NOMES_la_mare(self):
        dades = self._peces()

        self.assertIs(dades['te_mes_duna_peca'], False)
        self.assertEqual(len(dades['peces']), 1)
        mare = dades['peces'][0]
        self.assertEqual((mare['codi'], mare['es_mare'], mare['id']), (GARMENT_MARE, True, None))
        self.assertEqual(mare['nom'], 'Pijama')

    def test_la_mare_no_hereta_de_ningu(self):
        """No és un cas especial tolerat: un valor no hereta d'ell mateix."""
        mare = self._peces()['peces'][0]

        for camp in ModelGarment.CAMPS_HERETABLES:
            self.assertIs(mare[camp]['heretat'], False, camp)

    def test_cada_camp_porta_el_valor_EFECTIU_i_diu_si_lhereta(self):
        ModelGarment.objects.create(
            model=self.model, codi='02', nom='Pantaló', ordre=1, size_run_model='S·M')

        peca = self._peces()['peces'][1]

        self.assertEqual((peca['codi'], peca['nom'], peca['es_mare']), ('02', 'Pantaló', False))
        # Declarat per la peça → seu, i ho diu.
        self.assertEqual(peca['size_run_model'], {'valor': 'S·M', 'etiqueta': 'S·M',
                                                  'heretat': False})
        # NULL → el del model, amb el valor JA RESOLT i la marca d'herència.
        self.assertEqual(peca['base_size_label'], {'valor': 'M', 'etiqueta': 'M',
                                                   'heretat': True})
        # Els FK viatgen per PK, i l'etiqueta és per pintar (no és identitat).
        self.assertEqual(peca['size_system']['valor'], self.ss.pk)
        self.assertIs(peca['size_system']['heretat'], True)

    def test_la_mare_va_SEMPRE_primera_i_les_peces_per_ordre(self):
        ModelGarment.objects.create(model=self.model, codi='03', ordre=2)
        ModelGarment.objects.create(model=self.model, codi='02', ordre=1)

        dades = self._peces()

        self.assertIs(dades['te_mes_duna_peca'], True)
        self.assertEqual([p['codi'] for p in dades['peces']], [GARMENT_MARE, '02', '03'])

    def test_un_camp_sense_valor_enlloc_viatja_com_a_null_no_com_a_absent(self):
        """Un model sense joc de graduació: el camp hi és, amb `valor: None`. Una clau absent
        obligaria el client a distingir «no ho sé» de «no n'hi ha», que és el defecte que la
        llei del vocabulari (F22) ja va tancar en una altra superfície."""
        self.model.grading_rule_set = None
        self.model.save(update_fields=['grading_rule_set'])
        ModelGarment.objects.create(model=self.model, codi='02')

        peca = self._peces()['peces'][1]

        self.assertEqual(peca['grading_rule_set'],
                         {'valor': None, 'etiqueta': '', 'heretat': True})

    def test_un_model_inexistent_dona_404_i_no_peta(self):
        req = self.factory.get('/peces/')
        force_authenticate(req, user=self.user)
        self.assertEqual(peces_del_model_view(req, 10 ** 9).status_code, 404)


class ElGarmentTypeItemNoHiEsTest(_T2bisBase):
    """DECISIÓ REPORTADA, fixada perquè no torni per inèrcia.

    El brief demanava `garment_type_item` «nullable i sense cap lector». Un camp sense lector
    és la bastida que aquest sprint ha après a no construir —la clau `garment` de
    `base-measurements/` es va revertir el 10/08 amb aquest argument literal— i, a més, la
    decisió de domini és que el GTI NO baixa a la peça: la columna codificaria una capacitat
    que el domini nega. Si algun dia hi ha de baixar, és una migració d'una línia.
    """

    def test_modelgarment_no_te_garment_type_item(self):
        camps = {f.name for f in ModelGarment._meta.get_fields()}
        self.assertNotIn('garment_type_item', camps)
        self.assertNotIn('garment_type_item', ModelGarment.CAMPS_HERETABLES)
