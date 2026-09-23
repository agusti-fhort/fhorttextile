"""REPARACIÓ 23/09, diagnosi 208 — Patró C.

Precedent: la consolidació fitting→base (`fitting.services.consolidate_base_from_fitting`)
escrivia cada línia mesurada i la derivava cap a les seves germanes EN EL MATEIX PAS, línia a
línia. Amb una sessió de tres instàncies del mateix POM rectificades a la vegada, la
propagació d'una podia trepitjar el valor acabat d'escriure d'una altra abans que li arribés
el torn: una instància amb mesura PRÒPIA podia quedar amb `origen='DERIVAT'` i un valor que no
era el que la modista havia mesurat. El fix (COMMIT 1, mateixa data) tanca el forat cap
endavant; aquesta comanda repara el que ja hagi quedat trepitjat cap enrere.

QUÈ TOCA, i NOMÉS AIXÒ: `BaseMeasurement` d'UN model amb `origen='DERIVAT'` per a les quals
existeix una `PieceFittingLine` (de QUALSEVOL fitting d'aquest model) de la MATEIXA
(pom, capa, instància, garment), a la talla base, amb `valor_real` informat (REJECTED NO
sembra, D-31.21 — és l'única exclusió; ni la desviació respecte de `valor_teoric` ni el
`decisio` buit exclouen res més, LLEI Agus 24/09: v. `consolidate_base_from_fitting`). Amb
més d'una línia candidata es tria la MÉS RECENT (data de sessió, després pk de
`PieceFitting`, després pk de línia) — la mateixa noció d'«última mesura vàlida» que
`consolidate_base_from_fitting`.

Proposa: `base_value_cm := valor_real de la línia`, `origen := 'FITTED'`. Cap altra fila es
toca — ni una BaseMeasurement que ja no sigui DERIVAT, ni una sense línia candidata.

Dry-run per defecte; només escriu amb --apply. IDEMPOTENT: una segona passada no troba res a
reparar (la fila ja no és DERIVAT) i no proposa cap canvi.

`models_app` és TENANT-only: invocar sempre amb `tenant_command` de django-tenants i
`--schema=<schema>`.

    venv/bin/python manage.py tenant_command repara_base_des_de_fitting --schema=fhort --model 208
        # dry-run: taula id · POM · instància · abans → després

    venv/bin/python manage.py tenant_command repara_base_des_de_fitting --schema=fhort --model 208 --apply
        # aplica, amb rastre a MeasurementChangeLog (motiu = aquesta capçalera)
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from fhort.fitting.models import PieceFittingLine
from fhort.models_app.models import BaseMeasurement, Model

MOTIU = 'REPARACIÓ 23/09, diagnosi 208 — trepitjada de consolidació multi-instància'


class Command(BaseCommand):
    help = ('Repara BaseMeasurement origen=DERIVAT que tinguin una línia de fitting MESURADA '
            'pròpia (mateix pom/capa/instància/garment, talla base) — v. capçalera del fitxer. '
            'Invocar sempre amb "manage.py tenant_command repara_base_des_de_fitting '
            '--schema=<schema> --model <id> [--apply]" — models_app és TENANT-only.')

    def add_arguments(self, parser):
        parser.add_argument('--model', type=int, required=True, help='id del Model.')
        parser.add_argument('--apply', action='store_true',
                            help='Escriu. Sense aquest flag: dry-run (només llista).')

    def _linia_candidata(self, bm, base_size):
        # LLEI Agus 24/09 — «mesurat» = valor_real present, tingui o no desviació ni decisio.
        # L'única exclusió que queda és REJECTED (D-31.21: «la presa no val, NO sembra res»).
        return (PieceFittingLine.objects
                .filter(piece_fitting__model_id=bm.model_id,
                        pom_id=bm.pom_id, capa=bm.capa, instancia=bm.instancia,
                        garment=bm.garment, size_label=base_size,
                        valor_real__isnull=False)
                .exclude(decisio=PieceFittingLine.DECISIO_REJECTED)
                .select_related('piece_fitting__session')
                .order_by('-piece_fitting__session__data', '-piece_fitting_id', '-id')
                .first())

    def _proposta(self, bm, base_size):
        """Retorna la línia candidata i el valor a escriure, o `(None, None)` si aquesta
        `BaseMeasurement` no és una fila a reparar (llei del guard: només DERIVAT amb mesura
        pròpia — mesurada, no necessàriament diferent del teòric)."""
        linia = self._linia_candidata(bm, base_size)
        if linia is None:
            return None, None
        if bm.base_value_cm is not None and abs(linia.valor_real - bm.base_value_cm) < 1e-6:
            return None, None  # ja hi és (idempotència: 2a passada = 0 canvis)
        return linia, linia.valor_real

    def handle(self, *args, **opts):
        model_id = opts['model']
        apply_ = opts['apply']

        model = Model.objects.filter(pk=model_id).first()
        if model is None:
            raise CommandError(f'Model id={model_id} no existeix en aquest schema.')
        base_size = (model.base_size_label or '').strip()
        if not base_size:
            raise CommandError(f'Model {model_id} sense base_size_label: no hi ha talla base '
                               f'contra la qual reparar.')

        candidats = (BaseMeasurement.objects
                    .filter(model=model, origen='DERIVAT')
                    .select_related('pom')
                    .order_by('pom_id', 'capa', 'instancia'))

        propostes = []
        for bm in candidats:
            linia, valor_nou = self._proposta(bm, base_size)
            if linia is None:
                continue
            propostes.append((bm, linia, valor_nou))

        head = 'APLICANT' if apply_ else 'DRY-RUN (cap escriptura)'
        self.stdout.write(self.style.WARNING(
            f'=== repara_base_des_de_fitting · model={model_id} ({model.codi_intern}) · '
            f'talla base={base_size} · {head} ==='))
        if not propostes:
            self.stdout.write('  (cap fila a reparar)')
            self.stdout.write('\nTotal: 0 fila(es).')
            return

        for bm, linia, valor_nou in propostes:
            self.stdout.write(
                f'  id={bm.pk} · POM={bm.pom.codi_client} · capa={bm.capa} · '
                f'instancia={bm.instancia or "—"} · abans={bm.base_value_cm} → '
                f'després={valor_nou} · font=línia {linia.pk} (sessió '
                f'{linia.piece_fitting.session_id}, {linia.piece_fitting.session.data})')
        self.stdout.write(f'\nTotal: {len(propostes)} fila(es).')

        if not apply_:
            self.stdout.write(self.style.WARNING('DRY-RUN: cap fila tocada. --apply per aplicar.'))
            return

        with transaction.atomic():
            for bm, linia, valor_nou in propostes:
                bm.base_value_cm = valor_nou
                bm.origen = 'FITTED'
                bm._fitting_ref = linia.piece_fitting.grading_version.size_fitting
                bm._motiu = f'{MOTIU} · font: línia {linia.pk} (sessió {linia.piece_fitting.session_id})'
                bm.save(update_fields=['base_value_cm', 'origen', 'updated_at'])
        self.stdout.write(self.style.SUCCESS(f'=== FET: {len(propostes)} fila(es) reparades ==='))
