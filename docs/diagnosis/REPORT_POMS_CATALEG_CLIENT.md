# Els POMs es van a buscar al catàleg del client. Enlloc més.

> Llei d'Agus, 06/08. Tram sobre staging `dev`, cap push. Tota escriptura de prova s'ha fet dins
> d'un `atomic` que es desfà; el MILEY (1308) no s'ha tocat.

## Commits

| # | hash | què |
|---|---|---|
| 49 | `78ba69ac` | la cerca resol contra el catàleg del client + el resolutor invers + `origen='MODEL'` |
| 50 | `539407a0` | endpoint «Crear POM propi del model», amb validació de col·lisió |
| 51 | `0b2066a1` | la nomenclatura del llapis passa la mateixa validació; el nom segueix lliure |
| 52 | `527f5dae` | el cercador parla la nomenclatura del client · el gest de crear-ne un · mor l'encunyador |
| 53 | `c363c224` | el pla de neteja dels orfes, en sec |

---

## 🔴 La premissa que calia corregir

El camp `POMMaster.codi_client` **es diu «client» però és el codi de la CASA**. El codi *del
client* viu només a `CustomerPOMAlias.client_code`. Tota la confusió d'aquest tram surt d'aquí,
i el cercador la practicava: cercava per `POMMaster.codi_client` i pintava el resultat sota el
rètol «del catàleg del client».

Mesurat al schema `fhort`, buscant «U1» des d'un model de Brownie:

```
ABANS → 513  U1  JETTING WIDTH               (de LOSAN)
        440  U1  Height sequins piece (CF)   (un orfe creat per un import)
ARA   → 342  U1  Button spacing              (el que Brownie anomena U1)
```

Un model de Brownie veia els **393 POMs del tenant, inclosos els 240 de Losan**. Això és el
forat de font única i es tanca en aquest tram, com vas demanar.

També es corregeix el que es PINTA: el tècnic de Brownie llegia «CH» —el codi de la casa— quan
el seu document diu «A».

---

## Les quatre peces del brief

**1 · El cercador només resol contra el catàleg.** Amb `?model=`, la cerca va contra els àlies
del client d'aquest model (codi, descripció internacional i local). No és un filtre a sobre del
catàleg de la casa: és una altra pregunta, «quines mesures coneix aquest client?». Sense
`?model=` es manté el camí de sempre — hi ha superfícies que cerquen sense model al davant.

**2 · POM que el catàleg no té.** `POST /api/v1/models/<id>/pom-propi/ {nom, nomenclatura}`.
Demana les dues coses **per separat** —el nom, que és lliure; la nomenclatura, que és un codi— i
valida el codi contra el catàleg del client. El POM neix **al catàleg del client**: `POMMaster` +
`CustomerPOMAlias` amb `origen='MODEL'`, tots dos `pendent_revisio=True`.

**3 · En assignar joc, la regla es resol sola.** Verificat: el POM oficial afegit del catàleg
resol la regla del joc (`LINEAR db=2.00`) perquè comparteix `POMMaster` amb ella; el POM propi
del model no en té cap i surt «—» a Graduació, per informar a mà.

> ⚠️ Matís de la diagnosi del punt 1: la resolució **no és per àlies**, és pel `pom_id` cru
> (`_load_grading_rules`). El resultat pràctic és el que es vol *precisament perquè* ara els POMs
> vénen del catàleg. La llei nova és la que fa certa la premissa del brief.

**4 · El llapis d'identitat.** El NOM (`nom_canonic_model`) segueix lliure — sobirania. La
NOMENCLATURA (`nom_fitxa`) passa la mateixa validació, amb el mateix missatge.

---

## Verificació (model 169, MAI el MILEY · tot amb rollback, residu +0)

```
1 · cercar «CHEST»    → pom 273, i el client en diu «A» (no «CH», que és la casa)
2 · crear amb 'U1'    → 409 · «U1» ja és Button spacing al catàleg d'aquest client.
3 · crear amb 'SEQ H' → 201 · àlies origen=MODEL pendent_revisio=True
4 · el POM nou ja es troba pel cercador del client
5 · i ara ELL col·lisiona, també en minúscules ('seq h')
6 · en assignar joc: OFICIAL resol regla SOL · PROPI no en té → «—» a Graduació
7 · nom_fitxa='U1' → 400 amb el motiu · nom_fitxa='SEQ-X' → 200 · el NOM → 200 sempre
```

| control | resultat |
|---|---|
| `manage.py check` | net |
| `npm run build` | net |
| `eslint` (fitxers tocats) | 0 errors |
| i18n ca/en/es | paritat, `editable_table` idèntic als tres |
| `migrate_schemas` | 0061 aplicada als 3 schemas (NO-OP a BD: només choices) |
| `qa_mount_modelsheet` · `qa_p02` · `qa_p02b` · `qa_p05d` | tots verds |

---

## 🚩 La conseqüència que has de saber

El cens honest dels «12 codis duplicats» diu una altra cosa de la que semblava:

- **4 són convivència legítima** (`C1`, `E4`, `E7`, `S2`): el mateix codi de casa per a un POM de
  Brownie i un de Losan. No és cap error — la unicitat del domini és `(customer, client_code)`.
- **El dany real són els ORFES: 93 POMs actius sense cap àlies.** Els va crear el camí d'import
  agafant el codi del document sense mirar el catàleg del client. El 440 («Height sequins
  piece») n'és un.

**Amb la llei nova, aquests 93 POMs deixen de ser trobables pel cercador.** Les files que ja hi
apunten segueixen funcionant (apunten per `pom_id`), o sigui que **res del que hi ha es trenca**
— però un tècnic no els podrà afegir a un model nou fins que tinguin àlies. Això no és un
efecte secundari a corregir: és la llei funcionant. El que cal és donar-los el seu àlies.

`backend/scripts_tmp/neteja_codis_duplicats.py` fa exactament això, **en sec**:

```
93 orfes · 32 amb mesures vives d'UN SOL client → reparables sols (l'script els proposa)
           61 sense amo clar                     → es llisten, decisió humana
```

La reparació **no esborra ni fusiona res**: crea l'àlies que falta al catàleg del client que ja
fa servir el POM, amb un codi que no xoqui (i si el natural xoca, ho diu i en proposa un altre).
Cap `BaseMeasurement` es toca, cap `pom_id` es reapunta. **Només escriu amb `APLICA=1`, i això
es fa amb tu al davant.**

---

## Anotat, fora d'abast

1. 🚩 **El camí d'import segueix sense el guard.** `extraction_views.py:1765` i `:1901` miren
   només `POMMaster.codi_client`, mai `CustomerPOMAlias`. És el camí que va fabricar els orfes;
   ara hi ha `colisio_de_codi` per fer-ho bé, però connectar-lo és un tram propi (toca el matcher
   i les seves 4 estratègies).
2. 🚩 **`find_pom_master` té la consulta duplicada** (`extraction_views.py:1030`): és la mateixa
   pregunta que ara respon `pom_del_codi`. Convergir-les faria que el matcher i la validació no
   poguessin divergir.
3. 🚩 `set-measurements` escriu `nom_fitxa` sense passar per la validació nova (només s'ha posat a
   `gravar-pom`, que és la porta de Definició POM). Les dues portes haurien de dir el mateix.
