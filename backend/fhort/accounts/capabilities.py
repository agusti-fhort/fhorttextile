"""Capacitats i resolució de permisos (Sprint A). Font de veritat única."""
from rest_framework.permissions import BasePermission

# --- Capacitats (vocabulari controlat) ---
EXECUTE_TASKS = "execute_tasks"
DEFINE_TASKS = "define_tasks"
SCHEDULE_FITTINGS = "schedule_fittings"
CLOSE_GATES = "close_gates"
CONFIGURE = "configure"

ALL_CAPABILITIES = frozenset({
    EXECUTE_TASKS, DEFINE_TASKS, SCHEDULE_FITTINGS, CLOSE_GATES, CONFIGURE,
})

# --- Rol → capacitats base (config; es clona amb la plantilla del tenant) ---
ROLE_CAPABILITIES = {
    "technician":      frozenset({EXECUTE_TASKS}),
    "product_manager": frozenset({EXECUTE_TASKS, DEFINE_TASKS, SCHEDULE_FITTINGS}),
    "manager":         frozenset({EXECUTE_TASKS, DEFINE_TASKS, SCHEDULE_FITTINGS, CLOSE_GATES}),
    "admin":           ALL_CAPABILITIES,
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
        required = getattr(view, "required_capability", None)
        if required is None:
            return True
        return required in get_capabilities(request.user)
