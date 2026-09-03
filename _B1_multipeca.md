# B1 · MULTIPEÇA VIVA — cens de lectura pura

Data: 2026-08-07 · **MODE LECTURA PURA** (cap escriptura, cap migració, cap `manage.py` que
escrigui). Working dir `/var/www/ftt-staging`, branca `HEAD` detached (últim commit `ab78b14f`).

**Convenció.** Cada afirmació porta `fitxer:línia`. «NO EXISTEIX» = confirmat absent al codi.
Recomptes de BD via `psql` amb `SET search_path` (cap ORM, cap `manage.py shell`).

**Titular.** La diagnosi que el brief demana contrastar (`DIAGNOSI_MULTIPECA_DALIA.md`,
27/07/2026 matí) va quedar **superada el mateix dia a la tarda** pel sprint SET-1 (4 commits,
27/07). El seu diagnòstic central —«`GarmentSet` és un embrió mai encès, sense frontend»— **ja
no és cert**. El que sí que segueix cert és el fet més important per a la decisió d'ELEMENTS:
**0 files de `GarmentSet` i 0 files de `GarmentTypeItemPart` als DOS esquemes**. La màquina
existeix sencera i **mai s'ha engegat**.

---

## B1.1 · `create_model_wizard`: les DUES branques

**Ubicació:** `backend/fhort/models_app/views.py:788-1032`
(no és a `pom/wizard_views.py`; aquell fitxer és el wizard d'import de fitxa).
**Ruta:** `POST /api/v1/models/create-wizard/` → `backend/fhort/models_app/urls.py:213`
(`from ... import create_model_wizard` a `urls.py:13`).
**Consumidor de frontend:** `frontend/src/pages/ModelWizard.jsx:455-486` (`models.createWizard`).

### El repartidor: qui decideix la branca

La branca **NO** la decideix el payload. La decideix el **GTI** (`GarmentTypeItem.is_set`).
`views.py:841-878`:

```python
    # ── SET-1 · A4 — EL GTI MANA. Decisió 3 del sprint SET: és l'item qui declara PEÇA o
    #    CONJUNT, no el payload. `is_multipiece`/`num_pieces` (que cap superfície de frontend
    #    enviava) queden com a redundància: si contradiuen el GTI, 400 — mai s'endevina.
    item_triat = garment_fields.get('garment_type_item')
    parts_del_set = []
    if item_triat is not None and item_triat.is_set:
        parts_del_set = list(
            item_triat.parts.select_related(
                'part_item', 'part_item__garment_type',
                'part_item__grading_rule_set', 'part_item__base_size_definition',
            ).order_by('ordre', 'id'))
        if len(parts_del_set) < 2:
            return Response({... 'codi': 'set_sense_composicio'}, status=400)
        if 'is_multipiece' in request.data and not is_multipiece:
            return Response({... 'codi': 'contradiccio_gti_set'}, status=400)
        if num_pieces is not None and int(num_pieces) != len(parts_del_set):
            return Response({... 'codi': 'contradiccio_gti_num_pieces'}, status=400)
        is_multipiece = True
        num_pieces = len(parts_del_set)
    elif is_multipiece:
        # El camí llegat (N peces idèntiques d'un item que NO és conjunt) deixa d'existir: amb
        # la decisió 3, un conjunt és una declaració del catàleg. Es rebutja explícitament en
        # comptes de crear N models bessons que cap GTI no reconeixeria com a peces.
        return Response({... 'codi': 'contradiccio_gti_no_set'}, status=400)
```

`is_multipiece` / `num_pieces` es llegeixen del payload a `views.py:801-803`, però **només com a
redundància verificable**. Els 4 codis d'error del repartidor: `set_sense_composicio`,
`contradiccio_gti_set`, `contradiccio_gti_num_pieces`, `contradiccio_gti_no_set`.

### La numeració, comuna a les dues branques (`views.py:880-911`)

```python
    # next_num must look ONLY at base codes (FTT-SS26-NNNN), NOT at piece codes
    # (FTT-SS26-NNNN-NN). ...
    # We scan BOTH Model.codi_intern base codes AND GarmentSet.codi_base, because
    # a set's base number is consumed (its pieces are NNNN-01/-02) and must not be
    # reused by a later single model.
    base_pattern = f"^{prefix}-{season}{year_short}-[0-9]{{4}}$"
    with connection.cursor() as cursor:
        cursor.execute("SELECT codi_intern FROM models_app_model WHERE codi_intern ~ %s", [base_pattern])
        candidates = [r[0] for r in cursor.fetchall()]
        cursor.execute("SELECT codi_base FROM models_app_garmentset WHERE codi_base ~ %s", [base_pattern])
        candidates += [r[0] for r in cursor.fetchall()]
```

→ **SQL cru, sense schema qualificat** (depèn del `search_path` del tenant). Escaneja **dues
taules**: `models_app_model` i `models_app_garmentset`. El codi base d'un conjunt **consumeix
número**.

### BRANCA 1 — PEÇA ÚNICA (`views.py:913-953`)

Condició: `if not is_multipiece:` (`views.py:914`).

```python
    # Single piece (~90%): unchanged flow, no GarmentSet.
    if not is_multipiece:
        model = Model.objects.create(
            codi_intern=codi_base,
            codi_client=ref_client, customer=customer, codi_tenant=prefix,
            any=int(year), temporada=season, sequencial=next_num,
            nom_prenda=nom_prenda or None, descripcio=descripcio or None,
            collection=collection or '', created_by=creator,
            estat='Nou', data_objectiu=data_objectiu,
            **garment_fields,
        )
        if model.grading_rule_set_id:
            from fhort.models_app.services import (materialize_model_grading_rules,
                                               origen_mgr_des_de_ruleset)
            with transaction.atomic():
                materialize_model_grading_rules(
                    model, model.grading_rule_set.regles.all(),
                    origen=origen_mgr_des_de_ruleset(model.grading_rule_set))
        return Response({'id': model.id, 'codi_intern': model.codi_intern}, status=201)
```

**Què crea:** 1 `Model`. **A quines taules escriu:**

| Taula | Com |
|---|---|
| `models_app_model` | 1 fila (`Model.objects.create`, `views.py:915`) |
| `models_app_modelgradingrule` | N files, **només si** hi ha ruleset (`materialize_model_grading_rules`, `:948-951`) |

**Forma de la resposta:** `{'id', 'codi_intern'}`, 201.
**Transaccionalitat:** el `Model.objects.create` és **FORA** de la transacció; l'`atomic()` només
embolcalla la materialització de regles. Degradació gràcil documentada a `:930-937`.

### BRANCA 2 — CONJUNT / MULTI-PEÇA (`views.py:955-1032`)

Es fa en dos temps: **resolució per peça** (fora de transacció) i **escriptura atòmica**.

Temps 1 — cada peça resol el SEU món (`views.py:955-979`):

```python
    base_payload = {k: request.data.get(k) for k in (
        'garment_type_item_id', 'garment_type_id', 'size_system_id', 'grading_rule_set_id',
        'target', 'construction', 'size_run', 'base_size')}
    noms_peces = request.data.get('noms_peces') or {}
    if not isinstance(noms_peces, dict):
        return Response({'error': '`noms_peces` ha de ser un objecte {part_id: nom}.'}, status=400)

    camps_per_peca = []
    for part in parts_del_set:
        d_part = dict(base_payload)
        d_part['garment_type_item_id'] = part.part_item_id
        # El ruleset i la talla base de la PEÇA manen sobre els del payload; si la peça no en
        # declara, s'hereta el del conjunt (que és el que passava abans per a totes).
        if part.part_item.grading_rule_set_id:
            d_part['grading_rule_set_id'] = part.part_item.grading_rule_set_id
        if part.part_item.base_size_definition_id:
            d_part['base_size'] = part.part_item.base_size_definition.etiqueta
        fields_part, err_part = _resolve_garment_def(d_part)
        if err_part:
            err_part['peca'] = part.ordre
            return Response(err_part, status=400)
        nom_peca = (noms_peces.get(str(part.id)) or noms_peces.get(part.id) or '').strip()
        camps_per_peca.append((part, fields_part, nom_peca))
```

Temps 2 — escriptura (`views.py:981-1032`):

```python
    # Multi-piece: one GarmentSet + N piece Models, codi_intern = codi_base-NN.
    with transaction.atomic():
        garment_set = GarmentSet.objects.create(
            codi_base=codi_base, nom_comercial=nom_prenda or '', num_pieces=num_pieces,
        )
        pieces = []
        for i, (part, fields_part, nom_peca) in enumerate(camps_per_peca, start=1):
            piece = Model.objects.create(
                codi_intern=f"{codi_base}-{str(i).zfill(2)}",
                codi_client=ref_client, customer=customer, codi_tenant=prefix,
                any=int(year), temporada=season, sequencial=next_num,
                nom_prenda=(nom_peca or part.nom_peca or nom_prenda) or None,
                descripcio=descripcio or None, collection=collection or '',
                created_by=creator, estat='Nou', data_objectiu=data_objectiu,
                garment_set=garment_set,
                piece_number=i,
                **fields_part,
            )
            if piece.grading_rule_set_id:
                from fhort.models_app.services import (materialize_model_grading_rules,
                                               origen_mgr_des_de_ruleset)
                materialize_model_grading_rules(
                    piece, piece.grading_rule_set.regles.all(),
                    origen=origen_mgr_des_de_ruleset(piece.grading_rule_set))
            pieces.append({'id': piece.id, 'codi_intern': piece.codi_intern,
                           'piece_number': piece.piece_number, 'nom_prenda': piece.nom_prenda,
                           'garment_type_item': piece.garment_type_item_id})

    return Response({
        'garment_set_id': garment_set.id, 'codi_base': garment_set.codi_base,
        'num_pieces': garment_set.num_pieces, 'pieces': pieces,
    }, status=201)
```

**Què crea:** 1 `GarmentSet` + N `Model` (un per part de la composició del GTI).
**A quines taules escriu:**

| Taula | Com |
|---|---|
| `models_app_garmentset` | 1 fila (`views.py:983`) |
| `models_app_model` | N files amb `garment_set_id` + `piece_number` (`views.py:990-1009`) |
| `models_app_modelgradingrule` | N×M files, una tanda **per peça** i amb el ruleset **de la peça** (`:1013-1018`) |

**Forma de la resposta:** `{'garment_set_id', 'codi_base', 'num_pieces', 'pieces': [...]}`, 201.
**No hi ha `id`** — el frontend ho gestiona a `ModelWizard.jsx:473-481` (navega a `pieces[0].id`).
**Transaccionalitat:** TOT dins d'un sol `atomic()`; una fallada avorta el conjunt sencer.

### Diferències materials entre les dues branques

| | Peça única | Conjunt |
|---|---|---|
| Condició | GTI amb `is_set=False` | GTI amb `is_set=True` i ≥2 parts |
| `codi_intern` | `PFX-SS26-0001` | `PFX-SS26-0001-01`, `-02`, … |
| `garment_type_item` | el del payload | **el de cada `part_item`** (`:967`) |
| `grading_rule_set` | el del payload | el de la **part**, amb fallback al del payload (`:970-971`) |
| `base_size` | el del payload | el de la **part**, amb fallback (`:972-973`) |
| `nom_prenda` | del payload | `noms_peces[part.id]` → `part.nom_peca` → `nom_prenda` (`:1000`) |
| Atomicitat | només la materialització | tot |
| Resposta | `{id, codi_intern}` | `{garment_set_id, codi_base, num_pieces, pieces[]}` |

### La porta compartida: `_resolve_garment_def` (`views.py:710-786`)

La comparteixen la creació (les dues branques) i `update_model_step2` (`views.py:1061`).
Resol `garment_type_item` → deriva `garment_type` i `garment_group`; `size_system`;
`grading_rule_set` (tolerant); `target`; `construction`; `size_run` (via `run_del_model`,
porta única S24b, `:768-784`); `base_size_label`.

---

## B1.2 · Contrast amb `DIAGNOSI_MULTIPECA_DALIA.md`

Fitxer llegit sencer: `/var/www/ftt-staging/docs/diagnosis/DIAGNOSI_MULTIPECA_DALIA.md`
(402 línies, 2026-07-27, Patró A read-only).

**Context que la diagnosi no podia saber:** el mateix 27/07, després d'escriure-la, es va
dimensionar (`docs/diagnosis/DIAGNOSI_DIMENSIONAT_SET1_COPIA.md`) i **executar** el sprint SET-1,
en 4 commits + 1 deploy:

```
f3200dcc 2026-07-27 feat(cataleg): el GTI declara PECA o CONJUNT (SET-1)
20804146 2026-07-27 feat(meritacio): SET = 1 merit — l'albara ancora al conjunt (SET-1 A3)
607e15f7 2026-07-27 feat(creacio): un GTI-conjunt fa neixer les seves parts amb mon propi (SET-1 A4+A6)
31009911 2026-07-27 feat(federacio): el traspas conserva el conjunt (SET-1 C6)
1758199c 2026-07-27 Deploy: còpia de POMs model→model + SET-1 (…)
```

### Taula de contrast, fila per fila de la TAULA FINAL de DALIA

| # DALIA | Deia | Avui (07/08) | Veredicte |
|---|---|---|---|
| 1 | `GarmentSet` model + migració EXISTEIX | `models_app/models.py:43-77`; `0019_…` | **SEGUEIX CERT** (però el model té 1 camp MÉS: `consumption_started_at`, `:67-69`, migració `0065_set1_meritacio_conjunt`) |
| 2 | `Model.garment_set` + `piece_number` EXISTEIX | `models_app/models.py:214-221` | **SEGUEIX CERT** |
| 3 | 0 files a `fhort` i `los` | 0 i 0 (§B1.4) | **SEGUEIX CERT** |
| 4 | Creació via API wizard EXISTEIX (`views.py:824-870`) | `views.py:981-1032` | **CERT però REESCRIT**: ja no clona `**garment_fields`; cada peça resol el seu món |
| 5 | Creació via import massiu EXISTEIX | `bulk_import_service.py:495-531`, `:18` | **SEGUEIX CERT, SENSE CANVIS** |
| 6 | **Frontend de multi-peça NO EXISTEIX** (0 hits) | 3 superfícies (§B1.3) | **JA NO ÉS CERT** |
| 7 | Fitting sobre un set EXISTEIX | `fitting/models.py:281-286`, `:344-347`; `services.py:153-155` | **SEGUEIX CERT, SENSE CANVIS** |
| 8 | Camp de secció a les mesures NO EXISTEIX | `BaseMeasurement.seccio`, `models_app/models.py:675` | **JA NO ÉS CERT** (F3, 27/07 tarda) |
| 9 | **Clau `('model','pom')` EXISTEIX i BLOQUEJA** | `unique_together = [('model','pom','capa','instancia')]`, `models_app/models.py:769` | **JA NO ÉS CERT** — vegeu sota |
| 10 | Sufix TOP/PANTIE: decisió ajornada, mai implementada | cap POMMaster amb sufix; el mecanisme segueix sense existir | **SEGUEIX CERT** |
| 11 | Detector multi-model EXISTEIX | `extraction_views.py` cribratge | **SEGUEIX CERT** |
| 12 | Tractament de seccions: FUSIONA | el parser ara **captura** `seccio` per POM | **PARCIALMENT SUPERAT**: segueix fusionant a la mateixa llista, però ja no perd l'etiqueta |
| 13 | Branca no cablejada per separar seccions NO EXISTEIX | cap consumidor estructural de `seccio` | **SEGUEIX CERT** |
| 14 | Secció d'origen ES PERD a l'extracció | `extraction_views.py:421,433-436,464`; IA `:1621`; propagació `:1216`; desat a `BaseMeasurement.seccio` | **JA NO ÉS CERT** |
| 15 | Parser llegeix només el primer full | `extraction_views.py:1349` (cens de fulls) i fixture `smoke_multipeca_2fulls_3seccions.xlsx` a `test_parser_excel.py:563-573` | **JA NO ÉS CERT** |
| 16 | Meritació per peça NO EXISTEIX (és per Model) | `_meritar_conjunt`, `tasks/services_c.py:191-239` | **JA NO ÉS CERT**: hi ha meritació de conjunt, **SET = 1 mèrit** |
| 17 | Meritació activa: SÍ (33 events) | **46 events** a `public.backoffice_modelconsumptionevent` | **CERT, xifra actualitzada** |
| 18 | No es dispara en desar un model | `tasks/services_c.py`; `services_batec.py:62-71` | **SEGUEIX CERT** (cal `ModelTask`→`InProgress` o batec) |
| 19 | Packs del manifest SS27 NO EXISTEIXEN | sense canvis | **SEGUEIX CERT** |
| 20 | Cap validació que compti peces al món comercial | `num_pieces` només a `fitting/services.py:155` | **SEGUEIX CERT** |
| 21-22 | Bugs de talla base del pas 2 | fora d'abast d'aquest B1; no verificats | no contrastat |

### Els tres punts on DALIA **ja no descriu el codi**

**(a) «`GarmentSet` és un embrió mai encès, sense frontend» (§Resum executiu 1, taula §6).**
Fals avui. Hi ha 3 superfícies de frontend (§B1.3), 2 serializers, un badge a la llista i a la
fitxa, i un bloc de composició al wizard. El que **segueix sent cert** és el nucli dur del
diagnòstic: **0 files**. La màquina està encesa i **no ha arrencat mai**.

**(b) «El bloqueig no és un camp que falta: és la clau `('model','pom')`» (§Resum executiu 2,
taula §9).** El comentari del propi codi que ho cita **ha quedat obsolet**:

```python
# models_app/models.py:669-674
    # ⚠️ LÍMIT CONEGUT, no resolt aquí (DIAGNOSI_MULTIPECA_DALIA §Q2 i taula final §9): la
    # clau segueix sent `unique_together = [('model','pom')]`. Si DUES seccions del mateix
    # document comparteixen un POM, el confirm en col·lapsa les files i la que sobreviu es
    # queda amb la secció de l'ÚLTIMA — aquest camp no ho pot arreglar, perquè el bloqueig
    # no és el camp que faltava sinó la clau. …
```

…però 100 línies més avall, la clau REAL és de **quatre** columnes:

```python
# models_app/models.py:769
        unique_together = [('model', 'pom', 'capa', 'instancia')]
```

Verificat a BD (`fhort`):

```
 models_app_basemeasureme_model_id_pom_id_capa_ins_8405ced0_uniq | UNIQUE (model_id, pom_id, capa, instancia)
 models_app_basemeasurement_instancia_exigeix_nom                | CHECK (NOT (instancia > '' AND nom_fitxa = ''))
 models_app_basemeasurement_ordre_check                          | CHECK (ordre >= 0)
```

**I les comportes que C1 havia posat (`capa='exterior'` només, `instancia=''` només) JA NO HI
SÓN** — les va retirar el tram C4. L'única que queda és `instancia_exigeix_nom`. O sigui: el
mateix POM **ja pot existir N vegades al mateix model**, discriminat per `(capa, instancia)`, i
res a BD no ho impedeix. Els comentaris de `models.py:712-753` descriuen `instancia` com «de
QUINA DE LES REPETICIONS d'aquest mateix POM parla: la sisa dreta i l'esquerra». **Aquest és
l'eix de repetició que DALIA declarava inexistent.**

**(c) «Cap camí d'UI que en creï un, tret de l'Excel» (§Q1).** Fals avui: el `ModelWizard` en
crea un quan el GTI triat és `is_set`. Però hi ha una **porta que falta i que ningú documenta**:
**cap superfície de frontend permet declarar un GTI com a conjunt ni editar-ne la composició.**
L'endpoint existeix (`PUT /api/v1/garment-type-items/<id>/parts/`, `tasks/views_b.py:1020-1078`)
i `is_set` és escrivible pel PATCH genèric (`tasks/serializers_b.py:243-252`), però
`frontend/src/pages/ItemAuthoring.jsx` **no té cap hit de `is_set` ni de `parts`** i
`frontend/src/api/endpoints.js:515-522` **no exposa cap crida a `/parts/`**. Això explica
mecànicament el 0/0 de la BD: **el wizard sap fer conjunts, però no hi ha manera de declarar-ne
un al catàleg des de l'aplicació.**

---

## B1.3 · Cens EXHAUSTIU de multipeça

### 3.1 · Models (taules) i els seus camps

| Model | Fitxer:línia | Camps |
|---|---|---|
| `models_app.GarmentSet` | `backend/fhort/models_app/models.py:43-77` | `codi_base` (CharField 40, **unique**), `nom_comercial` (200, blank), `num_pieces` (PositiveSmallInteger, *«Immutable després de la creació»*), `created_at`, `consumption_started_at` (null, SET-1·A3, `:69`). `Meta.ordering=['codi_base']` |
| `tasks.GarmentTypeItemPart` | `backend/fhort/tasks/models.py:483-544` | `set_item` (FK→GarmentTypeItem, **CASCADE**, related_name=`parts`), `part_item` (FK→GarmentTypeItem, **PROTECT**, related_name=`part_of`), `ordre` (PositiveSmallInteger, dona el sufix -01/-02), `nom_peca` (120, blank). `unique_together=[('set_item','part_item')]` (`:512`). `clean()` (`:515-541`): anti-auto-referència, **anti-set-de-sets**, anti-cicle A↔B |

### 3.2 · Camps en ALTRES models que hi apunten

| Camp | Fitxer:línia | Forma |
|---|---|---|
| `models_app.Model.garment_set` | `models_app/models.py:214-220` | FK → `GarmentSet`, **SET_NULL**, null/blank, related_name=`peces` |
| `models_app.Model.piece_number` | `models_app/models.py:221` | PositiveSmallInteger, null/blank |
| `tasks.GarmentTypeItem.is_set` | `tasks/models.py:428-430` | Boolean, **default=False**, «la composició viu a GarmentTypeItemPart» |
| `fitting.FittingSession.garment_set` | `fitting/models.py:281-286` | FK → `GarmentSet`, **CASCADE**, related_name=`fitting_sessions` |
| `fitting.FittingSession` CheckConstraint | `fitting/models.py:341-348` | `fittingsession_set_xor_model` — set XOR model, mai tots dos, mai cap |
| `models_app.ConsumptionRecord.garment_set` | `models_app/models.py:1197-1199` | **OneToOne** → `GarmentSet`, CASCADE, related_name=`consumption_record` |
| `models_app.ConsumptionRecord` CheckConstraint | `models_app/models.py:1210-1216` | `consumptionrecord_model_xor_set` |
| `models_app.BaseMeasurement.seccio` | `models_app/models.py:675` | CharField 60, blank — rètol de secció del document («01.- DRESS»). **Descriptiu, cap consumidor estructural** |

### 3.3 · Migracions

| Migració | Què fa |
|---|---|
| `models_app/migrations/0019_garmentset_model_piece_number_model_garment_set.py:15,36` | crea `GarmentSet` + els 2 camps de `Model` |
| `tasks/migrations/0041_garmenttypeitem_set_i_parts.py` | crea `GarmentTypeItem.is_set` + la taula `GarmentTypeItemPart` |
| `models_app/migrations/0065_set1_meritacio_conjunt.py:16,31` | `ConsumptionRecord.garment_set` + el CHECK XOR |
| `fitting/migrations/0008_fittingsession_piecefitting_fittingphoto_and_more.py:30,93` | `FittingSession.garment_set` + el CHECK XOR |

### 3.4 · Vistes / endpoints

| Punt | Fitxer:línia | Rol |
|---|---|---|
| `create_model_wizard` | `models_app/views.py:788-1032` | **ÚNIC escriptor interactiu** de `GarmentSet` |
| `models_app/urls.py:213` | `models/create-wizard/` | ruta |
| import de `GarmentSet` a views | `models_app/views.py:26` | — |
| `ModelViewSet` prefetch | `models_app/views.py:160-162` | `select_related('garment_set')` + `prefetch_related('garment_set__peces')` |
| `GarmentTypeItemViewSet` | `tasks/views_b.py:993-1010` | prefetch `parts__part_item`; **`filterset_fields` inclou `is_set`** (`:1010`) |
| `GarmentTypeItemViewSet.parts` | `tasks/views_b.py:1020-1078` | **`PUT /api/v1/garment-type-items/<id>/parts/`** — reemplaçament declarat de la composició; gate CONFIGURE; crida `clean()` de cada fila |
| `tasks/urls.py:36-37` | `garment-type-items` router | ruta |
| `FittingSessionViewSet` | `fitting/views.py:153,161,226,240` | `filterset_fields` inclou `garment_set`; `schedule` accepta `garment_set_id` |
| `planning` gantt/calendari | `planning/views.py:343,377,395,487` | `select_related('garment_set')`; el títol de l'event cau a `garment_set.codi_base` quan no hi ha model |
| **NO EXISTEIX** | — | **cap endpoint propi de `GarmentSet`** (0 hits de `garment-sets` a tots els `urls*.py`) |

### 3.5 · Serializers

| Punt | Fitxer:línia |
|---|---|
| `GarmentSetMiniSerializer` | `models_app/serializers.py:87-105` — `('id','codi_base','nom_comercial','num_pieces','peces')`; `peces` = SerializerMethodField amb `{id, codi_intern, piece_number, nom_prenda}` |
| `ModelListSerializer.garment_set` | `models_app/serializers.py:125` (**read_only**) + `:183-184` als `fields` (`garment_set`, `piece_number`) |
| `ModelSerializer` (detall) `.garment_set` | `models_app/serializers.py:277` (**read_only**; desviació anotada a `:272-276` — abans `__all__` l'exposava com a pk escrivible) |
| `GarmentTypeItemPartSerializer` | `tasks/serializers_b.py:218-228` — `('id','part_item','part_item_code','part_item_name','ordre','nom_peca')` |
| `GarmentTypeItemSerializer` | `tasks/serializers_b.py:243-252` — `parts` **read_only** niuat; **`is_set` escrivible** pel PATCH genèric |
| `fitting` serializers | `fitting/serializers.py:80-82` (`target` derivat), `:128`, `:162`, `:185` |

### 3.6 · Serveis i lògica de domini

| Punt | Fitxer:línia | Rol |
|---|---|---|
| `_meritar_conjunt` | `tasks/services_c.py:191-239` | **SET = 1 mèrit**: marca el `GarmentSet`, estampa TOTES les germanes, crea **1 sol** `ConsumptionRecord` ancorat al set amb `code_snapshot = codi_base` |
| `_meritar_model` | `tasks/services_c.py:172-189` | camí del model sol |
| dispatcher | `tasks/services_batec.py:62-71` | `if model.garment_set_id: _meritar_conjunt(...) else: _meritar_model(...)` |
| `bulk_import_service` | `:18` (columnes `es_conjunt`/`referencia_conjunt`/`piece_number`), `:141`, `:147` (instruccions), `:309-324` (validació), `:347-348`, `:404-406` (recompte), `:427-441` (`_classify` → `set_groups`), `:444-450` (`_group_by_season`), `:495-531` (creació de `GarmentSet` + peces), `:730` | 2n escriptor de `GarmentSet` |
| `fitting/services.schedule_session` | `fitting/services.py:133-176` | XOR model/set (`:147-148`); `n = GarmentSet.num_pieces or 1` (`:153-155`) |
| segellat de sessió | `fitting/services.py:626`, `:793`, `:816-820`, `:850` | un set només segella si totes les peces estan resoltes |
| `federation_service` (anada) | `tenants/federation_service.py:88`, `:116-119` | serialitza `set_codi_base`, `set_nom_comercial`, `set_num_pieces`, `piece_number`. **`consumption_started_at` NO viatja mai** |
| `federation_service` (retorn) | `tenants/federation_service.py:149`, `:200-203`, `:226-227` | `GarmentSet.objects.get_or_create(codi_base=…)` — clau natural, tolerant a l'ordre i a traspassos parcials |
| `models_app/services.py:42` | comentari de la llei de numeració | — |

### 3.7 · Management commands

| Command | Fitxer:línia | Rol |
|---|---|---|
| `reconcile_consumption` | `backoffice/management/commands/reconcile_consumption.py:59-135` (`_reconcile_sets`), `:173-187` (models sols amb `garment_set__isnull=True`) | repesca forats de meritació de conjunt |
| `instantiate_external_models` | `tenants/management/commands/instantiate_external_models.py:58-62` | informa dels `GarmentSet` tocats al traspàs |
| `bootstrap_tenant` | `tasks/management/commands/bootstrap_tenant.py:60`, `:136`, `:159-161` | `GarmentTypeItemPart` al grup `garments`, clau natural `('set_item','part_item')` |
| `export_losan_package` | `pom/management/commands/export_losan_package.py:34`, `:229`, `:234-240` | exporta `is_set` i les files de composició |
| `load_losan_package` | `pom/management/commands/load_losan_package.py:34`, `:311`, `:313-321` | upsert per clau natural |
| `seed_losan_models` | `models_app/management/commands/seed_losan_models.py:208` | `'piece_number': None` |

### 3.8 · Tests

| Fitxer | Cobreix |
|---|---|
| `backend/fhort/models_app/test_set1_creacio.py` (163 l.) | A4+A6: 2 parts amb GTI distint, rulesets propis, contradiccions → 400 |
| `backend/fhort/tasks/test_set1_composicio.py` | composició del catàleg (anti-cicle, anti-set-de-sets) |
| `backend/fhort/tasks/test_set1_meritacio.py` (156 l.) | SET = 1 mèrit, idempotència |
| `backend/fhort/tenants/tests_traspas_conjunt.py` (132 l.) | traspàs parcial 2-de-3, `get_or_create` per `codi_base`, cap duplicat |
| `backend/fhort/models_app/test_parser_excel.py:563-573` | fixture `smoke_multipeca_2fulls_3seccions.xlsx` |

### 3.9 · FRONTEND

| Superfície | Fitxer:línia | Què fa |
|---|---|---|
| **Wizard · bloc de composició** | `frontend/src/pages/ModelWizard.jsx:706-733` | si `item.is_set`, pinta la composició en **LECTURA** (`item.parts`, `ordre` + `part_item_name`) amb un input per al nom de cada peça |
| Wizard · estat | `ModelWizard.jsx:88-90` | `const [setNoms, setSetNoms] = useState({})` |
| Wizard · payload | `ModelWizard.jsx:465-467` | `...(item?.is_set ? { noms_peces: … } : {})` |
| Wizard · resposta de conjunt | `ModelWizard.jsx:471-482` | detecta `r.data.pieces` i navega a `pieces[0].id` |
| **Fitxa de model · capçalera** | `frontend/src/pages/ModelSheet.jsx:1545-1570` | badge «SET n/N» + llista de germanes navegable, des de `garment_set.peces` |
| **Llista de models · badge** | `frontend/src/pages/Models.jsx:508-517` | badge SET amb tooltip `codi_base` + `nom_comercial` |
| i18n | `ca/es/en.json:955` (`models_list.set_badge`), `:1072-1074` (`model_wizard.set_title/set_hint/set_piece_name_ph`), `:1131-1132` (`model_sheet.set_badge/set_hint`) | 3 idiomes complets |
| Crida API | `frontend/src/api/endpoints.js:515-522` (`garmentTypeItems`) | **NO hi ha `parts()`** |
| **FORAT** | `frontend/src/pages/ItemAuthoring.jsx` | **0 hits de `is_set`, 0 hits de `parts`** — cap superfície per declarar un item-conjunt |
| **FORAT** | `frontend-backoffice/src` | **0 hits** de `garment_set` / `is_set` / `piece_number` |
| Fals positiu anotat | `frontend/src/components/pattern/PieceIdentityList.jsx:28` | comentari que aclareix que `GarmentTypeItemPart` **NO** són peces de patró |

### 3.10 · Grep ample: resultats de les paraules del brief

| Terme | Resultat |
|---|---|
| `GarmentSet` | 12 fitxers de codi + 4 migracions + 4 de test (llistats a §3.4-3.8) |
| `garment_set` | idem + 3 superfícies de frontend |
| `multipeca` / `multipeça` / `multi_peca` | **cap camp ni cap model**; només comentaris, docstrings i el nom d'una fixture (`test_parser_excel.py:573`) |
| `es_multipeca` | **0 hits al repo** |
| `is_multipiece` | només al payload del wizard (`views.py:801,842,859,871,873,914,939`) i als tests. **Cap hit de frontend** |
| `peces` | related_name de `Model.garment_set` (`models.py:219`), `noms_peces` del payload, `parts_del_set` |
| `GarmentTypeInstance` | **0 hits al repo** |
| `GTI` | 20+ hits, **tots amb el significat `GarmentTypeItem`** (`tasks/models.py:425`, `commerce/models.py:54,190-206`, `accounts/models.py:44`, `pom/models.py:978`, `views.py:836,841`) |

---

## B1.4 · Recompte de files a la BD, per schema

Schemes existents: `SELECT nspname FROM pg_namespace` → **`fhort`, `los`, `public`**.
Tenants (`public.tenants_client`): `1 public FHORT System` · `2 fhort FHORT Management` ·
`13 los LOSAN`.

**Cap taula de multipeça viu a `public`** (verificat: `information_schema.tables` per
`%garmentset%` / `%itempart%` / `%garmenttypeitem%` → només `fhort` i `los`; `public` no té cap
taula `models_app_*`).

```
===== SCHEMA fhort =====
 GarmentSet                        |     0
 Model TOTAL                       |     0
 Model amb garment_set             |     0
 Model amb piece_number            |     0
 GarmentTypeItem TOTAL             |    62
 GarmentTypeItem is_set=true       |     0
 GarmentTypeItemPart               |     0
 FittingSession amb garment_set    |     0
 ConsumptionRecord amb garment_set |     0
 ConsumptionRecord TOTAL           |     0

===== SCHEMA los =====
 GarmentSet                        |     0
 Model TOTAL                       |    51
 Model amb garment_set             |     0
 Model amb piece_number            |     0
 GarmentTypeItem TOTAL             |     1
 GarmentTypeItem is_set=true       |     0
 GarmentTypeItemPart               |     0
 FittingSession amb garment_set    |     0
 ConsumptionRecord amb garment_set |     0
 ConsumptionRecord TOTAL           |     0
```

`public.backoffice_modelconsumptionevent` = **46** (DALIA en deia 33).

### Sobre l'avís del brief («962 models LOS viuen a `fhort` — verifica-ho»)

**REFUTAT amb les dades d'avui.** `fhort.models_app_model` = **0 files**. `los` en té **51**,
totes amb `codi_tenant = 'LOS'`. La premissa era certa quan es va escriure (DALIA, 27/07,
comptava 1.056 models a `fhort` i 51 a `los`), però **el wipe del 06/08 va deixar `fhort` a
zero**. Per tant:

- **`fhort` no té cap model de cap mena** → el 0 de `garment_set` a `fhort` **no diu res** sobre
  si mai se n'ha creat cap. És un 0 derivat de la taula pare buida.
- **`los` és l'única població viva de models (51)**, i **cap** té `garment_set` ni
  `piece_number`. Aquest 0 **sí que és informatiu**: 51 models reals, cap conjunt.
- **El 0 realment decisiu és `GarmentTypeItemPart` = 0 als DOS esquemes, i `is_set=true` = 0
  als DOS esquemes.** Aquest no depèn de cap wipe de models: viu al **catàleg**, que la memòria
  del projecte dona per intacte. **Cap tenant ha declarat mai un item-conjunt.** L'única
  màquina que crea `GarmentSet` s'engega quan `is_set=True`, i aquesta condició no s'ha complert
  mai en tota la vida del projecte.
- **Conseqüència per a ELEMENTS:** no hi ha dades vives de multipeça a migrar, enlloc.
  Absorbir, redefinir o jubilar `GarmentSet` **no té cap cost de dades** — només cost de codi.

---

## B1.5 · PROPOSTA de noms per a l'entitat nova (no és una decisió)

**La col·lisió que el brief demana evitar és més gran del que sembla.** Al repo hi ha **tres**
paraules ja preses, no dues:

1. **`Set`** — `models_app.GarmentSet` (conjunt comercial de N models) **i** `pom.ItemBaseSet`
   (`pom/models.py:975`, que **no** és un conjunt de peces: és el satèl·lit de mesures base
   d'un item per món `item × size_system × fit`). Dos «set» amb semàntiques diferents.
2. **`Piece` / «peça»** — **triplement** carregada: `patterns.PatternPiece`
   (`patterns/models.py:150`, peça de patró), `fitting.PieceFitting`
   (`fitting/models.py:356`, peça avaluada en una sessió), i `Model.piece_number`
   (`models_app/models.py:221`, peça d'un conjunt comercial). 8 classes amb `Piece` al nom.
3. **🚨 `GTI`** — **el brief fa servir «GTI = garment type instance», però al repo `GTI` vol dir
   `GarmentTypeItem` a 20+ llocs** (`tasks/models.py:425`, `commerce/models.py:54,190-209`,
   `accounts/models.py:44`, `pom/models.py:978`, `models_app/views.py:836,841`, i el títol de
   `ProductPriceException` = *«Product price exception (GTI)»*). Si l'entitat nova es diu
   `GarmentTypeInstance`, l'acrònim `GTI` passa a ser **ambigu a tot el codi ja escrit** i cap
   grep no els podrà separar. Ho anoto com a troballa, no com a recomanació.

Cerca de col·lisió feta per a cada candidat (grep de classe i de string a
`backend/fhort` + `frontend/src`, exclosos `migrations/`):

| Candidat | Col·lisions al codi actual | Pro | Contra |
|---|---|---|---|
| **`ModelElement`** (camp `Model.elements`) | **CAP.** `ModelElement` → 0 hits. `class Element*` → 0 classes. `\belement\b` al backend → 5 hits, **tots en prosa de docstring** (`tenants/discovery_service.py:24`, `pom/services.py:808`, tests) — cap identifica cap entitat | Paraula del brief; zero col·lisió; el prefix `Model` el situa sense ambigüitat i encaixa amb `ModelTask`/`ModelGradingRule`/`ModelFitxer` ja existents | «element» és genèric: no diu que sigui una peça de roba. En una UI en català caldrà decidir com es diu («element» ≠ «peça», i l'usuari ja diu «peça») |
| **`ModelPiece`** (camp `Model.pieces`) | `ModelPiece` → 0 hits, però **`Piece` xoca frontalment**: `PatternPiece`, `PieceFitting`, `PieceFittingLine`, `PieceIdentityAcknowledgement`, `PieceMetadata`, `PieceData`, i `Model.piece_number` | És exactament la paraula del domini que fan servir l'Agus i el codi de multipeça | Amb `Model.piece_number` viu al mateix model, `ModelPiece` i `piece_number` conviurien sense ser la mateixa cosa fins que s'absorbeixi: ambigüitat màxima en el període de transició. `PieceFitting.model` apuntaria a `Model`, no a `ModelPiece` |
| **`ModelComponent`** (camp `Model.components`) | `ModelComponent` → 0 hits. `class Component*` → **0 classes al backend**. ⚠️ **`prod.components` SÍ existeix al frontend** (`frontend/src/pages/ProductDetail.jsx:218`, `parts = prod.components`) i `commerce` té `products.components_empty` a l'i18n | Zero col·lisió de classe; «component» ja el fa servir la diagnosi germana (`DIAGNOSI_COMPONENTS_MULTIPLES_MESURES.md`), o sigui que el vocabulari ja existeix en el projecte | El nom ja està ocupat al món **comercial** (composició d'un `Product`): dos «components» amb semàntiques diferents és exactament el problema que tenim amb «set» |
| **`ModelPart`** (camp `Model.parts`) | `ModelPart` → 0 hits, però **`parts` ja és un related_name viu**: `GarmentTypeItem.parts` → `GarmentTypeItemPart` (`tasks/models.py:500`), consumit a `views_b.py:996,1074`, `views.py:848`, `ModelWizard.jsx:711,716` | Continuïtat conceptual perfecta amb la composició del catàleg: `GarmentTypeItemPart` és la **plantilla** i `ModelPart` seria la **instància** | Dos `parts` a dues alçades (`item.parts` = plantilla, `model.parts` = instància) és elegant si es documenta i confús si no. Un grep de `.parts` deixa de ser concloent |
| **`GarmentInstance`** (camp `Model.garments`) | `GarmentInstance` → 0 hits. Però **`Garment*` és el prefix més carregat del repo: 24 classes** (`GarmentType`, `GarmentTypeGlobal`, `GarmentTypeItem`, `GarmentTypeItemPart`, `GarmentGroup`, `GarmentPOMMap`, `GarmentSet`…) | Diu literalment què és: la instància d'un tipus de peça de roba dins d'un model. Casa amb la formulació del brief | El 25è `Garment*`. I «instance» arrossega el conflicte de l'acrònim GTI descrit a dalt |

**Observació que va amb la proposta, no és una recomanació.** Sigui quin sigui el nom, hi ha
**dues** entitats candidates a ser absorbides i **no són intercanviables**:
`GarmentSet` (contenidor comercial de N `Model`, 0 files) i `GarmentTypeItemPart` (composició de
**catàleg**, plantilla, 0 files). Un ELEMENT «GTI sembrat dins del model» ocupa la posició de la
**instància** — que avui la fa un `Model` sencer amb `piece_number` — i deixa oberta la pregunta
de si `GarmentTypeItemPart` (la plantilla que diu de què es compon un conjunt) també s'absorbeix
o es conserva. Això és decisió Patró C i aquest informe no s'hi pronuncia.

---

## Què NO he pogut determinar en lectura

1. **Si el 0 de `GarmentTypeItemPart` a `fhort` és «mai s'ha usat» o «esborrat pel wipe».** La
  memòria del projecte diu que el wipe del 06/08 va tocar **models**, no el catàleg (i el
  catàleg de `fhort` té 62 GTI vius, que no s'haurien conservat si s'hagués esborrat el
  catàleg). Però **no he trobat cap evidència positiva** que ho tanqui: no hi ha `created_at` a
  `GarmentTypeItemPart` ni cap log consultable en lectura pura. El 0 de `los` (1 sol GTI, 0
  parts) sí que és net.
2. **Si el CHECK de C1 sobre `capa`/`instancia` es va retirar per migració declarada o per SQL
  a mà.** He verificat l'ABSÈNCIA a BD (`pg_constraint` sobre
  `fhort.models_app_basemeasurement` → només `instancia_exigeix_nom` i `ordre_check`), però no
  he auditat quina migració els va treure. El comentari de `models.py:722-723` diu «C4 el
  retirarà per migració»; el fet és que ja no hi són.
3. **Si l'`instancia` (`(model,pom,capa,instancia)`) és utilitzable com a eix de peça.** El camp
  existeix, la clau l'inclou i la comporta ha caigut, però els docstrings (`models.py:729-733`)
  el descriuen com «sisa dreta / esquerra, pit RELAXED / EXTENDED» — repeticions **dins** d'una
  peça, no **entre** peces. Si serveix per a ELEMENTS és una pregunta de disseny, no de lectura.
4. **Els bugs Q5 de DALIA** (talla base del pas 2, `extraction_views.py:419` vs `:358`) **no els
  he re-verificat**: queden fora de l'abast de B1 i el brief no els demana.
5. **Si `create_model_wizard` és l'únic camí interactiu.** Existeix un segon endpoint,
  `POST /api/v1/models/create-from-sheet/` (`models_app/urls.py:144` →
  `TechSheetCreateModelView`, `tech_sheet_views.py:238`), que **no he auditat**; el grep de
  `garment_set` no hi dona cap hit, o sigui que **no crea conjunts**, però no n'he llegit el cos.
6. **Cap comprovació contra PROD.** Tots els recomptes són de la BD de **staging**. PROD i
  staging divergeixen (la mateixa DALIA ho documentava: `LOS-SS27-0834` és DALIA a PROD i
  AMARANTA a staging).
