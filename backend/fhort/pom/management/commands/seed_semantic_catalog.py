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
    EdgeRole, Face, GarmentTypeItemEdgeProfile, GCPieceRoleMap, LandmarkRole,
    SeamPairTemplate, ZonaAnatomica,
)

#: Commit fixat de GarmentCode del qual surt tot el vocabulari. Viatja a cada `source_ref`.
GC = 'GarmentCode@d449629'
#: L'informe que va fer la lectura. Qui dubti d'una fila té dos llocs on anar.
INF = 'REPORT_GCD_ONTOLOGY_2026-08-25.md'
#: 🚨 **La sessió amb la Montse (26/08) és FONT D'AUTORITAT, i per això té constant pròpia.**
#: Tot el que porta aquesta marca al `source_ref` ve d'una patronista dient com se'n diu al
#: taller — no d'una lectura de GarmentCode. Quan les dues fonts diguin coses diferents,
#: aquesta mana: GarmentCode és un generador, i el vocabulari d'ofici és d'ofici.
MONTSE = 'Montse session 2026-08-26'

#: Conninfo de libpq (per paraules clau, una per línia). **No és un `.pgpass`** malgrat
#: el nom: `PGPASSFILE` no se'l menja (vegeu REPORT_GCD_CORPUS_IMPORT_2026-08-26 §3.7).
CORPUS_CONNINFO_FILE = '/root/gcd_corpus/corpus_ro.pgpass'


# ═════════════════════════════════════════════════════════════════════════════
# (a) VOCABULARI — de l'ontologia. Cap xifra d'aquí surt d'una mesura.
# ═════════════════════════════════════════════════════════════════════════════

Z = ZonaAnatomica
K = EdgeRole

