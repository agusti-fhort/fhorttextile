"""Tests de la biblioteca de nomenclatura del client (pom).

Convenció del repo: `tests.py` pla dins de l'app, executat amb
`python manage.py test fhort.pom` (el projecte NO fa servir pytest).

QA-S8 (DIAGNOSI_QA_S8_D3_D4 · D4a): el guard d'aprenentatge d'àlies. El que aquests tests
defensen és una sola frase: **un POM que el client ja reclama amb un altre codi no s'aprèn
en silenci.**
"""
import datetime

from django.db import connection
from django_tenants.test.cases import TenantTestCase

from fhort.models_app.extraction_views import find_pom_master
from fhort.pom.management.commands.seed_measurement_layers import CAPES
from fhort.pom.management.commands.seed_measurement_layers import sembra as sembra_capes
from fhort.pom.management.commands.seed_pattern_piece_roles import ROLS, sembra
from fhort.pom.models import (CustomerPOMAlias, MeasurementLayer, PatternPieceRole,
                              POMGlobal, POMMaster)
from fhort.pom.serializers import CustomerPOMAliasSerializer
from fhort.pom.services import maybe_learn_customer_alias
from fhort.tasks.models import Customer


class _TenantBase(TenantTestCase):

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Test Tenant'
        tenant.tipologia = 'MARCA'
        tenant.codi_tenant = 'TST'
        tenant.vat_number = 'X0000000X'
        tenant.tipus_client = 'STANDARD'
        tenant.gratis_fins = datetime.date(2030, 1, 1)
        return tenant


class GuardAprenentatgeAliasTest(_TenantBase):
    """`maybe_learn_customer_alias` no pot aprendre dos codis distints cap al mateix POM com
    si tots dos fossin bons.

    És la mateixa família de defecte que hi ha al catàleg viu de BRW: 'F' (FRONT total length)
    i 'FF' (BACK total length) tots dos sobre el POM 389 'TOTAL LENGTH', i 'U2' (1st BUTTON) /
    'U3' (LAST BUTTON) tots dos sobre el 439 'Width sequins piece' — mesures DISTINTES sobre
    un sol POM.

    El muntatge reprodueix el cas U2/U3, que és el que de debò passa pel camí d'APRENENTATGE:
    descripcions que el matcher NO sap resoldre sol (cap paraula en comú amb el nom del POM),
    de manera que arriba a sembrar l'àlies. Quan el matcher ja l'encerta sol (HIGH/MEDIUM),
    `maybe_learn_customer_alias` no sembra res per disseny i el guard no hi juga.
    """

    def setUp(self):
        self.customer = Customer.objects.create(codi='BRW', nom='Brownie')
        # El POM que al catàleg viu es va endur U, U2 i U3. El seu nom no té cap paraula en
        # comú amb '1st BUTTON'/'LAST BUTTON' → el matcher no els hi sap portar sol
        # (hi arriba per l'arrel del codi, 'U', amb confiança LOW).
        self.pom_u = POMMaster.objects.create(
            codi_client='U', nom_client='Width sequins piece')
        self.pom_altre = POMMaster.objects.create(
            codi_client='WA', nom_client='Waist width')

    def test_primer_codi_sapren_net(self):
        """Cap altre codi del client no reclama encara el POM → àlies normal, no pendent."""
        alias = maybe_learn_customer_alias(self.customer, 'U2', '1st BUTTON', self.pom_u)

        self.assertIsNotNone(alias)
        self.assertEqual(alias.pom_id, self.pom_u.id)
        self.assertFalse(
            alias.pendent_revisio,
            "El primer codi cap a un POM lliure no té res de sospitós: no s'ha de marcar.")

    def test_segon_codi_cap_al_mateix_pom_cau_a_pendent(self):
        """EL CAS F/FF (aquí, U2/U3). 'U2' ja reclama el POM; 'U3' és una mesura DISTINTA que
        hi torna a caure → s'ha de crear PENDENT DE REVISIÓ, no com un àlies bo."""
        maybe_learn_customer_alias(self.customer, 'U2', '1st BUTTON', self.pom_u)

        alias_u3 = maybe_learn_customer_alias(self.customer, 'U3', 'LAST BUTTON', self.pom_u)

        self.assertIsNotNone(alias_u3)
        self.assertEqual(alias_u3.pom_id, self.pom_u.id)
        self.assertTrue(
            alias_u3.pendent_revisio,
            "'U3' cau sobre un POM que 'U2' ja reclama: s'ha de marcar per revisar, no "
            "aprendre'l en silenci com si fos bo.")
        # I el primer no s'ha tocat: el guard no reescriu el passat.
        self.assertFalse(
            CustomerPOMAlias.objects.get(
                customer=self.customer, client_code='U2').pendent_revisio)

    def test_un_pom_lliure_no_queda_contaminat_pel_guard(self):
        """El guard mira el POM de DESTÍ, no el client sencer: un segon codi cap a un POM que
        ningú no reclama segueix essent un àlies net."""
        maybe_learn_customer_alias(self.customer, 'U2', '1st BUTTON', self.pom_u)

        alias_b = maybe_learn_customer_alias(self.customer, 'B', 'CINTURA', self.pom_altre)

        self.assertIsNotNone(alias_b)
        self.assertFalse(
            alias_b.pendent_revisio,
            'El POM WA no el reclama ningú: aquest àlies no té cap col·lisió.')

    def test_reaprendre_el_mateix_codi_no_el_marca(self):
        """Idempotència: re-sembrar el MATEIX codi cap al MATEIX POM no és una col·lisió (el
        guard exclou el propi codi), i per tant no ha de marcar-lo com a pendent."""
        maybe_learn_customer_alias(self.customer, 'U2', '1st BUTTON', self.pom_u)
        alias = maybe_learn_customer_alias(self.customer, 'U2', '1st BUTTON', self.pom_u)

        self.assertEqual(
            CustomerPOMAlias.objects.filter(
                customer=self.customer, client_code='U2').count(), 1)
        if alias is not None:  # si el matcher ja l'encerta sol, retorna None i no re-sembra
            self.assertFalse(alias.pendent_revisio)


