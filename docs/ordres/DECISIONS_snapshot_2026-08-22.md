═══ S44 (2026-08-19) — LLEIS DE LA FINESTRA DE MIGRACIÓ ═══

⚖️ OPERATIVA DE MIGRACIÓ:
· El mètode de finestra: dry-run → llista a l'humà → OK explícit → apply ORM
  amb GUARDA DE RECOMPTE EXACTE (RuntimeError dins l'atomic si ≠esperat) →
  verificació independent → idempotència demostrada en viu. Cap pas destructiu
  sense les sis peces.
· S'aplica EL CRITERI, no la xifra: si la guarda atura perquè el recompte no
  quadra, l'error és de la xifra derivada, no del criteri (el 19≠17: LIKE pel
  nom vs client real).
· L'assaig contra còpia restaurada al mateix clúster és obligatori abans de
  migrate a PROD: cobreix les N migracions reals, costa MB i minuts, i toca
  zero files vives. L'assaig es fa amb el dump POST-reparacions (el verge
  donaria vermells falsos).
· git fetch IMMEDIATAMENT abans de cada merge de deploy: el stale ref ha
  intentat colar un tren incomplet 3 cops en una setmana. El diff contra el
  commit ASSAJAT ha de ser buit abans del migrate.
· Els backups es verifiquen per FILES DINS (recomptes), no per EXIT=0 ni mida.
· Match per clau «igual» entre catàlegs NO és match de significat: mateix codi
  pot ser cota diferent (37/69 col·lisions CI eren cotes distintes). Tota
  fusió/enllaç automàtic exigeix comparació de CONTINGUT, i en dubte s'aparta
  (sufix -ANTIC), mai es fusiona.
· La clau d'idempotència d'una sembra no pot ser un camp que la migració
  mateixa rebateja (nom → codi_sistema abans del rebateig, mai després).

⚖️ AUTOMATISMES I SENYALS:
· Abans de sembrar files que un signal pot reclamar, CENS DE SIGNALS: la
  signatura (task NULL + dades NOT NULL) era propietat del watchpoint de
  sistema i el post_save l'hauria reescrit (el #59 n'era la prova viva).
  QuerySet.update() no dispara senyals — és l'eina per operar sota signals.
· No es dedueix absència de l'absència de proves: dades sense font (los amb
  mostres però 0 timers) es PROTEGEIXEN, no es posen a zero.
· Un corpus estadístic que compta el mateix treball N cops (multi-tancament)
  no es repara esborrant: es RECONSTRUEIX des de la font primària, i les
  cel·les sanes reproduïdes exactes són el test de correcció de franc.

⚖️ ARQUITECTURA DEL TRÀNSIT (decisions Agus):
· La restitució de catàleg és CONSEQÜÈNCIA de la reconstrucció dels models,
  no prerequisit: les PROTECT manen l'ordre. El catàleg nou entra ADDITIU;
  el vell mor com a arxiu (actiu=False), s'esborra quan ningú l'apunti o mai.
· Al món nou la relació model→ruleset compartit és OPCIONAL (regles residents
  graden soles); re-apuntar GTI és lot d'una tarda, no obra de setmanes.
· TOTS els models del trànsit com a pendents quan la dicotomia acabat/en-curs
  no és derivable de les dades: el watchpoint és l'instrument, no el NULL.

⚖️ JUBILACIÓ (reforç): jubilar ≠ amagar — verificar QUÈ filtra cada selector
abans de prometre l'efecte (el del wizard no mirava ni actiu ni client).
═══



⚖️ OPERATIVA GIT/DEPLOY:
· git commit <paths> SEMPRE, no només git add <paths>: un commit sense pathspec
  s'emporta TOT l'staged, inclòs el d'una sessió concurrent (2 incidents mirall
  el 17/08). La protecció no és llegir bé git status: és fer impossible
  l'accident.
· Restitucions de catàleg PER ORM, mai SQL directe: les FK PROTECT de Django
  són NO ACTION a la BD — un DELETE per SQL orfena milers de files en silenci.
· psql -c ignora default_transaction_read_only en transacció ja oberta: el
  blindatge read-only real és PGOPTIONS, i es verifica en les DUES direccions.
· Tota afirmació d'un cens sobre «el tren» es contrasta contra origin/dev:
  un agent que mira el repo local de PROD reporta absències falses.

⚖️ DOMINI:
· PRESA ≠ DECISIÓ ≠ PROPAGACIÓ: tres gestos, tres permisos. El guard es
  parteix per CAMP, no per endpoint (un payload mixt cola el veredicte per la
  porta de la presa).
· El SIZE SET és la CORBA DEL MODEL (GradedSpec/consolidat); una sessió
  l'ENRIQUEIX amb preses. Taula de fitting sense fitting NO existeix (no és
  una taula incompleta: és una taula que no toca).
· Un mateix predicat canvia d'ONTOLOGIA amb el moment del cicle:
  liniaTeContingut a presa viva (real==teoric → «no mesurada») vs sessió
  tancada («arribà clavada»). Reutilitzar un predicat exigeix verificar que
  el moment és el mateix.
· La marca de gest (presa_at) es mira PRIMERA; la inferència pels valors
  queda DARRERE per a les files anteriors al camp. Cap backfill que endevini
  gestos. Desdir-se treu la marca.
· El 409 sense gest visible a pantalla és un forat d'UX, no una protecció:
  la pantalla ha de saber ANOMENAR l'estat (el 5è estat TANCADA).

⚖️ PODA I CENS:
· Retirada per RUTA, no per funció, quan hi ha bancs penjats de la vista
  (escalat_ajustar_talla_view: 5 bancs; precedent set-size-override 21/07).
  El banc de guàrdia mira urls, no views: només ell cau si algú re-endolla.
· Un grep compta APARICIONS, no consumidors vius: el cens s'escriu abans
  però es TANCA amb el lint a la mà (cens fals de T5, caçat pel gate).
· Claus i18n dinàmiques (t(`prefix.${var}`)) NO es poden podar amb detector
  literal (sessio_segellada; el cens en compta 815).

⚖️ DOCUMENT TÈCNIC (fitxa):
· El sòl tipogràfic (8pt) es defensa CANVIANT DE FULL (apaïsat, partició per
  talles), MAI encongint. Sostre de format: A4 apaïsat 270mm; A3 fora de la
  tria automàtica.
· Capçaleres de columna del document tècnic SEMPRE en anglès via
  getFixedT('en') sobre les claus existents — MAI un segon joc de noms que
  pugui divergir.
═══

# DECISIONS.md — Registre de lleis de disseny FTT

> **Cervell del projecte.** Lleis durables i decisions vives, perquè no es re-litigui ni es
> re-investigui el que ja s'ha decidit en xats anteriors.
>
> **Com es llegeix:** dos tipus d'entrada.
> - **Lleis** (mètode · domini · presentació) = estables, gairebé no canvien. Es consulten ABANS
>   de cada diagnosi.
> - **Decisions d'abast vives** = evolucionen sprint a sprint; s'actualitzen sovint.
>
> **Com es manté:** s'actualitza al final de cada sessió (servidor `/root/fhort-sessions/DECISIONS.md`
> + còpia manual al projecte). Quan una decisió viva es completa, baixa a "Històric" o es promou a llei.
>
> Última actualització: 2026-08-21 (S45: MULTI-BREAK v2 per intervals + DECISIÓ A: matar el camp llegat `increment`)

---

## ⚡ DECISIÓ — LA REGLA DEL MODEL TÉ UNA SOLA FONT DE VERITAT: MOR EL CAMP LLEGAT `increment` (Agus, Patró C 2026-08-21, S45)

**Origen:** DIAGNOSI_BUGS_PROD_837 §A — `set_pom_regim_view` (views.py:5202-5220) mai escriu
`increment`, que queda fossilitzat amb el valor del joc materialitzat; `_apply_rule` porta un
fallback al llegat si `increment_base` és NULL (pom/services.py:1197-1198). 137/1332 regles
LINEAR actives a fhort divergeixen (POM D del 1215: 2,00 vs 0,50). Mina armada, no disparada.

- **LÒGICA DE LA DECISIÓ (Agus):** el tècnic REESCRIU la regla al model, i pel principi de
  sembra (la sembra ofereix, el model posseeix) això és el comportament NORMAL, no l'excepció.
  El mateix passarà quan introdueixi breaks nous al POM del model amb el sistema d'intervals.
  Un camp que conserva «el que deia el joc» contradiu la sobirania del model.
- **Execució (opció 1):** backfill únic `increment := increment_base` a les divergents (137 a
  fhort; censar los) + retirar el fallback llegat de `_apply_rule` + NULL passa a significar
  cel·la absent/error clar (coherent amb llei D2, mai FIXED fabricat ni delta fantasma).
- **PREREQUISIT DUR: banc de paritat reconstruït ABANS** — a PROD no existeix cap
  (BANC-*=0, golden 1320/1322 i POP 268/269 inexistents, només el 163; el «105/105» no
  correspon a cap artefacte localitzable). Banc nou = el 837 sembrat a staging (105 cel·les
  verificades pel recàlcul del Patró A) + POP si encara viu a staging.
- **Inclou de franc:** pantalles coherents — verificar quina superfície llegeix quin camp
  (hipòtesi: el símptoma vist per Agus/Montse era divergència de PANTALLA, no de motor) i
  deixar-les totes sobre la font única.
- Backfill dins del mètode S44 (dry-run → llista → OK → apply amb guarda de recompte).

---

## ⚡ DECISIÓ VIVA — MULTI-BREAK PER INTERVALS (Agus + Montse, Patró C 2026-08-21, S45 — v2, substitueix la v1 de trams del mateix dia)

**Substitueix la nota de disseny futura G6 «break doble lògic»** i la v1 «trams ordenats»
d'aquest matí. Forma validada amb Montse (autoritat de domini).

- **Forma: DELTA GENERAL + N INTERVALS DE SOBRESCRIPTURA.** El delta general afecta TOTES les
  talles per defecte. Cada break = `(talla_inici → talla_final, delta propi)`, inclusius.
  Fora de tot interval, mana el delta general — el retorn és AUTOMÀTIC, mai s'ha d'entrar.
  Exemple canònic: general 2 · break S→L=3 → XXS/XS/XL creixen 2; S/M/L creixen 3.
- **Per què guanya als trams:** menys entrada (un «creix 3 al mig» = 1 línia, no 2 punts de
  tall) · el conveni off-by-one S'EVAPORA (inici/final inclusius i explícits, res a
  interpretar) · la regla es LLEGEIX com es pensa a totes les superfícies.
- **Validació:** intervals sense solapament + inici ≤ final en ordre del SizeSystem.
  Interval d'una talla (inici=final) és legítim.
- **Construcció OBERTA amb signe + a la fila del POM**, al ruleset I a la graduació resident
  del model — mateixa gramàtica. **Només LINEAR** (delta per pas dins l'interval).
  **CONFIRMAT MONTSE/AGUS 2026-08-21: el delta és ENTRE TALLES CONSECUTIVES, mai salt total
  de l'interval** (break S→L=3 vol dir S→M creix 3 i M→L creix 3).
  **⚖️ ACLARIT I SEGELLAT (Agus, 21/08 nit): EL DELTA ÉS ABSOLUT — els cm REALS de cada
  pas dins l'interval, MAI relatiu al break anterior.** «XL +1» = la XL creix 1 cm sobre
  la L (cas F: 114,5→115,5), NO «1 més que el break d'abans». Motius: és com parla la
  tècnica (cm de debò) · el relatiu crea acoblament fantasma (editar un interval mouria
  els posteriors en silenci) · el relatiu és ambigu amb talles a general entre intervals ·
  l'equivalència 105/105 del banc està provada amb lectura absoluta. EL MOTOR JA FA
  ABSOLUT — aquesta entrada existeix perquè cap sessió futura reobri el dubte.
- **Límit: 3 intervals de sortida, constant EN UN SOL LLOC** (5 si un run real ho demana).
  Més enllà → STEP, via d'escapament.
- **EMMAGATZEMATGE DECIDIT (Agus, 21/08 nit): DINS LA REGLA — camp JSON `breaks`**
  (llista d'intervals) a GradingRule I ModelGradingRule, mai taula filla. Motiu: els
  intervals són FORMA de la regla (la comparació de grading és per forma); viatgen de
  franc amb federació/paquets/import/clon (el clon que perdia breaks n'és l'avís);
  precedent intern: valors_step. Constant MAX_BREAKS=3 en un sol lloc.
- **UI VALIDADA (Agus 21/08 vespre, «te la compro sencera»): XIPS D'INTERVAL** —
  a Mesures i Generar Regles, les columnes Δ BREAK + TALLA BREAK se substitueixen per
  una columna BREAKS amb xips «inici → final · +delta» (✕ treu, + afegeix, màx 3 i el
  + desapareix), edició inline amb selectors que NOMÉS ofereixen talles lliures (el
  solapament impossible de teclejar), regla d'1 break pintada com a interval sencer
  «X → última talla · +d» (convenció de motor, l'ambigüitat de document fora de la
  pantalla), inici=final amb fletxa igualment, FIXED inert. Mockup llei:
  proposta_ux_intervals_mesures.html (docs/ordres). Brief F4-bis emès.
- **Migració de la forma actual (1 break «a partir de X»):** tradueix a interval
  `X → última talla del SizeSystem` (el ventall, NO el run). ⚠️ ESMENAT 21/08 (§4 del
  re-ancoratge, equivalència PROVADA 105/105): **CAP desplaçament d'etiqueta a BD** — la
  BD ja desa la CONVENCIÓ DE MOTOR (talla_break_label = on comença el tram comú); l'inici
  de l'interval és l'etiqueta TAL QUAL. L'off-by-one és NOMÉS de la capa de document/
  pantalla (breakConvention.js, 10/08) i allà es queda. El desplaçament que la v2
  original demanava hauria mogut 33/105 cel·les — error de Claude Chat, caçat pel banc.
- S'informa a propagació i taula d'escalat. Cens de cost: secció F de
  DIAGNOSI_BUGS_PROD_837_2026-08-21.md (Patró A en curs). Motor = QA de paritat obligatòria
  (golden POP 105/105 + path 163) — llei RUN-CLIENT (d).

---

## 🏁 SET-2 · ESTAT FINAL (2026-08-12): LES COMPORTES SÓN FORA. Migracions fitting/0027 + models_app/0084. L'única CHECK que queda és la de D3 (codi de peça mai buit), que és permanent. Tota la resta del bloc SET-2 (D1–D7 i lleis derivades) segueix VIGENT com a llei de domini.

## ⚡ LLEIS NOVES — SET-2 MULTIPEÇA: LA PEÇA VIU DINS DEL MODEL (Agus, Patró C 2026-08-10, S39)

**Substrat:** `Diagnosis/DIAGNOSI_SET2_MULTIPECA.md` (Patró A 2026-08-10, 10 blocs, 15 riscos)
+ `Diagnosis/DIAGNOSI_MULTIPECA_DALIA.md` (2026-07-27 — **PARCIALMENT RÀNCIA**: diu que la clau
és `('model','pom')` i que `seccio` es perd a l'extracció; totes dues falses des de 0074 i 0067.
Vigent i únic a DALIA: Q3 parser d'un sol full + cribratge multi-model · Q4 meritació · Q5 bug
talla base).

**El marc:** un model conjunt (pijama = dalt + baix) NO es parteix en N Models. La peça viu DINS
del model. El model neix com una peça i el sistema avança.

- **D1 — EL «BUIT» ÉS SENTINELLA NO-NULL, MAI NULL.** L'eix nou és `CharField(default='')` NOT
  NULL, calc literal d'`instancia`. Les tres actes de la casa queden INTACTES (`models.py:744-745`
  «NULL voldria dir "no se sap", i aquí sempre se sap» · `pom/models.py:917-919` «un constraint que
  existeix i no protegeix és pitjor que cap» · `test_u2_acumulacio.py:7-10`). `nulls_distinct` NO
  EXISTEIX al codi i no s'estrena aquí. **Precedent a seguir literalment: 0070→0078** (7 passos,
  zero backfill, comporta CHECK a BD).
- **D2 — L'entitat i l'eix es diuen `garment`, NO `peça`.** «Peça» ja vol dir Model sencer a
  `PieceFitting`, `Model.piece_number` i `GarmentTypeItemPart.nom_peca` (4 apps). A la UI en català
  seguim dient «peça» al tècnic: la col·lisió és de codi, no de pantalla.
- **D3 — CONVENCIÓ MANDROSA.** `garment=''` és la peça mare i NO materialitza mai fila. En crear la
  2a peça es materialitza la fila del `'02'`. **Cap backfill sobre els 84+1 models vius.**
- **D4 — REOBERTURA CONSCIENT DE L'ACTA de `ModelGradingRule`:** la clau creix amb `garment`.
  Motiu: una peça pot tenir `grading_rule_set` propi (un top alpha + una calceta per mesos), o sigui
  que la llei d'increments POT divergir entre peces. L'acta original («la sisa dreta i l'esquerra
  gradúen igual») parla de **germanes DINS d'una peça** i segueix sent certa. ⚠️ El pin bessó de
  `pom.GradingRule` queda ESTRICTE i es REFORÇA: un ruleset és CATÀLEG, llei reutilitzable, mai
  propietat d'un model — és la línia que marca la frontera catàleg↔model.
- **D5 — El model conserva la definició PRINCIPAL** (run · ruleset · base_size); el `garment ''` n'és
  la cara i editar-lo escriu al MODEL per la porta única; els altres garments porten override
  nullable (NULL = hereten). *«Un top pot anar alpha però la calceta per edat; a la definició
  segueix manant el model.»*
- **⚡ D6 — MESURAR UNA PRENDA ÉS MESURAR TOT EL MODEL. EL SEGELL ÉS DEL MODEL.** (Agus, literal:
  «el fitting afecta a totes les peces; quan el tècnic mesura, mesura el model sencer, no una peça
  a part de les altres, i les decisions es prenen en el model sencer»). Conseqüències dures:
  `FittingSession`, `SizeCheck` i el veredicte **no guanyen mai l'eix**; **no existeix «tancar el
  fitting del dalt»**; el veredicte de Comprovació segueix comptant per fila sobre el model sencer.
  **La peça és PRESENTACIÓ a la taula, mai partició del treball.**
  🔑 **`SizeFitting`/`GradingVersion` amb eix de peça (l'antic F2) DEIXA DE SER DEUTE: és decisió,
  no limitació.** Si una sessió futura ho proposa com a millora, és contradicció de paradigma.

**R4 (estalitud) — CENSAT, NO ES CORREGEIX.** La premissa del brief era falsa: `_generated_from()`
és per `GradingVersion` (`staleness.py:179-183`), i una sola versió conté els `GradedSpec` de TOTES
les peces → moure la base d'una peça deixa la versió realment estala. **L'avís és correcte, no
contaminació.** Amb D6, a més, és el comportament desitjat. La drecera (comptador per garment contra
una versió que cobreix totes les peces) convertiria un fals positiu conservador en **fals negatiu
silenciós** — el forat que el mòdul existeix per tapar. Única peça additiva acceptada (post-T5): un
cop el signal F1 copiï l'eix al `MeasurementChangeLog`, l'estalitud pot **anomenar la peça** a
`poms_afectats` — localitzar on s'ha mogut, mai descarregar el destinatari.

**INVARIANT D'ORDRE (esmena al brief, la seva forma correcta):** no és «R3 abans de T2» (era
irrealitzable: el filtre no pot incorporar una columna que no existeix) sinó **R3 VERD ABANS DE
RETIRAR LA COMPORTA CHECK**. Mentre la comporta congela l'eix a `''`, cap garment 02 pot existir i
el filtre de `germanes_de` és un no-op.

**FRONTERA DE CATEGORIA (dissol dos riscos de la diagnosi):** `garment` és eix **DE MODEL**;
`POMPlacement` ancora a `ItemFitxer`, que és **CATÀLEG** → no hi entra mai. I la col·lisió que F11
temia no existeix en aquest disseny: **cada garment porta el SEU `garment_type_item`**, o sigui que
cada peça arriba al seu propi `ItemFitxer`. Això dissol alhora **F11 i R9/F10** («un Model = un GTI»
deixa de ser paret perquè el GTI baixa a la peça).

**SET-1 (`GarmentSet`) NO ES TOCA NI ES JUBILA.** Desplegat i migrat als dos schemes, federació que
el propaga, **0 files vives**. Alçada superior (N Models germans), no xoca. 🚩 **DECISIÓ DE PREU
OBERTA, i és el motiu real per conservar-lo:** la unitat meritada és el Model (DALIA Q4, meritació
ACTIVA amb 33 events) → amb SET-2 **un pijama de 3 peces merita 1**, on SET-1 en cobraria 3. Decisió
d'Agus pendent; cap codi hi toca fins llavors.

**DECISIÓ APROVADA (b) — LES PRESES REESCRITES ES VEUEN.** Quan la bidireccional de germanes reescriu
una presa humana (YT=19 → 13, 22 ms després) avui passa en **silenci total**. S'aprova una secció
informativa «preses reescrites per regla de germana» a la Comprovació (construeix-la un altre fil,
post-deadline). Motiu que descarta el «qui la va definir ja ho sap»: **la missió és preservar el
context perquè QUALSEVOL tècnic pugui reprendre el model, no qui el va definir.** Condició que sí
entra al sprint SET-2: el signal F1 ha de copiar `garment` al `MeasurementChangeLog`, o la secció
neixerà sense poder dir de quina peça parla.

