"""El sufix de la instància `bottom` passa de `B` a `BM`.

DECISIÓ D'AGUS (22-23/08): la POSICIÓ passa a tenir DOS EIXOS —lateral (left/right) i CARA
(front/back)—, i la cara posterior vol el sufix natural `B` (back). Avui `B` és de `bottom`,
i dos sufixos iguals a l'eix POSICIÓ farien que el codi proposat d'una germana no digués de
quina cara parla: `BB` seria «Waist width · bottom» i «Waist width · back» alhora.

Per això aquest rebateig va PRIMER i sol: `bottom` = `BM`, i `B` queda lliure per a `back`
(migració germana, al commit següent).

QUÈ ES TOCA I QUÈ NO
  · **El `slug` NO es toca.** `bottom` segueix sent `bottom`: és el contracte que desen les
    columnes `instancia` de les taules de mesura (llei G9). Aquí només canvia el `sufix`, que
    és la PROPOSTA de codi en crear una germana.
  · **No es toca cap `nom_fitxa` ja escrit.** El sufix proposa; qui bateja és el patronista, i
    el nom d'una fila viva és seu. A staging hi ha files amb `instancia='bottom'` i codi ja
    compost amb la `B` vella (`YB`, `BB`): es queden exactament com són. Només les germanes
    NOVES es proposaran amb `BM`.
  · 🚨 **NO ES TOCA `POMMaster`.** Existeix el POM de codi `B` («Waist width») i el seu codi
    NO té res a veure amb aquest sufix: són dues taules i dos conceptes. Aquesta migració
    filtra per `slug='bottom'` sobre `MeasurementInstance` i no pot arribar-hi ni per accident;
    el test `PomBTest` ho mesura en comptes de confiar-hi.

GUARDA DE RECOMPTE (llei S44): el `slug` és únic, o sigui que la fila esperada és UNA com a
molt. Si n'aparegués cap més, s'ATURA dins de l'atomic en comptes d'escriure a cegues.

ON CORRE: `fhort.pom` viu a SHARED **i** a TENANT alhora → `migrate_schemas` la passa per
`public` i per cada tenant tot sol. Mai `--schema` (llei del CLAUDE.md).

REVERSIBLE: `BM` → `B`, amb la mateixa guarda. Desfer-la només té sentit mentre `back` no
existeixi; per això el `reverse` NO el desfà si `back` ja hi és (dos `B` a l'eix seria el dany
que tot això ve a evitar).

⚠️ La FONT del sufix és `seed_measurement_instances.py`, alineada al mateix commit: sense
això, la propera passada de la sembra tornaria a posar `B` i aquesta migració seria un pedaç
d'un dia (la lliçó de `0060_extended_net`).
"""
from django.db import migrations

SLUG = 'bottom'
SUFIX_VELL = 'B'
SUFIX_NOU = 'BM'
#: `MeasurementInstance.slug` és `unique=True`: una fila per schema com a molt.
ESPERADES = 1


def _mou(Instancia, de, a, esperades=ESPERADES):
    """Mou el sufix de `bottom` amb guarda de recompte EXACTE. → files tocades.

    `esperades` és paràmetre i no constant tancada perquè la guarda sigui EXERCIBLE: el
    `slug` és únic i fabricar-ne una segona fila per provar-la és impossible, o sigui que la
    prova l'estreny (`esperades=0`) i mesura que ATURA de debò.
    """
    tocables = Instancia.objects.filter(slug=SLUG, sufix=de)
    n = tocables.count()
    if n > esperades:
        raise RuntimeError(
            f'0079: {n} files amb slug={SLUG!r} i sufix={de!r}; se n\'esperava {esperades} com a '
            f'molt. La migració s\'atura: el sufix es mou a mà quan se sàpiga d\'on surten.')
    fetes = tocables.update(sufix=a)
    if fetes != n:
        raise RuntimeError(f'0079: n\'havia de tocar {n} i n\'ha tocat {fetes}.')
    return fetes


def endavant(apps, schema_editor):
    _mou(apps.get_model('pom', 'MeasurementInstance'), SUFIX_VELL, SUFIX_NOU)


def enrere(apps, schema_editor):
    Instancia = apps.get_model('pom', 'MeasurementInstance')
    # Tornar `BM` a `B` amb `back` viu deixaria dos sufixos `B` a l'eix POSICIÓ, que és
    # exactament el dany que aquest tram tanca. Es deixa com és, i es diu.
    if Instancia.objects.filter(slug='back').exists():
        return
    _mou(Instancia, SUFIX_NOU, SUFIX_VELL)


class Migration(migrations.Migration):

    dependencies = [
        ('pom', '0078_sobirania_pom_copy_on_write'),
    ]

    operations = [
        migrations.RunPython(endavant, enrere),
    ]
