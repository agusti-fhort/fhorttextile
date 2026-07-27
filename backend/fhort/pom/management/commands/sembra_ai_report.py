"""INFORME de sembra `.ai` → POMPlacement (PATRÓ B-modificat) — FASE 1, NOMÉS LECTURA.

Sobre els `.ai` del lot LOSAN (SKETCH AI), aquest command produeix un informe determinista
SENSE tocar cap BD i SENSE modificar cap `.ai`. Reprodueix la lògica de la PoC B-modificat
(`FTT_POC_B_MODIFICAT_LOSAN.md`) + la dissecció del lot (`FTT_DISSECCIO_LOT_AI_LOSAN.md`):

  1. EXTRACCIÓ  · `pdftotext -bbox` → mots + coordenades (1 artboard = 1 pàgina).
  2. RED-GATE   · `pdftocairo -png` → màscara vermella; un mot és ETIQUETA si el seu bbox
                  cau sobre vermell (estil A: text vermell · estil B: text blanc sobre
                  pastilla vermella → el bbox és vermell igual). Descarta prosa i notes.
  3. RESOLUCIÓ  · cada etiqueta es resol pel MATEIX camí que F1 (CustomerPOMAlias →
                  POMMaster, prioritat àlies; `client_code`/`codi_client` `__iexact`) contra
                  el catàleg VIU (per defecte schema `fhort`, on viu Customer LOS: el schema
                  `los` és buit). Gradació:
                    · VERD  = match EXACTE (mateixa puntuació) al catàleg viu.
                    · GROC  = match només després de NORMALITZAR (A.1→A1, treure punts/espais,
                              casefold) o via variant secundària.
                    · ÒRFE  = etiqueta vermella amb forma de codi que el catàleg NO coneix.
  4. COL·LISIONS· codi_client DUPLICAT al catàleg (p.ex. `BJ`) i col·lisió de normalització
                  (dotted↔undotted coexistents: `A.1` vs `A1`) → la mida real del deute de
                  nomenclatura per a la neteja de la Montse.
  5. GEOMETRIA  · cota = path vermell (stroke) de la SVG (`pdftocairo -svg`) ≥12 pt, en espai
                  de pàgina (el marc SVG i el de `pdftotext` coincideixen sense offset).
                  Aparellament GOLÓS 1:1 etiqueta→cota per distància punt→segment; lligam
                  ESTRICTE ≤14 pt / AMPLI ≤34 pt / null. Extrems = els dos punts més allunyats
                  del path assignat. bbox de vista per PÍXELS del render (respecta clips — el
                  bbox vectorial menteix ~15%). n_vistes per clustering de tinta no-vermella.
  6. GTI_HINT   · referència de model al text negre (`L\\d{2}[A-Z]{2,3}\\d{3,4}`), si n'hi ha.

FORA D'ABAST (Fase 2, no aquí): cap escriptura a POMPlacement · pantalla de revisió · IA ·
resolució automàtica del GTI (va a cua) · fotografies (marcar, no sembrar).

    python manage.py sembra_ai_report                       # tot el lot → informe
    python manage.py sembra_ai_report --files "PANT PELAYO,PANT TORMENTA,CAMI FAST"
    python manage.py sembra_ai_report --schema fhort --out /root/sembra_ai/INFORME.md
"""
import glob
import math
import os
import re
import subprocess
import tempfile
from collections import Counter, defaultdict
from datetime import date

import numpy as np
from lxml import etree
from PIL import Image
from xml.etree import ElementTree as ETxml

from django.core.management.base import BaseCommand
from django_tenants.utils import schema_context

SVG_NS = '{http://www.w3.org/2000/svg}'
XH_WORD = '{http://www.w3.org/1999/xhtml}word'

# ── Paràmetres calibrats contra la PoC (PELAYO 14/19 · TORMENTA 12/24 · CAMI 12/18) ──
DPI = 150
STRICT_PT = 14.0        # lligam segur
WIDE_PT = 34.0          # lligam ampli (franja de revisió)
MIN_COTA_LEN_PT = 12.0  # un path vermell ≥12 pt és una cota (arrows curtes queden fora)
RED_FRAC = 0.06         # fracció mínima de píxels vermells al bbox per considerar-lo etiqueta
MAX_SVG_MB = 25         # per damunt (ràster incrustat) s'omet el motor vectorial de lligam

