"""SET-2/T10 — LES CÒPIES TRANSPORTEN LES PECES, no només el codi que hi apunta.

`BaseMeasurement.garment` ja viatjava des de T5 («la còpia COPIA»), i `clone_model_for_qa`
el porta sol perquè copia amb `pk=None` genèric. El que no viatjava enlloc era la fila que
dona SENTIT a aquell codi: `ModelGarment`.

EL DANY, i és per ABSÈNCIA com tota aquesta família: el model copiat es quedava amb mesures
de la peça '02' i CAP peça '02'. Codis orfes — i amb ells els overrides de run, joc de
graduació i talla base d'aquella peça, que en desaparèixer queien silenciosament als del
model. La còpia semblava correcta i el destí graduava la calceta amb l'escala del cos.

I una conseqüència pròpia de cada camí:
  · `copiar_de_model_view` — a més, sembrava les regles residents NOMÉS de la mare: les peces
    del model copiat naixien mudes (cap regla → llei de cel·la absent → cap cel·la emesa).
  · `clone_model_for_qa` — el veredicte «grading equivalent» del banc de QA compararia dues
    coses que no ho són, i pel motiu equivocat.

Amb les comportes de T2 vives cap dels dos casos es pot construir amb mesures; les PECES, en
canvi, sí que es poden crear (`ModelGarment` no té comporta de garment: té la de D3, que
prohibeix el codi buit). Per això aquests tests no necessiten alçar res.
"""
import datetime

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.models_app.models import BaseMeasurement, Model, ModelGarment
from fhort.models_app.views import copiar_de_model_view
from fhort.pom.models import (GradingRule, GradingRuleSet, POMMaster, SizeDefinition,
                              SizeSystem)


class _T10CopiaBase(TenantTestCase):

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
        self.user = get_user_model().objects.create(username='t10')
        self.ss = SizeSystem.objects.create(codi='SS_T10C', nom='SS', base_unit='ALPHA')
        self.ss_mesos = SizeSystem.objects.create(codi='SS_MESOS_C', nom='Mesos',
                                                  base_unit='ALPHA')
        for i, et in enumerate(['S', 'M', 'L']):
            SizeDefinition.objects.create(size_system=self.ss, etiqueta=et, ordre=i)
        self.pom = POMMaster.objects.create(codi_client='CH', nom_client='Pit')
        self.rs = GradingRuleSet.objects.create(nom='RS origen')
        self.src = self._model('SRC-T10', 1, rule_set=self.rs)
        self.dst = self._model('DST-T10', 2)
        self.factory = APIRequestFactory()

    def _model(self, codi, seq, rule_set=None):
        return Model.objects.create(
            codi_intern=codi, codi_tenant='TST', any=2026, sequencial=seq,
            nom_prenda='Pijama', size_system=self.ss, size_run_model='S·M·L',
            base_size_label='M', grading_rule_set=rule_set,
        )

    def _peces(self, model):
        return {p.codi: p for p in ModelGarment.objects.filter(model=model)}


