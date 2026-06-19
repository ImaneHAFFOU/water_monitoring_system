import { useEffect, useState } from 'react'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine,
} from 'recharts'
import { TrendingUp, TrendingDown, Activity, Clock } from 'lucide-react'
import { getForecast } from '../api.js'
import { KpiCard, Loader, ErrorBox } from '../components/ui.jsx'

const nf = new Intl.NumberFormat('fr-FR')
const fmt = (n) => nf.format(Math.round(n))
const HORIZONS = [
  { h: 24,  label: '24 h' },
  { h: 48,  label: '48 h' },
  { h: 72,  label: '3 jours' },
  { h: 168, label: '7 jours' },
]

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="rc-tooltip">
      <div className="lab">{label}</div>
      {payload.map((p) => (
        <div key={p.dataKey}>{p.dataKey === 'reel' ? 'Réel' : 'Prévu'} : {fmt(p.value)} L/h</div>
      ))}
    </div>
  )
}

export default function Forecast() {
  const [hours, setHours] = useState(48)
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    getForecast(hours)
      .then((d) => { setData(d); setErr(null) })
      .catch((e) => setErr(e.message))
      .finally(() => setLoading(false))
  }, [hours])

  if (err) return <ErrorBox msg={err} />
  if (!data) return <Loader />

  const hist = (data.history || []).map((p) => ({ t: p.timestamp.slice(5, 16), reel: p.value }))
  const fc = (data.forecast || []).map((p) => ({ t: p.timestamp.slice(5, 16), prevu: p.value }))
  if (hist.length && fc.length) hist[hist.length - 1].prevu = hist[hist.length - 1].reel
  const chartData = [...hist, ...fc]
  const splitAt = fc.length ? fc[0].t : null

  const vals = (data.forecast || []).map((p) => p.value)
  const peak = vals.length ? Math.max(...vals) : 0
  const trough = vals.length ? Math.min(...vals) : 0
  const mean = vals.length ? vals.reduce((s, v) => s + v, 0) / vals.length : 0

  return (
    <>
      <div className="topbar">
        <div>
          <div className="eyebrow">Prévision</div>
          <h1>Prévision de la demande</h1>
          <div className="sub">Modèle {data.model?.toUpperCase()} · demande horaire du réseau</div>
        </div>
        <div className="topbar-right">
          <div style={{ display: 'inline-flex', border: '1px solid var(--line)', borderRadius: 10, overflow: 'hidden', background: 'var(--surface)' }}>
            {HORIZONS.map((o, i) => (
              <button key={o.h} onClick={() => setHours(o.h)} disabled={loading}
                style={{
                  padding: '8px 14px', border: 'none', cursor: 'pointer',
                  borderLeft: i ? '1px solid var(--line)' : 'none',
                  background: hours === o.h ? 'var(--teal-700)' : 'transparent',
                  color: hours === o.h ? '#fff' : 'var(--text)',
                  fontFamily: 'var(--font-display)', fontWeight: 500, fontSize: 14,
                }}>
                {o.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="kpi-grid">
        <KpiCard tone="sand"   label="Pic prévu"      value={fmt(peak / 1000)}   unit="k L/h" icon={TrendingUp} />
        <KpiCard tone="teal"   label="Creux prévu"    value={fmt(trough / 1000)} unit="k L/h" icon={TrendingDown} />
        <KpiCard tone="teal"   label="Moyenne prévue" value={fmt(mean / 1000)}   unit="k L/h" icon={Activity} />
        <KpiCard tone="sand"   label="Horizon"        value={hours}              unit="h"     icon={Clock} hint={`${fc.length} points prévus`} />
      </div>

      <div className="card">
        <div className="card-head">
          <h2>Historique &amp; prévision</h2>
          <span className="meta">{loading ? 'Calcul en cours…' : `7 jours d'historique + ${hours} h prévues`}</span>
        </div>
        <div className="card-body">
          <div style={{ width: '100%', height: 400, opacity: loading ? 0.5 : 1, transition: 'opacity .2s' }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="gReelF" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#116069" stopOpacity={0.28} />
                    <stop offset="100%" stopColor="#116069" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="rgba(11,46,51,0.07)" vertical={false} />
                <XAxis dataKey="t" tick={{ fontSize: 11, fill: '#8A9A9B' }} minTickGap={48} tickLine={false} axisLine={{ stroke: 'rgba(11,46,51,0.12)' }} />
                <YAxis tick={{ fontSize: 11, fill: '#8A9A9B' }} tickLine={false} axisLine={false} width={54} tickFormatter={(v) => `${Math.round(v / 1000)}k`} />
                <Tooltip content={<ChartTooltip />} />
                {splitAt && <ReferenceLine x={splitAt} stroke="#E0A15B" strokeDasharray="4 4" label={{ value: 'maintenant', position: 'top', fill: '#B57A33', fontSize: 11 }} />}
                <Area type="monotone" dataKey="reel"  stroke="#116069" strokeWidth={2} fill="url(#gReelF)" dot={false} />
                <Area type="monotone" dataKey="prevu" stroke="#E0A15B" strokeWidth={2.4} strokeDasharray="5 4" fill="none" dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          <div style={{ display: 'flex', gap: 20, marginTop: 12, fontSize: 13, color: 'var(--muted)' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: 7 }}><span style={{ width: 16, height: 3, background: '#116069', borderRadius: 2 }} /> Consommation réelle</span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 7 }}><span style={{ width: 16, height: 0, borderTop: '2.4px dashed #E0A15B' }} /> Prévision {data.model?.toUpperCase()}</span>
          </div>
        </div>
      </div>
    </>
  )
}