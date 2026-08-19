"""U2 · LA LLEI DE L'ACUMULACIÓ — el catàleg de POMs que un item PROPOSA.

El catàleg s'acumula per nivell: **el grup aporta, la família suma, l'item suma**. Res exclou
res, i un mateix POM pot ser a molts items. La jerarquia NO viu a la BD —hi ha tres taules
germanes i independents (`GarmentGroupPOMMap`, `GarmentTypePOMMap`, `GarmentPOMMap`)—: viu
AQUÍ, com una unió a la lectura.

**PER QUÈ AIXÒ ÉS UNA FUNCIÓ I NO UNA CONSULTA A CADA PANTALLA.** Perquè el «Ve de» és part de
la resposta. Qui pinta la fitxa d'un item no ha de saber que hi ha tres taules; ha de rebre la
llista ja acumulada, cada fila dient de quin nivell arriba. Si aquesta unió es reescriu a cada
consumidor, el dia que s'afegeixi un nivell hi haurà tants llocs a tocar com pantalles.

**LA IDENTITAT D'UNA PERTINENÇA ÉS `(pom, capa, instancia)`**, la mateixa que la clau de les
tres taules. Dos nivells poden reclamar el mateix POM a la mateixa capa i instància: no és un
error ni un duplicat a esmenar, és el cas normal —el grup diu «tots els tops porten pit» i
l'item ho torna a dir. **Guanya el nivell MÉS ESPECÍFIC** (item > família > grup), perquè és qui
coneix millor la peça; els altres queden anotats a `tambe_a` perquè la pantalla pugui explicar
d'on més venia.
"""

#: Els tres nivells, del més bast al més específic. L'ordre MANA: l'últim que parla, guanya.
NIVELL_GRUP = 'grup'
NIVELL_FAMILIA = 'familia'
NIVELL_ITEM = 'item'
NIVELLS = (NIVELL_GRUP, NIVELL_FAMILIA, NIVELL_ITEM)


def _clau(m):
    """La identitat d'una pertinença: el POM, a quina capa i en quina instància."""
    return (m.pom_id, m.capa, m.instancia)


def _fila(m, nivell, anchor):
    return {
        'nivell': nivell,
        'ancora': anchor,
        'map_id': m.id,
        'pom_id': m.pom_id,
        'capa': m.capa,
        'instancia': m.instancia,
        'obligatori': m.obligatori,
        'is_key': m.is_key,
        'nivell_excel': m.nivell,
        'ordre': m.ordre,
        'pendent_revisio': m.pendent_revisio,
        #: Els altres nivells que reclamaven la MATEIXA identitat i que aquest ha tapat.
        #: No és brossa: és el que permet dir «això ve de l'item, però el grup ja ho demanava».
        'tambe_a': [],
    }


def acumula_poms_de_item(item):
    """El catàleg acumulat d'un `GarmentTypeItem`: llista de dicts, un per pertinença viva.

    Ordre de resolució: grup → família → item. El més específic guanya la identitat i es queda
    els altres a `tambe_a`. Retorna llista buida si l'item no té família (dada incompleta, no
    error): sense família no hi ha ni grup ni res a acumular.
    """
    from fhort.pom.models import GarmentGroupPOMMap, GarmentPOMMap, GarmentTypePOMMap

    familia = item.garment_type
    if familia is None:
        return []
    grup = familia.grup_ref            # C6 pas 1: la FK de grup. NULL = família sense grup encara.

    trams = []
    if grup is not None:
        trams.append((NIVELL_GRUP, grup.codi, GarmentGroupPOMMap.objects
                      .filter(garment_group=grup).select_related('pom')))
    trams.append((NIVELL_FAMILIA, familia.codi_client, GarmentTypePOMMap.objects
                  .filter(garment_type=familia).select_related('pom')))
    trams.append((NIVELL_ITEM, item.code, GarmentPOMMap.objects
                  .filter(garment_type_item=item).select_related('pom')))

    per_clau = {}
    for nivell, ancora, qs in trams:
        for m in qs:
            k = _clau(m)
            anterior = per_clau.get(k)
            nova = _fila(m, nivell, ancora)
            if anterior is not None:
                # El més específic tapa l'anterior, però se n'endú la memòria.
                nova['tambe_a'] = anterior['tambe_a'] + [
                    {'nivell': anterior['nivell'], 'ancora': anterior['ancora']}]
            per_clau[k] = nova

    # Ordre de pantalla: pel nivell que APORTA (el bast primer, que és com es llegeix un
    # catàleg que creix), i dins del nivell per l'`ordre` que cada taula ja declara.
    pes = {n: i for i, n in enumerate(NIVELLS)}
    return sorted(per_clau.values(), key=lambda f: (pes[f['nivell']], f['ordre'], f['pom_id']))


def recompte_per_nivell(acumulat):
    """`{grup: n, familia: n, item: n, total: n}` — el que la columna de la llista d'items pinta.

    Compta el que cada nivell APORTA de debò (el que no ha estat tapat per un de més específic),
    perquè la barra de la maqueta ha de sumar exactament el total.
    """
    r = {n: 0 for n in NIVELLS}
    for f in acumulat:
        r[f['nivell']] += 1
    r['total'] = sum(r[n] for n in NIVELLS)
    return r
