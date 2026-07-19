# REPORT — F-RECUR: facturació recurrent (quota + consum)

Data: 2026-07-17 · **Patró A exprés → B seguit** · staging `dev` · **6 commits, sense push**

## Estat

COMPLET a `dev`, sense push (el fa l'Agus). Regla del verd: `manage.py check` net,
`npm run build` (backoffice) net. Migració additiva `0009` aplicada i auditada a la BD.

Cadena F-RECUR (sobre F-FACT-B1, ja a dev):

| commit | peça |
|--------|------|
| `163f390` | diagnosi fase A (les juntes) |
| `5bb09db` | eix temporal del contracte (periodicitat) + vincle event→factura |
| `a55ad63` | motor `generate_invoices` (quota + consum, DRAFT idempotent) |
| `8275827` | endpoint tancament de període + periodicitat als serializers de contracte |
| `82e62a0` | pantalla Tancament de període (SPA) |
| `23d6413` | consum + factures del client a la seva fitxa |

## Quadre de comprovació (verificat, no llegit)

**Escenari rollback** (FTT subjecte, contracte i events fabricats, cap dada persistida):

| pas | esperat | obtingut |
|-----|---------|----------|
| dry-run: quota 750 + (8−5)×25 | base 825 s/IVA | **825,00** ✅ |
| dry-run persisteix? | no | cap factura ✅ |
| generate → DRAFT | 2 línies | quota 750 + consum 75 ✅ |
| events vinculats | 3/8 (5 inclosos) | **3** ✅ |
| re-executar període | 0 duplicats | 1 factura, 2 línies ✅ |
| emetre + IVA 21% | total 998,25 | **998,25** ✅ |
| rectificativa | −998,25 | ✅ |

**BD viva** (FTT no-gratuït temporal, 6 events 2026-08, regles toves, **netejat després**):

| pas | resultat |
|-----|----------|
| preview a pantalla | FTT quota 299 + consum 6 events·1×8 = **307,00** s/IVA |
| generar (POST) | DRAFT #11, `creada=True` |
| re-generar | mateixa factura, `creada=False`, **1 sola factura auto** al període |
| anti-doble-cobrament a la BD | dels 6 events, **1 vinculat** (5 inclosos lliures) |
| fitxa de client | consum 2026-06: 4 total / 4 pendents / 0 facturats; 3 factures llistades |
| neteja | FTT tornat a gratuït, 0 factures i 0 events de QA |

## Dos bugs propis trobats exercitant (no llegint)

- **`NameError: ModelConsumptionEvent`** a `views_invoices` (no era a l'import). `manage.py
  check` NO atrapa noms lliures en cos de funció → surt exercitant l'endpoint. Tancat.
- **Resposta ranci** a `linia/` (heretat de F-FACT-B1, ja tancat allà): recordatori que
  `get_object()` amb `prefetch_related` cau ranci després d'escriure.

## Decisions de disseny (capacitat, no configuració hardcoded)

- **Periodicitat** = dada al contracte (`mensual`/`trimestral`/`anual`), amb `quota_toca_al_periode`
  ancorada al mes de `data_inici`. No hi ha cap supòsit de cicle al codi.
- **Anti-doble-cobrament PER BD**: `ModelConsumptionEvent.invoice_line` (SET_NULL). El motor
  filtra `invoice_line__isnull=True`; un event facturat no re-entra. Esborrar un DRAFT desfà
  el vincle (no perd l'event).
- **Sèrie mai hardcoded**: la comanda i l'emissió reben la sèrie per paràmetre. APP (o la que
  sigui) és una fila que crea l'Agus.
- **Sempre DRAFT**: la comanda no emet mai. L'emissió (número + IVA congelat) és acció humana.
- **billing_service NO tocat**: el motor previ conviu fins que es jubili (watchpoint fase A).

## Pendents / watchpoints per a l'Agus

1. **`billing_service` + endpoint `facturacio/generar/` segueixen vius** (motor previ, sense
   IVA ni sèrie, compta amb `.count()` sense vincular). No s'ha jubilat per no trencar res en
   calent. Quan `generate_invoices` el substitueixi del tot, s'ha de retirar.
2. **Dades de QA de F-FACT-B1 persistides a staging**: `QAT26-000001` (emesa, immutable) + la
   seva rectificativa esborrany + sèrie QAT + tipus QA_ES21. No s'esborren pel guard; cal SQL
   cru si es vol staging net.
3. **Events orfes reals** a public: BRW 18 + LOS 3, de tenants morts. La marca `exclos` ja
   existeix per arxivar-los; no s'ha aplicat (capacitat, no decisió d'ara).
4. **Per a PROD** (LOSAN): segueix faltant sembrar un Plan (0 a PROD, `plan` obligatori) i
   omplir l'IBAN de FHORT. Additiu a F-FACT-B1, no a aquest sprint.

---

## BLOC PER AL VAULT

> **F-RECUR — facturació recurrent (quota + consum de models iniciats)** · COMPLET a `dev`
> sense push · 6 commits (`163f390`→`23d6413`) sobre F-FACT-B1.
>
> **Motor**: comanda `generate_invoices --period YYYY-MM [--client] [--serie] [--dry-run]`
> (`recurring_service.py`). Per client viu/no-gratuït/amb-contracte: línia de QUOTA (si la
> periodicitat toca) + CONSUM (events × tarifa − inclosos). SEMPRE DRAFT, mai emet.
> **Idempotent per BD**: `ModelConsumptionEvent.invoice_line` (SET_NULL) + quota única per
> (client,període) → re-executar no duplica, un event facturat no re-entra.
>
> **Periodicitat** = dada al `TenantContract` (mensual/trimestral/anual, `quota_toca_al_periode`
> ancora al mes de data_inici). **Sèrie per paràmetre**, mai hardcoded.
>
> **UI backoffice**: pestanya "Tancament de període" (preview dry-run → generar DRAFTs) +
> consum/factures a la fitxa de client. Endpoints: `facturacio/tancament-periode/` (GET preview
> / POST genera, ADMIN) i `facturacio/consum/<codi>/`.
>
> **Verificat**: rollback (quota 750 + 3×25 → 825 → IVA → 998,25; 3/8 events vinculats;
> 0 duplicats en re-run; rectificativa) + BD viva (DRAFT #11, 1 event vinculat de 6, netejat).
>
> **Watchpoints**: `billing_service`/`facturacio/generar/` (motor previ) segueixen vius fins a
> jubilar-los; events orfes BRW/LOS a public (marca `exclos` disponible); per PROD falta Plan +
> IBAN. Migració `0009` additiva, auditada.
