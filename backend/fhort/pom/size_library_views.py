"""A2 · La pregunta que la Size Library ha de saber respondre: ON S'USA UN RUN.

Germà exacte de `pom_us_view` (`cataleg_views.py`), i a posta: la fitxa d'un run i la d'un POM
fan la mateixa pregunta i han de rebre la mateixa forma de resposta —`us` / `bloquejants` /
`cascada` / `pot_esborrar` / `motiu`—, perquè les dues pantalles de Configuració tècnica es
comporten igual davant del mateix gest.

🔴 **PER QUÈ EL CENS GENÈRIC NO BASTA AQUÍ, I ÉS TOTA LA GRÀCIA.**

Recórrer `SizeSystem._meta.related_objects` troba el que apunta AL RUN: `GradingRuleSet`,
`ItemBaseSet`, `SizingProfile`, `Model`, `GarmentTypeItem`… i `SizeDefinition` (les seves talles,
CASCADE). El que NO troba és el que penja de les TALLES:

    GradingRule.talla_base ──PROTECT──> SizeDefinition ──CASCADE──> SizeSystem

Una regla de graduació no apunta mai al run: apunta a una TALLA del run. Per al cens directe, un
run pot tenir «0 usos» i ser l'àncora de talla base de centenars de regles. **Això no és
hipotètic: és exactament el que va passar amb `TGIRL-EU-HEIGHT` el 07/08** —un cens el va donar
per «risc zero» i era l'àncora de 350 regles de deu jocs—, i és la lliçó que la maqueta v3 posa
per escrit («"On s'usa" compta també les regles ancorades a les SEVES TALLES, no només el que
apunta al run»).

Per això `_regles_ancorades()` existeix i es compta a part, amb nom propi a la resposta. No és un
extra: és la xifra que decideix si el botó d'esborrar s'ofereix.

I una segona conseqüència, que la nota del peu ha de dir: esborrar el run vol dir CASCADE sobre
les seves talles, i aquelles talles estan PROTEGIDES per les regles. O sigui que el `DELETE`
fallaria igualment — però amb un error sobre talles, que no explica res a qui el llegeix. Aquí el
motiu parla de les REGLES, que és el que realment ho impedeix.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from fhort.pom.models import GradingRule, SizeSystem

#: Relacions que NO són ús real del run i que per tant no s'hi compten com a bloquejants:
#: `talles` són el run mateix (les seves files), i `parent` és llinatge, no consum.
_NO_ES_US = {'talles', 'derived_systems'}


def _cens_relacions(run):
    """`(bloquejants, cascada)` recorrent TOTES les relacions entrants declarades a l'ORM.

    Cap relació s'enumera a mà: el dia que algú afegeixi una FK cap a `SizeSystem`, aquest cens
    la veurà sola. Mateixa raó que a `cataleg_views._cens_relacions` — les FK amb
    `db_constraint=False` que la casa fa servir per creuar shared↔tenant **no existeixen per a
    Postgres**, i només l'ORM les veu.
    """
    bloquejants, cascada = [], []
    for rel in SizeSystem._meta.related_objects:
        accessor = rel.get_accessor_name()
        if accessor in _NO_ES_US:
            continue
        try:
            n = getattr(run, accessor).count()
        except Exception:
            # Comptar és lectura: si una relació peta, es diu, no s'ignora. Un cens que
            # s'empassa un error torna un «0» que no vol dir «cap».
            bloquejants.append({'model': rel.related_model._meta.label, 'camp': rel.field.name,
                                'n': None, 'indeterminat': True})
            continue
        if not n:
            continue
        fila = {'model': rel.related_model._meta.label, 'camp': rel.field.name, 'n': n}
        od = getattr(rel.field.remote_field, 'on_delete', None)
        nom_od = getattr(od, '__name__', '')
        # PROTECT amb files → impossible d'esborrar: això és ÚS.
        # CASCADE/SET_NULL amb files → possible, però se les endú o les desvincula: no és ús,
        # però s'ha de DIR. Un botó que desvincula 14 models en silenci és el mateix silenci
        # que ens ha costat un ensurt.
        (bloquejants if nom_od == 'PROTECT' else cascada).append(fila)
    return bloquejants, cascada


def _regles_ancorades(run):
    """Regles de graduació que fan servir una TALLA d'aquest run com a talla base.

    La consulta que el cens directe no pot fer. V. la capçalera del mòdul: `GradingRule` no
    apunta mai a `SizeSystem`, i per això un run pot semblar lliure i no ser-ho.
    """
    qs = GradingRule.objects.filter(talla_base__size_system=run)
    return qs.count(), qs.values('rule_set').distinct().count()


def _comptadors(run):
    """Els números que la fitxa pinta a «On s'usa». Cadascun d'una relació REAL, cap inventat."""
    n_regles, n_jocs = _regles_ancorades(run)
    return {
        'jocs_de_regles': run.grading_rule_sets.count(),
        'items_base': run.item_base_sets.count(),
        'models': run.models.count(),
        'perfils': run.sizing_profiles.count(),
        'items_proposen': run.proposed_by_items.count(),
        #: 🔴 L'ÀNCORA. Regles que pengen de les TALLES d'aquest run, no del run.
        'regles_ancorades': n_regles,
        'jocs_ancorats': n_jocs,
        'talles': run.talles.count(),
    }


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def size_system_us_view(request, size_system_id):
    """`GET /api/v1/size-systems/<id>/us/` — on s'usa aquest run i si es pot esborrar.

    La resposta porta el MOTIU sempre, tant si es pot com si no: la nota del peu de la fitxa la
    redacta el backend, que és qui sap el recompte.

    ⚠️ **AQUÍ NO HI HA CAP «CANÒNIC».** `SizeSystem` no té `is_system` ni cap flag de canonicitat
    (v. la maqueta v3.1, que retira el badge per aquest motiu). L'única cosa derivable de la dada
    és **si el run té client o no**, i això és `te_client`: un fet, no una categoria inventada.
    """
    run = (SizeSystem.objects
           .filter(pk=size_system_id)
           .select_related('customer')
           .prefetch_related('talles')
           .first())
    if run is None:
        return Response({'detail': 'Run no trobat.'}, status=404)

    bloquejants, cascada = _cens_relacions(run)
    comptadors = _comptadors(run)
    n_ancorades = comptadors['regles_ancorades']
    total_bloquejant = sum(f['n'] or 0 for f in bloquejants)
    indeterminat = any(f.get('indeterminat') for f in bloquejants)

    pot_esborrar = total_bloquejant == 0 and n_ancorades == 0 and not indeterminat

    if indeterminat:
        motiu = "No s'ha pogut comptar tot l'ús: no s'esborra res a cegues."
    elif n_ancorades:
        # Es diu PRIMER perquè és el que el cens directe no veu i el que més sorprèn.
        motiu = (f'{n_ancorades} regla/es de graduació de {comptadors["jocs_ancorats"]} joc/s '
                 f'estan ancorades a les talles d\'aquest run: es pot desactivar, no esborrar.')
    elif total_bloquejant:
        motiu = f'Té {total_bloquejant} usos: es pot desactivar, no esborrar.'
    elif cascada:
        n = sum(f['n'] for f in cascada)
        motiu = (f"Sense cap ús que ho impedeixi, però esborrar-lo desvincularà "
                 f"{n} fila/es associada/es.")
    else:
        motiu = 'Sense cap ús: es pot esborrar.'

    return Response({
        'size_system': run.id,
        'actiu': run.actiu,
        #: NO és «canònic»: és si té client. `SizeSystem` no té cap flag de canonicitat.
        'te_client': bool(run.customer_id or (run.customer_codi or '').strip()),
        'client': run.customer_codi or (run.customer.nom if run.customer_id else '') or '',
        'us': comptadors,
        'total_bloquejant': total_bloquejant,
        'bloquejants': bloquejants,
        'cascada': cascada,
        'pot_esborrar': pot_esborrar,
        'motiu': motiu,
    })
