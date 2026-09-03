# PLA D'IMPLEMENTACIÓ — MOTOR DE PATRONS · Traçadora end-to-end

> **Tipus:** pla executable. Briefs per sprint escrits perquè sessions autònomes de
> Claude Code (models menors) els implementin seqüencialment amb supervisió mínima.
> **Data:** 2026-07-12. **Autor:** sessió d'arquitectura Claude chat + Agus (Patró C).
> **Base:** `MOTOR_DE_PATRONS_V2.md` + esmenes §4.4 (capa FTT-POM, operació atòmica,
> parsing vs anotació, bases GTI).
> **Estat:** APROVAT per arrencar S0. Els briefs S1+ es refinen amb l'evidència de S0
> abans de llançar-los (el pla fixa QUÈ i les fronteres; la diagnosi fixa el COM local).

---

## 0. ESTRATÈGIA — LA TRAÇADORA

**Un fil prim que travessa totes les capes sobre UN fitxer real abans de cap amplada:**

```
importar AMELIA (DXF+RUL, Tuka)
  → veure (SVG servidor, després Konva)
  → anotar A MÀ (4+ POMs, 2+ costures; sense IA)
  → escalar amb una GradingVersion aprovada EXPLÍCITA (grading pinçat)
  → exportar DXF+RUL amb capa FTT-POM (gate humà)
  → reimportar el NOSTRE fitxer i llegir la capa POM com a taula
  → comparador round-trip verd
```

**Per què:** els límits del mòdul es descobreixen amb l'espina, no s'especulen.
Construir les fases PAT en amplada abans de travessar és teoritzar.

