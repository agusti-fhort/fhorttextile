# BIBLIOTECA DE NOMENCLATURA · EDITAR UN ÀLIES

**Data:** 2026-08-23 · **Entorn:** `/var/www/ftt-staging`, branca `dev` · **Patró B**
**Pantalla:** Clients > Tècnic > Biblioteca de nomenclatura (`CustomerDetail.jsx`)
**3 commits + acta. Cap push. PROD no s'ha tocat** (viatjarà amb el tren de la fase D).

| Control | Resultat |
|---|---|
| `manage.py check` | **net** |
| `fhort.pom.test_alies_edicio` (endpoint) | **8 tests · OK** |
| `node --test src/utils/edicioAlies.test.js` (component) | **10 tests · OK** |
| `npx eslint` dels tres fitxers tocats | **0 errors** |
| `npm run build` | **OK** · `systemctl restart ftt-staging` fet |
| i18n ca/en/es | **paritat verificada** |
| Altres suites | **cap** |

---

## 1 · El gest

Llapis Tabler outline a cada fila, **al costat de la paperera i abans**: d'esquerra a dreta, de
menys a més irreversible. Editant, els dos botons passen a ser **desar** i **cancel·lar**, i la
paperera desapareix — esborrar el que estàs editant no és un gest que aquesta pantalla hagi
d'oferir.

**Inline i no modal**: el que s'edita són tres textos i un POM, i la fila del costat és el
context que fa entendre què s'està canviant.

S'editen: **descripció EN** · **descripció local + idioma** · **POM canònic** (amb el **mateix
cercador** que el formulari d'alta, `PomPicker` — el catàleg té 165 POMs i un desplegable pla no
és consultable).

**Esc cancel·la · Enter desa**, i les dues tecles viuen al teclat de la **fila**, no de la
finestra: capturades globalment tancarien l'edició des de qualsevol racó de la pantalla.

## 2 · 🔒 El codi del client no s'edita, i es diu per què

Canviar el `client_code` no és editar l'àlies: és **esborrar-ne un i crear-ne un altre**, perquè
és el que el matcher busca a les importacions i el que la unicitat `(customer, client_code)`
protegeix.

- **A la pantalla**: cadenat i `title` amb el motiu, en lloc de deixar que algú ho descobreixi
  provant-ho.
- **Al servidor**: `CustomerPOMAliasSerializer.update` el rebutja amb 400 i el motiu escrit —
  **una pantalla no és una barana**, el camp entra per HTTP. Reenviar el **mateix** codi no
  molesta: el que es barra és el canvi.
- **Al codi del front**: no és a `CAMPS_EDITABLES`, o sigui que **no pot viatjar** encara que
  algú l'afegís a l'esborrany. Hi ha test.

## 3 · L'origen es conserva i l'edició s'hi suma

`PATCH` ja existia i **ja demanava CONFIGURE**, igual que l'alta (`CustomerPOMAliasViewSet` és
un `ModelViewSet` sencer): **no s'ha obert cap porta nova**.

Un àlies d'**IMPORT** corregit a mà segueix sent d'**IMPORT** — l'origen diu **D'ON VE**, no qui
l'ha tocat l'últim; reescriure'l a MANUAL perdria la provinença, que és per al que la columna
serveix. El que es mou és **`editat_at`** (`pom/0083`, additiva i `NULL` a totes les files,
aplicada als tres schemes). La columna Origen ho pinta: el badge de sempre, la data d'alta, i a
sota «Editat el …» quan n'hi ha.

> **Per què no `actualitzat_at`:** és `auto_now` i el mou **qualsevol** desa —una sembra, una
> migració de dades—, o sigui que no distingeix «algú ho ha corregit» de «una comanda hi ha
> passat per sobre». Són dues preguntes i volen dues columnes.

## 4 · Els errors, a la fila

L'error del servidor **es queda a la fila** i no puja al toast: un toast se'n va i no diu de
quina fila parlava. L'esborrany **es conserva** perquè qui ho arregli no hagi de tornar-ho a
escriure. `errorDeResposta` redueix el cos de DRF (`{camp: [missatge]}` o `{detail: …}`) a la
línia que la fila pot ensenyar, i cau al text genèric quan no n'hi ha cap.

## 5 · On viu cada cosa

| Fitxer | Què |
|---|---|
| `pom/models.py` · `pom/migrations/0083` | `CustomerPOMAlias.editat_at` |
| `pom/serializers.py` | `update()`: codi immutable + `editat_at` + `origen` intocable |
| `pom/test_alies_edicio.py` | 8 tests d'endpoint |
| `utils/edicioAlies.js` (+ test) | **la regla de què s'envia**, fora del component: PATCH mínim, camps tancats, error a una línia |
| `pages/CustomerDetail.jsx` | l'estat de la pantalla i el pintat |
| `llista/ChromLlista.jsx` | `BotoEditar` i `BotoIcona`, forma §8e de la paperera |

**El llapis no va en vermell:** editar no és esborrar, i la tinta destructiva diria que ho és.

## Anotat, fora d'abast

- 🚩 `client_description` segueix al contracte com a **llegat** i **no s'edita**: el camp viu és
  `description_en`.
- 🚩 `CustomerPOMAlias` **no té camp d'autor** (només dates): la marca diu *quan*, no *qui*.
