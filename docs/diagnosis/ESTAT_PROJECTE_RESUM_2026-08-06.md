# ESTAT DEL PROJECTE — resum per al vault · 2026-08-06 (tarda)

> ⚠️ **Aquest fitxer és la CÒPIA per pujar al vault.** L'MCP de claude.ai **no respon en aquesta
> sessió** (el connector demana autorització interactiva i la sessió és no-interactiva), o sigui que
> `ESTAT_PROJECTE.md` del vault **no s'ha actualitzat**. Cal pujar-hi aquest resum.
> El detall complet viu a [`ARQUITECTURA_2026-08-06.md`](ARQUITECTURA_2026-08-06.md).

**Base:** `origin/dev` = `dev` = `6d46fa92` en començar → **`43f8bd91`** en acabar. **Cap push.**

---

## El que ha entrat (bloc A · 4 commits nous, tots verds)

| commit | què |
|---|---|
| `61f938cf` | **A2** · `RegleEditCell`: el `onBlur` només envia si el valor ha CANVIAT, i mai declara un règim per defecte. Abans, tabular per la columna de Règim feia un POST per fila i `set_pom_regim_view` materialitza la resident i li estampa `origen='MANUAL'`: una passada de teclat convertia patrimoni heretat en autoria humana. |
| `ae906ef9` | **A5** · `es.json`: «Talla break» → «Talla de ruptura» (el fitxer ja tradueix *break* per *ruptura* a `:2262`). |
| `993c5a70` | **A6** · `MeasureGrid` i `ComprovacioPanel` passen al hook `useEstatDiccionari`: si el vocabulari no arriba, HO DIUEN. L'avís s'unifica a `components/ui/AvisDiccionari.jsx` — 3 superfícies, 1 avís, claus `dicc.error_*` als 3 idiomes. |
| `43f8bd91` | **A7** · L'acció AFEGIR del xat de mesures deixa de reescriure `origen` i les toleràncies: passa per `_procedencia_de_mesura`, la mateixa llei de `set-measurements` i `gravar-pom`. Tres portes, una sola llei. |

**A1** — QA2 ja estava tancat pels commits 58-66 (paritat i18n verificada).
**A3 i A4** — ja fets al commit 57 i **verificats a pantalla** (`qa_p08_pom_propi.py`, 3 idiomes).
**Backend reiniciat**; les dues rutes tocades responen 401 sense credencial (= vives).

---

## El que s'ha trobat (auditoria read-only, 5 fronts)

### 🔴 El primer de demà
**El wipe de graduació esborra les regles `MANUAL` que la pantalla nova acaba de crear.**
`materialize_model_grading_rules` fa `.all().delete()` sense filtre (`models_app/services.py:266`) i
la pantalla escriu `origen='MANUAL'` (`views.py:4694`). Hi ha **24 MANUAL vives a `fhort` i totes
estan armades**. Pitjor: el predicat que demana permís mira el **payload** (`views.py:1049`) i el que
destrueix mira l'**estat del model** (`views.py:1071`) → **qualsevol `update-step2` sobre un model
amb joc esborra les residents sense 409 i sense Watchpoint**.

### 🚨 Dany ja fet
**El MILEY (1308) té 4 regles `MANUAL` escrites avui a les 11:08:05 UTC** (3 noves + 1 convertida);
ha passat de 114 a 117 residents. El candidat més probable és el defecte que A2 acaba d'arreglar.
**No s'hi ha tocat res** — què se'n fa és decisió d'Agus.

### Altres riscos vius
- **L'import escriu al catàleg sense mirar el catàleg del client**: 4 resolutors codi→POM
  independents, 3 creadors de `POMMaster` sense àlies. **`D-31.27` NO EXISTEIX versionada.**
- **El pla dels 93 orfes no és executable**: 31 de 37 reparacions declararien que el codi de la CASA
  és el codi del CLIENT, i els «6 duplicats» són **un** import mal resolt, no sis casos.
- **L'exclusió de tasca ja NO estava trencada** (`fd633753`, 05/08) — **el forat és el relleu**:
  `traspassa_tram` no aplica l'exclusió al tècnic que arriba. Forat nou.
- **`DerivaTarget` deriva `KID_BOY` per a `JERSEY_TOPS` i `TAILORED_PANTS`** (famílies que també
  serveixen MAN i WOMAN): és el camí exacte del model 1307. Forat nou.
- **`los` és un tenant sense eixos** (0 targets, 0 perfils, sistemes sense talles) i el pas 3 del
  wizard **no bloqueja mai** allà.

---

## 12 decisions esperant l'Agus

1. Què es fa amb les 24 MANUAL vives — i amb les **4 del MILEY**.
2. Wipe de graduació: deixar-lo · protegir les MANUAL · no materialitzar.
3. Els 93 orfes: reparar només l'incident real? · què fem amb els 31 «codi de la casa»? · un POM
   canònic sense client ha de ser trobable?
4. Escriure `D-31.27` (no existeix al repo) **abans** d'implementar-la.
5. Credencials QA (2 tècnics amb `execute_tasks`) per poder córrer la prova de conflicte.
6. TimeSeed: quins minuts (els vius menteixen ×2,1 i ×12,3; en falten 7 a `fhort` i 15 a `los`).
7. `Paused→Done` (segueix prohibida des del 28/07).
8. El guard que pausa per DURADA i no per inactivitat.
9. On viu `PromoteToItemButton`.
10. «Entrada manual» del contenidor: camp nou + migració, o acceptar el criteri actual.
11. Els 51 models de `los` amb `target NULL`: runa d'assaig o dades bones?
12. Les dues doctrines de tria de joc (estricte vs eliminatiu): conviuen o convergeixen?

---

## Es pot tocar demà sense esperar ningú

Filtre d'`origen` al delete **+ el predicat de `views.py:1071`** (S) · Esc al modal de desfer (XS) ·
l'enllaç mort `/tasques/kanban` (XS) · instal·lar la cron del guard (XS) · les 4 línies del FK que
tenen LOSAN trencat (XS) · «Δ break» al castellà i «Talla break» al català (XS) · bolcar el guió de
la prova de 2 tècnics a `ops/qa/` (S) · la comprovació prèvia preguntant el que preguntarà el motor (S).
