#!/usr/bin/env python
"""QA F4-BIS SOBRE STAGING — el payload que la columna «Breaks» escriu, per les portes reals.

    cd /var/www/ftt-staging/backend
    venv/bin/python ../ops/qa/qa_f4bis_staging.py

F4-BIS és UI-only: el motor i la porta no es toquen. El que sí que és nou és **la forma del
payload** que la pantalla envia, i té una part que cap tram anterior havia exercit:

    🔑 quan un xip surt d'un break d'1 tram DESAT, editar-lo envia `breaks` **i buida**
       `increment_break` + `talla_break_label` — perquè una regla no es quedi amb dues formes.

Aquest script mesura les tres coses que això obre, i la primera és la que importa:

  ① **RE-DESAR UN BREAK LLEGAT COM A INTERVAL NO MOU CAP CEL·LA.** Es gradua, s'anota la corba
     sencera, s'envia el payload de F4-BIS i es torna a graduar: les cinc talles han de sortir
     IDÈNTIQUES. Si això es mogués, la columna nova estaria reescrivint graduació en silenci
     cada cop que algú toqués un xip — i seria indistingible d'una edició volguda.
  ② la regla queda amb UNA forma (els dos camps llegats a NULL i `breaks` poblat);
  ③ el solapament, que la UI no deixa TECLEJAR, el servidor també el rebutja (la xarxa hi és).

**El model és `QA-TRAMF-0001` (pk 1384), el de la QA del tram F. El banc 1383 NO es toca** —
i el gate `banc_paritat_1383.py` es corre abans i després igualment.

🚩 ESCRIU sobre el model de prova. El deixa amb la forma nova, que és el que la QA de pantalla
vol trobar-hi.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fhort.settings')

import django  # noqa: E402
django.setup()

from django.contrib.auth import get_user_model            # noqa: E402
from django_tenants.utils import schema_context           # noqa: E402
from rest_framework.test import APIRequestFactory, force_authenticate  # noqa: E402

class _Revert(Exception):
    """Senyal per desfer la transacció de la prova ⑦: escriure al banc no és gratis."""


CODI = 'QA-TRAMF-0001'
BANC = 1383
RUN = ['XS', 'S', 'M', 'L', 'XL']

#: El costat JS del mirall. Corre amb `node --input-type=module` des de `frontend/`, o sigui
#: que importa el MATEIX fitxer que el bundle: cap còpia, cap reimplementació.
_MIRALL_JS = r'''
import { readFileSync } from 'node:fs'
import { intervalsVisibles } from './src/utils/gradingRegime.js'
const { run, casos } = JSON.parse(readFileSync(process.argv[1], 'utf8'))

// El delta que mana a cada posició del run, donada una llista d'intervals i el general.
// És el mateix que fa `delta_de_posicio` al motor, i és el que decideix cada cel·la.
const corba = (ivs, general) => run.map((_, p) => {
  for (const iv of ivs) {
    const i = run.indexOf(iv.inici), f = run.indexOf(iv.final)
    if (i >= 0 && f >= 0 && p >= i && p <= f) return iv.delta
  }
  return general
})

const mal = []
let callats = 0
for (const c of casos) {
  const front = intervalsVisibles(c.regla, run)
    .map(iv => ({ inici: iv.inici, final: iv.final, delta: iv.delta }))
  const general = c.regla.increment_base ?? 0
  // 🚨 LA PROVA QUE IMPORTA DES DE LA REGLA DEL SILENCI: el front pot CALLAR un tram, però
  // callar-lo no pot moure ni una xifra. Es comparen les CORBES, no les llistes — que és el
  // que de debò declara el mirall: «la pantalla diu el mateix que el motor calcularà».
  const cf = corba(front, general), cm = corba(c.motor, general)
  if (JSON.stringify(cf) !== JSON.stringify(cm)) {
    mal.push(`${c.pom}: corba front=${cf} motor=${cm}`)
  }
  // I el que calla ha de ser NOMÉS soroll: cap tram amb delta diferent del que ja manava.
  if (front.length < c.motor.length) {
    callats += c.motor.length - front.length
    for (const iv of c.motor) {
      if (!front.some(f => f.inici === iv.inici && f.final === iv.final && f.delta === iv.delta)
          && iv.delta !== general) {
        mal.push(`${c.pom}: calla un tram que SÍ que diu alguna cosa (${JSON.stringify(iv)})`)
      }
    }
  }
}
if (mal.length) { console.error(mal.join(' | ')); process.exit(1) }
const vius = casos.filter(c => c.motor.length).length
console.log(`${casos.length} regles · ${vius} amb relleu al motor · ${callats} trams callats `
  + `per la regla del silenci · CAP corba mòbil`)
'''


def main():
    resultats = []

    def ok(cond, text, detall=''):
        resultats.append(bool(cond))
        print(f"  {'✅' if cond else '❌'} {text}{'' if cond else f'  → {detall}'}")

    with schema_context('fhort'):
        from fhort.fitting.models import GradedSpec, SizeFitting
        from fhort.fitting.services import vigent_grading_version
        from fhort.models_app.models import Model, ModelGradingRule
        from fhort.models_app.views import generate_grading_view, set_pom_regim_view
        from fhort.pom.grading_utils import intervals_de

        user = get_user_model().objects.get(username='a.devant@fhort.cat')
        model = Model.objects.filter(codi_intern=CODI).first()
        assert model, f'no hi ha {CODI} — corre abans `qa_tram_ef_staging.py`'
        sf = SizeFitting.objects.filter(model=model).order_by('numero').first()
        regla = ModelGradingRule.objects.filter(model=model).order_by('pk').first()
        pom = regla.pom
        print(f"MODEL DE PROVA · {CODI} (pk={model.pk}) · SF#{sf.pk} · POM {pom.codi_client}\n")

        def _post(view, body, *args):
            r = APIRequestFactory().post('/x/', body, format='json')
            force_authenticate(r, user=user)
            return view(r, *args)

        def propaga():
            _post(generate_grading_view, {'new_version': True}, model.pk)
            gv = vigent_grading_version(sf)
            return {s.size_label: float(s.graded_value_cm)
                    for s in GradedSpec.objects.filter(grading_version=gv, pom=pom)}

        def rule():
            return ModelGradingRule.objects.get(pk=regla.pk)

        # ── ① EL BREAK LLEGAT, RE-DESAT COM A INTERVAL: CAP CEL·LA ES MOU ────────────────────
        print('① un break d\'1 tram re-desat com a interval')
        # Es deixa la regla en la forma VELLA, que és la de les 21 del banc: Δ 2 · brk 3 · M.
        r = rule()
        r.increment_base, r.increment_break, r.talla_break_label, r.breaks = 2.0, 3.0, 'M', None
        r.save(update_fields=['increment_base', 'increment_break', 'talla_break_label', 'breaks'])
        abans = propaga()
        # El que la columna PINTA per a aquesta regla (mirall de `intervalsVisibles`): el motor
        # ja la llegeix com l'interval [M .. última del run], i el xip diu això mateix.
        llegit = intervals_de(rule(), RUN)
        ok(llegit == [(RUN.index('M'), len(RUN) - 1, 3.0)],
           f'el motor la llegeix com l\'interval M→XL +3', llegit)

        # 🔑 EL PAYLOAD DE F4-BIS: els intervals I la retirada de la forma vella, a la mateixa
        # crida. És literalment el que envia `escriuBreaks` quan `relleuLlegat` és cert.
        resp = _post(set_pom_regim_view, {
            'logica': 'LINEAR', 'increment_base': 2,
            'breaks': [{'inici': 'M', 'final': 'XL', 'delta': 3}],
            'increment_break': None, 'talla_break_label': None,
        }, model.pk, pom.pk)
        ok(resp.status_code == 200, 'la porta accepta el payload', resp.data)
        despres = propaga()

        ok(abans == despres, '🚨 CAP CEL·LA S\'HA MOGUT', f'{abans} → {despres}')
        print(f'      {abans}')

        r = rule()
        ok(r.breaks == [{'inici': 'M', 'final': 'XL', 'delta': 3.0}],
           '② la regla desa els intervals', r.breaks)
        ok(r.increment_break is None and r.talla_break_label is None,
           '② i la forma vella ha quedat BUIDA (una regla, una forma)',
           (r.increment_break, r.talla_break_label))

        # ── ③ AFEGIR, EDITAR I TREURE XIPS ──────────────────────────────────────────────────
        print('\n③ afegir · editar · treure')
        resp = _post(set_pom_regim_view, {
            'breaks': [{'inici': 'S', 'final': 'M', 'delta': 3},
                       {'inici': 'XL', 'final': 'XL', 'delta': 4}],
        }, model.pk, pom.pk)
        ok(resp.status_code == 200, 'dos intervals: acceptats', resp.data)
        corba2 = propaga()
        # S→M 3 i M→L torna al general 2 (L és fora del primer interval); XL creix 4.
        ok(corba2 == {'XS': 98.0, 'S': 100.0, 'M': 103.0, 'L': 105.0, 'XL': 109.0},
           'la corba diu el relleu de dos trams', corba2)

        resp = _post(set_pom_regim_view, {'breaks': []}, model.pk, pom.pk)
        ok(resp.status_code == 200, 'treure tots els xips: acceptat', resp.data)
        ok(rule().breaks is None,
           'una llista buida es desa NULL («no en té» i «cap» són el mateix)', rule().breaks)
        plana = propaga()
        ok(plana == {'XS': 98.0, 'S': 100.0, 'M': 102.0, 'L': 104.0, 'XL': 106.0},
           'sense relleu, la corba torna al Δ general', plana)

        # ── ④ LA XARXA DEL SERVIDOR ─────────────────────────────────────────────────────────
        # La UI no deixa TECLEJAR un solapament (els selectors no ofereixen talla ocupada), però
        # la porta hi és igualment: una pantalla no és mai l'única guarda d'una dada.
        print('\n④ el que la UI no deixa construir, la porta el rebutja igualment')
        for cas, body, codi in (
            ('solapament', [{'inici': 'S', 'final': 'L', 'delta': 3},
                            {'inici': 'M', 'final': 'XL', 'delta': 4}], 'BREAKS_SOLAPAMENT'),
            ('del revés', [{'inici': 'L', 'final': 'S', 'delta': 3}], 'BREAKS_ORDRE'),
            # ⚠️ «FORANA» ÉS RESPECTE DEL SISTEMA, NO DEL RUN DEL MODEL. `ALPHA_EU_W` va de la
            # XXS a la 3XL i el run d'aquest model només n'agafa cinc: un interval acabat a
            # `XXL` és LEGAL encara que el model no fabriqui aquella talla, perquè el motor
            # resol el relleu en espai de SISTEMA (llei S24b) i és per això que el picker
            # ofereix `run_sistema`. La primera versió d'aquesta prova esperava un 400 per a
            # `XXL` i el 200 tenia raó ell. Una talla forana de debò no és a cap dels dos.
            ('talla forana', [{'inici': 'ZZZ', 'final': 'ZZZ', 'delta': 3}], 'BREAKS_TALLA_FORANA'),
            ('Δ redundant', [{'inici': 'M', 'final': 'XL', 'delta': 2}], 'BREAKS_DELTA_REDUNDANT'),
            ('per sobre del sostre', [{'inici': 'XS', 'final': 'XS', 'delta': 1},
                                      {'inici': 'S', 'final': 'S', 'delta': 3},
                                      {'inici': 'M', 'final': 'M', 'delta': 4},
                                      {'inici': 'L', 'final': 'XL', 'delta': 5}], 'BREAKS_MAX'),
        ):
            resp = _post(set_pom_regim_view, {'breaks': body}, model.pk, pom.pk)
            ok(resp.status_code == 400 and resp.data.get('codi') == codi,
               f'{cas} → 400 {codi}', (resp.status_code, resp.data))

        # ── ⑤ EL BANC NO S'HA TOCAT ─────────────────────────────────────────────────────────
        print('\n⑤ el banc 1383')
        banc = ModelGradingRule.objects.filter(model_id=BANC)
        ok(banc.filter(breaks__isnull=False).count() == 0,
           'cap regla del banc ha guanyat intervals', banc.filter(breaks__isnull=False).count())
        amb_break = banc.filter(increment_break__isnull=False,
                                talla_break_label__isnull=False).count()
        ok(amb_break == 103, f'les {amb_break} regles d\'1 break del banc segueixen senceres',
           amb_break)

        # ── ⑥ EL MIRALL, CONTRA LES 21 FILES REALS DEL BANC ─────────────────────────────────
        # 🚨 LA PROVA QUE UN BANC DE JS NO POT FER SOL. `intervalsVisibles` (front) declara ser
        # el mirall de `intervals_de` (motor). Un banc de JS el prova contra fixtures que he
        # escrit jo; això el prova contra les 21 regles VIVES que la pantalla pintarà demà, i
        # amb el motor REAL a l'altre costat. Si els dos deixessin de dir el mateix, la columna
        # dibuixaria un relleu i el motor en graduaria un altre — en silenci, i sense que cap
        # build ho pogués veure.
        print('\n⑥ el mirall front↔motor sobre les 21 files del banc')
        from fhort.models_app.models import BaseMeasurement
        from fhort.pom.services import escala_del_model
        banc_model = Model.objects.get(pk=BANC)
        _sr, run_banc, _p, _bi = escala_del_model(banc_model)
        poms_amb_base = set(BaseMeasurement.objects.filter(model_id=BANC, is_active=True)
                            .values_list('pom_id', flat=True))
        casos = []
        for reg in ModelGradingRule.objects.filter(model_id=BANC, pom_id__in=poms_amb_base):
            casos.append({
                'pom': reg.pom.codi_client,
                'regla': {'logica': reg.logica,
                          'increment_base': float(reg.increment_base)
                          if reg.increment_base is not None else None,
                          'increment_break': float(reg.increment_break)
                          if reg.increment_break is not None else None,
                          'talla_break_label': reg.talla_break_label,
                          'breaks': reg.breaks},
                # El veredicte del MOTOR, en etiquetes (el front no parla d'índexs).
                'motor': [{'inici': run_banc[i], 'final': run_banc[f], 'delta': d}
                          for i, f, d in intervals_de(reg, run_banc)],
            })
        import json as _json
        import subprocess
        import tempfile
        with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as fh:
            _json.dump({'run': run_banc, 'casos': casos}, fh)
            tmp = fh.name
        arrel = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
        node = subprocess.run(
            ['node', '--input-type=module', '-e', _MIRALL_JS, tmp],
            cwd=os.path.join(arrel, 'frontend'), capture_output=True, text=True)
        os.unlink(tmp)
        print('    ' + (node.stdout or node.stderr).strip().replace('\n', '\n    '))
        ok(node.returncode == 0,
           f'les {len(casos)} regles del banc: el front en diu el MATEIX que el motor',
           node.stderr[-300:])

        # ── ⑦ EL CAS F DEL 1383 · general 0 + intervals vius ha de ser LEGAL ────────────────
        #
        # És EL cas canònic del disseny d'intervals («XXS→XS no creix, a partir de S creix 2»).
        # 🔑 ES FA EN TRANSACCIÓ REVERTIDA: la F és regla VIVA del banc, i provar-la escrivint-hi
        # mouria el `HASH RESIDENTS` i les 5 cel·les de F a tots dos blocs del gate. La mateixa
        # evidència sense deriva — l'ordre autoritzava la deriva, però no cal pagar-la.
        print('\n⑦ el cas F del 1383 (general 0 + intervals) · en transacció REVERTIDA')
        from django.db import transaction
        from fhort.models_app.models import BaseMeasurement
        from fhort.pom.grading_regime import es_linear_degenerada
        from fhort.pom.serializers import GradingRuleSerializer
        IV_F = [{'inici': 'M', 'final': 'L', 'delta': 2}, {'inici': 'XL', 'final': 'XL', 'delta': 3}]

        # ⓐ el PUNT ÚNIC, que és el que comparteixen les quatre portes.
        ok(es_linear_degenerada('LINEAR', 0, None, None, None, IV_F) is False,
           'ⓐ punt únic: general 0 + intervals vius NO és degenerada')
        ok(es_linear_degenerada('LINEAR', 0, None, None, None,
                                [{'inici': 'M', 'final': 'L', 'delta': 0}]) is True,
           'ⓐ punt únic: tot a zero amb breaks informats SEGUEIX degenerada')
        ok(es_linear_degenerada('LINEAR', 0, None, 2, 'M', None) is False,
           'ⓐ punt únic: regla vella d\'1 break amb ib=0 i brk=2 SEGUEIX legal')
        ok(es_linear_degenerada('LINEAR', 0, None, None, None, None) is True,
           'ⓐ punt únic: general 0 i cap tram → degenerada (com sempre)')

        regla_f = ModelGradingRule.objects.get(model_id=BANC, pom__codi_client='F', garment='')
        base_f = float(BaseMeasurement.objects.get(
            model_id=BANC, pom=regla_f.pom, capa='exterior', instancia='',
            garment='').base_value_cm)
        try:
            with transaction.atomic():
                # ⓑ porta ① — la resident, que és la que l'Agus té a pantalla.
                resp = _post(set_pom_regim_view, {
                    'logica': 'LINEAR', 'breaks': IV_F,
                    'increment_break': None, 'talla_break_label': None,
                }, BANC, regla_f.pom_id)
                ok(resp.status_code == 200,
                   'ⓑ porta ① `set_pom_regim_view`: la F es DESA', resp.data)

                # ⓒ porta ③ — el serializer del catàleg, amb la mateixa forma.
                from fhort.pom.models import GradingRule
                rj = GradingRule.objects.filter(
                    rule_set_id=Model.objects.get(pk=BANC).grading_rule_set_id,
                    pom=regla_f.pom).first()
                ser = GradingRuleSerializer(rj, data={'breaks': IV_F, 'increment_break': None,
                                                      'talla_break_label': None}, partial=True)
                ok(ser.is_valid(), 'ⓒ porta ③ `GradingRuleSerializer`: la mateixa forma passa',
                   getattr(ser, 'errors', None))

                # ⓓ propagar i llegir la corba.
                sf_banc = SizeFitting.objects.filter(model_id=BANC).order_by('numero').first()
                _post(generate_grading_view, {'new_version': True}, BANC)
                gv = vigent_grading_version(sf_banc)
                corba = {sp.size_label: float(sp.graded_value_cm) for sp in
                         GradedSpec.objects.filter(grading_version=gv, pom=regla_f.pom)}
                esperat = {'XS': base_f, 'S': base_f, 'M': base_f + 2,
                           'L': base_f + 4, 'XL': base_f + 7}
                ok(corba == esperat,
                   f'ⓓ propagat: XS/S al pas 0 · M→L al 2 · XL al 3  (base {base_f})',
                   f'{corba} != {esperat}')
                print(f'      {corba}')
                raise _Revert()
        except _Revert:
            pass
        ok(ModelGradingRule.objects.get(pk=regla_f.pk).breaks is None,
           '⑦ REVERTIT: la F del banc segueix com era (breaks NULL)')

        # ── ⑧ LINEAR → FIXED → LINEAR no ressuscita cap xip fantasma ────────────────────────
        print('\n⑧ canviar de règim no deixa fòssils')
        _post(set_pom_regim_view, {'logica': 'LINEAR', 'increment_base': 2,
                                   'breaks': [{'inici': 'M', 'final': 'L', 'delta': 4}]},
              model.pk, pom.pk)
        ok(rule().breaks is not None, 'la regla té relleu abans de canviar de règim')
        # El payload que la pantalla envia quan desa un règim que no gradua (`relleuResidual`).
        resp = _post(set_pom_regim_view, {'logica': 'FIXED', 'breaks': [],
                                          'increment_break': None, 'talla_break_label': None},
                     model.pk, pom.pk)
        ok(resp.status_code == 200, 'es desa com a FIXED', resp.data)
        r = rule()
        ok(r.breaks is None and r.increment_break is None and r.talla_break_label is None,
           '🚨 el FIXED ha quedat NET: cap fòssil a la BD',
           (r.breaks, r.increment_break, r.talla_break_label))
        resp = _post(set_pom_regim_view, {'logica': 'LINEAR', 'increment_base': 2},
                     model.pk, pom.pk)
        ok(resp.status_code == 200 and rule().breaks is None,
           '🚨 tornant a LINEAR no ressuscita cap xip fantasma', resp.data)

        # Deixa el model de prova amb la forma NOVA, que és el que la QA de pantalla vol veure.
        _post(set_pom_regim_view, {
            'logica': 'LINEAR', 'increment_base': 2,
            'breaks': [{'inici': 'S', 'final': 'L', 'delta': 3}],
        }, model.pk, pom.pk)
        propaga()
        print(f'\n  (el model {CODI} queda amb l\'interval S→L +3, com el deixava el tram F)')

    print()
    fallits = resultats.count(False)
    if fallits:
        print(f'❌ {fallits} de {len(resultats)} han fallat')
        return 1
    print(f'✅ {len(resultats)}/{len(resultats)} — el payload de F4-BIS entra, '
          f'no mou cap cel·la, i la porta segueix guardant')
    return 0


if __name__ == '__main__':
    sys.exit(main())
