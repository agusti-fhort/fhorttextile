"""Reader RUL (taula de regles de grading) → `GradeTable`.

El RUL és **tabular**: es llegeix com una taula, no s'interpreta com geometria. Format
verificat contra el fitxer real d'AMELIA (PolyPattern 11.0.1):

    version ANSI/AAMA-292-B
    AUTHOR: PolyPattern 11.0.1
    UNITS: METRIC
    GRADE RULE TABLE:AMELIA AZUL prova
    SAMPLE SIZE:M
    NUMBER OF SIZES:5
    SIZE LIST:XS S M L XL
    RULE: DELTA 1  0.00, 0.00  0.00, 0.00  0.00, 0.00  0.00, 0.00  0.00, 0.00
    END

Dues coses que enganyen:

  · **El decimal és PUNT i la coma separa dx de dy.** És al revés que als TEXT del DXF
    germà, on la coma és decimal (`Quantity: 1,0`). Mateix CAD, mateixa exportació,
    criteris oposats segons el fitxer: per això l'empremta guarda el separador per camp.
  · **Els deltes d'AMELIA són tots zero.** No fa el fitxer inútil: el que el motor ha
    de saber llegir és l'ESTRUCTURA (quantes talles, en quin ordre, quina és la base,
    quines regles hi ha). Els valors arribaran amb un RUL poblat de debò.

Les regles es lliguen a la geometria pel número: `RULE: DELTA 1` ↔ el TEXT '# 1' que
al DXF seu damunt de cada punt.
"""
from __future__ import annotations

import re
from typing import Optional

from .errors import ParseIssue, PatternParseError
from .geometry import GradeRuleData, GradeTable, PatternDocument

#: UNITS del RUL → mm. El RUL declara el sistema, no l'escala; 'METRIC' s'assumeix mm
#: (el mateix que el DXF germà). Mentre els deltes siguin zero, la suposició no és
#: verificable — i per això consta a `GradeTable.unitats_factor_mm`.
RUL_UNITS_TO_MM: dict[str, float] = {
    'METRIC': 1.0,
    'IMPERIAL': 25.4,
}

_RE_RULE = re.compile(r'^RULE:\s*DELTA\s+(\d+)\s*(.*)$', re.IGNORECASE)
_RE_NUM = re.compile(r'[-+]?\d*\.\d+|[-+]?\d+')


