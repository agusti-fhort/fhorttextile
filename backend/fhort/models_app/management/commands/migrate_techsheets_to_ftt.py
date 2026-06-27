"""Migra cada TechSheet (O2O) amb contingut v2 real al sistema .ftt (ModelFitxer TECHSHEET v1).

    python manage.py migrate_techsheets_to_ftt --schema fhort           # dry-run (per defecte)
    python manage.py migrate_techsheets_to_ftt --schema fhort --apply   # aplica

- Idempotent: salta els models que JA tenen un ModelFitxer tipus TECHSHEET (no duplica).
- Només migra TechSheets amb template_json v2 (clau 'pages'); ignora les buides.
- document.json es construeix amb services_ftt.v2_to_document, extraient binaris inline
  (image.src dataURL) a assets/<hash>.<ext>.
- metadata: reference=codi_intern, description=descripcio, season=temporada.
- ADDITIU: NO toca el TechSheet origen. El front segueix usant el TechSheet fins a la
  Fase 2 (que farà el cutover de l'editor i la retirada del model). Pensat per re-executar
  al cutover (idempotent).
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django_tenants.utils import schema_context

from fhort.models_app import services_ftt, services_ftt_document as svc
from fhort.models_app.models import ModelFitxer
from fhort.models_app.tech_sheet_models import TechSheet


def _metadata_for(model):
    return {
        "reference": model.codi_intern,
        "description": getattr(model, "descripcio", "") or "",
        "season": getattr(model, "temporada", "") or "",
    }


class Command(BaseCommand):
    help = "Migra els TechSheet amb contingut v2 a documents .ftt (ModelFitxer TECHSHEET v1)."

    def add_arguments(self, parser):
        parser.add_argument("--schema", required=True, help="Schema del tenant (p.ex. fhort).")
        parser.add_argument("--apply", action="store_true", help="Aplica (per defecte dry-run).")

    def handle(self, *args, **opts):
        schema = opts["schema"]
        apply = opts["apply"]
        mode = "APPLY" if apply else "DRY-RUN"
        self.stdout.write(self.style.NOTICE("[%s] schema=%s" % (mode, schema)))

        with schema_context(schema):
            sheets = TechSheet.objects.select_related("model").all()
            migrated = skipped_empty = skipped_exists = 0
            for sheet in sheets:
                tj = sheet.template_json or {}
                if not (tj.get("version") == 2 and isinstance(tj.get("pages"), list) and tj.get("pages")):
                    skipped_empty += 1
                    continue
                model = sheet.model
                if model.fitxers.filter(tipus=ModelFitxer.TIPUS_TECHSHEET).exists():
                    skipped_exists += 1
                    self.stdout.write("  · model %s (%s): ja té .ftt → salta" % (model.id, model.codi_intern))
                    continue

                document_json, assets = services_ftt.v2_to_document(tj, metadata=_metadata_for(model))
                n_obj = sum(len(p.get("objects") or []) for p in document_json["pages"])
                self.stdout.write(
                    "  → model %s (%s): %d pàg / %d objectes / %d assets"
                    % (model.id, model.codi_intern, len(document_json["pages"]), n_obj, len(assets))
                )
                if apply:
                    with transaction.atomic():
                        fitxer = svc.create_document(model, document_json=document_json, assets=assets)
                    # Auditoria immediata: round-trip sense pèrdua d'objectes.
                    out = svc.load_document(fitxer)
                    n_back = sum(len(p.get("objects") or []) for p in out["document_json"]["pages"])
                    if n_back != n_obj:
                        raise CommandError("Pèrdua d'objectes al model %s: %d→%d" % (model.id, n_obj, n_back))
                    self.stdout.write(self.style.SUCCESS(
                        "    ✓ .ftt id=%s v%s is_current=%s (round-trip %d objectes OK)"
                        % (fitxer.id, fitxer.versio, fitxer.is_current, n_back)
                    ))
                migrated += 1

            self.stdout.write(self.style.SUCCESS(
                "[%s] candidats=%d  migrats=%d  buits(saltats)=%d  ja_existents(saltats)=%d"
                % (mode, migrated, migrated if apply else 0, skipped_empty, skipped_exists)
            ))
            if not apply:
                self.stdout.write(self.style.WARNING("Dry-run: res escrit. Re-executa amb --apply."))
