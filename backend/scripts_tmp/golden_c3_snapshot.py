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
#: ── EL BANC · CENS DINÀMIC PEL PREFIX (2026-08-16) ─────────────────────────────────────────
#: Abans hi havia una LLISTA ESCRITA A MÀ (162·163·174·182·186·268·269) i el 16/08 es va
#: descobrir que **cap d'aquells models existia ja**: la sembra v4 del 09/08 se'n va endur el
#: corpus i ningú se'n va assabentar, perquè un golden que mesura models inexistents no peta —
#: emet 0 cel·les i un md5 perfectament estable. Una llista a mà no pot dir «ja no sóc el banc».
#:
#: El cens ara és el PREFIX, que és la definició real de pertinença: qui és del banc és qui
#: `sembra_banc_paritat` ha sembrat. Afegir una fitxa al document MOU l'empremta, i això és el
#: que ha de passar: obliga a un segell nou i datat en comptes de deixar-la entrar en silenci.
PREFIX_BANC = globals().get('PREFIX_BANC', 'BANC-')
MODELS = list(globals().get('MODELS', []))
OUT = globals().get('OUT', '/tmp/golden_c3.json')
SCHEMA = globals().get('SCHEMA', 'fhort')


class _Rollback(Exception):
    """Senyal de sortida de l'atomic de captura del generador. Mai no és un error."""


def _clau(model_id, pom_id, capa, instancia, garment, size_label):
    """La clau del golden. Ordre = ordre de la identitat: model → POM → eixos → talla.

    ── 2026-08-16 · EL `garment` ENTRA A LA CLAU ────────────────────────────────────────────
    Fins avui en quedava fora amb un argument que era bo: afegir-l'hi hauria canviat l'md5 sense
    que cap cel·la s'hagués mogut, i s'hauria perdut la comparació amb `165d6701…` justament al
    tram que l'havia de conservar. Aquell md5 ja no es pot comparar amb res —el seu corpus és
    mort— i el banc es re-segella de zero, o sigui que el motiu per deixar-lo fora ha caducat.

    I hi ha d'entrar: T8-ter ha baixat el garment a la fila i F6 tocarà la derivació per peça.
    Un golden cec a la peça no podria distingir «la regla del short ha canviat» de «no ha
    canviat res». Al banc totes les files són de la mare (les seccions del document NO són
    peces), o sigui que avui és una columna constant — i és exactament quan s'ha d'afegir, no
    el dia que ja hi hagi dany a amagar.
    """
    return f'{model_id}|{pom_id}|{capa}|{instancia}|{garment}|{size_label}'


with schema_context(SCHEMA):
    from fhort.models_app.models import BaseMeasurement, Model
    from fhort.fitting.models import GradedSpec, SizeFitting
    from fhort.pom.services import (
        SealedGradingVersionError, _load_base_measurements,
        generate_graded_specs, preview_graded_specs,
    )

    # El cens del banc, resolt AQUÍ (cal l'ORM). Una llista explícita per `MODELS=[...]` segueix
    # manant: és la porta per mesurar un model concret sense tocar el fitxer.
    if not MODELS:
        MODELS = list(Model.objects.filter(codi_intern__startswith=PREFIX_BANC)
                      .order_by('codi_intern').values_list('pk', flat=True))

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
        # SET-2/T6a (2026-08-11) — la clau del preview té QUATRE trams (`garment` darrere de
        # la instància), i abans se'n desempaquetaven tres: sense això l'arnès peta amb
        # `ValueError: too many values to unpack` i la paritat no es pot ni prendre.
        #
        # ⚠️ EL `garment` NO ENTRA A LA CLAU EMESA, i és deliberat: aquest golden és la
        # referència de NO-REGRESSIÓ del camí `garment=''` (v. el README, «l'abast d'aquesta
        # paritat»), i afegir-lo al `_clau` en canviaria l'md5 sense que cap cel·la s'hagi
        # mogut — es perdria la comparació amb 165d6701… justament al tram que l'ha de
        # conservar. Estendre la clau a la peça és una decisió per al dia que es retirin les
        # comportes, i demana refer el banc i segellar un md5 nou.
        for (pom_id, capa, instancia, _garment), fila in specs.items():
            for size_label, val in fila.items():
                preview_cells[_clau(model_id, pom_id, capa, instancia, _garment, size_label)] = {
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
                    # ⚠️ I ES TORNA A RESOLDRE LA VERSIÓ DESPRÉS DE GENERAR. `generate_graded_specs`
                    # pot obrir-ne una de NOVA (`_get_or_create_grading_version`), i llegint la
                    # d'abans el golden comptava 0 cel·les mentre el log deia «135 specs»: una
                    # mètrica de generador que sempre val zero és estable i CEGA, que és el
                    # pitjor que li pot passar a una referència.
                    gv = vigent_grading_version(sf.pk)
                    _camps = ['pom_id', 'capa', 'instancia', 'size_label', 'graded_value_cm']
                    if any(f.name == 'garment' for f in GradedSpec._meta.fields):
                        _camps.append('garment')
                    for s in GradedSpec.objects.filter(grading_version=gv, is_active=True).values(
                            *_camps):
                        generator_cells[_clau(model_id, s['pom_id'], s['capa'], s['instancia'],
                                              s.get('garment', ''),
                                              s['size_label'])] = s['graded_value_cm']
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
        'versio_golden': 'banc-brownie-v1',
        'clau': 'model_id|pom_id|capa|instancia|garment|size_label',
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
