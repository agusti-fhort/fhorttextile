"""Auditoria READ-ONLY dels fitxers de model. Informa, NO arregla res.

    python manage.py audit_fitxers                  # tots els tenants
    python manage.py audit_fitxers --schema fhort   # un sol tenant
    python manage.py audit_fitxers --json           # sortida per a eines

Dues comprovacions independents:

(a) INVARIANT DE CADENA — cada cadena `versio_anterior` ha de tenir exactament un
    registre amb is_current=True (el cap). La invariant està documentada al model però
    NO té constraint a la BD, i fins a S03a el ViewSet genèric la podia saltar.

(b) RECONCILIACIÓ DISC↔BD — fitxers a disc sense fila (orfes) i files amb el fitxer
    absent del disc (fantasmes). Els dos costats de la comparació han de parlar el MATEIX
    espai de noms: el de `fitxer.name`, relatiu a l'arrel del TENANT. El prefix del schema
    viu a `storage.location`, no al `name` (S03a · P2a), de manera que el disc s'ha de
    recórrer des de `storage.location` — no des de MEDIA_ROOT.
"""
import json
import os

from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django_tenants.utils import get_tenant_model, schema_context

from fhort.models_app.models import ModelFitxer

CHAIN_DIR = 'model_fitxers'


def _chain_roots(rows):
    """Union-find lleuger: retorna {chain_root_id: [row, ...]} seguint versio_anterior."""
    by_id = {r['id']: r for r in rows}
    root_of = {}

    def root(fid):
        path, visiting = [], set()
        while fid not in root_of:
            # Guard de cicle: versio_anterior hauria de ser acíclic, però aquesta comanda
            # existeix precisament per auditar dades corruptes. Un cicle es tanca sobre si
            # mateix i es reporta com a cadena (amb 0 o >1 caps), no penja la comanda.
            if fid in visiting:
                root_of[fid] = fid
                break
            visiting.add(fid)
            path.append(fid)
            pred = by_id[fid]['versio_anterior_id']
            if pred is None or pred not in by_id:
                root_of[fid] = fid
                break
            fid = pred
        base = root_of[fid]
        for p in path:
            root_of[p] = base
        return base

    chains = {}
    for r in rows:
        chains.setdefault(root(r['id']), []).append(r)
    return chains


def _audit_chains(rows):
    """Cadenes que violen la invariant (≠ 1 cap amb is_current)."""
    bad = []
    for root_id, chain in _chain_roots(rows).items():
        currents = [r['id'] for r in chain if r['is_current']]
        if len(currents) != 1:
            bad.append({
                'chain_root': root_id,
                'llargada': len(chain),
                'n_current': len(currents),
                'current_ids': currents,
                'ids': sorted(r['id'] for r in chain),
            })
    return sorted(bad, key=lambda c: c['chain_root'])


def _disk_names():
    """Noms de disc TRADUÏTS a l'espai de noms de `fitxer.name` (relatiu al tenant).

    L'arrel és `storage.location` (= MEDIA_ROOT/{schema} amb TenantFileSystemStorage), que és
    exactament l'origen de coordenades que `storage.path(name)` desfà. És la traducció inversa
    de `path`, i per això surt del storage i no d'una concatenació a mà: qualsevol canvi a
    MULTITENANT_RELATIVE_MEDIA_ROOT segueix els dos costats de la comparació alhora.

    Cal cridar-la DINS d'un `schema_context`: `location` es resol per tenant a cada accés.
    """
    root = default_storage.location
    found = set()
    for dirpath, _dirnames, filenames in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root)
        if CHAIN_DIR not in rel_dir.split(os.sep):
            continue
        for fn in filenames:
            rel = os.path.relpath(os.path.join(dirpath, fn), root)
            # El FileField sempre desa el `name` amb '/', sigui quin sigui l'os.sep.
            found.add(rel.replace(os.sep, '/'))
    return found


def _audit_disc(rows):
    db_names = {r['fitxer'] for r in rows if r['fitxer']}
    disk = _disk_names()
    return {
        'orfes': sorted(disk - db_names),          # bytes a disc, cap fila
        'fantasmes': sorted(db_names - disk),      # fila a BD, bytes absents
        'n_bd': len(db_names),
        'n_disc': len(disk),
    }


class Command(BaseCommand):
    help = 'Auditoria read-only de ModelFitxer: invariant de cadena + reconciliació disc↔BD.'

    def add_arguments(self, parser):
        parser.add_argument('--schema', help='Audita només aquest schema de tenant.')
        parser.add_argument('--json', action='store_true', dest='as_json',
                            help='Sortida JSON en lloc de text.')

    def handle(self, *args, **opts):
        known = list(get_tenant_model().objects
                     .exclude(schema_name='public')
                     .values_list('schema_name', flat=True))
        if opts['schema']:
            if opts['schema'] not in known:
                raise CommandError(
                    f"Schema '{opts['schema']}' no existeix. Tenants: {', '.join(known) or '(cap)'}")
            schemas = [opts['schema']]
        else:
            schemas = known

        report = {}
        for schema in schemas:
            with schema_context(schema):
                rows = list(ModelFitxer.objects.values(
                    'id', 'versio_anterior_id', 'is_current', 'fitxer'))
                report[schema] = {
                    'n_fitxers': len(rows),
                    'cadenes_invalides': _audit_chains(rows),
                    'disc': _audit_disc(rows),
                }

        if opts['as_json']:
            self.stdout.write(json.dumps(report, indent=2, ensure_ascii=False))
            return

        for schema, r in report.items():
            self.stdout.write(self.style.MIGRATE_HEADING(
                f"\n=== {schema} — {r['n_fitxers']} ModelFitxer"))

            bad = r['cadenes_invalides']
            if not bad:
                self.stdout.write(self.style.SUCCESS('  invariant is_current: OK'))
            else:
                self.stdout.write(self.style.ERROR(
                    f'  invariant is_current: {len(bad)} cadenes invàlides'))
                for c in bad:
                    self.stdout.write(
                        f"    cadena {c['chain_root']}: {c['llargada']} versions, "
                        f"{c['n_current']} is_current {c['current_ids']}")

            d = r['disc']
            self.stdout.write(f"  disc↔BD: {d['n_bd']} a BD, {d['n_disc']} a disc")
            for name in d['fantasmes']:
                self.stdout.write(self.style.ERROR(f'    FANTASMA (BD sense bytes): {name}'))
            for name in d['orfes']:
                self.stdout.write(self.style.WARNING(f'    ORFE (bytes sense BD): {name}'))
            if not d['fantasmes'] and not d['orfes']:
                self.stdout.write(self.style.SUCCESS('    reconciliació: OK'))
