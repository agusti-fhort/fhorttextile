# TREN DE PANYS · LES 5 PORTES QUE REVERTIEN SEMBRES

**Data:** 2026-08-22 · **Entorn:** `/var/www/ftt-staging`, branca `dev` · **Patró B**
**Substrat:** `CENS_CATALEG_V5_STAGING.md` (C6, els 24 escriptors-creadors) ·
`DECISIONS_snapshot_2026-08-22.md` (llei S44)

**6 commits + 1 d'acta. CAP push. CAP migració. CAP escriptura a cap BD viva** (els tests
corren contra una BD de test PRÒPIA, `test_ftt_panys`, perquè l'arbre i la
`test_ftt_staging` són compartits amb sessions concurrents).

---

## EL PRINCIPI, I ON ES VEU A CADA PANY

> Una comanda de sembra pot **CREAR el que falta**; no pot **REESCRIURE** nomenclatura,
> `pom_global` ni famílies d'allò que ja existeix, si no és amb un flag explícit d'overwrite
> que ho faci constar. I cap lookup d'idempotència per un camp rebatejable sense fallback +
> abort.

| Pany | Flag que ara exigeix la reescriptura | Què passa sense el flag |
|---|---|---|
| P1 | `--overwrite-nomenclature` | crea el que falta; el que ja hi és conserva nom, lligam i família |
| P2 | `--overwrite-nomenclature` | idem, i el destí (`--schema`) ja no té default |
| P3 | `--create-ruleset` | el joc es resol pels noms coneguts; cap coincidència ⇒ **ABORTA** |
| P4 | capacitat `CONFIGURE` | **403** amb missatge clar |
| P5 | `--overwrite` | create-only; i amb catàleg propi al destí, **ABORTA amb el recompte** |

**6 commits**, no 5: P5 en té dos (`db4dc6fa` el pany, `41bfbcf9` la contradicció
`--additive --overwrite`), i el sisè és aquesta acta.

---

## P1 · `load_losan_package` — el paquet no rebateja el que ja hi ha

**Commit:** `81f1878c`

**ABANS** (`backend/fhort/pom/management/commands/load_losan_package.py:247-285`,
`_load_pom_masters`): l'upsert portava `pom_global`, `codi_client`, `nom_client` i `categoria`
als `defaults` de l'UPDATE. Un POM que el tenant havia **desenganxat i rebatejat** tornava, a
la correguda següent, al text i al lligam del paquet. El pany de sobirania del 22/08 no hi
arriba: només veu `separat_de_global`, i un POM desenganxat **sense marca** hi és invisible.
I com que un upsert que reescriu el que ja hi havia no falla mai, no ho deia ningú.

**DESPRÉS**
- `:52` — `NOMENCLATURA_POM = ('pom_global', 'codi_client', 'nom_client', 'categoria')`
- `:80` — `--overwrite-nomenclature`
- `:133` — `_poda_nomenclatura(obj, defaults)`: treu dels defaults d'una ACTUALITZACIÓ els
  camps que canviarien, i retorna el detall **tant si poda com si no** (amb el flag, la
  sobreescriptura **consta**)
- `:334` — s'aplica només al camí d'UPDATE; el `create` no canvia gens
- `:234` — el recompte final: `🔒 nomenclatura PROTEGIDA` / `🔓 nomenclatura REESCRITA`

**Destí explícit:** `--schema-target` ja era `required=True`. Cap canvi.

**Tests** (`backend/fhort/pom/test_tren_panys.py::PanyP1LoadLosanPackageTest`, 4)
- `test_un_pom_desenganxat_no_es_re_enganxa` — el cas del cens, reproduït i bloquejat
- `test_create_if_missing_segueix_viu` — el camí legítim
- `test_camps_no_de_nomenclatura_segueixen_actualitzant_se` — el pany protegeix el VOCABULARI,
  no congela la fila (`notes`, `actiu` segueixen manant)
- `test_overwrite_nomenclature_reescriu_i_ho_fa_constar`

El paquet de la prova es fabrica al `tmp` (12 fitxers mínims): el que es mesura és
`_load_pom_masters`, que corre sencer i contra la BD.

---

## P2 · `extend_pom_catalog` — el mateix, i el destí sense default

**Commit:** `8c4538c0`

**ABANS** (`backend/fhort/pom/management/commands/extend_pom_catalog.py:213`): el
`update_or_create(pom_global=pg, defaults={codi_client, nom_client, actiu, categoria, notes})`
reescrivia el vocabulari a cada correguda. Aquí el POM **ni cal que estigui desenganxat**:
n'hi ha prou que el tenant l'hagi rebatejat sense separar-lo, i llavors `separat_de_global`
és buit i el pany de sobirania no el veu. I `--schema` tenia `default='fhort'`.

**DESPRÉS**
- `:177` — `--schema` passa a `required=True`
- `:180` — `--overwrite-nomenclature`
- `:236-250` — `codi_client`/`nom_client`/`categoria` només entren als defaults en **CREAR**;
  `actiu` i `notes` són ESTAT i segueixen manant
