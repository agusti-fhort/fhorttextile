# DIAGNOSI E2 — les tres correccions de la QA d'E1

> **Data:** 2026-08-17 · **Patró A (READ-ONLY)** · staging `dev` (`f0c99481`).
> **Abast:** respondre les dues preguntes que el brief exigeix abans d'implementar (extraïbilitat
> del component de decisió · causa del bug de la porta R5) i **una tercera que la QA no havia
> vist**: E2b no és possible sense migració. Convenció: `fitxer:línia` · «NO EXISTEIX» = confirmat
> absent.

---

## 🚨 P0 · E2b EXIGEIX UNA MIGRACIÓ (i el brief no ho podia saber)

El brief demana, com a criteri de QA:

> «confirmar sense canvi crea presa amb valor=teòrica **i `liniaTeContingut` la distingeix**»

**Avui això és impossible.** `PieceFittingLine` **NO TÉ cap camp** que digui «algú ha mesurat
aquesta línia»: el predicat és **inferit**, i les dues bandes infereixen igual —

- [taulaPresaPerTalla.js:44-50](../../frontend/src/utils/taulaPresaPerTalla.js#L44)
- [fitting/esdeveniments.py:29-36](../../backend/fhort/fitting/esdeveniments.py#L29) (bessona declarada)

```python
return float(linia.valor_real) != float(linia.valor_teoric)
```

Una línia neix amb `valor_real = valor_teoric` ([fitting/services.py:351](../../backend/fhort/fitting/services.py#L351)).
Per tant **«confirmar sense canvi» produeix exactament l'estat del naixement**, i cap predicat
derivat de valors el pot distingir. Camps de `PieceFittingLine`
([fitting/models.py](../../backend/fhort/fitting/models.py)): `valor_teoric`, `valor_real`, `nota`,
`decisio`, `capa`, `instancia`, `garment`. **Cap marca de gest.**

💡 **PROPOSTA (a validar) — l'única via que preserva la llei:** un camp explícit
`presa_at` (DateTimeField null) a `PieceFittingLine`, i `linia_te_contingut` passa a:

```
presa_at != null  → True          (marca EXPLÍCITA del gest)
altrament        → el predicat d'avui  (compatibilitat amb les files existents)
```

Això **no relaxa** la llei d'E1: la reforça. Avui la llei diu «existir no és haver mesurat» i ho
**endevina** pels valors; amb el camp ho **sap**. I el cas que la QA demana —confirmar la teòrica
tal qual— deixa de ser indistinguible del naixement.

⚠️ Sense aquest camp, E2b només es pot lliurar a mitges: el pre-omplert fantasma sí, però
«confirmar sense canvi» seria **una presa invisible** per a la fitxa tècnica, el Repàs i la
Comprovació —les tres superfícies que criden `linia_te_contingut`—, que és el defecte que E1 va
existir per matar.

---

## BLOC 1 · E2c — el component de decisió ÉS EXTRAÏBLE (via A)

**Veredicte: VIA A — reutilitzar el component existent dins d'Escalat. Cost baix.**

El component de decisió de `/models/1379?tab=Mesures&task_id=372` **no és una pàgina**: és
`CheckMeasureEditor` amb la font `fittingSource`, muntat a
[ModelSheet.jsx:1314-1315](../../frontend/src/pages/ModelSheet.jsx#L1314).

### Res hi està clavat a la ruta

| Necessita | D'on surt avui | Ho pot donar `PropagatedEditor`? |
|---|---|---|
| `model` | prop | ✅ ja té `modelInfo` |
| `source` | `fittingSource` importat | ✅ mateix import |
| `sourceCtx.fittingSession` | efecte de `?fitting_session=` | ✅ **la presa ja el porta**: `session.id` a [escalat_presa_views.py:120](../../backend/fhort/fitting/escalat_presa_views.py#L120) |
| `readOnly` | prop | ✅ ja el té |
| `onFeedback` / `onResolved` | props | ✅ trivials |
| `taskId` (el rellotge) | `editTaskId` de ModelSheet | ⚠️ **l'ha d'obrir ell** (`models.openTask(id,'size_check',sessionId)`) |

**La sessió PRIMA val**: `resolvePieceFitting`
([measureSources.jsx:46-63](../../frontend/src/components/model/measureSources.jsx#L46)) només
llegeix `fittingSession.id`; si no hi ha `piece_fittings` a la mà, crea la peça i, amb el 409
`piece_exists`, rellegeix la sessió sencera. O sigui que **un objecte `{id}` ja serveix** — i la
presa, a més, ja porta `piece_fitting_id` ([:89](../../backend/fhort/fitting/escalat_presa_views.py#L89)).

**Per tant NO cal component nou i NO hi ha contracte paral·lel**: mateix component, mateixa font,
mateixes portes de servidor (`piece-fitting-lines/<id>/` per veredicte i nota). L'única cosa nova
és **qui obre el rellotge** de la tasca `size_check`, i és una crida que ja existeix.

**Veredicte Bloc 1: llest. Via A.**

---

## BLOC 2 · El bug de la porta R5 — causa exacta

**Símptoma (QA d'Agus):** `?tab=Mesures&fitting_session=<id>` aterra al **mode d'edició de POM
(deltes)**, no a la sessió de fitting.

### La cadena

1. La porta construeix la URL a [PropagatedEditor.jsx:241-242](../../frontend/src/pages/PropagatedEditor.jsx#L241):
   `` `...?tab=Mesures&fitting_session=${presa?.session?.id ?? ''}` `` — **sense `task_id`**.
2. Sense `task_id`, entren en joc **DOS efectes independents i asíncrons**:
   - [ModelSheet.jsx:737-745](../../frontend/src/pages/ModelSheet.jsx#L737) — `fittingSessions.get(...)` → `setFittingSession(...)`
   - [ModelSheet.jsx:752-765](../../frontend/src/pages/ModelSheet.jsx#L752) — `models.openTask(...)` → `setEditing('Mesures')`
3. El render decideix la font a [ModelSheet.jsx:1315](../../frontend/src/pages/ModelSheet.jsx#L1315):
   ```jsx
   source={fittingSession ? fittingSource : null}
   ```
   **`null` = la font `check`**, que en mode treball és la taula de Definició POM **amb
   `RegleEditCell` (els deltes)** ([CheckMeasureEditor.jsx:362](../../frontend/src/components/model/CheckMeasureEditor.jsx#L362)).

**🔑 LA CAUSA NO ÉS UN PARÀMETRE IGNORAT: és que el PERDEDOR DE LA CURSA CAU A LA SUPERFÍCIE
EQUIVOCADA.** Si `setEditing('Mesures')` aterra abans que `setFittingSession`, es renderitza el
mode treball **sense sessió** → editor de POMs, amb el rellotge de `size_check` corrent al damunt.

### I hi ha un camí DETERMINISTA, no només una cursa

`fitting_session=${presa?.session?.id ?? ''}` produeix **`fitting_session=` (buit)** quan la presa
no té sessió. Llavors `sp.get('fitting_session')` és `''`, que en JS és **falsy**:

- [:739](../../frontend/src/pages/ModelSheet.jsx#L739) `if (!fittingSessionParam)` → `setFittingSession(null)`
- [:754](../../frontend/src/pages/ModelSheet.jsx#L754) `&& fittingSessionParam &&` → **`openTask` no es crida mai**

…i la porta no obre res. El mateix passa si el `get` de la sessió falla (404, sessió esborrada).

### La llei ja escrita que això incompleix

El mateix fitxer, 370 línies més amunt, ja ho diu ([ModelSheet.jsx:385-386](../../frontend/src/pages/ModelSheet.jsx#L385)):

> «Sense sessió no hi ha pantalla de fitting, i **val més no entrar que entrar a una ALTRA taula
> que se li assembla**»

Aquella llei es va aplicar al **botó ③** i **no al camí per URL**. És el patró de sempre: la llei
existeix i té un forat a la porta del costat.

### Qui més passa per aquest forat

Segons l'acta de [:752-753](../../frontend/src/pages/ModelSheet.jsx#L752), el camí
`?fitting_session=` sense `task_id` també el fan servir **la fulla de convocatòria** i el
**redirect de `/fittings/<id>`**. O sigui que **retirar només la porta R5 no tanca el forat**.

💡 **PROPOSTA (a validar):** el mínim que ho tanca és **no caure a la font `check` mentre hi hagi
`fitting_session` a la URL i la sessió no s'hagi resolt** — esperar, i si no arriba, dir-ho. Un
canvi acotat al render, que aplica al camí per URL la llei que el botó ③ ja compleix.

**Veredicte Bloc 2: llest. Causa identificada, i el forat és més ample que la porta R5.**

---

## BLOC 3 · E2a — la fusió de columnes és neta

Les dues columnes es construeixen a
[fittingGridAdapter.jsx:buildEscalatGroups](../../frontend/src/components/model/fittingGridAdapter.jsx)
(`teorica` · `propagada`) i s'omplen a
[cellaEscalat.js](../../frontend/src/utils/cellaEscalat.js):

```js
history: { teorica, propagada: vigent }   // teorica = presa?.teoric ?? vigent
```

**FET:** són iguals **per construcció** mentre no s'hagi propagat, i el propi fitxer ho diu
([cellaEscalat.js:12-16](../../frontend/src/utils/cellaEscalat.js#L12)): «Mentre no es propagui, és
igual que la teòrica; quan algú decideix a la base i propaga, es MOU».

⚠️ **El que NO es pot perdre en fusionar**: `baseValue` de la cel·la activa ha de seguir sent **la
TEÒRICA**, no la vigent — és el referent del vermell R1
([cellaEscalat.js:19-23](../../frontend/src/utils/cellaEscalat.js#L19)). La fusió és de
**presentació** (dues `historyCols` → una); el contracte de la cel·la activa **no es toca**.

**Veredicte Bloc 3: llest.** Fusió de presentació, `baseValue` intacte.

---

## TAULA FINAL

| Pregunta del brief | Resposta | Cost |
|---|---|---|
| E2c · el component és extraïble? | **SÍ — via A**, `CheckMeasureEditor` + `fittingSource` dins d'Escalat. Cap contracte paral·lel | **S** + obrir el rellotge `size_check` |
| Per què cau la porta R5 al mode POM? | **Dos efectes asíncrons i el perdedor cau a la font `check`**; i `fitting_session=` buit no obre res (determinista) | **XS** al render |
| E2a · la fusió perd el vermell R1? | **NO**, si `baseValue` segueix sent la teòrica | **XS** |
| E2b · es pot fer sense migració? | **NO.** `PieceFittingLine` no té marca de gest | **M** — 1 camp + migració + les 2 bessones |

## LÍMITS DECLARATS

1. **El bug R5 no s'ha reproduït en viu** (seria escriure: obrir tasca + sessió). La causa és
   lectura de codi, i el camí determinista (`fitting_session=` buit) és **inferit del `??  ''`**,
   no mesurat.
2. **No s'ha auditat** si la fulla de convocatòria i el redirect de `/fittings/<id>` passen
   `task_id`: l'acta de `:752` diu que no, i s'ha pres per bona. **PENDENT DE VERIFICAR.**
3. `presa_at` és **una proposta**, no una decisió: canvia una taula de domini i el predicat
   bessó. Decisió d'Agus (Patró C).
