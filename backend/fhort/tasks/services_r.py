"""Sprint F1 · EL RESOLUTOR ÚNIC de «la tasca del model» (i, a F1.1, la RONDA).

## Per què existeix aquest mòdul

Fins avui, tres punts del codi resolien «la tasca `<code>` d'aquest model» amb **tres criteris
diferents**, i dos d'ells amb l'ordre INVERTIT (`DIAGNOSI_PREF1_CICLE_TASCA.md` §S-4):

| Punt | Criteri vell |
|---|---|
| `views_b.open_model_task_view` | `filter(origen='prevista').first()` |
| `models_app.views._close_pom_task_for_model` | `filter(task_type__code='pom').order_by('id').first()` → **la més ANTIGA** |
| `models_app.services_size_check.resolve_size_check` | `.exclude(status='Done').order_by('-id').first()` → **la més NOVA** |

Mentre cada model va tenir **una** tasca per tipus, els tres deien el mateix i la divergència era
invisible. La constraint `uniq_prevista_model_tasktype` és PARCIAL (`WHERE origen='prevista'`,
`tasks/models.py`), de manera que la RONDA 2 pot crear una segona tasca del mateix tipus — i el dia
que això passi, «Gravar POM» de la ronda 2 tancaria la ronda 1. Aquesta funció és el prerequisit
que ho impedeix: **un sol criteri, un sol lloc**.

## La regla, en tres línies

1. Si el model té una **Ronda oberta** i aquella ronda té una tasca d'aquest `code` → **aquella**.
2. Si no (o si la ronda no cobreix aquest `code`) → la **prevista** i les seves **correccions**.
3. Dins del conjunt triat, **mai una `Done` si n'hi ha una de viva**.
4. I entre les vives, **mana la correcció més recent** (S-20): una correcció conviu amb la tasca
   que corregeix dins de la mateixa volta, i el que és vigent és l'esmena, no allò que s'esmena.

La regla 2 cobreix el cas «hi ha ronda oberta però d'un altre abast»: una ronda s'obre amb una
llista de codes concreta, i els codes que no hi són segueixen vivint a la tasca base. Sense aquesta
clàusula, `open-task` no trobaria res i intentaria CREAR una `prevista` que ja existeix → violació
de la unique.
"""


def _ronda_oberta(model):
    """La Ronda oberta del model, o None. Oberta = `tancada_el IS NULL`.

    `obrir_ronda` garanteix que no n'hi hagi dues; el `-seq` és una xarxa, no una política: si
    alguna vegada n'hi hagués dues, mana la ÚLTIMA, que és la que el tècnic està treballant.
    """
    from .models import Ronda
    return (Ronda.objects.filter(model=model, tancada_el__isnull=True)
            .order_by('-seq').first())


def tasca_vigent(model, code, *, ronda=None):
    """La tasca `code` VIGENT d'un model — l'únic resolutor del sistema.

    `model`: instància de `models_app.Model` (o el seu pk).
    `code`:  slug de `TaskType.code` (regla G9: mai per id).
    `ronda`: força una Ronda concreta. `None` (el cas normal) = resol la vigent.

    Retorna una `ModelTask` o `None`. No crea res, no transiciona res: és una consulta.
    """
    from django.db.models import Q

    from .models import ModelTask

    qs = ModelTask.objects.filter(model=model, task_type__code=code)

    r = ronda if ronda is not None else _ronda_oberta(model)
    if r is not None and qs.filter(ronda=r).exists():
        qs = qs.filter(ronda=r)
    else:
        # Regla 2: sense ronda (o amb una que no cobreix aquest code) mana la tasca BASE. I amb
        # ella hi van les seves CORRECCIONS (S-20): una correcció no obre ronda, neix `ad_hoc` i
        # hereta la ronda de la mare —NULL quan la mare és la prevista—, o sigui que filtrar
        # només per `origen='prevista'` la deixaria fora i el resolutor no la trobaria mai.
        qs = qs.filter(Q(origen='prevista') | Q(motiu='correccio', ronda__isnull=True))

    # Regla 3: la feina viva mana sobre la tancada.
    vives = qs.exclude(status='Done')
    tria = vives if vives.exists() else qs
    # Regla 4 (S-20): dins del conjunt triat, una CORRECCIÓ mana sobre allò que corregeix, i la
    # més recent sobre les anteriors. Ara que una correcció conviu amb la seva mare dins de la
    # mateixa volta, `order_by('id').first()` retornaria la mare —la feina que ja se sap que no
    # va sortir bé. `order_by('id')` es queda com a desempat determinista de la resta.
    return (tria.filter(motiu='correccio').order_by('-id').first()
            or tria.order_by('id').first())


