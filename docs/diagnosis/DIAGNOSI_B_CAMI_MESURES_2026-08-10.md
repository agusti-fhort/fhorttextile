# DIAGNOSI · S2 · BLOC B — LA LÒGICA DEL CAMÍ DE MESURES

> Banc: model **1320** (`BRW-FW26-0001` · Blusa KAYCE), tenant `fhort`, catàleg v4, ruleset
> GRADING BROWNIE 2026, taula generada (140 specs actives), 28 mesures base vives i **una**
> sessió de fitting amb veredictes (la 152) més una graella oberta i no tocada (la 153).
> Data: 2026-08-10. Cap push.
>
> ⚠️ Els BREAKS del ruleset els està corregint S1. **Cap número d'aquesta diagnosi depèn d'un
> break**: tot el que es tracta aquí surt de `BaseMeasurement`, `MeasurementChangeLog` i
> `PieceFittingLine`, que són preses i valors base, no escales.

---

## B1 · COMPROVACIÓ — AUDITORIA DE LÒGICA

### El que Agus veia, i d'on sortia cada xifra

Taula «número a pantalla → consulta que el produeix → valor correcte → veredicte». Tot
verificat contra la BD viva (`ops/qa/qa_b1_comprovacio_logica.py`).

| Número a pantalla | Consulta que el produïa | Font real | Valor correcte | Veredicte |
|---|---|---|---|---|
| **YT · mesurat 19** | `_seccio_enrere`: última fila del log amb `context='fitting'` (`MeasurementChangeLog#624`, `valor_nou=19`) | log, fila solta | 19 és una xifra REAL, però no és el que la presa va deixar escrit | 🚨 **fals positiu** |
| **YT · base d'ara 13** | `BaseMeasurement#2222.base_value_cm` | correcta | 13 | ✅ el número és bo |
| **YT · «0 dies»** | `ultim.created_at − presa.created_at`, amb `ultim` = `MeasurementChangeLog#627` (`context='derivat'`, 22 ms després) | log, fila solta | no hi ha cap moviment posterior: el #627 **és part del mateix desat** | 🚨 **la frase és falsa** |
| **E2 · teòric 29 / real 31** | `_seccio_tolerancia`: `PieceFittingLine` de la peça 37 **sense filtre de talla** → la fila **XXS** | `PieceFittingLine` (pf 37, XXS) | talla **S** (la base): teòric **31** / real **33** | 🚨 **talla equivocada** |
| **I · 63/64** | ídem, però aquí Postgres va tornar la fila S | `PieceFittingLine` (pf 37, S) | 63 / 64 | ✅ correcte per casualitat |
| **I4 · 80/81** | ídem | `PieceFittingLine` (pf 37, S) | 80 / 81 | ✅ correcte per casualitat |
| **J · 22,5/20** | ídem | `PieceFittingLine` (pf 37, S) | 22,5 / 20 | ✅ correcte per casualitat |
| **J1·extended · —** | mai consultada: `clau.get((pom, capa, ''))` amb la instància escrita a mà | `PieceFittingLine` (pf 37, S, `extended`) | 20 / 18 · **−2,00 sobre una banda de ±0,60** | 🚨 **invisible** |
| **YT·top / YB·bottom · —** | ídem | `PieceFittingLine` (pf 37, S) | 18/19 i 30/25 | 🚨 **invisibles** |
| **«al darrer fitting»** | `.order_by('-piece_fitting__id')` + primer encert per mesura | l'id de peça és l'ordre d'OBERTURA de graella | la peça **37** (sessió 152, l'única amb contingut) | 🚨 **barrejava fittings** |
| bloquegen · 0 punts | `base_value_cm is None` + POM sense `ModelGradingRule` | correcta | 0 i 0 | ✅ |
| descartades · 0 punts | `SizeCheckLine.decisio='valor_descartat'` | correcta (el check 30 té `decisio=None` a totes les línies) | 0 | ✅ |

