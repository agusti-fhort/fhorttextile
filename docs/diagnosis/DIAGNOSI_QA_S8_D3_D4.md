# DIAGNOSI — QA-S8 · D3 (modal del wizard) + D4 (biblioteca de nomenclatura)

> **Data:** 2026-07-13 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`.
> **Abast:** els defectes que QA humà ha trobat a la Biblioteca de nomenclatura del client 7
> (Textiles y Confecciones Brownie SL, `clients/7?tab=tecnic`) i al seu wizard de diccionari.
> **Frontera:** D1 (parser ràpid) i D2 (rectificació) tenen diagnosi pròpia a
> `DIAGNOSI_QA_S8_IMPORT.md` i ja estan fixats (`eb880fd`, `3db0b82`). Aquí NO es toquen.
> **Convenció:** `fitxer:línia` a cada afirmació. `NO EXISTEIX` = confirmat absent al codi,
> no especulat. Els censos de dades porten el `SELECT` literal.

---

## RESUM EXECUTIU

**D3.** El modal NO està trencat pel posicionament: `position: fixed` es resol bé contra el
viewport (**no hi ha cap ancestre amb `transform`/`filter`/`contain`** — l'única hipòtesi que
calia descartar). Està trencat per **capa z**: l'overlay del wizard és `zIndex: 60`
(`DictionaryWizard.jsx:112`) i el **Sidebar és `zIndex: 100`** (`Sidebar.jsx:312`), `position:
fixed`, `left: 0`, **240 px d'ample**. El sidebar es pinta **per sobre** del modal. Com que el
panell fa `min(1100px, 94vw)` **centrat al viewport**, la seva vora esquerra cau sota els 240 px
del sidebar en qualsevol pantalla < ~1580 px ⇒ **"escapçat per l'esquerra"**. I la franja
esquerra de 240 px tampoc no queda enfosquida ⇒ **"sense backdrop"** (percebut).

⚠️ **El backdrop SÍ que existeix al codi** (`rgba(0,0,0,0.4)`, `DictionaryWizard.jsx:112`).
El report de QA descrivia el símptoma, no la causa.

⚠️ **El patró canònic té el MATEIX defecte latent.** `ui/Modal.jsx:12` és `zIndex: 50` — també
per sota del sidebar. No es nota perquè el seu panell fa 460 px i mai no arriba a `x < 240`.
**Migrar el wizard a `ui/Modal.jsx` no arreglaria res**: cal aixecar la capa dels modals.

**D4a.** Els àlies "contaminats" els va sembrar la **migració 0031**, des d'un **dict
hardcodejat** les claus del qual **són descripcions angleses**
(`0031:17-27`), escrites al camp CODI a `0031:53-56` (`client_code=src, client_description=src`).
**Cens: exactament 5 files, totes del client 7.** ⚠️ **NO afecten el matching** (un `client_code`
descriptiu és **intencional i documentat**, `extraction_views.py:527-529`): la contaminació és
**de presentació**, no de motor. I **no tenen res a veure amb els 9 sense-match de D1** — ho
demostro empíricament més avall.

**D4b.** El wizard **SÍ que persisteix la descripció** (`dictionary_views.py:167-168` escriu
`description_en`/`description_local`). **La pèrdua és de LECTURA, no d'escriptura**: el
serialitzador **no exposa els camps nous** (`serializers.py:348-353`) i la taula pinta el camp
**obsolet** `client_description` (`CustomerDetail.jsx:196-197`), que el wizard no escriu mai.
Els 90 àlies d'avui tenen la descripció a BD — el `SELECT` ho prova.

**D4c.** Defecte de **CODI, no de dada**. `DICCIONARI` és un choice legítim del model
(`models.py:245`), però la clau i18n `clients.origen_DICCIONARI` **NO EXISTEIX** als tres
idiomes (només hi ha IMPORT/MANUAL/MIGRACIO, `{ca,en,es}.json:269-271`) i i18next torna la clau
crua.

**D5 (NOU — el CTO l'ha reportat en sessió).** La biblioteca **només llista 25 dels 95 àlies**
del client 7: `PAGE_SIZE = 25` (`settings.py:218`) i la crida **no demana més pàgines**
(`CustomerDetail.jsx:161-162`). El comptador de la capçalera també menteix.
El match per codi canònic `POM-XXX` **ja existeix** (`CustomerDetail.jsx:202`) — el que faltava
eren les files.

---

## D3 — EL MODAL DEL WIZARD

### D3a · Component i mecanisme de posicionament

Component únic: **`frontend/src/components/DictionaryWizard.jsx`**, muntat des de
`CustomerDetail.jsx:252-260` dins de `TecnicTab`, condicionat per `showDict`
(`CustomerDetail.jsx:159`).

```jsx
// DictionaryWizard.jsx:112   — OVERLAY
position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', zIndex: 60,
display: 'flex', justifyContent: 'center', alignItems: 'flex-start',
overflowY: 'auto', padding: '3vh 0'
// DictionaryWizard.jsx:114   — PANELL
width: 'min(1100px, 94vw)', borderRadius: 12, overflow: 'hidden'
```

- **Portal: NO EXISTEIX.** `grep -rn "createPortal" frontend/src` → **zero coincidències a tot
  el codebase**. Tots els modals del projecte es renderitzen inline a l'arbre.
- **Ancestre amb containing block: NO EXISTEIX.** Cadena `DictionaryWizard` → `TecnicTab` →
  `CustomerDetail` → `<Outlet/>` → `Shell`. `Shell.jsx:34-40` té `overflowY: 'auto'` al `<main>`,
  però **`overflow` NO crea containing block per a `position: fixed`** (només ho fan `transform`,
  `filter`, `perspective`, `contain`, `will-change`, `backdrop-filter`). Cap d'aquests apareix a
  `Shell.jsx`, a `CustomerDetail.jsx` ni a `index.css` (l'únic `transform` global és
  `index.css:59`, un `@keyframes spin`).
  ⇒ **La hipòtesi del containing block és FALSA. El `fixed` es resol bé contra el viewport.**

### D3b · La causa real: capa z per sota del Sidebar

```jsx
// Sidebar.jsx:303-315
position: 'fixed', left: 0, width: 240, zIndex: 100,   // ← :312
```

`60 < 100` ⇒ **el Sidebar es pinta per sobre de l'overlay i del panell.**

**Geometria del símptoma.** Panell centrat de `min(1100px, 94vw)` ⇒ vora esquerra a
`(vw − amplada) / 2`. Queda sota els 240 px del sidebar quan:

| viewport | amplada panell | vora esquerra | tapat pel sidebar (240 px) |
|---|---|---|---|
| 1920 | 1100 | 410 | no |
| 1580 | 1100 | 240 | **llindar exacte** |
| 1440 | 1100 | **170** | **sí — 70 px escapçats** |
| 1366 | 1284 (94vw) | **41** | **sí — 199 px escapçats** |

⇒ En qualsevol portàtil (1366/1440) el modal **surt escapçat per l'esquerra**, i la franja de
240 px **no s'enfosqueix** (el sidebar hi és a sobre) ⇒ es percep com a "sense backdrop" i com
si "tapés la pantalla de sota" a mitges. **Coincideix exactament amb el que ha vist QA.**

### D3c · Els dos passos comparteixen contenidor (una sola causa, un sol fix)

Un **únic** wrapper amb contingut condicional: overlay `:112` + panell `:114`, capçalera `:116-124`
i peu `:238-241` compartits; `{step === 'upload' && …}` a `:128` i `{step === 'review' && …}` a
`:143`. ⇒ **El defecte és idèntic als dos passos i es tanca amb un sol fix.**

### D3d · El patró canònic — i per què migrar-hi NO és el fix

**`frontend/src/components/ui/Modal.jsx`** (31 línies) és el modal canònic:

```jsx
// Modal.jsx:10-13
position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.35)',
alignItems: 'center', justifyContent: 'center', zIndex: 50,   // ← :12
// Modal.jsx:14-17 — panell
width: 460, maxWidth: '92vw', maxHeight: '85vh'
```

Dos fets que manen sobre el fix:

1. **També és `zIndex: 50` < 100 ⇒ també per sota del sidebar.** No es nota perquè el panell fa
   460 px: centrat, la vora esquerra només baixaria de 240 px en viewports < 940 px. **És el
   mateix defecte, latent.** Migrar-hi el wizard **heretaria el bug**.
2. **La seva API no encaixa** (`Modal.jsx:8`): `{title, subtitle, children, confirmLabel,
   cancelLabel, onConfirm, onCancel}` — és un **diàleg de confirmació de 460 px** amb peu fix
   Cancel·lar/Acció. El wizard necessita 1100 px, capçalera pròpia, peu propi que canvia entre
   passos i una taula amb scroll intern. **NO EXISTEIX cap component canònic de modal ample.**

⇒ **El fix correcte és la CAPA, no el component**: pujar els modals per sobre del sidebar.

### D3e · Cens d'overlays (per què uns funcionen i altres no)

| zIndex | Fitxers | vs Sidebar (100) |
|---|---|---|
| **50** | `ui/Modal.jsx:12` (canònic) · `App.jsx:139` · `UsersRoles.jsx:325,393,512,617` · `TechSheetEditor.jsx:4345,4365,4423` · `DeliveryNoteDetail.jsx:346,393` · `WorkOrderDetail.jsx:338,382` · `OrderDetail.jsx:244` · `DeliveryNotes.jsx:113` · `GradingRuleSets.jsx:996` · `PropagatedEditor.jsx:63` · `TaskAssignWizard.jsx:213` · `pattern/ExportModal.jsx:98` | ❌ per sota |
| **60** | **`DictionaryWizard.jsx:112`** · `assets/AssetNavigator.jsx:340` | ❌ per sota |
| **200** | `SizeAuthoringDrawer.jsx:17` · `SizeSystem/SizeSystemDrawer.jsx:118` · `model/WatchpointDrawer.jsx:27` | ✅ per sobre |
| **1000** | `model/CheckMeasureEditor.jsx:105` · `model/SessionActions.jsx:18` · `ModelSheet.jsx:1362,1387` | ✅ per sobre |

**Els que funcionen (200/1000) confirmen el diagnòstic per contrast: superen el sidebar.**

### D3f · Altres modals del tab tècnic

**CAP.** `TecnicTab` (`CustomerDetail.jsx:154-306`) només munta `DictionaryWizard`.
`AliasAddRow` (`:308`) és una fila inline amb un dropdown `<ul>` (`:367`), **no és un modal**.

> **Veredicte D3:** causa **continguda i inequívoca** (capa z). Un sol fix per als dos passos.
> El patró canònic comparteix el defecte ⇒ el fix ha d'aixecar **la capa dels modals**, no
> reescriure el wizard.

---

## D4a — ÀLIES AMB DESCRIPCIONS AL CAMP CODI

### D4a·1 · La migració culpable

**`backend/fhort/pom/migrations/0031_migrate_brownie_synonyms_to_aliases.py`**

L'origen de les dades **no és cap camp de cap model**: és un **dict hardcodejat al fitxer**,
`BROWNIE_ALIASES` (`0031:17-27`), **les claus del qual són descripcions angleses**, mogut del
diccionari de sinònims `_POM_SYNONYMS`:

```python
# 0031:17-27
BROWNIE_ALIASES = {
    'collar width':                    'neck tie length',
    'lining bottom width along hem':   'lining bottom',
    ...
}
# 0031:43-56  — L'ASSIGNACIÓ FATAL
for src, tgt in BROWNIE_ALIASES.items():          # ← src = la CLAU = la DESCRIPCIÓ
    pom = POMMaster.objects.filter(
        Q(nom_client__icontains=tgt) | Q(pom_global__nom_en__icontains=tgt)
    ).order_by('id').first()                      # ← :44-46  substring + id més baix
    CustomerPOMAlias.objects.create(
        customer_id=brw.id, pom_id=pom.id,
        client_code=src, client_description=src,  # ← :55  la DESCRIPCIÓ al camp CODI
        origen='MIGRACIO', pendent_revisio=False)
