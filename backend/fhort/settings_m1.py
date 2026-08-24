"""Shim de settings per a la suite de M1: BD de test PRÒPIA.

La BD `test_ftt_staging` és compartida entre sessions concurrents del mateix servidor
(llei `ftt-dev-concurrent-git`): si una altra sessió hi corre la suite, la meva la destrueix
i al revés. L'única cosa que canvia aquí és el NOM de la BD de test.
"""
from fhort.settings import *  # noqa: F401,F403

DATABASES['default']['TEST'] = {'NAME': 'test_ftt_m1_rondes'}  # noqa: F405