**Que quatre xifres de set fossin correctes era casualitat del pla de Postgres, no de la
consulta.** Aquest és el fet que explica per què «de vegades quadra».

### Els quatre defectes, i el que s'ha fet

1. **`_seccio_enrere` llegia files, no ACTES.** El log és append-only i una desada n'escriu
   N: la presa, i darrere seu les germanes que la regla bidireccional deriva. Al desat del
   fitting 152, YT va anar 18→19 (presa), YB 30→31 (derivat), YB 31→25 (presa) i YT 19→13
   (derivat) — **81 mil·lisegons en total**. Comparant la fila `fitting` (19) amb l'última
   fila de qualsevol mena (13), la secció acusava una base que ningú no havia mogut després.
   → Ara l'acte és l'**EVENT** (`FINESTRA_DESAT`, 2 s), el que es va prendre és **l'última
   paraula del desat** i només un event **estrictament posterior** deixa res enrere. Un punt
   d'aquesta secció ja no pot dir mai «fa 0 dies».
   *Decisió d'Agus (10/08): «no és quedar enrere — fora de la secció».*
2. **`_seccio_tolerancia` no filtrava per talla.** La secció compara contra `BaseMeasurement`,
   que ÉS la talla base. → talla base, i prou.
3. **«El darrer fitting» es resolia per id de peça.** → el resol
   `fitting/esdeveniments.py`, que ordena per **data de sessió** i descarta les graelles
   obertes i no tocades.
4. **L'eix d'instància estava escrit a mà a `''`.** Cap germana hi entrava: **5 mesures del
   1320 fora de tota vigilància**. → clau `(pom, capa, instancia)` sencera.

### La pregunta de domini que es va aturar i respondre

«Teòric» era ambigu entre la base d'ara, l'spec d'ara i el valor contra el qual es va mesurar.
**Resposta d'Agus (10/08): el valor de l'última data disponible, que és sobre el que es va
mesurar; si és la primera vegada, sobre la talla base entrada.** O sigui
`PieceFittingLine.valor_teoric` de la peça triada — un fet datat, que no es desdiu quan després
es propaga. La resposta ara porta `darrer_fitting` i `talla_base`, i la pantalla ho diu al peu
de la secció: **una xifra sense procedència no lliga amb res.**

### Resultat mesurat (1320)

| Secció | Abans | Ara |
|---|---|---|
| Van quedar enrere | 1 punt fals («0 dies») | **0 punts** |
| Fora de tolerància | 4 punts, talles barrejades, 3 germanes invisibles | **7 punts, tots de la talla S, amb veredicte** |

---

## B2 · REPÀS DE FITTINGS — REDISSENY DE CONTINGUT

### El que hi havia

Tres columnes per a **un sol fitting**: «DEV @09/08» (sessió 152, la que es va fer), «DEV
@09/08» (sessió 153, una graella que algú va obrir i **no va tocar** — 28 files amb
`valor_real == valor_teoric`, cap veredicte, cap nota) i una tercera d'etapa
(`etapa:fitting@…`), que era **el retorn del fitting 152 a la taula de mesures**. Files: només
els POMs fitats; la resta, absents.

### El que s'ha fet (les cinc ordres d'Agus)

