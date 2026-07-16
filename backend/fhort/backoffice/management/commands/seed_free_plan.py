"""
Management command: seed_free_plan
F3 P-FREE-SEED — sembra la fila `Plan` del tier Free (decisió Agus, coordinat amb F1).

    manage.py seed_free_plan

REPARTIMENT DE TERRITORI (F1 ↔ F3):
- F1 és propietari de `tenants/models.py`: hi afegeix `NOM_FREE='Free'` a
  `Plan.NOM_CHOICES` (migració `tenants/0005_alter_plan_nom`, ja aplicada).
- F3 (aquí) sembra la FILA `Plan` Free. F1 NO la sembra. Aquesta comanda no toca
  `tenants/models.py`: només escriu dades via l'ORM.

El Free NO viu a Stripe (no hi ha res a cobrar): preu 0 i `stripe_lookup_*` = NULL
(l'endpoint de pricing ja el retorna hardcoded, `pricing_service.FREE_TIER`).

IDEMPOTENT i NO destructiu: `get_or_create` per `nom`. Si la fila ja existeix, NO
sobreescriu els seus valors (poden estar afinats des del backoffice). Re-executable.

⚠️ FLAG CTO — QUOTES DEL FREE: `REGLES_FREE_TIERS_GMJ_TMA.md §4` (font canònica de
les quotes) NO és a staging. Els límits de sota (max_models=1, max_usuaris=1,
storage_gb=1, ia_credits_mes=0) són conservadors PER DEFECTE. Confirma'ls o ajusta'ls
(editant la fila al backoffice, o esborrant-la i re-sembrant amb els valors bons).
"""
from django.core.management.base import BaseCommand

from fhort.tenants.models import Plan

# Quotes Free per defecte (⚠️ FLAG CTO, veure capçalera). Conservadores.
FREE_DEFAULTS = dict(
    tipologia=Plan.TIPOLOGIA_ESTUDI,
    preu_mensual=0,
    max_models_actius=1,
    max_usuaris=1,
    storage_gb=1,
    ia_credits_mes=0,
    models_inclosos=0,
    preu_model_extra=0,
    moneda_pla='EUR',
    feature_flags={},
    actiu=True,
    stripe_lookup_platform=None,  # el Free no viu a Stripe
    stripe_lookup_model=None,
)


class Command(BaseCommand):
    help = "Sembra (idempotent) la fila Plan del tier Free (preu 0, sense Stripe)."

    def handle(self, *args, **options):
        plan, created = Plan.objects.get_or_create(
            nom=Plan.NOM_FREE, defaults=FREE_DEFAULTS)
        if created:
            self.stdout.write(self.style.SUCCESS(
                f"Plan '{Plan.NOM_FREE}' sembrat (id={plan.id}, preu={plan.preu_mensual}). "
                f"⚠️ Revisa les quotes contra REGLES_FREE_TIERS §4."))
        else:
            self.stdout.write(
                f"Plan '{Plan.NOM_FREE}' ja existeix (id={plan.id}, preu={plan.preu_mensual}). "
                f"Res a fer (no es sobreescriu).")
