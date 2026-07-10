"""UI 页面构建"""

import urllib.parse
from hydroApp import Page, Text, Button, Image, safe_area_style

_base_url = ""


def _qr_img_src(url: str) -> str:
    if _base_url:
        return _base_url + '/api/hydro/qr_image?data=' + urllib.parse.quote(url)
    return 'https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=' + urllib.parse.quote(url)


def _format_num(n: int) -> str:
    if n >= 10000:
        return f"{n / 10000:.1f}万"
    return str(n)


def landing_page(shape, logged_in=False, mid=0, name=""):
    """未登录时的落地页 / 已登录则跳转到首页"""
    if logged_in:
        return home_page(shape, [], mid, name)
    return Page(
        Text("HydroBili", fs=28, clr="#ffffff", fw="bold"),
        Text("Bilibili 扫码登录", fs=14, clr="#aaaaaa", mt=4),
        Button("扫码登录", action="generate", bg="#2196F3", w=240, h=50, br=25, mt=20),
        content_style=safe_area_style(shape),
    )


def home_page(shape, videos, mid, name):
    """首页：可点击标题 + 推荐视频列表"""
    items = [
        Button("首页", action="tabs", bg="transparent", h=30, mt=6, fs=22, fw="bold"),
    ]
    if not videos:
        items.append(Text("加载推荐中...", fs=14, clr="#aaaaaa", mt=20))
    else:
        for v in videos:
            title = v.get("title", "")
            owner = v.get("owner", {}).get("name", "未知")
            view = _format_num(v.get("stat", {}).get("view", 0))
            items.append(Text(title, fs=14, clr="#ffffff", mt=10))
            items.append(Text(f"{owner} · {view}播放", fs=12, clr="#888888", mt=2))
    return Page(*items, content_style=safe_area_style(shape))


def tabs_page(shape):
    """Tab 切换页"""
    return Page(
        Text("切换页面", fs=18, clr="#ffffff", fw="bold", mt=10),
        Button("  首页  ", action="home", bg="#2196F3", w=200, h=44, br=22, mt=20),
        Button("  我的  ", action="mine", bg="#555555", w=200, h=44, br=22, mt=12),
        content_style=safe_area_style(shape),
    )


def mine_page(shape, mid, name):
    """我的页面：用户信息 + 退出"""
    return Page(
        Button("首页", action="home", bg="transparent", h=30, mt=6, fs=22, fw="bold"),
        Text("已登录", fs=24, clr="#4CAF50", fw="bold", mt=10),
        Text(f"UID: {mid}", fs=16, clr="#ffffff", mt=4),
        Text(name, fs=18, clr="#ffffff", mt=2),
        Button("退出登录", action="logout", bg="#f44336", w=200, h=44, br=22, mt=20),
        content_style=safe_area_style(shape),
    )


def qr_scan(shape, url, status="等待扫码..."):
    """扫码页面"""
    color = "#4CAF50" if "确认" in status else "#aaaaaa"
    return Page(
        Button("取消", action="cancel", bg="#555555", w=120, h=40, br=20),
        Text("请使用 Bilibili App 扫码", fs=16, clr="#ffffff", mt=8),
        Image(src=_qr_img_src(url), w=200, h=200, br=12, mt=8),
        Text(status, fs=14, clr=color, mt=8),
        content_style=safe_area_style(shape),
    )


def expired(shape):
    """二维码已过期"""
    return Page(
        Text("二维码已过期", fs=20, clr="#f44336", fw="bold"),
        Button("重新生成", action="generate", bg="#2196F3", w=240, h=50, br=25, mt=20),
        content_style=safe_area_style(shape),
    )


def success(shape, mid, name):
    """登录成功"""
    return Page(
        Text("登录成功!", fs=24, clr="#4CAF50", fw="bold"),
        Text(f"UID: {mid}", fs=16, clr="#ffffff", mt=4),
        Text(name, fs=18, clr="#ffffff", mt=2),
        Text("Cookie 已存储到手表", fs=14, clr="#aaaaaa", mt=8),
        content_style=safe_area_style(shape),
    )
