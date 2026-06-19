import { useEffect, useState } from 'react'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine,
} from 'recharts'
import { Droplets, Gauge, BellRing, Activity } from 'lucide-react'
import { getHealth, getForecast, getZones, getAlerts } from '../api.js'
import { KpiCard, Loader, ErrorBox } from '../components/ui.jsx'

const nf = new Intl.NumberFormat('fr-FR')
const fmt = (n) => nf.format(Math.round(n))
const zoneColor = { residential: '#1B8A8F', tourist: '#E0A15B', industrial: '#116069' }
const zoneLabel = { residential: 'Résidentiel', tourist: 'Touristique', industrial: 'Industriel' }

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

export default function Dashboard() {
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)

  useEffect(() => {
    Promise.all([getHealth(), getForecast(48), getZones(), getAlerts(168, 6)])
      .then(([health, forecast, zones, alerts]) => setData({ health, forecast, zones, alerts }))
      .catch((e) => setErr(e.message))
  }, [])

  if (err) return <ErrorBox msg={err} />
  if (!data) return <Loader />

  const { health, forecast, zones, alerts } = data

  const totalConso = zones.reduce((s, z) => s + z.total_consumption, 0)
  const meters = health?.data?.meters ?? 0
  const anomalyRate = zones.length ? zones.reduce((s, z) => s + z.anomaly_rate, 0) / zones.length : 0
  const maxZone = Math.max(...zones.map((z) => z.total_consumption), 1)

  // Fusion historique + prévision pour une seule courbe continue
  const hist = (forecast.history || []).map((p) => ({ t: p.timestamp.slice(5, 16), reel: p.value }))
  const fc = (forecast.forecast || []).map((p) => ({ t: p.timestamp.slice(5, 16), prevu: p.value }))
  if (hist.length && fc.length) hist[hist.length - 1].prevu = hist[hist.length - 1].reel
  const chartData = [...hist, ...fc]
  const splitAt = fc.length ? fc[0].t : null

  return (
    <>
      <div className="topbar">
        <div>
          <div className="eyebrow">Tableau de bord</div>
          <h1>Surveillance du réseau d'eau</h1>
          <div className="sub">Vue d'ensemble en temps réel — {meters} compteurs de secteur, {zones.length} zones</div>
        </div>
        <div className="topbar-right">
          Période des données<br />
          <span className="stamp">{health?.data?.period_start?.slice(0, 10)} → {health?.data?.period_end?.slice(0, 10)}</span>
        </div>
      </div>

      <div className="kpi-grid">
        <KpiCard tone="teal"   label="Consommation totale" value={fmt(totalConso / 1e6)} unit="Ml" icon={Droplets} hint="Cumul sur la période" />
        <KpiCard tone="teal"   label="Compteurs suivis"    value={meters} icon={Gauge} hint="Approche DMA (par secteur)" />
        <KpiCard tone="danger" label="Alertes actives"      value={alerts.length} icon={BellRing} hint="7 derniers jours" />
        <KpiCard tone="sand"   label="Taux d'anomalie moyen" value={anomalyRate.toFixed(1)} unit="%" icon={Activity} hint="Toutes zones confondues" />
      </div>

      <div className="card">
        <div className="card-head">
          <h2>Prévision de la demande</h2>
          <span className="meta">Modèle {forecast.model?.toUpperCase()} · historique + 48 h prévues</span>
        </div>
        <div className="card-body">
          <div className="chart-wrap">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="gReel" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#116069" stopOpacity={0.28} />
                    <stop offset="100%" stopColor="#116069" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="rgba(11,46,51,0.07)" vertical={false} />
                <XAxis dataKey="t" tick={{ fontSize: 11, fill: '#8A9A9B' }} minTickGap={40} tickLine={false} axisLine={{ stroke: 'rgba(11,46,51,0.12)' }} />
                <YAxis tick={{ fontSize: 11, fill: '#8A9A9B' }} tickLine={false} axisLine={false} width={54}
                  tickFormatter={(v) => `${Math.round(v / 1000)}k`} />
                <Tooltip content={<ChartTooltip />} />
                {splitAt && <ReferenceLine x={splitAt} stroke="#E0A15B" strokeDasharray="4 4" label={{ value: 'maintenant', position: 'top', fill: '#B57A33', fontSize: 11 }} />}
                <Area type="monotone" dataKey="reel" stroke="#116069" strokeWidth={2} fill="url(#gReel)" name="Réel" dot={false} />
                <Area type="monotone" dataKey="prevu" stroke="#E0A15B" strokeWidth={2} strokeDasharray="5 4" fill="none" name="Prévu" dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-head"><h2>Consommation par zone</h2><span className="meta">cumul sur la période</span></div>
          <div className="card-body">
            {zones.map((z) => (
              <div className="zone-row" key={z.zone}>
                <span className="zone-name">{zoneLabel[z.zone] || z.zone}</span>
                <span className="zone-bar">
                  <span style={{ width: `${(z.total_consumption / maxZone) * 100}%`, background: zoneColor[z.zone] || '#116069' }} />
                </span>
                <span className="zone-val">{fmt(z.total_consumption / 1e6)} Ml</span>
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <div className="card-head"><h2>Alertes récentes</h2><span className="meta">{alerts.length} affichées</span></div>
          <div className="card-body">
            {alerts.length === 0 && <p style={{ color: 'var(--muted)', fontSize: 14 }}>Aucune alerte sur la période.</p>}
            {alerts.map((a, i) => (
              <div className="alert-row" key={i}>
                <span className={`sev ${a.severity === 'élevée' ? 'elevee' : 'moyenne'}`} />
                <div className="alert-main">
                  <div className="alert-title">{a.meterid} · {a.quartier || a.zone}</div>
                  <div className="alert-sub">{a.timestamp?.slice(0, 16)} · pression {a.pressure} bar</div>
                </div>
                <span className={`badge ${a.type?.includes('fuite') ? 'leak' : 'anom'}`}>
                  {a.type?.includes('fuite') ? 'fuite' : 'anomalie'}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  )
}
