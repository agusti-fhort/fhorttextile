# DIAGNOSI — L'ordre del run del model (`Model.size_run_model`)

**Data:** 2026-07-22 · **Patró A (read-only)** · **Entorn:** staging `/var/www/ftt-staging`, branca `dev`
**Cas real:** model 166 (Blusa MEREDITH, `BRW-FW26-0004`) a PROD → run `XS·S·L·XXS·M`
**Decisió:** Patró C d'Agus sobre aquest document. Aquí no s'ha escrit res: cap commit, cap escriptura a BD.

**Diagnosis germanes** (mateix dia, altre eix — es complementen, no es contradiuen):
`DIAGNOSI_REFACTOR_WIZARD_RUN_CLIENT_2026-07-22.md` tracta el referent del run del **DOCUMENT/ruleset**
(llei S24, helper `run_del_document`). Aquesta tracta el run del **MODEL**. Són els dos costats de la
mateixa moneda: allà es va arreglar la **derivació** de regles, aquí queda oberta l'**aplicació**.

---

## 0. Veredicte en una línia

`Model.size_run_model` **no té cap porta d'escriptura que ordeni**. Les 9 vies censades copien
l'ordre que els arriba (usuari, document, Excel). El motor de grading (`_apply_rule`) compta els
passos **per posició dins d'aquesta llista**, de manera que un run desordenat no produeix un ordre
de columnes lleig: produeix **valors graduats numèricament incorrectes, amb el signe invertit** per a
les talles apendades per sota de la base. I hi ha un **segon defecte independent** que ordenar el run
NO arregla: els runs *no contigus* (amb forats) també graduen malament.

---

## 1. Cens d'escriptors de `Model.size_run_model`

Camp: `models_app.Model.size_run_model` — `CharField`, etiquetes separades per `·` (es tolera `;`).
Ordre canònic de referència: `SizeDefinition.ordre` (`pom/models.py:345`), related_name `talles`,
amb `Meta.ordering = ['size_system','ordre']`.

**Cap de les vies següents ordena per `SizeDefinition.ordre`.** No existeix cap helper
d'ordenació al camí d'ESCRIPTURA — només n'hi ha a la LECTURA (`patterns/adapters.py:512`,
`pom/grading_utils.py:221`).

| # | Fitxer:línia | Via / endpoint | Font de les etiquetes | Veredicte |
|---|---|---|---|---|
| 1a | `models_app/views.py:590` (`_resolve_garment_def`, def a :549) | `create_model_wizard` (:618) → `POST /api/v1/models/create-wizard/` (`urls.py:195`) | `d['size_run']` — **string cru del payload** | **COPIA TAL QUAL** |
| 1b | `models_app/views.py:590` | `update_model_step2` (:775/:784) → `PATCH /api/v1/models/<id>/update-step2/` (`urls.py:196`) | Idem, cru | **COPIA TAL QUAL** — ⬅ **via del 166** |
| 2 | `models_app/extraction_views.py:1831` | `import_session_confirmar_view` → `POST /api/v1/import-sessions/<token>/confirmar/` (`urls.py:88`) | `extraccio['sizes']` = **ordre del DOCUMENT** (extracció LLM), traduït 1:1 per `_to_tenant` | **ORDRE DEL DOCUMENT** |
| 3 | `models_app/tech_sheet_views.py:308` | `TechSheetCreateModelView.post` → `POST /api/v1/models/create-from-sheet/` (`urls.py:129`) | `extracted['sizes']` | **ORDRE DEL DOCUMENT** (i sense `size_system` assignat) |
| 4a | `models_app/bulk_import_service.py:579` (`_build_model`) | `POST /api/v1/bulk-import/<id>/commit/` (`urls.py:147`) | `_split_sizes(g('run_talles'))` (:329) = **ordre de la cel·la d'Excel** | **ORDRE DE L'EXCEL** |
| 4b | `models_app/bulk_import_service.py:592` (`_complement_existing`) | mateix commit, branca complements | Idem (només si el camp és buit) | **ORDRE DE L'EXCEL** |
| 5 | `models_app/management/commands/restaura_size_run.py:61-62` | `manage.py restaura_size_run [--apply]` | Recorre el run existent i només **tradueix etiquetes** | **CONSERVA L'ORDRE EXISTENT** (explícit) |
| 6 | `models_app/management/commands/clone_model_for_qa.py` | `manage.py clone_model_for_qa` | Còpia d'instància (`pk=None; save()`) | **CÒPIA IDÈNTICA** |
| 7 | `models_app/serializers.py:218-223` `ModelDetailSerializer` | `ModelViewSet` → `POST/PUT/PATCH /api/v1/models/[<pk>/]` (`urls.py:44`) | Qualsevol valor del client | **VIA OBERTA, SENSE CAP GUARD** |
| 8 | `frontend/src/pages/ModelWizard.jsx:105` i `:361` | `sizingResult` → `skeletonPayload()` → `createWizard`/`updateStep2` | `selectedSizes.join('·')` | **ORDRE DE CLIC DE L'USUARI** |

