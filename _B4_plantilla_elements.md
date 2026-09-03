# B4 · Plantilla d'elements a l'item — informe de lectura pura

> **Mode:** LECTURA PURA. Cap escriptura, cap migració, cap fitxer de codi tocat.
> **Data:** 2026-08-07 · **Working dir:** `/var/www/ftt-staging` (backend a `backend/`)
> **Mètode:** censos de relacions per `Model._meta.related_objects` (mai `information_schema`
> per a relacions). Els recomptes de FILES sí que van per SQL directe amb `SET search_path`,
> perquè el que es vol saber és exactament «existeix la taula en aquest schema i quantes files hi ha».

---

## 🚨 TITULAR — LA MIGRACIÓ 0073 NO ESTÀ APLICADA A CAP SCHEMA

`GarmentTypePOMMap` i `GarmentGroupPOMMap` existeixen **només com a codi Python**.
Les seves taules **no existeixen a `public`, ni a `fhort`, ni a `los`**.

```
public ['0072_cat22_sembra_garmentgroup', '0071_...', '0070_...', '0069_...', '0068_...']
fhort  ['0072_cat22_sembra_garmentgroup', '0071_...', '0070_...', '0069_...', '0068_...']
los    ['0072_cat22_sembra_garmentgroup', '0071_...', '0070_...', '0069_...', '0068_...']
```

