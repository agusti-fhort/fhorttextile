"""ARNÈS T8-ter · LA PASSEJADA DE LA BRUMÀ, contra dades REALS i amb ROLLBACK.

Reprodueix el cas que motiva el tram —un document que porta la FALDILLA i el SHORT— fent servir
l'extracció REAL de la sessió 113 del model 1323 (16/08), i comprova que:

  1 · les 7 files de la secció SHORT surten PROPOSADES a la peça 02, i les 11 de la faldilla no.
  2 · el guard de many-to-one ja NO desvincula el POM 962 (G1 faldilla · M1 short).
  3 · el confirm escriu a DUES peces i cada fila es queda el SEU valor.
  4 · «M1» ja no necessita la instància inventada `relaxed`.
  5 · la poda respecta fronteres.
  6 · CAP ESCRIPTURA SOBREVIU: es força rollback i les 18 files d'avui queden byte a byte.

    venv/bin/python manage.py shell -c "exec(open('scripts_tmp/arnes_bruma_t8ter.py').read())"
"""
import sys

from django.db import transaction
from django_tenants.utils import schema_context


class _Rollback(Exception):
    """Sortida de l'atomic. Mai és un error: és com aquest arnès no toca res."""


MODEL_ID, SESSIO_ID, PECA = 1323, 113, '02'
ok, ko = [], []


def check(cond, txt):
    (ok if cond else ko).append(txt)
    sys.stdout.write(f'  {"✓" if cond else "✗"} {txt}\n')


