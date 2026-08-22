import { Outlet, NavLink } from 'react-router-dom'

import {
  LayoutDashboard,
  Sun,
  Wind,
  TrendingUp,
  Zap,
  Bell,
  Server,
  MessageSquare,
  Settings,
  Wrench
} from 'lucide-react'

import styles from './Layout.module.css'

const NAV_ITEMS = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/solar', icon: Sun, label: 'Solar' },
  { to: '/wind', icon: Wind, label: 'Wind' },
  { to: '/forecast', icon: TrendingUp, label: 'Forecast' },
  { to: '/grid', icon: Zap, label: 'Grid' },
  { to: '/alerts', icon: Bell, label: 'Alerts' },
  { to: '/assets', icon: Server, label: 'Assets' },
  { to: '/maintenance', icon: Wrench, label: 'Maintenance' },
  { to: '/ai', icon: MessageSquare, label: 'AI Assistant' },
  { to: '/simulation', icon: Settings, label: 'Simulation' },
]

export default function Layout() {
  return (
    <div className={styles.shell}>

      <aside className={styles.sidebar}>

        {/* GreenPulse Logo */}
        <div className={styles.logo}>
          <img
            src="/logo.png"
            alt="GreenPulse AI"
            className={styles.logoImage}
          />
        </div>

        {/* Navigation */}
        <nav className={styles.nav}>
          {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `${styles.navItem} ${isActive ? styles.active : ''}`
              }
            >
              <Icon size={16} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div className={styles.sidebarFooter}>
          <small>
            Kutch &amp; Banaskantha
            <br />
            Gujarat, India
          </small>
        </div>

      </aside>

      <main className={styles.main}>
        <Outlet />
      </main>

    </div>
  )
}