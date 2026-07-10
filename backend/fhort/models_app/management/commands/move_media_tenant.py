"""Trasllada els bytes de media a l'arrel per tenant (S03a · P2a).

    python manage.py move_media_tenant              # dry-run (per defecte)
    python manage.py move_media_tenant --apply      # mou de veritat

Context: fins a S03a el media NO estava aïllat per tenant (tots els schemas escrivien a
MEDIA_ROOT). Amb `MULTITENANT_RELATIVE_MEDIA_ROOT='%s'` i TenantFileSystemStorage, el
storage resol location=MEDIA_ROOT/<schema>. El `name` desat a la BD ja és relatiu a
aquesta arrel → **aquesta comanda NO escriu a la BD**: només mou bytes de
MEDIA_ROOT/<name> a MEDIA_ROOT/<schema>/<name>.

Abast: es mouen NOMÉS els fitxers referenciats per alguna fila (qualsevol FileField/
ImageField de qualsevol model instal·lat, no només ModelFitxer). Els orfes de disc es
queden on són — audit_fitxers ja els llista i no és feina d'aquesta comanda decidir-ne
el destí.

Idempotent: un fitxer ja present a la destinació (i absent de l'origen) es compta com a
`ja_fet` i no es toca. Verificació final: per cada schema, files amb bytes a la nova
arrel == files referenciades amb bytes en algun lloc.
"""
import os
import shutil

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import models as dj_models
from django_tenants.utils import get_tenant_model, schema_context


def _file_fields():
    """[(model, field_name)] de tots els FileField/ImageField dels models instal·lats."""
    out = []
    for model in apps.get_models():
        for field in model._meta.get_fields():
            if isinstance(field, dj_models.FileField):
                out.append((model, field.name))
    return out


def _referenced_names(model, field_name):
    return [n for n in model.objects.exclude(**{field_name: ''})
            .exclude(**{f'{field_name}__isnull': True})
            .values_list(field_name, flat=True) if n]


def _dirs_a_crear(path):
    """Els directoris que `os.makedirs(path)` haurà de crear, de l'arrel cap a la fulla.

    `os.makedirs` en crea DIVERSOS (`.../model_fitxers/2026/06`) i tots neixen amb l'owner del
    procés. Un chown només a la fulla deixaria els pares de root — la causa exacta de
    l'incident del 2026-07-10. Cal saber quins són nous ABANS de crear-los.
    """
    nous = []
    p = path
    while p and not os.path.exists(p):
        nous.append(p)
        pare = os.path.dirname(p)
        if pare == p:      # arrel del filesystem: atura
            break
        p = pare
    return list(reversed(nous))


