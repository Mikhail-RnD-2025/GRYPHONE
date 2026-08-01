// static/js/settings-logs.js

window.logsCollapsed = new Set();
window.isAllCollapsed = false;
window.lastLogsData = {};

function renderLogs(d) {
    const content = document.getElementById('log-content');
    const status = document.getElementById('log-status');
    if (!content || !status) return;

    let h = ''; let t = 0;
    const k = Object.keys(d || {}).sort();
    window.lastLogsData = d || {};

    if (!k.length) {
        content.innerHTML = '<div style="padding:16px;text-align:center;color:#64748b">⏳ Потоков нет...</div>';
        status.textContent = '⌛';
        return;
    }

    k.forEach(x => {
        t += d[x].length;
        const col = window.logsCollapsed.has(x);
        h += `
            <div class="stream-group">
                <div class="stream-title" onclick="toggleStreamLog('${escHtml(x)}')">
                    🎥 ${escHtml(x)} <span>${col ? '▶' : '▼'}</span>
                </div>
                <div class="stream-logs ${col ? 'collapsed' : ''}">
                    ${d[x].map(l => `<div class="log-line">${escHtml(l)}</div>`).join('')}
                </div>
            </div>
        `;
    });
    content.innerHTML = h;
    status.textContent = `${k.length} пот. | ${t} стр.`;
}

function toggleStreamLog(id) {
    window.logsCollapsed.has(id) ? window.logsCollapsed.delete(id) : window.logsCollapsed.add(id);
    document.querySelectorAll('.stream-group').forEach(g => {
        const logs = g.querySelector('.stream-logs');
        const title = g.querySelector('.stream-title').innerText.replace('🎥 ', '').trim();
        if (window.logsCollapsed.has(title)) {
            logs.classList.add('collapsed');
            g.querySelector('span').textContent = '▶';
        } else {
            logs.classList.remove('collapsed');
            g.querySelector('span').textContent = '▼';
        }
    });
}

function startLogs() {
    if (window.logInt) clearInterval(window.logInt);
    const f = () => fetch('/api/ffmpeg_logs').then(r => r.json()).then(d => renderLogs(d));
    f();
    window.logInt = setInterval(f, 2000);
}

function initLogsButtons() {
    document.getElementById('btn-clear-logs')?.addEventListener('click', () => {
        const content = document.getElementById('log-content');
        if (content) content.innerHTML = '';
        const status = document.getElementById('log-status');
        if (status) status.textContent = '🧹';
    });

    document.getElementById('btn-toggle-streams')?.addEventListener('click', () => {
        window.isAllCollapsed = !window.isAllCollapsed;
        if (window.isAllCollapsed) {
            window.logsCollapsed = new Set(Object.keys(window.lastLogsData));
        } else {
            window.logsCollapsed.clear();
        }
        document.querySelectorAll('.stream-group').forEach(g => {
            g.querySelector('.stream-logs').classList.toggle('collapsed', window.isAllCollapsed);
            g.querySelector('span').textContent = window.isAllCollapsed ? '▶' : '▼';
        });
    });
}

window.renderLogs = renderLogs;
window.toggleStreamLog = toggleStreamLog;
window.startLogs = startLogs;
window.initLogsButtons = initLogsButtons;