Cap altra superfície escriu el run: Escalat/Grading, `SizeSetDetail.jsx`, `PropagatedEditor.jsx`,
`pom/grading_views.py`, `pom/wizard_views.py` i `fitting/*` són **totes lectores**.

### 1.1 El punt d'entrada del backend no valida res

`models_app/views.py:585-592`:

```python
    if d.get('size_run'):
        fields['size_run_model'] = d['size_run']
    if d.get('base_size'):
        fields['base_size_label'] = d['base_size']
    return fields, None
```

Ni split, ni comprovació que les etiquetes pertanyin al `SizeSystem` que s'assigna **a la mateixa
crida**, ni ordenació. El test `tests_sembra_grading.py:303-306` segella el comportament: s'envia
`{'size_run': 'S·M'}` i es llegeix `'S·M'`.

### 1.2 L'origen del desordre: el toggle de chips APENDA

`frontend/src/pages/ModelWizard.jsx:622-626`:

```jsx
{sizeDefs.map(s => {
  const label = s.etiqueta || s.size_label || s.label
  const active = selectedSizes.includes(label)
  return <Chip key={label} active={active}
    onClick={() => setSelectedSizes(prev => active ? prev.filter(x => x !== label) : [...prev, label])}
  >{label}</Chip>
})}
```

Els chips es **pinten** en ordre canònic (`sizeDefs` ve de `SizeSystem.talles`, amb el `Meta.ordering`),
però l'estat desa **ordre de clic**: `[...prev, label]`. Marcar XXS i M sobre un run `XS·S·L` dona
literalment `XS·S·L·XXS·M`. No hi ha cap `.sort()` abans de `selectedSizes.join('·')` (:105).

### 1.3 Els fixes F1.x del bug 174 no van crear el desordre, però el van fer permanent

Commits del 16→22/07: `743b7cc` (F1.1+F1.2), `d28590d` (F1.3), `0251d9f` (F1.4), `2fa51b9` (F1.5),
`a7366b1` (F1.6). Els que toquen la rehidratació del pas 3 són **`743b7cc`** i **`a7366b1`**.

Abans de `743b7cc`, l'efecte `[selSystem]` feia sempre `setSelectedSizes(labels)` — és a dir,
entrar al pas 3 en edició **re-normalitzava el run a l'ordre canònic** (destructivament: per això
es va arreglar, era el bug 174). Després:

```js
+    const run = modelSizeRun.split(/[·,;]/).map(x => x.trim()).filter(Boolean).filter(l => labels.includes(l))
+    const vius = run.length ? run : labels
+    setSelectedSizes(vius)
```

`run` es construeix per `filter` sobre el **split del string desat**, no sobre `labels`: conserva
l'ordre de `size_run_model`. I el guard F1.2 `runCapDins(selectedSizes, labels)`
(`ModelWizard.jsx:29`, `every(l => labels.includes(l))`) és una comprovació de **pertinença de
conjunt, insensible a l'ordre** — un run desordenat "cap dins" el sistema, per tant es conserva i
es re-desa desordenat.

