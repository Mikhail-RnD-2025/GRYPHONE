// ============================================================
//  GRYPHONE — cameras editor page
// ============================================================
import Header from '../components/Header'
import CamerasEditor from '../components/CamerasEditor'
import Toasts from '../components/Toasts'

export default function CamerasPage() {
  return (
    <div className="page">
      <Header />
      <h1 className="page-title">📹 Редактор камер</h1>
      <div className="tab-content" style={{
          flex: 1, minHeight: 0, overflow: 'hidden',
          display: 'flex', flexDirection: 'column',
        }}>  {/* PATCH-223.1 */}
        <CamerasEditor />
      </div>
      <Toasts />
    </div>
  )
}
