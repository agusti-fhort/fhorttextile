# DIAGNOSI — LA SEMBRA DE RETORN (Studio → Brand)

Data: 2026-07-24 · Entorn: STAGING (`dev`) · Tipus: **Patró A, read-only**. Cap canvi de codi.
Context: P7 va donar al Brand la palanca (assignar) i P8 al Studio la safata (traspassar). El
camí d'anada està tancat. **Aquesta diagnosi mira el camí de tornada i no n'implementa res.**

> La pregunta que respon: quan el Studio acaba la feina, **què torna al Brand, com hi arriba, i
> què es trenca pel camí.** Totes les xifres són consultes reals sobre staging.

---

## A9-1 — Què és un LLIURABLE avui

**Espècimen:** `BRW-FW27-0001` (id=268, schema `fhort`) — el model amb més mesura base viva.

```
fase=Dev · estat=Nou · customer=BRW · size_system=ALPHA_EU_W
run='XXS·XS·S·M·L' · base='S' · grading_rule_set='BRW · Blusa · ALPHA_EU_W'

BaseMeasurement      48   (20 amb valor · 28 origen=TEMPLATE, encara buides)
                          origen: TEMPLATE 28 · MANUAL 20
ModelGradingRule     34
SizeFitting           1 → GradingVersion v1 (activa, NO aprovada) → GradedSpec 100
ModelFitxer           2   (TECHSHEET .ftt · v1 556 B obsoleta + v2 19 641 B vigent)
```

**Inventari global de `fhort`:** 1 056 Model (51 EXTERN) · 621 BaseMeasurement · 430
ModelGradingRule · 33 GradingVersion · 1 827 GradedSpec · 480 ModelFitxer.

### La troballa estructural que condiciona TOT el retorn

**`GradedSpec` no penja del Model.** La cadena real és:

```
Model → SizeFitting → GradingVersion → GradedSpec
        (fitting/models.py:62,181)
```

Un `GradedSpec` referencia `grading_version`, i `GradingVersion` referencia `size_fitting` —
mai el model directament. Per tant **sembrar les talles graduades al Brand no és copiar una
taula: és haver de fabricar-hi la cadena sencera** (SizeFitting + GradingVersion + specs), amb
la seva invariant d'"una sola versió vigent per SizeFitting" (constraint R7/G6-B2).

I una segona: `BaseMeasurement.pom` i `GradedSpec.pom` són **FK a `POMMaster` amb PROTECT** —
apunten al catàleg del schema on viuen. Un valor no viatja sol; viatja amb la seva identitat
de POM, que al destí ha de existir. Vegeu A9-4, que és on això peta.

### Què marca "acabat"

