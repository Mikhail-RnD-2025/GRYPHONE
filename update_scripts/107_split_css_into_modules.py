#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
107_split_css_into_modules.py

Разделяет styles.css на логические модули для лучшей управляемости.
Создаёт папку frontend/src/styles/ с модулями и новый главный styles.css с @import.

ЗАПУСК: python update_scripts/107_split_css_into_modules.py
"""

import sys
from pathlib import Path


def main():
    project_root = Path.cwd()
    css_file = project_root / "frontend/src/styles.css"
    styles_dir = project_root / "frontend/src/styles"
    backup = project_root / "frontend/src/styles.css.bak-107"

    print("=" * 76)
    print("107: Разделение styles.css на модули")
    print(f"Корень проекта: {project_root}")
    print("=" * 76)
    print()

    # ШАГ 1: Резервная копия
    print("--- ШАГ 1: Резервная копия ---")
    if css_file.exists():
        backup.write_text(css_file.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"  [BAK] {backup.name}")
        original_size = css_file.stat().st_size
        print(f"  Оригинальный размер: {original_size} байт")
    else:
        print("  [ERROR] Файл styles.css не найден")
        sys.exit(1)
    print()

    # ШАГ 2: Создание папки для модулей
    print("--- ШАГ 2: Создание структуры модулей ---")
    styles_dir.mkdir(exist_ok=True)
    print(f"  [OK] Создана папка: {styles_dir}")
    print()

    # ШАГ 3: Создание модулей
    print("--- ШАГ 3: Создание модулей ---")

    modules = {}

    # 1. base.css - базовые стили
    modules['base.css'] = """/* ============================================================
   Базовые стили (reset, body, html)
   ============================================================ */

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body, #root {
  height: 100%;
  overflow: hidden;
}

body {
  font-family: system-ui, -apple-system, sans-serif;
  background: #0b0d10;
  color: #e0e3e8;
}
"""

    # 2. layout.css - страница и контейнеры
    modules['layout.css'] = """/* ============================================================
   Страница и контейнеры
   ============================================================ */

.page {
  padding: 12px;
  max-width: none;
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.page-title {
  font-size: 1.5rem;
  margin-bottom: 12px;
  flex-shrink: 0;
}

.page.monitor-page,
.monitor-page {
  padding-top: 0 !important;
}

.page.monitor-page {
  padding: 0 !important;
  height: 100vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.page:not(.monitor-page) {
  padding-top: 12px;
}

/* Сетка камер */
.fullscreen-grid {
  flex: 1;
  min-height: 0;
  width: 100%;
  height: 100%;
  display: grid;
  gap: 2px;
  background: #0b0d10;
}

.camera-grid-fullspace {
  height: calc(100vh - 16px);
}

/* Секции */
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  margin-bottom: 12px;
  border-bottom: 1px solid #1e293b;
  flex-shrink: 0;
}

.section-header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.section-icon {
  font-size: 1.5rem;
  line-height: 1;
}

.section-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: #e0e3e8;
  margin: 0;
}

.section-desc {
  font-size: 0.875rem;
  color: #94a3b8;
  margin: 4px 0 0 0;
}

/* Вкладки */
.tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  flex-wrap: wrap;
  flex-shrink: 0;
}

.tab-content {
  background: #0b0d10;
  border-radius: 8px;
  padding: 16px;
  border: 1px solid #1e293b;
  overflow-y: auto;
  flex: 1;
  min-height: 0;
}

.empty-state {
  padding: 12px;
  border: 1px dashed #999;
  color: #666;
  border-radius: 8px;
}
"""

    # 3. header.css - шапка
    modules['header.css'] = """/* ============================================================
   Шапка приложения
   ============================================================ */

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  height: 56px;
  position: relative;
  background: linear-gradient(
    to bottom,
    rgba(11, 13, 16, 0.95) 0%,
    rgba(11, 13, 16, 0.85) 70%,
    rgba(11, 13, 16, 0.4) 100%
  );
  backdrop-filter: blur(8px);
  transition: transform 0.3s ease, opacity 0.3s ease;
  transform: translateY(0);
  opacity: 1;
}

