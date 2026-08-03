"""PROVA D'IDENTITAT del golden — el green flag de la Fase 0 (C3) i de la Fase 1 (C4).

El que es demostra NO és «el fitxer nou és igual al vell» com a bytes d'un fitxer que ja no
existeix, sinó dues coses comprovables sobre el corpus d'AVUI:

  1r · **IDENTITAT DE FORMA** — el golden nou (clau `model|pom|capa|instancia|talla`) conté
       EXACTAMENT la mateixa informació que el vell (clau `pom|talla`, la de
       `golden_163_snapshot.py`): el nou, col·lapsat a la clau del vell, ha de donar el vell
       sencer, sense cap cel·la de més ni de menys i sense cap valor mogut. A més els dos
       eixos han de ser CONSTANTS ('exterior', ''): si no ho fossin, el col·lapse estaria
       amagant informació i la comparació seria falsament verda.

  2n · **IDENTITAT DE CONTINGUT** (opcional, `REF=<ruta>`) — el golden d'avui, cel·la a
       cel·la, contra una referència desada en una sessió anterior. És la comprovació que
       diu si les DADES s'han mogut. Sense ella, la prova de forma només diu que el motor
       segueix sent coherent amb si mateix.

⚠️ C3/B — LA CLAU DEL MOTOR JA ÉS UNA TUPLA. `preview_graded_specs` retorna
`{(pom_id, capa, instancia): {talla: valor}}` des del commit `38636277`. Aquest script encara
feia el JOIN de tornada contra `BaseMeasurement` per recuperar els eixos, indexant per una
clau escalar que ja no existeix: `eixos_per_pom.get(<tupla>)` no trobava mai res i queia al
sentinella ('?', '?'), o sigui DIVERGEIX als 7 models amb els valors intactes. Era un vermell
del regle, no del corpus (Fase 1 de C4, 03/08). Ara la forma de la clau es COMPROVA i, si
torna a canviar, l'script s'atura dient-ho en comptes d'inventar-se un eix.

Qualsevol diferència que no sigui l'afegit dels eixos = ATURADA. No s'arrodoneix.

Ús:  venv/bin/python manage.py shell -c "exec(open('scripts_tmp/golden_c3_prova_identitat.py').read())"
     venv/bin/python manage.py shell -c "REF='scripts_tmp/golden_c4_T0_2026-08-03.json'
exec(open('scripts_tmp/golden_c3_prova_identitat.py').read())"
"""
import json
import sys

from django_tenants.utils import schema_context

MODELS = list(globals().get('MODELS', [162, 163, 174, 182, 186, 268, 269]))
SCHEMA = globals().get('SCHEMA', 'fhort')
REF = globals().get('REF', None)

