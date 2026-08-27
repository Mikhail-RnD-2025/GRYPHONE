// ============================================================
//  GRYPHONE — шапка приложения (v45)
//  ------------------------------------------------------------
//  Логика появления/скрытия:
//    1. По умолчанию шапка скрыта (на мониторинге)
//    2. При наведении курсора на верхнюю триггер-зону (20px)
//       шапка плавно появляется
//    3. Пока мышь находится НА ШАПКЕ — она остаётся видимой
//    4. После ухода мыши с шапки запускается таймер 3 сек
//    5. Если за 3 сек мышь не вернулась — шапка скрывается
//
//  На страницах настроек/справки шапка всегда видна.
// ============================================================
import { useState, useEffect, useRef } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { getSets, switchSet } from '../api'

export default function Header() {
  const [sets, setSets] = useState({})
  const [currentSet, setCurrentSet] = useState('')
  const [clock, setClock] = useState('')
  const [visible, setVisible] = useState(false)
  const hideTimerRef = useRef(null)
  const location = useLocation()

  const isMonitorPage = location.pathname === '/'
  const isSettingsPage = location.pathname === '/settings'
  const isHelpPage = location.pathname === '/help'

  useEffect(() => {
    loadSets()
  }, [])

  // Часы
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

  // ИСПРАВЛЕНО (v45): на не-мониторинге шапка всегда видна
  useEffect(() => {
    if (!isMonitorPage) {
      setVisible(true)
    } else {
      // На мониторинге по умолчанию скрыта
      setVisible(false)
    }
  }, [isMonitorPage])

  // ИСПРАВЛЕНО (v45): сброс таймера при входе мыши на зону/шапку
  const cancelHide = () => {
    if (hideTimerRef.current) {
      clearTimeout(hideTimerRef.current)
      hideTimerRef.current = null
    }
  }

  // ИСПРАВЛЕНО (v45): запуск таймера 3 сек при уходе мыши
  const scheduleHide = () => {
    if (!isMonitorPage) return
    cancelHide()
    hideTimerRef.current = setTimeout(() => {
      setVisible(false)
    }, 1000)
  }

  // ИСПРАВЛЕНО (v45): вход мыши в триггер-зону или на шапку
  const handleMouseEnter = () => {
    cancelHide()
    setVisible(true)
  }

  // ИСПРАВЛЕНО (v45): уход мыши с шапки — запускаем таймер
  const handleMouseLeave = () => {
    if (isMonitorPage) {
      scheduleHide()
    }
  }

  // Очистка таймера при размонтировании
  useEffect(() => {
    return () => {
      if (hideTimerRef.current) clearTimeout(hideTimerRef.current)
    }
  }, [])

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
      window.dispatchEvent(new CustomEvent('set-changed', { detail: { setId } }))
    } catch (e) {
      console.error('Ошибка переключения набора:', e)
    }
  }

  return (
    <>
      {/* ИСПРАВЛЕНО (v45): невидимая триггер-зона сверху.
          Только на мониторинге. Высота 20px, при наведении
          мыши показывает шапку. */}
      {isMonitorPage && (
        <div
          className="header-trigger"
          onMouseEnter={handleMouseEnter}
        />
      )}

      {/* Сама шапка */}
      <div
        className={`header ${isMonitorPage && !visible ? 'header-hidden' : ''}`}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
      >
        {/* Логотип слева */}
        <div className="header-left">
          <h1 className="header-title">GRYPHONE</h1>
        </div>

        {/* Время по центру */}
        <div className="header-center">
          <span className="header-clock">{clock}</span>
        </div>

        {/* Справа: наборы → навигация → справка */}
        <div className="header-right">
          {isMonitorPage && Object.keys(sets).length > 0 && (
            <select
              className="set-selector"
              value={currentSet}
              onChange={handleSetChange}
              title="Выбор набора"
            >
              {Object.entries(sets).map(([id, set]) => (
                <option key={id} value={id}>
                  {set.name}
                </option>
              ))}
            </select>
          )}

          {(isSettingsPage || isHelpPage) && (
            <Link to="/" className="header-btn" title="Назад к камерам">
              ← Камеры
            </Link>
          )}

          {(isMonitorPage || isHelpPage) && (
            <Link to="/settings" className="header-btn" title="Настройки">
              ⚙️
            </Link>
          )}

          {!isHelpPage && (
            <Link to="/help" className="header-btn" title="Справка">
              ❓
            </Link>
          )}
        </div>
      </div>
    </>
  )
}
