import axios from 'axios'

// L'URL du backend. Modifiable via un fichier .env (VITE_API_URL=...).
const API = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 60000,
})

export const getHealth    = ()                 => API.get('/health').then(r => r.data)
export const getForecast  = (hours = 48)       => API.get('/predict',   { params: { hours } }).then(r => r.data)
export const getZones     = ()                 => API.get('/zones').then(r => r.data)
export const getZoneShapes = ()                 => API.get('/zone-shapes').then(r => r.data)
export const getMeters    = ()                 => API.get('/meters').then(r => r.data)
export const getAlerts    = (hours = 168, top = 20) => API.get('/alerts', { params: { hours, top } }).then(r => r.data)
export const getAnomalies = (hours = 168)      => API.get('/anomalies', { params: { hours } }).then(r => r.data)
export const getModels    = ()                 => API.get('/models').then(r => r.data)

export default API