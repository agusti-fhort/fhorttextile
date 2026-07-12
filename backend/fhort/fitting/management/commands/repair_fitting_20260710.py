"""Reparació puntual de les dades incoherents del model 185, sprint fonaments-de-gravat (XE).

Font: docs/diagnosis/DIAGNOSI_DISSOLUCIO_FITTINGDETAIL_2026-07-10.md (Bloc X).
Causa (ja corregida per XA): close_piece_fitting no era atòmic; el guard D-1 (GradingVersion
aprovada) llançava ValueError DESPRÉS que la consolidació a BaseMeasurement i el Welford
haguessin commitat. Resultat viu a staging després de 5 reintents fallits (sessió 139, PF 19):

  1. Divergència base↔grading: BaseMeasurement pom 273=60.7 / 275=60.2 (origen FITTED),
     però el GradedSpec actiu de la talla base 'L' encara deia 60.5 / 60.0, i
     model.measurements_version es va quedar enrere.
  2. Welford contaminat: ClientMesuraPerfil (garment_type=63, talla 'L', poms 273/275) amb
     n_mostres=5 per una sola presa real (5 reintents), desviacio=0.0.

Aquest command repara les dues coses, EN AQUEST ORDRE (la reparació 1 usa el camí ja
protegit per XA/XB i torna a alimentar el Welford, per això la 2 va després):

  XE.1  Re-executa el close legítim de PF 19 amb allow_reopen_sealed=True → GradingVersion
        v+1 que supera la v5 aprovada, base i grading convergents, measurements_version++.
        Segella la sessió 139 (comportament normal del gravat).
  XE.2  Força n_mostres=1 als perfils Welford afectats (mitjana=valor, m2=0, desviacio=0).
        Correcció exacta i trivial perquè les 5 mostres són idèntiques. MAI toca
        MeasurementChangeLog.

One-shot documentat (no shell efímer). Idempotent i segur: dry-run per defecte; --apply per
executar; si ja està reparat, no fa res. NO toca el model 182 (també segellat, però sense
divergència activa coneguda) — vegeu ESTAT_PROJECTE.

    python manage.py repair_fitting_20260710 --schema fhort              # dry-run
    python manage.py repair_fitting_20260710 --schema fhort --apply
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django_tenants.utils import schema_context

PF_ID = 19
SESSION_ID = 139
MODEL_ID = 185
GARMENT_TYPE_ID = 63
SIZE_LABEL = 'L'
POM_IDS = [273, 275]


def _differ(a, b):
    if a is None or b is None:
        return a is not b
    return abs(float(a) - float(b)) > 1e-6


class Command(BaseCommand):
    help = "Repara la divergència base↔grading i el Welford del model 185 (sprint XE, diagnosi 2026-07-10)."

    def add_arguments(self, parser):
        parser.add_argument('--schema', required=True, help='Schema del tenant (ex: fhort)')
        parser.add_argument('--apply', action='store_true',
                            help='Aplica els canvis. Sense aquest flag, només informa (dry-run).')

    def handle(self, *args, **o):
        with schema_context(o['schema']):
            self._run(o['apply'])

    def _run(self, apply):
        from fhort.fitting.models import PieceFitting, GradedSpec
        from fhort.models_app.models import BaseMeasurement, Model
        from fhort.pom.models import ClientMesuraPerfil
        from fhort.fitting.services import close_piece_fitting

        model = Model.objects.filter(pk=MODEL_ID).first()
        if not model:
            raise CommandError(f"Model {MODEL_ID} no existeix.")
        pf = PieceFitting.objects.filter(pk=PF_ID, session_id=SESSION_ID, model_id=MODEL_ID).first()
        if not pf:
            raise CommandError(f"PieceFitting {PF_ID} (sessió {SESSION_ID}, model {MODEL_ID}) no existeix.")

        def base_vs_graded():
            """Retorna {pom: (base, graded_actiu)} de la talla base per als POMs afectats."""
            out = {}
            for pid in POM_IDS:
                bm = BaseMeasurement.objects.filter(model_id=MODEL_ID, pom_id=pid).first()
                gs = (GradedSpec.objects
                      .filter(grading_version__size_fitting__model_id=MODEL_ID,
                              grading_version__is_active=True,
                              pom_id=pid, size_label=SIZE_LABEL)
                      .first())
                out[pid] = (bm.base_value_cm if bm else None,
                            gs.graded_value_cm if gs else None)
            return out

        self.stdout.write(f"Mode: {'APPLY' if apply else 'DRY-RUN'} · schema OK")
        self.stdout.write(f"model {MODEL_ID} measurements_version={model.measurements_version}")

        # ── XE.1 — reobertura + close legítim ────────────────────────────────
        pre = base_vs_graded()
        diverge = any(_differ(b, g) for b, g in pre.values())
        self.stdout.write("\n[XE.1] base ↔ grading actiu (abans):")
        for pid, (b, g) in pre.items():
            flag = '  ⚠ DIVERGEIX' if _differ(b, g) else '  ok'
            self.stdout.write(f"   pom {pid}: base={b}  graded={g}{flag}")

        if not diverge:
            self.stdout.write("   → ja convergent; XE.1 no fa res (idempotent).")
        elif not apply:
            self.stdout.write("   → DRY-RUN: cridaria close_piece_fitting(19, allow_reopen_sealed=True) "
                              "→ GradingVersion v+1, convergència, measurements_version++, sessió Tancada.")
        else:
            with transaction.atomic():
                result = close_piece_fitting(
                    PF_ID, user_profile_id=pf.session.responsable_id,
                    allow_reopen_sealed=True,
                )
            self.stdout.write(f"   → close aplicat: {result}")
            model.refresh_from_db()
            post = base_vs_graded()
            self.stdout.write("   base ↔ grading actiu (després):")
            for pid, (b, g) in post.items():
                flag = '  ⚠ ENCARA DIVERGEIX' if _differ(b, g) else '  ✓ convergent'
                self.stdout.write(f"   pom {pid}: base={b}  graded={g}{flag}")
            self.stdout.write(f"   measurements_version={model.measurements_version} · "
                              f"sessió {SESSION_ID} estat={pf.session.__class__.objects.get(pk=SESSION_ID).estat}")

        # ── XE.2 — correcció del Welford ─────────────────────────────────────
        # (després de XE.1, que torna a alimentar el Welford: n passa a 6). Es força a 1.
        self.stdout.write("\n[XE.2] Welford ClientMesuraPerfil (garment_type=63, talla 'L'):")
        perfils = list(ClientMesuraPerfil.objects.filter(
            garment_type_id=GARMENT_TYPE_ID, talla=SIZE_LABEL, pom_id__in=POM_IDS))
        for p in perfils:
            needs = (p.n_mostres or 0) != 1 or _differ(p.m2_acum, 0.0) or _differ(p.desviacio, 0.0)
            self.stdout.write(f"   pom {p.pom_id}: n_mostres={p.n_mostres} mitjana={p.mitjana} "
                              f"m2={p.m2_acum} desv={p.desviacio}"
                              f"{'  ⚠ a corregir' if needs else '  ok'}")
            if needs and apply:
                # Les 5 mostres són idèntiques (desviacio=0.0) → n=1, mean=valor, m2=0, desv=0.
                # La mitjana ja és el valor real; només s'esmena el recompte. MAI MeasurementChangeLog.
                p.n_mostres = 1
                p.m2_acum = 0.0
                p.desviacio = 0.0
                p.save(update_fields=['n_mostres', 'm2_acum', 'desviacio'])
                self.stdout.write(f"      → corregit: n_mostres=1 m2=0 desv=0 (mitjana={p.mitjana} intacta)")
        if not apply:
            self.stdout.write("   → DRY-RUN: forçaria n_mostres=1, m2=0, desv=0 als perfils marcats.")

        # ── XE.3 — model 182: només anotació ─────────────────────────────────
        self.stdout.write("\n[XE.3] Model 182 (QA-SC): també té la GradingVersion activa aprovada, però "
                          "SENSE divergència activa coneguda. NO es repara aquí. Necessitarà reobertura "
                          "explícita (allow_reopen_sealed) si mai es torna a gravar. Anotat a ESTAT_PROJECTE.")
        self.stdout.write(self.style.SUCCESS("\nFet." if apply else "\nDry-run complet (cap canvi)."))
