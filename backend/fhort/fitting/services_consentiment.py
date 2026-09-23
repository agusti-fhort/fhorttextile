"""LLEI Agus 24/09 — CONSENTIMENT DE GERMANES en consolidar un fitting a la base.

Cap germana NO mesurada s'escriu sense consentiment explícit: el sistema PROPOSA
(`proposta_de_consolidacio`, PUR — no escriu res) i el tècnic decideix al modal; qui
escriu és `aplica_consolidacio_amb_consentiment` (Patró B, COMMIT 4).

Precedents: `docs/diagnosis/DIAGNOSI_CONSENTIMENT_GERMANES.md` (contracte de proposta/decisió)
i `fitting/services.py::consolidate_base_from_fitting` (mateix predicat de «mesurada»,
`linies_mesurades_talla_base`, compartit per no divergir).
"""
from fhort.fitting.services import linies_mesurades_talla_base
from fhort.models_app.models import BaseMeasurement
from fhort.models_app.services_derivacio import deriva

#: Únic origen que el defecte del modal tracta com «no mesurat» (LLEI Agus 24/09: «origen
#: DERIVAT → proposta pre-usada; origen mesurat (FITTED/MANUAL/IMPORTED) → mantenir»).
#: `TEMPLATE` mai hi arriba: `deriva()` ja descarta les germanes sense `base_value_cm`
#: (`services_derivacio.py:146-148`), i una fila sense valor no pot ser germana proposada.
ORIGEN_DERIVAT = 'DERIVAT'


def es_mesurat(origen):
    """Defecte del modal: `False` (⇒ proposta pre-usada) NOMÉS per `origen == 'DERIVAT'`."""
    return origen != ORIGEN_DERIVAT


def etiqueta_instancia(slug):
    """Humanitzat mínim. NO EXISTEIX vocabulari d'instància avui (DIAGNOSI BLOC Q2): sense
    ell, la frase és el slug amb els separadors canviats per espais — millor que un guio_baix
    cru, no pretén ser la frase final."""
    net = (slug or '').replace('_', ' ').replace('-', ' ').strip()
    return net or '—'


def _delta_confirmat(model_id, pom_id, capa, instancia_origen, instancia_desti):
    """El delta que EL MODEL ja ha confirmat per a aquesta parella (`ModelInstanceOffset`),
    o `None` si no n'hi ha cap. SOBIRANIA DEL MODEL: es consulta ABANS de qualsevol càlcul en
    viu — mai el catàleg/GTI, que avui no en té cap (i si algun dia en tingués, aquesta
    consulta hi seguiria tenint prioritat)."""
    from fhort.models_app.models import ModelInstanceOffset
    return (ModelInstanceOffset.objects
            .filter(model_id=model_id, pom_id=pom_id, capa=capa,
                    instancia_origen=instancia_origen, instancia_desti=instancia_desti)
            .values_list('delta', flat=True).first())


