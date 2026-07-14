"""Tests de l'import massiu de models (col·lecció Excel) — models_app.

Convenció del repo: mòdul de tests pla dins de l'app, executat amb
`python manage.py test fhort.models_app` (el projecte NO fa servir pytest).

El que aquests tests defensen és una sola frase: **el comptador del bulk no pot
contradir els models que ja hi ha a la BD.** Tres camins escriuen `sequencial`
(signal MAX, wizard MAX, bulk ModelSequence) i només l'últim mira el comptador;
si el comptador es mira només a si mateix, el primer import d'un client que ja té
models reserva l'1 i xoca contra codi_intern (unique) → IntegrityError → 500.
"""
import datetime

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.accounts.models import UserProfile
from fhort.models_app.models import (
    BulkCollectionImport, BulkCollectionRow, Model, ModelSequence)
from fhort.models_app.bulk_import_service import (
    _as_bool, commit_import, reconcile, validate_rows)
from fhort.models_app.bulk_import_views import commit_view
from fhort.models_app.services import reserve_sequence_range
from fhort.pom.models import (
    ConstructionType, GarmentType, SizeDefinition, SizeSystem, Target)
from fhort.tasks.models import Customer, GarmentTypeItem


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


class _BulkBase(_TenantBase):
    """Client BRW + perfil tècnic + helpers per muntar una importació previsada."""

    def setUp(self):
        super().setUp()
        self.customer = Customer.objects.create(codi='BRW', nom='Brownie SL')
        user = get_user_model().objects.create_user(username='tec', password='x')
        # El perfil el pot haver creat ja un signal d'accounts en néixer l'usuari.
        self.profile, _ = UserProfile.objects.get_or_create(
            user=user, defaults={'nom_complet': 'Tècnic', 'rol_nom': 'patronista'})

    def _manual_models(self, n, year=2026, season='FW'):
        """Models creats pel camí del wizard: codi_intern + sequencial explícits (el signal
        no hi toca). Cap d'ells actualitza ModelSequence — aquest és el terreny real."""
        yy = str(year)[-2:]
        for i in range(1, n + 1):
            Model.objects.create(
                codi_intern=f"BRW-{season}{yy}-{str(i).zfill(4)}",
                customer=self.customer, codi_tenant='BRW',
                any=year, temporada=season, sequencial=i,
                nom_prenda=f"Manual {i}", estat='Nou',
            )

    def _previsat(self, noms, year=2026, season='FW'):
        """Una importació PREVISADA amb una fila OK per nom (mínim viable: nom/any/temporada)."""
        imp = BulkCollectionImport.objects.create(
            customer=self.customer, creat_per=self.profile, estat='PREVISAT', resum={}, resultat=[])
        BulkCollectionRow.objects.bulk_create([
            BulkCollectionRow(
                importacio=imp, row_num=i, estat='OK', errors=[],
                raw_data={'nom_prenda': nom, 'any': str(year), 'temporada': season},
            )
            for i, nom in enumerate(noms, start=2)
        ])
        return imp


class ComptadorMonotonTest(_BulkBase):
    """T1 — reserve_sequence_range no pot tornar un número que ja és al terreny."""

    def test_comptador_buit_amb_models_manuals_continua_del_max_real(self):
        # El cas EXACTE de Brownie a PROD: 15 models manuals, comptador inexistent.
        self._manual_models(15)
        self.assertFalse(ModelSequence.objects.filter(customer=self.customer).exists())

        first, last = reserve_sequence_range(self.customer, 2026, 'FW', 5)

        self.assertEqual((first, last), (16, 20))

    def test_comptador_no_retrocedeix_si_va_per_davant_del_terreny(self):
        # Comptador avançat (imports previs) + pocs models al terreny → mana el comptador.
        self._manual_models(3)
        ModelSequence.objects.create(customer=self.customer, year=2026, season='FW', last_seq=40)

        first, last = reserve_sequence_range(self.customer, 2026, 'FW', 2)

        self.assertEqual((first, last), (41, 42))

    def test_reserva_escopada_per_temporada_i_any(self):
        # El MAX real d'una (any, temporada) no contamina les altres claus.
        self._manual_models(15, year=2026, season='FW')

        self.assertEqual(reserve_sequence_range(self.customer, 2026, 'SS', 2), (1, 2))
        self.assertEqual(reserve_sequence_range(self.customer, 2027, 'FW', 2), (1, 2))


