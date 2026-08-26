"""M5 · EL RETROACTIU DE LA R1 — el passat guanya la seva primera volta.

## Què fa, i per què existeix

Des d'M1-bis (FIT-4) **la R1 neix sola del primer gest de treball**. La feina anterior al canvi
de llei es va quedar amb `ronda = NULL` i **cap fila `Ronda`**, perquè M1-bis va declarar una
PROHIBICIÓ DE BACKFILL explícita: inventar voltes com a efecte secundari d'una migració seria
escriure història. La prohibició deia, literalment, «fins al retroactiu de M5».

**Això és el retroactiu de M5.** És l'ÚNICA vegada que la prohibició s'aixeca, i s'aixeca com a
**ACTE DECLARAT** —un script que es llegeix, es valida en sec i s'aplica amb guarda— i no com a
migració silenciosa.

## Les quatre lleis que el governen

1. **FIT-4 · l'univers.** Entren els models amb ALMENYS UNA `ModelTask`. Un model amb 0 tasques
   **no rep R1**: mai ha tingut cap gest de treball, i fabricar-li una volta seria inventar-la.
2. **FIT-1 · les R1 retroactives neixen OBERTES** (`tancada_el = NULL`) i **sense cap `Entrega`**.
   L'`Entrega` registra un fet que ha passat, i fabricar-ne una diria que aquella feina es va
   enviar quan ningú no ho ha declarat mai. Conseqüència buscada: **cap model canvia a
   «Entregats»** pel retroactiu.
3. **Adopció total.** La R1 adopta **TOTES** les `ModelTask` amb `ronda = NULL` del model. Aquí
   ja no hi ha «buit» ni «pre-primera» (les nocions d'M1-bis, que servien per repartir feina
   entre voltes existents): **tot el passat és R1**.
4. **Només s'escriu `ronda`.** Ni `motiu`, ni `mare`, ni estats, ni timers, ni Welford, ni cap
   `TaskTransition`. **És OMPLIMENT, no un gest**: la tasca ja existeix, ja té la seva història i
   potser ja s'ha treballat.

## La data de la volta

`Ronda.oberta_el` és `auto_now_add`, o sigui que la fila neix amb l'hora d'AVUI — que seria
mentida per a feina de fa dues setmanes. Es corregeix amb un `UPDATE` posterior al **mínim
`created_at` de les tasques que adopta**: el moment en què aquella volta va començar de debò.
(`update()` i no `save()`: `auto_now_add` només dispara a l'INSERT, però `updated_at`/`auto_now`
d'altres camps no s'ha de moure.)

## Ús

    # 1) EN SEC — no escriu res. Genera la llista que Agus valida.
    venv/bin/python ../ops/retroactius/retroactiu_r1_m5.py

    # 2) APLICAR — amb la GUARDA de recompte exacte de la llista validada.
    venv/bin/python ../ops/retroactius/retroactiu_r1_m5.py --apply \
        --espera-models 5 --espera-tasques 18

**Idempotent**: la segona execució troba l'univers buit i surt amb 0 canvis (i la guarda no
dispara: un univers buit és l'estat d'arribada, no una discrepància).
"""
import argparse
import os
import sys

import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                + '/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fhort.settings')
django.setup()

from django.db import connection, transaction                          # noqa: E402
from django_tenants.utils import get_tenant_model, schema_context      # noqa: E402


def univers(schema):
    """Els models que reben R1, amb el que adoptaran. Lectura PURA.

    L'univers és «models amb almenys una `ModelTask` de `ronda = NULL`». Un model que ja tingui
    voltes però amb feina solta pendent d'adoptar **també hi entra**: la seva feina sense volta
    és passat igual, i la llei d'adopció no distingeix. A `fhort` avui no n'hi ha cap (tots cinc
    són pre-llei purs, cap fila `Ronda`), però el codi no ho pot donar per fet.
    """
    from fhort.models_app.models import Model
    from fhort.tasks.models import ModelTask, Ronda

    ids = sorted(set(ModelTask.objects.filter(ronda__isnull=True)
                     .values_list('model_id', flat=True)))
    files = []
    for m in Model.objects.filter(pk__in=ids).order_by('pk'):
        tasques = list(ModelTask.objects.filter(model=m, ronda__isnull=True)
                       .select_related('task_type').order_by('created_at', 'id'))
        rondes = list(Ronda.objects.filter(model=m).order_by('seq'))
        estats = {}
        for t in tasques:
            estats[t.status] = estats.get(t.status, 0) + 1
        files.append({
            'model': m, 'tasques': tasques, 'rondes_existents': rondes,
            'data_inici': min(t.created_at for t in tasques),
            'estats': estats,
        })
    return files


