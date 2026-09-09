# A · CATÀLEG A LA BD — terreny (A1, A2, A4)

> **MODE LECTURA PURA.** Cap escriptura, cap migració, cap `--apply`. Tot per
> `./venv/bin/python manage.py shell -c` i SQL de consulta.
> Data: 2026-08-07 · staging `/var/www/ftt-staging/backend` · branca `dev` (HEAD net).

---

## 0 · Marc: quins schemas i què hi viu

`fhort.pom` és a **SHARED_APPS i a TENANT_APPS alhora**
(`backend/fhort/settings.py:36-76`), o sigui que **totes** les taules `pom_*` existeixen
físicament als tres schemas. Verificat a `information_schema.tables`:

| taula | public | fhort | los |
|---|---|---|---|
| `pom_pommaster` | existeix | existeix | existeix |
| `pom_customerpomalias` | existeix | existeix | existeix |
| `pom_measurementinstance` | existeix | existeix | existeix |
| `pom_garmenttypepommap` | **NO EXISTEIX** | **NO EXISTEIX** | **NO EXISTEIX** |
| `pom_garmentgrouppommap` | **NO EXISTEIX** | **NO EXISTEIX** | **NO EXISTEIX** |

Schemas presents a la BD: `public`, `fhort`, `los` (cap més).

### 🚨 Troballa transversal: la migració `0073` NO està aplicada

`./venv/bin/python manage.py showmigrations pom` (l'última línia):

```
 [X] 0072_cat22_sembra_garmentgroup
 [ ] 0073_u2_acumulacio_poms
```

Conseqüència directa: els models `GarmentTypePOMMap` i `GarmentGroupPOMMap`
(`fhort/pom/models.py:938` i `:957`) **estan declarats al codi però no tenen taula a cap
schema**. Als CSV d'A1 les seves columnes surten com a `ERR` — no és un zero, és
«la taula no hi és».

---

## A1 · Bolcat complet de `POMMaster`

### A1.0 — Definició LITERAL de `POMMaster` (`backend/fhort/pom/models.py:379-451`)

```python
class POMMaster(models.Model):
    pom_global = models.ForeignKey(
        POMGlobal,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='masters',
    )
    categoria = models.ForeignKey(
        POMCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='poms',
    )
    codi_client = models.CharField(max_length=30)
    nom_client = models.CharField(max_length=200)
    notes = models.TextField(blank=True)
    actiu = models.BooleanField(default=True)

    # Sprint 5B.1: standard tolerance for this catalogue POM (asymmetric).
    # Copied onto BaseMeasurement.tolerancia_minus/plus when measurements are poured
    # into a model (copy-at-the-moment, like base_value_cm — not a live reference).
    tolerancia_default_minus = models.DecimalField(max_digits=5, decimal_places=2, default=0.6)
    tolerancia_default_plus = models.DecimalField(max_digits=5, decimal_places=2, default=0.6)
    pendent_revisio = models.BooleanField(
        default=False,
        verbose_name='Pendent de revisió',
        help_text="POM creat automàticament des d'importació. Requereix revisió de la patronista.",
    )
    origen_import = models.CharField(
        max_length=200,
        blank=True,
        default='',
        verbose_name='Origen importació',
        help_text="Referència del model/fitxa des d'on s'ha creat aquest POM",
    )

    class Meta:
        verbose_name = 'POM (tenant)'
        verbose_name_plural = 'POMs (tenant)'

    def __str__(self):
        return f'{self.codi_client} · {self.nom_client}'

    # ── Alias properties for the sprint3/4 code ────────────────────────────
    # Resolve TECH_DEBT.md #2. Read-only — they do not work in the ORM (.filter/order_by).
    # For the ORM, use the natural FKs: pom__categoria__display_order, pom__pom_global__nom_ca.
    @property
    def pom_code(self):
        return self.codi_client or (self.pom_global.codi if self.pom_global_id else '')

    @property
    def name_cat(self):
        if self.pom_global_id and self.pom_global.nom_ca:
            return self.pom_global.nom_ca
        return self.nom_client

    @property
    def name_en(self):
        if self.pom_global_id and self.pom_global.nom_en:
            return self.pom_global.nom_en
        return self.nom_client

    @property
    def display_order(self):
        return self.categoria.display_order if self.categoria_id else 999

    @property
    def is_key_measure(self):
        # We have no equivalent field in the current schema. If we needed to
        # distinguish "key measures", add an explicit BooleanField to the model (migration).
        return False
```

**Camps de nom que existeixen de debò:** **només `nom_client`**. `POMMaster` **NO té
`nom_fitxa`** (aquell camp viu a `models_app.BaseMeasurement`, és del MODEL, no del catàleg)
ni `nom_en`/`nom_ca`/`nom_es`. Els noms multilingües només arriben per la FK
`pom_global` → `POMGlobal.nom_en/nom_ca/nom_es` (`models.py:33-35`), i **122 de 396 files a
`fhort` tenen `pom_global` NULL**, o sigui que per a aquelles el nom multilingüe no existeix.

**Família/categoria:** dues fonts, cap d'elles obligatòria:
- `categoria` → `POMCategory` (`models.py:359-376`: `codi`, `nom_en`, `nom_ca`, `body_area`,
  `display_order`). **219 de 396 la tenen NULL.**
- `pom_global.categoria` (CharField lliure, `models.py:36`).

Al CSV hi van totes dues, desdoblades.

### A1.1 — Cens de relacions entrants (via `POMMaster._meta.related_objects`, MAI `information_schema`)

16 models apunten a `POMMaster`. `on_delete` i `db_constraint` literals:

| model fill | camp | `on_delete` | `db_constraint` | accessor |
|---|---|---|---|---|
| `pom.POMEstadisticaTenant` | `pom` | CASCADE | True | `estadistiques` |
| `pom.CustomerPOMAlias` | `pom` | **CASCADE** | True | `client_aliases` |
| `pom.GarmentPOMMap` | `pom` | PROTECT | True | `garment_maps` |
| `pom.GarmentTypePOMMap` | `pom` | PROTECT | True | `garment_type_maps` — **taula inexistent (0073)** |
| `pom.GarmentGroupPOMMap` | `pom` | PROTECT | True | `garment_group_maps` — **taula inexistent (0073)** |
| `pom.ItemBaseMeasurement` | `pom` | PROTECT | True | `item_base_measurements` |
| `pom.GradingRule` | `pom` | PROTECT | True | `regles_grading` |
| `pom.ClientMesuraPerfil` | `pom` | PROTECT | True | `mesures_perfil` |
| `models_app.BaseMeasurement` | `pom` | PROTECT | True | `base_measurements` |
| `models_app.MeasurementChangeLog` | `pom` | PROTECT | True | `measurement_changes` |
| `models_app.ModelGradingOverride` | `pom` | PROTECT | True | `model_grading_overrides` |
| `models_app.ModelGradingRule` | `pom` | PROTECT | **False** | `model_grading_rules` |
| `models_app.POMPlacement` | `pom` | PROTECT | True | `placements` |
| `fitting.POMAlert` | `pom` | PROTECT | True | `alerts` |
| `fitting.GradedSpec` | `pom` | PROTECT | True | `graded_specs` |
| `patterns.PatternPOM` | `pom_master` | PROTECT | True | `pattern_poms` |

Notes:
- **`ModelGradingRule` és l'única amb `db_constraint=False`**: no sortiria mai a
  `information_schema` (per això el mètode és `related_objects`).
- **`CustomerPOMAlias` és l'única CASCADE cap avall des del catàleg** (a part de
  `POMEstadisticaTenant`): esborrar un POMMaster s'emporta els àlies del client.
  Tota la resta és PROTECT.