# forma laxa de codi — NOMÉS per reconèixer ÒRFES (prosa exclosa); la resolució és per catàleg
CODE_SHAPE = re.compile(r'^[A-Za-z]{1,3}[.\-/]?\d{0,3}([.\-/]?\d{1,3})?[A-Za-z]?$')
PURE_NUM = re.compile(r'^\d+$')
UNIT_WORDS = {'CM', 'MM', 'CMS', 'PC', 'PCS'}
MODEL_REF = re.compile(r'L\d{2}[A-Z]{2,3}\d{3,4}', re.I)
_NORM = re.compile(r'[^A-Za-z0-9]')


def norm(s):
    return _NORM.sub('', s or '').upper()


def looks_like_code(tok):
    t = (tok or '').strip()
    if not t or PURE_NUM.match(t) or t.upper() in UNIT_WORDS:
        return False
    return bool(CODE_SHAPE.match(t))


# ─────────────────────────── catàleg viu (resolució F1) ───────────────────────────
class Catalog:
    """Índexs de resolució idèntics a F1: prioritat àlies (client_code) → codi directe
    (codi_client), tots dos `__iexact`. `dup_master` = codi_client duplicat (família BJ)."""

    def __init__(self, schema):
        with schema_context(schema):
            from fhort.tasks.models import Customer
            from fhort.pom.models import POMMaster, CustomerPOMAlias
            los = Customer.objects.filter(codi='LOS').first()
            self.los_pk = los and los.pk
            self.exact_alias = defaultdict(list)
            self.norm_alias = defaultdict(list)
            if los:
                for a in CustomerPOMAlias.objects.filter(customer=los).select_related('pom'):
                    self.exact_alias[a.client_code.casefold()].append(a)
                    self.norm_alias[norm(a.client_code)].append(a)
            self.exact_master = defaultdict(list)
            self.norm_master = defaultdict(list)
            for m in POMMaster.objects.all():
                self.exact_master[m.codi_client.casefold()].append(m)
                self.norm_master[norm(m.codi_client)].append(m)
        self.dup_master = {k: [m.codi_client for m in v]
                           for k, v in self.exact_master.items() if len(v) > 1}
        # famílies de col·lisió de normalització: >1 variant textual distinta pel mateix norm
        self.norm_collision = {}
        for idx in (self.norm_alias, self.norm_master):
            for n, rows in idx.items():
                variants = sorted({getattr(r, 'client_code', None) or getattr(r, 'codi_client', '')
                                   for r in rows})
                if len(variants) > 1:
                    self.norm_collision.setdefault(n, set()).update(variants)

    def resolve(self, tok):
        """→ (grade, detail). grade ∈ VERD/GROC/ORFE."""
        cf = tok.casefold()
        n = norm(tok)
        if cf in self.exact_alias:
            rows = self.exact_alias[cf]
            poms = sorted({a.pom_id for a in rows if a.pom_id})
            return 'VERD', dict(via='alias-exact', pom_ids=poms, pom_null=not poms,
                                ambiguous=len(poms) > 1)
        if cf in self.exact_master:
            rows = self.exact_master[cf]
            return 'VERD', dict(via='master-exact', pom_ids=[m.pk for m in rows],
                                ambiguous=len(rows) > 1, dup=cf in self.dup_master)
        if n in self.norm_alias:
            rows = self.norm_alias[n]
            variants = sorted({a.client_code for a in rows})
            poms = sorted({a.pom_id for a in rows if a.pom_id})
            return 'GROC', dict(via='alias-norm', variants=variants, pom_ids=poms,
                                collision=n in self.norm_collision)
        if n in self.norm_master:
            rows = self.norm_master[n]
            variants = sorted({m.codi_client for m in rows})
            return 'GROC', dict(via='master-norm', variants=variants,
                                pom_ids=[m.pk for m in rows], collision=n in self.norm_collision)
        return 'ORFE', dict(via=None)

    def dup_hit(self, tok):
        """Si la forma EXACTA del codi és un codi_client DUPLICAT al catàleg (família BJ),
        retorna les variants — s'ha de marcar sigui quin sigui el camí de resolució."""
        return self.dup_master.get(tok.casefold())


