"""G1/G2 — LA GRADUACIÓ TÉ PORTA PRÒPIA, i propagar sense regla ja no és un error mut.

Decisions P1-P4 (Agus, 30-31/07). El que aquests tests defensen és una frase: **sense regla
informada no es propaga MAI, i el sistema no ho diu amb un error: t'hi porta.**

L'ordre de les proves segueix el GEST real del tècnic, que és com es va trencar i com s'ha
d'arreglar: mira l'estat → no hi ha regla → accepta la proposta → propaga. La represa en si
viu al front (`ModelSheet.onGraduacioAcceptada`), però el CONTRACTE que la fa possible és tot
aquí: si `grading-status` no digués `te_regles`, o si acceptar no deixés el model graduable,
el gest es trencaria i cap test de component ho veuria.

Convenció del repo: `python manage.py test fhort.models_app` (el projecte NO fa servir pytest).
"""
import datetime

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.models_app.models import BaseMeasurement, Model, ModelGradingRule
from fhort.models_app.services import (PROPOSTA_ITEM, PROPOSTA_MODEL, PROPOSTA_PERFIL,
                                       resol_proposta_graduacio)
from fhort.models_app.views import (accept_grading_proposal_view, generate_grading_view,
                                    grading_status_view, measurements_table_view)
from fhort.pom.models import (ConstructionType, FitType, GarmentType, GradingRule,
                              GradingRuleSet, POMMaster, SizeDefinition, SizeSystem,
                              SizingProfile, Target)


class _G1Base(TenantTestCase):

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
        self.user = get_user_model().objects.create(username='g1')
        self.factory = APIRequestFactory()

        self.ss = SizeSystem.objects.create(codi='SS_G1', nom='SS G1', base_unit='ALPHA')
        for i, et in enumerate(['S', 'M', 'L']):
            SizeDefinition.objects.create(size_system=self.ss, etiqueta=et, ordre=i)
        self.talla_base = SizeDefinition.objects.get(size_system=self.ss, etiqueta='M')
        self.pom = POMMaster.objects.create(codi_client='CH', nom_client='Chest width')

    # ── fixtures ────────────────────────────────────────────────────────────────────
    def _ruleset(self, nom, *, increment=2.0, amb_regla=True):
        rs = GradingRuleSet.objects.create(nom=nom, size_system=self.ss, actiu=True)
        if amb_regla:
            GradingRule.objects.create(
                rule_set=rs, pom=self.pom, talla_base=self.talla_base,
                logica='LINEAR', increment=increment, increment_base=increment, actiu=True)
        return rs

    def _model(self, codi='TST-G1', *, rule_set=None, amb_base=True, **kw):
        m = Model.objects.create(
            codi_intern=codi, codi_tenant='TST', any=2026, sequencial=1,
            nom_prenda='Test', size_system=self.ss, size_run_model='S·M·L',
            base_size_label='M', grading_rule_set=rule_set, **kw)
        if amb_base:
            BaseMeasurement.objects.create(model=m, pom=self.pom, base_value_cm=100.0)
        return m

    def _familia(self, codi='DRESS'):
        return GarmentType.objects.create(codi_client=codi, nom_client=codi.title(), grup='TOP')

    def _gti(self, code, rs, *, familia=None):
        """Un GarmentTypeItem amb ruleset assignat: la via per on la S4 va assignar a PROD."""
        from fhort.tasks.models import GarmentTypeItem
        return GarmentTypeItem.objects.create(
            code=code, name='Item test', garment_type=familia or self._familia(f'F{code}'),
            grading_rule_set=rs)

    # ── crides a les vistes (el mateix que fa el front, sense el front) ─────────────
    def _get(self, view, model, **kw):
        req = self.factory.get('/x')
        force_authenticate(req, user=self.user)
        return view(req, model.id, **kw)

    def _post(self, view, model, body=None):
        req = self.factory.post('/x', body or {}, format='json')
        force_authenticate(req, user=self.user)
        return view(req, model.id)


