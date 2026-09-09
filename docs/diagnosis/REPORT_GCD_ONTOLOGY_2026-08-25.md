# GarmentCode ontology extraction — the vocabulary already solved, and the map into the FTT semantic catalogue

**Date:** 2026-08-25 · **Thread:** F1 · Pattern A
**Source:** `github.com/maria-korosteleva/GarmentCode` @ `d449629` (2025-06-29), MIT
**Precedents:** `INFORME_GIMNAS_N2_GARMENTCODEDATA_2026-08-25.md` ·
`INFORME_ESBORRANYS_SESSIO_MONTSE_2026-08-25.md`
**Language:** written in English on purpose — the brief asks for the vocabulary in English,
and every slug proposed here is a contract that must not be translated later.

> **Boundaries respected.** The clone and every script live in `/root/gcd_ontology/`. No
> `systemctl`, no migration, no database write, no write to any worktree, read-only on the
> repo. **This file is the only write outside the scratchpad.** No `git add`, no commit —
> the shared index is dirty from parallel sessions and was not touched.
> Disk used: 27 MB (clone) + 60 KB (outputs).

---

## 0 · The verdict in eight lines

1. **The 24 panel roles are not a sampling artefact — they are the complete vocabulary.**
   Derived independently from the code (22 named call sites) they come out at exactly 24,
   and the set matches the 1 200-pattern census **element by element**, with nothing on
   either side left over. The brief assumed the opposite; §1.3 is the proof.
2. **The real tree is one level up, and it is a different axis.** 15 panel classes produce
   those 24 roles, and the relation is many-to-many: `skirt_front` is emitted by **four**
   different generator classes. **51,2 % of all panels carry a role that is not a single
   shape** — which is the structural reason the precedent's contour fingerprint stalled.
3. **The edge-label vocabulary is closed in the code**: four `propagate_label` call sites,
   six resulting labels, and the corpus contains those six and no others (§2.1). The
   dataset is not withholding anything here.
4. **The anatomical edge vocabulary is far richer than the labels** — it lives in the
   *interface* names (34 keys) and in the 13 named edge-construction factories. That is
   where the `EdgeRole` candidate list comes from: **24 slugs with code evidence** (§2).
5. 🚨 **`sleeve.armhole_shape` only has any effect when `sleeve.sleeveless == True`.** The
   code forces `ArmholeCurve` whenever a sleeve is actually attached
   (`sleeves.py:229`). The axis is sampled on 100 % of patterns and is **inert on 75,8 %**
   of them. This is one level deeper than the trap the brief describes (§3.2).
6. **Only 3 of 122 design parameters are unconditionally applicable.** Conditional
   applicability is the rule, not the exception, and the gate is derivable from the code
   rather than guessed from the data (§3).
7. **Seam pairs are co-generated**: `ArmholeCurve` returns the bodice cut *and* the mating
   sleeve edge from one call (`sleeves.py:56-105`). A `SeamPairTemplate` is therefore a
   record of something the generator guarantees, not a statistical regularity (§4).
8. 🚨 **The headline for FTT is the opposite of the brief's premise.** For *piece roles*
   FTT's own seeded catalogue is already **3,75× richer** than GarmentCode's (30 slugs vs
   8 actually touched). What GarmentCode brings that FTT has **nothing** of is the
   **edge roles, the seam grammar and the landmark derivation** (§5.1).

---

## 1 · Q1 · The panel class hierarchy

### 1.1 The class tree

`assets/garment_programs/` holds the garment programs; `pygarment/garmentcode/` holds the
engine. Two base types matter: `pyg.Panel` (produces one pattern piece) and
`pyg.Component` (assembles panels and other components).

**15 panel classes** (`base_classes.py:3` is abstract; the other 14 are concrete):

| class | file:line | constructor signature (beyond `name`) |
|---|---|---|
| `BaseBodicePanel` *(abstract)* | `base_classes.py:3` | `body, design` |
| `BodiceFrontHalf` | `bodice.py:13` | `body, design` |
| `BodiceBackHalf` | `bodice.py:89` | `body, design` |
| `TorsoFrontHalfPanel` | `tee.py:10` | `body, design` |
| `TorsoBackHalfPanel` | `tee.py:68` | `body, design` |
| `SleevePanel` | `sleeves.py:106` | `body, design, open_shape, length_shift, _standing_margin` |
| `PantPanel` | `pants.py:9` | `body, design, length, waist, hips, hips_depth, dart_position, crotch_width, …` |
| `SkirtPanel` | `skirt_paneled.py:10` | `waist_length, length, ruffles, flare, bottom_cut, match_top_int_to` |
| `ThinSkirtPanel` | `skirt_paneled.py:62` | `top_width, bottom_width, length, b_curvature` |
| `FittedSkirtPanel` | `skirt_paneled.py:97` | `body, design, waist, hips, hips_depth, length, dart_position, slit…` |
| `CircleArcPanel` | `circle_skirt.py:7` | `rad, length, arc` (+3 named constructors, §1.2) |
| `AsymHalfCirclePanel` | `circle_skirt.py:79` | `w_rad, f_length, s_length` |
| `StraightBandPanel` | `bands.py:6` | `width, depth, match_int_proportion` |
| `SimpleLapelPanel` | `collars.py:179` | `length, max_depth` |
| `HoodPanel` | `collars.py:268` | `f_depth, b_depth, f_length, b_length, width, in_length, depth` |
| `Insert` | `godet.py:10` | `id, width, depth` |

**26 component classes** assemble them. The composition root is `MetaGarment`
(`meta_garment.py:20`), and it has exactly **three slots**, each filled by class name
looked up in `globals()`:

```
meta.upper  ∈ {FittedShirt, Shirt, null}                       meta_garment.py:37-42
meta.wb     ∈ {StraightWB, FittedWB, null}                     meta_garment.py:55-77
meta.bottom ∈ {SkirtCircle, AsymmSkirtCircle, GodetSkirt,
               Pants, Skirt2, SkirtManyPanels, PencilSkirt,
               SkirtLevels, null}                              meta_garment.py:44-97
```

This three-slot shape is the **garment type generator**: `upper`+`bottom(Pants)` is a
jumpsuit, `upper`+`bottom(skirt)` a dress, `bottom` alone a skirt or trousers. There is no
separate "garment type" entity anywhere in the code — the type is a *function of the slots*.

### 1.2 🚨 The role is assigned at the call site, not by the class

Every panel class takes `name` as its **first constructor argument**. No panel class names
itself. The role vocabulary therefore lives in the **22 instantiation sites**, and the
same class serves different roles depending on who calls it:

| emitted name template | class | file:line | parent component |
|---|---|---|---|
| `wb_front` / `wb_back` | `StraightBandPanel` | `bands.py:96` / `:103` | `StraightWB.define_panels` |
| `wb_front` / `wb_back` | `CircleArcPanel.from_all_length` | `bands.py:134` / `:143` | `FittedWB.define_panels` |
| `{tag}_cuff_f` / `_cuff_b` | `StraightBandPanel` | `bands.py:165` / `:168` | `CuffBand` |
| `{tag}_cuff_skirt_f` / `_b` | `SkirtPanel` | `bands.py:202` / `:207` | `CuffSkirt` |
| `{tag}_collar_front` / `_back` | `StraightBandPanel` | `collars.py:154` / `:157` | `Turtle` |
| `{tag}_collar_front` | `SimpleLapelPanel` | `collars.py:232` | `SimpleLapel` |
| `{tag}_collar_back` | `StraightBandPanel` *or* `CircleArcPanel` | `collars.py:237` / `:243` | `SimpleLapel` (standing or not) |
| `{tag}_hood` | `HoodPanel` | `collars.py:350` | `Hood2Panels` |
| `{name}_ftorso` / `_btorso` | `BodiceFrontHalf` / `BodiceBackHalf` | `bodice.py:182` / `:184` | `BodiceHalf` (fitted) |
| `{name}_ftorso` / `_btorso` | `TorsoFrontHalfPanel` / `TorsoBackHalfPanel` | `bodice.py:187` / `:189` | `BodiceHalf` (not fitted) |
| `{tag}_sleeve_f` / `_b` | `SleevePanel` | `sleeves.py:270` / `:274` | `Sleeve` |
| `skirt_front` / `skirt_back` | `FittedSkirtPanel` | `skirt_paneled.py:334` / `:351` | `PencilSkirt` |
| `skirt_front{_tag}` / `skirt_back{_tag}` | `SkirtPanel` | `skirt_paneled.py:412` / `:421` | `Skirt2` |
| `skirt_front{_tag}` / `skirt_back{_tag}` | `CircleArcPanel.from_w_length_suns` | `circle_skirt.py:147` / `:153` | `SkirtCircle` |
| `skirt_front{_tag}` / `skirt_back{_tag}` | `AsymHalfCirclePanel` | `circle_skirt.py:166` / `:172` | `AsymmSkirtCircle` |
| `skirt_panel_{i}` | `ThinSkirtPanel` + `distribute_Y` | `skirt_paneled.py:476` / `:494` | `SkirtManyPanels` |
| `pant_f_{tag}` / `pant_b_{tag}` | `PantPanel` | `pants.py:208` / `:218` | `PantsHalf` |
| `ins_{base}_{i}` | `Insert` + `distribute_horisontally` | `godet.py:77` / `:81` | `GodetSkirt` |

