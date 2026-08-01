#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль routes.py
Отвечает за: HTTP/SSE эндпоинты, REST API, отдача HLS-файлов, статика React.
"""

import os
import asyncio
import json
import time
from pathlib import Path
from quart import Response, abort, jsonify, redirect, request, send_file, url_for, send_from_directory
from quart_cors import cors

from state import STATE_LOCK, LOGS_LOCK, CFG, CAMERAS_DB, CAMERA_SETS, current_set_id, STREAM_STATS, FFMPEG_LOGS
from database import DBManager
import workers

db = DBManager()

# Получаем абсолютный путь к директории проекта
BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"


def register_routes(app):
    """Регистрация всех HTTP-маршрутов приложения."""
    
    # Включаем CORS для API
    app = cors(app, allow_origin="*", allow_methods=["GET", "POST", "PUT", "DELETE"], allow_headers=["Content-Type"])

    # =====================================================
    # React App - раздача статики (основной UI)
    # =====================================================
    
    @app.route('/')
    async def react_app():
        """Основная страница React приложения"""
        return await send_from_directory(FRONTEND_DIST, 'index.html')
    
    @app.route('/<path:path>')
    async def react_static(path):
        """Раздача статических файлов React приложения"""
        if '.' in path:
            # Это файл (JS, CSS, изображения и т.д.)
            return await send_from_directory(FRONTEND_DIST, path)
        else:
            # Это SPA роутинг - возвращаем index.html
            return await send_from_directory(FRONTEND_DIST, 'index.html')

    @app.route('/api/data')
    async def api_data():
        cfg = CFG
        return jsonify({
            "config": cfg,
            "cameras": list(CAMERAS_DB.values()),
            "sets": {"default_set": cfg["app"].get("default_set"), "sets": CAMERA_SETS}
        })

    @app.route('/api/save', methods=['POST'])
    async def api_save():
        req = await request.get_json()
        if not req: return jsonify({"success": False, "msg": "Пусто"}), 400
        f = req.get("file")
        data = req.get("d")
        if data is None: return jsonify({"success": False, "msg": "Нет данных"}), 400
        try:
            from config import default_cfg, merge_dicts, sanitize_camera
            # Используем отдельный лок для операций записи конфигурации
            async with STATE_LOCK:
                merged = default_cfg()
                merge_dicts(merged, data)
                if f == "cameras":
                    CAMERAS_DB.clear()
                    for c in data:
                        cam = sanitize_camera(c)
                        if cam: CAMERAS_DB[cam["id"]] = cam
                    await db.save("cameras", [c for c in CAMERAS_DB.values() if c])
                    # Синхронизация запускается после выхода из блокировки
                    sync_task = workers.sync_camera_streams()
                elif f == "sets":
                    CAMERA_SETS.clear()
                    CAMERA_SETS.update(data.get("sets", {}))
                    CFG["app"]["default_set"] = data.get("default_set", CFG["app"].get("default_set", ""))
                    await db.save("sets", data)
                    await db.save("config", CFG)
                    sync_task = None
                elif f == "config":
                    CFG.clear()
                    CFG.update(merged)
                    await db.save("config", CFG)
                    sync_task = None
            
            # Запускаем синхронизацию вне блокировки
            if sync_task:
                asyncio.create_task(sync_task)
                
            return jsonify({"success": True, "msg": "✅ Сохранено"})
        except Exception as e:
            return jsonify({"success": False, "msg": str(e)}), 500

    @app.route('/api/camera_comment', methods=['POST'])
    async def api_camera_comment():
        req = await request.get_json()
        cid = req.get("camera_id")
        comment = req.get("comment", "")
        if not cid: return jsonify({"success": False, "msg": "Нет ID"}), 400
        async with STATE_LOCK:
            cam = CAMERAS_DB.get(cid)
            if not cam: return jsonify({"success": False, "msg": "Не найдена"}), 404
            cam["comment"] = comment
            await db.save("cameras", list(CAMERAS_DB.values()))
        return jsonify({"success": True, "msg": "✅ Комментарий сохранён"})

    @app.route('/api/toggle_camera', methods=['POST'])
    async def api_toggle():
        req = await request.get_json()
        cid = req.get("camera_id")
        en = req.get("enabled")
        if not cid or en is None: return jsonify({"success": False}), 400
        async with STATE_LOCK:
            cam = CAMERAS_DB.get(cid)
            if not cam: return jsonify({"success": False, "msg": "Не найдена"}), 404
            cam["enabled"] = bool(en)
            await db.save("cameras", list(CAMERAS_DB.values()))
        asyncio.create_task(workers.sync_camera_streams())
        return jsonify({
            "success": True,
            "enabled": cam["enabled"],
            "message": "✅ Камера включена" if cam["enabled"] else "🔌 Камера отключена"
        })

    @app.route('/api/stream_status')
    async def api_status():
        async def gen():
            try:
                while True:
                    async with STATE_LOCK:
                        yield f"data: {json.dumps(dict(STREAM_STATS), ensure_ascii=False)}\n\n"
                    await asyncio.sleep(CFG.get("performance", {}).get("sse_interval", 1.0))
            except asyncio.CancelledError:
                pass

        return Response(
            gen(),
            mimetype="text/event-stream",
            headers={'Cache-Control': 'no-cache', 'Connection': 'keep-alive', 'X-Accel-Buffering': 'no'}
        )

    @app.route('/api/ffmpeg_logs')
    async def api_logs():
        async with LOGS_LOCK:
            return jsonify({k: list(v)[-100:] if len(v) > 100 else list(v) for k, v in FFMPEG_LOGS.items()})

    @app.route('/hls/camera/<route_id>/<path:fn>')
    async def hls(route_id, fn):
        s = Path(fn).name
        cache_root = Path(CFG.get("paths", {}).get("hls_cache", "hls_cache")).resolve()
        f = (cache_root / "camera" / route_id / s).resolve()

        try:
            f.relative_to(cache_root)
        except ValueError:
            abort(403)

        if (s.startswith("init_") and s.endswith(".mp4")) or s in ("index.m3u8", "init.mp4"):
            if not f.is_file():
                for _ in range(100):  # Увеличено время ожидания до 20 сек
                    await asyncio.sleep(0.2)
                    if f.is_file():
                        break
                if not f.is_file():
                    response = Response("", status=202)
                    response.headers['Retry-After'] = '2'
                    return response

        if not f.is_file():
            abort(404)
        if (fn.endswith(".m4s") or fn.endswith(".ts")) and f.stat().st_size < CFG["app"].get("cleanup_min_file_size",
                                                                                             100):
            abort(404)

        mimetype = {
            ".m3u8": "application/vnd.apple.mpegurl",
            ".m4s": "video/mp4",
            ".mp4": "video/mp4",
            ".ts": "video/mp2t"
        }.get(Path(fn).suffix.lower(), "application/octet-stream")

        response = None
        for attempt in range(3):
            try:
                # ✅ ВАЖНО: await перед send_file
                response = await send_file(f, mimetype=mimetype)
                break
            except PermissionError:
                if attempt < 2:
                    await asyncio.sleep(0.1)
                else:
                    response = Response("", status=202)
                    response.headers['Retry-After'] = '1'
                    return response
            except FileNotFoundError:
                abort(404)

        if response is None:
            abort(500)

        if fn.endswith(".m4s") or fn.endswith(".ts"):
            response.headers['Cache-Control'] = 'public, max-age=300, must-revalidate'
            response.headers['Access-Control-Allow-Origin'] = '*'
        elif fn.endswith(".mp4"):
            response.headers['Cache-Control'] = 'public, max-age=3600, must-revalidate'
            response.headers['Access-Control-Allow-Origin'] = '*'
        elif fn.endswith(".m3u8"):
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            response.headers['Access-Control-Allow-Origin'] = '*'
        else:
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            response.headers['Access-Control-Allow-Origin'] = '*'

        if 'ETag' in response.headers:
            del response.headers['ETag']
        return response

    @app.route('/api/dashboard')
    async def api_dashboard():
        sys_info = {"cpu": 0, "ram": 0, "disk": 0}
        try:
            import psutil
            sys_info["cpu"] = round(psutil.cpu_percent(interval=0.1), 1)
            sys_info["ram"] = round(psutil.virtual_memory().percent, 1)
            disk_path = os.environ.get('SYSTEMDRIVE', 'C:') + '\\' if os.name == 'nt' else '/'
            sys_info["disk"] = round(psutil.disk_usage(disk_path).percent, 1)
        except Exception:
            pass  # Если psutil не установлен, вернем нули

        stats = {"total": 0, "online": 0, "offline": 0, "error": 0}
        cams = []
        async with STATE_LOCK:
            for cid, cam in CAMERAS_DB.items():
                stats["total"] += 1
                is_enabled = cam.get('enabled', True)
                rid = f"{cid}_main"
                st = STREAM_STATS.get(rid, {})
                state_val = st.get("state", "checking")
                met = st.get("metrics", {})

                if not is_enabled:
                    cams.append({"id": cid, "name": cam["name"], "status": "disabled", "enabled": False, "fps": "--",
                                 "bitrate": "--"})
                    stats["offline"] += 1
                    continue

                cams.append(
                    {"id": cid, "name": cam["name"], "status": state_val, "enabled": True, "fps": met.get("fps", "--"),
                     "bitrate": met.get("bitrate", "--")})
                if state_val == "ok":
                    stats["online"] += 1
                elif state_val == "err":
                    stats["error"] += 1
                else:
                    stats["offline"] += 1

        return jsonify({"system": sys_info, "stats": stats, "cameras": cams})



    @app.route('/api/archive/stats')
    async def api_archive_stats():
        return jsonify(await db.get_archive_stats())
