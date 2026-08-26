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


# ═══════════════════════════════════════════════════════════════════════════════════════════
# M4 · FIT-5 + FIT-12 — LA COSTURA AMB EL COMERCIAL: dins o fora del numeral de la comanda.
#
# Tres funcions i una sola direcció de lectura: `tasks` pregunta a `commerce` quantes voltes
# admet el pacte, i `commerce` no sap que les rondes existeixen. La resposta s'escriu a la
# `Ronda` en obrir-la (foto) i no es torna a calcular mai — v. el docstring dels camps.
# ═══════════════════════════════════════════════════════════════════════════════════════════

def linia_de_comanda(model):
    """LA LÍNIA DE COMANDA QUE GOVERNA AQUEST MODEL, o `None` si no en té cap.

    No hi ha cap FK directa model→comanda al sistema: **el pivot és el `WorkOrder`**
    (`commerce/models.py`, `WorkOrder.model` + `WorkOrder.order_line`). Un WO de tipus `ORDER`
    és «aquest model, per aquesta línia»; un `COLLECTOR` és el contenidor mensual de la feina
    SENSE comanda i per definició no en té cap (constraint `collector_no_model_no_orderline`).

    Quin WO mana, quan n'hi ha més d'un:
      1. **El que està OBERT.** `_assign_model_core` ja garanteix que no n'hi hagi dos alhora
         («El model ja té un encàrrec (WO ORDER) actiu»), o sigui que aquest cas és únic.
      2. Si cap no ho està, **el més recent** que encara conservi la seva línia. Un WO tancat
         segueix dient de quina venda venia la feina, i és la lectura correcta per a una volta
         que s'obre després d'haver tancat l'encàrrec.

    QUÈ QUEDA FORA, i per què:
      · `order_line = NULL` (WO **orfe**, desassignat) — desassignar és treure el model de la
        venda: si ja no hi penja, aquella comanda no li pot fixar cap límit. El camp
        `orphaned_from_line` guarda d'on venia, però és traça, no govern.
      · Comanda **CANCELLED** — una venda anul·lada no pacta res.

    Retorna una `commerce.SalesOrderLine` o `None`.
    """
    from fhort.commerce.models import WorkOrder

    base = (WorkOrder.objects
            .filter(model=model, kind='ORDER', order_line__isnull=False)
            .exclude(order_line__order__status='CANCELLED')
            .select_related('order_line'))
    wo = (base.filter(status='OPEN').order_by('-created_at').first()
          or base.order_by('-created_at').first())
    return wo.order_line if wo is not None else None


def numeral_efectiu(model):
    """QUANTES VOLTES ADMET EL PACTE d'aquest model. Retorna `(linia, numeral)`.

    `numeral` és `None` quan **no hi ha límit**, i el `None` arriba per dos camins que la crida
    ha de poder distingir mirant `linia`:
      · `(None, None)` — **el model no té comanda**. Sense pacte no hi ha límit: cap volta
        desborda mai. És el cas normal d'un model de mostrari, i **no és un error** (el cens del
        25/08 diu que avui, a `fhort`, ho són els 37 models: cap WO de tipus ORDER).
      · `(linia, None)` — hi ha comanda i el pacte **no fixa numeral** (`rounds_included` null).

    I `(linia, 0)` és el tercer cas, ben diferent d'aquests dos: el pacte no inclou **cap** volta,
    i per tant ja desborda la primera. Per això el camp és nullable i no té default 0.
    """
    linia = linia_de_comanda(model)
    if linia is None:
        return None, None
    return linia, linia.rounds_included


def resol_desbordament(ronda):
    """ESCRIU a la volta si cau DINS o FORA del numeral. Es crida UN COP, en obrir-la.

    FIT-12: `seq > numeral` → fora de comanda. Sense comanda o sense numeral → mai fora.
    Desa també la línia i el numeral vigents perquè el «perquè» de la safata («R3 · fora de
    comanda · n>2 de la comanda C-2026-0001») es pugui dir sencer més tard, encara que el
    numeral s'hagi editat entremig.

    Guarda els tres camps amb `update_fields` i retorna la mateixa `Ronda`, ja mutada en memòria.
    """
    linia, numeral = numeral_efectiu(ronda.model)
    ronda.linia_comanda = linia
    ronda.numeral_vigent = numeral
    ronda.fora_de_comanda = numeral is not None and ronda.seq > numeral
    ronda.save(update_fields=['linia_comanda', 'numeral_vigent', 'fora_de_comanda'])
    return ronda


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


