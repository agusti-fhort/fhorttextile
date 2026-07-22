"""D1 · PROPOSTA DE PROMOCIÓ — cap fila llegible es perd en silenci (Agus 2026-07-22).

El contenidor de client és INTOCABLE per a escriptura automàtica (llei M3). Un import que
troba POMs que el catàleg no cobreix (`amplia`) o que hi divergeixen (`conflicte`) els desa
al MODEL —base + overrides per-talla— i n'obre una PROPOSTA: promocionar-los al catàleg és
una decisió humana, per POM.

Abans, aquests POMs generaven dos avisos de text lliure que no arribaven enlloc (el front
descarta `grading_avisos`; cap serialitzador exposa `session.avisos`). La fila s'havia
desat, però ningú no ho sabia. Aquests tests fixen les dues meitats: que la proposta
EXISTEIX i és estructurada, i que aplicar-la fa el que promet.
"""
import datetime

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.models_app.extraction_views import promocionar_poms_view
from fhort.models_app.models import (
    Model, ModelGradingOverride, Watchpoint,
)
from fhort.models_app.services import (
    PROMOCIO_CODI, PROMOCIO_NOMES_MODEL, PROMOCIO_PROMOCIONAT,
    proposta_promocio, resum_proposta_promocio,
)
from fhort.pom.models import (
    GradingRule, GradingRuleSet, POMMaster, SizeDefinition, SizeSystem,
)


def _spec(pom, base_def_id, **kw):
    base = dict(pom_id=pom.id, pom=pom, talla_base_id=base_def_id, logica='LINEAR',
                increment=0, valors_step=None, increment_base=0.25,
                increment_break=None, talla_break_label=None, talla_break_pos=None)
    base.update(kw)
    return base


class _D1Base(TenantTestCase):

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
        from fhort.accounts.models import UserProfile
        self.user = get_user_model().objects.create(username='d1')
        self.profile, _ = UserProfile.objects.get_or_create(
            user=self.user, defaults={'nom_complet': 'D1', 'rol_nom': 'admin'})

        self.ss = SizeSystem.objects.create(codi='SS_D1', nom='SS D1', base_unit='ALPHA')
        for i, et in enumerate(['XS', 'S', 'M', 'L']):
            SizeDefinition.objects.create(size_system=self.ss, etiqueta=et, ordre=i)
        # `GradingRule.talla_base` és NOT NULL: la regla del catàleg sempre neix ancorada.
        self.base_def = SizeDefinition.objects.get(size_system=self.ss, etiqueta='S')

        self.pom_nou = POMMaster.objects.create(codi_client='D1', nom_client='Sleeve')
        self.pom_div = POMMaster.objects.create(codi_client='F', nom_client='Chest')

        self.model = Model.objects.create(
            codi_intern='TST-D1', codi_tenant='TST', any=2026, sequencial=1,
            nom_prenda='Test', size_system=self.ss, size_run_model='XS·S·M·L',
            base_size_label='S',
        )
        self.container = GradingRuleSet.objects.create(
            nom='Contenidor de prova', size_system=self.ss, actiu=True,
            origen=GradingRuleSet.ORIGEN_CLIENT_RUN)
        # El catàleg ja té el POM divergent, amb una forma DIFERENT de la de la fitxa.
        self.regla_div = GradingRule.objects.create(
            rule_set=self.container, pom=self.pom_div, talla_base=self.base_def,
            logica='LINEAR', increment=0, increment_base=0.50, actiu=True)

        self.cls = {
            'sembra': [],
            'amplia': [_spec(self.pom_nou, self.base_def.id)],
            'conflicte': [{
                'pom_id': self.pom_div.id, 'pom_codi': 'F',
                'spec_fitxa': _spec(self.pom_div, self.base_def.id, increment_base=0.25),
                'spec_container': {}, 'regla_container_id': self.regla_div.id,
                'detall': 'forma difereix (contenidor ib=0.5 vs fitxa ib=0.25)',
            }],
        }
        # L'estat en què l'import deixa el model: overrides per-talla, catàleg intacte.
        for pom in (self.pom_nou, self.pom_div):
            for label, val in (('XS', 10.0), ('M', 12.0), ('L', 13.0)):
                ModelGradingOverride.objects.create(
                    model=self.model, pom=pom, size_label=label, value_cm=val,
                    created_by=self.profile, motiu='Import W5 — test D1')


class PropostaTest(_D1Base):

    def test_recull_els_dos_buckets_amb_estat_inicial_nomes_model(self):
        p = proposta_promocio(self.cls, self.container, base_def_id=self.base_def.id)
        self.assertEqual(p['codi'], PROMOCIO_CODI)
        self.assertEqual(p['contenidor_id'], self.container.id)
        self.assertEqual({i['bucket'] for i in p['items']}, {'amplia', 'conflicte'})
        self.assertTrue(all(i['estat'] == PROMOCIO_NOMES_MODEL for i in p['items']))

    def test_el_spec_viatja_dins_la_proposta_i_es_serialitzable(self):
        """Promocionar més tard no pot dependre que la ImportSession encara existeixi."""
        import json
        p = proposta_promocio(self.cls, self.container, base_def_id=self.base_def.id)
        json.dumps(p)                                    # cap instància de model a dins
        self.assertNotIn('pom', p['items'][0]['spec'])
        self.assertEqual(p['items'][0]['spec']['increment_base'], 0.25)

    def test_sense_divergencies_no_hi_ha_proposta(self):
        buit = {'sembra': [_spec(self.pom_nou, self.base_def.id)], 'amplia': [], 'conflicte': []}
        self.assertIsNone(
            proposta_promocio(buit, self.container, base_def_id=self.base_def.id))

    def test_el_text_de_reserva_diu_alguna_cosa_sol(self):
        """Sense render de `dades`, el Watchpoint encara ha de ser llegible."""
        txt = resum_proposta_promocio(
            proposta_promocio(self.cls, self.container, base_def_id=self.base_def.id))
        self.assertIn('1 POM(s) que el catàleg no té', txt)
        self.assertIn('1 POM(s) que divergeixen del catàleg', txt)
        self.assertIn("NO s'ha tocat", txt)


