import { useState } from 'react'
import Dashboard from './pages/Dashboard'
import TransactionDetails from './pages/TransactionDetails'
import CustomerView from './pages/CustomerView'
import './styles.css'

export default function App() {
  const [selected, setSelected] = useState(null)
  const [customer, setCustomer] = useState('')
  if (selected) return <TransactionDetails id={selected} onBack={() => setSelected(null)} />
  if (customer) return <CustomerView customerId={customer} onBack={() => setCustomer('')} />
  return <Dashboard onSelect={setSelected} onCustomer={setCustomer} />
}
