"""INSTÀNCIES DE POSICIÓ v2 — la posició passa a tenir DOS EIXOS (Agus, 22-23/08).

lateral (left · right) i CARA (front · back). Dins d'un eix, EXCLOENTS; entre eixos,
COMBINABLES: `left`+`back` existeix, `left`+`right` i `front`+`back` no.

El sufix `B` era de `bottom` i el vol `back`: per això el tram comença rebatejant
`bottom` → `BM`, i només després entren les dues cares.

  · `SufixBottomTest`   — D1a: `bottom` proposa `BM`, i el POM de codi `B` no el toca ningú
  · `CaresFrontBackTest`— D1b: `front`/`back` existeixen, idempotents per slug
  · `ExclusioPerEixTest`— D2: la validació de backend (una etiqueta per eix, com a molt)
  · `SufixCompostTest`  — D2: CARA primer, LATERAL després (F · B · L · R · FL · FR · BL · BR)

⚠️ Cap escriptura a cap BD viva: `TenantTestCase` corre sobre una BD de test pròpia.
"""
from io import StringIO

from django.core.management import call_command
from django_tenants.test.cases import TenantTestCase

from fhort.pom.models import MeasurementInstance as I, POMMaster


def _migracio(nom):
    """El mòdul d'una migració, pel seu nom. Comencen per xifra: `import` no els veu."""
    import importlib
    return importlib.import_module(f'fhort.pom.migrations.{nom}')


class _Base(TenantTestCase):

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Test Instàncies v2'
        tenant.tipologia = 'MARCA'
        tenant.codi_tenant = 'TIV'
        return tenant

    def sembra(self):
        call_command('seed_measurement_instances', schema=self.tenant.schema_name,
                     stdout=StringIO())

    def sufix(self, slug):
        return I.objects.get(slug=slug).sufix


class SufixBottomTest(_Base):
    """D1a · `bottom` proposa `BM`, i `B` queda lliure per a la cara posterior.

    🚨 EL PARANY, EN TEST. Existeix un POM de catàleg amb codi `B` («Waist width») —a staging
    és la pk 906, i a PROD una altra: la pk divergeix entre entorns i per això aquí se'n
    fabrica un i no se'n cita cap. El seu codi NO té res a veure amb el sufix de la instància:
    són dues taules i dos conceptes. Un rebateig que hi arribés seria catàleg trepitjat.
    """

    def setUp(self):
        self.sembra()
        self.pom_b = POMMaster.objects.create(codi_client='B', nom_client='Waist width')

    def test_la_sembra_proposa_BM(self):
        self.assertEqual(self.sufix('bottom'), 'BM')

    def test_cap_altra_posicio_no_es_diu_BM(self):
        """El sufix ha de dir de QUINA cara parla: repetit, no diu res."""
        sufixos = [s for s in I.objects.filter(eix=I.EIX_POSICIO).values_list('sufix', flat=True) if s]
        self.assertEqual(len(sufixos), len(set(sufixos)), sufixos)

    def test_el_slug_no_es_toca(self):
        """El slug és el contracte: és el que desen les columnes `instancia` (llei G9)."""
        self.assertTrue(I.objects.filter(slug='bottom').exists())

    def test_el_POM_de_codi_B_no_el_toca_ningu(self):
        _migracio('0079_bottom_sufix_bm').endavant(self._apps(), None)
        self.pom_b.refresh_from_db()
        self.assertEqual(self.pom_b.codi_client, 'B')
        self.assertEqual(self.pom_b.nom_client, 'Waist width')

    def test_la_migracio_es_idempotent(self):
        m = _migracio('0079_bottom_sufix_bm')
        m.endavant(self._apps(), None)
        m.endavant(self._apps(), None)          # segona passada: no troba res a moure
        self.assertEqual(self.sufix('bottom'), 'BM')

    def test_la_guarda_de_recompte_atura(self):
        """La guarda, EXERCIDA: amb el sufix vell viu i `esperades=0`, ha d'aturar-se.

        El `slug` és únic i no es pot fabricar una segona fila `bottom`; el que es pot fer és
        estrènyer l'expectativa i comprovar que la guarda no és decorativa.
        """
        m = _migracio('0079_bottom_sufix_bm')
        I.objects.filter(slug='bottom').update(sufix='B')     # l'estat d'abans del rebateig
        with self.assertRaises(RuntimeError) as cm:
            m._mou(I, 'B', 'BM', esperades=0)
        self.assertIn('0079', str(cm.exception))
        self.assertEqual(self.sufix('bottom'), 'B')           # i no ha escrit res

    def _apps(self):
        """El `apps` d'una migració de dades: aquí n'hi ha prou amb el registre real."""
        from django.apps import apps
        return apps


class CaresFrontBackTest(_Base):
    """D1b · les dues cares existeixen, amb sufix propi, i entrar-hi dues vegades no duplica."""

    def setUp(self):
        self.sembra()

    def test_les_dues_cares_hi_son_amb_el_seu_sufix(self):
        self.assertEqual(self.sufix('front'), 'F')
        self.assertEqual(self.sufix('back'), 'B')

    def test_son_de_l_eix_posicio(self):
        for slug in ('front', 'back'):
            self.assertEqual(I.objects.get(slug=slug).eix, I.EIX_POSICIO, slug)

    def test_el_sufix_B_ja_no_es_de_bottom(self):
        """🚨 LA RAÓ DEL TRAM: `B` ha de dir «back» i només «back»."""
        self.assertEqual(self.sufix('bottom'), 'BM')
        self.assertEqual(
            list(I.objects.filter(eix=I.EIX_POSICIO, sufix='B').values_list('slug', flat=True)),
            ['back'])

    def test_la_migracio_es_idempotent_per_slug(self):
        m = _migracio('0080_posicions_front_back')
        from django.apps import apps
        m.endavant(apps, None)
        m.endavant(apps, None)
        self.assertEqual(I.objects.filter(slug__in=['front', 'back']).count(), 2)

    def test_la_guarda_atura_si_el_sufix_B_encara_es_d_una_altra_posicio(self):
        """Sense el rebateig de `bottom`, crear `back` deixaria dos `B` a l'eix: s'atura."""
        from django.apps import apps
        I.objects.filter(slug__in=['front', 'back']).delete()
        I.objects.filter(slug='bottom').update(sufix='B')      # l'estat d'abans de 0079
        with self.assertRaises(RuntimeError) as cm:
            _migracio('0080_posicions_front_back').endavant(apps, None)
        self.assertIn('0079', str(cm.exception))
        self.assertFalse(I.objects.filter(slug='back').exists())   # i no n'ha creat cap