`a7366b1` (F1.6) només separa `desat` de `run` per anomenar les talles perdudes; no canvia la
semàntica d'ordre.

> **Conclusió sobre el 174:** el fix és correcte en el seu propòsit (no destruir el run desat), però
> va eliminar **l'única re-normalització implícita que existia** en tot el sistema. Sense una porta
> d'escriptura que ordeni, qualsevol run desordenat ara es rehidrata i es re-desa desordenat per
> sempre. El 174 no és la causa; és el que va treure la xarxa.

---

## 2. Via exacta del 166

**`PATCH /api/v1/models/166/update-step2/`**, disparat des del **pas 3 del ModelWizard en mode
edició**. És l'única superfície de producte que permet ampliar el run d'un model existent
(via 1b + via 8 del cens).

Seqüència reconstruïda:

1. El model tenia `size_run_model = 'XS·S·L'`, `base_size_label = 'S'`.
2. L'usuari obre el pas 3 en edició → `743b7cc` rehidrata `selectedSizes = ['XS','S','L']`
   (ordre desat, no canònic).
3. Clica el chip **XXS** → `[...prev, 'XXS']` = `['XS','S','L','XXS']`.
4. Clica el chip **M** → `['XS','S','L','XXS','M']`.
5. `sizingResult.size_run = 'XS·S·L·XXS·M'` → `update-step2` → `views.py:590` ho desa cru.

### 2.1 Estat a staging (verificat)

```
pk=166 codi=BRW-FW26-0004 nom='Blusa MEREDITH'
  size_system='Alpha EU — Women'  run='XS·S·L'  base='S'
  ordre canònic: ['XXS','XS','S','M','L','XL','XXL','3XL']
```

Staging encara té el run **pre-ampliació**. Confirma que l'ampliació és un acte d'usuari fet a PROD
i que el snapshot de staging és anterior. Nota: `XS·S·L` ja està *ordenat*, però és **no contigu**
(falta la M) — vegeu §3.3.

### 2.2 Reproducció a staging — FETA, amb rollback (bug confirmat al 100%)

No s'ha fet per `curl` (hauria persistit). S'ha executat la **vista real** `update_model_step2` amb
`APIRequestFactory` + `force_authenticate` dins un `transaction.atomic()` amb rollback forçat, sobre
el model de QA **267 `[QA-S10] Blusa RUFUS STARS`**. Script a `scratchpad/repro_size_run.py`.

```
ABANS  : BRW-26-FW-0036 | [QA-S10] Blusa RUFUS STARS | run= XS·S·L | base= S | sys= ALPHA_EU_W
CANÒNIC: XXS·XS·S·M·L·XL·XXL·3XL
PAYLOAD: {'garment_type_item_id': 5, 'size_system_id': 29, 'size_run': 'XS·S·L·XXS', 'base_size': 'S'}
HTTP   : 200 {"id":267,"codi_intern":"BRW-26-FW-0036","regles_materialitzades":34}
PERSISTIT (dins tx): XS·S·L·XXS      ← apendat, ni ordenat ni rebutjat
>> ROLLBACK fet
DESPRÉS: XS·S·L | base= S            ← estat original intacte
```

Afegir **XXS** (per sota de la talla base `S`) la deixa **al final** del run. El backend retorna
**200 OK sense cap avís** — i, de propina, materialitza 34 regles sobre aquest run. La BD de staging
ha quedat exactament com era.

---

## 3. Impacte al motor — evidència executada, no assumida

Mètode: s'ha importat el `_apply_rule` **real** (`pom/services.py:785`) i s'hi han passat regles
sintètiques sobre els dos runs. Valor base 100.0, talla base `S`. Cap accés a BD, cap escriptura.
Script reproduïble a l'annex A.

### 3.1 LINEAR — el signe s'inverteix

`increment = 3` (idèntic amb `increment=3` clàssic i amb la forma canònica `increment_base=3`):

