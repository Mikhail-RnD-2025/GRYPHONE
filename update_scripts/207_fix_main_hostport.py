#!/usr/bin/env python3
"""
207.3.3 update_scripts/207_fix_main_hostport.py
----------------------------------------------------------------------------
main.py: host/port получаются через 3 fallback-стратегии:
  1) config.get("server") → dict
  2) config.get("server.port") → dotted
  3) setting_repo.get_json("config") напрямую

ЗАПУСК: python update_scripts/207_fix_main_hostport.py
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


HELPER = '''def _server_addr():
    """PATCH-207.3.3: host/port с fallback-стратегиями (любой API ConfigManager)."""
    # 1) config.get("server") -> dict
    try:
        srv = config.get("server")
        if isinstance(srv, dict):
            return srv.get("host", "0.0.0.0"), int(srv.get("port", 5000))
    except Exception:
        pass
    # 2) dotted-ключи
    try:
        h = config.get("server.host", "0.0.0.0") or "0.0.0.0"
        p = config.get("server.port", 5000)
        if p is not None:
            return h, int(p)
    except Exception:
        pass
    # 3) напрямую из setting_repo
    from app.db.repositories import setting_repo
    raw = setting_repo.get_json("config", {}) or {}
    srv = raw.get("server", {}) or {}
    return srv.get("host", "0.0.0.0"), int(srv.get("port", 5000))


'''


def main():
    root = find_project_root()
    f = root / "main.py"

    print("=" * 76)
    print("207.3.3: host/port через fallback-стратегии")
    print("=" * 76)
    print()

    b = f.with_suffix(".py.bak-20733")
    b.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    c = f.read_text(encoding="utf-8")

    old = '''    host = config.get("server.host", "0.0.0.0")
    port = int(config.get("server.port", 5000))'''
    new = '''    host, port = _server_addr()'''

    if old not in c:
        print("  [FAIL] якорь host/port не найден — откат")
        f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
        sys.exit(1)

    c = c.replace(old, new, 1)

    # вставляем хелпер перед def main():
    anchor = "def main():"
    if "_server_addr" not in c.split(anchor)[0]:
        c = c.replace(anchor, HELPER + anchor, 1)
        print("  [OK] хелпер _server_addr() добавлен")

    try:
        compile(c, str(f), "exec")
        f.write_text(c, encoding="utf-8")
        print("  [OK] host/port = _server_addr()")
    except SyntaxError as e:
        print(f"  [FAIL] синтаксис: {e} — откат")
        f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
        sys.exit(1)

    print()
    print("=" * 76)
    print("✅ Готово! Запустите:")
    print("  python main.py")
    print()
    print("Ожидаемо:")
    print("  [OK] alembic upgrade head")
    print("  ✅ Приложение создано и настроено")
    print("  🚀 Запуск сервера на 0.0.0.0:5000")
    print("=" * 76)


if __name__ == "__main__":
    main()