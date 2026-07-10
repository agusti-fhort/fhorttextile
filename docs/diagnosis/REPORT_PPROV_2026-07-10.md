# REPORT — P-PROV: provinença-lite de `GradingRuleSet` (DC-1)

Data: 2026-07-10 · **Patró B (IMPLEMENTACIÓ)** · staging `/var/www/ftt-staging`, branca `dev`
Base: `docs/diagnosis/DIAGNOSI_PBOOT_CENS_COPIA.md` (B2)
Lleis: **RUN-CLIENT** (`DECISIONS.md:304`) · **PROVINENÇA** (`DECISIONS.md:348`, *"pendent
d'implementar"* — això n'és la versió mínima)

**3 commits, sense push.** Regla del verd completa. **Cap `--map` executat sobre dades reals:**
els 25 rulesets segueixen amb `origen NULL`.

| Peça | Commit | Estat |
|---|---|---|
| P1 — camp `origen` + migració `pom/0036` | `ec0b551` | ✅ VERD |
| P2 — tancar l'aixeta (7 escriptors censats) | `c1dfba6` | ✅ VERD |
| P3 — `set_grading_origen` (backfill) | `26736b1` | ✅ VERD |

> **Concurrència:** la sessió de plataforma va **intercalar** `507aff9` (C3.0) i `1b27e44` (C3.1)
> entre el meu P1 i el P2. Verificat amb `git merge-base --is-ancestor`: els tres commits meus són
> a la història i la migració `0036` hi és. Cap pèrdua, cap amend.

---

## Guardes de concurrència

- `git status -- backend/fhort/pom/` → **buit** abans de començar. Territori lliure.
- **Migració:** `showmigrations` mostrava **una sola línia `[ ]`**, i era la meva
  (`pom.0036_gradingruleset_origen`). Cap app de l'altra sessió tenia res pendent → per la regla
  acordada, `migrate_schemas` normal. Aplicada a `public` i `fhort`.
- **Auditoria a la BD directa** (no em fio del OK de django-tenants):
  `information_schema.columns` → `origen` existeix als **dos** schemes com a
  `character varying(12), is_nullable=YES`; `25/25` files amb `origen IS NULL`.

*(Nota: la primera crida a `migrate_schemas` va ser denegada perquè la condició del brief no era
auditable al transcript — no havia mostrat la sortida sencera de `showmigrations`. La vaig fer
visible i vaig reintentar. La denegació era correcta.)*

---

## P1 — El camp

`GradingRuleSet.origen`: `CharField(max_length=12, choices=..., null=True, blank=True)`.

`null=True` deliberat: **NULL = "no classificat"**, l'estat de les 25 files existents. Qui el tanca
és el backfill (P3), que és decisió humana. `GradingRule` i `GradingException` **no** porten camp:
hereten per FK `CASCADE` (cens B2 de la diagnosi).

Migració `pom/0036_gradingruleset_origen.py`: un sol `AddField` nullable → additiu, sense
reescriptura de taula.

```python
migrations.AddField(
    model_name='gradingruleset',
    name='origen',
    field=models.CharField(blank=True, choices=[('CANONICAL', 'Canònic FHORT'),
        ('CLIENT_RUN', 'Derivat de run de client'), ('IMPORT', 'Importat')],
        help_text='Procedència. NULL = no classificat (anterior a la llei PROVINENÇA).',
        max_length=12, null=True),
)
```

---

## P2 — Cens dels escriptors i tancament de l'aixeta

El brief n'anticipava un (`grading_utils.py`). El `grep` exhaustiu en va trobar **7**.

