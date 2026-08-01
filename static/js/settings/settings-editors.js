// static/js/settings-editors.js

window.settingsEditors = {};

function initEditors() {
    if (typeof CodeMirror === 'undefined') {
        console.warn('⚠️ CodeMirror не загружен. Редакторы JSON недоступны.');
        return;
    }
    ['config', 'cameras', 'sets'].forEach(k => {
        const el = document.getElementById('editor-' + k);
        if (el) {
            window.settingsEditors[k] = CodeMirror(el, {
                mode: "application/json",
                theme: "dracula",
                lineNumbers: true,
                autoCloseBrackets: true,
                matchBrackets: true,
                indentUnit: 2,
                tabSize: 2,
                lineWrapping: true
            });
            window.settingsEditors[k].on('change', window.validateJSON);
        }
    });
}

function validateJSON() {
    try {
        JSON.parse(window.settingsEditors[window.currentTab]?.getValue() || '{}');
        const msg = document.getElementById('v-msg');
        if (msg) msg.innerHTML = '<span style="color:var(--ok)">✅ Валиден</span>';
        return true;
    } catch (e) {
        const msg = document.getElementById('v-msg');
        if (msg) msg.innerHTML = `<span style="color:var(--err)">❌ ${escHtml(e.message)}</span>`;
        return false;
    }
}

function saveConfig() {
    if (!validateJSON()) return;
    const b = document.getElementById('saveBtn');
    if (b) { b.disabled = true; b.textContent = '⏳...'; }
    try {
        const d = JSON.parse(window.settingsEditors[window.currentTab].getValue());
        fetch('/api/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ file: window.currentTab, d })
        })
            .then(r => r.json())
            .then(r => {
                showToast(r.msg, r.success ? 'ok' : 'err');
                if (b) { b.disabled = false; b.textContent = '💾 Сохранить'; }
            })
            .catch(() => {
                showToast('Ошибка сети', 'err');
                if (b) { b.disabled = false; b.textContent = '💾 Сохранить'; }
            });
    } catch (e) {
        if (b) { b.disabled = false; b.textContent = '💾 Сохранить'; }
    }
}

function formatJSON() {
    if (!window.settingsEditors[window.currentTab]) return;
    try {
        window.settingsEditors[window.currentTab].setValue(
            JSON.stringify(JSON.parse(window.settingsEditors[window.currentTab].getValue()), null, 2)
        );
    } catch (e) {
        showToast('Ошибка JSON', 'err');
    }
}

function exportJSON() {
    if (!validateJSON()) return;
    const a = document.createElement('a');
    a.href = URL.createObjectURL(
        new Blob([window.settingsEditors[window.currentTab].getValue()], { type: 'application/json' })
    );
    a.download = `${window.currentTab}.json`;
    a.click();
}

function loadConfigs() {
    fetch('/api/data')
        .then(r => {
            if (!r.ok) throw new Error(`HTTP ${r.status}`);
            return r.json();
        })
        .then(d => {
            ['config', 'cameras', 'sets'].forEach(k => {
                if (window.settingsEditors[k]) {
                    try {
                        window.settingsEditors[k].setValue(JSON.stringify(d[k] || {}, null, 2));
                    } catch (e) {
                        console.error(`Ошибка загрузки конфига [${k}]:`, e);
                    }
                }
            });
        })
        .catch((e) => {
            console.error('Load configs error:', e);
            showToast('Ошибка загрузки конфига', 'err');
        });
}

window.initEditors = initEditors;
window.validateJSON = validateJSON;
window.saveConfig = saveConfig;
window.formatJSON = formatJSON;
window.exportJSON = exportJSON;
window.loadConfigs = loadConfigs;