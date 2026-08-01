# GPYPHONE - React UI Migration Guide

## ✅ Выполненные изменения

### 1. Название проекта
- Изменено с "RTSP Viewer" на **GPYPHONE**
- Обновлены все HTML шаблоны, заголовки и конфигурации

### 2. React как основной UI фреймворк

#### Бэкенд (Quart)
- Добавлен `quart-cors` для CORS поддержки
- Новые маршруты для раздачи React статики:
  - `/react-app` - основная страница приложения
  - `/react-app/assets/*` - JS/CSS файлы
  - `/react-app/<path>` - SPA роутинг
- API endpoints остались без изменений:
  - `/api/data` - данные камер и наборов
  - `/api/stream_status` - SSE статус потоков
  - `/api/toggle_camera` - вкл/выкл камеры
  - `/api/camera_comment` - сохранение комментариев
  - `/hls/camera/*` - HLS потоки

#### Фронтенд (React + Vite + TypeScript)
- **Стек**: React 19, TypeScript, Vite, HLS.js, Axios
- **Структура сетки камер**:
  - Динамическое изменение количества колонок из настроек набора
  - Поддержка ограничения по строкам (max_rows)
  - Фильтрация камер по текущему набору (camera_ids)
  - Отображение скрытых камер
- **Компоненты**:
  - `App.tsx` - главный компонент с логикой сетки
  - `StreamCard.tsx` - карточка камеры с видео и контекстным меню
- **Конфигурация Vite**:
  - Base path: `/react-app/`
  - Code splitting: vendor, hls, http чанки
  - Proxy для разработки

### 3. Доступ к приложению
- **Основной URL**: `http://localhost:5000/react-app`
- **Альтернативный**: `http://localhost:5000/react`
- Старый UI через Jinja2 доступен на `/` (для обратной совместимости)

## 📦 Сборка фронтенда

```bash
cd frontend
npm install
npm run build
```

Собранные файлы появляются в `frontend/dist/`

## 🚀 Запуск сервера

```bash
python main.py
```

Сервер запускается на `http://0.0.0.0:5000`

## 🎯 Ключевые функции React UI

1. **Динамическая сетка камер**
   - Настройка колонок через `max_columns` в наборе
   - Ограничение строк через `max_rows`
   - Автоматический ресайз grid

2. **Real-time мониторинг**
   - SSE подключение к `/api/stream_status`
   - Индикаторы статуса (ok/err/checking)
   - Метрики потока (FPS, bitrate, time)

3. **Управление камерами**
   - Вкл/выкл через контекстное меню (ПКМ)
   - Редактирование комментариев
   - Просмотр URL потоков

4. **Наборы камер**
   - Переключение между наборами
   - Сохранение конфигурации в БД

## 📁 Структура файлов

```
/workspace
├── main.py              # Точка входа Quart
├── routes.py            # API и статика React
├── frontend/
│   ├── src/
│   │   ├── App.tsx      # Главный компонент
│   │   ├── components/
│   │   │   └── StreamCard.tsx
│   │   └── App.css
│   ├── dist/            # Собранный билд
│   ├── package.json
│   └── vite.config.ts
└── ...
```

## 🔧 Конфигурация сетки

Пример набора в БД:
```json
{
  "name": "🏢 403",
  "max_columns": 6,
  "max_rows": 5,
  "camera_ids": ["403-P-GAVw-001", "..."],
  "aspect_ratio": "16:9"
}
```

Это создаст сетку 6x5 (максимум 30 камер).

## ⚠️ Важные замечания

1. Старый UI (Jinja2) сохраняется для обратной совместимости
2. API endpoints не изменились
3. Для production рекомендуется настроить reverse proxy (nginx)
4. FFmpeg должен быть установлен в системе (`/usr/bin/ffprobe`)
