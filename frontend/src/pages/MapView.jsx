import { useEffect, useState, useRef, useMemo } from 'react'
import { MapContainer, TileLayer, CircleMarker, Polygon, Popup, Tooltip } from 'react-leaflet'
import { getMeters, getAlerts, getZoneShapes } from '../api.js'
import { Loader, ErrorBox } from '../components/ui.jsx'

const nf = new Intl.NumberFormat('fr-FR')
const fmt = (n) => nf.format(Math.round(n))
const ZONE_ORDER = ['residential', 'tourist', 'industrial']
const ZONE = {
  residential: { color: '#1B8A8F', fill: '#5DB6B3', label: 'Résidentiel' },
  tourist:     { color: '#B57A33', fill: '#E0A15B', label: 'Touristique' },
  industrial:  { color: '#0A363C', fill: '#116069', label: 'Industriel' },
}
const LEAK = '#C8453B'
const AGADIR = [30.4202, -9.5982]
const MARKER_R = 7 // taille fixe, comme la carte de référence — évite les bulles qui se chevauchent

function boundsOf(points) {
  const lats = points.map((p) => p[0]), lons = points.map((p) => p[1])
  return [[Math.min(...lats), Math.min(...lons)], [Math.max(...lats), Math.max(...lons)]]
}

export default function MapView() {
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)
  const mapRef = useRef(null)

  useEffect(() => {
    Promise.all([getMeters(), getAlerts(168, 100), getZoneShapes()])
      .then(([meters, alerts, shapes]) => setData({ meters, alerts, shapes }))
      .catch((e) => setErr(e.message))
  }, [])

  const grouped = useMemo(() => {
    if (!data) return {}
    const g = {}
    for (const m of data.meters) {
      g[m.zone] = g[m.zone] || { count: 0, quartiers: {} }
      g[m.zone].count++
      const q = m.quartier || ZONE[m.zone]?.label || m.zone
      g[m.zone].quartiers[q] = g[m.zone].quartiers[q] || []
      g[m.zone].quartiers[q].push(m.meterid)
    }
    return g
  }, [data])

  if (err) return <ErrorBox msg={err} />
  if (!data) return <Loader />

  const { meters, alerts, shapes } = data
  const alertMeters = new Set(alerts.map((a) => a.meterid))
  const meterById = Object.fromEntries(meters.map((m) => [m.meterid, m]))
  const center = meters.length
    ? [meters.reduce((s, m) => s + m.latitude, 0) / meters.length, meters.reduce((s, m) => s + m.longitude, 0) / meters.length]
    : AGADIR

  const flyTo = (m) => mapRef.current?.flyTo([m.latitude, m.longitude], 14, { duration: 0.8 })
  const flyToZone = (zone) => {
    const pts = shapes?.[zone]
    if (pts?.length) mapRef.current?.fitBounds(boundsOf(pts), { padding: [24, 24], duration: 0.8 })
  }

  return (
    <>
      <div className="topbar">
        <div>
          <div className="eyebrow">Carte interactive</div>
          <h1>Carte du réseau — Grand Agadir</h1>
          <div className="sub">{meters.length} compteurs de secteur · 3 zones · coordonnées vérifiées sur le terrain</div>
        </div>
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-head"><h2>Réseau de distribution</h2><span className="meta">données spatiales en direct</span></div>
          <div className="card-body">
            <div style={{ height: 580, borderRadius: 12, overflow: 'hidden', border: '1px solid var(--line)' }}>
              <MapContainer ref={mapRef} center={center} zoom={13} scrollWheelZoom style={{ height: '100%', width: '100%' }}>
                <TileLayer attribution='&copy; OpenStreetMap' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />

                {Object.entries(shapes || {}).map(([zone, pts]) => (
                  <Polygon key={zone} positions={pts}
                    pathOptions={{ color: ZONE[zone]?.color || '#116069', fillColor: ZONE[zone]?.fill || '#116069', fillOpacity: 0.22, weight: 2 }}>
                    <Tooltip sticky>{ZONE[zone]?.label || zone}</Tooltip>
                  </Polygon>
                ))}

                {meters.map((m) => {
                  const leak = alertMeters.has(m.meterid)
                  const col = leak ? LEAK : (ZONE[m.zone]?.color || '#116069')
                  return (
                    <CircleMarker key={m.meterid} center={[m.latitude, m.longitude]} radius={MARKER_R}
                      pathOptions={{ color: '#fff', weight: 2, fillColor: col, fillOpacity: 1 }}>
                      <Tooltip>{m.meterid}{leak ? ' · fuite' : ''}</Tooltip>
                      <Popup>
                        <div style={{ fontFamily: 'Inter, sans-serif', lineHeight: 1.5 }}>
                          <strong>{m.meterid}</strong> — {m.quartier || ''}<br />
                          Zone : {ZONE[m.zone]?.label || m.zone}<br />
                          Conso. moyenne : {fmt(m.mean_consumption)} L/15min<br />
                          Taux d'anomalie : {m.anomaly_rate}%
                          {leak && <><br /><span style={{ color: LEAK, fontWeight: 600 }}>⚠ Fuite détectée</span></>}
                        </div>
                      </Popup>
                    </CircleMarker>
                  )
                })}
              </MapContainer>
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          <div className="card">
            <div className="card-head"><h2>Zones &amp; quartiers</h2></div>
            <div className="card-body">
              {ZONE_ORDER.filter((z) => grouped[z]).map((zone) => (
                <div key={zone}
                  onClick={() => flyToZone(zone)}
                  style={{
                    display: 'flex', gap: 10, padding: '11px 12px', marginBottom: 8, cursor: 'pointer',
                    borderRadius: 10, borderLeft: `4px solid ${ZONE[zone].color}`,
                    background: 'var(--surface-2)', transition: 'transform .15s',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.transform = 'translateX(3px)')}
                  onMouseLeave={(e) => (e.currentTarget.style.transform = 'translateX(0)')}>
                  <span style={{ width: 11, height: 11, borderRadius: 3, background: ZONE[zone].color, marginTop: 3, flexShrink: 0 }} />
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontWeight: 600, fontSize: 13.5 }}>{ZONE[zone].label}</div>
                    <div style={{ fontFamily: 'var(--font-display)', fontSize: 11.5, color: 'var(--muted)', marginBottom: 4 }}>
                      {grouped[zone].count} compteur{grouped[zone].count > 1 ? 's' : ''}
                    </div>
                    <div style={{ fontSize: 11.5, color: 'var(--faint)', lineHeight: 1.7 }}>
                      {Object.entries(grouped[zone].quartiers).map(([q, ids]) => (
                        <div key={q}>📍 {q} ({ids.join(', ')})</div>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
              <p style={{ fontSize: 11.5, color: 'var(--faint)', marginTop: 4 }}>Clique une zone pour zoomer dessus.</p>
            </div>
          </div>

          <div className="card">
            <div className="card-head"><h2>Fuites localisées</h2><span className="meta">{alerts.length} alertes</span></div>
            <div className="card-body" style={{ maxHeight: 320, overflowY: 'auto' }}>
              {alerts.length === 0 && <p style={{ color: 'var(--muted)', fontSize: 14 }}>Aucune fuite détectée sur la période.</p>}
              {alerts.slice(0, 12).map((a, i) => {
                const m = meterById[a.meterid]
                return (
                  <div className="alert-row" key={i} style={{ cursor: m ? 'pointer' : 'default' }}
                    onClick={() => m && flyTo(m)} title={m ? 'Localiser sur la carte' : ''}>
                    <span className={`sev ${a.severity === 'élevée' ? 'elevee' : 'moyenne'}`} />
                    <div className="alert-main">
                      <div className="alert-title">{a.meterid} · {a.quartier || a.zone}</div>
                      <div className="alert-sub">{a.timestamp?.slice(0, 16)} · {a.pressure} bar</div>
                    </div>
                    <span className={`badge ${a.type?.includes('fuite') ? 'leak' : 'anom'}`}>
                      {a.type?.includes('fuite') ? 'fuite' : 'anomalie'}
                    </span>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      </div>
    </>
  )
}