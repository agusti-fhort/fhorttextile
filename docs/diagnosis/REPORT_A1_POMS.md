# REPORT A1 · /poms · Catàleg de POMs — 🛑 STOP: la maqueta no és construïble sencera

**Data:** 08/08/2026 · **Commits:** 142 (breadcrumb, transversal) · 143 (pell d'A1) · **CAP PUSH**
**HEAD:** `c4c35e62` · **Font:** `maqueta_cataleg_poms_v3.html` + `NORMA_LAYOUT.md`

La **pell està feta i verificada**. El **bastiment §8b i la fitxa** queden aturats: la maqueta
demana coses que el domini no té i altres que són funcionalitat nova sense dibuixar.

---

## 1 · Fet — commit 143 (només pell, cap lògica)

Cap crida, cap handler i cap secció canvien. **Zero tokens deprecats al fitxer** (verificat: 0
ocurrències de `--border`, `--bg-card`, `--bg-muted`, `--gray`, `--gold-pale`, `--text-muted`).

- Superfícies a `--panel`: capçaleres de panell i peu deixen de ser crema (§1)
- Selecció `--gold-pale` → **`--sel` + filet d'or** (§1)
- Categoria = **th 10px MAJÚSCULES tracking .08em**, ja no daurada (§8e)
- **Els tres badges amb filet del seu color** (§1, esmena Agus). El de revisió passa a
  `--warn-ink`: **1.86:1 → 5.32:1**
- IDENTITAT §8b.3 sobre el fons: comptador-selecció + etiqueta + descripció; el títol h2 se'n va
- «Desactivar» → terciària (§5.4); **cap blau a la pantalla**, correcte per §8c (consulta)

## 2 · Verificació bidireccional

**(a) maqueta → pantalla.** Tot el que la maqueta dibuixa i el domini permet, hi és.
**No hi és** (v. bloquejos): PageMenu §8b · «＋ Nou POM» · «Editar» · «Instàncies admeses» ·
«Capes on té sentit».

**(b) pantalla → maqueta** — el que la pantalla té i la maqueta NO:

| A la pantalla | Veredicte |
|---|---|
| Secció **«Capes i instàncies · ÚS OBSERVAT»** | **No és invenció**: és una decisió ratificada teva del 07/08 que substitueix les dues seccions declaratives de la maqueta. V. bloqueig B1 |
| **5** comptadors d'ús (items, famílies, grups, models, regles) vs **3** a la maqueta | La pantalla en sap més que la maqueta. Es queden; es llista aquí |
| Avís de **cascada** (`us.cascada`) | Conducta afegida: diu quantes files cauen si s'esborra |
| Nota del peu redactada pel **backend** (`us.motiu`) | Conducta afegida: el motiu el sap qui compta |
| `window.confirm` abans d'esborrar | Conducta afegida (§9: confirmació destructiva) |
| Caixa d'error + estats de càrrega | Estat asíncron, bastiment de la casa |

---

## 3 · 🛑 Bloquejos

### B1 · La maqueta demana dues seccions que el model no té — i que ja vas substituir

`maqueta_cataleg_poms_v3` dibuixa **«Instàncies admeses»** (Posició/Estat) i **«Capes on té
sentit»** com a **política declarada**, amb llistes de tags marcats/no marcats.

- **`POMMaster` no té cap camp per a això.** Verificat al backend; i
  `backend/fhort/pom/models.py:1503-1505` diu que és **deliberat**: donar-li aquests eixos
  «voldria dir demanar que es declari» el que no es vol declarar.
- La pantalla ja porta al seu lloc **«Ús observat»**, amb el comentari que ho ancora:
  *«ÚS OBSERVAT, no política declarada (decisió Agus 07/08). El model no té enlloc quines
  capes admet aquest POM; això és el que es fa servir DE DEBÒ.»*
- La v3 es declara a si mateixa **«estructura = v1 aprovada · pell = NORMA v1»**: la seva
  estructura és de la v1 i és **anterior** a la teva decisió del 07/08.

**Seguir la maqueta al peu de la lletra revertiria una decisió ratificada.** No ho faig.
**Recomanació:** que mani la decisió del 07/08 i que la maqueta s'esmeni; la pantalla ja hi és.

### B2 · «＋ Nou POM» i «Editar» són funcionalitat nova, no pell

Avui la pantalla **no té ni crear ni editar**. L'API sí (`poms.crearTenant`, `poms.update`),
però **la maqueta dibuixa els botons i cap formulari**: no diu quins camps, quins són
obligatoris, ni com es tria categoria, unitat o scope. Construir-los no és conformitat.

**Pregunta:** ¿entren a A1 —i amb quin formulari— o queden fora i el menú porta només el que ja existeix?

### B3 · La maqueta es contradiu: dues portes per a la mateixa acció

Porta **«Nou POM ▾» al PageMenu** *i* **«＋ Nou POM» blau** a la capçalera del panell, i la seva
nota diu «＋ Nou POM és l'únic blau de la pantalla». Però **§8e** diu que en una llista l'acció
primària **puja al menú i deixa de ser blava**.

**Pregunta:** ¿una sola porta al menú (§8e) o el blau al panell (maqueta)? Sense això no puc
muntar el PageMenu, perquè els seus tres ítems (`Nou POM ▾` · `Accions ▾` · `Filtres`) depenen
d'aquesta resposta i cap dels tres té contingut dibuixat.

---

## 4 · 🚩 Dos defectes anteriors, destapats per la captura amb dades reals

**(1) La llista només ensenya 200 dels 396 POMs.** L'API declara `count: 396`, en retorna
**200** (el servidor capa `page_size`) i deixa un `next` que ningú demana. El comptador diu
«200 POMs» i és **fals**: n'hi ha 396. **196 POMs són invisibles al catàleg**, en silenci.

**(2) Les categories es fragmenten.** 18 categories distintes es pinten en **131 blocs**, perquè
s'agrupa respectant l'ordre de la llista i l'ordre demanat és `codi_client`. A la captura es veu
«PART SUPERIOR DEL COS · 1» repetit una vegada i una altra. La maqueta les vol agrupades un cop.

Tots dos són **lògica**, no pell, i no els he tocat. El (1) em sembla prou greu per fer-lo abans
que A1 es doni per bo: una pantalla de catàleg que amaga la meitat del catàleg no és conforme
per molt ben vestida que estigui.

## 5 · 🚩 Menor

El menú lateral i el breadcrumb diuen **«POM Systems»**; el títol i la maqueta diuen **«Catàleg
de POMs»**. La memòria de la casa ja diu que «POM System» no és cap model, sinó un rètol vell.
¿S'unifica a «Catàleg de POMs» a `nav.poms_list`?

---

## 6 · Verificació

| Control | Resultat |
|---|---|
| `npm run build` | ✅ verd |
| `eslint` global | 1254 problems — **idèntic a la línia base, delta 0** |
| Tokens deprecats al fitxer | ✅ 0 |
| i18n | ✅ cap clau nova, cap literal nou |
| Breadcrumb 3 segments | ✅ 11 rutes × 3 idiomes |

**Captura:** `ops/qa/captures/a1_poms_despres.png`, amb **dades reals** (396 POMs de `fhort`).
Staging té basic-auth a nginx i el navegador no hi entra, així que el fixture es genera **en
procés** amb `APIClient` (`ops/qa/qa_a1_poms_fixture.py`), com fa la resta de QA de la casa.

## 7 · 🛑 STOP

Responent B1, B2 i B3 tanco A1 seguit. El defecte (1) del §4 el faria abans de passar a A2.
