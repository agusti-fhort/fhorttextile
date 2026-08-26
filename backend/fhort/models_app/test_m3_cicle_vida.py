"""M3 · EL CICLE DE VIDA DEL MODEL — FIT-9 (tres estats) · FIT-10 (tancar) · FIT-11 (reobrir).

El que aquests tests guarden no és que els camps es desin: és que **el tancament sigui un ACTE**
i no una deducció, que amb una ronda oberta el sistema **avisi abans de fer res**, i que quan
finalment ho fa, ho faci **sencer i en un sol moment** (entrega + volta + model).

Convenció del repo: `python manage.py test fhort.models_app.test_m3_cicle_vida` (no pytest).
"""
import datetime

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIClient

from fhort.models_app.models import Model, ModelEstatEsdeveniment
from fhort.models_app.services_cicle import (CicleVidaError, jubilar_model, reobrir_model,
                                             tancar_model)
from fhort.pom.models import GarmentType
from fhort.tasks.models import Customer, Entrega, GarmentTypeItem, ModelTask, Ronda, TaskType
from fhort.tasks.services_r import obrir_ronda


class BaseCicle(TenantTestCase):

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Test Tenant M3'
        tenant.tipologia = 'MARCA'
        tenant.codi_tenant = 'TM3'
        tenant.vat_number = 'X0000000X'
        tenant.tipus_client = 'STANDARD'
        tenant.gratis_fins = datetime.date(2030, 1, 1)
        return tenant

    def setUp(self):
        from fhort.accounts.models import UserProfile

        self.user = get_user_model().objects.create(username='capm3')
        # 🚨 El rol s'escriu sobre `user.profile`, no sobre una còpia: el perfil el crea un
        # signal i `get_or_create` en torna un objecte diferent del que l'usuari ja té cachejat
        # (el mateix parany que va deixar el board buit amb 200 al fitxer d'M3/FASE 0b).
        UserProfile.objects.get_or_create(user=self.user)
        self.prof = self.user.profile
        self.prof.rol_nom = 'manager'      # té CLOSE_GATES; no és admin a posta
        self.prof.save(update_fields=['rol_nom'])

        self.customer = Customer.objects.create(codi='CM3', nom='Client M3')
        gt = GarmentType.objects.create(codi_client='GT3', nom_client='Família M3', grup='TOPS')
        self.item = GarmentTypeItem.objects.create(garment_type=gt, code='item_m3', name='Item M3')
        self.tt_pom, _ = TaskType.objects.get_or_create(
            code='pom', defaults={'name': 'Definició POM', 'fase': 'Dev. tècnic'})
        self.tt_fitxa, _ = TaskType.objects.get_or_create(
            code='tech_sheet', defaults={'name': 'Fitxa tècnica', 'fase': 'Dev. tècnic'})
        self.model = Model.objects.create(
            codi_intern='TM3-SS26-0001', codi_tenant='TM3', any=2026, temporada='SS',
            sequencial=1, customer=self.customer, garment_type_item=self.item, nom_prenda='Peça')

    def _ronda_oberta(self, codes=('pom', 'tech_sheet')):
        """Una volta VIVA amb feina Pending a dins, pel camí normal."""
        return obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, list(codes), profile=self.prof)

    def _client(self):
        c = APIClient(SERVER_NAME=self.get_test_tenant_domain())
        c.force_authenticate(user=self.user)
        return c


class EstatsTest(BaseCicle):
    """FIT-9 — els tres estats, i que el model neixi al tauler."""

    def test_un_model_neix_nou(self):
        self.assertEqual(self.model.estat, Model.ESTAT_NOU)
        self.assertIsNone(self.model.motiu_tancament)
        self.assertIsNone(self.model.data_tancament)

    def test_el_vocabulari_es_exactament_de_tres(self):
        """Si algú hi torna a afegir estats, que sigui amb un test al davant i no de rebot."""
        self.assertEqual([c for c, _ in Model.ESTAT_CHOICES], ['nou', 'acabat', 'jubilat'])


