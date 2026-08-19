"""E2/B1 — LA MARCA DEL GEST: `presa_at` distingeix el que els números no poden.

Substrat: `docs/diagnosis/DIAGNOSI_E2_CORRECCIONS_QA.md` §P0. Decisió d'Agus (Patró C, 17/08):
camp explícit en comptes de continuar inferint.

## EL DEFECTE QUE TANCA

`linia_te_contingut` decidia «algú ha mesurat aquesta cel·la?» amb
`valor_real != valor_teoric`, i una `PieceFittingLine` NEIX amb els dos iguals
(`create_piece_fitting`). El predicat només veia, doncs, les preses que **per casualitat** no
coincidien amb la teòrica.

E2b posa la teòrica a la cel·la de l'Escalat en FANTASMA i deixa que l'usuari la confirmi tal
qual. Aquest gest produeix **exactament l'estat del naixement**: cap predicat derivat de valors
el pot distingir. D'aquí el camp.

## EL QUE AQUESTS TESTS VIGILEN, I PER QUÈ CADA UN

  1. una presa que **coincideix** amb la teòrica és una PRESA (el cas nou, impossible abans);
  2. la sembra **no** és una presa (la llei d'E1, que no es pot relaxar per fer passar el 1);
  3. **desdir-se** treu la marca (o quedaria una cel·la «mesurada» sense presa);
  4. les files **d'abans del camp** (`presa_at` NULL) es llegeixen com sempre — cap fila canvia
     de veredicte per la migració.
"""
import datetime

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase

from fhort.accounts.models import UserProfile
from fhort.fitting import services
from fhort.fitting.esdeveniments import linia_te_contingut
from fhort.fitting.models import (FittingSession, GradingVersion, PieceFitting,
                                  PieceFittingLine, SizeFitting)
from fhort.models_app.models import Model
from fhort.pom.models import POMMaster, SizeDefinition, SizeSystem


class BaseE2(TenantTestCase):

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
        self.ss = SizeSystem.objects.create(codi='SS_E2', nom='SS E2', base_unit='ALPHA')
        for i, et in enumerate(['S', 'M', 'L']):
            SizeDefinition.objects.create(size_system=self.ss, etiqueta=et, ordre=i)
        self.model = Model.objects.create(
            codi_intern='TST-E2', codi_tenant='TST', any=2027, sequencial=2,
            temporada='FW27', size_system=self.ss,
            size_run_model='S·M·L', base_size_label='M')
        user, _ = get_user_model().objects.get_or_create(
            username='qa_e2', defaults={'email': 'qa@e2.test'})
        self.perfil, _ = UserProfile.objects.get_or_create(
            user=user, defaults={'nom_complet': 'QA E2', 'rol_nom': 'QA'})
        self.sf = SizeFitting.objects.create(
            model=self.model, numero=1, codi='SF-E2', tipus='SizeSet',
            estat='Pendent', creat_per=self.perfil)
        self.gv = GradingVersion.objects.create(size_fitting=self.sf, version_number=1,
                                                is_active=True)
        self.sessio = FittingSession.objects.create(
            model=self.model, fase='Proto', responsable=self.perfil,
            data=datetime.date(2027, 2, 1), estat='Oberta')
        self.pf = PieceFitting.objects.create(session=self.sessio, model=self.model,
                                              grading_version=self.gv)

    def _linia(self, talla='M', teoric=50.0):
        """Una línia com la sembra la deixa: `valor_real == valor_teoric`, cap marca."""
        return PieceFittingLine.objects.create(
            piece_fitting=self.pf, pom=self.pom, size_label=talla,
            valor_teoric=teoric, valor_real=teoric)


