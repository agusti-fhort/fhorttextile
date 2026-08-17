# ACTA · E3 — l'estat TANCADA (F-A) i el botó «Mesurar set» (F-B, D5 tancada)

> Substrat: [`DIAGNOSI_QA_2054_REGRESSIO_O_FORAT.md`](DIAGNOSI_QA_2054_REGRESSIO_O_FORAT.md).
> 17/08/2026 · branca `dev` · **5 commits locals, cap push, cap PROD.**
> ⚠️ **La diagnosi NO se segella i es queda a l'arrel**: E3 implementa F-A i F-B, però **F-C
> (S4, play sobre tasca Feta) queda obert** per decisió d'Agus (deute datat al sprint Kanban).
> Una diagnosi amb una recomanació viva no és històric.

## Els commits

| | commit | què tanca |
|---|---|---|
| E3a/B1 | `f28a9930` | el GET serveix la darrera presa segellada (backend) |
| E3a/B2 | `718671d9` | el cinquè estat `TANCADA` + `escrivible` (`utils/estatPresa`) |
| E3a/B3 | `1b417209` | la pantalla el consumeix; el racó deixa de ser un gest |
| E3b | `cb6b0e53` | «Mesurar set» — el gest que crea la presa |
| E3/QA | `31206b8a` | el cicle sencer + la guarda del salt |

## L'arrel, i per què una sola peça en tanca tres

El GET de presa responia **exactament el mateix payload** per a un model que acabava de segellar
una presa de 90 línies i per a un que no n'ha tingut mai cap. D'aquell empat penjaven S1, S2 i S3.
Ara els casos són tres —`presa_oberta` · `presa_tancada` · cap— i cadascun té nom.

🔑 **`presa_oberta` NO ha canviat de significat** («s'hi pot escriure»), i per això el guard del
POST no s'ha tocat: **la lectura s'amplia, l'escriptura no**. El camp `presa_tancada` és additiu
i hi ha test que fixa que un payload vell es llegeix igual que abans.

🔑 **`escrivible` no és `estat !== TANCADA`.** Hi ha DOS estats sense on escriure (tancada i cap)
i qui els hagi de tractar igual —la graella— no els torna a enumerar. És l'únic predicat del qual
pot néixer un 409 des de la UI, i deriva del mateix booleà que el guard del servidor.

## El que va costar més d'encertar, i per què

**`obrePresa` va per OPCIÓ i no pel parell `(tab, code)`.** El parell `('Escalat','grading')`
també l'usa `autoEdit` en muntar `/models/:id/escalat` —la porta del Kanban—, de manera que
lligar-hi la creació hauria convertit **un enllaç en una escriptura de domini**: sessió + peça +
N línies nascudes de navegar. Crear és del gest; entrar-hi, de la ruta. Hi ha guarda que ho fixa
(`e3_gest_no_navega.mjs`, prova 5).

D'aquí en surt el corol·lari: **el botó sobreviu a `editing`**. Entrar per la ruta deixa
`editing='Escalat'` sense presa, i llavors la graella és de lectura fins que algú prem el botó.
Amagar-lo perquè «ja s'està editant» deixaria el tècnic dins d'un mode d'edició que no accepta
cap tecla i sense cap porta per obrir-ne una.

**Dues dependències load-bearing** que semblen soroll de linter i no ho són:
`editing` a l'efecte de `presaSet` (és per aquí que el botó s'assabenta que la presa que acaba de
crear ja existeix) i `readOnly` al `load` de `PropagatedEditor` — sense aquesta segona, la
graella es quedaria de lectura **just després del gest que l'havia d'obrir**: el botó funcionaria
i no ho semblaria.

## Els números

**Backend · 45/45** (`test_e3_cicle_mesurar_set` + `test_e3_presa_tancada` +
`test_e1_presa_escalat` + `test_e1_guard_partit`), `manage.py check` net.
**Front · 380/380** `node --test` a `src/utils/` · build net · eslint **0 errors, cap warning nou**
· i18n paritat 0/0 als tres idiomes.

