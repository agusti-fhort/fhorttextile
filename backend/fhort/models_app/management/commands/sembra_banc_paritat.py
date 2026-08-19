"""SEMBRA DEL BANC DE PARITAT — els 27 models reals de Brownie (decisió Agus, 2026-08-16).

── PER QUÈ EXISTEIX AQUESTA COMANDA ────────────────────────────────────────────────────────
`scripts_tmp/golden_c3_snapshot.py` mesurava els models **162·163·174·182·186·268·269** i cap
d'ells existeix ja: la sembra v4 del 09/08 se'n va endur el corpus. L'empremta `165d6701…` (560
cel·les) parla, doncs, d'un banc mort, i sense banc no es pot tocar el motor —que és el que
bloquejava F6/F7 del tram T8-ter.

El banc nou surt de `docs/ordres/GRADING_ENTRADA_MODELS_BROWNIE.md`: 27 fitxes REALS de Brownie,
recollides crues per a la comparació amb el catàleg canònic. Millor banc que el vell, perquè el
que hi ha a dins és el que el client mesura de veritat.

── QUÈ HI HA AL DOCUMENT, DIT EN CLAR (cens del 16/08) ─────────────────────────────────────
**Només 3 de les 27 porten run i grading** (1 «Dessuadora Animal» · 2 «RUFFLES» · 4 «MEREDITH»).
Les altres 24 són de TALLA BASE SOLA i el document ho diu elles mateixes («Aquesta fitxa NO porta
grading — només talla S»). Les 24 se sembren igual —són el corpus de comparació amb el catàleg i
donen `BaseMeasurement` reals— però **no deriven cap regla**, i per tant la superfície mesurable
de la paritat surt de les 3. Val més un banc petit i cert que un de gran i inventat.

── LES SECCIONS SÓN SECCIONS, NO PECES (Agus) ──────────────────────────────────────────────
Les fitxes porten Bodice · Pocket · Hoodie · Sleeves · Armhole… i **cap d'elles és un
`ModelGarment`**: tot va a la mare amb `seccio` informada. És exactament la distinció que T8-ter
ha hagut d'aprendre per l'altra banda —la secció és una capçalera del DOCUMENT, la peça és una
frontera del MODEL— i aquí es respecta sense excepció: aquesta comanda no crea cap peça.

── IDEMPOTÈNCIA ────────────────────────────────────────────────────────────────────────────
Re-executar-la no ha de moure ni un byte de l'empremta, perquè l'empremta és el que certifica el
motor. La clau estable és `codi_intern = 'BANC-NN'` (el número de fitxa del document), no el nom:
un model rebatejat al document seguiria sent el mateix model del banc. Les mesures van per
`update_or_create` sobre la identitat sencera, i les regles residents per
`materialize_model_grading_rules_from_specs`, que ja és wipe-and-recreate per `(model, garment)`.

Ús:
    venv/bin/python manage.py sembra_banc_paritat            # sembra/actualitza
    venv/bin/python manage.py sembra_banc_paritat --dry-run  # només el cens, cap escriptura
    venv/bin/python manage.py sembra_banc_paritat --purga    # esborra el banc i el refà
"""
import importlib.util
import os

from django.core.management.base import BaseCommand
from django.db import transaction
from django_tenants.utils import schema_context

PREFIX_CODI = 'BANC-'
PREFIX_NOM = '[BANC] '
COLLECTION = 'BANC DE PARITAT'
DOC = 'docs/ordres/GRADING_ENTRADA_MODELS_BROWNIE.md'