def board_ara(fila):
    """L'estat al board ABANS del retroactiu, per la lectura VELLA (l'excepció pre-llei d'M3).

    Reprodueix `views_b.kanban_state` per poder dir, a la llista de validació, si algun model
    es MOU de columna. La feina viva mana; sense feina viva i sense cap volta, l'excepció el
    posava a `done` (4a columna).
    """
    e = fila['estats']
    if e.get('InProgress'):
        return 'open'
    if e.get('Paused'):
        return 'paused'
    if e.get('Pending'):
        return 'pending'
    return 'done' if not fila['rondes_existents'] else 'pending'


def board_despres(fila):
    """L'estat al board DESPRÉS: la R1 hi és i és OBERTA (FIT-1), o sigui que la 4a columna
    —que és un FET D'ENTREGA— ja no la pot reclamar. Sense feina viva, cau a `pending`."""
    e = fila['estats']
    if e.get('InProgress'):
        return 'open'
    if e.get('Paused'):
        return 'paused'
    if e.get('Pending'):
        return 'pending'
    return 'pending'          # volta OBERTA i sense entrega → mai «done»


def informe(schema, files):
    linies = []
    tot_t = sum(len(f['tasques']) for f in files)
    linies.append(f"### Tenant `{schema}` — **{len(files)} models · {tot_t} tasques**\n")
    if not files:
        linies.append('_Cap model pre-llei: res a fer._\n')
        return linies, 0, 0
    linies.append('| model | codi | tasques que adopta | data_inici proposada | board ara → després |')
    linies.append('|---|---|---|---|---|')
    for f in files:
        m = f['model']
        codes = ' · '.join(f'`{t.task_type.code}`({t.status})' for t in f['tasques'])
        mou = '→' if board_ara(f) == board_despres(f) else '→ ⚠️'
        linies.append(
            f"| **{m.pk}** | `{m.codi_intern}` · {m.nom_prenda or '—'} | **{len(f['tasques'])}** — {codes} "
            f"| `{f['data_inici']:%Y-%m-%d %H:%M}` | `{board_ara(f)}` {mou} `{board_despres(f)}` |")
    linies.append('')
    return linies, len(files), tot_t


def aplica(schema, files, espera_models, espera_tasques):
    """Escriu, dins d'UNA transacció, amb la guarda de recompte exacte al davant."""
    from django.utils import timezone                                  # noqa: F401
    from fhort.tasks.models import ModelTask, Ronda

    n_m, n_t = len(files), sum(len(f['tasques']) for f in files)

    # ── LA GUARDA. Un univers BUIT no és cap discrepància: és l'estat d'arribada (idempotència).
    if n_m == 0:
        print(f'[{schema}] univers buit → 0 canvis (idempotent)')
        return 0, 0
    if (n_m, n_t) != (espera_models, espera_tasques):
        raise SystemExit(
            f'[{schema}] 🛑 AVORTAT SENSE ESCRIURE. La guarda esperava '
            f'{espera_models} models / {espera_tasques} tasques i n\'he trobat {n_m}/{n_t}. '
            f"L'univers ha canviat des del dry-run validat: torna a fer-lo en sec i revalida.")

    creades = adoptades = 0
    with transaction.atomic():
        for f in files:
            m = f['model']
            # 🔒 `get_or_create` i no `create`: la unique `(model, seq)` és qui garanteix que no
            # en neixi una segona, i si una execució anterior va morir a mig camí, aquesta
            # reaprofita la fila que va deixar en lloc de petar.
            ronda, nova = Ronda.objects.get_or_create(
                model=m, seq=1,
                defaults={'motiu': Ronda.MOTIU_NOVA_MOSTRA})
            creades += 1 if nova else 0
            # LA DATA: `auto_now_add` va posar l'hora d'ara. Es corregeix al moment en què
            # aquella volta va començar de debò. `update()` perquè no dispari cap `auto_now`.
            Ronda.objects.filter(pk=ronda.pk).update(oberta_el=f['data_inici'], tancada_el=None)
            # L'ADOPCIÓ: **només `ronda`**. Un `update()` de queryset no toca `updated_at`
            # (`auto_now` no dispara), que és exactament el que volem: adoptar no és editar.
            n = ModelTask.objects.filter(pk__in=[t.pk for t in f['tasques']]).update(ronda=ronda)
            adoptades += n
            # M4 · FIT-12 — la volta neix classificada com qualsevol altra. No és un gest ni una
            # transició: és el mateix veredicte que `obrir_ronda` escriu en obrir, i deixar-lo
            # sense resoldre crearia una població de `Ronda` que M4 no fabrica enlloc. Amb 0
            # comandes assignades a staging el resultat és (False, None, None) per a totes.
            from fhort.tasks.services_r import resol_desbordament
            ronda.refresh_from_db()
            resol_desbordament(ronda)
    print(f'[{schema}] R1 creades={creades} · tasques adoptades={adoptades}')
    return creades, adoptades