| talla | run desordenat `XS·S·L·XXS·M` | run canònic `XXS·XS·S·M·L` | error |
|---|---|---|---|
| XXS | **106.0** | 94.0 | **+12.0 — i al costat equivocat de la base** |
| XS | 97.0 | 97.0 | ✔ (coincideix per casualitat) |
| S | 100.0 | 100.0 | ✔ (és la base) |
| M | **109.0** | 103.0 | +6.0 |
| L | **103.0** | 106.0 | −3.0 |

La causa és `pom/services.py:182`:

```python
        for i, size_label in enumerate(size_run):
            steps = i - base_idx  # negative = smaller size, positive = larger
```

`base_idx = size_run.index('S') = 1`. XXS és a l'índex 3 → `steps = +2`. El motor la tracta com
**dues talles per sobre** de la S quan canònicament n'és **dues per sota**. No és un error de
magnitud: és un error de **direcció**.

**Veredicte del punt 1 del brief: CONFIRMAT.** La propagació LINEAR és incorrecta amb run desordenat.

### 3.2 LINEAR amb break — catastròfic

El break es resol per etiqueta però s'aplica **per índex** (`pom/services.py:819-830`):

```python
        break_idx = None
        if rule.talla_break_label and size_run:
            norm = [_norm_label(x) for x in size_run]
            tl = _norm_label(rule.talla_break_label)
            if tl in norm:
                break_idx = norm.index(tl)
        ...
        for j in path:
            total += brk if (break_idx is not None and j >= break_idx) else ib
```

Amb `increment_base=3`, `increment_break=6`, `talla_break_label='L'`:

| talla | desordenat | canònic | error |
|---|---|---|---|
| XXS | **112.0** | 94.0 | **+18.0** |
| M | **118.0** | 103.0 | **+15.0** |
| L | 106.0 | 109.0 | −3.0 |

`break_idx = run.index('L') = 2`. Com que XXS (3) i M (4) queden **després** de L a la llista, la
condició `j >= break_idx` és certa per a tot el seu recorregut: **la talla més petita del run gradua
amb l'increment extrem tres vegades**. El llindar "a partir de L, salt gran" perd tot el significat
quan la posició no correspon a la mida.

### 3.3 ⚠️ Segon defecte, independent: els runs NO CONTIGUS

Ordenar el run **no és suficient**. El run real del 166 a staging, `XS·S·L`, ja està ordenat — i
tot i així gradua malament, perquè li falta la M:

| talla | run ordenat amb forat `XS·S·L` | run canònic contigu `XXS·XS·S·M·L` |
|---|---|---|
| L | **103.0** | 106.0 |

El motor compta `S→L` com **1 pas** perquè són posicions adjacents a la llista; canònicament en són
**2**. `steps` mesura la distància dins la llista, no dins el sistema de talles.

Això és exactament el mateix defecte, en el costat de l'APLICACIÓ, que ja està documentat en el
costat de la DERIVACIÓ a `pom/grading_utils.py:347`, que cita el 166 pel seu nom:

> «És el bug del model 166 (run XS·S·L contra document XXS-L: S→L salta la M i val 2 passos → fals
> «×2» amb `talla_break_label='L'`)»

La llei S24 (`run_del_document`, `grading_utils.py:221`, commit `544b8c4` del Patró B en curs) va
arreglar el referent de la **derivació**. El referent de l'**aplicació** encara és la posició crua.

### 3.4 STEP

Falla igual: els deltes es busquen per etiqueta però el recorregut és per índex
(`pom/services.py:853-864`). Amb `valors_step = {'XXS':2,'XS':2,'M':3,'L':3}`:

| talla | desordenat | canònic |
|---|---|---|
| XXS | **105.0** = base + δ(L) + δ(XXS) | 96.0 |
| M | **108.0** | 103.0 |

### 3.5 Superfícies contaminades (col·laterals)

