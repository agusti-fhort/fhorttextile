"""PROVA D'IDENTITAT del golden C3 — el green flag de la Fase 0.

El que es demostra NO és «el fitxer nou és igual al vell» (impossible: el vell cobreix un
sol model i el seu T0 és d'un corpus anterior a la neteja del 02/08). El que es demostra és:

    sobre el MATEIX model i el corpus d'AVUI, el golden nou conté EXACTAMENT la mateixa
    informació que el vell, amb els dos eixos afegits com a constants ('exterior', ''),
    cap cel·la de més ni de menys i cap valor mogut.

Mètode: es corre el golden VELL (`golden_163_snapshot.py`, clau `pom_id|size`) i el NOU
sobre el mateix model i el mateix instant, i es col·lapsa el nou a la clau del vell. Han de
ser dicts idèntics. A més es verifica que els eixos són constants — perquè si no ho fossin,
el col·lapse estaria amagant informació i la comparació seria falsament verda.

Qualsevol diferència que no sigui l'afegit dels eixos = ATURADA. No s'arrodoneix.

Ús:  venv/bin/python manage.py shell -c "exec(open('scripts_tmp/golden_c3_prova_identitat.py').read())"
"""
import sys

from django_tenants.utils import schema_context

MODELS = list(globals().get('MODELS', [162, 163, 174, 182, 186, 268, 269]))
SCHEMA = globals().get('SCHEMA', 'fhort')

with schema_context(SCHEMA):
    from fhort.models_app.models import BaseMeasurement, Model
    from fhort.pom.services import _load_base_measurements, preview_graded_specs

    tot_ok = True
    total_cel = 0
    print(f'{"model":>6} {"vell":>6} {"nou":>6} {"eixos constants":>17}  veredicte')
    print('-' * 62)

    for model_id in MODELS:
        m = Model.objects.filter(pk=model_id).first()
        if m is None:
            print(f'{model_id:>6}      —      —                  —  NO EXISTEIX')
            continue

        # ── EL VELL: la seva expressió LITERAL (golden_163_snapshot.py:23-28) ─────────
        bases = _load_base_measurements(m.pk)
        specs = preview_graded_specs(m, bases)
        vell = {}
        for pom_id, row in specs.items():
            for size, val in row.items():
                vell[f'{pom_id}|{size}'] = val

        # ── EL NOU: la seva expressió LITERAL (golden_c3_snapshot.py) ────────────────
        files = list(BaseMeasurement.objects
                     .filter(model_id=model_id, is_active=True, base_value_cm__isnull=False)
                     .exclude(base_value_cm=0)
                     .values('pom_id', 'capa', 'instancia'))
        eixos_per_pom = {}
        for f in files:
            eixos_per_pom.setdefault(f['pom_id'], []).append((f['capa'], f['instancia']))

        nou = {}
        eixos_vistos = set()
        for pom_id, row in specs.items():
            for (capa, instancia) in (eixos_per_pom.get(pom_id) or [('?', '?')]):
                eixos_vistos.add((capa, instancia))
                for size, val in row.items():
                    nou[f'{model_id}|{pom_id}|{capa}|{instancia}|{size}'] = val

        # ── El col·lapse: el nou, reduït a la clau del vell ──────────────────────────
        collapsat = {}
        duplicats = []
        for k, v in nou.items():
            _mid, pom_id, _capa, _ins, size = k.split('|')
            ck = f'{pom_id}|{size}'
            if ck in collapsat and collapsat[ck] != v:
                duplicats.append(ck)
            collapsat[ck] = v

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
        total_cel += len(nou)

    print('-' * 62)
    if tot_ok:
        print(f'GREEN FLAG F0: OK — {total_cel} cel·les, {len(MODELS)} models.')
        print('El golden nou conté la mateixa informació que el vell; els dos eixos hi entren')
        print("com a constants ('exterior', ''), sense cap fila de més ni de menys.")
    else:
        print('GREEN FLAG F0: VERMELL — vegeu les divergències de sobre. ATURAR.')
        sys.exit(1)
