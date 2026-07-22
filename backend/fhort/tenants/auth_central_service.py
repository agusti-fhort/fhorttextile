"""Autenticació CENTRAL cross-schema + cicle de vida dels codis d'un sol ús (F1).

Què resol: amb django-tenants, les contrasenyes viuen a l'`auth_user` de CADA schema. El
`/api/token/` del public valida contra l'`auth_user` del public (usuaris de backoffice) i no
sap res dels usuaris de tenant (DIAGNOSI_LOGIN_UNIC §B4.3). Una porta d'entrada única, doncs,
ha de provar les credencials DINS de cada schema candidat. Això és el que fa aquest mòdul.

Reutilitza la peça bona del tenant-discovery (`find_workspaces_for_email`, provada i amb 9
tests): la mateixa passada per tots els tenants, sense early-out, que ja mitiga l'enumeració
per temps. El que hi afegeix és l'`authenticate()` dins de `schema_context`, amb el backend
del projecte (`EmailOrUsernameBackend`) — cap còpia de la lògica de credencials.

PRIVADESA — l'única resposta que existeix per a un fracàs és la genèrica. «Aquest email no hi
és» i «la contrasenya no és bona» han de ser INDISTINGIBLES: en cos, en codi HTTP i, tant com
es pugui, en temps. D'aquí el hash en va de `_crema_temps_de_hash()` quan no hi ha cap
candidat: sense això, un email inexistent tornaria sense fer mai un PBKDF2 i el rellotge del
client diria el que el cos calla.

Els codis (`CodiAuth`) sempre es toquen DES DEL PUBLIC de manera explícita. Amb django-tenants
el `search_path` d'un tenant ja inclou `public` i la taula es resoldria igualment, però
dependre d'això és dependre d'un efecte lateral: aquestes files són d'àmbit central i el codi
ho ha de dir.
"""
import hashlib
import logging
import secrets

from django.contrib.auth import authenticate, get_user_model
from django.utils import timezone
from django_tenants.utils import get_public_schema_name, get_tenant_model, schema_context

from .discovery_service import find_workspaces_for_email
from .models import CodiAuth

logger = logging.getLogger(__name__)

#: Bytes d'entropia del codi. `token_urlsafe(32)` → 43 caràcters, 256 bits: no s'endevina.
BYTES_CODI = 32


def _hash(codi):
    """El que es desa. Vegeu `CodiAuth` per què no és el codi en clar."""
    return hashlib.sha256((codi or '').encode()).hexdigest()


def _crema_temps_de_hash(password):
    """Fa una verificació de contrasenya que no pot reeixir mai.

    Mitigació de timing estàndard (la mateixa que fa `ModelBackend` de Django al seu camí
    d'usuari inexistent): quan no hi ha cap schema candidat no es faria cap PBKDF2 i la
    resposta arribaria molt abans que la d'un email que sí que existeix.
    """
    get_user_model()().check_password(password or '')


def autentica_cross_schema(email, password):
    """Els workspaces on `email`+`password` són credencials VÀLIDES.

    Retorna `[{'schema', 'nom', 'user_id'}, …]`, possiblement buida i possiblement amb més
    d'un element: si una persona reutilitza la contrasenya a dos workspaces, tots dos són
    seus i tots dos són respostes legítimes. Mai llança per credencials dolentes.
    """
    email = (email or '').strip()
    if not email or not password:
        _crema_temps_de_hash(password)
        return []

    # Passada completa per tots els tenants (la del discovery: cap early-out).
    candidats = find_workspaces_for_email(email)
    if not candidats:
        _crema_temps_de_hash(password)
        return []

    valids = []
    for w in candidats:
        with schema_context(w['schema']):
            # request=None a posta: aquí no hi ha sessió ni middleware; només credencials.
            user = authenticate(request=None, username=email, password=password)
            if user is not None:
                valids.append({'schema': w['schema'], 'nom': w['nom'], 'user_id': user.pk})
    return valids


