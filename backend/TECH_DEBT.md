# Tech Debt — runtime mismatches a la capa de grading/fitting

Aquest document llista les diferències entre el codi generat pels sprints
3 i 4 (services, views) i el schema real dels models. Tots els endpoints
estan registrats i retornen `401` sense token, però fallaran en runtime
quan es cridin amb dades reals fins que aquests punts es resolguin.

Última actualització: 2026-05-25 (post-sprint4 commit `0caab9a`).

## Resum executiu

| Component | Estat | Bloca quin flow |
|---|---|---|
| Endpoints HTTP + auth | ✓ Operatiu | — |
| Models de grading creats | ✓ Tots a la BD | — |
| Logica `_apply_rule` (motor pur) | ✓ Test passat | — |
| Lectura de GradingRule per nom de camp | ✗ | `generar_graded_specs` |
| Lectura de POMMaster per nom de camp | ✗ | `taula_mesures`, `crear_fitting` |
| Lectura/escriptura de `SizeFitting.estat_mesures` | ✗ | tot el flow de SF |
| `models_app.signals.sincronitzar_size_fitting` | ✗ | auto-creació SF al crear Model |

## 1. GradingRule — fields amb noms diferents — ✅ RESOLT

**Resolt seguint Opció A**. 3 substitucions a `pom/services.py`:
- `is_active` → `actiu` (al filter de `_load_grading_rules`)
- `rule.grading_type` → `rule.logica` (al `_apply_rule`)
- `rule.increment_cm or 0` → `float(rule.increment) if rule.increment else 0.0`
  (DecimalField necessita conversió per a math amb floats)

Camp `increment_above_xl` no existeix al model — el `getattr` ja gestionava
el fallback. Mantinguda la lògica STEP, ara amb `float()` explícit al
fallback també per consistència de tipus.

Test post-fix amb mock: LINEAR (54.5), FIXED (45.0), ZERO (0.0), STEP (56.0)
i confirmat amb GradingRule real a la BD (`logica=LINEAR, increment=0.7500,
actiu=True`).

Detalls del context original (mantenir per referència):