class AliasSensePomTest(_TenantBase):
    """Un àlies SENSE pom és vocabulari del client PENDENT DE MAPAR (QA-S8-R1, migració 0037).

    La invariant que aquests tests defensen: **un àlies sense destí no pot vincular res.** Si el
    matcher el mirés, `alias.pom.actiu` petaria amb AttributeError i, pitjor, un àlies que hem
    desvinculat precisament perquè el seu vincle era FALS tornaria a parlar."""

    def setUp(self):
        self.customer = Customer.objects.create(codi='BRW', nom='Brownie')
        self.pom = POMMaster.objects.create(
            codi_client='M-M79', nom_client='Width sequins piece')

    def test_alias_sense_pom_no_vincula_ni_peta(self):
        """El cas real: 'FF' desvinculat del POM 389. El matcher no l'ha de mirar."""
        CustomerPOMAlias.objects.create(
            customer=self.customer, client_code='FF', pom=None,
            description_en='BACK TOTAL LENGTH', pendent_revisio=True, origen='DICCIONARI')

        pm, match_type, _conf, _info = find_pom_master(
            'FF', 'BACK TOTAL LENGTH', customer=self.customer)

        self.assertNotEqual(
            match_type, 'alias_match',
            "Un àlies sense POM no té destí: no pot auto-vincular res. Si torna alias_match, "
            "el filtre pom__isnull=False del matcher ha desaparegut.")

    def test_alias_sense_pom_no_trenca_el_serialitzador(self):
        """La biblioteca ha de poder llistar-lo (hi pinta 'pendent de mapar')."""
        a = CustomerPOMAlias.objects.create(
            customer=self.customer, client_code='F3', pom=None,
            description_en='FRONT CENTER TOTAL LENGTH', origen='DICCIONARI')

        d = CustomerPOMAliasSerializer(a).data

        self.assertIsNone(d['pom'])
        self.assertIsNone(d['pom_codi'])
        self.assertIsNone(d['pom_code_global'])
        # La nomenclatura del client es conserva: és tot el sentit de desvincular en comptes
        # d'esborrar.
        self.assertEqual(d['client_code'], 'F3')
        self.assertEqual(d['description_en'], 'FRONT CENTER TOTAL LENGTH')

    def test_un_alies_mapat_segueix_vinculant(self):
        """La porta nova no pot haver trencat el camí normal."""
        CustomerPOMAlias.objects.create(
            customer=self.customer, client_code='U2', pom=self.pom, origen='DICCIONARI')

        pm, match_type, conf, _info = find_pom_master('U2', '1st BUTTON', customer=self.customer)

        self.assertEqual(match_type, 'alias_match')
        self.assertEqual(conf, 'HIGH')
        self.assertEqual(pm.id, self.pom.id)


