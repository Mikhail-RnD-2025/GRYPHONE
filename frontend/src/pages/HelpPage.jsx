// ============================================================
//  GRYPHONE — страница справки (/help)
//  ВОЗВРАЩЕНО (v37)
// ============================================================
import Header from '../components/Header'
import Help from '../components/Help'

export default function HelpPage() {
  return (
    <div className="page" style={{ overflowY: 'auto', height: 'auto', minHeight: '100vh' }}>
      <Header />
      <h1 className="page-title">❓ Справка</h1>
      <Help />
    </div>
  )
}
