# REPORT F2.1 · BACKEND · exposar el que faltava — 🛑 STOP de tram

**Data:** 08/08/2026 · **Commits:** 147 · 148 · 149 · **CAP PUSH** · HEAD `23204f1b`
**Migració:** `pom.0074_fittype_choices_al_dia` (aplicada) · **`ftt-staging` reiniciat**

---

## F2.1a · La forma de la resposta de `/poms/` deixa de variar per fila

**No s'hi ha afegit cap bloc nested.** Els 9 camps ja hi eren, plans i read-only; un nested els
hauria duplicat. Agus va acceptar el canvi de camí (duplicar camps = la mateixa malaltia que
duplicar enumeracions, llei 1).

**El mecanisme, escrit perquè no torni a passar:** quan el `source` d'un camp travessa un `None`,
`get_attribute()` de DRF llança `AttributeError`; i com que `read_only=True` implica
`required=False`, la branca de rescat acaba a `SkipField` i **el camp cau de la resposta**
(`rest_framework/fields.py:450-456`). Amb `allow_null=True` la mateixa branca retorna `None` i
la clau es queda.

**Es toquen els 21 camps que pengen de `pom_global`, no només els 9**: el concern és que la forma
no variï, i arreglar-ne nou de vint-i-un hauria deixat el mateix contracte inestable per als altres.

### Els TRES estats, ara distingibles

| Estat | Què vol dir | Quants (BD sencera) |
|---|---|---|
| `null` | **no lligat al catàleg global** | 122 / 396 |
| `""` | **lligat, però sense informar** | 149 / 396 |
| valor | dada de debò | **125 / 396 (32%)** |

**Verificat contra dades reals** (200 files): les 200 tenen **exactament les mateixes claus**
(`len(set(map(frozenset, claus))) == 1`), i a `scope` surten 74 `null` · 58 buides · 68 amb dada.

🚩 **Troballa de DADES per a la Montse, no de codi: el 68% del catàleg no té el «com es mesura».**
149 POMs estan lligats al catàleg i buits, i 122 no hi estan lligats. La UI ho ha de dir amb
paraules diferents (F2.3) i no maquillar-ho amb guions.

---

## F2.1b · Els choices de `FitType` es posen al dia

Declaraven **5** codis; la taula en té **10**. I un dels cinc —`LOOSE`— **no existeix com a fila**.

**Comporta de l'ordre, comprovada abans de treure'l:** `LOOSE` té **0 files** a `public`, `fhort`
i `los`, **0 runs** i **0 rulesets** que hi apuntin. Es podia treure sense aturar-se.

Ordre dels choices = `display_order` de la taula, no alfabètic.

### La prova que la migració no genera SQL

```
$ manage.py sqlmigrate pom 0074
BEGIN;
--
-- Alter field codi on fittype
--
-- (no-op)
COMMIT;
```

### Auditoria SQL DESPRÉS d'aplicar (a la BD, no al log)

| Comprovació | Resultat |
|---|---|
| `information_schema` · `public.pom_fittype.codi` | `character varying(20)`, `NOT NULL` — **intacta** |
| files a `public.pom_fittype` | 10 |
| files amb `codi='LOOSE'` | **0** |
| diferència choices ↔ codis de la taula | **CAP** |

Aplicada amb `migrate_schemas` (mai `--schema`, llei de la casa).

**`FitTypeSerializer` exposa `nom_cat` i `nom_es`.** Era l'única raó per la qual una UI catalana
de fits havia d'inventar-se les etiquetes: `Target` i `ConstructionType` ja les servien i aquest
no — i és exactament el que fa la maqueta de la size library. Les 10 files les tenen informades.

---

## F2.1c · `GET /api/v1/vocabulari/` — les enumeracions, publicades

Mateix patró i mateixa raó que `mesures/diccionari/`: eren als `choices` de sempre i **cap
endpoint les publicava**.

| Clau | N | Codis | Font |
|---|---|---|---|
| `regims_graduacio` | **5** | LINEAR · STEP · FIXED · ZERO · **EXCEPTION** | `GradingRule.LOGICA_CHOICES` |
| `fases_model` | 6 | Pending · Dev · Proto · SizeSet · PP · TOP | `Model.FASE_CHOICES` |
| `estats_model` | 4 | Nou · EnCurs · EnRevisio · Tancat | `Model.ESTAT_CHOICES` |
| `fases_tasca` | 6 | Disseny · Dev. tècnic · Prototip · Mostres · Preproducció · Producció | `TaskType.FASE_CHOICES` |

Cada element `{codi, etiqueta}`, **en l'ordre en què el model els declara** — l'ordre és part de
la dada. Lectura pura, sense paràmetres. **Verificat contra el servei reiniciat: 200 i les
quatre llistes completes.**

**Els codis no es tradueixen.** `LINEAR`, `Pending`, `TOP` són dada de domini com un codi de POM.
Si algun dia una llista s'ha de traduir, és decisió d'Agus i el lloc és una taula.

### 🛑 La decisió d'abast que vas preveure — resolta acotant, no endevinant

**Hi ha DUES «fases» al backend i no són la mateixa cosa:** el cicle de vida del MODEL
(`Pending…TOP`) i la fase d'una TASCA (`Disseny…Producció`). Les dues s'exposen, amb **claus
explícites i separades**, perquè cadascuna és inequívoca pel seu compte. No he hagut de triar-ne
una: el que calia era **no barrejar-les**.

🚩 **`components/PhaseStepper.jsx` les barrejava, i és codi mort.** Declara 8 fases empalmant
**tres** vocabularis: `'Nou'` i `'Tancat'` són d'`ESTAT_CHOICES`, cinc són fases de tasca, i
`'Tècnic'` **no existeix enlloc** (la real és `'Dev. tècnic'`). El grup i18n `model_phases` en
té les 8 claus, mirall de la invenció. **No el munta ningú** (`grep` de `PhaseStepper` fora del
seu propi fitxer: cap resultat). Va a F2.2 per esborrar-lo, no per corregir-lo.

---

## Verificació

| Control | Resultat |
|---|---|
| `manage.py check` | ✅ net a cada commit |
| Suite `fhort.pom` | ✅ **exit 0** |
| Suite `fhort.models_app` + `fhort.tasks` | v. addenda (corrent en tancar el report) |
| `sqlmigrate 0074` | ✅ `-- (no-op)` |
| Auditoria SQL post-migració | ✅ columna intacta, 0 `LOOSE`, diferència CAP |
| `systemctl restart ftt-staging` | ✅ `active` |
| Endpoints contra el servei viu | ✅ `/vocabulari/` 200 · `/fit-types/` amb `nom_cat` |

**Zones intocables respectades:** no s'ha tocat el motor de graduació, ni els POMs com a dada, ni
el `codi_client` duplicat de `pom_pommaster` (queda per al cens a part, com manava l'ordre).

## 🛑 STOP

F2.1 tancada. **F2.2 (matar els duplicats al frontend) queda desbloquejada**: ja hi ha d'on
llegir-ho tot —`mesures/diccionari/` per a capes i instàncies, `/vocabulari/` per a règims,
fases i estats, `/fit-types/` amb `nom_cat` per als fits— i per tant **cap enumeració necessita
fallback al client**.