```

**Per què hi va posar la descripció:** el bloc venia de `_POM_SYNONYMS`, un mapa
descripció→descripció. No hi havia cap codi curt disponible, i el disseny **accepta
deliberadament** que el `client_code` pugui ser text descriptiu — ho documenta el matcher:

> `extraction_views.py:527-529` — *"El client_code d'un àlies pot ser un codi posicional (LOS
> 'H.6') O el text de la descripció del client (BRW 'front armhole curve')"*

⇒ **No és un bug accidental del camp codi: és intencional.** El que **sí** és un bug és
(a) la resolució del POM per substring i (b) el buit de descripció que en resulta (§D4a·3).

**La migració 0034 ja va corregir 2 dels casos** (`0034:45-52`): repunta `lining length at
center front` (havia resolt al POM del *center BACK* per `icontains` + `order_by('id').first()`)
i esborra `front armhole curve`. La seva capçalera (`0034:3-9`) **declara l'arrel de l'error de
0031**. La "LLEI" que hi proclama (`0034:9`: *cap re-sembra futura ha de resoldre POMs per
substring*) **NO està aplicada a cap guard de codi** — és només un comentari.

### D4a·2 · Cens de dades (SELECT literal)

```sql
SELECT a.id, a.customer_id, c.nom AS client, a.client_code, a.client_description,
       a.description_en, a.origen, p.codi_client AS pom_codi, a.creat_at::date
