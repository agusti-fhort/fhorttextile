"""Transcriu la foto READ-ONLY del model 837 VESTIT (TRV-SS27-0001) de PROD a staging.

    python manage.py sembra_model_837                 # DRY-RUN (per defecte): no escriu res
    python manage.py sembra_model_837 --apply         # escriu (només amb OK explícit)

PROPÒSIT: banc de proves dels bugs S45. La sembra **TRANSCRIU**: no neteja, no
normalitza i no recalcula. Les incoherències de la foto són l'evidència i han
d'arribar VIVES a staging:

  · regla POM «D» amb increment=2.00 i increment_base/increment_break=0.50
  · 6 GradingVersions (v1-v5 amb pas 3.0 al D, v6 amb 0.5) i la vigent és la v6
  · PieceFitting #15 penjat de la v2, no de la vigent
  · joc de regles BROWNIE (BRW-CATALEG-v3) sobre un model del client TRV
  · SizeFitting en estat «TallesGenerades» amb base_tancada=False

Per això NO es crida MAI `generate_graded_specs`: els 615 GradedSpec es copien
tal com són. Cridar el motor els regeneraria coherents i mataria el banc.

CLAUS NATURALS (mai els pks de PROD). Tota FK es re-resol per la seva clau
natural al tenant destí i el mapa pk_PROD→pk_staging va al report. Un POMMaster
es resol per `codi_client`, però —LLEI S44— **match per codi no és match de
significat**: es compara el contingut (nom, categoria, pom_global) contra la
foto i qualsevol divergència va a `no_resolts`, que el dry-run reporta i que
bloqueja l'--apply si no s'accepta explícitament amb --accepta-discrepancies-pom.

SIGNALS (models_app/signals.py). La sembra entra SOTA els signals o el recompte
no quadraria:
  · `sync_size_fitting` crea un SizeFitting sol en crear el Model → NO en creem
    un segon: s'ADOPTA el que fa el signal i s'hi transcriuen els camps de la
    foto via .update() (per això el recompte segueix sent 1, no 2).
  · `log_measurement_change` escriuria un MeasurementChangeLog per cada
    BaseMeasurement creada → les 21 mesures entren per `bulk_create`, que no
    dispara post_save, i els 21 logs es transcriuen literals de la foto.
  · `update_last_activity` i tots els `auto_now`/`auto_now_add` sobreescriuen
    els timestamps → es restauren amb QuerySet.update(), que no dispara signals
    ni crida Field.pre_save.
  · `recompute_import_watchpoint` i `sync_encarrec_a_l_estudi` són no-ops aquí
    (0 Watchpoints oberts, studio_assignat='').

IDEMPOTÈNCIA: la clau és `codi_intern`. Si el model ja existeix, el command no
crea res i ho diu (2a passada = 0 creacions).
"""
import hashlib
import json
import os
from collections import OrderedDict

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django_tenants.utils import schema_context

#: Recompte del cens de PROD. Són GUARDES: si el que la sembra pensa crear no hi
#: quadra exacte, la transacció avorta. Un banc de proves incomplet és pitjor que
#: cap banc, perquè els bugs es busquen sobre el que hi falta.
GUARDES = OrderedDict([
    ('Model', 1),
    ('BaseMeasurement', 21),
    ('ModelGradingRule', 142),
    ('MeasurementChangeLog', 21),
    ('SizeFitting', 1),
    ('GradingVersion', 6),
    ('GradedSpec', 615),
    ('FittingSession', 2),
    ('PieceFitting', 2),
    ('PieceFittingLine', 200),
    ('ModelTask', 3),
    ('TimerEntrada', 8),
    ('ModelFitxer', 8),
    ('Watchpoint', 0),
])

JSON_DEFAULT = '/var/www/ftt-staging/docs/ordres/MODEL_837_EXPORT.json'


class Aturada(CommandError):
    """El dry-run ha trobat una cosa que demana decisió d'humà."""


