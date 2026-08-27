// ============================================================
//  GRYPHONE — analytics page (placeholder for future)
// ============================================================
import { Link } from 'react-router-dom'
import Header from '../components/Header'

export default function AnalyticsPage() {
  return (
    <div className="page" style={{ overflowY: 'auto', height: 'auto', minHeight: '100vh' }}>
      <Header />
      <h1 className="page-title">📈 Аналитика</h1>
      <div className="placeholder-card">
        <div className="placeholder-icon">📈</div>
        <h2>Раздел в разработке</h2>
        <p>Здесь будет аналитика по камерам, событиям и нагрузке системы.</p>
        <Link to="/" className="btn btn-primary">← На главную</Link>
      </div>
    </div>
  )
}
