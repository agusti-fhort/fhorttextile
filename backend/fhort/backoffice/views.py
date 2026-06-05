from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(['GET'])
@permission_classes([AllowAny])
def health_view(request):
    """Health check del routing public del backoffice (Sprint 0a). Sense auth."""
    return Response({'status': 'ok', 'scope': 'backoffice'})