- `:261` — el recompte (`PROTEGIDA` / `REESCRITA`), al costat del dels sobirans

**Anotat, no tocat:** el `POMGlobal.update_or_create` (`:181`, a `public` **i** al tenant) es
deixa com és. La sobirania del tenant es materialitza al `POMMaster` per copy-on-write; el
canònic no és on el tenant repara, i tocar-lo aquí seria un altre pany, no aquest.

**Tests** (`PanyP2ExtendPomCatalogTest`, 4): el rebateig respectat, el create-if-missing viu,
el flag que reescriu, i `--schema` sense default (`CommandError`).
`test_sobirania_pany_importadors` (el germà del 22/08) segueix verd.

---

## P3 · el joc rebatejat — 🚩 EL FITXER DEL BRIEF NO EXISTEIX

**Commit:** `3681f8fc`

🚩 **DESVIACIÓ DEL BRIEF, i és la important d'aquest tren.** El brief apunta a
`sembra_cataleg_v4_additiu.py:96`. **Aquest fitxer no existeix** —ni a `ftt-staging`, ni a
`ftt-t7`, ni a `ftt-t9`. Hi ha dos candidats reals, i **el que fabrica el segon joc no és el
que el brief anomena**:

| Fitxer | Lookup | Què faria avui (joc rebatejat a PROD) |
|---|---|---|
| `sembra_cataleg_v4.py:86` | `filter(nom='BRW-CATALEG-v3')` + `CommandError` | **ABORTA**: no en crea cap |
| `seed_brownie_ruleset.py:131` | **`update_or_create(nom='BRW-CATALEG-v3')`** | **CREA UN SEGON JOC** i hi sembra les 142 regles |

El pany s'ha posat **als dos**, perquè el principi («cap lookup d'idempotència per un camp
rebatejable sense fallback + abort») els governa igual, però **el forat viu era
`seed_brownie_ruleset`**.

**DESPRÉS** (`backend/fhort/pom/management/commands/seed_brownie_ruleset.py`)
- `:60` — `NOMS_DEL_JOC = ('GRADING BROWNIE 2026', 'BRW-CATALEG-v3')`
- `:63` — `resol_el_joc(customer)`: prova els noms en ordre i, de reserva, el **`codi_sistema`**
  —que és on el rebateig va deixar el nom antic (llei S44)
- `:130` — `--create-ruleset`; sense el flag, cap coincidència ⇒ `CommandError` amb el detall
- `:168` — un joc que ja existeix **ja no rep els `defaults`** (`origen`, `actiu`,
  `size_system`): la sembra hi posa REGLES, no li redefineix la identitat

`sembra_cataleg_v4.py:92` passa pel mateix resolutor (importat, no recopiat — ja n'importava
`forma_de_la_regla`) i **segueix sense crear-ne cap en cap cas**; els seus logs diuen ara el
nom REAL del joc trobat, no el literal `RULESET`.

**Tests** (`PanyP3JocRebatejatTest`, 4): el joc rebatejat que no es duplica (i les regles que
van AL VIU), el retrobat pel `codi_sistema`, l'abort sense cap nom conegut, i el
`--create-ruleset` explícit. El full de càlcul es fabrica a la prova (dues files): el que es
mesura és **quin joc rep les regles**, no el parser del full.

---

## P4 · `setup-from-excel` — CONFIGURE, i 403 amb missatge

**Commit:** `4ba5553d`

**ABANS** (`backend/fhort/pom/s9_views.py:79`): `@permission_classes([IsAuthenticated])` sobre
un POST que fa `update_or_create` de `POMCategory`, `Target` i `POMGlobal` des d'un Excel
pujat. Un **tècnic** —el rol més bàsic— podia rebatejar el vocabulari sencer del catàleg.

**DESPRÉS**
- `:11` — `class _Configure(HasCapability)` amb `required_capability = CONFIGURE` i `message`
  propi (el patró de `dictionary_views.py:25` i `size_map_views.py:78`)
- `:96` — `@permission_classes([_Configure])`

**La lògica interna de l'endpoint NO s'ha tocat**, com demanava el brief.

**Tests** (`PanyP4SetupFromExcelTest`, 3): el tècnic amb **403** i `CONFIGURE` al missatge,
l'anònim fora, i qui té CONFIGURE que **travessa la porta** (i topa amb el 400 de «cal
adjuntar l'Excel» — la prova que el gating no s'ha menjat el camí bo).

