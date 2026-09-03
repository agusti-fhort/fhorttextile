"""De la geometria a la proposta: el pont entre la BD i el matcher.

L'`engine.seam_matching` és pur —no sap què és un `PatternSegment` ni una `SewRelation`— i ha
de continuar sent-ho: és l'única manera de poder-lo provar amb números inventats i de poder-lo
canviar sense por. Aquí és on el món real (files, FK, versions de patró) es tradueix a
`Candidat` i on la proposta torna a ser una cosa que la UI pot ensenyar.

**Res del que hi ha aquí escriu.** Llegir la geometria, comptar piquets i proposar parelles és
una operació de només lectura, i el dia que això deixi de ser cert la proposta haurà deixat de
ser una proposta.
"""
from __future__ import annotations

from .adapters import DjangoGeometryStore
from .recognition import seam_expectations as expectations
from .recognition import seam_precedent as precedent
from .engine.seam_matching import (
    Candidat, Descartats, LLARG_MIN_CM, MM_PER_CM, clau_parella, piquets_de_la_vora,
    piquets_del_tram, proposar,
)
from .engine.segments import longitud_tram, longitud_vora
from .engine.sew import solapament_t, validar
from .models import PatternFile, PatternSegment, SewProposalRejection, SewRelation
from .preferences import preferencia_del_tram, rangs_apresos, rol_de_peca

#: Un tram del qual una costura declarada ja reclama més d'aquesta fracció NO es proposa. No és
#: zero perquè dos trams veïns es toquen per un extrem i un solapament de zero coma res no és una
#: col·lisió; no és 1.0 perquè mig tram ja cosit tampoc no es pot tornar a oferir sencer.
SOLAPAMENT_MAX_REL = 0.10


def _pinces_de_vora(model_id: int) -> set[int]:
    """Els ids de les costures que són pinces de vora.

    Els seus costats SÍ que treuen el tram de la llista de candidats —una pinça declarada és una
    decisió presa sobre aquell tros de vora—, però la pinça no «reclama» la vora com ho fa una
    costura: la seva tela es DESCOMPTA (W4b), i és `_costat_net` qui ho sap fer. Aquí només cal
    saber quines ho són.
    """
    from .annotation_views import es_pinca_de_vora
    return {
        rel.id for rel in SewRelation.objects
        .filter(model_id=model_id, tipus=SewRelation.TIPUS_PINCA)
        .prefetch_related('segments_a__piece', 'segments_b__piece')
        if es_pinca_de_vora(rel)
    }


def _trams_ja_declarats(model_id: int, exclou_sew_ids=frozenset()
                        ) -> dict[tuple[int, int], list[tuple[float, float]]]:
    """(peça, vora) → els rangs `t` que les costures i les pinces JA declarades ocupen.

    Tot el que una persona ja ha declarat surt de la subhasta. La proposta és per al que
    QUEDA per decidir: tornar a proposar el que algú ja ha cosit seria proposar-li que ho
    tornés a fer.
    """
    ocupats: dict[tuple[int, int], list[tuple[float, float]]] = {}
    relacions = (SewRelation.objects.filter(model_id=model_id)
                 .exclude(pk__in=exclou_sew_ids)
                 .prefetch_related('segments_a', 'segments_b'))
    for rel in relacions:
        for seg in list(rel.segments_a.all()) + list(rel.segments_b.all()):
            ocupats.setdefault((seg.piece_id, seg.vora), []).append((seg.t_inici, seg.t_fi))
    return ocupats


def _ja_cosit(
    seg: PatternSegment, ocupats: dict[tuple[int, int], list[tuple[float, float]]],
) -> bool:
    """Aquest tram, el reclama ja alguna costura declarada?"""
    rangs = ocupats.get((seg.piece_id, seg.vora), [])
    if not rangs:
        return False
    propi = solapament_t(seg.t_inici, seg.t_fi, seg.t_inici, seg.t_fi)
    if propi <= 0:
        return False
    reclamat = max(
        solapament_t(seg.t_inici, seg.t_fi, ini, fi) for ini, fi in rangs
    )
    return (reclamat / propi) > SOLAPAMENT_MAX_REL


