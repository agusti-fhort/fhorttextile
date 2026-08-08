# REPORT FASE_2 · TOP-UP DE LECTORS — CLAU COMPLETA · 2026-08-02

**Veredicte: «FASE_3 POT ARRENCAR».** 8 commits · 3 PENDENTs, tots amb motiu i tots
reassignats a una fase concreta · cap canvi visible.

---

## ELS 8 COMMITS, AMB LA FORMA I EL PER QUÈ

| # | hash | fitxers | forma | per què aquesta forma |
|---|---|---|---|---|
| F2-1 | **`94f64f7e`** | `pom/s6_views.py` · `s8_views.py` · `s10_views.py` · `s11_views.py` | **A** (s8, s10) · **B** (s6 ×2, s11) | **A** on la fila consumidora sap dir de quina instància parla: `PieceFittingLine` porta els dos eixos i cada línia s'ha de jutjar amb la SEVA tolerància. **B** on no: la resposta de s6 és una llista plana indexada per `pom_id`, i el body de s11 és `{pom_id, value_cm}` i no diu res de cap eix |
| F2-2 | **`91bb74d8`** | `pom/services.py` (`_load_model_overrides`) | **B** | la clau `(pom_id, size_label)` es queda per POM per la FRONTERA C3: `_load_base_measurements` és intocable i indexa per POM sol. El segon filtre tapa el segon forat sense moure la frontera |
| F2-3 | **`6e28ef72`** | `pom/grading_views.py` | **B** + creixement de la clau d'ordre | `cells` es serialitza tal qual a la resposta i `poms_info` porta l'`id` del POM: **la clau ÉS el contracte**. Àncora a les DUES branques. I `clau_ordre_taula` creix amb la instància o torna a ser parcial |
| F2-4 | **`f4c6af24`** | `fitting/serializers.py` · `graded_spec_views.py` · `repas_views.py` | **A** (graella, `_notes_de_check`) · **B** (taula de fitxa, repàs) | la graella la consulta una `PieceFittingLine`; la taula de la fitxa i el repàs s'indexen per `pom_id` al payload |
| F2-5 | **`de49a5a2`** | `models_app/serializers_size_check.py` · `pom_placement_views.py` | **A** | totes dues files consumidores (`SizeCheckLine`, `POMPlacement`) porten els dos eixos |
| F2-6 | **`7cd1e854`** | `models_app/views.py` (`base_stages_view` + `_sembra_step_des_dels_specs`) · `test_lectors_capa_onada1.py` | **A** (estadis) · **B** (sembra) | **el node del pin**. Pin i fumeig verificats **immediatament després** d'aquest commit |
| F2-7 | **`e733b7ce`** | `patterns/views.py` · `tenants/federation_service.py` | **B** ×2 | **els 2 forats**. Àncora i no clau composta per motiu de DOMINI (v. sota) |
| F2-8 | **`d5f98b2a`** | `models_app/test_lectors_instancia_cins.py` (nou) | — | harness de files germanes **v2** |

**CAP PUSH.** Cap fitxer de `docs/` dins de cap commit. `git add` de paths explícits a tots vuit.

## EL CONTRACTE, APLICAT

**FORMA A — la clau creix a `(pom, capa, instancia)`** allà on la fila consumidora sap dir
els dos eixos: `_tolerance_map` (s10) i el seu bessó de s8 · `spec_map` i els tres mapes de
nomenclatura de la graella de fitting · `bm_map` del size check · `bm_by_pom` i tota la
cascada de cotes · `_notes_de_check` del repàs · la cadena d'estadis de `base_stages_view`.

**FORMA B — àncora `capa='exterior', instancia=''` amb el motiu semàntic escrit** allà on el
payload s'indexa per `pom_id` i **la clau ÉS el contracte**, que no es toca fins a C4-ins: les
dues portes de s6 · `check_tolerances_view` (s11) · les dues branques de la taula de mesures ·
els quatre mapes de la taula de la fitxa i els quatre del repàs · els logs del repàs · la
sembra STEP · `_load_model_overrides` (frontera C3) · els dos forats.

**MAPES GERMANS, TOTS ALHORA.** Cap bloc s'ha partit: els 3 de la graella, els 4 de la fitxa,
els 4 del repàs, les 2 portes de s6, les 2 branques de la taula de mesures, i els 4 nodes de
la cadena d'estadis (`changes_by_ev`, `snapshot`, `displayed`, `clau_bm`).

