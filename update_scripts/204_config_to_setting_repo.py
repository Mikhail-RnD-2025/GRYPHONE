#!/usr/bin/env python3
"""
204. update_scripts/204_config_to_setting_repo.py
----------------------------------------------------------------------------
Финальная зачистка прикладного кода от legacy database.py:
  • SettingRepository: + get_json()/set_json() (семантика legacy db.get/db.save)
  • config.py: db.get/db.save → setting_repo.get_json/set_json

После патча legacy database.py остаётся ТОЛЬКО как:
  • поставщик пути БД для app/db/__init__.py
  • создатель таблиц при первом старте (_create_tables)
До PATCH-205 (Alembic) это его единственные роли.

ЗАПУСК: python update_scripts/204_config_to_setting_repo.py
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


JSON_METHODS = '''
    def get_json(self, key: str, default: Any = None) -> Any:
        """PATCH-204: читает значение с JSON-десериализацией.
        Совместимо с legacy db.get(): при ошибке парсинга возвращает сырую строку."""
        raw = self.get(key, None)
        if raw is None:
            return default
        try:
            return json.loads(raw)
        except (ValueError, TypeError):
            return raw

    def set_json(self, key: str, value: Any) -> None:
        """PATCH-204: сохраняет значение с JSON-сериализацией.
        Совместимо с legacy db.save(): ensure_ascii=False."""
        self.set(key, json.dumps(value, ensure_ascii=False))
'''


def patch_repositories(f):
    print("--- repositories.py: + get_json/set_json ---")
    b = f.with_suffix(".py.bak-204")
    b.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    c = f.read_text(encoding="utf-8")
    n = 0

    if "def get_json" not in c:
        # import json в шапку
        old = "from typing import List, Dict, Any, Optional"
        if old in c:
            c = c.replace(old, "import json  # PATCH-204\nfrom typing import List, Dict, Any, Optional", 1)
            n += 1
            print("  [OK] import json")

        # вставляем методы после set()
        anchor = """    def set(self, key: str, value: str) -> None:
        \"\"\"Сохраняет значение (INSERT OR REPLACE).\"\"\"
        with get_db() as session:
            existing = session.query(Setting).get(key)
            if existing:
                existing.value = value
            else:
                session.add(Setting(key=key, value=value))"""
        if anchor in c:
            c = c.replace(anchor, anchor + JSON_METHODS, 1)
            n += 1
            print("  [OK] get_json/set_json добавлены")

    if n == 2 or "def get_json" in f.read_text(encoding="utf-8"):
        try:
            compile(c, str(f), "exec")
            f.write_text(c, encoding="utf-8")
            print("  [OK] Сохранено")
            return True
        except SyntaxError as e:
            print(f"  [FAIL] синтаксис: {e} — откат")
            f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
            return False
    print("  [FAIL] якоря не найдены — откат")
    f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
    return False


def patch_config(f):
    print("--- config.py: db → setting_repo ---")
    b = f.with_suffix(".py.bak-204")
    b.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    c = f.read_text(encoding="utf-8")
    n = 0

    pairs = [
        ("from app.database import db",
         "from app.db.repositories import setting_repo  # PATCH-204"),
        ("        saved = db.get(self.KEY, None)",
         "        saved = setting_repo.get_json(self.KEY, None)  # PATCH-204"),
        ("            db.save(self.KEY, self._default)",
         "            setting_repo.set_json(self.KEY, self._default)  # PATCH-204"),
        ("        db.save(self.KEY, self._data)",
         "        setting_repo.set_json(self.KEY, self._data)  # PATCH-204"),
    ]
    for old, new in pairs:
        if old in c:
            c = c.replace(old, new, 1)
            n += 1
            print(f"  [OK] {old.strip()[:40]}...")

    if n == 4:
        try:
            compile(c, str(f), "exec")
            f.write_text(c, encoding="utf-8")
            print("  [OK] Сохранено")
            return True
        except SyntaxError as e:
            print(f"  [FAIL] синтаксис: {e} — откат")
            f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
            return False
    print(f"  [FAIL] {n}/4 — откат")
    f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
    return False


SMOKE = '''"""Smoke-тест PATCH-204: конфиг через setting_repo == legacy db.get."""
import sys
sys.path.insert(0, ".")
from app.db.repositories import setting_repo
from app.database import db as legacy_db

a = setting_repo.get_json("config", None)
b = legacy_db.get("config", None)
print("setting_repo.get_json('config') == legacy db.get('config'):", a == b)
if a is None or b is None:
    print("[FAIL] конфиг не читается")
    sys.exit(1)
if a != b:
    print("[FAIL] расхождение!")
    sys.exit(1)
from app.config import config
print("ConfigManager загружен, ключей:", len(config._data) if hasattr(config, "_data") else "?")
print("✅ PATCH-204 согласован с legacy")
'''


def main():
    root = find_project_root()
    print("=" * 76)
    print("204: ConfigManager → setting_repo (финальная зачистка)")
    print("=" * 76)
    print()

    ok = True
    ok &= patch_repositories(root / "app" / "db" / "repositories.py")
    ok &= patch_config(root / "app" / "config.py")
    if not ok:
        sys.exit(1)

    test_f = root / "smoke_test_204.py"
    test_f.write_text(SMOKE, encoding="utf-8")
    print()
    print("--- smoke-тест ---")
    res = subprocess.run([sys.executable, str(test_f)], cwd=str(root))
    if res.returncode != 0:
        print("  [FAIL]")
        sys.exit(1)
    test_f.unlink()

    print()
    print("=" * 76)
    print("✅ Готово! Проверка:")
    print("  grep -rn \"from app.database import\" app/ --include=\"*.py\"")
    print("  → должен остаться ТОЛЬКО app/db/__init__.py")
    print()
    print("  python main.py  →  curl -s http://127.0.0.1:5000/api/config | head -c 200")
    print("=" * 76)
    print()
    print("📦 Коммит:")
    print()
    print(f"cd {root}")
    print("git add -A")
    print('git commit -m "refactor(sqlalchemy): ConfigManager on setting_repo (PATCH-204)" \\')
    print('  -m "SettingRepository: get_json/set_json (legacy db.get/db.save semantics)" \\')
    print('  -m "config.py: no more legacy db import" \\')
    print('  -m "database.py now only: db path provider + schema bootstrap"')
    print("git push")
    print("=" * 76)


if __name__ == "__main__":
    main()