class Command(BaseCommand):
    help = "Transcriu la foto de PROD del model 837 (TRV-SS27-0001) a staging. Dry-run per defecte."

    def add_arguments(self, p):
        p.add_argument('--schema', default='fhort')
        p.add_argument('--json', default=JSON_DEFAULT)
        p.add_argument('--apply', action='store_true',
                       help="Escriu de debò. Sense això el command és READ-ONLY.")
        p.add_argument('--accepta-discrepancies-pom', action='store_true',
                       help="Reutilitza els POMMaster resolts per codi encara que el "
                            "contingut divergeixi de la foto. Cal OK explícit.")
        p.add_argument('--accepta-ruleset-divergent', action='store_true',
                       help="Reutilitza BRW-CATALEG-v3 de staging encara que el hash "
                            "canònic no coincideixi amb el de la foto.")
        p.add_argument('--crea-entorn-absent', action='store_true',
                       help="Crea el Customer i els actors de la foto que no existeixin a "
                            "staging. Els actors es creen NOUS (mai es remapen a un usuari "
                            "existent): l'actoria de la foto és evidència forense.")
        p.add_argument('--report', default='', help="Camí del report .md a escriure.")

    def handle(self, *a, **o):
        with open(o['json']) as fh:
            self.D = json.load(fh)
        self.o = o
        self.linies = []
        self.aturades = []
        self.creats_per_la_sembra = []
        with schema_context(o['schema']):
            return self._run()

    # ── sortida ──────────────────────────────────────────────────────────────
    def diu(self, txt='', style=None):
        self.linies.append(txt)
        self.stdout.write(style(txt) if style else txt)

    def atura(self, motiu):
        """Una aturada NO és un error de programa: és una decisió que li toca a Agus.

        En --apply avorta a l'acte (mai s'escriu amb una pregunta oberta). En dry-run
        s'acumula i la diagnosi CONTINUA: qui ha de decidir vol veure tots els forats
        d'una sola passada, no descobrir-los d'un en un.
        """
        self.aturades.append(motiu)
        if self.o['apply']:
            raise Aturada(motiu)

    def titol(self, txt):
        self.diu()
        self.diu('── %s ' % txt + '─' * max(0, 74 - len(txt)))

    # ── el cos ───────────────────────────────────────────────────────────────
    def _run(self):
        from fhort.models_app.models import Model

        codi = self.D['model']['codi_intern']
        self.diu(self.style.MIGRATE_HEADING(
            "SEMBRA 837 · %s → schema %s · mode %s" % (
                codi, self.o['schema'], 'APPLY' if self.o['apply'] else 'DRY-RUN')))

        ja = Model.objects.filter(codi_intern=codi).first()
        if ja:
            self.diu(self.style.WARNING(
                "IDEMPOTÈNCIA: el model %s ja existeix a staging (pk=%s). 0 creacions."
                % (codi, ja.pk)))
            self._escriu_report()
            return

        # L'entorn que es CREA (customer, actors) ha de caure amb el mateix rollback que la
        # transcripció: si una guarda de recompte peta, no poden quedar-hi actors orfes d'un
        # model que no existeix. Per això l'atomic exterior embolcalla les dues fases —
        # l'`@transaction.atomic` de `_sembra` hi entra com a savepoint anidat.
        with transaction.atomic():
            entorn = self._resol_entorn()
            poms = self._resol_poms()
            self._verifica_ruleset()
            self._pla()

            if self.o['apply']:
                self._sembra(entorn, poms)
                self._escriu_report()
                return

        if not self.o['apply']:
            self.titol('VEREDICTE')
            self.diu("  DRY-RUN: no s'ha escrit res a la BD ni al disc.")
            if self.aturades:
                self.diu(self.style.ERROR(
                    "  L'--apply està BLOQUEJAT per %d motiu(s):" % len(self.aturades)))
                for i, x in enumerate(self.aturades, 1):
                    self.diu(self.style.ERROR("    %d. %s" % (i, x)))
            else:
                self.diu(self.style.SUCCESS(
                    "  Cap bloqueig: la sembra pot córrer amb --apply."))
            self._escriu_report()
            return

    # ── 1. entorn per clau natural ───────────────────────────────────────────
    def _resol_entorn(self):
        from fhort.pom.models import GradingRuleSet, GarmentType, GarmentGroup, SizeSystem
        from fhort.tasks.models import GarmentTypeItem, Customer, TaskType
        from fhort.accounts.models import UserProfile

        self.titol('ENTORN (per clau natural; només es crea amb --crea-entorn-absent)')
        e, m, absents = self.D['entorn'], self.D['model'], []

        def resol(etiqueta, qs, clau, obligatori=True):
            fila = qs.first()
            if fila:
                self.diu("  OK        %-22s %-24s → pk=%s" % (etiqueta, clau, fila.pk))
            else:
                self.diu(self.style.ERROR("  ABSENT    %-22s %-24s → no existeix a staging"
                                          % (etiqueta, clau)))
                if obligatori:
                    absents.append('%s (%s)' % (etiqueta, clau))
            return fila

        ent = {}
        ent['garment_type'] = resol('GarmentType', GarmentType.objects.filter(
            codi_client=e['garment_type']['codi_client']), e['garment_type']['codi_client'])
        ent['garment_type_item'] = resol('GarmentTypeItem', GarmentTypeItem.objects.filter(
            code=e['garment_type_item']['code']), e['garment_type_item']['code'])
        ent['garment_group'] = resol('GarmentGroup', GarmentGroup.objects.filter(
            codi=e['garment_group']['codi']), e['garment_group']['codi'])
        ent['size_system'] = resol('SizeSystem', SizeSystem.objects.filter(
            codi=e['size_system']['codi']), e['size_system']['codi'])
        ent['grading_rule_set'] = resol('GradingRuleSet', GradingRuleSet.objects.filter(
            codi_sistema=self.D['grading_rule_set_snapshot']['codi_sistema']),
            self.D['grading_rule_set_snapshot']['codi_sistema'])
        # El customer del MODEL (TRV) — no el del joc de regles (BRW).
        ent['customer'] = resol('Customer', Customer.objects.filter(
            codi=e['customer']['codi']), e['customer']['codi'], obligatori=False)
        if ent['customer'] is None:
            ent['customer'] = self._crea_customer(e['customer'], absents)

        # Els actors: la clau natural d'un UserProfile és user.username. Un pk que
        # coincideixi entre PROD i staging NO és el mateix actor.
        ent['users'] = {}
        for uname in sorted({u for u in self._usernames_referenciats() if u}):
            up = UserProfile.objects.filter(user__username=uname).first()
            ent['users'][uname] = up
            if up:
                self.diu("  OK        %-22s %-24s → pk=%s" % ('UserProfile', uname, up.pk))
            else:
                self.diu(self.style.ERROR("  ABSENT    %-22s %-24s → cap username així"
                                          % ('UserProfile', uname)))
                ent['users'][uname] = self._crea_actor(uname, absents)

        ent['task_types'] = {}
        for t in self.D['model_tasks']:
            code = t['_task_type']['code']
            tt = TaskType.objects.filter(code=code).first()
            ent['task_types'][code] = tt
            if tt:
                self.diu("  OK        %-22s %-24s → pk=%s%s" % (
                    'TaskType', code, tt.pk,
                    '' if tt.pk == t['task_type_id'] else '  (PROD pk=%s)' % t['task_type_id']))
            else:
                self.diu(self.style.ERROR("  ABSENT    %-22s %-24s" % ('TaskType', code)))
                absents.append('TaskType (%s)' % code)

        # SizeDefinitions: les etiquetes han d'existir totes al sistema de talles.
        if ent['size_system']:
            from fhort.pom.models import SizeDefinition
            teniu = set(SizeDefinition.objects.filter(
                size_system=ent['size_system']).values_list('etiqueta', flat=True))
            falten = [s['etiqueta'] for s in e['size_definitions'] if s['etiqueta'] not in teniu]
            if falten:
                self.diu(self.style.ERROR("  ABSENT    SizeDefinition         %s" % falten))
                absents.append('SizeDefinition %s' % falten)
            else:
                self.diu("  OK        %-22s %-24s" % (
                    'SizeDefinition ×%d' % len(e['size_definitions']),
                    '·'.join(s['etiqueta'] for s in e['size_definitions'])))

        if absents:
            self.diu()
            self.diu(self.style.ERROR(
                "ATURADA · %d dependència(es) d'entorn ABSENT(s) a staging:" % len(absents)))
            for x in absents:
                self.diu(self.style.ERROR("    · " + x))
            self.diu(self.style.ERROR(
                "La sembra NO crea entorn (regla 3 de l'ordre): cal decisió d'Agus."))
            self.atura("entorn incomplet: %s" % ', '.join(absents))
        return ent

    def _crea_customer(self, foto, absents):
        """El Customer del model, amb les dades de la foto. Només amb --crea-entorn-absent."""
        from fhort.tasks.models import Customer
        if not self.o['crea_entorn_absent']:
            absents.append('Customer (%s)' % foto['codi'])
            return None
        if not self.o['apply']:
            self.diu(self.style.WARNING("  CREARÀ    %-22s %-24s → Customer nou (codi/nom/active "
                                        "de la foto)" % ('Customer', foto['codi'])))
            self.creats_per_la_sembra.append('Customer %s (%s)' % (foto['codi'], foto['nom']))
            return None
        c = Customer.objects.create(codi=foto['codi'], nom=foto['nom'],
                                    active=foto['active'], is_self=foto['is_self'],
                                    codi_global=foto['codi_global'])
        self.diu(self.style.SUCCESS("  CREAT     %-22s %-24s → pk=%s"
                                    % ('Customer', foto['codi'], c.pk)))
        self.creats_per_la_sembra.append('Customer %s (%s) → pk=%s' % (foto['codi'], foto['nom'], c.pk))
        return c

    def _crea_actor(self, uname, absents):
        """Un actor de la foto que no existeix a staging.

        Es crea NOU, mai es remapa a un usuari existent: qui va obrir una sessió o signar un
        PieceFitting és evidència forense del banc, i un remapatge silenciós la falsejaria
        (a PROD `fhort` és el pk=1 i a staging el pk=1 és un altre actor — el pk no és
        identitat). Contrasenya inutilitzable: aquests comptes no han de poder entrar.
        """
        from django.contrib.auth import get_user_model
        from fhort.accounts.capabilities import DEFAULT_ROLE
        from fhort.accounts.models import UserProfile
        if not self.o['crea_entorn_absent']:
            absents.append('UserProfile (%s)' % uname)
            return None
        if not self.o['apply']:
            self.diu(self.style.WARNING("  CREARÀ    %-22s %-24s → auth_user + UserProfile nous, "
                                        "password inutilitzable" % ('UserProfile', uname)))
            self.creats_per_la_sembra.append('UserProfile %s (actor de la foto)' % uname)
            return None
        User = get_user_model()
        u = User.objects.filter(username=uname).first()
        if u is None:
            u = User(username=uname, is_active=True)
            u.set_unusable_password()
            u.save()
        # `accounts/signals.py::create_user_profile` (post_save de User) JA ha creat el
        # UserProfile dins del tenant. Mateix patró que `sync_size_fitting`: s'adopta, no se'n
        # crea un segon —fer-ho peta contra `accounts_userprofile_user_id_key`.
        up = UserProfile.objects.filter(user=u).first()
        adoptat = up is not None
        if up is None:
            up = UserProfile.objects.create(user=u, nom_complet=uname, rol_nom=DEFAULT_ROLE)
        # El rol NO se l'inventa la sembra: la foto no el porta, i el que hi deixa el signal
        # (DEFAULT_ROLE) és una dada declarada, no una suposició. Aquest compte no ha
        # d'entrar enlloc — només ha de poder ser el destí d'una FK d'autoria.
        self.diu(self.style.SUCCESS(
            "  CREAT     %-22s %-24s → auth_user pk=%s · UserProfile pk=%s (%s, rol=%r)"
            % ('UserProfile', uname, u.pk, up.pk,
               'adoptat del signal' if adoptat else 'creat', up.rol_nom)))
        self.creats_per_la_sembra.append(
            'UserProfile %s → auth_user pk=%s (schema del tenant), UserProfile pk=%s, '
            'rol=%r, password inutilitzable' % (uname, u.pk, up.pk, up.rol_nom))
        return up

    def _usernames_referenciats(self):
        out = {self.D['model'].get('_created_by'), self.D['model'].get('_responsable'),
               self.D['size_fittings'][0].get('_creat_per')}
        for gv in self.D['size_fittings'][0]['grading_versions']:
            out.add(gv.get('_creat_per'))
        for s in self.D['fitting_sessions']:
            out.add(s.get('_created_by'))
            out.add(s.get('_responsable'))
            out |= set(s.get('_attendees') or [])
        for p in self.D['piece_fittings']:
            out.add(p.get('_created_by'))
        for t in self.D['model_tasks']:
            out.add(t.get('_assignee'))
            for tm in (t.get('timers') or []):
                out.add(tm.get('_tecnic'))
        for f in self.D['model_fitxers']:
            out.add(f.get('_pujat_per'))
        for b in self.D['base_measurements']:
            out.add(b.get('_created_by'))
        for l in self.D['measurement_change_log']:
            out.add(l.get('_created_by'))
        return out

    # ── 2. POMMaster: resol per codi, VERIFICA contingut ─────────────────────
    def _resol_poms(self):
        from fhort.pom.models import POMMaster

        self.titol('POMMaster · resolts per codi_client, VERIFICATS per contingut')
        foto = {p['id']: p for p in self.D['pom_masters_referenciats']}
        usats = sorted({b['pom_id'] for b in self.D['base_measurements']}
                       | {r['pom_id'] for r in self.D['model_grading_rules']}
                       | {s['pom_id'] for gv in self.D['size_fittings'][0]['grading_versions']
                          for s in self._specs(gv)}
                       | {l['pom_id'] for p in self.D['piece_fittings'] for l in p['lines']}
                       | {l['pom_id'] for l in self.D['measurement_change_log']})

        mapa, no_resolts, absents = {}, [], []
        for pid in usats:
            f = foto.get(pid)
            if not f:
                absents.append('pk PROD %s (no és a la foto)' % pid)
                continue
            cands = list(POMMaster.objects.filter(codi_client=f['codi_client'])
                         .select_related('pom_global', 'categoria'))
            if not cands:
                absents.append('%s (codi_client)' % f['codi_client'])
                continue
            if len(cands) > 1:
                no_resolts.append((f['codi_client'], pid,
                                   ['AMBIGU: %d POMMaster amb aquest codi' % len(cands)]))
                continue
            c = cands[0]
            diffs = []
            if (c.nom_client or '') != (f['nom_client'] or ''):
                diffs.append("nom_client: staging=%r foto=%r" % (c.nom_client, f['nom_client']))
            cat = getattr(c.categoria, 'codi', None)
            if cat != f['categoria_codi']:
                diffs.append("categoria: staging=%r foto=%r" % (cat, f['categoria_codi']))
            glob = getattr(c.pom_global, 'codi', None) if c.pom_global_id else None
            if glob != f['pom_code_global']:
                diffs.append("pom_global: staging=%r foto=%r" % (glob, f['pom_code_global']))
            if bool(c.actiu) != bool(f['actiu']):
                diffs.append("actiu: staging=%s foto=%s" % (c.actiu, f['actiu']))
            mapa[pid] = c
            if diffs:
                no_resolts.append((f['codi_client'], pid, diffs))

        self.diu("  resolts 1:1 per codi: %d/%d POMMaster" % (len(mapa), len(usats)))
        if absents:
            self.diu(self.style.ERROR("  ABSENTS a staging (%d): %s" % (len(absents), absents)))
        if no_resolts:
            self.diu(self.style.WARNING(
                "  no_resolts · %d POM resolen per codi però el CONTINGUT divergeix:"
                % len(no_resolts)))
            for codi, pid, diffs in no_resolts:
                marca = '‼' if any(d.startswith('pom_global') or d.startswith('AMBIGU')
                                   for d in diffs) else ' '
                self.diu("   %s %-5s (PROD pk=%s)" % (marca, codi, pid))
                for d in diffs:
                    self.diu("        · " + d)
            self.diu("     ‼ = divergència d'ANCORATGE (pom_global/ambigüitat): canvia el "
                     "significat, no només l'etiqueta.")

        if absents:
            self.atura("POMMaster absents: %s" % absents)
        if no_resolts and not self.o['accepta_discrepancies_pom']:
            self.diu()
            self.diu(self.style.ERROR(
                "ATURADA · match per codi NO és match de significat (LLEI S44).\n"
                "Cap POM es crea de nou. Per reutilitzar els de dalt tal com són cal OK "
                "explícit:  --accepta-discrepancies-pom"))
            self.atura("%d POM amb contingut divergent" % len(no_resolts))
        return mapa

    def _actor(self, uname, M, camp):
        """L'actor `uname` en la forma que demana `M.camp`.

        Els camps d'autoria no apunten tots al mateix model: `SizeFitting.creat_per` o
        `ModelTask.assignee` volen un UserProfile, però `BaseMeasurement.created_by`,
        `MeasurementChangeLog.created_by` i `Model.design_freeze_by` volen el User. Es llegeix
        del camp mateix en comptes de recordar-ho: així la sembra no es trenca en silenci si
        una FK canvia de banda.
        """
        up = self._users.get(uname)
        if up is None:
            return None
        remot = M._meta.get_field(camp).remote_field.model
        return up.user if remot.__name__ == 'User' else up

    @staticmethod
    def _specs(gv):
        return gv.get('graded_specs') or gv.get('specs') or []

    # ── 3. el joc de regles: hash canònic ────────────────────────────────────
    def _verifica_ruleset(self):
        import hashlib
        from fhort.pom.models import GradingRuleSet, GradingRule

        self.titol('GradingRuleSet BRW-CATALEG-v3 · hash canònic de les 142 regles')
        snap = self.D['grading_rule_set_snapshot']

        def n(x):
            if x is None:
                return None
            try:
                return "%.4f" % float(x)
            except (TypeError, ValueError):
                return str(x)

        def fila(pg, cc, log, i, ib, ibr, tbl, tbp, tblab, vs, act):
            return [pg, cc, log, n(i), n(ib), n(ibr), tbl, tbp, tblab,
                    json.dumps(vs, sort_keys=True) if vs is not None else None, bool(act)]

        def h(rows):
            rows = sorted(rows, key=lambda r: json.dumps(r, sort_keys=True, ensure_ascii=False))
            return hashlib.sha256(
                json.dumps(rows, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

        f_rows = [fila((r['_pom'] or {}).get('pom_global'), (r['_pom'] or {}).get('codi_client'),
                       r['logica'], r['increment'], r['increment_base'], r['increment_break'],
                       r['talla_break_label'], r['talla_break_pos'], r['talla_base_label'],
                       r['valors_step'], r['actiu']) for r in snap['rules']]
        rs = GradingRuleSet.objects.get(codi_sistema=snap['codi_sistema'])
        s_rows = [fila(getattr(r.pom.pom_global, 'codi', None) if r.pom.pom_global_id else None,
                       r.pom.codi_client, r.logica, r.increment, r.increment_base,
                       r.increment_break, r.talla_break_label, r.talla_break_pos,
                       getattr(r.talla_base, 'etiqueta', None), r.valors_step, r.actiu)
                  for r in GradingRule.objects.filter(rule_set=rs)
                  .select_related('pom', 'pom__pom_global', 'talla_base')]

        self.diu("  foto     %d regles · hash %s" % (len(f_rows), h(f_rows)))
        self.diu("  staging  %d regles · hash %s   (pk=%s)" % (len(s_rows), h(s_rows), rs.pk))
        if h(f_rows) == h(s_rows):
            self.diu(self.style.SUCCESS("  IDÈNTIC → es reutilitza el joc de staging."))
            return rs

        from collections import Counter
        cf = Counter(json.dumps(r, sort_keys=True, ensure_ascii=False) for r in f_rows)
        cs = Counter(json.dumps(r, sort_keys=True, ensure_ascii=False) for r in s_rows)
        nomes_foto, nomes_stg = list(cf - cs), list(cs - cf)
        self.diu(self.style.WARNING(
            "  DIVERGENT · %d fila(es) només a la foto, %d només a staging:"
            % (len(nomes_foto), len(nomes_stg))))
        for x in nomes_foto[:12]:
            self.diu("     foto    " + x)
        for x in nomes_stg[:12]:
            self.diu("     staging " + x)
        if not self.o['accepta_ruleset_divergent']:
            self.diu()
            self.diu(self.style.ERROR(
                "ATURADA · el joc de regles de staging NO és el de la foto.\n"
                "No es re-sembra cap joc sense OK. Per reutilitzar l'existent: "
                "--accepta-ruleset-divergent"))
            self.atura("hash del ruleset divergent")
        return rs

    # ── 4. el pla ────────────────────────────────────────────────────────────
    def _pla(self):
        self.titol('PLA · el que es crearà (ha de quadrar amb les guardes del cens)')
        pla = self._recompte_previst()
        tot_ok = True
        for k, esperat in GUARDES.items():
            prev = pla.get(k, 0)
            ok = prev == esperat
            tot_ok &= ok
            self.diu("  %-22s previst %4d   guarda %4d   %s"
                     % (k, prev, esperat, 'OK' if ok else '✗ NO QUADRA'))
        if not tot_ok:
            self.atura("el pla no quadra amb les guardes del cens")
        self.diu(self.style.SUCCESS("  Les 14 guardes quadren."))

        self.titol('INCOHERÈNCIES QUE ES CONSERVEN (són el banc de proves)')
        rd = next(r for r in self.D['model_grading_rules']
                  if (r['_pom'] or {}).get('codi_client') == 'D')
        self.diu("  regla POM «D»   increment=%s · increment_base=%s · increment_break=%s"
                 % (rd['increment'], rd['increment_base'], rd['increment_break']))
        for gv in self.D['size_fittings'][0]['grading_versions']:
            d = [s for s in self._specs(gv) if (s['_pom'] or {}).get('codi_client') == 'D']
            inc = sorted({s['increment_applied_cm'] for s in d})
            self.diu("  v%-2d %-22s vigent=%-5s specs=%3d · pas al D=%s"
                     % (gv['version_number'], repr(gv['nom'])[:22], gv['is_active'],
                        len(self._specs(gv)), inc))
        for p in self.D['piece_fittings']:
            gv = next(g for g in self.D['size_fittings'][0]['grading_versions']
                      if g['id'] == p['grading_version_id'])
            self.diu("  PieceFitting PROD#%s → GradingVersion v%d (vigent=%s) · %d línies"
                     % (p['id'], gv['version_number'], gv['is_active'], len(p['lines'])))
        sf = self.D['size_fittings'][0]
        self.diu("  SizeFitting     estat=%r · base_tancada=%s" % (sf['estat'], sf['base_tancada']))
        self.diu("  joc de regles   BROWNIE (%s) sobre un model del client %s"
                 % (self.D['grading_rule_set_snapshot']['codi_sistema'],
                    self.D['model']['codi_tenant']))

    def _recompte_previst(self):
        sf = self.D['size_fittings'][0]
        return {
            'Model': 1,
            'BaseMeasurement': len(self.D['base_measurements']),
            'ModelGradingRule': len(self.D['model_grading_rules']),
            'MeasurementChangeLog': len(self.D['measurement_change_log']),
            'SizeFitting': len(self.D['size_fittings']),
            'GradingVersion': len(sf['grading_versions']),
            'GradedSpec': sum(len(self._specs(g)) for g in sf['grading_versions']),
            'FittingSession': len(self.D['fitting_sessions']),
            'PieceFitting': len(self.D['piece_fittings']),
            'PieceFittingLine': sum(len(p['lines']) for p in self.D['piece_fittings']),
            'ModelTask': len(self.D['model_tasks']),
            'TimerEntrada': sum(len(t.get('timers') or []) for t in self.D['model_tasks']),
            'ModelFitxer': len(self.D['model_fitxers']),
            'Watchpoint': len(self.D['watchpoints']),
        }

    # ── 5. l'escriptura ──────────────────────────────────────────────────────
    @transaction.atomic
    def _sembra(self, ent, poms):
        from fhort.models_app.models import (Model, BaseMeasurement, ModelGradingRule,
                                             MeasurementChangeLog, ModelFitxer, Watchpoint)
        from fhort.fitting.models import (SizeFitting, GradingVersion, GradedSpec,
                                          FittingSession, PieceFitting, PieceFittingLine)
        from fhort.tasks.models import ModelTask, TimerEntrada

        self.titol('APPLY')
        m = self.D['model']
        u = self._users = ent['users']
        mapa_pk = {}

        # ── Model. `codi_intern` va explícit: així `generate_model_code` (pre_save)
        # no el regenera i el sequencial de la foto es conserva.
        model = Model(
            codi_intern=m['codi_intern'], codi_client=m['codi_client'],
            codi_tenant=m['codi_tenant'], any=m['any'], temporada=m['temporada'],
            sequencial=m['sequencial'], nom_prenda=m['nom_prenda'],
            descripcio=m['descripcio'], collection=m['collection'],
            color_referencia=m['color_referencia'], fit_type=m['fit_type'],
            estat=m['estat'], fase_actual=m['fase_actual'], prioritat=m['prioritat'],
            target=m['target'], construction=m['construction'],
            base_size_label=m['base_size_label'], size_run_model=m['size_run_model'],
            measurements_version=m['measurements_version'], origen=m['origen'],
            studio_assignat=m['studio_assignat'], observacions=m['observacions'],
            origen_patro=m['origen_patro'], versio=m['versio'],
            fabric_main=m['fabric_main'], fabric_composition=m['fabric_composition'],
            fabric_notes=m['fabric_notes'], shrinkage_type=m['shrinkage_type'],
            shrinkage_warp=m['shrinkage_warp'], shrinkage_weft=m['shrinkage_weft'],
            shrinkage_pct=m['shrinkage_pct'], shrinkage_iso_key=m['shrinkage_iso_key'],
            piece_number=m['piece_number'], reanchored_by_start=m['reanchored_by_start'],
            slots_prev_tecnics=m['slots_prev_tecnics'],
            slots_prev_confeccio=m['slots_prev_confeccio'],
            slots_reals_tecnic=m['slots_reals_tecnic'],
            slots_reals_confeccio=m['slots_reals_confeccio'],
            data_objectiu=m['data_objectiu'], data_tancament=m['data_tancament'],
            predicted_start=m['predicted_start'], predicted_end=m['predicted_end'],
            design_freeze_at=m['design_freeze_at'],
            customer=ent['customer'], garment_type=ent['garment_type'],
            garment_group=ent['garment_group'], garment_type_item=ent['garment_type_item'],
            size_system=ent['size_system'], grading_rule_set=ent['grading_rule_set'],
            created_by=u.get(m['_created_by']),
            responsable=u.get(m['_responsable']),
            design_freeze_by=self._actor(m['_design_freeze_by'], Model, 'design_freeze_by'),
        )
        model.save()   # ← dispara sync_size_fitting: el SF surt d'aquí
        mapa_pk['Model'] = {m['id']: model.pk}
        # auto_now_add / update_last_activity han escrit «ara»: es restaura la foto.
        Model.objects.filter(pk=model.pk).update(
            created_at=m['created_at'], data_entrada=m['data_entrada'],
            darrera_activitat=m['darrera_activitat'],
            consumption_started_at=m['consumption_started_at'])
        self.diu("  Model                pk=%s  (PROD %s)" % (model.pk, m['id']))

        # ── SizeFitting: s'ADOPTA el que ha creat el signal. Crear-ne un altre
        # en faria dos i la guarda (1) petaria.
        sf = self.D['size_fittings'][0]
        sf_obj = SizeFitting.objects.filter(model=model).first()
        if sf_obj is None:
            raise RuntimeError("el signal sync_size_fitting no ha creat el SizeFitting")
        SizeFitting.objects.filter(pk=sf_obj.pk).update(
            numero=sf['numero'], codi=sf['codi'], tipus=sf['tipus'], estat=sf['estat'],
            notes=sf['notes'], base_tancada=sf['base_tancada'],
            data_creacio=sf['data_creacio'], data_tancament=sf['data_tancament'],
            data_tancament_base=sf['data_tancament_base'],
            creat_per=u.get(sf['_creat_per']))
        sf_obj.refresh_from_db()
        mapa_pk['SizeFitting'] = {sf['id']: sf_obj.pk}
        self.diu("  SizeFitting          pk=%s  (PROD %s) · adoptat del signal, estat=%r"
                 % (sf_obj.pk, sf['id'], sf['estat']))

        # ── BaseMeasurement per bulk_create: no dispara post_save i per tant NO
        # escriu cap MeasurementChangeLog automàtic. Els 21 logs es transcriuen.
        bms = [BaseMeasurement(
            model=model, pom=poms[b['pom_id']], base_value_cm=b['base_value_cm'],
            is_key=b['is_key'], is_active=b['is_active'], notes=b['notes'],
            tolerancia_minus=b['tolerancia_minus'], tolerancia_plus=b['tolerancia_plus'],
            nom_fitxa=b['nom_fitxa'], origen=b['origen'], ordre=b['ordre'],
            seccio=b['seccio'], nom_canonic_model=b['nom_canonic_model'],
            nom_traduit_model=b['nom_traduit_model'], capa=b['capa'],
            instancia=b['instancia'], garment=b['garment'],
            created_by=self._actor(b['_created_by'], BaseMeasurement, 'created_by'))
            for b in self.D['base_measurements']]
        bms = BaseMeasurement.objects.bulk_create(bms)
        bm_pk = {b['id']: o.pk for b, o in zip(self.D['base_measurements'], bms)}
        mapa_pk['BaseMeasurement'] = bm_pk
        for b, o in zip(self.D['base_measurements'], bms):
            BaseMeasurement.objects.filter(pk=o.pk).update(
                created_at=b['created_at'], updated_at=b['updated_at'])
        self._guarda(BaseMeasurement.objects.filter(model=model).count(), 'BaseMeasurement')

        auto = MeasurementChangeLog.objects.filter(model=model).count()
        if auto:
            raise RuntimeError(
                "bulk_create ha disparat %d MeasurementChangeLog automàtics: el signal "
                "log_measurement_change ja no entra per post_save i la sembra hauria de "
                "canviar d'estratègia" % auto)

        mcls = [MeasurementChangeLog(
            model=model, pom=poms[l['pom_id']],
            base_measurement_id=bm_pk.get(l['base_measurement_id']),
            valor_anterior=l['valor_anterior'], valor_nou=l['valor_nou'],
            motiu=l['motiu'], context=l['context'], fitting_ref_id=None,
            fora_de_tolerancia=l['fora_de_tolerancia'], capa=l['capa'],
            instancia=l['instancia'], garment=l['garment'],
            created_by=self._actor(l['_created_by'], MeasurementChangeLog, 'created_by'))
            for l in self.D['measurement_change_log']]
        mcls = MeasurementChangeLog.objects.bulk_create(mcls)
        for l, o in zip(self.D['measurement_change_log'], mcls):
            MeasurementChangeLog.objects.filter(pk=o.pk).update(created_at=l['created_at'])
        self._guarda(MeasurementChangeLog.objects.filter(model=model).count(),
                     'MeasurementChangeLog')

        # ── ModelGradingRule: es copien CRUES. La «D» arriba amb increment=2.00
        # i base/break=0.50 — la incoherència és el banc.
        rules = [ModelGradingRule(
            model=model, pom=poms[r['pom_id']], logica=r['logica'],
            increment=r['increment'], valors_step=r['valors_step'],
            increment_base=r['increment_base'], increment_break=r['increment_break'],
            talla_break_label=r['talla_break_label'], talla_break_pos=r['talla_break_pos'],
            origen=r['origen'], actiu=r['actiu'], garment=r['garment'],
            derivat_de_rule_set=ent['grading_rule_set'])
            for r in self.D['model_grading_rules']]
        rules = ModelGradingRule.objects.bulk_create(rules)
        # L'ORDRE relatiu importa per al bug A: les regles es van editar ABANS de
        # generar la v6. Els timestamps de la foto el conserven.
        for r, o in zip(self.D['model_grading_rules'], rules):
            ModelGradingRule.objects.filter(pk=o.pk).update(
                created_at=r['created_at'], updated_at=r['updated_at'])
        self._guarda(ModelGradingRule.objects.filter(model=model).count(), 'ModelGradingRule')

        # ── Les 6 GradingVersions amb els seus GradedSpec, TAL QUAL.
        # Mai `generate_graded_specs`: transcripció, no regeneració.
        gv_pk, n_specs = {}, 0
        for gv in sf['grading_versions']:
            o = GradingVersion.objects.create(
                size_fitting=sf_obj, nom=gv['nom'], aprovada=gv['aprovada'],
                notes=gv['notes'], version_number=gv['version_number'],
                is_active=gv['is_active'], data_aprovacio=gv['data_aprovacio'],
                creat_per=u.get(gv['_creat_per']),
                aprovada_per=u.get(gv.get('_aprovada_per')))
            GradingVersion.objects.filter(pk=o.pk).update(data=gv['data'])
            gv_pk[gv['id']] = o.pk
            specs = self._specs(gv)
            GradedSpec.objects.bulk_create([GradedSpec(
                grading_version=o, pom=poms[s['pom_id']], size_label=s['size_label'],
                graded_value_cm=s['graded_value_cm'],
                grading_type_applied=s['grading_type_applied'],
                increment_applied_cm=s['increment_applied_cm'], is_active=s['is_active'],
                generated_from_version=s['generated_from_version'], capa=s['capa'],
                instancia=s['instancia'], garment=s['garment']) for s in specs])
            n_specs += len(specs)
            self.diu("  GradingVersion v%-2d   pk=%-5s (PROD %s) · %3d specs · vigent=%s"
                     % (gv['version_number'], o.pk, gv['id'], len(specs), gv['is_active']))
        mapa_pk['GradingVersion'] = gv_pk
        self._guarda(GradingVersion.objects.filter(size_fitting=sf_obj).count(), 'GradingVersion')
        self._guarda(GradedSpec.objects.filter(
            grading_version__size_fitting=sf_obj).count(), 'GradedSpec')

        # ── Sessions
        fs_pk = {}
        for s in self.D['fitting_sessions']:
            o = FittingSession.objects.create(
                model=model, fase=s['fase'], data=s['data'], start_time=s['start_time'],
                end_time=s['end_time'], model_persona=s['model_persona'],
                assistents=s['assistents'], lloc=s['lloc'], estat=s['estat'],
                notes=s['notes'], duracio_minuts=s['duracio_minuts'],
                convocatoria=s['convocatoria'], started_at=s['started_at'],
                finished_at=s['finished_at'], motiu_anullacio=s['motiu_anullacio'],
                created_by=u.get(s['_created_by']), responsable=u.get(s['_responsable']))
            FittingSession.objects.filter(pk=o.pk).update(created_at=s['created_at'])
            for uname in (s.get('_attendees') or []):
                if u.get(uname):
                    o.attendees.add(u[uname])
            fs_pk[s['id']] = o.pk
        mapa_pk['FittingSession'] = fs_pk
        self._guarda(FittingSession.objects.filter(model=model).count(), 'FittingSession')

        # ── PieceFitting: el #15 penja de la v2, NO de la vigent. Es respecta.
        n_lines = 0
        pf_pk = {}
        for p in self.D['piece_fittings']:
            o = PieceFitting.objects.create(
                session_id=fs_pk[p['session_id']], model=model,
                grading_version_id=gv_pk[p['grading_version_id']],
                gate=p['gate'], gate_motiu=p['gate_motiu'], gate_at=p['gate_at'],
                gate_per=u.get(p.get('_gate_per')), created_by=u.get(p['_created_by']))
            PieceFitting.objects.filter(pk=o.pk).update(created_at=p['created_at'])
            PieceFittingLine.objects.bulk_create([PieceFittingLine(
                piece_fitting=o, pom=poms[l['pom_id']], size_label=l['size_label'],
                valor_teoric=l['valor_teoric'], valor_real=l['valor_real'],
                presa_at=l['presa_at'], nota=l['nota'], decisio=l['decisio'],
                capa=l['capa'], instancia=l['instancia'], garment=l['garment'])
                for l in p['lines']])
            n_lines += len(p['lines'])
            pf_pk[p['id']] = o.pk
        mapa_pk['PieceFitting'] = pf_pk
        self._guarda(PieceFitting.objects.filter(model=model).count(), 'PieceFitting')
        self._guarda(PieceFittingLine.objects.filter(
            piece_fitting__model=model).count(), 'PieceFittingLine')

        # ── Tasques i timers. work_order NO es transcriu: la comanda #69 de PROD
        # no viatja a la foto i el camp és nullable.
        n_timers = 0
        for t in self.D['model_tasks']:
            o = ModelTask.objects.create(
                model=model, task_type=ent['task_types'][t['_task_type']['code']],
                status=t['status'], origen=t['origen'], order=t['order'],
                started_at=t['started_at'], finished_at=t['finished_at'],
                estimated_minutes=t['estimated_minutes'],
                planned_start=t['planned_start'], planned_end=t['planned_end'],
                planned_locked=t['planned_locked'], off_recipe=t['off_recipe'],
                motiu=t['motiu'], work_order=None,
                fitting_session_id=fs_pk.get(t['fitting_session_id']),
                assignee=u.get(t['_assignee']))
            ModelTask.objects.filter(pk=o.pk).update(
                created_at=t['created_at'], updated_at=t['updated_at'])
            for tm in (t.get('timers') or []):
                TimerEntrada.objects.create(
                    model_task=o, tecnic=u.get(tm['_tecnic']), inici=tm['inici'],
                    fi=tm['fi'], minuts=tm['minuts'], actiu=tm['actiu'],
                    last_heartbeat=tm['last_heartbeat'], origen=tm['origen'])
                n_timers += 1
        self._guarda(ModelTask.objects.filter(model=model).count(), 'ModelTask')
        self._guarda(TimerEntrada.objects.filter(model_task__model=model).count(),
                     'TimerEntrada')

        # ── ModelFitxer: la fila i, si la foto porta el document, el fitxer al disc.
        from django.conf import settings
        fx_pk, escrits = {}, 0
        for f in self.D['model_fitxers']:
            o = ModelFitxer.objects.create(
                model=model, nom_fitxer=f['nom_fitxer'], categoria=f['categoria'],
                tipus=f['tipus'], versio=f['versio'], is_current=f['is_current'],
                accessible_portal=f['accessible_portal'], mida_bytes=f['mida_bytes'],
                fitxer=f['fitxer'], url_extern=f['url_extern'],
                descripcio=f['descripcio'], enviat_ia=f['enviat_ia'],
                resultat_ia_path=f['resultat_ia_path'], checksum=f['checksum'],
                mimetype=f['mimetype'], origen=f['origen'],
                versio_anterior_id=fx_pk.get(f['versio_anterior_id']),
                pujat_per=u.get(f.get('_pujat_per')))
            ModelFitxer.objects.filter(pk=o.pk).update(data_pujada=f['data_pujada'])
            fx_pk[f['id']] = o.pk
            doc = f.get('_ftt_document')
            if doc and f.get('fitxer'):
                # 🚨 AQUÍ HI HAVIA DOS DEFECTES ALHORA, i tots dos donaven un ✅ FALS (J-bis/3).
                #
                # 1. EL FORMAT. Un `.ftt` no és el document en JSON: és un ZIP amb `manifest.json`
                #    + `document.json` (`services_ftt.pack`). Un `json.dump` cru produeix un
                #    fitxer que `load_document` no pot desempaquetar mai — l'editor l'obria BUIT.
                # 2. EL CAMÍ. `MEDIA_ROOT + name` NO és on Django llegeix: el default storage és
                #    `TenantFileSystemStorage`, que hi posa l'esquema pel mig
                #    (`media/fhort/model_fitxers/…`). Els vuit fitxers van anar a
                #    `media/model_fitxers/…`, un nivell massa amunt, i el comptador els va donar
                #    per escrits perquè l'`open()` havia funcionat.
                #
                # Es fa igual que el desat de veritat: `pack` per al blob i **el camp del model**
                # per al camí, que és l'únic que sap del tenant. I es desa `mida_bytes`/`checksum`
                # dels bytes REALS: el `checksum` de la foto és el sha del ZIP de PROD i **no és
                # reproduïble** —`zipfile` hi estampa l'hora de cada entrada, v. l'avís
                # d'`empremta_logica`—, o sigui que copiar-lo seria desar una empremta que no
                # correspon a cap fitxer d'aquest disc. La mida sí que casa, i és la comparació
                # que val: 451/468/594/1571/1591/1623/1626/1624, clavades.
                from fhort.models_app import services_ftt
                blob = services_ftt.pack(doc)
                dest = o.fitxer.path
                os.makedirs(os.path.dirname(dest), mode=0o2775, exist_ok=True)
                with open(dest, 'wb') as fh:
                    fh.write(blob)
                ModelFitxer.objects.filter(pk=o.pk).update(
                    mida_bytes=len(blob),
                    checksum=hashlib.sha256(blob).hexdigest())
                escrits += 1
        mapa_pk['ModelFitxer'] = fx_pk
        self._guarda(ModelFitxer.objects.filter(model=model).count(), 'ModelFitxer')
        self.diu("  ModelFitxer          %d files · %d documents .ftt escrits al disc"
                 % (len(fx_pk), escrits))

        self._guarda(Watchpoint.objects.filter(model=model).count(), 'Watchpoint')

        self.titol('MAPA pk PROD → pk staging')
        for ent_nom, mp in mapa_pk.items():
            mostra = ', '.join('%s→%s' % kv for kv in list(mp.items())[:8])
            self.diu("  %-20s %s%s" % (ent_nom, mostra, ' …' if len(mp) > 8 else ''))
        self.diu()
        self.diu(self.style.SUCCESS("SEMBRAT · model pk=%s · les 14 guardes quadren." % model.pk))
        self.model_pk = model.pk

    def _guarda(self, real, clau):
        esperat = GUARDES[clau]
        if real != esperat:
            raise RuntimeError(
                "GUARDA · %s: n'hi ha %d i el cens de PROD en diu %d. Res s'ha desat "
                "(rollback de l'atomic)." % (clau, real, esperat))
        self.diu("  guarda OK            %-22s %4d" % (clau, real))

    # ── report ───────────────────────────────────────────────────────────────
    def _escriu_report(self):
        if not self.o['report']:
            return
        with open(self.o['report'], 'w') as fh:
            fh.write('\n'.join(self.linies) + '\n')
        self.stdout.write("\nreport → %s" % self.o['report'])
