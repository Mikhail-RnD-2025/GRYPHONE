#!/usr/bin/env python3
"""
181. update_scripts/181_localstorage_current_set.py
----------------------------------------------------------------------------
  • Сервер НЕ хранит выбор: _current_set = '' при старте
  • Браузер хранит последний набор в localStorage['gryphone_current_set']
  • Header при загрузке: читает localStorage → показывает имя →
    синхронизирует сервер switchSet()
  • Убирает server-side persist из PATCH-180 (если применён)

ЗАПУСК: python update_scripts/181_localstorage_current_set.py
"""

import sys
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


def try_replace(content, candidates, label):
    """Пробует список вариантов (old, new), возвращает (content, ok)"""
    for old, new in candidates:
        if old in content:
            return content.replace(old, new, 1), True
    print(f"  [WARN] {label}: якорь не найден")
    return content, False


def main():
    root = find_project_root()
    print(f"  [OK] Корень проекта: {root}")
    print()
    print("=" * 76)
    print("181: последний набор хранится в localStorage браузера")
    print("=" * 76)
    print()

    svc_py = root / "app" / "services" / "camera_service.py"
    header = root / "frontend" / "src" / "components" / "Header.jsx"

    # ====================================================================
    # camera_service.py: сервер не помнит
    # ====================================================================
    print("--- camera_service.py ---")
    b = svc_py.with_suffix(".py.bak-181")
    b.write_text(svc_py.read_text(encoding="utf-8"), encoding="utf-8")
    c = svc_py.read_text(encoding="utf-8")
    n = 0

    # _load: current = '' (варианты: после 180 или после 177)
    c, ok = try_replace(c, [
        ("""        # PATCH-180: восстанавливаем последний выбранный набор из settings
        stored = db.get_setting("current_set", "")
        self._current_set = stored if stored in self._sets else """"",
         """        # PATCH-181: сервер НЕ хранит выбор — клиент синхронизирует сам
        self._current_set = """""),
        ("""        # PATCH-177: понятия "набор по умолчанию" больше нет — текущий = первый
        self._current_set = next(iter(self._sets), "")""",
         """        # PATCH-181: сервер НЕ хранит выбор — клиент синхронизирует сам
        self._current_set = """""),
    ], "_load")
    if ok: n += 1; print("  [OK] _load: current = ''")

    # switch_set: убрать persist (если был)
    old = """        self._current_set = set_id
        db.set_setting("current_set", set_id)  # PATCH-180: запоминаем выбор
"""
    new = """        self._current_set = set_id
"""
    if old in c:
        c = c.replace(old, new, 1); n += 1
        print("  [OK] switch_set: persist убран")
    else:
        print("  [OK] switch_set: persist не было")

    # save_sets: убрать persist (если был)
    c, ok = try_replace(c, [
        ("""        if self._current_set not in self._sets:
            self._current_set = ""
            db.set_setting("current_set", "")  # PATCH-180: набор удалён""",
         """        if self._current_set not in self._sets:
            self._current_set = """""),
    ], "save_sets")
    if ok: n += 1; print("  [OK] save_sets: persist убран")

    if n >= 1:
        try:
            compile(c, str(svc_py), "exec")
            svc_py.write_text(c, encoding="utf-8")
            print("  [OK] Сохранено")
        except SyntaxError as e:
            print(f"  [FAIL] синтаксис: {e} — откат")
            svc_py.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
            sys.exit(1)
    else:
        print("  [FAIL] ничего не заменено — откат")
        svc_py.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
        sys.exit(1)

    # ====================================================================
    # Header.jsx: localStorage
    # ====================================================================
    print()
    print("--- Header.jsx ---")
    b = header.with_suffix(".jsx.bak-181")
    b.write_text(header.read_text(encoding="utf-8"), encoding="utf-8")
    c = header.read_text(encoding="utf-8")
    m = 0

    # loadSets: чтение localStorage (варианты: после 180 или после 178/179)
    c, ok = try_replace(c, [
        ("""      setCurrentSet(data.current_set || '')  // PATCH-180: последний выбранный""",
         """      // PATCH-181: последний выбор хранится ЛОКАЛЬНО в браузере
      const stored = localStorage.getItem('gryphone_current_set') || ''
      if (stored && data.sets && data.sets[stored]) {
        setCurrentSet(stored)
        switchSet(stored).catch(() => {})  // синхронизируем сервер
      } else {
        setCurrentSet('')
      }"""),
        ("""      setCurrentSet('')  // PATCH-178""",
         """      // PATCH-181: последний выбор хранится ЛОКАЛЬНО в браузере
      const stored = localStorage.getItem('gryphone_current_set') || ''
      if (stored && data.sets && data.sets[stored]) {
        setCurrentSet(stored)
        switchSet(stored).catch(() => {})  // синхронизируем сервер
      } else {
        setCurrentSet('')
      }"""),
    ], "loadSets")
    if ok: m += 1; print("  [OK] loadSets: чтение localStorage")

    # handleSetChange: запись в localStorage
    old = """  const handleSetChange = async (setId) => {
    setCurrentSet(setId)
"""
    new = """  const handleSetChange = async (setId) => {
    setCurrentSet(setId)
    localStorage.setItem('gryphone_current_set', setId)  // PATCH-181
"""
    if old in c:
        c = c.replace(old, new, 1); m += 1
        print("  [OK] handleSetChange: запись в localStorage")

    if m == 2 and c.count('{') == c.count('}'):
        header.write_text(c, encoding="utf-8")
        print("  [OK] Сохранено")
    else:
        print(f"  [FAIL] {m}/2 — откат")
        header.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
        sys.exit(1)

    print()
    print("=" * 76)
    print("✅ Готово! Хранение теперь локальное:")
    print()
    print("  • localStorage['gryphone_current_set'] — последний выбор")
    print("  • Сервер при старте: current = '' (ничего не помнит)")
    print("  • Загрузка страницы: браузер показывает имя + sync сервера")
    print("  • Другой браузер / инкогнито → «— выберите набор —»")
    print()
    print("  ВАЖНО: перезапустить сервер (python main.py)")
    print(f"  cd {root}/frontend && npm run build && Ctrl+Shift+R")
    print("=" * 76)
    print()
    print("📦 ПОСЛЕ ПРОВЕРКИ — коммит:")
    print()
    print(f"cd {root}")
    print("git add -A")
    print('git commit -m "feat: store last selected set in browser localStorage (PATCH-181)" \\')
    print('  -m "server no longer persists current_set; client syncs via switchSet" \\')
    print('  -m "Header reads localStorage on load, shows name or placeholder"')
    print("git push")
    print("=" * 76)


if __name__ == "__main__":
    main()