def proposta_de_consolidacio(pf):
    """Calcula la proposta de consolidar `pf` a la base. PUR — no escriu res, no dispara cap
    senyal (mode pur de `deriva()`, `services_derivacio.py:125`).

    Retorna:
        {'piece_fitting_id': int, 'buit': bool,
         'poms': [{'pom': 'B', 'mesurades': [{'bm_id', 'instancia', 'abans', 'ara'}],
                   'germanes': [{'bm_id', 'instancia', 'origen', 'actual', 'proposat',
                                 'regla_text', 'font_instancia', 'decisio_defecte'}]}]}

    `buit=True` quan cap POM té germanes afectades — el cridador NO ha d'obrir cap modal
    (LLEI Agus 24/09, punt 4).

    Si dues instàncies mesurades de la MATEIXA sessió apunten a la MATEIXA germana no
    mesurada (p. ex. `relaxed` I `extended` totes dues rectificades i `seam` cap de les
    dues), la proposta mostrada és la de la FONT processada DARRERA en l'ordre determinista
    (POM, capa, instància) — el mateix ordre amb què `consolidate_base_from_fitting` (PAS 2)
    escriuria avui sense consentiment; el modal no amaga l'ambigüitat, la resol igual que ho
    fa el camí d'escriptura, i el tècnic hi pot decidir un valor manual si no hi està d'acord.
    """
    model = pf.model
    a_consolidar = linies_mesurades_talla_base(pf)
    mesurades = {(l.pom_id, l.capa, l.instancia) for l in a_consolidar}

    claus = {(l.pom_id, l.capa, l.instancia, l.garment) for l in a_consolidar}
    pom_ids = {c[0] for c in claus}
    bms_actuals = {
        (bm.pom_id, bm.capa, bm.instancia, bm.garment): bm
        for bm in BaseMeasurement.objects.filter(model=model, pom_id__in=pom_ids)
        if (bm.pom_id, bm.capa, bm.instancia, bm.garment) in claus
    }

    per_pom = {}          # codi POM → bucket
    germanes_per_pom = {} # codi POM → {bm_id: fila}  (last-wins, v. docstring)
    for line in a_consolidar:
        clau = (line.pom_id, line.capa, line.instancia, line.garment)
        bm_actual = bms_actuals.get(clau)
        valor_anterior = bm_actual.base_value_cm if bm_actual else None
        pom_codi = line.pom.codi_client

        bucket = per_pom.setdefault(pom_codi, {'pom': pom_codi, 'mesurades': [], 'germanes': []})
        germanes_bucket = germanes_per_pom.setdefault(pom_codi, {})
        bucket['mesurades'].append({
            'bm_id': bm_actual.pk if bm_actual else None,
            'instancia': line.instancia,
            'abans': valor_anterior,
            'ara': line.valor_real,
        })

        # Si `bm_actual` no existeix (primera mesura d'aquest pom/instància), un objecte
        # transitori (sense pk) n'hi ha prou: `deriva()` talla de seguida perquè
        # `valor_anterior` és `None` i mai arriba a llegir `bm.pk`/`germanes_de(bm)`.
        bm_per_deriva = bm_actual or BaseMeasurement(
            model=model, pom_id=line.pom_id, capa=line.capa, instancia=line.instancia,
            garment=line.garment)
        for d in deriva(bm_per_deriva, valor_anterior, line.valor_real, exclou=mesurades):
            delta_confirmat = _delta_confirmat(
                model.pk, line.pom_id, d.capa, line.instancia, d.instancia)
            if delta_confirmat is not None:
                valor_proposat = round(d.valor_actual + delta_confirmat, 2)
                delta_mostrat = delta_confirmat
                sufix = 'delta confirmat'
            else:
                valor_proposat = d.valor_proposat
                delta_mostrat = d.increment
                sufix = "regla d'instància"

            germana_bm = (BaseMeasurement.objects.filter(pk=d.base_measurement_id)
                          .only('origen').first())
            origen_actual = germana_bm.origen if germana_bm else ''
            xifra = f'{delta_mostrat:+.1f}'.replace('.', ',')

            germanes_bucket[d.base_measurement_id] = {
                'bm_id': d.base_measurement_id,
                'instancia': d.instancia,
                'origen': origen_actual,
                'actual': d.valor_actual,
                'proposat': valor_proposat,
                'regla_text': f'{etiqueta_instancia(line.instancia)} {xifra} · {sufix}',
                'font_instancia': line.instancia,
                'decisio_defecte': 'PROPOSTA' if not es_mesurat(origen_actual) else 'MANTINGUT',
            }

    poms = []
    for pom_codi, bucket in per_pom.items():
        bucket['germanes'] = list(germanes_per_pom[pom_codi].values())
        poms.append(bucket)

    buit = not any(p['germanes'] for p in poms)
    return {'piece_fitting_id': pf.pk, 'buit': buit, 'poms': poms}
