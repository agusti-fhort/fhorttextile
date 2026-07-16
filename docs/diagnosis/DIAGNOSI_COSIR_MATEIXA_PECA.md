# DIAGNOSI — La restricció de cosir sobre la mateixa peça

Data: 2026-07-16 · **Patró A (READ-ONLY)** · staging `/var/www/ftt-staging`, branca `dev`
Abast: per què «Declarar costura» no s'activa amb dos trams de la mateixa peça (QA Montse,
model 163 TATE_SLEEVE). Les dues capes (frontend + backend), l'origen de la llei, i el fix mínim.
Convenció: `fitxer:línia` · `"NO EXISTEIX" = confirmat absent al codi (no especulat)` ·
`💡 PROPOSTA (a validar)` = disseny, no fet.

---

## Resum executiu

1. **NO EXISTEIX cap gate de «mateixa peça».** Cap capa —ni el botó, ni la selecció de trams, ni
   el canvas, ni el serializer, ni el motor de longituds— compara la peça del costat A amb la del
   costat B. La condició que el brief buscava no és al codi.

2. **El defecte reportat es reprodueix, però la causa és una altra: la trampa del COSTAT ACTIU.**
   `triarTram` afegeix sempre al costat actiu (`costatActiu`, per defecte `'a'`), i res no avança
   a B. Qui clica els dos trams seguits —el gest natural quan tots dos són de la mateixa peça i
   surten arran l'un de l'altre al mateix grup— els posa **tots dos a Side A**; Side B queda buit;
   el gate `llest = A>0 && B>0` deixa el botó desactivat. Reproduït en viu (§B).

3. **La inversió és exacta:** el cas LEGÍTIM (mateixa peça, trams diferents) queda bloquejat de
   fet per la trampa d'UX; el cas ABSURD (el MATEIX tram als dos costats) SÍ que activa el botó
   —no hi ha cap dedup entre costats. El sistema impedeix el que hauria de permetre i permet el
   que hauria d'impedir (§B, §C).

4. **L'única «restricció» de peça que existeix és per a POMs i trams, no per a costures** (D8:
   «B tancat a la peça de l'A»), i viu al canvas via `pecaIman`/`voraIman`, **nul·les en mode
   `sew`** (`TallerPatro.jsx:853`). NO es va propagar a Cosir. La suposició de «dues peces» sí que
   viu, però només com a PROSA al docstring de `SewRelation` (`models.py:428-432`), sense cap
   `clean()` ni constraint que la faci complir (§A, part b).

5. **El motor de longituds és agnòstic de peça** (`validar`, `sew.py:115`): cosir mateixa-peça
   valida idènticament. La cobertura (`validar_cobertura`) treballa per VORA; per a les dades del
   163 els dos trams són a la mateixa vora 2 però NO se solapen (t[0–0.27] vs t[0.50–0.77]), així
   que no salta cap avís. Hi ha un risc residual documentat a §D.

6. **Fix mínim** (💡, a validar a §E): (i) avançar el costat actiu a B després de triar el primer
   costat, o fer visible que cal, perquè el cas legítim deixi de topar amb la trampa; (ii) tancar
   el forat real —impedir el MATEIX segment als dos costats— que és el que la restricció «de
   debò» hauria de tapar. Cap dels dos toca el motor ni la definició de dades.

---

## BLOC A — ON viu (i on NO viu) la restricció

### El gate del botó: només compta costats, no peces

`SewEditor.jsx:31`:
```js
const llest = segmentsA.length > 0 && segmentsB.length > 0
```
És l'ÚNICA condició que habilita «Declarar costura» (`SewEditor.jsx:108`, `disabled={!llest}`).
No compara peces. Va néixer així al commit `f3523b2` (W2/T3, 2026-07-13) i no ha canviat mai
(`git log -S`). **NO EXISTEIX** cap variant amb comparació de peça.

### La selecció de trams: afegeix al costat actiu, sense mirar peça ni l'altre costat

`TallerPatro.jsx:371-375`:
```js
const triarTram = (tram) => {
  const llista = costatActiu === 'a' ? segmentsA : segmentsB
  const set = costatActiu === 'a' ? setSegmentsA : setSegmentsB
  set(llista.includes(tram.id) ? llista.filter(x => x !== tram.id) : [...llista, tram.id])
}
```
- No compara `tram.peca` amb res.
- No hi ha dedup **entre** costats: un mateix tram pot acabar a `segmentsA` **i** a `segmentsB`.
- `costatActiu` per defecte és `'a'` (`TallerPatro.jsx:77`) i només el mou el clic als chips
  Side A/Side B (`onCostat`, `SewEditor.jsx:59,62`). **NO EXISTEIX** cap avanç automàtic a B
  després de triar el primer costat.

### El canvas: mateix handler, sense filtre de peça en mode sew

