#!/usr/bin/env bash
# ============================================================
#  GRYPHONE — скрипт 42: АВТОСКРЫВАЕМАЯ ШАПКА
#  ------------------------------------------------------------
#  Что делает:
#    1. Шапка приложения плавно наезжает сверху и исчезает
#    2. Автоскрытие через 3 секунды бездействия мыши
#    3. Появление при движении мыши
#    4. В полноэкранном режиме та же логика
#    5. На странице настроек шапка всегда видна
#
#  ЗАПУСК:  bash update_scripts/42_auto_hide_header.sh
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -f "$SCRIPT_DIR/main.py" ]; then
    PROJECT_DIR="$SCRIPT_DIR"
else
    PROJECT_DIR="${PROJECT_DIR:-$(dirname "$SCRIPT_DIR")}"
fi

echo "📁 Корень проекта: $PROJECT_DIR"
cd "$PROJECT_DIR"
echo "📂 Рабочая директория: $(pwd)"

# ============================================================
# ЧАСТЬ 1: Обновление Header.jsx — автоскрытие на мониторинге
# ============================================================
echo ""
echo "🔧 Обновляю шапку приложения..."

cat > "$PROJECT_DIR/frontend/src/components/Header.jsx" << 'HEADER_END'
// ============================================================
//  GRYPHONE — шапка приложения
//  ИСПРАВЛЕНО (v42):
//  • Автоскрытие через 3 секунды бездействия (только на мониторинге)
//  • Появление при движении мыши
//  • Плавная анимация наезда сверху
//  • На странице настроек шапка всегда видна
// ============================================================
import { useState, useEffect, useRef, useCallback } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { getSets, switchSet } from '../api'

export default function Header() {
  const [sets, setSets] = useState({})
  const [currentSet, setCurrentSet] = useState('')
  const [clock, setClock] = useState('')
  const [visible, setVisible] = useState(true)
  const hideTimerRef = useRef(null)
  const location = useLocation()

  const isSettingsPage = location.pathname === '/settings'
  const isMonitorPage = location.pathname === '/'

  useEffect(() => {
    loadSets()
  }, [])

  useEffect(() => {
    const updateClock = () => {
      const now = new Date()
      setClock(now.toLocaleTimeString('ru-RU', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      }))
    }
    updateClock()
    const interval = setInterval(updateClock, 1000)
    return () => clearInterval(interval)
  }, [])

  // ИСПРАВЛЕНО (v42): автоскрытие только на странице мониторинга
  useEffect(() => {
    if (!isMonitorPage) {
      setVisible(true)
      return
    }

    const showHeader = () => {
      setVisible(true)
      if (hideTimerRef.current) clearTimeout(hideTimerRef.current)
      hideTimerRef.current = setTimeout(() => setVisible(false), 3000)
    }

    showHeader()

    window.addEventListener('mousemove', showHeader)
    window.addEventListener('mousedown', showHeader)
    window.addEventListener('touchstart', showHeader)

    return () => {
      window.removeEventListener('mousemove', showHeader)
      window.removeEventListener('mousedown', showHeader)
      window.removeEventListener('touchstart', showHeader)
      if (hideTimerRef.current) clearTimeout(hideTimerRef.current)
    }
  }, [isMonitorPage])

  const loadSets = async () => {
    try {
      const data = await getSets()
      setSets(data.sets || {})
      setCurrentSet(data.default_set || '')
    } catch (e) {
      console.error('Ошибка загрузки наборов:', e)
    }
  }

  const handleSetChange = async (e) => {
    const setId = e.target.value
    setCurrentSet(setId)
    try {
      await switchSet(setId)
    } catch (e) {
      console.error('Ошибка переключения набора:', e)
    }
  }

  return (
    <div className={`header ${isMonitorPage && !visible ? 'header-hidden' : ''}`}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <h1 className="header-title" style={{ margin: 0 }}>GRYPHONE</h1>

        {!isSettingsPage && Object.keys(sets).length > 0 && (
          <select
            className="set-selector"
            value={currentSet}
            onChange={handleSetChange}
          >
            {Object.entries(sets).map(([id, set]) => (
              <option key={id} value={id}>
                {set.name}
              </option>
            ))}
          </select>
        )}

        {isSettingsPage && (
          <Link to="/" className="btn">
            ← Назад к камерам
          </Link>
        )}
      </div>

      <div className="header-clock">{clock}</div>
    </div>
  )
}
HEADER_END
echo "  ✔ frontend/src/components/Header.jsx (автоскрытие)"

# ============================================================
# ЧАСТЬ 2: Обновление FullscreenCamera.jsx — анимация наезда
# ============================================================
echo ""
echo "🔧 Обновляю шапку полноэкранного режима..."

cat > "$PROJECT_DIR/frontend/src/components/FullscreenCamera.jsx" << 'FULLSCREEN_END'
// ============================================================
//  GRYPHONE — полноэкранное окно камеры
//  ИСПРАВЛЕНО (v42):
//  • Шапка плавно наезжает сверху (transform: translateY)
//  • Автоскрытие через 3 секунды бездействия
//  • Появление при движении мыши
// ============================================================
import { useEffect, useRef, useState, useCallback } from 'react'
import Hls from 'hls.js'