- Els models de `models_app`, `fitting` i `patterns` són **tenant-only** → les seves
  taules **no existeixen a `public`** (verificat: `relation "models_app_basemeasurement"
  does not exist`). Al CSV de `public` aquestes columnes van a `ERR`.

### A1.2 — Recompte total per schema

| schema | files a `POMMaster` |
|---|---|
| `public` | **0** |
| `fhort` | **396** |
| `los` | **0** |

Confirmat per ORM (`connection.set_schema(...)`) **i** per SQL cru
(`select count(*) from "<schema>".pom_pommaster`), amb el mateix resultat.

**`los` no té CAP POMMaster ni CAP CustomerPOMAlias.** El catàleg del client LOSAN viu
íntegrament dins de `fhort` (v. A2: `customer_id=6` `LOS`, 240 àlies).

### A1.3 — Total de relacions vives, per schema

| relació | public | fhort | los |
|---|---|---|---|
| `POMEstadisticaTenant` | 0 | 0 | 0 |
| `CustomerPOMAlias` | 0 | **390** | 0 |
| `GarmentPOMMap` | 0 | **1 748** | 0 |
| `GarmentTypePOMMap` | ERR (taula inexistent) | ERR | ERR |
| `GarmentGroupPOMMap` | ERR (taula inexistent) | ERR | ERR |
| `ItemBaseMeasurement` | 0 | **37** | 0 |
| `GradingRule` | 0 | **1 267** | 0 |
| `ClientMesuraPerfil` | 0 | **20** | 0 |
| `BaseMeasurement` | ERR (tenant-only) | 0 | 0 |
| `MeasurementChangeLog` | ERR | 0 | 0 |
| `ModelGradingOverride` | ERR | 0 | 0 |
| `ModelGradingRule` | ERR | 0 | 0 |
| `POMPlacement` | ERR | **2** | 0 |
| `POMAlert` | ERR | 0 | 0 |
| `GradedSpec` | ERR | 0 | 0 |
| `PatternPOM` | ERR | 0 | 0 |

⚠️ Els zeros de `models_app`/`fitting` a `fhort` **no volen dir res**: són conseqüència del
wipe del 06/08 (0 models de peça). Les 1 267 `GradingRule` i les 1 748 `GarmentPOMMap`
són catàleg i van sobreviure.

### A1.4 — CSVs generats

| fitxer | files |
|---|---|
| `/var/www/ftt-staging/A1_pommaster_public.csv` | 0 (només capçalera) |
| `/var/www/ftt-staging/A1_pommaster_fhort.csv` | **396** |
| `/var/www/ftt-staging/A1_pommaster_los.csv` | 0 (només capçalera) |

Capçalera (idèntica als tres):

```
schema,pk,codi_client,nom_client,pom_global_codi,pom_global_nom_en,pom_global_categoria,
categoria_codi,categoria_nom_ca,categoria_body_area,actiu,pendent_revisio,origen_import,
tolerancia_default_minus,tolerancia_default_plus,notes,
n_POMEstadisticaTenant,n_CustomerPOMAlias,n_GarmentPOMMap,n_GarmentTypePOMMap,
n_GarmentGroupPOMMap,n_ItemBaseMeasurement,n_GradingRule,n_ClientMesuraPerfil,
n_BaseMeasurement,n_MeasurementChangeLog,n_ModelGradingOverride,n_ModelGradingRule,
n_POMPlacement,n_POMAlert,n_GradedSpec,n_PatternPOM,ORFE_sense_alias
```

`ERR` en una columna `n_*` = la taula no existeix en aquell schema (no és zero).

### A1.5 — 🚨 ORFES: 106, no 93 (i el 93 s'explica)

