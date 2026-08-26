"""NORMALITZACIÓ DELS SLUGS D'INSTÀNCIA A L'ORDRE CANÒNIC (llei d'Agus, 26/08).

## Per què cal

L'ordre dels trams d'un slug compost **entra a la clau única de cinc taules**. Fins al 26/08
l'ordre entre eixos el decidia `order_by('eix')` —alfabètic: `'ESTAT' < 'POSICIO'`— i el
sistema componia `extended-right` mentre la llei escrita deia posició-abans-que-estat. La BD en
porta la prova. Amb l'ordre nou viu i les files velles sense tocar, **re-desar una germana
composaria una clau que no casa amb la seva fila**: l'upsert no la trobaria i faria un INSERT
en comptes d'un UPDATE, amb 200 OK i en silenci.

## Les quatre lleis d'aquesta migració (Agus, 26/08)

1. **TOTES les taules amb `instancia`**, no només les del diccionari. Un slug recompost en una
   taula i vell en una altra trenca les claus creuades (`GradedSpec`, `PieceFittingLine`…). La
   llista NO s'escriu a mà: surt del registre de models, i així no pot quedar-se enrere.
2. **GUARDA DE COL·LISIÓ**: si el slug recompost ja existeix a la mateixa clau —una
   `right-extended` i una `extended-right` convivint—, **avorta i llista**. No tria. Fusionar
   dues germanes és una decisió de domini i no la pren una migració.
3. **IDEMPOTENT I AMB RECOMPTE DECLARAT.** Córrer-la dues vegades no fa res la segona. El pla
   es diu SEMPRE al log, per schema i per taula, perquè aquesta mateixa migració viatja al
   mini-tren i s'aplicarà a PROD **sobre una població que encara no s'ha comptat**.
4. **RES QUE NO SIGUI VOCABULARI DE LA CASA NO ES TOCA.** Un tenant pot crear-se la seva
   instància, i un slug sense família no té ordre canònic: reordenar-lo seria inventar-li una
   posició. Aquestes files es SALTEN i es diuen.

## Ús

    # només mirar (no escriu res):
    python manage.py normalitza_instancies --dry-run
    # amb canari, per al tren:
    python manage.py normalitza_instancies --dry-run --esperades 4
"""
import logging

from fhort.pom.families import familia_de, normalitza, trams_de

logger = logging.getLogger(__name__)


class ColisioDeNormalitzacio(Exception):
    """El slug canònic ja el té una altra fila de la mateixa clau. NO es tria: s'atura."""


def _models_amb_instancia(apps):
    """Tots els models que porten una columna `instancia`, del registre.

    🔑 **NO ÉS UNA LLISTA ESCRITA A MÀ.** Una llista a mà es queda enrere el dia que algú
    afegeixi la columna a una taula nova, i llavors aquella taula es quedaria amb els slugs
    vells mentre la resta del sistema en fa servir de nous — que és el mode de fallada que la
    llei 1 d'Agus vol matar.

    `apps` és el registre HISTÒRIC quan ve d'una migració i el viu quan ve de la comanda: la
    signatura és la mateixa i el resultat, també.
    """
    from django.db import connection

    # ⚠️ **NOMÉS LES TAULES QUE EXISTEIXEN EN AQUEST SCHEMA.** `fhort.pom` viu a SHARED **i** a
    # TENANT alhora, o sigui que una migració seva corre també a `public` — i allà hi ha 4 de
    # les 12 taules (les de `pom`), però cap de `models_app` ni de `fitting`. Sense aquest
    # filtre, la migració peta a `public` amb un `relation does not exist` i el tren s'atura per
    # una taula que en aquell schema no ha d'existir mai. Mesurat: `public` 4 · `fhort` 12 ·
    # `los` 12.
    presents = set(connection.introspection.table_names())
    out = []
    for model in apps.get_models():
        if not any(f.name == 'instancia' for f in model._meta.local_fields):
            continue
        if model._meta.db_table not in presents:
            continue
        out.append(model)
    return sorted(out, key=lambda m: m._meta.label)


def _clau_unica(model):
    """Els camps de la unique que conté `instancia`, o `None` si no n'hi ha cap.

    Sense unique no hi pot haver col·lisió (un log pot repetir el que vulgui), i llavors la
    fila es reescriu sense més comprovacions.
    """
    for ut in (model._meta.unique_together or ()):
        if 'instancia' in ut:
            return list(ut)
    for c in (model._meta.constraints or ()):
        camps = list(getattr(c, 'fields', ()) or ())
        if 'instancia' in camps:
            return camps
    return None