- **`talla_break_pos` derivat d'un run desordenat.** `models_app/views.py:3125`
  (`rule.talla_break_pos = run.index(tbl)`) i `views.py:1334-1338` (`_break_pos`) persisteixen una
  posició calculada sobre el run tal com està. **Avui és inert**: `_apply_rule` resol el break per
  ETIQUETA, no llegeix aquest camp (és «cache opcional», `pom/models.py:728` i `:742`). Però queda
  un valor mentider a la BD, esperant el primer lector que se'l cregui.
- **El frontend propaga el desordre més enllà d'Escalat.** `orderedSizes`
  (`FittingDetail.jsx:18`, duplicat literal a `SessionPanel.jsx:13`) ordena **pel run del model**:
  ```js
  const run = (sizeRun || '').replace(/;/g, '·').split('·').map(s => s.trim()).filter(Boolean)
  const ordered = run.filter(s => present.has(s))
  ```
  El comentari diu «Mai alfabètic», i és correcte — però tampoc no és canònic. Fitting mostra les
  columnes desordenades igual que Escalat.
- **Cap lector valida.** Els ~12 punts que fan `split('·')` sobre el camp (`services.py:144`,
  `grading_views.py:73`, `extraction_views.py:567/638/1639/1851`, `views.py:1108/1926/2017/2135`,
  `fitting/views.py:649`, `adapters.py:512`) accepten qualsevol ordre sense dir res.

---

## 4. Cens de dades

### 4.1 Resultat a STAGING (executat, read-only)

Tenants existents: `public`, `fhort`, `los`.

| Categoria | `fhort` | `los` |
|---|---|---|
| OK (ordenat canònicament) | **1004** | 0 |
| DESORDENAT | **0** | 0 |
| ETIQUETA_FORA (etiqueta que no és al `SizeSystem`) | **0** | 0 |
| SENSE_SISTEMA | **0** | 0 |

**Staging està net.** Cap run desordenat. Això no absol el codi: confirma que la corrupció és un
**fet d'edició posterior a la sembra**, no un defecte de la sembra. Els 1004 models de `fhort` són
sembrats (LOSAN SS27 i companyia) i van entrar per vies que reben llistes ja ordenades; el 166 és
un dels pocs que ha passat per mans d'usuari al wizard.

⚠️ **El cens que importa és el de PROD**, on viu el 166 amb `XS·S·L·XXS·M`. L'script de §4.2 està
preparat per executar-s'hi tal qual al proper deploy. **Aquí NO s'ha executat contra PROD.**

### 4.2 Script del cens — read-only, repetible a PROD

Guardat a `scratchpad/cens_size_run.py`. Cap escriptura: només `.values()` i `.iterator()`.

