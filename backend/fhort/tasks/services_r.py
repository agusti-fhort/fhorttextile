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
2. Si no (o si la ronda no cobreix aquest `code`) → la **prevista** (`origen='prevista'`).
3. Dins del conjunt triat, **mai una `Done` si n'hi ha una de viva**.

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
    from .models import ModelTask

    qs = ModelTask.objects.filter(model=model, task_type__code=code)

    r = ronda if ronda is not None else _ronda_oberta(model)
    if r is not None:
        de_la_ronda = qs.filter(ronda=r)
        if de_la_ronda.exists():
            qs = de_la_ronda
        else:
            # Regla 2: la ronda no cobreix aquest code → mana la tasca base.
            qs = qs.filter(origen='prevista')
    else:
        qs = qs.filter(origen='prevista')

    # Regla 3: la feina viva mana sobre la tancada. `order_by('id')` és desempat determinista;
    # amb la unique parcial viva no hi hauria d'haver mai dues `prevista` del mateix tipus, però
    # un resolutor no pot dependre que una constraint no s'hagi trencat mai.
    return qs.exclude(status='Done').order_by('id').first() or qs.order_by('id').first()


# ── F1.1 · LA RONDA ──────────────────────────────────────────────────────────

class RondaError(Exception):
    """Rebuig d'una operació de ronda (ja n'hi ha una d'oberta, cap code vàlid…)."""


def obrir_ronda(model, motiu, tasques_codes, *, profile=None):
    """Obre una volta nova de feina sobre un model i li crea les tasques.

    Aquesta és la sortida de D-5. Una tasca amb línia en albarà EMÈS no es reobre mai —
    `transition_task` la protegeix i ha de seguir fent-ho, perquè el que s'ha facturat s'ha
    facturat. El que es fa és **feina nova amb identitat pròpia**: una `Ronda`, i sota seu una
    `ModelTask` per code, cadascuna apuntant amb `mare` a la tasca homònima de la volta anterior.

    `motiu`: `Ronda.MOTIU_NOVA_MOSTRA` | `Ronda.MOTIU_CORRECCIO`.
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
    """Els `seq` de les rondes del model que ja han lliurat. Fet CONSULTABLE per al PM.

    Només el fet: quines voltes han donat el que havien de donar. L'avís visual (qui el veu,
    quan i com) és F2 — aquí no es notifica ningú.
    """
    from .models import Ronda
    return [r.seq for r in Ronda.objects.filter(model=model).order_by('seq')
            if ronda_lliurable(r)]
