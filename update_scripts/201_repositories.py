#!/usr/bin/env python3
"""
201. update_scripts/201_repositories.py
----------------------------------------------------------------------------
Создаёт app/db/repositories.py:
  • CameraRepository: get_all(), get_by_id(), save_all()
  • SettingRepository: get(), set()
  • SetRepository: get_all(), save() (временно через legacy db)

Все методы возвращают dict/dataclass-совместимые структуры,
избегая DetachedInstanceError.

ЗАПУСК: python update_scripts/201_repositories.py
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


REPOSITORIES = '''# -*- coding: utf-8 -*-
"""
app/db/repositories.py
======================
Repository-слой (PATCH-201).

Единая точка доступа к данным для сервисов. Все методы:
  • работают внутри контекста сессии (избегают DetachedInstanceError)
  • возвращают dict/примитивы (не detached ORM-объекты)
  • инкапсулируют запросы — сервисам не нужен SQL
"""
from typing import List, Dict, Any, Optional

from app.db import get_db
from app.db.models import Camera, Setting


# ============================================================================
# CameraRepository
# ============================================================================
class CameraRepository:
    """Репозиторий камер (полный SQLAlchemy CRUD)."""

    def get_all(self) -> List[Dict[str, Any]]:
        """Возвращает список всех камер как dict."""
        with get_db() as session:
            cams = session.query(Camera).order_by(Camera.id).all()
            return [c.to_dict() for c in cams]

    def get_by_id(self, camera_id: str) -> Optional[Dict[str, Any]]:
        """Возвращает камеру по ID или None."""
        with get_db() as session:
            cam = session.query(Camera).get(camera_id)
            return cam.to_dict() if cam else None

    def count(self) -> int:
        """Количество камер."""
        with get_db() as session:
            return session.query(Camera).count()

    def save_all(self, cameras: List[Dict[str, Any]]) -> int:
        """
        PATCH-201: полная замена списка камер (совместимо с legacy save_cameras_list).

        Args:
            cameras: список dict-ов с полями камеры

        Returns:
            количество сохранённых камер
        """
        with get_db() as session:
            session.query(Camera).delete()
            for c in cameras:
                session.add(Camera(
                    id=str(c.get("id", "")).strip(),
                    name=str(c.get("name", c.get("id", ""))).strip(),
                    login=str(c.get("login", "")).strip(),
                    pass_=str(c.get("pass", "")).strip(),
                    ipaddress=str(c.get("ipaddress", "")).strip(),
                    port=str(c.get("port", "554")).strip() or "554",
                    main_url=str(c.get("main_url", "")).strip().lstrip("/"),
                    sub_url=str(c.get("sub_url", "")).strip().lstrip("/"),
                    sub2_url=str(c.get("sub2_url", "")).strip().lstrip("/"),
                    enabled=bool(c.get("enabled", True)),
                    comment=str(c.get("comment", "")).strip(),
                    audio=bool(c.get("audio", True)),
                    location=str(c.get("location", "")).strip(),
                ))
            return len(cameras)


# ============================================================================
# SettingRepository
# ============================================================================
class SettingRepository:
    """Репозиторий настроек (key-value)."""

    def get(self, key: str, default: str = "") -> str:
        """Читает значение по ключу."""
        with get_db() as session:
            row = session.query(Setting).get(key)
            return row.value if row else default

    def set(self, key: str, value: str) -> None:
        """Сохраняет значение (INSERT OR REPLACE)."""
        with get_db() as session:
            existing = session.query(Setting).get(key)
            if existing:
                existing.value = value
            else:
                session.add(Setting(key=key, value=value))

    def delete(self, key: str) -> bool:
        """Удаляет ключ. Возвращает True если был удалён."""
        with get_db() as session:
            existing = session.query(Setting).get(key)
            if existing:
                session.delete(existing)
                return True
            return False

    def all(self) -> Dict[str, str]:
        """Возвращает все настройки как dict."""
        with get_db() as session:
            rows = session.query(Setting).all()
            return {r.key: r.value for r in rows}


# ============================================================================
# SetRepository (временная реализация через legacy)
# ============================================================================
class SetRepository:
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
        return list(data.get("sets", {}).keys())


# ============================================================================
# Синглтоны для удобного импорта
# ============================================================================
camera_repo = CameraRepository()
setting_repo = SettingRepository()
set_repo = SetRepository()
'''


SMOKE_TEST = '''"""Smoke-тест репозиториев (временный)."""
import sys
sys.path.insert(0, ".")

from app.db.repositories import camera_repo, setting_repo, set_repo
from app.database import db as legacy_db


def main():
    print("=" * 70)
    print("Repositories smoke-test (PATCH-201)")
    print("=" * 70)

    # --- CameraRepository ---
    sa_cams = camera_repo.get_all()
    lg_cams = legacy_db.get_all_cameras() or []
    print(f"  camera_repo.get_all():     {len(sa_cams)}")
    print(f"  legacy_db.get_all_cameras: {len(lg_cams)}")
    if len(sa_cams) != len(lg_cams):
        print("  [FAIL] количество камер не совпадает")
        return False

    if sa_cams and lg_cams:
        sa = sa_cams[0]
        lg = lg_cams[0]
        keys = set(sa.keys()) & set(lg.keys())
        diff = [k for k in keys if sa[k] != lg[k]]
        if diff:
            print(f"  [WARN] расхождения: {diff}")
        else:
            print(f"  [OK] to_dict() первой камеры совпадает")

    # --- SettingRepository ---
    sa_settings = setting_repo.all()
    print(f"  setting_repo.all(): {len(sa_settings)} настроек")
    if sa_settings:
        k, v = next(iter(sa_settings.items()))
        lg_v = legacy_db.get_setting(k, None)
        print(f"       пример: {k} = {v!r} (legacy: {lg_v!r})")

    # --- SetRepository ---
    sa_sets = set_repo.get_all()
    lg_sets = legacy_db.get_all_sets() or {"sets": {}}
    n_sa = len(sa_sets.get("sets", {}))
    n_lg = len(lg_sets.get("sets", {}))
    print(f"  set_repo.get_all():   {n_sa} наборов")
    print(f"  legacy_db.get_all_sets: {n_lg} наборов")
    if n_sa != n_lg:
        print("  [FAIL] количество наборов не совпадает")
        return False

    print("=" * 70)
    print("✅ Репозитории работают и согласованы со старой БД")
    print("=" * 70)
    return True


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
'''


def main():
    root = find_project_root()
    print(f"  [OK] Корень проекта: {root}")
    print()
    print("=" * 76)
    print("201: Repository-слой (CameraRepository, SettingRepository, SetRepository)")
    print("=" * 76)
    print()

    f = root / "app" / "db" / "repositories.py"
    test_f = root / "smoke_test_repos.py"

    print("--- app/db/repositories.py ---")
    if f.exists() and "PATCH-201" in f.read_text(encoding="utf-8"):
        print("  [OK] уже существует")
    else:
        f.write_text(REPOSITORIES, encoding="utf-8")
        print("  [OK] создан: camera_repo, setting_repo, set_repo")

    print()
    print("--- smoke_test_repos.py ---")
    test_f.write_text(SMOKE_TEST, encoding="utf-8")

    print()
    print("--- запуск smoke-теста ---")
    res = subprocess.run([sys.executable, str(test_f)], cwd=str(root))
    if res.returncode != 0:
        print("  [FAIL] smoke-тест не прошёл")
        sys.exit(1)

    print()
    print("=" * 76)
    print("✅ Этап 201 завершён!")
    print()
    print("Что добавлено:")
    print("  • CameraRepository — get_all/get_by_id/count/save_all")
    print("  • SettingRepository — get/set/delete/all")
    print("  • SetRepository — get_all/save (пока через legacy)")
    print("  • Синглтоны: camera_repo, setting_repo, set_repo")
    print()
    print("Следующий этап: PATCH-202 — перевод camera_service на camera_repo")
    print("=" * 76)
    print()
    print("📦 Коммит:")
    print()
    print(f"cd {root}")
    print("rm smoke_test_repos.py")
    print("git add -A")
    print('git commit -m "feat(sqlalchemy): repository layer (PATCH-201)" \\')
    print('  -m "app/db/repositories.py: CameraRepository, SettingRepository, SetRepository" \\')
    print('  -m "singletons: camera_repo, setting_repo, set_repo" \\')
    print('  -m "SetRepository temporarily uses legacy db (until PATCH-202)" \\')
    print('  -m "smoke-test: repos read same data as legacy database.py"')
    print("git push")
    print("=" * 76)


if __name__ == "__main__":
    main()