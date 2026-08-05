"""F5 · Migra els models de Brownie al ruleset BRW-CATALEG-v3, amb watchpoint.

**CADA MODEL MIGRAT ÉS UNA DECISIÓ PRÒPIA**, i per això la migració va separada de la sembra
del ruleset (F4): sembrar un joc de regles no obliga ningú a fer-lo servir.

**PASSA PEL MATEIX GUARD QUE LA UI, NO PEL COSTAT.** La comanda crida
`_validar_ruleset_assignable` —la mateixa funció que serveix el 409 de D-31.4 a l'endpoint— i
si dispara, escriu el recompte a la pantalla ABANS de confirmar. Escriure el `grading_rule_set`
a pèl per l'ORM hauria estat més curt i hauria saltat el guard sencer: el que fa que D-31.4
valgui alguna cosa és que ningú tingui una drecera.

Assignar un ruleset dispara un wipe-and-recreate de les regles residents
(`materialize_model_grading_rules`). Per això el guard no és cerimònia: hi ha 255 regles
residents de Brownie a staging, i 21 d'elles són IMPORTED — vénen del document del client.

**EL WATCHPOINT QUEDA SEMPRE**, encara que estiguem a staging i encara que el model no tingués
res a perdre. És l'única cosa que li dirà al pròxim tècnic per què aquest model ha canviat de
grading, qui ho va fer i d'on venia. Un canvi de joc de regles sense rastre és exactament el
que D-12 existeix per evitar.

Idempotent: un model que ja té el ruleset no es torna a assignar ni duplica el watchpoint.

    python manage.py migra_brownie_ruleset                # DRY-RUN
    python manage.py migra_brownie_ruleset --no-dry-run   # migra
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django_tenants.utils import schema_context

from fhort.models_app.models import Model, Watchpoint
from fhort.models_app.services import (materialize_model_grading_rules,
                                       origen_mgr_des_de_ruleset)
from fhort.models_app.views import _validar_ruleset_assignable, comptar_regles_residents
from fhort.pom.models import GradingRuleSet

CUSTOMER_CODI = 'BRW'
TENANT = 'fhort'
NOM_RULESET = 'BRW-CATALEG-v3'

#: Marca estable al text del watchpoint. Serveix per RETROBAR el watchpoint d'aquesta
#: migració i corregir-lo en comptes de crear-ne un de bessó: el text hi porta recomptes, i
#: un recompte que canvia no ha de deixar dues versions obertes contradient-se.
MARCA = 'catàleg Brownie v3 (F5)'

#: D'ON VENIA cada model, capturat ABANS de la primera assignació.
#:
#: ⚠️ Existeix per REPARAR una passada meva: la primera versió d'aquesta comanda assignava el
#: FK sense materialitzar les regles, i en tornar-la a passar `model.grading_rule_set` ja era
#: el joc NOU — o sigui que el watchpoint es va reescriure dient «venia de BRW-CATALEG-v3»,
#: que és exactament la informació que el watchpoint existeix per conservar. No hi ha històric
#: del camp enlloc (`GradingVersion` no el desa), així que el que se sap ve de la sortida de
#: la primera passada; el que no se sap es diu que no se sap, mai s'endevina.
#:
#: `None` = no tenia joc de regles. Absent del diccionari = no consta (models 169-173, 175-177).
ORIGEN_PREVI = {
    162: 75, 163: 115, 182: 75, 188: 79, 267: 115, 268: 115, 269: 115,
    **{i: None for i in (164, 165, 166, 167, 168)},
    **{i: None for i in range(247, 267)},
}


def frase_origen(model_id, venia_de, rs) -> str:
    """«D'on venia», dit amb la certesa que realment tenim (v. `ORIGEN_PREVI`)."""
    if model_id in ORIGEN_PREVI:
        prev = ORIGEN_PREVI[model_id]
        return f'Venia del joc de regles {prev}' if prev else 'No tenia joc de regles'
    if venia_de and venia_de.id != rs.id:
        return f'Venia de «{venia_de.nom}» (ruleset {venia_de.id})'
    return ('El joc de regles anterior NO CONSTA: es va perdre en una represa d\'aquesta '
            'mateixa migració, i el camp no té històric')


