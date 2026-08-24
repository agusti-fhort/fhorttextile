"""Banc de compatibilitat: la niada que emetem vs el fitxer que el PolyPattern exporta.

## Què mesura

La niada del 1383 s'obria al PolyPattern de la Montse amb geometria fidel però **sense
desplegar les talles**. Aquest banc compara, entitat a entitat, el DXF+RUL que emetem amb
el que el seu CAD exporta del MATEIX patró —que és, literalment, el fitxer d'origen de
PF20 (`837 CORS 194 VESTIT M3-4 AGUS.DXF`, pujat el 24/08)—, i comprova les quatre coses
que separaven un fitxer graduable d'un que no ho és:

    ①  cap punt de gir ORFE: tot POINT de capa 2 té el seu TEXT `# n` a sobre
    ②  el número de regla d'un gir del COSIT es repeteix a les capes 8 i 14, com fa ell
    ③  la numeració comença a 1 i la regla 1 és la de repòs (mai `DELTA 0`)
    ④  la capçalera del RUL, sencera: version + AUTHOR + UNITS + GRADE RULE TABLE
        (el nom de la taula, COPIAT del DXF; l'autor, el NOSTRE — decisió d'Agus 24/08)

I la invariant que no es pot perdre pel camí: la geometria segueix sortint a **0,0000 mm**
de l'original.

## Lectura, no escriptura

Tot corre dins d'un `transaction.atomic()` avortat: `build_export` no escriu res a la BD
(l'`ExportAcknowledgement` el crea la view, no el motor) i aquí no es passa per cap view.
Cap reconeixement, cap fitxer desat al banc.

## Ús

    venv/bin/python ../ops/qa/banc_niada_vs_polypattern.py        (des de backend/)

Codi de sortida 1 si alguna comprovació falla.
"""
import collections
import os
import re
import sys
from math import hypot

import django

ARREL = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ARREL + '/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fhort.settings')
django.setup()

from django.db import transaction                                      # noqa: E402
from django_tenants.utils import schema_context                        # noqa: E402

PF_ID = 20
GV_ID = 201
TENANT = 'fhort'
REFERENCIA = (ARREL + '/backend/media/fhort/pattern_files/'
              '837_CORS_194_VESTIT_M3-4_AGUS.DXF')

#: Les capes on el CAD escriu números de regla, i qui les porta.
CAPA_GIR, CAPA_PIQUET, CAPA_INTERNA, CAPA_COSIT = '2', '4', '8', '14'
ES_REGLA = re.compile(r'#\s*\d+')


# ── Lectura crua del DXF ─────────────────────────────────────────────────────
# A posta i no amb `AAMAReader`: el que es mesura aquí és el FITXER, i llegir-lo amb el
# nostre propi reader compararia la nostra idea del fitxer amb la nostra idea del fitxer.

def entitats(font):
    linies = (font if isinstance(font, str) else font.decode('utf-8', 'replace')).splitlines()
    fora, cur, i = [], None, 0
    while i < len(linies) - 1:
        codi, valor = linies[i].strip(), linies[i + 1].strip()
        i += 2
        if codi == '0':
            if cur:
                fora.append(cur)
            cur = {'type': valor}
        elif cur is not None:
            if codi == '8':
                cur['layer'] = valor
            elif codi == '1':
                cur['text'] = valor
            elif codi == '2':
                cur['name'] = valor
            elif codi in ('10', '20'):
                try:
                    cur['x' if codi == '10' else 'y'] = float(valor)
                except ValueError:
                    pass
    if cur:
        fora.append(cur)
    return fora


def per_bloc(ents):
    fora, bloc = collections.defaultdict(lambda: collections.defaultdict(list)), None
    for e in ents:
        if e['type'] == 'BLOCK':
            bloc = e.get('name')
        elif e['type'] == 'ENDBLK':
            bloc = None
        if bloc and 'x' in e:
            fora[bloc][(e['type'], e.get('layer'))].append(e)
    return fora


def regles(ents, capa=None):
    return [e for e in ents
            if e['type'] == 'TEXT' and ES_REGLA.fullmatch(e.get('text', '') or '')
            and (capa is None or e.get('layer') == capa)]


def numero(e):
    return int(e['text'].split('#')[1])


