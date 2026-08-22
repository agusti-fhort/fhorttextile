# SEMBRA DEL MODEL 837 A STAGING · DRY-RUN

**Data:** 2026-08-21 · **Entorn:** staging `/var/www/ftt-staging`, branca `dev`, tenant `fhort`
**Font:** `docs/ordres/MODEL_837_EXPORT.json` (foto READ-ONLY de PROD, model pk PROD=1215, `TRV-SS27-0001`)
**Command:** `backend/fhort/models_app/management/commands/sembra_model_837.py`
**Estat:** ✅ **SEMBRAT** amb OK d'Agus (21/08). Model **pk staging = 1383** (PROD 1215).
Verificació independent OK · idempotència OK · `/api/schema/` = 200. **Cap push.**

```bash
cd /var/www/ftt-staging/backend
venv/bin/python manage.py sembra_model_837            # dry-run (per defecte)
venv/bin/python manage.py sembra_model_837 --apply \
    --crea-entorn-absent --accepta-discrepancies-pom --accepta-ruleset-divergent
```

> Una 2a execució diu `IDEMPOTÈNCIA: … ja existeix (pk=1383). 0 creacions.` — comprovat
> dues vegades, amb els recomptes intactes després.

---

## 1. Els 3 bloquejos i com es van resoldre

El dry-run va aturar-se amb tres decisions obertes. Totes tres resoltes per Agus el 21/08:

| # | Bloqueig | Resolució |
|---|---|---|
| 1 | `Customer TRV` i `UserProfile fhort` **no existien a staging** | **CREATS** per la sembra (`--crea-entorn-absent`). Mai remapats a un actor existent: l'actoria és evidència forense. V. §3 |
| 2 | 30 dels 142 POMMaster resolen per codi però **el contingut divergeix** | **Resolució 1:1 acceptada**, catàleg de staging INTACTE. El deute queda anotat a §9 |
| 3 | El hash del joc `BRW-CATALEG-v3` **no coincideix** | **Joc de staging REUTILITZAT** (grading idèntic fila a fila, verificat). V. §5 |

---

## 2. El que SÍ que quadra

**Les 14 guardes de recompte quadren exactes** contra el cens de PROD:

| Entitat | Previst | Guarda | | Entitat | Previst | Guarda |
|---|---:|---:|---|---|---:|---:|
| Model | 1 | 1 | | PieceFitting | 2 | 2 |
| BaseMeasurement | 21 | 21 | | PieceFittingLine | 200 | 200 |
| ModelGradingRule | 142 | 142 | | ModelTask | 3 | 3 |
| MeasurementChangeLog | 21 | 21 | | TimerEntrada | 8 | 8 |
| SizeFitting | 1 | 1 | | ModelFitxer | 8 | 8 |
| GradingVersion | 6 | 6 | | Watchpoint | 0 | 0 |
| GradedSpec | 615 | 615 | | FittingSession | 2 | 2 |

L'entorn resol per clau natural sense crear res:
`GarmentType DRESSES`→71 · `GarmentTypeItem dress_simple`→28 · `GarmentGroup DRESSES`→8 ·
`SizeSystem ALPHA_EU_W`→29 (8 talles idèntiques) · `GradingRuleSet BRW-CATALEG-v3`→**219** (PROD 152) ·
`TaskType pom`→15, `size_check`→20, **`grading`→21 (PROD 23)** · `UserProfile Montse`→13.

> El `TaskType grading` és el cas que justifica la regla: el pk de PROD (23) apunta a
> **una altra fila** a staging. Resolt per `code`, no per pk.

---

## 3. Entorn creat per la sembra

Dues files **no existien a staging i les ha creat la sembra**. Queden marcades aquí perquè
NO són part de la foto de PROD: són el mínim perquè el banc es pugui aguantar dret.

| Creat | pk staging | Detall |
|---|---|---|
| `Customer TRV` | **11** | codi/nom/`active` de la foto (`TROVELS`). El del joc de regles és `BRW` i ja hi era |
| `auth_user fhort` | **23** | al schema del tenant, `set_unusable_password()` — aquest compte **no pot entrar** |
| `UserProfile fhort` | **24** | `rol_nom='technician'` (el `DEFAULT_ROLE` que hi posa el signal) |