def candidats_del_patro(fp: PatternFile, rols_en_memoria: dict | None = None,
                        exclou_sew_ids=frozenset()
                        ) -> tuple[list[Candidat], Descartats, dict]:
    """Els trams que es podrien cosir, amb els seus piquets. I què s'ha deixat pel camí.

    Els candidats són els trams DERIVATS (gir→gir): la hipòtesi de lectura del CAD. Un tram
    DECLARAT no és candidat de res —ja és una afirmació d'algú— i un tram derivat que una costura
    ja reclama, tampoc.

    Torna també `context`: el mapa de files de `PatternSegment` per id (per no tornar-les a
    llegir) i les vores, que després calen per al veredicte.
    """
    store = DjangoGeometryStore()
    doc = store.load_from(fp)
    # `exclou_sew_ids` NOMÉS el fa servir l'examen leave-one-out: amaga una costura
    # confirmada en LECTURA per veure si el motor la sabria tornar a trobar. No esborra res
    # i no és accessible des de cap porta HTTP.
    ocupats = _trams_ja_declarats(fp.model_id, exclou_sew_ids)
    # El costum del taller per als rols d'aquest patró: una consulta per a tot, no una per
    # candidat. És un senyal de desempat i no pot costar una volta a la BD per tram.
    apresos = rangs_apresos({rol_de_peca(p) for p in fp.pieces.all()})
    # F4.3 · el vocabulari del catàleg per tram. `rols_en_memoria` és per a l'EXAMEN: hi pot
    # passar rols de vora que cap humà ha confirmat encara, i així el mecanisme es mesura
    # sense escriure ni una fila. En producció va buit i mana el que diu la BD.
    rols_en_memoria = rols_en_memoria or {}

    candidats: list[Candidat] = []
    desc = Descartats()
    files: dict[int, PatternSegment] = {}

    for piece_row in fp.pieces.all():
        piece = doc.piece(piece_row.nom_block)
        if piece is None:
            continue

        segments = list(
            piece_row.segments.filter(origen=PatternSegment.ORIGEN_NATURAL)
            .select_related('edge_role'))
        if not segments:
            continue

        # La identitat de la PEÇA només compta si l'ha signat una persona: `rol_origen` és
        # el que separa el que algú ha dit del que va proposar la màquina, i construir el
        # senyal de catàleg sobre una proposta seria fer-lo aprendre del seu propi encert.
        from .recognition.edge_service import confirmed_role_of
        rol_peca = confirmed_role_of(piece_row) or ''

        # Tots els trams derivats d'una peça viuen sobre la MATEIXA vora base (la de cosit si
        # n'hi ha, la de tall si no: `engine.segments.segmentar_peca`). Es llegeix de les files,
        # no es torna a deduir: si un dia la regla canvia, les files ho sabran i una segona
        # deducció aquí diria una altra cosa.
        vora_idx = segments[0].vora
        if vora_idx >= len(piece.boundaries):
            continue
        boundary = piece.boundaries[vora_idx]
        llarg_vora = longitud_vora(boundary)
        if llarg_vora <= 0:
            continue

        piquets_vora = piquets_de_la_vora(
            boundary.points, boundary.closed, piece.notches, llarg_vora)
        confirmats, tallats = apresos.get(rol_de_peca(piece_row), ([], []))

        for seg in segments:
            llarg_mm = longitud_tram(boundary, seg.t_inici, seg.t_fi)
            if llarg_mm / MM_PER_CM < LLARG_MIN_CM:
                desc = _sumar(desc, curts=1)
                continue
            if _ja_cosit(seg, ocupats):
                desc = _sumar(desc, ja_cosits=1)
                continue

            files[seg.id] = seg
            candidats.append(Candidat(
                segment_id=seg.id,
                piece_id=piece_row.id,
                piece_nom=piece_row.nom_block,
                vora=seg.vora,
                t_inici=seg.t_inici,
                t_fi=seg.t_fi,
                longitud_mm=llarg_mm,
                piquets=piquets_del_tram(piquets_vora, seg.t_inici, seg.t_fi),
                preferencia=preferencia_del_tram(
                    seg.t_inici, seg.t_fi, confirmats, tallats),
                piece_role=rol_peca,
                face=piece_row.face or '',
                edge_role=(seg.edge_role.slug if seg.edge_role_id
                           else rols_en_memoria.get(seg.id, '')),
            ))

    return candidats, desc, {'files': files}


