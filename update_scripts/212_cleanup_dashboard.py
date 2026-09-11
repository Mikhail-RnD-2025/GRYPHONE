#!/usr/bin/env python3
"""
212. update_scripts/212_cleanup_dashboard.py
----------------------------------------------------------------------------
  • Dashboard.jsx: удаляет секции «📹 Камеры» и «⚠️ Проблемные камеры»
    (остаются только «💻 Система» и «📦 Наборы»)
  • CameraHealth.jsx: переименование «🏥 Здоровье камер» → «📊 Состояние камер»

ЗАПУСК: python update_scripts/212_cleanup_dashboard.py
"""

import sys
import subprocess
from pathlib import Path


def find_project_root():
    p = Path.cwd()
    while True:
        if (p / "frontend").is_dir() and (p / "update_scripts").is_dir():
            return p
        parent = p.parent
        if parent == p:
            print("[FAIL] Не найден корень проекта")
            sys.exit(1)
        p = parent


def patch_dashboard(root):
    print("--- Dashboard.jsx: удаление секций «Камеры» и «Проблемные камеры» ---")
    f = root / "frontend" / "src" / "components" / "Dashboard.jsx"
    b = f.with_suffix(".jsx.bak-212")
    b.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    c = f.read_text(encoding="utf-8")
    n = 0

    # 1. Удаляем секцию «📹 Камеры» (от <h3>📹 Камеры</h3> до <h3>💻 Система</h3>)
    cam_start = '      {/* Общая статистика камер */}\n      <h3 style={{ marginBottom: \'12px\' }}>📹 Камеры</h3>'
    sys_start = '      {/* Нагрузка системы */}\n      <h3 style={{ marginBottom: \'12px\' }}>💻 Система</h3>'

    i_start = c.find(cam_start)
    i_end = c.find(sys_start)
    if i_start != -1 and i_end != -1 and i_start < i_end:
        c = c[:i_start] + c[i_end:]
        n += 1
        print("  [OK] секция «📹 Камеры» удалена")
    else:
        print("  [WARN] секция «📹 Камеры» не найдена или уже удалена")

    # 2. Удаляем секцию «⚠️ Проблемные камеры» (от <h3> до конца компонента)
    prob_start = '      {/* Проблемные камеры */}\n      <h3 style={{ marginBottom: \'12px\' }}>⚠️ Проблемные камеры</h3>'
    i_prob = c.find(prob_start)
    if i_prob != -1:
        # Находим последнее закрытие </div> перед концом компонента
        # Структура: return (<div>...</div>)
        # Ищем последнее </div> перед закрывающей скобкой }
        c = c[:i_prob].rstrip() + '\n    </div>\n  )\n}\n'
        n += 1
        print("  [OK] секция «⚠️ Проблемные камеры» удалена")
    else:
        print("  [WARN] секция «⚠️ Проблемные камеры» не найдена или уже удалена")

    if n == 0:
        print("  [FAIL] ни одна секция не найдена — откат")
        f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
        return False

    f.write_text(c, encoding="utf-8")
    return True


def patch_camera_health(root):
    print("--- CameraHealth.jsx: переименование «Здоровье камер» → «Состояние камер» ---")
    f = root / "frontend" / "src" / "components" / "CameraHealth.jsx"
    b = f.with_suffix(".jsx.bak-212")
    b.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    c = f.read_text(encoding="utf-8")
    n = 0

    # Заголовок
    if "🏥 Здоровье камер" in c:
        c = c.replace("🏥 Здоровье камер", "📊 Состояние камер")
        n += 1
        print("  [OK] заголовок: 🏥 Здоровье камер → 📊 Состояние камер")

    # Loading текст
    if "Загрузка здоровья камер..." in c:
        c = c.replace("Загрузка здоровья камер...", "Загрузка состояния камер...")
        n += 1
        print("  [OK] loading: здоровье → состояние")

    if n == 0:
        print("  [WARN] текст уже изменён или не найден")
        return True

    f.write_text(c, encoding="utf-8")
    return True


def build_check(root):
    print("--- npm run build ---")
    res = subprocess.run(
        ["npm", "run", "build"],
        cwd=str(root / "frontend"),
        capture_output=True,
        text=True
    )
    if res.returncode != 0:
        print("  [FAIL] сборка упала:")
        print(res.stderr)
        return False
    print("  [OK] сборка успешна")
    return True


def main():
    root = find_project_root()
    print("=" * 76)
    print("212: чистка Dashboard + переименование")
    print("=" * 76)
    print()

    ok = True
    ok &= patch_dashboard(root)
    ok &= patch_camera_health(root)

    if not ok:
        sys.exit(1)

    ok &= build_check(root)
    if not ok:
        print()
        print("[FAIL] сборка упала — откат изменений")
        # Откат Dashboard
        d = root / "frontend" / "src" / "components" / "Dashboard.jsx"
        b = d.with_suffix(".jsx.bak-212")
        if b.exists():
            d.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
        # Откат CameraHealth
        h = root / "frontend" / "src" / "components" / "CameraHealth.jsx"
        b = h.with_suffix(".jsx.bak-212")
        if b.exists():
            h.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
        sys.exit(1)

    print()
    print("=" * 76)
    print("✅ PATCH-212 готов!")
    print()
    print("Откройте http://127.0.0.1:5000/status (Ctrl+F5)")
    print()
    print("Ожидаемо:")
    print("  • Секция «💻 Система» (CPU/RAM/Диск)")
    print("  • Секция «📦 Наборы» (4 карточки)")
    print("  • Секция «📊 Состояние камер» (бывш. «Здоровье камер»)")
    print("     - 6 summary-плашек + фильтры + таблица 24 строки")
    print("=" * 76)
    print()
    print("📦 Коммит:")
    print(f"cd {root}")
    print("git add -A")
    print('git commit -m "refactor(dashboard): remove stale sections, rename health (PATCH-212)" \\')
    print('  -m "Dashboard.jsx: removed «Камеры» and «Проблемные камеры» sections" \\')
    print('  -m "kept: «Система» (CPU/RAM/Disk) + «Наборы»" \\')
    print('  -m "CameraHealth.jsx: renamed «Здоровье камер» → «Состояние камер»"')
    print("git push")
    print("=" * 76)


if __name__ == "__main__":
    main()