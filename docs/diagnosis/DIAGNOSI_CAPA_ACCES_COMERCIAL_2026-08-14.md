# DIAGNOSI — Capa d'accés a la informació comercial

**Data:** 2026-08-14 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`
**Abast:** el sistema de capabilities, el bloc comercial sencer (front + backend), la fuita
de camps econòmics fora del bloc, i qui pot escriure a la pantalla de gestió d'usuaris.
**Motiu:** requisit de PROD — els tècnics no han de veure preus de venda ni costos.
**Decisió d'Agus ja presa:** capability única `COMERCIAL`, com a columna nova de la matriu.

> **Convenció:** cada afirmació porta `fitxer:línia`. `"NO EXISTEIX"` = confirmat absent al
> codi, no especulat. Les proves en viu s'han fet contra gunicorn `127.0.0.1:8001` amb
> `Host: staging.fhorttextile.tech` i un JWT segellat (`tenant_schema=fhort`) de l'usuari
> **19 `qa.loginunic@fhort.test` · rol `technician` · `permisos={}` · caps efectives
> `['execute_tasks']`**. Cap crida ha modificat estat (§4.2 explica com s'ha garantit).

---

## Resum executiu

1. **El sistema de capabilities SÍ es comprova AL SERVIDOR.** No és cosmètica de client:
   `HasCapability` és una `BasePermission` de DRF (`backend/fhort/accounts/capabilities.py:57-65`)
   i està endollada a desenes d'endpoints. La troballa principal **no** és "només client".
2. **La troballa principal és una altra: TOTA LECTURA COMERCIAL ÉS `IsAuthenticated`.**
   El patró declarat és «lectura = qualsevol autenticat; escriptura = `CONFIGURE`»
   (`backend/fhort/commerce/views.py:3-5` i `:31-37`). Verificat en viu: el tècnic rep
   **200 a les 16 col·leccions comercials**, amb `unit_price`, `line_total`, `subtotal`,
   `total`, `cost_price`, `sale_price` i `price_snapshot` al payload, i **es descarrega el
   PDF sencer d'una oferta** (108.509 bytes, `200 application/pdf`).
3. **El menú tampoc no tapa res: la secció Comercial no té `cap`**
   (`frontend/src/components/layout/navGroups.js:44-57`) i **cap `<Route>` està guardada**
   (`frontend/src/App.jsx:465-484`). Avui el tècnic veu el menú Comercial sencer.
4. **🔴 El forat fora del bloc és REAL i té nom: la pestanya Producció de la fitxa del
   model.** `frontend/src/components/model/ProductionTab.jsx:75-76` crida
   `commerce.workOrders.list({model})` i `commerce.deliveryNoteLines.list({model})` des
   d'una superfície purament tècnica. La UI només en pinta `number/kind/status/dn_number`
   (`ProductionTab.jsx:92-95`), però **al payload hi viatgen `unit_price`, `line_total`,
   `price_snapshot` i `internal_cost`** — aquest últim és el **COST INTERN** calculat com
   `minuts × TenantConfig.hourly_rate` (`backend/fhort/commerce/serializers.py:449-457`).
   És exactament el cas del brief: la pantalla no els pinta, i el tècnic els rep igual.
5. **🔴 `PATCH /api/v1/tenant-config/` és `IsAuthenticated` — d'escriptura.**
   `backend/fhort/pom/s2_views.py:339-341` posa `IsAuthenticated` a GET **i** a PATCH, i la
   llista de camps escrivibles (`s2_views.py:358-361`) inclou `hourly_rate`, `iban`,
   `tax_id`, `legal_name` i `legal_footer`. **Verificat en viu: HTTP 200 amb el token de
   tècnic.** Un tècnic pot llegir i reescriure la tarifa de cost i la identitat fiscal de
   l'emissor. És l'única escriptura sense gate que ha aparegut en tot el cens.
6. **La pantalla de gestió d'usuaris NO té el forat que es temia. El tall ja hi és.**
   `PATCH /api/v1/users/19/` → **403**; `POST /api/v1/users/bulk/` → **403**. Un tècnic
   **no** es pot apujar els permisos a si mateix (`accounts/views.py:118-123`). El
   «tall admin-only» de la peça 2 **ja està construït**: el que hi falta és a la vora
   (§4.3), no al centre.

---

## BLOC 1 — El sistema de capabilities actual

### 1.1 On viuen

| Què | On | Nota |
|---|---|---|
| Vocabulari de capacitats | `backend/fhort/accounts/capabilities.py:6-12` | 7 constants string |
| Ordre de columnes de la matriu | `capabilities.py:19-22` (tupla `CAPABILITIES`) | **l'ordre és dada** |
| Rol → capacitats base | `capabilities.py:26-32` (`ROLE_CAPABILITIES`) | 4 rols, config en CODI |
| Override per usuari | `accounts/models.py:16` — `UserProfile.permisos` `JSONField` | `{"grant":[…],"revoke":[…],"tasks":[…]}` |
| Resolució efectiva | `capabilities.py:42-54` — `(base \| grant) - revoke` | |
| Enforcement DRF | `capabilities.py:57-65` — `class HasCapability(BasePermission)` | |

Les 7 capacitats vigents: `execute_tasks`, `define_tasks`, `schedule_fittings`,
`close_gates`, `configure`, `view_team_tasks`, `manage_users` (`capabilities.py:6-12`).
Els 4 rols: `technician`, `product_manager`, `manager`, `admin` (`capabilities.py:26-32`).

**NO EXISTEIX cap taula de capabilities a la BD.** No hi ha model `Capability` ni
`RolePermission`: el vocabulari és codi i l'override és JSON dins `UserProfile.permisos`.

### 1.2 Com es comproven — SERVIDOR, no client

`HasCabability` llegeix `view.required_capability` i el compara amb
`get_capabilities(request.user)` (`capabilities.py:62-65`). Dos idiomes d'ús, tots dos vius:

- Subclasse amb l'atribut fix: `_DefineTasks` (`tasks/views_b.py:319-320`), `_ExecuteTasks`
  (`:419-420`), `_CloseGates` (`:653-654`), `_ScheduleFittings` (`:742-743`), `_Configure`
  (`:1012-1013`), `_ViewTeamTasks` (`:1140-1141`) → `@permission_classes([...])`.
- Assignació dins `get_permissions()`: `accounts/views.py:122`, `commerce/views.py:36`,
  `tasks/views_b.py:66/845/1055/1128`, `tenants/views_encarrecs.py:63-64`,
  `fitting/views.py:50-51` i `:74-75`.

⚠️ **Trampa del disseny** (`capabilities.py:58`): *«Sense declarar → com `IsAuthenticated`»*.
Una view que oblidi `required_capability` queda oberta i **no canta en vermell**.

El client fa **només amagatall d'UI**, sempre sobre `me.capabilities`
(`frontend/src/store/auth.js:85-113`) — 30+ punts, p.ex. `pages/Products.jsx:47`,
`pages/QuoteDetail.jsx:51`, `pages/UsersRoles.jsx:77`. És defensa en profunditat correcta,
**no** és l'única defensa. El client MAI decideix: el 403 el dona el servidor (§4.1).

### 1.3 Què costa una capability nova

Confirmat que **NO cal migració**: `permisos` ja és un `JSONField` (`accounts/models.py:16`)
i `ROLE_CAPABILITIES` és un diccionari en codi (`capabilities.py:26-32`). Tampoc cap seed.
Per afegir `COMERCIAL` calen exactament **4 tocs**:

1. `capabilities.py` — la constant + entrada a la tupla `CAPABILITIES:19-22` (la posició
   dins la tupla **és** la posició de la columna) + a quins rols la donem a `:26-32`.
2. **La columna de la matriu arriba SOLA.** `UsersRoles.jsx:76-77` ja no té còpia local:
   llegeix `capacitats` de `/vocabulari/`, que es publica des de la mateixa tupla
   (`backend/fhort/models_app/vocabulari_views.py:244`). Zero canvis a la pantalla.
3. **i18n ×3** — una clau `usersRoles.caps.comercial` a `frontend/src/i18n/{ca,en,es}.json`
   (bloc `caps`, ca.json:2140-2148). Sense ella la capçalera pinta la clau crua.
4. Els endpoints que la passen a exigir (§2, taula).

**Cost de la columna: pràcticament zero.** El cost real de la peça és el punt 4.

**Veredicte BLOC 1: llest.** El motor existeix, és de servidor i és extensible sense BD.
El que falta no és el mecanisme: és aplicar-lo a les LECTURES.

---

## BLOC 2 — El bloc comercial sencer

### 2.1 Frontend

Rutes (`frontend/src/App.jsx`): `comercial/productes`(465) `…/:id`(466)
`comercial/ofertes`(468) `…/:id`(469) `comercial/condicions-pagament`(471)
`comercial/comandes`(473) `…/:id`(474) `comercial/encarrecs`(476) `…/:id`(477)
`comercial/orfes`(479) `comercial/albarans`(481) `…/:id`(482) · `clients`(462)
`clients/:id`(463) · `suppliers`(459).

**Cap d'aquestes `<Route>` té guard de capability.** El patró de guard de ruta **NO EXISTEIX**
a `App.jsx`: l'únic embolcall és el d'autenticació (`App.jsx:409`).

Menú (`components/layout/navGroups.js:47-57`): la secció `nav.section_comercial` llista les
9 entrades **sense `cap`**, i el comentari `:44-46` ho diu explícitament — *«El gate de tier
del mòdul arriba a B5; de moment sense `cap`»*. Contrast: `configuracio/usuaris` sí que en té
(`navGroups.js:72`, `cap:'manage_users'`).

### 2.2 Backend — protecció per endpoint (verificat en viu)

Router: `backend/fhort/commerce/urls.py:13-36`. Mixin del patró:
`commerce/views.py:31-37` (`list`/`retrieve` → `IsAuthenticated`; la resta → `CONFIGURE`).

| Endpoint | Lectura | Escriptura | Font |
|---|---|---|---|
| `commerce/units/` | **AUTH** | ReadOnly | `views.py:40-45` |
| `commerce/products/` | **AUTH** | CONFIGURE | `:56-70` |
| `commerce/recipe-lines/` | **AUTH** | CONFIGURE | `:73-76` |
| `commerce/product-suppliers/` | **AUTH** | CONFIGURE | `:79-82` |
| `commerce/product-components/` | **AUTH** | CONFIGURE | `:85-88` |
| `commerce/price-exceptions/` | **AUTH** | CONFIGURE | `:91-94` |
| `commerce/payment-terms/` | **AUTH** | CONFIGURE | `:48-53` |
| `commerce/quotes/` (+`send`,`convert`) | **AUTH** | CONFIGURE | `:99-111`,`:122`,`:154` |
| `commerce/quotes/{id}/pdf/` | **AUTH** 🔴 | — | `:107-111`,`:140-152` |
| `commerce/quote-lines/` | **AUTH** | CONFIGURE | `:170-175` |
| `commerce/quote-line-intents/` (+`bulk`) | **AUTH** | CONFIGURE | `:178-216` |
| `commerce/orders/` | **AUTH** | CONFIGURE | `:221-234` |
| `commerce/orders/{id}/pdf/` | **AUTH** 🔴 | — | `:231-234`,`:246-256` |
| `commerce/order-lines/` | **AUTH** | CONFIGURE | `:259-270` |
| `commerce/order-lines/{id}/allocation/` | **AUTH** | — | `:267-300` |
| `…/assign-model/`, `…/assign-models/` | — | CONFIGURE | `:302-345` |
| `commerce/work-orders/` | **AUTH** | — | `:348-365` |
| `commerce/work-orders/orphaned/` | **AUTH** | — | `:358`,`:367-391` |
| `…/{id}/review/`,`unassign/`,`reattach/` | — | CONFIGURE | `:363-364` |
| `…/{id}/close/` | — | DEFINE_TASKS | `:363-364`,`:407` |
| `…/{id}/reattach-candidates/` | ⚠️ **DEFINE_TASKS** | — | `:363-364`,`:439` |
| `commerce/expenses/` | **AUTH** | CONFIGURE | `:481-487` |
| `commerce/delivery-notes/` | **AUTH** | CONFIGURE | `:495-510` |
| `…/{id}/pdf/` | **AUTH** 🔴 | — | `:507-510` |
| `…/billable/`,`generate/`,`issue/` | — | CONFIGURE | `:512-528` |
| `commerce/delivery-note-lines/` | **AUTH** | CONFIGURE | `:637-…` |
| `customers/` | **AUTH** | CONFIGURE | `tasks/views_b.py:793`,`:842-845` |
| `suppliers/` | **AUTH** | ⚠️ **SCHEDULE_FITTINGS** | `tasks/views_b.py:746`,`:764-767` |
| `tenant-config/` | **AUTH** | 🔴 **AUTH** | `pom/s2_views.py:339-341` |

**AUTH** = `IsAuthenticated` sol. **Cap endpoint comercial exigeix cap capability per llegir.**

Dues anomalies menors de coherència, anotades i **fora de scope**:
`reattach-candidates` és una lectura que ha caigut a `DEFINE_TASKS` per la forma del `if`
(`views.py:357-365`: només `list`/`retrieve`/`orphaned` s'exclouen); i l'escriptura de
Proveïdors va per `SCHEDULE_FITTINGS` (`views_b.py:767`) i no per `CONFIGURE` com Clients.

### 2.3 Prova en viu — token de tècnic (`execute_tasks` sol)

Totes **200**: `commerce/products` · `quotes`(8) · `orders`(2) · `work-orders`(5) ·
`expenses` · `delivery-notes`(2) · `payment-terms`(3) · `product-suppliers` ·
`price-exceptions` · `quote-lines`(13) · `order-lines`(3) · `delivery-note-lines`(4) ·
`units`(7) · `quote-line-intents` · `work-orders/orphaned` · `customers`(3) · `suppliers`(1)
· `tenant-config` · `users`.

Mostres reals rebudes pel tècnic:
- `products` → `"base_price":"20.00"`, `"sale_rate"`, `"markup_pct"`, `"tax_rate"`
- `order-lines` → `"unit_price":"120.00"`, `"line_total":"240.00"`
- `quotes` → clients, estats i imports de 8 ofertes
- `GET commerce/quotes/12/pdf/` → **200 `application/pdf`, 108.509 bytes** (l'oferta sencera)

**Veredicte BLOC 2: cal la peça.** L'escriptura està raonablement gatejada; la lectura
—que és exactament el que el requisit de PROD prohibeix— no ho està enlloc.

---

## BLOC 3 — 🔴 Preus i costos FORA del bloc comercial

Aquest és el forat que el menú no tapa. Té dues formes molt diferents.

### 3.1 Serializers NO comercials que emeten diner

El cens complet és **curt** — només dos:

1. **`TenantConfigSerializer.hourly_rate`** (`backend/fhort/pom/s2_serializers.py:210-211`) —
   *«tarifa interna de cost per hora»*. El serveix `tenant_config_view`
   (`pom/s2_views.py:339-341`), que és l'endpoint que **TOTA** la SPA consulta per saber
   `unitat_mesura`. Un tècnic que obre qualsevol pantalla de mesures rep la tarifa de cost
   de la casa al mateix payload. Verificat en viu (200; avui `null` en aquest tenant —
   quan es fixi a PROD, serà una xifra real).
2. **`CustomerSerializer.descompte_pct`** (`tasks/serializers_b.py:158`, camp a
   `tasks/models.py:335`) — % de descompte comercial. Viatja amb `condicions_pagament`,
   `email_facturacio`, `nif`, `tax_regime`, `payment_method`, `payment_terms` i els
   comptadors `quotes_sent`/`quotes_accepted`/`orders_open` (`serializers_b.py:150-167`).
   `SupplierSerializer` porta el bessó de compra: `condicions_compra`
   (`serializers_b.py:130-136`).

Fora d'això, `NO EXISTEIX` cap altre camp econòmic en serializers no comercials: el
`grep` de `unit_price|line_total|base_price|sale_rate|markup|tax_rate|subtotal|amount|cost`
sobre `models_app`, `planning`, `pom`, `fitting`, `tasks` i `tenants` només retorna
comptadors (`'total': qs.count()`, `models_app/views.py:269`) i toleràncies en cm.

**Fals positiu descartat:** `UserProfile.cost_hora` (`accounts/models.py:14`) apareix a
`UserProfileSerializer` (`accounts/serializers.py:109`), **però aquest serializer no
l'usa cap view** (grep sense resultats fora de la seva definició) → és codi mort. `/me/`
va per `MeSerializer` (`serializers.py:27-34`), que **no** inclou `cost_hora`.
Efecte lateral viu: `frontend/src/pages/UserProfilePage.jsx:67` pinta `profile.cost_hora`
d'una resposta de `me()` que mai el porta → **fila sempre buida** (fora de scope, anotat).

### 3.2 🔴 Superfícies TÈCNIQUES que criden endpoints COMERCIALS

Aquí és on el diner arriba de debò al tècnic. Cinc punts, tots amb `?model=` o equivalent:

| # | Superfície tècnica | Crida | Què arriba al payload |
|---|---|---|---|
| 1 | **Fitxa del model → tab Producció** `components/model/ProductionTab.jsx:75` | `commerce.workOrders.list({model})` | `price_snapshot` (`unit_price`,`tax_rate`,`product_code`) + `adjustments[].amount` — `commerce/serializers.py:352-355`, `:329-335` |
| 2 | **Fitxa del model → tab Producció** `ProductionTab.jsx:76` | `commerce.deliveryNoteLines.list({model})` | `unit_price`, `line_total`, `internal_minutes` i **`internal_cost`** — `commerce/serializers.py:459-466` |
| 3 | **Fitxa del model → menú d'accions** `components/model/ActionsMenu.jsx:86` | `commerce.orders.list({customer,status:'OPEN'})` | `subtotal`, `tax_amount`, `total`, venciments — `serializers.py:316-321` |
| 4 | **Llistat de models (assignació)** `pages/Models.jsx:142` | `commerce.quoteLineIntents.list()` | línia d'oferta i el seu context |
| 5 | **Dashboard (home de tothom)** `pages/Dashboard.jsx:233` | `customers.list({page_size:200})` | `descompte_pct` + fiscal de TOTS els clients |

També `components/CustomerSelector.jsx:35`, que fa servir `ModelWizard`
(`pages/ModelWizard.jsx:241`) i `SizeMapSetup.jsx:567` — camins purament tècnics.

**El cas 2 és el més net del brief.** La UI llegeix NOMÉS `l.dn_number` i `l.dn_status`
(`ProductionTab.jsx:79`) i pinta tres files de traçabilitat (`:90-96`). El backend, però,
retorna la línia sencera. **Verificat en viu** amb el token de tècnic:

```
GET /api/v1/commerce/delivery-note-lines/?page_size=2   → 200
{ "description":"Mesurar prenda · BRW-26-SS-0002",
  "unit_price":"30.00", "line_total":"30.00",
  "internal_minutes":"574.00", "internal_tecnic":null, "internal_cost":null }
