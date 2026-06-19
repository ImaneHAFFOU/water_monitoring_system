import { useEffect, useState } from 'react'
import { BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import { Trophy } from 'lucide-react'
import { getModels } from '../api.js'
import { Loader, ErrorBox } from '../components/ui.jsx'

const TEAL = '#116069', SAND = '#E0A15B', TEAL2 = '#1B8A8F'
const thStyle = { textAlign: 'left', fontSize: 12, letterSpacing: '.06em', textTransform: 'uppercase', color: 'var(--muted)', fontWeight: 600, padding: '10px 12px', borderBottom: '1px solid var(--line)', whiteSpace: 'nowrap' }
const tdStyle = { padding: '12px', borderBottom: '1px solid var(--line)', fontSize: 14, fontFamily: 'var(--font-display)' }

function Table({ rows, cols, bestIdx }) {
  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead><tr><th style={thStyle}>Modèle</th>{cols.map((c) => <th key={c} style={{ ...thStyle, textAlign: 'right' }}>{c}</th>)}</tr></thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} style={i === bestIdx ? { background: 'rgba(17,96,105,0.06)' } : null}>
              <td style={{ ...tdStyle, fontWeight: 500 }}>
                {i === bestIdx && <Trophy size={13} style={{ color: SAND, verticalAlign: -2, marginRight: 6 }} />}
                {r.model}
              </td>
              {cols.map((c) => <td key={c} style={{ ...tdStyle, textAlign: 'right', color: i === bestIdx ? TEAL : 'var(--text)' }}>{r[c]}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function ModelCompare() {
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)

  useEffect(() => {
    getModels().then(setData).catch((e) => setErr(e.message))
  }, [])

  if (err) return <ErrorBox msg={err} />
  if (!data) return <Loader />

  const fc = data.forecasting || []
  const det = data.detection || []
  const fcBest = fc.length ? fc.reduce((b, r, i, a) => (r.RMSE < a[b].RMSE ? i : b), 0) : -1
  const detBest = det.length ? det.reduce((b, r, i, a) => (r.F1 > a[b].F1 ? i : b), 0) : -1

  return (
    <>
      <div className="topbar">
        <div>
          <div className="eyebrow">Comparaison</div>
          <h1>Comparaison des modèles</h1>
          <div className="sub">Performances mesurées sur le jeu de test — un meilleur modèle par tâche</div>
        </div>
      </div>

      {fc.length === 0 && det.length === 0 ? (
        <div className="card"><div className="card-body">
          <p style={{ color: 'var(--muted)', fontSize: 14 }}>
            Aucun résultat trouvé. Lance les notebooks <strong>02</strong> et <strong>03</strong> :
            ils créent <code>models/forecasting_results.csv</code> et <code>models/detection_results.csv</code>,
            que cette page lit automatiquement.
          </p>
        </div></div>
      ) : (
        <>
          {/* ---------- PRÉVISION ---------- */}
          <div className="card" style={{ marginBottom: 20 }}>
            <div className="card-head">
              <h2>Prévision de la consommation</h2>
              <span className="meta">métrique d'erreur — plus c'est bas, mieux c'est</span>
            </div>
            <div className="card-body">
              {fcBest >= 0 && (
                <p style={{ fontSize: 14, color: 'var(--muted)', marginTop: 0 }}>
                  🏆 Meilleur modèle : <strong style={{ color: TEAL }}>{fc[fcBest].model}</strong> (RMSE le plus faible).
                </p>
              )}
              <div style={{ width: '100%', height: 280 }}>
                <ResponsiveContainer>
                  <BarChart data={fc} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
                    <CartesianGrid stroke="rgba(11,46,51,0.07)" vertical={false} />
                    <XAxis dataKey="model" tick={{ fontSize: 12, fill: '#5C6E70' }} tickLine={false} />
                    <YAxis tick={{ fontSize: 11, fill: '#8A9A9B' }} tickLine={false} axisLine={false} width={42} unit="%" />
                    <Tooltip formatter={(v) => [`${v}%`, 'MAPE']} />
                    <Bar dataKey="MAPE" radius={[6, 6, 0, 0]}>
                      {fc.map((r, i) => <Cell key={i} fill={i === fcBest ? SAND : TEAL} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div style={{ marginTop: 12 }}>
                <Table rows={fc} cols={['MAE', 'RMSE', 'MAPE']} bestIdx={fcBest} />
              </div>
            </div>
          </div>

          {/* ---------- DÉTECTION ---------- */}
          <div className="card">
            <div className="card-head">
              <h2>Détection des fuites</h2>
              <span className="meta">F1 et AUC — plus c'est haut, mieux c'est</span>
            </div>
            <div className="card-body">
              {detBest >= 0 && (
                <p style={{ fontSize: 14, color: 'var(--muted)', marginTop: 0 }}>
                  🏆 Meilleur modèle : <strong style={{ color: TEAL }}>{det[detBest].model}</strong> (F1 le plus élevé).
                </p>
              )}
              <div style={{ width: '100%', height: 280 }}>
                <ResponsiveContainer>
                  <BarChart data={det} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
                    <CartesianGrid stroke="rgba(11,46,51,0.07)" vertical={false} />
                    <XAxis dataKey="model" tick={{ fontSize: 12, fill: '#5C6E70' }} tickLine={false} />
                    <YAxis tick={{ fontSize: 11, fill: '#8A9A9B' }} tickLine={false} axisLine={false} width={42} domain={[0, 1]} />
                    <Tooltip />
                    <Legend wrapperStyle={{ fontSize: 13 }} />
                    <Bar dataKey="F1" fill={TEAL} radius={[6, 6, 0, 0]} />
                    <Bar dataKey="AUC" fill={SAND} radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div style={{ marginTop: 12 }}>
                <Table rows={det} cols={['Précision', 'Rappel', 'F1', 'AUC']} bestIdx={detBest} />
              </div>
            </div>
          </div>
        </>
      )}
    </>
  )
}