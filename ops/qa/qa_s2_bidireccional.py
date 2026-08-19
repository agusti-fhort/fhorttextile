"""BIDIRECCIONAL DEL LOT COMERCIAL · les llistes de la part B contra `NORMA_LLISTA_canonica.html`.

**PER QUÈ AQUESTA CORREGUDA EXISTEIX.** La bidireccional compara pantalla ↔ MAQUETA, i cap
pantalla del lot comercial en té una de pròpia: la seva referència és **la germana conformada**
(`/clients` es fa com `/models`). Però la §8e diu, amb aquestes paraules, que la graella canònica
**«no és un patró opcional de la pantalla Models: és LA graella de llista de la casa (Models,
Suppliers, Clients, Encàrrecs, Comercial, Fittings…)»**. Si això és cert, `NORMA_LLISTA_canonica`
ha de poder verificar una pantalla que **no** sigui Models — i fins avui no ho havia fet mai.

Això és, doncs, la prova d'aquella afirmació. Si un cas d'aquí falla, la pregunta no és només
«qui té raó, la maqueta o la pantalla?» sinó també **«la canònica és de debò de tota la casa o
només descrivia Models?»** — i la resposta va al report, no al codi.

**COM ESTAN TRIATS ELS SELECTORS.** El fitxer germà diu que van «per TEXT o per ARIA a posta: és
el que un humà veu, no una classe interna». Aquí s'hi afegeix una tercera mena, **estructural**
(`table thead th >> nth=N`), i el motiu és propi d'aquest lot: les etiquetes de columna són
**i18n del lot comercial**, o sigui que ancorar-hi lligaria la mesura a una traducció que pot
canviar per motius que no tenen res a veure amb la pell — el mateix mode de fallada que la coda
del bloc B va patir amb els dos casos ancorats al literal «Pendent». L'`aria` s'usa on n'hi ha
(`aria-current="page"` de la píndola activa) i el text, on és estable.

    FTT_QA_TOKEN=... /tmp/qa-venv/bin/python ops/qa/qa_s2_bidireccional.py
"""
import sys

import qa_bidireccional as base

CANON = 'NORMA_LLISTA_canonica.html'

#: (tram, què és, fitxer de maqueta, selector a la maqueta, gestos a la MAQUETA,
#:  ruta, gestos a la PANTALLA, selector a la pantalla)
CASOS = [
    # ── El MENÚ DE PANTALLA (§8b.2) ───────────────────────────────────────────────────────
    ('S2', 'fletxa ENRERE del menú de pantalla', CANON, '.back', [],
     '/clients', [], '[data-ftt-pagemenu] button >> nth=0'),
    ('S2', 'píndola de vista ACTIVA', CANON, '.mitem.on', [],
     '/clients', [], '[data-ftt-pagemenu] button[aria-current="page"]'),
    ('S2', 'píndola de vista en REPÒS', CANON, '.mitem:not(.on)', [],
     '/clients', [], '[data-ftt-pagemenu] button:not([aria-current]) >> nth=1'),

    # ── La FILA D'IDENTITAT (§8e: comptador + cerca, i res més) ───────────────────────────
    ('S2', 'comptador «X/N» — el número gran', CANON, '.headrow .kpi', [],
     '/clients', [], 'main span:has(> small) >> nth=0'),
    ('S2', 'comptador — el denominador', CANON, '.headrow .kpi small', [],
     '/clients', [], 'main span > small >> nth=0'),
    ('S2', 'rètol de l\'entitat (caption)', CANON, '.headrow .lab', [],
     '/clients', [], 'main span:text-is("clients")'),
    ('S2', 'camp de cerca', CANON, '.headrow input', [],
     '/clients', [], 'main input[type="text"], main input:not([type])'),

    # ── La GRAELLA (§8e) ──────────────────────────────────────────────────────────────────
    ('S2', 'contenidor de la llista', CANON, '.listbox', [],
     '/clients', [], 'main div:has(> table)'),
    ('S2', 'capçalera de columna en repòs', CANON, 'th.c-refc', [],
     '/clients', [], 'table thead th >> nth=1'),
    ('S2', 'capçalera de columna ORDENADA', CANON, 'th.sorted', [],
     '/clients', [], 'table thead th[aria-sort]'),
    ('S2', 'cel·la de la dada REINA (porta el pes)', CANON, 'td.c-nom', [],
     '/clients', [], 'table tbody tr >> nth=0 >> td >> nth=1'),
    ('S2', 'cel·la de referència secundària', CANON, 'td.c-refi', [],
     '/clients', [], 'table tbody tr >> nth=0 >> td >> nth=0'),

    # ── Els BADGES d'estat (§1: fons suau + tinta + vora fina del mateix color) ───────────
    ('S2', 'badge d\'estat VERD («acabat»)', CANON, '.b.ok', [],
     '/clients', [], 'table tbody tr >> nth=0 >> td >> nth=2 >> span'),
    ('S2', 'badge d\'estat TARONJA («en curs»)', CANON, '.b.warn', [],
     '/comercial/comandes', [], 'table tbody tr >> nth=0 >> td >> nth=2 >> span'),
    ('S2', 'badge d\'estat NEUTRE («començat»)', CANON, '.b.neutral', [],
     '/comercial/encarrecs', [], 'table tbody tr >> nth=0 >> td >> nth=1 >> span'),

    # ── La PAPERERA de fila (§8e) ─────────────────────────────────────────────────────────
    ('S2', 'paperera de fila', CANON, '.del', [],
     '/clients', [], 'table tbody tr >> nth=0 >> td:last-child button'),
]

if __name__ == '__main__':
    base.CASOS = CASOS
    sys.exit(base.main() or 0)
