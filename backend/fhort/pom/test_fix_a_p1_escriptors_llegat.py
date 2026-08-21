"""FIX-A/PAS-1 · ELS QUATRE ESCRIPTORS QUE POBLAVEN NOMÉS EL CAMP LLEGAT.

Substrat: `docs/ordres/DIAGNOSI_PRE_SPRINTS_STAGING_2026-08-21.md` §1.5, bloc C.

── EL FORAT, EN UNA FRASE ───────────────────────────────────────────────────────────────
El motor gradua per `increment_base` (forma canònica, `_apply_rule`) i només cau a `increment`
—el camp LLEGAT— quan `increment_base` és NULL, cosa que al corpus d'avui no passa mai. Quatre
portes vives escrivien **només `increment`**: tornaven 200 OK, ensenyaven el número nou, i la
graduació no es movia. Una cinquena cosa passava al CLON: perdia el break sencer.

Les quatre, i què mesura cada classe d'aquest fitxer:

  · `pom/s4_views.py`  update_grading_rule_with_history_view  → `EditaAmbHistorialTest`
  · `pom/s2_views.py`  update_grading_rule_view               → `EditaSimpleTest`
  · `pom/s4_views.py`  restore_version_view                   → `RestauraTest`
  · `pom/s2_views.py`  clone_sizing_profile_view              → `ClonPreservaLaReglaTest`

── EL FIXTURE ÉS LA FORMA DEL 1383 ──────────────────────────────────────────────────────
Les regles del banc no s'inventen: són la transcripció de les del model **1383**
(`TRV-SS27-0001`, joc `BRW-CATALEG-v3`), amb la seva incoherència VIVA —`increment` orfe que no
casa amb `increment_base`— perquè és exactament el que aquestes portes havien de saber tractar
i no sabien. Un fixture net hauria passat els quatre tests sense veure res.

  POM   logica  increment(llegat)  increment_base  increment_break  break
  A     LINEAR       2.00               2.00             3.00        M
  C     LINEAR       1.50               2.00             3.00        M      ← llegat ≠ canònic
  D     LINEAR       2.00               0.50             0.50        M      ← «la mina» de §A
  BF    FIXED        0.00               NULL             NULL        —
  ZST   STEP         0.00               NULL             NULL        —      (valors_step propis)

⚠️ NO es toca cap dada de staging: `TenantTestCase` corre sobre una BD de test pròpia.
"""
import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.pom.models import (ConstructionType, FitType, GarmentType, GradingRule,
                              GradingRuleSet, POMMaster, SizeDefinition, SizeSystem,
                              SizingProfile, Target)
from fhort.pom.s2_views import clone_sizing_profile_view, update_grading_rule_view
from fhort.pom.s4_views import restore_version_view, update_grading_rule_with_history_view

#: Els camps que SÓN la llei de graduació. Qualsevol còpia o comparació que en digui menys
#: menteix — és literalment el defecte que aquest fitxer tanca.
CAMPS_LLEI = ('logica', 'increment', 'increment_base', 'increment_break',
              'talla_break_label', 'talla_break_pos', 'valors_step')

#: La transcripció del 1383 (v. la capçalera).
REGLES_1383 = [
    # codi   logica     increment  inc_base  inc_break  break  valors_step
    ('A',   'LINEAR',   '2.00',    '2.00',   '3.00',    'M',   None),
    ('C',   'LINEAR',   '1.50',    '2.00',   '3.00',    'M',   None),
    ('D',   'LINEAR',   '2.00',    '0.50',   '0.50',    'M',   None),
    ('BF',  'FIXED',    '0.00',    None,     None,      None,  None),
    ('ZST', 'STEP',     '0.00',    None,     None,      None,  {'M': 1.0, 'L': 1.5}),
]


