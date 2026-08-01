import { useRef, useState, useEffect, useCallback } from 'react';
import Hls from 'hls.js';
import './StreamCard.css';

interface StreamStats {
  state: 'ok' | 'err' | 'checking';
  msg?: string;
  metrics?: {
    fps?: number;
    bitrate?: string;
    time?: string;
  };
}

interface Camera {
  id: string;
  name: string;
  enabled: boolean;
  comment: string;
  _m: string;
  _s: string;
  status?: string;
}

interface StreamCardProps {
  camera: Camera;
  onToggle?: (cameraId: string, enabled: boolean) => void;
  onSaveComment?: (cameraId: string, comment: string) => void;
  stats?: StreamStats;
}

export default function StreamCard({ 
  camera, 
  onToggle, 
  onSaveComment,
  stats 
}: StreamCardProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [hlsInstance, setHlsInstance] = useState<Hls | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [showOverlay, setShowOverlay] = useState(true);
  const [overlayMessage, setOverlayMessage] = useState('Подключение...');
  const [contextMenuOpen, setContextMenuOpen] = useState(false);
  const [comment, setComment] = useState(camera.comment || '');
  const [streamState, setStreamState] = useState<'ok' | 'err' | 'checking'>('checking');

  const mainUrl = `/hls/camera/${camera._m}/index.m3u8`;
  const subUrl = `/hls/camera/${camera._s}/index.m3u8`;

  // Initialize HLS player
  useEffect(() => {
    if (!videoRef.current || !camera.enabled) return;

    const video = videoRef.current;
    let hls: Hls | null = null;

    const initPlayer = () => {
      if (Hls.isSupported()) {
        hls = new Hls({
          enableWorker: true,
          lowLatencyMode: true,
          backBufferLength: 30,
        });

        hls.loadSource(subUrl);
        hls.attachMedia(video);

        hls.on(Hls.Events.MANIFEST_PARSED, () => {
          video.play().catch(console.warn);
        });

        hls.on(Hls.Events.ERROR, (_, data) => {
          if (data.fatal) {
            console.error(`[HLS Error] ${camera.id}:`, data);
            setStreamState('err');
            setOverlayMessage('Ошибка потока');
            setShowOverlay(true);
            
            switch (data.type) {
              case Hls.ErrorTypes.NETWORK_ERROR:
                hls?.startLoad();
                break;
              case Hls.ErrorTypes.MEDIA_ERROR:
                hls?.recoverMediaError();
                break;
              default:
                hls?.destroy();
                setTimeout(initPlayer, 3000);
                break;
            }
          }
        });

        setHlsInstance(hls);
      } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
        video.src = subUrl;
        video.addEventListener('loadedmetadata', () => {
          video.play().catch(console.warn);
        });
      }
    };

    initPlayer();

    return () => {
      if (hls) {
        hls.destroy();
      }
    };
  }, [camera.id, camera.enabled, camera._s, subUrl]);

  // Monitor stream state from stats
  useEffect(() => {
    if (!stats) return;

    const newState = stats.state;
    setStreamState(newState);

    // Priority 1: Check if video is actually playing
    if (videoRef.current && !videoRef.current.paused && 
        (videoRef.current.readyState >= 2 || videoRef.current.videoWidth > 0)) {
      setShowOverlay(false);
      setIsPlaying(true);
      return;
    }

    // Priority 2: Handle state changes
    if (newState === 'ok') {
      if (streamState === 'err' || streamState === 'checking') {
        setOverlayMessage('🔄 Переподключение...');
        setShowOverlay(true);
        
        // Trigger HLS recovery
        if (hlsInstance && Hls.isSupported()) {
          hlsInstance.startLoad();
        }
      }
    } else if (newState === 'err') {
      setOverlayMessage('Недоступна');
      setShowOverlay(true);
      setIsPlaying(false);
    } else if (newState === 'checking') {
      setOverlayMessage(stats.msg || 'Подключение...');
      setShowOverlay(true);
    }
  }, [stats, streamState, hlsInstance]);

  // Handle video play/pause events
  const handleVideoEvent = useCallback((e: Event) => {
    const video = e.target as HTMLVideoElement;
    setIsPlaying(!video.paused && video.readyState >= 2);
    setShowOverlay(video.paused || video.readyState < 2);
  }, []);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    video.addEventListener('play', handleVideoEvent);
    video.addEventListener('pause', handleVideoEvent);
    video.addEventListener('loadeddata', handleVideoEvent);
    video.addEventListener('error', handleVideoEvent);

    return () => {
      video.removeEventListener('play', handleVideoEvent);
      video.removeEventListener('pause', handleVideoEvent);
      video.removeEventListener('loadeddata', handleVideoEvent);
      video.removeEventListener('error', handleVideoEvent);
    };
  }, [handleVideoEvent]);

  // Context menu handlers
  const handleRightClick = (e: React.MouseEvent) => {
    e.preventDefault();
    setContextMenuOpen(true);
  };

  const handleCloseMenu = () => {
    setContextMenuOpen(false);
  };

  const handleToggleCamera = async () => {
    if (onToggle) {
      await onToggle(camera.id, !camera.enabled);
    }
    setContextMenuOpen(false);
  };

  const handleSaveComment = async () => {
    if (onSaveComment) {
      await onSaveComment(camera.id, comment);
    }
    setContextMenuOpen(false);
  };

  const getStatusDotClass = () => {
    if (isPlaying) return 'dot ok';
    switch (streamState) {
      case 'ok': return 'dot ok';
      case 'err': return 'dot err';
      case 'checking': return 'dot load';
      default: return 'dot';
    }
  };

  return (
    <div 
      className="stream-card"
      data-cam-id={camera.id}
      onContextMenu={handleRightClick}
    >
      {/* Header */}
      <div className="card-header">
        <span className={getStatusDotClass()}></span>
        <span className="cam-name" title={camera.name}>{camera.name}</span>
      </div>

      {/* Video Container */}
      <div className="video-wrapper" onClick={() => setContextMenuOpen(!contextMenuOpen)}>
        <div 
          className={`overlay ${showOverlay ? '' : 'hidden'}`}
          id={`ov-${camera._s}`}
        >
          {overlayMessage}
        </div>
        <video
          ref={videoRef}
          muted
          playsInline
          disablePictureInPicture
          id={`v-${camera._s}`}
        />
      </div>

      {/* Context Menu */}
      {contextMenuOpen && (
        <div className="context-menu" onClick={(e) => e.stopPropagation()}>
          <button 
            className={`ctx-toggle ${camera.enabled ? 'enabled' : 'disabled'}`}
            onClick={handleToggleCamera}
          >
            {camera.enabled ? '🔴 Отключить' : '🟢 Включить'}
          </button>

          {stats?.metrics && (
            <div className="ctx-metrics">
              <div className="ctx-item">
                <span className="ctx-label">🎥 FPS</span>
                <span className="ctx-value">{stats.metrics.fps ?? '--'}</span>
              </div>
              <div className="ctx-item">
                <span className="ctx-label">📶 Bitrate</span>
                <span className="ctx-value">{stats.metrics.bitrate ?? '--'}</span>
              </div>
              <div className="ctx-item">
                <span className="ctx-label">⏱️ Time</span>
                <span className="ctx-value">{stats.metrics.time ?? '--'}</span>
              </div>
            </div>
          )}

          <div className="ctx-urls">
            <div>
              <span>🔗 Main:</span>{' '}
              <span className="ctx-url" title={mainUrl}>{mainUrl}</span>
            </div>
            <div>
              <span>🔗 Sub:</span>{' '}
              <span className="ctx-url" title={subUrl}>{subUrl}</span>
            </div>
          </div>

          <div className="ctx-comment-section">
            <textarea
              id="ctx-comment"
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="📝 Комментарий..."
            />
            <button id="ctx-save-comment" onClick={handleSaveComment}>
              💾 Сохранить
            </button>
          </div>

          <button className="ctx-close" onClick={handleCloseMenu}>
            ✕ Закрыть
          </button>
        </div>
      )}
    </div>
  );
}
