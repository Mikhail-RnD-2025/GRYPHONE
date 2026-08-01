/**
 * main.js
 * Оркестратор: инициализирует глобальные состояния и запускает все модули в правильном порядке.
 */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Инициализация глобальных хранилищ состояний
    window.hlsInstances = {};
    window.prevStreamStates = {};
    window.hlsStreamStats = {};
    window.recoveryTimers = {};

    // 2. Запуск модулей
    if (typeof window.initGrid === 'function') window.initGrid();
    if (typeof window.initAutoHideHeader === 'function') window.initAutoHideHeader();
    if (typeof window.initCameras === 'function') window.initCameras();
    if (typeof window.initContextMenu === 'function') window.initContextMenu();
    if (typeof window.initStreamMonitoring === 'function') window.initStreamMonitoring();
});