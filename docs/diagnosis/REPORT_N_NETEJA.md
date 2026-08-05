# REPORT N · NETEJA · el FK mort, el conflicte, la ronda i la sembra de QA

> Staging `/var/www/ftt-staging`, branca `dev`, base `7e2b5c4f`. Quatre commits locals, cap push.
> Cap suite: verificació estreta per fitxer i a pantalla.

---

## N1 · EL CENS DE `target_id` — LA PEÇA CENTRAL

`grep -rn "target_id"` + `grep -rnE "\.target\b"` sobre **tot** `backend/fhort`, migracions i
tests a part. Set resultats, i **el que importa és que no tots parlen del mateix `target`**: n'hi
ha tres de vius sobre altres models i **quatre de morts** sobre `GradingRuleSet`, que és l'únic
que va perdre el camp.

| # | fitxer:línia | de quin objecte | estat |
|---|---|---|---|
| 1 | `models_app/serializers.py:314-315` | **GradingRuleSet** | 💀 **mort** → 500 viu · **FIXAT** |
| 2 | `models_app/serializers.py:355-356` | **GradingRuleSet** | 💀 **mort** → 500 viu · **FIXAT** |
| 3 | `pom/management/commands/export_losan_package.py:298` (`select_related('target')`) | **GradingRuleSet** | 💀 **mort** · ⚠️ NO TOCAT |
| 4 | `pom/management/commands/export_losan_package.py:308` (`r.target.codi if r.target_id`) | **GradingRuleSet** | 💀 **mort** · ⚠️ NO TOCAT |
| 5 | `pom/s8_views.py:124` | `SizingProfile.target` | ✅ viu |
| 6 | `pom/management/commands/reseed_tenant_fhort.py:462` | `SizingProfile.target` | ✅ viu |
| 7 | `pom/s2_views.py:235` · `pom/models.py:1521` | `SizingProfile.target` | ✅ viu |
| 8 | `pom/size_map_views.py:1062` | `SizeSystem.target` | ✅ viu |
| 9 | `models_app/**` (`model.target`, `obj.target`) | `Model.target` (text lliure) | ✅ viu |

### Què feia el bloc, i per què s'esborra en comptes de reescriure's

El fallback tenia tres graons: **(1)** els targets de la M2M · **(2)** el FK legacy · **(3)** el
camp de text lliure del `Model`. El graó 2 no era un fallback: era un `AttributeError` esperant
el seu torn, perquè `pom/0043` (P7, «un rol, un vincle») va **esborrar el camp**.

S'esborra, i l'argument és que **seria codi mort per construcció**. La pròpia `0043` fa la
reconciliació FK→M2M *abans* del `RemoveField`, i el seu docstring ho diu: *«Cap lligam del FK
legacy es perd: tot `target` no NULL ha de constar a `targets`»* — amb el cas real documentat (rs
98 al schema `fhort`). Per tant **no existeix cap estat** on `targets` sigui buida i el FK
tingués res a dir. El que el graó cobria de debò —un ruleset sense cap target— ja el cobreix el
graó 3.

### Verificació

| model | abans | després |
|---|---|---|
| 163 · 164 · 182 · 188 | **500** `AttributeError` | **200** ✔ |
| 185 (ruleset amb targets) | 200 | **200**, i segueix resolent pel catàleg: `Man` / `Home` / `Hombre` ✔ |

Els quatre trencats apuntaven **al mateix ruleset**: el 219 · `BRW-CATALEG-v3`, amb `targets=[]`.

Test de fitxer únic `models_app.test_grading_target_sense_fk` → **3/3**: fixa el camí de la M2M
(que ha de manar), el camí del text lliure (que és el que cobreix el ruleset sense targets) i el
cas sense res, que ha de donar `None` i no petar.

### 🚨 El que NO s'ha tocat, i per què

**El parell export/load del paquet LOSAN està trencat pel mateix motiu** (files 3 i 4), i a més
per partida doble: `load_losan_package.py:419-422` llegeix `r['target_legacy']` i escriu
`'target': tgt` a l'`upsert` d'un `GradingRuleSet` **que ja no té aquell camp**. O sigui que
exportar peta al `select_related` i carregar petaria a l'escriptura.

No s'hi ha tocat perquè arreglar-ho **canvia el format del paquet** (la clau `target_legacy`
desapareix o es converteix), i això és una decisió de federació, no d'aquesta neteja. El brief
acotava N1 a un serializer llegint un FK mort. **Queda obert i és feina d'un tram propi.**

---

## N2 · S-19 · EL CONFLICTE ÉS EL RELLOTGE, NO LA PLANIFICACIÓ · `6f2c154b`

`caraObrirTasca` tenia dues condicions per obrir la cara CONFLICTE. La segona —*assignada a un
altre encara que ningú hi treballi*— mirava la **planificació** i en deia conflicte. Ha marxat.

La regla que queda és la de F2.0, sencera: **hi ha conflicte NOMÉS si `obert_per` (el
`TimerEntrada` obert) és d'un altre.** Una tasca assignada a algú que no l'ha començada és feina
prevista, i agafar-la és el gest normal del taller.

- L'assignee diferent segueix **visible com a nota discreta** («Assignada a: nom» al panell de
  Tasques; el nom del tècnic al Pla de treball). No calia afegir res: ja hi era.
