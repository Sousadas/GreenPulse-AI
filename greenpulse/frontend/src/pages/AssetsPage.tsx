import { useQuery } from '@tanstack/react-query'
import { fetchAssets } from '../services/api'
import StatusBadge from '../components/StatusBadge'
import { Server } from 'lucide-react'
import styles from './GenericPage.module.css'

const TYPE_LABELS: Record<string, string> = {
  SOLAR_PANEL: 'Solar Panel',
  SOLAR_INVERTER: 'Solar Inverter',
  WIND_TURBINE: 'Wind Turbine',
  GENERATOR: 'Generator',
  TRANSFORMER: 'Transformer',
  GRID_INTERFACE: 'Grid Interface',
}

export default function AssetsPage() {
  const { data: assets } = useQuery({ queryKey: ['assets'], queryFn: () => fetchAssets() })

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1><Server size={20} /> Asset Registry</h1>
        <StatusBadge label={`${assets?.length ?? 0} assets`} variant="info" />
      </div>

      <div className={styles.table}>
        <table>
          <thead>
            <tr>
              <th>Asset ID</th>
              <th>Type</th>
              <th>Location</th>
              <th>Capacity (kW)</th>
              <th>Manufacturer</th>
              <th>Model</th>
              <th>Installed</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {assets?.map((a: any) => (
              <tr key={a.asset_id}>
                <td><strong>{a.asset_id}</strong></td>
                <td>{TYPE_LABELS[a.asset_type] ?? a.asset_type}</td>
                <td>{a.location}</td>
                <td>{a.capacity_kw.toLocaleString()}</td>
                <td>{a.manufacturer}</td>
                <td>{a.model}</td>
                <td>{new Date(a.installation_date).getFullYear()}</td>
                <td>
                  <StatusBadge
                    label={a.status}
                    variant={a.status === 'ONLINE' ? 'success' : a.status === 'WARNING' ? 'warning' : 'critical'}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
