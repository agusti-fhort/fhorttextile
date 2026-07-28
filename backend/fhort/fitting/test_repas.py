"""Repàs de fittings del model — forma de la resposta, ordre cronològic i últim comentari.

L'endpoint és LECTURA PURA (FittingRepasView). El que es blinda aquí és el que la taula
promet: que les sessions surtin en ordre cronològic, que cada cel·la porti el seu valor i la
seva nota, i que la columna COMENTARIS digui l'últim comentari REAL de cada POM — que no és
el de l'última sessió quan aquella no comenta aquell POM.
"""
import datetime

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.fitting.models import (
    FittingSession, GradingVersion, PieceFitting, PieceFittingLine, SizeFitting,
)
from fhort.fitting.repas_views import FittingRepasView
from fhort.models_app.models import BaseMeasurement, Model
from fhort.pom.models import POMMaster


class FittingRepasTest(TenantTestCase):

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
        from fhort.accounts.models import UserProfile
        self.user = get_user_model().objects.create(username='tester')
        self.profile, _ = UserProfile.objects.get_or_create(
            user=self.user, defaults={'nom_complet': 'Tester', 'rol_nom': 'admin'})

        self.pom_a = POMMaster.objects.create(codi_client='CH', nom_client='Pit')
        self.pom_b = POMMaster.objects.create(codi_client='WA', nom_client='Cintura')

        self.model = Model.objects.create(
            codi_intern='TST-1', codi_tenant='TST', any=2026, sequencial=1,
            temporada='SS26', size_run_model='S·M·L', base_size_label='M',
        )
        # Ordre de fitxa invertit respecte a l'alta: la taula ha de seguir la fitxa, no l'id.
        BaseMeasurement.objects.create(model=self.model, pom=self.pom_a, ordre=2)
        BaseMeasurement.objects.create(model=self.model, pom=self.pom_b, ordre=1)

        # El SizeFitting neix per signal en crear el Model (models_app.signals): s'agafa el
        # que ja hi ha; només es crea si el signal no ha pogut (defensa, no duplicat).
        sf = SizeFitting.objects.filter(model=self.model).first() or SizeFitting.objects.create(
            model=self.model, codi='SF-TST-1', tipus='Fit', numero=1, creat_per=self.profile)
        self.gv = GradingVersion.objects.create(size_fitting=sf, version_number=1,
                                                is_active=True, creat_per=self.profile)
        self.factory = APIRequestFactory()
        self.view = FittingRepasView.as_view()

    # ── Helpers ──────────────────────────────────────────────────────────────
    def _sessio(self, dia, estat='Tancada', notes=''):
        s = FittingSession.objects.create(
            model=self.model, fase='Fit', data=datetime.date(2026, 6, dia),
            estat=estat, notes=notes,
        )
        return s, PieceFitting.objects.create(session=s, model=self.model,
                                              grading_version=self.gv)

    def _linia(self, pf, pom, size, real, nota='', teoric=50.0):
        return PieceFittingLine.objects.create(
            piece_fitting=pf, pom=pom, size_label=size,
            valor_teoric=teoric, valor_real=real, nota=nota)

    def _get(self, **params):
        req = self.factory.get('/repas/', params)
        force_authenticate(req, user=self.user)
        return self.view(req, model_id=self.model.id)

    # ── Forma de la resposta ─────────────────────────────────────────────────
    def test_forma_i_ordre_cronologic(self):
        # Alta en ordre INVERS al cronològic: l'ordre l'ha de posar la data, no la creació.
        _, pf_tard = self._sessio(20)
        _, pf_aviat = self._sessio(10)
        self._linia(pf_tard, self.pom_a, 'M', 61.0)
        self._linia(pf_aviat, self.pom_a, 'M', 60.0)

        resp = self._get()
        self.assertEqual(resp.status_code, 200)
        d = resp.data
        self.assertEqual(d['talla'], 'M')                       # default = talla base
        self.assertEqual(d['talles_disponibles'], ['M'])
        self.assertEqual([s['data'] for s in d['sessions']], ['2026-06-10', '2026-06-20'])

        fila = d['rows'][0]
        for camp in ('pom_id', 'codi', 'nom_en', 'nom_local', 'is_key', 'valors', 'ultim_comentari'):
            self.assertIn(camp, fila)
        primera, segona = (str(s['id']) for s in d['sessions'])
        self.assertEqual(fila['valors'][primera]['valor_real'], 60.0)
        self.assertEqual(fila['valors'][segona]['valor_real'], 61.0)

    def test_files_en_ordre_de_fitxa(self):
        _, pf = self._sessio(10)
        self._linia(pf, self.pom_a, 'M', 60.0)   # ordre 2
        self._linia(pf, self.pom_b, 'M', 40.0)   # ordre 1
        rows = self._get().data['rows']
        self.assertEqual([r['pom_id'] for r in rows], [self.pom_b.id, self.pom_a.id])

    def test_sessio_anullada_fora(self):
        _, pf_ok = self._sessio(10)
        _, pf_nul = self._sessio(11, estat='Anullada')
        self._linia(pf_ok, self.pom_a, 'M', 60.0)
        self._linia(pf_nul, self.pom_a, 'M', 99.0)
        d = self._get().data
        self.assertEqual([s['data'] for s in d['sessions']], ['2026-06-10'])
        self.assertEqual(len(d['rows'][0]['valors']), 1)

    # ── Comentaris ───────────────────────────────────────────────────────────
    def test_ultim_comentari_per_pom_quan_lultima_sessio_no_comenta_tot(self):
        s1, pf1 = self._sessio(10)
        s2, pf2 = self._sessio(20)
        # POM A: comentat a totes dues → mana el de la 2a.
        self._linia(pf1, self.pom_a, 'M', 60.0, nota='massa ample')
        self._linia(pf2, self.pom_a, 'M', 59.0, nota='ja hi som')
        # POM B: només comentat a la 1a; l'última sessió el mesura però no el comenta.
        self._linia(pf1, self.pom_b, 'M', 40.0, nota='puja 1 cm')
        self._linia(pf2, self.pom_b, 'M', 41.0, nota='')

        rows = {r['pom_id']: r for r in self._get().data['rows']}
        self.assertEqual(rows[self.pom_a.id]['ultim_comentari'],
                         {'text': 'ja hi som', 'session_id': s2.id, 'data': '2026-06-20'})
        self.assertEqual(rows[self.pom_b.id]['ultim_comentari'],
                         {'text': 'puja 1 cm', 'session_id': s1.id, 'data': '2026-06-10'})

    def test_pom_sense_cap_comentari(self):
        _, pf = self._sessio(10)
        self._linia(pf, self.pom_a, 'M', 60.0)
        self.assertIsNone(self._get().data['rows'][0]['ultim_comentari'])

    def test_comentaris_de_sessio(self):
        s, pf = self._sessio(10, notes='La model arriba tard')
        pf.gate = 'NO_OK'
        pf.gate_motiu = 'Màniga curta'
        pf.save(update_fields=['gate', 'gate_motiu'])
        self._linia(pf, self.pom_a, 'M', 60.0)
        sessio = self._get().data['sessions'][0]
        self.assertEqual(sessio['id'], s.id)
        self.assertEqual(sessio['notes'], 'La model arriba tard')
        self.assertEqual(sessio['gate'], 'NO_OK')
        self.assertEqual(sessio['gate_motiu'], 'Màniga curta')

    # ── Eix de talla ─────────────────────────────────────────────────────────
    def test_talla_demanada_i_ordre_del_run(self):
        _, pf = self._sessio(10)
        self._linia(pf, self.pom_a, 'L', 62.0)
        self._linia(pf, self.pom_a, 'S', 58.0)
        self._linia(pf, self.pom_a, 'M', 60.0)
        d = self._get(talla='L')
        self.assertEqual(d.data['talla'], 'L')
        self.assertEqual(d.data['talles_disponibles'], ['S', 'M', 'L'])   # ordre del run
        sid = str(d.data['sessions'][0]['id'])
        self.assertEqual(d.data['rows'][0]['valors'][sid]['valor_real'], 62.0)

    def test_base_no_presa_cau_a_la_primera_disponible(self):
        _, pf = self._sessio(10)
        self._linia(pf, self.pom_a, 'L', 62.0)   # cap línia a la base 'M'
        d = self._get().data
        self.assertEqual(d['talla'], 'L')
        self.assertEqual(len(d['rows']), 1)

    def test_model_sense_fittings(self):
        d = self._get().data
        self.assertEqual(d['sessions'], [])
        self.assertEqual(d['rows'], [])
        self.assertIsNone(d['talla'])