class RULReader:
    """Implementa la meitat `read` del port `GradeCodec` (el `write` arriba a S2)."""

    def read(self, data: bytes) -> GradeTable:
        if not data:
            raise PatternParseError(
                'El RUL és buit.', [ParseIssue('empty_file', 'Zero bytes.')]
            )

        text = data.decode('utf-8', errors='replace')
        linies = [l.strip() for l in text.splitlines() if l.strip()]
        if not linies:
            raise PatternParseError(
                'El RUL no té contingut.', [ParseIssue('empty_file', 'Cap línia.')]
            )

        capsalera: dict[str, str] = {}
        aama_version = ''
        regles: dict[int, GradeRuleData] = {}
        issues: list[ParseIssue] = []

        # Primera passada: capçalera (cal saber les talles abans de repartir els deltes).
        for linia in linies:
            if linia.upper() == 'END':
                break
            if linia.lower().startswith('version'):
                aama_version = linia.split(None, 1)[1].strip() if ' ' in linia else ''
                continue
            if _RE_RULE.match(linia):
                continue
            if ':' in linia:
                clau, _, valor = linia.partition(':')
                capsalera[clau.strip().upper()] = valor.strip()

        talles = tuple(capsalera.get('SIZE LIST', '').split())
        talla_base = capsalera.get('SAMPLE SIZE', '')
        unitats = capsalera.get('UNITS', '').upper()
        factor = RUL_UNITS_TO_MM.get(unitats, 1.0)

        if not talles:
            raise PatternParseError(
                'El RUL no declara cap talla (SIZE LIST).',
                [ParseIssue('no_sizes', 'Sense SIZE LIST no es poden repartir els deltes.')],
            )

        declarat = _to_int(capsalera.get('NUMBER OF SIZES', ''))
        if declarat is not None and declarat != len(talles):
            issues.append(ParseIssue(
                'size_count_mismatch',
                f'NUMBER OF SIZES diu {declarat} però SIZE LIST en porta {len(talles)}.',
                detall={'declarat': declarat, 'reals': len(talles)},
            ))

        if talla_base and talla_base not in talles:
            issues.append(ParseIssue(
                'base_size_not_in_list',
                f"La talla base '{talla_base}' no és a la llista de talles {list(talles)}.",
                detall={'talla_base': talla_base, 'talles': list(talles)},
            ))

        # Segona passada: les regles.
        for linia in linies:
            m = _RE_RULE.match(linia)
            if not m:
                continue
            numero = int(m.group(1))
            valors = [float(v) for v in _RE_NUM.findall(m.group(2))]

            if len(valors) % 2 != 0:
                issues.append(ParseIssue(
                    'odd_delta_count',
                    f'La regla {numero} té {len(valors)} valors: no formen parells (dx, dy).',
                    detall={'regla': numero},
                ))
                valors = valors[:-1]

            parells = [
                (valors[i] * factor, valors[i + 1] * factor)
                for i in range(0, len(valors), 2)
            ]
            if len(parells) != len(talles):
                issues.append(ParseIssue(
                    'delta_count_mismatch',
                    f'La regla {numero} porta {len(parells)} parells de deltes per a '
                    f'{len(talles)} talles.',
                    detall={'regla': numero, 'parells': len(parells), 'talles': len(talles)},
                ))

            deltes = {talla: parells[i] for i, talla in enumerate(talles) if i < len(parells)}
            regles[numero] = GradeRuleData(numero=numero, deltes=deltes)

        if not regles:
            raise PatternParseError(
                'El RUL no conté cap regla (RULE: DELTA n).',
                [ParseIssue('no_rules', 'Una taula de grading sense regles no serveix de res.')]
                + issues,
            )

        return GradeTable(
            nom=capsalera.get('GRADE RULE TABLE', ''),
            talles=talles,
            talla_base=talla_base,
            regles=regles,
            unitats=unitats,
            unitats_factor_mm=factor,
            aama_version=aama_version,
            autor=capsalera.get('AUTHOR', ''),
            issues=tuple(issues),
        )


def coherencia_dxf_rul(doc: PatternDocument, table: GradeTable) -> list[ParseIssue]:
    """Creua el DXF amb el seu RUL germà i denuncia el que no lliga.

    Els dos fitxers viatgen junts però ningú no garanteix que ho siguin de debò: poden
    ser de models diferents, o d'exportacions distintes del mateix model. Tres controls,
    tots amb evidència al material real:

      · la talla de les peces (`Size: M`) ha de ser la talla base del RUL (`SAMPLE SIZE:M`);
      · tota regla que la geometria invoca ('# 1') ha d'existir a la taula;
      · si el RUL declara una regla que ningú no fa servir, es diu (no és un error).
    """
    issues: list[ParseIssue] = []

    talles_peces = {p.metadata.size for p in doc.pieces if p.metadata.size}
    if talles_peces and table.talla_base:
        if talles_peces != {table.talla_base}:
            issues.append(ParseIssue(
                'size_mismatch',
                f"Les peces del DXF són de la talla {sorted(talles_peces)} però el RUL "
                f"diu que la base és '{table.talla_base}'.",
                detall={'dxf': sorted(talles_peces), 'rul': table.talla_base},
            ))

    usades = {
        pt.grade_rule
        for p in doc.pieces
        for b in p.boundaries
        for pt in b.points
        if pt.grade_rule is not None
    } | {n.grade_rule for p in doc.pieces for n in p.notches if n.grade_rule is not None}

    for numero in sorted(usades - set(table.regles)):
        issues.append(ParseIssue(
            'rule_not_in_table',
            f'La geometria fa servir la regla {numero}, que no és al RUL.',
            detall={'regla': numero},
        ))

    for numero in sorted(set(table.regles) - usades):
        issues.append(ParseIssue(
            'rule_unused',
            f'El RUL declara la regla {numero} i cap punt no la fa servir.',
            detall={'regla': numero},
        ))

    return issues


def _to_int(valor: str) -> Optional[int]:
    try:
        return int(valor.strip())
    except (ValueError, AttributeError):
        return None
