# DIAGNOSI — El desat de la fitxa acumula versions (.ftt)

Data: **2026-08-02** · **FASE A · Patró A (READ-ONLY ABSOLUT)** · staging `/var/www/ftt-staging`, branca `dev`
HEAD: `277cb9e0d96f440a92e6b36e2dfcfe16809c5206`
BD: `ftt_staging` @5433 · Contrast PROD: `/srv/fhort-prod-backups/incoming/fhort_textile_20260801_023001.dump`
(llegit amb `pg_restore -a`, cap restauració; cal el binari de PG **18**).

**Convenció:** cada afirmació amb `fitxer:línia` verificat. **«NO EXISTEIX» = confirmat absent al codi.**
**Cap proposta de fix en aquesta fase** (§Fase B queda per decidir). Escriptura: només aquest document.

---

## RESUM EXECUTIU

1. **L'origen és UN sol punt:** `FttDocumentDetailView.patch` → `save_document()` → `save_model_file()`.
   Cada PATCH encadena una versió NOVA amb el **blob sencer** re-empaquetat. `save_document`
   (`services_ftt_document.py:519-524`) no té **cap** condició: sempre crida `save_model_file`.

2. **El ritme el marca l'autosave del frontend: debounce de 2 s sobre `[pages, locked, pageFormat, docLang]`**
   (`TechSheetEditor.jsx:3501-3540`). **Qualsevol** mutació de `pages` — moure un objecte, teclejar en una
   cel·la, canviar d'idioma — dispara un desat 2 s després. **Mediana real entre versions consecutives a
   staging: 8,2 segons.**

3. **🔴 LA TROBALLA QUE DECIDEIX LA FASE B: el `checksum` d'avui NO POT REPETIR-SE MAI.** El `.ftt` és un ZIP i
   `zipfile.writestr` hi estampa la **data-hora actual** a cada entrada (`services_ftt.py:88-97`). Amb el
   debounce de 2 s i la granularitat de 2 s del format ZIP, dos desats seguits **sempre** donen bytes
   diferents. Verificat empíricament i confirmat a les dades: **604 de 604 checksums distints a staging** i
   **3.603 de 3.606 a PROD**. 👉 **Un fix «B1» que compari `ModelFitxer.checksum` seria INERT: no hauria
   evitat ni una sola de les 3.566 versions mortes de PROD.**

4. **La comparació SÍ és possible, i la matèria primera ja existeix:** el manifest del `.ftt` ja porta un
   `checksums` amb el sha256 de `document.json` i de **cada** asset (`services_ftt.py:73-85`). Aquest sí és
   estable i és **el mateix per a contingut lògic idèntic**.

5. **NO EXISTEIX cap poda, cap límit, cap retenció.** Ni al codi, ni en cap management command, ni a cron, ni
   a cap systemd timer. `audit_fitxers` és **read-only** per la seva pròpia declaració
   (`models_app/management/commands/audit_fitxers.py:114`).

6. **L'historial de versions ÉS volgut per disseny** — l'acta és explícita a `services_ftt_document.py:8-9`:
   «El "Desa" de l'editor = una versió nova encadenada … **no una sobreescriptura**». El que **no** és volgut
   és que l'autosave hi entri: el mecanisme es va dissenyar per al **desat**, i qui l'alimenta és un
   **autodesat cada 8 segons**.

**La magnitud a PROD (01/08, abans del sanejament):**

| | valor |
|---|---|
| Files `ModelFitxer` a `fhort` | **3.813** |
| …de tipus `TECHSHEET` | **3.606** (94,6 %) |
| …amb `is_current=True` | **40** |
| **Versions mortes** | **3.566 (98,9 %)** |
| Pes total dels TECHSHEET | **15,6 GB** · mitjana **4,4 MB** |
| Model amb més versions | **205 → 495 versions, 3.142 MB** |
| Top 5 | 205 (495) · 163 (390) · 1185 (372) · 182 (364) · 1186 (298) |

---

## A1 · Tots els punts que creen `models_app_modelfitxer` amb un `.ftt`