**Per què creats i no remapats.** A PROD `fhort` és el `pk=1`; a staging el `pk=1` és
`a.devant@fhort.cat` — **mateix pk, actor diferent**. `fhort` és qui va obrir la
`FittingSession` #123 i signar el `PieceFitting` #16: remapar-lo hauria falsejat l'evidència.

**El rol no se l'inventa la sembra.** La foto no porta el rol de l'actor, així que es queda el
que hi deixa `create_user_profile`. Si el banc necessita que `fhort` tingui permisos concrets,
és un canvi a fer a mà i a consciència.

> ⚠️ **`create_user_profile` (post_save de `User`) ja crea el UserProfile dins d'un tenant.**
> El primer `--apply` va petar aquí (`duplicate key … accounts_userprofile_user_id_key`) i
> l'atomic va fer rollback net. És **el mateix patró que `sync_size_fitting`**: la sembra
> ADOPTA el que el signal ja ha creat. Dos casos, la mateixa llei.
>
> Detall de multi-tenant que va aparèixer investigant-ho: `auth_user` existeix a `public` **i**
> a cada tenant. `public.auth_user` té 2 files (login central: `fhort`, `a.devant@fhort.cat`)
> i `fhort.auth_user` en té 5, que són les que veu l'ORM sota `search_path = fhort, public`.
> Els `UserProfile` del tenant apunten a les del tenant.

## 4. Els 142 POMMaster: resolució 1:1 (LLEI S44)

Cap POMMaster és absent ni ambigu: **els 142 resolen 1:1 per `codi_client`**. El que divergeix és
el contingut. Tres classes, molt diferents en gravetat:

