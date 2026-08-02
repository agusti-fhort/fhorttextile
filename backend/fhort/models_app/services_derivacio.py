"""C3-D — servei de DERIVACIÓ entre germanes. Pur: calcula, no escriu.

LA REGLA DE DOMINI (Agus, 02/08 — no es qüestiona):
    L'exterior passa de 54 a 56 → el folre passa de 52 a 54.
    **Es mou el VALOR, mai el grading.** La folgança (aquí 2 cm) es conserva sola, perquè
    ningú no la toca: no hi ha cap norma de folgança enlloc del sistema i no se n'inventa cap.
    La folgança és, sempre, la RESTA entre dues files del mateix POM dins del mateix model.

Per això el que es propaga és l'INCREMENT i mai l'absolut. Propagar l'absolut («posa 56 a totes
les germanes») destruiria justament allò que fa que la parella tingui sentit.

QUÈ ÉS LA FAMÍLIA
    Mateix `(model, POM)`, i **exactament un eix diferent**:
      · germanes de CAPA      → mateixa instància, capa diferent  (exterior ↔ folre)
      · germanes d'INSTÀNCIA  → mateixa capa, instància diferent  (sisa esq. ↔ sisa dreta)
    Una fila que difereix en els DOS eixos (el folre de la sisa esquerra respecte de l'exterior
    de la dreta) no és germana directa de ningú: no hi ha cap parella de la qual llegir una
    folgança, i inventar-ne una seria fabricar una relació que ningú no ha declarat.
    Un sol mecanisme cobreix els dos eixos; l'única cosa que canvia és quin camp es manté fix.

QUÈ NO FA AQUEST SERVEI
    · NO escriu. Retorna proposta; qui escriu és la Fase E.
    · NO proposa mai un valor per a una germana QUE NO EXISTEIX. Si la fila no hi és, no hi és:
      la crea el tècnic o l'import, no el motor de derivació. Aquesta llei és la que impedeix
      que corregir l'exterior fabriqui un folre que ningú no ha mesurat mai.
    · NO toca el grading. El grading es regenera després, a partir de les bases noves.
    · NO decideix si s'aplica: oferir-ho a l'usuari és INTERFÍCIE i va a C4 (llei 3c.5).

COST DE LA CONSULTA: `(model_id, pom_id)` és el prefix exacte de l'índex UNIQUE
`(model_id, pom_id, capa, instancia)`, i l'ordre demanat són les seves columnes 3a i 4a → Index
Scan sense Sort. No cal cap índex nou (verificat amb EXPLAIN a la diagnosi C3 §A6.3).
"""
from dataclasses import dataclass

#: L'origen que estampa una fila moguda per derivació (v. `BaseMeasurement.ORIGEN_CHOICES`).
#: El registre n'hereta el context via `_ORIGEN_TO_CONTEXT`, i és el registre —append-only— qui
#: ha de poder dir després que aquell valor no el va mesurar ningú.
ORIGEN_DERIVAT = 'DERIVAT'

#: Els dos eixos qualificadors, i quin camp es manté FIX en propagar per cadascun.
EIX_CAPA = 'capa'
EIX_INSTANCIA = 'instancia'


@dataclass(frozen=True)
class Derivacio:
    """Una germana afectada i què li tocaria si s'apliqués la propagació.

    `increment` és el mateix per a totes les germanes (és el de la fila origen): és el que
    conserva la folgança. `valor_proposat` ja ve sumat, per comoditat de qui l'apliqui.
    """
    base_measurement_id: int
    pom_id: int
    capa: str
    instancia: str
    eix: str                  # EIX_CAPA o EIX_INSTANCIA: per quin costat és germana
    valor_actual: float
    increment: float
    valor_proposat: float


