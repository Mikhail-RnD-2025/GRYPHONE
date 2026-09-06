#!/usr/bin/env python3
"""
144. update_scripts/144_error_handling.py
----------------------------------------------------------------------------
Исправляет замечания аудита:
  FRONTEND (SetsPage.jsx):
    • try/catch во всех fetch-функциях (createSet, deleteSet, updateSet,
      removeCameraFromSet, updateCamerasOrder)
    • безопасный парсинг ошибок: res.json().catch(() => ({}))
    • унификация дефолтов сетки (8x7 вместо 4x6/8x7 рассинхрона)
  BACKEND (api.py):
    • валидация max_rows/max_columns (int + диапазон 1..32)
    • 400 вместо 500 при некорректных данных

ЗАПУСК: python update_scripts/144_error_handling.py
"""

import sys
from pathlib import Path


def main():
    project_root = Path.cwd()
    jsx_file = project_root / "frontend" / "src" / "pages" / "SetsPage.jsx"
    api_file = project_root / "app" / "routes" / "api.py"

    print("=" * 76)
    print("144: Обработка ошибок (frontend) + валидация (backend)")
    print("=" * 76)
    print()

    # ====================================================================
    # FRONTEND
    # ====================================================================
    print("--- SetsPage.jsx: try/catch ---")
    backup_jsx = jsx_file.with_suffix(".jsx.bak-144")
    backup_jsx.write_text(jsx_file.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"  [BAK] {backup_jsx.name}")

    content = jsx_file.read_text(encoding="utf-8")
    if "PATCH-144" in content:
        print("  [OK] Уже применён")
    else:
        n = 0

        # createSet
        old = """  async function createSet() {
    const name = prompt('Имя нового набора:', 'Новый набор')
    if (!name) return
    const res = await fetch('/api/sets', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, max_rows: 4, max_columns: 6 })
    })
    if (res.ok) await loadData()
    else alert('Ошибка: ' + ((await res.json()).error || res.status))
  }"""
        new = """  async function createSet() {
    const name = prompt('Имя нового набора:', 'Новый набор')
    if (!name) return
    try {  // PATCH-144
      const res = await fetch('/api/sets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, max_rows: 4, max_columns: 6 })
      })
      if (res.ok) await loadData()
      else {
        const err = await res.json().catch(() => ({}))
        alert('Ошибка: ' + (err.error || res.status))
      }
    } catch (e) {
      alert('Ошибка сети: ' + e.message)
    }
  }"""
        if old in content:
            content = content.replace(old, new, 1); n += 1
            print("  [OK] createSet: try/catch")

        # deleteSet
        old = """  async function deleteSet() {
    if (!activeSet) return
    if (!confirm(`Удалить набор "${activeSet.name}"?`)) return
    await fetch(`/api/sets/${activeSet.set_id}`, { method: 'DELETE' })
    await loadData()
  }"""
        new = """  async function deleteSet() {
    if (!activeSet) return
    if (!confirm(`Удалить набор "${activeSet.name}"?`)) return
    try {  // PATCH-144
      const res = await fetch(`/api/sets/${activeSet.set_id}`, { method: 'DELETE' })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        alert('Ошибка: ' + (err.error || res.status))
        return
      }
      await loadData()
    } catch (e) {
      alert('Ошибка сети: ' + e.message)
    }
  }"""
        if old in content:
            content = content.replace(old, new, 1); n += 1
            print("  [OK] deleteSet: try/catch")

        # updateSet
        old = """  async function updateSet(patch) {
    if (!activeSet) return
    await fetch(`/api/sets/${activeSet.set_id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(patch)
    })
    await loadData()
  }"""
        new = """  async function updateSet(patch) {
    if (!activeSet) return
    try {  // PATCH-144
      await fetch(`/api/sets/${activeSet.set_id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(patch)
      })
      await loadData()
    } catch (e) {
      console.error('[SetsPage] Ошибка обновления набора:', e)
    }
  }"""
        if old in content:
            content = content.replace(old, new, 1); n += 1
            print("  [OK] updateSet: try/catch")

        # removeCameraFromSet
        old = """  async function removeCameraFromSet(cameraId) {
    if (!activeSet) return
    await fetch(`/api/sets/${activeSet.set_id}/cameras/${cameraId}`, { method: 'DELETE' })
    await loadData()
  }"""
        new = """  async function removeCameraFromSet(cameraId) {
    if (!activeSet) return
    try {  // PATCH-144
      await fetch(`/api/sets/${activeSet.set_id}/cameras/${cameraId}`, { method: 'DELETE' })
      await loadData()
    } catch (e) {
      console.error('[SetsPage] Ошибка удаления камеры:', e)
    }
  }"""
        if old in content:
            content = content.replace(old, new, 1); n += 1
            print("  [OK] removeCameraFromSet: try/catch")

        # updateCamerasOrder
        old = """  async function updateCamerasOrder(newIds) {
    if (!activeSet) return
    await fetch(`/api/sets/${activeSet.set_id}/cameras/order`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ camera_ids: newIds })
    })
    await loadData()
  }"""
        new = """  async function updateCamerasOrder(newIds) {
    if (!activeSet) return
    try {  // PATCH-144
      await fetch(`/api/sets/${activeSet.set_id}/cameras/order`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ camera_ids: newIds })
      })
      await loadData()
    } catch (e) {
      console.error('[SetsPage] Ошибка сохранения порядка:', e)
    }
  }"""
        if old in content:
            content = content.replace(old, new, 1); n += 1
            print("  [OK] updateCamerasOrder: try/catch")

        # унификация дефолтов сетки
        old = """    max_rows: parseInt(raw.max_rows) || 4,
    max_columns: parseInt(raw.max_columns) || 6,"""
        new = """    max_rows: parseInt(raw.max_rows) || 7,    // PATCH-144: единый дефолт
    max_columns: parseInt(raw.max_columns) || 8,"""
        if old in content:
            content = content.replace(old, new, 1); n += 1
            print("  [OK] дефолты сетки унифицированы (8x7)")

        if n == 0:
            print("  [FAIL] Ничего не заменено — откат")
            sys.exit(1)

        if content.count('{') != content.count('}') or \
           content.count('(') != content.count(')'):
            print("  [FAIL] Скобки не сбалансированы — откат")
            jsx_file.write_text(backup_jsx.read_text(encoding="utf-8"), encoding="utf-8")
            sys.exit(1)

        jsx_file.write_text(content, encoding="utf-8")
        print("  [OK] Файл сохранён")

    # ====================================================================
    # BACKEND
    # ====================================================================
    print()
    print("--- api.py: валидация max_rows/max_columns ---")
    backup_api = api_file.with_suffix(".py.bak-144")
    backup_api.write_text(api_file.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"  [BAK] {backup_api.name}")

    acontent = api_file.read_text(encoding="utf-8")
    if "PATCH-144" in acontent:
        print("  [OK] Уже применён")
    else:
        n = 0

        # create_set
        old = """        sets_dict[set_id] = {
            "name": name,
            "max_rows": int(data.get("max_rows", 4)),
            "max_columns": int(data.get("max_columns", 6)),
            "aspect_ratio": data.get("aspect_ratio", "16:9"),
            "camera_ids": [],
        }"""
        new = """        # PATCH-144: валидация числовых полей (400 вместо 500)
        try:
            max_rows = min(max(int(data.get("max_rows", 7)), 1), 32)
            max_columns = min(max(int(data.get("max_columns", 8)), 1), 32)
        except (TypeError, ValueError):
            return jsonify({"error": "max_rows/max_columns must be integers"}), 400
        sets_dict[set_id] = {
            "name": name,
            "max_rows": max_rows,
            "max_columns": max_columns,
            "aspect_ratio": data.get("aspect_ratio", "16:9"),
            "camera_ids": [],
        }"""
        if old in acontent:
            acontent = acontent.replace(old, new, 1); n += 1
            print("  [OK] create_set: валидация")

        # update_set
        old = """        if "max_rows" in data:
            target_set.max_rows = int(data["max_rows"])
        if "max_columns" in data:
            target_set.max_columns = int(data["max_columns"])"""
        new = """        # PATCH-144: валидация числовых полей (400 вместо 500)
        try:
            if "max_rows" in data:
                target_set.max_rows = min(max(int(data["max_rows"]), 1), 32)
            if "max_columns" in data:
                target_set.max_columns = min(max(int(data["max_columns"]), 1), 32)
        except (TypeError, ValueError):
            return jsonify({"error": "max_rows/max_columns must be integers"}), 400"""
        if old in acontent:
            acontent = acontent.replace(old, new, 1); n += 1
            print("  [OK] update_set: валидация")

        if n == 0:
            print("  [FAIL] Ничего не заменено — откат")
            sys.exit(1)

        try:
            compile(acontent, str(api_file), "exec")
        except SyntaxError as e:
            print(f"  [FAIL] Синтаксис: {e} — откат")
            api_file.write_text(backup_api.read_text(encoding="utf-8"), encoding="utf-8")
            sys.exit(1)

        api_file.write_text(acontent, encoding="utf-8")
        print("  [OK] Файл сохранён")

    print()
    print("=" * 76)
    print("✅ Готово!")
    print()
    print("Frontend: все fetch обёрнуты в try/catch, дефолты 8x7")
    print("Backend: 400 вместо 500, диапазон сетки 1..32")
    print()
    print("Применение:")
    print("  cd frontend && npm run build")
    print("  python main.py  (перезапуск)")
    print("=" * 76)


if __name__ == "__main__":
    main()