| Ordre | Implementació |
|---|---|
| La taula porta SEMPRE totes les mesures | Les files se sembren de `BaseMeasurement` **vives**, en ordre de fitxa. Una mesura desactivada segueix fora: el cens és de mesures vives. |
| Primera columna = l'ENTRADA DE POMs | Columna `entrada` (`origen='ENTRADA'`), amb el valor **d'abans de la primera re-mesura** (`MeasurementChangeLog` més antic → `valor_anterior`, si no `valor_nou`; sense log, la base vigent). Només a la talla base. Sense cap valor entrat, la columna **no existeix** — no una columna de guionets. |
| Cada fitting = una columna, cronològica | Sense canvi de criteri (data de sessió, id de desempat), però la font ara és `peces_amb_contingut`. |
| Fora les duplicades sense contingut | Dos filtres. **(a)** una peça sense cap línia tocada no fa columna; **(b)** una etapa el `motiu` de la qual cita una sessió que **ja té columna** no en fa una altra — el pont és exacte (`'Fitting · sessió 152 · peça 37'`), no per rellotge. Les etapes **escrites a mà** es queden: és la decisió d'Agus del 28/07 i no dupliquen res. |
| Els canvis, en negreta i amb color | `canvi` i `veredicte` els calcula **el backend**, que és qui coneix l'ordre de les columnes. Un canvi és contra **l'última columna AMB valor** de la fila, no contra la immediatament anterior. |

**El color: pel VEREDICTE de la modista** (decisió d'Agus, 10/08) — `ADJUSTED` → `--warn-ink`
(taronja), `REJECTED` → `--err` (vermell) i ratllat, `ACCEPTED` → `--ok`. És literalment la
paleta que `fittingGridAdapter` i `MeasureGrid` ja fan servir per a aquesta matèria: el mateix
fet es llegeix igual a les dues superfícies. **Un canvi sense veredicte va en negreta i prou; la
resta, normal.**

### Resultat mesurat (1320)

De **3 columnes i 28 files parcials** a **2 columnes** (Entrada de POMs · Dev @09/08) i **28
files senceres**, amb 7 cel·les marcades en taronja (les 7 `ADJUSTED` del fitting 152, que són
exactament les 7 desviacions que la Comprovació denuncia — les dues pantalles ja diuen el
mateix).

---

## B3 · ROUTER DE LA TASCA «MESURAR PRENDA»

**El defecte.** El consum de la tasca entrant (J1b, `ModelSheet.jsx`) feia `setEditing('Mesures')`
**sense mirar de quina tasca es tractava**. Com que la font del `CheckMeasureEditor` és
`fittingSession ? fittingSource : null`, sense sessió cau a la font `check` — que és **el carril
d'entrada de POMs**. Entrar per `?tab=Mesures&task_id=<Mesurar prenda>` (el camí del WorkPlan)
aterrava a la pantalla de definir POMs **amb el rellotge de mesurar la peça corrent al damunt**.

La superfície de fitting existia i el botó ③ hi arribava bé: el que no hi arribava era l'entrada
per URL. El repartiment per tipus vivia **dins** de `obreDeDebo` i el camí de la URL no hi
passava.

**El fix.** `aterraSegonsTipus(tab, code)` — un sol repartidor, cridat pels dos camins. La
tasca es demana al servidor i mana el seu `task_type_code`:

| Tipus | On aterra |
|---|---|
| `pom` (Definició POM) | carril d'entrada (`mesuresEntry`) |
| `grading` (Escalat) | superfície de graduació (`?mode=graduacio`) |
| `size_check` (Mesurar prenda) | **sessió de fitting** — la que la tasca ja porta (`fitting_session`), i només si no en té, `sessioDeFitting()` |
| qualsevol altre / desconegut | superfície de treball del tab, com abans |

Es prefereix la sessió **pròpia de la tasca** i no una endevinada: la tasca oberta des d'una
convocatòria en sap la seva (la del 1320 porta la 153), i endevinar-la podria enganxar-ne una
altra o **crear-ne una de nova sense que ningú ho hagi demanat**. Sense sessió no s'entra: val
més no entrar que entrar a una altra taula que se li assembla — la mateixa llei que el botó ③.

---

## B4 · ESTAT DESINCRONITZAT — QUINA FONT MANA

**El fet.** No és que les dues fonts discrepessin: és que **el stepper no tenia cap fet per a
dos dels quatre passos**. `grading-status` deia `te_mesures` (① Editar POM) i `te_regles`
(② Graduació) i **res** sobre ③ Mesurar prenda i ④ Propagar, que per tant es pintaven sempre
com a portes normals. El Dashboard, mentrestant, llegia `ModelTask.status` i deia «Feta».
Al 1320: `pom=Done · size_check=Done · grading=Done · tech_sheet=InProgress`. **Cap dels dos
mentia; l'un callava.**

**La decisió: mana el FET DEL MODEL** (`grading-status`), i les dues superfícies diuen coses
diferents a posta:

- **El stepper diu ON ÉS EL MODEL.** Es deriva de dades i no pot dependre ni d'un gest ni d'un
  permís. És la mateixa llei que ja mana al gate d'entrada del tab Mesures (que llegeix
  `pom_task_done` **del model**, no la llista de tasques, perquè aquella va escopada per
  `view_team_tasks` i qui no tenia la capability veia «Mesures encara no disponibles» amb la
  taula plena), i la que diu `CLAUDE.md`: **la conformitat es mesura**.