No hi ha cap camp `acabat`. Els candidats existents són `fase_actual`
(`Pending→Dev→Proto→SizeSet→PP→TOP`), `estat`, `data_tancament` (avui buit a l'espècimen) i
`GradingVersion.aprovada` (el segell de producció que posa el gate). **Cap d'ells és avui una
declaració de lliurament al Brand** — són l'estat intern del Studio. La sembra de retorn
necessitarà un disparador explícit (proposta 💡3).

---

## A9-2 — Identitat de retorn: matching per `codi_intern`

`Model.codi_intern` és `unique=True` **dins de cada schema** (`models_app/models.py:129`) i
l'EXTERN conserva el codi del Brand (P3). Per tant el matching de retorn és directe:
`codi_intern` al schema del Brand. Cens real:

```
los  : 51 models LOS-*  → 51 INTERN, 0 EXTERN
fhort: 1013 models LOS-* → 962 INTERN, 51 EXTERN

codis presents als DOS schemas: 51
  · EXTERN a fhort (parella de retorn correcta): 51
  · INTERN a fhort (col·lisió real): 0
```

**Avui NO hi ha cap col·lisió.** Però la mina és exactament on el brief apuntava: **962 models
`LOS-SS27-*` viuen a `fhort` com a INTERN** (Bandera 8 de la diagnosi de federació — el
catàleg LOSAN es va sembrar al Studio, no a la Marca). `los` encara no en té cap.

**El dia que `los` sembri el seu SS27 propi** — que és el pla per a PROD — els mateixos
`codi_intern` existiran als dos schemas amb `origen=INTERN` als dos costats, i un retorn que
resolgui per `codi_intern` no sabrà distingir la parella federada d'un homònim natiu.

> 🔴 **La finestra per decidir-ho és ABANS d'aquella sembra, no després.** El discriminant
> ha de ser `origen=EXTERN` **a més** del codi (un retorn només té sentit sobre un model que
> va arribar per federació), i idealment un ancoratge explícit — vegeu 💡1.

---

## A9-3 — Media cross-schema

Ja està resolt a nivell d'infraestructura, i el propi `settings.py` explica per què (`:174-195`):

```python
MULTITENANT_RELATIVE_MEDIA_ROOT = '%s'   # %s = schema_name
STORAGES = {'default': {'BACKEND': 'django_tenants.files.storage.TenantFileSystemStorage'}}
```

**El fet que ho fa fàcil:** el `name` desat a la BD és **relatiu a l'arrel del tenant**
(`model_fitxers/2026/07/BRW-FW27-0001_fitxa.ftt`), perquè el prefix del schema viu a
`location`, no al nom. Traslladar bytes **no obliga a reescriure la BD**.

**Precedent directe i complet:** `models_app/management/commands/move_media_tenant.py` — recorre
tots els `FileField`/`ImageField` de tots els models instal·lats, mou bytes entre arrels, és
idempotent i no toca la BD. Una còpia Studio→Brand és el mateix patró amb origen i destí
diferents:

```
media/fhort/model_fitxers/2026/07/x.ftt   →   media/los/model_fitxers/2026/07/x.ftt
       └── llegir dins schema_context('fhort')      └── escriure dins schema_context('los')
```

**Dos esculls concrets, tots dos ja documentats:**
1. `media/los/` **no existeix** al disc de staging (només `fhort/`, `test/` i els directoris
   pre-aïllament). El crearà el primer `save()`, i **no s'ha de crear a mà com a root**:
   gunicorn corre com a `www-data` i un directori de root deixa el tenant sense poder escriure.
2. La còpia s'ha de fer **bytes a bytes obrint i reescrivint pel storage**, no amb `shutil` de
   ruta a ruta, si es vol que el `name` i el versionat (`is_current`, `versio`) els governi
   `services_fitxers.save_model_file` — que és l'única porta que manté la invariant de la
   cadena de versions (S03a · P0.1).

---

## A9-4 — Escriure al Brand: el mur

Estat REAL del Brand `los` avui:

```
UserProfile        1     (qa.loginunic@fhort.test)
POMMaster          0     ← EL MUR
BaseMeasurement    0     (el "residu de 46 mesures" del brief ja NO hi és)
SizeFitting       51     (creades soles pel signal en instanciar els 51 models)
GradingVersion     0  ·  GradedSpec 0
Model             51
```

### 🔴 Bloquejant dur: el Brand no té catàleg de POM

`BaseMeasurement.pom` i `GradedSpec.pom` són **FK PROTECT a `POMMaster`**, i `los` en té **zero**.
No és que la sembra de retorn falli a mitges: **no pot començar**. Abans de tornar ni una sola
mesura, el Brand ha de tenir un catàleg de POM on aterrar-la, i llavors la pregunta següent és
inevitable: *el mateix POM del Studio i el del Brand són el mateix POM?* La resposta d'avui és
la mateixa que a la instanciació d'anada — **resolució per CLAU NATURAL** (`codi_client` /
`code`), amb els no aparellats reportats i mai inventats.

### Els signals que saltaran

Tots viuen a `models_app/signals.py` i estan enganxats a `post_save` **genèric** (sense
`sender=`), de manera que es dispararan igual escrivint des d'un procés del Studio dins de
`schema_context('los')`:

| Signal | Què fa en una escriptura de retorn |
|---|---|
| `sync_size_fitting` (`:86`) | Ja ha creat les 51 SizeFitting buides. Una sembra que en creï una altra duplicaria. |
| `log_measurement_change` (`:233`) | **Escriu un `MeasurementChangeLog` per cada mesura amb valor.** Una sembra de 20 mesures × N models omple el log d'auditoria del Brand amb entrades sense autor. |
| `recompute_import_watchpoint` (`:145`) | Recalcula watchpoints d'import en desar el Model. |
| `update_last_activity` (`:177`) | `queryset.update()` — inofensiu (no recursiu). |

`created_by` és nullable a `BaseMeasurement` i a `MeasurementChangeLog`, i `GradingVersion.creat_per`
també (`on_delete=PROTECT` però `null=True`) → **la manca de `UserProfile` al Brand NO és
bloquejant**, però deixaria tot el rastre d'auditoria sense autor. És una decisió (💡4), no un
accident: qui és l'autor d'una mesura que ha pres un altre tenant?

---

## A9-5 — Planificació contínua: què podria veure el Brand

Les dates que existeixen avui, totes a `models_app/models.py`:

| Camp | Què és | Exposable al Brand? |
|---|---|---|
| `data_entrada` (`:237`) | alta del model | Sí — és un fet, no un temps de ningú |
| `data_objectiu` (`:247`) | compromís | Sí — és **el** compromís amb el Brand |
| `data_tancament` (`:248`) | tancament | Sí |
| `predicted_start` / `predicted_end` (`:249-250`) | predicció del planificador (M1) | ⚠️ deriven de la càrrega i la cua de persones concretes |
| `fase_actual` (`:223`) | `Pending→Dev→Proto→SizeSet→PP→TOP` | Sí — és maduresa, no temps |
| `FittingSession.data` | data de prova | Sí la data; **mai** els assistents |