```python
"""
CENS READ-ONLY: ordre canònic de size_run_model vs SizeSystem.talles.ordre

ÚS (STAGING o PROD — NOMÉS LECTURA):
    cd /var/www/ftt-staging/backend
    venv/bin/python manage.py shell -c "exec(open('/ruta/cens_size_run.py').read())"

Variables opcionals:
    FTT_SCHEMA   schema del tenant (default: 'fhort')
    FTT_MAX_ROWS files màximes per llistat (default: 40)
"""
import os
from django_tenants.utils import schema_context

SCHEMA = os.environ.get('FTT_SCHEMA', 'fhort')
MAX_ROWS = int(os.environ.get('FTT_MAX_ROWS', '40'))
SEPARADORS = '·;,'


def parse_run(raw):
    """Parseja el run tolerant a '·', ';' i ',' (imports antics)."""
    if not raw:
        return []
    txt = raw
    for s in SEPARADORS[1:]:
        txt = txt.replace(s, SEPARADORS[0])
    return [x.strip() for x in txt.split(SEPARADORS[0]) if x.strip()]


def main():
    from fhort.models_app.models import Model
    from fhort.pom.models import SizeDefinition

    # Ordre canònic per sistema: {size_system_id: {etiqueta: (ordre, id)}}
    canon = {}
    for sd in SizeDefinition.objects.all().values('size_system_id', 'etiqueta', 'ordre', 'id'):
        canon.setdefault(sd['size_system_id'], {})[sd['etiqueta'].strip()] = (sd['ordre'], sd['id'])

    # NO_CONTIGU (S24b): run ordenat però amb forats respecte del sistema. NO és un error i
    # NO s'ha de reparar — un client pot no fabricar la M. És INFORMATIVA: des que el motor
    # gradua en espai de sistema, aquests runs compten la distància real; abans col·lapsaven
    # (S->L valia 1 pas en comptes de 2), i per tant els seus GradedSpec antics són sospitosos.
    cats = {'OK': [], 'NO_CONTIGU': [], 'DESORDENAT': [], 'ETIQUETA_FORA': [],
            'SENSE_SISTEMA': [], 'RUN_BUIT': []}

    qs = (Model.objects.select_related('size_system')
          .only('id', 'codi_intern', 'nom_prenda', 'size_run_model',
                'base_size_label', 'size_system__id', 'size_system__codi')
          .order_by('id'))

    for m in qs.iterator():
        run = parse_run(m.size_run_model)
        if not run:
            continue  # models sense run: fora del cens
        if not m.size_system_id:
            cats['SENSE_SISTEMA'].append((m, run, None))
            continue
        mapa = canon.get(m.size_system_id, {})
        fora = [l for l in run if l not in mapa]
        if fora:
            dins = [l for l in run if l in mapa]
            esperat = sorted(dins, key=lambda l: (mapa[l][0], mapa[l][1]))
            cats['ETIQUETA_FORA'].append((m, run, esperat + [f'?{l}' for l in fora]))
            continue
        esperat = sorted(run, key=lambda l: (mapa[l][0], mapa[l][1]))
        if esperat != run:
            cats['DESORDENAT'].append((m, run, esperat))
            continue
        # Ordenat. Contigu = les posicions al sistema són consecutives.
        idx = sorted(mapa[l][0] for l in run)
        if idx == list(range(idx[0], idx[0] + len(idx))):
            cats['OK'].append((m, run, esperat))
        else:
            cats['NO_CONTIGU'].append((m, run, esperat))

    total = sum(len(v) for v in cats.values())
    print('=' * 78)
    print(f'CENS size_run_model — schema={SCHEMA} — models amb run no buit: {total}')
    print('=' * 78)
    for k in ('OK', 'NO_CONTIGU', 'DESORDENAT', 'ETIQUETA_FORA', 'SENSE_SISTEMA'):
        print(f'  {k:<16} {len(cats[k]):>6}'
              + ('   (legítim — informatiu, no a reparar)' if k == 'NO_CONTIGU' else ''))
    print()

    for k in ('DESORDENAT', 'ETIQUETA_FORA', 'NO_CONTIGU'):
        rows = cats[k]
        if not rows:
            continue
        print('-' * 78)
        print(f'{k} — {len(rows)} models (mostrant fins a {MAX_ROWS})')
        print('-' * 78)
        print(f"{'id':>6} | {'codi_intern':<18} | {'nom':<26} | {'sistema':<16} | "
              f"{'base':<6} | run actual -> run esperat")
        for m, run, esperat in rows[:MAX_ROWS]:
            ss = m.size_system.codi if m.size_system_id else '—'
            print(f"{m.id:>6} | {(m.codi_intern or ''):<18.18} | {(m.nom_prenda or ''):<26.26} | "
                  f"{ss:<16.16} | {(m.base_size_label or '—'):<6.6} | "
                  f"{'·'.join(run)}  ->  {'·'.join(esperat)}")
        if len(rows) > MAX_ROWS:
            print(f'  ... i {len(rows) - MAX_ROWS} més')
        print()

    if cats['SENSE_SISTEMA']:
        print('-' * 78)
        print(f"SENSE_SISTEMA — {len(cats['SENSE_SISTEMA'])} models (mostrant fins a {MAX_ROWS})")
        print('-' * 78)
        for m, run, _ in cats['SENSE_SISTEMA'][:MAX_ROWS]:
            print(f"{m.id:>6} | {(m.codi_intern or ''):<18.18} | {(m.nom_prenda or ''):<26.26} | "
                  f"run={'·'.join(run)}")
        print()


with schema_context(SCHEMA):
    main()
```

