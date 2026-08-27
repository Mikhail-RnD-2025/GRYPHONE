// ============================================================
//  GRYPHONE — reports page (placeholder for future)
// ============================================================
import { Link } from 'react-router-dom'
import Header from '../components/Header'

export default function ReportsPage() {
  return (
    <div className="page" style={{ overflowY: 'auto', height: 'auto', minHeight: '100vh' }}>
      <Header />
      <h1 className="page-title">📋 Отчёты</h1>
      <div className="placeholder-card">
        <div className="placeholder-icon">📋</div>
        <h2>Раздел в разработке</h2>
        <p>Здесь будут отчёты по доступности камер, событиям и архивам.</p>
        <Link to="/" className="btn btn-primary">← На главную</Link>
      </div>
    </div>
  )
}
