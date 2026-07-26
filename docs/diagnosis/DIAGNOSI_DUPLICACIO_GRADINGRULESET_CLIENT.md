# DIAGNOSI — Duplicació de GradingRuleSet de client (115 vs 116): reutilització inexistent o fallida?

> **Data:** 2026-07-16 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`
> **Abast:** dir per què el ruleset **116** (import-fitxa del model 269) es va crear en comptes de reutilitzar
> el **115** (creat a l'S10 per al model 268), si són bessons, si el patró és sistèmic, i on inseriria la
> reutilització. **Bloquejant abans de la Fase B.** Cap proposta d'implementació.
> **Convenció:** cada fet porta `fitxer:línia`. **"NO EXISTEIX" = confirmat absent al codi.** Xifres = `SELECT`
> real sobre `fhort` (tenant id=2). Propostes marcades `💡 PROPOSTA (a validar)` — decisió Agus (Patró C).

---

## RESUM EXECUTIU

1. **La lògica de reutilització SÍ EXISTEIX** (`grading_utils.py:312-351`, "anti-proliferació 1D"):
   `derive_grading_rule_set` busca un ruleset existent ABANS de crear-ne un de nou. Per tant la hipòtesi
   "s'ha creat automàticament EN COMPTES de coordinar-se" és **parcialment falsa**: el camí SÍ intenta
   coordinar-se, però **el filtre no va poder veure el 115**.
2. **Per què no va trobar el 115: tres motius acumulats, el primer decisiu.** (a) El filtre exigeix
   `construction/fit_type/garment_group` **iguals** (`:316-319`); el 115 els té **NULL** i l'import 116 els
   va derivar WOVEN/REGULAR/7 → el 115 **queda fora del `filter()` d'entrada**. (b) Encara que hi entrés,
   el conjunt de `pom_id` difereix (34 vs 25) → falla la igualtat estricta (`:324`). (c) La representació
   difereix (115 = forma canònica `increment_base/break`, valors_step NULL; 116 = `valors_step` de
   `detect_grading`) → falla la comparació regla-a-regla (`:333-341`).
3. **NO són bessons estrictes.** Solapament **Jaccard 55%** (21 pom compartits · 13 només-115 · 4 només-116).
   Mateix `size_system` (29), `customer` (7), `target` (WOMAN) — però el 115 té la fitxa POP SENCERA (34
   regles, feta a mà a l'S10) i el 116 té el que `detect_grading` va extreure del document del 269 (25).
   Per sota del llindar del 90% → **poden ser legítimament diferents** (font distinta), NO una còpia cega.
4. **Duplicació AVUI: incident aïllat** (1 sol parell). Cens: només **customer 7 / ss 29 = {115, 116}** té
   >1 ruleset de client per al mateix `size_system`. LOS (customer 6) en té 2 però en **size_systems
   diferents** (50, 51) → no és duplicació. **No és un patró recurrent en producció (encara).**
5. **Però el vector de duplicació és REAL i lligat a F-1.** El filtre de reutilització casa per eixos
   EXACTES; un ruleset nascut amb eixos NULL (el defecte que F-1 ataca) **mai** casarà amb un import que sí
   porta eixos. Mentre existeixin rulesets de client amb eixos NULL, la reutilització import↔ORM/size-map
   fallarà sistemàticament, encara que avui només se n'hagi materialitzat 1 cas.
6. **Punt d'inserció natural ja identificat** i amb precedents al codi: el `filter()` de candidats
   (`grading_utils.py:312-320`) + el patró "avís-i-confirma" (409 `grading_choice`, `extraction_views.py:1916`)
   per oferir al tècnic "ja existeix un ruleset similar per aquest client, reutilitzar-lo?".

---

## BLOC A.1 — La lògica de creació de `derive_grading_rule_set`

**Ubicació:** `backend/fhort/pom/grading_utils.py:229` (funció) · **cridada** des de
`import_session_confirmar_view` (`models_app/extraction_views.py:1840-1851`, Pas W5).

**Sí hi ha cerca de reutilització abans de crear** (`grading_utils.py:306-351`):
```python
candidats = GradingRuleSet.objects.filter(          # :313-320
    is_system_default=False,
    size_system=size_system,
    garment_group=garment_group,
    target=rs_target,
    construction=rs_constr,
    fit_type=rs_fit,
)
for c in candidats:
    if {r.pom_id for r in regles_c} != set(spec_by_pom):   # :324  (1) mateix conjunt de pom_id
        continue
    # (2)+(3) per pom: mateixa talla_base, logica, increment, valors_step   :328-341
    ...
    if igual:
        candidat = c; break