def cal_materialitzar(model, rs) -> bool:
    """El model gradua REALMENT amb `rs`? No n'hi ha prou amb tenir-hi el FK.

    Assignar el ruleset i materialitzar-ne les regles són DUES coses, i el motor obeeix la
    segona: les regles residents del model (`ModelGradingRule`) són les que apliquen. Un
    model amb el FK nou i les residents velles no ha migrat — gradua exactament com abans i
    ho fa amb una etiqueta que diu el contrari.

    Es compara el conjunt de POMs, que és el que la materialització garanteix («el set
    resultant és EXACTAMENT source_rules»).
    """
    residents = set(model.grading_rules.values_list('pom_id', flat=True))
    return residents != set(rs.regles.filter(actiu=True).values_list('pom_id', flat=True))


class Command(BaseCommand):
    help = f'F5 · Migra els models de Brownie a {NOM_RULESET} (guard D-31.4 + watchpoint).'

    def add_arguments(self, parser):
        parser.add_argument('--no-dry-run', action='store_true')
        parser.add_argument('--schema', default=TENANT)

    def handle(self, *args, **opts):
        dry = not opts['no_dry_run']
        head = 'DRY-RUN (cap escriptura)' if dry else 'MIGRANT'
        self.stdout.write(self.style.WARNING(
            f'=== migra_brownie_ruleset · {NOM_RULESET} · {head} ==='))

        migrats = ja_hi_eren = bloquejats = wp_creats = wp_corregits = 0
        residents_cremades = imported_cremades = 0
        linies, blocs = [], []

        with schema_context(opts['schema']), transaction.atomic():
            rs = GradingRuleSet.objects.filter(nom=NOM_RULESET).first()
            if not rs:
                raise CommandError(f'{NOM_RULESET} no existeix. Cal F4 abans.')

            models = Model.objects.filter(customer__codi=CUSTOMER_CODI).order_by('id')
            self.stdout.write(f'  ruleset {rs.id} · {models.count()} models de Brownie\n')

            # REPARACIÓ · la frase d'origen dels watchpoints que ja existeixen. Els recomptes
            # que hi porten són bons (es van calcular abans de materialitzar); l'únic que hi
            # és fals és el «venia de», que en la represa va llegir el ruleset ja assignat.
            # Es corregeix la frase i prou: reescriure el watchpoint sencer perdria la resta.
            fals = f'Venia de «{rs.nom}» (ruleset {rs.id})'
            for wp in Watchpoint.objects.filter(
                    model__customer__codi=CUSTOMER_CODI, estat='open',
                    text__contains=fals).select_related('model'):
                bo = frase_origen(wp.model_id, None, rs)
                wp.text = wp.text.replace(fals, bo)
                wp.save(update_fields=['text'])
                wp_corregits += 1

            for m in models:
                # ⚠️ El FK NO és la migració. Un model que ja apunta a `rs` però conserva les
                # residents velles gradua com abans; per això la condició d'«ja fet» mira les
                # regles, no el FK.
                if m.grading_rule_set_id == rs.id and not cal_materialitzar(m, rs):
                    ja_hi_eren += 1
                    continue

                venia_de = m.grading_rule_set
                total, per_origen = comptar_regles_residents(m)

                # 1r intent SENSE consentiment: és el que la UI ensenya a l'usuari.
                avis = _validar_ruleset_assignable(
                    rs, size_system_id=m.size_system_id, customer_id=m.customer_id, model=m)

                if avis:
                    payload, status = avis
                    if status == 400:
                        # BLOQUEIG DUR: no hi ha consentiment que el resolgui, i amb raó —
                        # graduar amb un run que no és el del model no vol dir res.
                        blocs.append(
                            f'  ⛔ model {m.id:4} {m.codi_intern:16} {status} '
                            f'{payload["codi"]} · {payload["message"]}')
                        bloquejats += 1
                        continue
                    # 409 · AVÍS CONSCIENT. El recompte, a la vista, abans de confirmar.
                    linies.append(
                        f'  ⚠️  model {m.id:4} {m.codi_intern:16} {status} {payload["codi"]}\n'
                        f'        residents que cauran: {payload["residents"]} '
                        f'({payload["per_origen"]}) · IMPORTED: {payload["imported"]}\n'
                        f'        {payload["message"]}')
                    residents_cremades += payload['residents']
                    imported_cremades += payload['imported']

                    # 2n intent AMB consentiment explícit. Els dos flags van separats a
                    # posta (D-31.4): acceptar el grading d'un altre client no és acceptar
                    # que s'esborrin les regles pròpies, i aquí només consentim el segon.
                    avis = _validar_ruleset_assignable(
                        rs, size_system_id=m.size_system_id, customer_id=m.customer_id,
                        model=m, confirmat_residents=True)
                    if avis:
                        payload, status = avis
                        blocs.append(f'  ⛔ model {m.id:4} {m.codi_intern:16} {status} '
                                     f'{payload["codi"]} (segon avís, no consentit aquí)')
                        bloquejats += 1
                        continue

                m.grading_rule_set = rs
                m.save(update_fields=['grading_rule_set'])
                # I ARA SÍ, LA MIGRACIÓ. `materialize_model_grading_rules` fa el
                # wipe-and-recreate del qual el guard D-31.4 avisa: sense aquesta crida el
                # model es queda amb el FK nou i les regles velles, gradua igual que abans i
                # el 409 hauria avisat d'un esborrat que no passa.
                n_noves = materialize_model_grading_rules(
                    m, rs.regles.filter(actiu=True), origen=origen_mgr_des_de_ruleset(rs))
                migrats += 1

                # EL WATCHPOINT: qui, quan i D'ON VENIA. `created_by` va a NULL perquè no hi
                # ha cap persona darrere d'una comanda — mentir-hi seria pitjor que el buit.
                # `dades=None` → watchpoint HUMÀ (text lliure), no de sistema: aquest text
                # l'ha d'entendre un tècnic, no un renderitzador de claus.
                detall = (f'Se li han esborrat {total} regles residents ({per_origen}) i '
                          f'se n\'hi han materialitzat {n_noves} del joc nou'
                          if total else
                          f'No tenia regles residents; se n\'hi han materialitzat {n_noves}')
                text = (f'Grading migrat a «{rs.nom}» (ruleset {rs.id}) el 2026-08-05 per la '
                        f'sembra del {MARCA}. {frase_origen(m.id, venia_de, rs)}. '
                        f'{detall}. Si alguna mesura gradua diferent del que esperaves, '
                        f'aquest és el canvi que ho explica.')
                # Es RETROBA pel marcador i s'actualitza. Crear-ne un de bessó cada cop que
                # el recompte canviés deixaria dos watchpoints oberts dient coses diferents
                # del mateix canvi, que és pitjor que no tenir-ne cap.
                wp = Watchpoint.objects.filter(
                    model=m, estat='open', text__contains=MARCA).first()
                if wp is None:
                    Watchpoint.objects.create(model=m, text=text, created_by=None,
                                              task=None, dades=None, estat='open')
                    wp_creats += 1
                elif wp.text != text:
                    wp.text = text
                    wp.save(update_fields=['text'])
                    wp_corregits += 1
                linies.append(f'  ✅ model {m.id:4} {m.codi_intern:16} '
                              f'{venia_de.id if venia_de else "—"} → {rs.id} · watchpoint obert')

            if dry:
                transaction.set_rollback(True)

        for l in linies:
            self.stdout.write(l)
        for b in blocs:
            self.stdout.write(self.style.ERROR(b))

        self.stdout.write(
            f'\n── RECOMPTE ──\n'
            f'  migrats: {migrats} · ja hi eren: {ja_hi_eren} · bloquejats: {bloquejats}\n'
            f'  watchpoints oberts: {wp_creats} · corregits: {wp_corregits}\n'
            f'  regles residents cremades: {residents_cremades} '
            f'(IMPORTED: {imported_cremades})')
        self.stdout.write(self.style.SUCCESS(f'\n=== FET ({head}) ==='))