POMs de `fhort` **sense cap `CustomerPOMAlias`**:

| tall | recompte |
|---|---|
| **ORFES totals** | **106** |
| ...dels quals `actiu=True` | **93** ← el número de la sessió anterior |
| ...dels quals `actiu=False` | 13 |
| ORFES amb `pendent_revisio=True` | 29 |
| ORFES amb `pendent_revisio=False` | 77 |
| ORFES amb `origen_import` buit | 76 |
| ORFES amb `origen_import` informat | 30 |
| ORFES amb `pom_global` NULL | 31 |
| ORFES amb `categoria` NULL | 16 |
| **ORFES sense CAP relacio viva** (0 maps, 0 grading, 0 base sets) | **37** |

**La cifra 93 de la sessió del 06/08 és el subconjunt `actiu=True`.** El cens complet
(incloent-hi els 13 desactivats) és 106. No hi ha hagut creixement de 93→106: són dos
talls diferents del mateix conjunt.

Estat global del catàleg de `fhort` (396 files):

| tall | recompte |
|---|---|
| `pendent_revisio=True` | **254** (64 %) |
| `actiu=False` | 16 |
| `pom_global` NULL (sense ancoratge al catàleg global) | **122** |
| `categoria` NULL | **219** (55 %) |

La llista nominal dels 106 orfes és al CSV (`ORFE_sense_alias=True`). Mostra dels casos
que criden l'atenció:

- `codi_client='0'` (pk 506, «Back opening length») — un codi que és literalment el caràcter zero.
- **Codis de client duplicats amb POMs diferents**: `D` apareix dos cops (pk 436
  «1/2 bottom width relaxed» i pk 528 «HIP WIDTH»), `H` dos cops (pk 423, pk 551).
  **`POMMaster` no té cap unicitat sobre `codi_client`** (v. `Meta` a `models.py:417-419`:
  no hi ha `unique_together` ni `constraints`).
- POMs nascuts dels diccionaris LOS/BRW (`origen_import='diccionari:LOS:2026-07-18'`,
  `'diccionari:BRW:2026-07-13'`) que després no van rebre àlies: `A2`, `B1`, `B2`, `D`, `H`,
  `H11`, `IC`, `JJ`, `SR9`.
- POMs amb sufix de model (`-M76`, `-M79`): `1-M76`, `D1-M76`, `F1-M76`, `T.1-M79`, `T.2-M79`,
  `G1-M76`, `LF-M76` — nascuts de fitxes concretes (`origen_import='Olivia Dress
  (REPRIS-26-SS-0001)'`, `'SS26 TROUSERS TWILL (14-26-SS-0002)'`).
- POMs amb `origen_import` = UUID cru (`030e788a-…`, `d4f50ff5-…`, `4e79eb3f-…`,
  `98444d69-…`, `28fb6e93-…`, `fd5a41ee-…`, `6de5fe49-…`): no es pot saber en lectura de
  quina fitxa venen sense creuar amb una taula d'items/fitxers.

### A1.6 — Què NO he pogut determinar

- **Quantes de les 1 748 `GarmentPOMMap` són de POMs orfes** està al CSV per fila, però no
  he fet el pivot invers (quins items reclamen POMs sense àlies) — no era la pregunta.
- **Els UUID d'`origen_import`** no els he resolt a una fitxa concreta (caldria creuar amb
  `tasks`/`models_app`, i `fhort` té 0 models de peça).
- **Res de PROD**: aquesta lectura és de STAGING. No he tocat cap dump.

---

## A2 · `CustomerPOMAlias` — definició literal

### A2.0 — El model SENCER (`backend/fhort/pom/models.py:471-553`)