#: (slug, zone, kind, mates_slug, needs_piece_role, nom_en, nom_ca, nom_es, source_ref,
#:  nota)  ← la NOTA és opcional i va al `source_ref` de la fila. És on van les lleis
#:  d'ofici de la sessió Montse: no hi ha camp d'estat ni de validació al catàleg, i
#:  inventar-ne un seria un segon vocabulari per a una cosa que `source_ref` ja diu.
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
     'Neckline', 'Escot', 'Escote', 'bodice.py:351; collars.py:12-88', ''),
    ('collar_attach', Z.NECK, K.KIND_SEAM, 'neckline', False,
     'Collar attach', 'Unió de coll', 'Unión de cuello', 'collars.py:169,259; bodice.py:333', ''),
    ('collar_outer_edge', Z.NECK, K.KIND_FINISHED, '', True,
     'Collar outer edge', 'Vora exterior del coll', 'Borde exterior del cuello', 'bands.py:24', ''),
    ('collar_side_seam', Z.NECK, K.KIND_SEAM, 'collar_side_seam', True,
     'Collar side seam', 'Costura lateral del coll', 'Costura lateral del cuello',
     'collars.py:161-163', ''),
    ('hood_attach', Z.NECK, K.KIND_SEAM, 'neckline', False,
     'Hood attach', 'Unió de caputxa', 'Unión de capucha', 'collars.py:324', ''),
    ('hood_centre_seam', Z.NECK, K.KIND_SEAM, 'hood_centre_seam', False,
     'Hood centre seam', 'Costura central de la caputxa', 'Costura central de la capucha',
     'collars.py:323', ''),
    ('strapless_top', Z.TORSO, K.KIND_FINISHED, '', False,
     'Strapless top edge', 'Vora de cos sense tirants', 'Borde de cuerpo sin tirantes',
     'bodice.py:382-383', ''),
    ('shoulder_seam', Z.SHOULDER, K.KIND_SEAM, 'shoulder_seam', False,
     'Shoulder seam', "Costura d'espatlla", 'Costura de hombro',
     'bodice.py:75; bodice.py:211-213', ''),
    # 🚨 LLEI D'OFICI per al matcher (Montse E.P3): **una sisa sense màniga porta vora.**
    # O sigui que en un sense-mànigues s'espera una costura `armhole ↔ facing`, que
    # GarmentCode no pot conèixer —no té `facing`— i que cap plantilla recull encara.
    # **No es crea la plantilla**: `facing` no té rols de vora definits, i inventar-n'hi un
    # per tancar la frase seria vocabulari sense evidència. Va a la llista d'extensió.
    ('armhole', Z.ARM, K.KIND_OPENING, 'sleeve_cap', False,
     'Armhole', 'Sisa', 'Sisa', 'bodice.py:306; sleeves.py:11-105',
     MONTSE + ' · E.P3: una sisa sense màniga porta vora (armhole↔facing en sleeveless); '
              'plantilla PENDENT de definir rols de vora a facing'),
    ('sleeve_cap', Z.ARM, K.KIND_SEAM, 'armhole', False,
     'Sleeve cap', 'Cap de màniga', 'Copa de manga', 'sleeves.py:180,289', ''),
    ('sleeve_underarm_seam', Z.ARM, K.KIND_SEAM, 'sleeve_underarm_seam', True,
     'Sleeve underarm seam', 'Costura de sota-màniga', 'Costura de bajo manga',
     'sleeves.py:281-284', ''),
    ('cuff_line', Z.ANY, K.KIND_SEAM, 'band_attach_upper', True,
     'Cuff line', 'Línia de puny', 'Línea de puño', 'sleeves.py:181,328-331', ''),
    ('centre_front', Z.TORSO, K.KIND_SEAM, 'centre_front', True,
     'Centre front', 'Centre davant', 'Centro delantero', 'bodice.py:74; bodice.py:443-444', ''),
    ('centre_back', Z.TORSO, K.KIND_SEAM, 'centre_back', True,
     'Centre back', 'Centre esquena', 'Centro espalda', 'bodice.py:126; bodice.py:445-446', ''),
    # 🚩 Sense canvi de nom, i amb una nota que val més que un canvi: el **costadillo** de
    # sastreria NO és el `side_seam` (Montse B.15). És un rol de peça de sastreria que el
    # catàleg encara no té, i confondre'ls faria que un patró de sastre s'etiquetés malament
    # amb 200 OK. **No es crea ara**: va a la llista d'extensió del report.
    ('side_seam', Z.TORSO, K.KIND_SEAM, 'side_seam', True,
     'Side seam', 'Costura lateral', 'Costura lateral',
     'bodice.py:73,217; pants.py:115,232',
     MONTSE + ' · B.15: costadillo ≠ side_seam — rol de sastreria FUTUR, no crear ara'),
    ('waistline', Z.WAIST, K.KIND_SEAM, 'band_attach_upper', True,
     'Waistline', 'Línia de cintura', 'Línea de cintura',
     'meta_garment.py:75; skirt_paneled.py:45', ''),
    ('band_attach_upper', Z.WAIST, K.KIND_SEAM, 'waistline', True,
     'Band upper attach', 'Unió superior de banda', 'Unión superior de banda', 'bands.py:19', ''),
    ('band_attach_lower', Z.WAIST, K.KIND_SEAM, 'waistline', True,
     'Band lower attach', 'Unió inferior de banda', 'Unión inferior de banda', 'bands.py:24', ''),
    ('band_side_seam', Z.WAIST, K.KIND_SEAM, 'band_side_seam', True,
     'Band side seam', 'Costura lateral de banda', 'Costura lateral de banda',
     'bands.py:74-75', ''),
    ('inseam', Z.LEG, K.KIND_SEAM, 'inseam', True,
     'Inseam', 'Entrecuix', 'Entrepierna', 'pants.py:120,233', ''),
    ('crotch_seam', Z.LEG, K.KIND_SEAM, 'crotch_seam', False,
     'Crotch seam', 'Costura de tir', 'Costura de tiro', 'pants.py:119,289-290', ''),
    ('hem', Z.ANY, K.KIND_FINISHED, '', True,
     'Hem', 'Baix', 'Bajo', 'skirt_paneled.py:49; pants.py:121', ''),
    ('gore_seam', Z.ANY, K.KIND_SEAM, 'gore_seam', True,
     'Gore seam', 'Costura de gaia', 'Costura de nesga', 'skirt_paneled.py:497-501', ''),
    # `nom_es` corregit per la Montse (B.24): al taller no se'n diu «brazo».
    ('dart_leg', Z.ANY, K.KIND_INTERNAL, 'dart_leg', False,
     'Dart leg', 'Braç de pinça', 'Largo de pinza', 'panel.py:238; edge_factory.py:313',
     MONTSE + ' · B.24 (nom_es)'),
    # ── ESTRUCTURALS (informe §2.4, últim paràgraf) ──────────────────────────────
    ('godet_insert_seam', Z.ANY, K.KIND_STRUCTURAL, 'slit_edge', False,
     'Godet insert seam', "Costura d'inserció de godet", 'Costura de inserción de godet',
     'godet.py:113-114', ''),
    ('level_join_seam', Z.ANY, K.KIND_STRUCTURAL, 'level_join_seam', False,
     'Level join seam', "Costura d'unió de nivells", 'Costura de unión de niveles',
     'skirt_levels.py:62-64', ''),
    ('slit_edge', Z.ANY, K.KIND_STRUCTURAL, '', True,
     'Slit edge', "Vora d'obertura", 'Borde de abertura',
     'skirt_paneled.py:192,218; circle_skirt.py:216; edge_factory.py:292', ''),

    # ── SESSIÓ MONTSE 26/08 · el slug que faltava ────────────────────────────
    # 🚩 F3 va deixar DUES parelles del cens sense nom («centre · collar/back ↔
    # collar/back» amb 16.296 costures i la seva bessona del davant amb 7.077) i no se'n va
    # inventar cap slug: §2.4 té el costat del coll i la vora exterior, però **no el
    # centre**. La Montse el bateja (B.ORF1/2) i amb ell les dues òrfenes deixen d'existir.
    #
    # `mates_slug` a si mateix és com el catàleg diu «es cus amb ella mateixa» —el mateix
    # que ja fan `shoulder_seam`, `centre_front` o `gore_seam`. **No hi ha camp
    # `symmetric`**, i afegir-ne un seria un segon vocabulari per a una cosa que
    # l'autoreferència ja diu.
    #
    # La zona és `neck` i no `collar`: el vocabulari de zones és TANCAT
    # (neck|shoulder|arm|torso|waist|leg|any) i un coll seu al coll.
    ('collar_centre_seam', Z.NECK, K.KIND_SEAM, 'collar_centre_seam', True,
     'Collar centre seam', 'Costura del centre del coll', 'Costura centro cuello',
     'sense evidència a GarmentCode: §2.4 no el nomena', MONTSE + ' · B.ORF1/2'),
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
#: La llei d'ofici, en anglès perquè és contracte i viatja al `source_ref` de la fila.
LLEI_ESCOT = (
    'neckline+shoulder_seam are evaluated on the piece that CARRIES THE NECKLINE — '
    'front/back OR YOKE; FTT extension, GarmentCode has no yoke'
)

