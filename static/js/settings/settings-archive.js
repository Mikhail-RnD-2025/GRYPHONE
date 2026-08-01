// static/js/settings-archive.js

function renderArchivePools(stats) {
    const c = document.getElementById('archive-pools');
    if (!c || !stats) return;
    c.innerHTML = '';
    const pools = window.archivePools || [];
    pools.forEach(p => {
        const u = stats[p.id]?.size || 0;
        const m = p.max_size_gb * 1024 ** 3;
        const pct = Math.min(100, (u / m) * 100);
        c.innerHTML += `
            <div class="pool-card">
                <div class="pool-header">
                    <span>📂 ${p.id}</span>
                    <span style="color:${pct > 90 ? 'var(--err)' : 'var(--ok)'}">
                        ${formatBytes(u)} / ${formatBytes(m)}
                    </span>
                </div>
                <div class="pool-bar">
                    <div class="pool-fill" style="width:${pct}%;background:${pct > 90 ? 'var(--err)' : '#3b82f6'}"></div>
                </div>
            </div>
        `;
    });
}

window.renderArchivePools = renderArchivePools;