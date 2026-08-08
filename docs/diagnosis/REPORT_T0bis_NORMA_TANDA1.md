# REPORT T0-bis · NORMA UI TANDA 1 (S38) — 🛑 STOP de tram

**Data:** 08/08/2026 · **Branca:** dev · **Commits:** 136 · 137 · 138 · **CAP PUSH**
**Punt de partida:** `91cf1e56` → **HEAD `a7bc6fa0`**

Tres commits aïllats, cadascun amb build verd. Cap pantalla tocada.

| # | Commit | Fitxers |
|---|---|---|
| 136 | `6f4a3be9` `--fs-caption` 8px → 10px | `index.css` |
| 137 | `ca30e41d` l'acció primària passa a blava | `components/ui/buttons.js` |
| 138 | `a7bc6fa0` els radis tenen nom | `index.css` · `PageMenu.jsx` |

---

## T0-bis.1 · `--fs-caption` 8px → 10px

**NO ha calgut partir el token.** Comprovació feta ABANS de tocar res, com manava l'ordre:

| Superfície de paper | Consumeix `--fs-caption`? |
|---|---|
| `FittingPrintSheet.jsx` — l'ÚNIC full que s'imprimeix (amb `@page` i `@media print`) | **0 usos.** Les seves mides són pt explícits: 6.8pt · 7.5pt · 8.5pt (+ un `--fs-body`) |
| `FttHeaderBand.jsx` — l'únic component que el full importa | **0 usos.** Mides via `px(ESTIL.v12.cos)` |
| `utils/capaInstancia.js` · `utils/identitatMesura.js` — els utils que importa | **0 usos** |
| PDF de la fitxa tècnica | **No hi arriba mai**: surt de `stage.toDataURL()`, ràster de Konva. Els 11 usos del `TechSheetEditor` són crom d'editor (panells, missatges, badges), no dibuix |

**El comentari que hi havia a `index.css` era enganyós i s'ha corregit.** Deia que el 8 era
«el terra (= mínim 8pt de la fitxa tècnica)», i això suggeria un lligam amb el paper que no
existeix. El mínim de 8pt del paper el segueix guardant el paper, amb els seus pt explícits.

**Consumidors que canvien: 289 punts en 78 fitxers.** Tots creixen alhora, de 8 a 10px.
Els cinc més densos: `RelationsPanel` (18) · `ModelPomList` (14) · `ModelWizard` (12) ·
`TechSheetEditor` (11) · `OrderDetail` (9).

**Conseqüència volguda, per si sorprèn:** `--fs-caption` i `--fs-label` queden tots dos a
**10px**. És el que la norma vol (§2: caption/TH 10/12 · label 10). Es mantenen com a dos noms
perquè els rols difereixen —el label va en majúscules amb tracking— i poden evolucionar a part.

---

## T0-bis.2 · L'acció primària passa a blava

`primaryBtn`: fons `--gold` → **`--accio`** · tinta `--text-main` → **`--white`**.
Reescrit d'un cop: **66 usos en 28 fitxers**.

**Contrast mesurat: blanc sobre `#2b65c2` = 5.61:1** → AA amb marge.

No contradiu S37, la substitueix. Aleshores la primària era daurada i el problema era el
contrast (blanc sobre daurat = 3.44:1); es va resoldre canviant la TINTA a `--text-main`
(4.91:1) sense tocar la marca. Ara no canvia la tinta sinó el **rol**: el fons ja no és de marca.

### Pantalles amb més d'un blau — el que s'ha MESURAT

Sonda sobre **30 rutes** comptant elements amb fons `--accio`: **cap pantalla amb dos blaus
alhora**. El que va sortir, un blau per pantalla i al seu lloc:

`/models` i `/models/1308` («Accions») · `/clients` («Nou client») · `/comercial/productes`
(«Nou producte») · `/comercial/ofertes` («Nova oferta») · `/comercial/albarans` («Compondre
albarà») · `/comercial/condicions-pagament` («Nova condició») · `/recursos` («Nou recurs») ·
`/configuracio/general` («Desar») · `/garment-types` («Nou tipus»).

El recompte estàtic n'assenyalava set de sospitoses. **Inspeccionades una per una, totes les
tenen en branques EXCLOENTS** i per això no es veuen mai juntes:

