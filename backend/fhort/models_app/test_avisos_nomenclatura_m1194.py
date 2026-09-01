"""M1194 · L'HOMONÍMIA DE NOMENCLATURA ES DIU, NO ES BARRA (Agus, Decisió 8 · 01/09).

## El defecte que tanca

`gravar_pom_view` refusava la petició SENCERA amb un 400 quan un `nom_fitxa` ja era
`CustomerPOMAlias` d'un altre POM del client. Abast **customer**, a una porta que no escriu
cap àlies: un model VERGE de BRW no es podia gravar perquè algú, en un ALTRE model, ja havia
anomenat «B» i «SF». La pantalla no oferia com reanomenar, o sigui que el refús no tenia
sortida (tres reintents en viu a la formació del 26/08).

## La llei que hi queda

- **Entre models: lliure.** Cap pregunta d'abast customer en aquesta porta.
- **Dins del model: AVÍS.** Mateix `(garment, capa, instancia, nom_fitxa)` amb POMs
  DIFERENTS → es desa igualment i el 200 ho diu a `avisos_nomenclatura`.

## Per què el banc és aquest

És **el mateix de `test_f_formacio_1.py`** —`nom_client` buit, àlies de diccionari pendent de
revisió— a posta: aquell fitxer provava el 400 amb aquestes mateixes dades i els cinc tests
s'han vist VERMELLS amb el codi nou abans de retirar-los. Un banc diferent hauria deixat obert
si el que ha canviat és la llei o les dades.

⚠️ La meitat pura va sense BD: la regla d'agrupació es pot dir sencera amb diccionaris, i és on
canta el dia que algú torni a comparar per menys camps dels que l'àmbit té.
"""
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIClient

from fhort.pom.nomenclatura import avisos_de_nomenclatura, germanes_homonimes


# ═══ PART 1 · LA REGLA D'AGRUPACIÓ (pura) ════════════════════════════════════════════════

def _f(ref, pom_id, nom, garment='', capa='exterior', instancia=''):
    return {'ref': ref, 'pom_id': pom_id, 'nom_fitxa': nom,
            'garment': garment, 'capa': capa, 'instancia': instancia}


class AvisosDeNomenclaturaTest(SimpleTestCase):

    def test_dos_poms_amb_el_mateix_nom_al_mateix_ambit_avisen(self):
        a = avisos_de_nomenclatura([_f(0, 906, 'B'), _f(1, 1015, 'B')])
        self.assertEqual(len(a), 1)
        self.assertEqual(a[0]['nom_fitxa'], 'B')
        self.assertEqual(a[0]['poms'], [906, 1015])
        self.assertEqual(a[0]['files'], [0, 1])

    def test_la_comparacio_del_nom_NO_distingeix_caixa(self):
        # Qui llegeix la fitxa impresa no distingeix «B» de «b»: si les dues línies es
        # llegeixen igual, l'avís ha d'existir. Mateix criteri que l'`iexact` d'`alies_del_codi`.
        a = avisos_de_nomenclatura([_f(0, 906, 'B'), _f(1, 1015, 'b')])
        self.assertEqual(len(a), 1)
        # …i el literal que torna és el de la PRIMERA fila: el que la persona ha escrit.
        self.assertEqual(a[0]['nom_fitxa'], 'B')

    def test_el_MATEIX_pom_repetit_no_es_homonimia(self):
        # Dues files del mateix POM amb el mateix nom no són ambigües a la fitxa. (I si a més
        # comparteixen àmbit, el guard de duplicats de la porta ja les refusa per un altre
        # motiu: dues escriptures a la mateixa fila.)
        self.assertEqual(avisos_de_nomenclatura([_f(0, 906, 'B'), _f(1, 906, 'B')]), [])

    def test_l_AMBIT_son_els_TRES_eixos_i_cadascun_separa(self):
        # 🚨 La família de defectes d'aquest sprint és «indexar per menys camps dels que la
        # identitat té». Aquí es mesura eix per eix: canviar-ne UN ja no és el mateix àmbit.
        for eix in ('garment', 'instancia', 'capa'):
            with self.subTest(eix=eix):
                altre = {eix: {'garment': '02', 'instancia': 'left', 'capa': 'folre'}[eix]}
                self.assertEqual(
                    avisos_de_nomenclatura([_f(0, 906, 'B'), _f(1, 1015, 'B', **altre)]), [],
                    f'l\'eix «{eix}» no separa l\'àmbit')

    def test_sense_nom_de_fitxa_no_hi_ha_res_a_comparar(self):
        self.assertEqual(avisos_de_nomenclatura([_f(0, 906, ''), _f(1, 1015, None)]), [])

    def test_tres_poms_al_mateix_ambit_son_UN_avis_amb_TRES_poms(self):
        # L'avís és per ÀMBIT i no per parella: dir-ho tres vegades seria fer-lo il·legible.
        a = avisos_de_nomenclatura([_f(0, 906, 'B'), _f(1, 1015, 'B'), _f(2, 907, 'B')])
        self.assertEqual(len(a), 1)
        self.assertEqual(a[0]['poms'], [906, 1015, 907])

    def test_buit_i_None_no_peten(self):
        self.assertEqual(avisos_de_nomenclatura([]), [])
        self.assertEqual(avisos_de_nomenclatura(None), [])


