"""DESVINCULA FILES APARELLADES PER description_match (16/09, DECISIONS.md).

El mode de fallada real del model 1216: una descripció de fitxa va matchejar per
`description_match` (MEDIUM, estratègia 3 de `find_pom_master`) contra el POM 'BR' —
ho podia fer perquè 'BR' encara era ACTIU quan es va importar. El dia que 'BR' es
retiri (COMMIT 1/4 ja fan que un import NOU no hi torni a caure en silenci), aquestes
files VELLES es queden apuntant a un POM que ja no hauria de rebre res nou.

Aquesta comanda les desfà: soft-desactiva (`is_active=False`, amb entrada a
`MeasurementChangeLog` — el mateix mecanisme que la poda de W5) les
`BaseMeasurement` d'UN model que apunten al POM indicat (`--pom`, per `codi_client`)
— o, si no se'n dona cap, a QUALSEVOL POM amb `nom_client` buit (el conjunt general
vulnerable a l'estratègia 3 abans del fix). RES S'ESBORRA: `nom_fitxa` i `notes`
(la descripció original del document) es conserven intactes — és la memòria que calia
per re-resoldre-les bé al pròxim import.

Sense --model: només CENS (recompte per model, cap escriptura) — per saber ABANS
de triar un model quins en són afectats.

Dry-run per defecte; només escriu amb --apply.

    venv/bin/python manage.py desvincula_description_match --pom BR
        # CENS: quants models tenen files apuntant a BR (o a nom buit si no hi ha --pom)

    venv/bin/python manage.py desvincula_description_match --model 1216 --pom BR
        # dry-run: llista les files del model 1216 que apunten a BR

    venv/bin/python manage.py desvincula_description_match --model 1216 --pom BR --apply
        # les desactiva (conservant nom_fitxa/notes), amb rastre a MeasurementChangeLog
"""
import datetime

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Count

from fhort.models_app.models import BaseMeasurement, Model
from fhort.pom.models import POMMaster


class Command(BaseCommand):
    help = ('Desvincula (soft, sense esborrar) les BaseMeasurement enganxades per '
            'description_match a un POM concret o a qualsevol POM amb nom buit.')

    def add_arguments(self, parser):
        parser.add_argument('--model', type=int, default=None,
                            help='id del Model. Sense aquest flag: només CENS per model.')
        parser.add_argument('--pom', default=None,
                            help='codi_client del POM sospitós (p.ex. BR). Sense aquest '
                                 'flag: qualsevol POM amb nom_client buit.')
        parser.add_argument('--since', default=None,
                            help='AAAA-MM-DD — només files creades des d\'aquesta data.')
        parser.add_argument('--apply', action='store_true',
                            help='Escriu (desactiva). Sense aquest flag: només llista.')

    def _poms_sospitosos(self, pom_codi):
        if pom_codi:
            poms = list(POMMaster.objects.filter(codi_client__iexact=pom_codi))
            if not poms:
                raise CommandError(f'Cap POM amb codi_client «{pom_codi}» en aquest schema.')
            return poms
        return list(POMMaster.objects.filter(nom_client=''))

    def _since_date(self, since_str):
        if not since_str:
            return None
        try:
            return datetime.datetime.strptime(since_str, '%Y-%m-%d').date()
        except ValueError:
            raise CommandError(f'--since ha de ser AAAA-MM-DD, rebut: {since_str!r}')

    def handle(self, *args, **opts):
        model_id = opts['model']
        pom_codi = opts['pom']
        since = self._since_date(opts['since'])
        apply_ = opts['apply']

        poms = self._poms_sospitosos(pom_codi)
        qs = BaseMeasurement.objects.filter(pom__in=poms, is_active=True)
        if since:
            qs = qs.filter(created_at__date__gte=since)

        criteri = (f'pom={pom_codi}' if pom_codi else 'pom amb nom_client buit')
        criteri += (f' · des de {since}' if since else '')

        if not pom_codi:
            # 🚨 SENSE --pom el criteri és «qualsevol POM amb nom_client buit», que des del
            # 23/08 és l'ESTAT NORMAL de 103 dels 144 POMs actius de fhort (POMs lligats al
            # catàleg canònic, no un símptoma). Sense --since per acotar-ho a una importació
            # concreta, --apply en aquest mode desactivaria mesures BONES a l'engròs.
            self.stdout.write(self.style.ERROR(
                '⚠️  SENSE --pom: el criteri és "qualsevol POM amb nom buit", que és l\'estat '
                'NORMAL del catàleg (no un símptoma). Acota amb --pom <codi> o, com a mínim, '
                '--since <data de la importació sospitosa> abans de --apply.'))

        # ── CENS (sense --model): NOMÉS RECOMPTE, MAI ESCRIPTURA ──────────────────────────
        if model_id is None:
            self.stdout.write(self.style.WARNING(
                f'=== desvincula_description_match · CENS · {criteri} ==='))
            per_model = (qs.values('model_id', 'model__codi_intern')
                        .annotate(n=Count('id')).order_by('-n'))
            total = 0
            for row in per_model:
                self.stdout.write(
                    f'  model {row["model_id"]} ({row["model__codi_intern"]}) · '
                    f'{row["n"]} fila(es)')
                total += row['n']
            if not total:
                self.stdout.write('  (cap fila)')
            self.stdout.write(f'\nTotal: {total} fila(es) · cap escriptura (cens).')
            return

        model = Model.objects.filter(pk=model_id).first()
        if model is None:
            raise CommandError(f'Model id={model_id} no existeix en aquest schema.')

        files = list(qs.filter(model=model).select_related('pom').order_by('id'))

        head = 'DRY-RUN (cap escriptura)' if not apply_ else 'APLICANT'
        self.stdout.write(self.style.WARNING(
            f'=== desvincula_description_match · model={model_id} ({model.codi_intern}) · '
            f'{criteri} · {head} ==='))
        for bm in files:
            self.stdout.write(
                f'  fila id={bm.pk} · nom_fitxa={bm.nom_fitxa!r} · pom={bm.pom.codi_client} '
                f'· valor={bm.base_value_cm} · creada={bm.created_at:%Y-%m-%d}')
        if not files:
            self.stdout.write('  (cap fila)')
        self.stdout.write(f'\nTotal: {len(files)} fila(es).')

        if not apply_:
            self.stdout.write(self.style.WARNING('DRY-RUN: cap fila tocada. --apply per aplicar.'))
            return

        with transaction.atomic():
            for bm in files:
                bm.is_active = False
                bm._desactivat = True
                bm._motiu = (f'desvincula_description_match: pom={bm.pom.codi_client} '
                            f'torna a pendent, nom_fitxa/descripció conservats')
                bm.save(update_fields=['is_active'])
        self.stdout.write(self.style.SUCCESS(f'=== FET: {len(files)} fila(es) desactivades ==='))