| # | Escriptor | Classificació | Base de la decisió |
|---|---|---|---|
| 1 | `pom/grading_utils.py:365` | **CLIENT_RUN** | Camí d'importació de fitxa (el que deia el brief) |
| 2 | `pom/size_map_views.py:813` | **CLIENT_RUN** | Wizard d'import de run de size-map; `_resolve_run_customer` (`:38-50`) pot tornar `None` → run genèric |
| 3 | `pom/s2_views.py:192` | **CLIENT_RUN** | 🛑 **Era AMBIGU** — vegeu sota |
| 4 | `pom/management/commands/seed_baby_months_grading.py:83` | **CANONICAL** | Seed de catàleg |
| 5 | `pom/management/commands/reseed_tenant_fhort.py:331` | **CANONICAL** | Seed de catàleg. Comanda **inert** (`CommandError` a `:84-87`); estampat per coherència del cens |
| 6 | `data/import_master.py:254` | **fora d'abast** | Script llegat Frappe (`/var/www/fhort-textile`, ruta morta), s'executa per redirecció a `shell`. Cap cridador. Usa `get_or_create`, no `create` |
| 7 | `fitting/tests.py:44` | **fora d'abast** | Fixture de test. `origen NULL` hi és **legítim**: és precisament l'estat que el codi ha de saber tolerar |

### L'escriptor ambigu i la decisió del CTO

`clone_sizing_profile_view` (`pom/s2_views.py:158`) clona un `GradingRuleSet` estàndard en una
**versió de client feta a mà**: ni seed de catàleg, ni importació d'un run. És viu i arribable
(registrat a `tasks/urls.py:164`, cridat pel frontend a `frontend/src/api/endpoints.js:144`); el seu
docstring diu *"Create a client version of the standard profile"* amb l'exemple
`"Brownie Knit Woman Regular"`, i posa `codi_sistema = <original>_CUSTOM` + `parent_version`. El
`rs98` («Custom Alpha EU — Women», parent 81) n'és l'empremta a la BD.

Per la llei del brief, **no el vaig decidir jo**. Vaig aturar-me i preguntar.

> **Decisió CTO (2026-07-10): `CLIENT_RUN`.**
> Semàntica fixada al docstring dels choices: **CLIENT_RUN = derivat de client**, sigui d'un run
> importat o d'**autoria manual** per a un client concret. El valor **no es renomena** (la migració
> ja està en vol); si algun dia molesta, és un rename cosmètic del choice.
> A `clone_sizing_profile_view`, fixar també el customer si el context de la crida el resol.

### Criteri uniforme aplicat als tres camins de client

**`origen` SEMPRE · `customer` si és resoluble · `logger.warning` si no.** La fuita de procedència
queda tancada per l'`origen` encara que l'eix de client quedi buit — que és exactament el que el
brief demanava per a `grading_utils`, i que he estès als altres dos camins per coherència.

- `grading_utils.py` — nou kwarg `customer=None`; `extraction_views.py:1398` li passa
  `model.customer`. Nou `logger` al mòdul (no en tenia).
- `size_map_views.py` — la resolució d'`alias_customer` **puja abans** del ruleset (la necessita);
  es retira la resolució duplicada que quedava més avall.
- `s2_views.py` — `customer = original.customer or original_rs.customer`. Nou `logger`.

Sense migració: els `choices` no canvien (`makemigrations --check` → `No changes detected`).

### Grep final de l'aixeta

```
fhort/pom/size_map_views.py:813              → origen=ORIGEN_CLIENT_RUN ✓
fhort/pom/grading_utils.py:365               → origen=ORIGEN_CLIENT_RUN ✓
fhort/pom/s2_views.py:192                    → origen=ORIGEN_CLIENT_RUN ✓
fhort/pom/.../reseed_tenant_fhort.py:331     → origen=ORIGEN_CANONICAL  ✓
fhort/fitting/tests.py:44                    → (fixture de test, NULL deliberat)
```

**Cap `GradingRuleSet.objects.create` de codi d'app neix sense `origen`.**

---

## P3 — `set_grading_origen`

`pom/management/commands/set_grading_origen.py`. La comanda **no endevina res**: ensenya i aplica.

- `--list [--all]` → taula `id · origen · customer · codi_sistema · n regles · nom`.
- `--map "75:CANONICAL,110:CLIENT_RUN:BRW"` → aplica; el customer es resol per `Customer.codi`.
- `--dry-run` → reporta sense escriure (`transaction.set_rollback(True)`).
- `--tenant SCHEMA` (default `fhort`).

**Validació completa abans d'escriure:** ids numèrics, valors d'`origen` dins dels choices,
existència del `GradingRuleSet` i del `Customer`. Si una sola entrada és invàlida, **no entra res**.

---

