# ELS 13 VERMELLS DE LA SUITE 3 — qui mentia, i per què

**Data:** 2026-08-21 · staging `dev` · log: `scratchpad/t_suite3.log:3753-3977`
**Punt de partida:** `Ran 1565 tests · FAILED (failures=2, errors=11, skipped=1)`

> **REGLA D'OR APLICADA:** primer decidir **qui ment** — el test o el codi. Cap test s'ha
> afluixat per passar. On el comportament nou és el correcte, el test s'actualitza **dient-ho**;
> on el codi hagués trencat una llei, s'hauria corregit el codi.
>
> **Veredicte global: cap dels 13 revela un defecte de codi.** Cap era una llei trencada. Onze
> són fixtures que van quedar incompletes sota una llei que no existia quan es van escriure, un
> és un contracte retirat a posta, i dos són un doble de test amb l'aritat vella.

---

## RESUM

| # | Família | Quants | Qui mentia | Sprint d'origen |
|---|---|---:|---|---|
| 1 | `RecomputeWelfordTest` | **8** | **la fixture** | J/R2 (sessió concurrent) |
| 2 | `StopEncadenatTest` | **2** | **la fixture** | J/R2 (sessió concurrent) |
| 3 | `test_regla_incompleta_warning_i_columna_plana` | **1** | **el test** (contracte retirat) | FIX A |
| 4 | `test_parser_excel` | **2** | **el doble de test** | preexistent · `4db5158d` (16/08) |

---

## 1 · `RecomputeWelfordTest` ×8 — CAUSA ÚNICA, i era al setup

Els vuit tracebacks acaben igual:

```
TaskTimeEstimate.DoesNotExist: TaskTimeEstimate matching query does not exist.
  → _cella()  →  TaskTimeEstimate.objects.get(garment_type_item=…, task_type=…)
```

La cel·la de Welford **no arriba a existir**. La crea `record_actual_time` a cada `→Done`, i
aquesta surt per la porta de `x <= 0`: `_real_minutes` suma `TRAMS_SANS` i no hi entrava cap tram.

### Qui mentia: la fixture

```python
def _tasca_treballada(self, minuts):
    """Una tasca oberta, treballada `minuts` i tancada — pel camí VIU (alimenta el Welford)."""
    transition_task(task, 'InProgress', self.prof)
    ...                                    # ← i aquí NO s'escriu res
    transition_task(task, 'Done', self.prof)
```

El helper **diu que treballa i no escriu**. Fins a J això no era una contradicció: un tram obert
i tancat ERA temps de feina i prou. Des de J/R2 no ho és — `_close_open_timer` jutja
`consulta=True` el tram que es tanca sense cap `escriptura_at`, i `TRAMS_SANS` el deixa fora del
Welford, de l'albarà i del consum. Una «tasca treballada» sense escriptura és, ara, **exactament
una consulta**.

### Per què el codi NO mentia

Vaig llegir J/R2 abans de tocar res, perquè un canvi a `TRAMS_SANS` pot buidar el Welford, els
albarans i el consum de cop. La implementació és correcta i el punt delicat està resolt:

```python
TRAMS_SANS = Q(fi__isnull=False, minuts__lte=MAX_MINUTS_TRAM) & ~Q(consulta=True)
```

