"""V2-DADA · cens dels defaults de sizing/target que no quadren amb el que serveixen (READ-ONLY).

    backend/venv/bin/python manage.py shell < scripts_tmp/v2_cens_defaults.py

Tres preguntes, per als DOS tenants:

  A · `SizingProfile` amb un TARGET que el seu `SizeSystem` no declara servir.
      El perfil diu «aquesta família, per a aquest públic, es dimensiona amb aquest sistema» i el
      sistema diu que aquell públic no és seu. Un dels dos menteix, i no hi ha cap `clean()` ni
      cap constraint que ho impedeixi (`pom/models.py:1480-1533`).

  B · ITEMS amb sizing per defecte (V1 `base_size_definition` / `grading_rule_set`, V2
      `ItemBaseSet`) i quants TARGETS serveix la seva família. La llei d'Agus del 06/08: el
      sizing per defecte només val on és UNÍVOC.

  C · Coherència interna del default: el sistema de la talla base i el del joc de regles.
"""
from django_tenants.utils import schema_context

TENANTS = ('fhort', 'los')


def targets_de_la_familia(gt, SizingProfile):
    return sorted({p.target.codi for p in SizingProfile.objects.filter(garment_type=gt)
                   .select_related('target') if p.target_id})


for schema in TENANTS:
    with schema_context(schema):
        from fhort.pom.models import SizingProfile, ItemBaseSet
        from fhort.tasks.models import GarmentTypeItem

        print(f'\n{"═" * 108}\nTENANT «{schema}»\n{"═" * 108}')

        # ── A ────────────────────────────────────────────────────────────────────────────
        print('\nA · SizingProfile amb target FORA dels targets del seu sistema')
        print(f'{"perfil":>7} {"família":26} {"activa":6} {"target":16} {"sistema":16} '
              f'{"targets del sistema"}')
        incoh = 0
        for p in (SizingProfile.objects
                  .select_related('target', 'size_system', 'garment_type').order_by('id')):
            if not (p.target_id and p.size_system_id):
                continue
            del_sistema = sorted(t.codi for t in p.size_system.targets.all())
            if not del_sistema or p.target.codi in del_sistema:
                continue
            incoh += 1
            gt = p.garment_type
            print(f'{p.id:>7} {(gt.codi_client if gt else "—"):26} '
                  f'{("sí" if getattr(gt, "actiu", True) else "NO"):6} {p.target.codi:16} '
                  f'{p.size_system.codi:16} {",".join(del_sistema)}')
        print(f'   → {incoh} perfils incoherents de {SizingProfile.objects.count()}')

        # ── B i C ────────────────────────────────────────────────────────────────────────
        print('\nB · ITEMS amb sizing per defecte · quants públics serveix la seva família')
        print(f'{"item":>5} {"família":24} {"codi item":22} {"base":6} {"sist.base":14} '
              f'{"joc":>4} {"sist.joc":14} {"targets família"}')
        amb_default = 0
        for it in (GarmentTypeItem.objects
                   .select_related('garment_type', 'base_size_definition__size_system',
                                   'grading_rule_set__size_system').order_by('id')):
            if not (it.base_size_definition_id or it.grading_rule_set_id):
                continue
            amb_default += 1
            tg = targets_de_la_familia(it.garment_type, SizingProfile)
            bsd = it.base_size_definition
            grs = it.grading_rule_set
            marca = '🔴' if len(tg) > 1 else ('🟢' if len(tg) == 1 else '⚪')
            print(f'{it.id:>5} {it.garment_type.codi_client:24} {it.code[:22]:22} '
                  f'{(bsd.etiqueta if bsd else "—"):6} '
                  f'{(bsd.size_system.codi if bsd else "—"):14} '
                  f'{(grs.id if grs else "—"):>4} '
                  f'{(grs.size_system.codi if grs and grs.size_system_id else "—"):14} '
                  f'{marca} {len(tg)}: {",".join(tg) or "—"}')
        print(f'   → {amb_default} items amb default de {GarmentTypeItem.objects.count()}')
        print(f'   → ItemBaseSet (V2): {ItemBaseSet.objects.count()}')

        print('\nC · el sistema de la talla base i el del joc, quadren?')
        for it in GarmentTypeItem.objects.select_related(
                'base_size_definition__size_system', 'grading_rule_set__size_system'):
            bsd, grs = it.base_size_definition, it.grading_rule_set
            if bsd and grs and grs.size_system_id and bsd.size_system_id != grs.size_system_id:
                print(f'   ✗ item {it.id} {it.code}: base={bsd.size_system.codi} '
                      f'joc={grs.size_system.codi}')
        print('   (cap línia ✗ = tots quadren)')
