import { useQuery } from '@tanstack/react-query'
import { fetchForecast } from '../services/api'
import StatusBadge from '../components/StatusBadge'
import { TrendingUp } from 'lucide-react'
import {
  ComposedChart, Area, Line, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid, Legend
} from 'recharts'
import { format } from 'date-fns'
import styles from './GenericPage.module.css'

export default function ForecastPage() {
  const { data: forecast } = useQuery({ queryKey: ['forecast24'], queryFn: () => fetchForecast(24) })

  const chartData = forecast?.map((p: any) => ({
    time: format(new Date(p.timestamp), 'HH:mm'),
    forecast: Math.round(p.predicted_generation_kw),
    lower: Math.round(p.lower_bound),
    upper: Math.round(p.upper_bound),
    confidence: Math.round(p.confidence * 100),
  })) ?? []

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1><TrendingUp size={20} /> 24-Hour Generation Forecast</h1>
        <StatusBadge label="FORECAST" variant="wind" />
      </div>

      <div className={styles.chartCard}>
        <div className={styles.chartTitle}>Hybrid Generation Forecast with Uncertainty Band (kW)</div>
        <ResponsiveContainer width="100%" height={320}>
          <ComposedChart data={chartData}>
            <defs>
              <linearGradient id="bandFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#147D64" stopOpacity={0.15} />
                <stop offset="95%" stopColor="#147D64" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis dataKey="time" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip />
            <Legend />
            <Area dataKey="upper" stroke="none" fill="url(#bandFill)" name="Upper bound" />
            <Line type="monotone" dataKey="forecast" stroke="#147D64" strokeWidth={2} dot={false} name="Forecast (kW)" />
            <Line type="monotone" dataKey="lower" stroke="#147D64" strokeDasharray="4 4" strokeWidth={1} dot={false} name="Lower bound" />
          </ComposedChart>
        </ResponsiveContainer>
        <div className={styles.dataLabel}>SOURCE: FORECAST · MODEL: simulation+statistical · CONFIDENCE: ~85%</div>
      </div>

      <div className={styles.table}>
        <table>
          <thead>
            <tr>
              <th>Time</th>
              <th>Forecast (kW)</th>
              <th>Lower (kW)</th>
              <th>Upper (kW)</th>
              <th>Confidence</th>
            </tr>
          </thead>
          <tbody>
            {chartData.map((r: any, i: number) => (
              <tr key={i}>
                <td>{r.time}</td>
                <td><strong>{r.forecast}</strong></td>
                <td>{r.lower}</td>
                <td>{r.upper}</td>
                <td>{r.confidence}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