# ═══ PART 2 · LA PORTA, CONTRA LA BD ═════════════════════════════════════════════════════

class GravarPomAvisaINoBarraTest(TenantTestCase):

    def setUp(self):
        from fhort.models_app.models import Model
        from fhort.pom.models import CustomerPOMAlias, POMGlobal, POMMaster
        from fhort.tasks.models import Customer, ModelTask, TaskType
        from fhort.accounts.models import UserProfile

        # EL BANC DE F3, INTACTE: `nom_client` buit (103 de 144 a `fhort`) i el nom al global.
        self.glob = POMGlobal.objects.create(
            codi='GLB-BT', nom_en='Leg opening girth', nom_ca='Contorn de boca de camal',
            nom_es='Contorno de boca de pernera')
        self.pom = POMMaster.objects.create(
            codi_client='BT', nom_client='', pom_global=self.glob, actiu=True)
        self.pom_mut = POMMaster.objects.create(
            codi_client='ZZ', nom_client='', pom_global=None, actiu=True)
        self.pom_tercer = POMMaster.objects.create(
            codi_client='YY', nom_client='', pom_global=None, actiu=True)

        self.customer = Customer.objects.create(codi='BRW', nom='Brownie')
        # L'àlies que ABANS barrava el pas. Es queda al banc: el que ha de canviar és l'efecte.
        CustomerPOMAlias.objects.create(
            customer=self.customer, pom=self.pom, client_code='BT',
            origen='DICCIONARI', pendent_revisio=True)

        self.model = Model.objects.create(
            codi_intern='TST-M1194', codi_tenant='TST', any=2027, sequencial=94,
            temporada='FW27', size_run_model='XS·S·M', base_size_label='S',
            customer=self.customer)
        self.user, _ = get_user_model().objects.get_or_create(
            username='qa_m1194', defaults={'email': 'qa@m1194.test'})
        UserProfile.objects.get_or_create(
            user=self.user, defaults={'nom_complet': 'QA M1194', 'rol_nom': 'QA'})
        tt, _ = TaskType.objects.get_or_create(
            code='pom', defaults={'name': 'POM', 'default_order': 1})
        ModelTask.objects.get_or_create(
            model=self.model, task_type=tt, defaults={'status': 'Pending'})

        self.api = APIClient(SERVER_NAME=self.get_test_tenant_domain())
        self.api.force_authenticate(self.user)

    def _grava(self, files):
        return self.api.post(f'/api/v1/models/{self.model.id}/gravar-pom/',
                             {'measurements': files}, format='json')

    def _files_actives(self):
        from fhort.models_app.models import BaseMeasurement
        return BaseMeasurement.objects.filter(model=self.model, is_active=True)

    # ── EL DEFECTE M1194 ─────────────────────────────────────────────────────────────────

    def test_m1194_un_nom_ja_usat_pel_CLIENT_ja_no_barra_res(self):
        # 🚨 EL VERMELL DE PROD: «BT» és àlies del client per al POM `self.pom`, i aquí
        # s'escriu sobre un ALTRE POM. Abans: 400 NOMENCLATURA_OCUPADA i cap fila desada.
        r = self._grava([{'pom_id': self.pom_mut.id, 'base_value_cm': 40, 'nom_fitxa': 'BT'}])
        self.assertEqual(r.status_code, 200, getattr(r, 'data', None))
        self.assertEqual(self._files_actives().count(), 1)
        # …i no és cap homonímia DINS del model: hi ha una sola fila.
        self.assertEqual(r.data['avisos_nomenclatura'], [])

    def test_m1194_el_codi_ja_usat_no_deixa_rastre_de_l_antic_contracte(self):
        # Qui llegís `codi`/`colisions` per decidir si el desat ha anat bé no ha de trobar-los.
        r = self._grava([{'pom_id': self.pom_mut.id, 'base_value_cm': 40, 'nom_fitxa': 'BT'}])
        self.assertNotIn('colisions', r.data)
        self.assertNotEqual(r.data.get('codi'), 'NOMENCLATURA_OCUPADA')

    # ── LA LLEI NOVA ─────────────────────────────────────────────────────────────────────

    def test_dues_files_homonimes_ES_DESEN_LES_DUES_i_l_avis_ho_diu(self):
        r = self._grava([
            {'pom_id': self.pom_mut.id, 'base_value_cm': 40, 'nom_fitxa': 'B'},
            {'pom_id': self.pom_tercer.id, 'base_value_cm': 55, 'nom_fitxa': 'B'},
        ])
        self.assertEqual(r.status_code, 200, getattr(r, 'data', None))
        # ⚠️ LA MEITAT QUE IMPORTA: **desar**. Un avís que perd feina és un refús mal educat.
        self.assertEqual(self._files_actives().count(), 2)
        self.assertEqual(r.data['created'], 2)
        avisos = r.data['avisos_nomenclatura']
        self.assertEqual(len(avisos), 1)
        self.assertEqual(avisos[0]['nom_fitxa'], 'B')
        self.assertEqual(sorted(avisos[0]['poms']), sorted([self.pom_mut.id, self.pom_tercer.id]))
        self.assertEqual(avisos[0]['files'], [0, 1])

    def test_l_avis_porta_l_AMBIT_perque_la_pantalla_pugui_trobar_les_files(self):
        r = self._grava([
            {'pom_id': self.pom_mut.id, 'base_value_cm': 40, 'nom_fitxa': 'B',
             'garment': '02', 'capa': 'folre', 'instancia': 'left'},
            {'pom_id': self.pom_tercer.id, 'base_value_cm': 55, 'nom_fitxa': 'B',
             'garment': '02', 'capa': 'folre', 'instancia': 'left'},
        ])
        a = r.data['avisos_nomenclatura'][0]
        self.assertEqual((a['garment'], a['capa'], a['instancia']), ('02', 'folre', 'left'))

    def test_l_ambit_separa_TAMBE_per_la_porta(self):
        # La mateixa llei que la PART 1, però passant per la normalització de la vista: dues
        # peces diferents no són homònimes encara que es diguin igual.
        r = self._grava([
            {'pom_id': self.pom_mut.id, 'base_value_cm': 40, 'nom_fitxa': 'B'},
            {'pom_id': self.pom_tercer.id, 'base_value_cm': 55, 'nom_fitxa': 'B',
             'garment': '02'},
        ])
        self.assertEqual(r.status_code, 200, getattr(r, 'data', None))
        self.assertEqual(r.data['avisos_nomenclatura'], [])
        self.assertEqual(self._files_actives().count(), 2)

    def test_el_camp_hi_es_SEMPRE_encara_que_sigui_buit(self):
        # Mateix argument que `camps_de`: el consumidor no ha de distingir «no n'hi ha» de
        # «aquest backend encara no ho serveix».
        r = self._grava([{'pom_id': self.pom_mut.id, 'base_value_cm': 40, 'nom_fitxa': 'A'}])
        self.assertIn('avisos_nomenclatura', r.data)
        self.assertEqual(r.data['avisos_nomenclatura'], [])

    # ── EL QUE NO S'HA TOCAT ─────────────────────────────────────────────────────────────

    def test_el_guard_de_DUES_ESCRIPTURES_A_LA_MATEIXA_FILA_segueix_refusant(self):
        # ⚠️ ES POT CONFONDRE AMB L'AVÍS I ÉS UNA ALTRA COSA. Aquell parla de dues files
        # DIFERENTS que es diuen igual; aquest, de dues entrades del payload que cauen sobre la
        # MATEIXA fila (mateix POM i mateix àmbit): allà no hi ha res a avisar perquè un dels
        # dos valors no arribaria mai a la BD. Es queda com un 400, i el canvi d'avui no l'ha
        # de tocar.
        r = self._grava([
            {'pom_id': self.pom_mut.id, 'base_value_cm': 40, 'nom_fitxa': 'A'},
            {'pom_id': self.pom_mut.id, 'base_value_cm': 55, 'nom_fitxa': 'B'},
        ])
        self.assertEqual(r.status_code, 400)
        self.assertIn('dues mesures', ' '.join(r.data['errors']))

    def test_el_guard_de_RANG_FISIC_segueix_sent_un_422(self):
        # L'altra sortida no-200 de la porta. Un avís de nomenclatura no la pot haver mogut.
        r = self._grava([{'pom_id': self.pom_mut.id, 'base_value_cm': 22224.7,
                          'nom_fitxa': 'BT'}])
        self.assertEqual(r.status_code, 422)


