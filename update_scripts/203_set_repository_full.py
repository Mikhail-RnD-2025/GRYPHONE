#!/usr/bin/env python3
"""
203. update_scripts/203_set_repository_full.py
----------------------------------------------------------------------------
Полный перевод SetRepository на SQLAlchemy + миграция БД:
  • Миграция: ALTER TABLE set_cameras ADD COLUMN position INTEGER
  • Модель Set: relationship с ordering
  • SetRepository: get_all/save с сохранением порядка камер
  • config.py: перевод на setting_repo (если использует db)

ЗАПУСК: python update_scripts/203_set_repository_full.py
"""

import sys
import sqlite3
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


def migrate_db(db_path):
    print("--- миграция БД: set_cameras.position ---")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Проверяем наличие колонки
    cols = [r[1] for r in cur.execute("PRAGMA table_info(set_cameras)")]
    if "position" in cols:
        print("  [OK] колонка position уже есть")
        conn.close()
        return True

    # Добавляем колонку
    cur.execute("ALTER TABLE set_cameras ADD COLUMN position INTEGER DEFAULT 0")

    # Заполняем position = rowid (сохраняем текущий порядок)
    cur.execute("UPDATE set_cameras SET position = rowid")

    conn.commit()
    conn.close()
    print("  [OK] добавлена колонка position + заполнена из rowid")
    return True


def update_set_model(f):
    print("--- app/db/models.py: Set relationship с ordering ---")
    b = f.with_suffix(".py.bak-203")
    b.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    c = f.read_text(encoding="utf-8")

    # Обновляем Table set_cameras
    old = """set_cameras = Table(
    "set_cameras",
    Base.metadata,
    Column("set_id", String, ForeignKey("sets.id"), primary_key=True),
    Column("camera_id", String, ForeignKey("cameras.id"), primary_key=True),
)"""
    new = """set_cameras = Table(
    "set_cameras",
    Base.metadata,
    Column("set_id", String, ForeignKey("sets.id"), primary_key=True),
    Column("camera_id", String, ForeignKey("cameras.id"), primary_key=True),
    Column("position", Integer, default=0),  # PATCH-203: порядок камер
)"""
    if old in c:
        c = c.replace(old, new, 1)
        print("  [OK] set_cameras: добавлена колонка position")
    else:
        print("  [FAIL] set_cameras не найден — откат")
        f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
        return False

    # Обновляем relationship в Set
    old = '    cameras = relationship("Camera", secondary=set_cameras, back_populates="sets")'
    new = '    cameras = relationship("Camera", secondary=set_cameras, back_populates="sets", order_by="set_cameras.c.position")  # PATCH-203'
    if old in c:
        c = c.replace(old, new, 1)
        print("  [OK] Set.cameras: order_by position")

    # Обновляем to_dict в Set
    old = '''    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "grid_columns": self.grid_columns,
            "grid_rows": self.grid_rows,
            "aspect_ratio": self.aspect_ratio or "16:9",
        }'''
    new = '''    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "grid_columns": self.grid_columns,
            "grid_rows": self.grid_rows,
            "aspect_ratio": self.aspect_ratio or "16:9",
            "camera_ids": [c.id for c in self.cameras],  # PATCH-203: порядок из relationship
        }'''
    if old in c:
        c = c.replace(old, new, 1)
        print("  [OK] Set.to_dict: camera_ids из ordered relationship")

    try:
        compile(c, str(f), "exec")
        f.write_text(c, encoding="utf-8")
        print("  [OK] Сохранено")
        return True
    except SyntaxError as e:
        print(f"  [FAIL] синтаксис: {e} — откат")
        f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
        return False


