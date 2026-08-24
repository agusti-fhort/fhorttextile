"""Shim de settings per al bloc GATES d'M3: BD de test pròpia i SEPARADA de la del bloc RONDA.

Els dos blocs es corren EN PARAL·LEL (són llargs i independents), i compartir la BD de test vol
dir que el segon en destrueix la del primer a mig camí — el mateix motiu pel qual `settings_m3`
ja no fa servir `test_ftt_staging`.
"""
from fhort.settings import *  # noqa: F401,F403

DATABASES['default']['TEST'] = {'NAME': 'test_ftt_m3_gates'}  # noqa: F405
