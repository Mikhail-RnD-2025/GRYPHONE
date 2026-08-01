#!/usr/bin/env bash
# =============================================================================
# scaffold.sh — создание ВСЕЙ структуры каталогов и ВСЕХ файлов-заглушек проекта
# GRYPHON v26.2 по явному манифесту путей.
#
# Что делает:
#   * mkdir -p для каждого каталога из DIRS;
#   * для каждого файла из FILES создаёт родительский каталог и сам файл-заглушку
#     (одна строка-маркер, зависящая от расширения);
#   * НЕ затирает уже существующие файлы (идемпотентность — можно гонять поверх
#     наполненного проекта: наполненные файлы будут пропущены, посчитаны в skipped);
#   * печатает отчёт: сколько каталогов/файлов создано и пропущено.
#
# Что НЕ делает:
#   * не пишет рабочий код внутрь файлов — только маркеры-заглушки. Рабочий код
#     каждого файла генерируют слои сборки (10/20/30/40-build-*.sh) через cat >;
#     нормальный порядок: scaffold.sh (каркас) -> слои (наполнение кодом).
#
# Использование:
#   chmod +x scaffold.sh && ./scaffold.sh            # в текущей папке создаст gryphon/
#   ROOT=/path/to/repo ./scaffold.sh                 # создать в заданном корне
# =============================================================================
set -euo pipefail

# --- Корень проекта: из переменной ROOT, иначе ./gryphon рядом со скриптом. ----
ROOT="${ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/gryphon}"
echo ">> scaffold: корень = ${ROOT}"

# =============================================================================
# МАНИФЕСТ КАТАЛОГОВ (DIRS). Включает и пустые папки, которые не покрыты файлами
# (tests/unit..load, features-заглушки фронта, [locale], ml, external и т.п.).
# Пути с [ ] (например app/[locale]) безопасны, потому что ниже всегда в кавычках.
# =============================================================================
DIRS=(
  # --- корень / инфра ---
  scripts
  deploy
  deploy/pg

  # --- backend: application layer ---
  backend/app
  backend/app/middleware

  # --- backend: vertical slices (features) ---
  backend/features/auth
  backend/features/devices
  backend/features/rbac
  backend/features/locations
  backend/features/tagbus
  backend/features/maps
  backend/features/schematics
  backend/features/analytics
  backend/features/audit
  backend/features/cognitive
  backend/features/settings

  # --- backend: shared infrastructure ---
  backend/infrastructure/database
  backend/infrastructure/database/models
  backend/infrastructure/database/repositories
  backend/infrastructure/tagbus
  backend/infrastructure/redis
  backend/infrastructure/rbac
  backend/infrastructure/audit
  backend/infrastructure/devices
  backend/infrastructure/ml
  backend/infrastructure/external

  # --- backend: shared kernel + tests ---
  backend/shared
  backend/tests/unit
  backend/tests/integration
  backend/tests/e2e
  backend/tests/load
  backend/tests/property

  # --- frontend: app router + widgets ---
  frontend/src/app
  "frontend/src/app/[locale]"
  frontend/src/widgets

  # --- frontend: feature slices ---
  frontend/src/features/locations/components
  frontend/src/features/locations/hooks
  frontend/src/features/dashboard/components
  frontend/src/features/dashboard/hooks
  frontend/src/features/cameras/components
  frontend/src/features/devices
  frontend/src/features/rbac
  frontend/src/features/analytics
  frontend/src/features/audit
  frontend/src/features/auth/hooks

  # --- frontend: shared design / ui / hooks / utils ---
  frontend/src/shared/design
  frontend/src/shared/design/themes
  frontend/src/shared/ui
  frontend/src/shared/hooks
  frontend/src/shared/shortcuts
  frontend/src/shared/utils
  frontend/src/shared/lib
  frontend/src/shared/types

  # --- frontend: i18n ---
  frontend/src/locales
)

# =============================================================================
# МАНИФЕСТ ФАЙЛОВ (FILES). Каждый путь получит заглушку по расширению.