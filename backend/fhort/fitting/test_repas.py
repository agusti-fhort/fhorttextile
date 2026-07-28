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
