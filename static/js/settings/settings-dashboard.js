/**
 * settings-dashboard.js
 * Отвечает за отображение статистики системы, камер и управление фильтрами/поиском.
 */

let dashInt = null; // Глобальный таймер для дашборда

function initDashboard() {
    const camListBox = document.getElementById('cam-list-box');
    const searchInput = document.getElementById('cam-search');
    const filterNotice = document.getElementById('filter-notice');
    const sysFooter = document.getElementById('sys-footer');

    let currentData = { cameras: [], stats: { total: 0, online: 0, offline: 0, error: 0 }, system: { cpu: 0, ram: 0, disk: 0 } };
    let activeFilters = { ok: true, err: true, disabled: true };
    let searchQuery = "";

    // Функция рендеринга списка камер с учетом фильтров и поиска
    function renderCamList() {
        if (!camListBox) return;

        camListBox.innerHTML = '';
        let visibleCount = 0;

        currentData.cameras.forEach(cam => {
            // Проверка поиска
            const matchSearch = cam.name.toLowerCase().includes(searchQuery) ||
                                cam.id.toLowerCase().includes(searchQuery);

            // Проверка фильтров
            const matchFilter = activeFilters[cam.status];

            if (matchSearch && matchFilter) {
                visibleCount++;
                const div = document.createElement('div');
                div.className = `cam-item status-${cam.status}`;

                const statusText = {
                    'ok': '🟢 В сети',
                    'err': '🔴 Ошибка',
                    'disabled': '🔌 Отключено',
                    'checking': '🟡 Подключение...'
                }[cam.status] || '⚪ Неизвестно';

                div.innerHTML = `
                    <div class="cam-info">
                        <div class="cam-name">${escHtml(cam.name)}</div>
                        <div class="cam-id">ID: ${escHtml(cam.id)}</div>
                    </div>
                    <div class="cam-stats">
                        <span class="stat-badge">${statusText}</span>
                        <span class="stat-badge">🎥 ${cam.fps} FPS</span>
                        <span class="stat-badge">📶 ${cam.bitrate}</span>
                    </div>
                `;
                camListBox.appendChild(div);
            }
        });

        // Управление уведомлением о фильтрации
        if (filterNotice) {
            if (visibleCount === 0 && currentData.cameras.length > 0) {
                filterNotice.textContent = '⚠️ Нет камер, соответствующих критериям поиска или фильтрам.';
                filterNotice.style.display = 'block';
            } else {
                filterNotice.style.display = 'none';
            }
        }
    }

    // Функция обновления данных с сервера
    async function updateDashboard() {
        try {
            const res = await fetch('/api/dashboard');
            if (!res.ok) throw new Error('Network response was not ok');
            currentData = await res.json();

            // Обновление счетчиков
            const dTotal = document.getElementById('d-total');
            const dOnline = document.getElementById('d-online');
            const dErr = document.getElementById('d-err');
            const dOff = document.getElementById('d-off');

            if (dTotal) dTotal.textContent = currentData.stats.total;
            if (dOnline) dOnline.textContent = currentData.stats.online;
            if (dErr) dErr.textContent = currentData.stats.error;
            if (dOff) dOff.textContent = currentData.stats.offline;

            // Обновление системной статистики
            if (sysFooter && currentData.system) {
                sysFooter.innerHTML = `
                    <div class="sys-item">💻 CPU: <b>${currentData.system.cpu}%</b></div>
                    <div class="sys-item">🧠 RAM: <b>${currentData.system.ram}%</b></div>
                    <div class="sys-item">💾 Disk: <b>${currentData.system.disk}%</b></div>
                `;
            }

            // Перерисовка списка с сохранением текущих фильтров
            renderCamList();

        } catch (err) {
            console.error('Dashboard update error:', err);
        }
    }

    // Обработчики фильтров (чекбоксы)
    document.querySelectorAll('.status-filter').forEach(cb => {
        cb.addEventListener('change', (e) => {
            activeFilters[e.target.dataset.status] = e.target.checked;

            // Визуальное обновление карточки фильтра
            const card = e.target.closest('.dash-card');
            if (card) {
                if (e.target.checked) card.classList.add('filter-active');
                else card.classList.remove('filter-active');
            }
            renderCamList();
        });
    });

    // Обработчик поиска
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            searchQuery = e.target.value.toLowerCase().trim();
            renderCamList();
        });
    }

    // Запуск начального обновления и интервала
    updateDashboard();
    dashInt = setInterval(updateDashboard, 3000); // Обновление каждые 3 секунды
}

// Функция для остановки таймера (вызывается при уходе с вкладки)
function stopDashboard() {
    if (dashInt) {
        clearInterval(dashInt);
        dashInt = null;
    }
}

window.initDashboard = initDashboard;
window.stopDashboard = stopDashboard;