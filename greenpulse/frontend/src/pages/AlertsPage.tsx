import { useQuery } from '@tanstack/react-query'
import { fetchAlerts } from '../services/api'
import StatusBadge from '../components/StatusBadge'
import { Bell } from 'lucide-react'
import { format } from 'date-fns'
import styles from './GenericPage.module.css'

export default function AlertsPage() {
  const { data: alerts } = useQuery({ queryKey: ['alerts'], queryFn: () => fetchAlerts() })

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1><Bell size={20} /> Active Alerts</h1>
        <StatusBadge label={`${alerts?.length ?? 0} open`} variant={alerts?.length ? 'critical' : 'success'} />
      </div>

      {!alerts?.length && (
        <div className={styles.empty}>No active alerts. System operating normally.</div>
      )}

      {alerts?.map((a: any) => (
        <div key={a.alert_id} className={styles.alertCard}>
          <div className={styles.alertCardHeader}>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <StatusBadge
                label={a.severity}
                variant={a.severity === 'CRITICAL' || a.severity === 'HIGH' ? 'critical' : 'warning'}
              />
              <strong>{a.asset_id}</strong>
              <span style={{ color: 'var(--color-muted)', fontSize: 12 }}>{a.category}</span>
            </div>
            <span style={{ color: 'var(--color-muted)', fontSize: 12 }}>
              {format(new Date(a.timestamp), 'HH:mm:ss dd MMM yyyy')}
            </span>
          </div>
          <p style={{ margin: '8px 0 4px' }}>{a.description}</p>
          <div className={styles.evidenceBlock}>
            <div className={styles.evidenceTitle}>Evidence</div>
            <ul>
              {a.evidence.map((e: string, i: number) => <li key={i}>{e}</li>)}
            </ul>
          </div>
          <div className={styles.recommendation}>
            <strong>Recommendation:</strong> {a.recommendation}
          </div>
        </div>
      ))}
    </div>
  )
}
