# CENS DE PODA — PLATAFORMA

> **Data:** 2026-08-17 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev` (`f0c99481`).
> **Abast:** mesurar la brossa acumulada i mapar-la contra el pla G de `DECISIONS.md:837-839`.
> **NO s'ha podat res.** Cap fitxer modificat, cap escriptura a BD, cap worktree.
>
> Convenció: tota afirmació porta `fitxer:línia`. **«NO EXISTEIX» = confirmat absent al codi**,
> no especulat. Les propostes van marcades `💡 PROPOSTA (a validar)`. Grups G segons
> `DECISIONS.md:837-839` (G2 estat del model · G3 import vell · G4 POM-editor vell + òrfenes ·
> G5 codi mort transversal · G8 higiene frontend); el que no hi encaixa va marcat
> **«fora de mapa, decisió Agus»**.

---

## RESUM EXECUTIU

1. **La brossa d'aquesta plataforma NO és accidental: és declarada.** Els 5 casos del patró B4
   (funcions vives només per bancs) porten **acta al lloc de la ruta**, amb data i motiu. El cens
   no ha trobat cap vista òrfena silenciosa: **0 de 146 `*_view` sense ruta ni acta**.
2. **El risc de runtime és quasi nul.** De 21 ítems censats, **1** és abastable per un client
   (un GET read-only sense consumidor) i **cap** pot corrompre dades. La resta és **pes mort inert**.
3. **El cost de poda NO és esborrar: és RE-ALLOTJAR LLEIS.** `escalat_ajustar_talla_view` és el
   vehicle de **8 bancs** que proven lleis VIVES (segell G6, guarda de rang, escriptura per
   germanes C4, conservació STEP, F1 garment). Podar-la sense donar-los un altre vehicle és
   perdre la cobertura, no netejar.
4. **Dues coses que semblen brossa i no ho són**, i el cens les treu de la llista: `discovery.*`
   (11 claus i18n + backend viu) és una **feina inacabada al 90%**, i les 2 bessones
   `longitud*` del motor de patrons són **zona intocable** pel brief.
5. **La i18n està sana**: paritat ca/en/es **perfecta** (0 falten, 0 sobren) i les 14 claus noves
   d'E1 **no** són òrfenes. Les 89 òrfenes reals són **1,9%** de 4.617.
6. **`MOCK_*` / dades falses residuals: 0.** Confirmat absent.
7. 🚨 **Un deute datat s'ha mesurat MÉS PETIT del que deia la meva pròpia acta**: de
   `_load_grading_rules` queden **2 boques**, no 4 (§C4.3). I un altre ja està **tancat** (el
   rètol del segell, §C4.5).

---

## ⚠️ MÈTODE — TRES TRAMPES DE MESURA (llegir abans de refer aquest cens)

Aquestes tres em van donar **xifres falses** abans d'arribar a les bones. Consten perquè qui
repeteixi el cens no les torni a pagar:

| Trampa | Xifra falsa | Xifra real | Per què |
|---|---|---|---|
| Buscar el nom de la vista al **text sencer** de `urls.py` | **0** sense ruta | 5 | Una vista jubilada segueix **citada a l'`import`** (`# noqa: F401`) i als comentaris de l'acta. |
| Buscar només línies amb `path(` | **54** sense ruta | 5 | `tasks/urls.py` registra amb **àlies** (`_path_b(...)`, `_path3(...)`) i els `path()` són **multilínia**. |
| Buscar imports `from '...'` al front | **58** components orfes | 14 | Les `pages/*` es carreguen amb **`lazy(() => import(...))`**. |

