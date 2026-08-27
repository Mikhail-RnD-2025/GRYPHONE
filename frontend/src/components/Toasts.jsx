// ============================================================
//  GRYPHONE — компонент «Уведомления»
//  ------------------------------------------------------------
//  ИСПРАВЛЕНО: уникальные id через счётчик (ранее использовался
//  Date.now(), что могло дать коллизию при быстром создании).
// ============================================================
import { useState, useEffect, useRef } from 'react'

export default function Toasts() {
  // Список активных уведомлений.
  const [toasts, setToasts] = useState([])
  // ИСПРАВЛЕНО: счётчик для уникальных id.
  const counterRef = useRef(0)

  // Функция для добавления уведомления.
  const addToast = (message, type = 'info') => {
    counterRef.current += 1
    const id = counterRef.current
    setToasts((prev) => [...prev, { id, message, type }])
    // Автоматически удаляем уведомление через 4 секунды.
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id))
    }, 4000)
  }

  // Экспортируем функцию добавления уведомлений через глобальную переменную.
  // При размонтировании компонента очищаем её.
  useEffect(() => {
    window.addToast = addToast
    return () => {
      delete window.addToast
    }
  }, [])

  return (
    <div className="toast-container">
      {toasts.map((toast) => (
        <div key={toast.id} className={`toast toast-${toast.type}`}>
          {toast.message}
        </div>
      ))}
    </div>
  )
}
