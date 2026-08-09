# NORMA_LAYOUT · v1 — ratificada per Agus (Patró C) 2026-08-08 (S37)

**Llei d'UI de la casa.** Cap pantalla nova ni retoc sense complir-la. El guardia-ui la fa complir
amb **verificació bidireccional** (maqueta→pantalla I pantalla→maqueta).
**Jerarquia: ordre/captura d'Agus > maqueta > NORMA > majoria de pantalles.**
Evidència visual: `ops/maquetes/` mock-ups NORMA_LAYOUT v2-v4 + FITXA_portes_i_accions + STEPPER_flux.

## 1 · Tokens

### Superfícies
- `--bg-page: #fbfaf8` — fons de pàgina (quasi blanc càlid)
- `--white: #ffffff` — TOT panell, targeta i capçalera
- `--sel: #f7f5f2` — SELECCIÓ (fila/contenidor triat) + filet d'or 3px esquerre
- `--line: #e8e5e0` — vores i separadors
- ❌ **`--gold-pale` (crema) ELIMINAT del sistema** — cap superfície ni estat

### Marca
- `--gold: #c27a2a` (== color del logo) — marca, icona activa, filet de selecció, focus, capçalera de columna base
- `--gold-border: #e0c8a0` — vora del botó secundari/portes, marc de columna base, watchpoints

### Tintes
- `--text-main: #1d1d1b` (4.91:1 s/gold) · `--text-soft: #6e6a64` (5.31:1 s/blanc, icones en repòs) · `--text-faint: #98938b` (només deshabilitat)

### Acció
- `--accio: #2b65c2` (blau mitjà, complementari del gold, 5.61:1 AA) — **NOMÉS el botó primari**
- 🔒 **EXCEPCIÓ ÚNICA DEL PRODUCTE (Agus, 09/08): LA PORTA D'ENTRADA VA EN DAURAT PLE.** A `Login`,
  `/entrar` i el reset de contrasenya (i la porta bessona del backoffice) la primària es queda
  `--gold` ple. **Motiu: allà encara no s'és dins del producte, s'és davant de la MARCA** — el
  botó d'entrar no competeix amb cap altra acció de la pantalla i el daurat hi fa de logo, no
  d'acció. És l'única excepció a la §5.1 i s'escriu aquí perquè una excepció que no consta és
  indistingible d'un incompliment: la sonda `ops/qa/qa_sonda_fons_accio.py` l'ha de conèixer i
  DIR-LA, mai callar-la. Tinta: `--text-main` sobre daurat (4.91:1, la solució de S37 «quan el
  fons de marca no pot canviar, canvia la TINTA»).

### Semàfor (D-31.21: la dada porta el color)
- `--ok: #2e7d32` (5.13 AA) + `--ok-bg: #e9f3ea`
- `--warn-state: #ff9942` + `--warn-state-bg: #ffedd9` — ⚠️ 2.12:1 com a text: **decisió de marca conscient** (pes 700 obligatori)
- `--err: #b42318` (6.63 AA) + `--err-bg: #fbebe9`
- **BADGES d'estat (esmenes Agus 08/08): SEMPRE fons suau + tinta del color + VORA FINA DEL MATEIX COLOR — sense excepció, tots els colors** (verd, taronja, vermell, neutre amb --line, casa amb --gold-border). Mai fons ple de color, mai badge de color sense filet.
- **DUES SELECCIONS DIFERENTS (esmena Agus 08/08):** «on soc» (fila activa, pas actual) = `--sel` + filet d'or · «INCLÒS en la definició» (targets/capes/restriccions marcades, multi-selecció) = **VERD**: fons `--ok-bg` + tinta i vora `--ok`. Marcar és confirmar, no navegar.
- **ACCIONS COMPOSTES (esmena Agus 08/08):** si una acció primària té variants (crear manual vs importar), UN sol botó blau amb desplegable — mai dos botons d'acció directa a la mateixa capçalera.

## 1b · MAPA DE TOKENS I POLÍTICA DE MIGRACIÓ (decisions Agus 08/08, resposta a l'aturada T0)
El codi viu i la norma no coincidien en 5 punts. Resolució:

