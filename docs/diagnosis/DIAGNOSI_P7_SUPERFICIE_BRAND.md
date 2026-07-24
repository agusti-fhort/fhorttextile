# DIAGNOSI P7 — La superfície del Brand (Patró A, read-only)

Data: 2026-07-24 · Entorn: STAGING (`/var/www/ftt-staging`, branca `dev` ≡ `origin/dev`, HEAD `be1ff61`).
Tipus: **lectura + verificació empírica**. Cap canvi de codi en aquesta fase.

Lleis que governen (DECISIONS.md §Federació Brand↔Studio, no re-obertes):
el Brand veu RECURS (mai persones ni temps) · el token governa el PONT, mai la capacitat de
treballar · l'assignació és sobirania del Brand, per model · el traspàs físic segueix sent del
Studio · referències per **codi nu**, mai FK · `tenants/` és la casa del cross-tenant.

---

## A1 — TenantLink des d'una petició de TENANT

**Pregunta:** `fhort.tenants` és a `SHARED_APPS` (settings.py:36-38) i no a `TENANT_APPS`
(settings.py:62-75) → les seves taules només existeixen a `public`. Es pot consultar
`TenantLink` des d'un request de tenant **sense** `schema_context` explícit?

**Verificació empírica** (`manage.py shell`, staging, dades reals):

```
=== tenants ===
  FTT | fhort | FHORT Management | tipologia=estudi | estat=actiu
  LOS | los   | LOSAN            | tipologia=marca  | estat=onboarding
  SYS | public| FHORT System     | tipologia=estudi | estat=actiu
=== TenantLink al public ===
  LOS -> FTT | ACTIU | token_len=43
=== A1: lectura des de DINS d'un tenant (schema_context) ===
  schema=los   search_path=los, public   TenantLink.count()=1  Client.count()=3
  schema=fhort search_path=fhort, public TenantLink.count()=1  Client.count()=3
```

I la comprovació que tanca el dubte (cap taula ombra al schema del tenant):

```sql
SELECT table_schema, table_name FROM information_schema.tables
 WHERE table_name IN ('tenants_tenantlink','tenants_client');
-- ('public', 'tenants_client')
-- ('public', 'tenants_tenantlink')
```

**VEREDICTE A1: SÍ, consultable directament. NO cal cap lectura delegada.**
Raó: django-tenants fixa `search_path = <tenant>, public`; `tenants_tenantlink` i
`tenants_client` viuen **només** a `public` i no hi ha homònima al schema del tenant que les
pugui ombrejar. Un `TenantLink.objects.filter(...)` dins d'una view de tenant resol contra
`public` per si sol. El patró `invoice_pdf`/delegat **no és necessari** i seria soroll.

Precedent ja viu del mateix principi: `TenantConfigSerializer.get_tipologia` (commit `4f34e7c`,
`pom/s2_serializers.py:191`) llegeix `request.tenant` — l'objecte `Client` que django-tenants ja ha
resolt — en comptes de fer cap consulta cross-schema. **`request.tenant` és la font barata del
codi del tenant actual** i s'usarà com a tal a P7 (mai el payload).

---

## A2 — `/me` avui

`accounts/views.py:42-60` (`me_view`): retorna `MeSerializer(request.user).data` + una injecció
directa a `data` (`legal_pending`), amb el comentari explícit que és "l'única incursió al tenant".
**Aquest és el precedent literal per a la injecció del tenant** (B1a): la view afegeix la clau, no
el serializer, i així no cal context ni tocar el contracte del `ModelSerializer`.

`MeSerializer` (`accounts/serializers.py:13-34`) — camps actuals:
`id · profile_id · username · first_name · last_name · email · full_name · avatar_url ·
nom_complet · rol_nom · color_avatar · capabilities`.
**No hi ha res del tenant.** Ni nom, ni codi, ni tipologia.

**El store SÍ descarta els camps nous.** `frontend/src/store/auth.js`, `fetchMe()` fa una
**còpia explícita camp a camp** cap a `user`:

```js
set({ user: { id, username, nom_complet, rol_nom, color_avatar, capabilities } })
```

