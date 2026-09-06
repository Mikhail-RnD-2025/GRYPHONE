#!/usr/bin/env python3
"""
146. update_scripts/146_aspect_ratio_field.py
----------------------------------------------------------------------------
Добавляет поле aspect_ratio в UI управления наборами:
  • селект 16:9 / 4:3 в верхней панели (рядом с размерностью)
  • дефолт при создании = 16:9 (уже на бэкенде)
  • валидация на бэкенде: только '16:9' или '4:3', иначе 400

ЗАПУСК: python update_scripts/146_aspect_ratio_field.py
"""

import sys
from pathlib import Path


def main():
    project_root = Path.cwd()
    jsx_file = project_root / "frontend" / "src" / "pages" / "SetsPage.jsx"
    css_file = project_root / "frontend" / "src" / "styles" / "sets.css"
    api_file = project_root / "app" / "routes" / "api.py"

    print("=" * 76)
    print("146: Поле aspect_ratio (16:9 / 4:3)")
    print("=" * 76)
    print()

    # ====================================================================
    # FRONTEND: селект в topbar
    # ====================================================================
    print("--- SetsPage.jsx ---")
    backup_jsx = jsx_file.with_suffix(".jsx.bak-146")
    backup_jsx.write_text(jsx_file.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"  [BAK] {backup_jsx.name}")

    content = jsx_file.read_text(encoding="utf-8")

    if "PATCH-146" in content:
        print("  [OK] Уже применён")
    else:
        old = """        <input
          className="sets-input sets-input-num" type="number" min="1" max="20"
          value={maxRows}
          onChange={(e) => updateSet({ max_rows: parseInt(e.target.value) || 1 })}
        />
        <span className="sets-counter">"""
        new = """        <input
          className="sets-input sets-input-num" type="number" min="1" max="20"
          value={maxRows}
          onChange={(e) => updateSet({ max_rows: parseInt(e.target.value) || 1 })}
        />
        <span className="sets-label">Формат:</span>
        <select
          className="sets-select sets-select-sm"
          value={activeSet ? activeSet.aspect_ratio : '16:9'}
          onChange={(e) => updateSet({ aspect_ratio: e.target.value })}
        >
          <option value="16:9">16:9</option>
          <option value="4:3">4:3</option>
        </select>
        <span className="sets-counter">"""

        if old in content:
            content = content.replace(old, new, 1)  # PATCH-146
            print("  [OK] селект 16:9 / 4:3 добавлен")
        else:
            print("  [FAIL] Точка вставки не найдена — откат")
            sys.exit(1)

        if content.count('{') != content.count('}') or \
           content.count('(') != content.count(')'):
            print("  [FAIL] Скобки не сбалансированы — откат")
            jsx_file.write_text(backup_jsx.read_text(encoding="utf-8"), encoding="utf-8")
            sys.exit(1)

        jsx_file.write_text(content, encoding="utf-8")
        print("  [OK] Файл сохранён")

    # ====================================================================
    # CSS: компактный селект
    # ====================================================================
    print()
    print("--- sets.css ---")
    css = css_file.read_text(encoding="utf-8")
    if "sets-select-sm" not in css:
        css += """
/* PATCH-146: компактный селект формата */
.sets-select-sm { min-width: 76px; }
"""
        css_file.write_text(css, encoding="utf-8")
        print("  [OK] .sets-select-sm добавлен")
    else:
        print("  [OK] Уже есть")

    # ====================================================================
    # BACKEND: валидация aspect_ratio
    # ====================================================================
    print()
    print("--- api.py ---")
    backup_api = api_file.with_suffix(".py.bak-146")
    backup_api.write_text(api_file.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"  [BAK] {backup_api.name}")

    acontent = api_file.read_text(encoding="utf-8")

    if "PATCH-146" in acontent:
        print("  [OK] Уже применён")
    else:
        n = 0

        # create_set
        old = '''            "aspect_ratio": data.get("aspect_ratio", "16:9"),'''
        new = '''            "aspect_ratio": aspect_ratio,'''
        # вставляем валидацию перед sets_dict[set_id]
        old_block = '''        sets_dict[set_id] = {
            "name": name,
            "max_rows": max_rows,
            "max_columns": max_columns,
            "aspect_ratio": data.get("aspect_ratio", "16:9"),
            "camera_ids": [],
        }'''
        new_block = '''        # PATCH-146: валидация aspect_ratio (16:9 или 4:3)
        aspect_ratio = data.get("aspect_ratio", "16:9")
        if aspect_ratio not in ("16:9", "4:3"):
            return jsonify({"error": "aspect_ratio must be '16:9' or '4:3'"}), 400
        sets_dict[set_id] = {
            "name": name,
            "max_rows": max_rows,
            "max_columns": max_columns,
            "aspect_ratio": aspect_ratio,
            "camera_ids": [],
        }'''
        if old_block in acontent:
            acontent = acontent.replace(old_block, new_block, 1)
            n += 1
            print("  [OK] create_set: валидация aspect_ratio")

        # update_set
        old_upd = '''        if "aspect_ratio" in data:
            target_set.aspect_ratio = data["aspect_ratio"]'''
        new_upd = '''        # PATCH-146: валидация aspect_ratio
        if "aspect_ratio" in data:
            if data["aspect_ratio"] not in ("16:9", "4:3"):
                return jsonify({"error": "aspect_ratio must be '16:9' or '4:3'"}), 400
            target_set.aspect_ratio = data["aspect_ratio"]'''
        if old_upd in acontent:
            acontent = acontent.replace(old_upd, new_upd, 1)
            n += 1
            print("  [OK] update_set: валидация aspect_ratio")

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
    print("  • UI: селект 'Формат: [16:9 ▾]' рядом с размерностью")
    print("  • Дефолт при создании набора: 16:9")
    print("  • Бэкенд: 400 при значении вне ('16:9', '4:3')")
    print()
    print("Применение:")
    print("  cd frontend && npm run build")
    print("  перезапуск: python main.py")
    print("  коммит: git add -A && git commit && git push")
    print("=" * 76)


if __name__ == "__main__":
    main()