# ─────────────────────────────── extracció + render ───────────────────────────────
def run(cmd):
    subprocess.run(cmd, check=True, capture_output=True)


def page_count(path):
    out = subprocess.run(['pdfinfo', path], capture_output=True, text=True)
    for line in out.stdout.splitlines():
        if line.startswith('Pages:'):
            return int(line.split()[1])
    return 0


def parse_words(path, page):
    with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as tf:
        out = tf.name
    try:
        run(['pdftotext', '-bbox', '-f', str(page), '-l', str(page), path, out])
        tree = ETxml.parse(out)
    finally:
        os.path.exists(out) and os.unlink(out)
    words = []
    for w in tree.iter(XH_WORD):
        words.append(dict(text=w.text or '', xMin=float(w.get('xMin')), yMin=float(w.get('yMin')),
                          xMax=float(w.get('xMax')), yMax=float(w.get('yMax'))))
    return words


def merge_fragments(words):
    """Cus un fragment que comença amb puntuació (p.ex. `.22`) al mot de l'esquerra a la
    mateixa línia base (`D` + `.22` → `D.22`) — el `pdftotext` parteix alguns codis."""
    words = sorted(words, key=lambda w: (round(w['yMin'] / 4), w['xMin']))
    out = []
    for w in words:
        if (out and w['text'][:1] in '.-/' and abs(w['yMin'] - out[-1]['yMin']) < 4
                and 0 <= w['xMin'] - out[-1]['xMax'] < 8):
            out[-1]['text'] += w['text']
            out[-1]['xMax'] = w['xMax']
        else:
            out.append(dict(w))
    return out


def render_rgb(path, page, dpi=DPI):
    d = tempfile.mkdtemp()
    root = os.path.join(d, 'pg')
    try:
        run(['pdftocairo', '-png', '-f', str(page), '-l', str(page), '-r', str(dpi), path, root])
        files = sorted(glob.glob(root + '*.png'))
        arr = np.asarray(Image.open(files[0]).convert('RGB'))
    finally:
        for f in glob.glob(root + '*.png'):
            os.unlink(f)
        os.path.isdir(d) and os.rmdir(d)
    return arr


def red_mask(arr):
    r, g, b = arr[..., 0].astype(int), arr[..., 1].astype(int), arr[..., 2].astype(int)
    return (r > 150) & (g < 110) & (b < 110) & (r - g > 60) & (r - b > 60)


def ink_mask(arr):
    """Tinta no-blanca (per a vistes i bbox de píxels que respecta clips)."""
    r, g, b = arr[..., 0].astype(int), arr[..., 1].astype(int), arr[..., 2].astype(int)
    return (r < 235) | (g < 235) | (b < 235)


def bbox_red_fraction(mask, w, scale, pad=2):
    H, W = mask.shape
    x0 = max(0, int(w['xMin'] * scale) - pad); x1 = min(W, int(w['xMax'] * scale) + pad)
    y0 = max(0, int(w['yMin'] * scale) - pad); y1 = min(H, int(w['yMax'] * scale) + pad)
    if x1 <= x0 or y1 <= y0:
        return 0.0
    return float(mask[y0:y1, x0:x1].mean())


# ───────────────────────────── motor vectorial de cotes ─────────────────────────────
IDENT = (1, 0, 0, 1, 0, 0)


def mat_mul(A, B):
    a, b, c, d, e, f = A
    a2, b2, c2, d2, e2, f2 = B
    return (a * a2 + c * b2, b * a2 + d * b2, a * c2 + c * d2, b * c2 + d * d2,
            a * e2 + c * f2 + e, b * e2 + d * f2 + f)


def mat_apply(M, x, y):
    a, b, c, d, e, f = M
    return (a * x + c * y + e, b * x + d * y + f)


