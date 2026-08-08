# REPORT DE BLOC · A1 · A2 · A3 · A4 — Configuració tècnica conforme

> 08/08/2026 · commits **171 → 178** (cap push) · build **desplegat** (`frontend/dist` és el que
> staging serveix: `npm run build` fet, Agus pot obrir el navegador sense reconstruir res).
> Aquest report tanca el bloc A. Les dues condicions de tancament, al §7.

---

## 1 · Un resum per pantalla

### A1 · Catàleg de POMs — `/poms` (commit 166, + correcció 173)
Ja estava construït al tram anterior. En aquest bloc hi entra **una sola cosa, i és greu**: cada
fila de la llista tenia una **línia negra de 3px** en comptes del filet d'1px de `--line-soft`.
Causa i remei al §4.

### A2 · Size Library — `/size-library` (commit 169, + correcció 173)
Igual: construïda al tram anterior; aquí hi entren **la mateixa línia negra** i, a més, **els 41
xips de les quatre capes renderitzant-se a 16px en comptes de 10**. Causa i remei al §4.

### A3 · Grading Rules — `/poms/grading` (commit 171) — **construïda de nou**
La cascada se'n va. El que hi havia era un `CascadeSelector` de quatre eixos que **no ensenyava cap
joc fins que se n'havien triat els quatre**. La maqueta v4 ho descarta amb aquestes paraules: «la
llista és una llista, no mitja pantalla». El que la cascada responia —quin joc surt per a aquest
cas— ho respon ara la columna **«Es proposa a»**, que ho diu de tots els jocs alhora.

Estructura, la de la maqueta sencera: **menú de pantalla → llista amb capçaleres → «Editar» →
pantalla pròpia del joc amb els tabs «Talles i regles» i «Relacions»**.

- **Cardinalitat**: `targets` M2M (multi) · `construction` · `fit_type` · `garment_group` **FK**
  (un sol valor; re-clicar **desdeclara**). És el que distingeix aquesta pantalla de la del run,
  on les quatre capes són M2M.
- **El break és de la REGLA**, no del joc. El gest de clicar una talla es conserva, però és una
  comoditat que escriu a les regles que **tenen Δ break**; la columna «Talla break» diu el de la
  seva fila.
- **Buit = «NO DECLARAT»**, mai «serveix a tothom» — ho té escrit el backend.
- **Règims**: els ofereix `/vocabulari/` amb la marca `autorable`. ZERO i EXCEPTION queden fora de
  l'autoria; una fila que ja en porti un el segueix mostrant.

### A4 · Garment Types — `/garment-types` (commit 174) — **sense maqueta**
No va caldre aturar-se: l'estructura és **mestre-detall**, exactament la de les dues germanes ja
conformades. Només pell i bastiment; cap funcionalitat nova.
- **§8b**: menú de pantalla amb ← · Actiu · Inactiu · Tots · «Nou tipus».
- **§8e**: comptador «17/21» amb la cerca al costat; el nom de l'entitat deixa de ser `<h1>`.
- **§5**: **la pantalla es queda sense cap blau**, i és correcte (§8c ho permet a una pantalla de
  consulta). «Nou tipus» puja al menú i hi perd el blau (§8e); **«Nou item» no era una acció
  primària: navega a `/cataleg-peces`, o sigui que és una PORTA** (§5.3) — n'hi havia dues, totes
  dues blaves.
- **§1**: la fila triada anava amb `--warn-bg` + tinta `--warn`. Taronja de **semàfor fent de
  selecció**. Ara `--sel` + filet d'or.

---

## 2 · El §8b ja tenia component i no el muntava ningú

`frontend/src/components/ui/PageMenu.jsx` —fletxa 32px amb destí explícit, píndoles de secció,
`children`— existia amb **zero consumidors**. La justificació «aquesta app encara no té menú de
pantalla» era **falsa**, i la va caçar el guardia-ui. A3 i A4 el munten ara, amb el contingut
exacte que la maqueta hi dibuixa.

Conseqüència de la §8e, aplicada: **l'acció primària pujada al menú deixa de ser botó i deixa de
ser blava** («el blau viu al contingut; el menú té el seu llenguatge»).

---

## 3 · Cens dada → endpoint (A3, la pantalla nova)

