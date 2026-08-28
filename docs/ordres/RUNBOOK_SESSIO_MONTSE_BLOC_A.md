# Runbook · Sessió Montse — Bloc A: confirmar la identitat de les peces

**Data de prep:** 2026-08-26 · **Entorn:** staging (`https://staging.fhorttextile.tech`) ·
**Tenant:** fhort · **Usuari:** Montse (`m.bohils@fhort.cat`, perfil *manager*, verificat)

> **Res no s'ha confirmat en aquesta prep.** El banc del reconeixedor s'entrena amb el
> criteri de la Montse, no amb el nostre. Avui té **10 peces i 5 rols**; en acabar la
> sessió en pot tenir **60 i una dotzena llarga de rols**.

---

## 🚨 Dues coses que el brief donava per fetes i no ho estan

**1 · La confirmació d'identitat NO és al Taller.** Viu al **tab «Patró» de la fitxa del
model** (`PatternTab` → `PieceIdentityList`). El Taller (`/patro/taller`) té les eines de
POM i costura, i **no té la llista d'identitat**. Les URL d'aquest runbook apunten al tab.

**2 · El `?task_id=` no fa res en aquest tab.** `ModelSheet` només el cabla al tab
*Mesures* (`ModelSheet.jsx:765`); el tab Patró no obre cap tasca ni engega cap rellotge, i
és a posta (`PatternTab.jsx:26-28`: *«obrir un fitxer no ha d'obrir cap tasca; qui ve a
treballar entra al taller i el rellotge corre»*). Les tasques existeixen i estan obertes —
els id són a la taula—, però **avui el temps d'aquesta feina no s'imputa sol**. Decisió per
a l'Agus, no bloquejant per a la sessió.

---

## Abans de res: les DUES portes

**1 · L'staging està darrere una contrasenya d'nginx** (`auth_basic "FTT Staging"`,
usuari **`ftt`**). El navegador la demana en obrir qualsevol URL de la llista. La
contrasenya és a `/etc/nginx/.htpasswd-staging` i **no s'escriu aquí**: passa-la per un
altre canal. Sense això, la Montse veurà un `401 Authorization Required` d'nginx i no la
pantalla de login de l'FTT — són dues coses diferents i s'assemblen prou per fer perdre
mitja hora.

**2 · Després, el login normal de l'FTT** amb el seu usuari (`m.bohils@fhort.cat`).

> Les crides de l'API (`/api/…`) no passen per l'auth bàsica (`auth_basic off`, l'API ja té
> JWT), o sigui que un cop dins tot funciona; la porta és només la primera càrrega.

---

## Ordre del guió

