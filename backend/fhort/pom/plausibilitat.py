"""Rang FÍSIC d'una mesura de peça — punt únic del backend.

Germana del FIX-4 (`frontend/src/utils/plausibilitatMesura.js`), i deliberadament d'una
altra naturalesa. El FIX-4 PREGUNTA («això sembla un increment, no una mesura: desar
igualment?») perquè els seus llindars són relatius a la base i hi ha peces petites
legítimes i deltes grans legítims: una guarda que bloqueja el legítim només ensenya a
esquivar-la.

Això d'aquí BLOQUEJA, perquè el que mira no és relatiu ni opinable: **cap peça de roba fa
més de 400 cm, i cap mesura és zero o negativa.** El 22224,7 que va entrar al POP (1206) el
30/07 no és una mesura discutible — és un teclat. Passada aquesta porta, la corba sencera
en queda enverinada i el rastre de com hi va entrar ja s'ha perdut.

LLEI (Agus, 30/07): **MAI cap altra restricció. Dins del rang, l'usuari mana.** Aquesta
funció no opina sobre si una mesura és plausible per a la seva peça — d'això ja se n'ocupa
el FIX-4 preguntant, que és com s'ha de tractar el que és opinable.
"""
from fhort.pom.grading_utils import normalitza_cm

#: Sostre físic. Una peça de roba mesurada en cm no hi arriba ni estesa; per sobre, el
#: número no descriu una peça.
MESURA_MAX_CM = 400.0

#: Codi de rebuig (422), perquè el frontend hi pugui penjar el seu missatge si mai el vol.
CODI_MESURA_FORA_RANG = 'MESURA_FORA_DE_RANG'


def mesura_fora_de_rang(valor):
    """Missatge de rebuig si `valor` no pot ser una mesura de peça; `None` si pot.

    Un valor no numèric retorna `None`: no és feina d'aquesta funció: el guard de TIPUS ja
    viu a cada cridador i té el seu propi missatge (400, «ha de ser numèric»).
    """
    v = normalitza_cm(valor)
    if v is None:
        return None
    if v <= 0:
        return (
            f"{v:g} cm no és una mesura. Si aquesta mesura no aplica a aquest model, "
            f"deixa-la buida o desactiva-la; no la posis a zero ni en negatiu."
        )
    if v > MESURA_MAX_CM:
        return (
            f"{v:g} cm no és una mesura de peça: el màxim físic és {MESURA_MAX_CM:g} cm. "
            f"Revisa el número (sembla un error de teclat)."
        )
    return None
