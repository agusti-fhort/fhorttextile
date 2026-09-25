# ORDRE — Sprint 1 · Fitxa tècnica (SVG=croquis · veredicte sencer · taules sota capçalera)

Data: 2026-09-24 · Patró B (autonomia condicionada al verd) · staging `/var/www/ftt-staging`, branca `dev`.
Substrat: `docs/diagnosis/DIAGNOSI_STAGING_NOMENCLATURA_CORPUS_FITXA.md` Bloc 4 + diagnosi PROD 24/09.
**Cap push fet.** Els 4 commits són locals a `dev`.

## SHA dels 4 commits

```
701245d2 fix(tech-sheet): S1.3-bis — yInici per pàgina a la paginació de taules
f57d48b1 feat(tech-sheet): S1.3 — les taules s'insereixen sota la capçalera
5a723c0a feat(tech-sheet): S1.2 — veredicte NO OK sencer a la columna, sense nota
4498643e feat(models_app): S1.1 — un .svg sense tipus és SKETCH_SVG (croquis)
```

Ordre cronològic: `4498643e` → `5a723c0a` → `f57d48b1` → `701245d2`.

---

## S1.1 · SVG = croquis — Commit A (`4498643e`)

**Punt obert de la diagnosi 4.1, confirmat abans de tocar res:** els dos fluxos de pujada
(canvas/editor i Finder) conflueixen en UN SOL component front (`FilePicker.jsx:110-127`,
`importar()`), que envia `fitxer`+`nom` però **mai `tipus`**. `TechSheetEditor.jsx:7571` usa el
mateix `<FilePicker>` per al panell «Croquis i flats». Backend: `upload_file_view`
(`views.py:2783-2825`) llegeix `tipus = request.data.get('tipus') or None` — sempre `None` des
d'aquest camí ("el Finder no l'ha enviada mai", comentari `:2807`) — i crida
`save_model_file(..., tipus=tipus, ...)`. Confirmat: els dos fluxos acaben a `save_model_file`
sense `tipus`.

**Canvi:**
- `backend/fhort/models_app/services_fitxers.py:285-288` — nou predicat `_es_svg(nom_fitxer, mimetype)`.
- `:358-362` (`save_model_file`) — `if tipus is None and _es_svg(...): tipus = 'SKETCH_SVG'`,
  **després** de l'herència de `versio_anterior` (mai trepitja tipus explícit ni heretat).
- `save_item_file` **NO tocat**: `ItemFitxer` comparteix el vocabulari (`models.py:598`) però cap
  lector el consumeix — `fitxersInseribles` del panell llegeix NOMÉS `/api/v1/model-fitxers/`
  (`TechSheetEditor.jsx:3542`), i `CatalegPecesItem.jsx:346-347` documenta explícitament que ja
  es va decidir NO exposar `tipus` al catàleg.
- Camins de còpia (`views.py:404,1866`, `item_fitxer_views.py:173`, `federation_service.py:934`)
  passen sempre `tipus` explícit — verificat, no tocats.
- Backfill: `backend/fhort/models_app/management/commands/reclassifica_svg_croquis.py` — dry-run
  per defecte, `--apply` explícit, transacció, idempotent.
- Test: `backend/fhort/models_app/test_svg_es_croquis.py` (5 casos: svg→SKETCH_SVG, png→ALTRES,
  tipus explícit mana, mimetype per extensió, versió nova hereta i no trepitja).

**Verd:** `manage.py check` net · 5/5 tests OK · verificador VERD · revisor-diff VERD (cap
signal sobre `ModelFitxer`, import "privat" `_es_svg` coherent amb el patró ja existent
`_compute_checksum`/`_guess_mimetype`, transacció íntegra, sense migració necessària).

**Dry-run del backfill a staging** (`tenant_command reclassifica_svg_croquis --schema=<s>`, sense `--apply`):

```
############ schema=fhort ############
=== reclassifica_svg_croquis · DRY-RUN (cap escriptura) ===
  model=TRV-SS27-0001 (837 VESTIT) · fitxer id=888 · 837_VESTIT.svg · versió=1 · is_current=True · ALTRES → SKETCH_SVG

Total: 1 fitxer(s).
DRY-RUN: cap fila tocada. --apply per aplicar.
############ schema=los ############
=== reclassifica_svg_croquis · DRY-RUN (cap escriptura) ===
  (cap fitxer a reclassificar)

Total: 0 fitxer(s).
```

Cap `--apply` executat.

---

## S1.2 · Veredicte sencer, sense nota — Commit B (`5a723c0a`)

**Mesura amb Konva real (word-wrap per mots, no la fórmula `Math.ceil(len/cabenPerLinia)` de
`liniesQueOcupa`) abans de tocar l'ample**, per a la taula `q8_fitting` (`fontSize=9`
body, `capcaleraFina:true`):