| Què es pinta | D'on surt |
|---|---|
| Llista de jocs · nom · codi · `actiu` | `GET /api/v1/grading-rule-sets/?page_size=200` (paginació seguida fins al final) |
| Columna **Client** | `customer_codi` del mateix serializer |
| Columna **Origen** | `origen` (`CANONICAL`/`CLIENT_RUN`/`IMPORT`/`null`) |
| Columna **Regles** | `regles_count` |
| Columna **Es proposa a** | `targets_codis` + `construction_codi` + `fit_type_codi` + `garment_group_codi`, resolts contra els vocabularis |
| Vocabulari de Target · Construcció · Fit | `useEixos()` → `/targets/` · `/construction-types/` · `/fit-types/` |
| Vocabulari de Grup | `useGarmentGroups()` → `/garment-groups/` |
| **Règims del desplegable** | `GET /api/v1/vocabulari/` → `regims_graduacio`, **filtrats per `autorable`** |
| Taula de regles (POM · nom · règim · Δ · Δ break · talla break) | `regles[]` niat al mateix serializer |
| **Talles de la barra de trencament** | `GET /api/v1/size-systems/` → `talles` del `size_system` del joc 🚩 |
| Desar regles | `PATCH /api/v1/grading-rules/{id}/` (només les files tocades) |
| Treure una regla | `DELETE /api/v1/grading-rules/{id}/` (**no esborra: marca `actiu=False`**) |
| Desar relacions | `PATCH /api/v1/grading-rule-sets/{id}/` amb `targets` · `construction` · `fit_type` · `garment_group` |
| Identitat / clonar / jubilar / esborrar | `POST` · `PATCH` · `DELETE` de `/grading-rule-sets/` |

**Cap enumeració de domini escrita al client.** Cap backend nou en aquest tram: el
`GradingRuleSetViewSet` i el `GradingRuleViewSet` ja eren ModelViewSet amb escriptura *gated*
CONFIGURE; el que hi havia era un `fetch()` a pèl des de la pàgina, que ara passa pel client de la
casa (amb refresh de token i base URL).

---

## 4 · Les línies negres i els badges grans — causa arrel

Les dues coses són **el mateix defecte**, i cap de les dues es veu llegint el codi.

### 4a · La línia negra de 3px (A1 i A2, cada fila de la llista)

```js
row: {
  borderBottom: '1px solid var(--line-soft)',   // ← el que es volia
  …
  border: 'none',                                // ← s'aplica DESPRÉS
  borderBottomStyle: 'solid',
  color: 'inherit',
}
```

Les propietats s'apliquen **en ordre de clau**, i una `shorthand` posterior a la seva pròpia
longhand la **reescriu sencera**: `border: none` posa l'amplada a `medium` (**3px**) i el color a
**`currentColor`**. Amb `color: 'inherit'`, `currentColor` és `--text-main`. El
`borderBottomStyle: 'solid'` de darrere tornava a fer visible **això**.

**Cap `var()` estava mal definida.** Tots els tokens de la norma són a `:root` i resolen. El que
fallava era l'ordre d'aplicació.

### 4b · Els xips a 16px (A2, els 41 de les quatre capes)

```js
style={{ ...cx.ab /* porta fontSize: var(--fs-label) */, cursor, font: 'inherit', fontSize: 'var(--fs-label)' }}
```

Les **claus duplicades de JS conserven la posició de la PRIMERA**: `fontSize` es queda a la ranura
primerenca de `cx.ab` i `font: 'inherit'` s'aplica **després**, menjant-se la mida. Heretaven els
16px del document. Remei: `fontFamily`, mai la shorthand `font`.

### 4c · Taula abans → després (computats, `getComputedStyle`)

| Pantalla | Vores negres (`rgb(29,29,27)`) | Badges/xips per sobre del sostre | Altres fora de paleta |
|---|---|---|---|
| A1 · Catàleg de POMs | **12 → 0** | 0 → 0 | 0 → 0 |
| A2 · Size Library | **23 → 0** | **41 → 0** | 0 → 0 |
| A3 · Grading Rules | 0 → 0 | 0 → 0 | 0 → 0 |
| A4 · Garment Types | 0 → 0 | 0 → 0 | **2 → 0** (`--gray-l` a 77 vores · `--warn` a `GroupPills`) |

**Total del bloc: 0 incompliments.** L'eina és `ops/qa/qa_auditoria_computats.py` i es corre contra
el servei viu. El crom del sistema (top bar i menú lateral) s'informa i **no** compta: la §8b diu
que el menú lateral no es toca i que la top bar està pendent de foto pròpia — **hi queden 3 colors
fora de paleta** (`#e4e4e2`, `#e8e8e8`, `#e0d5c5`), anotats per a qui els toqui.

