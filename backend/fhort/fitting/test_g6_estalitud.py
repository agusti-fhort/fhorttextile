"""G6-B2 — L'ESTALITUD: una versió aprovada, ¿encara diu la veritat?

El sistema té dues lleis que no es toquen: **la mesura és sobirana** (mai es bloqueja pel segell)
i **el segell és honest** (mai s'auto-actualitza). De les dues juntes en surt, inevitablement, que
una versió aprovada pot quedar enrere — i l'única sortida honesta és que el sistema ho DIGUI.

Aquests tests exerceixen el **setè camí** amb el codi de debò (`resolve_size_check`), no amb una
imitació: és l'únic que demostra que el detector veu el que passa de veritat.
"""
import datetime

from django.db import IntegrityError, transaction

from fhort.fitting.models import GradedSpec, GradingVersion
from fhort.fitting.staleness import DESCONEGUDA, ESTALA, FRESCA, NO_SEGELLADA, estalitud
from fhort.models_app.models import BaseMeasurement, Model, SizeCheck, SizeCheckLine
from fhort.models_app.services_size_check import resolve_size_check
from fhort.pom.services import bump_grading_version_and_generate
from fhort.pom.test_g6_segell import _SegellBase


class _BancSegellat(_SegellBase):
    """El banc de G6-B1, amb el segell DATAT DESPRÉS de les mesures que segella.

    `_SegellBase` segella amb una data fixa (2026-07-01) que és ANTERIOR a les files de
    `BaseMeasurement` que el seu propi `setUp` acaba d'escriure. Per al guard del segell tant li
    feia; per al detector d'estalitud no, i **amb raó**: un segell datat abans de la base que
    signa vol dir, literalment, que la base ha canviat després del segell. El fixture es corregeix
    aquí en comptes d'afluixar el detector — el detector té raó.
    """

    def setUp(self):
        super().setUp()
        self.gv.data_aprovacio = datetime.datetime.now(datetime.timezone.utc)
        self.gv.save(update_fields=['data_aprovacio'])


class EstalitudTest(_BancSegellat):
    """El detector, sobre el mateix banc que va servir per tancar el segell (G6-B1)."""

    def _segella(self, gv, quan=None):
        gv.aprovada = True
        gv.aprovada_per = self.profile
        gv.data_aprovacio = quan or datetime.datetime.now(datetime.timezone.utc)
        gv.save()
        return gv

    def _mou_la_base(self, valor=45.0, origen='MANUAL'):
        """Escriu una mesura base NOVA. El signal append-only en deixa constància."""
        bm = BaseMeasurement.objects.get(model=self.model, pom=self.pom)
        bm.base_value_cm = valor
        bm.origen = origen
        bm.save()
        return bm

    # ── el punt de partida ──────────────────────────────────────────────────
    def test_una_versio_NO_segellada_no_pot_quedar_enrere(self):
        """Qui no promet res no pot faltar a la seva paraula."""
        self.gv.aprovada = False
        self.gv.save()

        self.assertEqual(estalitud(self.gv).estat, NO_SEGELLADA)

    def test_segellada_i_la_base_quieta_es_FRESCA(self):
        self.assertEqual(estalitud(self.gv).estat, FRESCA)
        self.assertFalse(estalitud(self.gv).avisa)

    # ── EL SETÈ CAMÍ, amb el codi de debò ───────────────────────────────────
    def test_el_SETE_CAMI_canviar_la_base_sota_el_segell_deixa_la_versio_ESTALA(self):
        """`resolve_size_check` REAL: es grava una mesura base nova sobre un model segellat.

        La mesura NO es bloqueja (és sobirana) i el segell NO s'auto-actualitza (és honest). La
        conseqüència és que la versió aprovada ha quedat enrere — i el sistema ho ha de dir.
        """
        sc = SizeCheck.objects.create(
            model=self.model, estat='Pendent', talla_base_label='M')
        SizeCheckLine.objects.create(
            size_check=sc, pom=self.pom, valor_teoric=40.0, valor_real=44.0)

        resolve_size_check(
            sc.id, 'Acceptat', user_profile_id=self.profile.id,
            allow_reopen_sealed=True,
        )

        self.gv.refresh_from_db()
        e = estalitud(self.gv)
        self.assertEqual(e.estat, ESTALA)
        self.assertTrue(e.avisa)
        self.assertGreaterEqual(e.canvis_base, 1)
        # L'avís porta LES XIFRES, no un adjectiu: quin POM i quan.
        self.assertIn(self.pom.codi_client, e.poms_afectats)
        self.assertIsNotNone(e.ultim_canvi)

    def test_el_desa_de_la_fitxa_tambe_la_deixa_estala_encara_que_el_COMPTADOR_no_ho_vegi(self):
        """El forat que `generated_from_version` sol NO tapava.

        `measurements_version` només s'incrementa a `bump_grading_version_and_generate`. El desa de
        la fitxa (`pom/wizard_views.py`) escriu la base directament i no toca el comptador: per
        aquest camí la base es mou i el comptador no se n'assabenta. Qui ho veu és el registre
        append-only, i per això el detector el mira A ELL primer.
        """
        mv_abans = Model.objects.values_list(
            'measurements_version', flat=True).get(pk=self.model.pk)

        self._mou_la_base(45.0)

        mv_despres = Model.objects.values_list(
            'measurements_version', flat=True).get(pk=self.model.pk)
        self.assertEqual(mv_abans, mv_despres)        # el comptador NO s'ha mogut…
        self.assertEqual(estalitud(self.gv).estat, ESTALA)   # …i tanmateix és estala

    # ── la sortida: superar-la i tornar a signar ────────────────────────────
    def test_despres_de_BUMP_i_RESEGELL_la_versio_nova_es_FRESCA(self):
        """La reparació no és re-signar la vella: és fer-ne una de nova i signar-la."""
        self._mou_la_base(45.0)
        self.assertEqual(estalitud(self.gv).estat, ESTALA)

        nova = bump_grading_version_and_generate(
            self.sf.id, base_changed=True, profile_id=self.profile.id,
            allow_reopen_sealed=True, reopen_context='test',
        )
        self._segella(nova, quan=datetime.datetime.now(datetime.timezone.utc))

        self.assertEqual(estalitud(nova).estat, FRESCA)
        # I la VELLA continua sent estala: el que algú va signar aquell dia no canvia.
        self.gv.refresh_from_db()
        self.assertEqual(estalitud(self.gv).estat, ESTALA)

    # ── el quart estat: no saber ────────────────────────────────────────────
    def test_un_segell_SENSE_DATA_i_sense_rastre_es_DESCONEGUDA_no_fresca(self):
        """Les dues versions aprovades per un camí de codi que ja no existeix (R11).

        No saber i dir que va bé són coses diferents. El que va a la taula de tall no pot dependre
        d'un silenci.
        """
        self.gv.data_aprovacio = None
        self.gv.save()
        GradedSpec.objects.filter(grading_version=self.gv).update(generated_from_version=None)

        e = estalitud(self.gv)
        self.assertEqual(e.estat, DESCONEGUDA)
        self.assertTrue(e.avisa)          # s'ensenya amb avís: no es dona per bona

    def test_sense_data_de_segell_el_COMPTADOR_encara_parla(self):
        """El segon testimoni: veu menys (no sap dir QUAN) però sap dir que sí."""
        self.gv.data_aprovacio = None
        self.gv.save()
        GradedSpec.objects.filter(grading_version=self.gv).update(generated_from_version=1)
        Model.objects.filter(pk=self.model.pk).update(measurements_version=9)

        self.assertEqual(estalitud(self.gv).estat, ESTALA)