def verifica(schema):
    """Verificació POST **per SQL contra la taula**, no contra el que el script creu haver fet."""
    with connection.cursor() as c:
        c.execute('SET search_path TO %s', [schema])
        c.execute('SELECT count(*) FROM tasks_modeltask WHERE ronda_id IS NULL')
        orfes = c.fetchone()[0]
        c.execute("""SELECT count(*) FROM models_app_model m
                     WHERE EXISTS (SELECT 1 FROM tasks_modeltask t WHERE t.model_id = m.id)
                       AND NOT EXISTS (SELECT 1 FROM tasks_ronda r WHERE r.model_id = m.id)""")
        pre_llei = c.fetchone()[0]
        c.execute('SELECT count(*) FROM tasks_ronda WHERE seq = 1')
        r1 = c.fetchone()[0]
        c.execute('SELECT count(*) FROM tasks_ronda WHERE seq = 1 AND tancada_el IS NOT NULL')
        r1_tancades = c.fetchone()[0]
        c.execute("""SELECT count(*) FROM tasks_entrega e
                     JOIN tasks_ronda r ON r.id = e.ronda_id WHERE r.seq = 1""")
        r1_entregues = c.fetchone()[0]
    print(f'[{schema}] POST · ModelTask sense ronda={orfes} · models PRE-LLEI={pre_llei} · '
          f'R1={r1} (tancades={r1_tancades} · amb Entrega={r1_entregues})')
    return {'orfes': orfes, 'pre_llei': pre_llei, 'r1': r1,
            'r1_tancades': r1_tancades, 'r1_entregues': r1_entregues}


def main():
    p = argparse.ArgumentParser(description='M5 · retroactiu de la R1')
    p.add_argument('--apply', action='store_true', help='escriu (per defecte: en sec)')
    p.add_argument('--espera-models', type=int, help='guarda: models esperats (amb --apply)')
    p.add_argument('--espera-tasques', type=int, help='guarda: tasques esperades (amb --apply)')
    p.add_argument('--tenant', help='només aquest schema (per defecte: tots)')
    a = p.parse_args()

    if a.apply and (a.espera_models is None or a.espera_tasques is None):
        raise SystemExit('🛑 --apply exigeix --espera-models i --espera-tasques (la guarda del '
                         'dry-run validat). Sense guarda no s\'escriu res.')

    T = get_tenant_model()
    schemes = ([a.tenant] if a.tenant
               else [t.schema_name for t in T.objects.exclude(schema_name='public')
                     .order_by('schema_name')])

    md = ['# M5 · RETROACTIU DE LA R1 — llista de validació (DRY-RUN)', '',
          '> Generat per `ops/retroactius/retroactiu_r1_m5.py` (en sec, cap escriptura).', '']
    tot_m = tot_t = 0
    for schema in schemes:
        with schema_context(schema):
            files = univers(schema)
            linies, n_m, n_t = informe(schema, files)
            md += linies
            tot_m += n_m
            tot_t += n_t
            if a.apply:
                # La guarda es mesura PER TENANT amb el total: només un tenant pot tenir univers.
                aplica(schema, files, a.espera_models, a.espera_tasques)
                verifica(schema)
            else:
                print('\n'.join(linies))
    md += ['---', '',
           f'**TOTAL: {tot_m} models · {tot_t} tasques.**', '',
           'Guarda per a l\'apply:', '',
           '```',
           f'venv/bin/python ../ops/retroactius/retroactiu_r1_m5.py --apply \\',
           f'    --espera-models {tot_m} --espera-tasques {tot_t}',
           '```', '']
    if not a.apply:
        desti = (os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                 + '/docs/ordres/RETROACTIU_R1_STAGING_DRYRUN.md')
        with open(desti, 'w', encoding='utf-8') as f:
            f.write('\n'.join(md))
        print(f'\n📄 llista desada a {desti}')
    print(f'\nTOTAL: {tot_m} models · {tot_t} tasques.')


if __name__ == '__main__':
    main()