#: 🚨 **LLEI D'OFICI (Agus, 26/08): l'escot i l'espatlla s'avaluen sobre LA PEÇA QUE PORTA
#: L'ESCOT, que no sempre és el davant o l'esquena — pot ser el CANESÚ (`yoke`).** Aquesta
#: és una extensió d'FTT i no una lectura de GarmentCode: **GarmentCode no té canesú**
#: (informe §5.1: `yoke` és un dels 22 slugs que no pot produir), o sigui que el
#: 2.371/2.371 està mesurat sobre un món on la peça de l'escot és sempre el tors. Als
#: patrons de casa no ho és: el TATE en porta un (`TATE_FRONT_YOKE`).
#:
#: Per això `hps` porta ara `derivation_tiebreak='highest_y'`: **un verificador de
#: sanitat**, no un desempat de veritat. `shared_endpoint` ja exigeix un únic extrem comú;
#: si en surt un que NO és el més alt de la peça, alguna cosa no és el que dèiem —una vora
#: mal etiquetada, una peça girada al plànol— i val més que canti que no pas que passi.
LANDMARK_ROLES = [
    ('hps', Z.SHOULDER, True, LandmarkRole.OP_SHARED_ENDPOINT,
     {'a': 'neckline', 'b': 'shoulder_seam'}, 'highest_y', 2371, 2371,
     'n2_gym/out/hps_pont.txt · pont escot↔sisa = 1 vora en 2371 de 2371',
     'High point shoulder', "Punt alt d'espatlla", 'Punto alto de hombro', LLEI_ESCOT),
    ('shoulder_point', Z.SHOULDER, True, LandmarkRole.OP_SHARED_ENDPOINT,
     {'a': 'shoulder_seam', 'b': 'armhole'}, '', 2371, 2371,
     'n2_gym/out/hps_pont.txt · mateix pont, extrem oposat',
     'Shoulder point', "Punt d'espatlla", 'Punto de hombro', LLEI_ESCOT),
    ('underarm_point', Z.ARM, True, LandmarkRole.OP_FAR_ENDPOINT,
     {'a': 'armhole'}, 'lowest_y', None, None, '',
     'Underarm point', 'Punt de sota-braç', 'Punto de axila', ''),
    ('neck_centre_point', Z.NECK, True, LandmarkRole.OP_FAR_ENDPOINT,
     {'a': 'neckline'}, 'away_from:hps', None, None, '',
     'Neck centre point', "Punt central d'escot", 'Punto central de escote', ''),
    ('waist_side_point', Z.WAIST, True, LandmarkRole.OP_SHARED_ENDPOINT,
     {'a': 'side_seam', 'b': 'waistline'}, '', None, None, '',
     'Waist side point', 'Punt de cintura al costat', 'Punto de cintura en el costado', ''),
    ('hem_side_point', Z.ANY, True, LandmarkRole.OP_SHARED_ENDPOINT,
     {'a': 'side_seam', 'b': 'hem'}, '', None, None, '',
     'Hem side point', 'Punt de baix al costat', 'Punto de bajo en el costado', ''),
    ('crotch_point', Z.LEG, True, LandmarkRole.OP_SHARED_ENDPOINT,
     {'a': 'inseam', 'b': 'crotch_seam'}, '', None, None, '',
     'Crotch point', 'Punt de tir', 'Punto de tiro', ''),
    ('underarm_seam_point', Z.ARM, True, LandmarkRole.OP_SHARED_ENDPOINT,
     {'a': 'sleeve_cap', 'b': 'sleeve_underarm_seam'}, '', None, None, '',
     'Underarm seam point', 'Punt de sota-màniga', 'Punto de bajo manga', ''),

    # ═══════════════════════════════════════════════════════════════════════
    # SESSIÓ MONTSE 26/08 · C.09 — els NOU punts que el vocabulari no tenia
    # ═══════════════════════════════════════════════════════════════════════
    # Els noms `ca` són literalment els seus. Els vuit d'abans surten d'una lectura de
    # GarmentCode; aquests surten d'una patronista dient com se'n diu al taller, i per això
    # van amb `pendent_revisio=False`: **paraula d'ofici directa, no proposta**.
    #
    # 🚨 **Només UN dels nou és derivable, i és el que ho és de debò.** La temptació era
    # encadenar-los —«el punt de pit surt del de pinça»— i el brief ho prohibeix
    # explícitament: *NO assumir*. Un punt marcat com a derivable que després no es pugui
    # calcular és pitjor que un de manual, perquè F4 el buscarà i no el trobarà mai.
    #
    # 🚩 **`BodyMeasurementISO` és BUIDA** (0 files, comprovat 27/08), o sigui que
    # l'enllaç «a la mesura ISO corresponent» que el brief demanava per als corporals **no
    # existeix per a cap dels sis**. Queda dit a la nota de cada fila i no s'hi inventa cap
    # codi: un `codi_iso` fals seria pitjor que cap.

    #: L'ÚNIC derivable dels nou: l'àpex de la pinça és on es toquen els dos braços.
    ('dart_point', Z.ANY, True, LandmarkRole.OP_SHARED_ENDPOINT,
     {'a': 'dart_leg', 'b': 'dart_leg'}, '', None, None, '',
     'Dart point', 'Punt de pinça', 'Punto de pinza',
     MONTSE + ' · C.09 «punt de pinça (o de plec)» · àpex = juntura dels dos braços'),

    #: 🚩 Derivació BUIDA a posta. Passa pel punt de pinça en molts patrons, però **no
    #: sempre**: un davant sense pinça té punt de pit igualment, i un patró amb dues
    #: pinces en té un de sol. Marcar-lo derivable seria una promesa que no es pot complir.
    ('bust_point', Z.TORSO, False, LandmarkRole.OP_MANUAL, {}, '', None, None, '',
     'Bust point', 'Punt de pit', 'Punto de pecho',
     MONTSE + ' · C.09 · derivació NO assumida: pot coincidir amb dart_point però no '
              'sempre (un davant sense pinça en té igualment)'),

    #: Els SIS corporals. Es marquen o es mesuren sobre el cos; del patró no surten.
    ('hip_point', Z.WAIST, False, LandmarkRole.OP_MANUAL, {}, '', None, None, '',
     'Hip point', 'Punt de cadera', 'Punto de cadera',
     MONTSE + ' · C.09 · corporal; sense mesura ISO al catàleg (taula buida 27/08)'),
    ('knee_point', Z.LEG, False, LandmarkRole.OP_MANUAL, {}, '', None, None, '',
     'Knee point', 'Punt de genoll', 'Punto de rodilla',
     MONTSE + ' · C.09 · corporal; sense mesura ISO al catàleg (taula buida 27/08)'),
    ('elbow_point', Z.ARM, False, LandmarkRole.OP_MANUAL, {}, '', None, None, '',
     'Elbow point', 'Punt de colze', 'Punto de codo',
     MONTSE + ' · C.09 · corporal; sense mesura ISO al catàleg (taula buida 27/08)'),
    ('calf_point', Z.LEG, False, LandmarkRole.OP_MANUAL, {}, '', None, None, '',
     'Calf point', 'Punt de bessó', 'Punto de gemelo',
     MONTSE + ' · C.09 «punt de bessó (calf)» · corporal; sense mesura ISO (taula buida)'),
    ('biceps_point', Z.ARM, False, LandmarkRole.OP_MANUAL, {}, '', None, None, '',
     'Biceps point', 'Punt de bíceps', 'Punto de bíceps',
     MONTSE + ' · C.09 «punt biceps» · corporal; sense mesura ISO (taula buida)'),
    ('ankle_point', Z.LEG, False, LandmarkRole.OP_MANUAL, {}, '', None, None, '',
     'Ankle point', 'Punt de turmell', 'Punto de tobillo',
     MONTSE + ' · C.09 · corporal; sense mesura ISO al catàleg (taula buida 27/08)'),

    #: No és corporal ni derivable v1: és un punt de CONSTRUCCIÓ sobre la línia de puny, i
    #: qui el sabrà calcular és F4.2, quan els trams portin rol de vora.
    ('cuff_point', Z.ANY, False, LandmarkRole.OP_MANUAL, {}, '', None, None, '',
     'Cuff point', 'Punt de puny', 'Punto de puño',
     MONTSE + ' · C.09 · punt de construcció sobre `cuff_line`; derivable quan els trams '
              'portin rol de vora (F4.2)'),
]

