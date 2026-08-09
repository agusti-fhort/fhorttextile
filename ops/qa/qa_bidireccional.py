"""BIDIRECCIONAL MESURADA · maqueta ↔ pantalla, element per element, amb valors COMPUTATS.

⚠️ **PER QUÈ EXISTEIX.** La bidireccional era un procediment de LECTURA: obrir la maqueta, obrir
el JSX, comparar. Així es va donar per bona una selecció `--sel`+daurada on la maqueta diu, amb
el comentari escrit al costat, `.tg.on{background:var(--ok-bg)…} /* esmena Agus: inclòs = verd */`.
Llegir dos fitxers i creure que diuen el mateix no és verificar-ho.

Aquest script fa la comparació **contra valors computats de les dues bandes**:

  · obre la MAQUETA (fitxer local, `file://`) i, per a cada selector d'interès, en llegeix
    `getComputedStyle` — el color, la mida, el pes, el radi que el navegador realment pinta;
  · obre la PANTALLA (bundle de `frontend/dist` + API viva) i llegeix el mateix de l'element
    equivalent;
  · imprimeix les dues columnes UNA AL COSTAT DE L'ALTRA i marca les que no casen.

Cap dels dos costats s'escriu a mà: si la maqueta canvia, la referència canvia sola.

    FTT_QA_TOKEN=... /tmp/qa-venv/bin/python ops/qa/qa_bidireccional.py
"""
import mimetypes
import os
import pathlib
import sys

import requests
from playwright.sync_api import sync_playwright

REPO = pathlib.Path(__file__).resolve().parents[2]
DIST = REPO / 'frontend' / 'dist'
MAQ = REPO / 'ops' / 'maquetes'
BASE = 'https://staging.fhorttextile.tech'
VIU = 'http://127.0.0.1:8001'
HOST_TENANT = os.environ.get('FTT_QA_HOST', 'fhorttextile.tech')
TOKEN = os.environ.get('FTT_QA_TOKEN', '')

#: Les propietats que decideixen si dos elements «són el mateix» a ull.
PROPS = ['backgroundColor', 'color', 'vora', 'fontSize', 'fontWeight',
         'fontStyle', 'borderTopLeftRadius', 'textTransform']

