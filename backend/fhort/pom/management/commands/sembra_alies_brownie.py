"""S4 · ELS 105 ÀLIES DE BROWNIE — el seu codi, el nostre POM.

El full `ALIES_BROWNIE` diu «codi de Brownie → codi de sistema», i Brownie segueix escrivint
el seu codi a les seves fitxes. Aquí es materialitza com a `CustomerPOMAlias` del client `BRW`.

🔑 **EL DESTÍ ES RESOL PEL LLIGAM DE S3, NO PEL CODI DEL TENANT.** L'àlies apunta a un
`POMMaster`, i el full només en dona el codi de SISTEMA: el POM es busca per
`pom_global__codi`, que és el que S3 acaba d'escriure. És l'única resolució que val als dos
entorns —les pks divergeixen i els codis de casa no són els del sistema— i, de passada, fa que
S4 no pugui córrer abans que S3 hagi fet la seva feina: sense lligam no hi ha destí.

  · **cap POM lligat** a aquell codi de sistema → es reporta i no es crea res;
  · **més d'un** → AMBIGU: es reporta i no es tria (triar seria inventar la dada);
  · un àlies que **ja existeix amb un altre destí** → es reporta i **no es mou** (create-only,
    literal del brief).

🚩 **ELS 24 ÀLIES LOS DEL LOT C QUEDEN FORA D'ABAST** (el brief ho diu): aquesta comanda només
toca el client `BRW` i no mira cap altre.

    manage.py sembra_alies_brownie --schema fhort                # DRY-RUN
    manage.py sembra_alies_brownie --schema fhort --no-dry-run   # escriu
"""
from django.core.management.base import CommandError

from fhort.pom.models import CustomerPOMAlias, POMMaster
from fhort.pom.sembra_v5.base import ComandaV5
from fhort.tasks.models import Customer

CLIENT = 'BRW'
#: La mateixa provinença que la sembra v4 va donar als 93 àlies que ja hi ha.
ORIGEN = 'DICCIONARI'


class Command(ComandaV5):
    help = 'S4 · sembra els 105 àlies de Brownie del r2 (create-only).'
    PAS = 'S4 · àlies de Brownie'
    ESPERAT = {'àlies al corpus': 105}

    def arguments_propis(self, parser):
        parser.add_argument('--schema', required=True,
                            help='Schema del tenant (sense default: pany P2 del 22/08).')

    def corre(self, opts):
        alies = self.corpus['alies']
        self.guarda('àlies al corpus', len(alies))

        creats = iguals = conflictes = sense_pom = ambigus = 0
        with self.transacciona(opts['schema']):
            client = Customer.objects.filter(codi=CLIENT).first()
            if client is None:
                raise CommandError(f'Customer {CLIENT!r} no existeix a `{opts["schema"]}`.')

            per_global = {}
            for p in POMMaster.objects.filter(actiu=True, pom_global__isnull=False
                                              ).select_related('pom_global'):
                per_global.setdefault(p.pom_global.codi, []).append(p)
            existents = {a.client_code: a for a in
                         CustomerPOMAlias.objects.filter(customer=client).select_related('pom')}

            for a in alies:
                candidats = per_global.get(a['codi_sistema'], [])
                if not candidats:
                    sense_pom += 1
                    self.excepcio(f'{a["codi_brownie"]!r} → {a["codi_sistema"]!r}: cap POM del '
                                  'tenant lligat a aquest global (S3 no l\'ha lligat). Sense '
                                  'àlies.')
                    continue
                if len(candidats) > 1:
                    ambigus += 1
                    self.excepcio(
                        f'🚨 {a["codi_brownie"]!r} → {a["codi_sistema"]!r}: AMBIGU, '
                        f'{len(candidats)} POMs hi estan lligats '
                        f'({[c.codi_client for c in candidats]}). No se\'n tria cap.')
                    continue
                pom = candidats[0]
                vell = existents.get(a['codi_brownie'])
                if vell is not None:
                    if vell.pom_id == pom.id:
                        iguals += 1
                    else:
                        conflictes += 1
                        self.excepcio(
                            f'🔒 {a["codi_brownie"]!r}: ja és àlies de '
                            f'{vell.pom.codi_client!r} i el r2 el vol a {pom.codi_client!r} '
                            '— es REPORTA i NO es mou.')
                    continue
                CustomerPOMAlias.objects.create(
                    customer=client, pom=pom, client_code=a['codi_brownie'],
                    client_description='', description_en=a['nom_en'] or '',
                    description_local='', language='', origen=ORIGEN, pendent_revisio=False)
                creats += 1

            self.guarda('àlies creats', creats)
            self.guarda('àlies ja correctes (idempotència)', iguals)
            self.guarda('àlies amb un altre destí (reportats, no moguts)', conflictes)
            self.guarda('àlies sense POM lligat al seu global', sense_pom)
            self.guarda('àlies AMBIGUS (>1 POM al mateix global)', ambigus)
            self.guarda(f'àlies totals de {CLIENT} al tenant',
                        CustomerPOMAlias.objects.filter(customer=client).count())

        self.diu(f'   creats {creats} · iguals {iguals} · conflictes {conflictes} '
                 f'· sense POM {sense_pom} · ambigus {ambigus}')