#: El mapa GarmentCode→FTT (informe §5.1 + `scripts/mapping.py`), amb els cinc forats
#: tancats pels tres slugs de D6. **24 rols de GarmentCode → 11 slugs d'FTT × cara.**
#:
#: 🚨 **VUIT dels 24 rols cauen sobre `cuff`**: quatre conceptes (puny de màniga, puny de
#: màniga acampanat, puny de cama, puny de cama acampanat) × dues cares que l'eix `face`
#: absorbeix, o sigui vuit rols a dos destins. **La col·lisió és volguda** —l'acampanament
#: és un eix de variant, no una peça diferent— però vol dir que UNA plantilla de costura
#: d'FTT pot recollir més d'una parella del corpus, i per això les freqüències s'agreguen
#: a la BD del corpus i no sumant a mà.
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

# ═════════════════════════════════════════════════════════════════════════════
# E · ELS TRES PERFILS GTI PILOT (sessió Montse, E.P1-P3)
# ═════════════════════════════════════════════════════════════════════════════
#: 🚨 **La Montse va respondre a nivell de PRENDA i la taula és per PEÇA.**
#: «Una brusa porta escot» és cert; `GarmentTypeItemEdgeProfile` vol saber *quina peça* el
#: porta, perquè sense això la fila no es pot llegir (és la primera frase del docstring del
#: model: *un garment no té escot, el té el seu coll o el seu davant*). El pont l'he fet jo
#: i **cada fila diu si és unívoca o proposada**, perquè es pugui ratificar o corregir
#: d'una ullada en comptes de creure-se-la.
#:
#: L'origen de cada assignació, per ordre de força:
#:   `catàleg`  — les plantilles de costura només la col·loquen en aquesta peça
#:   `definició`— la vora ÉS d'aquella peça per definició (una vora exterior de coll)
#:   `ofici`    — el catàleg diu una altra cosa perquè GarmentCode parteix les peces
#:                d'una altra manera (el baix d'una brusa és al cos, no a cap faldilla)
#:
#: 🚩 **`presence` és NOT NULL i no hi ha cap mesura per GTI.** El que hi ha és el judici
#: de la Montse: aquestes vores pertanyen a aquesta peça. Per això `observed_*` van a NULL
#: —no s'ha mesurat res— i el grau surt d'una lectura meva que s'ha de ratificar: `core`
#: quan la vora hi és sempre, `rare` quan és una ALTERNATIVA a una altra de la mateixa
#: llista (una brusa amb escot sense tirants no té escot, i al revés) o una opció de
#: disseny. **El 75/30 de D.01 no s'hi aplica: és per a graus MESURATS.**

