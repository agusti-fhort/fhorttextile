# DIAGNOSI S42 · Escalat del 1379 i el botó «Mesurar prenda»

> **Patró A · READ-ONLY.** Cap escriptura a BD, cap fitxer del repo modificat, cap commit, cap push.
> Totes les sondes són `GET` (APIClient forçat) i lectures d'ORM dins del tenant `fhort`.

## Capçal — l'estat verificat abans de diagnosticar res

| Què | Valor | Com s'ha llegit |
|---|---|---|
| Branca | `dev` | `git branch --show-current` |
| HEAD | `987ca023` · 2026-08-16 **15:21:45 UTC** | `git log -1` |
| `ftt-staging` (gunicorn) | `active (running)` des de 2026-08-16 **12:23:34 UTC** | `systemctl show -p ActiveEnterTimestamp` |
| `frontend/dist` | construït 2026-08-16 **15:21:28 UTC** | `ls --time-style=full-iso dist/index.html` |
| Root del vhost | `/var/www/ftt-staging/frontend/dist` | `/etc/nginx/sites-enabled/ftt-staging:24` |

**El backend NO està desfasat, i s'ha comprovat en comptes de suposar-ho.** El gunicorn va
arrencar a les 12:23:34 i HEAD és de les 15:21:45, o sigui que la llei
[`ftt-backend-desplegat-vs-disc`] hi aplicaria — però els dos commits posteriors a l'arrencada no
toquen backend: `987ca023` és `EditableTable.jsx` + i18n ×3, i `4db5158d` és d'**11:40:14 UTC**,
anterior a l'arrencada. Cap `.py` del camí d'aquesta diagnosi ha canviat des que el procés viu.

**⚠️ El NAVEGADOR sí que estava desfasat a l'hora de la captura, i té evidència.**
`/var/log/nginx/ftt-staging-access.log`:

```
15:14:05 GET /assets/ModelSheet-DP8RFQ5p.js  304   ref: /models/1379
15:14:05 GET /assets/index-CR3RvM7R.js       304   ref: /models/1379
```

Aquell va ser **l'últim càrrega de pàgina sencera** (després només hi ha `timers/` i
`model-task-items/371/` cada 60 s, fins a les 15:42). El `dist` d'ara serveix
`ModelSheet-DROGH2D1.js` + `index-fdst7Cxt.js`, construïts a les 15:21:28 — **7 minuts després**
de l'última càrrega. La captura de les 17:34 (=15:34 UTC) mirava el bundle anterior.
Això **no** explica Q1 (v. avall: el repartiment és de `dbb8305e`, 12/08, i qualsevol build
posterior el porta), però ha de constar: **la primera cosa a fer abans de tornar a mirar la
pantalla és una recàrrega dura.**

### Dades del 1379, llegides en viu

```
MODEL 1379 · BRW-FW26-0002 · RUFFLES · customer=7 · run XXS·XS·S·M·L · base S
ModelGarment:      id=4 codi='02' nom='Short' ordre=1 · run/base/ruleset = NULL (hereta)
BaseMeasurement:   garment=''  is_active=True → 11 files
                   garment='02' is_active=True →  7 files
SizeFitting:       366        GradingVersion vigent: None
ModelGradingRule:  garment='' → 13 · garment='02' → 0        model.grading_rule_set_id: None
```

**Les comportes ja no hi són.** `SELECT … FROM pg_constraint WHERE conname LIKE '%garment_gate_set2%'`
→ **CAP**. Això és rellevant per a tot el document: hi ha almenys cinc llocs del codi el docstring
dels quals diu «revisar el dia que es retirin les comportes». Aquell dia **ja ha passat**.

---

## Q1 — ESCALAT: el repartiment per prenda

### Veredicte curt

> **El símptoma descrit NO es reprodueix.** El repartiment per `garment` de l'Escalat és present,
> correcte al codi font, correcte al bundle desplegat, i correcte contra les dades reals del 1379.
> **El que SÍ està trencat al mateix carril són dues altres coses**, i totes dues són el patró de
> família: la **REGLA** que la fila ensenya i, sobretot, **l'ESCRIPTURA**, que està clavada a la mare.

### El camí, citat

