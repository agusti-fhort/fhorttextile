"""Resolució d'un `LandmarkRole` sobre un graf de vores. **La peça que F4 hereta.**

Un `LandmarkRole` no és una dada que ningú marqui: és una REGLA. `hps` no vol dir «algú
ha clicat aquí», vol dir «l'extrem que comparteixen l'escot i la costura d'espatlla». Això
és el que fa que el bloquejant A11 d'`INFORME_CORPUS_I_AUTOANCORATGE_2026-08-24` —«cap
dada del sistema identifica l'HPS»— deixi de ser un bloquejant un cop existeix `EdgeRole`.

Aquest mòdul és **pur**: no toca BD, no sap què és un `PatternSegment` i no importa res de
Django. Rep un graf —una llista de trams amb rol i dos extrems— i torna un punt. Que sigui
pur no és estètica: vol dir que F4 el pot cridar tant sobre geometria real com sobre el
mini-graf sintètic dels tests, i que el dia que la regla falli es podrà reproduir sense
muntar un tenant.

⚠️ **La regla és sòlida; que un DXF del taller es pugui etiquetar és una ALTRA pregunta**
(D2). El 2.371/2.371 de `hps_pont.txt` està mesurat sobre patrons on el generador havia
posat els rols. Aquest mòdul assumeix que algú —reconeixedor o patronista— ja els hi ha
posat; no els endevina.
"""
from __future__ import annotations

from dataclasses import dataclass


class LandmarkNoResolt(Exception):
    """La regla no es pot resoldre sobre aquest graf, i el motiu ha de ser llegible.

    S'aixeca —i no es torna `None`— perquè «no hi ha punt» i «hi ha punt i és l'origen»
    no s'han de poder confondre mai en una expressió. Un `None` silenciós acabaria sent un
    (0, 0) tres capes més amunt.
    """


@dataclass(frozen=True)
class Tram:
    """Un tram de vora amb rol: el que `PatternSegment` serà quan tingui `edge_role`.

    Els extrems són hashables i comparables (una tupla `(x, y)` o un id de `PatternPoint`).
    El mòdul no els interpreta tret que una regla ho demani explícitament (`lowest_y`).
    """

    edge_role: str
    p0: object
    p1: object

    @property
    def extrems(self) -> tuple:
        return (self.p0, self.p1)


def _trams_amb_rol(graf, rol: str) -> list:
    return [t for t in graf if t.edge_role == rol]


def _extrems_de_rol(graf, rol: str) -> set:
    """Tots els extrems dels trams d'un rol.

    Els trams del mateix rol es tracten com UN de sol —un escot pot venir esmicolat en
    tres trams i segueix sent un escot—, i els punts interiors (els que dos trams germans
    comparteixen) **no** són extrems del conjunt: apareixen dos cops i s'anul·len.
    """
    trams = _trams_amb_rol(graf, rol)
    if not trams:
        raise LandmarkNoResolt('cap tram amb rol «{}» al graf'.format(rol))
    comptes: dict = {}
    for t in trams:
        for p in t.extrems:
            comptes[p] = comptes.get(p, 0) + 1
    return {p for p, n in comptes.items() if n == 1}


def _y(p):
    """La y d'un punt, o `None` si el punt no és una coordenada.

    Els extrems poden ser tuples `(x, y)` o identitats opaques (una pk de
    `PatternPoint`). Les regles que llegeixen coordenades han de poder **saltar-se el
    control** quan no n'hi ha, en comptes de petar: un verificador que no es pot avaluar
    no és una regla incomplerta, és una regla que aquí no aplica.
    """
    try:
        return float(p[1])
    except (TypeError, IndexError, ValueError):
        return None


def _verifica_highest_y(punt, candidats, slug: str) -> None:
    """🚨 VERIFICADOR DE SANITAT, no desempat (llei d'ofici Agus, 26/08).

    `shared_endpoint` ja exigeix un únic extrem comú: el punt no cal triar-lo. El que fa
    `highest_y` és **comprovar que el punt que ha sortit és el que hauria de ser**. L'HPS
    és el punt més alt de la peça que porta l'escot; si `shared_endpoint` en retorna un
    que no ho és, el que falla no és el desempat —és que alguna vora està mal etiquetada,
    o que la peça ve girada al plànol. Val més que canti que no pas que passi.

    ⚠️ **Empat permès.** En un escot de barca, el centre de l'escot és a la mateixa alçada
    que l'HPS. La comprovació és «és DELS més alts», no «és EL més alt»: exigir estrictament
    el màxim faria vermell un patró correcte.
    """
    ys = [y for y in (_y(p) for p in candidats) if y is not None]
    y_punt = _y(punt)
    if y_punt is None or len(ys) < 2:
        return
    marge = max((max(ys) - min(ys)) * 0.01, 1e-9)
    if y_punt < max(ys) - marge:
        raise LandmarkNoResolt(
            "«{}»: l'extrem compartit surt a y={:.4g}, i el més alt dels operands és "
            "y={:.4g}. El verificador de sanitat `highest_y` diu que aquest punt no és "
            "l'alt: revisa les etiquetes de vora o l'orientació de la peça"
            .format(slug, y_punt, max(ys)))