def planifica(apps):
    """`(canvis, colisions, saltades)` sense escriure RES.

    · `canvis`    — `[(model, pk, vell, nou)]`
    · `colisions` — `[(model, pk, vell, nou, pk_ocupant)]` → si n'hi ha cap, no s'aplica res
    · `saltades`  — `[(model, pk, valor, motiu)]` → vocabulari que no és de la casa
    """
    canvis, colisions, saltades = [], [], []
    for model in _models_amb_instancia(apps):
        etiqueta = model._meta.label
        clau = _clau_unica(model)
        # Només les compostes: un slug simple no té ordre i no pot canviar.
        #
        # ⚠️ SENSE `.iterator()`. Aquell obre un cursor de servidor amb NOM, i amb el canvi de
        # schema de `django_tenants` pel mig el cursor deixa d'existir enmig del recorregut
        # (`InvalidCursorName`) — mesurat a `public`. Aquí no cal: el filtre ja retalla a les
        # files amb slug COMPOST, que són una minoria estructural (a `fhort`, 6 de milers).
        #
        # ⚠️ I AMB `.order_by()` BUIT. Diversos d'aquests models porten `Meta.ordering` per un
        # camp de relació, i allò afegeix un JOIN a una taula que a `public` no existeix
        # (`pom_garmentpommap` → `tasks_garmenttypeitem`): la consulta petava en un schema on
        # la taula pròpia sí que hi és. Ordenar no serveix de res aquí i costa un JOIN.
        for fila in model.objects.filter(instancia__contains='-').order_by():
            vell = fila.instancia or ''
            trams = trams_de(vell)
            desconeguts = [t for t in trams if not familia_de(t)]
            if desconeguts:
                saltades.append((etiqueta, fila.pk, vell,
                                 f'trams sense família: {", ".join(desconeguts)}'))
                continue
            nou = normalitza(vell)
            if nou == vell:
                continue
            if clau:
                filtre = {c: getattr(fila, c) for c in clau if c != 'instancia'}
                filtre['instancia'] = nou
                ocupant = model.objects.filter(**filtre).exclude(pk=fila.pk).first()
                if ocupant is not None:
                    colisions.append((etiqueta, fila.pk, vell, nou, ocupant.pk))
                    continue
            canvis.append((etiqueta, fila.pk, vell, nou))
    return canvis, colisions, saltades


def informe(schema, canvis, colisions, saltades, aplicat):
    """El pla, dit al log SEMPRE. És l'única traça que quedarà de la correguda de PROD."""
    verb = 'APLICAT' if aplicat else 'DRY-RUN'
    logger.warning('[normalitza_instancies · %s @ %s] canvis=%d colisions=%d saltades=%d',
                   verb, schema, len(canvis), len(colisions), len(saltades))
    per_model = {}
    for etiqueta, _pk, vell, nou in canvis:
        per_model.setdefault(etiqueta, []).append(f'{vell} → {nou}')
    for etiqueta, mostres in sorted(per_model.items()):
        logger.warning('    %s: %d · %s', etiqueta, len(mostres),
                       ' · '.join(sorted(set(mostres))))
    for etiqueta, pk, valor, motiu in saltades:
        logger.warning('    SALTADA %s pk=%s «%s» — %s', etiqueta, pk, valor, motiu)
    for etiqueta, pk, vell, nou, ocupant in colisions:
        logger.warning('    COL·LISIÓ %s pk=%s «%s» → «%s» ja el té pk=%s',
                       etiqueta, pk, vell, nou, ocupant)


def aplica(apps, schema='?', esperades=None):
    """Normalitza. Avorta si hi ha col·lisions. Torna `(canvis, saltades)`.

    `esperades`: si es dona, el nombre de canvis ha de ser EXACTAMENT aquest o s'atura. És el
    canari per a la correguda controlada (a staging, 4); a PROD es deixa a `None` perquè allà
    la població encara no s'ha comptat i **assertar un número que no sabem seria aturar el tren
    per força**. El que sí que hi ha sempre és el recompte al log.
    """
    canvis, colisions, saltades = planifica(apps)
    informe(schema, canvis, colisions, saltades, aplicat=False)

    if colisions:
        detall = ' · '.join(f'{e} pk={pk} «{v}»→«{n}» ocupada per pk={o}'
                            for e, pk, v, n, o in colisions)
        raise ColisioDeNormalitzacio(
            f'{len(colisions)} col·lisió/ns a «{schema}»: el slug canònic ja el té una altra '
            f'fila de la mateixa clau. Fusionar dues germanes és una decisió de domini i no la '
            f'pren una migració. {detall}')

    if esperades is not None and len(canvis) != esperades:
        raise ColisioDeNormalitzacio(
            f'a «{schema}» s\'esperaven {esperades} canvis i n\'hi ha {len(canvis)}: '
            f'la població no és la que es va censar. No s\'ha escrit res.')

    per_model = {}
    for etiqueta, pk, _vell, nou in canvis:
        per_model.setdefault(etiqueta, []).append((pk, nou))
    models = {m._meta.label: m for m in _models_amb_instancia(apps)}
    for etiqueta, files in per_model.items():
        model = models[etiqueta]
        for pk, nou in files:
            model.objects.filter(pk=pk).update(instancia=nou)

    informe(schema, canvis, colisions, saltades, aplicat=True)
    return canvis, saltades