def germanes_de(bm, *, nomes_actives=True):
    """Les files germanes de `bm`: mateix (model, POM) i EXACTAMENT un eix diferent.

    No inclou `bm`. Retorna un queryset ordenat per (capa, instancia) — l'ordre explícit no és
    decoratiu: el `Meta.ordering` de `BaseMeasurement` no inclou `instancia`, de manera que
    entre dues germanes de la mateixa capa el desempat el faria el planner de Postgres.
    """
    from django.db.models import Q
    from fhort.models_app.models import BaseMeasurement

    qs = BaseMeasurement.objects.filter(model_id=bm.model_id, pom_id=bm.pom_id).exclude(pk=bm.pk)
    if nomes_actives:
        qs = qs.filter(is_active=True)
    # Exactament un eix diferent: o comparteixen instància i canvien de capa, o a l'inrevés.
    return qs.filter(
        Q(instancia=bm.instancia) | Q(capa=bm.capa)
    ).order_by('capa', 'instancia')


def _eix_de(bm, germana):
    """Per quin costat és germana. Amb la Q de sobre, una de les dues sempre es compleix."""
    return EIX_CAPA if germana.instancia == bm.instancia else EIX_INSTANCIA


def deriva(bm, valor_anterior, valor_nou, *, nomes_actives=True):
    """Donada una fila que canvia de valor, retorna QUÈ els tocaria a les seves germanes.

    Pur: no escriu res, no toca `bm`, no dispara cap signal.

    Retorna `[]` —i no és un error— quan:
      · l'increment és zero (no hi ha res a propagar),
      · `valor_anterior` és None (una CREACIÓ no deriva: no hi ha cap delta del qual partir;
        el valor de la germana és una mesura seva, no una conseqüència d'aquesta),
      · no hi ha cap germana viva,
      · una germana no té valor (`base_value_cm` NULL, fila materialitzada sense mesurar):
        moure-la voldria dir inventar-li un valor de partida, i el servei no fabrica mesures.
    """
    if valor_anterior is None or valor_nou is None:
        return []
    increment = round(float(valor_nou) - float(valor_anterior), 2)
    if increment == 0.0:
        return []

    fora = []
    for g in germanes_de(bm, nomes_actives=nomes_actives):
        if g.base_value_cm is None:
            # Fila materialitzada sense valor: no hi ha res d'on partir. No se n'inventa cap.
            continue
        actual = float(g.base_value_cm)
        fora.append(Derivacio(
            base_measurement_id=g.pk,
            pom_id=g.pom_id,
            capa=g.capa,
            instancia=g.instancia,
            eix=_eix_de(bm, g),
            valor_actual=actual,
            increment=increment,
            valor_proposat=round(actual + increment, 2),
        ))
    return fora


def aplica(bm, valor_anterior, valor_nou, *, auth_user=None, motiu_origen='',
           fitting_ref=None, nomes_actives=True):
    """C3/E — calcula la derivació i l'ESCRIU a les germanes. Retorna el que ha aplicat.

    És l'única porta d'escriptura de la derivació, i hi és perquè els dos punts que la criden
    facin exactament el mateix: un sol mecanisme, els dos eixos, el mateix rastre.

    Cada germana moguda queda amb `origen='DERIVAT'`, i és això el que fa que el signal F1
    estampi `context='derivat'` a la seva entrada del `MeasurementChangeLog` — el registre és
    qui ha de poder dir després que aquell valor no el va mesurar ningú (v. la nota de C).
    El `motiu` diu de quina germana ve, perquè una entrada que digui «derivada» sense dir
    d'on obliga a endevinar.

    NO obre transacció: la vol del cridador, que és qui sap si la correcció d'origen i la seva
    propagació han de caure juntes. Tots dos punts de la Fase E ja en tenen una.
    """
    aplicades = []
    for d in deriva(bm, valor_anterior, valor_nou, nomes_actives=nomes_actives):
        from fhort.models_app.models import BaseMeasurement
        germana = BaseMeasurement.objects.get(pk=d.base_measurement_id)
        germana.base_value_cm = d.valor_proposat
        germana.origen = ORIGEN_DERIVAT
        germana._changed_by = auth_user
        germana._fitting_ref = fitting_ref
        germana._motiu = (
            f'Derivat de {bm.capa}/{bm.instancia or "—"} '
            f'({d.increment:+.2f} cm){" · " + motiu_origen if motiu_origen else ""}'
        )
        germana.save(update_fields=['base_value_cm', 'origen', 'updated_at'])
        aplicades.append(d)
    return aplicades
