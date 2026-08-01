import { useState, useEffect } from 'react';
import axios from 'axios';
import './Settings.css';

interface Camera {
  id: string;
  name: string;
  main_url: string;
  sub_url: string;
  enabled: boolean;
  comment: string;
}

interface SetInfo {
  max_columns?: number;
  max_rows?: number;
  camera_ids?: string[];
  aspect_ratio?: string;
  name?: string;
}

interface SetsData {
  default_set: string;
  sets: { [key: string]: SetInfo };
}

interface Config {
  app: {
    default_set: string;
  };
  performance: {
    sse_interval: number;
  };
  paths: {
    hls_cache: string;
    archive: string;
  };
}

function Settings() {
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [sets, setSets] = useState<SetsData>({ default_set: '', sets: {} });
  const [config, setConfig] = useState<Config | null>(null);
  const [activeTab, setActiveTab] = useState<'cameras' | 'sets' | 'config'>('cameras');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);

  // Загрузка данных
  useEffect(() => {
    const loadData = async () => {
      try {
        const response = await axios.get('/api/data');
        const { cameras: cams, sets: setsData, config: cfg } = response.data;
        setCameras(cams);
        setSets(setsData);
        setConfig(cfg);
      } catch (error) {
        console.error('Failed to load data:', error);
        setMessage({ type: 'error', text: 'Ошибка загрузки данных' });
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, []);

  // Сохранение камер
  const handleSaveCameras = async () => {
    setSaving(true);
    try {
      await axios.post('/api/save', {
        file: 'cameras',
        d: cameras
      });
      setMessage({ type: 'success', text: '✅ Камеры сохранены' });
    } catch (error) {
      setMessage({ type: 'error', text: 'Ошибка сохранения камер' });
    } finally {
      setSaving(false);
      setTimeout(() => setMessage(null), 3000);
    }
  };

  // Сохранение наборов
  const handleSaveSets = async () => {
    setSaving(true);
    try {
      await axios.post('/api/save', {
        file: 'sets',
        d: sets
      });
      setMessage({ type: 'success', text: '✅ Наборы сохранены' });
    } catch (error) {
      setMessage({ type: 'error', text: 'Ошибка сохранения наборов' });
    } finally {
      setSaving(false);
      setTimeout(() => setMessage(null), 3000);
    }
  };

  // Сохранение конфигурации
  const handleSaveConfig = async () => {
    if (!config) return;
    setSaving(true);
    try {
      await axios.post('/api/save', {
        file: 'config',
        d: config
      });
      setMessage({ type: 'success', text: '✅ Конфигурация сохранена' });
    } catch (error) {
      setMessage({ type: 'error', text: 'Ошибка сохранения конфигурации' });
    } finally {
      setSaving(false);
      setTimeout(() => setMessage(null), 3000);
    }
  };

  // Добавление камеры
  const handleAddCamera = () => {
    const newCamera: Camera = {
      id: `cam_${Date.now()}`,
      name: 'Новая камера',
      main_url: 'rtsp://...',
      sub_url: 'rtsp://...',
      enabled: true,
      comment: ''
    };
    setCameras([...cameras, newCamera]);
  };

  // Удаление камеры
  const handleDeleteCamera = (id: string) => {
    setCameras(cameras.filter(c => c.id !== id));
  };

  // Обновление камеры
  const handleUpdateCamera = (id: string, field: keyof Camera, value: any) => {
    setCameras(cameras.map(c => 
      c.id === id ? { ...c, [field]: value } : c
    ));
  };

  // Добавление набора
  const handleAddSet = () => {
    const setId = `set_${Date.now()}`;
    setSets({
      ...sets,
      sets: {
        ...sets.sets,
        [setId]: {
          name: 'Новый набор',
          max_columns: 2,
          max_rows: 0,
          camera_ids: [],
          aspect_ratio: '16:9'
        }
      }
    });
  };

  // Удаление набора
  const handleDeleteSet = (setId: string) => {
    const newSets = { ...sets.sets };
    delete newSets[setId];
    setSets({
      ...sets,
      sets: newSets,
      default_set: sets.default_set === setId ? Object.keys(newSets)[0] || '' : sets.default_set
    });
  };

  // Обновление набора
  const handleUpdateSet = (setId: string, field: keyof SetInfo, value: any) => {
    setSets({
      ...sets,
      sets: {
        ...sets.sets,
        [setId]: {
          ...sets.sets[setId],
          [field]: value
        }
      }
    });
  };

  // Переключение камеры в наборе
  const handleToggleCameraInSet = (setId: string, cameraId: string) => {
    const set = sets.sets[setId];
    if (!set.camera_ids) set.camera_ids = [];
    
    const index = set.camera_ids.indexOf(cameraId);
    if (index === -1) {
      set.camera_ids.push(cameraId);
    } else {
      set.camera_ids.splice(index, 1);
    }
    
    setSets({
      ...sets,
      sets: {
        ...sets.sets,
        [setId]: { ...set }
      }
    });
  };

  if (loading) {
    return <div className="settings-loading">Загрузка настроек...</div>;
  }

  return (
    <div className="settings-page">
      <header className="settings-header">
        <h1>⚙️ Настройки</h1>
        <a href="/" className="back-link">← Назад к камерам</a>
      </header>

      {message && (
        <div className={`message ${message.type}`}>
          {message.text}
        </div>
      )}

      <nav className="settings-tabs">
        <button 
          className={activeTab === 'cameras' ? 'active' : ''}
          onClick={() => setActiveTab('cameras')}
        >
          📹 Камеры
        </button>
        <button 
          className={activeTab === 'sets' ? 'active' : ''}
          onClick={() => setActiveTab('sets')}
        >
          📊 Наборы
        </button>
        <button 
          className={activeTab === 'config' ? 'active' : ''}
          onClick={() => setActiveTab('config')}
        >
          🔧 Конфигурация
        </button>
      </nav>

      <main className="settings-content">
        {/* Вкладка КАМЕРЫ */}
        {activeTab === 'cameras' && (
          <div className="tab-content">
            <div className="tab-header">
              <h2>Управление камерами</h2>
              <button onClick={handleAddCamera} className="btn-add">
                + Добавить камеру
              </button>
            </div>
            
            <div className="cameras-list">
              {cameras.map(camera => (
                <div key={camera.id} className="camera-item">
                  <div className="camera-row">
                    <input
                      type="text"
                      value={camera.name}
                      onChange={(e) => handleUpdateCamera(camera.id, 'name', e.target.value)}
                      placeholder="Название"
                      className="camera-name"
                    />
                    <input
                      type="text"
                      value={camera.main_url}
                      onChange={(e) => handleUpdateCamera(camera.id, 'main_url', e.target.value)}
                      placeholder="Основной поток RTSP"
                      className="camera-url"
                    />
                    <input
                      type="text"
                      value={camera.sub_url}
                      onChange={(e) => handleUpdateCamera(camera.id, 'sub_url', e.target.value)}
                      placeholder="Доп. поток RTSP"
                      className="camera-url"
                    />
                  </div>
                  <div className="camera-row">
                    <input
                      type="text"
                      value={camera.comment}
                      onChange={(e) => handleUpdateCamera(camera.id, 'comment', e.target.value)}
                      placeholder="Комментарий"
                      className="camera-comment"
                    />
                    <label className="camera-enabled">
                      <input
                        type="checkbox"
                        checked={camera.enabled}
                        onChange={(e) => handleUpdateCamera(camera.id, 'enabled', e.target.checked)}
                      />
                      Включена
                    </label>
                    <button 
                      onClick={() => handleDeleteCamera(camera.id)}
                      className="btn-delete"
                    >
                      🗑️
                    </button>
                  </div>
                </div>
              ))}
            </div>
            
            <button 
              onClick={handleSaveCameras} 
              className="btn-save"
              disabled={saving}
            >
              {saving ? 'Сохранение...' : '💾 Сохранить камеры'}
            </button>
          </div>
        )}

        {/* Вкладка НАБОРЫ */}
        {activeTab === 'sets' && (
          <div className="tab-content">
            <div className="tab-header">
              <h2>Наборы камер</h2>
              <button onClick={handleAddSet} className="btn-add">
                + Добавить набор
              </button>
            </div>
            
            <div className="sets-list">
              {Object.entries(sets.sets).map(([setId, setData]) => (
                <div key={setId} className="set-item">
                  <div className="set-header">
                    <input
                      type="text"
                      value={setData.name || setId}
                      onChange={(e) => handleUpdateSet(setId, 'name', e.target.value)}
                      placeholder="Название набора"
                      className="set-name"
                    />
                    <button 
                      onClick={() => handleDeleteSet(setId)}
                      className="btn-delete"
                    >
                      🗑️
                    </button>
                  </div>
                  
                  <div className="set-settings">
                    <div className="setting-row">
                      <label>Колонок:</label>
                      <input
                        type="number"
                        min="1"
                        max="8"
                        value={setData.max_columns || 2}
                        onChange={(e) => handleUpdateSet(setId, 'max_columns', parseInt(e.target.value))}
                      />
                    </div>
                    <div className="setting-row">
                      <label>Строк (0 = без ограничений):</label>
                      <input
                        type="number"
                        min="0"
                        value={setData.max_rows || 0}
                        onChange={(e) => handleUpdateSet(setId, 'max_rows', parseInt(e.target.value))}
                      />
                    </div>
                    <div className="setting-row">
                      <label>Пропорции:</label>
                      <select
                        value={setData.aspect_ratio || '16:9'}
                        onChange={(e) => handleUpdateSet(setId, 'aspect_ratio', e.target.value)}
                      >
                        <option value="16:9">16:9</option>
                        <option value="4:3">4:3</option>
                        <option value="1:1">1:1</option>
                      </select>
                    </div>
                    <div className="setting-row">
                      <label>Набор по умолчанию:</label>
                      <input
                        type="radio"
                        name="default_set"
                        checked={sets.default_set === setId}
                        onChange={() => setSets({ ...sets, default_set: setId })}
                      />
                    </div>
                  </div>
                  
                  <div className="set-cameras">
                    <h4>Камеры в наборе:</h4>
                    <div className="cameras-checkboxes">
                      {cameras.map(camera => (
                        <label key={camera.id} className="camera-checkbox">
                          <input
                            type="checkbox"
                            checked={(setData.camera_ids || []).includes(camera.id)}
                            onChange={() => handleToggleCameraInSet(setId, camera.id)}
                          />
                          {camera.name}
                        </label>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
            
            <button 
              onClick={handleSaveSets} 
              className="btn-save"
              disabled={saving}
            >
              {saving ? 'Сохранение...' : '💾 Сохранить наборы'}
            </button>
          </div>
        )}

        {/* Вкладка КОНФИГУРАЦИЯ */}
        {activeTab === 'config' && config && (
          <div className="tab-content">
            <h2>Конфигурация приложения</h2>
            
            <div className="config-section">
              <h3>Основные настройки</h3>
              <div className="setting-row">
                <label>Набор по умолчанию:</label>
                <select
                  value={config.app.default_set}
                  onChange={(e) => setConfig({
                    ...config,
                    app: { ...config.app, default_set: e.target.value }
                  })}
                >
                  {Object.entries(sets.sets).map(([setId, setData]) => (
                    <option key={setId} value={setId}>
                      {setData.name || setId}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            
            <div className="config-section">
              <h3>Производительность</h3>
              <div className="setting-row">
                <label>SSE интервал (сек):</label>
                <input
                  type="number"
                  step="0.1"
                  min="0.1"
                  value={config.performance?.sse_interval || 1}
                  onChange={(e) => setConfig({
                    ...config,
                    performance: { ...config.performance!, sse_interval: parseFloat(e.target.value) }
                  })}
                />
              </div>
            </div>
            
            <div className="config-section">
              <h3>Пути</h3>
              <div className="setting-row">
                <label>HLS кэш:</label>
                <input
                  type="text"
                  value={config.paths?.hls_cache || 'hls_cache'}
                  onChange={(e) => setConfig({
                    ...config,
                    paths: { ...config.paths!, hls_cache: e.target.value }
                  })}
                />
              </div>
              <div className="setting-row">
                <label>Архив:</label>
                <input
                  type="text"
                  value={config.paths?.archive || 'archive'}
                  onChange={(e) => setConfig({
                    ...config,
                    paths: { ...config.paths!, archive: e.target.value }
                  })}
                />
              </div>
            </div>
            
            <button 
              onClick={handleSaveConfig} 
              className="btn-save"
              disabled={saving}
            >
              {saving ? 'Сохранение...' : '💾 Сохранить конфигурацию'}
            </button>
          </div>
        )}
      </main>
    </div>
  );
}

export default Settings;
