"""U1/U2 · Les dues preguntes que el catàleg ha de saber respondre.

  · `pom_us_view`        — ON S'USA un POM, i per tant si es pot esborrar.
  · `item_acumulacio_view` — el catàleg de POMs que un item PROPOSA (grup + família + item).

🔴 **LA REGLA D'ESBORRAT, I PER QUÈ ES PREGUNTA ALS MODELS DE DJANGO.**
El recompte d'ús es calcula recorrent `POMMaster._meta.related_objects`, **mai**
`information_schema`. La lliçó és de `TGIRL-EU-HEIGHT` (C3, 07/08): un cens fet contra la BD el
va donar per «risc zero» i resulta que era l'àncora de 350 regles de graduació. Les FK amb
`db_constraint=False` —que aquesta casa fa servir a tot arreu per creuar shared↔tenant— **no
existeixen per a Postgres**. Només l'ORM les veu.

I hi ha una segona lliçó, que és d'avui: no totes les relacions bloquegen igual.
  · **PROTECT amb files** → esborrar és impossible. Això és «ús».
  · **CASCADE amb files** → esborrar és possible, però se les endú. Això NO és ús, però
    s'ha de DIR: avui són `CustomerPOMAlias` (els àlies del client) i les estadístiques.
    Un botó que esborra 3 àlies de client sense avisar és el mateix silenci que ens ha costat
    un ensurt aquest matí.
"""
from django.apps import apps
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from fhort.pom.acumulacio import acumula_poms_de_item, recompte_per_nivell
from fhort.pom.models import POMMaster


def _cens_relacions(pom):
    """Recorre TOTES les relacions entrants declarades a l'ORM i compta files per cadascuna.

    Retorna `(bloquejants, cascada)`, dues llistes de dicts. Cap relació es deixa fora ni
    s'enumera a mà: el dia que algú afegeixi una FK cap a `POMMaster`, aquest cens la veurà
    sola. Això és el contrari del cens que va fallar amb TGIRL.
    """
    bloquejants, cascada = [], []
    for rel in POMMaster._meta.related_objects:
        accessor = rel.get_accessor_name()
        try:
            n = getattr(pom, accessor).count()
        except Exception:
            # Una relació que no es pot comptar (taula absent en aquest schema) no es pot
            # donar per zero en silenci: és exactament l'error que volem no repetir.
            bloquejants.append({'relacio': rel.related_model._meta.label,
                                'accessor': accessor, 'n': None, 'indeterminat': True})
            continue
        if not n:
            continue
        fila = {'relacio': rel.related_model._meta.label, 'accessor': accessor, 'n': n}
        on_delete = getattr(rel.on_delete, '__name__', str(rel.on_delete))
        (cascada if on_delete == 'CASCADE' else bloquejants).append(fila)
    return bloquejants, cascada


def _tres_comptadors(pom):
    """Els tres números que la fitxa ensenya: items del catàleg · models vius · regles.

    Es compten ÀNCORES DISTINTES, no files: un item que reclama el mateix POM a l'exterior i al
    folre és UN item, no dos, i dir-ne dos faria semblar el catàleg més gran del que és.
    """
    Model = apps.get_model('models_app', 'Model')

    items = set(pom.garment_maps.values_list('garment_type_item_id', flat=True))
    families = set(pom.garment_type_maps.values_list('garment_type_id', flat=True))
    grups = set(pom.garment_group_maps.values_list('garment_group_id', flat=True))
    items.discard(None)

    models_vius = set(pom.base_measurements.values_list('model_id', flat=True))
    models_vius |= set(pom.model_grading_rules.values_list('model_id', flat=True))
    models_vius |= set(pom.model_grading_overrides.values_list('model_id', flat=True))
    models_vius.discard(None)
    # Els models esborrats no compten: el que interessa és què hi ha VIU al davant.
    if models_vius:
        models_vius = set(Model.objects.filter(id__in=models_vius).values_list('id', flat=True))

    regles = pom.regles_grading.count() + pom.model_grading_rules.count()

    return {'items': len(items), 'families': len(families), 'grups': len(grups),
            'models': len(models_vius), 'rules': regles}


