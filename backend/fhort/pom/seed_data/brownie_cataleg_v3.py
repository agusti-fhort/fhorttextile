"""Taula de RESOLUCIÓ del catàleg Brownie v3 (full CATALEG de BROWNIE_CATALEG_POM_v3.xlsx).

🔑 **EL CRITERI (ratificat per Agus, 05/08).** El v3 NO importa `pom_id`. Importa NOM +
GRADING + ESTRUCTURA i els casa contra el que STAGING ja té. La columna `pom_id` del full és
traçabilitat de PROD —51 dels 119 apunten a un POM diferent del que l'àlies viu ja fa servir,
i 5 pks ni existeixen (v. `docs/diagnosis/DIAGNOSI_BROWNIE_V3_POM_ID.md`)— i **no s'escriu
mai**. Cap CREATE amb un pk importat.

L'ordre de resolució de cada codi és:

  1. **Àlies viu de Brownie** → aquell POM. La identitat no es toca (D1); només s'hi
     actualitza nom/grading.
  2. **`RESOLUCIO`** (aquest fitxer) → un POM que ja existeix a staging, normalment arribat
     per LOSAN. Es carrega un `CustomerPOMAlias` de Brownie a sobre; NO s'encunya (D3).
  3. **`ENCUNYAR`** → no existeix enlloc. POM nou (D4), i només amb el vist-i-plau previ.

**UN CONCEPTE FÍSIC, UN POM, N ÀLIES DE CLIENT.** És el mateix principi a D2 i a D3: si
Brownie necessita una etiqueta pròpia per a un concepte que ja té POM, l'etiqueta va a
l'àlies i el nom canònic no es toca — sobretot si LOSAN ja el fa servir.
"""

#: Codis del v3 SENSE àlies viu de Brownie que resolen per CONCEPTE contra un POM existent
#: (D3 · reutilitzar, mai encunyar). `codi → (pom_id, per què)`.
#:
#: La majoria són POMs que van entrar per LOSAN, tal com el mateix full insinua a la columna
#: NOTA («🆕 de LOSAN (D6)», «(S37)», «(AB)»…). El full en dona el pk de PROD; aquí hi ha el
#: de staging, resolt pel NOM, que és el que el criteri mana.
RESOLUCIO = {
    # ── el rebateig G1↔D1 ─────────────────────────────────────────────────────────────
    # 453 es diu avui «Bottom hem / Bottom rib height» i conflacta les DUES coses que el
    # rebateig separa. Es queda amb el baix (D1) i el canalé se'n va al G1 nou (ENCUNYAR).
    'D1':  (453, 'ex-G1 · el POM que ja porta el baix; el rebateig el hi deixa'),
    # ── conceptes que ja tenia el catàleg del tenant ──────────────────────────────────
    'M':   (311, 'LEG OP · Leg opening — mateix concepte, exacte'),
    'PR2': (357, 'PKT WB · Pocket placement from waistband — el POM que la reparació del '
                 '03/08 va crear; és la lectura del CATALEG, que mana (D5)'),
    'ZF':  (363, 'BELT W · Belt width (el codi passa de FZ a ZF: Z=complements)'),
    'ZL':  (362, 'BELT L · Belt length (era LZ)'),
    'ZL1': (660, 'SR10 · BOW LENGTH — exacte. L\'àlies LZ1 viu apuntava a ELBOW LENGTH, que '
                 'era fals; no es repunta, es declara el codi nou al POM correcte'),
    'U4':  (578, 'U4 · FLOUNCE HEIGHT — exacte. El full en deia 580, que a staging és V12/FOLD'),
    # ── entrecuix (família C) ─────────────────────────────────────────────────────────
    'CR':  (539, 'D6 · FRONT CROTCH WIDTH — exacte (el full ja diu «de LOSAN (D6)»)'),
    'CR1': (541, 'D7 · BACK CROTCH WIDTH — exacte (el full ja diu «de LOSAN (D7)»)'),
    'CR4': (413, 'CR L · Crotch length — exacte (el full ja diu «de LOSAN (CR L)»)'),
    # ── coll ──────────────────────────────────────────────────────────────────────────
    'CP':  (582, 'S37 · COLLAR PEAK — exacte (el full ja diu «de LOSAN (S37)»)'),
    'CB1': (584, 'AB · CONTOUR COLLAR TOTAL — exacte (el full ja diu «de LOSAN (AB)»)'),
    # ── caputxa ───────────────────────────────────────────────────────────────────────
    'H1':  (614, 'S53 · HOOD WIDTH LOCATION — «placement» i «location» són el mateix eix'),
    'HP':  (426, 'S.56 · HOOD PIECE WIDTH — exacte (el full ja diu «de LOSAN (S.56)»)'),
    'HZ':  (615, 'SR2 · DRAWSTRING LENGTH (measured at point where ties) — mateix concepte'),
    'HZ1': (616, 'SR3 · DRAWSTRING CHANNEL — exacte'),
    # ── traus, botons i ullets (família K nova, POMs vells) ───────────────────────────
    'K':   (669, 'C.13 · BUTTONHOLE LOCATION — mateix eix que «placement»'),
    'KU':  (385, 'C.14-M79 · EYELET LOCATION — íd.'),
    # ── pinces i plecs (família Q nova, POMs vells) ───────────────────────────────────
    'Q':   (397, 'V.13-M79 · DART LENGTH — exacte'),
    'QP':  (396, 'V.14-M79 · DART LOCATION — mateix eix que «placement»'),
    'QTP': (566, 'T13 · PLEAT LOCATION — íd.'),
    # ── gomes i pespunts ──────────────────────────────────────────────────────────────
    'WP':  (416, 'EL POS · Elastic location — mateix eix que «placement»'),
    'XV':  (513, 'U1 · JETTING WIDTH — exacte'),
}

