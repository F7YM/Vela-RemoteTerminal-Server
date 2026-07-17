"""扫码登录流程"""

from .api import generate_qr, poll_qr, parse_cookies, verify_cookies
from .pages import landing_page, qr_scan, expired, success


def do_generate(shape):
    """生成二维码"""
    print("[HydroBili] do_generate start", flush=True)
    d = generate_qr()
    print(f"[HydroBili] generate_qr result: {d is not None}", flush=True)
    if not d:
        return {"toast": "获取二维码失败"}
    print(f"[HydroBili] qr url len={len(d['url'])} key_len={len(d['qrcode_key'])}", flush=True)
    obj = qr_scan(shape, d["url"])
    result = obj.to_dict()
    print(f"[HydroBili] qr_scan dict keys={list(result.keys())}", flush=True)
    result["tick"] = 2000
    result["_qrcode_key"] = d["qrcode_key"]
    result["_qrcode_url"] = d["url"]
    return result


def do_poll(shape, qrcode_key, qrcode_url=""):
    """轮询扫码状态"""
    data = poll_qr(qrcode_key)
    code = data.get("code", -1)
    print(f"[HydroBili] poll code={code}", flush=True)

    if code == 86101:
        # 二维码未扫描，无需刷新 UI，继续轮询
        return {"tick": 2000}

    if code == 86090:
        # 已扫描，等待确认，更新状态文本（保持原 QR URL 不变）
        url = qrcode_url or f"https://passport.bilibili.com/h5-app/passport/login/scan?navhide=1&qrcode_key={qrcode_key}"
        obj = qr_scan(shape, url, "请在手机上确认登录")
        result = obj.to_dict()
        result["tick"] = 2000
        return result

    if code == 86038:
        return expired(shape).to_dict()

    if code == 0:
        resp = data.get("_resp")
        cookies = parse_cookies(resp) if resp else {}
        print(f"[HydroBili] poll success, cookies={list(cookies.keys())}", flush=True)
        if not cookies:
            return {"toast": "登录失败：未能获取 Cookie"}
        mid, name = verify_cookies(cookies)
        print(f"[HydroBili] verify_cookies mid={mid}", flush=True)
        if not mid:
            return {"toast": "登录失败：Cookie 验证未通过"}
        obj = success(shape, mid, name)
        result = obj.to_dict()
        result["_store"] = {"bili_cookies": cookies}
        result["_mid"] = mid
        result["_name"] = name
        return result

    return {"toast": f"未知状态 ({code})"}
