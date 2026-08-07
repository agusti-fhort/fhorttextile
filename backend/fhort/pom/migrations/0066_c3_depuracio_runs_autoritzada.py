# C3 (2026-08-07) — depuració AUTORITZADA de la biblioteca de talles (decisions d'Agus).
#
# L'Agus n'havia signat TRES. En van dos. El tercer, `TGIRL-EU-HEIGHT`, s'ha aturat aquí
# mateix perquè la re-verificació ha trobat ús viu, i el brief manava exactament això:
# «VERIFICAR les FK entrants a zero ABANS de cada delete — si alguna cosa hi apunta ara,
# ATURA i anota». V. `docs/diagnosis/REPORT_CATALEG_TALLES.md` §C3.
#
# 🔑 PER QUÈ EL CENS DE LA NIT NO HO VA VEURE, i la lliçó que val per a tots els deletes:
# el cens va comptar les 6 FK que apunten al **SizeSystem** i va trobar zero — correcte. Però
# l'ús viu d'un run de talles no penja del run: penja de les seves **talles**. `GradingRule.
# talla_base` és un FK a `SizeDefinition` amb `on_delete=PROTECT`, i `TGIRL-EU-HEIGHT` («Alpha
# EU — Grading Reference») és l'àncora de talla base de **350 regles repartides en 10 rulesets
# que són d'ALTRES runs**. Un guard que només mira el node i no el que penja dels seus fills
# dona verd a un esborrat que la BD rebutja — o, si el fill fos CASCADE en comptes de PROTECT,
# l'hauria executat en silenci.
#
# Els altres dos sí que cauen:
#   · MEN-SHIRT-NUM (26) — 0 talles i 0 referències de cap mena.
#   · WOMAN_BRW_01 (53) + el ruleset «Prova BRW ALPHA UE», que n'era l'ÚNIC ús (D2 resolta:
#     el grading BRW de debò penja del canònic ALPHA_EU_W). Les 21 regles que ancoren a les
#     seves talles són les d'aquell mateix ruleset, i cauen amb ell (`rule_set` és CASCADE).
# D1/D5/D6 NO es toquen: van diferits al fil LOSAN.
from django.db import migrations

#: (codi del run, id esperat a `fhort`). L'id és una segona clau: els ids NO són els mateixos
#: entre schemes, o sigui que si el codi surt amb un altre id, no és aquell run.
RUNS = [
    ('MEN-SHIRT-NUM', 26),
    ('WOMAN_BRW_01', 53),
]
#: L'únic ruleset que l'Agus autoritza a caure, i el run del qual penja.
RULESET_AUTORITZAT = ('Prova BRW ALPHA UE', 'WOMAN_BRW_01')


def _relacions_entrants(model):
    """Les relacions entrants DECLARADES ALS MODELS (no a `information_schema`).

    Les FK amb `db_constraint=False` —n'hi ha, i una és d'avui mateix— no deixen constraint
    a la BD: un cens fet només amb SQL se les deixaria i el delete semblaria segur.
    """
    return [f for f in model._meta.get_fields()
            if (f.one_to_many or f.one_to_one) and f.auto_created and not f.concrete]


def _penjats(model, filtre, excloure=()):
    fora = []
    for f in _relacions_entrants(model):
        if (f.related_model._meta.label, f.field.name) in excloure:
            continue
        n = f.related_model.objects.filter(**{f'{f.field.name}__in': filtre}).count()
        if n:
            fora.append(f'{f.related_model._meta.label}.{f.field.name}={n}')
    return fora


def depura(apps, schema_editor):
    SizeSystem = apps.get_model('pom', 'SizeSystem')
    SizeDefinition = apps.get_model('pom', 'SizeDefinition')
    GradingRuleSet = apps.get_model('pom', 'GradingRuleSet')

    for codi, id_esperat in RUNS:
        ss = SizeSystem.objects.filter(codi=codi).first()
        if ss is None:
            continue                       # a `public` i `los` no hi són: res a fer
        if ss.pk != id_esperat:
            raise RuntimeError(
                f'C3 ATURA · el run {codi!r} surt amb id {ss.pk} i el cens deia {id_esperat}. '
                'Els ids no són els mateixos entre schemes: no s\'esborra res a cegues.'
            )

        # El ruleset autoritzat cau ABANS del run: s'endú les seves regles (CASCADE) i, amb
        # elles, el PROTECT que aquestes regles posen sobre les talles del run.
        excloure_run = ()
        if codi == RULESET_AUTORITZAT[1]:
            seus = list(GradingRuleSet.objects.filter(size_system=ss))
            noms = {rs.nom for rs in seus}
            if noms - {RULESET_AUTORITZAT[0]}:
                raise RuntimeError(
                    f'C3 ATURA · {codi!r} té rulesets que l\'Agus no ha autoritzat a esborrar: '
                    f'{sorted(noms - {RULESET_AUTORITZAT[0]})}'
                )
            for rs in seus:
                sobre = _penjats(GradingRuleSet, [rs.pk],
                                 excloure=(('pom.GradingRule', 'rule_set'),))
                if sobre:
                    raise RuntimeError(
                        f'C3 ATURA · el ruleset {rs.nom!r} ja no està sol: hi apunta {sobre}. '
                        'Això no hi era al cens de la nit — anota-ho i decideix abans de continuar.'
                    )
                rs.delete()
            excloure_run = (('pom.GradingRuleSet', 'size_system'),)

        # (1) qui apunta al RUN …
        sobre_run = _penjats(SizeSystem, [ss.pk],
                             excloure=excloure_run + (('pom.SizeDefinition', 'size_system'),))
        # (2) … i qui apunta a les seves TALLES, que és on viu l'ús de debò.
        talles = list(SizeDefinition.objects.filter(size_system=ss).values_list('pk', flat=True))
        sobre_talles = _penjats(SizeDefinition, talles) if talles else []

        if sobre_run or sobre_talles:
            raise RuntimeError(
                f'C3 ATURA · {codi!r} NO té les FK entrants a zero. '
                f'Al run: {sobre_run or "res"}. A les seves {len(talles)} talles: '
                f'{sobre_talles or "res"}. El cens deia que sí — anota-ho i decideix.'
            )
        ss.delete()                        # les talles cauen per cascade


def enrere(apps, schema_editor):
    """Buida a posta: una depuració signada no es desfà sola. Si cal tornar-hi, es torna des
    del backup pre-V4, que és sencer i consistent."""


class Migration(migrations.Migration):

    dependencies = [
        ('pom', '0065_c2_parteix_baby_months'),
        # No són decoratives: `_relacions_entrants` pregunta a l'ESTAT HISTÒRIC, i una app que
        # no hi sigui, senzillament, no surt al recompte — donaria zero i el delete semblaria
        # segur. `models_app/0079` hi és expressament: porta `derivat_de_rule_set`, que és
        # `db_constraint=False` i que per tant tampoc no deixa rastre a `information_schema`.
        ('models_app', '0079_m3_derivat_de_rule_set'),
        ('tasks', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(depura, enrere),
    ]