### 4d · Per què la bidireccional no ho va caçar, i què s'hi ha fet

**Perquè llegia codi.** Les dues línies que calia comparar són correctes cadascuna per separat i
estan a vuit línies de distància dins del mateix objecte; el que falla és l'**ordre d'aplicació**,
que només existeix al navegador. És literalment el que la §8d ja deia —«la conformitat fina es
MESURA contra valors computats, mai a ull»— i el que faltava era l'eina.

Sí, s'havia executat sobre aquestes pantalles, i el seu veredicte sobre A3 va ser **VERMELL amb
cinc blocadors reals** (entre ells el `PageMenu` no muntat, les files que salten de línia i
`--text-faint` sobre dades) — tots corregits abans de tancar. El que no podia trobar eren els
computats.

**El guardià, corregit** (`.claude/agents/guardia-ui.md`):
1. Ha de **córrer l'auditoria de computats abans de cap veredicte**; sense mesura, **no hi ha VERD
   possible** — el veredicte és BLOQUEJAT per manca de mesura.
2. `rgb(29,29,27)` en una vora **mai és una decisió**: és `currentColor`, i la correcció va al token
   o a l'ordre de les propietats, mai amb un hex local.
3. Ha de **buscar activament** el patró *shorthand després de la seva longhand* al diff.
4. Mides amb sostre explícit: badge 10px · píndola de navegació 12px · th/caption/label 10px.

🚩 **La còpia vigent del guardià viu al vault** (§1b(e)): aquest canvi s'hi ha de sincronitzar.

---

## 5 · Conducta afegida (per si la vols vetar)

1. **Menú «Accions ▾»** a la capçalera del joc (Identitat… · Clonar · Jubilar/Reactivar ·
   Eliminar). A la maqueta viuen al menú de pantalla del §8b; es reallotgen sense canviar-ne cap.
2. **Modal d'identitat** (nom · codi · run). La maqueta no dibuixa cap editor d'identitat, i sense
   ell un joc **no es pot crear ni reanomenar**.
3. **Marca «= FIXED»** al costat del règim quan la regla és LINEAR degenerada (Δ 0 i sense break).
   El desplegable segueix dient el que hi ha **desat**: reinterpretar-lo sota els dits li canviaria
   la tria a qui l'està escrivint.
4. **Filet taronja** a la fila amb canvis pendents de desar. Ni `--sel` («on soc») ni verd
   («inclòs»): «pendent» és una tercera cosa, i el taronja és marca de dada.
5. **Bloc «Grup de peça» bloquejat amb motiu escrit** quan el joc declara l'abast per `scope_nodes`
   (5 de 47 jocs). D1: una sola font d'abast; escriure-hi el FK crearia la segona.
6. **Eixos deshabilitats** quan `is_system_default` (guard F-5, ja existent al serializer).
7. **Cerca al costat del comptador** en comptes de dins la capçalera de la llista (§8e mana pell;
   mateixa decisió que ja es va prendre a A1).
8. **`GroupPills` canvia per a tothom**: el component és únic i el fan servir també el selector de
   peça del wizard i el Navegador de POM Systems. El canvi va cap a la norma a totes tres, però les
   altres dues **encara no han passat la seva conformitat**.

---

## 6 · Pendents anotats

### 🚩 CAT2.1 — la distància, dita i no tancada
La maqueta diu «un joc no depèn de cap run». El pas (a) està fet (les regles ancoren per etiqueta i
el motor hi resol), però **la FK `GradingRuleSet.size_system` encara hi és i 40 de 47 jocs de
`fhort` la tenen poblada**: és d'on surten, avui, les talles de la barra de trencament. La pantalla
**pinta el que hi ha i ho diu** al text de la barra. Retirar la FK és el pas (b) i no és d'aquest
tram.

### 🛑 BLOQUEJAT — «＋ Afegir POM»
Pintat **deshabilitat amb el motiu al `title` i al peu**. `GradingRuleSerializer` té `rule_set` com
a **read_only** i `talla_base` és FK obligatòria: un `POST` a `/grading-rules/` no pot dir a quin
joc va la regla nova. **Demana backend, no pell.**

### 🚩 CENSAT-PENDENT
- **`valor_base`**: la taula vella en pintava una columna i **el camp no existeix** (esborrat al
  sprint Mesures Base per Item). Sempre deia «—». Ha desaparegut amb la maqueta.