# ═══ PART 3 · LES GERMANES HOMÒNIMES (01/09) ═════════════════════════════════════════════
#
# 🚨 EL QUE AQUEST BANC PROTEGEIX ÉS QUE LES DUES FAMÍLIES NO ES TORNIN A CONFONDRE. Tenen la
# mateixa forma de pregunta —«dues files es diuen igual»— i responen coses diferents:
#
#     files                                        germanes   homonímia
#     ─────────────────────────────────────────────────────────────────
#     mateix POM · left/right · «AH»                   1           0
#     POM diferent · left/right · «AH»                 1           0
#     POM diferent · mateixa instància · «AH»          0           1
#
# La fila del mig és la que costa: **la instància difereix, o sigui que NO és homonímia real**
# encara que els POMs siguin dos. Si algun dia les dues columnes es mouen alhora, és que algú
# ha fusionat els jutges i el tram del 01/09 s'ha desfet.

class GermanesHomonimesTest(SimpleTestCase):

    def test_dues_instancies_amb_el_mateix_nom_avisen(self):
        a = germanes_homonimes([_f(0, 904, 'AH', instancia='left'),
                                _f(1, 904, 'AH', instancia='right')])
        self.assertEqual(len(a), 1)
        self.assertEqual(a[0]['nom_fitxa'], 'AH')
        self.assertEqual(a[0]['instancies'], ['left', 'right'])
        self.assertEqual(a[0]['files'], [0, 1])
        # La forma NO porta `instancia` en singular: el grup travessa l'eix, no hi viu dins.
        self.assertNotIn('instancia', a[0])

    def test_el_POM_es_INDIFERENT(self):
        """El cas central és el mateix POM, però dos POMs també es llegeixen igual al paper."""
        for pom_b in (904, 907):
            with self.subTest(pom_b=pom_b):
                a = germanes_homonimes([_f(0, 904, 'AH', instancia='left'),
                                        _f(1, pom_b, 'AH', instancia='right')])
                self.assertEqual(len(a), 1)

    def test_la_instancia_BUIDA_compta_com_una_mes(self):
        """🚨 El cas més fàcil de fabricar: afegir una germana a una fila que no en tenia."""
        a = germanes_homonimes([_f(0, 904, 'AH'), _f(1, 904, 'AH', instancia='left')])
        self.assertEqual(len(a), 1)
        self.assertEqual(a[0]['instancies'], ['', 'left'])

    def test_la_MATEIXA_instancia_no_es_germana(self):
        """Això és l'altra família: mateix àmbit sencer amb POMs diferents."""
        files = [_f(0, 904, 'AH'), _f(1, 907, 'AH')]
        self.assertEqual(germanes_homonimes(files), [])
        self.assertEqual(len(avisos_de_nomenclatura(files)), 1)      # ← i aquella sí que salta

    def test_LES_DUES_FAMILIES_SON_ORTOGONALS(self):
        """El cas que les separa: POMs diferents PERÒ instàncies diferents → només germanes."""
        files = [_f(0, 904, 'AH', instancia='left'), _f(1, 907, 'AH', instancia='right')]
        self.assertEqual(len(germanes_homonimes(files)), 1)
        self.assertEqual(avisos_de_nomenclatura(files), [])

    def test_poden_encendre_s_ALHORA_sobre_files_diferents(self):
        """No són excloents: el desat pot dur les dues coses i cadascuna va al seu camp."""
        files = [_f(0, 904, 'AH'),
                 _f(1, 904, 'AH', instancia='left'),
                 _f(2, 907, 'AH', instancia='left')]
        self.assertEqual(len(germanes_homonimes(files)), 1)          # '' vs 'left'
        hom = avisos_de_nomenclatura(files)
        self.assertEqual(len(hom), 1)                                # 904 vs 907 a 'left'
        self.assertEqual(hom[0]['instancia'], 'left')

    def test_la_peca_i_la_capa_separen(self):
        for eix, valor in (('garment', '02'), ('capa', 'folre')):
            with self.subTest(eix=eix):
                a = germanes_homonimes([
                    _f(0, 904, 'AH', instancia='left'),
                    {**_f(1, 904, 'AH', instancia='right'), eix: valor}])
                self.assertEqual(a, [], f'l\'eix «{eix}» no separa')

    def test_noms_diferents_no_son_germanes(self):
        self.assertEqual(germanes_homonimes([_f(0, 904, 'AH', instancia='left'),
                                             _f(1, 904, 'AH-R', instancia='right')]), [])

    def test_la_caixa_no_separa(self):
        a = germanes_homonimes([_f(0, 904, 'ah', instancia='left'),
                                _f(1, 904, 'AH', instancia='right')])
        self.assertEqual(len(a), 1)
        self.assertEqual(a[0]['nom_fitxa'], 'ah')       # el literal de la PRIMERA fila

    def test_sense_nom_i_amb_brossa_no_peta(self):
        self.assertEqual(germanes_homonimes([]), [])
        self.assertEqual(germanes_homonimes(None), [])
        self.assertEqual(germanes_homonimes([_f(0, 904, ''), _f(1, 904, None)]), [])