class GestPropagarSenseReglaTest(_G1Base):
    """EL GEST SENCER, pas a pas, tal com el fa el tècnic (G2)."""

    def test_el_gest_complet_de_la_represa(self):
        model = self._model()          # sense ruleset i sense residents
        rs = self._ruleset('RS proposat')
        # La proposta arriba per l'item: és el fallback de la cadena D-B.
        model.garment_type_item = self._gti('it-gest', rs)
        model.save(update_fields=['garment_type_item'])

        # 1. Propagar MIRA ABANS: no hi ha regla → el front no propaga, obre Graduació.
        st = self._get(grading_status_view, model)
        self.assertEqual(st.status_code, 200)
        self.assertFalse(st.data['te_regles'], 'sense regla, `te_regles` ha de ser False')

        # 2. I si algú ho intentés igualment, el gate dur del backend el barra (no ha canviat).
        r = self._post(generate_grading_view, model, {'new_version': True})
        self.assertEqual(r.status_code, 400)

        # 3. La pantalla de Graduació ensenya una PROPOSTA (no les regles del model).
        taula = self._get(measurements_table_view, model)
        self.assertTrue(taula.data['graduacio']['es_proposta'])
        self.assertEqual(taula.data['graduacio']['rule_set_id'], rs.id)

        # 4. ACCEPTAR: les regles passen a ser residents del model (mecanisme del wizard).
        acc = self._post(accept_grading_proposal_view, model, {})
        self.assertEqual(acc.status_code, 200, acc.data)
        self.assertEqual(acc.data['n_regles'], 1)
        self.assertEqual(ModelGradingRule.objects.filter(model=model, actiu=True).count(), 1)

        # 5. LA REPRESA: el model ja és graduable, i la propagació que havia quedat en cua ara sí.
        st2 = self._get(grading_status_view, model)
        self.assertTrue(st2.data['te_regles'], 'després d\'acceptar, el model ha de ser graduable')
        r2 = self._post(generate_grading_view, model, {'new_version': True})
        self.assertNotEqual(r2.status_code, 400,
                            'després d\'acceptar, propagar ja no pot rebotar pel gate de regles')

    def test_cancellar_no_deixa_res_escrit(self):
        """Cancel·lar la graduació = no haver passat per aquí. L'ÚNIC que escriu és Acceptar:
        obrir la pantalla i mirar-la no pot deixar cap regla ni cap FK al model."""
        model = self._model()
        rs = self._ruleset('RS proposat')
        model.garment_type_item = self._gti('it-cancel', rs)
        model.save(update_fields=['garment_type_item'])

        # Obrir la pantalla (això és tot el que fa cancel·lar: mirar i marxar).
        self._get(measurements_table_view, model)
        self._get(grading_status_view, model)

        model.refresh_from_db()
        self.assertIsNone(model.grading_rule_set_id, 'mirar la proposta no pot assignar el ruleset')
        self.assertEqual(ModelGradingRule.objects.filter(model=model).count(), 0)
        self.assertFalse(self._get(grading_status_view, model).data['te_regles'])


class PropagarAmbReglaIntacteTest(_G1Base):
    """El camí que ja funcionava no es toca: amb regla, Propagar segueix sent directe."""

    def test_un_model_amb_regla_propaga_com_sempre(self):
        rs = self._ruleset('RS del model')
        model = self._model(rule_set=rs)

        st = self._get(grading_status_view, model)
        self.assertTrue(st.data['te_regles'])
        self.assertFalse(st.data['te_dades_propagades'], 'llenç net → el front propaga directe')

        r = self._post(generate_grading_view, model, {'new_version': True})
        self.assertNotEqual(r.status_code, 400)

    def test_acceptar_sobre_un_model_que_ja_en_te_es_refusa(self):
        """El guard que protegeix els ajustos del tècnic: `materialize` és wipe-and-recreate, i
        deixar-lo caure sobre regles residents ja ajustades les esborraria totes."""
        rs = self._ruleset('RS del model')
        model = self._model(rule_set=rs)
        ModelGradingRule.objects.create(model=model, pom=self.pom, logica='LINEAR',
                                        increment=9, increment_base=9, actiu=True)

        acc = self._post(accept_grading_proposal_view, model, {})

        self.assertEqual(acc.status_code, 409)
        self.assertEqual(acc.data['error'], 'ja_te_graduacio')
        self.assertEqual(ModelGradingRule.objects.get(model=model).increment_base, 9,
                         'el refús no pot haver tocat la regla ajustada a mà')


