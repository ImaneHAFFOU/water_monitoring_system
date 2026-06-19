import { useEffect, useState, useMemo } from 'react'
import { AlertTriangle, Droplet, ShieldAlert, Gauge, ArrowUpDown } from 'lucide-react'
import { getAlerts } from '../api.js'
import { KpiCard, Loader, ErrorBox } from '../components/ui.jsx'

const WINDOWS = [
  { h: 168, label: '7 jours' },
  { h: 336, label: '14 jours' },
  { h: 720, label: '30 jours' },
]
const FILTERS = [
  { k: 'all',  label: 'Toutes' },
  { k: 'leak', label: 'Fuites' },
  { k: 'anom', label: 'Anomalies' },
]
const isLeak = (a) => a.type?.includes('fuite')

const thStyle = { textAlign: 'left', fontSize: 12, letterSpacing: '.06em', textTransform: 'uppercase', color: 'var(--muted)', fontWeight: 600, padding: '10px 12px', borderBottom: '1px solid var(--line)', whiteSpace: 'nowrap' }
const tdStyle = { padding: '12px', borderBottom: '1px solid var(--line)', fontSize: 14, verticalAlign: 'middle' }
const segWrap = { display: 'inline-flex', border: '1px solid var(--line)', borderRadius: 10, overflow: 'hidden', background: 'var(--surface)' }
const segBtn = (active, i) => ({ padding: '8px 14px', border: 'none', borderLeft: i ? '1px solid var(--line)' : 'none', cursor: 'pointer', background: active ? 'var(--teal-700)' : 'transparent', color: active ? '#fff' : 'var(--text)', fontFamily: 'var(--font-display)', fontWeight: 500, fontSize: 14 })

export default function Alerts() {
  const [hours, setHours] = useState(168)
  const [filter, setFilter] = useState('all')
  const [sort, setSort] = useState({ key: 'score', dir: 'desc' })
  const [rows, setRows] = useState(null)
  const [err, setErr] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    getAlerts(hours, 100)
      .then((d) => { setRows(d); setErr(null) })
      .catch((e) => setErr(e.message))
      .finally(() => setLoading(false))
  }, [hours])

  const view = useMemo(() => {
    if (!rows) return []
    let r = rows
    if (filter === 'leak') r = r.filter(isLeak)
    if (filter === 'anom') r = r.filter((a) => !isLeak(a))
    const dir = sort.dir === 'desc' ? -1 : 1
    return [...r].sort((a, b) => {
      const va = sort.key === 'score' ? a.score : a.timestamp
      const vb = sort.key === 'score' ? b.score : b.timestamp
      return va > vb ? dir : va < vb ? -dir : 0
    })
  }, [rows, filter, sort])

  if (err) return <ErrorBox msg={err} />
  if (!rows) return <Loader />

  const total = rows.length
  const leaks = rows.filter(isLeak).length
  const high = rows.filter((a) => a.severity === 'élevée').length
  const meters = new Set(rows.map((a) => a.meterid)).size
  const toggleSort = (key) => setSort((s) => ({ key, dir: s.key === key && s.dir === 'desc' ? 'asc' : 'desc' }))

  return (
    <>
      <div className="topbar">
        <div>
          <div className="eyebrow">Alertes &amp; fuites</div>
          <h1>Détection des fuites</h1>
          <div className="sub">Anomalies détectées par l'Isolation Forest sur le réseau</div>
        </div>
        <div className="topbar-right">
          <div style={segWrap}>
            {WINDOWS.map((o, i) => (
              <button key={o.h} onClick={() => setHours(o.h)} disabled={loading} style={segBtn(hours === o.h, i)}>{o.label}</button>
            ))}
          </div>
        </div>
      </div>

      <div className="kpi-grid">
        <KpiCard tone="danger" label="Alertes totales"   value={total}  icon={AlertTriangle} />
        <KpiCard tone="danger" label="Fuites probables"  value={leaks}  icon={Droplet} />
        <KpiCard tone="sand"   label="Sévérité élevée"    value={high}   icon={ShieldAlert} />
        <KpiCard tone="teal"   label="Compteurs touchés"  value={meters} icon={Gauge} />
      </div>

      <div className="card">
        <div className="card-head">
          <h2>Journal des alertes</h2>
          <div style={segWrap}>
            {FILTERS.map((f, i) => (
              <button key={f.k} onClick={() => setFilter(f.k)} style={segBtn(filter === f.k, i)}>{f.label}</button>
            ))}
          </div>
        </div>
        <div className="card-body" style={{ opacity: loading ? 0.5 : 1, transition: 'opacity .2s' }}>
          {view.length === 0 ? (
            <p style={{ color: 'var(--muted)', fontSize: 14, padding: '8px 4px' }}>Aucune alerte pour ce filtre sur la période.</p>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr>
                    <th style={thStyle}>Sévérité</th>
                    <th style={thStyle}>Compteur</th>
                    <th style={thStyle}>Quartier</th>
                    <th style={thStyle}>Zone</th>
                    <th style={{ ...thStyle, cursor: 'pointer' }} onClick={() => toggleSort('time')}>
                      Date / heure <ArrowUpDown size={12} style={{ verticalAlign: -2, opacity: sort.key === 'time' ? 1 : 0.3 }} />
                    </th>
                    <th style={thStyle}>Pression</th>
                    <th style={{ ...thStyle, cursor: 'pointer' }} onClick={() => toggleSort('score')}>
                      Score <ArrowUpDown size={12} style={{ verticalAlign: -2, opacity: sort.key === 'score' ? 1 : 0.3 }} />
                    </th>
                    <th style={thStyle}>Type</th>
                  </tr>
                </thead>
                <tbody>
                  {view.map((a, i) => (
                    <tr key={i}>
                      <td style={tdStyle}><span className={`sev ${a.severity === 'élevée' ? 'elevee' : 'moyenne'}`} style={{ display: 'inline-block' }} /></td>
                      <td style={{ ...tdStyle, fontFamily: 'var(--font-display)', fontWeight: 500 }}>{a.meterid}</td>
                      <td style={tdStyle}>{a.quartier || '—'}</td>
                      <td style={{ ...tdStyle, textTransform: 'capitalize', color: 'var(--muted)' }}>{a.zone}</td>
                      <td style={{ ...tdStyle, color: 'var(--muted)' }}>{a.timestamp?.slice(0, 16).replace('T', ' ')}</td>
                      <td style={{ ...tdStyle, fontFamily: 'var(--font-display)', color: a.pressure < 3.2 ? 'var(--danger)' : 'var(--text)' }}>{a.pressure} bar</td>
                      <td style={{ ...tdStyle, fontFamily: 'var(--font-display)' }}>{a.score}</td>
                      <td style={tdStyle}><span className={`badge ${isLeak(a) ? 'leak' : 'anom'}`}>{isLeak(a) ? 'fuite' : 'anomalie'}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <p style={{ color: 'var(--faint)', fontSize: 12.5, marginTop: 12 }}>
            {view.length} alerte(s) affichée(s) · clique « Date / heure » ou « Score » pour trier.
          </p>
        </div>
      </div>
    </>
  )
}