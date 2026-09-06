#!/usr/bin/env python3
"""
155. update_scripts/155_form_field_ids.py
----------------------------------------------------------------------------
Добавляет id/name атрибуты к полям формы в SetsPage (рекомендация Lighthouse).

ЗАПУСК: python update_scripts/155_form_field_ids.py
"""

import sys
from pathlib import Path


def main():
    project_root = Path.cwd()
    jsx_file = project_root / "frontend" / "src" / "pages" / "SetsPage.jsx"

    print("=" * 76)
    print("155: Добавление id/name к полям формы")
    print("=" * 76)
    print()

    backup = jsx_file.with_suffix(".jsx.bak-155")
    backup.write_text(jsx_file.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"  [BAK] {backup.name}")

    content = jsx_file.read_text(encoding="utf-8")

    if "PATCH-155" in content:
        print("  [OK] Уже применён")
        return

    n = 0

    # 1. Поиск камер
    old = '''          <input
            className="sets-input sets-search"
            type="text"
            placeholder="🔍 Поиск камер..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          />'''
    new = '''          <input
            id="sets-search"
            name="search"
            className="sets-input sets-search"
            type="text"
            placeholder="🔍 Поиск камер..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          />'''
    if old in content:
        content = content.replace(old, new, 1); n += 1
        print("  [OK] поиск камер: id/name добавлены")

    # 2. Имя набора
    old = '''        <input
          className="sets-input sets-input-name"
          type="text"
          value={activeSet ? activeSet.name : ''}
          onChange={(e) => updateSet({ name: e.target.value })}
        />'''
    new = '''        <input
          id="set-name"
          name="set-name"
          className="sets-input sets-input-name"
          type="text"
          value={activeSet ? activeSet.name : ''}
          onChange={(e) => updateSet({ name: e.target.value })}
        />'''
    if old in content:
        content = content.replace(old, new, 1); n += 1
        print("  [OK] имя набора: id/name добавлены")

    # 3. max_columns
    old = '''        <input
          className="sets-input sets-input-num" type="number" min="1" max="20"
          value={maxCols}
          onChange={(e) => updateSet({ max_columns: parseInt(e.target.value) || 1 })}
        />'''
    new = '''        <input
          id="set-max-columns"
          name="max-columns"
          className="sets-input sets-input-num" type="number" min="1" max="20"
          value={maxCols}
          onChange={(e) => updateSet({ max_columns: parseInt(e.target.value) || 1 })}
        />'''
    if old in content:
        content = content.replace(old, new, 1); n += 1
        print("  [OK] max_columns: id/name добавлены")

    # 4. max_rows
    old = '''        <input
          className="sets-input sets-input-num" type="number" min="1" max="20"
          value={maxRows}
          onChange={(e) => updateSet({ max_rows: parseInt(e.target.value) || 1 })}
        />'''
    new = '''        <input
          id="set-max-rows"
          name="max-rows"
          className="sets-input sets-input-num" type="number" min="1" max="20"
          value={maxRows}
          onChange={(e) => updateSet({ max_rows: parseInt(e.target.value) || 1 })}
        />'''
    if old in content:
        content = content.replace(old, new, 1); n += 1
        print("  [OK] max_rows: id/name добавлены")

    # 5. select наборов
    old = '''        <select
          className="sets-select"
          value={activeSet ? activeSet.set_id : ''}
          onChange={(e) => setActiveSetId(e.target.value)}
        >'''
    new = '''        <select
          id="set-selector"
          name="set-selector"
          className="sets-select"
          value={activeSet ? activeSet.set_id : ''}
          onChange={(e) => setActiveSetId(e.target.value)}
        >'''
    if old in content:
        content = content.replace(old, new, 1); n += 1
        print("  [OK] select наборов: id/name добавлены")

    # 6. select формата
    old = '''        <select
          className="sets-select sets-select-sm"
          value={activeSet ? activeSet.aspect_ratio : '16:9'}
          onChange={(e) => updateSet({ aspect_ratio: e.target.value })}
        >'''
    new = '''        <select
          id="set-aspect-ratio"
          name="aspect-ratio"
          className="sets-select sets-select-sm"
          value={activeSet ? activeSet.aspect_ratio : '16:9'}
          onChange={(e) => updateSet({ aspect_ratio: e.target.value })}
        >'''
    if old in content:
        content = content.replace(old, new, 1); n += 1
        print("  [OK] select формата: id/name добавлены")

    if n < 6:
        print(f"  [WARN] Заменено {n}/6 — некоторые поля могли отсутствовать")

    if content.count('{') != content.count('}') or \
       content.count('(') != content.count(')'):
        print("  [FAIL] Скобки — откат")
        jsx_file.write_text(backup.read_text(encoding="utf-8"), encoding="utf-8")
        sys.exit(1)

    jsx_file.write_text(content, encoding="utf-8")
    print("  [OK] Сохранено")
    print()

    print("=" * 76)
    print("✅ Готово! Предупреждения Lighthouse исчезнут.")
    print()
    print("Но это НЕ решит проблему с drag & drop.")
    print("Для диагностики drag & drop откройте DevTools (F12) → Console")
    print("и попробуйте перетащить камеру. Пришлите скриншот ошибок.")
    print()
    print("  cd frontend && npm run build && Ctrl+Shift+R")
    print("=" * 76)


if __name__ == "__main__":
    main()