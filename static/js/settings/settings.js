/**
 * settings.js
 * Оркестратор страницы настроек: управление вкладками, отображение панелей
 * и критически важное управление фоновыми таймерами (Dashboard, Logs).
 */

document.addEventListener('DOMContentLoaded', () => {
    const tabs = document.querySelectorAll('.tab');
    const panels = document.querySelectorAll('.tab-panel');
    const controlsArea = document.getElementById('controls-area');

    // Получаем активную вкладку из глобальной переменной (передается из Jinja2)
    const initialTab = window.activeTab || 'config';

    /**
     * Функция переключения вкладок с полным управлением состоянием
     */
    function switchTab(tabId) {
        // 1. Обновление визуального состояния вкладок
        tabs.forEach(t => {
            if (t.dataset.tab === tabId) {
                t.classList.add('active');
            } else {
                t.classList.remove('active');
            }
        });

        // 2. Отображение нужной панели контента
        const panelMap = {
            'config': 'editor-config',
            'cameras': 'editor-cameras',
            'sets': 'editor-sets',
            'archive': 'archive-content',
            'logs': 'log-viewer',
            'dashboard': 'dashboard-content'
        };

        panels.forEach(p => {
            if (p.id === panelMap[tabId]) {
                p.classList.remove('hidden');
            } else {
                p.classList.add('hidden');
            }
        });

        // 3. Управление видимостью панели кнопок "Сохранить / Формат / Экспорт"
        // Показываем только на вкладках с редакторами
        if (['config', 'cameras', 'sets'].includes(tabId)) {
            if (controlsArea) controlsArea.classList.remove('hidden');
        } else {
            if (controlsArea) controlsArea.classList.add('hidden');
        }

        // 4. ✅ КРИТИЧЕСКИ ВАЖНО: Управление фоновыми таймерами

        // --- DASHBOARD ---
        if (tabId === 'dashboard') {
            // Сначала останавливаем старый таймер (на всякий случай), затем запускаем новый
            if (typeof window.stopDashboard === 'function') window.stopDashboard();
            if (typeof window.initDashboard === 'function') window.initDashboard();
        } else {
            // Если ушли с вкладки дашборда, обязательно останавливаем опрос
            if (typeof window.stopDashboard === 'function') window.stopDashboard();
        }

        // --- LOGS ---
        if (tabId === 'logs') {
            if (typeof window.startLogPolling === 'function') window.startLogPolling();
        } else {
            if (typeof window.stopLogPolling === 'function') window.stopLogPolling();
        }

        // --- ARCHIVE ---
        // Если у архива есть своя функция инициализации при открытии вкладки
        if (tabId === 'archive' && typeof window.initArchive === 'function') {
            window.initArchive();
        }
    }

    // Навешиваем обработчики кликов на все вкладки
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            switchTab(tab.dataset.tab);
        });
    });

    // 5. Первичная инициализация при загрузке страницы
    switchTab(initialTab);

    // Инициализация CodeMirror редакторов (функция должна быть в settings-editors.js)
    if (typeof window.initEditors === 'function') {
        window.initEditors(initialTab);
    }
});