class SembraRolsDePecaTest(_TenantBase):
    """La sembra del catàleg de rols: **idempotent i sense esborrar mai res**.

    La prova de foc d'un seed no és que funcioni el primer cop, és que la segona passada
    no dupliqui, no esborri i no es descuidi cap fila. És la mateixa llei que ja governa
    `extend_pom_catalog` i `0025_seed_canonical_task_types`.
    """

    def _sembra(self):
        return sembra(connection.schema_name)

    def test_la_segona_passada_no_duplica_ni_esborra(self):
        creats_1, actualitzats_1 = self._sembra()
        total_1 = PatternPieceRole.objects.count()
        ids_1 = set(PatternPieceRole.objects.values_list('id', flat=True))

        creats_2, actualitzats_2 = self._sembra()

        self.assertEqual(creats_1, len(ROLS))
        self.assertEqual(actualitzats_1, 0)
        self.assertEqual(creats_2, 0, 'la segona passada ha creat files')
        self.assertEqual(actualitzats_2, len(ROLS))
        self.assertEqual(PatternPieceRole.objects.count(), total_1)
        # Els MATEIXOS ids: `update_or_create` reforça la fila, no la substitueix. Si els
        # ids es moguessin, qualsevol FK que hi apuntés hauria quedat òrfena.
        self.assertEqual(set(PatternPieceRole.objects.values_list('id', flat=True)), ids_1)

    def test_els_rols_sembrats_son_de_sistema_i_amb_els_tres_idiomes(self):
        self._sembra()
        for rol in PatternPieceRole.objects.all():
            with self.subTest(slug=rol.slug):
                self.assertTrue(rol.is_system)
                self.assertFalse(rol.pendent_revisio)
                self.assertEqual(rol.origen, PatternPieceRole.ORIGEN_SEED)
                self.assertTrue(rol.nom_en and rol.nom_ca and rol.nom_es)
                self.assertIn(rol.classe, dict(PatternPieceRole.CLASSE_CHOICES))

    def test_un_rol_del_tenant_no_el_toca_la_sembra(self):
        """Un rol que el tenant s'ha creat pel seu compte (D-1: el tenant proposa) ha de
        sobreviure la sembra sencera: el seed només mana sobre els seus."""
        propi = PatternPieceRole.objects.create(
            slug='guarda-pit', nom_en='Chest guard', nom_ca='Guarda pit',
            nom_es='Guarda pecho', classe=PatternPieceRole.CLASSE_COMPLEMENT,
            is_system=False, pendent_revisio=True,
            origen=PatternPieceRole.ORIGEN_MANUAL)

        self._sembra()

        propi.refresh_from_db()
        self.assertFalse(propi.is_system)
        self.assertTrue(propi.pendent_revisio)
        self.assertEqual(PatternPieceRole.objects.count(), len(ROLS) + 1)


