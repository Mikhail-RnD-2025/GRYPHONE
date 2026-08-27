#!/usr/bin/env bash
# ============================================================
#  GRYPHONE — запускалка всех скриптов
#  ------------------------------------------------------------
#  Запускает все скрипты генерации по порядку, чтобы создать
#  полный проект. Если какой-то скрипт завершается с ошибкой,
#  выполнение останавливается.
#
#  Запуск:   bash 14_run_all.sh
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "🚀 Запуск всех скриптов генерации..."

# Массив скриптов в порядке выполнения.
SCRIPTS=(
  "00_structure.sh"
  "01_meta.sh"
  "02_settings.sh"
  "03_backend_core.sh"
  "04_backend_services.sh"
  "05_stream_manager.sh"
  "06_backend_workers.sh"
  "07_backend_utils.sh"
  "08_backend_routes.sh"
  "09_frontend_base.sh"
  "10_frontend_core.sh"
  "11_frontend_components.sh"
  "12_frontend_pages.sh"
  "13_main.sh"
)

# Запускаем каждый скрипт по порядку.
for script in "${SCRIPTS[@]}"; do
  echo "----------------------------------------"
  echo "📄 Запуск: $script"
  bash "$SCRIPT_DIR/$script"
done

echo "----------------------------------------"
echo "✅ Все скрипты выполнены успешно!"
echo "📁 Проект создан в: $(dirname "$SCRIPT_DIR")"
echo ""
echo "Следующие шаги:"
echo "  1. Установить зависимости бэкенда:  pip install -r requirements.txt"
echo "  2. Установить зависимости фронтенда: cd frontend && npm install"
echo "  3. Запустить бэкенд:                 python main.py"
echo "  4. Запустить фронтенд:               cd frontend && npm run dev"