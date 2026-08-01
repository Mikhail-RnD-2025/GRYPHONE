import asyncio, time, logging
from pathlib import Path

from state import STATE_LOCK, CFG, CAMERAS_DB, ASYNC_TASKS, STREAM_STATS
import stream_engine # ✅ ИЗМЕНЕНО

logger = logging.getLogger(__name__)

async def sync_camera_streams():
    await _async_sync_streams()

async def _async_sync_streams():
    async with STATE_LOCK:
        current_rids = list(ASYNC_TASKS.keys())
        needed_rids = set()
        to_start = []
        for cid, cam in CAMERAS_DB.items():
            if not cam.get("enabled"):
                for rid in (f"{cid}_main", f"{cid}_sub"):
                    task = ASYNC_TASKS.pop(rid, None)
                    if task: task.cancel()
                    STREAM_STATS.pop(rid, None)
                continue
            main_rid = f"{cid}_main"; sub_rid = f"{cid}_sub"
            needed_rids.add(main_rid); to_start.append((cam["main_url"], main_rid, cid))
            sub_url = cam.get("sub_url")
            if sub_url and sub_url != cam["main_url"]: needed_rids.add(sub_rid); to_start.append((sub_url, sub_rid, cid))
        for rid in set(current_rids) - needed_rids:
            task = ASYNC_TASKS.pop(rid, None)
            if task: task.cancel(); STREAM_STATS.pop(rid, None)
    for url, rid, cid in to_start:
        if rid not in ASYNC_TASKS:
            # ✅ ИЗМЕНЕНО: вызов через stream_engine
            ASYNC_TASKS[rid] = asyncio.create_task(stream_engine.hls_worker_async(url, rid, cid))
            logger.info(f"🚀 {rid}")

async def segment_cleanup_worker():
    while True:
        try:
            c = CFG; cc = c.get("cleanup", {})
            if not cc.get("enabled", True): await asyncio.sleep(60); continue
            cp = Path(c["paths"]["hls_cache"]).resolve()
            if not cp.is_dir(): await asyncio.sleep(300); continue
            now = time.time(); ma = cc.get("max_age_hours", 24) * 3600
            async with STATE_LOCK: active_routes = set(STREAM_STATS.keys())
            for d1 in cp.iterdir():
                if not d1.is_dir(): continue
                for d2 in d1.iterdir():
                    if not d2.is_dir(): continue
                    if d2.name in active_routes:
                        for f in d2.iterdir():
                            try:
                                if f.suffix in ('.m4s','.mp4','.ts') and (now - f.stat().st_mtime) > ma: f.unlink()
                            except FileNotFoundError: pass
                        continue
                    for f in d2.iterdir():
                        try:
                            if f.suffix in ('.m4s','.mp4','.ts') and (now - f.stat().st_mtime) > ma: f.unlink()
                        except FileNotFoundError: pass
                    try:
                        if not any(d2.iterdir()): d2.rmdir()
                    except OSError: pass
        except Exception as e: logger.warning(f"Cleanup error: {e}")
        await asyncio.sleep(c.get("cleanup", {}).get("interval_seconds", 300))