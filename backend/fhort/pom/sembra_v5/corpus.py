"""EL CORPUS DE LA SEMBRA v5 — un sol arxiu, verificat abans de llegir-ne cap cel·la.

`CATALEG_SISTEMA_POM_v5_COMPLET_r2.xlsx` és la **font única de contingut** del tram: 165 POMs,
14 famílies i 105 àlies de Brownie. Cap comanda de `sembra_v5` llegeix res d'enlloc més.

🔒 **EL HASH ES VERIFICA ABANS DE LLEGIR, I ABORTA.** L'arxiu viatja per dos camins distints
(a staging viu al repo, a PROD a `/root/cens_v5/material/`) i les dues meitats del gate final
—empremta d'staging == empremta de PROD— només tenen sentit si les dues han llegit **els
mateixos bytes**. Un `r2` retocat a mà en un dels dos entorns donaria dos catàlegs diferents
amb totes les comandes en verd, i el delta diria «divergeixen» sense poder dir per què.

🚨 **QUATRE COLUMNES DEL FULL NO TENEN DESTÍ A L'ESQUEMA** (v. `COLUMNES_SENSE_DESTI`). No
s'inventa cap camp i no s'aboquen a `notes`: és la mateixa decisió que ja es va prendre a la
sembra v4 (`REPORT_SEMBRA_V4_2026-08-09.md` §3) i el brief la torna a manar («PARAR i reportar
el forat. No inventar schema»). Cada comanda que en toca alguna ho diu al seu report.
"""
import hashlib
from decimal import Decimal
from pathlib import Path

from django.core.management.base import CommandError

#: L'empremta de l'arxiu, del brief. Si canvia el contingut, canvia aquí i es diu a l'acta.
SHA256_R2 = '07d29bdc2c6fd3355dca8738839d9edce94e4d72cddc0730f5152457ca60e7eb'
NOM_XLSX = 'CATALEG_SISTEMA_POM_v5_COMPLET_r2.xlsx'

#: Els dos camins del brief, EN ORDRE. El primer que existeix mana; el hash decideix si val.
_ARREL = Path(__file__).resolve().parents[4]          # …/ftt-staging
CAMINS = (_ARREL / 'docs' / 'ordres' / NOM_XLSX,      # staging: el repo
          Path('/root/cens_v5/material') / NOM_XLSX)  # PROD: el material del cens

#: Recomptes DECLARATS del corpus. Són guarda, no documentació: si el full no els dona, cap
#: comanda arrenca (una fila perduda en un desa d'Excel no es veu de cap altra manera).
N_POMS, N_FAMILIES, N_ALIES = 165, 14, 105
N_POMS_ACTIUS, N_POMS_INACTIUS = 161, 4

#: 🚨 Columnes del full que NO tenen camp al model, i on aniran el dia que Agus n'autoritzi la
#: migració. Es reporten a cada correguda perquè el forat no es pugui oblidar en silenci.
COLUMNES_SENSE_DESTI = {
    'Pos.': "ordre del POM dins la família — `POMGlobal` no té `display_order` "
            "(`POMCategory` sí, però és de la FAMÍLIA, no del POM)",
    'Règim': "Amplada · Llarg · Col·locació · Fix — cap camp a `POMGlobal` ni a `POMMaster`",
    'Ancoratge': "Cota · Caiguda · Component · Tirada — cap camp",
    'Capa': "exterior · fornitura · folre — la capa és de la PERTINENÇA "
            "(`GarmentPOMMap.capa`, slug de `MeasurementLayer`), no del catàleg",
    'FONT DEF.': "provenença de la definició (Master v2 · redactat · evident) — `iso_ref` és "
                 "per a la ISO 8559-1 i `notes` és del patronista: no s'hi aboca",
    'Origen': "Brownie v4 · complement PROD · proposta nova — documentació del full",
}

#: Capçaleres del full → clau interna. Les cel·les es llegeixen pel NOM de la columna i mai
#: per índex: reordenar dues columnes a l'Excel no ha de sembrar el nom on va la referència.
_COLS_CATALEG = {
    'Codi': 'codi', 'Nom EN (canònic)': 'nom_en', 'Nom CA': 'nom_ca', 'Nom ES': 'nom_es',
    'Fam.': 'familia', 'Pos.': 'posicio', "DES D'ON (punt A)": 'start_point',
    'FINS ON (punt B)': 'end_point', 'REFERÈNCIA': 'reference_point', 'SCOPE': 'scope',
    'ZONA': 'body_section', 'UNITAT': 'unitat', 'TOL. PROD (cm)': 'tol_prod_cm',
    'TOL. MOSTRA (cm)': 'tol_samp_cm', 'FONT DEF.': 'font_def', 'Origen': 'origen',
    'Règim': 'regim', 'Ancoratge': 'ancoratge', 'Capa': 'capa', 'Codi Brownie': 'codi_brownie',
    'Ús: models': 'us_models', 'pk PROD': 'pk_prod', 'Nota': 'nota',
    'ESTAT SEMBRA': 'estat',
}
_COLS_FAMILIES = {
    'Ordre': 'ordre', 'Lletra': 'codi', 'Família (CA)': 'nom_ca', 'Family (EN)': 'nom_en',
    'POMs': 'n_poms', 'Prefixos de codi que hi viuen': 'prefixos',
}
_COLS_ALIES = {
    'Codi Brownie': 'codi_brownie', '→ Codi sistema': 'codi_sistema',
    'Nom EN del sistema': 'nom_en', 'Fam.': 'familia', 'Ús: models': 'us_models',
    'pk PROD': 'pk_prod',
}


