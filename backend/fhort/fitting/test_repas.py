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

    # B2 (10/08) — LA TAULA PORTA SEMPRE TOTES LES MESURES DEL MODEL i la PRIMERA COLUMNA és
    # l'ENTRADA DE POMs. Les proves d'aquest fitxer llegien `rows[0]` donant per fet que només
    # hi havia files mesurades, i `sessions[0]` donant per fet que la primera columna era un
    # fitting. Cap de les dues coses és certa des d'aquest tram, i les afirmacions que
    # importaven —quins valors, en quin ordre, amb quin comentari— no en depenien: es demanen
    # per identitat i per origen.
    def _fila(self, data, pom):
        return next(r for r in data['rows'] if r['pom_id'] == pom.id)

    def _fittings(self, data):
        """Les columnes de FITTING: totes menys la d'entrada, que no n'és cap."""
        return [c for c in data['sessions'] if c['origen'] != 'ENTRADA']

    def _entrada(self, data):
        return next((c for c in data['sessions'] if c['origen'] == 'ENTRADA'), None)

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
        self.assertEqual([s['data'] for s in self._fittings(d)], ['2026-06-10', '2026-06-20'])

        fila = self._fila(d, self.pom_a)
        for camp in ('pom_id', 'codi', 'nom_en', 'nom_local', 'is_key', 'valors', 'ultim_comentari'):
            self.assertIn(camp, fila)
        primera, segona = (str(s['id']) for s in self._fittings(d))
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
        self.assertEqual([s['data'] for s in self._fittings(d)], ['2026-06-10'])
        self.assertEqual(len(self._fila(d, self.pom_a)['valors']), 1)

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
        self.assertIsNone(self._fila(self._get().data, self.pom_a)['ultim_comentari'])

    def test_comentaris_de_sessio(self):
        s, pf = self._sessio(10, notes='La model arriba tard')
        pf.gate = 'NO_OK'
        pf.gate_motiu = 'Màniga curta'
        pf.save(update_fields=['gate', 'gate_motiu'])
        self._linia(pf, self.pom_a, 'M', 60.0)
        sessio = self._fittings(self._get().data)[0]
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
        sid = str(self._fittings(d.data)[0]['id'])
        self.assertEqual(self._fila(d.data, self.pom_a)['valors'][sid]['valor_real'], 62.0)

    def test_base_no_presa_cau_a_la_primera_disponible(self):
        _, pf = self._sessio(10)
        self._linia(pf, self.pom_a, 'L', 62.0)   # cap línia a la base 'M'
        d = self._get().data
        self.assertEqual(d['talla'], 'L')
        # Les files hi són totes (B2), però fora de la base NO hi ha columna d'entrada: la
        # columna d'origen és `BaseMeasurement`, i ensenyar-la a una altra talla seria mentir
        # sobre quina talla es va entrar.
        self.assertIsNone(self._entrada(d))
        self.assertEqual(len(self._fittings(d)), 1)
        self.assertEqual(self._fila(d, self.pom_a)['valors'][
            str(self._fittings(d)[0]['id'])]['valor_real'], 62.0)
        self.assertEqual(self._fila(d, self.pom_b)['valors'], {})

    def test_model_sense_fittings(self):
        """Cap columna, però les FILES hi són: el cens de mesures del model existeix encara que
        ningú no n'hagi provat cap. És el front qui en diu «encara no té cap fitting fet»."""
        d = self._get().data
        self.assertEqual(d['sessions'], [])
        self.assertEqual([r['pom_id'] for r in d['rows']], [self.pom_b.id, self.pom_a.id])
        self.assertTrue(all(r['valors'] == {} for r in d['rows']))
        self.assertIsNone(d['talla'])


