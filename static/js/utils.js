function escHtml(s) {
    return String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

function debounce(fn, ms) {
    let t;
    return function(...args) { clearTimeout(t); t = setTimeout(() => fn.apply(this, args), ms); };
}

function showToast(msg, type = 'info') {
    const c = document.getElementById('toast-container');
    if (!c) return;
    const d = document.createElement('div');
    d.className = 'toast toast-' + type;
    d.textContent = msg;
    c.appendChild(d);
    setTimeout(() => d.remove(), 4000);
}

function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024, sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// ✅ ФУНКЦИЯ АВТОМАТИЧЕСКОГО СКРЫТИЯ ШАПКИ
function initAutoHideHeader() {
    const header = document.querySelector('header');
    if (!header) return;

    let hTimeout;
    const handlePointer = (cy) => {
        if (cy < 60) { // Мышь в верхней части экрана
            header.classList.remove('hidden');
            clearTimeout(hTimeout);
        } else if (cy > 120 && !header.matches(':hover')) { // Мышь внизу, шапка не под курсором
            hTimeout = setTimeout(() => header.classList.add('hidden'), 2500);
        }
    };

    document.addEventListener('mousemove', e => handlePointer(e.clientY));
    document.addEventListener('touchstart', () => {
        header.classList.remove('hidden');
        clearTimeout(hTimeout);
        hTimeout = setTimeout(() => {
            if (!header.matches(':hover')) header.classList.add('hidden');
        }, 4000);
    }, { passive: true });
}

document.addEventListener('DOMContentLoaded', () => {
    // Инициализация модального окна справки
    const helpBtn = document.getElementById('helpBtn');
    const helpModal = document.getElementById('helpModal');
    if (helpBtn && helpModal) {
        helpBtn.onclick = (e) => { e.preventDefault(); helpModal.style.display = 'flex'; };
        const closeBtn = helpModal.querySelector('.close');
        if (closeBtn) closeBtn.onclick = () => { helpModal.style.display = 'none'; };
        helpModal.onclick = (e) => { if (e.target === helpModal) helpModal.style.display = 'none'; };
    }

    // ✅ Запускаем авто-скрытие шапки на всех страницах
    initAutoHideHeader();
});