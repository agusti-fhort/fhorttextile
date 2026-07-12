"""Capa `FTT-POM` — ESPECIFICACIÓ CANÒNICA i reader.

═══════════════════════════════════════════════════════════════════════════════
AQUEST DOCSTRING ÉS L'ESPECIFICACIÓ. S2 (writer) la CONSUMEIX, no la redefineix.
Si el format ha de canviar, canvia aquí i el writer el segueix.
═══════════════════════════════════════════════════════════════════════════════

QUÈ ÉS
------
La capa que FTT afegeix als DXF que exporta: les mesures (POMs) ancorades a la
geometria, dibuixades i etiquetades DINS del fitxer. És l'única marca de FHORT que
viatja dins el lliurable, i fa que el DXF sigui **autocontingut**: el patronista obre
el fitxer al seu CAD i hi veu on van les mesures, cosa que cap altre actor del nínxol
no li dona.

LES DUES LLEIS (V2 §4.4 · E1)
-----------------------------
1. **Projecció, mai font de veritat.** La veritat viu a `PatternPOM` (BD). La capa es
   genera en exportar i, en reimportar, es llegeix com a **PROPOSTA a validar** — mai
   com a escriptura directa. Si algú edita la capa al seu CAD, no ha canviat res del
   nostre sistema: ha fet una proposta.
2. **Accelerador, no dependència.** El CAD del mig pot preservar-la, transformar-la o
   descartar-la, i no ho sabrem fins que ho provem amb cada CAD (entrada nova al perfil
   d'empremta). Si es perd, el reancoratge manual continua sent el camí. Res del motor
   pot dependre que la capa sobrevisqui.

FORMAT
------
Nom de capa: **`FTT-POM`** (alfabètica a propòsit: les capes AAMA són numèriques —
1, 2, 3, 8, 14… — i així no en pot col·lidir cap, ni les no catalogades com la 15
d'AMELIA).

Per cada POM ancorat, DUES entitats:

  · La **línia de mesura**, a la capa `FTT-POM`:
      - mesura recta      → `LINE` del punt A al punt B;
      - mesura sobre vora → `POLYLINE` que segueix la vora (la longitud d'arc real).

  · L'**etiqueta**, un `TEXT` a la capa `FTT-POM`, assegut al **punt mig** de la mesura:

        FTT <codi> <nom canònic EN> = <valor> mm

    Exemple:  `FTT POM-001 CHEST WIDTH = 525.0 mm`

    - El `codi` és el codi canònic del POM (`POMMaster`), sense espais.
    - El nom va en **anglès canònic** (la llengua franca del patronatge).
    - El decimal és **sempre PUNT**, i les unitats **sempre mm**, tant si el CAD
      d'origen feia servir coma com si treballava en polzades. Aquesta capa és NOSTRA:
      no imita l'empremta del fitxer, la contradiu deliberadament perquè sigui
      inequívoca.

I una entitat de **metadades**, una sola per document, `TEXT` a la capa `FTT-POM`:

        FTT-META v=<versio> src=fhort model=<codi_model> ts=<iso8601>

    Exemple:  `FTT-META v=3 src=fhort model=BRW-26-SS-0002 ts=2026-07-12T18:00:00Z`

    Diu de quina versió del `PatternFile` surt el fitxer. En reimportar, és el que
    permet saber si el DXF que torna és nét del que vam exportar o d'una versió vella.

PER QUÈ UN FORMAT DE TEXT I NO XDATA
------------------------------------
Els XDATA/EED d'AutoCAD serien més nets, però **cap CAD de patronatge en garanteix la
supervivència** i, sobretot, no els veu ningú. Un TEXT el llegeix el patronista amb els
ulls, i sobreviu a qualsevol importador que conservi entitats. Redundant i lleig, però
robust — que és el que ha de ser una projecció.
"""
from __future__ import annotations

import re
from typing import Iterable, Optional

from .geometry import POMAnchorData

#: El nom de la capa. Font única: writer (S2) i reader (aquí) el prenen d'aquí.
FTT_POM_LAYER = 'FTT-POM'

#: Prefixos de les dues menes de TEXT de la capa.
POM_PREFIX = 'FTT'
META_PREFIX = 'FTT-META'

_RE_POM = re.compile(
    r'^FTT\s+(?P<codi>\S+)\s+(?P<nom>.+?)\s*=\s*(?P<valor>-?\d+(?:\.\d+)?)\s*mm\s*$',
    re.IGNORECASE,
)
_RE_META = re.compile(r'^FTT-META\s+(?P<parells>.*)$', re.IGNORECASE)
_RE_KV = re.compile(r'(\w+)=(\S+)')


