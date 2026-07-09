# LECTURA QUIRÚRGICA CURTA — Matching / ampliació / creació de GradingRuleSet

> **Naturalesa:** lectura quirúrgica READ-ONLY (Patró A acotat). Abast estricte: el mecanisme
> `derive_grading_rule_set` i companyia, per saber si la pàgina d'autoria d'item (pas 2: assignar
> ruleset) el pot reutilitzar.
> **Estat:** res tocat, `git status` net. `FET` = `fitxer:línia`; `💡 PROPOSTA (a validar)` = Fase C.
> Paths relatius a `/var/www/ftt-staging/backend/`. Fitxer únic: `fhort/pom/grading_utils.py`.

---

## 0 · Veredicte ràpid

1. **`derive_grading_rule_set` és reutilitzable des d'item TAL QUAL per a "find-EXACT-or-create".**
   És **pura de model**: rep dades planes (run, base, matriu de valors, eixos per codis) i retorna
   `GradingRuleSet` o `None`. No toca cap `Model`. FET: `grading_utils.py:226-233`.

2. **La branca "AMPLIAR existent" NO existeix.** El mecanisme només fa **dues** coses: *reutilitzar
   tal qual* (si troba un ruleset amb graduació **idèntica i mateix conjunt exacte de POMs**) o
   *crear-ne un de nou*. No hi ha cap branca que afegeixi POMs/regles que falten a un ruleset
   existent. L'"ampliar" de l'Agus és, doncs, **codi a construir**, no codi existent. FET: §2.

3. **El matching és per IGUALTAT ESTRICTA**, no per similitud: si l'item difereix en un sol POM o un
   sol increment respecte un ruleset existent, **no encaixa → crea un de nou**. FET: `:318-339`.

4. **Determinisme:** el `.first()` sense `order_by` **sí pot afectar la selecció** del ruleset a
   reutilitzar, **però només si existeixen rulesets duplicats** (mateixos eixos + graduació idèntica).
   En absència de duplicats, dues crides equivalents són deterministes. FET: §4.

5. **Dependència d'entrada crítica per a item:** `derive_*` **detecta** el grading a partir de la
   **matriu de valors per talla** (`valors {pid:{talla:valor}}`). Si la pàgina d'item al pas 2 només
   té el valor base (no el run de valors), `detect_grading` no detecta lògica i **retorna `None`**.
   Cal decidir d'on surt la matriu de valors al wizard d'item. FET: §2, `:285`, `:116`.

---

## 1 · Signatura exacta i forma d'entrada/sortida

FET — `grading_utils.py:226-228`:

```python
def derive_grading_rule_set(*, size_run_model, base_size, valors, confirmed_pom_ids,
                            size_system, garment_group, target_codi, construction_codi,
                            fit_type_codi, nom, nom_sufix_unic, avisos):
```

Tot **keyword-only**. Què rep (FET, docstring `:229-248`):

