import { useEffect, useState } from 'react'
import { getDashboard, getTransactions, retryTransaction } from '../services/api'
import TransactionTable from '../components/TransactionTable'
import StatusBadge from '../components/StatusBadge'

export default function Dashboard({ onSelect, onCustomer }) {
  const [counts, setCounts] = useState({})
  const [items, setItems] = useState([])
  const [status, setStatus] = useState('')
  const [type, setType] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  async function load() {
    try {
      const [dashboard, transactions] = await Promise.all([
        getDashboard(), getTransactions({ status: status || undefined, type: type || undefined, page_size: 20 })
      ])
      setCounts(dashboard.data); setItems(transactions.data.items); setError('')
    } catch (e) { setError(e.response?.data?.detail || 'Unable to load transactions') }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [status, type])
  useEffect(() => { const timer = setInterval(load, 3000); return () => clearInterval(timer) }, [status, type])

  async function retry(id) {
    await retryTransaction(id)
    load()
  }

  return <main>
    <div className="page-head"><div><h1>Transaction Operations</h1><p>Local processing queue and customer balance monitor</p></div><form onSubmit={e => { e.preventDefault(); const id = e.currentTarget.customer.value.trim(); if (id) onCustomer(id) }}><input name="customer" placeholder="Customer ID"/><button className="primary" type="submit">View customer</button></form></div>
    <section className="cards">{['PENDING','PROCESSING','SUCCESS','FAILED'].map(key => <div className="card" key={key}><small>{key}</small><strong>{counts[key] ?? 0}</strong></div>)}</section>
    <section className="panel">
      <div className="toolbar"><select value={status} onChange={e => setStatus(e.target.value)}><option value="">All statuses</option>{['PENDING','PROCESSING','SUCCESS','FAILED'].map(x => <option key={x}>{x}</option>)}</select>
      <select value={type} onChange={e => setType(e.target.value)}><option value="">All types</option><option>CREDIT</option><option>DEBIT</option></select></div>
      {error && <div className="error">{error}</div>}
      {loading ? <div className="empty">Loading…</div> : <TransactionTable items={items} onSelect={onSelect}/>} 
    </section>
    <section className="panel"><h2>How retries work</h2><p>A failed job can be retried until the configured maximum attempt count is reached. The worker applies the balance change and SUCCESS state in one database transaction.</p></section>
  </main>
}