class CadenaDeLaPropostaTest(_G1Base):
    """D-B — SizingProfile PRIMER, GarmentTypeItem de fallback. I el model per damunt de tot."""

    def _perfil(self, rs, *, fit_codi='REGULAR'):
        target = Target.objects.create(codi='WOMAN', nom_en='Woman')
        constr = ConstructionType.objects.create(codi='WOVEN', nom_en='Woven')
        fit = FitType.objects.create(codi=fit_codi, nom_en=fit_codi.title(),
                                     ease_bust_cm=0, ease_waist_cm=0,
                                     ease_hip_cm=0, ease_thigh_cm=0)
        familia = self._familia('DRESS')
        SizingProfile.objects.create(
            target=target, garment_type=familia, construction=constr, fit_type=fit,
            size_system=self.ss, grading_rule_set=rs)
        return familia

    def test_el_perfil_guanya_a_litem(self):
        rs_perfil = self._ruleset('RS del perfil')
        rs_item = self._ruleset('RS de litem')
        familia = self._perfil(rs_perfil)
        model = self._model(target='WOMAN', construction='WOVEN', fit_type='Regular',
                            garment_type=familia)
        model.garment_type_item = self._gti('it1', rs_item, familia=familia)
        model.save(update_fields=['garment_type_item'])

        font, rs = resol_proposta_graduacio(model)

        self.assertEqual(font, PROPOSTA_PERFIL)
        self.assertEqual(rs.id, rs_perfil.id, "el perfil és la font viva des del 2026-07-23")

    def test_sense_perfil_cau_a_litem(self):
        rs_item = self._ruleset('RS de litem')
        model = self._model()
        model.garment_type_item = self._gti('it2', rs_item)
        model.save(update_fields=['garment_type_item'])

        font, rs = resol_proposta_graduacio(model)

        self.assertEqual(font, PROPOSTA_ITEM)
        self.assertEqual(rs.id, rs_item.id)

    def test_el_model_que_ja_en_te_no_rep_cap_proposta(self):
        """El catàleg proposa, el model disposa: si el model ja té graduació no hi ha res a
        acceptar, i el front no ha d'ensenyar cap botó d'Acceptar."""
        rs_item = self._ruleset('RS de litem')
        model = self._model(rule_set=self._ruleset('RS del model'))
        model.garment_type_item = self._gti('it3', rs_item)
        model.save(update_fields=['garment_type_item'])

        font, rs = resol_proposta_graduacio(model)

        self.assertEqual(font, PROPOSTA_MODEL)
        self.assertIsNone(rs)


class SenseGraduacioNoPetaResTest(_G1Base):
    """G4 — `grading_rule_set=NULL` i zero residents és un ESTAT VÀLID, no una avaria.

    P4: un model amb només talla base és COMPLET per a la seva fase. Cap superfície pot petar
    per això; l'estat de model mana, no el FK (patró `pom_task_done`).
    """

    def test_les_tres_superficies_responen_200_amb_null_pertot(self):
        model = self._model()   # cap ruleset, cap resident, cap item, cap perfil

        for view in (measurements_table_view, grading_status_view):
            with self.subTest(view=view.__name__):
                r = self._get(view, model)
                self.assertEqual(r.status_code, 200)

    def test_la_taula_diu_honestament_que_no_hi_ha_proposta(self):
        model = self._model()

        d = self._get(measurements_table_view, model).data

        self.assertIsNone(d['graduacio']['font'])
        self.assertFalse(d['graduacio']['es_proposta'])
        self.assertIsNone(d['graduacio']['rule_set_id'])
        # I la base HI ÉS: Escalat ensenya la talla base encara que no sàpiga graduar-la.
        self.assertEqual(len(d['rows']), 1)
        self.assertEqual(d['rows'][0]['base_value_cm'], 100.0)
        self.assertIsNone(d['rows'][0]['logica'])

    def test_acceptar_sense_proposta_no_peta_i_ho_diu(self):
        model = self._model()

        acc = self._post(accept_grading_proposal_view, model, {})

        self.assertEqual(acc.status_code, 404)
        self.assertEqual(acc.data['error'], 'sense_proposta')

    def test_un_model_sense_mesures_base_tampoc_peta(self):
        """El cas més buit de tots: ni graduació ni mesures."""
        model = self._model(codi='TST-G1-BUIT', amb_base=False)

        d = self._get(measurements_table_view, model).data

        self.assertEqual(d['rows'], [])
        self.assertIsNone(d['graduacio']['font'])


