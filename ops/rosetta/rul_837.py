"""A + B · El RUL del 837 i el mapa regla→punt.

**Què és aquest fitxer.** `837 CORS 194 VESTIT M3-4.RUL` és la taula de regles de grading
que el PolyPattern de la Montse va exportar per a l'estil del 837. A diferència del camp
(`camp_montse.py`), que és **extensional** —coordenades ja graduades, talla per talla—,
el RUL és **intensional**: diu, per a cada regla, quant es mou el punt que la porta a
cadascuna de les cinc talles. És l'autoria del grading, no el seu resultat.

**Per què no hi ha parser nou.** `engine/rul_reader.py` ja llegeix aquest dialecte des de
S1 i el seu docstring ja avisava del que aquí es confirma: «els deltes d'AMELIA són tots
zero… els valors arribaran amb un RUL poblat de debò». Aquest n'és el primer. Escriure'n
un segon lector duplicaria la gramàtica en un lloc on la del producte ja és correcta, i
faria que una regressió del reader no es veiés aquí. El que aquest mòdul afegeix és el que
el reader no pot saber: **les verificacions sobre els valors** i **el mapa cap a la
geometria**.

── EL MAPA, I PER QUÈ NO ÉS LA IDENTITAT ────────────────────────────────────────
El DXF mestre porta els números de regla com a TEXT ('# 65') assegut sobre el punt que
governen, i `aama_reader` ja els llegeix a `PointData.grade_rule`. Però **les dues
numeracions no coincideixen**: la geometria invoca l'1 i després 65–98, 171–198 i 226–238
(238 números en total, amb la línia de cosit numerada de 3 en 3), i el RUL en declara 90,
de l'1 al 90. Un `# 65` NO és la `RULE: DELTA 65`.

El que sí que hi ha és una correspondència **estructural**, i és verificable:

  · cada peça graduada ocupa un bloc CONTIGU de números al DXF (davant 65–98, esquena
    171–198, màniga 226–238: 34 + 28 + 13 = 75 números, sense forats);
  · el RUL té 90 regles, i les seves **75 últimes** —16–90— es reparteixen en blocs de la
    mateixa mida i en el mateix ordre;
  · la regla 1 és la regla NUL·LA (deltes zero a les cinc talles) i és la que porten les
    dues peces que no gradúen, coll i tapeta.

Això dona tres desplaçaments constants —49, 121, 148— que aquest mòdul **no escriu a mà**:
els deriva dels blocs. I la derivació no s'ha de creure: `exam_rul.py` la posa a prova
reconstruint les quatre talles i comparant-les amb la niada de la Montse. La reconstrucció
tanca a **0,0064 mm de màxim**, que és l'arrodoniment a dos decimals del RUL mateix
(±0,005 mm per component). Un mapa equivocat no dona això; dona metres.

🚨 **El RUL gradua el contorn de TALL, i prou.** Els punts de la línia de cosit porten
números propis (3, 6, 9… al davant) que no són a la taula, i cap desplaçament constant els
casa: mesurat, el millor deixa 11,8 mm. El cosit el deriva el CAD del tall; no és dada
d'autoria. `exam_rul.py` ho torna a mesurar en comptes de donar-ho per bo.

🚩 **Catorze regles que ningú no invoca.** Les 2–15 són al RUL, tenen deltes zero i cap
punt de cap de les cinc peces les demana. No és un error del mapa —el mapa es verifica a
0,006 mm—: la taula és de l'ESTIL i el DXF en porta cinc peces. Es reporta, no s'amaga.
"""
from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'backend'))

from fhort.patterns.engine.aama_reader import AAMAReader              # noqa: E402
from fhort.patterns.engine.geometry import GradeTable, PatternDocument  # noqa: E402
from fhort.patterns.engine.rul_reader import RULReader                # noqa: E402

