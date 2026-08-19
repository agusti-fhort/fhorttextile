"""Eines de PROVES del catàleg de POMs. No s'importa mai des de codi de producció.

⚠️ **PER QUÈ EXISTEIX AIXÒ.** La migració `pom/0075` va posar
`uniq_pommaster_codi_client_ci` — `codi_client` únic per tenant i insensible a majúscules —
i amb ella una família sencera de proves va passar a ser **impossible de muntar**: les que
defensen què fa el sistema quan el catàleg JA TÉ dos POMs amb el mateix codi.

Aquell estat no el pot fabricar cap camí viu (la BD el rebutja), però el GUARD que el
gestiona segueix al codi de producció (`import_session_poms_view` → 409 `codi_duplicat`,
amb candidats). Mentre el guard hi sigui, les seves proves l'han de poder exercitar; si
s'esborressin, el dia que algú retirés la constraint tornaria l'incident de PROD del 27/07
(`MultipleObjectsReturned` → 500 → sessió d'import descartada) sense cap xarxa.

🚩 **DECISIÓ PENDENT (Agus):** el 409 ha passat a ser defensa en profunditat d'un estat que
la BD ja no permet. O es retira el guard i s'esborren aquestes proves, o es queda tal com
està. Fins que es decideixi, es queda — retirar-lo és una decisió de producte, no de tram.
"""
from django.db import connection

from fhort.pom.models import POMMaster

NOM_CONSTRAINT = 'uniq_pommaster_codi_client_ci'


def desactiva_unicitat_codi_client():
    """Treu la constraint d'unicitat de `codi_client` DINS de la transacció de la prova.

    No la torna a posar a posta: a PostgreSQL el DDL és transaccional i el `rollback` que
    tanca cada `TestCase` la restaura sencera. Tornar-la a afegir aquí fallaria sempre —
    les files duplicades que la prova acaba de crear encara hi són.

    Cridar-ho des de `setUp()`, i NOMÉS a les proves que necessiten l'estat que la
    constraint prohibeix. Qualsevol altra prova ha de veure la llei tal com és a producció.
    """
    constraint = next(
        (c for c in POMMaster._meta.constraints if c.name == NOM_CONSTRAINT), None)
    if constraint is None:      # la constraint s'ha retirat del model: no hi ha res a fer
        return
    with connection.schema_editor(atomic=False) as editor:
        editor.remove_constraint(POMMaster, constraint)
