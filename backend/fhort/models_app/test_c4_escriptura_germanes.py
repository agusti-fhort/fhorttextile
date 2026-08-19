"""C4 · EL CAS POSITIU D'ACCEPTACIÓ DE L'ESCRIPTURA — dues germanes, el gest sencer.

El germà d'`test_c4_germanes_a_les_superficies.py`. Aquell vigila que una germana viva SURTI
a cada superfície de LECTURA; aquest vigila que hi ENTRI i en pugui SORTIR: que desar-ne dues
no en perdi cap, i que esborrar-ne una no s'endugui l'altra ni s'ignori en silenci.

PER QUÈ EXISTEIX
----------------
És l'ÚNIC test del projecte que exercita els dos camins d'escriptura de la taula de Mesures
amb dues germanes vives, i un dels dos —`set_measurements_view`— no en té cap altre
exercitador d'aquesta mena: està MORT des del producte (la branca `else` d'`EditableTable`
no s'assoleix mai perquè `MeasuresEntryPanel` passa `onPomSave` sense condició) però la ruta
segueix registrada i qualsevol client amb token hi arriba. Sense aquest guard, algú pot
re-ancorar qualsevol dels dos d'aquí a tres mesos i tota la suite seguirà verda.

⚠️ **UN RE-ANCORATGE DE QUALSEVOL DELS DOS UPSERTS —O DE QUALSEVOL DE LES DUES PODES— L'HA
DE FER CAURE.** Si un assert d'aquí falla, el que s'ha trencat és un escriptor, no l'assert.

EL QUE FIXA, I EL QUE ES VA MESURAR ABANS D'ARREGLAR-HO
--------------------------------------------------------
a) DESAR dues germanes (exterior 100 · folre 40) amb 111 i 44. Abans quedava
   `{exterior: 44, folre: 40}`: la fila d'exterior es quedava el valor del FOLRE i el folre
   no es movia. Cap de les dues deia la veritat. L'assert és FILA A FILA i no per recompte,
   perquè el recompte era correcte i el contingut no.

b) DUES ENTRADES DEL MATEIX REQUEST cap a la mateixa fila. Abans tornava 200 amb
   `updated: 2` per a UNA sola fila, en silenci. Ara és un 400 que diu quina fila és
   l'ambigua: ni es tria, ni es deixa caure cap edició, ni es corromp res.

c) ESBORRAR una germana. Abans la poda estava ancorada a `(exterior, '')` i treure la fila
   del folre NO FEIA RES: l'usuari clicava la paperera i en recarregar la fila hi tornava a
   ser. Ara `keep_mesures` poda per fila.

d) 🔴 EL CLIENT SENSE EIXOS CONSERVA EL COMPORTAMENT D'AVUI, I ÉS VOLGUT — NO ÉS UN FORAT
   PER TAPAR. Una petició amb `pom_id` pelat escriu a l'exterior de la instància única i
   poda només allà. El motiu no és de compatibilitat sinó de significat: **una llista de
   POMs no diu que cap germana s'hagi de treure**, i interpretar-ne el silenci com una ordre
   d'esborrar seria decidir per un client que no ha dit res. Qui "arregli" això farà caure
   els dos últims mètodes d'aquest fitxer, i haurà de venir a llegir això primer.

EL HARNESS
----------
`comportes_alcades` de `test_c4_germanes_a_les_superficies`, autoritzat per a aquesta feina:
alça les comportes dins d'un savepoint que SEMPRE es desfà. L'invariant
`instancia_exigeix_nom` NO s'alça mai — una germana ha de tenir nom, i aquesta regla ha de
SOBREVIURE C4.

Convenció del repo: `python manage.py test fhort.models_app` (el projecte NO fa servir pytest).
"""
import datetime

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.accounts.models import UserProfile
from fhort.models_app.models import BaseMeasurement, Model
from fhort.models_app.test_c4_germanes_a_les_superficies import comportes_alcades
from fhort.pom.models import MeasurementLayer, POMMaster, SizeDefinition, SizeSystem

EXTERIOR = MeasurementLayer.SLUG_DEFECTE
FOLRE = 'folre'
TAULES = ('models_app_basemeasurement', 'models_app_measurementchangelog')


