
# tests/_utils_io.py
import json, time, pathlib, contextlib

STATE = pathlib.Path("state"); STATE.mkdir(exist_ok=True)

def read_json(path, default):
    p = pathlib.Path(path)
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default

def write_json(path, obj):
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(p)

@contextlib.contextmanager
def stopwatch():
    t0 = time.perf_counter()
    yield lambda: time.perf_counter() - t0
