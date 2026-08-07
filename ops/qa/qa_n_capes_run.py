"""Fum de la nit N1-N3 — les capes del RUN, end-to-end i READ-ONLY.

## Per què READ-ONLY i per què no pel navegador

Dues restriccions manen aquesta nit i totes dues empenyen al mateix lloc:

  1. **Règim nocturn: CAP esborrat de dades.** Els fums de cicle (`qa_w2_cicle_model.py`)
     creen un model i el destrueixen al final. Aquesta nit no es destrueix res, ni tan sols
     el que un mateix ha creat: aquest fum no escriu **ni una fila**.
  2. **`fhort` no té cap model** (V4, 06/08 vespre). Qualsevol fum que necessiti un model viu
     no es pot córrer fins que hi hagi corpus de QA nou.

El que sí que es pot verificar sense escriure res és tot el que N1-N3 toquen: el model de
dades del run, el contracte de l'API que el pinta, i la funció d'ordre del pas 3 contra els
runs REALS de staging. La capa HTTP i el clic no hi passen; el codi de les vistes, els
serializers i la BD sí.

    backend/venv/bin/python ../ops/qa/qa_n_capes_run.py
"""
import os
import pathlib
import sys

BACKEND = pathlib.Path(__file__).resolve().parents[2] / 'backend'
sys.path.insert(0, str(BACKEND))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fhort.settings')

import django                                     # noqa: E402
django.setup()

from django.contrib.auth import get_user_model    # noqa: E402
from django_tenants.utils import schema_context   # noqa: E402
from rest_framework.test import APIClient         # noqa: E402

HOST = {'HTTP_HOST': 'staging.fhorttextile.tech'}
CANONICS = ['ALPHA_EU_W', 'ALPHA_EU_M', 'NUMERIC_EU_W', 'BABY_EU_CM']
# C3 (07/08) — `WOMAN_BRW_01` ja no hi és. L'Agus va resoldre D2: era la resta d'un experiment
# («Prova BRW ALPHA UE»), i el grading BRW de debò penja del canònic ALPHA_EU_W retallat pel
# model. El fum comprovava que amb client BRW el seu run propi sortís PRIMER; ara la prova és
# la que queda quan el client no en té cap de propi — que l'ordre no s'inventi res i no amagui.
TIPUS_VALIDS = {'ALPHA', 'NUM', 'MESOS', 'ALTURA'}