def ronda_del_gest(model):
    """M1-bis · FIT-4 — LA RONDA A LA QUAL NEIX una tasca que acaba de sortir d'un gest de treball.

    Aquesta és la peça que substitueix la llei vella («la R1 és implícita»): la volta 1 ja no es
    dóna per feta, **neix sola del primer gest de treball** —programar, assignar o entrar-hi i
    executar— sense que ningú l'hagi de declarar. Les voltes següents segueixen sent explícites
    (`obrir_ronda`), i per això aquí NOMÉS es crea la R1.

    Tres respostes, i cap és arbitrària:

      1. **Hi ha una ronda OBERTA** → aquella. És FIT-4: «es pot obrir una tasca lliure que entra
         en aquesta ronda». La feina nova que apareix enmig d'una volta és feina d'aquella volta.
      2. **El model no té CAP ronda** → es crea la **R1 (`seq=1`)** i s'hi lliga la tasca.
      3. **Té rondes però totes tancades** → **`None`**, i la tasca neix sense ronda. Obrir-ne una
         de nova aquí seria fabricar una R(n+1) automàticament, i FIT-4 diu el contrari: «R2+
         neixen amb +Ronda explícit». Aquesta feina espera que el PM obri la volta.

    🔒 **NOMÉS MIRA ENDAVANT** (sub-decisió b, Agus 24/08). No adopta res: en un model amb feina
    prèvia i cap ronda, el primer gest NOU crea la R1 i **només la tasca d'aquell gest hi entra**
    (c). El passat que això deixava enrere el va resoldre el **retroactiu de M5** (25/08), d'una
    sola vegada i com a acte declarat (`ops/retroactius/retroactiu_r1_m5.py`); d'aquesta funció
    no se n'espera cap adopció, ni abans ni ara.

    🔒 **NO POT NÉIXER DUES VEGADES.** Qui ho impedeix és la BD, no un `if`: `uniq_ronda_model_seq`
    (`Ronda.Meta.constraints`) ja fa única la parella `(model, seq)`, i `get_or_create` s'hi
    recolza —dos gestos simultanis sobre el mateix model xoquen a la constraint i el perdedor
    rellegeix la fila del guanyador. Sense la constraint caldria un lock; amb ella no en cal cap.

    Retorna la `Ronda` o `None`. **No transiciona res i no toca cap tasca existent.**
    """
    from .models import Ronda

    oberta = _ronda_oberta(model)
    if oberta is not None:
        return oberta
    if Ronda.objects.filter(model=model).exists():
        return None                      # cas 3: totes tancades → el PM ha d'obrir la següent
    ronda, creada = Ronda.objects.get_or_create(
        model=model, seq=1, defaults={'motiu': Ronda.MOTIU_NOVA_MOSTRA})
    # M4 · FIT-12 — també la R1 es pesa contra el numeral, i NOMÉS quan acaba de néixer. Amb un
    # `rounds_included` de 0 el pacte no inclou cap volta i la primera ja desborda; si es fes
    # només a `obrir_ronda` (seq≥2) aquell cas no el veuria ningú. El `creada` és el que evita
    # rescriure el veredicte cada cop que un gest retorna una R1 que ja existia: la foto és del
    # moment de l'obertura (v. els camps a `models.py`).
    if creada:
        resol_desbordament(ronda)
    return ronda


#: M1-bis · FIT-4 — QUÈ NO ES REPLICA d'una volta a la següent.
#:
#: 🚩 **ATENCIÓ, AQUESTA LLISTA ÉS UNA INTERPRETACIÓ I ESTÀ PENDENT D'AGUS** (v. l'acta de M1-bis).
#: El brief demana «no copiïs les tasques ad_hoc/lliures, només les de catàleg», i cap dels dos
#: camps que semblen dir-ho serveix per a això:
#:   · `origen`: **totes** les tasques que crea `obrir_ronda` neixen `ad_hoc` a posta (v. la nota
#:     de la funció: és el que les deixa conviure amb la `prevista` sota la unique parcial). Filtrar
#:     per `origen='prevista'` replicaria tot R1→R2 i **res** de R2→R3.
#:   · `motiu='nova_mostra'`: marca les que va proposar la volta anterior, però **la R1 no en té cap**
#:     —les seves tasques neixen dels gestos normals, amb `motiu` NULL—, o sigui que R1→R2 no
#:     replicaria res.
#: L'únic camp que literalment vol dir «això no és de la recepta» és `off_recipe`, i és el que
#: s'usa. Les correccions no calen a la llista: es dedupliquen soles, perquè comparteixen el `code`
#: de la tasca que corregeixen i la còpia va **per code**.
_NO_ES_REPLICA = {'off_recipe': True}


def codes_a_replicar(ronda):
    """El JOC DE TASQUES d'una volta, en CODES (G9), per tornar-lo a proposar a la següent.

    FIT-4: «R2+ … REPLIQUEN EL JOC DE TASQUES DE LA RONDA ANTERIOR com a proposta reexecutable».
    Es replica **el joc**, no les tasques: codes, no files. Per això surt `dict.fromkeys` sobre
    l'ordre de treball i no un `values_list` qualsevol — l'ordre de la volta nova ha de ser el de
    l'anterior, i els duplicats (una correcció i la seva mare comparteixen code) col·lapsen sols.

    Res del que es replica arrossega estat: ni temps, ni timers, ni assignació, ni notes. El que
    viatja és **què s'ha de tornar a fer**, i prou.
    """
    if ronda is None:
        return []
    qs = (ronda.tasques.exclude(**_NO_ES_REPLICA)
          .select_related('task_type').order_by('order', 'id'))
    return list(dict.fromkeys(t.task_type.code for t in qs))