```python
class CustomerPOMAlias(models.Model):
    """Àlies de NOMENCLATURA per client (N1, DIAGNOSI_NOMENCLATURA_ALIES_2026-07-08): separa
    "com anomena un client una mesura" (client_code/client_description) del catàleg canònic
    (POMMaster). Un client pot tenir DIVERSOS codis per al mateix POM (p.ex. Losan H.11 sleeve
    opening vs H.16 cuff opening) → unicitat (customer, client_code), NO (customer, pom).
    El matcher el consumeix com a estratègia (a) prioritària de find_pom_master (N3 fet,
    models_app/extraction_views.py:543)."""
    # `MODEL` (06/08) — l'àlies neix perquè un model necessitava una mesura que el catàleg del
    # client no tenia, i algú la va crear des del cercador de Definició POM («Crear POM propi del
    # model»). NO és un àlies de menys categoria: entra a l'espai de nomenclatura del client com
    # qualsevol altre, la validació de col·lisió el veu, i un altre model del mateix client el pot
    # reutilitzar pel cercador. Això és coneixement del client acumulant-se, que és el que ha de
    # passar (decisió d'Agus, 06/08).
    #
    # El que marca és la PROVINENÇA: d'on va sortir aquest codi. Serveix per saber què s'ha
    # d'ensenyar al diccionari com a pendent de consolidar i què ve d'un document oficial.
    ORIGEN_CHOICES = [
        ('IMPORT', 'Import'), ('MANUAL', 'Manual'), ('MIGRACIO', 'Migració'),
        ('DICCIONARI', 'Diccionari'), ('MODEL', 'Nascut d\'un model'),
    ]
    # db_constraint=False: `pom` és SHARED+TENANT però `tasks.Customer` és tenant-only → la FK
    # creua schemas (mateix patró que GarmentPOMMap). PROTECT a nivell ORM, sense constraint de BD.
    customer = models.ForeignKey(
        'tasks.Customer', on_delete=models.PROTECT, related_name='pom_aliases',
        db_constraint=False)
    # NULLABLE (QA-S8-R1): un àlies SENSE pom és vocabulari del client encara PENDENT DE MAPAR.
    # És un estat legítim del domini, no una dada incompleta: el client anomena una mesura i
    # encara no sabem a quin POM canònic correspon (o el mapatge que teníem era FALS i s'ha
    # desvinculat). El matcher no els mira (find_pom_master filtra `pom__isnull=False`): un
    # àlies sense destí no pot vincular res. (Migració 0037.)
    pom = models.ForeignKey(
        POMMaster, on_delete=models.CASCADE, related_name='client_aliases',
        null=True, blank=True)
    client_code = models.CharField(max_length=60)
    # OBSOLET (TODO): camp de descripció únic heretat. Substituït per description_en +
    # description_local. Es manté la columna (migració 0035 hi va bolcar el contingut propi
    # cap a description_en); no s'esborra per no perdre històric. No escriure-hi de nou.
    client_description = models.CharField(max_length=200, blank=True, default='')
    # Diccionari del client (carregat al setup): descripció canònica internacional (EN) +
    # descripció en l'idioma local de l'empresa. Ambdues alimenten find_pom_master com a
    # senyal de matching addicional. `language` = ISO 639-1 del camp local.
    description_en = models.CharField(max_length=200, blank=True, default='')
    description_local = models.CharField(max_length=200, blank=True, default='')
    language = models.CharField(max_length=2, blank=True, default='')
    origen = models.CharField(max_length=10, choices=ORIGEN_CHOICES, default='MANUAL')
    pendent_revisio = models.BooleanField(default=False)
    # F3/D-31.26 — ÀLIES D'INSTÀNCIA: aquest codi del client no és una mesura pròpia, és una
    # REPETICIÓ de la del `pom`. El doc oficial de Brownie declara A2/A3 variants de la mateixa
    # fila que A: no són tres amplades de pit, són l'amplada de pit dita tres vegades.
    #
    # Sense aquesta marca els dos casos són indistingibles per al matcher —un codi que resol a
    # un POM— i acabaria vinculant A2 al pit i donant la feina per feta. El que ha de passar és
    # l'altra cosa: resol el POM i DEIXA LA FILA A «assignar instància», perquè QUINA cara és
    # (la 2a? la de l'esquerra? l'estirada?) no ho diu el codi, ho diu qui mesura. Auto-triar-la
    # seria inventar-se una dada que el document no porta.
    #
    # ⚠️ AQUÍ NOMÉS HI HA LA DADA, NO LA REGLA. El comportament del matcher és el full MATCHER i
    # s'implementa al seu lloc; aquesta columna és el que llegirà quan hi sigui.
    #
    # Deliberadament NO desa QUINA instància és (ni l'ordinal «2a/3a» ni l'eix). Desar-ho seria
    # exactament l'auto-tria que la regla prohibeix, i el `nom_fitxa` del model ja és el lloc on
    # viu la resposta un cop una persona l'ha donada.
    es_instancia = models.BooleanField(
        default=False,
        help_text="Aquest codi és una REPETICIÓ del POM apuntat, no una mesura pròpia. "
                  "El matcher hi resol el POM però deixa la fila a «assignar instància».")
    creat_at = models.DateTimeField(auto_now_add=True)
    actualitzat_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Àlies POM de client'
        verbose_name_plural = 'Àlies POM de client'
        constraints = [
            models.UniqueConstraint(
                fields=['customer', 'client_code'], name='uniq_customer_client_code'),
        ]
        indexes = [
            models.Index(fields=['customer', 'client_code'], name='idx_customer_client_code'),
        ]

    def __str__(self):
        desti = self.pom.codi_client if self.pom_id else '(pendent de mapar)'
        return f'{self.customer.codi}:{self.client_code} → {desti}'
```

### A2.1 — LA PREGUNTA: ¿existeix CAP camp que proposi capa, instància o terna?

## **NO.**

**Prova — llista EXHAUSTIVA dels camps** (obtinguda de `CustomerPOMAlias._meta.get_fields()`,
no de la lectura del fitxer):

| # | camp | tipus |
|---|---|---|
| 1 | `id` | BigAutoField |
| 2 | `customer` | ForeignKey → `tasks.Customer` |
| 3 | `pom` | ForeignKey → `pom.POMMaster` |
| 4 | `client_code` | CharField(60) |
| 5 | `client_description` | CharField(200) — OBSOLET |
| 6 | `description_en` | CharField(200) |
| 7 | `description_local` | CharField(200) |
| 8 | `language` | CharField(2) |
| 9 | `origen` | CharField(10, choices) |
| 10 | `pendent_revisio` | BooleanField |
| 11 | `es_instancia` | BooleanField |
| 12 | `creat_at` | DateTimeField |
| 13 | `actualitzat_at` | DateTimeField |

**Tretze camps. Cap JSONField, cap `meta`, cap `default_*`, cap `sugerencia`, cap
`capa`, cap `instancia`, cap terna.** No hi ha cap FK ni M2M cap a `MeasurementLayer` ni
cap a `MeasurementInstance`.

L'únic camp que **toca** el tema és `es_instancia` (BooleanField), i **és deliberadament un
booleà i no un punter**. El comentari del codi ho declara com a decisió, no com a oblit
(`models.py:530-532`):

> «Deliberadament NO desa QUINA instància és (ni l'ordinal «2a/3a» ni l'eix). Desar-ho seria
> exactament l'auto-tria que la regla prohibeix, i el `nom_fitxa` del model ja és el lloc on
> viu la resposta un cop una persona l'ha donada.»

**Choices d'`origen`** (`models.py:487-490`), literals:
`IMPORT` · `MANUAL` · `MIGRACIO` · `DICCIONARI` · `MODEL`.

