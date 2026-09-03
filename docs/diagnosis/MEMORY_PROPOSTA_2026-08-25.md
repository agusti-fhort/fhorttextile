> # 🛑 PROPOSTA — no aplicar sense OK d'Agus
> Fitxer podat proposat per a `~/.claude/projects/-var-www/memory/MEMORY.md`.
> **Aquesta capçalera de tres línies NO forma part del fitxer**: es treu en aplicar.
> Cens i llista de baixes: `CENS_MEMORY_2026-08-25.md`.

---

# Memory index

> El ganxo, no el contingut: el detall viu al fitxer de cada tema. **Una entrada que
> explica què va passar ja és massa llarga.**
> 🚨 llei · 🔴 pendent viu · 🔑 fet vigent · 🚩 pendent amb dubte
> **On va cada cosa:** canvia COM ES DIAGNOSTICA → LLEI · què és VERITAT ara → FET ·
> què VA PASSAR → **només al fitxer del tema, mai aquí**.

## 🚨 LLEIS DE DIAGNOSI — llegir abans de concloure res

- 🚨 **«No hi ha res» sol ser error de mètode.** [bd-staging](ftt-bd-staging-com-sinterroga.md) — la BD viva és `postgresql@18-main` **port 5433** (la unitat `postgresql` diu `inactive` i és un paraigua buit); tenants `public=1 · fhort=2 · los=13`, **id=6 no existeix**; les meta-ordres de `psql` **soles a la seva línia** o fabriquen un buit fals
- 🚨 **Una acta diu què era veritat el dia que es va escriure.** [acta-pot-mentir](ftt-acta-al-codi-pot-mentir.md) — verifica importadors i rutes abans de construir-hi, i el COS de la funció abans d'aturar-te per un «bloquejant»
- 🚨 **El gunicorn serveix el codi de quan va arrencar.** [desplegat-vs-disc](ftt-backend-desplegat-vs-disc.md) — 404 (o guard fantasma) amb el codi bo al disc = `systemctl restart ftt-staging`. Compara l'hora del procés amb la del commit **abans** de censar duplicats
- 🚨 **Obrir una lectura ARMA les escriptures** que ningú no assolia (i al revés). [lectura-arma](ftt-lectura-que-arma-escriptures.md) · `?mode=entry` és un GEST: [una QA que hi entri ESCRIU AL DOMINI](ftt-bloc-b-cami-model.md)
- 🚨 **Una ⓘ muda no vol dir «no hi ha dada»**: sonda a la cel·la. [nom-local-tapa](ftt-nom-local-que-repeteix-tapa-la-traduccio.md)
- 🚨 **Una presa TANCADA és indistingible d'una que no ha existit mai**; el log d'nginx reconstrueix la QA sencera (servidor UTC, Agus UTC+2). [presa-segellada](ftt-presa-segellada-indistingible.md)
- 🚨 **Cada pantalla que entra al patró de peces s'hi cola un predicat de MODEL i no canta.** [família de tres](ftt-s2-fixes-s36-pell.md)
- 🚨 **Un camp nou de la REGLA vol `getattr` als TRES lectors genèrics**, al clon del backend I al del front. [camp-nou-getattr](ftt-camp-nou-de-forma-vol-getattr.md)
- 🚨 **Una fixture que obre i tanca una tasca sense ESCRIURE és una CONSULTA**: no alimenta el Welford i peta lluny de la causa. [consulta-fixtures](ftt-consulta-no-es-mostra-fixtures.md)
- 🚨 **Un desbordament es MESURA** (Chromium headless); una diagnosi read-only **no fa login**. [mesurar-impressió](ftt-mesurar-impressio-i-no-login.md)
- 🚨 **Mai dues corregudes alhora** sobre la mateixa superfície. [tram-instància](ftt-tram-instancia-20260802.md)
- 🚨 **Un `SerializerMethodField` heretat mata l'escriptura**: desa amb 200 OK i no passa res, amb check/build/QA verds. [sobirania-pom](ftt-sobirania-pom-font-unica.md)

## 🚨 LLEIS DEL GEST — com es toca