- **El Kanban/Dashboard diu QUÈ HA FET LA GENT.** Una `ModelTask` és el testimoni de la feina i
  del temps; algú la pot marcar Feta sense que hi hagi res al model, i això és informació, no
  una avaria.

**Els dos fets que faltaven**, afegits a `grading-status` (mai un endpoint nou: dos endpoints
per a la mateixa pregunta acaben donant dues respostes):

- `te_presa` — hi ha algun fitting **amb contingut**. Mateix predicat que el Repàs i la
  Comprovació (`fitting/esdeveniments.py`): una graella oberta i no tocada no és una presa.
- `te_propagacio` — àlies de `te_dades_propagades`, perquè el pas ④ es pinti amb el mateix
  vocabulari que els altres tres.

Al 1320 les quatre portes surten ara **en verd**, que és el que el Dashboard ja deia.

**Quan divergiran** (i és correcte que ho facin): tasca `Done` sense artefacte = algú la va
tancar sense fer-la; artefacte sense tasca `Done` = la feina es va fer fora del circuit de
tasques. El stepper dirà el fet; el Kanban, el gest.

---

## Fitxers

| Fitxer | Què |
|---|---|
| `backend/fhort/fitting/esdeveniments.py` | **nou** · què és un fitting que ha passat de debò. El comparteixen la Comprovació, el Repàs i `grading-status`. |
| `backend/fhort/models_app/comprovacio_views.py` | B1 · `_events`, `_seccio_enrere`, `_seccio_tolerancia`, `_darrer_fitting` |
| `backend/fhort/fitting/repas_views.py` | B2 · `_entrada_de_poms`, `_sessio_del_motiu`, sembra del cens, marcatge de canvis |
| `backend/fhort/models_app/views.py` | B4 · `te_presa` i `te_propagacio` a `grading_status_view` |
| `frontend/src/components/model/ComprovacioPanel.jsx` | B1 · procedència i columna VEREDICTE |
| `frontend/src/components/model/repasGridAdapter.jsx` · `FittingRepasPanel.jsx` | B2 · columna d'entrada, marcatge, recompte |
| `frontend/src/components/model/MeasureGrid.jsx` | B2 · les cel·les d'història accepten `canvi`/`veredicte` (**additiu**: qui no els envia pinta igual) |
| `frontend/src/pages/ModelSheet.jsx` | B3 · `aterraSegonsTipus` + J1b · B4 · passos ③ i ④ pel seu fet |

## Arnesos

| Arnès | Cobreix |
|---|---|
| `ops/qa/qa_b1_comprovacio_logica.py` | B1 · 11 afirmacions contra la BD viva, re-derivades des de les taules d'origen |
| `backend/fhort/fitting/test_repas.py::RepasB2Test` | B2 · 13 proves: entrada, cens sencer, columnes buides, dedupe d'etapa, marcatge |
| `ops/qa/qa_b34_router_i_estat.py` | B3 · els dos camins d'entrada · B4 · les quatre portes |