| Classe | N | Exemple | Toca el significat? |
|---|---:|---|---|
| **‼ `pom_global`**: la foto l'ancora a un POM global, staging no | **4** | `S`: foto `LOSPOM-548`, staging `None` | **SÍ** — canvia l'ancoratge |
| `categoria`: NULL a la foto, categoritzat a staging (o a l'inrevés) | 30 | `F`: foto `None`, staging `'F'` | no |
| `nom_client`: majúscules a la foto, Title case a staging | ~18 | `BR`: foto `FLY WIDTH`, staging `Fly width` | no |

Els **4 d'ancoratge** són `S`, `S2`, `BR`, `U4` — i **`S` i `S2` són dos dels 21 POM mesurats**
(`Front/Back armhole along seam`). Dos casos més de nom no són pura capitalització i val la pena
mirar-los: `E2` (foto `11cm`, staging `11 cm`) i `I`/`GD`, on la categoria de la foto és un valor
d'un altre vocabulari (`CAT-UB`, `Skirt / Dress`) i no un codi de categoria.

**Els 5 POM «no resolts» dels 21 mesurats:** `F`, `E`, `S`, `S2`, `I`.

---

## 5. El joc de regles: reutilitzat

```
foto     142 regles · hash 4f1dfa46…7395
staging  142 regles · hash 096990db…989f   (pk=219)
```

**Les 142 regles tenen el grading IDÈNTIC.** La divergència és, fila per fila, **només el
`pom_global`** dels mateixos 4 POM del bloqueig 2:

```
foto    ["LOSPOM-548", "S",  "LINEAR", 0.70, 0.70, 1.00, "S", …]
staging [null,         "S",  "LINEAR", 0.70, 0.70, 1.00, "S", …]
```

O sigui: `logica`, `increment`, `increment_base`, `increment_break`, `talla_break_*` i
`talla_base` coincideixen a les 142. Reutilitzar el joc de staging no canvia ni un valor
d'escalat; només deixa 4 regles sense ancoratge global.

**Decisió: es reutilitza el joc `pk=219` de staging.** El model 1383 hi apunta per
`grading_rule_set`, i les 142 `ModelGradingRule` en van derivar amb `derivat_de_rule_set=219`.

**Hash de referència del banc** (fórmula d'aquest command, sobre les 142 regles de staging):

```
096990db404b778a2140fffd8327c54294849b73d42ec67b3265247f9840989f
```

Si aquest hash canvia, el joc sota el banc s'ha mogut i els resultats de qualsevol prova feta
abans deixen de ser comparables.

> ⚠️ El hash **declarat** a la foto (`af881bb8…ef01`) no és reproduïble des d'aquí: la fórmula
> exacta de PROD no viatja amb el JSON. La comparació de dalt és foto↔staging amb la **mateixa**
> fórmula, i és la que decideix. La nota del snapshot descriu els camps, no la normalització.

---

## 6. Les incoherències que la sembra conserva

Aquest és el punt de tot: **es transcriuen crues.** El dry-run les enumera per poder-les
verificar després de l'apply.

**Regla POM `D` (Bottom width):** `increment=2.00` · `increment_base=0.50` · `increment_break=0.50`,
`talla_break_label='M'`, `talla_break_pos=2`, `origen=MANUAL`, editada a les 18:14:09 (v6 generada
a les 18:17:22 — **l'ordre relatiu es conserva**, que és el que importa per al bug A).

**El `D` graduat, versió per versió** (base `S`=59.0):

| | XS | S | M | L | XL |
|---|---|---|---|---|---|
| v1–v5 | 57.0 (−2.0) | 59.0 | 62.0 (+3.0) | 65.0 (+6.0) | 68.0 (+9.0) |
| **v6 (vigent)** | 58.5 (−0.5) | 59.0 | 59.5 (+0.5) | 60.0 (+1.0) | 60.5 (+1.5) |

**L'asimetria −2.0 / +3.0 de v1–v5 NO és cap anomalia.** És la semàntica del break: amb `S`
com a talla base, s'aplica **base 2 per sota** i **break 3 per sobre**. El comportament és
l'esperat i no s'ha de «corregir» — qui trobi aquests números al banc, que no els persegueixi.

**La mina és una altra: el `2.00` orfe.** Cap de les 6 versions l'aplica. És el llegat
`increment` **fossilitzat** (§A de la diagnosi): un valor que segueix a la fila i que ja no
mana res del que es genera. El banc el conserva viu precisament per poder-lo estudiar.

**La resta:**
- 6 GradingVersions, la **v6 vigent**; v1 sense nom i sense `creat_per`, v2–v6 «Propagació conscient».
- Specs per versió: 95 · 100 · 105 · 105 · 105 · 105 = **615**.
- **`PieceFitting` PROD#15 penja de la v2** (95 línies), no de la vigent; el #16 penja de la v6 (105).
- `SizeFitting` `TallesGenerades` amb `base_tancada=False`.
- Joc **BROWNIE** (`BRW-CATALEG-v3`, customer BRW) sobre un model del client **TRV**.

---

## 7. Com la sembra entra sota els signals

Cens de `models_app/signals.py` i què fa la sembra amb cadascun:

| Signal | Efecte si no es fa res | Com hi entra la sembra |
|---|---|---|
| `generate_model_code` (pre_save) | regeneraria codi i sequencial | es passa `codi_intern` explícit → el signal se'n desentén |
| `sync_size_fitting` (post_save) | crea **un** SizeFitting `Pendent` | **s'ADOPTA** i s'hi transcriu la foto amb `.update()` → segueixen sent 1, no 2 |
| `log_measurement_change` (post_save) | **21 logs automàtics** amb el context del signal | les 21 mesures entren per `bulk_create` (no dispara post_save) i els 21 logs es transcriuen literals |
| `update_last_activity` (post_save) | `darrera_activitat = now()` | es restaura amb `.update()` |
| `recompute_import_watchpoint` | — | no-op: 0 Watchpoints oberts |
| `sync_encarrec_a_l_estudi` | — | no-op: `studio_assignat=''` |
| `auto_now` / `auto_now_add` (9 camps) | timestamps = ara | `QuerySet.update()` no crida `Field.pre_save` → la foto es conserva |

Hi ha una **guarda activa** després del `bulk_create`: si arriba a existir un sol
`MeasurementChangeLog` automàtic, la sembra peta amb rollback. Si algun dia el signal deixa
d'entrar per `post_save`, això ho canta en comptes de duplicar 21 files en silenci.

**El que NO es transcriu:** `ModelTask.work_order` (comanda PROD #69 — `commerce.WorkOrder`, no
viatja a la foto; el camp és nullable). Els 8 `.ftt` sí que es recreen al disc: la foto en porta
el document sencer (451–1624 bytes cadascun). ⚠️ **Fins al 21/08 es recreaven MALAMENT** — v.
§8-bis.

---

## 8. Resultat de l'`--apply`

Corregut el 21/08 dins d'una sola transacció (l'entorn creat i la transcripció cauen amb el
mateix rollback). **Model pk=1383.**

**Verificació independent** — per ORM, sense passar pel command (`scratchpad/verif.py`):

- Els **13 recomptes** quadren: 21 · 142 · 21 · 1 · 6 · **615** · 2 · 2 · 200 · 3 · 8 · 8 · 0.
- **Regla `D`**: `increment=2.00` · `increment_base=0.50` · `increment_break=0.50`, break `M` pos 2 — **la incoherència és viva**.
- **v1–v5 pas 3.0 al `D`** (XS=57.0 S=59.0 M=62.0 L=65.0 XL=68.0); **v6 vigent, pas 0.5** (XS=58.5 … XL=60.5). Una sola versió activa i és la v6.
- `SizeFitting` `TallesGenerades` · `base_tancada=False` · codi `TRV-SS27-0001-SF1`.
- `PieceFitting` pk=52 → **v2** (sessió Anullada, 95 línies) · pk=53 → v6 (sessió Oberta, 105 línies).
- Joc `BRW-CATALEG-v3` (customer **BRW**) sobre model del customer **TRV**.
- Les **21 mesures base**: cap difereix de la foto.
- **Ordre relatiu conservat**: regla `D` editada 18:14:09 < v6 generada 18:17:22 → el bug A és reproduïble.
- ~~Els **8 `.ftt`** existeixen al disc sota `MEDIA_ROOT`.~~ 🚨 **CORREGIT EL 21/08 (J-bis/3).**
  Aquella línia era **literalment certa i pràcticament falsa**, que és la pitjor combinació: els
  vuit fitxers hi eren sota `MEDIA_ROOT`, però **no on Django els llegeix**, i a més **en un
  format que no s'obre**. V. §8-bis.

## 8-bis. 🚨 EL ✅ FALS DELS 8 `.ftt` — diagnòstic i reparació (21/08, J-bis/3)

> **Un ✅ fals és pitjor que un forat**, i aquest ho era per partida doble: va sobreviure a la
> verificació independent per ORM (que mira la BD, no el disc) i a dues sessions posteriors.
> H el va anotar d'UN fitxer (873) i H-bis de tots vuit; cap dels dos va poder dir per què.

### Què va verificar de veritat la sembra

**Que un `open()` no havia petat, i res més.** El comptador `escrits` s'incrementava després
d'escriure, i escriure va funcionar: els vuit fitxers hi eren. El que ningú no va comprovar és si
eren **llegibles** i si eren **al lloc on es llegeixen** — i no ho eren per **dos motius
independents**, que és el que ho feia difícil de veure (arreglar-ne un de sol no hauria servit).

| # | Defecte | Què passava | Per què no cantava |
|---|---|---|---|
| **1** | **FORMAT** | `json.dump(doc)` cru. Un `.ftt` és un **ZIP** amb `manifest.json` + `document.json` (`services_ftt.pack`) | `load_document` no el pot desempaquetar → **l'editor l'obre BUIT**, sense error |
| **2** | **CAMÍ** | `os.path.join(MEDIA_ROOT, name)`. El default storage és `TenantFileSystemStorage` i hi posa l'esquema pel mig | els fitxers van a `media/model_fitxers/…` i Django llegeix `media/fhort/model_fitxers/…` |

La prova del format és la MIDA: la foto diu 451 B per al primer i el que hi havia al disc en feia
**94** (el JSON cru). Amb el ZIP ben fet en fa **451**, clavats.

**No era «bytes mai exportats».** `MODEL_837_EXPORT.json` porta `_ftt_document` per als vuit,
sencer i fidel. **I per tant no calia cap `scp` de PROD**: el contingut ja era al repo.

### La reparació

Els vuit s'han **reempaquetat amb `services_ftt.pack`** i escrits per `ModelFitxer.fitxer.path`
(que és el que sap del tenant). Mides resultants **idèntiques a la foto**, una per una:

```
451 · 468 · 594 · 1571 · 1591 · 1623 · 1626 · 1624
```

🔑 **El `checksum` NO casa, i és CORRECTE que no casi.** Aquell camp és el sha del **blob ZIP**, i
`zipfile.writestr` hi estampa la data-hora de cada entrada: **dos empaquetats del mateix contingut
donen bytes diferents sempre** (mesurat al repo: 604/604 checksums distints a staging, 3.603/3.606
a PROD — v. l'avís d'`empremta_logica`). El `checksum` de la foto és el del ZIP de PROD i no és
reproduïble per ningú. S'ha desat el dels bytes REALS d'aquest disc: copiar el de la foto hauria
estat desar una empremta que no correspon a cap fitxer existent. **El que es compara és la mida i
l'empremta LÒGICA**, i totes dues casen.

**Verificat per `load_document`**, els vuit: obren, porten manifest i porten contingut —

| id | pàgines | objectes | taules |
|---|---|---|---|
| 866 · 867 | 1 | 0 | — |
| 868 | 1 | 1 | — |
| 869–873 | 1 | 2 | `q8_grading` |

que és una **cadena d'edició real** i no vuit còpies: el document creix.

### El command, arreglat

`sembra_model_837.py` ja no pot repetir-ho: empaqueta amb `pack`, escriu per `o.fitxer.path` i
desa `mida_bytes`/`checksum` dels bytes reals. Qui el torni a córrer sobre un entorn net obtindrà
fitxers que s'obren.

---

**Idempotència:** 2a i 3a passada → `0 creacions`, recomptes intactes, 1 sol `Customer TRV`.

**API:** `/api/schema/` = **200** (860 KB) per `https` amb `Host: staging.fhorttextile.tech`.
`/api/v1/models/?search=TRV-SS27-0001` = 401 sense credencials, que és el correcte.
🚩 **Queda la comprovació visual a l'app amb el login manual d'Agus.**

---

## 9. Deute de catàleg (anotat, NO tocat)

El catàleg de POMs de staging **no s'ha modificat**. Aquests desajustos contra la foto de PROD
queden aquí documentats; el banc funciona igualment perquè cap toca els valors d'escalat.

### 9a. Els 4 sense ancoratge global — l'únic deute amb significat

| POM | nom | `pom_global` a la foto | a staging |
|---|---|---|---|
| `S` | Front armhole along seam | `LOSPOM-548` | **NULL** |
| `S2` | Back armhole along seam | `LOSPOM-549` | **NULL** |
| `BR` | Fly width | `LOSPOM-487` | **NULL** |
| `U4` | Flounce height | `LOSPOM-578` | **NULL** |

`S` i `S2` són **dos dels 21 POM mesurats** del model. Aquests 4 són també l'única causa de la
divergència de hash de §5. Efecte al banc: qualsevol prova que depengui de la traducció de
domini o de la federació veurà aquests 4 POM desancorats. Per a l'escalat, cap efecte.

### 9b. Soroll cosmètic — 26 POM més

- **`categoria`**: NULL a la foto, categoritzada a staging (`E`, `F`, `B`, `S`…). El catàleg de
  staging està **més al dia** que la foto de PROD en aquest camp.
- **`nom_client`**: MAJÚSCULES a la foto vs Title case a staging (`FLY WIDTH` ↔ `Fly width`).
- Dos que no són pura capitalització i val la pena mirar algun dia: **`E2`** (`11cm` ↔ `11 cm`)
  i **`I`** / **`GD`**, on la categoria de la foto porta un valor d'un altre vocabulari
  (`CAT-UB`, `Skirt / Dress`) en comptes d'un codi de categoria.

### 9c. No transcrit

`ModelTask.work_order` (comanda PROD #69, `commerce.WorkOrder`): no viatja a la foto i el camp
és nullable. Les 3 tasques del banc no tenen comanda associada.

---

## 10. Com reproduir el banc des de zero

```bash
cd /var/www/ftt-staging/backend
venv/bin/python manage.py sembra_model_837 --apply \
    --crea-entorn-absent --accepta-discrepancies-pom --accepta-ruleset-divergent
```

Les tres banderes són **decisions preses el 21/08**, documentades a §1. Sense elles el command
s'atura i les torna a preguntar — que és el que ha de fer si algú el corre en un altre entorn.

**Cap push.** Commits a `dev`, en local.