#: El RUL, tal com ens el van donar. Nom amb espais, tal qual, com la resta del material
#: de la sessió Montse.
RUL_837 = REPO / 'docs' / 'ordres' / '837 CORS 194 VESTIT M3-4.RUL'

#: El patró MESTRE del 1383 (`PatternFile#20`, v3). És el que porta els `# n`.
MESTRE_837 = Path('/var/www/ftt-staging/backend/media/fhort/pattern_files/'
                  '837_CORS_194_VESTIT_M3-4_AGUS.DXF')

#: La capa del contorn de tall. És l'única que el RUL gradua (v. capçalera).
CAPA_TALL = '1'

#: Arrodoniment del RUL: dos decimals per component. La cota de l'error que un mapa
#: CORRECTE pot deixar és la diagonal d'aquesta cel·la, √2 · 0,005 = 0,0071 mm.
ARRODONIMENT_MM = 0.005
COTA_ARRODONIMENT_MM = math.hypot(ARRODONIMENT_MM, ARRODONIMENT_MM)


@dataclass(frozen=True)
class Verificacio:
    """Una comprovació amb el seu veredicte i la seva evidència."""
    codi: str
    titol: str
    ok: bool
    detall: str

    def __str__(self) -> str:
        return f'  {"PASS" if self.ok else "FAIL"}  {self.codi} · {self.titol}\n         {self.detall}'


@dataclass(frozen=True)
class Mapa:
    """El lligam entre els `# n` del DXF i les `RULE: DELTA n` del RUL."""
    #: número de regla del DXF → número de regla del RUL, només per a les peces graduades.
    dxf_a_rul: dict[int, int]
    #: peça → (primer, últim) número de DXF del seu bloc.
    blocs: dict[str, tuple[int, int]]
    #: peça → desplaçament constant DXF − RUL.
    desplacaments: dict[str, int]
    #: peça → nombre de punts del contorn de tall que porten regla.
    punts_amb_regla: dict[str, int]
    #: peça → nombre de regles DISTINTES que el contorn de tall invoca.
    regles_distintes: dict[str, int]
    #: la regla nul·la: la que porten les peces que no gradúen.
    regla_nulla: int
    #: regles del RUL que cap punt no invoca.
    no_invocades: tuple[int, ...]

    def rul(self, dxf_rule: int) -> int:
        """El número de RUL que governa un `# n` del DXF."""
        if dxf_rule == self.regla_nulla:
            return self.regla_nulla
        return self.dxf_a_rul[dxf_rule]


def carrega_rul(path: Path = RUL_837) -> GradeTable:
    return RULReader().read(path.read_bytes())


def carrega_mestre(path: Path = MESTRE_837) -> PatternDocument:
    return AAMAReader().read(path.read_bytes())


# ── A · LES VERIFICACIONS DEL RUL ────────────────────────────────────────────────
# Cap és decorativa: totes cauen si es toca el que miren. La A3 i la A4 són les úniques
# que miren VALORS —les altres miren estructura— i són les que el brief demanava
# re-confirmar contra el que es va mesurar en local.