#: 🚨 **La clau és el `code`, MAI la pk** (llei G9). Aquest seed corre als TRES esquemes,
#: i les pks de `tasks_garmenttypeitem` són locals de cada tenant: sembrar per id voldria
#: dir que el dia que `los` creï el seu GTI número 5, li enganxaríem un perfil de «Blusa»
#: en silenci. Avui no xocaria —`los` en té un de sol i no és cap dels tres— però la
#: bomba quedaria armada. Els codes són únics dins de cada tenant (comprovat) i no
#: viatgen entre esquemes.
#:
#: (gti_code, etiqueta, [(piece_role, face, edge_role, presence, origen_assignacio)])
GTI_PROFILES = [
    ('blouse', 'E.P1 · Blusa (Buttoned Tops)', [
        ('front', Face.FRONT, 'neckline', 'core', 'catàleg'),
        ('back', Face.BACK, 'neckline', 'core', 'catàleg'),
        ('collar', Face.CAP, 'collar_outer_edge', 'core', 'definició'),
        ('front', Face.FRONT, 'strapless_top', 'rare', 'ofici · alternativa a neckline'),
        ('sleeve', Face.FRONT, 'cuff_line', 'core', 'catàleg'),
        ('sleeve', Face.BACK, 'cuff_line', 'core', 'catàleg'),
        ('front', Face.FRONT, 'centre_front', 'core', 'catàleg'),
        ('front', Face.FRONT, 'hem', 'core', 'ofici · el baix d\'una brusa és al cos'),
        ('back', Face.BACK, 'hem', 'core', 'ofici · el baix d\'una brusa és al cos'),
        ('front', Face.FRONT, 'slit_edge', 'rare', 'ofici · opció de disseny'),
    ]),
    ('trousers', 'E.P2 · Pantaló estructurat (Tailored & Rigid Pants)', [
        ('pant', Face.FRONT, 'waistline', 'core', 'catàleg'),
        ('pant', Face.BACK, 'waistline', 'core', 'catàleg'),
        ('pant', Face.FRONT, 'hem', 'core', 'ofici · el baix d\'un pantaló és a la cama'),
        ('pant', Face.BACK, 'hem', 'core', 'ofici · el baix d\'un pantaló és a la cama'),
        ('pant', Face.FRONT, 'slit_edge', 'rare', 'ofici · opció de disseny'),
    ]),
    ('dress_simple', 'E.P3 · Vestit pla simple (Dresses)', [
        ('front', Face.FRONT, 'neckline', 'core', 'catàleg'),
        ('back', Face.BACK, 'neckline', 'core', 'catàleg'),
        ('front', Face.FRONT, 'strapless_top', 'rare', 'ofici · alternativa a neckline'),
        ('front', Face.FRONT, 'hem', 'core', 'ofici · un vestit pla es talla sencer'),
        ('back', Face.BACK, 'hem', 'core', 'ofici · un vestit pla es talla sencer'),
    ]),
]

#: El vocabulari que la Montse troba A FALTAR i que **NO es crea** (E.P2.falten,
#: E.P3.falten). Decidir un slug és decidir un contracte, i això és de l'Agus. Va al report.
EXTENSIONS_PENDENTS = [
    ('pocket_flap_edge', 'Tapeta de butxaca', 'E.P2.falten'),
    ('pocket_opening', 'Obertura de butxaca', 'E.P2.falten'),
    ('zip_placket_edge', 'Tapeta cremallera', 'E.P2.falten'),
    ('side_opening', 'Obertures laterals', 'E.P3.falten'),
    ('placket_edge', 'Tapeta (vora)', 'E.P3.falten'),
    ('cuff_edge', 'Punys (vora)', 'E.P3.falten'),
    ('skirt_hem', 'Baix de faldilla', 'E.P3.falten · potser ja és `hem` + peça `skirt`'),
    ('costadillo', 'Costadillo (rol de PEÇA, no de vora)', 'B.15 · sastreria'),
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
    # ── SESSIÓ MONTSE 26/08 · les dues òrfenes del cens, batejades ───────────
    # F3 les va deixar fora a posta perquè no hi havia slug per al centre del coll. Ara
    # n'hi ha (B.ORF1/2) i el cens es tanca: de 51 parelles mesurades, 0 sense plantilla.
    ('Montse B.ORF1', S.KIND_CENTRE, ('collar', Face.BACK, 'collar_centre_seam'),
     ('collar', Face.BACK, 'collar_centre_seam'), False, 'sense regla a §4.2'),
    ('Montse B.ORF2', S.KIND_CENTRE, ('collar', Face.FRONT, 'collar_centre_seam'),
     ('collar', Face.FRONT, 'collar_centre_seam'), False, 'sense regla a §4.2'),
]

#: 🚨 **LLEIS D'OFICI de la sessió Montse, per plantilla.** Van al `source_ref` de la fila:
#: expliquen per què la plantilla ÉS com és, que és el que `source_ref` vol dir.
#: `{clau_de_mesura: text}`.
#:
#: 🔑 **D.02 · el cap de màniga bascula endavant.** La plantilla creuada
#: `back.armhole ↔ sleeve/front.sleeve_cap` va sortir a ZERO mesurat, i el zero no és un
#: buit de dades: la meitat del DARRERE de la màniga cus contra la sisa del DAVANT perquè
#: el cap bascula cap endavant, i **el mirall invers no s'espera mai**. Era la resposta
#: correcta i ara diu per què.
#:
#: 🚩 **L'ALTRA fila de zero mesurat NO porta aquesta llei, i és a posta.**
#: `cuff/back.band_attach_upper ↔ pant/front.cuff_line` també surt a zero, però el brief
#: descrivia D.02 com «cap de màniga creuant espatlla» — i un puny de CAMA no té cap ni
#: espatlla. Aplicar-hi la mateixa frase seria posar una explicació de màniga a un pantaló i
#: deixar-la escrita per sempre amb el nom de la Montse a sota. **Queda sense lectura
#: d'ofici i va a la llista de preguntes del report.**
LLEIS_DE_PLANTILLA = {
    ('union', ('back', 'back'), ('sleeve', 'front')):
        MONTSE + " · D.02 LLEI d'ofici: el cap de màniga bascula endavant; el mirall "
                 "invers NO s'espera",
}

