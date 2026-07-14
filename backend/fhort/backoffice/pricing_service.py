"""
Servei de pricing — F1 (P-PRICE).

STRIPE ÉS LA FONT DE VERITAT DEL PREU. Aquest mòdul no inventa mai un import: llegeix
el catàleg DESITJAT del YAML (per saber QUINS lookup_keys existeixen) i el preu VIGENT
de Stripe (prices.list amb lookup_keys[]). La BD FHORT no hi entra: només lookup_keys.

Fronteres:
  · load_catalog()      → definició declarativa (YAML). NO és preu vigent.
  · resolve_pricing()   → preu vigent des de Stripe, amb cache 5 min i degradació stale.
  · El sync (management command) empeny catàleg→Stripe; viu a sync_stripe_catalog.py.
"""
import logging

import yaml
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger('fhort.backoffice.pricing')

# Tiers que SÍ van a Stripe (enterprise és contracte a mida, fora de catàleg públic).
TIERS = ('starter', 'team')
CONCEPTES = ('platform', 'model', 'extra_user')

# Camps obligatoris de cada entrada del catàleg.
_REQUIRED = ('product', 'concepte', 'interval', 'currency', 'unit_amount', 'lookup_key')
_INTERVALS = ('month', 'one_time')

# Free NO viu a Stripe (no hi ha res a cobrar): l'endpoint el retorna hardcoded.
FREE_TIER = {
    'platform': {'amount': 0, 'currency': 'eur', 'interval': 'month', 'lookup_key': None},
    'model': {'amount': 0, 'currency': 'eur', 'interval': 'one_time', 'lookup_key': None},
    'extra_user': {'amount': 0, 'currency': 'eur', 'interval': 'month', 'lookup_key': None},
}


def sget(obj, key, default=None):
    """Accés segur a un camp d'un objecte Stripe (StripeObject/ListObject NO tenen
    .get() a stripe 15.x: `.get` es resol com a clave i peta amb AttributeError)."""
    try:
        return obj[key]
    except (KeyError, TypeError):
        return default


class CatalogError(ValueError):
    """El YAML del catàleg és invàlid o incoherent."""


class PricingUnavailable(RuntimeError):
    """Stripe no respon i no hi ha cap cache (ni caducada) per servir."""


def load_catalog():
    """Llegeix i valida pricing_catalog.yaml. Retorna la llista d'entrades (dicts).

    No toca Stripe. Falla fort si una entrada està malformada: preferim un error
    explícit a empènyer brossa a la font de veritat del preu.
    """
    path = settings.STRIPE_PRICING_CATALOG
    try:
        with open(path, 'r', encoding='utf-8') as fh:
            data = yaml.safe_load(fh) or {}
    except FileNotFoundError as exc:
        raise CatalogError(f'Catàleg de pricing no trobat: {path}') from exc

    entries = data.get('entries')
    if not isinstance(entries, list) or not entries:
        raise CatalogError("El catàleg no té cap entrada sota 'entries:'.")

    seen = set()
    for i, e in enumerate(entries):
        if not isinstance(e, dict):
            raise CatalogError(f'Entrada #{i} no és un mapa.')
        for f in _REQUIRED:
            if e.get(f) in (None, ''):
                raise CatalogError(f"Entrada #{i} ({e.get('lookup_key', '?')}): falta '{f}'.")
        if e['product'] not in TIERS:
            raise CatalogError(f"Entrada #{i}: product '{e['product']}' no és {TIERS}.")
        if e['concepte'] not in CONCEPTES:
            raise CatalogError(f"Entrada #{i}: concepte '{e['concepte']}' no és {CONCEPTES}.")
        if e['interval'] not in _INTERVALS:
            raise CatalogError(f"Entrada #{i}: interval '{e['interval']}' no és {_INTERVALS}.")
        if not isinstance(e['unit_amount'], int) or e['unit_amount'] < 0:
            raise CatalogError(f"Entrada #{i}: unit_amount ha de ser enter de cèntims ≥ 0.")
        if e['lookup_key'] in seen:
            raise CatalogError(f"lookup_key duplicat: {e['lookup_key']}.")
        seen.add(e['lookup_key'])
        # Coherència de la convenció {tier}_{concepte}_{moneda}[_{pais}].
        pais = e.get('country')
        expected = build_lookup_key(e['product'], e['concepte'], e['currency'], pais)
        if e['lookup_key'] != expected:
            raise CatalogError(
                f"Entrada #{i}: lookup_key '{e['lookup_key']}' no segueix la convenció "
                f"(esperat '{expected}')."
            )
    return entries


