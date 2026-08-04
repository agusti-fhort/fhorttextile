# REPORT · L'embut d'imatge al coll dels adjunts de model

**Data:** 2026-08-02 · **Branca:** `dev` (staging) · **Push:** cap (el fa l'Agus)
**Abast:** backend pur. Cap fitxer de frontend tocat.

Dos commits separats i cherry-pickables per separat:

| # | Commit | Què fa |
|---|--------|--------|
| 1 | `1aed0311` | El fix: l'embut al coll. Para l'hemorràgia de les imatges **noves**. |
| 2 | `120aba99` | `reprocessa_imatges_adjuntes`: neteja les **velles**. |

---

## FASE A · Diagnosi (read-only)

### A.1 · Firma real de `redueix_imatge`

`backend/fhort/models_app/services_fitxers.py:107`

```python
def redueix_imatge(file, nom, content_type='', max_dim=None) -> (fitxer, nom)
```

- **Retorna una TUPLA `(fitxer, nom)`**, no un file-like sol. El `nom` pot canviar
  (HEIC → `.jpg`, PNG opac → `.jpg`), i qui la crida ha de fer servir el nom retornat o
  desarà un JPEG amb extensió `.heic`.
- Quan no cal tocar res retorna **el mateix objecte** amb `seek(0)` fet
  (`_intacte()`, :143). Quan sí, retorna un **`ContentFile`** nou amb `name=nom_nou`.
- `max_dim` **és nou d'aquest sprint** (vegeu A.4). Abans el sostre era literal.

**PNG:** no hi ha cap constant `PRESERVEN_ALFA` — la preservació és una **decisió al vol**
a :193-197: `te_alfa = imatge.mode in ('RGBA','LA','PA') or 'transparency' in imatge.info`.
Si té alfa surt PNG (o WEBP si ja ho era); si no en té, surt **JPEG i el nom canvia**. Un
PNG opac de 3000 px es desa com a `.jpg` — comportament ja viu i ja provat
(`test_upload_imatge.py:63`), no l'ha introduït aquest fix.

**HEIC:** es converteix sempre a JPEG, tingui la mida que tingui (:194). Si Pillow no la
sap llegir → `ConversioFallida`. Qualsevol **altra** imatge il·legible → es desa
l'original i s'escriu un warning (llei de `pom_vision_service`): un downscale no bloqueja
mai una pujada vàlida.

### A.2 · `RASTER_EXTENSIONS` (`:69`) — confirmat

```python
RASTER_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp'} | HEIC_EXTENSIONS
```

`.gif` i `.svg` en queden fora **a posta i amb motiu escrit**: de la GIF, Pillow en
llegiria només el primer fotograma i desar-la mataria l'animació en silenci; l'SVG és
vectorial i no té píxels a reduir. **No s'han tocat.**

### A.3 · ⚠️ Correcció a una premissa del brief

El brief deia que `save_model_file` desa cru «els IMG_XXXX.jpg de 5-6 MB». **Això és cert
per a quasi tots els camins, però NO per al camí d'upload manual**: `upload_file_view`
(`views.py:2111`) **ja cridava `redueix_imatge`** abans de delegar al servei. L'embut ja
vivia a **tres portes**:

| Porta | Fitxer | Sostre abans |
|-------|--------|--------------|
| Upload manual d'Arxius | `models_app/views.py:2111` | 2000 |
| Assets del `.ftt` | `models_app/ftt_document_views.py:130` | 2000 |
| Fotos de fitting | `fhort/fitting/views.py:712` | 2000 |

El que **no** hi passava és tot el que arriba al servei **per una altra via**, que és on
el fix té valor real:

- `models_app/views.py:387` — còpia model→model, per fitxer
- `models_app/views.py:1516` — còpia model→model, massiva
- `models_app/item_fitxer_views.py:173` — import catàleg→model
- `tenants/federation_service.py:841` — federació entre cases
- `models_app/extraction_views.py:2795` — re-import d'extracció (PDF: no-ràster)
- `models_app/services_ftt_document.py:464/544/682` — blobs `.ftt` (no-ràster)

**Conclusió:** el fix segueix valent la pena i es fa igual, però la seva descripció
correcta no és «ara les imatges es redueixen» sinó **«ara la reducció deixa de dependre
de per quina porta entra la imatge»**. La llei passa de ser una convenció de les portes a
ser una propietat del que hi ha desat.

### A.4 · Sostre: MAX proposat → **decidit per l'Agus**

Valor viu dels assets del `.ftt`: `MAX_COSTAT_LLARG_PX = 2000` (`:64`).

**Decisió d'Agus (02/08): `MAX_ADJUNT_DIM = 1500`** per als adjunts de model —
mig A4 a 150 dpi amb marge, i suficient perquè el text d'una taula d'Excel exportada com
a imatge segueixi llegint-se. Els assets del `.ftt` **no el toquen**: es queden a 2000.

Per fer conviure dos sostres, `redueix_imatge` guanya el paràmetre `max_dim` (per defecte
`MAX_COSTAT_LLARG_PX`). La **decisió** de quants píxels val la pena guardar és de qui
crida —depèn de com es mira la imatge—; el **com** es redueix segueix sent únic.

---

## FASE B · El fix (commit 1)

### B.1 · Punt exacte de la inserció

**`services_fitxers.py:_redueix_si_es_raster()`** (helper nou, al costat de
`_guess_mimetype`) i la seva crida a **`save_model_file`**, primera línia executable
després de resoldre `nom_fitxer`:

```python
nom_fitxer = nom or getattr(file, 'name', None) or 'fitxer'
file, nom_fitxer = _redueix_si_es_raster(file, nom_fitxer)   # ← EL FIX
checksum = _compute_checksum(file)
mida = getattr(file, 'size', None) or 0
mimetype = _guess_mimetype(file, nom_fitxer)
```

**L'ordre és el fix tant com la crida.** Abans, `checksum`/`mida_bytes` es calculaven
sobre l'original; ara descriuen **el fitxer que realment queda a disc**. No és cosmètic:
`federation_service.py:834` compara `anterior.checksum` per no encadenar dues vegades el
mateix fitxer, i un checksum que descrivís un fitxer inexistent li trencaria la
idempotència.

### B.2 · Gate per extensió, i què NO es toca

`_redueix_si_es_raster` mira `os.path.splitext(nom_fitxer)[1].lower()` contra
`RASTER_EXTENSIONS` — la llei de la casa (per extensió, com `ALLOWED_UPLOAD_EXTENSIONS`).
Els `.dxf`, `.pdf`, `.xlsx`, `.ftt`, `.svg` i `.gif` **no arriben ni a obrir-se**.

- **Invariant de cadena intacta:** `is_current`/`versio`/`versio_anterior` no es toquen.
  `save_model_file` en segueix sent l'únic escriptor. L'embut només decideix **quins
  bytes** es desen, mai quina versió són.
- **`save_item_file` NO tocat** (fora d'abast, com deia el brief). Vegeu «Anotat, no
  tocat».

### B.3 · Un canvi que el brief no demanava, i per què s'ha fet igualment

Amb el sostre a 1500 al coll i 2000 a la porta, una foto de mòbil pujada per Arxius es
re-encodaria **dues vegades** (3000→2000 a la porta, 2000→1500 al coll) i cada re-encodat
de JPEG hi deixa pèrdua. S'ha igualat el sostre de la porta:
`views.py:2111` ara passa `max_dim=MAX_ADJUNT_DIM`. Amb els dos sostres iguals, la segona
passada reconeix la imatge com a conforme i la torna **byte a byte**.

La crida de la porta **es queda** (no és redundant): és qui sap traduir `ConversioFallida`
en un **422**. Al coll, que serveix camins sense `request`, l'excepció puja com a
`ValueError` — i això és segur perquè `ConversioFallida(ValueError)` i els tres camins de
còpia ja capturen `ValueError`: federació → avís, catàleg→model → 400, còpia massiva →
warning. **Cap camí no peta amb un 500.**

Conseqüència: `test_upload_imatge.py:149` afirmava que la porta desava a 2000 px.
Aquella xifra era la llei antiga; ara la llei dels adjunts és 1500 i el test hi ha estat
retargetat a `MAX_ADJUNT_DIM`.

---

## Commit 2 · `reprocessa_imatges_adjuntes`

`backend/fhort/models_app/management/commands/reprocessa_imatges_adjuntes.py`

```bash
python manage.py reprocessa_imatges_adjuntes                  # DRY-RUN, tots els tenants
python manage.py reprocessa_imatges_adjuntes --schema fhort   # DRY-RUN, un tenant
python manage.py reprocessa_imatges_adjuntes --apply          # escriu
```

- **DRY-RUN per defecte.** Sense `--apply` no escriu res: compta candidates, redueix
  **en memòria** i informa MB actuals → MB previstos i l'estalvi total amb percentatge.
- **NO crea versió nova.** Els bytes es reemplacen al **mateix registre** i es recalculen
  `mida_bytes`/`checksum`/`mimetype`. Reduir una imatge no és un acte editorial: encadenar
  un «v2» diria que algú ha decidit alguna cosa sobre aquell document, i no és el cas.
  `is_current`/`versio` intactes.
- **IDEMPOTENT.** La mida es llegeix de la **capçalera** (`Image.open(...).size`, sense
  descodificar els píxels) i el que ja compleix se salta. Una segona passada sobre 149
  imatges netes costa mil·lisegons i **no re-encoda res** — important perquè cada
  re-encodat de JPEG hi deixaria gra.
- **Una imatge dolenta no atura la neteja:** `log.ERROR` amb el nom i continua. El resum
  final llista els noms amb error.
- **No-ràsters intocats:** ni entren a la llista de candidats.

**Desviació conscient del brief:** el brief demanava «transacció per lot». S'ha fet
**per fitxer**, perquè un `atomic` per lot no pot desfer les escriptures a disc que ja
s'han fet (deixaria mitja passada amb els bytes reduïts i la fila sense actualitzar) i
perquè trencaria el «una imatge dolenta no atura la neteja». L'ordre per fitxer és:
escriure bytes nous → `atomic` només sobre l'UPDATE de la fila → esborrar els bytes
vells. El pitjor cas és un fitxer orfe al disc, que `audit_fitxers` ja sap reportar; mai
una fila que apunti a uns bytes que ja no hi són.

---

## Verificació

### Estat de les dades a STAGING

```
ModelFitxer: 381 fitxers · extensions: {'.ftt': 364, '.pdf': 10, '.xlsx': 5, '.svg': 1, ...}
RASTERS: 0        ItemFitxer: 1 (0 rasters)
```

⚠️ **A staging no hi ha CAP imatge raster adjunta.** Les 149 imatges / 192 MB de les quals
parla el brief són de **PROD**. Conseqüència directa: la comanda de reprocessament
**només s'ha pogut validar amb tests**, mai contra dades reals. El `--dry-run` a PROD és
per això obligatori abans de l'`--apply`, i el seu recompte és el primer que s'ha de
llegir.

### Tests

**Ritual anti-enverinament abans de córrer** (lliçó del 02/08): kill de tot PID de test
viu · `DELETE FROM public.tenants_client WHERE schema_name='test'` + `DROP SCHEMA test
CASCADE` **contra `test_ftt_staging`, mai `ftt_staging`** (amb `assert` al script perquè no
hi pugui apuntar) · verificació explícita de `files test=0 · schema test=0` abans de
continuar · i **sense `--keepdb`**.

#### Suite acotada: `fhort.models_app --noinput` (BD construïda neta)

```
Ran 479 tests in 1489.072s
FAILED (failures=1)

FAIL: test_el_cami_felic_propaga_i_esborra_els_overrides
      (fhort.models_app.test_c3_a2_transaccio_grading.TransaccioGradingC3A2Test)
AssertionError: 400 != 200 : {'error': 'El model TST-C3A2 no té Size System assignat.'}
```

**L'únic vermell NO és d'aquest sprint.** `test_c3_a2_transaccio_grading.py` és un fitxer
**no versionat** (`??` a `git status`) d'una sessió concurrent que treballa la
transaccionalitat C3-A2 a `generate_grading_view`. Dues proves independents:

1. **A/B fet.** Amb els meus canvis revertits de l'arbre, el vermell es reprodueix
   **IDÈNTIC** (mateix test, mateix `400 != 200`, mateix missatge):
   `Ran 5 tests · FAILED (failures=1)`.
2. **Disjunció de camí.** Tot `generate_grading_view` no té **cap** referència a
   `save_model_file` ni a `redueix_imatge`: el fix no hi és abastable. I l'error és una
   precondició de fixture (el model de test sense Size System), llançada abans de tocar
   cap fitxer.

⚠️ L'A/B **no** s'ha fet amb `git stash` com deia el brief, i a posta: `views.py` conté
alhora els meus hunks i el treball C3-A2 del veí, de manera que estirar aquell path
hauria revertit codi viu d'una altra sessió **i** hauria invalidat el test investigat.
En lloc d'això s'han revertit NOMÉS els meus hunks (reverse-apply del patch filtrat) i
s'han restaurat els altres dos fitxers des de HEAD **només a l'arbre de treball**, deixant
l'índex i el treball del veí intactes. Mateixa evidència, sense danys col·laterals.

#### Els gates que importen

| Gate | Resultat |
|------|----------|
| `manage.py check` | net (0 silenced) |
| `test_save_model_file_embut` (7) + `test_reprocessa_imatges_adjuntes` (6) | **13/13 verds** |
| **Pin `test_base_stages_no_regressio`** | **13/13, cap vermell** |
| `test_upload_imatge` · `test_upload_heic` (portes) | verds |
| Vermells atribuïbles al fix | **cap** |

#### Comportament verificat a nivell de biblioteca

```
jpg 3000x2000 → (1500, 1000)   2539 kB → 745 kB   (−71%)
doble passada byte-a-byte: True          ← idempotent, no re-encoda
sense max_dim (assets .ftt) → (2000, 1333)  ← intactes
png amb alfa → PNG (1500,1500) RGBA      ← alfa preservat
dxf intacte: True
heic → JPEG (1500, 1000), nom IMG.jpg
```

#### Dry-run real contra staging

```
fhort: 0 imatge/s raster de 381 fitxers
los:   0 imatge/s raster de 0 fitxers
```

**⚠️ La suite completa de `fhort` NO s'ha corregut** (86 min, reservada per a canvis
estructurals). Aquest fix és acotat —`save_model_file` + una comanda— i la validació és
proporcional, per decisió d'Agus. La suite sencera queda com a **segell únic abans del
deploy a PROD**, si Agus la vol.

### Nota d'infra sobre com s'ha corregut la suite

Dues lliçons d'infra d'aquesta sessió, per si serveixen a la següent:

1. **Un `--keepdb` sobre una BD bruta menteix.** Una primera execució meva es va morir per
   timeout a mitja suite i va deixar la fila `tenants_client(schema_name='test')`. La
   següent, amb `--keepdb`, va donar **59 errors de `setUpClass`**, tots
   `duplicate key ... schema_name=(test)` — cap relacionat amb el codi. Lectura descartada
   i repetida des de zero després del ritual. És exactament el que documenta
   `ftt-tram-instancia-20260802`.

2. **`pgrep -f "manage.py test"` s'auto-detecta.** Un bucle d'espera que faci
   `until ! pgrep -f "...manage.py test"` conté ell mateix aquella cadena a la seva línia
   d'ordres i no acaba MAI. Van quedar dos processos penjats esperant-se a si mateixos i
   em van fer creure que la suite del veí encara corria quan feia estona que havia acabat.
   Filtrar amb `grep -v "bash -c"` o comparar per PID.

---

## Anotat, no tocat (scope creep vist)

1. **🚩 `save_item_file` no té embut, ni al coll ni a la porta.**
   `item_fitxer_views.py:82` crida `validate_upload` però **mai** `redueix_imatge`: el
   catàleg accepta un JPEG de 6 MB tal com arriba. És el mirall exacte del forat que
   aquest sprint tanca al model, i el brief l'escopa fora explícitament. Avui hi ha
   **1 sol `ItemFitxer` i 0 rasters**, o sigui que no hi ha hemorràgia viva — però el
   forat hi és. Fix d'una línia el dia que es vulgui, calcant `_redueix_si_es_raster`.

2. **🚩 Federació: el checksum és el de la casa d'origen.**
   `federation_service.py:704` empaqueta `f.checksum` (el de l'origen) i `:834` el compara
   amb el del destí. Si l'origen té una imatge **legacy crua** (>1500 px), el destí ara la
   desarà reduïda → els checksums **no coincidiran mai** → cada reenviament encadenarà una
   versió nova. No és regressió del fix sinó de la convivència entre dades velles i llei
   nova, i **desapareix sola** quan s'hagi corregut el commit 2 a totes dues cases. Avui a
   staging no hi ha cap raster, o sigui que no hi ha cas viu.

3. **🚩 Missatge d'error enganyós als dos camins de còpia.**
   `item_fitxer_views.py:176` i `views.py:390` capturen `ValueError` i responen
   *«.ftt origen il·legible»*. Amb el fix, una HEIC legacy corrupta hi arriba com a
   `ConversioFallida` (que és `ValueError`) i l'usuari llegiria un missatge sobre `.ftt`
   per una foto. Es gestiona bé (400, no 500); el que és dolent és el text.

4. **Un `nom_fitxer` estrany a staging:** hi ha un `ModelFitxer` amb extensió
   `'.3] capcalera maqueta + cos 10pt'`. No és ràster i no el toca res, però indica que
   `nom_fitxer` accepta qualsevol cosa.

---

## Per al cherry-pick a PROD

```bash
git cherry-pick 1aed0311      # el fix (para l'hemorràgia)
git cherry-pick 120aba99      # la neteja de les existents
python manage.py reprocessa_imatges_adjuntes --schema <tenant>            # LLEGIR el recompte
python manage.py reprocessa_imatges_adjuntes --schema <tenant> --apply
```

Els dos commits són independents: el 1 sense el 2 deixa d'engreixar; el 2 sense el 1
neteja una vegada i la següent pujada torna a entrar crua. **Cap dels dos toca migracions
ni frontend.**
