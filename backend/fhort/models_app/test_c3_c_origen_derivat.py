"""C3-C — el registre sap distingir una PRESA d'una DERIVACIÓ.

Fins aquí el `MeasurementChangeLog` no tenia cap manera de dir si un valor l'havia mesurat algú
o l'havia mogut el sistema. Amb la derivació entre germanes (Fases D i E) això deixa de ser un
detall: una auditoria exterior↔folre que no ho sàpiga es compara amb ella mateixa i sempre dona
verd, perquè no pot distingir «algú va mesurar el folre» de «el sistema el va moure quan es va
corregir l'exterior».

El que ha de dir «derivada» és sobretot L'ENTRADA DEL REGISTRE, no la columna `origen` de la
fila: l'origen d'una fila el sobreescriu el canvi següent, mentre que el registre és append-only
i conserva la seqüència. El camí triat és el que el sistema ja té muntat — l'`origen` de la fila
en el moment d'escriure alimenta el `context` de l'entrada via `_ORIGEN_TO_CONTEXT` — i aquests
tests fixen precisament el tram que importa: que del registre en surti la marca.

Convenció del repo: `python manage.py test fhort.models_app` (el projecte NO fa servir pytest).
"""
import datetime

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase

from fhort.models_app.models import BaseMeasurement, MeasurementChangeLog, Model
from fhort.models_app.signals import _ORIGEN_TO_CONTEXT
from fhort.pom.models import POMMaster


class OrigenDerivatC3CTest(TenantTestCase):

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
            codi_intern='TST-C3C', codi_tenant='TST', any=2026, sequencial=1,
            temporada='SS26', size_run_model='S·M·L', base_size_label='M',
        )
        self.user, _ = get_user_model().objects.get_or_create(
            username='qa_c3c', defaults={'email': 'qa@c3c.test'})

    def _log_de(self, bm):
        return (MeasurementChangeLog.objects
                .filter(base_measurement=bm).order_by('id').last())

    # ── El que ha de quedar provat ───────────────────────────────────────────────────

    def test_una_escriptura_DERIVAT_deixa_lentrada_marcada_al_registre(self):
        bm = BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=54.0, ordre=1, origen='DERIVAT')

        log = self._log_de(bm)
        self.assertIsNotNone(log, 'una creació amb valor ha de deixar entrada')
        self.assertEqual(log.context, 'derivat',
                         "el REGISTRE és qui ha de dir que el valor no l'ha mesurat ningú")

    def test_una_correccio_DERIVADA_es_distingeix_duna_presa_humana(self):
        """El cas real de D/E: la germana es mou i el registre ho ha de poder dir després."""
        bm = BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=52.0, ordre=1, origen='MANUAL')
        self.assertEqual(self._log_de(bm).context, 'manual')

        # El sistema mou la germana: mateix camp, valor nou, però ningú no l'ha mesurat.
        bm.base_value_cm = 54.0
        bm.origen = 'DERIVAT'
        bm.save(update_fields=['base_value_cm', 'origen', 'updated_at'])

        log = self._log_de(bm)
        self.assertEqual(log.context, 'derivat')
        self.assertEqual(log.valor_anterior, 52.0)
        self.assertEqual(log.valor_nou, 54.0)
        # Les DUES entrades hi són i es distingeixen: això és el que fa auditable la parella.
        self.assertEqual(
            list(MeasurementChangeLog.objects.filter(base_measurement=bm)
                 .order_by('id').values_list('context', flat=True)),
            ['manual', 'derivat'])

    # ── El forat que es tanca de passada ────────────────────────────────────────────

    def test_els_quatre_origens_orfes_ja_surten_del_mapa(self):
        """`TEMPLATE`, `CHECKED`, `ITEM_STANDARD` i `FEDERAT` queien al fallback silenciós."""
        for origen in ('CHECKED', 'ITEM_STANDARD', 'FEDERAT'):
            with self.subTest(origen=origen):
                self.assertIn(origen, _ORIGEN_TO_CONTEXT)
        # TEMPLATE no arriba mai a escriure entrada (una fila sense valor no és un canvi de
        # mesura, guard de signals.py), però ha de constar igualment al vocabulari declarat.
        self.assertIn('TEMPLATE', _ORIGEN_TO_CONTEXT)

    def test_el_vocabulari_del_registre_cobreix_TOTS_els_origens(self):
        """El guard estructural: cap origen nou no pot tornar a colar-se pel fallback.

        El fallback `origen.lower()` de signals.py no peta mai i per això el forat va viure
        tant: hi havia dos contextos ('checked', 'item_standard') vivint al registre de staging
        sense estar declarats enlloc. Si algú afegeix un origen i oblida el mapa, cau aquí.
        """
        declarats = {codi for codi, _etiqueta in BaseMeasurement.ORIGEN_CHOICES}
        mapats = set(_ORIGEN_TO_CONTEXT)
        self.assertEqual(declarats - mapats, set(),
                         'hi ha origens sense context declarat: cauran al fallback silenciós')

    def test_DERIVAT_es_un_origen_declarat_del_model(self):
        self.assertIn('DERIVAT', {c for c, _ in BaseMeasurement.ORIGEN_CHOICES})