class LaCopiaEntreModelsTransportaLesPecesTest(_T10CopiaBase):

    def _copia(self, **flags):
        cos = {'copy_run': True, 'copy_values': True, 'copy_grading': True,
               'copy_files': False}
        cos.update(flags)
        req = self.factory.post('/copiar/', cos, format='json')
        force_authenticate(req, user=self.user)
        return copiar_de_model_view(req, self.dst.id, self.src.id)

    def test_la_peca_viatja_amb_els_seus_overrides(self):
        """El pin del dany. Els overrides van SENCERS: el que la peça declara, i el que
        hereta (NULL), que és una declaració tan copiable com l'altra."""
        ModelGarment.objects.create(
            model=self.src, codi='02', nom='Pantaló', ordre=1,
            size_system=self.ss_mesos, size_run_model='3M·6M', base_size_label='6M')

        resp = self._copia()
        self.assertEqual(resp.status_code, 200, getattr(resp, 'data', None))

        peces = self._peces(self.dst)
        self.assertIn('02', peces, 'la peça no ha viatjat: el destí té codis orfes')
        p = peces['02']
        self.assertEqual((p.nom, p.ordre), ('Pantaló', 1))
        self.assertEqual(p.size_system_id, self.ss_mesos.id)
        self.assertEqual((p.size_run_model, p.base_size_label), ('3M·6M', '6M'))
        # El joc: la peça no en declara cap → NULL, que vol dir «hereta». Copiar-lo com a
        # valor el convertiria en una declaració.
        self.assertIsNone(p.grading_rule_set_id)

    def test_una_segona_copia_ACTUALITZA_la_peca_i_no_peta(self):
        """Idempotència per `(model, codi)`, com la unicitat."""
        ModelGarment.objects.create(model=self.src, codi='02', nom='Pantaló')
        self._copia()
        ModelGarment.objects.filter(model=self.src, codi='02').update(nom='Pantaló curt')

        resp = self._copia()

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(self._peces(self.dst)), 1)
        self.assertEqual(self._peces(self.dst)['02'].nom, 'Pantaló curt')

    def test_una_peca_que_NOMES_te_el_desti_no_sesborra(self):
        """Aquesta porta és MUDA —no demana permís—: esborrar una peça deixaria òrfenes les
        SEVES mesures al destí. El que no sap desfer, no ho desfà."""
        ModelGarment.objects.create(model=self.dst, codi='03', nom='Caputxa del destí')
        ModelGarment.objects.create(model=self.src, codi='02', nom='Pantaló')

        self._copia()

        self.assertEqual(sorted(self._peces(self.dst)), ['02', '03'])

    def test_CAS_DE_CONTROL_un_model_sense_peces_no_en_fabrica_cap(self):
        """El 100% del corpus d'avui: la còpia ha de quedar exactament com abans de T10."""
        resp = self._copia()

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self._peces(self.dst), {})

    def test_sense_cap_flag_que_les_anomeni_les_peces_NO_viatgen(self):
        """Només `copy_files`: un croquis no parla de peces."""
        ModelGarment.objects.create(model=self.src, codi='02', nom='Pantaló')

        self._copia(copy_run=False, copy_values=False, copy_grading=False, copy_files=True)

        self.assertEqual(self._peces(self.dst), {})


class ElClonDeQaTransportaLesPecesTest(_T10CopiaBase):

    def test_el_clon_de_qa_porta_les_peces(self):
        from django.core.management import call_command
        from django.db import connection
        from fhort.accounts.models import UserProfile
        UserProfile.objects.get_or_create(
            user=self.user, defaults={'nom_complet': 'QA T10', 'rol_nom': 'QA'})
        ModelGarment.objects.create(
            model=self.src, codi='02', nom='Pantaló', ordre=1, size_run_model='3M·6M')
        # El clon RE-GENERA el grading (no el copia), i el motor avorta si el model no té
        # cap llei: cal una mesura base i una regla al joc, o el command peta amb
        # «no té regles de grading» abans d'arribar a les peces.
        BaseMeasurement.objects.create(
            model=self.src, pom=self.pom, base_value_cm=100.0, ordre=1)
        GradingRule.objects.create(
            rule_set=self.rs, pom=self.pom,
            talla_base=SizeDefinition.objects.get(size_system=self.ss, etiqueta='M'),
            logica='LINEAR', increment=1.0, increment_base=1.0, actiu=True)

        # `--assignee` és obligatori (el clon en fa responsable del model i de la tasca) i
        # l'schema és el del tenant de proves, no un literal: el command entra amb
        # `schema_context` pel seu compte.
        call_command('clone_model_for_qa', schema=connection.schema_name,
                     source=self.src.id, assignee=self.user.username,
                     tag='[QA-T10]', verbosity=0)

        clon = Model.objects.filter(nom_prenda__startswith='[QA-T10]').first()
        self.assertIsNotNone(clon, 'el clon no s\'ha creat: el fixture no serveix')
        peces = self._peces(clon)
        self.assertIn('02', peces, 'el clon té mesures amb codi de peça i cap peça')
        self.assertEqual(peces['02'].size_run_model, '3M·6M')
        # I la peça és del CLON, no un àlies de la de l'origen.
        self.assertNotEqual(peces['02'].pk, self._peces(self.src)['02'].pk)
