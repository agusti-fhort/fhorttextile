"""BANC de `qa_break_per_regla.py` — el munta i el desmunta. NO toca el catàleg de Brownie.

⚠️ **PER QUÈ UN BANC PROPI I NO EL JOC 219.** El joc viu de `fhort` és `GRADING BROWNIE 2026`
(142 regles, el catàleg que l'Agus està corregint contra el document base). Un arnès que ESCRIU
break labels sobre aquell joc li mouria la feina sota els peus i, si petés a mitges, el deixaria
en un estat que ningú no sabria distingir d'una correcció seva. El banc és de l'arnès: tres jocs
`ZZ-QA-BREAK-*` que es creen abans i s'esborren després, sempre.

🔑 I ES REINICIA SEMPRE (llei del 09/08: un guió de QA que escriu ha de reiniciar el banc, o la
segona passada mesura l'empremta de la primera). `--crea` esborra el que hi hagi abans de sembrar.

Els tres jocs, i què mesura cadascun:
  · ZZ-QA-BREAK-ALPHA  ALPHA_EU_W  · 6 regles (4 amb Δ break, 2 sense) → el picker per fila,
                                     l'edició d'UNA sola fila, i el selector BLOQUEJAT amb motiu
  · ZZ-QA-BREAK-NUM    NUMERIC_EU_W· 2 regles amb Δ break             → les opcions del picker
                                     surten del sistema del joc, no d'ALPHA
  · ZZ-QA-BREAK-BUIT   ALPHA_EU_W  · 0 regles                         → el selector, OBERT

    backend/venv/bin/python ops/qa/qa_break_per_regla_banc.py --crea    # imprimeix JSON
    backend/venv/bin/python ops/qa/qa_break_per_regla_banc.py --esborra
"""
import json
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'backend'))

import django  # noqa: E402

django.setup()

from django_tenants.utils import schema_context  # noqa: E402

from fhort.pom.models import GradingRule, GradingRuleSet, POMMaster, SizeSystem  # noqa: E402

TENANT = 'fhort'
PREFIX = 'ZZ-QA-BREAK'


def _esborra():
    """Fora tots els jocs del banc. CASCADE se'n porta les regles."""
    qs = GradingRuleSet.objects.filter(nom__startswith=PREFIX)
    n_jocs = qs.count()
    n_regles = GradingRule.objects.filter(rule_set__in=qs).count()
    qs.delete()
    return n_jocs, n_regles


def _joc(nom, sistema, poms, especs):
    """Un joc del banc amb les seves regles. `especs` = [(Δ base, Δ break | None)]."""
    ss = SizeSystem.objects.get(codi=sistema)
    base = ss.talles.order_by('ordre').first()
    etiquetes = [t.etiqueta for t in ss.talles.order_by('ordre')]
    # El break de sembra va a la TERCERA talla: prou endins del run perquè moure'l amunt o avall
    # sigui visible, i mai la base (que no pot ser trencament de res).
    trenca = etiquetes[2] if len(etiquetes) > 2 else etiquetes[-1]
    rs = GradingRuleSet.objects.create(
        nom=nom, codi_sistema=nom, size_system=ss, actiu=True,
        origen=GradingRuleSet.ORIGEN_CANONICAL, is_system_default=False)
    ids = []
    for i, (d_base, d_break) in enumerate(especs):
        r = GradingRule.objects.create(
            rule_set=rs, pom=poms[i], talla_base=base, talla_base_label=base.etiqueta,
            logica=GradingRule.LOGICA_LINEAR, increment=Decimal(str(d_base)),
            increment_base=Decimal(str(d_base)),
            increment_break=None if d_break is None else Decimal(str(d_break)),
            talla_break_label=None if d_break is None else trenca,
            talla_break_pos=None, valors_step=None, actiu=True)
        ids.append(r.id)
    return {'id': rs.id, 'nom': nom, 'sistema': sistema, 'talles': etiquetes,
            'trenca': trenca, 'regles': ids}


def _crea():
    _esborra()
    poms = list(POMMaster.objects.filter(actiu=True).order_by('id')[:8])
    if len(poms) < 8:
        sys.exit(f'Calen 8 POMMaster vius al banc i només n\'hi ha {len(poms)}.')
    return {
        'alpha': _joc(f'{PREFIX}-ALPHA', 'ALPHA_EU_W', poms,
                      [(1, 2), (1, 2), (0.5, 1.5), (1, 3), (1, None), (0.5, None)]),
        'num': _joc(f'{PREFIX}-NUM', 'NUMERIC_EU_W', poms[6:], [(1, 2), (2, 4)]),
        'buit': _joc(f'{PREFIX}-BUIT', 'ALPHA_EU_W', poms, []),
    }


def main():
    accio = sys.argv[1] if len(sys.argv) > 1 else ''
    with schema_context(TENANT):
        if accio == '--crea':
            print(json.dumps(_crea(), ensure_ascii=False))
        elif accio == '--esborra':
            n_jocs, n_regles = _esborra()
            print(json.dumps({'jocs_esborrats': n_jocs, 'regles_esborrades': n_regles}))
        else:
            sys.exit(__doc__)


if __name__ == '__main__':
    main()