def resol_host(schema, host_actual=None):
    """El domini pel qual s'ha d'arribar a `schema`, vist des de `host_actual`.

    Si el tenant TÉ el host des del qual s'està entrant, aquell mana per damunt del primari.
    No és una comoditat: a staging el primari del tenant `fhort` és `fhorttextile.tech`
    (PROD) i `staging.fhorttextile.tech` és `is_primary=False` (DIAGNOSI_LOGIN_UNIC §B2.2).
    Sense aquesta regla, entrar des de staging redirigiria a producció. La mateixa regla és
    la que a PROD fa que el flux des de `login.*` (que no és de cap tenant) caigui al primari,
    que és el que allà toca.
    """
    host_actual = (host_actual or '').split(':')[0].lower()
    with schema_context(get_public_schema_name()):
        tenant = get_tenant_model().objects.filter(schema_name=schema).first()
        if tenant is None:
            return None
        dominis = list(tenant.domains.all())
    for d in dominis:
        if d.domain.lower() == host_actual:
            return d.domain
    primari = next((d for d in dominis if d.is_primary), None) or (dominis[0] if dominis else None)
    return primari.domain if primari is not None else None


def nom_del_tenant(schema):
    """Nom visible d'un schema. Cadena buida si el tenant ja no hi és."""
    with schema_context(get_public_schema_name()):
        tenant = get_tenant_model().objects.filter(schema_name=schema).first()
    return tenant.nom if tenant is not None else ''


def descriu_workspace(schema, nom, host_actual=None):
    """La forma en què un workspace es presenta al client.

    `mateix_host` el calcula el SERVIDOR. El frontend no ha de deduir de cap domini res que
    el backend ja sap (`client.js:3-19`), i és el que permet el cas C5: si el workspace triat
    és el host on ja som, no hi ha res a redirigir — es bescanvia aquí mateix.
    """
    host = resol_host(schema, host_actual)
    actual = (host_actual or '').split(':')[0].lower()
    return {
        'schema': schema,
        'nom': nom,
        'host': host,
        'mateix_host': bool(host) and host.lower() == actual,
    }


def _neteja_oportunista():
    """Esborra els codis passats de rosca. Sense cron nou: es paga a cada emissió.

    Es filtra per `created_at` i no per `used_at`: un codi mai bescanviat també ha de morir,
    i el llindar de retenció és prou per sobre del TTL més llarg perquè cap fila viva hi
    caigui. Errors empassats: la neteja MAI pot fer fracassar un login.
    """
    try:
        CodiAuth.objects.filter(
            created_at__lt=timezone.now() - CodiAuth.TTL_RETENCIO,
        ).delete()
    except Exception:   # noqa: BLE001 — higiene, no camí crític
        logger.exception('codis auth: neteja oportunista fallida (empassada)')


def emet_codi(mena, *, tenant_schema='', user_id=None, candidats=None):
    """Crea un codi viu i en retorna el valor EN CLAR (única vegada que existeix)."""
    codi = secrets.token_urlsafe(BYTES_CODI)
    with schema_context(get_public_schema_name()):
        _neteja_oportunista()
        CodiAuth.objects.create(
            codi_hash=_hash(codi),
            mena=mena,
            tenant_schema=tenant_schema or '',
            user_id=user_id,
            candidats=candidats or [],
        )
    return codi


def consumeix_codi(codi, mena):
    """Marca el codi com a usat i el retorna. `None` si no es pot consumir, sense dir per què.

    El consum és un UPDATE CONDICIONAL i el veredicte és el nombre de files afectades: si dos
    bescanvis simultanis arriben amb el mateix codi, tots dos passen la lectura però només un
    escriu `used_at` — l'altre veu 0 files i cau. Comprovar-i-després-marcar en dos passos
    deixaria justament aquesta escletxa.

    La caducitat entra a la MATEIXA sentència (`created_at__gte`), no en una comprovació
    prèvia, pel mateix motiu.
    """
    if not codi:
        return None
    h = _hash(codi)
    ara = timezone.now()
    ttl = CodiAuth.TTL_SELECCIO if mena == CodiAuth.MENA_SELECCIO else CodiAuth.TTL_BESCANVI
    with schema_context(get_public_schema_name()):
        files = CodiAuth.objects.filter(
            codi_hash=h,
            mena=mena,
            used_at__isnull=True,
            created_at__gte=ara - ttl,
        ).update(used_at=ara)
        if files != 1:
            return None
        return CodiAuth.objects.filter(codi_hash=h).first()
