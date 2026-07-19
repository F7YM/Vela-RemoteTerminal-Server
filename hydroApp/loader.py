import os
import sys
import json
import importlib.util
import zipfile
import tempfile
import shutil

if getattr(sys, 'frozen', False):
    _base = os.path.dirname(os.path.abspath(sys.executable))
else:
    _base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

APPS_DIR = os.path.join(_base, 'data', 'hydroApps')
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


def _safe_icon_check(app_dir: str, icon_rel: str) -> bool:
    """校验 icon 位于 app 的 icons/ 子目录"""
    if '..' in icon_rel:
        return False
    full = os.path.join(app_dir, icon_rel)
    icons_dir = os.path.join(app_dir, 'icons')
    if not os.path.isfile(full):
        return False
    return os.path.abspath(full).startswith(os.path.abspath(icons_dir) + os.sep)


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
        icon_url = ""
        pk_id = pk.get("id", "")
        if m.get("icon") and pk_id and _safe_icon_check(d, m["icon"]):
            icon_url = f"/api/hydro/app_icon/{pk_id}/{m['icon']}"
        result.append({
            "name": name,
            "displayName": pk.get("displayName", name),
            "id": pk_id,
            "version": pk.get("version", ""),
            "icon": icon_url,
            "path": d,
        })
    return result


def get_app_path(name: str) -> str | None:
    d = os.path.join(APPS_DIR, name)
    if os.path.isdir(d) and os.path.isfile(os.path.join(d, '__init__.py')):
        return d
    return None


def _ensure_parent_packages(name: str):
    """Ensure all parent packages exist in sys.modules for a dotted module name."""
    parts = name.split('.')
    for i in range(1, len(parts)):
        parent = '.'.join(parts[:i])
        if parent not in sys.modules:
            pkg = type(sys)(parent)
            pkg.__path__ = []
            sys.modules[parent] = pkg


def _extract_app_lib(app_name: str):
    """解压 App 自带的 lib/*.whl 到 lib/ 目录，离线加载第三方库"""
    lib_dir = os.path.join(APPS_DIR, app_name, 'lib')
    if not os.path.isdir(lib_dir):
        return
    for fname in os.listdir(lib_dir):
        if not fname.endswith('.whl'):
            continue
        whl_path = os.path.join(lib_dir, fname)
        with zipfile.ZipFile(whl_path, 'r') as zf:
            for member in zf.namelist():
                if '.dist-info/' in member:
                    continue
                try:
                    zf.extract(member, lib_dir)
                except Exception:
                    pass
    if lib_dir not in sys.path:
        sys.path.insert(0, lib_dir)
    print(f'[extract_lib] {app_name}: lib_dir={lib_dir}, on_path={lib_dir in sys.path}', flush=True)
    for fname in os.listdir(lib_dir):
        if fname.endswith('.pth'):
            pth_path = os.path.join(lib_dir, fname)
            try:
                with open(pth_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        sub = line.strip()
                        if sub and not sub.startswith('#'):
                            sub_path = os.path.join(lib_dir, sub)
                            if os.path.isdir(sub_path) and sub_path not in sys.path:
                                sys.path.insert(0, sub_path)
            except Exception:
                pass


def load_module(name: str):
    path = get_app_path(name)
    if not path:
        return None
    # 清除所有相关子模块缓存，确保代码修改生效
    for mod_name in list(sys.modules.keys()):
        if mod_name == name or mod_name.startswith(name + '.'):
            del sys.modules[mod_name]
    _ensure_parent_packages(name)
    _extract_app_lib(name)
    spec = importlib.util.spec_from_file_location(name, os.path.join(path, '__init__.py'))
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def install(zip_path: str):
    """安装 HydroApp，返回 (name, error) 元组。成功时 error 为 None，失败时 name 为 None。"""
    try:
        tmp = tempfile.mkdtemp()
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(tmp)
        # 找到含 __init__.py 的应用目录
        items = os.listdir(tmp)
        app_dir = None
        if os.path.isfile(os.path.join(tmp, '__init__.py')):
            app_dir = tmp
        else:
            for item in items:
                candidate = os.path.join(tmp, item)
                if os.path.isdir(candidate) and os.path.isfile(os.path.join(candidate, '__init__.py')):
                    app_dir = candidate
                    break
        if not app_dir:
            shutil.rmtree(tmp)
            return None, "压缩包中未找到 HydroApp 目录"
        # 读取 manifest.json 中的 package.name 作为目录名
        manifest = _read_manifest(app_dir)
        valid, err = validate_manifest(manifest)
        if not valid:
            shutil.rmtree(tmp)
            return None, err
        pkg = manifest.get("package", {})
        target_name = pkg.get("id") or os.path.basename(app_dir)
        target_path = os.path.join(APPS_DIR, target_name)
        # 如果目标已存在则删除
        if os.path.isdir(target_path):
            shutil.rmtree(target_path)
        os.makedirs(APPS_DIR, exist_ok=True)
        shutil.move(app_dir, target_path)
        _extract_app_lib(target_name)
        if os.path.abspath(tmp) != os.path.abspath(app_dir):
            shutil.rmtree(tmp)
        return target_name, None
    except Exception as e:
        return None, str(e)


def uninstall(name: str) -> bool:
    d = os.path.join(APPS_DIR, name)
    if not os.path.isdir(d):
        return False
    shutil.rmtree(d)
    return True