Laterality prefixes are not part of the name template: `BodiceHalf` is instantiated
literally as `'right'` and `'left'` (`bodice.py:437-440`), and the left half is
`.mirror()`ed. `Sleeve` and `PantsHalf` carry `tag` the same way (`sl_left`, `pant_r`).

### 1.3 🚨 Closure: the 24 roles are the complete vocabulary

Applying the precedent's role normalisation (strip laterality and trailing ordinal) to the
name templates above yields a set of roles derived **purely from the code**. Compared with
the 24 roles observed in the 1 200-pattern census
(`scripts/roles_closure.py`, reading `/root/n2_gym/out/empremtes.csv`):

```
roles derived from CODE     : 24
roles observed in 1200 specs: 24
CODE - OBSERVED (never sampled): NONE
OBSERVED - CODE (unexplained) : NONE
=> CLOSURE HOLDS
```

> **Correction to the brief.** The brief states *«els 24 eren artefacte de mostra: aquí
> volem l'arbre sencer»*. They are not an artefact: **24 is the whole tree at the role
> level**, and 1 200 patterns were enough to see all of it. The tree the brief is reaching
> for exists, but on a different axis — the 15 generator classes of §1.1, which the data
> can never show because the class name is not serialised.

### 1.4 🚨 Half the corpus has a role that is not a single shape

Eight of the 24 roles are emitted by more than one generator class:

| role | generator classes | n |
|---|---|---|
| `skirt_front` | `FittedSkirtPanel`, `SkirtPanel`, `CircleArcPanel`, `AsymHalfCirclePanel` | 4 |
| `skirt_back` | same four | 4 |
| `collar_back` | `StraightBandPanel` (Turtle), `StraightBandPanel` (standing lapel), `CircleArcPanel` (curved lapel) | 3 |
| `collar_front` | `StraightBandPanel`, `SimpleLapelPanel` | 2 |
| `ftorso` / `btorso` | `BodiceFrontHalf`/`BodiceBackHalf` (fitted), `TorsoFrontHalfPanel`/`TorsoBackHalfPanel` (tee) | 2 |
| `wb_front` / `wb_back` | `StraightBandPanel` (straight), `CircleArcPanel` (fitted/yoke) | 2 |

**6 700 of 13 078 panels (51,2 %) belong to one of these roles.**

> This is the structural explanation of the precedent's ceiling. Its §5 lists
> *«formes genuïnament homògrafes»* as an empirical nuisance; the code says something
> stronger and cheaper to act on: **for half the corpus the role is a union of
> shape-generators by construction**, so no function of the contour can be expected to
> converge on it. The precedent measured 52,16 % on roles; the multi-generator mass is
> 51,2 %. **The two numbers are close, and I am deliberately not claiming one explains the
> other** — they are different quantities over different splits. What the code does
> establish is the mechanism; quantifying its share would need a re-run of `classify.py`
> conditioned on generator class, which is not done here.

---

## 2 · Q2 · The edge construction vocabulary

Three distinct layers carry edge semantics in GarmentCode. Only the weakest of the three
reaches the serialised `specification.json`.

### 2.1 Layer 1 — the serialised edge labels (closed, and complete in the corpus)

Edge labels are written by exactly **four** `propagate_label` call sites in the whole
repository (`grep -rn "propagate_label" assets/ pygarment/`):

| call site | label emitted | anatomical meaning |
|---|---|---|
| `meta_garment.py:75` and `:95` | `lower_interface` | the waist join, on the top interface of the belt or of the lower garment |
| `bodice.py:306-307` | `{name}_armhole` → `left_armhole`, `right_armhole` | the armhole, after the sleeve shape is projected onto the bodice corner |
| `bodice.py:351-352` | `{name}_collar` → `left_collar`, `right_collar` | the neckline, after the collar shape is projected |
| `bodice.py:382-383` | `strapless_top` | the top edge of a strapless bodice |

`{name}` is the `BodiceHalf` name, which is literally `'left'` / `'right'`
(`bodice.py:437-440`). So the code predicts exactly six labels. Measured over the 1 200
specs:

```
edge labels: right_collar 1599 · left_collar 1609 · right_armhole 1339 ·
             left_armhole 1320 · lower_interface 6794 · strapless_top 380
panel labels: body 5232 · leg 4294 · arm 3552        (4 set_panel_label call sites)
```

**Six predicted, six observed, nothing else.** The precedent treated the label set as an
observation; it is a closed vocabulary, and no larger sample will extend it.

> ⚠️ `lower_interface` is ambiguous by construction, and the code says why: it is applied
> to *whatever component sits below* — the waistband's top edge or, when there is no belt,
> the lower garment's top edge (`meta_garment.py:75` vs `:95`). The precedent found the
> same ambiguity empirically (waist vs hem). **It is one label doing two jobs, and the
> disambiguator is the piece role, not the label.**

### 2.2 Layer 2 — the interface names (the real anatomical vocabulary)

`pyg.Interface` (`interface.py:10`) is the unit that gets stitched. Interface names are
**not serialised**, but they are the only place where the code says what an edge *is*.
34 distinct keys appear; the anatomically loaded ones, per panel class:

| panel class | interface key | anatomical role | file:line |
|---|---|---|---|
| `BodiceFrontHalf` / `TorsoFrontHalfPanel` | `outside` | side seam | `bodice.py:73`, `tee.py:51` |
| " | `inside` | centre front | `bodice.py:74`, `tee.py:52` |
| " | `shoulder` | shoulder seam | `bodice.py:75`, `tee.py:53` |
| " | `bottom` | waistline (or hem if nothing below) | `bodice.py:76`, `tee.py:54` |
| " | `shoulder_corner` | the corner the **armhole** is cut into | `bodice.py:79`, `tee.py:57` |
| " | `collar_corner` | the corner the **neckline** is cut into | `bodice.py:81`, `tee.py:58` |
| `BodiceBackHalf` / `TorsoBackHalfPanel` | `inside` | centre back | `bodice.py:126`, `tee.py:103` |
| `PantPanel` | `outside` | side seam | `pants.py:115` |
| " | `inside` | inseam | `pants.py:120` |
| " | `crotch` | crotch / rise seam | `pants.py:119` |
| " | `bottom` | leg hem | `pants.py:121` |
| `SleevePanel` | `in` | sleeve cap (mates the armhole) | `sleeves.py:180` |
| " | `out` | cuff line / sleeve hem | `sleeves.py:181` |
| " | `top` / `bottom` | the two underarm seams | `sleeves.py:182-183` |
| `SkirtPanel`, `FittedSkirtPanel`, `CircleArcPanel` | `top` | waistline | `skirt_paneled.py:45`, `circle_skirt.py:43` |
| " | `bottom` | hem | `skirt_paneled.py:49`, `circle_skirt.py:46` |
| " | `left` / `right` | skirt side seams / gore joins | `skirt_paneled.py:44,48` |
| `StraightBandPanel` | `top` / `bottom` | the two band attach edges | `bands.py:19,24` |
| " | `left` / `right` | band side seams | `bands.py:18,23` |
| `SimpleLapelPanel` | `to_collar`, `to_bodice` | lapel joins | `collars.py:197-198` |
| `HoodPanel` | `to_other_side` | hood centre-back seam | `collars.py:323` |
| " | `to_bodice` | hood neckline attach | `collars.py:324` |
| `NoPanelsCollar` etc. | `front_proj`, `back_proj` | the shape **projected** onto the bodice to cut the neckline | `collars.py:122-123` |
| `Sleeve` | `in_front_shape`, `in_back_shape` | the shape projected to cut the armhole | `sleeves.py:251-252` |

