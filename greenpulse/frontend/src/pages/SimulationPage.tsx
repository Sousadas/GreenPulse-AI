import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { postSimulationFault, fetchSimulationStatus } from '../services/api'
import StatusBadge from '../components/StatusBadge'
import { Settings } from 'lucide-react'
import styles from './SimulationPage.module.css'

const SCENARIOS = [
  { id: 'NORMAL', label: 'Normal Operation', description: 'All assets operating within normal parameters.' },
  { id: 'SOLAR_INVERTER_DEGRADATION', label: 'Solar Inverter Degradation', description: 'SOL-INV-042 begins to degrade — temperature rises, efficiency and power drop.' },
  { id: 'WIND_TURBINE_OVERHEATING', label: 'Wind Turbine Overheating', description: 'WT-017 generator temperature and vibration increase beyond thresholds.' },
  { id: 'HIGH_WIND_EVENT', label: 'High Wind Event', description: 'Wind speed increases significantly across the wind farm.' },
  { id: 'CLOUD_COVER_EVENT', label: 'Cloud Cover Event', description: 'Heavy cloud cover reduces solar irradiance and generation.' },
  { id: 'RENEWABLE_SURPLUS', label: 'Renewable Surplus', description: 'Generation exceeds grid demand — surplus available for export.' },
  { id: 'GRID_DEMAND_INCREASE', label: 'Grid Demand Increase', description: 'Grid load increases — risk of deficit if generation is insufficient.' },
]

export default function SimulationPage() {
  const [intensity, setIntensity] = useState(1.0)
  const { data: status, refetch } = useQuery({ queryKey: ['simStatus'], queryFn: fetchSimulationStatus })

  const mutation = useMutation({
    mutationFn: ({ scenario, intensity }: { scenario: string; intensity: number }) =>
      postSimulationFault(scenario, intensity),
    onSuccess: () => refetch(),
  })

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1><Settings size={20} /> Simulation Control</h1>
        {status && (
          <StatusBadge label={`Active: ${status.active_scenario}`} variant="info" />
        )}
      </div>

      <div className={styles.notice}>
        This control panel injects fault scenarios into the simulation engine to demonstrate how agents detect and respond to anomalies.
      </div>

      <div className={styles.intensityRow}>
        <label>Scenario Intensity: <strong>{intensity.toFixed(1)}</strong></label>
        <input
          type="range" min={0.1} max={1.0} step={0.1}
          value={intensity}
          onChange={e => setIntensity(parseFloat(e.target.value))}
          className={styles.slider}
        />
      </div>

      <div className={styles.grid}>
        {SCENARIOS.map(s => (
          <div
            key={s.id}
            className={`${styles.card} ${status?.active_scenario === s.id ? styles.active : ''}`}
          >
            <div className={styles.cardTitle}>{s.label}</div>
            <div className={styles.cardDesc}>{s.description}</div>
            <button
              className={styles.btn}
              disabled={mutation.isPending}
              onClick={() => mutation.mutate({ scenario: s.id, intensity })}
            >
              {status?.active_scenario === s.id ? '✓ Active' : 'Activate'}
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
