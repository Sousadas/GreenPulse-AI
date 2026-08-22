import { useQuery } from '@tanstack/react-query'
import { Sun, Wind, Zap, Bell, Activity, Shield } from 'lucide-react'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Legend,
} from 'recharts'
import MetricCard from '../components/MetricCard'
import StatusBadge from '../components/StatusBadge'
import {
  fetchGridStatus,
  fetchSolarGeneration,
  fetchWindGeneration,
  fetchAlerts,
  fetchForecast,
  fetchMaintenanceRisks,
  fetchGridRecommendation,
} from '../services/api'
import styles from './DashboardPage.module.css'
import { format } from 'date-fns'

export default function DashboardPage() {
  const { data: grid } = useQuery({
    queryKey: ['grid'],
    queryFn: fetchGridStatus,
  })

  const { data: gridRec } = useQuery({
    queryKey: ['gridRec'],
    queryFn: fetchGridRecommendation,
  })

  const { data: solar } = useQuery({
    queryKey: ['solar'],
    queryFn: fetchSolarGeneration,
  })

  const { data: wind } = useQuery({
    queryKey: ['wind'],
    queryFn: fetchWindGeneration,
  })

  const { data: alerts } = useQuery({
    queryKey: ['alerts'],
    queryFn: () => fetchAlerts(),
  })

  const { data: forecast } = useQuery({
    queryKey: ['forecast'],
    queryFn: () => fetchForecast(12),
  })

  const { data: risks } = useQuery({
    queryKey: ['maintenance'],
    queryFn: fetchMaintenanceRisks,
  })

  const totalSolarKw =
    solar?.reduce((s: number, a: any) => s + a.power_kw, 0) ?? 0

  const totalWindKw =
    wind?.reduce((s: number, a: any) => s + a.power_kw, 0) ?? 0

  const totalMw = (totalSolarKw + totalWindKw) / 1000

  const criticalAlerts =
    alerts?.filter(
      (a: any) =>
        a.severity === 'CRITICAL' || a.severity === 'HIGH'
    ).length ?? 0

  const openAlerts = alerts?.length ?? 0

  const criticalRisks =
    risks?.filter(
      (r: any) =>
        r.maintenance_risk === 'CRITICAL' ||
        r.maintenance_risk === 'HIGH'
    ).length ?? 0

  const forecastData =
    forecast?.slice(0, 12).map((p: any) => ({
      time: format(new Date(p.timestamp), 'HH:mm'),
      kw: Math.round(p.predicted_generation_kw),
      lower: Math.round(p.lower_bound),
      upper: Math.round(p.upper_bound),
    })) ?? []

  return (
    <div className={styles.page}>

      {/* Header */}
      <div className={styles.pageHeader}>
        <div>
          <h1>Operations Dashboard</h1>
          <p className={styles.headerSubtitle}>
            Renewable energy operations overview
          </p>
        </div>

        <div className={styles.headerBadges}>
          <StatusBadge label="SIMULATED" variant="info" />

          {gridRec && (
            <StatusBadge
              label={`Grid: ${gridRec.action}`}
              variant={
                gridRec.action === 'IMPORT'
                  ? 'warning'
                  : gridRec.action.startsWith('EXPORT')
                    ? 'success'
                    : 'muted'
              }
            />
          )}
        </div>
      </div>

      {/* Metrics */}
      <div className={styles.metrics}>
        <MetricCard
          title="Total Generation"
          value={totalMw.toFixed(2)}
          unit="MW"
          sub="Solar + Wind"
          accent="green"
          icon={<Activity size={16} />}
        />

        <MetricCard
          title="Solar Generation"
          value={(totalSolarKw / 1000).toFixed(2)}
          unit="MW"
          sub={`${solar?.length ?? 0} inverters`}
          accent="solar"
          icon={<Sun size={16} />}
        />

        <MetricCard
          title="Wind Generation"
          value={(totalWindKw / 1000).toFixed(2)}
          unit="MW"
          sub={`${wind?.length ?? 0} turbines`}
          accent="wind"
          icon={<Wind size={16} />}
        />

        <MetricCard
          title="Grid Surplus"
          value={
            grid
              ? grid.renewable_surplus_mw.toFixed(2)
              : '—'
          }
          unit="MW"
          sub={
            grid
              ? `Export: ${grid.grid_export_mw.toFixed(2)} MW`
              : ''
          }
          accent={
            grid?.renewable_surplus_mw >= 0
              ? 'green'
              : 'warning'
          }
          icon={<Zap size={16} />}
        />

        <MetricCard
          title="Active Alerts"
          value={openAlerts}
          sub={`${criticalAlerts} high/critical`}
          accent={criticalAlerts > 0 ? 'critical' : undefined}
          icon={<Bell size={16} />}
        />

        <MetricCard
          title="Maintenance Risks"
          value={criticalRisks}
          sub="High or critical"
          accent={criticalRisks > 0 ? 'warning' : undefined}
          icon={<Shield size={16} />}
        />
      </div>

      {/* Main charts */}
      <div className={styles.charts}>

        {/* Forecast */}
        <div className={styles.chartCard}>
          <div className={styles.chartHeader}>
            <div>
              <div className={styles.chartTitle}>
                12-Hour Hybrid Generation Forecast
              </div>
              <div className={styles.chartSubtitle}>
                Predicted renewable generation
              </div>
            </div>

            <span className={styles.chartUnit}>kW</span>
          </div>

          <div className={styles.chartArea}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={forecastData}>
                <defs>
                  <linearGradient
                    id="gFill"
                    x1="0"
                    y1="0"
                    x2="0"
                    y2="1"
                  >
                    <stop
                      offset="5%"
                      stopColor="#147D64"
                      stopOpacity={0.3}
                    />
                    <stop
                      offset="95%"
                      stopColor="#147D64"
                      stopOpacity={0}
                    />
                  </linearGradient>
                </defs>

                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="#e5e7eb"
                />

                <XAxis
                  dataKey="time"
                  tick={{ fontSize: 11 }}
                />

                <YAxis
                  tick={{ fontSize: 11 }}
                />

                <Tooltip />

                <Legend
                  wrapperStyle={{
                    fontSize: 11,
                    paddingTop: 4,
                  }}
                />

                <Area
                  type="monotone"
                  dataKey="upper"
                  stroke="none"
                  fill="#147D64"
                  fillOpacity={0.1}
                  name="Upper bound"
                />

                <Area
                  type="monotone"
                  dataKey="kw"
                  stroke="#147D64"
                  fill="url(#gFill)"
                  strokeWidth={2}
                  name="Forecast (kW)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          <div className={styles.dataLabel}>
            SOURCE: FORECAST · MODEL: greenpulse-stat-v1
          </div>
        </div>

        {/* Operational status */}
        <div className={styles.chartCard}>
          <div className={styles.chartHeader}>
            <div>
              <div className={styles.chartTitle}>
                Operational Status
              </div>
              <div className={styles.chartSubtitle}>
                Current system condition
              </div>
            </div>

            <Activity size={17} />
          </div>

          <div className={styles.statusContent}>

            {gridRec && (
              <div className={styles.recBlock}>
                <div className={styles.recLabel}>
                  Grid Advisory
                </div>

                <div className={styles.recText}>
                  {gridRec.recommendation}
                </div>

                <div className={styles.dataLabel}>
                  Renewable: {gridRec.renewable_generation_mw} MW
                  {' · '}
                  Load: {gridRec.grid_load_mw} MW
                  {' · '}
                  {gridRec.renewable_percentage}% renewable
                </div>
              </div>
            )}

            {openAlerts > 0 && (
              <div>
                <div
                  className={styles.recLabel}
                  style={{ marginBottom: 8 }}
                >
                  Active Alerts
                </div>

                {alerts?.map((a: any) => (
                  <div
                    key={a.alert_id}
                    className={styles.alertRow}
                  >
                    <StatusBadge
                      label={a.severity}
                      variant={
                        a.severity === 'CRITICAL' ||
                        a.severity === 'HIGH'
                          ? 'critical'
                          : 'warning'
                      }
                    />

                    <span>
                      <strong>{a.asset_id}</strong>
                      {' — '}
                      {a.description}
                    </span>
                  </div>
                ))}
              </div>
            )}

            {openAlerts === 0 && (
              <div className={styles.systemHealthy}>
                <span className={styles.healthDot} />
                <div>
                  <strong>System operating normally</strong>
                  <span>
                    No active alerts detected.
                  </span>
                </div>
              </div>
            )}

          </div>
        </div>
      </div>

      {/* System overview */}
      <div className={styles.overview}>

        <div className={styles.overviewCard}>
          <div className={styles.overviewIcon}>
            <Sun size={18} />
          </div>

          <div>
            <span>Solar Assets</span>
            <strong>{solar?.length ?? 0}</strong>
            <small>Active inverters</small>
          </div>
        </div>

        <div className={styles.overviewCard}>
          <div className={styles.overviewIcon}>
            <Wind size={18} />
          </div>

          <div>
            <span>Wind Assets</span>
            <strong>{wind?.length ?? 0}</strong>
            <small>Active turbines</small>
          </div>
        </div>

        <div className={styles.overviewCard}>
          <div className={styles.overviewIcon}>
            <Bell size={18} />
          </div>

          <div>
            <span>Alerts</span>
            <strong>{openAlerts}</strong>
            <small>
              {criticalAlerts > 0
                ? `${criticalAlerts} high/critical`
                : 'No high/critical alerts'}
            </small>
          </div>
        </div>

        <div className={styles.overviewCard}>
          <div className={styles.overviewIcon}>
            <Shield size={18} />
          </div>

          <div>
            <span>Maintenance</span>
            <strong>{criticalRisks}</strong>
            <small>
              {criticalRisks > 0
                ? 'High or critical'
                : 'No critical risks'}
            </small>
          </div>
        </div>

      </div>

    </div>
  )
}