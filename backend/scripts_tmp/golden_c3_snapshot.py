"""Golden C3 — referència de graduació indexada per la IDENTITAT COMPLETA de la mesura.

Substitueix `golden_163_snapshot.py`, que aplana per `f'{pom_id}|{size}'` i és CEC al canvi
que ve: dues files germanes del mateix POM (capa o instància diferent) li donen el mateix
fitxer, o sigui que no pot detectar ni un col·lapse ni una duplicació.

Clau d'aquest golden: **(model_id, pom_id, capa, instancia, size_label)**.

DUES MÈTRIQUES, capturades i comparades PER SEPARAT:

  · `preview`   — `preview_graded_specs`, els 7 models amb graduació viva. Read-only pur.
                  Els eixos NO surten del motor (que indexa per `pom_id` sol): es recuperen
                  fent el JOIN de tornada contra `BaseMeasurement`, que és qui els sap. Avui,
                  amb les comportes tancades, el join és 1:1; el dia que no ho sigui, el camp
                  `n_germanes` ho farà visible en comptes d'amagar-ho.

  · `generator` — `generate_graded_specs` + relectura de `GradedSpec`, els 5 NO segellats.
                  Aquí els eixos són NATIUS de la taula (`fitting_gradedspec` els porta a la
                  seva unicitat de 5 columnes): no cal endevinar res.

Per què les dues i no només el preview: **qui escriurà quan la clau creixi és el GENERADOR**.
Una referència que només miri el previsualitzador no vigila el camí d'escriptura. Els dos
segellats (163, 182) queden fora de la mètrica de generador perquè `_get_or_create_grading_version`
hi alça `SealedGradingVersionError` abans d'arribar a cap cel·la — no és una omissió, és que
aquell camí no existeix per a ells.

CAP ESCRIPTURA SOBREVIU: la captura del generador viu dins d'un `transaction.atomic()` que
acaba SEMPRE en rollback forçat per excepció. `generate_graded_specs` no és inert (fa
`update_or_create` de specs i posa `SizeFitting.estat='TallesGenerades'`), i aquest script ha
de poder córrer contra staging tants cops com calgui sense moure'n res.

Ús:  venv/bin/python manage.py shell -c "exec(open('scripts_tmp/golden_c3_snapshot.py').read())"
     (opcionals com a globals: MODELS=[...], OUT='/tmp/golden_c3.json')
"""
import json
import sys

from django.db import transaction
from django_tenants.utils import schema_context

# Els 7 models amb graduació viva al corpus post-neteja (02/08). Els dos segellats
# (163, 182) entren només a la mètrica de preview.
MODELS = list(globals().get('MODELS', [162, 163, 174, 182, 186, 268, 269]))
OUT = globals().get('OUT', '/tmp/golden_c3.json')
SCHEMA = globals().get('SCHEMA', 'fhort')


class _Rollback(Exception):
    """Senyal de sortida de l'atomic de captura del generador. Mai no és un error."""


def _clau(model_id, pom_id, capa, instancia, size_label):
    """La clau del golden. Ordre = ordre de la identitat: model → POM → eixos → talla."""
    return f'{model_id}|{pom_id}|{capa}|{instancia}|{size_label}'


