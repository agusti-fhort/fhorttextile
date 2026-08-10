"""EL MOTOR NO S'HA MOGUT — la prova que el tram del 10/08 és de PRESENTACIÓ i no de dada.

El tram canvia com es PINTA la talla de trencament (convenció del document, ±1) i obre el canvi
de sistema de talles. Cap de les dues coses ha de tocar un sol número graduat. Això no es pot
afirmar: es mesura.

COM. `GradedSpec` guarda el que el motor va emetre ABANS d'aquest tram (versió activa del model
1320). `preview_graded_specs` és el bessó sense persistència del generador —hi ha tests que
n'exigeixen la igualtat— i es torna a executar ARA, amb el codi d'avui, sobre les MATEIXES
mesures base. Si les dues taules són idèntiques cel·la a cel·la, la dada no s'ha mogut.

🔑 Es compara contra el que hi ha DESAT, no contra una segona execució del mateix codi: dues
crides al mateix motor sempre coincideixen i no demostrarien res.

NO ESCRIU RES (`preview_*` no persisteix i no es toca cap GradedSpec).

    backend/venv/bin/python ops/qa/qa_motor_1320_no_s_ha_mogut.py
"""
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'backend'))

import django  # noqa: E402

django.setup()

from django_tenants.utils import schema_context  # noqa: E402

from fhort.fitting.models import GradedSpec, GradingVersion  # noqa: E402
from fhort.models_app.models import Model  # noqa: E402
from fhort.pom.services import preview_graded_specs  # noqa: E402

TENANT = 'fhort'
MODEL_ID = 1320


def main():
    with schema_context(TENANT):
        model = Model.objects.get(id=MODEL_ID)
        gv = (GradingVersion.objects
              .filter(size_fitting__model_id=MODEL_ID, is_active=True)
              .order_by('-version_number').first())
        if gv is None:
            sys.exit(f'El model {MODEL_ID} no té cap GradingVersion activa: no hi ha «abans».')

        desat = {}
        base_values = {}
        for gs in GradedSpec.objects.filter(grading_version=gv).select_related('pom'):
            clau = (gs.pom_id, gs.capa or '', gs.instancia or '')
            desat.setdefault(clau, {})[gs.size_label] = gs.graded_value_cm
            if gs.size_label == model.base_size_label:
                base_values[clau] = gs.graded_value_cm

        print(f'model {MODEL_ID} · run {model.size_run_model} · base {model.base_size_label!r} '
              f'· ruleset {model.grading_rule_set_id}')
        print(f'GradedSpec DESATS (versió {gv.version_number}, activa): '
              f'{sum(len(v) for v in desat.values())} cel·les / {len(desat)} mesures')
        if not base_values:
            sys.exit(f'Cap cel·la a la talla base {model.base_size_label!r}: no hi ha d\'on partir.')

        avisos = []
        ara = preview_graded_specs(model, base_values, avisos)
        print(f'PREVIEW amb el codi d\'AVUI:            '
              f'{sum(len(v) for v in ara.values())} cel·les / {len(ara)} mesures')
        if avisos:
            print(f'  avisos del motor: {avisos[:5]}')

        # Cel·la a cel·la. Es comparen com a Decimal: `1.50` i `1.5` són el mateix número i una
        # diferència de format no és un desplaçament de graduació.
        def q(v):
            return None if v is None else Decimal(str(v)).normalize()

        difs, nomes_desat, nomes_ara = [], [], []
        for clau, files in desat.items():
            if clau not in ara:
                nomes_desat.append(clau)
                continue
            for talla, val in files.items():
                nou = ara[clau].get(talla)
                if nou is None:
                    difs.append((clau, talla, val, '(cap)'))
                elif q(val) != q(nou):
                    difs.append((clau, talla, val, nou))
        for clau in ara:
            if clau not in desat:
                nomes_ara.append(clau)

        print('═' * 72)
        print(f'{"CEL·LES QUE DIFEREIXEN":<28} {len(difs):>5}')
        print(f'{"mesures només al DESAT":<28} {len(nomes_desat):>5}')
        print(f'{"mesures només a l\'ARA":<28} {len(nomes_ara):>5}')
        print('═' * 72)
        for clau, talla, abans, despres in difs[:25]:
            print(f'   pom {clau[0]} {clau[1:]}  {talla:<6} {abans} → {despres}')
        if nomes_desat[:10]:
            print(f'   només desat: {nomes_desat[:10]}')
        if nomes_ara[:10]:
            print(f'   només ara:   {nomes_ara[:10]}')

        ok = not difs and not nomes_desat and not nomes_ara
        print(f'\n{"✓ LA DADA NO S HA MOGUT" if ok else "✗ EL MOTOR HA CANVIAT DE RESULTAT"}')
        return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