| Peça | Fitxer:línia |
|---|---|
| Superfície | [ModelSheet.jsx:1341](frontend/src/pages/ModelSheet.jsx#L1341) — `<PropagatedEditor inline readOnly={editing !== 'Escalat'} />`. És l'ÚNIC muntatge; `App.jsx:456` (`/models/:id/escalat`) hi torna a caure. |
| Contenidors | [PropagatedEditor.jsx:251](frontend/src/pages/PropagatedEditor.jsx#L251) — `<PecesDelModel model={modelInfo}>` |
| **El predicat del repartiment** | [PropagatedEditor.jsx:252](frontend/src/pages/PropagatedEditor.jsx#L252) — `filesDeLaPeca(gridRows, peca ? (peca.codi \|\| '') : null)` |
| La funció | [identitatMesura.js:69](frontend/src/utils/identitatMesura.js#L69) — `filter(f => (f.garment \|\| '') === eix)`; `null` = «encara no ho sabem» → **totes** |
| L'adaptador | [fittingGridAdapter.jsx:358](frontend/src/components/model/fittingGridAdapter.jsx#L358) `buildEscalatRows`, amb `garment: row.garment` a la [:379](frontend/src/components/model/fittingGridAdapter.jsx#L379) |
| Un contenidor per peça | [PecesDelModel.jsx:64-76](frontend/src/components/model/PecesDelModel.jsx#L64-L76) |
| **El payload** | [models_app/views.py:1982](backend/fhort/models_app/views.py#L1982) `measurements_table_view`; emet `'garment': bm.garment` a la [:2087](backend/fhort/models_app/views.py#L2087) (des de `f6d99e30`, 11/08 21:15 — molt anterior a l'arrencada del gunicorn) |

### La prova, no la lectura

Payload real + codi real (`filesDeLaPeca` importat del fitxer; `buildEscalatRows` extret del `.jsx`
i avaluat tal qual). Sonda a `scratchpad/sim_escalat.mjs`:

```
payload: 18 files · sizes=XXS,XS,S,M,L · base=S
gridRows: 18 · amb garment definit: 18
garments: ["","","","","","","","","","","","02","02","02","02","02","02","02"]
contenidor codi=""   (RUFFLES) → 11 files: B BB B1 BF D G1 FS FS2 FS3 FS4 FS5
contenidor codi="02" (Short)   →  7 files: FR FE CT M M1 F1 FT      ← les SET del brief
contenidor únic (peces=null)   → 18 files (control: /peces/ no ha contestat)
```

I el mateix, verificat **al bundle desplegat** (no al font): `dist/assets/ModelSheet-DROGH2D1.js`
conté `Lt` = `PecesDelModel` amb `He(E, t?t.codi||"":null)`, i
`dist/assets/identitatMesura-D8pZF_KS.js` porta el filtre sencer:
`function n(e,t){return t==null?e||[]:(e||[]).filter(e=>(e.garment||``)===t)}`.

**Conclusió Q1(repartiment):** ni hi falta el filtre ni hi falla. El predicat de MODEL colat que
buscàvem **no és aquí**. La hipòtesi de família es descarta *per a aquest punt* — i es confirma,
amb dany, dos paràgrafs més avall.

### 🚨 Q1-bis · LA REGLA de la fila SÍ que és un predicat de MODEL colat

[models_app/views.py:2042](backend/fhort/models_app/views.py#L2042) → `rules_by_pom = _load_grading_rules(model)`
[models_app/views.py:2075](backend/fhort/models_app/views.py#L2075) → `rule = rules_by_pom.get(pom.id)`

`_load_grading_rules` ([pom/services.py:774](backend/fhort/pom/services.py#L774)) és, literalment,
**una vista de la peça mare**:

```python
return {pom_id: regla
        for (pom_id, garment), regla in _load_grading_rules_per_garment(model).items()
        if garment == ''}
```

El seu propi docstring ([:815-821](backend/fhort/pom/services.py#L815-L821)) ho diu tot:

> *«QUAN ES REVISA, i és una condició, no una data: **el dia que es retirin les comportes
> `*_garment_gate_set2`**. A partir d'aquell punt un '02' pot existir i aquests cinc rètols
> podrien anunciar la llei de la mare sobre una fila que en té una altra».*

**La condició s'ha complert** (0 comportes vives, verificat) i la feina no s'ha fet. Les columnes
Δ / Δ break / talla break de l'Escalat ([fittingGridAdapter.jsx:399+](frontend/src/components/model/fittingGridAdapter.jsx#L399), `escalatRuleLeadCols`) pinten,
per a cada fila de la 02, **la regla de la mare**.

**I per què no canta en vermell:** al 1379 la 02 té **0** `ModelGradingRule` pròpies, o sigui que
la regla efectiva de la 02 *és* la de la mare per herència. El número que surt és el correcte —
però pel camí equivocat. **És el forat que es tapa amb ell mateix**, el mateix patró que
[`ftt-nom-local-que-repeteix-tapa-la-traduccio`]: rellegir el codi no ho ensenya, i mirar la
pantalla tampoc. **El cas real on es podrà veure ja existeix**: el POM **962 (G1)** viu a LES DUES
peces amb la mateixa `(capa, instancia)`. El dia que la 02 tingui regla pròpia per al 962, la
seva fila seguirà ensenyant la de la mare.

### 🚨 Q1-ter · L'ESCRIPTURA de l'Escalat està CLAVADA a la mare (dany viu)

Això no és un rètol. És on la cel·la es desa.

**El client no envia l'eix** — [endpoints.js:152-154](frontend/src/api/endpoints.js#L152-L154):

```js
escalatAjustarTalla: (modelId, pomId, talla, valor, eixos = {}) =>
  client.post(`/api/v1/models/${modelId}/escalat/ajustar-talla/`,
              { pom_id: pomId, talla, valor, capa: eixos.capa, instancia: eixos.instancia }),
```

…i això tot i que la fila **sí** que sap dir la seva peça: `perLinia`
([PropagatedEditor.jsx:60-63](frontend/src/pages/PropagatedEditor.jsx#L60-L63)) hi desa `garment`, i
[:82](frontend/src/pages/PropagatedEditor.jsx#L82) el deixa caure en construir la crida.

**El backend el desestructura i no el fa servir enlloc** —
[views.py:3346](backend/fhort/models_app/views.py#L3346): `capa, instancia, garment = _identitat_de_mesura(data)`.
Cerca de `garment` entre la :3346 i la :3500: **cap ús** fora d'un comentari i d'un literal `''`.
Les **quatre** vores d'escriptura/lectura d'aquesta vista van a la mare:

| Vora | Línia | Filtre |
|---|---|---|
| `_write_base` → `BaseMeasurement` | [:3689](backend/fhort/models_app/views.py#L3689) | la signatura **no té paràmetre `garment`**: `get_or_create(model, pom, capa, instancia)` |
| `ModelGradingOverride.delete()` | [:3421](backend/fhort/models_app/views.py#L3421) | `(model, pom, capa, instancia)` — sense `garment` |
| `ModelGradingOverride.update_or_create()` + `MeasurementChangeLog.create()` | [:3437-3448](backend/fhort/models_app/views.py#L3437-L3448) | idem |
| Resposta (`linies`) | [:3493](backend/fhort/models_app/views.py#L3493) i [:3496](backend/fhort/models_app/views.py#L3496) | `garment=''` **explícit** i `clau_mesura(pom.id, capa, instancia, '')` |

`ModelGradingOverride` i `MeasurementChangeLog` **tenen** columna `garment` (verificat a
`models_app/models.py`), i el motor ja hi indexa
([pom/services.py:943](backend/fhort/pom/services.py#L943), clau de 5 camps). No és que la dada no
hi càpiga: és que aquesta vora no la posa.

**Conseqüències, contra el 1379, amb `SizeFitting 366` existent (o sigui, sense el 400 primerenc):**

1. **500 real i reproduïble.** POM **962 (G1)**, `('exterior','')`, viu a les dues peces →
   `_write_base` fa `get_or_create` sobre **dues** files → `MultipleObjectsReturned`.
   Camí exacte: 962 és `FIXED` → `propaga=False` → branca `elif talla == base_size` ([:3427](backend/fhort/models_app/views.py#L3427))
   → `_write_base`. **Editar la cel·la S del G1, des de QUALSEVOL dels dos contenidors, peta.**
2. **Refresc que no arriba.** Per als 6 POMs que només viuen a la 02 (954·955·914·993·956·949),
   el `get_or_create` encerta la fila per casualitat (no hi ha germana a la mare), però la resposta
   llegeix specs amb `garment=''` i torna `clau` de la mare → el `lineId` no casa amb el de la
   graella (`{clau}:{talla}` amb quatre trams) i **les cel·les germanes es queden amb el valor
   vell fins a recarregar**. És el defecte ② que la pròpia vista documenta a la [:3474](backend/fhort/models_app/views.py#L3474)… un eix més tard.
3. **Poda creuada.** El `delete()` d'overrides s'enduria els de **les dues** peces per al mateix POM.

**Nota d'honestedat:** la vista **ja avisa** d'això a la [:3477-3486](backend/fhort/models_app/views.py#L3477-L3486)
(«Obrir el contracte d'ESCRIPTURA al garment és un tram propi»). No és un descuit: és **deute
declarat i datat que ha vençut** el dia que la 02 va existir amb dades. El que ha canviat des
d'aquell comentari és que ara hi ha un model real que el travessa.

### La sub-pregunta: ¿joc EFECTIU per herència D5-bis, o camp buit del garment?

**Les dues coses, i cadascuna per un camí diferent:**

- **El JOC (ruleset) del contenidor: EFECTIU i correcte.** Ve de `GET /peces/`
  ([garment_views.py:108](backend/fhort/models_app/garment_views.py#L108)), que serveix `valor`
  ja resolt per `services_garment.valor_efectiu`, i `PecaContenidor` el llegeix sense cap
  `peca.X || model.X` ([PecaContenidor.jsx:82-84](frontend/src/components/model/PecaContenidor.jsx#L82-L84)).
  Verificat en viu: la 02 del 1379 torna `grading_rule_set: {valor: null, etiqueta: '', heretat: true}`
  i `size_run/base` amb `heretat: true`. La resolució «override nullable → hereta» hi és.
- **Les REGLES per fila: NO passen per la resolució efectiva.** La funció que la fa —
  `_regla_de` ([pom/services.py:897](backend/fhort/pom/services.py#L897): pròpia de la peça →
  si no, la de la mare, que és exactament D5-bis) — **existeix, és correcta i el motor la fa
  servir** ([services.py:243](backend/fhort/pom/services.py#L243) i [:457](backend/fhort/pom/services.py#L457)).
  L'Escalat no hi entra: es queda a `_load_grading_rules(model).get(pom.id)`.

O sigui: **no llegiria el camp buit del garment** (ningú fa `garment.increment or model.increment`),
però **tampoc fa l'herència**: agafa la de la mare i prou. Avui el resultat coincideix; el dia que
divergeixin, mentirà. **La font ja existeix i el fix és mecànic**, tal com el docstring anuncia:
`_regla_de(_load_grading_rules_per_garment(model), pom_id, garment)`.

---

## Q2 — El botó «Mesurar prenda» apagat

### El predicat, citat

[ModelSheet.jsx:1266-1276](frontend/src/pages/ModelSheet.jsx#L1266-L1276):

```jsx
<button type="button"
  disabled={openingTask || (estatPas != null && !estatPas.te_taula)}
  title={estatPas != null && !estatPas.te_taula ? t('model_sheet.pas_sense_taula') : undefined}
  onClick={() => enterEdit('Mesures', 'size_check')}
  style={btnPas(estatPas != null && !estatPas.te_taula ? 'blocat' : (estatPas?.te_presa ? 'fet' : 'ara'), openingTask)}>
```

…i el rètol de fora, [:1277-1281](frontend/src/pages/ModelSheet.jsx#L1277-L1281), amb la mateixa
condició i la clau `model_sheet.pas_sense_taula` ([i18n/ca.json:992](frontend/src/i18n/ca.json#L992)):
**«Cal gravar el POM per generar la taula de talles»**.

`estatPas` = `GET /api/v1/models/<id>/grading-status/`
([ModelSheet.jsx:809](frontend/src/pages/ModelSheet.jsx#L809) i [:900](frontend/src/pages/ModelSheet.jsx#L900)).

### Què vol dir «POM gravat» per a aquest predicat: **res**

El predicat **no mira els POM ni les files**. Mira `te_taula`, i `te_taula` és
[views.py:3782](backend/fhort/models_app/views.py#L3782):

```python
te_taula = bool(gv and gv.is_active and GradedSpec.objects.filter(
    grading_version=gv, is_active=True).exists())
```

O sigui: **existeix una `GradingVersion` vigent i activa amb `GradedSpec` actives** — la taula de
talles PROPAGADA. No `BaseMeasurement`, no un flag del model, no un comptador de files. El fet
«els POM estan gravats» té un altre camp al mateix payload, `te_mesures`, i el predicat no el toca.

### Contra el 1379 real

`GET /api/v1/models/1379/grading-status/` (sonda read-only, tenant `fhort`):

```json
{"te_mesures": true, "te_taula": false, "te_presa": false, "te_propagacio": false,
 "te_dades_propagades": false, "segellada": false, "version_number": null,
 "estalitud": null, "te_regles": true}
```

I la lectura directa: `SizeFitting 366` existeix, **`GradingVersion` vigent = `None`**, i les 18
files de `taula-mesures` tornen `graded: {}` — **zero `GradedSpec` a tot el model**.

### 🔴 VEREDICTE Q2 = **(a) condició legítima**, amb el bug a la COMUNICACIÓ

**El botó té raó d'estar gris.** La taula de talles no s'ha generat mai: el pas ④ **Propagar** no
s'ha executat. Prémer «Mesurar prenda» hauria topat igualment amb el gate dur de `create-piece`.
El predicat **no** és de la família: no col·lapsa peces, no compta la mare i el Short com un, no
mira només `garment=''` — **no mira peces en absolut**, perquè el que mira (la versió de grading)
és de model per naturalesa.

**El defecte és que el rètol acusa el pas equivocat.** Diu «Cal gravar el POM» quan:
- `te_mesures: true` — els POM **estan** gravats, amb valor, a les dues peces;
- el botó ① es pinta amb ✓ **tres píxels més a l'esquerra** ([:1233](frontend/src/pages/ModelSheet.jsx#L1233));
- `te_regles: true` — el ② també està fet.

La pantalla es contradiu a un pam de distància: un ✓ al pas ① i, al costat, una frase que demana
fer el pas ①. L'usuari que veu «tots els POM definits amb valors a la taula» **té raó**, i la
pantalla li està dient que no.

**És exactament el mateix defecte que HEAD (`987ca023`) acaba d'arreglar per a «Gravar POM»**, i
val la pena citar-lo perquè la llei ja està escrita a l'acta d'aquell commit: *«El defecte no era
el predicat: era que la pantalla callava les dues coses que la persona havia vingut a saber»* ·
*«Un botó apagat sense causa és una porta tancada sense rètol»*. Aquí la porta té rètol, i el
rètol **menteix**. És un grau pitjor: un motiu fals costa més que un silenci, perquè envia el
tècnic a repetir una feina que ja està feta.

### La (b) hi és igualment, però LATENT — i **no comparteix helper amb Q1**

Cap dels quatre fets de `grading_status_view` reparteix per prenda: `te_mesures`, `te_taula`,
`te_presa` i `te_propagacio` són **de model**. El dia que la mare estigui propagada i la 02 no
(cosa que el motor ja permet: `_regla_de` gradua per peça), `te_taula` valdrà `true` **per una
peça sola**, el botó s'encendrà, i la presa obrirà un contenidor Short sense taula de talles.

**Q1 i Q2 NO comparteixen funció ni helper**:

| | Q1 | Q2 |
|---|---|---|
| On viu | front `filesDeLaPeca` (bé) + back `_load_grading_rules` / `escalat_ajustar_talla_view` | back `grading_status_view` |
| Naturalesa | eix de fila (per mesura) | fet agregat (per model) |
| Fix | passar `garment` pel contracte d'escriptura i pel lookup de regla | dir QUIN pas falta + repartir els quatre fets per peça |

**El fix són dos, i els guards dos.** No hi ha un sol punt que els tanqui tots dos.

---

## Q3 — Cens de la família (candidats a 5a aparició)

Grep dirigit al frontend: lectures de mesures/files del model que **no** reparteixen per `garment`.
Llista amb una línia de context; **no diagnosticats**.

### Ja reparteixen (6 superfícies — el control del cens)

`PropagatedEditor.jsx:252` · `GraduacioSuperficie.jsx:421` · `MeasuresEntryPanel.jsx:479` ·
`CheckMeasureEditor.jsx:750-751` · `FittingRepasPanel.jsx:75,81` — totes amb `filesDeLaPeca` dins
d'un `PecesDelModel`.

### Candidats

| # | Fitxer:línia | Context |
|---|---|---|
| 1 | [TechSheetEditor.jsx:5066](frontend/src/pages/TechSheetEditor.jsx#L5066) | T1a `base_measures`: `garmentId: GARMENT_MARE` **clavat**, i `rows = bms.map(...)` sobre **totes** les mesures del model. El payload `base-measurements/` **sí** que emet `garment` (i fins i tot `regla_model` resolta per `_regla_de`): la vora ja serveix l'eix i la inserció el descarta. La T1b (`pom_grading`, [:5191](frontend/src/pages/TechSheetEditor.jsx#L5191)) i la de fitting ([:5132](frontend/src/pages/TechSheetEditor.jsx#L5132)) **sí** parteixen (`g.garment`, `partirTaules`). |
| 2 | [utils/garmentFitxa.js:34-43](frontend/src/utils/garmentFitxa.js#L34-L43) | Afirmació d'estat **datada 2026-08-10 i ja falsa**: «AVUI CAP PAYLOAD LA SERVEIX» i «`SELECT DISTINCT garment` → només `''`». Avui `taula-mesures`, `base-measurements`, `graded-table` i `comprovacio` la serveixen, i el 1379 té `'02'` a la BD. La nota diu «re-verificar amb…»; s'ha re-verificat i cal actualitzar-la. |
| 3 | [ComprovacioPanel.jsx](frontend/src/components/model/ComprovacioPanel.jsx) (tot el fitxer) | Zero `garment` / `filesDeLaPeca` / `PecesDelModel`. Agrupa per «famílies» i «cares» (capa·instància, [:341-363](frontend/src/components/model/ComprovacioPanel.jsx#L341-L363)) i mai per prenda — tot i que `comprovacio_views.py` **sí** que indexa per la identitat de 4 camps ([:169](backend/fhort/models_app/comprovacio_views.py#L169), [:216](backend/fhort/models_app/comprovacio_views.py#L216), [:320](backend/fhort/models_app/comprovacio_views.py#L320)). Les files de les dues peces cauen a la mateixa llista. |
| 4 | [FittingDetail.jsx:687](frontend/src/pages/FittingDetail.jsx#L687) | `(g.lines \|\| []).map(l => l.pom_id === row.pom_id ? …)` — el refresc de règim després de `setPomRegim` casa per **`pom_id` sol**: ni capa, ni instància, ni garment. El fitxer sencer no té cap ocurrència de `garment`. |
| 5 | [api/endpoints.js:152-154](frontend/src/api/endpoints.js#L152-L154) | `escalatAjustarTalla` no envia `garment` (v. Q1-ter). És la vora del contracte, no una lectura, però pertany al mateix cens. |
| 6 | [EditableTable.jsx:413](frontend/src/components/EditableTable/EditableTable.jsx#L413) · [:477](frontend/src/components/EditableTable/EditableTable.jsx#L477) · [:535](frontend/src/components/EditableTable/EditableTable.jsx#L535) · [:663](frontend/src/components/EditableTable/EditableTable.jsx#L663) · [:983](frontend/src/components/EditableTable/EditableTable.jsx#L983) | Cinc predicats de germanor per `(pom_id, capa, instancia)` sense `garment` (capes lliures, germana ràpida, `dimState`, `germanesDeLEix`, `existents`). **Segurs AVUI però per construcció, no per predicat**: `MeasuresEntryPanel:479` ja li passa `rows` d'un sol contenidor. Es trencarien el dia que algú munti la taula sense el repartiment al davant. |
| 7 | [TaulaPOMsCataleg.jsx:142](frontend/src/components/cataleg/TaulaPOMsCataleg.jsx#L142) | `r.pom_id === fila.pom_id && (r.instancia \|\| '') === …` sense capa ni garment. És el catàleg del client (no files de model): rellevància baixa, s'anota per completesa. |
| 8 | [ModelSheet.jsx:270](frontend/src/pages/ModelSheet.jsx#L270) | `hasBaseValue = taulaRows.some(r => r.base_value_cm != null)` — decisió genesi↔consulta **de model** sobre files de dues peces. Probablement legítim (és de model), s'anota perquè és el mateix vocabulari. |

### Al backend, el cens ja el porta el codi

`grep -rn "_load_grading_rules(" --include=*.py` → **5 consumidors** vius, tots «llegeixen la mare
a posta» segons l'acta de SET-2/T5, amb la condició de revisió **ja complerta**:

`fitting/serializers.py:264` · `fitting/graded_spec_views.py:171` ·
`models_app/serializers_size_check.py:97` · `models_app/views.py:2042` · `models_app/views.py:3388`

El cinquè (**`views.py:3388`**) és el greu i cal separar-lo dels altres quatre: **no pinta un
rètol, decideix una ESCRIPTURA** (si l'ajust propaga o no). L'acta de T5 diu exactament que
aquest cas s'havia d'adaptar («No és presentació: decideix una ESCRIPTURA cap a la mesura base»)
i el va adaptar per a `fitting/views.py` — però `escalat/ajustar-talla` va quedar fora del cens.

---

## Q4 · «Taula de mesures» — el 9è candidat, i el cens no el va veure

> **Segona passada, 16/08 16:2x UTC.** Branca `dev`, HEAD **`25c306de`** (F2 ja entrat),
> gunicorn des de **12:23:34 UTC** (sense reiniciar), `dist` reconstruït **16:13:51 UTC**.
> Read-only estricte.

### El fet nou que ho tanca

L'Escalat del 1379 **reparteix bé en viu** (11 + 7), i la «Taula de mesures» del **mateix
model, mateix bundle** no. Això elimina d'un cop el payload, el bundle i `filesDeLaPeca` —les
tres coses que la passada anterior va perseguir— i deixa una sola diferència possible: **què
li arriba al filtre**. I efectivament: no és el mateix.

### El camí de render, citat

| Pas | Fitxer:línia |
|---|---|
| Sub-vista per defecte de Mesures | [ModelSheet.jsx:1315](frontend/src/pages/ModelSheet.jsx#L1315) — `mesuresView === 'taula'` cau a `<CheckMeasureEditor model={model} readOnly />` |
| Contenidors | [CheckMeasureEditor.jsx:748](frontend/src/components/model/CheckMeasureEditor.jsx#L748) — `<PecesDelModel model={model}>` |
| **La bifurcació** | [CheckMeasureEditor.jsx:602](frontend/src/components/model/CheckMeasureEditor.jsx#L602) — `const esPresa = src.kind === 'check'` |
| **L'adaptador que pinta aquesta pantalla** | [CheckMeasureEditor.jsx:603-645](frontend/src/components/model/CheckMeasureEditor.jsx#L603-L645) — `rowsPresa`, el «mode presa de l'eina mesures» (v8.1) |
| El repartiment | [CheckMeasureEditor.jsx:751](frontend/src/components/model/CheckMeasureEditor.jsx#L751) — `filesDeLaPeca(rowsPresa, eixPeca)` |
| La taula | [CheckMeasureEditor.jsx:766-773](frontend/src/components/model/CheckMeasureEditor.jsx#L766-L773) — `<EditableTable rows={presaDelContenidor} …>` |

### 🚨 El punt exacte de divergència

`esPresa` és `src.kind === 'check'` — i el CHECK és **la font per defecte**. O sigui que
`esPresa` val `true` **també en consulta**, i aquesta pantalla no passa mai per `MeasureGrid`:
va sempre a `EditableTable` amb `rowsPresa`.

I `rowsPresa` **no copia `garment`**. Copia `id`, `lineId`, `pom_id`, `pom_code`, `capa`,
`instancia`, els quatre noms, `is_key`, `base_value_cm`, la regla i `base_vigent`
([:609-643](frontend/src/components/model/CheckMeasureEditor.jsx#L609-L643)) — **l'eix de
prenda no hi és a cap línia**.

El contrast, al mil·límetre, amb l'Escalat:

```
buildEscalatRows      fittingGridAdapter.jsx:379    garment: row.garment      ← hi és
buildRepasRows        repasGridAdapter.jsx:151      garment: row.garment      ← hi és
buildRows (check)     CheckMeasureEditor.jsx:304    garment: r.garment        ← hi és
rowsPresa             CheckMeasureEditor.jsx:603    —                         ← NO HI ÉS
```

I la conseqüència és **exactament el forat mut** que el banc de `a2e0eb1c` va deixar escrit:
`filesDeLaPeca` fa `(f.garment || '') === eix`, i `undefined || ''` és `''`. Les 18 files
passen el filtre de la MARE i cap no passa el de la 02:

```
filesDeLaPeca(rowsPresa, '')   → 18   ← «Model base» amb tot
filesDeLaPeca(rowsPresa, '02') →  0   ← «Short» amb el capçal i res més
```

Sense error, sense avís i sense rastre. La pantalla no pot distingir «aquesta fila és de la
mare» de «algú ha deixat caure el camp pel camí», perquè el filtre no en té manera.

### ⚠️ Per què la passada anterior el va donar per bo (i què cal aprendre'n)

El Patró A va verificar `CheckMeasureEditor.buildRows` ([:271](frontend/src/components/model/CheckMeasureEditor.jsx#L271))
i va concloure que la superfície de Mesures repartia. **`buildRows` copia l'eix, sí — però
aquesta pantalla no el crida.** `rows` ([:698](frontend/src/components/model/CheckMeasureEditor.jsx#L698))
només alimenta la branca `MeasureGrid`, i amb la font check aquella branca no s'executa mai:
`buildRows` serveix únicament el camí de FITTING. **Es va auditar l'adaptador que aquesta
pantalla no fa servir.**

I el cens Q3 tampoc el podia veure, perquè **preguntava el que no calia**: va buscar
«superfícies que NO criden `filesDeLaPeca`». Aquesta el crida —línia 751, ben cridat— i el que
falla és el que li arriba. La pregunta que troba aquest bug és l'altra: **«qui CONSTRUEIX
files que acaben en un filtre per eix, i les hi porta senceres?»**. Els vuit candidats de Q3
segueixen sent vàlids; aquest és un **9è**, i no és un que se'ns escapés per poc: era invisible
des de l'angle on miràvem.

### ¿El mateix helper que Q1? **No. Són dos fixos i dos guards.**

| | Q1 (Escalat) | Q4 (Taula de mesures) |
|---|---|---|
| Filtre | `filesDeLaPeca` ✔ correcte | `filesDeLaPeca` ✔ correcte |
| Adaptador | `buildEscalatRows` ✔ porta l'eix | **`rowsPresa` ✘ el deixa caure** |
| Què falla | l'**escriptura** (F1: el `garment` no viatja al backend) | la **lectura**: les files no arriben al contenidor |
| Fix | contracte + 4 vores de `escalat_ajustar_talla_view` | **una línia** a `rowsPresa` |

Comparteixen el `filesDeLaPeca` i prou, i aquell no s'ha de tocar. **F1 i F5 són independents:
es poden fer en qualsevol ordre i no es toquen.**

### 🚩 Dany adjacent al mateix adaptador (anotat, NO tocat)

`rowsPresa` no és només lectura: alimenta `presaPortes`
([:649-692](frontend/src/components/model/CheckMeasureEditor.jsx#L649-L692)), i **tres portes
d'escriptura hereten el forat** perquè construeixen la identitat a partir de la fila:

- `onNova` ([:683](frontend/src/components/model/CheckMeasureEditor.jsx#L683)) — `baseMeasurements.create({model, pom, capa, instancia, …})` **sense `garment`**: una mesura nova creada des del contenidor de la 02 **neix a la mare**.
- `onParteix` ([:664](frontend/src/components/model/CheckMeasureEditor.jsx#L664)) — el mateix `create`, mateix forat: partir un POM de la 02 posa la germana a la mare.
- `onDesfaInstancia` ([:679](frontend/src/components/model/CheckMeasureEditor.jsx#L679)) — `desactivarPom(model, pom, undefined, {capa, instancia})` sense eix.

I el muntatge d'`EditableTable` d'aquí ([:766](frontend/src/components/model/CheckMeasureEditor.jsx#L766))
**no passa el prop `garment`**, que per defecte és `''`
([EditableTable.jsx:148](frontend/src/components/EditableTable/EditableTable.jsx#L148)) —
mentre que l'altre muntatge del MATEIX component sí que el passa
([MeasuresEntryPanel.jsx:511](frontend/src/components/model/MeasuresEntryPanel.jsx#L511)). El
mateix component, dos muntatges, un amb eix i l'altre sense. Avui el prop només mana a
`esBruta`/`construeixPayload` (que la presa no fa servir, perquè desa per fila), o sigui que
**no hi ha esborrat silenciós per aquesta via** — però el dia que la presa passi pel desat en
bloc, sí que n'hi hauria.

⚠️ Això és escriptura i **queda fora del fix mínim de Q4**. Es diu aquí perquè viu a tres
metres i el fix de lectura no el tanca.

### El joc de regles del contenidor Short: **NO seria l'efectiu** (mateix defecte que Q1-bis)

Quan les 7 files arribin al contenidor Short, la seva regla la servirà `reglaPerPom`
([CheckMeasureEditor.jsx:592-596](frontend/src/components/model/CheckMeasureEditor.jsx#L592-L596)),
i falla per **dues** raons independents:

1. **Backend — la llei de la mare.** `raw.regles` és `taula-mesures`, i allà `logica`/
   `increment_*` surten de `_load_grading_rules(model)` ([views.py:2042](backend/fhort/models_app/views.py#L2042))
   + `.get(pom.id)` ([:2075](backend/fhort/models_app/views.py#L2075)), que és **una vista de
   `garment=''`** ([pom/services.py:823-825](backend/fhort/pom/services.py#L823-L825)). És
   literalment el Q1-bis d'aquest mateix document.
2. **Front — el `Map` col·lapsa l'eix.** `new Map(rows.map(x => [x.pom_id, …]))`: clau
   `pom_id` **sol**. Amb el payload real del 1379 hi ha **tres** `pom_id` duplicats —
   `906`, `958` i `962`— i **l'últim escrit guanya**:

   ```
   pom 906 → guanya garment=''    (3 instàncies de la MARE: top·bottom·extended)
   pom 958 → guanya garment=''    (3 instàncies de la MARE: cf·cb·waistband_seam)
   pom 962 → guanya garment='02'  ← LA FRONTERA DE PRENDA, no germanor
   ```

   El comentari de [:637-640](frontend/src/components/model/CheckMeasureEditor.jsx#L637-L640)
   justifica la clau curta —«`ModelGradingRule` no porta capa ni instancia […] dues germanes
   COMPARTEIXEN regla»— i **té raó per a dos dels tres eixos i no per al tercer**:
   `ModelGradingRule` **sí** que és única per `(model, pom, garment)` (T3, i el front ja en té
   la clau pròpia a `identitatMesura.clauRegla`). Dels tres duplicats del 1379, dos són
   germanor legítima i el tercer és una frontera; el comentari no els distingeix.

**Per què no canta:** el 962 de la 02 i el de la mare valen tots dos `FIXED · +0,0` —la 02 té
**0** `ModelGradingRule` pròpies i hereta— o sigui que la col·lisió dona el número correcte.
**El forat es tapa amb ell mateix**, tercera vegada en aquest document.

La resolució efectiva EXISTEIX i és correcta (`_regla_de`, [pom/services.py:897](backend/fhort/pom/services.py#L897),
D5-bis: pròpia de la peça → si no, la de la mare) i el motor la fa servir. **Aquest camí no hi
entra.** El que sí que és efectiu, com a l'Escalat, és el JOC del capçal del contenidor, que ve
de `/peces/` ja resolt per `valor_efectiu`.

---

## Propostes de fix, dimensionades (res implementat)

> Ordre recomanat: **F5 primer** (una línia, tanca una pantalla trencada en viu), després F1.
> ~~F2~~ ✅ ja entrat (`25c306de`).

### F5 · «Taula de mesures» reparteix les files — **XS (≈15 min)** · 1 commit

- `rowsPresa` ([CheckMeasureEditor.jsx:612](frontend/src/components/model/CheckMeasureEditor.jsx#L612))
  afegeix `garment: r.garment` al costat de `capa` i `instancia`. `base-stages` ja el serveix
  (verificat: 11 `''` + 7 `'02'`), o sigui que **no cal tocar cap contracte, cap endpoint i cap
  altre fitxer**. Una línia.
- Amb una sola prenda l'eix val `''` a totes les files i el repartiment és el mateix que ara:
  **cap canvi observable per al 100% del corpus d'una peça**.
- ⚠️ **NO tanca les tres portes d'escriptura** (`onNova`, `onParteix`, `onDesfaInstancia`) ni el
  prop `garment` d'`EditableTable`: v. «dany adjacent». Aquell és un tram propi i vol la seva
  QA, perquè fa néixer files.
- 🚩 I deixa el contenidor Short **ensenyant la regla de la mare** (v. Q4 § joc de regles). Avui
  el número és correcte per herència; el fix és el mateix pas 3 de F1 i s'hi ha de fer, no aquí.

### F2 · «Mesurar prenda» diu QUIN pas falta — **S (≈1 h)** · 1 commit

- El rètol deixa de ser una constant i passa a derivar-se de l'estat que ja arriba al mateix
  payload. Amb `te_mesures && te_regles && !te_taula` → **«Cal propagar a grading per generar la
  taula de talles»**, i el text apunta al pas ④. Amb `!te_mesures` → el text d'ara, que llavors
  és cert.
- Tres claus i18n noves amb paritat ca/en/es (i18n-gate).
- **Cap canvi de predicat i cap canvi de backend**: `disabled` es queda igual. És el fix de
  comunicació que la (a) demana.
- Fitxers: `ModelSheet.jsx:1266-1282` + `i18n/{ca,en,es}.json`.

### F1 · L'Escalat escriu a la peça de la fila — **L (≈1 dia)** · 3 commits

El tram que la vista mateixa anomena «un tram propi». Es fa en tres peces perquè cadascuna té la
seva porta verda:

1. **El contracte** — `escalatAjustarTalla` afegeix `garment: eixos.garment` (`endpoints.js:154`)
   i `PropagatedEditor.jsx:82` el passa des de `perLinia` (que ja el té). Client vell que no el
   digui → `_identitat_de_mesura` ja li dona `''`: **cap regressió per al corpus d'una peça**.
2. **Les quatre vores** — `escalat_ajustar_talla_view` fa servir el `garment` que ja
   desestructura: `_write_base` guanya el paràmetre (i el `get_or_create` el filtre — **això sol
   ja mata el 500 del POM 962**), els dos `ModelGradingOverride` i el `MeasurementChangeLog` el
   porten, i la lectura de resposta canvia `garment=''` per la variable i
   `clau_mesura(pom.id, capa, instancia, garment)`. Les columnes hi són; no cal migració.
3. **La regla** — `views.py:2042/2075` i `views.py:3388` passen a
   `_regla_de(_load_grading_rules_per_garment(model), pom_id, garment)`. **⚠️ Aquest és el pas
   que ja va trencar 13 tests una vegada** (SET-2/T4, documentat a `services.py:786-789`): es fa
   sol, en un commit propi, i amb el cens dels 5 consumidors al davant. Els altres tres
   consumidors (serializers, graded_spec_views, size_check) **no entren aquí**: són rètols i
   volen el seu propi tram amb la seva QA.

### F3 · Els quatre fets de `grading-status`, per peça — **M (≈3-4 h)** · 1 commit

- `grading_status_view` afegeix `per_peca: {'': {...}, '02': {...}}` **sense treure** els camps
  actuals (additiu; consumidors antics no es toquen).
- El stepper pinta l'estat de la peça quan n'hi ha més d'una. Requereix decidir **què significa
  el pas amb dues peces a estats diferents** — i això és decisió d'Agus, no de l'agent
  (proposta: el pas és «fet» quan **totes** les peces ho estan, i el rètol diu **quina** falta).
- Depèn de F2 (el vocabulari del rètol) i no de F1.

### F4 · Cens Q3 — **no és un fix, és backlog**

Els 8 candidats no es toquen en aquest tram. El #2 (`garmentFitxa.js:34-43`) és **1 línia** i val
la pena escombrar-lo amb qualsevol dels commits de dalt: una afirmació d'estat datada i falsa
dins d'un docstring és pitjor que cap afirmació, perquè la següent sessió s'hi refia.

---

## Guards que caldran en Patró B

**Llei d'aquesta casa: cada guard s'ha de veure VERMELL amb el cas real 1379 abans del fix, i VERD
amb el control d'una peça.** El banc de guards del front és `node --test` sobre funcions pures
(`frontend/src/utils/*.test.js`); no hi ha vitest ni testing-library, i **no s'ha d'inventar cap
harness nou**.

| # | Guard | On | Vermell AVUI amb… | Control una-peça |
|---|---|---|---|---|
| G1 | El payload d'`escalat/ajustar-talla` porta `garment` | `frontend/src/utils/…` (funció pura extreta de la construcció del cos) o test de backend sobre la vista | fila de la 02 → el cos ha de dur `garment='02'` | fila de la mare → `garment=''`, byte a byte com ara |
| G2 | **`_write_base` no col·lapsa germanes de PEÇA** | `backend/.../test_*.py`, patró de `test_set2_r3_germanes_garment.py` | POM **962** amb files a `''` i `'02'` → avui `MultipleObjectsReturned`; després, escriu **la seva** | un sol POM sense germana → una sola escriptura |
| G3 | La resposta torna la corba i la `clau` **de la peça editada** | test de la vista | ajustar una fila de la 02 → `linies[i].id` comença per `…\|02`, no per la clau de la mare | mare → `…\|` (4t tram buit), idèntic a ara |
| G4 | L'override i el `MeasurementChangeLog` no travessen la frontera | test de la vista | esborrar overrides del POM 962 des de la mare **no** toca els de la 02 | model d'una peça → una sola fila afectada |
| G5 | **La regla de la fila és l'EFECTIVA de la peça** | test sobre `measurements_table_view` | sembrar una `ModelGradingRule(garment='02')` diferent per al POM 962 → la fila de la 02 ha d'ensenyar la seva, no la de la mare. **Sense sembrar-la el guard és cec** (avui la 02 té 0 residents i el forat es tapa amb ell mateix) | la 02 sense residents → hereta la de la mare (`_regla_de`), i el número no canvia |
| G6 | El rètol de «Mesurar prenda» diu el pas que falta | `frontend/src/utils/*.test.js` — extreure el predicat a una funció pura `motiuPasBlocat(estatPas)` | `{te_mesures:true, te_regles:true, te_taula:false}` → clau «cal propagar», **no** «cal gravar el POM» | `{te_mesures:false, …}` → la clau d'ara |
| G7 | El repartiment de l'Escalat (**regressió**, ja verd) | `identitatMesura.test.js` ✅ fet a `a2e0eb1c` | — | payload del 1379: 11 files a `''`, 7 a `'02'`, 18 amb `peces=null`. **Congela el que aquesta diagnosi ha comprovat que funciona**, perquè el tram de F1 no l'espatlli pel camí |
| **G8** | **`rowsPresa` conserva l'eix** (Q4) | l'adaptador viu dins d'un `.jsx` i `node --test` no el pot importar → **cal extreure'l a `utils/` com a funció pura**, que és el que ja es va fer amb `calFilaDePeca` i amb `motiuPasPresa`, i pel mateix motiu | files reals de `base-stages` del 1379 → `filesDeLaPeca(rowsPresa, '')` = **11** i `(…, '02')` = **7**. Amb el codi d'avui dona **18 / 0** | model sense `'02'`: totes les files a `''`, `filesDeLaPeca(…, '')` = totes, cap canvi |

**El guard de G8 és el que hauria d'haver existit i no existia**, i val la pena dir per què: el
banc de `filesDeLaPeca` ja provava el filtre (i el filtre mai va fallar), però **cap banc provava
que els adaptadors li portessin l'eix**. Un banc que cobreix la funció compartida i deixa els
quatre alimentadors sense cobrir dona exactament aquesta seguretat falsa. Els altres tres
adaptadors haurien de caure sota el mateix guard en el mateix moviment: mentre visquin dins de
`.jsx`, cap d'ells té banc.

**Un avís de mètode per al Patró B:** el guard G5 és el que aquesta família ja ha esquivat quatre
vegades. Un guard que només comprovi «el número que surt és el correcte» **passarà en verd amb el
codi trencat**, perquè avui la 02 hereta. **Ha de sembrar la divergència primer.** El mateix val
per a G2: sense el POM 962 (o un equivalent fabricat) a les dues peces, la col·lisió no existeix i
el test no prova res.

---

## Fronteres respectades

No s'ha tocat motor (`generate_graded_specs`), ni G6/segell, ni billing, ni la màquina d'estats de
tasques. Totes les sondes són `GET` o lectures d'ORM. Sondes a
`scratchpad/{s42_probe.py, dump_payload.py, sf.py, gates.py, sim_escalat.mjs}` — fora del repo.

## Fils que queden oberts (anotats, no tocats)

- **P1+P2+P3 del brief anterior** segueixen fora: `987ca023` ho deixa escrit («toquen la màquina
  d'estats de tasques, on ja hi va haver el vermell Q1»).
- ✅ **El símptoma «Q1» té causa, i era una altra pantalla.** L'Escalat sempre va estar bé (ara
  confirmat en viu: 11 + 7). El que es reparteix malament és la **«Taula de mesures»**, i és el
  Q4 d'aquest document: `rowsPresa` deixa caure l'eix. La lliçó de mètode que se n'endú és
  **anomenar la pantalla amb la ruta i la sub-vista, no amb el concepte**: «Mesures › Taula de
  mesures» i «Escalat» comparteixen model, contenidors i `filesDeLaPeca`, i no comparteixen
  l'adaptador — que és justament l'única peça on hi havia el forat.
- 🚩 **F1** (l'escriptura de l'Escalat per peça) segueix obert, i **F5** (una línia) el segueix.
- 🚩 **Les tres portes d'escriptura de la presa** (`onNova`, `onParteix`, `onDesfaInstancia`) i el
  prop `garment` d'`EditableTable` a `CheckMeasureEditor` queden anotats i **no tocats**: fan
  néixer files, i això vol tram i QA propis.

---

# SEGONA PASSADA · Q4-quater · Q5 · Q6

> **Patró A · READ-ONLY**, 16/08 **16:30 → 16:55 UTC**. Branca `dev`, HEAD **`25c306de`**
> (16:14:18 UTC), gunicorn `active (running)` des de **12:23:34 UTC**, `dist` construït
> **16:13:51 UTC**. Cap dels tres commits posteriors a l'arrencada toca un `.py`
> (`git log --since --name-only`): **el backend del disc és el que serveix el gunicorn**.
>
> Passada CONCURRENT amb la que va escriure Q4 (mateix fitxer, mateixa hora). **Q4 no es
> reescriu**: s'hi afegeix només el que la seva secció no cobreix, i que canvia el
> dimensionament de F5. Q5 i Q6 són trams nous.
>
> **La pantalla observada està identificada pel log, no per suposició**
> (`ftt-staging-access.log`): `16:21:44 GET /assets/ModelSheet-BxEg_Gnc.js ref /models/1379` i
> `16:30:57 GET /assets/FittingPrintSheet-CFrMvHG9.js ref /fittings/155/full/1379`. Els **dos
> chunks són els del `dist` d'ara**: el que es va veure és el codi d'ara, no un bundle ranci.

## 🚨 Q4-quater · F5 (una línia) obre un gest DESTRUCTIU que avui no ho és

La secció Q4 llista tres portes d'escriptura que hereten el forat (`onNova`, `onParteix`,
`onDesfaInstancia`) i conclou, correctament, que **avui** no hi ha esborrat silenciós per la via
del payload. **N'hi ha una quarta, i aquesta sí que esborra**: la PODA de fila.

| Baula | Fitxer:línia |
|---|---|
| El botó de la fila | `presaPortes.onTreu` → [CheckMeasureEditor.jsx:690](frontend/src/components/model/CheckMeasureEditor.jsx#L690) |
| El gest | [CheckMeasureEditor.jsx:570-575](frontend/src/components/model/CheckMeasureEditor.jsx#L570-L575) — `models.desactivarPom(model.id, row.pom_id, undefined, { capa: row.capa, instancia: row.instancia })` — **sense `garment`** |
| La vora | [views.py:4963-4966](backend/fhort/models_app/views.py#L4963-L4966) — `capa, instancia, garment = _identitat_de_mesura(request.data)` i `.filter(…, capa=capa, instancia=instancia, garment=garment)` |
| El default | [views.py:3626-3630](backend/fhort/models_app/views.py#L3626-L3630) — «qui no els diu rep el literal de sempre», i el literal de sempre és **la MARE** |

El backend **sí** filtra per `garment`; el client **no** el diu; el default és `''`. O sigui que
una poda demanada des del contenidor Short **desactiva la fila de la MARE del mateix POM**.

**Avui és inofensiu per una sola raó: el contenidor Short està buit.** No hi ha cap fila per
prémer. **F5 omple aquell contenidor amb 7 files i cadascuna estrena el botó de treure.** I la
col·lisió no és teòrica al 1379 — està sembrada a la BD (sonda ORM, tenant `fhort`):

```
(pom 962, capa 'exterior', instancia '')  →  garment ''   bm 3344  nom_fitxa 'G1'
                                             garment '02' bm 3354  nom_fitxa 'M1'
```

Treure la fila **M1** del contenidor Short enviaria `{pom: 962, capa: 'exterior', instancia: ''}`
i el backend desactivaria la **G1 de la mare**. Sense error i sense avís: `desactivar_pom` és
soft (`is_active=False` + registre), i la fila desapareix de la pantalla de l'altra prenda.

> **Conseqüència per al dimensionament: F5 NO és una línia.** És `garment: r.garment` a
> `rowsPresa` **i** `garment: row.garment` a `onPodar` — dues línies, un commit, i el guard de la
> poda al costat del de la lectura. Deixar la segona per a un tram posterior significa publicar
> un botó que esborra la fila equivocada, i el forat trigaria a cantar exactament el mateix que
> ha trigat aquest: fins que algú compti les files de l'altra peça.

---

## Q5 — FULL DE FITTING (PDF/print) · un TERCER punt, independent

### 1 · El generador, citat

| Peça | Fitxer:línia |
|---|---|
| Ruta (FORA del Shell) | [App.jsx:420](frontend/src/App.jsx#L420) — `/fittings/:sessionId/full/:modelId` |
| El generador | [FittingPrintSheet.jsx](frontend/src/pages/FittingPrintSheet.jsx) — pàgina HTML + `@page`, `window.print()` ([:147](frontend/src/pages/FittingPrintSheet.jsx#L147)). **No és Konva/pdf-lib** (això és la fitxa tècnica): el «PDF» el fa la impressora del navegador |
| Les dades | [:53-66](frontend/src/pages/FittingPrintSheet.jsx#L53-L66) — `fittingSessions.get` + `pieceFittings.get(peca.id)` → `PieceFittingGridSerializer` |
| **Les files** | [:87-93](frontend/src/pages/FittingPrintSheet.jsx#L87-L93) |
| La paginació | [:95-98](frontend/src/pages/FittingPrintSheet.jsx#L95-L98) |
| La taula | [:186-245](frontend/src/pages/FittingPrintSheet.jsx#L186-L245) |

**No comparteix res amb Q4**: altre muntatge, altre payload, altre constructor de files. Cap dels
quatre adaptadors del cens hi intervé. És el **tercer punt independent** de la família.

### 2 · Serialitza la llista PLANA — i el punt exacte on hauria d'obrir el contenidor

`grep -c garment FittingPrintSheet.jsx` → **0**. L'eix no hi apareix ni una vegada… excepte
**dins** d'`identitatMesura`, que sí el porta ([identitatMesura.js:36](frontend/src/utils/identitatMesura.js#L36),
quatre trams des de T6b). Per això les 18 files **hi són totes** —la deduplicació no en menja
cap— i totes cauen a la mateixa taula:

```js
const vistes = new Map()
for (const l of (dades.grid?.lines || [])) {
  if (baseLabel && l.size_label !== baseLabel) continue
  const clau = identitatMesura(l)          // ← l'eix ÉS a la clau (dedup correcta)
  if (!vistes.has(clau)) vistes.set(clau, l)
}
const files = [...vistes.values()]         // ← :93 · I AQUÍ ES PERD: llista plana, sense eix
```

**El punt de divergència és [:93](frontend/src/pages/FittingPrintSheet.jsx#L93)**, i el
contenidor Short s'hauria d'obrir **entre :93 i :95** — abans de la paginació, no després:
partir `files` per `garment` en l'ordre de `GET /peces/`, i paginar **dins de cada peça**, perquè
el `#` de fila (`desDe`, [:156](frontend/src/pages/FittingPrintSheet.jsx#L156)) i el
`pagina: n/N` de la capçalera es compten per full i no per prenda.

**La dada hi és a cada línia del payload**, verificat contra la sessió real que es va obrir
(sonda ORM + `PieceFittingGridSerializer` executat tal qual, `PieceFitting 40` · sessió 155 ·
model 1379):

```
90 línies · 18 a la talla base S → garment: {'': 11, '02': 7}
```

`fitting/serializers.py:356` emet `'garment': line.garment` amb l'acta de T6a al costat («servir
l'EIX D'UNA FILA és sempre legítim»). **El full el rep i no el mira.**

### 3 · ¿Comparteix helper amb Q4? **No. Són tres fixos.**

| | Q4 (Taula de mesures) | Q5 (Full de fitting) |
|---|---|---|
| Font | `base-stages` + `taula-mesures` | `piece-fittings/:id` (grid) |
| Constructor | `rowsPresa` (deixa caure l'eix) | `files` (el té a la clau i no el fa servir) |
| Contenidors | `PecesDelModel` ✔ ja muntat | **cap** — el full no demana `/peces/` |
| Fix | l'eix a la fila (+ la poda) | partir la llista i repetir capçalera per peça |

L'únic que compartirien és `filesDeLaPeca`, que no s'ha de tocar. El full, a més, **no pot
muntar `PecesDelModel`**: aquell component pinta `PecaContenidor` amb el crom de pantalla
(targeta, filets, accions) i el paper vol un rètol de secció. El repartiment sí que ha de sortir
del mateix punt únic; **el contenidor, no**.

### 🚨 Q5-bis · DANY VIU AL PAPER: la clau de 3 eixos del serializer col·lapsa les dues prendes

Això no és un contenidor que falta: és **una dada equivocada impresa al full que va al
fabricant**, i és el mateix patró de família una cinquena vegada — **amb escriptura**.

[fitting/serializers.py:302](backend/fhort/fitting/serializers.py#L302) resol la identitat de la
línia amb **tres** eixos, i els quatre mapes de [:288-293](backend/fhort/fitting/serializers.py#L288-L293)
es construeixen amb la mateixa clau curta sobre **tot** el model (`filter(model_id=…)`, sense
partir per prenda):

```python
clau_bm       = (line.pom_id, line.capa, line.instancia)      # ← falta garment
ordre_map     = {(p, c, i): o   for …}
nom_fitxa_map = {(p, c, i): nf  for …}   # el NOM que s'imprimeix
bm_id_map     = {(p, c, i): bid for …}   # ← el DESTÍ D'ESCRIPTURA del bateig
origen_map    = {(p, c, i): og  for …}
```

El comentari de [:270-280](backend/fhort/fitting/serializers.py#L270-L280) explica per què la
capa i la instància hi van entrar («per POM sol, el folre i l'exterior es disputarien el
`nom_fitxa` i —pitjor— el `bm_id`, que és per on aquesta superfície desa el bateig»). **L'argument
és literalment el mateix per al quart eix, i el quart eix no hi és.**

**La prova, no la lectura.** `PieceFittingGridSerializer(PieceFitting 40).data`, files 15 i 16 de
la talla base, tal com surten:

```
15   pom 962  garment '02'  capa exterior  inst ''   nom_fitxa 'M1'   bm_id 3354
16   pom 962  garment ''    capa exterior  inst ''   nom_fitxa 'M1'   bm_id 3354   ← la MARE
```

…quan a la BD la fila de la mare és **`bm 3344`, `nom_fitxa 'G1'`**. Identitat de 4 → 18 files
úniques; identitat de 3 → **17**. Les dues conseqüències:

1. **El paper menteix avui.** La columna CODE del full imprimeix `nom_fitxa || codi`
   ([:221](frontend/src/pages/FittingPrintSheet.jsx#L221)): la fila de la mare surt com a **M1**
   quan la fitxa diu **G1**. El document que es porta a la sala i torna al fabricant porta el nom
   de l'altra prenda.
2. **I hi ha una escriptura al darrere.** `bm_id` és el destí del bateig des de la superfície de
   Fitting (P4). Rebatejar la fila de la MARE escriuria a la `BaseMeasurement` **del Short**. És
   el mateix mode de fallada que F1, a l'altra pantalla, i **travessa la frontera de prenda**.

`ordre_map` i `origen_map` cauen amb la mateixa clau: l'ordre de fitxa i l'etiqueta «DERIVAT»
d'una germana poden acabar a la fila de l'altra peça.

**Al cens Q3 hi era el fitxer, no aquest defecte:** `fitting/serializers.py:264` hi consta com a
consumidor de `_load_grading_rules` (la regla, que és rètol). Això és **una segona cosa al mateix
fitxer**, i és dada d'identitat, no resolució.

### 🚩 Q5-ter · La talla del full és un predicat de MODEL (D5-bis, latent)

[:79](frontend/src/pages/FittingPrintSheet.jsx#L79) pren `baseLabel = model.base_size_label` —**del
MODEL**— i [:89](frontend/src/pages/FittingPrintSheet.jsx#L89) hi filtra totes les línies.
`ModelGarment` té **`base_size_label` i `size_run_model` propis** (camps verificats al model). El
dia que una peça tingui base pròpia, **les seves files no surten al full**: no surten malament,
**desapareixen**, i el paper no diu que hi falti res.

Avui coincideix perquè la 02 del 1379 té `base/run/ruleset = NULL` i hereta. **El joc EFECTIU
existeix i és accessible** (`GET /peces/` → `valor_efectiu`, [garment_views.py:108](backend/fhort/models_app/garment_views.py#L108)),
que és exactament la crida que el full haurà de fer igualment per saber quantes seccions obre:
**la mateixa petició resol el repartiment I la talla de cada secció.**

---

## Q6 — DESBORDAMENT D'IMPRESSIÓ · concern SEPARAT (no barrejar amb Q4/Q5)

### ⚠️ Veredicte honest: **mesurat, i NO es reprodueix** amb el codi d'avui

No s'ha llegit el CSS i deduït: s'ha **mesurat**, amb el pipeline d'impressió real de Chrome
(Playwright + Chromium headless) sobre una **rèplica fidel** del full —el mateix `@page`, el
mateix bloc `@media print`, la mateixa banda escalada, la mateixa taula amb `colgroup` en
percentatges— alimentada amb les **18 files reals** del `PieceFitting 40`. Sondes a
`scratchpad/{full_replica.mjs, mesura_full.mjs, limits.mjs, pdf_full.mjs}` (fora del repo).

```
caixa imprimible A4 apaïsat (297×210, marge 12mm) = 273×186 mm = 1032×703 px
  .ftt-full  amplada 1032 (scrollWidth 1032)     taula 1032 (scrollWidth 1032)
  body.scrollWidth 1032 → DESBORDA AMPLADA: no
PDF real (page.pdf, preferCSSPageSize) → 1 pàgina, 841,92×594,96 pt (A4 apaïsat), res fora del marc
```

I no és qüestió d'orientació ni de paper: `@page { size: A4 landscape }` **mana** —els tres PDFs
(preferCSSPageSize, `format:'A4'` vertical i apaïsat) surten tots apaïsats— i a Letter apaïsat
(965 px) i fins i tot a A4 VERTICAL (703 px) els blocs segueixen sense desbordar, perquè
`.ftt-full` va a `width:100%` i les columnes són **percentatges** (la lliçó ja escrita a
[:181-185](frontend/src/pages/FittingPrintSheet.jsx#L181-L185) és correcta i funciona).

**Cal saber què es mirava**, perquè les tres causes possibles tenen fixos diferents:
🔵 el **paper imprès**, 🔵 la **previsualització** de Chrome, o 🔵 **la pàgina a pantalla**. La
tercera és la que sí que es retalla, i és la hipòtesi més probable: v. (c).

### El que SÍ que està trencat, amidat

**(a) Vertical — el marge és ZERO i el retall és MUT.** `.ftt-full` fa `height: 184mm` dins d'una
caixa de 186 mm i porta `overflow: hidden`
([:136-140](frontend/src/pages/FittingPrintSheet.jsx#L136-L140)):

```
18 files reals (una amb nom de 2 línies) → contingut 695 px de 695 px disponibles → 0 px de marge
18 files amb nom de 2 línies             → 725 px → ⛔ 22 px FORA → llegenda i signatura RETALLADES
```

El comentari de [:25-28](frontend/src/pages/FittingPrintSheet.jsx#L25-L28) diu que
`FILES_PER_PAGINA = 18` és «un límit CONSERVADOR a posta» i que «una pàgina sencera de noms de
dues línies encara hi cap sense trepitjar el peu». **Mesurat: és fals.** I com que el retall és
`overflow: hidden`, el full surt de la impressora **sense la llegenda AC/AD/RJ i sense la
signatura**, que és justament el que fa el document utilitzable, i **res no ho anuncia**.

**(b) Amplada — l'únic element NO fluid és la BANDA.** `FttHeaderBand` escala amb
`escala = amplada / natW` ([FttHeaderBand.jsx:39](frontend/src/components/model/FttHeaderBand.jsx#L39)),
i `amplada` és `A4_W - MARGE*2` = **1033 px cuits a mà** ([FittingPrintSheet.jsx:166](frontend/src/pages/FittingPrintSheet.jsx#L166)),
una constant de PANTALLA — no l'amplada real del contenidor. El `maxWidth:'100%'`
([:46](frontend/src/components/model/FttHeaderBand.jsx#L46)) salva la caixa, però **no reescala el
contingut**: el que sobra es retalla.

```
caixa de pàgina 273,0 mm → contenidor 1032 px · banda dibuixada 1033 px → ok (per 1 px)
caixa de pàgina 255,4 mm → contenidor  965 px · banda dibuixada 1033 px → ⛔ 68 px retallats
caixa de pàgina 186,0 mm → contenidor  703 px · banda dibuixada 1033 px → ⛔ 330 px retallats
```

A A4 apaïsat coincideix **per construcció** (1033 ≈ 1032) i per això no canta. Qualsevol caixa
més estreta —marges més grans, paper Letter, una impressora amb àrea imprimible menor— es menja
la dreta de la banda, que és on viuen **la data i el `pàgina n/N`**. La capçalera és disseny
aprovat amb caixa intocable: **no es pot estirar, però sí que s'ha d'escalar contra l'amplada
REAL**, que és precisament el que el fitxer diu que fa i no fa.

**(c) A pantalla no hi ha cap escalat.** `.ftt-full` és **1123 px durs**
([:169](frontend/src/pages/FittingPrintSheet.jsx#L169)) i el `.ftt-wrap` no té ni `overflow-x`
ni `zoom`: amb una finestra de menys de 1123 px, **el paper es talla per la dreta a la pantalla**
—i el que es veu tallat és la columna COMMENTS i la vora dreta de la banda—, exactament el
símptoma descrit, sense que la impressió tingui cap problema. El log no registra el viewport, i
per això això és **hipòtesi**, no veredicte.

### Fix dimensionat — **commit PROPI, no barrejat amb Q4/Q5**

**F8 · El full no es retalla — S (≈1-2 h) · 1 commit, i que no toqui ni una fila de dades.**

1. **La banda escala contra el contenidor real**: `FttHeaderBand` deixa de rebre `amplada` en px
   i s'escala amb l'amplada mesurada (`ResizeObserver` o `width:100%` + `aspect-ratio` sobre el
   bloc transformat). Toca **un sol fitxer** i el consumidor. ⚠️ `FttHeaderBand` també el fa
   servir la fitxa; el canvi ha de ser additiu (si arriba `amplada`, mana; si no, mesura).
2. **El peu deixa de poder-se retallar**: `.ftt-full` passa a `min-height: 184mm` amb
   `overflow: visible` i `page-break-inside: avoid` per fila, o `FILES_PER_PAGINA` es calcula en
   comptes de declarar-se. La primera és menys codi i respecta la promesa «un div = una pàgina»
   només si les files hi caben; la segona la manté sempre. **Decisió de domini** (què val més: no
   partir mai una pàgina, o no perdre mai la signatura) — **d'Agus, no de l'agent**.
3. **A pantalla, el full s'ajusta a la finestra** amb un `transform: scale()` de
   previsualització (o `zoom`), sense tocar el render d'impressió.

**Res d'això toca `garment`**, i cap dels tres punts entra al mateix commit que F5/F6/F7.

---

## Propostes NOVES d'aquesta passada (res implementat)

| # | Què | Mida | Commits | Depèn de |
|---|---|---|---|---|
| **F5+** | **Q4 amb la poda inclosa**: `garment: r.garment` a `rowsPresa` **i** `garment: row.garment` a `onPodar` ([:574](frontend/src/components/model/CheckMeasureEditor.jsx#L574)) → el cos ja el sap llegir (`_identitat_de_mesura`) | **XS** (≈30 min) | 1 | — |
| **F6** | **El full de fitting reparteix**: `GET /peces/` al full, partir `files` per `garment` a [:93](frontend/src/pages/FittingPrintSheet.jsx#L93), una **secció per prenda** amb rètol i numeració pròpia, i paginar dins de cada secció | **M** (≈3-4 h) | 1 | — |
| **F7** | **La identitat del grid de fitting creix a 4 eixos**: `clau_bm` + els quatre mapes de [serializers.py:288-302](backend/fhort/fitting/serializers.py#L288-L302). Tanca el nom fals al paper **i** l'escriptura del bateig fora de la seva prenda | **M** (≈3-4 h) | 1 | — |
| **F8** | **Q6 · el full no es retalla** (banda + peu + pantalla) | **S** (≈1-2 h) | 1 | cap · **no barrejar** |

**Ordre recomanat: F7 → F6.** F7 és dany viu sobre un document que ja s'imprimeix; F6 és una
absència. Fer F6 primer deixaria el full repartit **amb el nom equivocat a la fila de la mare**,
que és pitjor que un full sense repartir: dos blocs ben separats donen més confiança a una dada
que continua sent falsa.

## Guards NOUS (v. la llei de dalt: VERMELL amb el 1379, VERD amb el control d'una peça)

| # | Guard | On | Vermell AVUI amb… | Control una-peça |
|---|---|---|---|---|
| **G9** | **La poda diu de quina prenda és la fila** | test de `desactivar_pom_view` | cos `{pom: 962, capa:'exterior', instancia:''}` **sense** `garment` mentre s'edita la 02 → avui desactiva `bm 3344` (la MARE); després, `bm 3354` | model d'una peça → `garment=''`, exactament la fila d'ara |
| **G10** | **El full de fitting reparteix** | `frontend/src/utils/*.test.js` sobre una funció pura `partirPerPeca(files, peces)` extreta del full (no és testable dins del `.jsx`) | les 18 línies reals del `PieceFitting 40` → **11 + 7** en dues seccions; avui **18 + cap secció** | `peces=[mare]` (o `/peces/` sense contestar) → **una** secció amb les 18 i la numeració byte a byte com ara |
| **G11** | **El grid de fitting no col·lapsa prendes** | `backend/fhort/fitting/test_*.py` | `PieceFittingGridSerializer(pf 40)`: les files del POM **962** han de portar `bm_id` **3344** i **3354** i `nom_fitxa` **'G1'** i **'M1'**. Avui les dues porten **3354 / 'M1'** | model d'una peça → payload idèntic camp a camp |
| **G12** | **La talla del full és l'EFECTIVA de la peça** | test sobre el full (funció pura de selecció) | ⚠️ **cal SEMBRAR la divergència**: `ModelGarment('02').base_size_label = 'M'` → les seves 7 files han de sortir a la seva secció. Sense sembrar-la el guard és **cec**, com G5 | la 02 sense base pròpia → hereta la del model i no canvia res |
| **G13** | **El peu del full no es retalla** (Q6, no és de `garment`) | mesura amb el Chromium que ja hi ha, o assert d'alçada sobre la funció que decideix `FILES_PER_PAGINA` | 18 files amb nom de 2 línies → **725 px** en una caixa de **695 px**: la llegenda i la signatura desapareixen | 18 files d'una línia → cap canvi de sortida |

**El parany de sempre, dit una vegada més:** G11 és l'únic guard d'aquesta llista que ja és
vermell **sense sembrar res**, perquè el 962 viu a les dues prendes de debò. G12 no ho és, i un
guard que només comprovi «surten 18 files» hi passarà en verd amb el codi trencat.

## Fronteres respectades en aquesta passada

Cap escriptura a BD (només `schema_context('fhort')` + lectures d'ORM i un serializer executat en
memòria), cap fitxer del repo modificat fora d'aquest document, cap commit, cap push. No s'ha
tocat motor, ni G6/segell, ni billing, ni la màquina d'estats de tasques, ni l'escriptura de
l'Escalat (F1). **No s'ha fet login a staging a posta**: autenticar-se escriuria `last_login`, i
per això Q6 s'ha mesurat amb una rèplica fidel i no amb la pàgina en viu. Sondes a
`scratchpad/{q45_probe.py, q5_grid.py, full_replica.mjs, mesura_full.mjs, limits.mjs,
pdf_full.mjs}` — fora del repo.

---

# Q8 · FITXA TÈCNICA — una taula per peça, cada una a la seva pàgina

> **Patró A · READ-ONLY**, 16/08 **16:58 → 17:20 UTC**. Branca `dev`, HEAD **`4591a7c9`**
> («Taula de mesures reparteix files per garment», 16:48:47 — **F5 ja entrat**), gunicorn
> `active` des de **12:23:34 UTC**, `dist` construït **16:48:16 UTC**.
> Fronteres: no s'ha tocat canvas/Konva, ni el pipeline PDF, ni `TechSheetEditor.jsx`. Només
> lectura, sondes `GET`/ORM i aquest document.
>
> ⚠️ **L'ESTAT DEL 1379 HA CANVIAT DES DE LA PRIMERA PASSADA D'AVUI.** `grading-status` diu ara
> `te_taula: true`, `te_propagacio: true`, `version_number: 1`, i `SizeFitting 366` porta
> `GradingVersion 122` activa amb **90 `GradedSpec`**. La lectura de Q2 (`te_taula: false`, zero
> `GradedSpec`) era certa a les 15:30 i **ja no ho és**: algú ha propagat entremig. Això importa
> aquí perquè **decideix quines taules són oferibles** a la fitxa (v. §2).

## 🔑 Correcció de premissa — **el repartiment per peça JA EXISTEIX a la fitxa**

El brief diu que «la fitxa tècnica MAI ha imprès multipeça i el repartiment per garment no
existeix». **Mesurat contra el codi: no és així**, i val més dir-ho abans de dimensionar res —
la llei de la casa és comprovar què ja s'ha CONSTRUÏT abans de dir que no hi és.

SET-2/T9 (10/08) ja va construir tot un eix de peça per a la fitxa:

| Peça construïda | On |
|---|---|
| El punt únic de l'eix | [utils/garmentFitxa.js](frontend/src/utils/garmentFitxa.js) — `GARMENT_MARE`, `garmentIdDe`, `garmentDeFila`, `agrupaPerGarment`, `calArbrePerGarment`, `garmentComu`, **`partirTaules`** |
| L'eix a cada objecte del `.ftt` | [TechSheetEditor.jsx:449](frontend/src/pages/TechSheetEditor.jsx#L449) — `garmentId: garmentId ?? GARMENT_MARE`, amb round-trip provat (`test_ftt_garment_roundtrip.py`) |
| La casella «partir per prenda» | [:7285-7295](frontend/src/pages/TechSheetEditor.jsx#L7285-L7295) — es pinta **només** si el model té més d'una peça |
| La llista de peces del model | [:5569](frontend/src/pages/TechSheetEditor.jsx#L5569) — `pecesDelModel` |
| L'arbre per peça del panell de POMs | [:7110-7115](frontend/src/pages/TechSheetEditor.jsx#L7110-L7115) |
| **Dues taules ja parteixen** | T1a [:5129-5132](frontend/src/pages/TechSheetEditor.jsx#L5129-L5132) i T1b [:5191](frontend/src/pages/TechSheetEditor.jsx#L5191) — `partirEnTaules(...)` + `garmentId: g.garment` |

I **al 1379 això ja està VIU avui**: `base-measurements/` serveix l'eix (sonda: **11 `''` + 7
`'02'`**), o sigui que `pecesDelModel` val `['02']`, **la casella es pinta** i inserir la T1a amb
la casella marcada ja produeix **DUES taules** amb les files ben repartides.

**El que NO existeix és el que Agus demana literalment: la PÀGINA.** Les N taules neixen totes a
la **mateixa** pàgina, desplaçades uns mil·límetres l'una de l'altra
([`escalonat`, :4994](frontend/src/pages/TechSheetEditor.jsx#L4994): «prou poc per no sortir de la
pàgina amb 3-4 peces»). Q8, doncs, no és «construir el repartiment»: és **portar el repartiment
que ja hi és a la paginació**, i **fer-hi entrar les dues taules que se n'han quedat fora**.

## 1 · Motor i estructura de paginació

**El motor, net: Konva per al llenç + pdf-lib per a l'export.** No és HTML+`@page` (això és el
full de fitting, Q5), no és reportlab, i no és una barreja: són dues meitats d'un sol camí.

| Fet | Fitxer:línia |
|---|---|
| Llenç | [TechSheetEditor.jsx:8-9](frontend/src/pages/TechSheetEditor.jsx#L8-L9) — `react-konva` + `konva` |
| Export | [:10](frontend/src/pages/TechSheetEditor.jsx#L10) `import { PDFDocument } from 'pdf-lib'` · [:5434-5444](frontend/src/pages/TechSheetEditor.jsx#L5434-L5444) `onExport` |
| **La pàgina és de primera classe** | [:2683](frontend/src/pages/TechSheetEditor.jsx#L2683) — `const [pages, setPages] = useState([{ id: uid(), objects: [] }])` |
| **El salt de pàgina** | **No hi ha flux ni tall automàtic**: el salt ÉS l'array. `onExport` fa `for (let pi = 0; pi < pages.length; pi++)` → **una pàgina d'editor = una pàgina de PDF**, amb la seva mida (F4, formats mixtos) |
| Crear pàgina | [:5371-5387](frontend/src/pages/TechSheetEditor.jsx#L5371-L5387) `addPage()` — neix amb una còpia de la capçalera mestra i hereta el format de la pàgina activa |
| Escriure a UNA pàgina | [:2852-2858](frontend/src/pages/TechSheetEditor.jsx#L2852-L2858) — `updatePageObjects(pi, updater)` **ja rep l'índex**; `addObject` només és aquell amb `currentPage` clavat |

**Una fitxa nova neix amb UNA pàgina i només la capçalera**
([backend/…/master_template.py:56](backend/fhort/models_app/master_template.py#L56)): les taules
no les «genera» ningú, **les insereix el tècnic** des de la llibreria. «Generar una taula per
peça» vol dir, exactament: *el gest d'inserir en produeix N i les reparteix per pàgines*.

## 2 · D'on surten les files — les sis variants

| Variant | `kind` | Builder | Font | ¿Parteix per peça? |
|---|---|---|---|---|
| T0 · Mesures talla base | `base_measures` | [:5023-5074](frontend/src/pages/TechSheetEditor.jsx#L5023-L5074) | `base-measurements/` | **NO** — `rows = bms.map(…)` sobre TOTES i `garmentId: GARMENT_MARE` clavat ([:5066](frontend/src/pages/TechSheetEditor.jsx#L5066)) |
| T1a · Fitxa de fitting | `pom_fitting` | [:5086-5141](frontend/src/pages/TechSheetEditor.jsx#L5086-L5141) | `base-measurements/` | **SÍ** ([:5129](frontend/src/pages/TechSheetEditor.jsx#L5129)) |
| T1b · Grading final | `pom_grading` | [:5148-5216](frontend/src/pages/TechSheetEditor.jsx#L5148-L5216) | `fitting/<sf>/graded-table/` | **SÍ** ([:5191](frontend/src/pages/TechSheetEditor.jsx#L5191)) |
| T3 · Repàs de fittings | `fitting_history` | [:5216-5271](frontend/src/pages/TechSheetEditor.jsx#L5216-L5271) | `fitting/model/<id>/repas/` | **NO** — `GARMENT_MARE` clavat ([:5263](frontend/src/pages/TechSheetEditor.jsx#L5263)) |
| T2 · BOM | `bom` | [:5274](frontend/src/pages/TechSheetEditor.jsx#L5274) | cap (buida) | n/a — legítim |
| Personalitzada | `custom` | [:5295](frontend/src/pages/TechSheetEditor.jsx#L5295) | cap | n/a — legítim |

**Les TRES fonts porten l'eix per fila. Verificat en viu, no llegit:**

```
base-measurements/ 1379 → 18 files · garment: {'': 11, '02': 7}   ← camp 'garment' al payload
graded-table/ sf=366   → 18 files · garment: {'': 11, '02': 7}   ← 18, no 17: NO col·lapsa
repas/                 → clau de QUATRE eixos (repas_views.py:201, :231)
```

⚠️ **Dos comentaris del codi diuen el contrari i són FALSOS**, amb data pròpia:
[:4981-4983](frontend/src/pages/TechSheetEditor.jsx#L4981-L4983) («les seves files vénen de
`graded-table/`, que encara NO serveix la peça») i
[:5561-5566](frontend/src/pages/TechSheetEditor.jsx#L5561-L5566) («el payload de
`base-measurements/` encara NO serveix l'eix… `grep class ModelGarment` avui: 0 resultats»).
Els dos són del 10/08, els dos demanen re-verificació, i **la re-verificació ja està feta: les
dues afirmacions han caigut**. Igual que `garmentFitxa.js:11-15` i `:37-40` (que ja constaven al
cens Q3 com a candidat #2). Una afirmació d'estat datada i falsa dins d'un docstring és pitjor
que cap afirmació: la propera sessió s'hi refia, i **aquest brief ja s'hi ha refiat**.

**¿Cal importar `filesDeLaPeca`? NO, i no s'hauria de fer.** Aquest camí té el seu punt únic
propi —`agrupaPerGarment`/`partirTaules`, amb proves— i fa una cosa diferent: `filesDeLaPeca`
FILTRA per un eix conegut (una pantalla amb contenidors), i `partirTaules` **PARTEIX** una llista
en N grups (un document que no sap quantes peces hi haurà). Són dues formes de la mateixa llei i
tenen dos consumidors distints; unificar-les no és feina de Q8.

## 3 · Què caldria construir — dimensionat

### (a) Que T0 i T3 entrin a la partició — **XS (≈30 min cadascuna)** · 1 commit

Les dues tenen `partirEnTaules` i `inserirTaules` a **tres metres** (mateix component, mateix
scope) i les dues fonts ja porten l'eix. És substituir el `addObject(fitTableObj({…}))` d'un sol
objecte pel `inserirTaules(partirEnTaules(files), g => ({… garmentId: g.garment …}))` que la T1a
ja fa. **Cap contracte, cap endpoint, cap fitxer nou.**

> **T0 és, quasi segur, la taula que Agus vol** («taula de mesures», 11 files skirt + 7 Short):
> és la que es diu «Mesures talla base» a la llibreria i la que porta POM + nomenclatura + mida.

### (b) Cada taula a la SEVA pàgina — **S (≈2-4 h)** · 1 commit

La maquinària hi és tota i **no cal tocar ni Konva ni pdf-lib**: és composició d'estat.

- `updatePageObjects(pi, …)` [:2852](frontend/src/pages/TechSheetEditor.jsx#L2852) **ja accepta
  l'índex de pàgina**; l'únic que hi ha clavat a `currentPage` és `addObject`.
- `addPage()` [:5371](frontend/src/pages/TechSheetEditor.jsx#L5371) ja resol el que és delicat:
  copiar la capçalera mestra i heretar el format.
- El cost real és **un sol `setPages` per al gest sencer**: N-1 pàgines noves + el seu objecte,
  en una sola mutació. Cridar `addPage()` en bucle llegiria `pages` ranci i, sobretot, deixaria
  **N passos d'undo** per a un sol gest (la història penja de `pages`,
  [:2887](frontend/src/pages/TechSheetEditor.jsx#L2887)).
- L'`escalonat` [:4994](frontend/src/pages/TechSheetEditor.jsx#L4994) es queda **per a l'eix de
  SECCIÓ** (diverses seccions d'una mateixa peça segueixen a la mateixa pàgina); el que canvia
  d'alçada és només l'eix de prenda.

🛑 **Decisió que NO és de l'agent:** ¿partir per peça implica SEMPRE pàgina nova, o són dues
caselles («una taula per peça» / «cada peça a la seva pàgina»)? Hi ha argument per a les dues i
és criteri de producte. Proposta per si serveix: **una sola casella**, perquè dues taules
esglaonades a la mateixa pàgina no és el que ningú demana quan marca «per peça».

### (c) Quins garments són «disponibles» — **ja resolt, res a construir**

[:5567-5569](frontend/src/pages/TechSheetEditor.jsx#L5567-L5569):

```js
const grupsPom      = agrupaPerGarment(pomRows)          // pomRows = base-measurements/
const pecesDelModel = grupsPom.map(g => g.garment).filter(g => g !== GARMENT_MARE)
```

És exactament el criteri del brief: **garments amb files VIVES al model**, derivats de les
mesures, **no del catàleg** (`GarmentTypeItem`) ni de `ModelGarment`. Al 1379 dona `['02']`.
⚠️ Únic matís: com que surt de `pomRows`, una peça que existís a `ModelGarment` **sense cap
mesura** no apareixeria — i això és el comportament CORRECTE per a una taula de mesures (una
pàgina de mesures buida no és una pàgina).

### (d) Herència D5-bis — on mossega i on no

- **Les XIFRES estan bé.** Els valors graduats surten de `GradedSpec`, que el motor calcula per
  peça amb `_regla_de`; `graded-table/` les serveix sense col·lapsar (18 files, verificat). La
  pàgina del Short imprimiria els seus números.
- **La REGLA servida és la de la mare** — `_load_grading_rules(model)` a
  [graded_spec_views.py:170](backend/fhort/fitting/graded_spec_views.py#L170), el 2n dels cinc
  consumidors del cens Q3. És el Q1-bis d'aquest document. **Però avui és LATENT a la fitxa**:
  la T1a va perdre les columnes Regla/Δ/Break el 31/07 i la T1b també, o sigui que **cap columna
  impresa llegeix aquests camps**. Ho hereta el dia que algú en torni a pintar una.
- **On sí que mossegarà de debò: la CAPÇALERA.** El `run` i la `talla base` de la banda surten
  del MODEL ([:5038](frontend/src/pages/TechSheetEditor.jsx#L5038) i la resolució de camps de
  `HDR_H_V3`), i `ModelGarment` té `size_run_model` i `base_size_label` **propis**. Una pàgina de
  peça amb el run del model seria una capçalera que menteix. La font correcta ja existeix i és la
  mateixa que necessita el §4: `GET /peces/` → `valor_efectiu`
  ([garment_views.py:108](backend/fhort/models_app/garment_views.py#L108)).

## 4 · Capçal i identitat de cada pàgina

- **Què hi ha avui:** cada pàgina porta la banda mestra (`masterHeaderInstance`
  [:5365](frontend/src/pages/TechSheetEditor.jsx#L5365), copiada per `addPage`). La spec
  `HDR_H_V3` **no té cap camp de peça** — és un disseny aprovat amb acta i caixa intocable.
- **Per tant, dir «Short» a la pàgina són dues opcions i cap és de l'agent:** (i) un camp nou a
  la spec de capçalera (toca `docs/spec/capcalera_ftt_v3.md` i les DUES bandes, Konva i HTML), o
  (ii) un objecte de text que el gest insereix damunt de la taula. **Les taules d'aquesta casa no
  tenen títol** per decisió explícita ([:5012-5017](frontend/src/pages/TechSheetEditor.jsx#L5012-L5017)):
  afegir-n'hi un canviaria el render de **totes** les variants, i això és molt més que Q8.
- **D'on surt el NOM:** avui la fitxa només sap el **codi** (`'02'`), perquè `pecesDelModel` el
  treu de les files. El nom «Short» és `ModelGarment.nom` i el serveix `GET /peces/` — **una
  crida que aquesta pantalla no fa**. És la mateixa que resol l'herència del §3(d): **una
  petició tanca el nom I la talla efectiva**. Les claus i18n que hi ha
  ([:7113-7115](frontend/src/pages/TechSheetEditor.jsx#L7113-L7115)) etiqueten l'arbre amb el
  CODI (`tech_sheet.garment_codi`), no amb el nom.

### ✅ La ferida de Q7 **NO es comparteix** — verificat executant els serializers reals

La fitxa **no passa per `PieceFittingGridSerializer`**. Les seves fonts resolen la fila per la
seva pròpia identitat i el POM 962 —la frontera que creua el full de fitting— surt **correcte a
les dues**:

```
base-measurements/ · POM 962 → garment ''   id 3344  nom_fitxa 'G1'
                              garment '02'  id 3354  nom_fitxa 'M1'     ← cada peça, la seva
graded-table/      · POM 962 → garment ''   ref 'G1'
                              garment '02'  ref 'M1'                    ← cada peça, la seva
```

**Q8 NO depèn de F7.** F7 (la clau de 4 eixos del grid de fitting) tanca el full de fitting i la
pantalla de Fitting; la fitxa tècnica ja hi arriba neta per un altre camí. Els dos trams es poden
fer en qualsevol ordre i no es toquen.

## 5 · Cens de la família en aquest camí

| # | Fitxer:línia | Context |
|---|---|---|
| 1 | [TechSheetEditor.jsx:5057-5066](frontend/src/pages/TechSheetEditor.jsx#L5057-L5066) | **T0**: `rows = bms.map(…)` sobre totes les mesures + `garmentId: GARMENT_MARE` clavat. Ja era el candidat **#1 del cens Q3**; segueix obert |
| 2 | [TechSheetEditor.jsx:5252-5263](frontend/src/pages/TechSheetEditor.jsx#L5252-L5263) | **T3**: `rows = (data.rows \|\| []).map(…)` + `GARMENT_MARE` clavat, quan `repas/` indexa per QUATRE eixos. **Nou al cens** |
| 3 | [garmentFitxa.js:11-15](frontend/src/utils/garmentFitxa.js#L11-L15) i [:37-40](frontend/src/utils/garmentFitxa.js#L37-L40) | Afirmacions d'estat datades **i falses** («cap peça 02 a cap dada real», «AVUI CAP PAYLOAD LA SERVEIX»). Candidat **#2 del cens Q3**, ara amb dues proves més en contra |
| 4 | [TechSheetEditor.jsx:4976-4983](frontend/src/pages/TechSheetEditor.jsx#L4976-L4983) | «inert sobre el corpus actual» + «`graded-table/` encara NO serveix la peça» — **falses totes dues**. Nou |
| 5 | [TechSheetEditor.jsx:5561-5566](frontend/src/pages/TechSheetEditor.jsx#L5561-L5566) | «avui això dona SEMPRE una sola branca» + «`grep class ModelGarment` → 0 resultats» — **falses**. Nou |
| 6 | [TechSheetEditor.jsx:5038](frontend/src/pages/TechSheetEditor.jsx#L5038) + capçalera | La talla base i el run de la pàgina són **del MODEL**; `ModelGarment` en té de propis. Latent fins que una peça n'assigni |
| 7 | [graded_spec_views.py:170](backend/fhort/fitting/graded_spec_views.py#L170) | `_load_grading_rules(model)` — la regla de la mare a totes les files. Ja al cens Q3 (backend); **latent a la fitxa** perquè cap columna impresa la llegeix |

## Guards que caldrien al Patró B (cap escrit — Patró A)

| # | Guard | On | Vermell AVUI amb el 1379 | Control una-peça |
|---|---|---|---|---|
| **G14** | **T0 i T3 parteixen per peça** | `frontend/src/utils/*.test.js` sobre `partirTaules` amb les files reals (la llei ja hi és i té banc; el que falta és que la variant la cridi) | les 18 files de `base-measurements/` → **2 grups: 11 + 7**. Avui: **1 grup de 18** | model sense `'02'` → **1** grup amb totes, objecte idèntic al d'ara (`garmentId: ''`) |
| **G15** | **Una peça, una pàgina** | test de la funció pura que composa l'estat (`pages` d'entrada + grups → `pages` de sortida), **no del component** | 2 grups → **2 pàgines amb 1 taula cadascuna** i la capçalera mestra a totes dues. Avui: **1 pàgina amb 2 taules esglaonades** | 1 grup → **1 pàgina**, `pages` byte a byte com abans (cap pàgina nova, cap `format` nou) |
| **G16** | **La pàgina diu el NOM de la peça, no el codi** | test de la funció que resol l'etiqueta | peça `'02'` → **«Short»** (de `GET /peces/`), no «Peça 02» ni `'02'` | la mare → l'etiqueta d'ara, i sense la crida el gest ha de degradar al codi, mai a buit |
| **G17** | 🚨 **ROUND-TRIP: les pàgines noves sobreviuen a desar i reobrir** | `backend/…/test_ftt_*_roundtrip.py`, patró de `test_ftt_garment_roundtrip.py` | desar amb 2 pàgines → reobrir → **2 pàgines i els 2 objectes amb el seu `garmentId`** | 1 pàgina → document idèntic |

🚨 **El parany d'implementació de Q8, escrit abans que passi.** `hidratarPagines`
([paginesFtt.js:18-24](frontend/src/utils/paginesFtt.js#L18-L24)) **reconstrueix cada pàgina camp
a camp** (`id`, `objects`, `guides`, `format`), i el seu propi capçal ho diu: *«cada cop que se
n'ha escrit una de nova, la clau nova s'hi ha perdut en silenci»*. L'OBJECTE, en canvi, fa
round-trip **opac** (`base = obj`). Per això T9 va decidir que **l'eix viu a l'objecte i MAI a la
pàgina** ([garmentFitxa.js:17-21](frontend/src/utils/garmentFitxa.js#L17-L21)). Q8 ha d'obeir la
mateixa llei: **la pàgina no ha de guanyar cap camp `garment`** — qui diu de quina peça és una
pàgina és la taula que hi viu. Si el Patró B hi escriu un camp de pàgina, es perdrà en reobrir i
el símptoma serà «les pàgines hi són però han perdut la peça», que és exactament la mena de bug
mut que aquest document persegueix des de Q1.

## Dimensionament total de Q8

| Peça | Mida | Commits | Depèn de |
|---|---|---|---|
| (a) T0 + T3 entren a la partició | **XS** ×2 | 1 | — |
| (b) Una peça, una pàgina | **S** (2-4 h) | 1 | (a) per veure'n l'efecte a T0 |
| (c) `GET /peces/` per al nom i la talla efectiva | **XS** | dins de (b) | — |
| (d) Netejar les 4 afirmacions datades i falses | **XS** | amb qualsevol dels de dalt | — |

**Total: S-M, i cap dependència amb F7 ni amb F1.** No toca motor, ni Konva, ni pdf-lib, ni el
contracte del `.ftt`. La part caríssima —l'eix a l'objecte, la llei de partir, el round-trip
provat, la pàgina com a unitat d'export— **ja està pagada des del 10/08**.

**Sondes d'aquesta secció** (fora del repo): `scratchpad/{q8_probe.py, q8_probe2.py, q8_estat.py}`.

---

## Q9 · FULL DE FITTING — capçalera repetida (thead) · x/N · fila-títol per peça · 15 mm · logo

> **Patró A · READ-ONLY.** Cap escriptura a BD, cap fitxer del repo tocat excepte aquest, cap
> commit, cap push. El disseny d'avui (Patró C, 17/08) **substitueix** el pla de Q5/Q6: el que
> segueix mesura si el camí que l'Agus proposa és el mínim, i amb quins números reals.
>
> **Res del que hi ha aquí és deduït del CSS: està mesurat** amb el pipeline d'impressió real
> (Chromium `--print-to-pdf` + `pdftotext -bbox` per llegir les coordenades del PDF, i el MATEIX
> binari via Playwright per als rects del layout). Sondes fora del repo:
> `scratchpad/{replica_q9.html, replica_q9b.html, replica_1379.html, replica_ungrup.html,
> replica_real_15mm.html, mesura.mjs, mesura2.mjs}`.

### Capçal — estat verificat abans de res

| Què | Valor | Com s'ha llegit |
|---|---|---|
| Branca | `dev` | `git branch --show-current` |
| HEAD | `3deda69c` (F5-bis) · F7 = `acfc3f24` · 2026-08-16 **17:45:52 UTC** | `git log -1 --format=%cd` |
| `ftt-staging` (gunicorn) | `active (running)` des de 2026-08-16 **18:10:56 UTC** | `systemctl show -p ActiveEnterTimestamp` |
| **F7 desplegat?** | ✅ **SÍ** — el commit és de les 17:45:52 i el procés va arrencar a les 18:10:56 | la llei [`ftt-backend-desplegat-vs-disc`] aplicada, no suposada |
| Payload real | `PieceFitting 40` · sessió 155 · model 1379 · talla base `S` → **18 files: 11 mare + 7 `'02'`**, cadascuna amb el SEU `nom_fitxa` i `bm_id` | `PieceFittingGridSerializer` executat tal qual dins del tenant |

---

### 1 · CAPÇALERA: ¿thead o div? — i el veredicte del x/N per superfície

#### 1.1 · Avui és un DIV FORA de la taula

[FittingPrintSheet.jsx:175](frontend/src/pages/FittingPrintSheet.jsx#L175) —
`<FttHeaderBand amplada={ampladaUtil} …/>` és **germà** de la taula, dins del `div.ftt-full`
([:168-174](frontend/src/pages/FittingPrintSheet.jsx#L168-L174)). El `<thead>` que la taula sí
que té ([:199-212](frontend/src/pages/FittingPrintSheet.jsx#L199-L212)) porta **només els vuit
títols de columna**, no la banda.

Avui la banda es repeteix igualment, però **per un altre mecanisme**: el JS parteix les files en
pàgines ([:95-98](frontend/src/pages/FittingPrintSheet.jsx#L95-L98)) i pinta **un `.ftt-full`
sencer per pàgina** ([:155-160](frontend/src/pages/FittingPrintSheet.jsx#L155-L160)), separats
amb `page-break-before: always` ([:141](frontend/src/pages/FittingPrintSheet.jsx#L141)). Cada
div torna a dibuixar la seva capçalera. **R2 = moure-la al `thead`** si es vol la repetició
gratuïta del navegador.

#### 1.2 · El `thead` FUNCIONA — mesurat, 4 pàgines reals

Rèplica amb la banda dins d'un `<th colspan="8">` del `thead`, 60 files, `@page margin: 15mm`:

```
Pages: 4
P1  RUFFLES y=52.98   LAYER/CODE y=114.53   fila #1 y=146.61   ← «Base model» (fila-títol) y=132.36
P2  RUFFLES y=52.98   LAYER/CODE y=114.53   fila #20 y=134.61  ← CAP fila-títol repetida
P3  RUFFLES y=52.98   LAYER/CODE y=114.53   fila #39 y=134.61  ← CAP fila-títol repetida
```

Les tres coses que calia provar, provades alhora: **la banda es repeteix idèntica** (mateixa `y`
al pt), **el tbody arrenca a la mateixa alçada a cada pàgina**, i **la fila-títol NO es repeteix**
—surt un cop, on cau al flux—, que és exactament el repartiment que R1 i R2 demanen. El camí és
el mínim: no cal cap càlcul de paginació per a la repetició.

#### 1.3 · 🚨 EL x/N NO SURT DEL `thead`. Tres mecanismes provats, tres fallats

| Mecanisme | Resultat mesurat |
|---|---|
| `@page { @bottom-right { content: counter(page) "/" counter(pages) } }` | **no s'imprimeix res** — Chrome ignora els *margin boxes* de CSS Paged Media |
| `counter(page)`/`counter(pages)` dins del `thead` | s'imprimeix **`THEAD 0/0`** a les 3 pàgines |
| `counter(page)` en un element `position: fixed` | l'element **sí que es repeteix** a totes les pàgines, però imprimeix **`FIXED 0/0`** |

Els comptadors de pàgina de CSS **només els resol un motor de paginació de debò** (Prince,
WeasyPrint). Chrome els deixa a zero fora dels *margin boxes*, i els *margin boxes* no els pinta.
El full **no passa per cap generador de PDF propi** —el «PDF» el fa la impressora del navegador
([:147](frontend/src/pages/FittingPrintSheet.jsx#L147))—, o sigui que no hi ha cap tercera
superfície on el comptador pugui néixer.

**Veredicte per superfície:**

| Superfície | Capçalera repetida | x/N |
|---|---|---|
| **Impressió del navegador** (`window.print()` → paper/PDF) | ✅ amb `thead` (mesurat) | ❌ amb `thead` · ✅ **només** si les pàgines les fa el JS (avui) |
| **Previsualització del diàleg** de Chrome | ✅ igual que el paper | igual que el paper |
| **Pantalla** (la pàgina web) | amb `thead` la capçalera surt **UN sol cop**: a pantalla no hi ha pàgines | amb `thead` el número **no té significat** a pantalla |
| PDF generat a part | **no existeix** per a aquest full (això és la fitxa tècnica: Konva + pdf-lib) | — |

**Conseqüència de producte, i és una decisió d'Agus, no de l'agent:** el `thead` regala la
repetició i el salt natural, però **es menja dues coses que avui hi són** — el `x/N` de la caixa
C4 (que és disseny APROVAT, [capcalera_ftt_v3.md](docs/spec/capcalera_ftt_v3.md) §C4, valor v18 a
731,1 · 44,1) i **la previsualització de pantalla com a full de paper**. Les tres sortides, amb el
preu de cadascuna, són a §5.

---

### 2 · FILA-TÍTOL per peça (R1)

**On es construeix el tbody:** [FittingPrintSheet.jsx:213-243](frontend/src/pages/FittingPrintSheet.jsx#L213-L243),
sobre `files` — la llista PLANA que neix a [:87-93](frontend/src/pages/FittingPrintSheet.jsx#L87-L93).

**Les files porten `garment`?** ✅ **SÍ**, i des d'abans de F5: el serializer el serveix a cada
línia ([fitting/serializers.py:352](backend/fhort/fitting/serializers.py#L352)) i la clau de
deduplicació ja el porta com a quart tram
([identitatMesura.js:35-37](frontend/src/utils/identitatMesura.js#L35-L37)). Verificat amb el
payload real:

```
g=''   → B · BB · B1 · BF · D · G1 · FS · FS2 · FS3 · FS4 · FS5          (11)
g='02' → FR · FE · CT · M · M1 · F1 · FT                                  (7)
```

**Com agrupar, i el parany de l'ordre.** El punt d'inserció és **entre [:93](frontend/src/pages/FittingPrintSheet.jsx#L93)
i [:95](frontend/src/pages/FittingPrintSheet.jsx#L95)** (ja identificat a Q5). ⚠️ **No n'hi ha
prou de recórrer `files` i emetre un títol cada cop que canvia el `garment`**: l'ordre del payload
és `BaseMeasurement.ordre`, que és **global al model** i no garanteix que una peça no s'intercali.
Al 1379 la mare té `ordre` 0-10 i la `'02'` 11-17, o sigui que avui surt bé **per casualitat de
les dades**. La llei ja escrita: agrupar per l'eix amb
[`filesDeLaPeca`](frontend/src/utils/identitatMesura.js#L69) i recórrer les peces en l'ordre de
`GET /peces/`, on la mare ve **sintètica i sempre primera** (`codi: ''`, `ordre: 0`).

**El nom de la peça.** No és al payload del full: `PieceFittingGridSerializer` només serveix
`model: {id, codi, nom, base_size_label, size_run_model}` — cap informació de peces. Cal la
**tercera crida**, que entra al `Promise.all` que ja hi és
([:63-66](frontend/src/pages/FittingPrintSheet.jsx#L63-L66)):
[`models.peces(modelId)`](frontend/src/api/endpoints.js#L76). Contracte verificat contra el 1379:

```
{'id': None, 'codi': '',   'nom': 'RUFFLES', 'ordre': 0, 'es_mare': True}
{'id': 4,    'codi': '02', 'nom': 'Short',   'ordre': 1, 'es_mare': False}
```

L'etiqueta la resol la funció que ja existeix i que les altres dues pantalles de peça fan servir
([`nomDeLaPeca`](frontend/src/utils/pecaDefinicio.js#L47), cridada a
[PecaContenidor.jsx:150](frontend/src/components/model/PecaContenidor.jsx#L150) i
[PecaDefinicioContenidor.jsx:242](frontend/src/components/model/PecaDefinicioContenidor.jsx#L242)):
la mare dona l'etiqueta genèrica `resum_wizard.model_base` i la peça el seu `nom`.

🔑 **Al full, en ANGLÈS** (D-31.22, la mateixa llei que ja aplica a les capes via `capaEn`): la
mare → **`tEn('resum_wizard.model_base')` = «Base model»**, i «Short» és **dada de domini i no es
tradueix**. ⚠️ Fixa't que la mare NO ha de dir `'RUFFLES'` (el `nom` que el contracte hi posa):
seria repetir el nom que la banda ja diu tres centímetres més amunt — i és exactament el patró
que la llei [`ftt-nom-local-que-repeteix-tapa-la-traduccio`] castiga. **A validar per l'Agus**,
perquè el contracte serveix les dues coses.

**Model sense peces:** el contracte resol el predicat ell mateix (`te_mes_duna_peca`) — **cap
`||` ni cap `length > 1` reconstruït al client**. Fals → **cap fila-títol**, taula neta com ara.

---

### 3 · GEOMETRIA (R3) — els números reals

**Marges @page avui:** `12mm` ([:121](frontend/src/pages/FittingPrintSheet.jsx#L121)). A pantalla
el full es dibuixa amb **números de px cuits i independents**: `A4_W=1123 · A4_H=794 · MARGE=45`
([:21-23](frontend/src/pages/FittingPrintSheet.jsx#L21-L23)) — 45 px = **11,9 mm**, que és el 12
mm d'`@page` retraduït a mà. **Dues declaracions de la mateixa geometria**, i és l'arrel de tot
Q6.

**Mesurat amb `@page margin: 15mm` (amplada útil 297−30 = 267 mm), amb el mateix binari que
imprimeix:**

| Peça | Alçada mesurada | Acumulat des del cantell |
|---|---|---|
| marge superior | 15,00 mm | → la banda comença a **15,00 mm** ✅ (PDF: `y = 42,52 pt`) |
| **banda de capçalera** (784,7×70,4 pt escalats 267/276,84 = **0,96446**) | **23,95 mm** | fi de banda a **38,95 mm** |
| **fila de títols de columna** (`thead`, 7,5 pt + padding 5 px) | **5,69 mm** | **44,64 mm** |
| **`thead` sencer** | **29,64 mm** | → **el `tbody` comença a 44,64 mm** |

🔑 **El 45 mm de l'Agus és correcte — i el 15+X també, si «X» inclou la fila de títols de
columna.** Els dos números són el mateix si es compta el `thead` sencer: **15 + 29,64 = 44,64 mm**
(«~45 mm»). Si «capçalera» volgués dir només la banda, seria 15 + 23,95 = **38,95 mm**, i llavors
els títols de columna quedarien fora. **La lectura que quadra amb el disseny és la primera.**

⚠️ **Hi ha un tercer bloc entremig que ningú ha nomenat**: la línia de sessió
([:177-179](frontend/src/pages/FittingPrintSheet.jsx#L177-L179), «FITTING SHEET · data · Base
size») val **≈6,9 mm** i, si es manté, empeny el `tbody` a **≈51,5 mm** i el 45 deixa de sortir.
La seva informació ja és a la banda dues vegades (la data a C4, la talla base subratllada al RUN
de C3). **Proposta: fora.** Decisió d'Agus.

**Quant encongeix la banda:** de 276,84 mm naturals a 267 mm → **escala 0,96446 (−3,55%)**, i
l'alçada baixa de 24,84 a **23,95 mm**. Amb `@page 12mm` era 273 mm → 0,98613. La banda **manté
la proporció i baixa dins del marge**: cap estirament, cap retall — sempre que l'escala es calculi
contra l'amplada REAL, que és el punt següent.

#### 3.1 · 🚨 Amb 15 mm, el codi d'AVUI RETALLA LA DATA de la caixa C4

L'escala de la banda surt d'un número cuit: `ampladaUtil = A4_W - MARGE*2` = **1033 px**
([:166](frontend/src/pages/FittingPrintSheet.jsx#L166)) → `escala = amplada / natW`
([FttHeaderBand.jsx:39](frontend/src/components/model/FttHeaderBand.jsx#L39)). Amb `@page 12mm`
l'àrea imprimible fa 1032 px i **coincideix per construcció** (per 1 px). Amb **15 mm** fa
**1009 px**, i la banda segueix dibuixant-se a 1033: sobra un 2,4% que el `overflow: hidden` del
wrap ([FttHeaderBand.jsx:46](frontend/src/components/model/FttHeaderBand.jsx#L46)) es menja **en
silenci**. Mesurat al PDF, mateixa rèplica, dues escales:

```
escala correcta (0,96446)  → DATA x=736,1 · "16/08/2026" x=736,1 ✅ · A4 x=736,1 · 1/N x=748,6
codi real (1033 px cuits)  → DATA x=752,6 · «16/08/2026» ⛔ ABSENT DEL PDF · A4 x=752,6 · 1/N x=765,3
```

**La data desapareix del paper** (surt fora del límit imprimible, 799,4 pt, i el clip la talla) i
el `1/N` queda fregant el marge. **R3 no és «canviar 12 per 15»: sense arreglar l'escala, els
15 mm trenquen la caixa C4.** Els dos canvis han d'anar al MATEIX commit.

🔑 **Correcció a Q6 (punt 1 del fix F8):** allà es va escriure que «`FttHeaderBand` també el fa
servir la fitxa» i que per això el canvi havia de ser additiu. **És fals i s'ha comprovat:**
`grep -rn FttHeaderBand --include=*.jsx` → **un sol consumidor**, aquest full. La fitxa tècnica
dibuixa la seva capçalera amb Konva a partir del mateix `HDR_H_V3`
([TechSheetEditor.jsx:1191-1221](frontend/src/pages/TechSheetEditor.jsx#L1191-L1221)), no del
component. El radi del canvi és **1**.

#### 3.2 · Quant hi cap — i per què el `18` cuit és avui una coincidència

Amb 15 mm i **sense peu ni llegenda** (R4): alçada útil 180 mm − `thead` 29,64 = **150,36 mm**
per al `tbody`. Alçades de fila mesurades: **5,22 mm** (nom d'una línia) · **9,11 mm** (dues) ·
**20,79 mm** (el `FS4` de 65 caràcters, quatre) · **fila-títol 6,28 mm**.

```
1379 · 18 files + 2 files-títol = 149,30 mm de 150,36 disponibles  →  1 PÀGINA, per 1,06 mm
```

**El 1379 amb el disseny nou cap en UNA pàgina** (PDF real: `Pages: 1`) — i per tant **NO exerceix
ni la repetició de capçalera ni el x/N amb N>1**. ⚠️ Això invalida el guard que el brief proposa
(«1379 → capçalera a cada pàgina, x/N correcte»): v. §6.

I `FILES_PER_PAGINA = 18` ([:28](frontend/src/pages/FittingPrintSheet.jsx#L28)) queda doblement
desmentit: amb les 2 files-títol el comptador veuria **20 elements** i partiria en **dues
pàgines** un full que en necessita **una**; i el seu comentari («un límit conservador… una pàgina
sencera de noms de dues línies encara hi cap») ja el va desmentir Q6 en vertical. **Un comptador
de files no pot mesurar una alçada que depèn del text.**

---

### 4 · LOGO (R5) — 🚨 el forat NO és el CSS: és l'ASSET

**On és:** [FttHeaderBand.jsx:61-69](frontend/src/components/model/FttHeaderBand.jsx#L61-L69) —
caixa `S.logo` = **126×28 pt** (spec §C1, caixa intocable amb acta) i
`objectFit: 'contain', objectPosition: 'left center'`. El CSS **ja és el correcte i mínim**: no hi
ha res a afegir-hi.

**L'asset**, `customer_logos/2026/08/Logo-BROWNIE.png` (**PNG**, el payload el serveix a
`ple.customer_logo` → [:159](frontend/src/pages/FittingPrintSheet.jsx#L159)):

```
llenç:               2084 × 1042 px  (ràtio 2,00)
CONTAIN a 126×28 pt →   56,0 × 28,0 pt  → ocupa  44% de l'ample · 100% de l'alt
tinta real (bbox alpha): 1610 × 253 px de 2084×1042  → 23% d'aire lateral · 76% d'AIRE VERTICAL
ràtio del CONTINGUT:  6,36   (la caixa és 4,50)
```

**El PNG porta el seu propi marge transparent.** Amb `contain`, el que s'ajusta a la caixa és el
LLENÇ, no la marca: la tinta acaba ocupant ~44% de l'ample i ~24% de l'alt de la caixa — **un 11%
de la seva àrea**. Es veu petit i centrat en un mar de no-res, i **cap canvi de CSS ho arregla**:
`cover` la retallaria, estirar-la la deformaria, i engrandir la caixa és exactament el que la
regla amb acta del [CLAUDE.md](CLAUDE.md) prohibeix a un agent.

**El fix és de DADES, no de codi:** re-pujar el logo escapçat (sense l'aire). Amb ràtio 6,36 dins
d'una caixa de 4,50, el `contain` d'avui li donaria **126 × 19,8 pt: el 100% de l'ample**, que és
literalment el que R5 demana. ⚠️ Afecta **també la fitxa tècnica**, que escala el mateix asset amb
la mateixa llei (`headerMasterLogoRect`,
[TechSheetEditor.jsx:1283-1292](frontend/src/pages/TechSheetEditor.jsx#L1283-L1292)) → **millora
les dues superfícies alhora**. Alternativa de codi (escapçar l'alpha en pujar el logo) = feina de
backend, fora d'aquest tram, i s'anota.

---

### 5 · Q6 · ¿els 15 mm resolen el desbordament de pantalla (1123 px)?

**No, i no el poden resoldre.** Són dos problemes diferents i Q6 ja els va separar:

- **Paper**: mesurat, no desborda (ni amb 12 ni amb 15 mm) — el que sí que es trenca amb 15 mm és
  la banda, i és el §3.1 d'aquí.
- **Pantalla**: `.ftt-full` fa **1123 px durs** ([:169](frontend/src/pages/FittingPrintSheet.jsx#L169))
  i `.ftt-wrap` no té `overflow-x` ni `zoom` ([:116](frontend/src/pages/FittingPrintSheet.jsx#L116)).
  Canviar `@page` de 12 a 15 mm **no toca ni un píxel de pantalla**: el marge intern passaria de
  45 a 57 px si es reescriu el `MARGE`, però el full seguiria fent 1123 px i seguiria tallant-se
  en una finestra més estreta. **Cal escalat de previsualització** (`transform: scale()` sobre el
  full, contenidor amb l'ample de la finestra), que és el punt 3 del F8 de Q6 i **un commit a
  part**.

🔑 **La cura d'arrel de tots dos, i és barata:** declarar el full **una sola vegada i en mm**
(297×210 amb `padding: 15mm`), i que la pantalla el mostri amb un `scale` de previsualització. Avui
la mateixa geometria està escrita **dues vegades i en dues unitats** —px a
[:21-23](frontend/src/pages/FittingPrintSheet.jsx#L21-L23), mm a
[:121](frontend/src/pages/FittingPrintSheet.jsx#L121)/[:136-140](frontend/src/pages/FittingPrintSheet.jsx#L136-L140)—
i el comentari de [:17-20](frontend/src/pages/FittingPrintSheet.jsx#L17-L20) ho declara com una
virtut («si les dues no diguessin el mateix…»). **Diuen el mateix per a A4 amb 12 mm i prou**: el
retall de la data del §3.1 és aquesta doble declaració cobrant-se el primer canvi de marge.

---

### 6 · Les tres sortides per al x/N — **decisió d'Agus**

|  | **A · `thead` pur** (el que R2 proposa) | **B · pàgines mesurades** amb `thead` per pàgina | **C · `thead` + comptador cuit d'avui** |
|---|---|---|---|
| Capçalera a cada pàgina | ✅ de franc (mesurat) | ✅ (un `.ftt-full` per pàgina, com avui) | ✅ |
| `tbody` sempre a 44,64 mm | ✅ estructural | ✅ estructural | ✅ |
| Salt de pàgina natural | ✅ | ✅ (el tall el decideix la mesura, no un número) | ❌ el `18` parteix on no toca |
| **x/N** | ❌ **impossible** (§1.3) | ✅ exacte | ✅ exacte però **pot mentir** de pàgina |
| Previsualització de paper a pantalla | ❌ es perd | ✅ es manté | ✅ |
| Codi | **el mínim**: −40 línies (fora paginació) | +`useLayoutEffect` de mesura (~40 línies) | mínim |
| Risc | la caixa C4 aprovada es queda sense número | la mesura ha de córrer abans d'imprimir | 20 elements → 2 pàgines quan en cap 1 (§3.2) |

**Recomanació de l'agent: B.** És l'única que compleix R1+R2+R3 senceres sense trencar disseny
aprovat. El `thead` hi entra igual —i és el que garanteix R3 **estructuralment**, en comptes de
per un número—; el que no es delega al navegador és **on** talla, perquè és justament el que
Chrome no sap dir-nos després. Si l'Agus prefereix **A**, cal decidir què va a la caixa C4 al
lloc del `1/n` (i **és disseny aprovat: demana acta**).

---

### 7 · Pla de commits proposat (res implementat)

| # | Commit | Abast | Per què junts / separats |
|---|---|---|---|
| **C1** | `fix(fitting): el full imprimeix amb 15mm i la banda escala contra l'amplada real` | `@page 12→15mm` · `FttHeaderBand` deixa de rebre px cuits · `.ftt-full` 184→180 mm · **R4: fora llegenda i signatura** ([:247-260](frontend/src/pages/FittingPrintSheet.jsx#L247-L260)) | **Un sol focus: la geometria vertical i horitzontal del paper.** R4 hi entra perquè és l'espai que C1 redistribueix i **perquè els 15 mm sense treure el peu deixarien el full sense marge** (Q6: 695/695 px). I l'escala **no és separable** dels 15 mm: sense ella el marge nou retalla la data (§3.1) |
| **C2** | `feat(fitting): la capçalera del full és el thead i es repeteix a cada pàgina` | banda + títols de columna dins del `<thead>`; fora la línia de sessió; segons §6, la paginació passa a mesurada (B) o desapareix (A) | Focus propi: **on viu la capçalera**. Depèn de C1 (l'escala ha de ser bona abans de moure-la) |
| **C3** | `feat(fitting): el full obre un contenidor per prenda amb fila-títol` | 3a crida `models.peces` al `Promise.all` · agrupació per `filesDeLaPeca` · fila-títol via `nomDeLaPeca` + `tEn` | Focus propi i **l'únic que toca DADES**. Va l'últim perquè és el que el guard vermell mesura |
| **C4** | *(cap commit)* **logo** | acció sobre l'**asset** (§4), no sobre codi | Requereix decisió d'Agus i **millora també la fitxa** |
| **C5** | `fix(fitting): el full s'ajusta a la finestra a pantalla` | `transform: scale()` de previsualització (Q6 punt 3) | **Fora d'aquest tram** si l'Agus vol: no és cap dels 5 requisits |

**Ordre obligat: C1 → C2 → C3.** Cada un verd (`npm run build` net) abans del següent.

---

### 8 · Guards (VERMELL avui amb el 1379 · VERD amb el control d'una peça)

| # | Guard | On | Vermell AVUI | Control una-peça |
|---|---|---|---|---|
| **G18** | **La partició per peça i les files-títol** | test de **funció pura** `agrupaPerPeca(files, peces)` a `frontend/src/utils/*.test.js` (`node --test`, no hi ha vitest) | 1379 → **2 grups: `''`/«Base model» amb 11 · `'02'`/«Short» amb 7**. Avui: **1 grup de 18** | `te_mes_duna_peca: false` → **1 grup i CAP fila-títol**; la llista de files, idèntica byte a byte |
| **G19** | **L'etiqueta de la mare és genèrica i en anglès** | mateix test | mare → **«Base model»**, MAI `'RUFFLES'` (el nom ja és a la banda) i mai `''` | sense la crida a `/peces/`, degrada al comportament d'ara — mai a una taula buida |
| **G20** | 🚨 **L'ordre no depèn de la sort de les dades** | mateix test, amb un fixture on la `'02'` porta un `ordre` **intercalat** (p. ex. 5) | 2 grups nets, mare primera. **Amb el codi «emet títol quan canvia el garment» sortirien 3-4 títols** | 1 grup |
| **G21** | **Geometria mesurada al PDF real** | sonda de repositori (Chromium `--print-to-pdf` + `pdftotext -bbox`), patró de les d'aquesta secció | banda a **15,00 mm** · `tbody` a **44,64 mm** · **iguals a TOTES les pàgines** | — |
| **G22** | 🚨 **La caixa C4 no es retalla** | mateixa sonda | amb 15 mm, **`"16/08/2026"` ha de ser present al text del PDF** (avui, amb els 1033 px cuits: **ABSENT**) | — |
| **G23** | **La fila-títol no es repeteix per pàgina** | mateixa sonda, fixture de **60 files d'un sol grup** | 4 pàgines · el títol **només a la P1** | — |

⚠️ **El guard de x/N NO el pot donar el 1379**: amb el disseny nou hi cap en **1 pàgina** (§3.2) i
diria `1/1` tant si el mecanisme funciona com si és un literal. **Cal un fixture de ≥40 files**
(o el 1379 amb el paper reduït) perquè `N > 1` signifiqui alguna cosa. Un guard de x/N contra el
1379 seria **verd sempre i no provaria res** — el mode de fallada que aquest document persegueix.

---

### 9 · Riscos

1. 🚨 **Els 15 mm sols són una REGRESSIÓ.** Sense l'escala contra l'amplada real, el marge nou fa
   desaparèixer la data de la caixa C4 **sense avisar** (§3.1, mesurat). Si C1 s'ha de partir, el
   tros de l'escala va PRIMER, mai després.
2. 🚨 **El `thead` es cobra el x/N i la previsualització de paper** (§1.3). Són dues pèrdues de
   producte, no dos detalls tècnics, i la primera toca **disseny aprovat amb acta**.
3. **L'ordre de les files és global al model, no per peça** (§2). El codi ingenu funciona amb el
   1379 **per casualitat**; G20 existeix per fer-lo caure.
4. **La numeració `#` de les files** ([:219](frontend/src/pages/FittingPrintSheet.jsx#L219)) avui
   és contínua per full (`desDe + j + 1`). Amb contenidors per peça cal decidir si segueix
   contínua o es reinicia a cada prenda. **Recomanació: contínua** —el `#` serveix per assenyalar
   una línia del paper a la sala—, però és decisió d'Agus.
5. **Claus i18n que queden òrfenes** amb R4: `fitting.print.legend_ac|legend_ad|legend_rj|signature`
   (i `session_line` si cau la línia de sessió). **Anotades, no esborrades**: treure-les del JSON
   és un altre focus i el gate d'i18n vol paritat ca/en/es.
6. **`FILES_PER_PAGINA` mor amb qualsevol de les tres sortides** (§3.2). Si sobreviu per
   inèrcia, partirà en dues pàgines un 1379 que en necessita una.
7. **`node --test`, no vitest** ([`ftt-s37-vet-c5-chip`]): els guards de funció pura han de
   respectar el corredor que el repo té.

### 10 · Fronteres respectades

Cap escriptura a BD (totes les sondes són `SELECT`/ORM de lectura i serializers executats en
lectura) · **cap login** (la llei [`ftt-mesurar-impressio-i-no-login`]: autenticar-se escriuria
`last_login`) · cap fitxer del repo modificat excepte aquest · cap commit, cap push, cap deploy ·
**no s'ha tocat** serializers (F7 és fet), motor, G6, billing, tasques, Konva ni `TechSheetEditor`
—només s'han LLEGIT `HDR_H_V3` i `headerMasterLogoRect` per citar-los—.

---

## Q10 · LOGO DEL CLIENT — mapa de Fase A (read-only). 🛑 **FASE B ATURADA**

> **17/08 · Patró B, tram del logo.** La Fase A havia de tornar un mapa net abans de tocar
> l'asset. No el torna: hi ha **dues troballes que canvien què vol dir «escapçar el logo»**, i
> totes dues demanen decisió. **Res tocat**: el fitxer del client segueix intacte.

### 1 · On viu, i què és

| Què | Valor |
|---|---|
| Camp | `Customer.logo = ImageField(upload_to='customer_logos/%Y/%m/')` — [tasks/models.py:320](backend/fhort/tasks/models.py#L320) |
| Fitxer (Brownie) | `backend/media/fhort/customer_logos/2026/08/Logo-BROWNIE.png` · 41.066 B · `www-data` |
| Format real | PNG RGBA **2084×1042** (ràtio 2,00) |
| Tinta real | bbox alfa **(232, 365, 1842, 618)** = 1610×253 → **23% d'aire lateral · 76% d'aire vertical** |
| Storage | **media de TENANT, fora de git** → si es toca, **no és un commit: és una operació d'asset** |

Els altres dos clients amb logo són **SVG** (`losan-logo.svg`, `Fhort_Textile_Tech.svg`), i el
seu `viewBox` (`0 0 841,9 784`) és gairebé quadrat: dins d'una caixa 4,5:1 en surten petits
també, però allà **és la forma del logo** i no hi ha res a retallar. El cas del Brownie és
l'altre: el llenç no diu res de la forma de la tinta.

### 2 · Qui el consumeix (escapçar-lo els toca tots)

| # | Consumidor | Com |
|---|---|---|
| 1 | **Full de fitting** | `customer_logo` → [FittingPrintSheet.jsx:196](frontend/src/pages/FittingPrintSheet.jsx#L196) → `FttHeaderBand`, caixa 126×28 pt, `object-fit: contain` |
| 2 | **Fitxa tècnica** (Konva) | [TechSheetEditor.jsx:2797](frontend/src/pages/TechSheetEditor.jsx#L2797) + `headerMasterLogoRect` — **mateixa caixa de la spec, mateixa llei CONTAIN** |
| 3 | 🚨 **El document `.ftt`** | [services_ftt_document.py:144-165](backend/fhort/models_app/services_ftt_document.py#L144-L165) — **CONGELA ELS BYTES** dins del document (`assets/field_customer_logo.png`) |
| 4 | Export/import de paquet | [export_losan_package.py:122](backend/fhort/pom/management/commands/export_losan_package.py#L122) · [load_losan_package.py:224](backend/fhort/pom/management/commands/load_losan_package.py#L224) |
| 5 | La URL del payload | [models_app/serializers.py:256](backend/fhort/models_app/serializers.py#L256) |

### 3 · 🚩 TROBALLA A · **el `.ftt` no llegeix el logo: se'l queda**

`_resolve_logo_obj` copia els BYTES del fitxer dins del document com a asset congelat. O sigui
que retallar el PNG **no arregla cap fitxa ja desada** i obre una divergència que avui no hi és:
els documents vells amb el logo amb aire, els nous amb el retallat. No és cap raó per no fer-ho
—el full de fitting i les fitxes noves guanyen igual—, però **la promesa «tots els consumidors
guanyen» és falsa** i havia de constar abans de tocar res.

### 4 · 🚩 TROBALLA B · **ja existeix un normalitzador de logos… i el del CLIENT no hi passa**

`accounts/logo.py::normalize_logo` ([:31](backend/fhort/accounts/logo.py#L31)) converteix el
que sigui a PNG, aplana paletes i acota a 2000 px. **Dues coses:**

1. **És per a l'ALTRE logo** — el de l'emissor (`TenantConfig.logo_file`, via
   [pom/s2_views.py:387](backend/fhort/pom/s2_views.py#L387)). El logo del CLIENT s'assigna
   **cru**: `customer.logo = logo_file` a
   [tasks/views_b.py:884-887](backend/fhort/tasks/views_b.py#L884-L887) (`POST
   /customers/<id>/upload-logo/`). **Dos camins de logo amb tractaments diferents**, i el que va
   al paper del fabricant és el que no en té cap.
2. **Ni tan sols `normalize_logo` faria trim**: no toca l'alfa. O sigui que no n'hi hauria prou
   d'encaminar-hi el logo de client; caldria afegir-hi el retall.

**Conseqüència directa: escapçar el fitxer d'avui és un pedaç PER FITXER.** El pròxim logo que
el client pengi tornarà a tenir l'aire que porti, i ningú se n'assabentarà fins que algú miri un
paper imprès. La solució que no torna és **normalitzar a la INGESTA** (trim de l'alfa dins de
`normalize_logo` + fer-hi passar `upload_logo`), i llavors el retall del fitxer d'avui és només
la migració d'un asset existent.

### 5 · Què faria el trim, mesurat (simulat al scratchpad; **`media/` NO tocat**)

```
original  2084 × 1042  ràtio 2,00  → CONTAIN a 126×28 pt =  56,0 × 28,0 pt = 44% ample · 11% d'àrea
retallat  1610 ×  253  ràtio 6,36  → CONTAIN a 126×28 pt = 126,0 × 19,8 pt = 100% ample · 71% d'àrea
```

El PNG retallat ja està generat i esperant a
`scratchpad/Logo-BROWNIE.trimmed.png` — **fora de `media/`, fora del repo**.

### 6 · El que falta per poder executar la Fase B

1. **Decisió**: pedaç per-fitxer (retallar el Brownie i prou) **o** normalització a la ingesta
   (i el retall com a migració). La segona toca `accounts/logo.py` i `upload_logo`, que aquest
   tram tenia **prohibits**.
2. Confirmar que la divergència del `.ftt` (troballa A) és acceptable.
3. Amb el sí: còpia `Logo-BROWNIE.original.png` al costat, substitució al mateix path i mateix
   nom (cap canvi al camp ni al codi), i PDF de verificació.
