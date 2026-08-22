import { useQuery } from '@tanstack/react-query'
import { fetchWindGeneration, fetchWeather } from '../services/api'
import MetricCard from '../components/MetricCard'
import StatusBadge from '../components/StatusBadge'
import { Wind } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import styles from './GenericPage.module.css'

export default function WindPage() {
  const { data: wind, isLoading } = useQuery({ queryKey: ['wind'], queryFn: fetchWindGeneration })
  const { data: weather } = useQuery({ queryKey: ['weather'], queryFn: () => fetchWeather() })

  const totalKw = wind?.reduce((s: number, a: any) => s + a.power_kw, 0) ?? 0

  const chartData = wind?.map((a: any) => ({
    id: a.asset_id,
    kw: Math.round(a.power_kw),
    vib: a.vibration_mm_s.toFixed(2),
  })) ?? []

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1><Wind size={20} style={{ color: 'var(--color-wind)' }} /> Wind Generation</h1>
        <StatusBadge label="SIMULATED" variant="info" />
      </div>

      <div className={styles.metrics}>
        <MetricCard title="Total Wind" value={(totalKw / 1000).toFixed(2)} unit="MW" accent="wind" />
        <MetricCard title="Wind Speed" value={weather ? weather.wind_speed_ms.toFixed(1) : '—'} unit="m/s" accent="wind" />
        <MetricCard title="Wind Direction" value={weather ? `${Math.round(weather.wind_direction)}°` : '—'} />
        <MetricCard title="Active Turbines" value={wind?.length ?? 0} accent="green" />
      </div>

      {!isLoading && (
        <div className={styles.chartCard}>
          <div className={styles.chartTitle}>Power Output per Turbine (kW)</div>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="id" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="kw" fill="#4DA3D9" name="Power (kW)" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
          <div className={styles.dataLabel}>SOURCE: SIMULATED</div>
        </div>
      )}

      <div className={styles.table}>
        <table>
          <thead>
            <tr>
              <th>Asset ID</th>
              <th>Power (kW)</th>
              <th>Wind (m/s)</th>
              <th>RPM</th>
              <th>Gen. Temp (°C)</th>
              <th>Vibration (mm/s)</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {wind?.map((a: any) => (
              <tr key={a.asset_id}>
                <td><strong>{a.asset_id}</strong></td>
                <td>{a.power_kw.toFixed(1)}</td>
                <td>{a.wind_speed_ms.toFixed(1)}</td>
                <td>{a.turbine_rpm.toFixed(0)}</td>
                <td>{a.generator_temperature_c.toFixed(1)}</td>
                <td>{a.vibration_mm_s.toFixed(2)}</td>
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
