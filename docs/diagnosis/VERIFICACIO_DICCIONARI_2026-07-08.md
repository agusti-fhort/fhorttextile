# VERIFICACIÓ RUNTIME — Diccionari de nomenclatura del client

Data: **2026-07-08** · staging `/var/www/ftt-staging`, branca `dev` · schema `fhort`
Abast: verificar el pipeline del diccionari del client (P1–P4) end-to-end en transacció
**revertida** (cap dada persistida). Sprint: CustomerPOMAlias bilingüe + preview + wizard +
commit idempotent.

Commits: P1 `b090960` · P2 `5b5796e` · P3 `6977c2d` · P4 `620d090`.

---

## ⚠️ Nota sobre el fitxer real de LOSAN

L'Excel **real** del diccionari de LOSAN **NO és al servidor** (cap `.xlsx` de LOSAN a
`/var/www/ftt-staging` ni a `/root`). La verificació s'ha fet amb un diccionari
**representatiu** derivat de nomenclatura real del catàleg (descripcions de POMs existents
+ codis dotted tipus LOSAN + entrades desconegudes). Els comptadors de sota són d'aquest
conjunt representatiu, **no** del fitxer real. Per obtenir el cost d'onboarding real de
LOSAN (dada de negoci), cal carregar l'Excel real des de la fitxa quan el faciliti l'Agus.

---

## Resultats (schema fhort, customer LOS, txn revertida)

Conjunt representatiu de 7 files (4 amb descripció que el matcher reconeix + 3 desconegudes):

| Comprovació | Esperat | Resultat |
|---|---|---|
| **Preview** (find_pom_master proposa, sense desar) | resum coherent | `total=7 · auto=4 (57%) · no_match=3` ✅ |
| **Commit** (taula confirmada) | vincula + crea | `linked=7 · created_pom=3 · skipped=0` ✅ |
| **Guard MANUAL sense ack** | 409, cap escriptura | `409` + 1 `manual_conflict` (H.99) ✅ |
| **Guard MANUAL amb ack** | sobreescriu | `200`, àlies re-apuntat ✅ |
| **Re-import (idèntic)** — àlies | cap duplicat | àlies estables (7 → 7) ✅ |
| **Re-import amb `create` forçat** — POMs | cap POM orfe nou | `created_pom=0` el 2n cop (reutilitza tenant-only) ✅ |
| **Rollback** | LOS intacte | cap fila persistida ✅ |

**Cost d'onboarding (representatiu):** de 7 nomenclatures, **4 (57%) es resolen soles** pel
matcher i **3 requereixen crear POM nou o resolució manual**. Amb el fitxer real de LOSAN
aquest percentatge serà la mètrica de negoci del temps estalviat per onboarding.

---

## Lleis verificades (de l'auditoria de 0031)

- ✅ L'àlies **mai** s'escriu per resolució automàtica sense revisió: el preview NOMÉS
  proposa (badge de confiança); l'escriptura passa pel commit de la taula confirmada.
- ✅ **Re-import idempotent**: `update_or_create` per `(customer, client_code)`; ni àlies
  ni POMs duplicats. El guard MANUAL evita sobreescriure correccions humanes en silenci.
- ✅ El diccionari **NO** substitueix el llaç d'escriptura per match manual de l'import de
  fitxes (P2 de la biblioteca): conviuen (fitxers separats, endpoints separats).
- ✅ Cap resolució per **substring genèric**: la proposta ve de `find_pom_master` (àlies
  exacte → sinònim → descripció) + selecció humana; el `#match` per substring és **només
  informatiu** (avís d'ambigüitat), mai resolutor (a diferència de 0031).

---

### Mètode
Patró B. Verificació en `transaction.atomic()` amb `set_rollback(True)` — cap escriptura a
BD. `manage.py check` net a cada peça · `npm run build` net · guardians (tokens CSS, icones
Tabler outline, i18n paritat ca/en/es). Real Excel de LOSAN pendent de l'Agus per a la
mètrica de negoci definitiva.