### Tres nodes que van créixer MÉS del que el dossier deia, i per què

1. **`pom/s6_views.py` · `graded_specs_with_units_view`** — el dossier el té al bloc D («ni
   tan sols va créixer a `(pom, capa)`»). Era el **germà desaparellat** de
   `base_measurements_with_units_view`, que sí que portava àncora de capa. Rep les dues
   àncores de cop: si un germà s'ancora i l'altre no, el fitxer serveix dues veritats.
2. **`models_app/pom_placement_views.py` · la CASCADA** — el dossier només censava
   `bm_by_pom` (`:74-82`). El cens executable va trobar que `exacte`/`germana`/`merged`
   (`:52-64`) segueixen indexats per **`pom_id` pelat**: col·lapsaven **abans** d'arribar a la
   clau composta, i quin precedent sobrevivia ho decidia l'ordre de la consulta.
3. **`pom/grading_views.py` · `clau_ordre_taula`** — node NOU trobat al re-cens de FASE_0.
   `F4a` la va fer TOTAL l'1/08 perquè els empats els desempatava el pla de Postgres; amb dues
   instàncies del mateix POM a la mateixa capa tornaria a empatar a tots els trams.

### Els 2 forats: per què àncora i no clau composta

`patterns/views.py` (`model-poms`) i `tenants/federation_service.py` (`_llegeix_patrimoni`)
són **àncora** i no clau, i el motiu és de **domini**:

- la unicitat de `PatternPOM` és `(pattern_piece, pom_master)` i aquella taula **no té cap dels
  dos eixos**. Creuar-la per clau completa vol dir decidir com un ancoratge de patró sap de
  quina capa i de quina instància parla — és el **sostre dur de `F2-patrons`** (§II.10: el
  format DXF `FTT "{codi}" {nom} = {valor} mm` no sobreviu un roundtrip amb instància);
- `_clau_natural_pom` és `(codi del diccionari, codi de client)` i **tampoc en porta cap**. Que
  creixi a 4-tupla i que els paquets es versionin és **FASE_3**, que ho té a l'abast especial.
  Aquí no s'endevina res: es deixa de dir el que no se sap dir.

## TESTS · HARNESS DE FILES GERMANES v2

`backend/fhort/models_app/test_lectors_instancia_cins.py` — **7 casos, OK**.

**Tres** files germanes del mateix POM, no dues: `exterior/''` (100 cm, ±0.5) ·
`folre/''` (98 cm, ±2.0) · `exterior/'left'` (40 cm, ±9.0). La tercera és el moll de l'os —
**un lector que hagués crescut a `(pom, capa)` i s'hagués quedat allà passa TOTS els tests
d'Onada 1 i col·lapsa igualment les dues instàncies de l'exterior.**

`comportes_alcades()` alça **les DUES famílies** de comporta per taula (Onada 1 només n'alçava
una) dins d'un savepoint que sempre es desfà; l'últim cas verifica al catàleg de Postgres que
**les 9 + 9 han tornat**.

| cas | què fixa |
|---|---|
| `..._mapa_de_tolerancies_te_una_entrada_per_germana` | 3 entrades, una per germana |
| `..._cada_linia_de_check_es_jutja_amb_la_tolerancia_de_la_SEVA_germana` | +1.0 cm és FORA de ±0.5, dins de ±2.0 i dins de ±9.0: si un lector col·lapsa, dos veredictes coincideixen |
| `..._un_estadi_dactivitat_no_salta_dentre_germanes` | el carry-forward no arrossega la presa d'una germana per la fila d'una altra |
| `..._els_lectors_ancorats_serveixen_nomes_la_instancia_unica` | **la cara B del contracte**: amb 3 germanes vives, s6 en serveix **1** |
| `..._la_llista_del_taller_no_repeteix_la_fila_per_germana` | forat #1: 1 fila, no 3 |
| `..._el_patrimoni_que_viatja_no_emet_dues_claus_iguals` | forat #2: 1 mesura, i cap clau natural repetida |
| `..._les_dues_comportes_tornen_a_estar_vives` | 9 + 9 al catàleg |