**El cicle sencer, baula a baula** (`test_el_cicle_sencer_i_els_seus_numeros`):

| baula | número |
|---|---|
| cap presa | `presa_oberta:false · presa_tancada:false` · POST → **409** |
| crear (Mesurar set) | `n_linies>0` · **n_preses = 0** ← la sembra no és feina feta |
| mesurar 2 talles | **n = 2** · desviació **1.4** · talles `['L','S']` |
| decidir + tancar | `changed:1 · base_changed:True` · base **50.0 → 51.0** |
| **segellar** | `presa_tancada:true` · `session.id` servit · **n = 3** · `decidides_base:1` · POST → **409** |
| Mesurar set (2n) | sessió **NOVA** · **n = 0** · l'acta sencera a l'històric (53.4 intacte) |
| tornar a mesurar | **n = 1** |

**La guarda del salt (§D2), vermell→verd mesurat:**
`node ops/qa/e3_gest_no_navega.mjs 1b417209^` → **1/5** · contra el disc actual → **5/5**.

## Límits mesurats (no són troballes)

1. **El fixture del cicle ha de sembrar `GradedSpec` explícitament.** La peça neix de clonar-los
   (`create_piece_fitting`); sense specs neix amb 0 línies i tota la presa contesta 404
   `sense_linia` — que és el que aquest banc va dir la primera vegada que va córrer.
2. **`close_piece_fitting` retorna `new_version: None` en aquest fixture.** Consolida la base
   (50.0 → 51.0, `base_changed:True`) però no regenera els specs, perquè el banc no porta muntada
   la cadena de re-derivació. Assertar que el teòric de la presa següent és la consolidació de
   l'anterior (llei de Q8) seria **assertar el motor de grading amb un fixture que no el porta**,
   i el motor és zona intocable. El test fixa la baula que sí és d'E3.
3. **La guarda del salt és una prova de TEXT.** El defecte viu a la juntura entre React Router i
   un `useEffect`, i aquí `node --test` no pot importar un `.jsx`. Fixa la PRECONDICIÓ (sense
   navegació no hi ha salt): tan forta com el fet que vigila i ni un pèl més. Queda dit al capçal.
4. **Cap QA visual d'Agus encara.** El `npm run build` ha refet `frontend/dist`, o sigui que
   staging ja serveix aquest front; **el backend, en canvi, segueix servint el codi de les
   18:15:27** i E3a/B1 no és viu fins que algú faci `systemctl restart ftt-staging`. Fins llavors
   la pantalla veurà `presa_tancada` absent i llegirà `SENSE_PRESA` — degradació correcta, però
   **el cinquè estat no es podrà veure a staging**.

## Anotat i NO tocat (fora d'abast, per decisió)

- 🚩 **F-C · S4 (play sobre tasca Feta → «Has acabat?»)** — deute datat al sprint Kanban. El fix
  natural és una cara pròpia a `caraObrirTasca` per a `Done` no-lliurable, avui `CARA_CAP`.
- 🚩 **`PieceFitting.garment = None` amb models de dues prendes** (el 1379). Deute prioritari nou;
  és la FAMÍLIA DE TRES rondant. `test_la_segona_prenda_no_es_perd_pel_cami` cobreix que el cicle
  d'E3 no ho empitjora, però **no ho arregla**.
- 🚩 **401 sense reintent** a `transition`/`unlock` (18:50:49 i 18:53:53 de la QA): el refresc
  arriba tard i els dos gestos es perden en silenci. V. `ftt-k1k6-sessio-jwt-refresh`.
- 🚩 **Q8-bis (`acabe1bf`, `932def89`) segueix sense QA visual**: es va desplegar a les 19:03,
  després de la QA de les 20:54 (hora local).
