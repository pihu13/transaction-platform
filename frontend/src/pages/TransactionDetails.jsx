import { useEffect, useState } from 'react'
import { getTransaction, retryTransaction } from '../services/api'
import StatusBadge from '../components/StatusBadge'

export default function TransactionDetails({ id, onBack }) {
  const [tx, setTx] = useState(null)
  const [error, setError] = useState('')
  async function load() { try { setTx((await getTransaction(id)).data) } catch (e) { setError(e.response?.data?.detail || 'Unable to load transaction') } }
  useEffect(() => { load(); const timer = setInterval(load, 2000); return () => clearInterval(timer) }, [id])
  async function retry() { await retryTransaction(id); load() }
  if (error) return <main><button onClick={onBack}>← Back</button><div className="error">{error}</div></main>
  if (!tx) return <main><div className="empty">Loading…</div></main>
  return <main><button onClick={onBack}>← Back</button><div className="panel details"><h1>Transaction {tx.id}</h1><p><StatusBadge status={tx.status}/></p><dl><dt>Customer</dt><dd>{tx.customer_id}</dd><dt>Type</dt><dd>{tx.type}</dd><dt>Amount</dt><dd>{tx.amount}</dd><dt>Attempts</dt><dd>{tx.attempts}</dd><dt>Failure reason</dt><dd>{tx.failure_reason || '—'}</dd></dl>{tx.status === 'FAILED' && tx.attempts < 3 && <button className="primary" onClick={retry}>Retry transaction</button>}</div></main>
}