**(a) Semàfor: la norma mana; el codi s'hi adapta.** `--ok` passa de `#3b6d11` a **`#2e7d32`**, `--ok-bg` de `#eaf3de` a **`#e9f3ea`**; `--err` de `#a32d2d` a **`#b42318`**, `--err-bg` de `#fcebeb` a **`#fbebe9`**. Motiu: les maquetes ratificades a pantalla porten els hex de la norma; dos verds al sistema és la deriva que combatem. Canvi global en UN commit aïllat, amb `--gate/--gate-bg/--placed-bg` (àlies) revisats darrere. Tots dos valors nous compleixen AA.

**(b) `--line` és token NOU que conviu amb `--border`.** `--border: #e0d5c5` (crema) NO es toca ni s'àlia: cada pantalla el canvia per `--line: #e8e5e0` quan passa la seva conformitat. Mateixa política progressiva que `--gold-pale`. `--border` queda marcat DEPRECAT amb comentari.

**(c) Escala de tintes de tres nivells.** Es creen `--text-soft: #6e6a64`, `--text-faint: #98938b`, `--panel: #ffffff`, `--line-soft: #f0eeea`. `--text-main` es manté. `--text-muted` es manté viu i DEPRECAT (no s'àlia fins saber-ne l'hex real; l'agent l'ha de reportar).

**(d) El taronja de TEXT s'enfosqueix; la regla d'Agus es manté.** `#ff9942` sobre `#ffedd9` dona 1.86:1 — inadmissible per a text i contradiu el vet de C5. Es parteix el token: **`--warn-state: #ff9942`** per a VORES, farciments i marques de dada · **`--warn-ink`** (taronja fosc de la mateixa família, ≥4.5:1 sobre `--warn-state-bg`) per al TEXT dels badges. La forma ratificada (fons clar + text taronja + filet fi) no canvia; només el to del text, perquè es llegeixi. Substitueix la nota «2.12:1 decisió conscient» del §1.

**(e) `guardia-ui.md` del repo és una còpia VELLA.** La versió vigent (amb NORMA com a llei primera i bidireccional obligatòria) viu al vault i s'ha de sincronitzar a la màquina abans de cap verificació. L'agent no el modifica mai pel seu compte.

**Jerarquia de fonts confirmada:** NORMA_LAYOUT.md és LA LLEI; els HTML canònics són l'EVIDÈNCIA VISUAL de seccions concretes (§8b, §8e, §8f). Si xoquen, mana la regla escrita de la norma i s'atura per reportar-ho.
- h1 pàgina **22px pes 500** / 28 · h2 secció 18/24 · h3 subtítol 15/20 · cos **12/16** (decisió conscient: mono densa) · caption/TH **10/12 — MÍNIM ABSOLUT, mai 8px llegible**
- **Capçalera de TALLA** (títol de columna de valors): **14px pes 600, tinta principal, centrada, sense majúscules forçades**
- Capçalera de llista = **th 10px MAJÚSCULES tracking .08em** a tot arreu (també llistes `<div>`)

## 3 · Espaiat i radis
- **Base 4px. Tot espai múltiple de 4. Excepcions: amb token i nom, o no existeixen.**
- Padding arrel de pàgina **0** (el `<main>` dona 24) · targeta padding **16** · separació entre panells **16**
- `--col-talla: 60px` — amplada ÚNICA de columna de valor, centrada, valors a pes normal (lectura ràpida: les talles juntes)
- Radis: control `6px` (`--r-ctrl`, excepció batejada) · targeta `12px` · badge/chip `999px` (píndola SEMPRE)

## 4 · Taula de mesures
- Columna base: **fons `--sel`** + vores fines `--gold-border` + etiqueta de talla en `--gold`; a la fila seleccionada la intersecció s'enfosqueix un punt (#f1ede7)
- Fila seleccionada: `--sel` + filet d'or 3px

## 5 · Jerarquia d'ACCIÓ — «dos mons que no es toquen»
**Blau = el que has vingut a fer (1/pantalla) · vora daurada = accions i portes de la casa · gris = utilitat · vora vermella = destrueix · semàfor = només tinta de dades · gold = marca/selecció/base.**

