# DIAGNOSI · 5 TROBALLES DE LA FORMACIÓ · 2026-08-26

> **READ-ONLY ABSOLUT.** Cap escriptura al domini, cap migració, cap suite, cap fix, cap
> commit, cap push. L'únic fitxer creat és aquest.

## PAS -1 · IDENTITAT, BASE I ENTORN

| Fet | Valor |
|---|---|
| `hostname` | `fhort-assessment` ✅ |
| `ftt-staging.service` · `WorkingDirectory` | `/var/www/ftt-staging/backend` ✅ |
| `ActiveState` | `active` · `ExecMainStartTimestamp` **2026-08-26 10:26:28 UTC** |
| **HEAD de `dev`** | **`cb23382e`** — *«merge: F4.1 · reconeixedor de peces v1 (banc de tenant, corpus apagat)»* |
| `dev` vs remot | **140 commits per davant d'`origin/main`** · 13 per davant d'`origin/dev` |
| BD viva | `ftt_staging` a **127.0.0.1:5433** (`postgresql@18-main`) · schemes `public` · `fhort` · `los` |
| `ps` en començar | **net** — cap suite, cap migració en marxa |

**Nota de context:** el `gunicorn` s'ha reiniciat a les **10:26:28 UTC**, o sigui que serveix
codi de `cb23382e`. Les dades de PROD que dona el brief (conflicte `BT`, entregues i rondes,
PDF al client) es prenen com a donades i **no s'han tornat a mesurar**.

---
---

# T1 · EL WIZARD D'IMPORTACIÓ NO PINTA NOMS DE POM

## VEREDICTE: **MIXT** — dos defectes de signe contrari sota un sol símptoma

| Camí | Arriba el nom? | El pinta el front? | |
|---|---|---|---|
| Desplegable «tria'n un del catàleg» | ✅ **SÍ** (`nom_ca`/`nom_en` resolts) | ❌ **NO** (llegeix `nom_client` cru) | **ARRIBA I NO ES PINTA** |
| Files «Es vincularà a…» | ❌ **NO** (`nom_client` cru) | — | **NO ARRIBA** |
| Candidats del conflicte 409 | ❌ **NO** (`nom_client` cru) | — | **NO ARRIBA** |

## FET · LA CAUSA COMUNA ÉS UN CAMP CRU, I LA DADA MESURADA

Al schema `fhort`, sobre `pom_pommaster` (144 actius):

| amb `nom_client` buit | …i **amb** `pom_global` | …i orfes | …**sense cap nom enlloc** |
|---:|---:|---:|---:|
| **103** | **103** | 0 | **7** |

I els codis del símptoma hi són tots:

| id | `codi_client` | `nom_client` (tenant) | `pom_global.nom_en` | `pom_global.nom_ca` |
|---:|---|---|---|---|
| 906 | `B` | *(buit)* | Foot width | Ample de peu |
| 908 | `BF` | *(buit)* | Foot length | Llarg de peu |
| 907 | `BT` | *(buit)* | Leg opening girth | Contorn de boca de camal |

**El nom existeix sempre** (llevat de 7 files). No és un forat de sembra: és el cas normal del
catàleg v4/v5 —POM del tenant lligat al canònic— i el que falla és **qui el va a buscar**.

## FET · EL DESPLEGABLE REP LA DADA I LA LLENÇA

