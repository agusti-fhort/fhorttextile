"""
fhort/pom/translation_service.py
LA FONT DE LA ⓘ — el nom d'un POM en la llengua de qui llegeix.

**QUÈ RESOL.** El catàleg v4 té 142 POMs amb el nom canònic en ANGLÈS i sense cap traducció a la
BD, per decisió explícita (09/08): el vocabulari tècnic del sector no és dada de la casa i
duplicar-lo per tenant crearia una segona font de veritat. La ⓘ de les taules de mesures, doncs,
callava — no per avaria, sinó perquè no tenia res a dir. Aquest mòdul és el que li dona veu: PREGUNTA
la traducció a un proveïdor extern, la MEMORITZA (`TranslationCache`) i, si el proveïdor no hi és,
CALLA EN ANGLÈS en comptes de trencar la pantalla.

**LES TRES LLEIS D'AQUEST MÒDUL**

1. **PER REFERÈNCIA, MAI PER TEXT LLIURE.** L'entrada són ids de POM, no cadenes. El text que
   s'envia al proveïdor el resol el servidor a partir del catàleg. Això no és una preferència
   d'estil: un endpoint que traduís text arbitrari seria un proxy de traducció obert amb la clau
   i la quota de la casa a dins, i a més faria que reformular un nom fos una entrada nova de
   cache en comptes de la mateixa.

2. **EL FALLBACK ÉS SILENCIÓS I NO ES MEMORITZA.** Proveïdor caigut, sense clau, timeout, quota
   esgotada → es torna el nom EN i un 200. La ⓘ no ensenya mai un toast vermell per una
   traducció. I el que NO es fa és desar aquell EN com si fos la traducció: quedaria congelat i
   la ⓘ callaria per sempre encara que el proveïdor tornés.

3. **UNA CRIDA PER LOT, I NOMÉS PELS QUE FALTEN.** La pantalla demana els POMs visibles d'un cop;
   els que ja són a la cache no arriben ni a mirar-se el proveïdor. L'univers és finit i petit
   (142 POMs × N idiomes ≈ 17k caràcters UN COP per tenant i idioma).

**EL PROVEÏDOR ÉS UN FORAT, NO UN CABLE.** Per decisió, el proveïdor és DeepL. Cal saber-ho i està
escrit aquí perquè no es descobreixi en producció: **DeepL no tradueix al CATALÀ** (la seva llista
d'idiomes destí no el porta). Amb DeepL, doncs, un usuari en `ca` cau al fallback i la ⓘ li parla en
anglès, mentre que en `es` (o `fr`, `de`, `it`…) parla. Per això la crida al proveïdor viu darrere
`_crida_proveidor` i se'n tria un per `.env` (`TRANSLATE_PROVIDER`): el dia que la ⓘ hagi de parlar
català, es posa la clau de Google —que sí que el té— i no es toca ni una línia de les pantalles.
"""
from __future__ import annotations

import logging

import httpx
from django.conf import settings

from fhort.pom.models import POMMaster, TranslationCache

logger = logging.getLogger(__name__)

# L'idioma del text canònic. Demanar-lo no és una traducció: es respon amb l'original.
LANG_ORIGEN = 'en'

# Sostre d'ids per petició. És **la porta qui el fa complir** (`translation_views`), i aquí
# només es declara.
#
# ⚠️ EL SUPÒSIT ORIGINAL HA CADUCAT. Deia: «l'univers real són 142 POMs; el sostre hi és
# perquè un client equivocat no pugui demanar una pàgina sencera de catàleg com si fos una
# sola pantalla». Doncs resulta que `/poms` **és** la pàgina sencera del catàleg, legítimament
# —carrega totes les pàgines des que `totesLesPagines` va substituir un `page_size: 1000` que
# mentia— i el catàleg d'algun tenant ja ha passat de 300. El sostre no era el problema; el
# problema era que ningú trossejava. Ara trosseja el client (`utils/traduccioPomCua.js`) i
# aquest número torna a ser el que sempre havia de ser: una barana contra una petició absurda,
# no un límit que una pantalla de producte hagi de tocar.
MAX_IDS = 300

