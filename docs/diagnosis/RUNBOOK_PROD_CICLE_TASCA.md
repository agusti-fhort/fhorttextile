# RUNBOOK · el que PROD arrossega del cicle de tasca

> **Escrit, NO executat.** Res d'això s'ha corregut contra PROD i res s'hi ha de córrer sense
> l'Agus al davant. Estat a 2026-08-05: tot el que hi ha a sota viu només a `dev` (staging), i
> `dev` **no està pushat**. El primer pas real de qualsevol desplegament és el push d'Agus.
>
> Ordre d'aquest document = ordre d'execució. El pas 2 depèn del pas 1: recomputar abans de
> migrar és recomputar contra un esquema vell.

---

## 0 · ABANS DE RES — el que fa que aquest runbook sigui necessari

PROD porta mesos planificant amb una estadística que, en bona part, **no mesurava temps sinó
tancaments**. El corpus es construïa per transició `→Done`; com que `Done→InProgress` és
permesa, cada re-tancament hi deixava una mostra nova amb el total acumulat d'aquell moment. Les
tasques que es reobren —les que costen— pesaven tantes vegades com s'havien reobert.

A staging això s'ha corregit avui. **A PROD, no.** Fins que el pas 2 no s'hi corri, el
planificador de PROD segueix servint els números vells.

---

## 1 · Desplegament de codi (el de sempre, amb dues trampes)

```
# a PROD (178.105.217.125), com sempre: merge dev→main, git pull, migrate, build, restart
git pull
python manage.py migrate_schemas          # MAI --schema (django-tenants dona OK enganyós)
npm run build
systemctl restart fhort.service           # fhort.service de PROD, NO el de PROJECTES
```

**⚠️ Auditar les columnes noves DIRECTAMENT a la BD després de migrar.** `migrate_schemas` pot
donar un OK que no es correspon amb el que ha entrat a cada schema.

**⚠️ Dependència nova al lock (HEIC, sprint del 28/07):** cal `pip install -r requirements.txt`
al desplegament, no només `git pull`. Sense això la importació de fotos de fitting peta.

---

## 2 · `recompute_welford --sense-orfes --apply` · **POST-MIGRACIÓ**

```
python manage.py recompute_welford --sense-orfes           # DRY-RUN primer, sempre
python manage.py recompute_welford --sense-orfes --apply
```

