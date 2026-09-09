# Informe · MAQUETA CANÒNICA del Taller de Patró (v4)

**Data:** 2026-08-25 · **Fil:** S46-MOTOR · Patró A + maqueta (agent UI)
**Lliurables:** `ops/maquetes/MAQUETA_TALLER_V4.html` (3 estats al mateix fitxer) + aquest informe
**Entrades:** `MOCKUP_TALLER_PATRO_V4.html` · `NORMA_LAYOUT.md` v1 ·
`CENS_UI_TALLER_2026-08-25.md` + `captures_ui_taller_2026-08-25/` · codi viu del Taller

> **Read-only.** Cap `systemctl`, cap test executat, cap escriptura a BD, cap línia de codi
> de producte tocada. Escriptura només a `ops/maquetes/MAQUETA_TALLER_V4.html` i a aquest
> fitxer. Res commitat. Les captures de verificació viuen al **scratchpad**, no al repo.

---

## 0 · El resum en set línies

1. **La maqueta canònica existeix i passa la NORMA amb valors computats: 0 incompliments**
   sobre 122 valors d'espaiat, 28 d'interlineat, 3 jocs d'icona i 4 badges. §2
2. **El mockup v4 en tenia 70**, mesurats amb el mateix arnès — entre ells **4 classes per
   sota del terra absolut de 10 px** (§2 de NORMA), que és un vet explícit. §2.3
3. **Les dues correccions d'Agus són aplicades** i la primera surt gairebé de franc: el
   component de capes **ja té la costura feta** (`contenidorEines` + `gran`), i passar-lo a
   la pestanya «Visualitzar» és **moure el destí del portal**, no escriure una tercera pell. §3
4. 🚨 **El mockup mostrava CINC desviacions de llei que la maqueta corregeix**, la més gran:
   dibuixava **sis capes** quan el 837 **només n'ofereix cinc** — «una capa que el fitxer no
   porta no s'ofereix» és llei escrita al codi. §5.1
5. 🚨 **El daurat ple del codi viu no és de NORMA, i el mateix fitxer ja ho sap**:
   `TallerPatro.jsx:1845-1852` escriu la lliçó als xips d'àncora mentre `:1557` i `:1778` la
   incompleixen. Mesurat: l'`opacity: .55` dels commutadors deixa el text a **3,79:1**. §5.2
6. **La taula de gap té 24 entrades**: 11 [estil] · 8 [estructura] · 5 [funcional-NOU]. §5
7. **9 increments proposats, cap implementat.** El candidat 1 (cotes de la peça
   seleccionada) és **un filtre a `PatternViewer.jsx:479`**, presentació pura. §6

---

## 1 · Nota de procedència de les fonts (i una errata de camí)

El brief situa la llei a **`docs/ordres/NORMA_LAYOUT.md`**. **Allà no hi és.** L'única còpia
del repo viu a `ops/maquetes/NORMA_LAYOUT.md`, i és **idèntica a les nou worktrees**
(17.505 B exactes a `ftt-staging`, `ftt-m1`, `ftt-m3cv`, `ftt-m4`, `ftt-m5`, `ftt-m5net`,
`ftt-f2`, `ftt-t7`, `ftt-t9`). Com que no hi ha dues versions possibles, **és una errata de
camí i no una ambigüitat de font**: s'ha fet servir aquella, que declara «v1 — ratificada
per Agus (Patró C) 2026-08-08».

El brief també cita una **«§5 del vault»** amb les regles de llenç. La NORMA del repo no en
té cap: la seva §5 és la jerarquia d'acció. S'ha fet servir **el resum inline del brief**,
que és el que el brief mana, i cada regla queda anotada al llenç de la maqueta.

`guardia-ui.md` del repo **no s'ha llegit ni tocat**: NORMA §1b(e) el declara còpia vella.

---

## 2 · Conformitat NORMA · MESURADA (§8d: valors computats, mai a ull)

### 2.1 L'arnès

Dos scripts al scratchpad, tots dos sobre el fitxer final:

| script | què mesura |
|---|---|
| `norma_check.py` | parseja el CSS regla a regla + el marcatge: escala tipogràfica, interlineat, radis, múltiples de 4, mides i traços d'icona, recompte de blaus per pantalla, forma dels badges, hex crus i `var()` orfes |
| `contrast.py` | ràtios de contrast WCAG de cada parella tinta/fons del sistema |
| `render.py` (Chromium headless, 1600×1000) | mesura el **DOM renderitzat**, no el CSS: mides reals, `getComputedStyle` |

### 2.2 Resultat sobre `MAQUETA_TALLER_V4.html`

```
valors comprovats: {'line-height': 28, 'espai': 122, 'icona-exempta': 6,
                    'font-size': 1, 'icona-ok': 3, 'blaus-frame-1': 0,
                    'blaus-frame-2': 1, 'blaus-frame-3': 0,
                    'badge-ok': 4, 'badge-pindola-vora': 1}
  · classes amb fons --accio al CSS: 1 (.primary)
  · hex al :root (tokens): 29 · hex FORA del :root: 3 (bastida, fora del .frame)
✓ CAP INCOMPLIMENT.
```

