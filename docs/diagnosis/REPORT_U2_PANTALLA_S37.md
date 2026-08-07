# REPORT · U2 · PANTALLA CATÀLEG DE PECES — S37

> **Data:** 2026-08-07 · **Branca:** `dev` (staging) · **Cap push** (7 commits locals).
> **Especificació LITERAL:** `ops/maquetes/maqueta_cataleg_peces_v4.html` (417 línies, llegida sencera)
> **Antecedent:** `docs/diagnosis/REPORT_UI_CATALEGS.md` §5 (el mapa de reutilització)
>
> **Aquest document té DUES parts.** §1-§6 són la **diagnosi** que va aturar el tram (07/08 vespre),
> i es conserven **intactes** perquè són el contracte contra el qual es verifica. **§7 endavant és
> la FASE D'IMPLEMENTACIÓ**, amb les resolucions d'Agus (R1-R6) ja aplicades i la checklist.

---

## 0 · VEREDICTE

### 0.a · Diagnosi (primera passada) — el tram es va aturar al PAS 2
El brief manava: *«PAS 3 — IMPLEMENTAR (només si 1 i 2 quadren)»*. No quadraven. **6 aturades dures
i 3 avisos**, i la principal no era de pantalla: **la taula que la maqueta pinta al tab «Talles i
POMs» no tenia ni component ni contracte d'API a nivell d'ITEM.**

### 0.b · Implementació (segona passada) — ✅ TANCAT
Amb R1-R6 resoltes per Agus, **la pantalla està construïda, desplegada i verificada als tres
idiomes**. Les 6 aturades queden totes tancades: 2 per esmena de backend autoritzada (R2·R3), 1 per
patró d'arquitectura (R1), 1 per absència de dada confirmada (R4 → N/A), 2 per decisió (R5·R6).
**Checklist: 46/46 elements ✓ (2 N/A amb motiu) · 79 claus × 3 idiomes.** V. §7-§11.

> 🔴 **Una cosa que aquest report deia i era FALSA** — v. §9.3: vaig escriure que les dues píndoles
> d'instància de la maqueta eren «dades de demostració». **No ho són: són la llei de la casa.**
> `EditableTable` fa exactament `d.opcions.slice(0, 2)`. Ho vaig construir malament, ho va delatar
> la captura, i està corregit.

| | Peça | Estat |
|---|---|---|
| 1 | Inventari literal de la maqueta (§1) | ✅ fet — **és el contracte de la checklist** |
| 2 | Cens del que ja hi ha (§2) | ✅ fet |
| 3 | Les 6 aturades (§3) | ✅ **totes tancades** — v. §9 |
| 4 | Backend R2 · R3 (§7) | ✅ 17 tests · migració auditada als schemes |
| 5 | Vista A · Vista B · la germana R1 (§8) | ✅ desplegades |
| 6 | Checklist maqueta↔pantalla · captures (§10) | ✅ **44 ✓ · 0 ✗ · 2 N/A** · 9 captures |
| 7 | El que queda obert (§11) | 🚩 **8 punts**, tots decisió d'Agus |

