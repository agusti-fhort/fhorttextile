"""LA TAULA DE MESURES ÉS INTOCABLE — pin de no-regressió de `base_stages_view`.

Decisió d'Agus (28/07, innegociable): la taula de mesures és l'eina d'IMPRESSIÓ per als
fittings presencials. El sprint del Repàs llegeix la mateixa matèria primera
(`MeasurementChangeLog`) però NO pot moure ni un byte del que aquesta vista respon.

Això no és un test del comportament de la vista: és un PIN. Fixa la resposta sencera per a
un model fabricat aquí, camp a camp i en ordre. Si algú —aquest sprint o el que vingui—
toca `base_stages_view`, l'agrupació per (context, segon), el carry-forward dels snapshots
o la poda d'estadis buits, aquest test cau i obliga a mirar-s'ho. És la xarxa que fa que
«no toquem la taula de mesures» sigui una propietat verificada i no una bona intenció.

El Repàs viu al seu propi endpoint (`fitting/repas_views.py`) i no importa res d'aquí.

Convenció del repo: `python manage.py test fhort.models_app` (el projecte NO fa servir pytest).
"""
import datetime
import json

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.models_app.models import BaseMeasurement, MeasurementChangeLog, Model
from fhort.models_app.views import base_stages_view
from fhort.pom.models import POMMaster