class TancarSenseRondaObertaTest(BaseCicle):
    """FIT-10 — el cas net: no hi ha volta viva i el tancament és un sol acte."""

    def test_tanca_i_persisteix_el_motiu(self):
        entrega = tancar_model(self.model, motiu=Model.MOTIU_TANCAMENT_ACABAT, profile=self.prof)
        self.model.refresh_from_db()
        self.assertIsNone(entrega)                       # sense volta oberta no hi ha res a entregar
        self.assertEqual(self.model.estat, Model.ESTAT_ACABAT)
        self.assertEqual(self.model.motiu_tancament, Model.MOTIU_TANCAMENT_ACABAT)
        self.assertEqual(self.model.data_tancament, datetime.date.today())

    def test_tret_de_cataleg_es_un_motiu_diferent_i_es_distingeix(self):
        tancar_model(self.model, motiu=Model.MOTIU_TANCAMENT_TRET_DE_CATALEG, profile=self.prof)
        self.model.refresh_from_db()
        self.assertEqual(self.model.motiu_tancament, Model.MOTIU_TANCAMENT_TRET_DE_CATALEG)

    def test_deixa_rastre_amb_autor(self):
        tancar_model(self.model, motiu=Model.MOTIU_TANCAMENT_ACABAT, profile=self.prof)
        ev = ModelEstatEsdeveniment.objects.get(model=self.model)
        self.assertEqual((ev.de_estat, ev.a_estat), (Model.ESTAT_NOU, Model.ESTAT_ACABAT))
        self.assertEqual(ev.per_id, self.prof.pk)
        self.assertEqual(ev.motiu, Model.MOTIU_TANCAMENT_ACABAT)

    def test_un_motiu_desconegut_no_tanca_res(self):
        with self.assertRaises(CicleVidaError) as cm:
            tancar_model(self.model, motiu='perque_si', profile=self.prof)
        self.assertEqual(cm.exception.code, 'motiu_invalid')
        self.model.refresh_from_db()
        self.assertEqual(self.model.estat, Model.ESTAT_NOU)

    def test_sense_perfil_no_hi_ha_acte(self):
        """Tancar un model és un acte humà: sense autor no és un acte, és un UPDATE."""
        with self.assertRaises(CicleVidaError) as cm:
            tancar_model(self.model, motiu=Model.MOTIU_TANCAMENT_ACABAT, profile=None)
        self.assertEqual(cm.exception.code, 'no_profile')

    def test_tancar_dues_vegades_es_rebutja(self):
        tancar_model(self.model, motiu=Model.MOTIU_TANCAMENT_ACABAT, profile=self.prof)
        with self.assertRaises(CicleVidaError) as cm:
            tancar_model(self.model, motiu=Model.MOTIU_TANCAMENT_ACABAT, profile=self.prof)
        self.assertEqual(cm.exception.code, 'ja_acabat')
        self.assertEqual(ModelEstatEsdeveniment.objects.count(), 1)

    def test_tancar_no_toca_les_tasques_quan_no_hi_ha_volta_viva(self):
        """El tancament NO és un tancament forçat de feina: sense volta oberta no hi ha FIT-6."""
        t = ModelTask.objects.create(model=self.model, task_type=self.tt_pom, status='Pending')
        tancar_model(self.model, motiu=Model.MOTIU_TANCAMENT_ACABAT, profile=self.prof)
        t.refresh_from_db()
        self.assertEqual(t.status, 'Pending')


