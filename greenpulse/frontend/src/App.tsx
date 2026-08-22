import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useSplash } from './hooks/useSplash'
import Layout from './components/Layout'
import DashboardPage from './pages/DashboardPage'
import SolarPage from './pages/SolarPage'
import WindPage from './pages/WindPage'
import ForecastPage from './pages/ForecastPage'
import GridPage from './pages/GridPage'
import AlertsPage from './pages/AlertsPage'
import AssetsPage from './pages/AssetsPage'
import MaintenancePage from './pages/MaintenancePage'
import AIAssistantPage from './pages/AIAssistantPage'
import SimulationPage from './pages/SimulationPage'

const queryClient = new QueryClient({
  defaultOptions: { queries: { refetchInterval: 15_000, staleTime: 10_000 } },
})

export default function App() {
  useSplash()   // dismisses the #gp-splash element from index.html

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<DashboardPage />} />
            <Route path="solar" element={<SolarPage />} />
            <Route path="wind" element={<WindPage />} />
            <Route path="forecast" element={<ForecastPage />} />
            <Route path="grid" element={<GridPage />} />
            <Route path="alerts" element={<AlertsPage />} />
            <Route path="assets" element={<AssetsPage />} />
            <Route path="maintenance" element={<MaintenancePage />} />
            <Route path="ai" element={<AIAssistantPage />} />
            <Route path="simulation" element={<SimulationPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