**`~Q(consulta=True)` i no `Q(consulta=False)`** — i la diferència és tot l'històric. Els tres
estats del camp (`None` no jutjat · `False` jutjable · `True` consulta) fan que cap fila
existent canvii de valor. I la constant de plausibilitat no s'ha tocat ni se n'ha fabricat una
de paral·lela: el descart de J **no és un llindar, és una marca**, i respon una altra pregunta
(«s'hi ha escrit?», no «quant ha durat?») — coherent amb la decisió d'Agus a `ModelSheet.jsx`.

**La semàntica que aquests tests protegeixen (S43) no canvia:** una consulta no és mostra; un
tram sa ho segueix sent. El que faltava era que la fixture **digués una cosa que abans no calia
dir**.

### El fix

Un helper `_hi_escriu(task)` que estampa l'escriptura **pel MATEIX emissor que fa servir el
producte** (`batec_escriptura`, font única de «s'hi ha escrit») i **no** estampant
`escriptura_at` a mà:

> Si algun dia aquell emissor deixés d'estampar el camp, aquests tests ho han de veure.
> Escriure-hi el camp directament els faria cecs precisament al node del qual depenen.

Dos punts d'inserció, i el segon no és òbvi: `test_una_tasca_reoberta_compta_com_a_mostra_NOVA`
reobre la tasca, i **el tram de la rectificació tampoc no s'escriu sol**.

---

## 2 · `StopEncadenatTest` ×2 — la mateixa causa, i un segon tram

`_tasca_pausada` té el mateix forat que `_tasca_treballada`. Però aquí n'hi havia **dos**:

**`_gest_stop` (el play+stop encadenat) obre un tram NOU**, i aquell tampoc no s'escriu sol.
Sense marcar-lo, el segon tram seria una consulta i el gest no aportaria el temps que el test
mesura — que és precisament el que el test existeix per comprovar.

⚠️ **El tram desbocat de `test_el_gest_aporta_nomes_el_temps_sa` es queda com estava.** Es crea
directament, sense `consulta`, o sigui `None` → compta com l'històric, i l'exclou la clàusula
`minuts__lte=MAX_MINUTS_TRAM`. **És el que el test assereix i no s'ha de tocar**: la mostra ha de
ser 45, no 45+3710, i el motiu ha de seguir sent el llindar de plausibilitat, no la marca de J.

---

## 3 · `test_regla_incompleta_warning_i_columna_plana` — contracte retirat a posta

Aquest és **del FIX A**, i el vaig classificar malament la primera vegada: vaig llegir la llista
de vermells amb un `head` que en tallava una línia i vaig donar per bo «29 fixtures + 2
preexistents» quan eren **28 + 2 + 1**. La que faltava era aquesta, i és la que importa.

El test documentava, en un comentari propi, que una regla sense cap delta havia de donar
**«propagació PLANA (totes = anchor_val) + un únic warning (degradació gràcil)»**.

**Una columna plana ÉS un valor fabricat**: repeteix l'ancoratge a totes les talles i el presenta
com si fos graduació — el FIXED inventat que la llei D2 prohibeix, i el que va deixar el model
163 amb 225 specs a delta 0 tornant 200 OK. La «degradació gràcil» era graciosa amb l'usuari i
mentidera amb la dada.

### Els dos tests del mateix fet, contrastats (el que l'ordre demanava)

| | `ReglaIncompletaTest` (via `_apply_rule`) | `PropagaAncoratgesTest` (via `propaga_ancoratges`) |
|---|---|---|
| valor | tot `None` | tot `None` |
| avís | 1, i nomena `increment_base` | 1, i nomena `increment_base` |
| control del llegat | amb delta base no pinta res | amb delta base no mou res |

**Quadren.** I hi ha un tercer testimoni que ho vigila en execució: el **bloc C** del banc
(`ops/qa/banc_paritat_1383.py`), que exigeix que els dos nodes diguin el mateix sense fixar quin
valor. Tres testimonis, una sola frase.

Dues proves noves tanquen les dues temptacions que quedaven: **ni la talla ancorada rep valor**
(una fila amb una xifra i tres buits es llegeix com «aquesta talla sí i les altres encara no»,
no com «aquesta regla no gradua»), i **el control del backfill** del PAS 2.

---

## 4 · `test_parser_excel` ×2 — cinc dies vermell, i no era del parser

```python
match_rows.side_effect = lambda files, customer: (...)      # aritat 2
_match_rows(files, customer, model=None)                    # aritat 3 des de `4db5158d`
```

`_match_rows` va guanyar el tercer paràmetre `model` el **16/08** (`4db5158d`, T8-ter, «el
conflicte mira la peça de la fila») i els **dos** dobles d'aquest fitxer es van quedar amb dos.
`_extraccio_via_excel` el crida amb tres → `TypeError` dins del mock.

Fix: `lambda files, customer, model=None`. El default hi és perquè el doble segueixi valent tant
si el cridador el passa com si no.

> **Lliçó:** un doble de test és un contracte, i cap gate el compara amb la funció real. Quan una
> signatura creix, els seus mocks no ho saben — i el vermell que en surt sembla del mòdul
> equivocat.

---

## VERIFICACIÓ

Només els quatre mòduls tocats (minuts, no hores), com manava l'ordre:

```
manage.py test  fhort.tasks.test_recompute_welford  fhort.tasks.test_stop_encadenat
                fhort.pom.test_propaga              fhort.models_app.test_parser_excel
```

**Resultat: `Ran 83 tests in 63.688s · OK`** — els 13 tancats, zero vermells.

🚩 **La suite SENCERA no es re-llança ara.** Queda com a gate final pre-push, després d'E+F.

---

## EL QUE NO S'HA TOCAT

- **`TRAMS_SANS`, `MAX_MINUTS_TRAM` i `tram_compta`**: la llei d'higiene no s'ha tocat. Un canvi
  aquí mou el Welford, l'albarà i el consum alhora, i cap dels 13 demanava tocar-la.
- **La màquina d'estats** (`ALLOWED`): `Paused → Done` segueix prohibida.
- **El tram desbocat** de `test_el_gest_aporta_nomes_el_temps_sa` (v. §2).
- **Cap asserció** de cap dels 13. Només fixtures, un doble, i un contracte que la decisió del
  fix A va retirar explícitament.