def verifica_rul(table: GradeTable) -> list[Verificacio]:
    nums = sorted(table.regles)
    contigu = nums == list(range(nums[0], nums[-1] + 1))
    no_base = [t for t in table.talles if t != table.talla_base]

    v = [Verificacio(
        'A1', 'Les regles són contínues',
        contigu and len(nums) == 90,
        f'{len(nums)} regles, {nums[0]}–{nums[-1]}, sense forats: {contigu}.',
    )]

    dolentes = [n for n in nums if table.regles[n].deltes.get(table.talla_base) != (0.0, 0.0)]
    v.append(Verificacio(
        'A2', 'La talla base no es mou',
        not dolentes,
        f"S és la base i el seu delta és (0,0) a les {len(nums)} regles."
        if not dolentes else f'Regles amb S ≠ 0: {dolentes[:8]}.',
    ))

    # A3 · les cotes per talla. El brief en donava quatre —10,6 · 15,2 · 30,1 · 45,4— i
    # les donava a un decimal, que és tota la precisió que declaren. La comprovació es fa
    # a ESA precisió: exigir-ne més convertiria l'arrodoniment del brief en un defecte del
    # fitxer (10,61 «superaria» 10,6 i la verificació cauria sense que res fos fals).
    cotes = {'XS': 10.6, 'M': 15.2, 'L': 30.1, 'XL': 45.4}
    fora, mesura = {}, {}
    for t in no_base:
        m = max(abs(table.regles[n].deltes[t][1]) for n in nums)
        mesura[t] = m
        if t in cotes and round(m, 1) != cotes[t]:
            fora[t] = (m, cotes[t])
    v.append(Verificacio(
        'A3', 'El moviment màxim en Y per talla és el que el brief va mesurar',
        not fora,
        '  '.join(f'{t}: max|dy| = {mesura[t]:.2f} (brief {cotes.get(t, float("nan")):.1f})'
                  for t in no_base)
        + ('' if not fora else f'  FORA: {fora}'),
    ))

    # A4 · la progressió a les 12 regles de més moviment. 🚨 Es mesura per EIX, i és per
    # això que cau: el brief n'esperava una, −0,67/1/2/3, i n'hi ha DUES que no s'assemblen.
    mov = sorted(nums, key=lambda n: max(
        math.hypot(*table.regles[n].deltes[t]) for t in no_base), reverse=True)[:12]
    files = []
    for n in mov:
        d = table.regles[n].deltes
        files.append((n, _ratio(d, no_base, 0), _ratio(d, no_base, 1)))
    unic = len({f[2] for f in files}) == 1 and len({f[1] for f in files}) == 1
    v.append(Verificacio(
        'A4', 'Les 12 regles de més moviment comparteixen una sola progressió',
        unic,
        'Les progressions de X i de Y NO són la mateixa i no n\'hi ha una de sola: '
        f'X → {sorted({f[1] for f in files})}, Y → {sorted({f[2] for f in files})}. '
        'Regles mesurades: ' + ', '.join(str(f[0]) for f in files) + '.',
    ))

    v.append(Verificacio(
        'A5', 'El reader no denuncia res del fitxer',
        not table.issues,
        f'issues = {[i.code for i in table.issues]}; unitats {table.unitats} '
        f'({table.unitats_factor_mm} mm/unitat); base {table.talla_base!r}; '
        f'talles {list(table.talles)}.',
    ))
    return v


def _ratio(deltes: dict, no_base: list[str], eix: int) -> tuple:
    """La progressió d'un eix, normalitzada al pas de la M. None si l'eix no es mou."""
    m = deltes['M'][eix]
    if abs(m) < 1.0:                     # sota el mil·límetre no és una progressió, és soroll
        return ()
    return tuple(round(deltes[t][eix] / m, 2) for t in no_base)


# ── B · EL MAPA ──────────────────────────────────────────────────────────────────

def _regles_de_tall(doc: PatternDocument) -> dict[str, list[int]]:
    """Peça → els números de regla que el seu contorn de TALL i els seus piquets invoquen.

    Els piquets hi entren perquè **numeren dins del mateix bloc** que el contorn (al davant,
    68 · 74 · 77 · 88 · 91 · 97 són els sis forats de 65–98), i sense ells el bloc no és
    contigu i la derivació del desplaçament no es pot fer.
    """
    out: dict[str, list[int]] = {}
    for p in doc.pieces:
        usades = set()
        for b in p.boundaries:
            if b.layer != CAPA_TALL:
                continue
            usades |= {pt.grade_rule for pt in b.points if pt.grade_rule is not None}
        usades |= {n.grade_rule for n in p.notches if n.grade_rule is not None}
        out[p.metadata.piece_name] = sorted(usades)
    return out