with schema_context('fhort'):
    from fhort.models_app.models import BaseMeasurement, ImportSession, Model, ModelGarment
    from fhort.models_app.extraction_views import (
        _apply_many_to_one_guard, _garment_de, _proposta_de_peca)

    model = Model.objects.get(pk=MODEL_ID)
    sessio = ImportSession.objects.get(pk=SESSIO_ID)
    peca = ModelGarment.objects.filter(model=model, codi=PECA).first()
    sys.stdout.write(f'\nModel {model.id} · {model.codi_intern} ({model.nom_prenda})\n')
    sys.stdout.write(f'Peça {PECA}: {peca.nom if peca else "NO EXISTEIX"}\n')

    # L'ESTAT D'AVUI, per poder-lo comparar després del rollback.
    abans = sorted(BaseMeasurement.objects.filter(model=model).values_list(
        'id', 'pom_id', 'capa', 'instancia', 'garment', 'base_value_cm', 'is_active', 'nom_fitxa'))
    sys.stdout.write(f'Estat d\'avui: {len(abans)} mesures base\n')

    # ── 1 · LA PROPOSTA, sobre l'extracció REAL ────────────────────────────────────────
    sys.stdout.write('\n1 · LA PROPOSTA SECCIÓ→PEÇA (extracció real de la sessió 113)\n')
    files = [dict(p) for p in sessio.poms_extrets]
    traca = _proposta_de_peca(model, files)
    proposades = [p for p in files if p.get('garment_proposat')]
    check(len(files) == 18, f'18 files a l\'extracció (n={len(files)})')
    check(len(proposades) == 7, f'7 files proposades al short (n={len(proposades)})')
    check({p['garment_proposat'] for p in proposades} == {PECA},
          f'totes proposades a la 02 ({ {p["garment_proposat"] for p in proposades} })')
    check(traca['seccions_sense_peca'] == [],
          f'cap secció sense peça ({traca["seccions_sense_peca"]})')
    codis = [p['codi_fitxa'] for p in proposades]
    check(codis == ['FR', 'FE', 'CT', 'M', 'M1', 'F1', 'FT'], f'i són {codis}')

    # ── 2 · EL GUARD DE MANY-TO-ONE ───────────────────────────────────────────────────
    sys.stdout.write('\n2 · EL GUARD DE MANY-TO-ONE (POM 962: G1 faldilla · M1 short)\n')
    del_962 = [p for p in files if p.get('pom_master_id') == 962]
    sys.stdout.write(f'    files del POM 962: {[(p["codi_fitxa"], p.get("garment_proposat")) for p in del_962]}\n')
    proves = [dict(p, actiu=True) for p in files]
    _apply_many_to_one_guard(proves)
    vius = [p for p in proves if p.get('pom_master_id') == 962]
    check(len(vius) == 2 and all(not p.get('many_to_one') for p in vius),
          'el POM 962 conserva les DUES files (abans les desvinculava totes dues)')

    # ── 3-5 · EL CONFIRM AMB DUES PECES, dins de l'atomic que es tomba ────────────────
    sys.stdout.write('\n3 · EL CONFIRM AMB DUES PECES (dins de rollback)\n')
    try:
        with transaction.atomic():
            # La decisió de la persona: confirmar el proposat. I «M1» recupera la instància
            # única — ja no li cal la inventada, que és el que aquest tram esborra.
            decidides = []
            for p in files:
                q = dict(p)
                if q.get('garment_proposat'):
                    q['garment'] = q['garment_proposat']
                    if q.get('codi_fitxa') == 'M1':
                        q['instancia'] = ''
                decidides.append(q)
            sessio.poms_extrets = decidides
            sessio.estat = 'MESURES'
            sessio.save(update_fields=['poms_extrets', 'estat', 'actualitzat_at'])

            # ⚠️ I ES TORNA A PASSAR PEL PAS 3, com fa el flux real (pas 2 decideix les peces,
            # pas 3 escriu els valors). Les mesures desades el 16/08 porten la identitat
            # D'ABANS —sense `garment`—, i una fila que canvia de peça DESPRÉS del pas 3 deixa
            # el seu valor enrere: la cel·la queda buida sense que ningú peti. És un ordre que
            # el wizard ja respecta i que aquest arnès ha de respectar també.
            from fhort.models_app.extraction_views import import_session_mesures_view
            from rest_framework.test import APIRequestFactory as _F, force_authenticate as _A
            valors_per_ordre = {}
            for m in (sessio.resultat or {}).get('mesures', []):
                if m.get('ordre') is not None:
                    valors_per_ordre.setdefault(m['ordre'], []).append(m)
            mesures = [{'ordre': o, 'talla_label': m['talla_label'], 'valor': m['valor']}
                       for o, ms in valors_per_ordre.items() for m in ms]
            _r = _F().patch(f'/api/v1/import-sessions/{sessio.token}/mesures/',
                            {'mesures': mesures}, format='json')
            from django.contrib.auth import get_user_model as _G
            _A(_r, user=_G().objects.filter(is_active=True).first())
            _res3 = import_session_mesures_view(_r, sessio.token)
            sys.stdout.write(f'    pas 3 re-desat → {_res3.status_code} '
                             f'({_res3.data.get("n_valors")} valors)\n')
            sessio.refresh_from_db()

            from fhort.models_app.extraction_views import import_session_confirmar_view
            from rest_framework.test import APIRequestFactory, force_authenticate
            from django.contrib.auth import get_user_model
            user = get_user_model().objects.filter(is_active=True).first()
            req = APIRequestFactory().post(
                f'/api/v1/import-sessions/{sessio.token}/confirmar/',
                {'container_choice': 'no_container', 'poda_choice': 'desactivar',
                 'manual_choice': 'sobreescriure'}, format='json')
            force_authenticate(req, user=user)
            res = import_session_confirmar_view(req, sessio.token)
            sys.stdout.write(f'    confirm → {res.status_code}\n')
            if res.status_code not in (200, 201):
                sys.stdout.write(f'    cos: {str(res.data)[:600]}\n')
            check(res.status_code == 201, f'confirm 201 (rebut {res.status_code})')
            sys.stdout.write(f'    resposta: podats={res.data.get("poms_podats")} '
                             f'conservats={res.data.get("poms_conservats")} '
                             f'buides={res.data.get("files_buides_desactivades")} '
                             f'bm={res.data.get("base_measurements")}\n')

            despres = BaseMeasurement.objects.filter(model=model)
            per_peca = {}
            for b in despres:
                per_peca.setdefault(b.garment, []).append(b)
            sys.stdout.write(f'    files per peça: '
                             f'{ {k or "(mare)": len(v) for k, v in per_peca.items()} }\n')
            vius = {k: [b for b in v if b.is_active] for k, v in per_peca.items()}
            sys.stdout.write(f'    VIVES per peça: '
                             f'{ {k or "(mare)": len(v) for k, v in vius.items()} }\n')
            check(set(per_peca) == {'', PECA}, f'dues peces escrites ({sorted(per_peca)})')
            check(len(vius.get(PECA, [])) == 7, f'7 vives a la 02 (n={len(vius.get(PECA, []))})')
            # 12, no 11: el POM 962 el fan servir LES DUES peces (G1 a la faldilla, M1 al
            # short), o sigui que la fila rància del short a la mare NO és òrfena —el document
            # segueix atribuint aquell POM a la mare per una altra fila— i es conserva amb raó.
            # Les altres 6 (CT·FT·FR·FE·F1·M) sí que cauen. És la poda per PECES ANOMENADES
            # funcionant: precisa, no aproximada.
            check(len(vius.get('', [])) == 12,
                  f'12 vives a la mare: cauen les 6 que el document ja no li atribueix '
                  f'(n={len(vius.get("", []))})')

            sys.stdout.write('\n4 · «M1» SENSE LA INSTÀNCIA INVENTADA\n')
            f962 = list(BaseMeasurement.objects.filter(model=model, pom_id=962, is_active=True))
            sys.stdout.write(f'    POM 962 → {[(b.nom_fitxa, b.garment, repr(b.instancia), b.base_value_cm) for b in f962]}\n')
            nou = [b for b in f962 if b.garment == PECA]
            ranci = [b for b in f962 if b.garment == '' and b.instancia == 'relaxed']
            check(len(nou) == 1 and nou[0].instancia == '',
                  'la fila del short neix amb instancia=\'\': la separa la FRONTERA, no un eix '
                  'inventat')
            check({b.garment for b in f962} == {'', PECA}, 'el POM 962 viu a les dues peces')
            check(len(ranci) == 1,
                  'i la «relaxed» del 16/08 hi queda: és la cicatriu del dany, i esborrar-la '
                  'no és feina d\'aquest import (el seu POM segueix atribuït a la mare)')

            sys.stdout.write('\n5 · LA PODA RESPECTA FRONTERES\n')
            mortes = [b for b in despres if not b.is_active]
            check(all(b.garment == '' for b in mortes),
                  f'la poda només toca les peces que el document anomena ({len(mortes)} baixes, '
                  f'totes a la mare)')

            raise _Rollback
    except _Rollback:
        sys.stdout.write('\n    ↩ ROLLBACK forçat.\n')

    # ── 6 · RES S'HA MOGUT ────────────────────────────────────────────────────────────
    sys.stdout.write('\n6 · EL CONTROL: les dades de l\'Agus, byte a byte\n')
    sessio.refresh_from_db()
    despres = sorted(BaseMeasurement.objects.filter(model=model).values_list(
        'id', 'pom_id', 'capa', 'instancia', 'garment', 'base_value_cm', 'is_active', 'nom_fitxa'))
    check(abans == despres, f'les {len(abans)} mesures base són idèntiques')
    check(sessio.estat == 'CONFIRMAT', f'la sessió 113 no s\'ha mogut (estat={sessio.estat})')
    check(len(sessio.poms_extrets) == 18 and not any(
        p.get('garment') for p in sessio.poms_extrets), 'i la seva extracció tampoc')

    sys.stdout.write(f'\n{"="*70}\nARNÈS BRUMÀ · {len(ok)} verds · {len(ko)} vermells\n')
    for t in ko:
        sys.stdout.write(f'  ✗ {t}\n')