class ImportSenseColisioTest(_BulkBase):
    """T1 — el cas de PROD punta a punta: import massiu sobre un client que ja té models."""

    def test_import_massiu_sobre_models_manuals_no_colisiona(self):
        self._manual_models(15)   # BRW-FW26-0001 .. BRW-FW26-0015
        imp = self._previsat(['Tate', 'Rosalia', 'Mika', 'Noa', 'Vera'])

        stats = commit_import(imp, self.profile)

        self.assertEqual(stats['models'], 5)
        nous = list(Model.objects.filter(customer=self.customer, any=2026, temporada='FW')
                    .order_by('sequencial').values_list('codi_intern', flat=True))
        self.assertEqual(nous[15:], [
            'BRW-FW26-0016', 'BRW-FW26-0017', 'BRW-FW26-0018',
            'BRW-FW26-0019', 'BRW-FW26-0020',
        ])
        # 20 codis, tots diferents: cap col·lisió amb el terreny previ.
        self.assertEqual(len(nous), 20)
        self.assertEqual(len(set(nous)), 20)

    def test_dos_imports_seguits_continuen_la_serie(self):
        self._manual_models(15)
        commit_import(self._previsat(['A', 'B']), self.profile)
        commit_import(self._previsat(['C', 'D']), self.profile)

        codis = set(Model.objects.filter(customer=self.customer).values_list('codi_intern', flat=True))
        self.assertIn('BRW-FW26-0018', codis)
        self.assertIn('BRW-FW26-0019', codis)
        self.assertEqual(len(codis), 19)


class EsConjuntTextualTest(_TenantBase):
    """T3 — 'NO' escrit a la columna es_conjunt vol dir NO. `bool('NO')` és True, i la fila
    petava demanant 'referencia_conjunt' a qui no havia demanat cap conjunt."""

    def setUp(self):
        super().setUp()
        self.customer = Customer.objects.create(codi='BRW', nom='Brownie SL')

    def _fila(self, es_conjunt):
        raw = [{'row_num': 2, 'cells': {
            'nom_prenda': 'Tate', 'any': '2026', 'temporada': 'SS', 'es_conjunt': es_conjunt}}]
        results, _resum = validate_rows(self.customer, raw)
        return results[0]

    def test_falsos_textuals_no_demanen_referencia_conjunt(self):
        for valor in ['NO', 'FALSE', 'no', 'False', 'fals', '0', '', 'N']:
            with self.subTest(valor=valor):
                fila = self._fila(valor)
                self.assertEqual(fila['estat'], 'OK', f"'{valor}' hauria de valer NO")
                self.assertEqual(fila['errors'], [])

    def test_un_si_de_debo_segueix_exigint_referencia_conjunt(self):
        fila = self._fila('SI')

        self.assertEqual(fila['estat'], 'ERROR')
        self.assertIn('referencia_conjunt', fila['errors'][0]['missatge_client'])

    def test_as_bool_unitari(self):
        for fals in ['NO', 'FALSE', 'fals', '0', '', '  no  ', 'None']:
            self.assertFalse(_as_bool(fals), fals)
        for cert in ['SI', 'TRUE', 'X', '1', 'sí', 'yes']:
            self.assertTrue(_as_bool(cert), cert)


