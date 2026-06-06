"""
tasks/signals.py — Signals retirats a Sprint 0 (branca rígida del gate).

Els dos receivers globals (after_save_model_task / after_delete_model_task), que
derivaven Model.fase_actual des de les tasques i desbloquejaven la cadena
'Bloquejada', s'han eliminat. L'únic amo de fase_actual és fitting.advance_phase.
"""
from django.dispatch import Signal

# Sprint 4: emès pel producte quan un model inicia la primera tasca (meritació).
# Payload (tot mastegat per l'emissor a 4.2; el receptor no llegeix res del tenant):
#   codi_client (str, 3), period (str 'YYYY-MM'), opaque_ref (uuid), merited_at (datetime)
model_consumption_started = Signal()
