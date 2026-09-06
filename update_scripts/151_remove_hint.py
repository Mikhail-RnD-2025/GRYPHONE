#!/usr/bin/env python3
"""
151. update_scripts/151_remove_hint.py
----------------------------------------------------------------------------
Убирает подсказку "💡 Перетащите камеру..." из SetsPage:
  • удаляет JSX-блок .sets-hint
  • удаляет CSS-правило .sets-hint

ЗАПУСК: python update_scripts/151_remove_hint.py
"""

import sys
from pathlib import Path


def main():
    project_root = Path.cwd()
    jsx_file = project_root / "frontend" / "src" / "pages" / "SetsPage.jsx"
    css_file = project_root / "frontend" / "src" / "styles" / "sets.css"

    print("=" * 76)
    print("151: Убираем подсказку drag & drop")
    print("=" * 76)
    print()

    # --- JSX ---
    backup_jsx = jsx_file.with_suffix(".jsx.bak-151")
    backup_jsx.write_text(jsx_file.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"  [BAK] {backup_jsx.name}")

    content = jsx_file.read_text(encoding="utf-8")

    # Удаляем блок hint
    hint_block = """          <div className="sets-hint">
            💡 Перетащите камеру из списка в ячейку или внутри сетки для изменения порядка.
            Drop обратно в список — убирает камеру из набора.
          </div>"""
    if hint_block in content:
        content = content.replace(hint_block, "", 1)
        print("  [OK] JSX-блок .sets-hint удалён")
    else:
        print("  [WARN] Блок не найден (возможно уже удалён)")

    if content.count('{') != content.count('}') or \
       content.count('(') != content.count(')'):
        print("  [FAIL] Скобки — откат")
        jsx_file.write_text(backup_jsx.read_text(encoding="utf-8"), encoding="utf-8")
        sys.exit(1)

    jsx_file.write_text(content, encoding="utf-8")
    print("  [OK] Сохранено")

    # --- CSS ---
    css = css_file.read_text(encoding="utf-8")
    css_block = """.sets-hint {
  font-size: 0.75rem;
  color: #64748b;
  padding: 6px 0 0;
  text-align: center;
}

"""
    if css_block in css:
        css = css.replace(css_block, "", 1)
        css_file.write_text(css, encoding="utf-8")
        print("  [OK] CSS-правило .sets-hint удалено")
    else:
        print("  [WARN] CSS-правило не найдено")

    print()
    print("=" * 76)
    print("✅ Готово!")
    print()
    print("  cd frontend && npm run build && Ctrl+Shift+R")
    print("=" * 76)


if __name__ == "__main__":
    main()