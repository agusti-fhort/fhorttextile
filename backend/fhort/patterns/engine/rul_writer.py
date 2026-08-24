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

#: La versió del format, tal com la declara el material real (el RUL que el PolyPattern
#: exporta del 837 obre amb aquesta línia exacta). NO és inventar-se res: és dir quin
#: format estem escrivint, i és el que escrivim. Només es fa servir quan el document
#: d'origen no en declara cap de seva —si en declara, mana la seva (reproduir, no millorar).
VERSIO_AAMA = 'ANSI/AAMA-292-B'

#: Idem per a les unitats: els deltes van en mm i el factor els torna a les natives, o
#: sigui que el fitxer és mètric. El material real ho diu així.
UNITATS_PER_DEFECTE = 'METRIC'


class RULWriter:
    """Implementa la meitat `write` del port `GradeCodec`."""

    def write(self, table: GradeTable) -> bytes:
        factor = table.unitats_factor_mm or 1.0
        linies: list[str] = []

        # ── LA CAPÇALERA, SENCERA I EN ORDRE ────────────────────────────────────────
        # L'ordre i la presència de les línies no són cosmètica. El RUL que el PolyPattern
        # exporta del 837 obre amb `version` + `AUTHOR:` + `UNITS:` + `GRADE RULE TABLE:`
        # i després el bloc de talles; el nostre n'emetia només `UNITS:` perquè les altres
        # tres eren condicionals i el patró venia sense RUL d'origen (`grade_table` a NULL),
        # o sigui que no hi havia d'on copiar-les. Ara la versió i les unitats tenen
        # defecte —són propietats del fitxer que ESCRIVIM, no de l'origen— i les altres
        # dues es copien del DXF (v. `grading_projection._capcalera_del_document`).
        linies.append(f'version {table.aama_version or VERSIO_AAMA}')
        if table.autor:
            linies.append(f'AUTHOR: {table.autor}')
        linies.append(f'UNITS: {table.unitats or UNITATS_PER_DEFECTE}')
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