class TancarAmbRondaObertaTest(BaseCicle):
    """🚨 EL FLUX ESTRELLA — amb una volta viva, el sistema AVISA i només tanca si es confirma."""

    def test_la_primera_crida_avisa_i_NO_toca_res(self):
        r = self._ronda_oberta()
        with self.assertRaises(CicleVidaError) as cm:
            tancar_model(self.model, motiu=Model.MOTIU_TANCAMENT_ACABAT, profile=self.prof)
        self.assertEqual(cm.exception.code, 'ronda_oberta')
        self.assertEqual(cm.exception.dades['ronda']['seq'], r.seq)
        r.refresh_from_db(); self.model.refresh_from_db()
        self.assertIsNone(r.tancada_el)                       # la volta segueix viva
        self.assertEqual(self.model.estat, Model.ESTAT_NOU)   # i el model, obert
        self.assertFalse(Entrega.objects.exists())            # i no s'ha entregat res

    def test_en_confirmar_ho_fa_TOT_i_en_un_sol_moment(self):
        r = self._ronda_oberta()
        entrega = tancar_model(self.model, motiu=Model.MOTIU_TANCAMENT_ACABAT, profile=self.prof,
                               confirmar_entrega=True, destinatari='Brumà SL',
                               descripcio='fitxa + patró')
        r.refresh_from_db(); self.model.refresh_from_db()
        self.assertEqual(entrega.destinatari, 'Brumà SL')      # 1 · l'entrega, informada (M1)
        self.assertIsNotNone(r.tancada_el)                     # 2 · la volta, tancada (FIT-13)
        self.assertFalse(r.tasques.exclude(status='Done').exists())   # 3 · cap feina viva (FIT-6)
        self.assertEqual(self.model.estat, Model.ESTAT_ACABAT)        # 4 · el model, acabat

    def test_sense_destinatari_no_es_tanca_RES(self):
        """🔒 L'ATOMICITAT, mesurada: M1 refusa una entrega sense destinatari, i aquell rebuig
        ha de deixar la volta viva I el model obert. Si el tancament del model visqués fora de
        la transacció, aquí quedaria un model acabat amb la seva volta oberta a dins."""
        r = self._ronda_oberta()
        with self.assertRaises(CicleVidaError) as cm:
            tancar_model(self.model, motiu=Model.MOTIU_TANCAMENT_ACABAT, profile=self.prof,
                         confirmar_entrega=True, destinatari='')
        self.assertEqual(cm.exception.code, 'entrega_invalida')
        r.refresh_from_db(); self.model.refresh_from_db()
        self.assertIsNone(r.tancada_el)
        self.assertEqual(self.model.estat, Model.ESTAT_NOU)
        self.assertFalse(ModelEstatEsdeveniment.objects.exists())

    def test_una_volta_JA_TANCADA_no_es_un_impediment(self):
        """«Ronda oberta» és `tancada_el IS NULL`, no «existeix una ronda»."""
        r = self._ronda_oberta()
        tancar_model(self.model, motiu=Model.MOTIU_TANCAMENT_ACABAT, profile=self.prof,
                     confirmar_entrega=True, destinatari='X')
        reobrir_model(self.model, profile=self.prof, motiu='torna el client')
        self.model.refresh_from_db()
        self.assertIsNone(tancar_model(self.model, motiu=Model.MOTIU_TANCAMENT_ACABAT,
                                       profile=self.prof))
        self.assertEqual(Entrega.objects.filter(ronda=r).count(), 1)   # no se n'ha inventat cap altra