def _ronda_anterior(model):
    """La volta TANCADA de `seq` més alta, o None. És «la volta anterior» del model.

    El filtre `tancada_el__isnull=False` és explícit i no redundant, encara que l'únic cridador
    (`obrir_ronda`) ja rebutgi els models amb una volta oberta: aquesta funció decideix **de quina
    volta es replica el joc i contra quina es resol la `mare`**, i deixar-ho depenent d'un guard
    que viu en una altra funció és com es fabriquen els defectes que sobreviuen a un refactor.
    """
    from .models import Ronda
    return (Ronda.objects.filter(model=model, tancada_el__isnull=False)
            .order_by('-seq').first())


def mare_homologa(ronda_anterior, code):
    """La tasca de `code` de la VOLTA ANTERIOR — la `mare` de la que ara es crearà.

    🚨 **PER QUÈ NO ES FA AMB `tasca_vigent`** (defecte heretat d'M1, corregit aquí). Quan
    `obrir_ronda` s'executa **totes les voltes són tancades** —és el seu propi guard—, i llavors
    `tasca_vigent` cau a la **regla 2**: `Q(origen='prevista') | Q(motiu='correccio', ronda NULL)`.
    Aquell filtre retorna la tasca **base**, que amb la llei nova és la de la **R1**. Resultat: la
    `mare` de la R3 apuntava a la R1 i **la cadena saltava totes les voltes intermèdies**. El
    `help_text` del camp deia «la tasca homònima de la volta anterior» i el codi en donava una
    altra.

    Ara es resol contra la volta anterior i prou. **Si no hi ha homòloga, `None`**: no s'encadena
    amb voltes més velles, perquè «la volta anterior no en tenia» és una dada, i inventar-hi una
    àvia com si fos la mare seria tornar a mentir en una altra direcció.

    ⚠️ **AQUESTA FUNCIÓ NO COBREIX EL MODEL SENSE CAP VOLTA.** Amb `ronda_anterior=None` no hi ha
    res contra què resoldre, i qui decideix què fer llavors és `obrir_ronda` — v. la nota del
    MODEL LLEGAT allà.

    Entre diverses tasques del mateix code dins d'aquella volta mana **la més recent** (`-id`),
    que és el mateix criteri que la regla 4 de `tasca_vigent`: quan hi ha una correcció i la tasca
    que corregeix, el que s'ha de repetir és l'esmena, no allò que es va esmenar.
    """
    if ronda_anterior is None:
        return None
    return (ronda_anterior.tasques.filter(task_type__code=code)
            .order_by('-id').first())


def tasques_del_buit(model, ronda_anterior):
    """CODA · DECISIÓ 2 — la feina nascuda al BUIT entre dues voltes, que la nova ha d'adoptar.

    El buit existeix perquè `ronda_del_gest` retorna `None` quan totes les voltes són tancades
    (cas 3): una tasca oberta llavors neix `ronda=NULL` i **espera**. Aquí s'acaba l'espera —
    quan el PM obre la volta següent, aquella feina hi entra.

    🔒 **NO ÉS UN BACKFILL, I LA FRONTERA ÉS TEMPORAL I EXACTA.** S'adopta només el que s'ha
    creat **DESPRÉS** que la volta anterior es tanqués: `created_at > ronda_anterior.tancada_el`
    (`Ronda.tancada_el` és el camp real; `ModelTask.created_at` és `auto_now_add`). Tot el que és
    anterior —les `ronda=NULL` d'abans de la primera volta del model, que són l'històric sencer—
    **no es toca**: segueix esperant el retroactiu de M5, i la sub-decisió (b) queda intacta.

    Sense volta anterior no hi ha buit: un model que encara no n'ha tancat cap no té «després de».
    """
    from .models import ModelTask

    if ronda_anterior is None or ronda_anterior.tancada_el is None:
        return ModelTask.objects.none()
    return (ModelTask.objects.filter(model=model, ronda__isnull=True,
                                     created_at__gt=ronda_anterior.tancada_el)
            .select_related('task_type').order_by('order', 'id'))


