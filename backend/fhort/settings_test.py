"""Settings de SUITE — la BD de test surt de l'ENTORN, i cada correguda pot tenir la seva.

## Per què existeix, i per què n'hi ha UN i no un per milestone

`test_ftt_staging` és compartida entre les sessions concurrents del mateix servidor (llei
`ftt-dev-concurrent-git`): si una altra sessió hi corre la suite, **la meva la destrueix a mig
camí, i al revés**. La sortida va ser donar-li a cada correguda una BD de test pròpia… i això va
anar creixent en fitxers: `settings_m1`, `settings_m3`, `settings_m3_gates`, `settings_m4`, tots
quatre idèntics tret d'una cadena, i cadascun amb el nom del sprint que el va necessitar.

**M5 · neteja del tren, 25/08.** Els quatre s'absorbeixen aquí. El nom de la BD deixa de ser una
constant al codi i passa a ser un **paràmetre de la correguda**, que és el que sempre va ser: una
sessió nova ja no ha d'afegir un cinquè fitxer, i cap fitxer amb nom de milestone sobreviu al tren.

## Ús

    # una correguda qualsevol (BD per defecte)
    venv/bin/python manage.py test fhort.tasks --settings=fhort.settings_test --keepdb

    # dues corregudes EN PARAL·LEL, cadascuna amb la seva BD (el cas que ho va motivar tot)
    FTT_TEST_DB=test_ftt_ronda venv/bin/python manage.py test … --settings=fhort.settings_test &
    FTT_TEST_DB=test_ftt_gates venv/bin/python manage.py test … --settings=fhort.settings_test &

⚠️ **Dues corregudes simultànies amb el MATEIX `FTT_TEST_DB` segueixen xocant.** Això no ho pot
arreglar cap settings: qui llança dos blocs alhora els ha de donar noms diferents, i és
exactament per a això que el nom és un paràmetre.
"""
import os

from fhort.settings import *  # noqa: F401,F403

#: El nom de la BD de test. Per defecte una de pròpia i explícita —MAI `test_ftt_staging`, que
#: és la compartida i la que el problema original destruïa.
DATABASES['default']['TEST'] = {  # noqa: F405
    'NAME': os.environ.get('FTT_TEST_DB', 'test_ftt_suite'),
}