def _us_observat(pom):
    """Les capes i les instàncies amb què aquest POM **es fa servir de debò**, avui.

    🔑 **NO és política declarada, i la pantalla ho ha de dir amb aquestes paraules.** El model
    no té enlloc «quines capes admet aquest POM» ni «quines instàncies el parteixen»: cap FK ni
    M2M de tot el codi apunta a `MeasurementLayer` ni a `MeasurementInstance`, que són catàlegs
    de vocabulari referenciats per slug. Decisió d'Agus (07/08): abans que inventar-se una
    declaració buida —que diria «cap» per als 274 POMs i seria FALS—, s'ensenya l'ÚS OBSERVAT,
    que és dada certa. El dia que la Montse tingui el catàleg v4, declarar-ho serà barat i
    llavors aquesta vista servirà per contrastar declarat vs observat.

    Es mira a les tres pertinences (els tres nivells del catàleg) i a les mesures base del
    model, que és on la capa i la instància acaben materialitzant-se.
    """
    BaseMeasurement = apps.get_model('models_app', 'BaseMeasurement')

    capes, instancies = set(), set()
    for qs in (pom.garment_maps.all(), pom.garment_type_maps.all(),
               pom.garment_group_maps.all(), pom.item_base_measurements.all()):
        for capa, inst in qs.values_list('capa', 'instancia'):
            capes.add(capa)
            if inst:
                instancies.add(inst)
    for capa, inst in BaseMeasurement.objects.filter(pom=pom).values_list('capa', 'instancia'):
        capes.add(capa)
        if inst:
            instancies.add(inst)

    return {'capes': sorted(c for c in capes if c),
            'instancies': sorted(instancies),
            'declarat': False}     # el contracte explícit: això és observat, no declarat


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def pom_us_view(request, pom_id):
    """`GET /api/v1/poms/<id>/us/` — on s'usa aquest POM i si es pot esborrar.

    La resposta porta el MOTIU sempre, tant si es pot com si no: la nota del peu de la fitxa
    la redacta el backend, que és qui sap el recompte.
    """
    pom = POMMaster.objects.filter(pk=pom_id).select_related('pom_global').first()
    if pom is None:
        return Response({'detail': 'POM no trobat.'}, status=404)

    bloquejants, cascada = _cens_relacions(pom)
    comptadors = _tres_comptadors(pom)
    total_bloquejant = sum(f['n'] or 0 for f in bloquejants)
    indeterminat = any(f.get('indeterminat') for f in bloquejants)

    # «DE SISTEMA» = ve del catàleg global de la casa (`pom_global`). Els que no en tenen han
    # nascut al tenant (import per IA, alta manual des d'un model) i són els únics esborrables.
    # ⚠️ `POMMaster` NO té cap camp `is_system`: això és una DERIVACIÓ, anotada al report.
    de_sistema = pom.pom_global_id is not None
    pot_esborrar = (not de_sistema) and total_bloquejant == 0 and not indeterminat

    if indeterminat:
        motiu = "No s'ha pogut comptar tot l'ús: no s'esborra res a cegues."
    elif de_sistema:
        motiu = 'POM de sistema: es pot desactivar, però no esborrar mai.'
    elif total_bloquejant:
        motiu = f'Té {total_bloquejant} usos: es pot desactivar, no esborrar.'
    elif cascada:
        n = sum(f['n'] for f in cascada)
        motiu = f"Sense cap ús que ho impedeixi, però esborrar-lo s'endurà {n} fila/es associada/es."
    else:
        motiu = 'Sense cap ús: es pot esborrar.'

    return Response({
        'pom': pom.id,
        'de_sistema': de_sistema,
        'actiu': pom.actiu,
        'us': comptadors,
        #: U1 — capes i instàncies OBSERVADES (v. `_us_observat`). `declarat: False` és part del
        #: contracte: la pantalla no pot pintar-ho com si fos una política declarada.
        'observat': _us_observat(pom),
        'total_bloquejant': total_bloquejant,
        'bloquejants': bloquejants,
        #: Files que NO bloquegen però que cauran amb el POM. Es diuen a posta.
        'cascada': cascada,
        'pot_esborrar': pot_esborrar,
        'motiu': motiu,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def item_acumulacio_view(request, item_id):
    """`GET /api/v1/garment-type-items/<id>/acumulacio/` — el catàleg que l'item PROPOSA.

    Cada fila diu de quin nivell arriba (`nivell` + `ancora`) i, si un nivell més bast també la
    reclamava, d'on més venia (`tambe_a`). El recompte és el que pinta la barra de la llista.
    """
    GarmentTypeItem = apps.get_model('tasks', 'GarmentTypeItem')
    item = (GarmentTypeItem.objects
            .filter(pk=item_id)
            .select_related('garment_type', 'garment_type__grup_ref')
            .first())
    if item is None:
        return Response({'detail': 'Item no trobat.'}, status=404)

    acumulat = acumula_poms_de_item(item)
    poms = {p.id: p for p in POMMaster.objects
            .filter(id__in=[f['pom_id'] for f in acumulat])
            .select_related('pom_global', 'categoria')}

    for f in acumulat:
        p = poms.get(f['pom_id'])
        pg = getattr(p, 'pom_global', None) if p else None
        f['pom_code'] = (pg.codi if pg else None) or (p.codi_client if p else '')
        f['name_en'] = (pg.nom_en if pg else None) or (p.nom_client if p else '')
        f['name_cat'] = (pg.nom_ca if pg else None) or (p.nom_client if p else '')
        f['abbreviation'] = (pg.abbreviation if pg else None) or (p.codi_client if p else '')
        f['unitat'] = pg.unitat if pg else ''

    return Response({
        'item': item.id,
        'item_codi': item.code,
        'familia': getattr(item.garment_type, 'codi_client', None),
        'grup': getattr(getattr(item.garment_type, 'grup_ref', None), 'codi', None),
        'recompte': recompte_per_nivell(acumulat),
        'poms': acumulat,
    })
