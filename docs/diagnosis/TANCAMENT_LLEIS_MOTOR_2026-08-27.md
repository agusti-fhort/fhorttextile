# TANCAMENT DE LLEIS DEL MOTOR — F6.1→F6.3 al ledger

**Data:** 2026-08-27 · **Patró:** B només-documentació · **Ratificació:** el llançament del brief
per part de l'Agus **és** l'acte formal per a totes les lleis que conté.
**Ledger tocat:** `/var/www/ftt-staging/DECISIONS.md` (viu, 1.540 → 1.625 línies)
**Reports font:** [`REPORT_F61_SOLVER_2026-08-27.md`](REPORT_F61_SOLVER_2026-08-27.md) ·
[`REPORT_F62_SOLVER_2026-08-27.md`](REPORT_F62_SOLVER_2026-08-27.md) ·
[`REPORT_F63_RUL_2026-08-27.md`](REPORT_F63_RUL_2026-08-27.md) (i la seva CODA)

> **Fronteres.** Cap codi, cap test, cap restart, cap BD. `DECISIONS.md` **NO es commita** —
> CLAUDE.md ho prohibeix i el fitxer viu al servidor com a memòria de treball; aquest informe sí.
> Cap push.

---

## 1 · 🚨 La numeració no era la que el brief donava per feta

El brief proposava **D-INV-8/9/10/11**. Verificat abans d'escriure res, i **8 i 9 ja estaven
ocupats**:

| | ocupat per | on |
|---|---|---|
| D-INV-8 | HPS és derivable del graf (2.371/2.371) | `docs/ordres/TANCAMENT_SESSIO_2026-08-25_MOTOR.md` |
| D-INV-9 | Davant/darrere: fora de la forma | mateix fitxer |

🚨 **I la sèrie no vivia al ledger.** `DECISIONS.md` no conté ni una sola cadena `D-INV`: el
registre D-INV-1..9 viu en un **tancament de sessió** sota `docs/ordres/` (S46-MOTOR, 25/08). El
brief deia «escriure al ledger DECISIONS.md» i la numeració havia de sortir d'un altre fitxer, cosa
que només es podia saber mirant-ho.

### Mapa de renumeració

| brief | assignat | llei |
|---|---|---|
| D-INV-8 | **D-INV-10** | Criteri de caràcter del motor de grading |
| D-INV-9 | **D-INV-11** | Les mesures d'arc són restriccions condicionals |
| D-INV-10 | **D-INV-12** | Propagació per costures + consentiment |
| D-INV-11 | **D-INV-13** | Reconciliació bidireccional per tolerància |
| L5 (sense número) | *esmena amb nom* | Esmena a la CONVENCIÓ-1 del banc |
| L6 (sense número) | *llei amb nom* | Llei operativa de banc — «l'escala era el bug» |

L5 i L6 s'han escrit com a **lleis amb nom i sense número**, que és com el brief les donava i com
el ledger escriu la majoria de les seves. Si l'Agus les vol numerades, són D-INV-14 i D-INV-15.

🚩 **Efecte lateral: el registre queda amb DOS domicilis.** D-INV-1..9 a `docs/ordres/`, D-INV-10..13
a `DECISIONS.md`. S'ha escrit un avís al capdamunt del bloc nou perquè ningú no torni a comptar
malament, però **consolidar-lo no s'ha fet d'ofici** — portar 1-9 al ledger, o deixar-hi només un
punter, és decisió de l'Agus.

🚩 **I una correcció al REPORT_F63.** El seu §6 proposava «D-INV-8» sense comprovar-ho. S'hi ha
posat el número bo i una nota que diu què va passar, en comptes de reescriure-ho en silenci.

## 2 · Què s'ha escrit, i on

Un bloc datat nou al capdamunt de `DECISIONS.md`, que és com el ledger ordena les sessions (S24,
S22, S21… en ordre invers), amb l'estil que ja hi és: `**LLEI — TÍTOL EN MAJÚSCULES.**` + prosa +
corol·laris amb guionets + evidència en cursiva.

