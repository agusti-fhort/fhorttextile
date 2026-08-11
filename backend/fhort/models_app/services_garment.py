"""LA RESOLUCIÓ `garment.X or model.X`, EN UN SOL PUNT — SET-2/T2-bis (2026-08-11).

D5 diu que una peça porta overrides nullables i que **NULL vol dir «hereta del model»**. Aquest
mòdul és l'ÚNIC lloc on aquella frase es converteix en codi.

⚠️ PER QUÈ UN SOL PUNT, i no un `or` escampat allà on faci falta: perquè ja ho vam pagar. El
10/08 es va revertir `7cc133b5` —una clau `garment` servida crua al payload de
`base-measurements/`— precisament amb aquest argument: una vora que serveix el valor CRU al
costat d'una altra que serveix el RESOLT són dos orígens per al mateix camp a la mateixa
superfície, i el dia que la regla d'herència canviï només se n'actualitzarà un. Qui necessiti
el valor efectiu d'una peça passa per aquí; qui necessiti l'eix d'una FILA (de quina peça és)
no necessita res d'això, que és dada factual i es serveix directament.

⚠️ EL PREDICAT ÉS `is None`, NO LA FALSEDAT, i la diferència no és teòrica. El brief l'escriu
com `garment.X or model.X`, però `or` també cauria al model amb `''` o amb `0`, i llavors una
peça no podria mai declarar un valor buit distint del de la mare. La llei declarada a
`ModelGarment` és «els overrides neixen NULL i NULL vol dir hereta»: el que decideix, doncs, és
la NUL·LITAT, no la veritat. Per als FK es pregunta pel `_id`, que és el que Postgres té.

⚠️ LA MARE NO TÉ FILA (D3) i aquí es fabrica SINTÈTICA, mai es llegeix ni s'escriu. Els seus
valors són els del model i per definició no hereten de ningú: `heretat=False` a tots els camps.
Es publica perquè qui pinti pugui recórrer totes les prendes d'un model amb un sol bucle, no
perquè existeixi enlloc.
"""
from fhort.models_app.models import ModelGarment

#: El codi de la peça mare. Mai és una fila: és el model mateix.
GARMENT_MARE = ''


def valor_efectiu(model, peca, camp):
    """El valor que governa `camp` per a aquesta peça: el seu, i si és NULL el del model.

    `peca=None` és la MARE i torna sempre el valor del model — no és un cas especial
    tolerat, és la definició: la mare ÉS el model.
    """
    if peca is None:
        return getattr(model, camp)
    propi = getattr(peca, camp)
    return getattr(model, camp) if propi is None else propi


def _etiqueta(valor):
    """Text presentable d'un valor efectiu. Els FK porten `__str__`; la resta són escalars."""
    if valor is None:
        return ''
    return str(valor)


def _camp_resolt(model, peca, camp):
    valor = valor_efectiu(model, peca, camp)
    heretat = peca is not None and getattr(peca, camp) is None
    return {
        # Els FK viatgen per PK (és el que un client desa i torna a enviar); els escalars,
        # tal qual. `etiqueta` és per pintar i no és identitat: ningú hi ha de decidir res.
        'valor': valor.pk if hasattr(valor, 'pk') else valor,
        'etiqueta': _etiqueta(valor),
        'heretat': heretat,
    }


def _peca_resolta(model, peca):
    es_mare = peca is None
    dades = {
        'codi': GARMENT_MARE if es_mare else peca.codi,
        'nom': (model.nom_prenda or '') if es_mare else peca.nom,
        'ordre': 0 if es_mare else peca.ordre,
        'es_mare': es_mare,
        # La mare no té fila: qui vulgui EDITAR-LA ha d'anar al model, no a una peça.
        'id': None if es_mare else peca.pk,
    }
    for camp in ModelGarment.CAMPS_HERETABLES:
        dades[camp] = _camp_resolt(model, peca, camp)
    return dades


def peces_del_model(model):
    """Totes les prendes d'un model —la mare inclosa— amb els seus valors EFECTIUS.

    Retorna una llista: la mare primer i després les peces per `ordre`/`codi`. Un model d'una
    sola prenda —el 100% del corpus d'avui— torna una llista d'UN element, i qui pinti pot
    decidir amb `len(...) > 1` si ensenya cap eina de peces (la mateixa llei que
    `calArbrePerGarment` ja aplica al front).
    """
    return [_peca_resolta(model, None)] + [
        _peca_resolta(model, p) for p in model.garments.all()
    ]


def te_mes_duna_peca(model):
    """El predicat que decideix si l'eix de peça és visible enlloc. En UN sol lloc, també."""
    return model.garments.exists()