Notes d'invocació: **no cal `tenant_command`** — el `schema_context` del propi script fa la feina.
Per a un altre tenant: `FTT_SCHEMA=los venv/bin/python manage.py shell -c "..."`. L'script no
reordena res: només classifica i imprimeix el `run esperat` al costat de l'actual.

**Actualització 2026-07-22 vespre (sprint S24b):** la categoria `NO_CONTIGU` ja hi és. Resultat a
staging després del sanejament: **990 OK · 14 NO_CONTIGU · 0 DESORDENAT · 0 ETIQUETA_FORA**. Els 14
són tots `XS·S·L` del lot Brownie (models 164-175, inclòs el **166**): runs legítims que fins ara
graduaven amb la distància col·lapsada (S→L = 1 pas en comptes de 2). No s'han de reparar — el motor
en espai de sistema ja els compta bé — però els seus `GradedSpec` **anteriors** al canvi de motor són
sospitosos i volen re-propagació conscient (D-10).

---

## 5. 💡 Proposta (NO implementada — decisió d'Agus)

### Tall 1 — Una sola porta d'escriptura que ordeni SEMPRE

El principi ja existeix i està escrit al repo: `run_del_document` (`grading_utils.py:221`, llei S24)
ordena les etiquetes del document contra el run del sistema fent servir `canonical_size_label` com a
pont únic (salva XXL↔2XL, que un `upper+strip` no cobreix):

```python
    canon_to_tenant = {canonical_size_label(e): e for e in run_sistema}
    ordre = {e: i for i, e in enumerate(run_sistema)}
    ...
    doc_run = sorted(presents, key=lambda e: ordre[e])
    return doc_run, desconegudes
```

**El mateix principi ha de manar al run del MODEL.** Proposta: un helper germà, p. ex.
`run_del_model(etiquetes, size_system)` a `pom/grading_utils.py`, que retorni
`(run_ordenat, etiquetes_desconegudes)` i que sigui **l'únic camí** cap a
`Model.size_run_model`. Cablat a:

- `models_app/views.py:590` — cobreix d'una sola vegada `create-wizard` **i** `update-step2` (vies
  1a i 1b, i per tant el 166).
- `extraction_views.py:1831`, `tech_sheet_views.py:308`, `bulk_import_service.py:579/592`.
- `serializers.py` — o bé passar `size_run_model` a `read_only_fields` del `ModelDetailSerializer`
  (via 7), o bé donar-li un `validate_size_run_model` que cridi el mateix helper. Deixar una via
  `PATCH` oberta sense guard fa inútils totes les altres.

Complement barat al frontend: `.sort()` per l'índex de `sizeDefs` a `ModelWizard.jsx:105`, perquè
l'usuari **vegi** el run ordenat abans de desar. És cosmètic — la llei ha de ser al backend.

### Tall 2 — Sanejament de les dades ja desordenades

Management command idempotent amb `--dry-run` per defecte (mateix patró que `restaura_size_run.py`,
que ja té l'esquelet i el pont d'etiquetes fet). Reordena `size_run_model` per `SizeDefinition.ordre`
i **no toca res més**. Les etiquetes fora del sistema s'informen i **no** es reordenen ni
s'esborren: són un cas diferent que vol decisió humana.

⚠️ **El sanejament canvia valors de grading ja calculats.** Un model desordenat amb `GradedSpec`
vigents té cel·les numèricament incorrectes; reordenar el run i re-propagar les canviarà. Cal
decidir si el command re-propaga, o si només marca els models afectats perquè algú els revisi —
sobretot si hi ha `GradingVersion` **aprovades/segellades** (guard D-1, `services.py:730`).

### Tall 3 — Guard al motor (i el defecte del run no contigu)

