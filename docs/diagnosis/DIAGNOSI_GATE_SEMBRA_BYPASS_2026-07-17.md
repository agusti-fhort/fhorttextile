# DIAGNOSI — el gate d'autorització de sembra: on viu i per on es bypasseja

Data: 2026-07-17 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`

**Abast:** troballa transversal destapada al PAS 0 de F-CATALEG-A (la precondició va fallar: 14/27
GradingRuleSet amb `origen=NULL`). Censa **només** el gate d'autorització del `bootstrap_tenant`:
on viu, què protegeix i què no. **No** és el cens de F-CATALEG (explorador, wizard, A1-A4): aquell
segueix bloquejat fins que la classificació estigui feta.

> Convenció: cada fet porta `fitxer:línia`. **"NO EXISTEIX" = confirmat absent al codi**, no especulat.
> Les propostes van marcades `💡 PROPOSTA (a validar)` i són decisió humana (Patró C).

---

## Resum executiu

1. **El gate de grading està ben pensat: és una allow-list positiva** (`origen=CANONICAL`), no una
   deny-list. Default-deny per construcció: un ruleset sense classificar **no** viatja.
   `bootstrap_tenant.py:404-405`.
2. **Però no viu al motor: viu a la branca `--profile` del CLI.** Està dins de
   `if options['profile'] is not None:` (`:380`), i `--profile` és **opcional** (`default=None`,
   `:183`). Sense perfil, `source_filters` queda buit i `_read_source` ho diu ell mateix:
   **"None = totes les files"** (`:197`).
3. **El bypass no requereix astúcia: només ometre una flag.** `manage.py bootstrap_tenant <schema>`
   sense `--profile` copia **els 27 rulesets** — els 2 `CLIENT_RUN` de BRW i els 14 `NULL` inclosos.
4. **Avui aquest és l'ÚNIC camí possible: hi ha 0 SeedProfile al tenant.** El camí automatitzat
   (`provision_free_tenant`) falla tancat sense perfil (`:62-65`), i no n'hi ha cap → qualsevol
   sembra que es faci ara mateix és, per força, la nua i sense filtre.
5. **Hi ha un forat germà, i aquest sí que és actiu fins i tot AMB perfil: `SizingProfile` no té
   camp `origen`** (confirmat: `hasattr(SizingProfile,'origen') == False`) i **cap filtre** al
   `source_filters`. N'hi ha 1 de derivat de client (id 524, BRW) que viatja sempre que el bloc
   `sizing_profiles` estigui seleccionat.
6. **El risc #6 de F3-FINE ("skip silenciós") NO es confirma: el skip és sorollós i té conseqüència.**
   Avisa per fila (`:302`), el compta al resum (`:425-427`) i posa `ok = False` (`:428-429`), cosa
   que **impedeix tancar l'onboarding** (`:434-435`). Cal corregir F3-FINE en aquest punt.

---

## BLOC A — Com és el gate i on viu

**FET.** El filtre és positiu i s'aplica a dues taules:

```python
source_filters[GradingRuleSet] = {'origen': GradingRuleSet.ORIGEN_CANONICAL}      # :404
source_filters[GradingRule]    = {'rule_set__origen': GradingRuleSet.ORIGEN_CANONICAL}  # :405
```

**FET.** Abans del filtre hi ha una guarda de fail-closed: si el perfil demana grading i l'origen no
té cap ruleset CANONICAL, `CommandError` i cap còpia (`:394-403`). El missatge fins i tot remet a
`set_grading_origen`. És bona enginyeria — però viu dins la mateixa branca condicional.

**FET.** Tot el bloc penja de `if options['profile'] is not None:` (`:380`). `selected_models` i
`source_filters` s'inicialitzen buits a `:378`.

**FET.** `--profile` és opcional: `parser.add_argument('--profile', dest='profile', type=int, default=None, ...)` (`:183`).

**FET.** El filtre s'aplica per model, i l'absència d'entrada = sense filtre:
`rows = self._read_source(model, source, (source_filters or {}).get(model))` (`:228`), i el docstring
de `_read_source` diu **"`filter_kwargs` … None = totes les files"** (`:196-197`).

**FET.** Sense `--profile`, `selected_models is None` → l'spec no es retalla (`:410-411`) → `GradingRuleSet`
(`:153`) i `GradingRule` (`:156`) entren a la còpia sense filtre.

**FET.** En copiar, `GradingRuleSet` porta `{'customer': NULL, ...}` (`:153`): el vincle amb el client
**no** viatja. Conseqüència: els rulesets de client arriben al tenant nou **desatribuïts** — sense el
`customer` que els delataria, amb aparença de canònics.

**Veredicte BLOC A:** el gate és correcte de disseny i insuficient d'emplaçament. Protegeix el camí
que passa per perfil; no protegeix el motor.

---

## BLOC B — Abast real del bypass

**FET.** L'únic cridador programàtic de `bootstrap_tenant` és `provision_free_tenant`, i sempre passa
perfil: `call_command('bootstrap_tenant', schema, '--profile', str(profile.pk))`
(`provision_free_tenant.py:69`). Falla tancat si no en troba cap (`:62-65`). Aquest camí **és segur**.

**FET.** `views_seeding.py` només importa `seed_block_counts` (`:49`) — lectura de comptadors. **NO
crida `bootstrap_tenant`**: no hi ha camí HTTP de sembra.

**FET (dada viva).** `SeedProfile.objects.count() == 0` al backoffice. Confirma el watchpoint obert
d'F3 ("0 SeedProfile a staging"). **Conseqüència no òbvia:** com que `provision_free_tenant` exigeix
un perfil i no n'hi ha cap, avui **no hi ha cap camí segur disponible**; l'única manera de sembrar un
tenant és el `bootstrap_tenant` nu — precisament el que no filtra.

**FET (dada viva).** Cens de `GradingRuleSet` a `fhort`: **27 totals** — 11 `CANONICAL`, 2 `CLIENT_RUN`
(115 i 124, ambdós `customer=7` BRW), **14 `NULL`** (dos amb `customer=6` LOS: 104 i 111). El brief de
F-CATALEG deia 25: el cens s'ha mogut.

**Veredicte BLOC B:** el bypass no és una fuita activa del flux Free (que està mort per manca de
perfil), sinó **l'estat per defecte de qualsevol sembra manual d'avui**. És el camí del TMA — el que
el wizard de F-CATALEG ha de formalitzar.

---

## BLOC C — El forat germà: `SizingProfile` no té eix de provinença

**FET.** `SizingProfile` **NO TÉ** camp `origen` (verificat en viu: `hasattr(SizingProfile,'origen') == False`).
L'eix PROVINENÇA existeix **només** a `GradingRuleSet` (`pom/models.py:528-530`).

**FET.** `source_filters` només conté entrades per a `GradingRuleSet` i `GradingRule` (`:404-405`).
Per a `SizingProfile` **no hi ha filtre en cap camí**, ni amb `--profile`.

**FET.** `SizingProfile` es copia amb `{'customer': NULL, 'modified_by_id': NULL, 'parent_profile': DEFER}`
(`:158-160`) i té bloc propi: `'sizing_profiles': ['SizingProfile']` (`:64`).

**FET (dada viva).** 27 SizingProfile a `fhort`; **1 amb `customer`**: id **524**, `customer=7` (BRW),
`Woman | Buttoned Tops | Woven (Plana) | Regular`.

**Veredicte BLOC C:** el 524 és derivat de client i, a diferència d'un ruleset CLIENT_RUN, **cap gate
el mira**. Si el bloc `sizing_profiles` entra a un perfil, viatja — amb `customer` a NULL, és a dir
desatribuït. La llei PROVINENÇA es fa complir a una taula i no a la seva germana.

---

## BLOC D — Clausura: què passa quan el gate i les FK dures es contradiuen

**FET.** `SizingProfile.grading_rule_set` és **PROTECT i no-nullable**; el mapa de dependències ho
reconeix explícitament: `'sizing_profiles': {'base','garments','size_systems','grading'}` amb el
comentari *"Dependència DURA → arrossega grading"* (`:70-73`).

**FET (dada viva).** Dels 27 SizingProfile, **11 pengen d'un ruleset NO-canònic**: 1 de `CLIENT_RUN`
(el 524 → ruleset 115) i **10 d'un ruleset amb `origen=NULL`**. Només 16 pengen d'un CANONICAL.

**FET.** Amb el gate actiu (perfil amb `grading`), els rulesets no-canònics **no es copien** → el
`maps[GradingRuleSet]` no té destí per a ells → la FK obligatòria no es pot resoldre → **la fila se
salta** (`:296-297`, `skip` + `break`).

**FET — CORRECCIÓ A F3-FINE (risc #6 "skip silenciós").** El skip **no és silenciós**:
- avisa per fila: `self.stdout.write(self.style.WARNING(f"    [skip] {model.__name__} pk={src_pk}: {skip}"))` (`:302`)
- el compta al resum per model (`:425-427`) i al total (`:451`)
- **posa `ok = False`** (`:428-429`), i `_close_onboarding` només corre `if ok and not dry` (`:434-435`)
  → un tenant amb skips **no tanca l'onboarding**.

**FET.** La distinció està deliberada al codi: una FK **nullable** cap a un bloc no seleccionat no és
error (es posa a NULL i es compta com `nulled`, `:292-295`); només és skip dur si la FK és obligatòria
(`:290-291`).

**Veredicte BLOC D:** la clausura no menteix, però **es queda coixa i ho canta**. I hi ha un lligam
directe amb la decisió pendent: **classificar els 14 NULL canviarà aquest recompte**. Cada NULL que
esdevingui `CANONICAL` allibera els seus SizingProfile; cada un que esdevingui `CLIENT_RUN`/`IMPORT`
els condemna al skip. La classificació no és etiquetatge: **és una decisió de clausura**.

---

## TAULA DE RISCOS

| # | Risc | Evidència | Gravetat | Estat |
|---|------|-----------|----------|-------|
| 1 | `bootstrap_tenant` sense `--profile` copia CLIENT_RUN i NULL a un tenant nou (viola PROVINENÇA) | `:380` + `:183` + `:197` | **ALTA** | **OBERT** |
| 2 | Els rulesets de client arriben desatribuïts (`customer`→NULL) → semblen canònics | `:153` | ALTA | OBERT (agreuja #1) |
| 3 | `SizingProfile` sense eix `origen` ni filtre: el 524 (BRW) viatja fins i tot amb perfil | `hasattr()==False` + `:404-405` | **ALTA** | **OBERT** |
| 4 | 0 SeedProfile → l'únic camí de sembra disponible avui és el nu (sense filtre) | `SeedProfile.count()==0` + `provision_free_tenant.py:62-65` | MITJA | OBERT (watchpoint F3) |
| 5 | 11/27 SizingProfile pengen de rulesets no-canònics → skip en sembra amb gate | dada viva + `:296-297` | MITJA | **Mitigat**: avisa i bloqueja onboarding (`:302`, `:428-429`) |
| 6 | 2 rulesets de client (104, 111, LOS) amb `origen=NULL` escapen de la constraint de contenidor únic (parcial a `CLIENT_RUN`) | `pom/models.py:614-617` | MITJA | OBERT (el tanca la classificació) |
| 7 | "Skip silenciós" (risc #6 de F3-FINE) | `:302`, `:425-429`, `:451` | — | **NO ES CONFIRMA** — cal corregir F3-FINE |

---

## 💡 PROPOSTES (a validar) — on tancar el forat

Cap d'aquestes s'ha implementat. Són material per a la decisió (1) de F-CATALEG-A (**on viu el flag**),
perquè aquesta troballa la condiciona: **allà on es posi el flag, el gate ha de ser inevitable**.

- **P1 — `--profile` obligatori.** Una línia; converteix el camí nu en un error. Barat i immediat,
  però només tapa el símptoma: el motor segueix sense llei pròpia, i el proper cridador que oblidi
  el filtre reobrirà el forat.
- **P2 — Gate al motor (recomanat com a direcció).** El filtre `origen=CANONICAL` neix al `_spec()`
  com a política per defecte del model, no com a decisió del cridador; un override explícit
  (`--include-client-grading`, auditat) seria l'única manera de portar-se'n res més. Fa el bypass
  impossible per omissió, que és exactament com s'ha produït.
- **P3 — Estendre PROVINENÇA a `SizingProfile`.** Sense un eix `origen` (o, com a mínim, una regla
  "amb `customer` → no viatja"), el forat #3 queda obert facis el que facis amb el grading. Migració
  a app de tenant → coordinació amb plataforma.
- **P4 — Regla general en lloc de llista.** Cap entitat amb `customer` no-NULL no viatja mai, al
  motor, per a totes les taules. Cobreix #1, #2 i #3 alhora i no depèn de recordar-se'n taula per
  taula. A verificar: quines taules tenen `customer` i si alguna el té legítimament per a sembra.

---

## Què NO cobreix aquest doc

- El cens de F-CATALEG-A (A1 flag, A2 size systems, A3 encaix, A4 pantalla): **bloquejat** pel PAS 0
  (14/27 `origen=NULL`). La classificació és decisió humana i el propi command ho diu:
  *"La CLASSIFICACIÓ és una decisió humana (Patró C): aquesta comanda no endevina res"*
  (`set_grading_origen.py:5`).
- Si els 14 es classifiquen, cal **re-mesurar el BLOC D**: el recompte d'11 SizingProfile coixos
  canviarà amb cada decisió.