| ample columna | `cabenPerLinia` | `"ADJUSTED"` (8 car.) | `"NO OK, FOLLOW SPEC"` (18 car.) — fórmula | — word-wrap real |
|---|---|---|---|---|
| 22mm (abans) | 9 | 1 línia | 2 línies | **3 línies** (`"NO OK,"`+`"FOLLOW"`+`"SPEC"`) |
| 26mm (adoptat, OK Agus) | 11 | 1 línia | 2 línies | **2 línies** (`"NO OK,"`+`"FOLLOW SPEC"`, 11/11 car. — al límit exacte, sense marge) |

A 22mm la fórmula del propi codi subestimava (deia 2, calien 3): implementar el canvi tal qual
allà hauria fet vessar la tercera línia per sota de la fila. Es va aturar, mesurar amples
alternatius i demanar OK — **Agus va triar ampliar a 26mm**, l'únic valor mesurat que encaixa
per totes dues vies.

**Canvi** (`frontend/src/pages/TechSheetEditor.jsx`):
- `:5545` — columna `verdict`: `width: 22` → `width: 26`.
- `:5548-5555` — cel·la: `f.veredicte ? etiquetaVeredicte(f.veredicte, true) : ''` →
  `f.veredicte ? { text: etiquetaVeredicte(f.veredicte, false), wrap: true } : ''` (forma
  LLARGA, mateix mecanisme `wrap:true` que NAME: `cellaPom`/`cellaCodi` `:5331/:5338` →
  `buildTableCellPrimitives` `:910` → `liniesQueOcupa` `:934-938`).
- Retirat el `entrades.push({ nota: tEn('tech_sheet.q8_nota_no_ok') })` (abans `:5573`) i el seu
  comentari.
- Retirada la clau `q8_nota_no_ok` de `frontend/src/i18n/{ca,en,es}.json` (les tres, sense
  referència òrfena — `grep -rn "q8_nota_no_ok" frontend/src` buit).
- Cap pantalla tocada: `fittingGridAdapter.jsx` (botó de pantalla, forma curta) i
  `ComprovacioPanel.jsx`/`CheckMeasureEditor.jsx` (forma llarga ja) confirmats fora del diff.