- 🚨 **El gate d'un tram és PROPORCIONAL**: check + build + NOMÉS l'app tocada. Una suite morta a mitges deixa `schema_name='test'` i dona 68 errors aliens. [verd-proporcional](ftt-verd-proporcional.md)
- 🚨 **Sessions concurrents a `dev`: MAI `git stash`**, i `git add` de paths explícits — **que tampoc n'hi ha prou**: l'índex és compartit i un commit es pot endur feina viva d'una altra sessió. [git-concurrent](ftt-dev-concurrent-git.md) · [pathspec](ftt-commit-sense-pathspec-endu-el-stage-alie.md)
- 🚨 **Una migració aplicada i no commitada és una divergència BD↔repo que CAP gate detecta.** [migracions](ftt-migracions-es-commiten-en-aplicar-se.md)
- 🚨 **Staging serveix `frontend/dist`: `npm run build` ÉS desplegar.** [tram-t-n](ftt-tram-t-n-cataleg-i-neteja.md)
- 🚨 **Un symlink de `node_modules` DESTRUEIX el directori real** (`npm ci` a 5 worktrees). [m4](ftt-m4-numeral-i-desbordament.md)
- 🚨 **L'`unattended-upgrades` reinicia Postgres a ~06:39 UTC i mata la suite**; una suite d'1 h vol `setsid nohup` (el wrapper de background mata a 10 min). [apt](ftt-suite-apt-mata-la-correguda.md) · [b3b4](ftt-s2-t7-b3b4-porta-peces.md)
- 🚨 **Una lectura sense gate es tanca amb PODA del payload, no amb 403.** [lectura-comercial](ftt-lectura-comercial-sense-gate.md)
- 🔒 **La traducció de domini NO viu a la BD** (vigent). [traducció](ftt-traduccio-domini-no-va-a-bd.md)
- 🚩 **L'agent NO pot emetre el JWT de QA** (classificador); Playwright a `/tmp/qa-venv`; un `goto` directe captura el **401 d'nginx**. [qa-jwt](ftt-qa-token-jwt-bloquejat.md)
- 🔑 Mètode versionat com a skills · les diagnosis van a `docs/diagnosis/`. [skills](ftt-metode-com-a-skills.md) · [ubicació](ftt-diagnosis-docs-location.md)

## 🔴 PENDENTS VIUS — feina que una sessió futura no pot passar per alt

- 🔴 **INFRA sense instal·lar:** `pip install` de la dep HEIC en desplegar [heic](ftt-heic-fotos-fitting.md) · cron capa 2 del refresh JWT [k1k6](ftt-k1k6-sessio-jwt-refresh.md) · cron del guard de tasca oblidada [guard](ftt-guard-tasca-oblidada.md)
- 🔴 **Patró C (motor):** ratificar convenció **CCW + origen mín(y,x)** · política de fraccions ja desades (**`SegmentPreference` en quarantena proposada**) · **camp de sentit relatiu a `SewRelation`** (el matcher ja el calcula i el llença). [desplegat](ftt-fil-desplegat-tancat.md)
- 🔴 **Reprocessament de PROD pendent** pel bug destructiu d'adjunts (`update_fields` sense `'fitxer'`). [embut](ftt-embut-adjunts-coll.md)
- 🔴 **R1 a MITGES**: el bateig no arriba a les taules. [bateig](ftt-bateig-no-arriba-a-les-taules.md)
- 🔴 **4 columnes del r2 sense camp a POMGlobal**: pre-tren de migració, decisió d'Agus. [catàleg-v5](ftt-cataleg-v5-forat-esquema.md)
- 🔴 **4 taules T1b congelades** (163, 166, 177, 195). [delta-break](ftt-delta-break-t1b-regla.md) · **taules Q8 congelades per llei i sense declarar versió**. [f4quater](ftt-f4quater-lectura-unificada.md)
- 🔴 **La fitxa es queda a 2 mm de l'A4 vertical** (198→192, sostre 190): decisió d'Agus. [f4quater](ftt-f4quater-lectura-unificada.md)
- 🔴 **Neteja del LOS antic BLOQUEJADA** [fase1-losan](ftt-fase1-losan-cataleg.md) · `los` **sense POMMaster** (confirmat 25/08: 0). [patró-c-retorn](ftt-federacio-patro-c-retorn.md)
- 🔴 **QA pendents:** 409 `ruleset_altre_client` [g1g2](ftt-g1g2-graduacio-porta-propia.md) · tancament de selecció a l'editor [editor](ftt-editor-tancament-seleccio.md) · fletxa curva [fletxa](ftt-fletxa-curva-sortides.md) · assets a `save_document`/`importarDelTenant` [imatges](ftt-sprint-fitxa-imatges.md)
- 🚩 **Sense context llegible** (destinar o eliminar): B1/B2 aturades [cua](ftt-cua-prec4-abc.md) · D-31.26 [maquetes](ftt-cens-maquetes-ui.md) · P8 [c5ui](ftt-c5ui-execucio-nocturna.md) · `measurements_chat_view` no tocat [origen-guard](ftt-comprovacio-i-origen-guard.md)