| Codi servei espera | Schema real té | Punts d'ús |
|---|---|---|
| `rule.is_active` | `rule.actiu` | [pom/services.py:207](fhort/pom/services.py#L207) (`_load_grading_rules` filter) |
| `rule.grading_type` | `rule.logica` | [pom/services.py:280](fhort/pom/services.py#L280) (`_apply_rule`) |
| `rule.increment_cm` | `rule.increment` (DecimalField) | [pom/services.py:281](fhort/pom/services.py#L281) (`_apply_rule`) |
| `rule.increment_above_xl` | (no existeix) | [pom/services.py:288](fhort/pom/services.py#L288) (`_apply_rule` STEP) |

**Opció A (recomanada)**: adaptar el codi del servei al schema real.
```python
# fhort/pom/services.py
GradingRule.objects.filter(rule_set_id=..., actiu=True)  # era is_active
grading_type = rule.logica                                # era rule.grading_type
increment = float(rule.increment) if rule.increment else 0  # era rule.increment_cm
# increment_above_xl: getattr ja gestiona el cas amb fallback, però mai serà servit
```

**Opció B**: afegir camps alias al model (`is_active = property(lambda s: s.actiu)`).
Menys invasiu però duplica conceptes.

## 2. POMMaster — fields que no existeixen al tenant — ✅ RESOLT

**Resolt amb Opció A**: 5 `@property` al POMMaster que delegen a `pom_global`
i `categoria` (read-only). 2 ORM `order_by` ajustades a `pom__categoria__display_order`
(camí real al schema). `select_related` ampliat a `'pom__pom_global', 'pom__categoria'`
per evitar N+1 a les 3 queries crítiques.

Verificació amb dades reals al schema fhort (POMMaster id=1):
- `pom_code='AB'`, `name_cat='Across Back (FHORT std)'`, `name_en='...'`,
  `display_order=1`, `is_key_measure=False`

`is_key_measure` retorna sempre `False` (no hi ha info al schema). Si el
frontend ho necessita per a UX, caldrà afegir BooleanField explícit al
POMMaster (migració).

Detalls del context original (mantenir per referència):

POMMaster real té: `actiu, categoria (FK), codi_client, id, nom_client, notes, pom_global (FK)`.

| Codi servei espera | Schema real té | Punts d'ús |
|---|---|---|
| `pom.pom_code` | `pom.codi_client` (o `pom.pom_global.codi` global) | [fitting/services.py:69](fhort/fitting/services.py#L69), [pom/grading_views.py:94,121](fhort/pom/grading_views.py#L94) |
| `pom.name_cat` | `pom.pom_global.nom_ca` (via FK al global) | [fitting/services.py:69](fhort/fitting/services.py#L69), [pom/grading_views.py:95,122](fhort/pom/grading_views.py#L95) |
| `pom.name_en` | `pom.pom_global.nom_en` | [fitting/services.py:69](fhort/fitting/services.py#L69), [pom/grading_views.py:96,123](fhort/pom/grading_views.py#L96) |
| `pom.display_order` | (no existeix; POMCategory en té un) | [pom/grading_views.py:86,97,124,137](fhort/pom/grading_views.py#L86), [pom/views.py:85](fhort/pom/views.py#L85), [fitting/services.py:196](fhort/fitting/services.py#L196) |
| `pom.is_key_measure` | (no existeix) | [pom/grading_views.py:99,125](fhort/pom/grading_views.py#L99) |

**Opció A**: afegir un layer de propietats al POMMaster.
```python
class POMMaster(models.Model):
    # ... camps existents ...
    @property
    def pom_code(self): return self.codi_client
    @property
    def name_cat(self): return self.pom_global.nom_ca if self.pom_global_id else self.nom_client
    @property
    def name_en(self): return self.pom_global.nom_en if self.pom_global_id else self.nom_client
```

**Opció B**: afegir camps reals `display_order` i `is_key_measure` (cal migració).

**Opció C**: canviar tot el codi del servei perquè usi els noms reals. Més canvis però sense afegir abstraccions.

## 3. SizeFitting — `estat_mesures` no existeix — ✅ RESOLT

**Resolt seguint Opció A** (adaptar codi al schema). 8 substitucions backend
+ 4 frontend. Resposta JSON inclou ambdues claus: `estat` (Django key,
canonical) + `estat_display` (label llegible). Verificat amb serializer:
`estat='BaseTancada'`, `estat_display='Base tancada'`.

Detalls del context original (mantenir per referència):

SizeFitting real té només `estat` amb choices: `Pendent, BaseOberta, BaseTancada, TallesGenerades, Tancat`.

Codi servei usa `estat_mesures` amb valors literals: `'Pendent', 'Talla base oberta', 'Talla base tancada', 'Talles generades', 'Tancat'`.

| Punt d'ús | Acció |
|---|---|
| [fitting/services.py:29,31](fhort/fitting/services.py#L29) | check `sf.estat_mesures not in ('Talles generades', 'Tancat')` |
| [pom/services.py:111](fhort/pom/services.py#L111) | update `estat_mesures='Talles generades'` |
| [pom/services.py:131,133](fhort/pom/services.py#L131) | check `sf.estat_mesures not in ('Talla base oberta', 'Pendent')` |
| [pom/services.py:140](fhort/pom/services.py#L140) | update `estat_mesures='Talla base tancada'` |
| [pom/grading_views.py:142](fhort/pom/grading_views.py#L142) | returna `'estat_mesures': sf.estat_mesures` |
| [models_app/signals.py:96](fhort/models_app/signals.py#L96) | create `estat_mesures='Pendent'` — **silent fail** ara (signal embolicat en try) |

**Opció A (recomanada)**: mapejar els valors literals als choices reals i renombrar `estat_mesures` → `estat` als 8 punts:
- `'Pendent'` → `'Pendent'` ✓
- `'Talla base oberta'` → `'BaseOberta'`
- `'Talla base tancada'` → `'BaseTancada'`
- `'Talles generades'` → `'TallesGenerades'`
- `'Tancat'` → `'Tancat'` ✓

**Opció B**: afegir camp `estat_mesures` separat al SizeFitting. Permet dos cicles d'estat (un de mesures, un d'aprovació). Més invasiu i confús.

## 4. models_app.signals.sincronitzar_size_fitting — ✅ RESOLT

Senyal netejat + descoberts i corregits bugs col·laterals del pre_save:

- **fields_to_copy loop eliminat** (no servia: els camps `garment_type_id`,
  `garment_group_id`, `grading_rule_set_id`, etc. no existeixen al SizeFitting;
  viuen al Model i s'accedeixen via `sf.model.X`).
- **Create funcional**: auto `numero=1`, auto `codi={model.codi_intern}-SF1`,
  default `tipus='Proto'`, `creat_per_id=instance.responsable_id`.
- **Skip si Model.responsable és None** (creat_per requerit + PROTECT a SizeFitting).
- **Pre_save signal `generar_codi_model` arreglat de pas** (era trencat des
  de sprint2): `instance.client_id` → `getattr(instance, 'client_id', None)`
  amb fallback a `codi_client` CharField; SQL crua amb `"any"` quoted
  (paraula reservada PostgreSQL); set `codi_intern` només si no està definit.

Verificat end-to-end: crear un Model amb `responsable` set genera un SizeFitting
amb `codi=TEST...-SF1, numero=1, tipus=Proto, estat=Pendent`.

Bonus afegit al sprint d'aquest fix: `Model.darrera_activitat` + signal
`actualitzar_darrera_activitat` (post_save, queryset.update() per bypassar
recursió de signals).

Detalls del context original (mantenir per referència):

Aquest signal crea automàticament un SizeFitting quan es crea un Model.
Té dos problemes (un derivat del #3):

[fhort/models_app/signals.py:90-110](fhort/models_app/signals.py#L90)

1. Setea `estat_mesures='Pendent'` (no existeix → tota la creació falla silenciosament).
2. `fields_to_copy` inclou `garment_group_id` que no existeix a Model (només `garment_type` existeix). El loop fa `getattr(instance, 'garment_group_id', None)` així que retorna None i s'ometen els camps inexistents.

**Acció**: arreglar el #3 i revisar el bloc. Probable que altres camps copiats també no existeixin al SizeFitting.

## 5. ModelTasca.fase / ModelTasca.gate no existeixen — ✅ RESOLT

**Resolt al commit posterior** seguint Opció B. Smoke test post-fix:
- `GET /api/v1/models/50/resum-tasques/` → 200 `{"model_id":50,"per_estat":{},"total":0}`
- `POST /api/v1/model-tasques/999/processar-gate/` → 404 `{"error":"Tasca no trobada"}`

Detalls del context original (mantenir per referència històrica):

Detectat al smoke test (commit `4ef2594`): `GET /api/v1/models/50/resum-tasques/` retorna **500 FieldError**:

```
Cannot resolve keyword 'fase' into field. Choices are: color_codi, cost_real,
data_limit, es_gate, estat, gate_data, gate_notes, gate_revisat_per, hores_reals,
id, item_ref, minuts_assignats, minuts_reals, model, ordre, paquet_origen,
responsable, resultat_gate, slots_base, slots_reals, tasca, timers, tipus_encarrec
```

`ModelTasca` té `es_gate` (boolean) però **no té `fase` ni `gate`** com a camps directes. Aquests viuen a `Tasca` (el catàleg) i s'haurien d'accedir via la FK `model_tasca.tasca.fase` / `.tasca.gate` — o copiats com a camps denormalitzats a la creació.

**Punts d'ús (sistemàtic — afecta tot el flow de tasques):**

| Fitxer:línia | Codi actual | Què passa |
|---|---|---|
| [tasks/action_views.py:45](fhort/tasks/action_views.py#L45) | `if not mt.gate:` | AttributeError quan es crida `processar-gate` |
| [tasks/action_views.py:72](fhort/tasks/action_views.py#L72) | `.values('estat', 'fase', 'gate')` | FieldError 500 (✗ confirmat al smoke test) |
| [tasks/services.py:85](fhort/tasks/services.py#L85) | `ModelTasca.objects.create(... fase=t['fase'] ...)` | TypeError al crear ModelTasca (kwargs invàlids) |
| [tasks/services.py:88](fhort/tasks/services.py#L88) | `ModelTasca.objects.create(... gate=t['gate'] ...)` | igual — la generació de tasques peta abans d'arribar a BD |
| [tasks/services.py:136](fhort/tasks/services.py#L136) | `(t.fase for t in tasques if ...)` | AttributeError dins `recalcular_fase_actual` |
| [tasks/services.py:143](fhort/tasks/services.py#L143) | `tasques[0].fase` | AttributeError |
| [tasks/services.py:163](fhort/tasks/services.py#L163) | `if not mt.gate or mt.estat != 'Feta':` | AttributeError dins `processar_gate` |
| [tasks/services.py:188](fhort/tasks/services.py#L188) | `if t.gate:` | AttributeError |
| [tasks/signals.py:37](fhort/tasks/signals.py#L37) | `if instance.estat == 'Feta' and instance.gate:` | AttributeError al `post_save` |

Tot el flow de tasques (generar, recalcular fase, processar gate) està **trencat fins que es resolgui**. L'únic motiu pel qual no s'ha vist fins ara és que no hi ha ModelTasca creats a la BD.

**Opció A (simplest, denormalitza)**: afegir `fase` i `gate` com a camps a `ModelTasca`, copiar-los des de `Tasca` a `generar_tasques_model`. ModelTasca ja té `es_gate` que duplica `tasca.gate` — afegir-hi `fase` (CharField, choices) i renombrar referències `mt.gate` → `mt.es_gate`. Una migració.

**Opció B (canonical Django)**: substituir tots els accessos:
- `mt.gate` → `mt.tasca.gate` (Python) o `mt.es_gate` si volem evitar JOIN
- `mt.fase` → `mt.tasca.fase` (Python) o `'tasca__fase'` (queryset)
- `.values('estat', 'fase', 'gate')` → `.values('estat', 'tasca__fase', 'tasca__gate')`
- `ModelTasca.objects.create(fase=..., gate=...)` → eliminar aquests kwargs (la info ja viu via FK a tasca_ref)

Sense migració però amb 9 punts de canvi.

**Recomanació**: B + mantenir `es_gate` existent com a denormalització actual. El que el sprint2 anomenava `gate` ja existeix com a `es_gate`. Per a `fase` no hi ha denormalització actual — el query `'tasca__fase'` és la via natural.

## Pla suggerit (en ordre)

1. ~~**#5 ModelTasca.fase/gate**~~ — ✅ RESOLT
2. ~~**#3 SizeFitting.estat_mesures**~~ — ✅ RESOLT
3. ~~**#1 GradingRule fields**~~ — ✅ RESOLT
4. ~~**#2 POMMaster fields**~~ — ✅ RESOLT
5. ~~**#4 Signal sincronitzar_size_fitting**~~ — ✅ RESOLT

**Tots els 5 punts del TECH_DEBT inicial resolts.** El flow end-to-end de
creació de Model → auto-SF → grading → fitting wizard hauria de ser viable
ara amb dades reals. Pendent: cobertura de tests d'integració.

Tots aquests punts es poden tractar en un sol PR `chore: align grading/tasks services with schema`. Cap requereix nous models ni migracions a banda del que ja està commited (excepte opció A del #5 si es trien camps denormalitzats).
