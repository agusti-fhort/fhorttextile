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
    """La Ronda oberta del model, o None.

    F1.0 — STUB DELIBERAT: l'entitat `Ronda` neix a F1.1 amb la seva migració. Fins llavors això
    retorna sempre None i la branca 1 de `tasca_vigent` és codi mort. La SIGNATURA de
    `tasca_vigent` ja és la final: els tres call-sites es migren un sol cop, ara, i F1.1 només ha
    d'omplir aquest cos.
    """
    return None


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
