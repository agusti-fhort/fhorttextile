"""
models_app/signals.py — Signals Django per al Model.
Equivalent als Server Scripts de Frappe:
  - before_insert: genera codi + sequencial
  - after_save: sincronitza Size & Fitting
"""
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver


def _get_model_class():
    from fhort.models_app.models import Model
    return Model


@receiver(pre_save)
def generar_codi_model(sender, instance, **kwargs):
    """
    Genera sequencial i codi {CLI}-{YY}-{TT}-{NNNN} al crear un Model nou.
    Equivalent al Server Script 'Model - Before Insert · Codificació'.
    """
    try:
        Model = _get_model_class()
    except Exception:
        return

    if sender is not Model:
        return

    if instance.pk:  # Ja existeix, no regenerar el codi
        return

    if not instance.client_id or not instance.any or not instance.temporada:
        return  # Sense dades suficients, la validació ho aturarà

    # Llegir codi client
    try:
        from fhort.accounts.models import Client
        client = Client.objects.get(pk=instance.client_id)
        codi_client = getattr(client, 'codi_client', None) or getattr(client, 'code', None)
        if not codi_client:
            # Intenta des del Customer linked
            codi_client = str(client)[:3].upper()
    except Exception:
        codi_client = None

    if not codi_client:
        return

    codi_client = codi_client.strip().upper()

    # MAX sequencial per client + any + temporada
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT MAX(sequencial)
            FROM models_app_model
            WHERE client_id = %s
              AND any = %s
              AND temporada = %s
        """, [instance.client_id, instance.any, instance.temporada])
        row = cursor.fetchone()

    seguent = 1 if (not row or row[0] is None) else int(row[0]) + 1

    any2 = str(instance.any)[-2:].zfill(2)
    seq4 = str(seguent).zfill(4)

    instance.sequencial = seguent
    instance.codi = f"{codi_client}-{any2}-{instance.temporada}-{seq4}"


@receiver(post_save)
def sincronitzar_size_fitting(sender, instance, created, **kwargs):
    """
    Crea automàticament el Size & Fitting quan es crea un Model nou.
    Equivalent al Server Script 'Model - After Insert · Crear SF'.
    """
    try:
        Model = _get_model_class()
    except Exception:
        return

    if sender is not Model:
        return

    if not created:
        return

    # Crear SF si no existeix
    try:
        from fhort.fitting.models import SizeFitting
        if not SizeFitting.objects.filter(model=instance).exists():
            sf = SizeFitting.objects.create(
                model=instance,
                estat='Pendent',
                base_tancada=False,
            )
            # Copiar camps del model al SF
            fields_to_copy = [
                'garment_type_id', 'garment_group_id', 'grading_rule_set_id',
                'size_system_id', 'base_size_label', 'size_run_model',
            ]
            update_fields = {}
            for f in fields_to_copy:
                val = getattr(instance, f, None)
                if val is not None:
                    sf_field = f.replace('_id', '')
                    try:
                        setattr(sf, f, val)
                        update_fields[f] = val
                    except Exception:
                        pass
            if update_fields:
                SizeFitting.objects.filter(pk=sf.pk).update(**update_fields)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"No s'ha pogut crear SF per {instance}: {e}")