class BaseStagesNoRegressioTest(TenantTestCase):

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
        self.user = get_user_model().objects.create(username='pinner')
        self.factory = APIRequestFactory()

        self.pom_a = POMMaster.objects.create(codi_client='CH', nom_client='Pit')
        self.pom_b = POMMaster.objects.create(codi_client='WA', nom_client='Cintura')
        self.model = Model.objects.create(
            codi_intern='TST-PIN', codi_tenant='TST', any=2026, sequencial=1,
            temporada='SS26', size_run_model='S·M·L', base_size_label='M',
        )
        # Ordre de fitxa invertit respecte a l'alta: la vista ha de seguir `ordre`.
        self.bm_a = BaseMeasurement.objects.create(
            model=self.model, pom=self.pom_a, ordre=2, base_value_cm=100.0,
            origen='MANUAL', nom_fitxa='PIT', is_key=True,
            tolerancia_minus=0.5, tolerancia_plus=0.5)
        self.bm_b = BaseMeasurement.objects.create(
            model=self.model, pom=self.pom_b, ordre=1, base_value_cm=80.0,
            origen='MANUAL', nom_fitxa='CINTURA')

    def _resposta(self):
        req = self.factory.get(f'/api/v1/models/{self.model.id}/base-stages/')
        force_authenticate(req, user=self.user)
        res = base_stages_view(req, self.model.id)
        self.assertEqual(res.status_code, 200)
        return json.loads(json.dumps(res.data))   # normalitza a JSON pur, com el client

    def test_les_claus_de_primer_nivell_son_exactament_aquestes(self):
        """Ni una clau més ni una menys: qui imprimeix la taula compta amb aquesta forma."""
        self.assertEqual(sorted(self._resposta().keys()), ['base_size', 'rows', 'stages'])

    def test_la_forma_de_cada_fila_es_exactament_aquesta(self):
        dades = self._resposta()
        self.assertEqual(dades['base_size'], 'M')
        self.assertEqual(len(dades['rows']), 2)
        self.assertEqual(sorted(dades['rows'][0].keys()), [
            # `nom_canonic_model` i `nom_traduit_model`: ampliació AUTORITZADA per l'Agus
            # 30/07 — sprint noms-POM (el bateig del model, buit = mana el catàleg).
            # `capa` i `instancia`: ampliació de C4/BLOC 2 (`6e259c8b`, 04/08) — la fila diu
            # de QUINA germana és, que és el que permet que dues mesures del mateix POM no es
            # confonguin a la taula. Aquest test va fer la seva feina: va detectar el canvi de
            # contracte, i el canvi era volgut.
            # `garment`: ampliació de SET-2/R11 (2026-08-11) — el TERCER eix, pel mateix
            # argument literal que `capa` i `instancia` un eix més tard. La fila diu de
            # quina PRENDA és, i sense això Comprovació no pot distingir dues peces del
            # mateix POM. Aquest test ha tornat a fer la seva feina: ha detectat el canvi
            # de contracte, i el canvi és volgut.
            # Tots són camps AFEGITS: cap dels altres canvia de nom, de valor ni d'ordre.
            'base_measurement_id', 'base_value_cm', 'capa', 'garment', 'instancia',
            'is_key',
            'nom_ca', 'nom_canonic_model', 'nom_en', 'nom_fitxa', 'nom_traduit_model',
            'pom_code', 'pom_id', 'takes', 'tol_minus', 'tol_plus',
        ])
        # L'ordre el mana `ordre` de la fitxa, no l'id d'alta.
        self.assertEqual([r['pom_code'] for r in dades['rows']], ['WA', 'CH'])
        fila_pit = dades['rows'][1]
        self.assertEqual(fila_pit['nom_fitxa'], 'PIT')
        self.assertEqual(fila_pit['base_value_cm'], 100.0)
        self.assertEqual(fila_pit['is_key'], True)
        self.assertEqual((fila_pit['tol_minus'], fila_pit['tol_plus']), (0.5, 0.5))
        # Els dos eixos no són decoratius: una mesura que no es desdobla els porta al seu
        # valor canònic, i és el que deixa que la germana en porti un altre sense col·lidir.
        self.assertEqual((fila_pit['capa'], fila_pit['instancia']), ('exterior', ''))

    def test_la_forma_de_cada_estadi_es_exactament_aquesta(self):
        """`key`, `context` i `at` — el trio que el front fa servir per pintar la capçalera."""
        estadis = self._resposta()['stages']
        self.assertTrue(estadis, 'la creació de les mesures ja ha de deixar estadi')
        for st in estadis:
            self.assertEqual(sorted(st.keys()), ['at', 'context', 'key'])
            # (la composició de la clau es valida a `test_els_estadis_agrupen_per_context_i_segon`)

    def test_la_tolerancia_per_defecte_segueix_essent_06(self):
        """Sense tolerància pròpia ni al POM, la vista posa 0.6. És un número que la gent
        del taller llegeix imprès: canviar-lo en silenci seria canviar el criteri d'acceptació."""
        fila_cintura = self._resposta()['rows'][0]
        self.assertEqual((fila_cintura['tol_minus'], fila_cintura['tol_plus']), (0.6, 0.6))

    def test_els_estadis_agrupen_per_context_i_segon(self):
        """La clau d'estadi és `<context>@<iso del segon>`: dos canvis del mateix context
        dins del mateix segon són UNA columna, no dues."""
        estadis = self._resposta()['stages']
        for st in estadis:
            ctx, _, moment = st['key'].partition('@')
            self.assertEqual(ctx, st['context'])
            self.assertNotIn('.', moment, 'el bucket ha de ser al segon, sense microsegons')

    def _separa_en_el_temps(self):
        """Reparteix els canvis ja registrats en segons distints.

        Cal fer-ho perquè els estadis s'agrupen per `<context>@<segon>` i un test corre sencer
        dins del mateix segon: sense això, dos canvis del mateix context col·lapsarien en una
        sola columna i la prova no miraria el que diu que mira. S'escriu amb `.update()` perquè
        `MeasurementChangeLog` és append-only i `save()` ho rebutjaria.
        """
        base = datetime.datetime(2026, 7, 28, 9, 0, 0, tzinfo=datetime.timezone.utc)
        for i, pk in enumerate(MeasurementChangeLog.objects.filter(model=self.model)
                               .order_by('created_at', 'id').values_list('pk', flat=True)):
            MeasurementChangeLog.objects.filter(pk=pk).update(
                created_at=base + datetime.timedelta(minutes=i))

    def test_el_carry_forward_es_mante(self):
        """Un estadi porta el valor vigent de CADA pom fins aquell moment, no només el que
        va canviar en aquell estadi."""
        self.bm_a.base_value_cm = 101.0
        self.bm_a.origen = 'FITTED'
        self.bm_a.save()
        self._separa_en_el_temps()

        dades = self._resposta()
        ultim = dades['stages'][-1]['key']
        preses = {r['pom_code']: r['takes'] for r in dades['rows']}
        self.assertEqual(preses['CH'][ultim], 101.0)
        self.assertIn(ultim, preses['WA'], 'carry-forward: la cintura arrossega el seu valor')
        self.assertEqual(preses['WA'][ultim], 80.0)

    def test_la_poda_nomes_es_menja_els_estadis_CAPDAVANTERS(self):
        """La poda d'estadis buits és més estreta del que sembla, i queda fixada aquí perquè
        ningú la «corregeixi» sense adonar-se'n.

        El filtre és `algun POM mostrat té valor en aquest snapshot`, i els snapshots són
        ACUMULATS. Per tant, un cop qualsevol POM mostrat té valor, tots els estadis
        posteriors el porten per carry-forward i cap més es pot podar — encara que aquell
        estadi només toqués un POM que avui està desactivat. Només cauen els estadis
        ANTERIORS a la primera presa d'un POM mostrat.
        """
        pom_x = POMMaster.objects.create(codi_client='XX', nom_client='Amagat')
        altre = Model.objects.create(
            codi_intern='TST-PODA', codi_tenant='TST', any=2026, sequencial=3,
            temporada='SS26', base_size_label='M')
        MeasurementChangeLog.objects.filter(model=altre).delete()

        # PRIMER el POM que després s'amagarà; DESPRÉS el que es veurà.
        bm_x = BaseMeasurement.objects.create(model=altre, pom=pom_x, ordre=1,
                                              base_value_cm=50.0, origen='MANUAL')
        BaseMeasurement.objects.create(model=altre, pom=self.pom_a, ordre=2,
                                       base_value_cm=100.0, origen='MANUAL')
        base = datetime.datetime(2026, 7, 28, 9, 0, 0, tzinfo=datetime.timezone.utc)
        for i, pk in enumerate(MeasurementChangeLog.objects.filter(model=altre)
                               .order_by('created_at', 'id').values_list('pk', flat=True)):
            MeasurementChangeLog.objects.filter(pk=pk).update(
                created_at=base + datetime.timedelta(minutes=i))

        def estadis():
            req = self.factory.get(f'/api/v1/models/{altre.id}/base-stages/')
            force_authenticate(req, user=self.user)
            return base_stages_view(req, altre.id).data['stages']

        abans = len(estadis())
        BaseMeasurement.objects.filter(pk=bm_x.pk).update(is_active=False)
        self.assertEqual(len(estadis()), abans - 1,
                         "l'estadi CAPDAVANTER d'un POM amagat sí que ha de caure")

    def test_amagar_un_POM_NO_esborra_els_estadis_posteriors(self):
        """La cara B de la poda: desactivar un POM del mig no fa desaparèixer la seva columna,
        perquè el snapshot acumulat hi porta els valors dels altres. Comportament VIGENT."""
        pom_c = POMMaster.objects.create(codi_client='HI', nom_client='Maluc')
        bm_c = BaseMeasurement.objects.create(model=self.model, pom=pom_c, ordre=3,
                                              base_value_cm=90.0, origen='MANUAL')
        self._separa_en_el_temps()
        abans = len(self._resposta()['stages'])

        BaseMeasurement.objects.filter(pk=bm_c.pk).update(is_active=False)
        self.assertEqual(len(self._resposta()['stages']), abans,
                         'la columna es manté: hi viuen els valors arrossegats dels altres POMs')

    def test_un_model_sense_historic_respon_igualment(self):
        """Degradació amb gràcia: sense canvis registrats, estadis buits però files senceres."""
        buit = Model.objects.create(
            codi_intern='TST-BUIT', codi_tenant='TST', any=2026, sequencial=2,
            temporada='SS26', base_size_label='M')
        MeasurementChangeLog.objects.filter(model=buit).delete()
        req = self.factory.get(f'/api/v1/models/{buit.id}/base-stages/')
        force_authenticate(req, user=self.user)
        res = base_stages_view(req, buit.id)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['stages'], [])
        self.assertEqual(res.data['rows'], [])