**Verd:** `npm run build` net · eslint 0 errors (cap warning nou al rang tocat) ·
`node --test taulesQ8.test.js` 26/26 · verificador VERD · guardia-i18n VERD (clau retirada als 3
idiomes, sense òrfena) · guardia-ui VERD (mesura pròpia confirma 2 línies a 26mm; **matís no
vetable: ajust exacte 11/11 caràcters a la 2a línia, sense marge — qualsevol etiqueta futura de
`veredictes_fitting` més llarga tornaria a trencar**) · revisor-diff VERD (via única
pantalla/PDF confirmada per comentari `:5852-5855`; `norm()` `:922` normalitza bé tant l'string
històric d'un `.ftt` ja desat com l'objecte nou, Llei F5 respectada; ample de taula molt per
sota d'`AMPLE_UTIL_MAX`).

**Nota del revisor-diff (no bloquejant):** `docs/diagnosis/DIAGNOSI_STAGING_NOMENCLATURA_CORPUS_FITXA.md:143`
descriu l'estat vell d'aquesta cel·la (forma curta, 22mm) i segueix a l'arrel com a vigent.
Aquest sprint la supera parcialment (només la part del veredicte). Pendent de sessió futura si
cal segellar-la o anotar-hi la superació parcial.

---

## S1.3 · Taules sota la capçalera — Commit C (`f57d48b1`)

**Canvi** (`frontend/src/pages/TechSheetEditor.jsx`, `inserirGrupPaginat`):
- `fmtKeyPag`/`hdrProto` es resolen ara ABANS del repartiment (abans es resolien després, només
  calien per a `novaPagina`).
- `primeraPaginaTeCapcalera`: si el grup obre un full nou (`fmtKeyGrup` truthy, `pagBase` encara
  no existeix) → `!!hdrProto` (mateix predicat que `novaPagina` farà servir per a aquell full);
  si el grup arrenca al full on som → mira directament `objectsOf(currentPage)`.
- `Y_INICI`: amb capçalera → `masterHeaderGeomFor(fmtKeyPag||pageFormat).y + .height + 6`
  (`6` = `separacio` per defecte, ja existent a `repartimentTaules.js:45` — cap constant
  nova); sense capçalera → `14`, exactament com abans.
- `yFinal` (`fmtGrup.h - MARGE`) **no s'ha tocat**: l'alçada disponible ja queda descomptada de
  la capçalera com a efecte de pujar `Y_INICI`, no calia cap segon canvi.

**Mesura pròpia del guardia-ui** (geometria, no CSS — no hi ha maqueta d'aquesta lògica):

| format | `header.y` | `header.height` | `Y_INICI` amb capçalera | `yFinal` | espai net |
|---|---|---|---|---|---|
| A4 apaïsat (A4L) | 13.76mm | 24.84mm | 44.60mm | 200mm | 155.4mm |
| A4 vertical (A4P) | 13.76mm | 32.74mm | 52.50mm | 287mm | 234.5mm |

Marge folgat als dos formats (una fila de taula ocupa pocs mm). `fmtKeyPag`/`fmtGrup` verificats
coherents entre si (mateixa cadena de resolució de format als dos càlculs).

**Verd:** `npm run build` net · eslint 0 errors (cap warning nou al rang tocat) ·
`node --test repartimentTaules.test.js` 25/25 + `taulesQ8.test.js` 26/26 (mòdul pur no tocat) ·
verificador VERD · guardia-ui VERD.

**🚩 revisor-diff: BANDERA (no bloquejant per aquesta peça, però cal decisió del CTO).**
Troballa addicional als 5 punts demanats: si el grup arrenca a `currentPage` SENSE capçalera
però `hdrProto` sí que en troba una a una altra pàgina del document (patró suportat:
`deleteHeaderOnPage`), i el mateix grup desborda a ≥2 pàgines DINS d'una mateixa crida, la(es)
pàgina(es) nova(es) neix(en) amb capçalera (via `hdrProto`, igual que `novaPagina` ja fa) però
`Y_INICI` es va calcular a `14` (perquè `currentPage` no en tenia) — xoc visual a la pàgina nova.
**No és una regressió d'aquesta peça** (abans TOTES les pàgines amb capçalera xocaven amb el cos;
ara només aquest cas estret hi xoca), i és una variant més concreta de la limitació ja anotada al
commit (`repartimentEnPagines` pren un `yInici` escalar per a tota la crida). Repro: capçalera
només a pàgina 1, anar a l'última pàgina (sense capçalera), inserir una taula prou alta perquè
`repartimentEnPagines` generi ≥2 trossos en una sola crida.

**💡 PROPOSTA (a validar):** arreglar-ho del tot exigiria que `repartimentEnPagines` accepti un
`yInici` per pàgina (o una funció) en lloc d'un escalar — canvi al mòdul compartit
`repartimentTaules.js`, fora de l'abast de «canvi mínim» d'aquesta peça. Alternativa més barata:
que `primeraPaginaTeCapcalera` (cas `!fmtKeyGrup`) tingui en compte `hdrProto` a més de
`currentPage` — però regressiona el cas normal (grup que cap sencer a `currentPage` sense
capçalera pròpia però amb `hdrProto` d'una altra pàgina: perdria ~30-40mm sense necessitat).
Cap de les dues s'ha aplicat; s'espera decisió.

---

## S1.3-bis · `yInici` per pàgina a la paginació de taules — Commit D (`701245d2`)

Decisió CTO sobre la BANDERA de S1.3: **proposta 1 adoptada** (`yInici` per pàgina).
Proposta 2 (`hdrProto` dins de `primeraPaginaTeCapcalera`) **descartada**.

**Canvi:**
- `frontend/src/utils/repartimentTaules.js:45-58` (`repartimentEnPagines`) — nou helper intern
  `yDeInici(pi) = typeof yInici === 'function' ? yInici(pi) : yInici`; els 3 usos directes de
  `yInici` dins la funció (inicialització i els dos punts de salt de pàgina, `nFiles===0` i el
  bucle de files) passen per aquest helper. Amb `yInici` numèric el comportament és idèntic al
  d'abans (test de compatibilitat, més avall). JSDoc actualitzat (`:36-44`).
- `frontend/src/pages/TechSheetEditor.jsx:5155-5181` (`inserirGrupPaginat`) — `fmtKeyPag`/
  `hdrProto`/`primeraPaginaTeCapcalera` es mantenen (calculats abans del repartiment, com a
  S1.3). `Y_INICI` deixa de ser un valor i passa a ser `(pagina) => (pagina===0 ?
  primeraPaginaTeCapcalera : !!hdrProto) ? yAmbCapcalera() : 14` — la pàgina 0 segueix la regla
  ja existent; les pàgines que la PAGINACIÓ crea dins la mateixa crida (`pagina>=1`) usen
  `!!hdrProto`, el mateix predicat literal que `novaPagina` (`:5217-5221`) fa servir de veritat
  per decidir si hi posa capçalera — mai poden divergir perquè totes dues lligen el mateix
  `hdrProto`, capturat una sola vegada abans del repartiment.
- `:5203` — la crida a `repartimentEnPagines` no canvia de forma (`{ yInici: Y_INICI, yFinal:
  fmtGrup.h - MARGE }`), només el tipus del valor que `Y_INICI` conté ara.

**Tests nous** (`frontend/src/utils/repartimentTaules.test.js`, 25→28):
1. *`yInici escalar dona el mateix resultat que abans (compatibilitat)`* — `repartimentEnPagines`
   amb número i amb una funció que sempre torna el mateix número produeixen `deepEqual`.
2. *`yInici com a funció: pàgina 0 a 14, pàgines següents a 44.6`* — confirma capacitat per
   pàgina (51 files pàgina 0, 44 files pàgines amb capçalera) i que cap fila es perd ni es
   repeteix.
3. *`repro del revisor-diff: capçalera només a la pàgina de desbordament, no a la primera`* —
   reprodueix l'escenari exacte que el revisor-diff va descriure al commit anterior i assegura
   `p1[0].y === 44.6` (no `14`) i `p1[0].y > 38.6` (per sota d'on acaba la capçalera real,
   `header.y+header.height` a A4 apaïsat).

**Verd:** `npm run build` net · eslint 0 errors (cap warning nou) ·
`node --test repartimentTaules.test.js` 28/28 · `node --test taulesQ8.test.js` 26/26 ·
verificador VERD (helper `yDeInici` substitueix els 3 usos directes de `yInici`, sense cap-ne
oblidat; compatibilitat escalar confirmada pel test 1) · guardia-ui VERD (predicat de `Y_INICI`
per a `pagina>=1` coincideix literalment amb el de `novaPagina`; geometria idèntica a S1.3, `6`/
`14`/`44.6`/`52.5` ja existien, només en canvia el moment d'aplicació) · revisor-diff VERD
(**la BANDERA de S1.3 queda tancada**: confirmat que `pagina` dins `repartimentEnPagines` és
relatiu a cada crida, `let pagina = 0` per repartiment, consistent amb l'assumpció de
`Y_INICI`; únic cridant de producció és `inserirGrupPaginat`; forma de l'objecte retornat
`{taula,ini,fi,pagina,y}` intacta; els 3 tests nous no són tautològics — la versió anterior del
mòdul tractava `yInici` sempre com a escalar i no hauria reproduït mai `y=44.6` a la pàgina de
desbordament).

**Cap bandera nova.** Punt obert de S1.3 tancat.

---

## Fitxer:línia de cada canvi (resum)

| Peça | Fitxer | Línies |
|---|---|---|
| S1.1 | `backend/fhort/models_app/services_fitxers.py` | `285-288` (`_es_svg`), `358-362` (`save_model_file`) |
| S1.1 | `backend/fhort/models_app/management/commands/reclassifica_svg_croquis.py` | nou fitxer |
| S1.1 | `backend/fhort/models_app/test_svg_es_croquis.py` | nou fitxer |
| S1.2 | `frontend/src/pages/TechSheetEditor.jsx` | `5545` (width), `5548-5555` (cel·la), nota retirada |
| S1.2 | `frontend/src/i18n/{ca,en,es}.json` | clau `q8_nota_no_ok` retirada |
| S1.3 | `frontend/src/pages/TechSheetEditor.jsx` | `~5138-5230` (`inserirGrupPaginat`) |
| S1.3-bis | `frontend/src/utils/repartimentTaules.js` | `45-58` (`repartimentEnPagines`, helper `yDeInici`) |
| S1.3-bis | `frontend/src/utils/repartimentTaules.test.js` | 3 tests nous, secció «S1.3-bis» |
| S1.3-bis | `frontend/src/pages/TechSheetEditor.jsx` | `5155-5181` (`Y_INICI` com a funció) |

## Punts oberts per al CTO

1. ~~🚩 S1.3 — BANDERA del revisor-diff~~ **TANCAT per S1.3-bis** (`701245d2`).
2. **4.1 (S1.1), obert des de la diagnosi**: no s'ha localitzat amb certesa el punt exacte on el
   panell puja el croquis amb `tipus='SKETCH_SVG'` explícit des del canvas (si n'hi ha cap) —
   irrellevant ara (el defecte nou el cobreix igualment), però queda com a nota per a qui toqui
   aquest flux.
3. **S1.2**: l'ajust a 26mm és exacte (11/11 car.) sense marge de seguretat per a una etiqueta
   `veredictes_fitting` futura més llarga que "NO OK, FOLLOW SPEC" — anotació per a qui toqui
   aquest vocabulari.
4. **`DIAGNOSI_STAGING_NOMENCLATURA_CORPUS_FITXA.md`**: parcialment superada per S1.2 (bloc del
   veredicte); no s'ha segellat ni mogut a `arxiu/` (fora d'abast d'aquest sprint).

## Què ha de fer el CTO

- Revisar la cadena de 4 commits (`git show <sha>` cadascun).
- Fer el push des de SSH quan doni el vistiplau (aquesta sessió no ha fet cap push).
