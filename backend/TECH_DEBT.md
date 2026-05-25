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

## 1. GradingRule — fields amb noms diferents

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

## 2. POMMaster — fields que no existeixen al tenant

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

## 3. SizeFitting — `estat_mesures` no existeix

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

## 4. models_app.signals.sincronitzar_size_fitting

Aquest signal crea automàticament un SizeFitting quan es crea un Model.
Té dos problemes (un derivat del #3):

[fhort/models_app/signals.py:90-110](fhort/models_app/signals.py#L90)

1. Setea `estat_mesures='Pendent'` (no existeix → tota la creació falla silenciosament).
2. `fields_to_copy` inclou `garment_group_id` que no existeix a Model (només `garment_type` existeix). El loop fa `getattr(instance, 'garment_group_id', None)` així que retorna None i s'ometen els camps inexistents.

**Acció**: arreglar el #3 i revisar el bloc. Probable que altres camps copiats també no existeixin al SizeFitting.

## Pla suggerit (en ordre)

1. **#3 SizeFitting.estat_mesures** — el més bloquejant. Sense això el signal post-create de Model no fa res i res no podrà generar SF automàticament.
2. **#1 GradingRule fields** — 3 substitucions concretes (`actiu`, `logica`, `increment`).
3. **#2 POMMaster fields** — opció A (properties) és la més ràpida; opció C la més neta.
4. **#4 Signal** — un cop resolts els altres, revisar el contingut.

Tots aquests punts es poden tractar en un sol PR `chore: align grading services with schema`. Cap requereix nous models ni migracions a banda del que ja està commited.