def _absents(fp: PatternFile, candidats, expectatives, rols_en_memoria=None) -> list[dict]:
    """A2b · Les expectatives de NUCLI que aquest model no té cosides. El checklist.

    🚨 **Informació, MAI un error.** Un vestit pot no portar una costura que el corpus
    considera de nucli, i dir-li «falta» amb to de defecte ensenyaria el patronista a no
    llegir la llista —el mateix mal que un llindar de proposta massa baix. La frase és
    «el catàleg n'esperaria una», no «te'n falta una».

    Només compta les parelles els DOS costats de les quals existeixen a aquest patró: dir a
    algú que al seu vestit li falta un `crotch_seam` seria soroll disfressat de checklist.
    """
    costats = []
    for c in candidats:
        costat = expectatives.costat_de(c)
        if costat is not None:
            costats.append(costat)
    # També els trams que JA estan cosits: una expectativa coberta no és absent, i els seus
    # trams no són candidats justament perquè ja tenen costura.
    ja = _costats_cosits(fp, rols_en_memoria)
    costats.extend(ja)
    if not costats:
        return []

    cobertes = {frozenset((a.clau(), b.clau()))
                for a, b in _parelles_cosides(fp, rols_en_memoria)}
    fora = []
    for e in expectatives.esperades(costats):
        if frozenset((e.a.clau(), e.b.clau())) in cobertes:
            continue
        fora.append({
            'a': {'piece_role': e.a.piece_role, 'edge_role': e.a.edge_role},
            'b': {'piece_role': e.b.piece_role, 'edge_role': e.b.edge_role},
            'seam_kind': e.seam_kind, 'grau': e.grau, 'ratio': e.ratio,
            'observed_seams': e.observed_seams, 'observed_den': e.observed_den,
            'detall': e.frase(),
        })
    return fora


def _costats_cosits(fp: PatternFile, rols_en_memoria=None) -> list:
    """Els costats de catàleg dels trams que JA tenen costura confirmada en aquest model."""
    return [c for parella in _parelles_cosides(fp, rols_en_memoria) for c in parella]


def _parelles_cosides(fp: PatternFile, rols_en_memoria=None) -> list[tuple]:
    """Les costures CONFIRMADES d'aquest model, en vocabulari de catàleg."""
    from .recognition.seam_precedent import _costat_de

    relacions = list(SewRelation.objects.filter(model_id=fp.model_id)
                     .prefetch_related('segments_a__piece__piece_role',
                                       'segments_b__piece__piece_role'))
    if not relacions:
        return []
    peces = {d.piece_id for r in relacions
             for d in list(r.segments_a.all()) + list(r.segments_b.all())}
    naturals: dict[int, list] = {}
    for seg in PatternSegment.objects.filter(
            piece_id__in=peces, origen=PatternSegment.ORIGEN_NATURAL).select_related('edge_role'):
        naturals.setdefault(seg.piece_id, []).append(seg)

    out = []
    for r in relacions:
        da = list(r.segments_a.all())
        db = list(r.segments_b.all())
        if not da or not db:
            continue
        # 🚨 Els MATEIXOS rols que ha vist el proposador. Amb un diccionari buit aquí, cap
        # costura confirmada resolia el seu vocabulari i el checklist declarava ABSENT tot
        # el que el model ja porta cosit — mesurat: deia que hi faltava la costura lateral
        # d'un vestit que en té dues.
        a = _costat_de(da[0], naturals, rols_en_memoria or {})
        b = _costat_de(db[0], naturals, rols_en_memoria or {})
        if a.edge_role and b.edge_role:
            out.append((a, b))
    return out


def rebuigs_del_model(model_id: int) -> frozenset[tuple[int, int]]:
    """Les parelles que ja s'han rebutjat, en clau canònica."""
    return frozenset(
        clau_parella(a, b) for a, b in
        SewProposalRejection.objects.filter(model_id=model_id)
        .values_list('segment_a_id', 'segment_b_id')
    )


def propostes_del_model(fp: PatternFile, rols_en_memoria: dict | None = None,
                        exclou_sew_ids=frozenset()) -> dict:
    """Les propostes vives d'un patró, amb el seu desglòs i el seu veredicte.

    El **veredicte** és el que `sew.validar` diria si la proposta es confirmés ARA: amb les
    pinces ja declarades descomptades, i amb el tipus i el diferencial que el motor proposa. No
    és una promesa —és una previsió calculada amb el mateix motor que després jutjarà la costura
    de veritat—, i és el que converteix la llista en una cosa que es pot revisar en comptes
    d'acceptar a cegues.
    """
    candidats, desc, ctx = candidats_del_patro(fp, rols_en_memoria, exclou_sew_ids)

    # F4.3 · els dos senyals nous. Es carreguen un cop per patró i viatgen com a DADA PLANA
    # al motor pur: `seam_matching` ha de continuar sense saber què és una BD.
    gti = getattr(getattr(fp, 'model', None), 'garment_type_item_id', None)
    expectatives = expectations.carrega(gti)
    # El model queda FORA del seu propi banc de precedents. Sense això, córrer el proposador
    # sobre el 837 hi trobaria les costures del 837 mateix i informaria de confiança perfecta
    # sobre res — el mateix error que `recognition.service.exclude_self` evita a F4.1.
    precedents = precedent.carrega(exclou_model_id=fp.model_id,
                                   rols_en_memoria=rols_en_memoria)

    propostes, desc = proposar(
        candidats, exclosos=rebuigs_del_model(fp.model_id), descartats=desc,
        expectatives=expectatives, precedents=precedents)

    return {
        'model': fp.model_id,
        'pattern_file': fp.id,
        'candidats': len(candidats),
        # El CHECKLIST del patronista (A2b): expectatives de nucli que aquest model podria
        # tenir i no té cosides. Informació, MAI un error: un vestit pot no portar-les.
        'absents': _absents(fp, candidats, expectatives, rols_en_memoria),
        'senyals_nous': {
            'expectatives_catalog': len(expectatives),
            'precedents_tenant': len(precedents),
        },
        'propostes': [_serialitzar(p, fp.model_id, ctx['files']) for p in propostes],
        # Els descartats no són decoració: diuen si una costura que falta és que el motor no l'ha
        # vista o és que ni tan sols l'ha mirada.
        'descartats': {
            'curts': desc.curts,
            'ja_cosits': desc.ja_cosits,
            'sota_llindar': desc.sota_llindar,
            'en_conflicte': desc.en_conflicte,
            'rebutjades': desc.rebutjades,
        },
        'llarg_min_cm': LLARG_MIN_CM,
    }