**Constraints**: una sola — `UniqueConstraint(fields=['customer','client_code'],
name='uniq_customer_client_code')`. Un índex: `idx_customer_client_code` sobre els mateixos
dos camps. **La unicitat és per (client, codi), NO per (client, POM)**: un client pot tenir
diversos codis apuntant al mateix POM (és precisament el cas dels `es_instancia`).

### A2.2 — `es_instancia`: qui l'omple i on

**Un únic escriptor a tot el codi** (grep `es_instancia` a `fhort/**/*.py`, exclosos
migracions i tests):

- **`backend/fhort/pom/management/commands/seed_brownie_germans.py:129`** →
  `'es_instancia': True` dins d'un `update_or_create`.
  Capçalera del fitxer (`:6`): «`CustomerPOMAlias` del germà cap al POM BASE, marcat
  `es_instancia=True`».
- **Cap serializer l'exposa**: `CustomerPOMAliasSerializer.Meta.fields`
  (`backend/fhort/pom/serializers.py:632-646`) **no inclou `es_instancia`**. O sigui que
  per l'API no s'hi pot escriure.
- Declaració: `backend/fhort/pom/models.py:533`.

**Files que l'omplen (`es_instancia=True`):**

| schema | files |
|---|---|
| `public` | 0 |
| `fhort` | **16** (totes de BRW) |
| `los` | 0 |

Les 16, literals (client · codi → POM base · origen):

```
BRW A2   -> CH        DICCIONARI
BRW A3   -> CH        DICCIONARI
BRW B1   -> WA        DICCIONARI   (description_en = "STRETCHED WAIST WIDTH")
BRW B3   -> WA        DICCIONARI
BRW B4   -> WA        DICCIONARI
BRW B5   -> WA        DICCIONARI
BRW B6   -> WA        DICCIONARI
BRW JTL  -> JTA       DICCIONARI
BRW R4   -> PKT W     DICCIONARI
BRW R5   -> O.21-M79  DICCIONARI
BRW R6   -> PKT W     DICCIONARI
BRW R7   -> O.21-M79  DICCIONARI
BRW TR1  -> TR        DICCIONARI
BRW UT2  -> UT1       DICCIONARI
BRW V1   -> V         DICCIONARI
BRW V2   -> V         DICCIONARI
```

**LOS té ZERO àlies marcats com a instància.** Cap dels 240 àlies de LOSAN porta
`es_instancia=True`.

### A2.3 — Recomptes d'àlies per customer i per schema

| schema | total |
|---|---|
| `public` | **0** |
| `fhort` | **390** |
| `los` | **0** |

Desglossat a `fhort` (els `Customer` viuen a `tasks`, tenant-only, dins de `fhort`):

| customer_id | codi | nom | àlies |
|---|---|---|---|
| 6 | `LOS` | LOSAN IBERIA SA | **240** |
| 7 | `BRW` | Textiles y Confecciones Brownie SL | **148** |
| 1 | `FTT` | FHORT Textile Tech | **2** |

Per `origen` (a `fhort`):

| origen | files |
|---|---|
| `DICCIONARI` | **337** |
| `IMPORT` | 48 |
| `MODEL` | 3 |
| `MIGRACIO` | 2 |
| `MANUAL` | **0** |

Altres talls a `fhort`:
- `pom` NULL («vocabulari pendent de mapar»): **0** — tots els 390 àlies tenen destí.
- `pendent_revisio=True`: **29**
- `es_instancia=True`: **16**

### A2.4 — Què NO he pogut determinar

- **Per què `MANUAL` té 0 files** tot i ser el `default` del camp: en lectura no es pot
  saber si mai s'ha creat un àlies per la via manual o si tots els creats així es van
  reescriure a `DICCIONARI`.
- **Quin codi escriu `origen='MODEL'`** (3 files): no ho he censat, no era la pregunta.
- **La regla del matcher sobre `es_instancia`** no està implementada enlloc (el propi
  comentari del model ho diu: «AQUÍ NOMÉS HI HA LA DADA, NO LA REGLA»). No he verificat
  si `find_pom_master` ja la mira.

---

## A4 · `MeasurementInstance` — estat exacte

### A4.0 — Definició literal (`backend/fhort/pom/models.py:245-334`), part declarativa

