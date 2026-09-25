# ORDRE · BLOC A — ALBARÀ = MODEL + RONDES (safata · pantalla · document) + COLUMNES D'ENCÀRRECS

**Patró B · IMPLEMENTACIÓ A STAGING.** Protocol PROTOCOL_IMPLEMENTACIO.
**Base:** `f2c3e9bd` · **branca:** `dev` · **11 commits locals, CAP PUSH.**
**Migracions:** **2**, les dues aprovades per Agus (A7 i A3). Cap tercera.
**Zones intocables:** `assessment/`, `trading/`, `webs/`, nginx — **cap tocada**.
**Precedents llegits:** `DIAGNOSI_ALBARA_COMANDA_DOMINI.md` · `ORDRE_LOT_0909.md`.

---

## PAS 0 · VERIFICACIÓ

### 0a · Porta d'entrada — **PASSA**
```
git pull → Already up to date
HEAD     → f2c3e9bd                                    ✅ el que el brief demana
md5sum ops/maquetes/maqueta_albara_v1.html
         → afd07de7734c670115767760f09ed7fb            ✅ exacte
```

### 0b · ⚑ ENCÀRRECS — **VEREDICTE: POBRESA DE DADES, NO BUG DE CODI**

A staging només hi havia col·lectors i **un** model d'encàrrec (QA-M4-0001, amb `collection`
buida): la llista semblava trencada i no ho estava.

S'ha creat el banc **per la porta real de l'API**, no per shell:
```
POST commerce/order-lines/12/assign-model/  {"model_id": 1361}   → 201
  WO-2026-0013 · model BANC-10 «[BANC] BEYONCÉ Top» · BANC DE PARITAT · client Brownie
```
I la llista pinta nom i col·lecció **a la primera**:
```
WO-2026-0013  codi=BANC-10       nom=[BANC] BEYONCÉ Top      col='BANC DE PARITAT'
WO-2026-0007  codi=QA-M4-0001    nom=[QA-M4] Amb comanda…    col=''
```
> **El codi ja era correcte des del lot anterior** (`model_nom`/`model_collection` al
> serializer). El que faltava era una dada: **30 dels models de `fhort` tenen nom i col·lecció**
> i cap estava assignat a una línia de comanda.

**El banc del bloc A** (model 1361 · WO-2026-0013 ← SO-2026-0002 línia 12 · **numeral 2**):

| volta | dins/fora | entregada | vist-i-plau | tasques |
|---|---|---|---|---|
| R1 | dins | ✅ 10/08 | ✅ 14/08 | 3/3 fetes |
| R2 | dins | ✅ 24/08 | — | 3/3 fetes |
| R3 | **FORA** | ✅ 06/09 | — | 2/3 (una «No realitzada») |
| R4 | fora | **EN CURS** | — | 0/1 |

Els quatre casos que el bloc A necessita, i el R4 és el que prova que una volta en curs es veu
però no es pot marcar.

### 0c · Estat real transcrit

| peça | on és | com estava |
|---|---|---|
| `get_billable_items` | `commerce/services.py:734` | partia de **`ModelTask` Done** + ajustos + despeses; un ítem = una tasca |
| consumidors | `views.py:693` (`billable/`) → `DeliveryNoteDetail.jsx:237` · `test_m4_safata_rondes` | **un sol consumidor de producció** → cap aturada |
| `DeliveryNote` | `commerce/models.py:689` | DRAFT / ISSUED / INVOICED · `delete()` refusa si no és DRAFT |
| `DeliveryNoteLine` | `:748` | FK a `model_task`/`expense`/`adjustment`/`model` · `_assert_editable()` DRAFT-only |
| **comentaris** | `models_base.py:58` | 🔑 **`AbstractDocument.notes` JA EXISTIA** → **cap tercera migració** |
| emetre/eliminar/comentar | `views.py:745` `issue` · `:804` `destroy` · PATCH de línia | el `destroy` de LÍNIA no estava cobert (v. §COMMIT 5) |
| PDF | `pdf_service.py:493` | Python/reportlab, **no template**: franja de color + graella de 6 columnes |
| `TenantConfig.hourly_rate` | `accounts/models.py:46` | **NULL a staging** |
| `Ronda.fora_de_comanda` / `linia_comanda` / `numeral_vigent` | `tasks/models.py:204-216` | foto de l'obertura, **mai recalculada** |
| `data_ok` / data de lliurament | `Entrega.data_ok` / `Entrega.data` | `tasks/models.py:260-275` |
| `SalesOrderLine.rounds_included` / `qty_allocated` | `commerce/models.py:395` / `:374` | numeral de voltes · cartera imputada |

---

## ELS 9 COMMITS

