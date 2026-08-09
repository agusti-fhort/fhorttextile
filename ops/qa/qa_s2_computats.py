"""AUDITORIA DE COMPUTATS · LES 16 SUPERFÍCIES DEL LOT COMERCIAL (S2, part B).

§8d: «la conformitat ES MESURA». Aquest fitxer **no duplica cap lògica**: importa el mesurador de
`qa_auditoria_computats` —la paleta ratificada, el JS que llegeix `getComputedStyle`, el proxy
cap al servei viu i el veredicte— i només li canvia la llista de rutes.

**PER QUÈ UN RUNNER I NO AFEGIR-LES A `PANTALLES`.** El fitxer original és de la sessió germana i
l'està tocant en paral·lel; dues sessions editant la mateixa llista és com es perd una ruta sense
que ho noti ningú. Amb un runner, cadascú té la seva llista i el MESURADOR és el mateix — que és
justament el que ha de ser únic.

⚠️ **EL BUNDLE ÉS EL QUE MESURA, NO EL CODI DEL DISC.** Aquest arnès llegeix `frontend/dist`. Si
el `dist` és anterior a l'últim commit, el que es mesura és la pantalla ANTERIOR i el resultat
—verd o vermell— no diu res del codi d'ara. Comprova la data del bundle abans de creure't el
número (llei d'infra de la casa, versió frontend).

    FTT_QA_TOKEN=... /tmp/qa-venv/bin/python ops/qa/qa_s2_computats.py
"""
import sys

import qa_auditoria_computats as base

#: Les rutes del lot comercial. Les fitxes de document i de client demanen un id VIU: si el banc
#: no en té cap, la ruta cau al seu estat buit i la mesura segueix sent vàlida (mesura el que
#: l'usuari veuria), però no cobreix la graella plena — v. la taula de límits del report.
PANTALLES = [
    ('B1 · Clients', '/clients'),
    ('B2 · Fitxa de client · Dades', '/clients/1?tab=dades'),
    ('B2 · Fitxa de client · Tècnic', '/clients/1?tab=tecnic'),
    ('B2 · Fitxa de client · Comercial', '/clients/1?tab=comercial'),
    ('B3 · Proveïdors', '/suppliers'),
    ('B4 · Productes', '/comercial/productes'),
    ('B5 · Ofertes', '/comercial/ofertes'),
    ('B6 · Comandes', '/comercial/comandes'),
    ('B7 · Encàrrecs (federació)', '/encarrecs'),
    ('B8 · Encàrrecs (WorkOrders)', '/comercial/encarrecs'),
    ('B9 · Albarans', '/comercial/albarans'),
    ('B10 · Orfes', '/comercial/orfes'),
    ('B11 · Condicions de pagament', '/comercial/condicions-pagament'),
]

if __name__ == '__main__':
    base.PANTALLES = PANTALLES
    sys.exit(base.main() or 0)