with schema_context(SCHEMA):
    from fhort.models_app.models import Model
    from fhort.pom.services import _load_base_measurements, preview_graded_specs

    tot_ok = True
    total_cel = 0
    nou_tot = {}
    print(f'{"model":>6} {"vell":>6} {"nou":>6} {"eixos constants":>17}  veredicte')
    print('-' * 62)

    for model_id in MODELS:
        m = Model.objects.filter(pk=model_id).first()
        if m is None:
            print(f'{model_id:>6}      —      —                  —  NO EXISTEIX')
            continue

        bases = _load_base_measurements(m.pk)
        specs = preview_graded_specs(m, bases)

        # ── La forma de la clau és part del contracte: es comprova, no es suposa ──────
        males = [k for k in specs if not (isinstance(k, tuple) and len(k) == 3)]
        if males:
            print(f'{model_id:>6}  CLAU INESPERADA del motor: {males[:3]}')
            print('         (post-C3/B ha de ser (pom_id, capa, instancia) — script obsolet)')
            tot_ok = False
            continue

        # ── EL NOU: la identitat sencera, tal com la desa `golden_c3_snapshot.py` ────
        nou = {}
        eixos_vistos = set()
        for (pom_id, capa, instancia), row in specs.items():
            eixos_vistos.add((capa, instancia))
            for size, val in row.items():
                nou[f'{model_id}|{pom_id}|{capa}|{instancia}|{size}'] = val

        # ── EL VELL: la seva expressió LITERAL (golden_163_snapshot.py:26-28), que
        #    aplana per `pom_id|talla` i per tant NO pot distingir dues germanes ──────
        vell = {}
        duplicats = []
        for (pom_id, _capa, _ins), row in specs.items():
            for size, val in row.items():
                ck = f'{pom_id}|{size}'
                if ck in vell and vell[ck] != val:
                    duplicats.append(ck)
                vell[ck] = val

        # ── El col·lapse: el nou, reduït a la clau del vell ──────────────────────────
        collapsat = {}
        for k, v in nou.items():
            _mid, pom_id, _capa, _ins, size = k.split('|')
            collapsat[f'{pom_id}|{size}'] = v

        constants = (eixos_vistos == {('exterior', '')})
        igual = (collapsat == vell)
        ok = igual and constants and not duplicats

        veredicte = 'IDÈNTIC' if ok else 'DIVERGEIX'
        if not ok:
            tot_ok = False
        print(f'{model_id:>6} {len(vell):>6} {len(nou):>6} {str(sorted(eixos_vistos)):>17}  {veredicte}')

        if not igual:
            nomes_vell = set(vell) - set(collapsat)
            nomes_nou = set(collapsat) - set(vell)
            movi = {k for k in set(vell) & set(collapsat) if vell[k] != collapsat[k]}
            print(f'         només al vell: {sorted(nomes_vell)[:6]}')
            print(f'         només al nou : {sorted(nomes_nou)[:6]}')
            print(f'         valor mogut  : {[(k, vell[k], collapsat[k]) for k in sorted(movi)[:6]]}')
        if not constants:
            print(f'         EIXOS NO CONSTANTS: {sorted(eixos_vistos)} — el col·lapse amagaria informació')
        if duplicats:
            print(f'         COL·LAPSE AMB PÈRDUA: {sorted(set(duplicats))[:6]}')
            print('         (dues germanes amb valors diferents cauen a la mateixa clau vella:')
            print('          el golden vell les hauria comptat com una sola. És el forat de C4.)')
        total_cel += len(nou)
        nou_tot.update(nou)

    print('-' * 62)
    if tot_ok:
        print(f'GREEN FLAG · FORMA: OK — {total_cel} cel·les, {len(MODELS)} models.')
        print('El golden nou conté la mateixa informació que el vell; els dos eixos hi entren')
        print("com a constants ('exterior', ''), sense cap fila de més ni de menys.")
    else:
        print('GREEN FLAG · FORMA: VERMELL — vegeu les divergències de sobre. ATURAR.')

    # ── 2n · IDENTITAT DE CONTINGUT contra la referència desada ──────────────────────
    if REF:
        with open(REF) as fh:
            ref = json.load(fh)
        ref_prev = {k: d['v'] for k, d in ref['preview'].items()}
        nomes_ref = sorted(set(ref_prev) - set(nou_tot))
        nomes_avui = sorted(set(nou_tot) - set(ref_prev))
        moguts = sorted(k for k in set(ref_prev) & set(nou_tot) if ref_prev[k] != nou_tot[k])
        print('-' * 62)
        print(f'REFERÈNCIA {REF}: {len(ref_prev)} cel·les de preview · avui {len(nou_tot)}')
        if not (nomes_ref or nomes_avui or moguts):
            print('GREEN FLAG · CONTINGUT: OK — cap cel·la afegida, perduda ni moguda.')
        else:
            tot_ok = False
            print(f'GREEN FLAG · CONTINGUT: VERMELL — les DADES s\'han mogut des de la referència.')
            print(f'         perdudes ({len(nomes_ref)}): {nomes_ref[:6]}')
            print(f'         noves    ({len(nomes_avui)}): {nomes_avui[:6]}')
            print(f'         mogudes  ({len(moguts)}): {[(k, ref_prev[k], nou_tot[k]) for k in moguts[:6]]}')

    if not tot_ok:
        sys.exit(1)
