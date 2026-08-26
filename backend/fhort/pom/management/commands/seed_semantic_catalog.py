"""Sembra del CATÀLEG SEMÀNTIC: rols de vora, punts notables, gramàtica de costura.

F3 · Patró B · 2026-08-26. Calca `seed_pattern_piece_roles`: **`update_or_create` per
clau natural, mai `delete`**, el mateix contingut a `public` i a cada tenant, i tantes
passades com calgui — la segona no ha de tocar res.

DUES FONTS, i no es barregen:

  (a) **EL VOCABULARI surt de l'ONTOLOGIA**, hardcodat aquí amb `source_ref` fila a fila:
      `docs/diagnosis/REPORT_GCD_ONTOLOGY_2026-08-25.md` §2.4 (27 rols de vora), §6.1
      (8 rols de punt notable), §4.2 (les regles de costura del codi) i §5.1 (el mapa
      GarmentCode→FTT). Aquestes files diuen QUÈ EXISTEIX i no depenen de cap mesura.

  (b) **LES FREQÜÈNCIES es MESUREN a `ftt_corpus`** (128.974 designs), en calent i en
      READ-ONLY. Aquestes columnes diuen QUANT PASSA. Si el corpus no és accessible, la
      sembra escriu igualment el vocabulari i deixa els `observed_*` a NULL —**NULL i no
      zero**: «no s'ha mesurat» i «mesurat i surt zero» no són la mateixa cosa.

🚨 **EL DENOMINADOR ÉS HONEST.** `observed_den` **no** són mai els 128.974: és el nombre
de designs de les CATEGORIES on la parella és possible, i «possible» es MESURA (categories
on totes dues peces hi apareixen), no s'endevina. Una parella de pantaló es mesura sobre
patrons amb pantaló. La regla i les categories de cada fila viatgen dins d'`observed_ref`,
perquè un percentatge sense denominador escrit al costat és una xifra que menteix sola.

⚠️ `GarmentTypeItemEdgeProfile` **es crea buida a posta**: els perfils per GTI concret els
ha de mapar l'Agus amb la Montse. El que F3 sap sembrar és el vocabulari GENÈRIC, i el
genèric viu a `SeamPairTemplate` amb `garment_type_item=NULL`.

Ús:  python manage.py seed_semantic_catalog --dry-run     # llista completa, no escriu
     python manage.py seed_semantic_catalog               # aplica, idempotent
     python manage.py seed_semantic_catalog --schema fhort
     python manage.py seed_semantic_catalog --sense-corpus # salta les freqüències
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django_tenants.utils import get_tenant_model, schema_context

from fhort.pom.models import (
    EdgeRole, Face, GCPieceRoleMap, LandmarkRole, SeamPairTemplate, ZonaAnatomica,
)

#: Commit fixat de GarmentCode del qual surt tot el vocabulari. Viatja a cada `source_ref`.
GC = 'GarmentCode@d449629'
#: L'informe que va fer la lectura. Qui dubti d'una fila té dos llocs on anar.
INF = 'REPORT_GCD_ONTOLOGY_2026-08-25.md'
#: Conninfo de libpq (per paraules clau, una per línia). **No és un `.pgpass`** malgrat
#: el nom: `PGPASSFILE` no se'l menja (vegeu REPORT_GCD_CORPUS_IMPORT_2026-08-26 §3.7).
CORPUS_CONNINFO_FILE = '/root/gcd_corpus/corpus_ro.pgpass'


# ═════════════════════════════════════════════════════════════════════════════
# (a) VOCABULARI — de l'ontologia. Cap xifra d'aquí surt d'una mesura.
# ═════════════════════════════════════════════════════════════════════════════

Z = ZonaAnatomica
K = EdgeRole

#: (slug, zone, kind, mates_slug, needs_piece_role, nom_en, nom_ca, nom_es, source_ref)
#:
#: Els 24 primers són ANATÒMICS (informe §2.4): diuen on seu la vora al cos. Els tres
#: últims són ESTRUCTURALS: diuen com s'ha muntat la peça, no on seu — i per això
#: `kind='structural'` i no una zona inventada.
#:
#: `needs_piece_role=True` marca les vores POLISÈMIQUES de §2.2: a GarmentCode la clau
#: `bottom` és cintura en un cos, baix en una faldilla, línia de puny en una màniga i vora
#: d'unió en una cinturilla; `inside` és centre-davant en un tors i entrecuix en un
#: pantaló. Aquestes NO es poden llegir soles: es llegeixen amb el rol de la peça.
EDGE_ROLES = [
    ('neckline', Z.NECK, K.KIND_OPENING, 'collar_attach', False,
     'Neckline', 'Escot', 'Escote', 'bodice.py:351; collars.py:12-88'),
    ('collar_attach', Z.NECK, K.KIND_SEAM, 'neckline', False,
     'Collar attach', 'Unió de coll', 'Unión de cuello', 'collars.py:169,259; bodice.py:333'),
    ('collar_outer_edge', Z.NECK, K.KIND_FINISHED, '', True,
     'Collar outer edge', 'Vora exterior del coll', 'Borde exterior del cuello', 'bands.py:24'),
    ('collar_side_seam', Z.NECK, K.KIND_SEAM, 'collar_side_seam', True,
     'Collar side seam', 'Costura lateral del coll', 'Costura lateral del cuello',
     'collars.py:161-163'),
    ('hood_attach', Z.NECK, K.KIND_SEAM, 'neckline', False,
     'Hood attach', 'Unió de caputxa', 'Unión de capucha', 'collars.py:324'),
    ('hood_centre_seam', Z.NECK, K.KIND_SEAM, 'hood_centre_seam', False,
     'Hood centre seam', 'Costura central de la caputxa', 'Costura central de la capucha',
     'collars.py:323'),
    ('strapless_top', Z.TORSO, K.KIND_FINISHED, '', False,
     'Strapless top edge', 'Vora de cos sense tirants', 'Borde de cuerpo sin tirantes',
     'bodice.py:382-383'),
    ('shoulder_seam', Z.SHOULDER, K.KIND_SEAM, 'shoulder_seam', False,
     'Shoulder seam', "Costura d'espatlla", 'Costura de hombro',
     'bodice.py:75; bodice.py:211-213'),
    ('armhole', Z.ARM, K.KIND_OPENING, 'sleeve_cap', False,
     'Armhole', 'Sisa', 'Sisa', 'bodice.py:306; sleeves.py:11-105'),
    ('sleeve_cap', Z.ARM, K.KIND_SEAM, 'armhole', False,
     'Sleeve cap', 'Cap de màniga', 'Copa de manga', 'sleeves.py:180,289'),
    ('sleeve_underarm_seam', Z.ARM, K.KIND_SEAM, 'sleeve_underarm_seam', True,
     'Sleeve underarm seam', 'Costura de sota-màniga', 'Costura de bajo manga',
     'sleeves.py:281-284'),
    ('cuff_line', Z.ANY, K.KIND_SEAM, 'band_attach_upper', True,
     'Cuff line', 'Línia de puny', 'Línea de puño', 'sleeves.py:181,328-331'),
    ('centre_front', Z.TORSO, K.KIND_SEAM, 'centre_front', True,
     'Centre front', 'Centre davant', 'Centro delantero', 'bodice.py:74; bodice.py:443-444'),
    ('centre_back', Z.TORSO, K.KIND_SEAM, 'centre_back', True,
     'Centre back', 'Centre esquena', 'Centro espalda', 'bodice.py:126; bodice.py:445-446'),
    ('side_seam', Z.TORSO, K.KIND_SEAM, 'side_seam', True,
     'Side seam', 'Costura lateral', 'Costura lateral',
     'bodice.py:73,217; pants.py:115,232'),
    ('waistline', Z.WAIST, K.KIND_SEAM, 'band_attach_upper', True,
     'Waistline', 'Línia de cintura', 'Línea de cintura',
     'meta_garment.py:75; skirt_paneled.py:45'),
    ('band_attach_upper', Z.WAIST, K.KIND_SEAM, 'waistline', True,
     'Band upper attach', 'Unió superior de banda', 'Unión superior de banda', 'bands.py:19'),
    ('band_attach_lower', Z.WAIST, K.KIND_SEAM, 'waistline', True,
     'Band lower attach', 'Unió inferior de banda', 'Unión inferior de banda', 'bands.py:24'),
    ('band_side_seam', Z.WAIST, K.KIND_SEAM, 'band_side_seam', True,
     'Band side seam', 'Costura lateral de banda', 'Costura lateral de banda',
     'bands.py:74-75'),
    ('inseam', Z.LEG, K.KIND_SEAM, 'inseam', True,
     'Inseam', 'Entrecuix', 'Entrepierna', 'pants.py:120,233'),
    ('crotch_seam', Z.LEG, K.KIND_SEAM, 'crotch_seam', False,
     'Crotch seam', 'Costura de tir', 'Costura de tiro', 'pants.py:119,289-290'),
    ('hem', Z.ANY, K.KIND_FINISHED, '', True,
     'Hem', 'Baix', 'Bajo', 'skirt_paneled.py:49; pants.py:121'),
    ('gore_seam', Z.ANY, K.KIND_SEAM, 'gore_seam', True,
     'Gore seam', 'Costura de gaia', 'Costura de nesga', 'skirt_paneled.py:497-501'),
    ('dart_leg', Z.ANY, K.KIND_INTERNAL, 'dart_leg', False,
     'Dart leg', 'Braç de pinça', 'Brazo de pinza', 'panel.py:238; edge_factory.py:313'),
    # ── ESTRUCTURALS (informe §2.4, últim paràgraf) ──────────────────────────────
    ('godet_insert_seam', Z.ANY, K.KIND_STRUCTURAL, 'slit_edge', False,
     'Godet insert seam', "Costura d'inserció de godet", 'Costura de inserción de godet',
     'godet.py:113-114'),
    ('level_join_seam', Z.ANY, K.KIND_STRUCTURAL, 'level_join_seam', False,
     'Level join seam', "Costura d'unió de nivells", 'Costura de unión de niveles',
     'skirt_levels.py:62-64'),
    ('slit_edge', Z.ANY, K.KIND_STRUCTURAL, '', True,
     'Slit edge', "Vora d'obertura", 'Borde de abertura',
     'skirt_paneled.py:192,218; circle_skirt.py:216; edge_factory.py:292'),
]

#: (slug, zone, derivable, op, input, tiebreak, ev_num, ev_den, ev_ref, en, ca, es)
#:
#: Informe §6.1. **Tots vuit deriven de ROLS DE VORA, no de GarmentCode**: la mesura de
#: 2 371/2 371 està feta sobre patrons on el generador havia etiquetat les vores.
#:
#: 🚨 Només `hps` i `shoulder_point` porten evidència, i porten LA MATEIXA: totes dues són
#: un extrem del pont d'espatlla que `hps_pont.txt` va mesurar. Els altres sis són regles
#: escrites amb el mateix patró però **mai mesurades**, i van amb `NULL` — no amb un zero
#: ni amb el 2 371 manllevat del veí.
LANDMARK_ROLES = [
    ('hps', Z.SHOULDER, True, LandmarkRole.OP_SHARED_ENDPOINT,
     {'a': 'neckline', 'b': 'shoulder_seam'}, '', 2371, 2371,
     'n2_gym/out/hps_pont.txt · pont escot↔sisa = 1 vora en 2371 de 2371',
     'High point shoulder', "Punt alt d'espatlla", 'Punto alto de hombro'),
    ('shoulder_point', Z.SHOULDER, True, LandmarkRole.OP_SHARED_ENDPOINT,
     {'a': 'shoulder_seam', 'b': 'armhole'}, '', 2371, 2371,
     'n2_gym/out/hps_pont.txt · mateix pont, extrem oposat',
     'Shoulder point', "Punt d'espatlla", 'Punto de hombro'),
    ('underarm_point', Z.ARM, True, LandmarkRole.OP_FAR_ENDPOINT,
     {'a': 'armhole'}, 'lowest_y', None, None, '',
     'Underarm point', 'Punt de sota-braç', 'Punto de sobaco'),
    ('neck_centre_point', Z.NECK, True, LandmarkRole.OP_FAR_ENDPOINT,
     {'a': 'neckline'}, 'away_from:hps', None, None, '',
     'Neck centre point', "Punt central d'escot", 'Punto central de escote'),
    ('waist_side_point', Z.WAIST, True, LandmarkRole.OP_SHARED_ENDPOINT,
     {'a': 'side_seam', 'b': 'waistline'}, '', None, None, '',
     'Waist side point', 'Punt de cintura al costat', 'Punto de cintura en el costado'),
    ('hem_side_point', Z.ANY, True, LandmarkRole.OP_SHARED_ENDPOINT,
     {'a': 'side_seam', 'b': 'hem'}, '', None, None, '',
     'Hem side point', 'Punt de baix al costat', 'Punto de bajo en el costado'),
    ('crotch_point', Z.LEG, True, LandmarkRole.OP_SHARED_ENDPOINT,
     {'a': 'inseam', 'b': 'crotch_seam'}, '', None, None, '',
     'Crotch point', 'Punt de tir', 'Punto de tiro'),
    ('underarm_seam_point', Z.ARM, True, LandmarkRole.OP_SHARED_ENDPOINT,
     {'a': 'sleeve_cap', 'b': 'sleeve_underarm_seam'}, '', None, None, '',
     'Underarm seam point', 'Punt de sota-màniga', 'Punto de bajo manga'),
]

#: El mapa GarmentCode→FTT (informe §5.1 + `scripts/mapping.py`), amb els cinc forats
#: tancats pels tres slugs de D6. **24 rols de GarmentCode → 11 slugs d'FTT × cara.**
#:
#: 🚨 Quatre rols de GarmentCode cauen tots sobre `cuff`: puny de màniga, puny de màniga
#: acampanat, puny de cama i puny de cama acampanat. **La col·lisió és volguda** —
#: l'acampanament és un eix de variant, no una peça diferent— però vol dir que UNA
#: plantilla de costura d'FTT pot recollir més d'una parella del corpus, i per això les
#: freqüències s'agreguen a la BD del corpus i no sumant a mà.
GC_MAP = [
    ('ftorso', 'front', Face.FRONT, 'directe'),
    ('btorso', 'back', Face.BACK, 'directe'),
    ('sleeve_f', 'sleeve', Face.FRONT, "eix `face` (D1)"),
    ('sleeve_b', 'sleeve', Face.BACK, "eix `face` (D1)"),
    ('skirt_front', 'skirt', Face.FRONT, "eix `face` (D1)"),
    ('skirt_back', 'skirt', Face.BACK, "eix `face` (D1)"),
    ('skirt_panel', 'panel', Face.CAP, 'faldilla de gaies: el panell no té cara'),
    ('wb_front', 'waistband', Face.FRONT, "eix `face` (D1)"),
    ('wb_back', 'waistband', Face.BACK, "eix `face` (D1)"),
    ('sl_cuff_f', 'cuff', Face.FRONT, 'puny de màniga'),
    ('sl_cuff_b', 'cuff', Face.BACK, 'puny de màniga'),
    ('sl_cuff_skirt_f', 'cuff', Face.FRONT, 'puny de màniga ACAMPANAT (eix de variant)'),
    ('sl_cuff_skirt_b', 'cuff', Face.BACK, 'puny de màniga ACAMPANAT (eix de variant)'),
    ('pant_cuff_f', 'cuff', Face.FRONT, 'puny de cama'),
    ('pant_cuff_b', 'cuff', Face.BACK, 'puny de cama'),
    ('pant_cuff_skirt_f', 'cuff', Face.FRONT, 'puny de cama ACAMPANAT (eix de variant)'),
    ('pant_cuff_skirt_b', 'cuff', Face.BACK, 'puny de cama ACAMPANAT (eix de variant)'),
    ('collar_front', 'collar', Face.FRONT, "eix `face` (D1)"),
    ('collar_back', 'collar', Face.BACK, "eix `face` (D1)"),
    ('pant_f', 'pant', Face.FRONT, 'slug NOU (D6): FTT no tenia cama de pantaló'),
    ('pant_b', 'pant', Face.BACK, 'slug NOU (D6): FTT no tenia cama de pantaló'),
    ('hood', 'hood', Face.CAP, 'slug NOU (D6): FTT no tenia caputxa'),
    ('ins_skirt_front', 'godet_insert', Face.FRONT, 'slug NOU (D6): FTT no tenia godet'),
    ('ins_skirt_back', 'godet_insert', Face.BACK, 'slug NOU (D6): FTT no tenia godet'),
]

S = SeamPairTemplate

#: (regla, seam_kind, (peça_a, cara_a, vora_a), (peça_b, cara_b, vora_b), co_generated,
#:  source_ref)
#:
#: Les 22 regles de costura del codi (informe §4.2) traduïdes a vocabulari d'FTT, més les
#: tres de la caputxa i la del coll que §2.4 evidencia però que §4.2 no llista.
#:
#: 🔑 `co_generated=True` **no és una tendència estadística: és una garantia del
#: generador** (§4.1). Les tres factories `Armhole*` retornen la retallada del cos I la
#: vora de la màniga d'UNA crida, i `ArmholeCurve` hi passa `curve_match_tangents` perquè
#: coincideixin en llargada i tangent. Els escots igual, via `front_proj`/`back_proj`.
#:
#: ⚠️ Les regles #7 i #8 (`f_sleeve.top↔b_sleeve.top` i `.bottom↔.bottom`) donen UNA sola
#: plantilla: §2.4 té un únic slug —`sleeve_underarm_seam`— per a les dues interfícies, i
#: inventar-ne un segon per simetria seria vocabulari que el codi no evidencia.
#:
#: ⚠️ La regla #20 (`MetaGarment`: amunt→cinturó→avall) no és UNA costura: és el patró que
#: MUNTA el garment, i genera tantes plantilles com combinacions de peces hi ha a sobre i
#: a sota del cinturó. S'hi despleguen les 11 combinacions que el corpus evidencia.
SEAM_PAIRS = [
    # ── R1-R2 · el tors ─────────────────────────────────────────────────────────
    ('#1', S.KIND_UNION, ('front', Face.FRONT, 'shoulder_seam'),
     ('back', Face.BACK, 'shoulder_seam'), False, 'bodice.py:211-213'),
    ('#2', S.KIND_UNION, ('front', Face.FRONT, 'side_seam'),
     ('back', Face.BACK, 'side_seam'), False, 'bodice.py:217-218'),
    # ── R3 · sisa ↔ cap de màniga. QUATRE files i no dues: el cap de màniga
    #        travessa l'espatlla, o sigui que cada meitat de màniga toca les dues
    #        cares del cos. Que una de les quatre surti a ZERO és una DADA (§4.3).
    ('#3', S.KIND_UNION, ('front', Face.FRONT, 'armhole'),
     ('sleeve', Face.FRONT, 'sleeve_cap'), True, 'bodice.py:289-291; sleeves.py:56-105'),
    ('#3', S.KIND_UNION, ('back', Face.BACK, 'armhole'),
     ('sleeve', Face.BACK, 'sleeve_cap'), True, 'bodice.py:289-291; sleeves.py:56-105'),
    ('#3', S.KIND_UNION, ('front', Face.FRONT, 'armhole'),
     ('sleeve', Face.BACK, 'sleeve_cap'), True, 'bodice.py:289-291; sleeves.py:56-105'),
    ('#3', S.KIND_UNION, ('back', Face.BACK, 'armhole'),
     ('sleeve', Face.FRONT, 'sleeve_cap'), True, 'bodice.py:289-291; sleeves.py:56-105'),
    # ── R4 · escot ↔ coll ───────────────────────────────────────────────────────
    ('#4', S.KIND_UNION, ('front', Face.FRONT, 'neckline'),
     ('collar', Face.FRONT, 'collar_attach'), True, 'bodice.py:333-335; collars.py:122-123'),
    ('#4', S.KIND_UNION, ('back', Face.BACK, 'neckline'),
     ('collar', Face.BACK, 'collar_attach'), True, 'bodice.py:333-335; collars.py:122-123'),
    # ── R5-R6 · els centres ─────────────────────────────────────────────────────
    ('#5', S.KIND_CENTRE, ('front', Face.FRONT, 'centre_front'),
     ('front', Face.FRONT, 'centre_front'), False, 'bodice.py:443-444'),
    ('#6', S.KIND_CENTRE, ('back', Face.BACK, 'centre_back'),
     ('back', Face.BACK, 'centre_back'), False, 'bodice.py:445-446'),
    # ── R7+R8 · la màniga ───────────────────────────────────────────────────────
    ('#7+#8', S.KIND_UNION, ('sleeve', Face.FRONT, 'sleeve_underarm_seam'),
     ('sleeve', Face.BACK, 'sleeve_underarm_seam'), False, 'sleeves.py:281-284'),
    # ── R9 · puny de màniga ─────────────────────────────────────────────────────
    ('#9', S.KIND_UNION, ('cuff', Face.FRONT, 'band_attach_upper'),
     ('sleeve', Face.FRONT, 'cuff_line'), False, 'sleeves.py:328-331'),
    ('#9', S.KIND_UNION, ('cuff', Face.BACK, 'band_attach_upper'),
     ('sleeve', Face.BACK, 'cuff_line'), False, 'sleeves.py:328-331'),
    # ── R10-R13 · el pantaló ────────────────────────────────────────────────────
    ('#10', S.KIND_UNION, ('pant', Face.FRONT, 'side_seam'),
     ('pant', Face.BACK, 'side_seam'), False, 'pants.py:232'),
    ('#11', S.KIND_UNION, ('pant', Face.FRONT, 'inseam'),
     ('pant', Face.BACK, 'inseam'), False, 'pants.py:233'),
    ('#12', S.KIND_CENTRE, ('pant', Face.FRONT, 'crotch_seam'),
     ('pant', Face.FRONT, 'crotch_seam'), False, 'pants.py:289'),
    ('#13', S.KIND_CENTRE, ('pant', Face.BACK, 'crotch_seam'),
     ('pant', Face.BACK, 'crotch_seam'), False, 'pants.py:290'),
    # ── R14 · puny de cama ──────────────────────────────────────────────────────
    ('#14', S.KIND_UNION, ('cuff', Face.FRONT, 'band_attach_upper'),
     ('pant', Face.FRONT, 'cuff_line'), False, 'pants.py:263-265'),
    ('#14', S.KIND_UNION, ('cuff', Face.BACK, 'band_attach_upper'),
     ('pant', Face.BACK, 'cuff_line'), False, 'pants.py:263-265'),
    # Els creuats del puny de cama, pel mateix motiu que els de la sisa: `pant_bottom` es
    # una interficie MULTIPLE i el puny hi cus totes dues cares. Un dels dos surt a ZERO
    # al corpus, i el zero es tan informatiu com el 3.673 del seu germa.
    ('#14', S.KIND_UNION, ('cuff', Face.FRONT, 'band_attach_upper'),
     ('pant', Face.BACK, 'cuff_line'), False, 'pants.py:263-265'),
    ('#14', S.KIND_UNION, ('cuff', Face.BACK, 'band_attach_upper'),
     ('pant', Face.FRONT, 'cuff_line'), False, 'pants.py:263-265'),
    # ── R15-R16 · faldilla i banda ──────────────────────────────────────────────
    ('#15', S.KIND_UNION, ('skirt', Face.FRONT, 'side_seam'),
     ('skirt', Face.BACK, 'side_seam'), False,
     'skirt_paneled.py:371-373,431-433; circle_skirt.py:185-187'),
    ('#16', S.KIND_UNION, ('waistband', Face.FRONT, 'band_side_seam'),
     ('waistband', Face.BACK, 'band_side_seam'), False, 'bands.py:73-75,172-174,213-215'),
    # 🚨 El puny TAMBE es una banda. La regla #16 es de `StraightBandPanel`, i la
    # cinturilla no n'es l'unica: un puny es una banda al voltant del brac o de la cama i
    # es tanca amb les mateixes dues costures laterals. Aquesta fila NO surt de rellegir
    # el codi: surt del cens del corpus, que la va deixar orfe amb 241.004 costures i
    # 47.912 patrons -- la parella orfa mes gran de totes, i era una regla que ja teniem.
    ('#16', S.KIND_UNION, ('cuff', Face.FRONT, 'band_side_seam'),
     ('cuff', Face.BACK, 'band_side_seam'), False, 'bands.py:73-75'),
    # ── R17 · el puny acampanat penja del puny recte (CuffBandSkirt) ────────────
    ('#17', S.KIND_UNION, ('cuff', Face.FRONT, 'band_attach_lower'),
     ('cuff', Face.FRONT, 'waistline'), False, 'bands.py:250-251'),
    ('#17', S.KIND_UNION, ('cuff', Face.BACK, 'band_attach_lower'),
     ('cuff', Face.BACK, 'waistline'), False, 'bands.py:250-251'),
    # ── R18 · gaia amb gaia ─────────────────────────────────────────────────────
    ('#18', S.KIND_UNION, ('panel', Face.CAP, 'gore_seam'),
     ('panel', Face.CAP, 'gore_seam'), False, 'skirt_paneled.py:497-501'),
    # ── R19 · nivells (D4: mena PRÒPIA) ─────────────────────────────────────────
    ('#19', S.KIND_LEVEL_JOIN, ('skirt', Face.FRONT, 'hem'),
     ('skirt', Face.FRONT, 'waistline'), False, 'skirt_levels.py:62-64'),
    ('#19', S.KIND_LEVEL_JOIN, ('skirt', Face.BACK, 'hem'),
     ('skirt', Face.BACK, 'waistline'), False, 'skirt_levels.py:62-64'),
    # ── R20 · la unió de cintura: la regla que MUNTA el garment ─────────────────
    ('#20', S.KIND_UNION, ('front', Face.FRONT, 'waistline'),
     ('waistband', Face.FRONT, 'band_attach_upper'), False, 'meta_garment.py:70-72,89-91'),
    ('#20', S.KIND_UNION, ('back', Face.BACK, 'waistline'),
     ('waistband', Face.BACK, 'band_attach_upper'), False, 'meta_garment.py:70-72,89-91'),
    ('#20', S.KIND_UNION, ('waistband', Face.FRONT, 'band_attach_lower'),
     ('skirt', Face.FRONT, 'waistline'), False, 'meta_garment.py:70-72,89-91'),
    ('#20', S.KIND_UNION, ('waistband', Face.BACK, 'band_attach_lower'),
     ('skirt', Face.BACK, 'waistline'), False, 'meta_garment.py:70-72,89-91'),
    ('#20', S.KIND_UNION, ('waistband', Face.FRONT, 'band_attach_lower'),
     ('pant', Face.FRONT, 'waistline'), False, 'meta_garment.py:70-72,89-91'),
    ('#20', S.KIND_UNION, ('waistband', Face.BACK, 'band_attach_lower'),
     ('pant', Face.BACK, 'waistline'), False, 'meta_garment.py:70-72,89-91'),
    ('#20', S.KIND_UNION, ('waistband', Face.FRONT, 'band_attach_lower'),
     ('panel', Face.CAP, 'waistline'), False, 'meta_garment.py:70-72,89-91'),
    ('#20', S.KIND_UNION, ('waistband', Face.BACK, 'band_attach_lower'),
     ('panel', Face.CAP, 'waistline'), False, 'meta_garment.py:70-72,89-91'),
    # …i les mateixes unions SENSE cinturó, que és el cas que el codi tracta a `:95`.
    ('#20', S.KIND_UNION, ('front', Face.FRONT, 'waistline'),
     ('skirt', Face.FRONT, 'waistline'), False, 'meta_garment.py:89-91'),
    ('#20', S.KIND_UNION, ('back', Face.BACK, 'waistline'),
     ('skirt', Face.BACK, 'waistline'), False, 'meta_garment.py:89-91'),
    ('#20', S.KIND_UNION, ('front', Face.FRONT, 'waistline'),
     ('pant', Face.FRONT, 'waistline'), False, 'meta_garment.py:89-91'),
    ('#20', S.KIND_UNION, ('back', Face.BACK, 'waistline'),
     ('pant', Face.BACK, 'waistline'), False, 'meta_garment.py:89-91'),
    ('#20', S.KIND_UNION, ('front', Face.FRONT, 'waistline'),
     ('panel', Face.CAP, 'waistline'), False, 'meta_garment.py:89-91'),
    ('#20', S.KIND_UNION, ('back', Face.BACK, 'waistline'),
     ('panel', Face.CAP, 'waistline'), False, 'meta_garment.py:89-91'),
    # ── R21 · el godet (D4: mena PRÒPIA) ────────────────────────────────────────
    ('#21', S.KIND_INSERT_JOIN, ('godet_insert', Face.FRONT, 'godet_insert_seam'),
     ('skirt', Face.FRONT, 'slit_edge'), False, 'godet.py:113-114'),
    ('#21', S.KIND_INSERT_JOIN, ('godet_insert', Face.BACK, 'godet_insert_seam'),
     ('skirt', Face.BACK, 'slit_edge'), False, 'godet.py:113-114'),
    # ── R22 · les pinces. NOMÉS els quatre rols que el codi punxa (D5: biaix de
    #        generador, no llei d'ofici — `double_dart=True` només a les esquenes).
    ('#22', S.KIND_DART, ('front', Face.FRONT, 'dart_leg'),
     ('front', Face.FRONT, 'dart_leg'), False, 'panel.py:238; bodice.py:51,62'),
    ('#22', S.KIND_DART, ('back', Face.BACK, 'dart_leg'),
     ('back', Face.BACK, 'dart_leg'), False, 'panel.py:238; bodice.py:147,152'),
    ('#22', S.KIND_DART, ('skirt', Face.BACK, 'dart_leg'),
     ('skirt', Face.BACK, 'dart_leg'), False, 'panel.py:238; skirt_paneled.py:246,295'),
    ('#22', S.KIND_DART, ('pant', Face.BACK, 'dart_leg'),
     ('pant', Face.BACK, 'dart_leg'), False, 'panel.py:238; pants.py:128,168'),
    # ── La caputxa i el coll: §2.4 les evidencia, la llista de §4.2 no les porta ──
    ('§2.4', S.KIND_UNION, ('front', Face.FRONT, 'neckline'),
     ('hood', Face.CAP, 'hood_attach'), False, 'collars.py:324'),
    ('§2.4', S.KIND_UNION, ('back', Face.BACK, 'neckline'),
     ('hood', Face.CAP, 'hood_attach'), False, 'collars.py:324'),
    ('§2.4', S.KIND_CENTRE, ('hood', Face.CAP, 'hood_centre_seam'),
     ('hood', Face.CAP, 'hood_centre_seam'), False, 'collars.py:323'),
    ('§2.4', S.KIND_UNION, ('collar', Face.FRONT, 'collar_side_seam'),
     ('collar', Face.BACK, 'collar_side_seam'), False, 'collars.py:161-163'),
]


# =============================================================================
# (b) FREQUENCIES -- mesurades a `ftt_corpus`, en READ-ONLY i en calent.
# =============================================================================

#: Separador de la clau composta (peca|cara). Cap slug ni cap cara no en porta mai.
SEP = '|'

#: Normalitzacio del nom del panell a rol de GarmentCode: treu lateralitat i ordinal.
#: Quatre passades i no una: GarmentCode posa el costat en tres llocs diferents segons la
#: familia (`left_ftorso`, `sl_left_cuff_f`, `pant_l_cuff_f`, `pant_f_l`). Verificat: sobre
#: els 128.974 designs dona **exactament 24 rols**, els mateixos 24 que l'informe va tancar
#: sobre 1.200 -- la clausura de §1.3 aguanta 107x la mostra amb que es va provar.
NORMALITZA_ROL = (
    "regexp_replace(regexp_replace(regexp_replace(regexp_replace("
    "{col}, '^(left|right)_', ''), '^sl_(left|right)_', 'sl_'), "
    "'^pant_(l|r)_', 'pant_'), '(_(l|r)|_[0-9]+)$', '')"
)

#: La mena de costura es classifica sobre els rols de **GarmentCode**, no sobre els slugs
#: d'FTT. Si es fes sobre els slugs, un puny recte cosit al seu puny acampanat
#: (`sl_cuff_b` <-> `sl_cuff_skirt_b`, dos rols diferents que cauen tots dos a `cuff/back`)
#: es llegiria com «una peca cosida amb ella mateixa» i cauria a `centre`. Seria una
#: costura real classificada com el seu contrari, i en silenci.
CENS_SQL = """
WITH p AS (
    SELECT pn.design_id, pn.name, d.garment_category AS cat,
           {norm_name} AS gc_role
    FROM panel pn JOIN design d ON d.id = pn.design_id
), m(gc_role, slug, face) AS (VALUES {map_values}),
pm AS (
    SELECT p.design_id, p.name, p.cat, p.gc_role,
           m.slug, m.face, m.slug || '{sep}' || m.face AS k
    FROM p JOIN m ON m.gc_role = p.gc_role
), s AS (
    SELECT st.design_id,
           CASE
             WHEN st.panel_a = st.panel_b THEN 'dart'
             WHEN pa.slug = 'godet_insert' OR pb.slug = 'godet_insert' THEN 'insert_join'
             WHEN pa.gc_role = pb.gc_role
                  AND pa.gc_role IN ('skirt_front','skirt_back') THEN 'level_join'
             WHEN pa.gc_role = pb.gc_role AND pa.gc_role = 'skirt_panel' THEN 'union'
             WHEN pa.gc_role = pb.gc_role THEN 'centre'
             ELSE 'union'
           END AS kind,
           LEAST(pa.k, pb.k) AS ka, GREATEST(pa.k, pb.k) AS kb
    FROM stitch st
    JOIN pm pa ON pa.design_id = st.design_id AND pa.name = st.panel_a
    JOIN pm pb ON pb.design_id = st.design_id AND pb.name = st.panel_b
),
pres AS (SELECT k, cat FROM pm GROUP BY 1, 2),
cats AS (SELECT garment_category AS cat, count(*) AS n FROM design GROUP BY 1),
agg AS (
    SELECT kind, ka, kb, count(*) AS seams, count(DISTINCT design_id) AS pats
    FROM s GROUP BY 1, 2, 3
),
den AS (
    SELECT agg.kind, agg.ka, agg.kb,
           COALESCE(sum(c.n), 0)::int AS den,
           COALESCE(string_agg(c.cat, ',' ORDER BY c.cat), '') AS cats
    FROM agg
    LEFT JOIN cats c ON EXISTS (SELECT 1 FROM pres WHERE pres.k = agg.ka AND pres.cat = c.cat)
                    AND EXISTS (SELECT 1 FROM pres WHERE pres.k = agg.kb AND pres.cat = c.cat)
    GROUP BY 1, 2, 3
)
SELECT agg.kind, agg.ka, agg.kb, agg.seams, agg.pats, den.den, den.cats
FROM agg JOIN den ON den.kind = agg.kind AND den.ka = agg.ka AND den.kb = agg.kb
"""

#: En quines categories apareix cada costat (peca+cara), i quants designs te cada
#: categoria. Amb aixo, una parella que el corpus **no conte** rep igualment un
#: denominador: 0 de N, que es una mesura, i no NULL, que es una absencia de mesura.
PRESENCIA_SQL = """
WITH p AS (
    SELECT pn.design_id, d.garment_category AS cat, {norm_name} AS gc_role
    FROM panel pn JOIN design d ON d.id = pn.design_id
), m(gc_role, slug, face) AS (VALUES {map_values})
SELECT m.slug || '{sep}' || m.face AS k, p.cat
FROM p JOIN m ON m.gc_role = p.gc_role
GROUP BY 1, 2
"""

CATEGORIES_SQL = 'SELECT garment_category, count(*) FROM design GROUP BY 1'


def _conninfo(fitxer: str) -> str:
    """El conninfo de libpq, d'una linia per paraula clau a una sola cadena.

    El fitxer es diu `.pgpass` i **no ho es**: PGPASSFILE no se'l menja
    (REPORT_GCD_CORPUS_IMPORT_2026-08-26 §3.7). Es consumeix com a cadena de connexio.
    """
    with open(fitxer) as f:
        return ' '.join(ln.strip() for ln in f
                        if ln.strip() and not ln.lstrip().startswith('#'))


def mesura_corpus(conninfo_file: str = CORPUS_CONNINFO_FILE) -> tuple[dict, dict]:
    """Cens de parelles de costura del corpus. -> ({clau: mesura}, {metadada})

    La clau es `(kind, (slug_a, face_a), (slug_b, face_b))` amb els dos costats ordenats
    per `(slug, face)` -- la mateixa ordenacio que `SeamPairTemplate.ordena`, pero sense el
    rol de vora, que el corpus no te.

    **READ-ONLY de debo**: connexio `readonly=True` a mes del rol `corpus_ro`, que ja
    nomes te `SELECT`. Dos panys i no un: el rol el pot canviar algu, la connexio no.
    """
    import psycopg2

    map_values = ', '.join(
        "('{}', '{}', '{}')".format(gc, slug, face) for gc, slug, face, _ in GC_MAP)
    sql = CENS_SQL.format(
        norm_name=NORMALITZA_ROL.format(col='pn.name'),
        map_values=map_values,
        sep=SEP,
    )
    cens: dict = {}
    conn = psycopg2.connect(_conninfo(conninfo_file))
    try:
        conn.set_session(readonly=True, autocommit=True)
        with conn.cursor() as cur:
            cur.execute(sql)
            for kind, ka, kb, seams, pats, den, cats in cur.fetchall():
                a = tuple(ka.split(SEP))
                b = tuple(kb.split(SEP))
                cens[(kind, a, b)] = {
                    'seams': seams, 'pats': pats, 'den': den, 'cats': cats,
                }
            cur.execute(PRESENCIA_SQL.format(
                norm_name=NORMALITZA_ROL.format(col='pn.name'),
                map_values=map_values, sep=SEP))
            presencia: dict = {}
            for k, cat in cur.fetchall():
                presencia.setdefault(tuple(k.split(SEP)), set()).add(cat)
            cur.execute(CATEGORIES_SQL)
            categories = dict(cur.fetchall())
            cur.execute('SELECT count(*) FROM design')
            n_designs = cur.fetchone()[0]
    finally:
        conn.close()
    return cens, {'n_designs': n_designs, 'n_parelles': len(cens),
                  'presencia': presencia, 'categories': categories}


def llegeix_mesura(cens, meta, kind, costat_a, costat_b):
    """La mesura d'una plantilla. -> dict o None (None NOMES si no hi ha corpus).

    🚨 **Una parella que el cens no porta NO es una absencia de mesura: es un ZERO
    mesurat.** El cens recorre els 3,9 M de costures del corpus sencer; si la clau no hi
    surt, vol dir que en 128.974 designs no passa mai. Escriure-hi NULL diria «no ho hem
    mirat» quan justament s'ha mirat tot, i taparia troballes com ara que
    `back.armhole <-> sleeve/front.sleeve_cap` surt a ZERO mentre el seu mirall surt a
    35.121 patrons. El denominador d'aquest zero es calcula igual, des de la presencia de
    les dues peces per categoria.
    """
    if cens is None:
        return None
    clau = clau_de_mesura(kind, costat_a, costat_b)
    if clau in cens:
        return cens[clau]
    _, ka, kb = clau
    presencia = meta.get('presencia', {})
    categories = meta.get('categories', {})
    cats = sorted(presencia.get(ka, set()) & presencia.get(kb, set()))
    return {
        'seams': 0, 'pats': 0,
        'den': sum(categories.get(c, 0) for c in cats),
        'cats': ','.join(cats),
        'zero': True,
    }


def clau_de_mesura(kind, costat_a, costat_b):
    """La clau del cens que correspon a una plantilla. **Sense el rol de vora.**

    El corpus no sap que es una vora: `stitch` en desa l'INDEX (`{panel, edge}`) i les
    interficies no se serialitzen (informe §4.1). O sigui que dues plantilles que
    comparteixen les dues peces --l'espatlla i el costat del tors son totes dues
    `front<->back`-- **cauen a la mateixa clau i comparteixen xifra**. No es un error de
    mesura: es el sostre del corpus, i `observed_ref` ho diu fila a fila perque ningu no
    llegeixi el numero com si fos nomes d'aquella costura.
    """
    ka = (costat_a[0], str(costat_a[1]))
    kb = (costat_b[0], str(costat_b[1]))
    return (kind, ka, kb) if ka <= kb else (kind, kb, ka)


# =============================================================================
# LA SEMBRA. `update_or_create` per clau natural, mai `delete`.
# =============================================================================

def _observed_ref(mesura, clau, conflictes) -> str:
    """La frase que acompanya cada xifra. Sense aixo, un percentatge menteix sol."""
    if mesura is None:
        return ''
    kind, a, b = clau
    parts = [
        'ftt_corpus@2026-08-26 (128.974 designs)',
        'clau={}/{}{}{}<->{}{}{}'.format(kind, a[0], SEP, a[1] or '-', b[0], SEP, b[1] or '-'),
        'den=categories on totes dues peces hi son: [{}]'.format(mesura['cats'] or 'cap'),
    ]
    if mesura.get('zero'):
        parts.append(
            'ZERO MESURAT: la parella no surt cap cop al corpus sencer (no es una '
            'absencia de mesura)')
    if conflictes > 1:
        parts.append(
            'ATENCIO: {} plantilles comparteixen aquesta xifra -- el corpus no serialitza '
            'els noms d\'interficie, nomes l\'index de vora (informe §4.1)'.format(conflictes))
    return ' · '.join(parts)


def sembra(schema: str, cens: dict | None, meta: dict, dry_run: bool = False) -> dict:
    """Sembra el catalec semantic en un schema. -> recompte per taula. MAI esborra."""
    # Quantes plantilles comparteixen cada clau del cens: es el que fa que la nota
    # de conflicte s'escrigui sola i no calgui recordar-se'n taula a taula.
    conflictes: dict = {}
    for _, kind, a, b, _, _ in SEAM_PAIRS:
        conflictes[clau_de_mesura(kind, a, b)] = \
            conflictes.get(clau_de_mesura(kind, a, b), 0) + 1

    r = {'edge_roles': [0, 0], 'landmark_roles': [0, 0],
         'seam_pairs': [0, 0], 'gc_map': [0, 0]}

    with schema_context(schema):
        if dry_run:
            r['edge_roles'] = _dry(EdgeRole, 'slug', [x[0] for x in EDGE_ROLES])
            r['landmark_roles'] = _dry(LandmarkRole, 'slug', [x[0] for x in LANDMARK_ROLES])
            r['gc_map'] = _dry(GCPieceRoleMap, 'gc_role', [x[0] for x in GC_MAP])
            existents = {
                (t.garment_type_item_id, t.seam_kind) + t.costat_a + t.costat_b
                for t in SeamPairTemplate.objects.all()
            }
            nous = 0
            for _, kind, a, b, _, _ in SEAM_PAIRS:
                ca, cb = SeamPairTemplate.ordena(a, b)
                if (None, kind) + ca + cb not in existents:
                    nous += 1
            r['seam_pairs'] = [nous, len(SEAM_PAIRS) - nous]
            return r

        with transaction.atomic():
            for ordre, (slug, zone, kind, mates, needs, en, ca, es, ref) in \
                    enumerate(EDGE_ROLES, start=1):
                _, creat = EdgeRole.objects.update_or_create(
                    slug=slug,
                    defaults={
                        'nom_en': en, 'nom_ca': ca, 'nom_es': es,
                        'zone': zone, 'kind': kind, 'mates_slug': mates,
                        'needs_piece_role': needs,
                        'is_system': True, 'pendent_revisio': False,
                        'origen': EdgeRole.ORIGEN_SEED,
                        'display_order': ordre * 10,
                        'source_ref': '{} {} · {} §2.4'.format(GC, ref, INF),
                    })
                r['edge_roles'][0 if creat else 1] += 1

            for ordre, (slug, zone, deriv, op, inp, tb, evn, evd, evr, en, ca, es) in \
                    enumerate(LANDMARK_ROLES, start=1):
                _, creat = LandmarkRole.objects.update_or_create(
                    slug=slug,
                    defaults={
                        'nom_en': en, 'nom_ca': ca, 'nom_es': es, 'zone': zone,
                        'derivable': deriv, 'derivation_op': op,
                        'derivation_input': inp, 'derivation_tiebreak': tb,
                        'evidence_num': evn, 'evidence_den': evd, 'evidence_ref': evr,
                        'is_system': True, 'pendent_revisio': False,
                        'origen': LandmarkRole.ORIGEN_SEED,
                        'display_order': ordre * 10,
                        'source_ref': '{} §6.1'.format(INF),
                    })
                r['landmark_roles'][0 if creat else 1] += 1

            for gc_role, slug, face, nota in GC_MAP:
                _, creat = GCPieceRoleMap.objects.update_or_create(
                    gc_role=gc_role,
                    defaults={'ftt_slug': slug, 'face': face, 'nota': nota,
                              'source_ref': '{} · {} §5.1'.format(GC, INF)},
                )
                r['gc_map'][0 if creat else 1] += 1

            for ordre, (regla, kind, a, b, cogen, ref) in enumerate(SEAM_PAIRS, start=1):
                # L'ordenacio canonica s'aplica ABANS del lookup, no despres: si nomes la
                # fes `save()`, la segona passada buscaria per l'ordre d'entrada, no el
                # trobaria i crearia un bessó. El punt unic es `ordena()`.
                ca_, cb_ = SeamPairTemplate.ordena(a, b)
                clau = clau_de_mesura(kind, a, b)
                mesura = llegeix_mesura(cens, meta, kind, a, b)
                _, creat = SeamPairTemplate.objects.update_or_create(
                    garment_type_item=None, seam_kind=kind,
                    piece_role_a_slug=ca_[0], face_a=ca_[1], edge_role_a_slug=ca_[2],
                    piece_role_b_slug=cb_[0], face_b=cb_[1], edge_role_b_slug=cb_[2],
                    defaults={
                        'co_generated': cogen,
                        'observed_seams': mesura['seams'] if mesura else None,
                        'observed_patterns': mesura['pats'] if mesura else None,
                        'observed_den': mesura['den'] if mesura else None,
                        'observed_ref': _observed_ref(
                            mesura, clau, conflictes.get(clau, 1)),
                        'is_system': True,
                        # Les xifres son d'un corpus de tercers i els llindars de D3
                        # encara no els ha fixat ningu: aixo es exactament el que
                        # `pendent_revisio` vol dir.
                        'pendent_revisio': True,
                        'origen': SeamPairTemplate.ORIGEN_IMPORT,
                        'display_order': ordre * 10,
                        'source_ref': '{} regla {} {} · {} §4.2'.format(GC, regla, ref, INF),
                    })
                r['seam_pairs'][0 if creat else 1] += 1
    return r


def _dry(model, camp: str, claus: list) -> list:
    existents = set(model.objects.values_list(camp, flat=True))
    nous = [k for k in claus if k not in existents]
    return [len(nous), len(claus) - len(nous)]


class Command(BaseCommand):
    help = ('Sembra el cataleg semantic (EdgeRole, LandmarkRole, SeamPairTemplate) i el '
            'mapa GarmentCode->FTT. Idempotent, mai esborra.')

    def add_arguments(self, parser):
        parser.add_argument('--schema', default='',
                            help='Nomes aquest schema. Per defecte: public i tots els tenants.')
        parser.add_argument('--dry-run', action='store_true',
                            help='Diu que faria i llista el contingut, sense escriure res.')
        parser.add_argument('--sense-corpus', action='store_true',
                            help='No mesura frequencies: deixa els observed_* a NULL.')
        parser.add_argument('--corpus-conninfo', default=CORPUS_CONNINFO_FILE,
                            help='Fitxer conninfo de libpq cap a ftt_corpus (read-only).')
        parser.add_argument('--llista', action='store_true',
                            help='Escriu la llista COMPLETA de files (taula/slug/valors/source_ref).')

    def handle(self, *args, **opts):
        dry = opts['dry_run']

        cens, meta = None, {}
        if opts['sense_corpus']:
            self.stdout.write(self.style.WARNING(
                '  --sense-corpus: els observed_* quedaran a NULL (no a zero).'))
        else:
            try:
                cens, meta = mesura_corpus(opts['corpus_conninfo'])
                self.stdout.write(
                    '  corpus: {} designs · {} parelles de costura censades'.format(
                        meta['n_designs'], meta['n_parelles']))
            except Exception as exc:  # noqa: BLE001 -- volem el motiu a la sortida
                # NO es un error fatal: el vocabulari es pot sembrar sense les xifres.
                # El que seria greu es escriure zeros fent veure que s'ha mesurat.
                self.stdout.write(self.style.ERROR(
                    '  corpus INACCESSIBLE ({}: {}) -- els observed_* quedaran a NULL, '
                    'no a zero.'.format(type(exc).__name__, exc)))

        if opts['llista']:
            self._llista(cens, meta)

        if opts['schema']:
            schemas = [opts['schema']]
        else:
            schemas = list(get_tenant_model().objects.values_list('schema_name', flat=True))

        for sch in schemas:
            r = sembra(sch, cens, meta, dry_run=dry)
            with schema_context(sch):
                totals = {
                    'edge_roles': EdgeRole.objects.count(),
                    'landmark_roles': LandmarkRole.objects.count(),
                    'seam_pairs': SeamPairTemplate.objects.count(),
                    'gc_map': GCPieceRoleMap.objects.count(),
                }
            prefix = '[dry-run] ' if dry else ''
            self.stdout.write('  {}[{}]'.format(prefix, sch))
            for taula, (creats, actualitzats) in r.items():
                self.stdout.write(
                    '      {:<16} creats: {:>3} · actualitzats: {:>3} · total ara: {:>3}'
                    .format(taula, creats, actualitzats, totals[taula]))

        if not dry:
            self.stdout.write(self.style.SUCCESS(
                '\nOK · cataleg semantic sembrat a {} schema/es · {} rols de vora, '
                '{} rols de punt, {} plantilles de costura, {} files de mapa GC.'.format(
                    len(schemas), len(EDGE_ROLES), len(LANDMARK_ROLES),
                    len(SEAM_PAIRS), len(GC_MAP))))

    # -- la llista del dry-run -------------------------------------------------
    def _llista(self, cens, meta):
        w = self.stdout.write
        w('')
        w('## EdgeRole ({} files)'.format(len(EDGE_ROLES)))
        w('| # | slug | zone | kind | mates | needs_piece_role | nom_en | nom_ca | nom_es | source_ref |')
        w('|---|---|---|---|---|---|---|---|---|---|')
        for i, (slug, zone, kind, mates, needs, en, ca, es, ref) in enumerate(EDGE_ROLES, 1):
            w('| {} | `{}` | {} | {} | {} | {} | {} | {} | {} | `{} {}` |'.format(
                i, slug, zone, kind, mates or '--', 'SI' if needs else '', en, ca, es, GC, ref))

        w('')
        w('## LandmarkRole ({} files)'.format(len(LANDMARK_ROLES)))
        w('| # | slug | zone | derivable | op | input | tiebreak | evidencia | nom_en | nom_ca | nom_es |')
        w('|---|---|---|---|---|---|---|---|---|---|---|')
        for i, (slug, zone, d, op, inp, tb, evn, evd, evr, en, ca, es) in \
                enumerate(LANDMARK_ROLES, 1):
            ev = '{}/{}'.format(evn, evd) if evn is not None else 'NO MESURADA'
            w('| {} | `{}` | {} | {} | {} | {} | {} | {} | {} | {} | {} |'.format(
                i, slug, zone, 'SI' if d else 'no', op,
                ' + '.join(inp.values()), tb or '--', ev, en, ca, es))

        w('')
        w('## GCPieceRoleMap ({} files)'.format(len(GC_MAP)))
        w('| # | gc_role | ftt_slug | face | nota |')
        w('|---|---|---|---|---|')
        for i, (gc, slug, face, nota) in enumerate(GC_MAP, 1):
            w('| {} | `{}` | `{}` | {} | {} |'.format(i, gc, slug, face or '--', nota))

        w('')
        w('## SeamPairTemplate ({} files, totes amb garment_type_item=NULL)'.format(
            len(SEAM_PAIRS)))
        w('| # | regla | kind | costat A | costat B | co_gen | seams | patrons | den | % | categories |')
        w('|---|---|---|---|---|---|---:|---:|---:|---:|---|')
        for i, (regla, kind, a, b, cogen, ref) in enumerate(SEAM_PAIRS, 1):
            ca_, cb_ = SeamPairTemplate.ordena(a, b)
            m = llegeix_mesura(cens, meta, kind, a, b)
            pct = ('{:.1f} %'.format(100.0 * m['pats'] / m['den'])
                   if m and m['den'] else ('0 %' if m else '--'))
            fmt = lambda c: '{}{}.{}'.format(c[0], '/' + c[1] if c[1] else '', c[2])
            w('| {} | {} | {} | `{}` | `{}` | {} | {} | {} | {} | {} | {} |'.format(
                i, regla, kind, fmt(ca_), fmt(cb_), 'SI' if cogen else '',
                m['seams'] if m else '--', m['pats'] if m else '--',
                m['den'] if m else '--', pct, m['cats'] if m else '--'))
        # Parelles que el corpus MESURA i que cap plantilla no recull. No son un error:
        # son vocabulari que l'ontologia no nomena, i el lloc on mirar quan F4 trobi una
        # costura que el cataleg no sap dir com es diu.
        if cens:
            cobertes = {clau_de_mesura(k, a, b) for _, k, a, b, _, _ in SEAM_PAIRS}
            orfes = sorted(
                ((c, v) for c, v in cens.items() if c not in cobertes),
                key=lambda x: -x[1]['seams'])
            w('')
            w('## Parelles MESURADES que cap plantilla no recull ({} de {})'.format(
                len(orfes), len(cens)))
            w("Vocabulari que l'ontologia no nomena. No es sembra res: es la llista per a")
            w('la sessio Montse i per a F4.')
            w('')
            w('| kind | costat A | costat B | seams | patrons |')
            w('|---|---|---|---:|---:|')
            for (kind, a, b), v in orfes:
                w('| {} | `{}{}` | `{}{}` | {} | {} |'.format(
                    kind, a[0], '/' + a[1] if a[1] else '',
                    b[0], '/' + b[1] if b[1] else '', v['seams'], v['pats']))

        w('')
        w('## GarmentTypeItemEdgeProfile')
        w('TAULA CREADA, SEMBRA BUIDA a posta: els perfils per GTI concret els ha de mapar')
        w("l'Agus amb la Montse. El vocabulari generic viu a SeamPairTemplate amb")
        w('`garment_type_item=NULL`.')
        w('')