#: (tram, què és, fitxer de maqueta, selector a la maqueta, gestos a la MAQUETA,
#:  ruta, gestos a la PANTALLA, selector a la pantalla)
#: Els selectors de pantalla van per TEXT o per ARIA a posta: són el que un humà veu, no una
#: classe interna. Els gestos són el que cal fer, a CADA banda, per arribar a l'estat que es
#: compara — sense ells `.tg.on` no existeix ni a la maqueta (les pastilles les pinta el seu JS).
CASOS = [
    # ── A2 · Size Library ────────────────────────────────────────────────────────────────
    ('A2', 'capa de restricció TRIADA (inclusió)', 'maqueta_size_library_v3.html',
     '.tg.on', [('click', '.run >> nth=0')],
     '/size-library', [('click', 'button:has-text("Alpha EU — Women")'),
                       ('click', 'div:has(> span:text-is("Target")) button:has-text("Woman") >> nth=0')],
     'div:has(> span:text-is("Target")) button[aria-pressed="true"]'),
    ('A2', 'capa de restricció NO triada', 'maqueta_size_library_v3.html',
     '.tg:not(.on)', [('click', '.run >> nth=0')],
     '/size-library', [('click', 'button:has-text("Alpha EU — Women")')],
     'div:has(> span:text-is("Target")) button[aria-pressed="false"]'),
    ('A2', 'fila del run SELECCIONADA («on soc»)', 'maqueta_size_library_v3.html',
     '.run.on', [],
     '/size-library', [('click', 'button:has-text("Alpha EU — Women")')],
     'button[aria-current="true"]'),
    ('A2', 'capçalera de secció de la fitxa', 'maqueta_size_library_v3.html',
     '.sec .h', [],
     '/size-library', [('click', 'button:has-text("Alpha EU — Women")')],
     'div:has(> span:text-is("Restriccions"))'),
    ('A2', 'estat buit («no declarat»)', 'maqueta_size_library_v3.html',
     '.kv .v.buit', [],
     '/size-library', [('click', 'button:has-text("Alpha EU — Women")')],
     'text=/no vol dir/'),
    ('A2', 'rètol de camp de la fitxa', 'maqueta_size_library_v3.html',
     '.kv .k', [],
     '/size-library', [('click', 'button:has-text("Alpha EU — Women")')], 'text=Target'),
    # ── A3 · Grading Rules ───────────────────────────────────────────────────────────────
    ('A3', 'capa de relació TRIADA (inclusió)', 'maqueta_grading_rules_v4.html',
     '.tg.on', [('click', 'button:has-text("Editar") >> nth=0'), ('click', '.tab >> nth=1')],
     '/poms/grading', [('fill', 'input[placeholder*="cerca"]', 'ZZ'),
                       ('click', 'button:has-text("Editar")'),
                       ('click', 'button:has-text("Relacions")'),
                       ('click', 'div:has(> div > span:text-is("Target")) button:has-text("Woman") >> nth=0')],
     'div:has(> div > span:text-is("Target")) button[aria-pressed="true"]'),
    ('A3', 'capa de relació NO triada', 'maqueta_grading_rules_v4.html',
     '.tg:not(.on)', [('click', 'button:has-text("Editar") >> nth=0'), ('click', '.tab >> nth=1')],
     '/poms/grading', [('fill', 'input[placeholder*="cerca"]', 'ZZ'),
                       ('click', 'button:has-text("Editar")'),
                       ('click', 'button:has-text("Relacions")')],
     'div:has(> div > span:text-is("Target")) button[aria-pressed="false"]'),
    ('A3', 'capçalera de bloc de relació', 'maqueta_grading_rules_v4.html',
     '.rblk .h', [('click', 'button:has-text("Editar") >> nth=0'), ('click', '.tab >> nth=1')],
     '/poms/grading', [('fill', 'input[placeholder*="cerca"]', 'ZZ'),
                       ('click', 'button:has-text("Editar")'),
                       ('click', 'button:has-text("Relacions")')],
     'div:has(> span:text-is("Construcció"))'),
    ('A3', 'capçalera de columna de la taula', 'maqueta_grading_rules_v4.html',
     'th', [('click', 'button:has-text("Editar") >> nth=0')],
     '/poms/grading', [('fill', 'input[placeholder*="cerca"]', 'ZZ'),
                       ('click', 'button:has-text("Editar")')],
     'th:has-text("RÈGIM")'),
    ('A3', 'capçalera de llista', 'maqueta_grading_rules_v4.html',
     '.lhead span', [],
     '/poms/grading', [], 'text=JOC DE REGLES'),
    ('A3', 'tab germana ACTIVA', 'maqueta_grading_rules_v4.html',
     '.tab.on', [('click', 'button:has-text("Editar") >> nth=0')],
     '/poms/grading', [('fill', 'input[placeholder*="cerca"]', 'ZZ'),
                       ('click', 'button:has-text("Editar")')],
     'button[aria-current="true"]'),
    ('A3', 'nom del joc a la capçalera', 'maqueta_grading_rules_v4.html',
     '.shead .t', [('click', 'button:has-text("Editar") >> nth=0')],
     '/poms/grading', [('fill', 'input[placeholder*="cerca"]', 'ZZ'),
                       ('click', 'button:has-text("Editar")')],
     'span:text-is("ZZ-TEST · Chino BOTTOMS regular")'),
    # ── A1 · Catàleg de POMs ─────────────────────────────────────────────────────────────
    ('A1', 'fila SELECCIONADA («on soc»)', 'maqueta_cataleg_poms_v3.html',
     '.pom.on', [('click', '.pom >> nth=0')],
     '/poms', [], 'button[aria-current="true"]'),
    # ⚠️ EL SELECTOR S'HA HAGUT D'ACOTAR A `main`, i el motiu val la pena. Anava per
    # `div[style*="sticky"] >> nth=0`, o sigui «el primer element enganxós de la pàgina» — i
    # des del §8b-quater(2) el primer element enganxós del document és el BLOC DE CROM del
    # Shell, que és fora del `<main>`. El cas va passar de mesurar la capçalera de categoria a
    # mesurar la top bar, i va donar cinc desviacions que NO eren de la pantalla.
    # És el mateix mode de fallada que la coda del bloc B va patir amb el literal «Pendent»: un
    # selector que depèn d'una cosa que es pot moure deixa de mesurar el que deia, sense avisar.
    ('A1', 'capçalera de categoria', 'maqueta_cataleg_poms_v3.html',
     '.cat', [],
     '/poms', [], 'main div[style*="sticky"] >> nth=0'),
    # ── A5 · Models · LA LLISTA CANÒNICA (§8e) ───────────────────────────────────────────
    # La maqueta d'aquest tram és la NORMA de llista, no la d'una pantalla: el que es mesura
    # aquí val per a QUALSEVOL llista del producte, i per això s'hi mesura la graella sencera
    # (capçalera, capçalera ordenada, dada reina, refs, fila triada, comptador, cerca, caixa).
    ('A5', 'capçalera de columna', 'NORMA_LLISTA_canonica.html',
     'th', [],
     '/models', [], 'th:has-text("REF INTERNA")'),
    ('A5', 'capçalera de la columna ORDENADA', 'NORMA_LLISTA_canonica.html',
     'th.sorted', [],
     '/models', [], 'th:has-text("ENTRADA")'),
    ('A5', 'la DADA REINA (el nom porta el pes)', 'NORMA_LLISTA_canonica.html',
     'td.c-nom', [],
     '/models', [], 'td:has-text("Pantalo test")'),
    ('A5', 'columna de referència (secundària)', 'NORMA_LLISTA_canonica.html',
     'td.c-refi', [],
     '/models', [], 'td:has-text("FTT-SS26-0001")'),
    # ⚠️ LA FASE ES MOU. Aquest cas anava ancorat al literal «Pendent» i va deixar de mesurar-se
    # el dia que el model del banc va avançar de fase: un selector que depèn d'un ESTAT DE DOMINI
    # deixa de mesurar sense avisar, i el silenci s'assembla massa a un verd. S'ancora a
    # QUALSEVOL de les sis fases del vocabulari, que és el que la columna sempre pinta.
    ('A5', 'columna de FASE (text pla, sense badge)', 'NORMA_LLISTA_canonica.html',
     'td.c-fase', [],
     '/models', [],
     'td:text-matches("^(Pendent|Desenvolupament|Prototip|Joc de talles|Preproducció|Producció)$")'),
    ('A5', 'fila SELECCIONADA («on soc»)', 'NORMA_LLISTA_canonica.html',
     'tr.on td.c-nom', [],
     '/models', [('click', 'input[aria-label="FTT-SS26-0001"]')], 'td:has-text("Pantalo test")'),
    ('A5', 'caixa de la llista', 'NORMA_LLISTA_canonica.html',
     '.listbox', [],
     '/models', [], 'div:has(> table)'),
    ('A5', 'comptador (valors-manen)', 'NORMA_LLISTA_canonica.html',
     '.headrow .kpi', [],
     '/models', [], 'div:has(> span:text-is("models")) > span >> nth=0'),
    ('A5', 'rètol de l\'entitat', 'NORMA_LLISTA_canonica.html',
     '.headrow .lab', [],
     '/models', [], 'span:text-is("models")'),
    ('A5', 'cerca al costat del comptador', 'NORMA_LLISTA_canonica.html',
     '.headrow input', [],
     '/models', [], 'input[placeholder*="Cerca"]'),
    ('A5', 'píndola de vista ACTIVA', 'NORMA_LLISTA_canonica.html',
     '.mitem.on', [],
     '/models', [], 'button[aria-current="page"]'),
    ('A5', 'píndola de vista en repòs', 'NORMA_LLISTA_canonica.html',
     '.pmenu .mitem:not(.on)', [],
     '/models', [], 'button:text-is("Models acabats")'),
    ('A5', 'fletxa d\'enrere', 'NORMA_LLISTA_canonica.html',
     '.back', [],
     '/models', [], 'button[aria-label="Tornar al Dashboard"]'),
    ('A5', 'paperera de fila (repòs)', 'NORMA_LLISTA_canonica.html',
     '.del', [],
     '/models', [], 'button[aria-label="Esborrar"]'),
    # ── A6 · Dashboard del model · §8b «aquesta pantalla va a missa» ─────────────────────
    # Aquí la maqueta és l'EVIDÈNCIA de l'estructura de pàgina de tot el producte: top bar →
    # menú de pantalla → identitat SOBRE EL FONS → contingut. El tram és NOMÉS PELL, i per
    # això el que es mesura són els embolcalls (identitat, rètols, targetes, buits) i no cap
    # component del dashboard, que no s'ha tocat.
    ('A6', 'codi de la identitat (caption)', 'PROPOSTA_menu_pantalla_v3.html',
     '.ident .code', [],
     '/models/1319', [], 'text=FTT-SS26-0001'),
    ('A6', 'nom de la identitat (22/500)', 'PROPOSTA_menu_pantalla_v3.html',
     '.ident .name', [],
     '/models/1319', [], 'h1'),
    # Mateix motiu que a A5: el badge s'ancora pel seu `title` («Fase»), que no es mou amb la
    # dada. Pel camí, això també desfà l'ambigüitat amb el «Pendent» del bloc «On sóc».
    ('A6', 'badge de FASE (neutre, §8c)', 'PROPOSTA_menu_pantalla_v3.html',
     '.b.fase', [],
     '/models/1319', [], 'span[title="Fase"]'),
    ('A6', 'acció secundària («Accions ▾»)', 'PROPOSTA_menu_pantalla_v3.html',
     '.ident .right .btn', [],
     '/models/1319', [], 'button:has-text("Accions")'),
    ('A6', 'acció DESTRUCTIVA (vora, mai plena)', 'PROPOSTA_menu_pantalla_v3.html',
     '.btn.dang', [],
     '/models/1319', [], 'button:has-text("Eliminar")'),
    ('A6', 'rètol de bloc del dashboard', 'PROPOSTA_menu_pantalla_v3.html',
     '.lblc', [],
     '/models/1319', [], 'div:text-is("Pla de treball")'),
    # El rètol del bloc és l'àncora: «Pendent» hi és DUES vegades a la pantalla (el badge de
    # fase de la identitat i la fase del bloc «On sóc»), i un selector per text les confon.
    ('A6', 'targeta de contingut («On sóc»)', 'PROPOSTA_menu_pantalla_v3.html',
     '.card.onsoc', [],
     '/models/1319', [], 'div:text-is("On sóc") + div'),
    ('A6', 'estat BUIT (§8c: tènue i cursiva)', 'PROPOSTA_menu_pantalla_v3.html',
     '.emptybox', [],
     '/models/1319', [], 'text=Encara no hi ha fitxa'),
    ('A6', 'fila-porta d\'artefacte', 'PROPOSTA_menu_pantalla_v3.html',
     '.rowlink', [],
     '/models/1319', [], 'button:has-text("Mesures base")'),
    ('A6', 'píndola de secció ACTIVA', 'PROPOSTA_menu_pantalla_v3.html',
     '.pill.on', [],
     '/models/1319', [], 'button[aria-current="page"]'),
    ('A6', 'píndola de secció en repòs', 'PROPOSTA_menu_pantalla_v3.html',
     '.pmenu .pill:not(.on)', [],
     '/models/1319', [], 'button:text-is("Escalat")'),
    # ── A7 · Resum · EL WIZARD PARTIT (§8f) ──────────────────────────────────────────────
    # El tram gros del bloc, i l'únic que no és pell: aquí es mesura que els TRES ESTATS del
    # subespai (FET · ACTUAL · BLOQUEJAT) i el xip d'inclusió pinten el que la maqueta diu.
    ('A7', 'títol de contenidor', 'PROPOSTA_resum_wizard_partit.html',
     '.chead .t', [],
     '/models/1319?tab=Resum', [], 'span:text-is("Informació")'),
    ('A7', 'nota del contenidor (quin pas és)', 'PROPOSTA_resum_wizard_partit.html',
     '.chead .n', [],
     '/models/1319?tab=Resum', [], 'span:text-is("1 · Identificació")'),
    ('A7', 'rètol de camp', 'PROPOSTA_resum_wizard_partit.html',
     '.kv .k', [],
     '/models/1319?tab=Resum', [], 'span:text-is("Client")'),
    ('A7', 'valor BUIT (tènue i cursiva)', 'PROPOSTA_resum_wizard_partit.html',
     '.kv .v.buit', [],
     '/models/1319?tab=Resum', [], 'span:text-is("Sense deadline")'),
    ('A7', 'numeral del pas FET (✓ verd)', 'PROPOSTA_resum_wizard_partit.html',
     '.step.done .shead .num', [],
     '/models/1319?tab=Resum', [], 'span:text-is("✓") >> nth=0'),
    ('A7', 'xip d\'INCLUSIÓ (elecció fixada)', 'PROPOSTA_resum_wizard_partit.html',
     '.chip.on', [],
     '/models/1319?tab=Resum', [], 'button[aria-pressed="true"] >> nth=0'),
    ('A7', 'acció PRIMÀRIA del pas pendent', 'PROPOSTA_resum_wizard_partit.html',
     '.btn.pri', [],
     '/models/1319?tab=Resum', [], 'button:has-text("Definir graduació")'),
    ('A7', 'capçalera del pas ACTUAL (--sel + filet d\'or)', 'PROPOSTA_resum_wizard_partit.html',
     '.step.now .shead', [],
     '/models/1319?tab=Resum',
     [('click', 'div:has(> span:text-is("Talles")) button:has-text("Canviar")')],
     'div:has(> span:text-is("Talles"))'),
    ('A7', 'xip en REPÒS (triable, no triat)', 'PROPOSTA_resum_wizard_partit.html',
     '.chips .chip:not(.on)', [],
     '/models/1319?tab=Resum',
     [('click', 'div:has(> span:text-is("Talles")) button:has-text("Canviar")')],
     'button[aria-pressed="false"] >> nth=0'),
    ('A7', 'fila de run TRIADA (inclusió)', 'PROPOSTA_resum_wizard_partit.html',
     '.runrow.on', [],
     '/models/1319?tab=Resum',
     [('click', 'div:has(> span:text-is("Talles")) button:has-text("Canviar")')],
     'div:has(> span:text-is("Alpha EU — Men"))'),
    # ── PART B · B1 · Desenvolupament (la home) ──────────────────────────────────────────
    # La home no té maqueta pròpia: el que s'hi mesura és l'ESTRUCTURA DE PÀGINA del §8b, i
    # per això la referència és la mateixa evidència que va servir per al dashboard del model
    # («aquesta pantalla va a missa»). El tram és pell: es mesuren els embolcalls, no cap
    # component del board.
    ('B1', 'píndola de secció ACTIVA', 'PROPOSTA_menu_pantalla_v3.html',
     '.pill.on', [],
     '/', [], 'button[aria-current="page"]'),
    ('B1', 'píndola de secció en repòs', 'PROPOSTA_menu_pantalla_v3.html',
     '.pmenu .pill:not(.on)', [],
     '/', [], 'button:text-is("Planificació")'),
    # 🛑 DESVIACIÓ ESPERADA I DECLARADA — no és un defecte que se'ns hagi escapat. Aquesta
    # pantalla és L'ARREL del producte i la fletxa hi surt DESHABILITADA (`--text-faint`, §1
    # «només deshabilitat») perquè des d'aquí no hi ha on pujar; la maqueta la dibuixa
    # habilitada perquè dibuixa una pantalla que SÍ que penja d'algun lloc. La caixa (fons,
    # vora, radi, mida) ha de casar; la TINTA no, i és la decisió que espera l'Agus. El cas hi
    # és a posta: el que no es mesura no s'ha verificat, i una desviació explicada val més que
    # un cas absent.
    ('B1', "fletxa d'enrere · ARREL (deshabilitada)", 'PROPOSTA_menu_pantalla_v3.html',
     '.back', [],
     '/', [], 'button[aria-disabled="true"]'),
    ('B1', 'nom de la identitat (22/500)', 'PROPOSTA_menu_pantalla_v3.html',
     '.ident .name', [],
     '/', [], 'h1'),
    ('B1', 'targeta de contingut (KPI)', 'PROPOSTA_menu_pantalla_v3.html',
     '.card', [],
     '/', [], 'div:has(> div:text-is("Models de l\'abast"))'),
    # ── B7 · el badge NEUTRE de la graella canònica ─────────────────────────────────────
    # AQUEST CAS ÉS EL REMEI DE LA QUARTA TAPADORA. La bidireccional d'A5 tenia la graella
    # sencera mesurada MENYS els badges, perquè `/models` no en pinta cap d'estat (ESTAT és
    # buida esperant el Kanban i FASE és text pla, §8e): l'única cosa que hi fa de badge neutre
    # és el `SetBadge` de la cel·la del nom, i no totes les files en porten. Es mesura a
    # `/models` amb el filtre que deixa una fila amb SET, i si el banc no en té cap el veredicte
    # ho dirà com a «NO TOCA RES» en comptes de fer-lo passar per verd.
    ('A5', 'badge NEUTRE (la marca de conjunt)', 'NORMA_LLISTA_canonica.html',
     '.b.neutral', [],
     '/models', [], 'td span[style*="border-radius: 999px"], td span[title]'),
]