class BancFixAP1(TenantTestCase):
    """Un joc amb la forma del 1383, i un SizingProfile estàndard que l'apunta."""

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
        super().setUp()
        self.user = get_user_model().objects.create(
            username='tester_fixa_p1', first_name='Test', last_name='Fix A')
        self.factory = APIRequestFactory()

        self.ss = SizeSystem.objects.create(codi='ALPHA_EU_W', nom='Alpha EU W',
                                            base_unit='ALPHA', actiu=True)
        self.talles = {}
        for i, et in enumerate(['XXS', 'XS', 'S', 'M', 'L', 'XL', 'XXL', '3XL']):
            self.talles[et] = SizeDefinition.objects.create(
                size_system=self.ss, etiqueta=et, ordre=i)

        self.rs = GradingRuleSet.objects.create(nom='BRW-CATALEG-v3 (banc)',
                                                codi_sistema='BRW_CAT_V3_BANC',
                                                size_system=self.ss, actiu=True)
        self.poms, self.regles = {}, {}
        for codi, logica, inc, ib, ibrk, brk, vs in REGLES_1383:
            pom = POMMaster.objects.create(codi_client=codi, nom_client=f'POM {codi}')
            self.poms[codi] = pom
            self.regles[codi] = GradingRule.objects.create(
                rule_set=self.rs, pom=pom, talla_base=self.talles['S'],
                talla_base_label='S', logica=logica,
                increment=Decimal(inc),
                increment_base=(Decimal(ib) if ib is not None else None),
                increment_break=(Decimal(ibrk) if ibrk is not None else None),
                talla_break_label=brk,
                talla_break_pos=(2 if brk else None),
                valors_step=vs, actiu=True,
            )

        self.target = Target.objects.create(codi='WOMAN', nom_en='Woman', display_order=1)
        self.gt = GarmentType.objects.create(nom_client='Dresses', actiu=True)
        self.constr = ConstructionType.objects.create(codi='WOVEN', nom_en='Woven',
                                                      display_order=1)
        self.fit = FitType.objects.create(codi='REGULAR', nom_en='Regular', display_order=1)
        self.perfil = SizingProfile.objects.create(
            target=self.target, garment_type=self.gt, construction=self.constr,
            fit_type=self.fit, size_system=self.ss, grading_rule_set=self.rs,
            is_default=True, version=1)

    # ── helpers ────────────────────────────────────────────────────────────────
    def _crida(self, vista, metode, dades, *args):
        req = getattr(self.factory, metode)('/', dades, format='json')
        force_authenticate(req, user=self.user)
        return vista(req, *args)

    def _llei(self, regla):
        return {c: getattr(regla, c) for c in CAMPS_LLEI}


class EditaAmbHistorialTest(BancFixAP1):
    """`PATCH .../regles/<pom>/editar/` (s4) — la porta que crida `SizeSetDetail.jsx:63`."""

    def _patch(self, pom_codi, dades):
        return self._crida(update_grading_rule_with_history_view, 'patch', dades,
                           self.rs.pk, pom_codi)

    def test_l_edicio_aterra_al_camp_que_MANA(self):
        resp = self._patch('C', {'increment': 4.5})
        self.assertEqual(resp.status_code, 200, resp.data)
        r = self.regles['C']; r.refresh_from_db()
        # ⬅️ EL DEFECTE: abans això valia 2.00 (intacte) i `increment` valia 4.50.
        self.assertEqual(r.increment_base, Decimal('4.50'))
        self.assertEqual(r.increment, Decimal('4.50'))       # mirall transitori del PAS 1

    def test_el_break_NO_es_toca(self):
        """Editar el delta base no és editar el relleu: el break sobreviu sencer."""
        self._patch('C', {'increment': 4.5})
        r = self.regles['C']; r.refresh_from_db()
        self.assertEqual(r.increment_break, Decimal('3.00'))
        self.assertEqual(r.talla_break_label, 'M')

    def test_l_historial_compara_el_delta_que_manava_amb_el_nou(self):
        """La fila d'historial deia `valor_anterior = increment` (el llegat, 1.50) i
        `valor_nou = increment` (4.50): documentava un canvi de 1.50→4.50 que no havia mogut
        cap cel·la. Ara diu 2.00→4.50, que és el que ha passat de debò."""
        from fhort.pom.models import GradingRuleHistory
        self._patch('C', {'increment': 4.5})
        h = GradingRuleHistory.objects.filter(rule_set=self.rs, pom_codi='C').latest('pk')
        self.assertEqual(Decimal(str(h.valor_anterior)), Decimal('2.00'))
        self.assertEqual(Decimal(str(h.valor_nou)), Decimal('4.50'))

    def test_la_resposta_diu_el_delta_que_mana(self):
        resp = self._patch('C', {'increment': 4.5})
        self.assertEqual(Decimal(str(resp.data['increment_cm'])), Decimal('4.50'))

    def test_A3_una_LINEAR_a_zero_sense_break_es_rebutja(self):
        """El guard que les altres portes d'autoria ja tenien. Sense break, delta 0 no gradua."""
        self.regles['C'].talla_break_label = None
        self.regles['C'].increment_break = None
        self.regles['C'].save(update_fields=['talla_break_label', 'increment_break'])
        resp = self._patch('C', {'increment': 0})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data.get('code'), 'LINEAR_INCREMENT_ZERO')
        r = self.regles['C']; r.refresh_from_db()
        self.assertEqual(r.increment_base, Decimal('2.00'))   # res desat

    def test_un_increment_no_numeric_es_400_i_no_un_500(self):
        resp = self._patch('C', {'increment': 'quatre'})
        self.assertEqual(resp.status_code, 400)