class TretDeCatalegNoEntregaTest(BaseCicle):
    """🔒 M3 · CODA — **`tret_de_cataleg` NO ESCRIU CAP ENTREGA** (decisió d'Agus).

    FIT-1: l'`Entrega` registra un fet que HA PASSAT —«això s'ha enviat a algú, aquest dia»—, i
    quan el client informa que la peça no es produirà no s'ha enviat res. La volta es tanca
    igual (la feina viva no pot quedar viva en un model acabat), però es tanca **declarant que
    es tanca**, no declarant un enviament que ningú no ha fet."""

    def test_tanca_la_volta_i_la_seva_feina_SENSE_cap_entrega(self):
        r = self._ronda_oberta()
        entrega = tancar_model(self.model, motiu=Model.MOTIU_TANCAMENT_TRET_DE_CATALEG,
                               profile=self.prof, confirmar=True)
        r.refresh_from_db(); self.model.refresh_from_db()
        self.assertIsNone(entrega)                                   # cap acte d'entrega…
        self.assertFalse(Entrega.objects.exists())                   # …ni cap fila
        self.assertIsNotNone(r.tancada_el)                           # la volta, tancada
        self.assertFalse(r.tasques.exclude(status='Done').exists())  # i la feina, tancada (FIT-6)
        self.assertEqual(self.model.estat, Model.ESTAT_ACABAT)
        self.assertEqual(self.model.motiu_tancament, Model.MOTIU_TANCAMENT_TRET_DE_CATALEG)

    def test_i_NO_demana_destinatari(self):
        """El destinatari és de l'acte d'ENTREGA. Sense entrega no hi ha a qui, i exigir-lo
        hauria bloquejat un tancament legítim per un camp que no vol dir res en aquesta via."""
        self._ronda_oberta()
        tancar_model(self.model, motiu=Model.MOTIU_TANCAMENT_TRET_DE_CATALEG,
                     profile=self.prof, confirmar=True, destinatari='')
        self.model.refresh_from_db()
        self.assertEqual(self.model.estat, Model.ESTAT_ACABAT)

    def test_l_avis_diu_quina_pregunta_toca_fer(self):
        """El 409 segueix sent la PREGUNTA, però `requereix_entrega` diu a la cara si ha de
        demanar el destinatari o no: les dues vies no pregunten el mateix."""
        self._ronda_oberta()
        with self.assertRaises(CicleVidaError) as cm:
            tancar_model(self.model, motiu=Model.MOTIU_TANCAMENT_TRET_DE_CATALEG,
                         profile=self.prof)
        self.assertEqual(cm.exception.code, 'ronda_oberta')
        self.assertFalse(cm.exception.dades['requereix_entrega'])
        self.assertIn('sense declarar cap entrega', str(cm.exception))

    def test_la_via_ACABAT_es_queda_com_estava(self):
        """La CODA no toca l'altra via: `acabat` segueix entregant i seguint demanant destinatari."""
        r = self._ronda_oberta()
        with self.assertRaises(CicleVidaError) as cm:
            tancar_model(self.model, motiu=Model.MOTIU_TANCAMENT_ACABAT, profile=self.prof)
        self.assertTrue(cm.exception.dades['requereix_entrega'])
        entrega = tancar_model(self.model, motiu=Model.MOTIU_TANCAMENT_ACABAT, profile=self.prof,
                               confirmar=True, destinatari='Brumà SL')
        self.assertIsNotNone(entrega)
        self.assertEqual(entrega.ronda_id, r.pk)

    def test_el_nom_VELL_del_parametre_segueix_valent(self):
        """`confirmar_entrega` és el que la porta va publicar a M3 i el que els fums d'abans de
        la CODA segueixen enviant: retirar-lo hauria trencat els dos fums sense guanyar res."""
        self._ronda_oberta()
        tancar_model(self.model, motiu=Model.MOTIU_TANCAMENT_TRET_DE_CATALEG,
                     profile=self.prof, confirmar_entrega=True)
        self.model.refresh_from_db()
        self.assertEqual(self.model.estat, Model.ESTAT_ACABAT)

    def test_sense_volta_oberta_les_dues_vies_es_comporten_igual(self):
        """Sense volta viva no hi ha res a tancar ni a entregar: el motiu només es persisteix."""
        tancar_model(self.model, motiu=Model.MOTIU_TANCAMENT_TRET_DE_CATALEG, profile=self.prof)
        self.model.refresh_from_db()
        self.assertEqual(self.model.estat, Model.ESTAT_ACABAT)
        self.assertFalse(Entrega.objects.exists())


