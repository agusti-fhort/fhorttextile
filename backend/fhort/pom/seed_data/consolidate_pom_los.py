"""Config versionable de la consolidació del catàleg POM LOSAN (PAS 4B).

Taula validada per Agus (gate 4A, 2026-07-18). Separada del command (motor/config).
Identificació dels prims per CLAU NATURAL: (codi_client + guard de nom + té àlies LOS) —
NO per pk. El codi_client NO és únic a POMMaster (p.ex. dos 'H', dos 'D'), per això el
guard de nom desambigua (ex: 'D' HIP WIDTH-LOS vs 'D' bottom-width no-LOS).
"""

# ── FUSIÓ (13 entrades · 14 prims; 'H' cobreix 2) ────────────────────────────
# (prim_codi, dest_canonic_codi, nom_guard_upper). El command fusiona TOTS els prims amb
# aquell codi que siguin prims (sense pom_global ni maps), amb àlies LOS, i el nom contingui
# el guard. Re-apunta refs vives, mou BaseMeasurement/ModelGradingRule (+ altres), esborra
# GradedSpec, re-apunta CustomerPOMAlias, i desactiva el prim.
FUSIONS = [
    ('T.1', 'RI FR',    'RISE'),                  # FRONT RISE
    ('T.2', 'RI BK',    'RISE'),                  # BACK RISE
    ('L.4', 'NK DR FR', 'NECK DROP'),             # FRONT NECK DROP
    ('L.5', 'NK DR BK', 'NECK DROP'),             # BACK NECK DROP
    ('A.1', 'AC FR',    'FRONT WIDTH'),           # → Across front
    ('A2',  'AC BK',    'BACK WIDTH'),            # → Across back
    ('H',   'BIC',      'SLEEVE MUSCLE'),         # 2 prims (H, H 1/2) → bicep
    ('B1',  'CH RLX',   'CHEST WIDTH RELAXED'),
    ('H11', 'SL OP',    'SLEEVE OPENING'),        # → Sleeve opening / cuff width
    ('K.2', 'AC SH',    'SHOULDER TO SHOULDER'),  # → Across shoulder (back)
    ('B2',  'CH STR',   'CHEST WIDTH EXTENDED'),  # → Chest width (stretched)
    ('D',   'HI PA',    'HIP WIDTH'),             # → Hip width (pants); guard exclou id436
    ('JJ',  'ELB',      'ELBOW WIDTH'),           # → Sleeve width at elbow
]

# Reverse-relations de POMMaster a tractar en fusió:
FUSIO_MOVE_RELS = ['base_measurements', 'model_grading_rules', 'measurement_changes',
                   'model_grading_overrides', 'item_base_measurements', 'mesures_perfil',
                   'alerts', 'pattern_poms', 'estadistiques']
FUSIO_DELETE_RELS = ['graded_specs']            # output pur del motor, regenerable
FUSIO_LEAVE_RELS = ['regles_grading']           # s'esborren al PAS 3; PROTECT → desactivar prim

# ── COMPLETAR (traduccions) ──────────────────────────────────────────────────
CSV_TRAD = 'traduccions_pom_los.csv'            # al mateix dir seed_data

# ── MAPS explícits (vault GRADING_SOURCES_LOSAN.md ABSENT en aquest host) ─────
# Només els exemples explícits i anatòmicament inequívocs del brief on el POM i l'item
# existeixen. La resta de GarmentPOMMap queda PENDENT del vault (es llisten a l'informe).
# (codi_o_alias, [item_codes])
MAPS_EXPLICIT = [
    ('D6',   ['baby_bodysuit']),                 # FRONT CROTCH WIDTH
    ('D7',   ['baby_bodysuit']),                 # BACK CROTCH WIDTH
    ('S.10', ['hoodie', 'baby_sleepsuit']),      # HOOD LENGTH
    ('S.56', ['hoodie', 'baby_sleepsuit']),      # HOOD PIECE WIDTH
    ('S53',  ['hoodie', 'baby_sleepsuit']),      # HOOD WIDTH LOCATION
]

CUSTOMER_CODI = 'LOS'
TENANT = 'fhort'
