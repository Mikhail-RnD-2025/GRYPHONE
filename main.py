# -*- coding: utf-8 -*-
"""
main.py
=======
Точка входа бэкенда.

PATCH-207.3: alembic upgrade head перед create_app()
"""
import logging
import subprocess
import sys
from pathlib import Path

# PATCH-207.3: миграции БД перед загрузкой приложения
def run_alembic_upgrade():
    """Применяет все неприменённые миграции."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=Path(__file__).parent,
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode != 0:
            print(f"[WARN] alembic upgrade failed: {result.stderr}")
        else:
            print("[OK] alembic upgrade head")
    except Exception as e:
        print(f"[WARN] alembic upgrade error: {e}")

run_alembic_upgrade()

from app import create_app
from app.config import config

# ============================================================
# PATCH-123: очистка старых snapshot при старте сервера
# ============================================================
def cleanup_old_snapshots_123():
    """Удаляет старые snapshot-файлы, чтобы не показывать 'старые потоки'."""
    import glob
    import os
    removed = 0
    for pattern in ["**/*.jpg", "**/*.jpeg"]:
        for f in glob.glob(os.path.join("data", pattern), recursive=True):
            try:
                os.remove(f)
                removed += 1
            except OSError:
                pass
    for pattern in ["**/*.jpg", "**/*.jpeg"]:
        for f in glob.glob(os.path.join("snapshots", pattern), recursive=True):
            try:
                os.remove(f)
                removed += 1
            except OSError:
                pass
    print(f"[PATCH-123] Удалено старых snapshot: {removed}")

cleanup_old_snapshots_123()
# ============================================================


logger = logging.getLogger(__name__)


def _server_addr():
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


def main():
    """Главная функция: создаёт и запускает приложение."""
    app = create_app()

    host, port = _server_addr()

    logger.info(f"🚀 Запуск сервера на {host}:{port}")
    app.run(host=host, port=port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
