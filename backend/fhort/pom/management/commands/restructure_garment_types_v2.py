"""Pas previ al Pas 5 — Reestructuració de Garment Types a 17 famílies + 57 items.

Opció 2: CREAR net + DESACTIVAR el vell. Regles dures:
  - TOT dins una sola transaction.atomic() → rollback total si qualsevol pas falla.
  - IDEMPOTENT: update_or_create / get_or_create per codi. Re-executar no duplica.
  - NO esborra CAP fila (ni GarmentType, ni POM-map, ni SizingProfile, ni item).
    Només CREA i DESACTIVA (actiu=False / active=False). Així evita PROTECT i CASCADE.

Capes:
  - GarmentTypeGlobal (public + rèplica al tenant): catàleg canònic de les 17 famílies.
  - GarmentType (tenant): les 17 famílies, FK a la rèplica global.
  - GarmentTypeItem (tenant): els 57 items (peça concreta) dins cada família.
  - TaskTimeEstimate (tenant): 9 estimacions de temps per item (matriu temps), perfil L/M/P.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django_tenants.utils import schema_context

TENANT = 'fhort'

# Ordre canònic dels 9 TaskType de la matriu de temps (coincideix amb els codes reals).
TASK_ORDER = ['pattern_digit', 'pattern_cad', 'pattern_hand', 'scaling',
              'marking', 'tech_sheet', 'bom', 'pom', 'grading']

# Perfils de temps (minuts) en l'ordre de TASK_ORDER.
PROFILES = {
    'L': [30, 20, 90, 10, 10, 40, 30, 30, 15],    # 275
    'M': [60, 40, 120, 15, 15, 40, 30, 30, 15],   # 365
    'P': [120, 180, 360, 30, 30, 80, 60, 60, 30],  # 950
}

# 17 famílies: (codi, nom_en, grup, descripcio)
FAMILIES = [
    ('BUTTONED_TOPS', 'Buttoned Tops', 'TOPS',
     "Teixit pla (woven). Obertura frontal completa amb vista/tapeta, canesú a l'esquena, "
     "pinces d'ajust i màniga sastre o de puny construït amb clapa."),
    ('JERSEY_TOPS', 'Jersey Tops', 'TOPS',
     "Gènere de punt circular (knit jersey). Patró geomètric simple de tronc tancat (sense "
     "pinces de pit) i màniga de corona baixa muntada en pla."),
    ('KNIT_SWEATERS', 'Knit Sweaters', 'TOPS',
     "Punt rectilini (fully fashioned). Peces tancades teixides malla a malla amb menguats a "
     "les cises i colls per evitar tallar el teixit."),
    ('KNIT_CARDIGANS', 'Knit Cardigans', 'TOPS',
     "Punt rectilini. Peces obertes davanteres amb tapeta de botonadura teixida integrada i "
     "remats en canalé."),
    ('SWEATSHIRTS_MIDLAYERS', 'Sweatshirts & Midlayers', 'TOPS',
     "Volum folgat en pelfa o polar. Ús prioritari de màniga ranglan per treure la costura de "
     "l'espatlla i millorar el confort tèrmic."),
    ('TAILORED_PANTS', 'Tailored & Rigid Pants', 'BOTTOMS',
     "Arquitectura de quatre peces (dos davants amb línia d'aplom i dos darreres amb fons "
     "d'assentament). Requereix pretina postissa, bragueta construïda i fons de butxaca."),
    ('LEGGINGS_TIGHTS', 'Leggings & Tights', 'BOTTOMS',
     "Teixit elàstic bidireccional. Sovint elimina la costura lateral exterior. Ajust anatòmic "
     "per pressió amb pretina alta elàstica, sense cremalleres."),
    ('SKIRTS', 'Skirts', 'BOTTOMS',
     "Estructures buides que cobreixen des de la cintura sense separació de cames, definides pel "
     "buidat de pinces de maluc o línies de capa."),
    ('DRESSES', 'Dresses', 'DRESSES',
     "Unió estructural de cos superior i faldilla en una sola línia d'aplom vertical, amb "
     "tancaments llargs posteriors o laterals."),
    ('ADULT_JUMPSUITS', 'Adult Jumpsuits & Overalls', 'DRESSES',
     "Unió de cos superior i pantaló per a adults. Control crític de la línia de tir total per a "
     "la flexió del tronc en seure."),
    ('UNDERWEAR', 'Underwear', 'UNDERWEAR',
     "Peces de mínim teixit i màxima elasticitat. Patrons anatòmics d'ajust a l'engonal amb "
     "gomes interiors i costures planes (flatlock)."),
    ('BRA_SHAPEWEAR', 'Bra & Shapewear', 'UNDERWEAR',
     "Patronatge d'alta precisió mil·limètrica basat en contorn i copa del pit o modelatge "
     "d'alta compressió. Allotjament per a cèrcols (aros) o escumes preformades."),
    ('SWIMWEAR', 'Swimwear', 'SWIMWEAR',
     "Patrons sense folgances per a teixits de licra que absorbeixen aigua sense deformar-se. "
     "Goma elàstica d'alta resistència al clor a totes les obertures."),
    ('STRUCTURED_JACKETS', 'Structured Jackets', 'OUTERWEAR',
     "Terceres capes estructurades. Costadillos verticals (sense costura lateral), màniga sastre "
     "de dues peces, entreteixits (fusing) i espatlleres."),
    ('HEAVY_OUTERWEAR', 'Heavy Outerwear', 'OUTERWEAR',
     "Terceres capes de gran volum amb índexs de folgança elevats, llargs per sota del maluc, "
     "per a teixits pesants o encoixinats."),
    ('BABY_ONEPIECES', 'Baby & Kids One-Pieces', 'DRESSES',
     "Peces de cos sencer amb patronatge adaptat a l'ergonomia infantil: sobredimensionat de tir "
     "per encabir el bolquer i obertures inferiors amb gafets."),
    ('BABY_SEPARATES', 'Baby & Kids Separates', 'TOPS',
     "Peces de nadó i infantil de tall separat (no integrals). Patronatge ergonòmic infantil amb "
     "obertures amplies i teixits suaus de punt."),
]

# 57 items: (family_codi, code, name, complexity_order, perfil)
ITEMS = [
    ('BUTTONED_TOPS', 'shirt_woven', 'Camisa (woven)', 1, 'M'),
    ('BUTTONED_TOPS', 'blouse', 'Blusa', 2, 'M'),
    ('BUTTONED_TOPS', 'overshirt', 'Sobrecamisa', 3, 'M'),
    ('BUTTONED_TOPS', 'uniform_shirt', "Camisola d'uniforme", 4, 'M'),

    ('JERSEY_TOPS', 't_shirt', 'Samarreta / T-shirt', 1, 'L'),
    ('JERSEY_TOPS', 'polo', 'Polo', 2, 'L'),
    ('JERSEY_TOPS', 'top_sleeveless', 'Top de tirants', 3, 'L'),
    ('JERSEY_TOPS', 'vest_top', 'Vest / Tank top', 3, 'L'),

    ('KNIT_SWEATERS', 'sweater', 'Jersei (coll alt, rodó o en V)', 1, 'L'),
    ('KNIT_SWEATERS', 'twinset', 'Twin-set (jersei + top)', 2, 'L'),

    ('KNIT_CARDIGANS', 'cardigan', 'Càrdigan / jaqueta de punt', 1, 'L'),
    ('KNIT_CARDIGANS', 'knit_gilet', 'Armilla de punt', 2, 'L'),

    ('SWEATSHIRTS_MIDLAYERS', 'hoodie', 'Dessuadora (amb/sense caputxa)', 1, 'M'),
    ('SWEATSHIRTS_MIDLAYERS', 'fleece_jacket', "Jaqueta polar d'abric", 2, 'P'),

    ('TAILORED_PANTS', 'trousers', 'Pantaló estructurat', 1, 'M'),
    ('TAILORED_PANTS', 'chino', 'Chino', 1, 'M'),
    ('TAILORED_PANTS', 'jeans', 'Jeans (denim)', 1, 'M'),
    ('TAILORED_PANTS', 'shorts', 'Pantaló curt / bermuda', 2, 'M'),
    ('TAILORED_PANTS', 'tracksuit_pant', 'Xandall', 2, 'M'),
    ('TAILORED_PANTS', 'workwear_pant', 'Treball / uniforme', 2, 'M'),

    ('LEGGINGS_TIGHTS', 'leggings', 'Malla / legging', 1, 'L'),
    ('LEGGINGS_TIGHTS', 'culotte_cycling', 'Culotte (amb badana)', 2, 'L'),

    ('SKIRTS', 'skirt_straight', 'Faldilla recta / tub', 1, 'L'),
    ('SKIRTS', 'skirt_volume', 'Faldilla volumètrica', 2, 'M'),

    ('DRESSES', 'dress_simple', 'Vestit pla simple', 1, 'M'),
    ('DRESSES', 'shirt_dress', 'Vestit camiser', 2, 'M'),
    ('DRESSES', 'dress_fancy', 'Vestit fantasia', 2, 'M'),
    ('DRESSES', 'dress_structured', 'Vestit estructurat', 3, 'M'),

    ('ADULT_JUMPSUITS', 'jumpsuit', 'Mono (vestir, mecànic o EPI)', 1, 'M'),
    ('ADULT_JUMPSUITS', 'dungarees', 'Peto (amb pitet i tirants)', 2, 'M'),
    ('ADULT_JUMPSUITS', 'playsuit', 'Playsuit / romper adult', 2, 'M'),

    ('UNDERWEAR', 'briefs_man', 'Calçotets (slip/boxer)', 1, 'L'),
    ('UNDERWEAR', 'briefs_woman', 'Braguetes (culotte/tanga)', 2, 'L'),
    ('UNDERWEAR', 'bodysuit', 'Body interior', 3, 'L'),
    ('UNDERWEAR', 'thermal_top', 'Samarreta interior tèrmica', 4, 'L'),
    ('UNDERWEAR', 'pyjama_set', 'Pijama (conjunt)', 2, 'L'),

    ('BRA_SHAPEWEAR', 'bra', 'Sostenidor', 1, 'L'),
    ('BRA_SHAPEWEAR', 'shapewear', 'Faixa modeladora', 2, 'L'),
    ('BRA_SHAPEWEAR', 'corset', 'Corset estructural', 3, 'L'),

    ('SWIMWEAR', 'swimsuit', "Banyador d'una peça", 1, 'L'),
    ('SWIMWEAR', 'bikini', 'Bikini (combo top+bragueta)', 2, 'L'),
    ('SWIMWEAR', 'swim_shorts', "Bàixador d'home", 3, 'L'),

    ('STRUCTURED_JACKETS', 'blazer', 'Americana / blazer', 1, 'P'),
    ('STRUCTURED_JACKETS', 'casual_jacket', 'Caçadora (denim/biker/bomber)', 2, 'P'),
    ('STRUCTURED_JACKETS', 'gilet', 'Gilet / armilla', 1, 'M'),

    ('HEAVY_OUTERWEAR', 'coat', 'Abric de llana', 1, 'P'),
    ('HEAVY_OUTERWEAR', 'trench', 'Gavardina / trench', 2, 'P'),
    ('HEAVY_OUTERWEAR', 'parka', 'Anorac / parca encoixinada', 3, 'P'),
    ('HEAVY_OUTERWEAR', 'leather_garment', 'Peça de pell / cuir', 3, 'P'),

    ('BABY_ONEPIECES', 'baby_sleepsuit', 'Pelele / pijama sencer', 1, 'M'),
    ('BABY_ONEPIECES', 'baby_sleepbag', 'Sac de dormir de nadó', 2, 'M'),
    ('BABY_ONEPIECES', 'baby_bloomers', 'Ranita (pantaló bombat)', 3, 'L'),

    ('BABY_SEPARATES', 'baby_bodysuit', 'Body de nadó', 1, 'L'),
    ('BABY_SEPARATES', 'baby_top', 'Top / samarreta de nadó', 1, 'L'),
    ('BABY_SEPARATES', 'baby_dress', 'Vestit de nadó', 2, 'M'),
    ('BABY_SEPARATES', 'baby_leggings', 'Leggings / pantalons de nadó', 2, 'L'),
    ('BABY_SEPARATES', 'baby_swimwear', 'Bany de nadó', 2, 'L'),
]

NEW_FAMILY_CODES = [f[0] for f in FAMILIES]


class Command(BaseCommand):
    help = 'Reestructura Garment Types a 17 famílies + 57 items (crear net + desactivar vell).'

    def handle(self, *args, **options):
        from fhort.pom.models import GarmentTypeGlobal, GarmentType
        from fhort.tasks.models import GarmentTypeItem, TaskType, TaskTimeEstimate

        rep = {
            'glob_public': [0, 0], 'glob_tenant': [0, 0], 'fam_tenant': [0, 0],
            'items': [0, 0], 'estimates': [0, 0],
            'glob_public_deact': 0, 'glob_tenant_deact': 0,
            'gt_deact': 0, 'items_deact': 0,
            'missing_tasktypes': [], 'banana_deact': False,
            'final_gt_active': None, 'final_items_active': None,
            'committed': False, 'rollback_reason': None,
        }

        def upsert_global(Model, codi, nom_en, grup, descripcio, order, bucket):
            obj, created = Model.objects.update_or_create(
                codi=codi,
                defaults=dict(nom_en=nom_en, nom_ca=nom_en, nom_es=nom_en, grup=grup,
                              descripcio=descripcio, is_system=True, actiu=True,
                              display_order=order),
            )
            bucket[0 if created else 1] += 1
            return obj

        try:
            with transaction.atomic():
                # ── PAS B (public): canònic global de les 17 famílies ──
                with schema_context('public'):
                    for i, (codi, nom_en, grup, desc) in enumerate(FAMILIES):
                        upsert_global(GarmentTypeGlobal, codi, nom_en, grup, desc, i * 10, rep['glob_public'])
                    rep['glob_public_deact'] = (GarmentTypeGlobal.objects
                                                .filter(actiu=True).exclude(codi__in=NEW_FAMILY_CODES)
                                                .update(actiu=False))

                # ── PAS B (rèplica tenant) + C + D + E ──
                with schema_context(TENANT):
                    # B: rèplica global al tenant
                    global_map = {}
                    for i, (codi, nom_en, grup, desc) in enumerate(FAMILIES):
                        global_map[codi] = upsert_global(
                            GarmentTypeGlobal, codi, nom_en, grup, desc, i * 10, rep['glob_tenant'])
                    rep['glob_tenant_deact'] = (GarmentTypeGlobal.objects
                                                .filter(actiu=True).exclude(codi__in=NEW_FAMILY_CODES)
                                                .update(actiu=False))

                    # C: famílies tenant (GarmentType)
                    for i, (codi, nom_en, grup, desc) in enumerate(FAMILIES):
                        _, created = GarmentType.objects.update_or_create(
                            codi_client=codi,
                            defaults=dict(nom_client=nom_en, nom_en=nom_en, nom_ca=nom_en,
                                          nom_es=nom_en, grup=grup, descripcio=desc,
                                          is_system=True, actiu=True,
                                          garment_type_global=global_map[codi]),
                        )
                        rep['fam_tenant'][0 if created else 1] += 1
                    fam_map = {gt.codi_client: gt for gt in
                               GarmentType.objects.filter(codi_client__in=NEW_FAMILY_CODES)}

                    # D: items + matriu de temps
                    tt_map = {tt.code: tt for tt in TaskType.objects.all()}
                    missing = [c for c in TASK_ORDER if c not in tt_map]
                    rep['missing_tasktypes'] = missing
                    new_item_ids = []
                    for fam_codi, code, name, complexity, profile in ITEMS:
                        item, created = GarmentTypeItem.objects.update_or_create(
                            garment_type=fam_map[fam_codi], code=code,
                            defaults=dict(name=name, complexity_order=complexity, active=True),
                        )
                        rep['items'][0 if created else 1] += 1
                        new_item_ids.append(item.id)
                        mins = PROFILES[profile]
                        for idx, tcode in enumerate(TASK_ORDER):
                            tt = tt_map.get(tcode)
                            if tt is None:
                                continue
                            _, c2 = TaskTimeEstimate.objects.update_or_create(
                                garment_type_item=item, task_type=tt,
                                defaults=dict(estimated_minutes=mins[idx]),
                            )
                            rep['estimates'][0 if c2 else 1] += 1

                    # E: desactivar el vell (sense esborrar)
                    rep['gt_deact'] = (GarmentType.objects
                                       .filter(actiu=True).exclude(codi_client__in=NEW_FAMILY_CODES)
                                       .update(actiu=False))
                    banana = GarmentTypeItem.objects.filter(code='Banana').first()
                    rep['banana_deact'] = bool(banana)
                    rep['items_deact'] = (GarmentTypeItem.objects
                                          .filter(active=True).exclude(id__in=new_item_ids)
                                          .update(active=False))

                rep['committed'] = True
        except Exception as e:  # rollback total
            rep['rollback_reason'] = repr(e)

        # Recompte final (després del commit)
        if rep['committed']:
            with schema_context(TENANT):
                rep['final_gt_active'] = GarmentType.objects.filter(actiu=True).count()
                rep['final_items_active'] = GarmentTypeItem.objects.filter(active=True).count()

        self._print_report(rep)
        if not rep['committed']:
            raise SystemExit('ROLLBACK: ' + str(rep['rollback_reason']))

    def _print_report(self, rep):
        p = self.stdout.write
        line = '═' * 64
        p('\n' + line)
        p('INFORME — Reestructuració Garment Types (17 famílies · 57 items)')
        p(line)
        p('check abans: OK (executat fora del command)')
        p('Famílies global PUBLIC (creades/actualitzades): %d / %d  | desactivades velles: %d'
          % (rep['glob_public'][0], rep['glob_public'][1], rep['glob_public_deact']))
        p('Famílies global TENANT (creades/actualitzades): %d / %d  | desactivades velles: %d'
          % (rep['glob_tenant'][0], rep['glob_tenant'][1], rep['glob_tenant_deact']))
        p('Famílies tenant GarmentType (creades/actualitzades): %d / %d  (esperat 17)'
          % (rep['fam_tenant'][0], rep['fam_tenant'][1]))
        p('Items creats/actualitzats: %d / %d  (esperat 57)'
          % (rep['items'][0], rep['items'][1]))
        p('TaskTimeEstimate creats/actualitzats: %d / %d  (esperat 513 = 57×9)'
          % (rep['estimates'][0], rep['estimates'][1]))
        p('GarmentTypes antics DESACTIVATS: %d' % rep['gt_deact'])
        p('Item brossa "Banana" desactivat: %s' % ('sí' if rep['banana_deact'] else 'no (no trobat)'))
        p('Items vells DESACTIVATS (inclou Banana): %d' % rep['items_deact'])
        p('TaskTypes NO trobats: %s' % (', '.join(rep['missing_tasktypes']) or 'cap (els 9 hi són)'))
        p('Recompte final → GarmentType actius: %s (esperat 17) | GarmentTypeItem actius: %s (esperat 57)'
          % (rep['final_gt_active'], rep['final_items_active']))
        p('Transacció: %s%s' % ('COMMIT' if rep['committed'] else 'ROLLBACK',
                                '' if rep['committed'] else ' — ' + str(rep['rollback_reason'])))
        p('git: NO committejat (working tree per revisar).')
        p('NOTA: nom_ca/nom_es de família = nom_en provisional (cal traducció CA/ES).')
        p(line + '\n')
