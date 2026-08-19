"""F1 · Sembra del catàleg POM de Brownie v3 (full CATALEG de BROWNIE_CATALEG_POM_v3.xlsx).

🔑 **EL CRITERI (Agus, 05/08).** El v3 no importa `pom_id`: importa NOM + GRADING +
ESTRUCTURA i els casa contra el que staging ja té. La columna `pom_id` del full és
traçabilitat de PROD i **no s'escriu mai**. Cap CREATE amb un pk importat.
La taula de resolució viu a `fhort/pom/seed_data/brownie_cataleg_v3.py`.

Què fa cada codi, per ordre:

  **D1 · UPDATE existent** — l'àlies viu de Brownie ja apunta al POM bo. S'hi actualitza el
  nom. La identitat NO es toca.

  **D2 · el nom canònic és intocable si el POM és compartit** — `POMMaster` és el catàleg del
  TENANT i LOSAN hi entra amb 240 àlies. Si un altre client fa servir el POM, l'etiqueta de
  Brownie va a `CustomerPOMAlias.description_en` i `nom_client` no es toca. Un concepte
  físic, un POM, N àlies de client.

  **D3 · àlies sobre POM existent** — el codi no té àlies però el concepte ja té POM (sovint
  arribat per LOSAN). Es carrega l'àlies a sobre. NO s'encunya.

  **REPUNTS** — àlies viu enganxat a un POM que no és el seu concepte, amb destí correcte ja
  existent. Cadascun té acta al seu fitxer; no se'n fa cap altre.

  **D4 · ENCUNYAR** — no existeix enlloc. **Aquesta comanda NO n'encunya cap**: els llista i
  prou. Encunyar és l'única operació que afegeix identitats al catàleg del tenant i té el seu
  repàs abans (llei del brief).

El GRADING (els Δ del full) NO s'escriu aquí: és F4, el ruleset BRW-CATALEG-v3. F1 deixa el
catàleg i la nomenclatura; F4 hi penja les regles.

Idempotent: `update_or_create` per clau natural, cap delete. --dry-run per defecte.

    python manage.py seed_brownie_cataleg                # DRY-RUN
    python manage.py seed_brownie_cataleg --no-dry-run   # escriu (mai encunya)
"""
from pathlib import Path

import openpyxl
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django_tenants.utils import schema_context

from fhort.pom.models import CustomerPOMAlias, POMMaster
from fhort.pom.seed_data.brownie_cataleg_v3 import (CODI_CATALEG, ENCUNYAR, REPUNTS,
                                                    RESOLUCIO, SENSE_DEFINICIO,
                                                    caixa_de_frase)
from fhort.tasks.models import Customer

XLSX = Path('/var/www/ftt-staging/docs/BROWNIE_CATALEG_POM_v3.xlsx')
CUSTOMER_CODI = 'BRW'
TENANT = 'fhort'


def llegir_full(path: Path) -> list[dict]:
    """Els 119 codis del full CATALEG. Les files de secció i de llegenda no hi entren.

    El full és la FONT i viu fora de git (untracked, per decisió del tram): es llegeix cada
    vegada en comptes de copiar-lo a una constant, perquè una còpia és una segona veritat que
    es desincronitza el dia que la Montse en toca una fila.
    """
    if not path.exists():
        raise CommandError(f'No hi ha el full: {path}')
    ws = openpyxl.load_workbook(path, data_only=True)['CATALEG']
    files = []
    for r in ws.iter_rows(min_row=2, values_only=True):
        codi, nom, pid, logica = r[0], r[1], r[2], r[3]
        if codi is None:
            continue
        # Files de SECCIÓ (només la 1a cel·la) i de llegenda de colors: no són codis.
        if nom is None and logica is None:
            continue
        if str(codi).startswith(('Groc', 'Verd', 'Rosa')):
            continue
        files.append({
            'codi': str(codi).strip(),
            # CAIXA DE FRASE, sempre (llei del brief). El full arrossega noms en CAIXA ALTA
            # de la nomenclatura vella; escriure'ls tal qual no seria «no tocar-los», seria
            # ENMAJUSCULAR-NE 28 que avui ja estan ben escrits («Skirt length» → «SKIRT
            # LENGTH»). Els acrònims del sector (CF, CB, HPS…) es conserven.
            'nom': caixa_de_frase(str(nom).strip()),
            'nom_full': str(nom).strip(),
            # Es llegeix NOMÉS per poder-lo contrastar a l'informe. Mai s'escriu.
            'pid_prod': None if pid in (None, '—') else int(pid),
            'logica': str(logica).strip(),
        })
    return files