### A1.0 · L'escriptor únic de la cadena
`services_fitxers.save_model_file` (`models_app/services_fitxers.py:271-317`). Declarat com a font única:
«És l'**ÚNIC** punt que escriu `is_current`/`versio` en una pujada» (`:280-281`). Sempre fa `INSERT`
(`ModelFitxer(...)` a `:296` + `fitxer.save()` a `:311`) i **mai** un `UPDATE` de bytes:

```python
294:        versio = 1
296:    fitxer = ModelFitxer( ... versio=versio, is_current=True, versio_anterior=versio_anterior,
305:                          checksum=checksum, ... )
310:    fitxer.fitxer.save(nom_fitxer, file, save=False)
311:    fitxer.save()
313:    if versio_anterior is not None and versio_anterior.is_current:
314:        versio_anterior.is_current = False
```

### A1.1 · Cens dels punts que hi criden amb un `.ftt`

| # | Punt d'entrada | Fitxer:línia | Crea .ftt? | Disparador |
|---|---|---|---|---|
| **1** | **`save_document()`** | **`services_ftt_document.py:495-524`** | **SÍ — el churn** | **autosave de l'editor (PATCH)** |
| 2 | `create_document()` | `services_ftt_document.py:439-467` | SÍ (v1, cadena nova) | acte humà: botó «nova fitxa» |
| 3 | `save_export()` | `services_ftt_document.py:527-544` | NO (.pdf, cadena pròpia) | acte humà: botó Export PDF |
| 4 | `ItemFitxerViewSet.usar_al_model` | `item_fitxer_views.py:126-184` | SÍ (còpia catàleg→model) | acte humà |
| 5 | `ModelFitxerViewSet.usar_al_model` | `views.py:345-397` | SÍ (còpia model→model) | acte humà |
| 6 | `copiar_de_model_view` | `views.py:1353, 1503` | SÍ (SKETCH*/PATRO; **DOCUMENT exclòs**, `views.py:1275`) | acte humà |
| 7 | Import guiat W5 → `tipus='DOCUMENT'` | `extraction_views.py:2778-2790` | NO (PDF d'origen) | acte humà: import |
| 8 | `federation_service` (bessó) | `federation_service.py:689, 829` | SÍ (còpia federada) | acte humà: enviament de feina |
| 9 | `FttSaveAsTemplateView` | `ftt_document_views.py:309-342` | NO (escriu `DocumentTemplate`, **no** `ModelFitxer`) | acte humà |
| 10 | `FttImageUploadView` | `ftt_document_views.py:96-150` | **NO — i és a posta** | col·locar una imatge |

**El punt 10 mereix nota:** ja porta l'acta del problema escrita al seu docstring
(`ftt_document_views.py:104-109`): «Escriure-hi ara voldria dir encadenar una versió nova per cada foto
col·locada — **justament el churn que patim**». O sigui: **el churn ja estava identificat i es va mitigar per
a les imatges, però no per al desat en si**.

**Conclusió A1:** dels 10 punts, **9 són actes humans discrets** (un clic = un fitxer, comportament correcte).
**El punt 1 és l'únic automàtic** i és el 94,6 % de les files a PROD.

---

## A2 · Quan es dispara cadascun · quants desats genera una sessió

### A2.1 · La cadena del desat, extrem a extrem

```
TechSheetEditor.jsx:3502   useEffect([pages, locked, pageFormat, docLang])
        ↓ debounce 2000 ms  (:3508, :3538)
TechSheetEditor.jsx:3523   PATCH /api/v1/ftt-documents/<head>/
        ↓
ftt_document_views.py:213  FttDocumentDetailView.patch
        ↓ (guards: is_current :215 · lock :220 · document_json present :226)
services_ftt_document.py:495  save_document(head, document_json, ...)
        ↓ load_document(head) :508  → fusiona assets :509-512 → pack() :518
services_fitxers.py:271    save_model_file(..., versio_anterior=head)
        ↓ INSERT ModelFitxer + escriptura del blob sencer a disc
```

**Els tres guards del PATCH no filtren res del churn:** `is_current` (sempre cert, el client reapunta
`fttHeadId` al nou cap, `TechSheetEditor.jsx:3529`), el lock (l'editor el té tota la sessió) i la presència de
`document_json` (sempre hi és). **NO EXISTEIX cap guard de contingut.**

### A2.2 · Què fa disparar l'autosave

L'efecte depèn de `pages`, i **tota** mutació passa per `updatePageObjects`
(`TechSheetEditor.jsx:2704-2706`), que fa `setPages(ps => ps.map(...))` → **sempre una identitat d'array nova,
tingui o no canvi real de contingut**.

| Gest | Node | Dispara? |
|---|---|---|
| Arrossegar un objecte (**per frame**) | `handleDragMove` `:3885-3897` | **NO** — muta el node Konva directament, sense `setPages` |
| Arrossegar un objecte (**en deixar-lo**) | `handleDragEnd` `:3898-3912` → `updateObject` | **SÍ** — 1 versió per gest |
| Redimensionar / rotar | `handleTransformEnd` `:3965` | SÍ |
| Teclejar en una cel·la de taula | `onChange` → `updateObject` `:7505`, `:7514` | SÍ, **per pulsació** (coalescides pel debounce: 1 versió per pausa de 2 s) |
| Editar un text del llenç | `commitTextEdit` `:4355`, `onBlur` `:7039` | SÍ, en confirmar |
| Moure X/Y pel panell de propietats | `:7269`, `:7274` | SÍ, per pulsació |
| Canviar l'idioma del document | dependència `docLang` `:3540` | SÍ |
| Canviar el format de pàgina | dependència `pageFormat` `:3540` | SÍ |
| Col·locar una imatge | `:4416-4441` | SÍ (i els bytes hi viatgen un sol cop, `:3516-3518`) |

👉 **El debounce SÍ coalesceix el teclejat continu** (`clearTimeout` a `:3507` abans de re-armar). El que no
coalesceix és el **ritme natural de treball**: cada pausa de més de 2 s entre gestos = una versió.

### A2.3 · Quants desats genera una sessió normal — MESURAT

Deltes entre versions consecutives de la mateixa cadena, staging `fhort`, 586 parells:

| < 10 s | 10 s – 1 min | 1 – 10 min | > 10 min | **mediana** |
|---|---|---|---|---|
| **321** (55 %) | 164 (28 %) | 44 | 57 | **8,2 s** |

**83 % dels desats van a menys d'un minut del següent.** A raó d'una versió cada ~8 s i **4,4 MB de mitjana**
(PROD), una hora d'edició continuada són **~450 versions ≈ 2 GB**. Els 75 G de PROD són ~35 hores d'edició
acumulades.

Versions per dia a staging (pic): **2026-07-21 → 112 versions / 627 MB en un sol dia**;
2026-07-26 → 122 versions; 2026-07-19 → 87.

### A2.4 · L'obertura també encadena versions

Hi ha **tres** mutacions de `pages` que passen just després de carregar el document, i el guard
`skipSave` és de **UN SOL ÚS** (`skipSave.current = false` al primer consum, `:3504`):

- `:3479` — re-derivació del text de les cotes vives (`skipSave.current = true`).
- `:3497` — auto-col·locació de l'etiqueta de cota (`skipSave.current = true`).
- `:3420-3422` — `convertLegacySketchSvgs(...).then(...)` fa un **segon `setPages` asíncron** que
  **NO re-arma `skipSave`**.

Amb dues d'aquestes mutacions encadenades, la primera consumeix el flag i **la segona desa**. Coincideix amb
l'observació ja registrada a la memòria del projecte (`ftt-ftt-version-churn`: «obrir la fitxa encadena una
versió nova cada cop»). ⚠️ Ho declaro com a **estructura llegida al codi**, no com a repro executada: no he
obert cap navegador en aquesta fase.

---

## A3 · El disseny de versions: volgut o efecte secundari?

### A3.1 · Què fa avui cada camp

`models_app/models.py:414-427`:

| Camp | Línia | Comportament real |
|---|---|---|
| `versio` | `:418` | `PositiveIntegerField(default=1)`; a `save_model_file:290` → `pred.versio + 1` |
| `is_current` | `:420` | «Invariant: **exactament un `is_current=True` per cadena** `versio_anterior` (el cap)» (`:419`). El predecessor es baixa a False a `services_fitxers.py:313-315` |
| `versio_anterior` | `:421-427` | FK a `self`, **`on_delete=SET_NULL`** |
| `generat_des_de` | `:431-437` | Enllaç, **no cadena** (el PDF d'export) |
| `checksum` | `:487` | `CharField(64)`, escrit a `save_model_file:305`. **Mai llegit per decidir res** (§A4) |

**Nota per a la Fase B:** `versio_anterior` és **`SET_NULL` a l'ORM**. La FK real a BD s'ha de comprovar
(el sanejament de PROD d'avui va necessitar deslligar abans d'esborrar, cosa que apunta a `NO ACTION` a la
BD). **Ho deixo com a punt a verificar abans de tocar res**, no verificat en aquesta fase.

### A3.2 · Volgut o no?

**L'historial és VOLGUT i està documentat.** Acta literal a `services_ftt_document.py:8-9`:

> «El "Desa" de l'editor = una versió nova encadenada (nou cap de cadena `is_current=True`, predecessor a
> `is_current=False`), **no una sobreescriptura**.»

I `services_fitxers.py:274-282` descriu la invariant de cadena com a contracte deliberat, amb
`document_root()` (`services_ftt_document.py:28-33`) recorrent la cadena fins a la v1 per identificar el
**document lògic** — que és el que fa servir el lock. O sigui: **la cadena és infraestructura d'identitat, no
runa**.

**El que NO és volgut és qui l'alimenta.** El disseny parla del **«Desa» de l'editor** (un acte); qui hi
entra realment és un **autodesat cada 8 segons**. La prova que la distinció ja era coneguda: el docstring de
`FttImageUploadView` (`ftt_document_views.py:104-109`) l'anomena pel seu nom — «justament el churn que
patim» — i evita escriure per no encadenar versions.

**Veredicte A3: historial VOLGUT + poda INEXISTENT + autodesat que hi entra com si fos un desat humà.**
Són tres coses distintes i només la primera és per disseny.

### A3.3 · Hi ha CAP poda o límit avui? — **NO EXISTEIX**

Confirmat per quatre vies independents:

1. **Cap constant de retenció.** `grep -rni "prune|purge|retenci|MAX_VERSIONS|keep_last|cleanup"` sobre
   `models_app/` → cap resultat sobre fitxers (només poda de *mesures*, un domini diferent).
2. **Cap esborrat automàtic.** Els únics `delete()` sobre fitxers són `perform_destroy` dels dos ViewSets
   (`item_fitxer_views.py:53-55` i el germà de `ModelFitxerViewSet`), tots dos **accionats per l'usuari**.
3. **`audit_fitxers` és read-only** — `models_app/management/commands/audit_fitxers.py:114`: «Auditoria
   **read-only** de ModelFitxer: invariant de cadena + reconciliació disc↔BD.» Cap `.save()`, cap `.delete()`.
4. **Cap cron, cap systemd timer.** `crontab -l` buit; `systemctl list-timers` sense cap entrada de FTT.

També ho diu el codi de la fusió d'assets, per al problema germà de dins del zip:
«`save_document` **fusiona i no poda mai**» — repetit a `ftt_document_views.py:72`, `services_ftt.py:132` i
`test_ftt_asset_embut.py:56`.

---

## A4 · 🔴 Hi ha comparació de checksum abans de crear?

### A4.1 · Resposta curta: NO. I si n'hi hagués, **amb el checksum d'avui no serviria de res**.

**(a) No hi ha comparació.** `save_model_file` **calcula** el checksum (`services_fitxers.py:285`) i el
**desa** (`:305`), però **no el llegeix mai per decidir**. `save_document` (`services_ftt_document.py:495-524`)
crida `save_model_file` incondicionalment: entre la línia 507 i la 524 no hi ha ni un `if`.

**(b) I aquí ve el que decideix la Fase B.** El `.ftt` és un ZIP construït amb `zipfile.writestr`
(`services_ftt.py:88-97`). Quan se li passa un **nom** (i no un `ZipInfo`), la stdlib crea el `ZipInfo` amb
`date_time = time.localtime()` → **el blob incorpora la data-hora del moment d'empaquetar**.

Verificat empíricament (stdlib pura, cap fitxer del repo tocat):

```
mateix contingut, 1,2 s de separació  → bytes IDÈNTICS   (ZIP té granularitat de 2 s)
mateix contingut, 3,5 s de separació  → bytes DIFERENTS
   dt A (2026, 8, 2, 8, 44, 58)   sha 8df84dbc…
   dt C (2026, 8, 2, 8, 45,  2)   sha 3c1e1e95…
```

Com que l'autosave té un debounce de **2 s** i la mediana real entre desats és de **8,2 s**, dos desats
consecutius cauen **sempre** en finestres de 2 s diferents. **El checksum no pot repetir-se.**

**(c) Les dades ho confirmen a les dues bandes:**

| | staging `fhort` | PROD `fhort` (01/08) |
|---|---|---|
| Files TECHSHEET | 604 | 3.606 |
| **Checksums distints** | **604 (100 %)** | **3.603 (99,9 %)** |
| Versions encadenades amb `checksum == checksum(predecessor)` | **0 de 581** | — |

👉 **Un fix que compari `ModelFitxer.checksum` amb el de la versió vigent hauria evitat 0 versions.**

### A4.2 · La comparació correcta ja té la matèria primera al lloc

`services_ftt.pack` **ja construeix** un mapa de checksums lògics abans de comprimir
(`services_ftt.py:73-85`):

```python
73:    checksums = {DOCUMENT_NAME: _sha256(document_bytes)}
74:    for name, data in assets.items():
75:        checksums[ASSETS_PREFIX + name] = _sha256(data)
79:    manifest = { "magic": ..., "kind": kind, "checksums": checksums }
```

I `document_bytes` es genera **de forma determinista**: `json.dumps(..., sort_keys=True,
separators=(",",":"))` (`services_ftt.py:69-71`). O sigui: **contingut lògic idèntic → `checksums` idèntic**,
sempre, sense dependre del rellotge. El `kind` també hi és, de manera que el mode plantilla no s'escaparia.

**Fet, no proposta:** aquesta empremta és llegible tant del blob nou (via `pack`) com de la versió vigent
(via `unpack`, que retorna el `manifest`, `services_ftt.py:276-292`).

---

## A5 · Frontend: en quins events es dispara el desat

Ja detallat a §A2.2. Resum del node únic — `TechSheetEditor.jsx:3501-3540`:

- **Un sol autosave, per `useEffect`**, amb `setTimeout` de **2000 ms** (`:3508`, `:3538`) i `clearTimeout`
  previ (`:3507`).
- **Dependències:** `[pages, locked, pageFormat, docLang]` (`:3540`).
- **NO hi ha `onBlur` global, ni interval periòdic de desat, ni desat en tancar.** L'únic `setInterval` del
  fitxer és el **heartbeat del lock** cada 10 min (`:3377-3381`), que **no desa** (fa `renew_lock`), i el
  `beforeunload` (`:3396-3401`) només **allibera el lock**.
- **Guards existents:** `docCarregat.current` (`:3503`, evita desar un full en blanc abans de carregar),
  `skipSave.current` (`:3504`, un sol ús) i `locked` (`:3505`).
- **La capçalera de l'arxiu ja ho declara** (`TechSheetEditor.jsx:38`): «Autosave (debounce 2s, només amb
  lock)».

