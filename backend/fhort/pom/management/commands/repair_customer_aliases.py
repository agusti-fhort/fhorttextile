"""Reparació dels àlies de nomenclatura contaminats (QA-S8 · D4a).

IDEMPOTENT · --dry-run PER DEFECTE (cal --apply explícit per escriure).

Repara DUES famílies de defecte, censades a docs/diagnosis/DIAGNOSI_QA_S8_D3_D4.md:

  FAMÍLIA 1 · PROSA AL CAMP CODI (migració 0031). 5 àlies del client BRW on el `client_code`
    és una DESCRIPCIÓ ('collar width', 'lining bottom width along hem'...). La 0031 va sembrar
    des d'un dict les claus del qual eren descripcions (0031:53-56: client_code=src,
    client_description=src), i la 0035 es va saltar el backfill de description_en precisament
    perquè codi i descripció eren iguals (0035:22-23) -> es veuen amb la descripció BUIDA.
    ACCIÓ: description_en := client_code · pendent_revisio := True.
    NO es toca el `client_code` (no pot quedar buit: NOT NULL + unique(customer, client_code),
    i 5 buits del mateix client col·lisionarien) ni el `pom` (els 5 destins són CORRECTES).
    El match per descripció es preserva: un client_code descriptiu és intencional i el matcher
    el prova contra la descripció del document (extraction_views.py:527-529, :545).

  FAMÍLIA 2 · POM EQUIVOCAT (wizard del diccionari). Àlies amb el codi BO apuntant a un POM
    que el mateix client ja reclama amb un ALTRE codi, essent mesures DISTINTES: 4 codis
    (F/FF/F3/F4 = front/back/center front/center back) sobre el POM 389 'TOTAL LENGTH',
    3 (U/U2/U3 = front overlap/1st button/last button) sobre el 439, etc.
    ACCIÓ segons --unlink: 'flag' (pendent_revisio=True, conserva el vincle) o 'delete'.

  BROSSA · client_code='0' (no és un codi). SEMPRE s'esborra.

⚠️ 'flag' NO impedeix que l'àlies segueixi auto-vinculant: find_pom_master (extraction_views.py
:545-550) torna alias_match/HIGH sense mirar `pendent_revisio`. Avui l'única acció que treu el
vincle fals de debò és 'delete'. Vegeu el BLOCADOR de la diagnosi.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django_tenants.utils import schema_context

from fhort.pom.models import CustomerPOMAlias


# Vincles DOLENTS, curats un per un contra el catàleg viu (§D4a·5 de la diagnosi).
# (codi_client_del_customer, client_code, pom_id, motiu)
VINCLES_DOLENTS = [
    ('BRW', 'F',  389, 'FRONT TOTAL LENGTH sobre un POM genèric TOTAL LENGTH (4 codis hi cauen)'),
    ('BRW', 'FF', 389, 'BACK TOTAL LENGTH — mesura distinta de F'),
    ('BRW', 'F3', 389, 'FRONT CENTER TOTAL LENGTH — mesura distinta'),
    ('BRW', 'F4', 389, 'BACK CENTER TOTAL LENGTH — mesura distinta'),
    ('BRW', 'U',  439, 'FRONT OVERLAP sobre POM "Width sequins piece" — no hi correspon'),
    ('BRW', 'U2', 439, '1st BUTTON — mesura distinta (la que D2 va veure col·lapsar amb U3)'),
    ('BRW', 'U3', 439, 'LAST BUTTON — mesura distinta'),
    ('BRW', 'P',  441, 'CENTER BACK YOKE HEIGHT sobre POM "Chest piece height at side seam"'),
    ('BRW', 'P2', 441, 'CENTER FRONT YOKE HEIGHT — mesura distinta de P'),
    ('BRW', 'F1', 437, 'TOTAL SIDE LENGTH sobre POM "Centre front length at CF"'),
    ('BRW', 'F2', 437, 'TOTAL SIDE LENGTH — descripció idèntica a F1, i el POM no hi correspon'),
    ('BRW', 'B1', 275, 'STRETCHED WAIST WIDTH sobre el POM de waist width (B, que SÍ és correcte)'),
]

# Brossa: no és un codi de client.
BROSSA = [('BRW', '0', 'client_code="0" — artefacte, no és cap codi')]


class Command(BaseCommand):
    help = 'Repara els àlies de nomenclatura contaminats (QA-S8 · D4a). --dry-run per defecte.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply', action='store_true',
            help='Escriu de veritat. Sense això NOMÉS ensenya què faria (dry-run).')
        parser.add_argument(
            '--unlink', choices=['flag', 'delete'], default='flag',
            help="Família 2 (POM equivocat): 'flag' marca pendent_revisio i conserva el vincle; "
                 "'delete' esborra l'àlies. Només 'delete' treu el vincle fals del matcher.")
        parser.add_argument(
            '--tenant', default='fhort',
            help='Schema del tenant on viuen els àlies (per defecte: fhort).')

    def handle(self, *args, **opts):
        with schema_context(opts['tenant']):
            self._run(opts)

    def _run(self, opts):
        apply_ = opts['apply']
        unlink = opts['unlink']
        mode = 'APPLY (escriptura)' if apply_ else 'DRY-RUN (cap escriptura)'
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"repair_customer_aliases · tenant={opts['tenant']} · {mode} · família 2 = {unlink}"))

        with transaction.atomic():
            n1 = self._familia1(apply_)
            n2 = self._familia2(apply_, unlink)
            n3 = self._brossa(apply_)

            self.stdout.write('')
            self.stdout.write(self.style.MIGRATE_HEADING('RESUM'))
            self.stdout.write(f'  família 1 (prosa al codi → description_en) : {n1}')
            self.stdout.write(f'  família 2 (POM equivocat → {unlink:6})        : {n2}')
            self.stdout.write(f'  brossa    (esborrats)                      : {n3}')
            total = n1 + n2 + n3
            if not apply_:
                self.stdout.write('')
                self.stdout.write(self.style.WARNING(
                    f'DRY-RUN: {total} àlies afectats. CAP escriptura. Torna-hi amb --apply.'))
                transaction.set_rollback(True)
            else:
                self.stdout.write('')
                self.stdout.write(self.style.SUCCESS(f'APLICAT: {total} àlies reparats.'))

    # ── FAMÍLIA 1 ────────────────────────────────────────────────────────────────
    def _familia1(self, apply_):
        """Prosa al camp codi: el text passa a description_en i es marca per revisar.
        Predicat idempotent: description_en buit (un cop omplert, ja no torna a entrar)."""
        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_LABEL(
            'FAMÍLIA 1 — prosa al camp codi (migració 0031)'))
        qs = (CustomerPOMAlias.objects
              .filter(origen='MIGRACIO', description_en='')
              .select_related('customer', 'pom'))
        n = 0
        for a in qs:
            code = (a.client_code or '').strip()
            desc = (a.client_description or '').strip()
            # Contaminat ⇔ el codi ÉS la descripció i és prosa (té espais).
            if not code or code.lower() != desc.lower() or ' ' not in code:
                continue
            self.stdout.write(
                f'  [{a.customer.codi}] id={a.id}  description_en: ∅ → "{code}"  '
                f'· pendent_revisio: {a.pendent_revisio} → True  '
                f'(codi i pom {a.pom.codi_client} intactes)')
            if apply_:
                a.description_en = code[:200]
                a.pendent_revisio = True
                a.save(update_fields=['description_en', 'pendent_revisio', 'actualitzat_at'])
            n += 1
        if n == 0:
            self.stdout.write('  (res a fer — ja reparat)')
        return n

    # ── FAMÍLIA 2 ────────────────────────────────────────────────────────────────
    def _familia2(self, apply_, unlink):
        """Vincles curats. Idempotent: només actua si l'àlies ENCARA apunta al POM dolent."""
        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_LABEL(
            f'FAMÍLIA 2 — POM equivocat (wizard del diccionari) · acció={unlink}'))
        n = 0
        for cust_codi, code, pom_id, motiu in VINCLES_DOLENTS:
            a = (CustomerPOMAlias.objects
                 .filter(customer__codi=cust_codi, client_code__iexact=code, pom_id=pom_id)
                 .select_related('customer', 'pom').first())
            if a is None:
                continue  # ja reparat, o el vincle ja no existeix
            if unlink == 'flag':
                if a.pendent_revisio:
                    continue  # ja marcat
                self.stdout.write(f'  [{cust_codi}] id={a.id} {code:4} → POM {pom_id} '
                                  f'· pendent_revisio → True · {motiu}')
                if apply_:
                    a.pendent_revisio = True
                    a.save(update_fields=['pendent_revisio', 'actualitzat_at'])
            else:
                self.stdout.write(f'  [{cust_codi}] id={a.id} {code:4} → POM {pom_id} '
                                  f'· ESBORRAT · {motiu}')
                if apply_:
                    a.delete()
            n += 1
        if n == 0:
            self.stdout.write('  (res a fer — ja reparat)')
        return n

    # ── BROSSA ───────────────────────────────────────────────────────────────────
    def _brossa(self, apply_):
        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_LABEL('BROSSA — client_code que no és un codi'))
        n = 0
        for cust_codi, code, motiu in BROSSA:
            a = (CustomerPOMAlias.objects
                 .filter(customer__codi=cust_codi, client_code=code)
                 .select_related('customer').first())
            if a is None:
                continue
            self.stdout.write(f'  [{cust_codi}] id={a.id} client_code="{code}" · ESBORRAT · {motiu}')
            if apply_:
                a.delete()
            n += 1
        if n == 0:
            self.stdout.write('  (res a fer — ja reparat)')
        return n