class SembraCapesDeMesuraTest(_TenantBase):
    """La sembra del catàleg de capes (C1/T1): **idempotent i sense esborrar mai res**.

    Calc literal de `SembraRolsDePecaTest`, que és la llei d'aquesta casa per a tot catàleg
    de sistema. La prova de foc d'un seed no és que funcioni el primer cop, és que la segona
    passada no dupliqui, no esborri i no es descuidi cap fila — i que els ids no es moguin,
    perquè el dia que alguna cosa hi apunti, una fila substituïda seria una FK òrfena.
    """

    def _sembra(self):
        return sembra_capes(connection.schema_name)

    def test_la_segona_passada_no_duplica_ni_esborra(self):
        creats_1, actualitzats_1 = self._sembra()
        total_1 = MeasurementLayer.objects.count()
        ids_1 = set(MeasurementLayer.objects.values_list('id', flat=True))

        creats_2, actualitzats_2 = self._sembra()

        self.assertEqual(creats_1, len(CAPES))
        self.assertEqual(actualitzats_1, 0)
        self.assertEqual(creats_2, 0, 'la segona passada ha creat files')
        self.assertEqual(actualitzats_2, len(CAPES))
        self.assertEqual(MeasurementLayer.objects.count(), total_1)
        self.assertEqual(set(MeasurementLayer.objects.values_list('id', flat=True)), ids_1)

    def test_les_capes_sembrades_son_de_sistema_i_amb_els_tres_idiomes(self):
        self._sembra()
        for capa in MeasurementLayer.objects.all():
            with self.subTest(slug=capa.slug):
                self.assertTrue(capa.is_system)
                self.assertFalse(capa.pendent_revisio)
                self.assertEqual(capa.origen, MeasurementLayer.ORIGEN_SEED)
                self.assertTrue(capa.nom_en and capa.nom_ca and capa.nom_es)

    def test_exterior_es_la_primera_i_es_el_defecte_del_sistema(self):
        """`exterior` no és una capa qualsevol: és el valor per defecte de la columna `capa`
        de vuit taules i l'únic que la comporta de C1 deixa passar. Si el seed la mogués de
        lloc o li canviés el slug, tots aquells defaults apuntarien al no-res."""
        self._sembra()
        primera = MeasurementLayer.objects.first()
        self.assertEqual(primera.slug, MeasurementLayer.SLUG_DEFECTE)
        self.assertEqual(primera.slug, 'exterior')

    def test_una_capa_del_tenant_no_la_toca_la_sembra(self):
        """Una capa que el tenant s'ha creat pel seu compte (D-1: el tenant proposa) ha de
        sobreviure la sembra sencera: el seed només mana sobre les seves."""
        propia = MeasurementLayer.objects.create(
            slug='termosegellat', nom_en='Heat seal', nom_ca='Termosegellat',
            nom_es='Termosellado', is_system=False, pendent_revisio=True,
            origen=MeasurementLayer.ORIGEN_MANUAL)

        self._sembra()

        propia.refresh_from_db()
        self.assertFalse(propia.is_system)
        self.assertTrue(propia.pendent_revisio)
        self.assertEqual(MeasurementLayer.objects.count(), len(CAPES) + 1)