```python
class MeasurementInstance(models.Model):
    ORIGEN_SEED = 'SEED'
    ORIGEN_MANUAL = 'MANUAL'
    ORIGEN_IMPORT = 'IMPORT'
    ORIGEN_CHOICES = [
        (ORIGEN_SEED, 'Sembra'),
        (ORIGEN_MANUAL, 'Manual'),
        (ORIGEN_IMPORT, 'Importació'),
    ]

    #: ON es mesura (lateralitat, vora, costura de referència).
    EIX_POSICIO = 'POSICIO'
    #: COM es mesura (amb tensió o sense).
    EIX_ESTAT = 'ESTAT'
    EIX_CHOICES = [
        (EIX_POSICIO, 'Posició'),
        (EIX_ESTAT, 'Estat'),
    ]
    #: EL NOM DE L'EIX, trilingüe, per a qui n'ha de pintar una COLUMNA (D-31.18: la taula de
    #: mesures té un grup de columnes per eix). Viu aquí, al costat de `EIX_CHOICES`, perquè
    #: l'eix es DEFINEIX aquí i no té fila pròpia a cap taula: és el discriminant de les que hi
    #: ha. Que el front se'ls escrigui seria el segon lloc que sap quins eixos hi ha, i el dia
    #: que se n'afegís un tercer la columna nova sortiria sense nom.
    EIX_NOMS = {
        EIX_POSICIO: {'nom_en': 'Position', 'nom_ca': 'Posició', 'nom_es': 'Posición'},
        EIX_ESTAT: {'nom_en': 'State', 'nom_ca': 'Estat', 'nom_es': 'Estado'},
    }

    #: La instància ÚNICA: cadena buida, no una fila d'aquesta taula. Una mesura que només
    #: es fa un cop no té res a qualificar (v. `sufixIdentitat`, que hi torna `''`).
    SLUG_UNICA = ''

    slug = models.SlugField(max_length=30, unique=True)
    nom_en = models.CharField(max_length=120)
    nom_ca = models.CharField(max_length=120)
    nom_es = models.CharField(max_length=120)
    eix = models.CharField(max_length=8, choices=EIX_CHOICES, db_index=True)
    #: Sufix que s'enganxa al codi base per PROPOSAR el codi de la germana (B→BT). Buit a
    #: l'eix ESTAT per decisió, i buit també a `waistband_seam`, que és un DATUM: es diu a la
    #: descripció, no al codi (full INSTANCIES, decisió Agus 05/08).
    sufix = models.CharField(max_length=4, blank=True, default='')
    #: Propietat de la casa: no s'esborra (mateix guard que `MeasurementLayer.is_system`).
    is_system = models.BooleanField(default=False)
    #: Instància nascuda al tenant i encara no promoguda a canònica.
    pendent_revisio = models.BooleanField(default=False)
    origen = models.CharField(max_length=10, choices=ORIGEN_CHOICES, default='MANUAL')
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = 'Instància de mesura'
        verbose_name_plural = 'Instàncies de mesura'
        ordering = ['eix', 'display_order', 'slug']
```

⚠️ **`waistband_seam` JA ESTÀ ANOTAT COM A DATUM AL CODI** —`models.py:318-319`: «buit també
a `waistband_seam`, que és un DATUM: es diu a la descripció, no al codi (full INSTANCIES,
decisió Agus 05/08)»— però viu a l'eix `POSICIO`. El comentari ja anticipa el moviment.

### A4.1 — Files actuals, per eix i per schema

**Contingut IDÈNTIC als tres schemas** (10 files cadascun; la sembra és `update_or_create`
sobre `public` + tots els tenants):

| schema | POSICIO | ESTAT | total |
|---|---|---|---|
| `public` | 8 | 2 | **10** |
| `fhort` | 8 | 2 | **10** |
| `los` | 8 | 2 | **10** |

Les 10 files, literals (iguals als tres schemas):

| eix | slug | sufix | is_system | pendent_revisio | origen | ordre | en / ca / es |
|---|---|---|---|---|---|---|---|
| POSICIO | `left` | `L` | True | False | SEED | 1 | Left / Esquerra / Izquierda |
| POSICIO | `right` | `R` | True | False | SEED | 2 | Right / Dreta / Derecha |
| POSICIO | `top` | `T` | True | False | SEED | 3 | Top / Superior / Superior |
| POSICIO | `bottom` | `B` | True | False | SEED | 4 | Bottom / Inferior / Inferior |
| POSICIO | `cf` | `CF` | True | False | SEED | 5 | CF / CF / CF |
| POSICIO | `cb` | `CB` | True | False | SEED | 6 | CB / CB / CB |
| POSICIO | `side` | `S` | True | False | SEED | 7 | Side seam / Costura lateral / Costura lateral |
| POSICIO | `waistband_seam` | *(buit)* | True | False | SEED | 8 | Waistband seam / Costura de cinturilla / Costura de pretina |
| ESTAT | `relaxed` | *(buit)* | True | False | SEED | 1 | Relaxed / Relaxada / Relajada |
| ESTAT | `extended` | *(buit)* | True | False | SEED | 2 | Extended / Estirada / Estirada |

**Cap fila `is_system=False`, cap `pendent_revisio=True`, cap origen ≠ `SEED`** a cap schema.

### A4.2 — 🚨 CAP CONSUMIDOR: totes les columnes `instancia` són `''` als tres schemas

Recompte de valors distints a totes les taules amb columna `instancia`:

| taula | public | fhort | los |
|---|---|---|---|
| `pom_garmentpommap` | buida | `('', 1748)` | buida |
| `pom_itembasemeasurement` | buida | `('', 37)` | buida |
| `models_app_basemeasurement` | (taula inexistent) | buida | buida |
| `models_app_pomplacement` | (taula inexistent) | `('', 2)` | buida |

**Zero files a tot staging fan servir cap slug d'instància.** El vocabulari està sembrat
i publicat però encara no l'ha escrit ningú. Això és el terreny més important d'A4: el cost
de dades de qualsevol moviment de vocabulari és, avui, **zero files a migrar**.

Constraints vives que toquen `instancia` (idèntiques als tres schemas):
- `models_app_basemeasurement_instancia_exigeix_nom`:
  `CHECK ((NOT (((instancia)::text > ''::text) AND ((nom_fitxa)::text = ''::text))))`
  — tota germana ha de portar nom.
- `uniq_pomplacement_item_pom_view_capa_instancia`: `UNIQUE (item_fitxer_id, pom_id,
  view_slot, capa, instancia)`.
- La resta són `NOT NULL instancia` a 9 taules.
- **Les comportes CHECK que només deixaven passar `''` JA NO HI SÓN** (retirades per
  `pom/0057_c4_g4_retira_comportes`, aplicada). No hi ha res que bloquegi escriure un
  slug d'instància.

**Cap CHECK valida el contingut d'`instancia` contra el catàleg.** Un slug inexistent
entraria sense queixa.

### A4.3 — ¿Afegir OPCIONS és dada pura?

**Gairebé, però NO del tot: no hi ha cap camí d'escriptura per API.**

