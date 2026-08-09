"""Fusiona un POMMaster DUPLICAT dins del seu CANÒNIC i, si queda net, l'esborra.

── PER QUÈ EXISTEIX (Agus, QA 09/08 · defecte 5) ─────────────────────────────────────────────
El model 1320 va néixer un POM propi `BRW-EK` («Neck width edge to edge») que duplica l'`EK` del
catàleg («Neck width»). La tècnica el va treure de la taula del model, però la fitxa seguia dient
«Té 2 usos: es pot desactivar, no esborrar». Els dos usos eren reals i no eren cap misteri:

  · `BaseMeasurement` (PROTECT) — la mesura del 1320 amb el valor 17, en estat `is_active=False`.
    **Treure una mesura de la taula la DESACTIVA, no la esborra**, i el cens de `pom_us_view`
    compta files, no files vives: per això el POM seguia retingut per una fila que la pantalla ja
    no ensenyava. La divergència entre el gest («l'he tret») i el gate («encara hi és») és el que
    feia que el defecte semblés un bloqueig sense causa.
  · `MeasurementChangeLog` (PROTECT) — el rastre append-only d'haver-hi entrat el 17.

I un tercer que NO bloquejava però que hauria caigut amb el POM: el `CustomerPOMAlias` (CASCADE)
que dona a Brownie el codi de client `EK`.

── QUÈ FA, I QUÈ NO ──────────────────────────────────────────────────────────────────────────
NO esborra les dues files que bloquejaven: **les RE-APUNTA al canònic**. La mesura que la tècnica
va entrar és una dada seva i el rastre del canvi és auditoria; el que sobra és el POM duplicat, no
el 17 ni la seva història. Un cop mogudes, el duplicat es queda amb zero referències i llavors sí
que es pot esborrar per la porta legítima —la mateixa que `pom_us_view` vigila—, no a la força.

El re-apuntament va per `.update()` fila a fila, mai `save()`: `MeasurementChangeLog` és
append-only i `BaseMeasurement` té `unique(model, pom, capa, instancia)`. Un `IntegrityError` vol
dir que el canònic JA té aquella fila (la mesura ja existia a les dues bandes): es compta com a
col·lisió i la fila es queda al duplicat, que llavors no s'esborrarà. Mai es perd res en silenci.

`--reactiva-mesures` torna les mesures mogudes a `is_active=True`. No és el defecte per defecte:
només té sentit quan el que es vol és justament el que l'Agus demana aquí —que el valor que va
entrar torni a ser visible, ara sota el POM canònic.

Les relacions que es mouen són les MATEIXES que la fusió del catàleg LOSAN
(`consolidate_pom_los.FUSIO_MOVE_RELS`), importades d'allà i no re-escrites: el dia que una FK
nova entri a la llista, les dues fusions se n'assabenten alhora.

DRY-RUN PER DEFECTE. En dry-run tot s'executa igual i l'atomic exterior fa rollback, de manera
que les col·lisions es detecten de veritat en comptes de predir-se.

    python manage.py fusiona_pom_duplicat --duplicat BRW-EK --canonic EK
    python manage.py fusiona_pom_duplicat --duplicat BRW-EK --canonic EK \
        --reactiva-mesures --esborra --no-dry-run
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, transaction
from django_tenants.utils import schema_context

from fhort.pom.models import CustomerPOMAlias, POMMaster
from fhort.pom.seed_data.consolidate_pom_los import FUSIO_MOVE_RELS


class Command(BaseCommand):
    help = 'Fusiona un POMMaster duplicat dins del seu canònic i, si queda net, l\'esborra.'

    def add_arguments(self, p):
        p.add_argument('--duplicat', required=True, help='codi_client del POM que sobra')
        p.add_argument('--canonic', required=True, help='codi_client del POM que es queda')
        p.add_argument('--schema', default='fhort')
        p.add_argument('--reactiva-mesures', action='store_true',
                       help='torna les BaseMeasurement mogudes a is_active=True')
        p.add_argument('--esborra', action='store_true',
                       help='esborra el duplicat si queda amb zero referències')
        p.add_argument('--no-dry-run', action='store_true')

    def handle(self, *a, **o):
        self.dry = not o['no_dry_run']
        cap = 'DRY-RUN' if self.dry else 'ESCRIVINT'
        self.stdout.write(self.style.WARNING(
            f"=== fusiona_pom_duplicat · {o['duplicat']} → {o['canonic']} · {cap} ==="))
        try:
            with schema_context(o['schema']), transaction.atomic():
                self._fes(o)
                if self.dry:
                    raise _Rollback()
        except _Rollback:
            self.stdout.write(self.style.WARNING(
                '\nDRY-RUN: cap escriptura desada. Repeteix-ho amb --no-dry-run.'))

    # ──────────────────────────────────────────────────────────────────────────────────────
    def _resol(self, codi):
        qs = POMMaster.objects.filter(codi_client=codi)
        if qs.count() != 1:
            raise CommandError(f'«{codi}» no resol a un POM únic ({qs.count()} coincidències). '
                               f'Cap fusió a cegues.')
        return qs.first()

    def _refs(self, pom):
        """Referències entrants VIVES, per relació. Mateixa aritmètica que `pom_us_view`."""
        out = {}
        for rel in POMMaster._meta.related_objects:
            acc = rel.get_accessor_name()
            n = getattr(pom, acc).count()
            if n:
                out[acc] = n
        return out

    def _fes(self, o):
        dup, can = self._resol(o['duplicat']), self._resol(o['canonic'])
        if dup.pk == can.pk:
            raise CommandError('El duplicat i el canònic són el mateix POM.')
        # El canònic ha de ser el que es queda: si el duplicat és de sistema i el canònic no,
        # la fusió va al revés del que toca i val més aturar-se que endreçar-ho malament.
        if dup.pom_global_id is not None and can.pom_global_id is None:
            raise CommandError(f'El duplicat {dup.codi_client!r} és DE SISTEMA i el canònic '
                               f'{can.codi_client!r} no. Revisa quin és quin.')

        self.stdout.write(f'  duplicat  id{dup.id} {dup.codi_client!r} "{dup.nom_client}" '
                          f'(global={dup.pom_global_id})')
        self.stdout.write(f'  canònic   id{can.id} {can.codi_client!r} "{can.nom_client}" '
                          f'(global={can.pom_global_id})')
        abans = self._refs(dup)
        self.stdout.write(f'  referències abans: {abans or "cap"}')

        mogudes, colls, mesures = 0, [], []
        # L'àlies primer: és CASCADE, o sigui que és el que s'endurien per davant si esborréssim
        # sense mirar. Si el canònic ja en té un per al mateix client, el del duplicat sobra.
        for al in list(CustomerPOMAlias.objects.filter(pom=dup)):
            xoca = CustomerPOMAlias.objects.filter(
                customer_id=al.customer_id, client_code=al.client_code).exclude(pk=al.pk).exists()
            if xoca:
                CustomerPOMAlias.objects.filter(pk=al.pk).delete()
                self.stdout.write(f'    àlies {al.client_code!r} (client {al.customer_id}) '
                                  f'JA existeix al canònic → esborrat el del duplicat')
            else:
                CustomerPOMAlias.objects.filter(pk=al.pk).update(pom=can)
                self.stdout.write(f'    àlies {al.client_code!r} (client {al.customer_id}) '
                                  f'→ re-apuntat al canònic')

        for rel in FUSIO_MOVE_RELS:
            for obj in list(getattr(dup, rel).all()):
                try:
                    with transaction.atomic():
                        type(obj).objects.filter(pk=obj.pk).update(pom=can)
                    mogudes += 1
                    if rel == 'base_measurements':
                        mesures.append(obj.pk)
                except IntegrityError:
                    colls.append(f'{rel}#{obj.pk}')

        # GradedSpec és sortida pura del motor i es regenera: moure-la seria moure un càlcul.
        n_gs = dup.graded_specs.count()
        if n_gs:
            dup.graded_specs.all().delete()
            self.stdout.write(f'    graded_specs ✗{n_gs} (output del motor, regenerable)')

        if mesures and o['reactiva_mesures']:
            BM = type(can).base_measurements.rel.related_model
            n = BM.objects.filter(pk__in=mesures, is_active=False).update(is_active=True)
            self.stdout.write(f'    {n} mesura/es reactivada/es (is_active=True) sobre el canònic')

        self.stdout.write(f'  mogudes={mogudes} col·lisions={len(colls)} '
                          + (f'→ {colls}' if colls else ''))

        despres = self._refs(dup)
        self.stdout.write(f'  referències després: {despres or "cap"}')

        if despres:
            self.stdout.write(self.style.WARNING(
                '  El duplicat encara té referències: NO s\'esborra. Resol les col·lisions.'))
            return
        if dup.pom_global_id is not None:
            self.stdout.write(self.style.WARNING(
                '  POM de sistema: es desactiva, mai s\'esborra.'))
            POMMaster.objects.filter(pk=dup.pk).update(actiu=False)
            return
        if not o['esborra']:
            self.stdout.write('  Net i esborrable. Passa --esborra per fer-ho.')
            return
        POMMaster.objects.filter(pk=dup.pk).delete()
        self.stdout.write(self.style.SUCCESS(
            f'  ✓ duplicat id{dup.id} {dup.codi_client!r} ESBORRAT.'))


class _Rollback(Exception):
    """Avorta l'atomic exterior en dry-run (l'escriptura s'ha fet i es desfà)."""
