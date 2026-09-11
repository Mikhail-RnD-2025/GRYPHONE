#!/usr/bin/env python3
"""
222. update_scripts/222_sanitize_route_id.py
----------------------------------------------------------------------------
hls_worker.py: санитизация route_id для файловой системы.

Windows запрещает символы < > : " / \\ | ? * в именах файлов/папок.
Новые камеры пользователя имеют ID с префиксом *- (например *-403-P-GAVw-026),
что вызывает WinError 123 при os.makedirs().

Фикс:
  • _sanitize_for_fs(): заменяет запрещённые символы на "_"
  • route_id санитизируется в начале hls_worker() → safe_route_id
  • safe_route_id используется везде, где route_id идёт в файловый путь
  • Оригинальный route_id сохраняется для статусов/SSE/логов

ЗАПУСК: python update_scripts/222_sanitize_route_id.py
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


def main():
    root = find_project_root()
    f = root / "app" / "workers" / "hls_worker.py"

    print("=" * 76)
    print("222: санитизация route_id для Windows filesystem")
    print("=" * 76)
    print()

    b = f.with_suffix(".py.bak-222")
    b.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    c = f.read_text(encoding="utf-8")

    if "PATCH-222" in c:
        print("  [OK] уже применён")
        return

    # 1. Импортируем re если нет
    if "import re" not in c:
        lines = c.split("\n")
        for i, ln in enumerate(lines):
            if ln.startswith("import ") or ln.startswith("from "):
                lines.insert(i, "import re  # PATCH-222")
                break
        c = "\n".join(lines)
        print("  [OK] import re")

    # 2. Добавляем функцию санитизации перед первой функцией
    lines = c.split("\n")
    insert_idx = None
    for i, ln in enumerate(lines):
        if ln.startswith("def ") or ln.startswith("async def "):
            insert_idx = i
            break

    if insert_idx is None:
        print("  [FAIL] не найдена точка вставки")
        sys.exit(1)

    sanitize_func = '''
# ============================================================================
# PATCH-222: санитизация route_id для файловой системы
# Windows запрещает: < > : " / \\ | ? *
# Применяется всегда (кроссплатформенность).
# ============================================================================
_INVALID_FS_CHARS = re.compile(r'[<>:"/\\\\|?*]')
def _sanitize_for_fs(s: str) -> str:
    """Заменяет запрещённые символы Windows на "_". Оригинальный route_id
    сохраняется для статусов/SSE — санитизация применяется только к путям."""
    return _INVALID_FS_CHARS.sub('_', s) if s else s

'''
    lines.insert(insert_idx, sanitize_func)
    c = "\n".join(lines)
    print("  [OK] _sanitize_for_fs() добавлена")

    # 3. В начале hls_worker создаём safe_route_id
    # Ищем строку с def hls_worker и вставляем после неё
    lines = c.split("\n")
    for i, ln in enumerate(lines):
        if "async def hls_worker" in ln or "def hls_worker" in ln:
            # Вставляем safe_route_id после первого блока кода
            # Ищем первую непустую строку после def
            for j in range(i+1, min(i+10, len(lines))):
                if lines[j].strip() and not lines[j].strip().startswith('#') and not lines[j].strip().startswith('"""'):
                    lines.insert(j, "    safe_route_id = _sanitize_for_fs(route_id)  # PATCH-222")
                    print(f"  [OK] safe_route_id создан в строке {j+1}")
                    break
            break
    c = "\n".join(lines)

    # 4. Заменяем использование route_id в путях на safe_route_id
    replacements = [
        # out_dir = project_root / hls_cache / "camera" / route_id
        ('out_dir = project_root / hls_cache / "camera" / route_id',
         'out_dir = project_root / hls_cache / "camera" / safe_route_id',
         'out_dir'),
        # build_ffmpeg_cmd(url, route_id, ...)
        ('cmd = build_ffmpeg_cmd(url, route_id, mode, ff_cfg, str(project_root / hls_cache))',
         'cmd = build_ffmpeg_cmd(url, safe_route_id, mode, ff_cfg, str(project_root / hls_cache))',
         'build_ffmpeg_cmd'),
        # pkill с route_id в путях
        ('if f"hls_cache/camera/{route_id}" in cmdline:',
         'if f"hls_cache/camera/{safe_route_id}" in cmdline:',
         'pkill check'),
        ('["pkill", "-9", "-f", f"hls_cache/camera/{route_id}"],',
         '["pkill", "-9", "-f", f"hls_cache/camera/{safe_route_id}"],',
         'pkill command'),
    ]

    n = 0
    for old, new, label in replacements:
        if old in c:
            c = c.replace(old, new, 1)
            n += 1
            print(f"  [OK] {label}: route_id → safe_route_id")
        else:
            print(f"  [SKIP] {label} не найден")

    if n < 4:
        print(f"  [WARN] применено только {n}/4 замен")

    # Sanity check
    try:
        compile(c, str(f), "exec")
    except SyntaxError as e:
        print(f"  [FAIL] синтаксис: {e} — откат")
        f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
        sys.exit(1)

    f.write_text(c, encoding="utf-8")
    print(f"  [OK] файл сохранён (замен: {n})")

    print()
    print("=" * 76)
    print("✅ PATCH-222 готов! Перезапуск сервера:")
    print()
    print(f"  cd {root} && python main.py")
    print()
    print("Ожидаемо:")
    print("  • Директории hls_cache/camera/_-403-P-GAVw-026_main создаются")
    print("    (* заменяется на _)")
    print("  • Воркеры стартуют без WinError 123")
    print("  • SSE/health используют оригинальный route_id (*-...) — работает")
    print()
    print("⚠️  Рекомендация: переименуйте камеры, убрав * из ID.")
    print("   Символ * в ID создаёт проблемы:")
    print("   - Windows не позволяет создавать файлы/папки")
    print("   - Может ломать URL-кодирование в HLS-плейлистах")
    print("   - В /cameras: найдите камеры с * и переименуйте в нормальные ID")
    print("=" * 76)
    print()
    print("📦 Коммит:")
    print(f"cd {root}")
    print("git add -A")
    print('git commit -m "fix(workers): sanitize route_id for Windows filesystem (PATCH-222)" \\')
    print('  -m "hls_worker: _sanitize_for_fs() replaces < > : \" / \\ | ? * with _" \\')
    print('  -m "safe_route_id used for paths, original route_id for SSE/status" \\')
    print('  -m "fixes WinError 123 when camera IDs contain * (e.g. *-403-P-GAVw-026)" \\')
    print('  -m "cross-platform: same sanitization on Windows and Linux"')
    print("git push")
    print("=" * 76)


if __name__ == "__main__":
    main()