**Anotat, fora d'abast:** `frontend/src/pages/OnboardingWizard.jsx:135` no amaga el botó a qui
no té CONFIGURE. Ara en rebrà el 403 amb missatge. El gating de botó és la peça germana
(llei del 14/08: els botons d'escriptura segueixen el gating que el servidor ja aplica).

---

## P5 · `bootstrap_tenant` — neix create-only, i guarda el destí poblat

**Commit:** `db4dc6fa`

**ABANS** (`backend/fhort/tasks/management/commands/bootstrap_tenant.py:341-356`): sense
`--additive`, `update_or_create` → **sobreescrivia** les famílies i el catàleg del destí amb
els de l'origen (`--from`, default `fhort`). El mode destructiu era **el defecte silenciós**.

**DESPRÉS**
- `:219` — `--overwrite`, l'única manera de reescriure
- `:435` — `additive = not options['overwrite']` — el defecte és **create-only**
- `:490` — 🔒 **LA GUARDA DE DESTÍ**: si el destí té `POMMaster` o `POMCategory` propis i no
  s'ha declarat res, `CommandError` amb el recompte —**quantes files pròpies té i quantes en
  trepitjaria l'origen**, per clau natural— i les dues sortides (`--additive` / `--overwrite`).
  Només mira els models que la correguda copiaria de debò: amb `--profile`, els que el perfil
  no selecciona no compten.
- `--additive` conserva el significat de sempre i ara és, a més, la **declaració** que el destí
  pot ser poblat.

**EL BOTÓ DE BACKOFFICE — quins flags passa.** El camí és
`ClientViewSet.create` → `_llanca_sembra_free` (`backoffice/views_tenants.py:44`, subprocés
detached) → `provision_free_tenant <schema>` → `bootstrap_tenant`. Queda **en mode additive**,
i el flag passa a ser **EXPLÍCIT** (`provision_free_tenant.py:73`:
`--profile <id> --additive`). Per què explícit si ja és el defecte: una sembra que salta una
peça **commiteja i després peta** (el `CommandError` final és fora de l'`atomic`), i el remei
documentat és re-executar-la — sense el flag, el segon intent moriria a la guarda i el tenant
es quedaria a mig sembrar.

**Tests** (`backend/fhort/tasks/tests_bootstrap_additive.py`, 12 — 7 d'abans + 5):
- `test_sense_cap_flag_el_defecte_es_create_only` — el cas del cens, invertit
- `test_un_desti_amb_families_propies_no_les_perd` — la guarda, amb el recompte exacte
  (`POMCategory: 2 propis, 1 que src trepitjaria`) i cap fila tocada
- `test_additive_explicit_travessa_la_guarda_i_no_toca_res`
- `test_overwrite_explicit_travessa_la_guarda_i_si_que_toca`
- `test_un_desti_verge_no_troba_la_guarda` — el camí del botó
- `test_sense_additive_sobreescriu` → reescrit a **`test_amb_overwrite_sobreescriu`**: mesurava
  exactament el defecte que aquest pany inverteix.
- `test_els_dos_flags_alhora_es_contradiuen` (commit `41bfbcf9`)

**Segon commit de P5 (`41bfbcf9`).** Amb `--additive --overwrite` alhora, `--overwrite` guanyava
per precedència i la guarda quedava saltada: qui els escrigués tots dos esperant create-only en
rebia l'oposat. Declarar les dues coses és no declarar-ne cap → `CommandError` (`:437`).

---

## EL VERD

| Control | Resultat |
|---|---|
| `manage.py check` (abans de cada commit) | **net**, 5/5 |
| `fhort.pom.test_tren_panys` (P1-P4) | **15 tests · OK** |
| `fhort.tasks.tests_bootstrap_additive` (P5) | **13 tests · OK** |
| **`fhort.pom` + `fhort.models_app` + `fhort.tasks`** | **1476 tests · OK (skipped=1)** · 6 652 s |

```
Ran 1476 tests in 6651.826s
OK (skipped=1)
```

**Com s'ha corregut, i per què així.** Aquella nit hi havia **tres sessions més** corrent
suites a l'arbre compartit. La `test_ftt_staging` és de tothom: la correguda va contra una BD
de test **pròpia**, amb un shim de settings que només canvia el nom:

```python
# <scratchpad>/settings_panys.py
from fhort.settings import *                              # noqa
DATABASES['default']['TEST']['NAME'] = 'test_ftt_panys'
```
```
PYTHONPATH=<scratchpad> venv/bin/python manage.py test fhort.pom fhort.models_app fhort.tasks \
    --settings=settings_panys --keepdb
```
…i llançada amb `setsid nohup` (el wrapper de background mata a 10 min; això va durar 1 h 51).
**Cap `npm run build` i cap `systemctl restart`**: aquest tren no toca frontend, i els gates
també són desplegament.

---

## EL QUE QUEDA OBERT (anotat, no tocat)

| | Què | On |
|---|---|---|
| 🚩 | El botó de l'onboarding no s'amaga a qui no té CONFIGURE: ara en rep el 403 | `frontend/src/pages/OnboardingWizard.jsx:135` |
| 🚩 | `POMGlobal` segueix sent upsert cec a `public` **i** al tenant (P2) | `extend_pom_catalog.py:181` |
| 🚩 | El paquet LOSAN **no transporta `breaks` ni `talla_break_pos`** (ho deia el cens, §③) | `export/load_losan_package.py` |
| 🚩 | `seed_brownie_ruleset --schema` i `sembra_cataleg_v4 --schema` conserven `default='fhort'` | el brief només demanava el destí explícit a P1/P2 |

**Cap push. El merge i el desplegament els fa l'Agus.**