export default function FullscreenCamera({ camera, onClose }) {
  const videoRef = useRef(null)
  const hlsRef = useRef(null)
  const overlayRef = useRef(null)
  const hideTimerRef = useRef(null)
  const [error, setError] = useState(null)
  const [showInfo, setShowInfo] = useState(true)

  const onCloseRef = useRef(onClose)
  useEffect(() => {
    onCloseRef.current = onClose
  }, [onClose])

  const handleClose = useCallback(() => {
    onCloseRef.current()
  }, [])

  const routeId = `${camera.id}_main`
  const streamUrl = `/hls/camera/${routeId}/index.m3u8`

  useEffect(() => {
    if (!videoRef.current) return
    setError(null)

    if (Hls.isSupported()) {
      const hls = new Hls({
        liveSyncDurationCount: 2,
        liveMaxLatencyDurationCount: 4,
        lowLatencyMode: true,
      })
      hls.loadSource(streamUrl)
      hls.attachMedia(videoRef.current)
      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        videoRef.current.play().catch(() => {})
      })
      hls.on(Hls.Events.ERROR, (event, data) => {
        if (data.fatal) {
          setError('Поток недоступен')
          hls.destroy()
          hlsRef.current = null
        }
      })
      hlsRef.current = hls
    } else if (videoRef.current.canPlayType('application/vnd.apple.mpegurl')) {
      videoRef.current.src = streamUrl
      videoRef.current.play().catch(() => setError('Не удалось воспроизвести'))
    }
    return () => {
      if (hlsRef.current) {
        hlsRef.current.destroy()
        hlsRef.current = null
      }
    }
  }, [streamUrl])

  // ИСПРАВЛЕНО (v42): автоскрытие с анимацией наезда
  useEffect(() => {
    const showInfoTemporarily = () => {
      setShowInfo(true)
      if (hideTimerRef.current) clearTimeout(hideTimerRef.current)
      hideTimerRef.current = setTimeout(() => setShowInfo(false), 3000)
    }

    showInfoTemporarily()

    window.addEventListener('mousemove', showInfoTemporarily)
    window.addEventListener('mousedown', showInfoTemporarily)
    window.addEventListener('touchstart', showInfoTemporarily)

    return () => {
      window.removeEventListener('mousemove', showInfoTemporarily)
      window.removeEventListener('mousedown', showInfoTemporarily)
      window.removeEventListener('touchstart', showInfoTemporarily)
      if (hideTimerRef.current) clearTimeout(hideTimerRef.current)
    }
  }, [])

  useEffect(() => {
    const el = overlayRef.current
    if (!el) return

    let unmounted = false

    const requestFs = async () => {
      try {
        if (el.requestFullscreen) {
          await el.requestFullscreen()
        } else if (el.webkitRequestFullscreen) {
          el.webkitRequestFullscreen()
        }
      } catch (e) {
        console.warn('Fullscreen API недоступен:', e)
      }
    }

    const timer = setTimeout(requestFs, 150)

    const handleFsChange = () => {
      const active = document.fullscreenElement ||
                     document.webkitFullscreenElement
      if (!active && !unmounted) {
        handleClose()
      }
    }
    document.addEventListener('fullscreenchange', handleFsChange)
    document.addEventListener('webkitfullscreenchange', handleFsChange)

    const handleEsc = (e) => {
      if (e.key === 'Escape' && !document.fullscreenElement) {
        handleClose()
      }
    }
    window.addEventListener('keydown', handleEsc)

    return () => {
      unmounted = true
      clearTimeout(timer)
      document.removeEventListener('fullscreenchange', handleFsChange)
      document.removeEventListener('webkitfullscreenchange', handleFsChange)
      window.removeEventListener('keydown', handleEsc)
    }
  }, [handleClose])

  const handleDoubleClick = () => {
    handleClose()
  }

  return (
    <div
      ref={overlayRef}
      className="fullscreen-overlay"
      onDoubleClick={handleDoubleClick}
      title="Двойной клик или Esc — выход"
    >
      <video
        ref={videoRef}
        muted={false}
        playsInline
        controls={false}
        className="fullscreen-video"
      />

      {/* ИСПРАВЛЕНО (v42): шапка с анимацией наезда */}
      <div className={`fullscreen-info-overlay ${showInfo ? 'visible' : ''}`}>
        <span className="fullscreen-info-name">{camera.name}</span>
        {camera.location && (
          <span className="fullscreen-info-location">📍 {camera.location}</span>
        )}
        <span className="fullscreen-info-badge">
          MAIN • {camera.audio ? '🔊' : '🔇'}
        </span>
      </div>

      {error && (
        <div className="fullscreen-error">
          {error}
        </div>
      )}
    </div>
  )
}
FULLSCREEN_END
echo "  ✔ frontend/src/components/FullscreenCamera.jsx (анимация наезда)"

