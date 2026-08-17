# ACTA F1 + Q1-bis — L'ESCRIPTURA PER GARMENT, TANCADA

> **Patró B · implementació.** Substrat: [`DIAGNOSI_F1_ESCRIPTURA_GARMENT.md`](DIAGNOSI_F1_ESCRIPTURA_GARMENT.md)
> (Patró A, 17/08/2026). Branca `dev`, **cap push** (l'Agus pusheja des de VSC).
> Data: 2026-08-17 · Tenant de referència `fhort` · **el model 1379 NO s'ha tocat**.
>
> Abast aprovat (Agus, Patró C): F1 + Q1-bis **al mateix tram**, perquè tancar F1 sol arma
> el lector de la regla de la mare. Inclou censar i tancar la **5a boca** (`views.py:2042`).
> Fora d'abast, deute anotat: la família pròpia d'`EditableTable` (v. § DEUTE).

---

## 0 · EL VERMELL, REPRODUÏT DE DEBÒ

La diagnosi va **inferir** el 500 (query + dades) sense escriure-hi. Aquest tram l'ha
**mesurat**. Contra el codi pre-fix, el banc nou dona:

```
fhort.models_app.models.BaseMeasurement.MultipleObjectsReturned:
    get() returned more than one BaseMeasurement -- it returned 2!
```

…i surt **dues vegades**: al punt únic (`_write_base`) i a la vora HTTP
(`escalat_ajustar_talla_view`). **9 de 9 tests vermells** abans, **9 de 9 verds** després.

El vermell es va acreditar revertint `views.py` a HEAD amb el pedaç desat a part i
tornant-lo a aplicar — **mai `git stash`** (llei de sessions concurrents).

| Banc | Abans | Després |
|---|---|---|
| `test_set2_f1_serializer_garment` (5 tests) | 🔴 **3 fallen** (`'' != '02'`) | 🟢 **OK** |
| `test_set2_f1_write_base_garment` (9 tests) | 🔴 **9 error** (`MultipleObjectsReturned`) | 🟢 **OK** |
| `utils/filesDePresa.test.js` (11 tests) | 🔴 1 falla (afirmava la llei vella) | 🟢 **OK** |

---

## 1 · 🚨 UNA INSTRUCCIÓ DEL BRIEF CONTRADITA

> «El lookup ha d'incloure garment **I is_active**: al 1320 la fila 02 INACTIVA també
> col·lapsa; garment sol NO cura el 500.»

**La premissa és certa i la conclusió no.** `is_active` **no pot entrar al lookup**.

La clau única de `BaseMeasurement` és `(model, pom, capa, instancia, garment)` — verificat
contra Postgres:

```
"models_app_basemeasureme_model_id_pom_id_capa_ins_e0a47a83_uniq"
    UNIQUE CONSTRAINT, btree (model_id, pom_id, capa, instancia, garment)
```

**`is_active` no hi és.** Amb `is_active=True` al `get_or_create`, la fila PODADA de la peça
(model 1320, POM 904, `garment='02'`, `is_active=false`) no es trobaria i s'intentaria
**CREAR-NE una segona amb la mateixa clau → `IntegrityError`**. Seria canviar un 500 per un
altre.

El que la diagnosi deia és una altra cosa: **una poda no cura el 500 mentre el lookup és
curt**. Amb la clau sencera, com a màxim hi ha UNA fila (comprovat: **0 claus de 5 columnes
amb més d'una fila** a tot el tenant), o sigui que **l'eix sol el cura**. I reviure la fila
podada en escriure-hi és el comportament correcte: qui n'ajusta la talla la vol viva.

Té banc propi i explicat: `test_una_germana_PODADA_no_fa_petar_ni_es_duplica`.

---

## 2 · ELS WRITE-PATHS TANCATS (11 de la llista + 1 no censat)

| # diagnosi | Write-path | Fitxer | Canvi |
|---|---|---|---|
| **5** | `BaseMeasurementSerializer.Meta.fields` | `models_app/serializers.py` | `'garment'` a `fields` |
| **1** | `_write_base` | `models_app/views.py:3712` | 3r eix al lookup (**no** `is_active`) |
| **4** | `ModelGradingOverride` ×3 + `MeasurementChangeLog` | `models_app/views.py` | eix als 4 punts |
| **9** | Q1-bis · la llei de l'Escalat | `models_app/views.py:3424` | `_regla_de(_load_grading_rules_per_garment(…))` |
| **8** | `Response` literal de l'Escalat | `models_app/views.py` | fora els dos `''` cuits |
| **11** | `Response` literal de la poda | `models_app/views.py` | `'garment': bm.garment` |
| **2** | `escalatAjustarTalla` | `api/endpoints.js` + `PropagatedEditor.jsx:82` | l'eix que ja tenia a la mà |
| **3** | `onDesfaInstancia` (**destructiu**) | `CheckMeasureEditor.jsx` | `eixosDeLaFila(g)`, fora el literal |
| **6** | `onNova` + `handleAddRow` + `germanaCapaRapida` | `CheckMeasureEditor.jsx` · `EditableTable.jsx` | prop `garment` cablat + eix al payload |
| **7** | `onParteix` | `CheckMeasureEditor.jsx` | `garment: row.garment` |
| **10** | `setPomRule` · `setPomRegim` | `CheckMeasureEditor.jsx` · `PropagatedEditor.jsx` | l'eix al payload |
| **— (nou)** | Q1-bis · **5a boca** | `models_app/views.py:2051` | `taula-mesures` reparteix per peça |
| **— (nou)** | Q1-bis · boca del fitting | `fitting/serializers.py` | `_regla_de(…, line.garment)` |
| **— (nou)** | Q1-bis · clau de la regla al front | `CheckMeasureEditor.jsx` · `utils/filesDePresa.js` | `clauRegla` en comptes de `pom_id` |

### Cap migració
Verificat a la diagnosi i re-verificat aquí: les 5 taules (`BaseMeasurement`,
`ModelGradingOverride`, `MeasurementChangeLog`, `ModelGradingRule`, `GradedSpec`) ja tenen la
columna. `makemigrations --check` → **«No changes detected»**.

---

## 3 · LA JUNTA, QUE ERA EL PATRÓ DE TOT EL TRAM

Cap dels defectes era «falta la dada». **La dada hi era i es perdia al lloc de la crida.**

- `PropagatedEditor.jsx:62` carregava `garment: r.garment` al `perLinia`; la crida de 20
  línies més avall n'enviava **dos de tres**.
- `onPodar` porta els tres eixos des de F5+ i el seu comentari diu que van junts **«i per
  això surten d'un sol lloc, no d'un literal escrit aquí»** — i **70 línies més avall** hi
  havia exactament aquest literal (`onDesfaInstancia`). Desfer una partició des del
  contenidor de la 02 **podava la fila de la MARE**: destructiu i mut.
- `EditableTable` ja tenia el prop `garment` i `MeasuresEntryPanel:511` l'hi passava;
  `CheckMeasureEditor` **no**. El contenidor sabia la peça i la porta de creació rebia el
  default de la mare.

---

## 4 · DUES ACTES CADUCADES, TANCADES

Totes dues deien «el dia que…», i el dia era avui:

1. **`RegleEditCell` (T7-B10)**: «aquest cridador no diu la prenda, i a posta … dirà la
   prenda el dia que el Check editi mesures d'UNA PEÇA». La graella ja viu dins de
   `PecesDelModel` i la fila ja ve repartida amb el seu eix: **no s'inventa res, l'hi diu la
   fila**.
2. **`Response` de l'Escalat (T6a ③)**: «obrir el contracte d'ESCRIPTURA al garment és un
   tram propi; això NO ho és». **Aquest és aquell tram.**

I un comentari **fals** corregit: `fittingGridAdapter.jsx` deia que «`escalat/ajustar-talla`
encara és per `pom_id` sol». Ja no.

---

## 5 · UN EFECTE COL·LATERAL DEL FIX, VIST I ACOTAT

Completar el conjunt únic al serializer **activa el `UniqueTogetherValidator` de DRF**, que
abans no es podia construir (li faltava una columna de cinc). Conseqüències:

- el duplicat real segueix barrat, però el motiu passa de `errors['instancia']` a
  `non_field_errors`. **Cap consumidor del front hi depenia** (els camins de presa fan
  `.catch(() => {})`); comprovat amb `grep`.
- és un validador de **serialitzador**: entra a **tota** escriptura, també a les PARCIALS. El
  camí viu `onIdentitat` (moure una fila de capa) és un `PATCH {capa}` i prou → té **banc de
  regressió propi**: `test_moure_una_fila_de_CAPA_segueix_funcionant_amb_un_PATCH_parcial`.

---

## 6 · GATES

| Gate | Resultat |
|---|---|
| `manage.py check` | 🟢 net (a cada commit backend) |
| `makemigrations --check --dry-run` | 🟢 «No changes detected» |
| `npm run build` | 🟢 net |
| `npx eslint` (5 fitxers tocats) | 🟢 **0 errors** (16 warnings preexistents, línies no tocades) |
| `node --test utils/filesDePresa.test.js` | 🟢 11/11 |
| i18n-gate ca/en/es | 🟢 **cap text d'usuari nou** — res a traduir |
| guardia-ui (tokens, icones outline) | 🟢 **cap CSS ni icona tocada** |
| Backend viu (T8-ter) | 🟢 `systemctl restart` + `ActiveEnterTimestamp` mogut |

### Bancs de regressió
| Correguda | Resultat |
|---|---|
| Consumidors del serializer (4 fitxers) | 🟢 **60 tests OK** |
| Consumidors de la vista de l'Escalat (8 fitxers) | 🟢 **86 tests OK** |
| `fhort.models_app` + `fhort.fitting` (suite sencera) | **866 tests · 2 errors PREEXISTENTS** (v. § VERMELL HERETAT) |

---

## 7 · RADI CONFIRMAT

Les dues claus que col·lapsaven a tot el tenant `fhort` deixen de fer-ho, perquè el lookup
ja distingeix les files que la BD sempre havia distingit:

| model | POM | files | garments | estat |
|---|---|---|---|---|
| **1379** «RUFFLES» (BRW-FW26-0002) | 962 | 2 | `''` + `02` | ✅ resolt per clau de 5 |
| **1320** «Blusa KAYCE» (BRW-FW26-0001) | 904 | 2 | `''` + `02` (la 2a **podada**) | ✅ resolt, i la poda no hi fa res |

**Cap escriptura sobre el 1379 ni el 1320**: el radi es verifica per la clau única de la BD i
pel banc, que reprodueix la seva forma exacta sobre un model de test.

---

## 8 · 🚩 DEUTE OBERT (declarat, fora d'abast per decisió d'Agus)

**`EditableTable` té la seva pròpia FAMÍLIA DE TRES.** `germanesDeLEix` (`:658`),
`capesLliuresDe` (`:410`) i `germanaCapaRapida` (`:473`) filtren `localRows` per
`pom_id` + `capa` **sense mirar `garment`**.

Avui **no és un bug**, i el motiu és el que el fa perillós: són correctes **per una propietat
del CRIDADOR** —`localRows` arriba ja partit per contenidor (`presaDelContenidor`)— i **no per
la seva pròpia condició**. El dia que una taula rebi files de dues peces alhora, els tres
fallen junts i en silenci.

Aquest tram **hi ha passat pel costat** (`germanaCapaRapida` ara llegeix `mare.garment`) i
**no els ha tancat**: tancar-los vol decidir si el predicat ha de dur l'eix o si la partició
pel cridador és la llei, i això és una decisió d'arquitectura, no un pedaç.

Altres límits que queden dits:

- **`fittingSource`** (`measureSources.jsx`) és una font alternativa del mateix component i
  **les seves portes no s'han censat**. `FittingDetail` (`/fittings/:id`) queda fora.
- **Els 4 consumidors restants de `_load_grading_rules`** (`graded_spec_views.py:171`,
  `serializers_size_check.py:97`, i els dos de `pom/views.py`/`wizard_views.py`) **segueixen
  llegint la llei de la mare**. Aquest tram n'ha tancat **3** (Escalat, `taula-mesures`,
  `fitting/serializers`); l'acta de `pom/services.py:774` s'ha de re-censar quan es tanquin
  els altres.
- **`origen` de la germana nova** (`onParteix` hereta, `onNova` força `'TEMPLATE'`): no s'ha
  verificat contra `_procedencia_de_mesura`. Fora d'abast, anotat.
- **PROD no s'ha mirat** (sense SSH). El radi és de staging.

---

## 9 · 🔴 UN VERMELL HERETAT, NO TOCAT (fora d'abast, però la porta està trencada)

La suite `fhort.models_app fhort.fitting` acaba amb **866 tests i 2 errors**, i **cap dels dos
és d'aquest tram**:

```
ERROR: test_parser_excel.ElCamiIAContinuaSentElFallbackTest
       .test_una_fitxa_bona_si_que_la_serveix_i_amb_header
ERROR: test_parser_excel.ElCamiIAContinuaSentElFallbackTest
       .test_la_resposta_porta_linforme_de_fulls_i_respecta_la_tria

TypeError: <locals>.<lambda>() takes 2 positional arguments but 3 were given
```

**Diagnòstic i prova:**

- El `side_effect` del test és `lambda files, customer:` (**2** paràmetres), i producció crida
  `_match_rows(raw_poms, import_customer, session.model)` (**3**).
- El 3r argument el va introduir el commit **`b7251589` · «SET-2/T8-ter F4 · El detector amb
  la peça a la clau»** — i **no va actualitzar aquest mock**.
- Aquest tram **no toca** `extraction_views.py` ni `test_parser_excel.py` (`git diff
  --name-only` ho confirma), i un `TypeError` d'aritat dins del lambda d'un test no el pot
  causar un canvi en un altre fitxer.

**No s'ha tocat** (llei de mètode: scope creep vist fora d'abast s'anota, no es toca). Però
queda dit, perquè és **el mateix patró que aquest sprint persegueix, a la família del costat**:
un canvi de contracte que passa `manage.py check` verd i deixa un mock caducat. **La suite de
`models_app` NO és verda avui, i no per F1.**

---

## RESULTAT FINAL

**F1 i Q1-bis tancats al mateix tram**, amb l'eix `garment` present a les 14 portes
d'escriptura i de llei censades. **Cap migració.** El 500 del POM 962 (1379) i del POM 904
(1320) queda resolt per la clau sencera, reproduït en vermell i verificat en verd.

Queda **obert i declarat**: la família pròpia d'`EditableTable` (§8), les 4 boques restants de
`_load_grading_rules`, `fittingSource`, i el vermell heretat de `test_parser_excel` (§9).
