"""M1 · BANC SINTÈTIC DE RONDES — tres models nous, creats pel camí normal del sistema.

⚠️ **AQUEST SCRIPT ESCRIU**, i per això no toca res que ja existeixi: fabrica MODELS NOUS amb
prefix `[QA-M1]` i treballa només sobre ells. **Mai el 1383** (banc del fil motor), **mai el
golden 162**, mai un model real.

**IDEMPOTENT**: la guarda és `codi_intern` amb prefix `QA-M1-`. Si els models ja hi són, no en
duplica cap i només reimprimeix la taula del banc.

🔑 **LES RONDES ES CREEN PEL CAMÍ NORMAL** (`services_r.obrir_ronda`), no per inserció directa,
i **els estats es mouen per `transition_task`**. El banc ha de provar el camí real: una ronda
inserida a mà no tindria ni tasques filles, ni `mare`, ni fila a `TaskTransition`, i el
tancament forçat de FIT-6 s'hi provaria contra una cosa que el sistema no fabrica mai.

    venv/bin/python ../ops/qa/banc_m1_rondes.py               (des de backend/)
    venv/bin/python ../ops/qa/banc_m1_rondes.py --remunta     (esborra el banc i el refà)
"""
import os
import sys

import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                + '/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fhort.settings')
django.setup()

from django_tenants.utils import schema_context                    # noqa: E402

from fhort.accounts.models import UserProfile                      # noqa: E402
from fhort.models_app.models import Model                          # noqa: E402
from fhort.tasks.models import (Customer, GarmentTypeItem, ModelTask,  # noqa: E402
                                Ronda, TimerEntrada)
from fhort.tasks.services_c import transition_task                 # noqa: E402
from fhort.tasks.services_r import (obrir_ronda, ronda_del_gest,   # noqa: E402
                                    tancar_ronda)
from fhort.tasks.services_g import lookup_estimated_minutes        # noqa: E402
from fhort.tasks.models import TaskType                            # noqa: E402

PREFIX = 'QA-M1-'
TENANT = 'fhort'

#: (sufix, nom, codes de la R1, estat final per code, obre_r2). None = es queda Pending.
#: M1-bis — la R1 ja NO s'obre amb `obrir_ronda`: **neix sola del primer gest**. El banc ho
#: reprodueix creant les tasques com ho fan els cinc punts de producte (amb `ronda_del_gest`),
#: perquè un banc que obrís la R1 a mà provaria un camí que el sistema ja no recorre.
BANC = [
    ('0001', '[QA-M1] Estats variats',
     ['pom', 'tech_sheet', 'grading', 'sample_check'],
     {'pom': 'Done', 'tech_sheet': 'InProgress', 'grading': 'Paused', 'sample_check': None},
     False),
    ('0002', '[QA-M1] Tot fet',
     ['pom', 'tech_sheet'],
     {'pom': 'Done', 'tech_sheet': 'Done'},
     False),
    ('0003', '[QA-M1] Verge sense tasques', [], {}, False),
    # M1-bis · FIT-4 — la R1 treballada i tancada, i la R2 oberta SENSE demanar cap code:
    # el joc ha de sortir replicat de la R1 tot sol.
    ('0004', '[QA-M1] R1 tancada + R2 replicada',
     ['pom', 'tech_sheet'],
     {'pom': 'Done', 'tech_sheet': 'Done'},
     True),
]

#: M2 · CODA-BIS — EL MODEL LLEGAT: feina amb `ronda=NULL` i **cap fila `Ronda`**.
#:
#: 🚨 **Aquest és l'ÚNIC cas del banc que NO es pot muntar pel camí normal, i és a posta.** Des
#: d'M1-bis qualsevol gest de treball fa néixer la R1 (`ronda_del_gest`), o sigui que el codi viu
#: **ja no sap fabricar** aquesta forma. Però és la que tenen els models d'abans del canvi de llei
#: —4 dels 7 models amb tasques de `fhort` al tancament d'M2— i seguirà sent-ho fins al retroactiu
#: de M5. Sense ell, la branca del PLA PLA (i la seva barra de progrés global) no es pot veure mai.
#:
#: Les tasques es creen amb `ronda=None` explícit i els estats es mouen per `transition_task`, que
#: no toca cap `Ronda` (cens d'M1-bis §1.2). No s'esquiva cap llei: es reprodueix una població.
LLEGAT = ('0005', '[QA-M1] Llegat sense volta (pre-llei)',
          ['pom', 'tech_sheet'],
          {'pom': 'Done', 'tech_sheet': None})


