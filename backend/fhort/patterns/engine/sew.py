"""Validació de costures: aquests dos costats es poden cosir?

La regla sembla òbvia —dues vores que es cusen han de fer el mateix— i és falsa. El
diferencial de longitud **vol dir coses oposades segons el tipus de costura** (V1 §5.3.3):

  · **Casat**: els dos costats han de fer el mateix. Qualsevol diferència és un ERROR del
    patró, i com més gran, pitjor. Aquí el diferencial esperat és zero i punt.
  · **Frunzit**: el costat llarg SOBRA a posta. Aquesta tela de més és la que s'arruga
    contra el costat curt, i el diferencial és **la instrucció de muntatge**: digues-li a
    la cosidora quants centímetres ha d'arronsar.
  · **Pinça**: igual, però la tela sobrant es plega i es cus en comptes d'arronsar-se.

Per tant, un mateix desviament de 3 cm pot ser un patró trencat o una peça ben dissenyada,
i el motor no pot decidir-ho pel seu compte: ho decideix el TIPUS que el patronista ha
declarat. El que sí que pot fer —i fa— és dir si la realitat encaixa amb el que s'ha
declarat.

**Cobertura** (Taller de patró, W1). Validar cada costura pel seu compte no n'hi ha prou:
dues costures poden ser correctes cadascuna i, alhora, reclamar el mateix tros de vora, o
sumar més tela de la que la peça té. Això no ho veu ningú mirant una costura sola —cal
mirar la VORA sencera— i és exactament el que passa quan els trams es declaren a mà. Per
això `validar_cobertura` mira, per vora, tot el que s'hi cus.

**La pinça (Taller de patró, W4b).** Una vora amb una pinça declarada MENTEIX sobre la seva
pròpia longitud, i menteix a posta. Els dos costats de la pinça es cusen l'un contra l'altre:
quan la pinça es tanca, els dos punts de la vora que la limiten passen a ser el mateix punt i
aquella tela desapareix de la costura. La vora fa 32.1 cm de contorn i n'aporta 29.8 a la
costura, i les dues xifres són certes alhora.

Un motor que no ho sabés diria que la costura no casa per 2.3 cm i el patró estaria bé; i és
el pitjor error que pot cometre un validador, perquè el patronista aprèn que el vermell no
vol dir res. Per això, quan un tram d'una costura **conté** (per rang `t`) els costats d'una
pinça declarada de la mateixa vora, es compara la longitud **NETA** —i es diu l'aritmètica
sencera, no el resultat: `32.1 − 2.3 (Pinça 1) = 29.8`. Una xifra que surt d'un descompte
s'ha de poder auditar, o és màgia.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

MM_PER_CM = 10.0

#: Marge per sota del qual dues longituds es consideren iguals. Un patró real no casa mai
#: a la mil·lèsima: 1 mm és el que un CAD i una taula de tall donen per bo.
TOLERANCIA_CM = 0.1

#: Marge del CONTENIMENT paramètric. No és la tolerància de longitud: és el gruix del
#: "dins" quan es compara un rang `t` amb un altre. Un costat de pinça declarat sobre els
#: mateixos vèrtexs que el tram que el conté hi cau just al límit, i una comparació estricta
#: el deixaria fora per un error de coma flotant de la quinzena xifra.
EPS_T = 1e-9


@dataclass(frozen=True)
class CostatPinca:
    """Un costat d'una pinça declarada, situat sobre la vora on viu.

    És el que el motor necessita saber d'una pinça per descomptar-la, i res més: on és
    (rang `t`), quant fa, i de quina pinça és. `nom` és el de la PINÇA, no el del costat:
    és el que la UI ha de dir quan expliqui el descompte ("− 2.3 (Pinça 1)").
    """
    sew_id: int
    segment_id: int
    nom: str
    t_inici: float
    t_fi: float
    longitud_cm: float


@dataclass(frozen=True)
class Descompte:
    """La tela que una pinça treu d'un costat de costura.

    Va amb NOM perquè el descompte s'ha de poder llegir: "menys 2.3 cm" no diu res, i
    "menys 2.3 cm de la Pinça 1" és una frase que el patronista pot anar a comprovar.
    """
    sew_id: int
    nom: str
    cm: float


@dataclass(frozen=True)
class SewCheck:
    """El veredicte d'una costura."""
    casa: bool
    #: La longitud que ENTRA a la costura: el contorn menys les pinces que s'hi tanquen.
    #: És la que es compara, perquè és la que es cus.
    longitud_a_cm: float
    longitud_b_cm: float
    #: Diferència REAL entre els dos costats (A − B). Signe inclòs: diu quin costat sobra.
    diferencia_cm: float
    #: Diferència que el patronista havia declarat.
    diferencial_declarat_cm: float
    #: El que separa la realitat del que s'esperava. Això és el que s'ha de mirar.
    desviament_cm: float
    tipus: str
    missatge: str
    #: El contorn, ABANS de descomptar cap pinça. Sense pinces és igual que la longitud.
    brut_a_cm: float = 0.0
    brut_b_cm: float = 0.0
    #: Les pinces que cada costat es menja. Buit = la longitud és el contorn i punt.
    descomptes_a: tuple[Descompte, ...] = field(default_factory=tuple)
    descomptes_b: tuple[Descompte, ...] = field(default_factory=tuple)


