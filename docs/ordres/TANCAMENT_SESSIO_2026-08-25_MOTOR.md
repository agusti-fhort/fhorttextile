# TANCAMENT SESSIÓ 25/08/2026 — FTT 08 S44 MOTOR DXF (dia d'investigació)
Blocs per copiar a ESTAT_PROJECTE.md i DECISIONS.md (vault + servidor). Cap línia de codi al repo avui: tot fonament.

═══════════════════════════════════════════════════════════════════
BLOC PER A ESTAT_PROJECTE.md
═══════════════════════════════════════════════════════════════════

## ═══ S46-MOTOR · 25/08 — DIA D'INVESTIGACIÓ: ecosistema llegit, tesi tancada 3/3, paquet Montse complet ═══

**Pla §2-bis executat sencer (punts 1-4) + 2a passada gimnàs + disseny UI. Zero codi al repo.**

**5 INFORMES PRODUÏTS (tots al vault / docs/diagnosis):**
1. `INFORME_PYGARMENT_MODEL_DADES_2026-08-25.md` — Edge/Panel/Interface/StitchingRule llegits al codi (MIT verificat). Troballes: T1 corbes amb controls RELATIUS al marc de la vora (resposta al conflicte àncora-sobre-corba); T2 costura = parella {panel,edge} + matching per FRACCIONS; T5 el plec NO existeix (meitats = 2 panells + costura — la nostra llei de mirall és superior, no s'adopta); T7 labels semàntics viatgen al JSON; T9 bug viu a Edge.__eq__ (invertit) — llegim idees, mai codi a cegues.
2. `INFORME_PLANEGCS_DECISIO_SOLVER_2026-08-25.md` — manual Abdullah (65 pàg.) + codi C++ contrastat. **VEREDICTE: scipy propi, planegcs NO s'enllaça** (desajust d'escala: 36 tipus de restricció vs ~5 nostres majoritàriament lineals; port WASM per a navegador, no Django; el valor és la formulació). 6 idees adoptades: I1 diagnosi QR del jacobià (=AUDITORIA del graf: DoF, redundants, conflictes) · I2 plec per REDUCCIÓ de paràmetres (impossible de violar) · I3 partició en components · I4 prioritat = durs QP + objectiu (el dragging: fitting = dragging amb noms) · I5 driving/reference (POM que mesura sense manar) · I6 Success≠Converged + residu per restricció.
3. `INFORME_FORMATS_CLO3D_837_2026-08-25.md` — .pacx = XML pla llegible I ESCRIVIBLE; .zpac = contenidor (el .pac binari codificat NO es toca, EULA). Costura CLO = peça + LÍNIA + Ratio inici/fi → **TESI TANCADA 3/3** (CLO+PyGarment+planegcs = SewRelation v1). Grading CLO = coordenades ABSOLUTES per punt × talla (camp extensional, estil Montse; el 837 importat porta les 5 talles idèntiques — el DXF no duia regles). «Neteja» d'Agus quantificada: 604 punts a CLO vs milers al font — round-trip per CLO NO fidel; respectar la geometria és diferenciador real. Notch = landmark ancorat a línia (X,Y,Alpha) — precedent industrial de l'àncora de POM. **OPORTUNITAT: exportar .pacx omplint GradingPoint des del solver → segon banc de verificació de la niada (visual+simulació) — dins la finestra de la trial (~13 dies).**
4. `INFORME_GIMNAS_N2_GARMENTCODEDATA_2026-08-25.md` (1a passada, Claude Code) — 1.200 patrons; label oficial pobre (body/leg/arm), taxonomia rica derivada del nom: 24 rols / 13 famílies. Empremta primitiva: 52% rols / 63% famílies → +prior GTI i log(àrea): **60% / 78%**. TROBALLA DURA: davant/darrere NO és al contorn (4 parelles = mateix polígon, 0% per construcció) — és al graf de costures + col·locació. Recomanacions: escala absoluta (+8,2 famílies) · davant/darrere fora de la forma · graf de costures. NO cal: afinar τ, refinar mirall.
5. `INFORME_ESBORRANYS_SESSIO_MONTSE_2026-08-25.md` (2a passada, Claude Code) — 4 lliurables PAPER DE TREBALL: plantilla anatòmica per família + parelles de costura empíriques (dels stitches) + vocabulari de landmarks + 60 SVGs per a Biblioteca GTI. 3 premisses tombades: vertex_labels són índexs 3D (la font bona: etiquetes de vora 2D) · llicència DADES = CC-BY-4.0 (citació per fila; atribució ha de viatjar a M7) · panells avg 12,1/max 35. **🔑 HPS DERIVABLE: escot—[espatlla, sempre 1 vora, 2.371/2.371]—sisa; extrems = HPS + punta d'espatlla → A11 deixa de ser bloquejant propi, passa a aigües avall del pas 1 (taxonomia de trams).** Pinça només a 4 rols (mai davants faldilla/pantaló) = 3r senyal davant/darrere. **🚨 LÍMIT: cos únic 172 cm — el corpus val per a reconeixement/topologia, ZERO per a graduació (el banc de grading segueix sent Montse).** Absents: infantil, petos, bodies, auxiliars DEREK.