# ── F1.1 · LA RONDA ──────────────────────────────────────────────────────────

class RondaError(Exception):
    """Rebuig d'una operació de ronda (ja n'hi ha una d'oberta, cap code vàlid…)."""


def obrir_ronda(model, motiu, tasques_codes, *, profile=None):
    """Obre una volta nova de feina sobre un model i li crea les tasques.

    Aquesta és la sortida de D-5. Una tasca amb línia en albarà EMÈS no es reobre mai —
    `transition_task` la protegeix i ha de seguir fent-ho, perquè el que s'ha facturat s'ha
    facturat. El que es fa és **feina nova amb identitat pròpia**: una `Ronda`, i sota seu una
    `ModelTask` per code, cadascuna apuntant amb `mare` a la tasca homònima de la volta anterior.

    `motiu`: `Ronda.MOTIU_NOVA_MOSTRA`. Les CORRECCIONS ja no passen per aquí (S-20): no obren
    volta, i tenen porta pròpia a `obrir_correccio`.
    `tasques_codes`: slugs de `TaskType` (G9: mai ids). Els inactius i els inexistents s'ignoren
    en silenci? NO — es rebutgen, perquè obrir una ronda a la qual li falta mitja feina és pitjor
    que no obrir-la.

    Les tasques neixen `origen='ad_hoc'`: és el que fa que la unique PARCIAL
    `uniq_prevista_model_tasktype` les deixi conviure amb la prevista del mateix tipus.

    Retorna la `Ronda` creada. Atòmic: o hi és sencera o no hi és.
    """
    from django.db import transaction

    from .models import ModelTask, Ronda, TaskType
    from .services_g import lookup_estimated_minutes

    if motiu == Ronda.MOTIU_CORRECCIO:
        raise RondaError('Una correcció no obre ronda: fes servir `obrir_correccio`.')
    if motiu not in dict(Ronda.MOTIU_CHOICES):
        raise RondaError(f'Motiu de ronda desconegut: {motiu!r}.')
    codes = list(dict.fromkeys(tasques_codes or []))   # dedup preservant ordre
    if not codes:
        raise RondaError('Una ronda sense cap tasca no és una ronda.')
    if _ronda_oberta(model) is not None:
        raise RondaError('Aquest model ja té una ronda oberta; tanca-la abans d\'obrir-ne una altra.')

    tipus = {t.code: t for t in TaskType.objects.filter(code__in=codes, active=True)}
    desconeguts = [c for c in codes if c not in tipus]
    if desconeguts:
        raise RondaError(f"Tipus de tasca inexistents o inactius: {', '.join(desconeguts)}.")

    # Les MARES es resolen ABANS de crear la Ronda, i el motiu és mecànic: un cop la ronda
    # existeix, `tasca_vigent` ja resol per ella i retornaria les filles (o None). Aquí encara
    # resol pel criteri vell, que és exactament «la tasca de la volta anterior».
    mares = {code: tasca_vigent(model, code) for code in codes}

    with transaction.atomic():
        seguent = (Ronda.objects.filter(model=model)
                   .order_by('-seq').values_list('seq', flat=True).first() or 1) + 1
        ronda = Ronda.objects.create(model=model, seq=seguent, motiu=motiu)
        base_order = ModelTask.objects.filter(model=model).count()
        for i, code in enumerate(codes):
            tt = tipus[code]
            ModelTask.objects.create(
                model=model, task_type=tt, order=base_order + i,
                status='Pending', origen='ad_hoc',
                ronda=ronda, mare=mares[code], motiu=motiu,
                assignee=profile,
                estimated_minutes=lookup_estimated_minutes(model, tt))
    return ronda