with schema_context(SCHEMA):
    from fhort.models_app.models import BaseMeasurement, Model
    from fhort.fitting.models import GradedSpec, SizeFitting
    from fhort.pom.services import (
        SealedGradingVersionError, _load_base_measurements,
        generate_graded_specs, preview_graded_specs,
    )

    preview_cells = {}
    generator_cells = {}
    per_model = {}
    segellats = []

    for model_id in MODELS:
        m = Model.objects.filter(pk=model_id).first()
        if m is None:
            per_model[str(model_id)] = {'existeix': False}
            continue

        # ── Identitat: qui són, de debò, les files que alimenten el motor ────────────
        # Mateix filtre que `_load_base_measurements`, per comptar el mateix conjunt.
        files = list(BaseMeasurement.objects
                     .filter(model_id=model_id, is_active=True, base_value_cm__isnull=False)
                     .exclude(base_value_cm=0)
                     .values('pom_id', 'capa', 'instancia', 'base_value_cm'))
        germanes_per_pom = {}
        for f in files:
            germanes_per_pom.setdefault(f['pom_id'], []).append((f['capa'], f['instancia']))

        # ── MÈTRICA 1 · preview (read-only, els 7) ───────────────────────────────────
        # C3/B — el JOIN de tornada contra `BaseMeasurement` per recuperar els eixos JA NO CAL:
        # des de la Fase B el motor els porta a la clau. Es manté el recompte de germanes
        # perquè `n_germanes` segueixi sent el senyal visible del dia que n'hi hagi més d'una.
        bases = _load_base_measurements(model_id)
        specs = preview_graded_specs(m, bases)
        n_prev = 0
        for (pom_id, capa, instancia), fila in specs.items():
            for size_label, val in fila.items():
                preview_cells[_clau(model_id, pom_id, capa, instancia, size_label)] = {
                    'v': val,
                    # Amb 1 germana això és soroll; amb 2+ és EL senyal.
                    'n_germanes': len(germanes_per_pom.get(pom_id) or [1]),
                }
                n_prev += 1

        # ── MÈTRICA 2 · generador (dins de rollback, els NO segellats) ───────────────
        n_gen = 0
        motiu_gen = None
        sf = SizeFitting.objects.filter(model=m).first()
        if sf is None:
            motiu_gen = 'sense SizeFitting'
        else:
            try:
                with transaction.atomic():
                    from fhort.fitting.services import vigent_grading_version
                    gv = vigent_grading_version(sf.pk)
                    # Buidem la versió ABANS de generar. Sense això llegiríem el CONTINGUT de
                    # la versió i no la SORTIDA d'aquesta passada: el model 162 arrossega 21
                    # specs ràncies de POMs que avui la llei D2 ja no emet (no tenen regla), i
                    # el golden n'hauria comptat 42 on el generador n'ha escrit 21. Una
                    # referència que barregi sortida i sediment és una regla torta.
                    # Tot això viu dins de l'atomic que es desfà: a staging no hi passa res.
                    GradedSpec.objects.filter(grading_version=gv).delete()
                    generate_graded_specs(sf.pk)
                    for s in GradedSpec.objects.filter(grading_version=gv, is_active=True).values(
                            'pom_id', 'capa', 'instancia', 'size_label', 'graded_value_cm'):
                        generator_cells[_clau(model_id, s['pom_id'], s['capa'],
                                              s['instancia'], s['size_label'])] = s['graded_value_cm']
                        n_gen += 1
                    raise _Rollback()
            except _Rollback:
                pass                      # captura feta i desfeta: res no ha sobreviscut
            except SealedGradingVersionError:
                motiu_gen = 'versió segellada'
                segellats.append(model_id)
                n_gen = None
            except Exception as e:         # qualsevol altre motiu es fa VISIBLE, no s'empassa
                motiu_gen = f'{type(e).__name__}: {e}'
                n_gen = None

        per_model[str(model_id)] = {
            'existeix': True,
            'codi': m.codi_intern,
            'base_size': m.base_size_label,
            'size_run': m.size_run_model,
            'n_files_base': len(files),
            'n_poms_preview': len(specs),
            'n_celles_preview': n_prev,
            'n_celles_generador': n_gen,
            'motiu_sense_generador': motiu_gen,
            'poms_amb_germanes': sorted(p for p, g in germanes_per_pom.items() if len(g) > 1),
        }

    payload = {
        'versio_golden': 'c3-identitat-completa-v1',
        'clau': 'model_id|pom_id|capa|instancia|size_label',
        'models': MODELS,
        'segellats_sense_generador': sorted(segellats),
        'n_celles_preview': len(preview_cells),
        'n_celles_generador': len(generator_cells),
        'per_model': per_model,
        'preview': dict(sorted(preview_cells.items())),
        'generator': dict(sorted(generator_cells.items())),
    }
    with open(OUT, 'w') as fh:
        json.dump(payload, fh, indent=0, sort_keys=True)

    sys.stdout.write(
        f'golden C3 → {OUT}\n'
        f'  preview  : {len(preview_cells)} cel·les · {len([k for k in per_model if per_model[k].get("existeix")])} models\n'
        f'  generador: {len(generator_cells)} cel·les · segellats fora: {sorted(segellats)}\n'
    )
    for mid in MODELS:
        d = per_model.get(str(mid), {})
        if not d.get('existeix'):
            sys.stdout.write(f'  · {mid}: NO EXISTEIX\n')
            continue
        germ = d['poms_amb_germanes']
        sys.stdout.write(
            f'  · {mid} {d["codi"]:<16} base={d["n_files_base"]:>3} '
            f'prev={d["n_celles_preview"]:>4} gen={str(d["n_celles_generador"]):>4}'
            f'{"  [" + d["motiu_sense_generador"] + "]" if d["motiu_sense_generador"] else ""}'
            f'{"  GERMANES:" + str(germ) if germ else ""}\n'
        )
