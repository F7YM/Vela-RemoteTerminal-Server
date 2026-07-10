"""Bilibili API 封装"""

import socket, requests

BILI_GENERATE = "https://passport.bilibili.com/x/passport-login/web/qrcode/generate"
BILI_POLL = "https://passport.bilibili.com/x/passport-login/web/qrcode/poll"
BILI_NAV = "https://api.bilibili.com/x/web-interface/nav"

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com/",
}


def _get(url, **kwargs):
    kwargs.setdefault("headers", _HEADERS)
    kwargs.setdefault("timeout", 5)
    return requests.get(url, **kwargs)


def _check_host(host: str) -> bool:
    """先检查 DNS 解析和端口可达性，避免 requests.get 卡死"""
    try:
        ip = socket.getaddrinfo(host, 443, socket.AF_INET, socket.SOCK_STREAM)
        return bool(ip)
    except Exception:
        return False


def parse_cookies(resp) -> dict:
    """从 response cookie jar 解析所有 cookie"""
    return {c.name: c.value for c in resp.cookies}


def generate_qr() -> dict | None:
    """请求二维码，返回 {url, qrcode_key} 或 None"""
    print("[HydroBili] generate_qr start", flush=True)
    if not _check_host("passport.bilibili.com"):
        print("[HydroBili] DNS resolve failed for passport.bilibili.com", flush=True)
        return None
    try:
        resp = _get(BILI_GENERATE, timeout=(5, 5))
        print(f"[HydroBili] BiliAPI /generate status={resp.status_code}", flush=True)
        data = resp.json()
        print(f"[HydroBili] BiliAPI /generate data code={data.get('code')}", flush=True)
        if data.get("code") == 0:
            return data["data"]
    except requests.exceptions.Timeout:
        print("[HydroBili] BiliAPI /generate timeout", flush=True)
    except Exception as e:
        import traceback
        print(f"[HydroBili] BiliAPI /generate error: {e}", flush=True)
        traceback.print_exc()
    return None


def poll_qr(qrcode_key: str) -> dict:
    """轮询扫码状态，返回 data 对象"""
    try:
        resp = _get(BILI_POLL, params={"qrcode_key": qrcode_key})
        result = resp.json()
        d = result.get("data", {})
        d["_resp"] = resp
        return d
    except Exception as e:
        return {"code": -1, "message": str(e)}


BILI_POPULAR = "https://api.bilibili.com/x/web-interface/popular"


def fetch_popular(cookies: dict) -> list:
    """获取热门推荐视频列表（备用）"""
    if not cookies:
        return []
    try:
        resp = _get(BILI_POPULAR, cookies=cookies)
        data = resp.json()
        if data.get("code") == 0:
            return data.get("data", {}).get("list", [])
    except Exception:
        pass
    return []


BILI_RCMD = "https://api.bilibili.com/x/web-interface/index/top/rcmd"


def fetch_recommend(cookies: dict) -> list:
    """获取个性化推荐视频列表（每次返回不同内容）"""
    if not cookies:
        return []
    try:
        import time
        params = {
            "fresh_type": 4,
            "ps": 12,
            "version": 1,
            "wts": int(time.time()),
        }
        resp = _get(BILI_RCMD, params=params, cookies=cookies)
        data = resp.json()
        if data.get("code") == 0:
            items = data.get("data", {}).get("item", [])
            # 只保留视频（过滤直播、番剧等）
            videos = []
            for item in items:
                if item.get("goto") == "av":
                    videos.append({
                        "title": item.get("title", ""),
                        "owner": item.get("owner", {}),
                        "stat": item.get("stat", {}),
                    })
            return videos
    except Exception:
        pass
    return []


def verify_cookies(cookies: dict) -> tuple:
    """验证 cookie，返回 (mid, uname) 或 (0, '')"""
    if not cookies:
        return 0, ""
    try:
        resp = _get(BILI_NAV, cookies=cookies)
        data = resp.json()
        if data.get("code") == 0 and data.get("data", {}).get("isLogin"):
            info = data["data"]
            return info.get("mid", 0), info.get("uname", "")
    except Exception:
        pass
    return 0, ""


BILI_CARD = "https://api.bilibili.com/x/web-interface/card"


def fetch_user_card(mid: int, cookies: dict) -> dict:
    """获取用户名片信息，返回 {face, name} 或 {}"""
    try:
        resp = _get(BILI_CARD, params={"mid": mid}, cookies=cookies)
        data = resp.json()
        if data.get("code") == 0:
            card = data.get("data", {}).get("card", {})
            return {"face": card.get("face", ""), "name": card.get("name", "")}
    except Exception:
        pass
    return {}
    """验证 cookie，返回 (mid, uname) 或 (0, '')"""
    if not cookies:
        return 0, ""
    try:
        resp = _get(BILI_NAV, cookies=cookies)
        data = resp.json()
        if data.get("code") == 0 and data.get("data", {}).get("isLogin"):
            info = data["data"]
            return info.get("mid", 0), info.get("uname", "")
    except Exception:
        pass
    return 0, ""
