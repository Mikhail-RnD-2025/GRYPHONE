// ============================================================
//  GRYPHONE — хук подписки на события в реальном времени
//  ------------------------------------------------------------
//  ИСПРАВЛЕНО (v33):
//  • Слияние статусов вместо полной замены — статусы не
//    теряются при пересинхронизации воркеров
//  • Устранено мигание статуса «подключение»
// ============================================================
import { useState, useEffect, useRef } from 'react'

export default function useStreamStatus() {
  const [stats, setStats] = useState({})
  // ИСПРАВЛЕНО (v33): хранилище последних известных статусов.
  // При получении новых данных сливаем с существующими, чтобы
  // не терять статусы при временном отсутствии в ответе.
  const lastStatsRef = useRef({})

  useEffect(() => {
    const source = new EventSource('/api/stream_status')

    source.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        // ИСПРАВЛЕНО (v33): слияние с последним известным статусом.
        // Если маршрут отсутствует в новых данных, сохраняем
        // последний известный статус, чтобы не мигало «подключение».
        const merged = { ...lastStatsRef.current, ...data }
        lastStatsRef.current = merged
        setStats(merged)
      } catch (e) {
        console.error('Ошибка разбора данных:', e)
      }
    }

    source.onerror = () => {
      console.warn('Ошибка подписки на события')
    }

    return () => {
      source.close()
    }
  }, [])

  return stats
}
