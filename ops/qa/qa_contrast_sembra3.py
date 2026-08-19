"""CONTRAST document ↔ BD del grading de Brownie, amb la CONVENCIÓ ±1 EXPLÍCITA.

Document base: `ops/sembra_v4/SEMBRA_3_grading_brownie.csv` (Agus, 10/08) — NO les columnes de
`SEMBRA_1_canonic.csv`, que és el catàleg i porta els Δ per un altre motiu.

🔑 LES DUES CONVENCIONS, QUE ÉS TOT EL QUE FA FALTA ENTENDRE AQUÍ:

    DOCUMENT  `talla_break` = l'ÚLTIMA talla del tram petit   (com escriu el full de Brownie)
    MOTOR     `talla_break_label` = la PRIMERA del tram gran  (on comença a aplicar-se Δ break)

    → són el MATEIX PUNT dit de dues bandes, i es tradueixen amb un desplaçament de +1 dins el
      run: doc `XS` ≡ bd `S` · doc `S` ≡ bd `M`. CASEN.

Per tant una fila DIVERGEIX només si, un cop traduïda, no cau al mateix lloc: doc `XS` amb bd
`M` són dos punts diferents i és una divergència REAL.

Aquest guió NO ESCRIU RES. Només mesura i imprimeix la taula.

    backend/venv/bin/python ops/qa/qa_contrast_sembra3.py
"""
import csv
import sys
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'backend'))

import django  # noqa: E402

django.setup()

from django_tenants.utils import schema_context  # noqa: E402

from fhort.pom.models import GradingRule, GradingRuleSet, SizeSystem  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
CSV = REPO / 'ops' / 'sembra_v4' / 'SEMBRA_3_grading_brownie.csv'
TENANT = 'fhort'
RULESET_ID = 219
BUIT = ('—', '-', '', 'N/A')
DELTES = ('d_xxs_xs', 'd_xs_s', 'd_s_m', 'd_m_l')


def doc_a_motor(etiqueta, run):
    """La talla del DOCUMENT → la que el MOTOR desa. Desplaçament de +1 dins el run."""
    if etiqueta in BUIT:
        return None
    if etiqueta not in run:
        return f'?{etiqueta}'                      # no és del run: no es pot traduir
    i = run.index(etiqueta)
    return run[i + 1] if i + 1 < len(run) else f'!{etiqueta}'   # l'última no té següent


def dec(v):
    try:
        return Decimal(str(v).strip().replace(',', '.'))
    except (InvalidOperation, AttributeError):
        return None


def main():
    if not CSV.exists():
        sys.exit(f'No hi ha el document base a {CSV}.')
    doc = {r['codi'].strip(): r for r in csv.DictReader(open(CSV, encoding='utf-8'), delimiter=';')}

    with schema_context(TENANT):
        rs = GradingRuleSet.objects.get(id=RULESET_ID)
        run = [t.etiqueta for t in SizeSystem.objects.get(id=rs.size_system_id)
               .talles.order_by('ordre')]
        viu = {r.pom.codi_client: r for r in
               GradingRule.objects.filter(rule_set=rs).select_related('pom')}

    print(f'DOCUMENT  {CSV.name}   {len(doc)} files')
    print(f'BD        ruleset {rs.id} «{rs.nom}»   {len(viu)} regles   run {run}')
    print(f'CONVENCIÓ doc→bd = +1 dins el run  (doc XS ≡ bd S · doc S ≡ bd M)\n')

    casen, divergeixen, absents, sobrants = [], [], [], sorted(set(viu) - set(doc))
    delta_div = []
    for codi in sorted(doc):
        r = viu.get(codi)
        if r is None:
            absents.append(codi)
            continue
        d_break = doc[codi]['talla_break'].strip()
        esperat = doc_a_motor(d_break, run)
        real = r.talla_break_label or None
        (casen if esperat == real else divergeixen).append((codi, d_break, esperat, real))
        # Els Δ, de propina: si el break casa però els increments no, el document i la BD
        # segueixen sense dir el mateix i val més saber-ho ara que a la propagació.
        d_doc = [dec(doc[codi][k]) for k in DELTES]
        petit, gran = d_doc[0], next((x for x in d_doc if x != d_doc[0]), None)
        if r.increment_base is not None and petit is not None and r.increment_base != petit:
            delta_div.append((codi, 'Δ base', str(petit), str(r.increment_base)))
        if gran is not None and r.increment_break is not None and r.increment_break != gran:
            delta_div.append((codi, 'Δ break', str(gran), str(r.increment_break)))

    print('═' * 78)
    print(f'{"CASEN":<12} {len(casen):>4}   la traducció ±1 les fa caure al mateix punt')
    print(f'{"DIVERGEIXEN":<12} {len(divergeixen):>4}   punts diferents — a corregir')
    print(f'{"AL DOC, NO A LA BD":<12} {len(absents):>4}')
    print(f'{"A LA BD, NO AL DOC":<12} {len(sobrants):>4}')
    print('═' * 78)

    print('\nCOM CASEN (document → traduït → desat):')
    for (d, e), n in sorted(Counter((c[1], c[2]) for c in casen).items(),
                            key=lambda x: -x[1]):
        print(f'   doc {d!r:6} → bd {str(e)!r:6}   {n:>3} regles')

    if divergeixen:
        print(f'\nDIVERGÈNCIES ({len(divergeixen)}):')
        print(f'   {"CODI":<8} {"DOC":<6} {"→ HAURIA DE SER":<16} {"BD DIU":<8}')
        for codi, d, e, real in divergeixen:
            print(f'   {codi:<8} {d:<6} {str(e):<16} {str(real):<8}')
    else:
        print('\nDIVERGÈNCIES: cap. Cada fila del document cau al punt que la BD té desat.')

    if absents:
        print(f'\nAL DOC I NO A LA BD ({len(absents)}): {absents}')
    if sobrants:
        print(f'A LA BD I NO AL DOC ({len(sobrants)}): {sobrants}')

    if delta_div:
        print(f'\n⚠️  Δ QUE NO CASEN ({len(delta_div)}):')
        for codi, quin, d, b in delta_div:
            print(f'   {codi:<8} {quin:<8} doc={d:<8} bd={b}')
    else:
        print('\nΔ: tots casen (base i break).')

    print('\nCAP ESCRIPTURA FETA: aquest guió només mesura.')
    return 0 if not divergeixen and not absents and not sobrants and not delta_div else 1


if __name__ == '__main__':
    sys.exit(main())