# Textos per crida al proveïdor. DeepL n'accepta 50 per petició; amb 142 POMs són 3 crides el
# primer cop de cada idioma, i cap més mai.
MIDA_LOT = 50

TIMEOUT_S = 8.0


def ref_de_pom(pom_id) -> str:
    """La clau estable d'un POM dins la cache. Un sol lloc: el dia que hi entrin els àlies de
    client seran `alias:<id>` i la taula no s'assabentarà de res."""
    return f'pom:{pom_id}'


def normalitza_lang(valor) -> str:
    """`ca-ES` → `ca`. El front envia el que li dona el navegador; aquí es redueix a la base."""
    return (valor or '').strip().lower().replace('_', '-').split('-')[0][:5]


# ── Proveïdors ────────────────────────────────────────────────────────────────────────────
# Contracte comú: reben la llista de textos EN i el codi d'idioma destí, i tornen una llista de
# la MATEIXA llargada amb les traduccions, o `None` si la cosa no ha anat bé. Cap d'ells aixeca
# excepcions: qui els crida ha de poder caure al fallback sense saber què ha passat.

def _deepl(texts, lang):
    clau = getattr(settings, 'DEEPL_API_KEY', '') or ''
    if not clau:
        return None
    # Les claus gratuïtes acaben en `:fx` i NO van al mateix host que les de pagament; endevinar-ho
    # aquí estalvia una variable d'entorn més i el 403 que ningú relaciona amb el host.
    # `DEEPL_API_URL` el sobreescriu: és el que permet posar un DOBLE al davant —una passarel·la,
    # o un servidor de proves— i comprovar el tram sencer, cache i tot, sense la clau real.
    base = (getattr(settings, 'DEEPL_API_URL', '') or '').rstrip('/') or (
        'https://api-free.deepl.com' if clau.endswith(':fx') else 'https://api.deepl.com')
    try:
        r = httpx.post(
            f'{base}/v2/translate',
            headers={'Authorization': f'DeepL-Auth-Key {clau}'},
            json={'text': list(texts), 'source_lang': 'EN', 'target_lang': lang.upper()},
            timeout=TIMEOUT_S,
        )
        r.raise_for_status()
        fora = [t.get('text', '') for t in r.json().get('translations', [])]
    except Exception as e:                                    # noqa: BLE001 — v. llei 2
        logger.warning('translate: DeepL ha fallat (%s): %s', lang, e)
        return None
    return fora if len(fora) == len(texts) else None


def _google(texts, lang):
    clau = getattr(settings, 'GOOGLE_TRANSLATE_API_KEY', '') or ''
    if not clau:
        return None
    try:
        r = httpx.post(
            'https://translation.googleapis.com/language/translate/v2',
            params={'key': clau},
            json={'q': list(texts), 'source': 'en', 'target': lang, 'format': 'text'},
            timeout=TIMEOUT_S,
        )
        r.raise_for_status()
        fora = [t.get('translatedText', '') for t in r.json().get('data', {}).get('translations', [])]
    except Exception as e:                                    # noqa: BLE001 — v. llei 2
        logger.warning('translate: Google ha fallat (%s): %s', lang, e)
        return None
    return fora if len(fora) == len(texts) else None


PROVEIDORS = {'deepl': _deepl, 'google': _google}


def _crida_proveidor(texts, lang):
    """L'ÚNICA porta cap enfora d'aquest tram. És el punt que els tests substitueixen per un
    mock amb comptador: si la cache funciona, aquest comptador no es mou."""
    proveidor = PROVEIDORS.get((getattr(settings, 'TRANSLATE_PROVIDER', '') or 'deepl').lower())
    if proveidor is None or not texts:
        return None
    return proveidor(texts, lang)


# ── El servei ─────────────────────────────────────────────────────────────────────────────

