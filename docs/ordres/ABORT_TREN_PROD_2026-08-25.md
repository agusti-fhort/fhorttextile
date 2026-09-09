# ABORT · TREN M1–M5 A PRODUCCIÓ · 2026-08-25

> **Estat: AVORTAT al PAS 0.** Cap escriptura, cap migració, cap restart, cap push.
> Tot el que segueix és **read-only**.

## Veredicte

El pas 0 de l'ordre diu: «llegeix `docs/ordres/GATE_TREN_2026-08-25.md`; si NO és APTE,
atura't». **El document no existeix enlloc de la màquina.** Sense gate no hi ha APTE, i
sense APTE l'ordre mateixa mana aturar-se. A més, la màquina on s'ha executat l'ordre
**no és producció**.

## Les quatre premisses falses

| Premissa de l'ordre | Realitat mesurada |
|---|---|
| Host `178.105.217.125` | Aquesta màquina és `fhort-assessment`, **`178.105.48.204`** |
| `/var/www/fhort-textile` | **No existeix** (`find /` sencer, 0 resultats) |
| `docs/ordres/GATE_TREN_2026-08-25.md` | **No existeix** cap fitxer `GATE_TREN*` ni cap doc amb «APTE» a cap `docs/ordres` |
| `fhort.service` = el back de textile | `fhort.service` **existeix i corre**, però és `FHORT Assessment Gunicorn`, `WorkingDirectory=/var/www/assessment` — **una altra aplicació, també viva** |

## 🚨 El perill concret

El pas 7 (`systemctl restart fhort.service`) **hauria trobat un servei amb aquest nom
i l'hauria reiniciat**: el d'*Assessment*, servit per nginx (`sites-enabled/assessment`).
Un restart cec d'un servei aliè en producció, sense cap error visible que avisés.

El back de textile d'aquesta màquina és `ftt-staging.service` (`/var/www/ftt-staging`),
que és **staging**, no PROD.

## Per què PROD no és abastable des d'aquí

- `/root/.ssh/config` no té cap entrada d'host.
- `known_hosts` **no conté `178.105.217.125`**.

PROD és una màquina a part — ho confirma `docs/ordres/DIAGNOSI_BUGS_PROD_837_2026-08-21.md`,
que l'encapçala com `PROD 178.105.217.125 · /var/www/fhort-textile`. **No s'hi ha intentat
connectar**: amb el tren avortat al pas 0, obrir sessió contra producció no toca.

## Passos no executats (tots)

1. **Re-cens 64/189** — vol la BD de PROD, que no és aquí. La de staging donaria una xifra
   d'un altre univers i el pas 1 la compararia com si fos la bona.
2. **`pg_dump`** — no fet.
3. **`git fetch` / `merge origin/dev`** — no fet. *(Nota, amb refs locals i sense fetch:
   al clon de staging `main..origin/dev` són **1.011 commits**, no els ~5 fitxers de
   migració que l'ordre espera. Xifra possiblement ranci; el tren la vol re-mesurada
   contra el remot des de PROD.)*
4. **Migracions** — no tocades.
5. **Retroactiu R1** — no llançat. L'script sí que consta provat a staging
   (`RETROACTIU_R1_STAGING_DRYRUN.md`, `IMPLEMENTACIO_M5_DIA_2026-08-25.md`).
6. **`npm ci` / build** — no fet.
7. **Restart** — **no fet, deliberadament** (vegeu «el perill concret»).
8. **Verificació canònica** — no aplicable.

## ⏰ La finestra ja és tancada

Ordre: 7:30–9:00, «a les 9:00, desplegat o avortat». Hora d'execució: **11:42 UTC**
(13:42 per l'Agus, UTC+2). La finestra havia passat de llarg abans de començar.

## Què cal de l'Agus per reprendre-ho

1. **Publicar el gate de nit** `GATE_TREN_2026-08-25.md` amb veredicte APTE explícit.
2. **Executar el tren des de PROD** (`178.105.217.125:/var/www/fhort-textile`), o obrir
   accés des d'aquí i dir-ho a l'ordre.
3. **Corregir el nom del servei** a l'ordre: a PROD, verificar que `fhort.service` és de
   debò el back de textile abans que cap pas el reiniciï.
4. **Finestra nova.**
