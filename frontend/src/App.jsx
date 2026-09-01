// ============================================================
//  GRYPHONE — main application component (v48)
// ============================================================
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import MonitorPage from './pages/MonitorPage'
import StatusPage from './pages/StatusPage'
import AnalyticsPage from './pages/AnalyticsPage'
import ReportsPage from './pages/ReportsPage'
import CamerasPage from './pages/CamerasPage'
import SetsPage from './pages/SetsPage'
import SettingsPage from './pages/SettingsPage'
import HelpPage from './pages/HelpPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MonitorPage />} />
        <Route path="/status" element={<StatusPage />} />
        <Route path="/analytics" element={<AnalyticsPage />} />
        <Route path="/reports" element={<ReportsPage />} />
        <Route path="/cameras" element={<CamerasPage />} />
        <Route path="/sets" element={<SetsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/help" element={<HelpPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