`PatternViewer.jsx:439` — un tram declarat és clicable si `mode === 'sew'`, sense cap condició
de peça; `onClick` crida el mateix `triarTram` (`PatternViewer.jsx:441` ← `TallerPatro.jsx:1232`).
La peça-imant (`pecaIman`) que tancaria el segon clic a la peça del primer és **null en mode
sew** (`TallerPatro.jsx:852-856`): només s'activa en `'pom'` i `'seg'`.

### El backend: cap validació de «peces diferents»

- `SewRelationSerializer` (`annotation_views.py:84-97`) no té `validate`/`validate_segments_*`.
- `SewRelationViewSet.perform_create` (`annotation_views.py:429-430`) només fixa `creat_per`.
- `SewRelation` (model) **NO EXISTEIX** cap `def clean`, `CheckConstraint` ni `UniqueConstraint`
  sobre peces (grep sobre `models.py:426-470`).
- L'única comparació `piece_id != piece_id` del fitxer (`annotation_views.py:975`) és a
  `PatternSegmentViewSet.update` i vigila que un tram **no canviï de peça en recol·locar-se** —
  no té res a veure amb costures.

> **Origen de la suposició (part b):** la idea de «dues peces» viu com a PROSA al docstring de
> `SewRelation` (`models.py:428-432`): *«quins trams d'una peça es cusen amb quins d'una altra…
> hi intervenen dues peces»*, i com a comentari al canvas (`PatternViewer.jsx:353-354`: *«una
> costura uneix DUES peces»*, sobre l'atenuació). És el model mental del cas comú, **no una
> regla imposada**. La restricció real «B tancat a la peça de l'A» és la D8 dels POMs
> (`TallerPatro.jsx:848-856`), i **no es va propagar** a Cosir. La hipòtesi del brief (còpia
> W3→Cosir) queda DESCARTADA: no hi ha còpia; simplement el gate de Cosir mai no ha mirat peces.

**Veredicte A:** la restricció de mateixa-peça NO EXISTEIX a cap capa. El bloqueig efectiu prové
del model d'un-sol-costat-actiu de `triarTram`, no d'un predicat de peça.

---

## BLOC B — Reproducció en viu (read-only, cap escriptura)

E2E contra staging servint el bundle nou per `page.route` i deixant passar `/api/` (auth off);
selecció = estat de client, cap POST; **0 POSTs de costura emesos** (verificat). Model 163, file 11,
trams declarats de TATE_SLEEVE: `430 "maniga 1"` i `431 "Maniga 2"`, tots dos vora 2.

| Seqüència | Side A | Side B | Botó |
|---|---|---|---|
| Inicial | 0 | 0 | disabled |
| maniga1 → A, canviar a B, maniga2 → B | 1 | 1 | **enabled** ✅ |
| maniga1 → A, maniga2 **sense canviar de costat** | **2** | 0 | **disabled** ❌ |
| maniga1 → A, canviar a B, **maniga1 un altre cop** → B | 1 | 1 | **enabled** ⚠️ |

- Fila 2: cosir mateixa-peça (trams diferents) **funciona** quan es reparteixen als dos costats.
- Fila 3: **el cas de la Montse**. Els dos trams a Side A, Side B buit → botó bloquejat. Reproduït
  exactament, sense cap gate de peça.
- Fila 4: el **mateix tram** (id 430) als dos costats activa el botó — el cas absurd no està tapat.

**Veredicte B:** el símptoma és real i la causa és la trampa del costat actiu, no la pertinença a
peça. Confirmat empíricament.

---

## BLOC C — Què protegeix de debò (mateixa peça vs mateix tram)

- **Mateixa peça, trams DIFERENTS** (màniga cosida sobre si mateixa, canó, puny): LEGÍTIM. Res al
  domini ho impedeix conceptualment, i el motor ho valida bé (§D). Avui queda bloquejat només per
  accident (§B, fila 3).
- **MATEIX tram als dos costats** (mateix `segment_id` a `segments_a` i `segments_b`): ABSURD —
  cosiria un tros de vora amb ell mateix, longitud contra ella mateixa, desviament sempre 0. Avui
  **està permès** (§B, fila 4; `triarTram` no dedup entre costats, `TallerPatro.jsx:371-375`). El
  backend tampoc no ho rebutja (§A). És el forat que una restricció «de debò» hauria de tapar.

**Veredicte C:** «mateixa peça» ≠ «mateix tram». La distinció que cal fer és a nivell de SEGMENT,
no de peça. El sistema té els dos exactament al revés.

---

## BLOC D — El motor de longituds i la cobertura amb mateixa-peça

- **`validar`** (`sew.py:115-123`) rep només `longitud_a_mm`, `longitud_b_mm`, tipus, diferencial
  i descomptes. **No coneix la peça.** Cosir dos trams de la mateixa peça es valida idènticament a
  cosir-ne de peces diferents: casa/no casa surt de les longituds i el tipus, res més.
- **`comprovar_costura`** (`annotation_views.py:199-220`) → `_costat_net` per costat → `validar`.
  Cap branca depèn de la peça.
- **`validar_cobertura`** (`sew.py:323-420`) treballa **per VORA**. Aquí sí que la mateixa-peça és
  rellevant: si els dos costats cosits comparteixen vora i **se solapen**, salta l'avís
  *«La costura X es trepitja a ella mateixa»* (`sew.py:369-380`); si la suma cosida passa de la
  vora, salta EXCÉS (`sew.py:400-413`). **Són avisos, no bloquegen** —la costura es crea igual.
  - Per a les dades del 163: `430` t[0.0000–0.2657] i `431` t[0.5043–0.7710], **mateixa vora 2**,
    **sense solapament** (0.27 < 0.50) i suma ≈ 53% < 100% → **cap avís** (verificat a la BD).

💡 **PROPOSTA / risc (a validar):** en un cas de mateixa-peça on els dos trams de debò comparteixen
tram de vora (p. ex. un puny mal declarat, o dos trams que es trepitgen), `validar_cobertura`
denunciaria un auto-solapament correcte. No és un bug; és el comportament desitjat. Però convé
tenir-ho present si el cas d'ús «canó/puny» posa els dos costats a la mateixa vora a posta.

**Veredicte D:** el motor NO assumeix res sobre la peça. Cosir mateixa-peça és segur per al càlcul.
L'únic matís és la cobertura per-vora, que informa (no bloqueja) i que per al 163 no salta.

---

## BLOC E — Fix mínim 💡 (a validar, Patró C)

Dos canvis independents, cap toca el motor ni les dades:

1. **Desbloquejar el cas legítim — treure la trampa del costat actiu.** Que el segon tram no
   caigui al mateix costat per inèrcia. Opcions (a triar):
   - **E1a — avançar a B automàticament** després de fixar el primer costat (quan `segmentsA`
     passa de buit a ple i B és buit, `setCostatActiu('b')`). Mínim, invisible, resol el gest
     natural. Risc: si algú vol dos trams a A (una sisa = davanter+esquena), l'avanç automàtic
     el molestaria — caldria avançar només en el PRIMER tram, no en cada clic.
   - **E1b — deixar la selecció on és i fer VISIBLE que falta el costat B**: el gate ja hi és; el
     que falla és que no es veu per què el botó està apagat. Un hint («tria el costat B») quan
     `segmentsA.length>0 && segmentsB.length===0`. No canvia el flux, només l'explica.
   - `TallerPatro.jsx:371-375` (`triarTram`) i/o `SewEditor.jsx:107-114` (zona del botó).

2. **Tapar el cas absurd — impedir el MATEIX segment als dos costats.** El gate honest no és
   «peces diferents» sinó «cap segment repetit entre A i B»:
   ```
   💡 llest = A.length>0 && B.length>0 && A i B no comparteixen cap id
   ```
   a `SewEditor.jsx:31`, i idealment també una validació al backend
   (`SewRelationViewSet`/serializer, avui inexistent, §A) perquè la regla no visqui només al
   client. Això SÍ que és la restricció que «volia tapar» el cas —però a nivell de tram, no de
   peça—, i **no reobre** el cas legítim de mateixa-peça-trams-diferents.

> Cap proposta introdueix una comparació de peça. La peça mai no ha de bloquejar una costura: el
> domini (canó, puny, màniga) demana explícitament poder cosir una peça sobre si mateixa.

---

## TAULA FINAL per al CTO

| # | Qüestió | Estat | Evidència |
|---|---|---|---|
| 1 | Gate del botó compara peces? | **NO** — només costats no-buits | `SewEditor.jsx:31` |
| 2 | `triarTram` restringeix per peça? | **NO** — afegeix al costat actiu | `TallerPatro.jsx:371-375` |
| 3 | Canvas filtra trams per peça en sew? | **NO** — `pecaIman` null en sew | `PatternViewer.jsx:439`, `TallerPatro.jsx:853` |
| 4 | Backend valida peces diferents? | **NO** — cap `validate`/`clean`/constraint | `annotation_views.py:84-97,429`; `models.py:426-470` |
| 5 | Causa real del bloqueig | Trampa del costat actiu (tots dos a A) | §B fila 3 (reproduït) |
| 6 | Cas absurd (mateix tram 2 costats) | **PERMÈS** (forat obert) | §B fila 4; `triarTram` sense dedup |
| 7 | Motor de longituds assumeix peça? | **NO** — agnòstic | `sew.py:115` |
| 8 | Cobertura amb mateixa-peça | Per-vora; avisa, no bloqueja; al 163 no salta | `sew.py:323-420`; BD 430/431 |
| 9 | Origen «dues peces» | Prosa al docstring, no regla | `models.py:428-432` |
| 10 | Fix mínim | E1 (desbloquejar) + E2 (tapar mateix-tram) | §E — 💡 a validar |

**Cap escriptura de codi feta. Aquesta diagnosi és l'únic fitxer creat.**
