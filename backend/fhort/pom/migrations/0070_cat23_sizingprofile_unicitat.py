# CAT2.3 (2026-08-07) — `SizingProfile`: netejar els duplicats REALS del catàleg de talles.
#
# ─────────────────────────────────────────────────────────────────────────────────────────
# REESCRITA 2026-08-19 (FASE 2 · PROD) — FORA LA CLAU ÚNICA, I LA NETEJA PASSA A SER DIRIGIDA
# PER DADES. Decisió d'Agus (D4).
#
# QUÈ HI HAVIA. Dues coses cablejades al cens de STAGING:
#   · `GRUPS = [(539, [540, 541]), (288, [510])]` — ids literals, amb un guard que avorta si
#     el perfil «que cau» ja no comparteix àmbit amb el que es queda.
#   · un `AlterUniqueTogether` que posava
#     `(target, garment_type, construction, fit_type, size_system, customer)` com a clau única.
#
# QUÈ VA TROBAR EL CENS DE PROD (19/08). Les dues peces fallaven, i per motius diferents:
#
#  1 · ELS IDS NO SÓN LES MATEIXES FILES. A `fhort` els cinc pks existeixen, però amb àmbits
#      que no tenen res a veure amb els de staging (540 → (9,71,2,1,44,None) contra els
#      (7,85,2,1,66,None) del 539). El guard disparava al primer `neteja()`, i tenia raó.
#
#  2 · ELS DUPLICATS DE DEBÒ SÓN UNS ALTRES, i la migració ni els mirava:
#        `fhort` · (1,71,1,5,29,None) → 515 i 557
#        `los`   · NEWBORN × {GIRL, BOY, UNISEX} → (23,24,25), (37,38,39), (40,41,42)
#
#  3 · I NO SÓN BESSONS. El precedent de staging deia «la versió no aportava res: el seu
#      ruleset era bessó BYTE A BYTE del canònic». A PROD cap parella ho és: 515/557 porten
#      rulesets de 77 regles amb empremtes distintes, i els tres de `los` són `LOS New Born
#      Knit — Tops` (45 regles), `— Onepieces` (48) i `— Bottoms` (31). Esborrar-ne un
#      perdria graduació real.
#
#  4 · I `los` TÉ 25 PERFILS, on la versió anterior d'aquest fitxer afirmava que no en tenia cap.
#
# 🔑 PER QUÈ CAU LA CLAU ÚNICA, i no és una rendició. El cas de `los` no és brutícia: és el
# domini dient que la clau no el sap expressar. La família `NEWBORN` necessita TRES lleis de
# graduació (Bottoms · Onepieces · Tops) per al mateix target, i l'eix que les distingeix és la
# MENA DE PEÇA — que `SizingProfile` no té (no hi ha `garment_type_item`). Amb la clau posada,
# LOSAN no pot existir. Amb la clau treta, existeix i el problema queda anotat on toca.
#
# 📌 DEUTE G6 · `garment_type_item` a la clau natural de `SizingProfile`. El disseny bo és
#    afegir-hi la mena de peça i llavors sí posar la unicitat. Requereix camp nou + migració +
#    decidir què fan els perfils existents amb `garment_type_item` NULL. La troballa que ho
#    justifica és la de LOSAN d'aquí sobre: 3 rulesets × 3 targets sobre una sola família.
#    Mentrestant la proliferació NO queda oberta: `SizingProfile.clean()` segueix blocant els
#    NOUS duplicats d'àmbit (models.py) — el que canvia és que la BD deixa de matar els que ja
#    hi són i que el domini justifica.
#
# LA NETEJA QUE QUEDA. Només cauen els bessons verificats BYTE A BYTE: mateix àmbit **i**
# mateix joc de regles. A PROD això és zero files a les tres schemas → no-op net, i la
# migració passa sense tocar res. Si algun dia n'apareix un de real, cau sol i queda al log.
# ─────────────────────────────────────────────────────────────────────────────────────────
from django.db import migrations

#: Els camps que fan que dos perfils siguin EL MATEIX àmbit.
CLAU = ('target_id', 'garment_type_id', 'construction_id',
        'fit_type_id', 'size_system_id', 'customer_id')


def _empremta(GradingRule, rule_set_id):
    """Identitat del joc de regles d'un ruleset. `None` = sense ruleset (no comparable)."""
    if rule_set_id is None:
        return None
    files = sorted(
        GradingRule.objects.filter(rule_set_id=rule_set_id).values_list(
            'pom_id', 'logica', 'increment_base', 'increment_break', 'talla_break_label',
        )
    )
    return repr(files)


def neteja(apps, schema_editor):
    SizingProfile = apps.get_model('pom', 'SizingProfile')
    GradingRule = apps.get_model('pom', 'GradingRule')
    schema = getattr(schema_editor.connection, 'schema_name', '?')

    def log(msg):
        print(f'  [CAT2.3 · {schema}] {msg}')

    grups = {}
    for sp in SizingProfile.objects.all().order_by('pk'):
        grups.setdefault(tuple(getattr(sp, c) for c in CLAU), []).append(sp)

    esborrats = 0
    for clau, membres in grups.items():
        if len(membres) < 2:
            continue
        # Es queda el MÉS ANTIC (pk més baix, i ja ve ordenat). Només cauen els que en són
        # bessons byte a byte; qualsevol altre es reporta i es queda.
        viu = membres[0]
        emp_viu = _empremta(GradingRule, viu.grading_rule_set_id)
        for mort in membres[1:]:
            emp_mort = _empremta(GradingRule, mort.grading_rule_set_id)
            if emp_viu is None or emp_mort is None or emp_mort != emp_viu:
                log(f'àmbit {clau}: pk={mort.pk} NO cau — el seu ruleset '
                    f'({mort.grading_rule_set_id}) no és bessó del de pk={viu.pk} '
                    f'({viu.grading_rule_set_id}). Duplicat CONSERVAT.')
                continue
            # L'única relació entrant de `SizingProfile` és ella mateixa (`parent_profile`,
            # SET_NULL). Si en penja algú, es reassigna al que es queda en comptes de deixar
            # un NULL mut — i si apareix qualsevol altra cosa, això peta i és el que volem.
            SizingProfile.objects.filter(parent_profile_id=mort.pk).update(
                parent_profile_id=viu.pk)
            mort.delete()
            esborrats += 1
            log(f'àmbit {clau}: pk={mort.pk} ESBORRAT (bessó byte a byte de pk={viu.pk})')

    if not esborrats:
        log('cap bessó real: no-op')


def enrere(apps, schema_editor):
    """Buida a posta: un esborrat signat no es desfà sol."""


class Migration(migrations.Migration):

    dependencies = [
        ('pom', '0069_cat21a_talla_base_label'),
    ]

    operations = [
        migrations.RunPython(neteja, enrere),
        # ⚠️ SENSE `AlterUniqueTogether`: v. la capçalera i el DEUTE G6. La clau natural no pot
        # ser aquesta mentre `SizingProfile` no sàpiga de quina MENA DE PEÇA parla.
    ]