def _text_aritmetica(brut: float, descomptes: Sequence[Descompte], net: float) -> str:
    """`32.1 − 2.3 (Pinça 1) = 29.8`. L'operació sencera, no el resultat."""
    if not descomptes:
        return f'{net:.1f}'
    restes = ' '.join(f'− {d.cm:.1f} ({d.nom})' for d in descomptes)
    return f'{brut:.1f} {restes} = {net:.1f}'


def validar(
    longitud_a_mm: float,
    longitud_b_mm: float,
    tipus: str = 'casat',
    diferencial_cm: float = 0.0,
    tolerancia_cm: float = TOLERANCIA_CM,
    descomptes_a: Sequence[Descompte] = (),
    descomptes_b: Sequence[Descompte] = (),
) -> SewCheck:
    """Compara els dos costats amb el que el TIPUS de costura promet.

    Les longituds que arriben són el CONTORN (brut). Si un costat conté pinces declarades,
    la tela que la pinça es menja no arriba mai a la costura, i el que es compara és el NET.
    Qui calcula quines pinces hi cauen és `descomptar_pinces`; aquí només es resta i es diu.
    """
    descomptes_a = tuple(descomptes_a)
    descomptes_b = tuple(descomptes_b)
    brut_a = longitud_a_mm / MM_PER_CM
    brut_b = longitud_b_mm / MM_PER_CM
    a = brut_a - sum(d.cm for d in descomptes_a)
    b = brut_b - sum(d.cm for d in descomptes_b)
    diferencia = a - b

    def _check(casa: bool, desviament: float, missatge: str) -> SewCheck:
        """Tots els retorns porten el mateix equipatge: l'aritmètica del descompte."""
        return SewCheck(
            casa=casa, longitud_a_cm=a, longitud_b_cm=b,
            diferencia_cm=diferencia, diferencial_declarat_cm=(
                0.0 if tipus == 'casat' else diferencial_cm),
            desviament_cm=desviament, tipus=tipus, missatge=missatge,
            brut_a_cm=brut_a, brut_b_cm=brut_b,
            descomptes_a=descomptes_a, descomptes_b=descomptes_b,
        )

    #: La frase del descompte, si n'hi ha. S'enganxa al missatge perquè qui llegeixi
    #: "casa: els dos costats fan 29.8" i sàpiga que la vora en fa 32.1 no pensi que el
    #: motor s'ha begut l'enteniment.
    detall = ''
    if descomptes_a or descomptes_b:
        detall = (
            f' (A: {_text_aritmetica(brut_a, descomptes_a, a)}'
            f' · B: {_text_aritmetica(brut_b, descomptes_b, b)})'
        )

    if tipus == 'casat':
        # En un casat, el diferencial declarat ha de ser zero: si algú n'hi posa un, ha
        # triat malament el tipus, i val més dir-l'hi que no pas fer-li cas.
        if abs(diferencial_cm) > tolerancia_cm:
            return _check(
                False, abs(diferencial_cm),
                f'Una costura CASADA no pot tenir un diferencial declarat de '
                f'{diferencial_cm:.1f} cm: si un costat ha de sobrar, és un frunzit o '
                f'una pinça, no un casat.',
            )
        desviament = abs(diferencia)
        casa = desviament <= tolerancia_cm
        return _check(
            casa, desviament,
            (f'Casa: els dos costats fan {a:.1f} cm.{detall}' if casa else
             f'NO casa: el costat A fa {a:.1f} cm i el B {b:.1f} cm '
             f'({desviament:.1f} cm de diferència).{detall}'),
        )

    # Frunzit i pinça: el diferencial és una PROMESA, i es comprova.
    desviament = abs(abs(diferencia) - abs(diferencial_cm))
    casa = desviament <= tolerancia_cm
    quin = 'A' if diferencia > 0 else 'B'
    nom = 'frunzit' if tipus == 'frunzit' else 'pinça'
    return _check(
        casa, desviament,
        (f'Casa: el costat {quin} sobra {abs(diferencia):.1f} cm, que és el '
         f'{nom} declarat.{detall}' if casa else
         f'NO casa: s\'havien declarat {abs(diferencial_cm):.1f} cm de {nom}, però '
         f'els costats es diferencien en {abs(diferencia):.1f} cm '
         f'({desviament:.1f} cm de desviament).{detall}'),
    )