`generate_graded_specs` (`services.py:136-152`) ja valida sistema, run, base i pertinença de la
base al run. Hi falten dues comprovacions, **abans** de calcular res:

1. **Etiqueta fora del sistema** → `ValueError` clar, no càlcul silenciós.
2. **Run desordenat** respecte de `SizeDefinition.ordre` → `ValueError` clar.

I la peça de fons, que és la decisió gran:

3. **`steps` i `break_idx` s'han de derivar de l'ordre del `SizeSystem`, no de la posició a la
   llista.** Sense això, un run legítimament no contigu (`XS·S·L`, un client que no produeix la M)
   continua graduant malament fins i tot després dels talls 1 i 2 — §3.3. Alternativa mínima si es
   vol evitar tocar el motor: exigir runs contigus i bloquejar-ho al guard. Això és una restricció
   de producte, no un detall tècnic.

> Zona intocable segons `CLAUDE.md` (POMs / `generate_graded_specs`). El tall 3 s'anota, no es toca
> sense encàrrec explícit.

### 🚩 Banderes per al CTO

1. **El tall 3.3 és el que decideix si això queda arreglat de veritat.** Talls 1+2 ordenen; el 166
   passaria de `XS·S·L·XXS·M` a `XXS·XS·S·M·L`, que és un run **contigu** i graduaria bé. Però un
   model amb run legítimament escapçat continua malament, en silenci.
2. **Radi del sanejament**: cal saber quantes `GradingVersion` aprovades pengen de models
   desordenats abans de decidir si es re-propaga.
3. **Coordinació amb el Patró B en curs** (`referent-document`, commits `544b8c4`/`975efaa`/`3f4acfe`):
   el tall 1 toca `grading_utils.py`, que és territori seu. L'helper germà s'hi ha d'afegir després
   que tanqui, o en un fitxer propi.

---

## Annex A — script de l'exemple en fred

Reproduïble sense BD (`backend/venv/bin/python`, cap escriptura):

```python
import django, os, sys
sys.path.insert(0, '/var/www/ftt-staging/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fhort.settings')
django.setup()
from fhort.pom.services import _apply_rule

class R:
    def __init__(s, logica, increment=0, ib=None, brk=None, tbl=None, vs=None):
        s.logica = logica; s.increment = increment; s.increment_base = ib
        s.increment_break = brk; s.talla_break_label = tbl; s.valors_step = vs
        s.pom = None; s.pom_id = 1

def taula(run, rule, titol, base='S'):
    b = run.index(base)
    print(f"\n--- {titol} | run={'·'.join(run)} base={base}(idx {b}) ---")
    for i, l in enumerate(run):
        v, _ = _apply_rule(rule, 100.0, i - b, i, b, size_run=run, warnings=[])
        print(f"  {l:4} idx={i} steps={i-b:+d}  ->  {v}")

DES = ['XS', 'S', 'L', 'XXS', 'M']    # run persistit del 166 a PROD
CAN = ['XXS', 'XS', 'S', 'M', 'L']    # ordre canònic ALPHA_EU_W

taula(DES, R('LINEAR', increment=3), "LINEAR inc=3 DESORDENAT")
taula(CAN, R('LINEAR', increment=3), "LINEAR inc=3 CANONIC")
taula(DES, R('LINEAR', ib=3, brk=6, tbl='L'), "LINEAR break@L DESORDENAT")
taula(CAN, R('LINEAR', ib=3, brk=6, tbl='L'), "LINEAR break@L CANONIC")
taula(DES, R('STEP', vs={'XXS': 2, 'XS': 2, 'M': 3, 'L': 3}), "STEP DESORDENAT")
taula(CAN, R('STEP', vs={'XXS': 2, 'XS': 2, 'M': 3, 'L': 3}), "STEP CANONIC")
# Defecte independent: run ordenat pero amb FORAT (estat real del 166 a staging)
taula(['XS', 'S', 'L'], R('LINEAR', increment=3), "LINEAR run ORDENAT amb FORAT")
```