**Per què `--sense-orfes`** (decisió d'Agus, 05/08): un tram *mesurat* damunt d'una tasca
*externa* és un rellotge que va córrer sol —la porta que obria timer sense pantalla, arreglada a
T2—. No pesen (a staging: 4 trams, 1 minut), però deixar-los hi és **afirmar que són temps
mesurat quan sabem que no ho són**.

**Per què després de migrar i no abans:** el command llegeix `TaskTimeEstimate`,
`TaskTransition` i `TimerEntrada` amb l'esquema d'avui. Córrer-lo contra l'esquema vell és
recomputar una altra cosa.

### El que s'ha de mirar abans d'escriure

El dry-run treu tres informes (delta per TaskType · tasques amb tancaments repetits · rellotges
orfes). **Llegir-los és el pas, no un extra.** A PROD s'ha d'esperar el mateix patró que a
staging però amb ordres de magnitud més grans, i dues coses que cal decidir amb el número al
davant:

1. **Quantes cel·les cauen per sota de `WELFORD_MIN_SAMPLES = 5`.** A staging, de 4 cel·les que
   governaven el planificador en va quedar **1**. A PROD el corpus és més gran i la proporció
   pot ser una altra — però la direcció serà la mateixa, perquè la causa és la mateixa.
2. **Les cel·les «sense cap tasca supervivent» NO es toquen** i el command ja les respecta
   (esborrar una `ModelTask` s'emporta timers i transicions en CASCADE; la cel·la és l'últim
   rastre d'aquella feina). Si a PROD n'hi ha amb `n >= 5`, el command ho diu amb un
   `JA MANA sobre el planificador`: són cel·les que governen sense prova viva, i què fer-ne és
   decisió d'Agus, no del command.

### ⚠️ El límit conegut, que a PROD pesa més

L'atribució **no és reproduïble**. La clau de cel·la surt de `model.garment_type_item_id`, que
és MUTABLE i del qual no es desa el valor històric. Si un model ha canviat de variant, la seva
mostra va entrar en una cel·la i el recompute la posarà a l'**actual**. Això no és una repetició
fidel del passat: és una re-derivació sota l'atribució d'avui — que és, de fet, la que el
planificador farà servir demà.

### Verificació — NO la dona el propi command

Un command que s'aprova a si mateix és una signatura, no una verificació. Llegir
`TaskTimeEstimate` directament de la BD abans i després i comparar:

```
python manage.py shell < scripts_tmp/f31b_snapshot_welford.py > ABANS.txt
# … --apply …
python manage.py shell < scripts_tmp/f31b_snapshot_welford.py > DESPRES.txt
diff ABANS.txt DESPRES.txt
```

El diff ha de tenir **exactament** les cel·les que el dry-run havia anunciat i cap més.

---

## 3 · La cron del guard de tasca oblidada (D-9)

**No hi és a PROD.** Sense ella, una tasca que es queda En curs perquè algú va abaixar el
portàtil corre tota la nit i torna a contaminar el Welford que el pas 2 acaba de netejar — o
sigui que el pas 2 sense el pas 3 es desfà sol amb el temps.

```
mkdir -p /var/log/ftt
crontab -e
*/5 * * * * cd <ARREL>/backend && <ARREL>/backend/venv/bin/python manage.py \
    pausa_tasques_oblidades >> /var/log/ftt/guard_tasques.log 2>&1
```

**Abans d'instal·lar-la, la mateixa comprovació que s'ha fet a staging:**

```
python manage.py pausa_tasques_oblidades --dry-run     # què tocaria, sense escriure
```

I mirar-ne el recompte. A PROD, on hi ha històric de veritat, **el dry-run pot anunciar una
pila de trams vençuts**: són tasques oblidades de fa setmanes, i pausar-les totes de cop és una
allau de transicions. Que sigui correcte no vol dir que hagi de passar sense avisar ningú.

**Els tres números del disseny, i per què no s'han de tocar a la lleugera:**

| | valor | per què |
|---|---|---|
| avís del navegador | 30 min | el camí normal: dona veu a la persona |
| gràcia del modal | 3 min | temps per respondre'l → 33 min en total |
| llindar del cron | **40 min** | **> 33 a posta**: el cron només recull el que el modal no ha pogut tancar |

Baixar el llindar del cron per sota de 33 min invertiria l'ordre: el cron pausaria abans que el
modal hagi acabat de preguntar, i el tècnic trobaria la tasca pausada mentre el diàleg encara és
a la pantalla.

**Els trams DECLARATS queden fora per construcció** (T3, amb contraprova al test): aquest guard
mesura SILENCI, i un crono declarat no té batec ni n'ha de tenir — la feina externa passa fora
de l'eina. Sense l'exclusió, la cron mataria cada crono declarat als 40 min, a mitja feina.

---

## 4 · El fix de timers `89009858` — què és i què NO és

Commit **`89009858`** (timers read-only). El `TimerEntradaSerializer` feia `fields = '__all__'`,
de manera que **`last_heartbeat` naixia ESCRIVIBLE** pel `PATCH` de `/api/v1/timers/`: qualsevol
client podia segellar el seu propi tram i **esquivar el guard sencer** posposant-lo
indefinidament. El fix és `read_only_fields`.

Va amb el desplegament del pas 1 (és codi, no una operació). **Es llista aquí a part perquè és
l'únic d'aquest runbook que és una porta oberta i no un número dolent**: mentre PROD no el
tingui, el guard de PROD és opcional per a qui sàpiga fer un PATCH.

---

## 5 · STAGING NO TÉ PAS DE DESPLEGAMENT — i això val per a qui llegeixi això

nginx serveix `/var/www/ftt-staging/frontend/dist` **directament**
(`/etc/nginx/sites-enabled/ftt-staging`). **`npm run build` ÉS el desplegament de staging.**

Conseqüències que han mossegat més d'una vegada:

- Un build fet per verificar un commit **posa `dev` HEAD en viu** a
  `staging.fhorttextile.tech`. No hi ha pas intermedi on aturar-se.
- Un `git checkout` enrere **NO desfà el `dist/`** fins que no es torna a construir.
- Un build amb el codi a mig fer deixa **staging a mig fer**.
- **No es pot fer forensia del bundle anterior**: es sobreescriu. Per això els recorreguts
  d'Agus poden no quadrar amb el codi que hi ha al repo en aquell moment (bundle ranci o bundle
  massa nou).

`dist/` està a `.gitignore`: els commits guarden el FONT, no el desplegat. **PROD sí que té pas
de desplegament** (`git pull` + `npm run build` + `systemctl restart`) i per això allà el codi no
entra en viu tot sol.

---

## Ordre curt, per si es llegeix amb pressa

1. Push d'Agus de `dev` · merge `dev`→`main`
2. PROD: `git pull` · `pip install -r requirements.txt` · `migrate_schemas` · **auditar la BD** ·
   `npm run build` · `restart` — això ja porta el fix `89009858`
3. `recompute_welford --sense-orfes` (dry-run) → **llegir-lo** → `--apply` → **diff contra la BD**
4. `pausa_tasques_oblidades --dry-run` → mirar el recompte → instal·lar la crontab `*/5`

Saltar-se el 3 deixa el planificador mentint. Saltar-se el 4 fa que el 3 es desfaci sol.
