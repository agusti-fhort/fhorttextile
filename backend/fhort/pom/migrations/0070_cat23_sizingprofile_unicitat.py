# CAT2.3 (2026-08-07) — `SizingProfile`: esborrar els duplicats i posar la clau natural.
#
# 5 files vives violaven la unicitat en 2 grups. El cens de CAT2.0 va ensenyar que NO són el
# mateix cas, i per això la decisió va pujar a l'Agus:
#
#   GRUP A · 539 · 540 · 541 — duplicats accidentals de debò: cap `parent_profile`, tots v1,
#            rulesets diferents (175 · 176 · 177). Criteri del brief: es queda el que té
#            ruleset viu i, com que empaten, **el més antic → 539**.
#   GRUP B · 288 · 510 — NO era un duplicat: 510 té `parent_profile=288`, o sigui que és una
#            VERSIÓ (el mecanisme que el model documenta com «apunta al pare si és versió
#            client»). Tots dos amb `customer=NULL`, i per això comparteixen clau natural.
#            **Decisió d'Agus (07/08): esborrar 510 i posar la clau.** El seu ruleset (98) és
#            bessó BYTE A BYTE del canònic 81, que és el del 288: la versió no aportava res.
#            ⚠️ Conseqüència acceptada: una versió del MATEIX àmbit deixa de ser possible
#            sense canviar `customer`. El versionat per `parent_profile` queda, de facto,
#            jubilat per a aquest cas.
#
# El delete no és cec: torna a comprovar la clau natural de cada fila abans de tocar-la i
# AVORTA si el que troba no és el que el cens deia.
from django.db import migrations, models

#: (id que es queda, ids que cauen). Els ids són d'aquest tenant; a `public` i `los` no hi ha
#: cap `SizingProfile`, o sigui que allà tot això és un no-op.
GRUPS = [(539, [540, 541]), (288, [510])]

CLAU = ('target_id', 'garment_type_id', 'construction_id',
        'fit_type_id', 'size_system_id', 'customer_id')


def neteja(apps, schema_editor):
    SizingProfile = apps.get_model('pom', 'SizingProfile')

    for es_queda, cauen in GRUPS:
        viu = SizingProfile.objects.filter(pk=es_queda).first()
        if viu is None:
            continue                       # schema sense aquestes files: res a fer
        clau_viva = {c: getattr(viu, c) for c in CLAU}
        for pk in cauen:
            mort = SizingProfile.objects.filter(pk=pk).first()
            if mort is None:
                continue
            if {c: getattr(mort, c) for c in CLAU} != clau_viva:
                raise RuntimeError(
                    f'CAT2.3 ATURA · el perfil {pk} JA NO comparteix àmbit amb {es_queda}. '
                    'El cens deia que sí: no s\'esborra res a cegues.'
                )
            # L'única relació entrant de `SizingProfile` és ella mateixa (`parent_profile`,
            # SET_NULL). Si en penja algú, es reassigna al que es queda en comptes de deixar
            # un NULL mut — i si apareix qualsevol altra cosa, això peta i és el que volem.
            SizingProfile.objects.filter(parent_profile_id=pk).update(parent_profile_id=es_queda)
            mort.delete()

    # Postgres no deixa fer `ALTER TABLE` sobre una taula amb events de trigger pendents, i un
    # DELETE dins la mateixa transacció n'hi deixa (els triggers de les FK són DEFERRED). Sense
    # això, l'`AlterUniqueTogether` de sota peta amb «pending trigger events» a tot schema on
    # s'hagi esborrat alguna fila — i `public`, que no n'esborra cap, passaria i amagaria el
    # problema. Forçar-los ara els resol dins d'aquesta mateixa transacció.
    schema_editor.execute('SET CONSTRAINTS ALL IMMEDIATE')


def enrere(apps, schema_editor):
    """Buida a posta: un esborrat signat no es desfà sol."""


class Migration(migrations.Migration):

    dependencies = [
        ('pom', '0069_cat21a_talla_base_label'),
    ]

    operations = [
        migrations.RunPython(neteja, enrere),
        migrations.AlterUniqueTogether(
            name='sizingprofile',
            unique_together={('target', 'garment_type', 'construction', 'fit_type',
                              'size_system', 'customer')},
        ),
    ]
