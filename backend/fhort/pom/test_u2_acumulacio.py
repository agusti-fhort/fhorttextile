"""U2 · LA LLEI DE L'ACUMULACIÓ — el grup aporta, la família suma, l'item suma.

El que aquests tests defensen no és una funció: és una **decisió de domini** (Agus, 2026-08-07).
El catàleg de POMs d'un item no viu en una taula sola; s'acumula per tres nivells que no
s'exclouen, i la pantalla ha de poder dir de quin nivell arriba cada POM («Ve de»).

Per què tres taules germanes i no una amb FKs nullables, que és la pregunta que qualsevol
llegint això es farà: a Postgres els NULL **no comparen iguals**, o sigui que el
`unique_together` hauria deixat de protegir exactament els dos nivells nous. L'argument sencer
viu a `pom/models.py`, sobre `_POMMapBase`.
"""
import datetime

from django_tenants.test.cases import TenantTestCase

from fhort.pom.acumulacio import (NIVELL_FAMILIA, NIVELL_GRUP, NIVELL_ITEM,
                                  acumula_poms_de_item, recompte_per_nivell)
from fhort.pom.models import (GarmentGroup, GarmentGroupPOMMap, GarmentPOMMap, GarmentType,
                              GarmentTypePOMMap, POMMaster)
from fhort.tasks.models import GarmentTypeItem