class AplicarPromocioTest(_D1Base):

    def setUp(self):
        super().setUp()
        self.factory = APIRequestFactory()
        self.wp = Watchpoint.objects.create(
            model=self.model, created_by=self.profile,
            dades=proposta_promocio(self.cls, self.container, base_def_id=self.base_def.id),
            text='proposta')

    def _post(self, body, model_id=None):
        req = self.factory.post('/promocionar-poms/', body, format='json')
        force_authenticate(req, user=self.user)
        return promocionar_poms_view(req, model_id=model_id or self.model.id)

    def test_res_entra_al_contenidor_sense_demanar_ho(self):
        r = self._post({'watchpoint_id': self.wp.id, 'promocions': []})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['regles_al_contenidor'], 0)
        self.assertEqual(GradingRule.objects.filter(rule_set=self.container).count(), 1)
        self.assertEqual(self.regla_div.increment_base, 0.50)

    def test_promocionar_un_pom_nou_l_afegeix_al_cataleg(self):
        r = self._post({'watchpoint_id': self.wp.id, 'promocions': [self.pom_nou.id]})
        self.assertEqual(r.status_code, 200)
        regla = GradingRule.objects.get(rule_set=self.container, pom=self.pom_nou)
        self.assertEqual(regla.increment_base, 0.25)

    def test_promocionar_esborra_els_overrides_perque_el_model_HERETI(self):
        """Sense això, la regla promocionada no s'aplicaria mai: l'override té prioritat
        sobre qualsevol regla al motor. Semblaria fet i no ho estaria."""
        self.assertEqual(ModelGradingOverride.objects.filter(
            model=self.model, pom=self.pom_nou).count(), 3)
        r = self._post({'watchpoint_id': self.wp.id, 'promocions': [self.pom_nou.id]})
        self.assertEqual(r.data['overrides_esborrats'], 3)
        self.assertFalse(ModelGradingOverride.objects.filter(
            model=self.model, pom=self.pom_nou).exists())
        # El POM NO promocionat conserva els seus.
        self.assertEqual(ModelGradingOverride.objects.filter(
            model=self.model, pom=self.pom_div).count(), 3)

    def test_un_conflicte_promocionat_ACTUALITZA_la_regla_del_cataleg(self):
        self._post({'watchpoint_id': self.wp.id, 'promocions': [self.pom_div.id]})
        self.regla_div.refresh_from_db()
        self.assertEqual(self.regla_div.increment_base, 0.25)

    def test_estat_per_pom_i_watchpoint_obert_mentre_quedi_algu_per_decidir(self):
        r = self._post({'watchpoint_id': self.wp.id, 'promocions': [self.pom_nou.id]})
        estats = {i['pom_id']: i['estat'] for i in r.data['items']}
        self.assertEqual(estats[self.pom_nou.id], PROMOCIO_PROMOCIONAT)
        self.assertEqual(estats[self.pom_div.id], PROMOCIO_NOMES_MODEL)
        self.assertEqual(r.data['watchpoint_estat'], 'open')
        self.wp.refresh_from_db()
        self.assertEqual(self.wp.estat, 'open')          # persistit, no només retornat

    def test_quan_no_queda_ningu_per_decidir_el_watchpoint_es_resol(self):
        r = self._post({'watchpoint_id': self.wp.id,
                        'promocions': [self.pom_nou.id, self.pom_div.id]})
        self.assertEqual(r.data['watchpoint_estat'], 'resolved')
        self.wp.refresh_from_db()
        self.assertEqual(self.wp.estat, 'resolved')
        self.assertIsNotNone(self.wp.resolved_at)

    def test_repetir_la_promocio_es_inofensiu(self):
        """Doble clic o pestanya ranci: s'ignora, no es duplica ni peta."""
        self._post({'watchpoint_id': self.wp.id, 'promocions': [self.pom_nou.id]})
        r = self._post({'watchpoint_id': self.wp.id, 'promocions': [self.pom_nou.id]})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['promocionats'], [])
        self.assertEqual(GradingRule.objects.filter(
            rule_set=self.container, pom=self.pom_nou).count(), 1)

    def test_watchpoint_inexistent_o_d_un_altre_model_es_404(self):
        self.assertEqual(self._post({'watchpoint_id': 999999}).status_code, 404)
        altre = Model.objects.create(
            codi_intern='TST-D1B', codi_tenant='TST', any=2026, sequencial=2,
            nom_prenda='Altre', size_system=self.ss, size_run_model='XS·S·M·L',
            base_size_label='S')
        self.assertEqual(
            self._post({'watchpoint_id': self.wp.id}, model_id=altre.id).status_code, 404)

    def test_un_watchpoint_que_no_es_una_proposta_es_404(self):
        wp_lliure = Watchpoint.objects.create(
            model=self.model, created_by=self.profile, text='avís escrit a mà')
        self.assertEqual(
            self._post({'watchpoint_id': wp_lliure.id}).status_code, 404)
