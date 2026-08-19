"""Capacitats i resolució de permisos (Sprint A). Font de veritat única."""
from django.db.models import Q
from rest_framework.permissions import BasePermission

# --- Capacitats (vocabulari controlat) ---
EXECUTE_TASKS = "execute_tasks"
DEFINE_TASKS = "define_tasks"
SCHEDULE_FITTINGS = "schedule_fittings"
CLOSE_GATES = "close_gates"
CONFIGURE = "configure"
VIEW_TEAM_TASKS = "view_team_tasks"   # veure les tasques de TOT l'equip (no només les pròpies)
MANAGE_USERS = "manage_users"         # gestió d'usuaris/rols/permisos (matriu)
COMERCIAL = "comercial"               # veure el DINER: preus de venda, costos i imports

#: L'ORDRE ÉS DADA. Aquesta tupla és l'ordre de les COLUMNES de la matriu de permisos
#: (`/configuracio/usuaris`), i va de la capacitat més bàsica a la més àmplia. `ALL_CAPABILITIES`
#: se'n deriva perquè hi hagi UNA sola llista: un `frozenset` no té ordre i no es pot publicar
#: per a una pantalla que en depèn — el client en tenia la còpia, ordenada a mà, i el dia que
#: aquí n'entrés una de nova la matriu no l'hauria ensenyada mai.
CAPABILITIES = (
    EXECUTE_TASKS, DEFINE_TASKS, SCHEDULE_FITTINGS, CLOSE_GATES, CONFIGURE,
    VIEW_TEAM_TASKS, MANAGE_USERS, COMERCIAL,
)
ALL_CAPABILITIES = frozenset(CAPABILITIES)

# --- Rol → capacitats base (config; es clona amb la plantilla del tenant) ---
ROLE_CAPABILITIES = {
    "technician":      frozenset({EXECUTE_TASKS}),
    "product_manager": frozenset({EXECUTE_TASKS, DEFINE_TASKS, SCHEDULE_FITTINGS}),
    # COMERCIAL NO hi és a posta (decisió d'Agus, 2026-08-14): un manager és un cap de
    # producció, no un comercial. Qui l'hagi de tenir la rep INDIVIDUALMENT per la matriu
    # (`permisos.grant`), que és el mecanisme que ja existeix i que `get_capabilities` aplica
    # a sota. Posar-la aquí la regalaria a tots els managers de tots els tenants d'un cop.
    "manager":         frozenset({EXECUTE_TASKS, DEFINE_TASKS, SCHEDULE_FITTINGS,
                                  CLOSE_GATES, VIEW_TEAM_TASKS}),
    "admin":           ALL_CAPABILITIES,   # inclou VIEW_TEAM_TASKS, MANAGE_USERS i COMERCIAL
}

DEFAULT_ROLE = "technician"

#: Els ROLS, en l'ordre en què `ROLE_CAPABILITIES` els declara (de menys a més capacitats), que
#: és l'ordre en què la pantalla els ofereix. Es deriva del mateix diccionari i no es reescriu:
#: els `dict` de Python conserven l'ordre d'inserció des de la 3.7.
ROLES = tuple(ROLE_CAPABILITIES)


def get_capabilities(user) -> set:
    """Capacitat efectiva = base del rol, amb overrides per usuari del JSON.
    permisos = {"grant": [...], "revoke": [...]}. Rol desconegut o sense perfil → set buit."""
    if not user or not getattr(user, "is_authenticated", False):
        return set()
    profile = getattr(user, "profile", None)
    if profile is None:
        return set()
    base = set(ROLE_CAPABILITIES.get(profile.rol_nom, frozenset()))
    overrides = profile.permisos or {}
    grant = set(overrides.get("grant", []))
    revoke = set(overrides.get("revoke", []))
    return (base | grant) - revoke


class HasCapability(BasePermission):
    """Permís DRF. La view declara `required_capability`. Sense declarar → com IsAuthenticated."""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        required = getattr(view, "required_capability", None) or getattr(self, "required_capability", None)
        if required is None:
            return True
        return required in get_capabilities(request.user)


