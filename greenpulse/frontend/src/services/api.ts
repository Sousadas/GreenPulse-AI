import axios from 'axios'

const api = axios.create({ 
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api' 
})

// Assets
export const fetchAssets = (type?: string) =>
  api.get('/assets', { params: type ? { asset_type: type } : {} }).then(r => r.data)
export const fetchAsset = (id: string) => api.get(`/assets/${id}`).then(r => r.data)
export const fetchAssetPerformance = (id: string) => api.get(`/assets/${id}/performance`).then(r => r.data)
export const fetchAssetHealth = (id: string) => api.get(`/assets/${id}/health`).then(r => r.data)
export const fetchAssetAlerts = (id: string) => api.get(`/assets/${id}/alerts`).then(r => r.data)

// Generation
export const fetchSolarGeneration = () => api.get('/solar/generation').then(r => r.data)
export const fetchWindGeneration = () => api.get('/wind/generation').then(r => r.data)

// Weather
export const fetchWeather = (location?: string) =>
  api.get('/weather/current', { params: location ? { location } : {} }).then(r => r.data)
export const fetchWeatherForecast = (hours = 24) => api.get(`/weather/forecast?hours=${hours}`).then(r => r.data)

// Grid
export const fetchGridStatus = () => api.get('/grid/status').then(r => r.data)
export const fetchGridRecommendation = () => api.get('/grid/recommendation').then(r => r.data)

// Forecast
export const fetchForecast = (hours = 24, type = 'HYBRID') =>
  api.get(`/forecast?hours=${hours}&type=${type}`).then(r => r.data)

// Alerts
export const fetchAlerts = (severity?: string) =>
  api.get('/alerts', { params: severity ? { severity } : {} }).then(r => r.data)

// Maintenance
export const fetchMaintenanceRisks = () => api.get('/maintenance/risks').then(r => r.data)

// AI
export const postAIQuery = (question: string) =>
  api.post('/ai/query', { question }).then(r => r.data)

// Simulation
export const postSimulationFault = (scenario: string, intensity = 1.0) =>
  api.post('/simulation/fault', { scenario, intensity }).then(r => r.data)
export const fetchSimulationStatus = () => api.get('/simulation/status').then(r => r.data)

// System
export const fetchSystemHealth = () => axios.get('/health').then(r => r.data)

export default api
