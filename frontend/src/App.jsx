import { Routes, Route } from 'react-router-dom'
import Sidebar from './components/Sidebar.jsx'
import Dashboard from './pages/Dashboard.jsx'
import MapView from './pages/MapView.jsx'
import Forecast from './pages/Forecast.jsx'
import Alerts from './pages/Alerts.jsx'
import ModelCompare from './pages/ModelCompare.jsx'

export default function App() {
  return (
    <div className="app">
      <Sidebar />
      <main className="content">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/carte" element={<MapView />} />
          <Route path="/prevision" element={<Forecast />} />
          <Route path="/alertes" element={<Alerts />} />
          <Route path="/modeles" element={<ModelCompare />} />
        </Routes>
      </main>
    </div>
  )
}
