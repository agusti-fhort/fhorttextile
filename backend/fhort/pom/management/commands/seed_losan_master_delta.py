"""PEÇA 2 del master_delta — SEMBRA (CREATE) de les 4 cel·les noves de grading LOS.

Font ÚNICA: `grading_rules_master_delta_v1.json` (transcrit verbatim). NOMÉS CREATE: crea 4
GradingRuleSet + 90 GradingRule + 4 SizingProfile (JERSEY_TOPS). NO toca cap ruleset/regla existent.

Patró de `seed_losan_rules` adaptat a CREATE, amb les decisions d'Agus (19/07):
  · Resolutor de POM: àlies LOS (CustomerPOMAlias.client_code) → codi directe → variants() de
    puntuació (precedent LOS). GUARDA D'AMBIGÜITAT: si variants() dona >1 candidat → NO resoldre,
    marcar AMBIGU (mai triar el primer).
  · talla_base = SizeDefinition(size_system, etiqueta del JSON). talla_break_label del JSON;
    talla_break_pos = NULL. logica = LINEAR. increment (flat) = increment_base (convenció 104).
  · Ruleset (vara v3): origen CLIENT_RUN + customer LOS + size_system + targets M2M + construction +
    fit_type + garment_group (abast per grup) + garment_type_item = NULL.
  · 1 SizingProfile per ruleset: customer LOS, garment_type = JERSEY_TOPS, is_default=False (sense
    això el ruleset és invisible al suggeridor).
  · Idempotent per clau natural: (size_system, nom) ruleset · (rule_set, pom) regla ·
    (target, garment_type, construction, fit_type, size_system, version) profile.
  · El dry-run imprimeix la TAULA D'AUDITORIA dels 90: codi JSON → POM (codi+nom) → via.

INVARIANT: si algun codi no resol o és ambigu → NO es crea la regla i el resum ho marca; amb
qualsevol no-resolt/ambigu el compte no dona 90/90 → cal ATURAR (no sembrar cel·les incompletes).

    python manage.py seed_losan_master_delta                # DRY-RUN
    python manage.py seed_losan_master_delta --no-dry-run   # escriu
"""
import json
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django_tenants.utils import schema_context

from fhort.pom.models import (GradingRuleSet, GradingRule, POMMaster, SizeSystem, SizeDefinition,
                              FitType, ConstructionType, Target, GarmentGroup, GarmentType,
                              SizingProfile, CustomerPOMAlias)
from fhort.tasks.models import Customer
from fhort.pom.seed_data import consolidate_pom_los as CFG
from fhort.pom.management.commands.consolidate_pom_catalog import variants

JSON_PATH = Path(__file__).resolve().parents[2] / 'seed_data' / 'grading_rules_master_delta_v1.json'
JERSEY_TOPS_NOM = 'Jersey Tops'   # garment_type del profile (decisió A · dominància al manifest)


def dec(v):
    return Decimal(str(v))