**Tokens de mètrica, un a un:**

| token | valor | veredicte |
|---|---|---|
| `--fs-caption` · `--fs-label` | 10px | ✓ el terra absolut de §2, mai per sota |
| `--fs-body` | 12px | ✓ («cos 12/16, decisió conscient: mono densa») |
| `--fs-h1` | 22px | ✓ |
| `--r-ctrl` / `--r-card` / `--r-pill` | 6 / 12 / 999 | ✓ §3 exacte |
| `--filet-sel` | 3px | ✓ **excepció BATEJADA** (§1, filet d'or de selecció) |
| `--filet-tab` | 2px | ✓ **excepció BATEJADA** (§8b-bis, subratllat d'or) |
| `--hair` | 1px | ✓ **excepció BATEJADA** (vora i separador) |

**Mesura al DOM renderitzat** (Chromium, no el CSS):

| element | mida real | fs | lh | radi | vora |
|---|---|---|---|---|---|
| `.back` (← de §8b) | **32,0 × 32,0** | 12px | 16px | 6px | 1px |
| `.fbtn` (navegació del llenç) | 32,0 × 32,0 | 12px | 16px | 6px | 1px |
| `.pill` | 84,0 × **20,0** | 10px | 12px | **999px** | 1px |
| `.badge` | 127,9 × **16,0** | 10px | 12px | **999px** | 1px |
| `.card` | 287,0 × 342,0 | 12px | 16px | **12px** | 1px |
| `.cmd.on` | 78,0 × 50,0 | 10px | 12px | 6px | 1px |
| `.primary` (l'únic blau) | 237,0 × 32,0 | 12px | 16px | 6px | 0 |
| `.colL` / `.colR` | 312 / 288 | — | — | — | — |

**Icones** — les tres mides de §8 i cap altra: `.i14` 14px traç **1.75** · `.i16` 16px traç
**1.5** · `.i20` 20px traç **1.5**. Verificat que cada classe declara la seva mida i el seu traç.

**Un sol blau** (§5.1): estat 1 = **0** · estat 2 = **1** · estat 3 = **0**. Cap pantalla en
porta dos. Els estats 1 i 3 en porten zero **a posta**: §8c admet zero primària, i les
pestanyes de secció **serialitzen el blau** exactament com §6 vol que ho faci un flux.

**Badges** (§1, esmena Agus 08/08): els quatre (`b-ok`, `b-warn`, `b-neu`, `b-casa`) porten
**fons suau + tinta del color + vora fina del mateix color**, tots píndola. Cap fons ple de
color, cap badge de color sense filet.

**Colors via token, mai hex** (CLAUDE.md): **0 hex crus al marcatge** i **0 `var()` orfes**.
Els 3 hex de fora del `:root` són la **bastida** del full (fons del document i tinta del
rètol de cada estat), **fora del `.frame`** — no són superfície de producte i s'allisten amb
nom a l'script.

### 2.3 El mateix arnès sobre el mockup v4 — el punt de partida

| categoria | mockup v4 | maqueta v4 |
|---|---|---|
| espai no múltiple de 4 | **54** | 0 |
| tipografia fora d'escala | **10** | 0 |
| interlineat fora d'escala | **4** | 0 |
| radi fora de 6/12/999 | **2** | 0 |
| **total** | **70** | **0** |

🚨 **Quatre d'aquelles deu són per SOTA del terra**: `.b-ok`, `.b-warn`, `.b-neu` i `.nou`
anaven a **9px**, i §2 diu «caption/TH — 10/12, **MÍNIM ABSOLUT, mai 8px llegible**». La
resta eren 11px i 10,5px, que no són cap graó de l'escala (10 · 12 · 14 · 18 · 22 · 32).
No és pedanteria de píxel: **és el mecanisme pel qual una escala deixa de ser una escala.**

### 2.4 Contrast · AA mesurat, no assumit

| parella | ràtio | veredicte |
|---|---|---|
| `--text-main` s/ `--white` | **16,88** | AA |
| `--text-main` s/ `--sel` | **15,52** | AA |
| `--text-main` s/ `--gold` | **4,91** | AA (la solució de S37) |
| `--text-soft` s/ `--white` | **5,37** | AA |
| `--text-soft` s/ `--sel` | **4,94** | AA |
| `--white` s/ `--accio` | **5,61** | AA |
| `--ok` s/ `--ok-bg` | **4,51** | AA |
| `--err` s/ `--err-bg` | **5,69** | AA |
| **`--warn-ink` s/ `--warn-state-bg`** | **5,32** | AA ✓ *(valor del codi)* |
| `--warn-ink` del **mockup** (#a15c0f) | **4,53** | AA just — **corregit al valor del codi** |
| `--warn-state` com a TEXT | 1,86 | **prohibit** — mai s'usa com a tinta a la maqueta |
| `--text-faint` s/ `--white` | 3,05 | només deshabilitat i estat buit (§1) |
| `--text-faint` s/ `--bg-page` | **2,93** | ⚠️ v. [E-11] |

Colors de llenç (no són text; el llindar d'UI és 3,0): `--k-pom` 5,05 · `--k-notch` 7,07 ·
`--k-grain` 6,21 · `--k-sew` 4,63 · `--k-tram` 5,19 · `--k-corba` 3,14 · `--k-int` 3,64.

---

## 3 · Les dues correccions d'Agus, aplicades

### 3.1 Les capes són COMANDOS de «Visualitzar» — i el codi ja hi arriba

La targeta «Capes» **desapareix** de la columna dreta. Passa a ser la fila de comandos de la
pestanya «Visualitzar» (**estat 2**), amb els controls de vista (Reduir · Ampliar ·
Encaixar · %) que avui hi viatgen a la mateixa fila.

🔑 **El component no s'ha de reescriure.** `PatternViewer` ja serveix **dues** superfícies amb
una gramàtica sola:

- `contenidorEines` ([PatternViewer.jsx:145-158](../../frontend/src/components/pattern/PatternViewer.jsx#L145))
  és el node DOM on el pare vol els controls; amb ell, els botons hi van **per portal**.
- `gran` ([:421-431](../../frontend/src/components/pattern/PatternViewer.jsx#L421)) tria la
  pell: mètrica de barra al Taller, mètrica compacta al tab Patró del model.

La correcció 1 **no demana una tercera pell: demana que el portal apunti a la `cmdrow` de
«Visualitzar»**. El cens ho havia marcat com el risc número 10 («les capes tenen DOS
consumidors; el mockup no n'ha de dissenyar un tercer») — i la resposta és que **no en
dissenya cap de nou**.

⚠️ **Conseqüència que Agus ha de veure** (v. dubte D-1): amb les capes dins d'una pestanya,
**des de «Cotes» o «Cosir» no s'hi arriba sense canviar de pestanya**. Avui la barra és una
i sempre les té a mà.

### 3.2 La columna dreta porta tabs de secció

`POMs · Motor` amb **subratllat d'or** (§8b-bis), i una **tercera pestanya contextual** quan
hi ha selecció (estat 3: `Costura`), separada per un filet i sempre **després** de les fixes.
Sense menú lateral: el Taller treballa a pantalla completa, i això és deliberat
([App.jsx:433](../../frontend/src/App.jsx#L433)).

El repartiment que la maqueta proposa: **esquerra = QUÈ ÉS** (arbre + característiques) ·
**dreta = QUÈ S'HI FA** (la feina i les accions). És el que evita que la selecció es
descrigui dues vegades a la mateixa pantalla.

---

## 4 · Els `[NOU]` són de TRES menes, i el mockup les barrejava

El mockup declara al peu: *«[NOU] al mockup encara sense columna a BD: tall · material · fil
editable · origen fix · driving/reference · sentit relatiu · mesura lliure · segment de guia
· filtre semàntics · moure peça»*. **Mesurat contra `patterns/models.py`, això no és exacte**,
i la diferència canvia què costa cada increment:

| `[NOU]` | on seu avui | mena |
|---|---|---|
| tall (CUT n+n) · material | `PatternPiece.metadata` (JSONField, [models.py:168](../../backend/fhort/patterns/models.py#L168)) | **[NOU-UI]** la dada hi és |
| fil editable | `PatternPiece.grain` ([:166](../../backend/fhort/patterns/models.py#L166)) | **[NOU-UI]** hi és, falta EDITAR-lo |
| moure peça (a Organitzar) | `PatternPiece.insert_at` ([:173](../../backend/fhort/patterns/models.py#L173)) | **[NOU-UI]** es persisteix per peça |
| eix de plec / veure plegat | `has_fold` · `doblec_original` ([:172](../../backend/fhort/patterns/models.py#L172)) | **[NOU-UI]** dada sí, vista no commutable |
| filtre «només semàntics» | — no vol cap dada | **[NOU-UI pur]** presentació |
| cotes de la peça seleccionada | — no vol cap dada | **[NOU-UI pur]** presentació |
| **origen fix de grading** | cap columna | **[NOU-BD]** |
| **driving / reference** del POM | cap columna | **[NOU-BD]** |
| **sentit relatiu** (t0↔t1) | cap columna | **[NOU-BD]** |
| **mesura lliure en mm** | cap columna (cens R5b: «`grep` → cap resultat») | **[NOU-BD]** |
| segment de guia | ⚖ **contradicció** — v. dubte D-2 | ? |

🔑 **La conseqüència pràctica:** sis dels onze `[NOU]` **no necessiten cap migració**. El
panell de característiques no està bloquejat pel gap UI→BD; només ho estan tres camps.
*(El gap es documenta aquí i **no s'implementa**, com mana el brief.)*

---

## 5 · VERIFICACIÓ BIDIRECCIONAL · taula de gap

Les dues direccions, com mana NORMA §9: **maqueta→pantalla** (què dibuixo que no hi és) i
**pantalla→maqueta** (recórrer la PANTALLA element per element, que és l'única direcció que
pot trobar el que la maqueta s'ha deixat).

Classificació: **[estil]** = mateix component, altres valors · **[estructura]** = el
component canvia de lloc, de forma o de recompte · **[funcional-NOU]** = comportament que
avui no existeix.

### 5.1 Maqueta → pantalla

| # | element | a la maqueta | al codi viu | classe |
|---|---|---|---|---|
| **M-01** | pestanyes de procés | 6 pestanyes (Fitxer · Visualitzar · Declarar · Cotes · Cosir · Organitzar), subratllat d'or | **no existeixen**: una barra plana amb 4 botons de mode ([TallerPatro.jsx:1566-1604](../../frontend/src/pages/TallerPatro.jsx#L1566)) | **[estructura]** |
| **M-02** | fila de comandos | 2a fila, comandos icona+text de la pestanya activa | només existeix per al mode POM (`SelectorMetode`, [:1755](../../frontend/src/pages/TallerPatro.jsx#L1755)); la resta són botons de la barra única | **[estructura]** |
| **M-03** | capes com a comandos | 6 comandos a «Visualitzar», 5 capes + filtre semàntic | **6 toggles a la barra única per portal** ([PatternViewer.jsx:1160-1177](../../frontend/src/components/pattern/PatternViewer.jsx#L1160)); mateixa gramàtica, altre lloc | **[estructura]** |
| **M-04** | filtre «només semàntics» | comando encès, amaga els 916 punts de corba | **no existeix**: `punts` és tot-o-res ([:1170](../../frontend/src/components/pattern/PatternViewer.jsx#L1170)) | **[funcional-NOU]** (R2) |
| **M-05** | arbre del patró | patró → peça → Trams / Costures / Pinces / Cotes, amb comptadors i badges | **no existeix**: `PieceList` és una llista plana de 5 targetes ([PieceList.jsx](../../frontend/src/components/pattern/PieceList.jsx)) | **[estructura]** |
| **M-06** | característiques en 5 seccions | Què és · Com és · Com es relaciona · Com gradua · Modificable | **no existeix**: `PieceIdentityList` (a l'altra pantalla) té 5 camps plans | **[estructura]** |
| **M-07** | colR amb tabs de secció | POMs · Motor (+ contextual) | **no existeix cap colR**: `<aside>` de 360 a l'ESQUERRA amb 3 `Contenidor` plegables ([TallerPatro.jsx:1280-1339](../../frontend/src/pages/TallerPatro.jsx#L1280)) | **[estructura]** |
| **M-08** | pestanya contextual «Costura» | apareix amb la selecció; accions de la costura | les accions hi són totes dins `RelationsPanel` (911 línies), sense pestanya ni contextualitat | **[estructura]** |
| **M-09** | «cotes: peça seleccionada» | píndola de dues posicions; per defecte, només la peça triada | **no existeix**: es pinten les de TOTES les peces sempre ([PatternViewer.jsx:479](../../frontend/src/components/pattern/PatternViewer.jsx#L479)) — visible a `08_proposta_cosit_oberta.png` | **[funcional-NOU]** |
| **M-10** | cotes fora i esglaonades | fora del contorn, en dos nivells, amb gap i sobresortint | es dibuixen **damunt** de la peça; `cota_offset_mm` és desplaçament manual, no col·locació automàtica | **[funcional-NOU]** |
| **M-11** | navegació flotant al llenç | 5 botons standalone 32px/icona 20 | els mateixos gestos existeixen (pan, zoom, encaixar) però **viuen a la barra**, no al llenç | **[estructura]** |
| **M-12** | llegenda de teclat a la barra d'estat | permanent, amb Esc · ←/→ o F · Supr · Espai | els textos existeixen (`pan_hint`, `arc_flip_hint`) però **només es mostren mentre el gest és viu** ([PatternViewer.jsx:1210-1220](../../frontend/src/components/pattern/PatternViewer.jsx#L1210)) | **[estil]** |
| **M-13** | breadcrumb amb tenant | `fhort › TRV-SS27-0001 · 837 VESTIT › Taller de patró` | comença pel codi intern; **el tenant no hi surt** ([:1921](../../frontend/src/pages/TallerPatro.jsx#L1921)) | **[estil]** |
| **M-14** | botó ← quadrat 32px | icona sola, 32×32, radi 6 (§8b) | botó de text «Tornar a la fitxa», radi **4** ([:1899-1911](../../frontend/src/pages/TallerPatro.jsx#L1899)) | **[estil]** |
| **M-15** | «Mesura lliure mm» `[NOU]` | comando de la pestanya Cotes | no existeix (cens R5b) | **[funcional-NOU]** |
| **M-16** | «Segment de guia» `[NOU]` | comando de la pestanya Cotes | ⚖ **el mode `seg` existeix i està FET** — v. dubte D-2 | **[?]** |
| **M-17** | comptadors d'arbre («21 cotes · 8 cosits», «2 sense nom») | badges informatius per node | les xifres hi són escampades pels títols dels `Contenidor`; **no hi ha node que les agregui** | **[estructura]** |

### 5.2 Pantalla → maqueta (recorregut element per element del codi viu)

| # | element del codi viu | a la maqueta | classe |
|---|---|---|---|
| **E-01** | **Botó de mode ACTIU = `background: var(--gold)` ple** ([TallerPatro.jsx:1557](../../frontend/src/pages/TallerPatro.jsx#L1557)) | `--sel` + vora `--gold-border` | **[estil]** 🚨 v. sota |
| **E-02** | **Botó de MÈTODE i d'OPCIÓ actius = daurat ple** ([:1779](../../frontend/src/pages/TallerPatro.jsx#L1779) i [:1808](../../frontend/src/pages/TallerPatro.jsx#L1808)) | idem | **[estil]** 🚨 |
| **E-03** | **Commutador de capa apagat = `opacity: 0.55`** ([PatternViewer.jsx:1133](../../frontend/src/components/pattern/PatternViewer.jsx#L1133)) | sense opacitat: distinció per fons i vora | **[estil]** 🚨 |
| **E-04** | **Capçalera de `Contenidor` FOSCA** (`--charcoal` + tinta blanca, tracking `.03em`, [Contenidor.jsx:44-52](../../frontend/src/components/ui/Contenidor.jsx#L44)) | capçalera blanca, caption 10 MAJÚSCULES, tracking **`.08em`**, tinta `--text-soft` | **[estil]** ⚖ D-3 |
| **E-05** | `METRICA_EINA.borderRadius = 4` i `METRICA_EINA_COMPACTA.borderRadius = 4` ([PatternViewer.jsx:71-76](../../frontend/src/components/pattern/PatternViewer.jsx#L71)) | `--r-ctrl` = **6** (§3) | **[estil]** |
| **E-06** | `Avis` (bàner de guia) amb fons **`--bg-muted`** i radi 4 ([TallerPatro.jsx:1866-1875](../../frontend/src/pages/TallerPatro.jsx#L1866)) | família `--warn-state-bg` / `--warn-ink`, radi 6 | **[estil]** |
| **E-07** | Píndola de versió amb `borderRadius: 10` ([:1937-1943](../../frontend/src/pages/TallerPatro.jsx#L1937)) | `--r-pill` (999) — «píndola SEMPRE» (§3) | **[estil]** |
| **E-08** | `Veredicte` amb `--warn` / `--warn-bg` (badges vells) ([:1673-1680](../../frontend/src/pages/TallerPatro.jsx#L1673)) | família `--warn-state` de §1b(d) | **[estil]** |
| **E-09** | **22 usos de `var(--mono)` que el sistema no declara** (§ mapa de tokens) | declarat al `:root` | **[estil]** |
| **E-10** | `--fs-h3: 14px` vs NORMA §2 «h3 15/20» | la maqueta **no fa servir h3** — no cal resoldre-ho aquí | **[estil]** ⚖ D-4 |
| **E-11** | `--text-faint` sobre `--bg-page` = **2,93:1** | la maqueta el fa servir **només sobre `--panel`** (3,05) | **[estil]** |
| **E-12** | **Els 4 modes són `disabled={!tascaId}`** ([:1568-1601](../../frontend/src/pages/TallerPatro.jsx#L1568)) | la píndola «Patró digitalització · en curs» diu d'on surt la tasca | ✅ conservat |
| **E-13** | **`?task_id=` és part del contracte**: sense ell, obrir el Taller ESCRIU al domini ([:242](../../frontend/src/pages/TallerPatro.jsx#L242)) | ✅ conservat i escrit al capçal del fitxer | ✅ |
| **E-14** | «una capa que el fitxer no porta no s'ofereix» (`capesPresents`) | ✅ conservat: **5 capes al 837**, no 6 ni 7 — v. §5.3 | ✅ **corregeix el mockup** |
| **E-15** | El motor no opina fins que li ho demanen ([:61](../../frontend/src/pages/TallerPatro.jsx#L61) i [:166](../../frontend/src/pages/TallerPatro.jsx#L166)) | ✅ conservat — v. §5.3 | ✅ **corregeix el mockup** |
| **E-16** | Vocabulari de senyals «+ / o / ⚠» amb el text de taller | ✅ conservat sencer, literal | ✅ |
| **E-17** | «7 parelles rebutjades no es mostren» + `Netejar` | ✅ conservat | ✅ |
| **E-18** | Col·locació guiada àncora per àncora («clica el punt A») | ✅ conservat (bàner de guia) | ✅ |
| **E-19** | Imant: cap marca a ull | ✅ conservat (rètol «l'imant enganxa el cursor al vèrtex») | ✅ |
| **E-20** | Selecció + atenuació de les altres a `opacity 0.25` | ✅ conservat als tres estats | ✅ |
| **E-21** | Barra d'estat amb coordenades i tram sota el cursor | ✅ conservat, i **hi afegeix la llegenda de teclat** (M-12) | ✅ |
| **E-22** | Tolerància acceptable **amb acta**; reobrir mai esborrar-i-crear; l'estat el recalcula el servidor | ✅ conservat a la pestanya contextual (estat 3) | ✅ |
| **E-23** | **`ModelPomList`: Δ fitxa→patró amb xip i semàfor** | ✅ conservat (`44,0→44,3` + `Δ +0,3`) | ✅ |
| **E-24** | `POMPicker` · `SewEditor` · `SegmentEditor` · modal d'esborrat · `ExportModal` | **no dibuixats**: són superfícies efímeres i el mockup no en porta cap | ⚠️ **buit conegut** |

**Recompte: 24 gaps · 11 [estil] · 8 [estructura] · 5 [funcional-NOU]**, més 12 lleis
conservades i **1 buit conegut** (E-24).

### 5.3 🚨 Les cinc desviacions de LLEI que el mockup portava i la maqueta corregeix

No són qüestió d'estil: són lleis escrites al codi o a la NORMA que el mockup contradeia.

1. **Sis capes on el 837 n'ofereix cinc.** El mockup dibuixava `Internes` i `Mirall`. El 837
   **no en porta cap de les dues** (captures `01` i `08`: només Tall · Cosit · Piquets · Fil ·
   Punts), i la llei és explícita: *«un toggle que no fa res és pitjor que no tenir-lo,
   perquè fa pensar que la capa hi és i està amagada»*. **La maqueta n'ofereix cinc.**
2. **Els dos estats del motor, alhora.** El mockup posava *«El motor encara no ha mirat
   aquest patró»* **i** una proposta al 55% a la mateixa targeta. Són mútuament excloents
   (cens §5.1 / §10.4). La maqueta pinta **l'estat "ja ha mirat"**; l'inicial és el de la
   captura `01`, i queda dit aquí.
3. **`--warn-ink` amb un valor que el codi no té** (#a15c0f vs #96500c) → corregit al del codi.
4. **Quatre classes a 9px**, per sota del terra absolut de §2 → totes a 10px.
5. **Radi de targeta i píndola escrits a mà** (12px, 999px) quan `--r-card` i `--r-pill`
   existeixen a `index.css:126-128` → passats a token.

### 5.4 🚨 El daurat ple: el codi ja sap la resposta i no se l'aplica

`TallerPatro.jsx` conté **les dues lectures alhora**, a 300 línies de distància:

- **[:1845-1852](../../frontend/src/pages/TallerPatro.jsx#L1845)** — els xips d'àncora:
  *«"on soc" s'escriu amb `--sel` + filet d'or, **mai amb el daurat ple** —el daurat de fons
  és de CONTROL, i com a tinta de text no arriba a AA (3,16:1 sobre `--sel`)»*, i decideix
  **no fer servir `opacity`** perquè *«apagar text de 10 px el deixava a 2,43:1»*.
- **[:1557](../../frontend/src/pages/TallerPatro.jsx#L1557)** i
  **[:1779](../../frontend/src/pages/TallerPatro.jsx#L1779)** — els botons de mode i de
  mètode: `background: actiu ? 'var(--gold)' : ...` — daurat ple.
- **[PatternViewer.jsx:1128-1134](../../frontend/src/components/pattern/PatternViewer.jsx#L1128)** —
  els commutadors de capa: `opacity: on ? 1 : 0.55`.

**Mesurat**, `--text-main` al 55% sobre `--panel` dona **`#838382` = 3,79:1**: per sota d'AA
per a text de 12px. La lliçó ja és al fitxer; el que falta és aplicar-la (increment I3).

---

## 6 · Increments proposats · ordenats per valor/cost · CAP IMPLEMENTAT

> Cap línia de codi de producte s'ha tocat. Això és una proposta d'ordre, no una feina feta.

### I1 · Cotes de la peça seleccionada per defecte 🥇 *(candidat fixat pel brief)*

| | |
|---|---|
| **què toca** | el `flatMap` que pinta les cotes de **totes** les peces passa a filtrar per la peça seleccionada, amb un commutador de dues posicions («peça seleccionada» / «mostra-les totes») |
| **fitxers** | `components/pattern/PatternViewer.jsx` — [:479-487](../../frontend/src/components/pattern/PatternViewer.jsx#L479) (el filtre) · [:177](../../frontend/src/components/pattern/PatternViewer.jsx#L177) (un estat local més) · `Controls` [:1117](../../frontend/src/components/pattern/PatternViewer.jsx#L1117) (el commutador) · i18n ca/en/es |
| **risc** | **BAIX.** Presentació pura: no toca ni la recepta, ni `valor_mesurat_cm`, ni `cota_offset_mm`. La peça focus **ja existeix** com a concepte ([:466](../../frontend/src/components/pattern/PatternViewer.jsx#L466), l'atenuació) |
| **depèn de** | **res** |
| **per què primer** | `08_proposta_cosit_oberta.png`: 21 etiquetes magenta damunt de 5 peces. És el soroll dominant de la pantalla real i el canvi és d'una vintena de línies |

### I2 · Filtre «només punts semàntics» (R2)

| | |
|---|---|
| **què toca** | `punts` deixa de ser tot-o-res: un segon estat amaga els punts de **corba** i deixa gir + piquets |
| **fitxers** | `PatternViewer.jsx` [:177-180](../../frontend/src/components/pattern/PatternViewer.jsx#L177) · [:470](../../frontend/src/components/pattern/PatternViewer.jsx#L470) (`mostraPunts`) · [:1082-1101](../../frontend/src/components/pattern/PatternViewer.jsx#L1082) (el pintat) · [:1170-1176](../../frontend/src/components/pattern/PatternViewer.jsx#L1170) (el toggle) · i18n |
| **risc** | **BAIX.** Presentació pura |
| **depèn de** | **res** |
| **valor** | llegit a `01_taller_estat_normal.png`, que llista els recomptes per peça: `837.DELANTERO` **984 punts · 56 de gir · 916 de corba**; `837.CUELLO` **1 224 · 20 · 1 196**. El soroll és de 16 a 1 i de 60 a 1 |

### I3 · Conformitat de NORMA de la barra (el daurat ple, l'opacitat i el radi)

| | |
|---|---|
| **què toca** | actiu = `--sel` + `--gold-border` (mai daurat ple) · apagat sense `opacity` · radi 4 → `--r-ctrl` |
| **fitxers** | `TallerPatro.jsx` [:1556-1563](../../frontend/src/pages/TallerPatro.jsx#L1556) · [:1779-1785](../../frontend/src/pages/TallerPatro.jsx#L1779) · [:1807-1813](../../frontend/src/pages/TallerPatro.jsx#L1807) · `PatternViewer.jsx` [:71-76](../../frontend/src/components/pattern/PatternViewer.jsx#L71) · [:1124-1134](../../frontend/src/components/pattern/PatternViewer.jsx#L1124) |
| **risc** | **BAIX-MITJÀ.** Toca 2 fitxers i **quatre famílies de botó** (mode, mètode, opció de mètode, commutador de capa), però **cap comportament**: només estil. Un commit aïllat, com §1b(a) prescriu per als canvis de token |
| **depèn de** | **res** — la lliçó ja és escrita al mateix fitxer ([:1845](../../frontend/src/pages/TallerPatro.jsx#L1845)) |
| **valor** | tanca un deute d'AA **mesurat** (3,79:1) i acaba amb dues gramàtiques de «actiu» a la mateixa pantalla |

### I4 · Capçalera de §8b: tenant al breadcrumb + ← quadrat de 32

| | |
|---|---|
| **fitxers** | `TallerPatro.jsx` [:1895-1946](../../frontend/src/pages/TallerPatro.jsx#L1895) (`Capcalera`) · píndola de versió a `--r-pill` |
| **risc** | **BAIX** |
| **depèn de** | **d'on surt el nom del tenant**: avui `Capcalera` no el rep. Cal saber si ve del context de sessió o del `model` |

### I5 · Llegenda de teclat permanent a la barra d'estat

| | |
|---|---|
| **fitxers** | `PatternViewer.jsx` `BarraEstat` [:1195-1245](../../frontend/src/components/pattern/PatternViewer.jsx#L1195) · i18n |
| **risc** | **BAIX.** Els textos ja existeixen (`pan_hint`, `arc_flip_hint`); el que canvia és que deixin de dependre del gest viu |
| **depèn de** | **res** |
| **nota** | és exactament el patró que `10_fitting_editor.png` ja fa servir a la casa |

### I6 · Columna dreta amb tabs «POMs · Motor» (correcció 2 d'Agus)

| | |
|---|---|
| **què toca** | l'`<aside>` esquerre de 360 baixa a 312 i **perd dos `Contenidor`**; neix un `<aside>` dret de 288 amb tabs de secció; `ModelPomList` hi va sencer; `RelationsPanel` **s'ha de partir** |
| **fitxers** | `TallerPatro.jsx` [:1279-1340](../../frontend/src/pages/TallerPatro.jsx#L1279) · `RelationsPanel.jsx` (911 línies) · un component nou de tabs |
| **risc** | **MITJÀ-ALT.** `RelationsPanel` barreja **propostes de costura, propostes de pinça, costures declarades i trams** en un sol panell amb accions de bloc |
| **depèn de** | **una decisió de domini no presa**: quines seccions van a «Motor» (el que el motor OPINA) i quines a la contextual (el que ja està DECLARAT). La maqueta proposa el tall, però és una proposta |

### I7 · Pestanyes de procés + capes a «Visualitzar» (correcció 1 d'Agus)

| | |
|---|---|
| **què toca** | la barra plana es parteix en 6 pestanyes amb la seva fila de comandos; `contenidorEines` apunta a la `cmdrow` de «Visualitzar» |
| **fitxers** | `TallerPatro.jsx` `BarraEines` [:1555-1632](../../frontend/src/pages/TallerPatro.jsx#L1555) i `SelectorMetode` [:1755](../../frontend/src/pages/TallerPatro.jsx#L1755) · `PatternViewer.jsx` (només el destí del portal) |
| **risc** | **MITJÀ.** El portal ja hi és i no s'ha de tocar. El risc real és **el mapa**: els 5 modes (`view · pom · seg · pinca · sew`) s'han de repartir entre «Declarar», «Cotes» i «Cosir», i **«Fitxer» i «Organitzar» no tenen contingut definit** al mockup |
| **depèn de** | **ratificació d'Agus del mapa mode→pestanya**, i de la conseqüència del dubte D-1 |

### I8 · Arbre del patró + panell de característiques

| | |
|---|---|
| **fitxers** | dos components nous; `PieceList.jsx` hi queda a dins; part de `PieceIdentityList.jsx` |
| **risc** | **MITJÀ-ALT** |
| **depèn de** | ⚖ **la convenció de RECORREGUT** (no ratificada): què passa en clicar un tram o una costura de l'arbre, i si la selecció de l'arbre és **la mateixa** que la del llenç. Sense això, l'arbre és decoració. També dels 3 camps **[NOU-BD]** de §4 — però **només de 3 dels 11** |

### I9 · Mesura lliure en mm · sentit relatiu · origen fix · driving/reference

| | |
|---|---|
| **risc** | **ALT** |
| **depèn de** | **columnes noves i vocabulari de servidor**. La mesura lliure, a més, xoca de cara amb la llei *«el VALOR no s'envia mai: s'envia la recepta»* — una mesura lliure en mm **és una recepta d'una mena que encara no existeix**, no un valor teclejat. Cal dissenyar-la abans de construir-la |

---

## 7 · ⚖ Dubtes per a Agus (curts, amb la meva recomanació)

**D-1 · Amb les capes dins de «Visualitzar», des de «Cotes» o «Cosir» no s'hi arriba.**
Avui la barra és una i les té sempre a mà. La teva correcció mana i està aplicada.
→ **La meva recomanació:** deixar-ho tal com has dit i mesurar-ho amb ús real abans de
tocar-hi res. Si molesta, la sortida barata **no és tornar-les a la dreta** sinó que
«Visualitzar» sigui **la pestanya per defecte en obrir**, perquè el primer gest del taller és
mirar. No he afegit cap accés ràpid al llenç: seria un component que el mockup no porta.

**D-2 · «Segment de guia» surt marcat `[NOU]`, però el mode `seg` («Definir tram») ja existeix
i el cens el dona per FET** (R5b: trams `auto`/`natural`/`declarat` + tecla d'invertir l'arc).
→ **La meva recomanació:** són **dues coses diferents** i el nom les confon. Un *tram
declarat* entra al vocabulari de **costura** (el motor l'usa per casar vores); un *segment de
guia* seria una línia **auxiliar només per mesurar**, que no ha d'aparèixer com a candidata a
cap costura. Si és això, el `[NOU]` és correcte i el que falta és **el nom**. Si no ho és, el
comando sobra perquè ja hi és. **No ho he resolt jo**: està anotat dins de la maqueta.

**D-3 · La capçalera de `Contenidor` és FOSCA al codi i BLANCA a la maqueta.**
La fosca té motiu escrit («un títol que pesa el mateix que el seu contingut no separa res»,
QA-TALLER E · T1); la blanca és el que diuen NORMA §1 i el teu mockup.
→ **La meva recomanació:** **blanca**, com al mockup. Amb l'arbre i les pestanyes, la
separació ja la fan l'estructura i el filet; sis franges negres en una pantalla plena de
dibuix pesen més que el dibuix. Però és una decisió teva perquè revoca una acta anterior.

**D-4 · `--fs-h3` val 14px al codi i NORMA §2 diu «h3 15/20».**
→ **La meva recomanació:** **que la NORMA baixi a 14** i no al revés. 15px no és cap graó de
l'escala d'`index.css` (10·12·14·18·22·32), el codi ja porta 14 a tot arreu, i §2 ja bateja
el 14 per a la «capçalera de TALLA». No urgeix: aquesta maqueta no fa servir cap h3.

**D-5 · Els estats 1 i 3 no tenen cap acció blava.**
És conseqüència directa de les pestanyes de secció: el blau del motor viu a «Motor».
→ **La meva recomanació:** **està bé així** — §6 diu «el flux els serialitza, mai dos blaus»,
i §8c admet zero primària. Ho poso perquè és un canvi visible respecte del mockup, on el CTA
taronja i el blau es veien alhora.

**D-6 · Falten les superfícies efímeres** (E-24): `POMPicker`, `SewEditor`, `SegmentEditor`,
el modal de confirmació d'esborrat i `ExportModal`.
→ **La meva recomanació:** **no dibuixar-les fins que l'estructura estigui ratificada.** El
mockup no en porta cap, i «adaptar ≠ redissenyar». Quan I6/I7 tinguin llum verda, mereixen
una maqueta pròpia — sobretot el `POMPicker`, que és el que decideix si el mode POM sense
`pomActiu` segueix tenint sentit amb pestanyes.

---

## 8 · Rastre

| què | com |
|---|---|
| conformitat NORMA | `norma_check.py` sobre el fitxer final · **0 incompliments** de 122 espaiats + 28 interlineats + 3 icones + 4 badges |
| contrast | `contrast.py` · 28 parelles, ràtios WCAG computats |
| mockup vs maqueta | `mesura_mockup.py` · **70 → 0** desviacions |
| render i mesura al DOM | Chromium headless 1600×1000, `file://` local, sobre les 3 tramades |
| codi viu | lectura de `index.css` (209) · `TallerPatro.jsx` (1 967) · `components/pattern/*` (5 414) · `components/ui/Contenidor.jsx` · `patterns/models.py` |
| pantalla real | les 10 captures de `captures_ui_taller_2026-08-25/` (llegides `01` i `08`) |
| scripts | tots al **scratchpad**, cap al repo |

**Cap servei tocat · cap test executat · cap escriptura a BD · cap codi de producte
modificat · res commitat.**