def build_lookup_key(tier, concepte, currency, country=None):
    """Convenció única de lookup_key: {tier}_{concepte}_{moneda}[_{pais}]."""
    base = f'{tier}_{concepte}_{currency.lower()}'
    if country:
        return f'{base}_{country.lower()}'
    return base


def configure_stripe():
    """Configura la clau de Stripe des del .env. Retorna el mòdul stripe llest.

    Falla fort si la clau no hi és: mai s'ha d'inventar un preu ni operar a cegues.
    """
    import stripe
    key = settings.STRIPE_SECRET_KEY
    if not key:
        raise PricingUnavailable('STRIPE_SECRET_KEY no configurada al .env.')
    stripe.api_key = key
    return stripe


def _cache_key(country):
    return f'pricing:v1:{(country or "_").lower()}'


def resolve_pricing(country=None):
    """Preu vigent per a l'endpoint. Retorna (payload, stale: bool).

    · Cache 5 min per país (LocMemCache). Un sol Stripe prices.list per refresc.
    · Resolució per país: {tier}_{concepte}_eur_{pais}; fallback {tier}_{concepte}_eur.
    · Si Stripe no respon: última cache encara que caducada (stale=True); si no n'hi ha,
      PricingUnavailable. MAI s'inventen preus.
    """
    key = _cache_key(country)
    fresh = cache.get(key)
    if fresh is not None:
        return fresh, False

    try:
        payload = _fetch_from_stripe(country)
    except PricingUnavailable:
        raise
    except Exception as exc:  # noqa: BLE001 — qualsevol fallada de xarxa/Stripe
        logger.warning('Stripe pricing indisponible (%s); intento cache stale.', exc)
        stale = cache.get(_stale_key(key))
        if stale is not None:
            return stale, True
        raise PricingUnavailable('Stripe no respon i no hi ha cache disponible.') from exc

    cache.set(key, payload, settings.PRICING_CACHE_TTL)
    # Còpia stale sense TTL (o molt llarg) per a degradació: sobreviu al refresc.
    cache.set(_stale_key(key), payload, None)
    return payload, False


def _stale_key(key):
    return f'{key}:stale'


def _fetch_from_stripe(country):
    """Construeix el payload de pricing llegint els Prices vigents de Stripe.

    Una sola crida prices.list(lookup_keys=[...]) per tots els conceptes; després
    resol país amb fallback. Free s'afegeix hardcoded (no viu a Stripe).
    """
    stripe = configure_stripe()

    # Candidats de lookup_key: per cada tier/concepte, la variant de país (si escau) i la base.
    wanted = {}          # lookup_key -> (tier, concepte, is_country_variant)
    for tier in TIERS:
        for concepte in CONCEPTES:
            base_lk = build_lookup_key(tier, concepte, 'eur')
            wanted[base_lk] = (tier, concepte, False)
            if country:
                ck = build_lookup_key(tier, concepte, 'eur', country)
                wanted[ck] = (tier, concepte, True)

    prices = stripe.Price.list(
        lookup_keys=list(wanted.keys()), active=True, limit=100,
    )
    by_lookup = {sget(p, 'lookup_key'): p for p in prices.data if sget(p, 'lookup_key')}

    payload = {'free': _free_payload()}
    for tier in TIERS:
        payload[tier] = {}
        for concepte in CONCEPTES:
            base_lk = build_lookup_key(tier, concepte, 'eur')
            chosen = None
            if country:
                chosen = by_lookup.get(build_lookup_key(tier, concepte, 'eur', country))
            if chosen is None:
                chosen = by_lookup.get(base_lk)
            payload[tier][concepte] = _price_payload(chosen)
    return payload


def _price_payload(price):
    """Normalitza un Price de Stripe a la forma de resposta. None → concepte absent."""
    if price is None:
        return None
    recurring = sget(price, 'recurring')
    interval = recurring['interval'] if recurring else 'one_time'
    return {
        'amount': price['unit_amount'],
        'currency': price['currency'],
        'interval': interval,
        'lookup_key': price['lookup_key'],
    }


def _free_payload():
    return {k: dict(v) for k, v in FREE_TIER.items()}


def invalidate_pricing_cache(country=None):
    """Buida la cache fresca (no la stale) per a un país; útil després d'un sync."""
    cache.delete(_cache_key(country))