class FittingRepasEtapesTest(FittingRepasTest):
    """UN FITTING NO ÉS SEMPRE UNA FittingSession (decisió Agus, 28/07).

    Al despatx els fittings s'escriuen a mà i s'entren a la TAULA DE MESURES. El cens de
    `fhort` ho confirma: 13 models tenen història de mesures i només 3 tenen PieceFitting —
    per a 10 el Repàs deia «cap fitting registrat» amb la feina feta a l'altra taula.

    Aquí es blinda que el Repàs reculli TOT el que és fitting, vingui de l'eina o de la
    taula, i —igual d'important— que NO reculli el que no ho és.
    """

    def _etapa(self, pom, valor, origen='MANUAL', dia=15, anterior=50.0, motiu=''):
        """Una re-mesura escrita a la taula de mesures, amb data controlada.

        Es fabrica el `MeasurementChangeLog` DIRECTAMENT en comptes de desar la
        BaseMeasurement: així la prova fixa el contracte que el Repàs llegeix, sense dependre
        del camí que l'hagi escrit (fitting, size check o edició a mà).
        """
        from fhort.models_app.models import MeasurementChangeLog

        ctx = {'MANUAL': 'manual', 'CHECKED': 'checked', 'FITTED': 'fitting'}[origen]
        log = MeasurementChangeLog.objects.create(
            model=self.model, pom=pom, valor_anterior=anterior, valor_nou=valor,
            context=ctx, motiu=motiu)
        quan = datetime.datetime(2026, 6, dia, 12, 0, 0, tzinfo=datetime.timezone.utc)
        MeasurementChangeLog.objects.filter(pk=log.pk).update(created_at=quan)
        return log

    def _neteja_log(self):
        """El signal registra un canvi per cada BaseMeasurement del setUp: fora, perquè cada
        prova digui exactament quines etapes hi ha."""
        from fhort.models_app.models import MeasurementChangeLog
        MeasurementChangeLog.objects.filter(model=self.model).delete()

    # ── Cas TATE: model amb NOMÉS etapes, cap sessió ──────────────────────────
    def test_model_sense_cap_sessio_pero_amb_etapes_treu_columnes(self):
        self._neteja_log()
        self._etapa(self.pom_a, 61.0, dia=15)

        d = self._get().data
        self.assertEqual(len(d['sessions']), 1, 'una etapa és una columna')
        col = d['sessions'][0]
        self.assertEqual(col['origen'], 'MANUAL')
        self.assertTrue(str(col['id']).startswith('etapa:'))
        self.assertEqual(d['rows'][0]['valors'][col['id']]['valor_real'], 61.0)
        self.assertEqual(d['talla'], 'M', 'les etapes viuen a la talla base')

    def test_el_buit_honest_nomes_si_no_hi_ha_NI_sessions_NI_etapes(self):
        self._neteja_log()
        d = self._get().data
        self.assertEqual(d['sessions'], [])
        self.assertEqual(d['rows'], [])

    # ── El criteri d'inclusió ────────────────────────────────────────────────
    def test_una_alta_inicial_NO_es_un_fitting(self):
        """`manual` amb valor_anterior NUL és algú donant d'alta la fitxa, no mesurant una
        peça. Al cens de `fhort` són 23 dels 28 events manuals: sense aquest filtre, el
        Repàs s'ompliria de columnes que no són fittings."""
        self._neteja_log()
        self._etapa(self.pom_a, 60.0, anterior=None)
        self.assertEqual(self._get().data['sessions'], [])

    def test_els_contextos_que_no_son_mesura_queden_fora(self):
        from fhort.models_app.models import MeasurementChangeLog
        self._neteja_log()
        for ctx in ('import', 'standard', 'calculated', 'item_standard', 'copied'):
            log = MeasurementChangeLog.objects.create(
                model=self.model, pom=self.pom_a, valor_anterior=50.0, valor_nou=60.0,
                context=ctx)
            MeasurementChangeLog.objects.filter(pk=log.pk).update(
                created_at=datetime.datetime(2026, 6, 15, 12, 0, 0,
                                             tzinfo=datetime.timezone.utc))
        self.assertEqual(self._get().data['sessions'], [],
                         'moure dades no és mesurar una peça')

    def test_els_tres_contextos_de_mesura_hi_entren(self):
        self._neteja_log()
        self._etapa(self.pom_a, 61.0, origen='MANUAL', dia=10)
        self._etapa(self.pom_a, 62.0, origen='CHECKED', dia=11)
        self._etapa(self.pom_a, 63.0, origen='FITTED', dia=12)
        self.assertEqual([c['origen'] for c in self._get().data['sessions']],
                         ['MANUAL', 'CHECKED', 'FITTING'])

    # ── Fusió cronològica de les dues fonts ──────────────────────────────────
    def test_sessions_i_etapes_es_fusionen_per_data(self):
        self._neteja_log()
        _, pf_10 = self._sessio(10)
        self._linia(pf_10, self.pom_a, 'M', 60.0)
        _, pf_20 = self._sessio(20)
        self._linia(pf_20, self.pom_a, 'M', 62.0)
        self._etapa(self.pom_a, 61.0, dia=15)      # entremig de les dues sessions

        d = self._get().data
        self.assertEqual([c['origen'] for c in d['sessions']], ['SESSIO', 'MANUAL', 'SESSIO'])
        self.assertEqual([c['data'][:10] for c in d['sessions']],
                         ['2026-06-10', '2026-06-15', '2026-06-20'])
        valors = d['rows'][0]['valors']
        self.assertEqual([valors[str(c['id'])]['valor_real'] for c in d['sessions']],
                         [60.0, 61.0, 62.0])

    def test_una_etapa_no_arrossega_POMs_que_ningu_va_tocar(self):
        """Sense carry-forward, a diferència de la taula de mesures: allà cada columna és un
        snapshot de la fitxa; aquí és UN esdeveniment. Arrossegar faria semblar que es van
        prendre mesures que ningú va prendre."""
        self._neteja_log()
        self._etapa(self.pom_a, 61.0, dia=15)      # només el pit

        d = self._get().data
        clau = d['sessions'][0]['id']
        per_pom = {r['pom_id']: r for r in d['rows']}
        self.assertIn(clau, per_pom[self.pom_a.id]['valors'])
        self.assertNotIn(self.pom_b.id, per_pom,
                         'un POM que ningú va mesurar no fa fila')

    # ── Comentaris: últim per POM amb les fonts barrejades ───────────────────
    def test_ultim_comentari_amb_fonts_barrejades(self):
        """La nota d'una etapa (DECISIÓ·NOTA del size check) i la d'una sessió competeixen
        pel mateix lloc: guanya la darrera en el temps, vingui d'on vingui."""
        from fhort.models_app.models import SizeCheck, SizeCheckLine
        self._neteja_log()

        _, pf = self._sessio(10)
        self._linia(pf, self.pom_a, 'M', 60.0, nota='de la sessió')

        # Un size check resolt: la nota viu a SizeCheckLine i el log hi apunta pel `motiu`.
        sc = SizeCheck.objects.create(model=self.model, talla_base_label='M', estat='Acceptat')
        SizeCheckLine.objects.create(size_check=sc, pom=self.pom_a, valor_teoric=60.0,
                                     valor_real=61.0, decisio='tolerancia_acceptada',
                                     nota='vora curta')
        self._etapa(self.pom_a, 61.0, origen='CHECKED', dia=20,
                    motiu=f'Size check · check {sc.pk}')

        ultim = self._get().data['rows'][0]['ultim_comentari']
        self.assertIn('vora curta', ultim['text'])
        self.assertIn('Tolerància acceptada', ultim['text'], 'la DECISIÓ també es diu')

    def test_si_l_etapa_no_comenta_val_el_comentari_anterior_de_la_sessio(self):
        self._neteja_log()
        _, pf = self._sessio(10)
        self._linia(pf, self.pom_a, 'M', 60.0, nota='de la sessió')
        self._etapa(self.pom_a, 61.0, dia=20)      # etapa POSTERIOR, sense nota

        ultim = self._get().data['rows'][0]['ultim_comentari']
        self.assertEqual(ultim['text'], 'de la sessió')

    def test_a_una_talla_que_no_es_la_base_no_es_pinten_etapes(self):
        """El log és història de BaseMeasurement: totes les seves preses són de la base.
        Ensenyar-les sota una altra talla seria mentir sobre què es va mesurar."""
        self._neteja_log()
        _, pf = self._sessio(10)
        self._linia(pf, self.pom_a, 'L', 70.0)
        self._etapa(self.pom_a, 61.0, dia=15)

        d = self._get(talla='L').data
        self.assertEqual(d['talla'], 'L')
        self.assertEqual([c['origen'] for c in d['sessions']], ['SESSIO'])