class Command(BaseCommand):
    help = 'Mou els bytes de media a MEDIA_ROOT/<schema>/ (dry-run per defecte). No toca la BD.'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true',
                            help='Executa el trasllat. Sense aquest flag només mostra el pla.')
        parser.add_argument('--schema', help='Limita el trasllat a aquest schema.')
        parser.add_argument(
            '--owner', default='www-data:www-data',
            help='owner[:group] dels directoris creats i dels fitxers moguts (--apply). '
                 'Gunicorn corre com www-data; si media/ és de root, tot upload dona 500.')

    def _chown(self, path):
        """chown best-effort. Si el procés no és root, avisa UN cop i continua: el trasllat
        de bytes és la feina d'aquesta comanda; l'owner és higiene, no ha de fer petar res."""
        if self._owner is None:
            return
        user, group = self._owner
        try:
            shutil.chown(path, user=user, group=group)
        except (PermissionError, LookupError, OSError) as e:
            if not self._chown_avisat:
                self._chown_avisat = True
                self.stdout.write(self.style.WARNING(
                    f'  AVÍS: chown {user}:{group} ha fallat ({e.__class__.__name__}: {e}).\n'
                    f'  Cal executar la comanda com a root, o aplicar el chown a mà després:\n'
                    f'    chown -R {user}:{group} {os.path.join(str(settings.MEDIA_ROOT))}\n'
                    f'  (avís emès un sol cop; el trasllat continua)'))

    def handle(self, *args, **opts):
        media_root = str(settings.MEDIA_ROOT)
        if getattr(settings, 'MULTITENANT_RELATIVE_MEDIA_ROOT', None) != '%s':
            raise CommandError(
                "MULTITENANT_RELATIVE_MEDIA_ROOT ha de ser '%s' perquè el trasllat tingui sentit.")

        known = list(get_tenant_model().objects
                     .exclude(schema_name='public')
                     .values_list('schema_name', flat=True))
        if opts['schema']:
            if opts['schema'] not in known:
                raise CommandError(
                    f"Schema '{opts['schema']}' no existeix. Tenants: {', '.join(known) or '(cap)'}")
            known = [opts['schema']]

        apply = opts['apply']
        mode = self.style.WARNING('APPLY') if apply else self.style.SUCCESS('DRY-RUN')

        # D19 — owner dels directoris nous. `os.makedirs` els crea amb l'owner del procés
        # (root al deploy) i `shutil.move` només preserva l'owner si és el MATEIX filesystem
        # (os.rename); cross-FS cau a copy2, que fa copystat però NO chown.
        self._chown_avisat = False
        raw = (opts['owner'] or '').strip()
        if not raw:
            self._owner = None
        else:
            user, _, group = raw.partition(':')
            self._owner = (user, group or user)

        self.stdout.write(f'MEDIA_ROOT: {media_root}   mode: {mode}'
                          + (f'   owner: {self._owner[0]}:{self._owner[1]}'
                             if self._owner and apply else ''))

        for schema in known:
            self.stdout.write(self.style.MIGRATE_HEADING(f'\n=== {schema}'))
            dest_root = os.path.join(media_root, schema)

            moguts = ja_fet = absents = 0
            amb_bytes = []      # noms que tenien bytes (origen o destí) → els que ha de verificar
            with schema_context(schema):
                for model, field_name in _file_fields():
                    for name in _referenced_names(model, field_name):
                        src = os.path.join(media_root, name)
                        dst = os.path.join(dest_root, name)

                        if os.path.exists(dst):
                            ja_fet += 1
                            amb_bytes.append(name)
                            continue
                        if not os.path.exists(src):
                            # Fila sense bytes enlloc (fantasma). No és feina d'aquesta comanda
                            # arreglar-ho; s'informa i s'exclou de la verificació final.
                            absents += 1
                            self.stdout.write(self.style.ERROR(
                                f'  FANTASMA (cap byte ni a origen ni a destí): {name}'))
                            continue

                        amb_bytes.append(name)
                        moguts += 1
                        self.stdout.write(f'  {name}  →  {schema}/{name}')
                        if apply:
                            dst_dir = os.path.dirname(dst)
                            nous = _dirs_a_crear(dst_dir)
                            os.makedirs(dst_dir, exist_ok=True)
                            for d in nous:
                                self._chown(d)
                            shutil.move(src, dst)
                            # També el fitxer: cross-FS, copy2 no fa chown i arriba com a root.
                            self._chown(dst)

            self.stdout.write(
                f'  resum: {moguts} a moure · {ja_fet} ja fets · {absents} fantasmes')

            # Verificació: tot fitxer que TENIA bytes n'ha de tenir a la nova arrel.
            # Els fantasmes (cap byte enlloc) queden fora: no els pot arreglar un mv.
            if apply:
                falten = [n for n in amb_bytes
                          if not os.path.exists(os.path.join(dest_root, n))]
                if falten:
                    self.stdout.write(self.style.ERROR(
                        f'  VERIFY KO: {len(falten)} referències sense bytes a {schema}/'))
                    for n in falten:
                        self.stdout.write(self.style.ERROR(f'    {n}'))
                else:
                    self.stdout.write(self.style.SUCCESS(
                        '  VERIFY OK: totes les referències amb bytes tenen bytes a la nova arrel.'))