`fhort/pom/migrations/0073_u2_acumulacio_poms.py` és al disc (generada 2026-08-07 07:29) i
**cap dels tres schemes l'ha aplicada**. Confirma la bandera 🚩 de la memòria
(`ftt-u1u2-catalegs`: «la `0073` no s'ha aplicat»).

**Conseqüència operativa immediata:** `acumula_poms_de_item()` **peta avui** contra qualsevol
schema (`ProgrammingError: relation "pom_garmentgrouppommap" does not exist`) tan bon punt
l'item tingui família — i sempre en té. L'endpoint `/acumulacio/` és, ara mateix, un 500 segur.
No hi ha cap `try/except` que ho amagui a `acumulacio.py` ni a `cataleg_views.py`.

---

## 1 · Definicions literals de `_POMMapBase`, `GarmentTypePOMMap`, `GarmentGroupPOMMap`

**Consultat:** `/var/www/ftt-staging/backend/fhort/pom/models.py:884-973`
(+ el bloc de decisió d'arquitectura immediatament anterior, `models.py:884-905`, que forma part
de la definició perquè hi diu *per què* són tres taules i no una).

### 1.a · El comentari de decisió que precedeix les tres — `fhort/pom/models.py:884-905`

```python
# ── U2 · LA LLEI DE L'ACUMULACIÓ (decisió Agus, 2026-08-07) ───────────────────────────────────
#
# El catàleg de POMs **s'acumula per nivell i PROPOSA**: el grup aporta, la família suma, l'item
# suma. Res exclou res, i un mateix POM pot ser a molts items. Fins avui la pertinença només
# sabia viure a l'ITEM (`GarmentPOMMap`, 1.748 files), i els dos nivells de sobre no hi cabien.
#
# **PER QUÈ TRES TAULES GERMANES I NO UNA AMB FKs NULLABLES** (la decisió, amb el seu motiu):
#   1. A Postgres els NULL **no comparen iguals**, o sigui que un `unique_together` sobre una FK
#      nullable deixaria de protegir exactament els dos nivells nous. Un constraint que existeix
#      i no protegeix és pitjor que cap.
#   2. El «Ve de» de la pantalla ha de dir de QUIN nivell arriba cada POM. Amb tres taules la
#      resposta és la taula mateixa; amb FKs nullables es respondria **per absència**, que és
#      fràgil.
#   3. Risc zero per a les 1.748 files vives i els 103 lectors de `GarmentPOMMap`, que no
#      s'assabenten que existeixen aquestes dues.
#
# L'acumulació és, doncs, una **UNIÓ A LA LECTURA** (v. `acumula_poms_de_item`), no una jerarquia
# a la BD. Cap fila existent es migra: el que avui és de l'item, de l'item es queda.
#
# ⚠️ Les FK d'aquestes dues van cap a `GarmentType` i `GarmentGroup`, que viuen a **la mateixa
# app** (`pom`) — per això SÍ que porten constraint de BD real, a diferència de la germana de
# l'item, que ha de creuar cap a `tasks` (tenant-only) amb `db_constraint=False`.
```

### 1.b · `_POMMapBase` — `fhort/pom/models.py:907-935`

```python
class _POMMapBase(models.Model):
    """El que les tres pertinences comparteixen: el POM, la seva capa, la seva instància i els
    tres eixos de com de fort es reclama (`obligatori`/`is_key`/`nivell`).

    Abstracta a posta: no crea taula i no toca `GarmentPOMMap`, que es queda tal com estava.
    """

    obligatori = models.BooleanField(default=False)
    is_key = models.BooleanField(default=False)
    nivell = models.CharField(
        max_length=1, blank=True, default='O',
        choices=[('K', 'Key'), ('M', 'Mandatory'), ('O', 'Optional'), ('D', 'Detail-dependent')],
    )
    ordre = models.PositiveIntegerField(default=0)
    pendent_revisio = models.BooleanField(default=False)
    # Mateixa declaració que a `GarmentPOMMap` i pel mateix motiu: la capa i la instància
    # formen part de la IDENTITAT de la pertinença (el mateix POM a l'exterior i al folre són
    # dues pertinences, i la sisa dreta i l'esquerra també). Per slug, mai per PK (llei G9).
    capa = models.CharField(
        max_length=20, default='exterior', db_index=True,
        help_text="Capa de mesura: slug de pom.MeasurementLayer (per SLUG, mai per PK).",
    )
    instancia = models.CharField(
        max_length=60, default='', db_index=True,
        help_text="Instància del POM dins la capa: slug compost canònic. '' és la instància única.",
    )

    class Meta:
        abstract = True
```

**FKs:** cap. `_POMMapBase` **no declara cap FK** — ni tan sols `pom`. Cada filla declara la seva.
**Meta:** només `abstract = True`. Cap constraint, cap ordering, cap unique.

### 1.c · `GarmentTypePOMMap` — `fhort/pom/models.py:938-954`

```python
class GarmentTypePOMMap(_POMMapBase):
    """POMs que aporta una FAMÍLIA (`GarmentType`). Se sumen als del grup i als de l'item."""

    garment_type = models.ForeignKey(
        'pom.GarmentType', on_delete=models.CASCADE, related_name='pom_maps')
    pom = models.ForeignKey(POMMaster, on_delete=models.PROTECT,
                            related_name='garment_type_maps')

    class Meta:
        verbose_name = 'Mapa família ↔ POM'
        verbose_name_plural = 'Mapes família ↔ POM'
        ordering = ['garment_type', 'ordre']
        # La MATEIXA clau que la germana de l'item, amb el nivell com a primer element.
        unique_together = [('garment_type', 'pom', 'capa', 'instancia')]

    def __str__(self):
        return f'{self.garment_type.codi_client} · {self.pom.codi_client}'
```

| FK | destí | `on_delete` | `db_constraint` | `related_name` |
|---|---|---|---|---|
| `garment_type` | `pom.GarmentType` | **CASCADE** | default → **True** (constraint real) | `pom_maps` |
| `pom` | `pom.POMMaster` | **PROTECT** | default → **True** | `garment_type_maps` |

**Meta:** `unique_together = [('garment_type','pom','capa','instancia')]`. **`constraints = []`
(no en declara cap).** Ordering `['garment_type','ordre']`.

### 1.d · `GarmentGroupPOMMap` — `fhort/pom/models.py:957-972`

```python
class GarmentGroupPOMMap(_POMMapBase):
    """POMs que aporta un GRUP (`GarmentGroup`), el nivell més bast de l'acumulació."""

    garment_group = models.ForeignKey(
        'pom.GarmentGroup', on_delete=models.CASCADE, related_name='pom_maps')
    pom = models.ForeignKey(POMMaster, on_delete=models.PROTECT,
                            related_name='garment_group_maps')

    class Meta:
        verbose_name = 'Mapa grup ↔ POM'
        verbose_name_plural = 'Mapes grup ↔ POM'
        ordering = ['garment_group', 'ordre']
        unique_together = [('garment_group', 'pom', 'capa', 'instancia')]

    def __str__(self):
        return f'{self.garment_group.codi} · {self.pom.codi_client}'
```

| FK | destí | `on_delete` | `db_constraint` | `related_name` |
|---|---|---|---|---|
| `garment_group` | `pom.GarmentGroup` | **CASCADE** | default → **True** | `pom_maps` |
| `pom` | `pom.POMMaster` | **PROTECT** | default → **True** | `garment_group_maps` |

**Meta:** `unique_together`, cap `constraints`.

### 1.e · La tercera germana, que **NO** hereta de `_POMMapBase` — `GarmentPOMMap`, `fhort/pom/models.py:809-881`

Cal dir-ho perquè trenca la simetria del patró i és el que qualsevol proposta ha de respectar:

```python
class GarmentPOMMap(models.Model):
    garment_type_item = models.ForeignKey('tasks.GarmentTypeItem', on_delete=models.CASCADE,
                                          related_name='pom_maps', null=True, blank=True,
                                          db_constraint=False)
    pom = models.ForeignKey(POMMaster, on_delete=models.PROTECT, related_name='garment_maps')
    ...
    class Meta:
        ...
        unique_together = [('garment_type_item', 'pom', 'capa', 'instancia')]
        constraints = [
            # ✅ C4/G4 (04/08) — retirada per la migració pom/0057 ...
        ]   # ← llista BUIDA en efecte: només comentaris
```

Diferències dures respecte de les dues noves:
- **`null=True, blank=True`** a l'àncora (les dues noves són NOT NULL).
- **`db_constraint=False`** (creua `pom` SHARED → `tasks` tenant-only).
- **No hereta `_POMMapBase`**: repeteix els camps a mà (`models.py:820-849`). Refactoritzar-la
  cap a la base era el «risc zero» que la decisió d'U2 va decidir NO córrer.

---

## 2 · Com resol l'acumulació a la lectura

**Consultat:** `/var/www/ftt-staging/backend/fhort/pom/acumulacio.py` **sencer (103 línies)**.

### 2.a · Verificació de la premissa de la memòria

La nota deia «l'acumulació són DUES TAULES GERMANES i una UNIÓ A LA LECTURA». **El codi diu
TRES, no dues.** `acumulacio.py:3-6`:

> «La jerarquia NO viu a la BD —hi ha **tres** taules germanes i independents
> (`GarmentGroupPOMMap`, `GarmentTypePOMMap`, `GarmentPOMMap`)—: viu AQUÍ, com una unió a la lectura.»

Les *noves* són dues (`0073`); les que participen de la unió són **tres**, perquè la vella
`GarmentPOMMap` és el nivell ITEM. La part «UNIÓ A LA LECTURA» queda **confirmada literalment**
(`models.py:900`, `acumulacio.py:6`).

### 2.b · La funció clau, enganxada — `fhort/pom/acumulacio.py:52-90`

```python
def acumula_poms_de_item(item):
    """El catàleg acumulat d'un `GarmentTypeItem`: llista de dicts, un per pertinença viva.

    Ordre de resolució: grup → família → item. El més específic guanya la identitat i es queda
    els altres a `tambe_a`. Retorna llista buida si l'item no té família (dada incompleta, no
    error): sense família no hi ha ni grup ni res a acumular.
    """
    from fhort.pom.models import GarmentGroupPOMMap, GarmentPOMMap, GarmentTypePOMMap

    familia = item.garment_type
    if familia is None:
        return []
    grup = familia.grup_ref            # C6 pas 1: la FK de grup. NULL = família sense grup encara.

    trams = []
    if grup is not None:
        trams.append((NIVELL_GRUP, grup.codi, GarmentGroupPOMMap.objects
                      .filter(garment_group=grup).select_related('pom')))
    trams.append((NIVELL_FAMILIA, familia.codi_client, GarmentTypePOMMap.objects
                  .filter(garment_type=familia).select_related('pom')))
    trams.append((NIVELL_ITEM, item.code, GarmentPOMMap.objects
                  .filter(garment_type_item=item).select_related('pom')))

    per_clau = {}
    for nivell, ancora, qs in trams:
        for m in qs:
            k = _clau(m)
            anterior = per_clau.get(k)
            nova = _fila(m, nivell, ancora)
            if anterior is not None:
                # El més específic tapa l'anterior, però se n'endú la memòria.
                nova['tambe_a'] = anterior['tambe_a'] + [
                    {'nivell': anterior['nivell'], 'ancora': anterior['ancora']}]
            per_clau[k] = nova

    # Ordre de pantalla: pel nivell que APORTA (el bast primer, que és com es llegeix un
    # catàleg que creix), i dins del nivell per l'`ordre` que cada taula ja declara.
    pes = {n: i for i, n in enumerate(NIVELLS)}
    return sorted(per_clau.values(), key=lambda f: (pes[f['nivell']], f['ordre'], f['pom_id']))
```

I les tres peces que la sostenen:

```python
# acumulacio.py:21-25
NIVELL_GRUP = 'grup'
NIVELL_FAMILIA = 'familia'
NIVELL_ITEM = 'item'
NIVELLS = (NIVELL_GRUP, NIVELL_FAMILIA, NIVELL_ITEM)

# acumulacio.py:28-30
def _clau(m):
    """La identitat d'una pertinença: el POM, a quina capa i en quina instància."""
    return (m.pom_id, m.capa, m.instancia)

# acumulacio.py:33-49
def _fila(m, nivell, anchor):
    return {
        'nivell': nivell, 'ancora': anchor, 'map_id': m.id, 'pom_id': m.pom_id,
        'capa': m.capa, 'instancia': m.instancia, 'obligatori': m.obligatori,
        'is_key': m.is_key, 'nivell_excel': m.nivell, 'ordre': m.ordre,
        'pendent_revisio': m.pendent_revisio,
        'tambe_a': [],
    }
```

### 2.c · Resposta EXACTA a les tres preguntes

**Quina és la precedència.** Per **ordre d'iteració de `trams`**, no per cap camp de dades:
`grup → família → item`. El `dict` `per_clau` **sobreescriu**: `per_clau[k] = nova` s'executa
sempre, tapat o no. Com que l'item s'itera l'últim, **guanya l'item**. És a dir: la precedència
és **posicional al codi**, i canviar l'ordre de `trams.append(...)` canviaria la llei sense
tocar cap taula. `acumulacio.py:16` ho declara: «Guanya el nivell MÉS ESPECÍFIC (item > família > grup)».

**Com desempata.** No hi ha desempat *dins* d'un nivell: l'`unique_together`
`(àncora, pom, capa, instancia)` de cada taula garanteix que un nivell no pot reclamar dues
vegades la mateixa clau `(pom, capa, instancia)` per a la mateixa àncora. Entre nivells, no és
desempat sinó **substitució total de la fila**: la nova fila porta *tots* els seus atributs
(`obligatori`, `is_key`, `ordre`, `nivell_excel`, `pendent_revisio`, `map_id`) i els de
l'anterior **es perden**, excepte el rastre `{'nivell','ancora'}` que va a `tambe_a`.
⚠️ **Cap merge d'atributs.** Si el grup diu `obligatori=True` i l'item diu `obligatori=False`,
el resultat és `False` — l'obligatorietat del grup desapareix. Això és disseny, no bug, però
no està escrit enlloc del docstring.

**Què passa si una entrada apareix a les dues (o tres) taules.** Surt **una sola fila** al
resultat, la del nivell més específic, amb `tambe_a` acumulant els anteriors **en ordre
cronològic d'aparició** (`nova['tambe_a'] = anterior['tambe_a'] + [...]`) — o sigui, si el
mateix POM és a grup + família + item, la fila final és la de l'item i
`tambe_a == [{'nivell':'grup',...}, {'nivell':'familia',...}]`. Cap error, cap duplicat, cap
409: `acumulacio.py:14-18` ho declara «el cas normal».

**El recompte** — `acumulacio.py:93-103`:

```python
def recompte_per_nivell(acumulat):
    """`{grup: n, familia: n, item: n, total: n}` — el que la columna de la llista d'items pinta.

    Compta el que cada nivell APORTA de debò (el que no ha estat tapat per un de més específic),
    perquè la barra de la maqueta ha de sumar exactament el total.
    """
    r = {n: 0 for n in NIVELLS}
    for f in acumulat:
        r[f['nivell']] += 1
    r['total'] = sum(r[n] for n in NIVELLS)
    return r
```

`total` és, per construcció, `len(acumulat)`: només compta files supervivents.

### 2.d · Dos forats que la lectura destapa

1. **Sense família → llista buida** (`acumulacio.py:62-63`). `GarmentTypeItem.garment_type` és
   **NOT NULL** (`tasks/models.py:417-418`, `on_delete=CASCADE`, sense `null=True`), o sigui que
   aquesta branca és **codi mort a la BD actual**. No fa mal, però no és el guard que sembla.
2. **Sense grup → el tram del grup no s'afegeix** (`acumulacio.py:67`). `GarmentType.grup_ref` és
   nullable (C6 pas 1, `pom/models.py:759-764`, `on_delete=PROTECT`). Com que el **pas 2 de C6
   no s'ha fet** (memòria `ftt-cataleg-talles-c1c6`), avui hi ha famílies amb `grup_ref=NULL` que
   **saltarien el nivell grup en silenci**. L'acumulació no ho reporta a la resposta.

---

## 3 · Qui CONSUMEIX l'acumulació avui

**Consultat:** grep de `acumula_poms_de_item|recompte_per_nivell|acumulacio|tambe_a` sobre
`backend/**/*.py`, `frontend/src/**`, `frontend-backoffice/src/**`.

### Backend

| # | Fitxer:línia | Què fa |
|---|---|---|
| 1 | `backend/fhort/pom/cataleg_views.py:25` | `from fhort.pom.acumulacio import acumula_poms_de_item, recompte_per_nivell` |
| 2 | `backend/fhort/pom/cataleg_views.py:183` | `acumulat = acumula_poms_de_item(item)` — dins `item_acumulacio_view` |
| 3 | `backend/fhort/pom/cataleg_views.py:202` | `'recompte': recompte_per_nivell(acumulat)` |
| 4 | `backend/fhort/pom/urls.py:99` | `from .cataleg_views import item_acumulacio_view, pom_us_view` |
| 5 | `backend/fhort/pom/urls.py:102` | `path('garment-type-items/<int:item_id>/acumulacio/', item_acumulacio_view)` |

**Cap altre cridant de producció.** Ni la sembra item→model, ni el grading, ni els loaders,
ni `bootstrap_tenant`, ni cap serializer.

### Tests (l'únic altre consumidor de la funció)

`backend/fhort/pom/test_u2_acumulacio.py:16-17` (import), i les crides a
`:66, :86, :87, :98, :114, :131, :136, :145, :157-158`.

### Frontend

| # | Fitxer:línia | Què fa |
|---|---|---|
| 1 | `frontend/src/api/endpoints.js:522` | `acumulacio: (id) => client.get(\`/api/v1/garment-type-items/${id}/acumulacio/\`)` |

**🛑 CAP component la crida.** `garmentTypeItems.acumulacio` està declarat i **no s'invoca des de
cap `.jsx`**. `frontend-backoffice/src` no la coneix. Confirma la memòria: «la pantalla de U2
NO està feta».

### Consumidors indirectes (llegeixen les DUES taules noves sense passar per `acumulacio.py`)

Importants per a P7, perquè són camins que una taula nova hauria de considerar:

| Fitxer:línia | Què llegeix |
|---|---|
| `backend/fhort/pom/views.py:426-435` | `GarmentTypePOMMapViewSet` → `/api/v1/garment-type-pom-maps/` (CRUD pla, `?garment_type=`) |
| `backend/fhort/pom/views.py:437-446` | `GarmentGroupPOMMapViewSet` → `/api/v1/garment-group-pom-maps/` (CRUD pla, `?garment_group=`) |
| `backend/fhort/pom/views.py:411-423` | `_POMMapNivellViewSet` — el motlle compartit (lectura `IsAuthenticated`, escriptura gated `CONFIGURE`) |
| `backend/fhort/pom/urls.py:33-34` | registre al router |
| `backend/fhort/pom/serializers.py:498-511` · `:512-524` | `GarmentTypePOMMapSerializer` · `GarmentGroupPOMMapSerializer` |
| `backend/fhort/pom/cataleg_views.py:64-65` | `_tres_comptadors` — `pom.garment_type_maps` / `pom.garment_group_maps` (fitxa d'ús d'un POM) |
| `backend/fhort/pom/cataleg_views.py:99-100` | `_us_observat` — capes/instàncies observades a les tres pertinences |
| `backend/fhort/pom/cataleg_views.py:37` | `_cens_relacions` — recorre `POMMaster._meta.related_objects`, o sigui que **veurà sola** qualsevol germana nova |

🔑 `_cens_relacions` (`cataleg_views.py:29-52`) és el cens genèric per `related_objects`: **una
taula germana nova hi entra sense tocar-lo**. Això és exactament el que la lliçó TGIRL del 07/08
demanava, i és un punt a favor de proposar una germana en comptes d'una columna nova.

---

## 4 · `ItemBaseSet`

### 4.a · Definició literal sencera — `/var/www/ftt-staging/backend/fhort/pom/models.py:975-1063`

```python
class ItemBaseSet(models.Model):
    """Sprint BaseSet condicionat (B1, 2026-07-25). Satèl·lit de mesures base de l'Item per MÓN.

    LLEI (Patró C, Agus 2026-07-25): «L'item MAI es parteix. Un sol GTI per peça, un sol superset
    de POMs. El món viu als satèl·lits: BaseSets condicionats per (item × size_system × fit).»
    Això substitueix el pointer únic GarmentTypeItem.base_size_definition (V1, llegat a jubilar):
    un item pot vestir-se en ALPHA_EU_M i en KIDS_CM alhora, i cada món té la seva talla base i
    els seus valors, sense partir l'item ni duplicar el superset de POMs (GarmentPOMMap).

    CAP scope-node, cap àmbit, cap cascada: el matching és un LOOKUP DIRECTE per la clau única
    (garment_type_item, size_system, fit_type). Vegeu `resolve_item_base_set()`.

    `fit_type` és NULLABLE per la llei, però la convenció de lookup és REGULAR: tant la creació
    com el resolver passen pel mateix `normalize_fit_type()`, que tradueix «cap fit» → el FitType
    REGULAR del schema. NULL només subsisteix en schemas que no tenen FitType sembrat (avui `los`).
    Sense aquesta normalització compartida un set creat sense fit i una cerca sense fit podrien
    caure en files diferents. Les DUES constraints d'unicitat (la normal i la parcial per a
    fit_type IS NULL) hi són perquè a Postgres NULL no participa en un UNIQUE: sense la parcial,
    dos sets «sense fit» del mateix món podrien conviure.

    db_constraint=False al FK cap a 'tasks' pel mateix motiu que GarmentPOMMap i
    ItemBaseMeasurement: 'pom' és app SHARED (taula també a 'public') i 'tasks' és tenant-only.
    """
    ORIGEN_PROMOCIO = 'PROMOCIO'  # nascut d'una promoció model→set (via canònica de naixement, B3)
    ORIGEN_MASTER = 'MASTER'      # entrat per paquet/màster de catàleg
    ORIGEN_MANUAL = 'MANUAL'      # creat a mà al catàleg (ItemAuthoring)
    ORIGEN_CHOICES = [
        (ORIGEN_PROMOCIO, 'Promogut des d\'un model'),
        (ORIGEN_MASTER, 'Màster de catàleg'),
        (ORIGEN_MANUAL, 'Creat manualment'),
    ]

    garment_type_item = models.ForeignKey('tasks.GarmentTypeItem', on_delete=models.CASCADE,
                                          related_name='base_sets', db_constraint=False)
    size_system = models.ForeignKey(SizeSystem, on_delete=models.PROTECT,
                                    related_name='item_base_sets')
    # PROTECT i no SET_NULL: el fit és part de la clau única. Un SET_NULL col·lapsaria el set
    # dins l'slot «sense fit» del mateix món i podria xocar amb un que ja hi visqués.
    # Referència per string: FitType es declara més avall en aquest mateix mòdul.
    fit_type = models.ForeignKey('pom.FitType', on_delete=models.PROTECT, null=True, blank=True,
                                 related_name='item_base_sets',
                                 help_text="Buit = Regular (convenció de lookup).")
    # OBLIGATÒRIA per la llei 2: la talla base es declara EN CREAR el set, i totes les mesures
    # del set s'hi expressen. PROTECT: esborrar la talla base d'un set viu ha de BLOQUEJAR.
    base_size_definition = models.ForeignKey('pom.SizeDefinition', on_delete=models.PROTECT,
                                             related_name='base_set_for_items',
                                             help_text="Talla base del set (on s'expressen els valors).")

    # Provinença i autoria — mateix patró P9 que ItemBaseMeasurement (2026-07-22).
    origen = models.CharField(max_length=20, choices=ORIGEN_CHOICES, default=ORIGEN_MANUAL)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='item_base_sets_updated',
    )

    class Meta:
        verbose_name = 'Set de mesures base d\'item'
        verbose_name_plural = 'Sets de mesures base d\'item'
        ordering = ['garment_type_item', 'size_system', 'fit_type']
        constraints = [
            models.UniqueConstraint(
                fields=['garment_type_item', 'size_system', 'fit_type'],
                name='uniq_itembaseset_item_system_fit',
            ),
            models.UniqueConstraint(
                fields=['garment_type_item', 'size_system'],
                condition=models.Q(fit_type__isnull=True),
                name='uniq_itembaseset_item_system_nofit',
            ),
        ]

    def clean(self):
        # La talla base ha de viure al sistema del set. Mateix esperit que GarmentTypeItem.clean()
        # (tasks/models.py:341): validació d'ORM, no constraint de BD (cross-table fràgil).
        super().clean()
        if self.base_size_definition_id and self.size_system_id:
            if self.base_size_definition.size_system_id != self.size_system_id:
                from django.core.exceptions import ValidationError
                raise ValidationError({
                    'base_size_definition': (
                        "La talla base ha de pertànyer al sistema de talles del set.")
                })

    def __str__(self):
        anchor = self.garment_type_item.code if self.garment_type_item_id else '?'
        fit = self.fit_type.codi if self.fit_type_id else 'REGULAR'
        return f'{anchor} · {self.size_system.codi} · {fit} @ {self.base_size_definition.etiqueta}'
```

**Taula de FKs:**

| FK | destí | `on_delete` | `db_constraint` | null | `related_name` |
|---|---|---|---|---|---|
| `garment_type_item` | `tasks.GarmentTypeItem` | CASCADE | **False** (creua SHARED→tenant) | no | `base_sets` |
| `size_system` | `pom.SizeSystem` | PROTECT | True | no | `item_base_sets` |
| `fit_type` | `pom.FitType` | PROTECT | True | **sí** | `item_base_sets` |
| `base_size_definition` | `pom.SizeDefinition` | PROTECT | True | no | `base_set_for_items` |
| `updated_by` | `AUTH_USER_MODEL` | SET_NULL | True | sí | `item_base_sets_updated` |

**🔑 Nota per a P7:** `ItemBaseSet` **NO té cap camp de peça/element/capa/instància**.
El seu eix és exclusivament **el MÓN** = `(item, size_system, fit_type)`.

### 4.b · Tots els usos al codi

**Producció (backend):**

| Fitxer:línia | Ús |
|---|---|
| `backend/fhort/pom/models.py:975` | definició |
| `backend/fhort/pom/models.py:1123` | docstring de `resolve_item_base_set` |
| `backend/fhort/pom/models.py:1135` | `return ItemBaseSet.objects.filter(...)` — el resolver, **lookup directe, cap heurística** |
| `backend/fhort/pom/models.py:1190` | `ItemBaseMeasurement.base_set = FK('pom.ItemBaseSet', on_delete=CASCADE, related_name='measurements')` |
| `backend/fhort/pom/views.py:22` · `:40` | imports |
| `backend/fhort/pom/views.py:448-457` | `ItemBaseSetViewSet` — queryset amb `annotate(mesures_count, mesures_amb_valor)` |
| `backend/fhort/pom/views.py:485` | `serializer.save(origen=ItemBaseSet.ORIGEN_MANUAL, updated_by=...)` |
| `backend/fhort/pom/views.py:567` | `sets_item = ItemBaseSet.objects.filter(garment_type_item_id=item_id)` (creació d'`ItemBaseMeasurement`: resolució del set, 400 `base_set_absent` si no n'hi ha) |
| `backend/fhort/pom/urls.py:14` · `:36` | router `item-base-sets` |
| `backend/fhort/pom/serializers.py:18` · `:526-550` | `ItemBaseSetSerializer` (`origen` read-only) |
| `backend/fhort/pom/management/commands/load_losan_package.py:396` · `:400` · `:405` | `get_or_create(..., origen=ORIGEN_MASTER)` en carregar el paquet |
| `backend/fhort/pom/management/commands/cleanup_losan_old.py:34` | comentari: `(ItemBaseSet, PROTECT)` al cens de bloquejants |
| `backend/fhort/models_app/views.py:1334` | import a `materialize_poms_view` (sembra item→model) |
| `backend/fhort/models_app/views.py:1362` | `base_set = resolve_item_base_set(item, model.size_system_id, model.fit_type)` |
| `backend/fhort/models_app/views.py:4255` · `:4295` | import + resolució a la via de PROMOCIÓ model→item |
| `backend/fhort/models_app/views.py:4553-4554` | `acte_canonic_base_set_view` — `POST /api/v1/item-base-sets/<id>/acte-canonic/` |
| `backend/fhort/models_app/urls.py:38` · `:247` | registre de l'acte canònic |

**Frontend:**

| Fitxer:línia | Ús |
|---|---|
| `frontend/src/api/endpoints.js:686-691` | `itemBaseSets` = `{list, create, remove, acteCanonic}` |
| `frontend/src/components/BaseSetPanel/BaseSetPanel.jsx:4` | import |
| `frontend/src/components/BaseSetPanel/BaseSetPanel.jsx:67` | `itemBaseSets.list({...})` |
| `frontend/src/components/BaseSetPanel/BaseSetPanel.jsx:117` | `itemBaseSets.create({...})` |
| `frontend/src/components/BaseSetPanel/BaseSetPanel.jsx:144` | `itemBaseSets.remove(set.id)` |

**Tests i scripts:** `backend/fhort/models_app/tests_sembra_grading.py:32, 93, 954, 956, 969-970, 1001`;
`backend/scripts_tmp/v2_cens_defaults.py:30, 76`; `backend/scripts_tmp/v2_neteja_defaults.py:56, 76, 78, 84, 95, 99, 101, 111`.

### 4.c · Recompte de files per schema

| schema | `pom_itembaseset` |
|---|---|
| `public` | **0** |
| `fhort` | **1** |
| `los` | **0** |

⚠️ **`fhort` = 1** és una xifra que crida. `ItemBaseSet` és un satèl·lit **de catàleg** (penja
d'un `GarmentTypeItem`, no d'un `Model`) i el wipe de models del 06/08 **no l'hauria d'haver
tocat** (no hi ha cap FK `Model → ItemBaseSet`). Amb 62 items i 1.748 `GarmentPOMMap` a `fhort`,
que hi hagi **1 sol BaseSet** vol dir que la via V2 pràcticament no s'ha exercitat. No s'ha
pogut determinar en lectura si aquest 1 és el que va sobreviure a alguna cosa o l'únic que s'ha
creat mai (no hi ha auditoria de fila esborrada).

---

## 5 · LA PREGUNTA P7 — on pot viure «a quin element va cada POM»

### 5.a · El terreny existent: què hi ha i què hi cap

He censat `GarmentTypeItem._meta.related_objects` (mètode demanat, **no** `information_schema`):

```
pom.GarmentPOMMap              via=garment_type_item   on_delete=CASCADE   db_constraint=False  accessor=pom_maps
pom.ItemBaseSet                via=garment_type_item   on_delete=CASCADE   db_constraint=False  accessor=base_sets
pom.ItemBaseMeasurement        via=garment_type_item   on_delete=CASCADE   db_constraint=False  accessor=base_measurements
pom.GradingRuleSet             via=garment_type_item   on_delete=SET_NULL  db_constraint=False  accessor=container_rule_sets
pom.RuleSetScopeNode           via=garment_type_item   on_delete=CASCADE   db_constraint=False  accessor=scope_nodes
models_app.Model               via=garment_type_item   on_delete=SET_NULL  db_constraint=True   accessor=models
models_app.ItemFitxer          via=garment_type_item   on_delete=CASCADE   db_constraint=True   accessor=fitxers
models_app.ImportSession       via=tipologia_confirmada on_delete=SET_NULL db_constraint=True   accessor=importsession_set
tasks.GarmentTypeItemPart      via=set_item            on_delete=CASCADE   db_constraint=True   accessor=parts
tasks.GarmentTypeItemPart      via=part_item           on_delete=PROTECT   db_constraint=True   accessor=part_of
tasks.TaskTimeEstimate         via=garment_type_item   on_delete=CASCADE   db_constraint=True   accessor=time_estimates
commerce.ProductPriceGTI       via=garment_type_item   on_delete=CASCADE   db_constraint=True   accessor=product_price_exceptions
patterns.PatternFile           via=garment_type_item   on_delete=CASCADE   db_constraint=True   accessor=pattern_files
```

### 5.b · 🔑 EL DESCOBRIMENT: **ja existeix un mecanisme d'«item que sembra 2+ peces»** — i està BUIT

`backend/fhort/tasks/models.py:428-430` i `:483-544`.

```python
    # SET-1 (2026-07-27) — el GTI declara PEÇA o CONJUNT. Decisió 3 del sprint: el DEFECTE és
    # NO SET i no hi ha cap backfill possible ni necessari (0 files de GarmentSet als dos
    # esquemes). La composició viu a `GarmentTypeItemPart` (related_name='parts').
    is_set = models.BooleanField(
        default=False,
        help_text="Aquest item és un CONJUNT: la seva composició viu a GarmentTypeItemPart.")
```

```python
class GarmentTypeItemPart(models.Model):
    """Composició d'un ITEM-CONJUNT: quines peces el formen i en quin ordre (SET-1).

    Decisió 3 del sprint SET (2026-07-27): **el GTI declara PEÇA o SET**. Un item amb
    `is_set=True` porta N files aquí; cadascuna diu quin ALTRE item és la peça (`part_item`),
    quina posició ocupa (`ordre` → 01/02/03) i com se'n diu la peça al conjunt (`nom_peca`).

    Per què una taula pròpia i no un M2M nu a `self`: la taula automàtica de Django no admet
    columnes extra, i la creació multi-peça necessita exactament les dues que hi falten
    (`ordre` i `nom_peca`). Amb un `through=` per portar-les, el M2M ÉS aquesta taula.

    `part_item` és PROTECT: esborrar un item que forma part d'un conjunt ha de BLOQUEJAR, no
    deixar el conjunt coix en silenci. `set_item` és CASCADE: si el conjunt desapareix, la
    seva composició no té cap sentit propi.
    """
    set_item = models.ForeignKey(
        GarmentTypeItem, on_delete=models.CASCADE, related_name='parts',
        help_text="L'item CONJUNT (el que té is_set=True).")
    part_item = models.ForeignKey(
        GarmentTypeItem, on_delete=models.PROTECT, related_name='part_of',
        help_text="L'item que fa de PEÇA dins el conjunt.")
    ordre = models.PositiveSmallIntegerField(
        default=0, help_text='Posició de la peça al conjunt (dona el sufix -01/-02/-03).')
    nom_peca = models.CharField(
        max_length=120, blank=True, default='',
        help_text='Nom de la peça dins el conjunt (ex: «Top», «Bikini bottom»).')

    class Meta:
        ordering = ['set_item', 'ordre', 'id']
        unique_together = [('set_item', 'part_item')]
        verbose_name = 'Peça d\'un item-conjunt'
        verbose_name_plural = 'Peces dels items-conjunt'
```

**Recompte per schema (SQL directe):**

| schema | `tasks_garmenttypeitempart` | `GarmentTypeItem` amb `is_set=True` |
|---|---|---|
| `public` | **NO EXISTEIX** (`tasks` és tenant-only) | — |
| `fhort` | **0** | **0** |
| `los` | **0** | **0** |

**Aquest és el terreny que P7 ha de decidir abans de res:** el sistema ja té una resposta
declarada a «un item que és més d'una peça», del 27/07, **amb zero adopció**. La pregunta real
de P7 no és només «on va el mapa POM→element», sinó **si «element» és el mateix que «part» o
una cosa nova**. Són semànticament diferents:

- **`GarmentTypeItemPart`**: la peça **ÉS un altre `GarmentTypeItem`** amb catàleg propi.
  Un bikini = top (item) + bottom (item). Cada peça ja té el seu `GarmentPOMMap`, el seu
  `ItemBaseSet` i el seu ruleset. **No cal cap taula POM→element**: el POM ja penja de l'item-peça.
- **«element sembrat dins del model»** (el brief): la peça **no és un item de catàleg**, és una
  entitat del model. Aquí sí que cal dir a quin element va cada POM, perquè tots els POMs
  pengen d'un **sol** `GarmentPOMMap`.

⚠️ **`GarmentTypeItemPart` prohibeix els sets de sets** (`clean()`, `tasks/models.py:525-533`).
Si «element» s'implementés com a part, un conjunt no podria tenir un element compost. Cal dir-ho.

### 5.c · Taules existents: on **PODRIA** viure i on **NO**

| Taula | Podria allotjar-ho? | Per què |
|---|---|---|
| **`GarmentPOMMap`** (`pom/models.py:809`) | ❌ **No, i és la temptació** | Afegir-hi `element` (FK nullable) col·lisiona frontalment amb la **decisió d'U2 escrita a `models.py:891-893`**: a Postgres «els NULL no comparen iguals», i l'`unique_together ('garment_type_item','pom','capa','instancia')` **deixaria de protegir** les files amb element. A més són **1.748 files vives** i, per la memòria d'U2, **103 lectors**. La decisió d'ahir mateix va escollir taules germanes exactament per no fer això. |
| **`_POMMapBase`** (`pom/models.py:907`) | ⚠️ **Base sí, camp no** | És abstracta i no declara cap FK: és el **motlle** correcte per a una germana nova. Però **afegir-hi `element`** contaminaria `GarmentTypePOMMap` i `GarmentGroupPOMMap`, on «element» no vol dir res (un grup no té peces). |
| **`GarmentTypePOMMap` / `GarmentGroupPOMMap`** | ❌ No | Les seves àncores són família i grup — nivells **per sobre** de l'item. Un element viu **per sota**. Posar-hi element invertiria la jerarquia d'`acumulacio.py:21-25`. |
| **`ItemBaseSet`** (`pom/models.py:975`) | ❌ No | El seu eix és **el MÓN** `(item, size_system, fit_type)`, amb dues `UniqueConstraint` que ho segellen. Afegir `element` a la clau multiplicaria els sets per element i trencaria `resolve_item_base_set()` (`models.py:1119-1140`), que és un **lookup directe de 3 camps** i que 4 camins de producció criden (`models_app/views.py:1362`, `:4295`, `pom/views.py:567`). A més la llei del BaseSet diu literalment «**L'item MAI es parteix**» (`models.py:978-982`). |
| **`ItemBaseMeasurement`** (`pom/models.py:1171`) | ❌ No | Porta el **VALOR**, no la pertinença. Si l'element visqués aquí, un item podria tenir la pertinença sense saber de quin element és fins que algú hi posés un número. |
| **`GarmentTypeItemPart`** (`tasks/models.py:483`) | ⚠️ **Podria, amb un canvi de semàntica** | Ja té `ordre` + `nom_peca` + `unique_together ('set_item','part_item')`. Però `part_item` és **NOT NULL i apunta a un altre GTI**: per fer d'element «lleuger» caldria fer-lo nullable → i tornem al problema del NULL a l'unique. També viu a **`tasks`, app tenant-only**, mentre que tot el catàleg POM viu a **`pom`, SHARED**: una FK `pom → tasks` obliga a `db_constraint=False` (patró `GarmentPOMMap`/`ItemBaseSet`). |
| **`models_app.BaseMeasurement`** | ❌ No | És la **instància al model**, no la plantilla. La sembra (`models_app/views.py:1412-1456`) hi copia des de `GarmentPOMMap`; l'element hauria d'arribar-hi ja resolt, no néixer-hi. |
| **`capa` / `instancia` de `_POMMapBase`** | ❌ **No, però és la trampa més fàcil** | `instancia` és un slug lliure (`max_length=60`) i seria temptador escriure-hi `'top'`/`'bottom'`. **No**: `instancia` significa «el mateix POM DUES VEGADES dins la mateixa capa» (sisa dreta/esquerra, `models.py:841-849`), i `capa` significa «de quina matèria» (exterior/folre). Són **dos eixos ortogonals a l'element**. Col·lapsar-los faria que un mateix POM al top i al bottom fos indistingible d'un POM esquerre i un de dret, i **trencaria `_clau()`** (`acumulacio.py:28-30`) de manera invisible. |

### 5.d · La conseqüència que P7 no pot ignorar: **`_clau()` ha de créixer**

`acumulacio.py:28-30` defineix la identitat com `(pom_id, capa, instancia)`. Si un item sembra
2+ elements i cada element reclama el mateix POM (un bikini que vol «amplada de cintura» al top
i al bottom), **les dues files col·lapsarien en una** al `per_clau` i la segona sobreescriuria la
primera **en silenci** — sense error, sense `tambe_a` útil, amb el recompte mentint.

Qualsevol taula d'elements obliga a `_clau()` a passar a `(element_id, pom_id, capa, instancia)`
i a `_fila()` a portar `element`. **Aquest és el veritable cost de P7, i no és a la BD: és a
`acumulacio.py`.** Els nivells grup/família no tenen element → hi anirien amb `element=None`,
que és precisament el que els fa acumulables sobre tots els elements de l'item.

### 5.e · PROPOSTA (TEXT, no codi) — la forma d'una taula germana

> ⚠️ **AIXÒ ÉS UNA PROPOSTA DINS L'INFORME.** No s'ha creat, no s'ha escrit a `models.py`,
> no s'ha generat cap migració. És text per a la decisió d'Agus.

Fan falta **DUES** peces, no una: el catàleg d'elements (què sembra l'item) i el mapa POM→element.