JS_UN = """
(el) => {
  const cs = getComputedStyle(el);
  const out = {};
  for (const p of %s) { if (p !== 'vora') out[p] = cs[p]; }
  // LA VORA, NOMÉS ON N'HI HA: un costat de gruix 0 computa `currentColor` i no és res que
  // ningú vegi. Es resumeixen els quatre costats amb gruix > 0 i estil != none.
  const v = [];
  for (const b of ['Top', 'Right', 'Bottom', 'Left']) {
    const w = parseFloat(cs['border' + b + 'Width']);
    if (w > 0 && cs['border' + b + 'Style'] !== 'none') v.push(b[0] + w + ':' + cs['border' + b + 'Color']);
  }
  out.vora = v.length ? v.join(' ') : '—';
  out.__txt = (el.textContent || '').trim().slice(0, 24);
  return out;
}
""" % PROPS


def _gestos(pag, gestos):
    for g in gestos:
        try:
            if g[0] == 'click':
                pag.locator(g[1]).first.click()
            elif g[0] == 'fill':
                pag.locator(g[1]).first.fill(g[2])
            pag.wait_for_timeout(600)
        except Exception:
            pass


def _mesura(pag, sel):
    """Els selectors van per TEXT o per ARIA a posta: és el que un humà veu, no una classe."""
    try:
        loc = pag.locator(sel).first
        if loc.count() == 0:
            return None
        return loc.evaluate(JS_UN)
    except Exception:
        return None