class MatcherAliesRetiratTest(_TenantBase):
    """COMMIT 1 (16/09, DECISIONS.md): un àlies a un POM RETIRAT és un salt SILENCIÓS si el
    matcher se'l salta i cau a una altra estratègia — el mode de fallada real del model 1216
    ('BR'). Ara es resol dins `find_pom_master` mateix i s'atura la cerca."""

    def setUp(self):
        self.customer = Customer.objects.create(codi='BRW', nom='Brownie')
        self.canonic = POMGlobal.objects.create(
            codi='QA-CANONIC', nom_en='Back neck drop', nom_ca='Back neck drop',
            categoria='QA')
        self.pom_retirat = POMMaster.objects.create(
            codi_client='BR', nom_client='Back neck drop OLD', actiu=False,
            pom_global=self.canonic)
        CustomerPOMAlias.objects.create(
            customer=self.customer, client_code='BR', pom=self.pom_retirat,
            description_en='Back neck drop from HPS to edge', origen='DICCIONARI')

    def test_alies_a_pom_retirat_amb_hereu_suggereix_lhereu_mai_el_retirat(self):
        hereu = POMMaster.objects.create(
            codi_client='BR2', nom_client='Back neck drop from HPS to edge', actiu=True,
            pom_global=self.canonic)

        pm, match_type, conf, info = find_pom_master(
            'BR', 'Back neck drop from HPS to edge', customer=self.customer)

        self.assertEqual(match_type, 'alias_pom_retirat')
        self.assertEqual(conf, 'LOW', 'un POM retirat mai auto-vincula, ni el seu hereu')
        self.assertEqual(info['motiu'], 'alies_pom_retirat')
        self.assertEqual(pm.id, hereu.id)
        self.assertNotEqual(pm.id, self.pom_retirat.id)

    def test_alies_a_pom_retirat_sense_hereu_queda_pendent_visible(self):
        pm, match_type, conf, info = find_pom_master(
            'BR', 'Back neck drop from HPS to edge', customer=self.customer)

        self.assertEqual(match_type, 'alias_pom_retirat')
        self.assertIsNone(pm, "sense hereu, no hi ha res a suggerir com a POM")
        self.assertEqual(info['motiu'], 'alies_pom_retirat')
        self.assertIsNone(info['suggerit'])

    def test_alies_a_pom_retirat_no_cau_a_description_match(self):
        """El mode de fallada real: sense aquest guard, la descripció trobava un ALTRE POM
        actiu per estratègia 3 i hi vinculava en HIGH/MEDIUM — exactament com 'BR' al 1216."""
        # Un POM actiu que la descripció també encertaria per continguda, si la cerca no
        # s'hagués aturat abans.
        POMMaster.objects.create(
            codi_client='ALTRE', nom_client='back neck drop from hps to edge extra', actiu=True)

        pm, match_type, _conf, _info = find_pom_master(
            'BR', 'Back neck drop from HPS to edge', customer=self.customer)

        self.assertEqual(match_type, 'alias_pom_retirat')
        self.assertNotEqual(match_type, 'description_match')


class MatcherNomBuitISenseCoincidenciaTest(_TenantBase):
    """COMMIT 1 · `nom_client=''` ("mana el canònic", 23/08) no pot ser una cadena que
    coincideix amb tot (`'' in qualsevol_cosa`), i un NO_MATCH real ha de dir per què."""

    def setUp(self):
        self.customer = Customer.objects.create(codi='BRW', nom='Brownie')

    def test_pom_amb_nom_buit_no_atrapa_qualsevol_descripcio(self):
        POMMaster.objects.create(codi_client='ZZ', nom_client='', actiu=True)

        pm, match_type, conf, _info = find_pom_master(
            '', 'una descripció qualsevol que no hauria de matchejar res', customer=None)

        self.assertIsNone(pm)
        self.assertEqual(match_type, 'no_match')
        self.assertEqual(conf, 'NO_MATCH')

    def test_sense_coincidencia_porta_motiu_explicit(self):
        pm, match_type, conf, info = find_pom_master(
            'INEXISTENT', 'descripció que no existeix enlloc del catàleg', customer=self.customer)

        self.assertIsNone(pm)
        self.assertEqual(match_type, 'no_match')
        self.assertEqual(conf, 'NO_MATCH')
        self.assertEqual(info['motiu'], 'sense_coincidencia')

    def test_quatre_files_amb_alies_propis_no_col·lapsen_al_mateix_pom(self):
        poms = [POMMaster.objects.create(codi_client=f'C{i}', nom_client=f'Mesura {i}',
                                          actiu=True) for i in range(4)]
        for i, p in enumerate(poms):
            CustomerPOMAlias.objects.create(
                customer=self.customer, client_code=f'C{i}', pom=p, origen='DICCIONARI')

        resolts = [find_pom_master(f'C{i}', '', customer=self.customer)[0] for i in range(4)]

        self.assertEqual(len({p.id for p in resolts if p}), 4)
