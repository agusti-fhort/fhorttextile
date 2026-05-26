"""
fhort/models_app/chat_views.py
Endpoint de xat IA per al wizard d'extracció de fitxa tècnica.
Manté el context del document + extracció + historial de conversa.
"""
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
import json
import base64
import logging

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Ets un assistent tècnic especialitzat en desenvolupament de moda i fitxes tècniques.

Estàs ajudant un tècnic de patronatge a revisar i completar les dades d'una fitxa tècnica.
Tens accés al document original que ha pujat (PDF, imatge o sketch) i a les dades que 
el sistema ha extret automàticament.

El teu objectiu és:
1. Identificar els camps que falten o que no s'han pogut extreure amb confiança
2. Fer preguntes concretes i específiques per completar-los
3. Detectar inconsistències entre el document i les dades extretes
4. Si el document conté múltiples models o sketches, identificar-los i preguntar com procedir
5. Actualitzar el JSON d'extracció quan el tècnic confirmi informació

Quan tinguis prou informació per completar un camp, retorna un JSON especial al final 
de la teva resposta amb el format:
<UPDATE_JSON>
{
  "camp": "valor_confirmat"
}
</UPDATE_JSON>

Parla sempre en català. Sigues concís i professional. 
No inventis dades — si no estàs segur, pregunta.
Si veus múltiples peces en el document, pregunta quin model vol processar primer."""


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser, MultiPartParser, FormParser])
def chat_extraccio_view(request):
    """
    POST /api/v1/models/chat-extraccio/
    Body (JSON):
    {
      "missatge": "text del tècnic",
      "historial": [...],          // array de {role, content}
      "extraccio": {...},           // JSON extret fins ara
      "file_base64": "...",         // opcional: fitxer en base64
      "file_type": "application/pdf" // opcional: MIME type
    }
    
    Retorna:
    {
      "resposta": "text de la IA",
      "updates": {...},   // camps nous detectats (si n'hi ha)
      "historial": [...]  // historial actualitzat
    }
    """
    missatge = request.data.get('missatge', '').strip()
    historial = request.data.get('historial', [])
    extraccio = request.data.get('extraccio', {})
    file_base64 = request.data.get('file_base64')
    file_type = request.data.get('file_type', 'application/pdf')

    if not missatge:
        return Response({'error': 'El camp "missatge" és obligatori'}, status=400)

    try:
        import os
        api_key = os.environ.get('ANTHROPIC_API_KEY') or getattr(
            __import__('django.conf', fromlist=['settings']).settings,
            'ANTHROPIC_API_KEY', None
        )
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY no configurat")

        import httpx

        # Construir el context del document
        extraccio_resum = _resum_extraccio(extraccio)

        # Missatge del sistema amb context actual
        system_with_context = SYSTEM_PROMPT + f"""

DADES EXTRETES FINS ARA:
{extraccio_resum}

CAMPS AMB CONFIANÇA BAIXA O BUITS:
{_camps_pendents(extraccio)}
"""

        # Construir els missatges
        messages = []

        # Afegir historial previ
        for msg in historial[-10:]:  # Màxim 10 missatges anteriors
            messages.append({
                'role': msg['role'],
                'content': msg['content']
            })

        # Missatge nou del tècnic — amb o sense fitxer
        if file_base64 and len(messages) == 0:
            # Primer missatge: incloure el document
            if file_type == 'application/pdf':
                content = [
                    {
                        'type': 'document',
                        'source': {
                            'type': 'base64',
                            'media_type': 'application/pdf',
                            'data': file_base64,
                        }
                    },
                    {'type': 'text', 'text': missatge or "Analitza aquest document i diga'm quines dades falten."}
                ]
            else:
                content = [
                    {
                        'type': 'image',
                        'source': {
                            'type': 'base64',
                            'media_type': file_type,
                            'data': file_base64,
                        }
                    },
                    {'type': 'text', 'text': missatge or "Analitza aquesta imatge i diga'm quines dades falten."}
                ]
        else:
            content = missatge

        messages.append({'role': 'user', 'content': content})

        # Crida a Claude API
        payload = {
            'model': 'claude-sonnet-4-6',
            'max_tokens': 1024,
            'system': system_with_context,
            'messages': messages,
        }

        headers = {
            'x-api-key': api_key,
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json',
            'anthropic-beta': 'pdfs-2024-09-25',
        }

        with httpx.Client(timeout=60.0) as client:
            resp = client.post(
                'https://api.anthropic.com/v1/messages',
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()

        data = resp.json()
        resposta_text = data['content'][0]['text']

        # Detectar UPDATE_JSON a la resposta
        updates = {}
        if '<UPDATE_JSON>' in resposta_text and '</UPDATE_JSON>' in resposta_text:
            try:
                start = resposta_text.index('<UPDATE_JSON>') + len('<UPDATE_JSON>')
                end = resposta_text.index('</UPDATE_JSON>')
                json_str = resposta_text[start:end].strip()
                updates = json.loads(json_str)
                # Netejar el tag de la resposta visible
                resposta_text = resposta_text.replace(
                    resposta_text[resposta_text.index('<UPDATE_JSON>'):
                                   resposta_text.index('</UPDATE_JSON>') + len('</UPDATE_JSON>')],
                    ''
                ).strip()
            except Exception:
                pass

        # Actualitzar historial
        nou_historial = list(historial) + [
            {'role': 'user', 'content': missatge},
            {'role': 'assistant', 'content': resposta_text},
        ]

        return Response({
            'resposta': resposta_text,
            'updates': updates,
            'historial': nou_historial[-20:],  # Màxim 20 missatges
        })

    except ValueError as e:
        return Response({'error': str(e)}, status=422)
    except Exception as e:
        logger.exception("Error al xat d'extracció")
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def iniciar_chat_extraccio_view(request):
    """
    POST /api/v1/models/iniciar-chat-extraccio/
    Inicia el xat amb el primer missatge de la IA basant-se 
    en l'extracció ja feta. No requereix el fitxer de nou.
    
    Body: { "extraccio": {...} }
    """
    extraccio = request.data.get('extraccio', {})

    try:
        import os, httpx

        api_key = os.environ.get('ANTHROPIC_API_KEY') or getattr(
            __import__('django.conf', fromlist=['settings']).settings,
            'ANTHROPIC_API_KEY', None
        )
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY no configurat")

        pendents = _camps_pendents(extraccio)
        resum = _resum_extraccio(extraccio)

        # Generar el primer missatge de benvinguda de la IA
        prompt_inici = f"""Acabo d'analitzar el document tècnic. Aquí tens el resum del que he trobat:

