import styles from './MetricCard.module.css'
import type { ReactNode } from 'react'

type Props = {
  title: string
  value: string | number
  unit?: string
  sub?: string
  accent?: 'solar' | 'wind' | 'green' | 'critical' | 'warning'
  icon?: ReactNode
}

export default function MetricCard({ title, value, unit, sub, accent, icon }: Props) {
  return (
    <div className={`${styles.card} ${accent ? styles[accent] : ''}`}>
      <div className={styles.header}>
        <span className={styles.title}>{title}</span>
        {icon && <span className={styles.icon}>{icon}</span>}
      </div>
      <div className={styles.value}>
        {value}
        {unit && <span className={styles.unit}> {unit}</span>}
      </div>
      {sub && <div className={styles.sub}>{sub}</div>}
    </div>
  )
}
