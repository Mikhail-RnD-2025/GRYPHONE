#!/usr/bin/env python3
"""
227. update_scripts/227_file_logging.py
----------------------------------------------------------------------------
Файловое логирование + эндпоинт /api/logs:

  • app/__init__.py: RotatingFileHandler → logs/gryphone.log
    (5MB × 3 файла, utf-8, тот же formatter)
  • app/routes/api.py: GET /api/logs?limit=500&level=
    парсит файл, склеивает multiline-traceback, возвращает JSON
    под формат LogsPage.jsx: {logs: [{timestamp, level, message}]}

ЗАПУСК: python update_scripts/227_file_logging.py
"""

import sys
import subprocess
import time
import json as _json
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


LOGS_ENDPOINT = '''    # ========================================================================
    # PATCH-227: GET /api/logs — читает хвост logs/gryphone.log
    # Формат ответа под LogsPage.jsx: {logs: [{timestamp, level, message}]}
    # ========================================================================
    @app.route("/api/logs")
    def get_logs():
        from flask import request, jsonify
        import re as _re
        log_path = Path(__file__).resolve().parent.parent.parent / "logs" / "gryphone.log"
        limit = min(int(request.args.get("limit", 500)), 2000)
        level_filter = request.args.get("level", "").upper()

        if not log_path.exists():
            return jsonify({"logs": []})

        # Читаем последние ~200KB (экономим память на больших логах)
        try:
            with log_path.open("rb") as f:
                f.seek(0, 2)
                size = f.tell()
                f.seek(max(0, size - 200 * 1024))
                tail = f.read().decode("utf-8", errors="replace")
        except Exception:
            return jsonify({"logs": []})

        # Формат: 2026-09-11 12:04:28,596 [INFO] app.services.stream_manager: текст
        hdr = _re.compile(
            r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) \[(\w+)\] ([^:]+): (.*)$"
        )
        entries = []
        for raw_line in tail.splitlines():
            m = hdr.match(raw_line)
            if m:
                entries.append({
                    "timestamp": m.group(1),
                    "level": m.group(2),
                    "logger": m.group(3),
                    "message": m.group(4),
                })
            elif entries:
                # продолжение предыдущей записи (traceback и т.п.)
                entries[-1]["message"] += "\\n" + raw_line

        # Фильтр по уровню (если задан)
        if level_filter:
            entries = [e for e in entries if e["level"] == level_filter]

        # limit последних
        entries = entries[-limit:]

        # Формат под LogsPage: timestamp в ISO, level/message
        logs = []
        for e in entries:
            # Преобразуем "2026-09-11 12:04:28,596" → "2026-09-11T12:04:28.596"
            ts_iso = e["timestamp"].replace(" ", "T").replace(",", ".")
            logs.append({
                "timestamp": ts_iso,
                "level": e["level"],
                "message": f"[{e['logger']}] {e['message']}",
            })
        return jsonify({"logs": logs})

'''


def patch_init(root):
    print("--- app/__init__.py: RotatingFileHandler ---")
    f = root / "app" / "__init__.py"
    b = f.with_suffix(".py.bak-227")
    b.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    c = f.read_text(encoding="utf-8")

    if "PATCH-227" in c:
        print("  [OK] уже применён")
        return True

    # 1. Импорт RotatingFileHandler
    if "RotatingFileHandler" not in c:
        # вставляем после "import logging"
        if "import logging" in c:
            c = c.replace("import logging",
                          "import logging\nfrom logging.handlers import RotatingFileHandler  # PATCH-227",
                          1)
            print("  [OK] импорт RotatingFileHandler")
        else:
            print("  [FAIL] import logging не найден — откат")
            f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
            return False

    # 2. Добавляем FileHandler после basicConfig
    # Ищем блок logging.basicConfig(...)
    # Якорь: строка с форматом
    anchor = '        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",'
    if anchor not in c:
        print("  [FAIL] якорь формата не найден — откат")
        f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
        return False

    # Находим закрывающую скобку basicConfig и вставляем FileHandler
    lines = c.split("\n")
    for i, ln in enumerate(lines):
        if anchor in ln:
            # ищем следующую строку с ")"
            for j in range(i+1, min(i+10, len(lines))):
                if lines[j].strip() == ")":
                    insert_idx = j + 1
                    file_handler_block = '''

    # PATCH-227: файловый логгер с ротацией
    log_dir = project_root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    _fh = RotatingFileHandler(
        log_dir / "gryphone.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    _fh.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    logging.getLogger().addHandler(_fh)'''
                    lines.insert(insert_idx, file_handler_block)
                    c = "\n".join(lines)
                    print("  [OK] RotatingFileHandler подключён")
                    break
            break

    try:
        compile(c, str(f), "exec")
        f.write_text(c, encoding="utf-8")
        return True
    except SyntaxError as e:
        print(f"  [FAIL] синтаксис: {e} — откат")
        f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
        return False