def _tecnic_sense_feina_oberta():
    """Un perfil que NO tingui cap tram obert.

    No és una precaució decorativa: entrar a `InProgress` dispara `_aplica_exclusio_tecnic`, que
    tanca els trams oberts d'aquell tècnic a QUALSEVOL altra tasca i les pausa. Muntar el banc
    amb el perfil d'algú que està treballant li pausaria la feina de debò.
    """
    ocupats = set(TimerEntrada.objects.filter(fi__isnull=True, actiu=True)
                  .values_list('tecnic_id', flat=True))
    lliure = UserProfile.objects.exclude(pk__in=ocupats).order_by('pk').first()
    if lliure is None:
        raise SystemExit('Cap UserProfile sense trams oberts: no munto el banc per no pausar '
                         'la feina de ningú.')
    return lliure


#: 🚨 L'EXCLUSIÓ D'UN-INPROGRESS-PER-TÈCNIC ÉS **GLOBAL**, NO PER MODEL. `_aplica_exclusio_tecnic`
#: (D-6) tanca els trams oberts d'aquell tècnic a QUALSEVOL altra tasca de QUALSEVOL model i les
#: pausa. Muntar el banc model a model deixava el banc **sense cap tasca en curs**: la `InProgress`
#: del model 0001 la pausava la primera `→InProgress` del model 0002 (mesurat, dos muntatges
#: seguits, tots dos amb `tech_sheet:Paused` on s'esperava `InProgress`).
#:
#: Per això el muntatge va en DUES PASSADES: primer tot el que acaba `Done`/`Paused` de tots els
#: models, i **al final** les que han de quedar en curs. No és cap truc per esquivar la llei: és
#: la llei, i és per això que el banc no pot tenir dues `InProgress` del mateix tècnic.
_ESTATS_PRIMERA_PASSADA = ('Done', 'Paused')


def _crea_tasca(model, code, prof):
    """Crea una tasca com ho fa un GEST DE TREBALL, i per tant fa néixer la R1 si cal.

    És la mateixa línia que els cinc punts de producte: `ronda=ronda_del_gest(model)`. El banc no
    la pot esquivar —si la creés amb `ronda=None` provaria un model que el sistema ja no fabrica.
    """
    tt = TaskType.objects.get(code=code, active=True)
    return ModelTask.objects.create(
        model=model, task_type=tt, order=ModelTask.objects.filter(model=model).count(),
        status='Pending', origen='prevista',
        estimated_minutes=lookup_estimated_minutes(model, tt),
        ronda=ronda_del_gest(model))


def _porta_estat(task, estat, prof):
    """Porta una tasca fins a `estat` NOMÉS per transicions legals d'`ALLOWED`."""
    if estat is None:
        return
    transition_task(task, 'InProgress', prof)
    task.refresh_from_db()
    if estat in ('Done', 'Paused'):
        transition_task(task, estat, prof)


#: M2 · minuts sintètics per tasca del banc, en l'ordre en què es munten. Prou diferents entre
#: si perquè la revisió visual distingeixi una columna ben alineada d'una que copia el veí.
_MINUTS_BANC = [74, 27, 66, 18]


