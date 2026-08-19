"""PARSER de `docs/ordres/GRADING_ENTRADA_MODELS_BROWNIE.md` — la bústia de fitxes de Brownie.

Pur: llegeix text i torna estructures. Cap ORM, cap escriptura. Viu al costat de la comanda que
el consumeix perquè no és una utilitat de la casa: és el lector d'UN document concret.

── QUÈ HI HA REALMENT AL DOCUMENT (cens del 16/08, 27 fitxes) ──────────────────────────────
No totes tenen la mateixa forma, i la diferència MANA:

  · **3 fitxes amb RUN i GRADING** (1 «Dessuadora Animal», 2 «RUFFLES», 4 «MEREDITH»): porten
    columnes per talla i una o dues columnes de Δ. Són les úniques que poden donar regles
    residents, i per tant les úniques que produeixen cel·les de paritat.
  · **24 fitxes de TALLA BASE SOLA**: una única columna («S», o «BASE · S»). El document ho diu
    en clar a les seves notes («Aquesta fitxa NO porta grading — només talla S»). Es sembren
    igual —són el corpus de comparació amb el catàleg— però no deriven cap regla.

Les capçaleres varien (`DESCRIPCIÓ (EN)` · `DESCRIPTION (EN)` · `POM`, i columnes de soroll com
`PROTO`, `SAMPLE (RECTI 1)`, `ADJUSTMENTS`, `COMMENTS`). El parser identifica les columnes de
TALLA per la seva etiqueta contra el run declarat, i descarta la resta: així una columna nova al
document no s'endú cap valor a una talla inventada.

⚠️ **LES DUES COLUMNES DE Δ NO S'INTERPRETEN.** Les fitxes 2 i 4 porten `GRAD. XXS-XS` i
`GRAD. XS-L`, i quina és «la bona» és precisament la pregunta oberta del document. El parser les
recull com a dada crua i **ningú les fa servir per derivar**: les regles surten dels VALORS PER
TALLA, via `derive_rules_from_fitxa`, que és el camí que l'import ja té. El Δ del document queda
com a senyal de verificació, no com a font.

⚠️ **COMA DECIMAL**: el document escriu `1,5`. Es normalitza amb `normalitza_cm`, la mateixa
porta que l'import (no un `replace(',', '.')` paral·lel).
"""
import re

#: Les capçaleres que NO són ni codi, ni descripció, ni talla: soroll de la fitxa original.
_COLS_SOROLL = {'proto', 'adjustments', 'comments', 'sample (proto)', 'sample (proto 1)',
                'sample (recti 1)', 'sample'}


def _neteja(cel):
    return re.sub(r'\*\*|`', '', (cel or '')).strip()


def _es_seccio(cels):
    """Una fila de SECCIÓ: primer camp en negreta i la resta buits («**Bodice**| | |»)."""
    return bool(cels) and cels[0].startswith('**') and not any(c.strip() for c in cels[1:])


def parse(text, normalitza_cm):
    """`[{num, nom, base, run, files: [...]}]`. `normalitza_cm` s'injecta (mòdul pur).

    ⚠️ EL RUN SURT DE LA CAPÇALERA DE LA TAULA, no de la línia de metadades, i és a posta: la
    meitat de les fitxes no declaren «Talles del run» enlloc (la 4 «MEREDITH» en porta cinc
    columnes i cap línia que ho digui). Llegir-lo de les COLUMNES és llegir el que el document
    realment té; la línia de metadades, quan hi és, només serveix per confirmar-lo.
    """
    out = []
    for bloc in re.split(r'\n## MODEL ', text)[1:]:
        num = int(bloc.split(' ·')[0].strip())
        nom = re.search(r'·\s*"([^"]+)"', bloc).group(1).strip()

        base_m = re.search(r'(?:Talla base[^:]*|Sample size|Talla)\:\*{0,2}\s*\*{0,2}\s*'
                           r'([A-Za-z0-9]+)', bloc)
        base = base_m.group(1).strip() if base_m else 'S'

        cap = re.search(r'^\|\s*CODI\s*\|(.+)$', bloc, re.M)
        if not cap:
            continue
        # ⚠️ +1: la capçalera es captura DESPRÉS de «CODI|», i les files de dades SÍ que porten
        # el codi a la posició 0. Sense el desplaçament, la columna de GRADING s'acabava
        # llegint com si fos la primera talla i tots els valors entraven correguts una casella.
        cols = [(_neteja(c), i + 1) for i, c in enumerate(cap.group(1).strip().strip('|').split('|'))]

        idx_talla, idx_desc, idx_grad = {}, None, []
        for etiqueta, i in cols:
            el = etiqueta.lower()
            if el.startswith('descripció') or el.startswith('description') or el == 'pom':
                if idx_desc is None:
                    idx_desc = i
            elif el.startswith('grad'):
                idx_grad.append((etiqueta, i))
            elif el in _COLS_SOROLL:
                continue
            elif el.startswith('base'):
                idx_talla[base] = i          # «BASE · S» → la talla base
            elif etiqueta:
                idx_talla[etiqueta] = i      # tota la resta de la capçalera ÉS una talla
        run = [et for et, _ in sorted(idx_talla.items(), key=lambda kv: kv[1])]
        if base not in run and run:
            base = run[0]

        files, seccio, ordre = [], None, 0
        for linia in bloc.split('\n'):
            if not linia.startswith('|') or linia.startswith('|---') or 'CODI' in linia[:12]:
                continue
            cels = linia.strip().strip('|').split('|')
            if _es_seccio([c.strip() for c in cels]):
                seccio = _neteja(cels[0])
                continue
            codi = _neteja(cels[0])
            if not codi:
                continue
            valors = {}
            for et, i in idx_talla.items():
                if i < len(cels):
                    v = normalitza_cm(_neteja(cels[i]))
                    if v is not None:
                        valors[et] = v
            if not valors:
                continue
            files.append({
                'codi': codi,
                'descripcio': (_neteja(cels[idx_desc])
                               if (idx_desc is not None and idx_desc < len(cels)) else ''),
                'seccio': seccio or '',
                'valors': valors,
                # CRU i sense interpretar: les fitxes amb dues columnes de Δ les porten totes dues.
                'grading_document': {et: _neteja(cels[i]) for et, i in idx_grad if i < len(cels)},
                'ordre': ordre,
            })
            ordre += 1

        # «Té grading» = el document dona valors a MÉS D'UNA talla. És l'única condició que
        # permet derivar-ne regles; les altres 24 fitxes són de talla base sola i ho diuen elles.
        te_grading = len(run) > 1 and any(len(f['valors']) > 1 for f in files)
        out.append({'num': num, 'nom': nom, 'base': base, 'run': run,
                    'files': files, 'te_grading': te_grading})
    return out