def main():
    fallits, ok = [], []

    def prova(nom, cond, detall=''):
        (ok if cond else fallits).append(nom)
        print(f'  {"✓" if cond else "✗"} {nom}{"" if cond else f" → {detall}"}')

    ref = entitats(open(REFERENCIA, encoding='utf-8', errors='replace').read())
    ref_bloc = per_bloc(ref)

    with schema_context(TENANT):
        with transaction.atomic():
            from fhort.patterns.models import PatternFile
            from fhort.patterns.export import build_export
            from fhort.patterns.adapters import DjangoGeometryStore
            from fhort.patterns.engine.aama_reader import AAMAReader, fold_piece
            from dataclasses import replace

            fp = PatternFile.objects.get(pk=PF_ID)
            res = build_export(fp, grading_version_id=GV_ID,
                               destination_profile='polypattern')
            nostre = entitats(res.dxf)
            nostre_bloc = per_bloc(nostre)
            rul = res.rul.decode('utf-8')

            print(f'\n── recompte de regles per capa ({len(regles(nostre))} nostres · '
                  f'{len(regles(ref))} de referència)')
            for capa in (CAPA_GIR, CAPA_INTERNA, CAPA_COSIT):
                n, r = len(regles(nostre, capa)), len(regles(ref, capa))
                prova(f'capa {capa}: {n} regles (referència {r})', n == r, f'{n} vs {r}')
            n4, r4 = len(regles(nostre, CAPA_PIQUET)), len(regles(ref, CAPA_PIQUET))
            print(f'  · capa {CAPA_PIQUET}: {n4} nostres vs {r4} de referència '
                  f'(divergència CONEGUDA: ell escriu un TEXT per PIQUET i nosaltres un per '
                  f'PUNT de piquet — v. l\'informe)')

            print('\n── ① cap punt de gir orfe, peça a peça')
            for peca in sorted(nostre_bloc):
                if not nostre_bloc[peca][('POINT', CAPA_GIR)]:
                    continue
                punts = nostre_bloc[peca][('POINT', CAPA_GIR)]
                coords = {(round(e['x'], 4), round(e['y'], 4))
                          for e in nostre_bloc[peca][('TEXT', CAPA_GIR)]
                          if ES_REGLA.fullmatch(e.get('text', '') or '')}
                orfes = [e for e in punts
                         if (round(e['x'], 4), round(e['y'], 4)) not in coords]
                prova(f'{peca}: {len(punts)} girs, {len(orfes)} orfes',
                      not orfes, f'{len(orfes)} sense TEXT')

            print('\n── ② el gir del cosit porta el número a les capes 2, 8 i 14')
            for peca in sorted(nostre_bloc):
                t8 = nostre_bloc[peca][('TEXT', CAPA_INTERNA)]
                t14 = nostre_bloc[peca][('TEXT', CAPA_COSIT)]
                r8 = len(ref_bloc.get(peca, {}).get(('TEXT', CAPA_INTERNA), []))
                if not t8 and not r8:
                    continue
                prova(f'{peca}: {len(t8)}/{len(t14)} a les capes 8/14 (referència {r8})',
                      len(t8) == len(t14) == r8, f'{len(t8)}/{len(t14)} vs {r8}')
            # i el número ha de ser el MATEIX a les tres capes de cada coordenada
            per_coord = collections.defaultdict(dict)
            for e in regles(nostre):
                if e.get('layer') == CAPA_PIQUET:
                    continue
                per_coord[(round(e['x'], 3), round(e['y'], 3))][e['layer']] = numero(e)
            discordants = [c for c, v in per_coord.items() if len(set(v.values())) > 1]
            prova('el número és el mateix a les tres capes de cada punt',
                  not discordants, f'{len(discordants)} coordenades discordants')

            print('\n── ③ la numeració')
            nums = sorted({numero(e) for e in regles(nostre)})
            prova('comença a 1 (cap `DELTA 0`)', nums[0] == 1, nums[:3])
            prova('cap `RULE: DELTA 0` al RUL', '\nRULE: DELTA 0 ' not in rul)
            repos = [l for l in rul.splitlines() if l.startswith('RULE: DELTA 1 ')]
            prova('la regla 1 és la de REPÒS (tot zeros)',
                  bool(repos) and set(re.findall(r'-?\d+\.\d+', repos[0])) == {'0.00'},
                  repos[:1])

            print('\n── ④ la capçalera del RUL')
            caps = rul.splitlines()[:4]
            prova('version ANSI/AAMA-292-B', caps[0] == 'version ANSI/AAMA-292-B', caps[0])
            prova('AUTHOR: FHORT Textile Tech (decisió d\'Agus, no el nom del CAD)',
                  caps[1] == 'AUTHOR: FHORT Textile Tech', caps[1])
            prova('UNITS: METRIC', caps[2] == 'UNITS: METRIC', caps[2])
            noms_ref = [e['text'][len('GRADE RULE TABLE:'):] for e in ref
                        if e['type'] == 'TEXT'
                        and (e.get('text') or '').startswith('GRADE RULE TABLE:')]
            prova('GRADE RULE TABLE copiat del DXF, no inventat',
                  caps[3] == f'GRADE RULE TABLE:{noms_ref[0]}' if noms_ref else False,
                  f'{caps[3]!r} vs {noms_ref[:1]}')

            print('\n── la invariant: la geometria no s\'ha mogut')
            base = DjangoGeometryStore().load_from(fp)
            plegada = replace(base, pieces=tuple(fold_piece(p) for p in base.pieces))
            rellegit = AAMAReader().read(res.dxf)
            pitjor, comptats = 0.0, 0
            for pv in plegada.pieces:
                pn = rellegit.piece(pv.nom_block)
                if pn is None:
                    continue
                parells = [(a, b) for bv, bn in zip(pv.boundaries, pn.boundaries)
                           for a, b in zip(bv.points, bn.points)]
                parells += list(zip(pv.notches, pn.notches))
                for a, b in parells:
                    pitjor = max(pitjor, hypot(a.x - b.x, a.y - b.y))
                    comptats += 1
            prova(f'{comptats} punts a {pitjor:.4f} mm de l\'original', pitjor < 1e-4,
                  f'{pitjor:.4f} mm')
            prova('autovalidació del round-trip verda',
                  res.autovalidacio.ok, res.autovalidacio.resum()[:120])
            print(f'  · {res.autovalidacio.resum()}')

            transaction.set_rollback(True)

    print(f'\n{len(ok)} ✓ · {len(fallits)} ✗')
    if fallits:
        print('FALLEN: ' + ', '.join(fallits))
    return 1 if fallits else 0


if __name__ == '__main__':
    sys.exit(main())
