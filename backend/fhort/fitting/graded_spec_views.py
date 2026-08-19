"""Taula de specs graduades d'un SizeFitting — per a la fitxa tècnica (F3).

GET /api/v1/fitting/<size_fitting_id>/graded-table/

Retorna la GradingVersion is_active=True del SizeFitting amb les seves GradedSpec
enriquides amb la nomenclatura POM (POMMaster → POMGlobal: codi, noms EN/CA, abreviatura,
categoria, unitat). Format pensat per pintar una taula POM × talla:
  - size_labels: ordre d'aparició de les talles
  - rows: una fila per POMMaster, amb {valors: {size_label: graded_value_cm}}

JSON directe (no cal serializer DRF). Multitenant: la consulta corre dins l'esquema del
tenant resolt pel middleware; un SizeFitting d'un altre tenant simplement no existeix aquí → 404.
"""
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import GradedSpec, SizeFitting


class GradedSpecTableView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, sf_id):
        sf = get_object_or_404(SizeFitting, pk=sf_id)

        # Versió vigent: criteri ÚNIC compartit amb taula-mesures (is_active prioritari,
        # fallback a la més recent). Evita divergència is_active vs -data.
        from fhort.fitting.services import vigent_grading_version
        gv = vigent_grading_version(sf)
        if gv is None:
            return Response(
                {'detail': "Aquest SizeFitting no té cap GradingVersion."},
                status=404,
            )

        # C4 — L'ÀNCORA SE'N VA I LA FILA CREIX A LA IDENTITAT SENCERA.
        #
        # Què hi havia i per què: entre FASE_2/C1-ins i C4 aquest queryset filtrava
        # `capa='exterior', instancia=''` perquè `rows_by_pom` s'indexava per `pom.id` pelat i
        # ÉS la fila del payload — sense àncora, dues germanes es fondrien a la mateixa fila i
        # l'última llegida guanyaria talla a talla. L'àncora era contenció mentre la fila no
        # sabia dir de quina germana parlava.
        #
        # Ara ho sap: la fila s'indexa per `(pom_id, capa, instancia)` i PUBLICA els dos eixos.
        # Amb la clau completa el filtre ja no protegeix res i seria pèrdua: amb les comportes
        # fora, la germana no es col·lapsaria —quedaria FORA del `filter`—, i la fitxa sortiria
        # coherent amb una fila de menys. Absència silenciosa, que és pitjor de veure que un
        # valor equivocat.
        # SET-2/T6a (2026-08-11) — LA FILA SERVEIX L'EIX DE LA PEÇA, i cal dir per què això
        # NO contradiu el revert de `7cc133b5` (que va TREURE una clau `garment` del payload
        # de `base-measurements/`). Els dos motius d'aquell revert no apliquen aquí:
        #
        #   (a) Allà el que s'hi servia era una DEFINICIÓ HEREDABLE (run, ruleset, talla base):
        #       un valor que la peça pot NO tenir i que s'ha de resoldre contra el model. La
        #       resolució `garment.X or model.X` ha de viure en UN SOL PUNT (D5), i servir-la
        #       crua des d'una vora n'obria una segona via. Aquí NO hi ha cap resolució: el
        #       `garment` d'una fila és l'eix PROPI de la fila, dada factual —de quina peça és
        #       aquesta mesura—, no heretada de ningú.
        #   (b) Allà la clau no tenia cap lector i era bastida sense funció. Aquí en té un de
        #       NOMENAT: la partició de la T1b per prenda (D7), i el camí ja existeix —
        #       `TechSheetEditor.jsx` passa `data.rows` per `partirEnTaules`→`garmentDeFila`,
        #       que avui llegeix la mare perquè el payload no la porta.
        #
        # 🔑 LA REGLA QUE SE'N DERIVA, i val per a tot el sprint: **servir l'EIX D'UNA FILA és
        # sempre legítim; servir una DEFINICIÓ RESOLTA, només des del punt únic.**
        #
        # L'`order_by` el porta també: sense ell, dues peces del mateix POM a la mateixa capa i
        # instància empataven a tots els camps i el desempat el decidia `id`, o sigui l'ordre
        # d'inserció dels specs.
        specs = (
            GradedSpec.objects
            .filter(grading_version=gv, is_active=True)
            .select_related('pom__pom_global')
            .order_by('pom_id', 'capa', 'instancia', 'garment', 'id')
        )

        # size_labels en ordre d'aparició (no alfabètic: respecta l'ordre dels specs).
        size_labels = []
        seen_sizes = set()
        # rows indexats per la IDENTITAT de la mesura (un dict de valors per talla), en ordre
        # d'aparició. La clau del dict és interna; el que surt al payload és la fila.
        rows_by_pom = {}
        rows_order = []

        for s in specs:
            if s.size_label not in seen_sizes:
                seen_sizes.add(s.size_label)
                size_labels.append(s.size_label)

            pom = s.pom
            pg = pom.pom_global  # pot ser None → fallback als camps *_client del POMMaster
            ident = (pom.id, s.capa, s.instancia, s.garment)
            if ident not in rows_by_pom:
                rows_by_pom[ident] = {
                    'pom_id': pom.id,
                    # SET-2/T6a — L'EIX DE LA FILA (v. l'acta del queryset, a sobre). El
                    # consumidor és `partirEnTaules`→`garmentDeFila`, que fins avui llegia la
                    # mare per a totes les files perquè aquest camp no hi era.
                    'garment': s.garment,
                    # C4 — ELS DOS EIXOS AL CONTRACTE. `pom_id` es queda i no canvia de
                    # significat (consumidors antics segueixen llegint-lo); el que canvia és que
                    # ja no és únic dins de `rows`, i aquests dos camps són el que ho desempata.
                    'capa': s.capa,
                    'instancia': s.instancia,
                    'codi': (pg.codi if pg else None) or pom.codi_client,
                    'abbreviation': (pg.abbreviation if pg else '') or '',
                    'nom_en': (pg.nom_en if pg else None) or pom.nom_client,
                    'nom_ca': (pg.nom_ca if pg else None) or pom.nom_client,
                    'categoria': (pg.categoria if pg else '') or '',
                    'unitat': (pg.unitat if pg else 'cm') or 'cm',
                    'valors': {},
                    'deltas': {},   # TS-4a: increment_applied_cm per talla (delta vs base)
                }
                rows_order.append(ident)

            rows_by_pom[ident]['valors'][s.size_label] = s.graded_value_cm
            rows_by_pom[ident]['deltas'][s.size_label] = float(s.increment_applied_cm or 0)

        # TS-4a: enriquiment del payload — talla base, ordre de fitxa i nomenclatura del croquis.
        # Imports locals (evita cicle fitting↔models_app a nivell de mòdul).
        from fhort.models_app.models import Model as TechModel, BaseMeasurement
        model = TechModel.objects.filter(pk=sf.model_id).first()
        base_size = model.base_size_label if model else None
        # ordre i nom_fitxa per POMMaster del model (precedent: serializers.py FIX 4B).
        # F3 — `seccio` viatja pel MATEIX camí que `ordre`/`nom_fitxa`: surt de la
        # BaseMeasurement del model, no del GradedSpec (la graduació no en sap res, i no li
        # pertoca: la secció és una propietat del document d'origen, no de l'escalat).
        #
        # C4 — ELS QUATRE MAPES CREIXEN A LA CLAU SENCERA, i han d'anar-hi tots quatre alhora
        # (era la llei de C2/Onada 1 i segueix sent-ho): si un cresqués i un altre no, una fila
        # podria acabar amb l'ordre d'una capa i el nom d'una altra. Amb dos eixos són quatre
        # maneres de barrejar-ho, no dues.
        #
        # L'àncora d'aquests mapes existia perquè la fila que els consulta no portava capa. Ara
        # la porta, o sigui que la contenció sobra i el filtre seria pèrdua: la germana es
        # quedaria sense ordre, sense nomenclatura de croquis, sense secció i sense bateig —
        # sortiria a la fitxa amb el nom del catàleg i al final de la taula.
        bms = BaseMeasurement.objects.filter(
            model_id=sf.model_id).values(
            'pom_id', 'capa', 'instancia', 'garment', 'ordre', 'nom_fitxa', 'seccio',
            # R1 (31/07) — el BATEIG viatja pel MATEIX camí que `ordre`/`nom_fitxa`: surt de la
            # BaseMeasurement del model, perquè és del MODEL i no de la graduació. Sense això,
            # la taula T1b de la fitxa imprimia el nom del catàleg d'un POM que el tècnic havia
            # rebatejat — el panell de cotes deia una cosa i el paper una altra.
            'nom_canonic_model', 'nom_traduit_model')

        def _ident(bm):
            # SET-2/T6a — ELS QUATRE MAPES CREIXEN ALHORA, i segueix sent la llei de C2/Onada 1
            # que ja obligava amb capa i instància: amb un eix més són vuit maneres de barrejar
            # l'ordre d'una peça amb el nom de l'altra, no quatre.
            return (bm['pom_id'], bm['capa'], bm['instancia'], bm['garment'])

        ordre_map = {_ident(bm): bm['ordre'] for bm in bms}
        nom_fitxa_map = {_ident(bm): bm['nom_fitxa'] for bm in bms}
        seccio_map = {_ident(bm): bm['seccio'] for bm in bms}
        bateig_map = {_ident(bm): (bm['nom_canonic_model'] or '',
                                   bm['nom_traduit_model'] or '') for bm in bms}

        # LA REGLA per fila. `deltas` (increment_applied_cm) és la distància ACUMULADA a la
        # base — invariant declarada a patterns/engine/ports.py:64 i grading_projection.py:29 —
        # i per tant NO és l'increment per salt. Qui vulgui pintar «Δ per talla» ha de llegir
        # la regla DECLARADA, no deduir-la del resultat: mateix camí que `ordre`/`nom_fitxa`
        # (BaseMeasurement, aquí a sobre), però des de la regla de graduació.
        #
        # `_load_grading_rules` és la MATEIXA font que fa servir el motor: ModelGradingRule
        # resident amb prioritat i fallback al GradingRuleSet extern. Els dos camins (F1
        # resident i RULESET) queden servits per una sola lectura, com el motor.
        from fhort.pom.services import _load_grading_rules
        regles = _load_grading_rules(model) if model else {}

        rows = [rows_by_pom[ident] for ident in rows_order]
        # ref = nomenclatura del croquis (nom_fitxa) amb fallback a abbreviation del POMGlobal.
        for ident, row in zip(rows_order, rows):
            row['ref'] = nom_fitxa_map.get(ident) or row['abbreviation']
            row['seccio'] = seccio_map.get(ident) or ''
            # R1 — CRUS i al costat del catàleg (`nom_en`/`nom_ca`, que no es toquen):
            # '' = no batejat → mana el catàleg. La cascada la resol qui pinta. Camps NOUS.
            _bat = bateig_map.get(ident) or ('', '')
            row['nom_canonic_model'], row['nom_traduit_model'] = _bat
            # La REGLA segueix sent per POM, i és decisió de domini amb acta
            # (`pom/services.py:723-730`): mateix POM, mateix increment a totes les capes i
            # instàncies. Aquí no s'hi busca amb la clau sencera perquè la taula de regles no
            # té els eixos — no és un oblit, és que la regla no en distingeix.
            r = regles.get(row['pom_id'])
            # Increment PER SALT ascendent (positiu). Sense regla, o amb regla sense increment
            # (STEP/FIXED), viatja null: el pintor decideix el placeholder, la vista no en posa.
            inc = getattr(r, 'increment_base', None) if r else None
            row['increment_base'] = float(inc) if inc is not None else None
            row['talla_break_label'] = (getattr(r, 'talla_break_label', None) if r else None) or ''
            row['logica'] = getattr(r, 'logica', None) if r else None
        # Ordre de fitxa (mesures sense BaseMeasurement → al final). El desempat pels dos eixos
        # no és decoratiu: dues germanes comparteixen `ordre` (és el del POM a la fitxa), i
        # sense ell l'ordre entre elles el decidiria el pla de Postgres i es mouria sol.
        # SET-2/T6a — la PEÇA encapçala el desempat, mateix criteri que `clau_ordre_taula`
        # (`pom/grading_views.py`): la llei de T9 és «la prenda a fora», o sigui que les files
        # d'una peça van JUNTES i no intercalades amb les d'una altra. La mare primer (`0`).
        # I sense ella la clau tornava a ser parcial: dues peces comparteixen `ordre` —és el
        # del POM a la fitxa— i el seu ordre relatiu el decidiria el pla de Postgres.
        rows.sort(key=lambda r: (0 if not r['garment'] else 1, r['garment'],
                                 ordre_map.get((r['pom_id'], r['capa'], r['instancia'],
                                                r['garment']), 10 ** 9),
                                 r['capa'], r['instancia']))

        return Response({
            'size_fitting_id': sf.id,
            'grading_version_id': gv.id,
            'grading_version_nom': gv.nom,
            'base_size': base_size,
            'size_labels': size_labels,
            'rows': rows,
        })
