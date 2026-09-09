# C · El dump com a línia base + cens d'inconsistències

**Mode:** LECTURA PURA. Cap escriptura a `ftt_staging` (schemes `public`/`fhort`/`los`).
L'única escriptura feta ha estat **crear una BD temporal nova** (`ftt_tmp_diag_v4`) i
restaurar-hi el dump. Cap migració, cap `UPDATE`/`DELETE` enlloc.

**Data d'execució:** 2026-08-07 · **Working dir:** `/var/www/ftt-staging`

---

## C1.3 · Credencials i host (primer, perquè tota la resta hi penja)

**Consultat**

    grep -nE "DATABASES|NAME|USER|HOST|PORT|PASSWORD" /var/www/ftt-staging/backend/fhort/settings.py
    sed -E 's/(PASSWORD|PASS|SECRET|KEY)[^=]*=.*/\1=<REDACTED>/I' /var/www/ftt-staging/backend/.env
    pg_lsclusters

**Resultat**

- `backend/fhort/settings.py:118-125` — un sol `DATABASES['default']`, tot llegit de l'entorn:
  `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST` (default `localhost`), `DB_PORT` (default `5432`).
- `backend/.env` (mode `0600`, owner `www-data`) — `DB_NAME=ftt_staging`, `DB_USER=ftt_staging`,
  `DB_HOST=127.0.0.1`, **`DB_PORT=5433`**. `DB_PASSWORD` llegida des del `.env` a la mateixa
  comanda (`set -a && . ./.env && set +a && export PGPASSWORD="$DB_PASSWORD"`), **mai enganxada
  en clar ni passada per línia d'ordres**.
- Clústers: `16/main` port 5432 **down**; `18/main` port 5433 **online**. El clúster viu és el 18.

**Patró de comanda usat a tot l'informe** (es dona un cop i no es repeteix):

    cd /var/www/ftt-staging/backend
    set -a && . ./.env && set +a && export PGPASSWORD="$DB_PASSWORD"
    psql -h 127.0.0.1 -p 5433 -U ftt_staging -d <BD> -X -c "<SQL>"

---

## C1.1 · El dump és restaurable?

**Consultat**

    ls -la /root/backups/
    stat -c '%s bytes  mtime=%y' /root/backups/ftt_staging_fhort_pre_V4_20260806_175759.dump
    md5sum /root/backups/ftt_staging_fhort_pre_V4_20260806_175759.dump
    pg_restore --list /root/backups/ftt_staging_fhort_pre_V4_20260806_175759.dump

**Resultat**

    -r-------- 1 root root 965892 Aug 6 17:57 ftt_staging_fhort_pre_V4_20260806_175759.dump
    965892 bytes  mtime=2026-08-06 17:57:59.519215993 +0000
    45a429dd3a2a197713eca07488bf2849

El `pg_restore` del **PATH** falla:

    pg_restore: error: unsupported version (1.16) in file header      # exit 1

`which pg_restore` → `/usr/bin/pg_restore` = **PostgreSQL 16.14**, però el dump el va escriure
**pg_dump 18.4**. 🔵 **Cal invocar el binari de la 18 explícitament**:

    /usr/lib/postgresql/18/bin/pg_restore --list /root/backups/ftt_staging_fhort_pre_V4_20260806_175759.dump

Capçalera literal:

    ; Archive created at 2026-08-06 17:57:59 UTC
    ;     dbname: ftt_staging
    ;     TOC Entries: 1346
    ;     Compression: gzip
    ;     Dump Version: 1.16-0
    ;     Format: CUSTOM
    ;     Dumped from database version: 18.4 (Ubuntu 18.4-1.pgdg24.04+1)
    ;     Dumped by pg_dump version: 18.4

**🚨 EL DUMP ÉS NOMÉS DE L'SCHEMA `fhort`.** Recompte d'entrades del TOC per tipus:

    1 SCHEMA (fhort) · 124 TABLE (totes `fhort`) · 124 TABLE DATA · 124 SEQUENCE
    124 SEQUENCE SET · 376 INDEX · 207 CONSTRAINT · 262 FK CONSTRAINT

No hi ha **cap** entrada de `public` ni de `los`. Qualsevol comparació de postcondició que
impliqui el catàleg compartit de `public` (p. ex. `public.pom_sizesystem`) **no es pot fer
contra aquest fitxer**.

**Veredicte: SÍ, és restaurable** (fet, apartat següent).

---

## C1.2 · Recomptes AL DUMP