class FittingRepasEtapesTest(FittingRepasTest):
    """UN FITTING NO ÉS SEMPRE UNA FittingSession (decisió Agus, 28/07).

    Al despatx els fittings s'escriuen a mà i s'entren a la TAULA DE MESURES. El cens de
    `fhort` ho confirma: 13 models tenen història de mesures i només 3 tenen PieceFitting —
    per a 10 el Repàs deia «cap fitting registrat» amb la feina feta a l'altra taula.

    Aquí es blinda que el Repàs reculli TOT el que és fitting, vingui de l'eina o de la
    taula, i —igual d'important— que NO reculli el que no ho és.
    """

    # ── Cas TATE: model amb NOMÉS etapes, cap sessió ──────────────────────────
    def test_model_sense_cap_sessio_pero_amb_etapes_treu_columnes(self):
        self._neteja_log()
        self._etapa(self.pom_a, 61.0, dia=15)

        d = self._get().data
        self.assertEqual(len(self._fittings(d)), 1, 'una etapa és una columna')
        col = self._fittings(d)[0]
        self.assertEqual(col['origen'], 'MANUAL')
        self.assertTrue(str(col['id']).startswith('etapa:'))
        self.assertEqual(self._fila(d, self.pom_a)['valors'][col['id']]['valor_real'], 61.0)
        self.assertEqual(d['talla'], 'M', 'les etapes viuen a la talla base')

    def test_el_buit_honest_nomes_si_no_hi_ha_NI_sessions_NI_etapes(self):
        self._neteja_log()
        d = self._get().data
        self.assertEqual(d['sessions'], [], 'cap columna: ni fitting ni entrada amb valor')
        self.assertTrue(all(r['valors'] == {} for r in d['rows']),
                        'i cap fila amb res a dir')

    # ── El criteri d'inclusió ────────────────────────────────────────────────
    def test_una_alta_inicial_NO_es_un_fitting(self):
        """`manual` amb valor_anterior NUL és algú donant d'alta la fitxa, no mesurant una
        peça. Al cens de `fhort` són 23 dels 28 events manuals: sense aquest filtre, el
        Repàs s'ompliria de columnes que no són fittings."""
        self._neteja_log()
        self._etapa(self.pom_a, 60.0, anterior=None)
        # B2 — es mira que no faci FITTING. La columna d'ENTRADA sí que hi pot ser, i és
        # justament el que una alta inicial és: el punt de partida, no una presa.
        self.assertEqual(self._fittings(self._get().data), [])

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
        self.assertEqual(self._fittings(self._get().data), [],
                         'moure dades no és mesurar una peça')

    def test_els_tres_contextos_de_mesura_hi_entren(self):
        self._neteja_log()
        self._etapa(self.pom_a, 61.0, origen='MANUAL', dia=10)
        self._etapa(self.pom_a, 62.0, origen='CHECKED', dia=11)
        self._etapa(self.pom_a, 63.0, origen='FITTED', dia=12)
        self.assertEqual([c['origen'] for c in self._fittings(self._get().data)],
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
        fittings = self._fittings(d)
        self.assertEqual([c['origen'] for c in fittings], ['SESSIO', 'MANUAL', 'SESSIO'])
        self.assertEqual([c['data'][:10] for c in fittings],
                         ['2026-06-10', '2026-06-15', '2026-06-20'])
        valors = self._fila(d, self.pom_a)['valors']
        self.assertEqual([valors[str(c['id'])]['valor_real'] for c in fittings],
                         [60.0, 61.0, 62.0])
        # …i l'ENTRADA va davant de tot, sempre (B2).
        self.assertEqual(d['sessions'][0]['origen'], 'ENTRADA')

    def test_una_etapa_no_arrossega_POMs_que_ningu_va_tocar(self):
        """Sense carry-forward, a diferència de la taula de mesures: allà cada columna és un
        snapshot de la fitxa; aquí és UN esdeveniment. Arrossegar faria semblar que es van
        prendre mesures que ningú va prendre."""
        self._neteja_log()
        self._etapa(self.pom_a, 61.0, dia=15)      # només el pit

        d = self._get().data
        clau = self._fittings(d)[0]['id']
        per_pom = {r['pom_id']: r for r in d['rows']}
        self.assertIn(clau, per_pom[self.pom_a.id]['valors'])
        # B2 (10/08) — LA FILA HI ÉS, LA CEL·LA NO. La versió anterior comprovava que el POM no
        # mesurat no fes FILA, i des que la taula porta el cens sencer això ja no és el que
        # separa el gra de la palla: el que no pot passar és que una columna d'etapa arrossegui
        # un valor que ningú no va prendre aquell dia. La fila de la cintura hi és —diu que
        # ningú no l'ha comprovada— i la seva cel·la d'aquella etapa està buida.
        self.assertIn(self.pom_b.id, per_pom, 'la taula porta totes les mesures del model')
        self.assertNotIn(clau, per_pom[self.pom_b.id]['valors'],
                         'un POM que ningú va mesurar no té valor en aquella columna')

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

        ultim = self._fila(self._get().data, self.pom_a)['ultim_comentari']
        self.assertIn('vora curta', ultim['text'])
        self.assertIn('Tolerància acceptada', ultim['text'], 'la DECISIÓ també es diu')

    def test_si_l_etapa_no_comenta_val_el_comentari_anterior_de_la_sessio(self):
        self._neteja_log()
        _, pf = self._sessio(10)
        self._linia(pf, self.pom_a, 'M', 60.0, nota='de la sessió')
        self._etapa(self.pom_a, 61.0, dia=20)      # etapa POSTERIOR, sense nota

        ultim = self._fila(self._get().data, self.pom_a)['ultim_comentari']
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


class RepasB2Test(FittingRepasTest):
    """B2 · EL REPÀS REDISSENYAT (ordre d'Agus, 10/08).

    Quatre coses, i totes quatre venien d'una queixa concreta a pantalla sobre el model 1320:

      · la taula porta SEMPRE totes les mesures del model (n'amagava amb «—»);
      · la PRIMERA columna és l'ENTRADA DE POMs, la base d'origen;
      · cada fitting és una columna nova, en ordre cronològic;
      · fora les columnes duplicades sense contingut («DEV @09/08» × 2);
      · i ELS CANVIS es marquen, amb el veredicte de la modista com a color.
    """

    def _amb_base(self, pom, valor):
        """Dona valor d'entrada a una mesura (és el que fa néixer la columna d'origen)."""
        bm = BaseMeasurement.objects.get(model=self.model, pom=pom)
        bm.base_value_cm = valor
        bm.save()
        return bm

    # ── La primera columna ────────────────────────────────────────────────────────────
    def test_la_primera_columna_es_lentrada_de_poms(self):
        self._amb_base(self.pom_a, 58.0)
        _, pf = self._sessio(10)
        self._linia(pf, self.pom_a, 'M', 60.0)

        d = self._get().data
        self.assertEqual(d['sessions'][0]['origen'], 'ENTRADA')
        self.assertEqual(self._fila(d, self.pom_a)['valors']['entrada']['valor_real'], 58.0)

    def test_lentrada_es_el_valor_ABANS_de_la_primera_re_mesura(self):
        """La columna d'origen no és la base d'ARA: és d'on es partia. Si un fitting ja ha
        mogut la base, ensenyar el valor d'avui faria desaparèixer el canvi que la taula ha
        d'explicar."""
        self._amb_base(self.pom_a, 58.0)          # el signal escriu l'alta al log
        bm = BaseMeasurement.objects.get(model=self.model, pom=self.pom_a)
        bm.base_value_cm = 60.0                   # i després algú la mou
        bm.save()

        d = self._get().data
        self.assertEqual(self._fila(d, self.pom_a)['valors']['entrada']['valor_real'], 58.0)

    def test_sense_cap_valor_entrat_no_hi_ha_columna_dorigen(self):
        _, pf = self._sessio(10)
        self._linia(pf, self.pom_a, 'M', 60.0)
        self.assertIsNone(self._entrada(self._get().data))

    # ── Totes les mesures ─────────────────────────────────────────────────────────────
    def test_la_taula_porta_totes_les_mesures_del_model(self):
        self._amb_base(self.pom_a, 58.0)
        _, pf = self._sessio(10)
        self._linia(pf, self.pom_a, 'M', 60.0)    # NOMÉS el pit s'ha fitat

        rows = self._get().data['rows']
        self.assertEqual([r['pom_id'] for r in rows], [self.pom_b.id, self.pom_a.id],
                         'la cintura hi és encara que ningú no l\'hagi provada mai')

    def test_una_mesura_desactivada_no_fa_fila(self):
        """El cens és de mesures VIVES: una fila retirada de la fitxa no torna pel Repàs."""
        self._amb_base(self.pom_a, 58.0)
        bm_b = BaseMeasurement.objects.get(model=self.model, pom=self.pom_b)
        bm_b.is_active = False
        bm_b.save(update_fields=['is_active'])

        rows = self._get().data['rows']
        self.assertEqual([r['pom_id'] for r in rows], [self.pom_a.id])

    # ── Les columnes sense contingut ──────────────────────────────────────────────────
    def test_una_graella_oberta_i_no_tocada_no_fa_columna(self):
        """El cas exacte del 1320: dues columnes «DEV @09/08», i la segona era una graella que
        algú va obrir —`valor_real == valor_teoric`, cap veredicte, cap nota— i no va tocar."""
        _, pf_fet = self._sessio(10)
        self._linia(pf_fet, self.pom_a, 'M', 60.0, teoric=58.0)     # s'hi va mesurar
        _, pf_verge = self._sessio(11)
        self._linia(pf_verge, self.pom_a, 'M', 58.0, teoric=58.0)   # sembrada i prou

        d = self._get().data
        self.assertEqual([s['data'] for s in self._fittings(d)], ['2026-06-10'])

    def test_una_nota_sola_ja_es_contingut(self):
        """Confirmar un número sense moure'l és una decisió, i deixar-hi escrit per què també:
        el predicat no és «ha canviat el valor», és «algú hi ha dit alguna cosa»."""
        _, pf = self._sessio(10)
        self._linia(pf, self.pom_a, 'M', 58.0, teoric=58.0, nota='queda bé així')
        self.assertEqual(len(self._fittings(self._get().data)), 1)

    def test_un_veredicte_sol_ja_es_contingut(self):
        _, pf = self._sessio(10)
        l = self._linia(pf, self.pom_a, 'M', 58.0, teoric=58.0)
        l.decisio = 'ACCEPTED'
        l.save(update_fields=['decisio'])
        self.assertEqual(len(self._fittings(self._get().data)), 1)

    def test_letapa_que_nomes_es_el_retorn_dun_fitting_no_duplica_columna(self):
        """Un fitting fet amb l'eina escriu a les seves línies I a la taula de mesures. La
        segona escriptura sortia com una columna pròpia, amb la mateixa data i els mateixos
        números. El pont és el `motiu` del log, que diu de quina sessió ve."""
        self._neteja_log()
        s, pf = self._sessio(10)
        self._linia(pf, self.pom_a, 'M', 61.0, teoric=60.0)
        self._etapa(self.pom_a, 61.0, origen='FITTED', dia=10,
                    motiu=f'Fitting · sessió {s.pk} · peça {pf.pk}')

        d = self._get().data
        self.assertEqual([c['origen'] for c in self._fittings(d)], ['SESSIO'])

    def test_una_etapa_escrita_a_ma_SI_fa_columna(self):
        """La decisió d'Agus del 28/07 no es toca: al despatx els fittings s'escriuen a mà a la
        taula de mesures i no obren cap sessió. Aquestes etapes no dupliquen res."""
        self._neteja_log()
        self._sessio(10)                          # sessió sense línies: no fa columna
        self._etapa(self.pom_a, 61.0, origen='MANUAL', dia=15)
        self.assertEqual([c['origen'] for c in self._fittings(self._get().data)], ['MANUAL'])

    # ── Els canvis es marquen ─────────────────────────────────────────────────────────
    def test_el_canvi_es_marca_i_el_veredicte_viatja(self):
        self._amb_base(self.pom_a, 58.0)
        _, pf = self._sessio(10)
        l = self._linia(pf, self.pom_a, 'M', 60.0, teoric=58.0)
        l.decisio = 'ADJUSTED'
        l.save(update_fields=['decisio'])

        valors = self._fila(self._get().data, self.pom_a)['valors']
        self.assertFalse(valors['entrada']['canvi'], 'la primera columna no canvia res')
        cel = valors[str(pf.session_id)]
        self.assertTrue(cel['canvi'])
        self.assertEqual(cel['veredicte'], 'ADJUSTED')

    def test_confirmar_el_mateix_numero_NO_es_un_canvi(self):
        self._amb_base(self.pom_a, 58.0)
        _, pf = self._sessio(10)
        l = self._linia(pf, self.pom_a, 'M', 58.0, teoric=58.0)
        l.decisio = 'ACCEPTED'
        l.save(update_fields=['decisio'])

        cel = self._fila(self._get().data, self.pom_a)['valors'][str(pf.session_id)]
        self.assertFalse(cel['canvi'], 'el mateix número no és res de nou')

    def test_el_canvi_es_contra_lultima_columna_AMB_valor(self):
        """Si un fitting no toca un POM, el següent que el toqui s'ha de llegir contra l'últim
        número que se'n va dir, no contra un buit."""
        self._amb_base(self.pom_a, 58.0)
        _, pf1 = self._sessio(10)
        self._linia(pf1, self.pom_a, 'M', 60.0, teoric=58.0)
        _, pf2 = self._sessio(20)
        self._linia(pf2, self.pom_b, 'M', 40.0, teoric=38.0)   # aquest no toca el pit
        _, pf3 = self._sessio(30)
        # La 3a sessió ha de tenir CONTINGUT o no fa columna (és el predicat d'aquest
        # tram): el seu teòric ve de l'spec vella (58) i el real confirma el 60 de la 1a.
        self._linia(pf3, self.pom_a, 'M', 60.0, teoric=58.0)

        valors = self._fila(self._get().data, self.pom_a)['valors']
        self.assertTrue(valors[str(pf1.session_id)]['canvi'], '58 → 60')
        self.assertNotIn(str(pf2.session_id), valors, 'no el va tocar')
        self.assertFalse(valors[str(pf3.session_id)]['canvi'],
                         '60 → 60 contra la 1a sessió, no contra el buit de la 2a')
