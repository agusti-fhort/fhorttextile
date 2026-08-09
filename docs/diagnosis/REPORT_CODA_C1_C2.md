# REPORT · CODA C1 (ownership de media) + C2 (el daurat ple deixa de ser acció)

Dues codes ratificades per Agus el 2026-08-09, executades sobre `dev` a staging.
Commits locals, **cap push**: `86cb640c` (C1) · `57dc3683` (C2) · aquest report.

---

## C1 · El directori del mes que ve neix ja llegible pel servidor web

### El bug no era un permís mal posat: era una CURSA, i es repetia cada 30 dies

`upload_to='…/%Y/%m/'` fa néixer un directori NOU cada mes, i `os.makedirs` el crea amb
l'amo del **procés**. Gunicorn corre com `www-data`, però `manage.py` es corre sovint com a
root. **Qui hi arriba primer decideix l'amo del mes sencer.** El 05/08 hi va arribar root →
`media/fhort/model_fitxers/2026/08` va quedar `root:root 755` → cap fitxa tècnica es va poder
crear en tot l'agost. El `chown` de l'agost no arregla el setembre.

### La via triada: setgid al FS + mode `0o2775` a Django. Les dues, o cap

| Meitat | Què aporta | Per què sola no serveix |
|---|---|---|
| **FS** (una vegada, fora de git)<br>`chgrp -R www-data media && chmod -R g+rwXs media` | El **GRUP**. El bit setgid d'un directori l'hereten els subdirectoris que s'hi creïn, i el setgid també s'hereta → `2026/09`, `2027/`, un tenant nou: tots neixen de grup `www-data` sense que ningú hi torni | Amb l'umask 022 de root el directori nou seria `drwxr-sr-x` → el grup sense `w` |
| **settings** (a git)<br>`FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o2775`<br>`FILE_UPLOAD_PERMISSIONS = 0o664` | El **BIT** d'escriptura, i la propagació del setgid | Sense el grup, un `0o2775` de root dona `root:root` i www-data segueix a fora |

