#!/usr/bin/env python3
"""
186. update_scripts/186_database_mapping_smart.py
----------------------------------------------------------------------------
Умный парсер блока маппинга в database.py (get_all_cameras):
  находит любую строку вида 'key': row[N] или 'key': bool(row[N])
  и перестраивает маппинг под новую схему.

ЗАПУСК: python update_scripts/186_database_mapping_smart.py
"""

import sys
import re
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


def rewrite_mapping(content):
    """
    Ищет блок маппинга в get_all_cameras и заменяет его.
    Возвращает (new_content, ok).
    """
    # Находим начало блока маппинга: return [ {
    pattern = re.compile(
        r"(return \[\s*\{\s*\n)"
        r"((?:[ \t]+'[a-z_]+': (?:bool\(row\[\d+\]\)|row\[\d+\]),?\s*\n)+)"
        r"([ \t]+\})\s*\n"
        r"([ \t]+for row in rows\s*\n)"
        r"([ \t]+\])",
        re.MULTILINE
    )
    m = pattern.search(content)
    if not m:
        return content, False

    mapping_block = m.group(2)
    indent_match = re.match(r"([ \t]+)'", mapping_block)
    ind = indent_match.group(1) if indent_match else "                "

    # Извлекаем текущие key→N
    current = {}
    for line in mapping_block.split("\n"):
        lm = re.match(r"\s+'(\w+)':\s*(bool\(row\[(\d+)\]\)|row\[(\d+)\]),?", line)
        if lm:
            key = lm.group(1)
            n = int(lm.group(2) or lm.group(3))
            current[key] = {"bool": lm.group(2) is not None, "idx": n}

    if not current:
        return content, False

    # Определяем, какие индексы свободны в новой схеме
    # old: id=0, name=1, main_url=2, sub_url=3, enabled=4, comment=5, audio=6, location=7
    # new: id=0, name=1, login=2, pass=3, ipaddress=4, port=5,
    #      main_url=6, sub_url=7, sub2_url=8, enabled=9, comment=10, audio=11, location=12
    new_mapping = [
        ("id",        0, False),
        ("name",      1, False),
        ("login",     2, False),
        ("pass",      3, False),
        ("ipaddress", 4, False),
        ("port",      5, False),
        ("main_url",  6, False),
        ("sub_url",   7, False),
        ("sub2_url",  8, False),
        ("enabled",   9, True),
        ("comment",   10, False),
        ("audio",     11, True),
        ("location",  12, False),
    ]

    lines = []
    for key, idx, use_bool in new_mapping:
        if use_bool:
            lines.append(f"{ind}'{key}': bool(row[{idx}]),")
        else:
            lines.append(f"{ind}'{key}': row[{idx}],")
    # последняя строка — без запятой (для соответствия оригиналу, если там тоже)
    # проверяем: в оригинале последняя строка имела запятую?
    last_had_comma = mapping_block.rstrip().endswith(",")
    if not last_had_comma and lines:
        lines[-1] = lines[-1].rstrip(",")

    new_block = "\n".join(lines) + "\n"
    new_content = content[:m.start(2)] + new_block + content[m.end(2):]
    return new_content, True


def main():
    root = find_project_root()
    f = root / "app" / "database.py"

    print("=" * 76)
    print("186: умный парсер маппинга в get_all_cameras")
    print("=" * 76)
    print()

    b = f.with_suffix(".py.bak-186")
    b.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    c = f.read_text(encoding="utf-8")

    if "PATCH-186" in c:
        print("  [OK] Уже применён")
        return

    new, ok = rewrite_mapping(c)
    if not ok:
        print("  [FAIL] блок маппинга не найден — откат")
        print("  Покажите реальный блок:")
        # печатаем то, что есть в get_all_cameras
        import re as _re
        m = _re.search(r"def get_all_cameras.*?(?=\n    def |\nclass |\Z)", c, _re.DOTALL)
        if m:
            print("  ---")
            for line in m.group(0).split("\n")[:40]:
                print("  |" + line)
            print("  ---")
        sys.exit(1)

    # помечаем применение
    new = new.replace(
        "def get_all_cameras(self):",
        "def get_all_cameras(self):  # PATCH-186 mapping rebuild"
    )

    try:
        compile(new, str(f), "exec")
    except SyntaxError as e:
        print(f"  [FAIL] синтаксис: {e} — откат")
        sys.exit(1)

    f.write_text(new, encoding="utf-8")
    print("  [OK] Маппинг перестроен под новую схему:")
    print("       id, name, login, pass, ipaddress, port, main_url, sub_url, sub2_url,")
    print("       enabled, comment, audio, location")
    print("  [OK] Сохранено")

    print()
    print("=" * 76)
    print("✅ database.py готов!")
    print()
    print("  Перезапустить сервер: python main.py")
    print("  Проверить потоки в мониторе")
    print()
    print("⚠️  Пока НЕ сохраняйте камеры из UI (форма ещё старая — до PATCH-187)")
    print("=" * 76)
    print()
    print("📦 ПОСЛЕ ПРОВЕРКИ потоков — коммит:")
    print()
    print(f"cd {root}")
    print("git add -A")
    print('git commit -m "refactor: camera RTSP URL split into parts (PATCH-184..186)" \\')
    print('  -m "DB: login/pass/ipaddress/port/main_url/sub_url/sub2_url + migration" \\')
    print('  -m "models.Camera: build_url() assembles rtsp on server, lstrip leading /" \\')
    print('  -m "database.py: line-based INSERT/SELECT + smart mapping rewrite" \\')
    print('  -m "stream_manager: uses build_url() to assemble full rtsp URL"')
    print("git push")
    print("=" * 76)


if __name__ == "__main__":
    main()