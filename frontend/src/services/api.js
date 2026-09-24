import axios from 'axios'
/* API Settings */
const api = axios.create({ baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000' })

export const getDashboard = () => api.get('/dashboard')
export const getTransactions = (params) => api.get('/transactions', { params })
export const getTransaction = (id) => api.get(`/transactions/${id}`)
export const getBalance = (customerId) => api.get(`/customers/${customerId}/balance`)
export const getCustomerTransactions = (customerId, params) => api.get(`/customers/${customerId}/transactions`, { params })
export const retryTransaction = (id) => api.post(`/transactions/${id}/retry`)
export const createTransaction = (payload) => api.post('/transactions', payload)
export default api
