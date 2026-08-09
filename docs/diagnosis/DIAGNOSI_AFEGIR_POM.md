# «＋ Afegir POM» — per què segueix tancat, i les tres vies per obrir-lo

> 09/08/2026 · coda del Tram 0 · **ATURADA**: triar via és decisió d'abast (§ del brief:
> «Si hi ha més d'una via possible i triar-ne una és decisió d'abast, ATURA i descriu-les»).
> Lectura pura: **cap línia tocada**.

---

## 1 · El bloqueig, exacte

El bloc A el va deixar deshabilitat amb aquest motiu escrit: «`rule_set` és read_only al
serializer». **Era la meitat del motiu.** Un `POST /api/v1/grading-rules/` topa amb **dues**
parets, no una:

| # | Paret | On |
|---|---|---|
| 1 | `rule_set` és **read_only** → un `create` no pot dir a quin joc va la regla | `pom/serializers.py:286` |
| 2 | `talla_base` és **FK NOT NULL** a `SizeDefinition` → un `create` ha de dir-ne una | `pom/models.py:1487` |

La primera es cau amb una línia. **La segona és la de debò**, i el motiu és que demana una dada
que **ningú no té i que el motor no llegeix**.

## 2 · Els cinc fets que manen aquí

1. **`talla_base` (la FK) és metadata morta.** El motor **no la llegeix mai**: `_apply_rule`
   ancora a `model.base_size_label`, i `pom/grading_utils.py:72` ho diu per escrit — «ancora a
   `model.base_size_label`, no a `rule.talla_base` (**mer metadata del seed**)». Els seus únics
   lectors són l'exportador i el `bootstrap_tenant` (serialització del catàleg).
2. **L'àncora viva és `talla_base_label`** (CAT2.1 · pas (a), ratificat per Agus el 07/08), i el
   pas **(b) —retirar la FK— està pendent, ajornat explícitament PER MIDA**.
3. **La maqueta v4 no té columna de talla base.** La taula de regles és
   `# · POM · Nom · Règim · Δ · Δ break · Talla break`. **La UI no ha de preguntar-la**, i el
   botó que la maqueta dibuixa és `＋ Afegir POM ▾` amb «Manual · Importar d'una fitxa».
4. **46 dels 47 jocs de `fhort` tenen ZERO regles** (l'únic amb regles és ZZ-TEST, amb 5, totes
   amb la mateixa `talla_base` = «M»). O sigui que **«copiar la base d'una regla germana» no
   serveix justament per al cas que importa**: estrenar el primer POM d'un joc buit.
5. **7 dels 47 jocs no tenen `size_system`**. Per a aquests, ni tan sols hi hauria un run contra
   el qual resoldre una etiqueta.

**La conclusió:** per a un joc buit **no existeix cap fet a les dades que digui quina és la seva
talla base**. Un `GradingRuleSet` no té camp de base. Qualsevol valor que hi posés el backend
—«la primera del sistema», «la del mig»— **seria inventat**, i el brief ho prohibeix
(«cap validació nova inventada»).

---

## 3 · Les tres vies

### A · Fer `rule_set` escrivible i **exigir `talla_base` al client**
- **Backend**: treure `rule_set` de `read_only_fields`. **Una línia.** Cap migració.
- **Frontend**: el flux d'afegir ha de **preguntar una talla base**. La pantalla ja carrega les
  `talles` del `size_system` del joc (les fa servir per a la barra de trencament), o sigui que
  té els ids a mà.
- **El preu**: posa davant del tècnic **una pregunta que la maqueta no té i que el motor
  ignora**. I per als **7 jocs sense `size_system`** no hi ha res a oferir → el botó seguiria
  mort allà.

### B · Fer `rule_set` escrivible i **derivar `talla_base` al backend**
- **Backend**: `rule_set` escrivible + `talla_base` opcional a l'API, resolta des de
  `talla_base_label` contra el `size_system` del joc (la mateixa resolució etiqueta→`SizeDefinition`
  que el sistema ja fa a `run_del_model`). Cap migració.
- **El preu**: **no hi ha cap etiqueta d'on partir en un joc buit**. `talla_base_label` és
  l'àncora de la regla, sí, però la regla encara no existeix — és el que estem creant. Caldria
  que el client l'enviés, i tornem al preu de la via A amb un pas més.

### C · Fer la FK **NULLABLE** (la versió mínima de CAT2.1 pas (b))
- **Backend**: migració d'una columna (`talla_base` → `null=True`), `rule_set` escrivible, i un
  guard de `None` als **dos** lectors de la FK. L'exportador **ja el té**
  (`_sizedef_key` retorna `None` si `sd is None`, `export_losan_package.py:72`); caldria mirar
  `bootstrap_tenant`.
- **El motor no es toca**: mai llegeix la FK.
- **Les regles existents no es toquen**: conserven la seva FK. Cap backfill.
- **El preu**: **hi ha migració**, i el brief deia «no n'hauria de caldre». I obre a mitges una
  decisió (CAT2.1 pas b) que estava ajornada sencera.

---

## 4 · Per què això és decisió d'abast i no la trio jo

Les tres vies **no fan la mateixa promesa**:

- **A i B** deixen el botó obert **només per als 40 jocs amb `size_system`**, i a canvi posen a
  la pantalla una pregunta que la maqueta va decidir no fer.
- **C** el deixa obert **per als 47**, no pregunta res, i és l'única que no contradiu ni la
  maqueta ni CAT2.1 — però **entra en territori de migració**, que és exactament el que es va
  ajornar per mida.

I n'hi ha una quarta que no és tècnica: **potser el botó no ha d'obrir-se ara.** Amb 46 jocs
buits al tenant, «afegir un POM a un joc» pot ser una feina que arribi amb la sembra del corpus i
no abans.

**El que sí que es pot arreglar avui sense decidir res**: el motiu escrit al botó, que **diu
mitja veritat** («`rule_set` és read_only») i amaga la paret que de debò mana (la FK
obligatòria). Si vols, el corregeixo i prou.
