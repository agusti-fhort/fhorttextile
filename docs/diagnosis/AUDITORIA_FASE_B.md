# AUDITORIA · PART B · SESSIÓ 1 (lot tècnic + propietària de compartits i backend)

> 09/08/2026 · branca `dev` · **cap push**. Una fitxa per pantalla, acumulada.
> Sessió germana en paral·lel: **S2**, lot comercial (només frontend). Coordinació per missatge.
> Numeració de commits: **S1 va a la sèrie 250+**, S2 a la 2xx (van xocar el 203 i el 204).

**Protocol de cada pantalla:** llegir-la sencera → cens dada→endpoint → germana conformada de
referència → aplicar → `ops/qa/qa_bidireccional.py` → fitxa → commit selectiu → build/eslint 0.

**Les tres eines de mesura** (cap veredicte sense elles):

| Eina | Què respon |
|---|---|
| `ops/qa/qa_auditoria_computats.py` | ¿hi ha cap vora, badge o rètol que no sigui el que la NORMA mana? |
| `ops/qa/qa_bidireccional.py` | ¿la pantalla i la seva maqueta pinten el mateix? (computats a les dues bandes) |
| `ops/qa/qa_8bquater_crom.py` **(nou)** | ¿el crom queda enganxat de debò en desplaçar-se? |

---

## §8b-quater · TOP BAR + MENÚ DE PANTALLA, UN SOL BLOC ENGANXAT (commit 250·203)

Ordre d'Agus del 09/08, prèvia a tot el lot. Va a `Shell.jsx` (top bar) i a `ui/PageMenu.jsx`
(menú), **un sol lloc cadascun**; cap pantalla ho re-declara, ni les ja conformades.

### El que no es veia llegint el codi

1. **`<main>` portava `overflowY: 'auto'` i això matava TOT sticky de dins.** El `<main>` no ha
   tingut mai scroll propi (la seva columna té `minHeight: 100vh` i cap alçada màxima: creix amb
   el contingut i qui es desplaça és el document). Però `overflow` ≠ `visible` **crea igualment
   una caixa de desplaçament**, i per a `position: sticky` la caixa més propera és la referència:
   qualsevol element enganxós quedava ancorat a un scrollport que no es desplaça mai. Mort sense
   fer soroll.
2. **La barra només es pot moure DINS del seu contenidor**, i el contenidor —el `<div>` de marge
   negatiu que cada pantalla hi posa perquè vagi de costat a costat— fa exactament la seva
   alçada: recorregut zero. Qui s'ha d'enganxar és el CONTENIDOR. Com que el declara cada
   pantalla, l'única manera de dir-ho un sol cop és pujar-hi amb `:has()` des de l'àncora
   `data-ftt-pagemenu`, a `index.css`.
3. **El `top` es va escriure compensant el marge negatiu** (`calc(… + 1.5rem)`), perquè
   l'especificació ancora la caixa de MARGE. **La mesura va dir el contrari**: amb la
   compensació, la barra queda 24px sota la top bar ja en repòs. Va sense compensar.

### Mesura

`ops/qa/qa_8bquater_crom.py` (nou) · **0 incompliments**. Comprova, a una pantalla llarga i una
curta: que en repòs es toquen · que després de desplaçar-se cap dels dos s'ha mogut · que el menú
s'atura exactament sota la top bar · que els dos fons són OPACS · que el filet inferior és
`--line` · les capes de z · i que el contingut hi passa PER SOTA (`elementFromPoint`).

⚠️ **La pantalla llarga només és llarga en un tenant poblat.** Amb `fhort` (UN model), `/models`
no desborda ni amb finestra baixa i la prova hauria passat **sense provar res**. Es corre també
amb `FTT_QA_HOST=los.fhorttextile.tech` (51 models → 860px de desplaçament real).

### Capes de z, tal com queden

`contingut < menú de pantalla (20) < top bar (30) < menú lateral (100) < modals (150) <
drawers (200) < editors a pantalla completa (1000) < guard de tasca oblidada (2000)`

### Pell de la TOP BAR (passa conformitat en aquest tram) — llistada per si es veta

- fons `--panel` i filet inferior `--line`: **se'n van dos dels tres colors fora de paleta** que
  els blocs A i B tenien anotats (`#e8e8e8` al filet, `#e4e4e2` al selector d'idioma i al botó de
  perfil). El tercer és del menú lateral, que **no es toca**.
