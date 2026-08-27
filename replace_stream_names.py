# -*- coding: utf-8 -*-
"""
Скрипт замены русских названий потоков на английские.
"""
import os

FILES = [
    "app/models.py",
    "app/services/stream_manager.py",
    "app/services/camera_service.py",
    "app/routes/hls.py",
    "app/workers/hls_worker.py",
    "frontend/src/api.js",
    "frontend/src/components/CameraCard.jsx",
    "frontend/src/components/ContextMenu.jsx",
    "frontend/src/components/FullscreenCamera.jsx",
    "frontend/src/pages/MonitorPage.jsx",
]

REPLACEMENTS = [
    ("_основной", "_main"),
    ("_дополнительный", "_sub"),
    ("'основной'", "'main'"),
    ("'дополнительный'", "'sub'"),
    ('"основной"', '"main"'),
    ('"дополнительный"', '"sub"'),
    ('f"{self.id}_основной"', 'f"{self.id}_main"'),
    ('f"{self.id}_дополнительный"', 'f"{self.id}_sub"'),
    ('`${camera.id}_основной`', '`${camera.id}_main`'),
    ('`${camera.id}_дополнительный`', '`${camera.id}_sub`'),
]


def replace_in_file(filepath):
    if not os.path.exists(filepath):
        print(f"⚠️  {filepath} не найден")
        return False

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content
    for old, new in REPLACEMENTS:
        content = content.replace(old, new)

    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  ✔ {filepath}")
        return True
    else:
        print(f"  ⚠️  {filepath} (без изменений)")
        return False


changed = sum(1 for f in FILES if replace_in_file(f))
print(f"\n✅ Изменено файлов: {changed}")