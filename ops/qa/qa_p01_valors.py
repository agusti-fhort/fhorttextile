"""P0.1 — el camí sencer d'un valor: escriure → BD → tornar-lo a llegir.

Sospita del brief: «Definició ensenyava unes files i la consulta unes ALTRES, tot “—”
(dues poblacions)». Aquest script el recorre amb les vistes REALS i mesura on es trenca:

    poms-suggerits   ← el que Definició POM pinta quan la taula encara és verge
    gravar-pom       ← el gest de Gravar
    taula-mesures    ← el que llegeixen Definició (ja materialitzada) i la Consulta
    BaseMeasurement  ← el que hi ha de debò a la BD

Sobre un model PROPI que es crea i s'esborra. **MAI el MILEY (1308)** ni cap model de ningú.

    backend/venv/bin/python ../ops/qa/qa_p01_valors.py
"""
import os
import pathlib
import sys

BACKEND = pathlib.Path(__file__).resolve().parents[2] / 'backend'
sys.path.insert(0, str(BACKEND))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fhort.settings')

import django                                     # noqa: E402
django.setup()

from django.contrib.auth import get_user_model    # noqa: E402
from django_tenants.utils import schema_context   # noqa: E402
from rest_framework.test import APIClient         # noqa: E402

HOST = {'HTTP_HOST': 'staging.fhorttextile.tech'}
MILEY = 1308
VALOR = 42.5


def main():
    problemes = []
    with schema_context('fhort'):
        from fhort.models_app.models import BaseMeasurement, Model
        from fhort.pom.models import SizeSystem
        from fhort.tasks.models import Customer, GarmentTypeItem

        u = get_user_model().objects.filter(is_superuser=True).first()
        c = APIClient()
        c.force_authenticate(user=u)

        cust = Customer.objects.get(codi='BRW')
        sysx = SizeSystem.objects.prefetch_related('talles').get(codi='WOMAN_BRW_01')
        talles = [d.etiqueta for d in sysx.talles.all().order_by('ordre')]
        item = (GarmentTypeItem.objects.filter(active=True, garment_type__isnull=False,
                                               pom_maps__isnull=False)
                .select_related('garment_type').distinct().order_by('id').first())
        if item is None:
            print('✗ cap item amb POMs mapats'); return 1

        r = c.post('/api/v1/models/create-wizard/', {
            'customer_id': cust.id, 'year': 2026, 'season': 'FW', 'ref_client': 'QA-P01',
            'target': 'WOMAN', 'garment_type_id': item.garment_type_id,
            'garment_type_item_id': item.id, 'size_system_id': sysx.id,
            'size_run': '·'.join(talles), 'base_size': talles[len(talles) // 2],
        }, format='json', **HOST)
        if r.status_code not in (200, 201):
            print(f'✗ no s\'ha pogut crear el model de prova: {r.status_code} {r.content[:200]}')
            return 1
        mid = r.json().get('id')
        assert mid != MILEY
        print(f'  · model de prova {mid} · item {item.name} · base {talles[len(talles)//2]}')

        try:
            # ── 1 · què pinta Definició POM quan encara és verge ────────────
            sug = c.get(f'/api/v1/models/{mid}/poms-suggerits/', **HOST).json().get('poms', [])
            taula0 = c.get(f'/api/v1/models/{mid}/taula-mesures/', **HOST).json().get('rows', [])
            print(f'  · poms-suggerits={len(sug)} · taula-mesures={len(taula0)} (verge)')
            if not sug:
                print('✗ l\'item no suggereix cap POM: el fum no pot continuar'); return 1

            pom = sug[0]
            pom_id = pom['pom_id']

            # ── 1b · OBRIR LA TASCA POM ────────────────────────────────────
            # El gest real: entrar a `?mode=entry` obre la tasca (ModelSheet:492). Sense això
            # `gravar-pom` respon 400 «Cal obrir la tasca POM abans de gravar-la» — que és
            # exactament el que aquest fum va trobar la primera vegada.
            ro = c.post(f'/api/v1/models/{mid}/open-task/', {'code': 'pom'}, format='json', **HOST)
            print(f'  · open-task pom → HTTP {ro.status_code}')
            if ro.status_code not in (200, 201):
                problemes.append(f'open-task pom → HTTP {ro.status_code}: {str(ro.content[:200])}')

            # ── 2 · GRAVAR un valor, com fa el botó Gravar ──────────────────
            r = c.post(f'/api/v1/models/{mid}/gravar-pom/', {
                'measurements': [{'pom_id': pom_id, 'base_value_cm': VALOR}],
                'rules': [],
            }, format='json', **HOST)
            if r.status_code not in (200, 201):
                problemes.append(f'gravar-pom → HTTP {r.status_code}: {str(r.content[:300])}')
            else:
                print(f'  ✓ gravat · POM {pom.get("pom_code")} = {VALOR}')

            # ── 3 · què hi ha a la BD ──────────────────────────────────────
            bms = list(BaseMeasurement.objects.filter(model_id=mid))
            meu = [b for b in bms if b.pom_id == pom_id]
            if not meu:
                problemes.append('a la BD no hi ha cap BaseMeasurement per al POM gravat')
            elif float(meu[0].base_value_cm or 0) != VALOR:
                problemes.append(f'la BD guarda {meu[0].base_value_cm}, no {VALOR}')
            else:
                print(f'  ✓ BD · BaseMeasurement {meu[0].id} = {meu[0].base_value_cm} '
                      f'(capa={meu[0].capa!r} instancia={meu[0].instancia!r})')

            # ── 4 · què torna la LECTURA (Definició materialitzada + Consulta) ──
            taula = c.get(f'/api/v1/models/{mid}/taula-mesures/', **HOST).json()
            rows = taula.get('rows', [])
            fila = next((x for x in rows if x.get('pom_id') == pom_id), None)
            if fila is None:
                problemes.append(f'taula-mesures NO retorna el POM gravat '
                                 f'({len(rows)} files, cap amb pom_id={pom_id}) '
                                 f'→ DUES POBLACIONS: s\'escriu a una i es llegeix d\'una altra')
            elif fila.get('base_value_cm') in (None, ''):
                problemes.append(f'taula-mesures retorna la fila amb el valor BUIT '
                                 f'(«—»): {fila.get("base_value_cm")!r}')
            else:
                print(f'  ✓ lectura · taula-mesures torna {fila.get("base_value_cm")} '
                      f'per al mateix POM ({len(rows)} files)')

            # ── 5 · el F5: tornar-hi en fred ───────────────────────────────
            c2 = APIClient(); c2.force_authenticate(user=u)
            rows2 = c2.get(f'/api/v1/models/{mid}/taula-mesures/', **HOST).json().get('rows', [])
            fila2 = next((x for x in rows2 if x.get('pom_id') == pom_id), None)
            if not fila2 or fila2.get('base_value_cm') in (None, ''):
                problemes.append('després de rellegir en fred (F5) el valor ja no hi és')
            else:
                print(f'  ✓ F5 · el valor segueix: {fila2.get("base_value_cm")}')
        finally:
            c.delete(f'/api/v1/models/{mid}/delete/', **HOST)
            queda = Model.objects.filter(pk=mid).exists()
            print(f'  {"✗" if queda else "✓"} model de prova esborrat')

    print()
    if problemes:
        print(f'✗ {len(problemes)} problema(es):')
        for x in problemes:
            print(f'   · {x}')
        return 1
    print('✓ P0.1 verd · el valor sobreviu escriptura → BD → lectura → F5')
    return 0


if __name__ == '__main__':
    sys.exit(main())
