#!/usr/bin/env python
"""QA · SOBIRANIA DEL POM — la llei mesurada contra les dades VIVES de staging (22/08).

    cd /var/www/ftt-staging/backend
    venv/bin/python ../ops/qa/qa_sobirania_pom.py [--tenant fhort]

🔒 NO DEIXA RESIDU. Els blocs que necessiten un POM LLIGAT al catàleg global no en troben cap
a staging —`fhort` té 144 POMMaster i **tots** amb `pom_global` a NULL, i 0 `POMGlobal` al seu
schema (els 125 canònics viuen a `public`)—, o sigui que se'l fabrica. Ho fa DINS d'una
transacció que es tomba sempre: la fixture existeix el temps de mesurar-la i desapareix. Cap
`--apply`, cap camí per escriure de debò. La resta de blocs són lectura pura.

🚨 I PER AIXÒ EL DEFECTE D'AGUS NO ES REPRODUEIX A STAGING. «LOSPOM-548 · FRONT ARMHOLE» és
una fila de PROD, on el catàleg global sí que té fills al tenant. A staging el mateix codi
donava el mateix resultat abans i després del fix, perquè no hi ha cap POM lligat que el
pogués delatar. Un verd d'aquest fitxer contra les 144 files reals **no** hauria demostrat
res: el que demostra la llei és el bloc de la fixture.

BLOCS
  A · CENS      quantes de les 144 files reals canvien de codi o de nom amb la llei nova
  B · LA LLEI   àlies > tenant > global, sobre una fixture lligada de debò (i tombada)
  C · UNA VEU   les DUES portes que es contradeien —`POMMaster.pom_code` i
                `POMMasterSerializer.get_pom_code`— dient el mateix sobre la mateixa fila,
                més la cascada del «com es mesura». Les altres superfícies (base-measurements,
                taula-mesures, la pertinença de peça) criden el mateix resolutor i ho fixen
                els tests de `fhort.pom.test_sobirania_nomenclatura`, no aquest banc.
  D · COW       separar-se no perd informació, i el «com es mesura» és informable al tenant
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fhort.settings')

import django  # noqa: E402
django.setup()

from django.db import transaction  # noqa: E402
from django_tenants.utils import schema_context  # noqa: E402


class _Tomba(Exception):
    """Sortida sempre-rollback del bloc de la fixture."""


OK, KO = '✅', '❌'
falles = []


def diu(cond, etiqueta, detall=''):
    print(f'    {OK if cond else KO} {etiqueta}' + (f'  —  {detall}' if detall else ''))
    if not cond:
        falles.append(etiqueta)
    return cond


# ── BLOC A · el cens de les files reals ─────────────────────────────────────────────────
def bloc_a():
    from fhort.pom.models import POMMaster
    from fhort.pom.nomenclatura import codi_de, noms_de

    poms = list(POMMaster.objects.select_related('pom_global', 'categoria').all())
    lligats = [p for p in poms if p.pom_global_id]
    print(f'\n  ▸ BLOC A · CENS  ·  {len(poms)} POMMaster  ·  {len(lligats)} lligats al global')

    # La llei VELLA del serializer: el global guanyava.
    canvien_codi, canvien_nom = [], []
    for p in poms:
        vell_codi = (p.pom_global.codi if p.pom_global_id else None) or p.codi_client
        vell_nom = (p.pom_global.nom_en if p.pom_global_id else None) or p.nom_client
        if codi_de(p) != vell_codi:
            canvien_codi.append((p.pk, vell_codi, codi_de(p)))
        if noms_de(p)['nom_en'] != vell_nom:
            canvien_nom.append((p.pk, vell_nom, noms_de(p)['nom_en']))

    print(f'      files que canvien de CODI: {len(canvien_codi)}  ·  de NOM: {len(canvien_nom)}')
    for pk, v, n in (canvien_codi + canvien_nom)[:10]:
        print(f'        pk={pk}  {v!r} → {n!r}')
    diu(len(canvien_codi) == len(lligats) or not lligats,
        'només canvien files LLIGADES (una fila tenant-only no pot canviar de sobirà)',
        f'lligats={len(lligats)} canvis={len(canvien_codi)}')
    # Cap fila pot quedar MUDA: la promesa de la columna que no surt mai buida.
    muts = [p.pk for p in poms if not codi_de(p)]
    diu(not muts, 'cap fila es queda sense codi visible', f'mudes={muts[:5]}')


# ── BLOC B · la llei, sobre una fixture lligada de debò ─────────────────────────────────
def bloc_b_c_d():
    from fhort.pom.models import CustomerPOMAlias, POMGlobal, POMMaster
    from fhort.pom.nomenclatura import (abreviatura_de, alies_per_pom, codi_de,
                                        com_es_mesura_de, noms_de, separa_del_global)
    from fhort.pom.serializers import POMMasterSerializer
    from fhort.tasks.models import Customer

    try:
        with transaction.atomic():
            pg = POMGlobal.objects.create(
                codi='QA-SOB-GLOBAL', nom_en='FRONT ARMHOLE', nom_ca='SISA DAVANTERA',
                categoria='Upper body', abbreviation='FR AH', unitat='cm',
                start_point='Shoulder point', end_point='Underarm point',
                reference_point='Along the armhole seam', scope='FULL',
                orientation='CURVED', state='FLAT', line='ALONG CURVE', body_section='FRONT')
            pom = POMMaster.objects.create(
                codi_client='QA-SD', nom_client='Sisa davantera QA', pom_global=pg, actiu=True)

            print('\n  ▸ BLOC B · LA LLEI  ·  àlies > tenant > global')
            print(f'      fixture: POMMaster pk={pom.pk} `QA-SD` → POMGlobal `QA-SOB-GLOBAL`')

            # ① sense àlies → el del TENANT (el defecte d'Agus, a l'inrevés)
            diu(codi_de(pom) == 'QA-SD', 'sense àlies mana el codi del TENANT',
                f'{codi_de(pom)!r} (el global diu {pg.codi!r})')
            diu(noms_de(pom)['nom_en'] == 'Sisa davantera QA',
                'sense àlies mana el nom del TENANT', repr(noms_de(pom)['nom_en']))
            diu(abreviatura_de(pom) == 'QA-SD', "l'abreviatura també és la del tenant")

            # ② amb àlies de client → el del CLIENT
            cust = Customer.objects.first()
            if cust is None:
                print('      ⚠️  cap Customer al tenant: el bloc de l\'àlies se salta')
            else:
                CustomerPOMAlias.objects.create(
                    # Codi de QA, no 'A': el client 7 (Brownie) JA en té un i la
                    # unicitat `(customer, client_code)` és de la BD. Un banc que xoqui amb
                    # les dades vives no mesura res, i el xoc era real.
                    customer=cust, pom=pom, client_code='QA-A',
                    description_en='Front armhole (client)', description_local='Sisa A',
                    origen='MANUAL')
                alies = alies_per_pom(cust.id)
                diu(codi_de(pom, alies.get(pom.pk)) == 'QA-A',
                    "amb àlies de client mana l'ÀLIES", f'client `{cust.codi}` diu «QA-A»')
                diu(noms_de(pom, alies.get(pom.pk))['nom_en'] == 'Front armhole (client)',
                    'i el nom també és el del client')

            # ③ el global, només si no hi ha res més
            pom.codi_client, pom.nom_client = '', ''
            diu(codi_de(pom) == 'QA-SOB-GLOBAL', 'el GLOBAL surt només si no hi ha res més')
            diu(noms_de(pom)['nom_en'] == 'FRONT ARMHOLE', 'i el nom global, igual')
            pom.codi_client, pom.nom_client = 'QA-SD', 'Sisa davantera QA'
            pom.save()

            # ── BLOC C · una sola veu per les quatre portes ─────────────────────────
            print('\n  ▸ BLOC C · UNA VEU  ·  les dues portes que es contradeien')
            del_serializer = POMMasterSerializer(pom).data
            diu(del_serializer['pom_code'] == codi_de(pom),
                'catàleg (POMMasterSerializer) diu el mateix que el resolutor',
                f"{del_serializer['pom_code']!r}")
            diu(del_serializer['name_en'] == noms_de(pom)['nom_en'],
                'i el nom, també')
            diu(pom.pom_code == del_serializer['pom_code'],
                '🚨 model i serializer JA NO ES CONTRADIUEN',
                f"model={pom.pom_code!r} serializer={del_serializer['pom_code']!r}")
            diu(pom.name_en == del_serializer['name_en'],
                'ni en el nom (era la segona meitat de la contradicció)')
            # el «com es mesura» que la pantalla ensenya surt de la cascada, no del global cru
            diu(del_serializer['start_point'] == com_es_mesura_de(pom)['start_point'],
                'el «com es mesura» del catàleg passa per la cascada',
                repr(del_serializer['start_point']))

            # ── BLOC D · copy-on-write ─────────────────────────────────────────────
            print('\n  ▸ BLOC D · COPY-ON-WRITE  ·  separar-se no és perdre')
            abans = com_es_mesura_de(pom)
            abans_en = noms_de(pom)['nom_en']
            separa_del_global(pom)
            pom.save()
            pom.refresh_from_db()
            diu(pom.pom_global_id is None, 'el POM ja no penja del global')
            diu(pom.separat_de_global == 'QA-SOB-GLOBAL', 'i porta la MARCA de sobirania',
                f'separat_at={pom.separat_at}')
            diu(com_es_mesura_de(pom) == abans,
                'el «com es mesura» diu EXACTAMENT el mateix que abans')
            diu(noms_de(pom)['nom_en'] == abans_en, 'i el nom canònic, també')
            diu(POMGlobal.objects.filter(codi='QA-SOB-GLOBAL').exists(),
                'el catàleg GLOBAL no s\'ha tocat')
            # informable al tenant: el forat que el tram 3 tanca
            pom.start_point = "De l'espatlla"
            pom.save(update_fields=['start_point'])
            diu(com_es_mesura_de(pom)['start_point'] == "De l'espatlla",
                'un POM propi JA pot dir com es mesura (era impossible fins avui)')

            raise _Tomba
    except _Tomba:
        pass

    from fhort.pom.models import POMGlobal as PG
    diu(not PG.objects.filter(codi='QA-SOB-GLOBAL').exists(),
        '🔒 la fixture ha desaparegut: cap residu a la BD')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tenant', default='fhort')
    a = ap.parse_args()
    print(f'\nQA · SOBIRANIA DEL POM  ·  tenant `{a.tenant}`')
    with schema_context(a.tenant):
        bloc_a()
        bloc_b_c_d()
    print(f'\n  VEREDICTE: {"✅ VERD" if not falles else "❌ " + str(len(falles)) + " FALLES"}')
    for f in falles:
        print(f'      · {f}')
    return 1 if falles else 0


if __name__ == '__main__':
    sys.exit(main())