#: REPUNTS · àlies VIUS de Brownie que apunten a un POM que no és el seu concepte, i que
#: tenen destí correcte JA EXISTENT. `codi → (pom_nou, pom_vell, per què)`.
#:
#: Repuntar un àlies viu és una operació que la sembra no fa mai sola: cadascun d'aquests té
#: acta. La mesura ja desada NO es mou —viu a `(model, pom, capa, instancia)` i el POM vell
#: continua sent el seu—; el que canvia és a quin POM apuntarà la propera vegada que el
#: matcher resolgui aquest codi.
REPUNTS = {
    # Ratificat per Agus 05/08. 296 es diu «Sleeve width at elbow», que és exactament el que
    # JJ mesura: JJ s'hi queda amb les 10 mesures vives. IC1 («elbow patch width») no hi
    # pintava res i se'n va a 496, que ja porta el codi escrit i és lliure (0 àlies, 0 mesures).
    # ⚠️ 296 el toquen també LOS:H4 i LOS:SR9 — el seu nom NO canvia de significat, només hi
    # perd un àlies de Brownie que hi estava mal enganxat.
    'IC1': (496, 296, 'ELBOW WIDTH · 496 ja porta el codi IC1 i és lliure; 296 es queda per '
                      'a JJ, que sí que és «sleeve width at elbow» (10 mesures vives)'),
    # 342 «BTN SP · Button spacing» és EXACTAMENT el que U1 mesura, i és lliure d'àlies. El
    # 440 on apunta avui és «Height sequins piece (CF)», que no té res a veure. (És l'únic
    # cas de tot el full on el `pom_id` de PROD i el de staging coincideixen per casualitat.)
    'U1':  (342, 440, 'BTN SP · Button spacing — exacte i lliure d\'àlies. 440 «Height '
                      'sequins piece (CF)» no és el concepte'),
}

