"""T1 · `visible` al catàleg: el camp, el seu default i la seva sortida al serializer.

El que aquest fitxer protegeix és una distinció que és fàcil de perdre en una revisió ràpida:
`visible` NO és `active`. Un tipus invisible segueix sent **vàlid** —es pot obrir feina, les
tasques vives segueixen sent seves— i el que canvia és només que el catàleg no l'ofereix.
Si algú un dia «simplifica» tornant-lo a lligar amb `active`, aquests tres tests cauen.

Convenció del repo: `python manage.py test fhort.tasks.test_cataleg_visible` (no pytest).
"""
import datetime

from django_tenants.test.cases import TenantTestCase

from fhort.tasks.models import TaskType
from fhort.tasks.serializers_b import TaskTypeSerializer


class CatalegVisibleTest(TenantTestCase):

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Test Tenant'
        tenant.tipologia = 'MARCA'
        tenant.codi_tenant = 'TCV'
        tenant.vat_number = 'X0000000X'
        tenant.tipus_client = 'STANDARD'
        tenant.gratis_fins = datetime.date(2030, 1, 1)
        return tenant

    def test_default_es_visible(self):
        """Un tipus nou neix oferible: el camp no pot amagar res per omissió."""
        tt = TaskType.objects.create(code='qa_visible_default', name='QA default')
        self.assertTrue(tt.visible)

    def test_serializer_exposa_visible_i_no_el_confon_amb_active(self):
        """La UI ha de poder llegir els dos per separat i decidir amb `visible`."""
        tt = TaskType.objects.create(code='qa_invisible', name='QA invisible', visible=False)
        dades = TaskTypeSerializer(tt).data
        self.assertIn('visible', dades)
        self.assertFalse(dades['visible'])
        # Invisible ≠ retirat: segueix actiu, i el serializer ho ha de dir clar.
        self.assertTrue(dades['active'])
        # I la resta del contracte que la UI de T2 llegeix segueix sent-hi.
        for camp in ('code', 'tipus', 'eina', 'mode', 'fase'):
            self.assertIn(camp, dades)

    def test_amagar_no_desactiva(self):
        """`visible=False` no toca `active`: són dues decisions diferents i han de viure separades."""
        tt = TaskType.objects.create(code='qa_dues_banderes', name='QA dues banderes')
        TaskType.objects.filter(pk=tt.pk).update(visible=False)
        tt.refresh_from_db()
        self.assertFalse(tt.visible)
        self.assertTrue(tt.active)