**FORA de la traçadora (registrat al backlog §3, prohibit dins dels sprints S0–S8):**
suggeriment IA d'ancoratge · autoria de biblioteca GTI (només l'ESQUEMA entra) ·
resolució G6 (s'esquiva pinçant la versió) · PAT-3 rectificació · PAT-4 nesting ·
prova round-trip al CAD real amb la Montse · regles fines de distribució de deltes.

**Pinçament del grading (decisió d'arquitectura):** la projecció GradedSpec→GradeRule
(S7) rep `grading_version_id` EXPLÍCIT amb `aprovada=True` com a paràmetre d'entrada.
Cap resolució automàtica de "quin ruleset mana" → les col·lisions dual-path de G6 no
es toquen ni es trepitgen. **G6 continua sent PREREQUISIT per GENERALITZAR** la
projecció (post-traçadora), no per a la traçadora.

**Ritme:** cada sprint = 1 sessió Claude Code autònoma amb regla del verd. S0 és
Patró A pur; S1–S8 són Patró B amb autorització d'Agus sprint a sprint.

---

## 1. REGLES TRANSVERSALS (copiar a la capçalera de TOTS els briefs)

```
[REGLES TRANSVERSALS · MOTOR DE PATRONS · van a tot brief]

MÈTODE
- Patró B autoritzat NOMÉS per a l'abast del sprint. Res fora d'abast, ni "de passada".
- Regla del verd: continua autònomament si tot verd; atura't i reporta a la primera
  contradicció de paradigma, check vermell o terreny no cartografiat.
- Codi mínim · un concern per commit · git add SELECTIU (mai -A) · missatge de commit
  amb prefix del sprint (ex. "S1:") · git log -1 després de cada commit · MAI push.
- manage.py check abans de cada commit backend · npm run build abans de cada commit
  frontend · restart ftt-staging.service després de canvis backend.
- Migracions: MOSTRAR el fitxer generat abans d'aplicar · migrate_schemas (mai
  --schema) · auditar la BD directament després (quirk django-tenants: no fiar-se
  de l'OK de Django).
- Al final del sprint: actualitzar ESTAT_PROJECTE.md (secció MOTOR DE PATRONS) al
  servidor. MAI commitejar fitxers d'estat.

HEXAGONAL (llei dura del motor)
- backend/fhort/patterns/engine/ és un paquet Python PUR. PROHIBIT importar django,
  rest_framework, o qualsevol model ORM dins engine/. El guard automàtic
  test_engine_purity (S1) ho vigila: si és vermell, el sprint és vermell.
- Els ports (Protocols) els defineix engine/ports.py; els adaptadors viuen FORA
  d'engine (patterns/adapters.py, patterns/models.py, patterns/views.py).
- Engine treballa amb les seves dataclasses, mai amb instàncies ORM.

DOMINI (fronteres no negociables)
- CAP primitiva de creació de geometria en CAP sprint (frontera §3.3: moure punts sí;
  pinces noves / vores partides / peces noves, MAI).
- LLM mai dibuixa coordenades. A la traçadora la IA no apareix enlloc.
- Capa FTT-POM: projecció, mai font de veritat (V2 §4.4 E1).
- Sobirania del Model: tot el que s'instancia pertany al Model.

UI/CONVENCIONS
- i18n gate: cap sprint amb UI tanca amb strings sense cablejar (checklist 5 punts).
- Icones Tabler outline (mai -filled). Colors per tokens CSS; DINS de canvas Konva,
  paleta literal KONVA_COL. L'SVG servidor és DOCUMENT: paleta pròpia fixa documentada
  al codi, no tokens.
- TaskTypes nous pattern_*: seed de sistema idempotent, referència per code slug,
  cap escriptor tenant-side (G9).

ENTORN
- Staging: /var/www/ftt-staging, branca dev, servei ftt-staging.service (port 8001),
  venv backend/venv. curl SEMPRE amb -H "Host: staging.fhorttextile.tech".
- Zones intocables del servidor: /var/www/assessment, /var/www/trading, /var/www/webs.
```

---

## 2. MAPA DE SPRINTS

| Sprint | Nom | Capa | Depèn de | Fita |
|---|---|---|---|---|
| **S0** | Diagnosi de terreny | — (read-only) | — | Mapa verificat |
| **S1** | Engine · lectura | motor pur | S0 | AMELIA i Polypattern llegits, tests verds |
| **S2** | Engine · escriptura + FTT-POM | motor pur | S1 | Round-trip propi verd |
| **S3** | Persistència + API | backend | S2 | Upload+parse+SVG per API a staging |
| **S4** | Tab Patró read-only | UI | S3 | **DEMO INTERNA** (= PAT-0a) |
| **S5** | Visor Konva | UI | S4 | Demo client (= PAT-0b) |
| **S6** | Anotació manual | full-stack | S5 | POMs+Sew ancorats a AMELIA (= PAT-1 nucli) |
| **S7** | Escalat + export + gate | full-stack | S6 | DXF niada exportat (= PAT-2 nucli pinçat) |
| **S8** | Tancament traçadora | QA/doc | S7 | E2E guionitzat verd + límits reals censats |

Seqüència estrictament lineal. Cap sprint arrenca sense el verd (i el QA d'Agus quan
n'hi ha) de l'anterior.

---

## S0 — DIAGNOSI DE TERRENY (Patró A · read-only · 1 sessió)

**Sortida:** `docs/diagnosis/DIAGNOSI_MOTOR_S0.md`. Evidència `fitxer:línia` a tot.
STOP absolut: cap escriptura, cap migració, cap seed.

- **B1 — Pipeline de fitxers.** `ModelFitxer` i `ItemFitxer`: models exactes, patró de
  versionat (`versio`/`versio_anterior`), views d'upload, on s'emmagatzemen els binaris
  (media root per tenant — el Gate 1 del deploy 12/07 en va confirmar l'arrel), mides
  màximes, permisos. Les migracions `models_app/0054_itemfitxer`, `0055_..derivat_de_item`,
  `0056_..derivat_de_model`: què fan exactament — és el patró de sembra item→model que
  la biblioteca GTI (E4) reutilitzarà.
- **B2 — `GarmentTypeItemAsset`.** Implementat o només disseny (doc 29/06)? Si `ItemFitxer`
  n'és la materialització, dir-ho amb evidència.
- **B3 — Material real.** Inventari dels DXF+RUL al servidor i/o repositori: AMELIA AZUL
  (Tuka) i el fitxer Polypattern. Ubicació, mida, integritat (capçalera llegible). Si NO
  hi són: FLAG VERMELL → Agus els puja abans de S1.
- **B4 — Fitxa del Model.** Estructura de tabs de `ModelSheet.jsx`, mecanisme exacte
  d'afegir un tab, convenció de rutes i lazy-loading si n'hi ha.
- **B5 — Límits d'upload.** nginx `client_max_body_size` per vhost d'staging (cicatriu
  coneguda: al bloc 443, mai al de redirect-80) + settings DRF de mida.
- **B6 — Render SVG.** matplotlib present a requirements.lock? (dependència de l'add-on
  `drawing` d'ezdxf). Si no hi és: pesar-ne el cost vs un render SVG propi des del model
  intern (línies + polilínies — trivial). Recomanar amb evidència; es decideix a S3.
- **B7 — Contracte del grading.** Com s'identifica la `GradingVersion` aprovada d'un
  model (camps, relació amb `GradedSpec`); forma EXACTA de `GradedSpec` (per POM×talla:
  camps, tipus, signe dels deltes). Això és el contracte del port `GradingSource`.
- **B8 — TaskTypes.** `pattern_digit` / `pattern_cad` / `scaling`: existeixen com a seed?
  On viuen, com es referencien (verificar compliment G9), com s'obre/tanca un `ModelTask`
  d'un tipus donat des del frontend (mecanisme a reutilitzar a S6-T5).
- **B9 — Convencions d'app.** `commerce/` com a referència: com s'instal·la una app a
  TENANT_APPS, convencions d'urls/serializers/permisos, on van els tests.

---

## S1 — ENGINE · LECTURA (paquet pur)

**Objectiu:** FTT llegeix DXF-AAMA + RUL reals i els converteix al model geomètric
intern, amb empremta de fidelitat. Zero Django, zero UI, zero migracions.

- **T1 — Esquelet.** App `patterns/` mínima (registrada a TENANT_APPS, sense models
  encara) + paquet `patterns/engine/` amb `__init__`, `geometry.py` (dataclasses:
  `PieceData`, `BoundaryData`, `PointData` amb kind turn/curve, `SegmentRange`,
  `POMAnchorData`, `GradeRuleData`, `Fingerprint`, `PatternDocument` com a agregat) —
  NO confondre amb els models Django de S3.
- **T2 — Ports.** `engine/ports.py`: Protocols `FormatCodec` (read/write),
  `GradingSource` (deltes per POM×talla d'una versió donada), `GeometryStore`
  (persistència del resultat). Contractes en dataclasses, mai ORM.
- **T3 — Reader AAMA** (`engine/aama_reader.py`, sobre ezdxf):
  - BLOCKS → peces; capes 1 (tall), 14 (cosit), 8 (internes), 2 (turn), 3 (curve),
    4 (piquets), 7 (grain), 6 (mirall).
  - Normalització d'unitats: `$INSUNITS`/`$MEASUREMENT` + factor per font (cas
    Polypattern ×10 verificat empíricament al juny).
  - Detecció de doblec PER GEOMETRIA (la capa 6 és inconsistent entre exports) +
    materialització de simetria: desplegar la peça sencera, anotar `doblec_original`.
  - Captura d'EMPREMTA completa: versió AAMA (2.1.1 vs 292-B), ordre de seccions,
    codis de capa, separador decimal (Polypattern usa COMA "1,0"), codi d'unitats,
    rastre literal per entitat (ezdxf preserva tags desconeguts — aprofitar-ho).
  - Degradació elegant: entrades reals mai peten el parser; error estructurat amb
    detall, mai excepció crua.
- **T4 — Reader RUL** (`engine/rul_reader.py`): tabular — talles, talla base,
  `RULE: DELTA n` → `GradeRuleData` (Δx,Δy per talla per regla).
- **T5 — Reader capa FTT-POM** (`engine/ftt_pom_layer.py`, meitat lectura): parseja
  línies de mesura + TEXT de codi + TEXT de metadades de la capa pròpia. Testejat amb
  un fixture SINTÈTIC (el writer real arriba a S2; definir aquí l'especificació de la
  capa — noms, estructura de TEXT — en un docstring canònic únic que S2 consumeix).
- **T6 — Tests** (`patterns/tests/` + `tests/fixtures/` amb còpies dels fitxers reals):
  AMELIA (Tuka) i Polypattern. Asserts: nº de peces, nº de punts per peça, unitats
  normalitzades a mm, doblec detectat on toca, deltes RUL llegits (encara que siguin 0
  a AMELIA — l'estructura compta), empremta amb els camps clau.
- **T7 — Guard de puresa** (`test_engine_purity.py`): escaneja els imports de tots els
  .py d'engine/ (AST) i falla si apareix django/rest_framework; a més importa
  `patterns.engine` en un subprocess sense DJANGO_SETTINGS_MODULE i verifica que no peta.

**Verd:** pytest verd (fitxers reals inclosos) + manage.py check + `git log` net + CAP
migració generada.

---

## S2 — ENGINE · ESCRIPTURA (reproducció pura + capa FTT-POM)

**Objectiu:** desriscar la capa crítica (exportació) el més aviat possible. Encara zero
Django.

- **T1 — Writer AAMA** (`engine/aama_writer.py`): reproducció pura des de l'empremta —
  reordenar seccions, respectar separador decimal, codis d'unitats i convencions del
  perfil de destí. Perfils: `tuka` i `polypattern` (des dels fitxers reals); `gerber` i
  `clo` com a ESBORRANYS derivats de les mostres de ksons/astm-parser (llegir per
  entendre el format; MAI copiar codi — respectar llicències).
- **T2 — Writer capa FTT-POM** (completa `ftt_pom_layer.py`): emet la capa segons
  l'especificació canònica de S1-T5 (línies de mesura + TEXT codi + TEXT metadades amb
  placeholder de versió). Paràmetre include_ftt_pom_layer al writer (per poder exportar
  sense capa si un destí la rebutgés).
- **T3 — Writer RUL** des de `GradeRuleData`.
- **T4 — Re-plegat del doblec** quan l'empremta indica que el CAD d'origen treballava
  a mitges (invers de la materialització de S1).
- **T5 — Comparador round-trip** (`engine/roundtrip.py`): `read(write(read(f)))` ≡
  `read(f)` — comparació SEMÀNTICA (peces, punts amb tolerància configurable en µm,
  capes, deltes, metadades) amb informe de diferències llegible. ⚠️ Aquesta eina és
  PERMANENT: és la validació barata de tota exportació futura i l'instrument de la
  prova Polypattern de la Montse (backlog).

**Verd:** round-trip semànticament idèntic amb AMELIA i Polypattern + round-trip amb
capa FTT-POM sintètica (escriure→llegir→taula de POMs idèntica) + guard de puresa verd.

---

## S3 — PERSISTÈNCIA + API (adaptadors)

**Objectiu:** el motor s'endolla a FTT. Primera migració del domini.

- **T1 — Models Django** (`patterns/models.py`):
  - `PatternFile`: `model` FK null · `garment_type_item` FK null · **CheckConstraint
    XOR (exactament un dels dos NOT NULL)** · `source_asset` FK null (traçabilitat de
    sembra, S0-B2 en confirma el target) · `versio`/`versio_anterior` (patró
    `ModelFitxer` literal, S0-B1) · `font_cad` · `escala_mm` · `empremta` JSONField ·
    fitxer DXF + fitxer RUL pel pipeline d'emmagatzematge existent.
  - `PatternPiece` (`pattern_file` FK, `rol`, `nom_block`, `contorns` JSON,
    `doblec_original`), `PatternPoint` (peça FK, x, y, `tipus`, rastre literal),
    `PatternSegment` (peça FK, `vora`, `t_inici`, `t_fi`, `tipus_vora`).
  - SENSE `PatternPOM`/`SewRelation` (S6) ni `GradeRule` persistit (S7 decideix si cal
    persistir-lo o és projecció efímera d'exportació).
- **T2 — Migració:** mostrar el fitxer abans d'aplicar · migrate_schemas · auditar les
  taules al schema fhort directament (psql).
- **T3 — Adaptadors** (`patterns/adapters.py`): `DjangoGeometryStore` (dataclasses ↔
  ORM, les dues direccions), adaptador d'storage sobre el pipeline S0-B1.
- **T4 — API DRF** (`patterns/views.py` + serializers + urls, convencions S0-B9):
  - `POST /api/models/<id>/pattern-files/` — upload DXF (+RUL opcional) → parse →
    persistir. Errors de parse = **422 amb detall estructurat, MAI 500** (mateixa llei
    de degradació elegant de l'import de fitxes).
  - `GET /api/pattern-files/<id>/` — metadades + peces + punts (paginar punts si cal).
  - `GET /api/pattern-files/<id>/render.svg` — SVG server-side. Implementació segons
    l'evidència S0-B6 (add-on drawing d'ezdxf si matplotlib és raonable; si no, render
    propi des del model intern — probablement més lleuger i sense dependència).
    Paleta pròpia fixa DOCUMENTADA en constant al codi (és document, no UI).
  - Permisos: mateixa política que `ModelFitxer` (S0-B1).
- **T5 — Smoke a staging:** curl (amb Host header) pujant l'AMELIA real a un model de
  QA → 201 → GET detail coherent → GET render.svg retorna SVG vàlid.

**Verd:** check + migració auditada + smoke complet + tests d'adaptador (round-trip
dataclass↔ORM↔dataclass idèntic).

---

## S4 — UI · TAB PATRÓ READ-ONLY (= PAT-0a complet · DEMO INTERNA)

**Objectiu:** la fitxa del Model MOSTRA el patró. Cap competidor del nínxol ho fa.

- **T1 — Tab "Patró"** a ModelSheet (mecanisme S0-B4): zona d'upload (DXF obligatori,
  RUL opcional, límits segons S0-B5), llista de peces (nom, rol si n'hi ha, nº punts,
  bounding box en cm), visor SVG del conjunt + per peça (clic a peça → SVG de peça),
  metadades (font CAD, unitats, versió AAMA, talles del RUL si n'hi ha).
- **T2 — Estats:** buit (call-to-action de pujada) · carregant · error de parse LLEGIBLE
  (el detall del 422) · carregat. Pujar versió nova → `versio_anterior` encadenat,
  selector de versió.
- **T3 — Convencions:** i18n complet · Tabler outline · tokens (l'SVG ve del servidor
  amb la seva paleta de document, no es re-tinta).

**Verd:** npm run build + checklist i18n + walkthrough guionitzat (pujar AMELIA des de
la UI, veure les 4 peces, obrir-ne una, provocar un error amb un fitxer corrupte i
llegir el missatge).

---

## S5 — VISOR KONVA INTERACTIU (= PAT-0b · demo client)

- **T1 —** Component visor react-konva dins el tab Patró: zoom (roda + botons), pan,
  toggle de capes (tall/cosit/internes/piquets/grain/FTT-POM si n'hi ha), glifs
  (turn = quadrat verd, curve = x groga — colors via KONVA_COL), hover amb coordenades
  en cm i longitud del tram de vora, selecció de peça.
- **T2 —** Reutilitzar patrons del TechSheetEditor (stage, offscreen rendering, gestió
  de zoom) — S0-B4/B9 n'assenyala els mòduls. NO extreure ni refactoritzar el
  TechSheetEditor: si la lògica és massa incrustada, duplicar presentació i compartir
  el que sigui net (patró vàlvula d'escapament, ja acceptat al projecte).
- **T3 —** Read-only estricte: cap manipulació de geometria.

**Verd:** build + walkthrough guionitzat (zoom/pan fluids amb l'AMELIA, capes commuten,
glifs correctes contra el que el parser va classificar).

---

## S6 — ANOTACIÓ MANUAL (= PAT-1 nucli, sense IA)

**Objectiu:** la Montse (o Agus fent de Montse a la traçadora) pot marcar POMs i cosir
peces. És la capa que val — i la que la biblioteca GTI reutilitzarà apuntada a item.

- **T1 — Models** + migració auditada:
  - `PatternPOM`: `pattern_piece` FK · `pom_master` FK · `definicio_mesura` JSON
    (dos punts ancorats O landmark + offset + direcció — la recepta ve del `POMMaster`)
    · `punts_ancora` · `valor_mesurat` (calculat, llegit de la geometria).
  - `SewRelation`: `model` FK (penja del MODEL, no de la peça) · `segments_a` /
    `segments_b` N-a-N · `tipus` (casat/frunzit/pinça) · `diferencial`.
- **T2 — Engine** (`engine/measure.py`, `engine/sew.py`): resolució de
  `definicio_mesura` sobre geometria (punts derivats inclosos: "1 cm sota el punt de
  sisa"), mesura (distància recta o longitud per vora, segons la definició del POM),
  validació Sew (longituds dels dos costats ± diferencial → casa / no casa amb el
  desviament exacte).
- **T3 — UI d'anotació** sobre el visor S5:
  - Mode "Marcar POM": seleccionar punt(s) amb snapping a turn/curve points + picker
    de `POMMaster` (reutilitzar el cercador de POMs existent) → línia de mesura dibuixada
    + valor llegit.
  - Mode "Sew": seleccionar segment(s) a la peça A, segment(s) a la peça B, tipus,
    diferencial → relació creada, estat casa/no-casa visible.
  - Panell lateral: llista de POMs ancorats (codi, valor, peça) editable/esborrable +
    llista de costures amb estat. Nomenclatura POM segons convenció (EN canònic + nom
    en llengua d'usuari en gris petit).
- **T4 — Seed TaskTypes** `pattern_digit`/`pattern_cad` si S0-B8 diu que no existeixen:
  management command de sistema, idempotent, G9 (code slug, cap escriptor tenant).
- **T5 — El temps d'anotació és tasca:** obrir el tab en mode anotació obre/reprèn un
  `ModelTask` de tipus `pattern_digit` pel mecanisme EXISTENT (S0-B8); tancar-lo el
  pausa. No construir res de nou de tasques.

**FORA:** suggeriment IA, matcher `CustomerPOMAlias`, autoria a item, edició de
nomenclatura.

**Verd:** build + check + migració auditada + guionitzat: 4+ POMs ancorats a AMELIA amb
valors coherents amb la fitxa tècnica del model, 2+ costures declarades (una casada,
una amb diferencial), tasca oberta i tancada visible al Kanban.

---

## S7 — ESCALAT + EXPORT + GATE (= PAT-2 nucli, grading pinçat)

**Objectiu:** la primera niada generada per FTT surt per la porta amb gate humà.

- **T1 — Operació atòmica** (`engine/operations.py`, esmena E2): moure punt = moure +
  reflow dels curve points adjacents (interpolació per ràtio de longitud d'arc) +
  re-derivació (tall per offset del cosit via shapely `offset_curve` mitre — pyclipper
  NOMÉS si shapely falla en corba espinosa; no instal·lar preventivament) + piquets per
  posició paramètrica + relectura de `valor_mesurat` dels PatternPOM afectats +
  revalidació del graf Sew. Postcondicions com a asserts amb informe estructurat.
- **T2 — Projecció** (`engine/grading_projection.py`): entrada = `grading_version_id`
  EXPLÍCIT (guard dur: `aprovada=True` o error). Per cada `PatternPOM` ancorat amb
  `GradedSpec` per a la versió: delta escalar × direcció de mesura → distribució Δx,Δy
  als punts d'ancoratge → `GradeRuleData`. **Distribució v1 deliberadament simple:
  repartiment simètric per defecte** (les regles fines per item són post-traçadora amb
  la Montse). POMs sense ancorar o sense spec → informe d'omissions, mai silenci.
- **T3 — Export:** DXF de la niada + RUL + capa FTT-POM, amb perfil d'empremta de destí
  seleccionable (tuka/polypattern; gerber/clo marcats EXPERIMENTAL).
- **T4 — Gate d'exportació:** modal ESPECÍFIC ("aquest fitxer ha estat generat
  automàticament; cal obrir-lo al teu CAD i verificar geometria, costures i grading
  abans de tallar") + reconeixement actiu + registre auditable (usuari, timestamp,
  `PatternFile` versió, `grading_version_id`). Text marcat PROVISIONAL — pendent
  d'advocat abans de producció real. Precondició dura: grading aprovat.
- **T5 — UI:** botó "Exportar niada" al tab Patró → selector de destí + selector de
  GradingVersion (NOMÉS aprovades) + gate + descàrrega del DXF+RUL.

**FORA:** resolució automàtica del ruleset (G6) · rectificació post-fitting ·
qualsevol operació que no sigui moure punts per deltes.

**Verd:** build + check + el fitxer exportat passa el comparador round-trip S2-T5 +
la capa FTT-POM del fitxer exportat es rellegeix com a taula idèntica als PatternPOM
de BD + descàrrega funcional a staging + registre del gate a BD auditat.

---

## S8 — TANCAMENT DE LA TRAÇADORA

- **T1 — Guió de QA E2E per a Agus** (document pas a pas, staging): pujar AMELIA a un
  model de QA actiu (NO el model 182 — reservat com a cas de prova del modal de grading
  segellat; NO el golden 162) → visor → anotar → escalar amb GradingVersion aprovada →
  gate → exportar → reimportar el fitxer FTT com a versió nova → capa POM llegida →
  comparador verd.
- **T2 — Neteja:** TODOs del domini, claus i18n òrfenes, docstrings dels ports.
- **T3 — Documentació:** actualitzar `ESTAT_PROJECTE.md` (bloc MOTOR DE PATRONS complet:
  hashos, migracions, endpoints) + `DECISIONS.md` (lleis noves: XOR model/item ·
  projecció-mai-veritat de la capa · operació atòmica · pinçament del grading) +
  preparar el DXF de prova per a la Montse (round-trip Polypattern, quan ella pugui).
- **T4 — Cens de límits REALS descoberts** → alimenta i re-prioritza el backlog §3.

---

## 3. BACKLOG POST-TRAÇADORA (registrat, NO seqüenciat — es re-prioritza amb S8-T4)

1. **Prova Montse** — round-trip Polypattern de la capa FTT-POM (preserva / transforma /
   descarta → entrada al perfil d'empremta). L'eina (comparador) ja existirà (S2-T5).
2. **Biblioteca GTI (E4)** — autoria de bases: l'editor S6 apuntat a
   `garment_type_item` + sembra item→model pel patró `derivat_de_item` + bases amb capa
   POM i Sew pre-cosits. L'esquema ja ho suporta (XOR de S3).
3. **Suggeriment IA d'ancoratge** — UX DictionaryWizard (proposta + confiança +
   confirmació, mai auto-escriptura) + matcher sobre TEXT del DXF + `CustomerPOMAlias`.
4. **G6** — prerequisit per GENERALITZAR la projecció (treure el pinçament manual).
5. **Regles de distribució de deltes per item** — amb la Montse.
6. **PAT-3** — rectificació post-fitting: operacions per història alimentades per
   `PieceFitting`, columna d'advertències DINS la superfície G1.
7. **Validació CAD real per destí** (Q5: qui obre què — Brownie/LOSAN) · **RUL real
   poblat** (Q6) · **nom comercial del servei** (Q7, Salva).
8. **Products del motor al catàleg** (Q4: `pattern-digitization`, `dxf-grading` —
   línia base Welford de la feina manual).
9. **PAT-4** — nesting (libnest2d), quan PAT-2 tingui tracció.

---

## 4. RISCOS DE LA TRAÇADORA

| # | Risc | Mitigació |
|---|---|---|
| T-R1 | Fitxers reals absents del servidor → S1 bloquejat | S0-B3 ho inventaria amb FLAG; Agus els puja abans de S1 |
| T-R2 | matplotlib pesat/absent per al render S3 | S0-B6 pesa alternatives; el render propi des del model intern és el pla B (probablement millor) |
| T-R3 | Distribució de deltes v1 dóna niades "correctes però millorables" | Acceptable a la traçadora; regles fines = backlog §3.5 amb Montse |
| T-R4 | Scope creep cap a "dibuixar" | Frontera §3.3 a les regles transversals de TOT brief; cap eina de creació en cap sprint |
| T-R5 | El TechSheetEditor (monòlit 2.8k línies) tempta un refactor a S5 | PROHIBIT: duplicar presentació + compartir lògica neta (vàlvula d'escapament) |
| T-R6 | Guard de puresa esquivat "per comoditat" | test_engine_purity és part del verd de TOTS els sprints S1+ |

---

## 5. ESMENES POST-S0 (2026-07-12 · `DIAGNOSI_MOTOR_S0.md`)

Ajustos vinculants sobre els briefs S1–S8; on col·lideixin, mana aquesta secció.

- **Verd sense pytest:** el projecte no té pytest. Tot a `patterns/tests.py`; engine amb
  `unittest.TestCase` pur (zero BD), app amb `django_tenants.test.cases.TenantTestCase`.
  Runner únic: `python manage.py test fhort.patterns`.
- **Unitats (S1-T3):** capçalera SI existeix; si `HEADER`/`TABLES` són buides (cas real
  AMELIA), DEDUCCIÓ per geometria amb heurística de plausibilitat dimensional. Factor +
  mètode + confiança sempre a l'empremta.
- **Capes 14 (cosit) i 6 (mirall) OPCIONALS per disseny:** `PieceData` porta flags de
  capacitat (`has_sew`, `has_fold`); operacions dependents (S7 re-derivació tall↔cosit)
  degraden amb informe explícit, mai assumeixen. Capes desconegudes (cas capa 15 AMELIA)
  es capturen i preserven genèricament a l'empremta.
- **Separador decimal: matís PER CAMP**, no per fitxer (AMELIA/Tuka: coordenades amb
  punt, TEXT amb coma "1,0").
- **S1-T4 (RUL):** implementació SEMPRE (format documentat al juny); test amb fitxer real
  si el material existeix a `ops/motor-patrons/material/`, sintètic + FLAG si no.
- **Fixtures reals VERSIONATS** a `backend/fhort/patterns/tests/fixtures/` (l'únic
  exemplar viu d'AMELIA és a `backend/media/`, fora de git).
- **S3-T1:** `source_asset` FK → **`models_app.ItemFitxer`** (GarmentTypeItemAsset no
  existeix ni ha existit); XOR → **`tasks.GarmentTypeItem`**. Riscos heretats del patró
  ModelFitxer (invariant `is_current` sense constraint de BD; bifurcació de cadena):
  💡 proposta per a S3 — PatternFile afegeix `UniqueConstraint` parcial per protegir la
  cadena a BD (decisió a S3 amb el terreny davant).
- **S6-T4 ELIMINAT:** `pattern_digit`/`pattern_cad`/`scaling` ja són al seed canònic
  (0025), més `pattern_review` i `marking` que el pla no coneixia. Substituït per:
  (a) acció de DADA del CTO — afegir els codes a `permisos["tasks"]` dels perfils
  (sense això, open-task → 403 excepte admin); (b) codi menor — `toolRoute` + `TASK_ICON`
  a `WorkPlan.jsx` I `TaskTree.jsx` (duplicació conscient) + 3 claus i18n `tasktype.*`.
- **S7-T2 (contracte grading):** guard d'aprovació per `filter(pk=explicit)` + comprovació
  del flag, **MAI `get(aprovada=True)`** (múltiples aprovades possibles; aprovada ≠
  is_active). Context `base_size_label`/`size_run` des del Model via
  `grading_version.size_fitting.model` — **MAI inferir la base per `delta == 0`** (regla
  ZERO dona 0 a totes les talles). La matriu pot tenir FORATS (STEP invàlid). El port
  `GradingSource` es transcriu de la pseudo-dataclass de `DIAGNOSI_MOTOR_S0.md` §B7.4.
- **B6 render:** recomanació RENDER SVG PROPI des del model intern (el DXF real només té
  polilínies/línies/punts; matplotlib arrossegaria Qt + 6 paquets). Decisió formal a S3.
- **Dependències:** `ezdxf==1.4.4` s'instal·la abans de S1 (acció CTO al venv +
  línia a `backend/requirements.txt` commitejada a S1-T1); shapely a S7; pyclipper mai
  preventiu. ⚠️ Pendent CTO: aclarir quin `requirements.lock` mana (arrel vs `backend/`,
  divergents).
- **Avisos operatius heretats de S0** (fora del motor, no tocar des dels sprints):
  `sites-available/ftt-staging` divergeix del `sites-enabled` que corre (editar-lo i
  re-enllaçar trencaria límit 25M + descàrregues gated).
- **REATRIBUCIÓ DE FONT (2026-07-12, P3 de S1):** l'AMELIA de staging és **PolyPattern**,
  no Tuka — tres evidències independents: RUL `ANSI/AAMA-292-B · AUTHOR: PolyPattern
  11.0.1` (pujat a `ops/motor-patrons/material/`), 266 entitats POINT (= el recompte
  Polypattern del V2 §2.2), coma decimal als TEXT. El fitxer que FALTA és el **Tuka**
  (92 punts, AAMA 2.1.1). Conseqüència: S2 escriu primer el perfil `polypattern` (el
  canònic ric, amb DXF+RUL reals coherents: SAMPLE SIZE M); perfil `tuka` amb FLAG fins
  que el fitxer aparegui. RUL real: 5 talles XS–XL, base M, 1 regla, deltes tots 0
  (l'estructura compta); dins el RUL el decimal és PUNT i la coma separa dx,dy.
  Lliçó: etiquetar fitxers per EMPREMTA tècnica, mai per procedència comercial.

### Tancament S1 (2026-07-12) — 8 commits 75197a7..3dac79a, 36 tests, verd complet

**Lleis empíriques noves (del material real, cap document les deia):**
- **Turn/curve points són POINT de capes 2/3 ASSEGUTS sobre el vèrtex que qualifiquen**:
  el parser els creua per coincidència de coordenades amb el contorn (100% de match a
  les 4 peces). Sense aquest creuament, un contorn no té semàntica.
- **La regla de grading viu NOMÉS a turn points i piquets, MAI a curve points**
  (22/22 turn amb regla, 0/42 curve a AMELIA). Confirma E2 amb evidència: els turn
  points es mouen per regla; els curve points FLUEIXEN entre ells. Fonament de
  l'operació atòmica de S7.
- El DXF porta TEXT `Author: PolyPattern` i `Units: Metric` al modelspace — metadades
  d'autor corroboren la deducció d'unitats per geometria.

**FLAGS vius per a S2:** (1) cap fitxer Tuka → una sola empremta real; (2) RUL real amb
deltes tots 0 → escala del RUL no verificable (`GradeTable.unitats_factor_mm` explícit,
es tanca amb Q6); (3) AMELIA sense capa 14 → S7-T1 sense font de cosit (ja previst,
capes opcionals).

**Ajust S2 (decisió arquitecte):** el writer implementa NOMÉS el perfil `polypattern`
(validable contra material real); el mecanisme de perfils queda dissenyat per a N, però
`tuka` NO s'implementa sense fitxer (implementar una empremta sense material seria
especular) i els esborranys `gerber`/`clo` de ksons/astm-parser passen al backlog.

**Deute registrat (fora del motor):** `fitting.PropagarActionTest.
test_regim_sense_fallback_400` falla (espera 400, rep 200), verificat preexistent a
b93db34 — probable seqüela dels sprints X/Y del fitting. Revisar abans del proper
deploy a PROD.

### Tancament S2 (2026-07-12) — 6 commits 7bd4da2..70e030b, 61 tests, verd complet

**Resultats durs:** round-trip DXF real 266 punts, desviació màx 0,000 µm (tol 1 µm),
cens d'entitats idèntic; RUL **byte a byte** (md5 e56202b0…). Estabilitat 4 voltes amb
cens immòbil (va pescar el bug del FTT-META que engreixava el fitxer una línia/volta).

**Lleis i decisions noves (canòniques):**
- **Llei dels TEXT de regla:** un TEXT a capa 2 per turn point + un addicional a capa 8
  si el punt pertany a línia interna + un a capa 4 per piquet. Reproduir-la exacta és
  el que quadra el cens (37 TEXT a la BACK).
- **Ubicació capa FTT-POM (ratificat Patró C):** línies de mesura DINS el BLOCK de la
  peça (el POM penja de la peça); metadada de document al modelspace. Escrit al
  docstring canònic (precisió S2).
- **El reader reconeix la seva pròpia capa** FTT-POM i la llegeix com a taula (E3);
  mai com a "capa desconeguda" (evitava doble escriptura en reexportar).
- **Perfils: error dur si no implementat** (tuka/gerber/clo), mai fallback silenciós.
- **Round-trip estàndard del motor = N voltes amb cens immòbil** (llei de mètode).
- `engine/roundtrip.py` = eina permanent: S7 l'ha de cridar abans de deixar sortir cap
  fitxer; és l'instrument de la prova Montse (mesura què fa el CAD del mig al fitxer).

**FLAGS vius (intactes):** Tuka absent · escala RUL no verificable (deltes 0; writer
provat amb deltes signats sintètics) · capa 14 absent a AMELIA.

**Decisions formals per a S3 (arquitecte):** render SVG PROPI confirmat (matplotlib
descartat); guard de bifurcació de cadena a BD via UniqueConstraint sobre
`versio_anterior` (un fitxer només pot tenir UN successor).

### Tancament S3 (2026-07-12) — 6 commits 25f9892..1b2a920, 87 tests, verd complet

**Migració `patterns.0001_initial`** (4 taules, 3 constraints, 1 índex) auditada per
EXERCICI: inserts reals en transacció revertida — XOR i anti-bifurcació rebotant de
debò a BD. **Llei nova:** l'anti-bifurcació de cadena viu a la BD (a diferència de
ModelFitxer, on és risc documentat). Mètode adoptat: **tota migració del motor
s'audita exercint les constraints, no llegint-les.**

**Smoke real:** model 186 (FTT-CO27-0001) · PatternFile id=8 · font polypattern,
escala 1.0 mm (geometry/high) · 4 peces, 266 punts == cens S0-B3 · grade_table
XS–XL base M sense avisos de coherència · render.svg 200 (rasteritzat i verificat
visualment: orientació Y correcta) · download DXF 31344 bytes exactes · RUL 228 ·
sense credencials 401 · corrupte 422 estructurat. **Dades deixades a staging per a S4.**

**Decisions fines ratificades (Patró C):**
- UNA veritat per a la geometria: coordenades NOMÉS a `PatternPoint`; `contorns` =
  metadada de vora (rol, capa, tancada).
- Serializers read-only; la invariant de cadena la governa `save_pattern_file`
  (cap segona porta d'escriptura — cicatriu ModelFitxerViewSet no repetida).
- RUL servit per proxy duck-type sobre `serve_fitxer` + SALT PROPI (tests dels tres
  creuaments de token: DXF↛RUL, ModelFitxer↛PatternFile).
- El comparador S2 va caçar que l'adapter no desava l'empremta → el store és AMO del
  document sencer (`load(save(doc)) ≡ doc` és la promesa completa del port).

**⚠️ ACCIONS DE DEPLOY A PROD acumulades (quan toqui):** `migrate_schemas`
(patterns.0001) + `venv/bin/pip install ezdxf==1.4.4` (ja a requirements.txt).

### Tancament S4 (2026-07-12) — 2 commits 49e0ff9, f230a27 · PAT-0a COMPLET (demo interna)

**Walkthrough e2e real (Playwright contra backend viu, 8 passos, model 186):** tab
entre Escalat i Fitxa tècnica · metadades honestes ("1 mm · deduïdes per geometria ·
alta", cosit absent, capa 15 preservada) · 4 peces amb recomptes reals · visor per
peça · 422 llegible amb patró intacte · cadena v1→v2 amb confirmació explícita i
verificació BD · descàrregues signades amb mides exactes. 37+ claus i18n ×3 idiomes
amb paritat verificada.

**Decisions post-S4 (arquitecte):**
- `render.svg` rere IsAuthenticated: resolt al client (fetch→blob→objectURL amb
  revocació). **`render-signed` DIFERIT al backlog** — S5 dibuixa des de la GEOMETRIA
  (API de punts), no des de l'SVG; el despertador és el PDF de fitxa amb peces.
- **Placeholder "Patró DXF" del menú (App.jsx:302): JUBILAR** (micro-tasca a S5) —
  el tab del model és la casa del patró; cap pàgina global no justifica l'entrada.
- Nota de procés: un commit va néixer amb build vermell i es va desfer i reordenar —
  història verda, lliçó dita.

**FITA:** la fitxa del model MOSTRA el patró real. Ensenyar a Montse/Salva abans de
S6 (no com a gate — la reacció de la Montse informa el disseny de l'anotació).

### Tancament S5 (2026-07-12) — 3 commits f19fdd4..339f0f7 · PAT-0b COMPLET (demo client)

**Walkthrough 10 passos contra staging viu:** visor Konva amb les 4 peces · toggle de
capes on "Cosit" NO apareix (absència = informació, coherent amb el fitxer) · zoom al
cursor, pan, fit · hover amb cm + longitud de tram · selecció de peça amb perímetre
real (BACK 235,4 cm) · glifs verificats per captura (quadrat verd/x groga/diamant
vermell/fletxa de fil) · SVG de document commutable · placeholder "Patró DXF" jubilat.
50 claus i18n ×3. Endpoint nou GET pattern-files/<id>/geometry/ (T1: el detall de S3
no duia coordenades; document sencer sense paginar, 19,7 KB real).

**Criteris de mètode nous (ratificats):**
- NO importar constants d'un altre domini encara que estiguin exportades si la seva
  semàntica no aplica (MM_TO_PX era A4; un patró fa metre i mig) — duplicar net >
  importar i corregir.
- Els tests d'ordenació/estructura comparen CONTRA LA FONT, mai contra llindars
  inventats (una aresta de 385 mm és legítima).
- El monòlit TechSheetEditor: 0 línies tocades (vàlvula d'escapament complerta).

### Tancament S6 (2026-07-12) — 6 commits ab60c62..d8a2378, 116 tests · PAT-1 nucli

**Guionitzat real:** 4 POMs ancorats (valor calculat al SERVIDOR des de la recepta —
el client mai envia la xifra) · 2 costures amb el domini sencer en una parella de
trams: CASAT no casa (0,5 cm = error de patró) vs FRUNZIT 20,08 casa (instrucció de
muntatge) — llei V1 §5.3.3 en viu · ModelTask 307 pattern_digit amb rellotge que es
pausa en sortir del tab · 84 segments turn→turn materialitzats (command idempotent;
prova: sumen el perímetre exacte de cada peça).

**Defectes caçats pel guionitzat (no per tests):** mesura a==b rebotada AL DOMINI
(no a la UI) · closure caducat a onClicPunt → forma funcional de setState.

**Troballes de domini:**
- **POMMaster NO porta recepta de mesura** (recta vs per vora: 51,3 vs 117,7 cm sobre
  els mateixos punts!). v1: `metode` explícit amb default recta, mai assumit en
  silenci. → BACKLOG: enriquir el catàleg canònic amb la recepta, AMB MONTSE (sessió
  PAT-1).
- Picker lleuger sobre poms/cerca/ (POMBrowser és gestor de membreses, no picker).
- ⚠️ **Incoherència semàntica assumida:** model 186 = "Test pantaló", patró = AMELIA
  (top). Valors geomètricament correctes, contrast amb fitxa impossible. **CONDICIÓ
  PER A S8: muntar l'AMELIA sobre un model amb la SEVA fitxa** (Patró C pendent).

**Deploy PROD acumulat:** migrate_schemas ara inclou patterns.0002 (i 0003 quan S7).

**DECISIÓ DE PROCÉS (Agus, 2026-07-12, pre-S7):** tota la validació S1–S6 és mecànica
(agents/Playwright/tests) — CAP ull humà ha vist la UI encara. S7 procedeix igualment
(engine-heavy, validesa demostrable amb números). **S8 = EL gate humà de la traçadora,
BLOQUEJAT fins que: (a) patró real muntat sobre model amb la SEVA fitxa, (b) l'Agus
faci el cicle sencer amb les seves mans a staging.** Res del motor toca PROD ni arriba
a la Montse abans de S8. Mentrestant, revisió d'ulls informal del tab Patró (model
186) quan l'Agus pugui, per corregir abans que S8 consolidi.

### Tancament S7 (2026-07-12) — 6 commits 0405399..cbf5ea7, 151 tests · PAT-2 nucli

**Projecció real (model 186, gv#53 aprovada, is_active=False — la trampa B7.1 en viu):**
desviament projecció↔spec 0,000000 a totes les cel·les, verificat pel CAMÍ INVERS
(regles → geometria → mesura = comptabilitat de doble entrada). Autovalidació: 266
punts, 0,000 µm, 10/10 regles, cens immòbil; dos tests trenquen el writer a posta i
l'export es BLOQUEJA sense emetre un byte.

**LLEIS NOVES (ratificades Patró C):**
- **S'aplica `increment_applied_cm`, MAI `graded_value_cm`** — grading relatiu: el
  patró és sobirà de la seva base (66,84 patró vs 100,00 fitxa = magnituds diferents;
  l'absolut hauria estirat 33 cm). El modal mostra les dues bases: la discrepància
  es veu, no s'amaga.
- **Correspondència tall↔cosit, MAI offset** (offset = vèrtexs nous = topologia =
  prohibit §3.3). Conseqüència: **shapely JUBILAT de les dependències del motor**.
- **El RUL exportat porta el size run del MODEL** (S–XXL base S), no el del fitxer
  del client — el grading que manem és el nostre.
- Regla per punt mogut · regla 0 per a la resta · piquets amb regla pròpia (reflow) ·
  curve points sense regla (flueixen — el CAD del client els fa fluir com nosaltres).
- Precisió del lliurable: ±5 µm (RUL a 2 decimals quantitza a 0,01 mm) — dit i prou.
- **El fitxer generat NO es persisteix com a PatternFile (v1)** — decidir si un
  fitxer fabricat per nosaltres entra a la cadena del client NO es fa de passada.
- Espec FTT-POM v2: codis ENTRE COMETES (HI RLX, LEG OP amb espais), valors a 3
  decimals (docstring canònic actualitzat).

**TROBALLA ESTRELLA:** la distribució simètrica v1 NO preserva longituds de costura
en graduar — el frunzit #4 casa a la base i falla des de la M. No és defecte: és LA
validació que cap CAD fa. Alimenta directament el backlog "regles fines amb Montse".
La costura #2 (casat) no casa a la base per 5,2 mm = dada de S6 → revisar a S8 (pot
ser defecte real del patró o de l'anotació).

**Defectes caçats:** `_rule_at` confonia la regla del piquet amb la del gir de sota
(latent de S1, invisible amb regles totes-1) · 415 als POST d'export (viewset sense
JSON) · origen del `t` de segment = primer gir, no vèrtex 0 (latent de S6).

**Housekeeping decidit:** esborrar pf#10 (niada reimportada del guionitzat) i
VERIFICAR a BD que pf#9 recupera is_current=True (no es restaura sol).

**⚠️ FORAT DE MÈTODE corregit:** la còpia del PLA al servidor era ESTALA (sense §5 ni
tancaments — només al vault). REGLA NOVA: cada esmena del pla al vault va acompanyada
de la línia de repujada scp al servidor.

**Deploy PROD acumulat:** migrate_schemas (patterns.0001–0003) + ezdxf==1.4.4.
**Estat de la traçadora: S0–S7 ✅ mecànicament. S8 BLOQUEJAT esperant l'Agus.**

### QA-S8 · Sessió de QA humà 2026-07-13 — dietari, fixos i lleis

**El QA d'Agus (primer ull humà) va aturar el circuit a la IMPORTACIÓ (no al motor)
i va destapar 5 defectes + 1 requeriment. Tot diagnosticat amb evidència, arreglat en
2 sessions paral·leles coordinades (mai 2 escrivint alhora), 14 commits QA-S8.**

**Dietari:**
- **D1** — El parser ràpid abdica per DESPLAÇAMENT DE COLUMNA (la taula Brownie viu a
  B:H, col A buida; el parser busca 'POM' a row[0]) → fallback Opus. TROBALLA CLAU
  (empírica): el matching és 100% determinista (find_pom_master) i corre igual pels dos
  camins — els 9 sense-match eren BUIT DE CATÀLEG, no parsing. La IA va perdre la fila
  JJ (única sense valor) EN SILENCI. **Fix C (perfil determinista Brownie/RECTI) →
  BACKLOG** amb llei innegociable: PORTA D'ABDICACIÓ (un parser més llest però equivocat
  no cau a la IA: substitueix en silenci — pitjor que el defecte) + condició: MESURAR la
  2a importació Brownie abans d'invertir-hi.
- **D2** — Cadena W3→W5 indexada per pom_master_id: U2/U3 → mateix POM = fila
  col·lapsada = MESURA PERDUDA EN SILENCI a W5. Fix A: guard many-to-one portat de la
  Size Library (l'exempció alias_match ES VA TREURE — BaseMeasurement és unique(model,
  pom): dues files no hi caben MAI, legítim o no). Fix A2: llindar (LOW no auto-vincula).
  Fix B: el codi del DOCUMENT mana al pas 3 (el del catàleg, atenuat rere fletxa).
- **D3** — Modal del wizard escapçat: CAPA Z (overlay z60 < sidebar z100; el Modal
  canònic z50 tenia el MATEIX forat) → sistema de capes únic. No era posicionament.
- **D4a** — Àlies contaminats (prosa com a codi, F/FF/F3/F4→389, U/U2/U3→439, '0') ·
  **D4b** — descripció escrita bé a description_en però LLEGIDA del camp obsolet
  (serializer + UI) · **D4c** — choice DICCIONARI sense clau i18n (violació del gate).
- **D5** — La biblioteca mostrava 25/95 àlies (PAGE_SIZE sense recórrer pàgines).
- **R1 (requeriment Agus)** — La biblioteca = REGISTRE COMPLET del vocabulari del
  client: pom NULLABLE (migració 0037, exercida), àlies sense pom = "pendent de mapar"
  amb mapatge en línia, --unlink=null com a DEFECTE del command de reparació (el codi i
  la descripció són informació BONA del client; el que està malament és el VINCLE;
  delete només per a brossa), aprenentatge a W5 de TOT vincle ferm confirmat
  (nomes_si_manual additiu), porta del matcher: pendent_revisio no auto-vincula mai
  (parla només si cap altra estratègia troba res, com a suggeriment LOW).

**Lleis noves:**
- "El que es confirma al pas 2, es recorda" — el pes es desplaça a la revisió humana.
  Llavor de backlog: si apareixen àlies MEDIUM cimentats per confirmacions distretes,
  el fix és UX del pas 2 (confirmació deliberada), MAI tornar el matcher desconfiat.
- Cap credencial d'auth als agents, mai — la verificació visual és humana (el
  classificador va blocar correctament un bypass ben intencionat; l'agent va destruir
  el token: comportament exemplar).
- Reparacions de dades: sempre command idempotent + dry-run per defecte + OK humà.

**Pendents del dia:** execució de la reparació (OK donat, la fa l'Agus) → reinici del
circuit amb l'Excel del Tate (sessió 33 MORTA, mai confirmar-la) → mesura dels
sense-match a la 2a importació (decideix el fix C) → continuar S8 cap al patró.

### QA-S8 (continuació) — El circuit REAL amb el Tate · el TALLER DE PATRÓ neix com a disseny

**Reimportació del Tate: el paquet QA-S8 verificat amb ulls.** 0 sense-match (la
palanca del catàleg DEMOSTRADA: els 10 codis resolen per àlies → el fix C queda al
backlog pagant-se només pel cost d'Opus i la fila JJ, que la IA HA TORNAT a perdre —
"25 POMs detectats" de 26). Guard en viu: 4 pendents (F/FF/U2/U3) amb missatge que
explica el perquè. Model REAL: BRW-FW26-0001 Blusa TATE Crudo — condició (a) de S8
complerta. ⚠️ Avisos donats a l'Agus: NO acceptar M-M79 per a F i FF (mesures
DIFERENTS — recrearia la contaminació i ara s'aprendria); revisar D→SK SW (concepte
de faldilla en una blusa: possible mapatge dolent del diccionari — pregunta Montse).

**El patró del Tate VIU:** 10 peces, empremta honesta (capa 13 desconeguda preservada
— genèric funcionant), tasca en curs, primer POM marcat a mà (T.1 51,5), primera
validació de costura en viu (Casat NO casa 1,4 cm — diagnosticable quan hi hagi
segments declarats).

**Dietari nou:** D6 upload UX (input natiu invisible → disseny 2 targetes
FileDropCard, component de design system: cura també import Excel i diccionari) ·
D7 la mà/pan no funciona en mode anotació · D8 marcar POM expulsa al render SVG (el
document) en lloc del visor Konva (l'eina) · D9 URLs signades couvades a la UI
caduquen (demanar token AL CLIC).

**DISSENY NOU (Agus, 2026-07-13): TALLER DE PATRÓ** — el feedback del QA convergeix
en un mòdul dedicat a pantalla completa (patró fitxa-tècnica: ruta pròpia, eines
pròpies), primer gran paquet POST-traçadora:
1. Canvas al màxim; columna esquerra fixa amb 3 contenidors d'scroll independent:
   PECES · POMS DEL MODEL · RELACIONS.
2. **Els POMs no es busquen: es col·loquen** — el 2n contenidor és la taula de
   Mesures del model (els aprovats) com a llista de treball amb estat i comparació
   immediata mesurat-vs-fitxa. Cercador de catàleg = via secundària.
3. Relacions (POMs ancorats + costures) editables al 3r contenidor.
4. **Segments: PRIMER DECLARAR, DESPRÉS COSIR** — la segmentació gir→gir és proposta,
   no veritat de costura. Eina "Definir segment" (punt A → punt B amb snapping;
   SegmentRange t_inici/t_fi ja ho suporta des de S1). "Cosir" només tria segments
   declarats. Validació nova del motor: suma de trams cosits vs longitud de vora per
   peça (solapaments/excessos canten).
5. D6+D7+D8+D9 dins del paquet.

**Seqüència decidida:** acabar el CICLE primer (grading del Tate per l'app → export
amb gate → reimport v2) = S8 demostrat; el Taller després, amb el QA d'avui com a
especificació.

**⏸️ S8 — TRAM FINAL EN PAUSA PER MATERIAL (2026-07-13):** el Tate només té talla
base (spec RECTI 1, sense deltes) → no es pot generar grading real. Escalat + export
+ reimport amb les mans de l'Agus queden PENDENTS DELS DELTES DE BROWNIE (petició
comercial natural via Salva). La mecànica ja està demostrada amb números (S7, model
186). S8 es tanca quan arribin.

**PAQUET TALLER — mapa aprovat (2026-07-13), seqüencial, 1 sessió escrivint alhora:**
- **W1** Segments declarats (backend+engine): origen auto|declarat + nom · resolució
  A→B per t · validació de cobertura (solapament/excés) · CRUD amb PROTECT.
- **W2** Taller shell: ruta dedicada, canvas màxim, columna esquerra 3 contenidors
  fixos (Peces · POMs del model · Relacions editables); el tab Patró queda de porta.
- **W3** POMs del model = llista de treball des de Mesures (estat + mesurat-vs-fitxa)
  · marcar al Konva (fix D8) · la mà (fix D7).
- **W4** Eines "Definir segment" (snapping A→B) + "Cosir" només sobre declarats +
  avisos de cobertura a la UI.
- **W5** FileDropCard al design system (patró + import Excel + diccionari, fix D6) +
  tokens de descàrrega frescos al clic (fix D9) + polit i18n.

### PAQUET TALLER — TANCAT (2026-07-13, W1–W5, 25 commits, 190 tests)

**W1** (5c): trams declarats — prova de frontera: arc curt + arc llarg = vora exacta
(9,52+187,12=196,64). El Tate PORTA CAPA 14 (primera branca de cosit exercida amb
material real — FLAG de S1 parcialment tancat). Defecte caçat: tram que creua
l'origen donava longitud 0 en silenci. Guard de materialize_segments corregit a
filter(origen='auto') (ratificat). Els tests que van "fallar" tenien raó ells.

**W2** (4c): Taller shell fora del Shell (com l'editor .ftt) — canvas 1212×733 a
1600×900 (abans 560px fixos). ResizeObserver per a contenidors (window.resize no
veu créixer un div). WorkPlan/TaskTree re-apuntats al taller (ratificat: rellotge
orfe evitat). Tab Patró = PORTA (981→603 línies). LLEI DE FRONTERA: al tab les
accions sobre el FITXER (versions, upload, descàrregues, export — el gate mereix
la solemnitat de la porta); al Taller les sobre el CONTINGUT (anotar, cosir —
obren tasca i rellotge).

**W3** (7c): POMs = llista de treball (es COL·LOQUEN, no es busquen): pendent→clic→
A→B→col·locat amb Δ mesurat-vs-fitxa i tolerància (precedència: mesura > catàleg >
0.6, mateixa escala que s10). B tancat a la peça de l'A (la llei del domini feta
impossibilitat física). T.1 fora-de-fitxa va a RELACIONS (el comptador diu la
veritat). Bug W2 caçat pel guionitzat: ResizeObserver lligat a encaixar() —
REENQUADRAR ÉS ORDRE EXPLÍCITA, MAI EFECTE SECUNDARI. D7+D8 morts. Δ del Tate:
mecanisme demostrat, mesures NO (clics arbitraris — les de debò, amb Montse).

**W4** (5c): Definir tram (dos arcs dibuixats amb longitud, el curt és DEFECTE no
veritat) · Cosir només sobre declarats (buit-estat → Definir tram: el pas previ és
flux) · cobertura INFORMA amb xifres, MAI bloqueja (el patronista mana — mateixa
filosofia que el gate d'export). LLIÇÓ MAJOR: "BUILD VERD NO ÉS PRODUCTE VERD"
(voraIman undefined passava el build — pàgina blanca).

**W5** (4c): ESLint EXISTIA i ningú l'executava (210 problemes = soroll). "UNA
PORTA QUE MAI NO ÉS VERDA NO ÉS UNA PORTA." Triatge: ERROR atura (no-undef,
no-unused-vars, hooks...) / WARNING s'anota. 33→0 netejats (codi mort real). npm
run lint ENTRA AL VERD de tot sprint frontend (documentat a eslint.config.js).
FileDropCard a les 3 pantalles (validació A LA TARGETA). D9: download-links signa
AL CLIC (testejat amb rellotge +16min: couvat 403, fresc 200). La porta va caçar
l'agent el mateix dia (replace cec sobre triple useTranslation → refet per línia).
VERD OBERT: passi visual d'Agus a les 3 pantalles (cap credencial als agents —
llei mantinguda ×3).

**W6 — TALLER-GTI (dissenyat, pendent post-Montse):** el Taller opera sobre
PatternFile i el XOR model/item hi és des de S3 — segona PORTA, mateix taller.
4 deltes: (1) 2n contenidor canvia de font: plantilla POMs de l'item (GarmentPOMMap
d'item — convergeix amb el mode ASSIGN pendent), no Mesures; (2) SENSE rellotge
(ModelTask no aplica al catàleg); (3) permisos CONFIGURE (territori Montse);
(4) SewRelation penja del Model → probable XOR model/item (migració, decidir amb
el terreny). Entrades: pantalla de l'item + menú Disseny ("Biblioteca de patrons").
Moment: DESPRÉS de W5 i de la sessió Montse (ella autora les bases; la seva
validació del gest és l'especificació).

**GUIÓ DEL GEST PER A LA SESSIÓ MONTSE (de W4):** un sol moviment — dos punts
imantats — tres significats (POM, tram, costura). Tres coses que li estranyaran si
no es diuen: (1) el 2n punt queda tancat a la peça/vora del 1r — no és limitació,
és el que fa la mesura d'aquella peça; (2) dos punts = dos arcs, el curt és només
el defecte; (3) cosir només ofereix el declarat — llista buida no és error, és que
encara no s'ha declarat res. La sessió és alhora: gate PAT-1, naixement de les
receptes de mesura del catàleg (recta vs vora — backlog S6), Δ reals del Tate, i
especificació del Taller-GTI.

**Fils oberts:** S8 tram final esperant deltes Brownie · sessió Montse · tasca 308
model 163 InProgress (probable pestanya d'Agus — verificar al Registre) · POMs de
vora/landmark sense camí d'UI (post-Montse) · backlog previ intacte (fix C amb
porta d'abdicació, JJ, render-signed, G6, biblioteca GTI=W6...).

### W4b — PINCES + PRECISIÓ + EDICIÓ (2026-07-13, 3 commits, 214 tests)

**T0 confirmat amb 0,13 mm de marge:** la costura "que no casava" (2,3266) era LA
PINÇA del TATE_FRONT (costats 1,33+1,01=2,3393; la diferència = folgança boca-vs-
corda). EL MOTOR DEIA LA VERITAT — el que faltava era que sabés què és una pinça.

**Construït:** gest "Marcar pinça" (3 clics) — CAP model nou (pinça = 2 trams +
SewRelation tipus pinça de S6/W1) · pinça DE VORA constatada de la GEOMETRIA (dos
costats a la mateixa vora), mai d'un flag — la pinça entre peces segueix sent
instrucció de muntatge i no descompta · validació per longitud NETA amb aritmètica
AUDITABLE sencera ("32,1 − 2,3 (Pinça 1) = 29,8 · casa") · cobertura sense doble
compte · previsualització direccional d'arc (tria d'arcs JUBILADA: "preguntar quan
la mà ja havia marxat") · REOBRIR les 3 entitats des de RELACIONS (mateix gest,
mateixa fila; PROTECT només per esborrar) · nom de costura GENERAT "tramA ⛓ tramB ·
condició" (compost en viu, bateig manual mana) · LLEI D'UNITAT de presentació:
formatLen únic — cm=1 decimal, inch=2, la DADA mai s'arrodoneix (BD/exports/motor
a precisió completa, valor sencer al title). Convergit amb fittingShared.fmtMeasure.

**PER A L'AGENDA MONTSE (primer punt):** la pinça real del Tate té costats
DESIGUALS (1,33 vs 1,01 — 3,1 mm): no tanca plana. ¿Defecte del DXF de Brownie o
folgança volguda? El motor avisa en groc sense bloquejar. Si és defecte: PRIMER
ERROR REAL trobat pel Taller en un patró de client — argument comercial.

**D10 (dietari, fora del taller):** ProtectedRoute avalua abans d'initAuth → F5 en
ruta protegida rebota a /login amb sessió vàlida (App.jsx:58-60, 207-210). Brief de
micro-fix donat (estat d'auth de 3 valors + Login que torna a l'origen).

### FIX C + DIAGNOSI G6 (2026-07-13, sessions paral·leles A escriu / B llegeix)

**FIX C (parser determinista, 3 commits, 292 tests):** TROBALLA MAJOR — la via
ràpida d'Excel era CODI MORT: 0 de 8 Excels acceptats mai; el 100% de fitxes han
anat SEMPRE a Opus. ⚠️ AVÍS DE DEPLOY: amb el fix, el camí ràpid s'encén PER
PRIMERA VEGADA en producció (revisió Sonnet, reconciliació de talles, derivació
de grading — tot s'exercita per primer cop; la porta d'abdicació és el que ho fa
segur). Resultats: Tate 26 POMs (JJ RECUPERADA, values={}), Rosalia 11, talles
netes, header ple. La porta d'abdicació també TRIA EL FULL (la Rosalia: PROTO
COMMENTS no passa la porta → RECTI 1 sí). Els avisos de matching es queden (D1d
confirmat: el matching és determinista, la palanca era el catàleg). Anotat:
columnes de talla per FÓRMULES planes → grading importat sortiria pla (avís
d'import al backlog + agenda Montse).

**DIAGNOSI G6 (read-only, committed):** el pinçament per grading_version_id
CONFIRMAT (esquiva tots els forks). Però **EL SEGELL MENT**: el guard només
protegeix crear v+1 — sis endpoints escriuen GradedSpec IN-PLACE sobre versions
aprovades (cas viu: gv67/model 182) i GradingVersionViewSet és CRUD obert
(PATCH aprovada=false per a qualsevol autenticat). El gate d'exportació del motor
confia en un flag que pot mentir → **Fase 2 (integritat del segell) = prioritat 1
de G6 = G6-B**. Bugs vius: fork 4 (s6_views 137-139) serveix la v5 DESACTIVADA
del 162 mentre la resta serveix v3 · **EL MODEL 163 (Tate) NO POT GRADUAR MAI**
(25 ModelGradingRule actives però grading_rule_set=NULL i el gate dur exigeix el
punter que el motor ja no usa) → **BLOQUEJA EL TRAM FINAL DE S8**: G6 passa de
"per al final" a CAMÍ CRÍTIC. GradingException = mort de facto (0 files, 0
escriptors) → es jubila. Deute fitting RESOLT: el test era ESTAL (guard tret a
consciència a 407d8af, Sprint Sobirania de la Regla, llei a DECISIONS:280) — es
reescriu per afirmar la llei, cap fix pre-PROD. Nota de mètode: afirmació d'un
investigador FALSADA per SQL i descartada — epistemologia com toca.

**Decisions (Patró C): G6-A** = fork4 + gate del 163 ("té regles": residents O
set, alineat amb Sobirania) + jubilar GradingException + test estal reescrit +
segellar QA_S8_IMPORT a arxiu/. **G6-B** = integritat del segell (Fase 2), brief
després de G6-A.

### G6-A TANCAT (2026-07-13, 5 commits, 315 tests · fitting 23/23 verd sencer)

El 163 GRADUA (25 specs en transacció revertida): el gate pregunta "té regles?"
(residents O set) — la porta s'alinea amb el motor, no s'obre. El gate DUPLICAT
(generador + preview del wizard) unificat via _te_regles (fora de brief,
RATIFICAT: arreglar-ne un i no l'altre = la malaltia que la diagnosi cataloga).
Fork 4: mort sumant-se a vigent_grading_version (criteri propi ERA el defecte) —
el 162 serveix v3 a totes les superfícies. GradingException enterrada amb
auditoria en fred (0 files als DOS schemes) + migració 0038 exercida
forward→reverse→forward + imports en dur de bootstrap/reseed retirats (haurien
petat). Test estal reescrit afirmant Sobirania de la Regla.

**Ratificat el que NO desbloqueja:** el pinçament del motor ES MANTÉ fins que
G6-B (integritat del segell) aterri. **G6-C registrat (no seqüenciat, decidir amb
Montse):** R4 — una sola ModelGradingRule aplana la resta de POMs a FIXED en
silenci (mina; el fix és semàntica de grading) · R6 — close_base no regenera mai
si hi ha specs de versió antiga.

**G6-B en marxa (decisions preses):** escriure sobre aprovada = 409 amb CTA
"crear versió nova" (MAI auto-bump — crear versió és decisió humana) · aprovar =
una sola direcció, @action amb CLOSE_GATES (aprovar és un gate; els gates són
humans) · des-aprovar per API NO existeix · guard centralitzat (patró _te_regles)
· test d'integritat: snapshot(aprovada) idèntic abans/després d'escriptura
rebutjada · gv67/182 protegida, historial NO es reescriu.

**Cua aprovada post-G6-B: paquet ANOTACIÓ ASSISTIDA** (tesi Agus: "millor 70-90%
d'efectivitat i 30% de feina que 100% de feina que el cansament no fa"). LLEI:
el sistema MAI escriu — proposa amb confiança i desglòs de senyals, el tècnic
confirma (= el gest manual, mateix camí de codi), el rebuig persisteix (un NO
també és informació). **A1** detecció de pinces (signatura geomètrica; tests
negatius manen) · **A2** proposta de cosits (piquets homòlegs = senyal fort +
longitud amb frunzit INFERIT del excés sistemàtic + semàntica de noms + cobertura
global; la taula de propostes del Tate = la demo comercial) · **A3** POMs per
recepta+plantilla GTI — POST-Montse (les receptes són seves). Briefs A1/A2
donats; llançar NOMÉS després de G6-B, seqüencials.

### G6-B TANCAT — EL SEGELL JA NO MENT (2026-07-13, 5 commits, 374 tests)

Guard ÚNIC a _get_or_create_grading_version (cap guard local: els endpoints
tradueixen l'excepció). Els SIS camins → 409 GRADING_VERSION_SEALED amb la
sortida al cos (bump existent). CAP auto-bump ("si el motor et creés la versió
nova tot sol, el segell hauria deixat de voler dir res"). Cas viu gv67/182:
refusat, petja idèntica (42 specs), historial NO reescrit. CRUD tancat:
retrieve/list/approve (close_gates); create/update/destroy = 405. Confessió que
val or: G6-A es va verificar CRIDANT EL SERVEI i dos callers conservaven el gate
vell (el 163 graduava pel motor però no per la UI) — "VAIG PROVAR EL MOTOR, NO
EL CAMÍ" — arreglat, 3 llocs criden _te_regles.

**EL SETÈ CAMÍ (decisió Patró C):** resolve_size_check escriu BaseMeasurement i
només bumpeja amb deltes → la base pot moure's sota una versió segellada. NI
bloquejar (subordinaria la mesura al grading — la llei és la contrària: l'última
mesura és la veritat) NI auto-bump (versions buides = soroll). Fix = **DETECTOR
D'ESTALITUD** (generated_from_version ja existeix, mai implementat): el segell
diu la veritat sobre el que es va aprovar + el sistema diu "la base s'ha mogut
des de llavors" (flag API + avís UI + GradingSnapshot del motor → el gate
d'exportació ho ensenya). = **G6-B2** (petit, post-A1) amb **R7**
(UniqueConstraint parcial: UNA is_active per SF; CAP constraint sobre aprovades
— l'historial és legítim). R4+R6 → G6-C amb Montse.

**El motor JA POT CONFIAR en gv.aprovada. El pinçament es manté** (G6-B el fa
fiable, no el retira — despinçar és decisió a part).

### A2 TANCAT ABANS QUE A1 (2026-07-13, 3 commits, 256 tests, migració 0006)

### A1 TANCAT — EL MOTOR VEU LES PINCES (2026-07-13, 3 commits, 272 tests, migració 0007)

**Titular:** la lateral del Tate passa de NO CASA a CASA marcant la pinça que EL
MOTOR HA TROBAT SOL (1,33+1,01=2,34; aritmètica idèntica al banc W4b; confirmar
= el gest de W4b, cap endpoint nou).

**DUES CORRECCIONS DEL MATERIAL AL BRIEF (el material mana):**
1. **La pinça de vora apunta cap a FORA** (el brief deia DINS — error de
   l'arquitecte): és tela que sobra i que desapareix en cosir-se; ha d'existir.
   V cap a dins = osca, no pinça. Verificat per 2 vies independents.
2. **La forma NO distingeix pinça de cantonada** (ràtios idèntiques a escales
   diferents: la invariància d'escala mata els criteris de forma). El que les
   separa: **BOCA vs VORA** (pinça 1,1%; cantonades/corbes ≥3,1%; llindar 2%).
   "Una pinça és un accident local d'una vora llarga; una cantonada és
   l'estructura de la peça."

**Resultats:** 2 candidats / 0 falsos positius sobre ~130 girs — i el segon és
LA PINÇA SIMÈTRICA que W4b no havia marcat (el sistema troba el que la mà es va
deixar). AMELIA: 0 (no en té). Confiança 48% HONESTA: penalitzada per
l'asimetria de costats — el mateix defecte que la persona va veure a W4b, ara
cobrat pel motor. 4 falsos positius rebutjats amb geometria explicada i
convertits en tests (els negatius manen). Reutilització d'A2 sencera
(DartProposalRejection germà, no fila; clau canònica; API no-persistida).

**PAQUET ANOTACIÓ ASSISTIDA A1+A2: COMPLET.** El Taller obre un DXF de client,
troba les pinces, proposa les costures amb frunzit inferit, i espera el criteri
del tècnic — la tesi del 70-90% feta producte.

**Pendents Agus:** neteja sew #12 (reobrir→casat→reanomenar) + CONFIRMAR la
pinça simètrica proposada (estrena real del flux) · e2e: línia mantinguda ·
G6-B2 (estalitud + R7) briefat, a la cua.

### G6-B2 TANCAT — EL SISTEMA DIU QUAN UN SEGELL HA QUEDAT ENRERE (2026-07-13, 3 commits, 403 tests, migració fitting.0016)

**Decisió de terreny (ratificada): CAP snapshot nou — el registre append-only ÉS
l'snapshot.** generated_from_version és insuficient (el desa de la fitxa escriu
BaseMeasurement sense tocar el comptador — test que ho clava);
MeasurementChangeLog ho veu TOT perquè penja del model de dades (post_save), no
d'un camí de codi. El comptador queda de SEGON TESTIMONI. Un snapshot hauria
estat una segona còpia d'una veritat ja registrada, amb risc de divergir.

**QUATRE ESTATS, un és "NO HO SÉ":** fresca · estala (amb els canvis datats) ·
desconeguda (segell sense data / specs sense origen — R11: camí de codi mort) —
"no saber i dir que va bé són coses diferents": la desconeguda s'ensenya amb
avís, mai es dona per bona. Dades reals: gv67 FRESCA · gv65 ESTALA (4 canvis
post-segell) · gv30/gv53 DESCONEGUDES.

**EL PANY DEL texts_shown (no era al brief — troballa major):** venia sencer del
client → es podia ometre l'avís que més importa. "Un reconeixement que es pot
buidar des del navegador no és cap reconeixement." Ara EL SERVIDOR enganxa
l'avís d'estalitud des de la mateixa versió que s'exporta — integritat LEGAL
del gate d'exportació.

**R7:** auditat abans (0 duplicats), constraint parcial exercida en viu (segona
activa rebota; segona aprovada inactiva entra — l'historial d'aprovades és
legítim). **Fixture _SegellBase corregit, detector NO afluixat** (segellava
abans de la base que signava: el detector tenia raó). Serializer porta
l'estalitud → qualsevol llista futura la té gratis.

**G6: A + B + B2 COMPLETS.** Queden G6-C (R4 aplana-a-FIXED + R6 close_base —
amb Montse) i R11 (segells històrics sense data — menor). El pinçament del
motor es manté per disseny; ara descansa sobre un segell que diu la veritat i
que confessa quan no la sap.

### 🚀 DEPLOY A PROD (2026-07-14, 05:01 UTC) + LA FITA DELS 4 MINUTS

**Desplegat a fhorttextile.tech** (merge dev bf35a0b → main 6f6181b, 105 commits,
~96k línies): motor de patrons complet (app patterns, 11 taules, tab + Taller +
propostes A1/A2 + export amb gate) · importació QA-S8 sencera (guard, llindar,
parser determinista, FileDropCard, diccionari, biblioteca) · G6 (segell íntegre,
estalitud, R7). Backup fhort_pre_motor_20260714_0452.dump (757K, verificat).
Migracions 10/10 als dos schemes, auditades a psql (constraints parcials com a
índexs únics: gradingversion_una_sola_activa_per_sf + patternfile_un_sol_
successor). ezdxf 1.4.4 al venv de PROD. VITE_API_URL=app.fhorttextile.tech és
CORRECTE (deploy de dominis 12/07, no la cicatriu). Smoke 200/200/401/200.
⚠️ El parser ràpid d'Excel s'encén per primera vegada a la seva vida a PROD —
vigilar la primera importació de tercers. ⚠️ Avisar la Montse: editar grading
aprovat ara dona 409 amb "crear versió nova" — és el sistema, no un error.

**LA FITA (Agus, mans pròpies, a PROD):** model Tate SENCER en **4 MINUTS** —
catàleg de POMs de Brownie carregat + fitxa importada + fitxers pujats + DXF
llegit + peça cosida. Tot perfecte. **És el número del Salva** ("del vostre
Excel i DXF a un model viu, mesurat i cosit: 4 minuts — cronometrat en
producció amb material real") i el guió d'obertura de la sessió Montse: que el
cronòmetre el posi ella.

### D10 — JA ERA MORT (2026-07-14): lliçó de dietari

El brief D10 es va executar i **el fix ja era viu** (fdb418c, 13 jul 14:21 —
una sessió d'ahir el va resoldre i el dietari no es va tancar). La disciplina
de precondicions de l'agent va evitar la implementació duplicada. Verificat
per lectura de flux: 3 valors (auth.js:16-24), DESCONEGUT → espera mai
redirect (App.jsx:79), from amb query params sencers (Login.jsx:57-59),
expiració per 401 intacta (navegació dura reconstrueix l'store). **LLIÇÓ DE
MÈTODE: abans de re-briefar un defecte, git log --grep — el dietari només és
fiable si es tanca amb la mateixa cura amb què s'obre.** Ratificat: NO muntar
infra de tests per verificar una peça (la infra >> la peça; vitest serà
decisió pròpia, no dany col·lateral).

**D10b registrat** (micro-paquet, propera sessió frontend oberta, no mereix
sessió pròpia): netejar isAuthenticated mort (auth.js:23,29,42,75, cap lector)
+ l'expiració per 401 conserva el from (client.js:20 — caducar al Taller ha de
tornar al Taller, no al taulell).

### DIAGNOSI W6-GTI + FITXA (2026-07-14) — l'ordre del tauler canvia

**Titular:** els 2 sprints de la fitxa són MOLT més barats del que s'assumia;
W6 és més car per DECISIONS, no per codi. **ORDRE APROVAT: F1 Peces a la fitxa
→ F2 Fitxers unificats → W6** (valor visible primer, risc quasi nul, exercita
el render del motor dins del lliurable que el client veu).

**Troballes de terreny:** el PDF de la fitxa es genera AL NAVEGADOR (pdf-lib;
Django només desa el PDF fet) → **render-signed JUBILAT DEFINITIVAMENT** (el
navegador ja baixa bytes autenticats → dataURL) · l'element "peça de patró" no
toca Python (~6-8 punts, 1 fitxer + i18n) amb LA TRAMPA DELS DOS SWITCHES
(canvas + generador PDF: només el primer = peça a pantalla i PDF BUIT) · el XOR
d'upload d'item JA EXISTEIX (PatternFileViewSet.create accepta
garment_type_item) però darrere: model-poms fa 400 sense model i **sew_specs
retorna 0 costures EN SILENCI per a patrons d'item** (cap export calla mai res
→ abast W6) · delta 4 del W6 infravalorat: el XOR és a TRES taules (SewRelation
+ 2 rebuigs A1/A2, mateixa FK model NOT NULL) — migració trivial (4 files) ·
delta 2 amb trampa: el gate de l'anotació avui ÉS el rellotge (disabled=
{!tascaId}) → treure'l al catàleg treu el gate: **deltes 2+3 ES DECIDEIXEN
JUNTS**.

**DECISIONS (2026-07-14):**
1. **Porta del Taller (DECISIÓ AGUS, substitueix la proposta "Biblioteca de
   patrons" de l'arquitecte):** entrada "Taller de patró" al menú DISSENY,
   germana de "Fitxa tècnica" — MATEIX patró canònic de picker, amb DUES
   BRANQUES (Models per client | Catàleg per família→item amb estat de base).
   Obrir model = taller amb rellotge; obrir item = taller GTI (porta CONFIGURE,
   sense rellotge — proposta arquitecte pendent de validació final). Cap pàgina
   de detall d'item s'inventa. ⚠️ LLIÇÓ DE MÈTODE (2a vegada): l'arquitecte
   proposa i dimensiona; les decisions de producte són d'Agus — "estàs decidint
   modals sense mi un altre cop".
2. **Gate del Taller-GTI = CONFIGURE a la porta** (no rellotge). La Montse el
   té de disseny (perfil 13); si a dades només admin → grant (acció de dada).
3. **Les bases de biblioteca viuen i s'exporten EN TALLA BASE** — la biblioteca
   ven forma, el model ven mides.
4. **LLEI DE BIFURCACIÓ-PRIMER (Agus):** l'autoguardat només escriu al fitxer
   obert; derivar-ne un de nou és acció EXPLÍCITA i PRÈVIA — al picker ("obrir
   com a base d'un de nou": destí exacte + nom ABANS del canvas) i dins
   l'editor ("duplicar cap a...", commuta l'autoguardat al nou). El versionat
   és xarxa, no disseny. Mata el Path 2 (matxacar el vell amb l'autoguardat).
5. **.FTT = FORMAT DE BIBLIOTECA** (intern, semàntic: POMs marcats + costures
   informades = mitja fitxa feta). Sketch a GTI en .ftt, MAI export a SVG. SVG
   només com a ENTRADA externa (Illustrator→SVG; .ai no) i renderitzat sempre
   com a imatge (mai injectat en cru — scripts). DXF = patrons.
6. **Noms composts:** [codi estructural automàtic: item/model] + [nom
   descriptiu lliure] ("jumpsuit · top tirantes mundial futbol").
7. **"Convertir model en sketch" (promoció model→GTI):** botó a la fitxa →
   tria item + nom → neix .ftt a GTI. **EL TÈCNIC SELECCIONA què viatja** —
   les mesures viuen a les taules, no al dibuix; el diàleg és selecció, mai
   imposició ("aquí el producte s'escapa del nostre ús i passa en mans de
   l'usuari"). Simètric: importar sketch GTI→model = fitxa gairebé construïda
   (derivat_de_item).

8. **ABAST DE LA PROMOCIÓ (decisió Agus 2026-07-14, tanca S0):** al sketch de
   biblioteca VIATGEN estructura + dibuix (sketch_svg/paths) + POMs marcats
   AMB LA SEVA NOMENCLATURA (codi de client inclòs — el tècnic guarda el seu
   vocabulari, és el seu arxiu de treball; editables al destí si vol, mai
   imposats) + costures informades + estat ESPERAT ("què s'ha de connectar").
   ES BUIDEN: valors de mesura (viuen a les taules del host) + vincles de host
   (model_id/size_fitting_id → null, "per vincular") + snapshot congelat (mai
   valors d'un fitting concret). La nomenclatura NO és mesura → no viola
   sobirania; preservar-la és protegir la feina del tècnic, no imposar-la.

**F1 briefat** (frontend pur: element peça-de-patró amb ELS DOS switches,
escala A4 vs peça de metre i mig, guionitzat amb PDF rasteritzat i verificat)
— ortogonal a tot l'anterior, llest per llançar. **Diagnosi de terreny .FTT
briefada** (desat actual, anatomia del .ftt, picker canònic, ItemFitxer+.ftt,
derivat_de_item pas a pas) — el paquet sencer es reescriu amb la seva
evidència.

### DIAGNOSI .FTT BIBLIOTECA (2026-07-14) — el terreny dona la raó al disseny

**TITULAR — SESSIÓ 0 prerequisit:** `unfreeze_document` (el que neteja un .ftt
per viure a un altre host) NO toca les taules snapshot (model_id, rows amb
mesures congelades) ni `data_block.size_fitting_id` (re-fetch viu contra el
fitting ORIGEN) — copiar una fitxa d'A a B portaria les mesures d'A EN SILENCI.
Encara no ha mossegat (0 files derivat_de_*: la maquinària de còpia mai s'ha
exercitat) — arreglar-ho ARA és gratis. Inclou l'asimetria item→model (no
descongela; docstring falsa) i el fix tipus='ALTRES' del .ftt a item (→ 404).

**El terreny és favorable:** el picker de dues branques NO es construeix — ES
DESBLOQUEJA (AssetNavigator ja navega Models|Catàleg; el fork era tancat dins
mode==='files') · el motor de bifurcació JA EXISTEIX (la prohibició és 1 línia,
el descongelat+re-resolució és a sota) · .ftt i .svg JA són a la whitelist ·
churn quantificat: 225 versions per a 6 fitxes (autosave debounce 2s = ZIP
sencer per canvi) — la bifurcació-primer no lluita contra el sistema, el
corregeix · **L'ANATOMIA DEL FORMAT VALIDA EL CRITERI D'AGUS**: tot el
promocionable (sketch_svg, paths, field chips sense valor, capçalera) és
estructura pura; tot el fràgil és taules i logo — el defecte natural del diàleg
de selecció ("estructura sí, taules no") és l'anatomia donant la raó, no una
opinió.

**DECISIÓ (Patró C, sobre la pregunta de la diagnosi):** les taules snapshot en
descongelar es BUIDEN CONSERVANT L'ESTRUCTURA + estat VISIBLE "per vincular al
model" + ids a NULL; re-vincular = acció del tècnic al destí (1 clic), MAI
automàtica. Ni esborrar (perd l'estructura triada) ni òrfena-que-sembla-plena
(el Path 2 amb una altra cara). RES EN SILENCI.

**SEQÜÈNCIA APROVADA (dimensions de la diagnosi):** S0 unfreeze complet (~1) →
bifurcació-primer (~1,5-2) → porta-picker (~1, desbloqueig) → sketches a GTI
(~1-2) → promoció amb selecció (~1,5). S0 briefat; llançar quan F1 reporti
(un sol escriptor).

### F1 TANCAT — PECES DE PATRÓ A LA FITXA (2026-07-14) + deute del registre de tipus

Element peça-de-patró operatiu al canvas I al PDF. **TROBALLA ESTRUCTURAL:** el
generador PDF (pdf-lib) i el canvas són DOS motors amb DOS catàlegs de tipus; el
default del PDF pintava un REQUADRE GRIS silenciós per a tot tipus desconegut
(F1 ho va patir amb patternPiece). Bugs nets: nom_peca amb ?? enlloc de || (peça
"0"/"" perdia nom — 3a vegada del patró || vs ?? aquesta setmana: mirar com a
patró) · proporcions esperant reflow.

**DEUTE AMB NOM — BIB-registre (aprovat, abans de la promoció):** registre ÚNIC
de tipus que les DUES bandes (canvas + PDF) consumeixin, en lloc de dos switch
sincronitzats a mà. La biblioteca multiplicarà els tipus que viatgen → sense
això, cada tipus nou és un requadre gris potencial al PDF d'un altre host.
**INVARIANT afegit a S0/T3:** l'estat "per vincular" i els tipus que viatgen no
cauen mai al default gris — placeholder honest, mai gris mut.

### IMPORT MASSIU DE MODELS — bug de PROD (2026-07-14, Salva bloquejat)

**Context:** el Salva vol donar d'alta 20 models FW26 de Brownie (TWIST…JESTER,
Woman, run XS·S·M base S) per pressupostar; l'import per la UI peta a PROD.
Decisió: **PROD rep NOMÉS aquests 20 (alta de dades comercial); el fix es fa a
staging i entra per deploy** — mai fix en calent a PROD.

**CAUSA REAL (diagnosi staging, hipòtesi dels espais FALSADA amb dades):** NO és
la plantilla (capçalera idèntica) ni les dades (tot casa) ni el parser (_split_
sizes ja fa strip, errors ja llegibles per fila). És **TRES GENERADORS DE
codi_intern QUE NO ES PARLEN**: signal (MAX), wizard (MAX), bulk import
(ModelSequence). El comptador ModelSequence viu a zero mentre Brownie ja té
models manuals → reserva BRW-SS26-0001 que ja existeix → IntegrityError → 500
(rollback net, cap dada a mitges). **Peta el primer import de QUALSEVOL client
amb models previs, i cada cop que algú en crea un a mà entre dos imports.**

**Fix staging (sprint IMPORT):** T1 sincronitzar el comptador (floor = max(
last_seq, MAX real) dins el select_for_update) — cura la causa · T2 commit_view
captura IntegrityError → 409 llegible · T3 es_conjunt textual robust ("NO"/
"FALSE" ara truthy → fila peta). **DEUTE ANOTAT:** els 3 generadors han de
convergir en UN servei canònic + unificar els 2 formats (BRW-26-SS-0002 vs
BRW-SS26-0001) — sprint propi.

**Via PROD (desbloqueig del Salva, decisions Agus):** alta per la via fiable
(create_model_wizard, que ja fa MAX real — evita el bug del comptador) amb
GUARDA: llegir MAX(sequencial) real abans de generar, verificar al dry-run que
cap codi xoca. Normalitzacions confirmades: KNIT/WOVEN, WOMAN, XS·S·M base S.
Talla base SENSE grading (opció b — el Salva pressuposta, no gradua; ruleset
després a la UI). garment_type_item per DEFECTE de família (Jersey Tops→8
Samarreta, Buttoned→5 Blusa, Skirts→26 recta, Dresses→31 estructurat, STARLITY→
GT68 item18 Pantaló estructurat) + plantilla nom→item_id perquè Montse/Salva
afinin la variant. Dry-run amb OK explícit d'Agus abans de l'apply; verificar
1 model a la UI abans dels 20.

### VIA PROD TANCADA + SPRINT IMPORT + IMPORT-2 + LA SAGA DE BRANQUES (2026-07-14)

**Els 20 models CREATS a PROD** (seed idempotent, schema fhort garantit per 3
vies, ids 194-213, BRW-FW26-0023..0042, MAX(seq)→42, verificats per l'endpoint
HTTP real als 2 dominis). Salva treballant. Command+CSV commitejats a dev
(61d2724). ⚠️ NEAR-MISS: l'agent va fer checkout dev al working tree de PROD
(codi al disc revertit; gunicorn en memòria va salvar) — corregit a main
immediatament. LLEIS NOVES: (1) el tree de PROD viu SEMPRE a main (commits de
dev via git worktree a part o des d'staging); (2) mai merge de branca sencera a
PROD sense diff previ.

**SPRINT IMPORT (staging, 4 commits):** T1 comptador monòton (floor=max(seq,
MAX real) dins select_for_update — test que falla amb l'IntegrityError EXACTE
de PROD i passa amb el fix) · T2 commit_view 409 llegible · T3 _as_bool robust.
Correcció Fase A: ModelSequence no era buida — buida NOMÉS per BRW/SS (FW era a
15). **DEUTE registrat** (DEUTE_CODI_INTERN_TRES_GENERADORS.md): 3 generadors +
2 formats de codi_intern → sprint propi mitjà-gran (migració de dades sobre
unique visible al client — decisió de format = Agus).

**LA SAGA DE BRANQUES (correccions en cadena — lliçó d'arquitecte):** vaig
dir "inversió" (fals) i després "bifurcació" (fals). La diagnosi real: **dev =
main + 110 commits, superfície de conflicte ZERO** (merge-base primer!, el
6f6181b era un hash fantasma, les "642 vs 646 línies" eren soroll d'arbre de
treball brut). LLIÇÓ: abans de dimensionar branques, merge-base. I LA TROBALLA:
**origin/main NO reflecteix PROD** — el deploy del matí va aterrar a la màquina
(motor confirmat funcionant per Agus, ensenyat al Salva) però el main LOCAL no
es va pushar a origin. → RUNBOOK NOU: després del merge de deploy, push de main
a origin + verificar origin/main == main local abans de tancar. Diagnosi
d'estat real de PROD briefada (prèvia obligatòria al proper deploy: certificar,
re-alinear origin, validar encaix del fix, llistar nou-vs-ja-hi-és).

**SPRINT IMPORT-2 — LA CONCILIACIÓ (staging, 3 commits):** el pas 2 del wizard
DEIXA DE SER preview i passa a CONCILIACIÓ fitxer↔catàleg: per fila×camp,
MATCH/NORMALITZAT (amb "abans→després" visible)/NO_MATCH (bloqueja LA FILA amb
motiu, mai l'import)/BUIT (gris, no compta — no saber ≠ encertar) + codis
previstos amb anti-col·lisió VISIBLE ("20 OK i 20 codis lliures") + idempotència
visible (re-import = complement, no duplicat) + invariant promesos==escrits.
Ratificat: checkbox indicador no control (selecció real = peça futura si cal) ·
convergir el pas 2 enlloc de 5a pantalla · troballa: error arxivat sota columna
equivocada (run_talles vs talla_base), caçat CONSTRUINT la pantalla.

**PENDENT IMMEDIAT:** diagnosi PROD → deploy pas a pas (fix+conciliació) amb
re-alineament d'origin/main al runbook.

⚠️ **Coordinació:** A1 mai es va llançar (A2 va entrar directe) i A2 va córrer
EN PARAL·LEL amb G6-B (dos escriptors — territoris disjunts, va sortir bé PER
SORT; la regla d'un-sol-escriptor es manté). A2 va construir ell el patró
compartit (SewProposalRejection + clau canònica + 3 portes) → **la dependència
s'inverteix: A1 reutilitza A2** (brief revisat donat).

**LA TAULA DEL TATE: 28 propostes netes de 112 candidats** — lateral, espatlles/
canesú, màniga↔sisa amb FRUNZIT INFERIT (0,86 cm, 5,9% — l'embut llegit de la
geometria). Exclou el ja-cosit. Les _LINI de l'AMELIA també surten. Guionitzat:
3 confirmades d'un clic (indistingibles de manuals) + 1 rebuig persistent +
cobertura verda + Tate net.

**Lliçons empíriques (cap suposició les hauria encertat):** (1) cada piquet surt
DUES VEGADES del CAD (tall + cosit a 7,5 mm) → dedupe per posició; (2) TOTS els
piquets seuen sobre GIRS → el senyal compta extrems inclosos; (3) sisa i copa
subdividides pels MATEIXOS piquets → el frunzit s'infereix tram a tram.

**Calibratge honest:** llindar 0.30 → 41 propostes, 30% soroll; branca NEGATIVA
del senyal de noms (bessones, entretela, famílies llunyanes) + llindar 0.40 →
28 sense perdre res de cert.

**Forats documentats (backlog):** mateixa-peça no es proposa (sota-màniga a mà;
el guard anti-simetria és disseny fi) · **A2.1**: matching 1:1, no N:N — quan una
pinça declarada parteix un tram, proposar la unió virtual (la lateral real del
Tate és 2⛓2).

**Neteja de dades (Agus, per la UI de W4b):** SewRelation #12 és la lateral del
seu QA etiquetada 'pinca' amb noms de trams creuats → reobrir, tipus casat,
reanomenar. **E2E navegador:** el harness va blocar encunyar un JWT — correcte;
línia mantinguda (cap credencial; usuari e2e dedicat = decisió Agus, recomanació:
no ara). **PUSH EN ESPERA** del tancament de G6-B (els commits d'A2 seuen sobre
els seus T2–T4).

### 🚀 DEPLOY #2 A PROD (2026-07-14, 16:36 UTC) — TANCAT + QA-TALLER (07-15)

**Deploy #2** (main 6f6181b→315f369, 16 commits, ZERO migracions — tot codi pur):
fix comptador + CONCILIACIÓ (BulkImportReconciliation) + F1 peces a la fitxa +
BIB S0 (unfreeze). El "6f6181b fantasma" ERA real (main local de PROD, mai pushat
— re-alineat al pas 1). Backup 865K. `.env` de PROD havia DESAPAREGUT (col·lateral
del near-miss del checkout; no trackejat → cap checkout el restaura) → reconstruït
(app.fhorttextile.tech) i verificat DINS del bundle compilat (grep al JS, no al
font). Smoke 200/200/401/200/401(conciliació viva). **Push final de main VERIFICAT**
(origin==main==HEAD). **LLEIS DE RUNBOOK DEFINITIVES:** (1) PAS -1 hostname+pwd
abans de tot (avui vam anar a staging per error); (2) llegir el cens SENCER abans
del merge; (3) verificar .env existeix + bundle compilat porta la URL; (4) push de
main a origin sempre pas explícit i verificat al final. Anotat: staging té un
fhort.service DUPLICAT + main local antic — mirar un altre dia.

**QA-TALLER-A TANCAT (07-15, 4 commits, 362 tests):** el tram s'expandia al canvas
(seg 314: 4cm pintat 13) — causa: EPSILON amb signe girat a puntsDelSegment
(eixamplava en lloc d'estrènyer; l'imant cau sobre vèrtex → aresta veïna entra).
CORROBORAT per 2 sessions independents (dades reals + vora sintètica). T1 epsilon
(4/4 error 0,00) · T2 ENVOLTA consolidat (5/5: reordena per RECORREGUT no per índex
— 3r cop que "el tram que envolta l'origen" dona guerra) · T3 color: blau=IDENTITAT
(preview i desat el mateix objecte), taronja=ASSENYALAR (selecció) — via tokens.
Cap dada de BD dolenta: defecte de PINTURA. Latent de pinça confirmat (àpex un
vèrtex de més, s'activava en declarar pinça).

**QA-TALLER-B (07-15, T1+T1b fets, 2 commits, 362 tests):** TRAMS NATURALS.
TROBALLA: el que sosté el mòdul NO és l'angle, és LA MÀSCARA — els piquets són
excursions en V amb girs de 63° (més forts que cantonades reals); emmascarats, el
buit corba(≤8,7°)/cantonada(≥28,5°) és net → angle a 22° amb tota la franja 20-25°
idèntica (test que clava la meseta). VALIDACIÓ QUE NO ES POT FALSEJAR: la capa
retroba SOLA les 2 costures que el patronista va declarar a mà a W4b (32,13=tram291,
29,80=tram290) sense ajustar cap número. TATE_FRONT 25→8 naturals, cobertura quadra.
**PENDENTS T2/T3/T4** (parada en frontera neta): T2 composts que salven pinces
(DECISIÓ: descompte de W4b MANA, T2 només UI — no duplicar; aritmètica ja verificada
297,89mm=29,79; el cas 69-71 espera Montse) · T3a el natural s'ofereix com a
PROPOSTA d'un clic al gest (Cosir segueix veient només declarats — la llei de W4
intacta; l'agent es va aturar davant la contradicció, RATIFICAT) · T3b A2 sobre
naturals (refactor candidats_del_patro, no un filtre) · T4 aprenentatge per rol.

### QA-TALLER T3b TANCAT (07-15, commit 4fe4c3b, migració 0008) — ELS TESTS VAN SALVAR PRODUCTE

**A2 sobre naturals materialitzats** (origen='natural', files reals com els AUTO —
CASCADE de FK invalida rebuigs sol en pujar versió; una vista sense id no es podia
rebutjar). Millora mesurada al Tate: 110→44 candidats, 27→7 propostes, soroll
5203→823, i surten costures reals (davanter⛓canesú 18,11⛓18,13, conf 0,96, casa).

**LA LLIÇÓ MAJOR (de mètode, general):** l'agent va dir "cap dels 12 tests vermells
és real" → l'arquitecte va construir el brief a sobre. FALS: 8 dels 12 caçaven un
TRENCAMENT DE PRODUCTE que el mateix refactor havia introduït (annotation_views.py:709
rebutjava en dur tot != ORIGEN_AUTO → confirmar-proposta d'A2 donava SEMPRE 400: la
confirmació estava MORTA). Els va salvar la REGLA 2 (no afluixar cap test): fer-los
passar tocant-los hauria codificat la conducta trencada. La correcció: == auto → ==
declarat (la docstring ja deia la llei bona; el codi la comprovava malament perquè
"derivat"=="auto" quan es va escriure). **REGLA NOVA: cap test és fals fins que
s'ha entès per què és vermell — un vermell és una afirmació que reclama, no soroll.**

**Invariants FETES MÉS EXIGENTS (no rebaixades):** comptar auto+natural per separat
(no l'agregat que passaria si una menàs deixés de generar-se) · exigir que els DOS
orígens hi siguin · el test del PROMOU comprova candidat abans/després + 201 del
confirm (el que va deixar passar el 400).

**CONTRACTE DE DADES CANVIAT (fet de producte, NO teòric):** cada peça porta trams
'natural' a més d''auto'. Qualsevol == auto implícit és bug latent (ja va mossegar
annotation_views:709). Nota dura per a C i tot el que toqui geometria.

**CORRECCIÓ DE DIETARI (T2):** l'arquitecte va escriure "descompte W4b mana, T2 només
UI" sense marcar que revertia el "compost mana" d'ahir — mateix error de dietari
repetit. VIGENT confirmada: descompte de W4b MANA, T2 només UI, brut+pinça-salvada
al compost. Espera Montse (69-71).

**Deploy: el paquet QA-Taller ja NO és codi pur** — porta migració 0008 (+ la de T4
quan es faci). Pendents: T4 (aprenentatge per rol, migració) · C (llista POMs).

### QA-TALLER T4 TANCAT (07-15, 3 commits e85257c/0cd2142/e2c4c2e, 380 tests, migració)

Aprenentatge per rol de peça: la confirmació humana registra preferència (rol +
signatura paramètrica t, no ids · confirmat/allargat/tallat · idempotent vegades=N).
Senyal al Tate: base 0,833 · +confirmat 0,883 (+0,05) · +tallat 0,633 (−0,20).

**LA PEÇA CLAU (geometria mana, de debò):** el costum entra per la porta EXISTENT
_te_evidencia_geometrica (seam_matching:591-596) — SUMA, no habilita. Pes 0,10 (sota
el nom: el nom descriu la peça del davant, el costum el que algú va fer en una ALTRA).
Test que fixa que CAP preferència fa néixer una costura que la geometria no sosté.

**DECISIONS RATIFICADES:** (1) rol = nom NORMALITZAT, no canònic (aama_reader:376
rol=piece_name) — un FRONT per subcadena col·lapsaria davanter+vista+canesú i faria
viatjar l'après on no toca. Preu: la preferència NO viatja entre estils — ACCEPTABLE
perquè el vehicle entre estils és W6 (correspondència homòloga explícita, amb Montse).
Rol canònic rol↔nom → agenda Montse. (2) allargat s'acumula però NO mou res ("aquí
havia de ser més llarg" no diu QUIN tram — fer-ne senyal = inventar la intenció, prohibit;
desats per a W6).

**Per a C:** A2 porta ara 4 menes de senyal (no 3) — UI s'ha d'obrir. i18n-gate: frase
del servidor = català pla al title; el text de fila el construeix la UI de dades (noms
de peça confirmats/contra).

**PAQUET TALLER (QA-TALLER) — estat:** A ✅ · B (T1,T1b,T3a,T3b,T4) ✅ · C ✅ · E ✅ ·
**T2-composts EN PAUSA** (Montse 69-71, únic viu del paquet).

### QA-TALLER E TANCAT (07-16, 5 commits b3e6fa0..3b5a899, 306 tests executats)

Jerarquia visual del panell (capçaleres alt contrast via tokens · tipografia dels trams
unificada amb els POMs) + SELECCIÓ PER GRUP amb bulk delete (casella "tots" per secció +
per fila + paperera amb compte + CONFIRMACIÓ; per-ítem-atòmic amb informe d'èxit parcial).
Guionitzat servint el bundle nou contra staging real; base exacta restaurada i verificada
per SQL.

**La revisió pre-tancament va caçar 4 troballes (F1 ALT: un bloc que rebota deixava la
pantalla MENTINT — files mortes pintades, sense error; l'agent el va reconèixer com a seu
i el va arreglar amb el patró de la casa: catch + recàrrega al finally + selecció buidada).
F2 marca fantasma (la clau d'una proposta es recalcula, no és pk → re-proposta reapareixia
MARCADA; test validat TRAIENT el fix — "un test que no he vist fallar no és un test").
F3 paritat bulk↔destroy (check_object_permissions per ítem — el comentari afirmava una
llei que el codi no complia). F4 informe ranci netejat.**

**Ratificat:** propostes SENSE bulk-delete propi (esborrar-ne una = crear el rebuig; un 2n
camí = lloc on la llei del rebuig divergiria) · pinces proposades sense selecció (grup
petit per disseny; s'afegirà si mai cal) · trams orfes en esborrar costura confirmada =
DECISIÓ PENDENT (fills de la costura o entitats pròpies? — criteri Montse quan el Taller
rodi). **Micro-paquet D10b creix:** variant destructiva del Modal + nom accessible de les
caselles de fila.

### QA-TALLER F TANCAT (07-16, 3 commits 59b9e8c/0c97230/b5ad894, 309 tests) — PROPOSTES SOTA DEMANDA

**L'ús real va tombar la ratificació d'E** ("esborrar proposta = crear rebuig"): les
propostes es recalculaven soles a cada recàrrega (rebutjar-ne una alliberava trams → el
motor en proposava de noves: l'HIDRA) i el bulk creava 27 rebuigs PERMANENTS no deliberats.
Fix: **la llista és de l'usuari, no del motor.** Grup arrenca BUIT + botó "Buscar propostes"
(A2 sota demanda, respecta rebuigs); CAP recàlcul automàtic. DUES accions amb semàntica
diferent: "Netejar" = EFÍMER (buida la vista, cap escriptura, re-buscar les torna) · "Rebutjar"
= PERSISTENT (el NO deliberat, en bloc amb confirmació que diu "permanently"). Recompte honest
+ línia "N parelles rebutjades no es mostren" amb veure/desfer (endpoint nou list+destroy de
rebuigs). **DECISIÓ SUPERADA:** "esborrar proposta = crear rebuig" (E) → netejar i rebutjar
són actes DIFERENTS (F).

Guardians: revisor-diff va caçar el buit que mentia (netejar deixava cercades=true → "el motor
no veu cap costura" quan les havies AMAGAT, contradeia T3) · e2e va caçar un TDZ que el build
no veu (useEffect referenciant una useCallback de més avall) · el classifier va blocar un DELETE
massa ample (neteja per id explícit). Watchpoint anotat: propostes no es reseteixen en canviar
de model in-page (no explotable — la navegació desmunta).

⚠️ **DEPLOY STAGING:** sew-proposal-rejections/ dona 404 fins que es reiniciï ftt-staging.service
(reiniciar = desplegar dev en viu; fer-ho amb el tauler quiet). La resta d'F ja funciona.

### 🔷 MÒDUL D'AUDITORIA DE MODEL (2026-07-16, ANOTAT — la peça que tanca el cercle FTT)

**Origen:** el veredicte de la Montse sobre la pinça 69-71 del Tate — **és DEFECTE** (costats
desiguals 1,3 vs 1,0, 3,1 mm: trenca la geometria de la peça → farà arruga o el cosidor haurà
de retallar a mà). **PRIMER DEFECTE REAL trobat pel sistema en un patró de client.** És el
mòdul que vam amagar dels tabs de model (ESTAT_BACKOFFICE / la fitxa d'empresa).

**INTENCIÓ (no disseny — sessió pròpia amb Montse):** una capa transversal que avalua
MESURES + GRADING + PATRÓ + ESCALATS DE PATRÓ en un sol lloc i respon la pregunta del PM (no
la del tècnic): **"això que enviem a producció, està bé?"** Recull els senyals de coherència
que avui viuen escampats (cada mòdul avisa del seu forat pel seu compte): quines toleràncies
es permeten, quins desajustos es troben. Assegura al PM que el que va a producció està bé →
evita costos i falles (tela, hores, retall a mà).

**Naturalesa:** gran part PARAMÈTRICA i DETERMINISTA (les toleràncies, els desajustos
geomètrics, el casat que no casa, la pinça que no tanca plana, el grading estàle) + recolzament
d'IA on toqui. **Tanca el cercle comercial de FTT:** no és una eina de dibuix, és la GARANTIA
que el que surt cap a la fàbrica no porta un defecte car.

**DISTINCIÓ FUNDACIONAL (llei, ratificada avui):** TOLERÀNCIA ≠ ERROR. Els 2mm de la màniga
(51,3 vs 51,5) = variació normal, s'absorbeix a mà sobre el matalàs en producció → el sistema
DIU "casa", NO proposa res. Els 3,1mm de la pinça = asimetria que trenca la peça → s'informa
amb xifra. **El sistema DETECTA + INFORMA, MAI modifica la geometria** (sobirania del dibuix
del tècnic — llei del motor: mai crea ni mou topologia). "Proposar modificar la peça perquè
encaixi" = porta que NO s'obre sense sessió pròpia (lliga amb PAT-3 rectificació post-fitting).

**Pendent immediat separat (NO és l'auditoria):** el fix del botó Cosir — la màniga es cus
sobre si mateixa (2 trams de TATE_SLEEVE) i el gate ho impedeix. La restricció "B tancat a la
peça de l'A" (W3, per POMs) es va propagar a Cosir de més: ha de passar de "peces diferents" a
"trams diferents" (mateixa peça = vàlid; mateix tram = absurd). Diagnosi read-only primer.
La UI ha de distingir "casa dins tolerància" (verd, endavant) de "asimetria que no tanca"
(mira-t'ho) — avui tots dos surten groc.

### QA-TALLER C TANCAT (07-15, 3 commits e8a4eff/7c6f6eb/4a9d986, 380 tests) — TANCA EL PAQUET

Llista de POMs: descripció idioma usuari (POMGlobal + àlies del customer si n'hi ha
UN sol: "El client en diu: X") · jerarquia tipogràfica (fitxa i mesurat GRANS i negres,
veredicte = xip de color) · popover "i" amb recepta. Guionitzat amb dades reals: CH
45,0→45,13 verd Δ0,13 · EK2 2,0→4,77 vermell Δ2,77 · 23 pendents (només fitxa) · àlies
"ANCHO PECHO" · popover amb recepta (Side seam→Side seam, ref 1cm sota sisa).

**TROBALLA: la recepta JA està mig plena** — 10/25 POMs del model ja porten start_/
end_/reference_point. El popover ja està encès per a la meitat. La feina de la Montse
és omplir 15 columnes que ja existeixen, cap camp nou (confirma la sospita de S6).

**Bugs caçats (mateix patró que T3b):** (1) el text() d'un senyal d'A2 queia a default
"noms" → pintava sig_name_undefined a la cara — la UI assumia que el motor no afegiria
mai un senyal nou; ara el defecte és el detall del servidor i el motor pot afegir-ne
sense que la UI els sàpiga abans (degradació amb gràcia — el que la biblioteca
necessitarà). (2) la fila era un <button> i la "i" no hi cabia (button dins button =
HTML invàlid, clic mort) → contenidor amb dos botons germans.

**Friccions (backlog):** POMGlobal no té descripcio_es (castellà cau a l'anglès canònic
— forat real del catàleg, no tapat inventant equivalències) · gairebé-invent de tokens
(--ok-bg/--err-bg són els bons, no --ok-pale; comprovat abans de commitejar — passa
build+lint, només es veu a pantalla).

**QA-TALLER-D (backlog, prioritat alta):** família "el motor mesura la vora amb
orígens diferents" — operations.py:717 _indexs_del_rang (cap costura declarada al
Taller es revalida en moviment → detector d'estalitud MENT en silenci) +
_longitud_indexs + segmentar_vora (t des del primer gir vs vèrtex 0, segments.py:
227-242). S'arreglen JUNTS amb una convenció única de recorregut de vora.

**QA-TALLER-C (pendent, darrere de B):** llista POMs — descripció idioma usuari
(canònic EN + local; T1 decisió: POMGlobal + àlies del customer si n'hi ha UN sol,
ambigu=canònic sol) + jerarquia tipogràfica (fitxa i mesurat GRANS i negres,
veredicte=xip de color) + popover "i" (T3: recepta = start_point/end_point/
reference_point que POMGlobal JA TÉ — buit=línia absent; s'encén sol quan Montse
els ompli, cap camp nou).

**PREGUNTES OBERTES PER A LA MONTSE (acumulades):** (1) pinça 69-71 del Tate:
pinça desigual (3,1mm) o piquet? — bloqueja T2 dels composts; (2) TATE_SLEEVE
natural de 0,2 cm (cantonada real però 2mm no és costura — fusionar/marcar?);
(3) receptes de mesura recta vs vora (POMMaster); (4) G6-C (R4/R6); (5) A3 POMs
per plantilla. **El paquet legal/comercial F1-F4 (pricing/free-seed/fitxa client/
docs legals) viu a dev, candidat a deploy propi — altra línia, no barrejar.**

---

*Document creat 2026-07-12. Es manté viu: S0 en refina els briefs, S8 en tanca el cicle
i re-prioritza el backlog. Font conceptual: MOTOR_DE_PATRONS_V2.md §4.4.*
