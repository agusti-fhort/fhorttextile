"""ORDRE CANÒNIC DELS SLUGS D'INSTÀNCIA (llei d'Agus, 26/08).

Fins avui l'ordre entre eixos d'un slug compost el decidia `order_by('eix')` —**alfabètic**:
`'ESTAT' < 'POSICIO'`— i el sistema componia `extended-right` mentre la llei escrita deia
posició-abans-que-estat. La BD en porta la prova.

Amb l'ordre nou viu i les files velles sense tocar, **re-desar una germana composaria una clau
que no casa amb la seva fila**: l'upsert no la trobaria i faria un INSERT en comptes d'un
UPDATE, amb 200 OK i en silenci. Per això la llei nova i aquesta migració són **el mateix
commit**: separar-les deixaria una finestra en què el sistema escriu claus que no troba.

⚠️ **LA MIGRACIÓ NO TRIA MAI.** Si el slug canònic ja el té una altra fila de la mateixa clau,
AVORTA i llista: fusionar dues germanes és una decisió de domini. I el vocabulari que no és de
la casa (una instància que s'hagi creat un tenant) no es toca — no té ordre canònic i
inventar-l'hi seria canviar-li la clau a algú.

⚠️ **CAP `esperades` AQUÍ.** El canari de 4 és de la correguda controlada a staging
(`manage.py normalitza_instancies --dry-run --esperades 4`); aquesta migració viatja al
mini-tren i s'aplica a PROD **sobre una població que encara no s'ha comptat**, i assertar-hi un
número que no sabem seria aturar el tren per força. El que sí que hi ha sempre és el RECOMPTE
al log, per schema i per taula: és l'única traça que quedarà de la correguda de PROD.

Cens de staging el 26/08 (`--dry-run`): `public` 0 · `fhort` **4** · `los` 0 · 0 col·lisions.
"""
from django.db import migrations

from fhort.pom.normalitza_instancies import aplica


def endavant(apps, schema_editor):
    aplica(apps, schema=getattr(schema_editor.connection, 'schema_name', '?'))


def enrere(apps, schema_editor):
    """NO es desfà, i no és un oblit.

    L'ordre canònic és el que la llei diu; tornar-hi enrere voldria dir recompondre els slugs
    amb l'ordre ALFABÈTIC que aquest tram existeix per matar — i el codi que el sabia fer ja no
    hi és. Desfer la migració no restauraria l'estat anterior: en fabricaria un de nou i pitjor.
    Les dades no es perden en cap cas: cap fila s'esborra, només se'n reordenen els trams.
    """
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('pom', '0085_unicitat_generica_seampairtemplate'),
        # Les altres 8 taules amb `instancia` no són de `pom`: han d'existir abans que això
        # corri, o la normalització en saltaria la meitat i deixaria el sistema amb DUES
        # convencions vives — que és exactament el que la llei 1 d'Agus prohibeix.
        ('models_app', '0087_m3_cicle_vida_model'),
        ('fitting', '0028_e2_b1_presa_at'),
    ]

    operations = [
        migrations.RunPython(endavant, enrere),
    ]