- El títol de la cara perd el fallback a `assignee_nom`. Com que el diàleg ja només surt amb un
  rellotge obert, caure a l'assignee seria tornar a barrejar planificació amb realitat al text
  que diu qui la té.

**Verificació**: els 15 tests de F2.1 giren l'afirmació on tocava i n'hi ha **17** (pausada +
assignada a un altre → cap modal; rellotge d'un altre amb l'assignee a nom meu → conflicte).
A pantalla, amb `open-task` interceptat: model **174** (pom assignat al tècnic 15, sense tram
obert) → **cap modal**; model **188** → segueix sortint la cara ALBARANADA.

---

## N3 · S-20 · `Ronda.seq` COMPTA MOSTRES · `2b79afca`

Una correcció obria ronda i el comptador pujava: un model amb tres esmenes nostres semblava que
hagués fet tres mostres al client. `seq` és el número que el PM llegeix i el que billing
consultarà — no pot comptar dues coses.

Ara una correcció és una **tasca nova** lligada a la mare, amb `motiu='correccio'`, que **hereta
la ronda de la mare** (NULL quan la mare és la prevista, que és la volta 1 implícita). Porta
pròpia: `obrir_correccio`. `obrir_ronda` rebutja el motiu.

**No és una idea nova**: `ModelTask.motiu` ja existia a part del de la `Ronda` precisament
«perquè una tasca ad-hoc pot néixer d'una correcció sense que s'obri cap ronda»
(`tasks/models.py:196`). El model ho preveia; el servei no ho feia.

### El punt delicat, verificat abans de tocar res

Ara **dues tasques del mateix `code` poden conviure a la mateixa volta**. `tasca_vigent` hi
guanya dues clàusules:

1. **Veu les correccions de la prevista.** Neixen `origen='ad_hoc'` amb `ronda=NULL`; el filtre
   per `origen='prevista'` les hauria deixat **invisibles per sempre**. Aquest era el forat de
   debò, i no es veia des de fora.
2. **Entre les vives, mana la correcció MÉS RECENT.** `order_by('id').first()` hauria retornat la
   mare — la feina que ja se sap que no va sortir bé.

**Verificació**: `test_ronda` **59/59** (4 tests nous de correcció + 3 del resolutor) i
`test_contracte_f2`+`test_tasca_vigent` **21/21**. Els que afirmaven la semàntica antiga **giren
l'afirmació** en comptes de desaparèixer. **Zero rondes a la BD**: canvi de semàntica endavant,
sense dades a migrar.

Efecte lateral acceptat i escrit: una correcció dins d'una ronda entra al recompte de
`ronda_lliurable`, o sigui que la volta no és lliurable fins que l'esmena estigui feta. És el que
ha de passar.

---

## N4 · LA SEMBRA DE QA · `1da6a122`

`backend/scripts_tmp/n4_sembra_ronda_qa.py` — **idempotent**, amb guard explícit contra el golden
162 i `--desfer`.

**Què crea**: una `Ronda` seq 2 (`nova_mostra`) sobre el model **185** (`FTT-FW27-0001` · «Test
camisa», del tenant propi) i la seva `ModelTask` de `tech_sheet` en `Done` amb `finished_at`. El
script comprova que el tipus sigui `es_lliurable`: sense això no hi hauria cara LLIURADA sinó una
reobertura silenciosa.

**Com es desfà**: `venv/bin/python scripts_tmp/n4_sembra_ronda_qa.py --desfer` — esborra la ronda
i les seves tasques i deixa el model com estava. La feina de la volta 1 no es toca.

**Es fa després de N3 a posta**: N3 canvia com neixen les rondes; sembrar abans hauria estat
provar una semàntica que estàvem canviant.

**Verificació a pantalla**: `/models/185` → tab Fitxa tècnica → «Modificar» → surt la cara
LLIURADA (*«Fitxa tècnica» ja està tancada i lliurada*) amb «Obrir ronda 3 · nova mostra» i «És
una correcció». **Primera vegada que aquesta cara es veu a staging.**

---

## SORPRESES

### 🚨 S-N1 · El paquet LOSAN està trencat pel mateix FK, i per partida doble
Detallat a N1. Exportar peta al `select_related('target')`; carregar petaria escrivint
`'target'` en un model que ja no el té. No és un 500 viu (són comandes manuals), però és una via
de federació que avui **no funciona** i ningú no ho havia dit. Tram propi.

### 🔑 S-N2 · El model ja preveia N3 des del primer dia
El comentari de `ModelTask.motiu` descriu exactament el cas que N3 implementa. La semàntica
correcta estava escrita al model i el servei feia una altra cosa: no calia dissenyar res, calia
llegir el que ja hi havia.

### 🚩 S-N3 · La cara LLIURADA no s'havia vist mai, i el badge de F2.7 tampoc
Amb 0 rondes a la BD, ni el modal de D-5 ni el badge «Lliurable · ronda N» de F2.7 s'havien
pintat mai contra dades reals. Tots dos han sortit bé a la primera amb la sembra de N4 — però
val la pena tenir present que **fins avui eren codi no executat**.

### 🔵 S-N4 · El 500 no es veia a la llista de models
`ModelListSerializer` no calcula `grading_*`: per això el llistat es veia sempre bé i el model
petava en obrir-lo. Un error que només apareix al detall és fàcil de llegir com a «aquest model
està malament» en comptes de «tots els models amb aquest ruleset estan malament».
