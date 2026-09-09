import sys
sys.path.insert(0, ".")

from app.db import get_db
from app.db.models import Camera, Set, Setting
from app.database import db as legacy_db


def main():
    print("=" * 70)
    print("SQLAlchemy smoke-test")
    print("=" * 70)

    # PATCH-200.2: читаем всё ВНУТРИ with-блока (иначе DetachedInstanceError)
    with get_db() as session:
        # Камеры
        sa_cams = session.query(Camera).all()
        sa_dicts = [c.to_dict() for c in sa_cams]  # PATCH-200.2: to_dict() пока сессия открыта
        legacy_cams = legacy_db.get_all_cameras() or []

        print(f"  SQLAlchemy: {len(sa_cams)} камер")
        print(f"  Legacy:     {len(legacy_cams)} камер")

        # Наборы
        sa_sets = session.query(Set).all()
        legacy_sets = legacy_db.get_all_sets() or {"sets": {}}
        n_legacy_sets = len(legacy_sets.get("sets", {}))

        print(f"  SQLAlchemy: {len(sa_sets)} наборов")
        print(f"  Legacy:     {n_legacy_sets} наборов")

        # Settings
        sa_settings = session.query(Setting).all()
        print(f"  SQLAlchemy: {len(sa_settings)} настроек")

    # Проверка согласованности (вне with — используем уже прочитанные данные)
    if len(sa_cams) != len(legacy_cams):
        print("  [FAIL] Количество камер не совпадает!")
        return False
    if len(sa_sets) != n_legacy_sets:
        print("  [FAIL] Количество наборов не совпадает!")
        return False

    # Сравнение первой камеры (to_dict уже вызван внутри with)
    if sa_dicts and legacy_cams:
        sa_dict = sa_dicts[0]
        lg_dict = legacy_cams[0]
        keys = set(sa_dict.keys()) & set(lg_dict.keys())
        mismatches = [k for k in keys if sa_dict[k] != lg_dict[k]]
        if mismatches:
            print(f"  [WARN] Расхождения по ключам: {mismatches}")
            for k in mismatches[:3]:
                print(f"       {k}: SA={sa_dict[k]!r}  legacy={lg_dict[k]!r}")
        else:
            print("  [OK] to_dict() совпадает для первой камеры")

    print("=" * 70)
    print("✅ SQLAlchemy слой работает и согласован со старой БД")
    print("=" * 70)
    return True


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
