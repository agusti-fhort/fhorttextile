// Ordre de talles a la UI — llei S24b (2026-07-22): l'ordre el mana el SizeSystem.
//
// El run persistit del model (`size_run_model`) ÉS la seqüència del sistema retallada al
// subconjunt que el model fabrica: des de la porta única d'escriptura del backend
// (`run_del_model`), el que arriba ja ve ordenat per `SizeDefinition.ordre`. Per això ordenar
// pel run és, avui, ordenar pel sistema.
//
// ⚠️ DEUTE ANOTAT: mentre quedin runs desordenats a la BD que el sanejament
// (`normalitza_size_run`) encara no hagi tocat, aquestes vistes els pintaran desordenats. La
// correcció completa demanaria que l'endpoint exposés les etiquetes del SizeSystem, cosa que
// avui no fa (`fitting/serializers.py`, `get_model` només envia size_run_model i base). No es
// fa aquí: seria una peça d'API, no de presentació.

// Separador `·` (U+00B7), amb `;` tolerat — mateixa normalització que el backend.
export function parseSizeRun(sizeRun) {
  return (sizeRun || '').replace(/;/g, '·').split('·').map(s => s.trim()).filter(Boolean)
}

// Ordena les talles PRESENTS segons el run del model. Mai alfabètic. Les talles presents que
// no surtin al run van al final (no es perden mai: si es descarten, desapareixen dades de la
// graella sense que ningú ho digui).
export function orderedSizes(sizeRun, present) {
  const run = parseSizeRun(sizeRun)
  const ordered = run.filter(s => present.has(s))
  const extras = [...present].filter(s => !run.includes(s))
  return [...ordered, ...extras]
}