class Command(BaseCommand):
    help = 'F1 · Sembra el catàleg POM de Brownie v3 (resol per concepte, mai pel pom_id del full).'

    def add_arguments(self, parser):
        parser.add_argument('--no-dry-run', action='store_true')
        parser.add_argument('--schema', default=TENANT)
        parser.add_argument('--xlsx', default=str(XLSX))
        parser.add_argument('--encunyar', action='store_true',
                            help='Crea els POMs de D4. Sense això només els llista.')

    def handle(self, *args, **opts):
        dry = not opts['no_dry_run']
        schema = opts['schema']
        head = 'DRY-RUN (cap escriptura)' if dry else 'ESCRIVINT'
        self.stdout.write(self.style.WARNING(
            f'=== seed_brownie_cataleg · schema={schema} · {head} ==='))

        files = llegir_full(Path(opts['xlsx']))
        self.stdout.write(f'  full: {len(files)} codis\n')

        noms_pom = noms_alias = alies_nous = repuntats = encunyats = 0
        d4, sense_def, protegits, canvis = [], [], [], []

        with schema_context(schema), transaction.atomic():
            brw = Customer.objects.filter(codi=CUSTOMER_CODI).first()
            if not brw:
                raise CommandError(f'Customer {CUSTOMER_CODI} no existeix a {schema}.')

            al = {a.client_code: a for a in
                  CustomerPOMAlias.objects.filter(customer=brw).select_related('pom')}
            # Quins POMs fa servir algú que no sigui Brownie → nom canònic intocable (D2).
            compartits = set(CustomerPOMAlias.objects.exclude(customer=brw)
                             .values_list('pom_id', flat=True))

            for f in files:
                codi, nom = f['codi'], f['nom']

                if codi in ENCUNYAR:
                    if not opts['encunyar']:
                        d4.append((codi, nom, f['logica'], ENCUNYAR[codi]))
                        continue
                    # L'ENCUNYAMENT. `codi_client` és el codi de Brownie tret que ja estigui
                    # ocupat (v. CODI_CATALEG); `pom_global=None` i `pendent_revisio=True`
                    # perquè un POM nascut d'un catàleg de client és una PROPOSTA fins que
                    # algú el promou a canònic — la mateixa llei que governa
                    # `MeasurementLayer.is_system` i `CustomerPOMAlias.pendent_revisio`.
                    pom, creat = POMMaster.objects.get_or_create(
                        codi_client=CODI_CATALEG.get(codi, codi), nom_client=nom,
                        defaults={'actiu': True, 'pendent_revisio': True,
                                  'origen_import': 'BRW-CATALEG-v3'},
                    )
                    encunyats += int(creat)
                    if creat:
                        vell = al[codi].pom_id if codi in al and al[codi].pom_id else None
                        canvis.append(
                            f'  🆕 {codi:5} pom {pom.id} «{nom}» (codi_cataleg '
                            f'{pom.codi_client!r})'
                            + (f' · l\'àlies deixa {vell}' if vell else ''))

                # ⚠️ `elif`, no `if`: un codi que s'acaba d'encunyar ja té el seu POM i no ha
                # de tornar a passar per la cadena de resolució — hi trobaria l'àlies VELL
                # (el de G1 a 453, el d'U a 439…) i el POM nou quedaria orfe el mateix segon
                # de néixer.
                elif codi in REPUNTS:
                    pom_id, vell, motiu = REPUNTS[codi]
                    pom = POMMaster.objects.filter(pk=pom_id).first()
                    if not pom:
                        raise CommandError(f'REPUNTS[{codi}] → pom {pom_id} no existeix.')
                    repuntats += 1
                    canvis.append(f'  ↪ {codi:5} REPUNTAT {vell} → {pom_id} · {motiu}')
                elif codi in al and al[codi].pom_id:
                    pom = al[codi].pom
                elif codi in RESOLUCIO:
                    pom_id = RESOLUCIO[codi][0]
                    pom = POMMaster.objects.filter(pk=pom_id).first()
                    if not pom:
                        raise CommandError(f'RESOLUCIO[{codi}] → pom {pom_id} no existeix.')
                else:
                    sense_def.append((codi, nom))
                    continue

                # D2 — el nom canònic només es toca si el POM és NOMÉS de Brownie.
                if pom.id in compartits:
                    protegits.append((codi, pom.id, pom.nom_client, nom))
                elif pom.nom_client != nom:
                    canvis.append(f'  ✎ {codi:5} pom {pom.id} «{pom.nom_client}» → «{nom}»')
                    pom.nom_client = nom
                    pom.save(update_fields=['nom_client'])
                    noms_pom += 1

                # L'àlies sempre porta l'etiqueta de Brownie: és la que el matcher llegeix i
                # la que fa que el nom del client no depengui de si el POM és compartit.
                obj, creat = CustomerPOMAlias.objects.update_or_create(
                    customer=brw, client_code=codi,
                    defaults={'pom': pom, 'description_en': nom, 'origen': 'DICCIONARI'},
                )
                alies_nous += int(creat)
                noms_alias += int(not creat)

            for codi, motiu in SENSE_DEFINICIO.items():
                sense_def.append((codi, motiu))

            if dry:
                transaction.set_rollback(True)

        for c in canvis:
            self.stdout.write(c)

        self.stdout.write(
            f'\n── RECOMPTE ──\n'
            f'  àlies de Brownie creats: {alies_nous} · actualitzats: {noms_alias}\n'
            f'  noms de POMMaster actualitzats: {noms_pom} · repunts: {repuntats}\n'
            f'  POMs ENCUNYATS (D4): {encunyats}\n'
            f'  noms NO tocats per POM compartit (D2): {len(protegits)}')

        self.stdout.write(f'\n── D2 · nom canònic protegit (l\'etiqueta va a l\'àlies): '
                          f'{len(protegits)} ──')
        for codi, pid, actual, vol in protegits[:8]:
            self.stdout.write(f'  {codi:5} pom {pid} es queda «{actual}» · Brownie el diu «{vol}»')
        if len(protegits) > 8:
            self.stdout.write(f'  … i {len(protegits) - 8} més')

        self.stdout.write(self.style.WARNING(
            f'\n── D4 · A ENCUNYAR — NO SE N\'HA CREAT CAP: {len(d4)} ──'))
        for codi, nom, logica, motiu in d4:
            self.stdout.write(f'  {codi:5} «{nom}» [{logica}]\n         {motiu}')

        self.stdout.write(self.style.ERROR(
            f'\n── SENSE DEFINICIÓ (no encunyables): {len(sense_def)} ──'))
        for codi, motiu in sense_def:
            self.stdout.write(f'  {codi}: {motiu}')

        self.stdout.write(self.style.SUCCESS(f'\n=== FET ({head}) ==='))
