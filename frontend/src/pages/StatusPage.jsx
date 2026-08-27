// ============================================================
//  GRYPHONE — status page (dashboard moved from settings)
// ============================================================
import Header from '../components/Header'
import Dashboard from '../components/Dashboard'
import Toasts from '../components/Toasts'

export default function StatusPage() {
  return (
    <div className="page" style={{ overflowY: 'auto', height: 'auto', minHeight: '100vh' }}>
      <Header />
      <h1 className="page-title">📊 Состояние системы</h1>
      <div className="tab-content">
        <Dashboard />
      </div>
      <Toasts />
    </div>
  )
}