**Restauració (feta)**

    createdb -h 127.0.0.1 -p 5433 -U ftt_staging ftt_tmp_diag_v4
    /usr/lib/postgresql/18/bin/pg_restore -h 127.0.0.1 -p 5433 -U ftt_staging \
      -d ftt_tmp_diag_v4 --no-owner --no-privileges \
      /root/backups/ftt_staging_fhort_pre_V4_20260806_175759.dump

Comprovat abans amb `psql -l` que no col·lisionava: les BD existents eren `ftt_staging`,
`postgres`, `tea205_probe`, `template0/1`, `test_ftt_f1_tmp`, `test_ftt_staging`,
`test_ftt_step_tmp`, `test_n4_nit_capes`.

Sortida literal (exit 1, **1 sol error, ignorat i inofensiu**):

    pg_restore: error: could not execute query: ERROR:  relation "public.tenants_client" does not exist
    Command was: ALTER TABLE ONLY fhort.pom_clientmesuraperfil
        ADD CONSTRAINT pom_clientmesuraperfil_client_id_dfb33d3b_fk_tenants_client_id
        FOREIGN KEY (client_id) REFERENCES public.tenants_client(id) DEFERRABLE INITIALLY DEFERRED;
    pg_restore: warning: errors ignored on restore: 1

→ conseqüència directa del fet que el dump no porta `public`. Totes les dades hi són.

**🔵 BD TEMPORAL DEIXADA CREADA (no esborrada), per reaprofitar:**

| BD | mida | contingut |
|---|---|---|
| **`ftt_tmp_diag_v4`** | **26 MB** | schema `fhort` del 06/08 17:57:59 UTC, sencer |

(`ftt_staging` viu = 49 MB, per comparació.)

### Recomptes demanats

    psql ... -d ftt_tmp_diag_v4 -X -c "
    SELECT 'models_app_model' t, count(*) FROM fhort.models_app_model
    UNION ALL SELECT 'models_app_basemeasurement', count(*) FROM fhort.models_app_basemeasurement
    UNION ALL SELECT 'models_app_measurementchangelog', count(*) FROM fhort.models_app_measurementchangelog
    UNION ALL SELECT 'fitting_gradedspec', count(*) FROM fhort.fitting_gradedspec ...;"

| taula (`fhort`) | AL DUMP | VIU avui | delta |
|---|---:|---:|---:|
| `models_app_model` (models de peça) | **46** | **0** | −46 |
| `models_app_basemeasurement` (BaseMeasurement) | **691** | **0** | −691 |
| `models_app_measurementchangelog` (MeasurementChangeLog) | **228** | **0** | −228 |
| `fitting_gradedspec` (GradedSpec) | **1 787** | **0** | −1 787 |
| `fitting_sizefitting` | 48 | 0 | −48 |
| `fitting_gradingversion` | 34 | 0 | −34 |
| `pom_pommaster` | 396 | 396 | 0 |
| `pom_customerpomalias` | 390 | 390 | 0 |
| `pom_pomglobal` | 274 | 274 | 0 |
| `pom_garmentpommap` | 1 748 | 1 748 | 0 |
| `pom_gradingrule` | 1 288 | 1 267 | **−21** |
| `pom_gradingruleset` | 47 | 46 | **−1** |
| `pom_sizesystem` | 28 | 26 | **−2** |
| `pom_sizedefinition` | 175 | 165 | **−10** |

Els 46 models són **tots `estat='Nou'`**, ids `162..1308`.
`BaseMeasurement` per `origen`: `TEMPLATE` 503 · `MANUAL` 171 · `IMPORTED` 9 · `FITTED` 7 · `CHECKED` 1.
`MeasurementChangeLog` per `context`: `import` 133 · `manual` 66 · `checked` 17 · `fitting` 10 · `item_standard` 2.

### Files amb POM `S` i POM `S2`

**🚨 `S` i `S2` NO són un POM cadascun: n'hi ha DOS de cada** a `fhort.pom_pommaster`
(mateix `codi_client`, POMs diferents). Al dump **i viu** (idèntic):

    SELECT id, codi_client, nom_client, pom_global_id, categoria_id, actiu, pendent_revisio
    FROM fhort.pom_pommaster WHERE codi_client IN ('S','S2') ORDER BY id;

    id  | codi_client |        nom_client        | pom_global_id | categoria_id | actiu | pendent_revisio
    457 | S           | Front armhole along seam |           262 |           13 | t     | t
    581 | S           | COLLAR HEIGHT ON TOP     |           353 |              | t     | t
    458 | S2          | Back armhole along seam  |               |           13 | t     | t
    583 | S2          | COLLAR BAND HEIGHT       |           224 |              | t     | t

Files al dump que hi pengen (JOIN per `pom_id`):