def _nom_canonic(pom: POMMaster) -> str:
    """El text que es tradueix. `name_en` ja resol la cadena de la casa (el `POMGlobal` si el POM
    hi està lligat, el nom del catàleg del tenant si no) — no se'n fabrica una segona aquí."""
    return (pom.name_en or '').strip()


def tradueix_poms(pom_ids, lang):
    """`{pom_id: {'text': str, 'font': 'origen'|'cache'|'api'|'fallback'}}`.

    `font` no és decoració: és el que fa comprovable que la cache i el fallback funcionen sense
    haver d'espiar la BD ni el proveïdor des de fora.
    """
    # 🚨 EL TRUNCAT SILENCIÓS SE'N VA. Això era `list(pom_ids)[:MAX_IDS]`, i convivia amb un
    # `if len(ids) > MAX_IDS: 400` a la vista: **dues polítiques per al mateix límit**, i cap
    # de les dues decidida. La que manava era la de la vista (mai s'hi arribava amb més de
    # MAX_IDS), o sigui que aquest tall era codi mort que deia una cosa contrària a la porta.
    #
    # I si algun dia hagués manat, hauria estat pitjor: retornar els 300 primers de 400 és
    # respondre 200 OK amb un terç de la resposta que falta i sense dir-ho. La llei de la casa
    # ja és l'altra —**un número que menteix és pitjor que un error que parla**, que és el que
    # va motivar `totesLesPagines`—, i per això la decisió és UNA: la porta accepta fins a
    # MAX_IDS i refusa per sobre amb un error clar; aquí no es talla res.
    lang = normalitza_lang(lang)
    ids = []
    for x in pom_ids:
        try:
            i = int(x)
        except (TypeError, ValueError):
            continue
        if i not in ids:
            ids.append(i)
    if not ids:
        return {}

    poms = {p.id: p for p in POMMaster.objects.filter(id__in=ids).select_related('pom_global')}
    fonts = {i: _nom_canonic(poms[i]) for i in ids if i in poms}

    # L'idioma del catàleg no es tradueix: la resposta és l'original. Un POM sense nom tampoc
    # té res a dir, i preguntar-ho gastaria quota per una cadena buida.
    if lang in ('', LANG_ORIGEN):
        return {i: {'text': t, 'font': 'origen'} for i, t in fonts.items()}

    resultat = {}
    pendents = {}

    memoritzat = {
        f.source_ref: f
        for f in TranslationCache.objects.filter(
            lang=lang, source_ref__in=[ref_de_pom(i) for i in fonts],
        )
    }
    for i, original in fonts.items():
        if not original:
            resultat[i] = {'text': '', 'font': 'origen'}
            continue
        fila = memoritzat.get(ref_de_pom(i))
        # `source_text` desigual = el nom canònic s'ha reformulat des que es va traduir. La CLAU
        # no canvia (mateix POM, mateixa entrada); el que es refà és el valor.
        if fila and fila.text and fila.source_text == original:
            resultat[i] = {'text': fila.text, 'font': 'cache'}
        else:
            pendents[i] = original

    if not pendents:
        return resultat

    ordre = list(pendents)
    for tall in range(0, len(ordre), MIDA_LOT):
        lot = ordre[tall:tall + MIDA_LOT]
        traduits = _crida_proveidor([pendents[i] for i in lot], lang)
        if traduits is None:
            # FALLBACK SILENCIÓS: el nom EN, un 200, i cap fila desada.
            for i in lot:
                resultat[i] = {'text': pendents[i], 'font': 'fallback'}
            continue
        for i, text in zip(lot, traduits):
            text = (text or '').strip()
            if not text:
                resultat[i] = {'text': pendents[i], 'font': 'fallback'}
                continue
            TranslationCache.objects.update_or_create(
                source_ref=ref_de_pom(i), lang=lang,
                defaults={
                    'text': text,
                    'source_text': pendents[i],
                    'provider': (getattr(settings, 'TRANSLATE_PROVIDER', '') or 'deepl').lower(),
                },
            )
            resultat[i] = {'text': text, 'font': 'api'}

    return resultat
