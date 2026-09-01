#!/usr/bin/env bash
# ============================================================
#  GRYPHONE — скрипт 45: ШАПКА ПО ФОКУСУ (триггер-зона)
#  ------------------------------------------------------------
#  Что меняет:
#    • Шапка больше не появляется при любом движении мыши
#    • Появляется ТОЛЬКО когда курсор попадает в верхнюю зону
#      (невидимая полоса 20px от верха экрана)
#    • Пока мышь на шапке — она не исчезает
#    • После ухода мыши — таймер 3 сек → плавное скрытие
#
#  ЗАПУСК:  bash update_scripts/45_header_focus.sh
#  ПОСЛЕ:   bash build_frontend.sh && python main.py
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
# Header.jsx — шапка с триггер-зоной
# ============================================================
echo ""
echo "🔧 Обновляю Header.jsx (фокус на триггер-зону)..."

mkdir -p "$PROJECT_DIR/frontend/src/components"

cat > "$PROJECT_DIR/frontend/src/components/Header.jsx" << 'HEADER_END'
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
    }, 3000)
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
HEADER_END
echo "  ✔ frontend/src/components/Header.jsx (фокус на триггер-зону)"

# ============================================================
# Стили триггер-зоны и шапки
# ============================================================
echo ""
echo "🔧 Добавляю стили триггер-зоны..."

STYLES_FILE="$PROJECT_DIR/frontend/src/styles.css"

cd "$PROJECT_DIR"

# Удаляем старые стили .header (глобальный mousemove больше не нужен)
python << 'PYEOF_CLEANUP'
from pathlib import Path
import re

file = Path("frontend/src/styles.css")
content = file.read_text(encoding="utf-8")

# Удаляем старые блоки, связанные с глобальным mousemove
# (они могут конфликтовать с новой логикой)
patterns_to_remove = [
    r'/\*\s*Шапка-оверлей \(v44\)[^*]*\*/',
    r'/\*\s*Автоскрываемая шапка \(v42\)[^*]*\*/',
]

# Удаляем только блоки-комментарии (стили оставляем, они совместимы)
for pat in patterns_to_remove:
    content = re.sub(pat, '', content, flags=re.DOTALL)

file.write_text(content, encoding="utf-8")
print("OK: styles.css очищен от устаревших комментариев")
PYEOF_CLEANUP

# Добавляем стили триггер-зоны и обновлённой шапки (если ещё нет)
if grep -q '.header-trigger' "$STYLES_FILE" 2>/dev/null; then
    echo "  ℹ️  Стили .header-trigger уже есть — пропускаю"
else
    cat >> "$STYLES_FILE" << 'STYLES_END'

/* ============================================================
   Триггер-зона и шапка по фокусу (v45)
   ------------------------------------------------------------
   • .header-trigger — невидимая полоса 20px сверху экрана
   • При наведении на неё — шапка появляется
   • Пока мышь на шапке — она видна
   • После ухода мыши — 3 сек и скрывается
   ============================================================ */

/* Невидимая зона сверху — реагирует на наведение мыши */
.header-trigger {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 20px;
  z-index: 999;
  /* полностью прозрачная, но ловит события мыши */
  background: transparent;
  pointer-events: auto;
}

/* Плавная анимация появления/скрытия шапки */
.header {
  transition: transform 0.3s ease, opacity 0.3s ease;
  transform: translateY(0);
  opacity: 1;
}

/* Скрытое состояние: шапка ушла вверх и прозрачна */
.header.header-hidden {
  transform: translateY(-100%);
  opacity: 0;
  pointer-events: none;
}

/* На мониторинге: шапка — оверлей (не занимает место в сетке) */
.page.monitor-page .header,
.monitor-page .header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  background: linear-gradient(
    to bottom,
    rgba(11, 13, 16, 0.95) 0%,
    rgba(11, 13, 16, 0.85) 70%,
    rgba(11, 13, 16, 0.4) 100%
  );
  backdrop-filter: blur(8px);
}

/* На не-мониторинге: шапка статичная (занимает место) */
.page:not(.monitor-page) .header {
  position: relative;
  background: rgba(11, 13, 16, 0.98);
  backdrop-filter: blur(8px);
}
STYLES_END
    echo "  ✔ Стили триггер-зоны добавлены в styles.css"
fi

# ============================================================
# Финальная проверка
# ============================================================
echo ""
echo "🔍 Финальная проверка..."

for f in frontend/src/components/Header.jsx frontend/src/styles.css; do
  if [ ! -s "$PROJECT_DIR/$f" ]; then
    echo "❌ ОШИБКА: файл $f пуст или не создан!" >&2
    exit 1
  fi
  echo "  ✔ $f"
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Шапка реагирует только на фокус"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Новая логика:"
echo "  • По умолчанию шапка СКРЫТА (на мониторинге)"
echo "  • Появляется ТОЛЬКО при наведении на верхнюю зону (20px)"
echo "  • Пока мышь на шапке — она не исчезает"
echo "  • После ухода мыши — таймер 3 сек → плавное скрытие"
echo "  • На страницах настроек/справки шапка всегда видна"
echo ""
echo "🎯 Визуальный эффект:"
echo "  • Наведите мышь к самому верху экрана → шапка наезжает"
echo "  • Уведите мышь вниз → через 3 сек шапка плавно уходит"
echo "  • Держите мышь на шапке → она остаётся видимой"
echo ""
echo "🚀 Дальше:"
echo "  1. bash build_frontend.sh"
echo "  2. python main.py"
echo "  3. Откройте: http://localhost:5000 (Ctrl+Shift+R)"