import { useEffect, useState } from 'react'
import { getBalance, getCustomerTransactions } from '../services/api'
import StatusBadge from '../components/StatusBadge'

export default function CustomerView({ customerId, onBack }) {
  const [balance, setBalance] = useState(null)
  const [items, setItems] = useState([])
  const [error, setError] = useState('')
  useEffect(() => {
    Promise.all([getBalance(customerId), getCustomerTransactions(customerId, { page: 1, page_size: 20 })])
      .then(([b, t]) => { setBalance(b.data); setItems(t.data.items) })
      .catch(e => setError(e.response?.data?.detail || 'Unable to load customer'))
  }, [customerId])
  return <main><button onClick={onBack}>← Back</button>{error && <div className="error">{error}</div>}<div className="panel"><h1>Customer {customerId}</h1><p>Current balance</p><strong className="balance">{balance?.balance ?? 'Loading…'}</strong></div><div className="panel"><h2>Transaction history</h2>{items.length ? <table><thead><tr><th>ID</th><th>Type</th><th>Amount</th><th>Status</th></tr></thead><tbody>{items.map(tx => <tr key={tx.id}><td>{tx.id}</td><td>{tx.type}</td><td>{tx.amount}</td><td><StatusBadge status={tx.status}/></td></tr>)}</tbody></table> : <div className="empty">No transactions found.</div>}</div></main>
}