| # | sha | concern |
|---|---|---|
| 1 | `c60b6ff1` | FE · les sis columnes definitives de la llista d'encàrrecs |
| 2 | `d4ddfd33` | BE · **MIGRACIÓ 1** · `DeliveryNoteLine` ↔ `Ronda` + `encarrec_directe` + `linia_comanda` |
| 3 | `fae50dae` | BE · **MIGRACIÓ 2** · `ModelTask.hourly_rate_override` (A3) |
| 4 | `a260b1bd` | BE · la safata és de models i rondes (A1 · A4 · A7) |
| 5 | `a94f6037` | BE · línies per model · preu editable · congelat en emetre |
| 6 | `861f62e4` | FE · safata (maqueta §1) |
| 7 | `0694d566` | FE · pantalla d'albarà (maqueta §2) |
| 8 | `a4a14767` | BE · document PDF (maqueta §3) |
| 9 | `36ef7b30` | QA · bidireccional contra la maqueta + els dos defectes que ha mesurat |
| 10 | `8ff5fa9f` | **fix · el que els guardians han trobat** (A3 inert · fuita d'FK · N+1) |
| 11 | `4d6f56cc` | QA · el banc de mesura apunta a l'esborrany viu |

```
17 fitxers · +1322 / −554
```

---

## LES MIGRACIONS — llegides abans, auditades després

### MIGRACIÓ 1 · `commerce/0023_bloc_a_linia_model_rondes`

**Llegida abans d'aplicar:** tres `AddField`, cap `NOT NULL` sense defecte, cap `RunPython`.

🔑 **PER QUÈ M2M I NO UNA FK.** L'A7 demana dues formes alhora: «1 línia = N rondes del mateix
pacte» i «1 línia = 1 ronda fora de pacte». Una FK `ronda` a la línia només serveix la segona;
una FK `linia` a la `Ronda` serviria les dues però posaria una dada de **document** dins del
domini de tasques — i una ronda ha de poder existir sense saber res de cap albarà.

I feia falta **ara**: la traça ronda↔albarà anava per `model_task.ronda`, i això bastava mentre
la línia era una TASCA. Amb la línia = MODEL, aquell camí es trenca — una línia que cobreix tres
voltes no té UNA tasca de la qual deduir-les.

**Auditada a psql** (no per l'OK de Django):
```
fhort → encarrec_directe boolean NOT NULL
        linia_comanda_id bigint → FK commerce_salesorderline (DEFERRABLE INITIALLY DEFERRED)
        taula commerce_deliverynoteline_rondes amb UNIQUE(deliverynoteline_id, ronda_id)
los   → els dos camps presents
Tenants declarats: public · fhort · los (3). La migració n'ha tocat 3 → cap schema enrere.
Les 4 línies llegades amb model NULL: INTACTES (0 directes, 0 amb línia de comanda).
```

### MIGRACIÓ 2 · `tasks/0054_bloc_a_cost_hora_per_tasca`

**Llegida abans d'aplicar:** un sol `AddField`, nul·lable, cap operació de dades.

🔑 **`null` NO vol dir 0**: vol dir «aquesta tasca no en té de pròpia, fes servir la del tenant».
Un `0` explícit SÍ que és una decisió («aquesta hora no la cobrem») i s'ha de poder desar — per
això el resolutor comprova `is not None` i no la veritat del valor.

🔒 **Viu a la TASCA, no a la línia**: una tasca pot entrar a més d'un document al llarg de la
seva vida i el cost intern d'aquella hora és el mateix a tot arreu. A la línia hi viu el preu de
VENDA, que sí que és del document.

**Auditada a psql:** `hourly_rate_override numeric(10,2)` nul·lable a `fhort` **i** a `los`.

> **Les dues migracions s'han aplicat amb `migrate_schemas` (mai `--schema`) i el servei s'ha
> reiniciat TOT SEGUIT**: la llei de la casa diu que migrar sense desplegar deixa el gunicorn viu
> amb un esquema que no coneix, i `encarrec_directe` és `NOT NULL`.

---

## CURLS (staging · schema `fhort` · client Brownie)

### La safata (commit 4)
```
GET delivery-notes/billable/?customer=7
MODEL BANC-10 · [BANC] BEYONCÉ Top · BANC DE PARITAT · FW2026
  PACTE: SO-2026-0002 · «Disseny patró» · 120,00 · numeral 2 · consumit 0
  BLOC pacte        → R1 (10/08, vist-i-plau 14/08) · R2 (24/08, sense OK)
  BLOC directe-136  → R3 fora, 06/09          ← targeta pròpia (A7)
  BLOC directe-137  → R4 fora, EN CURS        ← surt, i no es pot marcar
Models sense cap volta entregada: FORA de la safata (de 4 grups a 1).
```

### 🔑 L'HÍBRID A4, mesurat movent el numeral — no llegit
```
numeral 2 → R3 al bloc `directe-136`   fora_EFECTIU=True
numeral 3 → R3 al bloc `pacte`         fora_EFECTIU=False · fora_CONGELAT=True
            i la BD segueix dient (3, True)  ← la safata NO escriu
numeral 2 → torna al bloc directe. Estat restaurat.
```

### Línies, preu i estats (commit 5)
```
add-lines {pacte + directe-136} → added=2
  línia 27 «Disseny patró» 120,00 · product FITSES · linia_comanda=12 · directe=false
  línia 29 «[BANC] BEYONCÉ Top» 0,00 · directe=true   ← el concepte NO s'hereta del pacte
rondes_detall:
  R1 205 min → 179,92 €   (Definició POM a 65 €/h per OVERRIDE · la resta a 42 del tenant)
  R2 205 min → 143,50 €
  R3 amb «Mesurar prenda» feta=false               ← el badge «No realitzada»
PATCH unit_price 0,00 → 250,00 · line_total 250,00
DELETE de línia en esborrany → 204
volta EN CURS (directe-137) → added=0 · volta ja albaranada → added=0
EMETRE amb el numeral pujat a 5: BD R3.fora_de_comanda True → FALSE. Congelat.
en EMÈS: DELETE línia 409 · PATCH línia 400 · DELETE albarà 409
notes: desades i llegides (camp ja existent)
```

### El document (commit 8) — extracció de text del PDF real, HTTP 200 als tres idiomes
```
ca  «Pressupost SO-2026-0002 · Disseny patró · R×5 · Qtt 1/2»
    «Ronda 1 10/08/2026 · Ronda 2 24/08/2026»
    «Encàrrec directe sense pressupost»
    «Ronda 3 06/09/2026 · Definició POM · Fitxa tècnica»
    «Comentaris» + el text sencer
en  «Quote … · Qty 1/2» · «Round 1 …» · «Direct order, no quote» · «Comments»
es  «Presupuesto … · Ctd 1/2» · «Vuelta 1 …» · «Encargo directo sin presupuesto»

🔒 A3 VERIFICAT AL DOCUMENT: cap «Cost/h», cap «Cost ronda», cap de les tarifes (42, 65).
```

---

## 🚨 EL QUE LA MESURA HA TROBAT I NO ES VEIA AL CODI

**Un 500 que era un refús.** `DELETE` d'una línia d'un albarà emès contestava **500 amb una
pàgina HTML**. El guard hi era (`_assert_editable`) però llançava `ValidationError` de Django
sense que ningú la recollís, i DRF no la mapeja. Un refús correcte disfressat de crash: la UI no
en pot treure cap missatge i qui ho vegi als logs buscarà un error que no existeix. Ara **409**
amb el motiu.

**La mida no es declarava al contenidor.** La targeta de model, el bloc de totals, la caixa de
comentaris i el contenidor de la safata no deien `fontSize`, i per tant computaven els **16px del
document** en comptes dels 12 de la casa. És la trampa que la mesura ja va caçar a `TaulaLlista`
i al `stateBox`: **el que falla és el que NO hi ha escrit**, i només la bidireccional el veu.

---

## LA PORTA DEL VERD

| control | resultat |
|---|---|
| `manage.py check` | **net** — 0 issues |
| `npm run build` | **verd** |
| `eslint` sobre els 3 fitxers FE del bloc | **net** — 0 errors, 0 warnings |
| migracions | **2**, les dues aprovades · cap tercera |
| zones intocables | **cap tocada** |
| **bidireccional + auditoria de computats** | **31 casos · 9 desviacions**, totes amb nom (re-mesurat després dels fixos) |

### La mesura, contra `maqueta_albara_v1.html` amb **md5 verificat**

Si el md5 no casés, **no es mesuraria**: una maqueta que no és la que el brief nomena mesura una
altra cosa i el número que en surt no val per a res.

**Cap desviació és un defecte viu de pantalla.** Cadascuna té nom:

| n | què | veredicte |
|---:|---|---|
| 6 | `--border` (crema DEPRECAT) i `--pdf-accent` (grana) al `PdfButton`, a les 3 superfícies | **TOKENS, no literals**, i ja hi eren a `f2c3e9bd`. Component compartit amb Quote, Order i el kit → **deute anterior, fora d'abast** |
| 1 | `td.c-col{font-size:11px}` de la llista canònica | 11px **no és a l'escala** (10/12/14/18/22/32). Ja anotat al lot anterior — **decisió d'Agus** |
| 1 | el badge de `maqueta_albara_v1` va a pes 400 i el de `NORMA_LLISTA_canonica` a 600 | **les dues maquetes es contradiuen**. El `Badge` de la casa segueix el segon; no es canvia un component compartit per una d'elles |
| 1 | casella de la safata: `accentColor` auto vs `--gold` | la maqueta en dibuixa una de **FALSA** (`<span class="cb">`). La §8e mana l'accent daurat i la pantalla ho fa: **la pantalla és la correcta** |

**Tres defectes DEL PROPI ARNÈS**, vistos abans de donar cap número: una vora de 0px no pinta res
i comparar-ne estil i color donava soroll a cada element sense vora (maqueta pelada vs reset de
l'app) · el cas «bloc de totals» comparava l'última fila amb la primera · el cas «capçalera
ORDENANT» va quedar orfe quan la llista va perdre la columna de número.

---

## GUARDIANS — i el que han tombat

### 🟡 guàrdia-i18n · VERD als 7 punts menys un
Paritat de les 21 claus noves als tres fitxers (diff de conjunt buit als quatre sentits) · cap
literal de cara a l'usuari · les 5 claus del PDF als tres blocs · cap dada convertida en clau ·
cap `_plural`. **Vermell només a les claus mortes**: el bloc en deixava 29 en retirar la graella
de línies. Totes retirades (verificant abans, una a una, que cap tenia lector —tampoc dinàmic:
l'únic `t(\`…${x}\`)` viu és `status_*`). Paritat global final: **4.925 claus idèntiques**.

I una troballa que no era d'i18n però que va sortir llegint el generador: **`notes` s'imprimia
DUES vegades al PDF** —el bloc «Comentaris» nou i el bloc «Observacions» vell—, i no es veia al
diff perquè cadascun és correcte per separat: el que falla és que ara hi ha dos lectors del
mateix camp. També hi havia tres còpies obsoletes (`tray_hint` deia «Tasques acabades, extres,
despeses…» quan la safata ja és de models i voltes — i a més era **text d'ajuda, que el brief
prohibeix**: se n'ha anat i el seu lloc el pren el nom del client, que és el que la maqueta hi posa).

### 🔴 revisor-diff · dues 🔴 de seguretat i una d'inèrcia

**1 · L'A3 SENCER ERA INERT.** `hourly_rate_override` no era a `ModelTaskSerializer.Meta.fields`
i DRF descarta els camps desconeguts **en silenci**: el comercial escrivia 45 al cost/h, rebia
**200 OK**, la pantalla recarregava i el valor tornava a ser el de sempre. Cap error, cap log. La
migració 2 i `cost_hora_efectiu` no els exercitava ningú.
**Reproduït** (PATCH 200 · BD `None`) i corregit amb una porta pròpia amb gate COMERCIAL —el CRUD
va amb `DEFINE_TASKS` i tocar el cost intern no és de qui planifica— i lectura **podada**.
Mesurat: POST 200 · BD 99,00 · la Marta (sense COMERCIAL) **403** · lectura admin 77,00 / Marta null.

**2 · FUITA D'FK EN UN SOL PATCH.** `linia_comanda` i `encarrec_directe` eren escrivibles i sense
validació de client, **contra el que deia el comentari del seu propi serializer**. Un
`PATCH {"linia_comanda": <línia d'un ALTRE client>}` contestava 200 i, a partir d'aquí, el
document imprimia «Pressupost OF-…» d'aquell tercer i `pacte_consum` n'ensenyava la cartera.
Passen a `read_only_fields`. Mesurat: la BD segueix dient 12.

**3 · N+1 EN CASCADA A UNA PANTALLA DE TÈCNIC.** `rondes_detall` agregava timers **per tasca**;
una nota de 8 línies × 2 voltes × 6 tasques passava de 100 consultes — i el serializer es
serveix també `?model=` a la pestanya Producció, que obre qualsevol tècnic i on `rondes_detall`
no el pinta ningú. Ara els minuts van en UNA query per línia i els dos ViewSets porten el
prefetch de voltes → tasques → tipus/tècnic.

**🚩 I UNA COSA QUE JO HAVIA DIT MALAMENT.** El commit `a260b1bd` afirmava que l'híbrid A4
«conserva el veredicte congelat» de les voltes ja emeses. **Era codi mort**: `voltes` ja exclou
tot el que té línia d'albarà i «ja emesa» n'és un subconjunt, o sigui que els dos conjunts són
DISJUNTS per construcció i la comparació no s'avaluava mai certa. La meitat congelada de
l'híbrid la fa `issue_delivery_note`, i **només** ell. La branca se'n va.
**I el test que la cobria mentia al nom**: es deia «conserva el veredicte congelat» i el que
assertava —correctament— és que la volta ja no hi és. Renombrat: un test que promet més del que
mira fa creure que hi ha cobertura on no n'hi ha.

**Altres, totes mesurades i corregides:** `add_lines_to_draft` no era idempotent DINS d'una
crida (dos blocs iguals al mateix cos creaven dues línies sobre les mateixes voltes; ara
added=1) · `position` naixia amb `count()` i empatava amb l'última línia · «Afegir comentari»
creava una línia MANUAL amb text de plantilla que, retirada la graella, ja no es podia editar ni
amagar i sortia al PDF (el botó se'n va; el comentari viu a `notes`) · el PDF pintava les línies
sense model amb el text duplicat · `_pot_veure_diner` ignorava l'escapatòria
`context={'diner': True}` · un `map` niat a la safata tornava arrays sense clau.

**El revisor confirma:** cap tercera migració (`makemigrations --check` → *No changes*) · cap
cost intern al PDF (llei A3) · guards d'estat correctes · cap consumidor vell orfe.

### 🚩 EL QUE NO HE TOCAT I VOL DECISIÓ D'AGUS

1. **Extres, deduccions i despeses ja no són albaranables des de la safata.** La reescriptura
   n'ha eliminat els blocs; segueixen vius només per `generate/` des de la fitxa d'encàrrec. Un
   `EXTRA_BILL` revisat no apareix a `/comercial/albarans/<id>` → **es factura de menys, en
   silenci**. El brief deia «Cap tasca» i no deia res dels extres: no invento el disseny.
2. **Emetre pot contradir el bloc amb què es va facturar.** Si algú puja `rounds_included` abans
   d'emetre, una volta afegida com a `directe-<id>` (preu lliure) queda amb
   `fora_de_comanda=False` sobre una línia amb `encarrec_directe=True`, i el `consumit` del pacte
   la compta com a gastada del numeral.
3. **Un usuari amb CONFIGURE sense COMERCIAL** veu els inputs de preu **buits** i editables: si
   hi escriu, sobreescriu un preu que no pot llegir.

---

## 🚩 DIVERGÈNCIA DECLARADA amb la lletra del brief

El brief diu que la safata mostri «rondes ENTREGADES **no cobertes per cap línia d'albarà EMÈS**».
S'ha implementat com **no cobertes per cap línia, DRAFT inclòs**.

**Per què:** si una volta ja posada a un esborrany seguís sortint a la safata, es podria afegir
**dos cops al mateix esborrany** — el guard d'`add_lines_to_draft` és per ORIGEN, no per volta.
La llei anti-doble-comptatge que ja hi havia es manté, i esborrar l'esborrany les retorna soles
(CASCADE de línies). L'«EMÈS» del brief governa una **altra** pregunta —el congelat de l'A4— i
allà s'aplica al peu de la lletra.

---

## 🚩 ANOTAT, NO TOCAT

1. **`test_m4_safata_rondes` queda SUPERAT** i marcat `skip` amb el motiu: provava la safata per
   tasques i no pot passar mai més. No s'esborra —el que provava segueix sent llei i el seu banc
   és la lectura de com era el sistema. Un mòdul vermell per disseny ensenya a ignorar el vermell.
   El contracte viu és a `test_bloc_a_safata_models` (11 tests, escrits i **no executats**).
2. **`PdfButton` arrossega `--border`** (crema deprecat). És compartit amb Quote, Order i el kit
   comercial: conformar-lo és una passada pròpia.
3. **Claus i18n sense lector** que el bloc deixa enrere en retirar la graella de línies: pendents
   d'una neteja (v. §GUARDIANS).
4. **`TenantConfig.hourly_rate` era NULL** a staging; s'hi ha posat 42 €/h per poder mesurar
   l'A3, i un override de 65 €/h a una tasca del banc. Són dades de QA, no configuració decidida.
5. La resta del banc de QA (timers, R5) és fabricada i està declarada aquí.

---
---

# ESMENA · BLOC A — els tres forats que el bloc va deixar oberts

**Patró B · IMPLEMENTACIÓ A STAGING.** Skill `patro-b`.
**Base:** `4d6f56cc` · **branca:** `dev` · **3 commits, CAP PUSH.**
**Migracions:** **CAP.** `makemigrations --check` → *No changes detected* a cada commit.
**Zones intocables:** `assessment/`, `trading/`, `webs/`, nginx — **cap tocada.**
**Fitxers d'una altra sessió:** `DECISIONS.md` (+1215) i `ops/qa/qa_f22_vocabulari_captures.py`
**no s'han afegit a cap commit** (`git commit -- <paths>` explícits als tres).

Els tres commits són, un a un, els tres punts que el bloc A va deixar escrits a
**§EL QUE NO HE TOCAT I VOL DECISIÓ D'AGUS**.

| # | sha | concern | fitxers |
|---|---|---|---|
| 1 | `3a8e7401` | els extres, les despeses i les deduccions tornen a la safata | 6 · +381/−51 |
| 2 | `2195c437` | emetre s'atura davant la contradicció de pacte | 7 · +208/−8 |
| 3 | `2fe707b5` | preu i cost/h només editables amb COMERCIAL | 1 · +30/−4 |

---

## COMMIT 1 · `3a8e7401` — la regressió reparada

### Què passava
La safata del bloc A parteix de VOLTES. Els altres tres albaranables —`EXTRA_BILL` revisat,
`DEDUCTION`, `Expense`— van desaparèixer amb la reescriptura i només quedaven vius per
`generate/` des de la fitxa d'encàrrec. **Es facturaven de menys, en silenci.**

### Com tornen
Com a **llista pròpia del grup-model** (`extres`), no com un bloc de voltes més:

| | bloc de voltes | extra |
|---|---|---|
| unitat | N voltes → 1 línia, 1 import | 1 ítem → 1 línia |
| la casella marca | el bloc sencer | només l'ítem |
| `encarrec_directe` | segons el pacte | **sempre `False`** (un extra no és una volta fora de pacte) |
| voltes lligades | les del bloc | **cap** |

I **un model entra a la safata si té alguna volta entregada O algun extra** — aquesta era
exactament la porta per on desapareixien. Els que no tenen model resoluble (una deducció de
concepte lliure sobre un col·lector) van a un grup `None`, no al descart.

### 🚨 El guard anti-duplicació ara és als DOS camins
`generate/` filtrava els seus ajustos i despeses **només** pel `wo.delivery_note`, i aquesta
marca l'escriu **només ell**: un extra ja facturat des de la safata hi arribava amb el WO «net» i
entrava una segona vegada. Els tres orígens porten ara `delivery_note_lines__isnull=True`.

### 🚨 El que la mesura va caçar i la lectura no
**Els extres naixien sense IVA.** El producte és qui porta el tipus, i jo els l'havia tret
(«un extra no és un article de catàleg»). El senyal va ser que **subtotal i total sortissin
idèntics**: 115,00 i 115,00. La v1 ja adjuntava el producte de la línia de venda als ajustos i
l'article propi a les despeses. Amb això: **115,00 → 139,15**.

També viatja `work_order`, i no és decoració: `unassign_model_from_order_line` mira les línies
d'albarà **per `work_order`** per refusar desassignar un model ja albaranat.

### 🔑 Cap frase congelada a la columna
La v1 escrivia `'Extra'`/`'Deducció'` a `description` quan l'origen no en portava cap, i llavors
un albarà en anglès imprimia «Deducció». La descripció viatja **buida** i el TIPUS el diu qui
renderitza. Mesurat als tres idiomes.

### CURLS (staging · client Brownie · banc BANC-10)
```
GET billable/?customer=7
  MODEL BANC-10 · [BANC] BEYONCÉ Top
    bloc  pacte        preu 120,00 · voltes [4, 5]
    EXTRA ajust-21     EXTRA        85,00 · Retoc de màniga fora de recepta
    EXTRA ajust-22     DEDUCTION   −30,00 · Recepta no executada: escalat
    EXTRA despesa-2    EXPENSE      60,00 · Estampació externa   (3 × 20,00)
  EXTRA_ABSORB (40,00) → correctament ABSENT

POST add-lines {3 extres} → 200 · added=3
  subtotal 115,00 · total 139,15        ← l'IVA hi és
  EXTRA      85,00  adj=21           model=1361 directe=false rondes=0
  DEDUCTION −30,00  adj=22           model=1361 directe=false rondes=0
  EXPENSE    60,00  exp=2            model=1361 directe=false rondes=0

IDEMPOTÈNCIA
  repetir l'ajust en una 2a crida        → added=0
  dues vegades DINS de la mateixa crida  → added=0
  la safata ja no els ofereix            → extres pendents []

generate/ SOBRE EL MATEIX WO (tancant-lo i restaurant-lo)
  9 línies generades · ítems ja albaranats que es tornen a cobrar: 0
```

### El document
```
ca  [BANC] BEYONCÉ Top
    Ronda 5 08/09/2026                    120,00 €
    Retoc de màniga fora de recepta        85,00 €
    Recepta no executada: escalat         −30,00 €
    Estampació externa                     60,00 €
                        Base imposable    235,00 €
en  … Round 5 …   ·   es  … Vuelta 5 …
```
Una sola capçalera de model: els extres **no obren bloc**, van sota les voltes del seu. Amb la
descripció buida, el concepte el diu el tipus: `ca [Extra · Deducció · Despesa]` ·
`en [Extra · Deduction · Expense]` · `es [Extra · Deducción · Gasto]`.

---

## COMMIT 2 · `2195c437` — emetre s'atura davant la contradicció

### El forat
El numeral és editable (FIT-5) i el veredicte d'una volta es resol **en obrir-la**. Entre l'una i
l'altra hi cabia: algú puja `rounds_included` després que el comercial hagi compost la línia, i
el document surt dient «encàrrec directe sense pressupost» d'una volta que **ara hi entra** —
mentre el `consumit` del pacte se la compta com a gastada. Cap senyal: s'emetia i congelava.

### La forma
`contradiccions_de_pacte(delivery_note)` es comprova **abans de congelar i FORA de la
transacció** — congelar és el que fa irreversible el veredicte, i si la comprovació anés a dins
el codi hauria de desfer el que acaba d'escriure per poder-se negar.

**409, no 400, i excepció pròpia.** Els altres guards d'emissió diuen «això encara no es pot
fer»; aquest diu «això que tens davant ja no és cert» — un conflicte amb un estat que ha canviat
sota els peus (el mateix codi dels dos `destroy`) — i demana un gest diferent. Porta la **llista**
(`contradiccions`), no un text: la frase es compon a la cara, on hi ha l'idioma.

### 🔒 Mai auto-convertir
Dues sortides i **cap emet**: «Anar a la comanda» (on viu la causa) o «Tancar i convertir a mà».
El preu d'una volta directa és LLIURE; triar-li'n un de nou sense preguntar seria decidir per qui
ha compost el document. Sense candidat de comanda el botó s'apaga (una contradicció pot venir
d'una línia directa, que per definició no té línia de comanda).

### 🚨 Un fals positiu, tancat abans de committejar
La primera versió acusava tota línia directa d'un model **sense cap comanda**: `numeral_efectiu`
torna `(None, None)`, el veredicte sortia «dins» i la línia quedava acusada de contradir un pacte
que no existeix — quan justament diu la veritat. Els dos `None` volen dir coses diferents:

| `numeral_efectiu` | vol dir | una línia DIRECTA |
|---|---|---|
| `(None, None)` | el model no té cap comanda | **diu la veritat** → no es mira |
| `(linia, None)` | pacte sense límit de voltes | contradiu (cap volta en pot sortir) |
| `(linia, n)` | pacte amb numeral | contradiu si la volta hi cap |

Mesurat als dos costats desassignant el WO del banc i tornant-l'hi:
```
AMB pacte viu   → numeral_efectiu (SalesOrderLine 12, 5) → contradiccions [(5, 'dins', 5)]
SENSE pacte viu → numeral_efectiu (None, None)           → contradiccions []
```
I un pacte sense numeral ja no pinta «numeral null»: la cara hi posa «sense límit».

### CURLS
```
numeral 4 · add-lines directe-138 → línia 53 (encàrrec directe, preu lliure)
algú puja rounds_included a 5     → 200
EMETRE                            → 409
  «El numeral de la comanda ha canviat: aquest albarà diria del pacte una cosa que ja no és certa.»
  · línia 53 · [BANC] BEYONCÉ Top (BANC-10) · ronda 5 · numeral vigent 5 · ara DINS
  l'albarà segueix en DRAFT — no s'ha congelat res
corregir el numeral a 4           → EMETRE 200 · ISSUED

SIMÈTRIC · línia de PACTE, numeral baixa a 3
EMETRE → 409 · línia 50 · ronda 5 · numeral vigent 3 · ara FORA
```

### El modal
```
El pacte ha canviat
La ronda 4 de [BANC] BEYONCÉ Top ara és FORA del pacte (numeral 3), i aquesta línia
la factura sota el pressupost.
[ Anar a la comanda ]  [ Tancar i convertir a mà ]
```
`pacte_oferta_id` s'afegeix al serializer perquè el botó porti a la comanda de debò: el
`document_number` és per llegir-lo i la ruta va per pk. Mesurat: línia 54 →
`pacte_oferta=SO-2026-0002`, `pacte_oferta_id=10` → `/comercial/comandes/10`.

---

## COMMIT 3 · `2fe707b5` — el diner només s'edita amb COMERCIAL

### 📏 El que la mesura diu ABANS de tocar res
El punt 3 del bloc A deia: «un usuari amb CONFIGURE sense COMERCIAL veu els inputs de preu buits
i editables». **Mesurat amb la Montse** (manager, `configure=True comercial=False`, el cas real
d'staging), la porta ja el refusa per TRES bandes:

| | Montse | admin |
|---|---|---|
| `PATCH delivery-note-lines/54 {unit_price}` | **403** | 200 |
| `POST model-task-items/723/cost-hora/` | **403** | 200 |
| `GET delivery-notes/16/` (la pantalla) | **403** | 200 |
| `GET delivery-note-lines/54/` | 200, **sense** `unit_price` ni `internal_rate` | 200, `120.00` / `42.00` |
| `/comercial/albarans/16` al navegador | la ruta porta `cap="comercial"` → **0 senyals, 0 inputs, cap crida a l'API** | pantalla sencera |

> **Aquest commit NO corregeix cap defecte viu**, i s'ha de llegir així. La condició de la cara
> era incorrecta però inabastable: hi entra com a defensa en fondària, perquè una condició
> d'edició que no mira qui pot veure el diner és una trampa armada esperant la pantalla que un
> dia la renderitzi des d'una altra ruta.

### 🚨 El que SÍ que mentia
`Number(l.unit_price ?? 0).toFixed(2)` pintava **0,00 €** amb la mateixa cara que un import real
allà on el backend deia «això no et viatja». Un buit es nota; un zero es creu. Ara `—` quan el
camp no hi és, i `--text-main` **declarat** en comptes d'heretat.

Mateixa llei al total de cost d'una volta (`Number(x.cost || 0)` convertia una suma DESCONEGUDA
en un import creïble): si algun cost no ha viatjat, el total calla. La cel·la de cost/h ja era
honesta i no s'ha tocat.

**Lectura normal verificada:** albarà EMÈS com a admin → 0 inputs, imports reals
(30,00 · 0,00 · 120,00 · 250,00), color `rgb(29,29,27)` = `--text-main`. Esborrany → l'input hi
segueix sent.

---

## LA PORTA DEL VERD

| control | C1 `3a8e7401` | C2 `2195c437` | C3 `2fe707b5` |
|---|---|---|---|
| `manage.py check` | net | net | net |
| `makemigrations --check` | *No changes* | *No changes* | *No changes* |
| `npm run build` | verd | verd | verd |
| `eslint` del fitxer FE | net | net | net |
| **suite `fhort.commerce`** | **Ran 66 · OK (skipped=9)** | **Ran 66 · OK (skipped=9)** | **Ran 66 · OK (skipped=9)** |
| **guàrdia-ui bidireccional** | 31 casos · 9 desviacions | 31 · 9 | 31 · 9 |
| **guàrdia-i18n** | paritat 4928 · 0 literals | 4933 · 0 literals | 4934 · cap clau nova |
| zones intocables | cap tocada | cap tocada | cap tocada |

**Les 9 desviacions són EXACTAMENT el deute que el brief exclou** i no n'hi ha cap de nova:
6 tokens del `PdfButton` (`--border` crema × 3 superfícies · `--pdf-accent` grana × 3) ·
`11px` de la llista canònica · el pes del badge (400 a `maqueta_albara_v1` vs 600 a
`NORMA_LLISTA_canonica`) · l'`accentColor` de la casella (la maqueta en dibuixa una de falsa).

**El modal d'emissió no és a l'arnès bidireccional** i s'ha mesurat a part amb el MATEIX JS i les
mateixes taules (`qa_auditoria_computats.JS`, `VORES_OK`, `CROM`): **14 elements, 0 per sobre del
sostre, cap color fora de paleta propi** — els 2 que hi surten són el deute del `PdfButton` de la
pàgina de sota. No s'ha tocat l'arnès perquè cobrir-hi aquest modal exigiria una **segona
excepció d'escriptura** (cal moure el numeral per provocar el 409) a un fitxer que es declara
read-only i que només en té una, declarada.

---

## 🚩 EL BANC: el que hi he fet i com ha quedat

**Dades de QA afegides** (sobre `WO-2026-0013`, model `BANC-10`, client Brownie):
`EXTRA_BILL` 85,00 · `DEDUCTION` 30,00 · `EXTRA_ABSORB` 40,00 (per comprovar que queda fora) ·
`Expense` 3 × 20,00 amb un producte nou `qa-esmena-estampacio` (`EXTERNAL_SERVICE`, IVA 21 %) —
no n'hi havia cap de nature externa al tenant.

**🚨 DOS ENSOPECS MEUS, declarats:**

1. **Vaig esborrar `DN-2026-0006` (id 16) netejant la meva pròpia mesura** — i és l'esborrany que
   `qa_lot0909_bidireccional.py` cabla a `DN_ESBORRANY = 16`. L'arnès hauria quedat apuntant a un
   document inexistent, que és exactament el que el commit `4d6f56cc` ja havia hagut d'arreglar.
   Refet amb el mateix pk i número, com a esborrany del client 7 amb UNA línia de voltes.
2. **Vaig cridar `issue/` com si fos una consulta** («a veure si passaria») i **va emetre**
   l'albarà del banc i congelar `Ronda.fora_de_comanda`. Si es vol saber si emetria, es crida el
   PREDICAT (`contradiccions_de_pacte`), no la porta.

**Estat final verificat**, idèntic al de partida:
```
DN-2026-0006 (16)  DRAFT · 1 línia (volta 4) · total 145,20
línia de comanda 12 · rounds_included 5
R1 fora=False  R2 fora=False  R3 fora=False  R4 fora=True  R5 fora=False
línia 54 unit_price 120,00 · tasca 723 hourly_rate_override 65,00
safata: bloc `pacte` amb la volta 5 + els 3 extres pendents  ← el que els guardians necessiten
```

---

## 🚩 ANOTAT, NO TOCAT

1. **`generate/` segueix sent el camí de la v1 i multiplica el preu per TASCA.** Mesurat en
   exercir el guard anti-duplicació: sobre `WO-2026-0013` genera **9 línies TASK a 120,00 cadascuna
   (1.080 €)** contra una línia de comanda que ven 120 €/u. És el defecte que la diagnosi del 09/09
   va mesurar i que la safata del bloc A substitueix — però la porta vella segueix oberta des de la
   fitxa d'encàrrec. **Fora d'abast d'aquesta esmena; vol decisió d'Agus** (retirar-la, o refer-la
   sobre el mateix eix model+voltes).
2. **`generate/` i la safata poden cobrir la MATEIXA VOLTA dues vegades.** El guard que he afegit
   és per ÍTEM (ajust/despesa) i el de voltes va per la M2M `DeliveryNoteLine.rondes`, que
   `generate/` no omple mai: una volta facturada per la safata no impedeix que `generate/` en
   torni a cobrar les tasques. És la mateixa arrel que el punt 1.
3. **Els deutes de disseny del brief**: 6 tokens del `PdfButton` · les 2 contradiccions entre
   `maqueta_albara_v1` i `NORMA_LLISTA_canonica` · els 11px de la llista. Cap tocat.
4. **`_extres_albaranables` emet dues claus amb prefix `_`** (`_product_id`, `_work_order_id`) que
   viatgen al JSON de la safata. Són internes —`add_lines_to_draft` les llegeix de la safata viva,
   que és l'autoritat— i l'endpoint va amb gate COMERCIAL, o sigui que no exposen res que el
   consumidor no pugui veure. Si molesten, es poden podar a la vista.
5. **Cap test nou.** Els contractes nous (extres a la safata, contradicció de pacte) estan
   mesurats per la porta HTTP i pel document, però **no tenen test escrit**: la suite de
   `fhort.commerce` passa a 66 igual que abans. Si Agus els vol coberts, és una passada pròpia.

---

## QUÈ HA DE FER EL CTO

```
git log --oneline 4d6f56cc..HEAD     # els 3 commits d'aquesta esmena
git show 3a8e7401                    # extres a la safata (+ IVA + anti-duplicació)
git show 2195c437                    # guarda d'emissió (409)
git show 2fe707b5                    # gate COMERCIAL a la cara
git push origin dev                  # el push el fa l'Agus des d'SSH
```
Staging ja serveix aquest codi: `frontend/dist` construït i `ftt-staging` reiniciat.

---
---

# TANCAMENT · BLOC A — retirar `generate/` + contractes escrits (NO executats)

**Patró B · IMPLEMENTACIÓ A STAGING.** Skill `patro-b`.
**Base:** `2fe707b5` · **branca:** `dev` · **2 commits, CAP PUSH.**
**Migracions:** **CAP.** `makemigrations --check` → *No changes detected*.
**Zones intocables:** `assessment/`, `trading/`, `webs/`, nginx — **cap tocada.**
**Fitxers d'una altra sessió:** `DECISIONS.md` i `ops/qa/qa_f22_vocabulari_captures.py`
**no s'han afegit a cap dels dos commits** (`git commit -- <paths>` explícits als dos).
**Cap suite executada en aquest brief** (prohibició explícita del brief).

| # | sha | concern | fitxers |
|---|---|---|---|
| 1 | `63a2f583` | retirar la porta `generate/` de la fitxa d'encàrrec | 10 · +27/−297 |
| 2 | `a78b3800` | 29 tests nous del bloc A · escrits, NO executats | 1 · +531 |

---

## COMMIT 1 · `63a2f583` — la porta `generate/` retirada

### El cens abans de tocar res
`grep` de `generate/`, `deliveryNotes.generate`, `generate_delivery_note` a tot
`backend/` i `frontend/` (`dist-tenants/` exclòs, és build): **UN sol cridador** —el botó
«Generar albarà» de `WorkOrderDetail.jsx` (fitxa d'encàrrec) i el seu modal. Cap altra
pantalla, cap test viu. Per això la porta es retira SENCERA (no 410): no hi havia ningú
extern a qui avisar.

### Què se'n va
- **BE** — l'`@action generate` de `DeliveryNoteViewSet` (`views.py`) i la funció
  `generate_delivery_note` de `services.py` (153 línies: la construcció de línies TASK ·
  EXTRA · DEDUCTION · EXPENSE **per tasca**, que el bloc A ja no fa servir — la línia és el
  MODEL des de `add_lines_to_draft`). Sis docstrings/comentaris que la citaven pel nom,
  actualitzats perquè no descriguin un endpoint que ja no existeix.
- **FE** — el botó, el modal (selecció d'altres WO CLOSED), i l'estat (`dnModal`,
  `otherWos`, `selectedWos`, `genErrors`) i les funcions (`openDnModal`, `toggleWo`,
  `doGenerate`) de `WorkOrderDetail.jsx`. L'entrada `generate` d'`endpoints.js`.
- **i18n** — 9 claus mortes (`dn_generate`, `dn_title`, `dn_help`, `dn_others`,
  `dn_blocked`, `dn_blocked_help`, `dn_confirm`, `dn_cancel`, `dn_error`) retirades a
  ca/en/es. Paritat verificada: **4.925 claus idèntiques als tres**.
- **Es queda**: el botó «Veure albarà» (`dn_view`) — llegeix `wo.delivery_note`, que
  segueix sent una lectura vàlida per als WO albaranats pel camí vell.

### 🚩 EL QUE LA RETIRADA HA DEIXAT AL DESCOBERT
**`WorkOrder.delivery_note` queda LLEGAT.** Mesurat per grep (`\.delivery_note\s*=` a tot
`commerce/`): l'ÚNICA escriptora del camp era `generate_delivery_note`. Retirar-la vol dir
que **cap WO nou tornarà a tenir aquest camp informat**: la safata v2 factura per
MODEL+VOLTES (la M2M `DeliveryNoteLine.rondes`) i mai l'escriu. El botó «Veure albarà»
seguirà servint els WO ja albaranats pel camí vell (banc de QA inclòs), però és un camp que
ja no alimenta ningú més. No s'ha tocat el model (cap migració en aquest brief); s'anota
perquè quedi escrit i no es descobreixi per sorpresa el dia que algú hi confiï.

### Mesurat (staging, `Host: staging.fhorttextile.tech`, JWT tenant `fhort`)
```
POST /api/v1/commerce/delivery-notes/generate/          → 405 (Method Not Allowed)
```
🔑 **No és el 404 literal que el brief anticipava, i és fidel al que hi ha ara.** El
`DeliveryNoteViewSet` no porta `CreateModelMixin`: sense l'`action` de llista, el router
del `DefaultRouter` fa caure `generate` a la ruta de DETALL (`delivery-notes/<pk>/`), que
NO accepta POST — 405, no 404. El resultat és el mateix (la porta és inabastable), i es
declara la diferència de codi en lloc de maquillar-la.
```
GET  /api/v1/commerce/delivery-notes/billable/?customer=7   → 200 (safata intacta)
POST /api/v1/commerce/delivery-notes/draft/                  → 200 (draft intacte)
```

### La porta del verd
| control | resultat |
|---|---|
| `manage.py check` | net |
| `makemigrations --check` | *No changes detected* |
| `npm run build` | verd |
| `eslint` (`WorkOrderDetail.jsx`, `endpoints.js`) | net — 0 errors (1 warning pre-existent, línia 90, `setReview` a un `useEffect`, NO tocada per aquest diff) |
| paritat i18n ca/en/es | 4.925 = 4.925 = 4.925 |
| zones intocables | cap tocada |
| restart | `systemctl restart ftt-staging` fet abans del build (llei de la casa: el gunicorn no migra res aquí, però el codi del disc ha de ser el que serveix) |

---

## COMMIT 2 · `a78b3800` — 29 tests, escrits contra el codi real, NO executats

Els tres contractes de l'ESMENA (extres a la safata, contradicció de pacte, gate COMERCIAL
a la cara) no tenien test: la suite de `fhort.commerce` passava a 66 igual amb els tres
trencats (§ANOTAT de l'ESMENA, punt 5). Un fitxer nou,
`backend/fhort/commerce/test_esmena_bloc_a.py`, contra les signatures reals de
`services.py` / `views.py` / `serializers.py` / `pdf_service.py` i els curls d'aquesta
acta i de l'ESMENA — no contra suposicions.

**29 casos, sis grups** (detall al missatge del commit): `SafataExtresTest` (5) ·
`AddLinesTest` (6) · `HibridRecalculTest` (3) · `EmetreContradiccioTest` (5) ·
`GatesComercialTest` (7) · `PdfBlocsTest` (3).

🔑 **Decisions de lectura, per si el dia d'executar-los alguna no encaixa:**
- El PDF es verifica amb `pdftotext -layout` (poppler-utils, ja al sistema) i no amb cap
  llibreria Python: el venv només porta `reportlab` (que EMET, no llegeix) i `pikepdf`
  (estructura, no text pla). No s'ha afegit cap dependència nova.
- La «gate»: `model d'un altre client → 400» es prova sobre `assign-model`
  (`_assign_model_core`: `model.customer_id != order.customer_id`), no sobre
  `DeliveryNoteLine.linia_comanda` — aquest camp ja és `read_only_fields` des de la FUITA
  D'FK de l'ordre original: un PATCH amb un valor d'un altre client hi arriba **200 i
  s'ignora en silenci** (mesurat allà: «la BD segueix dient 12»), no 400. Són dues
  proteccions diferents contra el mateix risc («un altre client») i la que respon amb 400
  de debò és la d'`assign-model`.
- Les rondes del banc porten una `ModelTask` `Done` (`origen='prevista'`) perquè el PDF
  d'una volta directa pugui dir «Definició POM» sota la volta (§B4c, tasques fetes).

### La porta del verd d'aquest commit
| control | resultat |
|---|---|
| `python -m py_compile backend/fhort/commerce/test_esmena_bloc_a.py` | net |
| `python -m py_compile` dels 5 fitxers tocats al commit 1 | net |
| `manage.py test` | **NO EXECUTAT** (prohibició explícita del brief) — sense veredicte verd/vermell sobre el contingut |

---

## Sortida d'aquest tancament
```
git log --oneline 2fe707b5..HEAD
  a78b3800 test(commerce): contractes nous del bloc A · ESCRITS, NO EXECUTATS
  63a2f583 fix(commerce): retirar la porta generate/ de la fitxa d'encàrrec
git show 63a2f583   # generate/ retirat + 9 claus i18n mortes
git show a78b3800   # els 29 tests
```

## 🚩 ANOTAT, NO TOCAT
1. **`WorkOrder.delivery_note` és ara un camp llegat** (v. supra): ningú l'escriu, i
   `WorkOrderDetail.jsx` encara el llegeix per al botó «Veure albarà». Viu; no fa mal; és
   deute de comentari més que de codi. Vol decisió d'Agus només si algun dia es vol retirar
   del model (migració).
2. **Els 29 tests no s'han executat.** Quan es corrin (`python manage.py test
   fhort.commerce.test_esmena_bloc_a`), el primer vermell honest compta més que la meva
   lectura del codi: són fidels a les signatures d'avui, no a un comportament verificat.
3. **Els 6 tokens del `PdfButton`, les 2 contradiccions de maqueta i els 11px** segueixen
   sense tocar (deute declarat, fora d'abast des de l'ordre original).
