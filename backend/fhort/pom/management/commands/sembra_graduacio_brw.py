"""SEMBRA BRW · graduació denim + exterior (COMMIT 2, ops/sembra_brw/graduacio_denim_exterior.json).

Font canònica: el JSON de COMMIT 1 (font: GUIA_ENTRADA_BRW_DENIM_EXTERIOR.xlsx). Aquesta
comanda NOMÉS llegeix aquell fitxer i el fa idempotent contra la BD — cap valor literal viu
aquí, per no duplicar la font de veritat.

Sembra de DADES, no migració. Idempotent per clau natural a cada bloc:
  1. POMs nous — per `codi_client` (case-insensitive, `POMMaster.Meta.constraints`).
  2. Àlies — per `(customer, client_code)`; el `pom` de destí és el que decideix REPUNTAR/IGUAL.
  3. Joc 'BRW Exterior' — per `nom`, LINEAR pur (sense breaks, el full no en porta).
  4. Joc 'BRW Denim' — per `nom`; amb --create-run crea SYS_BRW_01 (P·32·34·36·38·40·42, base 34)
     si absent — MAI a PROD, on el brief diu que ja hi és.

Els 4 forats de catàleg del full DENIM (FE sense regla, RT/PR4/PR5 sense POM/àlies, R4
col·lidint amb R2 perquè `GradingRule` no té eix d'instància) es reporten com PENDENTS i
NO s'escriuen — decisió CTO 21/09, v. `avisos_pas0`/`pendents` del JSON. La tolerància
(TOL-/TOL+) tampoc s'escriu: `GradingRule` no té cap camp de tolerància.

🔑 DRY-RUN ESCRIU DE DEBÒ, DINS DE LA TRANSACCIÓ, I FA ROLLBACK AL FINAL. Cada bloc depèn
dels anteriors (les regles necessiten el POM que el bloc 1 acaba de crear): si el dry-run
no escrivís res, cada bloc a partir del segon reportaria «PENDENT» en cascada i el dry-run
deixaria de dir la veritat sobre l'estat final. `--apply` és només el que decideix si la
transacció es confirma o es desfà — la lectura del que passarà és IDÈNTICA als dos costats.

    venv/bin/python manage.py sembra_graduacio_brw --customer BRW                          # dry-run
    venv/bin/python manage.py sembra_graduacio_brw --customer BRW --create-run             # + crea SYS_BRW_01/BRW Denim si absents (dry-run)
    venv/bin/python manage.py sembra_graduacio_brw --customer BRW --create-run --apply     # escriu
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django_tenants.utils import schema_context

from fhort.pom.grading_regime import MAX_BREAKS, valida_breaks, normalitza_logica
from fhort.pom.models import (
    POMMaster, CustomerPOMAlias, SizeSystem, SizeDefinition,
    GradingRuleSet, RuleSetScopeNode, GradingRule, GarmentGroup,
)
from fhort.tasks.models import Customer

DEFAULT_FITXER = 'ops/sembra_brw/graduacio_denim_exterior.json'
ORIGEN_ALIES = 'SEMBRA0921'  # <=10 chars (CustomerPOMAlias.origen), no és un choice enumerat —
                              # mateix precedent que 'REPUNT_v5' a repunta_alies_retirats.py.

# Codis de POM que el full DENIM documenta però que NO esdevenen GradingRule (v.
# `pendents` al JSON per al motiu de cadascun). Font única d'exclusió: si el JSON canvia
# de forma i deixa de marcar-los pendents, aquesta llista s'ha d'actualitzar a mà —a posta,
# perquè excloure una fila és una decisió, no una inferència automàtica.
CODIS_PENDENTS_DENIM = {'FE', 'RT', 'PR4', 'PR5', 'R4'}


def _camp_eq(a, b):
    """Compara un camp EXISTENT (pot ser Decimal/None) amb el DERIVAT (float/int/list/dict/None)
    tolerant a la precisió — evita falsos «ACTUALITZAR» per `Decimal('0.7') != 0.7` (el float
    0.7 no té representació binària exacta, i Python els compara desiguals)."""
    if a is None or b is None:
        return a is None and b is None
    if isinstance(a, (int, float)) or hasattr(a, 'as_tuple'):  # numèric o Decimal
        try:
            return abs(float(a) - float(b)) < 1e-6
        except (TypeError, ValueError):
            return a == b
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return False
        return all(_camp_eq(x.get('delta') if isinstance(x, dict) else x,
                            y.get('delta') if isinstance(y, dict) else y) and
                   (not isinstance(x, dict) or (x.get('inici') == y.get('inici')
                                                and x.get('final') == y.get('final')))
                   for x, y in zip(a, b))
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a) != set(b):
            return False
        return all(_camp_eq(a[k], b[k]) for k in a)
    return a == b


def _resol_pom(codi):
    """POMMaster pel codi de CATÀLEG (codi_client, case-insensitive)."""
    return POMMaster.objects.filter(codi_client__iexact=codi).first()


def _resol_pom_denim(codi, customer):
    """Com `_resol_pom`, però amb fallback a l'àlies BRW quan el full DENIM dona un codi
    que NO és de catàleg (BB, PR3, R5): el full barreja codis de catàleg i codis de client
    perquè per a qui l'ha escrit són "el mateix POM dit de dues maneres". R4 hi entraria
    igual (l'àlies existeix, apunta a R2) però mai hi arriba: `CODIS_PENDENTS_DENIM` el
    filtra abans de cridar aquesta funció — la col·lisió amb la fila pròpia de R2 és
    exactament per què R4 és pendent, no una cosa que aquest fallback hagi de resoldre."""
    directe = _resol_pom(codi)
    if directe is not None:
        return directe
    alies = CustomerPOMAlias.objects.filter(
        customer=customer, client_code__iexact=codi, pom__isnull=False).select_related('pom').first()
    return alies.pom if alies else None


def _group_positions(labels, deltas):
    groups = []
    for lbl, v in zip(labels, deltas):
        if groups and abs(groups[-1][2] - v) < 1e-9:
            s, _e, val, c = groups[-1]
            groups[-1] = (s, lbl, val, c + 1)
        else:
            groups.append((lbl, lbl, v, 1))
    return groups


def _run_from_passos(passos):
    """['P→32','32→34',...] -> ['P','32','34',...]. El run que compta és el que declaren
    els PASSOS del full (les etiquetes que la guia realment toca), no el run sencer del
    `SizeSystem` a la BD — que pot portar talles (XL/XXL/3XL...) que el full mai esmenta."""
    run = [passos[0].split('→')[0]]
    run += [p.split('→')[1] for p in passos]
    return run


def deriva_regla_lineal_o_step(deltes, run, base_label):
    """[deltes literals del full] -> camps de GradingRule, o None si cap de les dues
    formes (LINEAR+breaks, STEP) el pot representar sense inventar-se res.

    `run` és el run declarat pel full (etiquetes en ordre); `deltes` cobreix totes les
    posicions EXCEPTE la base, en el mateix ordre que `run` menys `base_label`. Prova
    primer LINEAR (com a molt `MAX_BREAKS` intervals, arrodonint cap al grup MÉS GRAN com
    a delta general): si no hi cap, cau a STEP (`valors_step`, sense límit — és la forma
    pensada per a patrons irregulars, com ja avisa la nota "avança cada 2 talles").
    """
    labels = [x for x in run if x != base_label]
    if len(labels) != len(deltes):
        return None
    if all(abs(d) < 1e-9 for d in deltes):
        return {'logica': 'FIXED', 'increment_base': 0, 'breaks': None, 'valors_step': None}

    groups = _group_positions(labels, deltes)
    if len(groups) - 1 <= MAX_BREAKS:
        gi = max(range(len(groups)), key=lambda k: groups[k][3])
        general = groups[gi][2]
        breaks = [{'inici': s, 'final': e, 'delta': v}
                  for k, (s, e, v, c) in enumerate(groups) if k != gi]
        normalitzats, err = valida_breaks(breaks or None, logica='LINEAR', run=run,
                                          increment_base=general)
        if err is None:
            logica = normalitza_logica('LINEAR', increment_base=general, breaks=normalitzats)
            return {'logica': logica, 'increment_base': general,
                    'breaks': normalitzats, 'valors_step': None}

    # STEP: un valor per posició, sense agrupar — cobreix patrons irregulars (PR3/BR1/CR2).
    valors_step = {lbl: v for lbl, v in zip(labels, deltes)}
    return {'logica': 'STEP', 'increment_base': None, 'breaks': None,
            'valors_step': valors_step}


class Command(BaseCommand):
    help = "Sembra de graduació BRW (denim+exterior) des del JSON canònic de COMMIT 1. Dry-run per defecte."

    def add_arguments(self, parser):
        parser.add_argument('--customer', required=True, help="Codi del client (Customer.codi), p.ex. BRW.")
        parser.add_argument('--fitxer', default=DEFAULT_FITXER, help="Ruta del JSON canònic.")
        parser.add_argument('--apply', action='store_true', help="Escriu. Sense aquest flag: dry-run (rollback).")
        parser.add_argument('--create-run', action='store_true',
                            help="Permet crear SYS_BRW_01 i el contenidor 'BRW Denim' si "
                                 "no existeixen pel nom (staging). Sense aquest flag, si "
                                 "no existeixen la comanda s'atura (com hauria de passar a PROD).")
        parser.add_argument('--schema', default='fhort')

    def handle(self, *args, **opts):
        apply_ = opts['apply']
        create_run = opts['create_run']
        fitxer = Path(opts['fitxer'])
        if not fitxer.is_absolute():
            fitxer = Path(__file__).resolve().parents[5] / fitxer
        if not fitxer.exists():
            raise CommandError(f"No trobo el fitxer canònic: {fitxer}")
        data = json.loads(fitxer.read_text(encoding='utf-8'))

        head = 'APLICANT' if apply_ else 'DRY-RUN (escriu dins la transacció i fa rollback)'
        self.stdout.write(self.style.WARNING(f'=== sembra_graduacio_brw · {head} ==='))

        with schema_context(opts['schema']), transaction.atomic():
            customer = Customer.objects.filter(codi=opts['customer']).first()
            if customer is None:
                raise CommandError(f"Client «{opts['customer']}» no existeix en aquest schema.")

            self._bloc_poms_nous(data['poms_nous'])
            self._bloc_alies(data['alies'], customer)
            self._bloc_exterior(data['jocs'][0], customer)
            self._bloc_denim(data['jocs'][1], customer, create_run)
            self._llista_pendents(data.get('pendents', []))

            if not apply_:
                transaction.set_rollback(True)
                self.stdout.write(self.style.WARNING('\nDRY-RUN: rollback fet, cap fila queda escrita. --apply per aplicar.'))
        self.stdout.write(self.style.SUCCESS('=== FET ==='))

    # ── BLOC 1 · POMs nous ──────────────────────────────────────────────────────────────
    def _bloc_poms_nous(self, poms_nous):
        self.stdout.write('\n--- 1 · POMs nous ---')
        for p in poms_nous:
            existent = _resol_pom(p['codi'])
            if existent is None:
                accio = 'CREAT'
                POMMaster.objects.create(codi_client=p['codi'], nom_client=p['nom_en'])
            elif existent.nom_client != p['nom_en']:
                accio = f"DIVERGEIX (BD té {existent.nom_client!r}, guia diu {p['nom_en']!r}) — NO es sobreescriu sense --force"
            else:
                accio = 'IGUAL'
            self.stdout.write(f"  {p['codi']:<6} {p['nom_en']:<45} {accio}")

    # ── BLOC 2 · Àlies ───────────────────────────────────────────────────────────────────
    def _bloc_alies(self, alies, customer):
        self.stdout.write('\n--- 2 · Àlies BRW ---')
        for a in alies:
            pom_desti = _resol_pom(a['pom_desti_codi'])
            if pom_desti is None:
                self.stdout.write(f"  {a['codi_brw']:<6} PENDENT — POM destí {a['pom_desti_codi']!r} "
                                  "no existeix (corre primer el bloc 1)")
                continue
            es_instancia = a['es_instancia']
            existent = CustomerPOMAlias.objects.filter(
                customer=customer, client_code=a['codi_brw']).first()
            if existent is None:
                accio = 'CREAT'
                CustomerPOMAlias.objects.create(
                    customer=customer, client_code=a['codi_brw'], pom=pom_desti,
                    es_instancia=es_instancia, origen=ORIGEN_ALIES)
            elif existent.pom_id == pom_desti.id and existent.es_instancia == es_instancia:
                accio = 'IGUAL'
            else:
                accio = f'REPUNTAT (era pom={existent.pom and existent.pom.codi_client})'
                existent.pom = pom_desti
                existent.es_instancia = es_instancia
                existent.origen = ORIGEN_ALIES
                existent.save(update_fields=['pom', 'es_instancia', 'origen', 'actualitzat_at'])
            self.stdout.write(f"  {a['codi_brw']:<6} → {pom_desti.codi_client:<6} accio={accio}")

    # ── BLOC 3 · Joc BRW Exterior ────────────────────────────────────────────────────────
    def _bloc_exterior(self, joc, customer):
        self.stdout.write(f"\n--- 3 · Joc «{joc['nom']}» ---")
        size_system = SizeSystem.objects.filter(codi=joc['sistema']).first()
        if size_system is None:
            raise CommandError(f"Sistema de talles {joc['sistema']!r} no existeix.")
        base_def = SizeDefinition.objects.filter(
            size_system=size_system, etiqueta=joc['talla_base']).first()
        if base_def is None:
            raise CommandError(f"Talla base {joc['talla_base']!r} no existeix a {joc['sistema']!r}.")

        rs = GradingRuleSet.objects.filter(nom=joc['nom']).first()
        if rs is None:
            rs = GradingRuleSet.objects.create(
                nom=joc['nom'], size_system=size_system, customer=customer,
                origen=GradingRuleSet.ORIGEN_CLIENT_RUN, actiu=True)
            self.stdout.write(f"  ruleset: CREAT «{joc['nom']}» (id={rs.id})")
        else:
            self.stdout.write(f"  ruleset: IGUAL «{joc['nom']}» (id={rs.id})")

        grup = GarmentGroup.objects.filter(codi=joc['ambit_garment_group']).first()
        if grup and not RuleSetScopeNode.objects.filter(
                rule_set=rs, node_type=RuleSetScopeNode.NODE_GROUP, garment_group=grup).exists():
            RuleSetScopeNode.objects.create(
                rule_set=rs, node_type=RuleSetScopeNode.NODE_GROUP, garment_group=grup)

        for r in joc['regles']:
            pom = _resol_pom(r['pom'])
            if pom is None:
                self.stdout.write(f"  {r['pom']:<6} PENDENT — POM no existeix (corre el bloc 1 primer)")
                continue
            deltes = [float(d) for d in r['deltes_per_pas']]
            if len(set(round(d, 6) for d in deltes)) != 1:
                self.stdout.write(f"  {r['pom']:<6} PENDENT — no és lineal pur, guia diu que hauria de ser-ho")
                continue
            run = _run_from_passos(r['passos'])
            derivat = deriva_regla_lineal_o_step(deltes, run, joc['talla_base'])
            self._escriu_regla(rs, pom, base_def, derivat)

    # ── BLOC 4 · Joc BRW Denim ───────────────────────────────────────────────────────────
    def _bloc_denim(self, joc, customer, create_run):
        self.stdout.write(f"\n--- 4 · Joc «{joc['nom']}» ---")
        size_system = SizeSystem.objects.filter(codi=joc['sistema']).first()
        if size_system is None:
            if not create_run:
                raise CommandError(
                    f"Sistema {joc['sistema']!r} no existeix i --create-run no s'ha passat "
                    "(a PROD hauria d'existir sempre; a staging cal --create-run).")
            size_system = SizeSystem.objects.create(
                codi=joc['sistema'], nom='Brownie Denim EU', base_unit='NUMERIC_EU', actiu=True)
            for i, etq in enumerate(joc['sistema_talles']):
                SizeDefinition.objects.get_or_create(
                    size_system=size_system, etiqueta=etq,
                    defaults={'ordre': i,
                             'valor_numeric': int(etq) if etq.isdigit() else None})
            self.stdout.write(f"  sistema: CREAT «{joc['sistema']}» (id={size_system.id}, "
                              f"{len(joc['sistema_talles'])} talles)")
        else:
            self.stdout.write(f"  sistema: IGUAL «{joc['sistema']}» (id={size_system.id})")

        # El run que compta per als deltes és el declarat a `sistema_talles` (la guia).
        run = joc['sistema_talles']
        base_def = SizeDefinition.objects.filter(
            size_system=size_system, etiqueta=joc['talla_base']).first()
        if base_def is None:
            raise CommandError(f"Talla base {joc['talla_base']!r} no existeix a {joc['sistema']!r}.")

        rs = GradingRuleSet.objects.filter(nom=joc['nom']).first()
        if rs is None:
            if not create_run:
                raise CommandError(
                    f"Joc {joc['nom']!r} no existeix i --create-run no s'ha passat.")
            rs = GradingRuleSet.objects.create(
                nom=joc['nom'], size_system=size_system, customer=customer,
                origen=GradingRuleSet.ORIGEN_CLIENT_RUN, actiu=True)
            self.stdout.write(f"  ruleset: CREAT «{joc['nom']}» (id={rs.id})")
        else:
            self.stdout.write(f"  ruleset: IGUAL «{joc['nom']}» (id={rs.id})")

        grup = GarmentGroup.objects.filter(codi=joc['ambit_garment_group']).first()
        if grup and not RuleSetScopeNode.objects.filter(
                rule_set=rs, node_type=RuleSetScopeNode.NODE_GROUP, garment_group=grup).exists():
            RuleSetScopeNode.objects.create(
                rule_set=rs, node_type=RuleSetScopeNode.NODE_GROUP, garment_group=grup)

        pom_ids_usats = {}  # pom_id -> (codi de la fila que el va reclamar primer, deltes)
        for r in joc['regles']:
            codi = r['pom']
            if codi in CODIS_PENDENTS_DENIM:
                continue  # ja reportat al bloc de pendents (FE/RT/PR4/PR5/R4)
            if any(d == '—' for d in r['deltes_per_pas']):
                continue  # FE, per si mai s'afegís una fila amb el mateix patró

            pom = _resol_pom_denim(codi, customer)
            if pom is None:
                self.stdout.write(f"  {codi:<6} PENDENT — POM no existeix, ni de catàleg ni d'àlies "
                                  "(corre els blocs 1/2 primer)")
                continue

            deltes = [float(d) for d in r['deltes_per_pas']]
            if pom.id in pom_ids_usats:
                primer_codi, primeres_deltes = pom_ids_usats[pom.id]
                if [round(d, 6) for d in deltes] == [round(d, 6) for d in primeres_deltes]:
                    self.stdout.write(
                        f"  {codi:<6} DEDUP — mateix POM que «{primer_codi}» "
                        f"({pom.codi_client}), mateixos deltes: sense regla pròpia "
                        "(GradingRule no té eix d'instància)")
                else:
                    self.stdout.write(
                        f"  {codi:<6} CONFLICTE — mateix POM que «{primer_codi}» "
                        f"({pom.codi_client}) però deltes DIFERENTS: exclòs, cal resoldre a mà")
                continue
            pom_ids_usats[pom.id] = (codi, deltes)

            derivat = deriva_regla_lineal_o_step(deltes, run, joc['talla_base'])
            if derivat is None:
                self.stdout.write(f"  {codi:<6} PENDENT — no representable amb LINEAR+{MAX_BREAKS} breaks ni STEP")
                continue
            self._escriu_regla(rs, pom, base_def, derivat)

    # ── Escriptura d'una GradingRule (comuna als dos jocs) ──────────────────────────────
    def _escriu_regla(self, rs, pom, base_def, derivat):
        existent = GradingRule.objects.filter(rule_set=rs, pom=pom).first()
        camps = {
            'logica': derivat['logica'],
            'increment_base': derivat['increment_base'],
            'breaks': derivat['breaks'],
            'valors_step': derivat['valors_step'],
        }
        if existent is None:
            accio = 'CREAT'
            GradingRule.objects.create(
                rule_set=rs, pom=pom, talla_base=base_def, actiu=True, **camps)
        else:
            # Decimal(BD) vs float(derivat): comparar per valor, no per tipus — `Decimal('0.7')
            # == 0.7` és FALSE en Python (el float 0.7 no té representació binària exacta), i
            # comparar-los directe faria "ACTUALITZAT" eternament encara que el valor sigui el
            # mateix. `_camp_eq` normalitza els dos costats abans de comparar.
            divergeix = any(not _camp_eq(getattr(existent, k), v) for k, v in camps.items())
            if divergeix:
                for k, v in camps.items():
                    setattr(existent, k, v)
                existent.save(update_fields=list(camps.keys()))
            accio = 'ACTUALITZAT' if divergeix else 'IGUAL'
        detall = (f"logica={derivat['logica']} inc={derivat['increment_base']} "
                 f"breaks={derivat['breaks']} step={derivat['valors_step']}")
        self.stdout.write(f"  {pom.codi_client:<6} {accio:<12} {detall}")

    # ── Pendents (informatiu) ────────────────────────────────────────────────────────────
    def _llista_pendents(self, pendents):
        if not pendents:
            return
        self.stdout.write('\n--- PENDENTS (no escrits) ---')
        for p in pendents:
            self.stdout.write(f"  [{p['context']}] {p.get('pom', '?'):<6} {p['motiu']}")