class LaGraduacioNoEsVeuFinsQueSInformaTest(_G1Base):
    """EL CONTRACTE FINAL (Agus, 31/07) — bug del model 1302.

    «La graduació no es veu enlloc fins que s'informa pel botó de Graduació.»

    El 1302 es va crear expressament SENSE graduació i a Mesures hi sortia «CH · LINEAR
    +2,0 / +3,0 @XS». La BD era NETA: el que passava és que la pantalla pintava com a regla del
    model el ruleset penjat del seu ITEM. I no era només cosmètic — `EditableTable` reenviava el
    que ensenyava i `set_measurements_view` en fa upsert, o sigui que desar les mesures hauria
    materialitzat la regla d'un altre sense que ningú l'acceptés mai.

    La frontera és el paràmetre `?proposta=1`: només la pantalla que porta un botó d'Acceptar al
    davant té dret a ensenyar una regla que el model no ha adoptat.
    """

    def _model_amb_proposta_al_cataleg(self):
        """El muntatge del 1302: model net, item amb ruleset."""
        rs = self._ruleset('RS de litem', increment=2.0)
        model = self._model(codi='TST-1302')
        model.garment_type_item = self._gti('it-1302', rs)
        model.save(update_fields=['garment_type_item'])
        return model, rs

    def test_mesures_no_ensenya_cap_rastre_de_graduacio(self):
        model, _rs = self._model_amb_proposta_al_cataleg()

        d = self._get(measurements_table_view, model).data

        fila = d['rows'][0]
        self.assertIsNone(fila['logica'], 'Mesures ha pintat un règim que el model no té')
        self.assertIsNone(fila['increment_base'], 'Mesures ha pintat un Δ que el model no té')
        self.assertIsNone(fila['increment_break'])
        self.assertIsNone(fila['talla_break_label'])

    def test_la_proposta_nomes_surt_si_es_demana(self):
        """La MATEIXA vista, amb `?proposta=1`: aquí sí, perquè és la pantalla de Graduació."""
        model, rs = self._model_amb_proposta_al_cataleg()

        req = self.factory.get('/x', {'proposta': '1'})
        force_authenticate(req, user=self.user)
        d = measurements_table_view(req, model.id).data

        fila = d['rows'][0]
        self.assertEqual(fila['logica'], 'LINEAR')
        self.assertEqual(fila['increment_base'], 2.0)
        # …i segueix marcada com a PROPOSTA, no com a regla del model.
        self.assertTrue(d['graduacio']['es_proposta'])
        self.assertEqual(d['graduacio']['rule_set_id'], rs.id)

    def test_veure_la_proposta_no_escriu_res(self):
        """Q1/(b): la BD del 1302 era neta i ha de continuar essent-ho per molt que es miri."""
        model, _rs = self._model_amb_proposta_al_cataleg()

        req = self.factory.get('/x', {'proposta': '1'})
        force_authenticate(req, user=self.user)
        measurements_table_view(req, model.id)
        self._get(measurements_table_view, model)

        model.refresh_from_db()
        self.assertIsNone(model.grading_rule_set_id)
        self.assertEqual(ModelGradingRule.objects.filter(model=model).count(), 0)

    def test_nomes_acceptar_escriu_i_llavors_escalat_ho_ensenya(self):
        """El cicle sencer del contracte: net → proposta → ACCEPTAR → ara sí que és seva."""
        model, rs = self._model_amb_proposta_al_cataleg()

        # abans: Escalat (sense `proposta`) no ensenya res
        self.assertIsNone(self._get(measurements_table_view, model).data['rows'][0]['logica'])

        acc = self._post(accept_grading_proposal_view, model, {})
        self.assertEqual(acc.status_code, 200, acc.data)

        # després: la regla ÉS del model, i per tant surt sense demanar cap proposta
        d = self._get(measurements_table_view, model).data
        self.assertEqual(d['rows'][0]['logica'], 'LINEAR')
        self.assertEqual(d['rows'][0]['increment_base'], 2.0)
        self.assertEqual(d['graduacio']['font'], PROPOSTA_MODEL)
        self.assertFalse(d['graduacio']['es_proposta'], 'ja no és una proposta: és la seva regla')
        self.assertEqual(model.grading_rules.filter(actiu=True).count(), 1)

    def test_desar_mesures_sense_regles_no_en_fabrica_cap(self):
        """L'altra meitat del bug: el payload de Mesures ja no porta `rules`, o sigui que desar
        mesures d'un model sense graduació no li'n pot inventar cap. Sense això, el model
        passava a «tenir graduació» (LINEAR amb deltes buits) sense que ningú n'informés."""
        from fhort.models_app.views import set_measurements_view
        model, _rs = self._model_amb_proposta_al_cataleg()

        req = self.factory.post('/x', {
            'measurements': [{'pom_id': self.pom.id, 'base_value_cm': 101.0}],
            'keep_pom_ids': [self.pom.id],
        }, format='json')
        force_authenticate(req, user=self.user)
        r = set_measurements_view(req, model.id)

        self.assertEqual(r.status_code, 201, getattr(r, 'data', None))
        self.assertEqual(r.data['updated'], 1, 'la mesura sí que s\'ha de desar')
        self.assertEqual(ModelGradingRule.objects.filter(model=model).count(), 0,
                         'desar mesures ha fabricat una regla que ningú no ha informat')