**DISSENY UI CONSOLIDAT:** `DISSENY_TALLER_PATRO_V2.md` (vault) + `MOCKUP_TALLER_PATRO_V2.html` — 5 requisits d'Agus amb llei i estat (R5a cotes CAD ja FET; R2 punts semàntics = cara de la Capa 1, penja de taxonomia trams) + 2 horitzons: PATRÓ-PRIMER (POMs al patró de catàleg → model hereta → taula Mesures generada; sobirania intacta: sembra/posseeix; auditoria bidireccional per construcció; 4 preguntes Patró C obertes) + DESPLEGAT SIMÈTRIC (vista derivada mai persistida; eix de plec = DADA declarada; àncores mirrored=true; solver el rep reduït per I2). +3 preguntes candidates Montse (10-12). Mockup validat per Agus amb condició: **abans del definitiu, Patró A de cens de la UI actual (capes i altres valuosos) + captures.**

**OBJECTIU DE FASE (PROPOSAT, PENDENT RATIFICACIÓ AGUS):** «El model paramètric de la peça, verificat contra Montse» — 4 criteris: (1) Rosetta verda (238 regles vs graf, o desviacions documentades) · (2) solver reprodueix el camp de Montse des de GradedSpec+graf ≤0,5 mm/punt/talla (tolerància a ratificar) · (3) niada del solver desplega talles al PolyPattern (+CLO si .pacx funciona) · (4) auditoria re-mesura per talla verda al 837. **La fase NO promet:** reconeixement automàtic en producció · sembra corpus LOSAN · UI Taller v2 construïda · bucle PAT-3 sencer. Risc declarat: un sol model de banc (837).

