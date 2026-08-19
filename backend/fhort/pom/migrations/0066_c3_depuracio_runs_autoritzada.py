# C3 (2026-08-07) — depuració AUTORITZADA de la biblioteca de talles (decisions d'Agus).
#
# L'Agus n'havia signat TRES. El tercer, `TGIRL-EU-HEIGHT`, es va aturar perquè la
# re-verificació hi va trobar ús viu, i el brief manava exactament això: «VERIFICAR les FK
# entrants a zero ABANS de cada delete — si alguna cosa hi apunta ara, ATURA i anota».
# V. `docs/diagnosis/REPORT_CATALEG_TALLES.md` §C3.
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
# ─────────────────────────────────────────────────────────────────────────────────────────
# REESCRITA 2026-08-19 (FASE 2 · PROD) — EL GUARD PASSA A SER DIRIGIT PER DADES.
#
# QUÈ HI HAVIA. La migració portava el cens de STAGING cablejat: `RUNS = [('MEN-SHIRT-NUM',
# 26), ('WOMAN_BRW_01', 53)]`, i el codi del run havia de sortir amb AQUELL id o `RuntimeError`.
# A PROD `WOMAN_BRW_01` surt amb id **46**, i la migració avortava abans de mirar res més.
#
# I l'avortament amagava el que de debò importa: a PROD aquell run **no és el mateix objecte**.
# A staging era un run de prova amb un únic ruleset de prova; a PROD té **10 models vius**,
# 2 rulesets (`BRW WOMEN WOVEN REGULAR BLUSA`, 21 regles, 5 models · i el de Tops, 26 regles)
# i 5 talles. El ruleset «Prova BRW ALPHA UE» no existeix enlloc de PROD. Fer que les dades
# satisfessin el cens hauria volgut dir destruir producció.
#
# QUÈ HI HA ARA. Cap id, cap suposició d'schema. Un run cau NOMÉS si les dades diuen que és
# mort, i les tres condicions es comproven aquí mateix, cada vegada:
#
#   C1 · cap ruleset que no estigui a `RULESETS_AUTORITZATS`
#   C2 · cap model viu que hi apunti (`Model.size_system`)
#   C3 · cap FK entrant al run NI a les seves talles
#
# I si alguna falla: **LOG i SALTA**. No avorta i no esborra. Un run que és viu en un schema i
# mort en un altre és una situació normal en multi-tenant, no una anomalia que hagi de tombar
# les 43 migracions del tren a mitja finestra.
#
# ⚠️ EL CENS D'FK ES FA PER CAMPS CONCRETS, no per `get_fields()`. Les FK amb
# `related_name='+'` NO surten com a relació inversa: al cens de PROD del 19/08 n'hi havia
# DUES de setze cap a `POMMaster` (`SizeCheckLine.pom`, `PieceFittingLine.pom`, 644+189 files).
# És la mateixa lliçó del paràgraf de dalt un pis més avall: un guard que mira on és còmode
# mirar dona verd a un esborrat que no ho és.
# ─────────────────────────────────────────────────────────────────────────────────────────
from django.db import migrations

#: Els runs que l'Agus autoritza a caure SI les dades diuen que són morts. Sense ids: el codi
#: és la clau, i les tres condicions de sota són qui decideix de debò.
RUNS_AUTORITZATS = ('MEN-SHIRT-NUM', 'WOMAN_BRW_01')

#: Els únics rulesets que poden penjar d'un run autoritzat perquè segueixi sent esborrable.
RULESETS_AUTORITZATS = frozenset({'Prova BRW ALPHA UE'})


def _fks_cap_a(apps, objectiu):
    """Totes les FK CONCRETES cap a `objectiu`, `related_name='+'` incloses.

    `objectiu._meta.get_fields()` NO les hi posaria: una FK amb `related_name='+'` no crea
    relació inversa i, per tant, no apareix a la introspecció des del costat apuntat. Es
    recorren els models de l'ESTAT HISTÒRIC i se'n miren els camps concrets, que sí que hi són.
    """
    fora = []
    for model in apps.get_models():
        for f in model._meta.get_fields():
            if getattr(f, 'many_to_one', False) and f.concrete and f.related_model is objectiu:
                fora.append((model, f.name))
    return fora


