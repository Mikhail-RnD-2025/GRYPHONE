#!/usr/bin/env python3
"""
176. update_scripts/176_preserve_active_set.py
----------------------------------------------------------------------------
После сохранения активный набор НЕ сбрасывается на дефолтный:
  • loadData(silent=true) — загружает данные, не трогая activeSetId
  • saveChanges: запоминает prevActiveId перед save,
    после loadData(true) восстанавливает его, если набор ещё существует

ЗАПУСК: python update_scripts/176_preserve_active_set.py
"""

import sys
from pathlib import Path


def main():
    project_root = Path.cwd()
    sets_jsx = project_root / "frontend" / "src" / "pages" / "SetsPage.jsx"

    print("=" * 76)
    print("176: Сохранение активного набора после Save")
    print("=" * 76)
    print()

    b = sets_jsx.with_suffix(".jsx.bak-176")
    b.write_text(sets_jsx.read_text(encoding="utf-8"), encoding="utf-8")
    c = sets_jsx.read_text(encoding="utf-8")

    if "PATCH-176" in c:
        print("  [OK] Уже применён")
        return

    n = 0

    # 1. loadData: параметр silent
    old = "  async function loadData() {"
    new = "  async function loadData(silent = false) {  // PATCH-176"
    if old in c:
        c = c.replace(old, new, 1); n += 1
        print("  [OK] loadData(silent=false)")

    # 2. loadData: оборачиваем setActiveSetId в if (!silent) + return setsList
    old = """      setCameras(normalizeCameras(camsData))

      const currentRes = await fetch('/api/sets/current')
      const currentData = await currentRes.json()
      setActiveSetId(currentData.set_id || currentData.id || (setsList[0] && setsList[0].set_id))
    } catch (e) {
      console.error('[SetsPage] Ошибка загрузки:', e)
    } finally {"""
    new = """      setCameras(normalizeCameras(camsData))

      if (!silent) {  // PATCH-176: не трогаем activeSetId при тихой загрузке
        const currentRes = await fetch('/api/sets/current')
        const currentData = await currentRes.json()
        setActiveSetId(currentData.set_id || currentData.id || (setsList[0] && setsList[0].set_id))
      }
      return setsList
    } catch (e) {
      console.error('[SetsPage] Ошибка загрузки:', e)
      return []
    } finally {"""
    if old in c:
        c = c.replace(old, new, 1); n += 1
        print("  [OK] silent-блок + return setsList")

    # 3. saveChanges: запоминаем prevActiveId
    old = """  async function saveChanges() {
    setSaving(true)
    try {"""
    new = """  async function saveChanges() {
    setSaving(true)
    const prevActiveId = activeSetId  // PATCH-176: помним выбор пользователя
    try {"""
    if old in c:
        c = c.replace(old, new, 1); n += 1
        print("  [OK] prevActiveId запомнен")

    # 4. saveChanges: тихая загрузка + восстановление
    old = """      await loadData()
    } catch (e) {
      console.error('[SetsPage] Ошибка сохранения:', e)"""
    new = """      const freshSets = await loadData(true)  // PATCH-176: тихая загрузка
      if (prevActiveId && freshSets.some(s => s.set_id === prevActiveId)) {
        setActiveSetId(prevActiveId)  // возвращаем выбор пользователя
      }
    } catch (e) {
      console.error('[SetsPage] Ошибка сохранения:', e)"""
    if old in c:
        c = c.replace(old, new, 1); n += 1
        print("  [OK] тихая загрузка + восстановление activeSetId")

    if n == 4 and c.count('{') == c.count('}'):
        sets_jsx.write_text(c, encoding="utf-8")
        print("  [OK] Сохранено")
    else:
        print(f"  [FAIL] {n}/4 — откат")
        sets_jsx.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
        sys.exit(1)

    print()
    print("=" * 76)
    print("✅ Готово!")
    print()
    print("Поведение теперь:")
    print("  • Первая загрузка /sets → activeSetId = current (как раньше)")
    print("  • Редактирую набор 'Тест' → 💾 Сохранить → остаюсь на 'Тест'")
    print("  • Если набор удалили → переключение на первый оставшийся")
    print()
    print("  cd frontend && npm run build && Ctrl+Shift+R")
    print("=" * 76)
    print()
    print("📦 ПОСЛЕ ПРОВЕРКИ — коммит:")
    print()
    print("cd /c/GRYPHONE_PROJ/v26")
    print("git add -A")
    print('git commit -m "fix: preserve active set after save (PATCH-176)" \\')
    print('  -m "loadData(silent) does not touch activeSetId" \\')
    print('  -m "saveChanges remembers prevActiveId and restores it after reload"')
    print("git push")
    print("=" * 76)


if __name__ == "__main__":
    main()