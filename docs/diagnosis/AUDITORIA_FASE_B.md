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
