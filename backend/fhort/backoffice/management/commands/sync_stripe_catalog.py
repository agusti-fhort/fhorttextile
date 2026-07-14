"""
Management command: sync_stripe_catalog — F1 (P-PRICE).

STRIPE ÉS LA FONT DE VERITAT DEL PREU. El YAML (pricing_catalog.yaml) és la definició
del catàleg DESITJAT, no el preu vigent. Aquesta comanda l'empeny cap a Stripe de
manera IDEMPOTENT i sense destruir mai res:

  · Product: identitat determinista `fhort_{tier}_{concepte}` (id propi a Stripe) →
    retrieve fort (no search, que és eventual). Si no existeix, es crea amb metadata.
  · Price:  es busca per lookup_key (Price.list). Els Prices són immutables en
    unit_amount/currency/interval, per això:
      - cap price amb el lookup_key            → CREATED  (crea Price nou)
      - price amb el MATEIX amount+currency+interval → UNCHANGED (res)
      - price amb valors diferents             → ROTATED  (crea Price nou amb
        transfer_lookup_key=True i ARXIVA l'antic amb active=False)
  MAI s'esborra res a Stripe (arxivar ≠ esborrar). La BD FHORT no es toca.

Ús:
  manage.py sync_stripe_catalog            # --dry-run real: mostra el pla, no toca Stripe
  manage.py sync_stripe_catalog --apply    # executa
"""
import logging

from django.core.management.base import BaseCommand, CommandError

from fhort.backoffice.pricing_service import (
    CatalogError,
    PricingUnavailable,
    configure_stripe,
    load_catalog,
    sget,
)

logger = logging.getLogger('fhort.backoffice.pricing')

OK_CREATED = 'OK-CREATED'
OK_UNCHANGED = 'OK-UNCHANGED'
OK_ROTATED = 'OK-ROTATED'
ERROR = 'ERROR'


