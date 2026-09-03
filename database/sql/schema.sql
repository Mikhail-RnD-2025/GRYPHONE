-- ============================================================================
-- GRYPHONE — схема базы данных (SQLite)
-- ----------------------------------------------------------------------------
-- Этот файл содержит DDL-команды для создания структуры базы данных.
-- Автоматически создаётся и поддерживается в актуальном состоянии.
--
-- ПРИМЕНЕНИЕ:
--   sqlite3 database/gryphone-vision.db < database/sql/schema.sql
--
-- СИНХРОНИЗАЦИЯ С КОДОМ:
--   app/database.py — класс Database._create_tables() должен создавать
--   те же таблицы. Если вы меняете схему здесь, обновите и _create_tables().
--
-- ИСТОРИЯ:
--   Создано: 2026-09-03
--   Последнее обновление: см. историю коммитов
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Включаем поддержку внешних ключей (по умолчанию в SQLite выключена!)
-- Без этой строки FOREIGN KEY в таблицах не будет работать.
-- ----------------------------------------------------------------------------
PRAGMA foreign_keys = ON;

-- ----------------------------------------------------------------------------
-- Таблица: settings
-- Назначение: Key/value хранилище для конфигурации и настроек.
-- Используется ConfigManager для хранения конфига под ключом 'config'.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS settings (
    -- Уникальный строковый ключ (например: 'config', 'cameras', 'sets')
    key TEXT PRIMARY KEY,
    -- Значение в формате JSON-строки или простого текста
    value TEXT
);

CREATE INDEX IF NOT EXISTS idx_settings_key ON settings(key);

-- ----------------------------------------------------------------------------
-- Таблица: cameras
-- Назначение: Список камер наблюдения с их параметрами.
-- Каждая камера может иметь основной поток (main_url) и субпоток (sub_url).
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cameras (
    -- Уникальный идентификатор камеры (обычно из Excel или импорта)
    id TEXT PRIMARY KEY,
    -- Человекочитаемое имя камеры
    name TEXT,
    -- RTSP URL основного потока (обязательный)
    main_url TEXT,
    -- RTSP URL субпотока (опциональный, для снижения нагрузки)
    sub_url TEXT,
    -- Включена ли камера (0=выключена, 1=включена)
    enabled INTEGER DEFAULT 1,
    -- Комментарий/описание камеры (например, расположение)
    comment TEXT,
    -- Включать ли аудио при захвате (0=нет, 1=да)
    audio INTEGER DEFAULT 1,
    -- Местоположение камеры (физическое: этаж, корпус, комната)
    location TEXT
);

CREATE INDEX IF NOT EXISTS idx_cameras_enabled ON cameras(enabled);
CREATE INDEX IF NOT EXISTS idx_cameras_name ON cameras(name);

-- ----------------------------------------------------------------------------
-- Таблица: sets
-- Назначение: Наборы камер (сетки просмотра) для организации камер в группы.
-- Пользователь может переключаться между наборами в интерфейсе.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sets (
    -- Уникальный идентификатор набора
    id TEXT PRIMARY KEY,
    -- Человекочитаемое имя набора (например: "Главный офис", "Склад")
    name TEXT,
    -- Количество колонок в сетке просмотра
    grid_columns INTEGER DEFAULT 4,
    -- Количество строк в сетке просмотра
    grid_rows INTEGER DEFAULT 3,
    -- Является ли набором по умолчанию при старте (0=нет, 1=да)
    is_default INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_sets_is_default ON sets(is_default);

-- ----------------------------------------------------------------------------
-- Таблица: set_cameras
-- Назначение: Связь many-to-many между наборами (sets) и камерами (cameras).
-- Определяет, какие камеры входят в какой набор, и в каком порядке.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS set_cameras (
    -- Ссылка на набор (sets.id)
    set_id TEXT,
    -- Ссылка на камеру (cameras.id)
    camera_id TEXT,
    -- Составной первичный ключ: камера может быть в наборе только один раз
    PRIMARY KEY (set_id, camera_id),
    -- Внешний ключ на таблицу sets (каскадное удаление)
    FOREIGN KEY (set_id) REFERENCES sets(id) ON DELETE CASCADE,
    -- Внешний ключ на таблицу cameras (каскадное удаление)
    FOREIGN KEY (camera_id) REFERENCES cameras(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_set_cameras_set_id ON set_cameras(set_id);
CREATE INDEX IF NOT EXISTS idx_set_cameras_camera_id ON set_cameras(camera_id);

-- ----------------------------------------------------------------------------
-- Таблица: events
-- Назначение: Системные события (заготовка для аналитики и интеграции с PSIM).
-- Хранит события от камер, воркеров и системы: потери связи, ошибки, детекции.
--
-- ЗАРЕЗЕРВИРОВАНО: В текущей версии таблица создаётся, но запись в неё
-- пока не реализована в бэкенде. Планируется использовать для:
--   - Аудита действий пользователей
--   - Логирования ошибок и потерь связи
--   - Передачи событий в PSIM через интеграционный модуль
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS events (
    -- Уникальный идентификатор события (автоинкремент)
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    -- Временная метка события (Unix timestamp в секундах)
    ts REAL NOT NULL,
    -- Источник события (например: 'camera', 'worker', 'system', 'user')
    source TEXT NOT NULL,
    -- ID камеры, к которой относится событие (может быть NULL)
    camera_id TEXT,
    -- ID узла кластера, на котором произошло событие (для многонузловости)
    node_id TEXT,
    -- Тип события (например: 'stream_lost', 'stream_restored', 'error',
    -- 'motion_detected', 'camera_added', 'camera_removed', 'config_changed')
    event_type TEXT NOT NULL,
    -- Уровень серьёжности: 'debug', 'info', 'warning', 'error', 'critical'
    severity TEXT NOT NULL DEFAULT 'info',
    -- Дополнительные данные события в формате JSON
    payload TEXT,
    -- Подтверждено ли событие оператором (0=нет, 1=да)
    acknowledged INTEGER DEFAULT 0,
    -- Отправлено ли событие в PSIM (0=нет, 1=да, 2=ошибка отправки)
    sent_to_psim INTEGER DEFAULT 0,
    -- Внешний ключ на камеру (если указана camera_id)
    FOREIGN KEY (camera_id) REFERENCES cameras(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts);
CREATE INDEX IF NOT EXISTS idx_events_source ON events(source);
CREATE INDEX IF NOT EXISTS idx_events_camera_id ON events(camera_id);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_severity ON events(severity);
CREATE INDEX IF NOT EXISTS idx_events_acknowledged ON events(acknowledged);

-- ----------------------------------------------------------------------------
-- Начальные данные (опционально)
-- ----------------------------------------------------------------------------
-- Можно раскомментировать, если нужны стартовые значения:

-- Установить набор по умолчанию
-- INSERT OR IGNORE INTO sets (id, name, grid_columns, grid_rows, is_default)
-- VALUES ('default', 'По умолчанию', 4, 3, 1);

-- ----------------------------------------------------------------------------
-- Конец схемы
-- ----------------------------------------------------------------------------
