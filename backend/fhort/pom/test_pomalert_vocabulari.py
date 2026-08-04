"""B3 — EL VOCABULARI DE `POMAlert.estat` ÉS EL DECLARAT.

Mateixa família que el fallback d'origens que C3/C va tancar el 02/08: un valor que el codi
escriu i que la llista declarada no conté. Django NO valida `choices` a BD, o sigui que
l'anomalia entra en silenci i qui se n'adona és el LECTOR, que ha d'anar-la tolerant
(l'acta viva a `models_app/views.py`, al bloc de `RESOLVED_ALERT_STATES`).

Els dos disparadors de CREACIÓ escrivien `estat='Obert'`, que no és a `ESTAT_CHOICES`
(Pendent/Acceptat/Corregit). 'Obert' era un SINÒNIM de 'Pendent' —que és, a més, el
`default` del camp—, no un estat distint: substituir-lo no decideix res de domini i no
necessita migració.

🚩 NO cobert aquí, i a posta: el `estat='Resolt'` de `resolve_alert_view`
(`pom/s11_views.py`). Aquell no té sinònim declarat exacte —'Acceptat' (la desviació
s'accepta) i 'Corregit' (la mesura s'ha corregit) són resolucions DIFERENTS— i triar-ne
una és decisió de domini. Queda anotat al lector.

Convenció del repo: `python manage.py test fhort.pom` (el projecte NO fa servir pytest).
"""
import datetime

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.fitting.models import POMAlert
from fhort.models_app.models import BaseMeasurement, Model
from fhort.pom.models import POMMaster
from fhort.pom.s11_views import check_tolerances_view


class VocabulariDeLEstatDeLAlertaTest(TenantTestCase):
    """El que s'escriu ha de ser el que el model declara."""

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
        self.user = get_user_model().objects.create(username='alertaire')
        self.factory = APIRequestFactory()

        self.pom = POMMaster.objects.create(codi_client='CH', nom_client='Pit')
        self.model = Model.objects.create(
            codi_intern='TST-ALERT', codi_tenant='TST', any=2026, sequencial=1,
            temporada='SS26', size_run_model='S·M·L', base_size_label='M',
        )
        BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=100.0,
            origen='MANUAL', is_active=True)

    def _check(self, valor):
        """POST check-tolerances amb una mesura FORA de tolerància (TOL_DEFAULT = 0.6)."""
        req = self.factory.post(
            f'/api/v1/models/{self.model.id}/check-tolerances/',
            {'measurements': [{'pom_id': self.pom.id, 'value_cm': valor}]},
            format='json')
        force_authenticate(req, user=self.user)
        return check_tolerances_view(req, self.model.id)

    def test_lalerta_neix_amb_un_estat_DECLARAT(self):
        """Amb el codi vell això peta: naixia amb `estat='Obert'`, fora de ESTAT_CHOICES."""
        resp = self._check(105.0)          # desvia +5.0 cm, molt fora de ±0.6
        self.assertEqual(resp.status_code, 200)

        alerta = POMAlert.objects.get(model=self.model, pom=self.pom)
        declarats = {codi for codi, _ in POMAlert.ESTAT_CHOICES}
        self.assertIn(
            alerta.estat, declarats,
            f"`estat={alerta.estat!r}` no és a ESTAT_CHOICES ({sorted(declarats)}): "
            "vocabulari no declarat entrant en silenci")

    def test_i_l_estat_es_PENDENT_que_es_el_default_del_camp(self):
        """No n'hi ha prou que sigui declarat: ha de ser el que significa el mateix.
        'Obert' volia dir «encara no resolt», i això a la llista declarada és 'Pendent'."""
        self._check(105.0)

        alerta = POMAlert.objects.get(model=self.model, pom=self.pom)
        self.assertEqual(alerta.estat, 'Pendent')

    def test_i_el_panell_d_atencio_la_segueix_veient(self):
        """La substitució no pot amagar l'alerta: el lector del dashboard tracta «pendent»
        com «NO resolt», i 'Pendent' hi ha de surar igual que hi surava 'Obert'."""
        self._check(105.0)

        RESOLVED = ('Acceptat', 'Corregit', 'Resolt')   # el mateix conjunt del lector
        visibles = POMAlert.objects.filter(model_id=self.model.id).exclude(estat__in=RESOLVED)
        self.assertEqual(visibles.count(), 1)
