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


# ═════════════════════════════════════════════════════════════════════════════════════════
# L'ESCRIPTURA — SET-2/R11 (2026-08-11)
#
# Viu aquí i no a la vista: tota la lògica de peça en un mòdul, al costat de la resolució que
# la llegeix. Les vistes són primes i només tradueixen a HTTP.
# ═════════════════════════════════════════════════════════════════════════════════════════

#: Les taules que porten l'eix de la peça, amb el camí des del Model. **SÓN SET, no sis** —
#: els briefs d'aquest sprint n'han dit sempre «les 6 taules» i el cens del 2026-08-11 en
#: compta set: a les cinc de `models_app` s'hi sumen `GradedSpec` i `PieceFittingLine`, que
#: viuen a `fitting`. Cap d'elles pot quedar fora del guard d'esborrat: la que en quedés
#: deixaria files apuntant a una peça que ja no existeix.
#: Re-verificable: buscar `garment = models.CharField` a `models_app/models.py` i
#: `fitting/models.py`.
TAULES_AMB_GARMENT = (
    ('BaseMeasurement', lambda m: m.base_measurements),
    ('MeasurementChangeLog', lambda m: m.measurement_changes),
    ('ModelGradingOverride', lambda m: m.grading_overrides),
    ('ModelGradingRule', lambda m: m.grading_rules),
)


def mesures_penjades_de(model, codi):
    """Quantes files de cada taula pengen d'aquesta peça. `{}` = la peça està neta.

    És el guard de l'esborrat, i per això compta TOTES les taules i no només les mesures
    base: esborrar la peça deixaria files de qualsevol d'elles apuntant a un codi que ja no
    existeix — el mateix orfe que T10 va tancar a les còpies, fabricat des de l'altra banda.
    """
    from fhort.fitting.models import GradedSpec, PieceFittingLine
    from fhort.models_app.models import SizeCheckLine

    penjades = {}
    for nom, rel in TAULES_AMB_GARMENT:
        n = rel(model).filter(garment=codi).count()
        if n:
            penjades[nom] = n
    # Les tres que no pengen del Model directament: hi arriben per la seva cadena.
    per_cadena = (
        ('SizeCheckLine', SizeCheckLine.objects.filter(size_check__model=model, garment=codi)),
        ('GradedSpec', GradedSpec.objects.filter(
            grading_version__size_fitting__model=model, garment=codi)),
        ('PieceFittingLine', PieceFittingLine.objects.filter(
            piece_fitting__model=model, garment=codi)),
    )
    for nom, qs in per_cadena:
        n = qs.count()
        if n:
            penjades[nom] = n
    return penjades


def crea_peca(model, dades):
    """Crea una peça. → `(peca, error)`; `error` és `(payload, status)` o `None`.

    Els overrides NO s'accepten a la creació: una peça neix HERETANT-HO TOT (D5, NULL a tot
    arreu) i es desheretaal PATCH. Neixer amb overrides seria demanar a qui crea la peça que
    decideixi coses que encara no sap, i el camí de canviar-les ja existeix.

    MANDROSA (D3): crear la '02' no materialitza res més. La sembra de regles per
    `(model, garment)` la fa la porta que ja existeix quan toqui; disparar-la des d'aquí
    seria una segona via cap al mateix efecte.
    """
    from fhort.models_app.models import ModelGarment

    codi = (dades.get('codi') or '').strip()
    if not codi:
        # D3 escrita també a la vora: la comporta CHECK ho refusaria igualment, però amb un
        # 500 d'IntegrityError. Qui demana la mare per aquesta porta mereix saber per què no.
        return None, ({'error': "El codi de la peça no pot ser buit: la peça mare és el model "
                                "mateix i no té fila pròpia.",
                       'codi': 'garment_mare_no_te_fila'}, 400)
    if ModelGarment.objects.filter(model=model, codi=codi).exists():
        return None, ({'error': f"El model ja té una peça amb el codi «{codi}».",
                       'codi': 'garment_duplicat', 'garment': codi}, 409)

    peca = ModelGarment.objects.create(
        model=model, codi=codi,
        nom=(dades.get('nom') or '').strip(),
        ordre=dades.get('ordre') or 0,
    )
    return peca, None


#: Sentinella: distingeix «el payload no diu res del camp» de «el payload hi diu `null`».
_NO_DIT = object()


