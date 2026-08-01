/**
 * main-stream.js
 * Возврат к надежной логике: приоритет реального состояния видео над сообщениями сервера.
 */

function initStreamMonitoring() {
    const evtSource = new EventSource('/api/stream_status');
    window.recoveryTimers = {};

    let sseWatchdog;
    function resetWatchdog() {
        clearTimeout(sseWatchdog);
        sseWatchdog = setTimeout(() => {
            console.warn("⚠️ SSE watchdog: нет данных 15 сек. Перезагрузка страницы...");
            location.reload();
        }, 15000);
    }

    evtSource.onopen = () => {
        console.log("✅ SSE соединение установлено");
        resetWatchdog();
    };

    evtSource.onmessage = function (e) {
        resetWatchdog();

        try {
            const stats = JSON.parse(e.data);
            window.hlsStreamStats = stats;

            for (const [rid, info] of Object.entries(stats)) {
                const card = document.querySelector(`.card[data-sub-route="${rid}"]`);
                if (!card) continue;

                const dot = card.querySelector('.dot');
                const ov = card.querySelector('.ov');
                const v = card.querySelector('video');
                const camId = card.dataset.camId;
                const prevState = window.prevStreamStates[rid];
                const newState = info.state;

                // =========================================================================
                // 🛑 ШАГ 1: АБСОЛЮТНАЯ ИСТИНА (Как было в монолитной версии)
                // Если видео не на паузе И (готовность >= 2 ИЛИ есть реальные пиксели)
                // =========================================================================
                const isActuallyPlaying = v && !v.paused && (v.readyState >= 2 || v.videoWidth > 0);

                if (isActuallyPlaying) {
                    // ПРИНУДИТЕЛЬНО делаем зеленым. Сервер не может это переписать.
                    if (dot) dot.className = 'dot ok';
                    if (ov) ov.style.display = 'none';
                    window.prevStreamStates[rid] = 'ok'; // Синхронизируем состояние
                    continue; // Переходим к следующей камере
                }

                // =========================================================================
                // 🛑 ШАГ 2: ЗАПУСК ВОССТАНОВЛЕНИЯ
                // Сервер говорит "ok", но видео еще НЕ играет
                // =========================================================================
                if (newState === 'ok' && (prevState === 'err' || prevState === 'checking' || prevState === undefined)) {
                    console.log(`🔄 [${camId}] Сервер: OK, запускаем восстановление HLS...`);

                    if (window.recoveryTimers[camId]) {
                        clearTimeout(window.recoveryTimers[camId]);
                        delete window.recoveryTimers[camId];
                    }

                    // Показываем процесс переподключения
                    if (dot) dot.className = 'dot load';
                    if (ov) {
                        ov.textContent = '🔄 Переподключение...';
                        ov.style.display = 'block';
                    }

                    if (typeof window.recoverHlsInstance === 'function') {
                        window.recoverHlsInstance(card, camId);
                    }
                    continue; // Пропускаем стандартное обновление, чтобы не мигало
                }

                // =========================================================================
                // 🛑 ШАГ 3: ПОТЕРЯ СВЯЗИ
                // =========================================================================
                if (newState === 'err' && prevState === 'ok') {
                    console.log(`⚠️ [${camId}] Потеря связи. Таймер перезагрузки: 30 сек.`);
                    if (window.recoveryTimers[camId]) clearTimeout(window.recoveryTimers[camId]);
                    window.recoveryTimers[camId] = setTimeout(() => location.reload(), 30000);
                }

                // =========================================================================
                // 🛑 ШАГ 4: СТАНДАРТНОЕ ОБНОВЛЕНИЕ (Только если видео НЕ играет)
                // =========================================================================
                if (newState === 'ok') {
                    if (dot) dot.className = 'dot ok';
                    if (ov && !ov.classList.contains('ov-clickable')) ov.style.display = 'none';
                } else if (newState === 'err') {
                    if (dot) dot.className = 'dot err';
                    if (ov) { ov.textContent = 'Недоступна'; ov.style.display = 'block'; }
                } else {
                    // Состояние 'checking' (показываем только при первой загрузке, а не при восстановлении)
                    if (dot) dot.className = 'dot load';
                    if (ov) { ov.textContent = info.msg || 'Подключение...'; ov.style.display = 'block'; }
                }

                window.prevStreamStates[rid] = newState;
            }
        } catch (err) {
            console.error('SSE Error:', err);
        }
    };

    evtSource.onerror = function(err) {
        console.warn("⚠️ SSE соединение временно разорвано. Браузер переподключается автоматически...");
    };

    resetWatchdog();

    window.addEventListener('beforeunload', () => {
        clearTimeout(sseWatchdog);
        if (window.recoveryTimers) {
            Object.values(window.recoveryTimers).forEach(t => clearTimeout(t));
        }
    });
}

window.initStreamMonitoring = initStreamMonitoring;