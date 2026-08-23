"""S6 · EL TANCAMENT DELS 142 — les dues sisas que faltaven, i el duplicat que NO es fusiona.

Dues coses, i només dues:

  (a) **reactivar `S` i `S2`** (el brief els cita com a pk 462 i 463 de PROD) i donar-los
      família, que és camp del tenant;
  (b) **anotar** el duplicat `SF` («AH DEP» vs la fitxa) al report com a **fusió pendent**.

🔑 **PER CODI, MAI PER pk** (llei R-POM). El brief dona 462 i 463 perquè són els de PROD; a
staging els mateixos dos POMs són 1012 i 1013. Cap pk entra al codi d'aquesta comanda: entra el
codi, i la pk surt al report perquè es pugui anar a la fila.

🚫 **EL DUPLICAT NO ES FUSIONA AQUÍ, I NO ÉS TIMIDESA.** Fusionar dos POMs és moure mesures,
regles i àlies d'una fila a l'altra: vol **joc daurat i banc de paritat** (llei de la casa),
que és un tram propi. El que aquesta comanda fa és **no deixar-lo passar en silenci**: el
report el nomena, amb les dues files i amb qui les fa servir.

🔑 **LA FAMÍLIA NO S'ENDEVINA, I VE DEL r2 PER DOS CAMINS.** Primer, el lligam que S3 hagi
escrit; i si no n'hi ha, **el mateix mapa del r2 que fa servir S3** (codi Brownie → codi de
sistema → columna `Fam.`). Fora d'aquests dos, la comanda **no en tria cap**: es reporta, i
`--categoria CODI` és la manera que Agus en declari una.

🚨 **I AQUÍ HI HA UN ORDRE QUE EL BRIEF NO PODIA SABER.** Aquests dos POMs arriben a S6
**inactius** —és el que S6 ve a arreglar—, i S3 i S5 només toquen els VIUS: quan els reactiva,
ja han passat. Per això la família se'ls dona aquí, i per això el report acaba dient que **cal
tornar a passar S3 i S5** perquè els dos ressuscitats rebin el lligam com tots els altres. Totes
dues són idempotents: la re-passada no mou res més.

    manage.py tancament_142 --schema fhort                # DRY-RUN
    manage.py tancament_142 --schema fhort --no-dry-run   # escriu
"""
from django.db.models import Q

from fhort.pom.models import POMCategory, POMMaster
from fhort.pom.sembra_v5 import corpus
from fhort.pom.sembra_v5.base import ComandaV5

#: Els dos POMs del tancament, PEL SEU CODI.
CODIS = ('S', 'S2')
#: El duplicat que s'anota i no es toca: el codi de la fitxa i el text que el brief cita.
DUPLICAT_CODI = 'SF'
DUPLICAT_TEXT = 'AH DEP'


class Command(ComandaV5):
    help = 'S6 · reactiva `S` i `S2`, els dona família i anota la fusió pendent de `SF`.'
    PAS = 'S6 · tancament dels 142'
    ESPERAT = {'POMs del tancament trobats': 2}

    def arguments_propis(self, parser):
        parser.add_argument('--schema', required=True,
                            help='Schema del tenant (sense default: pany P2 del 22/08).')
        parser.add_argument('--categoria', default=None,
                            help='Codi de família a posar quan el r2 no la pugui donar.')

    def corre(self, opts):
        fam_del_pom = {p['codi']: p['familia'] for p in self.corpus['poms']}
        mapa = corpus.mapa_brownie(self.corpus['alies'])
        trobats = reactivats = ja_actius = amb_familia = sense_familia = 0

        with self.transacciona(opts['schema']):
            for codi in CODIS:
                p = (POMMaster.objects.select_related('pom_global', 'categoria')
                     .filter(codi_client=codi).first())
                if p is None:
                    self.excepcio(f'{codi!r}: no existeix a `{opts["schema"]}`.')
                    continue
                trobats += 1
                self.diu(f'   {codi:4} pk={p.pk} {p.nom_client!r} · actiu={p.actiu} '
                         f'· família={p.categoria.codi if p.categoria_id else None}')

                if p.actiu:
                    ja_actius += 1
                else:
                    p.actiu = True
                    p.save(update_fields=['actiu'])
                    reactivats += 1

                codi_v5 = (p.pom_global.codi if p.pom_global_id
                           else mapa.get(p.codi_client))
                fam = fam_del_pom.get(codi_v5) if codi_v5 else None
                if fam is None:
                    fam = opts['categoria']
                if p.pom_global_id is None and codi_v5 is not None:
                    self.excepcio(
                        f'{codi!r}: reactivat i SENSE lligam (S3 ja havia passat i el va '
                        'veure d\'arxiu). Torna a passar S3 i S5, que són idempotents.')
                if fam is None:
                    sense_familia += 1
                    self.excepcio(
                        f'{codi!r}: sense fila al r2 (no lligat per S3) i sense --categoria: '
                        'la família NO s\'endevina i es queda com està '
                        f'({p.categoria.codi if p.categoria_id else None!r}).')
                    continue
                cat = POMCategory.objects.filter(codi=fam).first()
                if cat is None:
                    self.excepcio(f'{codi!r}: la família {fam!r} no existeix al tenant '
                                  '(corre S5 abans).')
                    continue
                if p.categoria_id != cat.id:
                    p.categoria = cat
                    p.save(update_fields=['categoria'])
                amb_familia += 1

            self.guarda('POMs del tancament trobats', trobats)
            self.guarda('POMs reactivats', reactivats)
            self.guarda('POMs que ja eren actius (idempotència)', ja_actius)
            self.guarda('POMs amb família posada', amb_familia)
            self.guarda('POMs sense família resoluble', sense_familia)

            # ── La fusió pendent, anotada ─────────────────────────────────────────────────
            dup = list(POMMaster.objects.filter(
                Q(codi_client=DUPLICAT_CODI) | Q(nom_client__icontains=DUPLICAT_TEXT)
            ).select_related('categoria').order_by('pk'))
            self.guarda(f'files del duplicat {DUPLICAT_CODI!r} / {DUPLICAT_TEXT!r}', len(dup))
            for p in dup:
                n_bm = p.base_measurements.count()
                self.excepcio(
                    f'🚩 FUSIÓ PENDENT · pk={p.pk} {p.codi_client!r} {p.nom_client!r} '
                    f'actiu={p.actiu} · {n_bm} mesures de model · NO es fusiona aquí '
                    '(vol joc daurat + banc de paritat).')

        self.diu(f'   trobats {trobats} · reactivats {reactivats} · ja actius {ja_actius} '
                 f'· família posada {amb_familia} · sense família {sense_familia}')
