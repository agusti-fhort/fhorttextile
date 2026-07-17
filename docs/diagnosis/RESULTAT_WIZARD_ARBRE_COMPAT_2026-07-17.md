# RESULTAT — Wizard complet · Arbre únic · Compatibilitat de models existents

Data: **2026-07-17** · staging `dev`, tenant `fhort` · **SENSE push, SENSE deploy** (els fa l'Agus).
Diagnosi germana: `DIAGNOSI_WIZARD_ARBRE_COMPAT_2026-07-17.md`. Backup PRE-WIZ:
`ops/backups/PRE-WIZ_20260717_prewiz.dump` (pg_dump -Fc, capçalera verificada amb pg_restore v18).

Mètode: Patró A (diagnosi read-only) → GATE automàtic (verd) → Patró B (implementació, regla del verd,
commit per peça). **9 commits** (8 de codi + 1 de docs), tots amb `manage.py check` + `npm run build` nets. Motor
`generate_graded_specs` **INTOCAT**. Cap migració de model (el contracte ja era complet).

---

## Commits (per fase)

| # | Hash | Peça |
|---|---|---|
| B.1a | `d7e7c44` | matcher ESTRICTE (`matchingRuleSetsStrict`/`availableFitsStrict`) + props `strict`/`sizeSystemId` a RuleSetPicker |
| B.1b | `fbb04d6` | `garment_type_grup` al serializer + buidatge explícit de graduació (edició) |
| B.1c | `6f4107f` | pas 4 «Graduació» al ModelWizard (creació + edició) + i18n |
| C.3 | `12a2f83` | RuleSetCard → LECTURA enriquida + enllaç «Canviar graduació» (wizard pas 4) |
| C.2 | `c657e25` | font única de grups al frontend + `garment_group_codi` al serializer |
| C.1 | `26a6f83` | selector de GRUP (pills) a Garment Types + cerca que salta nivells |
| D.1 | `1e32ad1` | `backfill_model_taxonomy` (garment_group derivat, dry-run per defecte) |
| D.2 | `5979b15` | `flag_incomplete_models` (watchpoints de compleció, dry-run per defecte) |

*(+ 1 commit de docs `e8676da` — diagnosi + aquest resultat.)*

---

## Decisions clau (Patró C — a validar per l'Agus)

1. **`garment_group` és DERIVABLE i segur** (denormalització que el wizard ja fa) → el backfill l'omple.
   **`grading_rule_set` NO és derivable** de forma segura: `Model.grading_rule_set` i
   `GarmentTypeItem.grading_rule_set` són punters DESACOBLATS a posta (assignar-lo materialitzaria
   regles residents = **inventar graduació** → prohibit per D.1b). Els 34 models sense graduació es
   queden així (estat vàlid «sense graduació») i es marquen amb watchpoint per completar-los a mà.
2. **El fit NO s'escriu a `Model.fit_type`** des del wizard: el mapatge codi→choice és lossy
   (`FLARED`/`TAPERED`… no tenen choice; risc de 500). El fit viu al ruleset triat, que és qui el porta.
   El canvi Regular→Slim es realitza canviant el `grading_rule_set` (re-materialització).
3. **El canvi de graduació ja no és a un clic**: RuleSetCard passa a lectura; el canvi viu al wizard
   (enllaç → pas 4), explícit i re-materialitzador.
4. **Cens de grups (6 vs 7)**: la font de veritat és el model `GarmentGroup` (endpoint). Les llistes
   hardcoded del frontend eren el desajust; s'ha unificat a UN vocabulari. **La neteja de la TAULA
   `GarmentGroup`** (11 files live, 5 sense ús: ACCESSORIES, KNITWEAR, DRESSES-FULL, TOPS-KNIT,
   TOPS-WOVEN) és decisió de DADES d'Agus, no de codi (runbook, pas opcional).

---

## Verificació (18/18 verd · endpoints reals + rollback, cap escriptura persistida)

- **D.3 robustesa**: `ModelDetailSerializer` sobre **43 models** i `GradingRuleSetSerializer` sobre
  **26 rulesets** → **0 errors**. Model buidat (garment_group + grading NULL) serialitza amb
  `garment_group_codi=None` (tolera el buit, no peta).
- **E.1**: strict-match Brownie (WOMAN/WOVEN/REGULAR/TOPS/ALPHA_EU_W) → **exactament `[115]`**; cap
  dels **23 rulesets amb eix NULL** cola com a comodí. Create-wizard amb grs=115 → **201**, model neix
  amb `grading_rule_set=115` + **34 regles residents** + `garment_group=TOPS` derivat.
- **E.2**: «Sense graduació» → **201 net**, `grading_rule_set=None`, 0 residents, garment_group derivat igual.
- **E.3**: canvi de graduació via update-step2 (115→75) → **re-sembra** (61 residents), **talla base INTACTA**.
- **E.4** (Garment Types grup-pills) i **E.5** (fitxa de tots els models) → build verd + D.3 sense 500.
- **E.6** no-regressió: ruleset 115 (contenidor client) intacte (gti=5, 34 regles, CLIENT_RUN).
- Post-verificació: **43 models, cap residual E2E**, cens intacte (35 garment_group NULL, 34 grading NULL).

---

## CHECKLIST VISUAL per a l'Agus (prova a staging abans del push)

- [ ] **Crear model nou** pel wizard: pas 1-3 com sempre, i ara apareix el **pas 4 «Graduació»**.
      Tria una peça WOMAN / teixit pla / talles ALPHA_EU_W, al pas 4 tria fit **Regular** → ha
      d'aparèixer **NOMÉS** el joc de regles Brownie (115), cap comodí. Crear → la fitxa mostra la
      graduació.
- [ ] Al pas 4, marca **«Sense graduació»** → pots crear igualment (201). El model queda sense
      graduació i amb l'avís de compleció.
- [ ] **Editar** un model existent pel wizard → el pas 4 mostra la graduació vigent; canvia-la (p.ex.
      a un altre fit) → es re-sembra i la **talla base no es mou**.
- [ ] **Fitxa del model** (tab Resum): la targeta de graduació ara és **LECTURA** (nom, target,
      construcció, fit, sistema, nº regles, provinença) amb botó **«Canviar graduació»** que obre el
      wizard al pas 4. Ja **no** hi ha canvi a un sol clic.
- [ ] **Garment Types**: el filtre de grup ara són **pills** (com el selector del wizard); escriu al
      cercador i veuràs que **salta nivells** (busca a tots els grups).
- [ ] **Models antics**: obre'n uns quants (import, wizard, clon) → cap pantalla trencada; els que no
      tenen graduació mostren «— pendent» i tenen l'avís de compleció.

---

## RUNBOOK DE DEPLOY (l'executa l'Agus; cap pas d'agent a PROD)

Els passos **5-7 són POST-deploy del codi i PRE-obertura a l'equip.**

1. **Backup PROD** (`pg_dump -Fc`) a `/srv/fhort-prod-backups/`; verificar la capçalera amb
   `/usr/lib/postgresql/18/bin/pg_restore -l <dump>`.
2. **fetch/merge** de `dev` → PROD + verificacions habituals (revisar la cadena amb `git show <hash>`).
3. **Migracions**: en aquest sprint **NO n'hi ha** (contracte de model complet, tot additiu). Si
   `migrate_schemas` es corre igualment, **auditar columnes directament a la BD** (no `--schema`).
4. **Build front** (`npm run build` a `frontend/`) + **restart** gunicorn/servei.
5. **`backfill_model_taxonomy`** — primer **dry-run** (per defecte), revisar la taula i l'AUDIT
   (garment_group NULL abans/després), després **`--commit`**:
   ```
   python manage.py backfill_model_taxonomy --schema fhort            # dry-run: revisar
   python manage.py backfill_model_taxonomy --schema fhort --commit   # escriure
   ```
   Auditar a la BD: `SELECT count(*) FROM models_app_model WHERE garment_group_id IS NULL;` (ha de baixar).
6. **`flag_incomplete_models`** — igual, dry-run → `--commit`:
   ```
   python manage.py flag_incomplete_models --schema fhort             # dry-run: revisar
   python manage.py flag_incomplete_models --schema fhort --commit    # escriure (watchpoints)
   ```
7. **Verificació**: obrir una mostra de models reals (fitxa + wizard edició) → **cap error 500**,
   els sense graduació mostren «— pendent» i tenen **watchpoint visible**; els backfillats mostren el grup.
8. *(OPCIONAL, decisió de DADES)* Netejar la taula `GarmentGroup` (desactivar els 5 grups sense ús:
   ACCESSORIES, KNITWEAR, DRESSES-FULL, TOPS-KNIT, TOPS-WOVEN) perquè l'endpoint sigui la font neta.

> `backfill_model_taxonomy` i `flag_incomplete_models` són **idempotents**: re-executar-los no
> duplica res (models ja backfillats es salten; watchpoints oberts no es dupliquen).
