/**
 * main-camera.js
 * Инициализация HLS и восстановление потока.
 */

function initCameras() {
    const cams = window.camsData || [];
    const hlsConfig = window.hlsCfg || {};

    cams.forEach(c => {
        const d = document.querySelector(`.card[data-cam-id="${c.id}"]`);
        if (!d) return;

        if (!c.enabled) {
            d.querySelector('.dot').className = 'dot disabled';
            d.querySelector('.ov').textContent = 'Отключено';
            return;
        }

        const wrap = d.querySelector('.wrap');
        const v = wrap.querySelector('video');
        const dot = d.querySelector('.dot');
        const ov = d.querySelector('.ov');

        v.controls = false;
        v.disablePictureInPicture = true;

        d.addEventListener('dblclick', (e) => {
            e.preventDefault();
            if (document.fullscreenElement) {
                document.exitFullscreen();
            } else {
                if (v.requestFullscreen) v.requestFullscreen();
                else if (v.webkitRequestFullscreen) v.webkitRequestFullscreen();
                else if (v.msRequestFullscreen) v.msRequestFullscreen();
            }
        });

        if (Hls.isSupported()) {
            const hls = new Hls({
                ...hlsConfig,
                liveSyncDuration: 3,
                liveMaxLatencyDuration: 10,
                enableWorker: true,
                lowLatencyMode: false,
                startFragPrefetch: true,
                maxBufferLength: 10,
                maxMaxBufferLength: 30,
                xhrSetup: x => {
                    x.setRequestHeader('Cache-Control', 'no-store');
                    x.setRequestHeader('Pragma', 'no-cache');
                }
            });

            window.hlsInstances[c.id] = hls;

            hls.on(Hls.Events.MANIFEST_PARSED, () => {
                if (ov) ov.style.display = 'none';
                v.play().catch(() => {
                    if (ov) {
                        ov.textContent = '▶ Нажмите';
                        ov.classList.add('ov-clickable');
                        ov.onclick = () => { v.play().catch(() => {}); ov.style.display = 'none'; };
                    }
                });
                if (dot) dot.className = 'dot ok';
            });

            hls.on(Hls.Events.ERROR, (e, data) => {
                if (data.type === Hls.ErrorTypes.NETWORK_ERROR && data.details === Hls.ErrorDetails.MANIFEST_LOAD_ERROR) {
                    setTimeout(() => hls.loadSource(d.dataset.subUrl), 2000);
                    return;
                }
                if (data.fatal) {
                    if (dot) dot.className = 'dot err';
                    if (ov) { ov.textContent = 'Ошибка: ' + (data.details || 'unknown'); ov.style.display = 'block'; }
                }
            });

            hls.loadSource(d.dataset.subUrl);
            hls.attachMedia(v);

        } else if (v.canPlayType('application/vnd.apple.mpegurl')) {
            v.src = d.dataset.subUrl;
            v.load();
            v.addEventListener('playing', () => {
                if (dot) dot.className = 'dot ok';
                if (ov) ov.style.display = 'none';
            }, { once: true });
        }
    });
}

function recoverHlsInstance(card, camId) {
    const v = card.querySelector('video');
    const ov = card.querySelector('.ov');
    const dot = card.querySelector('.dot');
    if (!v) return;

    console.log(`🛠️ [${camId}] Запуск процедуры восстановления HLS...`);

    const oldHls = window.hlsInstances[camId];
    if (oldHls) {
        try { oldHls.destroy(); } catch (e) {}
        delete window.hlsInstances[camId];
    }

    v.pause();
    v.removeAttribute('src');
    v.load();
    v.controls = false;
    v.disablePictureInPicture = true;

    // Задержка 500 мс для освобождения ресурсов браузера
    setTimeout(() => {
        const baseUrl = card.dataset.subUrl;
        const url = baseUrl + (baseUrl.includes('?') ? '&' : '?') + 't=' + Date.now();
        const hlsConfig = window.hlsCfg || {};

        console.log(`🔄 [${camId}] Создание нового HLS с URL: ${url}`);

        if (Hls.isSupported()) {
            const hls = new Hls({
                ...hlsConfig,
                liveSyncDuration: 3,
                liveMaxLatencyDuration: 10,
                enableWorker: true,
                lowLatencyMode: false,
                startFragPrefetch: true,
                maxBufferLength: 10,
                maxMaxBufferLength: 30,
                xhrSetup: x => {
                    x.setRequestHeader('Cache-Control', 'no-store');
                    x.setRequestHeader('Pragma', 'no-cache');
                }
            });

            window.hlsInstances[camId] = hls;

            // Когда HLS подключается, он делает свою часть работы.
            // А main-stream.js на следующем тике увидит isActuallyPlaying и закрепит успех.
            hls.on(Hls.Events.MANIFEST_PARSED, () => {
                console.log(`✅ [${camId}] HLS восстановлен!`);
                if (ov) ov.style.display = 'none';
                v.play().catch(() => {
                    if (ov) {
                        ov.textContent = '▶ Нажмите';
                        ov.classList.add('ov-clickable');
                        ov.onclick = () => { v.play().catch(() => {}); ov.style.display = 'none'; };
                    }
                });
                if (dot) dot.className = 'dot ok';
            });

            hls.on(Hls.Events.ERROR, (e, data) => {
                if (data.type === Hls.ErrorTypes.NETWORK_ERROR && data.details === Hls.ErrorDetails.MANIFEST_LOAD_ERROR) {
                    console.log(`⏳ [${camId}] Манифест не готов. Повтор через 2 сек...`);
                    setTimeout(() => recoverHlsInstance(card, camId), 2000);
                    return;
                }
                if (data.fatal) {
                    console.error(`❌ [${camId}] Фатальная ошибка HLS.`);
                    setTimeout(() => location.reload(), 2000);
                }
            });

            hls.loadSource(url);
            hls.attachMedia(v);

        } else if (v.canPlayType('application/vnd.apple.mpegurl')) {
            v.src = url;
            v.load();
            v.addEventListener('playing', () => {
                if (dot) dot.className = 'dot ok';
                if (ov) ov.style.display = 'none';
            }, { once: true });
        }
    }, 500);
}

window.initCameras = initCameras;
window.recoverHlsInstance = recoverHlsInstance;