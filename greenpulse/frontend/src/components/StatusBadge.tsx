import styles from './StatusBadge.module.css'

type Props = {
  label: string
  variant?: 'success' | 'warning' | 'critical' | 'info' | 'muted' | 'solar' | 'wind'
}

export default function StatusBadge({ label, variant = 'info' }: Props) {
  return <span className={`${styles.badge} ${styles[variant]}`}>{label}</span>
}