**FORATS OBERTS (per ordre):** QA-TALLER-D (prerequisit 0, bloqueja construcció) · sessió Montse = camí crític PERÒ rebaixada: de construir a VALIDAR (3 esborranys + preguntes d'ofici pur: repartiment E/S/E1, LOSAN, 0078) · verificació Rosetta executable JA al xat sense solver (només funcions d'error — cal re-pujar DXF+RUL de Montse + nostre) · gate niada→PolyPattern (gest d'Agus, VM) · corbes relatives = hipòtesi adoptada NO validada contra el 837 · 28 commits dev sense push · trial CLO ~13 dies.

**GIMNÀS N2 operatiu:** /root/n2_gym/ (scratchpad, venv propi) — scripts+CSV reproduïbles de les 2 passades; svg_gti/ 60 fitxers 452 KB amb INDEX.csv (citació CC-BY per fila). Baixada 2a: 1.200 elements · 1,8 GB xarxa · 27,5 MB disc.

═══════════════════════════════════════════════════════════════════
BLOC PER A DECISIONS.md
═══════════════════════════════════════════════════════════════════

## ═══ S46-MOTOR · 25/08 — LLEIS I DECISIONS DEL DIA D'INVESTIGACIÓ ═══

**D-INV-1 · TRAM + FRACCIÓ ÉS L'ESTÀNDARD DE FACTO (fet, 3/3).** La costura serialitzada com a «peça + tram amb identitat + fracció de longitud d'arc» coincideix a CLO3D (.pacx: línia+Ratio), PyGarment (fraccions projectades + subdivisió fins a 1:1) i planegcs (parametrització del sketcher). SewRelation v1 queda validada per representació. Tancat.

**D-INV-2 · SOLVER v2 = SCIPY PROPI (decidit llegint, no estimant).** planegcs NO s'enllaça (escala, plataforma, LGPL sense benefici). Formulació: incògnites = desplaçaments de vèrtexs de tram per talla · plec i miralls ELIMINATS PER REDUCCIÓ (estructura del vector, no equació) · durs per client (grading: deltes POM + orígens; fitting: correccions de prova) · objectiu: deformació mínima+suau + correspondències · resolució KKT lineal + Gauss-Newton residual · DIAGNOSI QR ABANS DE RESOLDRE (DoF, redundants, conflictes, per component) · sortida amb vocabulari Success≠Converged + residu per restricció (alimenta la llista de problemes de l'export). Els POMs tenen DOS ROLS declarables: driving (mana al grading) / reference (mesura i informa — l'auditoria).

**D-INV-3 · CORBES RELATIVES AL MARC DEL TRAM (hipòtesi ADOPTADA, pendent de validació).** Els controls de corba es guarden relatius al segment del tram; el camp de desplaçament mou NOMÉS vèrtexs i les corbes es re-deriven conservant forma (font: PyGarment T1; dissol el conflicte àncora-sobre-corba del cens A/C/S2). ABANS de fixar-la com a representació canònica: validar contra les corbes reals del 837 (residus A5).

**D-INV-4 · MATÍS DE LA LLEI DE TOPOLOGIA: subdividir una vora per casar costures o allotjar una pinça NO és crear topologia** — és refinar la mateixa frontera (segmentar_vora ja hi viu). La llei «el sistema mai crea topologia» prohibeix peces/forats/vores noves, no el refinament de frontera. (Font: PyGarment T8 + matching CLO.)

**D-INV-5 · PLEC: LA NOSTRA LLEI GUANYA (contrastada).** PyGarment modela meitats com 2 panells + costura; CLO porta FoldAngle com a semàntica de simulació. Cap dels dos restringeix el grading a l'eix. La nostra (plec = restricció de mirall; al solver, REDUCCIÓ de paràmetres) es manté i és superior per al domini. DESPLEGAT SIMÈTRIC = vista derivada, mai persistida; eix de plec = DADA declarada al panell de peça (detecció assistida proposa, humà confirma); àncores al costat mirall = (punt canònic, mirrored=true).

**D-INV-6 · COL·LOCACIÓ AL LLENÇ = PRESENTACIÓ, MAI DADA.** Offset/rotació de visualització per peça persistits a servidor; la geometria importada no es toca mai (precedent: Instance de CLO). Round-trip per CLO demostrat NO fidel (re-mostreja: 604 vs milers) — «respectem la geometria» és diferenciador de producte, no mania.

**D-INV-7 · GARMENTCODEDATA: ÚS I LÍMITS (fet mesurat).** Val per a: taxonomia per família (esborranys), parelles de costura empíriques, vocabulari de landmarks (de vores 2D, NO vertex_labels 3D), SVGs per a Biblioteca GTI, gimnàs del reconeixedor. NO val per a: graduació (cos únic 172 cm — el banc de grading és NOMÉS Montse), infantil/petos/bodies/auxiliars DEREK. Llicència DADES: CC-BY-4.0 — l'atribució (Korosteleva et al., ECCV 2024) viatja amb qualsevol derivat, inclosa la futura Biblioteca GTI (M7). Els esborranys són PAPER DE TREBALL: cap sembra sense validació de Montse (llei LOSAN).

**D-INV-8 · HPS ÉS DERIVABLE DEL GRAF (troballa 100%: 2.371/2.371).** Espatlla = l'única vora entre escot i sisa; extrems = HPS + punta d'espatlla. A11 deixa de ser bloquejant propi → aigües avall del pas 1 (taxonomia de trams). El nostre CAD no porta etiquetes equivalents (confirmat Agus): la cascada N1-N4 segueix sent el camí.

**D-INV-9 · DAVANT/DARRERE: FORA DE LA FORMA (reforçada amb 3r senyal).** El contorn no el porta (1a passada); es resol amb regla a part: graf de costures + col·locació + PRESÈNCIA DE PINÇA (només 4 rols, mai davants de faldilla/pantaló).

**LLEI DE FORMA UI (del DISSENY_TALLER_PATRO_V2):** punts semàntics al llenç = Capa 1 visible (penja de taxonomia trams, no és sprint independent) · vermell reservat a ANOTACIÓ/COTA · icones Tabler outline · tokens mockup → tokens reals (D-9) · panell de peça pre-omplert amb EVIDÈNCIA (chips N1/N2/N4) · franja de diagnosi «informa, mai bloqueja» amb vocabulari I1/I6 · el mockup no mana sobre trams exclosos. Abans del mockup definitiu: Patró A de cens de la UI actual + captures.

═══════════════════════════════════════════════════════════════════
CUES VIVES DESPRÉS D'AVUI (recordatori curt, no substitueix ESTAT)
═══════════════════════════════════════════════════════════════════
· Ratificar objectiu de fase + tolerància ≤0,5 mm (Agus, Patró C)
· Push consolidació (28 commits) + gate niada→PolyPattern (Agus, VM)
· Verificació Rosetta al xat (re-pujar DXF+RUL Montse + nostre)
· QA-TALLER-D (prerequisit 0)
· AGENDAR MONTSE (paquet de sessió COMPLET: 3 esborranys + 60 SVGs + preguntes 1-12)
· Prova .pacx mínima (1 peça, 2 talles) DINS finestra trial CLO
· Patró A cens UI actual + captures (previ al mockup definitiu)
· Pilot 0078 dels 21 POMs del 837 (Agus)
