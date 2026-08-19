"""F3.3 · cens dels trams OBERTS abans/després de la cron del guard.

Verifica explícitament les dues coses que la cron NO ha de tocar:
  · cap tram amb BATEC VIU (últim senyal per sota del llindar)
  · cap tram DECLARAT (T3: no tenen batec per definició; matar-los seria pausar el tècnic a
    mitja feina externa per no haver fet res que aquí es pugui veure)

Ús:  python manage.py shell < scripts_tmp/f33_cens_trams_oberts.py
"""
from django.utils import timezone
from django_tenants.utils import get_tenant_model, schema_context

from fhort.tasks.models import ModelTask, TimerEntrada

LLINDAR = 40   # el mateix que `pausa_tasques_oblidades`

for tenant in get_tenant_model().objects.exclude(schema_name='public').order_by('schema_name'):
    with schema_context(tenant.schema_name):
        ara = timezone.now()
        oberts = list(TimerEntrada.objects.filter(fi__isnull=True, actiu=True)
                      .select_related('model_task', 'model_task__task_type')
                      .order_by('inici'))
        print(f'== {tenant.schema_name} · {len(oberts)} tram/s oberts ==')
        venc_mesurat = venc_declarat = viu = no_inprogress = 0
        for tr in oberts:
            segell = tr.last_heartbeat or tr.inici
            edat = (ara - segell).total_seconds() / 60
            task = tr.model_task
            declarat = tr.origen == TimerEntrada.ORIGEN_DECLARAT
            venc = edat > LLINDAR
            marca = []
            if declarat:
                marca.append('DECLARAT·INTOCABLE')
            if task.status != 'InProgress':
                marca.append(f'tasca={task.status}·fora')
            marca.append('VENÇUT' if venc else 'BATEC VIU·INTOCABLE')
            print(f'  timer={tr.pk:<5} task={task.pk:<5} {task.task_type.code:<14} '
                  f'origen={tr.origen:<9} edat={edat:>9.1f} min  {" · ".join(marca)}')
            if task.status != 'InProgress':
                no_inprogress += 1
            elif not venc:
                viu += 1
            elif declarat:
                venc_declarat += 1
            else:
                venc_mesurat += 1
        orfes = (ModelTask.objects.filter(status='InProgress')
                 .exclude(timers__fi__isnull=True, timers__actiu=True).count())
        print(f'  -- LA CRON N\'HA DE PAUSAR: {venc_mesurat}')
        print(f'  -- INTOCABLES: {viu} amb batec viu · {venc_declarat} declarats vençuts '
              f'· {no_inprogress} sobre tasca no-InProgress')
        print(f'  -- anomalia anotada: {orfes} tasca/ques En curs sense cap tram obert')