def construeix_mapa(doc: PatternDocument, table: GradeTable) -> Mapa:
    """Deriva la correspondència DXF→RUL dels blocs. Cap número escrit a mà.

    La derivació és: els números de DXF de les peces que gradúen, en ordre ascendent i
    omplint els forats dels piquets, es corresponen un a un —i en el mateix ordre— amb les
    últimes regles del RUL. Que això sigui cert no es decideix aquí: es MESURA a
    `exam_rul.py`, reconstruint les quatre talles i comparant-les amb la niada.
    """
    per_peca = _regles_de_tall(doc)
    nulles = {n for n, r in table.regles.items()
              if all(d == (0.0, 0.0) for d in r.deltes.values())}
    # La regla nul·la és la que comparteixen les peces d'un sol número. Si n'hi hagués més
    # d'una candidata seria una tria i no una regla: es demana i no s'endevina.
    candidates = {u[0] for u in per_peca.values() if len(u) == 1}
    if len(candidates) != 1:
        raise ValueError(f'La regla nul·la no és única: {sorted(candidates)}')
    regla_nulla = candidates.pop()
    if regla_nulla not in nulles:
        raise ValueError(f'La regla {regla_nulla} la porten peces que no gradúen, '
                         f'però els seus deltes no són zero.')

    blocs = {nm: (u[0], u[-1]) for nm, u in per_peca.items() if len(u) > 1}
    for nm, (lo, hi) in blocs.items():
        if sorted(per_peca[nm]) != list(range(lo, hi + 1)):
            raise ValueError(f'El bloc de {nm} ({lo}–{hi}) té forats: '
                             f'{sorted(set(range(lo, hi + 1)) - set(per_peca[nm]))}')

    graduats = sorted(n for lo, hi in blocs.values() for n in range(lo, hi + 1))
    cua = sorted(table.regles)[-len(graduats):]
    if len(cua) != len(graduats):
        raise ValueError(f'El RUL té {len(table.regles)} regles i la geometria en demana '
                         f'{len(graduats)}: no hi caben.')
    dxf_a_rul = dict(zip(graduats, cua))

    desplacaments = {nm: lo - dxf_a_rul[lo] for nm, (lo, _hi) in blocs.items()}
    for nm, (lo, hi) in blocs.items():
        d = desplacaments[nm]
        if any(dxf_a_rul[n] != n - d for n in range(lo, hi + 1)):
            raise ValueError(f'El bloc de {nm} no es desplaça de manera constant.')

    punts, distintes = {}, {}
    for p in doc.pieces:
        nm = p.metadata.piece_name
        rs = [pt.grade_rule for b in p.boundaries if b.layer == CAPA_TALL
              for pt in b.points if pt.grade_rule is not None]
        punts[nm] = len(rs)
        distintes[nm] = len(set(rs))

    invocades = set(dxf_a_rul.values()) | {regla_nulla}
    no_invocades = tuple(sorted(set(table.regles) - invocades))
    return Mapa(dxf_a_rul=dxf_a_rul, blocs=blocs, desplacaments=desplacaments,
                punts_amb_regla=punts, regles_distintes=distintes,
                regla_nulla=regla_nulla, no_invocades=no_invocades)


#: B2 · El contrast de sanitat que el brief demanava: els recomptes per peça han de ser
#: els que F6.2 va mesurar pel seu compte, llegint els mateixos TEXT amb un altre codi.
RECOMPTES_F62 = {'837.DELANTERO': 28, '837.ESPALDA': 24, '837.MANGA': 9,
                 '837.CUELLO': 1, '837.TAPETA': 1}


