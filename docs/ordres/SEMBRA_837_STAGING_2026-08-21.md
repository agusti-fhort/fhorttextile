# SEMBRA DEL MODEL 837 A STAGING · DRY-RUN

**Data:** 2026-08-21 · **Entorn:** staging `/var/www/ftt-staging`, branca `dev`, tenant `fhort`
**Font:** `docs/ordres/MODEL_837_EXPORT.json` (foto READ-ONLY de PROD, model pk PROD=1215, `TRV-SS27-0001`)
**Command:** `backend/fhort/models_app/management/commands/sembra_model_837.py`
**Estat:** ⛔ **ATURAT AL DRY-RUN.** Res escrit a la BD ni al disc. Calen 3 decisions d'Agus.

```bash
cd /var/www/ftt-staging/backend
venv/bin/python manage.py sembra_model_837            # dry-run (per defecte)
```

---

## 1. Veredicte: 3 bloquejos

L'`--apply` està bloquejat per tres motius. Cap és un error del command: són tres decisions
que no li toca prendre a la sembra.

| # | Bloqueig | Naturalesa | Desbloqueig |
|---|---|---|---|
| 1 | `Customer TRV` i `UserProfile fhort` **no existeixen a staging** | falta entorn | crear-los (decisió d'Agus) |
| 2 | 30 dels 142 POMMaster resolen per codi però **el contingut divergeix** | LLEI S44 | `--accepta-discrepancies-pom` |
| 3 | El hash del joc `BRW-CATALEG-v3` **no coincideix** amb el de la foto | ancoratge | `--accepta-ruleset-divergent` |

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

## 3. Bloqueig 1 — entorn absent

- **`Customer` codi `TRV`** (TROVELS): no hi és. És el customer del **model**; el del joc de
  regles és `BRW` i aquest sí que hi és. Sense ell el model no té propietari.
- **`UserProfile` amb username `fhort`**: no hi és. A PROD és el `pk=1`; a staging el `pk=1`
  és `a.devant@fhort.cat` — **el mateix pk, un altre actor**. Aquest usuari és qui va crear
  la `FittingSession` #123 (l'oberta), el `PieceFitting` #16 i n'és l'assistent.

La sembra no els crea (regla 3 de l'ordre). Opcions per a Agus:

1. Crear `Customer TRV` i un `UserProfile` amb username `fhort` a staging, i re-córrer el dry-run.
2. Decidir un actor de staging que substitueixi `fhort` (p.ex. `a.devant@fhort.cat`) — llavors cal
   una opció de mapatge explícita al command, perquè **la substitució silenciosa d'un actor és
   exactament el que la regla 4 prohibeix**.

---

## 4. Bloqueig 2 — 30 POM amb contingut divergent (LLEI S44)

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

## 5. Bloqueig 3 — hash del joc de regles

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

Dues coses per mirar al banc: **cap de les 6 versions aplica el `2.00`** de la regla, i a
v1–v5 el pas per sota de la base és **−2.0, no −3.0** (asimetria que el pas de 3.0 no explica).

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
el document sencer (451–1624 bytes cadascun).

---

## 8. Què falta per tancar

1. **Decisió d'Agus** sobre els 3 bloquejos (§3, §4, §5).
2. `--apply` amb les banderes que corresponguin.
3. Verificació independent post-apply: recomptes per ORM · regla `D` amb 2.00/0.50/0.50 ·
   v6 vigent amb pas 0.5 i v1–v5 amb 3.0 · `/api/schema/` = 200 · model visible a l'app (login manual).
4. 2a execució del command → **0 creacions** (idempotència per `codi_intern`).

**Cap push.** El command és un sol commit a `dev`, en local.