# ─────────────────────────────────────────────────────────────────────────────
# COBERTURA D'UNA VORA — què s'hi cus, tot junt (Taller de patró · W1)
# ─────────────────────────────────────────────────────────────────────────────

MENA_SOLAPAMENT = 'solapament'
MENA_EXCES = 'exces'


@dataclass(frozen=True)
class TramCosit:
    """Un tram d'una vora que una costura reclama.

    `t_fi` < `t_inici` vol dir que el tram passa per l'origen de la vora (vora tancada):
    la mateixa convenció que `engine.segments.fraccio_tram`.
    """
    sew_id: int
    segment_id: int
    t_inici: float
    t_fi: float
    nom: str = ''
    #: Aquest tram és un COSTAT D'UNA PINÇA. No és una etiqueta decorativa: canvia què vol
    #: dir que el trepitgi la costura que el conté. Vegeu `validar_cobertura`.
    es_pinca: bool = False


@dataclass(frozen=True)
class AvisCobertura:
    """Un problema de cobertura, amb les xifres. Mai un booleà pelat.

    Un avís que digui "hi ha solapament" i prou obliga el patronista a buscar-lo a mà. El
    que serveix és quins trams, de quines costures, i quants centímetres.
    """
    mena: str                      # MENA_SOLAPAMENT | MENA_EXCES
    vora: int
    longitud_vora_cm: float
    missatge: str
    #: Solapament: les dues costures i els dos trams que es trepitgen, i quant.
    sews: tuple[int, ...] = ()
    segments: tuple[int, ...] = ()
    solapament_cm: float = 0.0
    #: Excés: quanta tela reclamen totes les costures juntes, i quanta en sobra.
    suma_cosida_cm: float = 0.0
    exces_cm: float = 0.0


