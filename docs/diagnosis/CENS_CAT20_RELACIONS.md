# CAT2.0 · CENS PREGUNTANT ALS MODELS (read-only)

## Relacions entrants declarades (des dels MODELS, no de la BD)

| entitat | qui hi apunta | camp | on_delete | db_constraint | mena |
|---|---|---|---|---|---|
| `pom.SizeSystem` | `pom.SizeSystem` | `parent` | SET_NULL | True | FK |
| `pom.SizeSystem` | `pom.SizeDefinition` | `size_system` | CASCADE | True | FK |
| `pom.SizeSystem` | `pom.ItemBaseSet` | `size_system` | PROTECT | True | FK |
| `pom.SizeSystem` | `pom.GradingRuleSet` | `size_system` | PROTECT | True | FK |
| `pom.SizeSystem` | `pom.SizingProfile` | `size_system` | PROTECT | True | FK |
| `pom.SizeSystem` | `models_app.Model` | `size_system` | SET_NULL | True | FK |
| `pom.SizeDefinition` | `pom.ItemBaseSet` | `base_size_definition` | PROTECT | True | FK |
| `pom.SizeDefinition` | `pom.GradingRule` | `talla_base` | PROTECT | True | FK |
| `pom.SizeDefinition` | `tasks.GarmentTypeItem` | `base_size_definition` | SET_NULL | True | FK |
| `pom.SizingProfile` | `pom.SizingProfile` | `parent_profile` | SET_NULL | True | FK |
| `pom.GarmentType` | `pom.RuleSetScopeNode` | `garment_type` | CASCADE | True | FK |
| `pom.GarmentType` | `pom.ClientMesuraPerfil` | `garment_type` | CASCADE | True | FK |
| `pom.GarmentType` | `pom.SizingProfile` | `garment_type` | PROTECT | True | FK |
| `pom.GarmentType` | `models_app.Model` | `garment_type` | SET_NULL | True | FK |
| `pom.GarmentType` | `tasks.GarmentTypeItem` | `garment_type` | CASCADE | True | FK |
| `pom.GarmentGroup` | `pom.SizeSystem` | `grups` | — | True | M2M |
| `pom.GarmentGroup` | `pom.GarmentType` | `grup_ref` | PROTECT | True | FK |
| `pom.GarmentGroup` | `pom.GradingRuleSet` | `garment_group` | PROTECT | True | FK |
| `pom.GarmentGroup` | `pom.RuleSetScopeNode` | `garment_group` | CASCADE | True | FK |
| `pom.GarmentGroup` | `models_app.Model` | `garment_group` | SET_NULL | True | FK |

⚠️ **0 relacions amb `db_constraint=False`** — invisibles a `information_schema`:


## SCHEMA `public`

### `pom.SizeSystem` · 14 files

| qui hi apunta | via | camp | on_delete | dbc | files |
|---|---|---|---|---|---|
| `pom.SizeDefinition` | DIRECTE | `size_system` | CASCADE | True | **70** |
| `pom.GradingRuleSet` | DIRECTE | `size_system` | PROTECT | True | **1** |

### `pom.SizeDefinition` · 70 files

| qui hi apunta | via | camp | on_delete | dbc | files |
|---|---|---|---|---|---|
| _(cap referència directa)_ | | | | | |

### `pom.SizingProfile` · 0 files

| qui hi apunta | via | camp | on_delete | dbc | files |
|---|---|---|---|---|---|
| _(cap referència directa)_ | | | | | |

### `pom.GarmentType` · 0 files

| qui hi apunta | via | camp | on_delete | dbc | files |
|---|---|---|---|---|---|
| _(cap referència directa)_ | | | | | |

### `pom.GarmentGroup` · 8 files

| qui hi apunta | via | camp | on_delete | dbc | files |
|---|---|---|---|---|---|
| _(cap referència directa)_ | | | | | |



## SCHEMA `fhort`

### `pom.SizeSystem` · 26 files

| qui hi apunta | via | camp | on_delete | dbc | files |
|---|---|---|---|---|---|
| `pom.SizeDefinition` | DIRECTE | `size_system` | CASCADE | True | **165** |
| `pom.ItemBaseSet` | DIRECTE | `size_system` | PROTECT | True | **1** |
| `pom.GradingRuleSet` | DIRECTE | `size_system` | PROTECT | True | **39** |
| `pom.SizingProfile` | DIRECTE | `size_system` | PROTECT | True | **37** |
| `pom.ItemBaseSet` | **VIA FILL** `SizeDefinition` (165) | `base_size_definition` | PROTECT | True | **1** |
| `pom.GradingRule` | **VIA FILL** `SizeDefinition` (165) | `talla_base` | PROTECT | True | **1267** |
| `tasks.GarmentTypeItem` | **VIA FILL** `SizeDefinition` (165) | `base_size_definition` | SET_NULL | True | **2** |