| taula | `S` total | `S2` total | desglossat per `pom_id` |
|---|---:|---:|---|
| `models_app_basemeasurement` | 4 | 5 | 457→4 · 458→4 · **583→1** · 581→0 |
| `fitting_gradedspec` | 36 | 36 | 457→36 · 458→36 · 581→0 · 583→0 |
| `models_app_measurementchangelog` | 4 | 4 | — |
| `pom_gradingrule` | 4 | 4 | — |

🔑 Els POMs 581/583 (els «COLLAR») són **quasi buits**: només 1 BaseMeasurement en total i
cap GradedSpec. Tota la càrrega viu als 457/458.

### 🔵 Empremta de línia base de `GradedSpec` (per a la postcondició «idèntic»)

Perquè una sessió futura pugui contrastar sense dependre dels `id` (que canviaran en refer
el catàleg), es deixa una empremta **ancorada a `Model.codi_intern` + `POMMaster.codi_client`**:

    WITH k AS (
      SELECT mo.codi_intern, pm.codi_client AS pom, g.size_label, g.capa, g.instancia,
             g.graded_value_cm, g.grading_type_applied, g.increment_applied_cm,
             g.is_active, gv.version_number
      FROM fhort.fitting_gradedspec g
      JOIN fhort.fitting_gradingversion gv ON gv.id = g.grading_version_id
      JOIN fhort.fitting_sizefitting sf    ON sf.id = gv.size_fitting_id
      JOIN fhort.models_app_model mo       ON mo.id = sf.model_id
      JOIN fhort.pom_pommaster pm          ON pm.id = g.pom_id)
    SELECT count(*),
           md5(string_agg(codi_intern||'|'||pom||'|'||size_label||'|'||capa||'|'||instancia||'|'
               ||version_number||'|'||graded_value_cm||'|'||grading_type_applied||'|'
               ||increment_applied_cm||'|'||is_active, E'\n'
               ORDER BY codi_intern,pom,size_label,capa,instancia,version_number))
    FROM k;

    files |         fingerprint_md5
     1787 | e7de6f09b5bc04e7974e3afcf8e5a6e6

Repartiment de les 1 787: **10 models** amb spec, **33 GradingVersion**.
Per `(capa, instancia)`: `exterior/''` 1 770 · `exterior/'cb'` 5 · `exterior/'right'` 4 ·
`exterior/'left'` 4 · **`folre/''` 4**.

---

## C2 · Cens d'inconsistències (NOMÉS REPORTAR)

> Recordatori de mètode: `pom` és SHARED+TENANT. Cada línia diu de quin schema parla.

### C2.0 · El repartiment real de dades entre schemes (viu, avui)

    SELECT 'pommaster', (SELECT count(*) FROM public.pom_pommaster),
                        (SELECT count(*) FROM fhort.pom_pommaster),
                        (SELECT count(*) FROM los.pom_pommaster) ... ;

| entitat | `public` | `fhort` | `los` |
|---|---:|---:|---:|
| `pom_pomglobal` | 125 | 274 | **0** |
| `pom_pommaster` | **0** | 396 | **0** |
| `pom_customerpomalias` | **0** | 390 | **0** |
| `pom_garmentpommap` | **0** | 1 748 | **0** |
| `pom_sizesystem` | 14 | 26 | 2 |
| `pom_sizedefinition` | 70 | 165 | **0** |
| `pom_gradingruleset` | 14 | 46 | **0** |
| `pom_gradingrule` | **0** | 1 267 | **0** |
| `models_app_model` | *(taula no existeix)* | **0** | **51** |
| `models_app_basemeasurement` | *(n/a)* | **0** | **0** |
| `fitting_gradedspec` | *(n/a)* | **0** | **0** |
| `models_app_measurementchangelog` | *(n/a)* | **0** | **0** |
| `fitting_sizefitting` | *(n/a)* | **0** | **51** |

**Inconsistències que se'n desprenen, amb evidència:**

- **🚨 `los` té 51 models i 51 SizeFitting però 0 POMMaster, 0 BaseMeasurement, 0 GradedSpec i
  0 GradingRule.** (confirma el `🚩 los sense POMMaster` de sessions anteriors, i l'amplia: no
  té CAP mesura ni cap spec).
- **🚨 `los.pom_sizesystem` té 2 files i `los.pom_sizedefinition` en té 0** → dos sistemes de
  talla sense cap talla:

      SELECT id, codi, nom, actiu FROM los.pom_sizesystem ORDER BY id;
       1 | ALPHA_EU_W   | Alpha EU — Women  | t
       2 | SYS-ONLY-LOS | Sistema només LOS | t

