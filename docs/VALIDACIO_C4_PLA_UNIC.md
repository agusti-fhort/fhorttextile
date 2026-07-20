# Validació manual — C4 Font única d'ordre (Planificació → Board + Gantt)

> Sprint 3 FRONTS (F1·F2·F3=C4). Test manual guiat per a la validació visual d'Agus a staging
> DESPRÉS del deploy. Cap push/deploy des d'agent.

## Precondició de deploy (OBLIGATÒRIA abans de validar)

C4 afegeix el camp `Model.reanchored_by_start` (migració **0057**). El codi backend
(`by_model`, `gantt_view`, `open-task`, `plan/reorder`) ja el llegeix/escriu, així que:

```
# des de backend/ amb el venv actiu
python manage.py migrate_schemas            # aplica 0057 a TOTS els schemes (mai --schema)
# auditar que la columna existeix al tenant abans de reiniciar:
#   \d models_app_model  → ha d'incloure reanchored_by_start
sudo systemctl restart ftt-staging.service  # carrega el codi nou DESPRÉS de migrar
```

Ordre estricte: **migrar → auditar columna → reiniciar**. Si es reinicia abans de migrar,
`by_model`/`gantt` fan 500 (columna inexistent).

## Llei que es valida

Una sola font d'ordre = el **pla materialitzat** (`planned_start`/`planned_end` que escriu
l'scheduler des de prioritat + override manual + fets reals). Planificació és l'ÚNIC editor;
Board i Gantt són **lectors** — no reordenen pel seu compte.

## Passos

### T1 — Reorder a Planificació es reflecteix a Board i Gantt
1. Planificació → tab *Assignació*. En una cua de tècnic amb ≥2 models, arrossega un model
   amunt/avall.
2. **Esperat**: la llista es reordena i es desa (toast "ordre desat").
3. Ves al Dashboard (Board, tab 1): l'ordre dels models a les columnes segueix el nou pla
   (min `planned_start`). Ves al Gantt (tab 2, ordre = **Pla**): les files segueixen el mateix
   ordre. Cap dels dos reordena diferent.
4. **Fallaria si**: Board o Gantt mostressin un ordre distint del de Planificació.

### T2 — Iniciar una tasca puja el model i el marca amb "+"
1. Al Board, agafa un model de la cua (no el primer) i entra-hi; inicia la seva tasca
   (p.ex. "Mesurar prenda") — auto-start Pending→InProgress.
2. **Esperat (C3+C4)**: en iniciar, el pla del tècnic es reancora al present → aquest model
   puja a dalt de la cua.
3. Torna a Planificació / Board / Gantt: el model apareix amunt i amb un **"+"** daurat
   discret al costat del codi (a les **tres** superfícies).
4. Al Board, en entrar la seva targeta té **anell daurat** (ressaltat d'actiu) i queda
   **enfocada** (auto-scroll). Al Gantt, en carregar, l'scroll vertical baixa fins al primer
   model amb feina viva (els acabats queden amunt, visibles pujant).
5. Torna a Planificació i fes un **reorder manual** de la cua: el **"+"** del model desapareix
   (el reorder és l'ACK del planificador).
6. **Fallaria si**: iniciar no mogués el model; o el "+" no aparegués a alguna superfície; o no
   s'esborrés en reordenar.

### T3 — Només els planificats existeixen
1. Un model **sense cap tasca amb `planned_start`** (no assignat/planificat) **no** apareix ni
   al Board ni al Gantt. Sí a la llista de Planificació (pendents).
2. En assignar-li/iniciar-li una tasca, entra al Board i al Gantt.

### T4 — Vistes alternatives del Gantt segueixen disponibles
1. Al Gantt, el selector *Ordena per* té **Pla** (per defecte) + Lliurament / Pròxima fita /
   Fase com a alternatives explícites. Canviar-les reordena NOMÉS la vista del Gantt (elecció
   d'usuari), no toca el pla.

## Notes
- El marcador "+" és efímer per disseny: viu des de l'inici real fins al següent reorder manual.
- El Gantt segueix llegint dades del pla; la columna `predicted_*` NO s'ha tocat (la usen 4
  consumidors més: viabilitat a ModelSheet/Planning/Informes/DashboardGov — V2).
