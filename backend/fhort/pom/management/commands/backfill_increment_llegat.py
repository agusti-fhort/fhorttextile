"""FIX-A/PAS-2 · BACKFILL DEL CAMP LLEGAT `increment` (mètode S44).

    increment := increment_base     — per a les LINEAR ACTIVES on divergeixen

── QUÈ ARREGLA, I PER QUÈ NO ÉS COSMÈTIC ────────────────────────────────────────────────
El motor gradua per `increment_base` i **cau a `increment` quan `increment_base` és NULL**
(`pom/services.py`, `_apply_rule` · `pom/grading_utils.py`, `increment_de_l_aresta`). Mentre
els dos camps diguin coses diferents, aquella caiguda és una **segona veritat oculta**: n'hi ha
prou de buidar el camp «Δ base» a la pantalla de Graduació —que passa la validació si la regla
té break— perquè el motor gradui, en silenci i amb 200 OK, **amb el delta del joc antic**.

Aquest command és el pas previ a retirar el fallback (PAS 3). Iguala els dos camps perquè, si
qualsevol camí no censat encara hi cau, hi caigui sobre el valor BO. Després del PAS 3 el camp
ja no el llegeix ningú i això queda com el que és: higiene d'un camp mort.

── LA GUARDA ÉS EL PUNT DE TOT (S44) ────────────────────────────────────────────────────
Es diu ABANS quantes files s'esperen i, si no quadra, **s'atura sense escriure**. Una xifra
mesurada el 21/08 al matí:

    staging  fhort → 14   (totes del model 1383, totes origen=MANUAL)
    staging  los   → 0    (no hi ha cap ModelGradingRule en aquest schema)
    PROD     fhort → 137  ← cens PROPI allà; la xifra pot haver crescut. Es passa amb
                            `--esperades`, mai es dedueix.

── QUÈ NO TOCA ──────────────────────────────────────────────────────────────────────────
· Regles **no LINEAR**. Les 39 FIXED del 1383 tenen `increment=0.00` i `increment_base=NULL`:
  en SQL cru `increment IS DISTINCT FROM increment_base` també les compta (53 en comptes de 14),
  però `_apply_rule` no els agafa mai la branca canònica —cauen a `FIXED → return base_val`— i
  el llegat no s'hi llegeix. Igualar-los-hi seria inventar-los una forma canònica que no tenen.
· Regles **inactives**. El motor filtra `actiu=True`; una inactiva no gradua res.
· Regles amb **`increment_base` NULL**. Aquí el llegat encara ÉS la veritat: copiar-hi res al
  revés seria decidir-ne una, i qui les ha de resoldre és el PAS 3 (cel·la absent + error clar).
  Se n'informa el recompte, no es toquen.

    venv/bin/python manage.py backfill_increment_llegat                        # dry-run, fhort
    venv/bin/python manage.py backfill_increment_llegat --schema los
    venv/bin/python manage.py backfill_increment_llegat --tots                 # tots els tenants
    venv/bin/python manage.py backfill_increment_llegat --esperades 14 --apply
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django_tenants.utils import schema_context


class Command(BaseCommand):
    help = ("Iguala el camp llegat `increment` a `increment_base` a les regles LINEAR actives "
            "on divergeixen. Dry-run per defecte.")

    def add_arguments(self, p):
        p.add_argument('--schema', default='fhort',
                       help="Schema del tenant (per defecte `fhort`).")
        p.add_argument('--tots', action='store_true',
                       help="Audita TOTS els tenants. Amb --apply, escriu a tots.")
        p.add_argument('--apply', action='store_true',
                       help="Escriu. Sense això només mesura i llista.")
        p.add_argument('--esperades', type=int, default=None,
                       help="Guarda S44: nombre de files que s'espera moure EN TOTAL. Si no "
                            "quadra, s'atura sense escriure.")
        p.add_argument('--limit-llista', type=int, default=60,
                       help="Files a llistar per schema (per defecte 60).")

    # ── mesura ────────────────────────────────────────────────────────────────
    def _cens(self, schema):
        """Retorna (a_moure, informatius) per a un schema. Cap escriptura."""
        from fhort.models_app.models import ModelGradingRule
        from fhort.pom.models import GradingRule

        out = {'residents': [], 'cataleg': [], 'ib_null': 0, 'no_linear': 0}
        with schema_context(schema):
            for etiqueta, qs, dest in (
                ('residents',
                 ModelGradingRule.objects.select_related('pom', 'model'), out['residents']),
                ('cataleg',
                 GradingRule.objects.select_related('pom', 'rule_set'), out['cataleg']),
            ):
                for r in qs.filter(logica='LINEAR', actiu=True):
                    if r.increment_base is None:
                        out['ib_null'] += 1
                        continue
                    if r.increment != r.increment_base:
                        dest.append(r)
                out['no_linear'] += qs.model.objects.exclude(logica='LINEAR').count()
        return out

    def _diu_schema(self, schema, cens, limit):
        res, cat = cens['residents'], cens['cataleg']
        self.stdout.write(self.style.MIGRATE_HEADING(f"\n── schema `{schema}` ──"))
        self.stdout.write(f"  ModelGradingRule LINEAR actives a moure : {len(res)}")
        self.stdout.write(f"  GradingRule      LINEAR actives a moure : {len(cat)}")
        self.stdout.write(f"  (informatiu) LINEAR actives amb increment_base NULL: "
                          f"{cens['ib_null']}  → NO es toquen, les resol el PAS 3")
        for r in res[:limit]:
            self.stdout.write(
                f"    MGR#{r.pk:<6} model {r.model.codi_intern:<18} POM {r.pom.codi_client:<8} "
                f"origen={r.origen:<10} {r.increment} → {r.increment_base}")
        if len(res) > limit:
            self.stdout.write(f"    … i {len(res) - limit} més")
        for r in cat[:limit]:
            self.stdout.write(
                f"    GR#{r.pk:<7} joc   {r.rule_set.codi_sistema:<18} POM {r.pom.codi_client:<8} "
                f"{r.increment} → {r.increment_base}")
        if len(cat) > limit:
            self.stdout.write(f"    … i {len(cat) - limit} més")

    # ── escriptura ────────────────────────────────────────────────────────────
    def _aplica(self, schema, cens):
        """`update_fields=['increment']` i prou: aquest command NO toca la llei, només el
        mirall. Un `save()` sencer aquí podria arrossegar qualsevol camp que un altre camí
        hagués deixat brut a la instància en memòria."""
        n = 0
        with schema_context(schema), transaction.atomic():
            for r in cens['residents'] + cens['cataleg']:
                r.increment = r.increment_base
                r.save(update_fields=['increment'])
                n += 1
        return n

    def handle(self, *a, **o):
        from fhort.tenants.models import Client

        if o['tots']:
            schemes = list(Client.objects.exclude(schema_name='public')
                           .order_by('schema_name').values_list('schema_name', flat=True))
        else:
            schemes = [o['schema']]

        self.stdout.write(self.style.MIGRATE_HEADING(
            "BACKFILL `increment` := `increment_base`  (LINEAR actives, increment_base NO NULL)"))
        self.stdout.write(f"  schemes: {', '.join(schemes)}   ·   "
                          f"mode: {'APPLY' if o['apply'] else 'DRY-RUN'}")

        censos, total = {}, 0
        for s in schemes:
            censos[s] = self._cens(s)
            self._diu_schema(s, censos[s], o['limit_llista'])
            total += len(censos[s]['residents']) + len(censos[s]['cataleg'])

        self.stdout.write(self.style.MIGRATE_HEADING(f"\nTOTAL A MOURE: {total}"))

        # ── la guarda S44 ─────────────────────────────────────────────────────
        if o['esperades'] is not None and o['esperades'] != total:
            raise CommandError(
                f"ATURADA · guarda S44: s'esperaven {o['esperades']} files i n'hi ha {total}. "
                "El corpus no és el que el cens deia. Torna a mesurar abans d'escriure.")

        if not o['apply']:
            self.stdout.write(self.style.WARNING(
                "\nDRY-RUN. Res desat. Per escriure: --esperades <N> --apply"))
            return

        if o['esperades'] is None:
            raise CommandError(
                "ATURADA · `--apply` exigeix `--esperades <N>`. Escriure sense guarda és "
                "exactament el que el mètode S44 no permet.")

        mogudes = 0
        for s in schemes:
            n = self._aplica(s, censos[s])
            mogudes += n
            self.stdout.write(f"  `{s}`: {n} files desades")

        self.stdout.write(self.style.SUCCESS(f"\n✅ {mogudes} files. `increment` ja no divergeix."))

        # Re-mesura: idempotència demostrada, no promesa.
        resta = sum(len(self._cens(s)['residents']) + len(self._cens(s)['cataleg'])
                    for s in schemes)
        if resta:
            raise CommandError(f"⚠️ després d'escriure encara en queden {resta}. Revisa-ho.")
        self.stdout.write(self.style.SUCCESS("   Re-mesurat: 0 divergents. Idempotent."))
