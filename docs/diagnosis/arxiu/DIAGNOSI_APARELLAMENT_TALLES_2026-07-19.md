> ⚠️ SUPERADA 2026-07-19 — implementada (FASE B: canònic estès · escombrat corrupció ·
> talla_mapping llei de sessió · taula d'aparellament + talla base al pas 1). Consulta com a històric.

# DIAGNOSI — Aparellament de talles document↔model (pas 1 del wizard d'import)

Data: 2026-07-19 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`

Abast: FASE A del brief APARELLAMENT DE TALLES. Entendre on viu l'estat del pas Talles, per què
el panell dret mostra etiquetes del document, on és l'auto-matching actual, i si el contracte
`talla_mapping` cap al JSON de sessió sense migració. Reportar i GATE abans d'implementar.
Convenció: `fitxer:línia` · "NO EXISTEIX" = confirmat absent.

---

## Resum executiu (per al gate)

1. **Dues fonts de la mateixa veritat, cap persistida com a llei.** El pas 1
   (`import_session_talles_view`) desa `run_conciliat` amb dues llistes SEPARADES (`document` vs
   `configurat`/`seleccionades`) i un `mapeig` OPCIONAL que **el frontend no envia mai** i que **el
   confirm no llegeix mai**. El confirm (post-78d891d) **re-deriva** la correspondència pel seu
   compte (remap canònic C1b) → la segona font. Amb un dialecte nou (`3-6m`) que el canònic actual
   no reconeix, el confirm no troba parella i cau al guard 422.

2. **El panell dret menteix perquè llegeix un camp de text lliure corromput.** Mostra
   `model.size_run_model` (string), NO les `SizeDefinition` reals del system. I l'acció **`alinear`
   SOBREESCRIU `model.size_run_model` amb les etiquetes del DOCUMENT** → un cop algú hi clica, el run
   del model queda en dialecte document per sempre. **Model 467 (PETALIA) ja està corromput** (vegeu
   §2). Les etiquetes tenant reals SÍ existeixen al backend (`system_labels`) però **no s'envien mai**
   al frontend.

3. **El contracte `talla_mapping` cap SENSE migració.** `run_conciliat` és un `JSONField`; ja hi ha
   la clau `mapeig` (dict). Formalitzar-la com a llista ordenada de parelles + `no_aparellades` és
   additiu al JSON, **cap migració**.

4. **⚠️ TROBALLA TRANSVERSAL (fora del brief, cal decisió):** l'acció `alinear`
   (`extraction_views.py:641-644`) és un camí de **corrupció de dades** (posa etiquetes-document dins
   `model.size_run_model`). El fix d'aparellament l'ha de **substituir** (la parella ja porta la
   traducció) i **restaurar** `size_run_model` de model 467 a etiquetes tenant.

5. **L'extensió del canònic és viable i segura.** Simulació sobre les **84** etiquetes de tots els
   systems amb `-`≡`/` + sufix mesos + zero-padding per tram: **0 col·lisions**. `M`/`S`/`L` (talles
   lletra) es preserven perquè la 'M' de mesos només es treu **precedida de dígit** (`ext('M')='M'`,
   `ext('3-6m')='3/6'=canonical('03/06')`).

---

## §1 — On desa la sessió l'estat del pas Talles i què en consumeix el confirm

**Escriptura (pas 1):** `import_session_talles_view` (PATCH `/talles/`, `extraction_views.py:604-698`).
Rep `talles_seleccionades` (etiquetes del DOCUMENT), `accio` (`alinear|mapejar|res`),
`mapeig_talles` (dict opcional `{label_doc: label_model}`, `:614,:633`). Escriu a
`session.run_conciliat` (`:661-669`):

```
run_conciliat = { 'document': [...doc...], 'sistema': ..., 'configurat': [...model run...],
                  'seleccionades': [...doc sel...], 'mapeig': {...}, 'sense_desti': [...],
                  'estat': 'RESOLT'|'PENDENT' }
```

- El gating és per **pertinença canònica**, no per parella explícita: `sense_desti` = seleccionades
  la forma canònica de les quals no és a `destins` (configurat ∪ system_labels ∪ mapeig.values)
  (`:653-658`). `ready` quan cap queda sense destí.
- **`mapeig` és opcional i mai el frontend l'omple** (l'agent de frontend ho confirma: `patchTalles`
  només envia `talles_seleccionades`+`accio`). No hi ha taula de parelles.

**Consum (confirm):** `import_session_confirmar_view` (`extraction_views.py:1692+`) **NO llegeix
`run_conciliat`**. Reconstrueix la correspondència amb el remap canònic C1b (`:1720-1745` aprox., el
del fix 78d891d) a partir de les claus de `valors` i les `SizeDefinition` del `model.size_system`.
El guard 422 (C1c) és la xarxa final. → **dues fonts**: el pas 1 decideix una cosa (gating canònic) i
el confirm en re-deriva una altra (remap canònic), sense que la del pas 1 sigui llei.

**Veredicte §1:** l'estructura hi és (`run_conciliat`, amb `mapeig`), però **ni es fixa com a llei ni
el confirm la consumeix**. El brief B1 (fixar `talla_mapping` i consumir-lo en exclusiva) tanca el fork.

## §2 — Per què el panell dret mostra `3-6m` (model 467)

**Cadena (frontend):** panell dret renderitza `configurat.map(...)`
(`ImportWizard.jsx:579`) ← estat `configurat` ← `data.run_configurat` (a l'upload) i
`data.run_conciliat.configurat` (després d'`alinear`). **Font backend de `run_configurat`**
(`extraction_views.py:566-568`): `model.size_run_model` (text lliure), **no** les `SizeDefinition`.

Les etiquetes tenant reals SÍ es calculen al backend (`system_labels`,
`extraction_views.py:648-649`) però **només** per al gating (`:653`) i **mai** es retornen al
frontend → el panell no té accés a les etiquetes reals i només pot mostrar `size_run_model`.

**Per què `size_run_model` porta `3-6m`:** l'acció `alinear` (`:641-644`):
```python
if accio == 'alinear' and talles_sel:
    model.size_run_model = '·'.join(talles_sel)   # talles_sel = etiquetes DEL DOCUMENT
    model.save(update_fields=['size_run_model'])
```
`talles_sel` ve de `run_talles_document`. Un cop algú clica "Alinear i adoptar", el run del model
queda en dialecte document.

**Estat REAL de model 467 (PETALIA, L27SBG0712 / LOS-SS27-0193):**
- `size_system` = `BABY_LOS_01`; `SizeDefinition` = `['03/06','06/09','09/12','12/18','18/24','24/36']`.
- **`size_run_model` = `'3-6m·6-9m·9-12m·12-18m·18-24m·24-36m'`** (CORROMPUT, dialecte document).
- `base_size_label` = `'03/06'` (intacte — `alinear` no el toca).
- `BaseMeasurement` = 10, **valued 0** (mateix símptoma que el 396 abans del fix).
- Sessions: la 60 tenia `configurat=['03/06'…]`; a la 61 (POMS) `configurat` ja és `['3-6m'…]` → prova
  que `alinear` va corrompre `size_run_model` entremig.

**Veredicte §2:** el panell dret ha de mostrar **`system.SizeDefinition.etiqueta`** (via endpoint nou
o camp nou a la resposta del pas 1), mai `size_run_model`. I `alinear` s'ha de retirar/substituir.

## §3 — On viu l'auto-matching i si perd parelles

- **Pas 1:** només calcula `sense_desti` per pertinença canònica (`:653-658`); **no genera cap llista
  de parelles** proposades al servidor. El `mapeig` és el que dugués el tècnic, i avui va buit.
- **Confirm:** el remap C1b construeix un dict transitori `canon_to_tenant` (parelles document→tenant)
  cada cop, l'aplica i **el llença** — no es persisteix ni es mostra al pas 1.

**Veredicte §3:** SÍ es produeixen parelles internament (al confirm), però **transitòries i
invisibles** al pas 1. El brief B2 les ha de **materialitzar com a proposta** al pas 1 i persistir-les
a `talla_mapping` perquè el confirm les consumeixi (una sola font).

## §4 — El contracte cap sense migració?

**SÍ, sense migració.** `ImportSession.run_conciliat` és `JSONField`. La clau `mapeig` (dict) ja hi és.
💡 PROPOSTA B1: afegir a `run_conciliat` la clau **`talla_mapping`** = llista ordenada de
`{"document": "3-6m", "model": "03/06"}` + **`no_aparellades`** = llista d'etiquetes-document sense
parella. Additiu, cap `migrate_schemas`. (El `mapeig` dict queda deprecat o es deriva de
`talla_mapping`.)

## §5 — Viabilitat de l'extensió del canònic (regressió)

Simulació sobre les **84** `SizeDefinition.etiqueta` de tots els systems, amb: `-`→`/`, treure sufix
mesos `m/M` **només si va precedit de dígit** (preserva `M/S/L`), i zero-padding per tram (fix C1a):
- **0 col·lisions** dins de cap system.
- `ext('3-6m') = '3/6' = canonical('03/06')` ✓ · `ext('M') = 'M'` (Medium intacte) ✓ ·
  `ext('6M') = '6'` · `ext('6/9') = '6/9'`.
- Etiquetes amb `m/M` presents: `0M, 0M-1M, 1M, 1M-3M, 3M, 3M-6M, 6M, 6M-9M, 9M, 9M-12M, 12M, 18M,
  24M, M`. La 'M' solitària (Medium) es preserva; les de mesos col·lapsen bé.

**⚠️ Detall d'implementació (B2):** el sufix mesos s'ha de treure **per tram** (cada segment
`digits+m`), no només al final del token (p.ex. `0M-1M`→`0/1`), i **només** amb dígit al davant. La
regressió d'unicitat s'ha de córrer sobre TOTS els systems abans de commitar (STOP si col·lapsa).

---

## TAULA per al CTO

| # | Fet | Ancoratge | Implicació (FASE B) |
|---|---|---|---|
| 1 | `mapeig` existeix però ni s'envia ni es consumeix | `extraction_views.py:614,633,653-658` · confirm no llegeix rc | B1: `talla_mapping` llei + B2 confirm el consumeix |
| 2 | Panell dret = `model.size_run_model` (text), no `SizeDefinition` | `ImportWizard.jsx:579` · `extraction_views.py:566-568,595` | B3: enviar i mostrar `SizeDefinition.etiqueta` |
| 3 | `alinear` corromp `size_run_model` amb dialecte document | `extraction_views.py:641-644` | retirar/substituir + restaurar model 467 |
| 4 | Model 467 corromput (`size_run_model='3-6m…'`, 10 mesures NULL) | ORM | verificar-lo com a cas PETALIA (B) |
| 5 | Contracte cap al JSON sense migració | `models.py ImportSession.run_conciliat JSONField` | B1: additiu, cap `migrate_schemas` |
| 6 | Extensió canònic viable, 0 col·lisions, `M/S/L` intactes | simulació 84 labels | B2: sufix mesos per tram, dígit-precedit; regressió obligatòria |

---

*FASE A completa. Read-only. **GATE** — esperant validació d'Agus del contracte `talla_mapping`
(dins `run_conciliat`, sense migració), del retir de `alinear`, i de l'extensió del canònic abans de
la FASE B.*