## 🔑 FETS VIGENTS · infraestructura, BD i desplegament

- **BD staging** `ftt_staging` · unitat `postgresql@18-main` · **port 5433** · esquemes `public`/`fhort`/`los`. Ports, `pg_restore` i tenants: [staging-infra](ftt-staging-infra.md)
- **Cens de la BD (mesurat 25/08)** — `fhort`: 39 models · 144 POMMaster · 3 PatternFile · 21 PatternPOM · 2 ExportAcknowledgement · **0 peces amb doblec**. `los`: 51 models · **0** POMMaster · 0 PatternFile
- **django-tenants va pel Host header**: `curl -H "Host: staging.fhorttextile.tech"` o dona **404 a tot**. [host](ftt-staging-tenant-host.md)
- **Verifica el deploy contra el root de CADA vhost.** [vhost](ftt-vhost-root-per-domini.md)
- **Permisos de `media`**: `safe_makedirs` fa `chmod` DESPRÉS del `mkdir` i mata el setgid → `0o2775`; **el mes nou torna a caure**. [permisos](ftt-media-uploads-permisos.md) · [namespace](ftt-media-namespace-tenant.md) · [crom](ftt-s2-fitxa-patrons-crom.md)
- **Estat de PROD sense SSH**: pel backup diari. [prod-dump](ftt-prod-estat-via-dump.md) · e2e real a staging: [playwright](ftt-e2e-playwright-staging.md)
- **Tests**: `settings_test` amb `FTT_TEST_DB` [m5](ftt-m5-retroactiu-r1-i-tren.md) · el control del front és `npx eslint src`; no hi ha vitest, és `node --test` [f22](ftt-f22-vocabulari-marques.md) · [s37](ftt-s37-vet-c5-chip.md)

## 🔑 FETS VIGENTS · POM, talles i grading

- **Nomenclatura**: `codi_client` ≠ `client_alias` ≠ `pom_code_global` ≠ `nom_fitxa`; `codi_client` és el codi **de la casa** i el catàleg del client és `CustomerPOMAlias`. [noms](ftt-nomenclatura-pom-camps.md) · [catàleg-client](ftt-poms-cataleg-client.md)
- **Llei de sobirania ÀLIES > TENANT > GLOBAL**; la contradicció fina viu DINS del model (`pom_code` tenant, `name_en` global). [sobirania](ftt-sobirania-pom-font-unica.md)
- **«POM System» NO és un model**: és un rètol sobre `GarmentPOMMap`. El GRUP surt de `GarmentGroup`, mai de `POMCategory`. [vocabularis](ftt-diagnosi-vocabularis-pom-system.md) · [capes](ftt-nit-capes-run-n1n6.md)
- **El break es PRESENTA en convenció de DOCUMENT (±1)**; la BD segueix en MOTOR. I **el break sempre ha estat un INTERVAL**: `intervals_de` és el punt únic, resolt en espai de **sistema**. [convenció](ftt-break-convencio-document.md) · [intervals](ftt-interval-viu-en-espai-de-sistema.md)
- **L'eix és `size_system`, no `target`**; la rigidesa és DADES+UX. [baseset](ftt-baseset-implementat.md) · [cardinalitat](ftt-size-systems-cardinalitat.md) · `talla_mapping` és llei: [aparellament](ftt-aparellament-talles-done.md)
- **Assignar un joc JA materialitza residents**: l'observable és `origen`. [p05d](ftt-p05d-graduacio-superficie.md) · ruleset buit → FIXED amb 200, i LINEAR+0 = FIXED. [163](ftt-diagnosi-refactor-grading-163.md) · [melo](ftt-melo-linear0-soroll-poda.md)
- Paritat fitting↔grading i golden path: [diagnosi](ftt-paritat-fitting-grading.md) · [6 peces](ftt-impl-paritat-grading.md) · [silenci](ftt-silenci-grading-done.md) · [5 capes](ftt-5capes-proces.md)