def obrir_correccio(model, tasques_codes, *, profile=None):
    """Refà feina que no va sortir bé. **No obre cap Ronda** (S-20, 05/08).

    Una ronda és una MOSTRA: `Ronda.seq` és el número que el PM llegeix i el que billing
    consultarà per a les voltes pactades. Fins avui una correcció n'obria una i el comptador
    pujava, de manera que un model amb tres esmenes nostres semblava que hagués fet tres
    mostres al client. Comptaven dues coses diferents amb el mateix número.

    Ara una correcció és el que sempre va ser: una tasca NOVA lligada a la que corregeix
    (`mare`), amb `motiu='correccio'`, que **hereta la ronda de la mare** — i NULL quan la mare
    és la prevista, que és la volta 1 implícita. El model ja ho preveia (`ModelTask.motiu`
    existeix a part del de la Ronda «perquè una tasca ad-hoc pot néixer d'una correcció sense
    que s'obri cap ronda»); el que faltava era que el servei ho fes.

    A diferència d'`obrir_ronda`, això NO topa amb la ronda oberta: una correcció dins de la
    volta que s'està treballant és el cas normal, no una excepció.

    Retorna `(ronda_heretada | None, [ModelTask])`. Atòmic.
    """
    from django.db import transaction

    from .models import ModelTask, Ronda, TaskType
    from .services_g import lookup_estimated_minutes

    codes = list(dict.fromkeys(tasques_codes or []))
    if not codes:
        raise RondaError('Una correcció sense cap tasca no és una correcció.')

    tipus = {t.code: t for t in TaskType.objects.filter(code__in=codes, active=True)}
    desconeguts = [c for c in codes if c not in tipus]
    if desconeguts:
        raise RondaError(f"Tipus de tasca inexistents o inactius: {', '.join(desconeguts)}.")

    # Sense mare no hi ha correcció: corregir vol dir refer ALGUNA COSA. Si el model no té encara
    # aquella tasca, el que toca és obrir-la (`open-task`), no corregir-la.
    mares = {code: tasca_vigent(model, code) for code in codes}
    orfes = [c for c, m in mares.items() if m is None]
    if orfes:
        raise RondaError(f"No hi ha res a corregir de: {', '.join(orfes)}.")

    fetes = []
    with transaction.atomic():
        base_order = ModelTask.objects.filter(model=model).count()
        for i, code in enumerate(codes):
            mare = mares[code]
            tt = tipus[code]
            fetes.append(ModelTask.objects.create(
                model=model, task_type=tt, order=base_order + i,
                status='Pending', origen='ad_hoc',
                ronda=mare.ronda, mare=mare, motiu=Ronda.MOTIU_CORRECCIO,
                assignee=profile,
                estimated_minutes=lookup_estimated_minutes(model, tt)))
    return (fetes[0].ronda if fetes else None), fetes


def tancar_ronda(ronda):
    """Tanca una ronda (`tancada_el = ara`). Idempotent: tancar-ne una de tancada no fa res."""
    from django.utils import timezone

    from .models import Ronda
    Ronda.objects.filter(pk=ronda.pk, tancada_el__isnull=True).update(tancada_el=timezone.now())
    ronda.refresh_from_db()
    return ronda


def ronda_lliurable(ronda):
    """La ronda ha produït tot el que havia de lliurar?

    Cert quan **totes** les tasques de la ronda el `TaskType` de les quals és `es_lliurable`
    estan `Done`. Els lliurables són els PRODUCTES (fitxa, patró), no la feina intermèdia: una
    ronda pot tenir el POM obert i ser lliurable igualment si la fitxa i el patró ja hi són.

    Sense cap tasca lliurable a la ronda retorna **False**, no True: «no hi ha res per lliurar»
    no és «ja està lliurat», i un avís al PM que salta sobre el buit és soroll.
    """
    qs = ronda.tasques.filter(task_type__es_lliurable=True)
    if not qs.exists():
        return False
    return not qs.exclude(status='Done').exists()