- **🚨 `public.pom_gradingruleset` té 14 rulesets i `public.pom_gradingrule` en té 0** → 14
  rulesets sense cap regla. A més **13 dels 14 tenen `size_system_id` NULL**:

      SELECT id, nom, size_system_id FROM public.pom_gradingruleset ORDER BY id;
      -- només el 14 ("EU Woven Woman Numeric") té size_system_id=4; els altres 13, NULL.

- **🔵 `fhort.pom_pomglobal` (274) > `public.pom_pomglobal` (125)** — el tenant té 149 POMGlobal
  que el compartit no té. No s'ha determinat si això és disseny o divergència.

### C2.1 · `public.TODDLER_EU` — **✅ SEGUEIX CORRUPTE, CONFIRMAT**

    SELECT 'public', s.codi, d.etiqueta, d.ordre, d.body_height_cm, d.body_bust_cm,
           d.body_waist_cm, d.body_hip_cm, s.base_unit
    FROM public.pom_sizedefinition d JOIN public.pom_sizesystem s ON s.id=d.size_system_id
    WHERE s.codi IN ('TODDLER_EU','KIDS_EU','BABY_EU_CM')
    UNION ALL <el mateix per fhort i per los> ORDER BY 2,1,4;

    sch    |    codi    | etiqueta | ordre |   h   | bust | waist | hip  | base_unit
    public | TODDLER_EU | 92       |     1 |  92.0 | 52.0 |  26.0 | 32.0 | CM_HEIGHT
    public | TODDLER_EU | 98       |     2 |  98.0 | 54.0 |  28.0 | 34.0 | CM_HEIGHT
    public | TODDLER_EU | 104      |     3 | 104.0 | 56.0 |  30.0 | 36.0 | CM_HEIGHT
    public | TODDLER_EU | 110      |     4 | 110.0 | 58.0 |  32.0 | 38.0 | CM_HEIGHT
    public | TODDLER_EU | 116      |     5 | 116.0 | 60.0 |  34.0 | 40.0 | CM_HEIGHT
    fhort  | TODDLER_EU | 86       |     1 |  86.0 | 53.0 |  53.0 | 55.0 | CM_HEIGHT
    fhort  | TODDLER_EU | 92       |     2 |  92.0 | 55.0 |  54.0 | 58.0 | CM_HEIGHT
    fhort  | TODDLER_EU | 98       |     3 |  98.0 | 57.0 |  55.0 | 61.0 | CM_HEIGHT
    fhort  | TODDLER_EU | 104      |     4 | 104.0 | 59.0 |  56.0 | 63.0 | CM_HEIGHT
    fhort  | TODDLER_EU | 110      |     5 | 110.0 | 61.0 |  57.0 | 65.0 | CM_HEIGHT
    fhort  | TODDLER_EU | 116      |     6 | 116.0 | 60.0 |  58.0 | 67.0 | CM_HEIGHT
    public | KIDS_EU    | 6Y       |     1 | 116.0 | 60.0 |  54.0 | 64.0 | AGE_YEARS
    fhort  | KIDS_EU    | 6Y       |     1 | 116.0 | 60.0 |  54.0 | 64.0 | AGE_YEARS

Tres evidències, no una:
1. **`waist`/`hip` ~20-25 cm avall** a `public.TODDLER_EU` respecte de `fhort.TODDLER_EU`.
2. **Contradicció DINS del mateix schema `public`:** a 116 cm d'alçada, `KIDS_EU 6Y` diu
   waist 54 / hip 64 i `TODDLER_EU 116` diu **34 / 40**.
3. **`public` té 5 talles i `fhort` en té 6** — a `public` hi falta la `86`, i tot l'`ordre`
   està desplaçat una posició.

**Bonus no demanat, mateixa família:** `public.BABY_EU_CM` té **`waist` i `hip` tots NULL**
(8/8 files) i el `bust` divergeix de `fhort` a totes les talles (p. ex. talla 50: `public`
34.0 vs `fhort` 40.0).

    SELECT s.codi, count(d.id) FROM public.pom_sizesystem s
    LEFT JOIN public.pom_sizedefinition d ON d.size_system_id=s.id GROUP BY 1;
    -- ALPHA_EU_U 0 · ALPHA_US_W 0 · NUMERIC_EU_M 0 · NUMERIC_US_W 0  (4 sistemes sense cap talla)

### C2.2 · POMs de `POMMaster` orfes (sense `CustomerPOMAlias`) — **el número ha CANVIAT: 106, no 93**

    SELECT count(*) FROM fhort.pom_pommaster m
    WHERE NOT EXISTS (SELECT 1 FROM fhort.pom_customerpomalias a WHERE a.pom_id = m.id);
    -- 106   (idèntic al dump: 106)

