#!/usr/bin/env python3
"""
158. update_scripts/158_fix_add_camera.py
----------------------------------------------------------------------------
Фикс добавления камеры из списка в сетку:
  • добавляет функцию addCameraToSet (POST /api/sets/<id>/cameras)
  • handleDropOnGrid: если камеры нет в наборе → сначала POST, затем order
  • debug-логи [DRAG] для консоли

ЗАПУСК: python update_scripts/158_fix_add_camera.py
"""

import sys
from pathlib import Path


def main():
    project_root = Path.cwd()
    jsx_file = project_root / "frontend" / "src" / "pages" / "SetsPage.jsx"

    print("=" * 76)
    print("158: Фикс добавления камеры из списка в сетку")
    print("=" * 76)
    print()

    backup = jsx_file.with_suffix(".jsx.bak-158")
    backup.write_text(jsx_file.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"  [BAK] {backup.name}")

    content = jsx_file.read_text(encoding="utf-8")

    if "PATCH-158" in content:
        print("  [OK] Уже применён")
        return

    n = 0

    # 1. Заменяем handleDropOnGrid: добавление через POST + логи
    old = """  function handleDropOnGrid(e, idx) {
    e.preventDefault()
    if (!draggedCamera || !activeSet) return
    const ids = [...activeSet.camera_ids]
    const from = ids.indexOf(draggedCamera.id)
    if (from === -1) {
      ids.splice(idx, 0, draggedCamera.id)
    } else {
      ids.splice(from, 1)
      ids.splice(idx > from ? idx - 1 : idx, 0, draggedCamera.id)
    }
    updateCamerasOrder(ids)
    setDraggedCamera(null)
    setDropTarget(null)
  }"""

    new = """  // PATCH-158: добавление камеры в набор (POST), без этого order даёт 400
  async function addCameraToSet(cameraId) {
    if (!activeSet) return
    try {
      const res = await fetch(`/api/sets/${activeSet.set_id}/cameras`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ camera_id: cameraId })
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        console.error('[API] addCameraToSet ошибка:', err)
      } else {
        console.log('[API] камера добавлена в набор:', cameraId)
      }
    } catch (e) {
      console.error('[API] addCameraToSet сеть:', e)
    }
  }

  async function handleDropOnGrid(e, idx) {
    e.preventDefault()
    console.log('[DRAG] drop idx:', idx, 'cam:', draggedCamera && draggedCamera.id)
    if (!draggedCamera || !activeSet) return
    const ids = [...activeSet.camera_ids]
    const from = ids.indexOf(draggedCamera.id)
    if (from === -1) {
      // PATCH-158: камера из списка — сначала POST добавить, затем order
      ids.splice(idx, 0, draggedCamera.id)
      await addCameraToSet(draggedCamera.id)
    } else {
      ids.splice(from, 1)
      ids.splice(idx > from ? idx - 1 : idx, 0, draggedCamera.id)
    }
    await updateCamerasOrder(ids)
    setDraggedCamera(null)
    setDropTarget(null)
  }"""

    if old in content:
        content = content.replace(old, new, 1); n += 1
        print("  [OK] handleDropOnGrid: addCameraToSet + логи")
    else:
        print("  [FAIL] handleDropOnGrid не найден — откат")
        sys.exit(1)

    # 2. Лог в handleDragStart
    old = """  function handleDragStart(e, cam) {
    setDraggedCamera(cam)
    e.dataTransfer.effectAllowed = 'move'
  }"""
    new = """  function handleDragStart(e, cam) {
    console.log('[DRAG] start:', cam.id)  // PATCH-158
    setDraggedCamera(cam)
    e.dataTransfer.effectAllowed = 'move'
  }"""
    if old in content:
        content = content.replace(old, new, 1); n += 1
        print("  [OK] handleDragStart: лог")

    if content.count('{') != content.count('}') or \
       content.count('(') != content.count(')'):
        print("  [FAIL] Скобки — откат")
        jsx_file.write_text(backup.read_text(encoding="utf-8"), encoding="utf-8")
        sys.exit(1)

    jsx_file.write_text(content, encoding="utf-8")
    print("  [OK] Файл сохранён")
    print()

    print("=" * 76)
    print("✅ Готово! Теперь drop из списка работает:")
    print()
    print("  1. POST /api/sets/<id>/cameras      ← добавить камеру")
    print("  2. PUT  /api/sets/<id>/cameras/order ← поставить на позицию")
    print()
    print("Применение:")
    print("  cd frontend && npm run build")
    print("  Ctrl+Shift+R (или инкогнито)")
    print()
    print("Ожидаемые логи в консоли:")
    print("  [DRAG] start: 210-P-GAVw-016")
    print("  [DRAG] drop idx: 4 cam: 210-P-GAVw-016")
    print("  [API] камера добавлена в набор: 210-P-GAVw-016")
    print("=" * 76)


if __name__ == "__main__":
    main()