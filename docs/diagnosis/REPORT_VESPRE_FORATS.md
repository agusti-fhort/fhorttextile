# REPORT · el vespre dels forats · 2026-08-06 (V1-V6)

> **Data** 2026-08-06 vespre · **Patró B (IMPLEMENTACIÓ)** amb l'Agus present · staging
> `/var/www/ftt-staging`, branca `dev`. **Cap push** (el fa ell).
> **Base:** `04156084` (els 5 commits de la tarda) → **HEAD final `ea483439`**, 8 commits nous.
> Referència del que es venia a tancar: [`ARQUITECTURA_2026-08-06.md`](ARQUITECTURA_2026-08-06.md),
> actualitzat amb l'estat de cada punt.

---

## 0 · RESUM

| tram | què | commit | verd |
|---|---|---|---|
| **V1** | F1-bis: el permís i la destrucció miren el mateix (+ la 2a porta, «Sense graduació») | `d6c1a9db` | `check` net · `tests_sembra_grading` **84/84** (77+7 de noves) |
| **V3** | l'exclusió del tècnic també val per la porta del relleu | `38931d59` | suite `fhort.tasks` **239/239** |
| **V5a** | el modal de desfer: Esc + focus gestionat | `77dc0d5a` | eslint 0 errors (mateix perfil) · build net · P0.8 i P0.2 verds |
| **V5b** | el castellà acaba de parlar de RUPTURA | `d49a995c` | `json.load` net · build net |
| **V2-codi** | el wizard només deriva el target quan és UNÍVOC | `f91253e7` | `node --test` **154/154** · build net |
| **V4** | staging es queda sense models: els 46 de `fhort` i el seu rastre | `af2b16dc` | **0 orfes** · catàleg i `los` intactes |
| **V2-dada** | el que era FALS al catàleg fora; l'AMBIGU documentat | `0abe0456` | idempotent verificat |
| **V6** | les dues col·lisions que ha obert la nit mateixa | `ea483439` | 11 fums de navegador verds |

**Dues decisions preses per l'Agus aquesta nit**, totes dues amb el cens al davant:
1. **Les dues portes destructives de graduació tenen el mateix tracte** (V1). «Sense graduació» diu
   que desacobla el joc, no que s'endugui les regles escrites a mà: com que les mata, ha de demanar
   permís amb el recompte davant.
2. **S'esborren els 46 models de `fhort`** (V4), assumint que el corpus de temps queda a 0.
3. I el criteri de V2-dada: **FALS s'esborra · AMBIGU es documenta i es resol amb domini davant.**

---

## 1 · V1 · F1-bis — el permís i la destrucció miren el mateix

**El defecte.** Dos predicats per al mateix acte: el 409 de D-31.4 mirava el **payload**
(`views.py:1049`) i el wipe-and-recreate mirava l'**estat del model** (`views.py:1071`). El
destructiu era el més ample → qualsevol `update-step2` sobre un model amb joc reescrivia les
residents i es menjava les `MANUAL` **sense 409, sense Watchpoint i sense que la resposta ho digués**.

**La llei.** Un sol predicat: `canvia_joc` = la clau entra al payload **i** el valor és un altre.
`grs_abans` es captura abans que el resolutor assigni res (a partir del `setattr` el model ja porta
el valor nou i la pregunta ja no es pot respondre). **El motor no es toca**: només canvia QUAN es crida.

**La segona porta.** «Sense graduació» (`grading_rule_set_id: null`) també esborrava amb 200 OK.
Ara demana el mateix 409 i escriu el seu Watchpoint (`tipus='desacoblat_graduacio'`, amb el joc del
qual es desacobla). El `tipus` del 409 és el **mateix** (`esborrat_residents`) a posta: el fet és
idèntic i `useConfirmacioRuleset.FLAG_PER_TIPUS` ja el sap gestionar → **zero canvis de frontend,
zero i18n**. El que canvia és la causa, i viu al `message`, que el redacta el backend.