def _dona_temps_real(model, prof):
    """M2 · dona TEMPS CONSOLIDAT als trams del banc, perquè les dues cares tinguin què pintar.

    🔑 **PER QUÈ CAL.** Els trams que el banc fabrica es tanquen dins del mateix segon i sense cap
    escriptura, i `_close_open_timer` els marca `consulta=True` —«s'hi ha entrat, no s'hi ha
    treballat»—, que és exactament el que `TRAMS_SANS` exclou. Resultat: tot el banc sortia a
    **0h 00m** i amb la columna «Qui» buida. Amb això, la graella del Registre i les capçaleres
    de volta del Pla es poden contrastar amb el mockup als eixos temps i qui, que si no queden
    muts.

    🔒 **NO SIMULA CAP BATEC.** S'escriuen els camps del TRAM directament (`inici`, `minuts`,
    `escriptura_at`, `consulta`) i prou. Cridar el batec d'escriptura de producte dispararia la
    MERITACIÓ SaaS i l'event a `public` —v. `_merita_sintetic`—, que és el que aquest banc no ha
    de tocar mai.
    """
    from datetime import timedelta

    tocats = 0
    trams = (TimerEntrada.objects
             .filter(model_task__model=model, fi__isnull=False)
             .order_by('pk'))
    for i, tram in enumerate(trams):
        minuts = _MINUTS_BANC[i % len(_MINUTS_BANC)]
        tram.inici = tram.fi - timedelta(minutes=minuts)
        tram.minuts = minuts
        tram.escriptura_at = tram.inici + timedelta(minutes=1)
        tram.consulta = False
        tram.tecnic = tram.tecnic or prof
        tram.save(update_fields=['inici', 'minuts', 'escriptura_at', 'consulta', 'tecnic'])
        tocats += 1
    return tocats


def _merita_sintetic(model):
    """M2 · dona al model del banc l'ALBARÀ que el Registre d'activitat exigeix per ensenyar-se.

    🔒 **I NO PASSA PEL CAMÍ NORMAL, A POSTA.** La meritació de producte (`services_c._meritar_model`,
    disparada pel batec d'escriptura) emet `model_consumption_started` a `public`, i aquell event
    ÉS la unitat facturable del SaaS (`backoffice/recurring_service` en fa el `.count()` del
    període). Meritar un model sintètic pel camí normal ficaria feina inventada a la facturació
    d'algú. Aquí s'escriu **només la fila local** —`ConsumptionRecord` + la marca del model—, que
    és exactament el que la porta `/albara/` mira (`merited: False` si no n'hi ha cap), i **cap
    event surt del tenant**.

    Idempotent: si el model ja té albarà, no en fa cap altre.
    """
    from django.utils import timezone

    from fhort.models_app.models import ConsumptionRecord

    if getattr(model, 'consumption_record', None) is not None:
        return False
    ara = timezone.now()
    Model.objects.filter(pk=model.pk).update(consumption_started_at=ara)
    ConsumptionRecord.objects.create(
        model=model, code_snapshot=model.codi_intern, name_snapshot=model.nom_prenda or '',
        period=ara.strftime('%Y-%m'), merited_at=ara)
    return True


def desmunta():
    """Esborra NOMÉS els models del banc. La guarda és el prefix i no hi ha cap altra via.

    Existeix perquè el banc és sintètic i remuntar-lo és més honest que reparar-lo a mà: si un
    fum l'ha consumit (una entrega tanca la ronda i no es pot desfer), el que toca és tornar-lo
    a fabricar sencer.
    """
    from fhort.models_app.models import ConsumptionRecord

    qs = Model.objects.filter(codi_intern__startswith=PREFIX)
    codis = list(qs.values_list('codi_intern', flat=True))
    ModelTask.objects.filter(model__codi_intern__startswith=PREFIX).delete()
    Ronda.objects.filter(model__codi_intern__startswith=PREFIX).delete()
    # L'albarà sintètic d'M2 se'n va amb el banc: si es quedés, `reconcile_consumption` el
    # veuria com una fila d'un model que ja no existeix.
    ConsumptionRecord.objects.filter(model__codi_intern__startswith=PREFIX).delete()
    qs.delete()
    print(f'desmuntats: {codis or "(cap)"}')


