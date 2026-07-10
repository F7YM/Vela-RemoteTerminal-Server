import os
import sys
import json
import importlib.util
import zipfile
import tempfile
import shutil

APPS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'hydroApps')
# 客户端最低 API 等级（与客户端 manifest.json 的 minAPILevel 保持一致）
CLIENT_MIN_API_LEVEL = 2


def _read_manifest(app_dir: str) -> dict:
    mp = os.path.join(app_dir, 'manifest.json')
    if os.path.isfile(mp):
        try:
            with open(mp, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def validate_manifest(manifest: dict) -> tuple:
    """校验 manifest，返回 (是否合法, 错误信息)"""
    if not manifest:
        return False, "缺少 manifest.json"
    pkg = manifest.get("package", {})
    if not pkg.get("id"):
        return False, "manifest.json 缺少 package.id"
    min_api = manifest.get("minAPILevel")
    if min_api is None:
        return False, "manifest.json 缺少 minAPILevel"
    try:
        min_api = int(min_api)
    except (ValueError, TypeError):
        return False, f"minAPILevel 无效: {min_api}"
    if min_api < CLIENT_MIN_API_LEVEL:
        return False, f"minAPILevel ({min_api}) 低于客户端最低要求 ({CLIENT_MIN_API_LEVEL})"
    return True, ""
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
    # 清除所有相关子模块缓存，确保代码修改生效
    for mod_name in list(sys.modules.keys()):
        if mod_name == name or mod_name.startswith(name + '.'):
            del sys.modules[mod_name]
    spec = importlib.util.spec_from_file_location(name, os.path.join(path, '__init__.py'))
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def install(zip_path: str) -> str | None:
    try:
        tmp = tempfile.mkdtemp()
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(tmp)
        # 找到含 __init__.py 的应用目录
        items = os.listdir(tmp)
        app_dir = None
        for item in items:
            candidate = os.path.join(tmp, item)
            if os.path.isdir(candidate) and os.path.isfile(os.path.join(candidate, '__init__.py')):
                app_dir = candidate
                break
        if not app_dir:
            shutil.rmtree(tmp)
            return None
        # 读取 manifest.json 中的 package.name 作为目录名
        manifest = _read_manifest(app_dir)
        valid, err = validate_manifest(manifest)
        if not valid:
            shutil.rmtree(tmp)
            print(f"[HydroApp] 安装失败: {err}", flush=True)
            return None
        pkg = manifest.get("package", {})
        target_name = pkg.get("id") or os.path.basename(app_dir)
        target_path = os.path.join(APPS_DIR, target_name)
        # 如果目标已存在则删除
        if os.path.isdir(target_path):
            shutil.rmtree(target_path)
        os.makedirs(APPS_DIR, exist_ok=True)
        shutil.move(app_dir, target_path)
        shutil.rmtree(tmp)
        return target_name
    except Exception:
        return None


def uninstall(name: str) -> bool:
    d = os.path.join(APPS_DIR, name)
    if not os.path.isdir(d):
        return False
    shutil.rmtree(d)
    return True