**Els 4 tests que el brief demanava, i 3 més:**

| test | què fixa |
|---|---|
| `test_un_patch_que_no_parla_de_graduacio_no_toca_cap_regla` | (a) compara **els mateixos ids** de regla, no el recompte: un wipe-and-recreate deixaria el mateix nombre de files amb ids NOUS |
| `test_canviar_de_joc_amb_MANUAL_vives_avisa_amb_recompte` | (b) 409 amb `residents` i `per_origen` |
| `test_canvi_de_joc_confirmat_esborra_i_deixa_watchpoint` | (c) |
| `test_reenviar_el_mateix_joc_no_toca_res_ni_rebota` | (d) no-op: ni 409, ni materialització, ni rastre |
| `test_desacoblar_amb_residents_demana_permis` · `..._confirmat_esborra_i_deixa_el_seu_rastre` · `..._sense_residents_no_frega` | la 2a porta |

**Un detall del fixture que val la pena saber:** un `GradingRuleSet` **sense `origen` classificat
materialitza les seves residents com a `MANUAL`** (`origen_mgr_des_de_ruleset`). Els jocs dels tests
porten `origen=CLIENT_RUN` explícit perquè «el que ve del joc» i «el que ha escrit el tècnic» no es
diguin igual. **Auditat a dades vives abans d'esborrar-les:** les 24 MANUAL de `fhort` NO venien
d'aquest camí (model 186 → joc 107 amb `origen=IMPORT`; model 1308 → joc 219 amb `CLIENT_RUN`), o
sigui que eren autoria real — o del blur que va tancar el commit 67.

**🔴 El que NO tanca V1** (i per què): el wipe sense filtre d'`origen` viu a **tres camins més** —
`copiar_de_model` (`views.py:1650`), reimport W5 (`extraction_views.py:2737`) i el command
`migra_brownie_ruleset`. V1 arreglava el PREDICAT, no el motor. Protegir les MANUAL dins de
`materialize_model_grading_rules` és la **decisió 6.1**, oberta.

---

## 2 · V3 · l'exclusió del tècnic, també per la porta del relleu

F1.5 va ancorar D-6 a **qui treballa** (`TimerEntrada.tecnic`) i el va tancar a `transition_task`.
**El relleu no hi passa**: `claim` (`views_b.py:523`) i la branca de handoff d'`open-task`
(`views_b.py:598-608`) criden `traspassa_tram` sense transició —correctament, perquè el relleu no
canvia l'estat— i `_open_timer` només tanca els trams **d'aquesta tasca**. Un tècnic que ja
treballava en una altra i es quedava aquesta acabava amb **dos trams oberts**.

**Per què va sobreviure:** els cinc tests de handoff parteixen sempre de B **sense** feina pròpia.

**El fix.** El bucle surt de `transition_task` i passa a `_aplica_exclusio_tecnic(profile, task)` —
punt únic—, i el relleu el crida abans d'obrir el seu tram. Dos fets, dues files de log que no es
confonen: la feina que es deixa queda `auto='exclusio_inprogress'` i el relleu manté `auto='handoff'`.

**3 tests nous**, el primer parteix de B ja treballant (el forat), el segon separa les dues files de
log i el tercer fixa que l'exclusió **no** toca la feina d'altres tècnics (D-8 segueix valent).

🟡 **Anotat, no fet (XS):** `traspassa_tram` no retorna quina tasca ha pausat, o sigui que la
resposta de `claim`/`open-task` no ho pot dir com sí que fa `transition` amb `paused_task_id`.
Canviar-ho toca la firma i dues vistes.

---

## 3 · V5 · els dos petits

