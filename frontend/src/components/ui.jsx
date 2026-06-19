import { AlertTriangle, CheckCircle2 } from 'lucide-react'

export function KpiCard({ label, value, unit, icon: Icon, tone = 'teal', hint }) {
  return (
    <div className={`kpi ${tone}`}>
      <div className="kpi-head">
        <span className="kpi-label">{label}</span>
        {Icon && <Icon size={16} className="kpi-icon" />}
      </div>
      <div className="kpi-value">{value}{unit && <span className="kpi-unit">{unit}</span>}</div>
      {hint && <div className="kpi-hint">{hint}</div>}
    </div>
  )
}

export function Loader() {
  return <div className="state"><div className="spinner" /></div>
}

export function ErrorBox({ msg }) {
  return (
    <div className="state err">
      <div className="ic"><AlertTriangle size={28} /></div>
      <h2>Impossible de joindre l'API</h2>
      <p>Vérifie que le backend est démarré, puis recharge la page.</p>
      <p>Dans un terminal : <code>cd backend &amp;&amp; uvicorn main:app --reload</code></p>
      <p style={{ color: 'var(--faint)', fontSize: 12 }}>Détail : {msg}</p>
    </div>
  )
}

export function EmptyState({ title, children }) {
  return (
    <div className="state empty">
      <div className="ic"><CheckCircle2 size={28} /></div>
      <h2>{title}</h2>
      <p>{children}</p>
    </div>
  )
}