class NomesPresesDeTallaBaseTest(TenantTestCase):
    """FIX-2 (DIAGNOSI_MESURES_TEA_205) — la taula és de la TALLA BASE, i prou.

    El docstring de `base_stages_view` sempre ho ha promès («NOMÉS de la talla base») però
    la consulta es quedava tots els `MeasurementChangeLog` del model. Els overrides de talla
    NO-base —l'edició d'una cel·la d'Escalat i `set_size_override`— s'hi escriuen amb
    `base_measurement` a NULL, i com que els estadis són snapshots ACUMULATS, un override
    arrossegava el seu valor cap endavant per tota la fila.

    El cas és la fila B del model 205: base 46 cm, i dos overrides de valor 1 escrits a XXS i
    XS (algú va teclejar l'increment a la cel·la de la talla). La taula de base ensenyava el
    POM B caient de 46 a 1 — una base que la fitxa no ha tingut mai.
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
        self.user = get_user_model().objects.create(username='fix2')
        self.factory = APIRequestFactory()
        self.pom_b = POMMaster.objects.create(codi_client='B', nom_client='Llargada')
        self.model = Model.objects.create(
            codi_intern='TST-205', codi_tenant='TST', any=2026, sequencial=205,
            temporada='SS27', size_run_model='XXS·XS·S·M·L', base_size_label='S',
        )
        self.bm = BaseMeasurement.objects.create(
            model=self.model, pom=self.pom_b, ordre=1, base_value_cm=46.0, origen='IMPORT')

    def _overrides_de_talla(self):
        """Els dos logs d'Escalat del 205, tal com els escriu `escalat_ajustar_talla_view`."""
        for talla in ('XXS', 'XS'):
            MeasurementChangeLog.objects.create(
                model=self.model, pom=self.pom_b, base_measurement=None,
                valor_anterior=None, valor_nou=1.0, context='manual',
                motiu=f'Escalat talla {talla}')

    def _resposta(self):
        req = self.factory.get(f'/api/v1/models/{self.model.id}/base-stages/')
        force_authenticate(req, user=self.user)
        res = base_stages_view(req, self.model.id)
        self.assertEqual(res.status_code, 200)
        return res.data

    def test_els_overrides_de_talla_no_pinten_columna(self):
        abans = len(self._resposta()['stages'])
        self._overrides_de_talla()
        self.assertEqual(len(self._resposta()['stages']), abans,
                         'un override de talla no-base no és una presa de la talla base')

    def test_lhistoric_del_pom_no_cau_a_lincrement(self):
        """El símptoma exacte: la fila B no pot ensenyar mai el valor 1."""
        self._overrides_de_talla()
        fila = self._resposta()['rows'][0]
        self.assertEqual(fila['pom_code'], 'B')
        self.assertEqual(fila['base_value_cm'], 46.0)
        self.assertEqual(list(fila['takes'].values()), [46.0])
        self.assertNotIn(1.0, fila['takes'].values())

    def test_els_logs_segueixen_intactes(self):
        """No es neteja res: els overrides viuen al log (auditoria). Només no pinten taula."""
        self._overrides_de_talla()
        self._resposta()
        self.assertEqual(
            MeasurementChangeLog.objects.filter(
                model=self.model, base_measurement__isnull=True).count(), 2)

    def test_una_presa_de_base_posterior_si_que_hi_entra(self):
        """La cara B: després dels overrides, tocar la BASE sí que obre estadi nou."""
        self._overrides_de_talla()
        abans = len(self._resposta()['stages'])
        self.bm.base_value_cm = 47.0
        self.bm.origen = 'FITTED'
        self.bm.save()
        base = datetime.datetime(2026, 7, 29, 9, 0, 0, tzinfo=datetime.timezone.utc)
        for i, pk in enumerate(MeasurementChangeLog.objects.filter(model=self.model)
                               .order_by('created_at', 'id').values_list('pk', flat=True)):
            MeasurementChangeLog.objects.filter(pk=pk).update(
                created_at=base + datetime.timedelta(minutes=i))
        dades = self._resposta()
        self.assertEqual(len(dades['stages']), abans + 1)
        self.assertEqual(sorted(dades['rows'][0]['takes'].values()), [46.0, 47.0])