def cami_del_corpus(explicit=None):
    """El camí de l'arxiu: l'explícit, o el primer dels dos del brief que existeixi."""
    if explicit:
        p = Path(explicit)
        if not p.is_file():
            raise CommandError(f'--xlsx {p}: no existeix.')
        return p
    for p in CAMINS:
        if p.is_file():
            return p
    raise CommandError(
        f'{NOM_XLSX} no és a cap dels camins coneguts: ' + ' · '.join(str(p) for p in CAMINS))


def verifica(cami):
    """El hash de l'arxiu, o `CommandError`. Cap lectura passa per davant d'aquesta funció."""
    h = hashlib.sha256(Path(cami).read_bytes()).hexdigest()
    if h != SHA256_R2:
        raise CommandError(
            f'HASH NO COINCIDENT a {cami}\n   esperat: {SHA256_R2}\n   real:    {h}\n'
            '   Els dos entorns han de llegir els MATEIXOS bytes: la sembra no continua.')
    return h


def _files(ws, cols, clau):
    """Files d'un full com a dicts. Fila 1 = títol, fila 2 = capçalera, la resta = dades.

    Una capçalera que el full no porti ATURA: llegir per nom i tolerar-ne l'absència tornaria
    a ser llegir per índex, amb una passa més de silenci.
    """
    it = ws.iter_rows(values_only=True)
    next(it)                                    # el títol del full
    capcalera = [(c or '').strip() if isinstance(c, str) else c for c in next(it)]
    falten = [c for c in cols if c not in capcalera]
    if falten:
        raise CommandError(f'{ws.title}: hi falten columnes {falten}')
    idx = {cols[c]: i for i, c in enumerate(capcalera) if c in cols}
    out = []
    for fila in it:
        r = {k: fila[i] for k, i in idx.items()}
        if r.get(clau) in (None, ''):
            continue                            # cua de files buides del full
        out.append({k: (v.strip() if isinstance(v, str) else v) for k, v in r.items()})
    return out


def _decimal(v):
    return None if v in (None, '') else Decimal(str(v))


def carrega(explicit=None):
    """El corpus sencer, verificat i comptat. Retorna `(sha, poms, families, alies)`."""
    import openpyxl                             # dependència de la sembra, no del servei

    cami = cami_del_corpus(explicit)
    sha = verifica(cami)
    wb = openpyxl.load_workbook(cami, read_only=True, data_only=True)

    poms = _files(wb['CATALEG'], _COLS_CATALEG, 'codi')
    families = _files(wb['FAMILIES'], _COLS_FAMILIES, 'codi')
    alies = _files(wb['ALIES_BROWNIE'], _COLS_ALIES, 'codi_brownie')

    for p in poms:
        p['tol_prod_cm'] = _decimal(p['tol_prod_cm'])
        p['tol_samp_cm'] = _decimal(p['tol_samp_cm'])
        p['actiu'] = (p['estat'] == 'ACTIU')

    # ── Les guardes del corpus. Cap d'aquestes xifres és decorativa ────────────────────────
    _guarda('POMs al full CATALEG', len(poms), N_POMS)
    _guarda('famílies al full FAMILIES', len(families), N_FAMILIES)
    _guarda('àlies al full ALIES_BROWNIE', len(alies), N_ALIES)
    _guarda('POMs ACTIU', sum(1 for p in poms if p['actiu']), N_POMS_ACTIUS)
    _guarda('POMs INACTIU', sum(1 for p in poms if not p['actiu']), N_POMS_INACTIUS)

    codis = [p['codi'] for p in poms]
    if len(set(codis)) != len(codis):
        rep = sorted({c for c in codis if codis.count(c) > 1})
        raise CommandError(f'CATALEG: codis repetits {rep} — la identitat és el CODI.')
    fam_codis = {f['codi'] for f in families}
    orfes = sorted({p['familia'] for p in poms} - fam_codis)
    if orfes:
        raise CommandError(f'CATALEG: famílies {orfes} que el full FAMILIES no declara.')
    fora = sorted({a['codi_sistema'] for a in alies} - set(codis))
    if fora:
        raise CommandError(f'ALIES_BROWNIE: destins {fora} que no són cap POM del CATALEG.')
    brw = [a['codi_brownie'] for a in alies]
    if len(set(brw)) != len(brw):
        rep = sorted({c for c in brw if brw.count(c) > 1})
        raise CommandError(f'ALIES_BROWNIE: codi Brownie repetit {rep}.')

    return sha, poms, families, alies


def _guarda(que, real, esperat):
    if real != esperat:
        raise CommandError(f'CORPUS · {que}: esperats {esperat}, llegits {real}.')


def mapa_brownie(alies):
    """`{codi Brownie → codi de sistema}` — el mapa que fa servir S3 i S4."""
    return {a['codi_brownie']: a['codi_sistema'] for a in alies}
