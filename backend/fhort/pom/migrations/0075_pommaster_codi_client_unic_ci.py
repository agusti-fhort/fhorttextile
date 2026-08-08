"""`POMMaster.codi_client` ÚNIC PER TENANT, insensible a majúscules.

**PER QUÈ ARA.** El catàleg de `fhort` acabava de tenir **12 codis duplicats** (`U1`, `D`, `J1`,
`BJ`, `C1`, `L1`, `S2`, `E4`, `H`, `U`, `E7`, `S`, cadascun × 2 = 24 files), i la causa és
coneguda i està escrita al codi: `pom/wizard_views.py` diu, al camí que crea un POM propi, que
copiar el codi del client al codi de la casa «és exactament el que va fabricar els 12 duplicats de
`POMMaster.codi_client` que hi ha avui». La validació hi era; el que faltava era que la BD la fes
complir.

**LA SEMÀNTICA NO ÉS NOVA: ÉS LA DEL CAMÍ 4.** `create_model_pom_view` ja comprova
`POMMaster.objects.filter(codi_client__iexact=…)` i, si el codi és ocupat, requalifica amb el codi
del customer. Aquesta constraint és aquella comprovació, però a la banda que no es pot saltar: una
validació que només viu a una vista deixa fora l'import, l'admin, el shell i qualsevol camí futur
—i van ser aquests, no la vista, els que van fabricar els duplicats—.

**INSENSIBLE A MAJÚSCULES, i per això és una constraint d'EXPRESSIÓ** (`Upper('codi_client')`), que
PostgreSQL materialitza com a índex funcional únic. `u1` i `U1` són el mateix codi per a una
patronista, i deixar-los conviure seria tenir la constraint i el problema alhora.

**SENSE `Trim`, i és una decisió, no un descuit.** `Trim` faria que `'U1'` i `'U1 '` xoquessin, cosa
que sona bé fins que et fixes que llavors la BD accepta desar `'U1 '` i el rebutja com a duplicat
d'ell mateix en el següent desat. L'espai sobrant s'ha de netejar a l'ENTRADA (on ja es fa:
`request.data.get('nomenclatura').strip()`), no amagar-lo amb un índex que el tolera.

**PER TENANT vol dir PER SCHEMA.** `fhort.pom` viu a `SHARED_APPS` i a `TENANT_APPS`
(`settings.py:55,68`): la taula existeix a cada schema i l'índex també, o sigui que dos tenants
poden tenir el mateix `codi_client` sense xocar — que és el que ha de passar.

⚠️ **ORDRE OBLIGATORI: aquesta migració va DESPRÉS del buidat.** Amb les 24 files duplicades vives
la creació de l'índex falla. Va en migració pròpia i separada de l'esborrat també per una segona
raó: esborrar i fer `ALTER TABLE` dins de la mateixa transacció dona *pending trigger events*.

**EL BUIT.** `codi_client` no té `blank=True` però tampoc `default`: si algun dia dues files hi
arribessin amb `''`, la constraint les rebutjaria com a duplicades. És el comportament correcte
—un catàleg amb dos POMs sense codi no és un catàleg— i queda dit aquí perquè el dia que passi el
missatge d'error tingui explicació.
"""
from django.db import migrations, models
from django.db.models.functions import Upper


class Migration(migrations.Migration):

    dependencies = [
        ('pom', '0074_fittype_choices_al_dia'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='pommaster',
            constraint=models.UniqueConstraint(
                Upper('codi_client'),
                name='uniq_pommaster_codi_client_ci',
                violation_error_message=(
                    "Ja hi ha un POM al catàleg amb aquest codi (les majúscules no el distingeixen)."
                ),
            ),
        ),
    ]
