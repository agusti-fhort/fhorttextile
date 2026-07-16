# F4 P-LEGAL — lògica compartida (pending + acceptació + IP real). Viu al backoffice
# (SHARED/public) i la consumeixen: els endpoints del backoffice (views_legal) i les
# incursions al tenant (gate /me + accept del tenant), sense duplicar la vista.
from .models import LegalDocument, LegalDocumentVersion, LegalAcceptance


def client_ip(request):
    """IP real del client. Rere nginx, el REMOTE_ADDR és el proxy: la IP de l'usuari
    és la PRIMERA entrada de X-Forwarded-For (nginx hi afegeix, en ordre, client→proxies).
    F4 és el primer consumidor que la necessita bé; s'assumeix nginx com a únic proxy de
    confiança (config estàndard `proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for`)."""
    xff = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if xff:
        primera = xff.split(',')[0].strip()
        if primera:
            return primera
    return request.META.get('REMOTE_ADDR') or None


def vigents_publicades():
    """Última versió PUBLICADA de cada document ACTIU (les 'vigents')."""
    out = []
    for doc in LegalDocument.objects.filter(actiu=True):
        v = (doc.versions.filter(estat=LegalDocumentVersion.ESTAT_PUBLICADA)
             .order_by('-numero_versio').first())
        if v is not None:
            out.append(v)
    return out


def pending_versions_for_client(client, nomes_reacceptacio=False):
    """Versions vigents (última publicada de cada document actiu) que el client NO ha
    acceptat. Amb `nomes_reacceptacio=True` (gate del /me) es filtra a les que porten
    requereix_reacceptacio=True."""
    if client is None:
        return []
    acceptades = set(
        LegalAcceptance.objects.filter(client=client).values_list('versio_id', flat=True))
    pend = [v for v in vigents_publicades() if v.id not in acceptades]
    if nomes_reacceptacio:
        pend = [v for v in pend if v.requereix_reacceptacio]
    return pend


def record_acceptance(client, versio, accepted_by, request, metode):
    """Registra (idempotent) una LegalAcceptance. Re-acceptar la mateixa (client, versio)
    NO duplica: get_or_create per la clau única. Retorna (acceptance, created)."""
    if versio.estat != LegalDocumentVersion.ESTAT_PUBLICADA:
        raise ValueError('Només es poden acceptar versions PUBLICADES.')
    acc, created = LegalAcceptance.objects.get_or_create(
        client=client, versio=versio,
        defaults=dict(
            accepted_by=(accepted_by or '').strip(),
            ip=client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:2000],
            metode=metode,
        ),
    )
    return acc, created
