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

ALL_CAPABILITIES = frozenset({
    EXECUTE_TASKS, DEFINE_TASKS, SCHEDULE_FITTINGS, CLOSE_GATES, CONFIGURE,
    VIEW_TEAM_TASKS, MANAGE_USERS,
})

# --- Rol → capacitats base (config; es clona amb la plantilla del tenant) ---
ROLE_CAPABILITIES = {
    "technician":      frozenset({EXECUTE_TASKS}),
    "product_manager": frozenset({EXECUTE_TASKS, DEFINE_TASKS, SCHEDULE_FITTINGS}),
    "manager":         frozenset({EXECUTE_TASKS, DEFINE_TASKS, SCHEDULE_FITTINGS,
                                  CLOSE_GATES, VIEW_TEAM_TASKS}),
    "admin":           ALL_CAPABILITIES,   # inclou VIEW_TEAM_TASKS i MANAGE_USERS
}

DEFAULT_ROLE = "technician"


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