Un `tenant` nou a la resposta **no arribaria enlloc** sense tocar aquest bloc → B2 és obligatori,
no cosmètic. (`fetchMe` sí retorna `data` sencer al cridant, però cap consumidor l'aprofita.)

**Segona font de `tipologia` ja existent:** `GET /api/v1/tenant-config/` l'exposa des de
`4f34e7c`, i `Customers.jsx:72` ja hi depèn. P7 no la retira (fora d'abast, i és la que sosté el
fix del self-client); queda **anotada com a convergència pendent**: dues portes per al mateix fet.
La d'identitat ha de ser `/me`.

---

## A3 — El self-customer al tenant

**Ja resolt en gran part per la sessió anterior** (commits `006c0f2`, `b29410e`, `6c5ab64`, avui):

| Superfície | Estat |
|---|---|
| `Customers.jsx` | En tenant `marca` ja **no** s'envia `exclude_self` → el self es veu. Guard anti-flash: no demana la llista fins tenir la tipologia (`:84,96`). Badge `({t('clients.self')})` a la columna codi (`:130`). Fila del self sense Desactivar/Esborrar (`:158`). |
| Backend | Blindatge real: `destroy` d'un `is_self` → 409, `active=false` sobre `is_self` → 409, tots dos amb `code: self_customer_protected`; `is_self` read-only al serializer (`tasks/views_b.py`, `tasks/serializers_b.py`). 11 tests a `tasks/tests_self_customer.py`. |
| `CustomerDetail.jsx` | Tab Comercial amagat si `is_self` (`:66-69`). |
| `CustomerSelector` / `Dashboard` | Deliberadament **no** filtren el self (comentats a `6c5ab64`). |

**Què queda per a B5, doncs:** molt poc, i ha de ser codi mínim. La i18n `clients.self` avui diu
`propi / self / propio` — un matís tipogràfic, no una identitat. El forat real que queda és que
**a la fitxa (`CustomerDetail`) el self no es distingeix de cap altre client**: entres i no saps que
estàs mirant la teva pròpia casa. B5 = badge explícit ("Aquesta casa") a la llista i a la fitxa,
amb clau i18n pròpia. Res més: **no cal pantalla nova** (les dades pròpies — nom, codi — ja hi són).

---

## A4 — Superfície de models al Brand

**Selecció múltiple: JA EXISTEIX i és madura.** `pages/Models.jsx`:
- `selected` (Set d'ids) + checkbox per fila (`:458`) + select-all de pàgina (`:297`).
- **Mode CONJUNT filtrat** estil Gmail (`selectAllFilter` + `excludeIds`, `:36-37,304-324`):
  "els N del filtre" sense materialitzar la llista al client.
- **Accions en bloc: `components/model/ActionsMenu.jsx`** — el desplegable "Accions (N)".
  El seu contracte és `targets` (llista d'objectes) o `selectionSet` (`{filters, excludeIds, count}`).
  En mode conjunt **només** "assignar tasques" s'escala; la resta s'inhabiliten amb `conjuntHint`.

→ **El lloc de "Assignar a recurs" és `ActionsMenu`**, com una entrada més de `items` (`:201-208`),
amb el seu `Modal`. No s'inventa cap barra nova. Segueix el patró de `assign_order`: una entrada,
un `Modal` amb un `<select>`, i `runBulk`/crida única.
Deliberadament **NO** s'escala al mode conjunt en aquest sprint (mateix `conjuntHint` que
production/fitting/assign_order): l'endpoint pren `model_ids` explícits.

**Columna "Recurs": el camp NO viatja a la llista.** `ModelListSerializer`
(`models_app/serializers.py:87-135`) enumera els camps un a un i `studio_assignat` no hi és
→ cal afegir-l'hi.

**Escriptura per API, avui:** `ModelDetailSerializer` fa `fields = '__all__'`
(`serializers.py:250-255`) → **`studio_assignat` JA és escrivible per `PATCH /api/v1/models/<id>/`**.
Això no és la palanca que la llei demana: és una via oberta, sense guard de vincle, per a qualsevol
usuari que pugui editar un model. **BANDERA 1** (sota). La porta legítima ha de ser l'endpoint
en bloc de B1d, amb validació del `TenantLink` ACTIU.

`ModelViewSet` (`models_app/views.py:129`) ja té `@action(detail=False, ...)` (`fase-counts`,
`garment-counts`) → `assignar-recurs` hi encaixa sense tocar `urls.py`.

---

## A5 — Permisos

Vocabulari a `accounts/capabilities.py:6-17`. La capacitat que governa la **configuració /
mestres del tenant** és `CONFIGURE` (`"configure"`), i és consistent a tot el projecte:
- `CustomerViewSet` escriptura → `CONFIGURE` (`tasks/views_b.py:761,870`)
- Tot el mòdul Comercial (mestres i actes comercials) → `CONFIGURE` (`commerce/views.py`, 15+ punts)
- `promoure-a-item` → `CONFIGURE`
- Sidebar: `cap: 'configure'` ja governa la secció Sistema (`Sidebar.jsx:72-73`)

Rols que la tenen: **només `admin`** (`ROLE_CAPABILITIES`, `capabilities.py:20-26`), més overrides
per usuari (`permisos.grant`).

→ **B1b/c/d i el menú de B3 es gategen amb `CONFIGURE`.** La lectura de `/recursos/` es manté a
`IsAuthenticated` (patró de la casa: llegir obert, escriure gated)… **excepte el token**, que no
és lectura de catàleg sinó una credencial (vegeu B1b).

---

## A6 — i18n

`frontend/src/i18n/{ca,en,es}.json` · **186 claus de primer nivell a cadascun** (paritat exacta
avui). Patró: un namespace per pantalla (`suppliers`, `clients`, `models_list`, `models_filters`,
`model_sheet`, …) + `nav.*` per a les entrades de menú i `nav.section_*` per als grups.

**COL·LISIÓ DE NOM detectada:** `nav.suppliers` ja és **"Proveïdors / Suppliers / Proveedores"** i
és una pàgina viva i diferent (`pages/Suppliers.jsx` — catàleg de tallers/fàbrica del Studio,
`SupplierViewSet`, escriptura gated `SCHEDULE_FITTINGS`). Dues entrades de menú titulades
"Proveïdors" amb significats diferents serien un error d'ús, no un detall estètic.

→ **Decisió d'implementació (desviació anotada):** la pantalla nova del Brand es diu **"Recursos"**
(`nav.recursos`, namespace i18n `recursos`), que a més és **exactament el mot de la llei**
("el Brand veu RECURS") i el mot de l'endpoint que el brief ja fixa (`/api/v1/recursos/`).
Canviar-ho a "Proveïdors" seria una sola cadena a 3 fitxers si el CTO ho prefereix.

---

## Banderes (anotades, no tocades)

1. **`studio_assignat` és escrivible pel CRUD genèric** (`ModelDetailSerializer.fields='__all__'`).
   Qualsevol `PATCH /api/v1/models/<id>/` el pot fixar a qualsevol codi, sense validar que existeixi
   un `TenantLink` ACTIU. És el mateix gènere de forat que la llei S24b va tancar per a
   `size_run_model` (`validate()` a `serializers.py:230-248`). P7 hi construeix la porta legítima al
   costat; **tancar la via oberta (read-only al serializer) és una decisió del CTO**, perquè trencaria
   qualsevol client que avui l'escrigui per aquest camí.
2. **Dues fonts de `tipologia` al frontend** (`/api/v1/tenant-config/` i, després de B1a, `/me`).
   La d'identitat ha de ser `/me`; la convergència de `Customers.jsx` cap a `isBrand()` queda per a
   un sprint d'higiene (avui `Customers.jsx` funciona i no es toca — codi mínim).
3. **`los` és `estat='onboarding'`**, no `actiu`. No bloqueja res de P7 (cap gate de P7 llegeix
   `estat`), però és el que caldrà mirar abans del go-live del Brand a PROD.
4. **🔴 FK cross-schema per id nu: `backoffice.BackofficeUser.usuari` → `auth_user`** (trobada
   durant l'assaig del B7, en netejar un usuari de proves). `fhort.backoffice` és SHARED
   (public-only) però `auth_user` viu a `public` **i** a cada tenant. Amb `search_path='<tenant>,
   public'`, el *collector* d'esborrat de Django llegeix `backoffice_backofficeuser` de `public` i
   l'aparella amb l'`auth_user` del TENANT **per id nu**. Comprovat en viu:

   ```
   los.auth_user:  id=2 → qa.p7@fhort.test      (usuari de tenant)
   public.backoffice_backofficeuser: (id=1, usuari_id=2, 'ADMIN')  → a.devant, usuari de PUBLIC
   → DELETE de l'usuari 2 de `los`:
     ProtectedError: ... referenced through protected foreign keys: 'BackofficeUser.usuari'
   ```
   Aquí el resultat és **segur** (PROTECT bloqueja un esborrat legítim: soroll, no dany). El que
   preocupa és el germà: **`AccioLog.usuari` és `SET_NULL`** (`backoffice/models.py:60`) — el
   mateix encreuament, però en comptes de bloquejar, **posaria a NULL files del log del backoffice
   quan s'esborra un usuari d'un tenant amb l'id coincident**, en silenci i sense cap traça.
   Fora de l'abast de P7 (cap peça d'aquest sprint hi toca) i **no introduït per P7**, però és una
   frontera cross-tenant trencada: `backoffice` hauria d'apuntar a un usuari de `public`
   explícitament, no a `AUTH_USER_MODEL` resolt pel `search_path`. **Decisió del CTO.**

---

## Assaig manual a staging (B7) — executat 2026-07-24 amb el codi d'aquest sprint

Servei `ftt-staging.service` reiniciat · `/api/schema/` 200 des dels dos hosts
(`staging.fhorttextile.tech` → `fhort`/FTT · `los.fhorttextile.tech` → `los`/LOS).
Usuari d'assaig `qa.p7@fhort.test` (rol admin) creat als dos schemas i **esborrat en acabar**.

| # | Pas | Resultat real |
|---|---|---|
| 1 | `/me` com a LOS | `tenant = {'nom':'LOSAN','codi_tenant':'LOS','tipologia':'marca'}` ✓ |
| 2 | `GET /api/v1/recursos/` | 1 recurs: `FTT · FHORT Management · ACTIU · 2026-07-23`. **0 aparicions de `token`** ✓ |
| 3 | Guards de l'alta | duplicat → **409** `link_exists` · destí inexistent → **400** `invalid_studio` · auto-vincle → **400** `self_link` |
| 4 | Models del Brand | 50 models a `los`, **tots amb `studio_assignat=''`** (línia base neta) |
| 5 | Assignar 3 (ids 7, 55, 54) | `{assignats: 3, ja_hi_eren: 0, no_trobats: []}` |
| 5b | Repetir la mateixa acció | `{assignats: 0, ja_hi_eren: 3}` — el compte no s'infla ✓ |
| 6 | Auditoria a BD (`schema los`) | 3 files amb `studio_assignat='FTT'` (`LOS-ASSAIG-0002/0049/0050`) · 47 sense |
| 7 | `instantiate_external_models --brand LOS --studio FTT` (dry-run) | `models al Brand: 50 · assignats a FTT: 3` · **`llegits (assignats): 3`** · `a crear: 0 · saltats (ja hi són): 3` |
| 8 | **La llei de les dues claus, en viu** | aturar → `ATURAT` · assignar amb pont aturat → **409** `link_not_active` · **retirar** amb pont aturat → **200**, 1 retirat · reactivar → `ACTIU` · re-assignar → 1 ✓ |
| 9 | Un ESTUDI (FTT) davant la superfície | `/me` diu `tipologia='estudi'` · `GET /recursos/` → **403** · `POST /recursos/` → **403** |

**Nota del pas 7:** `a crear: 0` és correcte i esperat — l'assaig de federació del 2026-07-23 ja
va instanciar els 50 models sintètics a `fhort`, i el command és idempotent per `codi_intern`. El
que aquest sprint havia de demostrar és la xifra de l'esquerra: **el traspàs llegeix exactament
els 3 models que el Brand ha assignat des de la UI**, no els 50 del pont.

**Estat de staging en acabar (restaurat):** vincle `LOS→FTT` **ACTIU**, 3 models assignats a FTT,
cap usuari d'assaig viu.

---

## Veredicte de la Fase A

**Cap bloquejant.** Les 4 lleis tenen suport tècnic verificat:
- el vincle és llegible des del tenant sense cap patró nou (A1);
- la injecció a `/me` té precedent literal a la mateixa view (A2);
- la superfície de selecció en bloc ja existeix i té el punt d'entrada correcte (A4);
- el gate és `CONFIGURE`, sense ambigüitat (A5).

Es procedeix a la Fase B amb dues desviacions declarades: **"Recursos" en comptes de "Proveïdors"**
(col·lisió real, A6) i **B5 reduït a un badge** (el gruix ja el va fer la sessió d'avui, A3).