def _prep_pagina(pag, handler):
    pag.route('**/*', handler)


def main():
    if not TOKEN:
        sys.exit('Falta FTT_QA_TOKEN.')
    if not DIST.exists():
        sys.exit('Cal `npm run build`.')
    sess = requests.Session()

    def handler(route, request):
        url = request.url
        cami = url.split(BASE, 1)[-1].split('?')[0] if url.startswith(BASE) else url
        if cami.startswith('/api/'):
            try:
                r = sess.request(request.method, VIU + url.split(BASE, 1)[-1],
                                 headers={'Host': HOST_TENANT, 'Authorization': f'Bearer {TOKEN}',
                                          'Content-Type': 'application/json'},
                                 data=request.post_data_buffer, timeout=30)
                route.fulfill(status=r.status_code, body=r.content,
                              headers={'content-type': r.headers.get('content-type', 'application/json')})
            except Exception as e:
                route.fulfill(status=502, body=f'{{"error":"{e}"}}',
                              headers={'content-type': 'application/json'})
            return
        f = DIST / cami.lstrip('/')
        if not f.is_file():
            f = DIST / 'index.html'
        route.fulfill(status=200, body=f.read_bytes(),
                      headers={'content-type': mimetypes.guess_type(f.name)[0] or 'text/html'})

    desviacions = 0
    # 🚨 LA QUARTA TAPADORA (part B, entre les dues sessions): **una comprovació que no toca res
    # és indistingible d'una que passa.** La bidireccional d'A5 donava verd sobre `.b.neutral`
    # durant tot un bloc perquè la graella de `/models` **no pinta cap badge d'estat** (la columna
    # ESTAT hi és buida esperant el Kanban i la FASE és text pla, §8e): el cas existia, es corria,
    # i no comparava res. Un selector que no troba res i un selector que troba una cosa correcta
    # produeixen el MATEIX silenci.
    # `_mesura()` ja distingeix els dos casos —torna `None` quan `count() == 0`—, o sigui que la
    # informació hi era i el que faltava era que el VEREDICTE la separés. Ara es compten a part i
    # es llisten al final: un cas mort no pot passar per un cas verd.
    morts = []
    casen = 0
    with sync_playwright() as p:
        nav = p.chromium.launch()
        # ── banda MAQUETA: fitxer local, sense cap intercepció ────────────────────────────
        maq_ctx = nav.new_context(viewport={'width': 1600, 'height': 1000})
        maq_pag = maq_ctx.new_page()
        maq_cache = {}

        def llegeix_maqueta(fitxer, sel, gestos_maq):
            clau = (fitxer, tuple(map(tuple, gestos_maq)))
            if maq_cache.get('clau') != clau:
                maq_pag.goto((MAQ / fitxer).as_uri(), wait_until='networkidle')
                maq_pag.wait_for_timeout(500)
                _gestos(maq_pag, gestos_maq)
                maq_cache['clau'] = clau
            return _mesura(maq_pag, sel)

        # ── banda PANTALLA: bundle del disc + API viva ────────────────────────────────────
        ctx = nav.new_context(viewport={'width': 1600, 'height': 1000})
        pag = ctx.new_page()
        _prep_pagina(pag, handler)
        pag.goto(BASE + '/', wait_until='domcontentloaded')
        pag.evaluate("([t]) => { localStorage.setItem('access_token', t);"
                     " localStorage.setItem('fhort.lang','ca') }", [TOKEN])

        # `FTT_QA_TRAM=B1,A5` corre NOMÉS aquests trams. La llista sencera passa de 50 casos i
        # triga; sense filtre, tancar un tram obliga a esperar tots els altres — i, pitjor, el
        # token de la sessió pot CADUCAR pel camí. Quan això passa l'app redirigeix a /login i
        # els casos del final es mesuren contra una pantalla que no és la seva: surten com a
        # «no mesurat» i com a desviacions absurdes (un h1 a 40px/700, que és el del navegador).
        # És un fals negatiu que s'assembla massa a un defecte. El filtre és per a treballar;
        # **la correguda de tancament es fa SEMPRE sencera i sense filtre**.
        nomes = {x.strip() for x in os.environ.get('FTT_QA_TRAM', '').split(',') if x.strip()}
        tram_actual = None
        for tram, què, fitxer, sel_maq, gestos_maq, ruta, gestos, sel_pant in CASOS:
            if nomes and tram not in nomes:
                continue
            if tram != tram_actual:
                print(f'\n═══════ {tram} ═══════')
                tram_actual = tram
            m = llegeix_maqueta(fitxer, sel_maq, gestos_maq)

            pant = None
            if sel_pant:
                pag.goto(BASE + ruta, wait_until='networkidle')
                pag.wait_for_timeout(1400)
                _gestos(pag, gestos)
                pant = _mesura(pag, sel_pant)

            print(f'\n  · {què}   [maqueta `{sel_maq}`]')
            if m is None:
                print('      ⚠️  la maqueta no té aquest element — cas a revisar')
                morts.append(f'{tram} · {què} · NO HI ÉS A LA MAQUETA (`{sel_maq}`)')
                continue
            if pant is None:
                print('      ⚠️  NO MESURAT a la pantalla (estat no assolible amb les dades vives)')
                morts.append(f'{tram} · {què} · NO MESURAT a la pantalla (`{sel_pant}`)')
                continue
            for prop in PROPS:
                a, b = m.get(prop), pant.get(prop)
                if a == b:
                    continue
                # el radi de píndola i el pes es comparen igual; la resta és senyal
                desviacions += 1
                print(f'      🔴 {prop:22} maqueta={a!r:26} pantalla={b!r}')
            else:
                pass
            if all(m.get(x) == pant.get(x) for x in PROPS):
                casen += 1
                print('      ✓ casa a totes les propietats mesurades')
        nav.close()
    # ── EL VEREDICTE ÉS DE TRES COLUMNES, no de dues (proposta de la S2, ratificada per Agus).
    # «N mesurats · M desviacions» amagava la tercera possibilitat, que és la pitjor de les tres:
    # el cas que **no toca res**. Ara es diuen els tres números i el tercer, si no és zero,
    # s'explica cas per cas — igual que una desviació.
    total = casen + desviacions + len(morts)
    print(f'\n──────── {casen} CASEN · {desviacions} DESVIEN · {len(morts)} NO TOQUEN RES '
          f'(de {total} casos) ────────')
    if morts:
        print('   ⚠️  ELS QUE NO TOQUEN RES NO SÓN VERDS: SÓN SILENCI. Cadascun s\'ha')
        print('       d\'explicar (selector que no troba · estat no assolible amb les dades')
        print('       vives · element que la maqueta no dibuixa), com una desviació.')
        for x in morts:
            print(f'   · {x}')
    # El codi de sortida segueix penjant NOMÉS de les desviacions: un cas no mesurable amb les
    # dades del banc és una limitació declarada, no un defecte de la pantalla. El que canvia és
    # que ja no es pot passar per alt, que era el problema.
    sys.exit(1 if desviacions else 0)


if __name__ == '__main__':
    main()