def patch_api(root):
    print("--- app/routes/api.py: GET /api/logs ---")
    f = root / "app" / "routes" / "api.py"
    b = f.with_suffix(".py.bak-227")
    b.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    c = f.read_text(encoding="utf-8")

    if '"/api/logs"' in c:
        print("  [OK] эндпоинт уже есть")
        return True

    # Вставляем перед helper'ом _build_health_payload (он на уровне модуля)
    # или в конец файла
    lines = c.split("\n")
    insert_idx = len(lines)
    for i, ln in enumerate(lines):
        if ln.startswith("def _build_health_payload"):
            insert_idx = i
            break

    # Если _build_health_payload нет — ищем последний @app.route и вставляем после
    if insert_idx == len(lines):
        last_route = -1
        for i in range(len(lines)-1, -1, -1):
            if "@app.route" in lines[i] and lines[i].startswith("    "):
                last_route = i
                break
        if last_route >= 0:
            # Пропускаем всю функцию этого роута
            j = last_route + 1
            while j < len(lines):
                ln = lines[j]
                if ln.strip() == "":
                    j += 1
                    continue
                if ln.startswith("    ") or ln.startswith("        "):
                    j += 1
                    continue
                break
            insert_idx = j

    new_lines = lines[:insert_idx] + LOGS_ENDPOINT.split("\n") + lines[insert_idx:]
    c = "\n".join(new_lines)

    try:
        compile(c, str(f), "exec")
    except SyntaxError as e:
        print(f"  [FAIL] синтаксис: {e} — откат")
        f.write_text(b.read_text(encoding="utf-8"), encoding="utf-8")
        return False

    f.write_text(c, encoding="utf-8")
    print("  [OK] эндпоинт GET /api/logs добавлен")
    return True


def smoke_test(root):
    print("\n--- smoke-тест ---")
    proc = subprocess.Popen(
        [sys.executable, "main.py"],
        cwd=str(root),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        ready = False
        for _ in range(25):
            time.sleep(1)
            if proc.poll() is not None:
                print("  [FAIL] сервер упал")
                return False
            try:
                r = subprocess.run(
                    ["curl", "-s", "-o", "NUL", "-w", "%{http_code}",
                     "http://127.0.0.1:5000/api/logs"],
                    capture_output=True, text=True, timeout=3,
                )
                if r.stdout.strip() == "200":
                    ready = True
                    break
            except Exception:
                continue
        if not ready:
            print("  [FAIL] /api/logs не ответил 200")
            return False

        # Проверка файла
        log_file = root / "logs" / "gryphone.log"
        if not log_file.exists():
            print(f"  [FAIL] файл {log_file} не создан")
            return False

        # Читаем JSON
        r = subprocess.run(
            ["curl", "-s", "http://127.0.0.1:5000/api/logs?limit=5"],
            capture_output=True, text=True, timeout=5,
        )
        try:
            data = _json.loads(r.stdout)
            logs = data.get("logs", [])
            print(f"  [OK] файл создан: {log_file}")
            print(f"  [OK] /api/logs вернул {len(logs)} записей")
            if logs:
                e = logs[-1]
                print(f"       последняя: [{e['level']}] {e['message'][:80]}")
            return True
        except Exception as e:
            print(f"  [FAIL] некорректный JSON: {e}")
            print(f"         ответ: {r.stdout[:200]}")
            return False
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()


def main():
    root = find_project_root()
    print("=" * 76)
    print("227: файловый логгер + эндпоинт /api/logs")
    print("=" * 76)
    print()

    ok = True
    ok &= patch_init(root)
    ok &= patch_api(root)
    if not ok:
        sys.exit(1)

    ok &= smoke_test(root)
    if not ok:
        sys.exit(1)

    print()
    print("=" * 76)
    print("✅ PATCH-227 готов!")
    print()
    print(f"  cd {root} && python main.py")
    print()
    print("Откройте http://127.0.0.1:5000/logs:")
    print("  • Логи с таймстампами, уровнями, именами логгеров")
    print("  • Фильтры ERROR/WARNING/INFO/DEBUG работают")
    print("  • Автообновление каждые 5 сек")
    print("  • Ротация: 5MB × 3 файла (logs/gryphone.log)")
    print("=" * 76)
    print()
    print("📦 Коммит:")
    print(f"cd {root}")
    print("git add -A")
    print('git commit -m "feat(logs): file logging + /api/logs endpoint (PATCH-227)" \\')
    print('  -m "app/__init__.py: RotatingFileHandler -> logs/gryphone.log (5MB x 3)" \\')
    print('  -m "api.py: GET /api/logs parses file, merges multiline traceback" \\')
    print('  -m "response: {logs: [{timestamp, level, message}]} for LogsPage.jsx" \\')
    print('  -m "level filter via query param (ERROR/WARNING/INFO/DEBUG)"')
    print("git push")
    print("=" * 76)


if __name__ == "__main__":
    main()