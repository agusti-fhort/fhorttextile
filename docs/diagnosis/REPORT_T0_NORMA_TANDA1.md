# REPORT T0 · NORMA UI TANDA 1 (S38) — FONAMENT CONSTRUÏT · 🛑 STOP de tram

**Data:** 08/08/2026 · **Branca:** dev · **Commits:** 131 · 132 · 133 · 134 · **CAP PUSH**
**Punt de partida:** `c6b74704` → **HEAD `8922bd04`**

T0 està fet sencer (T0.1 · T0.2 · T0.3). Cap pantalla s'ha tocat, que era la condició del tram.
Aquest document substitueix el report d'aturada del PAS 0: les 6 troballes van quedar resoltes
per `NORMA_LAYOUT.md §1b` i la seva execució es detalla aquí.

---

## 1 · Commits i fitxers tocats

| # | Commit | Fitxers |
|---|---|---|
| 131 | `8e15f195` semàfor alineat a la norma (**aïllat**) | `frontend/src/index.css` |
| 132 | `85d6ff7c` tokens de la norma (llista tancada) | `frontend/src/index.css` |
| 133 | `820556e1` `<PageMenu>` | `frontend/src/components/ui/PageMenu.jsx` (nou) |
| 134 | `8922bd04` breadcrumb de la top bar | `Topbar.jsx` · `Sidebar.jsx` · `navGroups.js` (nou) |
| 135 | `185575ae` aquest report | `docs/diagnosis/REPORT_T0_NORMA_TANDA1.md` |

El 131 va aïllat perquè l'ordre ho demanava: són 348 usos en 75 fitxers i ha de poder revertir-se sol.

---

## 2 · T0.1 · Tokens

### (a) Semàfor — la norma mana, el codi s'hi adapta