def _carrega_parser():
    ruta = os.path.join(os.path.dirname(__file__), '_banc_paritat_parser.py')
    spec = importlib.util.spec_from_file_location('_banc_paritat_parser', ruta)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Command(BaseCommand):
    help = 'Sembra el banc de paritat des de la bústia de fitxes de Brownie (idempotent).'

    def add_arguments(self, p):
        p.add_argument('--schema', default='fhort')
        p.add_argument('--dry-run', action='store_true')
        p.add_argument('--purga', action='store_true',
                       help='Esborra els models [BANC] abans de sembrar-los de nou.')
        p.add_argument('--doc', default=None, help='Ruta alternativa del document.')

    def handle(self, *a, **o):
        ruta = o['doc'] or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
                os.path.dirname(os.path.abspath(__file__)))))), '..', DOC)
        ruta = os.path.normpath(ruta)
        if not os.path.exists(ruta):
            self.stderr.write(self.style.ERROR(f'No hi ha el document: {ruta}'))
            return

        with schema_context(o['schema']):
            from fhort.pom.grading_utils import (derive_rules_from_fitxa, normalitza_cm)
            from fhort.models_app.extraction_views import find_pom_master
            from fhort.models_app.models import (BaseMeasurement, Model, ModelGradingRule)
            from fhort.models_app.services import materialize_model_grading_rules_from_specs
            from fhort.pom.models import MeasurementLayer, SizeSystem

            fitxes = _carrega_parser().parse(open(ruta, encoding='utf-8').read(), normalitza_cm)
            self.stdout.write(f'Document: {len(fitxes)} fitxes · '
                              f'{sum(len(f["files"]) for f in fitxes)} files')

            # El model de referència del tenant dona la classificació (client, tipus, target):
            # el banc ha de graduar com els models de debò, no com una configuració exòtica.
            ref = (Model.objects.filter(codi_intern__startswith='BRW')
                   .exclude(codi_intern__startswith=PREFIX_CODI).first())
            if ref is None:
                self.stderr.write(self.style.ERROR('Cap model BRW de referència al tenant.'))
                return
            sistema = (SizeSystem.objects.filter(codi='ALPHA_EU_W').first()
                       or ref.size_system)

            if o['purga'] and not o['dry_run']:
                n, _ = Model.objects.filter(codi_intern__startswith=PREFIX_CODI).delete()
                self.stdout.write(self.style.WARNING(f'PURGA: {n} objecte(s) esborrat(s).'))

            no_resolts, resum = {}, []
            for fitxa in fitxes:
                codi_intern = f'{PREFIX_CODI}{fitxa["num"]:02d}'
                run = '·'.join(fitxa['run'])

                # ── els POMs de la fitxa, resolts contra el catàleg CANÒNIC ────────────────
                # Un codi que no resol es CENSA i se salta. Inventar-lo seria fabricar catàleg
                # per fer quadrar un banc, que és exactament el contrari del que un banc és.
                resoltes = []
                for f in fitxa['files']:
                    pm, _tipus, _conf = find_pom_master(f['codi'], f['descripcio'],
                                                        customer=ref.customer)
                    if pm is None:
                        no_resolts.setdefault(f['codi'], []).append(fitxa['num'])
                        continue
                    resoltes.append((f, pm))

                if o['dry_run']:
                    resum.append((codi_intern, fitxa['nom'], len(resoltes), 0, fitxa['te_grading']))
                    continue

                with transaction.atomic():
                    model, _ = Model.objects.update_or_create(
                        codi_intern=codi_intern,
                        defaults={
                            'nom_prenda': f'{PREFIX_NOM}{fitxa["nom"]}',
                            # Camps obligatoris del registre. El `sequencial` és el número de
                            # FITXA del document: així el codi del banc i el del document diuen
                            # el mateix i una fitxa nova no renumera les que ja hi són.
                            'codi_tenant': ref.codi_tenant,
                            'any': ref.any,
                            'temporada': ref.temporada,
                            'sequencial': fitxa['num'],
                            'collection': COLLECTION,
                            'customer': ref.customer,
                            'garment_type': ref.garment_type,
                            'garment_type_item': ref.garment_type_item,
                            'target': ref.target or 'WOMAN',
                            'fit_type': ref.fit_type,
                            'size_system': sistema,
                            'size_run_model': run,
                            'base_size_label': fitxa['base'],
                            # El banc NO hereta cap joc de regles del client: el que ha de
                            # mesurar la paritat són les regles DERIVADES DE LA FITXA, i un
                            # contenidor al darrere les taparia (el motor el llegeix quan la
                            # mare no té residents).
                            'grading_rule_set': None,
                        })

                    # ── les mesures de la talla BASE ──────────────────────────────────────
                    vistes = set()
                    for f, pm in resoltes:
                        base_val = f['valors'].get(fitxa['base'])
                        if base_val is None:
                            continue
                        # Dues files de la MATEIXA fitxa amb el mateix POM col·lapsarien a la
                        # mateixa cel·la: la primera mana i la segona es censa com a no resolta
                        # de fet (el document reutilitza codis entre seccions).
                        if pm.id in vistes:
                            no_resolts.setdefault(f'{f["codi"]} (dup→{pm.codi_client})', []).append(
                                fitxa['num'])
                            continue
                        vistes.add(pm.id)
                        BaseMeasurement.objects.update_or_create(
                            model=model, pom=pm, capa=MeasurementLayer.SLUG_DEFECTE,
                            instancia='', garment='',
                            defaults={'base_value_cm': base_val, 'origen': 'IMPORTED',
                                      'is_active': True, 'ordre': f['ordre'],
                                      'nom_fitxa': f['codi'][:20],
                                      'notes': f['descripcio'],
                                      # Les seccions del document, informades i sense
                                      # convertir-se en peces.
                                      'seccio': f['seccio'][:60]})

                    # ── les regles residents, NOMÉS si la fitxa gradua ────────────────────
                    n_regles = 0
                    if fitxa['te_grading']:
                        # ⚠️ NO S'ESCRIU CAP DERIVADOR NOU: es reusa el camí de l'import. I les
                        # regles surten dels VALORS PER TALLA, no de la columna de Δ del
                        # document —que a les fitxes 2 i 4 en són DUES i quina mana és
                        # precisament la pregunta oberta d'aquell document.
                        valors = {pm.id: f['valors'] for f, pm in resoltes
                                  if len(f['valors']) > 1}
                        avisos, bloqueigs, descartades = [], [], []
                        specs = derive_rules_from_fitxa(
                            run_document=fitxa['run'], base_size=fitxa['base'], valors=valors,
                            confirmed_pom_ids=list(valors), size_system=sistema,
                            avisos=avisos, bloqueigs=bloqueigs, descartades=descartades)
                        if specs:
                            materialize_model_grading_rules_from_specs(
                                model, specs, origen='IMPORTED', garment='')
                            n_regles = len(specs)
                        if bloqueigs:
                            self.stdout.write(self.style.WARNING(
                                f'  {codi_intern}: {len(bloqueigs)} bloqueig(s) de derivació '
                                f'(files incompletes) — regles no derivades per a aquestes.'))

                    resum.append((codi_intern, fitxa['nom'], len(vistes), n_regles,
                                  fitxa['te_grading']))

            self.stdout.write('')
            for codi, nom, n_bm, n_rules, grad in resum:
                self.stdout.write(
                    f'  {codi}  {(PREFIX_NOM + nom)[:38]:38} '
                    f'bm={n_bm:3}  regles={n_rules:3}  {"GRADUA" if grad else "base sola"}')

            tot_bm = sum(r[2] for r in resum)
            tot_rl = sum(r[3] for r in resum)
            self.stdout.write(self.style.SUCCESS(
                f'\n{len(resum)} models · {tot_bm} mesures base · {tot_rl} regles residents'))
            if no_resolts:
                self.stdout.write(self.style.WARNING(
                    f'\nCODIS NO RESOLTS (censats i saltats, mai inventats): {len(no_resolts)}'))
                for codi, usos in sorted(no_resolts.items()):
                    self.stdout.write(f'  · {codi:24} a les fitxes {sorted(set(usos))}')
