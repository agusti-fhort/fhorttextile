# CUA DEL TAULELL · S38 — dues maquetes + un disseny nou

**Data:** 08/08/2026 · Sessió paral·lela. Outputs propis, **cap contacte amb el vault**, cap brief
a Claude Code, **`wizard_model` no tocat**. Els fitxers esperen aquí per pujar-los tu.

**Verificació en execució** (Chromium, 1500 i 1280 px), abans d'entregar:
cap error de JS · **cap text per sota de 10px** · cap desbordament horitzontal · cap radi fora de
6/12/999 · i els gestos exercitats un per un (v. §3).

---

## 🚨 ABANS DE RES: les tres esmenes anteriors NO són a `ops/maquetes/`

Em vas dir que estaven «entregades i pujades». **No hi són.** Ho he comprovat en obrir la cua:

| Fitxer a `ops/maquetes/` | Senyal | Estat |
|---|---|---|
| `maqueta_fitting_v4.html` | `LAYEN` encara diu `'Entretela':'Interlining'` (línia 333) i `sis:{lay:'Folre', folg:2.0}` (322) | **original** |
| `maqueta_grading_rules_v4.html` | `const REGIMS=['LINEAR','LINEAR+BREAK','STEP','FIXED']` (368) | **original** |
| `maqueta_size_library_v3.html` | 10 aparicions de `sys:true/false` | **original** |

Els tres corregits segueixen intactes a
`scratchpad/maquetes_esmenades/`. No els he copiat jo a `ops/maquetes/`: la còpia és teva i no
sé si «pujades» volia dir en un altre lloc. **Si els vols aquí, digue-m'ho i els copio** — són
tres `cp` i ja estan verificats.

---

## 1 · `maqueta_temps_declarat_i_modal_v2.html`

> La v1 era a `ops/maquetes/` (arrel), no a `superades/` — no ha calgut demanar-la.
> **Estructura, seccions, gestos i JS: idèntics.** Només pell. He mantingut el nom de família
> (`_i_modal_`) i he pujat la versió: v1 → v2.

### El bastiment que no hi era (§8b)
La v1 és anterior al §8b: era una pàgina solta amb `<h1>` i prou. Ara porta **top bar** amb
breadcrumb `Fhort Textile Tech › Models › BRW-SS26-0002`, **menú de pantalla** blanc amb el **←
sempre primer** (32px, icona 16) i les píndoles de secció, i la **identitat sobre el fons de
pàgina, sense contenidor**. Les tres peces viuen a **Tasques del model**, que és d'on surten
(«torna al panell de tasques del model», ho deia la v1 mateixa).

**Zero accions primàries a la identitat** (§8c: les pantalles de consulta en poden tenir cap): el
blau d'aquesta pantalla viu dins del crono, que és on hi ha feina per completar.

### Pell
| Què | v1 | v2 |
|---|---|---|
| Superfícies | crema `--head #f5efe4` i `--sel #f2e6cf` (= el `--gold-pale` que la norma **elimina**) | blanc `--panel`, fons `--bg #fbfaf8`, selecció `--sel #f7f5f2` + filet d'or |
| Acció | marró `--btn #9a5f22` | `--accio #2b65c2`, **un sol blau per estat** |
| Tintes | `#3a3530 / #8a8279 / #a9a199` | `--text-main #1d1d1b` · `--text-soft #6e6a64` · `--text-faint #98938b` |
| Semàfor | verd `#5f8a3f`, vermell `#b4483a`, ambre `#c47f1a` | `--ok #2e7d32` · `--err #b42318` · `--warn-state`/`--warn-ink` |
| Tipografia | 9 · 9.5 · 10.5 · 11.5 · 12.5 · 13 · 17 · 34px | **10 · 11 · 12 · 14 · 15 · 18 · 22** (+ el crono, v. sota) |
| Radis | 5 · 6 · 7 · 8 · 9 · 11px | **6** controls · **12** targetes i modal · **999** píndoles |
| Badges | fons pla + tinta, sense filet | **fons suau + tinta + filet fi del mateix color**, sempre |

### Sis decisions de pell que val la pena que miris
1. **El crono: 34px → 28px, amb token batejat `--fs-clock`.** El número gran de la casa és 22/600
   (§8e) i 34 no és a cap escala. 28 és la interlínia de l'h1, ja al sistema. **És una excepció
   conscient** (§3: «amb token i nom, o no existeixen»); si el vols a 22 estricte, es canvia el
   token i prou.
2. **El número de secció es queda daurat, però amb tinta principal.** Blanc sobre `#c27a2a` és
   **3.4:1** i no passa AA; `--text-main` hi dona **4.91:1**. És literalment el vet de C5:
   *quan el fons de marca no pot canviar, canvia la TINTA*.