| Paràmetre | Tipus | Naturalesa |
|---|---|---|
| `size_run_model` | **str** (`'S·M·L·XL'`) | run; es parteja a llista internament `:258-261` |
| `base_size` | **str** (label) | talla base; es resol a `SizeDefinition` via `.first()` `:262-264` |
| `valors` | **dict** `{pom_id: {talla: valor}}` | la matriu de valors per talla (la "sortida" de l'import) |
| `confirmed_pom_ids` | **list[int]** | POMs a incloure (dedup per FK `:280`) |
| `size_system` | **instància** `SizeSystem` \| None | entra a la combinació tal com és |
| `garment_group` | **instància** `GarmentGroup` \| None | íd. |
| `target_codi` | **str (codi)** \| None | resolt a FK via `codi__iexact` aquí dins `:302` |
| `construction_codi` | **str (codi)** \| None | íd. `:303` |
| `fit_type_codi` | **str (codi)** \| None | íd. `:304` |
| `nom` | str | nom primari del ruleset nou |
| `nom_sufix_unic` | str | sufix determinista, només si `nom` col·lisiona exacte `:351-352` |
| `avisos` | list (mutable) | hi acumula la traça (efecte lateral) |

**No rep cap `Model`.** Docstring literal `:231-233`: «Pura de model: rep run/base/valors + la
classificació (per CODIS) + el nom, i RETORNA el GradingRuleSet (nou o reutilitzat) o None. NO toca
cap model, NO fa re-apuntat, NO desa cap sessió.»

**Sortida (FET):**
- `None` si manca run/base (`:266-269`), base no trobada (`:270-274`), o cap regla detectada (`:296-299`).
- `GradingRuleSet` **existent reutilitzat** (`:341-346`, `return candidat`).
- `GradingRuleSet` **nou creat** + les seves `GradingRule` (`:353-386`, `return new_rule_set`).

---

## 2 · Què fa pas a pas (i on és cada branca)

FET — `grading_utils.py:256-386`:

1. **Parseig + validació** (`:258-274`): run→llista, `base_size`→`SizeDefinition` (`.first()` `:262`).
   Si manca run/base o no troba la base → `None`.
2. **Detecció per POM** (`:280-294`): per cada pom_id (dedup `dict.fromkeys` `:280`), crida
   `detect_grading(valors.get(pid), run_ordenat, base_size)` (`:285`) que classifica LINEAR/FIXED/STEP
   des dels **valors per talla**. POMs sense lògica → omesos. Si cap → `None` (`:296-299`).
3. **Resolució d'eixos** (`:302-304`): target/construction/fit codi→FK via `codi__iexact` + `.first()`.
4. **MATCHING DE CANDIDATS** (`:308-339`):
   - Filtre (`:308-315`): `GradingRuleSet` amb `is_system_default=False` + **els 5 eixos**
     (`size_system`, `garment_group`, `target` FK, `construction`, `fit_type`). ⚠️ Aquí target va pel
     **FK legacy** (no la M2M) — deute anotat al codi (`:89-92`).
   - Per cada candidat (`:316-339`): **(1)** mateix **conjunt exacte** de `pom_id` («igualtat estricta,
     no subconjunt» `:318-320`); **(2-4)** per cada POM: mateixa `talla_base`, `logica`, `increment`
     (tol 0.001), `valors_step` (`:323-336`).
5. **BRANCA "REUTILITZAR"** (`:341-346`): primer candidat que passa tot → `return candidat` **sense
   crear ni modificar res**. El cridador re-apunta (a fora).
6. **BRANCA "CREAR NOU"** (`:348-386`): desambigua el nom (`:350-352`), crea `GradingRuleSet`
   (`:353-362`) + una `GradingRule` per POM amb forma canònica (`derive_break_fields` `:368-382`) →
   `return new_rule_set`.

### 2.1 · ¿Hi ha branca "AMPLIAR"? — NO (FET)

Només existeixen **dues** sortides amb ruleset: *reutilitzar idèntic* (`:341-346`) i *crear nou*
(`:348-386`). **No hi ha cap codi** que agafi un ruleset existent i hi **afegeixi** POMs/regles que
falten. Ho garanteix la condició `:319`: el conjunt de `pom_id` ha de ser **idèntic** (`!=` → `continue`);
un superconjunt/subconjunt **no** és candidat, va a crear-ne un de nou. → L'"ampliar existent" del
flux que descriu l'Agus **no és al motor**; és funcionalitat a dissenyar (§5).

---

## 3 · Acoblament a model

**FET: `derive_grading_rule_set` no accedeix a cap atribut de `Model`.** Treballa només amb els
paràmetres rebuts i amb `SizeDefinition`/`Target`/`ConstructionType`/`FitType`/`POMMaster`/
`GradingRuleSet`/`GradingRule` (imports locals `:250-254`). Confirma el comentari de la lectura prèvia.

- És cridable amb **dades d'item** (els eixos triats al wizard: `size_system` instància,
  `garment_group` instància, `target/construction/fit` com a **codis**, `run` com a string, `base`
  com a label, `valors` com a matriu, `confirmed_pom_ids`). Cap adaptació estructural.
- **Únic residu de model (cosmètic):** els textos d'`avisos` diuen "del model" (p.ex. `:298`, `:268`).
  Deute ja anotat al codi (DEUTE 1C-3, `:247-248`): «quan la Library sigui el segon cridador (sense
  model) cal fer-los neutres model/catàleg». No afecta la lògica, només el text dels avisos.
- **Atenció — `cerca_canonic_equivalent(model)` SÍ rep un `Model`** (`:81`, `:95-98`). Però aquesta és
  una funció **diferent** (comparació informativa amb el canònic ISO), **no** la del pas 2. El pas
  "assignar ruleset" només necessita `derive_grading_rule_set`, que és model-free.

---

## 4 · Idempotència / determinisme

FET — punts amb `.first()` / queryset sense `order_by` dins el camí de `derive_*`:

| Punt | On | Afecta SELECCIÓ del ruleset? |
|---|---|---|
| Filtre de candidats iterat sense `order_by` | `:308-316` → primer match `:337-339` | **SÍ, però només si hi ha duplicats** |
| `base_size`→`SizeDefinition` `.first()` | `:262-264` | si hi ha labels duplicats al sistema |
| `target/construction/fit` `codi__iexact .first()` | `:302-304` | si hi ha codis case-duplicats a les taules de referència |

