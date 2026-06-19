import { NavLink } from 'react-router-dom'
import { LayoutDashboard, Map, TrendingUp, BellRing, BarChart3, Droplets } from 'lucide-react'

const items = [
  { to: '/',          label: 'Tableau de bord',  icon: LayoutDashboard, end: true },
  { to: '/carte',     label: 'Carte interactive', icon: Map },
  { to: '/prevision', label: 'Prévision',         icon: TrendingUp },
  { to: '/alertes',   label: 'Alertes & fuites',  icon: BellRing },
  { to: '/modeles',   label: 'Comparaison',       icon: BarChart3 },
]

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="brand">
        <span className="brand-mark"><Droplets size={22} /></span>
        <div>
          <div className="brand-name">AquaVeille</div>
          <div className="brand-sub">Grand Agadir</div>
        </div>
      </div>

      <nav className="nav">
        {items.map(({ to, label, icon: Icon, end }) => (
          <NavLink key={to} to={to} end={end}
            className={({ isActive }) => 'nav-item' + (isActive ? ' active' : '')}>
            <Icon size={18} />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-foot">
        <div className="live"><span className="dot" /> Système en ligne</div>
        <div className="foot-note">PFE · Université Ibn Zohr</div>
      </div>
    </aside>
  )
}