def parse_transform(s):
    M = IDENT
    for name, args in re.findall(r'(matrix|translate|scale)\(([^)]*)\)', s or ''):
        v = [float(x) for x in re.split(r'[,\s]+', args.strip()) if x]
        if name == 'matrix' and len(v) == 6:
            T = tuple(v)
        elif name == 'translate':
            T = (1, 0, 0, 1, v[0], v[1] if len(v) > 1 else 0)
        elif name == 'scale':
            T = (v[0], 0, 0, v[1] if len(v) > 1 else v[0], 0, 0)
        else:
            continue
        M = mat_mul(M, T)
    return M


def is_red_color(s):
    m = re.search(r'rgb\(([\d.]+)%,\s*([\d.]+)%,\s*([\d.]+)%\)', s or '')
    if not m:
        return False
    r, g, b = map(float, m.groups())
    return r > 80 and g < 30 and b < 30


def flatten_d(d):
    """Punts (x,y) en espai local: M/L absoluts; C mostrejat (t=0.5,1.0)."""
    stream = re.findall(r'([MLCZ])|(-?\d*\.?\d+(?:e-?\d+)?)', d)
    pts = []
    cur = None
    idx = 0

    def readn(k):
        nonlocal idx
        vals = []
        while len(vals) < k and idx < len(stream):
            c, n = stream[idx]
            if n:
                vals.append(float(n)); idx += 1
            else:
                break
        return vals

    while idx < len(stream):
        c, _ = stream[idx]
        if c in ('M', 'L'):
            idx += 1
            xy = readn(2)
            if len(xy) == 2:
                cur = (xy[0], xy[1]); pts.append(cur)
        elif c == 'C':
            idx += 1
            v = readn(6)
            if len(v) == 6 and cur:
                for t in (0.5, 1.0):
                    mt = 1 - t
                    x = mt**3 * cur[0] + 3 * mt * mt * t * v[0] + 3 * mt * t * t * v[2] + t**3 * v[4]
                    y = mt**3 * cur[1] + 3 * mt * mt * t * v[1] + 3 * mt * t * t * v[3] + t**3 * v[5]
                    pts.append((x, y))
                cur = (v[4], v[5])
        else:
            idx += 1
    return pts


def red_cotas(svg_path):
    """Polilínies de cota (path vermell, fill=none, ≥12 pt) en espai de pàgina."""
    root = etree.parse(svg_path).getroot()
    cotas = []

    def walk(el, M):
        M2 = mat_mul(M, parse_transform(el.get('transform')))
        if el.tag == SVG_NS + 'path':
            stroke = el.get('stroke', '') or el.get('style', '')
            if el.get('fill', '') == 'none' and is_red_color(stroke):
                pts = [mat_apply(M2, x, y) for x, y in flatten_d(el.get('d', ''))]
                if len(pts) >= 2:
                    length = sum(math.dist(pts[k], pts[k + 1]) for k in range(len(pts) - 1))
                    if length >= MIN_COTA_LEN_PT:
                        cotas.append(pts)
        for ch in el:
            walk(ch, M2)

    walk(root, IDENT)
    return cotas


def _pt_seg(p, a, b):
    px, py = p; ax, ay = a; bx, by = b
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    if L2 == 0:
        return math.dist(p, a)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def label_cota_dist(bb, path):
    """Distància del CENTRE de l'etiqueta al segment més proper del path (calibrat contra la
    PoC: el centre reprodueix el llindar de 14 pt; el bbox-min l'infla)."""
    x0, y0, x1, y1 = bb
    p = ((x0 + x1) / 2, (y0 + y1) / 2)
    best = float('inf')
    for k in range(len(path) - 1):
        best = min(best, _pt_seg(p, path[k], path[k + 1]))
    return best


def extrems(path):
    """Els dos punts més allunyats del path (extrems de la cota)."""
    best = (0.0, path[0], path[-1])
    for i in range(len(path)):
        for j in range(i + 1, len(path)):
            dd = math.dist(path[i], path[j])
            if dd > best[0]:
                best = (dd, path[i], path[j])
    return best[1], best[2]