Comptat a `public` i `los`: **0 i 0** (les taules són buides, v. C2.0).
Cap `CustomerPOMAlias` amb `pom_id IS NULL` (0). No s'ha fet cap CSV ni bolcat de POMMaster
(feina d'un altre investigador).

Mesures veïnes barates, del mateix escombrat:

    SELECT 'pommaster sense GarmentPOMMap', count(*) FROM fhort.pom_pommaster m
      WHERE NOT EXISTS (SELECT 1 FROM fhort.pom_garmentpommap g WHERE g.pom_id=m.id) ...

| indicador (`fhort`, viu) | valor |
|---|---:|
| `POMMaster` total | 396 |
| …**sense cap `CustomerPOMAlias`** | **106** |
| …**sense cap `GarmentPOMMap`** | **230** |
| …**ni àlies ni map** (doblement orfe) | **58** |
| …`pom_global_id IS NULL` | **122** |
| …`actiu = false` | 16 |
| …**`pendent_revisio = true`** | **254 (64 %)** |
| `CustomerPOMAlias` amb `pendent_revisio` | 29 |
| `GarmentPOMMap` amb `pendent_revisio` | 238 |
| `POMGlobal` sense cap `POMMaster` | 0 |

**🚨 `pendent_revisio` massiu confirmat: 254 de 396 POMs del tenant (64 %) segueixen marcats
com a «creat automàticament des d'importació, requereix revisió».** Idèntic al dump.

### C2.3 · Duplicats de `codi_client` a `fhort.pom_pommaster` — **12 codis, 24 files**

    SELECT codi_client, count(*) n, string_agg(id||':'||nom_client, ' | ' ORDER BY id)
    FROM fhort.pom_pommaster GROUP BY 1 HAVING count(*)>1 ORDER BY n DESC, codi_client;

    BJ | 2 | 418:FRONT & BACK WIDTH LOCATION | 514:FRONT&BACK WIDTH LOCATION
    C1 | 2 | 471:STRETCHED HIP WIDTH         | 524:WAIST WIDTH EXTENDED
    D  | 2 | 436:1/2 bottom width relaxed    | 528:HIP WIDTH
    E4 | 2 | 455:Shoulder forward            | 535:BOTTOM WIDTH EXTENDED
    E7 | 2 | 475:Center collar panel height  | 537:BOTTOM HEIGHT
    H  | 2 | 423:SLEEVE MUSCLE (1/2)         | 551:SLEEVE MUSCLE
    J1 | 2 | 460:Sleeve opening relaxed      | 507:SHOULDER DROP LOCATION
    L1 | 2 | 505:Back yoke side height...    | 510:NECK TOTAL
    S  | 2 | 457:Front armhole along seam    | 581:COLLAR HEIGHT ON TOP
    S2 | 2 | 458:Back armhole along seam     | 583:COLLAR BAND HEIGHT
    U  | 2 | 439:Width sequins piece (CF)    | 512:RIB WIDTH
    U1 | 2 | 440:Height sequins piece (CF)   | 513:JETTING WIDTH

**No hi ha cap constraint d'unicitat sobre `pom_pommaster.codi_client`** (verificat a `\d`).
Dos casos són **col·lisions semàntiques reals** (`BJ`: «FRONT & BACK» vs «FRONT&BACK» — el
mateix concepte escrit de dues maneres; `H`: «SLEEVE MUSCLE (1/2)» vs «SLEEVE MUSCLE»).
La resta són codis curts reutilitzats per conceptes diferents.

### C2.4 · 9 POMs amb `nom_fitxa` BUIT — **la premissa era de PROD, i a staging el problema és MOLT més gran**

El «9» de sessions anteriors era una **mesura de PROD sobre el POM 389** (28 BaseMeasurement,
repartides `FF`→15 / `M`→4 / **`<BUIT>`→9**). No és una propietat de POMMaster: `nom_fitxa` és
columna de `models_app_basemeasurement` i de `pom_itembasemeasurement` (verificat a
`information_schema.columns`: només aquestes dues, a `fhort` i `los`; a `public` només
`pom_itembasemeasurement`).

**A `fhort` VIU no es pot mesurar: `models_app_basemeasurement` té 0 files** (wipe).
**Al dump:**

    SELECT count(*) total, count(*) FILTER (WHERE nom_fitxa='') buit,
           count(*) FILTER (WHERE base_value_cm IS NULL) sense_valor
    FROM fhort.models_app_basemeasurement;

    total | buit | sense_valor
      691 |  558 |         503

**🚨 558 de 691 BaseMeasurement (81 %) tenien `nom_fitxa` buit al dump**, no 9.
I **39 POMs** eren reclamats per més d'un `nom_fitxa` alhora:

    SELECT b.pom_id, m.codi_client, count(DISTINCT b.nom_fitxa) n_noms, count(*) n_files,
           string_agg(DISTINCT coalesce(nullif(b.nom_fitxa,''),'<BUIT>'), ',')
    FROM fhort.models_app_basemeasurement b JOIN fhort.pom_pommaster m ON m.id=b.pom_id
    GROUP BY 1,2 HAVING count(DISTINCT b.nom_fitxa)>1 ORDER BY n_files DESC;

    pom_id | codi | n_noms | n_files | noms
       284 | AH DEP |   5 |      21 | AHL,AHR,<BUIT>,J1,SF
       273 | CH     |   3 |      20 | A,A-FOL,<BUIT>
       301 | NK W   |   3 |      19 | <BUIT>,EK,R
       ... (39 files en total; el pom 438 = 'FF' → <BUIT>,FF · el 389 = 'M-M79' → <BUIT>,M)

**A `pom_itembasemeasurement` (`fhort`, VIU): 37 de 37 files tenen `nom_fitxa=''` (100 %).**
A `public` i `los` la taula és buida.

### C2.5 · Duplicats de `SizeFitting` (models 185 i 182) — **la premissa era l'entitat equivocada; el dany real és a `SizeCheck` i HI ERA al dump**

`fitting_sizefitting` VIU a `fhort` = **0** (wipe). Mesurat **al dump**:

    SELECT model_id, count(*) n_sf, string_agg(id||':'||codi||'/'||tipus||'/'||estat||'/n'||numero,' | ' ORDER BY id)
    FROM fhort.fitting_sizefitting GROUP BY 1 HAVING count(*)>1;

    163 | 2 | 53:BRW-FW26-0001-SF1/Proto/TallesGenerades/n1 | 79:IMP-163-2/SizeSet/Tancat/n2
    174 | 2 | 64:BRW-FW26-0012-SF1/Proto/TallesGenerades/n1 | 186:IMP-174-2/SizeSet/Tancat/n2

    SELECT id, model_id, numero, codi, tipus, estat FROM fhort.fitting_sizefitting
    WHERE model_id IN (182,185);
    75 | 182 | 1 | BRW-26-SS-0002-SF1 | Proto   | TallesGenerades
    76 | 185 | 1 | FTT-FW27-0001-SF-1 | SizeSet | TallesGenerades

→ **Els models 182 i 185 tenien UN SOL `SizeFitting` cadascun.** Els únics amb 2 són el 163 i
el 174, i el segon és sempre `codi='IMP-…'`, `estat='Tancat'` (creat deliberadament pel wizard
d'import). **Cap model amb >1 `SizeFitting` no-tancat.**

**El duplicat real era `SizeCheck`, i al dump hi és:**

    SELECT model_id, count(*) n_checks, count(*) FILTER (WHERE estat='Pendent') pendents,
           string_agg(id||':'||estat, ',' ORDER BY id)
    FROM fhort.models_app_sizecheck GROUP BY 1 HAVING count(*)>1;

    182 | 4 | 1 | 16:Acceptat,17:Acceptat,20:Acceptat,21:Pendent
    185 | 3 | 0 | 18:Acceptat,19:Acceptat,22:Acceptat

    SELECT c.model_id, c.id, c.estat, l.pom_id, l.valor_teoric, l.valor_real, c.created_at::date
    FROM fhort.models_app_sizecheck c JOIN fhort.models_app_sizecheckline l ON l.size_check_id=c.id
    WHERE (c.model_id=185 AND l.pom_id=273) OR (c.model_id=182 AND l.pom_id=379);

    182 | 16 | Acceptat | 379 | 41   | 41.4 | 2026-06-16
    182 | 17 | Acceptat | 379 | 41.4 | 41.7 | 2026-06-22
    182 | 20 | Acceptat | 379 | 41.7 |      | 2026-06-23
    182 | 21 | Pendent  | 379 | 41.7 | 41.7 | 2026-06-23     <-- teòric congelat
    185 | 18 | Acceptat | 273 | 60   | 60.5 | 2026-06-22
    185 | 19 | Acceptat | 273 | 60.5 |      | 2026-06-23
    185 | 22 | Acceptat | 273 | 60.5 | 61.1 | 2026-06-24     <-- cap 'Pendent'

I la base vigent del 182/POM 379 al dump:

    SELECT model_id, pom_id, base_value_cm, origen, updated_at::date
    FROM fhort.models_app_basemeasurement WHERE model_id=182 AND pom_id=379;
    182 | 379 | 42.6 | CHECKED | 2026-06-24

**🚨 El desfasament segueix: el check 21 (`Pendent`) diu `valor_teoric=41.7` i la base vigent
al mateix dump és `42.6`.** El dany documentat el 03/08 estava intacte quan es va fer el dump.

### C2.6 · **🚨 NOU · 125 `GradingRule` amb la talla base FORA del seu propi sistema de talles**

    SELECT s.id rs_id, s.nom, ss.codi sys, r.talla_base_label,
           EXISTS (SELECT 1 FROM fhort.pom_sizedefinition d2
                   WHERE d2.size_system_id = s.size_system_id
                     AND d2.etiqueta = r.talla_base_label) label_existeix_al_sistema,
           count(*) n
    FROM fhort.pom_gradingrule r
    JOIN fhort.pom_gradingruleset s ON s.id = r.rule_set_id
    JOIN fhort.pom_sizesystem ss    ON ss.id = s.size_system_id
    GROUP BY 1,2,3,4,5 ORDER BY 5, 6 DESC;

    rs_id |          nom            |     sys      | talla_base_label | existeix |  n
       91 | EU Woven Woman Numeric  | NUMERIC_EU_W | 128              | f        |  61
       87 | EU Knit Baby Regular    | BABY_EU_CM   | 128              | f        |  25
       89 | EU Knit Kids Regular    | KIDS_EU      | 128              | f        |  20
       88 | EU Knit Toddler Regular | TODDLER_EU   | 128              | f        |  19
       ... (tota la resta: existeix = t)

I el `talla_base_id` d'aquestes 125 regles apunta a una `SizeDefinition` d'un **altre** sistema:

    SELECT ... WHERE d.size_system_id <> s.size_system_id ...
    -- els 4 rulesets de sobre; sys_talla_base = TGIRL-EU-HEIGHT (fhort.pom_sizesystem id=6) en els 4

**125 regles de 4 rulesets tenen `talla_base_label='128'`, etiqueta que NO existeix al sistema
de talles del seu propi ruleset**, i el seu `talla_base_id` penja de `TGIRL-EU-HEIGHT`.
Com que el motor ancora per etiqueta (`base_size_label`), aquestes 125 regles **no poden
resoldre la seva talla base dins del seu run**. Concorda amb la nota `🚨 TGIRL: àncora de N
regles` de sessions anteriors, i ho quantifica avui: **125**.

Coherència creuada (no hi ha soroll addicional):

    'gradingrule talla_base_label buit'      -> 0
    'gradingrule label != sizedef.etiqueta'  -> 0   (l'etiqueta i el FK sempre concorden entre si)

### C2.7 · Rulesets i sistemes buits a `fhort` (viu)

    'gradingruleset sense size_system'  -> 7    (ids 77,78,80,82,85,92,98)
    'gradingruleset sense cap regla'    -> 1
    'sizesystem sense sizedefinition'   -> 4    (31 ALPHA_EU_U, 33 NUMERIC_EU_M,
                                                 39 ALPHA_US_W, 40 NUMERIC_US_W — tots actiu=t)

### C2.8 · Residu post-wipe a `fhort` (viu) — **cap dada òrfena de models**

    SELECT 'tasks_modeltask', count(*) FROM fhort.tasks_modeltask UNION ALL ... ;

    tasks_modeltask 0 · models_app_modelfitxer 0 · models_app_sizecheck 0 ·
    models_app_sizecheckline 0 · models_app_modelgradingrule 0 ·
    models_app_modelgradingoverride 0 · models_app_garmentset 0 ·
    fitting_piecefitting 0 · fitting_piecefittingline 0 · fitting_pomalert 0 ·
    fitting_fittingsession 0 · patterns_patternfile 0 · patterns_patternpom 0 ·
    commerce_quotelinemodelintent 0
    -- sobreviuen (i NO pengen de Model): models_app_importsession 24 · tasks_customer 3 ·
    --   tasks_garmenttypeitem 62 · pom_itembaseset 1 · pom_itembasemeasurement 37 ·
    --   pom_garmentpommap 1748 · models_app_pomplacement 2

Les 2 `PomPlacement` supervivents pengen d'`item_fitxer_id=14` (ItemFitxer), **no** de Model
→ no són òrfenes del wipe. Verificat:

    'pomplacement -> models_app_itemfitxer' -> 0 òrfenes
    'pomplacement -> pom_pommaster'         -> 0 òrfenes

**Escombrat complet dels FK LÒGICS (`db_constraint=False`, els que la BD no protegeix)** a
`fhort` viu — **tots a 0 òrfenes**:

    garmentpommap→tasks_garmenttypeitem 0 · garmentpommap→pom_pommaster 0
    itembaseset→tasks_garmenttypeitem 0 · itembasemeasurement→tasks_garmenttypeitem 0
    gradingruleset→tasks_garmenttypeitem 0 · gradingruleset→tasks_customer 0
    sizingprofile→tasks_customer 0 · sizesystem→tasks_customer 0
    customerpomalias→tasks_customer 0 · customerpomalias→pom_pommaster 0
    rulesetscopenode→tasks_garmenttypeitem 0 · pommaster→pom_pomglobal 0

⚠️ **Fals positiu descartat:** una primera consulta donava 20 òrfenes a
`pom_clientmesuraperfil → public.tenants_client`. És artefacte del `NOT EXISTS` amb NULLs:

    SELECT count(*) total, count(DISTINCT client_id) n_clients FROM fhort.pom_clientmesuraperfil;
    -- 20 | 0     → les 20 files tenen client_id IS NULL. NO són òrfenes.

### C2.9 · El que ha canviat al catàleg DESPRÉS del dump (06/08 17:57 → avui) — **cascada neta, no dany**

    -- diff per id entre ftt_tmp_diag_v4 i ftt_staging
    SizeSystem esborrats:      26|MEN-SHIRT-NUM · 53|WOMAN_BRW_01     (cap de nou)
    GradingRuleSet esborrat:   124|Prova BRW ALPHA UE                 (cap de nou)
    SizeDefinition esborrades: 10                                     (cap de nova)
    GradingRule esborrades:    21                                     (cap de nova)
    -- i les 21 regles esborrades pertanyien TOTES al ruleset 124:
    SELECT rule_set_id, count(*) FROM fhort.pom_gradingrule WHERE id IN (<les 21>) GROUP BY 1;
    124 | 21

Cap alta. La diferència entre dump i viu al catàleg és **exclusivament** l'esborrat coherent
del ruleset de prova 124 + els 2 sistemes de talla + les seves 10 talles i 21 regles.

---

## Què NO s'ha pogut determinar en lectura

1. **La postcondició «GradedSpec idèntic» no es pot avaluar contra `public` ni `los`**: el dump
   només conté l'schema `fhort` (C1.1). Si el catàleg es refà tocant `public`, aquest fitxer no
   dona línia base per a aquesta part.
2. **`fhort.models_app_model` viu és 0**, o sigui que qualsevol contrast de «models» és
   dump-contra-buit. No es pot saber, en lectura, **què** va executar el wipe ni quan
   exactament (no s'ha inspeccionat cap log d'aplicació ni el WAL).
3. **La reconciliació dels ids entre dump i un catàleg refet no és determinable**: els `id` de
   `models_app_model` (162..1308) i de `fitting_gradingversion` es regeneraran. Per això
   l'empremta de C1.2 s'ancora a `codi_intern`+`codi_client` i no a ids; **no s'ha verificat que
   `codi_intern` sigui únic al conjunt** (no formava part de l'encàrrec).
4. **Si els 12 `codi_client` duplicats de C2.3 són error o disseny** no es pot decidir llegint la
   BD: no hi ha constraint que ho prohibeixi ni cap camp que digui quin és el vigent.
5. **Els 106 POMs sense àlies**: només se n'ha comptat el nombre. El bolcat/CSV el fa un altre
   investigador (per encàrrec explícit, no s'ha duplicat).
6. **`public.pom_pomglobal` (125) vs `fhort.pom_pomglobal` (274)**: no s'ha determinat si els 149
   de diferència són extensió legítima del tenant o divergència del compartit.
7. **La corrupció de `public.TODDLER_EU`** està confirmada com a fet observable, però **quin dels
   dos jocs de números és el correcte** és una decisió humana, no una lectura.
8. **No s'ha comprovat el codi que llegeix cap d'aquestes taules** (l'encàrrec era lectura de
   dades); les afirmacions sobre l'efecte de C2.6 en el motor descansen en notes de sessions
   prèvies, no en una traça executada aquí.

---

## Rastre d'artefactes deixats

| artefacte | on | estat |
|---|---|---|
| BD temporal amb el dump restaurat | `ftt_tmp_diag_v4` (127.0.0.1:5433, owner `ftt_staging`) | **deixada creada**, 26 MB |
| Aquest informe | `/var/www/ftt-staging/_C_dump_inconsistencies.md` | escrit |
| Fitxers de treball (TOC, diffs) | scratchpad de sessió | efímers |

Cap escriptura a `ftt_staging`. Cap migració. Cap reparació.