class EscripturaGermanesTest(TenantTestCase):

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
        self.ss = SizeSystem.objects.create(codi='SS_W', nom='SS W', base_unit='ALPHA')
        for i, et in enumerate(['XS', 'S', 'M']):
            SizeDefinition.objects.create(size_system=self.ss, etiqueta=et, ordre=i)
        self.model = Model.objects.create(
            codi_intern='TST-W', codi_tenant='TST', any=2027, sequencial=9,
            temporada='FW27', size_system=self.ss,
            size_run_model='XS·S·M', base_size_label='S')
        self.user, _ = get_user_model().objects.get_or_create(
            username='qa_w', defaults={'email': 'qa@w.test'})
        UserProfile.objects.get_or_create(
            user=self.user, defaults={'nom_complet': 'QA W', 'rol_nom': 'QA'})
        # `gravar_pom_view` tanca la tasca POM del model i falla si no n'hi ha cap.
        from fhort.tasks.models import ModelTask, TaskType
        tt, _ = TaskType.objects.get_or_create(
            code='pom', defaults={'name': 'POM', 'default_order': 1})
        ModelTask.objects.get_or_create(
            model=self.model, task_type=tt, defaults={'status': 'Pending'})

    def _req(self, body):
        r = APIRequestFactory().post('/x/', body, format='json')
        force_authenticate(r, user=self.user)
        return r

    def _germanes(self):
        """Exterior 100 · folre 40. Valors lluny per ordre de magnitud."""
        BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=100.0, nom_fitxa='A-EXT')
        BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=40.0, nom_fitxa='A-FOL', capa=FOLRE)

    def _valors(self):
        """Les files VIVES del POM del banc, per eixos. Acotat a `self.pom` a posta: la clau
        és `(capa, instancia)` i un segon POM hi cauria a sobre, cosa que faria passar per bo
        un assert que no ho és."""
        return {(bm.capa, bm.instancia): float(bm.base_value_cm)
                for bm in BaseMeasurement.objects.filter(
                    model=self.model, pom=self.pom, is_active=True)}

    # ── Camí VIU: gravar-pom ────────────────────────────────────────────────────────

    def test_gravar_pom_desa_cada_germana_a_la_seva_fila(self):
        from fhort.models_app.views import gravar_pom_view

        with comportes_alcades(*TAULES):
            self._germanes()
            resp = gravar_pom_view(self._req({'measurements': [
                {'pom_id': self.pom.id, 'capa': EXTERIOR, 'instancia': '',
                 'base_value_cm': 111.0, 'nom_fitxa': 'A-EXT'},
                {'pom_id': self.pom.id, 'capa': FOLRE, 'instancia': '',
                 'base_value_cm': 44.0, 'nom_fitxa': 'A-FOL'},
            ], 'keep_pom_ids': [self.pom.id]}), self.model.id)

            self.assertIn(resp.status_code, (200, 201), getattr(resp, 'data', None))
            self.assertEqual(self._valors(),
                             {(EXTERIOR, ''): 111.0, (FOLRE, ''): 44.0},
                             'cada germana ha de rebre EL SEU valor')

    def test_gravar_pom_rebutja_dues_mesures_per_a_la_mateixa_fila(self):
        from fhort.models_app.views import gravar_pom_view

        with comportes_alcades(*TAULES):
            self._germanes()
            resp = gravar_pom_view(self._req({'measurements': [
                {'pom_id': self.pom.id, 'base_value_cm': 111.0},
                {'pom_id': self.pom.id, 'base_value_cm': 222.0},
            ], 'keep_pom_ids': [self.pom.id]}), self.model.id)

            self.assertEqual(resp.status_code, 400, getattr(resp, 'data', None))
            self.assertIn('dues mesures per a la mateixa fila',
                          ' '.join(resp.data.get('errors', [])),
                          f'el 400 ha de ser EL DEL GUARD, no un altre: {resp.data}')
            self.assertEqual(self._valors(), {(EXTERIOR, ''): 100.0, (FOLRE, ''): 40.0},
                             'una petició rebutjada no ha d\'haver escrit res')

    # ── Camí de RESERVA: set-measurements ───────────────────────────────────────────

    def test_set_measurements_desa_cada_germana_a_la_seva_fila(self):
        from fhort.models_app.views import set_measurements_view

        with comportes_alcades(*TAULES):
            self._germanes()
            resp = set_measurements_view(self._req({'measurements': [
                {'pom_id': self.pom.id, 'capa': EXTERIOR, 'instancia': '',
                 'base_value_cm': 111.0, 'nom_fitxa': 'A-EXT'},
                {'pom_id': self.pom.id, 'capa': FOLRE, 'instancia': '',
                 'base_value_cm': 44.0, 'nom_fitxa': 'A-FOL'},
            ], 'keep_pom_ids': [self.pom.id]}), self.model.id)

            self.assertIn(resp.status_code, (200, 201), getattr(resp, 'data', None))
            self.assertEqual(self._valors(),
                             {(EXTERIOR, ''): 111.0, (FOLRE, ''): 44.0},
                             'cada germana ha de rebre EL SEU valor')

    def test_set_measurements_rebutja_dues_mesures_per_a_la_mateixa_fila(self):
        from fhort.models_app.views import set_measurements_view

        with comportes_alcades(*TAULES):
            self._germanes()
            resp = set_measurements_view(self._req({'measurements': [
                {'pom_id': self.pom.id, 'base_value_cm': 111.0},
                {'pom_id': self.pom.id, 'base_value_cm': 222.0},
            ], 'keep_pom_ids': [self.pom.id]}), self.model.id)

            self.assertEqual(resp.status_code, 400, getattr(resp, 'data', None))
            self.assertIn('dues mesures per a la mateixa fila',
                          ' '.join(resp.data.get('errors', [])),
                          f'el 400 ha de ser EL DEL GUARD, no un altre: {resp.data}')
            self.assertEqual(self._valors(), {(EXTERIOR, ''): 100.0, (FOLRE, ''): 40.0},
                             'una petició rebutjada no ha d\'haver escrit res')

    # ── ESBORRAR una germana (C4/BLOC 1-TER) ────────────────────────────────────────

    def _mesura(self, capa):
        return {'pom_id': self.pom.id, 'capa': capa, 'instancia': ''}

    def test_gravar_pom_esborra_nomes_la_germana_que_el_client_treu(self):
        """Treure la fila del FOLRE deixa l'exterior viva. Abans no feia res: la poda estava
        ancorada a `(exterior, '')` i no mirava mai la germana."""
        from fhort.models_app.views import gravar_pom_view

        with comportes_alcades(*TAULES):
            self._germanes()
            resp = gravar_pom_view(self._req({
                'measurements': [{'pom_id': self.pom.id, 'capa': EXTERIOR, 'instancia': '',
                                  'base_value_cm': 100.0, 'nom_fitxa': 'A-EXT'}],
                'keep_mesures': [self._mesura(EXTERIOR)],
            }), self.model.id)

            self.assertIn(resp.status_code, (200, 201), getattr(resp, 'data', None))
            self.assertEqual(self._valors(), {(EXTERIOR, ''): 100.0},
                             'el folre s\'havia de donar de baixa i l\'exterior havia de viure')

    def test_gravar_pom_esborra_lexterior_i_deixa_viure_el_folre(self):
        """L'inrevés del d'abans. Que la germana que sobreviu sigui la que NO és el default
        és el cas que l'àncora feia impossible."""
        from fhort.models_app.views import gravar_pom_view

        with comportes_alcades(*TAULES):
            self._germanes()
            resp = gravar_pom_view(self._req({
                'measurements': [{'pom_id': self.pom.id, 'capa': FOLRE, 'instancia': '',
                                  'base_value_cm': 40.0, 'nom_fitxa': 'A-FOL'}],
                'keep_mesures': [self._mesura(FOLRE)],
            }), self.model.id)

            self.assertIn(resp.status_code, (200, 201), getattr(resp, 'data', None))
            self.assertEqual(self._valors(), {(FOLRE, ''): 40.0},
                             'l\'exterior s\'havia de donar de baixa i el folre havia de viure')

    def test_set_measurements_esborra_nomes_la_germana_que_el_client_treu(self):
        from fhort.models_app.views import set_measurements_view

        with comportes_alcades(*TAULES):
            self._germanes()
            resp = set_measurements_view(self._req({
                'measurements': [{'pom_id': self.pom.id, 'capa': FOLRE, 'instancia': '',
                                  'base_value_cm': 40.0, 'nom_fitxa': 'A-FOL'}],
                'keep_mesures': [self._mesura(FOLRE)],
            }), self.model.id)

            self.assertIn(resp.status_code, (200, 201), getattr(resp, 'data', None))
            self.assertEqual(self._valors(), {(FOLRE, ''): 40.0})

    def test_el_client_vell_no_esborra_cap_germana(self):
        """🔴 EL CAS QUE NO POT CANVIAR MAI. Amb `keep_pom_ids` sol —una llista d'ENTERS— el
        client no ha dit que cap germana s'hagi de treure: ha dit de quins POMs parla. La
        poda es limita a l'exterior de la instància única, exactament com abans.

        Si algú desancora això «per coherència», dues germanes vives desapareixerien totes
        dues en desar una taula des d'un client antic, i ningú ho hauria demanat."""
        from fhort.models_app.views import gravar_pom_view

        with comportes_alcades(*TAULES):
            self._germanes()
            # El POM NO és a `keep`: amb la poda per POM, les dues germanes cauríen.
            altre = POMMaster.objects.create(codi_client='WA', nom_client='Cintura')
            resp = gravar_pom_view(self._req({
                'measurements': [{'pom_id': altre.id, 'base_value_cm': 70.0}],
                'keep_pom_ids': [altre.id],
            }), self.model.id)

            self.assertIn(resp.status_code, (200, 201), getattr(resp, 'data', None))
            vius = self._valors()
            self.assertEqual(vius.get((FOLRE, '')), 40.0,
                             'el client vell NO pot donar de baixa una germana que no ha vist')
            self.assertNotIn((EXTERIOR, ''), vius,
                             'l\'exterior sí que cau: és la fila que el client vell SÍ que mira')

    # ── PODA des de la graella (C4/BLOC 2 · `desactivar_pom`) ───────────────────────

    def test_desactivar_pom_treu_la_germana_que_el_client_diu(self):
        """La poda d'UNA fila des de MeasureGrid. Abans la ruta només portava `pom_id` i la
        vista s'ancorava a `(exterior, '')`: treure la sisa dreta en donava de baixa una
        altra, i el `MeasurementChangeLog` —append-only— en guardava l'atribució falsa."""
        from fhort.models_app.views import desactivar_pom_view

        with comportes_alcades(*TAULES):
            self._germanes()
            req = APIRequestFactory().post('/x/', {'capa': FOLRE, 'instancia': ''},
                                           format='json')
            force_authenticate(req, user=self.user)
            resp = desactivar_pom_view(req, self.model.id, self.pom.id)

            self.assertEqual(resp.status_code, 200, getattr(resp, 'data', None))
            self.assertEqual(resp.data['capa'], FOLRE,
                             'la resposta ha de dir QUINA fila ha caigut')
            self.assertEqual(self._valors(), {(EXTERIOR, ''): 100.0},
                             'havia de caure el folre i havia de viure l\'exterior')

    def test_desactivar_pom_sense_eixos_treu_lexterior_com_sempre(self):
        """El client que no diu els eixos rep el literal de sempre. No es mira mai quines
        files hi ha per triar-ne una: aquell desempat el feia el planner."""
        from fhort.models_app.views import desactivar_pom_view

        with comportes_alcades(*TAULES):
            self._germanes()
            req = APIRequestFactory().post('/x/', {}, format='json')
            force_authenticate(req, user=self.user)
            resp = desactivar_pom_view(req, self.model.id, self.pom.id)

            self.assertEqual(resp.status_code, 200, getattr(resp, 'data', None))
            self.assertEqual(self._valors(), {(FOLRE, ''): 40.0})

    # ── ALERTES (C4/BLOC 2 · POMAlert) ──────────────────────────────────────────────

    def test_dues_germanes_fora_de_tolerancia_fan_dues_alertes(self):
        """Una alerta és el veredicte sobre UNA mesura, no sobre un POM: la sisa dreta pot
        desviar i l'esquerra no. Amb la clau `(model, pom, size_fitting)` les dues germanes
        escrivien la MATEIXA fila, l'última guanyava, i el `missatge` —que porta la talla i
        la desviació— acabava descrivint una mesura i titulant-ne una altra."""
        from fhort.fitting.models import (FittingSession, GradingVersion, PieceFitting,
                                          PieceFittingLine, POMAlert, SizeFitting)
        from fhort.pom.s10_views import fitting_vs_spec_view

        with comportes_alcades(*TAULES, 'fitting_piecefittingline'):
            self._germanes()
            perfil = UserProfile.objects.get(user=self.user)
            sf, _ = SizeFitting.objects.get_or_create(
                model=self.model, numero=1,
                defaults={'codi': 'SF-W', 'tipus': 'SizeSet', 'estat': 'Pendent',
                          'creat_per': perfil})
            gv = GradingVersion.objects.create(size_fitting=sf, version_number=1,
                                               is_active=True)
            sessio = FittingSession.objects.create(
                model=self.model, fase='Proto', responsable=perfil,
                data=datetime.date(2027, 1, 15))
            pf = PieceFitting.objects.create(session=sessio, model=self.model,
                                             grading_version=gv)
            # Les dues germanes desvien MOLT, i cadascuna amb una xifra distinta.
            PieceFittingLine.objects.create(
                piece_fitting=pf, pom=self.pom, size_label='S',
                valor_teoric=100.0, valor_real=130.0)
            PieceFittingLine.objects.create(
                piece_fitting=pf, pom=self.pom, size_label='S', capa=FOLRE,
                valor_teoric=40.0, valor_real=55.0)

            req = APIRequestFactory().get(f'/x/{pf.id}/vs-spec/')
            force_authenticate(req, user=self.user)
            resp = fitting_vs_spec_view(req, pf.id)
            self.assertEqual(resp.status_code, 200, getattr(resp, 'data', None))

            alertes = {(a.capa, a.instancia): float(a.desviacio_cm)
                       for a in POMAlert.objects.filter(model=self.model)}
            self.assertEqual(alertes, {(EXTERIOR, ''): 30.0, (FOLRE, ''): 15.0},
                             'cada germana ha de tenir LA SEVA alerta amb LA SEVA desviació')

    # ── AJUST DE TALLA a l'Escalat (C4/BLOC 2 · `escalat_ajustar_talla_view`) ───────

    def _sf(self):
        """SizeFitting + regla resident: `generate_graded_specs` refusa un model sense regles."""
        from fhort.models_app.models import ModelGradingRule
        ModelGradingRule.objects.get_or_create(
            model=self.model, pom=self.pom,
            defaults={'logica': 'LINEAR', 'increment': 1.0, 'actiu': True})
        from fhort.fitting.models import SizeFitting
        sf, _ = SizeFitting.objects.get_or_create(
            model=self.model, numero=1,
            defaults={'codi': 'SF-W', 'tipus': 'SizeSet', 'estat': 'Pendent',
                      'creat_per': UserProfile.objects.get(user=self.user)})
        return sf

    def test_ajustar_talla_mou_la_base_de_la_seva_germana(self):
        """Aquesta vista escriu a QUATRE taules i totes quatre anaven amb el literal
        `(exterior, '')`: ajustar la talla base del FOLRE movia la base de l'EXTERIOR."""
        from fhort.models_app.views import escalat_ajustar_talla_view

        # `fitting_gradedspec` hi entra perquè ajustar una talla encadena cap al motor
        # (`generate_graded_specs`): la base de folre en fa specs de folre, i la comporta
        # d'aquella taula les atura. La cadena d'escriptura no s'acaba a `BaseMeasurement`.
        with comportes_alcades(*TAULES, 'fitting_gradedspec'):
            self._germanes()
            self._sf()
            resp = escalat_ajustar_talla_view(self._req({
                'pom_id': self.pom.id, 'talla': 'S', 'valor': 44.0,
                'capa': FOLRE, 'instancia': '',
            }), self.model.id)

            self.assertEqual(resp.status_code, 200, getattr(resp, 'data', None))
            self.assertEqual(self._valors(), {(EXTERIOR, ''): 100.0, (FOLRE, ''): 44.0},
                             'la base que s\'ha de moure és la del folre, no la de l\'exterior')

    def test_les_linies_de_la_resposta_porten_la_clau_de_la_mesura(self):
        """🔴 REGRESSIÓ INTRODUÏDA AL BLOC 3 I TANCADA AQUÍ. `MeasureGrid` indexa la resposta
        per `linies[].id` dins del seu buffer de cel·les, que va per `lineId`; el `lineId` de
        l'Escalat va passar a `{clau}:{talla}` a `a0f588f9` i el backend seguia emetent
        `{pom_id}:{talla}`. Els dos formats no casaven i el refresc de les talles propagades
        no arribava a la pantalla: l'escriptura es feia, la corba es re-derivava, i les
        cel·les germanes es quedaven amb el valor vell fins a recarregar. Sense error."""
        from fhort.models_app.views import escalat_ajustar_talla_view

        # `fitting_gradedspec` hi entra perquè ajustar una talla encadena cap al motor
        # (`generate_graded_specs`): la base de folre en fa specs de folre, i la comporta
        # d'aquella taula les atura. La cadena d'escriptura no s'acaba a `BaseMeasurement`.
        with comportes_alcades(*TAULES, 'fitting_gradedspec'):
            self._germanes()
            self._sf()
            resp = escalat_ajustar_talla_view(self._req({
                'pom_id': self.pom.id, 'talla': 'S', 'valor': 44.0,
                'capa': FOLRE, 'instancia': '',
            }), self.model.id)

            self.assertEqual(resp.status_code, 200, getattr(resp, 'data', None))
            ids = [l['id'] for l in resp.data['linies']]
            # SET-2/T6a (2026-08-11) — un tram més a la clau (`{pom}|{capa}|{inst}|{garment}`)
            # i per tant un `|` més al prefix. La germana ajustada segueix sent EXACTAMENT la
            # mateixa —el folre de la instància única de la peça mare— i les tres talles
            # tornades són les mateixes: el pin va caure per la forma, no pel contingut.
            # L'escalar és una vora d'ESCRIPTURA i el seu contracte no diu la peça: la mare és
            # el default explícit, i el tram buit del prefix és justament això.
            self.assertTrue(all(i.startswith(f'{self.pom.id}|{FOLRE}||:') for i in ids),
                            f'l\'id ha de ser `{{clau}}:{{talla}}` de LA germana ajustada: {ids}')

    # ── L'ONZENA SUPERFÍCIE (C4/BLOC 2 · `generar-grading`) ─────────────────────────

    def test_generar_grading_torna_la_corba_de_cada_germana(self):
        """El payload de `generar-grading` llegia els specs per `(grading_version, pom)` i les
        germanes hi queien totes al mateix `graded[size_label]`: guanyava l'última llegida.
        Mesurat a ROSALIA (model 188) amb G1 retirat: la fila d'exterior (base 37,0) ensenyava
        la corba del folre (S=35,5). La BD era correcta; només mentia el payload. El cens de
        C4 tenia deu superfícies i aquesta era l'onzena."""
        from fhort.models_app.views import generate_grading_view

        with comportes_alcades(*TAULES, 'fitting_gradedspec'):
            self._germanes()
            self._sf()
            resp = generate_grading_view(self._req({}), self.model.id)
            self.assertEqual(resp.status_code, 200, getattr(resp, 'data', None))

            per_eixos = {(r['capa'], r['instancia']): r for r in resp.data['rows']
                         if r['pom_id'] == self.pom.id}
            self.assertEqual(set(per_eixos), {(EXTERIOR, ''), (FOLRE, '')},
                             'cada germana ha de tenir la seva fila, i dir quina és')
            self.assertEqual(per_eixos[(EXTERIOR, '')]['graded'].get('S'), 100.0)
            self.assertEqual(per_eixos[(FOLRE, '')]['graded'].get('S'), 40.0)

    # ── El client antic segueix escrivint on escrivia ───────────────────────────────

    def test_una_fila_sense_eixos_va_a_lexterior_de_la_instancia_unica(self):
        from fhort.models_app.views import gravar_pom_view

        with comportes_alcades(*TAULES):
            self._germanes()
            resp = gravar_pom_view(self._req({'measurements': [
                {'pom_id': self.pom.id, 'base_value_cm': 111.0},
            ], 'keep_pom_ids': [self.pom.id]}), self.model.id)

            self.assertIn(resp.status_code, (200, 201), getattr(resp, 'data', None))
            self.assertEqual(self._valors(), {(EXTERIOR, ''): 111.0, (FOLRE, ''): 40.0},
                             'sense eixos s\'escriu a l\'exterior i no es tria cap germana')