def associate(labels, cotas):
    """Aparellament golós 1:1 etiqueta→cota per distància creixent."""
    pairs = []
    for li, lab in enumerate(labels):
        for ci, cota in enumerate(cotas):
            pairs.append((label_cota_dist(lab['bb'], cota), li, ci))
    pairs.sort(key=lambda p: p[0])
    used_l, used_c, out = set(), set(), {}
    for dist, li, ci in pairs:
        if li in used_l or ci in used_c:
            continue
        used_l.add(li); used_c.add(ci)
        out[li] = (dist, ci)
    return out


# ───────────────────────────────── vistes (view_slot) ─────────────────────────────────
def connected_components(mask):
    """Etiquetatge de components connexos (4-veïns) en numpy pur, 2 passades + union-find.
    Opera sobre una màscara ja reduïda (barata). Retorna (labels, n)."""
    H, W = mask.shape
    labels = np.zeros((H, W), dtype=np.int32)
    parent = [0]

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    nxt = 1
    for y in range(H):
        row = mask[y]
        for x in range(W):
            if not row[x]:
                continue
            up = labels[y - 1, x] if y > 0 else 0
            left = labels[y, x - 1] if x > 0 else 0
            if up and left:
                labels[y, x] = min(up, left); union(up, left)
            elif up:
                labels[y, x] = up
            elif left:
                labels[y, x] = left
            else:
                labels[y, x] = nxt; parent.append(nxt); nxt += 1
    # segona passada: canonicalitza
    remap = {}
    n = 0
    for y in range(H):
        for x in range(W):
            if labels[y, x]:
                r = find(labels[y, x])
                if r not in remap:
                    n += 1; remap[r] = n
                labels[y, x] = remap[r]
    return labels, n


def view_analysis(arr, labels_px, scale):
    """n_vistes: components de tinta no-vermella prou grans que contenen ≥1 etiqueta.
    Retorna (n_vistes, n_sense_cotes, view_bbox_max_mm)."""
    ink = ink_mask(arr) & ~red_mask(arr)
    H, W = ink.shape
    ds = 8
    small = ink[::ds, ::ds]
    # dilatació box (3x3, 2 iteracions) via màxim desplaçat
    for _ in range(2):
        d = small.copy()
        d[1:, :] |= small[:-1, :]; d[:-1, :] |= small[1:, :]
        d[:, 1:] |= small[:, :-1]; d[:, :-1] |= small[:, 1:]
        small = d
    comp, n = connected_components(small)
    if n == 0:
        return 0, 0, 0.0
    areas = np.bincount(comp.ravel())
    min_area = max(20, int(0.002 * small.size))
    # centres d'etiqueta en coords del mapa reduït
    lab_cells = [(int(l['bb'][1] * scale / ds), int(l['bb'][0] * scale / ds)) for l in labels_px]
    n_vistes = n_sense = 0
    max_h_mm = 0.0
    for cid in range(1, n + 1):
        if areas[cid] < min_area:
            continue
        ys, xs = np.nonzero(comp == cid)
        has_label = any(comp[min(cy, comp.shape[0] - 1), min(cx, comp.shape[1] - 1)] == cid
                        for cy, cx in lab_cells)
        h_px = (ys.max() - ys.min() + 1) * ds
        h_mm = h_px / scale * 25.4 / 72.0
        if has_label:
            n_vistes += 1
            max_h_mm = max(max_h_mm, h_mm)
        else:
            n_sense += 1
    return n_vistes, n_sense, max_h_mm