.page.monitor-page .header,
.monitor-page .header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
}

.page:not(.monitor-page) .header {
  position: relative;
  background: rgba(11, 13, 16, 0.98);
}

.header.header-hidden {
  transform: translateY(-100%);
  opacity: 0;
  pointer-events: none;
}

.header-trigger {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 20px;
  z-index: 999;
  background: transparent;
  pointer-events: auto;
}

.header-left {
  flex: 1;
  display: flex;
  align-items: center;
  min-width: 0;
}

.header-title {
  font-size: 1.25rem;
  color: #2563eb;
  margin: 0;
  white-space: nowrap;
}

.header-center {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  pointer-events: none;
}

.header-clock {
  font-size: 1rem;
  font-weight: 500;
  color: #e0e3e8;
  font-family: monospace;
}

.header-right {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  min-width: 0;
}

.header-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 6px 10px;
  background: #334155;
  color: #e0e3e8;
  border-radius: 6px;
  text-decoration: none;
  font-size: 0.875rem;
  transition: background 0.2s ease;
  white-space: nowrap;
}

.header-btn:hover {
  background: #475569;
}
"""

    # 4. camera.css - карточки камер
    modules['camera.css'] = """/* ============================================================
   Карточки камер (видеостена)
   ============================================================ */

.camera-card {
  position: relative;
  overflow: hidden;
  background: #000;
  border: none;
  border-radius: 0;
  padding: 0;
  display: flex;
  min-height: 0;
  height: 100%;
}

.fullscreen-grid .camera-card {
  position: relative;
  overflow: hidden;
  background: #000;
  height: 100%;
  width: 100%;
}

.camera-video {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: contain;
  background: #000;
  z-index: 1;
}

.fullscreen-grid .camera-card video,
.fullscreen-grid .camera-video {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: contain;
  background: #000;
}

.camera-card-header {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  z-index: 2;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 6px;
  padding: 3px 6px;
  background: linear-gradient(
    to bottom,
    rgba(0, 0, 0, 0.65) 0%,
    rgba(0, 0, 0, 0.25) 70%,
    transparent 100%
  );
  pointer-events: none;
}

.camera-name {
  font-size: 0.7rem;
  font-weight: 500;
  color: #fff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
  min-width: 0;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.8);
}

.status-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
  box-shadow: 0 0 3px rgba(0, 0, 0, 0.5);
}

.status-dot.online {
  background: #059669;
  box-shadow: 0 0 6px #059669;
}

.status-dot.offline {
  background: #dc2626;
  box-shadow: 0 0 6px #dc2626;
}

.status-dot.connecting {
  background: #d97706;
  box-shadow: 0 0 6px #d97706;
  animation: pulse-dot 1.5s ease-in-out infinite;
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.35; }
}

.camera-audio-badge {
  position: absolute;
  bottom: 4px;
  right: 4px;
  z-index: 2;
  background: rgba(0, 0, 0, 0.55);
  border-radius: 4px;
  padding: 1px 5px;
  font-size: 0.7rem;
  pointer-events: none;
}

.camera-stream-badge {
  position: absolute;
  bottom: 4px;
  left: 4px;
  z-index: 2;
  background: rgba(0, 0, 0, 0.55);
  border-radius: 4px;
  padding: 1px 5px;
  font-size: 0.65rem;
  color: #94a3b8;
  pointer-events: none;
}

.camera-overlay-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 2;
  color: #94a3b8;
  font-size: 0.8rem;
  text-align: center;
  pointer-events: none;
  white-space: nowrap;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.9);
}