FROM fhort.pom_customerpomalias a
  JOIN fhort.tasks_customer c ON c.id = a.customer_id
  JOIN fhort.pom_pommaster  p ON p.id = a.pom_id
WHERE a.origen = 'MIGRACIO' ORDER BY a.id;
```

```
 id | cli |          client_code          |       client_description      | desc_en | pom_codi | creat
----+-----+-------------------------------+-------------------------------+---------+----------+-----------
  2 |  7  | collar width                  | collar width                  |  (buit) | S1-M76   | 2026-07-08
  3 |  7  | body zip length               | body zip length               |  (buit) | ZIP L    | 2026-07-08
  4 |  7  | lining length at center front  | lining length at center front |  (buit) | LF-M76   | 2026-07-08
  5 |  7  | lining length at center back  | lining length at center back  |  (buit) | 1-M76    | 2026-07-08
  6 |  7  | lining bottom width along hem | lining bottom width along hem |  (buit) | F1-M76   | 2026-07-08
  7 |  1  | T.1                           | FRONT RISE                    | FRONT RISE | T.1   | 2026-07-08
  8 |  1  | T.2                           | BACK RISE                     | BACK RISE  | T.2   | 2026-07-08
```

**CENS: exactament 5 àlies contaminats, TOTS del client 7.** Les 2 files restants d'origen
`MIGRACIO` (client 1, de la migració `0032`, codis dotted reals) **són correctes** — el contrast
dona el predicat exacte:

```sql
-- Predicat de contaminació (retorna exactament 5, tots client 7):
SELECT count(*) FROM fhort.pom_customerpomalias
 WHERE client_code = client_description AND client_code LIKE '% %';   -- → 5
```

**Cens de TOTS els clients** (no n'hi ha cap més):

```sql
SELECT customer_id, origen, count(*) FROM fhort.pom_customerpomalias GROUP BY 1,2;
--  1 | MIGRACIO   |  2      ← correctes (0032, codis dotted)
--  7 | MIGRACIO   |  5      ← ELS 5 CONTAMINATS
--  7 | DICCIONARI | 90      ← del wizard, codis reals (EK, EKK, E1, E4…)
```

**Els POMs de destí són CORRECTES** (verificat: el `nom_client` del POM coincideix amb el text
de l'àlies — `Collar Width (Neck Tie Length)`, `Lining Length at Center Front`, …). El desastre
del substring que va motivar 0034 **ja està corregit**. ⇒ **La reparació NO ha de tocar el `pom`.**

### D4a·3 · Per què tenen la descripció BUIDA

La migració `0035` va fer el backfill `client_description → description_en`, **però se salta
explícitament les files on la descripció duplica el codi**:

```python
# 0035:22-23
if cd.lower() == (a.client_code or '').lower():
    continue                                   # ← els 5 de 0031 queden amb description_en = ''
