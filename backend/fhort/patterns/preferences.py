"""L'aprenentatge barat: com aquest taller talla les costures d'un rol de peça.

**Aprèn del «sí» humà, no del seu propi encert.** El motor llegeix la vora i proposa; una
persona confirma, corregeix o calla. Només el que la persona fa es desa. Un motor que
aprengués de les seves pròpies coincidències es donaria la raó sol —cada volta amb més
confiança i el mateix error a dins—, que és exactament el que els rebuigs d'A1/A2 eviten
desant el judici i no el veredicte.

**Mai escriu sol i mai mana.** El que s'acumula aquí és un senyal ADDICIONAL: desempata
propostes que la geometria ja avala, i no en pot habilitar cap (v. `_te_evidencia_geometrica`
a `engine/seam_matching`, la llei de W4: la geometria mana, el nom acompanya). Una preferència
no pot fer néixer una costura que els piquets i les longituds no sostenen.

**No és herència estructural.** Això és una preferència local d'un tenant sobre un nom de
peça. Una base per família que tot patró d'aquella família hereta és una altra cosa, demana
el criteri d'un patronista i viu a un altre lloc (bases GTI/W6).
"""
from __future__ import annotations

from django.db import transaction
from django.db.models import F

from .engine.sew import solapament_t
from .models import PatternPiece, PatternSegment, SegmentPreference

#: Quant es poden assemblar dos trams i seguir sent «el mateix tram», en fracció de la vora.
#: La comparació ha de ser per solapament i no per igualtat: el mateix tram, redibuixat en una
#: versió nova del patró, no dona el mateix float mai.
SOLAPAMENT_MIN = 0.80


def rol_de_peca(piece: PatternPiece | str) -> str:
    """El rol sota el qual s'aprèn: el nom de la peça, normalitzat.

    Al material real el `rol` del CAD no és cap rol canònic —`aama_reader` fa
    `rol = piece_name or block.name`—, així que l'AMELIA dona 'FRONT' i el Tate 'TATE_FRONT',
    'TATE_FRONT_FACING', 'TATE_FRONT_YOKE'. Es normalitza i prou: reduir-los a un FRONT
    canònic per subcadena col·lapsaria tres peces diferents en una i faria viatjar el que
    s'aprèn del davanter cap a la seva vista i el seu canesú.
    """
    nom = piece if isinstance(piece, str) else (piece.rol or piece.nom_block)
    return (nom or '').strip().upper()


def classifica_accio(t_inici: float, t_fi: float, naturals) -> tuple[str, object | None]:
    """Què ha fet la persona amb la lectura del motor, comparant el seu tram amb els naturals.

    Es busca el natural que MÉS es solapa amb el que s'ha declarat i es mira si el que hi ha
    és el mateix tram (confirmat), un de més llarg (allargat) o un de més curt (tallat). Si no
    hi ha cap natural que s'hi assembli prou, no s'ha corregit res del que el motor deia: és
    un tram nou, i d'un tram nou no se n'aprèn cap preferència sobre la lectura.
    """
    propi = solapament_t(t_inici, t_fi, t_inici, t_fi)
    if propi <= 0:
        return '', None

    millor, millor_sol = None, 0.0
    for nat in naturals:
        sol = solapament_t(t_inici, t_fi, nat.t_inici, nat.t_fi)
        if sol > millor_sol:
            millor, millor_sol = nat, sol

    if millor is None or (millor_sol / propi) < SOLAPAMENT_MIN:
        return '', None

    seu = solapament_t(millor.t_inici, millor.t_fi, millor.t_inici, millor.t_fi)
    # Les tres respostes surten de comparar el que s'ha declarat amb el que el motor llegia.
    # L'epsilon és de coma flotant, no de criteri: 1e-6 de la vora són micres.
    if abs(propi - seu) <= 1e-6:
        return SegmentPreference.ACCIO_CONFIRMAT, millor
    if propi > seu:
        return SegmentPreference.ACCIO_ALLARGAT, millor
    return SegmentPreference.ACCIO_TALLAT, millor


@transaction.atomic
def registra(segment: PatternSegment, usuari=None) -> SegmentPreference | None:
    """Desa el que una persona acaba de decidir sobre un tram. Idempotent.

    Re-confirmar el mateix tram no duplica la fila: la REFORÇA (`vegades`). Un judici repetit
    deu cops no val el mateix que un de vist una vegada, i desar-lo deu cops en files
    separades seria tenir el mateix fet escrit deu llocs.

    Torna `None` quan no hi ha res a aprendre —un tram que no correspon a cap lectura del
    motor—, i **no toca res més**: aquesta funció acumula senyal, no canvia cap comportament.
    """
    if segment.origen != PatternSegment.ORIGEN_DECLARAT:
        # Només s'aprèn del que una persona ha afirmat. Un derivat no l'ha decidit ningú.
        return None

    naturals = list(
        segment.piece.segments
        .filter(origen=PatternSegment.ORIGEN_NATURAL, vora=segment.vora)
    )
    accio, _ = classifica_accio(segment.t_inici, segment.t_fi, naturals)
    if not accio:
        return None

    pref, creada = SegmentPreference.objects.get_or_create(
        rol=rol_de_peca(segment.piece),
        accio=accio,
        t_inici=segment.t_inici,
        t_fi=segment.t_fi,
        defaults={
            'apres_de': usuari if getattr(usuari, 'pk', None) else None,
            'apres_a': segment.piece.pattern_file,
        },
    )
    if not creada:
        SegmentPreference.objects.filter(pk=pref.pk).update(vegades=F('vegades') + 1)
        pref.refresh_from_db()
    return pref


def preferencia_del_tram(t_inici: float, t_fi: float, preferides, tallades) -> str:
    """Què n'ha après el taller, d'un tram com aquest: `''`, `'confirmat'` o `'tallat'`.

    Una correcció explícita mana sobre una confirmació: si algú va ESCURÇAR un tram en aquest
    rol, tornar a proposar el llarg és tornar a proposar el que ja li han corregit.
    """
    propi = solapament_t(t_inici, t_fi, t_inici, t_fi)
    if propi <= 0:
        return ''

    def _hi_cau(rangs) -> bool:
        return any(
            (solapament_t(t_inici, t_fi, a, b) / propi) >= SOLAPAMENT_MIN for a, b in rangs
        )

    if _hi_cau(tallades):
        return SegmentPreference.ACCIO_TALLAT
    if _hi_cau(preferides):
        return SegmentPreference.ACCIO_CONFIRMAT
    return ''


def rangs_apresos(rols: set[str]) -> dict[str, tuple[list, list]]:
    """Per rol: els rangs CONFIRMATS i els TALLATS. Una consulta per a tot el patró.

    Els allargats no hi són a posta: dir «aquí el tram havia de ser més llarg» no diu quin
    tram nou s'ha de proposar, i fer-ne un senyal seria inventar-se què volia dir la persona.
    S'acumulen igualment (són auditables i valen per a W6), però encara no mouen res.
    """
    out: dict[str, tuple[list, list]] = {r: ([], []) for r in rols}
    if not rols:
        return out
    for p in SegmentPreference.objects.filter(
        rol__in=rols,
        accio__in=[SegmentPreference.ACCIO_CONFIRMAT, SegmentPreference.ACCIO_TALLAT],
    ):
        conf, tall = out.setdefault(p.rol, ([], []))
        (tall if p.accio == SegmentPreference.ACCIO_TALLAT else conf).append((p.t_inici, p.t_fi))
    return out