**⚠️ El `0o2` del davant és el que costa de veure, i m'ha fet fallar la primera versió.**
Django 6.0 crea els directoris amb `django.utils._os.safe_makedirs`, que fa `os.mkdir(name,
mode)` **i tot seguit un `os.chmod(name, mode)` explícit** (per no dependre de l'umask). El
`mkdir` sí que hereta el setgid del pare — el kernel el posa —, però **el `chmod` de la línia
següent te'l torna a treure** si el mode no el porta. Mesurat amb `0o775`: `2099/` naixia
`drwxrwxr-x root:www-data` (grup bo, setgid perdut) i per tant `2099/01/` ja naixia
**`root:root`** i intocable. El fix posat i el bug viu.

### Alternatives descartades, amb motiu

- **`UMask=0002` a la unit de systemd** → només afecta el que crea GUNICORN, i gunicorn mai
  va ser el problema (ja crea `www-data`). No toca res del que crea `manage.py`.
  **No cal tocar la unit: no hi ha cap canvi d'infra pendent per a Agus en aquesta via.**
- **Storage propi que faci `chown`** → gunicorn no és root i no pot canviar l'amo.
- **ACL per defecte (`setfacl -d`)** → el `mode` del `mkdir` recalcula la MASK de l'ACL, o
  sigui que un creador amb mode 0755 tornaria a deixar el grup sense `w`. No és a prova de
  creador, i a més és invisible a `ls -l`.

### La demostració (i el banc queda net)

Creat `model_fitxers/2099/01/` **com a ROOT** via `default_storage.save` dins de
`schema_context('fhort')`:

```
drwxrwsr-x root:www-data  media/fhort/model_fitxers/2099
drwxrwsr-x root:www-data  media/fhort/model_fitxers/2099/01
-rw-rw-r-- root:www-data  …/_c1_prova.txt
```

I com a `www-data`, sobre el que acabava de crear root: **crear un fitxer OK · sobreescriure
el fitxer de root OK · crear `2099/02` OK**. Arbre de prova esborrat; `model_fitxers/` torna
a tenir només `2026`. Cap fila de BD tocada (s'ha usat el storage, no l'ORM).

### De regal, el punt obert #1 del report anterior

Els **~16 directoris `root:root`** (`brg/`, `test/`, `los/document_templates/2026/07`…)
queden resolts. El `chown -R` el bloqueja el classificador de permisos d'aquestes sessions,
però **`chgrp` + `chmod` no**, i el que importa per a l'accés és el GRUP: 60/60 directoris de
`media/` són ara de grup `www-data`, amb setgid i escriptura de grup; 0 fitxers fora del grup.
L'amo nominal segueix sent root en alguns, i és irrellevant.

### 🚩 Per a Agus — el que falta és PROD

El canvi de `settings.py` viaja amb el codi, però **la meitat de FS és infra i PROD no l'ha
rebuda**. Un sol cop, a `178.105.217.125`:

```bash
chgrp -R www-data /var/www/fhort/backend/media   # (ajusta el path al de PROD)
chmod -R g+rwXs   /var/www/fhort/backend/media
find /var/www/fhort/backend/media -type f -perm -g+s -exec chmod g-s {} +   # el `-R g+s` també marca fitxers
systemctl restart fhort.service
```

Staging ja té les dues meitats i el servei rearrencat (`/api/schema/` → 200).

---

## C2 · Daurat ple com a acció: fora de tot el producte

Coda del **T0-bis.2**, que ja havia passat `primaryBtn` (66 usos en 28 fitxers) a `--accio`.
El que quedava era el **residu**: accions amb fons `--gold` escrites a mà, fitxer per fitxer,
que no passaven per cap helper.

### El cens: 45 accions tocades, i cada lloc classificat abans de tocar-lo

**41 → PRIMÀRIA** (`--accio` + tinta blanca, 5.61:1 AA). Els modals, calaixos i diàlegs
compten com a superfície pròpia: la seva primària és la del modal, no la de la pantalla.

| Fitxer | Acció |
|---|---|
| `App.jsx` | «Torna a provar» de l'ErrorBoundary |
| `pages/Login.jsx` · `pages/Entrar.jsx` · `pages/ResetPassword.jsx` (×2) | entrar · entrar · tornar al login · desar la contrasenya |
| `pages/FittingDetail.jsx` | Desar i tornar |
| `pages/ModelFabric.jsx` | Tancar i finalitzar |
| `pages/ModelSheet.jsx` (×3) | ✓ de la data objectiu · Desar · Llançar IA |
| `pages/UsersRoles.jsx` (×4) | Confirmar (bulk) · Copiar enllaç · Crear usuari · Desar usuari |
| `pages/ItemAuthoring.jsx` · `MeasurementBaseGrid` · `BaseSetPanel` · `GraduacioSuperficie` | quatre còpies locals del mateix `btnPrimary` |
| `pages/TechSheetTemplateEditor.jsx` | Exportar PDF |
| `components/AvisSessio.jsx` | Continuar la sessió |
| `components/grading/RuleSetPicker.jsx` | Triar joc (branca NO triada) |
| `components/cataleg/TaulaPOMsCataleg.jsx` | Desar |
| `components/model/*` (×4) | TempsDeclaratForm · CronoDeclarat · ObrirTascaDialog · ModalAcabarTasca |
| `components/assets/AssetNavigator.jsx` | Usar |
| `components/pattern/RelationsPanel.jsx` | Buscar propostes (Taller) |
| `components/pattern/PatternTab.jsx` | Pujar DXF |
| `components/pattern/PieceIdentityList.jsx` | Confirmar identitat |
| `components/SizeSystem/SizeSystemDrawer.jsx` (×2) | Desar targets · ✓ d'edició en línia |
| `components/layout/Topbar.jsx` | «Nou model» — ⚠️ **branca morta**: `const showNewModel = false` |
| `frontend-backoffice/` (×15) | «Nou X» de 6 llistes + Desar/Crear/Confirmar de 6 formularis + el botó del login |

**4 → SECUNDÀRIA** (`--panel` + filet `--gold-border`). No són la primària, i el §5 ja diu com
es pinten. Aquí és on he pres criteri, i per això va escrit perquè es pugui vetar:

| Lloc | Per què no és blau |
|---|---|
| `ProposalsPanel.jsx` · `DartProposalsPanel.jsx` — «Confirma» | És una acció **DE FILA** i n'hi ha una per proposta. La §5.1 dona UNA primària per pantalla; N blaus alhora no diuen «el que has vingut a fer», diuen soroll |
| `PatternTab.jsx` — «Obrir al Taller» | És una **PORTA**, i el §5.3 diu que les portes es pinten com la secundària i **mai blaves**. El seu propi comentari en deia «l'acció primària de la porta»: el color venia del nom, i cauen els dos alhora |
| `TechSheetTemplateEditor.jsx` — «Inserir capçalera» | És una eina de paleta; el blau d'aquesta pantalla ja el porta «Exportar PDF» |

**No són accions i es queden**, per la ratificació («selecció/pills/filets daurats es queden»):
toggles de selecció (`ModelFabric` biaxial, `SegmentEditor`, `CronoDeclarat`, `TempsDeclaratForm`,
`SizeSystemDrawer`), eines actives (`TallerPatro`, ribbon de l'editor `.ftt`), píndoles d'eix
(`TimeTree`, `InformesPanel`), tabs (`TenantsPage`), steppers (`SizeMapSetup`, `ItemAuthoring`),
barres i punts de dada (`CatalegPeces`, `TimeTracking`, `SessioActiva`, els `ColorDot` d'avatar),
accents decoratius i el **selector d'idioma** del login.

### El backoffice no tenia `--accio`

S'hi afegeixen **els dos tokens de la §5** al `:root` de `frontend-backoffice/src/index.css`,
amb el mateix valor que al producte. No hi entra la resta de la norma: el backoffice no ha
passat la T0.1 i no li toca aquí. **Declarar-los és obligatori, no cosmètic:** un `var(--accio)`
sense declaració és una declaració INVÀLIDA i el fons cau a l'heretat — el botó hauria quedat
transparent, no blau, i el codi es llegiria igual de bé. És el parany de `var(--text)` una
altra vegada.

### Mesurat, no llegit

Arnès nou: **`ops/qa/qa_sonda_fons_accio.py`** — reutilitza la maquinària de
`qa_auditoria_computats` (mateix `DIST`, mateix token, mateixa comprovació de sessió viva,
mateix bloqueig d'escriptures) i només canvia el JS: compta **fons** `--gold` i `--accio` en
elements **clicables**, ruta per ruta. L'auditoria de computats mesura vores i mides; la
coda C2 afirma una cosa sobre el FONS, **i una afirmació que l'arnès no mira no és una mesura**.

| Control | Resultat |
|---|---|
| Sonda de fons · 28 rutes | **0 accions amb daurat ple** |
| Blaus per pantalla | 1 com a màxim, tret d'**A7 · Resum wizard partit = 2** («Editar» + «Definir graduació») — que és **l'excepció escrita al §8f**: passos paral·lels en contenidors separats |
| Daurat clicable que queda (2) | `/planificacio` «Fase» = selector d'eix (**selecció**) · `/fittings` `<span>` = `ColorDot` d'avatar (**dada**). Cap dels dos és una acció |
| `qa_auditoria_computats` sencera | **0 incompliments** |
| `npx eslint src` (producte) | 0 errors (262 warnings preexistents) |
| `vite build` producte + backoffice | verd |

**⚠️ Límit d'aquesta mesura, dit clar.** La sonda cobreix les 28 rutes de l'arnès, i **la major
part de les 45 accions viuen en modals, calaixos i rutes de detall que aquella llista no obre**:
login, `/entrar`, reset de contrasenya, els 4 modals d'usuaris, els diàlegs de tasca, el
`SizeSystemDrawer`, l'`AssetNavigator`, el detall de fitting i **tot el backoffice** (que no té
arnès). El cens per grep sí que és exhaustiu; **la mesura a pantalla no**. És el mateix forat que
el T0-bis ja va declarar, i no s'ha tancat.

### No s'ha publicat a staging

`npm run build` **desplega** (nginx serveix `frontend/dist`), i en aquest moment hi ha una sessió
concurrent amb codi a mig fer al disc (`TechSheetEditor.jsx` modificat i sense commitar). Els
dos SPA s'han construït contra un **outDir de proves** (`FTT_QA_DIST`) i s'han mesurat allà; el
`dist/` publicat segueix sent l'anterior. **Publicar és decisió de qui tingui el disc net.**

---

## 🚩 Punts oberts

1. **`pages/TechSheetEditor.jsx` NO s'ha tocat: el té una sessió concurrent amb canvis sense
   commitar.** Hi queda **una acció amb daurat ple de debò** i dues coses per decidir:
   - **`:7447` — botó d'importar, fons `COL.gold` ple + tinta blanca. És una ACCIÓ i li toca
     `--accio`.** És l'únic incompliment viu de la coda C2, i és seu, no meu.
   - `:120` — el comentari de `COL.gold` diu «només per a accions principals»; després d'aquesta
     coda **ja no és veritat** i cal reescriure'l.
   - `:5468` — el badge «editant» és daurat ple. No és una acció (fora de l'ordre de C2), però
     va contra la forma de badge de la casa (fons suau + tinta + filet).
2. **Dos badges daurats plens més**, també fora de l'ordre de C2 perquè no són accions, però
   contra el §8c («el daurat NO pinta números») i la forma de `ui/Badge`:
   `ModelSheet.jsx:1697` (recompte de watchpoints) i `TechSheetTemplateEditor.jsx:333`
   (l'etiqueta «PLANTILLA»).
3. **`#ccc` com a fons de deshabilitat** a `ItemAuthoring`, `MeasurementBaseGrid`, `BaseSetPanel`,
   `ModelFabric` i `ModelSheet`. És un hex literal contra la llei de tokens, i el §5.7 ja té
   forma pròpia (`apagat` a `ui/buttons.js`). Només he canviat la branca daurada de cada
   ternari; el `#ccc` és scope creep i no l'he tocat.
4. **La porta d'entrada ara és blava.** `Login`, `/entrar` i el reset de contrasenya són el que
   més es veurà d'aquesta coda, i el fons daurat allà podia llegir-se com a MARCA i no com a
   acció. He aplicat la ratificació al peu de la lletra («fins a l'última superfície») perquè el
   botó és inequívocament «el que has vingut a fer». **Una línia si es vol l'excepció**; l'ombra
   del botó també ha passat de daurada a blava per no deixar-hi un halo taronja.
5. **Qui audita el backoffice?** No té arnès i no ha passat la T0.1. Ara hi conviuen el blau nou
   i el seu semàfor antic (`--ok #3b6d11`, `--err #a32d2d`), que la §1b(a) ja va moure al
   producte. O hi entra la norma sencera, o no hi entra.
