# DEUTE — `codi_intern`: tres generadors i dos formats

> Obert el 2026-07-14 pel sprint **IMPORT** (fix del comptador del bulk).
> Estat: **candidat de sprint propi**. Aquí NO hi ha res trencat *ara mateix* — el sprint
> IMPORT va tapar el forat que sagnava. Això és el deute que el va fer possible.

## El fet

Tres camins creen models i cadascun es fabrica el número i el codi pel seu compte. Cap
d'ells sap dels altres.

| # | Camí | D'on treu el número | Format que escriu | Toca `ModelSequence`? |
|---|---|---|---|---|
| 1 | Signal `generate_model_code` — [signals.py:71-80](../../backend/fhort/models_app/signals.py#L71-L80) | `SELECT MAX(sequencial)` | `BRW-26-SS-0002` (`{CUST}-{YY}-{TT}-{NNNN}`) | **No** |
| 2 | Wizard — [views.py:383](../../backend/fhort/models_app/views.py#L383) i [views.py:514-525](../../backend/fhort/models_app/views.py#L514-L525) | MAX sobre els **codis** existents (`LIKE base%`) | `BRW-SS26-0001` (`{CUST}-{TT}{YY}-{NNNN}`) | **No** |
| 3 | Import massiu — [services.py:38](../../backend/fhort/models_app/services.py#L38) → [bulk_import_service.py:446](../../backend/fhort/models_app/bulk_import_service.py#L446) | comptador `ModelSequence` | `BRW-SS26-0001` | **Sí** (l'únic) |

Dues conseqüències, totes dues visibles a la BD de staging avui:

1. **Dos formats conviuen** per al mateix client i temporada: `BRW-SS26-0001` (wizard) i
   `BRW-26-SS-0002` (signal). No és cosmètic: qualsevol codi que ordeni, agrupi o parsegi
   `codi_intern` per posició ha de conèixer els dos.
2. **El número i el codi poden desalinear-se.** El camí 2 deriva el següent número del text
   del codi; el camí 1, de `sequencial`. Un model amb `codi_intern` acabat en `0016` i
   `sequencial=3` és perfectament possible — i és exactament el forat pel qual encara pot
   entrar una col·lisió (per això el sprint IMPORT hi va deixar una xarxa: 409 llegible a
   [bulk_import_views.py](../../backend/fhort/models_app/bulk_import_views.py), no un 500).

## Què va passar (per què això és aquí)

El primer import massiu de Brownie a PROD (20 models) petava amb un 500. El comptador del
bulk començava per 1 en un client que ja tenia models creats pels camins 1 i 2 → `codi_intern`
(unique) → `IntegrityError`, **després** d'un preview que deia "20 files OK". El sprint IMPORT
va fer el comptador monòton respecte del terreny (`max(comptador, MAX(sequencial) real)`).

Això **atura el sagnat, no cura la malaltia**: el comptador ja no contradiu la BD, però
seguim amb tres fonts de veritat per a un sol espai de números.

## La feina (sprint propi)

1. **UN servei canònic** de `codi_intern` + `sequencial` — l'únic autoritzat a repartir
   números, amb `select_for_update` sempre. Els tres camins passen a cridar-lo; el signal es
   queda com a xarxa per als creadors que no el criden, o desapareix.
2. **UN format.** Decisió de producte (l'Agus): quin dels dos mana. El que perdi necessita
   **migració de dades** dels codis ja emesos — i cal auditar abans qui depèn del format
   (PDF d'albarà, cerques, exports, la fitxa `.ftt`).
3. **Reconciliar `sequencial` amb el codi** allà on hagin divergit, com a pas previ.

**Dimensió estimada: mitjana-gran.** El codi és poc (un servei + tres crides), però arrossega
una migració de dades sobre una columna `unique` que ja és a PROD i una decisió de format que
toca superfícies de cara al client. No és un sprint de tarda: vol la seva diagnosi de radi
(qui llegeix `codi_intern`) abans de tocar res.

## Zona de risc

`codi_intern` és la clau que el client veu i diu per telèfon. Qualsevol canvi de format és
visible per a ells i probablement irreversible a la pràctica. La migració ha de ser una
decisió de l'Agus, no una conseqüència d'un refactor.