```

⇒ **Per construcció**, els 5 contaminats són els únics àlies del sistema amb `description_en`
buit. Es veuen a la Biblioteca com **"codi llarg de prosa + descripció buida"**. És exactament
el que ha reportat QA.

### D4a·4 · Impacte real sobre el matching: CAP (i no toca els 9 de D1)

`find_pom_master`, branca (a) — `extraction_views.py:544-550`:

```python
for key in (k for k in (code, desc_clean) if k):      # ← :545  codi I descripció
    alias = CustomerPOMAlias.objects.filter(
        customer=customer, client_code__iexact=key).select_related('pom').first()
    if alias and alias.pom.actiu:
        return alias.pom, 'alias_match', 'HIGH'       # ← :550  primera branca, HIGH
```

- **Un `client_code` descriptiu SÍ que fa match**, perquè el bucle compara `client_code` també
  contra `desc_clean` (la descripció del document). **La contaminació no trenca el matcher: el
  fa servir tal com es va dissenyar.**
- **No pot robar un codi curt.** La comparació és `iexact` sobre la cadena sencera: `'collar
  width'` mai no col·lisiona amb `FC`, `FB` o `E3`. (El risc de segrest real és un altre: un
  àlies descriptiu **amb el POM equivocat** guanyaria a `exact_description` perquè la branca (a)
  és la primera i torna `HIGH` — però §D4a·2 confirma que **els 5 POMs de destí són correctes**.)

**PROVA EMPÍRICA — els 5 contaminats NO expliquen els 9 sense-match de D1.** He passat els 10
codis sense-match de D1 per `find_pom_master` amb el catàleg d'avui (lectura pura, cap
escriptura):

```
codi  match_type    conf   POM        codi  match_type    conf   POM
G1    alias_match   HIGH   G1         J     alias_match   HIGH   BIC
E1    alias_match   HIGH   SH         JJ    alias_match   HIGH   JJ
E4    alias_match   HIGH   E4         J1    alias_match   HIGH   SL OP
EP    alias_match   HIGH   EP         I3    alias_match   HIGH   I3
S     alias_match   HIGH   S          S2    alias_match   HIGH   S2
```

**Els 10 resolen ara a `alias_match`/`HIGH`** — gràcies als **90 àlies `DICCIONARI` creats avui
(2026-07-13 06:15) pel mateix wizard que QA estava provant**, no gràcies als 5 contaminats
(que no hi tenen cap relació: apunten a POMs de folre i coll). Vegeu §FRONTERA.

### D4a·5 · CENS AMPLIAT — POMs reclamats per 2+ codis del MATEIX client *(T4a)*

Aquest cens és **independent** de la contaminació de 0031 i **més greu**: són àlies amb el
**codi correcte** però **apuntant al POM equivocat**. Els va sembrar el **wizard del diccionari**
(`origen='DICCIONARI'`), avui.

```sql
SELECT a.pom_id, p.codi_client, p.nom_client, count(*) AS n_codis,
       string_agg(a.client_code||' ['||coalesce(nullif(a.description_en,''),'∅')||']', ', ' ORDER BY a.id)
FROM fhort.pom_customerpomalias a JOIN fhort.pom_pommaster p ON p.id = a.pom_id
WHERE a.customer_id = 7
GROUP BY a.pom_id, p.codi_client, p.nom_client
HAVING count(*) > 1 ORDER BY count(*) DESC;
```

| POM | `nom_client` del POM | codis que el reclamen (amb la seva `description_en`) | Veredicte |
|---|---|---|---|
| **389** | TOTAL LENGTH | `F`[FRONT TOTAL LENGTH] · `FF`[BACK TOTAL LENGTH] · `F3`[FRONT CENTER TOTAL LENGTH] · `F4`[BACK CENTER TOTAL LENGTH] | 🔴 **DOLENT** — **4 mesures distintes** (davant/darrere/centre davant/centre darrere) col·lapsades en un POM genèric |
| **439** | Width sequins piece (CF) | `U`[FRONT OVERLAP] · `U2`[1st BUTTON] · `U3`[LAST BUTTON] | 🔴 **DOLENT** — 3 mesures distintes, i **cap** és "width sequins piece" |
| **441** | Chest piece height at side seam | `P`[CENTER BACK YOKE HEIGHT] · `P2`[CENTER FRONT YOKE HEIGHT] | 🔴 **DOLENT** — davant vs darrere; el POM no és cap de les dues |
| **437** | Centre front length at CF | `F1`[TOTAL SIDE LENGTH] · `F2`[TOTAL SIDE LENGTH] | 🔴 **DOLENT** — descripció **idèntica** en dos codis, i el POM (centre front) **no és** "side length" |
| **275** | Waist width | `B`[WAIST WIDTH] · `B1`[STRETCHED WAIST WIDTH] | 🟠 **DOLENT (lleu)** — `B` és correcte; `B1` (**stretched**) és una mesura distinta sense POM propi |
| **461** | Sleeve slit | `0`[SLIT] · `I3`[CUFF SLIT] | 🔴 **BROSSA** — `client_code = '0'` (id 110) **no és un codi**; `I3` és correcte |
| **341** | Zipper length | `body zip length`[∅] *(MIGRACIO)* · `CR2`[ZIPPER] | 🟢 **LEGÍTIM** — mateixa mesura, dos noms. (El `MIGRACIO` és un dels 5 contaminats de §D4a·2.) |

