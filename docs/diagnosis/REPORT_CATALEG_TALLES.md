# REPORT · CATÀLEG DE TALLES (C1–C6) — 2026-08-07

> Sessió d'implementació sobre staging `dev`. **Cap push.** Commits locals 93→99.
> Ordre respectat: s'ha esperat el restart de M-FI (05:36:03) abans de tocar la BD.
> Referències: `REPORT_NIT_CAPES.md` §7.1/§7.4 · `DIAGNOSI_VOCABULARIS.md` §T3 i §2.6.

---

## 0 · EL TITULAR, EN QUATRE FRASES

1. **C1, C2, C4-parcial, C5 i C6-pas-1 tancats i verificats contra la BD.** El catàleg de
   talles ja no menteix: 0 conflictes de `base_unit`, 0 `ordre` duplicats i una constraint que
   ho manté així.
2. 🚨 **C3 ha caigut a mitges, i la troballa val més que la feina**: `TGIRL-EU-HEIGHT` NO
   s'esborra. El cens de la nit el donava per «risc zero» perquè va mirar el lloc equivocat.
3. 🛑 **C6 s'atura al pas 1, exactament com el brief manava**, per una dada concreta del
   tenant `los`.
4. 🚩 **Dos guards i tres valors esperen la teva paraula** (i la de la Montse). Estan tots
   marcats amb 🚩 i cap d'ells bloqueja res del que ja corre.

---

## 1 · C1 · TODDLER_EU  ✅  (commit `ea855527`)

Tres defectes alhora, en un run del catàleg `public` i per tant present a **dos** schemes
(`public.8` i `fhort.36`; a `los` no hi és — el brief en deia tres, en són dos).

**La decisió de mètode que ha evitat un desastre:** la reparació la manen les DADES, no el
schema. A `public` la sèrie de contorns és coherent (waist 26·28·30·32·34) i a `fhort` no
(53·54·55·56·57 i després un 34). **Una escriptura cega dels valors de `fhort` hauria
corromput `public`.** Cada defecte es detecta abans de tocar-lo, i per això el resultat és
asimètric a posta:

| | `public.8` | `fhort.36` |
|---|---|---|
| `base_unit` | `AGE_YEARS` → **`CM_HEIGHT`** | `AGE_YEARS` → **`CM_HEIGHT`** |
| `ordre` | ja era 1..5 → intacte | 86 i 92 empatats a 1 → **1..6 per alçada** |
| talla 116 | sèrie monòtona → **intacte** | **reparada** (sota) |

### 🚩 EL VALOR TRIAT, per validar (Agus · Montse)

La talla 116 de `fhort` portava `waist=34 / hip=40` enmig d'una sèrie que va de 53 a 57 i de
55 a 65. **Són exactament els valors de la fila homòloga de `public`**: aquella fila no es va
actualitzar mai quan la resta del run es va tornar a mesurar.