def format_pom_text(codi: str, nom: str, valor_mm: float) -> str:
    """L'etiqueta d'un POM. **S2 (writer) ha de fer servir aquesta funció**, no una
    còpia del format: així l'especificació no pot divergir entre qui escriu i qui llegeix."""
    return f'{POM_PREFIX} {codi} {nom} = {valor_mm:.1f} mm'


def format_meta_text(versio: int, model: str = '', ts: str = '') -> str:
    """La metadada del document. Mateixa llei que `format_pom_text`."""
    parts = [f'{META_PREFIX} v={versio}', 'src=fhort']
    if model:
        parts.append(f'model={model}')
    if ts:
        parts.append(f'ts={ts}')
    return ' '.join(parts)


def parse_pom_text(text: str) -> Optional[POMAnchorData]:
    """Etiqueta → `POMAnchorData`. None si el TEXT no és nostre.

    Ull: torna el POM **sense punts d'ancoratge**. Els punts els posa el reader, que
    és qui veu la línia de mesura que acompanya l'etiqueta.
    """
    m = _RE_POM.match(text.strip())
    if not m:
        return None
    return POMAnchorData(
        pom_code=m.group('codi'),
        valor_mesurat_mm=float(m.group('valor')),
        definicio_mesura={'nom': m.group('nom').strip()},
    )


def parse_meta_text(text: str) -> Optional[dict]:
    """`FTT-META v=3 src=fhort …` → dict. None si no és una metadada nostra."""
    m = _RE_META.match(text.strip())
    if not m:
        return None
    return dict(_RE_KV.findall(m.group('parells')))


class FTTPOMLayerReader:
    """Llegeix la capa `FTT-POM` d'un DXF que hem exportat nosaltres.

    Treballa sobre un document ezdxf ja obert (l'`AAMAReader` ja l'ha llegit: no cal
    tornar a parsejar el fitxer). El resultat és **una proposta**, no un fet: qui la
    consumeixi (S6) l'ha de fer validar.
    """

    def read(self, doc) -> tuple[tuple[POMAnchorData, ...], dict]:
        """→ (poms, metadades). Un DXF sense capa FTT-POM torna ((), {}) — no és un error:
        és el cas normal d'un fitxer que ve del client."""
        textos: list[tuple[float, float, str]] = []
        mesures: list[tuple[float, float, tuple[tuple[float, float], ...]]] = []

        for entity in _ftt_entities(doc):
            kind = entity.dxftype()
            if kind == 'TEXT':
                ins = entity.dxf.insert
                textos.append((ins.x, ins.y, entity.dxf.text))
            elif kind == 'LINE':
                s, e = entity.dxf.start, entity.dxf.end
                punts = ((s.x, s.y), (e.x, e.y))
                mesures.append(((s.x + e.x) / 2, (s.y + e.y) / 2, punts))
            elif kind == 'POLYLINE':
                punts = tuple((v.dxf.location.x, v.dxf.location.y) for v in entity.vertices)
                if punts:
                    mig = punts[len(punts) // 2]
                    mesures.append((mig[0], mig[1], punts))

        metadades: dict = {}
        poms: list[POMAnchorData] = []

        for tx, ty, text in textos:
            meta = parse_meta_text(text)
            if meta is not None:
                metadades.update(meta)
                continue
            pom = parse_pom_text(text)
            if pom is None:
                continue
            # L'etiqueta seu al punt mig de la seva mesura: així s'aparellen.
            punts = _mesura_mes_propera(tx, ty, mesures)
            poms.append(POMAnchorData(
                pom_code=pom.pom_code,
                punts_ancora=punts,
                definicio_mesura=pom.definicio_mesura,
                valor_mesurat_mm=pom.valor_mesurat_mm,
            ))

        return tuple(poms), metadades


def _ftt_entities(doc) -> Iterable:
    """Totes les entitats de la capa FTT-POM, siguin al modelspace o dins d'un BLOCK."""
    for e in doc.modelspace():
        if e.dxf.layer == FTT_POM_LAYER:
            yield e
    for block in doc.blocks:
        if block.name.startswith('*'):
            continue
        for e in block:
            if e.dxf.layer == FTT_POM_LAYER:
                yield e


def _mesura_mes_propera(
    x: float, y: float, mesures: list[tuple[float, float, tuple]]
) -> tuple[tuple[float, float], ...]:
    if not mesures:
        return ()
    millor = min(mesures, key=lambda m: (m[0] - x) ** 2 + (m[1] - y) ** 2)
    return millor[2]