class MarcaDePresaTest(BaseE2):

    def test_la_SEMBRA_no_es_una_presa(self):
        """🔒 LA LLEI D'E1, i va primera perquè és la que no es pot relaxar per fer passar la
        resta: existir no és haver mesurat."""
        linia = self._linia()
        self.assertIsNone(linia.presa_at)
        self.assertFalse(linia_te_contingut(linia),
                         'una línia acabada de sembrar no pot comptar com a mesurada')

    def test_confirmar_la_TEORICA_tal_qual_ES_una_presa(self):
        """🔴 EL CAS NOU D'E2b, i el que era impossible abans d'aquest camp.

        L'usuari veu el pre-omplert en fantasma i el confirma sense canviar res: el número
        desat és idèntic al teòric, o sigui que `valor_real != valor_teoric` diu FALS. Només
        la marca ho pot distingir."""
        self._linia(teoric=50.0)
        linia = services.desa_presa_escalat(
            self.model, pom_id=self.pom.id, capa='exterior', instancia='', garment='',
            talla='M', valor=50.0)
        self.assertEqual(float(linia.valor_real), float(linia.valor_teoric),
                         'el banc ha de provar el cas COINCIDENT, o no prova res')

        # 🔴 EL VERMELL, ACREDITAT AQUÍ MATEIX i no per una reversió temporal: aquest és el
        # predicat EXACTE d'abans d'E2/B1 (les tres condicions derivades de valors), i sobre
        # aquesta mateixa línia diu FALS. És la prova que el cas nou era indistinguible del
        # naixement i que el que el distingeix és la marca, no el número.
        predicat_vell = (
            bool((linia.decisio or '').strip())
            or bool((linia.nota or '').strip())
            or (linia.valor_real is not None and linia.valor_teoric is not None
                and float(linia.valor_real) != float(linia.valor_teoric)))
        self.assertFalse(predicat_vell,
                         'si el predicat vell ja ho veiés, aquest camp no caldria')

        self.assertIsNotNone(linia.presa_at, 'anotar ha de deixar marca')
        self.assertTrue(linia_te_contingut(linia),
                        'confirmar la teòrica tal qual ÉS una presa')

    def test_una_presa_que_es_desvia_segueix_sent_una_presa(self):
        """El cas que ja funcionava: no es pot trencar en arreglar l'altre."""
        self._linia(teoric=50.0)
        linia = services.desa_presa_escalat(
            self.model, pom_id=self.pom.id, capa='exterior', instancia='', garment='',
            talla='M', valor=53.5)
        self.assertIsNotNone(linia.presa_at)
        self.assertTrue(linia_te_contingut(linia))

    def test_DESDIR_SE_treu_la_marca_i_la_linia_torna_al_teoric(self):
        """`valor` buit és desdir-se. Deixar-hi la marca diria que algú ha mesurat una cel·la
        que ja no té cap presa — el defecte del naixement, girat."""
        self._linia(teoric=50.0)
        services.desa_presa_escalat(
            self.model, pom_id=self.pom.id, capa='exterior', instancia='', garment='',
            talla='M', valor=53.5)
        linia = services.desa_presa_escalat(
            self.model, pom_id=self.pom.id, capa='exterior', instancia='', garment='',
            talla='M', valor=None)
        self.assertIsNone(linia.presa_at, 'desdir-se ha de tornar al no-gest')
        self.assertEqual(float(linia.valor_real), 50.0)
        self.assertFalse(linia_te_contingut(linia))

    def test_les_files_D_ABANS_del_camp_es_llegeixen_com_sempre(self):
        """🚧 LA COMPATIBILITAT, i és el que fa que la migració no canviï cap veredicte.

        Amb `presa_at` NULL —totes les files d'abans del 17/08— manen les tres condicions
        velles: un número desviat, un veredicte o una nota. La marca es mira primera però no
        substitueix res."""
        desviada = self._linia(talla='S', teoric=48.0)
        desviada.valor_real = 49.0
        desviada.save(update_fields=['valor_real'])
        self.assertIsNone(desviada.presa_at)
        self.assertTrue(linia_te_contingut(desviada), 'el predicat vell segueix valent')

        amb_veredicte = self._linia(talla='L', teoric=52.0)
        amb_veredicte.decisio = 'ACCEPTED'
        amb_veredicte.save(update_fields=['decisio'])
        self.assertIsNone(amb_veredicte.presa_at)
        self.assertTrue(linia_te_contingut(amb_veredicte))

    def test_la_cella_del_payload_serveix_la_presa_coincident(self):
        """La vora de lectura: `_cella` no pot amagar una presa només perquè el número
        coincideix amb la teòrica (seria el defecte d'E2b servit des del backend)."""
        from fhort.fitting.escalat_presa_views import _cella
        self._linia(teoric=50.0)
        linia = services.desa_presa_escalat(
            self.model, pom_id=self.pom.id, capa='exterior', instancia='', garment='',
            talla='M', valor=50.0)
        c = _cella(linia)
        self.assertEqual(c['real'], 50.0, 'la presa coincident ha de sortir com a presa')
        self.assertEqual(c['teoric'], 50.0)
        self.assertEqual(c['desviacio'], 0.0,
                         'desviació 0 NO és el mateix que «no mesurat» (que és None)')

    def test_una_cella_sense_presa_serveix_real_None(self):
        """El contrapunt: sense gest, `real` és None i la pantalla ha de posar-hi el fantasma."""
        from fhort.fitting.escalat_presa_views import _cella
        c = _cella(self._linia(teoric=50.0))
        self.assertIsNone(c['real'])
        self.assertIsNone(c['desviacio'], 'no mesurat no és desviació zero')
