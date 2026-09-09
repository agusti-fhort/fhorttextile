# IMPLEMENTACIÓ · SOBIRANIA DEL POM — font única, pany i edició

**Data:** 2026-08-22 · **Entorn:** staging `/var/www/ftt-staging`, branca `dev`
**Estat:** ✅ **ELS QUATRE TRAMS TANCATS** · 10 commits locals · **CAP PUSH**
**Gate:** banc de paritat 1383 ✅ (abans i després, 3 blocs) · `check` ✅ · `build` ✅ ·
i18n ca/en/es ✅ · QA de pantalla 20/20 ✅ · banc de sobirania 21/21 ✅

---

## 0 · El substrat que no hi era, i com s'ha suplert

> ⚠️ **`CENS_LOSPOM_FHORT_2026-08-22.md` NO ÉS AL DISC.** Ni a `docs/ordres/`, ni a
> `docs/diagnosis/`, ni enlloc del servidor (`find / -name 'CENS_LOSPOM*'` → buit; cap fitxer
> de menys de 24 h fora de dos logs de cron). El tram E del cens no s'ha pogut llegir.

L'ordre, però, descriu el defecte amb prou precisió (els dos noms de funció i el símptoma
literal), i els trams 1 i 3 **exigeixen un cens propi abans de construir**. S'ha fet aquest
cens des de zero, i és el que hi ha al §1.1. Si el document apareix, val la pena contrastar-hi
la llista: el que aquí es declara és el que s'ha mesurat al codi d'avui.

---

## 1 · TRAM 1 · FONT ÚNICA DEL CODI I DEL NOM

### 1.1 El cens (fet de nou) — 14 superfícies i dues lleis contràries

El defecte no eren dues implementacions: eren dues **lleis** contràries convivint, i una
d'elles contradient-se a si mateixa.

| Node | Llei que aplicava |
|---|---|
| `pom/models.py:454` `POMMaster.pom_code` | `codi_client or global.codi` → **TENANT guanya** |
| `pom/models.py:459,465` `name_cat` / `name_en` | `global.nom_* or nom_client` → **GLOBAL guanya** |
| `pom/serializers.py:97` `POMMasterSerializer.get_pom_code` | `global.codi or codi_client` → **GLOBAL guanya** |

🚨 **La contradicció més fina era DINS DEL MODEL**: `pom_code` feia guanyar el tenant i els
dos noms feien guanyar el global. Una mateixa fila podia sortir amb **el codi de la casa i el
nom del catàleg canònic** — mig POM de cada sobirà. La contradicció model↔serializer és la que
es veu de seguida; aquesta és la que hauria sobreviscut a un fix parcial.

Les 14 superfícies que resolien codi o nom, ara totes pel resolutor:

- `POMMaster.{pom_code,name_en,name_cat}` · `POMMasterSerializer` (5 mètodes)
- `GarmentPOMMapSerializer` · `_POMDisplayMixin` (família i grup) · `GradingRuleSerializer`
  · `CustomerPOMAliasSerializer` · `s2_serializers`
- `s4_views` (CSV de regles) · `s6_views` (HTM) · `s8_views` (export) · `s10_views` (fitting vs spec)
- `wizard_views`: `poms/cerca/` i `base-measurements/`
- `models_app`: `BaseMeasurementSerializer`, `poms/suggerits/`, `taula-mesures`,
  `graded-table`, `base-stages` i les cotes precedents (`pom_placement_views`)

**El que NO hi passa, a posta.** Els llocs que resolen un POM per **cercar-lo** —`_resolve_pom`
del paquet LOSAN, `find_pom_master`, tots els `filter(pom_global__codi=…)`— segueixen amb la
seva llei: allà el codi global és una **clau natural**, no una etiqueta per pintar. I els camps
que es diuen `*_global` (`pom_code_global`, `pom_global_codi`) segueixen servint el camp del
catàleg canònic tal com és: **el seu nom ja diu què són**, i una cadena de precedència amagada
darrere un nom que promet el global seria pitjor que la que hem tret.