> 🚨 **The same key means different anatomy on different classes.** `bottom` is a waistline
> on a bodice, a hem on a skirt, a cuff line on a sleeve and a band attach edge on a
> waistband. `inside` is centre-front on a torso panel and the inseam on a trouser panel.
> **An `EdgeRole` cannot be keyed on the interface name alone — it is keyed on
> (piece role, interface).** This is the edge-side twin of the `armhole_shape` trap.

### 2.3 Layer 3 — the named edge-construction factories

These are the functions that actually build anatomical edges. They are selected **by
parameter value** through `globals()` / `getattr` lookup, so their names are simultaneously
the construction vocabulary and the values of a design axis.

**Neckline constructions** — 7, all with signature `(depth, width, **kwargs)`, all returning
an `EdgeSequence` for *half* a neckline:

| function | file:line | geometry produced |
|---|---|---|
| `VNeckHalf` | `collars.py:12` | one straight `Edge` |
| `SquareNeckHalf` | `collars.py:18` | two straight edges |
| `TrapezoidNeckHalf` | `collars.py:24` | two straight edges; **degrades to `VNeckHalf`** at angle 0/180 or on invalid overlap |
| `CurvyNeckHalf` | `collars.py:47` | one cubic `CurveEdge` (2 control points) |
| `CircleArcNeckHalf` | `collars.py:57` | one `CircleEdge` from points+angle |
| `CircleNeckHalf` | `collars.py:68` | `CircleEdge` from 3 points, subdivided in half |
| `Bezier2NeckHalf` | `collars.py:79` | one quadratic `CurveEdge` |

**Armhole constructions** — 3, signature `(incl, width, angle, invert=True, …)`:

| function | file:line | geometry | returns |
|---|---|---|---|
| `ArmholeSquare` | `sleeves.py:11` | two straight edges | `(bodice_cut, sleeve_edges)` |
| `ArmholeAngle` | `sleeves.py:36` | piecewise-smooth, 2 edges | `(bodice_cut, sleeve_edges)` |
| `ArmholeCurve` | `sleeves.py:56` | cubic Bezier, tangent-matched to the sleeve | `(bodice_cut, sleeve_edges)` |

> 🔑 **The armhole factories return a PAIR.** One call produces the cut-out on the bodice
> *and* the mating edge on the sleeve, and `ArmholeCurve` even runs an optimiser
> (`ops.curve_match_tangents`, `sleeves.py:88-96`) so the two match in length and tangent.
> This is the single most important fact for `SeamPairTemplate` (§4.1).

**Decorative / slit shapes** — `Sun` (`shapes.py:15`), `SIGGRAPH_logo` (`shapes.py:45`),
`SVGFile` (`shapes.py:56`), selected by `pencil-skirt.style_side_cut`.

**Generic edge machinery** — `EdgeSeqFactory` (`edge_factory.py:220`) supplies
`from_verts`, `from_fractions`, `side_with_cut` (`:292`, an edge with internal vertices so
only part of it is stitched — this is how slits are made) and `dart_shape` (`:313`, the
triangular dart). `CircleEdgeFactory` (`:43`) and `CurveEdgeFactory` (`:155`) build the
three curvature types the precedent already characterised (`quadratic`, `circle`, `cubic`).

**Darts** are inserted by `Panel.add_dart` (`panel.py:238`) and appear as *stitches within
one panel* — the precedent's `PINCA` category. Call sites: `bodice.py:51,62,147,152`
(bust and waist darts), `pants.py:128,168`, `skirt_paneled.py:246,295`.

### 2.4 The `EdgeRole` candidate list

Twenty-four slugs, each with the construction that evidences it. `mates` names the edge
role it is normally sewn to (§4).

| slug | zone | kind | mates | evidence |
|---|---|---|---|---|
| `neckline` | neck | opening | `collar_attach` | `bodice.py:351`; `collars.py:12-88` |
| `collar_attach` | neck | seam | `neckline` | `collars.py:169`, `:259`; `bodice.py:333` |
| `collar_outer_edge` | neck | finished | — | `bands.py:24` on collar panels |
| `collar_side_seam` | neck | seam | itself | `collars.py:161-163` |
| `hood_attach` | neck | seam | `neckline` | `collars.py:324` |
| `hood_centre_seam` | neck | seam | itself | `collars.py:323` |
| `strapless_top` | torso | finished | — | `bodice.py:382-383` |
| `shoulder_seam` | shoulder | seam | itself | `bodice.py:75`; `bodice.py:211-213` |
| `armhole` | arm | opening | `sleeve_cap` | `bodice.py:306`; `sleeves.py:11-105` |
| `sleeve_cap` | arm | seam | `armhole` | `sleeves.py:180`, `:289` |
| `sleeve_underarm_seam` | arm | seam | itself | `sleeves.py:281-284` |
| `cuff_line` | arm/leg | seam | `band_attach_upper` | `sleeves.py:181`, `:328-331` |
| `centre_front` | torso | seam/fold | itself | `bodice.py:74`; `bodice.py:443-444` |
| `centre_back` | torso | seam/fold | itself | `bodice.py:126`; `bodice.py:445-446` |
| `side_seam` | torso | seam | itself | `bodice.py:73`, `:217`; `pants.py:115`, `:232` |
| `waistline` | waist | seam | `band_attach_upper` | `meta_garment.py:75`; `skirt_paneled.py:45` |
| `band_attach_upper` | waist | seam | `waistline` | `bands.py:19` |
| `band_attach_lower` | waist | seam | `waistline` | `bands.py:24` |
| `band_side_seam` | waist | seam | itself | `bands.py:74-75` |
| `inseam` | leg | seam | itself | `pants.py:120`, `:233` |
| `crotch_seam` | leg | seam | itself | `pants.py:119`; `pants.py:289-290` |
| `hem` | any | finished | — | `skirt_paneled.py:49`; `pants.py:121` |
| `gore_seam` | any | seam | itself | `skirt_paneled.py:497-501` |
| `dart_leg` | any | internal | itself | `panel.py:238`; `edge_factory.py:313` |

Two further slugs are **structural rather than anatomical** and are proposed separately,
because they describe *how a piece was assembled*, not where it sits on the body:
`godet_insert_seam` (`godet.py:113-114`) and `level_join_seam` (`skirt_levels.py:62-64`).
A third, `slit_edge` (`skirt_paneled.py:192,218`; `circle_skirt.py:216`;
`edge_factory.py:292`), marks the part of an edge deliberately left unstitched.

---

## 3 · Q3 · The design_params axes and their applicability gates

`assets/design_params/default.yaml` is the sampling space. Parsed to leaves
(`scripts/params_tree.py`): **122 parameters**, in 12 top-level groups.

```
leaves by group : left 32 · collar 18 · sleeve 17 · flare-skirt 10 · pants 10 ·
                  pencil-skirt 9 · levels-skirt 7 · skirt 5 · godet-skirt 5 ·
                  shirt 4 · meta 3 · waistband 2
leaves by type  : float 76 · int 14 · bool 13 · select 11 · select_null 8
tree depth      : 2 levels 67 · 3 levels 49 · 4 levels 6
```