> **Els commits d'aquest tram:** `6826e5e4` (R2) · `77dc0c29` (R3) · `f0a2ffab` (i18n) ·
> `62368823` (Vista A) · `44962217` (germana R1 + pantalla d'item) · `998188eb` (rutes + retirada) ·
> `7d4972dc` (fix del nom anglès). **Cap push** — els fa Agus des de SSH.

---

## 1 · INVENTARI LITERAL DE LA MAQUETA v4 — EL CONTRACTE

Recitat element per element. La implementació no pot tenir **ni un element més ni un de menys**.

### VISTA A · CATÀLEG (`#vCat`)

#### Z1 · Capçalera de pàgina
| # | Element | Què mostra | D'on surt | En clicar |
|---|---|---|---|---|
| A1 | `.crumb` | «Configuració tècnica › **Catàleg de peces**» | estàtic | — (no és enllaç) |
| A2 | `h1` | «Catàleg de peces» | estàtic | — |
| A3 | `.chip` dins l'`h1` | «Brownie» | el tenant/marca | — |
| A4 | `.sub` | text de 2 frases (v. §1.5 T4) | estàtic | — |

#### Z2 · Columna 1 · Grup (amplada fixa 222px)
| # | Element | Què mostra | D'on surt | En clicar |
|---|---|---|---|---|
| A5 | `.colhead .t` | «1 · Grup» | estàtic | — |
| A6 | `.colhead .n` | nombre de grups (`8` a la maqueta) | recompte de grups | — |
| A7 | `.search input` | placeholder «cerca grup…» | — | filtra la llista |
| A8 | `.list` | scroll, `max-height:520px` | — | — |
| A9 | `.row .nm` | nom del grup | `GarmentGroup.nom` | selecciona el grup |
| A10 | `.row .cd` | codi del grup | `GarmentGroup.codi` | ídem |
| A11 | `.row .ct` | «{N} fam.» | nre. de famílies del grup | ídem |
| A12 | `.row .pm` | «{N} POMs» | POMs a **nivell de grup** | ídem |
| A13 | `.addrow button` | «＋ Nou grup» (amplada plena) | — | crea grup |

*Efecte de `selG(i)`: fixa el grup, **reinicia família a la 1a i item a 0**.*

#### Z3 · Columna 2 · Família (222px)
| # | Element | Què mostra | D'on surt | En clicar |
|---|---|---|---|---|
| A14 | `.colhead .t` | «2 · Família» | estàtic | — |
| A15 | `.colhead .n` | nre. de famílies · **«—» sense grup triat** | recompte | — |
| A16 | `.search input` | placeholder «cerca família…» | — | filtra |
| A17 | `.row .nm` | nom de la família | `GarmentType.nom_client` | selecciona |
| A18 | `.row .cd` | codi de la família | `GarmentType.codi_client` | ídem |
| A19 | `.row .ct` | «{N} items» | `items_count` | ídem |
| A20 | `.row .pm` | **«+{N} POMs»** (amb el `+`) | POMs a **nivell de família** | ídem |
| A21 | `.addrow button` | «＋ Nova família» | — | crea família |

#### Z4 · Columna 3 · Item (`1fr`)
| # | Element | Què mostra | D'on surt | En clicar |
|---|---|---|---|---|
| A22 | `.colhead .t` | «3 · Item» | estàtic | — |
| A23 | nota inline dins A22 | «· els temps de tasca s'ancoren aquí» (minúscula, `--ink-faint`) | estàtic | — |
| A24 | `.colhead .n` | «{N} items» · **«—» sense selecció** | recompte | — |
| A25 | botó `.btn.sm` a la capçalera | «＋ Nou item» | — | crea item |
| A26 | `.irowhead` | 6 cel·les: «Item» · «Catàleg de POMs proposat» · «Run de talles» · «Talla base» · «Fitxers» · **(buida)** | estàtic | — |

**`.irow` — una LÍNIA per item** (`grid: 1fr 190px 148px 96px 104px 92px`):

| # | Cel·la | Què mostra | D'on surt |
|---|---|---|---|
| A27 | 1 · `.nm` | nom de l'item | `GarmentTypeItem.name` |
| A28 | 1 · `.tagm` | píndola **«EL CAS MILEY»** — només si l'item ho és | ❌ **cap dada** (v. §3 G1) |
| A29 | 1 · `.cd` | codi de l'item | `GarmentTypeItem.code` |
| A30 | 2 · `.acc` | «grup **{g}** · fam **{f}** · item **{p}**» | `acumulacio.recompte` |
| A31 | 2 · `.acc .tot` | el total, en or, més gran | `recompte.total` |
| A32 | 2 · `.bar` | barra de 3 segments proporcionals (grup · família · item) | ídem |
| A33 | 3 · `.v` | nom del run de talles | ❌ **no és camp de l'item** (§3 G5) |
| A34 | 4 · `.v` | etiqueta de la talla base | `base_size_label` |
| A35 | 5 · `.fx` | «**{N}** · {EXT · EXT · …}» — o «**0** · —» | compte ✅ · desglossament ⚠️ (§3 A3) |
| A36 | 6 · `.btn.sm` | **«Editar»** — l'ÚNIC botó de la línia | → vista B |

#### Z5 · Peu `.foot`
| # | Element | Contingut |
|---|---|---|
| A37 | `.foot` | «Què canvia respecte de la v3» + 3 pics | ⚠️ **v. §3 A1: és comentari SOBRE la maqueta, no pantalla** |

### VISTA B · PANTALLA DE L'ITEM (`#vItem`)

#### Z6 · Crumb i capçalera
| # | Element | Què mostra | En clicar |
|---|---|---|---|
| B1 | `.crumb a` | «← Catàleg de peces» (or, clicable) | torna a la vista A |
| B2 | `.crumb b#bcF` | «{Grup} › {Família}» | — |
| B3 | `.crumb b#bcI` | «{Item}» | — |
| B4 | `.shead .t` | nom de l'item | — |
| B5 | `.shead .c` | codi de l'item | — |
| B6 | `.tabs button` | **«Talles i POMs»** — actiu per defecte | mostra `#tP` |
| B7 | `.tabs button` | **«Fitxers»** | mostra `#tF` |

#### Z7 · Tab «Talles i POMs» · `.runbar`
| # | Element | Què mostra | En clicar/canviar |
|---|---|---|---|
| B8 | `.lbl` | «Run de talles» | — |
| B9 | `select#run` | 3 opcions literals: «Alpha EU — Women · XXS·XS·S·M·L» · «Alpha agrupat · XS-S · S-M · M-L» · «Numeric EU — Women · 32…42» | canvia el run **i reassigna la talla base** |
| B10 | `.lbl` | «Talla base» | — |
| B11 | `.sizes .sz` | una píndola per talla del run | fixa la talla base **i repinta la taula** |
| B12 | `.sz.base` | estat seleccionat (or + anell) | — |
| B13 | `.hint` | «La talla base obre i informa la columna de mesures de partida.» | — |

#### Z8 · Tab «Talles i POMs» · línia de tecles
| # | Element | Contingut literal |
|---|---|---|
| B14 | `.keys` | `↓`/`Enter` següent · `↑` anterior · `L` germana de capa · `I` grups d'instància · `N` nomenclatura · última fila `↓` = cercador |

#### Z9 · Tab «Talles i POMs» · la taula (10 columnes, `min-width:1060px`)
**Capçalera, 2 files:**
| # | Element | Contingut |
|---|---|---|
| B15 | fila 1 · `colspan=5` | buida |
| B16 | fila 1 · `th.ins colspan=3` | **«Instància»** (fons `--sel`, text or) |
| B17 | fila 1 · `th.base rowspan=2` | **«Mesura de partida»** + `<b>` amb l'etiqueta de la talla base (o «—») |
| B18 | fila 1 · `rowspan=2` | buida |
| B19 | fila 2 | «#» · «Capa» · **(buida)** · «POM» · «Nom» · «Posició» · «Estat» · «Més» |

**Cos — una fila per POM acumulat** (deduplicat per codi, ordre grup → família → item):
| # | Col. | Contingut | D'on surt |
|---|---|---|---|
| B20 | 1 | número d'ordre (gris) | índex |
| B21 | 2 | `select`: «Exterior» · «Folre» · «Entretela» | ❌ `capa` **no exposada** (§3 G2) |
| B22 | 3 | «⧉» `title="duplicar"` | ❌ (§3 G3) |
| B23 | 4 | codi del POM (or, negreta) | `pom_code` ✅ |
| B24 | 5 | nom del POM | `name_cat`/`name_en` ✅ |
| B25 | 5 | «ⓘ» `title="nom en català"` | ✅ |
| B26 | 5 | «✎» `title="editar nom i nomenclatura"` | ❌ (§3 G3) |
| B27 | 6 | 2 botons: «Left» · «Right» | ❌ `instancia` **no exposada** (§3 G2) |
| B28 | 7 | 2 botons: «Relaxed» · «Extended» | ❌ ídem |
| B29 | 8 | botó «＋» centrat | ❌ ídem |
| B30 | 9 | `input.val` — valor base, `placeholder="—"`, fons `--sel` | `ItemBaseMeasurement.base_value_cm` ✅ |
| B31 | 10 | «✕» `title="treure"` | ✅ |

#### Z10 · Tab «Talles i POMs» · peus
| # | Element | Contingut literal |
|---|---|---|
| B32 | `.finder input` | placeholder «codi o nom…  «C.f» folre · «S.l» esquerra» (vora or, 330px) |
| B33 | nota del finder | «Enter confirma · Esc torna al carril» |
| B34 | `.sfoot button` | «↑ Importar d'una fitxa» |
| B35 | `.sfoot span` | «El que hi hagi aquí és el que se sembrarà al model. El que no hi sigui, no se sembra.» |
| B36 | `.sfoot button` | «Tornar» → vista A |
| B37 | `.sfoot button.pri` | **«Gravar»** |

#### Z11 · Tab «Fitxers» (`grid: 290px 1fr`, `min-height:320px`)
| # | Element | Què mostra | En clicar |
|---|---|---|---|
| B38 | `.frow .ext` | badge d'extensió (JPG · AI · DXF · RUL) | selecciona |
| B39 | `.frow .fn` | nom del fitxer (ellipsis) | ídem |
| B40 | `.frow .fs` | mida llegible | ídem |
| B41 | `.frow.on` | estat seleccionat (fons `--sel` + barra or) | — |
| B42 | `.canvas` | 3 textos segons extensió: «previsualització del patró (DXF)» · «joc de regles (RUL) — lectura» · «previsualització de {nom}» | — |
| B43 | `.vmeta` | **{nom}** · «{EXT} · {mida}» · {descripció} | — |
| B44 | botó | «↑ Pujar fitxer» | — |
| B45 | botó | «↓ Descarregar» | — |
| B46 | botó `.dang` | «Esborrar» (alineat a la dreta) | — |

### 1.4 · ESTATS VISIBLES A LA MAQUETA
✅ **Hi són:** fila seleccionada (`.row.on`, `.frow.on` — fons `--sel` + `inset 3px` or) · talla base
seleccionada (`.sz.base`) · tab actiu (`.tab.on`) · píndola «EL CAS MILEY» · hover de fila · «—» al
comptador sense selecció · «—» al valor buit (`placeholder`) · «—» a la talla base sense triar
(`#bs`) · «0 · —» a la columna Fitxers sense fitxers.

🛑 **NO hi són — i per Regla Zero, per tant, NO EXISTEIXEN:**
- **loading** (cap spinner, cap «carregant…»)
- **error de xarxa** (cap avís)
- **llista buida** — un grup sense famílies, una família sense items: la maqueta simplement no
  pinta res. **Ni text buit, ni caixa de puntets.**
- **permisos** — «＋ Nou grup», «Editar» i «Gravar» surten **sempre**, sense cap gate `CONFIGURE`.
- **«mesura proposada EN GRIS»** — el brief la demana; **la maqueta no la té.** V. §3 A2.

### 1.5 · TEXTOS LITERALS (i18n ca/es/en)
`T1` «Configuració tècnica» · `T2` «Catàleg de peces» · `T3` «Brownie» *(dada, no traduir)* ·
`T4` «Estructura pròpia de la marca, definida al setup. El catàleg de POMs s'acumula per nivell i
proposa: grup → família → item. Els grups agrupen per com es MESURA, no per com es ven.» ·
`T5` «1 · Grup» · `T6` «cerca grup…» · `T7` «{N} fam.» · `T8` «{N} POMs» · `T9` «＋ Nou grup» ·
`T10` «2 · Família» · `T11` «cerca família…» · `T12` «{N} items» · `T13` «+{N} POMs» ·
`T14` «＋ Nova família» · `T15` «3 · Item» · `T16` «· els temps de tasca s'ancoren aquí» ·
`T17` «＋ Nou item» · `T18` «Item» · `T19` «Catàleg de POMs proposat» · `T20` «Run de talles» ·
`T21` «Talla base» · `T22` «Fitxers» · `T23` «grup» · `T24` «fam» · `T25` «item» ·
`T26` «EL CAS MILEY» · `T27` «Editar» · `T28` «← Catàleg de peces» · `T29` «Talles i POMs» ·
`T30` «La talla base obre i informa la columna de mesures de partida.» · `T31` la línia de tecles
sencera (6 fragments) · `T32` «Instància» · `T33` «Mesura de partida» · `T34` «#» · `T35` «Capa» ·
`T36` «POM» · `T37` «Nom» · `T38` «Posició» · `T39` «Estat» · `T40` «Més» · `T41` «Exterior» ·
`T42` «Folre» · `T43` «Entretela» · `T44` «duplicar» · `T45` «nom en català» ·
`T46` «editar nom i nomenclatura» · `T47` «Left» · `T48` «Right» · `T49` «Relaxed» ·
`T50` «Extended» · `T51` «treure» · `T52` «codi o nom…  «C.f» folre · «S.l» esquerra» ·
`T53` «Enter confirma · Esc torna al carril» · `T54` «↑ Importar d'una fitxa» ·
`T55` «El que hi hagi aquí és el que se sembrarà al model. El que no hi sigui, no se sembra.» ·
`T56` «Tornar» · `T57` «Gravar» · `T58` «previsualització» · `T59` «previsualització del patró (DXF)» ·
`T60` «joc de regles (RUL) — lectura» · `T61` «previsualització de {nom}» · `T62` «↑ Pujar fitxer» ·
`T63` «↓ Descarregar» · `T64` «Esborrar»

**64 claus × 3 idiomes = 192 entrades.** *(«Exterior/Folre/Entretela» i «Left/Right/Relaxed/Extended»
són **vocabulari de domini** i venen del diccionari de la BD (D-31.22/D-31.26): NO són claus i18n.
Descomptades, queden **57 claus × 3 = 171**.)*

---

## 2 · CENS DEL QUE JA HI HA (read-only)

### 2.1 · Les dues pantalles que es redissenyen
| Fitxer | Línies | Ruta | Es reaprofita | Mor |
|---|---|---|---|---|
| [`pages/GarmentTypes.jsx`](../../frontend/src/pages/GarmentTypes.jsx) | 448 | `garment-types` | el patró de càrrega de fitxers lligada a clau (`clauFitxers`, l. 89-100) · `pujarFitxer` · `TypeModal` (＋ Nova família) | mestre-detall pla · `GroupPills` · `ItemCard` (graella de cards) · `StatusLine` (termòmetre) · secció Fitxers sota la llista |
| [`pages/ItemAuthoring.jsx`](../../frontend/src/pages/ItemAuthoring.jsx) | 429 | `garment-type-items/:itemId/editar` · `.../nou/:typeId` | `ensureItem` · `slugify` · `pickBaseSize` | stepper de 2 passos · `CascadeSelector` (filtre d'eixos) · `RuleSetPicker` · el slot d'import inert |

**Qui hi apunta des de fora** (`navigate(...)`), tots dos supervivents del redisseny:
- `→ /garment-types`: [`GarmentTypes.jsx:217,218,231`](../../frontend/src/pages/ItemAuthoring.jsx#L217) (retorns d'`ItemAuthoring`) + el menú del Shell.
- `→ /garment-type-items/:id/editar`: [`GarmentTypes.jsx:254`](../../frontend/src/pages/GarmentTypes.jsx#L254).
- `→ /garment-type-items/nou/:typeId`: [`GarmentTypes.jsx:236,246`](../../frontend/src/pages/GarmentTypes.jsx#L236).
- `BaseSetPanel` és consumit **només** per `ItemAuthoring` — el seu únic consumidor mor amb el pas 2.

### 2.2 · El mapa de reutilització del REPORT_UI_CATALEGS.md, contrastat
| Component | Contracte real | Cobreix el que la maqueta demana? |
|---|---|---|
| [`CascadeFinder`](../../frontend/src/components/CascadeSelector/CascadeFinder.jsx#L43) | `{value, onChange, onPickItem, target, compat, query, renderHeader, renderItemMeta, height}` — **és exactament** grup › família › item en 3 columnes de finder | 🟡 **parcial.** Cobreix Z2+Z3 i la tria. **No** la columna 3 de la maqueta: `renderItemMeta` és un nus **a la dreta de la fila**, i la maqueta vol una **graella de 6 columnes alineades** amb capçalera pròpia (A26). I diu de si mateix: *«no coneix cap acció de catàleg (editar/esborrar/nou)»* — els 3 botons «＋» (A13/A21/A25) hi són a fora. |
| [`MeasurementBaseGrid`](../../frontend/src/components/MeasurementBaseGrid/MeasurementBaseGrid.jsx#L45) | `{garmentTypeItemId, baseSetId, readOnly, onSaved}` | 🛑 **NO.** V. §3 G3 — les columnes no s'assemblen. |
| [`FileList`](../../frontend/src/components/assets/FileList.jsx#L19) | `{files, selectedId, onSelect, onOpen, emptyLabel}` | 🟡 **parcial.** Té selecció i ordenació; pinta **nom · tipus · data**. La maqueta vol **badge d'extensió · nom · mida** i **cap columna de data**, i hi afegeix un **visor a la dreta** (B42-B46) que no existeix enlloc. |
| `itemFitxers` (endpoints.js:210) | `list · create · usarAlModel` | 🟡 falta `remove` (B46 «Esborrar») i `download` (B45). |
| [`Chip`](../../frontend/src/components/grading/wizardUI.jsx#L25) | píndola seleccionable | ✅ serveix per B11 (talles) — **i és zona de frontera: es consumeix, no es toca.** |

### 2.3 · El contracte de l'endpoint d'acumulació
[`GET /api/v1/garment-type-items/<id>/acumulacio/`](../../backend/fhort/pom/cataleg_views.py#L169) retorna:
`{item, item_codi, familia, grup, recompte:{grup,familia,item,total}, poms:[{nivell, ancora, map_id,
pom_id, capa, instancia, obligatori, is_key, nivell_excel, ordre, pendent_revisio, tambe_a[],
pom_code, name_en, name_cat, abbreviation, unitat}]}`

✅ **`recompte` cobreix A30/A31/A32 exactament** (els 3 nivells sumen el total: la barra quadra).
✅ **I aquest sí que porta `capa` i `instancia` per fila.** Però és **read-only** (`@api_view(['GET'])`):
serveix per pintar B21/B27/B28, **no per escriure-hi**. V. §3 G2.
⚠️ És **una crida per ITEM**: pintar la columna A30 d'una família de 2 items són 2 peticions; el
catàleg viu en té 62 en total, repartits en 21 famílies (màx. observat per família: pocs). Acceptable,
**però és N+1 i s'ha de dir.**

### 2.4 · L'estat REAL de les dades (staging, schema `fhort`)
| Què | Compte | Lectura |
|---|---|---|
| Grups (`pom_garmentgroup`) | **12** | la maqueta en dibuixa 8; 12 és dada, no bug |
| Famílies (`pom_garmenttype`) | **21** (17 actives) | |
| Famílies amb `grup_ref` | **21 / 21** | 🟢 **la cascada grup›família té base sencera** |
| Items (`tasks_garmenttypeitem`) | **62** (62 actius) | |
| `pom_garmentgrouppommap` | **0** | 🟡 **buit per BD**, no per bug (§3 A4) |
| `pom_garmenttypepommap` | **0** | 🟡 ídem |
| `pom_garmentpommap` | **1.748** | |
| … amb `capa` ≠ `exterior` | **0** | |
| … amb `instancia` ≠ `''` | **0** | |
| Items amb `grading_rule_set` | **3 / 62** | ⚠️ la columna A33 seria «—» a 59 files |
| Items amb `base_size_definition` | **2 / 62** | ⚠️ la columna A34 seria «—» a 60 files |
| `models_app_itemfitxer` | **1** (tipus `SKETCH_SVG`) | ⚠️ A35 seria «0 · —» a 61 files |
| `pom_itembaseset` | **1** | |

> 🟢 **CORRECCIÓ A LA MEMÒRIA DE SESSIONS ANTERIORS.** La nota «la `0073` de `pom` NO està
> aplicada / les taules d'acumulació no existeixen» **ja no és certa**: `public.django_migrations`
> registra `0073_u2_acumulacio_poms` i `to_regclass` confirma **les dues taules vives** a `fhort`.
> Estan **buides**, que és una cosa diferent i està documentada com a 🚩3 del report anterior.

---

## 3 · 🛑 LES ATURADES — PER QUÈ NO S'IMPLEMENTA

### 🛑 G1 · «EL CAS MILEY» (A28) no té cap dada al darrere
La maqueta pinta una píndola daurada sobre el nom d'un item. A les dades de la maqueta és
`{c:'dress_circle', …, miley:true}` — **una bandera escrita a mà en un sol dels 13 items d'exemple**.
Cap camp de `GarmentTypeItem`, ni cap serializer, ni cap endpoint diu res semblant.

Les dues lectures possibles porten a coses oposades i **cap de les dues és meva**:
- **bastida de demostració** (l'autor de la maqueta anotant «aquest és el cas que discutíem») → no
  s'implementa i desapareix de l'inventari;
- **estat real de producte** («aquest item té una incidència oberta») → llavors falta el camp, i
  crear-lo és backend, que el brief prohibeix.

**Decisió d'Agus.** Inventar-me qualsevol de les dues és exactament el que la Regla Zero veta.

### 🛑 G2 · `capa` i `instancia` NO surten per l'API d'escriptura de l'item
La maqueta dedica **4 de les 10 columnes** de la taula a la identitat de la fila: «Capa» (B21) i el
bloc «Instància» → «Posició» · «Estat» · «Més» (B27/B28/B29).

- El **model** les té: [`GarmentPOMMap.capa`](../../backend/fhort/pom/models.py#L836) i
  [`.instancia`](../../backend/fhort/pom/models.py#L845), i totes dues són **clau única** amb el POM.
- El **serializer NO les exposa**. [`GarmentPOMMapSerializer.Meta.fields`](../../backend/fhort/pom/serializers.py#L437)
  acaba amb `'is_key', 'obligatori', 'ordre', 'pendent_revisio'` — **`capa` i `instancia` no hi són.**

Conseqüència exacta: `garmentPomMaps.list()` no les retorna i `garmentPomMaps.create/update` les
ignora en silenci. **Les 4 columnes es podrien pintar en LECTURA** (via l'endpoint d'acumulació, §2.3)
**i no es podrien escriure de cap manera.** Botons «Left»/«Relaxed»/«＋» que no fan res no són la
maqueta: són pitjor que no tenir-los.

L'esmena són **dos noms dins d'una tupla** — i és backend. El brief diu «**Cap canvi de backend**» i
«**NO ampliïs backend**». M'aturo aquí i ho reporto, que és el que mana.

> ⚠️ I aquest és el precedent que la memòria de la casa ja porta apuntat: **una columna que existeix
> a la BD i no surt pel serializer és invisible per a tothom que llegeixi per API.**

### 🛑 G3 · Cap component existent és la taula de la maqueta
El brief diu «taula idèntica a la de Definició de POMs». **«Definició de POMs» és
[`EditableTable`](../../frontend/src/components/EditableTable/EditableTable.jsx)**, via
`MeasuresEntryPanel` (`t('model_measurements.pom_title')` = «Definició de POMs i talla base»). I la
maqueta **és aquella taula**, literalment: el desplegable de capa, les píndoles d'instància, les
tecles `L`/`I`/`N`, el cercador del peu amb els sufixos `C.f`/`S.l`.

| | El que la maqueta vol | `MeasurementBaseGrid` (el que el mapa de reutilització proposava) | `EditableTable` (la de debò) |
|---|---|---|---|
| Àncora | **item del catàleg** | item ✅ | **model** 🛑 (`modelId` obligatori, desa per `models.setPomRegla`) |
| Capa (B21) | desplegable | ❌ no té | ✅ |
| ⧉ duplicar (B22) | sí | ❌ | ✅ |
| ✎ nomenclatura (B26) | sí | ❌ | ✅ |
| Instància ×3 (B27-29) | sí | ❌ | ✅ |
| Tecles `L`/`I`/`N` (B14) | sí | ❌ | ✅ |
| Cercador `C.f`/`S.l` (B32) | sí | ❌ | ✅ |
| Mesura de partida (B30) | 1 columna | ✅ | ✅ |
| **Columnes que SOBREN** | — | `nom_fitxa` · `tol−` · `tol+` · nansa de drag | — |

`MeasurementBaseGrid` comparteix amb la maqueta **4 de 10 columnes**, i n'aporta 4 que la maqueta no
té. No és «reutilitzar-lo», és reescriure'l.

`EditableTable` **sí** és la taula — i són **2.075 línies ancorades al model**: `modelId` com a prop,
el mode `presa` amb les seves portes de model, `onPomSave` → `models.setPomRegla`. Portar-la a un
item vol dir donar-li **un segon backend de dades**. Això no és feina de pantalla, **és una decisió
d'arquitectura**, i el brief acota «Cap canvi de backend · abast tancat a la pantalla».

**Pregunta per a Agus:** la taula de l'item ha de ser *la mateixa* `EditableTable` amb una àncora
nova (convergència real, tram propi amb el seu pressupost), o *una de nova* que se li assembli
(i llavors la casa té dues taules de mesures, que és el que el veto dels dos sistemes prohibeix)?

### 🛑 G4 · La línia de tecles (B14) promet el que G2+G3 no poden donar
`L` germana de capa · `I` grups d'instància · `N` nomenclatura són **literalment els gestos de
`EditableTable`** sobre `capa`/`instancia`. Sense G2 no tenen on escriure i sense G3 no tenen
component. Pintar la línia igualment seria anunciar 3 tecles mortes. Cau amb G2/G3.

### 🛑 G5 · «Run de talles» (A33/B9) no és cap camp de l'item — i les dues superfícies que existeixen es contradiuen
La maqueta ho tracta com una propietat **de l'item**: una columna a la llista i **un desplegable que
es canvia** a la pantalla d'edició. A la casa hi ha **dues** coses que hi podrien correspondre, i
diuen l'una el contrari de l'altra:

| | Via A · `grading_rule_set.size_system` | Via B · `ItemBaseSet` (system × fit) |
|---|---|---|
| Quants per item | **1** | **N** (un per «món») |
| Canviar el run vol dir | **reassignar el joc de regles** | crear/triar un altre BaseSet |
| Xoc | **C1**: el joc de regles s'assigna **al MODEL**; el de l'item és *un suggeriment*. Un desplegable que el reassigni pren una decisió que la llei posa en un altre lloc. | **La llei del propi `BaseSetPanel`**: *«La talla base es tria EN CREAR el set i després no es toca des d'aquí: canviar-la reinterpretaria totes les mesures que ja hi pengen, i això no és un desplegable.»* |
| Dades vives | 3 items de 62 | 1 BaseSet en total |

La maqueta ensenya **un** run i **una** talla base clicable per item. **Cap de les dues vies ho diu
això.** Quina és la bona és domini, no pantalla.

### 🛑 G6 · Les píndoles de talla base (B11/B12) són clicables i xoquen amb la llei del BaseSet
Derivada de G5, i es reporta a part perquè és **escriptura**: `base_size_definition` sí que és
escrivible ✅, però el `clean()` d'A3 exigeix que pertanyi al `size_system` del joc de regles, i
`BaseSetPanel` declara que la talla base d'un món **no es re-tria**. La maqueta la fa un clic.
Amb G5 resolt, això es resol sol; sense, no.

### ⚠️ A1 · El peu `.foot` (A37) és comentari SOBRE la maqueta
«Què canvia respecte de la v3» + 3 pics que expliquen el pas de v3 a v4 («els items són línies, no
pastilles», «un sol botó: Editar»…). **És a la maqueta**, i per Regla Zero tot el que hi és, hi és.
Però parla al lector de maquetes, no a l'usuari de la pantalla: un tècnic de Brownie no ha vist mai
la v3. **No l'implemento pel meu compte ni el descarto pel meu compte** — confirmació d'Agus.

### ⚠️ A2 · El brief demana un estat que la maqueta no té
El brief diu «**mesura proposada EN GRIS fins que el tècnic l'accepta**». **He buscat el gris de
proposta a la maqueta i no hi és**: l'`input.val` té un únic aspecte, i l'única grisor és el
`placeholder:"—"` de la cel·la buida. El brief mateix resol l'empat — «*el que fixa la maqueta
(llegir-la mana si aquest resum difereix)*» — o sigui que **no es construeix**. Es reporta perquè
és una divergència entre dos documents d'especificació, no un detall.

### ⚠️ A3 · El desglossament d'extensions de la columna Fitxers (A35)
«**{N}** · JPG · AI · DXF» — el compte `N` ✅ (`fitxers_count`, anotat al queryset). El desglossament,
no: `ItemFitxer.tipus` **no és l'extensió**, és un vocabulari de rol (`ALTRES · DOCUMENT · TECHSHEET ·
EXPORT · PATRO · ESCALAT · SKETCH_FLETXES · SKETCH_NET · SKETCH_SVG · MARCADA · RUL`). Només `RUL`
coincideix amb la maqueta; `JPG`/`AI`/`DXF` s'haurien de derivar de `nom_fitxer`.
**Es pot fer sense tocar backend** (una crida `itemFitxers.list` per item + partir l'extensió del nom),
al preu d'un **segon N+1**. No bloqueja; s'anota perquè és una decisió de cost, no de gust.

### ⚠️ A4 · «N POMs» de grup i família (A12/A20) sortiran a **0** — i és correcte
Les taules existeixen i estan **buides** (§2.4). La barra d'acumulació dirà «grup **0** · fam **0** ·
item **{n}**». **Això és buit per BD, no per bug** — el brief demanava distingir-ho i queda dit.
Els recomptes es poden obtenir sense tocar backend (`garmentGroupPomMaps.list` /
`garmentTypePomMaps.list`, que ja existeixen i filtren per àncora); cap serializer no porta el camp
comptat, o sigui que serien **2 crides més**.

---

## 4 · EL QUE SÍ QUE ES PODRIA CONSTRUIR AVUI, SI AGUS HO VOL
Perquè l'aturada no s'entengui com «no es pot fer res». Amb G1 respost i **sense tocar backend**,
la **vista A sencera** és construïble: A1-A27, A29-A32, A34-A36 (i A33 buida o suprimida, segons G5).
És mitja pantalla amb dos forats declarats.

**No ho he fet**, i el motiu és el criteri d'acceptació del propi brief: «*un sol ✗ = tram no
tancat*». Entregar la meitat A amb la meitat B bloquejada deixaria el catàleg viu **redissenyat a
mitges**: la llista nova apuntaria amb «Editar» a l'`ItemAuthoring` vell, que és el stepper de 2
passos que la maqueta suprimeix. **Això no és mig tram, és una pantalla trencada.** Si Agus prefereix
partir-ho, es fa — però és decisió seva, no meva.

---

## 5 · EL QUE ES DEMANA, EN ORDRE

| # | Bloqueja | Pregunta / acció | De qui |
|---|---|---|---|
| 🛑 1 | A28 | «EL CAS MILEY»: bastida de demostració o estat real? | **Agus** |
| 🛑 2 | B21·B27·B28·B29·B14 | `capa`+`instancia` a `GarmentPOMMapSerializer.Meta.fields` — **2 strings, però és backend**: s'autoritza en aquest tram o va a un de propi? | **Agus** |
| 🛑 3 | tota la taula | La taula de l'item: **`EditableTable` amb àncora nova** (convergència, tram propi) o **component nou** (i dues taules de mesures a la casa)? | **Agus** |
| 🛑 4 | A33·B9·B11 | Què és el «Run de talles» d'un item: el `size_system` del joc de regles, o l'`ItemBaseSet`? I com es concilia amb C1 i amb la llei del BaseSet? | **Agus** |
| ⚠️ 5 | A37 | El peu «Què canvia respecte de la v3»: va a la pantalla o es queda a la maqueta? | **Agus** |
| ⚠️ 6 | A2 | Es confirma que el «gris de proposta» del brief **no** es construeix (la maqueta mana)? | **Agus** |
| ⚠️ 7 | A35 | S'accepta el 2n N+1 per desglossar extensions des de `nom_fitxer`? | **Agus** |

---

## 6 · FRONTERA I MÈTODE — COMPLERTS
- ✅ **No s'ha tocat `index.css`, `ui/buttons.js` ni `wizardUI.jsx`** (sessió `--gold-action` concurrent).
- ✅ **Cap escriptura de cap mena**: ni codi, ni migració, ni commit. El `git status` de treball queda
  com estava; l'únic fitxer nou és aquest report.
- ✅ **Consultes a la BD, totes de lectura** (`select` / `to_regclass`); cap `migrate_schemas`, cap
  `--list` (que en aquesta versió no és read-only).
- ✅ **La suite NO s'ha corregut**: aquest tram no ha canviat codi, i la porta de tests que el report
  anterior va deixar oberta (§4 de `REPORT_UI_CATALEGS.md`) **segueix oberta i no és d'aquest tram**.

---
---

# PART II · FASE D'IMPLEMENTACIÓ (07/08, vespre)

> Les resolucions R1-R6 les va prendre Agus (Patró C). Aquí es documenta **què s'ha construït, què
> s'ha compartit i què s'ha duplicat, amb motiu** — i la checklist element per element.

## 7 · ELS DOS DIFFS DE BACKEND

### 7.1 · R2 · `capa` i `instancia` surten per l'API · commit `6826e5e4`
**Un sol fitxer de producció**, `backend/fhort/pom/serializers.py`:

```python
# afegit a GarmentPOMMapSerializer
capa = serializers.CharField(max_length=20, default='exterior')
instancia = serializers.CharField(max_length=60, default='', allow_blank=True)
# afegit a Meta.fields
'capa', 'instancia',
```

**Els dos `default` NO són decoratius, i aquesta és la part que gairebé em passa per alt.** En
completar-se la tupla de la `unique_together`, DRF hi enganxa **sol** un `UniqueTogetherValidator`
— que és el que volíem (el duplicat passa d'`IntegrityError`/500 a **400 net**). Però el seu
`enforce_required_fields` exigeix **tots** els camps de la clau al `create`, i un camp de model amb
`default` arriba a DRF **només com a `required=False`, sense default de serializer**. Sense els dos
`default` explícits, **tota crida que ja existeix** —`MeasurementBaseGrid` crea amb
`{garment_type_item, pom, ordre}`— **hauria començat a rebre un 400 «This field is required»**.

En PATCH parcial DRF salta els defaults i el validador omple la clau des de la instància: desar
només `{ordre}` segueix sense moure de capa cap fila.

**7 tests** (`pom/test_u2_r2_capa_instancia_api.py`): lectura · escriptura · el mateix POM a dues
capes són dues pertinences · duplicat explícit · duplicat implícit · **crear sense els camps** ·
**PATCH parcial no reseteja la identitat**. Els dos últims són les no-regressions.

**Cap migració** (els camps ja eren a BD, com el brief deia). Verificat: les comportes CHECK que el
`help_text` encara anuncia (`«fins a C4 només s'admet exterior»`) **ja no existeixen** — C4/G4 les
va retirar per `pom/0057`, i `pg_constraint` ho confirma. Escriure `folre` no topa amb res.

### 7.2 · R3 · la PROPOSTA de run i talla base · commit `77dc0c29`
`GarmentTypeItem` guanya dos camps, migració additiva `tasks/0049`:

```python
proposed_size_system = FK('pom.SizeSystem', on_delete=SET_NULL, null=True, blank=True)
proposed_base_size_label = CharField(max_length=30, blank=True, default='')
```

- **`SET_NULL` i no `PROTECT`** (al contrari de `grading_rule_set`): que un item «proposés» un run
  no pot impedir retirar-lo del catàleg ni endur-se l'item.
- **Etiqueta i no FK**, com el brief mana i com el motor ja fa: les regles ancoren per
  `base_size_label` i la fila de `SizeDefinition` és mer metadata del seed (CAT2.1).
- **`clean()` amb la llei d'A3**: si tots dos estan informats, l'etiqueta ha de ser del run; si en
  falta un, **skip** (és l'estat normal d'un item sense proposta). *Afegit meu, no demanat pel
  brief: sense això la pantalla podria desar una etiqueta que cap run conté, que és exactament el
  valor inventat que la Regla Zero prohibeix. Es diu aquí per si Agus el vol fora.*
- ⚠️ **El probe del serializer havia de créixer.** `GarmentTypeItemSerializer.validate()` construeix
  un `GarmentTypeItem` sintètic per invocar `clean()`; portava només `grading_rule_set` i
  `base_size_definition`. Si no hi afegia els dos camps nous, **la branca nova hauria vist sempre
  els camps buits i no s'hauria executat mai per API** — una validació escrita i morta.

**10 tests** (`tasks/test_u2_r3_proposta_item.py`), inclosos: la independència (la proposta **no**
assigna joc de regles ni toca la talla base real), el `SET_NULL`, i **la no-regressió d'A3**.

**Auditoria de la migració, a `information_schema` i `pg_constraint`:**

| Schema | `proposed_size_system_id` | `proposed_base_size_label` | FK resolta a |
|---|---|---|---|
| `fhort` | ✅ bigint, nullable | ✅ varchar, NOT NULL (default `''`) | `fhort.pom_sizesystem` |
| `los` | ✅ bigint, nullable | ✅ varchar, NOT NULL (default `''`) | `los.pom_sizesystem` |
| `public` | **N/A** | **N/A** | — |

> `public` **no té la taula** `tasks_garmenttypeitem` i és correcte: `tasks` és **tenant-only** (no
> és a `SHARED_APPS`). Els «tres schemes» del brief són dos tenants reals + el compartit, i el
> compartit no en té per disseny. Cada tenant resol la FK **al seu propi schema**, que és el que
> calia comprovar de debò.

---

## 8 · R1 · LA GERMANA: QUÈ ES COMPARTEIX I QUÈ ES DUPLICA

`components/cataleg/TaulaPOMsCataleg.jsx` · commit `44962217`.
**`EditableTable` no s'ha tocat ni una línia** (verificat: `git diff` no l'inclou).

### 8.1 · COMPARTIT — i la sorpresa és que no ha calgut extreure RES
El brief autoritzava extreure a mòduls compartits «el que sigui pur i barat». **Ja hi era tot**,
d'sprints anteriors. La germana només l'ha de consumir:

| Mòdul | Què n'agafa | Per què importa |
|---|---|---|
| `utils/capaInstancia.js` | `CAPES` · `etiquetaCapa` · `etiquetaInstancia` | Les paraules de capa i instància |
| `utils/diccionariMesures.js` | `dimensionsDe` · `composaInstancia` · `tramsInstancia` | Els EIXOS i la composició del slug |
| `utils/diccionariMesuresFont.js` | `useEstatDiccionari` | El vocabulari REAL de la BD (D-31.26) |
| `api/endpoints.js` | `garmentPomMaps` · `poms.cerca` · `garmentTypeItems.acumulacio` | Les portes |

**Conseqüència pràctica:** si la Montse sembra una instància nova, apareix a la taula del model **i**
a la del catàleg sense tocar codi. Cap segon vocabulari, cap segona regla de composició.

Dues coses més compartides fora de la taula: `useGarmentGroups` (Vista A) i `midaLlegible`
(tab Fitxers).

### 8.2 · DUPLICAT — el cicle de vida de la fila, i el motiu
| Què | Per què no s'ha compartit |
|---|---|
| Alta / baixa / reordre de fila | A `EditableTable` va entrellaçat amb el desat del MODEL i amb el mode `presa` (portes per fila). Aquí és **una sola porta** (`garmentPomMaps`) i **un sol botó**. |
| El canvi d'identitat (capa · instància) | Ídem: allà passa per `presa.onIdentitat`/`onPomSave`; aquí és estat local fins a «Gravar». |
| ⧉ duplicar (germana de capa) | La regla («la següent capa **LLIURE**») és la mateixa i està **reimplementada**, no copiada: 12 línies. Extreure-la hauria demanat obrir el fitxer prohibit. |
| El cercador amb sufixos `C.f`/`S.l` | El d'`EditableTable` porta l'encunyador de POMs de model i el 409 de col·lisió d'àlies, que aquí **no toquen**: el catàleg no té client de qui parlar. |
| La graella (capçalera de 2 files, 10 columnes) | Presentació pura; és el que la «germana de presentació» vol dir. |

**Balanç honest:** ~200 línies de cicle de vida reimplementades contra 2.075 que no s'han obert, i
**zero vocabulari duplicat**. El risc de divergència real —que les paraules se separin— està tancat
pels mòduls compartits; el que es duplica és mecànica de formulari.

---

## 9 · LES SIS ATURADES, TANCADES

| # | Aturada | Com queda |
|---|---|---|
| **G1** | «EL CAS MILEY» sense dada | **R4 → N/A.** V. §9.1 |
| **G2** | `capa`/`instancia` invisibles per API | ✅ **R2** (§7.1) |
| **G3** | Cap component és la taula | ✅ **R1** — germana de presentació (§8) |
| **G4** | Les tecles prometien el que G2/G3 no donaven | ✅ cau amb G2+G3: `↓`/`Enter`/`↑`/`L` funcionen |
| **G5** | «Run de talles» no és camp de l'item | ✅ **R3** (§7.2) |
| **G6** | Talla base clicable vs. llei del BaseSet | ✅ **R3**: la proposta és una tercera cosa, i `ItemBaseSet` queda intacte |

### 9.1 · R4 · la píndola «EL CAS MILEY» NO es pinta
El brief la condicionava a que hi hagués **retall de rang del run** informat a l'item. **Cens fet:
no existeix aquesta dada.** Ni `GarmentTypeItem` ni `SizeSystem` porten cap camp de retall; el que
s'hi assembla és `Model.size_run_model`, que és **del MODEL, no de l'item**. `SizeSystem.parent` +
`customer_codi` permeten un run DERIVAT per client, però llavors el run ja **és** el retallat i no hi
ha res per superposar.

**→ No es pinta. Cap bastida falsa.** Elements A28 i el text T26 queden **N/A**.

### 9.2 · R5 · el «gris de proposta» no es construeix
Confirmat i no construït. La divergència entre brief-mare i maqueta queda anotada; Agus esmena el
brief-mare.

### 9.3 · 🔴 R6 · el mapa de reutilització, i un error meu que la captura va delatar
- `MeasurementBaseGrid` **descartat** com a base de la taula, com el brief mana.
- `FileList` **NO s'ha pogut fer servir**: pinta `nom · TIPUS · DATA` amb ordenació per columnes, i
  la v4 vol **badge d'extensió · nom · mida** i cap data. S'ha reutilitzat la part pura
  (`midaLlegible`) i s'ha fet la llista a la pàgina. `itemFitxers` **sí**, sencer (+ `remove`, que
  faltava al client tot i que el ViewSet ja el servia).
- `CascadeFinder` **NO s'ha pogut fer servir** per a la Vista A (§ raons a la capçalera de
  `CatalegPeces.jsx`); s'ha compartit la **font de dades** (`useGarmentGroups`) i el **vocabulari**
  (`nomLocal`), que és el que tanca el veto dels dos sistemes.
- `Chip` (`wizardUI`): **zona de frontera, no s'ha tocat.**

> 🔴 **L'error.** A §1.4 d'aquest report vaig escriure que les **dues** píndoles per eix de la
> maqueta eren «dades de DEMOSTRACIÓ», i vaig construir la taula pintant-les **totes vuit**. La
> captura del fum ho va delatar: files de vuit ratlles d'alt. Anant a mirar `EditableTable` hi ha
> literalment `const visibles = d.opcions.slice(0, 2)`. **Les dues píndoles són la llei de la casa**
> — dues en línia i la resta darrere el `＋`, que és la seva porta. Corregit (`44962217`).
> **La lliçó:** havia aplicat bé D-31.26 («el vocabulari surt de la BD») i malament la seva
> conseqüència: *que la llista surti de la BD no vol dir que s'hagi de pintar sencera.*

---

## 10 · CHECKLIST MAQUETA ↔ PANTALLA

Contra la pantalla **desplegada** (`staging.fhorttextile.tech`, `frontend/dist`), amb captures als
tres idiomes. **46 elements de l'inventari · 44 ✓ · 0 ✗ · 2 N/A.**

### Vista A · Catàleg
| # | Element | | Nota |
|---|---|---|---|
| A1 | crumb «Configuració tècnica › Catàleg de peces» | ✓ | |
| A2 | `h1` «Catàleg de peces» | ✓ | |
| A3 | xip de marca | ✓ | «FHORT Management» (dada del tenant; la v4 deia «Brownie») |
| A4 | subtítol de 2 frases | ✓ | |
| A5 | «1 · Grup» | ✓ | |
| A6 | comptador de grups | ✓ | **12** (la v4 en dibuixa 8; és dada) |
| A7 | cerca de grup | ✓ | |
| A8 | llista amb scroll (520px) | ✓ | |
| A9 | nom del grup | ✓ | |
| A10 | codi del grup | ✓ | |
| A11 | «{N} fam.» | ✓ | |
| A12 | «{N} POMs» | ✓ | **0** — buit per BD (taules vives i buides), no per bug |
| A13 | «＋ Nou grup» | ✓ | gated CONFIGURE |
| A14 | «2 · Família» | ✓ | |
| A15 | comptador · «—» sense grup | ✓ | |
| A16 | cerca de família | ✓ | |
| A17-18 | nom i codi de família | ✓ | |
| A19 | «{N} items» | ✓ | |
| A20 | «+{N} POMs» (amb el `+`) | ✓ | **0** — ídem A12 |
| A21 | «＋ Nova família» | ✓ | |
| A22 | «3 · Item» | ✓ | |
| A23 | nota «· els temps de tasca s'ancoren aquí» | ✓ | minúscula i atenuada |
| A24 | comptador · «—» sense selecció | ✓ | |
| A25 | «＋ Nou item» | ✓ | |
| A26 | capçalera de 6 columnes | ✓ | 5 rètols + 1 buida |
| A27 | nom de l'item | ✓ | |
| A28 | píndola «EL CAS MILEY» | **N/A** | **R4: no hi ha dada de retall de rang** (§9.1) |
| A29 | codi de l'item | ✓ | |
| A30 | «grup N · fam N · item N» | ✓ | de `/acumulacio/` |
| A31 | el total, en or i més gran | ✓ | |
| A32 | barra de 3 segments proporcionals | ✓ | |
| A33 | run de talles | ✓ | de `proposed_size_system_nom` (R3) |
| A34 | talla base | ✓ | de `proposed_base_size_label` (R3) |
| A35 | «N · JPG · AI · DXF» | ✓ | extensió del **nom**; `tipus` és vocabulari de rol |
| A36 | «Editar», únic botó de la línia | ✓ | va a la pantalla NOVA |
| A37 | peu «Què canvia respecte de la v3» | **N/A** | ⚠️ **decisió pendent** (§11) |

### Vista B · Pantalla de l'item
| # | Element | | Nota |
|---|---|---|---|
| B1 | «← Catàleg de peces» clicable | ✓ | |
| B2-B3 | crumb família › item | ✓ | |
| B4-B5 | nom i codi a la capçalera | ✓ | |
| B6 | tab «Talles i POMs», actiu per defecte | ✓ | |
| B7 | tab «Fitxers» | ✓ | |
| B8-B9 | «Run de talles» + desplegable | ✓ | opcions = `SizeSystem` reals |
| B10-B12 | «Talla base» + píndoles + estat seleccionat | ✓ | |
| B13 | hint de la talla base | ✓ | |
| B14 | línia de tecles (6 fragments) | ✓ | `↓`/`Enter`/`↑`/`L` **funcionen** |
| B15-B19 | capçalera de 2 files, 10 columnes | ✓ | «Instància» colspan 3 · «Mesura de partida» + talla |
| B20 | número de fila | ✓ | |
| B21 | desplegable de Capa | ✓ | **R2** · vocabulari de la BD |
| B22 | ⧉ duplicar | ✓ | següent capa **lliure** |
| B23 | codi del POM en or | ✓ | |
| B24 | nom del POM | ✓ | **anglès** a la cel·la (fix `7d4972dc`) |
| B25 | ⓘ «nom en català» | ✓ | ara **porta el valor** al `title` |
| B26 | ✎ «editar nom i nomenclatura» | ✓ | |
| B27-B28 | píndoles Posició · Estat | ✓ | **2 per eix**, com `EditableTable` (§9.3) |
| B29 | «＋» (Més) | ✓ | |
| B30 | cel·la de mesura de partida | ✓ | |
| B31 | ✕ treure | ✓ | |
| B32 | finder amb «C.f» / «S.l» | ✓ | sufixos resolts pel diccionari |
| B33 | «Enter confirma · Esc torna al carril» | ✓ | |
| B34 | «↑ Importar d'una fitxa» | ✓ | |
| B35 | «El que hi hagi aquí és el que se sembrarà…» | ✓ | |
| B36-B37 | «Tornar» · «Gravar» | ✓ | |
| B38-B41 | llista de fitxers: badge · nom · mida · seleccionat | ✓ | |
| B42 | 3 textos de previsualització | ✓ | DXF · RUL · genèric |
| B43 | metadades del fitxer | ✓ | |
| B44-B46 | Pujar · Descarregar · Esborrar | ✓ | `download_url` signada |

### Textos · 79 claus × 3 idiomes
`ca`/`es`/`en` amb **paritat verificada per construcció i per diff** (cap clau perduda de les que ja
hi havia). Les 64 de l'inventari + 4 d'estats asíncrons (§11) + 11 de formulari/errors que els
gestos de la maqueta impliquen. **Vocabulari de domini NO traduït**: Exterior/Folre/Entretela i
Left/Right/Relaxed/Extended vénen del diccionari de la BD (llei d'Agus, 05/08).

**Captures** (`u2/`): `A_cataleg_{ca,es,en}.png` · `B_poms_{ca,es,en}.png` · `B_fitxers_{ca,es,en}.png`.

---

## 11 · 🚩 EL QUE QUEDA OBERT

| # | Què | Per què és decisió d'Agus |
|---|---|---|
| 🚩 1 | **Els estats asíncrons** (`loading` · `load_error` · `save_error` · `saved`) | **La maqueta no en dibuixa cap i la pantalla és tota asíncrona.** He fet servir el bastiment que la casa ja té (`Center`, `Feedback`), **sense cap vocabulari visual nou**. És l'única cosa que he posat sense que la v4 ho mostri, i es treu en un bloc. |
| 🚩 2 | **El buit de llista** («aquest item no té fitxers», i la columna 3 muda quan la família no en té) | Mateix cas que 🚩1: la v4 no dibuixa el buit. Al tab Fitxers hi ha text; a la columna d'items **no n'hi he posat** (la v4 hi deixa el buit nu). Són dos criteris diferents a la mateixa pantalla i mereixen una sola decisió. |
| 🚩 3 | **El peu A37** («Què canvia respecte de la v3») | És a la maqueta, però parla al lector de maquetes, no a l'usuari. **No l'he posat.** |
| 🚩 4 | **`ItemAuthoring` i la cadena d'orfes** | Retirat de rutes (ordenat), **fitxer conservat**. És l'únic consumidor de `BaseSetPanel` → `MeasurementBaseGrid`, i `BaseSetPanel` és **l'única UI dels `ItemBaseSet`**, que R3 deixa explícitament intactes. Esborrar-lo enterraria aquella superfície. |
| 🚩 5 | **`/garment-types` segueix viva per URL** | Encara és **l'única superfície que EDITA i ESBORRA famílies i items** (i els camps `nom_en`/`nom_es`/`construccio_habitual`), cosa que la v4 no cobreix. Fora del menú, però viva: retirar-la perdria funció. |
| 🚩 6 | **El `clean()` de coherència de R3** | Afegit meu, no demanat (§7.2). Impedeix desar una etiqueta que el run no conté. Si sobra, és un bloc. |
| 🚩 7 | **`ⓘ` i `✎` són inerts** | La v4 els dibuixa amb `title` i **sense cap `onclick`**: no diu què obren. Pintats i sense acció, literal. |
| 🚩 8 | **Els POMs de grup i família estan a 0** | Les dues taules són vives i **buides**: la llei de l'acumulació no es veurà fins que algú hi declari alguna cosa (ja era 🚩3 del report anterior). |

### Verificació — l'estat real
| Control | |
|---|---|
| `manage.py check` | 🟢 net |
| `pom.test_u2_r2_capa_instancia_api` | 🟢 **7/7** |
| `tasks.test_u2_r3_proposta_item` | 🟢 **10/10** |
| `npm run build` | 🟢 |
| `eslint` (porta) | 🟢 **0 errors** · 4 avisos `set-state-in-effect` (patró de tota la casa) |
| `node --test "src/**/*.test.js"` | 🟢 **218/218** |
| Fum 3 idiomes contra el DESPLEGAT | 🟢 cap error de consola, cap literal absent, 9 captures |
| `migrate_schemas` + auditoria SQL | 🟢 `fhort` i `los`; `public` N/A per disseny |

---
---

# PART III · CORRECCIÓ CONTRA LA CAPTURA D'AGUS (07/08, 19:35)

> Commit `779a1b3b`. **L'evidència primària és la captura d'Agus, no el fum del tram anterior.**

## 12 · PER QUÈ LA CHECKLIST DE 44 ✓ ERA FALSA

No era falsa per un error de lectura: era falsa **per construcció**. La vaig recórrer en **una sola
direcció** —maqueta → pantalla— i aquesta direcció **no pot trobar una invenció per definició**:
només comprova que no falti res. Tot el que la pantalla té de més hi passa invisible.

La direcció que faltava, i que aquesta part fa, és **pantalla → maqueta**. Ha tret **10 elements**
que la maqueta no demana, dels quals **3 eren defectes reals** (els d'Agus) i **2 més els he trobat
jo pel camí**.

## 13 · ELS TRES D'AGUS

### 13.1 · L'etiqueta de tenant — FORA
Pintava «FHORT Management» al costat del títol. **Fet exacte, per al registre:** la v4 **sí** que
porta un `.chip` a l'`h1` (línia 162: `<span class="chip">Brownie</span>`). Però Agus mira la
pantalla real i la treu, i és la seva decisió: qui llegeix el catàleg ja sap de quina casa és.
**Retirada.**

### 13.2 · Les mides — el defecte era d'ESCALA, i era meu
L'escala de la casa és `--fs-caption: 8px` · `--fs-label: 10px` · `--fs-body: 12px`. **Havia fet
servir `--fs-caption` (8px) per a text de lectura**: subtítol, comptadors de columna, la línia
d'acumulació, els hints, els noms de fitxer, les píndoles d'instància i la línia de tecles. Models
fa servir `--fs-body` (12px) per a tot això.

| Element | Abans | Ara | Referència |
|---|---|---|---|
| `h1` de pàgina | `--fs-h2` pes 600 | `--fs-h2` **pes 500** | `Models.jsx:234`, idèntic |
| Subtítol | `--fs-caption` (8px) | `--fs-body` (12px) | `Models.jsx:235` |
| Molla de pa | `--fs-caption` | `--fs-body` | — |
| Capçalera de columna | `--fs-label` (10px) | `--fs-body` versaletes | — |
| Comptadors i acumulació | `--fs-caption`/`--fs-label` | `--fs-body` | `Models.jsx:470-483` |
| Capçalera de la taula | `--fs-label` | `--fs-body` | — |
| Píndoles · tecles · finder | `--fs-caption` | `--fs-body` | — |
| Llista de fitxers | `--fs-caption`/`--fs-label` | `--fs-body` | — |

> **Un judici que he hagut de fer i que declaro**: el **codi** sota el nom a les llistes es queda a
> `--fs-label` (10px). Models **no té files de dues línies** per copiar; els dos precedents de la
> casa per a aquesta forma exacta —`GarmentTypes.jsx` i `CascadeFinder`— fan tots dos nom a
> `--fs-body` i codi a `--fs-label`. Si Agus el vol a 12px, és un token.

### 13.3 · El crema — FORA de panells i capçaleres

> 📌 **PER AL REGISTRE, perquè una sessió futura no ho «restauri» citant la Regla Zero: la maqueta
> v4 SÍ que porta crema a les capçaleres** (`--head:#f5efe4` a `.colhead`, `.irowhead`, `.shead` i
> `th`). **Treure'l és una ordre d'Agus que passa PER SOBRE de la maqueta**, presa mirant la
> pantalla real dins del producte — on el crema sobre el gris de pàgina no s'assembla a cap altra
> superfície. Mateix cas que l'etiqueta de tenant (§13.1). **La v4 mana en tot menys en això.**

`--gold-pale` (#f5e6d0) i `--bg-muted` (#f5f0e8) surten de: capçaleres de les 3 columnes · peu
d'alta · capçalera de la pantalla d'item · barra de run i talla base · capçalera de la taula (i les
dues destacades, que conserven **la tinta d'or sobre blanc**) · peu de la taula · fons ratllat del
visor. **Tot a `--white`**, que és el que Models fa amb les seves targetes sobre el gris de pàgina.

**On es queda el crema, i per què** (cap dels tres és fons de panell ni de capçalera):

| On | Precedent |
|---|---|
| Fila/tab/píndola **seleccionats** | `CascadeFinder` fa exactament això per a la fila seleccionada |
| **Badge** d'extensió de fitxer | `Models.jsx:433` — badge = `gold-pale` + or + vora d'or |
| Columna **«Mesura de partida»** | La v4 la declara així (`.mes{background:var(--sel)}`) **i** `EditableTable:1295` pinta la mateixa cel·la igual |

🚩 **Si Agus també vol fora el crema d'aquests tres, són tres línies** — però anirien contra la v4 i
contra la taula del model alhora, i per això no ho he decidit jo.

## 14 · AUDITORIA BIDIRECCIONAL (b) — TOT EL QUE LA PANTALLA TÉ

Recorregut de la **pantalla**, element per element. **10 trobats.**

| # | Què hi ha a la pantalla | A la maqueta? | Decisió |
|---|---|---|---|
| 1 | Etiqueta de tenant al títol | (hi és, però Agus la treu) | ✅ **RETIRADA** aquest tram |
| 2 | `tipus` al 3r nus del visor de fitxers | ❌ la v4 hi vol una **descripció**, i `ItemFitxer` **no en té camp** | ✅ **RETIRAT** — omplir el buit amb un vocabulari de ROL era inventar-me'l |
| 3 | «Tornar» feia `history.back()` | ❌ la v4 fa `tanca()` → al catàleg | ✅ **CORREGIT** |
| 4 | **Formulari d'alta** (Codi + Nom) darrere els 3 «＋ Nou» | ❌ **la v4 ensenya els botons i mai el que obren** | 🚩 **PREGUNTAR.** Es conserva: treure'l deixaria 3 botons morts |
| 5 | **Gate de permisos** (`canEdit` amaga «＋ Nou», «Pujar», «Esborrar» i inhabilita el run i les talles) | ❌ la v4 els ensenya sempre | 🚩 **PREGUNTAR.** És llei de la casa i el backend ja hi posa `CONFIGURE`; però és comportament que la v4 no mostra |
| 6 | **Confirmació** en esborrar un fitxer | ❌ la v4 té «Esborrar» a pèl | 🚩 **PREGUNTAR.** Patró de la casa (`GarmentTypes`), i l'esborrat destrueix bytes |
| 7 | «— sense run proposat» + «sense proposta» | ❌ no a la v4 | ✅ **AUTORITZAT PER R3** («Buits = la capçalera ho diu, no s'inventa cap valor») |
| 8 | `dup_identitat` i `sense_capa_lliure` | ❌ no a la v4 | 🚩 **PREGUNTAR.** Impedeixen escriure damunt d'una germana viva en silenci — la lliçó de C1 |
| 9 | Càrrega · error · desat · 404 (`Center`/`Feedback`) | ❌ no a la v4 | ✅ **EXCEPCIÓ APROVADA** (bastiment de la casa) |
| 10 | «Aquest item no té fitxers» | ❌ la v4 no dibuixa cap buit | ✅ **EXCEPCIÓ APROVADA** — mateixa família que 9 |

> **Els 4 punts amb 🚩 no els he tocat**: tots quatre **afegeixen protecció o fan funcionar un botó
> que la v4 dibuixa**, i treure'ls seria destruir funció, no netejar una invenció decorativa. Però
> **cap dels quatre és a la maqueta**, i per la Regla Zero això els fa decisió d'Agus, no meva.

**També comprovat i net:** cap clau i18n morta (les 5 de capçalera s'usen via literal de plantilla,
que el grep no veu) · cap clau usada sense definir · cap `hex` (tots els colors són tokens) · cap
icona `-filled` · IBM Plex Mono a tot arreu.

## 15 · VERIFICACIÓ D'AQUEST TRAM

| Control | |
|---|---|
| `npm run build` | 🟢 |
| `eslint` (porta) | 🟢 **0 errors** · 4 avisos (patró de tota la casa) |
| Fum 3 idiomes contra el DESPLEGAT | 🟢 «FUM NET: cap error, cap literal absent» |
| Captures comparatives | `tres/1_maqueta_v4.png` · `tres/2_cataleg_corregit.png` · `tres/3_models_referencia.png` |
| Captures de la pantalla | `u2/A_cataleg_{ca,es,en}.png` · `u2/B_poms_{ca,es,en}.png` · `u2/B_fitxers_{ca,es,en}.png` |

> ⚠️ **`Models` es veu BUIDA a la captura de referència** i no és un defecte de la captura: el
> tenant `fhort` **no té cap model** (46 esborrats en un tram anterior). La comparació d'escala
> tipogràfica es fa igualment amb el títol, el subtítol i la barra de filtres, que sí que hi són.

## 16 · LA LLIÇÓ DE MÈTODE

**Una checklist d'una sola direcció no és una verificació, és un inventari de mancances.** La
direcció maqueta → pantalla només pot trobar el que falta; per trobar el que sobra cal recórrer la
**pantalla**. Les tres coses que Agus va veure d'un cop d'ull eren totes de la segona direcció, i cap
d'elles podia sortir de la primera.

👉 **A partir d'ara, tota checklist contra una maqueta és bidireccional**, i la segona direcció es
recorre sobre la pantalla desplegada, no sobre el codi.