#: Codis que NO existeixen enlloc —ni a Brownie ni a LOSAN ni a la resta del catàleg— i que
#: per tant s'han d'ENCUNYAR (D4). `codi → per què no es reutilitza res`.
#:
#: ⚠️ **Es llisten abans d'encunyar-los, i la sembra no en crea cap sense `--encunyar`.**
#: Encunyar és l'única operació d'aquest tram que afegeix identitats al catàleg del tenant.
ENCUNYAR = {
    'G1':  'Rib height. El rebateig 05/08 li torna el significat oficial; el contingut vell '
           'se\'n va a D1 (POM 453). No hi ha cap POM de «rib height» sol: 453 el conflacta '
           'amb el baix, 300 és «Rib cuff height» i 329 «Rib hem height» — tots tres són una '
           'altra cosa.',
    'FS5': 'Lining length difference. POM nou per decisió d\'Agus (opció a, FIXED 1 cm). El '
           'més proper és 596 «FRONT LINING LENGTH», que és una llargada, no una diferència.',
    'CR3': 'Crotch width placement. Existeixen 538 (D18 · FRONT) i 540 (D19 · BACK) però cap '
           'de genèric, i el v3 el declara un de sol. Triar-ne un seria decidir davant/darrere.',
    'KB':  'Button placement. 342 és «Button spacing» (separació entre botons, no col·locació) '
           'i 498/499 són el 1r i l\'últim botó, que són fites.',
    'QT':  'Pleat width. 345 és «Pleat depth» (profunditat ≠ amplada) i 567 «PLEAT» a seques.',
    'N':   'Motive placement. Només hi ha 683 «BOTTOM MOTIVE LOCATION», que és el motiu del '
           'baix; el v3 vol UN POM genèric + zona, explícitament no els 5 codis de LOSAN.',
    'NF':  'Motive width. Cap.',
    'NL':  'Motive height. Cap.',
    'W':   'Elastic width. 414/415 són la goma relaxada i estirada (ESTATS d\'una mesura), no '
           'la seva amplada.',
    'X':   'Stitching width. Només 674 «WAIST HEIGHT STITCHING», que és el pespunt d\'un lloc '
           'concret.',
    'XP':  'Stitching placement. Cap.',
    'GD':  'Godet length at longest point. Cap POM de godet a staging, i el pk del full (795) '
           'no existeix.',
    'GD1': 'Godet length at the seams. Íd. (796 tampoc existeix).',
    'SLT': 'Slit. 461 és «Sleeve slit», específic de màniga; el v3 el vol genèric. El pk del '
           'full (871) no existeix i l\'àlies «0» que hi apuntava a PROD, aquí va a 461.',
    # ── els que arriben d'una COL·LISIÓ o d'una DERIVA (ratificat Agus 05/08) ──────────
    # Llei aplicada: «si la descripció no coincideix, no és el mateix POM, encara que el
    # número sigui temptadorament proper». Els candidats hi eren; cap no diu el que cal.
    'P':   'Center back yoke height. Col·lisió a 484 amb L: L s\'hi queda (mateix nom, BACK '
           'YOKE) i P no hi cap. 505 és «Back yoke SIDE height» i 564 «BACK YOKE CENTER '
           'LENGTH» — costat≠centre, llargada≠alçada. Agus: no forcis 505.',
    'P1':  'Side yoke height. L\'àlies viu va a 442 «Chest piece height at center», que és '
           'peça de pit, no canesú. Els lliures són 505 (back yoke side HEIGHT, però back) i '
           '399 (front yoke LENGTH); 565 «SIDE YOKE LENGTH» és de LOSAN i és llargada.',
    'P2':  'Center front yoke height. L\'àlies viu va a 441 «Chest piece height at side '
           'seam». Els candidats de canesú frontal (399, 561, 562) diuen tots LENGTH.',
    'U':   'Front overlap. L\'àlies viu va a 439 «Width sequins piece (CF)». El full afirma '
           '«la BD mana: U és FRONT OVERLAP», però és la BD de PROD: a staging no hi ha cap '
           'POM de creuament (343 «Placket width» és de LOSAN, amb 9 mesures).',
    'IC':  'Elbow patch placement. L\'àlies viu va a 495 «ELBOW POSITION», que és on és el '
           'colze, no on va la coquera. 378 és «Chest patch pocket position».',
    'F1':  'Curve at side (difference between CB length and side seam). Col·lisió a 437 amb '
           'F i F2. El full ho subratlla: «NO és TOTAL SIDE LENGTH: és una DIFERÈNCIA». '
           'L\'únic lliure de diferències és 433 «Difference Bottom», que és del baix.',
    'F2':  'Total side length. Col·lisió a 437. El més proper és 283 «SS · Side seam length» '
           '—de LOSAN i amb 14 mesures vives—, i «side seam length» i «total side length» no '
           'són prou el mateix per enganxar-hi Brownie sense acta.',
    'F3':  'Front center total length. Col·lisió a 389 «TOTAL LENGTH», que és de LOSAN (LOS:M) '
           'i no es pot renombrar. Desdoblar-lo és el que el brief demana: 389 es queda '
           'servint només el que li correspon.',
    'F4':  'Back center total length. Íd. F3.',
}

#: Codis que el brief demana però que NO es poden encunyar perquè no hi ha què encunyar-hi.
#: Es reporten i prou.
SENSE_DEFINICIO = {
    'J4': 'El brief el demana «nou i buit», però J4 NO ÉS A CAP FULL del v3: no en tenim nom, '
          'ni lògica, ni grading, ni família. Un POM sense nom no és un POM. I el '
          'compartiment que el motiva («pom 504 COMPARTIT amb IC i J4») no existeix a '
          'staging: 504 és «I4 · Sleeve length from CB over shoulderpoint» amb àlies BRW:I4, '
          'i IC ja té el seu POM propi (495).',
}

#: Acrònims que la caixa de frase NO abaixa (llei de nomenclatura del brief).
ACRONIMS = {'CF', 'CB', 'HPS', 'HSP', 'CT', 'AH', 'FS', 'PP'}


def caixa_de_frase(nom: str) -> str:
    """«BOTTOM HEM HEIGHT» → «Bottom hem height», però «Neck drop from HPS» conserva HPS.

    Només s'aplica als noms NOUS (els que s'encunyen): reescriure els que ja existeixen
    seria tocar identitats vives per una qüestió d'estil, que no és el que el brief demana.
    Un nom que ja ve en caixa de frase no el toca ningú.
    """
    if not nom:
        return nom
    paraules = nom.split(' ')
    fora = []
    for i, p in enumerate(paraules):
        nu = p.strip('()')
        if nu.upper() in ACRONIMS:
            fora.append(p.replace(nu, nu.upper()))
        elif i == 0:
            fora.append(p[:1].upper() + p[1:].lower())
        else:
            fora.append(p.lower())
    return ' '.join(fora)
