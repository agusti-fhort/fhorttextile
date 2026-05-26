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

    # Model real no té camp 'client' (FK); usa codi_client (CharField) directament.
    # Defensiu: si camps no hi son o estan buits, sortim sense fer res.
    client_id = getattr(instance, 'client_id', None)
    codi_client_raw = getattr(instance, 'codi_client', None)
    if not (client_id or codi_client_raw) or not getattr(instance, 'any', None) or not getattr(instance, 'temporada', None):
        return

    # Codi client: del camp directe (si existeix), o via FK client (si el schema l'afegeix més endavant)
    codi_client = codi_client_raw
    if not codi_client and client_id:
        try:
            from fhort.accounts.models import Client
            client = Client.objects.get(pk=client_id)
            codi_client = getattr(client, 'codi_client', None) or getattr(client, 'code', None)
            if not codi_client:
                codi_client = str(client)[:3].upper()
        except Exception:
            codi_client = None

    if not codi_client:
        return

    codi_client = codi_client.strip().upper()

    # MAX sequencial per (codi_client, any, temporada)
    # Si el schema futur afegeix un FK 'client', migrar a client_id; per ara
    # usem codi_client (CharField) que és la chave de negoci real al Model.
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT MAX(sequencial)
            FROM models_app_model
            WHERE codi_client = %s
              AND "any" = %s
              AND temporada = %s
        """, [codi_client, instance.any, instance.temporada])
        row = cursor.fetchone()

    seguent = 1 if (not row or row[0] is None) else int(row[0]) + 1

    any2 = str(instance.any)[-2:].zfill(2)
    seq4 = str(seguent).zfill(4)

    instance.sequencial = seguent
    # Model no té camp 'codi' (té 'codi_intern'). Generem codi_intern si està buit
    # — si l'usuari ja l'ha proporcionat (com a roholi8r9k), no el sobreescrivim.
    if not getattr(instance, 'codi_intern', None):
        instance.codi_intern = f"{codi_client}-{any2}-{instance.temporada}-{seq4}"


@receiver(post_save)
def sincronitzar_size_fitting(sender, instance, created, **kwargs):
    """
    Crea automàticament el Size & Fitting quan es crea un Model nou.
    Camps de configuració (garment_type, size_system, etc.) NO es dupliquen
    al SF: viuen al Model i s'accedeixen via la FK sf.model.X.

    Skip si Model.responsable és None (creat_per és required + PROTECT
    al SizeFitting). En aquest cas l'SF es pot crear manualment més tard.
    """
    try:
        Model = _get_model_class()
    except Exception:
        return

    if sender is not Model:
        return

    if not created:
        return

    if not instance.responsable_id:
        return  # No podem crear SF sense creat_per

    try:
        from fhort.fitting.models import SizeFitting
        if SizeFitting.objects.filter(model=instance).exists():
            return
        numero = 1
        codi = f"{instance.codi_intern}-SF{numero}"
        SizeFitting.objects.create(
            model=instance,
            numero=numero,
            codi=codi,
            tipus='Proto',
            estat='Pendent',
            base_tancada=False,
            creat_per_id=instance.responsable_id,
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"No s'ha pogut crear SF per {instance}: {e}")


@receiver(post_save)
def actualitzar_darrera_activitat(sender, instance, **kwargs):
    """
    A cada save d'un Model, actualitza darrera_activitat = now().
    Usa queryset.update() per bypassar signals → cap recursió infinita.
    """
    try:
        Model = _get_model_class()
    except Exception:
        return

    if sender is not Model:
        return

    from django.utils import timezone
    Model.objects.filter(pk=instance.pk).update(darrera_activitat=timezone.now())
