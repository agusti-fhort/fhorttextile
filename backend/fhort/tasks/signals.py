"""
tasks/signals.py — Signals retirats a Sprint 0 (branca rígida del gate).

Els dos receivers globals (after_save_model_task / after_delete_model_task), que
derivaven Model.fase_actual des de les tasques i desbloquejaven la cadena
'Bloquejada', s'han eliminat: cap SIGNAL deriva fase_actual.
Avui fase_actual s'escriu des de diversos punts: l'avanç de gate
(tasks.advance_phase_gate / regress_phase), fitting.advance_phase (de moment),
un automatisme a tasks.services_c (Pending→Dev en arrencar la primera tasca) i la
inicialització en crear/clonar el model. La cadena D-3 unifica l'amo a l'avanç de gate.
"""
from django.dispatch import Signal

# Sprint 4: emès pel producte quan un model inicia la primera tasca (meritació).
# Payload (tot mastegat per l'emissor a 4.2; el receptor no llegeix res del tenant):
#   codi_client (str, 3), period (str 'YYYY-MM'), opaque_ref (uuid), merited_at (datetime)
model_consumption_started = Signal()
