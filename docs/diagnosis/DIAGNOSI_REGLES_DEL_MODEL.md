# Diagnosi — què vol dir avui «regla del model»

> 06/08. Diagnòstic demanat com a punt 1 del tram P0.5d. **No és una proposta d'implementació**:
> és el mapa del que hi ha, per poder decidir. Lectura pura excepte on s'indica; tota escriptura
> de prova s'ha fet dins d'un `atomic` que es desfà.

## La frase curta

Avui **«regla del model» vol dir «fila que ha quedat a `models_app_modelgradingrule` després de
l'última materialització»**. No vol dir que algú l'hagi triada, ni que el model en sigui l'autor,
ni que sobrevisqui al gest següent.

---

## 1 · La clau de resolució NO és l'àlies del catàleg

Les tres taules apunten al **mateix objecte**, `pom.POMMaster`, i **per PK**:

| taula | FK | fitxer:línia |
|---|---|---|
| `pom.GradingRule` (joc) | `POMMaster`, PROTECT | `backend/fhort/pom/models.py:1245` |
| `models_app.ModelGradingRule` (resident) | `POMMaster`, PROTECT, `db_constraint=False` | `backend/fhort/models_app/models.py:1043` |
| `models_app.BaseMeasurement` | `POMMaster`, PROTECT | `backend/fhort/models_app/models.py:629` |

```python
# backend/fhort/pom/services.py:747-753
rules = ModelGradingRule.objects.filter(model_id=model.id, actiu=True)
if rules.exists():
    return {r.pom_id: r for r in rules}
if model.grading_rule_set_id:
    return {r.pom_id: r for r in GradingRule.objects.filter(
        rule_set_id=model.grading_rule_set_id, actiu=True)}
```

⚠️ **Conseqüència per al tram del catàleg**: la premissa «la relació POM→regla es resol sola per
l'àlies del catàleg» és **falsa tal com està escrita**. Es resol pel **`pom_id`**. Ara bé, el
resultat pràctic és el que es vol *si i només si* la `BaseMeasurement` del model apunta al mateix
`POMMaster` que el joc — que és exactament el que garanteix anar a buscar els POMs al catàleg. La
llei del tram nou és, doncs, la que fa certa aquesta premissa; avui no ho és perquè el cercador
deixa entrar POMs de fora.

L'únic lloc que sí resol per codi és la **federació** (`tenants/federation_service.py:548-631`),
i és una frontera entre cases, no resolució interna.

---

## 2 · Un POM que només existeix per a aquest model

**Aquesta entitat no existeix al domini.** `POMMaster` (`pom/models.py:379-451`) no té cap camp
`customer`, `model`, `scope` ni `es_del_model`. Hi ha un *conveni* no declarat
(`pom_global=None` + `pendent_revisio=True` + `origen_import=<token>`), però és **estat, no
pertinença**: aquests POMs viuen al catàleg global del tenant i surten a la cerca de tothom.

Què li passa a la seva regla quan s'assigna un joc que no el conté:

```python
# backend/fhort/models_app/services.py:264-283
model.grading_rules.all().delete()      # ← WIPE TOTAL: no filtra per pom, ni origen, ni actiu
```

El POM queda **sense cap regla**: el fallback al joc tampoc el cobreix (el joc no el té) i, com
que `_load_grading_rules` és tot-o-res, no hi ha barreja. A la fitxa la fila queda muda a totes
les columnes menys la base. **La regla està esborrada, no desactivada: no hi ha desfés.**

---

## 3 · `origen` no dona cap privilegi de supervivència

| origen | qui l'escriu | sobreviu a una materialització? |
|---|---|---|
| `CANONICAL` / `CLIENT_RUN` | `origen_mgr_des_de_ruleset` (`services.py:243`) | **NO** |
| `IMPORTED` | import W5 (`extraction_views.py:2738`) | **NO** — i ve del document del client |
| `MANUAL` | `set_pom_regim_view:4661` · `gravar_pom_view:2220` | **NO** — i és **irrecuperable** |
| `FEDERAT` | `federation_service.py:813` | **NO** — cal reenviar el paquet |

`origen` només alimenta el text del 409 i el Watchpoint. **Cap regla està protegida per la seva
provinença.**

---

## 4 · Els forats, sense embuts

