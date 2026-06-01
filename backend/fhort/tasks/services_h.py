"""JUBILAT (Sprint B — motor de planificació).

La lògica antiga d'aquest mòdul (Sprint H: `compute_plan` / `compute_and_save_plan`,
models EN SÈRIE amb capacitat agregada `technician_count × minuts/dia`, sense festius
ni assignee ni calendari real) ha estat SUBSTITUÏDA pel motor determinista per-tècnic
sobre el calendari laboral:

    fhort/planning/scheduler_service.py   → schedule(model_task_qs, save=...)
    fhort/planning/plan_service.py        → compute_and_save / preview / apply

Es conserven, intactes i reaprofitats pel motor nou:
    - PlanSnapshot (fhort/tasks/models.py) — previsió persistida (previst-vs-real).
    - El lookup de durada amb Welford (services_g.lookup_estimated_minutes / services_i).

Aquest fitxer es manté buit a propòsit (sense codi viu) per deixar constància de la
jubilació, seguint el patró del projecte (cf. tasks/signals.py).
"""
