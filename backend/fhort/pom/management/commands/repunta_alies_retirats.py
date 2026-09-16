"""REPUNTA ELS ÀLIES QUE RECLAMEN UN POM RETIRAT (16/09, DECISIONS.md).

`find_pom_master` (COMMIT 1) ja no salta en silenci un àlies que apunta a un POM inactiu:
el deixa pendent amb l'hereu com a suggeriment, si n'hi ha. Aquesta comanda és la neteja
de FONS: per als àlies que JA tenen hereu clar, repunta'ls d'una vegada perquè deixin de
caure a pendents a cada importació.

🔄 CRITERI D'HEREU (revisió 16/09, el mateix que `find_pom_master`): un POM ACTIU amb
`codi_client` IGUAL al `client_code` de l'ÀLIES (case-insensitive) — no al `codi_client`
del POM retirat (que és únic per constraint de BD i mai el pot compartir cap altre POM,
actiu o no), ni al `pom_global`. El nom de l'hereu pot ser buit ("mana el canònic",
23/08): no es filtra per `nom_client`.

Dry-run per defecte (LLISTA); només escriu amb --apply.

    venv/bin/python manage.py repunta_alies_retirats --customer BRW            # dry-run
    venv/bin/python manage.py repunta_alies_retirats --customer BRW --apply    # escriu
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from fhort.pom.models import CustomerPOMAlias, POMMaster
from fhort.tasks.models import Customer

#: Marca l'àlies com a repuntat per aquesta comanda — deixa rastre de LA CAUSA (no és un
#: aprenentatge ni una importació, és una reparació de catàleg) i `actualitzat_at` (auto_now)
#: en dona la data.
ORIGEN_REPUNT = 'REPUNT_v5'


class Command(BaseCommand):
    help = ('Repunta els àlies d\'un client que reclamen un POM retirat cap al seu hereu '
            '(POM actiu amb codi_client == client_code de l\'àlies). Dry-run per defecte.')

    def add_arguments(self, parser):
        parser.add_argument('--customer', required=True,
                            help='Codi del client (Customer.codi), p.ex. BRW.')
        parser.add_argument('--apply', action='store_true',
                            help='Escriu. Sense aquest flag: només llista (dry-run).')

    def handle(self, *args, **opts):
        codi_client = opts['customer']
        apply_ = opts['apply']

        customer = Customer.objects.filter(codi=codi_client).first()
        if customer is None:
            raise CommandError(f'Client «{codi_client}» no existeix en aquest schema.')

        alies_retirats = (CustomerPOMAlias.objects
                          .filter(customer=customer, pom__isnull=False, pom__actiu=False)
                          .select_related('pom')
                          .order_by('id'))

        files = []
        for a in alies_retirats:
            hereu = (POMMaster.objects
                    .filter(codi_client__iexact=a.client_code, actiu=True)
                    .exclude(pk=a.pom_id).order_by('id').first())
            if hereu is None:
                accio = 'SENSE HEREU'
            elif CustomerPOMAlias.objects.filter(
                    customer=customer, client_code=a.client_code, pom=hereu).exclude(pk=a.pk).exists():
                # Ja hi ha una fila (customer, client_code, hereu): repuntar duplicaria
                # exactament el que `find_pom_master` ja hauria de veure com a contradicció
                # o com a àlies normal — no toquem res, es queda per revisió manual.
                accio = 'JA REPUNTAT (fila bessona existent)'
            else:
                accio = 'REPUNTAR'
            files.append((a, hereu, accio))

        head = ('DRY-RUN (cap escriptura)' if not apply_ else 'APLICANT')
        self.stdout.write(self.style.WARNING(
            f'=== repunta_alies_retirats · client={codi_client} · {head} ==='))
        self.stdout.write(f'{"codi":<20} {"POM retirat":<28} {"hereu":<28} acció')
        for a, hereu, accio in files:
            retirat_txt = f'{a.pom.codi_client} · {a.pom.nom_client or "(sense nom)"}'[:28]
            hereu_txt = (f'{hereu.codi_client} · {hereu.nom_client or "(sense nom)"}'[:28]
                        if hereu else '—')
            self.stdout.write(f'{a.client_code:<20} {retirat_txt:<28} {hereu_txt:<28} {accio}')

        n_repuntats = sum(1 for _, _, accio in files if accio == 'REPUNTAR')
        n_sense_hereu = sum(1 for _, _, accio in files if accio == 'SENSE HEREU')
        n_ja = sum(1 for _, _, accio in files if accio.startswith('JA REPUNTAT'))
        self.stdout.write(
            f'\nTotal: {len(files)} · a repuntar: {n_repuntats} · sense hereu: {n_sense_hereu} '
            f'· ja repuntats/bessons: {n_ja}')

        if not apply_:
            self.stdout.write(self.style.WARNING('DRY-RUN: cap fila escrita. --apply per aplicar.'))
            return

        ara = timezone.now()
        with transaction.atomic():
            for a, hereu, accio in files:
                if accio != 'REPUNTAR':
                    continue
                a.pom = hereu
                a.origen = ORIGEN_REPUNT
                a.editat_at = ara
                a.save(update_fields=['pom', 'origen', 'editat_at', 'actualitzat_at'])
        self.stdout.write(self.style.SUCCESS(f'=== FET: {n_repuntats} àlies repuntats ==='))
