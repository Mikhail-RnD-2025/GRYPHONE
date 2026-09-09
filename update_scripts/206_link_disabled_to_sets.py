#!/usr/bin/env python3
"""
206. update_scripts/206_link_disabled_to_sets.py
----------------------------------------------------------------------------
  • SetRepository.add_cameras(): дописывает камеры в конец набора (position)
  • camera_import_service: после импорта все камеры, не состоящие ни в одном
    наборе (ВКЛЮЧАЯ отключённые), допривязываются к целевому набору
    (самому наполненному); в результат добавляются linked_to_set/target_set
  • database.py: автопривязка новых БД без фильтра enabled = 1
  • UI: тост импорта показывает количество допривязанных камер

ЗАПУСК: python update_scripts/206_link_disabled_to_sets.py
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


REPO_IMPORT = "from sqlalchemy import select, func  # PATCH-206\nfrom app.db import get_db"

REPO_METHOD = '''    def add_cameras(self, set_id: str, camera_ids: List[str]) -> int:
        """PATCH-206: дописать камеры в конец набора (пропуск существующих)."""
        from app.db.models import set_cameras
        added = 0
        with get_db() as session:
            existing = {
                r[0] for r in session.execute(
                    select(set_cameras.c.camera_id).where(set_cameras.c.set_id == set_id)
                )
            }
            max_pos = session.execute(
                select(func.coalesce(func.max(set_cameras.c.position), -1)).where(
                    set_cameras.c.set_id == set_id
                )
            ).scalar()
            pos = (max_pos if max_pos is not None else -1) + 1
            for cid in camera_ids:
                if not cid or cid in existing:
                    continue
                session.execute(
                    set_cameras.insert().values(set_id=set_id, camera_id=cid, position=pos)
                )
                pos += 1
                added += 1
        return added


'''

SERVICE_HELPER = '''    def _ensure_set_membership(self, camera_ids: List[str]):
        """PATCH-206: камеры, не состоящие ни в одном наборе (включая
        отключённые), допривязываются к целевому набору (самому наполненному).
        Возвращает (count, target_set_id)."""
        from app.db.repositories import set_repo
        sets = (set_repo.get_all() or {}).get("sets", {})
        if not sets:
            return 0, ""
        member = set()
        for s in sets.values():
            member.update(s.get("camera_ids", s.get("cameras", [])) or [])
        missing = [cid for cid in camera_ids if cid and cid not in member]
        if not missing:
            return 0, ""
        target = sorted(
            sets.keys(),
            key=lambda k: (-len(sets[k].get("camera_ids", sets[k].get("cameras", [])) or []), k)
        )[0]
        n = set_repo.add_cameras(target, missing)
        return n, target

'''

EXCEL_OLD = """            all_cams = list(current_cams.values())
            self.camera_service.save_cameras(all_cams)

            return {
                'success': True,
                'imported': len(all_cams),
                'updated': updated,
                'added': added,
                'skipped': skipped_rows,
                'errors': errors
            }"""

EXCEL_NEW = """            all_cams = list(current_cams.values())
            self.camera_service.save_cameras(all_cams)

            # PATCH-206: камеры вне наборов (включая отключённые) → в целевой набор
            linked, target = self._ensure_set_membership([c.get('id') for c in all_cams])

            return {
                'success': True,
                'imported': len(all_cams),
                'updated': updated,
                'added': added,
                'skipped': skipped_rows,
                'linked_to_set': linked,
                'target_set': target,
                'errors': errors
            }"""

JSON_OLD = """            self.camera_service.save_cameras(all_cams)

            return {
                'success': True,
                'imported': len(all_cams),
                'updated': updated,
                'added': added,
                'errors': errors
            }"""

JSON_NEW = """            self.camera_service.save_cameras(all_cams)

            # PATCH-206: камеры вне наборов (включая отключённые) → в целевой набор
            linked, target = self._ensure_set_membership([c.get('id') for c in all_cams])

            return {
                'success': True,
                'imported': len(all_cams),
                'updated': updated,
                'added': added,
                'linked_to_set': linked,
                'target_set': target,
                'errors': errors
            }"""

DB_OLD = '            cursor.execute("SELECT id FROM cameras WHERE enabled = 1")'
DB_NEW = '            cursor.execute("SELECT id FROM cameras")  # PATCH-206: включая отключённые'

UI_OLD = """            `✅ Импорт: всего ${result.imported} (обновлено ${result.updated || 0}, добавлено ${result.added || 0})`,"""
UI_NEW = """            `✅ Импорт: всего ${result.imported} (обновлено ${result.updated || 0}, добавлено ${result.added || 0})` +
            (result.linked_to_set ? ` | в набор ${result.target_set}: +${result.linked_to_set}` : ''),"""


def main():
    root = find_project_root()
    print("=" * 76)
    print("206: допривязка камер в наборы при импорте (включая отключённые)")
    print("=" * 76)
    print()
    n = 0

    # 1. repositories.py
    f = root / "app" / "db" / "repositories.py"
    b = f.with_suffix(".py.bak-206")
    b.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    c = f.read_text(encoding="utf-8")
    if "from sqlalchemy import select, func" not in c:
        c = c.replace("from app.db import get_db", REPO_IMPORT, 1); n += 1
        print("  [OK] repositories: import select, func")
    anchor = "# ============================================================================\n# Синглтоны для удобного импорта"
    if "def add_cameras" not in c and anchor in c:
        c = c.replace(anchor, REPO_METHOD + anchor, 1); n += 1
        print("  [OK] repositories: SetRepository.add_cameras()")
    try:
        compile(c, str(f), "exec"); f.write_text(c, encoding="utf-8")
    except SyntaxError as e:
        print(f"  [FAIL] repositories: {e} — откат"); f.write_text(b.read_text(encoding="utf-8")); sys.exit(1)

    # 2. camera_import_service.py
    f = root / "app" / "services" / "camera_import_service.py"
    b = f.with_suffix(".py.bak-206")
    b.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    c = f.read_text(encoding="utf-8")
    a = "    def export_to_json(self) -> List[Dict[str, Any]]:"
    if "_ensure_set_membership" not in c and a in c:
        c = c.replace(a, SERVICE_HELPER + a, 1); n += 1
        print("  [OK] service: _ensure_set_membership()")
    if EXCEL_OLD in c:
        c = c.replace(EXCEL_OLD, EXCEL_NEW, 1); n += 1
        print("  [OK] service: excel-импорт допривязывает в набор")
    if JSON_OLD in c:
        c = c.replace(JSON_OLD, JSON_NEW, 1); n += 1
        print("  [OK] service: json-импорт допривязывает в набор")
    try:
        compile(c, str(f), "exec"); f.write_text(c, encoding="utf-8")
    except SyntaxError as e:
        print(f"  [FAIL] service: {e} — откат"); f.write_text(b.read_text(encoding="utf-8")); sys.exit(1)

    # 3. database.py (автопривязка новых БД)
    f = root / "app" / "database.py"
    c = f.read_text(encoding="utf-8")
    if DB_OLD in c:
        c = c.replace(DB_OLD, DB_NEW, 1); n += 1
        f.write_text(c, encoding="utf-8")
        print("  [OK] database.py: автопривязка без фильтра enabled")

    # 4. UI toast
    f = root / "frontend" / "src" / "components" / "CamerasEditor.jsx"
    c = f.read_text(encoding="utf-8")
    if UI_OLD in c:
        c = c.replace(UI_OLD, UI_NEW, 1); n += 1
        f.write_text(c, encoding="utf-8")
        print("  [OK] UI: тост показывает допривязанные камеры")

    print(f"\n  [OK] замен: {n}/7")
    if n < 6:
        print("  [WARN] некоторые якоря не найдены — проверьте вывод выше")

    print()
    print("=" * 76)
    print("✅ Готово!")
    print()
    print("  cd frontend && npm run build")
    print("  python main.py")
    print()
    print("Мгновенная допривязка БЕЗ импорта (одноразово):")
    print('  python -c "from app.services.camera_import_service import camera_import_service as s; from app.services.camera_service import camera_service as cs; print(s._ensure_set_membership([c.id for c in cs.all_cameras()]))"')
    print("=" * 76)
    print()
    print("📦 Коммит:")
    print(f"cd {root}")
    print("git add -A")
    print('git commit -m "feat: import links unlinked cameras (incl. disabled) to sets (PATCH-206)" \\')
    print('  -m "SetRepository.add_cameras(): append with position ordering" \\')
    print('  -m "import excel/json: _ensure_set_membership after save" \\')
    print('  -m "fresh DB auto-link no longer filters enabled=1" \\')
    print('  -m "UI toast shows linked count + target set"')
    print("git push")
    print("=" * 76)


if __name__ == "__main__":
    main()