#: 🔑 **D.03 · la lectura de la Montse sobre les pinces, literal.** Va a `observed_ref` de
#: TOTES les files de pinça i no a `source_ref` perquè el que matisa és la XIFRA: que el
#: 52 % dels patrons del corpus portin pinça al darrere i cap al davant no és una llei
#: d'ofici, i ella ho diu amb totes les lletres —**«no hi ha un perquè»**. Sense aquesta
#: nota, algú llegiria el 52 % com una regla.
#:
#: Es transcriu SENCERA i sense retocar. Una cita atribuïda que s'escurça deixa de ser-ho.
CITA_D03 = (
    MONTSE + ' · D.03 (literal): «No hi ha un perquè, va en funció del disseny i del '
             'volum que es vol donar a una prenda. Tanmateix, les pinces habitualment es '
             'fan a darrera per ajustar la forma del cul. Per tant el que has trobat '
             "s'ajusta al què és normal.»"
)

# ═════════════════════════════════════════════════════════════════════════════
# D.01 · ELS LLINDARS DE GRAU
# ═════════════════════════════════════════════════════════════════════════════
#: 🚨 **Els llindars de la Montse (D.01): core ≥ 75 % · common ≥ 30 % · la resta, rara.**
#: Substitueixen els 90/25 del precedent, que eren una proposta sense ofici a sota.
PRESENCE_CORE_PCT = 75
PRESENCE_COMMON_PCT = 30

#: 🚩 **`SeamPairTemplate` NO té columna de grau.** El brief demanava «recalcular el grade
#: de TOTES les plantilles», i l'únic lloc del catàleg amb `presence` és
#: `GarmentTypeItemEdgeProfile`. Afegir-ne una columna hauria estat una migració que el
#: brief deia que no s'esperava, i deixar-ho córrer hauria perdut la decisió.
#: **El grau es CALCULA i s'escriu dins d'`observed_ref`**: queda visible, queda auditable,
#: i el dia que faci falta com a columna, la llei ja és aquí i el valor es pot migrar.
def grau_de(patrons, den) -> str:
    """`core` | `common` | `rare` segons els llindars de la Montse. → etiqueta llegible."""
    if not den or patrons is None:
        return ''
    pct = 100.0 * patrons / den
    if pct >= PRESENCE_CORE_PCT:
        grau = 'core'
    elif pct >= PRESENCE_COMMON_PCT:
        grau = 'common'
    else:
        grau = 'rare'
    return 'grau={} ({:.1f} % · llindars {}/{} de {} D.01)'.format(
        grau, pct, PRESENCE_CORE_PCT, PRESENCE_COMMON_PCT, MONTSE)


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

def _observed_ref(mesura, clau, conflictes, llei: str = '') -> str:
    """La frase que acompanya cada xifra. Sense aixo, un percentatge menteix sol.

    `llei` és la lectura d'ofici de la Montse quan n'hi ha: la xifra diu QUÈ passa i la
    llei diu PER QUÈ. Un zero sense el seu perquè es llegeix com una dada que falta.
    """
    if mesura is None:
        return llei
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
    grau = grau_de(mesura['patterns'] if 'patterns' in mesura else mesura['pats'],
                   mesura['den'])
    if grau:
        parts.append(grau)
    if llei:
        parts.append(llei)
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
         'seam_pairs': [0, 0], 'gc_map': [0, 0], 'gti_profiles': [0, 0]}

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
            r['gti_profiles'] = _dry_gti()
            return r

        with transaction.atomic():
            for ordre, (slug, zone, kind, mates, needs, en, ca, es, ref, nota) in \
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
                        'source_ref': '{} {} · {} §2.4{}'.format(
                            GC, ref, INF, ' · ' + nota if nota else ''),
                    })
                r['edge_roles'][0 if creat else 1] += 1

            for ordre, (slug, zone, deriv, op, inp, tb, evn, evd, evr, en, ca, es, llei) in \
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
                        # C1 · la sessió Montse repassa les vuit regles. Les dues que
                        # portaven mesura les CONFIRMA; les sis que no en portaven cap les
                        # VALIDA — que és una cosa diferent i val la pena que la fila ho
                        # digui: una regla validada per ofici i una regla mesurada sobre
                        # 2.371 patrons no tenen el mateix pes, i el dia que una falli
                        # convé saber de quina de les dues es fiava el sistema.
                        #
                        # Es deriva de l'evidència i no s'escriu a mà una llista de sis:
                        # una llista a mà caduca la primera vegada que algú mesuri'n una.
                        'source_ref': '{} §6.1{} · {}'.format(
                            INF, ' · ' + llei if llei else '',
                            MONTSE + (' · C.01-02 confirmada' if evn is not None
                                      else ' · C.03-08 validada')),
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
                            mesura, clau, conflictes.get(clau, 1),
                            CITA_D03 if kind == S.KIND_DART else ''),
                        'is_system': True,
                        # Les xifres son d'un corpus de tercers i els llindars de D3
                        # encara no els ha fixat ningu: aixo es exactament el que
                        # `pendent_revisio` vol dir.
                        'pendent_revisio': True,
                        'origen': SeamPairTemplate.ORIGEN_IMPORT,
                        'display_order': ordre * 10,
                        'source_ref': '{} regla {} {} · {} §4.2{}'.format(
                            GC, regla, ref, INF,
                            ' · ' + LLEIS_DE_PLANTILLA[clau]
                            if clau in LLEIS_DE_PLANTILLA else ''),
                    })
                r['seam_pairs'][0 if creat else 1] += 1

            # ── E · els perfils GTI pilot ────────────────────────────────────
            # 🚨 **Es SALTEN els GTI que no existeixen en aquest schema**, i no és
            # tolerància: els tres pilots són ids del tenant `fhort`, i `public` i `los`
            # no tenen per què tenir-los. Petar-hi seria fer que la sembra d'un catàleg
            # compartit depengués de les dades d'UN tenant.
            gtis = _gtis_del_schema() or {}
            for code, _etiqueta, files in GTI_PROFILES:
                gti_id = gtis.get(code)
                if gti_id is None:
                    continue
                for ordre, (peca, cara, vora, presencia, origen) in enumerate(files, 1):
                    _, creat = GarmentTypeItemEdgeProfile.objects.update_or_create(
                        garment_type_item_id=gti_id, piece_role_slug=peca,
                        face=cara, edge_role_slug=vora,
                        defaults={
                            'presence': presencia,
                            # NULL i no zero: no s'ha mesurat res per GTI. Un zero diria
                            # «mesurat i no hi és», que és el contrari del que passa.
                            'observed_n': None, 'observed_den': None,
                            'observed_ref': MONTSE + ' · judici d\'ofici, NO mesurat · '
                                            'assignació de peça: ' + origen,
                            'is_system': True,
                            'pendent_revisio': True,
                            'origen': GarmentTypeItemEdgeProfile.ORIGEN_MANUAL,
                            'display_order': ordre * 10,
                            'source_ref': MONTSE + ' · E.P1-P3',
                        })
                    r['gti_profiles'][0 if creat else 1] += 1
    return r