**Anàlisi per a la pàgina d'item:**
- El matching exigeix **igualtat estricta** en eixos + conjunt de POMs + graduació per POM. Si la BD
  té **un sol** ruleset que encaixa (cas que l'anti-proliferació 1D pretén garantir), dues crides
  equivalents retornen **el mateix** ruleset → **determinista**.
- Si existeixen **rulesets duplicats** idèntics (1D ho evita en endavant però no purga els històrics),
  la iteració sense `order_by` (`:316`) pot retornar-ne **un diferent** entre crides → **no
  determinista**. Aquest és exactament el risc §4.2 de la lectura prèvia, i **sí aplica a la SELECCIÓ**
  (no només a la comparació canònica de `cerca_canonic_equivalent`).
- La branca **crear nou** és determinista donats els inputs (nom + sufix `:350-352`).

> 💡 PROPOSTA (a validar — Fase C): si la pàgina d'item ancora la FK Item→GradingRuleSet via aquest
> mecanisme, afegir `order_by` explícit al filtre de candidats (`:308`) i/o un upsert idempotent dóna
> garantia que dues autories equivalents apunten al mateix ruleset. Cost baix (un `.order_by('id')`),
> però és canvi de motor → decisió humana. Reportat, **no tocat**.

---

## 5 · Veredicte: ¿reutilitzar tal qual o cal variant "find-or-extend-or-create"?

**FET — el que es pot reutilitzar AVUI sense tocar res:** la pàgina d'item pot cridar
`derive_grading_rule_set` per al sub-pas **"buscar exacte → si cap, crear"**, passant-li els eixos del
wizard. És model-free i la forma d'entrada (codis + instàncies + matriu) encaixa amb el que el wizard
d'item té a mà. **Cost: ~0** (només construir el kwargs i re-apuntar la futura FK a fora, com fa el W5
a `extraction_views.py:1899-1901`).

**FET — el que NO cobreix:**
1. **No hi ha "ampliar existent".** El flux que vol l'Agus («buscar → proposar ampliar → si cap,
   crear») té **tres** estats; el motor només en té **dos** (exacte / nou). La branca "proposar
   ampliar un ruleset que quasi encaixa (afegint els POMs que falten)" és **codi nou**.
2. **Matching és exacte, no per similitud.** Per "proposar ampliar" cal un matcher de **subconjunt/
   superconjunt** (avui `:319` rebutja tot el que no sigui igualtat estricta) + lògica per afegir
   `GradingRule` a un ruleset existent + UI de proposta. Això NO existeix.
3. **Dependència d'entrada:** `derive_*` necessita la **matriu de valors per talla** per detectar el
   grading (`:285`, `detect_grading` `:116`). Si al pas 2 d'item només hi ha el valor base (sense run
   de valors), retorna `None`. Cal definir d'on surt aquesta matriu (¿valors de plantilla? ¿import?
   ¿el ruleset es tria d'un catàleg sense derivar-lo?).

> 💡 PROPOSTA (a validar — Fase C): dues opcions per al pas 2 de la pàgina d'item:
> **(A) Reutilitzar `derive_grading_rule_set` tal qual** com a "find-exact-or-create" — cost ~0, però
> sense "ampliar" i exigint la matriu de valors. Encaixa si l'item tria/deriva ruleset a partir d'una
> graduació completa.
> **(B) Construir una variant desacoblada `find_or_extend_or_create_rule_set`** que: (1) reusi el
> matcher exacte d'ara; (2) afegeixi un matcher per-eixos que trobi rulesets "quasi-iguals" (mateixos
> eixos, subconjunt de POMs) i proposi ampliar-los; (3) tingui una branca que afegeixi les
> `GradingRule` que falten. Cost real (matcher nou + branca d'ampliació + UI de proposta + tests).
> Recomanació tècnica: si "assignar ruleset" a l'item significa **triar un ruleset de catàleg** (no
> derivar-lo de valors), potser el pas 2 ni tan sols necessita `derive_*`, sinó un **selector** sobre
> `GradingRuleSet` filtrat pels eixos (un `.filter(...)` per la combinació) + l'opció de crear. Decidir
> primer QUÈ és "assignar ruleset" a l'item (triar vs derivar) abans de triar A/B.

---

## 6 · Checklist

- [x] Signatura exacta + entrada/sortida (§1): model-free, dades planes, retorna ruleset|None.
- [x] Pas a pas + ubicació de cada branca (§2): reutilitzar `:341-346` / crear `:348-386`.
- [x] Branca "ampliar": **no existeix** (§2.1, `:319`); és codi a construir.
- [x] Acoblament a model: **nul** a `derive_*` (§3); residu cosmètic als avisos; `cerca_canonic` SÍ rep model però és una altra funció.
- [x] Determinisme: `.first()` afecta la selecció **si hi ha duplicats** (§4).
- [x] Veredicte cost real A vs B (§5).
- [x] Res tocat, `git status` net.

---

*Lectura quirúrgica curta · Patró A acotat · 2026-06-22 · READ-ONLY · staging `dev`.*