class Command(BaseCommand):
    help = 'Sincronitza pricing_catalog.yaml cap a Stripe (idempotent, no destructiu).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply', action='store_true',
            help='Executa els canvis a Stripe. Sense aquest flag, dry-run (per defecte).',
        )

    def handle(self, *args, **opts):
        apply = opts['apply']
        try:
            entries = load_catalog()
        except CatalogError as exc:
            raise CommandError(f'Catàleg invàlid: {exc}')

        # El dry-run també consulta Stripe (només lectura) per a un pla EXACTE
        # crear/actualitzar/rotar. Sense clau: --apply falla; --dry-run degrada a
        # pla teòric (no pot comparar amb l'estat vigent).
        try:
            stripe = configure_stripe()
        except PricingUnavailable as exc:
            if apply:
                raise CommandError(str(exc))
            stripe = None
            self.stdout.write(self.style.WARNING(
                f'⚠ {exc} — dry-run sense estat viu de Stripe (pla teòric).'
            ))

        mode = 'APPLY' if apply else 'DRY-RUN (res es tocarà a Stripe)'
        self.stdout.write(self.style.MIGRATE_HEADING(f'sync_stripe_catalog — {mode}'))

        counts = {OK_CREATED: 0, OK_UNCHANGED: 0, OK_ROTATED: 0, ERROR: 0}
        for e in entries:
            lk = e['lookup_key']
            try:
                outcome, detail = self._sync_entry(stripe, e, apply)
            except Exception as exc:  # noqa: BLE001 — una entrada no ha de tombar les altres
                outcome, detail = ERROR, str(exc)
                logger.exception('sync_stripe_catalog: error a %s', lk)
            counts[outcome] += 1
            self._emit(outcome, lk, detail)

        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING('Resum'))
        self.stdout.write(
            f'  CREATED={counts[OK_CREATED]}  UNCHANGED={counts[OK_UNCHANGED]}  '
            f'ROTATED={counts[OK_ROTATED]}  ERROR={counts[ERROR]}'
        )
        if counts[ERROR]:
            raise CommandError(f'{counts[ERROR]} entrada/es amb ERROR — revisa la sortida.')

    # ── per entrada ──────────────────────────────────────────────────────────
    def _sync_entry(self, stripe, e, apply):
        lk = e['lookup_key']
        product_id = f"fhort_{e['product']}_{e['concepte']}"

        if not apply:
            return self._plan_entry(stripe, e, product_id)

        self._ensure_product(stripe, e, product_id)

        existing = self._find_price_by_lookup(stripe, lk)
        if existing is None:
            self._create_price(stripe, e, product_id, transfer=False)
            return OK_CREATED, f'Price nou amb lookup_key {lk}'

        if self._price_matches(existing, e):
            return OK_UNCHANGED, f'{existing["id"]} ja coincideix'

        # Valors diferents: rota (Prices són immutables).
        new_price = self._create_price(stripe, e, product_id, transfer=True)
        stripe.Price.modify(existing['id'], active=False)
        return OK_ROTATED, (
            f'{existing["id"]} (amount={existing["unit_amount"]}) arxivat → '
            f'{new_price["id"]} (amount={e["unit_amount"]})'
        )

    def _plan_entry(self, stripe, e, product_id):
        """Dry-run: calcula QUÈ passaria sense tocar Stripe. Si no hi ha clau, no
        podem consultar l'estat vigent → ho declarem com a pla teòric."""
        lk = e['lookup_key']
        if stripe is None:
            # Sense clau (dry-run pur): informem el desig, sense poder comparar.
            return OK_CREATED, f'[pla] garantiria Product {product_id} + Price {lk}'
        existing = self._find_price_by_lookup(stripe, lk)
        if existing is None:
            return OK_CREATED, f'[pla] crearia Price {lk} (amount={e["unit_amount"]})'
        if self._price_matches(existing, e):
            return OK_UNCHANGED, f'[pla] {existing["id"]} ja coincideix'
        return OK_ROTATED, (
            f'[pla] rotaria {existing["id"]} ({existing["unit_amount"]}) → '
            f'amount={e["unit_amount"]}'
        )

    # ── primitives Stripe ────────────────────────────────────────────────────
    def _ensure_product(self, stripe, e, product_id):
        """Retrieve fort per id determinista; crea si falta. Idempotent."""
        import stripe as stripe_mod
        try:
            return stripe.Product.retrieve(product_id)
        except stripe_mod.error.InvalidRequestError as exc:
            if getattr(exc, 'code', None) != 'resource_missing':
                raise
        return stripe.Product.create(
            id=product_id,
            name=f"FHORT {e['product'].title()} · {e['concepte']}",
            metadata={'tier': e['product'], 'concepte': e['concepte'], 'fhort': 'pricing'},
        )

    def _find_price_by_lookup(self, stripe, lookup_key):
        res = stripe.Price.list(lookup_keys=[lookup_key], limit=1)
        data = res.data
        return data[0] if data else None

    def _create_price(self, stripe, e, product_id, transfer):
        params = {
            'product': product_id,
            'currency': e['currency'],
            'unit_amount': e['unit_amount'],
            'lookup_key': e['lookup_key'],
            'metadata': {'tier': e['product'], 'concepte': e['concepte']},
        }
        if e['interval'] == 'month':
            params['recurring'] = {'interval': 'month'}
        if transfer:
            params['transfer_lookup_key'] = True
        return stripe.Price.create(**params)

    def _price_matches(self, price, e):
        if price['unit_amount'] != e['unit_amount']:
            return False
        if price['currency'] != e['currency'].lower():
            return False
        recurring = sget(price, 'recurring')
        if e['interval'] == 'month':
            return bool(recurring) and recurring['interval'] == 'month'
        return recurring is None

    # ── sortida ──────────────────────────────────────────────────────────────
    def _emit(self, outcome, lk, detail):
        style = {
            OK_CREATED: self.style.SUCCESS,
            OK_UNCHANGED: self.style.HTTP_NOT_MODIFIED,
            OK_ROTATED: self.style.WARNING,
            ERROR: self.style.ERROR,
        }[outcome]
        self.stdout.write(f'  {style(f"{outcome:<12}")}  {lk}  · {detail}')