def _junctura_del_mateix_rol(graf, rol: str, slug: str):
    """El vèrtex on es TOQUEN dos trams del MATEIX rol. L'àpex d'una pinça.

    🚨 **És el cas invers d'`_extrems_de_rol`, i per això no es podia resoldre amb ell.**
    Aquella funció torna els punts que apareixen UN cop —els caps del conjunt— i cancel·la
    els que apareixen dos, que són justament les juntures interiors. L'àpex d'una pinça és
    exactament un d'aquests: els dos braços hi arriben, o sigui que hi apareix dos cops i
    la funció germana el llençava.

    Una pinça són dos braços i un àpex (Montse C.09: «punt de pinça, o de plec»). Si en
    surt més d'un, la peça porta més d'una pinça i la regla no diu quina: es queixa en
    comptes de triar-ne una.
    """
    trams = _trams_amb_rol(graf, rol)
    comptes: dict = {}
    for t in trams:
        for p in t.extrems:
            comptes[p] = comptes.get(p, 0) + 1
    junctures = {p for p, n in comptes.items() if n == 2}
    if len(junctures) != 1:
        raise LandmarkNoResolt(
            '«{}»: hi ha {} juntures de «{}» i la regla en vol exactament 1 '
            '(la peça deu portar més d\'una pinça)'.format(slug, len(junctures), rol))
    return junctures.pop()


def _shared_endpoint(graf, entrada: dict, tiebreak: str = '', slug: str = ''):
    """L'extrem que dos rols comparteixen. **N'hi ha d'haver exactament un.**

    Zero vol dir que les dues vores no es toquen (o que hi falta un rol); més d'un vol dir
    que es toquen dos cops, que en un contorn tancat és una peça que no s'assembla al que
    la regla descrivia. Cap dels dos casos no s'ha de resoldre «triant-ne un».
    """
    a, b = entrada['a'], entrada['b']
    # Els dos operands SÓN el mateix rol: no es busca un extrem compartit entre dues
    # vores, es busca la JUNTURA de dues vores germanes. És l'àpex de la pinça.
    if a == b:
        return _junctura_del_mateix_rol(graf, a, slug or a)
    extrems_a = _extrems_de_rol(graf, a)
    extrems_b = _extrems_de_rol(graf, b)
    comuns = extrems_a & extrems_b
    if len(comuns) != 1:
        raise LandmarkNoResolt(
            '«{}» i «{}» comparteixen {} extrems, i la regla en vol exactament 1'
            .format(a, b, len(comuns)))
    punt = comuns.pop()
    if tiebreak == 'highest_y':
        _verifica_highest_y(punt, extrems_a | extrems_b, slug or '{}+{}'.format(a, b))
    return punt


def _far_endpoint(graf, entrada: dict, tiebreak: str, resolts: dict):
    """L'extrem LLUNYÀ d'un rol: dels seus dos caps, el que el desempat tria.

    `away_from:<slug>` és el desempat honest quan l'altre cap ja és un landmark resolt
    (el punt de sisa per al de sota-braç, l'HPS per al centre de l'escot): no es mesura
    res, s'exclou el que ja té nom. `lowest_y` només s'hi fa servir si aquell landmark no
    està resolt encara —és una lectura de coordenades, i les coordenades menteixen si la
    peça ve girada al plànol.
    """
    rol = entrada['a']
    extrems = _extrems_de_rol(graf, rol)
    if tiebreak.startswith('away_from:'):
        altre = resolts.get(tiebreak.split(':', 1)[1])
        if altre is not None:
            restants = extrems - {altre}
            if len(restants) != 1:
                raise LandmarkNoResolt(
                    'traient «{}» de «{}» queden {} extrems, no 1'
                    .format(tiebreak, rol, len(restants)))
            return restants.pop()
    if tiebreak == 'lowest_y':
        return min(extrems, key=lambda p: p[1])
    raise LandmarkNoResolt(
        'el rol «{}» té {} extrems i el desempat «{}» no els sap separar'
        .format(rol, len(extrems), tiebreak or '(cap)'))


def resol_landmark(regla, graf, resolts: dict | None = None):
    """Resol una regla de `LandmarkRole` sobre un graf de `Tram`. → el punt.

    `regla` és qualsevol objecte amb `derivable`, `derivation_op`, `derivation_input` i
    `derivation_tiebreak` — o sigui, una fila de `LandmarkRole`, però també un
    `SimpleNamespace` als tests. No es demana el model per no lligar un mòdul pur a l'ORM.

    `resolts` són els landmarks ja calculats, per slug: és el que permet que
    `underarm_point` s'expressi com «l'altre cap de la sisa» en comptes d'una lectura de
    coordenades.
    """
    resolts = resolts or {}
    if not regla.derivable:
        raise LandmarkNoResolt(
            'la regla no és derivable: aquest punt es marca, no es calcula')
    op = regla.derivation_op
    if op == 'shared_endpoint':
        return _shared_endpoint(graf, regla.derivation_input,
                                regla.derivation_tiebreak, getattr(regla, 'slug', ''))
    if op == 'far_endpoint':
        return _far_endpoint(graf, regla.derivation_input,
                             regla.derivation_tiebreak, resolts)
    raise LandmarkNoResolt("l'operació «{}» encara no té implementació".format(op))