| # | model | patró | URL (clic directe) | peces | què hi trobarà | task_id |
|---|---|---|---|---:|---|---|
| **1** | 1383 | **837 VESTIT** | [`/models/1383?tab=Patró`](https://staging.fhorttextile.tech/models/1383?tab=Patr%C3%B3) | 5 | ja identificades · el sistema hi encerta | **692** ⚠️ |
| 2 | 1499 | [QA-PAT] CALLIE | [`/models/1499?tab=Patró`](https://staging.fhorttextile.tech/models/1499?tab=Patr%C3%B3) | 16 | **16 silencis** | 696 |
| 3 | 1500 | [QA-PAT] MEREDITH | [`/models/1500?tab=Patró`](https://staging.fhorttextile.tech/models/1500?tab=Patr%C3%B3) | 15 | **15 silencis** | 697 |
| 4 | 1501 | [QA-PAT] TATE | [`/models/1501?tab=Patró`](https://staging.fhorttextile.tech/models/1501?tab=Patr%C3%B3) | 10 | **10 silencis** | 698 |
| 5 | 1502 | [QA-PAT] AMELIA | [`/models/1502?tab=Patró`](https://staging.fhorttextile.tech/models/1502?tab=Patr%C3%B3) | 4 | **4 silencis** | 699 |

⚠️ **La tasca 692 (837) està assignada a l'Agus, no a la Montse.** Les altres quatre sí que
són seves. No s'ha reassignat perquè el 837 és un model VIU i la frontera de la prep deia
de no tocar-lo. Si voleu el rellotge a nom seu, reassigneu-la abans de començar.

---

## Com es llegeix la pantalla

| el que veu | què vol dir | què ha de fer |
|---|---|---|
| Camp de rol **buit i blanc** | ningú no ho ha dit i la màquina ha callat | triar el rol |
| Camp de rol **taronja**, amb píndola i ✓ | **PROPOSTA de la màquina**, no desada | mirar l'evidència; ✓ si hi està d'acord, o triar-ne un altre |
| Camp de rol ple, targeta **verda** | **confirmat per una persona** | res, tret que hi discrepi |
| «Sense proposta» en gris | la màquina ha mirat i **no ho sap** | triar el rol; és el cas normal avui |

**El taronja no és un avís: és «encara no ho ha dit ningú».** El verd només el posa una
persona. Passar el ratolí per la píndola diu el marge, el llindar i quants veïns s'han
mirat; el text de la píndola diu **la raó** («és la mateixa peça que 837.MANGA», «es cus amb
front, back»).

**El botó «Identificar»** torna a proposar. No desfà res confirmat: només reescriu les
propostes.

---

## 1 · 837 VESTIT — on el sistema encerta (fes-ho PRIMER)

### 1a · Veure'l funcionar (mirar, no tocar)

Al selector **Versió** de la capçalera, tria la **v1** (`837 VESTIT s opcio cost`). Les cinc
peces surten **taronja** amb la píndola *«és la mateixa peça que…»* i marge **1,000**: el
reconeixedor les ha trobades idèntiques a les que ja hi ha confirmades a la v2/v3.

> És una versió superada i **no cal confirmar-hi res**: la geometria ja és al banc per la
> v3. Serveix per veure com es veu un encert.

Torna a la **v3** (la vigent) per treballar.

### 1b · La feina de debò (v3, la vigent)

Les 5 peces ja tenen rol confirmat i acta signada (24/08). El que els **falta**:

| peça | rol confirmat | bateig | lateralitat | cara | la màquina hi diu |
|---|---|---|---|---|---|
| 837.CUELLO | `collar` | — | — | — | **CALLA** (marge 0,108) |
| 837.DELANTERO | `front` | — | — | — | `front` (0,506) ✓ coincideix |
| 837.ESPALDA | `back` | — | — | — | `back` (0,668) ✓ coincideix |
| 837.MANGA | `sleeve` | — | — | — | `sleeve` (0,574) ✓ coincideix |
| 837.TAPETA | `placket` | — | — | — | `placket` (0,255) ✓ coincideix |

**Feina:** completar **bateig** (com en dieu al taller) i **lateralitat** de les cinc, i
**revisar els rols ja confirmats**.

> 🚩 **Si en canvies cap, ANOTA-HO.** No és un error teu: és una **discrepància de criteri**
> entre qui els va assignar i tu, i és informació que val més que la correcció.

El silenci del CUELLO és honest i val la pena mirar-lo: entre `collar` i `placket` el marge
era 0,108 sobre un llindar de 0,20 — dues tires petites, i el sistema ha preferit callar
abans que jugar-s'ho a cara o creu.

---

## 2-5 · Els quatre QA — on el sistema calla i tu l'ensenyes

**Els 45 silencis són correctes, no una avaria.** El banc només coneix cinc rols
(`collar`, `front`, `back`, `sleeve`, `placket`) i cap d'aquests quatre patrons no comparteix
peça amb el 837. Un sistema que hagués proposat alguna cosa s'ho hauria inventat.

Per a cada peça: **rol · cara · lateralitat · bateig**. Quan n'hagis fet un patró sencer,
confirma en bloc amb el botó de baix.

### 🔁 El bucle que val la pena veure

Després de confirmar **CALLIE** (16 peces), obre **MEREDITH** i prem **«Identificar»**.
El banc haurà passat de 10 a 26 peces i **poden començar a sortir propostes taronja**. Fes
el mateix abans de TATE i abans d'AMELIA.

> Això és el sistema aprenent del teu criteri en directe. Si les propostes que surten són
> bones, la palanca funciona; si en surt cap de dolenta, **anota-la** — és la dada més
> valuosa de tota la sessió.

### Notes per patró

| patró | peces | el que cal saber |
|---|---:|---|
| **CALLIE** | 16 | Blocs numerats `1`…`16`, sense noms parlants: el bateig hi val doble. 8 peces venien al doblec i el sistema les ha desplegades — la `14` fa 105.022 mm², exactament el doble de la meitat |
| **MEREDITH** | 15 | Noms parlants (`FRONT_`, `BACK_YOKE`, `FRONT_RUFFL`…). Porta **canesús** i **volants**, que el catàleg sí que sap dir (`yoke`, `ruffle`) |
| **TATE** | 10 | El més ric en auxiliars: `FACING_YOKE`, `FRONT_FACING`, `NECK_BAND`, `NECK_BAND_INTERLINING`. Quatre rols que GarmentCode no sap ni anomenar i que **només els pots ensenyar tu** |
| **AMELIA** | 4 | El més curt. `BACK`/`FRONT` + els dos de folre (`_LINI`) |

---

## Pas final · el recompte i, si toca, la re-calibració

**1 · Recompte del banc:**

```bash
set -a && . ./.env && set +a
venv/bin/python -c "
import django,os; os.environ.setdefault('DJANGO_SETTINGS_MODULE','fhort.settings'); django.setup()
from django_tenants.utils import schema_context
from fhort.patterns.recognition.bank import build_tenant_bank
with schema_context('fhort'):
    b = build_tenant_bank()
    print('peces al banc:', len(b))
    print('rols:', sorted({r[\"ftt_slug\"] for r in b.rows}))
"
```

**2 · Si el banc té ≥ 30 peces, torna a calibrar el llindar.** Amb més rols el marge
s'estreny per construcció, i el 0,20 d'avui es va fixar amb només cinc:

```bash
cd /var/www/ftt-staging/backend && set -a && . ./.env && set +a
for T in 0.05 0.10 0.15 0.20 0.30; do
  echo -n "llindar $T · "
  venv/bin/python ../ops/recognition/lab_d2.py --threshold $T 2>&1 \
    | grep -E "RIGHT|WRONG" | tr '\n' ' '; echo
done
```

**Anota la taula al final d'aquest fitxer.** El criteri no canvia: **el llindar més baix que
manté ZERO errades**, i després es dobla. Si el 0,20 deixa de tenir zero errades, el valor
nou va a `FTT_RECOGNITION_MIN_SCORE` (settings) i cal reiniciar `ftt-staging.service`.

---

## Estat de la prep, verificat

| comprovació | resultat |
|---|---|
| 4 models QA creats | 1499 · 1500 · 1501 · 1502 (client FTT, responsable Montse) |
| patrons importats **pel camí HTTP normal** | fitxers 21 · 22 · 23 · 24 · **45 peces** |
| reconeixedor corregut a l'import | `proposed_at` NOT NULL a **45 de 45** |
| propostes / silencis als QA | 0 / 45 — l'esperat |
| desplegat del CALLIE (cas canònic) | peça `14`: \|àrea\| = **105.022,6 mm² = 2 × 52.511,3** ✅ |
| tasques `pattern_digit` obertes | 696 · 697 · 698 · 699 (Montse) · 692 (837, **Agus**) |
| login i lectura amb el perfil de la Montse | 200 a model, patró, peces, catàleg de rols i tasques |
| escriptura amb el seu perfil | 200 a `identificar/` i a `recognize/` |
| flag `FTT_PATTERNS_ENABLED` al `dist` servit | absent → **encès** (el tab Patró es pinta) |
| UI del reconeixedor al bundle desplegat | «Identificant», «Sense proposta», «s'assembla a» ✅ |
| cap peça confirmada per nosaltres | ✅ 0 |
| 1383 / 162 tocats | ✅ cap escriptura |

### 🚩 Un desplegament pendent que NO és d'aquesta prep

Mentre es preparava això, **dues altres sessions han fusionat feina a `dev` i no l'han
desplegada**: `coda-t3-families` i `fixos-formacio-1`. Ara mateix staging serveix codi de
les **15:18** i el darrer commit és de les **15:52** — 34 fitxers de diferència.

- **No afecta la sessió**: cap dels 34 toca `patterns/`, `PatternTab`, `PieceIdentityList`
  ni `ModelSheet`, i les claus i18n del reconeixedor hi són als tres idiomes (comprovat).
- **Les verificacions d'aquesta taula valen per al procés que corre ARA.** Si algú
  desplega aquelles dues branques abans de la sessió, val la pena repetir el smoke de la
  taula: són cinc minuts.
- **No s'ha reiniciat des d'aquí**: no és feina d'aquest tram i desplegar la feina d'altri
  sense verificar-la, just abans d'una sessió amb la Montse, seria pitjor que el decalatge.

**Signe negatiu de l'àrea del CALLIE:** és l'únic material de la casa en sentit **horari**
(`fixtures/README.md`), o sigui que l'àrea signada negativa és una propietat del fitxer i no
un defecte. El que importa és la magnitud: el doble de la meitat.

---

## Resultat de la sessió *(a omplir)*

- Peces confirmades: ____ / 50
- Discrepàncies de criteri al 837: ____
- Propostes que van sortir al bucle (i si eren bones): ____
- Recompte final del banc: ____ peces, ____ rols
- Re-calibració: llindar nou ____ (o «es queda a 0,20»)