**V5a.** El commit 57 va treure l'Esc del modal de posicions amb una llei escrita —«cap modal de la
casa pot ser un cul-de-sac de teclat»— i el modal de DESFER (commit 59) va néixer dos dies després
sense ella, amb el mateix vel `fixed inset:0` que intercepta tots els clics de sota. Ara Esc el
tanca. **I el focus, que aquí no és cosmètic:** en obrir-se va al botó de CANCEL·LAR i no al de
confirmar —aquest modal retira germanes amb valor pres i deixar el gest destructiu sota l'Enter és
convidar-hi— i en tancar-se torna d'on venia. Amb `role="dialog"`, `aria-modal` i `aria-labelledby`.

**V5b.** `Δ break`→`Δ ruptura` (:2592, :3549), `Delta break`→`Delta de ruptura` (:3274, :3276) i
`{{count}} con break`→`con ruptura` (:3520).
**No es toquen, i no és oblit:** `regle_break` (:2578) i `tbl_col_break` (:3051) valen «Break» als
**tres** idiomes. Un text idèntic a ca/en/es no és una traducció pendent: és la convenció de **dada
de domini** del `CLAUDE.md` (com LINEAR/STEP). El que distingia «Talla break» era justament que
l'anglès **sí** el traduïa («Break size»).

---

## 4 · V2 · la causa arrel del model 1307, a les dues capes

### 4.1 · CODI — el wizard només deriva quan la família ho diu sense ambigüitat

`DerivaTarget` agafava «el primer que el catàleg declara», i l'ordre d'aquella llista no té res a
veure amb el model: la consulta va **sense `customer_codi`** i l'ordre acaba sortint del nom del
sistema de talles. Amb dades vives donava `KID_BOY` a `JERSEY_TOPS` i `TAILORED_PANTS` —famílies
que també serveixen MAN i WOMAN— i el pas 3 hi preseleccionava un run de nen amb base 6 o 7.

La decisió surt del component i passa a `utils/derivaTarget.js` per poder-la provar amb `node --test`
com `destiTasca.js`. **6 tests** amb els perfils reals, inclòs el que fixa que **l'ordre de la
llista ja no decideix res** (amb la llista invertida, el resultat és el mateix).

**Una col·lisió que obre el propi fix, tancada al mateix commit:** sense target, el pas 3 deia «Cap
sistema disponible per aquesta combinació», que era **fals** —no falta cap sistema, falta dir per a
qui és la peça— i amb la derivació restringida aquesta branca passa a veure's sovint. Clau nova
`model_wizard.no_target` als 3 idiomes; `no_sizes` es queda per a l'altra branca (:763), on sí que
és certa.

### 4.2 · DADA — FALS s'esborra, AMBIGU es documenta

**Esborrats: 9 `SizingProfile`** que reclamaven un target que el seu propi `SizeSystem` no declara
servir. S'esborra el **perfil** i no s'amplien els `targets` del sistema: ampliar-los seria
inventar-se un fet sobre el sistema per fer quadrar l'altre.

| perfil | família | estat | target | sistema | el sistema serveix |
|---|---|---|---|---|---|
| 519 · 520 · 522 | `SWEATSHIRTS_MIDLAYERS` | **ACTIVA** | BABY_GIRL · BABY_BOY · KID_BOY | `GIRL_LOS_03` | KID_GIRL |
| 377 · 389 | `T_SHIRT` | desactivada | NEWBORN_BOY · NEWBORN_UNISEX | `BABY_EU_CM` | NEWBORN_GIRL |
| 407 | `DRESS` | desactivada | NEWBORN_UNISEX | `BABY_MONTHS` | NEWBORN_GIRL |
| 425 · 449 · 473 | `T_SHIRT` | desactivada | BABY_BOY · KID_BOY · TEEN_BOY | `TODDLER_EU` · `KIDS_EU` · `TEEN_ALPHA` | BABY_GIRL · KID_GIRL · TEEN_GIRL |

**Esborrat: el punter V1 de l'item 4 `shirt_woven`**, que apuntava a `ALPHA_EU_M` (home) mentre la
seva família `BUTTONED_TOPS` serveix TEEN_BOY i WOMAN — **MAN no hi és**. Zero pèrdua: el seu
`ItemBaseSet` (V2: `ALPHA_EU_M`, base L, fit REGULAR) diu el mateix i V2 mana sobre V1 a
`resolve_item_base_set`.