#### Peça 1 — la declaració d'elements de l'item

Dues vies possibles, i **cal que Agus triï**:

- **Via A — reutilitzar `GarmentTypeItemPart`** (0 files, 0 items `is_set`, per tant reutilitzable
  sense migració de dades). Costos: `part_item` hauria de fer-se nullable (→ problema del NULL a
  l'unique), i cauria el guard anti-set-de-sets.
- **Via B — una taula pròpia `GarmentTypeItemElement`**, que és la que proposo, perquè manté
  `GarmentTypeItemPart` intacte per al seu significat (conjunt de items de catàleg) i no obre
  cap NULL a cap clau.

```python
# ─────────── PROPOSTA · NO IMPLEMENTAT ───────────
class GarmentTypeItemElement(models.Model):
    """Els ELEMENTS que un item sembra al model. Catàleg pur, germà d'`ItemBaseSet`.

    Un item pot sembrar 2+ elements (top + bottom d'un bikini, jaqueta + pantaló d'un vestit)
    SENSE partir-se: la llei del BaseSet («l'item MAI es parteix», pom/models.py:978) es manté,
    perquè l'element NO és un altre item de catàleg — és una peça DINS d'aquest item.

    Diferència amb `tasks.GarmentTypeItemPart` (SET-1, 2026-07-27): allà la peça ÉS un altre
    `GarmentTypeItem` amb catàleg propi; aquí l'element no té catàleg propi i hereta el de l'item.
    Les dues poden conviure; són preguntes diferents.

    Viu a `pom` (SHARED) i no a `tasks` perquè el consumidor és el catàleg de POMs, que és
    SHARED — mateix motiu que `GarmentPOMMap` i `ItemBaseSet`, i per tant mateix `db_constraint=False`.
    """
    garment_type_item = models.ForeignKey(
        'tasks.GarmentTypeItem', on_delete=models.CASCADE,
        related_name='elements', db_constraint=False,
        help_text="L'item que sembra aquest element.")
    codi = models.SlugField(
        max_length=40,
        help_text="Slug estable de l'element dins l'item (p.ex. 'top', 'bottom'). Per SLUG, "
                  "mai per PK (llei G9): és el que la sembra item→model copia.")
    nom = models.CharField(max_length=120, blank=True, default='')
    ordre = models.PositiveSmallIntegerField(
        default=0, help_text="Posició de l'element dins l'item (dona el sufix -01/-02/-03).")
    actiu = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Element sembrat d'un item"
        verbose_name_plural = "Elements sembrats dels items"
        ordering = ['garment_type_item', 'ordre', 'codi']
        # NOT NULL a les dues columnes → l'unique protegeix de debò (la lliçó de U2,
        # pom/models.py:891-893: a Postgres els NULL no comparen iguals).
        constraints = [
            models.UniqueConstraint(fields=['garment_type_item', 'codi'],
                                    name='uniq_gtielement_item_codi'),
        ]

    def __str__(self):
        return f'{self.garment_type_item_id}/{self.codi}'
```

#### Peça 2 — la germana de `_POMMapBase` que respon «a quin element va cada POM»

```python
# ─────────── PROPOSTA · NO IMPLEMENTAT ───────────
class GarmentElementPOMMap(_POMMapBase):
    """POMs que aporta un ELEMENT concret d'un item. El nivell MÉS específic de l'acumulació.

    Quarta germana del patró `_POMMapBase` (U2, 2026-08-07): mateixos camps compartits, la seva
    pròpia àncora, la seva pròpia clau. Segueix les tres raons de la decisió d'U2 al peu de la
    lletra —taula pròpia i no columna nullable a `GarmentPOMMap`—, i per les mateixes tres:

      1. Un `element` nullable a `GarmentPOMMap` deixaria l'`unique_together` existent
         `('garment_type_item','pom','capa','instancia')` SENSE protegir les files amb element,
         perquè a Postgres els NULL no comparen iguals. És exactament el que U2 va rebutjar.
      2. El «Ve de» de la pantalla ha de dir de quin element arriba cada POM: amb taula pròpia
         la resposta és la taula; amb columna nullable es respondria per absència.
      3. Risc zero per a les 1.748 files vives de `GarmentPOMMap` i els seus lectors, que no
         s'assabenten que aquesta existeix.

    ⚠️ NO hereta `pom` de la base: `_POMMapBase` no declara cap FK (pom/models.py:907-935);
    cada filla declara la seva àncora I el seu `pom`.
    """

    element = models.ForeignKey(
        'pom.GarmentTypeItemElement', on_delete=models.CASCADE, related_name='pom_maps',
        help_text="L'element de l'item que reclama aquest POM.")
    pom = models.ForeignKey(POMMaster, on_delete=models.PROTECT,
                            related_name='garment_element_maps')

    class Meta:
        verbose_name = 'Mapa element ↔ POM'
        verbose_name_plural = 'Mapes element ↔ POM'
        ordering = ['element', 'ordre']
        # La MATEIXA forma de clau que les tres germanes: àncora + pom + capa + instància.
        # Totes NOT NULL → el constraint protegeix de debò.
        unique_together = [('element', 'pom', 'capa', 'instancia')]

    def __str__(self):
        return f'{self.element.codi} · {self.pom.codi_client}'
```

**Per què `on_delete` així:**
- `element` → **CASCADE**: igual que `garment_type`/`garment_group` a les germanes d'U2. Sense
  element, la seva pertinença no té sentit propi.
- `pom` → **PROTECT**: idèntic a les tres germanes. És el que fa que el cens de
  `cataleg_views.py:_cens_relacions` (`cataleg_views.py:37`, que recorre
  `POMMaster._meta.related_objects`) **la vegi sola** i la compti com a **bloquejant** d'esborrat.
  Aquesta és la lliçó TGIRL i s'hereta gratis.
- `garment_type_item` (a la peça 1) → **CASCADE + `db_constraint=False`**: mateix patró que
  `GarmentPOMMap` (`models.py:816-818`) i `ItemBaseSet` (`models.py:1007-1008`), perquè `pom` és
  SHARED (taula també a `public`) i `tasks` és tenant-only.

#### El que la proposta OBLIGA a tocar (i que no és cap taula)

1. **`acumulacio.py:28-30`** — `_clau()` ha de passar a `(element_id, pom_id, capa, instancia)`,
   amb `element_id=None` per als nivells grup/família/item, que no en tenen. Sense això, dos
   elements que reclamin el mateix POM col·lapsen en silenci (§5.d).
2. **`acumulacio.py:21-25`** — `NIVELLS` ha de créixer amb `NIVELL_ELEMENT = 'element'` al final
   (és el més específic), i `trams` amb el seu `append` **després** del d'item.
3. **`acumulacio.py:33-49`** — `_fila()` ha de portar `element` i `element_codi` a la resposta.
4. **`models_app/views.py:1412-1456`** (`materialize_poms_view`) — la sembra item→model copia
   des de `GarmentPOMMap` amb clau `(pom, capa, instancia)`; si els elements arriben, o bé el
   `BaseMeasurement` guanya un eix d'element, o bé la sembra ha d'aplanar-los — i **aplanar-los
   és perdre la informació**. 🚩 **Aquesta és la decisió d'arquitectura oberta que P7 destapa i
   que aquest informe NO pot tancar en lectura.**
5. **`cataleg_views.py:99-100`** (`_us_observat`) — hauria d'incloure el nou queryset.
   `_tres_comptadors` (`:63-79`) hauria de guanyar `elements`.

---

## 6 · Recompte de files per schema

**Consultat:** SQL directe amb `SET search_path TO <schema>` per taula
(justificació: aquí la pregunta és «existeix la taula i quantes files té», no «quines relacions
hi ha» — els censos de RELACIONS sí que han anat per `_meta.related_objects`, §5.a).

### 6.a · Les dues germanes d'U2

| schema | `pom_garmenttypepommap` | `pom_garmentgrouppommap` |
|---|---|---|
| `public` | **NO EXISTEIX** | **NO EXISTEIX** |
| `fhort` | **NO EXISTEIX** | **NO EXISTEIX** |
| `los` | **NO EXISTEIX** | **NO EXISTEIX** |

🚨 **No és 0: és que la taula no hi és.** La migració `0073_u2_acumulacio_poms` està al disc i
**no s'ha aplicat enlloc** (§ titular). La distinció importa exactament pel que demanava el brief:
un **0** en una taula de catàleg seria informatiu («el catàleg no s'ha poblat»); un **«no existeix»**
és una altra cosa i molt més forta — **el codi d'U2 no pot córrer**. La cautela del wipe de models
del 06/08 aquí no aplica: aquestes són taules de catàleg, cap wipe de `models_app` les tocaria.

### 6.b · Context — les taules veïnes, per poder llegir el 0

| taula | `public` | `fhort` | `los` |
|---|---|---|---|
| `pom_garmentpommap` (nivell ITEM, la vella) | 0 | **1.748** | 0 |
| `pom_itembaseset` | 0 | **1** | 0 |
| `pom_garmenttype` (famílies) | 0 | **21** | 1 |
| `pom_garmentgroup` (grups) | **8** | **12** | 1 |
| `pom_pommaster` | 0 | **396** | 0 |
| `tasks_garmenttypeitem` | NO EXISTEIX (app tenant-only) | **62** | 1 |
| `tasks_garmenttypeitempart` | NO EXISTEIX | **0** | **0** |
| `GarmentTypeItem` amb `is_set=True` | — | **0** | **0** |

**Com llegir-ho:**
- **`public` té 8 `GarmentGroup` i 0 de tota la resta.** El vocabulari de grups és el que la
  migració `0072_cat22_sembra_garmentgroup` hi va sembrar (app SHARED). Els grups de `fhort` (12)
  són els seus propis. `pom` és SHARED+TENANT: **les dues còpies conviuen** i cap lectura pot
  ometre de quin schema surt.
- **`los` és pràcticament buit** (1 família, 1 grup, 1 item, 0 POMMaster, 0 GarmentPOMMap).
  Coherent amb la memòria «`los` sense POMMaster» (`ftt-federacio-patro-c-retorn`).
- **`fhort` viu**: 1.748 pertinences d'item, 396 POMs, 62 items. **El wipe del 06/08 va matar
  models, no catàleg** — i això queda confirmat aquí.
- **`GarmentTypeItemPart` = 0 a tot arreu i `is_set=True` = 0 a tot arreu**: el mecanisme
  multi-peça del 27/07 **mai s'ha fet servir**. És terreny lliure per a P7 (§5.b).

---

## 7 · Què NO s'ha pogut determinar en lectura

1. **Si `acumula_poms_de_item()` funciona.** No es pot verificar: les seves taules no existeixen a
   cap schema. Els 10 tests de `test_u2_acumulacio.py` no s'han corregut (i, per la memòria
   `ftt-cataleg-talles-c1c6`, «`… | tail` es menja el codi de sortida de la suite» — o sigui que
   un «va bé» d'una correguda anterior no seria de fiar). **La lògica està llegida i és coherent;
   la seva execució no està verificada.**
2. **Quantes famílies de `fhort` tenen `grup_ref = NULL`** i, per tant, saltarien el nivell grup
   en silenci (`acumulacio.py:67`). No comptat: no formava part del brief i el pas 2 de C6 està
   obert. **És una comprovació d'una línia que val la pena abans de desplegar U2.**
3. **Què és exactament l'únic `ItemBaseSet` de `fhort`** (a quin item, quin món). No inspeccionat.
4. **Si «element» ha de ser el mateix concepte que `GarmentTypeItemPart`.** És una **decisió
   d'Agus**, no una lectura. Aquest informe presenta les dues semàntiques (§5.b) i proposa la
   Via B, però no la pot tancar.
5. **Com la sembra item→model transportaria l'element.** `materialize_poms_view`
   (`models_app/views.py:1295-1460`) escriu `BaseMeasurement` amb clau `(model, pom, capa,
   instancia)`. **No hi ha cap eix d'element al costat del model.** Si l'element ha de sobreviure
   la sembra, `models_app.BaseMeasurement` necessita alguna cosa que avui no té — i determinar
   QUÈ està fora de l'abast d'una lectura del catàleg. 🚩 **És el bloquejant real de P7.**
6. **Els «103 lectors de `GarmentPOMMap`»** que cita la decisió d'U2 (`models.py:897`) no s'han
   recensat. El grep d'avui en troba ~25 referències de producció (§3, taula d'indirectes); la
   xifra 103 ve d'un cens anterior amb un criteri que desconec. **No la contradic; no la confirmo.**
7. **Recompte a PROD.** Sense SSH a PROD (memòria `ftt-prod-estat-via-dump`). Tots els números
   d'aquest informe són de **staging**.