## Verificació

Lliçó S03b respectada: **tota** escriptura de prova dins `transaction.atomic()` amb rollback
explícit. Arnès a `scratchpad/verify_pprov.py` (fora del repo).

| # | Escenari | Resultat |
|---|---|---|
| 1 | Run simulat importat | ruleset **creat** (25→26), `origen=CLIENT_RUN`, `customer=BRW` ✅ |
| 1b | Run simulat **sense** customer | `origen=CLIENT_RUN`, `customer=None`, **`logger.warning` emès** ✅ |
| 2 | `set_grading_origen --list` | **25 files amb `origen NULL`** ✅ |
| 3 | `--map "75:CANONICAL,110:CLIENT_RUN:BRW"` | 1a passada: **2 canviats, 0 ja hi eren**. 2a passada idèntica: **0 canviats, 2 ja hi eren** → idempotent ✅ |

Estat real després de tots els rollbacks: **25 rulesets, 25 amb `origen NULL`** — intacte.

`manage.py check` → `System check identified no issues (0 silenced)` després de cada peça. Frontend
no tocat.

### Un fals negatiu instructiu

L'escenari 1b va **fallar a la primera**: el segon ruleset sortia amb `customer=BRW`. No era cap bug
del codi — era l'**anti-proliferació (1D)** de `derive_grading_rule_set` (`grading_utils.py:308-345`)
fent la seva feina: els meus dos jocs de valors tenien el **mateix increment (+2)**, la graduació era
idèntica, i el segon run **va reutilitzar** el ruleset del primer en lloc de crear-ne un de nou.
Dades de prova defectuoses. Amb increment `+3`, el camí de creació s'exercita i passa.

---

## Anotacions fora d'scope (vistes, no tocades)

1. **🚩 La reutilització (1D) pot enganxar un run de client a un ruleset CANÒNIC.** El filtre de
   candidats (`grading_utils.py:310`) és `is_system_default=False`, i **vuit rulesets clarament
   canònics del seed ISO tenen `is_system_default=False`** (76, 77, 78, 80, 82, 85, 92, 93 — vegeu
   la taula de la diagnosi B2). Un import de client amb graduació idèntica a un canònic hi
   quedaria enganxat. **No hi ha fuita de secret** (per definició de la reutilització, les regles
   són idèntiques), però un cop el backfill marqui aquests com a `CANONICAL`, seria net que el
   filtre exclogués `origen=CANONICAL`. 💡 **PROPOSTA (a validar)** — canvia comportament, fora
   d'aquesta peça.
2. **`is_system_default` no és un discriminador de canonicitat**, malgrat el que suggereix el nom.
   Confirmat amb dades. Qui el llegeixi com a tal s'equivocarà. Candidat a documentar o renombrar.
3. **`data/import_master.py`** apunta a `/var/www/fhort-textile` (ruta que no existeix en aquest
   servidor) i no té cap cridador. Sembla codi mort del temps de Frappe. Candidat a jubilació.
4. **Territori aliè tocat, per encàrrec del brief:** `models_app/extraction_views.py` (**una sola
   línia**, `customer=model.customer`). Verificat amb `git diff` que el canvi era exclusivament meu
   abans de commitejar.

---

## Què ha de fer el CTO

1. Revisar la cadena: `git show ec0b551`, `git show c1dfba6`, `git show 26736b1`.
2. **Push des de SSH** (cap agent ha fet push).
3. **Classificar els 25 rulesets** (Agus + Montse). Punt de partida:
   `manage.py set_grading_origen --list`. La taula de la diagnosi B2 ja diu quins semblen canònics
   (75-93, el seed ISO) i quins derivats (104, 107, 110, 111, i probablement 98 i 108). **Recordatori
   de la diagnosi:** `rs107` és FTT i `rs111` és LOS; el de Brownie és `rs110`.
4. Aplicar amb `--dry-run` primer, després sense.
5. Decidir sobre l'anotació 1 (excloure `CANONICAL` de la reutilització 1D).
6. Amb `origen` poblat, **DC-1 queda desbloquejada** i `bootstrap_tenant` ja pot filtrar
   `origen=CANONICAL` sense heurístiques de nom.
