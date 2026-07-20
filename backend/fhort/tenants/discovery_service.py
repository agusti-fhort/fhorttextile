"""Tenant-discovery: donat un email, trobar en quin(s) tenant(s) té compte, i avisar-lo per
correu (best-effort). Viu al schema PUBLIC (l'endpoint és a fhort.urls_public).

PRIVADESA (llei d'aquest mòdul): la revelació de "aquest email existeix" NOMÉS pot arribar per
la BÚSTIA del titular (el correu). Cap camí d'aquest mòdul torna informació d'existència al
cridador HTTP. L'enviament és best-effort: si l'SMTP falla, es registra i s'empassa — mai
canvia la resposta ni propaga (la resposta uniforme la garanteix la vista).

Reutilitza el patró canònic provat (management commands): enumerar tenants
(get_tenant_model().objects.exclude(schema_name=public)) + entrar a cada schema (schema_context)
+ buscar l'usuari (User.objects.filter(email__iexact=..., is_active=True)) — mateixa semàntica
que EmailOrUsernameBackend (accounts/backends.py).
"""
import logging

from django.contrib.auth import get_user_model
from django_tenants.utils import get_tenant_model, get_public_schema_name, schema_context

logger = logging.getLogger(__name__)


def find_workspaces_for_email(email):
    """Retorna la llista de workspaces (tenants) on `email` és un usuari ACTIU.
    Cada element: {'schema', 'nom', 'host'}. host = domini primari del tenant (o el primer).
    Recorre SEMPRE tots els tenants (cap early-out) perquè el cost/temps no depengui del
    resultat (mitigació d'enumeració per timing). Llista buida si no hi és enlloc."""
    email = (email or '').strip()
    if not email:
        return []
    Client = get_tenant_model()
    User = get_user_model()
    public = get_public_schema_name()
    workspaces = []
    for tenant in Client.objects.exclude(schema_name=public):
        with schema_context(tenant.schema_name):
            exists = User.objects.filter(email__iexact=email, is_active=True).exists()
        if exists:
            dom = tenant.domains.filter(is_primary=True).first() or tenant.domains.first()
            workspaces.append({
                'schema': tenant.schema_name,
                'nom': tenant.nom,
                'host': dom.domain if dom is not None else None,
            })
    return workspaces


def build_discovery_email(workspaces):
    """Cos del correu (text pla, monolingüe català per convenció de backend). Un enllaç per
    workspace; amb >1, actua de selector dins el correu."""
    linies = []
    for w in workspaces:
        if w.get('host'):
            linies.append(f"· {w['nom']}: https://{w['host']}/login")
        else:
            linies.append(f"· {w['nom']}")
    cos = (
        "Hola,\n\n"
        "Has demanat accés a FHORT Textile Tech. Aquests són els teus espais de treball:\n\n"
        + "\n".join(linies)
        + "\n\nObre l'enllaç del teu espai i entra amb la teva contrasenya.\n"
        "Si no has demanat això, pots ignorar aquest correu.\n"
    )
    return cos


def send_discovery_email(email, workspaces):
    """Envia (best-effort) el correu de discovery si hi ha workspaces. MAI llança: una fallada
    d'SMTP no pot afectar la resposta uniforme ni filtrar existència."""
    if not workspaces:
        return False
    from django.core.mail import send_mail
    try:
        send_mail(
            subject="El teu accés a FHORT Textile Tech",
            message=build_discovery_email(workspaces),
            from_email=None,   # DEFAULT_FROM_EMAIL
            recipient_list=[email],
            fail_silently=True,
        )
        return True
    except Exception:   # noqa: BLE001 — best-effort dur: res pot escapar cap a la resposta
        logger.exception("discovery: enviament de correu fallit (best-effort, empassat)")
        return False