# ─────────────────────────────────────── informe ───────────────────────────────────────
class Command(BaseCommand):
    help = 'INFORME determinista de sembra .ai → POMPlacement (FASE 1, NOMÉS LECTURA, cap BD).'

    def add_arguments(self, parser):
        parser.add_argument('--dir', default='/root/sembra_ai')
        parser.add_argument('--schema', default='fhort')
        parser.add_argument('--out', default=None,
                            help='fitxer de sortida (per defecte <dir>/INFORME_SEMBRA_AI.md)')
        parser.add_argument('--files', default=None,
                            help='subconjunt per nom (sense .ai), separats per coma')
        parser.add_argument('--dpi', type=int, default=DPI)
        parser.add_argument('--max-pages', type=int, default=0,
                            help='límit de pàgines per fitxer (0 = totes)')

    def handle(self, *args, **opts):
        w = self.stdout.write
        style = self.style
        ai_dir = opts['dir']
        scale = opts['dpi'] / 72.0
        out_path = opts['out'] or os.path.join(ai_dir, 'INFORME_SEMBRA_AI.md')

        w(style.WARNING(f'=== sembra_ai_report · FASE 1 (NOMÉS LECTURA) · schema={opts["schema"]} ==='))
        cat = Catalog(opts['schema'])
        if not cat.los_pk:
            w(style.ERROR(f'Customer LOS no existeix al schema {opts["schema"]} — avortat.'))
            return
        w(f'Catàleg viu: LOS pk={cat.los_pk} · àlies={sum(len(v) for v in cat.exact_alias.values())} '
          f'· masters={sum(len(v) for v in cat.exact_master.values())} '
          f'· codi_client duplicats={len(cat.dup_master)} · col·lisions-norm={len(cat.norm_collision)}')

        files = sorted(glob.glob(os.path.join(ai_dir, '*.ai')))
        if opts['files']:
            wanted = {f.strip() for f in opts['files'].split(',')}
            files = [f for f in files if os.path.splitext(os.path.basename(f))[0] in wanted]
        if not files:
            w(style.ERROR('Cap .ai trobat.'))
            return

        lines = [f'# INFORME SEMBRA `.ai` → POMPlacement — FASE 1 (NOMÉS LECTURA)',
                 f'',
                 f'**Data:** {date.today()} · **Schema catàleg:** `{opts["schema"]}` '
                 f'(Customer LOS pk={cat.los_pk}) · **DPI render:** {opts["dpi"]}',
                 f'**Font:** `{ai_dir}` · {len(files)} fitxers · **Cap escriptura a BD, cap `.ai` modificat.**',
                 f'']
        # acumuladors globals
        g = Counter()
        orphans = []      # (codi, fitxer, artboard)
        collisions = []   # (codi, detall, fitxer, artboard)
        per_file_rows = []

        for path in files:
            name = os.path.splitext(os.path.basename(path))[0]
            try:
                npages = page_count(path)
            except Exception as e:
                w(style.ERROR(f'{name}: pdfinfo ha fallat ({e}) — SALTAT'))
                lines.append(f'\n## {name}\n- ⚠️ pdfinfo ha fallat: `{e}` — fitxer saltat.')
                continue
            if opts['max_pages']:
                npages = min(npages, opts['max_pages'])
            lines.append(f'\n## {name} — {npages} artboard(s)')
            w(style.MIGRATE_HEADING(f'\n▸ {name} ({npages} artboards)'))

            for pg in range(1, npages + 1):
                rec = self._analyze_page(path, pg, cat, scale, opts['dpi'])
                if rec.get('error'):
                    lines.append(f'- ab{pg}: ⚠️ error `{rec["error"]}`')
                    w(style.ERROR(f'  ab{pg}: error {rec["error"]}'))
                    continue
                g['codis'] += rec['n_codis']
                g['verd'] += rec['verd']; g['groc'] += rec['groc']; g['orfe'] += rec['orfe']
                g['segur'] += rec['segur']; g['ampli'] += rec['ampli']
                g['vistes'] += rec['n_vistes']
                for c in rec['orphan_codes']:
                    orphans.append((c, name, pg))
                for c, det in rec['collision_codes']:
                    collisions.append((c, det, name, pg))
                per_file_rows.append((name, pg, rec))
                lines.append(
                    f'- **ab{pg}** · codis={rec["n_codis"]} '
                    f'(🟩{rec["verd"]} 🟨{rec["groc"]} 🟥{rec["orfe"]}) · '
                    f'lligam segur={rec["segur"]} ampli={rec["ampli"]} · '
                    f'vistes={rec["n_vistes"]} (sense_cotes={rec["n_sense"]}) · '
                    f'bbox_vista_max={rec["view_h_mm"]:.1f}mm · '
                    f'gti_hint={rec["gti"] or "—"}'
                    + (f' · lligam OMÈS (SVG {rec["svg_mb"]:.0f}MB, ràster)' if rec.get('lligam_skipped') else '')
                    + (' · ⚠️ FOTOGRAFIA (marcar, no sembrar)' if rec['is_photo'] else ''))
                if rec['orphan_codes']:
                    lines.append(f'    · ÒRFES: {", ".join(rec["orphan_codes"])}')
                w(f'  ab{pg}: codis={rec["n_codis"]} (V{rec["verd"]}/G{rec["groc"]}/O{rec["orfe"]}) '
                  f'segur={rec["segur"]} ampli={rec["ampli"]} vistes={rec["n_vistes"]} '
                  f'gti={rec["gti"] or "—"}')

        # ── secció global ──
        net = g['verd'] + g['groc']
        lines += [
            f'\n---\n\n# GLOBAL — la mida real del problema',
            f'',
            f'- **Codis extrets (etiquetes vermelles):** {g["codis"]}',
            f'- **Resolen net (VERD+GROC):** {net} '
            f'({100 * net / g["codis"]:.1f}%)' if g['codis'] else '- Resolen net: 0',
            f'  - 🟩 VERD (match exacte al catàleg viu): {g["verd"]}',
            f'  - 🟨 GROC (només normalitzant / variant secundària): {g["groc"]}',
            f'- **🟥 ÒRFES (el catàleg viu NO els coneix):** {g["orfe"]} → deute per a la Montse',
            f'- **Lligam de cota:** segur={g["segur"]} · ampli={g["ampli"]} '
            f'(de {g["codis"]} codis)',
            f'- **Vistes detectades:** {g["vistes"]}',
        ]

        # famílies de col·lisió del catàleg (globals, independents del lot)
        lines.append(f'\n## Col·lisions del catàleg viu (deute de nomenclatura)')
        lines.append(f'- **codi_client DUPLICAT** ({len(cat.dup_master)} famílies): '
                     + (', '.join(f'`{v[0]}`×{len(v)}' for v in cat.dup_master.values()) or '—'))
        lines.append(f'- **col·lisió de normalització** dotted↔undotted '
                     f'({len(cat.norm_collision)} famílies): '
                     + (', '.join('/'.join(sorted(vs)) for vs in list(cat.norm_collision.values())[:40])
                        or '—'))

        # còdis del lot que xoquen (grocs amb collision + orfes)
        lines.append(f'\n## Codis del lot que XOQUEN (per artboard) — or per a la Montse')
        if collisions:
            seen = defaultdict(list)
            for c, det, fn, pg in collisions:
                seen[c].append(f'{fn}·ab{pg}')
            for c in sorted(seen):
                lines.append(f'- `{c}` ({det_for(collisions, c)}) → {", ".join(seen[c][:12])}')
        else:
            lines.append('- cap col·lisió activa al lot.')

        lines.append(f'\n## Codis ÒRFES del lot (cap match al catàleg viu)')
        if orphans:
            seen = defaultdict(list)
            for c, fn, pg in orphans:
                seen[c].append(f'{fn}·ab{pg}')
            for c in sorted(seen):
                lines.append(f'- `{c}` → {", ".join(seen[c][:12])}')
        else:
            lines.append('- cap òrfena: tots els codis vermells del lot resolen al catàleg viu.')

        lines.append(f'\n---\n*FASE 1 · cap escriptura a cap BD · cap `.ai` modificat. '
                     f'Fase 2 (escriptura a POMPlacement) es briefa DESPRÉS de llegir aquest informe.*')

        report = '\n'.join(lines)
        with open(out_path, 'w') as fh:
            fh.write(report + '\n')
        w(style.SUCCESS(f'\n=== GLOBAL: codis={g["codis"]} · net={net} · òrfes={g["orfe"]} '
                        f'· col·lisions-lot={len(set(c for c,_,_,_ in collisions))} ==='))
        w(style.SUCCESS(f'Informe escrit a: {out_path}'))

    # ── anàlisi d'un artboard ──
    def _analyze_page(self, path, page, cat, scale, dpi):
        rec = dict(n_codis=0, verd=0, groc=0, orfe=0, segur=0, ampli=0, n_vistes=0, n_sense=0,
                   view_h_mm=0.0, gti=None, is_photo=False, orphan_codes=[], collision_codes=[])
        try:
            words = merge_fragments(parse_words(path, page))
            arr = render_rgb(path, page, dpi)
        except Exception as e:
            rec['error'] = f'{type(e).__name__}: {e}'
            return rec
        rmask = red_mask(arr)

        # etiquetes = mots red-gated amb forma de codi o que resolen
        labels = []
        for word in words:
            if bbox_red_fraction(rmask, word, scale) <= RED_FRAC:
                continue
            grade, det = cat.resolve(word['text'])
            if grade == 'ORFE':
                t = word['text'].strip()
                # prosa vermella: descarta si no té forma de codi (p.ex. "REVERSIBLE") o si és
                # una paraula pura-alfabètica ≥3 lletres sense dígit ni puntuació (BACK, ONLY,
                # TAPE, TCX). Els codis reals porten dígit/puntuació o són molt curts (BJ, C, U).
                if not looks_like_code(t):
                    continue
                if (not any(c.isdigit() for c in t) and not any(c in '.-/' for c in t)
                        and len(norm(t)) >= 3):
                    continue
            labels.append(dict(text=word['text'], grade=grade, det=det,
                               bb=(word['xMin'], word['yMin'], word['xMax'], word['yMax'])))

        rec['n_codis'] = len(labels)
        for lab in labels:
            rec[{'VERD': 'verd', 'GROC': 'groc', 'ORFE': 'orfe'}[lab['grade']]] += 1
            if lab['grade'] == 'ORFE':
                rec['orphan_codes'].append(lab['text'])
            det = lab['det']
            dup = cat.dup_hit(lab['text'])
            if dup:
                rec['collision_codes'].append(
                    (lab['text'], f'codi_client DUPLICAT ×{len(dup)} (família BJ)'))
            elif lab['grade'] == 'GROC' and det.get('collision'):
                rec['collision_codes'].append((lab['text'], 'variants dotted↔undotted: '
                                               + '/'.join(det.get('variants', []))))

        # geometria (lligam) via motor vectorial — amb guarda per SVG ràster gegant
        d = tempfile.mkdtemp()
        svg = os.path.join(d, 'p.svg')
        try:
            run(['pdftocairo', '-svg', '-f', str(page), '-l', str(page), path, svg])
            svg_mb = os.path.getsize(svg) / 1e6
            rec['svg_mb'] = svg_mb
            if svg_mb <= MAX_SVG_MB:
                cotas = red_cotas(svg)
                assign = associate(labels, cotas)
                for li, (dist, _ci) in assign.items():
                    if dist <= STRICT_PT:
                        rec['segur'] += 1; rec['ampli'] += 1
                    elif dist <= WIDE_PT:
                        rec['ampli'] += 1
            else:
                rec['lligam_skipped'] = True
        except Exception as e:
            rec['lligam_skipped'] = True
            rec['svg_mb'] = rec.get('svg_mb', 0.0)
        finally:
            for f in glob.glob(os.path.join(d, '*')):
                os.unlink(f)
            os.path.isdir(d) and os.rmdir(d)

        # vistes + bbox de píxels
        try:
            n_v, n_s, h_mm = view_analysis(arr, labels, scale)
            rec['n_vistes'], rec['n_sense'], rec['view_h_mm'] = n_v, n_s, h_mm
        except Exception:
            pass

        # fotografia: molt ràster + molt pocs traços vectorials (TEJANO ZARA)
        ink = ink_mask(arr)
        raster_frac = float((ink & ~red_mask(arr)).mean())
        rec['is_photo'] = raster_frac > 0.20 and rec['n_codis'] > 0 and rec.get('svg_mb', 0) > 3

        # gti_hint
        try:
            txt = subprocess.run(['pdftotext', '-f', str(page), '-l', str(page), path, '-'],
                                 capture_output=True, text=True).stdout
            m = MODEL_REF.search(txt)
            rec['gti'] = m.group(0).upper() if m else None
        except Exception:
            pass
        return rec


def det_for(collisions, code):
    for c, det, _fn, _pg in collisions:
        if c == code:
            return det
    return ''
