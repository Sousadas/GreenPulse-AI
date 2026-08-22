import { useQuery } from '@tanstack/react-query'
import { fetchSolarGeneration, fetchWeather } from '../services/api'
import MetricCard from '../components/MetricCard'
import StatusBadge from '../components/StatusBadge'
import { Sun, Thermometer } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import styles from './GenericPage.module.css'

export default function SolarPage() {
  const { data: solar, isLoading } = useQuery({ queryKey: ['solar'], queryFn: fetchSolarGeneration })
  const { data: weather } = useQuery({ queryKey: ['weather'], queryFn: () => fetchWeather() })

  const totalKw = solar?.reduce((s: number, a: any) => s + a.power_kw, 0) ?? 0

  const chartData = solar?.map((a: any) => ({
    id: a.asset_id,
    kw: Math.round(a.power_kw),
    eff: Math.round(a.efficiency * 100),
  })) ?? []

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1><Sun size={20} style={{ color: 'var(--color-solar)' }} /> Solar Generation</h1>
        <StatusBadge label="SIMULATED" variant="info" />
      </div>

      <div className={styles.metrics}>
        <MetricCard title="Total Solar" value={(totalKw / 1000).toFixed(2)} unit="MW" accent="solar" />
        <MetricCard title="Irradiance" value={weather ? Math.round(weather.solar_irradiance_w_m2) : '—'} unit="W/m²" accent="solar" icon={<Sun size={14} />} />
        <MetricCard title="Ambient Temp" value={weather ? weather.temperature_c.toFixed(1) : '—'} unit="°C" icon={<Thermometer size={14} />} />
        <MetricCard title="Active Inverters" value={solar?.length ?? 0} sub="Online" accent="green" />
      </div>

      {!isLoading && (
        <div className={styles.chartCard}>
          <div className={styles.chartTitle}>Power Output per Inverter (kW)</div>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="id" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="kw" fill="#F5B942" name="Power (kW)" radius={[3, 3, 0, 0]} />
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
              <th>Efficiency</th>
              <th>Inv. Temp (°C)</th>
              <th>Irradiance (W/m²)</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {solar?.map((a: any) => (
              <tr key={a.asset_id}>
                <td><strong>{a.asset_id}</strong></td>
                <td>{a.power_kw.toFixed(1)}</td>
                <td>{(a.efficiency * 100).toFixed(1)}%</td>
                <td>{a.inverter_temperature_c.toFixed(1)}</td>
                <td>{a.irradiance_w_m2.toFixed(0)}</td>
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