class EditaSimpleTest(BancFixAP1):
    """`PATCH .../regles/<pom>/` (s2) — la germana sense historial."""

    def _patch(self, pom_codi, dades):
        return self._crida(update_grading_rule_view, 'patch', dades, self.rs.pk, pom_codi)

    def test_l_edicio_aterra_al_camp_que_MANA(self):
        resp = self._patch('D', {'increment': 1.25})
        self.assertEqual(resp.status_code, 200, resp.data)
        r = self.regles['D']; r.refresh_from_db()
        self.assertEqual(r.increment_base, Decimal('1.25'))
        self.assertEqual(r.increment, Decimal('1.25'))

    def test_la_resposta_deixa_de_dir_el_llegat(self):
        resp = self._patch('D', {'increment': 1.25})
        self.assertEqual(Decimal(str(resp.data['increment'])), Decimal('1.25'))
        self.assertEqual(Decimal(str(resp.data['increment_base'])), Decimal('1.25'))

    def test_A3_hi_val_igual(self):
        self.regles['D'].talla_break_label = None
        self.regles['D'].increment_break = None
        self.regles['D'].save(update_fields=['talla_break_label', 'increment_break'])
        resp = self._patch('D', {'increment': 0})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data.get('code'), 'LINEAR_INCREMENT_ZERO')


class RestauraTest(BancFixAP1):
    """`POST /sizing-profiles/<id>/restaurar/` — «restaurat a l'estàndard» ha de ser cert."""

    def setUp(self):
        super().setUp()
        # Un clon a mà (no per l'endpoint: aquest test no mesura el clon) amb la llei SENCERA.
        self.rs_client = GradingRuleSet.objects.create(
            nom='Versió de client', codi_sistema='BRW_CAT_V3_BANC_CUSTOM',
            size_system=self.ss, parent_version=self.rs, version_number=2)
        self.client_rules = {}
        for codi, r in self.regles.items():
            self.client_rules[codi] = GradingRule.objects.create(
                rule_set=self.rs_client, pom=r.pom, talla_base=r.talla_base,
                talla_base_label=r.talla_base_label,
                **{c: getattr(r, c) for c in CAMPS_LLEI}, actiu=True)
        self.perfil_client = SizingProfile.objects.create(
            target=self.target, garment_type=self.gt, construction=self.constr,
            fit_type=self.fit, size_system=self.ss, grading_rule_set=self.rs_client,
            is_default=False, parent_profile=self.perfil, version=2)

    def _restaura(self):
        return self._crida(restore_version_view, 'post', {'confirmar': True},
                           self.perfil_client.pk)

    def test_una_divergencia_NOMES_al_break_es_veu_i_es_restaura(self):
        """⬅️ EL DEFECTE: el `!=` només mirava `increment` i `logica`. Una regla amb el break
        canviat es declarava IGUAL i no es restaurava mai."""
        c = self.client_rules['A']
        c.increment_break = Decimal('9.00')
        c.talla_break_label = 'XL'
        c.save(update_fields=['increment_break', 'talla_break_label'])

        resp = self._restaura()
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.data['regles_restaurades'], 1)
        c.refresh_from_db()
        self.assertEqual(c.increment_break, Decimal('3.00'))
        self.assertEqual(c.talla_break_label, 'M')

    def test_restaurar_deixa_la_llei_SENCERA_igual_a_l_estandard(self):
        c = self.client_rules['C']
        c.increment = Decimal('7.00')
        c.increment_base = Decimal('7.00')
        c.increment_break = Decimal('8.00')
        c.talla_break_label = 'L'
        c.save()
        self._restaura()
        c.refresh_from_db()
        self.assertEqual(self._llei(c), self._llei(self.regles['C']))

    def test_els_valors_step_tambe_es_restauren(self):
        z = self.client_rules['ZST']
        z.valors_step = {'M': 99.0}
        z.save(update_fields=['valors_step'])
        self._restaura()
        z.refresh_from_db()
        self.assertEqual(z.valors_step, {'M': 1.0, 'L': 1.5})

    def test_sense_cap_divergencia_no_restaura_res(self):
        resp = self._restaura()
        self.assertEqual(resp.data['regles_restaurades'], 0)