**F1 · El wipe és total; el consentiment, parcial.** Quatre camins esborren totes les residents;
**un de sol** demana permís (409 `GRADING_RESIDENTS_WIPE`, `views.py:1063`) i deixa rastre.
Cas concret: model amb 30 regles `MANUAL` escrites a Graduació. El tècnic tria «Sense graduació»
al pas 4 → `views.py:1041-1043` les esborra totes, 200 OK, **sense 409 i sense Watchpoint**
(perquè `residents_abans` només es calcula a la branca del ruleset *truthy*). Igual a
`extraction_views.py:2701` en reimportar sobre un contenidor amb regles.

**F2 · Es materialitzen regles que el motor no llegiria.** Els quatre camins passen
`grading_rule_set.regles.all()` (`views.py:925, 998, 1076, 1584`) **sense `actiu=True`**, però
`_load_grading_rules` sí que el filtra a la branca del joc (`pom/services.py:751`). Un joc amb 5
regles donades de baixa lògica dona **40 residents actives** a un model nou i **35** a un de vell
que graduï pel fallback. La mateixa pregunta, dues respostes, segons quan es va crear el model.

**F3 · `ModelGradingRule.actiu` és write-once-True.** Cap camí humà pot posar-lo a `False` (els
dos escriptors el forcen a `True`); la germana del joc sí que té baixa lògica
(`pom/views.py:300`). Mitja base de codi filtra `actiu=True` i l'altra mitja no; avui coincideixen
per accident.

**F4 · Cap gest humà pot esborrar UNA regla resident.** Podar una mesura
(`_poda_mesures`, `views.py:3157`) desactiva la `BaseMeasurement` i **deixa la regla viva per
sempre**. L'única manera de treure-la és destruir-les totes.

**F5 · La comprovació prèvia a l'enviament no fa la pregunta del motor.**
`comprovacio_views.py:230` mira **només residents**. Un model que gradua legítimament pel joc
(0 residents) veu **totes** les mesures a «BLOQUEGEN L'ENVIAMENT» mentre el motor li genera les
talles perfectament.

**F6 · `resol_proposta_graduacio`** (`models_app/services.py:218`), l'única funció que respon
literalment «mana el model o proposa el catàleg», **no la crida cap vista**. Codi mort.

**F7 · La federació envia mesures sense llei.** `_llegeix_patrimoni`
(`federation_service.py:672`) empaqueta només `ModelGradingRule`. Un model que gradua pel joc
envia `regles: []` i el `GradingRuleSet` **no viatja**. L'informe no ho diu.

---

## 5 · ✅ El forat que ja s'ha tancat (era meu, d'avui)

**La columna «VE DE» mentia al cas de fallback.** El commit 36 va servir `regla_origen` com si
`origen` pogués dir la procedència, i `pom.GradingRule` **no té aquest camp**: quan el model
gradua de debò pel joc arribava `None` i el front pintava «del model».

Provocat en transacció sobre el model 169: 13 files resoltes pel joc, totes mentint. Corregit al
commit **`954b875f`** amb `regla_es_resident` (de quina taula ha sortit la regla), i verificats
els quatre casos end-to-end sense residu:

| cas | resident | origen | pinta |
|---|---|---|---|
| materialitzada del joc | `True` | `CLIENT_RUN` | del joc ✅ |
| editada a mà | `True` | `MANUAL` | del model ✅ |
| fallback pur | `False` | `None` | del joc ✅ |
| sense regla | `None` | `None` | (res) ✅ |

---

## 6 · Què queda per decidir (Agus)

1. **El wipe-and-recreate en assignar joc** — és el que fa que comptar residents no mesuri res
   (v. `REPORT_P05D_GRADUACIO.md`). Opcions: deixar-lo com està; protegir les `MANUAL`; o no
   materialitzar i deixar graduar pel joc fins que algú editi. **És un canvi de motor.**
2. **F1** — que els quatre camins de wipe demanin el mateix consentiment, o cap.
3. **F5** — la comprovació hauria de cridar `_te_regles`/`_load_grading_rules` i no mirar només
   residents. És un fals positiu que bloqueja enviaments bons.
4. **F3** — o `actiu` serveix per a alguna cosa (i hi ha un gest que el baixa), o sobra.
