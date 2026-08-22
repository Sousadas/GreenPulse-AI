import { useQuery } from '@tanstack/react-query'
import { fetchGridStatus } from '../services/api'
import MetricCard from '../components/MetricCard'
import StatusBadge from '../components/StatusBadge'
import { Zap } from 'lucide-react'
import styles from './GenericPage.module.css'

export default function GridPage() {
  const { data: grid } = useQuery({ queryKey: ['grid'], queryFn: fetchGridStatus })

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1><Zap size={20} /> Grid Integration</h1>
        <StatusBadge label="SIMULATED" variant="info" />
      </div>

      <div className={styles.notice}>
        ⚠️ <strong>AI RECOMMENDATION — Advisory only.</strong> This system does not directly control the electrical grid.
      </div>

      <div className={styles.metrics}>
        <MetricCard title="Renewable Gen." value={grid ? grid.renewable_generation_mw.toFixed(2) : '—'} unit="MW" accent="green" />
        <MetricCard title="Grid Load" value={grid ? grid.grid_load_mw.toFixed(2) : '—'} unit="MW" />
        <MetricCard title="Surplus" value={grid ? grid.renewable_surplus_mw.toFixed(2) : '—'} unit="MW" accent={grid?.renewable_surplus_mw > 0 ? 'green' : 'warning'} />
        <MetricCard title="Grid Export" value={grid ? grid.grid_export_mw.toFixed(2) : '—'} unit="MW" accent="wind" />
        <MetricCard title="Grid Import" value={grid ? grid.grid_import_mw.toFixed(2) : '—'} unit="MW" />
        <MetricCard title="Frequency" value={grid ? grid.grid_frequency_hz.toFixed(2) : '—'} unit="Hz" />
        <MetricCard title="Voltage" value={grid ? (grid.grid_voltage_v / 1000).toFixed(1) : '—'} unit="kV" />
      </div>

      {grid && (
        <div className={styles.chartCard}>
          <div className={styles.chartTitle}>Grid Balance</div>
          <div className={styles.gridBalance}>
            <div className={styles.balanceRow}>
              <span>Renewable Generation</span>
              <strong style={{ color: 'var(--color-secondary)' }}>{grid.renewable_generation_mw.toFixed(2)} MW</strong>
            </div>
            <div className={styles.balanceRow}>
              <span>Grid Load</span>
              <strong>{grid.grid_load_mw.toFixed(2)} MW</strong>
            </div>
            <div className={styles.balanceDivider} />
            <div className={styles.balanceRow}>
              <span>Surplus</span>
              <strong style={{ color: grid.renewable_surplus_mw >= 0 ? 'var(--color-success)' : 'var(--color-critical)' }}>
                {grid.renewable_surplus_mw >= 0 ? '+' : ''}{grid.renewable_surplus_mw.toFixed(2)} MW
              </strong>
            </div>
            <div className={styles.balanceRow}>
              <span>Recommendation</span>
              <span style={{ color: 'var(--color-secondary)', fontSize: '13px' }}>
                {grid.renewable_surplus_mw > 2
                  ? 'AI RECOMMENDATION: Export renewable power to grid or charge available storage.'
                  : grid.renewable_surplus_mw < -2
                  ? 'AI RECOMMENDATION: Prepare for generation deficit. Consider grid import.'
                  : 'AI RECOMMENDATION: Generation closely matches demand. Maintain current operation.'}
              </span>
            </div>
          </div>
          <div className={styles.dataLabel}>SOURCE: SIMULATED</div>
        </div>
      )}
    </div>
  )
}