class ClonPreservaLaReglaTest(BancFixAP1):
    """🚨 `POST /sizing-profiles/<id>/clonar/` — el clon PERDIA EL BREAK.

    És bug propi i anterior al fix A: el clon copiava sis camps de deu i el joc nou sortia amb
    `increment_base`/`increment_break`/`talla_break_label` a NULL. Com que el motor gradua per
    `increment_base`, el clon graduava PLA on l'original tenia relleu — sense petar, sense avís,
    i amb el `increment` llegat intacte per fer-ho semblar bo.
    """

    def _clona(self):
        return self._crida(clone_sizing_profile_view, 'post',
                           {'nom_client': 'Clon del banc'}, self.perfil.pk)

    def test_el_clon_copia_la_regla_SENCERA_regla_a_regla(self):
        resp = self._clona()
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data['rules_copiades'], len(REGLES_1383))

        noves = {r.pom.codi_client: r for r in
                 GradingRule.objects.filter(rule_set_id=resp.data['grading_rule_set_id'])
                 .select_related('pom')}
        self.assertEqual(set(noves), set(self.regles))
        for codi, original in self.regles.items():
            with self.subTest(pom=codi):
                # ⬅️ EL DEFECTE: `increment_base`, `increment_break` i `talla_break_label`
                # sortien a NULL a A, C i D.
                self.assertEqual(self._llei(noves[codi]), self._llei(original))

    def test_el_clon_conserva_l_ancoratge_de_talla_base(self):
        resp = self._clona()
        for r in GradingRule.objects.filter(rule_set_id=resp.data['grading_rule_set_id']):
            self.assertEqual(r.talla_base_id, self.talles['S'].pk)
            self.assertEqual(r.talla_base_label, 'S')

    def test_el_clon_gradua_IGUAL_que_l_original(self):
        """La prova que importa de debò: mateixa corba, cel·la a cel·la.

        Es mesura amb el motor de veritat (`_apply_rule` sobre les arestes) i no comparant
        camps: si algun dia el clon es fes per una altra via, això seguiria dient la veritat.
        """
        from fhort.pom.services import _apply_rule
        resp = self._clona()
        noves = {r.pom.codi_client: r for r in
                 GradingRule.objects.filter(rule_set_id=resp.data['grading_rule_set_id'])
                 .select_related('pom')}
        run = ['XXS', 'XS', 'S', 'M', 'L', 'XL', 'XXL', '3XL']
        base_idx, base_val = 2, 100.0
        for codi in ('A', 'C', 'D'):
            for i, _lab in enumerate(run):
                orig, _ = _apply_rule(self.regles[codi], base_val, i - base_idx, i, base_idx,
                                      size_run=run, warnings=[])
                clon, _ = _apply_rule(noves[codi], base_val, i - base_idx, i, base_idx,
                                      size_run=run, warnings=[])
                with self.subTest(pom=codi, talla=run[i]):
                    self.assertEqual(round(clon, 2), round(orig, 2))
