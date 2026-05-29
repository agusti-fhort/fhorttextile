import datetime

from django.db import connection
from rest_framework import viewsets
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.filters import OrderingFilter, SearchFilter
from django_filters.rest_framework import DjangoFilterBackend

from .models import BaseMeasurement, Model, ModelFitxer
from .serializers import (
    BaseMeasurementSerializer,
    ModelDetailSerializer,
    ModelFitxerSerializer,
    ModelListSerializer,
)


class ModelViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['estat', 'fase_actual', 'garment_type', 'responsable']
    search_fields = ['codi_intern', 'codi_client', 'nom_prenda']
    ordering_fields = ['prioritat', 'data_objectiu', 'data_entrada']
    ordering = ['-prioritat']
    queryset = Model.objects.all()

    def get_queryset(self):
        # django-tenants ja restringeix les queries a l'esquema actual del tenant
        # via la connection. Al schema 'public' no hi ha taules de models, però
        # retornem un queryset buit per evitar errors a vistes mal encaminades.
        if getattr(connection, 'schema_name', None) == 'public':
            return Model.objects.none()
        return (
            Model.objects
            .select_related('garment_type', 'garment_group',
                            'responsable', 'responsable__user',
                            'size_system', 'talla_base', 'grading_rule_set')
            .all()
        )

    def get_serializer_class(self):
        if self.action == 'list':
            return ModelListSerializer
        return ModelDetailSerializer


class ModelFitxerViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ModelFitxerSerializer
    queryset = ModelFitxer.objects.select_related('model', 'pujat_per').all()
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['model', 'categoria', 'tipus', 'enviat_ia']
    ordering_fields = ['data_pujada']
    ordering = ['-data_pujada']


# Sprint S14B — BaseMeasurement CRUD
class BaseMeasurementViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = BaseMeasurementSerializer
    queryset = (
        BaseMeasurement.objects
        .select_related('pom', 'pom__pom_global')
        .all()
    )
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['model', 'pom', 'is_active', 'origen']
    ordering_fields = ['updated_at', 'id']
    ordering = ['model', 'id']

    def get_queryset(self):
        # Al schema 'public' no hi ha dades de tenant — retorna queryset buit.
        if getattr(connection, 'schema_name', None) == 'public':
            return BaseMeasurement.objects.none()
        return super().get_queryset()



# Sprint 1C — ModelServeiViewSet
from rest_framework import viewsets, permissions
from django_filters.rest_framework import DjangoFilterBackend

class ModelServeiViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['model', 'servei', 'contractat', 'estat_autoritzacio']
    ordering = ['servei__ordre_popup']

    def get_queryset(self):
        from .models import ModelServei
        return ModelServei.objects.select_related('servei', 'model').all()

    def get_serializer_class(self):
        from .serializers import ModelServeiSerializer
        return ModelServeiSerializer


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def next_model_ref(request):
    year = request.GET.get('year', str(datetime.date.today().year))
    season = request.GET.get('season', 'SS')
    prefix = 'FTT'
    year_short = str(year)[-2:]
    base = f"{prefix}-{season}{year_short}-"
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT codi_intern FROM models_app_model "
            "WHERE codi_intern LIKE %s "
            "ORDER BY codi_intern DESC LIMIT 1",
            [base + '%']
        )
        row = cursor.fetchone()
    if row:
        last_num = int(row[0].split('-')[-1])
        next_num = last_num + 1
    else:
        next_num = 1
    codi = f"{base}{str(next_num).zfill(4)}"
    return Response({'codi_intern': codi, 'next_number': next_num})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_model_wizard(request):
    year = request.data.get('year')
    season = request.data.get('season')
    ref_client = request.data.get('ref_client', '')
    nom_prenda = request.data.get('nom_prenda', '')
    descripcio = request.data.get('descripcio', '')

    if not year or not season:
        return Response({'error': 'year i season són obligatoris'}, status=400)

    prefix = 'FTT'
    year_short = str(year)[-2:]
    base = f"{prefix}-{season}{year_short}-"

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT codi_intern FROM models_app_model "
            "WHERE codi_intern LIKE %s "
            "ORDER BY codi_intern DESC LIMIT 1",
            [base + '%']
        )
        row = cursor.fetchone()
    next_num = (int(row[0].split('-')[-1]) + 1) if row else 1
    codi_intern = f"{base}{str(next_num).zfill(4)}"

    model = Model.objects.create(
        codi_intern=codi_intern,
        codi_client=ref_client,
        codi_tenant=prefix,
        any=int(year),
        temporada=season,
        sequencial=next_num,
        nom_prenda=nom_prenda or None,
        descripcio=descripcio or None,
        estat='Nou',
    )
    return Response({'id': model.id, 'codi_intern': model.codi_intern}, status=201)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_model_step2(request, model_id):
    try:
        model = Model.objects.get(id=model_id)
    except Model.DoesNotExist:
        return Response({'error': 'Model no trobat'}, status=404)

    d = request.data
    if d.get('garment_type_id'):
        from fhort.pom.models import GarmentType
        try:
            model.garment_type = GarmentType.objects.get(id=d['garment_type_id'])
        except GarmentType.DoesNotExist:
            return Response({'error': 'GarmentType no trobat'}, status=400)
    if d.get('size_system_id'):
        from fhort.pom.models import SizeSystem
        try:
            model.size_system = SizeSystem.objects.get(id=d['size_system_id'])
        except SizeSystem.DoesNotExist:
            return Response({'error': 'SizeSystem no trobat'}, status=400)
    if d.get('grading_rule_set_id'):
        from fhort.pom.models import GradingRuleSet
        try:
            model.grading_rule_set = GradingRuleSet.objects.get(id=d['grading_rule_set_id'])
        except GradingRuleSet.DoesNotExist:
            pass
    if d.get('target'):
        model.target = d['target']
    if d.get('construction'):
        model.construction = d['construction']
    if d.get('size_run'):
        model.size_run_model = d['size_run']
    if d.get('base_size'):
        model.base_size_label = d['base_size']

    model.save()
    return Response({'id': model.id, 'codi_intern': model.codi_intern})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def poms_suggerits_view(request, model_id):
    try:
        model = Model.objects.get(id=model_id)
    except Model.DoesNotExist:
        return Response({'error': 'Model no trobat'}, status=404)

    if not model.garment_type:
        return Response({'poms': [], 'warning': 'Garment type no definit'})

    from fhort.pom.models import GarmentPOMMap

    maps = GarmentPOMMap.objects.filter(
        garment_type=model.garment_type,
    ).select_related('pom', 'pom__pom_global').order_by('-is_key', 'ordre')

    result = []
    for m in maps:
        pom = m.pom
        pg = getattr(pom, 'pom_global', None)
        result.append({
            'pom_id': pom.id,
            'pom_code': pom.codi_client,
            'nom_en': pg.nom_en if pg else pom.nom_client,
            'nom_ca': pg.nom_ca if pg else pom.nom_client,
            'abbreviation': pg.abbreviation if pg else '',
            'categoria': pg.categoria if pg else '',
            'is_key': m.is_key,
            'ordre': m.ordre,
        })

    return Response({'poms': result, 'total': len(result)})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def taula_mesures_view(request, model_id):
    try:
        model = Model.objects.get(id=model_id)
    except Model.DoesNotExist:
        return Response({'error': 'Model no trobat'}, status=404)

    from fhort.models_app.models import BaseMeasurement

    size_run = []
    if model.size_run_model:
        size_run = [s.strip() for s in model.size_run_model.split('·') if s.strip()]

    base_measurements = BaseMeasurement.objects.filter(
        model=model,
        is_active=True,
    ).select_related('pom', 'pom__pom_global').order_by('ordre', 'pom__codi_client')

    graded_by_pom = {}
    try:
        from fhort.fitting.models import SizeFitting, GradingVersion, GradedSpec
        sf = SizeFitting.objects.filter(model=model).first()
        if sf:
            gv = GradingVersion.objects.filter(
                size_fitting=sf
            ).order_by('-data').first()
            if gv:
                for spec in GradedSpec.objects.filter(grading_version=gv):
                    pom_id = spec.pom_id
                    if pom_id not in graded_by_pom:
                        graded_by_pom[pom_id] = {}
                    graded_by_pom[pom_id][spec.size_label] = (
                        float(spec.graded_value_cm) if spec.graded_value_cm is not None else None
                    )
    except Exception:
        pass

    rows = []
    for bm in base_measurements:
        pom = bm.pom
        pg = getattr(pom, 'pom_global', None)
        rows.append({
            'id': bm.id,
            'ordre': bm.ordre,
            'pom_id': pom.id,
            'pom_code': pom.codi_client,
            'nom_fitxa': bm.nom_fitxa or '',
            'nom_en': pg.nom_en if pg else pom.nom_client,
            'nom_ca': pg.nom_ca if pg else pom.nom_client,
            'abbreviation': pg.abbreviation if pg else '',
            'base_value_cm': float(bm.base_value_cm) if bm.base_value_cm is not None else None,
            'origen': bm.origen,
            'notes': bm.notes or '',
            'graded': graded_by_pom.get(pom.id, {}),
        })

    base_size = model.base_size_label

    def _valor_talla(row, size):
        # El valor de la talla base viu a base_value_cm; la resta, a graded (GradedSpec).
        if size == base_size:
            return row['base_value_cm']
        return row['graded'].get(size)

    # Talles amb almenys un valor real (≠ null) en alguna fila.
    sizes_amb_dades = [
        s for s in size_run
        if any(_valor_talla(r, s) is not None for r in rows)
    ]

    # Δ = mitjana d'increments entre talles consecutives amb dades; None si <2 valors.
    deltes = {}
    for r in rows:
        valors = [_valor_talla(r, s) for s in sizes_amb_dades]
        valors = [v for v in valors if v is not None]
        if len(valors) >= 2:
            increments = [valors[i + 1] - valors[i] for i in range(len(valors) - 1)]
            deltes[str(r['pom_id'])] = round(sum(increments) / len(increments), 2)
        else:
            deltes[str(r['pom_id'])] = None

    return Response({
        'model_id': model.id,
        'codi_intern': model.codi_intern,
        'base_size': base_size,
        'size_run': size_run,               # mantingut per no trencar consumidors
        'size_run_complet': size_run,
        'sizes_amb_dades': sizes_amb_dades,
        'deltes': deltes,
        'rows': rows,
        'total_poms': len(rows),
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def set_measurements_view(request, model_id):
    try:
        model = Model.objects.get(id=model_id)
    except Model.DoesNotExist:
        return Response({'error': 'Model no trobat'}, status=404)

    measurements = request.data.get('measurements', [])
    if not measurements:
        return Response({'error': 'measurements és obligatori'}, status=400)

    from fhort.pom.models import POMMaster
    from fhort.models_app.models import BaseMeasurement

    created = updated = 0
    errors = []

    for m in measurements:
        pom_id = m.get('pom_id')
        value = m.get('base_value_cm')
        if not pom_id or value is None:
            errors.append(f'pom_id i base_value_cm obligatoris')
            continue
        try:
            pom = POMMaster.objects.get(id=pom_id)
            _, was_created = BaseMeasurement.objects.update_or_create(
                model=model, pom=pom,
                defaults={
                    'base_value_cm': float(value),
                    'notes': m.get('notes', ''),
                    'origen': 'MANUAL',
                }
            )
            if was_created: created += 1
            else: updated += 1
        except POMMaster.DoesNotExist:
            errors.append(f'POMMaster {pom_id} no trobat')

    try:
        from fhort.fitting.models import SizeFitting, GradingVersion, GradedSpec
        from fhort.pom.models import GradingRule, GradingRuleSet

        sf, _ = SizeFitting.objects.get_or_create(
            model=model,
            defaults={'size_system': model.size_system}
        )

        gv = GradingVersion.objects.create(size_fitting=sf)

        size_run = []
        if model.size_run_model:
            size_run = [s.strip() for s in model.size_run_model.split('·') if s.strip()]

        base_size = model.base_size_label

        all_bm = BaseMeasurement.objects.filter(model=model, is_active=True)
        grading_rule_set = model.grading_rule_set

        for bm in all_bm:
            base_val = float(bm.base_value_cm) if bm.base_value_cm else 0

            for size_label in size_run:
                if size_label == base_size:
                    graded_val = base_val
                else:
                    delta = 0
                    if grading_rule_set:
                        rule = GradingRule.objects.filter(
                            rule_set=grading_rule_set,
                            pom=bm.pom,
                            size_label=size_label,
                        ).first()
                        if rule:
                            delta = float(rule.increment_cm or 0)
                    graded_val = base_val + delta

                GradedSpec.objects.update_or_create(
                    grading_version=gv,
                    pom=bm.pom,
                    size_label=size_label,
                    defaults={'graded_value_cm': graded_val}
                )
    except Exception:
        pass

    return Response({'created': created, 'updated': updated, 'errors': errors},
                    status=201 if not errors else 207)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reorder_measurements_view(request, model_id):
    """
    Actualitza l'ordre de les BaseMeasurements d'un model.
    Payload: { order: [bm_id_1, bm_id_2, ...] }
    """
    try:
        model = Model.objects.get(id=model_id)
    except Model.DoesNotExist:
        return Response({'error': 'Model no trobat'}, status=404)

    order = request.data.get('order', [])
    if not order:
        return Response({'error': 'order és obligatori'}, status=400)

    from fhort.models_app.models import BaseMeasurement
    for i, bm_id in enumerate(order):
        BaseMeasurement.objects.filter(id=bm_id, model=model).update(ordre=i)

    return Response({'updated': len(order)})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def upload_fitxer_view(request, model_id):
    try:
        model = Model.objects.get(id=model_id)
    except Model.DoesNotExist:
        return Response({'error': 'Model no trobat'}, status=404)

    fitxer = request.FILES.get('fitxer')
    if not fitxer:
        return Response({'error': 'fitxer és obligatori'}, status=400)

    tipus = request.data.get('tipus', 'ALTRES')
    nom = request.data.get('nom') or fitxer.name

    # versio: incrementa l'última del mateix tipus
    ultima = ModelFitxer.objects.filter(model=model, tipus=tipus).order_by('-id').first()
    try:
        num_prev = int(ultima.versio) if ultima and ultima.versio else 0
    except (TypeError, ValueError):
        num_prev = 0
    versio = str(num_prev + 1)

    # Mapeig de tipus → categoria (existent) per coherència de filtres antics
    categoria_map = {
        'PATRO': 'Patro', 'MARCADA': 'Patro', 'ESCALAT': 'Patro',
        'SKETCH_FLETXES': 'Disseny', 'SKETCH_NET': 'Disseny',
        'FITXA': 'Document',
    }
    categoria = categoria_map.get(tipus, 'Document')

    mf = ModelFitxer.objects.create(
        model=model,
        fitxer=fitxer,
        nom_fitxer=nom,
        tipus=tipus,
        categoria=categoria,
        versio=versio,
        mida_bytes=fitxer.size,
        path_servidor=fitxer.name,
        pujat_per=getattr(request.user, 'profile', None),
    )

    return Response({
        'id': mf.id,
        'nom_fitxer': mf.nom_fitxer,
        'tipus': mf.tipus,
        'categoria': mf.categoria,
        'versio': mf.versio,
        'url': request.build_absolute_uri(mf.fitxer.url) if mf.fitxer else None,
    }, status=201)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def analisi_ia_view(request, model_id):
    try:
        model = Model.objects.get(id=model_id)
    except Model.DoesNotExist:
        return Response({'error': 'Model no trobat'}, status=404)

    import anthropic
    import base64
    import json
    from django.conf import settings

    base_measurements = BaseMeasurement.objects.filter(
        model=model, is_active=True
    ).select_related('pom').order_by('ordre')

    mesures_text = "\n".join([
        f"- {bm.pom.codi_client}: {bm.base_value_cm}cm ({bm.pom.nom_client or ''})"
        for bm in base_measurements
    ])

    fitxers_analisi = list(ModelFitxer.objects.filter(
        model=model,
        tipus__in=['PATRO', 'ESCALAT', 'SKETCH_FLETXES', 'SKETCH_NET']
    ).order_by('-id')[:5])

    content_blocks = []
    for mf in fitxers_analisi:
        if not mf.fitxer:
            continue
        try:
            with mf.fitxer.open('rb') as f:
                data = f.read()
            ext = mf.nom_fitxer.split('.')[-1].lower()
            if ext == 'pdf':
                content_blocks.append({
                    'type': 'document',
                    'source': {
                        'type': 'base64',
                        'media_type': 'application/pdf',
                        'data': base64.standard_b64encode(data).decode('utf-8'),
                    },
                    'title': mf.nom_fitxer,
                })
            elif ext in ('jpg', 'jpeg', 'png', 'svg'):
                media_map = {'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
                             'png': 'image/png', 'svg': 'image/svg+xml'}
                content_blocks.append({
                    'type': 'image',
                    'source': {
                        'type': 'base64',
                        'media_type': media_map.get(ext, 'image/png'),
                        'data': base64.standard_b64encode(data).decode('utf-8'),
                    },
                })
        except Exception:
            continue

    if not content_blocks:
        return Response({'error': 'No hi ha fitxers per analitzar'}, status=400)

    prompt = (
        f"Ets un expert tècnic en patronatge i especificació de peces de moda.\n\n"
        f"MODEL: {model.codi_intern} — {model.nom_prenda or ''}\n"
        f"TARGET: {model.target or ''} | CONSTRUCCIÓ: {model.construction or ''} | "
        f"FIT: {model.fit_type or ''}\n"
        f"TALLA BASE: {model.base_size_label or ''} | RUN: {model.size_run_model or ''}\n\n"
        f"MESURES DE LA TALLA BASE:\n{mesures_text or 'No hi ha mesures registrades.'}\n\n"
        "Analitza els fitxers adjunts i detecta discrepàncies. Retorna ÚNICAMENT aquest JSON:\n"
        "{\n"
        '  "alertes": [\n'
        "    {\n"
        '      "tipus": "DISCREPANCIA_TEIXIT|DISCREPANCIA_MESURA|DISCREPANCIA_ESCALAT|AVÍS_SKETCH|ALTRE",\n'
        '      "gravetat": "CRITICA|IMPORTANT|INFORMATIVA",\n'
        '      "descripcio": "descripció clara del problema",\n'
        '      "pom_afectat": "codi POM o null",\n'
        '      "valor_taula": "valor a la taula o null",\n'
        '      "valor_patro": "valor al patró o null",\n'
        '      "accio_suggerida": "què hauria de fer el tècnic"\n'
        "    }\n"
        "  ],\n"
        '  "resum": "resum breu de l\'anàlisi",\n'
        f'  "fitxers_analitzats": {len(fitxers_analisi)}\n'
        "}"
    )

    content_blocks.append({'type': 'text', 'text': prompt})

    try:
        api_key = getattr(settings, 'ANTHROPIC_API_KEY', None)
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model='claude-opus-4-5',
            max_tokens=4096,
            messages=[{'role': 'user', 'content': content_blocks}],
            extra_headers={'anthropic-beta': 'pdfs-2024-09-25'},
        )
        text = response.content[0].text
        text = text.replace('```json', '').replace('```', '').strip()
        resultat = json.loads(text)
        return Response({
            'model_id': model_id,
            'analisi': resultat,
            'fitxers_analitzats': len(fitxers_analisi),
        })
    except json.JSONDecodeError as e:
        return Response({'error': f'Resposta IA no parsejable: {e}'}, status=500)
    except Exception as e:
        return Response({'error': f'Error IA: {e}'}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def xat_mesures_view(request, model_id):
    try:
        model = Model.objects.get(id=model_id)
    except Model.DoesNotExist:
        return Response({'error': 'Model no trobat'}, status=404)

    missatge = (request.data.get('missatge') or '').strip()
    historial = request.data.get('historial', []) or []

    if not missatge:
        return Response({'error': 'missatge és obligatori'}, status=400)

    from fhort.pom.models import POMMaster

    base_measurements = BaseMeasurement.objects.filter(
        model=model, is_active=True
    ).select_related('pom').order_by('ordre')

    mesures_context = "\n".join([
        f"ID:{bm.id} | CODI:{bm.pom.codi_client} | "
        f"NOM:{bm.pom.nom_client or bm.pom.codi_client} | VALOR:{bm.base_value_cm}cm"
        for bm in base_measurements
    ])

    system_prompt = (
        f"Ets un assistent tècnic de patronatge per al model {model.codi_intern}.\n"
        "Pots fer canvis REALS a les mesures. Quan l'usuari demani un canvi, retorna un JSON d'acció.\n\n"
        f"MESURES ACTUALS:\n{mesures_context}\n\n"
        "Respon SEMPRE amb aquest format JSON:\n"
        "{\n"
        '  "resposta": "text de resposta a l\'usuari en català",\n'
        '  "accions": [\n'
        '    {\n'
        '      "tipus": "ACTUALITZAR|AFEGIR|ELIMINAR|CAP",\n'
        '      "bm_id": <id del BaseMeasurement o null si és nou>,\n'
        '      "pom_codi": "codi del POM",\n'
        '      "valor": <float o null>,\n'
        '      "nom_fitxa": "nomenclatura nova o null"\n'
        '    }\n'
        '  ]\n'
        "}\n\n"
        "Regles:\n"
        "- Si l'usuari corregeix un valor, usa tipus ACTUALITZAR amb el bm_id corresponent\n"
        "- Si demana afegir un POM nou, usa tipus AFEGIR (bm_id=null)\n"
        "- Si demana eliminar, usa tipus ELIMINAR\n"
        "- Si és una pregunta sense acció, usa tipus CAP i accions=[]\n"
        "- Sempre confirma l'acció a la resposta en català"
    )

    import anthropic
    import json
    from django.conf import settings

    messages = historial + [{'role': 'user', 'content': missatge}]

    try:
        client = anthropic.Anthropic(api_key=getattr(settings, 'ANTHROPIC_API_KEY', None))
        response = client.messages.create(
            model='claude-sonnet-4-5',
            max_tokens=1024,
            system=system_prompt,
            messages=messages,
        )
        text = response.content[0].text.replace('```json', '').replace('```', '').strip()
        resultat = json.loads(text)

        accions_executades = []
        for accio in resultat.get('accions', []):
            tipus = accio.get('tipus')
            try:
                if tipus == 'ACTUALITZAR' and accio.get('bm_id'):
                    bm = BaseMeasurement.objects.get(id=accio['bm_id'], model=model)
                    if accio.get('valor') is not None:
                        bm.base_value_cm = float(accio['valor'])
                    if accio.get('nom_fitxa') is not None:
                        bm.nom_fitxa = accio['nom_fitxa']
                    bm.save()
                    accions_executades.append(
                        f"Actualitzat {bm.pom.codi_client} = {bm.base_value_cm}cm"
                    )
                elif tipus == 'AFEGIR' and accio.get('pom_codi'):
                    pom = POMMaster.objects.filter(
                        codi_client__iexact=accio['pom_codi']
                    ).first()
                    if pom and accio.get('valor') is not None:
                        bm, created = BaseMeasurement.objects.update_or_create(
                            model=model, pom=pom,
                            defaults={
                                'base_value_cm': float(accio['valor']),
                                'origen': 'MANUAL',
                                'ordre': base_measurements.count(),
                            },
                        )
                        accions_executades.append(
                            f"{'Afegit' if created else 'Actualitzat'} {pom.codi_client}"
                        )
                elif tipus == 'ELIMINAR' and accio.get('bm_id'):
                    bm = BaseMeasurement.objects.get(id=accio['bm_id'], model=model)
                    nom = bm.pom.codi_client
                    bm.is_active = False
                    bm.save()
                    accions_executades.append(f"Eliminat {nom}")
            except Exception as e:
                accions_executades.append(f"Error: {e}")

        mesures_actualitzades = list(
            BaseMeasurement.objects.filter(model=model, is_active=True)
            .select_related('pom').order_by('ordre')
            .values('id', 'pom__codi_client', 'base_value_cm', 'nom_fitxa', 'ordre')
        )

        return Response({
            'resposta': resultat.get('resposta', ''),
            'accions_executades': accions_executades,
            'mesures_actualitzades': mesures_actualitzades,
            'historial_nou': messages + [{'role': 'assistant', 'content': text}],
        })
    except json.JSONDecodeError as e:
        return Response({'error': f'Error parsing IA: {e}'}, status=500)
    except Exception as e:
        return Response({'error': f'Error: {e}'}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generar_grading_view(request, model_id):
    try:
        model = Model.objects.get(id=model_id)
    except Model.DoesNotExist:
        return Response({'error': 'Model no trobat'}, status=404)

    if not model.grading_rule_set_id:
        return Response({'error': 'El model no té GradingRuleSet configurat'}, status=400)
    if not model.size_run_model or not model.base_size_label:
        return Response({'error': 'Cal configurar talles i talla base'}, status=400)

    from fhort.fitting.models import SizeFitting, GradingVersion, GradedSpec
    from fhort.pom.services import generar_graded_specs

    base_measurements_qs = BaseMeasurement.objects.filter(model=model, is_active=True)
    if not base_measurements_qs.exists():
        return Response({'error': 'No hi ha mesures base'}, status=400)

    # Obtenir o crear SizeFitting amb els camps obligatoris reals
    sf = SizeFitting.objects.filter(model=model).first()
    if not sf:
        next_num = 1
        codi = f"{model.codi_intern}-SF-{next_num}"
        while SizeFitting.objects.filter(codi=codi).exists():
            next_num += 1
            codi = f"{model.codi_intern}-SF-{next_num}"
        profile = getattr(request.user, 'profile', None)
        try:
            sf = SizeFitting.objects.create(
                model=model,
                numero=next_num,
                codi=codi,
                tipus='SizeSet',
                creat_per=profile,
            )
        except Exception as e:
            return Response({'error': f'Error creant SizeFitting: {e}'}, status=500)

    # Cridar el motor existent
    try:
        graded_count = generar_graded_specs(sf.id)
    except ValueError as e:
        return Response({'error': str(e)}, status=400)
    except Exception as e:
        return Response({'error': f'Error generant grading: {e}'}, status=500)

    # Construir resposta tipus taula-mesures
    size_run = [s.strip() for s in model.size_run_model.split('·') if s.strip()]
    gv = GradingVersion.objects.filter(size_fitting=sf).order_by('-data').first()

    rows = []
    for bm in (
        BaseMeasurement.objects.filter(model=model, is_active=True)
        .select_related('pom', 'pom__pom_global').order_by('ordre')
    ):
        pom = bm.pom
        pg = getattr(pom, 'pom_global', None)
        graded = {}
        if gv:
            for spec in GradedSpec.objects.filter(grading_version=gv, pom=pom):
                graded[spec.size_label] = (
                    float(spec.graded_value_cm) if spec.graded_value_cm is not None else None
                )
        rows.append({
            'id': bm.id,
            'pom_id': pom.id,
            'pom_code': pom.codi_client,
            'nom_fitxa': bm.nom_fitxa or '',
            'nom_ca': pg.nom_ca if pg else pom.nom_client,
            'nom_en': pg.nom_en if pg else pom.nom_client,
            'base_value_cm': float(bm.base_value_cm) if bm.base_value_cm is not None else None,
            'graded': graded,
            'ordre': bm.ordre,
        })

    return Response({
        'model_id': model_id,
        'graded_count': graded_count,
        'size_run': size_run,
        'base_size': model.base_size_label,
        'rows': rows,
    })


ISO_SHRINKAGE_TABLE = [
    {'id': 'woven_cotton',    'nom': 'Woven Cotton',    'warp': 3.0, 'weft': 3.0},
    {'id': 'woven_linen',     'nom': 'Woven Linen',     'warp': 3.0, 'weft': 3.0},
    {'id': 'woven_viscose',   'nom': 'Woven Viscose',   'warp': 4.0, 'weft': 4.0},
    {'id': 'woven_silk',      'nom': 'Woven Silk',      'warp': 2.0, 'weft': 2.0},
    {'id': 'woven_polyester', 'nom': 'Woven Polyester', 'warp': 1.0, 'weft': 1.0},
    {'id': 'knit_cotton',     'nom': 'Knit Cotton',     'warp': 5.0, 'weft': 5.0},
    {'id': 'knit_jersey',     'nom': 'Knit Jersey',     'warp': 5.0, 'weft': 5.0},
    {'id': 'stretch_knit',    'nom': 'Stretch Knit',    'warp': 8.0, 'weft': 8.0},
    {'id': 'knit_wool',       'nom': 'Knit Wool',       'warp': 6.0, 'weft': 6.0},
    {'id': 'denim',           'nom': 'Denim',           'warp': 5.0, 'weft': 3.0},
    {'id': 'technical',       'nom': 'Technical',       'warp': 0.0, 'weft': 0.0},
]


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def iso_shrinkage_view(request):
    return Response(ISO_SHRINKAGE_TABLE)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_fabric_view(request, model_id):
    try:
        model = Model.objects.get(id=model_id)
    except Model.DoesNotExist:
        return Response({'error': 'Model no trobat'}, status=404)

    fields = ['fabric_main', 'fabric_composition', 'shrinkage_type',
              'shrinkage_warp', 'shrinkage_weft', 'shrinkage_pct', 'fabric_notes']
    for f in fields:
        if f in request.data:
            setattr(model, f, request.data[f])
    model.save()
    return Response({'id': model.id, 'fabric_main': model.fabric_main})