| llei | resum d'una línia | evidència ancorada |
|---|---|---|
| **D-INV-10** | Amb RUL, reproduir el RUL (0,0073 mm / 7.376 punts, terra 0,0071) · sense RUL, el CONTRACTE ≤0,1 mm és el gate · **el 0,5 mm/vèrtex es RETIRA** | REPORT_F63 §0, §5, §6 |
| **D-INV-11** | L'arc mana si hi ha marge; si es contradiu, **es descarta sencer** i passa a control. Jerarquia FIXED > distància > arc. Àrbitre: la diagnosi QR (D-INV-2) | REPORT_F63 §C2 + PLA del vault |
| **D-INV-12** | El delta viatja pel graf de costures; l'embegut passa a quantitat governada; topar amb un objectiu declarat **avisa amb el número i demana consentiment**; el trade-off es registra | conversa Agus 27/08 (PLA) |
| **D-INV-13** | La discrepància fitxa↔patró és una **decisió**, oferta en les dues direccions, **només fora de la tolerància declarada**. Consentiment + rastre. El patronista mana | REPORT_F63 CODA §C2 |
| *esmena* | CONVENCIÓ-1: l'origen es calcula al **tall**; el cosit l'hereta **per proximitat** (l'argmin propi erra a la TAPETA) | REPORT_F61 + `parity_837.json` → `meta.convencio_1` |
| *llei de banc* | **«L'escala era el bug»**: peces de prova a escala real (~2.000 mm); un verd a 400 mm d'un defecte que mossega a 2.000 és un test mentider | REPORT_F61 + docstring de `big_square()` |

## 3 · ✅ Una pregunta oberta del ledger que aquestes lleis tanquen

`DECISIONS.md` portava des del **21/07** un «**Tema aparcat amb nom — RUL com a font de graduació**»
amb tres preguntes obertes. Una era literalment:

> «qui mana si RUL i fitxa discrepen (un RUL és matemàticament exacte — podria merèixer MÉS
> precedència)?»

**La resposta d'Agus d'avui és «MANA EL PATRÓ»**, i D-INV-10 i D-INV-13 la formalitzen. S'ha
**anotat** el paràgraf aparcat amb un punter a les dues lleis — **sense reescriure'l ni esborrar-lo**:
el text original és el registre del que es va pensar el 21/07 i no és nostre de retocar. Les altres
dues preguntes (crea ruleset nou o alimenta l'assignat? és peça del meló GTI?) **segueixen obertes**,
i s'hi ha deixat dit que el camí de codi RUL→`GradingRuleSet` que aquell paràgraf demanava
**segueix sense existir**.

⚠️ **Això no és una fusió de lleis duplicades** —el brief demanava proposar-ne una si n'hi havia— sinó
el tancament d'una pregunta. No s'ha trobat cap llei del ledger que digui el mateix que aquestes
sis amb altra redacció: `CONVENCIÓ-1`, `sisa`, `arc`, `escala real`, `SeamPair`, `embegut`,
`consentiment` i `tolerància declarada` no hi surten enlloc.

## 4 · El que NO s'ha escrit com a llei

Per instrucció del brief, són **horitzó i no doctrina**, i el ledger no té secció d'horitzó, així que
queden aquí anotats i **fora** de `DECISIONS.md`:

- l'sprint de la **mesura d'arc** (D-INV-11 la declara; implementar-la és feina, no llei);
- **l'embegut com a feature** de producte;
- la **targeta de reconciliació** a producte (la UI de D-INV-13).

## 5 · Diff resumit

```
 DECISIONS.md | 86 +++++++++++++++++++++++++++++++++++++++++++++++++++++-
                1 línia substituïda (la capçalera «Última actualització»)
               85 línies afegides   (bloc nou de lleis + anotació del tema aparcat)
```

Purament additiu tret de la capçalera de data, verificat per `diff` contra una còpia presa abans
d'editar. `DECISIONS.md` es queda **sense commitar** (CLAUDE.md), i ja portava una modificació d'una
altra sessió que **no s'ha tocat ni revertit**.

## 6 · Queda obert

| | |
|---|---|
| 🚩 **Consolidar el registre D-INV** | Dos domicilis. Decisió d'Agus. |
| 🚩 **Numerar L5 i L6?** | Avui són lleis amb nom. Serien D-INV-14 i D-INV-15. |
| ⏳ **Segellar la GV v10** | De la CODA F6, encara pendent: el banc segueix apuntant a la 201/v9. |
| 🚩 **S/S2: el PAS, no l'origen** | D-INV-11 li dona el marc; la discrepància mesurada segueix oberta. |
| 🚩 **El vermell del catàleg de rols** | `33 != 30`, anterior a l'sprint (REPORT_F63 §C7). Fix d'una línia, de qui té el catàleg. |
