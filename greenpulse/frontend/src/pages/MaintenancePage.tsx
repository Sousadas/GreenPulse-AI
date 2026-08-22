import { useQuery } from '@tanstack/react-query'
import { fetchMaintenanceRisks } from '../services/api'
import StatusBadge from '../components/StatusBadge'
import MetricCard from '../components/MetricCard'
import { Wrench } from 'lucide-react'
import styles from './GenericPage.module.css'

const RISK_VARIANT: Record<string, 'success' | 'warning' | 'critical' | 'muted'> = {
  LOW: 'success',
  MEDIUM: 'warning',
  HIGH: 'critical',
  CRITICAL: 'critical',
}

function HealthBar({ score }: { score: number }) {
  const color = score >= 75 ? '#22A06B' : score >= 50 ? '#F59E0B' : '#DC3545'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div style={{ flex: 1, height: 6, background: '#e5e7eb', borderRadius: 3, overflow: 'hidden' }}>
        <div style={{ width: `${score}%`, height: '100%', background: color, borderRadius: 3 }} />
      </div>
      <span style={{ fontSize: 12, fontWeight: 600, minWidth: 36, color }}>{score}</span>
    </div>
  )
}

export default function MaintenancePage() {
  const { data: risks } = useQuery({ queryKey: ['maintenance'], queryFn: fetchMaintenanceRisks })

  const critical = risks?.filter((r: any) => r.maintenance_risk === 'CRITICAL').length ?? 0
  const high = risks?.filter((r: any) => r.maintenance_risk === 'HIGH').length ?? 0
  const avgHealth = risks?.length
    ? Math.round(risks.reduce((s: number, r: any) => s + r.health_score, 0) / risks.length)
    : 0

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1><Wrench size={20} /> Predictive Maintenance</h1>
        <StatusBadge label="SIMULATED" variant="info" />
      </div>

      <div className={styles.metrics}>
        <MetricCard title="Critical Risk" value={critical} accent={critical > 0 ? 'critical' : undefined} />
        <MetricCard title="High Risk" value={high} accent={high > 0 ? 'warning' : undefined} />
        <MetricCard title="Avg Health Score" value={avgHealth} unit="/ 100" accent="green" />
        <MetricCard title="Assets Monitored" value={risks?.length ?? 0} />
      </div>

      <div className={styles.table}>
        <table>
          <thead>
            <tr>
              <th>Asset ID</th>
              <th>Health Score</th>
              <th>Risk Level</th>
              <th>Contributing Factors</th>
            </tr>
          </thead>
          <tbody>
            {risks?.map((r: any) => (
              <tr key={r.asset_id}>
                <td><strong>{r.asset_id}</strong></td>
                <td style={{ minWidth: 160 }}><HealthBar score={r.health_score} /></td>
                <td>
                  <StatusBadge label={r.maintenance_risk} variant={RISK_VARIANT[r.maintenance_risk] ?? 'info'} />
                </td>
                <td style={{ fontSize: 12, color: 'var(--color-muted)' }}>
                  {r.contributing_factors.length
                    ? r.contributing_factors.join(' · ')
                    : 'No issues detected'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
