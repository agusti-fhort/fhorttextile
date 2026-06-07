import client from './client';
const BASE = '/api/backoffice/v1';

// Catàleg de serveis
export const getServeis     = (params) => client.get(`${BASE}/serveis/`, { params });
export const getServei      = (id)     => client.get(`${BASE}/serveis/${id}/`);
export const createServei   = (data)   => client.post(`${BASE}/serveis/`, data);
export const updateServei   = (id, d)  => client.patch(`${BASE}/serveis/${id}/`, d);
export const deleteServei   = (id)     => client.delete(`${BASE}/serveis/${id}/`);

// Contractes per tenant
export const getContractes  = (params) => client.get(`${BASE}/contractes/`, { params });
export const getContracte   = (id)     => client.get(`${BASE}/contractes/${id}/`);
export const createContracte= (data)   => client.post(`${BASE}/contractes/`, data);
export const updateContracte= (id, d)  => client.patch(`${BASE}/contractes/${id}/`, d);
export const deleteContracte= (id)     => client.delete(`${BASE}/contractes/${id}/`);
