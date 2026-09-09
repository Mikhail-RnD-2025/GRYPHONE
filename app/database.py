"""
GRYPHONE — database module
Provides SQLite connection and basic operations.
On first run, creates database and populates it from JSON files in data/.
"""
import json
import os
import sqlite3
from pathlib import Path

# Path configuration - use absolute paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / 'data'
DATABASE_DIR = BASE_DIR / 'database'
DATABASE_PATH = DATABASE_DIR / 'gryphone-vision.db'

# Allow override via environment variable
DB_PATH = os.environ.get("GRYPHONE_DB", str(DATABASE_PATH))


class Database:
    """Simple SQLite database wrapper with auto-initialization from JSON."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or DB_PATH

        # Ensure database directory exists
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

        # Check if database file already exists
        db_file_exists = Path(self.db_path).exists()

        # Create tables
        self._create_tables()

        # If database is new, populate from JSON
        if not db_file_exists:
            self._populate_from_json()

    def _create_tables(self):
        """Create database tables if they don't exist.
    
        Схема читается из database/sql/schema.sql и применяется через
        executescript(). Это делает schema.sql единственным источником
        истины для структуры БД.
        """
        schema_path = BASE_DIR / "database" / "sql" / "schema.sql"
        if not schema_path.is_file():
            raise FileNotFoundError(
                f"Файл схемы БД не найден: {schema_path}. "
                f"Запустите update_scripts/74_create_schema_sql.sh"
            )
        schema_sql = schema_path.read_text(encoding="utf-8")
        conn = sqlite3.connect(self.db_path)
        try:
            # Включаем внешние ключи (в SQLite по умолчанию выключены).
            # PRAGMA должна быть выполнена на каждом соединении отдельно.
            conn.execute("PRAGMA foreign_keys = ON")
            # Применяем всю схему одним скриптом (поддерживает несколько
            # CREATE TABLE, PRAGMA, индексы и комментарии).
            conn.executescript(schema_sql)

            # PATCH-161: миграция существующих БД — добавляем aspect_ratio
            # (идемпотентно: CREATE TABLE IF NOT EXISTS не меняет старые БД)
            mig_cursor = conn.cursor()
            mig_cursor.execute("PRAGMA table_info(sets)")
            _cols = [r[1] for r in mig_cursor.fetchall()]
            if "aspect_ratio" not in _cols:
                mig_cursor.execute(
                    "ALTER TABLE sets ADD COLUMN aspect_ratio TEXT DEFAULT '16:9'"
                )
                conn.commit()
                print("[PATCH-161] Миграция: sets + aspect_ratio")
            conn.commit()
        finally:
            conn.close()
    
    def _populate_from_json(self):
        """Populate database tables from JSON files in data/ folder.
        
        Исправлено (PATCH-77): привязывает только существующие камеры.
        Если привязок нет — автоматически привязывает все включённые камеры
        к набору по умолчанию.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Load cameras.json
        cameras_file = DATA_DIR / "cameras.json"
        if cameras_file.exists():
            try:
                with open(cameras_file, "r", encoding="utf-8") as f:
                    cameras_data = json.load(f)
                if isinstance(cameras_data, list):
                    for cam in cameras_data:
                        cursor.execute("""
                            INSERT OR REPLACE INTO cameras
                            (id, name, login, pass, ipaddress, port, main_url, sub_url, sub2_url, enabled, comment, audio, location)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            cam.get("id", ""),
                            cam.get("name", ""),
                            cam.get("login", ""),
                            cam.get("pass", ""),
                            cam.get("ipaddress", ""),
                            cam.get("port", "554"),
                            str(cam.get("main_url", "")).lstrip("/"),  # PATCH-187
                            str(cam.get("sub_url", "")).lstrip("/"),
                            str(cam.get("sub2_url", "")).lstrip("/"),
                            1 if cam.get("enabled", True) else 0,
                            cam.get("comment", ""),
                            1 if cam.get("audio", True) else 0,
                            cam.get("location", "")
                        ))
                    print(f" ✔ Loaded {len(cameras_data)} cameras from data/cameras.json")
            except (json.JSONDecodeError, IOError) as e:
                print(f" ⚠️ Error loading cameras.json: {e}")
        else:
            print(f" ⚠️ cameras.json not found in data/")
        
        # Load sets.json
        sets_file = DATA_DIR / "sets.json"
        if sets_file.exists():
            try:
                with open(sets_file, "r", encoding="utf-8") as f:
                    sets_data = json.load(f)
                sets_dict = sets_data.get("sets", {})
                for set_id, set_info in sets_dict.items():
                    cursor.execute("""
                        INSERT OR REPLACE INTO sets
                        (id, name, grid_columns, grid_rows, aspect_ratio)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        set_id,
                        set_info.get("name", set_id),
                        set_info.get("max_columns", set_info.get("grid_columns", 4)),
                        set_info.get("max_rows", set_info.get("grid_rows", 3)),
                        set_info.get("aspect_ratio", "16:9")
                    ))
                    # PATCH-77: привязываем только существующие камеры
                    camera_ids = set_info.get("cameras", [])
                    for cam_id in camera_ids:
                        # Проверяем, существует ли камера в БД
                        cursor.execute("SELECT id FROM cameras WHERE id = ?", (cam_id,))
                        if cursor.fetchone():
                            cursor.execute("""
                                INSERT OR REPLACE INTO set_cameras (set_id, camera_id)
                                VALUES (?, ?)
                            """, (set_id, cam_id))
                print(f" ✔ Loaded {len(sets_dict)} sets from data/sets.json")
            except (json.JSONDecodeError, IOError) as e:
                print(f" ⚠️ Error loading sets.json: {e}")
        else:
            print(f" ⚠️ sets.json not found in data/")
        
        conn.commit()
        
        # PATCH-77: Автоматическая привязка, если привязок нет
        cursor.execute("SELECT COUNT(*) FROM set_cameras")
        bindings_count = cursor.fetchone()[0]
        if bindings_count == 0:
            print(" ⚠️ Привязок камер к наборам нет — создаю автоматически")
            # Находим набор по умолчанию
            # PATCH-182: набора по умолчанию нет — берём первый
            cursor.execute("SELECT id FROM sets LIMIT 1")
            default_set_row = cursor.fetchone()
            if default_set_row:
                default_set_id = default_set_row[0]
                # Получаем все включённые камеры
                cursor.execute("SELECT id FROM cameras")  # PATCH-206: включая отключённые
                enabled_cameras = cursor.fetchall()
                for cam_row in enabled_cameras:
                    cam_id = cam_row[0]
                    cursor.execute("""
                        INSERT OR IGNORE INTO set_cameras (set_id, camera_id)
                        VALUES (?, ?)
                    """, (default_set_id, cam_id))
                conn.commit()
                print(f" ✔ Привязано {len(enabled_cameras)} камер к набору {default_set_id}")
            else:
                print(" ⚠️ Нет наборов для автоматической привязки")
        
        conn.close()
    def get_connection(self):
        """Get a new database connection."""
        return sqlite3.connect(self.db_path)

    def get_setting(self, key: str, default: str = None) -> str:
        """Get a setting value by key."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else default

    def set_setting(self, key: str, value: str):
        """Set a setting value."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, value)
        )
        conn.commit()
        conn.close()

    def get(self, key: str, default=None):
        """Get a JSON-serialized value by key (for ConfigManager compatibility)."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        result = cursor.fetchone()
        conn.close()
        if result:
            import json
            try:
                return json.loads(result[0])
            except (json.JSONDecodeError, TypeError):
                return result[0]
        return default

    def save(self, key: str, value):
        """Алиас для set() — для совместимости с ConfigManager."""
        return self.set(key, value)
    def set(self, key: str, value):
        """Set a JSON-serialized value by key (for ConfigManager compatibility)."""
        import json
        conn = self.get_connection()
        cursor = conn.cursor()
        json_value = json.dumps(value, ensure_ascii=False)
        cursor.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, json_value)
        )
        conn.commit()
        conn.close()

    def get_all_cameras(self):
        """Get all cameras from database."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, login, pass, ipaddress, port, main_url, sub_url, sub2_url, enabled, comment, audio, location
            FROM cameras
        """)
        rows = cursor.fetchall()
        conn.close()

        cameras = []
        for row in rows:
            cameras.append({
                'id': row[0],
                'name': row[1],
                'login': row[2],
                'pass': row[3],
                'ipaddress': row[4],
                'port': row[5],
                'main_url': row[6],
                'sub_url': row[7],
                'sub2_url': row[8],
                'enabled': bool(row[9]),
                'comment': row[10],
                'audio': bool(row[11]),
                'location': row[12]
            })
        return cameras

    def get_all_sets(self):
        """Get all sets with their cameras."""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id, name, grid_columns, grid_rows, aspect_ratio FROM sets")  # PATCH-182
        sets_rows = cursor.fetchall()

        sets_data = {}

        for row in sets_rows:
            set_id = row[0]
            sets_data[set_id] = {
                'name': row[1],
                'grid_columns': row[2],
                'grid_rows': row[3],
                'aspect_ratio': (row[4] or '16:9') if len(row) > 4 else '16:9',  # PATCH-182
                'cameras': []
            }

        for set_id in sets_data:
            cursor.execute("""
                SELECT camera_id FROM set_cameras WHERE set_id = ?
            """, (set_id,))
            camera_ids = [row[0] for row in cursor.fetchall()]
            sets_data[set_id]['cameras'] = camera_ids

        conn.close()

        return {
            'sets': sets_data
        }



    def save_cameras_list(self, cameras):
        """Сохранить список камер в таблицу cameras (полная замена)."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cameras")
        for cam in cameras:
            cursor.execute("""
                INSERT OR REPLACE INTO cameras
                (id, name, login, pass, ipaddress, port, main_url, sub_url, sub2_url, enabled, comment, audio, location)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                cam.get('id', ''),
                cam.get('name', ''),
                cam.get('login', ''),
                cam.get('pass', ''),
                cam.get('ipaddress', ''),
                cam.get('port', '554'),
                str(cam.get('main_url', '')).lstrip('/'),  # PATCH-187
                str(cam.get('sub_url', '')).lstrip('/'),
                str(cam.get('sub2_url', '')).lstrip('/'),
                1 if cam.get('enabled', True) else 0,
                cam.get('comment', ''),
                1 if cam.get('audio', True) else 0,
                cam.get('location', '')
            ))
        conn.commit()
        conn.close()

    def save_sets_data(self, sets_data):
        """Сохранить наборы в таблицы sets и set_cameras (полная замена)."""
        conn = self.get_connection()
        cursor = conn.cursor()
        sets_dict = sets_data.get('sets', {})
        cursor.execute("DELETE FROM set_cameras")
        cursor.execute("DELETE FROM sets")
        for set_id, set_info in sets_dict.items():
            if not isinstance(set_info, dict):
                continue
            cursor.execute("""
                INSERT OR REPLACE INTO sets
                (id, name, grid_columns, grid_rows, aspect_ratio)
                VALUES (?, ?, ?, ?, ?)
            """, (
                set_id,
                set_info.get('name', set_id),
                set_info.get('max_columns', set_info.get('grid_columns', 4)),
                set_info.get('max_rows', set_info.get('grid_rows', 3)),
                set_info.get('aspect_ratio', '16:9')
            ))
            camera_ids = set_info.get('camera_ids', set_info.get('cameras', []))
            for cam_id in camera_ids:
                cursor.execute("""
                    INSERT OR REPLACE INTO set_cameras (set_id, camera_id)
                    VALUES (?, ?)
                """, (set_id, cam_id))
        conn.commit()
        conn.close()

# Global database instance
db = Database()