3. **La selecció del modal és «on soc», no verd.** `--sel` + filet d'or. El verd de la norma és
   per a la **inclusió en una definició** (targets, capes); aquí s'està triant un camí.
4. **«Descartar» baixa a terciària** i el **vermell ple només surt a la confirmació final** (§5.5).
   Abans «Sí, descartar» i «Aturar» tenien el mateix pes visual.
5. **Deshabilitat baixa el fons, no la tinta** (§5.7). La v1 feia `opacity:.45`.
6. **Icones Tabler outline** a 14px dins de les opcions del modal i 16px al ←. Els glifs `✓` i
   `⏸` de la v1 no eren icones del sistema. **Mantenen el seu significat**: marquen què fa cada
   opció, no quina està triada — això ho diu el fons.

---

## 2 · `maqueta_pom_form_v1.html` — DISSENY NOU (el B2 d'A1)

Dissenyat de zero **contra el model real**, llegit avui: `POMMaster`, `POMMasterSerializer`
(`fields = '__all__'`), el `POMMasterViewSet` i els dos camins d'escriptura alternatius.

### On viu
**No és una pantalla nova.** És el **panell dret del Catàleg de POMs** quan es crea o s'edita
(§8f: el formulari s'obre **al mateix lloc** de la fitxa). Mateix bastiment, mateixa llista a
l'esquerra, mateix idioma de classes que `maqueta_cataleg_poms_v3.html`. Cap modal gran.

### Els camps: els nou que el model té, ni un més
`POMMaster` té **deu** camps concrets escrivibles; el formulari en porta **nou** i el desè el
mostra sense escriure'l.

| Camp | Al formulari | Nota |
|---|---|---|
| `codi_client` (max 30) | Text · **obligatori** | Únic camp sense `blank=True`, amb `nom_client` |
| `nom_client` (max 200) | Text · **obligatori** | |
| `categoria` FK | Select, amb «— sense categoria —» | `null=True, blank=True` |
| `pom_global` FK | **Bloc propi amb 3 estats** (v. sota) | `null=True, blank=True` |
| `tolerancia_default_minus` | Número, def. 0,60 | **Dos camps, no un «± 0,6»** |
| `tolerancia_default_plus` | Número, def. 0,60 | La tolerància del sistema és **asimètrica** |
| `actiu` | Casella, def. ✓ | |
| `pendent_revisio` | Casella, def. ✗ | Amb el `help_text` literal del model |
| `notes` | Textarea | |
| `origen_import` | **Es mostra, no s'edita** | Provinença de màquina; no és un camp per teclejar |

### El lligam amb el catàleg global: els 3 estats, dits amb paraules diferents
És el punt que la Fase 2 va corregir al serializer, i el formulari l'hereta:

| Estat | Quants a `fhort` | Què diu la pantalla |
|---|---|---|
| **No lligat** (`null`) | 122 de 396 POMs | «No és al catàleg global. **No és un error ni una dada incompleta**» — el tenant proposa, promoure és un acte a part. I: **els camps de "com es mesura" no existeixen per a ell**, no és que estiguin buits |
| **Lligat, sense informar** (cadena buida) | 149 de 274 globals | «Lligat, però el catàleg global no diu com es mesura» — badge taronja, i camp a camp «el catàleg global no ho té informat» |
| **Lligat amb dada** | 125 | Bloc read-only amb unitat, des d'on, fins on, referència i zona del cos |

**Lligar i deslligar són gestos propis**, mai un efecte secundari de desar.

### «Creació = acte conscient», implementat i no només escrit
- Un POM nou **neix buit**: cap valor heretat de la selecció, cap lligam automàtic. Els únics
  valors previs són els `default` que declara el model.
- **«Crear el POM» està deshabilitat fins que codi i nom tenen contingut.**
- El peu ho diu en veu alta: *«Res s'ha creat encara. El POM neix quan cliques Desar, i no abans.»*
- Badge **ENCARA NO DESAT** mentre el formulari és nou.

### Una etiqueta que calia corregir
El camp es diu `codi_client`, **però és el codi d'aquesta casa, no el del client**. El vocabulari
de cada client viu a part, als àlies (`CustomerPOMAlias`), i un mateix POM pot tenir un codi
diferent per client. L'etiqueta diu **«Codi del catàleg»** i el hint ho explica — si es titulés
«Codi del client» la pantalla estaria mentint sobre el model.

---

## 3 · Què s'ha exercitat en execució (no a ull)

**Temps declarat:** els cinc estats del crono en seqüència · un sol blau visible per estat · els
dos modes de correcció · el vermell ple mesurat a la confirmació (`rgb(180,35,24)`) · el crono
avança de debò (`00:14:32 → 00:14:33`) · el modal deixa exactament una opció triada.

**Formulari de POM:** els tres estats del lligam, un per un · «Desar» deshabilitat amb només el
codi, habilitat amb codi + nom · l'avís de duplicat salta amb `D` i **deixa desar** · desapareix
amb un codi net · editar el POM `D` **no** avisa del seu propi codi · els comptadors 30/200 ·
i **el focus no salta mentre s'escriu** (només es repinten les parts derivades).

---

## 4 · 🚨 El forat que el disseny ha destapat: tres camins d'escriptura que no diuen el mateix

No és una decisió de maqueta, és backend, i el formulari no s'ho pot inventar:

| Camí | Unicitat de `codi_client` | Camps que accepta |
|---|---|---|
| `POST /api/v1/poms/` (ViewSet) | ❌ **cap comprovació** | tots |
| `POST /api/v1/poms/crear-tenant/` | ✅ rebutja el codi repetit amb 400 | només 4 (`codi_client`, `nom_client`, `categoria_id`, `notes`) |
| `PATCH /api/v1/poms/{id}/nomenclatura/` | ❌ **cap** | deixa **renombrar fins a xocar** |

I `codi_client` **no té unicitat ni al model ni a la BD**: avui hi ha **12 codis repetits** a
`fhort` (`D · S · S2 · J1 · U1 · BJ · C1 · L1 · E4 · H · U · E7`, ×2 cadascun).

**El formulari avisa del xoc com a OBSERVACIÓ i deixa desar**, perquè fingir una comporta que el
sistema no té seria pitjor que no tenir-la. Si el codi ha de ser únic, això és una **constraint +
un backfill dels 12**, no una validació de pantalla — i llavors cal decidir quin dels tres camins
sobreviu.

## 5 · 🚨 El catàleg global no té endpoint

`POMGlobal` (274 files) **no té ni ViewSet ni serializer propis a tot el backend**: només s'hi
arriba aplanat i read-only des de `/api/v1/poms/`. **El cercador de lligam del formulari no té
d'on llegir.** La llista `GLOBALS` de la maqueta és una mostra per poder dibuixar el gest, marcada
com a tal — però **cal exposar el catàleg global abans de construir aquesta peça**. És el mateix
patró que ja teníem obert amb els règims: la pantalla la demana i el backend no la serveix.

## 6 · Decisions meves, per si les vols vetar

1. **Qui pot crear POMs?** El ViewSet és `IsAuthenticated` i prou: qualsevol usuari autenticat pot
   crear, editar i esborrar el catàleg sencer. **No hi he posat cap gate perquè no n'hi ha cap.**
2. **«Pendent de revisió» com a casella editable en tots dos sentits.** El camp és per als POMs
   nascuts d'importació i el seu sentit és que la patronista el **desmarqui**. Si vols que només
   es pugui desmarcar, es converteix en una acció d'un sol sentit.
3. **«Esborrar» no és al formulari.** Es queda a la fitxa, que és qui sap si el POM s'usa
   (`GET /poms/{id}/us/` ja retorna `pot_esborrar` i `motiu`).
4. **El crono a 28px** amb token batejat (§1, punt 1).

## 7 · Vist i no tocat

- **`POMCategory` té el vocabulari duplicat**: conviuen dues famílies de codis per a la mateixa
  categoria (`CAT-UB` i `Upper body`, tots dos «Part superior del cos»; igual amb `CAT-SL`/`Sleeve`,
  `CAT-CL`/`Collar / Neckline`…). El desplegable de categoria d'una pantalla real les ensenyaria
  totes dues. **No és feina de maqueta**, però algú ho ha de netejar.
- `wizard_model`: **no tocat**, com vas dir.

## 8 · Fitxers

```
maqueta_temps_declarat_i_modal_v2.html   ← reskin NORMA v1 (la v1 es pot moure a superades/)
maqueta_pom_form_v1.html                 ← disseny nou (B2)
shot_temps.png · shot_pomform.png · shot_pomform_nou.png   ← captures de verificació
```

---

# 9 · MICRO-CONSULTA (08/08, read-only) — camins d'escriptura de `POMMaster` AVUI

**HEAD verificat: `2f533d36`** (8 commits per sobre de la meva lectura anterior). Dels vuit,
**només un toca `pom/`**: `16208b11 · construction-types serveix nom_es`, i només afegeix 7 línies
a `s2_serializers.py`. `git log -S"codi_client"` i `-S"POMMasterViewSet"` en aquest tram: **buits**.

## Resposta curta
**El ViewSet segueix viu, obert i acceptant codis repetits.** No s'ha desllligat, ni tancat, ni
restringit. Segueix registrat (`urls.py:22`), segueix sent un `ModelViewSet` pelat amb
`IsAuthenticated`, i **no té cap `create`/`perform_create`/`http_method_names` propi**.

## ⚠️ Correcció del que et vaig reportar: no en són tres, en són SIS
Vaig llistar tres camins. N'hi ha **sis d'actius per HTTP**, i **dos sí que es defensen** —un
d'ells millor que cap dels que jo havia mirat.

| # | Camí HTTP | Validació de `codi_client` | Viu |
|---|---|---|---|
| 1 | `POST` · `PUT/PATCH /api/v1/poms/{id}/` — `POMMasterViewSet` | 🔴 **CAP** | ✅ |
| 2 | `POST /api/v1/poms/crear-tenant/` | 🟢 `filter(codi_client=code).exists()` → **400**. Exacte, **case-SENSITIVE** | ✅ |
| 3 | `PATCH /api/v1/poms/{id}/nomenclatura/` | 🔴 **CAP** — deixa **renombrar fins a xocar** | ✅ |
| 4 | `POST /api/v1/models/{id}/pom-propi/` | 🟢🟢 **doble capa** (v. sota) | ✅ |
| 5 | `POST /api/v1/pom/customers/{id}/dictionary/commit/` | 🔴 **CAP** — el comentari ho diu: «POM tenant-only nou (**sense gate — fase beta**)» | ✅ |
| 6 | `POST` import · `import_session_poms_view` | 🟠 **parcial** (v. sota) | ✅ |

### Per què el 4 és el bo
`create_model_pom_view` fa dues coses que cap altre fa:
1. **Espai del CLIENT** — `colisio_de_codi(customer_id, codi)` → **409 `NOMENCLATURA_OCUPADA`**
   amb *amb què* xoca («U1 ja és BUTTON SPACING al catàleg Brownie»).
2. **Codi de la CASA** — `filter(codi_client__iexact=...)`: si està ocupat **no peta, el
   QUALIFICA** (`{cust}-{codi}`, o `M{model_id}-{codi}`, truncat a 30).

I el seu propi comentari assenyala l'origen del dany: *«El codi de la CASA no és el del client, i
copiar-hi el del client és exactament el que va fabricar els 12 duplicats que hi ha avui.»*
Nota: és l'únic que compara amb **`__iexact`**; el camí 2 ho fa case-sensitive, o sigui que
`ch` i `CH` passen la porta del 2 i no la del 4.

### Per què el 6 és taronja i no verd
La porta 409 `codi_duplicat` (`extraction_views.py:1838-1846`) **només salta si el codi ja té
2+ POMs tenant-only** (`.count() > 1`): bloqueja per **ambigüitat**, no per duplicació.
Amb `count==1` **reutilitza**, amb `count==0` **crea**. O sigui que per aquesta branca no en
fabrica de nous. 🔎 **No he traçat `_pla_de_resolucions`**, que alimenta l'altra branca que crea
(`:1872`, amb el codi que tria el tècnic) — és l'únic punt d'aquest cens que no dono per tancat.

## Per què el 1 i el 3 no els atura res més avall (re-verificat avui)
| Capa | Estat |
|---|---|
| `codi_client.unique` | `False` · `db_index=False` |
| `Meta.constraints` / `unique_together` | `[]` / `()` |
| `POMMaster.clean()` / `.save()` propis | cap dels dos |
| `POMMasterSerializer` | **cap** `validate*`, `validators`, `extra_kwargs` ni `read_only_fields` |
| Signals amb `sender=POMMaster` | **cap** a tot `fhort/` |

## Fora d'HTTP (no són camins d'usuari, però escriuen)
`load_losan_package` · `extend_pom_catalog` · `seed_baby_poms` · `seed_master_delta_catalog` ·
`seed_brownie_cataleg` · `reseed_tenant_fhort` · `consolidate_pom_catalog` — management commands.
Cap comprovació d'unicitat de `codi_client` (van per `get_or_create`/`update_or_create` amb
claus pròpies).

## Conclusió per a la maqueta
El que diu `maqueta_pom_form_v1.html` **es manté i no cal tocar-lo**: el formulari va contra el
camí 1, que no té comporta, i per això **avisa sense bloquejar**. L'únic que canvia és el §4 del
report: el diagnòstic és més gros del que vaig dir —**sis camins, quatre criteris diferents**— i
ja hi ha una implementació de referència a `pom-propi/` que resol el problema bé. Si es
normalitza, és aquella la que s'ha de copiar, no inventar-ne una altra.
