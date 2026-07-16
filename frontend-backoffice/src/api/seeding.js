import client from './client';
const BASE = '/api/backoffice/v1';

// F3 P-FREE-SEED: perfils de sembra (què se sembra a un tenant Free en donar-lo d'alta).
export const getSeedProfiles  = ()      => client.get(`${BASE}/perfils-sembra/`);
export const getSeedProfile   = (id)    => client.get(`${BASE}/perfils-sembra/${id}/`);
export const createSeedProfile= (data)  => client.post(`${BASE}/perfils-sembra/`, data);
export const updateSeedProfile= (id, d) => client.patch(`${BASE}/perfils-sembra/${id}/`, d);
export const deleteSeedProfile= (id)    => client.delete(`${BASE}/perfils-sembra/${id}/`);

// Metadades dels blocs: etiqueta, dependències i comptadors reals de fhort.
export const getSeedBlocksMeta= ()      => client.get(`${BASE}/perfils-sembra/blocs-meta/`);