- **`CascadeSelector`, `matchingRuleSets*` i les targetes de RuleSet** deixen d'estar muntats a
  `/poms/grading`. **No s'esborren**: el wizard i altres superfícies els munten.
- **`isDegenerateLinear` a la resta de superfícies**: aquí es diu amb la marca «= FIXED»; les altres
  tres superfícies segueixen com estaven.
- **Crom del sistema**: 3 colors fora de paleta a la top bar i el menú lateral (§4c).

### ❓ Preguntes per a Agus
1. **`/garment-types` vs `/cataleg-peces` (U2).** Segueixen sent **dues pantalles del mateix
   catàleg**. `/garment-types` és avui **l'única superfície que edita i esborra famílies i items**,
   que la v4 de `/cataleg-peces` no cobreix — per això **no s'ha retirat** i se li ha donat la pell
   igualment. **Cal decidir si convergeixen i en quina direcció.**
2. **El 409 `codi_duplicat` de l'import** ha passat a ser defensa en profunditat d'un estat que la
   BD **ja no permet** (migració `pom/0075`). O es retira el guard i s'esborren les seves 7 proves,
   o es queda tal com està. Ho he deixat **tal com està**: retirar-lo és decisió de producte.
3. **Marcar el trencament escriu a TOTES les regles amb Δ break** (gest ratificat a la v2). Límit
   conegut: així no es pot donar un break diferent a dues regles del mateix joc, cosa que el model
   **sí** que permet.

---

## 7 · Les dues condicions de tancament

### (1) A1+A2+A3+A4 fets, amb build desplegat — ✅
`npm run build` fet i `frontend/dist` és el que staging serveix. `npx eslint src` → **0 errors**.
Auditoria de computats a les 4 pantalles → **0 incompliments**.

### (2) La suite — ✅ **913 tests · OK · 0 errors**
`python manage.py test fhort.pom fhort.models_app fhort.fitting` · 3.597 s. Els 11 vermells de la
correguda anterior eren tots de la migració `pom/0075` d'aquest mateix tram i estan resolts (§8).

**Captures** (contra el servei VIU, un estat per captura; `ops/qa/captures/`):
`a3_01_llista` · `a3_02_llista_cerca` · `a3_03_joc_regles` · `a3_04_joc_relacions` ·
`a3_05_relacions_declarades` · `a3_06_joc_buit` · `a3_07_jubilats_buit` ·
`a4_01_llista` · `a4_02_detall` · `a4_03_inactives`.

⚠️ **Les icones surten buides a les captures i no és un defecte de la pantalla**: Tabler entra per
webfont des d'un CDN i l'arnès de captura intercepta `**/*`. Al navegador de debò hi són.

---

## 8 · La suite

**Correguda anterior** (`fhort.pom fhort.models_app fhort.fitting`): **913 tests · 11 errors**.
Els **onze** eren el mateix `UniqueViolation` sobre `uniq_pommaster_codi_client_ci` — la constraint
de la migració `pom/0075`, **d'aquest tram** (commit 165). **Cap era arrossegat.**

Tres causes diferents, tres remeis diferents (commit 172):

| Proves | Causa | Remei |
|---|---|---|
| `test_ordre_regla_grading` (3) | El fixture muntava el cas viu **literalment**: dos POMs amb el mateix `codi_client`. Aquell estat ja no existeix. | **L'ambigüitat no desapareix, canvia de porta**: dos POMs poden respondre al mateix codi de la URL un pel seu `codi_client` i l'altre pel seu codi global. El corpus es remunta així. **Criteri provat intacte.** |
| `tests_sembra_grading` (1) | `self._seq` **no s'incrementa enlloc**: les dues files MANUAL demanaven el mateix codi. La prova volia tres POMs i en creava dos iguals **sense saber-ho**. | L'índex del bucle els separa. **La constraint ha delatat un defecte de la prova.** |
| `test_import_poms_*` (7) | L'estat és impossible, **però el guard del 409 segueix viu al codi de producció**. Esborrar-les el deixaria sense xarxa. | `fhort/pom/catalog_testing.py` treu la constraint **només dins de la transacció** de la prova que la necessita (el DDL de Postgres és transaccional: el rollback la restaura). |

**Verds per mòdul, verificats**: `test_ordre_regla_grading` 4/4 · `test_import_poms_duplicats` +
`test_import_poms_resolucions` 16/16 · `tests_sembra_grading` 103/103.

