/**
 * main-grid.js
 * Отвечает за расчет размеров ячеек и идеальное центрирование сетки камер.
 */

function initGrid() {
    const cams = window.camsData || [];
    const grid = document.getElementById('grid');
    const MAX_COLS = window.maxCols || 2;
    const AR_STR = window.aspectRatio || '16:9';

    if (!grid || cams.length === 0 || MAX_COLS < 1) return;

    function fitGrid() {
        const wrapper = document.querySelector('.grid-wrapper');
        if (!wrapper) return;

        const cols = MAX_COLS;
        const rows = Math.ceil(cams.length / cols);
        const ar = AR_STR.split('/');
        const ratio = (parseFloat(ar[0]) || 16) / (parseFloat(ar[1]) || 9);
        const gap = 8;

        const style = window.getComputedStyle(wrapper);
        const padTop = parseFloat(style.paddingTop) || 0;
        const padBottom = parseFloat(style.paddingBottom) || 0;
        const padLeft = parseFloat(style.paddingLeft) || 0;
        const padRight = parseFloat(style.paddingRight) || 0;

        const availW = wrapper.clientWidth - padLeft - padRight;
        const availH = wrapper.clientHeight - padTop - padBottom;
        if (availW <= 0 || availH <= 0) return;

        const maxH_by_W = (availW - (cols - 1) * gap) / (cols * ratio);
        const maxH_by_H = (availH - (rows - 1) * gap) / rows;

        let cellH = Math.min(maxH_by_W, maxH_by_H);
        cellH = Math.max(60, Math.floor(cellH));
        const cellW = Math.floor(cellH * ratio);
        const totalW = cols * cellW + (cols - 1) * gap;
        const totalH = rows * cellH + (rows - 1) * gap;

        grid.style.width = `${totalW}px`;
        grid.style.height = `${totalH}px`;
        grid.style.gridTemplateColumns = `repeat(${cols}, ${cellW}px)`;
        grid.style.gridTemplateRows = `repeat(${rows}, ${cellH}px)`;
    }

    new ResizeObserver(fitGrid).observe(document.querySelector('.grid-wrapper'));
    setTimeout(fitGrid, 100);
}

window.initGrid = initGrid;