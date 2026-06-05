"""models_app/matching.py — motor de matching run_talles + target → SizeSystem.

Donat un Target i una llista d'etiquetes de talla (p.ex. ['S','M','L','XL']), tria el
SizeSystem del tenant que millor encaixa. Gestió graceful del catàleg brut: els sistemes
inactius, buits (0 talles) o amb target=None NO entren com a candidats (s'ignoren en silenci).

Els missatges d'error són llegibles pel CLIENT final (no pel tècnic).
"""
import re
from collections import Counter
from dataclasses import dataclass, field


@dataclass
class MatchResult:
    size_system: object = None           # instància SizeSystem, o None si no hi ha candidat
    score: float = 0.0                   # fracció d'etiquetes reconegudes (0..1)
    unmatched_labels: list = field(default_factory=list)
    base_ok: bool = True
    warning: str = ''                    # avís (score parcial / empat) — no bloqueja
    error: str = ''                      # error llegible pel client — bloqueja

    @property
    def ok(self):
        return self.size_system is not None and not self.error


def _label_kind(label):
    """Classifica una etiqueta pel seu format, per desambiguar empats per base_unit."""
    l = str(label).strip().upper()
    if not l:
        return None
    if l == 'NB':
        return 'MONTHS'
    if re.search(r'\dY$', l):            # 6Y, 8Y
        return 'AGE_YEARS'
    if re.search(r'\dM', l):             # 3M, 0M-1M, 6M-9M
        return 'MONTHS'
    if re.fullmatch(r'[0-9]+(/[0-9]+)?', l):   # 34, 38, 9/10
        n = int(l.split('/')[0])
        return 'CM_HEIGHT' if n >= 50 else 'NUMERIC_EU'
    if l in {'XXS', 'XS', 'S', 'M', 'L', 'XL', 'XXL', '3XL', '4XL'} or re.fullmatch(r'[0-9]?X*[SML]', l):
        return 'ALPHA'
    return 'OTHER'


def _infer_base_unit(labels):
    """base_unit més probable del format dels labels (per trencar empats)."""
    kinds = [k for k in (_label_kind(x) for x in labels) if k and k != 'OTHER']
    if not kinds:
        return ''
    return Counter(kinds).most_common(1)[0][0]


def match_size_system(target_codi, labels_input, base_size):
    """Tria el SizeSystem candidat per a (target, labels). Vegeu MatchResult.

    Algoritme: candidats = sistemes actius del target amb >0 talles → score per intersecció
    d'etiquetes → guanyador per score màxim (desempat per base_unit inferit) → classifica el
    resultat (perfecte / parcial-avís / error) i valida que base_size sigui al run.
    """
    from django.db.models import Count
    from fhort.pom.models import SizeSystem, SizeDefinition

    labels = [str(x).strip() for x in labels_input if str(x).strip()]
    if not labels:
        return MatchResult(error="Columna 'run_talles': el run de talles és buit.")

    candidates = list(
        SizeSystem.objects
        .filter(target__codi=target_codi, actiu=True)
        .annotate(n_talles=Count('talles'))
        .filter(n_talles__gt=0)
    )
    if not candidates:
        return MatchResult(
            error=f"Columna 'run_talles': no hi ha cap sistema de talles configurat per a "
                  f"aquest target. Contacta amb l'estudi.")

    input_set = set(labels)
    scored = []
    for sys in candidates:
        ordered = list(
            SizeDefinition.objects.filter(size_system=sys).order_by('ordre')
            .values_list('etiqueta', flat=True))
        etiquetes = set(ordered)
        score = len(input_set & etiquetes) / len(input_set)
        scored.append((sys, score, etiquetes, ordered))

    max_score = max(s for _, s, _, _ in scored)
    winners = [w for w in scored if w[1] == max_score]

    warning = ''
    if len(winners) > 1:
        inferred = _infer_base_unit(labels)
        by_unit = [w for w in winners if w[0].base_unit == inferred] if inferred else []
        if by_unit:
            winner = by_unit[0]
        else:
            winner = winners[0]
            warning = f"Diversos sistemes encaixaven igual; s'ha triat {winner[0].codi}."
    else:
        winner = winners[0]

    sys, score, etiquetes, ordered = winner
    unmatched = [l for l in labels if l not in etiquetes]
    base_ok = base_size in input_set if base_size else False

    if score < 0.5:
        exemples = ', '.join(ordered[:8])
        return MatchResult(
            size_system=sys, score=score, unmatched_labels=unmatched, base_ok=base_ok,
            error=(f"Columna 'run_talles': format de talles no reconegut. El format esperat "
                   f"és: {exemples}. Talles no reconegudes: {', '.join(unmatched)}."))

    res = MatchResult(size_system=sys, score=score, unmatched_labels=unmatched,
                      base_ok=base_ok, warning=warning)
    if 0.5 <= score < 1.0:
        msg = f"Algunes talles no s'han reconegut: {', '.join(unmatched)}."
        res.warning = (warning + ' ' + msg).strip()
    if not base_ok:
        res.error = (f"Columna 'talla_base': la talla base '{base_size}' no és al run de "
                     f"talles ({', '.join(labels)}).")
    return res
