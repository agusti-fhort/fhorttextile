"""FASE D · L'EXAMEN DE LES COSTURES: leave-one-out sobre el 837.

Per cada `SewRelation` CONFIRMADA del banc: s'amaga **en lectura** i es mira si el motor la
torna a proposar, amb quina força i amb quins senyals. Res s'esborra i res s'escriu.

🚨 **Els rols de vora els posa el proposador de F4.2 EN MEMÒRIA.** A la BD només n'hi ha UN
de confirmat per un humà, i el senyal de catàleg no es pot mesurar sense els dos costats. És
la mateixa tècnica que el gate D2 de F4.2: provar la regla no exigeix adoptar-la.

    python3 ops/recognition/lab_seams.py [--model 1383] [--pf 20]
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'backend'))


def solapament(a0, a1, b0, b1) -> float:
    def trossos(t0, t1):
        return [(t0, t1)] if t0 <= t1 else [(t0, 1.0), (0.0, t1)]
    return sum(max(0.0, min(x1, y1) - max(x0, y0))
               for x0, x1 in trossos(a0, a1) for y0, y1 in trossos(b0, b1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', type=int, default=1383)
    ap.add_argument('--pf', type=int, default=20)
    ap.add_argument('--schema', default='fhort')
    args = ap.parse_args()

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fhort.settings')
    os.chdir(REPO / 'backend')
    import django
    django.setup()
    from django_tenants.utils import schema_context

    from fhort.patterns.models import PatternFile, PatternSegment, SewRelation
    from fhort.patterns.recognition.edge_service import propose_edge_roles
    from fhort.patterns.seam_proposals import propostes_del_model

    with schema_context(args.schema):
        fp = PatternFile.objects.get(pk=args.pf)

        rols = {}
        for pc in fp.pieces.select_related('piece_role').prefetch_related('points'):
            for p in propose_edge_roles(pc)['proposals']:
                if p['edge_role']:
                    rols[p['segment_id']] = p['edge_role']
        print('rols de vora en memoria (F4.2): {}'.format(len(rols)))

        naturals = {}
        for s in PatternSegment.objects.filter(
                piece__pattern_file=fp, origen=PatternSegment.ORIGEN_NATURAL):
            naturals.setdefault(s.piece_id, []).append(s)

        def natural_de(d):
            millor, cob = None, 0.0
            for n in naturals.get(d.piece_id, []):
                if n.vora != d.vora:
                    continue
                c = solapament(d.t_inici, d.t_fi, n.t_inici, n.t_fi)
                if c > cob:
                    millor, cob = n, c
            return millor

        relacions = list(SewRelation.objects.filter(model_id=args.model)
                         .prefetch_related('segments_a__piece', 'segments_b__piece')
                         .order_by('id'))
        print('costures confirmades: {}'.format(len(relacions)))
        print('=' * 100)

        recuperades, perdudes = 0, []
        for r in relacions:
            da = list(r.segments_a.all())
            db = list(r.segments_b.all())
            na = natural_de(da[0]) if da else None
            nb = natural_de(db[0]) if db else None
            etiqueta = '{} + {}'.format(
                da[0].piece.nom_block if da else '?', db[0].piece.nom_block if db else '?')
            if na is None or nb is None:
                perdudes.append((r.id, etiqueta, 'cap tram natural cobreix el declarat'))
                print('sew#{:<3} {:<34} NO RECUPERADA - cap tram natural el cobreix'
                      .format(r.id, etiqueta))
                continue
            if na.piece_id == nb.piece_id:
                perdudes.append((r.id, etiqueta,
                                 'els dos costats son de la MATEIXA peca: proposar() les salta per disseny'))
                print('sew#{:<3} {:<34} NO RECUPERADA - mateixa peca (el motor les salta per disseny)'
                      .format(r.id, etiqueta))
                continue

            res = propostes_del_model(fp, rols_en_memoria=rols, exclou_sew_ids={r.pk})
            trobada = None
            for p in res['propostes']:
                ids = {p['a']['segment_id'], p['b']['segment_id']}
                if ids == {na.id, nb.id}:
                    trobada = p
                    break
            if trobada:
                recuperades += 1
                menes = {s['mena']: s for s in trobada['senyals']}
                print('sew#{:<3} {:<34} RECUPERADA  conf={:.3f}  senyals={}'
                      .format(r.id, etiqueta, trobada['confianca'], '+'.join(sorted(menes))))
                if 'cataleg' in menes:
                    print('        cataleg: {}'.format(menes['cataleg']['detall']))
                if 'precedent' in menes:
                    print('        precedent: {}'.format(menes['precedent']['detall']))
            else:
                motiu = 'no ha arribat a proposta (candidats={}, sota llindar={})'.format(
                    res['candidats'], res['descartats']['sota_llindar'])
                perdudes.append((r.id, etiqueta, motiu))
                print('sew#{:<3} {:<34} NO RECUPERADA - {}'.format(r.id, etiqueta, motiu))

        print('=' * 100)
        print('D1 . RECUPERADES {} de {}'.format(recuperades, len(relacions)))
        for sid, et, motiu in perdudes:
            print('   no recuperada . sew#{} {} -> {}'.format(sid, et, motiu))

        res = propostes_del_model(fp, rols_en_memoria=rols)
        print('=' * 100)
        print('D4 . ABSENTS (expectatives de nucli sense costura): {}'.format(len(res['absents'])))
        for a in res['absents']:
            print('   {}.{} + {}.{}   {} ({:.2f})'.format(
                a['a']['piece_role'], a['a']['edge_role'],
                a['b']['piece_role'], a['b']['edge_role'], a['grau'], a['ratio']))
        print('senyals: {}'.format(res['senyals_nous']))


if __name__ == '__main__':
    main()