### 3.1 The gate is derivable from the code, not guessable from the data

The precedent derived applicability empirically and warned that
*«`design_params` porta sempre l'arbre SENCER de paràmetres, faci servir la peça aquella
branca o no»*. That warning is right; the fix is to read **who consumes each parameter**.

Method (`scripts/readers.py` + `scripts/gates2.py`): grep every `design['…']['…']` chain,
attribute it to the enclosing class, then resolve relative reads to absolute paths using
the verified subtree rebinds, and finally map each consuming class to the `meta` slot that
can reach it. Result: **all 122 leaves resolve, none left over.**

| gate (which `meta` slot must be non-null) | leaves |
|---|---:|
| `always` (the `meta` slot selectors themselves) | 3 |
| `meta.upper` | 71 |
| `meta.bottom` | 46 |
| `meta.wb` | 2 |

> **Only 3 of 122 parameters are unconditionally applicable.** Conditional applicability is
> the normal case. A catalogue that stores a variant axis without its gate stores a value
> that is meaningless for ~97 % of its rows.

The verified subtree rebinds (each is a `design = design['x']` inside a constructor, so
every read below it is relative):

```
tee.py:20,78    → shirt          sleeves.py:211      → sleeve
bands.py:160    → cuff           bands.py:195        → cuff
pants.py:182    → pants          circle_skirt.py:133 → flare-skirt
skirt_paneled.py:311 → pencil-skirt   skirt_paneled.py:399 → skirt
skirt_paneled.py:462 → flare-skirt    godet.py:31 / skirt_levels.py:12 → (aliased, reads stay absolute)
```

> 🔑 **The `cuff` subtree is mounted twice.** `CuffBand` / `CuffSkirt` / `CuffBandSkirt` are
> instantiated both from `Sleeve` (`sleeves.py:311`, tag `sl_*`) and from `PantsHalf`
> (`pants.py:252`, tag `pant_*`), so the *same component's* parameters live at
> `sleeve.cuff.*` **and** at `pants.cuff.*`. An axis is therefore **not addressable by path
> alone** — the mount point is part of its identity. This is what produces the four
> distinct cuff roles (`sl_cuff_*`, `pant_cuff_*`) from two classes.

### 3.2 🚨 The `armhole_shape` trap is deeper than the brief describes

The brief flags `armhole_shape` being sampled on skirts. It is worse than that:

```python
# NOTE: Non-trad armholes only for sleeveless styles due to
# unclear inversion and stitching errors (see below)
armhole = globals()[design['armhole_shape']['v']] if design['sleeveless']['v'] else ArmholeCurve
                                                                    # sleeves.py:227-229
```

**When a sleeve is actually attached, the parameter is discarded and `ArmholeCurve` is
forced.** The axis only has an effect on *sleeveless* garments. Measured over the 1 200
`_design_params.yaml` of the corpus:

| | patterns | share |
|---|---:|---:|
| `armhole_shape` **sampled** | 1 200 | 100 % |
| has an upper garment (the naive gate) | 821 | 68,4 % |
| has an upper garment **and** is sleeveless (**the true gate**) | **290** | **24,2 %** |
| axis **inert** | 910 | **75,8 %** |

