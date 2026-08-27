// ============================================================
//  GRYPHONE — cameras editor page
// ============================================================
import Header from '../components/Header'
import CamerasEditor from '../components/CamerasEditor'
import Toasts from '../components/Toasts'

export default function CamerasPage() {
  return (
    <div className="page" style={{ overflowY: 'auto', height: 'auto', minHeight: '100vh' }}>
      <Header />
      <h1 className="page-title">📹 Редактор камер</h1>
      <div className="tab-content">
        <CamerasEditor />
      </div>
      <Toasts />
    </div>
  )
}
