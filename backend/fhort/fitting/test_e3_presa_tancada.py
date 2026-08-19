"""E3a · EL CINQUÈ ESTAT — una presa SEGELLADA té nom, i deixa de ser el no-res.

Substrat: `docs/diagnosis/DIAGNOSI_QA_2054_REGRESSIO_O_FORAT.md` (arrel única).

🚨 EL COR D'AQUEST BANC ÉS `test_segellada_i_cap_presa_NO_donen_el_mateix_payload`. Tota la
resta és contorn. El forat que E3a tanca no era un càlcul equivocat: era que el GET responia
**exactament el mateix** per a un model que acabava de segellar una presa de 90 línies i per a
un que no n'ha tingut mai cap. D'aquell únic empat en penjaven tres símptomes que a la QA
semblaven tres bugs (graella editable amb 409 per cel·la, sub-tab de Decisió que no obre, i el
racó oferint obrir una presa sobre una acta acabada de tancar). Si algun dia algú torna a
col·lapsar els dos casos, aquest test és l'única cosa que ho dirà.

I la meitat que el sosté és `test_llegir_l_acta_NO_obre_cap_porta_d_escriptura`: servir les
dades d'una sessió tancada no pot convertir-la en escrivible. La lectura s'amplia; el guard no.
"""
import datetime

from fhort.fitting.models import FittingSession, PieceFitting, PieceFittingLine

from .test_e1_presa_escalat import BASE, MARE, SEGONA, TEORICS, PresaEscalatBase


class PresaTancadaBase(PresaEscalatBase):
    """Reusa el fixture d'E1 sencer: mateix model, mateix POM viu a DUES prendes."""

    def _presa(self, *, estat, data, anotada=None):
        """Una presa amb el seu estat i la seva data. `anotada` = {(garment, talla): valor}.

        S'escriu `presa_at` a mà i no per l'API a posta: sobre una sessió `Tancada` l'API no
        deixa escriure —que és justament el que l'altre test comprova—, i aquí el que cal és
        una ACTA ja feta, no el camí per fer-la.
        """
        sessio = FittingSession.objects.create(
            model=self.model, fase='Dev', data=data, estat=estat)
        pf = PieceFitting.objects.create(session=sessio, model=self.model,
                                         grading_version=self.gv)
        linies = {}
        for garment, base_val in ((MARE, TEORICS[BASE]), (SEGONA, 30.0)):
            for sl, v in TEORICS.items():
                teoric = v if garment == MARE else base_val + (v - TEORICS[BASE])
                real = (anotada or {}).get((garment, sl))
                linies[(garment, sl)] = PieceFittingLine.objects.create(
                    piece_fitting=pf, pom=self.pom, size_label=sl, garment=garment,
                    valor_teoric=teoric,
                    valor_real=(real if real is not None else teoric),
                    presa_at=(datetime.datetime(2026, 8, 16, 12, 0,
                                                tzinfo=datetime.timezone.utc)
                              if real is not None else None))
        return sessio, pf, linies