**Total a reparar: 13 àlies dolents + 1 brossa** (`0`), sobre 6 POMs. Confirmat el que deia el
brief, i **ampliat**: els 4 POMs multi-codi no auditats resulten ser **3 dolents més** (441, 437,
275) **i 1 legítim** (341).

**⚠️ Per què el wizard va sembrar això:** `dictionary_service.py:147` crida `find_pom_master` per
fila i **no comprova que el POM ja estigui reclamat** per una altra fila del mateix full. Amb
`n_match > 1` el marca com a ambigu a la UI (`DictionaryWizard.jsx:194`), però **col·lapsar dues
files distintes sobre un mateix POM no és cap avís**. És **el mateix mode de fallada** que la
`FIX A` va tancar a l'importador de models — **i el diccionari no el té**.

### D4a·6 · La xarxa de seguretat JA HI ÉS (i canvia la urgència)

El commit **`eb880fd` (FIX A, sessió d'importació)** va portar el **guard many-to-one** al camí
d'import **i deliberadament NO exempta l'`alias_match`**:

> *"aquí l'ÀLIES **NO** queda exempt del guard […] el catàleg viu té els àlies BRW 'F' (Centre
> FRONT length) i 'FF' (Centre BACK length) tots dos cap al POM 389 'TOTAL LENGTH', i 'U2'/'U3'
> tots dos cap al 439. Amb l'exempció posada, aquestes quatre files travessaven les dues portes
> amb confiança HIGH i dues mesures del Brownie es perdien."*

⇒ **Avui, en una importació, `F`/`FF`/`F3`/`F4` i `U`/`U2`/`U3` ja NO auto-vinculen**: cauen a
pendents i el tècnic decideix. **La pèrdua silenciosa de mesures està tancada.**

