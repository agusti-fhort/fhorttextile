import json

BASE = '/var/www/fhort-textile/backend/data/import_ops'

with open(f'{BASE}/Model.json', encoding='utf-8') as f:
    models_data = json.load(f)

print(f'Models trobats al JSON: {len(models_data)}')

from fhort.models_app.models import Model
from fhort.pom.models import GarmentType
from fhort.accounts.models import UserProfile

default_gt = GarmentType.objects.first()
default_resp = UserProfile.objects.first()
print(f'Garment type: {default_gt}')
print(f'Responsable: {default_resp}')

PRIORITAT_MAP = {
    'Baixa': 1, 'Normal': 3, 'Alta': 4, 'Urgent': 5,
    'Low': 1, 'Medium': 3, 'High': 4, 'Critical': 5,
}

creats = 0
errors = 0

for m in models_data:
    try:
        prioritat_raw = m.get('prioritat') or 'Normal'
        try:
            prioritat = int(prioritat_raw)
        except (ValueError, TypeError):
            prioritat = PRIORITAT_MAP.get(prioritat_raw, 3)

        gt = None
        gt_nom = m.get('garment_type') or m.get('tipologia_model')
        if gt_nom:
            gt = GarmentType.objects.filter(nom_client__icontains=gt_nom).first()
        if not gt:
            gt = default_gt

        obj, created = Model.objects.get_or_create(
            codi_intern=m.get('name', ''),
            defaults={
                'codi_client':      m.get('codi_client') or m.get('name', ''),
                'nom_prenda':       m.get('nom_prenda') or m.get('name', 'Sense nom'),
                'descripcio':       m.get('descripcio') or '',
                'color_referencia': m.get('color_referencia') or '',
                'temporada':        m.get('temporada') or 'SS',
                'any':              int(m.get('any') or 26),
                'estat':            m.get('estat') or 'Nou',
                'fase_actual':      m.get('fase_actual') or '',
                'prioritat':        prioritat,
                'codi_tenant':      'FHT',
                'sequencial':       int(m.get('sequencial') or 1),
                'garment_type':     gt,
                'responsable':      default_resp,
            }
        )
        if created:
            creats += 1
            print(f'  ✓ {obj.codi_intern} — {obj.nom_prenda}')
        else:
            print(f'  · {obj.codi_intern} ja existia')
    except Exception as e:
        errors += 1
        print(f'  ✗ {m.get("name")}: {e}')

print(f'\nResultat: {creats} creats, {errors} errors')
print(f'Total models a BD: {Model.objects.count()}')