class AvisAlMotorTest(_BancSegellat):
    """L'avís no es queda a la UI: viatja amb el snapshot del motor i arriba al gate."""

    def test_el_snapshot_del_motor_porta_lavis_destalitud(self):
        from fhort.patterns.adapters import DjangoGradingSource

        BaseMeasurement.objects.filter(model=self.model, pom=self.pom).update(base_value_cm=45)
        bm = BaseMeasurement.objects.get(model=self.model, pom=self.pom)
        bm.base_value_cm = 46
        bm.save()          # deixa rastre al registre append-only

        snap = DjangoGradingSource().snapshot(self.gv.id)

        # El guard dur NO canvia: aprovada segueix sent aprovada, i la niada es pot generar.
        self.assertTrue(snap.approved)
        # Però l'avís viatja amb ella: qui exporti se'n pot fer responsable SABENT-HO.
        self.assertTrue(snap.estala)
        self.assertIn('base ha canviat', snap.avis_estalitud)

    def test_el_gate_dexportacio_ESCRIU_lavis_al_reconeixement(self):
        """`texts_shown` és el text LITERAL que se li va ensenyar a qui va exportar.

        Si el text vingués sencer del client, el client podria ometre'n l'avís que més importa — i
        el registre diria que aquella persona va acceptar una cosa que no se li va dir.
        """
        from fhort.patterns.views import _texts_del_gate

        bm = BaseMeasurement.objects.get(model=self.model, pom=self.pom)
        bm.base_value_cm = 47
        bm.save()

        texts = _texts_del_gate('El text que envia el client', self.gv.id)

        self.assertIn('El text que envia el client', texts)
        self.assertIn('base ha canviat', texts)     # …i l'avís que el client no ha enviat

    def test_una_versio_FRESCA_no_embruta_el_reconeixement(self):
        from fhort.patterns.views import _texts_del_gate

        texts = _texts_del_gate('Text del client', self.gv.id)

        self.assertEqual(texts, 'Text del client')


class R7UnaSolaActivaTest(_BancSegellat):
    """R7 — la BD té una opinió sobre quantes versions poden ser vigents alhora."""

    def test_una_segona_ACTIVA_rebota(self):
        """L'invariant ja el respectava el codi. Ara no depèn que tothom hi passi."""
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                GradingVersion.objects.create(
                    size_fitting=self.sf, version_number=99, is_active=True, nom='intrusa')

    def test_una_segona_APROVADA_inactiva_SI_que_entra(self):
        """L'historial d'aprovades és LEGÍTIM: un segell vell ha de poder continuar dient què es
        va signar aquell dia. `aprovada` i `is_active` són ortogonals."""
        gv2 = GradingVersion.objects.create(
            size_fitting=self.sf, version_number=98, is_active=False,
            aprovada=True, nom='historial')

        self.assertEqual(
            GradingVersion.objects.filter(size_fitting=self.sf, aprovada=True).count(), 2)
        self.assertEqual(
            GradingVersion.objects.filter(size_fitting=self.sf, is_active=True).count(), 1)
        self.assertFalse(gv2.is_active)

    def test_el_bump_normal_continua_funcionant_amb_la_constraint(self):
        """El camí viu: desactiva l'activa i crea la nova. Si la constraint el trenqués, hauríem
        canviat una invariant de cortesia per una avaria."""
        nova = bump_grading_version_and_generate(
            self.sf.id, base_changed=True, profile_id=self.profile.id,
            allow_reopen_sealed=True, reopen_context='test',
        )

        self.assertTrue(nova.is_active)
        self.assertEqual(
            GradingVersion.objects.filter(size_fitting=self.sf, is_active=True).count(), 1)