def _intervals(t_inici: float, t_fi: float) -> list[tuple[float, float]]:
    """Un rang de vora, com a intervals que NO donen la volta.

    Un tram que passa per l'origen és, en paràmetre, dos trossos: [t_inici, 1] i [0, t_fi].
    Partir-lo aquí deixa les comparacions de més avall com a comparacions d'intervals normals
    i corrents, en comptes d'un niu d'`if` sobre casos que donen la volta.
    """
    if t_fi >= t_inici:
        return [(t_inici, t_fi)]
    return [(t_inici, 1.0), (0.0, t_fi)]


def _subtrams(tram: TramCosit) -> list[tuple[float, float]]:
    return _intervals(tram.t_inici, tram.t_fi)


def _solapament(a: TramCosit, b: TramCosit) -> float:
    """Fracció de vora que dos trams comparteixen."""
    total = 0.0
    for ai, af in _subtrams(a):
        for bi, bf in _subtrams(b):
            total += max(0.0, min(af, bf) - max(ai, bi))
    return total


def conte(
    ext_inici: float, ext_fi: float, int_inici: float, int_fi: float, eps: float = EPS_T,
) -> bool:
    """El rang exterior conté SENCER l'interior?

    És la pregunta que decideix si una pinça es descompta d'un tram: una pinça que només cau
    a mitges dins de la costura no és una pinça d'aquesta costura —o està mal declarada, o és
    d'una altra vora—, i descomptar-la seria inventar-se tela.
    """
    for ii, if_ in _intervals(int_inici, int_fi):
        if not any(ei - eps <= ii and if_ <= ef + eps for ei, ef in _intervals(ext_inici, ext_fi)):
            return False
    return True


def descomptar_pinces(
    trams: Sequence[TramCosit], pinces: Sequence[CostatPinca],
) -> list[Descompte]:
    """Les pinces que un COSTAT de costura conté, agrupades per pinça.

    Un costat pot ser diversos trams i una pinça té dos costats: el que la costura es menja
    és la SUMA dels costats de pinça que li cauen a dins, i es reporta **per pinça** (no per
    costat) perquè el que el patronista reconeix és la pinça, no les seves meitats.

    Una pinça que no cau sencera dins de cap tram no es descompta: `conte` és estricte a
    posta. Val més una costura que no casa i es pot investigar que una que casa perquè el
    motor ha decidit pel seu compte que aquella tela no hi era.
    """
    per_pinca: dict[int, list[CostatPinca]] = {}
    for costat in pinces:
        if any(conte(t.t_inici, t.t_fi, costat.t_inici, costat.t_fi) for t in trams):
            per_pinca.setdefault(costat.sew_id, []).append(costat)

    return [
        Descompte(
            sew_id=sew_id,
            nom=costats[0].nom,
            cm=round(sum(c.longitud_cm for c in costats), 4),
        )
        for sew_id, costats in sorted(per_pinca.items())
    ]


def fraccio_cosida(tram: TramCosit) -> float:
    """Fracció de la vora que ocupa un tram (dona la volta si cal)."""
    return sum(f - i for i, f in _subtrams(tram))