class AcumulacioPOMsTest(TenantTestCase):
    """Els tres nivells, la seva unió, i qui guanya quan dos reclamen el mateix."""

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
        self.grup = GarmentGroup.objects.create(codi='U2_TOPS', nom='Tops')
        self.familia = GarmentType.objects.create(
            codi_client='U2_WOVEN', nom_client='Tops de teixit pla',
            grup='U2_TOPS', grup_ref=self.grup)
        self.item = GarmentTypeItem.objects.create(
            garment_type=self.familia, code='u2_blouse', name='Blusa')
        self._seq = 0

    def _pom(self, codi):
        self._seq += 1
        return POMMaster.objects.create(codi_client=f'U2-{codi}', nom_client=f'POM {codi}')

    def _a_grup(self, pom, **kw):
        return GarmentGroupPOMMap.objects.create(garment_group=self.grup, pom=pom, **kw)

    def _a_familia(self, pom, **kw):
        return GarmentTypePOMMap.objects.create(garment_type=self.familia, pom=pom, **kw)

    def _a_item(self, pom, **kw):
        return GarmentPOMMap.objects.create(garment_type_item=self.item, pom=pom, **kw)

    # ── la llei ───────────────────────────────────────────────────────────────

    def test_els_tres_nivells_se_SUMEN_i_cadascun_diu_d_on_ve(self):
        pg, pf, pi = self._pom('G'), self._pom('F'), self._pom('I')
        self._a_grup(pg)
        self._a_familia(pf)
        self._a_item(pi)

        acc = acumula_poms_de_item(self.item)

        self.assertEqual(len(acc), 3)
        per_pom = {f['pom_id']: f for f in acc}
        self.assertEqual(per_pom[pg.id]['nivell'], NIVELL_GRUP)
        self.assertEqual(per_pom[pf.id]['nivell'], NIVELL_FAMILIA)
        self.assertEqual(per_pom[pi.id]['nivell'], NIVELL_ITEM)
        # I l'àncora diu QUIN grup/família/item, no només el nivell.
        self.assertEqual(per_pom[pg.id]['ancora'], 'U2_TOPS')
        self.assertEqual(per_pom[pf.id]['ancora'], 'U2_WOVEN')
        self.assertEqual(per_pom[pi.id]['ancora'], 'u2_blouse')

    def test_res_exclou_res_un_POM_pot_ser_a_molts_items(self):
        """La segona meitat de la llei: el catàleg PROPOSA, no restringeix."""
        pom = self._pom('COMPARTIT')
        altre_item = GarmentTypeItem.objects.create(
            garment_type=self.familia, code='u2_shirt', name='Camisa')
        self._a_item(pom)
        GarmentPOMMap.objects.create(garment_type_item=altre_item, pom=pom)

        self.assertEqual(len(acumula_poms_de_item(self.item)), 1)
        self.assertEqual(len(acumula_poms_de_item(altre_item)), 1)

    def test_el_nivell_MES_ESPECIFIC_guanya_i_es_queda_la_memoria_dels_altres(self):
        """El cas normal, no el rar: el grup diu «tots els tops porten pit» i l'item ho torna a
        dir. No és un duplicat a esmenar — mana l'item, que coneix millor la peça, i el
        `tambe_a` conserva d'on més venia perquè la pantalla ho pugui explicar."""
        pom = self._pom('PIT')
        self._a_grup(pom, ordre=1)
        self._a_familia(pom, ordre=2)
        m_item = self._a_item(pom, ordre=3)

        acc = acumula_poms_de_item(self.item)

        self.assertEqual(len(acc), 1)                       # una identitat, una fila
        f = acc[0]
        self.assertEqual(f['nivell'], NIVELL_ITEM)
        self.assertEqual(f['map_id'], m_item.id)
        self.assertEqual([x['nivell'] for x in f['tambe_a']], [NIVELL_GRUP, NIVELL_FAMILIA])

    def test_la_capa_i_la_instancia_son_IDENTITAT_no_decoracio(self):
        """El mateix POM a l'exterior i al folre són DUES pertinences, no una — la mateixa llei
        que ja governa `GarmentPOMMap`. Si l'acumulació les col·lapsés, el folre desapareixeria."""
        pom = self._pom('SISA')
        self._a_grup(pom, capa='exterior')
        self._a_item(pom, capa='folre')
        self._a_item(pom, capa='exterior', instancia='left')

        acc = acumula_poms_de_item(self.item)

        self.assertEqual(len(acc), 3)
        self.assertEqual({(f['capa'], f['instancia']) for f in acc},
                         {('exterior', ''), ('folre', ''), ('exterior', 'left')})

    # ── els casos de vora ─────────────────────────────────────────────────────

    def test_una_familia_SENSE_GRUP_acumula_igual_els_altres_dos_nivells(self):
        """`grup_ref` és nullable (C6 pas 1 encara conviu amb el string): una família sense grup
        no és un error, és una dada incompleta que no ha de fer caure la pantalla."""
        self.familia.grup_ref = None
        self.familia.save(update_fields=['grup_ref'])
        self._a_grup(self._pom('IGNORAT'))            # el grup existeix, però no hi penja
        self._a_familia(self._pom('F'))
        self._a_item(self._pom('I'))

        acc = acumula_poms_de_item(self.item)

        self.assertEqual({f['nivell'] for f in acc}, {NIVELL_FAMILIA, NIVELL_ITEM})

    def test_un_item_sense_res_declarat_dona_llista_buida_no_error(self):
        self.assertEqual(acumula_poms_de_item(self.item), [])

    def test_el_recompte_per_nivell_SUMA_exactament_el_total(self):
        """La barra de la maqueta es pinta amb aquests tres números: si no sumen el total,
        la barra menteix."""
        self._a_grup(self._pom('G1')); self._a_grup(self._pom('G2'))
        self._a_familia(self._pom('F1'))
        self._a_item(self._pom('I1')); self._a_item(self._pom('I2')); self._a_item(self._pom('I3'))

        r = recompte_per_nivell(acumula_poms_de_item(self.item))

        self.assertEqual(r, {NIVELL_GRUP: 2, NIVELL_FAMILIA: 1, NIVELL_ITEM: 3, 'total': 6})

    def test_el_recompte_compta_el_que_cada_nivell_APORTA_de_debo(self):
        """Quan l'item tapa un POM del grup, aquell POM ja no l'aporta el grup: si es comptés
        als dos llocs, el total seria més gran que la llista que hi ha a sota."""
        pom = self._pom('TAPAT')
        self._a_grup(pom)
        self._a_item(pom)
        self._a_grup(self._pom('NOMES_GRUP'))

        acc = acumula_poms_de_item(self.item)
        r = recompte_per_nivell(acc)

        self.assertEqual(r, {NIVELL_GRUP: 1, NIVELL_FAMILIA: 0, NIVELL_ITEM: 1, 'total': 2})
        self.assertEqual(r['total'], len(acc))

    # ── la clau, a la BD ──────────────────────────────────────────────────────

    def test_la_clau_de_les_germanes_protegeix_de_debo(self):
        """El motiu de ser tres taules i no una amb FKs nullables. Aquí la unicitat SÍ que val,
        perquè no hi ha cap NULL a la clau."""
        from django.db import IntegrityError, transaction
        pom = self._pom('CLAU')
        self._a_grup(pom)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self._a_grup(pom)

        pomf = self._pom('CLAUF')
        self._a_familia(pomf)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self._a_familia(pomf)


