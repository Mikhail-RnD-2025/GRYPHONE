import asyncio
from concurrent.futures import ThreadPoolExecutor

STATE_LOCK = asyncio.Lock()
LOGS_LOCK = asyncio.Lock()
ACTIVE_PROCS_LOCK = asyncio.Lock()

CFG = {}
CAMERAS_DB = {}
CAMERA_SETS = {}
current_set_id = ""
STREAM_STATS = {}
FFMPEG_LOGS = {}
ASYNC_TASKS = {}
ACTIVE_PROCS = {}
PROBE_EXECUTOR = None