⚠️ **És una EXTRAPOLACIÓ, no una interpolació.** 116 és l'última talla i no té veïna per
sobre; el brief deia «interpolació de les veïnes» i això aquí no es pot fer. El criteri
aplicat és **continuar el pas local** (l'últim tram real de cada columna):

| columna | 86 | 92 | 98 | 104 | 110 | **116 (abans)** | **116 (ara)** | pas aplicat |
|---|---|---|---|---|---|---|---|---|
| `body_waist_cm` | 53 | 54 | 55 | 56 | 57 | ~~34~~ | **58** | +1 |
| `body_hip_cm` | 55 | 58 | 61 | 63 | 65 | ~~40~~ | **67** | +2 |

🚩 **I una tercera columna de la mateixa fila que NO s'ha tocat:** `body_bust_cm = 60`, quan
la sèrie fa 53·55·57·59·61 i a 116 li tocaria **63**. Amb 60 la sèrie **baixa** de 110 a 116,
que és tan impossible com el waist — però el brief només autoritzava waist i hip, i canviar-la
pel meu compte hauria estat inventar-me domini. **És una paraula teva**: si dius que sí, és
una línia.

---

## 2 · C2 · BABY_MONTHS  ✅  (commit `0c793378`)

`BABY_MONTHS` portava **dos jocs dins d'un**: el PUNTUAL (NB·0M·1M·3M…) i un de RANGS
(0M-1M·1M-3M…) que és còpia exacta de `BABY_MONTHS_COM`. Els `ordre` es trepitjaven 1..5, i
**això és el que fa mal: un run desordenat és un grading incorrecte** (el motor compta per
posició).

- **Es queda el PUNTUAL.** Les 5 files de rang no s'han migrat enlloc: ja existeixen,
  idèntiques i amb els mesos ben posats, a `BABY_MONTHS_COM` **del mateix schema** — i la
  migració ho comprova abans d'esborrar res, més les 3 FK entrants de `SizeDefinition` a zero
  (`ItemBaseSet`, `GradingRule.talla_base`, `GarmentTypeItem`). Totes 0.
- **Mesurat:** `fhort` 14 talles → **9** · `public` 9 → 9 (allà no hi havia files de rang;
  només calien els mesos) · `los`, res.

### 🚩 Els mesos, i el que espera validació

Estaven desplaçats **dues posicions** (`24M` deia 96-144 mesos). El criteri no me l'he
inventat: és **la convenció que la casa ja fa servir a `BABY_MONTHS_COM`** — l'etiqueta és el
mes d'INICI i el final és l'inici de la següent talla.

`NB 0-1 · 0M 0-1 · 1M 1-3 · 3M 3-6 · 6M 6-9 · 9M 9-12 · 12M 12-18 · 18M 18-24 · **24M 24-30**`

🚩 **L'última no té «següent» de qui sortir.** S'ha aplicat el pas local (24 + 6 = **30**). La
convenció comercial habitual per a 2T seria **24-36**. Trio el valor auditable i t'ho deixo
marcat: si la Montse diu 36, és una línia.

---

## 3 · C3 · DEPURACIÓ  ⚠️  DOS DE TRES  (commit `fef5c95e`)

| run | veredicte |
|---|---|
| `fhort`·26 `MEN-SHIRT-NUM` | ✅ **esborrat** — 0 talles i 0 referències de cap mena |
| `fhort`·53 `WOMAN_BRW_01` | ✅ **esborrat** + el ruleset 124 «Prova BRW ALPHA UE» |
| `fhort`·6 `TGIRL-EU-HEIGHT` | 🚨 **NO s'esborra — ATURAT** |

**fhort: 28 runs → 26.**

### 🚨 Per què s'atura, i per què el cens no ho va veure

El cens de la nit va comptar **les 6 FK que apunten al `SizeSystem`** i va trobar zero. Era
correcte. I era insuficient:

> **L'ús viu d'un run de talles no penja del run. Penja de les seves TALLES.**

`GradingRule.talla_base` és un FK a `SizeDefinition` amb `on_delete=PROTECT`. I
`TGIRL-EU-HEIGHT` —que es diu, literalment, **«Alpha EU — Grading Reference»**— és l'àncora de
talla base de **350 regles repartides en 10 rulesets que són d'ALTRES runs**:

| ruleset | el seu propi `size_system` | regles ancorades aquí |
|---|---|---|
| 91 `EU Woven Woman Numeric` | 32 | 61 |
| 78 `EU Woven Woman Oversized` | (cap) | 61 |
| 77 `EU Woven Woman Relaxed` | (cap) | 61 |
| 80 `EU Knit Woman Slim` | (cap) | 40 |
| 85 `EU Woven Man Slim` | (cap) | 35 |
| 87 `EU Knit Baby Regular` | 35 | 25 |
| 89 `EU Knit Kids Regular` | 37 | 20 |
| 88 `EU Knit Toddler Regular` | 36 | 19 |
| 82 · 92 | (cap) | 19 + 9 |

La BD el va rebutjar. **I aquesta és la part que fa por: si el fill hagués estat `CASCADE` en
comptes de `PROTECT`, l'esborrat s'hauria executat en silenci i s'haurien endut 350 regles.**

🚩 **Decisió teva:** `TGIRL-EU-HEIGHT` no és brossa, és infraestructura de graduació amb un nom
que enganya. Les opcions són (a) deixar-lo i **rebatejar-lo** perquè ningú més el proposi per
esborrar, (b) moure les 350 àncores al canònic que toqui i llavors esborrar-lo. No he fet cap
de les dues.

**El guard ha quedat arreglat per sempre:** la migració ara mira les DUES capes (qui apunta al
run i qui apunta a les seves talles) i pregunta les relacions **als models**, no a
`information_schema` — les FK amb `db_constraint=False` no deixen constraint, i n'hi ha una
d'avui mateix (`derivat_de_rule_set`, de M-FI). Per això depèn de `models_app/0079`: una app
fora de l'estat històric no surt al recompte i el delete semblaria segur.

---

## 4 · C4 · GUARDS DE DISSENY  ⚠️  DOS DE TRES  (commit `d139324d`)

### ✅ §7.4.4 · `SizeDefinition.ordre` únic per run
`unique_together` + el `UniqueTogetherValidator` que DRF en fabrica sol. Depèn de C1 i C2 a
posta: abans hi havia **6 parells duplicats** i la constraint hauria petat la migració.
Verificat a `pg_constraint` als **3 schemes**, i comprovat que mossega (un `INSERT` amb `ordre`
repetit rep `IntegrityError`).

### ✅ §7.4.3 · `base_unit` / `tipus_escala` contrastats amb les etiquetes
N1 va posar l'algorisme i el va fer servir **una** vegada, a la data migration. Faltava la
porta — i per això `TODDLER_EU` havia pogut arribar a dir `AGE_YEARS` amb talles en cm. Ara:
`SizeSystem.clean()` (les dues fonts) + `validate_tipus_escala` al serializer. `base_unit` no
és escrivible per l'API, però `tipus_escala` sí, **i és la mateixa mentida per una altra
porta**. Neix amb el terra net: **0 conflictes als 3 schemes** després de C1.

### 🚩 §7.4.2 · el `unique_together` de `SizingProfile` NO S'HI POT POSAR

La clau natural és `(target, garment_type, construction, fit_type, size_system, customer)`.
A `fhort` la violen **5 files vives en 2 grups**:

| grup | ids | àmbit compartit |
|---|---|---|
| A | **539 · 540 · 541** | target 4 · gt 82 · constr 2 · fit 1 · run 62 · client 6 |
| B | **288 · 510** | target 1 · gt 24 · constr 3 · fit 2 · run 29 · sense client |

⚠️ **El grup B no sortia a la diagnosi** (§7.4.2 només parlava de 539/540/541). El va trobar el
pre-flight. Comparteixen àmbit i només canvien de ruleset.

Afegir la constraint peta la migració, i resoldre-ho vol dir **fusionar o esborrar perfils**:
decisió teva, no d'un agent. Mentrestant el fre viu a `SizingProfile.clean()`, que **bloqueja
els NOUS i deixa en pau els que ja hi són**. La constraint és una línia el dia que ho diguis.

---

## 5 · C5 · EDITOR DE RESTRICCIONS AL RUN  ✅  (commit `b406cdfc`)

Fins ara les 4 capes de N1 només es podien omplir des de la data migration que les va deduir:
un run nou —o un que la deducció no va poder classificar— es quedava **mut per sempre**.

**Zero backend nou.** `SizeSystemViewSet` ja era un `ModelViewSet` amb escriptura gated
CONFIGURE i el serializer ja tenia les 4 llistes escrivibles **per codi**. L'únic que faltava
era la porta del client.

- Vocabulari reutilitzat, cap llista nova: els mateixos chips i claus i18n de N2.
- **Els GRUPS surten de la BD, no de la constant del front**: `fhort` en té 12 (`TOPS-KNIT`,
  `DRESSES-FULL`, `NEWBORN`…) i `gradingAxes.GARMENT_GROUPS` només en declara 7. Editar amb la
  llista curta hauria fet **desaparèixer en silenci** grups que el run ja té. Un codi triat que
  no sigui a la llista viva es conserva igualment.
- Els canònics nous neixen sense restriccions (no es toca cap default).
- i18n: 12 claus × ca/en/es, paritat comprovada. Lint dels 2 fitxers: 0 errors.

### 🚩 Una paraula del brief que he canviat a posta
El brief deia «**buit = serveix a tothom**». Operativament és cert (ningú queda fora), però
dir-ho així contradiu la llei que hi ha escrita al serializer i a N3: **buit no és «universal»,
és «no declarat»**, i el pas 3 ORDENA per proximitat sense amagar res (D-31.3). El text de la
UI diu «*Capa no declarada — no exclou ningú*». Si prefereixes l'altra redacció, és una clau
i18n.

---

## 6 · C6 · `GarmentType.grup` → FK  🛑  PAS 1 FET, PAS 2 ATURAT  (commit `cb938566`)

Decisió 1 de §2.6 aplicada: **l'amo del vocabulari és la BD**. `grup_ref` → FK a
`GarmentGroup`, nullable, backfill **per codi**, idempotent i només-omple.

### Auditoria del backfill (contra `information_schema`, després d'aplicar)

| schema | columnes | `GarmentType` | amb FK | **amb grup i SENSE FK** |
|---|---|---|---|---|
| `public` | `grup` varchar NOT NULL · `grup_ref_id` bigint NULL | 0 | 0 | 0 |
| `fhort` | idem | 21 | **21** | 0 |
| `los` | idem | 1 | 0 | 🚨 **1** |

Repartiment a `fhort`: TOPS 7 · DRESSES 4 · BOTTOMS 3 · UNDERWEAR 2 · OUTERWEAR 2 ·
ACCESSORIES 1 · NEWBORN 1 · SWIMWEAR 1.

### 🛑 Per què el pas 2 no es fa

> El tenant **`los`** té un `GarmentType` (`BUTTONED_TOPS`, grup `'TOPS'`) i la taula
> **`GarmentGroup` BUIDA**. Allà el backfill no té amb què resoldre el codi, i **retirar el
> string perdria l'única informació de grup que existeix en aquell schema**.

El brief deia: *si algun lector no es pot migrar net, ATURA al pas 1 (FK conviu amb string) i
reporta*. Això és. Mentre convisquin, **la font de veritat segueix sent `grup`**: cap lector
canvia, cap contracte d'API es mou, i `GarmentType.save()` manté la FK alineada — una FK que
ningú escriu és pitjor que no tenir-la.

### El cens de lectors, i els tres deutes que el pas 2 haurà de pagar abans

**46 línies de backend + 20 de frontend + 21 entrades JSON.** Migrables netes gairebé totes.
Les que no:

1. 🚩 **`pom/serializers.py:169` · `GarmentTypeSerializer` és `fields = '__all__'`** — l'ÚNIC
   serializer de `GarmentType` del repo. Amb una FK, `grup` sortiria com a **PK int** i
   trencaria el contracte-codi de **tot** el front (`garmentCatalog.js`, `ModelWizard`,
   `GarmentTypes.jsx`, `POMBrowser`). Cal `SlugRelatedField(slug_field='codi')` **abans**.
2. 🚩 **`pom/views.py:127` · `filterset_fields = ['actiu', 'grup']`** — `?grup=TOPS` passaria a
   esperar un id. Cal un FilterSet explícit amb `grup__codi`.
3. 🚩 **Tres tests sembren codis que no existeixen a `GarmentGroup`** i petarien en crear la
   FK: `tasks/tests.py:39` i `patterns/tests.py:901` (`'tops'`, en minúscules) i
   `models_app/test_g1_graduacio.py:72` (`'TOP'`, en singular).
4. ⚠️ **`proximitatRun.js:50,56` falla EN SILENCI** si el contracte canvia: compara el valor de
   `GarmentType.grup` contra `SizeSystem.grup_codis`; si un passa a id, ordena malament i no
   llança res. No hi ha test d'integració que ho detecti.
5. 🔵 `GarmentTypeGlobal.grup` (`pom/models.py:85`) es queda `CharField`: la incoherència serà
   visible i és una decisió a part.

---

## 7 · VERIFICACIÓ

| control | resultat |
|---|---|
| `manage.py check` | ✅ net (0 silenced), a cada pas |
| `migrate_schemas` (mai `--schema`) | ✅ 0064→0068 als 3 schemes |
| auditoria directa a la BD | ✅ feta a cada peça (no em fio del OK de django-tenants) |
| `npm run build` | ✅ `built in 889ms` |
| lint dels fitxers nous | ✅ 0 errors |
| i18n ca/en/es | ✅ paritat verificada |
| fum read-only de N6 | ✅ **VERD** (v. sota) |
| restart de `ftt-staging` | ✅ fet després del bloc backend |

### El fum de N6, re-corregut (commit `091c2bdf`)

Va sortir **vermell**, i era **ell** qui codificava el món vell: exigia 5 runs de referència i
un era `WOMAN_BRW_01`, que C3 ha esborrat per decisió teva. Mateix cas que el M1-bis de M-FI.
La prova **canvia de pregunta** en comptes de baixar el llistó: ara comprova què passa quan un
client **no** té run propi — que l'ordre no s'inventi cap primer lloc i que **no amagui res**.

De passada, el fum ensenya sol els efectes de la nit:

```
N1a · 26 runs · classificats 26 · sense classificar 0 []      ← abans 28 i 1 ['MEN-SHIRT-NUM']
N1b · GET size-systems/ 200 · 26 files · capes exposades OK
N3 · ordre amb client BRW · target WOMAN: ALPHA_EU_W › NUMERIC_EU_W › ALPHA_EU_M › BABY_EU_CM
✅ FUM VERD · cap escriptura feta
```

I la nota groga `TODDLER_EU: base_unit=AGE_YEARS contradiu les etiquetes` **ha desaparegut
sola**: C1 l'ha reparada.

---

## 8 · EL QUE ESPERA LA TEVA PARAULA

| # | on | la pregunta |
|---|---|---|
| 1 | §1 | `body_bust_cm` de la talla 116 (`fhort`): 60 trenca la sèrie i li tocaria **63**. L'apliquem? |
| 2 | §2 | `24M` → **24-30** (pas local) o **24-36** (convenció comercial 2T)? |
| 3 | §3 | 🚨 `TGIRL-EU-HEIGHT`: **rebatejar-lo** (és infraestructura, no brossa) o **moure les 350 àncores** i esborrar-lo? |
| 4 | §4 | Els 5 `SizingProfile` duplicats (539·540·541 i **288·510**): fusionar o esborrar? Sense això no hi pot haver constraint. |
| 5 | §6 | `los` sense `GarmentGroup`: **sembrem-hi el catàleg** o el pas 2 es fa només on es pot? |
| 6 | §5 | La redacció «capa no declarada» vs «serveix a tothom». |

---

## 9 · SORPRESES

1. 🔴 **El cens de la nit mirava el lloc equivocat** per a un dels dos runs «sense risc». La
   lliçó és general i val per a qualsevol esborrat futur: **un guard que mira el node però no
   el que penja dels seus fills dona verd a un esborrat que la BD rebutja** — o l'executa en
   silenci si el fill és CASCADE.
2. 🟡 **La col·lisió de numeració de commits ja és triple.** M-FI i jo hem fet servir el `96`
   tots dos (`d139324d` i `61d4ec67`). Els hashos manen; els números, no.
3. 🔵 **C1 va acabar sent asimètrica per schema, i aquest era el resultat correcte.** Si
   la migració hagués estat «apliquem els valors bons», hauria corromput `public`.
4. 🔵 **Editar una migració ja aplicada, aquesta vegada, era la jugada neta.** La `0066` havia
   entrat a `public` com a **no-op demostrable** (cap dels 3 codis hi existeix, verificat), i
   `fhort`/`los` encara no l'havien vista. Reescriure-la era més honest que apilar-hi una 0069
   correctora.
