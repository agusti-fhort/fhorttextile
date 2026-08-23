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


class ExclusioPerEixTest(_Base):
    """D2 · LA VALIDACIÓ DE BACKEND: fins a UNA etiqueta per eix, i una per sub-eix a la posició.

    🚨 UNA PANTALLA NO ÉS UNA BARANA. Els xips ja no deixaran encendre `left` i `right` alhora,
    però el slug entra per HTTP i qualsevol client (l'import, un script, una pestanya vella)
    el pot compondre. La llei viu a `MeasurementInstance.error_de_combinacio` i la criden les
    portes; això és el que mesura que la combinació il·legal no arriba a la BD.
    """

    def setUp(self):
        self.sembra()

    def mal(self, valor):
        return I.error_de_combinacio(valor)

    # ── el que NO pot ser ────────────────────────────────────────────────────────────────
    def test_left_i_right_no(self):
        self.assertIn('left', self.mal('left-right'))
        self.assertIn('LATERAL', self.mal('left-right'))

    def test_front_i_back_no(self):
        self.assertIn('CARA', self.mal('front-back'))

    def test_dos_estats_no(self):
        self.assertTrue(self.mal('relaxed-extended'))

    def test_una_posicio_sense_subeix_no_es_combina_amb_cap_altra(self):
        """`top`, `cf`, `side`… es comporten com sempre: excloents amb tot el seu eix."""
        self.assertTrue(self.mal('top-left'))
        self.assertTrue(self.mal('cf-back'))
        self.assertTrue(self.mal('top-bottom'))

    # ── el que SÍ que pot ser ────────────────────────────────────────────────────────────
    def test_la_combinada_legitima_back_left(self):
        self.assertEqual(self.mal('back-left'), '')
        self.assertEqual(self.mal('front-right'), '')

    def test_els_dos_eixos_grans_segueixen_creuant_se(self):
        self.assertEqual(self.mal('left-relaxed'), '')
        self.assertEqual(self.mal('back-left-extended'), '')

    def test_una_sola_etiqueta_i_la_unica(self):
        for v in ('', 'left', 'back', 'waistband_seam'):
            self.assertEqual(self.mal(v), '', v)

    def test_el_vocabulari_desconegut_no_es_jutja(self):
        """Un tenant pot crear-se la seva instància; un slug que el diccionari no conté no diu
        de quin eix és, i inventar-li una llei seria pitjor que deixar-lo passar."""
        self.assertEqual(self.mal('sleeve-2'), '')
        self.assertEqual(self.mal('left-sleeve'), '')


class PortesDeLaCombinacioTest(_Base):
    """D2 · les portes HTTP la criden de debò: el serializer de mesures i el de la pertinença."""

    def setUp(self):
        self.sembra()

    def test_el_serializer_de_la_pertinenca_rebutja(self):
        from fhort.pom.serializers import GarmentPOMMapSerializer
        s = GarmentPOMMapSerializer()
        with self.assertRaises(Exception) as cm:
            s.validate_instancia('left-right')
        self.assertIn('LATERAL', str(cm.exception))

    def test_el_serializer_de_la_pertinenca_deixa_passar_la_legitima(self):
        from fhort.pom.serializers import GarmentPOMMapSerializer
        self.assertEqual(GarmentPOMMapSerializer().validate_instancia('back-left'), 'back-left')

    # ── la porta per fila de la pantalla de mesures, EXERCIDA (llei S27: res per introspecció)
    def _serializer(self, instancia):
        from fhort.models_app.models import Model
        from fhort.models_app.serializers import BaseMeasurementSerializer
        pom = POMMaster.objects.create(codi_client='CH', nom_client='Pit')
        model = Model.objects.create(
            codi_intern='TIV-1', codi_tenant='TIV', any=2026, sequencial=1,
            temporada='SS26', size_run_model='S·M·L', base_size_label='M')
        return BaseMeasurementSerializer(data={
            'model': model.id, 'pom': pom.id, 'capa': 'exterior', 'instancia': instancia,
            'nom_fitxa': 'CHX', 'base_value_cm': '10.00',
        })

    def test_la_porta_de_mesures_rebutja_la_combinacio_impossible(self):
        ser = self._serializer('left-right')
        self.assertFalse(ser.is_valid())
        self.assertIn('instancia', ser.errors)
        self.assertIn('LATERAL', str(ser.errors['instancia']))

    def test_la_porta_de_mesures_accepta_la_combinada_legitima(self):
        ser = self._serializer('back-left')
        self.assertTrue(ser.is_valid(), ser.errors)


class SufixCompostTest(_Base):
    """D2 · el SUFIX: un de sol quan hi ha un eix (F · B · L · R) i compost quan n'hi ha dos,
    amb la CARA primer i el LATERAL després (FL · FR · BL · BR).

    ⚠️ DUES ORDENACIONS, I NO ES CONTRADIUEN. L'ordre de COMPOSICIÓ el mana
    `MeasurementInstance.SUBEIXOS` (cara → lateral: el codi que va al fabricant es llegeix
    cara-i-banda); l'ordre de PRESENTACIÓ dels xips el mana el `display_order` de les files
    (Left · Right · Front · Back: el que es fa servir cada dia va primer). Qui composa el codi
    és el front (`utils/diccionariMesures.codiProposat`), amb la regla que aquest diccionari
    publica — aquí es mesura que la publica bé.
    """

    def setUp(self):
        self.sembra()

    def test_els_quatre_sufixos_simples(self):
        self.assertEqual(
            {s: self.sufix(s) for s in ('front', 'back', 'left', 'right')},
            {'front': 'F', 'back': 'B', 'left': 'L', 'right': 'R'})

    def test_l_ordre_de_composicio_es_cara_i_despres_lateral(self):
        self.assertEqual([clau for clau, _ in I.SUBEIXOS], ['CARA', 'LATERAL'])

    def test_el_subeix_de_cada_slug(self):
        self.assertEqual(I.subeix_de('front'), 'CARA')
        self.assertEqual(I.subeix_de('back'), 'CARA')
        self.assertEqual(I.subeix_de('left'), 'LATERAL')
        self.assertEqual(I.subeix_de('right'), 'LATERAL')
        for sense in ('top', 'bottom', 'cf', 'cb', 'side', 'waistband_seam', 'relaxed'):
            self.assertEqual(I.subeix_de(sense), '', sense)

    def test_el_diccionari_publica_l_estructura(self):
        """El front no se l'ha d'escriure: `subeix` per fila i l'ordre dels sub-eixos."""
        from django.contrib.auth import get_user_model
        from rest_framework.test import APIClient
        user = get_user_model().objects.create_user('dicc_tiv', password='x')
        c = APIClient(HTTP_HOST=self.get_test_tenant_domain())
        c.force_authenticate(user=user)

        r = c.get('/api/v1/mesures/diccionari/')

        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['subeixos'], ['CARA', 'LATERAL'])
        per_slug = {f['slug']: f for f in r.data['instancies']['POSICIO']}
        self.assertEqual(per_slug['back']['subeix'], 'CARA')
        self.assertEqual(per_slug['back']['sufix'], 'B')
        self.assertEqual(per_slug['left']['subeix'], 'LATERAL')
        self.assertEqual(per_slug['bottom']['subeix'], '')      # excloent amb tot el seu eix
        self.assertEqual(per_slug['bottom']['sufix'], 'BM')