- L'endpoint de vocabulari és **read-only**: `GET /api/v1/mesures/diccionari/`
  (`backend/fhort/pom/urls.py:110-112` → `identity_views.measurement_identity_vocabulary_view`,
  `backend/fhort/pom/identity_views.py:55`). La capçalera del fitxer ho declara:
  «Lectura pura: cap escriptura, cap efecte» (`identity_views.py:26`).
- **No hi ha `MeasurementInstanceSerializer` ni cap ViewSet** (grep a `pom/serializers.py`
  i `pom/views.py`: cap ocurrència).
- L'únic camí d'entrada de files és la comanda de sembra:
  **`backend/fhort/pom/management/commands/seed_measurement_instances.py`**, amb les llistes
  **hardcodejades**:
  - `POSICIONS` → **línies 37-49**
  - `ESTATS` → **línies 51-63**
  - `INSTANCIES = [(I.EIX_POSICIO, POSICIONS), (I.EIX_ESTAT, ESTATS)]` → **línia 66**

**Veredicte:** afegir una opció **no toca cap esquema ni cap migració** (és una fila més a
una taula existent), però **sí toca codi**: cal editar la llista del fitxer de sembra i
tornar a executar-la (és idempotent, `update_or_create`, mai esborra). Es podria fer
directament per SQL/shell, però llavors la propera passada de la sembra **no** l'esborraria
(només toca les `is_system`), de manera que quedaria fora del fitxer que la casa considera
font. Hi ha, a més, un **mirall al front** que cal mantenir (v. A4.5).

### A4.4 — ¿Afegir un EIX toca `EIX_CHOICES`? — SÍ. Fitxer:línia exactes

| què | fitxer:línia |
|---|---|
| **`EIX_CHOICES`** | `backend/fhort/pom/models.py:294-297` |
| `EIX_POSICIO = 'POSICIO'` | `backend/fhort/pom/models.py:291` |
| `EIX_ESTAT = 'ESTAT'` | `backend/fhort/pom/models.py:293` |
| **`EIX_NOMS`** (noms trilingües de la columna) | `backend/fhort/pom/models.py:303-306` |
| camp `eix = models.CharField(max_length=8, choices=EIX_CHOICES, db_index=True)` | `backend/fhort/pom/models.py:316` |

