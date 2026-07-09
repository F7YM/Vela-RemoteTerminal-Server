import os
import sys
import json
import importlib.util
import zipfile

APPS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'hydroApps')


def _read_manifest(app_dir: str) -> dict:
    mp = os.path.join(app_dir, 'manifest.json')
    if os.path.isfile(mp):
        try:
            with open(mp, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def list_apps() -> list[dict]:
    if not os.path.isdir(APPS_DIR):
        return []
    result = []
    for name in sorted(os.listdir(APPS_DIR)):
        d = os.path.join(APPS_DIR, name)
        if not os.path.isdir(d) or not os.path.isfile(os.path.join(d, '__init__.py')):
            continue
        m = _read_manifest(d)
        pk = m.get("package", {})
        result.append({
            "name": name,
            "displayName": pk.get("displayName", name),
            "id": pk.get("id", ""),
            "version": pk.get("version", ""),
            "path": d,
        })
    return result


def get_app_path(name: str) -> str | None:
    d = os.path.join(APPS_DIR, name)
    if os.path.isdir(d) and os.path.isfile(os.path.join(d, '__init__.py')):
        return d
    return None


def load_module(name: str):
    path = get_app_path(name)
    if not path:
        return None
    if name in sys.modules:
        del sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, os.path.join(path, '__init__.py'))
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def install(zip_path: str) -> str | None:
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            top = zf.namelist()[0].split('/')[0]
            if not os.path.isdir(APPS_DIR):
                os.makedirs(APPS_DIR)
            for member in zf.namelist():
                if member.endswith('/'):
                    os.makedirs(os.path.join(APPS_DIR, member), exist_ok=True)
                else:
                    os.makedirs(os.path.join(APPS_DIR, os.path.dirname(member)), exist_ok=True)
                    zf.extract(member, APPS_DIR)
            if not os.path.isfile(os.path.join(APPS_DIR, top, '__init__.py')):
                return None
            return top
    except Exception:
        return None


def uninstall(name: str) -> bool:
    import shutil
    d = os.path.join(APPS_DIR, name)
    if not os.path.isdir(d):
        return False
    shutil.rmtree(d)
    return True