## 🔑 FETS VIGENTS · motor de patrons, fitxa i editor

- **AMELIA = PolyPattern** (no Tuka). Trams naturals: llindar 22°, i **mana la màscara de PIQUETS**. [s0](ftt-motor-patrons-s0.md) · [trams](ftt-trams-naturals.md) · [W2](ftt-taller-patro-w2.md) · [QA A](ftt-qa-taller-a-done.md)
- **`patternfile_xor_model_item` ja admet un `PatternFile` penjat d'un GTI** en lloc d'un Model: mitja infraestructura del patró de catàleg ja existeix, sense migració. [desplegat](ftt-fil-desplegat-tancat.md)
- **Banc S45: model pk=1383 VIU** a `fhort` (confirmat 25/08) — 🚩 **ja no és el de la sembra** (regla D editada + v7) i **cap fitxer seu és al disc**. [sembra-837](ftt-sembra-837-banc-s45.md) · [fix-a](ftt-fix-a-font-unica-regla.md) · [h-bis](ftt-hbis-columnes-identitat-fitxa.md)
- **La fitxa JA reparteix per peça** — falta la PÀGINA. [multipeça](ftt-fitxa-multipeca-ja-construida.md)
- **La fitxa NO és reportlab** (Konva + pdf-lib); **mai A3: s'imprimeix en A4**; Chrome no sap numerar pàgines (x/N → paginar en JS). [motor-fitxa](ftt-fitxa-tecnica-motor.md) · [q8](ftt-q8-taules-fitxa-per-peca.md) · [q9](ftt-s42-q9-full-thead-i-geometria.md)
- **Import**: la base del parser és l'etiqueta del DOCUMENT; una talla no-base fora del sistema **es DESCARTA**; «l'import esborra» era FALS. [multipeça](ftt-sprint-import-multipeca-f1f6.md) · [guard](ftt-import-talla-nobase-descarta.md) · [no-esborra](ftt-import-no-esborra-i-nom-canonic.md)
- Editor `.ftt`: mapa real i 7 fases · un `.ftt` és un ZIP i `MEDIA_ROOT+name` **no** és on Django llegeix (usa `obj.fitxer.path`); `checksum` no compara contingut. [editor](ftt-editor-estat-faseb.md) · [j-bis](ftt-jbis-ftt-al-disc-i-transicio-guardada.md)

## 🔑 FETS VIGENTS · federació, comercial i altres projectes

- **Federació**: el Model **no és particionable**; `TenantLink` + origen EXTERN; destí poblat → `--additive`. 🚩 [camí crític](ftt-federacio-v2-cami-critic.md) *(la xifra «962 models LOS a `fhort`» no quadra amb el cens del 25/08 — a verificar)* · [P1P2](ftt-federacio-v2-p1p2-done.md) · [bootstrap](ftt-bootstrap-desti-poblat.md) · [login únic](ftt-login-unic-f1f2f3.md)
- **Comercial**: commerce B1→B4c, **B5 pendent** · fitxa Empresa + logo cairosvg (2 accions de deploy) · Stripe F1 · alta mínima F2 · dashboard/gantt · planning. [bchain](ftt-comercial-modul-bchain.md) · [empresa](ftt-empresa-fiscal-logo-done.md) · [planning](ftt-planning-complet-done.md)
- **L'estat del model és del MODEL** (gate de mesures) · `tipologia` discrimina la UI · LLEI C5 al gate GRS. [gate](ftt-gate-mesures-pom-task-done.md) · [marca](ftt-self-customer-marca.md) · [grs](ftt-gate-grs-item-2026-07-23.md)
- **Web/altres**: `prefers-reduced-motion` es menjava 7 de 8 imatges · l'overlay de cotes MANA · webiafy (Astro SSR híbrid) · 🚩 `frappe-cleanup-fhort` pendent DROP BD. [journey](ftt-web-journey-motor.md) · [landing](ftt-web-landing-portes-tecnic.md) · [webiafy](webiafy-project.md) · [frappe](frappe-cleanup-fhort.md)

---

> **Cròniques de sessió:** fora d'aquest índex a posta. Cada tema té el seu fitxer a
> `memory/` i el relat de la feina viu a `ESTAT_PROJECTE.md` / `DECISIONS.md`.
> Si una sessió deixa una LLEI o un FET, va a la secció que li toca **en una línia**.