**Cost tècnic d'afegir `DATUM`:**
- `max_length=8` de `eix` → `'DATUM'` (5 car.) **hi cap**: cap `AlterField` per llargada.
- Tocar `choices` **sí que genera una migració** de Django (`AlterField`), però és una
  **migració NOOP a la BD**: Postgres no materialitza els `choices` (no hi ha CHECK; només
  hi ha el `NOT NULL` i l'índex). O sigui: migració obligatòria per la mecànica de Django,
  cost zero a la BD.
- Afegir l'entrada a `EIX_NOMS` és imprescindible o **la columna nova sortiria sense
  capçalera** — està escrit al mateix comentari del codi (`models.py:298-302`) i al de
  `identity_views.py:65-70`.
- `identity_views.py:81-85` construeix `eixos` iterant `EIX_CHOICES` i filtrant els buits →
  **es propaga sol**, no cal tocar-lo.
- `seed_measurement_instances.py:66` (`INSTANCIES`) i `:124-130` (el missatge final, que
  indexa `per_eix[I.EIX_POSICIO]` i `per_eix[I.EIX_ESTAT]` **hardcodejats**) sí que
  s'han de tocar.

### A4.5 — On és el codi que composa el sufix de la instància

**La REGLA la publica el backend com a DADA; la COMPOSICIÓ la fa el frontend.**

| peça | fitxer:línia |
|---|---|
| **Emissió de la regla** (`sufix_separador:''`, `sufix_ordre:'base+sufix'`, `capa_al_codi:false`, `instancia_separador:'-'`) | `backend/fhort/pom/identity_views.py:91-105` |
| Emissió del `sufix` per fila | `backend/fhort/pom/identity_views.py:78` |
| **`codiProposat(dicc, base, trams)`** — la composició real `base+sufix` | `frontend/src/utils/diccionariMesures.js:128-134` |
| `codiBase(dicc, codi, trams)` — desfà el sufix per re-partir | `frontend/src/utils/diccionariMesures.js:144-156` |
| `composaInstancia(dicc, trams)` — compon el SLUG (`left-relaxed`) | `frontend/src/utils/diccionariMesures.js:108-115` |
| `tramsInstancia` / `sepInst` — el desmunta pels guions | `frontend/src/utils/diccionariMesures.js:96-101` |
| `eixPrincipal(dicc)` — quin eix es «gira» en partir un POM | `frontend/src/utils/diccionariMesures.js:63` |
| `dimensionsDe(dicc)` — un grup de columnes per eix | `frontend/src/utils/diccionariMesures.js:43-54` |
| **`COMPLEMENTARIA`** — parelles hardcodejades al front | `frontend/src/utils/diccionariMesures.js:25-30` |
| **Únic consumidor (tot el gest d'escriptura)** | `frontend/src/components/EditableTable/EditableTable.jsx:166, 317, 502, 506, 521, 610-611, 1436-1458` |
| Mirall de lectura (literals abans que arribi el GET) | `frontend/src/utils/capaInstancia.js:55` (`NOM_INSTANCIA`), `:67` (`INSTANCIES`) |
| Sufixos a la sembra (font) | `backend/fhort/pom/management/commands/seed_measurement_instances.py:37-63` |

### A4.6 — 🚨 Dues coses que la lectura ha destapat i que afecten el cost d'afegir un eix

**(1) `composaInstancia` NO usa l'ordre d'eixos declarat — usa l'ordre alfabètic dels slugs d'eix.**

`frontend/src/utils/diccionariMesures.js:109`:

```js
const eixos = Object.keys(dicc?.instancies || {})
```

Però el backend construeix `instancies` amb
`MeasurementInstance.objects.all().order_by('eix', ...)` (`identity_views.py:75`), i
`'ESTAT' < 'POSICIO'` alfabèticament. Verificat contra la BD viva:

```
ORDRE de les claus de `instancies` (JSON): ['ESTAT', 'POSICIO']
ORDRE de `eixos` (EIX_CHOICES):            ['POSICIO', 'ESTAT']
```

Les dues llistes del mateix payload van en **ordre invers**. `dimensionsDe`/`eixPrincipal`
llegeixen `dicc.eixos` (ordre bo: POSICIO primer); `composaInstancia` llegeix
`Object.keys(dicc.instancies)` (ordre ESTAT primer) → **compondria `relaxed-left` i no
`left-relaxed`**, que és exactament el que el seu propi docstring (`:102-107`) diu que no
ha de passar. Avui no ha fet mal perquè **cap fila té instància** (A4.2), però queda armat.
Amb un eix `DATUM` la barreja canvia (`'DATUM' < 'ESTAT' < 'POSICIO'`).

**(2) `eixPrincipal` és «el primer eix declarat», i és el que es gira en partir un POM.**

`diccionariMesures.js:59-63` — el comentari ho diu explícitament: era el literal `'POSICIO'`
i ara es dedueix de l'ordre. **Si `DATUM` s'insereix davant de `POSICIO` a `EIX_CHOICES`,
el gest de «partir un POM» passa a girar el DATUM** en comptes de la lateralitat, sense que
res més canviï. La posició del nou eix dins de `EIX_CHOICES` és, doncs, una decisió de
comportament, no d'ordre visual.

### A4.7 — Dimensionament, cru (sense recomanació)

| acció | dades | codi backend | migració | codi frontend |
|---|---|---|---|---|
| Afegir ~10 opcions a un eix existent | 10 files noves (`update_or_create`) | `seed_measurement_instances.py:37-63` | **cap** | `capaInstancia.js:55` (mirall de literals) |
| Afegir l'eix `DATUM` | — | `models.py:294-297` + `:303-306`; `seed_...py:66` i `:124-130` | **AlterField(choices)** — noop a BD, `max_length=8` ja hi cap | cap fitxer *obligat* (`dimensionsDe` és genèric), però v. A4.6: `composaInstancia` i `eixPrincipal` canvien de comportament |
| Moure `waistband_seam` POSICIO→DATUM | **0 files a migrar** a tot staging (A4.2) | `seed_...py:48` (moure la tupla de `POSICIONS` a la nova llista) + una data-migration si es vol garantir-ho sense re-sembra | cap d'esquema | cap (`NOM_INSTANCIA` ja el porta i no diu de quin eix és) |

Detalls que condicionen:
- `slug` és **`unique=True` a tota la taula, no per eix** (`models.py:312`). Un slug de
  `DATUM` no pot repetir cap dels 10 existents.
- `sufix` és `max_length=4` (`models.py:320`). Els sufixos de DATUM, si en porten, hi han
  de cabre. `waistband_seam` avui té sufix buit (per la decisió d'Agus del 05/08).
- La columna `instancia` és `max_length=60` a **totes** les taules consumidores. Amb un
  tercer eix els slugs compostos passen a tenir fins a 3 trams
  (`waistband_seam-left-relaxed` = 28 car.) — hi cap, però el marge es redueix.
- Moure `waistband_seam` d'eix **no és una migració d'esquema**: és un `UPDATE` d'una fila
  per schema (×3), o una re-sembra.

### A4.8 — Què NO he pogut determinar en lectura

- **Si el catàleg v4 vol que `DATUM` sigui el primer eix o l'últim.** És una decisió d'Agus
  i té conseqüència de comportament (A4.6 punt 2).
- **Els ~10 valors del nou eix DATUM**: no són enlloc del codi ni de la BD. Vindran del
  full INSTANCIES de `docs/BROWNIE_CATALEG_POM_v3.xlsx`, que no he obert.
- **Si `find_pom_master` ja mira `es_instancia`** i quin gest deixaria la fila a «assignar
  instància»: el propi model diu que la regla no està implementada.
- **PROD**: tot això és staging. No he mirat cap dump de producció.

---

## Resum de banderes

1. 🚨 **`pom/0073_u2_acumulacio_poms` NO aplicada** — `GarmentTypePOMMap` i
   `GarmentGroupPOMMap` són models sense taula a cap schema.
2. 🚨 **106 POMs orfes a `fhort`** (93 si només es compten els `actiu=True` — d'aquí el
   número de la sessió anterior). 37 no tenen **cap** relació viva.
3. 🚨 **254 de 396 POMs (64 %) estan `pendent_revisio=True`**; 122 sense `pom_global`;
   219 sense `categoria`.
4. 🚨 **`POMMaster` no té cap unicitat sobre `codi_client`**: `D` i `H` estan duplicats a
   `fhort` amb POMs semànticament diferents.
5. 🚨 **`composaInstancia` (front) ordena els trams per l'ordre alfabètic dels eixos, no
   pel declarat** — armat, inert avui perquè cap fila té instància.
6. 🔵 **`los` no té CAP POMMaster ni CAP àlies**: tot el catàleg del client LOSAN viu dins
   de `fhort` com a `Customer` `LOS`.
7. 🔵 **Zero files fan servir cap slug d'instància a tot staging**: el vocabulari està
   sembrat i publicat, però encara no l'escriu ningú. Les comportes CHECK ja no hi són.
8. 🔵 **No hi ha camí d'escriptura per API per a `MeasurementInstance`**: només la comanda
   de sembra, amb les llistes hardcodejades.