```

`internal_cost` és `null` només perquè `hourly_rate` encara és `null` en aquest tenant
(`commerce/serializers.py:449-457`: `rate is None → None`). **El dia que a PROD s'ompli la
tarifa, aquest camp passa a ser el cost intern real i el tècnic ja el rep.** El comentari
del propi codi ho diu: *«columna interna de cost, NOMÉS pantalla, mai al PDF»*
(`serializers.py:425-427`) — la reserva es va fer contra el PDF, no contra el payload.

**Veredicte BLOC 3: cal la peça, i el gate de menú NO n'hi ha prou.** Amagar la secció
Comercial no toca cap dels 5 punts: tots viuen a pantalles tècniques que han de seguir
funcionant. Cal capar **el payload**, no la navegació.

---

## BLOC 4 — La pantalla de gestió d'usuaris

### 4.1 El que diu el codi

`UserViewSet` (`accounts/views.py:98-220`), `get_permissions()` a `:118-123`:
`list`/`retrieve` → `IsAuthenticated`; **tota la resta → `MANAGE_USERS`**. Cobreix
`create`(:136), `update`/`partial_update`, `bulk`(:161-163) i `reset-link`(:210-215).
El serializer també es tria per capacitat (`:125-134`): sense `MANAGE_USERS`, la lectura
cau a `UserListSerializer` (`serializers.py:71-82` — 6 camps, **sense** `permisos` ni
`capabilities`); amb ella, a `UserAdminSerializer` (`:113-141`).

### 4.2 El que diu la crida real ✅

Amb el token del tècnic 19, contra `127.0.0.1:8001`:

| Crida | Resultat |
|---|---|
| `PATCH /api/v1/users/19/` `{"rol_nom":"__no_such_role__"}` | **403** `{"detail":"No té permisos per realitzar aquesta acció."}` |
| `POST /api/v1/users/bulk/` `{"user_ids":[19],"action":"__bogus__"}` | **403** (idem) |
| `POST /api/v1/commerce/products/` `{}` | **403** (idem) |
| `PATCH /api/v1/tenant-config/` `{"__camp_inexistent__":1}` | 🔴 **200** |

**Mètode de la prova, i per què no ha calgut cap rollback:** cada payload està construït per
**fallar la validació DESPRÉS del permís**. Si el gate aguanta → `403` sense arribar mai al
serializer; si el gate cedeix → `400` de validació, també sense escriure. Un `403` prova el
tall i un `400` n'hauria provat l'absència, i cap dels dos camins toca la BD. El cas de
`tenant-config` va amb un camp que **no és a la llista blanca** de `s2_views.py:358-361`, per
tant el `setattr` no s'executa i el `config.save()` desa el registre igual que estava: el
**200** demostra l'autoritat d'escriptura sense exercir-la. **Cap dada del tenant s'ha
modificat en aquesta diagnosi.**

### 4.3 Conclusió i la vora que sí que falta

**Un tècnic autenticat que conegui la crida NO es pot canviar els permisos a si mateix.**
El tall admin-only del centre de la pantalla ja existeix i funciona al servidor.

Queden tres vores, per ordre de gravetat:

1. 🔴 **`PATCH /api/v1/tenant-config/` sense gate** (`pom/s2_views.py:339-341`). No és la
   matriu d'usuaris, però és configuració del tenant i porta la tarifa de cost i la
   identitat fiscal (`hourly_rate`, `iban`, `tax_id`, `legal_name`, `legal_footer` —
   `s2_views.py:358-361`). **La sola escriptura oberta de tot el cens.** La UI que l'edita
   (`pages/GeneralConfig.jsx:43`) sí que demana `configure`; el backend, no.
2. 🟡 `GET /api/v1/users/` obert a qualsevol autenticat (`accounts/views.py:120-121`) —
   deliberat (el selector de responsable) i el serializer mínim no filtra `permisos`. **Sense
   risc**, però és el motiu pel qual la ruta `/configuracio/usuaris` no cal guardar-la:
   sense `manage_users` la matriu no rep ni columnes ni dades.
3. 🟡 `Montse` (id 13, rol `manager`) té `manage_users` **per override**
   `permisos.grant` — legítim segons `capabilities.py:42-54`, però convé que Agus ho sàpiga:
   avui la gestió d'usuaris no és estrictament "rol admin", és "qui tingui la capability".

**Veredicte BLOC 4: la peça 2 és MOLT més petita del previst** — el tall existeix; el que
cal és tapar `tenant-config`.

---

## TAULA FINAL — riscos i estat

| # | Risc | Estat | Ancoratge |
|---|---|---|---|
| R1 | Tècnic llegeix **tot** el bloc comercial (preus, imports, marges) | 🔴 **OBERT** — 16 col·leccions a 200 | `commerce/views.py:31-37` |
| R2 | Tècnic es descarrega els **PDF** d'oferta/comanda/albarà | 🔴 **OBERT** — verificat 200, 108 KB | `views.py:107-111`,`:231-234`,`:507-510` |
| R3 | **Cost intern** (`internal_cost`) al payload d'una pantalla tècnica | 🔴 **OBERT** — fitxa del model | `serializers.py:449-457` + `ProductionTab.jsx:76` |
| R4 | **`price_snapshot`** i `adjustments.amount` a la fitxa del model | 🔴 **OBERT** | `serializers.py:352-355` + `ProductionTab.jsx:75` |
| R5 | **`hourly_rate`** a `/tenant-config/`, que llegeix tota la SPA | 🔴 **OBERT** | `s2_serializers.py:210-211` |
| R6 | **`PATCH /tenant-config/` sense gate** (escriu tarifa i dades fiscals) | 🔴 **OBERT** — verificat 200 | `s2_views.py:339-341`,`:358-361` |
| R7 | `descompte_pct` + fiscal de clients al **Dashboard de tothom** | 🟠 OBERT | `serializers_b.py:158` + `Dashboard.jsx:233` |
| R8 | Menú Comercial i rutes visibles per a tothom | 🟠 OBERT — cosmètic | `navGroups.js:47-57`, `App.jsx:465-484` |
| R9 | Escalada de privilegis via `/users/` | ✅ **TANCAT** — 403 verificat | `accounts/views.py:118-123` |
| R10 | Escriptura comercial per un tècnic | ✅ **TANCAT** — 403 verificat | `commerce/views.py:31-37` |
| R11 | `reattach-candidates` (lectura) gatejat `DEFINE_TASKS` | ⚪ anomalia, fora scope | `views.py:357-365` |
| R12 | Escriptura de Proveïdors per `SCHEDULE_FITTINGS` | ⚪ anomalia, fora scope | `views_b.py:764-767` |
| R13 | `UserProfilePage` pinta `cost_hora` que `/me/` no envia | ⚪ fila morta, fora scope | `UserProfilePage.jsx:67` |

---

## 💡 PROPOSTA (a validar) — cost del Patró B en dues peces

> Decisió humana (Patró C). Això és una estimació de volum, no un disseny aprovat.

### Peça 1 — capability `COMERCIAL` · ~1 sessió

**Backend (el gruix):**
- `capabilities.py` — constant + tupla `:19-22` + `ROLE_CAPABILITIES:26-32`. **Pregunta per
  a Agus:** ¿`manager` la té per defecte, o només `admin` i qui la rebi per `grant`?
- Un mixin bessó de `_ConfigureWriteMixin` que posi `COMERCIAL` **també a `list`/`retrieve`**,
  aplicat a les 16 registres de `commerce/urls.py:13-36` → toca ~14 classes de
  `commerce/views.py`, més les 3 `@action` de PDF (`:140`,`:246`, DN) i `billable`.
- 🔑 **El nus de la peça:** els 5 punts del §3.2. Un `403` sec trencaria la fitxa del model
  per a tots els tècnics. Cal decidir per a cadascun: *(a)* podar els camps econòmics del
  serializer quan qui llegeix no té `COMERCIAL`, o *(b)* un endpoint de traçabilitat
  no-comercial. La sortida barata i honesta per als casos 1-2 és **(a)**, perquè la UI ja
  només consumeix `number/kind/status/dn_number` (`ProductionTab.jsx:79`,`:92-95`): podar no
  trenca res del que es pinta avui. El cas 5 (Dashboard) demana podar `CustomerSerializer`.
- `TenantConfigSerializer` — treure `hourly_rate` del payload sense `COMERCIAL`
  (`s2_serializers.py:210-211`); és un camp, no una pantalla.

**Frontend:** `cap:'comercial'` a les 9 entrades de `navGroups.js:47-57`; i18n ×3
(`usersRoles.caps.comercial`). La columna de la matriu **arriba sola** (§1.3).
**Guard de ruta:** el patró NO EXISTEIX a `App.jsx` — si es vol, és feina nova; si el
backend poda, es pot deixar per a una peça posterior.

**Gates:** `manage.py check` + `npm run build` + córrer els tests de `commerce/` que ja
existeixen (`test_batch_assign.py`, `test_intents_reattach.py`, `test_orphan_iva.py`,
`test_unassign.py`), que passen per aquests endpoints i cantarien si el gate els talla.

### Peça 2 — tall admin-only de la gestió d'usuaris · **~1 hora**

Molt més petita del que el brief preveia: **el tall ja hi és i està verificat** (§4.2).
El que queda és una sola línia de fons: posar `HasCapability`+`CONFIGURE` (o `MANAGE_USERS`,
decisió d'Agus) al **PATCH** de `tenant_config_view` mantenint el **GET** obert —
`pom/s2_views.py:339-341` és un `@api_view(['GET','PATCH'])` amb un
`@permission_classes([IsAuthenticated])` únic, o sigui que el tall va per branca de mètode
dins la funció. Opcionalment, `cap:'manage_users'` a la `<Route>` de `/configuracio/usuaris`
(cosmètic: la matriu ja arriba buida sense la capability).

**Ordre suggerit:** Peça 2 primer (una hora, tapa l'única escriptura oberta), després Peça 1.
