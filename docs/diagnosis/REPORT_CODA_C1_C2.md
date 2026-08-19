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
4. ~~La porta d'entrada ara és blava.~~ ✅ **DECIDIT PER AGUS el 09/08: la porta d'entrada torna a
   DAURAT PLE, i és l'EXCEPCIÓ ÚNICA del producte.** Motiu: allà encara no s'és dins del producte,
   s'és davant de la **marca**. Revertit a `Login`, `/entrar`, el reset i la porta bessona del
   backoffice; l'ombra del botó torna al taronja. **L'excepció s'ha ESCRIT a tres llocs** perquè
   no la «corregeixi» ningú en un cens futur: `NORMA_LAYOUT.md` §1 · Acció, un comentari a cada
   fitxer, i la sonda. ⚠️ **La tinta de la porta del backoffice SÍ que canvia**: hi tenia `#fff`
   sobre daurat (**3.44:1**, per sota d'AA) i la §1 escriu que la tinta d'aquesta excepció és
   `--text-main` (4.91:1, la solució de S37). El blanc hi era des d'abans de la norma i el blau
   de C2 el tapava per accident; en tornar el daurat, tornava també el defecte.
5. **Dues respostes a la mateixa pregunta: «Exportar PDF».** La coda de fusió de capçaleres
   (commits `133496e2`/`2353c222`, sessió concurrent) va pujar l'«Exportar PDF» de l'editor
   `.ftt` al `PageMenu`, on el §8e li treu el color: **aquella pantalla queda sense cap blau**.
   El seu germà `TechSheetTemplateEditor` fa la MATEIXA acció i aquí li he posat el blau,
   perquè encara es pinta la seva pròpia capçalera i no ha passat la fusió. No és una
   contradicció de criteri —les dues segueixen la norma des d'on són—, però **el mateix botó
   es veu de dues maneres**, i això s'arregla absorbint també el template editor al bastiment
   comú, no repintant-lo.
6. **Qui audita el backoffice?**
7. ⬇️ **La cua «Sistema → wizards → STOP de lot» JA ESTAVA FETA** — v. la secció final. No té arnès i no ha passat la T0.1. Ara hi conviuen el blau nou
   i el seu semàfor antic (`--ok #3b6d11`, `--err #a32d2d`), que la §1b(a) ja va moure al
   producte. O hi entra la norma sencera, o no hi entra.

---

## 🛑 LA CUA SEGÜENT JA ESTAVA FETA — i no la refaig

Encàrrec rebut: *«Sistema (Encàrrecs · Catàleg de tasques · Perfil · Recursos) → wizards
9·10·11 → STOP de lot»*. **Els tres trams existeixen ja, commitats per la sessió S1**, que ara
va pel 279. He anat a mirar-ho abans de tocar res, i el que hi ha és exactament la cua sencera:

| Tram de la cua | On és | Què conté |
|---|---|---|
| **Sistema** | `99463960` · «258 · S1·Sistema» | `TaskTypes.jsx` · `UserProfilePage.jsx` · `Recursos.jsx`, i de retruc `ui/Table`, `ui/Center` i `ui/Badge` |
| **Encàrrecs** | `212` (S2) | conformada abans; el 258 la declara **«verificada, no refeta»** |
| **Wizards 9·10·11** | `c408d7ea` · «259 · S1·B9·B10·B11» | `OnboardingWizard.jsx` (+ i18n que NO tenia: 22 claus) · `BulkImportWizard.jsx` · `SizeMapSetup.jsx` |
| **STOP de lot** | `aaa06f6f` (263) i `eb82f02b` (273) | fitxa de tancament de 24 pantalles · suite 966 tests en verd |

### Verificat per mi, no acceptat

No em refio d'un missatge de commit per dir que una cosa està feta — és la mateixa regla que
S1 es va aplicar al 279 amb la MEVA feina de C1. Mesurat avui, sobre el bundle construït del
codi d'ara:

| Control | Resultat |
|---|---|
| `qa_auditoria_computats` · B9 Catàleg de tasques · B10 Perfil · B11 Recursos · B12 Encàrrecs · B13 Config. inicial · B14 Import massiu | **0 incompliments** a totes sis |
| `qa_sonda_fons_accio` · les mateixes sis | **0 accions daurades**; blaus: 0 · 0 · 0 · 0 · 1 («Començar») · 0 |
| `PageMenu` muntat a les 7 pantalles del tram | ✅ 7/7 |
| Paritat i18n ca/en/es | **4544 = 4544 = 4544**, 0 claus òrfenes en cap direcció |
| `background: var(--gold)` ple a les 7 | 1, i és el **punt del stepper** de `SizeMapSetup` (selecció, no acció) — i aquell `export default` no té ruta |

### Per què NO la refaig

Refer-la seria una segona passada divergent sobre fitxers d'una altra sessió viva, sense un sol
defecte mesurat que la justifiqui. És literalment la lliçó que el 279 va escriure a partir del
meu propi treball: **una llista d'accions caduca pel treball que s'ha fet mentrestant, i el que
no es revisa és justament el propi.** El 279 va matar el seu punt 8 perquè el meu C1 ja l'havia
resolt; aquest tram és el mateix cas amb els papers canviats.

🚩 **Per a Agus, la pregunta que sí que canvia la feina:** si aquesta cua era per a mi i no per
a S1, digues **què hi vols de diferent** (una segona lectura bidireccional? un tram nou?), perquè
tal com està escrita ja té les quatre pantalles i els tres wizards tancats i mesurats. Si era la
cua de S1, aquí no hi ha res pendent i el meu STOP de lot és aquest report.