class TancadaTeNomTest(PresaTancadaBase):

    def test_segellada_i_cap_presa_NO_donen_el_mateix_payload(self):
        """🚨 EL COR. Dos estats oposats no poden compartir resposta."""
        buit = self._get().data
        self.assertEqual(buit['presa_oberta'], False)
        self.assertEqual(buit['presa_tancada'], False)
        self.assertIsNone(buit['session'])
        self.assertEqual(buit['preses'], {})

        self._presa(estat='Tancada', data=datetime.date(2026, 8, 16),
                    anotada={(MARE, 'L'): 53.4, (MARE, 'S'): 47.5})
        acta = self._get().data

        # ELS DOS BOOLEANS, que és el que la pantalla mira per triar estat.
        self.assertEqual(acta['presa_oberta'], False)     # no s'hi escriu…
        self.assertEqual(acta['presa_tancada'], True)     # …però HI ÉS.
        # I la diferència no és només una bandera: l'acta porta les dades.
        self.assertNotEqual(acta['preses'], {})
        self.assertNotEqual(acta['session'], buit['session'])

    def test_l_acta_diu_QUAN_i_EN_QUIN_ESTAT(self):
        """El racó ha de poder escriure «Presa del 16/08 · tancada» sense preguntar enlloc més."""
        sessio, _, _ = self._presa(estat='Tancada', data=datetime.date(2026, 8, 16),
                                   anotada={(MARE, 'L'): 53.4})
        s = self._get().data['session']
        self.assertEqual(s['id'], sessio.id)
        self.assertEqual(s['data'], '2026-08-16')
        self.assertEqual(s['estat'], 'Tancada')

    def test_els_valors_de_la_presa_tancada_son_VISIBLES(self):
        """La graella queda read-only, però no buida: una acta que no s'ensenya no serveix."""
        self._presa(estat='Tancada', data=datetime.date(2026, 8, 16),
                    anotada={(MARE, 'L'): 53.4, (SEGONA, 'S'): 27.5})
        d = self._get().data
        self.assertEqual(d['preses'][self._clau(MARE, 'L')]['real'], 53.4)
        self.assertEqual(d['preses'][self._clau(SEGONA, 'S')]['real'], 27.5)
        # I la desviació segueix sortint del servidor, com a la presa viva.
        self.assertEqual(d['preses'][self._clau(MARE, 'L')]['desviacio'], 1.4)
        # Les que ningú no va mesurar segueixen dient `null`: no mesurat ≠ desviació zero.
        self.assertIsNone(d['preses'][self._clau(MARE, 'XL')]['real'])
        self.assertEqual(d['resum']['n_preses'], 2)
        self.assertEqual(d['resum']['n_linies'], len(TEORICS) * 2)

    def test_llegir_l_acta_NO_obre_cap_porta_d_escriptura(self):
        """🚨 La lectura s'amplia; el guard NO. Servir-la no la fa escrivible."""
        _, _, linies = self._presa(estat='Tancada', data=datetime.date(2026, 8, 16),
                                   anotada={(MARE, 'L'): 53.4})
        self.assertEqual(self._get().data['presa_tancada'], True)   # es llegeix…
        r = self._post(pom_id=self.pom.id, talla='L', valor=99.9)   # …i no s'hi escriu.
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.data['codi'], 'sense_presa_oberta')
        self.assertEqual(
            float(PieceFittingLine.objects.get(pk=linies[(MARE, 'L')].pk).valor_real), 53.4)

    def test_anullada_tambe_es_una_acta(self):
        """`SEALED_SESSION_ESTATS` són DOS. Mirar només 'Tancada' seria una tercera llei."""
        self._presa(estat='Anullada', data=datetime.date(2026, 8, 16),
                    anotada={(MARE, 'L'): 53.4})
        d = self._get().data
        self.assertEqual(d['presa_tancada'], True)
        self.assertEqual(d['session']['estat'], 'Anullada')


class PrecedenciaTest(PresaTancadaBase):
    """Qui mana quan n'hi ha més d'una. Mateix ordre que `peca_de_presa_del_model`."""

    def test_la_VIVA_mana_sobre_la_segellada_encara_que_sigui_mes_antiga(self):
        """L'ordre no és cronològic: és «on es treballa ARA». Al revés, obrir-ne una de nova
        no es notaria fins a recarregar la pàgina."""
        self._presa(estat='Tancada', data=datetime.date(2026, 8, 16),
                    anotada={(MARE, 'L'): 53.4})
        viva, _, _ = self._presa(estat='Oberta', data=datetime.date(2026, 8, 10))
        d = self._get().data
        self.assertEqual(d['presa_oberta'], True)
        self.assertEqual(d['presa_tancada'], False)
        self.assertEqual(d['session']['id'], viva.id)

    def test_entre_dues_segellades_mana_LA_MES_RECENT(self):
        self._presa(estat='Tancada', data=datetime.date(2026, 8, 10),
                    anotada={(MARE, 'L'): 40.0})
        nova, _, _ = self._presa(estat='Tancada', data=datetime.date(2026, 8, 16),
                                 anotada={(MARE, 'L'): 53.4})
        d = self._get().data
        self.assertEqual(d['session']['id'], nova.id)
        self.assertEqual(d['preses'][self._clau(MARE, 'L')]['real'], 53.4)

    def test_una_presa_NOVA_desbanca_l_acta_sense_esborrar_la(self):
        """E3b: «Mesurar set» sobre una presa tancada en crea una de NOVA. L'acta es queda a
        l'històric i deixa de ser el que la pantalla ensenya — les dues coses alhora."""
        vella, _, _ = self._presa(estat='Tancada', data=datetime.date(2026, 8, 16),
                                  anotada={(MARE, 'L'): 53.4})
        nova, _, _ = self._presa(estat='Oberta', data=datetime.date(2026, 8, 17))
        d = self._get().data
        self.assertEqual(d['session']['id'], nova.id)
        self.assertEqual(d['presa_oberta'], True)
        self.assertTrue(FittingSession.objects.filter(pk=vella.pk, estat='Tancada').exists())


class ResumDeLActaTest(PresaTancadaBase):
    """El recompte de decisions d'una acta és el que era, no zero."""

    def test_les_decisions_de_la_base_es_compten_igual_que_a_la_viva(self):
        _, _, linies = self._presa(estat='Tancada', data=datetime.date(2026, 8, 16),
                                   anotada={(MARE, BASE): 51.0, (SEGONA, BASE): 31.0})
        PieceFittingLine.objects.filter(pk=linies[(MARE, BASE)].pk).update(decisio='ACCEPTED')
        d = self._get().data
        # DUES prendes = DUES bases (llei d'`estatDeLaPresa`): una decidida, una pendent.
        self.assertEqual(d['resum']['decidides_base'], 1)
        self.assertEqual(d['resum']['pendents_base'], 1)