def munta():
    prof = _tecnic_sense_feina_oberta()
    customer = Customer.objects.order_by('pk').first()
    item = GarmentTypeItem.objects.order_by('pk').first()
    if customer is None or item is None:
        raise SystemExit('Falta Customer o GarmentTypeItem al tenant: banc no muntable.')

    creats, en_curs, amb_r2 = [], [], []
    for sufix, nom, codes, estats, obre_r2 in BANC:
        codi = PREFIX + sufix
        model = Model.objects.filter(codi_intern=codi).first()
        if model is not None:
            creats.append((model, False))
            continue
        model = Model.objects.create(
            codi_intern=codi, codi_tenant='FTT', any=2026, temporada='SS',
            sequencial=int(sufix), customer=customer, garment_type_item=item, nom_prenda=nom)
        for code in codes:                     # el PRIMER d'aquests gestos fa néixer la R1
            t = _crea_tasca(model, code, prof)
            estat = estats.get(code)
            if estat in _ESTATS_PRIMERA_PASSADA:
                _porta_estat(t, estat, prof)
            elif estat == 'InProgress':
                en_curs.append(t)
        if obre_r2:
            amb_r2.append(model)
        creats.append((model, True))

    # ⚠️ Va ABANS de la segona passada, i pel mateix motiu que ella existeix: els seus
    # `_porta_estat` passen per `InProgress`, i `_aplica_exclusio_tecnic` és GLOBAL —
    # muntat després, pausava la `InProgress` del model 0001 (mesurat).
    # CINQUENA (M2 · CODA-BIS) — el model LLEGAT, sense cap volta. V. la nota de `LLEGAT`.
    sufix, nom, codes, estats = LLEGAT
    codi = PREFIX + sufix
    model = Model.objects.filter(codi_intern=codi).first()
    if model is None:
        model = Model.objects.create(
            codi_intern=codi, codi_tenant='FTT', any=2026, temporada='SS',
            sequencial=int(sufix), customer=customer, garment_type_item=item, nom_prenda=nom)
        for code in codes:
            tt = TaskType.objects.get(code=code, active=True)
            t = ModelTask.objects.create(
                model=model, task_type=tt,
                order=ModelTask.objects.filter(model=model).count(),
                status='Pending', origen='prevista',
                estimated_minutes=lookup_estimated_minutes(model, tt),
                ronda=None)                     # ← la forma pre-llei, i no la fa cap gest
            _porta_estat(t, estats.get(code), prof)
        creats.append((model, True))
    else:
        creats.append((model, False))

    # SEGONA PASSADA — v. la nota de `_ESTATS_PRIMERA_PASSADA`.
    for t in en_curs:
        _porta_estat(t, 'InProgress', prof)

    # TERCERA — tancar la R1 i obrir la R2 SENSE codes: el joc ha de sortir replicat sol.
    for model in amb_r2:
        r1 = Ronda.objects.filter(model=model, tancada_el__isnull=True).first()
        if r1 is not None:
            tancar_ronda(r1, profile=prof)
        obrir_ronda(model, Ronda.MOTIU_NOVA_MOSTRA, [], profile=prof)

    # QUARTA (M2) — l'ALBARÀ. Sense `ConsumptionRecord` la porta `/albara/` respon
    # `merited: False` i el Registre d'activitat no ensenya res: el banc d'M1 no en tenia cap i
    # la meitat B d'M2 no s'hi podia provar. Se'n donen a TOTS els models amb tasques; el verge
    # es queda sense, que és el control negatiu de l'estat «encara no ha iniciat activitat».
    for model, _nou in creats:
        if ModelTask.objects.filter(model=model).exists():
            _dona_temps_real(model, prof)
            _merita_sintetic(model)
    return prof, creats


def taula(creats):
    print(f"\n{'MODEL':<28} {'RONDA':<12} {'TASQUES (code:estat)'}")
    print('-' * 96)
    for model, nou in creats:
        rondes = list(Ronda.objects.filter(model=model).order_by('seq'))
        rlab = ' · '.join(f'R{r.seq}{"" if r.tancada_el is None else "✓"}'
                          for r in rondes) or '—'
        tasques = ModelTask.objects.filter(model=model).select_related('task_type').order_by('order')
        cos = ', '.join(f'{t.task_type.code}:{t.status}' for t in tasques) or '(cap)'
        print(f"{model.codi_intern:<28} {rlab:<12} {cos}   {'[NOU]' if nou else '[ja hi era]'}")
    print('-' * 96)


if __name__ == '__main__':
    with schema_context(TENANT):
        if '--remunta' in sys.argv:
            desmunta()
        prof, creats = munta()
        print(f"tenant={TENANT} · tècnic del muntatge = UserProfile {prof.pk} "
              f"({getattr(prof, 'nom_complet', '?')})")
        taula(creats)
        nous = sum(1 for _, n in creats if n)
        print(f"\n{nous} model(s) creats, {len(creats) - nous} ja hi eren. "
              f"Rondes del banc: {Ronda.objects.filter(model__codi_intern__startswith=PREFIX).count()}")