**La forma mínima que respecta la llei ("el Brand mai veu temps ni tècnics"):** el Brand veu
**MADURESA + COMPROMÍS**, no execució. És a dir, per model: `fase_actual`, `data_objectiu`,
`data_tancament` i la data de la propera fita — i **res** de `predicted_*` en brut, perquè una
predicció és el reflex directe de la cua de treball d'una persona. Si es vol donar previsió, ha
de ser **derivada i arrodonida a fase** ("SizeSet previst la setmana del 12/10"), no la data
exacta que el planificador calcula per a un tècnic.

Això ja té la infraestructura de transport feta: és exactament la mateixa lectura delegada
(`schema_context` + dicts) que fa `safata_del_studio` a P8, però en direcció contrària.

---

## A9-6 — 💡 PROPOSTES (per decidir, cap implementada)

| # | Proposta | Per què | Cost |
|---|---|---|---|
| **💡1** | **Ancoratge explícit del retorn.** Afegir `Model.origen_brand_codi` (codi nu, buit als INTERN) al Studio, escrit per la instanciació. El retorn resol per `(origen=EXTERN, origen_brand_codi, codi_intern)` i mai pel codi sol. | Tanca la mina d'A9-2 **abans** que `los` sembri el seu SS27 i els codis es dupliquin als dos costats amb `origen=INTERN`. | **S** — 1 camp + migració + 2 línies al servei de P8. Fer-ho ara val 10× fer-ho després. |
| **💡2** | **Sembrar el catàleg de POM al Brand** com a prerequisit declarat, reutilitzant la resolució per clau natural que ja fa la instanciació d'anada. | Sense això la sembra de retorn no pot ni començar (A9-4). No és part del retorn: és la seva precondició. | **M** — decisió de domini (quin catàleg és el canònic) + command idempotent. |
| **💡3** | **Un acte explícit de LLIURAMENT**, no una sincronització contínua. Un endpoint del Studio (`POST /encarrecs/<codi>/lliurar/`) que empaqueta i escriu al Brand, amb el seu informe, mirall exacte de `traspassar`. | No hi ha cap camp que digui "acabat" (A9-1), i inventar-ne un que s'hagi de mantenir sincronitzat seria repetir l'error que P8 va evitar amb `estat_local`. Un acte deixa data, autor i informe. | **M** — el patró ja existeix; és omplir-lo. |
| **💡4** | **Decidir l'autoria del rastre importat**: `created_by=NULL` + un `origen` nou (`FEDERAT`) a `BaseMeasurement`, en comptes de fer passar per MANUAL una mesura que ha pres un altre tenant. | El log d'auditoria del Brand s'omplirà (A9-4); ha de poder distingir el que ha fet ell del que li ha arribat. | **S** — 1 choice nou + el filtre al signal. |
| **💡5** | **Silenciar els signals durant la sembra** amb una marca explícita (`instance._sembra_federada = True`), com ja es fa amb `_desactivat` i `_changed_by`. | Evita omplir `MeasurementChangeLog` amb N×M entrades sense autor i duplicar SizeFitting. El patró de marca explícita ja és el de la casa. | **S** |
| **💡6** | **Vista de maduresa per al Brand** (`GET /api/v1/recursos/<studio>/progres/`): per model, `fase_actual` + `data_objectiu` + `data_tancament`. **Sense** `predicted_*`, sense assistents, sense hores. | És el que A9-5 conclou que es pot ensenyar sense trencar la llei, i el transport ja existeix (lectura delegada de P8 en direcció contrària). | **M** |
| **💡7** | **Fitxes i patrons: enllaç, no còpia**, en una primera fase. El Brand veu que existeix un lliurable i en demana la descàrrega puntual; no se'n dupliquen els bytes a `media/los/`. | La còpia de media és resoluble (A9-3) però duplica emmagatzematge i obre la pregunta de quina còpia mana quan el Studio en publica una versió nova. | **S** ara / **L** si es fa còpia real. |

### Decisions obertes per al CTO (numerades)

1. **💡1 abans o després de la sembra SS27 a `los`?** — És l'única d'aquestes que té data de
   caducitat: després, cal desfer dades.
2. **Quin catàleg de POM és el canònic** quan Brand i Studio en tenen un de propi (💡2)?
3. **El retorn és un acte de lliurament o una sincronització contínua** (💡3)? Tot el disseny
   de P7/P8 apunta a acte explícit, però és decisió de producte.
4. **Què veu el Brand de la planificació** (💡6): res, maduresa+compromís, o maduresa+previsió
   arrodonida?
5. **Els lliurables es copien o s'enllacen** (💡7)?

---

## Banderes anotades

- **962 `LOS-SS27-*` INTERN a `fhort`** (heretada de la diagnosi de federació): és la causa
  arrel de la mina d'A9-2 i condiciona 💡1.
- **`los` no té catàleg** (0 POMMaster): bloquejant dur de tot el retorn (A9-4).
- **El "residu de 46 mesures a `los`" que citava el brief ja no hi és** (0 BaseMeasurement).
  Anotat com a correcció factual, no com a problema.
- **51 SizeFitting buides a `los`** creades pel signal en instanciar: qualsevol sembra de
  retorn les ha de REUTILITZAR, no crear-ne de noves (constraint d'una sola versió vigent).
