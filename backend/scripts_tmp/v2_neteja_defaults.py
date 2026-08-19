"""V2-DADA · esborra els defaults de catàleg FALSOS (decisió d'Agus, 06/08 vespre).

    EN SEC:   backend/venv/bin/python manage.py shell < scripts_tmp/v2_neteja_defaults.py
    APLICA: APLICA=1 backend/venv/bin/python manage.py shell < scripts_tmp/v2_neteja_defaults.py

IDEMPOTENT: el que ja no hi és, no es torna a comptar. Es pot córrer dues vegades.

── EL CRITERI (Agus, 06/08 vespre) ─────────────────────────────────────────────────────────
**FALS s'esborra · AMBIGU es documenta i es resol amb domini davant.** Un default ambigu no és
un default dolent: esborrar-lo per higiene trencaria funcionalitat vigent.

1 · `SizingProfile` amb un TARGET que el seu propi `SizeSystem` NO declara servir → **FALS**.
    El perfil diu «aquesta família, per a aquest públic, es dimensiona amb aquest sistema» i el
    sistema diu que aquell públic no és seu. S'esborra el PERFIL i no s'amplien els `targets`
    del sistema: ampliar-los seria inventar-se un fet sobre el sistema per fer quadrar l'altre.
    (Cap `clean()` ni cap constraint ho impedeix avui: `pom/models.py:1480-1533`.)

2 · Item `shirt_woven` (id 4): apunta a `ALPHA_EU_M` (home) i la seva família `BUTTONED_TOPS`
    serveix TEEN_BOY i WOMAN — **MAN no hi és**. És contradictori, no ambigu. I no perd res:
    la seva fila `ItemBaseSet` (V2) ja diu el mateix, i V2 mana sobre V1 a
    `resolve_item_base_set` (`models_app/views.py:1237`), amb el fallback V1 només si l'item té
    ≤1 set. S'esborra el punter V1.

NO ES TOQUEN (ambigus, documentats al report): items 5 `blouse`, 10 `top_sleeveless` i 58
`baby_dress`. Apunten al sistema d'un públic que la seva família SÍ serveix, i no tenen cap
`ItemBaseSet` que els cobreixi: treure'ls el default els deixaria sense sembra de talla base.
Qui ha de dir quins públics serveix de debò cada família és el catàleg v4, amb la Montse.
"""
import os

from django.db import transaction
from django_tenants.utils import schema_context

SCHEMA = 'fhort'          # `los` no en té cap (0 perfils, 0 items amb default): no s'hi entra.
APLICA = os.environ.get('APLICA') == '1'
ITEM_SHIRT_WOVEN = 4


def perfils_falsos(SizingProfile):
    """Els que reclamen un públic que el seu sistema nega. Idempotent per construcció: es
    recalcula cada vegada, i el que ja no hi és no hi surt."""
    fora = []
    for p in (SizingProfile.objects
              .select_related('target', 'size_system', 'garment_type').order_by('id')):
        if not (p.target_id and p.size_system_id):
            continue
        del_sistema = {t.codi for t in p.size_system.targets.all()}
        # Un sistema que no declara CAP target no nega res: no s'hi entra.
        if not del_sistema or p.target.codi in del_sistema:
            continue
        fora.append(p)
    return fora


with schema_context(SCHEMA):
    from fhort.pom.models import SizingProfile, ItemBaseSet
    from fhort.tasks.models import GarmentTypeItem

    print(f'{"═" * 96}\nV2-DADA · defaults FALSOS de catàleg · tenant «{SCHEMA}» · '
          f'{"APLICA" if APLICA else "EN SEC"}\n{"═" * 96}')

    falsos = perfils_falsos(SizingProfile)
    print(f'\n1 · SizingProfile FALSOS: {len(falsos)} (de {SizingProfile.objects.count()})')
    for p in falsos:
        gt = p.garment_type
        print(f'   · perfil {p.id:>4} · {(gt.codi_client if gt else "—"):24} '
              f'{"[activa]" if getattr(gt, "actiu", True) else "[desactivada]":14} '
              f'target={p.target.codi:16} sistema={p.size_system.codi:14} '
              f'(el sistema serveix: {",".join(sorted(t.codi for t in p.size_system.targets.all()))})')

    it = GarmentTypeItem.objects.filter(pk=ITEM_SHIRT_WOVEN).first()
    te_default = bool(it and (it.base_size_definition_id or it.grading_rule_set_id))
    print(f'\n2 · item {ITEM_SHIRT_WOVEN} `shirt_woven` · default V1 present: '
          f'{"SÍ" if te_default else "no (ja net)"}')
    if te_default:
        sets = ItemBaseSet.objects.filter(garment_type_item=it)
        print(f'   · base={getattr(it.base_size_definition, "etiqueta", None)} '
              f'joc={it.grading_rule_set_id} · ItemBaseSet (V2) que el cobreixen: {sets.count()}')
        for s in sets:
            print(f'     - set {s.id}: sistema={s.size_system.codi} '
                  f'base={getattr(s.base_size_definition, "etiqueta", None)} '
                  f'fit={getattr(s.fit_type, "codi", None)}')
        if sets.count() == 0:
            print('   🛑 SENSE cap ItemBaseSet: NO es toca (deixaria l\'item sense sembra).')

    if not APLICA:
        print('\n🟡 EN SEC: no s\'ha escrit res. Torna-hi amb APLICA=1.')
    else:
        with transaction.atomic():
            n = 0
            for p in falsos:
                p.delete()
                n += 1
            print(f'\n   · SizingProfile esborrats: {n}')
            if te_default and ItemBaseSet.objects.filter(garment_type_item=it).exists():
                it.base_size_definition = None
                it.grading_rule_set = None
                it.save(update_fields=['base_size_definition', 'grading_rule_set'])
                print('   · item 4: punter V1 retirat (el cobreix el seu ItemBaseSet)')
            elif te_default:
                print('   · item 4: NO tocat (no té ItemBaseSet que el cobreixi)')
        print('\n🟢 APLICAT (dins d\'una sola transacció).')

    # ── VERIFICACIÓ ───────────────────────────────────────────────────────────────────────
    print(f'\n{"═" * 96}\nVERIFICACIÓ\n{"═" * 96}')
    resten = perfils_falsos(SizingProfile)
    print(f'   {"✓" if not resten else "✗"} SizingProfile falsos que resten: {len(resten)}')
    print(f'   · SizingProfile totals: {SizingProfile.objects.count()}')
    it = GarmentTypeItem.objects.filter(pk=ITEM_SHIRT_WOVEN).first()
    print(f'   · item 4 · base={it.base_size_definition_id} joc={it.grading_rule_set_id} '
          f'· ItemBaseSet={ItemBaseSet.objects.filter(garment_type_item=it).count()}')
    amb_default = GarmentTypeItem.objects.filter(
        base_size_definition__isnull=False).count() + GarmentTypeItem.objects.filter(
        base_size_definition__isnull=True, grading_rule_set__isnull=False).count()
    print(f'   · items amb algun default V1: {amb_default} '
          f'(els 3 AMBIGUS que es queden a posta: 5 blouse · 10 top_sleeveless · 58 baby_dress)')
