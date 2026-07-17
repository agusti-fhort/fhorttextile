import client from './client';
const BASE = '/api/backoffice/v1/facturacio';

// Sèries de numeració — les crea l'operador; el codi no en sembra cap.
export const getSeries    = (params) => client.get(`${BASE}/series/`, { params });
export const createSerie  = (data)   => client.post(`${BASE}/series/`, data);
export const updateSerie  = (id, d)  => client.patch(`${BASE}/series/${id}/`, d);
export const deleteSerie  = (id)     => client.delete(`${BASE}/series/${id}/`);

// Tipus d'IVA — percentatge i menció legal són dada, no constants.
export const getTipusIva   = (params) => client.get(`${BASE}/tipus-iva/`, { params });
export const createTipusIva = (data)  => client.post(`${BASE}/tipus-iva/`, data);
export const updateTipusIva = (id, d) => client.patch(`${BASE}/tipus-iva/${id}/`, d);
export const deleteTipusIva = (id)    => client.delete(`${BASE}/tipus-iva/${id}/`);

// Factures. El client s'identifica per codi_tenant (clau natural de tot el backoffice).
export const getFactures   = (params) => client.get(`${BASE}/factures/`, { params });
export const getFactura    = (id)     => client.get(`${BASE}/factures/${id}/`);
export const createFactura = (data)   => client.post(`${BASE}/factures/`, data);
export const deleteFactura = (id)     => client.delete(`${BASE}/factures/${id}/`);
export const previewFactura= (id)     => client.get(`${BASE}/factures/${id}/preview/`);
export const emetreFactura = (id, serie) => client.post(`${BASE}/factures/${id}/emetre/`, { serie });
export const rectificarFactura = (id, motiu) => client.post(`${BASE}/factures/${id}/rectificar/`, { motiu });

// Línies de l'esborrany. El total el calcula el servidor (quantitat × preu_unit).
export const addLinia    = (id, data) => client.post(`${BASE}/factures/${id}/linia/`, data);
export const updateLinia = (id, data) => client.patch(`${BASE}/factures/${id}/linia/`, data);
export const deleteLinia = (id, liniaId) => client.delete(`${BASE}/factures/${id}/linia/`, { data: { id: liniaId } });

// Tancament de període: preview (dry-run) i generació dels DRAFTs recurrents.
const periodeParams = (period, codi) => ({ params: { period, ...(codi ? { client: codi } : {}) } });
export const previewPeriode = (period, codi) => client.get(`${BASE}/tancament-periode/`, periodeParams(period, codi));
export const generarPeriode = (period, codi) => client.post(`${BASE}/tancament-periode/`, { period, ...(codi ? { client: codi } : {}) });

// El PDF s'obre en una pestanya nova amb el token: és una GET autenticada, no un <a href>.
export const pdfFacturaUrl = (id) => `${client.defaults.baseURL}${BASE}/factures/${id}/pdf/`;
export const fetchPdf = (id) => client.get(`${BASE}/factures/${id}/pdf/`, { responseType: 'blob' });