| Fitxer | Usos | Per què no coincideixen |
|---|---|---|
| `SizeMapSetup.jsx` | 7 | `step === 1 / 2 / 3` |
| `WorkOrderDetail.jsx` | 6 | `isOpen` vs `isClosed` (L255 i L261 són excloents) |
| `BulkImportWizard.jsx` | 5 | passos del wizard |
| `CustomerDetail.jsx` | 4 | 3 tabs (`?tab=`): Dades · Tècnic · Comercial |
| `QuoteDetail` · `ProductDetail` · `DeliveryNoteDetail` | 4 c/u | mateixa forma (estat/modal) |

⚠️ **Límit d'aquesta mesura, dit clar:** l'escaneig corre amb corpus buit (`fhort` té 0 models),
o sigui que **no ha pogut exercitar detalls poblats ni modals oberts**. La inspecció del codi
cobreix el forat per als 7 fitxers densos, però no puc afirmar-ho dels 28.

### 🚩 El que la sonda SÍ que ha destapat — a resoldre a la conformitat, no aquí

**El disparador d'`ActionsMenu` («Accions ▾») ara surt BLAU i no hauria.** Consumeix
`primaryBtn` (`ActionsMenu.jsx:543`, `triggerBtn = { ...primaryBtn, marginLeft: 0 }`), i la
norma §5.6 el vol **SECUNDARI**: «Menú Accions ⋯ (secundari): NOMÉS ocasionals (duplicar,
exportar, arxivar). MAI passos de flux.» Es veu a `t0bis_caption_despres.png`, a dalt a la dreta.

Afecta **`/models` (T1)** i el **dashboard del model (T2)**, i també `TaskAssignWizard`.
No s'ha tocat, per ordre. És el primer que cauria a T1.

---

## T0-bis.3 · Tokens de radi

`--r-ctrl: 6px` · `--r-card: 12px` · `--r-pill: 999px` (§3).

Els tres valors ja eren els de la casa; el que faltava era el nom. `<PageMenu>` passa a
consumir `--r-ctrl` i `--r-pill` (tenia el literal `6` perquè el token no existia encara).
**La resta de literals de radi NO s'han migrat**, com manava l'ordre.

---

## Verificació

| Control | Resultat |
|---|---|
| `npm run build` | ✅ verd als 3 commits |
| `eslint` global | **1254 problems (991 errors, 263 warnings)** — **idèntic a la línia base: delta 0** |
| Tokens al navegador | ✅ 8/8 nous i modificats al valor esperat (`--fs-caption` 10px · `--r-ctrl/card/pill` · `--accio` · `--warn-ink` · `--col-talla`) |
| `eslint` a `PageMenu.jsx` | ✅ net |
| i18n | ✅ cap clau nova, cap literal nou |

**Guardia-ui:** la còpia vigent ja és a `.claude/agents/`. T0-bis no dibuixa cap pantalla i no
té maqueta contra la qual anar bidireccional; la primera verificació bidireccional de debò
és la de T1 contra `NORMA_LLISTA_canonica.html`.

## Captures — `ops/qa/captures/`

| Fitxer | Què és |
|---|---|
| `t0bis_caption_abans.png` / `t0bis_caption_despres.png` | Taula de mesures amb caption a 8px i a 10px (mateix bundle, token reinjectat: l'única diferència és el token) |
| `t0bis_primaria_clients.png` | El blau primari amb tinta blanca («Nou client») |
| `t0bis_primaria_models.png` | `/models` — s'hi veu l'«Accions ▾» blau que no hauria de ser-ho |

## Conducta afegida

**Cap.** Els tres commits són tokens i un fitxer d'estils compartit; cap petició, cap estat
asíncron, cap decisió de permís.

## PROVISIONAL-DOMINI

**Cap a T0-bis.**

---

## 🛑 STOP

T0-bis tancat i verificat. **Espero validació a pantalla real** — el blau primari és un canvi
visible a tot el producte i afecta 28 fitxers.

Res no bloqueja T1: les 4 decisions que vas donar (breadcrumb de 4 segments, `--text-muted`
ajornat, `--bg-page` correcte, i les tres d'aquest tram) ja són aplicades o anotades.