### 1.2 El resolutor

`pom/nomenclatura.py` — al costat del que ja hi havia per a l'àlies, que és on tocava.

```
codi_de(pom, alias=None)         àlies.client_code  > codi_client       > global.codi
abreviatura_de(pom, alias=None)  àlies.client_code  > codi_client       > global.abbreviation
noms_de(pom, alias=None)         àlies.description_* > nom_client       > global.nom_en/nom_ca
categoria_de(pom)                                     categoria (FK)    > global.categoria (text)
```

Pur, cap consulta. Qui té context de client li passa l'àlies (`alies_per_pom`); qui no en té
—el catàleg, que és de la casa i no d'un client— el deixa a `None` i la cadena comença al
tenant.

### 1.3 El front

`nomenclaturaPom.js` tenia la cadena **invertida als dos últims graons**
(`… → pom_code_global → codi_client`). És el node exacte que imprimia «LOSPOM-548» a la fitxa.
Ara `… → codi_client → … → pom_code_global`: el global es queda a la cadena, **l'últim**, perquè
la promesa que la columna no surt mai buida segueix intacta.

🔑 **`cotaLabelDe` (TechSheetEditor) deia l'ordre BO i era l'única superfície que el deia** —
i per això la cota i la fila de Mesures podien discrepar: el que hi afegia de propi era
**saltar-se l'àlies del client**. Ara delega al resolutor i la còpia en línia mor.

### 1.4 Un efecte lateral que era un forat obert

`BaseMeasurementSerializer` (`models_app/serializers.py:434`) llegia **només** `pom.pom_global`.
En travessar un FK nul, DRF esborra el camp de la resposta (`SkipField`). Per als **144 POMs de
`fhort` —tots tenant-only—** aquest serializer **no deia ni el codi ni el nom**. Ara sempre hi són.

---

## 2 · TRAM 2 · EL PANY ALS IMPORTADORS

`load_losan_package._load_pom_masters` i `extend_pom_catalog` fan UPSERT sobre `codi_client`,
`nom_client`, `actiu`, `categoria` i `pom_global`. **Idempotents respecte del catàleg global i
destructius respecte del tenant**: una re-execució revertia la reparació feta a PROD.

I no ho hauria cantat res: **un upsert que reescriu el que ja hi havia no falla mai.** El POM
tornava al text del canònic i el següent que mirés la fitxa hauria vist «LOSPOM-548 · FRONT
ARMHOLE» un altre cop, sense saber d'on venia.

Ara, davant d'un POM amb la marca de sobirania: **el salten i el REPORTEN** (amb codi, nom i
pk). Mai un upsert silenciós — un conflicte de sobirania no és un error de l'importador, és una
decisió del tenant que aquests processos han de respectar i **fer visible**.

🔑 **La marca es busca pel CODI del global (`separat_de_global=pg.codi`), no pel FK.** La
separació justament el desfà: `filter(pom_global=pg)` no en trobaria cap.

**El test és la seqüència sencera contra la BD** (`test_sobirania_pany_importadors`): sembra →
separació → re-execució → el nom i el codi es queden, no s'ha fabricat cap POM nou al seu lloc,
i ho ha dit.

---

## 3 · TRAM 3 · SOBIRANIA PER COPY-ON-WRITE

### 3.1 El cens previ dels camps

| Camp | Hi era a `POMMaster`? |
|---|---|
| `codi_client`, `nom_client`, `categoria`, `notes`, `actiu`, `pendent_revisio`, `origen_import`, toleràncies | ✅ ja hi eren |
| `unitat`, `start_point`, `end_point`, `reference_point`, `scope`, `orientation`, `state`, `line`, `body_section` | ❌ **NOMÉS a `POMGlobal`** |

Per això «complementar la informació d'un POM propi» era **literalment impossible**: la pantalla
del catàleg ho pintava com a «no lligat al catàleg global» i **no hi havia on escriure-ho**.

### 3.2 La migració `0078` — additiva, `POMGlobal` intacte