def main():
    problemes, notes = [], []
    with schema_context('fhort'):
        from fhort.pom.models import SizeSystem
        from fhort.pom.size_labels import conflicte_tipus_escala, dedueix_tipus_escala

        # ── N1a · el model de dades: les 4 capes hi són i la classificació ha corregut ────
        runs = list(SizeSystem.objects.prefetch_related(
            'talles', 'targets', 'construccions', 'fits', 'grups').select_related('customer'))
        sense_tipus = [r.codi for r in runs if not r.tipus_escala]
        dolent = [r.codi for r in runs if r.tipus_escala and r.tipus_escala not in TIPUS_VALIDS]
        if dolent:
            problemes.append(f'N1a · tipus_escala fora del vocabulari: {dolent}')
        print(f'N1a · {len(runs)} runs · classificats {len(runs) - len(sense_tipus)} · '
              f'sense classificar {len(sense_tipus)} {sense_tipus}')

        # La classificació ha de ser IDEMPOTENT: tornar-la a calcular no pot donar una altra cosa.
        for r in runs:
            if not r.tipus_escala:
                continue
            etiquetes = [t.etiqueta for t in r.talles.all().order_by('ordre', 'id')]
            tipus, _font = dedueix_tipus_escala(etiquetes, r.base_unit)
            if tipus and tipus != r.tipus_escala:
                problemes.append(
                    f'N1a · {r.codi}: desat «{r.tipus_escala}» però es dedueix «{tipus}»')

        # Els `base_unit` que contradiuen les seves pròpies etiquetes: NO és un problema del
        # codi, és una dada a corregir. S'anota, no fa vermell.
        for r in runs:
            etiquetes = [t.etiqueta for t in r.talles.all().order_by('ordre', 'id')]
            if conflicte_tipus_escala(etiquetes, r.base_unit):
                notes.append(f'N1a · {r.codi}: base_unit={r.base_unit} contradiu les etiquetes '
                             f'(tipus_escala={r.tipus_escala}) — dada a corregir')

        # ── N1b · el contracte de l'API: capes per CODI, i escriptura validada ────────────
        u = get_user_model().objects.filter(is_superuser=True).first()
        if u is None:
            problemes.append('N1b · cap superusuari a `fhort`: no es pot autenticar l\'APIClient')
            return _informe(problemes, notes)
        c = APIClient()
        c.force_authenticate(user=u)

        resp = c.get('/api/v1/size-systems/?page_size=100', **HOST)
        if resp.status_code != 200:
            problemes.append(f'N1b · GET size-systems/ → {resp.status_code}')
        else:
            files = resp.data.get('results', resp.data)
            claus = {'tipus_escala', 'target_codis', 'construccio_codis', 'fit_codis',
                     'grup_codis', 'customer', 'customer_alias'}
            falten = claus - set(files[0].keys()) if files else claus
            if falten:
                problemes.append(f'N1b · el serializer no exposa {sorted(falten)}')
            print(f'N1b · GET size-systems/ 200 · {len(files)} files · capes exposades OK')

        # Els filtres nous han de filtrar de debò (i no petar amb un valor desconegut).
        for q, esperat in (('tipus_escala=ALPHA', 'ALPHA'), ('tipus_escala=ALTURA', 'ALTURA')):
            r2 = c.get(f'/api/v1/size-systems/?{q}&page_size=100', **HOST)
            if r2.status_code != 200:
                problemes.append(f'N1b · GET size-systems/?{q} → {r2.status_code}')
                continue
            files2 = r2.data.get('results', r2.data)
            forasters = [f['codi'] for f in files2 if f['tipus_escala'] != esperat]
            if forasters:
                problemes.append(f'N1b · el filtre {q} deixa passar {forasters}')
            print(f'N1b · filtre {q} → {len(files2)} runs, tots {esperat}')

        # ── N2 · el payload que pinta la Size Library ─────────────────────────────────────
        r3 = c.get('/api/v1/sizing-profiles/?target=WOMAN', **HOST)
        if r3.status_code != 200:
            problemes.append(f'N2 · GET sizing-profiles/?target=WOMAN → {r3.status_code}')
        else:
            perfils = r3.data['results']
            sense_run = [p['id'] for p in perfils if not p.get('size_system')]
            if sense_run:
                problemes.append(f'N2 · perfils sense size_system al payload: {sense_run}')
            claus_run = {'tipus_escala', 'target_codis', 'construccio_codis', 'fit_codis',
                         'grup_codis', 'customer_nom'}
            if perfils:
                falten = claus_run - set(perfils[0]['size_system'].keys())
                if falten:
                    problemes.append(f'N2 · size_system del perfil sense {sorted(falten)}')
            print(f'N2 · GET sizing-profiles/?target=WOMAN 200 · {len(perfils)} perfils · '
                  f'el run hi porta les seves capes')

        # ── N3 · la proximitat, contra els 4 canònics ────────────────────────────────────
        # Es reprodueix aquí la funció d'ordre del pas 3 (`utils/proximitatRun.js`) i es
        # comprova contra les dades REALS. Si el JS i això divergeixen, un dels dos menteix.
        refs = [r for r in runs if r.codi in CANONICS]
        if len(refs) != len(CANONICS):
            problemes.append(f'N3 · no hi són els {len(CANONICS)} canònics de referència: '
                             f'trobats {[r.codi for r in refs]}')
        else:
            # Un client SENSE run propi no ha de fer desaparèixer res ni guanyar-se cap
            # primer lloc regalat: l'eix de client només desempata quan n'hi ha un que hi casa.
            ordenats = _ordena(refs, target='WOMAN', customer_codi='BRW')
            if len(ordenats) != len(CANONICS):
                problemes.append('N3 · la proximitat ha AMAGAT algun run (ha d\'ordenar, mai amagar)')
            if ordenats[0].codi != 'ALPHA_EU_W':
                problemes.append(f'N3 · amb client BRW (que ja no té run propi) i target WOMAN, '
                                 f'el primer hauria de ser el canònic ALPHA_EU_W i és '
                                 f'{ordenats[0].codi}')
            print('N3 · ordre amb client BRW · target WOMAN: '
                  + ' › '.join(r.codi for r in ordenats))
            sense_client = _ordena(refs, target='WOMAN', customer_codi=None)
            if sense_client[0].codi != 'ALPHA_EU_W':
                problemes.append(f'N3 · sense client, el primer hauria de ser el canònic '
                                 f'ALPHA_EU_W i és {sense_client[0].codi}')
            print('N3 · ordre sense client       · target WOMAN: '
                  + ' › '.join(r.codi for r in sense_client))

    return _informe(problemes, notes)


def _prop_capa(codis, valor):
    if not valor:
        return 0
    if not codis:
        return 1
    return 0 if valor in codis else 2


def _ordena(runs, target, customer_codi):
    """Mirall exacte de `frontend/src/utils/proximitatRun.js:ordenaPerProximitat`."""
    def clau(r):
        origen = 1 if not r.customer_codi else (0 if r.customer_codi == customer_codi else 2)
        return (
            _prop_capa([t.codi for t in r.targets.all()], target),
            origen,
            _prop_capa([c.codi for c in r.construccions.all()], None),
            _prop_capa([f.codi for f in r.fits.all()], None),
            _prop_capa([g.codi for g in r.grups.all()], None),
            r.nom or r.codi or '',
        )
    return sorted(runs, key=clau)


def _informe(problemes, notes):
    print()
    for n in notes:
        print(f'  🟡 ANOTAT · {n}')
    if problemes:
        print(f'\n❌ {len(problemes)} PROBLEMES')
        for p in problemes:
            print(f'  · {p}')
        return 1
    print('\n✅ FUM VERD · cap escriptura feta')
    return 0


if __name__ == '__main__':
    sys.exit(main())