def get_allowed_task_types(user) -> set:
    """Allow-list de TaskType.code que un usuari pot EXECUTAR (Opció A).
    - Admin (té MANAGE_USERS o rol 'admin') → TOTS els codes de TaskType actius (bypass total).
    - Altrament → set(profile.permisos["tasks"]). Sense clau "tasks" → set buit (default DENY)."""
    if not user or not getattr(user, "is_authenticated", False):
        return set()
    profile = getattr(user, "profile", None)
    is_admin = (profile is not None and profile.rol_nom == "admin") or \
        MANAGE_USERS in get_capabilities(user)
    if is_admin:
        from fhort.tasks.models import TaskType   # import local: evita cicle accounts↔tasks
        return set(TaskType.objects.filter(active=True).values_list("code", flat=True))
    if profile is None:
        return set()
    return set((profile.permisos or {}).get("tasks", []))


def pot_veure_diner(request) -> bool:
    """¿Qui fa aquesta petició pot rebre imports? Font única del predicat de la poda.

    Sense request al context, la resposta és NO. És deliberat: un serializer instanciat a mà
    (un PDF, un test, un command) no ha de filtrar diner per omissió d'un paràmetre. Qui
    necessiti els imports fora d'una petició HTTP els demana explícitament amb
    `context={'diner': True}` — vegeu `PodaEconomicaMixin`.
    """
    user = getattr(request, 'user', None) if request is not None else None
    return COMERCIAL in get_capabilities(user)


class PodaEconomicaMixin:
    """Els camps econòmics viatgen NOMÉS a qui té COMERCIAL. La resta ni els rep al payload.

    PER QUÈ UN MIXIN I NO UN GATE PER ENDPOINT
    -------------------------------------------
    Un 403 sec als endpoints comercials trencaria pantalles TÈCNIQUES que hi depenen: la
    pestanya Producció de la fitxa del model demana work-orders i delivery-note-lines per
    `?model=` (`frontend/src/components/model/ProductionTab.jsx:75-76`) per pintar la cadena
    comanda→encàrrec→albarà, i el selector d'assignació demana comandes OPEN
    (`ActionsMenu.jsx:86`). Cap de les dues pinta un import: la primera només fa servir
    `number/kind/status/dn_number` i la segona `document_number/quantity/qty_allocated`.
    O sigui que el que sobra és el PAYLOAD, no la crida — i el que cal és podar, no tallar.

    La diagnosi del 14/08 §3.2 ho va mesurar: aquelles crides retornaven `price_snapshot`,
    `unit_price`, `line_total` i `internal_cost` —el COST INTERN, minuts × tarifa/hora— a
    qualsevol tècnic autenticat, sense que cap pantalla ho pintés mai.

    ÚS
    --
        class ExpenseSerializer(PodaEconomicaMixin, serializers.ModelSerializer):
            CAMPS_ECONOMICS = ('cost_price', 'sale_price')

    Els serializers niats hereten el `context` del pare sols (DRF el propaga), així que una
    línia dins d'una capçalera queda podada igual que si es demanés solta.

    ESCAPATÒRIA EXPLÍCITA: `context={'diner': True}` salta la poda, per a qui hagi de compondre
    imports fora d'una petició HTTP. Avui no la fa servir ningú — els generadors de PDF
    (`commerce/pdf_service.py`) llegeixen del model amb reportlab i no passen per serializer,
    o sigui que el seu gate és el de l'endpoint que els crida. Existeix perquè el dia que
    calgui, la sortida sigui explícita i no un `context` oblidat.
    """

    #: Noms de camp a podar. Cada serializer declara els seus; la mecànica viu aquí.
    CAMPS_ECONOMICS = ()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if self.context.get('diner') is True:
            return data
        if pot_veure_diner(self.context.get('request')):
            return data
        for camp in self.CAMPS_ECONOMICS:
            data.pop(camp, None)
        return data


def scope_model_task_queryset(qs, user):
    """Scope de visibilitat/edició de ModelTask segons capacitats (font única).

    Tres branques:
      - view_team_tasks (manager/admin) → tot el queryset (sense filtre).
      - sense view_team_tasks PERÒ define_tasks (product_manager) → les pròpies + les NO
        assignades (assignee IS NULL), perquè qui defineix tasques pugui veure i assignar les
        "pendents d'assignar" SENSE accedir a les tasques ja assignades d'altri.
      - cap de les dues (technician) → només les pròpies. Sense perfil → res.

    NOMÉS per a querysets de ModelTask. La semàntica de FittingSession ("on ets assistent")
    és diferent i no fa servir aquest helper.
    """
    caps = get_capabilities(user)
    if VIEW_TEAM_TASKS in caps:
        return qs
    profile = getattr(user, "profile", None)
    if profile is None:
        return qs.none()
    if DEFINE_TASKS in caps:
        return qs.filter(Q(assignee=profile) | Q(assignee__isnull=True))
    return qs.filter(assignee=profile)