**La mesura bona**: treure comentaris **i blocs d'import** de cada `urls.py` i buscar a la resta;
al front, cobrir import estàtic **i** dinàmic. Els `bulk_import_views` són **fals positiu** fins i
tot així, perquè es registren amb `as` ([models_app/urls.py:156-166](../../backend/fhort/models_app/urls.py#L156-L166)).

---

## BLOC C1 — CODI MORT BACKEND

### C1.1 · El patró B4: vistes sense ruta, vives per als bancs (5)

Cap és accidental: **totes cinc porten acta al lloc de la ruta**.

| Vista | Def | Acta | Bancs que la fan servir |
|---|---|---|---|
| `escalat_ajustar_talla_view` | [views.py:3327](../../backend/fhort/models_app/views.py#L3327) | **E1/B4, avui** ([urls.py:237-253](../../backend/fhort/models_app/urls.py#L237)) | **8**: `test_e1_presa_escalat`, `test_g6_segell`, `test_guarda_rang_mesura`, `test_arestes_tea205`, `test_step_conserva_valors`, `test_set2_f1_write_base_garment`, `test_base_stages_no_regressio`, `test_c4_escriptura_germanes` |
| `set_size_override_view` | [views.py:3196](../../backend/fhort/models_app/views.py#L3196) | **D5 · 21/07** ([urls.py:236](../../backend/fhort/models_app/urls.py#L236)) | 1: `test_g6_segell` |
| `close_base_view` | [pom/grading_views.py:12](../../backend/fhort/pom/grading_views.py#L12) | **D5 · 21/07** ([tasks/urls.py:130-135](../../backend/fhort/tasks/urls.py#L130)) | 1: `test_g6_segell` |
| `regenerate_sizes_view` | [pom/grading_views.py:35](../../backend/fhort/pom/grading_views.py#L35) | **D5 · 21/07** (idem) | 1: `test_g6_segell` |
| `confirm_base_size_view` | [pom/wizard_views.py:487](../../backend/fhort/pom/wizard_views.py#L487) | **D5** ([models_app/urls.py:121-122](../../backend/fhort/models_app/urls.py#L121)) | 1: `test_g6_segell` |

**FET:** sense ruta, **cap client hi arriba**. El `# noqa: F401` de
[models_app/urls.py:18](../../backend/fhort/models_app/urls.py#L18) existeix precisament per
mantenir-les importables.

**El cost real de podar-les** no és esborrar la funció: és que **12 fitxers de banc perden el seu
vehicle**. `test_g6_segell` les exercita com «els sis camins» del segell — una llei VIVA.

### C1.2 · Serializers sense cap consumidor de producció (3 de 120)

| Serializer | On | Qui el referencia | Nota |
|---|---|---|---|
| `UserProfileSerializer` | [accounts/serializers.py:100](../../backend/fhort/accounts/serializers.py#L100) | **CAP** (ni prod ni bancs) | Substituït per `UserAdminSerializer`, just a sota ([:113](../../backend/fhort/accounts/serializers.py#L113)) |
| `ContracteSerializer` | [models_app/serializers.py:214](../../backend/fhort/models_app/serializers.py#L214) | **CAP** | `fields='__all__'` |
| `LiniaContracteSerializer` | [models_app/serializers.py:220](../../backend/fhort/models_app/serializers.py#L220) | **CAP** | `fields='__all__'` |

Cap referència per **string** (`'UserProfileSerializer'`) — comprovat, **NO EXISTEIX**.

### C1.3 · El clúster `Contracte` — el contracte ANTERIOR, sencer i buit

| Peça | On | Estat mesurat |
|---|---|---|
| Model `Contracte` | [models_app/models.py:14](../../backend/fhort/models_app/models.py#L14) | **0 files** (`fhort` i `los`) |
| Model `LiniaContracte` | [models_app/models.py:29](../../backend/fhort/models_app/models.py#L29) | **0 files** |
| FK `Model.contracte` | [models_app/models.py:277-283](../../backend/fhort/models_app/models.py#L277) | **0 de 31 models** el tenen |
| FK `Model.linia_contracte` | [models_app/models.py:284-290](../../backend/fhort/models_app/models.py#L284) | **0 de 31** |
| Els 2 serializers | §C1.2 | sense consumidor |

**El substitut viu**: `backoffice.TenantContract` ([backoffice/models.py:236](../../backend/fhort/backoffice/models.py#L236))
+ `ContractLine` ([:283](../../backend/fhort/backoffice/models.py#L283)). Són app de **`public`
només** ([settings.py:57](../../backend/fhort/settings.py#L57)) — `fhort.backoffice_tenantcontract`
**NO EXISTEIX**, verificat.

⚠️ Podar-lo **exigeix migració** sobre `models_app_model` (dues columnes FK).

### C1.4 · Models orfes amb taula buida (2)

| Model | On | Referències | Files |
|---|---|---|---|
| `POMEstadisticaGlobal` | [pom/models.py:338](../../backend/fhort/pom/models.py#L338) | **CAP** enlloc | **0** (`fhort`·`los`·`public`) |
| `POMEstadisticaTenant` | [pom/models.py:480](../../backend/fhort/pom/models.py#L480) | **CAP** enlloc | **0** |

`_POMMapBase` ([pom/models.py:933](../../backend/fhort/pom/models.py#L933)) surt al detector però és
**`abstract = True`** ([:961](../../backend/fhort/pom/models.py#L961)) → **fals positiu**, no és brossa.

### C1.5 · Seeds i one-shots consumits (35 de 77)

| Categoria | N | Nota |
|---|---|---|
| one-shot (`fix_*`·`backfill_*`·`migra_*`·`reseed_*`·`delete_*`) | **11** | feina feta per definició |
| `seed_*` / `sembra_*` | **24** | sembres de tenant/catàleg ja aplicades |
| altres (eines recurrents) | 42 | **NO són brossa** |

**Sense CAP citació enlloc** (ni docs, ni `ops/`, ni cron, ni codi): només **2** —
`qa_set2_forats` i `fusiona_pom_duplicat`. La resta estan documentats, o sigui que **la poda és
una decisió de cicle de vida, no de descobriment**.

### C1.6 · `Response({...})` literals (705 a producció)

**26** emeten claus d'**identitat de mesura** sense passar per serializer — la família que aquesta
casa ja ha pagat tres vegades:

| Fitxer:línia | Claus emeses |
|---|---|
| [models_app/views.py:5030](../../backend/fhort/models_app/views.py#L5030), [:5039](../../backend/fhort/models_app/views.py#L5039) | `capa`·`instancia`·**`garment`** ✅ (F1, els 3 eixos) |
| [extraction_views.py:3081](../../backend/fhort/models_app/extraction_views.py#L3081), [:3135](../../backend/fhort/models_app/extraction_views.py#L3135) | `pom_id`·`garment` |
| [views.py:5219](../../backend/fhort/models_app/views.py#L5219), [:5227](../../backend/fhort/models_app/views.py#L5227), [extraction_views.py:906](../../backend/fhort/models_app/extraction_views.py#L906), [:3682](../../backend/fhort/models_app/extraction_views.py#L3682) | `garment` |
| 8× [pom/wizard_views.py](../../backend/fhort/pom/wizard_views.py) (349·357·802·807·812·821·850), [views.py:1300](../../backend/fhort/models_app/views.py#L1300)·[:1305](../../backend/fhort/models_app/views.py#L1305)·[:3306](../../backend/fhort/models_app/views.py#L3306)·[:3313](../../backend/fhort/models_app/views.py#L3313)·[:4930](../../backend/fhort/models_app/views.py#L4930)·[:4940](../../backend/fhort/models_app/views.py#L4940), [s6_views.py:49](../../backend/fhort/pom/s6_views.py#L49), [size_map_views.py:665](../../backend/fhort/pom/size_map_views.py#L665), [translation_views.py:41](../../backend/fhort/pom/translation_views.py#L41), 2× [pom_placement_views.py](../../backend/fhort/models_app/pom_placement_views.py) | `pom_id` sol |

💡 **PROPOSTA (a validar)**: no són poda —són **superfície de risc**. Els 4 que emeten `garment`
ja hi han entrat; els 8 de `wizard_views` són del **POM-editor vell (G4)** i cauran amb ell.

### Veredicte C1: **llest per decidir.** 0 vistes òrfenes silencioses · 5 amb acta · 7 peces de domini buides.

---

## BLOC C2 — CODI MORT FRONT

### C2.1 · Components sense cap import (14 de 195) — **2.516 línies**

Cap referenciat per bancs.

| Component | Línies | Nota |
|---|---|---|
| [pages/TechSheetTemplateEditor.jsx](../../frontend/src/pages/TechSheetTemplateEditor.jsx) | 442 | ⚠️ veí de `TechSheetEditor` (**NO TOCAR** pel brief) |
| [pages/ItemAuthoring.jsx](../../frontend/src/pages/ItemAuthoring.jsx) | 429 | **declarat substituït** per `CatalegPecesItem` ([App.jsx:61](../../frontend/src/App.jsx#L61), [:483](../../frontend/src/App.jsx#L483)) |
| [components/SizeSetDetail.jsx](../../frontend/src/components/SizeSetDetail.jsx) | 383 | |
| [components/SizingProfileSelector.jsx](../../frontend/src/components/SizingProfileSelector.jsx) | 378 | |
| [components/POMBrowser/POMCatalogue.jsx](../../frontend/src/components/POMBrowser/POMCatalogue.jsx) | 187 | |
| [components/model/PromoteToItemButton.jsx](../../frontend/src/components/model/PromoteToItemButton.jsx) | 131 | **òrfena AMB ACTA**: [CheckMeasureEditor.jsx:725](../../frontend/src/components/model/CheckMeasureEditor.jsx#L725) diu que es conserva «a posta» |
| [components/model/ProductionTab.jsx](../../frontend/src/components/model/ProductionTab.jsx) | 118 | |
| [components/SessioActiva.jsx](../../frontend/src/components/SessioActiva.jsx) | 89 | |
| [components/model/RuleSetCard.jsx](../../frontend/src/components/model/RuleSetCard.jsx) | 78 | |
| [components/EstatBadge.jsx](../../frontend/src/components/EstatBadge.jsx) | 74 | 🔗 candidat **G2** (estat del model) |
| [components/ui/TimerWidget.jsx](../../frontend/src/components/ui/TimerWidget.jsx) | 62 | |
| [components/model/TaskLog.jsx](../../frontend/src/components/model/TaskLog.jsx) | 61 | |
| [components/model/FittingTab.jsx](../../frontend/src/components/model/FittingTab.jsx) | 46 | ja constava a [[ftt-cens-ui-pendent]] |
| [components/HTMTooltip.jsx](../../frontend/src/components/HTMTooltip.jsx) | 38 | |

### 🚨 C2.2 · Una acta FALSA trobada de passada

[CheckMeasureEditor.jsx:723-725](../../frontend/src/components/model/CheckMeasureEditor.jsx#L723) diu:

> «El candidat natural és la fitxa de l'ITEM (`ItemAuthoring`), que és l'única pantalla que ja
> edita el catàleg i **que avui només s'obre des de `GarmentTypes`**»

**Totes dues meitats són falses avui**: `ItemAuthoring` està **retirat de rutes**
([App.jsx:61](../../frontend/src/App.jsx#L61)) i `GarmentTypes` navega a `/cataleg-peces`
([GarmentTypes.jsx:316](../../frontend/src/pages/GarmentTypes.jsx#L316), [:336](../../frontend/src/pages/GarmentTypes.jsx#L336)),
no a `ItemAuthoring`. És el patró dels **docstrings datats i FALSOS**: una acta que orienta el
proper sprint cap a una pantalla morta.

### C2.3 · `MOCK_*` i dades falses: **0** ✅
`MOCK_`·`mockData`·`FAKE_`·`DUMMY_`·`TODO_REMOVE` a `frontend/src` (fora de bancs): **NO EXISTEIX**.

### C2.4 · Rutes sense enllaç: **2, i totes dues falsos positius**

| Ruta | Veredicte |
|---|---|
| `/reset-password/:uid/:token` | **VIVA** — deep-link des del correu, no hi ha d'haver `<Link>` |
| `models/nou-des-de-fitxer` | **VIVA** — és un `<Navigate to="/models/nou" replace />` de compatibilitat ([App.jsx:449](../../frontend/src/App.jsx#L449)) |

### C2.5 · Claus i18n òrfenes: **89 de 4.617 (1,9%)**

Definició estricta: no apareix **literal** al codi **ni** hi ha el seu prefix viu (per descartar
les dinàmiques `t(\`${pre}.${x}\`)`). Amb el criteri fluix serien 904; **815 d'aquestes són
dinàmiques i NO són òrfenes**.

| Prefix | N | Grup G |
|---|---|---|
| `measurement_table.*` | **31** | **G4** (POM-editor vell) |
| `discovery.*` | **11** | ⚠️ **fora de mapa** — v. C2.6 |
| `model.*` | 10 | G8 |
| `garment_selector.*` | 8 | G8 |
| `fitting.gate.*` | 7 | G8 |
| `measurements_chat.*` | 5 | G8 |
| `size_map_*` (14 prefixos d'1 clau) | 14 | G8 |
| `graduacio.confirma.*` | 2 | G8 |
| `graduacio.superficie.col_origen` · `origen_joc` · `origen_model` | **3** | **G8** — v. l'addenda de sota |

### ➕ ADDENDA S45/G3 (2026-08-21) — la columna «Ve de» s'ha retirat, les claus NO

`GraduacioSuperficie` ja no pinta la columna «Ve de» (capçalera, cel·la i el `delJoc` que la
calculava). Les seves 3 claus × 3 idiomes queden **òrfenes i s'anoten aquí en lloc de podar-se
en calent**, per la llei S43: una clau i18n no es pot donar per morta amb un `grep` del literal
—les dinàmiques `t(`${pre}.${x}`)` no hi surten— i aquest cens és l'únic lloc que en sap
distingir les òrfenes REALS de les que només ho semblen.

⚠️ **NO CONFONDRE amb les seves homònimes, que són VIVES**: `grading.jocs.col_origen`
([JocsDeRegles.jsx:1151](../../frontend/src/components/grading/JocsDeRegles.jsx#L1151)) i
`comprovacio.col_origen`
([ComprovacioPanel.jsx:362](../../frontend/src/components/model/ComprovacioPanel.jsx#L362)).
Són claus DIFERENTS amb el mateix últim segment: podar per sufix se les enduria.

Els camps del payload (`regla_origen`, `regla_es_resident`,
[models_app/views.py:2163-2164](../../backend/fhort/models_app/views.py#L2163)) **es queden**:
són additius i tenen altres lectors potencials; retirar-los seria un segon tram.

✅ **Les 14 claus `escalat.*` d'E1 NO són òrfenes** (confirmat: 0 de 14).
✅ **Paritat ca/en/es perfecta**: 0 falten, 0 sobren, als tres fitxers.

### C2.6 · `discovery.*` NO és brossa: és feina inacabada

- Backend **VIU**: [tenants/views_discovery.py](../../backend/fhort/tenants/views_discovery.py) amb contracte documentat.
- i18n **complet** als 3 idiomes (11 claus).
- Front: **0 usos**, i [Entrar.jsx:175](../../frontend/src/pages/Entrar.jsx#L175) ho diu explícitament
  («la peça de backend hi és (discovery) però…»).

💡 **PROPOSTA (a validar)**: **no podar.** Podar les claus destruiria la meitat feta d'una
funcionalitat que només li falta el cablejat de front. Decisió d'Agus: **acabar-la o retirar-la
sencera**, mai a mitges.

### Veredicte C2: **llest.** 14 components (2.516 línies) · 89 claus · 0 mocks · i18n sana.

---

## BLOC C3 — DUPLICACIONS

### C3.1 · Bessones front/back (5): **3 declarades, 2 no**

| Llei | Front | Back | Estat |
|---|---|---|---|
| `liniaTeContingut` / `linia_te_contingut` | [taulaPresaPerTalla.js:43](../../frontend/src/utils/taulaPresaPerTalla.js#L43) | [fitting/esdeveniments.py:28](../../backend/fhort/fitting/esdeveniments.py#L28) | ✅ **DECLARADA** (bessona legal, es citen mútuament) |
| `documentToV2` / `document_to_v2` | [TechSheetEditor.jsx:679](../../frontend/src/pages/TechSheetEditor.jsx#L679) | [services_ftt.py:276](../../backend/fhort/models_app/services_ftt.py#L276) | ✅ **DECLARADA** |
| `v2ToDocument` / `v2_to_document` | [TechSheetEditor.jsx:699](../../frontend/src/pages/TechSheetEditor.jsx#L699) | [services_ftt.py:254](../../backend/fhort/models_app/services_ftt.py#L254) | ✅ **DECLARADA** |
| `longitudVora` / `longitud_vora` | [patternGeometry.js:98](../../frontend/src/components/pattern/patternGeometry.js#L98) | [patterns/engine/segments.py:57](../../backend/fhort/patterns/engine/segments.py#L57) | 🚨 **NO declarada** |
| `longitudTram` / `longitud_tram` | [patternGeometry.js:117](../../frontend/src/components/pattern/patternGeometry.js#L117) | [patterns/engine/segments.py:100](../../backend/fhort/patterns/engine/segments.py#L100) | 🚨 **NO declarada** |

⚠️ Les dues no declarades són **al motor de patrons / traçadora** → **zona intocable pel brief**.
Es reporten i **no es toquen**. **fora de mapa, decisió Agus.**

### C3.2 · Endpoints que fan el mateix (2 parells)

| Nom duplicat | A | B | Consumidor front |
|---|---|---|---|
| `measurements_table_view` | [models_app/views.py:1982](../../backend/fhort/models_app/views.py#L1982) `models/<id>/taula-mesures/` | [pom/grading_views.py:106](../../backend/fhort/pom/grading_views.py#L106) `size-fittings/<sf_id>/taula-mesures/` | **només A**. De B: **CAP** (grep exhaustiu a `frontend/src`) |
| `suggested_poms_view` | [models_app/views.py:1296](../../backend/fhort/models_app/views.py#L1296) `models/<id>/poms-suggerits/` | [pom/wizard_views.py:62](../../backend/fhort/pom/wizard_views.py#L62) `poms/suggerits/` | **només A** |

**FET sobre B de la primera**: està **ROUTADA i sense consumidor**
([tasks/urls.py:138](../../backend/fhort/tasks/urls.py#L138)), però és
**`@api_view(['GET'])` read-only** ([grading_views.py:104-105](../../backend/fhort/pom/grading_views.py#L104)) →
**no pot escriure res**. És l'**únic ítem del cens abastable per un client**.

### Veredicte C3: **llest.** 2 bessones no declarades (intocables) · 2 endpoints duplicats, un routat sense consumidor.

---

## BLOC C4 — DEUTES DATATS: CONFIRMACIÓ D'ESTAT

| # | Deute | Estat mesurat avui |
|---|---|---|
| 1 | **`test_parser_excel` ×2** (de `b7251589`) | 🔴 **SEGUEIX VERMELL.** Els mocks són `lambda files, customer` (2 args) a [test_parser_excel.py:511](../../backend/fhort/models_app/test_parser_excel.py#L511) i [:539](../../backend/fhort/models_app/test_parser_excel.py#L539); producció crida `_match_rows(raw_poms, import_customer, session.model)` (3) a [extraction_views.py:1641](../../backend/fhort/models_app/extraction_views.py#L1641). **La suite de `models_app` no és verda.** |
| 2 | **`EditableTable` família de 3** | 🚩 **OBERTA.** `germanesDeLEix` [:666](../../frontend/src/components/EditableTable/EditableTable.jsx#L666) filtra per `pom_id`+`capa` **sense `garment`**; també `capesLliuresDe` [:413](../../frontend/src/components/EditableTable/EditableTable.jsx#L413) i `germanaCapaRapida` [:476](../../frontend/src/components/EditableTable/EditableTable.jsx#L476). Correctes **només** perquè el cridador passa les files ja partides. |
| 3 | **«4 boques» de `_load_grading_rules`** | ✅ **EN QUEDEN 2, NO 4** — correcció d'una xifra meva. Boques reals: [graded_spec_views.py:171](../../backend/fhort/fitting/graded_spec_views.py#L171) i [serializers_size_check.py:97](../../backend/fhort/models_app/serializers_size_check.py#L97). Les altres dues que la meva acta comptava (`pom/views.py`, `wizard_views.py`) **només la citen en comentaris**. |
| 4 | **W5 · overrides orfes** | 🟡 **LATENT, no materialitzat.** L'escriptor viu és [extraction_views.py:3544](../../backend/fhort/models_app/extraction_views.py#L3544) i, des d'E1/B4, **cap superfície els pot editar**. A la BD: **2 overrides en total**, i tots dos són d'una sembra QA (`motiu = 'QA SET-2 · cobertura de paritat'`), **cap de W5**. |
| 5 | **Rètol de segell inassolible (B3)** | ✅ **JA TANCAT.** E1/B3 el va **retirar amb acta** ([PropagatedEditor.jsx:172-180](../../frontend/src/pages/PropagatedEditor.jsx#L172)): «un rètol que no pot sortir és pitjor que no tenir-ne». El gest viu a «Propagar a grading». |
| — | **G5 acumulat: maquinària de temps del fitting** | 🟡 `DECISIONS.md:1515` diu «**0 files**». Avui `fhort.fitting_fittingdurationstat` té **1 fila**: l'escriptor ([fitting/services.py:1039](../../backend/fhort/fitting/services.py#L1039)) **està actiu** i segueix sense lector. |

### Veredicte C4: 2 tancats o reduïts · 2 oberts · 1 vermell heretat que trenca una porta.

---

## BLOC C5 — TAULA FINAL, ORDENADA PER RISC

**Premissa de risc de `DECISIONS.md:835-836`**: el deploy sobreescriu PROD (versió antiga, sense
clients reals) → els antics «riscos de dades a PROD» són, com a molt, correcció de lògica.

| # | Ítem | On | Qui el referencia | G | RISC | Cost de poda amb banc |
|---|---|---|---|---|---|---|
| 1 | **`test_parser_excel` ×2 vermells** | [test_parser_excel.py:511](../../backend/fhort/models_app/test_parser_excel.py#L511)·[:539](../../backend/fhort/models_app/test_parser_excel.py#L539) | producció a [extraction_views.py:1641](../../backend/fhort/models_app/extraction_views.py#L1641) | **fora de mapa** | 🔴 **La porta ja està trencada**: la suite de `models_app` no és verda i tapa regressions futures | **XS** — 2 línies de mock (+1 arg). No és poda: és reparació |
| 2 | **`EditableTable` família de 3** | [:413](../../frontend/src/components/EditableTable/EditableTable.jsx#L413)·[:476](../../frontend/src/components/EditableTable/EditableTable.jsx#L476)·[:666](../../frontend/src/components/EditableTable/EditableTable.jsx#L666) | `presaDelContenidor` (el cridador) | **fora de mapa** (Agus ho va excloure d'F1) | 🟠 **Pot fallar en runtime** el dia que una taula rebi 2 peces: els 3 fallen junts i **en silenci** | **S** — decisió d'arquitectura (predicat vs partició del cridador) + 3 bancs |
| 3 | **2 boques de `_load_grading_rules`** | [graded_spec_views.py:171](../../backend/fhort/fitting/graded_spec_views.py#L171)·[serializers_size_check.py:97](../../backend/fhort/models_app/serializers_size_check.py#L97) | serveixen la llei de la MARE | **fora de mapa** (cua de Q1-bis) | 🟠 **Menteix en silenci** amb 2 peces: rètol de règim de la peça amb la llei de la mare | **S** — `_regla_de(...)` + banc per boca (patró ja fet 3 vegades) |
| 4 | **`size-fittings/<sf_id>/taula-mesures/`** | [pom/grading_views.py:106](../../backend/fhort/pom/grading_views.py#L106) · ruta [tasks/urls.py:138](../../backend/fhort/tasks/urls.py#L138) | **CAP consumidor** | **G5** | 🟡 **Abastable** per qualsevol client amb token, però **GET read-only**: no corromp res | **XS** — treure 1 ruta; la funció pot seguir importable com les 5 de C1.1 |
| 5 | **`FittingDurationStat` + escriptor** | [fitting/models.py:541](../../backend/fhort/fitting/models.py#L541)·[services.py:1039](../../backend/fhort/fitting/services.py#L1039) | s'escriu, **cap lector** | **G5** (ja acumulat) | 🟡 Escriu a cada sessió; **1 fila** viva. Inert, però creix | **S** — model + servei + migració; verificar `override_changed` (sempre False) |
| 6 | **W5 · overrides sense editor** | [extraction_views.py:3544](../../backend/fhort/models_app/extraction_views.py#L3544) | escriptor viu, **0 lectors editables** | **G3** (import vell) | 🟡 **Latent**: 0 files de W5 avui. Un import W5 crearia dades **que ningú pot veure ni corregir** | **M** — o es reobre una superfície d'edició, o W5 deixa d'escriure'ls. Decisió de producte |
| 7 | **5 vistes B4 (vives per bancs)** | §C1.1 | **12 fitxers de banc** | **G5** | 🟢 **Inert**: sense ruta, cap client hi arriba | **L** — el cost NO és esborrar: és **re-allotjar 8+4 bancs** de lleis vives (segell G6, rang, C4, STEP, F1) |
| 8 | **Clúster `Contracte`** (2 models · 2 FK · 2 serializers) | §C1.3 | només entre ells | **G5** | 🟢 Inert i **buit** (0 files, 0/31 FK) | **M** — **exigeix migració** sobre `models_app_model` (2 columnes) |
| 9 | **14 components front orfes (2.516 línies)** | §C2.1 | **CAP** (ni bancs) | **G8** (·G2 per `EstatBadge`) | 🟢 Inert: no entren al bundle | **S** — esborrat pla. ⚠️ 2 amb acta (`PromoteToItemButton`) i 1 veí de zona intocable (`TechSheetTemplateEditor`) |
| 10 | **`measurement_table.*` (31 claus i18n)** | `i18n/{ca,en,es}.json` | **CAP** | **G4** | 🟢 Inert | **XS** — cauen amb el POM-editor vell; no abans (paritat als 3 idiomes) |
| 11 | **58 claus i18n òrfenes restants** | §C2.5 | **CAP** | **G8** | 🟢 Inert | **XS** — esborrat als 3 fitxers alhora |
| 12 | **2 models `POMEstadistica*`** | [pom/models.py:338](../../backend/fhort/pom/models.py#L338)·[:480](../../backend/fhort/pom/models.py#L480) | **CAP enlloc** | **G5** | 🟢 Inert, **0 files** als 3 esquemes | **S** — migració de `DROP TABLE`, sense lectors ni escriptors |
| 13 | **3 serializers orfes** | §C1.2 | **CAP** | **G5** | 🟢 Inert | **XS** |
| 14 | **35 seeds/one-shots consumits** | §C1.5 | 33 citats a docs; 2 a res | **G5** | 🟢 Inert | **S** — decisió de cicle de vida, no de descobriment |
| 15 | **`Model.estat`: columna sempre `'—'`** | [models.py:242](../../backend/fhort/models_app/models.py#L242) · [Models.jsx:372-379](../../frontend/src/pages/Models.jsx#L372) | acta 🚩 PROVISIONAL-DOMINI al lloc | **G2** | 🟢 Inert i **declarat** | **M** — no és poda: és **decidir si el Kanban existirà**. Decisió d'Agus |
| 16 | **8 `Response` literals de `wizard_views`** | §C1.6 | POM-editor vell | **G4** | 🟢 Inert avui | **XS** — cauen amb G4 |
| 17 | **Acta FALSA a `CheckMeasureEditor:723`** | [:723](../../frontend/src/components/model/CheckMeasureEditor.jsx#L723) | orienta el proper sprint | **G8** | 🟡 **Risc de MÈTODE**: envia el proper sprint a una pantalla morta | **XS** — 3 línies de comentari. Alt valor per cost zero |
| 18 | **`ItemAuthoring` (429 línies)** | [pages/ItemAuthoring.jsx](../../frontend/src/pages/ItemAuthoring.jsx) | substituït per `CatalegPecesItem` | **G8** | 🟢 Inert | **XS** — esborrat pla + arreglar l'ítem 17 alhora |
| 19 | **`longitudVora`/`longitudTram` no declarades** | §C3.1 | motor de patrons | **fora de mapa** (**intocable**) | 🟢 Inert avui, però **divergiran** | **—** No es toca. 💡 Cost mínim: **declarar-les bessones** (comentari creuat), no unificar-les |
| 20 | **`suggested_poms_view` duplicat** | [wizard_views.py:62](../../backend/fhort/pom/wizard_views.py#L62) | ruta `poms/suggerits/`, sense front | **G4** | 🟢 Inert | **XS** — cau amb G4 |
| 21 | **`discovery.*` (11 claus + backend viu)** | §C2.6 | backend sí, front no | **fora de mapa** | 🟢 Inert | **NO PODAR** — 💡 acabar o retirar **sencera**. Decisió d'Agus |

---

## RECOMPTE PER GRUP G

| G | Ítems del cens | Volum mesurat |
|---|---|---|
| **G2** estat del model | 15 (+`EstatBadge` de 9) | 1 columna + 1 component (74 l.) |
| **G3** import vell | 6 | 1 escriptor sense lector editable |
| **G4** POM-editor vell + òrfenes | 10 · 16 · 20 | 31 claus i18n + 8 Response + 1 endpoint |
| **G5** codi mort transversal | 4 · 5 · 7 · 8 · 12 · 13 · 14 | 5 vistes + 4 models buits + 3 serializers + 35 comandaments + 2 rutes |
| **G8** higiene frontend | 9 · 11 · 17 · 18 | ~2.516 línies + 58 claus + 1 acta falsa |
| **fora de mapa** (decisió Agus) | 1 · 2 · 3 · 19 · 21 | 2 vermells/oberts + 2 bessones intocables + 1 feina inacabada |

---

## TAULA DE RISC — EL QUE UN CTO HA DE SABER EN 30 SEGONS

| Pot fallar en runtime | Ítems | Acció que el cens suggereix |
|---|---|---|
| 🔴 **Ja falla** | 1 (`test_parser_excel`) | Reparar el mock. **No és poda.** |
| 🟠 **Fallarà en silenci** quan hi hagi 2 peces | 2 (`EditableTable`), 3 (2 boques) | Decisió d'arquitectura + `_regla_de` |
| 🟡 **Abastable o latent** | 4 (GET sense consumidor), 5 (escriu sense lector), 6 (W5) | Poda barata (4) · decisió de producte (6) |
| 🟢 **Pes mort inert** | 7–16, 18, 20 | Poda per grups G, quan toqui |
| ⛔ **No podar** | 19 (intocable), 21 (feina inacabada) | Decisió d'Agus |

---

## LÍMITS DECLARATS

1. **`docs/diagnosis/arxiu/` no s'ha fet servir com a font** (llei de mètode). Hi ha una
   `DIAGNOSI_G2_MODEL_ESTAT.md` arxivada que **no s'ha llegit**: el que consta de G2 surt del codi
   i de `DECISIONS.md`.
2. **El cens de bancs mesura CITACIÓ, no execució.** Un banc pot citar una funció en un comentari
   i no exercitar-la. Els 8 bancs d'`escalat_ajustar_talla_view` s'han vist **importar-la i
   cridar-la** (mostrejat a 3); els altres 5 són citació verificada, no execució verificada.
3. **No s'ha censat `frontend-backoffice/`**, ni `webs/`, ni `ops/maquetes/`. Només
   `backend/fhort` + `frontend/src`.
4. **Els 705 `Response({...})` no s'han auditat un per un** — només els 26 que emeten identitat de
   mesura. Els altres 679 poden contenir més duplicacions de serializer: **PENDENT DE VERIFICAR**.
5. **`ESTAT_*.md` i `MAPA_SISTEMA.md` no s'han llegit** (fitxers d'estat del servidor, i el
   working tree de la sessió concurrent és intocable).
6. **`los` s'ha comptat només per a les taules buides.** El cens de codi és de `fhort`.
7. Els **42 comandaments «altres»** no s'han classificat un per un: poden contenir més one-shots
   consumits. **PENDENT DE VERIFICAR.**
