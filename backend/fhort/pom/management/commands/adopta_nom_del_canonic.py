"""S8 · EL NOM CANÒNIC MANA — buida el nom propi dels POMs lligats al catàleg del sistema.

⚖️ **DECISIÓ D'AGUS, 23/08 (tancament de la sembra v5):** *el nom del tenant que duplica o
divergeix del canònic deixa de manar; el POM lligat mostra el canònic del global, amb les
seves traduccions.*

Per què fa falta una comanda i no n'hi ha prou amb sembrar: `nomenclatura.noms_de` diu, i ho
diu al seu docstring, que `nom_ca` = descripció LOCAL de l'àlies **>** `nom_client` del tenant
**>** `nom_ca` del global. Els 144 POMs de `fhort` tenen `nom_client` propi —en anglès, heretat
de Brownie—, i per això **el català i el castellà del v5 no arribaven mai a la fitxa** encara
que la sembra els hagués escrit. Buidar el nom propi és el que fa caure la cascada al canònic.

🔒 **ÉS UN REBATEIG, I PORTA LA PORTA QUE ELS REBATEIGS PORTEN** (tren de panys, 22/08):
`--buida-el-nom-del-tenant` és **obligatori per escriure**. Sense el flag, la comanda mesura,
reporta i no toca res —ni amb `--no-dry-run`—, perquè un rebateig silenciós és exactament el
que aquell tren va tancar.

**Què NO toca:**
  · els POMs **no lligats** (sense `pom_global`) — el seu nom és l'únic que tenen;
  · els POMs **sobirans** (`separat_de_global`) — el tenant ja va decidir que no parlen amb el
    canònic, i aquesta comanda no els contradiu;
  · el **codi** del tenant (`codi_client`) i els **àlies de Brownie**, que són vocabulari del
    client i no es toquen mai;
  · l'**arxiu** (`actiu=False`).

    manage.py adopta_nom_del_canonic --schema fhort                  # mesura i reporta
    manage.py adopta_nom_del_canonic --schema fhort --no-dry-run \\
        --buida-el-nom-del-tenant                                    # escriu
"""
from django.core.management.base import CommandError

from fhort.pom.models import POMMaster
from fhort.pom.nomenclatura import noms_de
from fhort.pom.sembra_v5.base import ComandaV5


class Command(ComandaV5):
    help = 'S8 · buida el nom propi dels POMs lligats perquè mani el canònic del global.'
    PAS = 'S8 · el nom canònic mana'

    def arguments_propis(self, parser):
        parser.add_argument('--schema', required=True,
                            help='Schema del tenant (sense default: pany P2 del 22/08).')
        parser.add_argument('--buida-el-nom-del-tenant', action='store_true',
                            help='LA PORTA DEL REBATEIG. Sense això no s\'escriu res.')

    def corre(self, opts):
        flag = opts['buida_el_nom_del_tenant']
        buidats = ja_buits = sobirans = 0
        mostra = []

        with self.transacciona(opts['schema']):
            vius = (POMMaster.objects.filter(actiu=True, pom_global__isnull=False)
                    .select_related('pom_global').order_by('codi_client'))
            self.guarda('POMs vius LLIGATS al catàleg', vius.count())
            self.guarda('POMs vius NO lligats (no es toquen)',
                        POMMaster.objects.filter(actiu=True, pom_global__isnull=True).count())

            for p in vius:
                if p.separat_de_global:
                    sobirans += 1
                    self.excepcio(f'🔒 {p.codi_client!r}: SOBIRÀ — no se li toca el nom.')
                    continue
                if not p.nom_client:
                    ja_buits += 1
                    continue
                vell, canonic = p.nom_client, p.pom_global.nom_en
                if flag:
                    p.nom_client = ''
                    p.save(update_fields=['nom_client'])
                buidats += 1
                if len(mostra) < 8:
                    p_net = POMMaster(codi_client=p.codi_client, nom_client='',
                                      pom_global=p.pom_global)
                    n = noms_de(p_net)
                    mostra.append(f'{p.codi_client:<8} {vell!r} → EN {n["nom_en"]!r} · '
                                  f'CA {n["nom_ca"]!r}')

            self.guarda('noms buidats', buidats)
            self.guarda('noms que ja eren buits (idempotència)', ja_buits)
            self.guarda('sobirans respectats', sobirans)

            if not flag and not self.dry:
                raise CommandError(
                    f'{buidats} POMs canviarien de nom i falta `--buida-el-nom-del-tenant`. '
                    'Un rebateig no es fa sense dir-ho (tren de panys, 22/08).')

        self.diu(f'   buidats {buidats} · ja buits {ja_buits} · sobirans {sobirans}'
                 + ('' if flag else '   ⚠️ SENSE el flag: no s\'ha escrit res'))
        if mostra:
            self.diu('\n   El que la fitxa passarà a ensenyar:')
            for m in mostra:
                self.diu(f'      {m}')