By garment type (type derived from `meta`, so counts differ by a few units from the
dataset's own labels — the 290/1 200 total is exact and independent of that derivation):

| garment type | patterns | precedent-style gate | true gate | overcount |
|---|---:|---:|---:|---:|
| dress | 457 | 457 | 167 | 2,7× |
| upper_garment | 296 | 296 | 100 | 3,0× |
| jumpsuit | 68 | 68 | 23 | 3,0× |
| skirt | 282 | 282 | **0** | axis dead |
| pants | 97 | 97 | **0** | axis dead |
| **total** | **1 200** | **1 200** | **290** | **4,1×** |

The precedent's `out/plantilla_variants.csv` reports
`dress, sleeve.armhole_shape, ArmholeCurve, 310, 446, 69.51 %` — i.e. all 446 dresses
counted as applicable. **The denominator should be 167.** The distribution of values is
still informative; the percentages are inflated ~2,7×.

### 3.3 The gate has three orders, not one

| order | gate | example |
|---|---|---|
| 1 · slot | which `meta` slot is non-null | `pants.*` needs `meta.bottom == 'Pants'` |
| 2 · switch | a bool/select inside the branch | `sleeve.cuff.*` needs `sleeve.cuff.type != null` (`sleeves.py:300`) |
| 3 · inversion | the parameter is read but discarded | `sleeve.armhole_shape` needs `sleeve.sleeveless == True` (`sleeves.py:229`) |

Second-order guards found in the code:

```
sleeves.py:255   if design['sleeveless']['v']:   return    → no sleeve panels at all
sleeves.py:300   if design['cuff']['type']['v']:           → cuff panels exist
pants.py:238     if design['cuff']['type']['v']:           → leg cuff panels exist
bodice.py:205    if design['shirt']['strapless']['v'] and fitted:   → strapless only when fitted
bodice.py:237    if design['collar']['width']['v'] >= 0:
bodice.py:283    if not design['sleeve']['sleeveless']['v']:        → sleeve attached
circle_skirt.py:179  if design['cut']['add']['v'] and slit:
skirt_paneled.py:315 if design['style_side_cut']['v'] is not None:
```

### 3.4 🚨 Axes are not independent: there is a dependency resolver

`Shirt.eval_dep_params` (`bodice.py:457-478`) rewrites the design dict before anything is
built. When `left.enable_asym` is true it **forces `collar.component.style = None`** with
the comment *«Force no collars since they are not compatible with each other»*, and copies
`shirt.length`, `collar.fc_depth`, `collar.bc_depth` from the right side onto the left.

Consequences for the catalogue:

- **31 of the 122 leaves are second-order gated** by `left.enable_asym == True` (the whole
  `left.*` subtree except the switch itself), and they *mirror* their symmetric sibling.
- **Asymmetry and panelled collars are mutually exclusive** — a constraint between two
  axes, not a property of either. A catalogue that models only per-axis enablement cannot
  express it.

### 3.5 The categorical axes (candidate variant axes)

`select`/`select_null`/`bool`: 32 leaves. Those whose range is a **set of class or function
names** are simultaneously an axis and a generator selector:

| axis | range | selector mechanism |
|---|---|---|
| `meta.upper` | `FittedShirt`, `Shirt`, null | `globals()` — `meta_garment.py:38` |
| `meta.wb` | `StraightWB`, `FittedWB`, null | `globals()` — `meta_garment.py:57` |
| `meta.bottom` | 8 skirt/trouser classes, null | `globals()` — `meta_garment.py:46` |
| `collar.f_collar` / `b_collar` | 7 `*NeckHalf` functions | `globals()` — `collars.py:98,110` |
| `collar.component.style` | `Turtle`, `SimpleLapel`, `Hood2Panels`, null | `getattr(collars, …)` — `bodice.py:311` |
| `sleeve.armhole_shape` | `ArmholeSquare`, `ArmholeAngle`, `ArmholeCurve` | `globals()` — `sleeves.py:229` |
| `sleeve.cuff.type` / `pants.cuff.type` | `CuffBand`, `CuffSkirt`, `CuffBandSkirt`, null | `getattr(bands, …)` — `sleeves.py:310`, `pants.py:251` |
| `godet-skirt.base` | `Skirt2`, `PencilSkirt` | `globals()` |
| `levels-skirt.base` / `.level` | 4 / 3 skirt classes | `globals()` — `skirt_levels.py:22,36` |
| `pencil-skirt.style_side_cut` | `Sun`, `SIGGRAPH_logo`, null | `shapes.py` |

The purely stylistic ones: `shirt.strapless`, `collar.f_flip_curve`, `collar.b_flip_curve`,
`collar.component.lapel_standing`, `sleeve.sleeveless`, `sleeve.standing_shoulder`,
`left.enable_asym`, `flare-skirt.cut.add`, `flare-skirt.skirt-many-panels.panel_curve`
(8 discrete curvature values), `godet-skirt.num_inserts` (4/6/8/10/12).

---

## 4 · Q4 · Stitch graph semantics

### 4.1 How a seam is born

`StitchingRule` (`connector.py:7`) takes **two `Interface` objects** and emits stitches.
A component declares its seams either at construction (`pyg.Stitches(...)`) or by
`stitching_rules.append((int_a, int_b))`. Serialisation (`connector.py:145-176`) writes
each stitch as a pair of `{panel, edge}` records:

```json
[{"panel": "skirt_front", "edge": 0}, {"panel": "skirt_back", "edge": 3}]
```

so **the seam graph survives into the JSON, but the interface names do not**. The `edge`
index is all that is left of `outside` / `crotch` / `shoulder`.

An optional third element, `'right_wrong'` (`connector.py:170-173`), marks a stitch whose
faces are joined the other way round. In the corpus: **362 of 36 785 stitches (0,98 %)**,
all traceable to `collars.py:249` — the standing lapel back panel. It is the only notion
of fabric face in the whole system.

> 🔑 **Mating edges are co-generated.** The three `Armhole*` factories return
> `(bodice_cut, sleeve_edges)` from one call (`sleeves.py:11,36,56`), and `ArmholeCurve`
> runs `ops.curve_match_tangents` to force the two to agree in length and tangent
> (`sleeves.py:88-96`). Necklines work the same way: the collar component exposes
> `front_proj` / `back_proj` (`collars.py:122-123`) which `ops.cut_corner` subtracts from
> the bodice corner (`bodice.py:320-326`). **A `SeamPairTemplate` for these pairs records a
> guarantee of the generator, not a statistical tendency.**

### 4.2 The seam rules in the code

Twenty rule sites. `A ↔ B` reads *interface A of panel/component A is stitched to B*:

| # | rule | file:line | anatomical seam |
|---|---|---|---|
| 1 | `ftorso.shoulder ↔ btorso.shoulder` | `bodice.py:211-213` | shoulder seam |
| 2 | `ftorso.outside ↔ btorso.outside` | `bodice.py:217-218` | torso side seam |
| 3 | `sleeve.in ↔ bodice armhole` | `bodice.py:289-291` | armhole / sleeve cap |
| 4 | `collar_comp.bottom ↔ bodice neckline` | `bodice.py:333-335` | collar attach |
| 5 | `right.front_in ↔ left.front_in` | `bodice.py:443-444` | centre front |
| 6 | `right.back_in ↔ left.back_in` | `bodice.py:445-446` | centre back |
| 7 | `f_sleeve.top ↔ b_sleeve.top` | `sleeves.py:281-282` | sleeve upper seam |
| 8 | `f_sleeve.bottom ↔ b_sleeve.bottom` | `sleeves.py:283-284` | sleeve underarm seam |
| 9 | `cuff.top ↔ sleeve.out` | `sleeves.py:328-331` | cuff attach |
| 10 | `pant_f.outside ↔ pant_b.outside` | `pants.py:232` | trouser side seam |
| 11 | `pant_f.inside ↔ pant_b.inside` | `pants.py:233` | inseam |
| 12 | `right.crotch_f ↔ left.crotch_f` | `pants.py:289` | front rise |
| 13 | `right.crotch_b ↔ left.crotch_b` | `pants.py:290` | back rise |
| 14 | `pant_bottom ↔ cuff.top` | `pants.py:263-265` | leg cuff attach |
| 15 | `front.right ↔ back.right`, `front.left ↔ back.left` | `skirt_paneled.py:371-373`, `:431-433`; `circle_skirt.py:185-187` | skirt side seams |
| 16 | `wb.front.right ↔ wb.back.right` (and left) | `bands.py:73-75`, `:172-174`, `:213-215` | band side seams |
| 17 | `cuff.bottom ↔ skirt.top` | `bands.py:250-251` | `CuffBandSkirt` internal join |
| 18 | `subs[i-1].left ↔ subs[i].right` (ring) | `skirt_paneled.py:497-501` | gore-to-gore |
| 19 | `subs[-2].bottom ↔ subs[-1].top` | `skirt_levels.py:62-64` | tier join |
| 20 | `subs[-2].bottom ↔ subs[-1].top` | `meta_garment.py:70-72`, `:89-91` | **upper↔belt↔lower waist join** |
| 21 | `insert.interfaces[0] ↔ cut edge` | `godet.py:113-114` | godet insert |
| 22 | *darts* — two edges of one panel | `panel.py:238` | dart legs |

Rule 20 is the one that assembles the garment: `MetaGarment` stitches each slot's `bottom`
to the next slot's `top` in the order upper → belt → lower, which is exactly why
`lower_interface` is the label it propagates there.

### 4.3 Empirical frequency (1 200 patterns, 36 423 seams)

Aggregating the precedent's `out/parelles_costura.csv` over garment types gives **61
distinct role pairs**. The top of the table, with the code rule that produces each:

| kind | role A | role B | seams | patterns | code rule |
|---|---|---|---:|---:|---|
| UNION | `btorso` | `ftorso` | 4 014 | 821 | #1 shoulder + #2 side |
| UNION | `skirt_back` | `skirt_front` | 2 188 | 651 | #15 |
| UNION | `sleeve_b` | `sleeve_f` | 1 964 | 503 | #7 + #8 |
| DART | `ftorso` | `ftorso` | 1 840 | 460 | #22 (`bodice.py:51,62`) |
| DART | `btorso` | `btorso` | 1 840 | 460 | #22 (`bodice.py:147,152`) |
| UNION | `btorso` | `wb_back` | 1 686 | 381 | #20 |
| UNION | `ftorso` | `wb_front` | 1 224 | 381 | #20 |
| UNION | `wb_back` | `wb_front` | 1 206 | 603 | #16 |
| DART | `skirt_back` | `skirt_back` | 1 156 | 289 | #22 (`skirt_paneled.py:246`) |
| UNION | `btorso` | `skirt_back` | 1 030 | 211 | #20 (no belt) |
| UNION | `pant_b` | `pant_f` | 990 | 165 | #10 + #11 |
| UNION | `sl_cuff_skirt_b` | `sl_cuff_skirt_f` | 950 | 265 | #16 |
| UNION | `ftorso` | `sleeve_f` | 926 | 503 | #3 |
| UNION | `btorso` | `sleeve_b` | 926 | 503 | #3 |
| UNION | `ins_skirt_front` | `skirt_front` | 830 | 110 | #21 |
| CENTRE | `ftorso` | `ftorso` | 821 | 821 | #5 |
| CENTRE | `btorso` | `btorso` | 821 | 821 | #6 |
| UNION | `skirt_panel` | `skirt_panel` | 806 | 88 | #18 |
| UNION | `skirt_front` | `skirt_front` | 154 | 54 | **#19** |

The last row is worth pointing out: a `skirt_front`↔`skirt_front` union looks like a data
error until you find rule #19 — `SkirtLevels` stitches tier *i*'s waist to tier *i−1*'s hem,
and both tiers carry the same role because the tag is only an ordinal
(`skirt_levels.py:46`, `tag=str(i)`). **The code explains an empirical pair the data alone
would have flagged as suspicious.**

### 4.4 On the three seam kinds

The precedent's `UNIO` / `PINCA` / `CENTRE` split is confirmed by the code, and the code
adds precision:

- **DART** (`PINCA`) is not a seam between pieces at all — it is `Panel.add_dart`
  (`panel.py:238`) creating a stitch **inside one panel's own edge loop**. Its call sites
  are exactly four roles: `ftorso`, `btorso`, `skirt_back`, `pant_b` — matching the
  precedent's finding that `skirt_front` and `pant_f` never carry one. The asymmetry is a
  **generator decision** (`double_dart=True` only on the back panels, `pants.py:228`,
  `skirt_paneled.py:362`), not a law of the trade. That answers question 4 of the
  precedent's Montse list: **generator bias, and the front panels do get a side dart,
  just via a different mechanism** (`bodice.py:51`, inserted into the side edge).
- **CENTRE** is rules #5/#6 only, and it exists because `Shirt` always builds two mirrored
  halves. It is a *fold or seam* depending on the garment — GarmentCode always makes it a
  seam.
- Two structural kinds deserve their own row rather than being folded into `UNION`:
  **`level_join`** (#19) and **`insert_join`** (#21).

---

## 5 · Q5 · The map into the four FTT catalogue tables

### 5.1 🚨 First, what FTT already has — and the premise this overturns

Before proposing anything, the existing schema was read. **None of the four tables exists**
(`grep -rniE "EdgeRole|LandmarkRole|SeamPairTemplate|GarmentTypeItemEdgeProfile"` over the
backend: no hits). But three things that matter very much *do* exist:

| existing entity | file:line | what it is |
|---|---|---|
| `PatternPieceRole` | `backend/fhort/pom/models.py:140` | **the canonical piece-role catalogue**, 30 seeded English slugs |
| `PatternPiece` | `backend/fhort/patterns/models.py:150` | one DXF block; carries `piece_role` FK, laterality, ordinal, `nom` |
| `PatternSegment` | `backend/fhort/patterns/models.py:314` | a span of an edge in parametric coordinates (`vora`, `t_inici`, `t_fi`), origin auto/natural/declared, **free-text `nom` and no role FK** |

The 30 seeded piece roles (`backend/fhort/pom/management/commands/seed_pattern_piece_roles.py:23-52`):

```
front back body sleeve cuff collar collar_stand neckband yoke facing lining interlining
pocket pocket_flap pocket_facing waistband belt_loop fly zip_guard placket panel ruffle
skirt tie strap binding piping knee_patch lace_strip template
```

Mapping GarmentCode's 24 roles onto them (`scripts/mapping.py`):

```
GarmentCode roles          : 24
FTT PatternPieceRole slugs : 30
GC roles mapping cleanly   : 19
GC roles with NO FTT slug  : 5  -> pant_f, pant_b, hood, ins_skirt_front, ins_skirt_back
FTT slugs GC never produces: 22
distinct FTT slugs actually touched: 8
GC roles that encode FRONT/BACK in the role name: 22/24
```

> 🚨 **This overturns the brief's premise for one of the four tables.** The brief's goal is
> *«que el catàleg neixi ple d'anys de feina aliena»*. For **piece roles** that is backwards:
> GarmentCode's 24 roles collapse onto **8** of FTT's slugs, and **22 of FTT's 30 slugs
> GarmentCode cannot produce at all** — every DEREK auxiliary (`facing`, `lining`,
> `interlining`, `pocket*`, `belt_loop`, `fly`, `zip_guard`, **`placket` = TAPETA**,
> `binding`, `piping`, `knee_patch`, `lace_strip`, `template`) plus `yoke`, `collar_stand`,
> `neckband`, `ruffle`, `tie`, `strap`, `body`. **FTT's own piece catalogue is already
> 3,75× richer.** Importing GarmentCode's piece vocabulary would be a downgrade.
>
> **What GarmentCode genuinely brings is the other three tables.** FTT has *no* anatomical
> edge vocabulary at all (`PatternSegment.nom` is free text; `PatternSegment.tipus_vora` is
> an unconstrained `CharField` with no vocabulary anywhere in the code), *no* landmark role
> vocabulary (`PatternPOM` can anchor to a `PatternPoint` id — `patterns/models.py:436` —
> but the point has no name), and *no* seam grammar. **That** is the years of other
> people's work worth importing.
>
> The nearest thing FTT has to an edge vocabulary is `LayerRole`
> (`backend/fhort/patterns/engine/geometry.py:26`): `cut`, `sew`, `internal`, `turn`,
> `curve`, `notch`, `grain`, `mirror`. That is **CAD-layer semantics** — it says *this is a
> cutting line*, never *this is a neckline*. It is orthogonal to `EdgeRole`, not a rival.

### 5.2 🚨 The front/back axis mismatch

**22 of GarmentCode's 24 roles encode front/back in the role name** (`ftorso`/`btorso`,
`sleeve_f`/`sleeve_b`, `wb_front`/`wb_back`, …). FTT encodes **laterality** (L/R) as a
field on `PatternPiece` but has **no front/back axis at all**; only `front` and `back`
exist, and as two separate *body* roles.

Two ways out, and they are not equivalent:

- **(a) Add a `face` axis to `PatternPiece`** (`front` / `back` / `none`), mirroring the
  existing laterality field. 24 GarmentCode roles then collapse to 8 FTT roles × face, the
  role catalogue stays at 30, and `sleeve` stays one concept.
- **(b) Split the role vocabulary** into `sleeve_front` / `sleeve_back` etc. This doubles a
  catalogue that is already seeded and referenced by `PatternPiece.piece_role` (PROTECT),
  and it would put the same distinction in two places for `front`/`back`.

**Recommendation: (a).** It is the same shape as the laterality field that already works,
and it keeps `PatternPieceRole` stable — which matters because its slug is a cross-tenant
contract. *This is a decision for Agus (§7, D1).*

### 5.3 House style the new tables must follow

`PatternPieceRole` and `MeasurementLayer` (`pom/models.py:213`) establish the pattern for a
system catalogue, and the new tables should not invent a different one:

- **lives in `fhort.pom`** — the only app that is SHARED *and* TENANT, so the catalogue can
  exist in `public` and replicate to every tenant (`pom/models.py:145-149`);
- **`slug` is the stable contract**, `unique`, referenced by slug and **never by PK**
  (law G9, stated at `pom/models.py:239-241`) — which is exactly the brief's
  *«Referència per SLUG mai PK»*;
- **trilingual names from day one** (`nom_en`, `nom_ca`, `nom_es`), because adding them
  later means revisiting rows by hand;
- **the tenant proposes, promotion is a separate act**: `is_system`, `pendent_revisio`,
  `origen ∈ {SEED, MANUAL, IMPORT}`;
- **seeding never deletes**: `update_or_create` by slug, reverse migration is a noop.

> 🔑 The brief asks for *«estat de validació com a camp d'auditoria»*. **FTT already has
> that idiom** — `is_system` + `pendent_revisio` + `origen`. Introducing a new
> `validation_state` enum would be a second vocabulary for the same thing. The tables below
> reuse the existing three and add only what GarmentCode provenance genuinely needs
> (`source_ref`).

### 5.4 Proposed DDL

Text only. **No migration is written and none should be, until D1–D5 (§7) are answered** —
D1 in particular changes the shape of two of these tables.

```sql
-- =====================================================================
-- 1 · EdgeRole  — what an edge IS, anatomically.  fhort.pom (SHARED+TENANT)
-- =====================================================================
CREATE TABLE pom_edgerole (
    id                bigserial PRIMARY KEY,
    slug              varchar(60)  NOT NULL UNIQUE,   -- the contract; referenced by slug
    nom_en            varchar(120) NOT NULL,
    nom_ca            varchar(120) NOT NULL,
    nom_es            varchar(120) NOT NULL,
    -- anatomical zone: neck|shoulder|arm|torso|waist|leg|any
    zone              varchar(12)  NOT NULL,
    -- opening | seam | finished | internal | structural
    kind              varchar(12)  NOT NULL,
    -- the edge role this one is normally sewn to (slug, nullable, self-reference by slug)
    mates_slug        varchar(60)  NULL,
    -- true when the role is meaningful only together with a piece role (see §2.2)
    needs_piece_role  boolean      NOT NULL DEFAULT false,
    is_system         boolean      NOT NULL DEFAULT false,
    pendent_revisio   boolean      NOT NULL DEFAULT false,
    origen            varchar(10)  NOT NULL DEFAULT 'MANUAL',  -- SEED|MANUAL|IMPORT
    display_order     smallint     NOT NULL DEFAULT 0,
    -- provenance of an imported row: 'GarmentCode@d449629 bodice.py:306'
    source_ref        text         NOT NULL DEFAULT ''
);

-- Dock onto the existing edge-span entity. NEW COLUMN on an existing table:
--   ALTER TABLE patterns_patternsegment
--     ADD COLUMN edge_role_id bigint NULL REFERENCES pom_edgerole(id) ON DELETE RESTRICT;
-- `nom` (free text) stays: the role says what it is, `nom` says what this workshop calls it
-- — the same coexistence PatternPiece already has between `piece_role`, `nom_block`, `nom`.

-- =====================================================================
-- 2 · LandmarkRole — a named POINT, and whether it can be derived
-- =====================================================================
CREATE TABLE pom_landmarkrole (
    id                bigserial PRIMARY KEY,
    slug              varchar(60)  NOT NULL UNIQUE,
    nom_en            varchar(120) NOT NULL,
    nom_ca            varchar(120) NOT NULL,
    nom_es            varchar(120) NOT NULL,
    zone              varchar(12)  NOT NULL,
    -- TRUE = the point is computable from edge roles, no human marking required
    derivable         boolean      NOT NULL DEFAULT false,
    -- how: 'shared_endpoint' | 'far_endpoint' | 'extremum' | 'manual'
    derivation_op     varchar(20)  NOT NULL DEFAULT 'manual',
    -- operands as edge-role SLUGS, e.g. {"a": "neckline", "b": "shoulder_seam"}
    derivation_input  jsonb        NOT NULL DEFAULT '{}'::jsonb,
    -- tie-breaker when the op alone is ambiguous, e.g. 'lowest_y'
    derivation_tiebreak varchar(20) NOT NULL DEFAULT '',
    -- evidence for the rule, as measured: 2371 of 2371
    evidence_num      integer      NULL,
    evidence_den      integer      NULL,
    evidence_ref      text         NOT NULL DEFAULT '',
    is_system         boolean      NOT NULL DEFAULT false,
    pendent_revisio   boolean      NOT NULL DEFAULT false,
    origen            varchar(10)  NOT NULL DEFAULT 'MANUAL',
    display_order     smallint     NOT NULL DEFAULT 0,
    source_ref        text         NOT NULL DEFAULT ''
);

-- =====================================================================
-- 3 · GarmentTypeItemEdgeProfile — which edges a given piece is EXPECTED
--     to have, for a given garment-type item.  The anatomical template.
-- =====================================================================
CREATE TABLE pom_garmenttypeitemedgeprofile (
    id                    bigserial PRIMARY KEY,
    -- FK to the existing tasks.GarmentTypeItem (a complexity variant of a GarmentType)
    garment_type_item_id  bigint      NOT NULL REFERENCES tasks_garmenttypeitem(id)
                                      ON DELETE CASCADE,
    -- WHICH PIECE. Without this the row cannot be read: a garment does not have a
    -- neckline, its collar/front piece does.  By slug, per law G9.
    piece_role_slug       varchar(60) NOT NULL,
    -- optional face discriminator, pending decision D1: 'front'|'back'|''
    face                  varchar(6)  NOT NULL DEFAULT '',
    edge_role_slug        varchar(60) NOT NULL,
    -- core (>=90%) | common (25-90%) | rare (<25%)  — the precedent's three grades
    presence              varchar(8)  NOT NULL,
    min_count             smallint    NOT NULL DEFAULT 1,
    max_count             smallint    NULL,
    -- the measurement behind `presence`, with an HONEST denominator (see §3.2)
    observed_n            integer     NULL,
    observed_den          integer     NULL,
    observed_ref          text        NOT NULL DEFAULT '',
    pendent_revisio       boolean     NOT NULL DEFAULT true,
    origen                varchar(10) NOT NULL DEFAULT 'IMPORT',
    source_ref            text        NOT NULL DEFAULT '',
    UNIQUE (garment_type_item_id, piece_role_slug, face, edge_role_slug)
);

-- =====================================================================
-- 4 · SeamPairTemplate — which edge normally meets which edge
-- =====================================================================
CREATE TABLE pom_seampairtemplate (
    id                bigserial PRIMARY KEY,
    -- NULL = applies to any garment type
    garment_type_item_id bigint    NULL REFERENCES tasks_garmenttypeitem(id) ON DELETE CASCADE,
    -- union | dart | centre | level_join | insert_join
    seam_kind         varchar(12)  NOT NULL,
    piece_role_a_slug varchar(60)  NOT NULL,
    face_a            varchar(6)   NOT NULL DEFAULT '',
    edge_role_a_slug  varchar(60)  NOT NULL,
    piece_role_b_slug varchar(60)  NOT NULL,
    face_b            varchar(6)   NOT NULL DEFAULT '',
    edge_role_b_slug  varchar(60)  NOT NULL,
    -- TRUE = the two edges are produced by ONE constructor and are guaranteed to match
    -- (the Armhole* / neckline-projection case, §4.1). A matcher may trust these.
    co_generated      boolean      NOT NULL DEFAULT false,
    observed_seams    integer      NULL,
    observed_patterns integer      NULL,
    observed_den      integer      NULL,
    observed_ref      text         NOT NULL DEFAULT '',
    pendent_revisio   boolean      NOT NULL DEFAULT true,
    origen            varchar(10)  NOT NULL DEFAULT 'IMPORT',
    source_ref        text         NOT NULL DEFAULT ''
);
-- Ordering convention (a,b) must be canonical — sort the two sides by
-- (piece_role_slug, face, edge_role_slug) — or the same seam gets stored twice.
```

### 5.5 Field-by-field provenance

For every field: **imported** as-is from GarmentCode, **translated** (GarmentCode has the
information under another shape), or **FTT extension** (nothing in GarmentCode corresponds).

| table.field | status | note |
|---|---|---|
| `EdgeRole.slug`, `nom_en` | **translated** | from interface names + label call sites (§2.4); English names are ours, the concepts are theirs |
| `EdgeRole.nom_ca`, `nom_es` | **FTT extension** | GarmentCode is English-only |
| `EdgeRole.zone`, `kind` | **translated** | inferred from the panel class each interface belongs to |
| `EdgeRole.mates_slug` | **imported** | directly from the 20 stitch rules (§4.2) |
| `EdgeRole.needs_piece_role` | **translated** | encodes the §2.2 finding that `bottom`/`inside` are polysemous |
| `EdgeRole.source_ref` | **FTT extension** | audit of the import |
| `LandmarkRole.derivable`, `derivation_*` | **imported** | the HPS rule and its siblings (§6) |
| `LandmarkRole.evidence_*` | **imported** | 2 371/2 371, from the precedent |
| `GTIEdgeProfile.presence` | **translated** | the precedent's NUCLI/comuna/rara grades, **pending Montse** |
| `GTIEdgeProfile.observed_den` | **FTT extension** | the honest denominator §3.2 shows is needed |
| `GTIEdgeProfile.face` | **FTT extension** | the axis GarmentCode puts in the role name (§5.2) |
| `SeamPairTemplate.seam_kind` | **imported** | union/dart/centre from the code; level_join/insert_join added (§4.4) |
| `SeamPairTemplate.co_generated` | **imported** | the `Armhole*` pair-return guarantee (§4.1) |
| every `is_system`/`pendent_revisio`/`origen` | **FTT extension** | house style, §5.3 |
| **children's / newborn sizing** | **FTT extension** | GarmentCode's 1 200 patterns are cut for **one** adult body (§6.3) |
| **TAPETA / placket, DEREK auxiliaries** | **FTT extension** | absent from GarmentCode entirely (§5.1) |

> Table names above are Django defaults (`{app_label}_{model}`) derived from
> `name = 'fhort.tasks'` / `'fhort.pom'` in the app configs, with no `db_table` or
> `app_label` override anywhere in either `models.py`. Verify against the live schema
> before any migration is authored.

---

## 6 · LandmarkRole: what is derivable, and what is not

### 6.1 The HPS rule, and why it is safe

The precedent established that between the neckline run and the armhole run of a torso
panel there is **always exactly one edge** — the shoulder seam — in **2 371 of 2 371**
cases (100,00 %, `/root/n2_gym/out/hps_pont.txt`). The code says why this is structural
rather than lucky: the neckline and the armhole are cut into **two different corners** of
the same panel, `collar_corner` and `shoulder_corner` (`bodice.py:79-81`, `tee.py:57-58`),
and those two corners are separated by `self.edges[-2]` — **the shoulder edge**, which is
the very edge exposed as the `shoulder` interface (`bodice.py:75`). The two cuts can never
meet because they are applied to disjoint corners.

That makes the derivation a two-line rule over edge roles:

| landmark | op | operands | tiebreak |
|---|---|---|---|
| `hps` (high point shoulder) | `shared_endpoint` | `neckline`, `shoulder_seam` | — |
| `shoulder_point` | `shared_endpoint` | `shoulder_seam`, `armhole` | — |
| `underarm_point` | `far_endpoint` | `armhole` (away from `shoulder_point`) | `lowest_y` |
| `neck_centre_point` | `far_endpoint` | `neckline` (away from `hps`) | — |
| `waist_side_point` | `shared_endpoint` | `side_seam`, `waistline` | — |
| `hem_side_point` | `shared_endpoint` | `side_seam`, `hem` | — |
| `crotch_point` | `shared_endpoint` | `inseam`, `crotch_seam` | — |
| `underarm_seam_point` | `shared_endpoint` | `sleeve_cap`, `sleeve_underarm_seam` | — |

> 🔑 **This is the direct answer to blocker A11** of
> `INFORME_CORPUS_I_AUTOANCORATGE_2026-08-24`, which states that *no system datum
> identifies the HPS*. Once `EdgeRole` exists, the HPS is a derived value, not a datum
> anyone has to mark.
>
> ⚠️ **But it derives from EDGE ROLES, not from GarmentCode.** The 2 371/2 371 is measured
> on patterns where *the generator* labelled the edges. It says the rule is sound; it says
> nothing about whether FTT's CAD files carry anything equivalent. **Whether a DXF from the
> workshop can be given edge roles at all — automatically, or by the pattern maker
> declaring them — is the question that decides whether table 1 is worth building.**
> That is a question for Agus, not for Montse (§7, D2).

### 6.2 `derivable = false` is the interesting column

Landmarks that are **not** derivable from edge roles, and must be marked or measured:
bust point, apex, waist level on a curved side seam, knee line, elbow line. GarmentCode
computes several of these from *body measurements* (`body['bust_points']`,
`body['_bust_line']`, `body['hips_line']` — used at `bodice.py:48-49`, `pants.py:212`), i.e.
**from the body, not from the pattern**. That is a genuinely different mechanism and the
`derivation_op = 'manual'` default is the honest record of it.

### 6.3 What GarmentCode does not contain

Confirming and extending the precedent's §6 from the code side:

| gap | code evidence |
|---|---|
| **grading / sizing** | no grading anywhere; every panel is built from one `body` dict. The corpus's 1 200 `body_measurements.yaml` are byte-identical (precedent §6) |
| **children / newborn** | no age or body-class concept; `BodyParametrizationBase` (`params.py:11`) is one adult parametrisation |
| **plackets (TAPETA), pockets, facings, linings, interlinings** | no panel class produces any of them; the 24-role closure of §1.3 proves the absence rather than merely failing to observe it |
| **raglan / kimono sleeves** | `Sleeve` always attaches `in` to the bodice armhole (`bodice.py:289`); there is no alternative attachment |
| **fabric face** | only the binary `right_wrong` flag on 0,98 % of stitches (§4.1) |
| **notches, grain line** | not generated; FTT's `LayerRole` already has both (`geometry.py:38-39`) |
| **seam allowance** | absent — panels are net shapes; `LayerRole.SEW` in FTT exists precisely for this |

> The last two rows matter: **FTT's CAD layer is ahead of GarmentCode** on notches, grain
> and sewing lines. The import is not a one-way upgrade.

---

## 7 · Decisions left for Agus / Montse

Five, each with a recommendation. **D1 and D2 gate the DDL** — the rest can be settled
while building.

| # | question | recommendation | for |
|---|---|---|---|
| **D1** | Front/back: a new `face` axis on `PatternPiece`, or split the piece-role vocabulary? (§5.2) | **`face` axis.** Same shape as the laterality field that already works; keeps the 30 seeded slugs — a cross-tenant contract — untouched. Splitting would double the catalogue and duplicate the distinction that `front`/`back` already carry. | Agus |
| **D2** | Can an FTT DXF be given edge roles at all — derived from the CAD, or declared by the pattern maker? (§6.1) | **Answer this before writing any migration.** `PatternSegment` already has the `declarat` origin and a human declaring "this is the side seam" (`patterns/models.py:314-336`), so the manual path exists today. If the automatic path is not viable, table 1 is still worth it but its seeding story changes completely. | Agus |
| **D3** | Are `core`/`common`/`rare` at 90 % / 25 % the right cuts, and should the denominator be the true gate (§3.2)? | **Keep the three grades, fix the denominator.** The grades are a reasonable trade vocabulary; the denominators in the precedent's CSVs are inflated up to 4,1× and should be recomputed against the code-derived gate before anyone reads a percentage as a fact. | Montse + Agus |
| **D4** | Do `level_join` and `insert_join` deserve their own seam kinds, or are they unions? (§4.4) | **Own kinds.** Both join two pieces of the *same* role, so folding them into `union` makes the graph say a piece is sewn to itself — the precedent's own argument for separating `PINCA`. | Montse |
| **D5** | Is the dart asymmetry (back panels only) a law of the trade or generator bias? (§4.4) | **Generator bias**, with a caveat: the front bodice does get a dart, inserted into the side edge rather than the waist (`bodice.py:51`). The trade question Montse should actually be asked is whether front waist darts are expected in FTT's garments, not whether GarmentCode omits them. | Montse |

**Not a decision, a warning:** the brief cites `INFORME_PYGARMENT_MODEL_DADES` as a
precedent. **No file of that name exists** anywhere on this machine
(`find / -iname '*PYGARMENT*MODEL*'` → nothing), and
`INFORME_GIMNAS_N2_GARMENTCODEDATA_2026-08-25.md` cites it too, in its own header. Two
documents now reference a third that was never written. Nothing in this report depends on
it, but the citation chain should be broken rather than propagated again.

---

## 8 · Reproduction

Everything lives in `/root/gcd_ontology/`. The Python used is the precedent's venv
(`/root/n2_gym/venv/bin/python`, for `yaml` only) — **no package was installed and no venv
was created**, so no disk beyond the clone.

| script | what it produces | section |
|---|---|---|
| `scripts/params_tree.py` | `out/params_leaves.json` — the 122 leaves with type/range/default | §3 |
| `scripts/readers.py` | `out/param_readers.json`, `out/param_sites.json` — which class reads which parameter | §3.1 |
| `scripts/gates2.py` | the applicability gate per leaf, all 122 resolved | §3.1 |
| `scripts/roles_closure.py` | the 24-role closure proof and the multi-generator count | §1.3, §1.4 |
| `scripts/mapping.py` | the GarmentCode ↔ FTT piece-role mapping | §5.1 |

```bash
mkdir -p /root/gcd_ontology && cd /root/gcd_ontology
git clone --depth 1 https://github.com/maria-korosteleva/GarmentCode.git GarmentCode
P=/root/n2_gym/venv/bin/python
$P scripts/params_tree.py && $P scripts/readers.py && $P scripts/gates2.py
$P scripts/roles_closure.py          # reads /root/n2_gym/out/empremtes.csv
$P scripts/mapping.py
```

No seeds and no randomness: every number here is an exhaustive count or a grep over a
pinned commit (`d449629`). The corpus figures reuse the precedent's
`/root/n2_gym/out/` and `/root/n2_gym/data/b0_{default,aux}/` unchanged.

**Licensing.** The **code** read here is MIT (`LICENSE`, GarmentCode repo). The **data**
reused from the precedent is CC-BY-4.0 and requires attribution — see the precedent's §7
for the citation. Slugs and English names proposed in §2.4 and §6.1 are ours; the concepts
they name are GarmentCode's, and `source_ref` is where that is recorded row by row.