def obrir_ronda(model, motiu, tasques_codes, *, profile=None):
    """Obre una volta nova de feina sobre un model i li crea les tasques.

    Aquesta és la sortida de D-5. Una tasca amb línia en albarà EMÈS no es reobre mai —
    `transition_task` la protegeix i ha de seguir fent-ho, perquè el que s'ha facturat s'ha
    facturat. El que es fa és **feina nova amb identitat pròpia**: una `Ronda`, i sota seu una
    `ModelTask` per code, cadascuna apuntant amb `mare` a la tasca homònima de la volta anterior
    —**la de seq més alta tancada**, no la base: v. `mare_homologa`.

    `motiu`: `Ronda.MOTIU_NOVA_MOSTRA`. Les CORRECCIONS ja no passen per aquí (S-20): no obren
    volta, i tenen porta pròpia a `obrir_correccio`.

    CODA · DECISIÓ 2 — la volta nova **ADOPTA la feina del BUIT**: les tasques `ronda=NULL`
    creades DESPRÉS del tancament de la volta anterior (v. `tasques_del_buit`). Els seus codes no
    es repliquen —el que ja existeix no es proposa— i es reporten a `ronda._codes_adoptats`.

    `tasques_codes`: slugs de `TaskType` (G9: mai ids), **ADDITIUS**. M1-bis · FIT-4 — la volta
    neix amb el **joc de tasques de l'anterior** (`codes_a_replicar`) i el que es demana aquí s'hi
    SUMA. Es pot cridar amb la llista buida: aquest és ara el cas normal d'un +Ronda que només vol
    repetir la volta. Els codes DEMANATS inexistents o inactius es rebutgen (qui els demana s'ha
    equivocat); els REPLICATS que hagin quedat inactius s'ometen i es reporten a
    `ronda._codes_omesos`, perquè un canvi de catàleg no pot tombar una obertura.

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
    demanats = list(dict.fromkeys(tasques_codes or []))   # dedup preservant ordre
    # 🔒 **UNA RONDA OBERTA PER MODEL** (llei ratificada per Agus/CTO, M2 · CODA-BIS). El guard hi
    # és des d'F1.1 i és l'ÚNIC lloc que el pot imposar: `Ronda.objects.create` només apareix aquí
    # i a `ronda_del_gest`, que fa `get_or_create(seq=1)` i per tant no pot fabricar una segona
    # volta viva. La BD no hi ajuda a posta —`uniq_ronda_model_seq` fa única la parella
    # `(model, seq)`, no «una d'oberta»— perquè una constraint parcial obligaria a inventar-se el
    # tancament, i tancar una volta és un acte humà (v. el docstring de `Ronda`).
    #
    # El MISSATGE diu QUINA volta bloqueja i les DUES sortides que té. Deia només «tanca-la», i
    # això amagava la sortida normal: la volta es tanca **entregant-la** (FIT-13), i «tancar» sol
    # no té cap porta pròpia. Qui el llegeix és l'usuari, al toast de «+ Nova ronda».
    oberta = _ronda_oberta(model)
    if oberta is not None:
        raise RondaError(f'Aquest model ja té una ronda oberta: entrega o tanca la '
                         f'R{oberta.seq} primer.')

    # M1-bis · FIT-4 — LA VOLTA NOVA NEIX AMB EL JOC DE L'ANTERIOR. El que el cridador demana
    # s'HI SUMA, no el substitueix: la proposta replicada no es pot «desmarcar», perquè FIT-4 diu
    # que les replicades «es poden NO EXECUTAR» — la manera de no fer-ne una és no fer-la, no
    # treure-la de la volta. L'ordre és el de la volta anterior, i els extres van al final.
    anterior = _ronda_anterior(model)
    # DECISIÓ 2 — la feina del BUIT entra a aquesta volta. Es resol ABANS de res perquè decideix
    # què NO cal replicar: si al buit algú ja ha obert el `pom`, la volta ja té el seu `pom` —i és
    # feina VIVA, potser començada. Replicar-lo a sobre en fabricaria un segon de buit al costat
    # del que s'està fent, i `tasca_vigent` hauria de triar entre dos germans dins de la mateixa
    # volta. L'adopció mana sobre la proposta: el que ja existeix no es proposa.
    adoptables = list(tasques_del_buit(model, anterior))
    # ⚠️ QUI TAPA LA PROPOSTA I QUI NO. Un extra `off_recipe` nascut al buit **s'adopta igual**
    # —és feina d'aquesta volta—, però **no tapa** la rèplica del seu code: `off_recipe` vol dir
    # literalment «fora de la recepta», i que algú hagi fet un extra de `pom` no vol dir que la
    # volta no hagi de fer el `pom` de la recepta. És la mateixa frontera que `_NO_ES_REPLICA`,
    # llegida des de l'altre costat.
    codes_adoptats = {t.task_type.code for t in adoptables if not t.off_recipe}

    replicats = codes_a_replicar(anterior)
    codes = [c for c in dict.fromkeys(replicats + demanats) if c not in codes_adoptats]
    if not codes and not adoptables:
        raise RondaError('Una ronda sense cap tasca no és una ronda.')

    tipus = {t.code: t for t in TaskType.objects.filter(code__in=codes, active=True)}
    # Un code DEMANAT que no existeix o és inactiu segueix sent un rebuig dur: el cridador s'ha
    # equivocat i ha de saber-ho. Un code REPLICAT que ha quedat inactiu des de la volta anterior
    # NO pot tombar l'obertura —ningú no ha fet res malament, el catàleg ha canviat sota els peus—:
    # s'omet i es diu quins, perquè ometre en silenci seria pitjor que no replicar.
    desconeguts = [c for c in demanats if c not in tipus]
    if desconeguts:
        raise RondaError(f"Tipus de tasca inexistents o inactius: {', '.join(desconeguts)}.")
    omesos = [c for c in codes if c not in tipus]
    codes = [c for c in codes if c in tipus]
    if not codes and not adoptables:
        raise RondaError('Cap de les tasques de la volta anterior segueix activa al catàleg.')

    # Les MARES surten de la VOLTA ANTERIOR, una per code (v. `mare_homologa`). Abans es
    # demanaven a `tasca_vigent`, que aquí sempre cau a la regla 2 i retorna la tasca base —o
    # sigui la de la R1—, de manera que la cadena saltava les voltes intermèdies a partir de la R3.
    #
    # 🚩 EL MODEL LLEGAT, I ÉS UNA DESVIACIÓ DECLARADA DE LA LLETRA DE LA DECISIÓ 3. Quan el model
    # **no té CAP volta** —tota la seva feina és `ronda=NULL`, que és la forma de tots els models
    # d'abans del canvi de llei— no hi ha «volta anterior» contra què resoldre, i aplicar
    # `mare=NULL` literalment **esborraria una genealogia que era CORRECTA**: la feina històrica
    # ÉS la volta anterior d'aquell model, encara que no tingui fila. La decisió prohibeix
    # «encadenar amb voltes MÉS VELLES», i aquí no n'hi ha cap per saltar-se.
    #
    # Per això, i només en aquest cas, es conserva el criteri d'abans (`tasca_vigent`, que hi cau
    # a la regla 2 i retorna precisament la tasca base). Amb la llei nova aquest camí s'apaga sol:
    # tot model que rebi un gest ja neix amb R1. Tres tests d'M1 (`test_la_filla_apunta_a_la_mare_
    # homonima`) el fixen, i van ser el que va enxampar la regressió.
    mares = {code: (mare_homologa(anterior, code) if anterior is not None
                    else tasca_vigent(model, code))
             for code in codes}

    with transaction.atomic():
        seguent = (Ronda.objects.filter(model=model)
                   .order_by('-seq').values_list('seq', flat=True).first() or 1) + 1
        ronda = Ronda.objects.create(model=model, seq=seguent, motiu=motiu)
        # L'adopció NOMÉS escriu `ronda`. Ni `motiu`, ni `mare`, ni `order`, ni l'estat: la tasca
        # ja existeix, ja té la seva història i potser ja s'ha treballat. Entrar a una volta no és
        # néixer-hi, i reescriure-li la genealogia seria inventar que la va proposar la ronda.
        if adoptables:
            ModelTask.objects.filter(pk__in=[t.pk for t in adoptables]).update(ronda=ronda)
        base_order = ModelTask.objects.filter(model=model).count()
        for i, code in enumerate(codes):
            tt = tipus[code]
            ModelTask.objects.create(
                model=model, task_type=tt, order=base_order + i,
                status='Pending', origen='ad_hoc',
                ronda=ronda, mare=mares[code], motiu=motiu,
                assignee=profile,
                estimated_minutes=lookup_estimated_minutes(model, tt))
        # M4 · FIT-12 — DINS o FORA del numeral de la comanda, decidit aquí i no més tard. Dins
        # de la transacció a posta: una volta que existeix sense veredicte seria una volta que
        # el comercial no pot classificar, i el veredicte depèn del `seq` que s'acaba de
        # reservar. El tècnic no se n'assabenta: `obrir_ronda` no retorna res de nou i la cara
        # del Pla de treball no ha canviat ni una línia.
        resol_desbordament(ronda)
    # Informatiu per a la porta HTTP: quins codes de la volta anterior s'han quedat pel camí.
    ronda._codes_replicats = [c for c in replicats if c in tipus]
    ronda._codes_omesos = omesos
    ronda._codes_adoptats = sorted({t.task_type.code for t in adoptables})
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


#: M1 · FIT-6 — l'ordre en què es tanquen les tasques vives d'una ronda. NO és cosmètic:
#: cada entrada a `InProgress` dispara `_aplica_exclusio_tecnic`, que pausa la resta de feina
#: oberta del MATEIX tècnic. Tancant primer el que ja és `InProgress` (un sol salt) i deixant les
#: `Pending` per al final, l'exclusió no es dispara contra tasques que aquest mateix bucle
#: acabarà de tancar de totes maneres, i el log no s'omple de pauses que ningú no ha fet.
_ORDRE_TANCAMENT = {'InProgress': 0, 'Paused': 1, 'Pending': 2}


def tanca_tasques_de_la_ronda(ronda, profile):
    """FIT-6 · Tanca TOTES les tasques vives d'una ronda. Retorna les que ha tancat.

    🔑 **PEL MECANISME ÚNIC, MAI UN `UPDATE` DIRECTE.** Cada tasca passa per `transition_task`
    perquè la màquina d'estats VEGI el gest: si es tanquessin amb un `update(status='Done')`, no
    hi hauria ni tram tancat, ni fila a `TaskTransition`, ni crida a `record_actual_time` — o
    sigui que el Welford no veuria el tancament d'una tasca que SÍ que s'havia treballat, i el
    log diria que aquella feina segueix viva.

    ⚠️ **I PER AIXÒ SÓN DOS SALTS.** `ALLOWED` no té `Pending→Done` ni `Paused→Done`, i això és
    una decisió d'Agus (Patró C, 28/07, fixada a `test_stop_encadenat`): el Stop sobre una tasca
    pausada és **play+stop encadenat**, dues transicions legals en un sol gest. Aquí s'aplica el
    mateix patró en comptes d'obrir cap camí nou a la taula — la màquina d'estats no es toca.

    🔑 **EL WELFORD NO S'ENVERINA, I NO CAL CAP GUARD NOU PER A AIXÒ.** El tram que obre el salt
    de cortesia neix `consulta=False` (`services_c._open_timer`) i, en tancar-se sense cap
    `escriptura_at`, `_close_open_timer` el marca **`consulta=True`** — o sigui que queda fora de
    `TRAMS_SANS` (`services_i`) i no suma ni un minut. Per a una tasca `Pending` que ningú no ha
    tocat, `_real_minutes` segueix sent 0 i `record_actual_time` surt pel seu propi
    `if x <= 0: return None`: **cap mostra**. Per a una que sí que s'ha treballat, els seus trams
    reals hi són igualment i la mostra és la de sempre. La llei d'Agus —«el Welford no mesura res
    d'una tasca que no s'ha executat»— ja la imposava el sistema; aquí només s'hi confia.

    `profile` és OBLIGATORI quan hi ha feina viva: `TimerEntrada.tecnic` és NOT NULL i, sobretot,
    tancar la feina d'algú és un ACTE i ha de tenir autor al log.
    """
    from .services_c import TransitionError, transition_task

    vives = [t for t in ronda.tasques.exclude(status='Done').select_related('task_type')]
    if not vives:
        return []
    if profile is None:
        raise RondaError('Cal un tècnic per tancar les tasques vives de la ronda.')

    tancades = []
    for task in sorted(vives, key=lambda t: (_ORDRE_TANCAMENT.get(t.status, 9), t.pk)):
        task.refresh_from_db()          # l'exclusió del tècnic pot haver-la mogut en una volta
        if task.status == 'Done':
            continue
        try:
            if task.status != 'InProgress':
                transition_task(task, 'InProgress', profile)
                task.refresh_from_db()
            transition_task(task, 'Done', profile)
        except TransitionError as e:
            raise RondaError(f'No s\'ha pogut tancar la tasca {task.pk} '
                             f'({task.task_type.code}): {e}')
        tancades.append(task)
    return tancades


def tancar_ronda(ronda, *, profile=None):
    """Tanca una ronda (`tancada_el = ara`) I TOTA la feina que hi penja. Idempotent.

    M1 · FIT-6 — fins avui aquesta funció només segellava la data i deixava les tasques vives de
    la volta exactament on eren. El resultat era feina que ja no era de ningú: en tancar-se la
    ronda, `tasca_vigent` torna a resoldre per la PREVISTA (regla 2), de manera que aquelles
    `Pending`/`Paused` seguien obertes al kanban i al Pla **sense que cap porta hi tornés a
    entrar mai**. Ara la volta es tanca sencera.

    🔒 **CAP TASCA MIGRA A LA RONDA SEGÜENT** (FIT-6). Tancar no és traspassar: la feina que no
    s'ha fet en aquesta volta es tanca en aquesta volta, i si s'ha de refer, es refà obrint-ne
    una de nova (`obrir_ronda` / `obrir_correccio`), que és el que deixa la genealogia escrita.

    `profile`: qui tanca. Només és obligatori si queda feina viva — tancar una ronda ja acabada
    (o ja tancada) segueix sent un no-op que no necessita autor.
    """
    from django.db import transaction
    from django.utils import timezone

    from .models import Ronda

    with transaction.atomic():
        tancades = tanca_tasques_de_la_ronda(ronda, profile)
        Ronda.objects.filter(pk=ronda.pk, tancada_el__isnull=True).update(
            tancada_el=timezone.now())
    ronda.refresh_from_db()
    ronda._tasques_tancades = tancades    # informatiu per a qui ho vulgui dir a la resposta
    return ronda


# ── M1 · FIT-1 + FIT-13 · L'ENTREGA ──────────────────────────────────────────

class EntregaError(Exception):
    """Rebuig d'una operació d'entrega (la ronda ja en té una, l'ok ja s'ha informat…)."""


def informar_entrega(ronda, *, destinatari, profile, descripcio='', data=None):
    """Declara que una ronda s'ha ENTREGAT. **I amb això la tanca** (FIT-13).

    🔑 **L'ESTAT «ENTREGADA» ES DECLARA, NO ES DEDUEIX.** `ronda_lliurable` seguirà responent el
    que sempre ha respost —«ja hi és tot?»— i es queda com el senyal PREVI que permet a la UI
    oferir el gest («ja es pot marcar entregable»). El que diu que una volta s'ha entregat és
    aquesta fila, escrita per una persona que ho sap perquè ho ha fet.

    🔒 **L'ACTE TANCA LA RONDA, I EN LA MATEIXA TRANSACCIÓ** (FIT-13 · M1). Entregar i deixar la
    volta oberta seria declarar que s'ha enviat una cosa que encara s'està fent; i fer-ho en dues
    transaccions deixaria, el dia que la segona fallés, una entrega informada sobre una ronda
    viva —l'estat que precisament no ha d'existir. O hi són totes dues o no hi és cap.
    Com que tancar la ronda tanca la seva feina viva (FIT-6), `profile` és sempre obligatori
    aquí: entregar és un acte, i el seu autor és qui també signa aquell tancament.

    Retorna l'`Entrega` creada.
    """
    from django.db import transaction

    from .models import Entrega

    if profile is None:
        raise EntregaError('Cal un perfil per informar una entrega.')
    destinatari = (destinatari or '').strip()
    if not destinatari:
        raise EntregaError('Una entrega sense destinatari no diu res: cal dir a qui s\'ha entregat.')
    if Entrega.objects.filter(ronda=ronda).exists():
        raise EntregaError('Aquesta ronda ja té una entrega informada; una volta s\'entrega un cop.')

    with transaction.atomic():
        entrega = Entrega.objects.create(
            ronda=ronda, destinatari=destinatari, descripcio=(descripcio or '').strip(),
            qui_informa=profile, **({'data': data} if data is not None else {}))
        tancar_ronda(ronda, profile=profile)
    return entrega


def informar_ok_client(entrega, *, profile, data_ok=None):
    """El client ha dit que li ha arribat bé. Senyal MANUAL i POSTERIOR (FIT-1).

    No es dedueix de res i no té cap efecte sobre la ronda: quan arriba, la ronda ja fa estona
    que és tancada. S'informa **un sol cop**: és un fet, no un interruptor.
    """
    from django.utils import timezone

    if profile is None:
        raise EntregaError('Cal un perfil per informar l\'OK del client.')
    if entrega.data_ok is not None:
        raise EntregaError('L\'OK del client d\'aquesta entrega ja estava informat.')
    entrega.data_ok = data_ok or timezone.now()
    entrega.qui_informa_ok = profile
    entrega.save(update_fields=['data_ok', 'qui_informa_ok'])
    return entrega


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


# ── T3 · D-2 · EL CRONO DE TEMPS DECLARAT ────────────────────────────────────
#
# `declara_temps` (F1.7) cobreix «ja he treballat, apunta-ho». El que faltava és l'altra meitat:
# «començo ARA i encara no sé quant durarà». La maqueta aprovada
# (`ops/maquetes/maqueta_temps_declarat_i_modal_v1.html`) ho fixa en quatre gestos —engegar,
# aturar, acceptar/descartar, corregir— i en una frase que mana sobre tot el disseny:
#
#     «Viu al servidor: sobreviu a recarregar, canviar de pestanya i tancar el navegador.»
#
# Per això el crono NO és un cronòmetre de navegador que després desa: és un `TimerEntrada` OBERT
# de debò, amb `origen='declarat'` des del primer segon. El navegador només el pinta. I per això
# s'engega per la MATEIXA porta que tota la resta (`transition_task`): així hereta l'exclusió
# un-InProgress-per-tècnic, el log de transicions i l'auto-assignació, en comptes de tenir-ne una
# versió pròpia que caldria mantenir en paral·lel.

def _tram_obert(task):
    """El tram obert d'una tasca, o None. Invariant del sistema: n'hi ha ≤1."""
    from .models import TimerEntrada
    return TimerEntrada.objects.filter(model_task=task, fi__isnull=True, actiu=True).first()


def engega_crono_declarat(task, profile):
    """Obre un tram DECLARAT viu sobre una tasca externa. Idempotent.

    Merita el model, com el primer batec d'escriptura fa a les internes (D-10): un model que
    comença per una tasca externa també ha de meritar, i aquí no hi haurà cap escriptura que
    ho dispari. La meritació passa per `_meritar_si_cal`, que ja porta el guard d'idempotència
    — les tres funcions de facturació no es toquen.

    Retorna el `TimerEntrada` obert.
    """
    from .models import TimerEntrada
    from .services_batec import _meritar_si_cal
    from .services_c import TransitionError, _open_timer, transition_task

    if task.task_type.tipus != 'Externa-lliure':
        raise TempsDeclaratError(
            'El crono declarat és per a tasques Externa-lliure: les internes es mesuren soles.')
    if profile is None:
        raise TempsDeclaratError('Cal un perfil de tècnic per engegar el crono.')

    obert = _tram_obert(task)
    if obert is not None:
        # Ja n'hi ha un de viu: engegar dos cops no obre dos trams. Si era MESURAT (ve d'una
        # porta antiga), es queda com està: convertir-lo seria reescriure temps ja comptat.
        return obert

    if task.status != 'InProgress':
        try:
            transition_task(task, 'InProgress', profile, origen=TimerEntrada.ORIGEN_DECLARAT)
        except TransitionError as e:
            raise TempsDeclaratError(str(e))
        tram = _tram_obert(task)
    else:
        # En curs i sense tram obert: l'anomalia que el guard ja anota i no pot recollir. Aquí es
        # tapa obrint el tram que falta, sense inventar cap transició que la màquina prohibeix.
        tram = _open_timer(task, profile, origen=TimerEntrada.ORIGEN_DECLARAT)

    _meritar_si_cal(task)
    return tram


def atura_crono_declarat(task, profile):
    """Tanca la sessió declarada i deixa la tasca PAUSADA, amb el tram a punt de confirmar.

    La tasca no es tanca mai per aquí: acabar-la és un gest propi (T4). El tram queda desat —
    el crono viu al servidor— i el tècnic encara pot descartar-lo o corregir-lo.

    Retorna el `TimerEntrada` tancat.
    """
    from .models import TimerEntrada
    from .services_c import TransitionError, transition_task

    tram = _tram_obert(task)
    if tram is None:
        raise TempsDeclaratError('Aquesta tasca no té cap crono en marxa.')
    if tram.origen != TimerEntrada.ORIGEN_DECLARAT:
        raise TempsDeclaratError('El tram obert no és declarat: atura\'l pel transport normal.')

    if task.status == 'InProgress':
        try:
            transition_task(task, 'Paused', profile)   # tanca el tram amb la seva durada
        except TransitionError as e:
            raise TempsDeclaratError(str(e))
    tram.refresh_from_db()
    return tram


def descarta_tram_declarat(tram):
    """Esborra un tram declarat ja tancat: «no queda cap temps registrat per aquesta sessió».

    Només trams DECLARATS i només tancats: esborrar temps mesurat seria esborrar evidència, i
    esborrar-ne un de viu seria una altra manera d'aturar-lo.
    """
    from .models import TimerEntrada

    if tram.origen != TimerEntrada.ORIGEN_DECLARAT:
        raise TempsDeclaratError('Només es descarta temps declarat.')
    if tram.fi is None:
        raise TempsDeclaratError('Atura el crono abans de descartar-lo.')
    tram.delete()


def corregeix_tram_declarat(tram, *, minuts=None, inici=None, fi=None):
    """Reescriu la mesura d'un tram declarat: durada O BÉ franja, mai les dues (D-2).

    És la mateixa regla que `declara_temps` i es valida igual, perquè és la mateixa pregunta feta
    en un altre moment: quant hi has dedicat de debò.
    """
    import datetime as _dt

    from django.utils import timezone

    from .models import TimerEntrada
    from .services_i import MAX_MINUTS_TRAM

    if tram.origen != TimerEntrada.ORIGEN_DECLARAT:
        raise TempsDeclaratError('Només es corregeix temps declarat.')
    if tram.fi is None:
        raise TempsDeclaratError('Atura el crono abans de corregir-lo.')

    te_minuts = minuts is not None
    te_franja = inici is not None or fi is not None
    if te_minuts == te_franja:
        raise TempsDeclaratError('Cal {minuts} O BÉ {inici, fi}, mai els dos ni cap dels dos.')

    if te_minuts:
        try:
            minuts = int(minuts)
        except (TypeError, ValueError):
            raise TempsDeclaratError('`minuts` ha de ser un enter.')
        fi = tram.fi or timezone.now()
        inici = fi - _dt.timedelta(minutes=minuts)
    else:
        if inici is None or fi is None:
            raise TempsDeclaratError('La franja necessita `inici` I `fi`.')
        if fi <= inici:
            raise TempsDeclaratError('`fi` ha de ser posterior a `inici`.')
        minuts = int((fi - inici).total_seconds() // 60)

    if minuts <= 0:
        raise TempsDeclaratError('Un tram declarat ha de durar com a mínim un minut.')
    if minuts > MAX_MINUTS_TRAM:
        raise TempsDeclaratError(
            f'Un tram declarat no pot superar {MAX_MINUTS_TRAM} minuts ({MAX_MINUTS_TRAM // 60} h).')

    tram.inici, tram.fi, tram.minuts = inici, fi, minuts
    tram.save(update_fields=['inici', 'fi', 'minuts'])
    return tram
