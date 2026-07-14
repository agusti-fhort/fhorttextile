import client from './client';
const BASE = '/api/backoffice/v1/legal';

// F4 P-LEGAL: documents legals amb hash + acceptacions probatòries.
export const getLegalDocs      = ()      => client.get(`${BASE}/documents/`);
export const getLegalDoc       = (id)    => client.get(`${BASE}/documents/${id}/`);
export const createLegalDoc    = (data)  => client.post(`${BASE}/documents/`, data);
export const updateLegalDoc    = (id, d) => client.patch(`${BASE}/documents/${id}/`, d);

export const createLegalVersion= (data)  => client.post(`${BASE}/versions/`, data);
export const updateLegalVersion= (id, d) => client.patch(`${BASE}/versions/${id}/`, d);
export const deleteLegalVersion= (id)    => client.delete(`${BASE}/versions/${id}/`);
export const publishLegalVersion=(id)    => client.post(`${BASE}/versions/${id}/publish/`, {});

export const getLegalAcceptances=(params)=> client.get(`${BASE}/acceptances/`, { params });
