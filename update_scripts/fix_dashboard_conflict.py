# -*- coding: utf-8 -*-
"""
fix_dashboard_conflict.py
Удаляет дублирующий роут /api/dashboard из app/routes/api.py.

Улучшенная версия этого роута теперь живёт в app/routes/dashboard.py,
поэтому старую из api.py нужно убрать, иначе Flask падает с ошибкой:
  AssertionError: View function mapping is overwriting an existing endpoint
"""
from pathlib import Path

api_path = Path("app/routes/api.py")
if not api_path.exists():
    print("Файл не найден:", api_path.absolute())
    raise SystemExit(1)

lines = api_path.read_text(encoding="utf-8").split("\n")

# Ищем строку-декоратор с /api/dashboard
route_idx = None
for idx, line in enumerate(lines):
    if "/api/dashboard" in line and "dashboard_legacy" not in line:
        # Откатываемся к началу декоратора @app.route
        j = idx
        while j >= 0 and "@app.route" not in lines[j]:
            j -= 1
        route_idx = j if j >= 0 else idx
        break

if route_idx is None:
    print("Роут /api/dashboard в api.py не найден — удалять нечего.")
    raise SystemExit(0)

start = route_idx
# Подхватываем комментарии непосредственно над декоратором (до пустой строки)
hdr = start - 1
while hdr >= 0 and lines[hdr].strip() != "" and lines[hdr].strip().startswith("#"):
    start = hdr
    hdr -= 1

# Ищем строку def после декоратора
def_idx = start
while def_idx < len(lines) and not lines[def_idx].strip().startswith("def "):
    def_idx += 1

if def_idx >= len(lines):
    print("Не удалось найти тело функции — блок не удалён.")
    raise SystemExit(1)

def_line = lines[def_idx]
def_indent = len(def_line) - len(def_line.lstrip())

# Тело функции: строки с отступом больше, чем у def
end = def_idx + 1
while end < len(lines):
    line = lines[end]
    if line.strip() == "":
        end += 1
        continue
    cur_indent = len(line) - len(line.lstrip())
    if cur_indent > def_indent:
        end += 1
    else:
        break

new_lines = lines[:start] + lines[end:]
api_path.write_text("\n".join(new_lines), encoding="utf-8")
print(f"Удалён блок /api/dashboard из api.py (строки {start + 1}-{end}).")