def validar_cobertura(
    vora: int,
    longitud_vora_mm: float,
    trams: list[TramCosit],
    tolerancia_cm: float = TOLERANCIA_CM,
) -> list[AvisCobertura]:
    """Tot el que es cus sobre UNA vora, mirat junt.

    Dos defectes que només es veuen des d'aquí:

      · **SOLAPAMENT** — dues costures reclamen el mateix tros de vora. Cadascuna, mirada
        sola, pot casar perfectament; juntes, cusen dues vegades la mateixa tela. És el
        defecte típic de declarar trams a mà, i el que la segmentació gir→gir feia
        impossible (els trams derivats no es trepitgen mai perquè són consecutius).
      · **EXCÉS** — la suma del que es cus passa de la vora que hi ha. La peça no té tanta
        tela: o un tram està mal declarat, o hi ha una costura de més.

    Els dos avisos porten les xifres. `longitud_vora_mm` = 0 no és un avís: és una vora
    degenerada, i el que en digués aquesta funció seria soroll sobre un problema que ja
    s'ha reportat abans.
    """
    if longitud_vora_mm <= 0 or not trams:
        return []

    llarg_cm = longitud_vora_mm / MM_PER_CM
    avisos: list[AvisCobertura] = []

    # ── Les pinces que una costura conté no són un conflicte: són la pinça ──
    #
    # Un costat de pinça viu SEMPRE dins de la costura que el travessa —és un tros de la
    # mateixa vora—, i sense aquesta excepció la cobertura el denunciaria dues vegades: com a
    # solapament (la costura i la pinça reclamen la mateixa tela) i com a excés (la suma
    # compta aquells centímetres dos cops). Cap de les dues denúncies seria certa: la costura
    # ja NO cus aquella tela, perquè `validar` l'hi ha descomptada.
    #
    # L'excepció és estreta a posta: només val per als costats de pinça CONTINGUTS en un tram
    # que no és de pinça. Una pinça declarada al mig de res —que no la cus ninguna costura—
    # continua comptant, i ha de comptar: aquella tela sí que es reclama.
    contingut = {
        t.segment_id for t in trams
        if t.es_pinca and any(
            (not u.es_pinca) and conte(u.t_inici, u.t_fi, t.t_inici, t.t_fi)
            for u in trams
        )
    }

    # ── Solapaments, parell a parell ────────────────────────────────────────
    for i in range(len(trams)):
        for j in range(i + 1, len(trams)):
            a, b = trams[i], trams[j]
            if a.segment_id in contingut or b.segment_id in contingut:
                continue
            solapa_cm = _solapament(a, b) * llarg_cm
            if solapa_cm <= tolerancia_cm:
                continue
            mateixa = a.sew_id == b.sew_id
            quins = ' i '.join(filter(None, [a.nom, b.nom])) or 'dos trams'
            avisos.append(AvisCobertura(
                mena=MENA_SOLAPAMENT, vora=vora, longitud_vora_cm=round(llarg_cm, 2),
                sews=(a.sew_id, b.sew_id), segments=(a.segment_id, b.segment_id),
                solapament_cm=round(solapa_cm, 2),
                missatge=(
                    f'La costura {a.sew_id} es trepitja a ella mateixa: {quins} comparteixen '
                    f'{solapa_cm:.1f} cm de la vora {vora}. La longitud del costat compta '
                    f'aquesta tela dues vegades.'
                    if mateixa else
                    f'Les costures {a.sew_id} i {b.sew_id} reclamen els mateixos '
                    f'{solapa_cm:.1f} cm de la vora {vora} ({quins}): aquesta tela no es pot '
                    f'cosir dues vegades.'
                ),
            ))

    # ── Excés: la suma no hi cap ────────────────────────────────────────────
    # Els costats de pinça continguts NO sumen: la seva tela ja la compta el tram que els
    # conté. Comptar-la a part la comptaria dues vegades i inventaria un excés que no hi és.
    compten = [t for t in trams if t.segment_id not in contingut]
    suma_cm = sum(fraccio_cosida(t) for t in compten) * llarg_cm
    exces_cm = suma_cm - llarg_cm
    if exces_cm > tolerancia_cm:
        avisos.append(AvisCobertura(
            mena=MENA_EXCES, vora=vora, longitud_vora_cm=round(llarg_cm, 2),
            sews=tuple(sorted({t.sew_id for t in compten})),
            segments=tuple(t.segment_id for t in compten),
            suma_cosida_cm=round(suma_cm, 2), exces_cm=round(exces_cm, 2),
            missatge=(
                f'La vora {vora} fa {llarg_cm:.1f} cm i les costures en reclamen '
                f'{suma_cm:.1f} cm: en sobren {exces_cm:.1f} cm. La peça no té tanta tela.'
            ),
        ))

    return avisos
