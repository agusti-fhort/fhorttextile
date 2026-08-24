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
from fhort.tasks.services_r import obrir_ronda                     # noqa: E402

PREFIX = 'QA-M1-'
TENANT = 'fhort'

#: (sufix de codi, nom, codes de la ronda, estat final per code). None = es queda Pending.
BANC = [
    ('0001', '[QA-M1] Estats variats',
     ['pom', 'tech_sheet', 'grading', 'sample_check'],
     {'pom': 'Done', 'tech_sheet': 'InProgress', 'grading': 'Paused', 'sample_check': None}),
    ('0002', '[QA-M1] Tot fet',
     ['pom', 'tech_sheet'],
     {'pom': 'Done', 'tech_sheet': 'Done'}),
    ('0003', '[QA-M1] Verge sense tasques', [], {}),
]


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


def _porta_estat(task, estat, prof):
    """Porta una tasca fins a `estat` NOMÉS per transicions legals d'`ALLOWED`."""
    if estat is None:
        return
    transition_task(task, 'InProgress', prof)
    task.refresh_from_db()
    if estat in ('Done', 'Paused'):
        transition_task(task, estat, prof)


def desmunta():
    """Esborra NOMÉS els models del banc. La guarda és el prefix i no hi ha cap altra via.

    Existeix perquè el banc és sintètic i remuntar-lo és més honest que reparar-lo a mà: si un
    fum l'ha consumit (una entrega tanca la ronda i no es pot desfer), el que toca és tornar-lo
    a fabricar sencer.
    """
    qs = Model.objects.filter(codi_intern__startswith=PREFIX)
    codis = list(qs.values_list('codi_intern', flat=True))
    ModelTask.objects.filter(model__codi_intern__startswith=PREFIX).delete()
    Ronda.objects.filter(model__codi_intern__startswith=PREFIX).delete()
    qs.delete()
    print(f'desmuntats: {codis or "(cap)"}')


def munta():
    prof = _tecnic_sense_feina_oberta()
    customer = Customer.objects.order_by('pk').first()
    item = GarmentTypeItem.objects.order_by('pk').first()
    if customer is None or item is None:
        raise SystemExit('Falta Customer o GarmentTypeItem al tenant: banc no muntable.')

    creats, en_curs = [], []
    for sufix, nom, codes, estats in BANC:
        codi = PREFIX + sufix
        model = Model.objects.filter(codi_intern=codi).first()
        if model is not None:
            creats.append((model, False))
            continue
        model = Model.objects.create(
            codi_intern=codi, codi_tenant='FTT', any=2026, temporada='SS',
            sequencial=int(sufix), customer=customer, garment_type_item=item, nom_prenda=nom)
        if codes:
            ronda = obrir_ronda(model, Ronda.MOTIU_NOVA_MOSTRA, codes, profile=prof)
            for t in ronda.tasques.select_related('task_type'):
                estat = estats.get(t.task_type.code)
                if estat in _ESTATS_PRIMERA_PASSADA:
                    _porta_estat(t, estat, prof)
                elif estat == 'InProgress':
                    en_curs.append(t)
        creats.append((model, True))

    # SEGONA PASSADA — v. la nota de `_ESTATS_PRIMERA_PASSADA`.
    for t in en_curs:
        _porta_estat(t, 'InProgress', prof)
    return prof, creats


def taula(creats):
    print(f"\n{'MODEL':<28} {'RONDA':<12} {'TASQUES (code:estat)'}")
    print('-' * 96)
    for model, nou in creats:
        r = Ronda.objects.filter(model=model).order_by('-seq').first()
        rlab = f'seq {r.seq} {"oberta" if r.tancada_el is None else "TANCADA"}' if r else '—'
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
