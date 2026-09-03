# Patró A express · On és el segell de `GradingVersion`

**Read-only.** Clon: `ftt-staging` (branca `dev`). Cap escriptura, cap gest executat.

---

## 1. Qui escriu `GradingVersion.aprovada`

**Un sol escriptor, i és un servei.**

- `backend/fhort/fitting/services.py:965` · `seal_grading_version(version, *, user_profile_id, now)`
  — l'ÚNIC lloc del codi que assigna `aprovada = True`. Escriu **els tres camps junts**
  (`fitting/services.py:984`: `save(update_fields=['aprovada','aprovada_per','data_aprovacio'])`).
  Idempotent: si ja està aprovada, retorna sense reescriure qui/quan. **Des-segellar no existeix.**

Els dos únics camins que hi arriben:

| Camí | Fitxer:línia | Gate |
|---|---|---|
| **A. Endpoint directe** `POST /api/v1/grading-versions/<pk>/approve/` | `fitting/views.py:101` → `:119` | capability `CLOSE_GATES` |
| **B. Avanç de fase (gate del responsable)** | `tasks/services_d.py:60-62` → `fitting/services.py:988` `seal_model_grading` → `:1021` | capability `CLOSE_GATES` |

- **Serializer**: no hi escriu mai — `fitting/serializers.py:60`,
  `read_only_fields = ('data','aprovada','aprovada_per','data_aprovacio','is_active')`.
- **ViewSet**: `fitting/views.py:78` és `ReadOnlyModelViewSet` (PATCH/PUT/DELETE → 405);
  registrat a `fitting/urls.py:42`.
- **Admin**: **cap** `ModelAdmin` registra `GradingVersion` (`grep GradingVersion --include=admin.py` → 0 resultats).
- Camí B, matisos: `seal_model_grading` tria la versió **activa del SizeFitting de treball**
  (`_resolve_working_size_fitting`, `fitting/services.py:919`) i **no segella una versió sense
  `GradedSpec` actives** (`fitting/services.py:1018`). `fitting/advance_phase` (tancar sessió de
  fitting) **ja NO segella** des de D-3 peça 2 (`fitting/services.py:1201-1206`).

---

## 2. Controls d'UI que el criden

**El camí A (`approve`) no té CAP control d'UI. Zero.**

- `frontend/src/api/endpoints.js:895-897` — l'objecte `gradingVersions` només exposa `list`.
  No hi ha cap `approve`, i **`gradingVersions.list` no té cap call-site al front**
  (l'únic consumidor de versions és `patterns.export.gradingVersions`, `endpoints.js:1142`).
- Escalat / `PropagatedEditor` / fitting: només **topen** amb el segell (409 `sealed` en escriure-hi,
  `endpoints.js:169`, guard a `models_app/views.py:3146`). Cap gest per posar-lo.
- `components/model/DashboardTab.jsx:229-233` — **només mostra** el badge
  «Aprovada»/«Esborrany»; el botó obre la pestanya Escalat.
- `components/pattern/ExportModal.jsx:34,119` — **només consumeix** l'aprovació
  (llista únicament versions aprovades; si no n'hi ha cap, avís `exp_no_approved`).

**El camí B (gate de fase) SÍ té UI**, i és avui l'únic gest humà que segella:

- `frontend/src/api/endpoints.js:113` · `modelsApi.gate(id, {to_phase})` → `POST /api/v1/models/<id>/gate/`
- `components/planning/DashboardGovPanel.jsx:224` (bloc «Llestos per validar», individual)
  i `:236` (`gates.bulk`, en lot)
- `components/model/ActionsMenu.jsx:213` · `runAdvance` (avançar fase dels models seleccionats)
- Backend: `tasks/views_b.py:804` `gate_model_view` (`@permission_classes([_CloseGates])`),
  ruta a `tasks/urls.py:108`.

> Conseqüència: **avui no es pot aprovar una GradingVersion sense avançar la fase del model.**
> El segell és un efecte lateral del gate, i el gate és irreversible en el sentit que escriu
> `fase_actual` + `GateEvent`.

---

## 3. El writer d'export: exigeix `aprovada=True`?

**Sí, i és una precondició dura — cap byte.**

- **On rebota**: `patterns/engine/grading_projection.py:162-166` —
  `if not snapshot.approved: raise GradingNotApproved(...)`, a la primera línia de `project()`.
- **Qui posa el flag al snapshot**: `patterns/adapters.py:497` · `approved=bool(gv.aprovada)`
  (`DjangoGradingSource.snapshot`, amb `filter(pk=…)` i el flag MIRAT, mai `get(aprovada=True)`).
- **Com puja**: `patterns/export.py:180` captura `GradingNotApproved` → `ExportBlocked`
  (abans del writer: no s'escriu res).
- **HTTP**: `patterns/views.py:787` (`export-preview`), `:826` (`export`), `:863` (`export-rul`)
  → **422** amb `e.as_dict()`.
- A més, el selector ni tan sols l'ofereix: `patterns/views.py:737-751`
  (`GET …/pattern-files/<id>/grading-versions/`) filtra `aprovada=True`.
  Amb la GV201 sense aprovar, l'`ExportModal` del 1383 surt **buit** amb l'avís «cap versió aprovada».

---

## 4. Gest mínim perquè l'Agus aprovi la GV201 (v9) del SizeFitting 371 — SENSE executar-lo

Estat verificat avui (lectura, schema `fhort`):

```
model 1383 · TRV-SS27-0001 · 837 VESTIT · fase_actual = Dev
SizeFitting 371 · TRV-SS27-0001-SF1 · estat TallesGenerades
  gv124 v1 … gv200 v8 → is_active=False, aprovada=False
  gv201 v9 → is_active=True, aprovada=False, 105 GradedSpec actives   ← la vigent
```

Les tres precondicions de l'endpoint es compleixen: **v9 és l'activa** (si no, 409 `not_active`,
`fitting/views.py:112`), té **105 specs** i l'Agus (`a.devant@fhort.cat`, rol `admin`) té
`close_gates`.

```bash
# 1) token (staging serveix el tenant pel Host; el JWT queda segellat a l'schema `fhort`)
TOKEN=$(curl -s https://staging.fhorttextile.tech/api/token/ \
  -H 'Content-Type: application/json' \
  -d '{"username":"a.devant@fhort.cat","password":"<LA SEVA>"}' | jq -r .access)

# 2) el segell (idempotent; si ja estigués aprovada torna ja_estava_aprovada:true i no reescriu)
curl -s -X POST https://staging.fhorttextile.tech/api/v1/grading-versions/201/approve/ \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{}'
```

Resposta esperada: **200** amb `{"ok":true,"ja_estava_aprovada":false, …}` i
`aprovada_per` = el perfil de l'Agus, `data_aprovacio` = ara.

**Efecte immediat**: l'`ExportModal` del patró del 1383 passa de buit a oferir «Propagació
conscient · v9 · 105 specs», i `project()` deixa de rebotar amb 422.

**Efecte lateral a tenir present**: un cop segellada, `bump_grading_version_and_generate` refusa
escriure-hi (guard D-1, `pom/services.py:1122-1147`) i qualsevol propagació nova exigirà
**reobertura explícita**. El segell no es pot desfer: se supera creant la v10.

*Alternativa sense curl (l'única per UI): avançar la fase del model 1383 des de
«Llestos per validar» o des del menú d'accions — però això també escriu `fase_actual` i un
`GateEvent`, i no és el que es demana.*
