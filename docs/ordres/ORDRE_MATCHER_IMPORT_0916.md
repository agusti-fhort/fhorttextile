# ORDRE MATCHER IMPORT · 16/09/2026

Patró B (implementació) sobre staging `dev` (`/var/www/ftt-staging`, `ftt-staging.service` :8001).
7 commits granulars, **cap push** (el fa l'Agus des de SSH). Verd a cada pas: `manage.py check`
abans de commit backend, `npm run build` + `eslint` abans de commit frontend, `git log -1` després
de cada commit, restart del servei després de cada canvi de BE.

HEAD de partida: `f4e8cb53` (branca `dev`, tal com deia la barana). HEAD final: `cc719273`.

---

## PAS 0 · VERIFICACIÓ (sense escriure)

### 0a. `find_pom_master` sencera i els seus cridadors

Transcrita i llegida sencera a `backend/fhort/models_app/extraction_views.py:1176-1311` (abans
del canvi). Confirmat contra el codi real:

- **Estratègies**: (a) àlies exacte del client → HIGH; (b) sinònim curat + `nom_client`/`nom_en`
  → HIGH/MEDIUM; (c) codi numèric + "lining" → MEDIUM; (c-bis) àlies `pendent_revisio` com a
  últim suggeriment → LOW; (d) fallback transitori per `codi_client` exacte i arrel → LOW.
- **La línia `nom in desc_base`** (estratègia 3, `description_match`): **confirmada**, era
  `if desc_base in nom or nom in desc_base` sense cap guard de nom buit.
- **El salt de l'àlies a POM inactiu**: **confirmat**, `if alias and alias.pom.actiu:` — si
  `alias.pom.actiu` era `False`, el `if` sencer era fals i el codi seguia sense deixar cap rastre
  que hi hagués hagut un àlies.
- **Consulta sense ORDER BY**: **confirmat** — les tres iteracions de candidats (estratègies 2,
  3, 4) eren `POMMaster.objects.select_related(...).filter(...)` sense `.order_by()`, iterades
  amb `for`. `POMMaster.Meta` no declara `ordering`.

**5 cridadors reals** (grep `find_pom_master(` fora de `def`/tests):
`fhort/pom/size_map_views.py:312,547` · `fhort/pom/dictionary_service.py:147` ·
`fhort/pom/services.py:747` · `fhort/models_app/extraction_views.py:1443` (la pròpia
`_match_rows`, el camí de l'import de models) · `fhort/models_app/management/commands/
sembra_banc_paritat.py:113`. (3 cridadors més als tests: `fhort/pom/tests.py` ×2,
`fhort/models_app/tests.py` ×1.)

### 0b. Calibratge del banc a staging

```sql
-- fhort: POMs actius amb nom_client buit
SELECT count(*) FROM fhort.pom_pommaster WHERE actiu=true AND (nom_client='' OR nom_client IS NULL);
→ 103   (de 144 POMs actius — CONFIRMA la magnitud citada al brief)

-- fhort: àlies que apunten a un POM inactiu
SELECT count(*) FROM fhort.pom_customerpomalias a JOIN fhort.pom_pommaster p ON p.id=a.pom_id
WHERE p.actiu=false;
→ 0

-- fhort: TOTS els POMs, per actiu
SELECT actiu, count(*) FROM fhort.pom_pommaster GROUP BY actiu;
→ actiu=t: 144   (CAP POM inactiu al schema fhort)

-- los (l'altre schema tenant): buit de tot (0 POMs, 0 àlies, 0 customers)
```

🚨 **Conseqüència directa per al banc**: a staging **no hi ha cap POM retirat de veritat** —
l'escenari «38 àlies BRW a POM retirat amb hereu, 43 sense hereu» és de PROD, no reproduïble
aquí. Precedent ja vist a la casa (sobirania POM, 22/08): **el banc s'ha de FABRICAR** dins
d'una transacció que sempre fa `savepoint_rollback` — mai dades persistents noves a staging.

Model **1216 NO existeix** a `fhort` (`SELECT id FROM models_app_model WHERE id=1216` → 0
files; 43 models en total, ids fins a 1502, dispersos). Client **BRW = Customer id 7** de
`fhort` (l'schema `los` no en té). El COMMIT 5 documenta aquest fet explícitament a la seva
sortida de comanda.

### 0c. On es crea un àlies i on es pinta la fila pendent

**Creació d'un `CustomerPOMAlias`** (cridadors NO-test):
- `fhort/pom/services.py:762` `maybe_learn_customer_alias()` — el camí de W5 (confirmació
  d'import), cridat des de `extraction_views.py` amb `model` ja en abast.
- `fhort/pom/wizard_views.py:934` — «crear POM propi» des d'un model (origen='MODEL'); `model_id`
  ja en abast.
- `fhort/pom/dictionary_views.py:163` — diccionari del client (origen='DICCIONARI'), NO lligat a
  cap model concret.

**Pintat de la fila pendent**: `frontend/src/components/ImportWizard/ImportWizard.jsx:1292-1400`
(el `.map` de `grup.items`). `pendent` (booleà JS) = `noMatch && weak_suggestion && !tenantOnly`.
El «hint» de suggeriment feble ja hi era (`weak_hint`/`many_to_one_hint`); calia afegir-hi la
línia de MOTIU i el sufix «après a X».

---

## COMMIT 1 · `b4ce62df` — `find_pom_master`: nom buit, ORDER BY, àlies retirat

**Diff**: `extraction_views.py` (+127/−?, funció reescrita), `size_map_views.py`,
`dictionary_service.py`, `services.py`, `sembra_banc_paritat.py` (els 5 cridadors reals
actualitzats a 4-tuple), `tests.py` ×2 (tests nous + 3 cridadors de test actualitzats).

**Canvis**:
1. `find_pom_master` passa de `(pom, match_type, confidence)` a
   `(pom, match_type, confidence, info)`, `info` sempre un dict amb `motiu`.
2. Estratègies 2/3/4: cada comparació de nom afegeix `if nom and ...` — un `nom_client`/`nom_en`
   buit ja no participa.
3. Totes les consultes de candidats porten `.order_by('id')`.
4. Àlies → POM inactiu: **ja no se salta**. Es busca l'hereu (POM actiu amb el mateix
   `pom_global_id` — **no** el mateix `codi_client`, que és únic per constraint de BD i mai el
   pot compartir un altre POM) i es retorna `(hereu_o_None, 'alias_pom_retirat', 'LOW',
   {'motiu': 'alies_pom_retirat', 'suggerit': hereu})`. La cerca **s'atura aquí**: no cau a
   `description_match`.
5. NO_MATCH final porta `motiu: 'sense_coincidencia'`.

**Curls (banc BRW fabricat, transacció sempre-rollback)** — reprodueix l'escenari del brief amb
dades pròpies ja que staging no en té:

```
PASS  alies_pom_retirat: motiu                          :: alies_pom_retirat
PASS  alies_pom_retirat: mai auto-vincula (conf LOW)     :: LOW
PASS  alies_pom_retirat: suggerit és l'hereu             :: (pom hereu, mai el retirat)
PASS  alies_pom_retirat: match_type                      :: alias_pom_retirat
PASS  sense_hereu: pm és None / motiu / suggerit=None    :: 3/3
PASS  sense_coincidencia: pm None / motiu / match_type / conf :: 4/4
PASS  nom_buit: no atrapa descripcions arbitràries       ::
PASS  4 files no col·lapsen al mateix POM                :: 4 POMs diferents
TOTAL 14 FAILS 0
```

Verificat a la BD (abans/després idèntic): `fhort.pom_pommaster`=144, `fhort.pom_customerpomalias`=154.

`manage.py check` net → `systemctl restart ftt-staging` → verd.

---

## COMMIT 2 · `b916c2cb` — migració `CustomerPOMAlias.model_origen`

`AddField`, FK nul·lable a `models_app.Model`, `on_delete=SET_NULL`, `db_constraint=False`
(mateix creuament de schema que `customer`: `models_app` és TENANT-only, `pom` viu també a
`public`). Migració `0087_alies_model_origen.py`.

```
$ manage.py migrate_schemas pom
Applying pom.0087_alies_model_origen... OK   (×3: public, fhort, los)
```

Auditat per `\d` als tres schemas — columna `model_origen_id bigint NULL` present als tres, cap
FK constraint de BD (com correspon). `SELECT count(*), count(model_origen_id) FROM
fhort.pom_customerpomalias` → `154, 0` (els 154 àlies existents queden amb origen desconegut).

---

## COMMIT 3 · `40fdeff5` — àlies amb origen i contradicció (2a migració, APROVADA)

⚠️ **Decisió d'Agus enmig del tram** (vegeu transcripció completa a la conversa): la unicitat de
`CustomerPOMAlias` passava de `(customer, client_code)` a `(customer, client_code, pom)` —
imprescindible perquè el matcher pugui veure ≥2 àlies del mateix codi amb POMs diferents. Això
és una **segona migració**, fora de la barana original («UNA, aprovada»). Es va presentar la
tensió a l'Agus (amb 2 alternatives sense migració, cap satisfeia literalment el curl del brief)
i **va aprovar explícitament l'opció amb 2a migració**, amb 4 condicions — totes complertes:

1. Migració additiva (`unique(customer, client_code)` → `unique(customer, client_code, pom)`).
   ✅ Migració `0088_alies_unicitat_amb_pom.py`, llegida abans → `migrate_schemas` → `\d`
   auditat als 3 schemas. Additiva confirmada: cap fila viva tenia mai 2 `pom` pel mateix codi.
2. `find_pom_master`: ≥2 files pel mateix codi amb POMs diferents → pendent
   `alies_contradictoris` amb la llista `{pom, model_origen}` de TOTES; 1 sola fila →
   comportament normal. ✅
3. `wizard_views.py:862` (pom-propi): la regla «no crear un POM amb un codi que ja té àlies» es
   manté com a validació d'APLICACIÓ (`colisio_de_codi`), ja no com a xarxa de seguretat de BD.
   ✅ Verificat (banc + test): `colisio_de_codi` segueix detectant el codi ocupat.
4. Cap altra migració. ✅ (0089 no existeix.)

**Efecte col·lateral trobat i corregit al mateix commit** (Postgres tracta cada `NULL` com a
distint dels altres): sense un índex parcial, la constraint composta hauria permès clonar
l'àlies «pendent de mapar» (`pom=NULL`) del mateix codi. Afegit
`UniqueConstraint(customer, client_code, condition=Q(pom__isnull=True))` a LA MATEIXA migració.

**Altres efectes col·laterals de la constraint més laxa, corregits al mateix commit**:
- `dictionary_views.py:163` — `update_or_create(customer=, client_code=)` era un lookup MÉS CURT
  que la nova unique → hauria petat amb `MultipleObjectsReturned` si el codi ja arrossegava una
  contradicció (el mateix mode de fallada de la llei de memòria
  `ftt-lookup-curt-no-peta-segresta`, aquí en la seva forma inversa: no segresta, PETA). `pom`
  hi entra a la cerca.
- `nomenclatura.alies_del_codi:96` — `.first()` sense `order_by` → afegit.

**Curls (banc fabricat)** — reprodueix LITERALMENT l'escenari del brief:

```
crear àlies EP a model A → POM X ................ PASS (model_origen=A)
a model B, vincular EP → POM Y ................... PASS (FILA NOVA, A intacte a X)
importar EP a model C ............................ PASS pendent 'alies_contradictoris'
    candidats = [X(model A), Y(model B)] .......... PASS (2 candidats, tots dos)
re-aprendre (EP,X) des d'un 3r punt ............... PASS (retorna LA MATEIXA fila, no en crea 3a)
colisio_de_codi encara bloqueja el codi ocupat .... PASS
TOTAL 16 FAILS 0
```

`manage.py check` net → `migrate_schemas pom` (×3 schemas) → restart → verd.

---

## COMMIT 4 · `4525b0c8` — comanda `repunta_alies_retirats`

`manage.py repunta_alies_retirats --customer <codi> [--apply]`. Dry-run per defecte, taula
`codi · POM retirat · hereu · acció`. Per cada àlies del client a POM inactiu: hereu (mateix
`pom_global` actiu) trobat → `REPUNTAR` (`--apply`: `pom=hereu`, `origen='REPUNT_v5'`,
`editat_at`=ara); sense hereu → `SENSE HEREU` (no es toca); ja existeix una fila bessona
`(customer, client_code, hereu)` → `JA REPUNTAT` (no es toca ni es duplica, queda per revisió
manual — evita xocar amb la constraint nova).

**Banc fabricat** (`call_command` a la mateixa connexió/transacció, rollback en sortir) — 3 casos:

```
DRY-RUN: no escriu res, llista REPUNTAR / SENSE HEREU / JA REPUNTAT correctament .. 4/4
APPLY: cas 1 (amb hereu) repuntat, origen=REPUNT_v5 ................................ 2/2
APPLY: cas 2 (sense hereu) intacte .................................................. 1/1
APPLY: cas 3 (bessona existent) cap de les dues es toca ............................ 2/2
resum final correcte ................................................................ 1/1
TOTAL 10 FAILS 0
```

**Dry-run real sobre BRW a staging**:
```
$ manage.py tenant_command repunta_alies_retirats --schema=fhort --customer BRW
Total: 0 · a repuntar: 0 · sense hereu: 0 · ja repuntats/bessons: 0
```
(0 files — coherent amb 0b: `fhort` no té cap POM retirat avui.)

---

## COMMIT 5 · `02160f2d` — comanda `desvincula_description_match`

`manage.py desvincula_description_match --model <id> [--pom <codi>] [--since AAAA-MM-DD]
[--apply]`. Sense `--model`: CENS per model (recompte agrupat, cap escriptura). Amb `--model`:
llista/desactiva (soft, `is_active=False`, mateix mecanisme que la poda de W5, amb entrada a
`MeasurementChangeLog`) les `BaseMeasurement` d'aquell model que apunten al `--pom` indicat (o,
sense `--pom`, a qualsevol POM amb `nom_client` buit). **Res s'esborra**: `nom_fitxa` i `notes`
(la descripció original) es conserven intactes; el `pom` de la fila tampoc es toca (és soft).

🚨 **Avís explícit a la sortida** quan no es dona `--pom`: el criteri «POM amb nom buit» és
l'estat NORMAL de 103 dels 144 POMs actius (no un símptoma) — `--apply` sense `--pom` ni
`--since` desactivaria mesures BONES a l'engròs.

**Model 1216 no existeix a staging** (confirmat a 0b) — el banc reprodueix l'escenari amb un
model i un POM fabricats.

**Banc fabricat** (`call_command`, rollback en sortir):

```
CENS (sense --model): veu els DOS models afectats (el dolent i un altre), cap escriptura .. 3/3
DRY-RUN: llista la fila dolenta, no la toca, no llista la bona d'un altre POM .............. 3/3
APPLY: la dolenta es desactiva; nom_fitxa i notes intactes; pom NO es toca (soft) .......... 4/4
APPLY: la bona (altre POM) i la d'un altre model NO es toquen .............................. 2/2
APPLY: deixa rastre a MeasurementChangeLog .................................................. 1/1
sense --pom: també agafa les de nom buit .................................................... 1/1
TOTAL 14 FAILS 0
```

**Cens real sobre `fhort`** (sense `--pom`, per veure l'abast normal — NO s'ha aplicat res):
```
$ manage.py tenant_command desvincula_description_match --schema=fhort
Total: 435 fila(es) repartides en 32 models (BANC-01…27, BRW-FW26-*, TRV-SS27-0001…)
```
Confirma la lectura de 0b/COMMIT 5: aquest volum és l'estat normal del catàleg (POMs lligats al
canònic sense bateig propi), no un incident — l'ús real de la comanda ha de portar sempre
`--pom` (o `--since`) acotant a la importació concreta que es vol desfer.

---

## COMMIT 6 · `cc719273` — pantalla d'importació: motius i origen de l'àlies

`ImportWizard.jsx`: la fila pendent (o la de «sense match») mostra ara una línia `--text-soft`
amb el motiu quan el backend en dona un:
- `pendent` (amb hereu): **"àlies a POM retirat · hereu: X"**
- «sense match» (sense hereu): **"àlies a POM retirat · sense hereu"**
- «sense match» sense res: **"sense coincidència per descripció"**
- «sense match» amb ≥2 candidats: **"àlies contradictoris: X (model A) · Y (model B)"** (llista
  tots els candidats, no només 2)

El suggeriment d'un àlies (línia de «confiança baixa, suggeriment: X») porta ara **"· après a
NOM MODEL"** quan `find_pom_master` sap de quin model es va aprendre (`alias_pendent_revisio` i
`alias_pom_retirat` amb hereu).

Backend previ (`3018daf1`, no numerat com a commit propi del brief però necessari per servir la
dada): `find_pom_master` exposa `info['suggerit_origen_id']`/`['suggerit_origen_nom']`;
`_match_rows` ho porta a la fila com a `weak_suggestion_model_origen`.

i18n ca/en/es amb 6 claus noves, paritat i placeholders verificats (script Python de
comparació + revisió per agent independent). Tokens `NORMA_LAYOUT` (`--text-soft`, `--fs-label`)
— sense maqueta nova, conformitat sobre les línies existents. `npm run build` + `eslint` nets.

**Revisió independent** (agent guardia-ui + revisor-diff, sense accés d'escriptura): **VERD**.
Única observació — `key` del `.map` de candidats podia col·lidir amb `pom_id` duplicat sota
`client_code__iexact` distint (escenari marginal, no introduït per aquest diff) — aplicada la
correcció (`key={`${c.pom_id}-${i}`}`) abans de committar.

---

## Estat final

```
$ git log --oneline -7
cc719273 feat(import-wizard): motius visibles i origen de l'àlies a la pantalla d'importació
3018daf1 feat(pom): find_pom_master porta l'origen del suggeriment d'àlies (prep COMMIT 6)
02160f2d feat(models_app): comanda desvincula_description_match
4525b0c8 feat(pom): comanda repunta_alies_retirats
40fdeff5 feat(pom): àlies amb origen i detecció de contradicció entre models (COMMIT 3)
b916c2cb feat(pom): CustomerPOMAlias.model_origen
b4ce62df fix(pom): find_pom_master no salta àlies a POM retirat, nom buit, ORDER BY
```

Servei `ftt-staging` reiniciat i verd després de cada commit backend. `frontend/dist`
reconstruït (staging el serveix directament — `npm run build` ÉS desplegar). Cap push.

## Pendent / a revisar per l'Agus

1. **La 2a migració (0088)** és fora de la barana escrita original; es va aprovar explícitament
   enmig del tram (vegeu COMMIT 3). Revisar-la en el `git show 40fdeff5` abans de push.
2. **`REPUNT_v5`** com a valor de `CustomerPOMAlias.origen` NO s'ha afegit a `ORIGEN_CHOICES` del
   model (per no obrir una 3a migració per un canvi purament de metadades/`choices`, que Django
   no valida a `.save()`). Funciona, però l'admin de Django no el llistaria bonic al desplegable.
   Si es vol polir, és una migració trivial (`AlterField`, sense canvi d'esquema) a fer junts amb
   la propera que toqui aquest model.
3. **`desvincula_description_match` sense `--pom`** és deliberadament ampli (avisa a la sortida);
   l'ús real hauria d'anar sempre amb `--pom <codi>` (i idealment `--since`) acotat a la
   importació concreta que es vol desfer — mai a l'engròs.
4. **Model 1216 i el banc BRW real (38/43 àlies) no existeixen a staging**: tota la verificació
   d'aquest tram s'ha fet amb bancs fabricats (transacció sempre-rollback). El comportament amb
   les dades reals de PROD s'ha de confirmar al desplegament.