class Command(BaseCommand):
    help = 'Sembra (CREATE) les 4 cel·les noves de grading LOS del master_delta.'

    def add_arguments(self, parser):
        parser.add_argument('--no-dry-run', action='store_true')
        parser.add_argument('--schema', default=CFG.TENANT)

    def handle(self, *args, **opts):
        dry = not opts['no_dry_run']
        head = 'DRY-RUN (cap escriptura)' if dry else 'ESCRIVINT'
        self.stdout.write(self.style.WARNING(f'=== seed_losan_master_delta · {head} ==='))

        data = json.loads(JSON_PATH.read_text(encoding='utf-8'))
        self.audit = []        # (cel·la, codi_json, pom_codi, pom_nom, via)
        self.unresolved = []   # (cel·la, codi_json)
        self.inactiu_only = [] # (cel·la, codi_json, detall) — únic candidat inactiu (catàleg brut)
        self.ambiguous = []    # (cel·la, codi_json, detall)
        self.obscured = []     # (cel·la, codi_json, winner, [candidats enfosquits])
        self.summary = []      # (nom, n_rs_created, n_rules_created, n_prof_created)

        with schema_context(opts['schema']), transaction.atomic():
            los = Customer.objects.filter(codi=CFG.CUSTOMER_CODI).first()
            if not los:
                raise CommandError('Customer LOS no existeix.')
            jersey = GarmentType.objects.filter(nom_client__iexact=JERSEY_TOPS_NOM)
            if jersey.count() != 1:
                raise CommandError(f'GarmentType {JERSEY_TOPS_NOM!r} ambigu/inexistent (n={jersey.count()}).')
            jersey = jersey.first()
            self.los, self.jersey = los, jersey

            for rs in data['rule_sets']:
                self._seed_rule_set(rs, dry)

            if dry:
                transaction.set_rollback(True)

        self._report(dry)

    def _lvl_candidates(self, code, kind):
        """Candidats d'un NIVELL. kind ∈ {alias-ex, alias-var, codi-ex, codi-var}. Retorna
        (actius, inactius) com a llistes úniques per ordre (separa actiu/inactiu per a la LLEI b)."""
        act, ina = [], []
        codes = [code] if kind.endswith('-ex') else variants(code)
        for c in codes:
            if kind.startswith('alias'):
                poms = [x.pom for x in CustomerPOMAlias.objects.filter(
                    customer=self.los, client_code=c, pom__isnull=False).select_related('pom')]
            else:
                poms = list(POMMaster.objects.filter(codi_client=c))
            for p in poms:
                if p not in act and p not in ina:
                    (act if p.actiu else ina).append(p)
        return act, ina

    def _resolve_pom(self, code):
        """LLEI DE RESOLUCIÓ DE POM (Agus 19/07):
          (a) ordre: àlies-exacte → àlies-variant → codi-exacte → codi-variant.
          (b) actiu=True a TOTES; si l'únic candidat és inactiu → NO resoldre i REPORTAR (catàleg brut).
          (c) guarda d'ambigüitat PER NIVELL (>1 actiu dins d'un nivell → AMBIGU).
          (d) candidats ENFOSQUITS: si un nivell inferior hauria casat amb un POM ACTIU diferent del
              guanyador → informar-ho (no bloqueja). També s'anoten els inactius trobats.
        Retorna (pom|None, via, obscured[list str], detall|None)."""
        order = [('àlies-exacte', 'alias-ex'), ('àlies-variant', 'alias-var'),
                 ('codi-exacte', 'codi-ex'), ('codi-variant', 'codi-var')]
        levels = [(name, self._lvl_candidates(code, kind)) for name, kind in order]
        winner = via = None
        obscured, inactives = [], []
        for name, (act, ina) in levels:
            if ina:
                inactives.append(f'{name}=[{",".join(p.codi_client for p in ina)}]')
            if winner is None:
                if len(act) > 1:
                    return (None, 'AMBIGU', [], f'{name}: {[p.codi_client for p in act]}')
                if len(act) == 1:
                    winner, via = act[0], name
            else:
                for p in act:
                    if p.id != winner.id:
                        obscured.append(f'{name}:{p.codi_client}/{p.nom_client}')
        if winner is None:
            return ((None, 'INACTIU_ONLY', [], '; '.join(inactives)) if inactives
                    else (None, 'NO_RESOLT', [], None))
        if inactives:
            obscured += [f'inactiu@{s}' for s in inactives]
        return (winner, via, obscured, None)

    def _seed_rule_set(self, spec, dry):
        nom = spec['nom']
        ss = SizeSystem.objects.filter(codi=spec['size_system_codi']).first()
        if not ss:
            raise CommandError(f'SizeSystem {spec["size_system_codi"]!r} no existeix ({nom}).')
        base = SizeDefinition.objects.filter(size_system=ss, etiqueta=spec['talla_base']).first()
        if not base:
            raise CommandError(f'talla_base {spec["talla_base"]!r} no existeix a {ss.codi} ({nom}).')
        construction = ConstructionType.objects.filter(codi=spec['construction']).first()
        fit = FitType.objects.filter(codi=spec['fit_type']).first()
        grp = GarmentGroup.objects.filter(codi=spec['garment_group']).first()
        if not (construction and fit and grp):
            raise CommandError(f'construction/fit/grup no resolts ({nom}).')
        targets = [Target.objects.filter(codi=c).first() for c in spec['targets']]
        if not all(targets):
            raise CommandError(f'algun target no resolt ({nom}): {spec["targets"]}.')
        break_label = spec.get('talla_break_label')

        # ── Ruleset (clau natural size_system+nom) ──
        rs, rs_created = GradingRuleSet.objects.get_or_create(
            size_system=ss, nom=nom,
            defaults={'origen': GradingRuleSet.ORIGEN_CLIENT_RUN, 'customer': self.los,
                      'construction': construction, 'fit_type': fit, 'garment_group': grp,
                      'garment_type_item': None, 'target': targets[0], 'actiu': True})
        rs.targets.set(targets)

        # ── Regles ──
        nrules = 0
        for r in spec['regles']:
            code = r['codi_client']
            pom, via, obscured, detail = self._resolve_pom(code)
            if obscured:
                self.obscured.append((nom, code, pom.codi_client if pom else '—', obscured))
            if pom is None:
                if via == 'AMBIGU':
                    self.ambiguous.append((nom, code, detail))
                elif via == 'INACTIU_ONLY':
                    self.inactiu_only.append((nom, code, detail))
                else:
                    self.unresolved.append((nom, code))
                continue
            self.audit.append((nom, code, pom.codi_client, pom.nom_client, via))
            has_break = r.get('increment_break') is not None
            ib = dec(r['increment_base'])
            _, created = GradingRule.objects.get_or_create(
                rule_set=rs, pom=pom,
                defaults={'talla_base': base, 'logica': GradingRule.LOGICA_LINEAR,
                          'increment': ib, 'increment_base': ib,
                          'increment_break': dec(r['increment_break']) if has_break else None,
                          'talla_break_label': break_label if has_break else None,
                          'talla_break_pos': None, 'valors_step': None, 'actiu': True})
            nrules += int(created)

        # ── SizingProfile (perquè el suggeridor el vegi) ──
        _, prof_created = SizingProfile.objects.get_or_create(
            target=targets[0], garment_type=self.jersey, construction=construction,
            fit_type=fit, size_system=ss, version=1,
            defaults={'grading_rule_set': rs, 'customer': self.los, 'is_default': False})

        self.summary.append((nom, int(rs_created), nrules, int(prof_created)))

    def _report(self, dry):
        self.stdout.write('\n── TAULA D\'AUDITORIA (codi JSON → POM → via) ──')
        cur = None
        for cel, code, pcodi, pnom, via in self.audit:
            if cel != cur:
                self.stdout.write(f'\n  [{cel}]'); cur = cel
            self.stdout.write(f'    {code:6} → {pcodi:12} \'{pnom}\'  [{via}]')

        self.stdout.write('\n── RESUM PER CEL·LA ──')
        trs = trr = tpr = 0
        for nom, nrs, nr, npr in self.summary:
            trs += nrs; trr += nr; tpr += npr
            self.stdout.write(f'  {nom}: ruleset {"CREAT" if nrs else "ja existia"} · '
                              f'{nr} regles creades · profile {"CREAT" if npr else "ja existia"}')
        self.stdout.write(f'\n  TOTALS: rulesets creats={trs} · regles creades={trr} · profiles creats={tpr}')
        self.stdout.write(f'  codis resolts (a la taula)={len(self.audit)} · NO resolts={len(self.unresolved)} · '
                          f'INACTIU_ONLY={len(self.inactiu_only)} · AMBIGUS={len(self.ambiguous)}')
        for nom, code in self.unresolved:
            self.stdout.write(self.style.ERROR(f'    NO RESOLT: {nom} · {code}'))
        for nom, code, det in self.inactiu_only:
            self.stdout.write(self.style.ERROR(f'    INACTIU_ONLY (catàleg brut): {nom} · {code} → {det}'))
        for nom, code, det in self.ambiguous:
            self.stdout.write(self.style.ERROR(f'    AMBIGU: {nom} · {code} → {det}'))

        self.stdout.write(f'\n── CANDIDATS ENFOSQUITS (informatiu, la precedència ha amagat aquests) ──')
        if not self.obscured:
            self.stdout.write('  (cap)')
        for nom, code, winner, cands in self.obscured:
            self.stdout.write(f'  {nom} · {code} (→ {winner}) enfosqueix: {cands}')

        ok = (len(self.audit) == 90 and not self.unresolved
              and not self.ambiguous and not self.inactiu_only)
        self.stdout.write(self.style.SUCCESS('\n  INVARIANT 90/90 codis resolts: OK ✅')
                          if ok else self.style.ERROR('\n  ⚠️ INVARIANT NO complert (≠90 o no-resolts/ambigus) → ATURAR'))
        self.stdout.write(self.style.SUCCESS(f'=== FET ({head_of(dry)}) ==='))


def head_of(dry):
    return 'DRY-RUN' if dry else 'ESCRIT'
