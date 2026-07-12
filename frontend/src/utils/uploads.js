// MIRALL de `ALLOWED_UPLOAD_EXTENSIONS` (backend/fhort/models_app/services_fitxers.py:33-45).
//
// No existeix cap endpoint de configuració que serveixi la whitelist al client, i crear-ne un
// per a una llista d'extensions seria una superfície nova (auth, cache, versionat) per a una
// dada que canvia un cop l'any. La duplicació es paga aquí, en UN sol lloc: si la whitelist del
// backend canvia, es canvia aquesta línia i enlloc més.
//
// El backend valida igualment (`validate_upload`, D12/D18): aquest `accept` és ergonomia del
// diàleg de fitxers, no un guard de seguretat. Un usuari pot forçar-hi qualsevol fitxer i rebrà
// un 400.
//
// NO s'aplica a: l'input d'Importar Garment de l'editor (filtra .svg/.dxf pel seu propòsit),
// els inputs de logo (imatges) ni els assistents d'importació de dades (.xlsx de mesures).
export const UPLOAD_ACCEPT =
  '.ftt,.pdf,.dxf,.svg,.rul,.txt,.png,.jpg,.jpeg,.webp,.gif,.xlsx,.xls'