1. **PRIMÀRIA**: fons `--accio` + blanc. **UNA per pantalla**, sempre al mateix lloc. És «l'acció que completa la feina d'aquí».
2. **SECUNDÀRIA**: blanc + vora `--gold-border` + tinta i icona fosques, padding 8×16. (Agus ratifica la vora daurada: és la vora de la casa, no crida marca.)
3. **PORTES** (Graduació, Fitxers…): estil secundari **+ chevron/icona de destí**. Mai blaves (no comprometen). Seccions germanes = **tabs**, no botons.
4. **TERCIÀRIA**: text sol `--text-soft`, hover `--sel`. El **ghost daurat es JUBILA com a botó** (mor el deute AA dels ghosts d'acció).
5. **DESTRUCTIVA**: vora + tinta `--err`, mai plena en repòs; el vermell ple només a la confirmació final.
6. **Menú «Accions ⋯»** (secundari): NOMÉS ocasionals (duplicar, exportar, arxivar). MAI passos de flux.
7. Deshabilitat: **baixa el fons, no la tinta.**

## 6 · Accions de MOTOR = passos de FLUX (stepper), no botons solts
- Seqüència visible com a contenidors amb estat: p.ex. Mesures = `POM → Graduació → Mesurar prenda → Propagar`.
- Estats del pas: **FET** `--ok-bg`+check+`--ok` · **ACTUAL** `--sel`+filet d'or (el «on soc» de la casa) · **DISPONIBLE** blanc+`--line` · **BLOQUEJAT** `--text-faint` s/`--bg-page`.
- **El blau de la pantalla és sempre «el pas actual, executat»** i canvia sol en avançar (Desar mesures → Propagar). Mai dos blaus: el flux els serialitza. El stepper diu ON ETS; el blau diu FES-HO.
- ⚠️ Conscient (no col·lisió): `--ok` a «fet» del stepper i a «Accepted» del fitting — contexts separats, mateix significat «positiu confirmat».
- 🔒 **La seqüència exacta de cada superfície és DOMINI (Montse), no estil.** La forma entra a la norma; el contingut de cada flux es valida abans de construir.

## 7 · Controls de veredicte (A/J/R)
- Botons neutres en repòs; el triat: `--sel` + subratllat del color del veredicte.
- El color PLE el porta el RESULTAT (text «Accepted/Adjusted/Rejected» + el número, mateix color, mateix estil els tres). **Sense badges, sense pastilles, sense «Pendent»** (cel·la buida).

## 8 · Icones
- **Tabler outline. TRES MIDES i prou (esmena Agus 08/08): 14px** dins de botó i inline amb cos (traç 1.75) · **16px** files de llista, capçaleres de columna, inputs (traç 1.5) · **20px** menú lateral i standalone (traç 1.5). Res fora d'aquestes tres; el contenidor que les envolta, múltiple de 4.
- Quatre tintes: repòs `--text-soft` · activa `--gold` · deshabilitada `--text-faint` · destructiva `--err`. Dins de botó: `currentColor` sempre.

## 8b · Estructura de pàgina — CANÒNICA (ratificada Agus 08/08 · evidència: PROPOSTA_menu_pantalla_v3.html — «aquesta pantalla va a missa»)
De dalt a baix, TOTA pantalla del producte:
1. **TOP BAR del sistema** (blanca, filet inferior): a l'esquerra el **breadcrumb de navegació — Tenant › secció › pantalla** (tenant sempre primer; així sempre se sap on s'està navegant); a la dreta usuari · data/hora · commutadors (cm→inch, idioma) · perfil.
2. **MENÚ DE PANTALLA**: barra **BLANCA de costat a costat amb FILET A DALT I A BAIX** — sempre reconeixible. Dins: **← SEMPRE PRIMER** (botó quadrat 32px, icona 16, destí explícit — mai history.back() a pèl) · separador vertical fi · **píndoles de secció** (activa = fons --sel + vora --gold-border + pes 600; repòs = --text-soft sense vora; hover --sel — ni blau ni daurat ple: navegació no és acció ni marca) · extrem dret: portes transversals (Watchpoints…) en secundari petit, mai l'acció primària.
   **Sense seccions: només queda la fletxa.** La barra no desapareix mai — la posició del ← és fixa a tot el producte.