**Correguda sencera de tancament**: ✅ **913 tests · OK · 0 errors · 0 fallides** (3.597 s),
amb la mateixa comanda i la mateixa selecció d'apps que la que en donava 11.

> La referència «671/671» del brief és d'una **selecció d'apps diferent**; aquesta correguda en fa
> 913 perquè cobreix `fhort.pom` + `fhort.models_app` + `fhort.fitting` sencers. El número que val
> per comparar és el d'aquesta mateixa comanda.

---

## 9 · Segona passada de conformitat (esmena Agus) — i la resposta a la pregunta de mètode

### 9a · La pregunta de mètode, sense embuts

**El procediment que es feia servir NO era la bidireccional.** Era obrir la maqueta, obrir el JSX
i comparar-los **llegint**. Amb això es va donar per bona una selecció `--sel`+daurada a la Size
Library allà on la maqueta diu, amb el comentari escrit **al costat**:

```css
.tg.on{background:var(--ok-bg);border-color:var(--ok);color:var(--ok);font-weight:600}
                                          /* esmena Agus: inclòs = verd */
```

Llegir dos fitxers i creure que diuen el mateix no és verificar-ho.

**I hi ha un segon forat, de procés, que és igual d'important:** la bidireccional es corria **un
cop per tram i sobre la pantalla del tram**. A1 i A2 es van tancar abans d'aquest bloc; l'esmena
del verd és del 08/08 i **no va tornar a passar per sobre seu mai**. Una regla ratificada després
d'una pantalla no arribava mai a aquella pantalla.

Les dues coses són ara al brief del guardià:
`ops/qa/qa_bidireccional.py` compara **valors computats de les dues bandes** (obre la maqueta amb
`file://`, obre la pantalla amb el bundle + l'API viva, executa els gestos que calen a cada banda
per arribar al mateix estat, i llegeix `getComputedStyle` element per element); i **quan la NORMA
o una maqueta canvia, es torna a córrer sobre TOTES les pantalles ja conformades**.

### 9b · Les tres desviacions, mesurades i corregides

| # | Què | Abans (computat) | Ara (computat) |
|---|---|---|---|
| 1 | A2 · capa de restricció TRIADA | `--sel` · tinta `--text-soft` · vora `--gold-border` | **`--ok-bg` · tinta i vora `--ok` · pes 600** — casa amb `.tg.on` a les 8 propietats |
| 2 | A2 · «no declarat» | 12px, **repetit sota cadascuna de les 4 capes** | **10px, tènue, cursiva, UN COP per secció** + l'estat al costat del títol («cap capa declarada») |
| 3 | A1·A2·A3·A4 · descripció sota el comptador | hi era | **fora** (§8e: comptador + cerca i prou) |

**Sobre la #3, i cal dir-ho clar: la maqueta d'`ops/maquetes/` SÍ QUE LA PORTA.** `.ident .desc`
està definida i usada a `maqueta_size_library_v3.html:154,190` i a `maqueta_grading_rules_v4.html:225`.
No he llegit cap còpia prèvia: és la vigent. L'ordre d'Agus és **posterior** a la maqueta i mana
(jerarquia §8b), i per això la línia se'n va de les quatre pantalles.
🚩 **Les maquetes s'han d'esmenar**, o el pròxim tram la tornarà a pintar amb la maqueta a la mà.

### 9c · El quart estat fantasma

En desmarcar un xip es quedava amb **vora fosca i gruixuda**: ni verd ni repòs. No era el toggle
—desmarcava bé— sinó **l'anell de focus**, que el botó conserva després del clic (hipòtesi (b)
d'Agus, confirmada).

`frontend/src/components/ui/toc.js` (NOU, **compartit**) resol hover i focus amb estat de React i
només pinta l'anell amb focus de **teclat** (`:focus-visible`), amb `outline: 'none'` a la base
perquè el de l'UA no torni a entrar per la seva porta. **Tres estats i cap més**: repòs (`--line`
fina + `--panel`) · seleccionat (`--ok-bg` + `--ok` + 600) · hover (`--sel`, i **no trepitja el
verd**). El fix va al component: l'usen A2, A3 i `GroupPills` —que és compartit amb el selector de
peça del wizard i el Navegador de POM Systems, i tampoc no en tenia.

### 9d · El que la MESURA va trobar i ningú no havia vist

- **La fila de la llista computava 16px** (A1 i A2): heretava la mida del document. Els fills
  posaven la seva i per això a ull no es notava. Contra `.pom.on`/`.run.on` = 12px.
