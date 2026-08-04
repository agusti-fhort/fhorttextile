"""F4 · l'ordre de la taula de mesures és una DECISIÓ, no el pla de Postgres (2026-08-01).

`measurements_table_view` ordenava `poms_info` només per l'ordre del catàleg, que és de la
CATEGORIA i no del POM: dins d'una categoria tot són empats, i el `sort` de Python és
estable, o sigui que els empats conservaven l'ordre en què Postgres havia tornat les files.
Afegir-hi un `WHERE` va canviar el pla i, amb ell, l'ordre del payload — mateixos POMs,
mateixos ids, un altre ordre. Va ser el motiu de revertir C7.

Ordre decidit per l'Agus: catàleg → capa (exterior primer) → codi del POM. El `slug` de la
capa i l'`id` del POM tanquen la clau perquè sigui TOTAL (el codi no és únic: dos POMMaster
del tenant poden compartir `codi_client`).

Aquests tests fixen l'ordre emès i que les cel·les el segueixin.
"""
import datetime

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.accounts.models import UserProfile
from fhort.fitting.models import GradedSpec, GradingVersion, SizeFitting
from fhort.models_app.models import BaseMeasurement, Model
from fhort.pom.grading_views import measurements_table_view
from fhort.pom.models import POMCategory, POMMaster


class OrdreTaulaMesuresTest(TenantTestCase):

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
        self.user, _ = get_user_model().objects.get_or_create(
            username='qa_f4', defaults={'email': 'qa@f4.test'})
        self.perfil, _ = UserProfile.objects.get_or_create(
            user=self.user, defaults={'nom_complet': 'QA F4', 'rol_nom': 'QA'})
        self.model = Model.objects.create(
            codi_intern='TST-F4', codi_tenant='TST', any=2026, sequencial=1,
            temporada='SS26', size_run_model='S·M·L', base_size_label='M',
        )
        self.cos = POMCategory.objects.create(codi='UPPER', display_order=1)
        self.manega = POMCategory.objects.create(codi='SLEEVE', display_order=2)

        # Es creen a posta en ordre INVERS del que han de sortir: si l'ordre vingués de
        # l'ordre d'inserció (el que passava), el test seria vermell.
        self.sl = self._pom('SL', self.manega)       # categoria 2
        self.wa = self._pom('WA', self.cos)          # categoria 1, codi alt
        self.ch = self._pom('CH', self.cos)          # categoria 1, codi baix
        self.orfe = self._pom('AA', None)            # sense categoria → 999, l'últim

    def _pom(self, codi, categoria):
        return POMMaster.objects.create(
            codi_client=codi, nom_client=f'POM {codi}', categoria=categoria)

    def _taula(self, sf):
        req = APIRequestFactory().get(f'/api/v1/size-fittings/{sf.id}/taula-mesures/')
        force_authenticate(req, user=self.user)
        resp = measurements_table_view(req, sf_id=sf.id)
        if hasattr(resp, 'render'):
            resp.render()
        return resp

    def _sf(self, amb_graduacio):
        # `numero=2`: el model ja neix amb el seu primer SizeFitting (unicitat model+numero).
        sf = SizeFitting.objects.create(model=self.model, numero=2, codi='TST-SF-F4',
                                        tipus='PROTO', creat_per=self.perfil)
        if not amb_graduacio:
            return sf
        gv = GradingVersion.objects.create(size_fitting=sf, is_active=True,
                                           version_number=1, creat_per=self.perfil)
        for pom in (self.sl, self.wa, self.ch, self.orfe):
            for talla, val in [('S', 98.0), ('M', 100.0), ('L', 102.0)]:
                GradedSpec.objects.create(grading_version=gv, pom=pom, size_label=talla,
                                          graded_value_cm=val, grading_type_applied='LINEAR')
        return sf

    #: Catàleg (1 → 2 → 999) i, dins de cada categoria, codi de POM.
    ESPERAT = ['CH', 'WA', 'SL', 'AA']

    def test_branca_de_specs_ordre_del_cataleg_i_despres_codi(self):
        resp = self._taula(self._sf(amb_graduacio=True))

        self.assertEqual(resp.status_code, 200)
        self.assertEqual([p['codi'] for p in resp.data['poms']], self.ESPERAT)

    def test_branca_de_mesures_base_mateix_ordre(self):
        """La vista té dues portes segons si el model té graduació. La taula és una sola:
        no pot estar ordenada d'una manera o d'una altra segons per quina porta s'hi entra."""
        for i, pom in enumerate((self.sl, self.wa, self.ch, self.orfe), start=1):
            BaseMeasurement.objects.create(model=self.model, pom=pom,
                                           base_value_cm=100.0 + i, ordre=i)

        resp = self._taula(self._sf(amb_graduacio=False))

        self.assertEqual(resp.status_code, 200)
        self.assertEqual([p['codi'] for p in resp.data['poms']], self.ESPERAT)

    def test_les_celles_segueixen_l_ordre_dels_poms(self):
        """`cells` és un objecte JSON i el seu ordre de claus és el d'inserció: si no se
        l'ordena amb els POMs, la taula i les seves cel·les van per camins diferents.

        C4 — LA CLAU DE `cells` HA CRESCUT; l'invariant que aquest test defensa, NO. Fins a C4
        la clau era `str(pom_id)` i aquest assert la comparava amb `p['id']`; ara és la
        identitat sencera de la mesura (`pom.identitat.clau_mesura`), i qui la porta a
        `poms` és el camp NOU `clau`. El que es comprova segueix sent exactament el mateix —
        que les dues llistes van en el mateix ordre— i de fet es comprova MILLOR: amb la clau
        antiga, dues germanes del mateix POM haurien donat la mateixa entrada a `cells` i
        l'assert hauria passat amb una cel·la de menys sense adonar-se'n.
        """
        resp = self._taula(self._sf(amb_graduacio=True))

        self.assertEqual(
            list(resp.data['cells']),
            [p['clau'] for p in resp.data['poms']])

    def test_cada_pom_porta_la_clau_que_enllaça_amb_les_seves_celles(self):
        """C4 — el camp que fa navegable el payload: sense ell, el front té dues llistes i cap
        manera de creuar-les quan `pom_id` deixa de ser únic."""
        resp = self._taula(self._sf(amb_graduacio=True))

        for p in resp.data['poms']:
            self.assertEqual(p['clau'], f"{p['id']}|{p['capa']}|{p['instancia']}")
            self.assertIn(p['clau'], resp.data['cells'])