Onze columnes, totes buides per defecte. Els nou del «com es mesura» amb els **mateixos
`choices` que `POMGlobal`, importats i no copiats**.

Més les dues de la marca: **`separat_de_global` + `separat_at`**.

> 🚨 **PER QUÈ CAL UNA MARCA I NO N'HI HA PROU AMB `pom_global IS NULL`.** Un POM nascut al
> tenant (els 144 de `fhort`, els que crea `poms/crear-tenant/`) **també** té `pom_global` a
> NULL. Els dos estats són **indistingibles per la columna del FK**, i sense marca els
> importadors no poden dir «aquest ja no és teu».

Aplicada amb `migrate_schemas` (mai `--schema`) i **auditada directament a la BD**: `public`,
`fhort` i `los` tenen les 11 columnes (22 en total a `pom_pommaster`).

### 3.3 El copy-on-write

`separa_del_global(pom)`: copia **el que el POM ENSENYAVA gràcies al global** (nom canònic, codi
—l'abreviatura del global si el tenant no en tenia—, i els nou camps), estampa la marca, i posa
`pom_global` a NULL. **NO fa `save()` a posta**: la separació és part de l'escriptura que la
provoca i ha d'entrar a la MATEIXA transacció, mai en una de pròpia que pugui quedar orfe.
Retorna els camps tocats perquè qui crida els posi al seu `update_fields`.

### 3.4 🔒 L'excepció, i per què NO és un forat: el NOM LOCAL

`POMGlobal` té dos noms (`nom_en` + `nom_ca`); `POMMaster` en té **un**. El primer test que ho
va tocar va sortir vermell i **la resposta correcta era canviar el test, no el codi**:

> **Decisió d'Agus, 09/08, vigent:** *la traducció de vocabulari de domini NO viu a la base de
> dades*. `nom_ca`/`nom_es` a `POMMaster` hi estan **explícitament descartats**, perquè el
> vocabulari tècnic del client no és dada de la casa i duplicar-lo crearia una segona font de
> veritat per mantenir a mà a cada tenant i cada catàleg nou.

O sigui que el nom local **no es perd en separar-se: CANVIA DE FONT**, i passa a
`TranslationCache` (`/api/v1/translate/pom/`, tram ⓘ del 13/08), que és on la casa ha decidit
que viu. Afegir un camp «per no perdre'l» hauria desfet aquella decisió **de passada, per un
efecte lateral d'aquest sprint**.

### 3.5 Què separa i què no

`CAMPS_QUE_SEPAREN` = `codi_client`, `nom_client`, `categoria` + els nou del «com es mesura».

Deixa fora `actiu`, `notes`, `pendent_revisio`, `origen_import` i les toleràncies: **desactivar
un POM del catàleg o anotar-hi una nota és administrar-lo, no redefinir-lo**, i separar-lo per
això obligaria a triar entre arxivar-lo i mantenir-lo lligat.

---

## 4 · TRAM 4 · LA PANTALLA I LA PORTA

### 4.1 🔴 Què era `PATCH /api/v1/poms/<id>/`

Un `ModelViewSet` **pelat**: `IsAuthenticated` per a tot, `fields='__all__'`, i **`pom_global`
ESCRIVIBLE**. Un tècnic —el rol més bàsic— podia amb un sol PATCH re-enganxar un POM a
qualsevol fila del catàleg global o desenganxar-l'hi, **sense decisió i sense traça**. És el
defecte d'aquest sprint vist per l'altra cara.

Ara: escriptura gated **CONFIGURE** (com `SizeSystemViewSet` i `SizeDefinitionViewSet`),
`POMMasterWriteSerializer` amb camps explícits, i `read_only_fields` **derivat de `_meta`**
perquè **una columna nova neixi READ-ONLY** — el defecte contrari, que neixi escrivible per API
sense que ningú ho hagi decidit, és exactament el que acabem de pagar.

**La separació hi passa**: si el PATCH toca un camp de `CAMPS_QUE_SEPAREN` d'un POM lligat,
`update` **separa PRIMER i escriu DESPRÉS**. L'ordre invers deixaria el valor editat trepitjat
per la còpia.

### 4.2 🪦 L'endpoint orfe: RETIRAT (i per què no reconduït)

`PATCH /api/v1/poms/<id>/nomenclatura/` — **zero cridadors** a `frontend/`,
`frontend-backoffice/` i `ops/`. I feia les tres faltes d'aquest sprint alhora:

1. **Cap validació d'unicitat.** `codi_client` té una constraint d'EXPRESSIÓ
   (`uniq_pommaster_codi_client_ci`) que DRF no tradueix sol → `IntegrityError` →
   `except Exception` → **500 amb el text cru del driver**, quan `validate_codi_client` ja dona
   un 400 que diu quin POM ocupa el codi.
2. **Cap gating.** `IsAuthenticated` per rebatejar el catàleg de la casa.
3. **Cap separació.** Rebatejava un POM lligat sense fer-lo sobirà.

**Retirat, no reconduït.** Fer-lo passar pel camí validat hauria estat escriure una segona
façana del mateix PATCH amb un altre nom d'URL i un altre contracte de resposta: la **setena**
ocurrència del patró que aquest sprint tanca. La manera de no repetir-la és que en quedi una.
La nomenclatura del CLIENT —el que aquest nom d'URL prometia i mai no va fer— viu on ha de
viure: `CustomerPOMAlias`.

### 4.3 La pantalla

`POMCataleg` guanya edició de nomenclatura, nom, família, unitat i «com es mesura».

- **L'esborrany surt del que la fitxa ENSENYA, no del camp cru.** Per a un POM lligat, el «com
  es mesura» que es veu és el del global i és el que el copy-on-write conservarà; si l'esborrany
  naixia buit, desar hauria semblat un canvi net i hauria estat un **esborrat silenciós de mitja
  fitxa**.
- **S'envia només el que ha canviat.** Tocar `codi_client` és el que SEPARA: enviar-lo sense que
  ningú l'hagi tocat **separaria POMs per desar una nota**.
- **Canviar de POM tanca l'edició** — arrossegar l'esborrany d'una fila a l'altra és el mode de
  fallada clàssic del patró.
- **L'avís de separació es dona ABANS de desar**, i només als lligats.
- **Vocabularis de la font única.** Els sis (`unitat`, `scope`, `orientation`, `state`, `line`,
  `body_section`) entren a `/api/v1/vocabulari/`, que existeix precisament perquè el front no
  se'ls escrigui a mà. *Un endpoint propi a `pom/` va arribar a estar escrit i es va retirar:
  hauria estat la mateixa falta amb un altre nom.*

**I els BOTONS segueixen el gating del servidor.** Amb el CONFIGURE al ViewSet, un tècnic
hauria vist els quatre botons d'escriptura i cada clic li hauria donat un 403: **una porta que
es veu oberta i no ho és és pitjor que una porta que no hi és.** Mateix patró que la resta de
pantalles gated de la casa. La LECTURA no es toca — el tècnic segueix veient la llista, la
fitxa sencera, l'ús observat i els àlies.

🚨 **I `estatCamp` canvia d'ordre.** Mirava `pom_global == null` PRIMER. Amb el tram 3, un POM
propi acabat d'omplir hauria seguit dient **«no lligat al catàleg global» amb el valor escrit al
davant i invisible**. Ara mana el VALOR: si n'hi ha, es diu.

---

## 5 · GATE

| Control | Resultat |
|---|---|
| `banc_paritat_1383` **abans** | ✅ A=105 · B=525 · C=4 · joc intacte |
| `banc_paritat_1383` **després** | ✅ A=105 · B=525 · C=4 · **els dos hashes IDÈNTICS** |
| `manage.py check` | ✅ net a cada commit |
| `npm run build` | ✅ net |
| i18n ca/en/es | ✅ paritat verificada (71 claus a `poms.cat` a les tres) |
| `npx eslint` (fitxers tocats) | ✅ 0 errors |
| `qa_sobirania_pom.py` (banc, BD viva) | ✅ 21 verds, **cap residu** |
| `qa_sobirania_cataleg_pantalla.py` (bundle real) | ✅ **20 verds** (dues passades: admin i tècnic) |
| Columnes de la `0078` a la BD | ✅ `public` · `fhort` · `los` |
| Suite `fhort.pom` + `fhort.models_app` | *(v. §7)* |

### 🚨 Per què el banc de paritat verd NO és un accident

Cap cel·la s'ha mogut perquè **el resolutor és de PRESENTACIÓ i el motor no en llegeix cap
camp**: `generate_graded_specs` i `propaga_ancoratges` treballen amb `pom_id`, `logica`,
`increment_base`, `breaks` i etiquetes de talla. El codi i el nom d'un POM no entren mai al
càlcul. Els dos hashes (joc i residents) surten idèntics.

### 🚨 I per què el banc de la BD viva necessitava una fixture

`fhort` té **144 POMMaster i tots amb `pom_global` a NULL** (0 `POMGlobal` al seu schema; els
125 canònics viuen a `public`). **A staging el codi vell i el nou donen exactament el mateix
resultat sobre les 144 files reals**: no hi ha cap POM lligat que els pugui delatar.
«LOSPOM-548 · FRONT ARMHOLE» és una fila de **PROD**.

Un verd contra les dades reals hauria **semblat** una prova i no ho hauria estat. Per això el
banc fabrica un POM lligat de debò, el mesura, i **el tomba** (transacció sempre-rollback, cap
`--apply`; l'últim assert és que ha desaparegut).

---

## 5-bis · 🚨 EL QUE EL GATE VA ENXAMPAR (i cap control estàndard veia)

### ① El «com es mesura» NO ERA ESCRIVIBLE — el desat s'hauria perdut en silenci

`POMMasterWriteSerializer` heretava de `POMMasterSerializer` «per no repetir la forma». Allà
els nou camps del «com es mesura» estan declarats com a `SerializerMethodField` —perquè la
LECTURA ha de passar per la cascada— i **un `SerializerMethodField` és read-only SEMPRE**.

Conseqüència: el formulari hauria enviat `start_point`, `scope`, `unitat`…, DRF els hauria
descartat sense piular, i la pantalla hauria desat amb **200 OK sense que passés res**. És el
mode de fallada que aquesta casa ja ha pagat dues vegades (`increment` a
`GradingRuleSerializer` i el motiu del seu `validate`), i hauria arribat a l'Agus com «l'edició
no funciona de vegades».

**Cap gate el veia**: `check` verd, `build` verd, i la **QA de pantalla verda** —només mesurava
el PATCH que s'ENVIA, no el que el servidor n'ACCEPTA. Ho va dir `serializer().fields`, mesurat
expressament.

> 🔑 **LLEI:** *un serializer d'escriptura NO hereda del de lectura.* `Meta.fields` tancat, i la
> LECTURA delegada per `to_representation`. Amb això `pom_global` deixa de ser «read-only» i
> passa a **no ser camp** — garantia més forta, perquè DRF ignora el que no és camp.

### ② Dos vermells del banc de la porta que no eren del producte

- **`APIClient()` sense `HTTP_HOST`** → `TenantMainMiddleware` resol el schema PUBLIC i
  `/api/v1/poms/` torna un **404**. No un 403 ni un 500: un **404**, que s'assembla prou a
  «l'endpoint no hi és» com per enviar la diagnosi al router.
- **`user.profile` CACHEJA** i `get_capabilities` llegeix d'aquell cau: sense rellegir l'usuari
  després de posar-li el rol, **l'admin rep 403 com si el gating fos massa dur**. Llei que ja
  tenia acta (J-consulta, 21/08) i que aquest banc va tornar a pagar. `test_gate_tenant_config._usuari`
  ja ho documentava tot: **el camí curt era llegir-lo abans d'escriure el banc.**

### ③ Una asserció contra `body` sencer va donar VERMELL amb el producte CORRECTE

La QA de pantalla feia `'LOSPOM-548' not in cos`… i la fila de l'últim recurs **l'ha
d'ensenyar**. Igual amb `FR AH` a la fitxa. Una asserció que llegeix tota la pàgina **no pot
distingir «hi surt on toca» de «hi surt on no toca»**. Assercions per FILA i per PANELL.

---

## 6 · ANOTAT (fora de scope, no tocat)

- 🚩 **`GarmentPOMMapSerializer` no s'ha convergit amb `_POMDisplayMixin`.** Diuen exactament el
  mateix i ara criden el mateix resolutor, però segueixen sent dues classes. Convergir-les toca
  un serializer viu amb ~100 lectors i aquest sprint no ho demanava. **La divergència ja no és
  possible** (el criteri és compartit); el que queda és duplicació de forma.
- 🚩 **`POMGlobal.is_key` no té equivalent al tenant.** `POMMaster.is_key_measure` torna `False`
  fix i `BaseMeasurementSerializer.pom_is_key` segueix llegint el global. Un POM sobirà perd la
  marca de «mesura clau» en separar-se. No entra al llistat de camps que l'ordre demanava
  (unitat + «com es mesura»); **cal decisió d'Agus** sobre si `is_key` és del catàleg global o
  de la casa.
- 🚩 **`POMGlobal.tol_prod_cm` / `tol_samp_cm` tampoc.** `POMMaster` té les seves
  (`tolerancia_default_*`), que són les que el domini fa servir; les del global queden com a
  informació de referència. Mateix cas, menys urgent.
- 🚩 **Els «tags» i els camps de formulari de `POMCataleg` són locals a la pantalla.** La casa no
  té ni un `Tag` de només-lectura ni un `Field` de fitxa; inventar-los aquí hauria estat un
  component nou de sistema en un sprint que no ho demana. Convergència òbvia, ja anotada al tram
  U1 i que segueix pendent.
- 🚩 **`nomsDePom` (front) manté `nom_client` a la cadena** encara que el backend ja el resolgui.
  És xarxa per als payloads que no passen pel resolutor (`taula-mesures` en serveix uns quants
  crus a posta). Retirar-lo demana censar-los un per un.

---

## 7 · COMMITS (10, locals, **cap push**)

```
5ed49bf8 test(pom): la porta del catàleg — el client va al DOMINI DEL TENANT i el perfil es rellegeix
d9cf23f9 fix(pom): el «com es mesura» no era escrivible — el desat s'hauria perdut en silenci
58cbb36f test(qa): la pantalla del catàleg — la llei i l'edició, contra el bundle real
6f17e312 test(qa): el banc de la sobirania del POM — la llei mesurada, sense deixar residu
d57736ce feat(cataleg): la pantalla de POMs guanya edició — nomenclatura, nom, família i «com es mesura»
fe5b004e fix(pom): tanca la porta d'escriptura del catàleg — CONFIGURE, camps explícits, i la separació
96f9c02b fix(import): el pany de sobirania — l'importador REPORTA i no toca
926fc4f1 feat(pom): sobirania — el POM se separa del global i passa a ser del tenant
a8fb2fac fix(fitxa): la nomenclatura del client mana sobre el codi canònic
be7bedf8 feat(pom): UNA font per al codi i el nom d'un POM — àlies > tenant > global
```

⚠️ **Sessions concurrents actives durant tot el tram.** Cada commit s'ha fet amb pathspec
explícit **i** s'ha verificat `git diff HEAD~1 HEAD --name-only` DESPRÉS de fer-lo: cap dels
10 s'ha endut cap fitxer aliè. (Llei del 21/08: el pathspec protegeix de l'índex aliè, no del
fitxer aliè.) Els fitxers que barrejaven dos trams —`nomenclatura.py` i `models.py`— s'han
partit a mà (còpia al scratchpad, retirada del bloc, commit, restitució) per no fer servir
`git stash`, que aquí està prohibit.
