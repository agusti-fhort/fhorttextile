"""Writer RUL: `GradeTable` → fitxer de regles de grading.

Mirall exacte del `rul_reader`. Reprodueix el format del RUL real d'AMELIA
(PolyPattern 11.0.1):

    version ANSI/AAMA-292-B
    AUTHOR: PolyPattern 11.0.1
    UNITS: METRIC
    GRADE RULE TABLE:AMELIA AZUL prova
    SAMPLE SIZE:M
    NUMBER OF SIZES:5
    SIZE LIST:XS S M L XL
    RULE: DELTA 1  0.00, 0.00  0.00, 0.00  0.00, 0.00  0.00, 0.00  0.00, 0.00
    END

Detall que no és un detall: **el decimal és PUNT i la coma separa dx de dy**. És
l'invers del criteri dels TEXT del DXF germà, on la coma és decimal. El mateix CAD
escriu els dos fitxers amb criteris oposats, i reproduir-ho és el que fa que el fitxer
torni a ser seu.

Els deltes surten en les unitats natives del RUL, desfent el factor que el reader va
aplicar per portar-los a mm.
"""
from __future__ import annotations

from .geometry import GradeTable

#: Separador entre columnes de deltes, i espai final de la línia de regla. Tots dos
#: copiats del fitxer real: amb això, el RUL que escrivim surt **byte a byte** com el
#: que vam llegir. No és estètica — és la prova més dura que hi ha de reproducció.
COL_SEP = ' '
FI_LINIA_REGLA = ' '


class RULWriter:
    """Implementa la meitat `write` del port `GradeCodec`."""

    def write(self, table: GradeTable) -> bytes:
        factor = table.unitats_factor_mm or 1.0
        linies: list[str] = []

        if table.aama_version:
            linies.append(f'version {table.aama_version}')
        if table.autor:
            linies.append(f'AUTHOR: {table.autor}')
        if table.unitats:
            linies.append(f'UNITS: {table.unitats}')
        if table.nom:
            linies.append(f'GRADE RULE TABLE:{table.nom}')
        if table.talla_base:
            linies.append(f'SAMPLE SIZE:{table.talla_base}')
        linies.append(f'NUMBER OF SIZES:{len(table.talles)}')
        linies.append(f'SIZE LIST:{" ".join(table.talles)}')

        for numero in sorted(table.regles):
            regla = table.regles[numero]
            columnes = []
            for talla in table.talles:
                dx, dy = regla.delta(talla)
                # De mm a les unitats del fitxer, i amb PUNT decimal.
                columnes.append(f'{dx / factor:.2f}, {dy / factor:.2f}')
            linies.append(
                f'RULE: DELTA {numero}{COL_SEP}{COL_SEP.join(columnes)}{FI_LINIA_REGLA}'
            )

        linies.append('END')
        return ('\n'.join(linies) + '\n').encode('utf-8')
