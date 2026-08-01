/**
 * main-header.js
 * Отвечает за автоматическое скрытие и появление верхней панели управления.
 */

function initAutoHideHeader() {
    const handlePointer = cy => {
        const h = document.querySelector('header');
        if (!h) return;

        if (cy < 60) {
            h.classList.remove('hidden');
            clearTimeout(window.hTimeout);
        } else if (cy > 120 && !h.matches(':hover')) {
            window.hTimeout = setTimeout(() => h.classList.add('hidden'), 2500);
        }
    };

    document.addEventListener('mousemove', e => handlePointer(e.clientY));
    document.addEventListener('touchstart', () => {
        const h = document.querySelector('header');
        if (h) h.classList.remove('hidden');
        clearTimeout(window.hTimeout);
        window.hTimeout = setTimeout(() => { if (h) h.classList.add('hidden'); }, 4000);
    }, { passive: true });
}

window.initAutoHideHeader = initAutoHideHeader;