### `pom.SizeDefinition` · 165 files

| qui hi apunta | via | camp | on_delete | dbc | files |
|---|---|---|---|---|---|
| `pom.ItemBaseSet` | DIRECTE | `base_size_definition` | PROTECT | True | **1** |
| `pom.GradingRule` | DIRECTE | `talla_base` | PROTECT | True | **1267** |
| `tasks.GarmentTypeItem` | DIRECTE | `base_size_definition` | SET_NULL | True | **2** |

### `pom.SizingProfile` · 37 files

| qui hi apunta | via | camp | on_delete | dbc | files |
|---|---|---|---|---|---|
| `pom.SizingProfile` | DIRECTE | `parent_profile` | SET_NULL | True | **1** |

### `pom.GarmentType` · 21 files

| qui hi apunta | via | camp | on_delete | dbc | files |
|---|---|---|---|---|---|
| `pom.RuleSetScopeNode` | DIRECTE | `garment_type` | CASCADE | True | **1** |
| `pom.ClientMesuraPerfil` | DIRECTE | `garment_type` | CASCADE | True | **20** |
| `pom.SizingProfile` | DIRECTE | `garment_type` | PROTECT | True | **37** |
| `tasks.GarmentTypeItem` | DIRECTE | `garment_type` | CASCADE | True | **62** |
| `pom.GarmentPOMMap` | **VIA FILL** `GarmentTypeItem` (62) | `garment_type_item` | CASCADE | False | **1748** |
| `pom.ItemBaseSet` | **VIA FILL** `GarmentTypeItem` (62) | `garment_type_item` | CASCADE | False | **1** |
| `pom.ItemBaseMeasurement` | **VIA FILL** `GarmentTypeItem` (62) | `garment_type_item` | CASCADE | False | **37** |
| `pom.GradingRuleSet` | **VIA FILL** `GarmentTypeItem` (62) | `garment_type_item` | SET_NULL | False | **1** |
| `pom.RuleSetScopeNode` | **VIA FILL** `GarmentTypeItem` (62) | `garment_type_item` | CASCADE | False | **9** |
| `models_app.ItemFitxer` | **VIA FILL** `GarmentTypeItem` (62) | `garment_type_item` | CASCADE | True | **1** |
| `models_app.ImportSession` | **VIA FILL** `GarmentTypeItem` (62) | `tipologia_confirmada` | SET_NULL | True | **24** |
| `tasks.TaskTimeEstimate` | **VIA FILL** `GarmentTypeItem` (62) | `garment_type_item` | CASCADE | True | **463** |

### `pom.GarmentGroup` · 12 files

| qui hi apunta | via | camp | on_delete | dbc | files |
|---|---|---|---|---|---|
| `pom.GarmentType` | DIRECTE | `grup_ref` | PROTECT | True | **21** |
| `pom.GradingRuleSet` | DIRECTE | `garment_group` | PROTECT | True | **18** |
| `pom.RuleSetScopeNode` | DIRECTE | `garment_group` | CASCADE | True | **1** |



## SCHEMA `los`

### `pom.SizeSystem` · 2 files

| qui hi apunta | via | camp | on_delete | dbc | files |
|---|---|---|---|---|---|
| `models_app.Model` | DIRECTE | `size_system` | SET_NULL | True | **30** |

### `pom.SizeDefinition` · 0 files

| qui hi apunta | via | camp | on_delete | dbc | files |
|---|---|---|---|---|---|
| _(cap referència directa)_ | | | | | |

### `pom.SizingProfile` · 0 files

| qui hi apunta | via | camp | on_delete | dbc | files |
|---|---|---|---|---|---|
| _(cap referència directa)_ | | | | | |

### `pom.GarmentType` · 1 files

| qui hi apunta | via | camp | on_delete | dbc | files |
|---|---|---|---|---|---|
| `tasks.GarmentTypeItem` | DIRECTE | `garment_type` | CASCADE | True | **1** |
| `models_app.Model` | **VIA FILL** `GarmentTypeItem` (1) | `garment_type_item` | SET_NULL | True | **20** |

### `pom.GarmentGroup` · 0 files

| qui hi apunta | via | camp | on_delete | dbc | files |
|---|---|---|---|---|---|
| _(cap referència directa)_ | | | | | |

