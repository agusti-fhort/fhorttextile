# REPORT W2 · El wizard de model segons la maqueta

> Tram W2 · 06/08/2026 · staging `dev` · cap push, cap suite.
> Especificació: `ops/maquetes/maqueta_wizard_model_v1.html` — **validada per l'Agus el
> 06/08/2026 a pantalla**. Les dades de la maqueta són de demostració; la forma és l'ordre.
> README de maquetes actualitzat en aquest tram (la línia «pendent de validació» ha caigut).

## Estat del tram

| Peça | Què és | Estat |
|---|---|---|
| **W2.0** | `CascadeFinder` — el navegador GRUP › FAMÍLIA › ITEM, component únic | ✅ `2ac9f6a2` |
| **W2.1** | El pas 2 refet: filtres per descarte a dalt, finder a sota | ✅ `1996e4f8` |
| **W2.2** | El pas 3: proximitat ordena, cap sistema amagat | ✅ `1996e4f8` |
| **W2.3** | Els textos de la maqueta · i18n ca/es/en amb paritat | ✅ `1996e4f8` |
| — | Garment Types consumint el finder | 🚩 **TRAM PROPI** (decisió d'Agus, 06/08) |

**Verd:** `npm run build` net · `eslint` a la mateixa marca que HEAD (0 errors; els 7 avisos són
els preexistents de la pàgina) · paritat i18n verificada per script · fum de navegador i cicle de
model, tots dos verds (v. «Verificació»).

## La frontera amb Sessió 2, i com s'ha resolt

`ModelWizard.jsx` portava feina de Sessió 2 **sense commitar**. Es va aturar el tram i preguntar
(era la línia FRONTERA del brief). Sessió 2 va commitar a `6fc4b1a7` i W2.1/W2.2 s'han fet **a
sobre**. Les seves dues coses segueixen intactes i verificades al navegador:

- l'avís del motor de temps viu al pas 2, **una sola aparició**, al costat de la tria de peça;
- «Següent» desactivat conserva caixa i contrast i porta el motiu (`next_needs_customer` /
  `next_needs_season`) al costat i al `title`. El fum hi passa a cada corregada: arriba al pas 2
  pel GEST (triar client + temporada i prémer «Següent»), no per URL.

⚠️ **Un efecte del solapament, per si es busca:** les claus `cascade_finder.*` de W2.0 van quedar
dins del commit de Sessió 2 (`6fc4b1a7`), no del meu. Els tres `i18n/*.json` tenien canvis de tots
dos i `git add` d'un fitxer se'ls endú tots. Res perdut, tot a HEAD; només que el commit que les
conté no és el que les explica.

## Dues premisses del brief que no s'aguantaven

### 1 · Garment Types no té cap cascada per reutilitzar

`GarmentTypes.jsx` és mestre-detall: `GroupPills` + cerca + llista PLANA de famílies, i una
graella de *cards* d'item. **No hi ha cap finder de tres columnes enlloc del frontend.** L'únic
component compartit de cascada és `CascadeSelector`, que és de píndoles apilades.

S'ha aplicat la branca de reserva del brief: **construir-ne UN** → `CascadeFinder`.

🚩 **PENDENT EXPLÍCIT** — Garment Types el consumirà en un tram propi (decisió d'Agus: avui no es
toca cap pàgina de gestió que funciona). **Mentre no es faci, el veto dels dos sistemes segueix
obert**: el component ja hi és, li falta el segon consumidor. Forma prevista: el finder substitueix
el mestre i el detall (capçalera, Editar/Esborrar/Nou, Fitxers) es manté intacte al costat.

### 2 · Els ítems no tenen ni target ni fit

La maqueta filtra cada peça per TARGET i FIT (`it.tgt`, `it.fit`). Al domini real **això no
existeix a l'ítem**: `GarmentTypeItemSerializer` (`backend/fhort/tasks/serializers_b.py:247-254`)
no exposa cap eix. El target i el fit viuen a la **FAMÍLIA**, via `SizingProfile`, i el backend ja
els resol amb `compat_target`/`compat_construction`/`compat_fit`, que **anoten** cada família amb
`.compat = {ok, motiu}` en comptes d'excloure-la.

No trenca la maqueta: hi encaixa. Les píndoles segueixen sent filtres per descarte, però el que
atenuen és la columna de FAMÍLIA (i el grup que es queda sense famílies compatibles). El grid de
grups amb «Sense perfil de talles per a el target» **com a bloqueig ha desaparegut** del pas 2; el
text es conserva com a motiu d'atenuació — que és el que la maqueta demana.

## ⚠️ Divergència conscient amb la maqueta: la CONSTRUCCIÓ es queda

La maqueta té dues files de píndoles (TARGET i FIT) i el brief n'enumera dues. **Se n'han deixat
tres.** Motiu: `construction` **viatja al payload** del model (`skeletonPayload`,
`ModelWizard.jsx:417`) i aquestes píndoles són **l'únic lloc del producte que l'escriu**. La
maqueta el resol amb una fila d'eixos DERIVATS de la peça i editables — que no és en aquest brief.
Treure les píndoles sense construir abans aquella fila no hauria estat seguir la maqueta: hauria
estat perdre un camp pel camí, en silenci.

**Decisió pendent d'Agus** (una línia): o s'accepta la tercera fila, o s'obre la peça de la fila
d'eixos derivats i llavors cau sola.

## Què ha canviat al pas 3 (W2.2)

Abans, `ModelWizard.jsx` **excloïa** sistemes de talles pel target:

```js
(!s.target_codis || s.target_codis.length === 0 || s.target_codis.includes(target))
```

Amb dades reals de staging això amagava **15 dels 20** sistemes amb talles. Ara el target és la
primera clau d'**ordre** i no en cau cap. `ordenaPerProximitat` ordena per dues claus:

1. **el target**: el declara (0) › no en declara cap (1) › en declara un altre (2). Un sistema
   sense targets no és universal per contracte (v. el serializer): queda al mig, no al davant.
2. **de qui és**: run d'aquest client (0) › canònic (1) › run d'un ALTRE client (2). L'últim graó
   és el parany del model 174: no s'amaga, però no s'ofereix com si fos teu.

`talles.length > 0` **segueix filtrant**: un sistema sense talles no és llunyà, és buit.

Ordre real obtingut al navegador per a un model de BRW amb target WOMAN:

```
WOMAN_BRW_01[BRW] › ALPHA_EU_W[canònic] › NUMERIC_EU_W[canònic] › WOMAN_LOS_01[LOS] › WOMAN_NUM_LOS_01[LOS]
```

## Verificació

### Fum de navegador · `ops/qa/qa_w2_wizard.py` — **verd**

Bundle REAL de `frontend/dist` (el mateix que nginx publica), amb les respostes **reals** de
l'API capturades per `ops/qa/qa_w2_fixture.py` (62 ítems, 17 famílies, 25 sistemes): les formes
són les del producte, no les que li aniria bé al fum.

```
✓ comptador correcte: 62 peces al catàleg
✓ grup → família (ACCESSORIES → Accessories)
✓ família → ítem (Accessories → Gorra / barret)
✓ cerca sense coincidències: «0 de N peces encaixen»
✓ cap amagat: els grups segueixen a la llista amb 0 coincidències
✓ consola neta al pas 2
✓ pas 3 · cap amagat: hi son els 20 sistemes amb talles (inclosos els 15 que no declaren WOMAN)
✓ pas 3 · proximitat: WOMAN_BRW_01[BRW] › ALPHA_EU_W › NUMERIC_EU_W › WOMAN_LOS_01 › WOMAN_NUM_LOS_01
✓ pas 3 · etiqueta «Run de client · BRW» present
✓ ca / es / en · consola neta als tres
✓ F5: el pas 2 torna a muntar, sense errors
```

### Cicle del model · `ops/qa/qa_w2_cicle_model.py` — **verd**

```
· client BRW · peça BUTTONED_TOPS › Shirt Man Regular · run WOMAN_BRW_01 ['XXS','XS','S','M','L']
✓ creat · model id=1310 · BRW-FW26-0036
✓ run de client desat: WOMAN_BRW_01
✓ run desat en ordre del sistema: XXS·XS·S·M·L
✓ peça desada: Shirt Man Regular
✓ client i prefix del codi: BRW-FW26-0036      ← el gate del 04/06, INTACTE
✓ surt a la llista de models
✓ esborrat · no queda rastre a la BD
```

**El model de prova s'ha esborrat**: staging no queda amb runa d'aquesta QA.

### 🚩 El que NO s'ha pogut verificar pel navegador: el clic de DESAR

El cicle crear → llistar → esborrar passa per la **vista real** (`create_wizard`, serializers,
porta única del run, BD) amb l'`APIClient` de DRF, **no** per HTTP amb un clic. Motiu: el gunicorn
viu **rebutja els tokens encunyats des del shell** (401 confirmat en aquest tram; ja consta a la
nota d'e2e del vault) i a staging **no s'hi creen usuaris de QA**. El que queda fora de la prova
és la capa HTTP i el clic del botó; tot el que decideix què es desa hi ha passat.

Per tancar-ho de debò caldria una sessió amb credencial real d'Agus al navegador. Ho anoto com a
pendent honest, no com a fet.

## Fora d'abast, vist pel camí (s'anota, no es toca)

- **`CascadeSelector` (mode single) segueix viu** a la resta de superfícies. Quan el finder les
  cobreixi, caldrà decidir si el mode single es jubila. Avui conviuen a posta.
- **La preselecció del pas 3 ara pot caure en un sistema llunyà.** `rows[0]` es preselecciona en
  creació; amb el filtre retirat, per a un target sense cap sistema que el declari el primer és
  ara un sistema «del mig» en comptes de cap. No és silenciós (sense run i talla base no es pot
  desar) i abans la pantalla directament sortia buida, però és un canvi de conducta que val la
  pena mirar a la QA de les 9:30.
- El comentari de `ModelWizard.jsx:560-564` ja avisava que «sense perfil» compta com a
  incompatible al veredicte del backend. Segueix sent cert i segueix sent un PENDENT anotat allà.
- El comptador («N de M peces encaixen») respon **només a la cerca de text**. Target i fit no
  exclouen ítems —atenuen famílies—, així que no mouen el número. És correcte, però si algú
  espera que el comptador baixi en filtrar per target, aquesta és la raó que no ho fa.

## Commits del tram (cap push — el fa l'Agus des de SSH)

| Hash | Què |
|---|---|
| `2ac9f6a2` | 14 · el navegador de peça en tres columnes, com a component únic |
| `1996e4f8` | 15 · W2.1/W2.2 · el pas 2 amb el navegador i el pas 3 sense amagar res |
| _(aquest)_ | 16 · el fum del tram i el report |

Per revisar: `git show <hash>`. El de Sessió 2 és `6fc4b1a7` i va PRIMER.