3. **IDENTITAT — SOBRE EL FONS DE PÀGINA, SENSE CONTENIDOR** (és informativa, no un panell): codi en caption + nom a 22/500 + badge de fase (neutre) + **accions a la dreta** (Accions ▾ secundari · destructiva amb vora · blau només si la pantalla té acció primària).
4. **CONTINGUT**: targetes blanques amb filet --line i radi 12.
El breadcrumb VIU a la top bar (mai s'elimina); el menú lateral de sistema NO ES TOCA.
Regla de conformitat d'aquesta estructura: **s'adapta l'estil, MAI es canvia cap component ni se n'inventa cap** — l'estructura de cada pantalla mana la pantalla/maqueta existent.

## 8b-bis · Menú de pantalla vs tabs de secció
- **MENÚ DE PANTALLA** (seccions grans d'una entitat: Dashboard · Resum · Mesures · Escalat…): píndoles dins la barra blanca del §8b. UN sol tipus de menú de pantalla a tot el producte.
- **TABS DE SECCIÓ** (2-3 germanes dins d'un panell: «Talles i POMs · Fitxers»): subratllat d'or. No es barregen els dos patrons al mateix nivell.
- **Menú lateral (sistema): NO ES TOCA** — a Agus li agrada tal com és. Ítem actiu ja fa --sel+filet; només alinear icones a 20px/--text-soft quan toqui.
- **Top bar**: pendent de foto pròpia.

## 8c · KPI, badges de fase i estats buits (decisions Agus 08/08)
- **Badge de FASE: NEUTRE** (fons suau + tinta --text-main + filet --line), com a les maquetes. La fase no és semàfor ni marca.
- **KPI/recomptes neutres** (comptadors d'abast, totals): **--text-main**. NOMÉS els KPI d'alerta porten semàfor (p.ex. «En risc · 1» en --err). El daurat NO pinta números.
- **Estat buit = frase en --text-faint cursiva** («Cap esdeveniment proper»), mai caixa buida muda.
- **Pantalles de CONSULTA poden tenir ZERO accions primàries** — si no hi ha «cosa que has vingut a fer», no hi ha blau. Si n'hi ha una, és blava (o el que toqui: destructiva, etc.).
- **Filtres en línia** (cerca, selects, dates): control de la casa (vora --line, radi 6, focus daurat), alçada única, MAI blaus — filtrar no és l'acció de la pantalla. «Neteja» = terciària.

## 8e · Llistes principals — CANÒNICA PER A QUALSEVOL LLISTA (ratificada Agus 08/08 «va a missa» · evidència NORMA_LLISTA_canonica.html)
**TOTA llista del producte té aquest layout amb capçaleres.** No és un patró opcional de la pantalla Models: és LA graella de llista de la casa (Models, Suppliers, Clients, Encàrrecs, Comercial, Fittings, jocs de regles, runs…).
- **Acció primària PUJADA AL MENÚ = ESTIL DE MENÚ** (deixa de ser botó, deixa de ser blava). El blau viu al contingut; el menú té el seu llenguatge.
- **Ordre del menú**: ← · [filtres de VISTA: «en curs» (defecte) · «acabats»] · separador · [accions: Nou ▾ · Accions ▾ · Filtres]. Primer què veig, després què hi faig. Les accions a l'ESQUERRA (comportament de menú), mai a la dreta.
- **Filtres ràpids de vista al menú**: els elements acabats NO es llisten per defecte (embruten la cerca). Criteri exacte de «acabat», pendent de domini.
- **Comptador = selecció, no KPI, i ELS VALORS MANEN**: «12/84» gran (22/600, «/84» menor i suau) + etiqueta «models» en caption — el nom de l'entitat ja no és títol, és element. La CERCA comença al costat, mateixa línia, amb els selects ràpids; els filtres avançats viuen al menú.
- **Llista columnada a amplada plena** (comptant el menú lateral): capçaleres th 10 MAJÚSCULES ordenables; **icona d'ordenació SVG 12px traç 1.75** (mai caràcter de text — a 10px no es veu): inactiva --text-faint (--text-soft al hover), columna ordenada amb fletxa --gold traç 2.
- **Amplades de columna PER CONTINGUT, no iguals**: cada columna amb min/max propis (refs estretes, dates fixes, la dada reina generosa).
- **OVERFLOW: ellipsis (…) + hover mostra el text sencer** (title/tooltip). MAI salt de línia (trenca la fila d'una línia), MAI scroll per columna.
- **La dada reina de cada llista porta el pes** (a Models: EL NOM, 600/tinta principal; les refs en secundari — l'invers del catàleg de POMs on la reina és el codi).
- **FASE = NOMÉS TEXT** (Pendent · Desenvolupament · Proto…), sense badge. **ESTAT (comercial, del Kanban) = badge amb codi de colors**: Començat neutre · En curs taronja · Acabat verd.
- Fila seleccionada: --sel + filet d'or. Checkbox amb accent --gold. Paperera per fila: icona destructiva 14, hover --err-bg.
- Tècnic assignat FORA de les llistes de models (viu a Planificació).

## 8f · Wizard partit en subespais + blau per estat (ratificat Agus 08/08 · evidència PROPOSTA_resum_wizard_partit.html)
- **El Resum del model té DOS CONTENIDORS COSTAT A COSTAT**: esquerra «Informació» (= pas 1 · Identificació del wizard; «Editar» obre el formulari AL MATEIX LLOC, mai pantalla a part) · dreta «Definició del model» = LA COLUMNA DE TREBALL.
- **Els passos 2 · Peça, 3 · Talles i 4 · Graduació viuen al contenidor dret com a SUBESPAIS separats**, cadascun amb les seves accions dins del seu espai. El model no desapareix mai de la vista.
- **Les eleccions queden FIXADES i VISIBLES en completar-se** (chips verds d'inclusió + valors escrits) amb «Canviar» en secundari. Res s'amaga en tancar-se.
- **Estats del subespai = llenguatge del stepper**: FET verd amb ✓ · ACTUAL --sel + filet d'or · BLOQUEJAT tènue amb el motiu escrit.
- **EL BLAU DEPÈN DE L'ESTAT**: pendent = acció primària blava («Editar» en model nou, «Desar talles» al pas actual); fet = baixa a secundària o esdevé porta («Veure graduació ›»). El blau assenyala el pas pendent i calla quan està fet.
- **Excepció matisada a «un blau per pantalla»**: passos paral·lels d'un mateix camí en contenidors separats poden portar un blau per pas pendent; s'apaguen en completar-se.

## 8d · Mètode de conformitat (lliçó 08/08)
- **Les fotos serveixen per a estructura i norma nova; la conformitat fina (hex, px, alçades) es MESURA** contra valors computats (taula_mestra / guardia-ui), mai a ull. Cap pantalla és «conforme» fins que els tokens nous estiguin desplegats i mesurats.

## 9 · Regles de conducta (de S37, ratificades)
- Les maquetes fixen **aparença i estructura**; els **estats asíncrons** (loading/error/buit) van amb el bastiment de la casa (Center/Feedback), zero vocabulari nou, treïbles en un bloc.
- La **conducta imprescindible** (què obre un botó, permisos, confirmacions destructives, validacions de clau) va amb patrons de la casa i **es llista SEMPRE al report com a «conducta afegida»** perquè Agus la pugui vetar.
- **Verificació bidireccional obligatòria**: la direcció maqueta→pantalla no pot trobar invencions per construcció; cal recórrer la PANTALLA element per element.

## 10 · Notes de registre
- El daurat de marca es queda: ghosts INFORMATIUS de text daurat (no-acció) segueixen sent decisió conscient sota AA.
- Colors descartats amb motiu: verd/llima de botó (col·lisió semàfor) · teula (col·lisió err) · turquesa (AA) · magenta/violeta (caràcter) · blau cel #2B95C2 (no aguanta tinta blanca; reservat com a possible informatiu secundari).
