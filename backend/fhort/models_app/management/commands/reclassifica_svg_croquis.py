"""BACKFILL S1.1 (ordre Agus 24/09, `DIAGNOSI_STAGING_NOMENCLATURA_CORPUS_FITXA.md` Bloc 4.1).

`save_model_file` ja no deixa entrar un `.svg` nou com a `ALTRES` (v. `services_fitxers.py`,
`_es_svg`), però el canvi no és retroactiu: cada `ModelFitxer` `.svg` pujat ABANS d'aquesta
peça es va quedar amb `tipus='ALTRES'` i, per tant, invisible al panell «Croquis i flats»
(`TIPUS_GEOMETRIA`, `TechSheetEditor.jsx:69`). Aquesta comanda reclassifica els que ja hi són.

QUÈ TOCA, i NOMÉS AIXÒ: `ModelFitxer` amb `tipus='ALTRES'` i extensió `.svg` (o
`mimetype='image/svg+xml'`) — mateix predicat `_es_svg` que `save_model_file`, cap criteri
nou. Cap fitxer amb `tipus` ja explícit (SKETCH_SVG o qualsevol altre) es toca. Cap ràster.

Dry-run per defecte; només escriu amb --apply. IDEMPOTENT: una segona passada no troba res
(les files ja no són `ALTRES`) i no proposa cap canvi.

`models_app` és TENANT-only: invocar sempre amb `tenant_command` de django-tenants i
`--schema=<schema>`.

    venv/bin/python manage.py tenant_command reclassifica_svg_croquis --schema=fhort
        # dry-run: llista per model (codi + nom) dels ModelFitxer que passarien a SKETCH_SVG

    venv/bin/python manage.py tenant_command reclassifica_svg_croquis --schema=fhort --apply
        # aplica el canvi de tipus, dins d'una única transacció
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from fhort.models_app.models import ModelFitxer
from fhort.models_app.services_fitxers import _es_svg


class Command(BaseCommand):
    help = ("Reclassifica a 'SKETCH_SVG' els ModelFitxer .svg que avui tenen tipus='ALTRES' "
            "(backfill S1.1). Invocar sempre amb \"manage.py tenant_command "
            "reclassifica_svg_croquis --schema=<schema> [--apply]\" — models_app és TENANT-only.")

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true',
                            help='Escriu. Sense aquest flag: dry-run (només llista).')

    def handle(self, *args, **opts):
        apply_ = opts['apply']

        candidats = (ModelFitxer.objects
                    .filter(tipus='ALTRES')
                    .select_related('model')
                    .order_by('model__codi_intern', 'nom_fitxer'))
        propostes = [f for f in candidats if _es_svg(f.nom_fitxer, f.mimetype)]

        head = 'APLICANT' if apply_ else 'DRY-RUN (cap escriptura)'
        self.stdout.write(self.style.WARNING(
            f'=== reclassifica_svg_croquis · {head} ==='))
        if not propostes:
            self.stdout.write('  (cap fitxer a reclassificar)')
            self.stdout.write('\nTotal: 0 fitxer(s).')
            return

        for f in propostes:
            self.stdout.write(
                f'  model={f.model.codi_intern} ({f.model.nom_prenda}) · '
                f'fitxer id={f.pk} · {f.nom_fitxer} · versió={f.versio} · '
                f'is_current={f.is_current} · ALTRES → SKETCH_SVG')
        self.stdout.write(f'\nTotal: {len(propostes)} fitxer(s).')

        if not apply_:
            self.stdout.write(self.style.WARNING('DRY-RUN: cap fila tocada. --apply per aplicar.'))
            return

        with transaction.atomic():
            for f in propostes:
                f.tipus = 'SKETCH_SVG'
                f.save(update_fields=['tipus'])
