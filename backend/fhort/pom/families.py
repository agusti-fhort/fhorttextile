"""LES FAMÍLIES D'EIXOS D'UNA INSTÀNCIA — la llei d'Agus (26/08), i prou.

🚨 PER QUÈ AIXÒ ÉS UN MÒDUL I NO ES QUEDA AL MODEL. Les migracions de dades treballen amb
models HISTÒRICS (`apps.get_model`), que **no porten els mètodes de la classe viva**: una
migració que hagi de recompondre un slug no pot cridar `MeasurementInstance.composa`. Si la
llei visqués només al model, la migració se n'hauria d'escriure una còpia — i una còpia de
l'ordre canònic és exactament el defecte que aquest tram tanca.

Aquí no hi ha res de Django a posta: es pot importar des d'una migració, des d'un test pur i
des del model viu. `MeasurementInstance` n'és el consumidor, no el propietari.

LA LLEI, SENCERA
────────────────
  1 PEÇA         {front, back}                mirall
  2 BANDA        {left, right}                mirall
  3 VERTICALITAT {top, bottom}                mirall
  4 COSTURA      {side, waistband_seam}       SENSE mirall — no és binomial
  5 LÍNIA        {cf, cb}                     mirall   ← família PRÒPIA, NO és peça
  Ú ESTAT        {relaxed, extended}          mirall

  · Excloents DINS de família · combinables ENTRE totes.
  · Les redundàncies (`front`+`cf`) són LEGALS: criteri de qui mesura, no error del sistema.
  · **L'ORDRE D'AQUESTA TUPLA ÉS L'ORDRE CANÒNIC** i el sistema l'imposa, MAI l'alfabet.
  · El MIRALL és propietat de la FAMÍLIA i només el tenen les binomials. Es declara com a
    DADA; **cap operació de gir s'implementa** (el motor ja els demanarà).
"""

FAM_PECA = 'PECA'
FAM_BANDA = 'BANDA'
FAM_VERTICALITAT = 'VERTICALITAT'
FAM_COSTURA = 'COSTURA'
FAM_LINIA = 'LINIA'
FAM_ESTAT = 'ESTAT'

#: `(família, (slugs...), té_mirall)` EN ORDRE CANÒNIC.
FAMILIES = (
    (FAM_PECA,         ('front', 'back'),          True),
    (FAM_BANDA,        ('left', 'right'),          True),
    (FAM_VERTICALITAT, ('top', 'bottom'),          True),
    (FAM_COSTURA,      ('side', 'waistband_seam'), False),
    (FAM_LINIA,        ('cf', 'cb'),               True),
    (FAM_ESTAT,        ('relaxed', 'extended'),    True),
)

SEPARADOR = '-'


def familia_de(slug):
    """La família d'un slug simple, o `''` si no és del vocabulari de la casa.

    🔑 **CAP SLUG DE LA SEMBRA ÉS ORFE.** El `''` queda per al que un tenant s'hagi creat pel
    seu compte: allò no es jutja ni s'ordena, es deixa passar tal com arriba.
    """
    for clau, slugs, _ in FAMILIES:
        if slug in slugs:
            return clau
    return ''


def mirall_de(slug):
    """El REVERS d'un slug dins de la seva família, o `''` si la família no és binomial.

    `side` i `waistband_seam` **no en tenen**: són dues costures diferents, no l'una el revers
    de l'altra.
    """
    for _clau, slugs, mirall in FAMILIES:
        if mirall and slug in slugs and len(slugs) == 2:
            return slugs[1] if slugs[0] == slug else slugs[0]
    return ''


def ordre_canonic(slug):
    """El PES d'un slug: com més baix, més a l'esquerra del slug compost.

    El desconegut va AL FINAL, i com que `sorted` és estable hi conserva l'ordre d'entrada: no
    es pot inventar on cau un slug del qual no se sap la família, i moure'l seria canviar-li la
    clau a algú altre.
    """
    for i, (_clau, slugs, _m) in enumerate(FAMILIES):
        if slug in slugs:
            return i
    return len(FAMILIES)


def trams_de(valor, separador=SEPARADOR):
    """El slug compost, partit i net. `''`/`None` → `[]`."""
    return [t for t in str(valor or '').split(separador) if t]


def composa(trams, separador=SEPARADOR):
    """Els trams en ORDRE CANÒNIC, sense repetits. **La porta única de composició del backend.**

    És la mateixa llei que `composaInstancia` a `frontend/src/utils/diccionariMesures.js`; les
    dues bandes han de dir el mateix perquè **l'ordre entra a la clau única de cinc taules**.
    """
    vistos, nets = set(), []
    for t in (trams or []):
        t = str(t or '').strip()
        if t and t not in vistos:
            vistos.add(t)
            nets.append(t)
    return separador.join(sorted(nets, key=ordre_canonic))


def normalitza(valor, separador=SEPARADOR):
    """Un slug compost tal com la llei el vol escrit. Idempotent.

    Un slug simple (o buit) torna igual: no hi ha res a ordenar.
    """
    trams = trams_de(valor, separador)
    return composa(trams, separador) if len(trams) > 1 else (trams[0] if trams else '')