⇒ **La reparació de dades NO és una urgència de pèrdua de dades: és higiene de catàleg.** El que
queda viu és que aquests àlies **suggereixen un POM equivocat amb confiança HIGH** i, si una
importació futura porta **només un** dels codis del grup (p.ex. `F` sense `FF`), **el guard no
salta** (no hi ha col·lisió dins d'aquell document) i **s'auto-vincula al POM equivocat**.
**Aquest és el forat que la reparació tanca.**

> **Veredicte D4a:** dues famílies de defecte, totes dues **contingudes** i **censades**:
> **(1)** 5 àlies amb prosa al camp codi (0031) — dany **de presentació**, POMs correctes;
> **(2)** 13 àlies + 1 brossa amb el codi bo i el **POM equivocat** (wizard del diccionari) —
> dany **de matching**, mitigat per `eb880fd` però no tancat.
> La reparació és **acotada però NO trivial** — vegeu §REPARACIÓ.

---

## D4b — LA DESCRIPCIÓ DEL WIZARD NO ES VEU

### El viatge, salt a salt (i on es trenca DE VERITAT)

| # | Etapa | Fitxer:línia | Porta la descripció? |
|---|---|---|---|
| 1 | Parse de l'Excel | `dictionary_service.py:14` (`COLUMNS`), `:143-145`, `:165-178` | ✅ `descripcio_en`, `descripcio_local`, `idioma` |
| 2 | Resposta del preview | `dictionary_views.py:77-78` (dict literal, sense serialitzador) | ✅ |
| 3 | Estat del pas 2 | `DictionaryWizard.jsx:51-58` (spread `...r`), pintat a `:177-182` | ✅ |
| 4 | Payload de "Desar diccionari" | `DictionaryWizard.jsx:90-98`, concretament **`:93`** | ✅ |
| 5 | Endpoint de desar | `dictionary_views.py:133-135` (llegeix) → **`:163-172`** (escriu) | ✅ **escriu `description_en`/`description_local`/`language`** |
| 6 | **Serialitzador de la llista** | **`serializers.py:348-353`** | ❌ **`Meta.fields` NO inclou els camps nous** |
| 7 | **Taula del frontend** | **`CustomerDetail.jsx:190-197`** | ❌ **pinta `client_description`** |

**⇒ La descripció NO es perd: MAI SURT.** El defecte és **de lectura**, en dos punts encadenats.

```python
# dictionary_views.py:163-172 — L'ESCRIPTURA (correcta)
CustomerPOMAlias.objects.update_or_create(
    customer=customer, client_code=code,
    defaults={'pom': pom, 'description_en': desc_en,
              'description_local': desc_local, 'language': idioma,
              'origen': 'DICCIONARI'})          # ← mai escriu client_description (correcte)
```

```jsx
// CustomerDetail.jsx:190-197 — LA LECTURA (trencada)
const descDup = (r) => !r.client_description || …        // ← :190  sempre TRUE per al wizard
{ key: 'client_description', label: t('clients.alias_desc'),
  render: r => descDup(r) ? <span…>—</span> : r.client_description }   // ← :196-197
```

`client_description` és `''` per a **tot** àlies del wizard ⇒ `descDup` sempre `true` ⇒ **sempre "—"**.
El comentari de `CustomerDetail.jsx:189` ho deia: *"El diccionari (description_en/local) omplirà
això de veritat"* — **la promesa mai es va cablejar**.

### PROVA A BD: la dada HI ÉS

```sql
SELECT id, client_code, client_description, description_en, description_local, language
FROM fhort.pom_customerpomalias WHERE origen='DICCIONARI' AND customer_id=7 ORDER BY id LIMIT 5;
```

```
 id | client_code | client_description |   description_en   |   description_local   | lang
----+-------------+--------------------+--------------------+-----------------------+------
 26 | EK          |      (buit)        | NECKLINE WIDTH     | ANCHO ESCOTE          | es
 27 | EKK         |      (buit)        | BACK NECKLINE WIDTH| ANCHO ESCOTE ESPALDA  | es
 30 | E           |      (buit)        | SHOULDER TO SHOULDER| HOMBRO A HOMBRO      | es
```

**Els 90 àlies del wizard tenen la descripció desada, en EN i en local.** El model marca
`client_description` com a **OBSOLET** i prohibeix escriure-hi (`models.py:255-258`).

**Contradicció viva (fora d'abast, ANOTADA):** el camí d'aprenentatge automàtic
(`services.py:384,390,392`) i el **formulari d'alta manual** (`CustomerDetail.jsx:328`) **encara
escriuen `client_description`**, el camp que el model prohibeix. Per això els àlies vells sí que
mostren descripció i els del wizard no.

**Efecte lateral del mateix desfasament:** `views.py:349`
`search_fields = ['client_code', 'client_description']` ⇒ **la cerca de la biblioteca no troba
les descripcions del diccionari.**

> **Veredicte D4b:** causa **continguda i inequívoca**. **Cap dada perduda, cap reparació de
> dades necessària.** Fix de lectura en 2 punts (+2 de convergència).

---

## D4c — ORIGEN MOSTRA LA CLAU CRUA

```jsx
// CustomerDetail.jsx:217
<Badge variant={ORIGEN_VARIANT[r.origen] || 'gray'}>{t(`clients.origen_${r.origen}`)}</Badge>
```

Clau i18n **construïda dinàmicament** per interpolació. Claus `clients.origen_*` existents:

| fitxer | claus |
|---|---|
| `frontend/src/i18n/ca.json:269-271` | `origen_IMPORT`, `origen_MANUAL`, `origen_MIGRACIO` |
| `frontend/src/i18n/en.json:269-271` | idem |
| `frontend/src/i18n/es.json:269-271` | idem |

**`clients.origen_DICCIONARI`: NO EXISTEIX a cap dels tres.** i18next, en no trobar-la, retorna
la clau crua ⇒ el text `clients.origen_DICCIONARI` a la cel·la.

**El valor de BD és LEGÍTIM:** `origen` té 4 choices (`models.py:243-246`:
`IMPORT`/`MANUAL`/`MIGRACIO`/**`DICCIONARI`**) i el wizard hi escriu `'DICCIONARI'`
(`dictionary_views.py:170`). El cens de BD només retorna `MIGRACIO` i `DICCIONARI` — **cap valor
estrany**.

**Bug germà a la mateixa línia:** `CustomerDetail.jsx:28`
`const ORIGEN_VARIANT = { IMPORT: 'gold', MANUAL: 'ok', MIGRACIO: 'gray' }` — **tampoc té
`DICCIONARI`** ⇒ el badge cau al fallback gris.

> **Veredicte D4c:** defecte **de CODI, no de dada**. **NO s'ha de normalitzar cap valor de BD.**
> Incompliment del guardià *i18n-gate ×3* del `CLAUDE.md`: l'sprint que va afegir el choice
> `DICCIONARI` no va afegir la clau als tres idiomes.

---

## D5 — LA BIBLIOTECA NO LLISTA TOTS ELS ÀLIES *(reportat pel CTO en sessió)*

```jsx
// CustomerDetail.jsx:161-162
const loadAliases = useCallback(() => customerAliases.list({ customer: customer.id })
  .then(res => setAliases(res.data?.results ?? …)), [customer.id])   // ← només la 1a pàgina
```

- `settings.py:217-218`: `DefaultPagination`, **`PAGE_SIZE = 25`** (`pagination.py:5-8`,
  `max_page_size = 200`, `page_size_query_param = 'page_size'`).
- El client 7 té **95 àlies** (5 + 90). La crida **no passa `page_size` ni recorre `next`**
  ⇒ **es pinten 25 de 95** (ordenats per `client_code`, `views.py:350`).
- El comptador de la capçalera (`CustomerDetail.jsx:237`, `aliases.length`) **també menteix**.

**El match per codi canònic JA HI ÉS:** `CustomerDetail.jsx:201-212` pinta `pom_code_global`
(`POM-XXX`) com a element principal, amb abreviatura + nom EN a sota; el serialitzador el
calcula a `serializers.py:326-329`. ⇒ **no cal construir res: cal portar les files que falten.**

> **Veredicte D5:** causa **continguda i inequívoca** (paginació no recorreguda).

---

## REPARACIÓ DE DADES D4a — PROPOSTA (NO EXECUTADA · espera OK de l'Agus)

### ⚠️ DOS MURS D'ESTRUCTURA: el brief demana dues coses que la BD no permet

**Mur 1 — `client_code` NO pot quedar buit** (família 1, els 5 de 0031):
- `client_code = CharField(max_length=60)` — **NOT NULL, sense `blank=True`** (`models.py:254`).
- `UniqueConstraint(['customer','client_code'])` (`models.py:273-276`).
⇒ **5 files del MATEIX client amb `client_code=''` violarien la unicitat.** Només una podria
quedar buida. *"Moure el text codi→descripció i deixar codi buit"* és **impossible per constraint
de BD**, no per criteri.

**Mur 2 — `pom = None` NO és possible** (família 2, els 13 dolents):
- `pom = models.ForeignKey(POMMaster, on_delete=models.CASCADE)` — **sense `null=True`**
  (`models.py:252-253`); a la BD, `pom_id | bigint | not null`.
⇒ *"desvincula […] `pom=None`"* **requereix una MIGRACIÓ d'esquema** (`null=True`) i que tot el
codi que llegeix `alias.pom` la toleri (`extraction_views.py:549` faria `AttributeError`).
**No es pot fer amb un `UPDATE`.**

**Mur 3 (el que de debò mana) — `pendent_revisio` és INERT per al matcher:**
```python
# extraction_views.py:545-550  — la branca (a), tal com és avui
alias = CustomerPOMAlias.objects.filter(customer=customer, client_code__iexact=key).first()
if alias and alias.pom.actiu:
    return alias.pom, 'alias_match', 'HIGH'      # ← NO mira pendent_revisio
```
⇒ **Marcar `pendent_revisio=True` NO impedeix que l'àlies segueixi auto-vinculant amb HIGH.**
Tancar-ho és **una línia** a `extraction_views.py` — **fitxer PROHIBIT en aquesta sessió**
(territori de la sessió d'importació). **DECISIÓ DEL CTO** (vegeu §BLOCADOR).

### 💡 PROPOSTA (a validar) — per família i per cas

**FAMÍLIA 1 · els 5 de la migració 0031** (prosa al camp codi · POM correcte · sense impacte de
matching). Acció: **`REPARA_DESC`** — conservadora, sense pèrdua.
1. `description_en := client_code` (el text va al camp que li toca ⇒ la columna Descripció deixa
   de ser "—").
2. `pendent_revisio := True` (no hi ha cap codi real de Brownie per a aquestes 5 ⇒ són,
   literalment, àlies pendents que algú ha de mirar).
3. `client_code` **intacte** (preserva el match per descripció, que funciona **per disseny**:
   `extraction_views.py:527-529`) · `pom` **intacte** (els 5 destins són correctes, §D4a·2).

**FAMÍLIA 2 · els 13 àlies amb el POM equivocat** (wizard del diccionari). Acció: **`DESVINCULA`**.
Com que `pom=None` és impossible (Mur 2) i `pendent_revisio` és inert (Mur 3), **l'única acció
que de debò treu el verí avui és ESBORRAR l'àlies**. És **reversible**: la nomenclatura viu al
full Excel del client i es torna a carregar amb el wizard (aquest cop, cap al POM correcte).

⚠️ **NO és una pèrdua de coneixement**: el que s'esborra és un **vincle equivocat**, no la
descripció del client (que és al full). Sense l'àlies, el matcher cau a les branques
deterministes (descripció/sinònims) — **pitjor confiança, però cap vincle FALS amb HIGH**.

**FAMÍLIA 3 · la brossa.** `id=110`, `client_code='0'` → **ESBORRAR**. No és un codi.

**Alternativa a la família 2 (millor, però és feina de catàleg i la decideix una persona):**
**repuntar** cada àlies al POM correcte, creant els POMs que falten (`F3`/`F4` centre davant/darrere,
`B1` stretched waist, `U2`/`U3` first/last button…). El command **no ho fa** — no s'inventa POMs.

### Abans / després (dry-run REAL, executat en mode lectura)

```
FAMÍLIA 1 — REPARA_DESC (5)                     description_en    pendent_revisio
  id 2  collar width                    ∅ → collar width                  f → TRUE
  id 3  body zip length                 ∅ → body zip length               f → TRUE
  id 4  lining length at center front   ∅ → lining length at center front f → TRUE
  id 5  lining length at center back    ∅ → lining length at center back  f → TRUE
  id 6  lining bottom width along hem   ∅ → lining bottom width along hem f → TRUE
  (client_code i pom: SENSE CANVIS)

FAMÍLIA 2 — DESVINCULA (13, esborrat del vincle fals)
  POM 389 TOTAL LENGTH  ......  F · FF · F3 · F4
  POM 439 Width sequins ......  U · U2 · U3
  POM 441 Chest piece height .  P · P2
  POM 437 Centre front length .  F1 · F2
  POM 275 Waist width ........  B1        (B es CONSERVA: és el correcte)
FAMÍLIA 3 — BROSSA (1)
  id 110  client_code='0'  → esborrat
```

**Entrega:** management command **idempotent, `--dry-run` per defecte** (cal `--apply` explícit).
**NO S'HA EXECUTAT EN MODE ESCRIPTURA.** L'executa l'Agus amb confirmació explícita.

---

## 🛑 BLOCADOR PER AL CTO (decisió humana · Patró C)

**`pendent_revisio` no atura res.** El matcher (`extraction_views.py:545-550`) torna
`alias_match`/`HIGH` **sense mirar la bandera**. Conseqüències:

1. La **reparació** de la família 2 **només pot ser un esborrat** (o una migració `null=True`).
   Si es prefereix **conservar** els àlies marcats en comptes d'esborrar-los, **cal primer** que
   el matcher honori `pendent_revisio` — **1 línia a `extraction_views.py`, fitxer que aquesta
   sessió té PROHIBIT tocar**.
2. El **guard d'aprenentatge** (T4c, implementat) crea l'àlies sospitós amb `pendent_revisio=True`
   perquè algú el miri — **però aquest àlies seguirà auto-vinculant amb HIGH** fins que es tanqui
   el mateix forat. El guard **evita el vincle dolent nou**, però **la bandera no protegeix res
   per si sola**.

**Recomanació:** afegir `pendent_revisio=False` al filtre de la branca (a) del matcher (o excloure
els àlies marcats). **Ho ha de fer la sessió d'importació** (propietària del fitxer), o
l'Agus autoritza aquesta sessió a tocar-lo.

---

## TAULA FINAL PER AL CTO

| Defecte | Causa (fitxer:línia) | Tipus | Contingut? | Reparació de dades? |
|---|---|---|---|---|
| **D3** modal escapçat/sense backdrop | `DictionaryWizard.jsx:112` z=60 < `Sidebar.jsx:312` z=100 | CODI (capa z) | ✅ sí | ❌ no |
| **D3-latent** | `ui/Modal.jsx:12` z=50 — **el patró canònic té el mateix forat** | CODI | ✅ sí | ❌ no |
| **D4a** prosa al camp codi | `0031:53-56` (dict amb claus = descripcions) | DADES | ✅ 5 files, 1 client | ⚠️ **PROPOSADA, espera OK** |
| **D4b** descripció "—" | `serializers.py:348-353` + `CustomerDetail.jsx:190-197` (lectura) | CODI | ✅ sí | ❌ **no — la dada hi és** |
| **D4c** clau i18n crua | `{ca,en,es}.json:269-271` sense `origen_DICCIONARI` + `CustomerDetail.jsx:28` | CODI | ✅ sí | ❌ **no — el valor és legítim** |
| **D5** només 25 de 95 àlies | `CustomerDetail.jsx:161-162` + `PAGE_SIZE=25` (`settings.py:218`) | CODI | ✅ sí | ❌ no |

### Banderes (fora d'abast, ANOTADES)

1. **`ui/Modal.jsx:12` (z=50) i ~18 overlays a mà (z=50/60) estan tots per sota del sidebar.**
   Avui només es nota al wizard (és l'únic panell prou ample). **Deute latent de tot el projecte.**
2. **`services.py:384,390,392` i `CustomerDetail.jsx:328` escriuen `client_description`**, camp
   que `models.py:255-257` declara obsolet i prohibeix escriure. Convergència pendent.
3. **`views.py:349` `search_fields`** no cerca als camps nous ⇒ la cerca no troba descripcions
   del diccionari.
4. **La "LLEI" de `0034:9`** (no resoldre POMs per substring) **no té cap guard de codi**: és un
   comentari. Una re-sembra futura pot repetir l'error de 0031.
5. **`find_pom_master` retorna `HIGH` per a un àlies sense mirar `pendent_revisio`**
   (`extraction_views.py:550`) ⇒ un àlies marcat per revisar auto-vincula igualment.

---

## FRONTERA AMB D1/D2 (`DIAGNOSI_QA_S8_IMPORT.md`)

**Són DOS importadors germans i separats**, i aquesta diagnosi **no toca cap fitxer de l'altra**:

| | D1/D2 (import de model) | D3/D4 (diccionari del client) |
|---|---|---|
| Wizard | `components/ImportWizard/ImportWizard.jsx` | `components/DictionaryWizard.jsx` |
| Backend | `models_app/extraction_views.py` | `pom/dictionary_views.py` + `dictionary_service.py` |
| Escriu | `BaseMeasurement` (mesures d'un model) | `CustomerPOMAlias` (nomenclatura d'un client) |
| Estat | **FIXAT** (`eb880fd` guard many-to-one + llindar · `3db0b82` codi del document) | aquesta diagnosi |

**⭐ LA TROBALLA QUE UNEIX LES DUES.** `DIAGNOSI_QA_S8_IMPORT.md` (D1d) conclou que *"la palanca
de debò sobre els 9 sense-match no és el parser: és el catàleg / `CustomerPOMAlias`"*, i recomana
**mesurar-ho abans d'invertir en el parser determinista (fix C)**.

**Aquesta diagnosi tanca aquella pregunta oberta amb evidència:** el wizard del diccionari va
sembrar **90 àlies del client 7 avui (2026-07-13 06:15)** i, amb el catàleg d'ara, **els 10
codis sense-match de D1 (`G1 E1 E4 EP S S2 J JJ J1 I3`) resolen TOTS a `alias_match`/`HIGH`**
(§D4a·4, verificat executant `find_pom_master`).

⇒ **El buit de catàleg de D1 ja està tancat.** Una reimportació de Brownie no hauria de tenir
cap sense-match. **Recomanació: mesurar-ho abans de decidir el fix C** (el parser determinista),
tal com demanava D1 — el seu argument principal (el matching) ha desaparegut; el que queda a
favor de C és el cost/latència d'Opus i la fila `JJ` perduda en silenci.

⚠️ **Cap dels 5 àlies contaminats (D4a) hi té res a veure**: apunten a POMs de coll, cremallera i
folre, no a cap dels 10 codis sense-match. **La contaminació i els sense-match són defectes
independents.**

---

*Diagnosi read-only. Cap escriptura de codi, cap migració, cap `UPDATE`. Els censos són
`SELECT` purs sobre `fhort.pom_customerpomalias`; la prova del matcher és una crida a
`find_pom_master` (funció de lectura pura, `extraction_views.py:519-620`).*
