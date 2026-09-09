#!/usr/bin/env python3
"""
scripts/seed_db.py
==================
Seed данных при первой установке (заменяет legacy _populate_from_json).

Использование:
  python scripts/seed_db.py

Загружает cameras.json и sets.json из data/ в БД.
"""
import json
from pathlib import Path
from app.db import get_db
from app.db.models import Camera, Set, set_cameras


def seed():
    base_dir = Path(__file__).resolve().parent.parent
    data_dir = base_dir / "data"

    cameras_file = data_dir / "cameras.json"
    sets_file = data_dir / "sets.json"

    with get_db() as session:
        # Проверяем, есть ли уже данные
        if session.query(Camera).count() > 0:
            print("  [SKIP] камеры уже есть в БД")
            return

        # Камеры
        if cameras_file.exists():
            with open(cameras_file, "r", encoding="utf-8") as f:
                cameras_data = json.load(f)
            if isinstance(cameras_data, list):
                for cam in cameras_data:
                    session.add(Camera(
                        id=cam.get("id", ""),
                        name=cam.get("name", ""),
                        login=cam.get("login", ""),
                        pass_=cam.get("pass", ""),
                        ipaddress=cam.get("ipaddress", ""),
                        port=cam.get("port", "554"),
                        main_url=str(cam.get("main_url", "")).lstrip("/"),
                        sub_url=str(cam.get("sub_url", "")).lstrip("/"),
                        sub2_url=str(cam.get("sub2_url", "")).lstrip("/"),
                        enabled=bool(cam.get("enabled", True)),
                        comment=cam.get("comment", ""),
                        audio=bool(cam.get("audio", True)),
                        location=cam.get("location", ""),
                    ))
                print(f"  [OK] загружено {len(cameras_data)} камер")

        # Наборы
        if sets_file.exists():
            with open(sets_file, "r", encoding="utf-8") as f:
                sets_data = json.load(f)
            sets_dict = sets_data.get("sets", {})
            for set_id, set_info in sets_dict.items():
                s = Set(
                    id=set_id,
                    name=set_info.get("name", set_id),
                    grid_columns=set_info.get("grid_columns", 4),
                    grid_rows=set_info.get("grid_rows", 3),
                    aspect_ratio=set_info.get("aspect_ratio", "16:9"),
                )
                session.add(s)
                session.flush()
                camera_ids = set_info.get("cameras", [])
                for pos, cam_id in enumerate(camera_ids):
                    if session.query(Camera).filter_by(id=cam_id).first():
                        session.execute(
                            set_cameras.insert().values(
                                set_id=set_id, camera_id=cam_id, position=pos
                            )
                        )
            print(f"  [OK] загружено {len(sets_dict)} наборов")


if __name__ == "__main__":
    print("Seed БД...")
    seed()
    print("✅ Готово")
