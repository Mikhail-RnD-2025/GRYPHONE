# -*- coding: utf-8 -*-
"""
app/database.py
===============
Слой доступа к данным (репозиторий).

Сейчас реализован поверх встроенной реляционной БД (таблица "ключ-значение").
Интерфейс намеренно узкий (чтение / сохранение / список ключей), чтобы будущая
замена на другую СУБД (через внешний драйвер) затронула только этот модуль.

Публичный интерфейс:
    db.get(key, default)  -> объект (распакованный из текстового формата)
    db.save(key, data)    -> сохраняет объект
    db.keys()             -> список всех ключей
"""
import json
import logging
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

# Database path configuration
DATABASE_PATH = BASE_DIR / 'database' / 'gryphone-vision.db'
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / 'data'

logger = logging.getLogger(__name__)

# Путь к файлу БД. Можно переопределить переменной окружения.
DB_PATH = os.environ.get("GRYPHONE_DB", str(DATABASE_PATH))


def _json_default(obj):
    """Сериализатор для объектов, не сериализуемых по умолчанию."""
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    return str(obj)


class Database:
    """Обёртка над хранилищем "ключ-значение"."""

    def __init__(self, path: str = DB_PATH):
        self.db_path = path
        self._init_db()

    # ------------------------------------------------------------------
    # Служебные методы
    # ------------------------------------------------------------------
    def _get_conn(self):
        """Создаёт новое соединение (потокобезопасно через флаг)."""
        return sqlite3.connect(self.db_path, check_same_thread=False)

    @contextmanager
    def get_db(self):
        """Контекстный менеджер: соединение с авто-коммитом/откатом."""
        conn = self._get_conn()
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Создаёт таблицу настроек и при необходимости мигрирует файлы."""
        with self.get_db() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS settings "
                "(key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            # Миграция нужна только если таблица пуста.
            if conn.execute("SELECT COUNT(*) FROM settings").fetchone()[0] == 0:
                self._migrate_from_files(conn)

    def _migrate_from_files(self, conn) -> None:
        """Переносит данные из устаревших файлов в БД (однократно)."""
        logger.info("📦 Миграция из файлов...")
        for fname, key in [
            (DATA_DIR / DATA_DIR / 'config.json', "config"),
            (DATA_DIR / DATA_DIR / 'cameras.json', "cameras"),
            (DATA_DIR / DATA_DIR / 'sets.json', "sets"),
        ]:
            if os.path.exists(fname):
                try:
                    with open(fname, "r", encoding="utf-8") as fh:
                        data = json.load(fh)
                    conn.execute(
                        "INSERT OR REPLACE INTO settings VALUES(?,?)",
                        (key, json.dumps(data, ensure_ascii=False)),
                    )
                    logger.info("  ✔ Мигрирован %s", fname)
                except Exception as e:
                    logger.error("❌ Ошибка миграции %s: %s", fname, e)
        logger.info("✅ Миграция завершена.")

    # ------------------------------------------------------------------
    # Публичный интерфейс
    # ------------------------------------------------------------------
    def get(self, key: str, default=None):
        """Читает значение по ключу. Возвращает ``default``, если нет."""
        with self.get_db() as conn:
            row = conn.execute(
                "SELECT value FROM settings WHERE key=?", (key,)
            ).fetchone()
            return json.loads(row[0]) if row else default

    def save(self, key: str, data) -> None:
        """Сохраняет значение по ключу."""
        with self.get_db() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO settings VALUES(?,?)",
                (key, json.dumps(data, ensure_ascii=False, default=_json_default)),
            )

    def keys(self):
        """Возвращает список всех ключей."""
        with self.get_db() as conn:
            rows = conn.execute("SELECT key FROM settings").fetchall()
            return [r[0] for r in rows]


# Единственный экземпляр БД для всего приложения.
db = Database()