def rondes_lliurables(model):
    """Les rondes del model que JA han lliurat. Fet CONSULTABLE per al PM.

    Retorna `[{'seq', 'motiu', 'lliurat_el'}]`, de la més antiga a la més nova. `lliurat_el` és
    l'instant en què va caure l'ÚLTIM lliurable de la volta — el moment en què el PM podria
    haver-ho sabut. Sense data, un badge que digui «lliurable» no diu si va passar avui o al març.

    F2.7 — només el FET. Qui el veu, quan i com és pintat; notificar activament (correu, push)
    és una decisió a part que aquest sprint no pren.
    """
    from django.db.models import Max

    from .models import Ronda
    fora = []
    for r in Ronda.objects.filter(model=model).order_by('seq'):
        if not ronda_lliurable(r):
            continue
        quan = (r.tasques.filter(task_type__es_lliurable=True)
                .aggregate(q=Max('finished_at'))['q'])
        fora.append({'seq': r.seq, 'motiu': r.motiu,
                     'lliurat_el': quan.isoformat() if quan else None})
    return fora


# ── F1.7 · D-2 · EL TEMPS DECLARAT ───────────────────────────────────────────

class TempsDeclaratError(Exception):
    """Rebuig d'una declaració de temps (tipus de tasca intern, dades incoherents…)."""


def declara_temps(task, profile, *, minuts=None, inici=None, fi=None):
    """Registra temps que el sistema NO ha pogut mesurar.

    D-2, tercera pota: «externes = temps declarat». Una tasca `Externa-lliure` (patró a mà,
    revisió de disseny, aclariments) es fa **fora de l'eina**: no hi ha cap escriptura que batre
    i el rellotge no hi arriba mai. Fins avui aquell temps simplement no existia enlloc.

    Dues formes, EXCLOENTS:
      · `minuts`        — «hi he dedicat 90 minuts». El tram s'ancora acabant ARA.
      · `inici` + `fi`  — «hi vaig treballar de tal a tal hora».

    El tram neix TANCAT (`fi` informat, `actiu=False`) i amb `origen='declarat'`, de manera que
    `TRAMS_SANS` el compta i el Welford l'aprèn igual que un de mesurat: una tasca és una mostra
    (D-3) tant si el temps s'ha comptat sol com si l'ha dit una persona.

    Guard dur: **només tasques `Externa-lliure`**. Declarar hores sobre una tasca interna seria
    poder inventar temps facturable a mà sobre feina que l'eina SÍ que mesura.
    """
    import datetime as _dt

    from django.utils import timezone

    from .models import TimerEntrada
    from .services_i import MAX_MINUTS_TRAM

    if task.task_type.tipus != 'Externa-lliure':
        raise TempsDeclaratError(
            "El temps només es declara en tasques Externa-lliure: les internes es mesuren soles.")
    if profile is None:
        raise TempsDeclaratError('Cal un perfil de tècnic per declarar temps.')

    te_minuts = minuts is not None
    te_franja = inici is not None or fi is not None
    if te_minuts == te_franja:
        raise TempsDeclaratError("Cal {minuts} O BÉ {inici, fi}, mai els dos ni cap dels dos.")

    if te_minuts:
        try:
            minuts = int(minuts)
        except (TypeError, ValueError):
            raise TempsDeclaratError('`minuts` ha de ser un enter.')
        fi = timezone.now()
        inici = fi - _dt.timedelta(minutes=minuts)
    else:
        if inici is None or fi is None:
            raise TempsDeclaratError('La franja necessita `inici` I `fi`.')
        if fi <= inici:
            raise TempsDeclaratError('`fi` ha de ser posterior a `inici`.')
        minuts = int((fi - inici).total_seconds() // 60)

    if minuts <= 0:
        raise TempsDeclaratError('Un tram declarat ha de durar com a mínim un minut.')
    # Mateix sostre que la higiene de trams: un tram de més d'un dia no és una jornada llarga,
    # és una dada que no ens creiem. Aquí es rebutja en comptes d'excloure'l després en silenci.
    if minuts > MAX_MINUTS_TRAM:
        raise TempsDeclaratError(
            f'Un tram declarat no pot superar {MAX_MINUTS_TRAM} minuts ({MAX_MINUTS_TRAM // 60} h).')

    return TimerEntrada.objects.create(
        model_task=task, tecnic=profile, inici=inici, fi=fi, minuts=minuts,
        actiu=False, origen=TimerEntrada.ORIGEN_DECLARAT)