**🚩 OBERT — RUNS DIVERGENTS A LA GRAELLA (STOP declarat, decisió d'Agus).** D5 permet run propi per
peça i D6 obliga a mesurar-les totes a la mateixa sessió → **la mateixa taula ha de prendre mesures
de dos runs alhora**. `MeasureGrid` agrupa COLUMNES per talla i dues peces amb runs diferents no en
comparteixen; la identitat de fila NO ho resol. La diagnosi SET-2 no ho cobreix (va mirar files, no
columnes). Es censa i es reporta el cost; **no es construeix sense que Agus ho vegi.**

**Fora del radi, confirmat per cens:** Kanban/tasques (impermeable, 2 punts i cap és lògica de
tasques) · billing (5 escriptors, cap sota el Model) · el `.ftt` (round-trip d'objecte OPAC, provat
amb test → `garmentId` a l'objecte és gratis i sense migració de documents; a la PÀGINA seria 4
punts, i per això no hi va).

**Absències confirmades:** `ModelPiece` NO EXISTEIX (0 hits) · numerador de peça INTERN (dins d'un
model) NO EXISTEIX — el `-01/-02` d'avui és de **Models germans** sota un GarmentSet.

---

## ⚡ LLEI NOVA — FEDERACIÓ v3: INTERACTIVITAT PER SUPERFÍCIE (Agus, Patró C 2026-07-27)

**Substrat:** DIAGNOSI_FEDERACIO_INTERACTIVITAT.md (cens Patró A 2026-07-27: 26 famílies
d'estat, calaixos A=14 camps · B=13 · C=14; transport únic = traspassa, unidireccional,
crear-si-no-hi-és; taula de riscos R1–R14). Condició nova d'Agus: Brand i Studio poden fer
tasques sobre la mateixa peça (ex.: LOSAN fa fittings mentre FHORT fa POM+fitxa; herència
creuada i refacció).

- **MODEL D'INTERACTIVITAT: TESTIMONI PER SUPERFÍCIE/TASCA, mai per model.** Cada superfície
  del calaix C té UNA mà en cada moment; la TASCA és la clau natural del testimoni (fitting
  governa C4→C1; POM governa C1/C2; fitxa governa C9). Simultaneïtat entre cases per
  superfícies DIFERENTS: legítima. Dues mans sobre la mateixa superfície: mai.
  Descartades: sincronia per events (fora de mida, R13) i partició estàtica (R7).
- **MÀ DE TREBALL cross-schema**: registre a `public` (patró meritació/receivers, amb
  actor_schema), clau (brand_codi, codi_intern, task_type per slug — mai PK, regla G9).
  Obrir tasca = reclamar la mà; l'altra casa rep bloqueig honest (qui + des de quan).
  **PAUSADA CONSERVA LA MÀ** (pause guarda la posició; el mig-fet és local i no
  materialitzable — alliberar-la regalaria R1). Alliberament NOMÉS per: Stop
  (Done + materialització) · cessió conscient (el mig-fet queda local, no viatja) ·
  TTL d'inactivitat amb confirmació. Mai robatori silenciós.
  **Degradació:** pont no ACTIU → la mà NO bloqueja (llei "cap dada es destrueix / el token
  no governa la capacitat de treballar": cada casa conserva i treballa el que té).
  Reassignació intra-casa (handoff PLA_DE_TREBALL) intacta: la mà és DE LA CASA.
- **RELLEU = materialització per superfície amb DIFF CONSCIENT** (motlle promoció
  model→item: dry-run + diff + confirmar qui rep). Mai merge automàtic, mai
  últim-escriptor-cec cross-schema. L'entrada al destí es registra al log local amb
  origen/context FEDERACIO. R11 vigent: `traspassa` segueix sense actualitzar mai;
  la re-materialització és el relleu, no un upsert del traspàs.
- **FASE (C7/R2): la canònica és del BRAND** (la casa). El Studio té fase operativa local;
  el relleu de lliurament la reporta; el gate que autoritza Producció (C14) és el de la casa.
- **WATCHPOINTS (C8/R5): els oberts viatgen SEMPRE al paquet de relleu, en les dues
  direccions** — compleixen la seva pròpia llei ("viatja amb el model") a la frontera.
- **PAQUET v1 per superfície:** C1 (mesures + entrada al log) · C2 · C3 (re-materialització
  de versió activa al destí respectant la invariant G6 LOCALMENT) · C8 · C11
  (measurements_version com a segell comparatiu, mai fusionat). C4/C5 viatgen com a
  HISTORIAL DE LECTURA (el veredicte viatja via C1/C2; la sessió és de qui la va fer).
  C9: snapshot del document lliurat SÍ; edició creuada NO (el lock no ho pot prometre, R4).
  **C12 POMPlacement FORA** (llei F2b: independent per schema, font compartida — la
  re-sembra des del .ai és el transport). C13 patterns fora (zona intocable).
- **Banderes R8/R9 (fix independent i barat):** `garment_type`, `target`, `construction` i
  el bloc `fabric_*`/`shrinkage_*` s'afegeixen al traspàs inicial.
- **Capa de visibilitat (opció 4, des del dia u):** la UI declara sempre la doble instància
  ("aquesta peça té instància a X") — mai suggerir que les dues cases miren la mateixa fila.
- **Ordre d'execució:** (1) setmana-2: UI del token + assignació per-model HTTP (avui
  command-only, R12/§4.2) → (2) mà de treball a public → (3) relleu per superfície v1.

**LLIÇONS DE MÈTODE S27 (2026-07-27):**
- **DRF i els camps mandrosos:** declarar un camp de serializer fora de `Meta.fields` peta
  amb 500 en runtime mentre `manage.py check` és verd. Regla nova de brief: EXERCIR cada
  serializer tocat (crida real o test) abans del commit. (Cas: customer_language.)
- **El log no menteix:** tota transició automàtica porta marca `auto=<slug>` (mai boolean,
  mai text lliure; slugs estables sense choices, patró FederacioError). L'exclusió
  una-InProgress signava com a gest humà des de sempre — corregit.
- **Higiene compartida:** el llindar de plausibilitat (trams >24h) és UNA constant que
  comparteixen data-op, recompute i `_real_minutes` — el criteri viu a un sol lloc; el
  recompute que rellegeix cru sense la regla reprodueix la contaminació. L'històric 1-24h
  només és destriable amb sostres HUMANS per task_type (paquet Montse).

---

## ⚡ LLEI NOVA — ELS DOS RÈGIMS DE LA COTA (Agus, Patró C 2026-07-26)

**La llei «LLM mai dibuixa coordenades» protegeix la geometria SOBIRANA (DXF, motor de
patrons) i NO aplica a la fitxa tècnica, que és camp INFORMATIU.** Verificat a la diagnosi:
la llei viu al motor (`patterns/engine/ports.py`), i la fitxa ja guardava la frontera a
posta (cota = dibuix sense binding). Conseqüències:
- Sobre el croquis de la fitxa, la IA POT proposar col·locacions de cotes (coordenades
  normalitzades) perquè no hi ha veritat mètrica a corrompre: el valor viu a la taula de
  POMs; la cota diu ON es mesura, mai QUANT. Tolerància d'error = visual-humana.
- El vincle cota↔POM és NOMÉS LECTURA (llegeix el POM viu per a l'etiqueta; mai escriu
  valors de mesura → frontera G1 intacta).
- Al DXF sobirà, la llei original segueix intacta i sense excepcions.
- Tota proposta IA passa per mode revisió humà (motlle DictionaryWizard: proposta +
  confiança + confirmació, mai autoescriptura). Els POMs no col·locables s'informen en
  llista de treball manual — mai absència silenciosa (una cota mal posada costa més que
  una d'absent → llindar de confiança conservador i configurable).

**DECISIÓ VIVA — COTES POM SOBRE SKETCH (aprovat Agus 2026-07-26, fases F0–F3):**
- F0 (sense codi): reunir originals SVG LOSAN/Brownie (n'hi ha) + benchmark de col·locació
  amb el corpus ràster com a joc de proves auto-etiquetat (separació capa vermella/flat
  verificada empíricament) + pregunta a Montse sobre format natiu de les fitxes.
- F1: promoure la cota `cota_pom` EXISTENT (TechSheetEditor, dibuix mort) a vincle viu de
  lectura (`pom_id`/`bm_id` + etiqueta re-derivada). Sense migració.
- F2: entitat `POMPlacement` (models_app; FK POMMaster PROTECT; coordenades normalitzades
  PER VISTA, mai per pàgina) + sembra idempotent des dels SVG (motlle
  seed_losan_master_delta: dry-run + invariant-abort).
- F3: endpoint de visió (imatge de pàgina + llista POMs → JSON placements; client Anthropic
  ja multimodal, 0 canvi) + mode revisió (greenfield sobre visible/layer + patró
  isPendentVincle/build*Prims).
- Cascada runtime: precedent exacte → transposició peça germana → IA → llista manual.
  El cost IA decreix amb l'ús per disseny (mateix patró d'actiu acumulatiu que
  CustomerPOMAlias / Welford / GradingRuleSet: aquí s'acumula la COL·LOCACIÓ).
- Acció per PÀGINA; normalització per VISTA (una pàgina pot dur davant+darrere+detall).
- Ràster: el tècnic ajusta extrems a mà — acceptat. Fotografia: fora de v1.
- Comercial: no és SKU; ataca el temps per model (mètrica: Welford abans/després).
  Comptador d'ús IA per tenant des del dia 1 (mesurar, no facturar). Mai comunicar com
  a IA (llei de posicionament del motor, idèntica aquí).
- Fronteres zero-contacte confirmades a la diagnosi: motor/traçadora · capa DXF FTT-POM ·
  annotation_views (receptes) · G1 escriptura · G6 · billing.
- DECISIONS D1–D7 TANCADES (Agus, Patró C 2026-07-26):
  · D1 el precedent viu a l'ItemFitxer de catàleg (una veritat); la cascada el resol via
    derivat_de_item EN LECTURA (no herència de dades, no paradigma nou). Ajust del model =
    feina seva al seu .ftt; proposar-lo com a precedent nou = acte conscient.
  · D2 etiqueta visible = àlies de client || codi canònic (pom_code_global); canònic sempre
    com a metadada + tooltip. base_measurements_view s'estén amb l'àlies (prefetch, mai N+1).
  · D3 ingesta de precedents = IA-assistida amb revisió humana (reutilitza F3 apuntat als
    fitxers precedents; parsing pur = optimització futura). Sembra i runtime comparteixen
    pipeline → ràster i vector entren pel mateix camí.
  · D4 camp `view_slot` (evita col·lisió amb `vista` de patterns); slugs oberts, canònics
    front/back/detail (+sufix lliure).
  · D5 crida de visió SÍNCRONA amb guards (timeout explícit al SDK + mida màx. d'imatge);
    async només amb evidència de 502. Deute anotat: el camí wizard SDK no fixa timeout.
  · D6 detecció de vistes v1 = frontend Paper.js (clustering de bounds) per a fitxes noves;
    a la sembra la vista la torna la mateixa crida de visió (D3). Backend per píxel: només
    si els dos camins barats fallen.
  · D7 fall-through de peça = tasks.GarmentTypeItem. Unicitat POMPlacement =
    (fitxer, pom, view_slot).
- RÀSTER (decidit 2026-07-26): F1 indiferent al substrat · F3 rep sempre la pàgina
  rasteritzada (renderPageToDataURL); snap-a-vora = refinament NOMÉS si el fons és
  vectorial, mai mecanisme base · F2 guarda `source_kind` (vector/raster) com a traça;
  caixa per píxels com a fallback de normalització. Precedent validat per Montse val
  igual sigui quin sigui el substrat (la validació dona la qualitat, no l'origen).
- F1 TANCADA (2026-07-26, commits f1ef0ad backend + 9913ea8 frontend/i18n, dev sense push):
  cota viva amb pomId/bmId/pomCanonical, etiqueta client_alias||pom_code_global re-derivada
  a càrrega (skipSave per no encadenar versions .ftt), degradació elegant, colocat/armat per
  id i no per text, G1 intacta. client_alias resolt amb un sol prefetch de CustomerPOMAlias.
  Verificat in-process: model 182, 16 files, 8 amb àlies / 8 al canònic.
  ⚠️ DEUTE QA: round-trip .ftt desar→reobrir, degradació en viu i export PDF==live són
  browser-only, verificats per arquitectura i NO a píxel. Comprovació manual al navegador
  abans de F2a (F2a assumeix que la cota recorda el seu POM); Playwright amb sessió logada
  queda com a deute anotat, no bloquejant.
- PARTICIÓ DE F2 (Agus, Patró C 2026-07-26): D3 (ingesta IA-assistida) feia que la sembra
  depengués de F3 → dependència circular. Es parteix:
  · F2a — precedent viu: entitat POMPlacement + cascada (exacte→germana→buit) + consum a
    l'editor + acte conscient "desar com a precedent" + view_slot assignat pel tècnic.
    CAP IA, CAP sembra. Valor sol: la segona fitxa del mateix item neix amb cotes.
  · F3 — visió + mode revisió (com estava).
  · F2b — sembra massiva dels SVG LOSAN/Brownie reutilitzant F3 + detecció auto de vista.
  El corpus de precedents comença a créixer des del dia u amb feina que ja es fa igualment.
- FASE 2 SEMBRA — DECISIONS Patró C (Agus, 2026-07-27, sessió S28 MODELS PROD):

  · OPCIÓ B DE NORMALITZACIÓ: PlacementProposal guarda la proposta CRUA (coords en espai
    d'artboard + caixa usada + view_bbox candidata, nullable); la NORMALITZACIÓ PER VISTA es
    fa A LA VALIDACIÓ humana, quan la vista queda confirmada. La llei "normalitzar per vista,
    mai per pàgina" queda INTACTA a POMPlacement — la proposta no és el placement. Criteri
    d'Agus: transferir tot el viable, no escriure amb dubtes importants; el model es depura
    treballant.
  · PlacementProposal SENSE FK a ItemFitxer (a PROD n'hi ha 0): referencia fitxer·artboard +
    gti; la materialització d'ItemFitxer passa al pas de validació, no a la sembra.
  · 🟢 GATE artboard→GTI AVANÇAT: PLE de 172 artboards TOTS amb GTI, fet per Agus+equip i
    VALIDAT AMB MONTSE. 31 GTIs distints, resolen a `los` per name exacte (0 no trobats).
    El gate dur del 27/07 matí queda satisfet per aquesta via (PLE validat, no cua UI).
  · Dry-run de Fase 2 per SUBCONJUNT primer: PANT PELAYO + CAMI FAST + KID GIRL FLETXES
    (aquest darrer cobreix l'Estil B pastilla-vermella). Si quadra amb xifres conegudes
    (19/19 · 15/15 · Estil B > 0) → lot dels 27.
  · Entrega en dues seccions: A staging (Claude Code: patch + model + migració 0064 + command
    + deps lxml/pikepdf al lock; push d'Agus) → B PROD (checkout → backup → dry-run → OK
    d'Agus → migrate → --commit → auditoria).

- LLEIS NOVES S28 (2026-07-27 vespre, totes DESPLEGADES a main bc409b4):
  · LA FITXA LLEGEIX EL MODEL: T1a i capçalera del PDF usen ruleset si n'hi ha
    i ModelGradingRule/camps propis si no — la graduació resident (D-10) és
    ciutadana de primera a totes les superfícies.
  · seccio és DADA PERSISTENT: BaseMeasurement.seccio (0067); el confirm de
    l'import la desa; la clau ('model','pom') segueix manant (test guardià) —
    el multipeça estructural és SET-2, no la seccio.
  · FEDERACIÓ EN DOS CANALS: DADES = acte humà (envia_a_la_marca, sobirania
    del destí, origen=FEDERAT, mai .ftt viu/PATRO/tasques) · ESTAT = automàtic
    bidireccional (maduresa FTT→LOS via federacio_estat; prioritat+data_objectiu
    LOS→FTT, la marca mana en aquests dos). La marca mai veu hores ni tècnics.
  · L'ANADA porta l'ENCÀRREC (identitat + config + collection/descripcio/
    target/construction/prioritat/data_objectiu), mai la feina.
  · FORMAT DE PÀGINA per pàgina al .ftt (clau opcional retrocompatible);
    capçalera vertical = layout derivat en excepció declarada fins a spec SVG.
  · N fitxes .ftt per model amb nom propi; resolver 0→crea/1→obre/N→tria.
  · SET-1 DESPLEGAT (deploy 2): GTI declara peça/conjunt, mèrit SET=1 ancorat
    al GarmentSet, còpia model→model amb origen COPIED, federació conserva el
    conjunt per codi_base.
- PRECONDICIÓ DE F2a (anotada al brief): el precedent penja de l'ItemFitxer, i un model
  només l'hereta via derivat_de_item → si els sketches s'importen de fora del catàleg, no hi
  ha reutilització. El brief comença amb un guard read-only (recompte ItemFitxer SKETCH_* i
  ModelFitxer.derivat_de_item); si és 0, atura i reporta. Coherent amb LLEI GTI-MÓN (el GTI
  porta els SEUS sketches).
- NORMALITZACIÓ v1: extrems relatius a la BBOX DE L'OBJECTE SKETCH (exacta i gratuïta en
  vector i ràster), no a la silueta ni a la pàgina. bbox-objecte ≠ silueta: acceptat, traçat
  per source_kind, revisable si els precedents deriven.
- F2a LLANÇADA (brief Patró B, 2026-07-26). F3 i F2b pendents de brief.
- ⚡ CONVIVÈNCIA DELS DOS MODELS (Agus, Patró C 2026-07-26) — regla que va a TOT brief de F3,
  sigui quin sigui l'ordre d'execució: **acceptar una proposta de la IA ESCRIU PRECEDENT, no
  només dibuix.** Si la proposta es desa només al document, cada model torna a pagar la crida
  i el cost mai baixa; si aterra a POMPlacement, decau amb l'ús. Amb aquesta regla, l'ordre
  F2a→F3 vs F3→F2a és indiferent estructuralment (només canvia quant es paga d'IA a la
  finestra intermèdia). Ordre mantingut: F2a→F3. Els dos camins conviuran de forma permanent:
  precedent per al que ja se sap, IA per al fred.
- 🔴 TROBALLA DEL GUARD (PAS 0 de F2a, 2026-07-26): **0 ItemFitxer SKETCH_* i 0
  ModelFitxer.derivat_de_item a TOTS els schemas.** El pipeline d'item-fitxers existeix
  (migracions 0054-0056) però no s'ha poblat MAI. Lectura correcta: no és un buit de dades de
  QA, és que **la LLEI GTI-MÓN encara no és operativa** — cap sketch de cap model ve del
  catàleg. F2a n'és el PRIMER CONSUMIDOR REAL (mateix patró que el fix del self-customer com a
  primer consumidor de `tipologia`). El guard va funcionar: va evitar construir sobre un
  substrat inexistent.
  · DECISIÓ: opció 1 — poblar el QA pels ENDPOINTS REALS (1 sketch a l'ItemFitxer del GTI del
    BRW + usar-al-model cap al 182), acció de DADES no de codi, i llavors continuar F2a.
    Descartades: construir a cegues (producte inverificable end-to-end, contra la regla del
    verd) i re-scope a ModelFitxer (seria decidir arquitectura per pressa, contradiu D1).
  · REPORT EXIGIT amb el resultat: **si el camí puja-sketch-a-item → usar-al-model és
    abastable des de la UI o només per API.** Si només per API, F2a s'entregaria sense que
    ningú la pugui alimentar → pot caldre una peça d'UI (informar, no construir).
- ❓ PREGUNTA PER A MONTSE (reescrita per la troballa del guard, 2026-07-26): ja no és només
  "en quin format neixen els flats", sinó **"acceptes col·locar el sketch base a nivell
  d'item?"**. Tota l'economia de precedents penja d'aquest sí. Si diu que no —si per a ella el
  sketch és sempre del model—, llavors penjar precedents de ModelFitxer deixa de ser una
  contradicció de D1 i passa a ser la REOBERTURA CONSCIENT de D1, decidida amb ella al davant
  i mai amb un sprint bloquejat empenyent.
- ⚡ LLEI — LA PROCEDÈNCIA VIU AL SKETCH, NO AL DOCUMENT (Agus, Patró C 2026-07-26).
  El brief de F2a ancorava la cascada a `ModelFitxer.derivat_de_item` (document-level). Error
  meu: la diagnosi ja deia a B1 que `importarDelTenant` **importa una còpia i no vincula**
  (`TechSheetEditor.jsx:4459-4462`) — llegit, citat per als fitxers, i tot i així mal aplicat.
  Evidència dura: 454 tech sheets `.ftt` amb 0 procedència. Claude Code ho va aturar per regla
  del verd (contradicció de paradigma) abans que costés res.
  · **L'ancoratge correcte és a l'OBJECTE sketch** (`sourceItemFitxer`), no al document: una
    fitxa pot dur sketches de dos items alhora (detall, combinació, peça d'un GarmentSet), i
    l'objecte és l'única granularitat on "de quin item ve això" té resposta unívoca.
  · Mateix mecanisme que `pomId` a F1: escalar dins l'objecte, round-trippa sol per l'opacitat
    de `document.json`. Cap `schema_version` tocat.
  · D1 intacte: el precedent segueix vivint al catàleg; només canvia PER ON s'hi arriba.
- HOST-REF — VERDICTE I PUNT CEC DEL GUARD (2026-07-26). `sourceItemFitxer` NO és host-ref:
  apunta al catàleg i ha de sobreviure el canvi de host, com `pomId`→POMMaster. Verificat amb
  27 tests `tests_ftt` verds i `unfreeze_document` conservant `sourceItemFitxer`/`viewSlot`.
  ⚠️ **DEUTE TRANSVERSAL:** part de la justificació era que en camelCase sense sufix `_id` el
  test `test_cap_referencia_de_host` no el veu — el guard **escaneja `*_id`**. O sigui que una
  host-ref real batejada en camelCase passaria en silenci. El veredicte és correcte pel fons
  (semàntica), no per la forma. Mateixa espècie que el symlink d'nginx: un guard que sembla
  cobrir i no cobreix. Anotar per a G8/higiene.
- F2a TANCADA (2026-07-26, 6 commits a dev sense push: 881b79d model+migració 0062 · 8c2e501/
  fb32eb6 endpoints document-level SUPERATS · b877c89 endpoints object-level amb cascada
  EXACTE→GERMANA · d680112/aa99a74 frontend+i18n). `migrate_schemas` + audit de columnes a
  fhort/los. Cascada amb `bm_id` per `?model_id` i `no_al_model` explícit (mai crash ni
  silenci). Frontera G1 intacta.
- OPERATIU REUTILITZABLE: el JWT fet a mà per a smoke tests HTTP **necessita el claim
  `tenant_schema`** (era el que feia fallar la verificació de F1 per resolució d'usuari
  cross-schema). Camí de poblament del catàleg abastable per UI (dues pantalles) → F2a és
  alimentable. Fricció menor anotada: el camp `nom` d'ItemFitxer valida extensió.
- FRED CONEGUT I ACCEPTAT: els 454 `.ftt` existents queden sense procedència i **sense backfill
  possible** (el vincle no ha existit mai; els bytes no diuen d'on venien). Entraran per via
  manual o per F3. ModelFitxer 582 queda vestigial (residu del poblament de QA) — neteja en fred.
- 🧵 TRAM IMPORT SVG (2026-07-26, disparat pel primer SVG de producció LOSAN:
  L27WKG0612_VEGA-3.svg, a media/ de staging — cas de prova canònic d'ara endavant):
  · DISSECCIÓ DEL FITXER (feta a Claude chat, fora del repo): 806 paths = 748 dents de
    cremallera dibuixades una a una (fill gris #9d9d9c) + 19 repunts (stroke-dasharray) +
    ~35 silueta/detalls (traç fosc, fill:none) + 4 hardware amb gradient. El 93% del pes és
    decoració d'un accessori. Les classes CSS d'Illustrator discriminen el rol → separació
    determinista per ESTILS, mai IA.
  · LLEI DE CRITERI (Agus): els REPUNTS són informació tècnica (es conserven amb el seu dash);
    la GRANULARITAT de la cremallera no ho és (l'element sí). Import fidel: res es descarta.
  · FIX PROPORCIÓ (95823a0, opció B — Patró C Agus contra la recomanació A de Claude Code):
    escalat UNIFORME al contingut (Math.min), no al marc del viewBox. Motiu de pes: el marge
    d'artboard és artefacte d'exportació, i amb A hauria entrat a la bbox que normalitza els
    precedents de F2a → coordenades no transferibles entre exports. B preserva la semàntica
    existent (ja es retallava el marge) amb 2 línies.
  · DOS CAMINS D'IMPORT (annex 1262a24): la deformació reportada post-fix NO era el mateix bug
    — "Arxius del model"/biblioteca lateral anava per addModelFitxer → RÀSTER en caixa fixa
    120×80 (ni tan sols vectorial); pujada directa i AssetNavigator anaven pel camí corregit.
    FIX Q1 (3b19686): addModelFitxer bifurca per extensió; els TRES punts d'entrada de .svg
    convergeixen a importFlatSvgText per construcció.
  · PROCEDÈNCIA PEL CAMÍ NOU: sourceItemFitxer = f.derivat_de_item (mai f.id, que és
    ModelFitxer i trencaria l'endpoint de placements). El vincle document-level que F2a va
    descartar com a ancoratge de cascada troba la seva funció real: PONT de procedència quan
    un fitxer de model entra a l'editor.
  · CREMALLERA DESPLAÇADA = TRANSFORMS PERDUTS (annex): mapSegs llegia coordenades LOCALS
    ignorant la globalMatrix que Paper conserva als rects rotats (translate+rotate -70,1°).
    Preexistent i ortogonal al fix B (que només ho va fer visible en tornar la proporció
    fidel). FIX Q2 (6cfea03): transformar punt i nanses (com a vectors) per globalMatrix —
    identitat = no-op per als elements sense transform.
  · ⚠️ VALIDACIÓ A PÍXEL PENDENT (browser-only, declarat honestament als dos sprints): Paper
    no corre headless. La passada manual amb VEGA-3 pels DOS camins és el gate abans de
    l'estratificat.
  · EN CUA: import ESTRATIFICAT (brief emès: grup de 3 objectes per rol — silueta/repunts amb
    dash/detall col·lapsat — heurística per estils, dubte→silueta, capes buides no es creen;
    prerequisit ara = Q1+Q2 validats). Watchpoints no tocats: gradients/clipPath/dasharray
    fora de repunts.
  · LLIÇÓ DE MÈTODE (patró del dia, 3a ocurrència): mai verificar "l'import" en abstracte —
    cada porta d'entrada és un camí propi (dist-tenants 24/07 · document-level F2a ·
    addModelFitxer avui). La verificació es fa contra EL CAMÍ QUE USA L'USUARI.
  · CUA DE CREMALLERA = CLIPPATH PERDUT (3r bug del mateix fitxer, predit literalment a la
    diagnosi Q2 original: "el que el clip amagava pot fer-se visible"). Hipòtesi confirmada amb
    mesura: bbox amb clip 777×334, sense clip 777×417 — la cua vivia entre y=334 i 417. El guard
    de precondició va tornar a pagar: el PAS 2 briefat hauria estat un NO-OP perquè Paper mai
    veia el clip (viatja per classe CSS a <g>, i inlineSvgClassStyles no processava ni <g> ni
    clip-path). FIX 17bd894 (abast ampliat, Patró C): PART 1 inline de clip-path/clip-rule a
    <g> (només clip, mai pintura — no alterar herència de color) + PART 2 retall COGUT A
    GEOMETRIA a l'import amb TRIATGE per bounds (dins→tal qual · fora→descartat · creua→
    intersect booleà de Paper, només aquests · fallit→conservar sencer i COMPTAR, mai perdre
    geometria en silenci · la màscara mai s'emet com a traç). Report de recompte a consola.
    Motiu del retall a import i no clip en render: resultat cuit → zero canvis als dos renders,
    round-trip .ftt i PDF de franc. DESCARTADA l'alternativa bbox (el baix és corbat: canviaria
    un artefacte per un altre). Validació a píxel amb VEGA-3: GATE pendent (Agus, navegador).
- 🖥️ SESSIÓ UI EDITOR (paral·lela, 2026-07-26): C1 babc3e9 cursor lupa amb modificador de zoom
  (zoom-in/out per Ctrl-⌘/+Alt, reset a blur, prioritat màxima a viewportCursor) · C2 91645d5
  pàgines com a persiana del dock dret (mateixa gramàtica que Capes/Camps, miniatures verticals,
  activa en gold, tira inferior eliminada, zero lògica nova de pàgines). Clau òrfena
  tech_sheet.pages → calaix G8. S2 BRIEFADA (en cua): multiselecció estil Illustrator — filet
  per element (NOMÉS overlay de pantalla, mai al camí d'export ni al .ftt) + Shift+clic toggleja
  amb recàlcul del Transformer. Fora d'abast: subpath, marquee.
- ⚠️ REGLA OPERATIVA NOVA (Agus+Claude, 2026-07-26): SERIALITZAR els sprints que toquin
  TechSheetEditor.jsx. Avui dues sessions concurrents hi han commitat (C1/C2 + clip) i ha anat
  bé per zones disjuntes i git add selectiu, però el monòlit de 5.893 línies és el pitjor lloc
  del repo per fer-ne costum (línies desplaçades entre sessions = conflicte silenciós). Una
  sessió activa per fitxer-monòlit.
- 🧭 DIRECCIÓ ANOTADA — PRECEDENTS A DOS NIVELLS (Agus, 2026-07-26, no es construeix ara):
  el motor és de plataforma, les dades per-tenant. Evolució prevista: nivell SISTEMA a public
  (col·locacions base per garment type × POMGlobal × view_slot, actiu FHORT curat per Montse,
  patró POMGlobal/G9) + nivell TENANT (POMPlacement actual) que el sobreescriu. Pont per
  MATERIALITZACIÓ, mai lectura ORM en viu (llei federació). F2b en seria el primer poblament;
  necessita backoffice per governar-lo. Cap decisió de F3 ho contradiu: POMPlacement tal com
  està migrat ÉS el nivell tenant.

---

## ⚡ LLEI NOVA — EL GTI ÉS LA PLANTILLA COMPLETA D'UN MÓN (Agus, Patró C 2026-07-24)

**DEROGA la L0 del 2026-07-18** ("T-shirt és T-shirt per a totes les edats"). Evolució conscient:
- **Eix del catàleg = peça × món**: T-SHIRT NEWBORN, T-SHIRT KID BOY… Cada GTI-món porta les
  SEVES mesures base, els SEUS patrons DXF base i els SEUS sketches. És un contenidor que es
  granularitza en models.
- **El GTI porta el SUPERSET de POMs i mesures de la peça** (coll rodó + pic + obert + perkins);
  el model neix sembrat del superset i el tècnic PODA el que no aplica. La L1 (sembra = oferta,
  el model posseeix) queda intacta i reforçada.
- **Objectiu operatiu que valida el disseny:** model nou = importar POMs correctes amb mesures
  base + podar + vincular grading rule + propagar, en **&lt;5 minuts**.
- **NAIXEMENT MANDRÓS (anti-explosió, Agus):** cap sembra massiva de GTI-món. El sistema DETECTA
  quan cal (model d'un món sense GTI propi) i PROPOSA al tècnic fer-lo néixer des del context del
  model — les relacions neixen ja establertes.
- **Targets = vocabulari del client al seu tenant** (LOSAN: MAN, WOMAN, TEEN BOY/GIRL, KID
  BOY/GIRL, BABY BOY/GIRL, NEWBORN BOY/GIRL). El Studio els consumeix via materialització.
- Efecte col·lateral positiu: la tensió "ItemBaseMeasurement sense eix de món" es dissol — cada
  GTI-món té la seva talla base i les seves IBM sense ambigüitat.
- **PENDENTS (D1/D2):** granularitat exacta del món (target-amb-gènere vs món-de-talles, decidir
  amb la matriu item×target real + resposta física de Montse: el patró base difereix per gènere?)
  · on viu el fit (GTI propi per fit vs fit només a contenidor+bases).


---

## ⚡ LLEIS I DECISIONS NOVES — S22 FEDERACIÓ v2 (2026-07-22/23, decidit Agus Patró C)

**LLEI — FEDERACIÓ v2: LA CASA I EL TALLER (deroga la forma del disseny S01 del 2026-07-07, en conserva la sobirania).**
- **El Brand és LA CASA del model i del patrimoni**: catàleg propi (GT/GTI/SizeSystems/rulesets,
  sembrat a l'onboarding), models canònics, mesures finals i fitxers lliurats. **El Studio és EL
  TALLER**: instància de treball `Model.origen=EXTERN`, tasques, temps, empíric Welford. El temps
  es relaciona amb la tasca → viu a QUI EXECUTA, mai al Brand.
- **El Brand veu RECURS, el Studio veu MODELS.** El recurs és únic ("Studio X"), amb 1 o 20
  persones dins; el Brand mai veu temps ni tècnics — no per permís: perquè físicament viuen en un
  altre schema.
- **El vincle és un TOKEN emès pel Brand** (tria proveïdor tipus studio → genera token → el Studio
  l'introdueix al seu camp de client). Token vigent = pont viu. **El token governa el PONT, mai la
  capacitat de treballar. Cap dada es destrueix mai en aturar o revocar.**
- **TRES ESTATS DE CLIENT legítims per a un Studio** (llei C1): (1) sense tenant — Customer intern,
  com BRW dins fhort: mode de ple dret, cap error; (2) amb tenant + token actiu — federació plena;
  (3) amb tenant + token aturat — el Studio segueix treballant amb el seu Customer intern, només
  el pont s'atura. El pas 1→2 és activar un token, mai una migració.
- **DOS CAMINS DE NAIXEMENT, UNA SOLA CASA**: el Brand crea i assigna, O el Studio l'entra (Excel
  → bulk) i el sembra al Brand. En tots dos casos el registre canònic és del Brand i el codi surt
  de la SÈRIE DEL BRAND. L'EXTERN mai genera codi: el porta.
- **L'EXTERN neix amb IDENTITAT + CONFIGURACIÓ, mai amb feina**: viatgen codi, nom, any/temporada,
  sequencial i els 4 de CONFIG_KEYS resolts per CLAU NATURAL (codi GTI, nom ruleset). La feina
  (mesures, grading materialitzat, fitxes, fittings) neix a ZERO al Studio.
- **Catàleg d'una altra casa: MATERIALITZACIÓ PRÈVIA, mai lectura ORM en viu** (Bandera 3: el
  wizard desa FKs reals). El gateway en viu només per LLISTAR, amb disciplina de dicts
  (schema_context + còpia, llei invoice_pdf). Aplicar = acte conscient (motlle del 409
  GRADING_CUSTOMER_MISMATCH, ja cablejat end-to-end).
- **MERITACIÓ PER ACTOR: qui obre la tasca, paga.** `codi_client` = de qui és el model (casa) ·
  `actor_schema` = qui executa (paga la plataforma). Ja divergien a les dades (9 events LOS
  meritats des de fhort) sense camp que ho digués. *Planificar és gratuït, treballar merita.*
- **TIER FREE = tasques bloquejades passats els 4 primers models amb tasca iniciada pel propi
  Brand.** La resta de funcionals actius (càrrega, planificació, descàrregues). Els models que
  obre el Studio NO consumeixen quota del Brand (els paga el Studio). El Free no pot generar cost
  per construcció: qui no obre tasca, no merita.
- Comercialment: el Studio no necessita els gradings de tots els clients (viuen a cada tenant);
  la plataforma es mostra gratis i cobra quan es treballa; **els Studios són canal de
  distribució** (cada Studio porta N brands com a tenants free).

**DECISIONS TANCADES S22 (les 10 de la diagnosi, Patró C 2026-07-23):**
1. TenantLink viu a `fhort/tenants/` (mai backoffice — no invertir la dependència neta).
2. Referència per CODI NU, mai FK (precedent CodiAuth.tenant_schema).
3. `codi_global`: backfill self-customers + índex unique parcial WHERE NOT NULL. **Fet (P1).**
4. `tipologia` s'activa amb el seu primer consumidor: la validació del TenantLink (marca↔estudi).
   Els tests amb 'MARCA' majúscules → G8/higiene.
5. Actor: backfill retroactiu `actor_schema='fhort'` als 31 events (veritat històrica). Els 18
   BRW són cas 1 legítim, no error.
6. `feature_flags`: PARKED amb billing (Bandera 7 — serializers que el descarten — al rebuild).
7. `/me` ampliat: DIFERIT (via freda `accounts/` quan calgui UI diferenciada Studio/Brand).
8. Sembra de retorn Studio→Brand: dins d'abast, SETMANA 2 — abans del primer lliurament, no de
   la primera tasca.
8b. UI DEL TOKEN (setmana 2, amb la sembra de retorn): costat Brand = secció "Proveïdors"
   (genera token, Aturar/Reactivar/Revocar); costat Studio = camp token a CustomerDetail
   (valida contra public, lliga vincle↔Customer intern via codi_global, mostra estat del pont).
   Fins llavors el vincle s'opera per seed_tenant_link (SSH) — conscient i acceptat.
   Dependència: exposar tipologia al frontend (decisió 7) — la UI del token n'és el primer
   consumidor real.
9. Bulk cross-schema: per management command ara; HTTP quan hi hagi backoffice de vincles.
10. Materialització quirúrgica: vocabulari de BLOCS (motlle SeedProfile), mai pks de catàleg.

**ESTAT D'IMPLEMENTACIÓ (2026-07-23, FINAL — desplegat i operatiu a PROD):** LES 4 PECES + P5/P5b
VERDES I DESPLEGADES. P1 (TenantLink+seed+backfill codi_global) · P2 (Model.origen+exclusió
terra) · P3 (instantiate_external_models) · P4 (actor_schema+backfill) · P5 (bootstrap_tenant
--additive: materialització quirúrgica sense sobreescriure catàleg viu) · P5b (--additive
tolerant a claus ambigües al destí — trobat en viu: 12 codi_client duplicats a
fhort.pom_pommaster, deute de dades pre-existent NO relacionat amb LOSAN; ara se salten
intactes i es reporten a `ambigus_al_desti`, mai es trien ni duplicen). **Tot pushat i mergeat
a `main`, migracions aplicades i auditades als 3 schemas de PROD.**

**RESULTAT REAL A PROD (2026-07-23, migdia):** catàleg v2 de LOSAN materialitzat a `fhort`
(1035 files noves, 0 actualitzades — catàleg propi de fhort intacte, verificat byte-a-byte).
**960 models LOSAN instanciats com a EXTERN a `fhort`** (+2 INTERN antics preexistents, la
col·lisió coneguda LOS-SS27-0001/LOS-SS26-0001, saltats per idempotència de codi). 960 SizeFitting
creades (signal disparat correctament). **579/960 amb ruleset resolt, 381 pendents de graduació**
— la feina real del contracte. Terra de seqüència LOS a fhort: aïllat i correcte (max INTERN=1,
EXTERN exclosos). Vincle TenantLink LOS↔FTT: ACTIU. LOSAN operatiu per a dilluns.

**DEUTE ANOTAT (no bloquejant, per resoldre sense pressa):** 12 codi_client duplicats a
fhort.pom_pommaster (A3,BJ,C1,E4,F1,F2,S,S2,U(×3),U1,V — categoria_id=13 vs NULL en la majoria
de casos) — deute de dades històric de fhort, descobert per l'assaig de materialització, NO
causat per la federació. Pendent de neteja (decidir quina fila és la vàlida per codi).

Diagnosi + verificacions completes: docs/diagnosis/DIAGNOSI_FEDERACIO_V2_CAMI_CRITIC.md,
ASSAIG_FEDERACIO_STAGING_2026-07-24.md, VERIFICACIO_BOOTSTRAP_DESTI_POBLAT.md. Deute fi
menor: el signal manual de numeració ja exclou EXTERN (P2b, tancat).

**PROD LOSAN verificat (2026-07-23):** tenant `los` ACTIU, onboarding complet, pla 3. 961 models,
format únic wizard (LOS-SS27-NNNN), comptador exacte (961=961), 1 customer self (LOS, codi_global
NULL pre-backfill), 2 UserProfiles, catàleg viu (62 GTI, 11 SizeSystems, 19 rulesets, 46
basemeasurements de residu de prova). **381/961 sense ruleset** = la feina de graduació del
contracte. Cadena operativa confirmada (Agus): "els models existeixen a Losan però nosaltres fem
tota la feina" → EXTERN neix amb config, feina a zero a fhort.

---

## ⚡ LLEIS I DECISIONS NOVES — S24 (2026-07-22 tarda, cas real Brownie: wizard run-client + bug 166)

**LLEI NOVA (Agus, 2026-07-22 vespre) — L'ORDRE I LA DISTÀNCIA ENTRE TALLES ELS MANA EL SIZESYSTEM.**
El run del model és un subconjunt — potencialment NO CONTIGU (client que no fabrica la M) — que mai
redefineix ni l'ordre ni la distància. La seqüència del SizeSystem marca també l'ordre de
visualització a totes les superfícies. Corol·laris:
- Porta única d'escriptura de `Model.size_run_model`: helper `run_del_model(etiquetes, size_system)`
  (germà de `run_del_document`), que ordena SEMPRE per `SizeDefinition.ordre` i rebutja etiquetes
  fora del sistema. Cablat a views.py:590 (create-wizard + update-step2), extraction, tech_sheet,
  bulk_import, i tancant la via oberta del `ModelDetailSerializer` (PATCH acceptava qualsevol run).
- MOTOR AUTORITZAT (encàrrec explícit, zona intocable oberta amb condicions): `_apply_rule`/`steps`/
  `break_idx` passen a resoldre's en ESPAI DE SISTEMA (ordre de SizeDefinition), no per posició a la
  llista del run — un run ordenat-amb-forat (XS·S·L) ha de graduar S→L com DOS passos. Condició
  dura: QA DE PARITAT — golden S10 (105/105 model POP) i golden path 163 IDÈNTICS post-canvi; una
  cel·la canviada = stop.
- Sanejament de dades: command dry-run per defecte; el cens (scratchpad/cens_size_run.py) s'executa
  a PROD al proper deploy amb categoria nova NO_CONTIGU (informativa, no a reparar). Re-propagació
  de models afectats = decisió per model, mai automàtica (GradingVersion segellades pel mig).
- Context: diagnosi DIAGNOSI_ORDRE_RUN_MODEL_2026-07-22.md — motor amb run desordenat inverteix el
  SIGNE (XXS graduava com si fos 2 talles per SOBRE de la base); cap de les 9 vies d'escriptura
  ordenava; el fix F1.x del 174 va retirar l'única re-normalització implícita (correctament — era
  destructiva — però sense substituir-la per una porta ordenada).

**LLEI NOVA — el referent de derivació de regles és el RUN DEL DOCUMENT (Agus, Patró C 2026-07-22).**
Esmena el *referent* de la llei d'integritat del 2026-07-08 sense derogar-ne la protecció:
- Un `GradingRuleSet` nou es defineix amb: SizeSystem (ventall — informa, no obliga) + talla base
  (ETIQUETA, mai valor) + deltes/breaks del document. RES MÉS. Quines talles usa cada model es
  decideix AL MODEL; el motor propaga sobre `size_run_model`.
- El guard d'integritat valida contra el run del DOCUMENT: (a) cap forat intern dins el propi run
  del document; (b) break derivable sense ambigüitat; (c) STEP amb valor explícit per talla (la
  segona meitat — model que excedeix les talles amb valor — JA viu al motor com a cel·la absent);
  (d) NOU: etiqueta del document que el sistema no coneix = 400 real (avui s'ignora en silenci).
- Es conserva del 2026-07-08: bloqueig 400 abans d'escriure, llista de files afectades, pont únic
  `canonical_size_label`, "el size_run del prompt IA és ajuda, mai garantia".

**Wizard «Nou run de client» (SizeMapSetup/size_map_views):** la graella de talles s'ELIMINA del
camí REUTILITZAR (avui és inútil i enganyosa: `wiz.talles` no viatja mai al preview i al create
només persisteix a CLONAR/CREAR — la poda no desbloqueja res). Es CONSERVA a CREAR/CLONAR (única
font de `SizeDefinition` del sistema nou).

**Mecanisme del bug 166 IDENTIFICAT (diagnosi S24):** mateix defecte amb el signe invertit. El
wizard bloqueja perquè el referent és massa AMPLE (run del SizeSystem sencer, 8 talles vs document
de 5); l'import de fitxa fabrica regles falses perquè és massa ESTRET (`derive_rules_from_fitxa`
deriva contra `model.size_run_model`=XS·S·L mentre el document porta XXS-L → el delta de L salta la
M absent = 2d → "break=2×base a L" emergent, cap codi fa ×2). El camí d'import de fitxa NO té cap
guard d'integritat (només avisos). Fix únic: helper pur `run_del_document(values, size_system)` a
`grading_utils.py`, compartit pels 4 punts (preview fitxer/paste, create, derive_rules_from_fitxa).
7 talls dimensionats a `DIAGNOSI_REFACTOR_WIZARD_RUN_CLIENT_2026-07-22.md` (staging); mínim
Meredith = 1+2+3, tancar bug 166 = +4, graella+i18n = 5+6, traça extrapolació = 7 (pendent decisió).

**Banderes anotades (no tocades):** fallback silenciós de talla base (`size_map_views.py:801`,
candidat 400) · `_norm_label` del motor no canonicalitza XXL↔2XL (zona intocable, break perdut amb
200 OK) · extrapolació amunt sense marca (decisió Agus pendent: muda/warning/marca a cel·la).

**P1 Brownie (context PROD):** catàleg v2 (8 grups·17 types·62 items, espec HTML validada amb
Montse) s'ha de sembrar a PROD `fhort` — Fase A amb gate en curs. Font d'estructura: schema `los`
de PROD; MAI rulesets de client entre tenants.

---

## ⚡ LLEIS I DECISIONS NOVES — S22 (2026-07-21 nit, refactor grading G6)

**Origen:** símptoma viu d'Agus — canviar `GradingRuleSet` d'un model i propagar no funcionava,
en silenci (200 OK, taula plana). Patró A sobre el model TATE (163) va confirmar causa arrel:
`GradingRuleSet 108` assignat era l'únic ruleset buit del tenant (0 regles de 45); el wipe-and-
recreate de `materialize_model_grading_rules` va esborrar 25 `ModelGradingRule` residents i en va
crear 0, i el motor —davant base-sense-regla— fabricava un `FIXED` en lloc de fallar. Diagnosi
completa: `docs/diagnosis/DIAGNOSI_REFACTOR_GRADING_2026-07-21.md`.

**LLEI D2 — cel·la absent (definitiva, motor de grading):**
- Regla absent → **cel·la ABSENT** (mai `FIXED` fabricat). Si una propagació produiria 0 cel·les,
  **error clar**, mai 200 amb taula buida/plana.
- Regla `FIXED` amb increment 0 → **legítim** (0 ≠ buit: un buit no és una regla, llei LOSAN ja
  existent).
- Regla `LINEAR` amb increment 0 → **invàlida** (una LINEAR que no incrementa no és una regla: o
  és FIXED o no existeix) → bloquejada en autoria/import (D2b).
- Valor base 0 o absent → el POM no existeix per a aquest model → cap cel·la; si ve d'entrada
  d'usuari/import, error explícit (talla base a zero és físicament impossible).
- **Excepció històrica conscient:** 9 de les 34 regles del ruleset 115 (BRW·Blusa·ALPHA_EU_W,
  el contenidor validat a l'S10) són LINEAR amb delta 0 i NO s'han tocat — són dades beneïdes
  numèricament per l'S10 (105/105 exactes contra el SIZE SET real); reescriure-les per encaixar
  amb la llei nova hauria estat tocar dades bones. Si mai es re-materialitzen des de zero, la
  llei nova ja les agafaria bé.

**LLEI D1 — validacions a l'assignació de `GradingRuleSet` (wizard bloc 4, severitats):**
- Ruleset amb 0 `GradingRule` → **BLOQUEIG DUR** (mai assignable; no és una eina, és un
  contenidor buit).
- `size_system` del ruleset ≠ `size_system` del model → **BLOQUEIG DUR** (impossibilitat
  estructural: els breaks no resolen contra el run).
- `customer` del ruleset ≠ `customer` del model → **AVÍS CONSCIENT + confirmació explícita, MAI
  bloqueig** (flux de taller legítim: un Studio pot aplicar regles d'un altre client si li
  solventa el problema; les regles són eines del tècnic, no propietat del model — el model rep
  informació creuada de moltes fonts i el wizard/regles l'acoten, no la impedeixen). Patró
  d'avís: `window.confirm()` amb missatge explícit, validat en viu (model 523).

**LLEI D4 — una sola porta de propagació (auto-propagació jubilada):** `resolve_size_check` i
`close_piece_fitting` **ja no criden** `bump_grading_version_and_generate`; consoliden només
base (`BaseMeasurement` + `MeasurementChangeLog` + Welford), preservant `measurements_version++`.
Tancava una contradicció llei↔codi des del 23/06 (la llei deia "a jubilar", el sprint del 07/07
l'havia centralitzat sense jubilar-la). El helper i els guards D-1 es queden: són EL camí únic,
cridat només pel botó conscient (`generar-grading`).

**Deutes conscientment aturats (Patró C, no bloquegen res):**
- **`GradingRuleSet 108` (buit) NO esborrat:** el protegeix `SizingProfile 523`, node default
  del catàleg (Woman|Dresses|Woven). Amb D1 viu ja és inert (bloqueig dur si algú l'assigna);
  repuntar o esborrar el 523 és decisió de domini pendent, sense urgència.
- **`GradingRuleSet 98`** ("Custom Alpha EU — Women", `parent=81`, `customer=None`, 0 models)
  segueix sense classificar — reportat, no assumit.
- **4 endpoints orfes jubilats** (rutes+views: `set-size-override`, `regenerar-talles`,
  `tancar-base`, `confirmar-talla-base`); els serveis subjacents amb ús real es van conservar.
- **Provinença reparada (R8):** 3 call-sites del wizard passaven `origen` literal sense mirar
  el del ruleset font → 104 `ModelGradingRule` mentides com `CANONICAL` (models 267/268/292/293)
  reparades a `CLIENT_RUN` real.
- **Classificació `GradingRuleSet.origen` NULL:** 104→`CLIENT_RUN`, 107/110→`IMPORT` fets;
  la resta (76-93, seeds candidats a `CANONICAL`) pendent de repàs.
- **`gv30`/`gv53`** (aprovades sense signatura, `aprovada_per`/`data_aprovacio` NULL — gv53 va
  signar l'única exportació real del tenant): decisió = reassignar signatura vàlida (acte
  explícit, no desaprovar). Pendent confirmar si ja executat al sprint d'implementació.

**Golden path — model TATE (163), verd:** repunt `rs 108→115` + `size_system 67→29` FET PER UI
(wizard, no shell) → 34 MGR `CLIENT_RUN` → 96 `GradedSpec`, 0% FIXED, 51 amb increment real →
`GradingVersion` v3 (gv81) activa i **segellada**. QA d'estrès validat en viu: ruleset buit→
bloqueig, size_system creuat→bloqueig, client creuat→avís-i-confirma amb propagació real
posterior (model 523, sessió separada). **Encara pendent:** ancorar els 23 `PatternPOM` restants
del 163 (2 de 25 fets) — feina de taller, fora d'abast de codi.

**Tema aparcat amb nom — RUL com a font de graduació:** un `.rul` amb graduacions reals hauria
de ser font tan vàlida com una fitxa de client, però **no existeix cap camí de codi** que llegeixi
un RUL i creï `GradingRuleSet`/`GradingRule` — el RUL avui només s'usa com a entrada/sortida del
motor de patrons (lectura de geometria / escriptura d'exportació), mai com a font de regles.
Domini nou de veritat (a diferència del meló GTI, que és construït i no endollat). Preguntes
obertes per quan toqui (Patró A propi, sense pressa): crea ruleset nou o alimenta l'assignat?
qui mana si RUL i fitxa discrepen (un RUL és matemàticament exacte — podria merèixer MÉS
precedència)? és peça del meló GTI o independent?

---

## 🔴 DECISIÓ VIVA — MELÓ GTI-PLANTILLA (2026-07-21 nit → TANCADES 2026-07-22 matí)

**Diagnosi completa:** `docs/diagnosis/DIAGNOSI_GTI_PLANTILLA_2026-07-21.md`. Domini construït i
no endollat: `ItemBaseMeasurement` (model+API+UI d'autoria, 37 files reals) i `PatternFile`
ancorat a item (XOR a BD, auditat, testejat, 0 files reals) **ja existeixen**. `GarmentTypeItem
Asset` (disseny 29/06) **mai ha existit** — substituït per `ItemFitxer`+XOR, decisió ja segellada.

**✅ B4 TANCADA (Agus, 2026-07-22): CAP eix de client a `ItemBaseMeasurement` (Opció 1), amb
formulació pròpia que esdevé llei:** `ItemBaseMeasurement` és un actiu de plantilla més, com el
patró base o l'sketch — les mides estàndard del taller que defineixen l'item complet. TOTA la
personalització viu al model: podar POMs, rectificar mides, canviar fit, repuntar ruleset,
propagar. Cas d'ús canònic (Agus+Montse): T-shirt regular → model nou → rectificar cintura →
reconfigurar slim → ruleset slim → propagar. **"La biblioteca ven forma (i mides estàndard); el
model ven realitat."**

**✅ PRINCIPI DEL SOROLL TANCAT (Agus, 2026-07-22), generalitza la política de POMs no-mencionats:**
*el model s'alimenta de realitat — tot element sense contingut real (sembrat o importat: POMs de
plantilla no mencionats al document, files amb base i talles a zero...) és soroll i ES PROPOSA
eliminar, amb confirmació del tècnic.* Execució tècnica: `is_active=False` (soft) + rastre al
log, mai DELETE dur — la UI pot dir "eliminar", per sota es conserva auditoria.

**✅ LINEAR+0 = FIXED (Agus, 2026-07-22): display + conversió de dades.** Tota regla LINEAR amb
increment 0 i sense break es mostra com a FIXED a totes les superfícies, i les existents al
catàleg es converteixen a FIXED explícit via migració de dades EXPLÍCITA amb log (quantes i
quines) — matemàticament idèntica, zero risc de càlcul, mai silenciosa. D2b ja impedeix que en
neixin de noves.

**🆕 PAQUET NOU OBERT (Agus, 2026-07-22) — item-plantilla-completa, necessita Patró A ampliat:**
(a) **Import→item:** quan es crea un item per importació (el cas més habitual), guardar també la
talla base i les seves mides a `ItemBaseMeasurement` (avui l'import només escriu deltes/breaks al
ruleset i mides al MODEL — la graella d'item queda a guions). Matís de flux a resoldre: la
promoció model→item ha de ser **acte explícit** ("promou com a estàndard de l'item"), mai
automàtic a cada import, o l'estàndard del taller deixaria de ser-ho.
(b) **Assignacions múltiples item↔ruleset:** un item ha de poder oferir el seu ventall de
rulesets (per fit/sistema/client) i el tècnic tria al model. La multiplicitat JA existeix del
costat del ruleset (`GradingRuleSet.targets` M2M + `SizingProfile`); el que cal és CONSOLIDAR un
sol mecanisme (llei D4: mai dos sistemes pel mateix): FK singular `GarmentTypeItem.
grading_rule_set` = com a molt "suggerit per defecte"; resoldre R21 (FK legacy `target` vs M2M,
10 divergències); cap ruleset LOSAN té `garment_type_item` informat.

**QA en viu COMPLET (Agus, nit 21 + matí 22): 5/5 verds + stress extra** — inclòs canvi de
construcció plana→punt amb run completament diferent i re-propagació. El flux wizard→sembra→
grading queda VALIDAT com a peça clau de la plataforma.

**Ordre d'implementació (c0 ✅ fet a S22b):** c+b (col·lisió import↔sembra amb el principi del
soroll + superfície de poda) → paquet item-plantilla-completa DESPRÉS del seu Patró A.

**✅ TANCAT I DESPLEGAT (2026-07-22, HEAD=f22cce8, dev=origin/dev):** els 10 commits del paquet
sencer (LINEAR+0/soroll/poda + Camí A promoció + Camí B consolidació) pushats i en producció de
staging. `/api/schema/` 200.

---

## ✅ PAQUET ITEM-PLANTILLA-COMPLETA — DECISIONS TANCADES (Agus, 2026-07-22)

**✅ TANCAT I DESPLEGAT (2026-07-22):** els cinc peces del paquet complet — 10 commits totals,
HEAD=f22cce8=origin/dev, servei reiniciat, /api/schema/ 200:
- LINEAR+0=FIXED (display+dades, 127 regles) · principi del soroll a l'import · superfície de poda
- Camí A: guard de talla · esquema ItemBaseMeasurement (origen/timestamps) · acte de promoció
  model→item (dry-run+confirm+talla base) · tests (35→56)
- Camí B: FK legacy target jubilat (M2M única font) · V1 suggerit per defecte · eina de propostes
  d'àmbit per a Montse (dry-run: 19 contenidors, 45 nodes ITEM, 20 sense evidència — material a punt)
- Incident de sessió superat: dues sessions penjades (test 44min + hook de sistema) resoltes amb
  Ctrl+Q + reconnexió, zero pèrdua de feina (tot ja commitat abans del penjament)
reordenen el mapa: cap camí automàtic escriu mai `ItemBaseMeasurement` (per disseny, no accident);
els vincles item↔ruleset són CINC (V1..V5), cap picker llegeix V1 ni V2 (el ventall el generen
V3+V4 amb comodí d'eix NULL); `derive_grading_rule_set` és codi mort (R21 reclassificat a baix);
el backfill LOSAN literal és IMPOSSIBLE (13/20 rulesets serveixen un CONJUNT d'items).

**✅ LLEI NOVA (aprova la contradicció amb la norma inamovible 1):** *"La sobirania del model és
sobre els SEUS valors. L'estàndard del taller és un acte separat, explícit i CONFIGURE — mai un
efecte secundari d'un import."*

**✅ P1 — guard de talla (FER JA, independent de tot):** la sembra item→model i la promoció han de
comparar `GarmentTypeItem.base_size_definition` ↔ `Model.base_size_label` — tanca la fuga viva de
valors ITEM_STANDARD aterrant en talla equivocada en silenci.

**✅ D-PROM — política de promoció model→item: SOBREESCRIURE AMB CONFIRMACIÓ** (dry-run diff: què
canvia/s'afegeix/sobraria + confirm explícit — mateix patró que D1 client-creuat i el principi del
soroll). Condicions dures: **P9 abans** (camp `origen` + timestamps + autoria a
`ItemBaseMeasurement` — sense això una promoció és irrecuperable i anònima) · **gate CONFIGURE
propi** (mai heretar IsAuthenticated de l'amfitrió) · **P3 dins el mateix acte** (la promoció
escriu també `base_size_definition` — l'únic moment on el sistema SAP la talla).

**✅ D-CONS — consolidació del ventall item↔ruleset ("un rol, un vincle"):**
- **V4 `RuleSetScopeNode` = FONT ÚNICA DEL VENTALL** (l'únic N↔N, ja cablat als dos pickers)
- **V1 `GarmentTypeItem.grading_rule_set` = suggerit per defecte** (es queda, primer lector real:
  preselecció al picker del wizard de model)
- **V2 `GradingRuleSet.garment_type_item` = IDENTITAT del contenidor** (no es jubila, surt del
  ventall — sosté `uniq_client_container_identity` i el NIVELL 1 del matcher)
- **FK legacy `target` = JUBILAR** (codi mort que encara rep escriptures a 4 punts; 5 passos
  documentats a la diagnosi §B2.6)
- **V5 `SizingProfile` = fora del ventall** (preset de biblioteca)
- **ORDRE INAMOVIBLE: P4 (poblar scope-nodes) ABANS de P5 (endurir el comodí)** — al revés els
  pickers queden buits (6/45 rulesets tenen nodes). P4 és criteri de domini: eina + sessió de
  treball amb Montse (seed assistit des dels models reals de cada ruleset, taula §B2.7).
- **Backfill LOSAN de V2: DESCARTAT en forma literal** (per la dada) — la higiene LOSAN va via V4.

**Nota de circuit (incident 2026-07-22):** la diagnosi no va trobar el §MELÓ perquè el DECISIONS.md
del SERVIDOR estava al 16/07 — el vault era la font bona. Recordatori: sincronitzar vault→servidor
en tancar sessió, i les diagnosis llegeixen la còpia del servidor.

---

## 🔴 BUG WIZARD MODEL 174 (2026-07-21 nit — diagnosi ESCRITA i verificada)

**Deliverable escrit:** `docs/diagnosis/DIAGNOSI_MODEL_174_2026-07-21.md` (confirmat, el primer
intent va fallar per timeout d'un hook del sistema, recuperat sense escapar-se per `bash` sense
avisar). Veredicte complet, verificat en detall contra el codi real:

**Veredicte:** model 174 SA, zero dades a reparar. Bug d'UI reproduïble en qualsevol model en
mode EDICIÓ — calent per a models futurs. Causa arrel: `ModelWizard.jsx` no rehidrata els tres
estats del pas 3 (`selSystem`/`selectedSizes`/`baseSize`, `:180,191-195`) en mode edició; latent
des de sempre, disparat pel commit `6f4107f` (17/07) que va afegir el pas 4 "Graduació" també en
edició, depenent 100% d'un `useMemo` (`sizingResult`, `:86-92`) que exigeix els tres alhora.
"Sistema de talles: —" = `sizingResult?.size_system_nom || '—'` (`:549`). El "botó que no
respon" no existeix: amb `sizingResult` null, `RuleSetPicker` ni es renderitza (`:562,582`); el
que està deshabilitat és Guardar (`baseSizeInvalid`, `:615`).

**Parany identificat:** el run del model coincideix caràcter a caràcter amb un sistema de client
(`WOMAN_BRW_01`, id 53) mostrat amb distintiu "Run de client: BRW" al pas 3 — triar-lo (opció
visualment correcta per a un model BRW) fa `53≠29` → `baseSize=null` → pas 4 cec. Per a models
LOS no existeix aquest parany (no hi ha sistema client amb aquell run). **Radi confirmat: 174,
268, 269** (mateixa forma exacta). D1 i el backend són innocents — el bloqueig passa abans de
cap petició HTTP.

**🔴 Bonus greu fora d'abast, anotat:** triar un sistema al pas 3 en edició SUBSTITUEIX tot el
run del model i mou la base al mig (`:192-195`), sense avisar — avui només ho atura per accident
el mateix guard buggat. Si es repara el bug principal sense tractar això, deixa de petar en fals
i comença a canviar runs de veritat en silenci. **Necessita guard conscient propi abans o alhora
del fix principal.**

**Radi confirmat per dades reals (no només inferència):** 174, 268, 269 — mateixa combinació
exacta `size_system=29` + run `XXS·XS·S·M·L`. **Camins addicionals que disparen el mateix bug**
(trobats a la diagnosi escrita, no citats abans): saltar pel stepper directament al pas 4, o
entrar per «Canviar graduació» (`?block=4`) — en aquest segon camí **els sistemes de talles ni
tan sols es carreguen**.

**Pendent:** (1) verificar 268/269 abans de tocar res; (2) brief d'implementació — 5 propostes ja
dimensionades a la diagnosi (rehidratar pas 3 en edició · pas 4 amb fallback al sistema del model
· no tocar el run si ja és vàlid dins el sistema triat · marcar/filtrar per client al pas 3 · el
picker ha de dir per què no es mostra) — sessió pròpia, domini UI/wizard, diferent del motor de
grading.

---

## ⚡ LLEIS NOVES — S21 (2026-07-21, editor de fitxa)

**Llei d'arquitectura de l'editor (definitiva):** ESQUERRA = biblioteca d'inserció
(tot el que ve del model: POMs/Sketches/Taules/Arxius/Peces de patró — persianes amb
llistes directes, MAI popups) · DALT = totes les eines per tabs, mai desbordament ·
DRETA = tot el que és de l'element seleccionat, en persianes homogènies (Capes NO és
tab) · MIG = pàgina. Qualsevol superfície nova de l'editor segueix aquest patró.

**Llei — DESAGRUPAR és el gest universal:** un sol botó, motor segons context — objecte
compost→group Konva de sempre; path compound (SVG/peça importada)→N objectes path
independents (subpaths); bloc atòmic (capçalera)→materialització en objectes reals amb
type:'field' per als valors amb clau. Sentit únic. Qualsevol bloc atòmic futur (mai
taules, decisió explícita) segueix aquest mateix patró en lloc d'un "explode" a mida.

**Llei — geometria SEMPRE (bake):** escalar/rotar una forma o path SEMPRE reescriu la
geometria real (via paperOps); mai es desa com a scaleX/rotation decoratiu sobre un
objecte que després cal desfer. Aplica també al Transformer d'objectes.

**Llei — edició CONTÍNUA, no transacció:** l'edició de nodes/formes escriu directament
al document i entra a l'historial general (⌘Z normal); no hi ha Fet/Cancel·lar.
Decidida VEIENT dues maquetes reals (HTML), no per ASCII ni descripció — coherent amb
la llei S19 de validació visual per a decisions de flux.

**Llei — un sol contracte de pintura (paint.js):** subpath mana sobre l'objecte;
absent hereta; 'transparent' és decisió explícita de l'usuari i NO hereta; sense color
no hi ha traç; mai un color inventat com a fallback. Viu i PDF el llegeixen d'aquí.

**Llei — peces de patró són vector, no imatge:** el DXF ja arriba aplanat a punts pel
parser (M…L…Z), així que importar-les com a `type:'path'` és cost baix i dona tot el
comportament d'objecte vectorial (desagrupar/nodes/bake/pintura per capa DXF).

---

## ⚡ LLEIS I DECISIONS NOVES — S20 (2026-07-21, editor de fitxa)

**Llei de domini/arquitectura — cap bloc atòmic:** tot bloc compost del document (capçalera,
taula de mesures, qualsevol `data_block` futur) ha de ser DESAGRUPABLE en objectes reals de
primer nivell: `rect`/`line`/`text` per a decoració, **`type:'field'` amb `field_key` per a
valors del model** (el binding ja existeix), `group` embolcallant, `ungroupObject` existent fa
la resta. Desagrupar és de sentit únic (tornar = re-inserir de plantilla).

**Llei de l'editor — geometria sempre:** mirall/rotar/escalar sobre formes REESCRIUEN segments
(mai `scaleX` negatiu com a hack). UN sol motor d'organització per a objectes i formes (destí:
Camí 2, Konva pur amb Paper com a calculadora). Els forats (subpaths 1..n) entren a l'abast.

**Llei de l'editor — jerarquia Illustrator:** dos cursors (fletxa negra=FORMA per defecte,
fletxa blanca=nodes), doble-clic entra; tota acció accessible des de la barra superior en el
mode que toca; cap acció d'abast objecte a un clic en mode nodes (gate del panell = B3,
pendent, cost S, prioritari).

**Llei de la cota POM:** la cota neix del contenidor POMs amb text RESOLT (còpia estàtica de
la nomenclatura, fletxa vermella saturada + text blanc bold fons vermell) — MAI vincle viu a
la mesura (frontera G1 intacta). Editable i eliminable després; el text s'amaga durant
l'edició de corba; text separable i rotable.

**Llei del mode plantilla:** construir plantilla és un ESTAT EXPLÍCIT (botó + etiqueta a la
barra) amb guardat propi que desactiva l'autoguardat del model. La pestanya Camps només
existeix en aquest mode.

**Decisions visuals pendents (es decideixen VEIENT maquetes, llei S19):** Q1 transacció
Fet/Cancel·lar vs edició contínua amb undo de document · Q3 "Editar" com a tab de ribbon vs
barra contextual.

---

## 🔴 DECISIÓ VIVA — LOGIN AMB DISCOVERY INTEGRAT (Agus, 2026-07-20 nit) · REDISSENY

**El disseny anterior (pantalla prèvia d'email → correu amb link) està MORT** — desplegat a
PROD i revertit el mateix dia per ordre d'Agus en veure'l en viu. Decisió definitiva, sense
ambigüitat: **CAP pantalla prèvia, CAP fricció d'entrada.** El discovery viu DINS la pantalla
de login existent (fhorttextile.tech/login): email+password com sempre → el sistema descobreix
el tenant per sota → l'usuari arriba al seu espai AUTENTICAT. Zero passos nous.

**Es reutilitza:** discovery_service (lookup cross-schema), throttle, tests (backend a dev/main).
**Mor:** Entrar.jsx + ruta /entrar + subdomini login. (revertit a PROD; retirar el codi en
sprint de neteja).

**Abans de reimplementar:** Patró A propi (autenticar cross-schema vs descobrir+reautenticar;
JWT emès per quin schema; seguretat del flux) + **VALIDACIÓ VISUAL a staging abans de cap
runbook** (llei nova de sota).

**Llei de mètode nova (cicatriu d'avui):** tota decisió que afecti el FLUX D'ENTRADA o creï
una PANTALLA sencera nova es valida VISUALMENT a staging abans de qualsevol pas a PROD. El vet
sobre un informe escrit NO és vet sobre el producte — una UX no es pot vetar llegint.

---

## ⚡ LLEIS I DECISIONS NOVES — S18 (2026-07-20 vespre)

**Llei de domini — pendent d'OFERTA vs pendent de COMANDA:** una línia de pressupost és
"pendent" quan `count(model_intents) == 0` — amb ≥1 intent ja està "pensada"; la `quantity`
de l'oferta és xifra comercial, MAI sostre d'intents (la intenció no és cartera). Una línia
de comanda és "pendent" quan `qty_allocated < quantity`. Els dos càlculs de "següent línia
pendent" viuen a l'ORIGEN (OrderDetail/QuoteDetail), no al servidor.

**Llei de domini — assignació en lot = TOT-O-RES:** `assign-models` (batch) valida capacitat
conjunta abans de tocar res, `select_for_update` sobre la línia, i si UN model del lot topa
amb el guard de dualitat, CAP s'assigna (error identificant el conflictiu). L'assignació
parcial és el defecte que el batch existeix per eliminar. El single `assign-model` es
conserva (compatibilitat), però tot camí nou de N models usa el batch.

**Llei d'arquitectura — propòsit i retorn per QUERY PARAM, mai per historial:** el mode
"selecció amb intenció" (`?select_for=<tipus>:<id>&select_max=&return=`) segueix la doctrina
que el propi codebase ja predicava (FittingDetail.jsx:530-538): el propòsit viatja per URL,
el destí es reconstrueix de dades — MAI `location.state` ni `navigate(-1)` per a context.
Els params de propòsit s'exclouen de FILTER_KEYS (no viatgen al backend de list) i es
consumeixen amb `setSearchParams(replace)`.

**Llei de presentació — mode intenció a la llista de Models:** quan `select_for` és actiu:
selecció capada a N amb comptador x/N · mode Gmail i ActionsMenu OCULTS (oposats de
"limitat a N") · prefiltre `customer` BLOQUEJAT (chip amb candau, el guard backend
l'exigeix igualment) · barra de confirmació fixa. La llista de Models és LA superfície
universal de selecció: qualsevol origen nou que necessiti triar models hi navega amb
propòsit — MAI un picker/modal inline nou.

---

## ⚡ LLEIS I DECISIONS NOVES — S17 (2026-07-20 tarda-2)

**Llei de domini — el vincle model↔oferta és INTENCIÓ, mai contracte:** `QuoteLineModelIntent`
(through: quote_line + model + qty + position) és purament informatiu — cap WorkOrder, cap
`qty_allocated`, cap snapshot. La vinculació contractual neix NOMÉS amb la comanda (a la
conversió). Editable en DRAFT i SENT; segellat en ACCEPTED.

**Llei de domini — conversió oferta→comanda amb regla de dualitat:** per cada intent, en ordre:
model LLIURE → assignació normal (WO ORDER nou) · model amb WO ORDER OPEN d'una ALTRA comanda →
NO viatja + avís al comercial (`intent_conflicts` al meta; la conversió MAI es bloqueja) ·
model amb WO ORFE → re-adopció (reattach) sobre la línia clonada.

**Llei de domini — reattach (re-adopció d'orfe):** simètric estricte d'unassign (7 guards
espill: ORDER · OPEN · orfe · order destí OPEN · customer coherent · qty disponible · no
albaranat). RE-CONGELA `price_snapshot`/`recipe_snapshot` contra el product de la línia NOVA
(preu, IVA, recepta alineats amb qui factura). Els `WorkOrderAdjustment` històrics es RESPECTEN
tal qual (valorats al seu moment). `orphaned_from_line` es NETEJA (l'orfandat és transitòria,
no història).

**Llei de presentació/arquitectura — UN sol selector de cascade per a tot el sistema:**
`CascadeSelector` (frontend/src/components/CascadeSelector/) amb dos modes — `single` (valor
pla de 6 camps, camí únic amb neteja de nivells inferiors) i `multi` (array de nodes
GROUP/TYPE/ITEM acumulatiu, navegar⊥marcar). Props: mode · value|nodes · onChange · target? ·
ruleSets? · minLevel/maxLevel · stopPolicy ('free'|'require-item') · onConfirm? · showCounts?.
Els comptadors per node són OPT-IN i els injecta el consumidor (el component mai fa fetch) —
només les superfícies de filtre els paguen. JUBILATS: AxesSelector, ScopeSelector,
GarmentTypeSelector, GarmentPOMMapEditor. Qualsevol superfície nova que necessiti triar
peça USA CascadeSelector — mai un selector nou.

**Deute observat (no tocar sense dades):** `useGarmentCatalog` sense cache compartida — cada
selector muntat refetcha. Tolerable avui; revisitar amb react-query/provider NOMÉS si els
comptadors ho fan car a la pràctica.

---

## ⚡ LLEIS I DECISIONS NOVES — S16 (2026-07-20, dev, 16 commits, cap push a main encara)

**Context:** tres sprints Patró B corrent en sessions concurrents sobre `dev` (dominis disjunts:
planning/models/fitting · commerce · tenants/auth), cap col·lisió — `git add -p` selectiu dins
fitxers compartits (i18n) va bastar. Push fet (`760ffdf..af37b20`). Deploy a PROD: NO fet, pendent
de decisió d'Agus (pot ser un merge combinat dels 3 o per separat).

**Llei — contracte de conjunt per a accions bulk (#4/#9):** les accions massives sobre Models
accepten `{filters, exclude_ids}` A MÉS d'`ids` explícits (XOR, mai els dos). El backend re-avalua
el queryset amb el FilterSet canònic al moment d'executar, itera per LOTS, i fa recompute UN SOL
COP per tècnic afectat al final — mai per element. `assign-batch` (`planning/views.py:599`) és el
primer consumidor. Límit dur a `ids` explícits (500); `filters` no en necessita.

**Llei — FilterSet canònic únic:** `ModelFilter` (`models_app/views.py`) és ara l'ÚNICA font de
filtres, consumida per Model list + `by_model` + `fase-counts` — es van eliminar els dos
entrypoints mirall. `responsable` = SEMPRE director del model; `assignee` (param nou) = tècnic amb
tasca assignada (abans confós sota `responsable` a `by_model`/`fase-counts`).

**Llei — esborrat de ModelTask restringit a Pending:** `destroy()` propi a `ModelTaskViewSet` només
permet `status='Pending'` (altres → 409). Si la Pending estava planificada/assignada, replica la
cascada d'`unassign` (`recompute_for_technicians` + `cleanup_queue_order` + neteja `predicted_*`).
Gate `DEFINE_TASKS` (ja existia, no es toca).

**Llei — fitting "aquí i ara" substitueix l'alta lliure:** `create_session`/`FittingSessionNew.jsx`
JUBILATS (POST `/fitting-sessions/` retorna 405). Únic camí = `schedule_session` via l'acció
`schedule-now`: un clic sobre un model, data/hora=ara, attendee=actor de la request, sense obrir
cap formulari — tot el camí normal (guard solapament, recompute, calendari) s'executa ocult.
Coherent amb la llei "el camí lliure captura qui el fa" (S15).

**Llei — desassignar un WorkOrder d'una comanda deixa TRAÇA, no esborra:** nou camp
`WorkOrder.orphaned_from_line` (FK SalesOrderLine, SET_NULL, migració `commerce.0020`). En
desassignar: `order_line=None` (allibera `qty_allocated`, surt de `line.work_orders`) +
`orphaned_from_line=<línia original>` (traça per a l'informe d'orfes, mateix acte). Restringit a
WO `kind=ORDER, status=OPEN` SENSE `DeliveryNoteLine` (ja albaranat = no reversible per API).
Les `ModelTask` migrades es queden intactes al WO orfe (decisió conscient: és feina realitzada,
no es reverteix). `price_snapshot` ara congela també `tax_rate` — un WO orfe (`product=None`)
albara amb l'IVA correcte, no 0%. Informe de "pendents de reassignar" a `/comercial/orfes`.

**Decisió d'abast — el modal d'assignació de comanda NO s'ha unificat encara** amb la futura
superfície universal de selecció de Models (mode "selecció amb intenció" + multi-select + round-trip
línia-a-línia). El prerequisit (`unassign`) ja existeix; la unificació pròpiament dita és sprint futur.
La línia de comanda NO té garment_type (és comercial pura, `SalesOrderLine`) — cap prefiltre de
garment és possible sense derivar-lo del `Product`; pendent de decidir si val la pena.

**Decisió d'abast — pont temps→preu (TIME_BASED) NO tocat:** `Product.price_mode=TIME_BASED` +
`sale_rate`/`markup_pct` són esquelet documentat als docstrings, ZERO cablejat (cap consumidor a
`commerce/` de `lookup_estimated_minutes`/Welford). Multiplicador de preu per garment/temps NO
EXISTEIX (`ProductPriceGTI` és preu ABSOLUT d'excepció, no factor). Mereix disseny propi, sprint futur.

**Deute NOU (infra, no d'aquest sprint):** `TenantTestCase` no neteja rows entre mètodes de test →
col·lisió `SizeFitting(model_id=1, numero=1)` quan classes germanes de test comparteixen schema de
tenant al mateix procés. 78/528 tests amb la mateixa firma en 5 fitxers (`pom.test_g6_segell`,
`fitting.test_g6_estalitud`, `patterns.tests` 25/336, `fitting.tests`, `pom.test_g6_grading_gates`).
Confirmat NO-regressió (cap dels 16 commits toca aquests fitxers ni `fitting/models.py`); mateixa
firma reproduïda en aïllament. Fix propi: fixtures úniques o `TenantTransactionTestCase`.

## ✅ RESOLTA — LOGIN CENTRAL AMB TENANT-DISCOVERY (S16, 2026-07-20)

**Decisió presa (opció B, marcada a la diagnosi, sense vet d'Agus en contra):** porta neutra NOVA
`login.fhorttextile.tech` → PUBLIC, NO reassignar `app.`/`staging.` (és l'entrada viva del tenant
fhort; migrar-la trencaria bookmarks). DNS ja creat per Agus (A → 178.105.217.125, la IP de PROD —
el discovery és feature de producte real, no d'infra de test; no calen DNS a staging, només
`curl -H Host` per verificar-hi el codi).

**Implementat (dev, 3 commits, verd):** `POST /api/discovery/` (public schema, `AllowAny`,
`DiscoveryRateThrottle` propi 10/h): email → resposta SEMPRE uniforme (0/1/>1 tenants
indistingibles) + correu best-effort amb link o selector. Pantalla `/entrar` (frontend). 9 tests
verds (servei 1/0/>1, iexact, resposta indistingible, throttle 429).

**PENDENT (manual, a PROD, quan Agus ho decideixi — runbook al doc de diagnosi):**
1. Fila `Domain.objects.get_or_create(domain='login.fhorttextile.tech', tenant=public)` — sense
   ella, 404 malgrat el DNS.
2. vhost nginx PROD (esborrany al doc).
3. Certbot.
4. **SMTP real — sense ell el correu és fum** (resposta uniforme funciona, però ningú rep res).
5. Verificar `/api/schema/` 200 contra el domini nou.

---

## 🔴 DECISIÓ VIVA — LOGIN CENTRAL AMB TENANT-DISCOVERY (Agus, 2026-07-19) · URGENT

⚠️ **SUPERADA per la resolució S16 de dalt** — es manté aquest bloc només com a registre de
l'enunciat original; la decisió d'arquitectura ja està presa i implementada a `dev`.

**Necessitat (Patró C, prioritat alta):** un usuari ha de poder entrar per una porta ÚNICA
(`app.fhorttextile.tech` o una pantalla neutra d'accés) i el sistema l'ha de DESVIAR al seu
tenant (subdomini) — sense haver de saber ni teclejar la URL del seu workspace.

**Estat actual (context tècnic):** django-tenants resol l'schema pel HOST abans del login →
`app.` és la porta del tenant fhort, `losan.` la del tenant los. Un usuari de LOSAN NO existeix
a `app.` (viu dins l'schema `los`). No hi ha cap descobriment de tenant.

**Peça a dissenyar (sessió pròpia, Patró A primer):**
- Pantalla/endpoint NEUTRE de descobriment: email → a quin(s) tenant(s) existeix → redirecció
  al subdomini corresponent (o selector si multi-tenant).
- El lookup travessa schemas → la peça viu probablement a PUBLIC (patró backoffice), amb molta
  cura de privadesa (no revelar existència d'emails: resposta uniforme + email de link, o
  redirecció només post-verificació).
- Encaix natural: lliga amb backoffice/onboarding (registre central de tenants) i amb el futur
  self-service. Considerar si `app.` passa a ser la porta neutra i fhort rep subdomini propi,
  o si es crea `login.`/landing — DECISIÓ D'ARQUITECTURA OBERTA.
- Precedent del dia: Agus esperava entrar a LOSAN via `app.` — la fricció és real d'usuari.

**No implementar sense diagnosi:** toca middleware de tenants, auth i DNS/nginx — visió
transversal obligatòria.

---

## ⚡ DEUTES S14 — GO-LIVE TENANT LOS A PROD (2026-07-19, vespre)
**[ACTUALITZACIÓ S15 20/07]** El forat B2 (signal SizeFitting) està RESOLT i desplegat.
Lleis noves del PLA ÚNIC + implementació C1-C4: veure ESTAT_PROJECTE S15. Deutes S14 restants
segueixen vius (loader, s9, admin temporal, tasques 961). Deute NOU: formulari "Nou fitting"
crea sessions sense attendees ni planificació — alinear amb el camí del planificador.

**Fixos de CODI pendents a staging (destapats pel go-live directe a PROD):**
1. **Paquet LOSAN sense vocabularis-fulla** (Target/ConstructionType/FitType): afegir
   `00_vocabularies.json` a export/loader; el loader ha de FALLAR amb error clar (no warning)
   si una FK de ruleset/profile no resol — mai crear coix. (A PROD es va resoldre amb còpia de
   dades fhort→los.)
2. **Bug lookup de POMMaster al loader:** amb `codi_client` duplicat (S, J1 — parells
   multi-àlies), `_resolve_pom(key)` col·lapsa les dues files sobre el mateix master →
   2 masters perduts + refs desviades + convergència impossible (updated≠0 crònic). Fix: lookup
   pel parell `(pom_global, codi_client)` ABANS de la llei de resolució. (A PROD: reparació
   manual, masters #734/#733 + 5 repunts, verificada.)
3. **`s9_views.py:37`** — check d'onboarding amb criteri obsolet (`is_system_default>=1`);
   corregir a "rulesets amb regles >= 1". **Pedaç viu a PROD a retirar:** ruleset 37 LOS Baby
   Knit — Tops marcat `is_system_default=True` només per satisfer el check.
4. **RUNBOOK_DEPLOY_PROD:** afegir bloc SPA backoffice (rebuild `frontend-backoffice` +
   verificar root del vhost) — el 19/07 PROD servia el dist del 7-juny.

**Decisions/estats:** Plans PROD = Free (seed) + Brand id=3 (quotes provisionals; "Team"
d'staging és fila fora de choices, no replicar) · tasques dels 961 = CAP fins a ordre d'Agus ·
admin1@losantest.com temporal · build tenant-genèric `frontend/dist-tenants` (VITE_API_URL="")
= el dist únic per a tots els tenants.


---

## ⚡ LLEIS I DECISIONS NOVES — S12 TEMPLATE FTT (2026-07-19)

**Llei de presentació — Template FTT (plantilla mestra de capçalera de fitxa tècnica):**
- **Etiquetes del PDF SEMPRE en anglès, fixes** (DATE·PAGE·TECHNICIAN / INTERNAL REFERENCE·
  CLIENT REFERENCE·SEASON·STYLE NAME·COLLECTION / GARMENT TYPE | ITEM·TARGET | FIT TYPE |
  CONSTRUCTION·SIZE SYSTEM·SIZE RUN). És com treballa el sector. **Excepció i18n conscient**
  (tanca la "decisió B" pendent del juny per a la capçalera). Els camps de document (data,
  pàgina) també en format anglès/neutre; els valors escrits pel client, en el seu idioma tal
  com els va escriure. Valors de catàleg (TARGET/FIT/CONSTRUCTION) → `nom_en`.
- **Etiquetes a 6px = excepció conscient al sòl de 8pt** (són acompanyament de valors 9px que
  ja es llegeixen bé; el sòl de 8pt segueix vigent per al COS de la fitxa).
- Geometria canònica: banda x=28.6 y=39 w=784.7 h=90.2 · marc únic + divisòries 170.3/491.8 ·
  padding 6pt homogeni · graella etiqueta y=47.5+i·22.5, valor +10 · subcolumna x+w/2+6 ·
  base del run en bold+underline (3 segments, charW=fontSize·0.6).
- Abast: NOMÉS capçalera, instanciada com a **bloc ancorat a cada pàgina nova**. L'usuari pot
  "Delete on this page" (per instància) o "Detach & edit" (perd sincronia amb la mestra —
  conseqüència assumida). Coherent amb la llei "document plàstic, dada immutable".
- Logo = `customer.logo` resolt al render, MAI cuit dins el template.

**Decisions d'arquitectura S12:**
- La mestra es defineix PER CODI (`build_master_header_document()`) i la sembra pack-eja el
  `.fttpt` a la media de cada tenant (pas especial de `bootstrap_tenant`, NO tuple de `_spec()`
  — un template file-backed no es pot copiar com a fila). Idempotent.
- **"Template FTT" substitueix DocumentTemplate id=2 "Capçalera LOSAN"; id=2 NO viatja a PROD.**
  Template FTT = plantilla base de sembra de qualsevol tenant nou.
- TARGET/FIT/CONSTRUCTION s'exposen al ModelDetailSerializer resolts des de
  `model.grading_rule_set` (5-capes), mai dels CharField legacy del Model.

## 1. Lleis de mètode (no negociable)

- A Claude xat es DISSENYA i es fa ARQUITECTURA; un cop decidit, es generen instruccions per a
  Claude Code (blocs copiables) que l'Agus passa i executa. Primer investigar, després construir.
- **Patró A** (diagnosi read-only) → **Patró B** (implementació amb equip) → **Patró C** (decisió de
  disseny = Agus; Claude decideix detall tècnic només quan es delega explícitament).
- **Diagnosi abans de dimensionar — en ESPAI i en TEMPS.** Espai: llegir el codi real abans d'estimar.
  Temps: comprovar al registre + converses passades si la decisió JA existeix abans de re-obrir-la.
- **Llegir el projecte SENCER, no l'illa.** Comprovar què ja s'ha CONSTRUÏT abans de dir "no existeix"
  o "és estructural". (Lliçó 2026-06-23: el read-only del check va ignorar el fitting editor ja fet.)
- **No més pedaços: unificar el ja construït.** Si dues superfícies viuen del mateix UI/dades, no es
  peguen per separat — es convergeixen. Pegar dues vegades garanteix reprocés. (Llei transversal a tot
  el refactor, no només a G1.)
- Codi mínim · un focus per commit · `git add` explícit (mai `-A`) · regla del verd abans de cada
  commit (`manage.py check` + `npm run build` + verificador/guardians/revisor) · MAI push d'agents
  (l'Agus puja des de SSH) · i18n-gate ca/en/es a tota UI nova.
- Els agents corren amples i autònoms; **verd = continuen**. Només s'aturen per blocador dur,
  contradicció de paradigma, o verd trencat.
- **Mètode com a skills al repo (2026-07-07).** La litúrgia viu versionada: `CLAUDE.md` (lleis
  sempre-actives) + `.claude/skills/patro-a` (diagnosi) i `patro-b` (implementació) + 8 agents a
  `.claude/agents/`. Els prompts passen a ser briefs curts que invoquen les skills. **Diagnosis
  commitades:** l'arrel de `docs/diagnosis/` = vigents (font de veritat); `docs/diagnosis/arxiu/` =
  històric segellat (capçalera `⚠️ SUPERADA`), MAI font per a decisions. `ESTAT_*`/`DECISIONS.md`
  segueixen SENSE commitar.
- **El remot SEMPRE descriu producció (2026-07-12).** Tot deploy a PROD s'anota a
  `ESTAT_PROJECTE.md` amb **data + commit de merge + migracions aplicades**, i `origin/main` es
  **pusha immediatament després del merge**. (Lliçó 2026-07-12: la foto mental de PROD anava un
  desplegament endarrerida — es creia que corria el `main` del 27/06 quan de fet corria un merge
  local del 09/07 mai pushat. El pre-deploy va haver de **llegir el dump diari** per saber què
  corria de veritat, perquè cap ref de git ho descrivia: `origin/main` parat des del 07/07 i el
  `main` local 467 commits endarrerit. Un merge que no es pusha no existeix per a ningú més.)

## 2. Lleis de domini

- **LLEI D'ARQUITECTURA DE DADES — les 5 capes que conflueixen al Model (2026-07-16; les lleis
  particulars de grading/sembra en són corol·laris):**
  1. **GarmentType/GarmentTypeItem — el QUÈ:** defineix la peça i, transversalment, QUINS POMs li
     pertoquen (domini de mesura; una faldilla no té llarg de màniga — el POM no existeix per a ella).
  2. **Sistema de POMs — el COM:** catàleg canònic de punts de mesura (definició, mètode, toleràncies,
     nomenclatura). Independent de peça i client; el diccionari de client n'és la traducció.
  3. **Llibreria de talles (SizeSystem) — l'ESCALA:** runs POCS i PURS (alpha/numèric/edats). **Un run
     NO té fit**: XXS-3XL és el mateix run per a regular que per a slim. Mínims runs possibles.
  4. **Regles de graduació (GradingRuleSet) — el VINCLE en forma de REGLA, mai de model:** vincula
     peça+POM+escala+fit+client com a fórmula d'expansió abstracta (cap valor absolut, cap model).
     **El fit viu AQUÍ**, no al run. És on es fa la selecció rica (cascada target→constr+fit→grup).
  5. **Model — la INSTÀNCIA on tot es SEMBRA selectivament:** agafa NOMÉS allò que li convé (subconjunt
     de POMs de la fitxa, regles d'aquells POMs) i hi afegeix l'únic que cap capa té: valors mesurats.
  **Capes 1-4 = DEFINICIONS** (catàleg, reutilitzables, cap centímetre mesurat). **Model = INSTÀNCIA**
  (sobirà, valors reals, història). La sembra és la frontera: **unidireccional i selectiva** — el
  catàleg proposa, el model disposa. Cap instància escriu a la definició sense acte explícit.
  **Seqüència de decisió del model:** primer run+base (capa 3, pura), DESPRÉS graduació (capa 4, on el
  fit discrimina). `SizingProfile` = preset de biblioteca, MAI la unitat de selecció del model.
  *Patologies del 2026-07-16 com a casos d'escola (totes violacions d'aquest mapa): 115 orfe (vincle
  sense identitat), 116 (instància creant definició), fit colat al pas de Talles del wizard (escala
  contaminada), ruleset "EU Woven Woman Numeric" penjant d'un run alfa (vincle a escala equivocada).*

- **L'última presa de mesura escrita és la veritat vigent** (precedència temporal, no d'origen).
- **Mesura manual i automàtica són el mateix procés d'entrada;** cada presa = una columna nova.
- **Fitting i size check són EL MATEIX ACTE** (mesurar → resoldre en columna nova) → mateixa
  superfície tècnica (Mesures), no dues pantalles. El **fitting com a PANTALLA convocada amb totes
  les talles propagades QUEDA JUBILAT**: es dissol en (1) presa de mesura dins Mesures (talla base,
  origen FITTED) i (2) tot el treball sobre totes les talles → funcionalitat de **Grading/Escalat**.
- **`size_check` és LA tasca de presa de mesures (2026-07-12).** El `TaskType` `code='size_check'`
  (name "Mesurar prenda", eina `mesures`, mode `presa`; **pk=20 a `fhort`**) ≡ l'acte de mesurar
  sobre peça física. **Serveix fitting I check sobre maniquí**: mateix acte, mateixa eina, mateix
  rellotge. El que canvia és **el camí d'entrada** i **l'origen al log**: `FITTED` si hi ha sessió
  de fitting, `CHECKED` si no. **MAI es crea un `TaskType` de fitting separat** — un type nou
  obligaria a migrar dades reals (`ModelTask`, `TaskTransition`, 5 literals
  `task_type__code='size_check'` hardcoded) sense guanyar res.
- **La sessió/convocatòria de fitting és un CONTENIDOR, no el treball (2026-07-12).** Agenda i
  llança la tasca; **el treball —estat, temps, qui— sempre passa per `ModelTask`**. La sessió no
  és una unitat d'execució: és una franja d'agenda amb una acta.
- **Mort del fitting → migració a Grading (CONDICIÓ BLOQUEJANT):** tota la maquinària que avui penja
  del fitting (càlcul, propagació, règim LINEAR/STEP, breaks, generate_graded_specs, GradingVersion,
  ModelGradingOverride, _apply_rule/derive_break_fields) ha d'existir i estar VERIFICADA viva i
  accessible a Grading ABANS de jubilar cap pantalla/funció de fitting. No es jubila res del fitting
  fins que el seu equivalent és viu a Grading — altrament es perd l'esforç de construcció.
- **Check = decisió de qualitat per línia** (accept dins tolerància / descarta discrepància), no una
  segona mesura. El veredicte de model (Acceptat/Rebutjat/Descartat) el deriva el motor.
- **Fitting amb model = més maduració** que el check a taller → els estadis es mostren DIFERENCIATS a
  la taula (`checked` vs `fitting`); el backend ja els distingeix (origen CHECKED vs FITTED).
- **Sobirania de dades:** la plantilla (`GarmentTypeItem`) sembra; el model POSSEEIX. L'autoria
  (valors, nomenclatura) viu a nivell de model.
- **Propagar grading sobre la realitat mesurada vàlida crea una columna nova.**
- **Propagar = ACTE CONSCIENT.** Propagar és aplicar deltes+breaks sobre les talles per omplir la
  taula de grading, i és SEMPRE decisió conscient de la tècnica. MAI automàtic: ni acceptar un size
  check ni "tancar un fitting" propaga. Flux: s'obre Mesures (mai fitting), es treballa la talla base
  tantes vegades com calgui; quan està bé es propaga; en propagar s'entra a Grading (totes les talles,
  règim, breaks, ajustos puntuals per talla sobre prendes reals). L'auto-propagació viva avui
  (resolve_size_check:230, close_piece_fitting:469) és codi a JUBILAR/RECONSTRUIR dins el zoom-out,
  NO a retocar ara (trencar-ho abans de tenir Grading-com-a-tasca estrandaria l'usuari).
- **On viu el Propagar conscient:** com a TASCA de Grading al Pla de treball intern del ModelSheet
  (zoom-in), reconstruïda durant el zoom-out. Mai acoblat al Kanban de menú (que es jubila).
- Els estadis de la taula base són un **llibre major** (lectura derivada de `MeasurementChangeLog`);
  l'escriptura de base la fan els motors (mesura/check/fitting), no la vista.
- **Semàntica del break a l'extrem petit del run (validada S10, 2026-07-16).** Per expressar "el pas
  de l'extrem petit del run (p.ex. XXS↔XS) és diferent de la resta": `talla_break_label` = la talla ON
  COMENÇA el tram COMÚ (p.ex. `'XS'`, NO `'XXS'`); `increment_base` = el valor del pas ESPECIAL (l'extrem
  petit); `increment_break` = el valor COMÚ (la resta del run). Noms de camp contraintuïtius per a aquest
  cas (semànticament invertits respecte a l'ús habitual "base=normal, break=excepció des d'amunt"). El
  motor (`_apply_rule`, `pom/services.py:719-765`) llegeix `talla_break_label` contra `size_run_model`
  (mai `talla_break_pos`, que és cache/auditoria). Validat numèricament 105/105 cel·les exactes sobre un
  model real (Brownie POP, run XXS-XS-S-M-L, base S).
- **Regla sense base = cel·la ABSENT, no cel·la a zero.** Si un `GradingRule`/`ModelGradingRule` no té
  `BaseMeasurement` amb valor per aquell POM, `generate_graded_specs` simplement no emet `GradedSpec` per
  aquell POM (ni FIXED). És patrimoni de catàleg sense mesura, no un buit a omplir amb zero. Validat S10.
- **LLEI — GradingRuleSet de client = CONTENIDOR ACUMULATIU per (customer + size_system +
  garment_type_item + fit) (2026-07-16, esmena la decisió del 2026-06-08).** MAI es crea un ruleset nou
  per model: cada brusa nova amb un POM nou NO genera contenidor — l'enriqueix. L'import de fitxa:
  (a) **SEMBRA** el model amb les regles del contenidor per als POMs de la fitxa — la sembra ESCULL i
  descarta els POMs no usats; el catàleg pot ser més ampli que qualsevol model (per això ampliar-lo no
  contamina res); (b) les regles de la fitxa per a POMs que el contenidor NO té s'hi **AFEGEIXEN
  automàticament** (ampliar no destrueix); (c) si la fitxa **CONTRADIU** una regla existent → conflicte
  conscient (mantenir catàleg / actualitzar catàleg / resident només al model). Un contenidor nou només
  neix quan el client estrena la combinació — i com a acte explícit de l'usuari, mai silenciós.
  **Cas canònic (Regular→Slim):** canviar la graduació d'un model = canviar de contenidor germà
  (update-step2 re-sembra les residents amb les regles del nou; la talla base NO es toca; en propagar
  conscientment, la mateixa base es projecta amb les regles noves). Granularitat futura family-level
  (`garment_type` amb catàlegs POM més amplis): anotada, NO decidida.
  *(Revoca: "el ruleset derivat de fitxa es desa com a catàleg reutilitzable [creant-ne un per import]",
  2026-06-08 → la intenció era acumular SOBRE la base existent, no crear-ne de nous. 1B/1D van
  implementar la lectura equivocada; el cas 115/116 la va destapar.)*
- **Welford pur, llindar 5 (2026-07-07).** `WELFORD_MIN_SAMPLES=5`. L'empíric (`TaskTimeEstimate`:
  n/mean/m2) només conté **mostres reals**; el seed teòric viu a `TimeSeed` com a **llavor de tenant**,
  MAI a `TaskTimeEstimate`. (Migració: les 442 cel·les teòriques n=0 destil·lades a llavors per-task.)
- **Cascada de resolució de temps (2026-07-07).** Ordre: empíric(item,task) si n≥5 → empíric global del
  tenant per task (mitjana de cel·les madures) → llavor `TimeSeed` (scope task, sinó fase) → **captura
  conscient del PM**. **Mai None en planificar, mai valor inventat.** El PM captura via `needs_estimate`
  (llavor origen=CAPTURA) i desbloqueja al moment. El snapshot (`ModelTask.estimated_minutes`) es
  **re-resol NOMÉS per a tasques Pending** als punts de recompute (convergència única
  `recompute_for_technicians`); InProgress/Paused/Done conserven el snapshot. Cap canvi d'estimació
  espontani fora de recompute; mai es clobbera un valor amb None.

## 3. Lleis de presentació (UI)

- **Nomenclatura POM a 2 línies:** nom EN canònic a dalt + nom en idioma usuari a sota (més petit,
  cursiva gris). Lligat a la dada `nom_client = nom_en`. Implementació de referència: POMBrowser
  (verificar el landing exacte abans de reusar).
- **Nomenclatura sempre editable a nivell model** (el tècnic la renomena al fer patrons/fitxa);
  la canònica només sembra. *(Implementació pendent — vegeu §5.)*
- **Amplada de columnes real** (no estirar a l'amplada de finestra); les columnes s'afegeixen cap a la
  dreta, amb scroll horitzontal en sobreeixir (i vertical per molts POMs).
- **Icones només outline** (mai `-filled`; webfont Tabler). **Colors via tokens CSS, mai hex**
  (excepció: `KONVA_COL` literal per a canvas, que no resol `var()`).
- **Fitxa tècnica:** cos de text mínim 8pt, ideal 9-10pt; mai per sota de 8pt.
- **Display de TaskType per code via i18n (2026-07-07).** El nom visible d'un tipus de tasca es resol
  pel namespace `tasktype.<code>` (ca/en/es); `TaskType.name` (BD) = **fallback** (base EN canònic),
  mai es persisteix ni es pinta en cru. Tot render-site passa pel helper `taskTypeLabel(t, code, name)`.

---

## 4. Decisions d'abast vives (s'actualitzen sprint a sprint)

### DUES FACTURACIONS SEPARADES (2026-07-07)
**backoffice→tenant** (ús de la plataforma; domini public existent; APARCAT) **≠ studio→tercers**
(mòdul comercial tenant-side). **No comparteixen entitats.** Cap barreja de models entre les dues.

### Model comercial Studio (2026-07-07, per implementar — T3)
- Entitats: **Comanda → LiniaComanda** (servei × `garment_type_item` × preu × qty) **→ Encàrrec**
  (model, línia) **→ `ModelTask.encarrec`** (FK nullable).
- **Tasca fora de recepta = extra facturable detectat.**
- **Preu = decisió comercial;** el sistema INFORMA el cost estàndard (Welford) i el marge, no el fixa.
- **Gate per tier:** Brand no veu el mòdul.
- Decisions OBERTES abans del brief T3: (a) cost intern pla vs per-perfil; (b) fitting per sessió vs
  per fase; (c) recepta oberta-amb-marca vs tancada. + `garment_type_item` obligatori al wizard.

### Mòdul Comercial Studio — disseny fundacional (2026-07-08)
Disseny complet a `DISSENY_MODUL_COMERCIAL.md`. Substitueix les 3 decisions obertes de l'entrada
T3 anterior. **Lleis del mòdul:**
- **Mestre Product amb 4 natures:** INTERNAL_SERVICE / EXTERNAL_SERVICE / GOODS / PACK.
- **Servei extern NO és tasca:** crea `Expense` + event de calendari (no entra al motor de tasques/Welford).
- **Preu = el sistema PROPOSA, l'humà FIXA.**
- **Snapshot de preu i recepta als documents** (congelat al moment d'emissió).
- **Delta bidireccional a l'entrega:** extres + regularització negativa (cas Brownie).
- **Factura legal FORA de l'abast:** el mòdul arriba fins a albarà + liquidació + marca `invoiced`.
- **Naming BD/codi en ANGLÈS.**
- **Multi-proveïdor amb preus per article.**
- **Cost intern v1 = tarifa plana** (`TenantConfig.hourly_rate`).
- **Fitting per sessió.**
- **Recepta oberta amb marca `off_recipe`.**
Inventari: 13 taules · 7 pàgines · 7 modals · 4 PDFs · 7 informes. Blocs B0–B5, ~8-10 sessions.
Oferta confirmada a v1 (dolor Brownie). Es desenvolupa en XAT PROPI amb el document com a substrat.
El document JA és al servidor (324 línies) amb l'Annex A = brief B0 llest per llançar.

### 2026-07-08 — Decisions §9 Comercial Studio (deferides / tancades post-B0)

- **#1 (estructura línies Quote/Order), #2 (numeració documents), #5 (estats WorkOrder)**:
  deferides conscientment a investigació pròpia de B2/B3. No bloquegen B1 (cap toca
  Product/Unit/satèl·lits).
- **#3 (tarifa de venda TIME_BASED)**: TANCADA — camp `sale_rate` a `Product`. El preu és
  Welford(task_code, GTI) × multiplicador, bifurcat en dos: `hourly_rate` (TenantConfig,
  cost) i `sale_rate` (Product, venda). El GTI és pes de complexitat dins la cascada, no un
  preu en si.
- **#4 (UX matriu preu×GTI)**: TANCADA — `ProductPriceGTI` reescopit com a taula
  d'EXCEPCIONS (no graella densa; no hi ha "57 items" com a mida fixa, cada tenant crea els
  GTI que vulgui). Rellevant només per: serveis `FIXED` (sense cascada) i correccions manuals
  puntuals sobre `TIME_BASED`. UX: llista filtrable + "afegir excepció" des de la fitxa del
  Product.
- **Naming `Product` ↔ `Production`**: no és col·lisió (B0 confirmat), és proximitat visual.
  Convenció: imports amb prefix de context explícit (`from commerce.models import Product`)
  + docstring a `Product` que remet a no confondre amb `tasks.Production`.
- **Dependència B5**: `feature_flags` no s'exposa a `/me` (`accounts/serializers.py:16-33`).
  Bloquejant per al gate de tier; primer pas del brief de B5.

### Federació Brand↔Studio (2026-07-07, disseny; pendent d'implementar rere prerequisits)
- El model té **UNA casa (Brand)**; l'**execució** (tasques, timers, Welford) viu a **QUI EXECUTA
  (Studio)**. Lliurables = **un binari, dues referències** (`DeliverableRegistry` a public, futur).
- Vincle **`TenantLink` a public** via clau (ancoratges reservats: `Customer.codi_global` al tenant /
  `Client.codi_tenant` a public). Al Studio, el model assignat s'instancia com a **Model local
  origen=EXTERN (opció B2)**.
- **Brand veu** planificació/maduresa/entrega/incidències; **MAI temps ni tècnics.**
- **Benchmark cross-tenant:** minuts, k≥5 tenants, **mai entra a la cascada** de planificació.
- **Prerequisits:** R5 (seed onboarding genèric), R9 (media per schema), R10 (primitiva cross-tenant).

### Refactor d'eines — pla de grups (post-aparcament de facturació)
- **APARCAT:** motor de facturació/backoffice + meritació → sprint futur, tier `estudi`. No es toca res.
- Premissa: el deploy sobreescriu PROD (versió antiga, sense clients reals) → els antics "riscos de
  dades a PROD" passen a ser, com a molt, correcció de lògica.
- Grups: **G1** (unificat, vegeu sota) · **G2** estat del model · **G3** import vell · **G4** POM-editor
  vell + òrfenes · **G5** codi mort transversal · **G6** grading (l'últim dels grossos) · **G7** bug
  calendari · **G8** higiene frontend. **G9** = lent transversal (TaskType governance), no grup en seqüència.

### G1 — redefinit a SUPERFÍCIE UNIFICADA de mesura resolta (2026-06-23)
- **Ja NO és "re-allotjar el size check"** sinó la superfície única on conviuen **check + fitting**
  (mateix editor, layout i contracte de dades). Decisió Agus: no més pedaços.
- L'**editor de fitting** (`/fittings/<id>`) ja fa història read-only + columna editable a UNA graella,
  oberta des de la tasca, expandint-se per columnes. **És la referència; no es reinventa.**
- El motor `resolve_size_check` queda INTACTE i passa a ser un cas d'ús d'aquesta superfície.
- Properes correccions de G1 que entren a la convergència (de la validació en viu 2026-06-23):
  - una sola superfície editable (no dues graelles separades);
  - consulta des de model · edició via tasca (avui `/mesures` SEMPRE edita — cal cablejar el gating);
  - botó "des de model" ha d'OBRIR/reclamar la tasca, no navegar sec;
  - purgar vocabulari mort "tasca de POM" (4 claus `model_sheet.*`); "POM" com a capçal de columna és
    legítim i es manté.

### Frontera G1-unificat ↔ G6 (grading)
- La unificació toca el que escriu grading propagat (`GradedSpec`/`GradingVersion`). La **diagnosi de
  convergència mesures+fitting ha de MARCAR la frontera amb G6**, no colar-s'hi. Guard de segellat
  `GradingVersion` i col·lisions de grading segueixen sent G6.

### Sprint S10 — primera GradingRuleSet real de client (Brownie), validada de punta a punta (2026-07-16)
**ZERO CODI.** Sprint de validació pura amb dades reals (shell ORM + endpoints reals), no implementació.
5 QA GATES (1·2·4·5 passats; 3 tancat per equivalència amb el 5 — decisió Agus). Cap push, cap migració,
cap commit de codi. Backup PRE-S10 verificat abans de la primera escriptura.
- **GradingRuleSet 115** `BRW · Blusa · ALPHA_EU_W` (ss=29 ALPHA_EU_W, `origen=CLIENT_RUN`, customer 7
  BRW) amb 34/34 `GradingRule` exactes (14 amb break a l'extrem petit, 20 planes).
- **Model 268 `Blusa POP`** (BRW-FW27-0001): 21 bases reals MANUAL, run XXS-XS-S-M-L, base S. Assignat
  el ruleset 115 → 34 residents → **105/105 `GradedSpec` exactes (±0.01)** contra el SIZE SET real del
  document font. **Primera prova numèrica del motor de grau amb dades reals de client de punta a punta.**
- **Tres destinacions confirmades vives des de dades de client:** Escalat (`taula-mesures`) i TechSheet
  (`graded-table`) — totes dues PASS amb valors exactes. **Motor de Patrons: NO EXERCITABLE** aquest
  sprint (el model usat no porta DXF/RUL) — candidat de sessió pròpia amb un model amb patró real.
- **`clone_model_for_qa` no reutilitzable per a BRW:** guarda idempotent PER-CUSTOMER col·lisiona amb el
  `[QA-SC]` 182 (golden de Size Check, ja existent per BRW). Es va usar un clon ORM fidel (`[QA-S10]`,
  model 267) per no tocar cap original (162/163/182 intactes).
- **Troballa:** els candidats "obvis" de clonatge (models 164-167/175, "37 mesures") tenien les 37 files
  `BaseMeasurement` sense valor (`base_value_cm` NULL) i el run sense `XXS` → la QA estructural sobre ells
  no era exercitable; delegada íntegrament al model POP (gate per equivalència, decisió Agus).
- Veure LLEIS DE DOMINI (§2) per la semàntica del break i "regla sense base = cel·la absent".
- Veure DEUTES (§5) per la provinença `CANONICAL` no propagada i `origen` no exposat per l'API.
- Resultat complet: `docs/diagnosis/RESULTAT_S10_GRADING_BROWNIE.md` (no commitat, còpia servidor).

### Nota de disseny futura (G6) — break doble lògic (petit + gran)
Arran de S10: avui la forma canònica només suporta UN break. El cas real Losan (run nen→adult fins 6XL)
necessitaria dos breaks lògics simètrics — un cap a talles petites, un cap a talles grans, amb un tram
central comú — avui només representable com STEP (valors explícits, es perd la compacitat de regla).
**Decisió pendent, NO urgent:** ampliar la forma canònica a `increment_central` +
`(talla_break_baixa, increment_baixa)` + `(talla_break_alta, increment_alta)` NOMÉS si un run real ho
exigeix i STEP resulta impracticable a l'autoria. Elimina de soca-rel la inversió semàntica del break
actual (perquè "central" deixa de ser ambigu). No tocar sense un cas real damunt la taula.

### Deutes anotats de l'S10 (no arreglats, no urgents)
- **Provinença `CANONICAL` no propagada:** `materialize_model_grading_rules` (via `update-step2`) sempre
  escriu `origen='CANONICAL'` a les residents, encara que el `GradingRuleSet` font sigui `CLIENT_RUN`.
  Confirmat en viu (models 267 i 268). Cap impacte al motor (llegeix per FK), sí a traçabilitat.
- **`GradingRuleSetSerializer` no exposa `origen`:** l'API retorna `null` pel ruleset 115 tot i que la BD
  té `CLIENT_RUN` correcte. Classificació bona a BD, invisible a UI/API.
- **14 `GradingRuleSet.origen` encara NULL** (dels 25 originals, 11 ja classificats a CANONICAL a l'S10):
  104/111 (customer LOS), 110 (import BRW), 107 (import FTT), 108 (Mango) són candidats sensibles a
  `CLIENT_RUN`/`IMPORT` — classificar abans del proper `bootstrap_tenant` per no filtrar dades de client
  a un tenant nou.

### TROBALLA (2026-07-16) — la peça anti-proliferació JA EXISTEIX (1D), forat = sense `customer`
Arran del cas real 115/116 (dos rulesets BRW gairebé simultanis per al mateix garment, no fusionats
sols): **1D** ("Reutilitzar GradingRuleSet equivalent a l'import", commit `bdaa19f`, tancat 2026-06-16)
ja fa exactament aquesta feina — automàtica, dins el W5 de l'`ImportWizard`, sense UI nova. Abans de
crear, busca un ruleset `is_system_default=False` amb la mateixa combinació
`size_system+garment_group+target+construction+fit_type`; si troba un amb **igualtat estricta de
graduació** (mateix conjunt exacte de `pom_id` + mateixa lògica/increment/valors_step per POM comú +
mateixa talla_base), **reutilitza** (re-apunta el model); si no, crea nou.
- **Per què no ha fusionat 115/116:** el filtre de candidats de 1D **NO inclou `customer_id`** — mateix
  forat axis-exacte-sense-client ja identificat al brief CRUD-eixos. A més, en aquest cas concret la
  igualtat estricta tampoc hauria casat (115=34 regles de test S10, 116=25 regles d'import real; 1D ha
  actuat CORRECTAMENT amb la informació que tenia).
- **Decisió Agus (2026-07-16):** la peça de reutilització client-aware passa DAVANT de F-1..F-5 del brief
  CRUD-eixos (és la causa arrel; els eixos NULL n'eren un símptoma). **NO tocar dades dels 115/116/268/269
  avui** (deute anotat, <90% solapament, no són bessons reals). **Intensitat del fix:** avisar-i-confirmar
  (patró 409/`grading_choice` ja existent al sistema, NO automàtic silenciós) — evolució de com actua 1D
  avui (automàtic amb avís de text) cap a una confirmació explícita del tècnic, en comptes de
  "reutilitzar automàtic dur" (massa risc de casar dades de clients diferents).
- **Peça a fer (abast confirmat, pendent de Fase A ampliada + gate):** afegir `customer_id` al filtre de
  candidats de 1D + convertir la resolució en avís-i-confirma (409) en lloc de silenciosa.

### ✅ TANCAT (2026-07-16) — Peça R + F-1..F-3/F-5 implementades, 7 commits verds a dev (SENSE push)
Diagnosi ampliada (`DIAGNOSI_DUPLICACIO_GRADINGRULESET_CLIENT.md`) va confirmar: 1D existeix i és
axis-first+estricta; el 115 li és invisible per eixos NULL (no per manca de `customer` únicament). 115
vs 116: **Jaccard 55%, NO bessons** (21 pom comuns · 13 sol-115 · 4 sol-116; 15/21 increments idèntics).
Duplicació **aïllada avui** (únic parell customer+size_system repetit: `(7, 29)`), però **risc latent
sistèmic** perquè qualsevol ruleset de client amb eixos NULL serà sempre invisible a 1D.
**GATE Agus:** reutilització client-aware PRIMER (causa arrel, davant de F-1..F-5) · dades 115/116/268/269
= deute anotat, NO fusionar · intensitat = avís-i-confirma TOU (mai automàtic dur) · trigger = mateix
`customer`+`size_system` (no exigir target/group — el 115 en té NULL) · superfície = NOMÉS import-fitxa
ara (size-map hereta consistència via F-1 més tard, no duplicar cerca als dos camins).
**7 commits a `dev`** (`b39dc81..27971ad`, tots amb check+build verds i QA propi):
1. `b39dc81` — backend: `cerca_client_equivalent` + 409 `{reuse_candidates}` a import-fitxa (peça R).
2. `514d5f3` — frontend: prompt a l'`ImportWizard` (reutilitzar/crear nou) + i18n.
3. `59d5b02` — F-1: size-map cabla `construction`/`fit_type` al `GradingRuleSet.create()` (consistència
   amb import-fitxa, que ja ho feia).
4. `116edf4` — F-2a: `id` a `FitTypeSerializer` (gap que bloquejava F-2).
5. `89eb9a0` — F-2: modal CRUD editable per a rulesets `not is_system_default` (lookups S2 + codi→id).
6. `e9820e5` — F-3: `origen` read-only al serializer (l'API ja no retorna `null` pel 115/116).
7. `27971ad` — F-5: guard `validate()` al serializer — bloqueja canvi d'eixos si `is_system_default=True`
   (protecció explícita dels 11 seeds; abans només el frontend `disabled` protegia, ara també el backend).
**Ajornat deliberadament:** F-4 (garment_group al picker/cascada — eix vestigial, NULL a 24/27 inclosos
els 11 seeds, no val la pena tocar la cascada per ell) · fork `gradingAxes.js` vs còpia inline de
`GradingRuleSets.jsx` (deute assenyalat, no arreglat).
**Dades:** 27 rulesets intactes, 115/116/268/269 sense alterar. Pendent: (1) Agus revisa `git show` de la
cadena, prioritzant R (`b39dc81`/`514d5f3`, causa arrel) i el guard (`27971ad`, seguretat dels seeds);
(2) prova real: importar una tercera fitxa BRW i confirmar que apareix el prompt de reutilització abans
del push; (3) push des de SSH quan validat.

### Checklist Montse — reconciliació diccionari Brownie (pendent, decisió humana de domini)
- **Codi `U` → TAPETA ANCHO perdut** sota CRUCE DELANTE (col·lisió last-wins al loader del diccionari).
  Cal segon codi per a TAPETA ANCHO?
- **`B4`/`B6`** (zones ARRIBA/ABAJO): 0 files, mai van entrar. El diccionari original els contenia?
- **`F1`→POM 437** i **codi `0`→POM 461**: mapatges possiblement lossy (dues descripcions diferents
  resolent al mateix POM). Exclosos del ruleset 115.
- **7 forats sense POM canònic** (`D1, M1, M2, I4, J4, I1, L1`): exclosos del ruleset 115, específics de
  model — candidats a `nom_fitxa`/regla resident quan calgui.
- **Convenció ½ amplades vs canònic (CH/273):** cal decidir si els POMs d'amplada són ½-contorn o sencer
  abans de fixar bases de producció. Els valors del ruleset 115 es van entrar tal com dona el document
  font (verificat, quadra amb el SIZE SET real); la convenció general resta oberta.

### Sprint TANCAMENT MESURES + FITTING — estat (2026-06-23)
**Mesures + Fitting tancats com a UNA superfície de treball sobre l'editor únic `MeasureGrid`**, en
ritme barat. Cadena de commits locals VERDS sobre B-bis (`9a370c1..b12b36b`, dev, SENSE push).
- **P0 — botó de tornar transversal:** `BackButton` reusable + slot `onBack` a `EditorHeader`; fix del
  back hardcoded (sense i18n) a `GarmentPOMMapEditor`. *(troballa: Mesures/Fitting/Escalat ja tenien
  back propi; el que faltava era el patró únic + el cas no-i18n).*
- **P5 (a-d) — CONVERGÈNCIA DEL FITTING a `MeasureGrid`:** `FittingDetail` ja no usa `MeasureTable`;
  paritat plena amb el check (nomenclatura 2 línies, color només-activa, règim editable al leadCol,
  propagació de germanes via `onSave`→`propagar`/`update`, capçalera `EditorHeader` amb franja
  contextual de sessió). Motor `close_piece_fitting` INTACTE (resolució a ReviewScreen). **`MeasureTable.jsx`
  NO jubilat:** `PropagatedEditor` (Escalat, mode-model `persistCell`) encara en depèn → la jubilació real
  és una peça pròpia **Escalat→MeasureGrid** (no en aquest sprint). [VALIDACIÓ EN VIU pendent: propagació
  runtime + capçalera.]
- **P6 — unitats a presentació:** `fmtMeasure`+`useUnit` (helper únic); 1 decimal cm / 2 inch a les
  cel·les de valor en lectura; l'input editable es desa canònic (cap round-trip drift).
- **P7 — nomenclatura editable a nivell model: 🛑 BLOQUEJAT.** L'endpoint `poms/<id>/nomenclatura/`
  edita `POMMaster.nom_client` (tenant-POM COMPARTIT) → violaria la sobirania (§2) i "la canònica només
  sembra" (§3), i ni es reflectiria a la cel·la (mostra `name_en`/`name_cat`). L'autoria de model viu a
  `BaseMeasurement.nom_fitxa`, que exigeix emetre `bm_id` als serializers + precedència de visualització +
  decisió de domini → peça pròpia. Diagnosi: `/root/fhort-sessions/DIAGNOSI_P7_NOMENCLATURA.md`.
- **P8 — arbre de dependència + ruleset (lectura a Mesures):** `DependencyPanel` (llinatge garment_type→
  item→model + `grading_rule_set` vigent); backend emet `grading_rule_set_nom` (read-only). SEAM visible,
  autoria a edició-de-model (no aquí).
- **P9 — presa tipada per origen:** `stageAccent` tipa CADA origen amb punt de color (fitting=verd,
  taller/proto=daurat, derivada/importada=gris) a la columna/historial del check.
- **Fronteres pendents (no tocades):** PROPAGAR-conscient (D-10), Watchpoints (D-12), Enviar a producció
  (handoff), Calendari/dates (es refà), G6 (rename/segellat grading), jubilació Kanban, Escalat→MeasureGrid.

### Sprint TANCAMENT (2a tanda) — Escalat + cicle de tasca + 2 bugs (2026-06-23)
Cadena VERDA sobre l'anterior (`90ed4fa..f3300f1`, dev, SENSE push). **L'editor únic `MeasureGrid` ara
serveix les TRES superfícies: check + fitting + escalat.**
- **P1 [VIU] — Escalat → MeasureGrid:** `PropagatedEditor` deixa `MeasureTable` i usa `MeasureGrid` en
  mode model (Base vigent read + Fit actual = override; talla base read-only via nou `active.readonly`),
  capçalera `EditorHeader` ("Escalat", no "grading propagat"). Motor INTACTE: segueix cridant
  `models.setSizeOverride` (mateix QUI/QUAN); l'interior (`generate_graded_specs`) no es toca; germanes
  es refresquen rellegint `taula-mesures`. **JUBILATS `MeasureTable.jsx` + `MeasurementTable.jsx`** (−806
  línies netes). Adapter `buildEscalatGroups/Rows` a `fittingGridAdapter`.
- **P2 [VIU] — sortir → Pausada:** `ModelMeasurements` pausa la tasca en desmuntar si s'hi va entrar per
  tasca (patró d'`EscalatTask`). Desbloqueja el Play-per-reobrir (InProgress no té Play). `transition_task`
  i l'exclusió un-InProgress NO tocats.
- **P3 — coma decimal:** input `type=text inputMode=decimal` + `toNum` (`,`→`.`) a MeasureGrid → 60,5 == 60.5
  (check/fitting/escalat). (La hipòtesi inicial "és P6" era falsa: `fmtMeasure` és display-only.)
- **P4 — botó "Editar" a Resum:** mogut de `ModelSheetHeader` a la pestanya Resum (edita el model, no la
  pantalla visible).
- **Editors a HEAD:** MeasureGrid (check · fitting · escalat) · EditableTable (entrada/estructura POM,
  superfície a part) · MeasurementBaseGrid (catàleg d'ítems). Els 2 grids legacy, jubilats.
- **Fronteres respectades:** generar/propagar grading conscient (D-10/G6), anti-fragmentació plena de
  ModelMeasurements, watchpoints/handoff/calendari, cicle de tasca complet (auto-tancar/sort+open).

### Sprint CADENA DE TREBALL — el tècnic fa tot el camí des del menú (2026-06-23)
Cadena VERDA (`ba14b7e..8048e77`, dev, SENSE push). **La cadena del tècnic és construïble end-to-end**;
única frontera pendent = propagar-conscient (D-10, supervisada). Cens base: DIAGNOSI_CADENA_TREBALL.md.
- **P1 [VIU] — porta-menú:** `open_model_task_view` (POST `models/<id>/open-task/ {code}`) CREA la
  ModelTask si falta + la posa En curs reusant `transition_task` (auto-assign+timer). ModelSheet treu
  el gate `hasPomTask`; "Editar mides"/"Editar escalat" obren la tasca encara que no existeixi.
- **P2 — convocar fitting des del menú:** `ActionsMenu` → `FittingSessionNew?model=` (prefill); el
  fitting es convoca des del llenç (abans standalone).
- **P3 — ruleset CANVIABLE al model:** `RuleSetCard` a Resum (reusa AxesSelector+RuleSetPicker) →
  PATCH `update-step2 {grading_rule_set_id}` (re-materialitza config; NO toca el motor de propagació).
  Tanca SPEC §1.6 (visible+canviable).
- **P4 [VIU] — nomenclatura per-model (desbloqueja P7):** autoria del nom al MODEL (`BaseMeasurement.
  nom_fitxa`, precedència sobre la canònica), NO al POM tenant. Serializers emeten `bm_id`+`nom_fitxa`;
  NomCell de MeasureGrid editable a check+fitting. *(Integració al wizard d'import = follow-up.)*
- **P5 [VIU] — Watchpoints (D-12):** entitat nova + migració `0042_watchpoint` (generada, NO aplicada)
  + endpoints (resolve/reopen) + `WatchpointsPanel` a l'editor de mesures. Text lliure ancorat al model
  + tasca d'origen, open→resolved, travessa gates, no a la fitxa. *(Timeline = follow-up.)*
- **P6 — jubilació import vell:** retirats els 2 endpoints d'onboarding morts (0 consumidors). El servei
  `extraction_service`/`EXTRACTION_PROMPT` es MANTÉ (viu: wizard nou + size-map) — frontera respectada.
- **Frontera pendent (supervisada, NO autònoma):** propagar-conscient D-10 (gate abans dels 3
  `generate_graded_specs`) + segellat D-1 → es fa amb l'Agus al davant.

### Sprint SOBIRANIA DE LA REGLA — import reté regla, no propagat; regla viva i editable (2026-06-23)
Cadena VERDA (`5ded3d4..ad10e4a`, dev, SENSE push). **Llei (Agus):** tot sembra el model però tot viu i
és modificable AL MODEL, inclosa la REGLA (deltes+breaks). L'import CALCULA tot però RETÉ només base +
deltes + breaks; NO reté el grading PROPAGAT (col·lisiona amb el sembrat del motor). base s'autora ·
deltes+breaks s'autoren · grading PROJECTA (conscient, D-10).
- **P1 [VIU] — import reté base+deltes+breaks, no el propagat:** `import_session_confirmar_view` deixa de
  persistir `GradingVersion`/`GradedSpec`; manté extracció + `detect_grading` (breaks) + `ModelGradingRule`
  (deltes+breaks). SF = contenidor; `generate_grading_view` projecta després (D-10).
- **P2 [VIU] — conflicte conscient importat vs retingut:** snapshot abans del wipe + `grading_rules_match`
  (per forma; motor intacte) → 409 + rollback (patró Size Library) → tècnic tria (`grading_choice`
  importats/heretats); la triada esdevé la regla del model. Cap overwrite silenciós.
- **P3 [VIU] — delta+break editables a la talla base (Mesures):** `set_pom_regim_view` estès per desar
  `increment_base/increment_break/talla_break_label` a `ModelGradingRule` (origen MANUAL). Motor de càlcul
  (`_apply_rule`/`generate_graded_specs`) INTACTE: només canvia QUINA regla llegeix (la viva) i COM s'edita.
- **P5 [VIU] — poda del propagat a la superfície d'estructura** (Generar grading/Veure escalat) + "Tornar al model".
- **P6 [VIU] — "Fer comentari" (Watchpoint) al menú del model**, ancorat a la tasca en curs o al model.
- **P4 DIFERIT:** jubilar pantalles 4/5 fusionant l'editor d'estructura dins CheckMeasureEditor = disseny +
  funció gran (validació en viu) → amb l'Agus. P5 ja ha tret la col·lisió de propagat d'aquelles pantalles.
- **Fronteres SUPERVISADES (NO tocades):** estat/segellat del SizeFitting + GradingVersion a l'import (D-1/D-10);
  propagar-conscient (D-10). El motor de patrons no s'ha tocat ("motor bé, tocar poc").

### G9 — TaskType governance (lent transversal, activa des d'ara)
- **Congelació viva:** cap escriptor/editabilitat nou de `TaskType` al tenant; referències noves
  sempre per `code`, mai per PK (el sistema ja s'hi ancora).
- **Tall futur:** definició de TaskType → sistema/public (patró POMGlobal); `TaskTimeEstimate` (Welford)
  queda al tenant com a FK cross-schema. Repensar `on_delete` (CASCADE/PROTECT no valen cross-schema).
- **Moviment físic = sprint futur bloquejat per** crear `stagingbackoffice.fhorttextile.tech`.

### Frontera del motor → REASSIGNADA al zoom-out (2026-06-24)
- La diagnosi docs/diagnosis/DIAGNOSI_MOTOR_FRONTERES.md va revelar que: (A) el guard de segellat JA
  existeix complet als dos camins (close_piece_fitting + resolve_size_check mirror) amb allow_reopen_sealed
  → és AUDIT, no forat (només cal netejar docstring stale a advance_phase:714-715). (B) el desacoblament
  de la propagació NO és "treure una línia": és la punta de la migració fitting→Grading, que pertany al zoom-out.
- DECISIÓ: el motor NO es toca en sessió pròpia abans del zoom-out. Es tanca DINS del zoom-out, perquè
  el destí (Grading-com-a-tasca) és part d'aquell. El següent gran salt és UN de sol: zoom-out + tasques
  + reconstrucció de Grading com a successor del fitting.
- PRIMERA TASCA del zoom-out = DIAGNOSI DE PARITAT fitting→Grading (inventari): per cada funció del motor
  que el fitting consumeix, on és, si Grading ja la crida, i què falta. BLOQUEJANT abans de jubilar res.

---

### RUN-CLIENT — La regla com a actiu core i secret industrial (2026-07-08)
> Diagnosi: `docs/diagnosis/DIAGNOSI_RUN_CLIENT_VINCULACIO_2026-07-08.md` · cadena Patró B `d324b22..8731d8d`.

- **[LLEI DE DOMINI] `GradingRuleSet` = ACTIU CORE i SECRET INDUSTRIAL del tenant** — la forma de
  fit per GTI × marca; el fit de cada marca és identitat de producte. Corol·laris:
  - (a) tota captura/import de regles exigeix una superfície de **PARITAT verificable** contra el
    document ABANS de persistir;
  - (b) a federació, les grading rules tenen **permís propi al vincle** (mai al paquet genèric) i el
    Studio les aplica **sense còpia de la forma**;
  - (c) el **benchmark cross-tenant EXCLOU per llei** tota forma de graduació;
  - (d) canvis al motor (G6) sempre amb **diagnosi de paritat**.
- **Valor base NO viu al run:** el run és actiu de **REGLES** (portable a un altre model); el valor
  base és dada de **MODEL** (`BaseMeasurement`/`ItemBaseMeasurement`). Confirmat: `GradingRule.valor_base`
  eliminat; `increment_base` sí poblat.
- **Import de regles (decisions vives):**
  - no-resolts = **cua persistent** (`pendents_vincular`), no creació de POM des del wizard;
  - **col·lisió de mapping = bloqueig 400** amb llista (mai `update_or_create` silenciós);
  - **toleràncies = mostrar**, persistència **diferida** al sprint POM-review amb col·lapse 2→1 ± (deute §5).

---

### NOMENCLATURA, MATCHER, INTEGRITAT DE GRADUACIÓ, PROVINENÇA (2026-07-08)
> Diagnosi: `docs/diagnosis/DIAGNOSI_NOMENCLATURA_ALIES_2026-07-08.md` (vigent, no segellada; N3 n'implementa
> només la part del matcher) · cadena N3 `e90f39f · beadaaf · 513cb88`.

- **[NOMENCLATURA] El catàleg canònic (`POMMaster`/`POMGlobal`) NO conté nomenclatura de client.**
  Els àlies viuen a `CustomerPOMAlias (customer, pom, client_code, client_description)`, unicitat
  `(customer, client_code)` i **NO** `(customer, pom)` — un client pot tenir dos codis per al mateix
  POM (Losan H.11 sleeve opening / H.16 cuff opening). Autoria: **fitxa de Client** (àlies) vs
  **POMBrowser** (catàleg). `GradingRuleSet.customer` = **FK real** (backfill des de
  `SizeSystem.customer_codi`).
- **[MATCHER] Ordre canònic de `find_pom_master(code, description, customer)`:** (a) **àlies exacte
  del customer → HIGH** (client_code casa contra codi *i* descripció); (b) **descripció + sinònims
  canònics** → HIGH/MEDIUM; (c) **fuzzy → LOW → pendents** (mai auto-vincula, llindar c2b19bd);
  (d) **codi_client/root = fallback LOW transitori, a retirar** (abans anaven 1r amb HIGH). Si
  `customer=None`, se salta (a).
- **[MATCHER] Guard anti-many-to-one:** dues files del mateix document → mateix POM per
  descripció/fuzzy = **totes a pendents** (mai la 2a sobreescriu la regla de la 1a; `GradingRule`
  únic per `(rule_set, pom)`). **L'àlies exacte n'és EXEMPT** (repetició legítima de POM per client).
- **[INTEGRITAT DE GRADUACIÓ] Cap regla es deriva d'una taula incompleta.** Talla del run sense
  valor = fila incompleta = **BLOQUEIG de creació (400)**, mai derivació amb deltes parcials (un break
  perdut degradava a LINEAR en silenci). Normalització d'etiquetes: **pont únic `canonical_size_label`**;
  el prompt (`wizard_context` amb `size_run`) és **ajuda, mai garantia**. Deute: tres normalitzadors
  (`canonical_size_label` / `_norm` / `_norm_label`) → **convergir** (§5).
- **[PROVINENÇA] (llei nova, PENDENT d'implementar):** tot `GradingRuleSet` importat ha de guardar el
  **document d'origen + snapshot dels `values_by_size`** extrets i re-clavats. Un actiu de secret
  industrial ha de ser **auditable i regenerable contra la seva font**.

### Sèrie DA — decisions d'arquitectura (2026-07-09)

> **Per què el prefix `DA-`:** la sèrie `D-N` ja està ocupada i és citada des del codi
> (`D-1`, `D-3`, `D-10` PROPAGAR-conscient, `D-12` Watchpoints → `models_app/views.py:216`,
> `models_app/models.py:849`, `WatchpointsPanel.jsx:9`, `CheckMeasureEditor.jsx:323`).
> Les decisions d'aquesta tanda entren amb prefix propi per no col·lidir-hi.
> Registre d'execució (commits, deploys, verificacions) a `ESTAT_PROJECTE.md`; aquí només
> **què es va decidir i per què**.

#### S03a — Arxius: el terra

- **DA-7 — El règim de `/media/` és aïllament + gate.** Els bytes els servia nginx per
  `alias`, sense cap check d'autenticació ni de tenant. Es tanca per les dues bandes:
  aïllat per tenant (P2a) i servit per una porta de Django (P2b). El `location /media/`
  directe sobreviu només per a les superfícies encara no migrades → **a jubilar**.
- **DA-8 — Cap dataURL nou dins `document.json`.** L'extracció inline→assets es fa en
  desar (P3), no en una migració de dades: les fitxes velles se sanegen soles en re-desar-se.
  Motiu: una migració hauria hagut de desempaquetar i reempaquetar 209 `.ftt` sense necessitat.
- **DA-9 — [FORAT AMB NOM, NO ES TAPA]** El grup "Marcades" de `FittingDetail` filtra
  `tipus='MARCADA'` i cap escriptor l'emet. El filtre és **correcte**; el que falta és
  l'emissor, que posarà el flux de marcada. Tapar-ho ara seria inventar-se una semàntica.
- **DA-10 — El menú de fitxa tècnica crida `open-task` i navega només en èxit** (pendent,
  S03b). El gate d'allow-list viu al backend; una navegació directa se'l saltaria. En 403,
  oferir "obrir en consulta" en lloc d'error sec.
- **DA-11 — Es poda el que ningú llegeix, no el que sembla mort.** `path_servidor` (escriptura
  pura, zero lectors) i `get_url()` (zero consumidors) fora. `addModelFitxer`, en canvi, **NO
  es poda**: és òrfena però és la llavor confirmada del futur FilePicker.
- **DA-12 — L'upload d'`ItemFitxer` valida mida + mimetype per whitelist** (pendent, S03b).
  Explícitament: **no** copiar el patró de `Customer.upload_logo`, que no valida res.
- **DA-13 — Descàrrega signada de curta vida.** Els bytes surten per dues portes, totes dues
  a Django: `download/` (capçalera `Authorization`) i `download-signed/?token=` (TimestampSigner,
  salt propi, TTL 900 s). Motiu: `<a href>` i `<img src>` **no poden** portar capçaleres i el
  JWT viu a localStorage. `AllowAny` a l'endpoint signat és deliberat — el permís el porta el
  token, que només rep qui ja s'ha autenticat per llegir la fila; el payload és l'id, així que
  un token no val per a un altre fitxer. Reutilitza el mateix helper X-Accel que l'endpoint
  autenticat. **Corol·lari:** `SECURE_PROXY_SSL_HEADER` és obligatori, o `build_absolute_uri`
  emet `http://` dins pàgines `https://` (mixed content).
- **DA-14 — `FittingPhoto` té el mateix forat que DA-13 acaba de tancar** per a `ModelFitxer`
  (bytes servits per `/media/` sense gate). NO resolt. Quan es faci: aplicar `serve_model_file()`
  i DA-13 tal com són, **no redissenyar**.

Corol·laris tècnics d'S03a que manen sobre el codi futur:
- **Una sola porta d'escriptura de fitxers:** `save_model_file` és l'ÚNIC escriptor de la
  invariant `is_current`/`versio`. Qualsevol escriptor nou hi delega. (La invariant segueix
  **sense constraint a BD**; la vigila `audit_fitxers`, que informa i no arregla.)
- **Eix únic `tipus`.** `categoria` queda en estil G2: el camp viu, ningú l'escriu amb valor
  semàntic ni el llegeix. El DROP, en un sprint posterior.
- **Un sol lloc extreu els binaris inline** (`extract_document_assets`), compartit pel camí de
  plantilles i el de documents. Els objectes de l'editor són un **arbre** (grups amb fills):
  qualsevol recorregut pla es deixa les imatges niades.
- **Diferida amb nom — promoció ② (catàleg→model).** El `.ftt` és auto-contingut
  (`src="assets/<sha16>.<ext>"`, noms interns del zip): importar un document entre models NO
  exigeix reescriure cap `src`. Prerequisit ja tancat per DA-8. **Fet a S03b · P5 (DA-27).**

#### S03b — Catàleg + fitxa (2026-07-09, nit)

- **DA-23 — El catàleg té fitxers propis (`ItemFitxer`), mirall d'`ModelFitxer`**, no una taula
  genèrica. Mateixa invariant de cadena, mateixos `TIPUS_CHOICES`. **Sense `categoria`**: un eix
  mort no es reprodueix en un model nou. Tampoc `url_extern`/`origen`/`generat_des_de`: s'afegiran
  si hi ha un cas, no per simetria.
- **DA-24 — [DUPLICAR ÉS MÉS NET QUE ABSTREURE, AQUÍ]** `save_item_file` duplica les 20 línies de
  `save_model_file` en comptes de compartir un helper parametritzat: els conjunts de camps
  difereixen prou perquè l'abstracció sortís més llarga i més opaca. El que **sí** es comparteix és
  el que és realment comú: checksum, mimetype, `validate_upload` i el servei de bytes
  (`serve_fitxer`, un de sol per als dos models).
- **DA-25 — Cada model de fitxer té el SEU salt de signatura.** El payload del token és només l'id;
  amb un salt compartit, un enllaç signat per a `ModelFitxer` id=5 obriria `ItemFitxer` id=5.
  Corol·lari de DA-13, no una variant.
- **DA-26 — L'upload valida per EXTENSIÓ, no per mimetype**, i el sostre és el **més estricte dels
  que ja existien** (20 MB, de `tech_sheet_views.py`), no el d'nginx. Els formats de domini
  (`.dxf`, `.rul`, `.ftt`) arriben com `application/octet-stream`: filtrar per `content_type` els
  rebutjaria falsament. Tanca DA-12.
- **DA-27 — El cicle ① catàleg→model és IMPORTACIÓ, no edició in-place.** Es crea un `ModelFitxer`
  nou (cadena pròpia) amb `derivat_de_item` com a procedència; l'`ItemFitxer` no es toca mai i pot
  desaparèixer (SET_NULL) sense afectar la còpia. Un `.ftt` es copia tal qual: és auto-contingut
  des de DA-8, per tant **cap `src` s'ha de reescriure**.
- **DA-28 — L'escriptura al catàleg exigeix `CONFIGURE`; la importació cap al model, no.**
  `usar-al-model` escriu al MODEL: mateix gate que `upload-fitxer` (`IsAuthenticated`). Exigir
  `CONFIGURE` per importar impediria al tècnic fer la seva feina.
- **DA-29 — [FRONTERA, NO ES CREUA]** La promoció ② (model→catàleg) **no es construeix**, tot i que
  amb `derivat_de_item` i `save_item_file` al lloc seria barata. Falta decisió de producte: quina
  versió es promociona, qui pot fer-ho, i què passa si l'item ja té un fitxer d'aquell tipus.
- **DA-30 — El menú de fitxa tècnica crida `open-task` i navega només en èxit; el 403 d'allow-list
  ofereix "obrir en consulta", no un error sec.** Implementa DA-10. Perquè el frontend distingeixi
  el bloqueig tou del dur sense fer *match sobre el text del missatge*, `open_model_task_view` emet
  ara un `code` discriminant (`task_type_not_allowed` / `no_profile`). Additiu.
- **DA-31 — Cap fallback silenciós a consulta.** Si `open-task` respon de manera inesperada (sense
  `task_id`, timeout), es mostra error i s'atura: val més que el sistema sembli trencat que amagar
  un fallo real fent-lo passar per una consulta normal. El mode consulta, quan és legítim, es fa
  **visible** amb un badge a l'editor (fins ara era silenciós).
- **DA-32 — El FilePicker crida `addModelFitxer`, no la reimplementa.** Confirma DA-11: la funció
  òrfena era la llavor, i el "futur tab Components" que anunciava el comentari (R1) és aquest
  drawer. Importar des del picker puja sempre al MODEL, mai al catàleg.

#### Mòdul Comercial (B1→B4c) + biblioteca client + i18n + fitxa Empresa

- **DA-15 — La safata d'albarà parteix de `ModelTask`, no de `WorkOrder`.** És l'única manera
  de veure feina facturable sense WO (col·lectors i encàrrecs directes). Amb dades reals de
  Brownie, 3 de 3 tasques albaranables tenien `work_order=NULL`. Patró a preservar.
- **DA-16 — [UN SOL CONCEPTE, NO DOS]** La visibilitat de línia (camp `visible`) substitueix
  qualsevol `exclude_from_billing` o `TaskType.facturable`. Un sol interruptor (ull obert/tancat)
  cobreix "cobro 0 € però ho mostro" i "no ho mostro en absolut". Els totals es calculen NOMÉS
  sobre les línies visibles.
- **DA-17 — "Albaranat" = la tasca té QUALSEVOL línia d'albarà** (DRAFT o ISSUED), no només
  ISSUED. Evita el doble comptatge si dos DRAFT simultanis reclamen la mateixa tasca. Esborrar
  un DRAFT allibera la tasca.
- **DA-18 — El guard de reobertura només bloqueja amb albarà ISSUED/INVOICED.** Un DRAFT encara
  es pot desfer, per tant no bloqueja. Injectat a `transition_task`, no a cap view: un sol punt.
- **DA-19 — A `WorkOrderAdjustment`, `kind` és atribut mutable, mai part de la identitat**
  (`UniqueConstraint(work_order, model_task)`). Re-resoldre un extra actualitza la fila, no en
  crea una segona.
- **DA-20 — [NO POSAR REGLA DURA]** Durant la fase beta del catàleg POM, crear un POM nou des
  del wizard de diccionari va **sense gate ni validació dura**. Decisió conscient de l'Agus: no
  posar regles extra dures mentre el catàleg canònic no sigui definitiu. El rastre de procedència
  (customer + diccionari + data) es manté per decidir la promoció a `POMGlobal` quan tanqui la beta.
- **DA-21 — Traduccions: patró híbrid** (columna EN canònica + taula `Translation` genèrica per a
  la resta), **no** un mixin de columnes fixes (`name_es`, `name_fr`…). Avui ja calen 3 idiomes i
  se n'esperen més: el mixin no hauria escalat.
- **DA-22 — El logo de tenant accepta qualsevol format** (SVG/PNG/JPG) i el backend el normalitza
  sempre a PNG ràster amb cairosvg. Mai exigir un format concret a l'usuari (arran del feedback
  "administració no comprovarà res").

### S03c — Higiene de fitxers i backend del Navigator (2026-07-10, IMPLEMENTAT)

Font de fets: `docs/diagnosis/DIAGNOSI_S03C_NAVEGACIO.md`. D17/D18/D19 aplicades a S03c-1;
D16 aplicada a S03c-2; **D20/D21 IMPLEMENTADES a S03c-3** (AssetNavigator + els 4 endolls).

- **D16 — L'import model→model d'un `.ftt` DESCONGELA, no re-resol.** Els camps de plantilla
  congelats a `type:'text'` tornen a `type:'field'`; l'asset `assets/field_customer_logo.<ext>`
  es **purga del ZIP**; l'objecte `image kind:'logo'` amb la URL de l'origen s'elimina;
  `metadata{}` es regenera. La capçalera `data_block kind:'header'` **no es toca** (ja llegeix
  de `modelData` en viu). Un `.ftt` importat torna a ser "jove", com un d'acabat d'instanciar.
  Cobreix els 4 punts materialitzats de Q4.4.
  - **IMPLEMENTAT a S03c-2** (`unfreeze_document`, C3.1 + `reescriure_ftt_per_model`, C3.2).
  - **Precisió tancada per l'Agus (2026-07-10, S03c-2):** després de descongelar, el pipeline
    **re-resol contra el model destí** (`unfreeze → resolve_placeholders(destí)`), de manera que
    el `.ftt` desat queda congelat AMB les dades del destí. L'alternativa (persistir `type:'field'`
    i resoldre al render, per simetria literal amb la capçalera) exigia tocar `FieldChipNode`
    (`TechSheetEditor.jsx:594`), que avui pinta un xip `{clau}` i no llegeix `modelData`. Es va
    descartar per abast: era feina de frontend i afectava l'editor de plantilles.
  - **Condició descoberta i resolta:** el congelat era **irreversible** (`_resolve_obj` no
    conservava la `key`). Va caldre una capa (i) que deixa la marca `field_key` en congelar.
    Els `.ftt` anteriors a S03c-2 **no en tenen**: es deixen tal qual i l'API retorna un `avis`.
    Cap heurística de matching per contingut (fràgil, i corrompria documents).
- **D17 — `derivat_de_model` és un camp NOU, no es reutilitza `generat_des_de`.** Els tres camps
  de procedència codifiquen coses diferents: `generat_des_de` = *artefacte generat des d'un altre
  fitxer* (PDF EXPORT d'un `.ftt`); `derivat_de_item` i `derivat_de_model` = *còpia amb
  procedència*. Cap dels tres tenia lectors (eren write-only): la decisió no és per col·lisió
  tècnica sinó per no amagar dues semàntiques sota un sol camp. **S03c-1 hi afegeix el primer
  lector** (`derivat_de_label` al serializer), tal com demanava la condició de D17.
- **D18 — `.xlsx` i `.xls` entren a `ALLOWED_UPLOAD_EXTENSIONS`.** `upload_file_view` no validava
  res i hi ha 1 `.xlsx` real a la BD pujat per aquesta via. Endollar-hi `validate_upload` sense
  ampliar la whitelist hauria rebutjat dades que el sistema ja accepta. La whitelist s'amplia
  ABANS d'activar el guard, mai al revés.
- **D19 — El `chown` viu a la comanda, no al runbook.** `move_media_tenant --apply` normalitza
  l'owner de cada directori que crea i de cada fitxer que mou (`--owner`, default
  `www-data:www-data`). `os.makedirs` els creava amb l'owner del procés (root al deploy) i
  gunicorn corre com `www-data`: causa provada de l'incident del 2026-07-10. Un pas manual que
  cal recordar és un pas que un dia s'oblida.
- **D20 — Les facetes del Navigator es deriven AL CLIENT.** Amb ~20 models, es calculen en
  memòria sobre el `list` existent; l'endpoint d'agregació server-side queda **diferit amb nom**,
  no descartat. Llindar de re-obertura: **~300-500 models, o lentitud percebuda real**. Quan
  toqui, el patró a clonar és `fase-counts` (`models_app/views.py:97-133`), que ja agrega
  respectant els mateixos filtres que el board.
  - **✅ IMPLEMENTADA a S03c-3** (`components/assets/AssetNavigator.jsx`, commit `cb2b0d8`).
    `models.list({page_size: 200})` — per sota del `max_page_size=200` de `DefaultPagination`.
    El comentari del component diu explícitament que, en créixer el tenant, això ha de passar a
    agregació al servidor i **no** a una pàgina més gran.
- **D21 — El tab/secció "Fitxers" del GTI va a la columna DETALL de `GarmentTypes.jsx`**
  (consulta al lloc de consulta), **no dins el wizard `ItemAuthoring.jsx`** (autoria). L'slot
  d'import inert de Fase C (`ItemAuthoring.jsx:272-288`) queda **intacte**. Punt d'inserció:
  després de la graella de cards, abans de tancar el bloc de la columna DETALL.
  - **✅ IMPLEMENTADA a S03c-3** (commit `02aa0b4`). Secció amb el `FileList` compartit del
    navegador. **Tria de versions:** per defecte només els caps de cadena (`is_current`), amb
    un interruptor "Totes les versions" — la vista és de consulta i `FileList` ja mostra la
    columna `v`. **Gates:** veure = LECTURA; pujar = CONFIGURE (`ItemFitxerViewSet.create`, P4).
  - **Forat tapat pel camí:** el flux d'upload de P4 existia **només al backend**; el frontend no
    n'havia tingut mai cap superfície (`itemFitxers` només exposava `list` + `usarAlModel`). Per
    això `ItemFitxer` tenia **0 files**. S03c-3 hi afegeix `itemFitxers.create`.

### S03c-3 — AssetNavigator i els 4 endolls (2026-07-10, IMPLEMENTAT)

- **El navegador no coneix cap cicle de domini.** `AssetNavigator` retorna la selecció via
  `onPick` i prou; **mai** crida `usar-al-model`. El consumidor distingeix un `ModelFitxer` (porta
  `model`) d'un `ItemFitxer` (porta `garment_type_item`) pel propi objecte, i decideix.
- **Sobirania al canvas (C5.2).** El que s'insereix és SEMPRE un fitxer del model actual: un fitxer
  d'un altre model o del catàleg es copia abans (`usar-al-model`). Si s'hi inserís l'origen,
  esborrar el model A trencaria el document del model B.
- **Importar geometria (C5.3) NO copia.** Allà s'importen els **bytes** (un SVG es converteix en
  paths editables; una imatge s'encasta com a dataURL): el document no en guarda cap referència, i
  per tant no hi ha sobirania a defensar. `TIPUS_GEOMETRIA = [SKETCH_SVG, SKETCH_NET,
  SKETCH_FLETXES]` — els tipus que el canvas sap rebre avui. PATRO/ESCALAT/MARCADA queden fora
  perquè són DXF i el motor no hi és.
- **Asimetria de parsers resolta.** `ItemFitxerViewSet.usar_al_model` heretava
  `parser_classes=[MultiPart, Form]` de la classe (que `create` necessita) i rebutjava amb **415**
  el JSON que li enviava `endpoints.js`: el camí catàleg→model era **inaccessible des de la UI**.
  Override a l'`@action` (commit `5c9a7a2`).

### Flux de fitting — integritat i navegació (2026-07-10, IMPLEMENTAT)

Font de fets: `docs/diagnosis/DIAGNOSI_FLUX_FITTING_NAV.md` (inclou el cens P0).

- **D22 — El fitting NOMÉS edita la talla base, i el guard viu a la VISTA.**
  `fitting_line_is_non_base` rebutja amb 400 tota escriptura d'usuari a una talla no-base
  (PATCH i propagar). Fins ara la vista les acceptava i `close_piece_fitting` les descartava en
  silenci. El guard usa la MATEIXA font que `consolidate_base_from_fitting`; si divergissin,
  tornaria el forat. El motor NO es toca. La propagació interna a les germanes es manté: aquells
  `valor_real` són derivats del motor, no feina del tècnic. La graella pinta un sol group (base),
  com `CheckMeasureEditor`.
- **D23 — El gravat comprova el segellat REAL abans de navegar.** `seal` ja retornava `estat`;
  ara es llegeix. Amb un GarmentSet amb peces sense resoldre, `_seal_session` no tanca i abans
  s'hi navegava igual. Tancament parcial del bucle de `close` → missatge "N de M", sense reintent
  ni rollback (informar, no corregir el motor).
- **D24 — La fulla de convocatòria és la superfície de "mirar"; entrar a una sessió és
  "treballar".** Per això l'obertura automàtica `Programada → Oberta` al muntar `FittingDetail`
  **es manté**: F2-7 queda resolta per la navegació, no pel codi. Abans de la fulla, entrar era
  l'única manera de mirar i la mutació era abusiva; ara la fulla mostra models, hores, estats i
  watchpoints sense entrar enlloc.
  *Fet que ho reforça (no era a la diagnosi):* `started_at` té lector real
  (`planning/views.py:335-337`, `durada_real` del calendari); moure l'`open` fora del muntatge el
  perdria en entrar per URL directa.
- **D25 — El landing d'una sessió editable és la graella, no la revisió.** La card "Veure /
  editar taula" no cridava cap endpoint ni movia cap estat: era un toggle de client. La revisió
  segueix sent el landing de les sessions Tancada/Anullada (split de consulta).
- **D26 — La fulla no agrega watchpoints al backend.** El `Watchpoint` s'ancora al MODEL, no a la
  sessió: la fulla fa una crida per model (~5). Crear un agregat seria decisió d'arquitectura, no
  necessitat de volum. Es mostren com a lectura; la resolució viu al model.
- **D27 — Afegir models a una convocatòria SEGELLADA es permet (flexibilitat conscient).**
  Resol la §PER DECIDIR 8 de la diagnosi (F8c-5, `services.py:883-890`): avui és possible i **es
  deixa possible**. Una convocatòria segellada no és un document tancat, és una jornada: que hi
  entri un model tard és operativa normal, no corrupció. El segellat protegeix **les línies de la
  sessió** (`fitting_line_is_locked`), no la composició de la convocatòria.
- **D28 — Les sessions individuals entren directes, sense fulla.** La fulla de convocatòria és el
  punt d'entrada i de retorn **de les sessions convocades**. Una sessió solta no en té ni en
  necessita: s'obre i es torna al lloc d'on es venia. No es fabrica una fulla d'un sol model per
  simetria.

---

### Tasca unificada de mesures (2026-07-10, IMPLEMENTAT — sprint Y)

Font de fets: `docs/diagnosis/DIAGNOSI_TASCA_UNIFICADA_MESURES_2026-07-10.md`.
Les 6 decisions de l'Agus. Lleis de domini derivades → §2 (`size_check` = LA tasca; sessió = contenidor).

1. **Reús del `TaskType` `size_check` pk=20.** Cap alta de catàleg, `code` intacte. La tasca
   unificada ja existia; no calia inventar-la, calia adonar-se'n.
2. **Eina i mode intactes** (`mesures` / `presa`). **L'origen `FITTED`/`CHECKED` es decideix per
   PRESÈNCIA DE SESSIÓ en consolidar**, mai pel catàleg. El catàleg no sap de fittings.
3. **El rellotge de la TASCA mana** (`TimerEntrada` → Welford). La sessió conserva
   `data`/`hora`/`durada` com a **AGENDA** (franges busy del scheduler) i `started_at`/`finished_at`
   com a **acta**. Res del temps de treball es mesura des de la sessió. → **`FittingDurationStat`
   es JUBILA** (va a G5).
4. **Àncora: `ModelTask.fitting_session`**, FK nullable `SET_NULL` per string. És un **punter
   MUTABLE al cicle vigent**: expressa **provinença, no historial**. L'historial és
   `TaskTransition` + el log F1 amb `_fitting_ref`.
5. **La reagenda s'extreu i es fa genèrica:**
   `tasks/services_scheduling.py::reagenda_tasca(model, data_represa, task_type_code)`. No és una
   funció del fitting: és una funció de tasques.
6. **La tasca es materialitza EN OBRIR, mai en agendar.** Agendar 5 models i que n'apareguin 3
   crearia 2 "Pendents" fantasma que ningú tancaria. La convocatòria promet; obrir compromet.

---

### Dissolució de FittingDetail (2026-07-10 → 2026-07-12, IMPLEMENTAT — sprints X i Y)

Font de fets: `docs/diagnosis/DIAGNOSI_DISSOLUCIO_FITTINGDETAIL_2026-07-10.md`.

- **`FittingDetail` queda JUBILADA com a pantalla de treball.** Sobreviu **només com a vista
  read-only de sessions Tancades/Anul·lades** (el split de consulta 40/60, intacte). La ruta viva
  (`/fittings/<id>` d'una sessió editable) → **redirect a Mesures amb context de sessió**. No hi ha
  dues superfícies de mesura: n'hi ha una.
- **Mode sessió a Mesures:** les **preses són editables**; **règim, deltes i nomenclatura són
  read-only** (`lockRules`). Mesurar no és regradar: el que es toca dins una sessió és la realitat
  mesurada, no la regla. El **panell de sessió** (Canvis / Observacions / Imatges) viu **dins la
  mateixa superfície**, no en una pantalla a part.
- **Reobertura de grading segellat = ACTE HUMÀ EXPLÍCIT.** El backend retorna
  `code='grading_sealed'`; el front obre **modal** i, si l'usuari confirma, reintenta amb
  `allow_reopen_sealed`. **Ancorat a la tasca**, no a la sessió. Mai una reobertura silenciosa.
- **`close_piece_fitting` és ATÒMIC des de 2026-07-10** (`transaction.atomic`, commit `d736adc`):
  un 400 del guard fa rollback total (`BaseMeasurement` + F1 + Welford junts). Tanca CO-4.
- **`GarmentSet`: FORA D'ABAST fins al primer conjunt real.** Direcció registrada perquè no es
  perdi: la fulla llistarà les peces del set, i `createPiece` acceptarà `model_id ≠ session.model`.
  No es construeix infraestructura per a un cas que encara no existeix.

---

## 5. Deutes i peces pròpies anotades (no ara)

- **Tolerància:** avui 2 valors; sempre simètrica ± → fusionar a 1 sola columna (p.ex. ±0.6). Sprint POMs.
- **Gating de `resolve`** = `IsAuthenticated` → revisar al grup de govern/gating.
- **Nomenclatura editable per-model:** autoria de nom a nivell model (avui `nom_fitxa` és per-POM
  compartit) → peça pròpia post-unificació.
- **Combo/multipeça:** `GarmentSet`, 2 graelles per peça identificades (presa simultània) → peça pròpia.
- **i18n nous idiomes** (fr/it/pt/de): infra-readiness fixa (un cop) vs traducció lineal; desacoblar
  "fer N-idiomes-ready" de "publicar traduccions"; eix car amagat = dades de domini (noms POM a BD).
- **N+1 preexistent a `garment-types/`** (vist a S03c-1, fora d'abast): 19 queries a `pom_target`
  que arrossega `fields='__all__'` a `GarmentTypeSerializer`. Existia abans de C2.1 (40 queries
  sense l'annotate); C2.1 no l'empitjora ni el corregeix.
- **`audit_fitxers` estava TRENCAT des del trasllat de media d'S03a** — ✅ RESOLT (2026-07-10, commit
  `fix(models_app): audit_fitxers compara disc i BD al mateix espai de noms`). Comparava el `name` de
  la BD (`model_fitxers/…`, relatiu a l'arrel del tenant) contra paths de disc relatius a `MEDIA_ROOT`
  (`fhort/model_fitxers/…`). No casaven mai → **cada fitxer sortia alhora com a fantasma i com a orfe**
  (228 files → 228 fantasmes + 228 orfes; la veritat era 0 i 0). Un esborrat massiu guiat per aquesta
  sortida hauria destruït tots els fitxers vius. Fix: `_disk_names()` recorre `default_storage.location`
  (= `MEDIA_ROOT/{schema}`, la traducció inversa de `storage.path(name)`) en lloc de `MEDIA_ROOT`, de
  manera que els dos costats parlen l'espai de noms de `fitxer.name`. Com a efecte secundari deixa de
  llegir el media d'altres tenants en auditar-ne un de sol. La comprovació (a) d'invariant de cadena
  sempre va ser fiable (no toca disc) i no s'ha tocat.
- **Orfes de disc preexistents** — ✅ RESOLT (neteja 2026-07-10): els 8 orfes reals vivien a
  l'arrel ANTIGA `media/model_fitxers/` (inabastables: el storage resol sota `media/<schema>/`).
  Esborrats amb el directori. `media/fhort/` no en té cap.
- **Asimetria estructural bytes↔fila:** el sistema pot tenir bytes-sense-fila (orfes) i
  fila-sense-bytes (fantasmes) alhora. S03c-1 va posar guard al costat de la fantasma
  (`serve_fitxer`, C1.3) i va tapar la font dels orfes (C1.1); no hi ha cap guard que impedeixi
  que se'n tornin a crear per altres vies.
- **`ItemFitxer` té 0 files:** tota la superfície de catàleg (incl. `fitxers_count`) està
  verificada per construcció, no amb dades reals.
- **`test_regim_sense_fallback_400` FALLA a `dev`** (vermell PREEXISTENT, verificat amb `git stash`
  contra HEAD `b08baaf`): `set_pom_regim_view` retorna 200 on el test espera 400 quan el POM no té
  `GradingRule` de fallback. No té res a veure amb el fitting; peça pròpia.
- **5 línies no-base rectificades a la BD** (cens P0): totes del model 182 `[QA-SC] OLIVIA DRESS`,
  en 2 sessions ja `Tancada`. Cap dada de client → **no cal migració a `ModelGradingOverride`**.
  Queden mortes on són; esborrar-les és decisió de l'Agus, no s'ha tocat cap fila.
- **La taula "Canvis" del ReviewScreen segueix pintant totes les talles**
  (`FittingDetail.jsx:321-353`). És read-only i mostra l'històric de sessions anteriors, que sí pot
  contenir canvis no-base. No s'ha tocat.
- **`.ftt` anteriors a S03c-2 no són descongelables** (sense marca `field_key`). En importar-los
  model→model, els camps de plantilla mantenen les dades de l'origen i l'API retorna `avis`.
  Es re-marquen sols en re-instanciar-se; no hi ha migració de dades i no se n'ha de fer cap
  per heurística.
- **`preview.png` no es propaga a l'import model→model** (S03c-2): era un render dels valors de
  l'origen. Es regenera al primer desat des de l'editor. Si algun dia el Finder mostra
  miniatures, un `.ftt` importat i no desat encara no en tindrà.
- **Asimetria de parsers entre els dos `usar-al-model`** (preexistent, vista a S03c-2):
  `ItemFitxerViewSet` té `parser_classes=[MultiPart, Form]` i el seu `usar-al-model` rebutja
  JSON amb 415; el de `ModelFitxerViewSet` accepta JSON. El client de C5 ho ha de saber.
- **Els missatges d'error del backend són literals en català** (no i18n). No és nou (tot
  `models_app/views.py` ho fa), però l'`avis` de l'import model→model és el primer text llarg
  de cara a l'usuari que surt del backend. Si es vol i18n de missatges d'API, és peça pròpia.

### Deutes nous (2026-07-10 → 2026-07-12)

- **🔴 `DECISIONS.md` ESTÀ TRACKEJAT AL REPO** (hi va entrar al commit `7f05b1f`, 2026-07-09,
  "docs: consolidar diagnosis i documents de metode pendents de commitar"), **contradient la llei
  §1** que diu que `ESTAT_*`/`DECISIONS.md` NO es commiten mai. `ESTAT_PROJECTE.md`, en canvi, NO
  està trackejat. **Decidir en fred, no en calent:** o `git rm --cached DECISIONS.md` (i mantenir
  la llei), o canviar la llei i acceptar que el cervell del projecte viu versionat. Avui la
  situació és la pitjor de les tres: mig dins, mig fora, i la capçalera del fitxer encara diu que
  el canònic viu a `/root/fhort-sessions/` (on de fet **no hi ha cap dels dos fitxers**).
- **G5 += la maquinària de temps del fitting, morta.** `FittingDurationStat` +
  `_capture_duration` + `update_fitting_duration_stat`: **s'escriu i no es llegeix mai** (0 files).
  El rellotge bo és el de la tasca (Welford). Jubilar amb G5. Hi va també `override_changed`,
  **sempre False**.
- **G6 += jubilació de `PieceFittingLine` com a magatzem.** Amb la talla base com a únic eix, la
  taula deixa de tenir raó de ser com a magatzem de treball. Hi queda la **propagació interna a les
  germanes sense lector** (**CO-1 residual**, ara darrere el guard P1a): ja no s'hi pot escriure des
  de la UI, però el codi de propagació segueix viu i sense destí.
- **Migració `tasks/0025_seed_canonical_task_types` editada DESPRÉS d'aplicada** (canvi cosmètic:
  rebateig a "Mesurar prenda"). Inert a la pràctica —el seed ja havia corregut i el `code` no es
  toca—, però trenca la regla que una migració aplicada és immutable. Anotat, no revertit.
- **Fila òrfena `files/0001` a `django_migrations` de PROD.** Inert (l'app no existeix).
  **NO TOCAR**: esborrar-la no arregla res i pot trencar un `migrate` futur.
- **Residus de media a PROD sense referència a BD** (`bulk_imports`, `model_fitxers`,
  `import_sessions`, `tenant_logos`): bytes que van quedar a l'arrel antiga després del trasllat
  d'S03a. No fan mal (ningú els serveix). **Neteja de disc en fred**, mai durant un deploy.
- **`main` local d'staging va 467 commits endarrerit** (`685c944`, 2026-06-16). No descriu res:
  ni PROD ni el remot. **Actualitzar-lo o ignorar-lo conscientment**, però deixar de mirar-lo:
  el pre-deploy del 12/07 va haver d'usar `origin/main` perquè `main..origin/dev` donava una xifra
  sense sentit.

---

## 6. Històric (decisions completades, per traçabilitat)

- *(buit — s'hi baixaran les decisions vives en completar-se)*