- `--gray` (**3.64:1, per sota d'AA**) → `--text-soft` a la data i l'hora · `--charcoal` →
  `--text-main` · radis 8 i 4 → `--r-ctrl` · vores de `0.5px` → 1px.
- `UnitToggle`: se'n van `--gold-pale` (**ELIMINAT** per la §1), `--border` i `--text-muted`
  (DEPRECATS per la §1b) i **el daurat dels dos estats** — la unitat vigent ja la diu la paraula
  escrita, i pintar-la de marca és marca pintant una dada (§8c).
- El botó de perfil no tenia ni títol ni `aria-label`, i la icona anava a 17px (cap de les tres
  mides de la §8) → 20, que és la d'una icona standalone.

### 🚨 Porta d'i18n trencada, i arreglada

`UnitToggle` tenia el títol en una **cadena catalana a pèl** (`Canviar a Polzades (inch)`),
idèntica en anglès i en castellà. Passa a `t()` amb paritat als tres idiomes
(`topbar.unit_switch` · `topbar.profile`).

---

## B1 · Desenvolupament — `/` (commit 251)

La home del tècnic. `nav.dashboard` es diu «Desenvolupament» (per això el brief la nomena així);
el fitxer és `pages/Dashboard.jsx`. **Germana de referència: el dashboard del model (A6)** —
mateixa estructura de pàgina del §8b i mateix tram de «només pell».

### Cens dada → endpoint

| Què es pinta | D'on surt |
|---|---|
| Salutació (nom de pila) | `GET /api/v1/me/` → `full_name` / `username` |
| Targeta de configuració inicial | `GET /api/v1/onboarding/status/` → `percentatge` · `passos_pendents` |
| KPI «Models de l'abast» · «En curs» | `GET /api/v1/model-tasks/by-model/?all=true&assignee=me` (paginació seguida) |
| KPI «En risc» | creuament de l'anterior amb `calendar/events` (`tipus='tasca'` amb `en_risc`) |
| «Properament» | `calendar/events?start=&end=` (+60 dies) → `fitting` i `confeccio`, filtrats als models de l'abast |
| Board · files i estat de columna | mateix `by-model` (`kanban_state` **derivat al backend**, `tasks/views_b.py:193`) |
| Targeta de model (nom · codi · fase · nre. de tasques) | `model_nom` · `model_codi` · `fase` · `counts{}` |
| Filtre de client | `GET /api/v1/customers/?page_size=200` |
| Filtre de fase | `GET /api/v1/vocabulari/` → `fases_model` |
| **Filtre de temporada** | **`GET /api/v1/vocabulari/` → `temporades` (NOU en aquest tram)** |
| Obrir un model | navegació a `/models/{id}` |

### CENSAT-PENDENT exposat en aquest tram

**`temporades`** (`Model.TEMPORADA_CHOICES`: SS · FW · CO · SP). La pantalla la declarava al
client (`TEMPORADES = ["SS","FW","CO","SP"]`) i ara surt de `/vocabulari/`, com les fases. Sense
vocabulari el filtre **no ofereix cap temporada** — no en sabem cap, i inventar-ne seria tornar-hi.

### Desviacions trobades i corregides

| Què | Abans | Ara |
|---|---|---|
| Menú de pantalla | **no existia**: banda de pestanyes amb l'activa en daurat + subratllat daurat | §8b: barra blanca amb píndoles (mateix defecte que A6 va treure del dashboard del model) |
| Padding arrel | 24px **a sobre** dels 24 del `<main>` | 0 (§3) |
| Targeta de configuració inicial | fons `--gold-pale` (**token ELIMINAT**), % en daurat dins d'un cercle, fals botó de fons daurat ple | targeta de la casa + % com a **KPI neutre** + **PORTA** en secundari amb chevron (§5.3) |
| KPI | vora `--border` (deprecat), radi 8, rètol `--text-muted`, valors en **daurat** | `--line` · `--r-card` · `--text-soft` · valors **neutres**; **només «En risc» porta semàfor** (§8c: «el daurat NO pinta números») |
| Targeta de model | **codi en daurat 600** i nom en tinta normal | **el NOM és la dada reina** (600, tinta principal) i el codi va en secundari — la jerarquia de la llista germana (§8e) |
| Model actiu | anell daurat de 1.5px per fora (la targeta canviava d'amplada en encendre's) | `--sel` + **filet d'or de 3px** a l'esquerra, sempre declarat (transparent quan no toca) |
| Fase a la targeta | xip gris amb radi 6 | **només text** (§8e) |
| Capçalera de columna | fons `--gray-l`, filets de `0.5px`, recompte en píndola grisa | panell blanc, filet `--line`, recompte neutre |
| Controls de filtre | còpia local amb `--gray-l` de vora i `0.5px` | control de la casa (§8c): vora `--line`, radi 6, alçada única |
| «Neteja» i «Carregar-ne més» | estil d'**input** fent de botó | terciària i secundària (§5) |
| Deshabilitat de «Carregar-ne més» | `opacity: 0.6` | `apagat` (§5.7: baixa el fons, no la tinta) |
| Estats buits | caixa amb **vora discontínua** i icona de 26px | frase `--text-faint` cursiva (§8c) |
| Rètols de bloc | `--gold` / `--text-muted` | `--text-soft`, majúscules amb tracking |
| Icones | 15px, `--gray` | 16px, `--text-soft` (§8: tres mides, quatre tintes) |
| Targetes sense mida de cos | heretaven els **16px del document** | declaren `--fs-body` (defecte que la mesura del bloc A va treure a la llum) |

### 🛑 ATURADA · LA FLETXA DE L'ARREL — decisió d'Agus

La §8b diu que el menú porta **sempre** la fletxa `←` amb destí explícit i que «la posició del ←
és fixa a tot el producte». Però `/` **és l'arrel i no penja d'enlloc**: una fletxa que apunta a
la pantalla on ja ets és una mentida que es descobreix al primer clic, i és exactament el que el
`backTo` obligatori de `ui/PageMenu` existeix per evitar.

**Proposta conjunta de les dues sessions** (per no donar dues respostes al mateix dubte):
**la barra es queda i la fletxa TAMBÉ, però DESHABILITADA.** Ni desapareix —això contradiria la
lletra de la norma i, pitjor, la seva raó («és justament el que la fa trobable sense mirar»)— ni
menteix. Deshabilitada diu la veritat exacta: el botó existeix, és al seu lloc de sempre, i des
d'aquí no hi ha on pujar.

La forma no s'inventa: §5.7 («deshabilitat: baixa el fons, no la tinta») amb l'excepció que el
bloc B ja va resoldre **dins d'aquesta mateixa barra blanca** —«a la barra no hi ha fons que
baixar; donar-li `--bg-page` el deixa a un pas de `--sel`, que allà vol dir el contrari»— i que
va concloure que al menú mana la §1: **`--text-faint` és «només deshabilitat»**.

Implementació: `backTo={null}` és una **declaració explícita**, no un valor per defecte que es
pugui colar per oblit (`undefined` segueix pintant la fletxa i, sense destí, falla de seguida).
**Si Agus ho vol d'una altra manera, és una línia.**

### Verificació

| Eina | Resultat |
|---|---|
| `qa_auditoria_computats.py` (10 pantalles, les 9 conformades + `/`) | ✅ **0 incompliments** |
| `qa_bidireccional.py` · tram B1 (5 casos) | **1 desviació, i és la declarada** (v. sota) |
| `qa_8bquater_crom.py` | ✅ **0 incompliments** |
| `npx eslint src` | ✅ **0 errors** |
| `npm run build` | ✅ net i desplegat |

**La desviació que queda, explicada:** `.back` · `color` maqueta `rgb(110,106,100)` (`--text-soft`)
vs pantalla `rgb(152,147,139)` (`--text-faint`). **És l'aturada de sobre**: la maqueta dibuixa una
pantalla que sí que penja d'algun lloc; aquesta és l'arrel i la fletxa hi va deshabilitada. La
caixa (fons, vora, radi, mida) casa; la tinta és la decisió que espera.

### Esmena a la MAQUETA (la font, no la pantalla)

`PROPOSTA_menu_pantalla_v3.html` · `.back` **no declarava ni `color` ni `font-size`** i es quedava
amb els de l'agent d'usuari (negre, 13.33px). A la maqueta no es notava perquè la icona és un
`<svg>` amb la seva pròpia mida i el seu propi `stroke`; però la pantalla fa servir una icona de
**font**, que els hereta del botó, i la bidireccional donava com a desviació de la pantalla un
valor que **ningú no havia decidit a la maqueta**. Mateixa esmena i mateix motiu que el bloc B va
aplicar a `NORMA_LLISTA_canonica`. **Zero canvi de píxel.**

### 🚩 Anotat, NO tocat

1. **`pages/Models.jsx:14` · `SEASONS`** — la germana viva de `TEMPORADES`. És pantalla
   **CONFORMADA (A5) i per tant intocable en aquest lot**: es reporta, no es corregeix. Ara que
   `temporades` és a l'endpoint, matar-la és canviar tres línies.
2. **Petició de xarxa morta a cada canvi de filtre.** `modelsApi.faseCounts(...)` es crida a
   `ModelBoard` i **el resultat es llença**: `const [, setFaseCounts] = useState(...)` — el valor
   no el llegeix ningú des que les pastilles de comptes es van amagar («higiene diferida», diu el
   comentari). És una petició per teclejada (amb debounce) que no pinta res.
3. **`KPICard` té un `onClick` que ningú no li passa** mai: la targeta declara `cursor: pointer`
   condicional i dos gestos de hover per a un camí mort.
4. **El codi de colors de les quatre columnes del board se'n va, i falta UNA decisió per
   recuperar-lo.** Hi havia `--gray`/`--gold`/`--warn`/`--ok` tenyint la icona de cada capçalera:
   la §8 només admet quatre tintes d'icona i el daurat és marca, no dada. Es podria fer amb
   semàfor —la §1 diu que «la dada porta el color»— però **la §8e només nomena TRES estats**
   (Començat neutre · En curs taronja · Acabat verd) i aquest board en té **QUATRE**: dir de quin
   color és «pausat» és domini, no pell. Les columnes es distingeixen pel nom i la posició.
5. **19 ViewSets més perden l'`OrderingFilter` en silenci** (v. la coda de `/customers`, sota).

---

## B2 · Planificació — `/planificacio` (commit 252)

El shell de govern del planificador: **sis seccions** (Dashboard · Planificació · Assignació ·
Calendari de projecte · Informes · Registre) sobre la mateixa pantalla, i el Gantt de projecte.
Germana de referència: **A6** per a l'estructura i **A5/§8e** per a les llistes de dins.

### Cens dada → endpoint

| Què es pinta | D'on surt |
|---|---|
| Carpetes Pendents/Assignades | `model-tasks/by-model/?all=true` + `model-tasks/` + `users/` (paginació seguida a les tres) |
| Cua d'un tècnic (ordre real) | `planned_start`/`planned_end` de les tasques no-Done d'aquell tècnic |
| Reordenar la cua | `POST plan/reorder/` (`assignee_id` + `model_ids`) |
| Desassignar un model | `POST models/{id}/unassign/` |
| Reassignar una tasca | `PATCH model-tasks/{id}/` (`assignee`) |
| Esborrar una tasca | `DELETE model-tasks/{id}/` (el backend només ho permet en `Pending`) |
| Gantt de projecte | `GET plan/gantt/` + `companyCalendar` (dies no laborables) |
| Ordre de fases del Gantt | `GET /api/v1/vocabulari/` → `fases_model` |
| Viabilitat (latest start · semàfor) | **calculada al client** a partir de `estimated_minutes` i `data_objectiu` 🚩 |

### Desviacions trobades i corregides

| Què | Abans | Ara |
|---|---|---|
| Menú de pantalla | **no existia**: sis botons amb l'actiu en **daurat ple** sobre `--bg-muted` | §8b: píndoles a la barra blanca |
| Rètol de carpeta | **píndola taronja** (`--warn-bg` + `--warn` a 600) amb el recompte entre parèntesis | §8e: **el valor mana** (22/600) + etiqueta en caption, i la cerca al costat |
| Fila desplegada / arrossegada | fons `--warn-bg` (**semàfor fent de selecció**) | `--sel` (§1) |
| Nansa d'arrossegar | el caràcter braille **`⠿`** | icona Tabler 16px (§8: mai un caràcter tipogràfic) |
| Fons de la fila desplegada | **`var(--bg, #faf9f7)`** — `--bg` **no existeix**: es pintava sempre el literal de reserva | `--bg-page` |
| «En risc» del semàfor | `--warn` (1.86:1 com a text) | `--warn-ink` (§1b(d)) |
| Xips de filtre del Gantt | el triat s'omplia de **`--err` PLE** amb tinta blanca | «inclòs» = verd (§1): `--ok-bg` + tinta i vora `--ok` |
| Xips de tècnic | el triat es marcava amb vora `--text-main` | mateixa forma verda d'inclusió |
| Capçalera de l'eix del Gantt | crema `--bg-muted` | panell blanc + filet `--line` |
| Sense accés | caixa centrada amb icona de **32px** i tinta `--gray` | frase `--text-faint` cursiva (§8c) |
| Tokens | `--gray-l`, `--gray`, `--border`, `--text-muted`, `--bg-card`, `--bg-muted`, vores de `0.5px`, radis literals, pes 300 | l'escala de la norma |

**Fitxers del tram:** `pages/Planning.jsx` · `components/planning/{ProjectGantt,DashboardGovPanel,InformesPanel,TimeTree,PhaseTimeStrip}.jsx` · `pages/RegistreActivitat.jsx` (el tab «Registre»).

### `ui/buttons.js` · `selS` es conforma per a TOT el producte

`selS` és el control en línia de la casa i el consumeixen **126 usos en 24 fitxers**. Anava amb
`0.5px solid var(--gray-l)`: `--gray-l` (#f0f0f0) és un àlies de **farciment** fent de vora, en
gris fred, quan la vora de la norma és `--line`; i mig píxel no és de cap escala (el navegador
l'arrodoneix i el resultat depèn del zoom).

⚠️ **Toca pantalles ja conformades** (`/cataleg-peces`, `/garment-types`, l'`ActionsMenu` del
model). Va cap a la norma a totes — mateix criteri amb què el bloc A va canviar `GroupPills` i el
bloc B `ui/Badge` per a tot el producte — i per això la bidireccional es torna a córrer sencera
sobre tot el que ja estava tancat. **L'alçada NO s'hi fixa a posta**: hi ha usos que ajusten el
`padding` per encabir el control dins d'una cel·la de taula, i una alçada única els trencaria en
silenci.

### 🚩 Anotat, NO tocat

1. **La VIABILITAT es calcula al client.** `calcViabilitat` (`Planning.jsx`) dedueix el «latest
   start» i el semàfor amb **420 min/dia i dl-dv sense festius escrits a mà**, mentre el Gantt de
   la mateixa pantalla llegeix els dies no laborables del **CompanyCalendar** (font única). Dues
   respostes a la mateixa pregunta a la mateixa pantalla. No s'ha tocat: unificar-ho és decidir
   quina mana, i això és domini.
2. **L'auditoria de computats només mesura el tab per defecte** (Dashboard de govern): l'arnès no
   clica. Els altres cinc tabs s'han conformat per token i pel lint, **no mesurats un a un**.
3. `FASE_COLORS` del Gantt **es queda**: és una paleta de data-viz indexada pel codi de fase
   (mateix criteri que `KONVA_COL`), no una còpia de l'enumeració — el fitxer ja ho tenia escrit.

## B3 · Fittings — `/fittings` (commit 253)

La llista de sessions de fitting, amb els grups (convocatòries) plegables. Germana de
referència: **A5/§8e**.

### Cens dada → endpoint

| Què es pinta | D'on surt |
|---|---|
| Files i grups | `GET /api/v1/fitting-sessions/?page_size=100` (+ `fase`, `estat`) |
| Els quatre recomptes de dalt | quatre `GET …?page_size=1` → `count` (el cens no es dedueix d'una pàgina) |
| Filtre de fase / d'estat | `GET /api/v1/vocabulari/` → `fases_model` · `estats_sessio_fitting` |
| Assistents (punts de color) | `attendees_info[].color_avatar` de la mateixa resposta |
| Assistents elegibles | `GET plan/eligible-attendees/` |
| «Fitting aquí i ara» | `POST fitting-sessions/schedule-now/` |
| Accions de grup (reprogramar, afegir model, assistents, esborrar) | `fitting-sessions/` + `AddModelToGroupModal` |

### Desviacions trobades i corregides

| Què | Abans | Ara |
|---|---|---|
| Menú de pantalla | **no existia**; «Fitting ara» era un botó de fons **`--charcoal`** (negre ple) | §8b: l'acció puja al menú i **deixa de ser botó i de ser de color** |
| Capçalera | `h1` amb el nom de l'entitat i el recompte sol dins d'un `<p>` **sense dir de què era** | §8e: el valor gran + la seva etiqueta + els filtres a la mateixa línia |
| Els dos eixos de filtre | **dues files de pastilles** amb el triat en negre ple (sis fases + quatre estats = dues línies senceres) | dos selects, control de la casa (§8c) |
| Columna FASE | `Badge variant="gate"` — el **verd d'èxit** pintant una fase | **només text** (§8e) |
| Columna «objectiu» (la dada reina) | `--gold` a pes 500 | `--text-main` a 600 (§8e) |
| Filet de la fila filla del grup | `2px solid var(--gold-pale)` — **token ELIMINAT** | `--gold-border` |
| Assistent marcat al modal | fons `--gold-pale` | «inclòs» = verd (§1) |
| Confirmar/cancel·lar en línia | `--charcoal` ple / vora `--gray-l`, radi 4 | primària blava i terciària (§5) |
| Estats buit i de càrrega | caixa de `3rem` centrada | frase `--text-faint` cursiva (§8c) |
| KPI | `subColor` de semàfor a tres dels quatre | **neutres**: cap dels quatre és una alerta. I era **codi mort**: cap passa `sub`, i `subColor` només tenyeix el subtítol |

### Dos components de `ui/` conformats amb aquesta pantalla (toquen tot el producte)

- **`ui/StatCard`**: `#e4e4e2` de vora · icona en `--gold` (§8c: «el daurat NO pinta números»;
  §8: el daurat és la tinta ACTIVA, no la de repòs) · `--gray`/`--charcoal` · el valor a `2rem`
  escrit a mà, que és exactament `--fs-display` però sense nom · subtítol a pes 300.
- **`ui/Card`**: `#e4e4e2`, vores de mig píxel, radi literal, paddings en `rem` fora de la base
  de 4, i la icona de capçalera a **18px en `--gold`** (ni la mida ni la tinta són de la §8).

### 🚨 L'auditoria absolia un color que ja no li pertocava

`qa_auditoria_computats.py` tenia tres hex a la llista de **«crom del sistema»** (top bar + menú
lateral) que no compten com a incompliment. Dos eren de la **top bar**, que ja ha passat
conformitat i no en fa servir cap. Deixar-los era pitjor que inútil: **qualsevol pantalla que els
pintés quedava absolta per una excepció que ja no li pertocava** — i va passar, amb les quatre
vores de `ui/Card` a `/fittings`, donades per bones. La llista s'escurça a l'únic hex que segueix
sent del menú lateral. **Una excepció que sobreviu al seu motiu és una tapadora.**

## B4 · Documents — `/disseny/documents` · B5 · Fitxa tècnica — `/fitxa-tecnica` (commit 254)

Dues pantalles petites al mateix commit perquè comparteixen exactament el mateix defecte
d'estructura i el mateix remei.

### B4 · Documents

És un **placeholder** (`DissenyPlaceholder`): la pàgina real arriba en sprints posteriors. Una
pantalla sense contingut **té estructura igualment** (§8b: «de dalt a baix, TOTA pantalla del
producte»), i és on més es nota si no la té — aquí no hi ha res que distregui de la seva absència.

🚨 **El títol no tenia mida.** `var(--fs-title)` **no existeix a `:root`** (el token de la casa és
`--fs-h1`): la declaració queda invàlida al càlcul, la mida cau a la de l'agent d'usuari per a un
`h1` —2em, **32px**— i el que es veia era un títol un terç més gran que el de qualsevol altra
pantalla. És germà del `var(--bg, #faf9f7)` de Planificació, i **pitjor**: allà el fallback amagava
el forat, aquí no n'hi havia i el tapava el navegador. **Cap de les dues es veu llegint; totes dues
es veuen mesurant.**

També: cap menú de pantalla (i per tant cap manera de tornar enrere que no fos el menú lateral),
icona en `--gold`, i la frase de «properament» en `--text-muted`. Ara: barra amb **només la
fletxa** (§8b.2), identitat 22/500, i la frase com a estat buit de la casa (§8c).

### B5 · Fitxa tècnica — **NOMÉS crom**, com mana el brief

| Superfície | Què s'hi ha fet |
|---|---|
| `pages/TechSheetEntry.jsx` (la porta) | menú de pantalla amb només la fletxa · identitat · l'avís d'error i el bloc de «no autoritzat» passen a la forma de la casa (radi, vora d'1px, `--err-bg`) · el botó «obrir en consulta» és una **PORTA** (§5.3 → `botoSec`), no un botó daurat · el `padding` arrel duplicat se'n va |
| `components/assets/{AssetNavigator,FileList}.jsx` | 41 substitucions de token: `--border`, `--gray-l`, `--text-muted`, `--gray`, `--white`, `--bg-card`, `--gold-pale`, vores de `0.5px`, radis literals |
| `pages/TechSheetEditor.jsx` | **NOMÉS el mapa `COL`** (v. sota) + tres literals que se li havien escapat |

**Per què tocar `COL` és exactament «només crom».** L'editor ja tenia separades les dues paletes:
`COL` és el **DOM** (on `var()` resol) i `KONVA_COL` és el **canvas** (literals, perquè Konva no
resol `var()`). Tocar `COL` conforma la closca sencera sense acostar-se ni al llenç ni al pipeline
de PDF, que és el que el brief demanava. `KONVA_COL` **no s'ha tocat**.
Dins de `COL`: `--gold-pale` (**ELIMINAT**) → `--sel` · `--border` i `--text-muted` (**DEPRECATS**)
→ `--line` i `--text-soft` · `--white`/`--bg-card` → `--panel` · i el fons de treball, que anava a
`--gray-l` **perquè era el que el `<main>` pintava** —el comentari ho deia— passa a `--bg-page`,
que és on el `<main>` ja va anar al bloc B: **el motiu escrit apunta ara al token nou**.

### 🚩 Anotat, NO tocat (fitxa tècnica)

1. **`COL.gold` segueix sent l'accent de les accions principals de l'editor**, i la §5 diu que la
   primària és blava. Canviar-ho és tocar la jerarquia d'acció d'un editor complet, no crom.
2. **`COL.charcoal`** (capçalera fosca de secció, compartida amb el Taller de Patró): la §1 no té
   cap superfície fosca. És una decisió cross-superfície amb acta pròpia; es reporta.
3. L'editor **conserva la seva pròpia capçalera** i no hi entra el `PageMenu`, **pel mateix motiu
   que A9 va donar per a `FittingDetail`**: és una superfície d'editor a pantalla completa.

---

## 🚨 EL BADGE NEUTRE TENIA DUES DEFINICIONS (commit 254)

Trobat per la sessió 2 en estrenar la bidireccional contra `NORMA_LLISTA_canonica.html` — **la
primera vegada que la canònica verifica una pantalla que no és Models**, que és justament el que
la §8e diu que ha de passar.

```
maqueta  .b.neutral        → --bg(-page) + --ink-soft   + --line
Models.jsx `badgeNeutre`   → --bg-page   + --text-soft  + --line   ← casa amb la maqueta
ui/Badge  variant `gray`   → --sel       + --text-main  + --line   ← NO casava
```

**Per què no s'havia vist mai:** la graella de `/models` **no pinta cap badge d'estat** (la
columna ESTAT hi és buida esperant el Kanban i la FASE és text pla, §8e). La bidireccional d'A5
**no va comparar `.b.neutral` amb res**. El lot comercial és el primer que els pinta de debò.

**Resolució: mana la maqueta, i la NORMA hi va a favor.** La §1 reserva `--sel` a la SELECCIÓ
(«fila/contenidor triat, sempre amb filet d'or»). Un badge d'estat sobre `--sel` **li roba el
significat**: dins d'una fila triada —que ja és `--sel`— hi desapareix a sobre, i dins d'una fila
normal diu «triat» sense ser-ho. `ui/Badge` passa a `--bg-page` + `--text-soft` + `--line`.
Toca **21 fitxers**.

🚩 **Pregunta oberta per a Agus:** la variant `gold` comparteix el mateix fons `--sel` (el bloc B
la va ratificar explícitament així, i el seu filet `--gold-border` la distingeix). **No s'ha
tocat.**
🚩 **`Models.jsx` conserva una còpia local `badgeNeutre`** que ara és redundant. És pantalla
conformada i **intocable en aquest lot**: matar-la és una línia el dia que es decideixi.

## Esmena a CINC maquetes · el badge taronja no complia AA

`.b.warn` pintava el TEXT en `--warn` (#ff9942) sobre `--warn-bg`: **1.86:1**. La §1b(d) va
partir el token precisament per això (`--warn-state` per a vores i marques de dada; `--warn-ink`
per al text, 5.32:1) i la pantalla ja ho feia des del bloc B: **la maqueta s'havia quedat al valor
anterior i la bidireccional donava com a desviació de la PANTALLA un defecte d'ella**. Esmenades
les cinc a la font, amb acta. La forma ratificada per Agus (fons clar + text taronja + filet fi)
no canvia; només el to del text, perquè es llegeixi.

## L'auditoria absolia un color que ja no li pertocava — i va caçar-ne un de real

En escurçar `CROM` a un sol hex (v. B3), la correguda següent va treure **12 vores `--border`
(deprecat) a `/fitxa-tecnica`**, dins de l'`AssetNavigator`, que fins llavors quedaven absoltes.
Corregides. **12 pantalles → 0 incompliments** amb la paleta escurçada, i la bidireccional sencera
→ **0 desviacions** llevat de la declarada (la tinta de la fletxa d'arrel).

## B6 · Configuració general · B7 · Usuaris i rols · B8 · Calendari d'empresa (commit 256)

Les tres pantalles del mòdul **Sistema** que ja eren al brief. Cap gest canvia a cap.

### Cens dada → endpoint

| Pantalla | Què es pinta | D'on surt |
|---|---|---|
| B6 | fitxa del tenant · logo | `GET/PATCH /api/v1/tenant-config/` · `POST …/logo/` |
| B6 | **unitat de mesura · norma de referència** | **`/vocabulari/` → `unitats_mesura` · `normes_referencia` (NOUS)** |
| B7 | matriu d'usuaris · permisos · tasques | `users/` · `taskTypes/` (+ `permisos.grant/revoke`) |
| B7 | **columnes de la matriu · rols** | **`/vocabulari/` → `capacitats` · `rols` (NOUS)** |
| B8 | horaris i festius del tenant | `GET/PUT /api/v1/company-calendar/` |

### CENSAT-PENDENT exposats en aquest tram (4)

`unitats_mesura` · `normes_referencia` (`TenantConfig`) · `capacitats` · `rols`
(`accounts/capabilities.py`). Les dues primeres **la capçalera del mòdul de vocabulari les tenia
censades amb el motiu escrit** —«l'ordre les condicionava a que Mesures/Fitting les PINTESSIN, i
no les pinten»—: la condició s'ha complert per l'altra banda, la pantalla que SÍ que les pinta és
la de Configuració general i passa conformitat ara.

⚠️ **`capacitats` va obligar a canviar la FONT, no només a publicar-la.** `ALL_CAPABILITIES` és un
`frozenset` i **un `frozenset` no té ordre**; l'ordre de les capacitats és l'ordre de les
**columnes de la matriu de permisos**, o sigui DADA. S'hi afegeix la tupla `CAPABILITIES` (de la
més bàsica a la més àmplia) i el `frozenset` se'n deriva: una sola llista. Amb la còpia local que
el client tenia, el dia que hi entrés una capacitat nova **la matriu no l'hauria ensenyada mai**.
`ROLES` es deriva de `ROLE_CAPABILITIES` (els `dict` conserven l'ordre d'inserció).
Ni capacitats ni rols tenen **etiqueta** al backend: la pantalla els tradueix per codi des de
sempre, i s'emeten amb `etiqueta` = codi perquè la forma de l'endpoint no canviï.

### Desviacions trobades i corregides

| Pantalla | Què | Ara |
|---|---|---|
| totes 3 | cap menú de pantalla | §8b (sense seccions: només la fletxa) |
| B6 | el títol de pàgina anava a `--fs-h2` (18) | `--fs-h1` 22/500 (§2) |
| B6 | el rètol de camp era **cos a 12 en MAJÚSCULES** | `--fs-label` 10 amb tracking (§2: 12 en majúscules és la mida d'un VALOR, no d'una etiqueta) |
| B6 · B8 | «Desar» amb `opacity` en desactivar-se; a B8 a més **daurat ple** | primària blava + `apagat` (§5.1 · §5.7) |
| **B7** | **LA PANTALLA SENCERA ERA TARONJA**: `--warn-bg` de fons a la columna fixa, a les capçaleres del bloc de tasques i a TOTES les etiquetes de formulari; `#ba7517` de filet, que no és a cap paleta | la columna fixa va al fons de pàgina (que és el que la distingeix del panell blanc que hi llisca per sota) i els filets a `--line`. **La §1 reserva el taronja a la DADA**; aquí no hi havia cap dada taronja, hi havia una pantalla pintada de taronja |
| B7 | «Nou usuari» era un botó **daurat ple** a l'extrem de la barra de filtres | puja al menú i hi perd el color (§8e); i deixa de barrejar-se amb els filtres |
| B7 · B8 | «sense accés» amb icona de 32px i `--gray` | frase `--text-faint` cursiva (§8c) |
| **B8** | **els set noms de dia eren rètols en majúscules a 12px** | `--fs-label` 10 — **ho va trobar la mesura**: 7 rètols per sobre del sostre |
| totes 3 | `--gray-l`, `--gray`, `--border`, `--text-muted`, `--white`, `--bg-card`, `0.5px`, radis literals, pes 300 | l'escala de la norma |

## CODA · el `badgeNeutre` de `Models.jsx` i EL TRI-ESTAT DEL VEREDICTE (commit 257)

Dues codes autoritzades per Agus, i totes dues surten del tancament del lot comercial.

### 1 · La còpia local mor

`Models.jsx` (pantalla conformada, A5) es va quedar una definició pròpia del badge neutre. Avui
és *redundant però correcta*; el risc no és avui, **és el dia que algú toqui `ui/Badge` i no
sàpiga que hi ha una segona definició que no se n'assabentarà**. Substituïda pel component.

⚠️ **I la substitució hauria perdut el TOOLTIP en silenci.** `ui/Badge` no acceptava `title`, i
la còpia local en tenia un —el badge és una abreujació («SET 2/3») i el text sencer viu al
tooltip—. Un tooltip que desapareix no trenca res i no el veu ningú fins que algú el busca.
`ui/Badge` el reenvia ara.

### 2 · EL VEREDICTE DE QA PASSA A TRES COLUMNES

**`N mesurats · M desviacions` amagava la tercera possibilitat, que és la pitjor**: el cas que
**no toca res**. `_mesura()` ja distingia els dos casos —torna `None` quan el selector no troba
res— i el que faltava era que el veredicte ho separés. Ara:

```
──────── 14 CASEN · 0 DESVIEN · 1 NO TOQUEN RES (de 15 casos) ────────
   ⚠️ ELS QUE NO TOQUEN RES NO SÓN VERDS: SÓN SILENCI.
   · A5 · badge NEUTRE (la marca de conjunt) · NO MESURAT a la pantalla (…)
```

**I ha justificat el seu preu a la primera correguda.** La passada d'A5 va sortir **0 CASEN · 0
DESVIEN · 15 NO TOQUEN RES**: els quinze morts de cop. Amb el veredicte antic això s'hauria
imprès com **«0 desviacions»** i hauria passat per verd. La causa era el **token caducat a mitja
sessió** (tapadora núm. 2): l'app queia a `/login` i es mesurava una altra pantalla.
Amb un token fresc: 14 casen · 0 desvien · **1 no toca res**, i aquest un s'explica —**cap model
de cap dels dos tenants té `garment_set`** (0/1 a `fhort`, 0/51 a `los`), o sigui que el
`SetBadge` no és assolible amb les dades vives. Limitació declarada, no defecte.

### LES CINC TAPADORES, tal com queden

| # | Tapadora | Com es veu | Com es tanca |
|---|---|---|---|
| 1 | **Bundle ranci** | verd o vermell sobre codi que ja no existeix | mirar la data del `dist` |
| 2 | **Token caducat** | l'app cau a `/login` i mesures una altra pantalla | correguda de tancament sencera + el tri-estat, que ho delata |
| 3 | **Excepció caducada** | el defecte hi és i l'eina l'absol | revisar *per què* existeix cada exempció |
| 4 | **Cas que no toca res** | verd perquè el selector no troba l'element | el tri-estat del veredicte |
| 5 | **Un sol motor** | la mesura passa on l'usuari no mira | v. §8b-quater(2): `:has()` a Chromium ✓, Firefox ✗ |

Les cinc tenen la mateixa forma: **el verd no vol dir el que sembla.** I cap es veu llegint codi.

## AMPLIACIÓ DE LOT · la secció SISTEMA sencera (Agus 09/08) — commit 258

| Pantalla | Ruta | Estat |
|---|---|---|
| Catàleg de tasques | `/task-types` | ✅ conformada aquí |
| El meu perfil | `/perfil` | ✅ conformada aquí |
| Recursos (P7, gate `brand_configure`) | `/recursos` | ✅ conformada aquí |
| **Safata d'encàrrecs** | `/encarrecs` | ✅ **ja la va conformar la S2** (commit 212) — **verificada, no refeta** |

### Cens dada → endpoint

| Pantalla | Què es pinta | D'on surt |
|---|---|---|
| Catàleg de tasques | `code` · `name` · `default_order` · `active` | `GET /api/v1/task-types/?ordering=default_order` (**ReadOnlyModelViewSet**: escriure-hi és 405) |
| Perfil | fitxa de l'usuari · inicials · color | `GET /api/v1/me/` |
| Perfil | canvi de contrasenya | `POST` del mateix mòdul |
| Recursos | vincles del Brand amb els seus Studios | `GET /api/v1/…/recursos/` (llista de `TenantLink`) |
| Recursos | estat del vincle | `estat` + `/vocabulari/` → `estats_vincle_tenant` |
| Recursos | alta amb token · aturar/reactivar/revocar | accions del mateix mòdul (gate `brand_configure`, **intacte**) |

### Desviacions corregides

- **Catàleg de tasques**: cap menú · badge d'estat pintat a mà **sense vora**, amb `--gray-l` de
  fons i `--gray` de tinta → `ui/Badge` · caixa i filets a l'escala de la norma.
  **G9 (llei vigent) verificada i NO tocada**: la pantalla és de consulta pura, referencia per
  `code` i no escriu res; el ViewSet és read-only. Cap writer nou.
- **Perfil**: cap menú · **DOS botons daurats plens** (tancar sessió i canviar contrasenya).
  Tancar sessió **no és l'acció primària** —el que has vingut a fer aquí és canviar la
  contrasenya— i tampoc és destructiva: és una PORTA de sortida → secundària, i deixa d'ocupar
  la línia sencera. La de contrasenya sí que és la primària → blava, amb `apagat` en desactivar-se.
- **Recursos**: cap menú · «Nou vincle» era un botó blau a la capçalera → **puja al menú i hi
  perd el color** (§8e), i **només per a qui té la capacitat: el gate no es toca** · el codi de
  l'Studio anava en **daurat a pes 700** (marca pintant una dada, i 700 no és cap dels tres
  pesos) → tinta principal a 600 · el badge d'estat, pintat a mà sense vora i amb `--warn` de
  tinta (1.86:1) → `ui/Badge`.

### Tres components de `ui/` conformats amb aquestes pantalles (toquen tot el producte)

- **`ui/Table`** — la taula simple de consulta (7 consumidors fora del lot comercial): th a
  `--gray`/pes 400/tracking .1em → §2 · filets de mig píxel → `--line`/`--line-soft` · hover de
  fila en `--gray-l` (gris fred) → `--sel` · estats de càrrega i buit en caixa de 3rem → §8c.
- **`ui/Center`** — l'estat de pàgina que munten **30+ pantalles**: era una caixa de 3rem
  centrada en `--gray` (3.64:1), i el centrat feia que un missatge d'una línia semblés una
  pàgina d'error → frase `--text-faint` cursiva (§8c).
- **`ui/Badge`** — hi entra `title` (v. la coda del commit 257).

### 🚩 Anotat, NO tocat

`ESTAT_VARIANT` de Recursos **es queda**: és un mapa de PELL indexat pel codi que arriba, no una
llista de valors possibles — el mateix criteri que `FASE_COLORS` del Gantt. Que les seves claus
coincideixin amb una enumeració publicada no el converteix en vocabulari.

## B9·B10·B11 · Configuració inicial · Import massiu · Size Map Setup (commit 259)

Els tres wizards del lot. Cap gest, cap pas, cap validació canvia a cap.

### 🚨 B9 · La Configuració inicial NO TENIA i18n

**Cap** cadena de cara a l'usuari passava per `t()`: **vint literals catalans escrits a dins**
(«Benvingut a FHORT Textile Tech», «Guardar i continuar →», «Nom de l'empresa *»…). És la porta
que el `CLAUDE.md` posa com a guardià de frontend, i era **la pantalla on més mal fa: és la
PRIMERA que veu un tenant nou**, i un estudi anglès o castellà l'obria en català sense cap
manera de canviar-ho. 22 claus noves amb paritat ca/en/es.

**I la paleta era una altra**: nou hex literals fora de la casa (`#f0f9f0`, `#fff0f0`, `#c0dd97`,
`#f09595`, `#3b6d11`, `#a32d2d`, `#f5e6d0`, `#f5f0ea`, `#c8b89a`) — entre ells **el verd i el
vermell ANTERIORS a l'alineació del semàfor de la §1b(a)**, que el bloc A ja va migrar a tot el
producte. Aquesta pantalla se n'havia quedat fora perquè no els llegia dels tokens: se'ls havia
escrit.

**§6 · el wizard no tenia stepper.** Quatre passos i cap manera de saber on eres. La seqüència
**no se l'inventa aquest tram** —ja era al codi (`step` 0→1→2→3) i és la que el backend
serveix—; el que hi entra és la FORMA que la norma li dona: FET (verd amb ✓) · ACTUAL (`--sel` +
filet d'or) · DISPONIBLE (blanc + `--line`) · BLOQUEJAT (tènue).
I les unitats, que eren `['CM','INCH']` al client, surten de `/vocabulari/` → `unitats_mesura`.

### B10 · Import massiu

| Què | Abans | Ara |
|---|---|---|
| Sortida | una **`✕ Cancel·lar` de text pla** a l'extrem de la capçalera, i **cap altra** | menú de pantalla amb la fletxa a `/models` + la `✕` com a terciària (cancel·lar i tornar no són el mateix gest) |
| Stepper | cercle **daurat ple** amb tinta blanca (**3.44:1**) i un `✓` tipogràfic | §6: FET `--ok-bg`+check · ACTUAL `--sel`+filet d'or · DISPONIBLE blanc+`--line` |
| Primària | **daurat ple** amb tinta blanca | blava (§5.1), amb `apagat` en desactivar-se |
| «Ghost» daurat | botó de vora daurada i tinta daurada | secundària de la casa — **la §5.4 jubila el ghost daurat com a botó** |
| Avís d'error | `#fee` / `#fcc` / `#c00` | `--err-bg` + filet i tinta `--err` (§1) |
| `GOLD` | **`var(--gold, #c27a2a)`** — una `var()` amb **fallback literal** | fora |

⚠️ El fallback literal aquí **no s'usava mai** (el token existeix). Es diu igualment perquè és
**el mateix patró** que a Planificació amagava un token INEXISTENT (`var(--bg, #faf9f7)`): un
fallback que ningú no veu és una xarxa que no se sap si aguanta.

### B11 · Size Map Setup — 🛑 i el titular és un altre

| Què | Abans | Ara |
|---|---|---|
| Badge de confiança del matching | mapa amb **4 hex literals** i **l'etiqueta EN CATALÀ escrita a dins** (`label: 'alta'`, `'sense match'`) | `ui/Badge` + clau i18n |
| MEDIUM i LOW | tots dos en **daurat** (marca fent de semàfor) | taronja d'avís; la distinció la fa l'etiqueta, que és qui la sap dir |
| Acció «Nou run» | botó blau a la capçalera | puja al menú i hi perd el color (§8e) |

🛑 **`SizeMapSetup` NO TÉ RUTA.** El seu `export default` **no el munta ningú**: `App.jsx` no en
declara cap `<Route>` i l'únic consumidor de tot `src/` és `SizeAuthoringDrawer`, que n'importa
**el `Wizard`** (i el munten la Size Library i els jocs de regles). O sigui que **la pantalla-llista
és codi mort** i el que és viu és el wizard de dins.
Conseqüència pràctica: la conformitat del **wizard** (que és el gruix del fitxer, i el que porta
el badge de confiança) **arriba a l'usuari**; la de la capçalera-llista i el seu menú de pantalla,
**no**. No s'esborra —els esborrats són decisió d'Agus— i **no s'audita per ruta**: posar-hi una
ruta inventada hauria mesurat un 404. Precedent de la casa: `GraduacioPanel`.

### El que la mesura va treure a `/models/importar-colleccio`

Dos incompliments que **no eren de la pantalla sinó del `CustomerSelector`** que hi munta:
`--gray-l` de vora al select (àlies de farciment fent de vora, en gris fred) i **`--warn` de
tinta I de vora al botó «+ Nou client»** — el taronja del SEMÀFOR fent de botó, quan la §1 el
reserva a la dada. Passa a secundària de la casa. I un rètol «Client» a 12px en majúscules
(§2: un rètol va a 10; 12 en majúscules és la mida d'un valor).
⚠️ `CustomerSelector` és el component de frontera amb el lot comercial: el canvi és **pell pura**,
cap prop, cap `onChange`, cap contracte del modal.

### `ui/PageMenu` · es tanca un mode de fallada silenciós (avís de la sessió de fitxa tècnica)

`FORAT_CROM` és un node de mòdul: existeix des que es carrega el bundle, i qui l'enganxa al
document és el Shell. **Hi ha rutes FORA del Shell** (l'editor de fitxa tècnica, el taller de
patró); si una d'elles muntés `PageMenu`, el portal aniria a un node desenganxat i **la barra no
es pintaria, en silenci** — el mateix mode de fallada que el `:has()` del §8b-quater(2). Ara es
comprova `isConnected` **després** del muntatge (no durant el render: dins del Shell el pare fa
`commit` després que els fills hagin renderitzat, i comprovar-ho al render pintaria la barra al
mig de la pàgina una passada). Cas normal sense parpelleig; cas anòmal, **degradació visible**.

## 🛑 STOP DE LOT · S1 (lot tècnic + secció Sistema + compartits + backend)

### Les 24 pantalles, i on són

| # | Pantalla | Ruta | Commit |
|---|---|---|---|
| 1 | Desenvolupament (la home) | `/` | 251 |
| 2 | Planificació + Gantt + 4 panells + Registre | `/planificacio` | 252 |
| 3 | Fittings | `/fittings` | 253 |
| 4 | Documents | `/disseny/documents` | 254 |
| 5 | Fitxa tècnica (porta + crom de l'editor) | `/fitxa-tecnica` | 254 |
| 6 | Configuració general | `/configuracio/general` | 256 |
| 7 | Usuaris i rols | `/configuracio/usuaris` | 256 |
| 8 | Calendari d'empresa | `/configuracio/calendari` | 256 |
| 9 | Catàleg de tasques | `/task-types` | 258 |
| 10 | El meu perfil | `/perfil` | 258 |
| 11 | Recursos | `/recursos` | 258 |
| 12 | Safata d'encàrrecs | `/encarrecs` | **S2 · 212** (verificada, no refeta) |
| 13 | Configuració inicial | `/onboarding` | 259 |
| 14 | Import massiu | `/models/importar-colleccio` | 259 |
| 15 | Size Map Setup (el `Wizard`; la llista és codi mort) | — | 259 |
| — | + les 9 pantalles ja conformades dels blocs A i B, re-mesurades senceres | | |

### Les tres eines, a la correguda de tancament

| Eina | Resultat |
|---|---|
| `qa_auditoria_computats.py` · **27 rutes** (24 d'aquest lot + 3 de la sessió de patrons) | ✅ **0 incompliments** |
| `qa_bidireccional.py` · **56 casos, sencera i sense filtres** | **53 CASEN · 1 DESVIA · 2 NO TOQUEN RES** |
| `qa_8bquater_crom.py` · 5 rutes × 2 tenants | ✅ **0 incompliments** |
| `npx eslint src` | ✅ 0 errors |
| `npm run build` | ✅ net i **desplegat** (`frontend/dist` és el que serveix staging) |
| `manage.py check` | ✅ net |
| **La suite** · `fhort.tasks fhort.models_app fhort.accounts fhort.tenants` | ✅ **966 tests · OK · 0 errors · 0 fallides** (4.499 s = **75 min**) |

**L'única desviació és la declarada** (la tinta de la fletxa d'arrel, que espera Agus). **Els dos
casos sense mesura estan explicats**: l'estat «cap capa declarada» d'A2 —que el bloc A ja va
deixar anotat com a no assolible amb les dades del run que l'arnès obre— i el badge de conjunt
d'A5: **cap model de cap dels dos tenants té `garment_set`** (0/1 a `fhort`, 0/51 a `los`).

### El vocabulari: de 6 llistes a 27

`/api/v1/vocabulari/` ha passat de **6** a **27** llistes en aquest lot. **21 enumeracions de
domini** han sortit del client. Les del lot tècnic: `temporades` · `unitats_mesura` ·
`normes_referencia` · `capacitats` · `rols`. Les altres 16, per al lot comercial.

**Dues van obligar a canviar la FONT, no només a publicar-la:**
- **`capacitats`**: `ALL_CAPABILITIES` és un `frozenset` i **un `frozenset` no té ordre** — i
  l'ordre de les capacitats és l'ordre de les COLUMNES de la matriu de permisos, o sigui DADA.
- **`estats_locals_encarrec`**: no surt de cap `choices` (és una COMPARACIÓ), i els dos literals
  vivien inline en quatre punts de `federation_service`.

### LES CINC TAPADORES · el verd que no vol dir el que sembla

Totes cinc trobades avui entre les tres sessions. **Cap es veu llegint codi.**

| # | Tapadora | Com es veu | Com es tanca |
|---|---|---|---|
| 1 | **Bundle ranci** | verd o vermell sobre codi que ja no existeix | mirar la data del `dist`; `FTT_QA_DIST` per mesurar sense publicar |
| 2 | **Token caducat** | l'app cau a `/login` i mesures una altra pantalla | correguda sencera + **el tri-estat, que ho delata** (15/15 morts de cop) |
| 3 | **Excepció caducada** | el defecte hi és i l'eina l'absol | revisar *per què* existeix cada exempció |
| 4 | **Cas que no toca res** | verd perquè el selector no troba l'element | **el veredicte de tres columnes** |
| 5 | **Un sol motor** | la mesura passa on l'usuari no mira | `:has()` ✓ a Chromium, ✗ a Firefox < 121 → §8b-quater(2) |

I dues variants seves que van sortir al tancament:
- **L'element que NO HI ÉS**: `SessioActiva` és crom **global** però només es pinta amb una tasca
  oberta. El banc no en tenia cap i les 24 pantalles donaven 0 amb un element de crom global
  **sense mesurar mai**. Quan una altra sessió en va obrir una, va aparèixer a totes alhora.
- **El selector que es mou**: el cas d'A1 anava per `div[style*="sticky"] >> nth=0` i, en fer del
  crom un sol bloc enganxat, va passar a mesurar **la top bar** i a acusar la pantalla equivocada
  (5 desviacions falses).

### `var()` QUE NO EXISTEIXEN — el patró, batejat

Tres al lot, i **cap fallava**: una `var()` inexistent no peta, cau a l'heretat i **es veu bé per
accident**.

| On | Què | Efecte real |
|---|---|---|
| `DissenyPlaceholder` | `var(--fs-title)` | el títol queia als **32px de l'agent d'usuari** per a un `h1` |
| `Planning` | `var(--bg, #faf9f7)` | **amb fallback**: pinta un crema que ningú ha decidit i **cap eina el veu** |
| `IssueDateField` | `var(--text)` | el color queia a l'heretat i es veia negre |

### El creuament de claus · publicades ↔ consumides (idea de la sessió comercial)

`GET /vocabulari/` → conjunt de claus, creuat amb un `grep` de les que el client demana. Detecta
les **dues** direccions, i cap es veu llegint codi.

| Direcció | Resultat |
|---|---|
| 🔴 **demanada i NO publicada** (select buit en silenci; **sempre és un defecte**) | ✅ **cap** |
| 🟠 **publicada i sense consumidor** (pregunta, no veredicte) | **4** |

Les quatre, dites sense embuts perquè **dues són meves i van contra la política que el mateix
mòdul del vocabulari té escrita** («afegir-les totes ara seria publicar vocabulari que ninguna
pantalla conforme consumeix»):

- `origens_encarrec` i `tipus_linia_albara` — **publicades i no llegides per ningú**. Venien del
  cens del lot comercial, que ja avisava que eren de prioritat baixa («si les deixes fora, ho dic
  al report i no invento res»). **Les vaig publicar igualment**: era més barat fer-ho d'una
  passada, i el preu és aquest. No es retiren (retirar-les podria trencar feina pendent), però
  **el dia que algú les canviï no hi ha cap pantalla que ho delati**.
- `estats_vincle_tenant` i `origens_alias_pom` — **surten només a COMENTARIS** (a `Recursos.jsx` i
  a `CustomerDetail.jsx`), explicant que el mapa de pell local **no és** l'enumeració. El
  raonament és bo; el consum, no hi és. Cas de frontera: la pantalla decideix la pell pel codi
  que ARRIBA i no necessita la llista. **Dit, no resolt.**

### El protocol de mesura, tal com queda tancat

Tres eines, i **tres asserccions que abans no hi eren** — cadascuna tanca una tapadora:

| Assercció | Qui la va proposar | Quina tapadora tanca |
|---|---|---|
| **La sessió és viva** (`GET /me/` abans i després de la correguda) | sessió de fitxa tècnica/patrons | **2 · token caducat** |
| **El veredicte és de tres columnes** (`casen · desvien · NO TOQUEN RES`) | sessió comercial | **4 · cas que no toca res** |
| **El senyal de pantalla** (`data-ftt-screen`; sense senyal es CRIDA, no es mesura) | sessió de fitxa tècnica/patrons | **4-bis · la ruta que no és la que creus** |

🚩 **DEUTE CONEGUT, dit i no fet**: el senyal de pantalla és **opcional a la tupla** i els meus
24 casos encara no en porten. Posar-los és additiu i no trenca res, però és feina nova al
tancament: **queda escrit, no mig fet.** Sense senyal, una ruta meva que canviés de destí es
mesuraria contra una altra pantalla i donaria el mateix zero.

⚠️ I el senyal va justificar el seu preu de seguida, però per una tapadora que no era la seva:
la primera correguda després d'afegir-lo va donar **3 incompliments** —`🛑 SENYAL ABSENT` a les
tres rutes de patrons— i **era cert**: les àncores eren al codi i **no al bundle**. Sense el
senyal, tres zeros que hauria donat per bons. **Tapadora 1 caçada per l'eina de la 4.**

### La vora de «un sol builder» (lliçó de mètode, de la sessió de patrons)

Amb tres sessions escrivint al mateix disc, la regla **«un sol builder»** és bona i s'ha
mantingut tot el lot. Però té una vora que va aparèixer al final: **si no construeixes, no
mesures el que has escrit.** Les àncores de la sessió de patrons eren al codi i no al bundle
precisament perquè aquella sessió, correctament, no publicava.

La sortida no és trencar la regla: és `FTT_QA_DIST`, que mesura contra un `outDir` de proves
**sense publicar**. Existia i no es va fer servir a l'última correguda. **La regla es queda; el
que s'aprèn és que «no publico» i «no mesuro» no poden ser la mateixa decisió.**

### LA SISENA TAPADORA · el canvi que no mou cap valor mesurat però mou la pàgina

Va sortir al final, amb una petició de la sessió de fitxa tècnica: fer del `<main>` una columna
flex perquè l'editor a pantalla completa pogués omplir l'alçada restant. **Les dues sessions vam
raonar que era zero risc** amb un argument correcte en tot el que deia (un fill de bloc s'estira;
amb un sol fill arrel no hi ha marges amb què col·lapsar) — i **incomplet en el que no deia**.

`ops/qa/qa_diff_layout.py` (nou) va prendre una foto geomètrica de les 26 rutes amb el canvi i
sense, aïllat de debò (base neta → build → foto; canvi → build → foto): **8 de 26 es movien.**

| Ruta | Què |
|---|---|
| A6 · A7 · A8 · A10 · C2 | el primer fill del `<main>` **baixa 24px**: el `<div>` de marge negatiu del menú **deixa de pujar** com a element flex |
| A3 i els dos wizards | la caixa centrada (`maxWidth` + `margin: 0 auto`) perd l'`align-items: stretch` i cau a mida de CONTINGUT: **1312 → 1064 · 600 → 505.7 · 920 → 561.6** |
| C1 | l'editor creix 67px i el document desborda 2 |

**Cap dels vuit canvia un sol color ni una sola mida de lletra: les tres eines li haurien donat
verd.** El canvi **no entra**; el que entra és `--chrome-h`.

### `--chrome-h` · i per què es MESURA i no s'escriu

L'editor l'ha de poder llegir per fer `height: calc(100vh - var(--chrome-h))`. La pregunta que
calia respondre abans de publicar-la —i la va fer la sessió que la demanava— és **si el bloc de
crom fa sempre el mateix alt**. Mesurat, cinc amplades × tres rutes:

```
1600 → /models 106 · /models/1319 107 · /perfil 106      900 → /models 140 · /models/1319 143
1200 → /models 106 · /models/1319 143                    520 → /models 210 · /models/1319 245
```

**De 106 a 245 px** (el menú porta `flexWrap`). Una constant hauria estat correcta **només en una
finestra ampla**. Es publica en viu amb `ResizeObserver` —i no amb `resize` de finestra, perquè el
bloc també canvia quan canvia el CONTINGUT del menú— sobre `documentElement`, perquè la llegeixi
també el que es pinta per portal. Verificat: 15 combinacions **i el redimensionat en viu** → 0
desacords.

### 🛑 LA SUITE · dues vermelles, i totes dues diuen alguna cosa

Primera correguda de `fhort.tasks fhort.models_app fhort.accounts fhort.tenants`: **966 tests ·
1 fallida · 1 error**. **Correguda de tancament, després dels dos remeis: 966 tests · OK · 0
errors · 0 fallides** (75 minuts).

⏱️ **La suite d'aquestes quatre apps triga 75 minuts** i el gruix és muntar els esquemes de
tenant, no córrer les proves — el mateix ordre de magnitud que el bloc B ja va deixar anotat per
a `pom+models_app+fitting`. **No es mata amb timeouts curts**, i `--keepdb` menteix (v. el report
del bloc B: 73 errors, cap real).

**1 · FAIL `test_les_sis_llistes_hi_son_i_van_en_lordre_del_model` — MEVA, i la prova tenia raó
a mitges.** Comprovava `assertEqual(set(d.keys()), …)`: «les sis hi són» escrit com a **«NOMÉS hi
ha aquestes sis»**. L'endpoint ha passat de 6 a 27 llistes seguint la política escrita a la
capçalera del seu propi mòdul (cada enumeració s'hi publica quan la SEVA pantalla passa
conformitat) — o sigui que **la prova prohibia el creixement que el disseny preveu**. Passa a
subconjunt + una comprovació NOVA que abans no hi era: **cap llista pot arribar buida** (publicar
una clau sense membres és pitjor que no publicar-la; el client no distingeix «no n'hi ha» de «no
ho sé»). *Una prova que impedeix el que el disseny preveu no és una xarxa: és un cable.*

**2 · ERROR `test_additiu_clau_ambigua_al_desti` — NO és meva, i portava mesos vermella.**
`IntegrityError` sobre `uniq_pommaster_codi_client_ci`: la prova ha de fabricar dos POMs amb el
mateix `codi_client` i **la BD ho rebutja des de la migració `pom/0075`** (bloc A). El bloc A ja
va caçar aquesta família i li va fer l'eina —`pom/catalog_testing.desactiva_unicitat_codi_client()`,
amb el motiu escrit— però **la va aplicar només a `fhort.pom`**: aquesta viu a `fhort.tasks`, una
app que aquell bloc **no va córrer**. **Una prova vermella en una app que ningú corre és una
prova que no existeix.** Remei: el de la casa, sense inventar-ne cap.

### DUES TRAMPES DE MÈTODE que ens han caçat a totes les sessions

**1 · L'`opacity` que sobreviu a una migració de color.** Quan una coda canvia el COLOR d'un
botó, es mira el color — i **l'`opacity` que hi havia a sota no se'n va sola**. La §5.7 la
prohibeix amb el motiu escrit: apaga TAMBÉ el text i el deixa per sota d'AA, i el que diu un
botó deshabilitat és justament el que ara no es pot fer.
Trobada **tres vegades** avui, i cap per relectura: a `ui/Modal` (commit 250), als dos botons
d'`UsersRoles` que la ratificació del daurat va portar a blau (270), i a «Exportar PDF» de
l'editor .ftt —que la va posar la mateixa sessió tres hores abans i no la va veure en canviar
el color—. En repassar el meu lot amb aquest criteri n'ha sortit **una quarta**: les etiquetes
de tasca d'`UsersRoles` per a un admin (`opacity: 0.6`). Aquí no hi ha fons que baixar (és una
etiqueta damunt del panell) i mana la §1: **`--text-faint`**, la mateixa resolució que el bloc B
va donar al menú de pantalla.
**I la regla té QUATRE remeis, no un** — el cens complet el va fer la sessió de patrons amb
aquest criteri i li'n van sortir ~20 llocs més:

| | Cas | Remei |
|---|---|---|
| **A** | botó **amb fons** | `apagat` (§5.7: baixa el fons) — mecànic |
| **B** | **text sense fons** | l'escala de tintes (`--text-faint`) — és el cas d'`UsersRoles` |
| **C** | **contenidor OCUPAT** (una fila que s'atenua *mentre treballa*) | ❓ **no és deshabilitat, és EN CURS, i la norma no en té forma escrita** |
| **D** | **regió sencera** (`<fieldset disabled>` amb children arbitraris) | ❓ ni `apagat` (no és un botó) ni una tinta (són molts elements) |

🚩 **C i D són PREGUNTES DE NORMA i van a la taula**, no a un tram: amb només A i B això seria una
escombrada de deu minuts.
🚩 **Tampoc es toca** l'`opacity: 0.45` de `ribbonToolStyle` (≈60 botons d'eina de la cinta):
`apagat` els donaria fons `--bg-page` dins d'una barra d'eines. **És una decisió de com es veu
una eina inactiva, no un descuit.**

⚠️ **I el cens NO es fa per nom de propietat.** La meitat del que surt amb `grep opacity` és de
DIBUIX (primitives Konva, objectes de document, i les dianes de `PaperFlatEditor` a `0.001`), i
un cens per nom se les hauria endut. **Es classifica per QUÈ ÉS cada número, no per com es diu
la propietat** — el mateix parany que els `fontSize` de la fitxa tècnica, i tots dos esperen al
mateix lloc: un fitxer amb llenç.

**2 · El comentari `{/* … */}` com a primer fill d'un `{cond && ( … )}` o d'un `return (`.**
Allà encara ets en context d'EXPRESSIÓ i les claus es llegeixen com un **objecte literal**;
l'error surt com a `Unexpected token` **a la línia SEGÜENT**, no a la del comentari — que és el
que el fa car de trobar. **Quatre vegades avui entre les quatre sessions.** El comentari ha
d'anar FORA, o com a `//` abans del `return`.

### 🚩 A LA TAULA D'AGUS

1. **La fletxa de l'ARREL** — proposta conjunta de dues sessions: la barra es queda i la fletxa
   TAMBÉ, **deshabilitada** (`--text-faint`). Una línia si es vol d'una altra manera.
2. ~~**El daurat ple de l'acció primària**~~ — ✅ **RATIFICAT I TANCAT PER AGUS** mentre aquest
   lot es tancava, en una quarta sessió (commit `57dc3683`): 45 accions amb fons `--gold`
   escrites a mà, **classificades una a una** abans de tocar-les (41 primàries → `--accio`, 4
   secundàries pel §5.3/§5.4, i la resta —selecció, píndoles, toggles d'eina, punts de color,
   steppers— que **no són accions** i es queden). Mesurat: 0 accions amb daurat ple a 28 rutes.
   **Les tres sessions vam encertar deixant-la oberta**: era una decisió de producte i s'ha
   pres una sola vegada per a tot el producte, no pantalla a pantalla.
   🚩 **Residu, corregit aquí**: aquella coda va portar dos botons d'`UsersRoles` (pantalla
   d'aquest lot) de daurat a blau —correcte— però **l'`opacity: 0.6` del deshabilitat s'hi va
   quedar**, i la §5.7 la prohibeix. Passen a `apagat`.
3. **`components/EstatBadge.jsx` és CODI MORT** (zero imports) amb 5 hex literals: candidat a
   esborrar. **`SizeMapSetup`** (l'`export default`) tampoc té ruta.
4. **`Models.jsx` conserva `badgeNeutre`?** No: mort al 257. El que queda obert és si la variant
   `gold` d'`ui/Badge` ha de deixar `--sel` com ha fet la `gray`.
5. **El codi de colors de les 4 columnes del board** (Desenvolupament): la §8e només nomena TRES
   estats i el board en té QUATRE. Dir de quin color és «pausat» és domini.
6. **La VIABILITAT es calcula al client** (Planificació) amb 420 min/dia i dl-dv escrits a mà,
   mentre el Gantt de la mateixa pantalla llegeix el CompanyCalendar. Dues respostes a la
   mateixa pregunta.
7. **19 ViewSets més perden l'`OrderingFilter`** pel mateix patró que `/customers`.
8. **INFRA · `backend/media/` amb directoris `root:root`** i gunicorn com a www-data → 500 a tot
   upload. **El directori del mes és nou cada mes**: arreglar l'agost no arregla el setembre.
   Demana un `umask`/propietari al desplegament, no un `chown` cada trenta dies.

## CODES PER A LA S2 (backend i compartits · commits 250·204, 250·205, 250)

### `/customers` tornava a ordenar — DRF es menjava l'ordre en silenci
`CustomerViewSet` declarava `filter_backends = [DjangoFilterBackend, SearchFilter]`, i això **no
afegeix backends al defecte: els substitueix tots**. El que hi queia era l'`OrderingFilter`.
`pages/Customers.jsx` enviava `ordering=codi` a cada crida i DRF el descartava **sense error ni
avís**; la llista sortia ordenada igualment pel `Meta.ordering` del model, i per això no ho havia
delatat ningú. Ara: `codi · nom · active` + **els quatre comptadors** (són `annotate` d'una sola
consulta: ordenar-hi és gratis, i una capçalera de comptador que no ordena és una capçalera que
menteix).
**I una segona cosa del mateix tipus:** les anotacions es deien `cnt_quotes_sent`… i el que el
client rep es diu `quotes_sent`… — o sigui que `?ordering=quotes_sent` hauria tornat a ser
descartat en silenci. **El nom amb què s'ordena ha de ser el nom amb què es llegeix.**

### `/suppliers` tenia un cercador que no filtrava
Germà **invers**: aquí el `SearchFilter` hi era i el que faltava era `search_fields`. Sense la
llista de camps, el `SearchFilter` de DRF **deixa passar el queryset sencer**. Mesurat abans i
després: `?search=zzzz` → `count 1` (tot) → **`count 0`**.
🛑 **Límit declarat:** l'**ordenació** de proveïdors no s'ha pogut observar contra dades (un sol
proveïdor a `fhort`, cap a `los`). El contracte la sosté; la mesura no hi arriba.

### 15 enumeracions del lot comercial, publicades
`/api/v1/vocabulari/` passa de 6 llistes a **21** (22 amb `temporades`). Els codis **no es
tradueixen**; l'etiqueta ve del propi `choices`.

**Es pregunta al CAMP, no a la constant** (`_choices_del_camp`, nou). Els tres documents
comercials hereten `AbstractDocument.STATUS_CHOICES` i **dos dels tres la sobreescriuen**:
escriure `SalesOrder.STATUS_CHOICES` dona cinc valors que aquell camp no accepta i el codi sembla
correcte. Ho ha demostrat de seguida: **`DeliveryNoteLine` no té cap camp `kind`** (es diu
`line_kind`), i publicar `LINE_KIND_CHOICES` a cegues hauria estat correcte *per casualitat*.

🚨 **Una ja havia derivat, i es veu a pantalla.** `CustomerDetail.jsx` declarava QUATRE orígens
d'àlies amb el comentari «els QUATRE choices del model»; el model en té **CINC** des que el
cercador de Definició POM va estrenar «Crear POM propi del model» (`pom/wizard_views.py:694`
escriu `origen='MODEL'`, provinença permanent). Un àlies nascut d'un model **pinta la clau i18n
crua** a la cel·la. Hi entra també la clau que faltava als tres idiomes.

**L'única que no surt de cap `choices`:** `estat_local` d'un encàrrec de la safata és una
COMPARACIÓ, no un camp (`safata_del_studio`), i és a posta. Però un conjunt tancat de valors que
una pantalla ha de saber pintar **és una enumeració de domini encara que la dada sigui derivada**.
Es publica des d'una constant **al mòdul que la calcula** (`ESTATS_LOCALS_ENCARREC`), no d'una
llista escrita a l'endpoint; els dos literals estaven inline en quatre punts. Cap valor canvia.

### `ui/Modal.jsx` passa la §5
És el crom de mitja part B. Quatre defectes: **cancel·lar anava amb `selS`** (l'estil d'un
*input*) quan la §5.4 li dona terciària · **el deshabilitat anava per `opacity: 0.5`**, que la
§5.7 prohibeix («baixa el fons, no la tinta»: l'opacitat apaga també el text i el deixa sota AA) ·
`--gray` al subtítol → `--text-soft` · radi literal → `--r-card`, títol `--fs-h3` → `--fs-h2`
(§2), padding 22 → 20 (§3, múltiple de 4). **La família sencera de la §5 ja vivia a
`ui/buttons.js` i aquest fitxer no en consumia cap.**

### i18n
Lots 1 i 2 aplicats amb paritat ca/en/es (38 claus de la S2 + `topbar.*` i `dashboard.back_arrel`).

### 🚩 Decisió d'Agus pendent · `components/EstatBadge.jsx`
**Codi mort**: zero imports a tot `src/` (cens de la S2, verificat). Té **5 hex literals** i
consumeix `--border` (deprecat), o sigui que és el primer que troba qui cerqui «com es fa un badge
en aquesta casa». **No es conforma** (conformar codi mort és pintar una porta a una paret) i
**no s'esborra** (els esborrats són decisió d'Agus). Candidat a esborrar, amb el motiu escrit.

### 🚩 `ui/Table.jsx` no es podrà esborrar
Quan la S2 buidi les seves 11 pantalles, li queden set consumidors **fora** del lot comercial:
`components/model/{FittingTab,ProductionTab,RegistreActivitatTab,TaskLog}.jsx`, `pages/Recursos.jsx`,
`pages/SizeMapSetup.jsx` i `pages/TaskTypes.jsx`. Dos són del meu lot (SizeMapSetup) o adjacents.

---
---

# [S2] AUDITORIA · PART B · SESSIÓ 2 — LOT COMERCIAL (només frontend)

> 09/08/2026 · branca `dev` · **cap push** · commits **199 → 215** (sèrie 2xx).
> Sessió germana: **S1**, lot tècnic + propietària de `index.css`, `components/ui/*`,
> `components/layout/*`, `src/i18n/*` i **tot** `backend/`. Aquesta sessió **no ha tocat cap
> fitxer d'aquells**: tot el que hi calia s'ha demanat per missatge i ho ha fet S1.
> **Cap build i cap restart des d'aquí** (un sol builder, S1).

## Perímetre — 16 superfícies i 2 kits

| # | Superfície | Commit |
|---|---|---|
| B1 | `/clients` (llista) | 200 · 201 · 203 |
| B2 | `/clients/:id` (fitxa, 3 tabs) | 200 · 202 |
| B3 | `/proveïdors` + el seu modal (= la seva fitxa) | 204 · 209 |
| B4 | `/comercial/productes` + `/productes/:id` + modal d'article | 211 |
| B5 | `/comercial/ofertes` + modal d'alta | 207 |
| B6 | `/comercial/comandes` | 208 |
| B7 | Encàrrecs de federació (safata del Studio) | 212 |
| B8 | `/comercial/encàrrecs` (WorkOrders) | 208 |
| B9 | `/comercial/albarans` | 208 |
| B10 | Encàrrecs orfes | 210 |
| B11 | Condicions de pagament + el seu modal | 210 |
| B12 | Les 4 fitxes de document (Oferta · Comanda · Encàrrec · Albarà) | 213 · 214 · 215 |
| — | `components/commercial/*` (kit de fitxa, 5 components) | 213 |
| — | `components/llista/ChromLlista.jsx` (crom de llista) — **nou** | 199 |
| — | `components/commercial/estats.jsx` (badges d'estat) — **nou** | 206 |
| — | `CustomerModal` · `CustomerForm` (frontera acordada amb S1) | 202 · 215 |

## Les dues peces compartides que s'han creat, i per què no són invenció

**`components/llista/ChromLlista.jsx` (199).** `ui/TaulaLlista` ja havia tret de `/models` la
GRAELLA; el que es va quedar dins de `Models.jsx` va ser la capa del voltant —botó amb estil de
menú, desplegable d'acció composta, comptador «X/N», camp de filtre, paginació, estat buit,
paperera de fila—. Aquest lot són onze pantalles: copiar-la vuit vegades és el pedaç que la llei
de mètode prohibeix, i el mode de fallada és conegut (nou còpies d'una decisió divergeixen sense
que falli res; només es pinten diferent). **Cada valor surt d'A5, ja conformada i mesurada**;
l'única cosa que s'hi afegeix és `ui/toc`, que A5 encara no feia.

**`components/commercial/estats.jsx` (206).** Aquí NO hi ha cap llista de codis: només el mapa de
COLOR. La frontera, escrita al fitxer: **una llista AFIRMA quins membres existeixen** i el dia que
l'original n'afegeix un menteix sense fallar (`CustomerPOMAlias.origen` en va guanyar un cinquè i
el client en seguia declarant quatre); **un mapa amb fallback no afirma res** — qui no hi és es
pinta neutre i **s'ensenya igualment**.

---

## Cens dada → endpoint (les 11 pantalles)

| Pantalla | Llista | Filtres server-side | Enumeracions (totes de `/vocabulari/`) |
|---|---|---|---|
| Clients | `GET /customers/` + `page_size=1` per al cens | `active` · `search` · `ordering`(7) | — |
| CustomerDetail | `/customers/{id}/`, `/customer-aliases/`, `/grading-rule-sets/`, `/sizing-profiles/`, `/quotes/`, `/orders/`, `/delivery-notes/` | `customer` | `origens_alias_pom` · `estats_vincle_tenant` |
| Proveïdors | `GET /suppliers/` | `active` · `search` · `ordering`(3) | 🛑 `Supplier.type` — v. §Desviació |
| Productes | `GET /commerce/products/` | `active` · `nature` · `ordering` | `natures_producte` · `modes_preu_producte` |
| Ofertes | `GET /commerce/quotes/` | `status` · `customer` · `ordering` | `estats_oferta` |
| Comandes | `GET /commerce/orders/` | `status` · `customer` · `ordering` | `estats_comanda` · `estats_tasca` |
| Encàrrecs (fed.) | `GET /encarrecs/` | — (informe agrupat per Brand) | `estats_locals_encarrec` |
| WorkOrders | `GET /commerce/work-orders/` | `kind` · `status` · `customer` · `ordering` | `estats_encarrec` · `tipus_encarrec` · `estats_tasca` |
| Albarans | `GET /commerce/delivery-notes/` | `status` · `customer` · `ordering` | `estats_albara` · `tipus_linia_albara` |
| Orfes | `GET /commerce/work-orders/orphaned/` (informe sencer) | — | `estats_encarrec` |
| Cond. pagament | `GET /commerce/payment-terms/` | `active` · `ordering` | — |

**Cap endpoint nou a tot el lot.**

---

## 🚨 Els cinc defectes que no eren d'estil

### 1 · `/clients` demanava un ordre que DRF descartava EN SILENCI
`CustomerViewSet` declarava `filter_backends = [DjangoFilterBackend, SearchFilter]`. Declarar-ne
dos **no n'afegeix: els substitueix tots tres** del `DEFAULT_FILTER_BACKENDS`, i queia
l'`OrderingFilter`. `pages/Customers.jsx` enviava `ordering=codi` a cada crida des de feia mesos.
**No fallava mai**: la llista sortia en l'ordre del `Meta.ordering` del model i semblava que
funcionés. Arreglat per S1 (commit 250·204) amb els set camps —els tres de dada i els **quatre
comptadors**, que són `annotate` i per tant ordenables sense cost—, i **mesurat contra l'API viva
abans de posar cap icona**.

### 2 · `/proveïdors` tenia un cercador que no filtrava — el GERMÀ INVERS
Aquí el `SearchFilter` **hi era** i el que faltava era `search_fields`; DRF, sense
`search_fields`, **deixa passar el queryset sencer**. Mesurat abans (`?search=zzzz` → `count 1`,
el mateix que sense filtre) i després de l'arreglo de S1 (`count 0`). **Dos silencis diferents amb
la mateixa cara**: no falla, no avisa, i el control sembla que funciona.

### 3 · Quatre llistes filtraven EN MEMÒRIA sobre `page_size: 500`
Ofertes, comandes, encàrrecs i albarans demanaven 500 files i després feien `items.filter(...)`.
**La llista es partia en silenci a partir de la 501** —la 501a no existia per a ningú— i el
comptador no podia dir mai la veritat, perquè només sabia comptar el que ja tenia carregat.

### 4 · `ModelTask.status` declarat DUES vegades amb DOS mapes de color divergents
`WorkOrderDetail:23` (badge) i `OrderDetail:299` (punt de color). **La mateixa tasca es pintava
d'un color a la comanda i d'un altre a l'encàrrec**, i cap dels dos fitxers sabia que l'altre
existia.

### 5 · Un error de COMPOSICIÓ es pintava com un error de CÀRREGA
A `/albarans`, si «Compondre albarà» fallava, el `catch` feia `setError(true)` i la pantalla deia
«no s'han pogut carregar els albarans» **quan els havia carregat perfectament**.

---

## Conformitat de norma — el que ha canviat, per secció

**§8b** · Les 16 superfícies porten `ui/PageMenu` amb destí explícit. Se'n van: sis botons-fletxa
solts sobre el títol, i **dues bandes de navegació pròpies amb l'activa en DAURAT PLE**
(`CustomerDetail`, `CustomerModal`) — el mateix defecte que A6 va corregir al dashboard del model.

**§8b.3** · Identitat sobre el fons, sense contenidor, a les sis fitxes. A les de document el
subjecte **canvia**: el número baixa a caption i el **CLIENT** puja a `h1`. A la LLISTA la reina
és el número (allà se cerca per número); a la FITXA ja saps quin document mires i el que has de
reconèixer d'un cop d'ull és **de qui és**.

**§8e** · Vuit llistes passen a `ui/TaulaLlista` amb capçaleres ordenables, amplades per
contingut i `ellipsis + title`. `/productes` deixa de fer servir `LineTable` —que és la taula de
**línies d'un document**— per a una llista principal: que les dues fossin taules no les feia la
mateixa taula.

**§5** · Tots els botons a la família de `ui/buttons`. Se'n van: quatre `primaryBtn` que es
fabricaven a mà, un vermell PLE fet sobreescrivint el fons del primari, un «Cancel·lar» amb
l'estil d'un **input**, tres ghosts daurats i sis usos d'`opacity` com a deshabilitat.

**§1** · `--gold-pale` (ELIMINAT del sistema), `--model-band` (crema) i `--intern-bg` (gris fred,
fora de paleta) deixen de tenir consumidors al lot. **Cens del perímetre: 0** ocurrències de
`--gray-l` · `--text-muted` · `--border` · `--gray` · `--bg-muted` · `--gold-pale` ·
`--model-band` · `--intern-bg` · qualsevol `0.5px`.

---

## 🚩 Decisions de DOMINI (no d'estil) — per si Agus les vol vetar

1. **Els INACTIUS deixen d'estar a la llista per defecte** a Clients, Proveïdors, Productes i
   Condicions de pagament. La §8e ho mana; aquí, a diferència de Models, **el criteri no
   s'endevina** (`active` és un camp de debò i el backend ja el filtra). Són a un clic.
2. **OFERTA · `EXPIRED` es pinta com `REJECTED` (vermell).** Totes dues volen dir que l'oferta
   s'ha acabat sense convertir-se en comanda; la diferència la diu la paraula. Abans era taronja,
   que en aquesta escala vol dir «encara en curs», i una oferta caducada no ho està.
3. **TASCA · `Paused` i `Pending` comparteixen el neutre.** Quatre estats sobre un eix de tres
   colors; el que col·lapsa és «ara mateix no corre». L'eix de la §8e és el **progrés**, no el
   rellotge.
4. **PROVINENÇA i TIPUS DE LÍNIA deixen de pintar-se com a semàfor.** `origen` d'un àlies i
   `line_kind` d'un albarà són CLASSIFICACIONS: cap membre és millor que un altre. Anaven amb
   verd, daurat, vermell i taronja repartits sense criteri llegible —`TASK` verd i `DEDUCTION`
   vermell suggerien que una deducció és un error—. El vermell d'una deducció **el porta el
   número**, que ja és negatiu (D-31.21).
5. **El GOVERN baixa de la llista a la fitxa** (logo i actiu/inactiu del client; editar i
   actiu/inactiu de l'article). La graella canònica no dona columna a les accions de fila i la
   §5.6 reserva el menú als gestos ocasionals. **Entren en el mateix tram que la llista les perd**,
   perquè la capacitat no desaparegui en cap moment intermedi.

## 🚩 Desviacions declarades

**`/proveïdors` · `Supplier.type` (workshop · factory) — BLOQUEJAT-PER-S1.** Els `choices` són
**inline** al model (`fhort/tasks/models.py:273`, ni una constant amb nom) i cap endpoint els
publica. És un select que **ESCRIU**. La llei prohibeix inventar-ne de noves; aquesta ja hi era i
es queda **viva i censada**, com el bloc A va fer amb les ~25 sense endpoint. **És l'única
enumeració de domini que el lot encara declara al client.**

**`/clients/:id` · tres columnes de la biblioteca d'àlies porten DUES línies.** No és un salt de
línia (que és el que la §8e prohibeix perquè trenca la fila): és una **pila de dos camps**
—descripció EN + descripció local amb el seu codi d'idioma, i codi global de POM + abreviatura—.
Aplanar-les faria desaparèixer dades que aquesta pantalla existeix per ensenyar.

**Encàrrecs de federació NO és una llista canònica**, i és a posta: són **grups per Brand**,
cadascun amb la seva acció i el seu comptador. Aplanar-ho perdria el que la pantalla diu.

**Orfes no té paginació**: l'endpoint és un **informe** (torna `{orphaned: [...]}` sencer, sense
`count` ni `next`). Paginar-ho al client seria paginar una llista que ja hi és tota.

## 🛑 Límits del banc — el que NO s'ha pogut veure

| Pantalla | Dades vives | Conseqüència |
|---|---|---|
| Proveïdors | **1** (`Syttex`, `fhort`) · **0** a `los` | l'ordenació no és observable |
| Productes | **1** (`FITSES`) | ni ordenació ni paginació observables |
| Orfes | **0** | la taula amb dades i el modal de reassignació, **no fotografiables** |
| Comandes · Albarans | 2 i 2 | paginació no observable |
| Ofertes | 8 (6 DRAFT + 2 ACCEPTED) | l'únic conjunt on el filtre és visible de debò |

**El que SÍ està verificat**: cada filtre i cada ordenació **mesurats contra l'API viva** abans de
connectar-hi cap control (els números, a cada commit), `npx eslint src` → **0 errors**, i el cens
de tokens del perímetre a **0**. **El que NO**: la pell de les graelles plenes. No està amagat:
està dit.

---

## [S2] VERIFICACIÓ MESURADA

### `ops/qa/qa_s2_computats.py` (nou) — ✅ **0 incompliments · 13 rutes**

No duplica lògica: importa el mesurador de `qa_auditoria_computats` —la paleta ratificada, el JS
de `getComputedStyle`, el proxy cap al servei viu i el veredicte— i **només li canvia
`PANTALLES`**. Runner i no ampliació de la llista original perquè el fitxer és de la sessió
germana i s'està tocant en paral·lel: dues sessions editant la mateixa llista és com es perd una
ruta sense que ho noti ningú. Cadascú la seva llista; **el mesurador, un**.

Resultat de la correguda de tancament: **totes les vores de les 13 rutes són de la paleta de la
§1** (`--line` · `--line-soft` · `--gold-border` · `--gold` · `--ok` · `--err` · `--warn-state` ·
`--accio` · `--panel` · `--sel` · `--bg-page` · transparent), **0 rètols/badges/píndoles per sobre
del seu sostre**, i cap `currentColor` (que és el que delata una `var()` que no resol). Els tres
colors del crom del sistema (top bar i menú lateral) s'informen i no compten: §8b diu que el menú
lateral no es toca.

### 🚨 La lliçó de la primera correguda: **EL BUNDLE ÉS EL QUE MESURA, NO EL CODI DEL DISC**

La primera passada va donar **72 incompliments** de `--gray-l` sobre `<input>` a la fitxa de
client. **No era un defecte del codi**: era el `selS` d'ABANS de conformar-lo, congelat en un
`dist` de deu minuts abans. L'arbre ja el tenia bé.

És la mateixa família de trampa que el token que caduca a mitja correguda (que deixa mesurant
contra `/login`), per l'altra porta: **un resultat que no diu res del codi d'ara i que s'assembla
massa a un de veritat**. Està escrit a la capçalera de l'arnès perquè el pròxim no hi caigui.
⚠️ El commit **218** (la provinença d'àlies) és POSTERIOR a aquest bundle: la seva mesura entra
a la pròxima correguda. El canvi és semàntic (classificació vs semàfor), no de token.

### Altres controls

| Control | Resultat |
|---|---|
| `npx eslint src` | ✅ **0 errors** (el control de porta de la casa; `eslint .` compta `dist-tenants/` i menteix) |
| Auditoria de computats · **correguda de tancament** | ✅ **0 incompliments · 13 rutes**, amb la llista d'exempcions ja ESCURÇADA a un sol hex |
| Cens de tokens deprecats al perímetre | ✅ **0** ocurrències en codi |
| Claus de `/vocabulari/` consumides pel client vs publicades | ✅ **15/15 existeixen** — creuament contra l'endpoint viu |

**El creuament de claus és el que va destapar el commit 218**: `origens_alias_pom` estava
publicada i no la consumia ningú perquè el mapa local havia sobreviscut a la meva pròpia neteja.
**Una declaració a un missatge de commit no és una comprovació.**

### `ops/qa/qa_s2_bidireccional.py` (nou) — ✅ **16 casos · 16 casen · 0 desviacions**

> **Estat FINAL, després que S1 resolgués les tres.** La correguda que les va trobar (13/3) i el
> que en va sortir es conserven a sota, perquè el valor no és el número sinó el que va destapar.

Cap pantalla del lot comercial té maqueta pròpia: la seva referència és **la germana conformada**.
Però la §8e diu, amb aquestes paraules, que la graella canònica **«no és un patró opcional de la
pantalla Models: és LA graella de llista de la casa»**. Si això és cert, `NORMA_LLISTA_canonica`
ha de poder verificar una pantalla que **no** sigui Models — i **fins avui no ho havia fet mai**.
Aquesta correguda n'és la prova, i ha donat fruit al primer intent.

**Les tres desviacions són de la MAQUETA o del component compartit. Cap és de les pantalles.**

#### 🚨 DUES DEFINICIONS DEL BADGE NEUTRE convivint, totes dues a pantalles conformades
```
maqueta  .b.neutral      → --bg      + --ink-soft   + --line
Models.jsx `badgeNeutre` → --bg-page + --text-soft  + --line    ← casa amb la maqueta
ui/Badge  variant `gray` → --sel     + --text-main  + --line    ← NO casa
```
`Models.jsx` (A5) es va quedar una **còpia local** del badge neutre; `ui/Badge` (bloc B, **21
fitxers**) en té una altra. Dues còpies d'una decisió, divergides sense que falli res.

**I la raó per la qual no s'havia vist mai és el que ho fa valuós: la graella de `/models` no
pinta cap badge d'estat.** La columna ESTAT hi és buida amb «—» esperant el Kanban i FASE és text
pla (§8e); l'únic badge és el `SetBadge`, una marca condicional que gairebé cap fila porta. La
bidireccional d'A5 **no va comparar `.b.neutral` amb res, mai**. El lot comercial és el primer que
pinta de debò els badges d'estat de la canònica.

🚩 **Decisió d'Agus**, amb els dos arguments: a favor de `ui/Badge`, que un estat ha de ser
llegible i `--text-main` és la tinta principal. A favor de la maqueta —i és NORMA literal— que
**`--sel` és la SELECCIÓ** («fila/contenidor triat, sempre amb filet d'or»): un badge neutre sobre
`--sel` li roba el significat, desapareix dins d'una fila triada i diu «triat» dins d'una que no
ho és. Si mana la maqueta, és **una línia** a `ui/Badge` i la còpia local de `Models.jsx` mor tot
seguit.

#### La tercera, sense dos costats
`.b.warn` de la maqueta encara fa servir `--warn`/`--warn-bg`, **els tokens anteriors a la
§1b(d)** — que va partir el token precisament perquè `#ff9942` com a text dona **1.86:1**.
`ui/Badge` ja fa `--warn-ink`. Aquí la pantalla té raó i **la maqueta dibuixa una cosa que no
compleix AA**. Sembla esmena de maqueta a la font, amb acta.

## [S2] 🚨 ERROR DE MÈTODE, escrit perquè consti

El commit **215** es va endur **dos fitxers de la sessió germana** (`components/ui/buttons.js` i
`pages/Planning.jsx`), que van quedar commitats sota el meu missatge. Causa: `git add
frontend/src/pages/ frontend/src/components/` — **paths de DIRECTORI**. El `CLAUDE.md` ho prohibeix
(«`git add` de paths explícits, mai `-A`/`-u`») i ara se sap per què: amb dues sessions escrivint
alhora, un `add` de directori no afegeix «els meus canvis», afegeix **tot el que hi ha brut**.
El contingut de la sessió germana és **intacte** (el meu script no els tocava; només han quedat
mal etiquetats). No s'ha reescrit història: hi ha commits a sobre i un `rebase` amb dues sessions
vives és pitjor que un commit mal etiquetat. Avisat de seguida a S1.


### [S2] LA TERCERA MANERA QUE UN VERD TÉ DE NO VOLER DIR EL QUE SEMBLA

La sessió germana va escurçar `CROM` —la llista d'exempcions de l'auditoria— de tres hex a un:
dos eren de la **top bar**, que ja havia passat conformitat i no en fa servir cap. Deixar-los
absolia **qualsevol pantalla** que els pintés, i havia passat de debò (`/fittings` sortia verd amb
quatre vores de `ui/Card` tapades). **Una excepció que sobreviu al seu motiu és una tapadora.**

Amb això ja en són tres, i totes tres són el mateix mal amb tres cares:

| Tapadora | Com es veu | Com es descobreix |
|---|---|---|
| **El bundle ranci** | verd o vermell sobre codi que ja no existeix | mirar la data del `dist` abans de creure's el número |
| **El token caducat** a mitja correguda | l'app cau a `/login` i es mesura contra una altra pantalla | correguda de tancament sencera, sense filtres |
| **L'excepció caducada** | el defecte hi és i l'eina l'absol | revisar per què existeix cada exempció, no només si hi és |

La xifra de tancament d'aquest lot (**0/13**) està presa amb les tres tancades: bundle que porta
l'últim commit, token fresc, i la llista d'exempcions ja escurçada.


## [S2] RE-CORREGUDA DE TANCAMENT — §8d: si la norma o les maquetes canvien, es torna a mesurar TOT

S1 va resoldre les tres desviacions: `ui/Badge` variant `gray` passa a **`--bg-page` +
`--text-soft` + `--line`** (mana la maqueta: la §1 reserva `--sel` a la SELECCIÓ i un badge d'estat
a sobre li roba el significat) i les **cinc** maquetes que portaven `.b.warn` amb els tokens
anteriors a la §1b(d) queden esmenades a la font amb acta.

Això toca `ui/Badge`, que **el meu lot munta a totes les llistes**. La §8d mana tornar-hi:

| Eina | Resultat |
|---|---|
| `qa_s2_computats.py` · 13 rutes | ✅ **0 incompliments** (es manté) |
| `qa_s2_bidireccional.py` · 16 casos | ✅ **16 casen · 0 desviacions** (era 13/3) |

**Les tres desviacions eren les tres de la maqueta o del component compartit, i el lot no s'ha
tocat per resoldre-les.** És el que la §8d demana distingir: una desviació no és per definició un
defecte de pantalla, i «arreglar» la pantalla per fer callar la mesura hauria estat el pitjor
desenllaç possible — hauria propagat als 21 fitxers d'`ui/Badge` un fons que la norma té reservat.

### 🚨 LA QUARTA TAPADORA · **una comprovació que no toca res és indistingible d'una que passa**

`ui/Badge` i `Models.jsx` portaven **dues definicions divergents del badge neutre** i la
bidireccional d'A5 donava verd, perquè **la graella de `/models` no pinta cap badge d'estat**: la
columna ESTAT hi és buida esperant el Kanban i FASE és text pla (§8e). El cas existia, es corria,
i **no comparava res**.

S'afegeix a la sèrie, que ja en són quatre:

| Tapadora | Com es veu | Com es tanca |
|---|---|---|
| **El bundle ranci** | verd o vermell sobre codi que ja no existeix | mirar la data del `dist` |
| **El token caducat** | l'app cau a `/login` i mesures una altra pantalla | tancament sencer, sense filtres |
| **L'excepció caducada** | el defecte hi és i l'eina l'absol | revisar *per què* existeix cada exempció |
| **El cas que no toca res** | verd perquè el selector no troba l'element | comprovar que cada cas MESURA de debò |

Les quatre s'han trobat el mateix dia, entre les dues sessions, i cap es veu llegint codi.

---

# [S2] LOT FITXA TÈCNICA + PATRONS (09/08) — crom, mai llenç

Encàrrec: el bug d'accés reportat per Agus, i després el repàs de conformitat de la Fitxa
tècnica i de Patrons **amb frontera absoluta al llenç** (ni components del canvas, ni
`KONVA_COL`, ni el pipeline PDF, ni cap mida en pt del món paper).

## 🔴 EL BUG D'ACCÉS · «la Fitxa tècnica no s'obre»

**No era una regressió del crom** —que és on el report apuntava, perquè el commit 254 havia
tocat la Fitxa tècnica el mateix matí— i té **dues meitats**.

### La causa: infra, no codi

Reproduït contra el gunicorn viu (bundle de `dist` servit per `page.route`, `/api/` reenviat a
`127.0.0.1:8001` amb el Host del tenant):

```
POST /api/v1/models/1319/ftt-document/ → 500
PermissionError: [Errno 13] Permission denied:
  media/fhort/model_fitxers/2026/08/FTT-SS26-0001_fitxa.ftt
```

`backend/media/fhort/model_fitxers/2026/08/` era **root:root** —creat el 05/08 per un procés
root— i el gunicorn corre com www-data. O sigui: **cap fitxa tècnica nova s'ha pogut crear en
tot l'agost, a cap model**. El registre del servei en té un altre d'idèntic a les 11:29, set
minuts abans de la meva reproducció: no és un cas de laboratori.

És el parany conegut de `media/`, i té una propietat que el fa reincident: **el directori del
mes és nou cada mes**. L'1 de setembre pot tornar a passar sol si qui el crea primer és un
procés root.

Resolt amb `chown www-data:www-data` (infra, fora de git). L'editor obre: `/models/1319/ftt/758`.

### La meitat que sí que era codi: **el 500 era invisible**

`FttResolver` (App.jsx) tenia tres `catch { /* noop */ }` i, en fallar, feia
`navigate('/models/:id')` **sense dir res**. Per això un error del servidor es veia exactament
com «una pantalla que no obre»: ni missatge, ni rastre, ni cap manera de saber que hi havia
hagut una crida — i per això el report va anar a parar al crom.

**El defecte real no era el 500: era que el 500 fos invisible.** Sense arreglar això, el pròxim
tornarà a semblar una altra cosa.

| `catch` | Què feia | Ara |
|---|---|---|
| crear el document | se n'anava a `/models/:id` en silenci | ho diu, amb el missatge del servidor si n'hi ha i una porta de sortida |
| llistar les fitxes | `fitxes = []` → **i zero vol dir «crea'n una de nova»** | ho diu i s'atura |
| llistar les plantilles | crea en blanc en comptes d'oferir la plantilla | 🚩 es queda: molesta, no fa mal |

🔑 **El de llistar era pitjor del que sembla.** Una caiguda de xarxa deixava el model amb una
fitxa DUPLICADA al costat de les que ja hi ha. **Zero perquè no n'hi ha i zero perquè no s'ha
pogut saber no són el mateix zero**, i el codi els confonia — germà de la lliçó de F2.2 sobre
`null` («no ho sé») contra 0 («no n'hi ha»).

## 🚨 `var(--text)` NO EXISTEIX a `:root`

Dos consumidors trobats i corregits a `--text-main`: `FttResolver` (les tres caixes) i
`components/pattern/PieceIdentityList.jsx`.

La declaració queda invàlida al càlcul i el color cau a l'heretat: **es veia negre per accident,
no per decisió**, i el dia que el pare canviï de tinta canvia sol. És el mode de fallada exacte
del `var(--fs-title)` del commit 254 i del `var(--bg, #faf9f7)` de Planificació. **No es veu
llegint**: `var(--text)` s'assembla massa a `var(--text-main)` per cridar l'atenció.

## Perímetre i frontera

Tres superfícies que **comparteixen components**: el tab «Patró» del model, el Taller de patró i
—no ho esperava— **l'aside de l'editor .ftt**, que munta `ModelPomList`. No són dos lots; és el
mateix codi vist des de tres portes, i per això una sola passada sobre `components/pattern/*`
conforma alhora part del repàs de la Fitxa tècnica.

**La frontera, verificada pel diff i no per la intenció:** cap literal de color ha canviat, cap
fitxer de canvas és al diff, cap primitiva, cap mida del món paper. A `PatternViewer` només
canvien el contenidor, la barra de zoom i la barra d'estat; les 18 constants de dibuix, intactes.
A `TechSheetEditor`, `COL` ja el va separar el 254 i `KONVA_COL` no s'ha tocat.

## Cens de tokens — 162 substitucions

| Deprecat | Viu | Motiu |
|---|---|---|
| `--border` | `--line` | §1b(b) |
| `--text-muted` | `--text-soft` | §1b(c) · 3.64:1 → 5.37:1 (per sota d'AA) |
| `--bg-card` | `--panel` | mateix blanc, ara amb nom de ROL |
| `--gold-pale` | `--sel` | ELIMINAT del sistema |
| `--gray` / `--charcoal` | `--text-soft` / `--text-main` | àlies legacy |
| `--white` | `--panel` | **NOMÉS on fa de SUPERFÍCIE** |

🔑 **`--white` va haver d'anar per (fitxer, línia), no per substitució cega** — l'única peça no
mecànica del tram. `--white` fa DOS papers: superfície i TINTA. La superfície passa a `--panel`,
que és el nom del rol; **la tinta blanca sobre un farciment ple es queda** — és el que `botoPri`
ja fa, i canviar-la per un nom de superfície diria una cosa falsa del que és. Són 19 llocs de
superfície i 8 de tinta; un `replace` global n'hauria fet un sol munt.

## Dues coses que no eren tokens

· **L'overlay del resolutor es feia a mà, amb `zIndex: 50`.** El sistema en té un
  (`ui/overlay.js`, `Z_MODAL` = 150) i existeix precisament perquè el menú lateral és `fixed` a
  z 100. Aquí no es notava —el resolutor va fora del Shell—, però **un overlay propi que no es
  nota és el que acaba copiat a la pantalla on sí que es notarà**.

· **«Document en blanc» anava en daurat i les plantilles en gris.** Són la mateixa decisió —d'on
  surt el document— i el daurat hi deia «aquesta és la bona» sense que ho hagués decidit ningú;
  amb una plantilla mestra sembrada a cada tenant, la recomanable és més aviat l'altra. §5.3: cap
  de les dues és una acció, totes dues són portes.

## VERIFICACIÓ MESURADA · `qa_auditoria_computats.py`, tres rutes noves

Tres corregudes: abans del tram · després de la meva passada · després de la coda de la
sessió 1 (commit 261, les tres vores de `ui/*`).

| | Ruta | `--border` | `--gray-l` | Mides |
|---|---|---|---|---|
| C1 | `/models/1319/ftt/758` | 14 → 14 → **0** ✅ | 0 → 4 → **0** ✅ | 7 · 0 per sobre |
| C2 | `/models/1319?tab=Patró` | 4 → 0 → **0** ✅ | 12 → **0** ✅ | 15 · 0 per sobre |
| C3 | `/models/1319/patro/taller` | 32 → 6 → **0** ✅ | 4 → **0** ✅ | 9 · 0 per sobre |

🟢 **TANCAT: 0 incompliments a l'auditoria SENCERA** (les 17 pantalles de la llista, no només
les tres meves). Les úniques vores que queden a C1·C2·C3 són `--line`, `--gold`, `--gold-border`,
`--err` i transparent.

🔑 **I la peça de mètode d'aquest tancament: el zero no me l'he pogut donar jo.** Les meves tres
rutes van quedar-se a mig conformar durant una hora perquè el que faltava era de `ui/*`, i el
camí no va ser arreglar-ho «de passada» —hauria propagat el meu criteri a 24 fitxers d'una altra
sessió— sinó **mesurar-ho, dir de qui era amb fitxer i línia, i esperar**. Amb dues sessions
sobre el mateix disc, la propietat de fitxers no és burocràcia: és el que fa que un verd
signifiqui alguna cosa.

Les tres hi entren **tot i tenir llenç, i a posta**: un `<canvas>` és un sol node opac per a
l'auditor —ni vores del DOM ni `fontSize` computat—, o sigui que mesurar aquestes rutes és,
literalment, mesurar-ne el crom.

L'script guanya `FTT_QA_DIST`: aquí `npm run build` DESPLEGA, i amb tres sessions escrivint
alhora, verificar un canvi propi no pot obligar a publicar el codi a mig fer de ningú altre.
Sense la variable es comporta com sempre.

### 🛑 El zero que falta, i de qui és

**Tot el que queda a les tres rutes és de `components/ui/*`, que és de la sessió 1.** Enviat per
missatge amb la mesura; s'escriu aquí perquè **el zero que falta tingui amo i no sembli feina
meva a mitges**:

| Fitxer | Línia | Token | On es veia | |
|---|---|---|---|---|
| `ui/Contenidor.jsx` | 36, 44 | `--border` | 6 vores a C3, 14 a C1 (capçalera de secció col·lapsable) | ✅ 261 |
| `ui/FileDropCard.jsx` | 78 | `--gray-l` | 12 a C2, 4 a C1/C3 («Fitxer DXF obligatori») | ✅ 261 |
| `ui/TranslatableField.jsx` | 51 | `--gray-l` | fora de les meves rutes; mateix token | ✅ 261 |

**Tancat per la sessió 1 al commit 261**, ~40 minuts després d'enviar-li la mesura.

## 🚩 Punts oberts

1. **~16 directoris `root:root` sota `media/`** (`brg/`, `test/`, `los/document_templates/2026/07/`).
   El `chown -R` el bloqueja el classificador de permisos d'aquesta sessió; els crítics
   (`fhort/model_fitxers/2026/08`, `los/`, `los/document_templates/`) sí que estan fets. Per a Agus:
   `chown -R www-data:www-data /var/www/ftt-staging/backend/media`.
2. **El daurat ple de l'acció primària** (`COL.gold` a l'editor, «Buscar propostes» al Taller)
   contra el §5 «un blau per pantalla». La sessió 1 ja el va marcar com a pregunta al 254; **no
   el toco unilateralment**: és la mateixa decisió i l'ha de prendre Agus una sola vegada.
3. **Ni l'editor .ftt ni el Taller de patró munten `PageMenu`** — les dues rutes són fora del
   Shell a posta («és una eina a pantalla completa, el canvas mana»). Si la §8b els ha d'arribar,
   és decisió de navegació, no de tokens. ⚠️ I si algun dia hi munten `PageMenu`, el portal se
   n'anirà a un node **desenganxat** i la barra no es pintarà EN SILENCI: `FORAT_CROM` és un node
   de mòdul i existeix igualment, o sigui que el fallback `FORAT_CROM ? … : barra` no salta.
4. **El `catch` de les plantilles** segueix mut (crea en blanc en comptes d'oferir la plantilla).
5. **No s'hi ha construït res.** El Motor de Patrons v2 és disseny sense implementació
   (`MOTOR_DE_PATRONS_V2.md`, `PLA_IMPLEMENTACIO_MOTOR_PATRONS.md`, cap dels dos commitats).

## 🛑 Límits del banc

El tenant `fhort` té **1 model i 0 documents .ftt**; `los`, 51 models i 0 documents. O sigui que
**abans d'aquest tram no existia cap fitxa tècnica a cap tenant**, i el camí «obrir una que ja
hi és» (1 fitxa → entra directe; N → selector) **no s'ha pogut exercir amb dades reals**: el
selector de N s'ha vist amb la llista servida per l'arnès, no pel banc. El model 1319 no té cap
patró carregat, i per això el Taller s'ha mesurat en estat buit.

⚠️ **He deixat un document creat**: `ModelFitxer` 758 sobre FTT-SS26-0001, fet en verificar que
la fitxa torna a obrir després del `chown`. No l'esborro —és la prova que el camí funciona, i
esborrar-lo és una altra escriptura al domini—; queda dit perquè el banc ja no és com el vaig
trobar.

---

# [S2] FUSIÓ DE CAPÇALERES · la fitxa tècnica entra al bastiment comú (09/08)

🔴 **AGUS, A PANTALLA:** «doble/triple menú superior propi, fora del layout implantat a la
resta». Era literal, i tenia una causa d'arquitectura: **la ruta de l'editor .ftt es va declarar
FORA del Shell** amb l'argument «és una eina a pantalla completa, el canvas mana».

🔑 **L'ARGUMENT SE'NS VA TORNAR EN CONTRA.** Sense bastiment, l'editor se'l va haver de pintar
ell mateix —logo, breadcrumb, barra de 56px—, i el resultat era la fitxa tècnica **amb el camí
escrit dues vegades, mantingut a part, i sense assemblar-se a cap altra secció del model**. La
llibertat de no tenir marc va acabar sent l'obligació de fabricar-se'n un de pitjor.

## Els tres nivells, i de qui és cadascun

| | Nivell | Amo |
|---|---|---|
| 1 | Top bar del Shell | **la casa** — identitat i camí |
| 2 | `ui/PageMenu` | seccions del model + crom del DOCUMENT |
| 3 | La cinta | **l'editor** — és crom d'eina legítim i es queda |

El molla de pa passa a quatre segments reals: **Tenant › Models › {NOM} › Fitxa tècnica**.
L'editor només publica a `store/molla` el tros que la ruta no pot dir (`/models/1319/ftt/761`
no sap com es diu el model ni que això és la fitxa tècnica); la top bar el llegeix.

## El que va marxar, i el que NO es podia esborrar

**El nivell de 26px d'«Edició»** era una franja pròpia per a UN sol desplegable — un pis de crom
per a un botó. Baixa a la fila de tabs de la cinta.

🚨 **Però esborrar-lo hauria estat un error, i el codi ho tenia escrit:** les seves cinc entrades
—desfés, refés, copia, enganxa, duplica— són **l'ÚNICA superfície VISIBLE d'aquestes accions**; a
tot arreu més només existeixen com a drecera de teclat, i *una drecera que ningú anuncia no
existeix per a qui no la sap*. Es mou de lloc; no es perd. «Absorbir» no vol dir «eliminar», i
aquí la diferència era una funcionalitat sencera per a qui no es sap les dreceres.

## 🚨 Totes les sortides per la mateixa porta

`sortirDeLaFitxa` tenia el destí com a CONSTANT perquè hi havia UNA sortida: la fletxa de la
barra pròpia. El menú comú n'obre **nou més** (les seccions del model). Si alguna hagués navegat
pel seu compte, **hauria tret l'usuari de la fitxa amb la tasca oberta i el rellotge corrent** —
exactament el que el modal d'acabar existeix per impedir. El destí passa a ser paràmetre.

## «Exportar PDF»: resolt per JERARQUIA, no per votació

El brief el marcava com un dels daurats plens pendents. **No ha calgut decidir la pregunta gran**
(blau contra daurat), que és d'Agus i per a tot el producte: la §8b diu que a l'extrem dret del
menú de pantalla hi van PORTES en secundari petit, **mai l'acció primària**. En pujar-hi, deixa
de ser l'acció primària d'una barra pròpia i passa a ser una porta del menú comú → `botoSec`.

I per tant **aquesta pantalla es queda sense cap blau, i és correcte**: és la §8e literal —
*«l'acció pujada al menú deixa de ser blava»*— i té precedent mesurat a A4. La ratificació que
Agus va signar mentrestant (commit C2) hi va a favor: les portes són `--panel` + `--gold-border`,
i els toggles d'eina de la cinta —que **no són accions**— es queden daurats per ordre seva.

## L'alçada: `--chrome-h`, i per què no podia ser una constant

Vaig demanar a la sessió 1 que el `<main>` fos columna flex i **li vaig escriure que era
zero-risc raonant-ho**. Ho va mesurar (`qa_diff_layout.py`) i va trobar **8 de 26 rutes amb
moviment**: el `<div>` de marge negatiu del menú deixa de pujar (forat de 24px a dalt) i les
caixes centrades amb `margin: 0 auto` cauen a mida de contingut (1312→1064 · 600→505.7 ·
920→561.6).

🚨 **CAP D'AQUESTS VUIT CANVIA UN COLOR NI UNA MIDA DE LLETRA: les tres eines li haurien donat
verd.** És una tapadora nova — **el canvi que no mou cap valor MESURAT però mou la pàgina** — i
la vaig proposar jo. El meu raonament era correcte *en tot el que deia* i fallava en el que no
deia. No es dedueix llegint.

La sortida: el Shell publica `--chrome-h` **en viu** (`ResizeObserver`) i només l'editor la
consumeix. I la pregunta que valia la pena fer abans d'acceptar-la era si era constant:

| Amplada | Crom | Editor | Desbordament |
|---|---|---|---|
| 1600 | 108 | 892 | **0** |
| 1200 | 144 | 856 | **0** |
| 900 | 178 | 822 | **0** |

**De 106 a 245px** segons la mesura de la sessió 1: el menú porta `flexWrap`. Una constant hauria
estat certa només en una finestra ampla.

## «Res sota 10px»: ja es complia, i per què no s'ha tocat res

Els `fontSize: 8` i `9` del fitxer són **TOTS del món paper** (`measureTextWidthMm`, objectes de
document en mm, primitives Konva). 🚨 **Una escombrada per número els hauria «corregit» i hauria
canviat la mida de la lletra IMPRESA.** La frontera es respecta mirant QUÈ és cada número, no
quant val.

## 🚨 UNA AUDITORIA NO POT ESCRIURE AL DOMINI QUE MESURA

Trobat pel símptoma —«Error desant» a C1— i la causa no era l'editor: **l'arnès reenviava els
PATCH d'autosave al servei viu**, o sigui que *cada correguda de l'auditoria creava una versió
nova del document*. El `758` de la llista arrossega una cadena de quatre i ja no és el cap
vigent; el backend s'hi nega (409) i jo mesurava un editor en error.

**I el senyal `data-ftt-screen` NO ho atrapa**: l'`aside` es pinta igual. El senyal respon «és
aquesta pantalla?», no «està en un estat que ningú ha provocat des de fora?». Dues preguntes.

Regla nova: cap escriptura surt de l'arnès, amb **una excepció escrita** — el `lock` del .ftt, que
és efímer i és *condició per veure la pantalla* (sense lock no es pinten els panells i mesuraríem
una closca buida creient que és l'editor). I el que es bloqueja **es diu**:

```
✋ 2 escriptures BLOQUEJADES (l'auditoria mesura, no muta):
   ×1  PATCH /api/v1/ftt-documents/761/
   ×1  POST  /api/v1/models/1319/open-task/
```

🚨 **El segon és pitjor que el primer i no el buscava:** el Taller obre la TASCA en carregar-se.
Cada correguda de C3 des d'ahir ha posat `pattern_digit` a córrer. **Es veia a les meves pròpies
captures i no ho vaig llegir** — la píndola de tasca activa creixia 4m → 9m → 16m foto a foto.

## VERIFICACIÓ

🟢 **27 rutes · 0 incompliments**, i ara amb la garantia afegida que els zeros no s'han pagat
mutant res. eslint 0 errors · `vite build` net (outDir de proves).

## 🚩 El que la meva eina ha deixat al banc (per a Agus, i NO ho toco)

1. **Model 1319 té 4 documents .ftt** (758→759→760→761) on abans d'ahir no n'hi havia cap. El
   resolutor hi ensenyarà ara el selector de «quina fitxa obro?».
2. **Tasca `pattern_digit` (pk 361) en `InProgress`** amb un `TimerEntrada` obert des de les
   13:24. **Tocar hores registrades és decisió seva**: un timer és el registre d'un fet, i
   esborrar-lo o tancar-lo són dues mentides diferents. El `GuardTascaOblidada` hi és per a això.

## 🚩 El germà que queda fora: `TechSheetTemplateEditor`

La sessió C2 ho va veure des de l'altre cantó i té raó: **el mateix botó «Exportar PDF» ha
quedat amb dues formes**. Al meu editor puja al menú de pantalla i el §8e li treu el color; al
`TechSheetTemplateEditor` és blau, perquè **aquella pantalla encara es pinta la capçalera ella
mateixa**. Cadascuna segueix la norma des d'on és, i per això la divergència **no es tanca
repintant-ne cap**: es tanca absorbint el template editor al bastiment comú, com s'ha fet aquí.

⚠️ **I no és un calc del que acabo de fer**, per això queda anotat i no fet: una PLANTILLA no
penja d'un model. `pindolesDeModel` no li serveix —no té seccions de model— i el seu molla de pa
no pot ser «Models › {NOM} › …». Absorbir-la demana decidir **de qui penja una plantilla** i què
hi ha al seu menú de pantalla, i això és una pregunta de navegació, no de tokens.

Cens ja fet d'aquell fitxer (del tram anterior): 9 usos de token deprecat i 5 literals hex.

## 🚩 CENS D'`opacity` AL PERÍMETRE (§5.7) — la lectura feta, la decisió no

S1 va passar el criteri «una migració de color no s'emporta l'`opacity` de sota» pel seu lot i el
va aplicar també al meu avís; **el criteri em va caçar el meu «Exportar PDF»** (corregit) i, en
passar-lo per tot el perímetre, surten ~20 llocs més. **Cap és meu d'aquest tram i cap es toca**:
el que segueix és el cens classificat, perquè qui ho agafi comenci amb la lectura feta.

🔑 **La troballa del cens és que NO hi ha un sol remei, n'hi ha quatre** — i per això no és una
escombrada:

| Família | On | Remei |
|---|---|---|
| **A · Botó amb fons** | `ExportModal:236` · `PatternTab:394` · `RelationsPanel:396` · `SegmentEditor:77` · `SewEditor:116` · `TallerPatro:1317` · `PatternViewer:884` · `TechSheetEditor:7165`, `8087` | `apagat` (§5.7: baixa el fons, no la tinta) |
| **B · Text sense fons** | `SewEditor:200` (`opacity: 0.85` en un valor de longitud) | **`--text-soft`/`--text-faint`** — no és cap deshabilitat, és un secundari fet amb opacitat en comptes de token (§1). És el cas que S1 va resoldre a `UsersRoles`: *quan no hi ha fons que baixar, mana l'escala de tintes*. |
| **C · Contenidor «ocupat»** | `ProposalsPanel:99` · `DartProposalsPanel:71` (fila sencera amb `background: --panel` mentre treballa) | ❓ **No és deshabilitat, és EN CURS.** La norma no en té forma escrita. Decisió. |
| **D · Regió sencera** | `TechSheetEditor:8141` — un `<fieldset disabled>` amb `opacity: 0.45` que embolica *children* arbitraris quan la tasca està en pausa | ❓ Ni `apagat` (no és un botó) ni una tinta (són molts elements). **Decisió.** |

**Fora del cens i intocable:** tota l'`opacity` de `PatternViewer` (552, 594, 639, 660, 803, 838)
i de `TechSheetEditor` (2194, 7342) és **de dibuix** — primitives Konva i objectes de document.
Una escombrada per `grep opacity` se les hauria endut, que és el mateix parany que els
`fontSize: 8` del món paper.

**I el que es queda per decisió meva, escrit perquè consti:** `ribbonToolStyle:6395`
(`opacity: 0.45`, ~60 botons d'eina). `apagat` els donaria fons `--bg-page` **dins d'una barra
d'eines**; això és una decisió de com es veu una eina inactiva, no un descuit.

> 🔑 **La lliçó de mètode, que és de S1 i val més que el cens:** de les quatre `opacity` fora de
> norma trobades avui entre les sessions, **cap es va trobar rellegint el diff**. Totes quatre,
> amb el criteri escrit a la mà. *Un criteri escrit troba coses que la mateixa persona no veu
> tornant a mirar el mateix codi.*
