"""normalitza_size_run — sanejament de l'ORDRE de `Model.size_run_model` (llei S24b).

L'ordre i la distància entre talles els mana el SizeSystem. Fins que la porta única
d'escriptura (`run_del_model`) no va existir, cap de les 9 vies del cens ordenava: totes
desaven l'ordre d'entrada (clic de l'usuari al wizard, ordre del document, ordre de la cel·la
d'Excel). El resultat són runs apendats com el del model 166 a PROD (`XS·S·L·XXS·M`), que el
motor graduava amb el SIGNE INVERTIT. Context: DIAGNOSI_ORDRE_RUN_MODEL_2026-07-22.md.

Aquesta comanda reordena `size_run_model` per `SizeDefinition.ordre`. RES MÉS:

  - **Mai afegeix ni treu talles.** Un run NO CONTIGU és LEGÍTIM (un client que no fabrica la
    M) i es conserva amb el seu forat: el motor ja hi compta la distància real.
  - **Les etiquetes fora del sistema S'INFORMEN i NO es toquen.** No són un problema d'ordre
    sinó de vocabulari, i endevinar-les seria inventar-se dades. Per a aquestes hi ha la
    comanda germana `restaura_size_run`, que tradueix a forma-tenant.
  - **MAI re-propaga.** La re-propagació és un acte conscient per model (D-10): un model
    desordenat té `GradedSpec` numèricament incorrectes, i regenerar-los canvia valors que
    poden estar sota una `GradingVersion` APROVADA. L'informe diu quins models en tenen
    perquè algú ho decideixi; la comanda no ho decideix mai.

Dry-run per defecte; `--apply` per escriure. Idempotent: un segon passi no canvia res.
"""
from django.core.management.base import BaseCommand
from django_tenants.utils import schema_context


class Command(BaseCommand):
    help = ("Reordena Model.size_run_model per SizeDefinition.ordre (dry-run per defecte). "
            "Mai afegeix/treu talles, mai re-propaga.")

    def add_arguments(self, parser):
        parser.add_argument('--schema', default='fhort')
        parser.add_argument('--apply', action='store_true', help='Escriu (default dry-run).')

    def handle(self, *args, **opts):
        from fhort.models_app.models import Model
        from fhort.pom.grading_utils import run_del_model

        schema, apply = opts['schema'], opts['apply']
        desordenats, amb_etiquetes_fora, ja_ok = [], [], 0

        with schema_context(schema):
            qs = (Model.objects.filter(size_system__isnull=False)
                  .exclude(size_run_model__isnull=True).exclude(size_run_model='')
                  .select_related('size_system').order_by('pk'))

            for m in qs:
                actual = [x.strip() for x in m.size_run_model.replace(';', '·').split('·')
                          if x.strip()]
                ordenat, fora = run_del_model(actual, m.size_system)
                if fora:
                    # No es toca: el run porta talles que el sistema no coneix, i reordenar
                    # només les conegudes les faria desaparèixer del camp.
                    amb_etiquetes_fora.append((m, actual, fora))
                    continue
                if ordenat == actual:
                    ja_ok += 1
                    continue
                desordenats.append((m, actual, ordenat))

            self.stdout.write('=' * 78)
            self.stdout.write(f"normalitza_size_run — schema={schema} — "
                              f"{'APPLY' if apply else 'DRY-RUN'}")
            self.stdout.write('=' * 78)
            self.stdout.write(f"  ja ordenats        {ja_ok:>6}")
            self.stdout.write(f"  DESORDENATS        {len(desordenats):>6}")
            self.stdout.write(f"  amb etiqueta fora  {len(amb_etiquetes_fora):>6}  (NO es toquen)")
            self.stdout.write('')

            if desordenats:
                impacte = self._impacte_grading({m.pk for m, _, _ in desordenats})
                self.stdout.write('-' * 78)
                self.stdout.write('DESORDENATS')
                self.stdout.write('-' * 78)
                for m, actual, ordenat in desordenats:
                    marca = impacte.get(m.pk)
                    self.stdout.write(
                        f"  {m.pk:>6} {(m.codi_intern or ''):<18.18} "
                        f"{'·'.join(actual)}  ->  {'·'.join(ordenat)}"
                        + (f"   ⚠️ {marca}" if marca else '')
                    )
                self.stdout.write('')

            if amb_etiquetes_fora:
                self.stdout.write('-' * 78)
                self.stdout.write('ETIQUETES FORA DEL SISTEMA — decisió humana, cap canvi')
                self.stdout.write('-' * 78)
                for m, actual, fora in amb_etiquetes_fora:
                    self.stdout.write(
                        f"  {m.pk:>6} {(m.codi_intern or ''):<18.18} "
                        f"run={'·'.join(actual)}  desconegudes={', '.join(fora)}"
                    )
                self.stdout.write('')

            if not apply:
                self.stdout.write(self.style.WARNING(
                    'DRY-RUN: no s\'ha escrit res. Repeteix amb --apply per aplicar-ho.'))
                return

            for m, _, ordenat in desordenats:
                m.size_run_model = '·'.join(ordenat)
                m.save(update_fields=['size_run_model'])
            self.stdout.write(self.style.SUCCESS(
                f'{len(desordenats)} model(s) reordenats.'))
            if desordenats:
                self.stdout.write(self.style.WARNING(
                    'Els GradedSpec existents d\'aquests models NO s\'han regenerat: els que '
                    'es van calcular amb el run desordenat segueixen sent incorrectes. La '
                    're-propagació és un acte conscient per model (D-10).'))

    def _impacte_grading(self, model_ids):
        """Quins d'aquests models tenen graduació vigent, i quina n'és segellada.

        No decideix res: només posa damunt la taula el que fa que la re-propagació sigui una
        decisió humana i no un pas automàtic d'aquesta comanda.
        """
        from fhort.fitting.models import GradingVersion

        out = {}
        qs = (GradingVersion.objects
              .filter(size_fitting__model_id__in=model_ids, is_active=True)
              .values_list('size_fitting__model_id', 'aprovada'))
        for model_id, aprovada in qs:
            if aprovada:
                out[model_id] = 'té GradingVersion activa APROVADA (segellada)'
            else:
                out.setdefault(model_id, 'té GradingVersion activa')
        return out
