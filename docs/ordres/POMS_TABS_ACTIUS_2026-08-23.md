# /poms · TABS ACTIUS/INACTIUS + FILTRE PENDENTS

**Data:** 2026-08-23 · **Entorn:** `/var/www/ftt-staging`, branca `dev` · **Patró B**
**Decisió:** Agus, 23/08 · **Cap push. Cap canvi de backend.**

> La pantalla deia **«521/521»** quan el catàleg viu en són **141**. Tres de cada quatre files
> són ARXIU —la llei S44 diu que el catàleg vell mor com a `actiu=False`, no s'esborra— i
> embrutaven la llista de treball.

| Commit | Concern |
|---|---|
| `4b4c4c0e` | **D1** · tres tabs amb recompte, defecte «Actius» |
| `94109804` | **D2** · la cerca travessa el tab (la guarda anti-duplicats) |
| `824b915b` | **D3** · el xip «Pendents de revisió (n)» |
| `953c182f` | **D4** · la fila inactiva porta el badge DESACTIVAT |
| `46255fd2` | el guard de «el tab no persisteix» |

---

## LA PREGUNTA QUE EL BRIEF DEMANAVA RESPONDRE ABANS DE DECIDIR

> *«Els recomptes surten del servidor, no de comptar la pàgina carregada. Si la llista és
> paginada… mirar com serveix la llista el backend ABANS de decidir (no assumir que ve
> sencera).»*

**Mesurat, i la resposta és les dues coses alhora:**

| | |
|---|---|
| El backend **PAGINA** | `DefaultPagination`, 25/pàgina, `max_page_size=200` (`fhort/pagination.py`) |
| La pantalla **JA ES CARREGA SENCERA** | `totesLesPagines(poms.list, {page_size: 200})` — `POMCataleg.jsx:18`, segueix el `next` de DRF fins al final |
| Els filtres **JA HI SÓN** | `filterset_fields = ['actiu', 'pom_global']` · `search_fields` · `POMMasterSerializer` emet `fields='__all__'`, o sigui que **`pendent_revisio` ja viatja** |

**Conclusió:** al client hi ha les 521 files, no un tros. Comptar-les **no és «comptar la
pàgina carregada»** —que és el que la llei prohibeix perquè menteix—: és comptar-les totes.
Per tant els recomptes són exactes **sense tocar el backend**, i el brief demanava expressament
no tocar-lo si no calia.

🚩 **I ON ES TRENCA AIXÒ.** El dia que la pantalla pagini de debò, els recomptes i la creuada
deixen de ser certs **el mateix dia i sense avisar**. Per això la condició està escrita a la
capçalera de `filtrePoms.js` i no en aquesta acta sola: qui hi torni la llegirà al fitxer.

---

## D1 · ELS TABS

`Actius (n) · Inactius (n) · Tots (n)`, a la capçalera de la llista.

- **`ui/SubTabs`**, el component de tabs de la casa (subratllat d'or, NORMA §8b-bis). Cap
  patró nou i cap color nou. ⚠️ El seu badge **no pinta el zero a posta** («un 0 permanent al
  costat d'un tab és soroll») i aquí es respecta: sense arxiu, «Inactius» va sol.
- **S'obre sempre a Actius** i el tab **no es desa**: la llei de la casa és que les decisions
  d'usuari es deriven del servidor o es reinicien. Amb `localStorage`, el dia que algú hi
  deixés «Inactius» posat, el catàleg viu semblaria buit i ningú sabria per què.
- **La cerca actua dins del tab**, i canviar de tab **no la perd**.
- Els recomptes són de la llista sencera i **no ballen amb la cerca**: el badge diu què hi ha
  al catàleg, no què queda del filtre d'ara.

**La regla viu FORA del component** (`components/POMCataleg/filtrePoms.js`), com
`instanciaTria.js`: és el que la fa provable amb `node --test` sense React.

## D2 · LA TRAVESSA — **s'ha fet la variant RICA, amb xifra exacta**

El brief donava dues variants i demanava dir quina i per què.

| Variant | Feta? | Per què |
|---|---|---|
| **«N coincidències més a Inactius»**, clicable | ✅ | La llista és sencera al client: el recompte creuat **no costa cap petició ni cap aproximació** |
| «Cerca també a Inactius» sense xifra | ❌ | Era el pla B per si el recompte creuat sortia car. No en surt |

Va **sota** els resultats, en to discret, i porta a l'altre tab **sense perdre el text**.
Calla quan no hi ha res a dir (sense cerca, o al tab «Tots»), i **apareix encara que el tab
actiu doni ZERO resultats** — que és precisament el cas que la motiva: buscar «waist» a
Actius, no trobar-lo, i fabricar el duplicat 522 d'un POM que viu a l'arxiu.

## D3 · EL XIP DE PENDENTS

`ui/Xip`, el commutable de la casa. Diu quants n'hi ha **dins del tab i de la cerca**, i el
número **no canvia** pel fet de tenir-lo encès —si canviés, apagar-lo seria endevinar—. Sense
cap pendent no s'ofereix: un filtre que no pot filtrar res és una porta pintada.

## D4 · COHERÈNCIA VISUAL

- La fila inactiva porta el **badge DESACTIVAT de la fitxa**, amb els seus tokens
  (`--bg-page` / `--text-soft` / `--line`) i la seva clau (`poms.cat.badge_off`). L'opacitat
  0,5 que ja hi havia es queda, però sola no diu QUÈ passa: una fila pàl·lida es llegeix igual
  com «deshabilitada» o «carregant».
- **Al tab «Tots», els inactius van darrere dins de cada família** (`inactiusDarrere`). No es
  condiciona al tab: una regla que val sempre no té cas especial que es pugui oblidar.

---

## EL VERD

| Control | Resultat |
|---|---|
| `node --test filtrePoms.test.js` | **15 tests · OK** |
| `npx eslint src` | **0 errors** (272 warnings preexistents) |
| `npm run build` | **OK** — ⚠️ i això **publica `frontend/dist`**, que és el que staging serveix |
| i18n ca/en/es | **paritat verificada** per script; cap text hardcoded |
| backend | **no tocat** → `manage.py check` net (sense canvis) |

**Els tests que el brief demanava:**

| Demanat | On |
|---|---|
| defecte = Actius | `test('el defecte és ACTIUS, i és el primer tab')` |
| el tab no persisteix | `test('la pantalla no desa el tab enlloc')` — prova **estructural**, i es diu: sense navegador no es recarrega res; el que es mesura és que no hi ha cap magatzem |
| recomptes correctes amb paginació | `test('els recomptes són de la llista SENCERA…')` + la nota de dalt: avui **no hi ha paginació al client** |
| cerca dins de tab + travessa | 4 tests (dins, creuada, quan calla, i amb 0 resultats al tab actiu) |
| pendents combinat amb tab i cerca | 2 tests |
| i18n | paritat comprovada amb script |

## ANOTAT, FORA D'ABAST

- 🚩 La fitxa i els botons Desactivar/Esborrar **no s'han tocat**, com manava el brief.
- 🚩 Si algun dia el catàleg creix prou per haver de paginar al client, **els recomptes i la
  creuada han de passar al servidor** (comptadors, no un CRUD). La condició és a
  `filtrePoms.js`.

**Cap push. El merge i el desplegament els fa l'Agus.**