.camera-empty {
  position: relative;
  background: linear-gradient(135deg, #0f1116 0%, #13151c 100%);
  border: 1px dashed #24272f;
  border-radius: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  min-height: 0;
  height: 100%;
}

.fullscreen-grid .camera-empty {
  height: 100%;
  width: 100%;
}

.camera-empty::before {
  content: '';
  width: 26px;
  height: 26px;
  border-radius: 50%;
  border: 1.5px solid #2e313a;
  background: radial-gradient(circle, #2e313a 0%, #2e313a 22%, transparent 23%);
  opacity: 0.8;
}

.status-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.75rem;
  white-space: nowrap;
}

.status-online { background: #059669; color: #fff; }
.status-offline { background: #dc2626; color: #fff; }
.status-connecting { background: #d97706; color: #fff; }
"""

    # 5. components.css - кнопки, тосты, контекстное меню
    modules['components.css'] = """/* ============================================================
   Компоненты: кнопки, тосты, контекстное меню
   ============================================================ */

.btn {
  padding: 8px 16px;
  border-radius: 6px;
  border: none;
  cursor: pointer;
  font-size: 0.875rem;
  background: #334155;
  color: #e0e3e8;
  text-decoration: none;
  display: inline-block;
}

.btn:hover { background: #475569; }

.btn-primary { background: #2563eb; color: #fff; }
.btn-primary:hover { background: #1d4ed8; }

.btn-danger { background: #dc2626; color: #fff; }
.btn-danger:hover { background: #b91c1c; }

.toast-container {
  position: fixed;
  top: 16px;
  right: 16px;
  z-index: 10000;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.toast {
  padding: 12px 16px;
  border-radius: 6px;
  color: #fff;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.toast-success { background: #059669; }
.toast-error { background: #dc2626; }
.toast-info { background: #2563eb; }

.context-menu {
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 8px;
  padding: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
  min-width: 220px;
}

.context-menu .btn {
  width: 100%;
  margin-bottom: 8px;
}

.context-menu textarea {
  background: #0b0d10;
  color: #e0e3e8;
  border: 1px solid #334155;
  border-radius: 4px;
  padding: 8px;
  font-size: 0.875rem;
  resize: vertical;
  font-family: inherit;
}

.placeholder-card {
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 12px;
  padding: 60px 40px;
  text-align: center;
  margin: 40px auto;
  max-width: 500px;
}

.placeholder-icon {
  font-size: 4rem;
  margin-bottom: 16px;
}

.placeholder-card h2 {
  margin-bottom: 12px;
  color: #e0e3e8;
}

.placeholder-card p {
  color: #94a3b8;
  margin-bottom: 24px;
  line-height: 1.5;
}
"""

    # 6. fullscreen.css - полноэкранный режим
    modules['fullscreen.css'] = """/* ============================================================
   Полноэкранный режим
   ============================================================ */

.fullscreen-overlay {
  background: #000;
}

.fullscreen-overlay:fullscreen,
.fullscreen-overlay:-webkit-full-screen,
.fullscreen-overlay:-moz-full-screen,
.fullscreen-overlay:-ms-fullscreen {
  width: 100vw !important;
  height: 100vh !important;
  padding: 0 !important;
  margin: 0 !important;
}

.fullscreen-video {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: contain;
  background: #000;
  z-index: 1;
}

.fullscreen-info-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 20px;
  background: linear-gradient(
    to bottom,
    rgba(0, 0, 0, 0.8) 0%,
    rgba(0, 0, 0, 0.4) 70%,
    transparent 100%
  );
  pointer-events: none;
  transform: translateY(-100%);
  opacity: 0;
  transition: transform 0.3s ease, opacity 0.3s ease;
}

.fullscreen-info-overlay.visible {
  transform: translateY(0);
  opacity: 1;
}

.fullscreen-info-name {
  font-size: 1rem;
  font-weight: 600;
  color: #fff;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.8);
  white-space: nowrap;
}

.fullscreen-info-location {
  font-size: 0.875rem;
  color: #cbd5e1;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.8);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.fullscreen-info-badge {
  font-size: 0.75rem;
  color: #94a3b8;
  background: rgba(255, 255, 255, 0.1);
  padding: 2px 10px;
  border-radius: 4px;
  white-space: nowrap;
}

.fullscreen-error {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 20;
  color: #dc2626;
  font-size: 1.25rem;
  text-align: center;
  background: rgba(0, 0, 0, 0.6);
  padding: 16px 24px;
  border-radius: 8px;
}
"""

    # 7. hamburger.css - меню гамбургера
    modules['hamburger.css'] = """/* ============================================================
   Меню гамбургера
   ============================================================ */

.hamburger-menu {
  position: relative;
}

.hamburger-btn {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  width: 32px;
  height: 24px;
  padding: 4px 0;
  background: transparent;
  border: none;
  cursor: pointer;
  transition: transform 0.2s ease;
}

.hamburger-btn:hover {
  transform: scale(1.1);
}

.hamburger-line {
  display: block;
  width: 100%;
  height: 2px;
  background: #e0e3e8;
  border-radius: 2px;
  transition: all 0.3s ease;
}

.hamburger-btn.active .hamburger-line:nth-child(1) {
  transform: translateY(11px) rotate(45deg);
}

.hamburger-btn.active .hamburger-line:nth-child(2) {
  opacity: 0;
}

.hamburger-btn.active .hamburger-line:nth-child(3) {
  transform: translateY(-11px) rotate(-45deg);
}

.hamburger-dropdown {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  min-width: 220px;
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
  padding: 8px;
  z-index: 2000;
  animation: dropdown-in 0.15s ease;
}

@keyframes dropdown-in {
  from { opacity: 0; transform: translateY(-8px); }
  to { opacity: 1; transform: translateY(0); }
}

.hamburger-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  color: #e0e3e8;
  text-decoration: none;
  border-radius: 6px;
  transition: background 0.15s ease;
  font-size: 0.9rem;
  cursor: pointer;
}

.hamburger-item:hover {
  background: #334155;
}

.hamburger-item.active {
  background: #2563eb;
  color: #fff;
}

.hamburger-item.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.hamburger-item-icon {
  font-size: 1.1rem;
  width: 24px;
  text-align: center;
}

.hamburger-item-label {
  flex: 1;
}

.hamburger-item-badge {
  font-size: 0.7rem;
  color: #94a3b8;
  background: rgba(255, 255, 255, 0.08);
  padding: 2px 6px;
  border-radius: 4px;
}
"""

    # 8. forms.css - селекторы и формы
    modules['forms.css'] = """/* ============================================================
   Селекторы и формы
   ============================================================ */

.set-selector {
  background: #1e293b;
  color: #e0e3e8;
  border: 1px solid #334155;
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 0.875rem;
  cursor: pointer;
  outline: none;
  transition: border-color 0.2s ease;
}

.set-selector:hover {
  border-color: #2563eb;
}

.set-selector:focus {
  border-color: #2563eb;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.2);
}
"""

    # Сохраняем модули
    for filename, content in modules.items():
        module_file = styles_dir / filename
        module_file.write_text(content, encoding="utf-8")
        size = len(content.encode('utf-8'))
        print(f"  [OK] {filename}: {size} байт")

    # Создаём главный styles.css с импортами
    main_css = """/* ============================================================
   GRYPHONE — главный файл стилей
   ------------------------------------------------------------
   Этот файл импортирует все модули из папки styles/
   ============================================================ */

@import './styles/base.css';
@import './styles/layout.css';
@import './styles/header.css';
@import './styles/camera.css';
@import './styles/components.css';
@import './styles/fullscreen.css';
@import './styles/hamburger.css';
@import './styles/forms.css';
"""

    css_file.write_text(main_css, encoding="utf-8")
    print(f"\n  [OK] {css_file.name}: создан с импортами ({len(main_css.encode('utf-8'))} байт)")

    # Итоговая статистика
    total_size = sum(len(c.encode('utf-8')) for c in modules.values())
    print(f"\n  Всего модулей: {len(modules)}")
    print(f"  Общий размер модулей: {total_size} байт")

    print()
    print("=" * 76)
    print("Готово! CSS разделён на модули.")
    print()
    print("Структура:")
    print("  frontend/src/styles.css          (главный файл с @import)")
    print("  frontend/src/styles/")
    for filename in modules.keys():
        print(f"    ├── {filename}")
    print()
    print("Обязательно пересоберите фронтенд:")
    print("  cd frontend && npm run build")
    print()
    print(f"Резервная копия: {backup.name}")
    print("=" * 76)


if __name__ == "__main__":
    main()