class ConciliacioTest(_BulkBase):
    """IMPORT-2/T1 — el sistema ENSENYA el que ha entès de cada cel·la, i què ocuparà."""

    def setUp(self):
        super().setUp()
        self.gt = GarmentType.objects.create(nom_client='Jersey Tops', actiu=True)
        self.item = GarmentTypeItem.objects.create(
            garment_type=self.gt, name='Samarreta / T-shirt', active=True)
        self.target = Target.objects.create(codi='WOMAN', nom_en='Woman', display_order=1)
        self.constr = ConstructionType.objects.create(
            codi='KNIT', nom_en='Knit (Punt Jersey)', display_order=1)
        self.ss = SizeSystem.objects.create(codi='ALPHA_EU_W', nom='Alpha', actiu=True,
                                            base_unit='ALPHA')
        self.ss.targets.add(self.target)
        for i, et in enumerate(['XS', 'S', 'M', 'L', 'XL']):
            SizeDefinition.objects.create(size_system=self.ss, etiqueta=et, ordre=i)

    def _cells(self, **over):
        base = {
            'nom_prenda': 'Tate', 'any': '2026', 'temporada': 'SS',
            'familia': 'Jersey Tops', 'tipus': 'Jersey Tops / Samarreta / T-shirt',
            'target': 'Woman', 'construccio': 'Knit (Punt Jersey)',
            'run_talles': 'XS, S, M, L, XL', 'talla_base': 'M', 'es_conjunt': '',
        }
        base.update(over)
        return base

    def _import(self, files_cells):
        imp = BulkCollectionImport.objects.create(
            customer=self.customer, creat_per=self.profile, estat='PREVISAT', resum={}, resultat=[])
        results, _resum = validate_rows(
            self.customer, [{'row_num': i, 'cells': c} for i, c in enumerate(files_cells, start=2)])
        BulkCollectionRow.objects.bulk_create([
            BulkCollectionRow(importacio=imp, row_num=r['row_num'], raw_data=r['raw_data'],
                              estat=r['estat'], errors=r['errors']) for r in results])
        return imp

    def _camp(self, fila, camp):
        return next(c for c in fila['camps'] if c['camp'] == camp)

    def test_fitxer_net_tot_casa_i_els_codis_son_lliures(self):
        imp = self._import([self._cells(nom_prenda=n) for n in ['Tate', 'Rosalia', 'Mika']])

        rec = reconcile(imp)

        self.assertEqual(rec['resum']['netes'], 3)
        self.assertEqual(rec['resum']['bloquejades'], 0)
        self.assertEqual(rec['resum']['codis_ocupats'], 0)
        self.assertEqual([f['codi_previst'] for f in rec['files']],
                         ['BRW-SS26-0001', 'BRW-SS26-0002', 'BRW-SS26-0003'])
        self.assertTrue(all(f['codi_lliure'] for f in rec['files']))

    def test_el_que_s_ha_transformat_es_MOSTRA(self):
        # El bug real: "XS, S, M, L, XL" es transforma en silenci. Ara es veu.
        imp = self._import([self._cells(target='  woman  ', temporada='ss')])

        fila = reconcile(imp)['files'][0]

        run = self._camp(fila, 'run_talles')
        self.assertEqual(run['estat'], 'NORMALITZAT')
        self.assertEqual(run['valor_fitxer'], 'XS, S, M, L, XL')
        self.assertEqual(run['valor_resolt'], 'XS·S·M·L·XL')
        self.assertEqual(run['candidat']['nom'], 'ALPHA_EU_W')   # contra quin sistema ha casat

        tgt = self._camp(fila, 'target')
        self.assertEqual(tgt['estat'], 'NORMALITZAT')
        self.assertEqual((tgt['valor_fitxer'], tgt['valor_resolt']), ('woman', 'Woman'))

        self.assertEqual(self._camp(fila, 'temporada')['estat'], 'NORMALITZAT')
        self.assertEqual(self._camp(fila, 'familia')['estat'], 'MATCH')

    def test_els_quatre_desajustos_cadascun_amb_el_seu_motiu(self):
        imp = self._import([
            self._cells(nom_prenda='A', familia='Familia Inventada'),
            self._cells(nom_prenda='B', target='Womannn'),
            self._cells(nom_prenda='C', talla_base='XXL'),
            self._cells(nom_prenda='D', es_conjunt='NO'),
        ])

        files = reconcile(imp)['files']

        fam = self._camp(files[0], 'familia')
        self.assertEqual(fam['estat'], 'NO_MATCH')
        self.assertIn('Familia Inventada', fam['motiu'])

        tgt = self._camp(files[1], 'target')
        self.assertEqual(tgt['estat'], 'NO_MATCH')
        self.assertIn('Womannn', tgt['motiu'])

        # El motiu va a la cel·la que el causa: talla_base, no run_talles.
        base = self._camp(files[2], 'talla_base')
        self.assertEqual(base['estat'], 'NO_MATCH')
        self.assertIn("no és al run", base['motiu'])
        self.assertEqual(self._camp(files[2], 'run_talles')['estat'], 'NORMALITZAT')

        # es_conjunt='NO' vol dir NO: ni bloqueja ni demana referència (fix T3 d'IMPORT-1).
        conj = self._camp(files[3], 'es_conjunt')
        self.assertEqual((conj['estat'], conj['valor_resolt']), ('MATCH', 'NO'))
        self.assertEqual(files[3]['estat'], 'OK')

        # Les 3 bloquejades no reben codi; la neta sí. L'import parcial és legítim.
        self.assertEqual([f['codi_previst'] for f in files],
                         [None, None, None, 'BRW-SS26-0001'])
        self.assertEqual(reconcile(imp)['resum']['bloquejades'], 3)

    def test_el_codi_que_ENSENYA_es_el_que_el_commit_ESCRIU(self):
        # La invariant de tot l'sprint: la pantalla no pot mentir.
        self._manual_models(2, year=2026, season='SS')
        imp = self._import([self._cells(nom_prenda=n) for n in ['Tate', 'Rosalia']])

        promesos = [f['codi_previst'] for f in reconcile(imp)['files']]
        commit_import(imp, self.profile)
        escrits = list(Model.objects.filter(customer=self.customer, sequencial__gt=2)
                       .order_by('sequencial').values_list('codi_intern', flat=True))

        self.assertEqual(promesos, ['BRW-SS26-0003', 'BRW-SS26-0004'])
        self.assertEqual(promesos, escrits)

    def test_es_idempotent_i_no_escriu_res(self):
        imp = self._import([self._cells()])
        abans = (Model.objects.count(), ModelSequence.objects.count())

        primera = reconcile(imp)
        segona = reconcile(imp)

        self.assertEqual(primera, segona)          # cridar-ho dos cops dona el mateix
        self.assertEqual(abans, (Model.objects.count(), ModelSequence.objects.count()))
        imp.refresh_from_db()
        self.assertEqual(imp.estat, 'PREVISAT')    # ni tan sols mou l'estat

    def test_un_codi_ocupat_es_VEU_abans_de_commitar(self):
        # Model amb el codi 0001 ocupat però sequencial desalineat → el pla xocaria.
        Model.objects.create(
            codi_intern='BRW-SS26-0001', customer=self.customer, codi_tenant='BRW',
            any=2026, temporada='SS', sequencial=0, nom_prenda='Desalineat', estat='Nou')
        imp = self._import([self._cells(nom_prenda='Tate')])

        rec = reconcile(imp)

        self.assertEqual(rec['files'][0]['codi_previst'], 'BRW-SS26-0001')
        self.assertFalse(rec['files'][0]['codi_lliure'])
        self.assertEqual(rec['resum']['codis_ocupats'], 1)


