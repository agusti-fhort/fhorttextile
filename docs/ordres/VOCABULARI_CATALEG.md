# VOCABULARI_CATALEG — creuament amb fonts externes · v2
**Data:** 2026-08-26 · **v2:** incorpora les RATIFICACIONS D'AGUS (8 esmenes CA + 2 alineacions ES) — pendents de seed idempotent.
**Objecte:** pre-validar `name_en` / `name_es` / `name_ca` dels 27 EdgeRole + 8 LandmarkRole sembrats a F3 perquè la sessió amb la Montse es concentri NOMÉS en les files ⚠.
**Regla:** el slug (EN) és contracte i NO es toca; els noms són dades editables. Tota esmena de la Montse mana.

**Veredictes:** ✓ = avalat (font externa o ratificació d'Agus) · ⚠ = pregunta dirigida per a la Montse.

---

## 0 · ESMENES PENDENTS DE SEED (ratificades Agus 26/08 — aplicar amb seed_semantic_catalog, idempotent)

    collar_outer_edge.name_ca  = "Canto exterior del coll"
    strapless_top_edge.name_ca = "Escot sense tirants"
    strapless_top_edge.name_es = "Escote sin tirantes"        (alineació)
    crotch_seam.name_ca        = "Tiro"
    dart_leg.name_ca           = "Llarg de pinça"
    level_join_seam.name_ca    = "Costura d'unió de capes"
    level_join_seam.name_en    = "Tier seam"                  (proposta v1, no vetada)
    level_join_seam.name_es    = "Costura de unión de capas"  (alineació, confirmar Montse)
    slit_edge.name_ca          = "Canto de l'obertura"
    waist_side_point.name_ca   = "Punt de costura lateral de cintura"
    crotch_point.name_ca       = "Punt de tiro"

---

## 1 · EDGE ROLES (27)

| # | slug | name_en | name_ca | name_es | V | nota |
|---|------|---------|---------|---------|---|------|
| 1 | neckline | Neckline | Escot | Escote | ✓ | fehrtrade; UoF |
| 2 | collar_attach | Collar attachment seam | Unió de coll | Unión de cuello | ✓ | estàndard |
| 3 | collar_outer_edge | Collar outer edge | Canto exterior del coll | Borde exterior del cuello | ✓ | **RATIFICAT AGUS** («canto» = registre d'ofici CA) |
| 4 | collar_side_seam | Collar side seam | Costura lateral del coll | Costura lateral del cuello | ✓ | estàndard (coll Turtle) |
| 5 | hood_attach | Hood attachment seam | Unió de caputxa | Unión de capucha | ✓ | estàndard |
| 6 | hood_centre_seam | Hood centre seam | Costura central de la caputxa | Costura central de la capucha | ✓ | estàndard |
| 7 | strapless_top_edge | Strapless top edge | Escot sense tirants | Escote sin tirantes | ✓ | **RATIFICAT AGUS** (és un escot, no una «vora de cos») |
| 8 | shoulder_seam | Shoulder seam | Costura d'espatlla | Costura de hombro | ✓ | universal |
| 9 | armhole | Armhole | Sisa | Sisa | ✓ | fehrtrade + maquila; EN variant *armscye* a la definició |
| 10 | sleeve_cap | Sleeve cap | Cap de màniga | Copa de manga | ✓ | UoF |
| 11 | underarm_seam | Underarm seam | Costura de sota-màniga | Costura de bajo manga | ⚠ | ES: ¿«bajo manga» o «inferior de la manga»? — Montse |
| 12 | cuff_line | Cuff line | Línia de puny | Línea de puño | ✓ | universal |
| 13 | centre_front | Centre front | Centre davant | Centro delantero | ✓ | universal (CF) |
| 14 | centre_back | Centre back | Centre esquena | Centro espalda | ✓ | universal (CB) |
| 15 | side_seam | Side seam | Costura lateral | Costura lateral | ⚠ | fehrtrade dona també **«costadillo»** (sastreria) — ¿el taller el fa servir segons peça? |
| 16 | waistline | Waistline | Línia de cintura | Línea de cintura | ✓ | fehrtrade |
| 17 | band_attach_upper | Band upper attachment | Unió superior de banda | Unión superior de banda | ✓ | estàndard |
| 18 | band_attach_lower | Band lower attachment | Unió inferior de banda | Unión inferior de banda | ✓ | estàndard |
| 19 | band_side_seam | Band side seam | Costura lateral de banda | Costura lateral de banda | ✓ | estàndard |
| 20 | inseam | Inseam | Entrecuix | Entrepierna | ✓ | universal |
| 21 | crotch_seam | Crotch seam | Tiro | Costura de tiro | ✓ | **RATIFICAT AGUS** (CA d'ofici = «tiro») |
| 22 | hem | Hem | Baix | Bajo | ⚠ | ES: «bajo» (línia) vs «dobladillo» (acabat) — que la Montse confirmi la distinció |
| 23 | gore_seam | Gore seam | Costura de gaia | Costura de nesga | ✓ | «nesga» confirmat |
| 24 | dart_leg | Dart leg | Llarg de pinça | Brazo de pinza | ✓ | **RATIFICAT AGUS** (CA); ES «brazo de pinza» es manté si la Montse no diu el contrari |
| 25 | godet_insert_seam | Godet insert seam | Costura d'inserció de godet | Costura de inserción de godet | ✓ | universal |
| 26 | level_join_seam | Tier seam | Costura d'unió de capes | Costura de unión de capas | ⚠ | **RATIFICAT AGUS** (CA «capes»); ES alineada — confirmar Montse |
| 27 | slit_edge | Slit edge | Canto de l'obertura | Borde de abertura | ✓ | **RATIFICAT AGUS» («canto»); EN nota: *vent* si és d'americana |

**Resum: 23 ✓ · 4 ⚠ (#11 · #15 · #22 · #26, totes preguntes d'ES).**

---

## 2 · LANDMARK ROLES (8)

| # | slug | name_en | name_ca | name_es | V | nota |
|---|------|---------|---------|---------|---|------|
| 1 | hps | High Point Shoulder (HPS) | HPS · punt alt d'espatlla | HPS · punto alto del hombro | ✓ | UoF usa HPS com a origen de mesures — confirma la llei de la casa |
| 2 | shoulder_point | Shoulder point | Punta d'espatlla | Punta de hombro | ✓ | UoF |
| 3 | underarm_point | Underarm point | Fons de sisa | Punto de axila | ✓ | ratificat Agus (axila) |
| 4 | neck_centre_point | Neck centre point | Centre de l'escot | Centro del escote | ✓ | estàndard |
| 5 | waist_side_point | Side waist point | Punt de costura lateral de cintura | Cintura en el costado | ✓ | **RATIFICAT AGUS** (CA) |
| 6 | hem_side_point | Hem side point | Baix al costat | Bajo en el costado | ✓ | coherent |
| 7 | crotch_point | Crotch point | Punt de tiro | Punto de tiro | ✓ | **RATIFICAT AGUS** (CA) |
| 8 | underarm_sleeve_point | Sleeve underarm point | Punt de sota-màniga | Punto de axila de manga | ⚠ | ¿nom propi al taller? |

**Resum: 7 ✓ · 1 ⚠.**

---

## 3 · ELS 3 PIECE ROLES NOUS (D6) + face

| slug | name_en | name_ca | name_es | V | nota |
|------|---------|---------|---------|---|------|
| pant | Pant leg | Camal | Pernera | ✓ | ¿«camal» o «cama»? — de passada |
| hood | Hood | Caputxa | Capucha | ✓ | universal |
| godet_insert | Godet | Godet | Godet | ✓ | universal |
| face=front | Front | Davant | Delantero | ✓ | universal |
| face=back | Back | Esquena / darrere | Espalda / trasero | ⚠ | ES: «espalda» (cos) vs «trasero» (pantaló/faldilla) — ¿un o depèn? |

---

## 4 · FONTS

1. fehrtrade — Spanish-English sewing translations (PDF): https://blog.fehrtrade.com/wp-content/uploads/2016/06/spanish-english-translations.pdf
2. Getex — Diccionario de términos textiles EN-ES (PDF): https://getex.net/blog/wp-content/uploads/2013/06/Diccionario-de-t%C3%A9rminos-textiles-EN-ES.pdf
3. University of Fashion — Terminology: https://www.universityoffashion.com/resources/terminology/
4. Maven Patterns — The Stitchery glossary: https://mavenpatterns.co.uk/the-stitchery-a-glossary-of-sewing-terms/
5. Wikipedia — Glossary of sewing terms: https://en.wikipedia.org/wiki/Glossary_of_sewing_terms
6. Glossari de producció maquila (Monografías) — registre LatAm, NOMÉS contrast
7. *(pendent)* GLOSSARY OF GARMENT DESIGNATIONS — preguntar Montse / INTEXTER

## 5 · QUÈ QUEDA PER A LA SESSIÓ

Vocabulari reduït a **8 converses dirigides**: #11 sota-màniga (ES) · #15 costadillo (ES) · #22 bajo/dobladillo (ES) · #26 unión de capas (ES) · punt de sota-màniga · espalda/trasero · les 2 òrfenes del coll (batejar). Tota la resta, contrastat — i si li grinyola una ✓ de passada, la seva paraula mana igualment.
