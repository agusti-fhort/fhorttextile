# DIMENSIONAT — Sprint A (SET-1) + Sprint B (còpia de POMs model→model)

Data: 2026-07-27 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`
(HEAD llegit: `95dee480`, amb **arbre de treball SUCIÓS d'una sessió paral·lela** — §B4)

**Abast.** DIMENSIONAR dos sprints ja decidits (Patró C, 27/07). No es re-litiga cap decisió i
no es proposa cap alternativa d'arquitectura. Per cada bloc: **DIMENSIÓ** (fitxers, S/M/L,
migració sí/no) + **riscos** + **què contradiu** les decisions fixades.

**Base obligada** (no se'n repeteix el cens; s'hi remet i s'hi estén):
- [`DIAGNOSI_MULTIPECA_DALIA.md`](DIAGNOSI_MULTIPECA_DALIA.md) — Q1-Q5, taula final 22 files.
- [`DIAGNOSI_COMPONENTS_MULTIPLES_MESURES.md`](DIAGNOSI_COMPONENTS_MULTIPLES_MESURES.md) — P1-P4.

**Decisions fixades que emmarquen el dimensionat** (donades, no discutides):
1. UN codi comercial; peces = parts internes 01/02/03; el client veu el model sencer.
2. SET = 1 mèrit. Conversió mandrosa (mai preventiva).
3. El GTI declara PEÇA o SET amb composició d'items; DEFECTE = NO SET (cap backfill).
4. Hipòtesi de construcció preferida: **(a) parts com a Models interns sota `GarmentSet`**.

**Convenció.** Cada afirmació porta `fitxer:línia`. **"NO EXISTEIX" = confirmat absent al codi.**
Les formes alternatives es dimensionen TOTES DUES sense triar-ne cap.

---

## 0 · Dues files de la base ja estan SUPERADES (avui mateix)

Cal dir-ho abans de dimensionar res, perquè canvia el punt de partida d'A5:

| Base | Deia | Estat real 27/07 |
|---|---|---|
| DALIA taula §14 | «Secció d'origen del POM: **ES PERD** a l'extracció» | **SUPERADA** per `95dee480` (F4, avui 11:18). Cada POM porta `seccio` pels DOS camins: parser `extraction_views.py:421,433-436,464`; IA `:1621` (camp `section` opcional al prompt); propagació `:1216`. Arriba a `session.poms_extrets`. **Consumidors: ZERO** (grep `seccio` → 5 llocs, tots productors; `frontend/src` → 0 hits). |
| DALIA taula §15 | «Parser llegeix només el primer full» | **EN CURS ARA MATEIX**, sense commitar. El diff viu de `extraction_views.py` (+120 línies) introdueix el cens de fulls que passen la porta, la tria `full_seleccionat` desada a `run_conciliat` (JSONField existent, cap migració) i l'informe de fulls pels dos camins. Vegeu §B4. |

Conseqüència directa: **la matèria primera per "descobrir parts" des de l'import ja existeix
(secció per POM) i la segona forma de document multi-peça (un full per peça) s'està cablejant en
paral·lel.** A5 deixa de ser "cal tocar l'extractor" i passa a ser "cal donar consumidor a una
dada que ja hi és".

---

## Resum executiu del dimensionat

1. **A4 és gairebé gratis: el backend multi-peça JA existeix sencer.** `create_model_wizard`
   (`models_app/views.py:698-871`) crea `GarmentSet` + N Models amb `piece_number` i materialitza
   les regles de cada peça (`:824-870`). La numeració reserva el codi base a les DUES taules
   (`:776-790`) i les peces són `-01/-02`, **exclosos de l'escaneig per regex** — encaixa amb
   parts internes sense tocar res.

2. **Però totes les peces neixen IDÈNTIQUES.** `**garment_fields` (`:849`) és el MATEIX dict per
   a cada peça: mateix `garment_type_item`, mateix `grading_rule_set`, mateix `nom_prenda`
   (`:838`). **La composició d'items de la decisió 3 no té cap consumidor.** Aquesta única línia
   decideix si A6 (grading per part) és gratis o no.

3. **A2 és EL cost del sprint, i és L per les dues formes.** No per volum de codi sinó perquè
   `GarmentSet` **no és un Model**: si s'amaguen les parts, la llista no té cap fila per al
   conjunt. 11 superfícies de frontend llisten Models i **3 punts de backend salten el filtre
   canònic** (`by_model`, `assign-batch`, `project-gantt`).

4. **A3 té un blocador de forma, no de codi:** `ConsumptionRecord.model` és un
   **OneToOneField** (`models_app/models.py:864-866`). Un mèrit de conjunt no es pot expressar
   sense triar una peça guanyadora o migrar. I el guard s'ha de posar a **DOS** llocs alhora:
   tocar només `services_c.py` deixa que `reconcile_consumption` re-meriti les germanes.

5. **La conversió mandrosa NO té camí d'escriptura avui.** `Model.garment_set` no s'escriu enlloc
   fora de la creació (grep: `views.py:847`, `bulk_import_service.py:519-527`), el serializer no
   l'exposa (0 hits a `models_app/serializers*.py`) i `num_pieces` està documentat *"Immutable
   després de la creació"* (`models_app/models.py:61-63`). A5 és inventari d'ancoratges; el camí
   no hi és.

6. **B2 reusa ~5 línies de `clone_model_for_qa` de 165.** El que serveix és el bucle
   `:92-96`; la resta (clon de Model, tag QA, MGR, SF, grading, tasca, `_purge`) sobra. I el
   command **no és cridable des de la UI** (management command amb `--schema`).

7. **B2 té una validació obligatòria que no és al brief: la talla.** `materialize_poms_view` té
   el guard P1 (`views.py:1071-1092`) precisament perquè *un valor està expressat EN UNA TALLA*.
   Copiar valors model→model té el MATEIX perill. Sense transposar-lo, es reintrodueix un bug ja
   corregit.

8. **`BaseMeasurement.origen` no té cap valor admissible per a una còpia** (`models_app/models.py:571-580`).

9. **Col·lisió B4 real = 4 fitxers**, tots de frontend: `api/endpoints.js` + `i18n/{ca,en,es}.json`.
   Zero solapament de Python entre Sprint B i l'import. **A5, en canvi, són els MATEIXOS fitxers
   que el sprint en vol.**

---

# SPRINT A — SET-1

## A1 · Camp SET al GTI

### On viu i qui el toca (cens complet)

**Model.** `GarmentTypeItem` a `tasks/models.py:306-350`. Docstring `:307-309`: *"Variant d'un
GarmentType per grau de complexitat… Pantaló → xandall < chino < sastre"*. Camps: `garment_type`
FK(`pom.GarmentType`, CASCADE), `code` SlugField(60), `name` CharField(200),
`complexity_order`, `active`, `base_size_definition` FK(`pom.SizeDefinition`, SET_NULL, `:321`),
`grading_rule_set` FK(`pom.GradingRuleSet`, PROTECT, `:337`). **Cap noció de composició ni de
conjunt.**

| Capa | Ancoratge | Què caldria |
|---|---|---|
| Serializer | `tasks/serializers_b.py:133-173` · `Meta.fields` `:149-151` · `validate()` `:159-173` | +1 camp a `fields`; +composició si es niua |
| ViewSet | `tasks/views_b.py:932-967` · `queryset` `:947-954` (annotate `poms_count`/`fitxers_count`) · `filterset_fields=['garment_type','active']` `:960` · `search_fields` `:961` | `?is_set=` al filterset si la UI l'ha de filtrar |
| Permisos | `tasks/views_b.py:963-967` — list/retrieve = `IsAuthenticated`; escriptura = `CONFIGURE` | cap canvi |
| URL | `tasks/urls.py` router `basename='garment-type-item'` | cap canvi |
| Frontend · autoria | `pages/ItemAuthoring.jsx` (429 l.) — `create` `:142-146`, `update` `:158`, `:177`, `:190`, `:208`; wizard de 2 passos, `canNext` `:203` | **el punt de declaració** |
| Frontend · graella | `pages/GarmentTypes.jsx` (448 l.) — `list` `:73`, cards `:236-254` | badge SET |
| Frontend · comercial | `pages/ProductDetail.jsx:49` — `garmentTypeItems.list({active:true})` | lectura; cap canvi |
| Frontend · API | `api/endpoints.js:409-414` | cap canvi (PATCH genèric) |
| Frontend · consum | `CascadeSelector` (nivell item) + `ModelWizard` bloc 2 | vegeu A4 |
| **Còpia de tenants** | `tasks/management/commands/bootstrap_tenant.py:155` — `_spec()`: `(GarmentTypeItem, ('garment_type','code'), {}, (), None)` | **una boolean hi passa gratis; una taula de composició necessita entrada pròpia** |
| **Paquet LOSAN** | `export_losan_package.py:220-227` — serialització **camp a camp** (i `name` ja no hi és) · `load_losan_package.py` | +1 línia per camp nou; +bloc per taula nova |
| **Federació** | `tenants/federation_service.py:139-147` — resol GTI per clau natural (`gt.codi_client`, `code`) | cap canvi (no llegeix camps del GTI) |
| Comercial | `commerce/models.py:160` `ProductComponent` → FK a GTI | cap canvi |

### Les dues formes de composició, dimensionades

**Forma 1 · M2M a si mateix** (`parts = M2M('self', symmetrical=False, related_name='part_of')`)
- Migració: 1 (`AddField` + taula de junció automàtica). Cap backfill (default = buit).
- Serializer: `fields += ['is_set','parts']` → llista d'ids. Escriptura per PATCH genèric.
- **Límit dur i decisiu: la taula automàtica de Django NO té columnes extra.** No hi cap ni
  `ordre` (quina peça és 01/02/03) ni `nom_peca`. La decisió d'A4 («neixen les parts **amb nom
  per peça**») exigeix les dues. Amb `through=` per afegir-les, la Forma 1 **és** la Forma 2.
- `bootstrap_tenant`: el M2M va al 4t element de la tupla `_spec()` (`:155`), com
  `SizeSystem.targets` (`:146`) — però és **auto-referent**, i les parts poden no existir encara
  quan es copia l'ítem-set. `SizeSystem.parent` fa servir `DEFER` (`:146`) per aquest mateix
  problema: hi ha precedent, no és terra verge.
- Dimensió: **S** de codi, **però no cobreix el requisit**.

**Forma 2 · taula pròpia** (`GarmentTypeItemPart(set_item FK, part_item FK, ordre, nom_peca)`)
- Migració: 1 (`CreateModel` + `AddField is_set`). Cap backfill.
- Clau natural per a `bootstrap_tenant`/paquet: `('set_item','part_item')`, entrada nova a
  `_spec()` **després** de `GarmentTypeItem` (`:155`) — ordre topològic, com `GarmentPOMMap`
  (`:156`) respecte del seu item.
- Serializer: niuat read (`PartSerializer(many=True)`) + un write path propi (el PATCH genèric no
  escriu relacions inverses) → **una acció o un endpoint nou**, no surt gratis del ModelViewSet.
- Guard de cicles (un ítem-set que es té a si mateix com a part) i de profunditat (un set de
  sets): `clean()` al model, precedent exacte a `GarmentTypeItem.clean()` (invocat des del
  serializer a `serializers_b.py:159-173`, perquè *"DRF no crida Model.clean() sol"*).
- Dimensió: **M**.

| DIMENSIÓ A1 | |
|---|---|
| Fitxers backend | `tasks/models.py`, `tasks/serializers_b.py`, `tasks/views_b.py`, `tasks/migrations/00NN_*`, `tasks/management/commands/bootstrap_tenant.py`, `pom/management/commands/export_losan_package.py`, `pom/management/commands/load_losan_package.py` |
| Fitxers frontend | `pages/ItemAuthoring.jsx`, `pages/GarmentTypes.jsx`, `i18n/{ca,en,es}.json` |
| Talla | **S** (Forma 1 nua) · **M** (Forma 2 / Forma 1 amb `through`) |
| Migració | **SÍ**, 1 · additiva · **cap backfill** (`is_set` default False) |

**Riscos.** (1) Els 3 mecanismes de còpia enumeren camps a mà — oblidar-ne un fa que els sets no
sobrevisquin a un `bootstrap_tenant` ni al paquet LOSAN, **en silenci**. (2) `export_losan_package.py:223-227`
ja no exporta `name`: el precedent d'oblit existeix. (3) `complexity_order` i `is_set` són
ortogonals però la graella els pintarà junts (`GarmentTypes.jsx:236-254`).

**Contradiu?** **No.** `is_set` default False + 0 files de `GarmentSet` als dos esquemes
(§A2, cens de BD) = decisió 3 satisfeta literalment, cap backfill possible ni necessari.

---

## A2 · Hipòtesi (a): parts com a Models interns — EL cost real

### Cens de BD (executat, read-only)

```
fhort: GarmentSet=0 · Models=1056 · Models amb garment_set=0 · GTI=62 · BaseMeasurement=647
los:   GarmentSet=0 · Models=51   · Models amb garment_set=0 · GTI=1  · BaseMeasurement=0
```

Confirma la base (DALIA §Q1) i tanca l'«Obert» de la diagnosi de components (§Obert, línia 191).
**Terra verge: cap dada a migrar, cap fila a amagar avui.**

### El fet que governa tot el bloc

`GarmentSet` (`models_app/models.py:43-72`) **no és un `Model`**: no té `fase_actual`, ni
`prioritat`, ni `data_objectiu`, ni `responsable`, ni tasques, ni customer. I `ModelListSerializer`
(`models_app/serializers.py:87-133`) **no exposa ni `garment_set` ni `piece_number`** (verificat:
`fields` `:104-133`). Per tant, amagar les parts deixa la llista **sense cap fila per al conjunt**;
agrupar-les obliga a triar una part com a cara visible.

### Backend — qui filtra i qui NO

| # | Superfície | Ancoratge | Hereta un filtre nou a `ModelFilter`? |
|---|---|---|---|
| 1 | `ModelViewSet` list | `models_app/views.py:129-181` · `get_queryset` `:138-180` · `filterset_class` `:132` | **SÍ** (i també un default a `get_queryset`) |
| 2 | `ModelFilter` (font única C1) | `models_app/views.py:31-127` · `Meta.fields` `:68-72` | és el punt d'edició |
| 3 | `fase-counts` | `models_app/views.py:196-217` — `self.filter_queryset(self.get_queryset())` `:213` | **SÍ** (les dues vies) |
| 4 | `garment-counts` | `models_app/views.py:219-253` — mateix patró `:246` | **SÍ** (les dues vies) |
| 5 | Kanban `by-model` | `tasks/views_b.py:102-233` — **`ModelFilter(qp, queryset=Model.objects.all())` `:150`** | **només el FilterSet.** Salta `ModelViewSet.get_queryset` → un default de queryset **NO hi arriba** |
| 6 | Planificació `assign-batch` (conjunt per filtres) | `planning/views.py:658-672` — mateix patró `:664` | **igual que #5** |
| 7 | **`project-gantt`** | `planning/views.py:718-760` — filtres **a mà** (`model_id` `:736`, `responsable` `:738`, `collection` `:740`, `temporada` `:742`) | **NO. Ni FilterSet ni get_queryset** → pedaç explícit obligatori |
| 8 | Numeració · terra de seqüència | `models_app/services.py:83-86` `_real_max_seq` (`Max('sequencial')`, exclou EXTERN) | irrellevant per sort: **totes les peces neixen amb `sequencial=next_num`, el MATEIX valor** (`views.py:840`) → el terra no s'infla |
| 9 | **Federació · traspàs** | `tenants/federation_service.py:163-177` | **NO propaga `garment_set` ni `piece_number`** (llista de camps explícita). Un set traspassat arriba al Studio com a N Models solts amb codis `-01`/`-02` i **el conjunt es dissol** |
| 10 | Import massiu (únic creador viu de sets) | `bulk_import_service.py:508-527` · columnes manuals `:18` | ja crea sets; cap canvi |

**Cost mínim de "una sola edició": no existeix.** Un default a `ModelFilter` cobreix #1-#4 i #5-#6
com a FilterSet; **#7 exigeix un pedaç a mà i #9 una decisió pròpia**.

### Frontend — les 11 superfícies que llisten Models

| # | Superfície | Ancoratge | Naturalesa |
|---|---|---|---|
| 1 | **`pages/Models.jsx`** (545 l.) | list `:139` · garment-counts `:130` · fase-counts `:134` · `visibleItems` `:201` · `ModelRow` `:453` · paginació `:169-171`, `:347-354` | la llista mestra |
| 2 | **Bulk** `components/model/ActionsMenu.jsx` (477 l.) | `runBulk` `:104-120` · gate/regress `:200-201` · assign a línia `:207` · `assignarRecurs` `:215` | per-element, EXCEPTE `assignarRecurs` (1 crida en bloc) |
| 3 | **Selecció per FILTRE** | `Models.jsx:40`, `:170`, `:205-211`, `selectionSet` `:247` → `planning/views.py:664` | el conjunt es defineix **al backend per filtres**: llista i bulk han de dir el mateix o la selecció menteix |
| 4 | `pages/Dashboard.jsx` (609 l.) | by-model `:154` · fase-counts `:175` · KPIs `:429` | Kanban + KPIs |
| 5 | `components/planning/DashboardGovPanel.jsx` (315 l.) | `fetchAllPages(modelsApi.list,{})` `:124` · fase-counts `:83` | govern |
| 6 | `components/planning/InformesPanel.jsx` (313 l.) | `fetchAllPages(modelsApi.list,{})` **×2** `:99`, `:178` | agregació al client |
| 7 | `components/planning/ProjectGantt.jsx` | endpoint #7 del backend | **el que no hereta res** |
| 8 | `components/assets/AssetNavigator.jsx:108` | `modelsApi.list({page_size:PAGE_MODELS})` | Finder d'actius |
| 9 | `pages/FittingSessionList.jsx:539-600` `FittingNowPicker` | `modelsApi.list({search,page_size:20})` `:552` | selector (vegeu B1) |
| 10 | `components/model/AddModelToGroupModal.jsx:32` | `modelsApi.list({page_size:500})` | selector `<select>` (vegeu B1) |
| 11 | `pages/RegistreActivitat.jsx:171` | files → `/models/:id` | navegació |

**Bona notícia acotada: NO hi ha cerca global de models.** `components/layout/Topbar.jsx` no té
cap camp de cerca (grep `search` → 0 hits útils). Una superfície menys.

### Les dues formes d'ocultació, dimensionades

**Forma α · AMAGAR les parts** (`ModelFilter` default `garment_set__isnull=True`, opt-in
`?include_pieces=1`)
- Coherent amb la decisió 1 (el client veu el model sencer) i amb "parts internes".
- **Però la llista es queda sense el conjunt.** Cal una font de files per als sets: endpoint nou
  (`GarmentSet` list amb la forma de `ModelListSerializer`) o una unió al mateix endpoint. El
  serializer del conjunt hauria de **derivar** fase/prioritat/responsable de les peces
  (`GarmentSet` no en té cap) → agregació nova, no reús.
- Superfícies a tocar: #1 (files de conjunt), #7 (pedaç), #9 (decisió), + els comptadors
  (#3/#4 backend) passen a comptar conjunts, no Models → **`fase-counts` deixa de ser un
  `values('fase_actual').annotate(Count('id'))`** (`views.py:214-215`).
- Dimensió: **L**.

**Forma β · AGRUPAR sota la peça 01** (la part `piece_number=1` és la fila visible; germanes
niuades)
- Cap font de files nova: la fila existeix (és un Model).
- **Però tot el que compta, compta 3.** `count`/`pages` (`Models.jsx:169`), `fase-counts`,
  `garment-counts`, KPIs (`Dashboard.jsx:429`), barres del Gantt, i la **selecció per filtre**
  (#3: `filterCount = count - excludeIds.size`, `Models.jsx:170`) → l'usuari veu 1 fila i el bulk
  actua sobre 3. Això no és un detall d'UI: és el contracte de conjunt de `selectionSet`.
- Superfícies a tocar: #1, #2, #3, #4, #5, #6, #7 (les 4 primeres de debò).
- Dimensió: **L**.

| DIMENSIÓ A2 | |
|---|---|
| Fitxers backend | `models_app/views.py` (ModelFilter + ViewSet + 2 comptadors), `tasks/views_b.py`, `planning/views.py` (×2 punts), `tenants/federation_service.py`, + serializer/endpoint de conjunt (només Forma α) |
| Fitxers frontend | `Models.jsx`, `ActionsMenu.jsx`, `Dashboard.jsx`, `DashboardGovPanel.jsx`, `InformesPanel.jsx`, `ProjectGantt.jsx`, `AssetNavigator.jsx`, `i18n×3` |
| Talla | **L** per les dues formes |
| Migració | **NO** (`garment_set` + `piece_number` ja existeixen i estan aplicats — `0019_…`) |

**Riscos.**
1. **#7 `project-gantt` és l'únic lector que no passa per cap font única de filtres.** Qualsevol
   ocultació que no el toqui explícitament ensenyarà les parts al Gantt i enlloc més.
2. **#9 federació dissol el conjunt.** Silenciós: el Studio rep 3 models `-01/-02/-03` sense
   `GarmentSet`; res no falla, la unitat comercial desapareix. Toca la decisió 1 de ple.
3. **La paginació menteix a la Forma β** i el `selectionSet` per filtres (#3) hereta la mentida.
4. `ModelSheet` d'una part no té navegació a les germanes (0 hits de `garment_set` a `frontend/src`,
   base DALIA taula §6) → un tècnic dins una part no sap que forma part de res.
5. `ConsumptionRecord.code_snapshot` (`models_app/models.py:867`) i els snapshots de `WorkOrder`
   congelen `codi_intern` — d'una PART. Vegeu A3.

**Contradiu?** **Una tensió real, no una contradicció de la decisió.** La decisió 1 diu «UN codi
comercial… el client veu el model sencer». Amb hipòtesi (a), el codi comercial viu a
`GarmentSet.codi_base` — **una fila que no és un Model** — mentre totes les superfícies de cara al
client imprimeixen `Model.codi_intern` (llista `serializers.py:106`, albarà `models.py:867`,
encàrrec, fitxa). És el preu de (a), i s'ha de pagar explícitament a A3 (albarà) i al PDF.

---

## A3 · Meritació set = 1 amb parts com a Models

### Els punts EXACTES (n'hi ha dos, no un)

**Punt 1 · runtime** — `tasks/services_c.py`, dins la transició a `InProgress`:

| Línia | Què fa | Per què és per-pk |
|---|---|---|
| `:162-164` | `Model.objects.filter(pk=task.model_id, consumption_started_at__isnull=True).update(consumption_started_at=now)` | el guard d'idempotència **és** aquest `filter(pk=…)` |
| `:165` | `if rows:` — només la primera vegada d'AQUELL Model | 3 parts = 3 primeres vegades |
| `:167-173` | `ConsumptionRecord.objects.create(model=model, code_snapshot=model.codi_intern, …)` | **`ConsumptionRecord.model` és `OneToOneField`** (`models_app/models.py:864-866`) |
| `:174-182` | `model_consumption_started.send(...)` → `backoffice/receivers.py:7-23` → `ModelConsumptionEvent.get_or_create(opaque_ref=…)` a `public` | l'event **no té cap referència a model** (`backoffice/models.py:79-104`): només `codi_client`/`period`/`opaque_ref` |

Facturació: `backoffice/recurring_service.py:87` fa `.count()` d'events del període i `:104` factura
l'excés. **La unitat facturable és l'event; 3 events = 3.**

**Punt 2 · reconciliació** — `backoffice/management/commands/reconcile_consumption.py`:

| Línia | Què fa |
|---|---|
| `:74-83` | criteri de forat: `consumption_started_at__isnull=True` **AND** `model_tasks__status__in=['InProgress','Done','Paused']` |
| `:120-124` | segon guard d'idempotència, **mateixa forma** `filter(pk=…, consumption_started_at__isnull=True)` |
| `:139-147` | `ConsumptionRecord.objects.create(...)` + `send(...)` |

### La trampa que el brief demana localitzar

**Tocar només el Punt 1 és una fuita garantida.** Si el guard de conjunt deixa
`consumption_started_at=NULL` a les peces 02 i 03 (perquè "ja ha meritat la 01"), aquestes dues
peces compleixen EXACTAMENT el criteri de forat de `reconcile_consumption:74-83` — tenen activitat
de tasca i no tenen marca — i **la propera execució les merita**. El resultat és set=3 amb un
retard.

Per tant: **els dos punts han de canviar a la mateixa peça, sempre.**

### Tres col·locacions del guard (dimensionades, no triades)

| | Forma | Codi | Migració | Efecte lateral |
|---|---|---|---|---|
| i | Excloure germanes al `filter` del Punt 1 (+ mateix criteri al Punt 2) | `services_c.py:162-164` + `reconcile_consumption.py:74-83`,`:120-124` | **NO** | Deixa `consumption_started_at` NULL a les germanes → cal el canvi bessó al Punt 2, i el camp perd el significat de "aquest model va arrencar" per a 2 de 3 peces |
| ii | Estampar `consumption_started_at` a **totes** les germanes, crear **un sol** `ConsumptionRecord` | mateixos 2 fitxers | **NO** | `reconcile` queda honest sol (cap forat). Cal **peça guanyadora determinista** (`piece_number=1`? la de la tasca?) → decisió. `code_snapshot` serà d'una PART |
| iii | Ancorar a `GarmentSet` (`GarmentSet.consumption_started_at` + `ConsumptionRecord.garment_set` nullable + XOR) | + `models_app/models.py` + migració | **SÍ**, 1 | L'única que expressa "1 mèrit del conjunt" a la BD. Toca la taula de facturació del tenant |

| DIMENSIÓ A3 | |
|---|---|
| Fitxers | `tasks/services_c.py` (`:150-195`), `backoffice/management/commands/reconcile_consumption.py` (`:74-147`) · +`models_app/models.py`+migració només a (iii) |
| Talla | **S/M** (i, ii) · **M** (iii) |
| Migració | **NO** (i, ii) · **SÍ** (iii) |
| Intocats | `backoffice/receivers.py`, `backoffice/recurring_service.py`, `ModelConsumptionEvent` — emetem 1 event i el recompte ja és correcte |

**Riscos.**
1. **`ConsumptionRecord` és OneToOne + CASCADE** (`models_app/models.py:864-866`): a (i)/(ii),
   esborrar la peça guanyadora **esborra l'albarà del conjunt sencer** mentre les germanes viuen.
2. `opaque_ref` és `unique` i el receiver és idempotent **només per `opaque_ref`**
   (`receivers.py:16`) — no per (codi_client, model). Un mèrit repetit per una via nova genera un
   event nou; ja hi ha precedent documentat (`MAPA_SISTEMA_EXHAUSTIU.md:326`).
3. `reconcile_consumption` és **manual** i actua per tenant: el forat no es veu fins que algú
   l'executa.
4. El bloc de meritació és `try/except` no-fatal (`services_c.py:183-186`): un guard que peti hi
   quedarà **enterrat al log**, no bloquejarà res.

**Contradiu?** **Sí, un punt concret.** `code_snapshot` (`services_c.py:169`) desa
`model.codi_intern` — amb (i)/(ii) serà el codi d'una PART (`…-0834-01`). L'albarà que el client
veu (`ConsumptionRecord`, *"Viu al TENANT, el veu el client"*, `models.py:861`) nomenaria una peça
interna. **Xoca amb la decisió 1** («el client veu el model sencer»). Amb (iii) no passa. És una
conseqüència de la forma, no un defecte del codi actual.

---

## A4 · Creació: què falta

### El que JA hi és (i és molt)

`create_model_wizard` (`models_app/views.py:698-871`), `POST models/create-wizard/`
(`urls.py:203`):

| Peça | Línies | Estat |
|---|---|---|
| `is_multipiece` / `num_pieces` del payload | `:710-711` | EXISTEIX |
| Validació (`int`, `>= 2`) | `:750-760` | EXISTEIX |
| GTI obligatori | `:745-748` | EXISTEIX |
| **Numeració** que reserva el base a les DUES taules | `:776-790` | EXISTEIX |
| Branca single (≈90%) | `:792-819` | EXISTEIX |
| **Branca multi-peça**: `GarmentSet` + N Models + `piece_number=i` + MGR per peça, tot dins un `atomic` | `:822-870` | **EXISTEIX SENCERA** |

### Numeració: encaixa amb parts NO visibles? — **SÍ, exactament**

`:776` → `base_pattern = f"^{prefix}-{season}{year_short}-[0-9]{{4}}$"`. El regex **ancora 4
dígits al final**, de manera que els codis de peça (`-NNNN-01`) **queden fora de l'escaneig**
(comentari literal `:769-775`). I escaneja **les dues taules**: `models_app_model.codi_intern`
(`:779-781`) **i** `models_app_garmentset.codi_base` (`:783-786`), *"because a set's base number is
consumed… and must not be reused by a later single model"*.

I el terra de seqüència no s'infla: totes les peces neixen amb `sequencial=next_num`, **el mateix
valor** (`:840`), i `_real_max_seq` (`models_app/services.py:83-86`) fa `Max('sequencial')` →
un conjunt de 3 peces consumeix **un** número, no tres. **Cap canvi necessari a la numeració.**

### El que FALTA per «GTI compost → neixen les parts amb nom per peça»

| # | Forat | Ancoratge exacte |
|---|---|---|
| 1 | **Totes les peces són idèntiques.** `**garment_fields` és el MATEIX dict al bucle | `:849` (i `_resolve_garment_def` resol UNA definició del payload, `:619-693`) |
| 2 | **Cap nom per peça.** `nom_prenda=nom_prenda or None` per a totes | `:838` (i `GarmentSet.nom_comercial=nom_prenda`, `:828`) |
| 3 | **Dues fonts de veritat per a "és un conjunt".** `is_multipiece`/`num_pieces` venen del payload; la decisió 3 diu que **el GTI ho declara** → `num_pieces` hauria de derivar de la composició (A1) | `:710-711` vs A1 |
| 4 | **El frontend no envia res.** 0 hits de `is_multipiece`/`num_pieces` a `frontend/src` (base DALIA §Q1) | `ModelWizard.jsx:422-427` (`payload`) + `:374-389` (`skeletonPayload`) |
| 5 | **El frontend PETARIA amb un set.** `navigate(\`/models/${r.data.id}\`)` — però la resposta multi-peça és `{garment_set_id, codi_base, num_pieces, pieces[]}` (`views.py:866-870`), **sense `id`** → `/models/undefined` | `ModelWizard.jsx:435` |
| 6 | **Editar "el conjunt" no existeix.** `update_model_step2` (`views.py:876+`) és per-Model; `handleSaveEdit` fa `models.update(id,…)` + `updateStep2(id,…)` | `ModelWizard.jsx:441-458` |

**On surt a la UI:** bloc 2 («Peça») del wizard, `ModelWizard.jsx:545-622` — és on es tria
family/item i on el GTI compost es faria visible. `BLOCKS` `:467`; `block1Resolved` `:472`.

| DIMENSIÓ A4 | |
|---|---|
| Fitxers backend | `models_app/views.py` (bucle `:832-866` + `_resolve_garment_def` `:619` per part) |
| Fitxers frontend | `pages/ModelWizard.jsx` (860 l. — bloc 2, `skeletonPayload`, `handleCreate`, navegació), `i18n×3` |
| Talla | **S** backend · **M** frontend |
| Migració | **NO** (la porta A1) |

**Riscos.** (1) El forat #5 és un **crash silenciós** el dia que el frontend enviï `is_multipiece`
— el backend ja respon bé, el frontend no ho sap llegir. (2) `num_pieces` és *"Immutable després
de la creació"* (`models.py:61-63`): si deriva del GTI i el GTI canvia de composició, els sets ja
creats divergeixen del seu GTI **sense cap avís**. (3) L'`atomic` del multi-peça (`:824`) és
tot-o-res per disseny: una peça amb GTI mal resolt avorta el conjunt.

**Contradiu?** **No la decisió, però sí una dualitat a resoldre:** amb la decisió 3, `is_multipiece`
al payload (`:710`) i la composició del GTI diuen la mateixa cosa dues vegades. Quina mana és
decisió; que avui hi hagi dues fonts és un fet.

---

## A5 · Conversió mandrosa — inventari d'ancoratges (cap disseny)

### Fet previ que emmarca tot el bloc

**No existeix cap camí d'escriptura per convertir un Model existent en part d'un conjunt.**
- `Model.garment_set` s'escriu en **exactament dos llocs**, tots dos de CREACIÓ:
  `models_app/views.py:847` i `bulk_import_service.py:519-527`.
- El serializer **no l'exposa** (0 hits de `garment_set` a `models_app/serializers*.py`) → el
  PATCH genèric del `ModelViewSet` no hi arriba.
- `GarmentSet.num_pieces` és *"Immutable després de la creació"* (`models.py:61-63`).
- El número base ja s'ha consumit com a model simple (`views.py:790`) quan el model va néixer.

### (i) Ancoratges al wizard d'import quan hi ha seccions

| Ancoratge | Fitxer:línia | Estat |
|---|---|---|
| **`seccio` per POM · parser** | `extraction_views.py:421` (`seccio_vigent`), `:433-436` (lectura de la fila), `:464` (al dict) | **PRODUEIX** (commit `95dee480`, avui) |
| **`seccio` per POM · IA** | `extraction_prompt.py` (camp `section` opcional) + `extraction_views.py:1621` | **PRODUEIX** |
| Propagació per l'aparellador | `extraction_views.py:1216` (`_match_rows`) + docstring `:1184-1186` | **PROPAGA TAL QUAL** |
| Destí de la dada | `session.poms_extrets` (JSONField) | **arriba i s'atura aquí** |
| **Consumidors** | grep `seccio` backend → 5 llocs, **tots productors**; `frontend/src` → **0 hits** | **CAP** |
| Taula de pre-vol (pas 2) on s'ensenyaria | `ImportWizard.jsx:726-888`, files `:804-834`; segon llistat `:952-956` | sense columna de secció |
| Escriptura final (on NO hi cap) | `extraction_views.py:2402` `BaseMeasurement.objects.update_or_create(model=model, pom=pm, defaults=…)`; `_defaults` `:2393-2401` | `BaseMeasurement` **no té camp de secció** (base: components §P1) → la bifurcació només pot ser a **nivell de MODEL**, mai de fila |
| Detector multi-model (ja existent) | `extraction_views.py:96-122` (`CRIBRATGE_PROMPT`), `:641-676`; avís i18n `ca.json:3423` | EXISTEIX, decideix `pot_continuar` |
| **Tria de full (2a forma de document)** | **DIFF VIU, sense commitar**: cens de fulls que passen la porta, `full_seleccionat` a `run_conciliat` (`import_session_talles_view`, ~`:794-798`), informe pels dos camins (`_extraccio_via_excel`, ~`:1369-1377`) | **EN CONSTRUCCIÓ ARA** (§B4) |

### (ii) Ancoratges a la pantalla de POMs

| Ancoratge | Fitxer:línia | Què és |
|---|---|---|
| Selector de gènesi | `components/model/MeasuresEntryPanel.jsx:26` — `mode ∈ 'loading'|'selector'|'manual'|'import'` | on viuria una 3a branca |
| Oferta que ESPERA confirmació | `:35` (`seedOffer`), `:96-111` (`confirmSeed`), llei F2.1 `:161-166` (*"la sembra és un ACTE DEL TÈCNIC, mai un efecte de muntatge"*) | el patró confirmar-abans-d'escriure |
| Chips per-POM (subconjunt) | `:30` (`seedPomIds`), `:71-76` (preselecció), `:102` (viatgen com a `pom_ids`) | UI de subconjunt ja resolta |
| Font de POMs de l'item | `models_app/views.py:949-981` `suggested_poms_view` (`urls.py:205`) — retorna el `GarmentPOMMap` **pla**, sense secció ni part | l'endpoint que hauria de saber de parts |
| Sembra item→model | `models_app/views.py:986-1177` `materialize_poms_view` | vegeu B2: mateix motlle |

**Cap disseny.** Inventari tancat: 12 ancoratges (7 a l'import, 5 a POMs), **0 camins
d'escriptura** de conversió.

| DIMENSIÓ A5 | |
|---|---|
| Fitxers | *cap en aquest sprint* — inventari |
| Talla | **S** (aquest sprint) · una conversió real seria **L** (necessita camí d'escriptura de `garment_set`, re-numeració i les 11 superfícies d'A2) |
| Migració | **NO** |

**Riscos.** (1) `seccio` és dada sense consumidor: si passa un sprint més sense usar-se, torna a
ser candidata a perdre's en un refactor. (2) L'ancoratge principal (`extraction_views.py`,
`ImportWizard.jsx`) és **el fitxer que la sessió paral·lela té obert** (§B4).

**Contradiu?** **Sí, i és la troballa més punxeguda del document.** La decisió 2 diu «conversió
mandrosa (mai preventiva)». Avui **la conversió mandrosa no és possible**: no hi ha cap escriptura
de `garment_set` fora de la creació, `num_pieces` és immutable per docstring, i el número base ja
s'ha gastat. Un model que neix simple **no pot descobrir-se conjunt**. La decisió és coherent com
a política; el que falta és el camí, i no és petit.

---

## A6 · Fitting i grading amb parts

### Fitting: ja ho sap, i amb la forma exacta de (a)

| Peça | Ancoratge | Lectura |
|---|---|---|
| Target XOR | `fitting/models.py:234-244` (FKs) + `CheckConstraint` `:293-301` + `__str__` `:305` | GarmentSet **XOR** Model |
| Programació | `fitting/services.py:133-176` — guard XOR `:147-148`, durada `n = GarmentSet.num_pieces or 1` `:153-155` | 1 sessió per al conjunt |
| **Obrir una peça** | `fitting/services.py:292-341` — `create_piece_fitting(session_id, model_id, *, created_by_id)`; `PieceFitting.objects.create(session=…, model=model, grading_version=version)` `:322`; resol l'SF de treball `:307-313` i la GV activa `:315-320` | **entra per `model_id`**: una part-Model hi encaixa sense cap canvi |
| `PieceFitting` | `fitting/models.py:309-352` — `model` FK a `models_app.Model` `:321-323`, `unique_together ('session','model')` `:349` | una fila per part-Model |
| Línies | `fitting/models.py:355-377` — clona `GradedSpec` a `PieceFittingLine` (`services.py:329-340`) | per part |
| Segellat | `fitting/services.py:665-673` `_seal_session` — el set no es tanca fins que **totes** les peces tenen gate ∈ {OK, EXCEPCIO} (`session_can_advance`, `:652-662`) | ja hi ha porta de conjunt |
| Durada | `fitting/services.py:701` — divideix per `piece_fittings.count()` si hi ha set | ja compta peces |
| API | `fitting/views.py:151` (`filterset_fields` inclou `garment_set`), `:224-238` (XOR al body); serializers `:69-71`, `:117`, `:151`, `:174` | exposat |
| Planificació | `planning/views.py:343`, `:377`, `:395` (`garment_set_id` al payload del calendari) | exposat |

**Veredicte: confirmat. Zero codi nou al fitting.**

### Grading: res llegeix `garment_set` — i la condició per a que sigui gratis

- **Grep de `garment_set`/`piece_number`/`num_pieces` a `pom/`: 0 hits.** El motor
  (`generate_graded_specs`, `pom/services.py`) **no en sap res**. `GradedSpec` és unique per
  `('grading_version','pom','size_label')` (`fitting/models.py:209`) i penja de la
  `GradingVersion` → del `SizeFitting` → **del Model**. Cada part-Model gradua sola.
- **Escalat / GradedSpec: res que llegeixi `garment_set`.** Confirmat pel mateix grep (els únics
  consumidors de `garment_set` són `fitting/`, `planning/`, `models_app/views.py` i els
  serializers del fitting — vegeu la taula d'A2).
- Cada part-Model va al seu contenidor/GTI **si i només si porta el seu propi
  `garment_type_item` i `grading_rule_set`**. Avui **NO**: `create_model_wizard:849` clona un únic
  `garment_fields` a totes les peces (forat #1 d'A4).

> **La frase exacta: A6 és gratis si i només si A4 resol el forat #1.** No hi ha cap altra
> dependència.

| DIMENSIÓ A6 | |
|---|---|
| Fitxers | **cap**, si A4 dona GTI per peça |
| Talla | **S** (verificació + QA, sense codi) |
| Migració | **NO** |

**Riscos.** (1) La base ja anotava 5 criteris distints per a «quin és l'SF d'aquest model»
(components §A3) i `A4`: *dos SFs del mateix model graduarien la MATEIXA base*. Amb 3 parts,
l'exposició a aquests defectes **es multiplica per 3**; no són nous però es fan 3 vegades més
probables. (2) `open_piece` materialitza l'SF en l'acte si no n'hi ha (`services.py:307-313`) →
amb parts, 3 SFs es poden crear per camins diferents.

**Contradiu?** **No.**

---

# SPRINT B — CÒPIA DE POMs model→model

## B1 · Inventari del que es reutilitza

### `clone_model_for_qa` — què copia i què en sobra

`models_app/management/commands/clone_model_for_qa.py` (165 línies):

| Bloc | Línies | Serveix a B2? |
|---|---|---|
| Args (`--schema`, `--source`, `--assignee`, `--recreate`) | `:30-36` | **NO** (management command, no vista) |
| Guard idempotent per `customer + nom_prenda startswith '[QA-SC]'` | `:59-70` | **NO** |
| Clon del Model (`pk=None`, codi regenerat, tag QA, `measurements_version=1`, fase Proto, 4 camps a None) | `:72-88` | **NO** |
| **Còpia de `BaseMeasurement`** | **`:92-96`** | **SÍ — és tot el que serveix** |
| `ModelGradingRule` | `:100-103` | NO |
| SF pel signal + `GradingVersion` + `generate_graded_specs` | `:105-112` | NO |
| Tasca `size_check` | `:114-121` | NO |
| Verificació d'equivalència de grading | `:123-144` | NO (idea útil per a QA) |
| `_purge` (cadena de FKs PROTECT) | `:149-164` | NO |

El nucli reutilitzable, literal (`:92-96`):

```python
for bm in BaseMeasurement.objects.filter(model=src):
    bm.pk = None; bm.id = None
    bm.model = clone
    bm.save()      # F1 registra creació
```

**Semàntica que això implica i que cal decidir a B2:** copia **tots** els camps, incloent-hi
`origen`. Un `MANUAL` copiat arriba al destí dient MANUAL — afirmant que algú el va mesurar en
AQUEST model. Al clon de QA és acceptable (és un clon declarat); a una còpia entre models de
producció **és una mentida d'auditoria**.

Nota addicional: `--source 162` per defecte (`:32`) lliga el command a un golden de PROD-fhort
(deute ja anotat a `MAPA_SISTEMA_EXHAUSTIU.md:1530`). Irrellevant per a B2, que no el reusa.

### El selector de models del frontend

**NO EXISTEIX cap component de selecció de models genèric.** N'hi ha dos ad-hoc, cap reutilitzable
tal qual:

| | Ancoratge | Forma | Genèric? |
|---|---|---|---|
| 1 | `pages/FittingSessionList.jsx:539-600` `FittingNowPicker` | **cerca amb debounce 200ms** + `modelsApi.list({search, page_size:20, ordering:'-data_entrada'})` `:552`; files amb `codi_intern`/`nom_prenda`/`fase_actual` `:588-601` | **NO**: funció interna de la pàgina, no exportada, i **l'acció (`scheduleNow`) està cosida al `pick`** `:559-571` |
| 2 | `components/model/AddModelToGroupModal.jsx` (76 l.) | `<select>` sobre `modelsApi.list({page_size:500})` `:32`; opcions `codi_intern · nom_prenda` `:63-65` | **NO**: component extret, però cablat a `fittingSessions.groupAddModel` `:42` — el picker i l'acte són la mateixa peça |

El precedent de patró de selecció més net del sistema és un altre: **«1 → auto, N → modal»** de la
fitxa tècnica (`TechSheetEditor.jsx:3517-3523`, modal `:5236-5243`), censat a la base
(components §P4.1) com **l'únic del sistema**, i és de SizeFittings, no de Models.

| DIMENSIÓ B1 | |
|---|---|
| Reús real de backend | **~5 línies** de 165 |
| Reús real de frontend | **0 components**; 1 patró (cerca amb debounce) a copiar o extreure |
| Talla | **S** (extreure un `ModelPicker` de `FittingNowPicker`) |

**Risc / mètode.** Copiar el patró una **tercera** vegada xoca amb `CLAUDE.md` («No més pedaços:
unificar el ja construït»). Extreure `ModelPicker` toca `FittingSessionList.jsx` (1.
consumidor viu) → un focus de commit propi.

---

## B2 · Endpoint nou

### Forma mínima

`POST /api/v1/models/<int:model_id>/copiar-poms-de/<int:src_id>/`, registrat a
`models_app/urls.py` al costat de `materialitzar-poms` (`:206`) i `poms-suggerits` (`:205`).

**El motlle exacte a mirar és `materialize_poms_view`** (`models_app/views.py:986-1177`, 190
línies), que ja resol els cinc problemes de B2:

| Problema de B2 | Ja resolt a `materialize_poms_view` |
|---|---|
| Subconjunt de POMs | `pom_ids` opcional al body `:1028-1035`; desconeguts reportats, no ignorats `:1043-1046`, `:1170-1174` |
| Merge no destructiu | **SOBIRANIA DEL MODEL** `:994-996`: sembra només on no hi ha res o hi ha un **TEMPLATE BUIT**; `MANUAL/IMPORTED/FITTED` o amb valor → intocables i comptats a `skipped` `:1122-1136` |
| Forma de resposta | `{materialized, seeded, skipped, total_template}` `:1138-1139` |
| Coherència de talla | **guard P1** `:1071-1092` |
| Atomicitat | `with transaction.atomic():` `:1096` |

### Validacions necessàries

| # | Validació | Fet / ancoratge |
|---|---|---|
| 1 | **Mateix tenant** | **cap codi a escriure**: django-tenants acota per schema de connexió (`views.py:139-141`); un `src_id` d'un altre tenant simplement no existeix. ⚠️ El guard de `public` del ViewSet (`:142-143`) **no té equivalent a les vistes de funció** — `materialize_poms_view:1013-1016` tampoc en té. Exposició **preexistent**, no nova |
| 2 | `src_id != model_id` | **cal escriure-la** (avui no hi ha precedent); si no, la còpia es reescriu a sí mateixa i toca `origen` |
| 3 | Destí buit **o** merge | **la llei de sobirania ja ho respon** (merge no destructiu, `:1122-1136`) → cap decisió nova |
| 4 | Origen amb files | 400, com el `warning` de `:1019-1020` |
| 5 | **Talla base compatible** | **OBLIGATÒRIA i no és al brief.** Transposició directa de `:1071-1092`: `src.base_size_label` vs `dst.base_size_label`; divergents → es copia la **pertinença** (fila `TEMPLATE` buida) i **cap valor**, amb avís explícit. Sense això es reintrodueix el bug que P1 va corregir |
| 6 | `is_active` | copiar només les files `is_active=True` de l'origen (mateix criteri que `base_measurements_view`, `pom/wizard_views.py:312-313`) |

### Cens de què propaga

| Camp | Origen | Nota |
|---|---|---|
| `pom` | `src.pom_id` | la clau. Unicitat destí `('model','pom')` (`models.py:619`) → `update_or_create`/`filter().first()`, com `:1103` |
| `ordre` | `src.ordre` | l'ordre és *"ÚNIC i global del model"* (`views.py:2420`) → copiar-lo és coherent; xoca si el destí ja té files pròpies |
| `tolerancia_minus` / `_plus` | `src` | nullable; els consumidors cauen a 0.6 (`models.py:602-604`) |
| `nom_fitxa` | `src` | `max_length=20` (`:610`) |
| `is_key` | `src` | *"Còpia de la plantilla GarmentPOMMap"* (`:589`) |
| `notes` | `src` | 🚩 text lliure: una nota sobre el model A pot ser falsa al model B |
| **`base_value_cm`** | **paràmetre OPCIONAL** | amb valors → aplica la validació #5 |
| `is_active` | `True` | |
| **`origen`** | **cap valor admissible** | ↓ |

### `BaseMeasurement.origen`: quin valor admet una còpia

`ORIGEN_CHOICES` (`models_app/models.py:571-580`) = `STANDARD`, `IMPORTED`, `MANUAL`, `FITTED`,
`CALCULATED`, `TEMPLATE`, `CHECKED`, `ITEM_STANDARD`. **Cap significa "copiat d'un altre model".**
Tres camins, dimensionats:

| | Camí | Migració | Honest? |
|---|---|---|---|
| a | **`TEMPLATE`** per al cas sense valors | **NO** | **SÍ**: la seva definició literal és *"Materialitzat de plantilla (sense valor encara)"* (`:577`) |
| b | **Valor nou** (p. ex. `COPIED`) per al cas amb valors | **SÍ**, 1 `AlterField` **només de metadades** (Postgres no imposa `choices`; cap reescriptura de taula) | SÍ |
| c | Copiar `src.origen` verbatim (el que fa `clone_model_for_qa:92-96`) | NO | **NO**: un `MANUAL` copiat afirma que algú el va mesurar aquí |

Efectes col·laterals d'un valor nou (camí b), tots menors i **ja precedents**:
- `_ORIGEN_TO_CONTEXT` (`models_app/signals.py:199-205`) no el coneixerà → el `context` del log cau
  al fallback `origen.lower()` (`:273`). **Exactament el forat A6 de la base**, que ja afecta
  `ITEM_STANDARD`, `TEMPLATE` i `CHECKED`.
- `MeasurementChangeLog.context` és `CharField(max_length=50)` **sense `choices`**
  (`models_app/models.py:646`) → `'copied'` hi entra sense migració.
- **Cada valor copiat genera una fila de log** (`signals.py`, post_save: `created` + valor no
  `None` → escriu). Desitjable com a auditoria, però són N files per còpia; l'`atomic` les inclou.
- L'import esborra en DUR les files sense valor d'origen `TEMPLATE`/`ITEM_STANDARD`
  (`extraction_views.py:2362-2364`) i SOFT la resta: un `COPIED` sense valor cauria a la branca
  SOFT. Coherent, però s'ha de saber.

| DIMENSIÓ B2 | |
|---|---|
| Fitxers backend | `models_app/views.py` (1 vista ~80-110 l., mirall de `:986-1177`), `models_app/urls.py` (1 línia) · +`models_app/models.py`+migració **només** amb el camí (b) |
| Fitxers frontend | `api/endpoints.js` (1 línia) |
| Talla | **S/M** |
| Migració | **NO** amb (a)/(c) · **SÍ** (metadades) amb (b) |

**Riscos.** (1) Ometre la validació #5 (talla) reintrodueix un bug ja corregit. (2) Copiar `ordre`
sobre un destí amb files pròpies barreja dos ordres globals. (3) `notes` copiades = afirmacions
sobre un altre model. (4) `POMMaster` és FK PROTECT compartida (`models.py:583`): copiar la
pertinença no duplica cap POM del catàleg — **no hi ha risc de contaminació de catàleg** (verificat).

**Contradiu?** **No.** Sprint B és ortogonal a les 4 decisions del SET.

---

## B3 · Punt d'UI: l'estat buit de Mesures

### Els components exactes

| Peça | Ancoratge | Detall |
|---|---|---|
| **Caixa d'estat buit** | `pages/ModelSheet.jsx:458-480` | caixa `dashed`; títol `model_sheet.measures_empty_title` `:468`, cos `…_body` `:470`, **un únic botó** `model_sheet.start_pom` `:472-478` → `enterEdit('Mesures','pom')` |
| Condició que l'ensenya | `ModelSheet.jsx:459` | `(!taskParam && editing !== 'Mesures' && !pomReady)` |
| **El panell que és el propietari real de la gènesi** | `components/model/MeasuresEntryPanel.jsx` | muntat a `ModelSheet.jsx:455-458`; docstring `:12-19`: cobreix `(a) cas BUIT → selector (manual/import)`, `(b) seed des de GTI`, `(c) import` |
| `mode` | `MeasuresEntryPanel.jsx:26` | `'loading' | 'selector' | 'manual' | 'import'` ← **la 3a branca hi entra** |
| Patró confirmar-abans-d'escriure | `:96-111` (`confirmSeed`) + llei F2.1 `:161-166` | *"la sembra és un ACTE DEL TÈCNIC, mai un efecte de muntatge"* |
| Chips de subconjunt (→ `pom_ids`) | `:30`, `:71-76`, `:102` | mapeja 1:1 amb el paràmetre de l'endpoint B2 |
| Recàrrega post-escriptura | `:88-91` (`reloadTable`) + `onMaterialized` (`ModelSheet.jsx:456`) | ja fa `exitEdit + reloadTaula + reloadModel` |

### Cost d'afegir-hi l'acció

1. Tercera targeta al `selector` de `MeasuresEntryPanel` («Copiar POMs d'un altre model»).
2. Modal amb el **ModelPicker** (extret de `FittingNowPicker`, §B1) → tria de model origen.
3. Reús dels chips existents per triar quins POMs (`:71-76`) i d'un `<input type=checkbox>` per
   «copiar també els valors base».
4. Confirmació (mateix patró que `confirmSeed`) + `reloadTable('manual')`.
5. Opcional: segon botó a la caixa buida de `ModelSheet.jsx:472-478`.

| DIMENSIÓ B3 | |
|---|---|
| Fitxers | `components/model/MeasuresEntryPanel.jsx` (principal), `components/model/ModelPicker.jsx` (nou o extret), `pages/FittingSessionList.jsx` (només si s'extreu), `pages/ModelSheet.jsx` (només si la caixa buida guanya botó), `api/endpoints.js`, `i18n/{ca,en,es}.json` |
| i18n | ~6-8 claus **× 3 fitxers** (3987 línies cadascun; paritat estricta ca/en/es per `CLAUDE.md`) |
| Talla | **M** |
| Migració | **NO** |

**Riscos.** (1) `MeasuresEntryPanel` ja té 5 estats i 3 camins de gènesi; una 4a via el fa un
commutador. (2) La caixa buida de `ModelSheet.jsx:458-480` i el `selector` del panell són **dues**
superfícies de "buit" — afegir l'acció només a una deixa mig camí (i afegir-la a les dues és el
pedaç que `CLAUDE.md` prohibeix). (3) Icones Tabler **outline** i colors per token, mai hex.

---

## B4 · Col·lisions amb el sprint d'import EN CURS

### Estat de la sessió paral·lela (llegit ara)

**Commitat** (avui): `73bbd2cb` (409 codi duplicat), `fd23f6d3` (wizard llegeix el 409),
`efdc08ac` (F2 talla base del DOCUMENT), `c443f79a` (F3 traceback a fitxer), `95dee480` (F4 secció).

**NO commitat — arbre de treball SUCIÓS ara mateix:**
```
 M backend/fhort/models_app/extraction_views.py   (+120 −22)
 M backend/fhort/models_app/test_parser_excel.py  (+147)
```
Contingut del diff (F5): cens de fulls que passen la porta, tria `full_seleccionat` desada a
`run_conciliat`, informe de fulls pels dos camins, `_avis_files_perdudes`. **És la fila §15 de la
base DALIA, en construcció.**

### Fitxers que els dos sprints tocarien alhora

| Fitxer | Sprint B el toca? | Import en curs el toca? | Col·lisió |
|---|---|---|---|
| `models_app/extraction_views.py` | **NO** | **SÍ (obert ara)** | — |
| `models_app/extraction_prompt.py` | NO | SÍ (F4) | — |
| `models_app/test_parser_excel.py` | NO | **SÍ (obert ara)** | — |
| `models_app/test_import_poms_duplicats.py` | NO | SÍ (F1) | — |
| `models_app/views.py` | **SÍ** (vista nova) | NO (F1-F5 no l'han tocat) | — |
| `models_app/urls.py` | **SÍ** (1 línia) | NO | — |
| `components/ImportWizard/ImportWizard.jsx` | NO | **SÍ** (F5 necessita tria de full) | — |
| **`frontend/src/api/endpoints.js`** | **SÍ** | **SÍ** (F5: tria de full) | **⚠️ SÍ** |
| **`i18n/ca.json`** | **SÍ** | **SÍ** | **⚠️ SÍ** |
| **`i18n/en.json`** | **SÍ** | **SÍ** | **⚠️ SÍ** |
| **`i18n/es.json`** | **SÍ** | **SÍ** | **⚠️ SÍ** |

**Col·lisió real de Sprint B = 4 fitxers, tots de frontend, tots additius** (línies noves en llocs
diferents del fitxer). **Zero solapament de Python.**

**Col·lisió de Sprint A = molt més gran, i és A5:** els ancoratges d'A5 **són**
`extraction_views.py` + `ImportWizard.jsx`, exactament els fitxers oberts. Mentre A5 sigui
inventari (§A5, DIMENSIÓ: cap fitxer) no hi ha xoc; **una implementació d'A5 ha d'esperar que F5
aterri.**

**Mètode** (memòria `ftt-dev-concurrent-git`): `dev` té sessions concurrents que poden amendar
commits. `git add` de **paths explícits**, mai `-A`/`-u`; `git log -1` després de cada commit.

---

# TAULA FINAL DE DIMENSIONAT

| Bloc | Fitxers a tocar | Talla | Migració | Contradiu una decisió fixada? |
|---|---|---|---|---|
| **A1** camp SET al GTI | 7 backend + 3 frontend | **S** (M2M nu) / **M** (taula o `through`) | **SÍ** ×1, additiva, cap backfill | No |
| **A2** parts com a Models: superfícies | 6 backend + 8 frontend | **L** (les dues formes) | **NO** | Tensió: el codi comercial viu a una fila que no és Model; la federació dissol el conjunt |
| **A3** meritació set=1 | 2 (o 3 amb migració) | **S/M** (i,ii) · **M** (iii) | **NO** (i,ii) · **SÍ** (iii) | **SÍ**: `code_snapshot` de l'albarà nomenaria una PART |
| **A4** creació | 1 backend + 2 frontend | **S** backend · **M** frontend | **NO** | No (però hi ha 2 fonts per a "és un conjunt") |
| **A5** conversió mandrosa | *cap* (inventari) | **S** ara · **L** implementada | **NO** | **SÍ**: avui la conversió mandrosa **no té camí d'escriptura** |
| **A6** fitting/grading | **cap** si A4 dona GTI per peça | **S** | **NO** | No |
| **B1** inventari de reús | — | **S** (extreure `ModelPicker`) | **NO** | No |
| **B2** endpoint de còpia | 2 backend (+1 amb migració) + 1 frontend | **S/M** | Només amb un `origen` nou (metadades) | No |
| **B3** punt d'UI | 4-6 frontend + i18n×3 | **M** | **NO** | No |
| **B4** col·lisions | 4 compartits (tots frontend) | — | — | — |

### Les tres decisions que aquest document deixa a la taula (no les pren)

1. **A1** — M2M nu vs taula pròpia. **Fet que hi pesa:** un M2M automàtic **no pot** portar `ordre`
   ni `nom_peca`, i A4 («amb nom per peça») els demana tots dos. Amb `through` per portar-los, les
   dues formes convergeixen.
2. **A2** — amagar (α) vs agrupar (β). **Fet que hi pesa:** α necessita una **font de files** per
   al conjunt que avui no existeix (`GarmentSet` no té fase/prioritat/responsable); β fa que **tot
   el que compta, compti 3**, inclosa la selecció per filtre del bulk.
3. **A3** — (i) germanes NULL / (ii) germanes estampades i un sol albarà / (iii) ancorar a
   `GarmentSet`. **Fet que hi pesa:** `ConsumptionRecord.model` és **OneToOne**, i (i)/(ii) fan que
   l'albarà del client porti el codi d'una peça interna.

---

## Límits d'aquest dimensionat

- **Arbre de treball SUCIÓS.** `extraction_views.py` i `test_parser_excel.py` tenen canvis no
  commitats d'una sessió paral·lela. Les línies que en cito del diff (F5, tria de full) **es poden
  desplaçar o revertir**; les de `95dee480` (F4, `seccio`) són fermes.
- **No he executat cap import, cap crida a la IA, cap `migrate`, cap escriptura.** L'única cosa
  executada contra la BD són **COUNTs de lectura** (cens de `GarmentSet`/`Model`/`GTI`/`BaseMeasurement`
  a `fhort` i `los`).
- **Les talles S/M/L són de superfície tocada, no d'hores.** Un **L** aquí vol dir "travessa ≥6
  fitxers i ≥2 contractes de dades", no "difícil".
- **`_load_base_measurements`** (`pom/services.py`, zona intocable per `CLAUDE.md`) **no s'ha
  obert**. No cal per a cap dels dos sprints: amb parts com a Models, la clau `(model, pom)` es
  manté intacta i el motor no canvia. Si algun dia es tria la Proposta P2-B de la base (dimensió
  dins `BaseMeasurement`), aquest dimensionat **no hi serveix**.
- **No he vist el xlsx de DALIA** (mateix límit que la base): les dues formes de document
  multi-peça (seccions dins d'un full / un full per peça) estan inferides del codi.
- `frontend/src/components/EditableTable/` no auditat fila a fila (mateix límit obert de la base).