class ReobrirTest(BaseCicle):
    """FIT-11 — el model torna a OBERT, i el rastre diu qui, quan i per què."""

    def _acabat(self):
        tancar_model(self.model, motiu=Model.MOTIU_TANCAMENT_ACABAT, profile=self.prof)
        self.model.refresh_from_db()

    def test_reobrir_torna_l_estat_i_neteja_el_tancament(self):
        self._acabat()
        reobrir_model(self.model, profile=self.prof, motiu='el client vol una talla més')
        self.model.refresh_from_db()
        self.assertEqual(self.model.estat, Model.ESTAT_NOU)
        self.assertIsNone(self.model.motiu_tancament)
        self.assertIsNone(self.model.data_tancament)

    def test_el_rastre_no_s_esborra_en_reobrir(self):
        """La història és acumulativa: el tancament segueix escrit després de la reobertura."""
        self._acabat()
        reobrir_model(self.model, profile=self.prof, motiu='defecte a la màniga')
        evs = list(ModelEstatEsdeveniment.objects.filter(model=self.model).order_by('id'))
        self.assertEqual([(e.de_estat, e.a_estat) for e in evs],
                         [('nou', 'acabat'), ('acabat', 'nou')])
        self.assertEqual(evs[1].motiu, 'defecte a la màniga')
        self.assertEqual(evs[1].per_id, self.prof.pk)

    def test_reobrir_un_model_obert_es_rebutja(self):
        with self.assertRaises(CicleVidaError) as cm:
            reobrir_model(self.model, profile=self.prof)
        self.assertEqual(cm.exception.code, 'ja_obert')

    def test_reobrir_NO_obre_cap_ronda_ni_reobre_cap_tasca(self):
        """Reobrir només torna el model al tauler: què es fa a dins es decideix després."""
        t = ModelTask.objects.create(model=self.model, task_type=self.tt_pom, status='Done')
        self._acabat()
        reobrir_model(self.model, profile=self.prof)
        t.refresh_from_db()
        self.assertEqual(t.status, 'Done')
        self.assertFalse(Ronda.objects.filter(model=self.model).exists())


class JubilarTest(BaseCicle):
    """FIT-9 — l'arxiu: només a mà i només des d'`acabat`."""

    def test_un_model_viu_no_es_jubila_de_cop(self):
        with self.assertRaises(CicleVidaError) as cm:
            jubilar_model(self.model, profile=self.prof)
        self.assertEqual(cm.exception.code, 'no_acabat')

    def test_d_acabat_a_jubilat_amb_rastre(self):
        tancar_model(self.model, motiu=Model.MOTIU_TANCAMENT_ACABAT, profile=self.prof)
        jubilar_model(self.model, profile=self.prof, motiu='temporada tancada')
        self.model.refresh_from_db()
        self.assertEqual(self.model.estat, Model.ESTAT_JUBILAT)
        ultim = ModelEstatEsdeveniment.objects.filter(model=self.model).first()
        self.assertEqual((ultim.de_estat, ultim.a_estat), ('acabat', 'jubilat'))

    def test_un_jubilat_es_pot_reobrir(self):
        """Desjubilar és reobrir: no s'inventa cap gest intermedi."""
        tancar_model(self.model, motiu=Model.MOTIU_TANCAMENT_ACABAT, profile=self.prof)
        jubilar_model(self.model, profile=self.prof)
        reobrir_model(self.model, profile=self.prof, motiu='torna a producció')
        self.model.refresh_from_db()
        self.assertEqual(self.model.estat, Model.ESTAT_NOU)

    def test_un_jubilat_no_es_torna_a_tancar(self):
        tancar_model(self.model, motiu=Model.MOTIU_TANCAMENT_ACABAT, profile=self.prof)
        jubilar_model(self.model, profile=self.prof)
        self.model.refresh_from_db()
        with self.assertRaises(CicleVidaError) as cm:
            tancar_model(self.model, motiu=Model.MOTIU_TANCAMENT_ACABAT, profile=self.prof)
        self.assertEqual(cm.exception.code, 'jubilat')


