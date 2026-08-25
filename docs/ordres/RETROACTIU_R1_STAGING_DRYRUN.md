# M5 · RETROACTIU DE LA R1 — llista de validació (DRY-RUN)

> Generat per `ops/retroactius/retroactiu_r1_m5.py` (en sec, cap escriptura).

### Tenant `fhort` — **5 models · 18 tasques**

| model | codi | tasques que adopta | data_inici proposada | board ara → després |
|---|---|---|---|---|
| **1320** | `BRW-FW26-0001` · Blusa KAYCE | **5** — `pom`(Paused) · `size_check`(Done) · `grading`(Done) · `tech_sheet`(Paused) · `pattern_digit`(Paused) | `2026-08-09 16:42` | `paused` → `paused` |
| **1322** | `BRW-26-FW-0002` · [QA-SET2] Blusa KAYCE | **2** — `size_check`(Paused) · `pom`(Paused) | `2026-08-10 10:43` | `paused` → `paused` |
| **1379** | `BRW-FW26-0002` · RUFFLES | **4** — `pom`(Paused) · `size_check`(Paused) · `grading`(Paused) · `tech_sheet`(Paused) | `2026-08-16 14:51` | `paused` → `paused` |
| **1383** | `TRV-SS27-0001` · 837 VESTIT | **5** — `pom`(Done) · `size_check`(Paused) · `grading`(Paused) · `tech_sheet`(Paused) · `pattern_digit`(Paused) | `2026-08-20 16:53` | `paused` → `paused` |
| **1496** | `QA-M1-0005` · [QA-M1] Llegat sense volta (pre-llei) | **2** — `pom`(Done) · `tech_sheet`(Pending) | `2026-08-24 20:44` | `pending` → `pending` |

### Tenant `los` — **0 models · 0 tasques**

_Cap model pre-llei: res a fer._

---

**TOTAL: 5 models · 18 tasques.**

Guarda per a l'apply:

```
venv/bin/python ../ops/retroactius/retroactiu_r1_m5.py --apply \
    --espera-models 5 --espera-tasques 18
```

---

## Les lleis que aquesta llista aplica

| | |
|---|---|
| **FIT-4 · l'univers** | Models amb **almenys una `ModelTask`**. Els **29 models de `fhort` sense cap tasca NO reben R1** (ni els 51 de `los`): mai han tingut cap gest de treball, i fabricar-los una volta seria inventar-la. |
| **FIT-1 · neixen OBERTES** | `tancada_el = NULL` i **cap `Entrega` fabricada**. Per això **cap model canvia a «Entregats»** — la columna d'entregats és un FET D'ENTREGA, i aquí no se'n declara cap. |
| **Adopció total** | La R1 adopta **TOTES** les tasques `ronda = NULL` del model. Aquí ja no hi ha «buit» ni «pre-primera»: **tot el passat és R1**. |
| **Només s'escriu `ronda`** | Ni `motiu`, ni `mare`, ni estats, ni timers, ni Welford, ni cap `TaskTransition`. És **ompliment, no un gest**. `updated_at` tampoc es mou (`update()` de queryset no dispara `auto_now`). |

**Cap model es mou de columna al board** (la darrera columna de la taula: totes les fletxes van a
la mateixa paraula). Era el resultat esperat i està mesurat, no suposat: cap dels cinc models té
tota la feina a `Done`, o sigui que cap no vivia a la 4a columna per l'excepció pre-llei.

## 🚩 DUES COSES QUE VOLEN EL TEU ULL ABANS DE L'APPLY

### 🚨 1 · El model **1383** hi és — i és el banc del fil motor

`TRV-SS27-0001 · 837 VESTIT` és el banc que diverses lleis de la casa declaren **intocable**
(«patterns/** i model 1383 intocables»). Hi entra perquè té 5 tasques amb `ronda = NULL` i la
llei no l'exclou.

- **El retroactiu NO li toca res del motor**: ni graduació, ni patrons, ni mesures, ni POMs.
  L'única escriptura és `ModelTask.ronda` a les seves 5 tasques, més una fila `Ronda` nova.
- **Sí que li canvia la CARA**: el seu Pla de treball passarà de pla a per-voltes (un contenidor
  «R1»), i el Registre li ensenyarà la volta. El board no el mou (`paused → paused`).
- **Si queda fora, queda un model pre-llei viu**, i llavors la FASE 2 no es pot fer: les dues
  excepcions autoextingibles només es poden retirar si la població és **zero**.

**La meva recomanació: incloure'l.** «Intocable» ha volgut dir sempre *no li toquis el motor*, i
això no l'hi toca. Però és el teu banc i la decisió és teva.

### 🚩 2 · `QA-M1-0005` — el pre-llei FABRICAT

`[QA-M1] Llegat sense volta (pre-llei)` el fabrica `ops/qa/banc_m1_rondes.py` a posta, i és
**l'únic cas del banc que no es pot muntar pel camí normal**: existeix precisament per poder
veure les dues branques que la FASE 2 retira.

**El que faig: adoptar-lo com la resta, I retirar-lo del banc.** Adoptar-lo sol no n'hi ha prou —
un `banc_m1_rondes.py --remunta` **tornaria a fabricar un model pre-llei** l'endemà, i
ressuscitaria una població que el codi ja no sabrà explicar. Les dues coses van juntes o cap.

---

## ⏸️ ESTAT: PENDENT DE VALIDACIÓ

L'apply **no s'ha executat**. Quan validis la llista:

```
cd backend && venv/bin/python ../ops/retroactius/retroactiu_r1_m5.py --apply \
    --espera-models 5 --espera-tasques 18
```

Si l'univers ha canviat entremig, la guarda **avorta sense escriure** i demana revalidar.