| Token | Abans | Ara | AA (mesurat) |
|---|---|---|---|
| `--ok` | `#3b6d11` | `#2e7d32` | 5.13:1 s/blanc — **coincideix exacte amb el que diu la norma** |
| `--ok-bg` | `#eaf3de` | `#e9f3ea` | — |
| `--err` | `#a32d2d` | `#b42318` | 6.57:1 s/blanc (la norma diu 6.63; diferència d'arrodoniment) |
| `--err-bg` | `#fcebeb` | `#fbebe9` | — |

**Àlies revisats, com demanava l'ordre.** `--gate`, `--gate-bg` i `--placed-bg` són literalment
`var(--ok)`/`var(--ok-bg)`: segueixen el canvi sols. Verificat **al navegador**, no al fitxer —
els tres resolen a `#2e7d32`/`#e9f3ea` i mantenen la lectura «positiu confirmat». No calia tocar-los.

### (b) Tokens nous (llista tancada, res més)

`--accio #2b65c2` · `--accio-hover #245399` · `--panel #ffffff` · `--sel #f7f5f2` ·
`--line #e8e5e0` · `--line-soft #f0eeea` · `--text-soft #6e6a64` · `--text-faint #98938b` ·
`--warn-state #ff9942` · `--warn-state-bg #ffedd9` · **`--warn-ink #96500c`** · `--col-talla 60px`

Verificat al navegador que **els 19 tokens** (nous + intocables) resolen al valor esperat.

### (c) `--warn-ink`: hex final i ràtio mesurat

**`#96500c` sobre `#ffedd9` = 5.32:1** → passa AA **sense haver d'enfosquir**. El punt de partida
que vas donar ja complia; no s'ha mogut ni un dígit. La forma del badge es manté exacta:
`background: var(--warn-state-bg)` · `color: var(--warn-ink)` · `border: 1px solid var(--warn-state)`.

### (d) `--text-muted`: l'hex real que demanaves

**`#868685`** — **3.64:1 sobre blanc, per sota d'AA.** Dades per a la decisió futura:

| | ràtio s/blanc | distància RGB des de `--text-muted` |
|---|---|---|
| `--text-soft #6e6a64` | 5.37:1 | 49 |
| `--text-faint #98938b` | 3.05:1 | 23 |

**Van en direccions oposades.** Pel color s'assembla més a `--text-faint`; per contrast, l'únic
que el posa en norma és `--text-soft`. Mapar-lo a `faint` empitjoraria 849 usos en 138 fitxers.
Queda viu i DEPRECAT amb comentari, sense aliar, tal com vas ordenar.

`--border` també queda viu i deprecat amb comentari (432 usos en 93 fitxers), migració per pantalla.

---

## 3 · T0.2 · `<PageMenu>`

`frontend/src/components/ui/PageMenu.jsx`. Cap pantalla el consumeix encara.
Props: `backTo` (**obligatori**), `backTitle`, `items[]`, `children`, `rightChildren`.

Mesurat al navegador contra el canònic (valors computats, no a ull):

| | Norma / canònic | Mesurat |
|---|---|---|
| Barra | blanca, filet 1px `--line` a dalt i a baix | `#fff` · `1px rgb(232,229,224)` ✅ |
| Fletxa | 32×32, icona 16, vora `--line`, radi control | 32×32 · radi 6 · vora `rgb(232,229,224)` ✅ |
| Píndola repòs | `--text-soft`, sense fons ni vora | `rgb(110,106,100)` · fons transparent ✅ |
| Píndola activa | `--sel` + vora `--gold-border` + pes 600 | `rgb(247,245,242)` · `rgb(224,200,160)` · 600 ✅ |
| Píndola | radi 999, padding 6/14 | `999px` · `6px 14px` ✅ |
| Sense seccions | només la fletxa | ✅ (ni separador ni buit) |

Pàgina de prova temporal creada, fotografiada i **esborrada**; `App.jsx` verificat net (`git diff` buit).

---

## 4 · T0.3 · Breadcrumb

`Topbar.jsx` tenia un `PATH_TO_KEY` propi amb **11 de les 58 rutes** del router. Fora d'aquelles
onze el rètol requeia a `t('app.title')` i, com que el primer element ja era `t('app.title')`, el
breadcrumb es llegia **«Fhort Textile Tech › Fhort Textile Tech»** — es veu a qualsevol captura
d'un model d'abans d'avui.

La navegació surt de `Sidebar.jsx` a un mòdul propi **`navGroups.js`** que ara comparteixen el menú
lateral i el breadcrumb: amb dues llistes, el molla i el ressaltat del menú acabarien contradient-se.
Mòdul propi i no `export` des del component perquè exportar una constant d'un fitxer de component
trenca el fast-refresh de Vite — l'avís va sortir al primer intent i està corregit.

Primer element = **nom del TENANT** (`store.tenant.nom`, la casa i no la persona). Mentre `/me` no
ha respost es diu el nom del producte, que és el que deia abans.

**Verificat a 11 rutes × 3 idiomes:** cap duplicació, cap ruta sense rètol, tot traduït.
La dreta de la top bar **no s'ha tocat**.

---

## 5 · Verificació

| Control | Resultat |
|---|---|
| `npm run build` | ✅ verd a cada commit |
| `eslint` (global) | **1254 problems (991 errors, 263 warnings)** — **idèntic a la línia base**: delta 0 |
| Tokens al navegador | ✅ 19/19 al valor esperat |
| Breadcrumb | ✅ 11 rutes × ca/en/es |
| PageMenu | ✅ 6/6 mesures contra el canònic |
| i18n gate | ✅ **cap clau nova**: `PageMenu` no porta cap literal (les etiquetes arriben traduïdes de qui el crida) i el breadcrumb reutilitza les `nav.*` existents |

⚠️ **Cap veredicte de guardia-ui**, per ordre teva: la còpia bona encara no hi és (§7).
El lint global ja era vermell abans de T0 i segueix igual; cap error és meu.

---

## 6 · Captures — `ops/qa/captures/`

| Fitxer | Què és |
|---|---|
| `t0_abans_dashboard.png` / `t0_despres_dashboard.png` | Dashboard del model 1308 — 4 elements amb semàfor |
| `t0_abans_patro.png` / `t0_despres_patro.png` | Tab Patró — 1 element amb `--err` |
| `t0_taulell_semafor.png` | Els 4 tokens en forma de badge, abans i després |
| `t0_pagemenu_repos.png` / `t0_pagemenu_hover.png` | PageMenu: amb seccions + porta, i sense seccions |

**Dues pantalles reals i un taulell, no tres pantalles — i cal dir per què.** Vaig escriure una
sonda que compta els elements realment pintats amb el semàfor i vaig escanejar **16 rutes**: només
en surt a aquestes dues. `fhort` té **0 models** (V4, 06/08), o sigui que les llistes surten buides,
i el panell més dens en semàfor (`ComprovacioPanel`: 3 usos de `--ok`, 6 de `--err`) demana
`/models/{id}/comprovacio/`, que no es pot generar sense model viu. El taulell hi és perquè el
vermell no apareix a cap pantalla poblada i el canvi s'ha de poder ratificar igualment.

L'abans i el després surten del **mateix bundle**, amb els 4 hex vells reinjectats per CSS: així
l'única diferència entre les dues fotos són els 4 valors. No s'ha reconstruït dos cops perquè aquí
**construir és desplegar** (nginx serveix `frontend/dist`), i `git stash` està prohibit.

**Dos falsos positius meus, resolts, per si tornen:** (1) el primer joc de captures va sortir tot
daurat i no provava res — d'aquí la sonda; (2) la fletxa ← «no es veia» perquè el harness servia
la fulla de `@tabler/icons-webfont` (CDN) des de `dist`: no faltava la icona, faltava la font.

---

## 7 · 🛑 Punts oberts — necessiten decisió teva

**(1) El TERCER segment del breadcrumb — bloqueja T2.**
Els dos canònics no diuen el mateix per a una pantalla d'entitat:
`PROPOSTA_menu_pantalla_v3` posa «… › Models › **Dashboard**» i `PROPOSTA_resum_wizard_partit`
posa «… › Models › **TOLEDO**». La regla escrita («Tenant › secció › pantalla») no ho desempata.
Avui el breadcrumb mostra **dos segments a tot arreu** i espera ordre. La norma mateixa mana
aturar-se en aquest cas (§1b, jerarquia de fonts).

**(2) `--fs-caption` són 8px i la norma diu que mai — bloqueja T1.**
`index.css` té `--fs-caption: 8px`. La norma §2 diu **«caption/TH — 10/12, MÍNIM ABSOLUT, mai 8px
llegible»**. T1 demana l'etiqueta «models» en caption i th a 10: amb el token actual sortiria a 8px
i incompliria. Fora de la llista tancada de T0, així que no l'he tocat. ¿`--fs-caption` puja a 10px
(i què passa amb el terra de 8pt de la fitxa tècnica, que és d'on venia), o T1 fa servir `--fs-label`?

**(3) L'acció primària de `buttons.js` encara és daurada.**
`primaryBtn` pinta `--gold` amb tinta `--text-main` (el fix AA de S37). La norma §5 diu que la
primària és `--accio` blau. No he tocat res —no era del tram— però T1 i T3 hi xocaran de cara.
¿La conformitat de cada pantalla se l'endú, o `primaryBtn` es reescriu d'un cop?

**(4) `--bg-page` no era un token nou.** Ja existia a `#fafafa` des de S37, posat expressament
com a provisional («el mateix valor que `--bg-card` per no introduir cap salt visual»). Era a la
teva llista tancada amb `#fbfaf8`, així que l'he portat al valor de norma: **toca 7 usos en 5
fitxers** (`App.jsx`, `Entrar.jsx`, `TallerPatro.jsx` ×2, `TechSheetEditor.jsx`). Ho reporto perquè
el supòsit de partida era que s'afegia, no que se substituïa.

**(5) `guardia-ui.md`: la ruta que demanaves.**
`/var/www/ftt-staging/.claude/agents/guardia-ui.md`
(n'hi ha una segona còpia, també vella, a `/root/hotfix-work/tree/.claude/agents/guardia-ui.md`).
No l'he tocat i no he corregut cap verificació de guardia.

**(6) `--r-ctrl` no és a la llista tancada.** La norma §3 el bateja (radi de control 6px) però no
era a la llista, així que `PageMenu` fa servir el literal `6`, com la resta de la casa. Si el vols
com a token, entra al tram següent.

**(7) Menor, sense impacte:** a `NORMA_LAYOUT.md` falta la capçalera del **§2** — les regles de
tipografia comencen a la línia 49 penjant del §1b. Les regles s'entenen igual; és de format.

---

## 8 · Conducta afegida

**Cap.** T0 no dibuixa cap pantalla: són tokens i dos components de sistema sense estats asíncrons.
`PageMenu` no fa cap petició, no té loading ni error, i no decideix cap permís.

## 9 · PROVISIONAL-DOMINI

**Cap a T0.** (El commutador «en curs / acabats» de T1 en portarà un: el criteri d'«acabat» no
existeix al domini.)

---

## 10 · STOP

T0 tancat i verificat. **Espero validació a pantalla real** i resposta als 3 punts que bloquegen
(1 · breadcrumb → T2 · 2 · caption → T1 · 3 · primària daurada → T1/T3).
Amb el punt 2 resolt, T1 arrenca sense cap més consulta.