def _gtis_del_schema() -> dict | None:
    """`{code: pk}` dels GTI d'aquest schema, o `None` si aquí no n'hi pot haver.

    🚨 **`public` NO té `tasks_garmenttypeitem` i no en tindrà mai**: `tasks` és
    tenant-only i `pom` viu a SHARED *i* a TENANT. És la mateixa llei que va obligar a
    `db_constraint=False` a les dues FK (F3 §1.3), vista des de l'altra banda: allà petava
    la migració, aquí peta la consulta.

    Es comprova mirant si la TAULA hi és, no si l'schema es diu `public`: el dia que hi
    hagi un segon schema compartit, un `if schema == 'public'` seria una bomba de rellotgeria.
    """
    from django.db import connection

    from fhort.tasks.models import GarmentTypeItem

    taula = GarmentTypeItem._meta.db_table
    with connection.cursor() as cur:
        if taula not in connection.introspection.table_names(cur):
            return None
    return dict(GarmentTypeItem.objects.values_list('code', 'pk'))


def _dry_gti() -> list:
    """Quantes files de perfil GTI es crearien en aquest schema, i quantes ja hi són."""
    gtis = _gtis_del_schema()
    if gtis is None:
        return [0, 0]
    existents = {
        (p.garment_type_item_id, p.piece_role_slug, p.face, p.edge_role_slug)
        for p in GarmentTypeItemEdgeProfile.objects.all()
    }
    nous = vells = 0
    for code, _e, files in GTI_PROFILES:
        gti_id = gtis.get(code)
        if gti_id is None:
            continue
        for peca, cara, vora, _p, _o in files:
            if (gti_id, peca, str(cara), vora) in existents:
                vells += 1
            else:
                nous += 1
    return [nous, vells]