`search_poms_view` ([wizard_views.py:115](backend/fhort/pom/wizard_views.py#L115)), servit a
[pom/urls.py:50](backend/fhort/pom/urls.py#L50), emet **sis** camps de nomenclatura al seu `_fila`:

- [wizard_views.py:295-296](backend/fhort/pom/wizard_views.py#L295-L296) — `codi_client` · `nom_client` ← **CRU**
- [wizard_views.py:299-300](backend/fhort/pom/wizard_views.py#L299-L300) — `nom_ca` · `nom_en` = `noms_de(p)[…]` ← **RESOLT**
- …més `client_code` / `client_name_en` / `client_name_local` a la secció del client.

`noms_de` ([nomenclatura.py:178](backend/fhort/pom/nomenclatura.py#L178)) és la font única de la
llei **ÀLIES > TENANT > GLOBAL** (22/08) i **cau al global quan el tenant no té nom**. Per als
103, `nom_en`/`nom_ca` arriben plens.

El front pinta només el camp cru:
[ImportWizard.jsx:167](frontend/src/components/ImportWizard/ImportWizard.jsx#L167) —
`<b>{…c.codi_client}</b>{' · '}{c.nom_client}` → **«B · »**. I l'`onPick`
([:158-159](frontend/src/components/ImportWizard/ImportWizard.jsx#L158-L159)) propaga només
`{id, codi_client, nom_client}`: `nom_ca`/`nom_en` **es perden allà i ja no tornen**.

**`ImportWizard.jsx` no importa `nomsDePom`.** El resolutor de les DUES LÍNIES existeix i és
[nomenclaturaPom.js:60-71](frontend/src/utils/nomenclaturaPom.js#L60-L71) (`canonic = nom_canonic_model
|| nom_en || nom_client || local`, i `local` a la segona línia només si diu una cosa diferent).
Els imports del fitxer són [:1-17](frontend/src/components/ImportWizard/ImportWizard.jsx#L1-L17).

## FET · LES FILES I ELS CANDIDATS NO LA REBEN

Cap dels dos passa per `noms_de` **ni fa `select_related('pom_global')`**:

- Files del pas 2 — [extraction_views.py:1430](backend/fhort/models_app/extraction_views.py#L1430):
  `'pom_nom': pm_efectiu.nom_client if pm_efectiu else None` (i `weak_suggestion` a [:1438](backend/fhort/models_app/extraction_views.py#L1438)).
- Candidats del 409 — [extraction_views.py:1920](backend/fhort/models_app/extraction_views.py#L1920),
  dins de `_candidats_de_codi` ([:1907](backend/fhort/models_app/extraction_views.py#L1907)).

Punts de pintura: [ImportWizard.jsx:212](frontend/src/components/ImportWizard/ImportWizard.jsx#L212) ·
[:255](frontend/src/components/ImportWizard/ImportWizard.jsx#L255) ·
[:1324](frontend/src/components/ImportWizard/ImportWizard.jsx#L1324) ·
[:1554](frontend/src/components/ImportWizard/ImportWizard.jsx#L1554). El literal és
`"Es vincularà a {{codi}} · {{nom}}"` ([ca.json:4217](frontend/src/i18n/ca.json#L4217)) — el
«· » despenjat del símptoma és aquest `{{nom}}` buit.

## RELACIÓ AMB `d0877bc5` I AMB T5

**Amb el hotfix: CAP.** `d0877bc5` (merge de `5306df7e`, *«/api/schema/ tornava 500 — `name_es`
declarat i fora de `fields`»*) toca **només** `backend/fhort/pom/serializers.py`: hi afegeix
`get_name_es` + `name_es` a `GarmentPOMMapSerializer.Meta.fields` i a `_POMDisplayMixin.CAMPS`.
Aquells són serializers de DRF del catàleg i del mapa peça↔POM; **els tres camins del wizard són
`@api_view` que retornen diccionaris a mà i no passen per cap serializer.** El hotfix és, això
sí, la prova que la llei de la font única s'estava estenent camí a camí — i que aquests tres es
van quedar fora.

**Amb T5: SÓN DUES CAPES DIFERENTS, i es sumen.** T1 és el **nom de catàleg**
(`nom_client`/`nom_ca`/`nom_en`); T5 és la **ⓘ de traducció** (`TranslationCache` + proveïdor),
que és un *overlay* per damunt del nom. A `/poms` les dues fallen alhora: el nom canònic pot
faltar (T1) **i** la ⓘ mor sencera (T5) → la fila es queda **només amb el codi**. Són fixos
independents; **cap dels dos és causa de l'altre**.

## RADI (R13)

| # | Fitxer | Línies | Canvi |
|---|---|---|---|
| 1 | `frontend/src/components/ImportWizard/ImportWizard.jsx` | 158-159, 167 | Pintar amb `nomsDePom`; propagar `nom_ca`/`nom_en` a l'`onPick` |
| 2 | `backend/fhort/models_app/extraction_views.py` | 1430, 1438 | `noms_de(...)` + ⚠️ `select_related('pom_global')` a la consulta de dalt |
| 3 | `backend/fhort/models_app/extraction_views.py` | 1907-1924 | `_candidats_de_codi`: `noms_de` + `select_related('pom_global')` |
| 4 | `frontend/src/components/ImportWizard/ImportWizard.jsx` | 212, 255, 1324, 1554 | Els quatre punts de pintura |

**Tests:** `frontend/src/utils/nomenclaturaPom.test.js` prova `nomsDePom`, però **cap test toca
el wizard amb un POM de `nom_client` buit**. Banc natural: el POM **906 (`B`)**.
⚠️ **N+1**: sense el `select_related` el fix compra una query per fila.

---
---

# T2 · ELS BREAKS NO ACCEPTEN DECIMALS

## VEREDICTE: **FRONT** — i són **DOS inputs**, no un

## FET · LA BD I EL BACKEND JA ELS ACCEPTEN

| taula | columna | tipus |
|---|---|---|
| `models_app_modelgradingrule` · `pom_gradingrule` | `increment_break` | **`numeric(6,2)`** |
| `models_app_modelgradingrule` · `pom_gradingrule` | `breaks` | `jsonb` |

El validador és `valida_breaks` ([grading_regime.py:168](backend/fhort/pom/grading_regime.py#L168)),
cridat des de [pom/serializers.py:456](backend/fhort/pom/serializers.py#L456). El Δ hi passa per
`_f` ([grading_regime.py:59-66](backend/fhort/pom/grading_regime.py#L59-L66)):

```python
def _f(v):
    if v is None or v == '': return None
    try: return float(str(v).replace(',', '.'))     # ← LA COMA, EXPLÍCITA
    except (TypeError, ValueError): return None
```

La lectura, `intervals_de` ([grading_utils.py:1111](backend/fhort/pom/grading_utils.py#L1111)),
fa `float(brk_raw)`. **Cap porta del backend rebutja un decimal.**

## FET · EL DEFECTE ÉS EL *MOMENT* DEL PARSEIG

[EditorIntervals.jsx:303-308](frontend/src/components/grading/EditorIntervals.jsx#L303-L308):

```jsx
<input type="text" inputMode="decimal" size={4} autoFocus
  value={esborrany.delta === null || esborrany.delta === undefined ? '' : esborrany.delta}
  onChange={e => toca({ delta: num(e.target.value) })}      // ← parseja a CADA TECLA
  style={inputDelta} />
```

`num` ([:100-104](frontend/src/components/grading/EditorIntervals.jsx#L100-L104)) **és correcta i
ja accepta la coma**. El defecte és que **es crida per tecla sobre un valor controlat pel número
que en surt**:

| es tecleja | `num()` retorna | `value` repinta | |
|---|---|---|---|
| `1` | `1` | `"1"` | ✅ |
| `1.` | `Number("1.")` = `1` | `"1"` | ❌ **el punt desapareix mentre s'escriu** |
| `1,` | `Number("1.")` = `1` | `"1"` | ❌ **la coma desapareix** |

**L'estat intermedi `"1."` no és representable** → no s'arriba mai al decimal, amb cap dels dos
separadors. No hi ha `type="number"`, ni `step`, ni `pattern`: `type="text" inputMode="decimal"`
ja és el correcte.

## FET · EL CONTRAST — LA POLÍTICA JA ÉS ESCRITA I UN GERMÀ LA COMPLEIX

[MeasureGrid.jsx:51-53](frontend/src/components/model/MeasureGrid.jsx#L51-L53) i
[:256-257](frontend/src/components/model/MeasureGrid.jsx#L256-L257):

> *«L'input editable és `type=text inputMode=decimal` perquè la coma s'hi pugui escriure
> (`type=number` la rebutja segons locale abans d'arribar a `onChange`). (…) Es desa sempre el
> valor canònic (**`toNum` normalitza la coma al commit**).»*

| Superfície | Línia | `onChange` | |
|---|---|---|---|
| Mesures (carril) | [EditableTable.jsx:1836-1842](frontend/src/components/EditableTable/EditableTable.jsx#L1836-L1842) | guarda `txt` cru | ✅ |
| Graduació del model · Δ base | [GraduacioSuperficie.jsx:468-470](frontend/src/components/grading/GraduacioSuperficie.jsx#L468-L470) | **cru**; `num()` al submit ([:309](frontend/src/components/grading/GraduacioSuperficie.jsx#L309)) | ✅ |
| **Jocs de regles · Δ base** | [JocsDeRegles.jsx:874](frontend/src/components/grading/JocsDeRegles.jsx#L874) | `num(e.target.value)` | ❌ **mateix defecte** |
| **Breaks · Δ d'interval** | [EditorIntervals.jsx:307](frontend/src/components/grading/EditorIntervals.jsx#L307) | `num(e.target.value)` | ❌ **el del símptoma** |

⚠️ `JocsDeRegles.jsx:874` té la forma exacta: `valorCamp`
([:295](frontend/src/components/grading/JocsDeRegles.jsx#L295)) repinta `String(v)` del número
que `edita` ([:486-497](frontend/src/components/grading/JocsDeRegles.jsx#L486-L497)) va desar.
**El Δ base dels jocs de regles tampoc no admet decimals** — no era al brief.

## RADI (R13)

| # | Fitxer | Línies | Canvi |
|---|---|---|---|
| 1 | `frontend/src/components/grading/EditorIntervals.jsx` | 303-308 | Esborrany en TEXT; `num()` al confirmar. ⚠️ `potConfirmar` avui jutja el número |
| 2 | `frontend/src/components/grading/JocsDeRegles.jsx` | 874 (+295, +486) | El mateix: cru a `edicions`, `num()` al desar |

**Cap canvi de backend ni migració.** **Tests:** `backend/fhort/pom/test_tram_f_intervals.py`
(**ja passa** amb decimals) i `frontend/src/utils/gradingRegime.test.js`. **Cap toca l'input.**
🚩 Un test de regressió ha de teclejar `"1"`,`"."`,`"5"` en **tres gestos**: un que passi `"1.5"`
sencer dona **verd sense mesurar res**.

---
---

# T3 · TAXONOMIA DE FAMÍLIES D'INSTÀNCIA

> **NO ES REPARA RES.** Substrat mesurat + proposta marcada com a tal.

## VEREDICTE: **EL MECANISME JA ESTÀ CONSTRUÏT; EL QUE FALTA ÉS DADA**

De les quatre famílies que Agus declara, **només dues existeixen**; **6 dels 10 slugs de posició
no tenen família**, i per això exclouen tot. **`Left`+`Front` ja és legal avui** — mesurat.

## (a) ON VIU L'ESTRUCTURA I ON S'IMPOSA L'EXCLUSIÓ

| Peça | On | Què és |
|---|---|---|
| **Vocabulari** (slugs, eix, sufix, ordre) | taula `pom.MeasurementInstance` ([pom/models.py:282](backend/fhort/pom/models.py#L282)) | **DADA** — 12 files, idèntiques als 3 schemes |
| **Famílies** (quin slug és de quina) | constant `MeasurementInstance.SUBEIXOS` ([pom/models.py:366-371](backend/fhort/pom/models.py#L366-L371)) | **CODI** — a posta: geometria de la peça, no dada de tenant |

```python
SUBEIXOS = (('CARA', ('front', 'back')), ('LATERAL', ('left', 'right')))
```

**L'exclusió s'imposa a QUATRE llocs, i tots quatre diuen el mateix:**

| # | On | Fitxer:línia |
|---|---|---|
| 1 | Regla de domini | [`error_de_combinacio`, pom/models.py:385-423](backend/fhort/pom/models.py#L385-L423) |
| 2 | Publicació | [identity_views.py:84](backend/fhort/pom/identity_views.py#L84) (`subeix` per fila) · [:101](backend/fhort/pom/identity_views.py#L101) (`subeixos` en ordre) |
| 3 | Mirall al front | [`xoquen`, diccionariMesures.js:112-120](frontend/src/utils/diccionariMesures.js#L112-L120) · [`clauExclusio`, :95-100](frontend/src/utils/diccionariMesures.js#L95-L100) |
| 4 | Handler dels xips | [`triaTram`, instanciaTria.js:52-65](frontend/src/components/instancia/instanciaTria.js#L52-L65) · [`triaAlModal`, :80-92](frontend/src/components/instancia/instanciaTria.js#L80-L92) |

La llei tal com la diu el codi (i és **exactament** la que Agus descriu): eixos diferents →
conviuen · mateix eix, **sub-eixos diferents → conviuen** · mateix sub-eix → xoquen · **algun
sense sub-eix → xoquen** *(el comportament d'abans, conservat)*.

### 🔑 MESURAT CONTRA LA BD VIVA (schema `fhort`)

```
left-front   -> LEGAL       left-right -> IL·LEGAL (mateix sub-eix LATERAL)
back-left    -> LEGAL       front-back -> IL·LEGAL (mateix sub-eix CARA)
left-relaxed -> LEGAL       top-left   -> IL·LEGAL («top» no té sub-eix)
                            cf-left    -> IL·LEGAL («cf» no té sub-eix)
```

**«Triar Front desactiva Left/Right» NO es reprodueix a staging.** Lectures, per probabilitat:

1. **Es va prémer un slug SENSE família** (`Top`,`Bottom`,`CF`,`CB`,`Side seam`,`Waistband seam`):
   aquests **sí** desactiven tota la resta, per disseny d'avui. **Són 6 dels 10 xips** — l'explicació
   més econòmica.
2. **PROD servia codi ranci.** Els 5 commits d'instàncies v2 (`4e1ebc60`·`dd81e6ef`·`c277ab55`·
   `952c9654`·`448c3a3b`) **sí que són a `origin/main`** (verificat), però el gunicorn serveix el
   codi de quan va arrencar. Sense `subeix` al payload, `subeixDe` torna `''` → **`xoquen` dona
   cert per a TOTA parella del mateix eix** → **la posició es comporta com UN grup exclusiu**.
   👉 *És literalment la forma del símptoma. Es tanca amb una sola lectura: `GET /api/v1/mesures/diccionari/`
   a PROD porta `subeix` a les files?*
3. Migració `pom/0080` i sembra desaparellades en algun schema de PROD.
4. `dev` va **140 commits** per davant d'`origin/main`.

## (b) COM ES MATERIALITZA A BD: **COMPOSICIÓ, i ja és viva**

El slug **ja és compost** amb separador `-` (`regles.instancia_separador`,
[identity_views.py:110](backend/fhort/pom/identity_views.py#L110)); el front el desmunta per
trams des de sempre ([capaInstancia.js:117-121](frontend/src/utils/capaInstancia.js#L117-L121)).

### 🔑 El cens del 25/08 deia «9 slugs PLANS». **Ja no és cert.**

| taula | valors vius (schema `fhort`) |
|---|---|
| `fitting_gradedspec` | `relaxed`46 · `extended`41 · `bottom`35 · `top`35 · `waistband_seam`30 · `cf`15 · `cb`15 · `front`6 · `back`6 |
| `fitting_piecefittingline` | `relaxed`36 · `extended`31 · `bottom`25 · `top`25 · `waistband_seam`20 · `cf`10 · `cb`10 · `front`6 · `back`6 |
| `models_app_basemeasurement` | `relaxed`5 · `top`4 · `extended`4 · `bottom`4 · `waistband_seam`2 · **`front-left`1** · **`extended-right`1** · **`relaxed-right`1** · `cf`1 · `cb`1 · `front`1 · `back`1 |
| `models_app_measurementchangelog` | `bottom`9 · `top`9 · `extended`8 · `relaxed`6 · `waistband_seam`2 · **`front-left`1** · **`extended-right`1** · **`relaxed-right`1** · `cf`1 · `cb`1 · `front`1 · `back`1 |
| `models_app_sizecheckline` | `relaxed`2 · `extended`1 · `bottom`1 · `top`1 |
| `pom_garmentpommap` | *(cap fila amb instància)* |

**Tres slugs compostos ja són a la BD.** La composició no és hipòtesi: **ja funciona**.

### 🚨 TROBALLA · L'ORDRE CANÒNIC EL DECIDEIX UN ATZAR ALFABÈTIC

L'ordre dels trams **és load-bearing per a la clau única** (`left-relaxed` vs `relaxed-left` =
dues files per a la mateixa germana). El docstring de `composaInstancia`
([diccionariMesures.js:177-182](frontend/src/utils/diccionariMesures.js#L177-L182)) diu
**«posició abans que estat»**. **El codi no fa això:** `pesCanonic`
([:165-170](frontend/src/utils/diccionariMesures.js#L165-L170)) pren l'ordre de
`Object.keys(dicc.instancies)`, i el backend el construeix amb `order_by('eix', …)`
([identity_views.py:75](backend/fhort/pom/identity_views.py#L75)) — **alfabètic**. Mesurat:

```
claus de `instancies` (el que veu pesCanonic):        ['ESTAT', 'POSICIO']
`eixos`  (el que veu dimensionsDe/eixPrincipal):      ['POSICIO', 'ESTAT']
```

**Ordres OPOSATS.** `'ESTAT' < 'POSICIO'`, i prou. Per això la BD diu **`extended-right`** i
**`relaxed-right`** —l'estat davant— i no `right-extended`. **Les files vives donen la raó al
codi, no al docstring.** (`front-left` sí surt bé: l'ordre DINS la posició ve de `dicc.subeixos`,
que **sí** es declara explícitament.)

**Per què cap test ho va veure:** el fixture de
[diccionariMesures.test.js:39-57](frontend/src/utils/diccionariMesures.test.js#L39-L57) escriu
`instancies` amb **`POSICIO` primer** — un ordre que el servidor **no envia mai**. El test
[:82](frontend/src/utils/diccionariMesures.test.js#L82) passa en verd contra un payload irreal.

**Per què és una mina:** avui l'ordre és estable. El dia que entri un tercer eix o es reanomeni
un codi d'eix, **la mateixa germana compondrà un slug diferent** → la `UNIQUE` deixarà de casar
amb la fila existent → **fila nova en comptes d'update, amb 200 OK i en silenci.**

## (c) IMPACTE SOBRE LES CLAUS

### ✅ CAP UNIQUE ASSUMEIX MONOVALOR

Les **10** constraints úniques del schema tracten `instancia` com **una columna de text opaca**:

| taula | UNIQUE |
|---|---|
| `fitting_gradedspec` | `(grading_version_id, pom_id, size_label, capa, instancia, garment)` |
| `fitting_piecefittingline` | `(piece_fitting_id, pom_id, size_label, capa, instancia, garment)` |
| `models_app_basemeasurement` | `(model_id, pom_id, capa, instancia, garment)` |
| `models_app_modelgradingoverride` | `(model_id, pom_id, size_label, capa, instancia, garment)` |
| `models_app_sizecheckline` | `(size_check_id, pom_id, capa, instancia, garment)` |
| `models_app_pomplacement` | `(item_fitxer_id, pom_id, view_slot, capa, instancia)` |
| `pom_garmentpommap` · `pom_garmenttypepommap` · `pom_garmentgrouppommap` | `(…, pom_id, capa, instancia)` |
| `pom_itembasemeasurement` | `(base_set_id, pom_id, capa, instancia)` |

Un slug compost hi és **una cadena distinta i prou**. La condició de correcció **no és
l'esquema: és que el slug estigui en ordre canònic** — v. la troballa de (b).

### ✅ AMPLADA · ✅ LECTORS GENÈRICS

Les **12** columnes `instancia` són `varchar(**60**)`. Pitjor cas amb 4 famílies + estat
(`waistband_seam-back-left-extended`) = **33**. Marge de sobres.

- `_identitat_de_mesura` ([models_app/views.py:3828-3853](backend/fhort/models_app/views.py#L3828-L3853))
  passa `m.get('instancia') or ''` **tal qual**: opac.
- **Zero comparacions literals** a un slug simple en tot `backend/fhort/` i `frontend/src/`
  (`grep -E "instancia *(==|!=|===|!==) *'(left|right|…)'"` → cap ocurrència).
- `error_de_combinacio` **no jutja vocabulari desconegut** ([pom/models.py:396-398](backend/fhort/pom/models.py#L396-L398)).

### ⚠️ FIX F2 — no es trenca, però no sabrà escriure la germana

[FIX_F2_GARMENT_OVERRIDE_2026-08-25.md:72](docs/ordres/FIX_F2_GARMENT_OVERRIDE_2026-08-25.md#L72):
*«`capa` i `instancia` segueixen sent literals en aquesta porta. No és un oblit»*; i a
[:137](docs/ordres/FIX_F2_GARMENT_OVERRIDE_2026-08-25.md#L137) 🚩 *«La germana d'instància
segueix sense porta en aquest camí»*.

### 🚨 L'ÚNIC QUE ARROSSEGA L'ERA MONOVALOR: LA COMPLEMENTÀRIA

[`COMPLEMENTARIA`, diccionariMesures.js:25-30](frontend/src/utils/diccionariMesures.js#L25-L30)
va **de slug simple a slug simple**. Qui tria **quin** tram es gira és
[EditableTable.jsx:632-635](frontend/src/components/EditableTable/EditableTable.jsx#L632-L635)
(bessó a [:1601-1603](frontend/src/components/EditableTable/EditableTable.jsx#L1601-L1603)):

```js
const aGirar = trams.find(s => COMPLEMENTARIA[s] && eixDe(dicc, s) === principal)
            || trams.find(s => COMPLEMENTARIA[s])
```

**Desempata per EIX, no per SUB-EIX.** Amb `back`+`left` —tots dos `POSICIO`— agafa el primer i
gira la **cara**: partir «esquena esquerra» dona «davant esquerra», mai «esquena dreta». Avui
queda tapat; **amb quatre famílies, «quina família es gira?» no té resposta declarada enlloc.**

## (d) INVENTARI COMPLET · el que la UI ofereix avui

12 files, idèntiques a `public`, `fhort` i `los`:

| eix | slug | sufix | `display_order` | **família avui** |
|---|---|---|---:|---|
| POSICIO | `left` | `L` | 1 | **LATERAL** |
| POSICIO | `right` | `R` | 2 | **LATERAL** |
| POSICIO | `top` | `T` | 3 | — |
| POSICIO | `bottom` | `BM` | 4 | — |
| POSICIO | `cf` | `CF` | 5 | — |
| POSICIO | `cb` | `CB` | 6 | — |
| POSICIO | `side` | `S` | 7 | — |
| POSICIO | `waistband_seam` | *(buit)* | 8 | — |
| POSICIO | `front` | `F` | 9 | **CARA** |
| POSICIO | `back` | `B` | 10 | **CARA** |
| ESTAT | `relaxed` | *(buit)* | 1 | *(l'eix ja fa de família)* |
| ESTAT | `extended` | *(buit)* | 2 | *(l'eix ja fa de família)* |

La instància ÚNICA **no és una fila**: és `''` ([pom/models.py:347](backend/fhort/pom/models.py#L347)).

👉 **La proposta de taula de famílies va a part, al final del report.**

## RADI (R13) — si Agus aprova la taxonomia

| # | Fitxer | Línies | Canvi |
|---|---|---|---|
| 1 | `backend/fhort/pom/models.py` | 366-371 | `SUBEIXOS`: de 2 a 4 famílies. **L'únic canvi de llei** |
| 2 | `backend/fhort/pom/models.py` | 385-423 | **cap canvi** — `error_de_combinacio` ja és genèrica |
| 3 | `backend/fhort/pom/identity_views.py` | 84, 101 | **cap canvi** — ja emet `subeix`/`subeixos` |
| 4 | `frontend/src/utils/diccionariMesures.js` | 95-120 | **cap canvi** — `xoquen`/`clauExclusio` ja genèriques |
| 5 | `frontend/src/components/instancia/instanciaTria.js` | 52-92 | **cap canvi** — ja va per bloc d'exclusió |
| 6 | `diccionariMesures.js:25-30` + `EditableTable.jsx:632, 1601` | — | ⚠️ **SÍ**: declarar quina família gira la complementària |
| 7 | `backend/fhort/pom/identity_views.py` | 75 | ⚠️ **SÍ** *(independent)*: ordenar per `EIX_CHOICES`, no per alfabet |
| 8 | `frontend/src/utils/diccionariMesures.test.js` | 39-57 | ⚠️ **SÍ**: el fixture ha de dir el que la porta emet |
| 9 | `frontend/src/utils/capaInstancia.js` | 18-19, 75 | Comentaris: diuen «10 files»/«vuit posicions»; en són 12 i deu (🚩 censat el 25/08, encara viu) |

**🔑 De nou requadres, cinc són «cap canvi».** El mecanisme estava ben construït: això és una
ampliació de **dada** sobre una arquitectura que ja la preveia.

**Tests:** `backend/fhort/pom/test_instancies_posicio_v2.py` ·
`backend/fhort/pom/test_u2_r2_capa_instancia_api.py` ·
`frontend/src/components/instancia/instanciaTria.test.js` ·
`frontend/src/utils/diccionariMesures.test.js` (⚠️ fixture desalineat). Els quatre estan escrits
**contra `SUBEIXOS`**, no contra `front`/`back` a mà — **s'ha de veure, no suposar.**

---
---

# T4 · `gravar-pom` → 400: LA UX DEL REFÚS DE NOMENCLATURA

## VEREDICTE: **EL BACKEND SAP TOT EL QUE CAL I NO EN DIU RES**

El refús és **correcte de domini** i **inútil d'acció**: identifica la col·lisió, no la sortida.

## FET · LA VISTA I LA VALIDACIÓ

`gravar_pom_view` ([models_app/views.py:2384](backend/fhort/models_app/views.py#L2384)),
ruta `POST /api/v1/models/<id>/gravar-pom/` ([models_app/urls.py:225](backend/fhort/models_app/urls.py#L225)).

La validació de nomenclatura és
[views.py:2488-2497](backend/fhort/models_app/views.py#L2488-L2497):

```python
nomen = (m.get('nom_fitxa') or '').strip()
if nomen and model.customer_id:
    _xoc, _etiqueta = colisio_de_codi(model.customer_id, nomen, excloent_pom_id=int(pom_id))
    if _xoc is not None:
        errors.append(f'POM {pom_id}: la nomenclatura «{nomen}» ja és {_etiqueta} al catàleg '
                      f'd\'aquest client')
        continue
```

…i l'única sortida 400 del bloc és
[views.py:2511](backend/fhort/models_app/views.py#L2511): `Response({'errors': errors}, status=400)`.

**Aquesta vista només pot emetre DOS 400:**

| línia | cos |
|---|---|
| [2406](backend/fhort/models_app/views.py#L2406) | `{'error': 'measurements és obligatori'}` (**39 B**) |
| [2511](backend/fhort/models_app/views.py#L2511) | `{'errors': [...]}` ← **el dels reintents** |

*(El rang físic té resposta pròpia, **422**, a [:2506](backend/fhort/models_app/views.py#L2506) — mai es barreja.)*

## FET · ELS DOS COSSOS VISTOS (191 B i 105 B)

Tots dos són **`{'errors': [...]}` de la línia 2511** — l'aritmètica hi encaixa i cap altre 400
d'aquesta vista s'hi acosta. Mesurat amb el render compacte de DRF (`UNICODE_JSON=True` →
`ensure_ascii=False`, `«»` = 2 bytes cadascun):

| cos | bytes | lectura |
|---|---:|---|
| `{"error":"measurements és obligatori"}` | 39 | descartat |
| `{"errors":["Cal introduir almenys una mida base abans de gravar POM"]}` | 70 | descartat |
| **UNA** col·lisió, etiqueta de ~23 car. | **105** | ✅ **encaixa amb el cos petit** |
| **DUES** col·lisions, etiquetes de ~17-18 car. | ~180-191 | ✅ **encaixa amb el cos gran** |
| duplicat de fila (una entrada) | 141 | — |

> ⚠️ **Fet vs lectura:** els **valors 105 i 191 són fets**; l'atribució «una col·lisió» / «dues
> col·lisions» és una **lectura aritmètica**. No tinc el payload de PROD i **no reconstrueixo les
> cadenes exactes**. El que sí és fet: **cap dels dos pot venir d'una altra línia d'aquesta vista.**

## FET · QUÈ SAP EL BACKEND EN AQUEST PUNT, I QUE LLENÇA

La cadena és `colisio_de_codi` → `pom_del_codi`
([nomenclatura.py:75-88](backend/fhort/pom/nomenclatura.py#L75-L88)):

```python
alias = (CustomerPOMAlias.objects
         .filter(customer_id=customer_id, client_code__iexact=..., pom__isnull=False)
         .select_related('pom').first())
return alias.pom if alias else None      # ← L'ÀLIES ES LLENÇA AQUÍ
```

**L'objecte `CustomerPOMAlias` és a la mà i es descarta sencer.** Els camps que porta
([pom/models.py:697-745](backend/fhort/pom/models.py#L697-L745)) i que el missatge **podria** dir:

| camp | què diria | avui |
|---|---|---|
| `client_code` | el codi **amb la seva caixa real** (`BT` vs `bt`) | ❌ |
| `pendent_revisio` | **«pendent de revisió»** ← *el cas de PROD* | ❌ |
| `origen` (`DICCIONARI`·`IMPORT`·`MANUAL`·`MIGRACIO`·`MODEL`) | **«del diccionari BRW»** | ❌ |
| `description_en` / `description_local` | com el client l'anomena | ❌ |
| `es_instancia` | «és una repetició, no una mesura pròpia» | ❌ |
| `pom.pk` | **quin POM el té** → enllaç al cercador | ❌ |

Distribució viva a staging (154 àlies): **`DICCIONARI` 146** (0 pendents) · `IMPORT` 7 (5
pendents) · `MODEL` 1 (1 pendent). **6 pendents de revisió en total** — la població del cas de PROD.

I la constraint que hi ha al fons és real:
`uniq_pommaster_codi_client_ci ON fhort.pom_pommaster (upper(codi_client::text))`.

### 🚨 EL VINCLE AMB T1 · EL MISSATGE POT SER UNA TAUTOLOGIA

`_etiqueta` es construeix a [nomenclatura.py:104-105](backend/fhort/pom/nomenclatura.py#L104-L105):

```python
nom = (pom.nom_client or getattr(getattr(pom, 'pom_global', None), 'nom_en', '') or
       pom.codi_client or '').strip()
```

Comença per **`nom_client` cru** — el camp que **103 de 144 POMs tenen buit** (T1). Aquí sí hi ha
fallback al global, o sigui que se salva… **excepte per als 7 POMs sense cap nom enlloc**
(mesurat), on cau a `codi_client` i el refús es llegeix:

> **«BT» ja és BT al catàleg d'aquest client**

**I la porta germana és pitjor.** `create_model_pom_view`
([wizard_views.py:891](backend/fhort/pom/wizard_views.py#L891)) fa
`etiqueta_casa = (ja_hi_es.nom_client or codi_casa).strip()` — **sense cap fallback al global**.
Per als **103**, aquell missatge és tautològic sempre.

## FET · ON HO MOSTRA EL FRONT

[MeasuresEntryPanel.jsx:263-265](frontend/src/components/model/MeasuresEntryPanel.jsx#L263-L265):

```js
const msg = err?.response?.data?.error || err?.response?.data?.errors?.join?.(' · ')
  || t('model_measurements.save_pom_err')
setError(msg); setPomConfirmOpen(false)
```

Els errors **s'aplanen amb `' · '`** i es pinten com a **banda vermella de text pla**
([:284-286](frontend/src/components/model/MeasuresEntryPanel.jsx#L284-L286)). **Cap camp
estructurat es llegeix**, i `setPomConfirmOpen(false)` **tanca el modal**: qui rep el refús perd
el context del gest. Això explica els **3 reintents en viu** — el missatge no diu què canviar,
i tornar-hi és l'única acció que la pantalla ofereix.

## LECTURA · QUÈ CALDRIA PER UN REFÚS ACCIONABLE

**El model ja existeix a la casa i és el 409 de `create_model_pom_view`**
([wizard_views.py:892-900](backend/fhort/pom/wizard_views.py#L892-L900)), que retorna
**camps estructurats + una frase amb sortida**:

```python
return Response({'codi': 'CODI_CASA_OCUPAT', 'nomenclatura': codi,
                 'pom_id': ja_hi_es.pk, 'pom_nom': etiqueta_casa,
                 'message': f'«{codi}» ja és {etiqueta_casa} al catàleg. Fes-lo servir des del '
                            f'cercador, o dona-li una nomenclatura diferent.'}, status=409)
```

El comentari que el precedeix ([:881-888](backend/fhort/pom/wizard_views.py#L881-L888)) ja diu la
doctrina: *«la sortida no és inventar un codi: és **DIR AMB QUÈ XOCA** (…) el que necessita no és
un codi nou, és que li ensenyin l'existent»*. **`gravar-pom` no ha rebut aquesta llei.**

Per arribar a «*BT ja és X del diccionari BRW, pendent de revisió — revisa'l o tria'n un altre*»
calen tres coses, i cap és estructural:

1. **Que `colisio_de_codi` torni l'ÀLIES**, no només el POM (avui el llença a una línia).
2. **Que el missatge digui `origen` + `pendent_revisio` + `pom_id`**, com el 409 germà.
3. **Que el front llegeixi camps**, no una cadena — i **que no tanqui el modal** en refusar.

## RADI (R13)

| # | Fitxer | Línies | Canvi |
|---|---|---|---|
| 1 | `backend/fhort/pom/nomenclatura.py` | 75-88, 96-105 | `pom_del_codi`/`colisio_de_codi` tornen també l'ÀLIES; `_etiqueta` per `noms_de` (mata la tautologia) |
| 2 | `backend/fhort/models_app/views.py` | 2488-2497, 2511 | Error estructurat (`codi`, `pom_id`, `alias_origen`, `pendent_revisio`) al costat del text |
| 3 | `backend/fhort/pom/wizard_views.py` | 891 | `etiqueta_casa` per `noms_de` — avui **sense fallback al global** |
| 4 | `frontend/src/components/model/MeasuresEntryPanel.jsx` | 263-266 | Llegir els camps; **no tancar el modal** en refús |

⚠️ **`colisio_de_codi` té dos cridadors** (`gravar_pom_view` i `create_model_pom_view`): canviar-ne
la signatura els toca tots dos — que és **justament el que fa que el missatge sigui un de sol**.

**Tests:** `backend/fhort/pom/test_s45_d_alta_pom_cataleg.py` cobreix l'alta i el 409.
**Cap test cobreix el 400 de col·lisió de `gravar-pom`**, i cap assereix el TEXT del refús.
🚩 Banc natural: un dels **6 àlies `pendent_revisio`** de staging.

---
---

# T5 · `translate/pom` EN LOT → 400

## VEREDICTE: **BACKEND (el sostre) + FRONT (no trosseja)** — i el fix previ d'un altre bug és el que el dispara

## FET · EL SOSTRE, I QUE SÓN DUES POLÍTIQUES CONTRADICTÒRIES

La vista és `translate_poms_view`
([translation_views.py:28](backend/fhort/pom/translation_views.py#L28)), ruta
`GET /api/v1/translate/pom/` ([pom/urls.py:127](backend/fhort/pom/urls.py#L127)). **Només GET;
no hi ha POST ni cap paràmetre de paginació.**

```python
if len(ids) > MAX_IDS:
    return Response({'detail': f'Massa POMs en una petició (màxim {MAX_IDS}).'}, status=400)
```
([translation_views.py:34-37](backend/fhort/pom/translation_views.py#L34-L37))

**`MAX_IDS = 300`** ([translation_service.py:52](backend/fhort/pom/translation_service.py#L52)),
amb aquest motiu escrit a sobre ([:50-51](backend/fhort/pom/translation_service.py#L50-L51)):

> *«L'univers real són 142 POMs; el sostre hi és perquè un client equivocat no pugui demanar una
> pàgina sencera de catàleg com si fos una sola pantalla.»*

⚠️ **El supòsit ha caducat**: `/poms` **és** la pàgina sencera del catàleg, legítimament, i el
catàleg ha passat de 300.

⚠️ **I hi ha DUES polítiques per al mateix límit.** El servei **ja trosseja sol**:
`for x in list(pom_ids)[:MAX_IDS]` ([translation_service.py:149](backend/fhort/pom/translation_service.py#L149)).
O sigui: **la vista rebutja el que el servei estava preparat per absorbir.** Cap de les dues és
bona per al cas real —rebutjar mata la ⓘ, truncar la mataria en silenci per als 100 darrers—
però **conviuen sense que ningú ho hagi decidit**.

*(El `MIDA_LOT = 50` de [:56](backend/fhort/pom/translation_service.py#L56) és un altre eix: els
50 textos per crida que admet el proveïdor. No té res a veure amb el sostre de la petició.)*

## FET · QUI CONSTRUEIX LA URL I QUAN ES DISPARA

Cadena, de dalt a baix:

1. **La pantalla** — `/poms` és [pages/POMs.jsx:10](frontend/src/pages/POMs.jsx#L10) →
   `POMCataleg`.
2. **Carrega el catàleg SENCER** —
   [POMCataleg.jsx:334](frontend/src/components/POMCataleg/POMCataleg.jsx#L334):
   `totesLesPagines(poms.list, { page_size: 200, ordering: 'codi_client' })`, i `totesLesPagines`
   ([:18-28](frontend/src/components/POMCataleg/POMCataleg.jsx#L18-L28)) **segueix la paginació de
   DRF fins al final**.
3. **Passa TOTS els ids a la ⓘ** —
   [POMCataleg.jsx:318](frontend/src/components/POMCataleg/POMCataleg.jsx#L318):
   `useTraduccioPoms(llista.map(p => p.id))`.
4. **La cua NO trosseja** — [traduccioPomCua.js:39-47](frontend/src/utils/traduccioPomCua.js#L39-L47):
   `buida()` agafa **tot** el `Set` acumulat d'un idioma i el passa en **una sola crida**.
5. **La URL** — [endpoints.js:307-309](frontend/src/api/endpoints.js#L307-L309):
   `params: { pom_ids: [...pomIds].join(','), lang }`.

Amb ~400 ids → `len(ids) = 400 > 300` → **400**.
*(La llargada d'URL **no** hi té res a veure: 400 ids × ~5 car. ≈ 2 KB, molt per sota de
qualsevol sostre de capçalera. El 400 és de l'aplicació, no del transport.)*

### 🚨 LA IRONIA: EL FIX D'UN BUG ANTERIOR ÉS EL QUE OBRE AQUEST

El comentari de `totesLesPagines`
([POMCataleg.jsx:14-17](frontend/src/components/POMCataleg/POMCataleg.jsx#L14-L17)) diu:

> *«`page_size: 1000` era un SOSTRE: amb un catàleg més gran, la pantalla n'hauria pintat 1000 i
> el comptador n'hauria dit 1000, sense que res indiqués que en faltaven. **Un número que menteix
> és pitjor que una llista curta.**»*

**Dues decisions correctes per separat que es contradiuen en trobar-se**: la pantalla es va
arreglar per **no mentir mai** (carrega-ho tot), i la ⓘ està capada a 300. El resultat és que
`/poms` demana el catàleg sencer a una porta que no el pot servir.

## FET · EL FRACÀS ÉS SILENCIÓS, I PER DISSENY

[traduccioPomCua.js:48-53](frontend/src/utils/traduccioPomCua.js#L48-L53):

```js
} catch {
  // NO es memoritza res i es desmarquen els ids.
  for (const id of ids) demanats.delete(clau(lang, id))
}
```

I la doctrina de dalt de tot
([traduccioPomFont.js:14-16](frontend/src/utils/traduccioPomFont.js#L14-L16)):
*«**EL SILENCI ÉS UNA RESPOSTA VÀLIDA.** Un POM sense traducció torna `''` i la ⓘ no es pinta.
Cap error, cap toast, cap estat de càrrega.»*

**Conseqüència:** a `/poms` la ⓘ **no surt mai**, no hi ha cap avís, i com que el `catch`
desmarca els ids, **cada remuntatge o canvi de signatura torna a disparar la mateixa petició
condemnada**. No és un bucle infinit —`novetat` queda `false`, o sigui que no es provoca cap
re-render— però **sí una repetició garantida a cada entrada a la pantalla**.

## FET · NO ÉS UNA SOLA PANTALLA

| superfície | línia | quants ids passa |
|---|---|---|
| **`/poms`** (POMCataleg) | [:318](frontend/src/components/POMCataleg/POMCataleg.jsx#L318) | **el catàleg sencer** (totes les pàgines) |
| **POMBrowser** | [POMCatalogue.jsx:53](frontend/src/components/POMBrowser/POMCatalogue.jsx#L53) + [:61](frontend/src/components/POMBrowser/POMCatalogue.jsx#L61) | fins a **`page_size: 1000`** |
| Graduació · Mesures · Catàleg per peça | `GraduacioSuperficie.jsx:170` · `EditableTable.jsx:326` · `TaulaPOMsCataleg.jsx:77` | files visibles (desenes) — **fora de perill** |

**POMBrowser és la segona exposada**, i amb un sostre encara més alt.

*(A staging `fhort` té **144** POMs actius i `los` **0** — per això **el defecte no es reprodueix
aquí**: cal un catàleg de >300. La mesura de ~400 ve de PROD, segons el brief.)*

## RELACIÓ AMB T1

**Capes diferents, i cap causa l'altra.** T1 és el **nom de catàleg** que serveixen els endpoints
de POM; T5 és la **ⓘ**, un overlay de traducció servit per un proxy amb cache pròpia. **Se sumen
a `/poms`**: si el nom canònic falta (T1) i la ⓘ mor sencera (T5), la fila es queda **només amb
el codi** — que és el que es va veure a la formació. **Dos fixos independents.**

## RADI (R13)

| # | Fitxer | Línies | Canvi |
|---|---|---|---|
| 1 | `frontend/src/utils/traduccioPomCua.js` | 39-47 | **Trossejar a `buida()`** (lots de ≤`MAX_IDS`, seqüencials). **És el fix mínim i suficient** |
| 2 | `backend/fhort/pom/translation_views.py` | 34-37 | Decidir UNA política: o pujar/treure el sostre, o rebutjar amb un codi que el client sàpiga trossejar. **Avui contradiu `[:MAX_IDS]` del servei** |
| 3 | `backend/fhort/pom/translation_service.py` | 52, 149 | Alinear el sostre amb la política triada |
| 4 | `frontend/src/utils/traduccioPomCua.js` | 48-53 | ⚠️ El `catch` mut fa que un 400 sigui indistingible d'un tall de xarxa. Almenys distingir 4xx (no reintentar) de 5xx/xarxa |

**El fix mínim és (1) i és de FRONT**: el trossejat fa desaparèixer el 400 sense tocar cap porta
ni cap sostre. (2) i (3) són la neteja de la contradicció.

**Tests:** `frontend/src/utils/traduccioPomCua.test.js` **existeix** i prova cua/lot/memòria —
**cap cas amb més de `MAX_IDS` ids**, que és exactament el forat. Al backend no s'ha trobat cap
test de `translate_poms_view` que exerciti el sostre. 🚩 Un test de trossejat ha de comptar
**quantes crides** fa la cua amb 400 ids, no només el resultat.

---
---

# TANCAMENT · ELS CINC VEREDICTES

| | Troballa | Veredicte | Radi | Migració? |
|---|---|---|---|---|
| **T1** | El wizard no pinta noms de POM | **MIXT** — el desplegable la rep i no la pinta; files i candidats no la reben | 2 fitxers · 4 punts | ❌ |
| **T2** | Els breaks no accepten decimals | **FRONT** — backend i BD ja els accepten; **2 inputs**, no 1 | 2 fitxers · 2 punts | ❌ |
| **T3** | Taxonomia de famílies d'instància | **SUBSTRAT JA CONSTRUÏT** — falten 2 de 4 famílies (dada, no arquitectura) | 1 constant + 3 higienes | ❌ |
| **T4** | `gravar-pom` → 400 no accionable | **EL BACKEND HO SAP TOT I NO EN DIU RES** — el 409 germà ja és el model a seguir | 4 fitxers | ❌ |
| **T5** | `translate/pom` en lot → 400 | **BACKEND (sostre 300) + FRONT (no trosseja)** — 2 pantalles exposades | 2 fitxers (mínim: 1) | ❌ |

**Cap dels cinc demana migració.** Quatre són de codi pur; T3 és una decisió de domini.

## EL QUE VA MÉS ENLLÀ DEL BRIEF

1. 🚨 **`JocsDeRegles.jsx:874` té el mateix defecte de decimals que els breaks** (Δ base dels
   jocs de regles). Mateixa forma, mateix fix.
2. 🚨 **L'ordre canònic de composició d'instància el decideix un atzar alfabètic**
   (`'ESTAT' < 'POSICIO'`), contradiu el seu propi docstring i és load-bearing per a **10
   constraints úniques**. La BD ja en porta la prova (`extended-right`), i **el test que ho hauria
   de veure passa en verd contra un fixture que el servidor no emet mai.** Independent de T3.
3. 🚨 **El refús de `create_model_pom_view` és tautològic per a 103 de 144 POMs**
   ([wizard_views.py:891](backend/fhort/pom/wizard_views.py#L891) no té fallback al global) —
   T4 i T1 tenen **la mateixa arrel**: llegir `nom_client` cru.
4. 🚨 **POMBrowser està exposat al mateix 400 que `/poms`**, amb `page_size: 1000`.
5. 🚨 **`translate_poms_view` rebutja el que el seu propi servei ja estava preparat per absorbir**
   (`[:MAX_IDS]`): dues polítiques per a un límit, cap decidida.
6. 🔑 **La primera comprovació de T3 no és de codi, és de desplegament:** si el gunicorn de PROD
   és ranci, `subeix` no viatja i la posició **es comporta com un sol grup exclusiu** — que és
   literalment el símptoma. Una lectura de `GET /api/v1/mesures/diccionari/` a PROD ho tanca.

## ESTAT DEL REPOSITORI EN TANCAR

- `dev` = **`cb23382e`** · **cap commit, cap `git add`, cap push** fets per aquesta sessió.
- `dev` va **140 commits** per davant d'`origin/main` i 13 per davant d'`origin/dev`.
- L'únic fitxer creat: aquest. Cap suite executada. `ps` net en començar i en acabar.

---
---
---

# ANNEX · PROPOSTA DE TAULA DE FAMÍLIES (T3)

> 🟡 **AIXÒ ÉS UNA PROPOSTA, NO UNA LECTURA.** Es presenta per a la **decisió d'Agus** i no
> s'ha implementat res. La llei la fixa ell.

## El canvi és a UNA constant

`MeasurementInstance.SUBEIXOS` ([pom/models.py:366-371](backend/fhort/pom/models.py#L366-L371)),
de 2 famílies a 4:

| família proposada | slugs | sufixos | estat avui |
|---|---|---|---|
| `LATERALITAT` | `left` · `right` | `L` · `R` | ✅ **ja existeix** (avui `LATERAL`) |
| `PROFUNDITAT` | `front` · `back` · `cf` · `cb` | `F` · `B` · `CF` · `CB` | ⚠️ **ampliació** — avui `CARA` només té `front`/`back` |
| `VERTICALITAT` | `top` · `bottom` | `T` · `BM` | ❌ **nova** |
| `COSTURES` | `side` · `waistband_seam` | `S` · *(buit)* | ❌ **nova** |

**Combinacions que això obriria** (avui il·legals): `top`+`left` · `top`+`front` ·
`bottom`+`back` · `side`+`top` · `cf`+`left` · `waistband_seam`+`left`…

## Els casos reals de la Montse, dits amb aquest vocabulari

| el que es vol dir | slug compost | sufix proposat | avui |
|---|---|---|---|
| sisa davantera esquerra | `front-left` | `FL` | ✅ **ja legal — i ja n'hi ha 1 fila viva** |
| boca de camal esquerra per baix | `bottom-left` | `BML` | ❌ il·legal |
| centre davant per dalt | `top-cf` | `CFT` | ❌ il·legal |
| costura lateral esquerra | `side-left` | `SL` | ❌ il·legal |
| cintura estirada per darrere | `back-extended` | `B` | ✅ ja legal (eixos diferents) |

## ⚠️ TRES DECISIONS QUE LA PROPOSTA NO POT PRENDRE SOLA

1. **`CF`/`CB` són PROFUNDITAT o són COSTURES?** El brief els posa a profunditat. Si hi van,
   **`cf`+`front` queda il·legal** (mateixa família) — defensable, perquè «centre davant» ja *és*
   davant. Si es llegeixen com a costures de centre, `cf`+`front` seria legal. **És domini.**
2. **L'ORDRE DE LA TUPLA `SUBEIXOS` ÉS L'ORDRE DEL SUFIX** i entra a la clau única
   ([pom/models.py:355-359](backend/fhort/pom/models.py#L355-L359)). Amb quatre famílies cal
   declarar-lo sencer. ⚠️ **I abans cal tancar la troballa (b)**: avui l'ordre *entre eixos* és
   un atzar alfabètic.
3. **QUINA FAMÍLIA GIRA LA COMPLEMENTÀRIA**: avui es desempata per EIX
   ([EditableTable.jsx:632-635](frontend/src/components/EditableTable/EditableTable.jsx#L632-L635)),
   i amb quatre famílies això deixa de tenir resposta.

## ✅ EL RISC DE DADES ÉS BAIX — ⚠️ PERÒ HI HA UNA COMPROVACIÓ OBLIGATÒRIA

Ampliar famílies **només afegeix combinacions legals; no n'invalida cap d'existent**. Les files
vives amb instància simple del cens segueixen sent vàlides. **Cap backfill, cap migració de dades.**

⚠️ **El que SÍ cal mesurar abans: COL·LISIONS DE SUFIX.** La migració `pom/0079` ja va haver de
rebatejar `bottom` de `B` a **`BM`** perquè `B` el volia `back`. Amb famílies noves apareixen
concatenacions noves (`TL`, `BML`, `SL`, `CFT`…) i **cal comprovar que cap xoqui amb un
`codi_client` viu** —recordant que la constraint és **case-insensitive**
(`uniq_pommaster_codi_client_ci`)— **abans** de proposar-les a ningú.