# ============================================================
# ЧАСТЬ 3: Обновление MonitorPage.jsx — отступ для шапки
# ============================================================
echo ""
echo "🔧 Обновляю страницу мониторинга..."

# Проверяем наличие файла
if [ ! -f "$PROJECT_DIR/frontend/src/pages/MonitorPage.jsx" ]; then
    echo "⚠️  ВНИМАНИЕ: файл MonitorPage.jsx не найден — пропускаю"
else
    # Добавляем класс для отступа под фиксированную шапку
    # через sed (безопасная замена)
    if grep -q 'monitor-page' "$PROJECT_DIR/frontend/src/pages/MonitorPage.jsx" 2>/dev/null; then
        echo "  ℹ️  Класс monitor-page уже есть — пропускаю"
    else
        # Заменяем <div className="page"> на <div className="page monitor-page">
        sed -i 's|<div className="page"|<div className="page monitor-page"|g' \
            "$PROJECT_DIR/frontend/src/pages/MonitorPage.jsx" 2>/dev/null || true
        echo "  ✔ Добавлен класс monitor-page в MonitorPage.jsx"
    fi
fi

# ============================================================
# ЧАСТЬ 4: Обновление стилей — автоскрываемая шапка
# ============================================================
echo ""
echo "🔧 Обновляю стили..."

STYLES_FILE="$PROJECT_DIR/frontend/src/styles.css"

# Проверяем, не добавлены ли стили уже
if grep -q '.header-hidden' "$STYLES_FILE" 2>/dev/null; then
    echo "  ℹ️  Стили автоскрытия уже есть в styles.css — пропускаю"
else
    cat >> "$STYLES_FILE" << 'STYLES_END'

/* ============================================================
   Автоскрываемая шапка (v42)
   ============================================================ */

/* Шапка приложения: фиксированная, поверх всего */
.header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  background: rgba(11, 13, 16, 0.95);
  backdrop-filter: blur(8px);
  transition: transform 0.3s ease, opacity 0.3s ease;
  transform: translateY(0);
  opacity: 1;
}

/* Скрытое состояние: сдвинута вверх и прозрачна */
.header.header-hidden {
  transform: translateY(-100%);
  opacity: 0;
  pointer-events: none;
}

/* Отступ для контента на странице мониторинга (под фиксированную шапку) */
.monitor-page {
  padding-top: 70px;
}

/* На странице настроек шапка всегда видна — без отступа */
.page:not(.monitor-page) {
  padding-top: 12px;
}

/* Полноэкранный режим: шапка с анимацией наезда */
.fullscreen-info-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 20px;
  background: linear-gradient(
    to bottom,
    rgba(0, 0, 0, 0.8) 0%,
    rgba(0, 0, 0, 0.4) 70%,
    transparent 100%
  );
  pointer-events: none;
  /* ИСПРАВЛЕНО (v42): начальное состояние — скрыта (сдвинута вверх) */
  transform: translateY(-100%);
  opacity: 0;
  transition: transform 0.3s ease, opacity 0.3s ease;
}

/* Видимое состояние: наезжает сверху */
.fullscreen-info-overlay.visible {
  transform: translateY(0);
  opacity: 1;
}

.fullscreen-info-name {
  font-size: 1rem;
  font-weight: 600;
  color: #fff;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.8);
  white-space: nowrap;
}

.fullscreen-info-location {
  font-size: 0.875rem;
  color: #cbd5e1;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.8);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.fullscreen-info-badge {
  font-size: 0.75rem;
  color: #94a3b8;
  background: rgba(255, 255, 255, 0.1);
  padding: 2px 10px;
  border-radius: 4px;
  white-space: nowrap;
}
STYLES_END
    echo "  ✔ Стили автоскрываемой шапки добавлены в styles.css"
fi

# ============================================================
# Финальная проверка
# ============================================================
echo ""
echo "🔍 Финальная проверка..."

for f in frontend/src/components/Header.jsx frontend/src/components/FullscreenCamera.jsx frontend/src/styles.css; do
  if [ ! -s "$PROJECT_DIR/$f" ]; then
    echo "❌ ОШИБКА: файл $f пуст или не создан!" >&2
    exit 1
  fi
  echo "  ✔ $f"
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Автоскрываемая шапка добавлена"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Что изменено:"
echo "  • Шапка приложения фиксированная, поверх контента (z-index: 1000)"
echo "  • Плавно наезжает сверху (transform: translateY)"
echo "  • Исчезает через 3 секунды бездействия мыши"
echo "  • Появляется при движении/клике/касании"
echo "  • В полноэкранном режиме та же логика"
echo "  • На странице настроек шапка всегда видна"
echo ""
echo "🚀 Дальше:"
echo "  1. bash build_frontend.sh"
echo "  2. python main.py"
echo "  3. Откройте: http://localhost:5000 (Ctrl+Shift+R)"