class ColisioRetorna409Test(_BulkBase):
    """T2 — si tot i el comptador monòton un codi ja és ocupat, el client rep un 409
    llegible, no un 500 pelat. La transacció de commit_import fa rollback: res a mitges."""

    def _commit(self, imp):
        request = APIRequestFactory().post(f'/api/v1/bulk-import/{imp.pk}/commit/')
        force_authenticate(request, user=self.profile.user)
        return commit_view(request, imp.pk)

    def test_colisio_real_de_codi_retorna_409_i_no_importa_res(self):
        # Terreny desalineat REAL: el codi 0016 ja és ocupat però el sequencial del seu
        # model no ho diu (passa perquè conviuen dos formats de codi_intern). El comptador
        # monòton reserva el 16 → el codi xoca.
        self._manual_models(15)
        Model.objects.create(
            codi_intern='BRW-FW26-0016', customer=self.customer, codi_tenant='BRW',
            any=2026, temporada='FW', sequencial=3, nom_prenda='Desalineat', estat='Nou')
        imp = self._previsat(['Tate', 'Rosalia'])
        abans = Model.objects.count()

        resp = self._commit(imp)

        self.assertEqual(resp.status_code, 409)
        self.assertIn('torna-ho a provar', resp.data['error'])
        # Rollback net: cap model creat, la importació segueix previsada (es pot reintentar).
        self.assertEqual(Model.objects.count(), abans)
        imp.refresh_from_db()
        self.assertEqual(imp.estat, 'PREVISAT')

    def test_commit_correcte_segueix_retornant_200(self):
        self._manual_models(15)
        imp = self._previsat(['Tate', 'Rosalia'])

        resp = self._commit(imp)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['models'], 2)
        self.assertEqual(resp.data['estat'], 'IMPORTAT')
