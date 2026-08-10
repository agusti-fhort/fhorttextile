"""Què compta com un FITTING QUE HA PASSAT DE DEBÒ. Lectura pura, cap escriptura.

Un `PieceFitting` es materialitza en OBRIR la graella: la peça existeix des del moment que
algú clica, amb totes les línies sembrades des de l'spec (`valor_real = valor_teoric`, cap
decisió, cap nota). Existir-hi, doncs, NO vol dir que s'hi hagi mesurat res.

Aquesta distinció no era enlloc i les dues superfícies que la necessiten la van resoldre
cadascuna a la seva manera —o no la van resoldre gens:

  · el REPÀS pintava una columna per peça, i al 1320 en sortien dues d'idèntiques
    («DEV @09/08» × 2): la del fitting que es va fer i la de la graella que algú va obrir i
    no va tocar. Una columna sense contingut al costat d'una amb contingut es llegeix com
    dos fittings, i el tècnic hi busca la diferència;
  · la COMPROVACIÓ deia «al darrer fitting» i recorria TOTES les peces per id descendent,
    quedant-se amb el primer encert de cada mesura: o sigui que barrejava fittings.

El predicat és el de la modista, no un llindar: una línia té contingut si algú hi ha DIT
alguna cosa —un veredicte (D-31.21: `''` NO és 'ACCEPTED', és «ningú no ho ha mirat»), una
nota— o si el número real s'aparta del teòric amb què va néixer. Els tres són gestos humans;
la sembra no en fa cap.
"""
from .models import PieceFitting

#: Estat de sessió que treu la peça del cens: la taula diu què s'ha fet, no què es va programar.
ESTAT_FORA = 'Anullada'


def linia_te_contingut(linia):
    """Algú ha tocat aquesta línia? Veredicte, nota o número que s'aparta del teòric."""
    if (linia.decisio or '').strip():
        return True
    if (linia.nota or '').strip():
        return True
    if linia.valor_real is None or linia.valor_teoric is None:
        return False
    return float(linia.valor_real) != float(linia.valor_teoric)


def peces_amb_contingut(model_id):
    """Les peces del model on s'ha mesurat de debò, en ordre CRONOLÒGIC.

    Ordre per `session.data` amb `session_id` de desempat estable —mai per id de peça sol,
    que és l'ordre en què es van OBRIR les graelles i no el dia en què es va provar la peça.
    """
    peces = (PieceFitting.objects
             .filter(model_id=model_id)
             .exclude(session__estat=ESTAT_FORA)
             .select_related('session', 'session__responsable')
             .prefetch_related('linies')
             .order_by('session__data', 'session__id'))
    return [p for p in peces if any(linia_te_contingut(l) for l in p.linies.all())]


def darrera_peca_amb_contingut(model_id):
    """LA del «darrer fitting»: l'última peça on algú va mesurar. `None` si no n'hi ha cap."""
    peces = peces_amb_contingut(model_id)
    return peces[-1] if peces else None
