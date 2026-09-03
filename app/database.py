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
        """Create database tables if they don't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cameras (
                id TEXT PRIMARY KEY,
                name TEXT,
                main_url TEXT,
                sub_url TEXT,
                enabled INTEGER DEFAULT 1,
                comment TEXT,
                audio INTEGER DEFAULT 1,
                location TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sets (
                id TEXT PRIMARY KEY,
                name TEXT,
                grid_columns INTEGER DEFAULT 4,
                grid_rows INTEGER DEFAULT 3,
                is_default INTEGER DEFAULT 0
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS set_cameras (
                set_id TEXT,
                camera_id TEXT,
                PRIMARY KEY (set_id, camera_id),
                FOREIGN KEY (set_id) REFERENCES sets(id),
                FOREIGN KEY (camera_id) REFERENCES cameras(id)
            )
        """)

        conn.commit()
        conn.close()

    def _populate_from_json(self):
        """Populate database tables from JSON files in data/ folder."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Load cameras.json
        cameras_file = DATA_DIR / 'cameras.json'
        if cameras_file.exists():
            try:
                with open(cameras_file, 'r', encoding='utf-8') as f:
                    cameras_data = json.load(f)

                if isinstance(cameras_data, list):
                    for cam in cameras_data:
                        cursor.execute("""
                            INSERT OR REPLACE INTO cameras
                            (id, name, main_url, sub_url, enabled, comment, audio, location)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            cam.get('id', ''),
                            cam.get('name', ''),
                            cam.get('main_url', ''),
                            cam.get('sub_url', ''),
                            1 if cam.get('enabled', True) else 0,
                            cam.get('comment', ''),
                            1 if cam.get('audio', True) else 0,
                            cam.get('location', '')
                        ))
                    print(f"  ✔ Loaded {len(cameras_data)} cameras from data/cameras.json")
            except (json.JSONDecodeError, IOError) as e:
                print(f"  ⚠️  Error loading cameras.json: {e}")
        else:
            print(f"  ⚠️  cameras.json not found in data/")

        # Load sets.json
        sets_file = DATA_DIR / 'sets.json'
        if sets_file.exists():
            try:
                with open(sets_file, 'r', encoding='utf-8') as f:
                    sets_data = json.load(f)

                default_set = sets_data.get('default_set', '')
                sets_dict = sets_data.get('sets', {})

                for set_id, set_info in sets_dict.items():
                    is_default = 1 if set_id == default_set else 0
                    cursor.execute("""
                        INSERT OR REPLACE INTO sets
                        (id, name, grid_columns, grid_rows, is_default)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        set_id,
                        set_info.get('name', set_id),
                        set_info.get('grid_columns', 4),
                        set_info.get('grid_rows', 3),
                        is_default
                    ))

                    camera_ids = set_info.get('cameras', [])
                    for cam_id in camera_ids:
                        cursor.execute("""
                            INSERT OR REPLACE INTO set_cameras (set_id, camera_id)
                            VALUES (?, ?)
                        """, (set_id, cam_id))

                print(f"  ✔ Loaded {len(sets_dict)} sets from data/sets.json")
            except (json.JSONDecodeError, IOError) as e:
                print(f"  ⚠️  Error loading sets.json: {e}")
        else:
            print(f"  ⚠️  sets.json not found in data/")

        # Load config.json into settings table
        config_file = DATA_DIR / 'config.json'
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)

                for key, value in config_data.items():
                    cursor.execute("""
                        INSERT OR REPLACE INTO settings (key, value)
                        VALUES (?, ?)
                    """, (key, str(value) if not isinstance(value, str) else value))

                if config_data:
                    print(f"  ✔ Loaded {len(config_data)} config entries from data/config.json")
            except (json.JSONDecodeError, IOError) as e:
                print(f"  ⚠️  Error loading config.json: {e}")

        conn.commit()
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
            SELECT id, name, main_url, sub_url, enabled, comment, audio, location
            FROM cameras
        """)
        rows = cursor.fetchall()
        conn.close()

        cameras = []
        for row in rows:
            cameras.append({
                'id': row[0],
                'name': row[1],
                'main_url': row[2],
                'sub_url': row[3],
                'enabled': bool(row[4]),
                'comment': row[5],
                'audio': bool(row[6]),
                'location': row[7]
            })
        return cameras

    def get_all_sets(self):
        """Get all sets with their cameras."""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id, name, grid_columns, grid_rows, is_default FROM sets")
        sets_rows = cursor.fetchall()

        sets_data = {}
        default_set = None

        for row in sets_rows:
            set_id = row[0]
            sets_data[set_id] = {
                'name': row[1],
                'grid_columns': row[2],
                'grid_rows': row[3],
                'cameras': []
            }
            if row[4]:
                default_set = set_id

        for set_id in sets_data:
            cursor.execute("""
                SELECT camera_id FROM set_cameras WHERE set_id = ?
            """, (set_id,))
            camera_ids = [row[0] for row in cursor.fetchall()]
            sets_data[set_id]['cameras'] = camera_ids

        conn.close()

        return {
            'default_set': default_set or '',
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
                (id, name, main_url, sub_url, enabled, comment, audio, location)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                cam.get('id', ''),
                cam.get('name', ''),
                cam.get('main_url', ''),
                cam.get('sub_url', ''),
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
        default_set = sets_data.get('default_set', '')
        sets_dict = sets_data.get('sets', {})
        cursor.execute("DELETE FROM set_cameras")
        cursor.execute("DELETE FROM sets")
        for set_id, set_info in sets_dict.items():
            if not isinstance(set_info, dict):
                continue
            is_default = 1 if set_id == default_set else 0
            cursor.execute("""
                INSERT OR REPLACE INTO sets
                (id, name, grid_columns, grid_rows, is_default)
                VALUES (?, ?, ?, ?, ?)
            """, (
                set_id,
                set_info.get('name', set_id),
                set_info.get('max_columns', set_info.get('grid_columns', 4)),
                set_info.get('max_rows', set_info.get('grid_rows', 3)),
                is_default
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