class POMUsIEsborratTest(TenantTestCase):
    """U1 · LA REGLA D'ESBORRAT — la lliçó de `TGIRL-EU-HEIGHT`, convertida en codi.

    Aquell run es va donar per «6 FK entrants a zero» i resulta que era l'àncora de 350 regles
    de graduació: el cens s'havia fet contra la BD, i les FK amb `db_constraint=False` —que
    aquesta casa fa servir a tot arreu per creuar shared↔tenant— **no existeixen per a
    Postgres**. Aquí es pregunta a `_meta.related_objects`, que és qui les veu totes.
    """

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
        from django.contrib.auth import get_user_model
        from fhort.accounts.models import UserProfile
        self.user = get_user_model().objects.create(username='u1tec')
        UserProfile.objects.get_or_create(user=self.user)
        self.grup = GarmentGroup.objects.create(codi='U1_TOPS', nom='Tops')
        self.familia = GarmentType.objects.create(
            codi_client='U1_FAM', nom_client='Família', grup='U1_TOPS', grup_ref=self.grup)
        self.item = GarmentTypeItem.objects.create(
            garment_type=self.familia, code='u1_item', name='Item')

    def _us(self, pom):
        from rest_framework.test import APIRequestFactory, force_authenticate
        from fhort.pom.cataleg_views import pom_us_view
        req = APIRequestFactory().get(f'/api/v1/poms/{pom.id}/us/')
        force_authenticate(req, user=self.user)
        return pom_us_view(req, pom.id)

    def _pom_tenant(self, codi='LLIURE'):
        """Un POM NASCUT AL TENANT: sense `pom_global`. És l'únic tipus esborrable."""
        return POMMaster.objects.create(codi_client=codi, nom_client='POM del tenant')

    def test_un_POM_sense_cap_us_es_pot_esborrar(self):
        r = self._us(self._pom_tenant())
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data['pot_esborrar'])
        self.assertEqual(r.data['total_bloquejant'], 0)
        self.assertIn('es pot esborrar', r.data['motiu'])

    def test_un_POM_DE_SISTEMA_no_s_esborra_mai_ni_sense_us(self):
        """El discriminant és `pom_global`: ve del catàleg de la casa."""
        from fhort.pom.models import POMGlobal
        pg = POMGlobal.objects.create(codi='U1-SYS', nom_en='System POM', nom_ca='POM de sistema',
                                      categoria='TEST')
        pom = POMMaster.objects.create(codi_client='SYS', nom_client='De sistema', pom_global=pg)

        r = self._us(pom)

        self.assertTrue(r.data['de_sistema'])
        self.assertFalse(r.data['pot_esborrar'])
        self.assertEqual(r.data['total_bloquejant'], 0)      # no té ús...
        self.assertIn('no esborrar mai', r.data['motiu'])    # ...i tot i així no s'esborra

    def test_una_pertinença_a_QUALSEVOL_dels_tres_nivells_bloqueja(self):
        """El cens no mira només l'item: les dues taules noves també hi són, perquè
        `_meta.related_objects` les ha vistes soles sense que ningú les enumeri."""
        for fabrica, camp in (
            (lambda p: GarmentPOMMap.objects.create(garment_type_item=self.item, pom=p), 'item'),
            (lambda p: GarmentTypePOMMap.objects.create(garment_type=self.familia, pom=p), 'família'),
            (lambda p: GarmentGroupPOMMap.objects.create(garment_group=self.grup, pom=p), 'grup'),
        ):
            pom = self._pom_tenant(f'BLOQ_{camp}')
            fabrica(pom)

            r = self._us(pom)

            self.assertFalse(r.data['pot_esborrar'], camp)
            self.assertEqual(r.data['total_bloquejant'], 1, camp)
            self.assertIn('no esborrar', r.data['motiu'])

    def test_els_tres_comptadors_compten_ANCORES_no_files(self):
        """Un item que reclama el mateix POM a l'exterior i al folre és UN item, no dos."""
        pom = self._pom_tenant('DOBLE')
        GarmentPOMMap.objects.create(garment_type_item=self.item, pom=pom, capa='exterior')
        GarmentPOMMap.objects.create(garment_type_item=self.item, pom=pom, capa='folre')

        r = self._us(pom)

        self.assertEqual(r.data['us']['items'], 1)
        self.assertEqual(r.data['total_bloquejant'], 2)   # però files n'hi ha dues

    def test_una_relacio_CASCADE_no_bloqueja_pero_ES_DIU(self):
        """🔴 Els àlies del client cauen amb el POM. No impedeixen esborrar-lo —el CASCADE ho
        permet— però un botó que n'esborra tres sense avisar és el silenci de sempre."""
        from fhort.pom.models import CustomerPOMAlias
        from fhort.tasks.models import Customer
        pom = self._pom_tenant('AMB_ALIES')
        cli = Customer.objects.create(codi='U1C', nom='Client U1')
        CustomerPOMAlias.objects.create(customer=cli, pom=pom, codi_client='XX')

        r = self._us(pom)

        self.assertTrue(r.data['pot_esborrar'])            # es pot: cap PROTECT
        self.assertEqual(r.data['total_bloquejant'], 0)
        self.assertEqual(len(r.data['cascada']), 1)        # ...però se n'endú una fila
        self.assertIn('pom.CustomerPOMAlias', r.data['cascada'][0]['relacio'])
        self.assertIn("s'endurà", r.data['motiu'])

    def test_el_cens_recorre_TOTES_les_relacions_declarades_no_una_llista_a_ma(self):
        """El pin de la lliçó TGIRL: si algú afegeix una FK cap a POMMaster i no toca aquest
        codi, el cens l'ha de veure igual. Aquí es fixa que el recorregut és per l'ORM."""
        from fhort.pom.cataleg_views import _cens_relacions
        rels = {r.related_model._meta.label for r in POMMaster._meta.related_objects}
        # Les tres pertinences i les dues CASCADE hi han de ser, com a mínim.
        for esperada in ('pom.GarmentPOMMap', 'pom.GarmentTypePOMMap', 'pom.GarmentGroupPOMMap',
                         'pom.CustomerPOMAlias', 'models_app.ModelGradingRule'):
            self.assertIn(esperada, rels)
        # I amb un POM verge, cap de les 16 no reporta res (ni peta).
        bloq, casc = _cens_relacions(self._pom_tenant('VERGE'))
        self.assertEqual((bloq, casc), ([], []))

    def test_l_us_OBSERVAT_de_capes_i_instancies_surt_de_dades_reals(self):
        """U1 · decisió Agus (07/08). El model no sap quines capes ADMET un POM —no hi ha cap
        FK ni M2M cap a `MeasurementLayer`/`MeasurementInstance`—, o sigui que la fitxa ensenya
        les que es fan servir DE DEBÒ, i el contracte diu `declarat: False` perquè la pantalla
        no ho pugui pintar com si fos una declaració."""
        pom = self._pom_tenant('OBS')
        GarmentPOMMap.objects.create(garment_type_item=self.item, pom=pom, capa='exterior')
        GarmentPOMMap.objects.create(garment_type_item=self.item, pom=pom,
                                     capa='folre', instancia='left')
        GarmentGroupPOMMap.objects.create(garment_group=self.grup, pom=pom, capa='entretela')

        obs = self._us(pom).data['observat']

        self.assertEqual(obs['capes'], ['entretela', 'exterior', 'folre'])
        self.assertEqual(obs['instancies'], ['left'])
        self.assertFalse(obs['declarat'])

    def test_un_POM_sense_us_no_te_capes_observades_i_no_menteix(self):
        """El cas que fa honesta la decisió: llista buida vol dir «encara no s'ha fet servir»,
        no «no admet cap capa». La pantalla ha de dir la primera cosa."""
        obs = self._us(self._pom_tenant('VERGE_OBS')).data['observat']
        self.assertEqual(obs['capes'], [])
        self.assertEqual(obs['instancies'], [])
