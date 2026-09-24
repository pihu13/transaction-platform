import StatusBadge from './StatusBadge'

export default function TransactionTable({ items, onSelect }) {
  if (!items.length) return <div className="empty">No transactions found.</div>
  return <table>
    <thead><tr><th>ID</th><th>Customer</th><th>Type</th><th>Amount</th><th>Status</th><th>Attempts</th></tr></thead>
    <tbody>{items.map(tx => <tr key={tx.id} onClick={() => onSelect(tx.id)} className="clickable">
      <td>{tx.id}</td><td>{tx.customer_id}</td><td>{tx.type}</td><td>{tx.amount}</td><td><StatusBadge status={tx.status}/></td><td>{tx.attempts}</td>
    </tr>)}</tbody>
  </table>
}