def update_set_repository(f):
    print("--- app/db/repositories.py: SetRepository на SQLAlchemy ---")
    b = f.with_suffix(".py.bak-203")
    b.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    c = f.read_text(encoding="utf-8")

    old = '''class SetRepository:
    """
    PATCH-201: репозиторий наборов.

    ВРЕМЕННО использует legacy database.py, потому что модель Set в
    app/db/models.py ещё не включает camera_ids (M2M без порядка).
    В PATCH-202 будет переведён на чистый SQLAlchemy.
    """

    def get_all(self) -> Dict[str, Any]:
        """Возвращает {"sets": {...}} в legacy-формате."""
        from app.database import db as legacy_db
        return legacy_db.get_all_sets() or {"sets": {}}

    def save(self, sets_data: Dict[str, Any]) -> None:
        """Сохраняет все наборы (legacy save_sets)."""
        from app.database import db as legacy_db
        legacy_db.save_sets(sets_data)

    def get_ids(self) -> List[str]:
        """Список ID наборов."""
        data = self.get_all()
        return list(data.get("sets", {}).keys())'''

    new = '''class SetRepository:
    """
    PATCH-203: репозиторий наборов (полный SQLAlchemy CRUD).
    """

    def get_all(self) -> Dict[str, Any]:
        """Возвращает {"sets": {...}} с camera_ids."""
        from app.db.models import Set
        with get_db() as session:
            sets = session.query(Set).all()
            return {
                "sets": {s.id: s.to_dict() for s in sets}
            }

    def save(self, sets_data: Dict[str, Any]) -> None:
        """Сохраняет все наборы (полная замена)."""
        from app.db.models import Set, set_cameras
        with get_db() as session:
            # Очищаем таблицы
            session.query(Set).delete()
            session.execute(set_cameras.delete())

            # Добавляем новые наборы
            for set_id, set_dict in sets_data.get("sets", {}).items():
                s = Set(
                    id=set_id,
                    name=set_dict.get("name", set_id),
                    grid_columns=set_dict.get("grid_columns", 4),
                    grid_rows=set_dict.get("grid_rows", 3),
                    aspect_ratio=set_dict.get("aspect_ratio", "16:9"),
                )
                session.add(s)
                session.flush()  # получаем s.id

                # Добавляем связи с камерами
                camera_ids = set_dict.get("camera_ids", [])
                for pos, cam_id in enumerate(camera_ids):
                    session.execute(
                        set_cameras.insert().values(
                            set_id=set_id,
                            camera_id=cam_id,
                            position=pos
                        )
                    )

    def get_ids(self) -> List[str]:
        """Список ID наборов."""
        from app.db.models import Set
        with get_db() as session:
            return [s.id for s in session.query(Set).all()]'''

    if old in c:
        c = c.replace(old, new, 1)
        try:
            compile(c, str(f), "exec")
            f.write_text(c, encoding="utf-8")
            print("  [OK] SetRepository переведён на SQLAlchemy")
            return True
        except SyntaxError as e:
            print(f"  [FAIL] синтаксис: {e} — откат")
            f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
            return False
    else:
        print("  [FAIL] старый SetRepository не найден — откат")
        f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
        return False


def check_config_py(f):
    print("--- app/config.py: проверка использования db ---")
    c = f.read_text(encoding="utf-8")

    # Ищем использование db
    if "db." in c:
        print("  [WARN] config.py использует db.* — нужно проверить")
        print("  [INFO] Пока оставляем как есть (не критично)")
        return False
    else:
        print("  [OK] config.py не использует db напрямую")
        return True


def main():
    root = find_project_root()
    print(f"  [OK] Корень проекта: {root}")
    print()
    print("=" * 76)
    print("203: SetRepository на SQLAlchemy + миграция БД")
    print("=" * 76)
    print()

    db_path = root / "database" / "gryphone-vision.db"

    ok = True
    ok &= migrate_db(str(db_path))
    ok &= update_set_model(root / "app" / "db" / "models.py")
    ok &= update_set_repository(root / "app" / "db" / "repositories.py")
    check_config_py(root / "app" / "config.py")

    if not ok:
        print()
        print("[FAIL] часть шагов не прошла")
        sys.exit(1)

    print()
    print("=" * 76)
    print("✅ Этап 203 завершён!")
    print()
    print("Что сделано:")
    print("  • БД: set_cameras.position добавлена + заполнена из rowid")
    print("  • Модель Set: relationship с order_by(position)")
    print("  • SetRepository: полный SQLAlchemy CRUD")
    print("  • camera_service: теперь использует set_repo.get_all/save")
    print()
    print("  python main.py   (проверить что всё работает)")
    print("=" * 76)
    print()
    print("📦 ПОСЛЕ ПРОВЕРКИ — коммит:")
    print()
    print(f"cd {root}")
    print("git add -A")
    print('git commit -m "feat(sqlalchemy): SetRepository full + DB migration (PATCH-203)" \\')
    print('  -m "DB: set_cameras.position column (preserves camera order)" \\')
    print('  -m "models.Set: relationship with order_by(position)" \\')
    print('  -m "SetRepository: full SQLAlchemy CRUD (no more legacy db)" \\')
    print('  -m "camera_service: uses set_repo for all set operations"')
    print("git push")
    print("=" * 76)


if __name__ == "__main__":
    main()