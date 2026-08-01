/**
 * main-menu.js
 * Реализация контекстного меню с мгновенным локальным обновлением UI (без перезагрузки страницы).
 */

// Страховка: если showToast не определен в utils.js, используем console.log
if (typeof window.showToast !== 'function') {
    window.showToast = (msg, type) => console.log(`[${type.toUpperCase()}] ${msg}`);
}

function initContextMenu() {
    const ctxPanel = document.getElementById('ctx-panel');
    if (!ctxPanel) {
        console.error('❌ Элемент #ctx-panel не найден в DOM!');
        return;
    }

    // 1. Находим ВСЕ карточки камер и вешаем обработчик напрямую
    const cards = document.querySelectorAll('.card');
    cards.forEach(card => {
        card.addEventListener('contextmenu', (e) => {
            // 🔒 АБСОЛЮТНАЯ БЛОКИРОВКА стандартного меню браузера
            e.preventDefault();
            e.stopPropagation();

            const camId = card.dataset.camId;
            console.log(`🖱️ Правый клик по камере: ${camId}`);

            showContextMenu(e.clientX, e.clientY, camId, card);
        });
    });

    // 2. Закрытие меню при клике в ЛЮБОМ месте вне его
    document.addEventListener('click', (e) => {
        if (ctxPanel.style.display === 'block' && !ctxPanel.contains(e.target)) {
            ctxPanel.style.display = 'none';
        }
    });

    // 3. Запрет вызова стандартного меню внутри самого нашего контекстного меню
    ctxPanel.addEventListener('contextmenu', (e) => {
        e.preventDefault();
        e.stopPropagation();
    });

    // 4. Обработчик кнопки "Включить/Отключить" (БЕЗ ПЕРЕЗАГРУЗКИ)
    const toggleBtn = document.getElementById('ctx-toggle');
    if (toggleBtn) {
        toggleBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            e.stopPropagation();

            const camId = ctxPanel.dataset.camId;
            if (!camId) return;

            const card = document.querySelector(`.card[data-cam-id="${camId}"]`);
            if (!card) return;

            const currentEnabled = card.dataset.enabled === 'true';
            const newState = !currentEnabled;

            try {
                const response = await fetch('/api/toggle_camera', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ camera_id: camId, enabled: newState })
                });

                const r = await response.json();
                if (r.success) {
                    window.showToast(newState ? 'Камера включена' : 'Камера отключена', 'ok');

                    // ✅ МГНОВЕННОЕ ОБНОВЛЕНИЕ ИНТЕРФЕЙСА БЕЗ RELOAD

                    // 1. Обновляем глобальные данные
                    const camData = window.camsData.find(c => c.id === camId);
                    if (camData) {
                        camData.enabled = newState;
                    }

                    // 2. Обновляем атрибут на карточке
                    card.dataset.enabled = newState.toString();

                    // 3. Обновляем кнопку в меню (на случай, если оно осталось открытым)
                    toggleBtn.textContent = newState ? '🔴 Отключить' : '🟢 Включить';
                    toggleBtn.className = `ctx-toggle ${newState ? 'btn-disable' : 'btn-enable'}`;

                    // 4. Визуальное обновление карточки при отключении
                    if (!newState) {
                        const dot = card.querySelector('.dot');
                        const ov = card.querySelector('.ov');
                        if (dot) dot.className = 'dot disabled';
                        if (ov) {
                            ov.textContent = 'Отключено';
                            ov.style.display = 'block';
                        }
                        // Останавливаем видео, если оно играло
                        const video = card.querySelector('video');
                        if (video) {
                            video.pause();
                            if (window.hlsInstances && window.hlsInstances[camId]) {
                                window.hlsInstances[camId].destroy();
                                delete window.hlsInstances[camId];
                            }
                        }
                    } else {
                        // При включении возвращаем статус "Подключение...", HLS запустится через SSE
                        const dot = card.querySelector('.dot');
                        const ov = card.querySelector('.ov');
                        if (dot) dot.className = 'dot load';
                        if (ov) {
                            ov.textContent = 'Подключение...';
                            ov.style.display = 'block';
                        }
                    }

                    // 5. Закрываем меню
                    ctxPanel.style.display = 'none';

                } else {
                    window.showToast(r.msg || 'Ошибка сервера', 'err');
                }
            } catch (err) {
                console.error('Toggle error:', err);
                window.showToast('Ошибка сети', 'err');
            }
        });
    }

    // 5. Обработчик кнопки "Сохранить комментарий"
    const saveBtn = document.getElementById('ctx-save-comment');
    if (saveBtn) {
        saveBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            e.stopPropagation();

            const camId = ctxPanel.dataset.camId;
            if (!camId) return;

            const txt = ctxPanel.querySelector('#ctx-comment').value;

            try {
                const response = await fetch('/api/camera_comment', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ camera_id: camId, comment: txt })
                });

                const r = await response.json();
                if (r.success) {
                    window.showToast('Комментарий сохранён', 'ok');

                    // Обновляем локальные данные
                    const camData = window.camsData.find(c => c.id === camId);
                    if (camData) {
                        camData.comment = txt;
                    }

                    ctxPanel.style.display = 'none';
                } else {
                    window.showToast(r.msg || 'Ошибка сервера', 'err');
                }
            } catch (err) {
                console.error('Comment error:', err);
                window.showToast('Ошибка сети', 'err');
            }
        });
    }
}

function showContextMenu(x, y, camId, cardElement) {
    const ctx = document.getElementById('ctx-panel');
    if (!ctx) return;

    ctx.style.display = 'none'; // Сброс перед перерисовкой
    ctx.dataset.camId = camId;

    const camData = window.camsData.find(c => c.id === camId) || {};

    const toggleBtn = ctx.querySelector('#ctx-toggle');
    toggleBtn.textContent = camData.enabled ? '🔴 Отключить' : '🟢 Включить';
    toggleBtn.className = `ctx-toggle ${camData.enabled ? 'btn-disable' : 'btn-enable'}`;

    ctx.querySelector('#ctx-url-main').textContent = cardElement.dataset.mainUrl || '--';
    ctx.querySelector('#ctx-url-sub').textContent = cardElement.dataset.subUrl || '--';
    ctx.querySelector('#ctx-comment').value = camData.comment || '';

    const rid = cardElement.dataset.subRoute;
    const stats = window.hlsStreamStats || {};
    const info = stats[rid] || {};
    const metrics = info.metrics || {};

    ctx.querySelector('#ctx-fps').textContent = metrics.fps || '--';
    ctx.querySelector('#ctx-br').textContent = metrics.bitrate || '--';
    ctx.querySelector('#ctx-time').textContent = metrics.time || '--';

    const menuW = 260;
    const menuH = 280;
    const left = Math.min(x, window.innerWidth - menuW - 10);
    const top = Math.min(y, window.innerHeight - menuH - 10);

    ctx.style.left = `${left}px`;
    ctx.style.top = `${top}px`;
    ctx.style.display = 'block';
}

window.initContextMenu = initContextMenu;