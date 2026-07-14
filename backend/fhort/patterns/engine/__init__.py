"""Motor de patrons — nucli geomètric.

**Paquet Python PUR.** Llei dura del mòdul: aquí dins NO s'importa `django`, ni
`rest_framework`, ni cap model ORM. El motor treballa amb les seves pròpies
dataclasses (`geometry.py`) i parla amb el món per Protocols (`ports.py`); els
adaptadors viuen FORA d'`engine/` (a `patterns/adapters.py`, `models.py`, `views.py`,
que arriben a S3).

El guard `PurityGuardTest` (patterns/tests.py) ho vigila per AST i importa aquest
paquet en un subprocés sense `DJANGO_SETTINGS_MODULE`: si algú hi cola Django, el
sprint és vermell.
"""