def verifica_mapa(doc: PatternDocument, table: GradeTable, mapa: Mapa) -> list[Verificacio]:
    esperat = {nm: (mapa.regles_distintes[nm] if nm in mapa.blocs else 1)
               for nm in mapa.regles_distintes}
    ok = esperat == RECOMPTES_F62
    v = [Verificacio(
        'B2', 'Els recomptes per peça són els que F6.2 va mesurar',
        ok,
        '  '.join(f'{nm.replace("837.", "")}: {esperat[nm]}' for nm in sorted(esperat))
        + (f'   (F6.2 deia {RECOMPTES_F62})' if not ok else ''),
    )]
    v.append(Verificacio(
        'B3', 'Cada punt de gir del contorn de tall porta UNA regla, i cap la comparteix',
        all(mapa.punts_amb_regla[nm] == mapa.regles_distintes[nm] for nm in mapa.blocs),
        '  '.join(f'{nm.replace("837.", "")}: {mapa.punts_amb_regla[nm]} punts / '
                  f'{mapa.regles_distintes[nm]} regles' for nm in sorted(mapa.blocs))
        + '  → el patró NO declara cap agrupació de punts.',
    ))
    v.append(Verificacio(
        'B4', 'Tota regla que la geometria invoca existeix al RUL',
        all(r in table.regles for r in mapa.dxf_a_rul.values()),
        f'{len(mapa.dxf_a_rul)} regles mapades a {sorted(mapa.dxf_a_rul.values())[0]}–'
        f'{sorted(mapa.dxf_a_rul.values())[-1]}, més la nul·la {mapa.regla_nulla}. '
        f'Desplaçaments: ' + ', '.join(f'{nm.replace("837.", "")} {d:+d}'
                                       for nm, d in sorted(mapa.desplacaments.items())) + '.',
    ))
    v.append(Verificacio(
        'B5', 'El RUL no declara regles que ningú no faci servir',
        not mapa.no_invocades,
        f'{len(mapa.no_invocades)} regles declarades i mai invocades: '
        f'{list(mapa.no_invocades)}. La taula és de l\'ESTIL; el DXF en porta cinc peces.',
    ))
    return v


# ── ELS HORARIS ─────────────────────────────────────────────────────────────────
# El que el RUL diu sobre com es passa d'una talla a l'altra, per EIX i per PEÇA. És la
# llei que F6.1 i F6.2 buscaven a les fosques i no podien deduir de 16 mesures.

@dataclass(frozen=True)
class Horari:
    """La progressió d'un eix d'una peça, normalitzada al pas de la M."""
    peca: str
    eix: str
    coeficients: tuple[float, ...]
    #: Quant deixa el model separable `d_eix(t) = coeficient(t) · u_punt`, en mm.
    residu_rms_mm: float
    residu_max_mm: float


def horaris(table: GradeTable, mapa: Mapa) -> dict[tuple[str, str], Horari]:
    """L'horari de cada (peça, eix), per SVD de rang 1 sobre els deltes de la peça.

    Que sigui rang 1 **per eix** és el descobriment: rang 1 sobre el punt sencer —una
    direcció per punt i una amplitud per talla, que és el model d'F6.2— deixa 3,0 mm de
    residu rms, perquè X i Y no gradúen amb el mateix horari. Separats, cada eix tanca a
    mig mil·límetre.
    """
    no_base = [t for t in table.talles if t != table.talla_base]
    out = {}
    for nm, (lo, hi) in mapa.blocs.items():
        regles = [mapa.dxf_a_rul[n] for n in range(lo, hi + 1)]
        for eix, j in (('x', 0), ('y', 1)):
            d = np.array([[table.regles[r].deltes[t][j] for t in no_base] for r in regles])
            u, s, vt = np.linalg.svd(d, full_matrices=False)
            a, coef = vt[0] * s[0], u[:, 0]
            pas_m = a[no_base.index('M')]
            if abs(pas_m) > 1e-9:
                coef, a = coef * pas_m, a / pas_m
            res = d - np.outer(coef, a)
            out[(nm, eix)] = Horari(
                peca=nm, eix=eix, coeficients=tuple(round(float(x), 4) for x in a),
                residu_rms_mm=float(np.sqrt((res ** 2).mean())),
                residu_max_mm=float(np.abs(res).max()))
    return out