{resum}

{f'Els camps pendents de confirmar són:{pendents}' if pendents.strip() else 'He pogut extreure totes les dades principals.'}

Pots fer-me preguntes sobre el document, confirmar o corregir qualsevol dada, 
o dir-me quines talles tindrà el model si no les he detectat.

Per on vols començar?"""

        payload = {
            'model': 'claude-sonnet-4-6',
            'max_tokens': 512,
            'system': SYSTEM_PROMPT,
            'messages': [{'role': 'user', 'content': prompt_inici}],
        }

        headers = {
            'x-api-key': api_key,
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json',
        }

        with httpx.Client(timeout=30.0) as client:
            resp = client.post('https://api.anthropic.com/v1/messages', json=payload, headers=headers)
            resp.raise_for_status()

        data = resp.json()
        resposta = data['content'][0]['text']

        historial_inicial = [
            {'role': 'user', 'content': prompt_inici},
            {'role': 'assistant', 'content': resposta},
        ]

        return Response({
            'resposta': resposta,
            'historial': historial_inicial,
        })

    except Exception as e:
        logger.exception("Error iniciant xat")
        return Response({'error': str(e)}, status=500)


def _resum_extraccio(extraccio):
    """Genera un resum llegible de les dades extretes."""
    if not extraccio:
        return "Sense dades extretes."

    lines = []

    def val(field):
        v = extraccio.get(field)
        if isinstance(v, dict): return v.get('value')
        return v

    def conf(field):
        v = extraccio.get(field)
        if isinstance(v, dict): return v.get('confidence', '?')
        return 'high' if v else 'low'

    camps = [
        ('Marca', 'brand'), ('Estil', 'style_name'), ('Codi', 'style_code'),
        ('Temporada', 'season'), ('Any', 'year'), ('Prenda', 'garment_type'),
        ('Material', 'main_fabric'), ('Composició', 'fabric_composition'),
        ('Talla base', 'base_size'), ('Run talles', 'size_run'),
    ]

    for label, field in camps:
        v = val(field)
        c = conf(field)
        if v:
            conf_str = '✓' if c == 'high' else '~' if c == 'medium' else '?' if c == 'low' else ''
            lines.append(f"  {conf_str} {label}: {v}")

    poms = extraccio.get('poms', [])
    if poms:
        poms_amb_val = [p for p in poms if p.get('base_value_cm')]
        lines.append(f"  POMs: {len(poms)} detectats, {len(poms_amb_val)} amb valor")

    grading = extraccio.get('has_grading_table', False)
    if grading:
        lines.append("  ✓ Taula de grading inclosa")

    fit_comments = extraccio.get('fit_comments', [])
    if fit_comments:
        lines.append(f"  Fit comments: {len(fit_comments)} correccions")

    return '\n'.join(lines) if lines else "Document buit o no reconegut."


def _camps_pendents(extraccio):
    """Retorna llista de camps buits o amb confiança baixa."""
    if not extraccio:
        return "Tots els camps pendents."

    pendents = []

    def val(field):
        v = extraccio.get(field)
        if isinstance(v, dict): return v.get('value')
        return v

    def conf(field):
        v = extraccio.get(field)
        if isinstance(v, dict): return v.get('confidence', 'low')
        return 'high' if v else 'low'

    camps_obligatoris = [
        ('Nom del model', 'style_name'),
        ('Temporada', 'season'),
        ('Any', 'year'),
        ('Tipus de prenda', 'garment_type'),
        ('Material principal', 'main_fabric'),
        ('Composició', 'fabric_composition'),
        ('Talla base', 'base_size'),
        ('Run de talles', 'size_run'),
    ]

    for label, field in camps_obligatoris:
        v = val(field)
        c = conf(field)
        if not v:
            pendents.append(f"  ✗ {label}: no detectat")
        elif c == 'low':
            pendents.append(f"  ? {label}: {v} (confiança baixa — confirma)")
        elif c == 'medium':
            pendents.append(f"  ~ {label}: {v} (confirma si és correcte)")

    poms = extraccio.get('poms', [])
    poms_sense_valor = [p for p in poms if not p.get('base_value_cm')]
    if poms_sense_valor:
        pendents.append(f"  ~ {len(poms_sense_valor)} POMs sense valor de talla base")

    blockers = extraccio.get('design_freeze_blockers', [])
    if blockers:
        for b in blockers:
            pendents.append(f"  ✗ BLOQUEJANT: {b}")

    return '\n'.join(pendents) if pendents else "Tots els camps principals estan complets."
