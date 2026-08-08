"""Tests de `GET /api/v1/vocabulari/` — i sobretot de les MARQUES (coda F2.2, 08/08).

Convenció del repo: fitxer `test*.py` dins de l'app, executat amb
`python manage.py test fhort.models_app` (el projecte NO fa servir pytest).

**PER QUÈ AQUESTS TESTS I NO UN «torna 200».** L'endpoint en si és trivial —quatre `choices`
serialitzats— i un test que només comprovés la forma no defensaria res. El que aquí sí que es pot
trencar en silenci és la MARCA: `autorable` i `segellat` són DECISIONS (quins règims pot triar un
tècnic; en quins estats una sessió és de només lectura) que ara viuen en un sol lloc perquè el
client les ha deixat de declarar. Si algú afegeix un `choice` nou a `GradingRule.LOGICA_CHOICES`,
per defecte sortirà `autorable=True` i s'oferirà a tots els selects de la casa sense que ningú hi
hagi dit res. Aquests tests són el que fa soroll aquell dia.

I `segellat` defensa una cosa més estreta encara: que la marca sigui el MATEIX
`SEALED_SESSION_ESTATS` que `fitting_line_is_locked` fa complir a l'escriptura, i no una segona
llista que hi coincideixi avui. Per això el test l'importa i el compara, en comptes d'escriure
`['Tancada', 'Anullada']` a mà — que seria replantar al test el duplicat que l'endpoint mata.
"""
from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.fitting.models import FittingSession, PieceFittingLine
from fhort.fitting.services import SEALED_SESSION_ESTATS
from fhort.models_app.models import Model
from fhort.models_app.vocabulari_views import vocabulari_domini_view
from fhort.pom.models import GradingRule
from fhort.tasks.models import TaskType


class VocabulariDominiTests(TenantTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.factory = APIRequestFactory()
        cls.user = get_user_model().objects.create_user(
            username='voc_tester', password='x', email='voc@test.cat')

    def _get(self):
        req = self.factory.get('/api/v1/vocabulari/')
        force_authenticate(req, user=self.user)
        resp = vocabulari_domini_view(req)
        self.assertEqual(resp.status_code, 200)
        return resp.data

    # ── forma ────────────────────────────────────────────────────────────────

    def test_les_sis_llistes_hi_son_i_van_en_lordre_del_model(self):
        """L'ORDRE és part de la dada: reordenar-lo al client trencaria qualsevol stepper."""
        d = self._get()
        esperat = {
            'regims_graduacio': GradingRule.LOGICA_CHOICES,
            'fases_model': Model.FASE_CHOICES,
            'estats_model': Model.ESTAT_CHOICES,
            'fases_tasca': TaskType.FASE_CHOICES,
            'estats_sessio_fitting': FittingSession.ESTAT_CHOICES,
            'veredictes_fitting': PieceFittingLine.DECISIO_CHOICES,
        }
        self.assertEqual(set(d.keys()), set(esperat.keys()))
        for clau, choices in esperat.items():
            self.assertEqual([x['codi'] for x in d[clau]], [c for c, _ in choices], clau)
            self.assertTrue(all(x['etiqueta'] for x in d[clau]), clau)

    # ── autorable ────────────────────────────────────────────────────────────

    def test_exception_no_es_autorable(self):
        """`EXCEPTION` és la petja que el motor estampa des d'un `ModelGradingOverride`
        (`pom/services.py:259,266`), no un règim que un tècnic triï."""
        d = {x['codi']: x for x in self._get()['regims_graduacio']}
        self.assertFalse(d['EXCEPTION']['autorable'])

    def test_zero_no_es_autorable(self):
        """Cap camí el produeix: el detector (`grading_utils`) només surt amb LINEAR/STEP/FIXED,
        i «sempre 0» ja és FIXED amb base 0. 🛑 `SizeMapSetup.jsx:21` l'oferia; la marca resol la
        contradicció i el report ho deixa dit."""
        d = {x['codi']: x for x in self._get()['regims_graduacio']}
        self.assertFalse(d['ZERO']['autorable'])

    def test_els_tres_regims_de_treball_si_que_son_autorables(self):
        d = {x['codi']: x for x in self._get()['regims_graduacio']}
        for codi in ('LINEAR', 'STEP', 'FIXED'):
            self.assertTrue(d[codi]['autorable'], codi)

    def test_cap_regim_desapareix_de_la_llista(self):
        """La marca diu si es pot ESCRIURE, no si existeix: el règim és una columna de
        `GradingRule` i una fila que en porti un de no-autorable s'ha de poder LLEGIR."""
        codis = [x['codi'] for x in self._get()['regims_graduacio']]
        self.assertEqual(codis, [c for c, _ in GradingRule.LOGICA_CHOICES])

    def test_tot_choice_nou_de_logica_ha_de_passar_per_aqui(self):
        """GUARDIÀ. El dia que algú afegeixi un règim, aquest test peta i l'obliga a decidir si és
        autorable — en comptes que s'ofereixi a tots els selects de la casa per omissió."""
        self.assertEqual(
            {c for c, _ in GradingRule.LOGICA_CHOICES},
            {'LINEAR', 'STEP', 'FIXED', 'ZERO', 'EXCEPTION'},
            'Règim nou: decideix `autorable` a REGIMS_NO_AUTORABLES i actualitza aquest test.')

    # ── segellat ─────────────────────────────────────────────────────────────

    def test_segellat_es_el_mateix_guard_que_fa_complir_lescriptura(self):
        """No una llista bessona: el MATEIX `SEALED_SESSION_ESTATS` de `fitting/services.py`."""
        segellats = {x['codi'] for x in self._get()['estats_sessio_fitting'] if x['segellat']}
        self.assertEqual(segellats, set(SEALED_SESSION_ESTATS))

    def test_una_sessio_oberta_no_esta_segellada(self):
        d = {x['codi']: x for x in self._get()['estats_sessio_fitting']}
        self.assertFalse(d['Oberta']['segellat'])
        self.assertFalse(d['Programada']['segellat'])

    # ── veredictes ───────────────────────────────────────────────────────────

    def test_el_buit_no_es_un_veredicte(self):
        """`''` és l'ABSÈNCIA de veredicte, no un quart membre. Emetre'l faria que qualsevol
        select el pintés com una opció triable i tornaria a ensorrar la distinció que
        `PieceFittingLine.decisio` defensa amb el `default=''`: una cel·la que ningú no ha mirat
        no és una cel·la acceptada."""
        codis = [x['codi'] for x in self._get()['veredictes_fitting']]
        self.assertEqual(codis, ['ACCEPTED', 'ADJUSTED', 'REJECTED'])
        self.assertNotIn('', codis)