class PortesTest(BaseCicle):
    """LES TRES PORTES — codis de resposta i el gate de govern."""

    def test_post_tancar_amb_ronda_oberta_dona_409_amb_les_dades_de_la_volta(self):
        r = self._ronda_oberta()
        resp = self._client().post(f'/api/v1/models/{self.model.pk}/tancar/',
                                   {'motiu': 'acabat'}, format='json')
        self.assertEqual(resp.status_code, 409, resp.data)
        self.assertEqual(resp.data['code'], 'ronda_oberta')
        self.assertEqual(resp.data['ronda']['seq'], r.seq)

    def test_post_tancar_TRET_DE_CATALEG_no_torna_cap_entrega(self):
        """CODA — per HTTP, la via del catàleg tanca sense entrega i sense demanar destinatari."""
        self._ronda_oberta()
        resp = self._client().post(
            f'/api/v1/models/{self.model.pk}/tancar/',
            {'motiu': 'tret_de_cataleg', 'confirmar': True}, format='json')
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.data['estat'], 'acabat')
        self.assertIsNone(resp.data['entrega'])
        self.assertFalse(Entrega.objects.exists())

    def test_post_tancar_el_409_diu_si_cal_entrega(self):
        self._ronda_oberta()
        resp = self._client().post(f'/api/v1/models/{self.model.pk}/tancar/',
                                   {'motiu': 'tret_de_cataleg'}, format='json')
        self.assertEqual(resp.status_code, 409)
        self.assertFalse(resp.data['requereix_entrega'])

    def test_post_tancar_confirmat_torna_l_estat_i_l_entrega(self):
        self._ronda_oberta()
        resp = self._client().post(
            f'/api/v1/models/{self.model.pk}/tancar/',
            {'motiu': 'acabat', 'confirmar_entrega': True, 'destinatari': 'Brumà SL'},
            format='json')
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.data['estat'], 'acabat')
        self.assertEqual(resp.data['entrega']['destinatari'], 'Brumà SL')
        self.assertEqual(resp.data['rastre']['a'], 'acabat')

    def test_post_reobrir_i_jubilar_van_per_la_seva_porta(self):
        self._client().post(f'/api/v1/models/{self.model.pk}/tancar/',
                            {'motiu': 'acabat'}, format='json')
        resp = self._client().post(f'/api/v1/models/{self.model.pk}/jubilar/', {}, format='json')
        self.assertEqual(resp.data['estat'], 'jubilat')
        resp = self._client().post(f'/api/v1/models/{self.model.pk}/reobrir/',
                                   {'motiu': 'torna'}, format='json')
        self.assertEqual(resp.data['estat'], 'nou')
        self.assertEqual(resp.data['rastre']['motiu'], 'torna')

    def test_un_model_inexistent_dona_404(self):
        resp = self._client().post('/api/v1/models/999999/tancar/', {'motiu': 'acabat'},
                                   format='json')
        self.assertEqual(resp.status_code, 404)

    def test_sense_CLOSE_GATES_la_porta_es_tanca(self):
        """Un tècnic pot entregar una volta (M1, `execute_tasks`) però NO acabar el model:
        acabar-lo tanca la feina viva d'altri i és un acte de govern."""
        self.prof.rol_nom = 'technician'
        self.prof.save(update_fields=['rol_nom'])
        resp = self._client().post(f'/api/v1/models/{self.model.pk}/tancar/',
                                   {'motiu': 'acabat'}, format='json')
        self.assertEqual(resp.status_code, 403)
        self.model.refresh_from_db()
        self.assertEqual(self.model.estat, Model.ESTAT_NOU)

    def test_el_PATCH_generic_ja_no_pot_acabar_un_model(self):
        """🔒 El forat que el cens va trobar: `fields='__all__'` feia `estat` escrivible."""
        self.prof.rol_nom = 'admin'
        self.prof.save(update_fields=['rol_nom'])
        resp = self._client().patch(f'/api/v1/models/{self.model.pk}/',
                                    {'estat': 'acabat'}, format='json')
        self.assertIn(resp.status_code, (200, 202), resp.data)
        self.model.refresh_from_db()
        self.assertEqual(self.model.estat, Model.ESTAT_NOU)   # ignorat, no desat
        self.assertFalse(ModelEstatEsdeveniment.objects.exists())
