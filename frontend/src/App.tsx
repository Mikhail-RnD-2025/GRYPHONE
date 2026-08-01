import { useState, useEffect } from 'react';
import axios from 'axios';
import StreamCard from './components/StreamCard';
import './App.css';

interface Camera {
  id: string;
  name: string;
  enabled: boolean;
  comment: string;
  _m: string;
  _s: string;
  status?: string;
}

interface StreamStats {
  [key: string]: {
    state: 'ok' | 'err' | 'checking';
    msg?: string;
    metrics?: {
      fps?: number;
      bitrate?: string;
      time?: string;
    };
  };
}

interface SetInfo {
  max_columns?: number;
  max_rows?: number;
  camera_ids?: string[];
  aspect_ratio?: string;
  name?: string;
}

interface Sets {
  [key: string]: SetInfo;
}

function App() {
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [sets, setSets] = useState<Sets>({});
  const [currentSet, setCurrentSet] = useState<string>('');
  const [stats, setStats] = useState<StreamStats>({});
  const [loading, setLoading] = useState(true);
  const [gridConfig, setGridConfig] = useState({ columns: 2, rows: 0 });

  // Load initial data
  useEffect(() => {
    const loadData = async () => {
      try {
        const response = await axios.get('/api/data');
        const { cameras: cams, sets: setsData } = response.data;
        
        setCameras(cams.map((cam: any) => ({
          ...cam,
          _m: `${cam.id}_main`,
          _s: `${cam.sub_url === cam.main_url ? '_main' : '_sub'}`,
        })));
        
        const setsObj = setsData.sets || {};
        setSets(setsObj);
        
        const defaultSet = setsData.default_set || Object.keys(setsObj)[0] || '';
        setCurrentSet(defaultSet);
        
        // Обновляем конфигурацию сетки
        if (setsObj[defaultSet]) {
          setGridConfig({
            columns: setsObj[defaultSet].max_columns || 2,
            rows: setsObj[defaultSet].max_rows || 0
          });
        }
      } catch (error) {
        console.error('Failed to load data:', error);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, []);

  // SSE connection for stream status
  useEffect(() => {
    const evtSource = new EventSource('/api/stream_status');
    
    evtSource.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        setStats(data);
      } catch (err) {
        console.error('SSE parse error:', err);
      }
    };

    evtSource.onerror = () => {
      console.warn('SSE connection lost, reconnecting...');
    };

    return () => {
      evtSource.close();
    };
  }, []);

  // Handle set change
  const handleSetChange = async (setId: string) => {
    setCurrentSet(setId);
    const setData = sets[setId];
    if (setData) {
      setGridConfig({
        columns: setData.max_columns || 2,
        rows: setData.max_rows || 0
      });
    }
  };

  // Handle toggle camera
  const handleToggleCamera = async (cameraId: string, enabled: boolean) => {
    try {
      await axios.post('/api/toggle_camera', {
        camera_id: cameraId,
        enabled,
      });
      
      setCameras(prev =>
        prev.map(cam =>
          cam.id === cameraId ? { ...cam, enabled } : cam
        )
      );
    } catch (error) {
      console.error('Failed to toggle camera:', error);
    }
  };

  // Handle save comment
  const handleSaveComment = async (cameraId: string, comment: string) => {
    try {
      await axios.post('/api/camera_comment', {
        camera_id: cameraId,
        comment,
      });
      
      setCameras(prev =>
        prev.map(cam =>
          cam.id === cameraId ? { ...cam, comment } : cam
        )
      );
    } catch (error) {
      console.error('Failed to save comment:', error);
    }
  };

  if (loading) {
    return <div className="loading">Загрузка GPYPHONE...</div>;
  }

  // Фильтруем камеры по текущему набору
  const currentSetData = sets[currentSet];
  const displayedCameras = currentSetData?.camera_ids 
    ? cameras.filter(cam => currentSetData.camera_ids!.includes(cam.id))
    : cameras;

  // Ограничиваем количество камер по строкам
  const maxCameras = gridConfig.rows > 0 
    ? gridConfig.columns * gridConfig.rows 
    : displayedCameras.length;
  
  const finalCameras = displayedCameras.slice(0, maxCameras);
  const hiddenCount = displayedCameras.length - finalCameras.length;

  return (
    <div className="app">
      <header className="app-header">
        <h1>📹 GPYPHONE</h1>
        <div className="header-controls">
          {Object.keys(sets).length > 0 && (
            <select
              value={currentSet}
              onChange={(e) => handleSetChange(e.target.value)}
              className="set-selector"
            >
              {Object.entries(sets).map(([setId, setData]) => (
                <option key={setId} value={setId}>
                  {setData.name || setId}
                </option>
              ))}
            </select>
          )}
          <a href="/settings" className="settings-link" title="Настройки">
            ⚙️
          </a>
        </div>
      </header>

      <main className="grid-container">
        {finalCameras.length === 0 ? (
          <div className="alert">
            📭 Наборы не созданы. Перейдите в{' '}
            <a href="/settings">Настройки</a>.
          </div>
        ) : (
          <>
            <div 
              className="grid"
              style={{
                gridTemplateColumns: `repeat(${gridConfig.columns}, minmax(320px, 1fr))`
              }}
            >
              {finalCameras.map((camera) => (
                <StreamCard
                  key={camera.id}
                  camera={camera}
                  stats={stats[camera._s]}
                  onToggle={handleToggleCamera}
                  onSaveComment={handleSaveComment}
                />
              ))}
            </div>
            {hiddenCount > 0 && (
              <div className="hidden-cameras-info">
                Скрыто камер: {hiddenCount} (настройте в параметрах набора)
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}

export default App;