if candidat is not None:
    return candidat            # REUTILITZA (:346-351) — no crea res
# ... si no, CREAR NOU (:365-376)
```

**Què rep del cridador** (`extraction_views.py:1845-1850`):
```python
construction_codi=model.construction,   # :1845
fit_type_codi=model.fit_type,           # :1846
customer=model.customer,                # :1850
nom=f"Importació fitxa · {model.codi_intern}",   # :1847
```
→ els eixos surten del **model 269** (WOVEN/REGULAR); el `garment_group` de la combinació. El `customer`
és BRW (7).

**Per què NO va trobar el 115 (FET, no interpretació):**
- **(decisiu)** El `filter()` (`:316-319`) casa **`construction=WOVEN`, `fit_type=REGULAR`, `garment_group=7`**.
  El **115 té `construction=NULL, fit_type=NULL, garment_group=NULL`** (verificat a BD) → **NO entra ni tan
  sols al conjunt de candidats**. El `customer` **NO és al filtre** (no es filtra per client).
- Encara que hi entrés: `{pom_id}` del 115 = 34, de l'spec importat = 25 → `!=` a `:324` → descartat.
- Encara que el conjunt casés: el 115 desa la forma canònica (`increment_base/increment_break`, `valors_step`
  NULL) mentre `detect_grading` produeix `logica`+`increment`+`valors_step`; la comparació (`:333-341`) mira
  `increment` i `valors_step` → divergeix.

> **FET:** la reutilització existeix i és estricta. El 115 és **invisible** per a ella per tres motius, el
> primer i suficient és **els eixos NULL del 115** (el mateix defecte que F-1 vol resoldre). El filtre **no
> considera el `customer`** com a eix de cerca.

**Veredicte A.1:** existeix reutilització (`grading_utils.py:312-351`); va fallar per eixos NULL al 115 +
conjunt de POM diferent + representació diferent. **No és "cap lògica de dedup"; és una dedup estricta i
axis-first que un artefacte amb eixos NULL no pot activar.**

---

## BLOC A.2 — 115 vs 116: són bessons?

| Dimensió | 115 (`BRW · Blusa · ALPHA_EU_W`) | 116 (`Importació fitxa · BRW-FW27-0002`) |
|---|---|---|
| origen | CLIENT_RUN | CLIENT_RUN |
| customer | 7 (BRW) | 7 (BRW) |
| size_system | 29 | 29 |
| targets | {WOMAN} | {WOMAN} |
| construction / fit / group | **NULL / NULL / NULL** | **WOVEN / REGULAR / 7** |
| nre. regles | **34** | **25** |
| creat per | ORM/size-map (S10, model 268) | import-fitxa (`derive_grading_rule_set`, model 269) |

**Creuament de regles per `pom_id`:**
- **21 pom compartits** · **13 només al 115** · **4 només al 116**.
- Solapament **Jaccard = 21/38 = 55%** (relatiu al 116: 21/25 = **84%**; relatiu al 115: 21/34 = **62%**).
- Dels 21 compartits, **15/21 idèntics** en `logica+increment_base+increment_break+talla_break_label`;
  **14/21** tenen `valors_step` en almenys un costat (divergència de representació canònica vs valors_step).

> **FET: NO són bessons estrictes** (<90%). Comparteixen la **identitat conceptual** (customer 7 · ss29 ·
> WOMAN · blusa POP · el nucli de 21 POM amb increments majoritàriament iguals) però el 115 porta la fitxa
> POP **sencera** (34 regles, construïda a mà a l'S10) i el 116 porta el que `detect_grading` va extreure del
> **document del model 269** (25). Diferència de FONT i de completesa, no còpia cega.

**Veredicte A.2:** duplicació conceptual (mateix garment+run+client), NO duplicació material. El 115 és un
superconjunt parcial del 116 amb representació diferent. Per la regla del brief (<90% → poden ser
legítimament diferents), **no es poden fusionar cegament**; qualsevol consolidació és decisió humana.

---

## BLOC A.3 — És sistèmic o aïllat?

**Cens de rulesets de client** (`customer_id IS NOT NULL OR origen='CLIENT_RUN'`):

| id | origen | customer | size_system | constr/fit | nom |
|---|---|---|---|---|---|
| 104 | NULL | 6 (LOS) | 50 | –/– | LOS Kids Knit Regular 2Y-12Y |
| 111 | NULL | 6 (LOS) | 51 | –/– | EU ALPHA LOS TOP KNIT REGULAR V01 |
| **115** | CLIENT_RUN | **7 (BRW)** | **29** | NULL/NULL | BRW · Blusa · ALPHA_EU_W |
| **116** | CLIENT_RUN | **7 (BRW)** | **29** | WOVEN/REGULAR | Importació fitxa · BRW-FW27-0002 |

**Agrupat per `customer + size_system` amb `count>1`:** **només `(7, 29) = {115, 116}`**. LOS (6) té 2
rulesets però en **size_systems diferents** (50 ≠ 51) → NO és duplicació (són runs distints: Kids vs Top).

> **FET: incident AÏLLAT** (1 sol parell duplicat), i el parell és **el 115 de test de l'S10** (fet a mà)
> topant amb **el primer import real** (116) del mateix garment. No hi ha evidència que el patró s'hagi
> repetit abans amb altres customers/imports.

**⚠️ Matís (risc latent, no incident):** el filtre de reutilització NO inclou `customer` i casa per eixos
EXACTES. Qualsevol futur ruleset de client nascut amb eixos NULL (defecte F-1) serà invisible a la dedup →
el vector de duplicació **queda obert** encara que avui només s'hagi materialitzat 1 cop.

**Veredicte A.3:** aïllat AVUI (1 parell), però amb causa arrel compartida amb F-1 (eixos NULL) → **risc
sistèmic latent** si no es tanca.

---

## BLOC A.4 — On inseriria la reutilització (sense implementar)

**Punt natural 1 — el filtre de candidats** (`grading_utils.py:312-320`): és **on ja viu** la dedup. Avui
és `size_system + garment_group + target + construction + fit_type` amb igualtat estricta i **sense
`customer`**. És el lloc exacte per fer la cerca **client-aware i menys axis-strict** (p.ex. cercar per
`customer + size_system` i tractar els eixos NULL com a comodí, o com a candidat "similar" a proposar).

**Punt natural 2 — precedents ja existents al codi** (reutilitzables com a patró, no com a còpia):
- `cerca_canonic_equivalent(model)` (`grading_utils.py:84`, cridat a `extraction_views.py:1884`): ja **cerca
  un equivalent** (canònic de la Library) i **avisa** sense trencar el flux. Un germà `cerca_client_equivalent`
  (per customer) encaixaria al mateix punt.
- **Patró "avís-i-confirma" (409 + `grading_choice`)** (`extraction_views.py:1855-1916`; front
  `ImportWizard.jsx:447-460`, `handleConfirmar(gradingChoice)`): ja existeix per resoldre el conflicte
  "regla importada vs retinguda". El **mateix mecanisme** serviria per "ja existeix un ruleset de client
  similar #115 — reutilitzar-lo o crear-ne un de nou?".

**Punt natural 3 — pas del wizard on encaixa la pregunta al tècnic:** el flux d'import té un pas de
**grading preview** (`import_session_grading_preview_view`, `extraction_views.py:1460`, Pas W3; front
`ImportWizard.jsx` step 3, `handleGenerarGrading` `:308`). És on el grading derivat ja és conegut ABANS de
confirmar → el lloc net per mostrar "existeix un ruleset de client similar per BRW/ss29" sense trencar el
flux (i el commit final es fa a W5 `import_session_confirmar_view` amb el patró 409).

> **💡 PROPOSTA (a validar) — NO implementar:** la cerca de reutilització hauria de ser **client-first**
> (`customer + size_system`, opcionalment `garment_group`) i **oferir** el candidat al tècnic (avís-i-confirma)
> en comptes d'exigir igualtat estricta d'eixos+regles. Això cobreix el cas 115/116 (mateix client+run,
> regles i eixos diferents) que la dedup estricta actual mai unirà.

**Veredicte A.4:** el punt d'inserció **ja existeix** (`grading_utils.py:312-320`); el patró d'UI també
(409/`grading_choice` a W3/W5). No cal maquinària nova; cal **eixamplar** la cerca i **surface**-jar-la.

---

## TAULA RESUM (per al GATE d'Agus)

| Pregunta | Resposta | Font |
|---|---|---|
| **Existeix lògica de reutilització?** | **SÍ** (estricta, axis-first, sense `customer`) | `grading_utils.py:312-351` |
| **Per què no va reutilitzar el 115?** | eixos NULL del 115 (fora del `filter`) + pom-set 34≠25 + representació canònica vs valors_step | `grading_utils.py:316-341`; BD |
| **% solapament 115/116** | **Jaccard 55%** (21 comú · 13 sol-115 · 4 sol-116; 15/21 increments idèntics) | BD |
| **Són bessons?** | **NO** (<90%): mateixa identitat, font i completesa diferents | A.2 |
| **Nre. customers amb rulesets de client duplicats (mateix size_system)** | **1** → `(customer 7, ss 29) = {115,116}` | BD (A.3) |
| **Patró sistèmic o aïllat?** | **aïllat** avui (1 parell), **risc latent** per eixos NULL (F-1) | A.3 |
| **Punt d'inserció recomanat** | `grading_utils.py:312-320` (cerca client-aware) + patró 409/`grading_choice` a W3/W5 | `grading_utils.py:312`; `extraction_views.py:1460,1916` |
| **Fusió 115/116 automàtica?** | **NO** sense decisió humana (<90%, representacions distintes) | A.2 |

---

## RELACIÓ AMB F-1..F-5 (context per al GATE, sense decidir)

- El **115 amb eixos NULL** és, alhora, el símptoma que F-1 ataca (usabilitat al picker) **i** la causa que
  la dedup no el va veure (A.1). → F-1 (cablar eixos al camí de creació) **redueix** el vector de duplicació,
  però **no fusiona** el 115/116 ja existents ni fa la cerca client-aware.
- El **116 ja té els eixos correctes** perquè `derive_grading_rule_set` **ja els cabla** (`:365-376` via
  `model.construction/fit_type`). → el camí **import-fitxa ja fa el que F-1 vol fer al size-map**. F-1 seria,
  doncs, **consistència entre camins** (que el size-map faci el mateix que import-fitxa), no lògica nova.

---

*Fase A tancada. Read-only respectat: cap escriptura fora d'aquest fitxer, cap dada modificada.*

---

## GATE D'AGUS (2026-07-16) — decisió Patró C

1. **Reutilització client-aware PRIMER** (davant de F-1..F-5): és la causa arrel; els eixos NULL n'eren símptoma.
2. **Dades 115/116/268/269:** deixar-ho, **deute anotat** (no fusionar; <90% solapament).
3. **Intensitat:** **avís-i-confirma tou** (oferir el candidat al tècnic, no reutilitzar automàticament).
4. **Trigger de "similar":** **mateix `customer` + mateix `size_system`**.
5. **Superfície:** **només import-fitxa** ara (el size-map hereta consistència via F-1 després).

→ Fase B (ordre): **Peça R** (R-1 cerca `cerca_client_equivalent` + R-2 409 avís-i-confirma backend · R-3
prompt ImportWizard) **abans** de F-1..F-5. NO tocar dades, F-4, ni el fork gradingAxes.
