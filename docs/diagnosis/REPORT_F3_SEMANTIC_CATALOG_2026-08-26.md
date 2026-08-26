# F3 · Catàleg semàntic — acta

**Data:** 2026-08-26 · **Patró B** · **Branca:** `f3-semantic-catalog` → merge a `dev`
(4 commits + merge, **cap push**) · **Worktree:** `/var/www/ftt-f3`
**Font del vocabulari:** `REPORT_GCD_ONTOLOGY_2026-08-25.md` (GarmentCode@d449629, MIT)
**Font de les freqüències:** `ftt_corpus` (128.974 designs, CC-BY-4.0), **read-only**

> ## ⏸️ ESTAT: FASE B ATURADA ESPERANT L'AGUS
>
> **Les migracions estan aplicades i el codi desplegat. La SEMBRA no.** Les quatre taules
> són **buides als tres esquemes** i esperen l'OK sobre la llista de
> `docs/ordres/SEED_SEMANTIC_CATALOG_DRYRUN_2026-08-26.md`. Res del que hi ha aquí no és
> reversible-amb-pressa perquè res de dada no s'ha escrit.
>
> | fase | estat |
> |---|---|
> | A · migracions | ✅ aplicades i auditades amb `\d` als 3 esquemes |
> | B · sembra | ⏸️ **dry-run fet, llista lliurada, esperant OK** |
> | C · tests | ✅ `Ran 23 tests · OK` |
> | D · acta | 🔵 aquesta (es completa amb les xifres de l'apply) |

---

## 0 · Les quatre coses que val la pena que quedin

1. **🚨 El `UNIQUE` que havia d'impedir la costura duplicada no protegia RES**, i el va
   descobrir un test que va donar vermell amb la fila duplicada ja dins. §3.
2. **🚨 El cens del corpus va auditar el meu propi vocabulari**: quatre parelles reals
   sense plantilla, i la més gran (241.004 costures) no era vocabulari nou sinó una regla
   del codi que jo havia acotat massa estret. §4.
3. **🚨 Migrar des del worktree va TRENCAR staging** i el trencament era invisible: el
   gunicorn desplegat no podia crear cap `PatternPiece`. §6.
4. **La clausura dels 24 rols aguanta 107× la mostra amb què es va provar.** L'informe la
   va tancar sobre 1.200 patrons; sobre els 128.974 del corpus segueixen sent exactament
   24, ni un més. §5.

---

## 1 · Fase A · Les migracions, i què diu la BD de debò

### 1.1 A1 · Els noms de taula, verificats abans d'escriure res

L'informe avisa que els noms del seu DDL són defaults de Django i que s'han de verificar
contra l'esquema viu (§5.5, última nota). Fet amb `\dt` abans de la primera línia de model:

| esperat | trobat | on |
|---|---|---|
| `pom_patternpiecerole` | ✅ | `public` **i** `fhort` **i** `los` |
| `tasks_garmenttypeitem` | ✅ | **NOMÉS** `fhort` i `los` — **no és a `public`** |
| `patterns_patternpiece` / `patterns_patternsegment` | ✅ | `fhort`, `los` (tenant-only) |

**Aquella tercera fila va decidir el disseny de dues columnes.** §1.3.

### 1.2 A2-A5 · Què s'ha creat

| migració | què fa |
|---|---|
| `pom.0084_cataleg_semantic_f3` | 5 taules noves: `pom_edgerole`, `pom_landmarkrole`, `pom_seampairtemplate`, `pom_garmenttypeitemedgeprofile`, `pom_gcpiecerolemap` |
| `pom.0085_unicitat_generica_seampairtemplate` | parteix el UNIQUE de `SeamPairTemplate` en dues constraints parcials (§3) |
| `patterns.0018_patternpiece_face` | `PatternPiece.face` `('front'\|'back'\|'')`, default `''`, indexat (D1) |
| `patterns.0019_patternsegment_edge_role` | `PatternSegment.edge_role` FK → `pom.EdgeRole`, NULL, `RESTRICT` |
| `seed_pattern_piece_roles` | +`pant`, +`hood`, +`godet_insert` (D6) — 30 → 33 slugs |

### 1.3 🚨 `db_constraint=False` a les FK cap a `tasks.GarmentTypeItem`

El DDL de l'informe declara les dues FK com a constraints normals. **Amb constraint real
la migració PETA**, i el missatge és aquest, mesurat:

```
django.db.utils.ProgrammingError: relation "tasks_garmenttypeitem" does not exist
```

`pom` viu a SHARED **i** a TENANT; `tasks` només a TENANT. Quan `migrate_schemas` arriba a
`public`, la taula de destí **no hi és i no hi serà mai**. La casa ja ho tenia resolt i jo
no ho vaig veure a la primera: les migracions `0025`, `0040` i `0047` porten
`db_constraint=False` explícit des del primer dia.

> 🔑 **La lliçó, i no és la que semblava.** El meu primer `\d` sobre `pom_garmentpommap`
> va mostrar columna i índex sense constraint, i en vaig deduir que django-tenants les
> retirava sol. **Era fals**: algú les havia declarat explícitament. Un `\d` diu com és una
> taula avui, **no per què**; el «per què» és a la migració, i llegir-lo és el que separa
> heretar una llei de reinventar-la malament.

### 1.4 A6 · Auditoria `\d` directa (django-tenants pot donar un OK enganyós)

Les 5 taules noves existeixen als **tres** esquemes (`public`, `fhort`, `los`). Les 2
columnes noves existeixen als **dos** tenants, i la FK de `patterns_patternsegment` apunta
a **la còpia de cada tenant**:

```
fhort: FOREIGN KEY (edge_role_id) REFERENCES fhort.pom_edgerole(id)
los:   FOREIGN KEY (edge_role_id) REFERENCES los.pom_edgerole(id)
```

⚠️ **`RESTRICT` no surt al `\d` i no hi sortirà mai.** Django no emet cap `ON DELETE` a la
BD: `RESTRICT` i `PROTECT` els fa complir l'ORM. Qui auditi aquesta llei amb `psql` no la
trobarà. Per això té un test propi (§7), i per això queda escrit aquí.

---

## 2 · Fase B · Què s'escriuria (ATURAT)

| taula | files | origen |
|---|---:|---|
| `pom_edgerole` | 27 | SEED · `is_system` · 24 anatòmics + 3 estructurals |
| `pom_landmarkrole` | 8 | SEED · `is_system` · tots `derivable=True` |
| `pom_seampairtemplate` | 53 | IMPORT · `pendent_revisio=True` · totes amb GTI NULL |
| `pom_gcpiecerolemap` | 24 | el traductor GarmentCode→FTT |
| `pom_garmenttypeitemedgeprofile` | **0** | **buida a posta** — feina de la sessió Montse |

**112 files × 3 esquemes.** La llista sencera, fila a fila i amb `source_ref`, és a
`docs/ordres/SEED_SEMANTIC_CATALOG_DRYRUN_2026-08-26.md`.

La comanda llegeix `ftt_corpus` **en calent i en read-only** amb dos panys i no un: el rol
`corpus_ro` (que només té `SELECT`) **i** `conn.set_session(readonly=True)`. El rol el pot
canviar algú; la connexió no.

---

## 3 · 🚨 El `UNIQUE` que no tancava cap porta

La convenció d'ordenació canònica que el brief demanava **implementada i no comentada**
hi era: `SeamPairTemplate.ordena()` (funció pura), `canonitza()` i `save()` que l'aplica
sempre. I un `UniqueConstraint` sobre les 8 columnes.

El test va escriure la mateixa costura dues vegades amb els costats girats, i **la segona
va entrar**:

```
AssertionError: IntegrityError not raised
```

`garment_type_item` és nul·lable. **A Postgres dos NULL no són iguals**, o sigui que un
índex únic que porti aquella columna **no casa mai** mentre sigui NULL. I genèriques
—`garment_type_item = NULL`— ho són **les 53 plantilles que F3 sembra**: totes. El pany hi
era, i no protegia ni una fila.

És exactament la llei de `ftt-diagnosi-pre-sembra-v4`: *una FK nul·lable a la clau trenca
la unicitat EN SILENCI*. Partit en dues constraints parcials, verificades amb `\d`:

```
uniq_seampairtemplate_canonic          … WHERE garment_type_item_id IS NOT NULL
uniq_seampairtemplate_canonic_generic  … WHERE garment_type_item_id IS NULL
```

> 🔑 **Un test d'igualtat que no has vist VERMELL no val.** Aquest en va donar un, i la
> frase exacta —`IntegrityError not raised`— era la que calia veure. Si l'hagués escrit
> després de la constraint parcial, hauria donat verd des del primer moment i no hauria
> demostrat res.

---

## 4 · 🚨 El cens del corpus va auditar la MEVA llista

La llista de plantilles surt de les 22 regles de costura del codi (informe §4.2). En
mesurar-la contra el corpus, la comanda imprimeix les parelles que **el corpus veu i cap
plantilla no recull**. N'hi havia quatre, i la primera era enorme:

| parella òrfena | costures | patrons | què era |
|---|---:|---:|---|
| `cuff/front ↔ cuff/back` | **241.004** | 47.912 | **la regla #16 mal acotada per mi** |
| `cuff/front ↔ pant/back` | 7.346 | 3.673 | el creuat de la regla #14 |
| `centre · collar/back ↔ collar/back` | 16.296 | 16.296 | 🚩 **l'ontologia no té slug per a això** |
| `centre · collar/front ↔ collar/front` | 7.077 | 7.077 | 🚩 idem |

La primera no era vocabulari nou: la regla #16 és `bands.py:73-75`, les costures laterals
d'un `StraightBandPanel`, i **la cinturilla no és l'únic panell d'aquella classe** — un
puny és una banda al voltant del braç o de la cama i es tanca amb les mateixes dues
costures. Tres files afegides (#16-cuff i els dos creuats de #14); **53 plantilles, no 50**.

Les dues últimes es queden fora a posta: `collar_side_seam` i `collar_outer_edge` existeixen
a §2.4, però **cap slug per al centre del coll**. Inventar-ne un ara seria vocabulari sense
evidència de codi. Va a la llista de la Montse.

> 🔑 **El cens no serveix només per omplir columnes de freqüència: serveix per auditar el
> vocabulari.** Una parella òrfena amb 241.000 costures no és soroll, és una regla que et
> vas deixar. Per això la llista d'òrfenes viu dins de la comanda (`--llista` la imprimeix
> sempre) i no és un fitxer d'un dia.

### 4.1 Un ZERO és una mesura, i n'hi havia dos que ho eren

La primera versió deixava a NULL les plantilles que el cens no portava. **Fals**: el cens
recorre els 3,9 M de costures del corpus sencer, o sigui que una clau absent vol dir
*mai passa en 128.974 designs*. Corregit: `observed_seams=0` amb denominador honest i
`observed_ref` que diu literalment `ZERO MESURAT`.

| plantilla | patrons | el seu mirall | patrons |
|---|---:|---|---:|
| `back/back.armhole ↔ sleeve/front.sleeve_cap` | **0** | `front/front.armhole ↔ sleeve/back.sleeve_cap` | 35.121 |
| `cuff/back.band_attach_upper ↔ pant/front.cuff_line` | **0** | el seu germà | 3.673 |

El cap de màniga travessa l'espatlla: la meitat del **darrere** de la màniga cus també
contra la sisa del **davant**, però mai al revés. Amb NULL, aquesta asimetria hauria
quedat tapada com si no s'hagués mirat.

### 4.2 El denominador, mesurat i no endevinat

`observed_den` **no són mai els 128.974**. És el total de designs de les categories on
**totes dues peces hi apareixen**, i aquesta llista es mesura:

| tipus de parella | denominador | categories |
|---|---:|---|
| tors (`front`↔`back`) | 90.273 | dresses, jumpsuits, upper_garments |
| pantaló | 17.130 | jumpsuits, pants |
| faldilla | 77.690 | dresses, skirts |
| banda de cintura | 128.974 | les cinc (una cinturilla surt a tot arreu) |

La regla i les categories de cada fila viatgen dins d'`observed_ref`: un percentatge sense
el seu denominador escrit al costat és una xifra que menteix sola.

### 4.3 ⚠️ El sostre del corpus, dit a la cara

`stitch` desa l'**índex** de vora (`{panel, edge}`); els noms d'interfície no se
serialitzen (informe §4.1). O sigui que **el corpus no sap què és una vora**: les files #1
i #2 —espatlla i costat del tors— són totes dues `front↔back` i **comparteixen xifra**.
Les 436.842 costures són la SUMA de les dues. No és un error de mesura, és el sostre de la
font, i `observed_ref` ho diu a totes dues files.

---

## 5 · La clausura dels 24 rols, re-mesurada 107× més gran

L'informe tanca el vocabulari de rols sobre 1.200 patrons (§1.3). La normalització de la
comanda —quatre passades, perquè GarmentCode posa el costat en tres llocs diferents segons
la família (`left_ftorso`, `sl_left_cuff_f`, `pant_l_cuff_f`, `pant_f_l`)— dona, sobre els
**128.974** designs:

```
SELECT count(distinct role) → 24
```

**Exactament els mateixos 24, ni un més.** La clausura no era un artefacte de la mostra.

I la reducció cap a FTT també queda mesurada: **24 rols → 11 slugs**. Vuit rols cauen tots
sobre `cuff` (quatre conceptes × dues cares, que l'eix `face` absorbeix en dos destins).
Aquest recompte va corregir un «quatre» que jo havia escrit a tres docstrings i que el test
`test_els_24_cauen_sobre_11_slugs_i_no_mes` va tombar amb `8 != 4`.

---

## 6 · 🚨 Migrar des del worktree va trencar staging, i no cantava

`migrate_schemas` es va córrer des de `/var/www/ftt-f3`. La BD va quedar amb
`patterns_patternpiece.face NOT NULL`, i el gunicorn seguia servint el codi de `dev`, que
no coneix aquella columna. Resultat, mesurat amb un `INSERT` dins d'un `ROLLBACK`:

```
ERROR: null value in column "face" of relation "patterns_patternpiece"
       violates not-null constraint
```

**Importar un patró a staging hauria petat**, i cap `check`, cap test i cap `\d` ho deia:
el codi del disc era bo, la BD era bona, i el que estava trencat era la distància entre
els dos. És la família de `ftt-backend-desplegat-vs-disc` i de
`ftt-migracions-es-commiten-en-aplicar-se`, amb una cara nova: **aquí la divergència no la
crea no-commitar, la crea migrar des d'un worktree que encara no s'ha desplegat.**

Tancat: merge a `dev` + `systemctl restart ftt-staging.service` (WorkingDirectory verificat
= `/var/www/ftt-staging/backend`) + smoke. **Es va desplegar només l'esquema i el codi; la
sembra segueix aturada.**

```
active · /api/v1/  401 (auth, no 500) · crear PatternPiece: OK · face=''
EdgeRole: 0 · SeamPairTemplate: 0
```

> 🔑 **Un tram que migra ha de desplegar-se en acabar la fase A, no en acabar el tram.**
> Entre la migració i el restart hi ha una finestra en què l'app viva no sap el que la BD
> ja sap, i les columnes `NOT NULL` la converteixen en una finestra amb dents.

---

## 7 · Fase C · Els tests

`backend/fhort/pom/tests_semantic_catalog.py` — fitxer **nou i a part** de `pom/tests.py`,
llei de suites proporcionals: el tram s'executa sol i no arrossega la suite de `pom`.

```
FTT_TEST_DB=test_ftt_f3 venv/bin/python manage.py test fhort.pom.tests_semantic_catalog \
    --settings=fhort.settings_test --keepdb
Ran 23 tests in 168.594s · OK
```

| classe | què defensa |
|---|---|
| `OrdenacioCanonicaTest` (3) | (a,b) i (b,a) són una sola fila, i el pany és el UNIQUE i no l'ORM per educació |
| `IdempotenciaDeLaSembraTest` (4) | 2a i 3a passada = 0 creats · sense corpus els `observed_*` són NULL i no zero · cap plantilla apunta a un rol de vora inexistent |
| `EdgeRoleRestrictTest` (3) | RESTRICT bloqueja · un rol orfe SÍ s'esborra (un pany que no deixa passar res és un mur) · `nom` i `edge_role` conviuen |
| `DerivacioDeLandmarksTest` (8) | l'HPS es CALCULA sobre un mini-graf sintètic · una vora que falta aixeca excepció i no torna `None` · només 2 regles porten evidència i és la mateixa |
| `MapaGCTest` (5) | els 24 rols resolen · 5 NOMÉS gràcies a D6 · cap plantilla usa una peça fora del catàleg |

### 7.1 `pom/landmarks.py` — la peça que F4 hereta

El resolutor és **pur**: ni BD, ni Django, ni `PatternSegment`. Rep una llista de `Tram`
(rol + dos extrems) i torna un punt. Que sigui pur vol dir que F4 el pot cridar tant sobre
geometria real com sobre el graf sintètic dels tests, i que el dia que una regla falli es
podrà reproduir sense muntar un tenant.

Dues decisions que hi són a posta:

- **`LandmarkNoResolt` i mai un `None`.** «No hi ha punt» i «hi ha punt i és l'origen» no
  s'han de poder confondre en una expressió: un `None` silenciós acaba sent un `(0,0)` tres
  capes més amunt.
- **`shared_endpoint` exigeix EXACTAMENT un comú.** Zero vol dir que les vores no es toquen;
  més d'un vol dir que es toquen dos cops. Cap dels dos no es resol «triant-ne un».

---

## 8 · Desviacions del DDL de l'informe, amb motiu

| desviació | motiu |
|---|---|
| `db_constraint=False` a les 2 FK cap a `tasks.GarmentTypeItem` | **Mesurat**: sense això la migració peta a `public`. §1.3 |
| DOS `UNIQUE` parcials a `SeamPairTemplate` (el DDL no en porta cap) | Un de sol no protegeix res amb la FK a NULL. §3 |
| `UNIQUE` de `GTIEdgeProfile` inclou `face` | El DDL llistava el camp però el deixava fora de la clau |
| `mates_slug` és `''` i no `NULL` | Estil de casa: cap `CharField` nul·lable al catàleg |
| `zone` de `cuff_line` = `any` | Un puny és de màniga **i** de cama; triar-ne una seria mentir |
| `centre_front`/`centre_back` amb `kind='seam'` | §2.4 diu «seam/fold»; GarmentCode sempre en fa costura, i el doblec ja el registra `PatternPiece.doblec_original` |
| `CatalegSemanticOrigenMixin` | Els 5 camps d'auditoria surten a 4 taules; escrits 4 cops, és on començarien a divergir |
| `GCPieceRoleMap` (no és al DDL) | La demana el brief (A3): taula i no diccionari en un script, perquè F4 l'ha de consultar en calent |
| 4 files per a la regla #3 (i 3 per a la #14) | El cap de màniga travessa l'espatlla; un dels creuats surt a ZERO i el zero és una dada |
| Les regles #7 i #8 donen UNA plantilla | §2.4 té un únic slug per a les dues interfícies; inventar-ne un segon per simetria seria vocabulari sense evidència |

---

## 9 · Què queda per a la sessió Montse

1. **`GarmentTypeItemEdgeProfile` sencera.** Taula creada i buida: cal mapar GTIs reals de
   `fhort` i `los` contra el vocabulari genèric.
2. **Revisió de `nom_ca` / `nom_es`** dels 27 rols de vora i els 8 de punt. Els `slug` són
   el contracte i no es toquen; els noms es reescriuen amb una passada més de la sembra
   **sense migrar cap fila**.
3. **D3: els llindars.** `core` ≥90 % / `common` 25-90 % / `rare` <25 % són els graus del
   precedent i estan per confirmar. **Els denominadors ja estan arreglats** (§4.2); el que
   falta és decidir on es tallen.
4. **Els dos slugs que falten:** el centre del coll, davant i darrere (§4). 23.373 costures
   sense nom.
5. **D5, la pregunta ben feta:** no és si GarmentCode omet les pinces de davant, és **si
   una pinça de cintura al davant s'espera als garments d'FTT**.

## 10 · Què desbloqueja

- **F4 · el banc de veïns.** `pom_gcpiecerolemap` és el traductor que li permet llegir un
  panell del corpus en vocabulari de casa, i `PatternPiece.face` és l'eix pel qual filtrarà
  abans de comparar contorns.
- **El bloquejant A11** d'`INFORME_CORPUS_I_AUTOANCORATGE_2026-08-24` («cap dada del
  sistema identifica l'HPS») deixa de ser un bloquejant: `pom/landmarks.py` el calcula, i
  el test ho demostra. ⚠️ **Sobre un graf que algú ha d'haver etiquetat** (D2): la regla és
  sòlida, però que un DXF del taller es pugui etiquetar és una altra pregunta i segueix
  oberta.
- **La gramàtica de costura amb evidència**, que és el que un aparellador de vores
  necessita per proposar sense inventar — i `co_generated` li diu on pot confiar en comptes
  d'apostar.

## 11 · Fronteres respectades

Cap escriptura a `ftt_corpus` · cap dada de MODEL tocada · PROD ni s'ha mirat · cap push ·
`migrate_schemas` sense `--schema` · restart només de `ftt-staging.service`.