def actualitza_peca(model, peca, dades):
    """Modifica una peça. → `(peca, error)`.

    🔑 LA DISTINCIÓ QUE HO SOSTÉ TOT: **`null` explícit vol dir «torna a heretar»; el camp
    ABSENT vol dir «no toquis»**. Sense ella, desheretar és impossible — un PATCH que envia
    només el camp que canvia no podria mai buidar-ne un altre, i un que els enviés tots
    convertiria cada herència en una declaració. És el mateix mecanisme que
    `_procedencia_de_mesura` ja fa servir amb el seu sentinella, i per la mateixa raó.

    El RUN i el SISTEMA passen per la PORTA ÚNICA del model (`_resolve_garment_def`, llei
    S24b): la peça es comporta com el model, amb les mateixes condicions i els mateixos
    avisos. No hi ha cap política nova per a les peces — si el model avui refusa un run amb
    talles que el seu sistema no coneix, la peça també.
    """
    from fhort.pom.models import GradingRuleSet, SizeSystem
    from fhort.models_app.views import _resolve_garment_def

    canvis = []
    if 'nom' in dades:
        peca.nom = (dades['nom'] or '').strip()
        canvis.append('nom')
    if 'ordre' in dades:
        peca.ordre = dades['ordre'] or 0
        canvis.append('ordre')

    # Els FK: `null` → hereta; un id → declara.
    for camp, Model_ in (('size_system', SizeSystem), ('grading_rule_set', GradingRuleSet)):
        valor = dades.get(camp, _NO_DIT)
        if valor is _NO_DIT:
            continue
        if valor is None:
            setattr(peca, f'{camp}_id', None)
        else:
            obj = Model_.objects.filter(pk=valor).first()
            if obj is None:
                return None, ({'error': f'{Model_.__name__} no trobat',
                               'codi': 'referencia_no_trobada', 'camp': camp}, 400)
            setattr(peca, f'{camp}_id', obj.pk)
        canvis.append(camp)

    for camp in ('size_run_model', 'base_size_label'):
        valor = dades.get(camp, _NO_DIT)
        if valor is _NO_DIT:
            continue
        setattr(peca, camp, valor)
        canvis.append(camp)

    # PORTA ÚNICA: es valida el run EFECTIU contra el sistema EFECTIU (tots dos ja resolts
    # amb els canvis d'aquest PATCH aplicats a l'objecte en memòria, encara no desat).
    if 'size_run_model' in canvis or 'size_system' in canvis:
        run_efectiu = valor_efectiu(model, peca, 'size_run_model')
        ss_efectiu = valor_efectiu(model, peca, 'size_system')
        if run_efectiu:
            _fields, err = _resolve_garment_def({
                'size_run': run_efectiu,
                'size_system_id': ss_efectiu.pk if ss_efectiu is not None else None,
            })
            if err:
                return None, (err, 400)
            # El run normalitzat (ordenat per l'ordre del sistema) NOMÉS es desa si la peça
            # el declara: si l'hereta, el que s'ha validat és el del model i tocar-lo aquí
            # seria escriure a la peça una declaració que no ha fet.
            if peca.size_run_model is not None:
                peca.size_run_model = _fields['size_run_model']

    peca.save()
    return peca, None


def esborra_peca(model, peca):
    """Esborra una peça. → `(None, error)`.

    🛑 409 SI TÉ RES PENJAT, i és la garantia PER CONSTRUCCIÓ que aquesta porta no toca cap
    de les set taules de mesura: si n'hi ha una sola fila, no s'esborra. Decisió d'Agus
    (2026-08-11): esborrat de debò, no arxivat — una peça que mai no ha tingut res mesurat
    és un error de teclat, i arxivar-la deixaria brossa que la pantalla hauria d'explicar.

    El payload diu QUANTES files i DE QUINA taula: «no pots» sense el motiu obliga qui ho
    llegeix a endevinar per on buidar-la.
    """
    penjades = mesures_penjades_de(model, peca.codi)
    if penjades:
        total = sum(penjades.values())
        return None, ({
            'error': (f"La peça «{peca.codi}» té {total} files de dades penjades i no es pot "
                      f"esborrar. Cal buidar-la abans."),
            'codi': 'garment_amb_dades',
            'garment': peca.codi,
            'penjades': penjades,
            'total': total,
        }, 409)
    peca.delete()
    return None, None
