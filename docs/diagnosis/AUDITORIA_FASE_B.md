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
