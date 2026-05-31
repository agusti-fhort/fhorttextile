"""
tasks/signals.py — Signals retirats a Sprint 0 (branca rígida del gate).

Els dos receivers globals (after_save_model_task / after_delete_model_task), que
derivaven Model.fase_actual des de les tasques i desbloquejaven la cadena
'Bloquejada', s'han eliminat. L'únic amo de fase_actual és fitting.advance_phase.
"""