**NO es toquen (AMBIGUS, no falsos):** items 5 `blouse`, 10 `top_sleeveless`, 58 `baby_dress`.
Apunten al sistema d'un públic que la seva família **sí** serveix i **no tenen cap `ItemBaseSet`**
que els cobreixi: treure'ls el default els deixaria sense sembra de talla base. Trencar
funcionalitat vigent per higiene és el tracte equivocat — ho resol el catàleg v4, amb la Montse.

**Comprovació de col·lisió (cap família s'ha quedat sense cobertura):** `SWEATSHIRTS_MIDLAYERS`
conserva KID_GIRL i WOMAN. Les 10 famílies actives amb 0 perfils ja hi eren abans (és la R1 de
`DIAGNOSI_TAXONOMIA`, no un efecte d'aquesta nit).

🟡 **Obert:** `SizingProfile` segueix **sense `clean()` ni constraint** (`pom/models.py:1480-1533`).
Res impedeix tornar a escriure demà un perfil com els nou d'avui.

---

## 5 · V4 · staging es queda sense models — ANNEX D'AUDITORIA SQL

### 5.1 · El cens, com a acta del que hi havia (abans d'esborrar)

```
TENANT «fhort» · 46 models · 21 aguanten el corpus de temps · 25 nets

🛑 AGUANTEN EL CORPUS DE TEMPS (D-3) · 21 models
   id ref                    nom                      cli   mes  regl  fit  tsq  c/t    min albarà
  162 BRW-SS26-0001          OLIVIA DRESS             BRW    16   114    2    3    3   1012 —
  163 BRW-FW26-0001          Blusa TATE Crudo         BRW    25   114    1    6    3   3780 —
  164 BRW-FW26-0002          Blusa CLIMENTA           BRW    37   114    1    5    3     39 —
  165 BRW-FW26-0003          Blusa RUFUS STARS        BRW    37   114    1    6    1      9 —
  166 BRW-FW26-0004          Blusa MEREDITH           BRW    37   114    1    7    1      1 —
  167 BRW-FW26-0005          Blusa OWEN               BRW    37   114    1    5    2    245 —
  168 BRW-FW26-0006          Vestido LEXI             BRW    35   114    2    5    1      2 —
  169 BRW-FW26-0007          Top AMELIA               BRW    29   114    2    6    1    488 sí
  170 BRW-FW26-0008          Short BERLIN Rayas       BRW    22   114    2    5    1     11 —
  172 BRW-FW26-0010          Pantalón RICHARD         BRW     0   114    1    5    1      2 —
  174 BRW-FW26-0012          Blusa CALLIE             BRW    21    17    1    6    2    849 —
  177 BRW-FW26-0015          Blusa JAMIE              BRW     0   114    1    5    1     98 —
  182 BRW-26-SS-0002         [QA-SC] OLIVIA DRESS     BRW    14   114    4    3    3    727 sí
  185 FTT-FW27-0001          Test camisa              FTT     3    35    2    4    3    955 —
  186 FTT-CO27-0001          Test pantaló             FTT    20    20    0    4    3   1553 —
  188 BRW-SS27-0001          ROSALIA                  BRW    13   114    1    3    2     44 EMÈS
  268 BRW-FW27-0001          Blusa POP                BRW    48   114    0    1    1     28 —
  269 BRW-FW27-0002          POP                      BRW    25   114    0    1    1      4 —
 1302 FTT-SS26-0001          Test Agus                FTT     6    34    0    1    1      5 —
 1307 BRW-SS26-0002                                   BRW    34     0    0   12    6    179 —
 1308 BRW-SS26-0003          MILEY                    BRW    12   117    1    3    3    131 —
TOTAL                                                       471  1933   24   96   43  10162

NETS · 25 models (171 · 173 · 175 · 176 · 247…267)
TENANT «los» · 51 models · 0 aguanten el corpus · 51 nets   ← NO S'HI HA TOCAT
```

### 5.2 · L'esborrat i l'auditoria de zero-orfes

| taula | abans | després |
|---|---|---|
| Model | 46 | **0** |
| BaseMeasurement | 691 | **0** |
| MeasurementChangeLog | 228 | **0** |
| ModelGradingRule | 4.783 | **0** |
| SizeCheck (+ línies) | 14 (+107) | **0** |
| Watchpoint | 69 | **0** |
| FittingSession | 28 | **0** |
| SizeFitting | 48 | **0** |
| PieceFitting (+ línies) | 9 (+295) | **0** |
| ModelTask | 117 | **0** |
| TimerEntrada | 253 | **0** |
| TaskTransition | 529 | **0** |
| ConsumptionRecord | 23 | **0** |
| ModelFitxer | 304 | **0** |

```
AUDITORIA · orfes que apunten a un model inexistent
   ✓ BaseMeasurement 0 · MeasurementChangeLog 0 · ModelGradingRule 0 · SizeCheck 0
   ✓ Watchpoint 0 · FittingSession 0 · SizeFitting 0 · PieceFitting 0 · ModelTask 0
   ✓ ConsumptionRecord 0 · ModelFitxer 0
   ✓ TimerEntrada (sense tasca) 0 · TaskTransition (sense tasca) 0
   TOTAL ORFES: 0
```

**El que NO s'ha tocat, verificat després:**
`POMMaster` 396 · `CustomerPOMAlias` 390 · `GradingRuleSet` 47 · `GradingRule` 1.288 ·
`GarmentType` 21 · `GarmentTypeItem` 62 · `SizeSystem` 28 · `SizeDefinition` 175 ·
`SizingProfile` 37 (46 − 9 de V2-dada) · `TaskType` 15 · `TimeSeed` 8 · `Customer` 3.
**`los`: 51 models intactes.** El schema `public` no s'ha tocat.

**Sobreviuen amb `model=NULL` PER DISSENY** (no són orfes penjants, són el que l'esquema decideix):
24 `ImportSession` · 8 `AIUsage` (comptabilitat de cost real) · 37 `BulkCollectionRow` ·
4 `DeliveryNoteLine`.

### 5.3 · La paret de l'albarà: no s'ha desmuntat, i no calia

`te_paret_albara` (`tasks/services_c.py:44`) és un guard de **transició d'estat de tasca**, no
d'esborrat: no bloqueja res d'aquí i es queda intacta per a la vida real. I
`DeliveryNoteLine.model` és **SET_NULL**, o sigui que el model 188 (albarà `DN-2026-0001`, ISSUED)
s'ha esborrat sense forçar res.
🔴 **No s'han esborrat línies ni albarans**: deixaria un document EMÈS amb un total que no quadra
amb les seves línies, i un document incoherent és pitjor que un enllaç a NULL. Els dos albarans
(`DN-2026-0001` ISSUED i `DN-2026-0002` DRAFT) queden amb les seves 4 línies i `model=NULL`.

### 5.4 · Els dos bloquejants PROTECT

`SizeCheck.model` i `PieceFitting.model` són PROTECT i s'han retirat explícitament abans (les seves
línies cauen per CASCADE des d'ells). `WorkOrder.model` també és PROTECT, però les 5 files el tenen
a NULL: no bloquejava.

### 5.5 · Còpia de seguretat — **l'única foto dels 46 models amb el seu corpus**

```
/root/backups/ftt_staging_fhort_pre_V4_20260806_175759.dump   (944 KB, 0400)
```

`pg_dump -Fc -n fhort` del schema sencer **abans** d'esborrar res. Viu a `/root/backups/`, que és
on la casa ja guarda aquest tipus de foto (`ftt_staging_pre_S03a_20260709_165935.dump`, 09/07) —
i **no** dins de `ftt-staging/`, que és arbre de git: un binari de 944 KB allà dins acabaria
brut al `git status` i a un `git add` distret.

**Verificat abans i després de moure'l** (md5 idèntic, `45a429dd…`): 1.342 entrades d'arxiu ·
124 `TABLE DATA` · i la dada hi és de debò, comptada dins del propi dump sense tocar cap BD —
**46 `models_app_model` · 253 `tasks_timerentrada` · 4.783 `models_app_modelgradingrule` ·
691 `models_app_basemeasurement`**, que és exactament el que deia el cens.

> ⚠️ **PER RESTAURAR-LO CAL EL BINARI 18.** El clúster és PostgreSQL 18.4 (port 5433) però el
> `pg_restore` del `PATH` és el 16.14: `/usr/bin/pg_dump` és el `pg_wrapper` de Debian, que tria
> la versió segons el clúster de destí — i sobre un FITXER solt no té clúster d'on deduir-la, o
> sigui que cau al 16 i diu `unsupported version (1.16) in file header`. **No vol dir que el dump
> estigui malament.** Cal invocar-lo explícitament:
> ```
> /usr/lib/postgresql/18/bin/pg_restore -l <dump>          # llistar
> /usr/lib/postgresql/18/bin/pg_restore -a -t <taula> -f - <dump>   # treure'n una taula
> ```

---

## 6 · V6 · el loop de re-revisió

### 6.1 · Les dues col·lisions que ha obert la nit mateixa (les dues, tancades)

1. **P0.5d en vermell per V5b.** El fum assereix les capçaleres de les quatre columnes de regla pel
   seu literal, i el castellà ha deixat de dir «break». **El vermell era correcte; l'expectativa
   no.** Actualitzada la taula `COLS` del fum → P0.5d torna a verd als 3 idiomes.
2. **Els generadors de fixture escrivien 404s damunt d'un fixture bo.** Amb `fhort` sense models,
   `qa_p02_fixture.py 169` feia sis crides, en fallaven cinc i **desava igualment**: tots els fums
   de navegador que en viuen haurien quedat en vermell per un motiu impossible d'endevinar
   mirant-los —el producte bé, el fixture buit—. Els quatre generadors comproven ara que el model
   ha respost abans d'escriure; si no hi és, **no toquen res**. Verificat: el `qa_p02_fixture.json`
   bo (28 KB) no s'ha mogut.
   (`qa_q4_fixture.py` ja tenia el seu guard. `qa_w2_cicle_model.py` crea el model que després
   llegeix: no li afecta.)

I `qa_q34_presa_reconciliada.py`, que corre contra dades **vives**, moria amb un
`Model.DoesNotExist` pelat: ara diu quin model no hi és i què fer.

### 6.2 · Els controls sobre el HEAD final

| control | resultat |
|---|---|
| `manage.py check` | net |
| `tests_sembra_grading` | **84/84 OK** |
| suite `fhort.tasks` | **239/239 OK** |
| `node --test src/utils/*.test.js` | **154/154 OK** |
| `npm run build` | net |
| eslint | 0 errors · **mateix perfil d'alertes que a la base** a tots els fitxers tocats |
| fums de navegador (11) | ✅ muntatge · P0.2 · P0.2b · **P0.5d** · P0.6 · P0.7 · P0.8 · Q1 · Q2 · Q4 |
| fums contra dades vives | ⏸️ q34 i els generadors: **a l'espera dels models de QA nous** (conseqüència esperada de V4, i ara ho DIUEN) |
| restart + rutes vives | `update-step2` 401 · `claim` 401 · `xat-mesures` 401 · `regim` 401 |

### 6.3 · Grep de qui més llegia el que s'ha tocat

- **`materialize_model_grading_rules`** → 3 camins més sense el fix del predicat (§1, «el que no
  tanca V1»). **Anotat, obert.**
- **`traspassa_tram`** → només `views_b.py:523` i `:603`, tots dos coberts pel fix.
- **`sizingProfiles.list`** → `CustomerDetail`, `SizingProfileSelector` i `GraduacioPanel` el
  filtren per client/eixos; cap deriva «el primer que surti». **Cap col·lisió.**
- **Cobertura de famílies després de V2-dada** → cap família ha perdut tota la cobertura.

---

## 7 · LA LLISTA DE DEMÀ, revisada

### 7.1 · Es pot tocar sol

| # | peça | mida | nota |
|---|---|---|---|
| 1 | El filtre d'`origen` dins de `materialize_model_grading_rules` + els 3 camins que hi queden | **S** | és la decisió 6.1: **necessita l'Agus** abans de tocar-ho |
| 2 | `clean()`/constraint a `SizingProfile` (target ⊆ targets del sistema) | **S** | avui res impedeix reescriure els 9 d'ahir |
| 3 | L'enllaç mort `ModelFabric.jsx:120` → `/tasques/kanban` | **XS** | censat tres dies seguits |
| 4 | Instal·lar la cron de `pausa_tasques_oblidades` | **XS** | D-9 |
| 5 | LOSAN: les 4 referències al FK `target` retirat | **XS** | + **M** de re-verificació del paquet |
| 6 | `paused_task_id` a la resposta de `claim`/`open-task` | **XS** | el 🟡 de V3 |
| 7 | Bolcar el guió de la prova de 2 tècnics a `ops/qa/` | **S** | escrit a l'informe B3 de la tarda |
| 8 | `comprovacio_views.py:230-234`: preguntar el que preguntarà el motor | **S** | |

### 7.2 · Necessita l'Agus

1. **Decisió 6.1** — protegir les MANUAL dins del motor, o deixar el wipe com està.
2. **El camí d'import i el pla dels 93 orfes** — la sessió de matcher, amb `D-31.27` escrita
   primer (segueix sense text al repo).
3. **Els 3 defaults AMBIGUS** (`blouse`, `top_sleeveless`, `baby_dress`) — catàleg v4, amb la Montse.
4. **Models de QA nous** pel wizard: fins que no n'hi hagi, els fums contra dades vives i els
   generadors de fixture no poden córrer.
5. **TimeSeed** — ara és més urgent: amb el corpus a 0, el planificador **viu només de seeds**, i
   7 dels 15 TaskType a `fhort` no en tenen (i els 15 de `los`).
6. Les de sempre que segueixen obertes: credencials QA · `Paused→Done` · el guard per durada ·
   on viu `PromoteToItemButton` · «entrada manual» del contenidor · els 51 models de `los`.

---

## 8 · SORPRESES DE LA NIT

1. **Un `GradingRuleSet` sense `origen` classificat materialitza les seves residents com a
   `MANUAL`.** O sigui que «MANUAL» al camp `origen` **no vol dir sempre «ho ha escrit una
   persona»**. Auditat abans d'esborrar: les 24 MANUAL de `fhort` sí que eren autoria (els seus
   jocs tenien `origen` classificat), però la lectura ingènua del camp és un parany.
2. **El predicat destructiu i el del permís no només eren diferents: el destructiu era el més
   ample.** Qualsevol dels dos hauria estat un bug; que el gros fos el silenciós és el que el va
   fer sobreviure tant.
3. **Els cinc tests de handoff partien sempre del mateix estat.** El forat de V3 no es va escapar
   per falta de tests, sinó perquè tots cinc compartien la mateixa premissa.
4. **La paret de l'albarà no bloquejava l'esborrat.** Ens preparàvem per haver-la de sortejar i
   resulta que és un guard de transició, no de delete: el 188 va caure sense tocar-la.
5. **El fum més afectat per la nit no ha estat cap dels que provaven el codi tocat**, sinó els
   generadors de fixture — que no proven res, però poden deixar-ho tot en vermell.