- **El xip en repòs anava en `--text-soft`** (és `cx.ab`, el xip de només-lectura). La maqueta el
  vol en tinta principal: un xip que es pot triar no és una etiqueta apagada.
- **La tab germana** portava 1px transparent als altres tres costats i era 2px més ampla.

### 9e · Les 3 desviacions que queden, i per què queden

| Element | Maqueta | Pantalla | Per què |
|---|---|---|---|
| `.tg` de grading (×2) | 11px | **12px** | 🚩 **11px no és a l'escala de la casa** (§2: 10·12·14·18·22·32). Mana la norma; la maqueta té un valor fora d'escala. |
| `.shead .t` | 15px | **14px** | 🚩 **LA NORMA ES CONTRADIU AMB EL SEU PROPI TOKEN**: §2 escriu «h3 subtítol 15/20» i `index.css` defineix `--fs-h3: 14px`. **Decisió d'Agus.** |

I un cas **no mesurat**: l'estat «cap capa declarada» d'A2 no és assolible amb les dades vives del
run que l'arnès obre (totes les seves capes estan declarades). Anotat, no amagat.

---

## 10 · Tancament del bloc — les tres ordres

### 1 · Maquetes: fora la descripció sota el comptador ✅ (commit 180)

Corregida **la font**. Mentre la maqueta la demanés, el pròxim tram la tornaria a dibuixar i amb raó.

| Fitxer | Línies tocades |
|---|---|
| `maqueta_size_library_v3.html` | **154** (regla CSS `.ident .desc`) · **190** (ús) |
| `maqueta_grading_rules_v4.html` | **187** (regla CSS) · **225** (ús) |
| `maqueta_cataleg_poms_v3.html` | **161** (regla CSS; **només la regla** — no la feia servir ningú) |
| `maqueta_cataleg_peces_v4.html` | **cap canvi**: no en tenia ni regla ni ús |

Al lloc de la regla hi queda escrit **per què** se'n va, i les dues maquetes amb acta d'esmena al
peu en porten l'entrada. Verificat: cap `.desc` viu —ni regla ni ús— a cap de les quatre.

🚩 **Divergència coneguda i NO tocada** (l'ordre no la demana): a les maquetes la **cerca** segueix
a la capçalera de la llista, i a les pantalles ha pujat al costat del comptador (§8e: «la CERCA
comença al costat, mateixa línia»). És l'únic que queda perquè maqueta i pantalla casin del tot.

### 2 · h3 → mana el token (14px) ✅ — RESOLT, cap canvi de codi
La pantalla ja fa servir `--fs-h3: 14px`. La NORMA del vault està esmenada; Agus la re-puja a
`ops/maquetes/`. La desviació «maqueta 15px / pantalla 14px» de `qa_bidireccional.py` queda tancada
com a **defecte de la maqueta**, no de la pantalla.

### 3 · El guardià ✅ — `qa_bidireccional.py` és protocol
El brief del vault ja porta la bidireccional **per computats** i la **re-execució sobre les
pantalles tancades quan una norma s'esmena**; Agus el re-puja a `.claude/agents/`. A partir d'ara
**tot report d'una pantalla ha de citar `ops/qa/qa_bidireccional.py`** amb el seu resultat, igual
que ja cita `ops/qa/qa_auditoria_computats.py`.

### 4 · «＋ Afegir POM» — 🛑 pendent de decisió d'Agus
Queda **deshabilitat amb el motiu escrit al botó i al peu**. `GradingRuleSerializer` té `rule_set`
com a read_only i `talla_base` és FK obligatòria: un `POST` a `/grading-rules/` no pot dir a quin
joc va la regla nova. Les dues sortides són **coda backend** o **deshabilitat fins post-deadline**;
cap de les dues s'ha pres.

---

## 11 · El protocol de verificació, tal com queda

Tota pantalla que passi conformitat corre **les dues eines** i en posa el resultat al report:

| Eina | Què respon |
|---|---|
| `ops/qa/qa_auditoria_computats.py` | «¿hi ha cap vora, cap badge o cap rètol que no sigui el que la NORMA mana?» — sobre les pantalles del bloc, contra el servei viu |
| `ops/qa/qa_bidireccional.py` | «¿la pantalla i la seva maqueta pinten el mateix?» — computats de les dues bandes, element per element, amb els gestos que calen a cada costat |

I cada desviació que quedi s'**explica**: defecte de pantalla, defecte de maqueta, o ordre d'Agus
posterior a la maqueta. El silenci no és una resposta.