def _penjats(apps, objectiu, pks, excloure=()):
    """`['app.Model.camp=N', …]` per a tot el que apunti a `pks`. Buit = ningú hi apunta."""
    fora = []
    for model, camp in _fks_cap_a(apps, objectiu):
        if (model._meta.label, camp) in excloure:
            continue
        n = model.objects.filter(**{f'{camp}__in': pks}).count()
        if n:
            fora.append(f'{model._meta.label}.{camp}={n}')
    return fora


def depura(apps, schema_editor):
    SizeSystem = apps.get_model('pom', 'SizeSystem')
    SizeDefinition = apps.get_model('pom', 'SizeDefinition')
    GradingRuleSet = apps.get_model('pom', 'GradingRuleSet')
    Model = apps.get_model('models_app', 'Model')
    schema = getattr(schema_editor.connection, 'schema_name', '?')

    def log(msg):
        print(f'  [C3 · {schema}] {msg}')

    for codi in RUNS_AUTORITZATS:
        ss = SizeSystem.objects.filter(codi=codi).first()
        if ss is None:
            continue                                   # no hi és en aquest schema: res a fer

        # ── C1 · rulesets no autoritzats ───────────────────────────────────────────────
        seus = list(GradingRuleSet.objects.filter(size_system=ss))
        forasters = sorted({rs.nom for rs in seus} - RULESETS_AUTORITZATS)
        if forasters:
            log(f'{codi} (pk={ss.pk}) NO es toca: hi pengen rulesets no autoritzats '
                f'{forasters}')
            continue

        # ── C2 · models vius ───────────────────────────────────────────────────────────
        n_models = Model.objects.filter(size_system=ss).count()
        if n_models:
            log(f'{codi} (pk={ss.pk}) NO es toca: {n_models} models vius hi apunten')
            continue

        # Els rulesets autoritzats cauen ABANS del run: s'enduen les seves regles (CASCADE) i,
        # amb elles, el PROTECT que aquestes regles posen sobre les talles del run.
        excloure_run = ()
        if seus:
            aturat = False
            for rs in seus:
                sobre = _penjats(apps, GradingRuleSet, [rs.pk],
                                 excloure=(('pom.GradingRule', 'rule_set'),))
                if sobre:
                    log(f'{codi}: el ruleset {rs.nom!r} no està sol (hi apunta {sobre}) — '
                        f'el run NO es toca')
                    aturat = True
                    break
            if aturat:
                continue
            for rs in seus:
                rs.delete()
            excloure_run = (('pom.GradingRuleSet', 'size_system'),)

        # ── C3 · FK entrants al run I a les seves talles ───────────────────────────────
        sobre_run = _penjats(apps, SizeSystem, [ss.pk],
                             excloure=excloure_run + (('pom.SizeDefinition', 'size_system'),))
        talles = list(SizeDefinition.objects.filter(size_system=ss)
                      .values_list('pk', flat=True))
        sobre_talles = _penjats(apps, SizeDefinition, talles) if talles else []
        if sobre_run or sobre_talles:
            log(f'{codi} (pk={ss.pk}) NO es toca: al run {sobre_run or "res"}; '
                f'a les seves {len(talles)} talles {sobre_talles or "res"}')
            continue

        ss.delete()                                    # les talles cauen per cascade
        log(f'{codi} (pk={ss.pk}) ESBORRAT amb {len(talles)} talles: 0 rulesets forasters, '
            f'0 models, 0 FK entrants')


def enrere(apps, schema_editor):
    """Buida a posta: una depuració signada no es desfà sola. Si cal tornar-hi, es torna des
    del backup pre-V4, que és sencer i consistent."""


class Migration(migrations.Migration):

    dependencies = [
        ('pom', '0065_c2_parteix_baby_months'),
        # No són decoratives: `_fks_cap_a` pregunta a l'ESTAT HISTÒRIC, i una app que no hi
        # sigui, senzillament, no surt al recompte — donaria zero i el delete semblaria segur.
        # `models_app/0079` hi és expressament: porta `derivat_de_rule_set`, que és
        # `db_constraint=False` i que per tant tampoc no deixa rastre a `information_schema`.
        ('models_app', '0079_m3_derivat_de_rule_set'),
        ('tasks', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(depura, enrere),
    ]