def _veredicte(model_id: int, seg_a: PatternSegment, seg_b: PatternSegment,
               tipus: str, diferencial_cm: float) -> dict:
    """Què diria el motor si això es cosís ara mateix. Amb les pinces descomptades."""
    from .annotation_views import _BoundaryCache, _costat_net, _mapa_pinces

    boundaries = _BoundaryCache()
    pinces = _mapa_pinces(model_id)
    brut_a, desc_a = _costat_net([seg_a], boundaries, pinces)
    brut_b, desc_b = _costat_net([seg_b], boundaries, pinces)

    check = validar(
        brut_a, brut_b, tipus=tipus, diferencial_cm=diferencial_cm,
        descomptes_a=desc_a, descomptes_b=desc_b,
    )
    return {
        'casa': check.casa,
        'longitud_a_cm': round(check.longitud_a_cm, 2),
        'longitud_b_cm': round(check.longitud_b_cm, 2),
        'brut_a_cm': round(check.brut_a_cm, 2),
        'brut_b_cm': round(check.brut_b_cm, 2),
        'descomptes_a': [
            {'sew_id': d.sew_id, 'nom': d.nom, 'cm': round(d.cm, 2)} for d in check.descomptes_a],
        'descomptes_b': [
            {'sew_id': d.sew_id, 'nom': d.nom, 'cm': round(d.cm, 2)} for d in check.descomptes_b],
        'diferencia_cm': round(check.diferencia_cm, 2),
        'desviament_cm': round(check.desviament_cm, 2),
        'missatge': check.missatge,
    }


def _costat(c: Candidat) -> dict:
    return {
        'segment_id': c.segment_id,
        'piece_id': c.piece_id,
        'peca': c.piece_nom,
        'vora': c.vora,
        't_inici': c.t_inici,
        't_fi': c.t_fi,
        'longitud_cm': round(c.longitud_cm, 2),
        # Les posicions dels piquets DINS del tram: és el que la UI ha d'ensenyar quan algú
        # pregunti per què el motor creu que aquests dos trams es toquen.
        'piquets': [round(s, 4) for s in c.piquets],
    }


def _serialitzar(p, model_id: int, files: dict[int, PatternSegment]) -> dict:
    return {
        # La clau canònica: és el que el rebuig desa i el que el confirmar rep. La UI no ha
        # d'inventar-se cap identificador — una proposta no és una fila, i no en té.
        'clau': list(clau_parella(p.a.segment_id, p.b.segment_id)),
        'a': _costat(p.a),
        'b': _costat(p.b),
        'tipus': p.tipus,
        'diferencial_cm': p.diferencial_cm,
        'confianca': p.confianca,
        'invertit': p.invertit,
        'senyals': [
            {
                'mena': s.mena,
                'punts': round(s.punts, 3),
                # La frase del servidor va en català pla: NO és una clau i18n. La UI construeix
                # el seu text de `dades` (ca/en/es) i es queda aquesta per al `title`, on hi cap
                # el matís que a la fila no hi cabria.
                'detall': s.detall,
                'dades': s.dades,
            }
            for s in p.senyals
        ],
        'veredicte': _veredicte(
            model_id, files[p.a.segment_id], files[p.b.segment_id],
            p.tipus, p.diferencial_cm),
    }


def _sumar(d: Descartats, **camps) -> Descartats:
    return Descartats(**{**d.__dict__, **{k: getattr(d, k) + v for k, v in camps.items()}})
