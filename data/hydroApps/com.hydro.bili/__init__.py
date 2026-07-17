"""HydroBili — Bilibili 扫码登录"""

from .api import verify_cookies, fetch_recommend, fetch_user_card, fetch_video_info
from .pages import splash_page, landing_page, home_page, tabs_page, mine_page, video_detail
from .login import do_generate, do_poll

_cache = {
    "cookies": {},
    "mid": 0,
    "name": "",
    "qrcode_key": "",
    "qrcode_url": "",
    "videos": [],
}


def _restore(store: dict):
    """用客户端持久化的数据恢复会话"""
    cookies = store.get("bili_cookies", {})
    if cookies and not _cache["cookies"]:
        mid, name = verify_cookies(cookies)
        if mid:
            _cache["cookies"] = cookies
            _cache["mid"] = mid
            _cache["name"] = name


def _build_home(shape, refresh=False):
    """获取推荐视频并构建首页"""
    if refresh or not _cache.get("videos"):
        videos = fetch_recommend(_cache["cookies"]) if _cache["cookies"] else []
        _cache["videos"] = videos
        _cache["bids"] = [v.get("bvid", "") for v in videos]
    return home_page(shape, _cache["videos"], _cache["mid"], _cache["name"])


def _build_mine(shape):
    """获取用户名片并构建我的页面"""
    face, name = "", _cache["name"]
    if _cache["cookies"]:
        card = fetch_user_card(_cache["mid"], _cache["cookies"])
        face = card.get("face", "")
        if card.get("name"):
            name = card["name"]
    return mine_page(shape, face, name)


def page(shape, sw, sh, store=None):
    if not store or not store.get("bili_cookies"):
        return landing_page(shape, logged_in=False)
    return splash_page(shape)


def handle(action, params, shape=None, sw=0, sh=0):
    print(f"[HydroBili] handle action={action} params={list(params.keys()) if isinstance(params, dict) else 'N/A'}", flush=True)
    client_store = {}

    if isinstance(params, dict):
        raw = params.get("_store")
        if isinstance(raw, dict):
            client_store = raw
        elif isinstance(raw, str):
            import json
            try:
                client_store = json.loads(raw)
            except Exception:
                pass
    _restore(client_store)

    # 验证/恢复会话
    if action == "verify":
        if _cache["cookies"]:
            mid, name = verify_cookies(_cache["cookies"])
            if mid:
                _cache["mid"] = mid
                _cache["name"] = name
                return _build_home(shape, refresh=True).to_dict()
            _cache["cookies"] = {}
        return landing_page(shape).to_dict()

    # 刷新首页视频推荐
    elif action == "refresh":
        if _cache["cookies"]:
            mid, name = verify_cookies(_cache["cookies"])
            if mid:
                _cache["mid"] = mid
                _cache["name"] = name
                return _build_home(shape, refresh=True).to_dict()
        return {"toast": "登录已失效"}

    # Tab 切换页
    elif action == "tabs":
        return tabs_page(shape).to_dict()

    # 关闭 HydroApp
    elif action == "exit":
        return {"exit": True}

    # 首页（从详情页返回时命中此 action，使用缓存不刷新）
    elif action == "home":
        if _cache["cookies"]:
            return _build_home(shape).to_dict()
        return {"toast": "未登录"}

    # 我的
    elif action == "mine":
        if _cache["cookies"]:
            return _build_mine(shape).to_dict()
        return {"toast": "未登录"}

    # 视频详情
    elif action.startswith("video_detail_"):
        if not _cache["cookies"]:
            return {"toast": "未登录"}
        try:
            idx = int(action.split("_")[-1])
            bids = _cache.get("bids", [])
            if idx < 0 or idx >= len(bids):
                return {"toast": "视频不存在"}
            bvid = bids[idx]
        except (ValueError, IndexError):
            return {"toast": "视频不存在"}
        video = fetch_video_info(bvid, _cache["cookies"])
        if not video:
            return {"toast": "获取视频信息失败"}
        return video_detail(shape, video).to_dict()

    # 生成二维码
    elif action == "generate":
        result = do_generate(shape)
        if isinstance(result, dict) and "_qrcode_key" in result:
            _cache["qrcode_key"] = result.pop("_qrcode_key")
            _cache["qrcode_url"] = result.pop("_qrcode_url", "")
        return result

    # 取消扫码
    elif action == "cancel":
        _cache["qrcode_key"] = ""
        _cache["qrcode_url"] = ""
        if _cache["cookies"]:
            return _build_home(shape).to_dict()
        return landing_page(shape).to_dict()

    # 轮询扫码（由 tick 触发）
    elif action == "tick":
        key = _cache.get("qrcode_key")
        if not key:
            return {"toast": ""}
        result = do_poll(shape, key, _cache.get("qrcode_url", ""))
        store = result.get("_store", {})
        if store.get("bili_cookies"):
            _cache["cookies"] = store["bili_cookies"]
            _cache["mid"] = result.get("_mid") or 0
            _cache["name"] = result.get("_name") or ""
            _cache["qrcode_key"] = ""
            r = _build_home(shape, refresh=True).to_dict()
            r["_store"] = store
            r["toast"] = "登录成功"
            return r
        return result

    # 退出
    elif action == "logout":
        _cache["cookies"] = {}
        _cache["mid"] = 0
        _cache["name"] = ""
        _cache["qrcode_key"] = ""
        _cache["qrcode_url"] = ""
        result = landing_page(shape).to_dict()
        result["_clearStore"] = ["bili_cookies"]
        return result

    return {"toast": f"未知操作: {action}"}