def guarda_tancament(schema: str) -> list:
    """El catàleg ha de TANCAR sobre si mateix. -> llista de forats, buida si tot va bé.

    🚨 Existeix perquè el forat va passar de debò (F3, 26/08): el mapa GC→FTT es va sembrar
    apuntant a `pant`, `hood` i `godet_insert`, i **aquells tres slugs no eren a staging** —
    el seed de `PatternPieceRole` s'havia EDITAT i mai EXECUTAT. Cap `check`, cap test i cap
    migració no ho veien: els tests sembren els rols al `setUp`, o sigui que a la suite el
    catàleg tancava i a la BD viva no.

    **Un recompte de guarda que només es fa el dia de la sembra no és un guard, és un
    record.** Aquest es corre sol a cada passada i crida fort si troba un slug mort.
    """
    from fhort.pom.models import PatternPieceRole

    forats = []
    with schema_context(schema):
        peces = set(PatternPieceRole.objects.values_list('slug', flat=True))
        vores = set(EdgeRole.objects.values_list('slug', flat=True))
        for m in GCPieceRoleMap.objects.all():
            if m.ftt_slug not in peces:
                forats.append('gc_map «{}» -> rol de peça «{}» NO EXISTEIX'.format(
                    m.gc_role, m.ftt_slug))
        for t in SeamPairTemplate.objects.all():
            for slug in (t.piece_role_a_slug, t.piece_role_b_slug):
                if slug not in peces:
                    forats.append('plantilla «{}» -> rol de peça «{}» NO EXISTEIX'.format(
                        t, slug))
            for slug in (t.edge_role_a_slug, t.edge_role_b_slug):
                if slug not in vores:
                    forats.append('plantilla «{}» -> rol de vora «{}» NO EXISTEIX'.format(
                        t, slug))
        for r in EdgeRole.objects.exclude(mates_slug=''):
            if r.mates_slug not in vores:
                forats.append('vora «{}» -> mates «{}» NO EXISTEIX'.format(
                    r.slug, r.mates_slug))
        for l in LandmarkRole.objects.all():
            for operand in l.derivation_input.values():
                if operand not in vores:
                    forats.append('punt «{}» -> opera sobre la vora «{}», que NO EXISTEIX'
                                  .format(l.slug, operand))
    return forats


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

        if opts['schema']:
            schemas = [opts['schema']]
        else:
            schemas = list(get_tenant_model().objects.values_list('schema_name', flat=True))

        if opts['llista']:
            self._llista(cens, meta, schemas)

        for sch in schemas:
            r = sembra(sch, cens, meta, dry_run=dry)
            with schema_context(sch):
                totals = {
                    'edge_roles': EdgeRole.objects.count(),
                    'landmark_roles': LandmarkRole.objects.count(),
                    'seam_pairs': SeamPairTemplate.objects.count(),
                    'gc_map': GCPieceRoleMap.objects.count(),
                    'gti_profiles': (GarmentTypeItemEdgeProfile.objects.count()
                                     if _gtis_del_schema() is not None else 0),
                }
            prefix = '[dry-run] ' if dry else ''
            self.stdout.write('  {}[{}]'.format(prefix, sch))
            for taula, (creats, actualitzats) in r.items():
                self.stdout.write(
                    '      {:<16} creats: {:>3} · actualitzats: {:>3} · total ara: {:>3}'
                    .format(taula, creats, actualitzats, totals[taula]))

        if not dry:
            # El recompte de guarda, cada passada i no només el dia de la sembra.
            forats = []
            for sch in schemas:
                forats += ['[{}] {}'.format(sch, f) for f in guarda_tancament(sch)]
            if forats:
                self.stdout.write(self.style.ERROR(
                    '\nCATALEG OBERT: {} referencia/es morta/es. La sembra ha escrit, '
                    'pero el cataleg NO tanca sobre si mateix.'.format(len(forats))))
                for f in forats[:20]:
                    self.stdout.write(self.style.ERROR('      ' + f))
                if len(forats) > 20:
                    self.stdout.write(self.style.ERROR(
                        '      ... i {} mes'.format(len(forats) - 20)))
                self.stdout.write(self.style.WARNING(
                    '  Probablement falta: python manage.py seed_pattern_piece_roles'))
                return

        if not dry:
            self.stdout.write(self.style.SUCCESS(
                '\nOK · cataleg semantic sembrat a {} schema/es · {} rols de vora, '
                '{} rols de punt, {} plantilles de costura, {} files de mapa GC.'.format(
                    len(schemas), len(EDGE_ROLES), len(LANDMARK_ROLES),
                    len(SEAM_PAIRS), len(GC_MAP))))

    # -- la llista del dry-run -------------------------------------------------
    def _llista(self, cens, meta, schemas):
        w = self.stdout.write
        w('')
        w('## EdgeRole ({} files)'.format(len(EDGE_ROLES)))
        w('| # | slug | zone | kind | mates | needs_piece_role | nom_en | nom_ca | nom_es | source_ref |')
        w('|---|---|---|---|---|---|---|---|---|---|')
        for i, (slug, zone, kind, mates, needs, en, ca, es, ref, _n) in enumerate(EDGE_ROLES, 1):
            w('| {} | `{}` | {} | {} | {} | {} | {} | {} | {} | `{} {}` |'.format(
                i, slug, zone, kind, mates or '--', 'SI' if needs else '', en, ca, es, GC, ref))

        w('')
        w('## LandmarkRole ({} files)'.format(len(LANDMARK_ROLES)))
        w('| # | slug | zone | derivable | op | input | tiebreak | evidencia | nom_en | nom_ca | nom_es |')
        w('|---|---|---|---|---|---|---|---|---|---|---|')
        for i, (slug, zone, d, op, inp, tb, evn, evd, evr, en, ca, es, _llei) in \
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

        # ── E · els perfils GTI pilot ────────────────────────────────────
        # 🚨 Els GTI es resolen DINS d'un schema de tenant. La llista es dibuixa una sola
        # vegada, fora del bucle de sembra, i sense això corria al schema per defecte
        # —`public`, que no té la taula— i deia «NO EXISTEIX» de tots tres.
        gtis, schema_gti = {}, ''
        for sch in schemas:
            with schema_context(sch):
                trobats = _gtis_del_schema()
            if trobats:
                gtis, schema_gti = trobats, sch
                break
        w('')
        w('## GarmentTypeItemEdgeProfile — els 3 pilots de la Montse ({} files)'.format(
            sum(len(f) for _, _, f in GTI_PROFILES)))
        w('')
        w('_GTI resolts contra l\'schema `{}`._'.format(schema_gti or 'cap'))
        w('')
        w('🚨 **La Montse va respondre per PRENDA i la taula és per PEÇA.** El pont el fa')
        w("aquesta llista i cada fila diu d'on surt l'assignació: `catàleg` (les plantilles")
        w('nomes la col·loquen alla), `definicio` (la vora ES d\'aquella peca) o `ofici`')
        w('(el cataleg diu una altra cosa perque GarmentCode parteix les peces d\'una')
        w('altra manera). **Les marcades `ofici` son la lectura que cal ratificar.**')
        w('')
        w('`presence` surt del seu judici i NO d\'una mesura: `observed_*` van a NULL i')
        w('els llindars 75/30 de D.01 no s\'hi apliquen (son per a graus MESURATS).')
        for code, etiqueta, files in GTI_PROFILES:
            pk = gtis.get(code)
            w('')
            w('### {} · `{}` → {}'.format(
                etiqueta, code, 'pk {}'.format(pk) if pk else 'NO EXISTEIX en aquest schema'))
            w('')
            w('| # | peça | cara | vora | presence | assignació de peça |')
            w('|---|---|---|---|---|---|')
            for i, (peca, cara, vora, pres, origen) in enumerate(files, 1):
                marca = '🚩 ' if origen.startswith('ofici') else ''
                w('| {} | `{}` | {} | `{}` | {} | {}{} |'.format(
                    i, peca, cara or '—', vora, pres, marca, origen))

        w('')
        w('## Vocabulari que la Montse troba a FALTAR — proposat, NO creat ({})'.format(
            len(EXTENSIONS_PENDENTS)))
        w('')
        w('Decidir un slug es decidir un contracte. Aquests van al report i esperen l\'Agus.')
        w('')
        w('| slug proposat | com en diu ella | d\'on surt |')
        w('|---|---|---|')
        for slug, nom, font in EXTENSIONS_PENDENTS:
            w('| `{}` | {} | {} |'.format(slug, nom, font))
        w('')