**Un assert és un TRIPWIRE declarat.** La fila d'exterior encara veu valors que no són seus, i
**no hi arriben per cap lector** —tots llegeixen amb la clau completa— sinó pel **signal F1**,
que escriu `MeasurementChangeLog` sense estampar cap dels dos eixos. És escriptor: FASE_3.
L'assert és `assertNotEqual(vals_ext, {100.0})` amb el missatge que diu com estrènyer-lo. **Peta
el dia que FASE_3 tapi el forat**, que és exactament el que ha de fer.

I `test_lectors_capa_onada1.py` parla la clau nova de `_tolerance_map` (tres trams en comptes
de dos): prova el mateix, i el fitxer no s'ha redissenyat.

## GREEN FLAGS

| flag | resultat |
|---|---|
| `manage.py check` | **net** abans de cada commit |
| pin `base_stages` 13/13 | **OK** — verificat immediatament després de F2-6, el seu commit |
| `test_capa_comporta_c1` | **OK** |
| `test_instancia_comporta_cins` | **12/12 OK** |
| `test_lectors_capa_onada1` | **OK** amb la clau nova |
| `test_lectors_instancia_cins` (harness v2) | **7/7 OK** |
| `pom.test_ordre_taula_mesures` | **3/3 OK** (la clau d'ordre ha crescut) |
| conjunt dels sis mòduls | **Ran 40 tests · OK** (+7 del harness v2) |
| **fumeig `base-stages` = T0** | **`a14ce3ec1d47c1555fd8f3e59cae9a5f`** ✅ |
| **dump de superfícies = T0** | **`fd2eaebed9ad576ca52246b400cce265`** ✅ — verificat **després de CADA commit**, 18 blocs, 0 excepcions |
| OpenAPI (des del codi) | **`9d0ec949e7d7e378ff488d1b681687ec`** = T0, byte-idèntic. 1 ocurrència de `instancia`, l'homònim català de sempre |
| comportes de les dues famílies | vives, i el harness ho verifica al catàleg de PG dins de rollback |

## PENDENTS (3, tots amb fase assignada)

| node | motiu | va a |
|---|---|---|
| **`models_app/services_size_check.py` `_materialize_lines`** (`ja_hi_son` per `pom_id` pelat) | és un **ESCRIPTOR**, i **FASE_3 el reclama explícitament** a l'abast especial: *«materialize_lines + N3: l'aparellament passa de pom_id pelat a clau completa — és el "pitjor cas del cens", tracta'l amb el seu propi commit i el seu propi test»*. Fer-ne aquí la meitat de lectura hauria partit el node | **FASE_3** |
| **`pom/services.py` `preview_graded_specs`** (`out[pom_id] = row`, `:366-401`) | **INTOCABLE per arrossegament**: la seva clau la dicta `_load_base_measurements`, que és zona de motor amb decisió humana. Tocar-la aquí voldria dir inventar els eixos dins del motor — la decisió que **C3** ha de prendre en fred | **C3, sessió diürna amb Agus** |
| **`pom/nomenclatura.py` `alies_per_pom`** (`:21-42`) | **fora del contracte**: llegeix `CustomerPOMAlias`, que **no és cap de les 9 taules** i no té ni `capa` ni `instancia`. Un àlies és nomenclatura de client per POM, no per instància. **Proposta: treure'l del cens de `top-up-lectors` del dossier** | — (reclassificació) |

## ABAST QUE S'HA DEIXAT FORA, AMB EL MOTIU

Els blocs **E** i **F** de §II.10 del dossier **no** entren al contracte d'aquesta fase, que és
literal: *«cap dict/set/lookup per `pom_id` (ni per `(pom_id, capa)`) sobre les 9 taules»*.

- **Bloc E · comptadors i gates que canvien de SIGNIFICAT** (11 nodes: `views.py:3230` ·
  `wizard_views.py:252-257` · `services_size_check.py:90` · `serializers_size_check.py:37` ·
  `fitting/serializers.py:32,112` · `pom/views.py:361-364` · `tasks/views_b.py:970` +
  `tasks/serializers_b.py:152-169` · `patterns/views.py:739` · `pom/s9_views.py:55-58` ·
  `grading_projection.py:184-200` · `fitting/staleness.py:112-117`). **No són diccionaris:
  compten files.** Amb la comporta tancada el resultat és idèntic; canviar-los vol dir decidir
  si «5 mesures» vol dir 5 POMs o 5 files — **decisió de producte (Patró C), no de refactor**.
- **Bloc F · lectors de llista sense capa** (6 nodes). **No col·lapsen: emeten dues files.** El
  problema és del CONSUMIDOR de frontend, que indexa per `pom_id` — i el frontend és
  **C4-ins** (203 nodes, 158 de frontend).

## DESCOBERTES · 27 NODES QUE EL DOSSIER NO TENIA

El cens executable de la fase va fer un grep de control sobre les 9 taules i va trobar **27
nodes** que el registre de 487 no recull. **Cap s'ha tocat** (llei del `CLAUDE.md`). Els
importants són **escriptors**, o sigui **radi de FASE_3**:

**Sobre `ItemBaseMeasurement` — cap node del dossier hi arriba:**
`models_app/views.py:1136` i `:1145-1146` (`materialize_poms_view`, dues branques que omplen el
MATEIX `ibms`) · `:3657` i `:3690` i `:3660-3661` (el DIFF de `promoure_a_item_view`, amb
`GarmentPOMMap` inclòs) · **`:3851-3852`** (`acte_canonic_base_set_view`: `.first()` per
`pom_id` sol — **escriu l'acte canònic sobre una instància arbitrària**).

**Sobre `GradedSpec`:** `views.py:1637-1642` (la taula de mesures principal) · `:1736-1738` ·
`:2494-2497` (N files de resposta amb el mateix `pom_id`) · **`:2789-2793`** (l'`id` sintètic és
`f'{pom.id}:{talla}'` → **col·lisió d'ids entre instàncies**) · `:2634-2637` ·
`patterns/adapters.py:484-488` (frontera amb el motor de patrons).

**Sobre `PieceFittingLine` — la de gravetat més alta:** **`fitting/views.py:665-668`** —
`.update()` massiu per `pom` sol: **la propagació escriu a TOTES les instàncies del POM**, i no
peta. Germà: `:617-619`. I `fitting/services.py:362-372` — `consolida_fitting` escriu a la
`BaseMeasurement` trobada per `(model, pom)` sol, **ignorant els eixos que la línia SÍ que
porta**.

**Lookups `(model, pom)` que escriuen:** `federation_service.py:689` (cara d'escriptura del
forat #2) · `views.py:1417` (còpia de model) · `:1182` · `:1921` (`gravar_pom_view`) ·
**`:3927-3929`** (`desactivar_pom_view`: **desactiva una instància arbitrària de la família**) ·
`extraction_views.py:2331-2335`, `:2367-2372`, `:2381` (la porta d'import raona per `pom_id`
sol a totes tres) · `pom/wizard_views.py:326-330` i `:365` (mateix patró que s6, **sense** el
filtre).

**Menors:** `export_losan_package.py:150-151` · `author_baby_pom_maps.py:146` ·
`fitting/staleness.py:110-116` (llegeix però no indexa: només noms duplicats a l'avís) ·
`views.py:3351-3360` (llista, no dict).

## INCIDENT DE PROCÉS (anotat perquè no es repeteixi)

El commit **F2-1** va canviar la clau de `_tolerance_map` i es va verificar amb `manage.py
check` i amb el dump byte-idèntic —tots dos verds— **però no amb la suite de tests**. El test
`test_c1_el_mapa_de_tolerancies_no_col·lapsa_les_dues_capes` d'Onada 1, que afirma la clau de
dos trams, va quedar vermell fins que es va detectar tres commits més tard (a F2-6) i es va
corregir al mateix commit. **Lliçó: el dump byte-idèntic NO substitueix el harness — per
construcció, amb les comportes tancades el dump no pot veure un canvi de clau.** Els harnesses
de dues i tres files germanes són l'única cosa que sí que el veu, i s'han d'executar a cada
commit que toqui una clau, no només al final.

També: **dues execucions de `manage.py test --keepdb` alhora sobre la mateixa BD de test es
trepitgen** (schema `test` a mitges + `tenants_client` duplicat). Cal netejar el tenant residual
(`DELETE FROM public.tenants_client WHERE schema_name='test'` + `DROP SCHEMA test CASCADE`) i
no paral·lelitzar-les.

---

## VEREDICTE

**FASE_3 POT ARRENCAR.**