**El que NO hi ha:** cap comparació del `document_json` serialitzat contra l'últim desat. El client **ja
calcula** `docSerialitzat = JSON.stringify(documentJson)` a `:3520` — però només per netejar els assets
pendents (`:3533-3535`), mai per decidir si val la pena desar.

---

## REGISTRE DE NODES

| Fitxer:línia | Tipus | Paper en el vessament | Risc |
|---|---|---|---|
| `services_ftt_document.py:519-524` | servei | **L'ORIGEN**: crida `save_model_file` sense cap condició | 🔴 |
| `services_fitxers.py:271-317` | servei | escriptor únic de la cadena; calcula el checksum i **no el compara** (`:285`, `:305`) | 🔴 |
| `services_ftt.py:88-97` | servei | `writestr` estampa la data-hora → **el checksum del blob no pot repetir-se** | 🔴 |
| `services_ftt.py:69-85` | servei | `document_bytes` determinista + `manifest['checksums']` = **empremta lògica estable** | 🟢 |
| `TechSheetEditor.jsx:3501-3540` | frontend | autosave debounce 2 s sobre `[pages, locked, pageFormat, docLang]` | 🔴 |
| `TechSheetEditor.jsx:2704-2706` | frontend | `updatePageObjects` sempre crea identitat nova (dispara encara que el contingut no canviï) | 🟡 |
| `TechSheetEditor.jsx:3504` | frontend | `skipSave` és d'**un sol ús** → la segona mutació d'obertura sí desa | 🟡 |
| `TechSheetEditor.jsx:3420-3422` | frontend | `setPages` asíncron que **no re-arma** `skipSave` | 🟡 |
| `TechSheetEditor.jsx:7505,7514` | frontend | `onChange` per pulsació a les cel·les de taula | 🟡 |
| `ftt_document_views.py:213-246` | vista | 3 guards, **cap de contingut** | 🔴 |
| `models_app/models.py:418-427` | model | `versio` / `is_current` / `versio_anterior` (SET_NULL a l'ORM) | 🟡 |
| `models_app/models.py:487` | model | `checksum` — escrit, **mai llegit** | 🔴 |
| `ftt_document_views.py:104-109` | vista | **el churn ja estava diagnosticat** i mitigat només per a les imatges | 🟢 |
| `services_ftt_document.py:8-9` | acta | l'historial és **volgut**: «no una sobreescriptura» | 🟢 |
| `audit_fitxers.py:114` | comanda | auditoria **read-only** — l'única eina existent, i no poda | 🟢 |
| **poda / retenció / cron** | — | **NO EXISTEIX** | 🔴 |

---

## LÍMITS DECLARATS

1. **No he obert cap navegador.** El comportament de §A2.4 (versió en obrir) és **lectura d'estructura del
   codi**, no repro executada. La cadència de §A2.3 **sí** és mesura real (deltes de `data_pujada` a la BD).
2. **La FK `versio_anterior_id` a nivell de BD no l'he verificada.** A l'ORM és `SET_NULL`
   (`models.py:423`); el sanejament de PROD d'avui suggereix `NO ACTION` a la BD. **Cal comprovar-ho abans de
   qualsevol poda.**
3. **Els recomptes de PROD surten del dump del 01/08** (anterior al sanejament d'avui), comptant línies del
   bloc `COPY` amb `awk` sobre la columna `tipus`. Fiable per a aquestes columnes; un `descripcio` multi-línia
   podria desquadrar alguna fila aïllada.
4. **No he mirat `los` en detall** (11 files de `ModelFitxer` a PROD, cap TECHSHEET rellevant).
5. **No he tocat el tram instància** ni cap fitxer del repo. `git status` només mostra aquest document nou.

---

## STOP — DECISIÓ D'AGUS PER A LA FASE B

Reporto el que la diagnosi obliga a saber abans de triar:

**Sobre B1 (desat idempotent per checksum)** — la idea és bona però **la implementació literal és inert**:
comparar `ModelFitxer.checksum` no hauria evitat cap de les 3.566 versions mortes, perquè el ZIP hi estampa
l'hora. Perquè B1 funcioni ha de comparar l'**empremta lògica** (`manifest['checksums']`, que ja existeix i ja
és determinista), no els bytes del blob. **I aleshores tampoc resol el gruix del problema**: la mediana de 8,2 s
entre desats no són desats en va — són desats amb **canvi real** (moure, teclejar, col·locar). B1 tallaria la
cua de no-ops (obertura, `skipSave` consumit, gestos nuls), no el riu.

**Sobre B2 (poda a N)** — és **l'únic que ataca el volum de debò**: amb 495 versions i només 1 viva, qualsevol
N raonable elimina el 98 % del pes. Requereix la comprovació de la FK del punt 2 dels límits.

**Sobre B3 (frontend: no desar sense canvi real / debounce)** — el client **ja calcula** el JSON serialitzat
(`:3520`); comparar-lo amb l'últim desat és barat. Allargar el debounce redueix la freqüència però no el
creixement il·limitat.

**La meva lectura, per si ajuda a decidir** (no és una proposta de codi, és el que diuen els números):
el vessament és **volum × freqüència sense sostre**. B1 i B3 baixen la freqüència; **només B2 posa sostre**.
Si el deploy de dilluns ha de garantir que el disc no torni a omplir-se, **B2 hi ha de ser**; B1+B3 sols
alentirien el rellotge sense aturar-lo.

**Espero l'OK i la tria abans de tocar una sola línia.**

---

*Fi de la Fase A. Cap fitxer del repo modificat, cap escriptura a BD, cap commit.*
