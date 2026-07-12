"""UI 页面构建"""

import urllib.parse
from hydroApp import Page, Text, Button, Image, Row, Column, safe_area_style

_base_url = ""


def _qr_img_src(url: str) -> str:
    return '/api/hydro/qr_image?data=' + urllib.parse.quote(url)


def _format_num(n: int) -> str:
    if n >= 10000:
        return f"{n / 10000:.1f}万"
    return str(n)


def splash_page(shape):
    return Page(
        Image(src=_icon("home"), w=120, h=120),
        content_style=safe_area_style(shape) + "; justify-content: center; align-items: center",
    )


def landing_page(shape, logged_in=False, mid=0, name=""):
    """未登录时的落地页 / 已登录则跳转到首页"""
    if logged_in:
        return home_page(shape, [], mid, name)
    return Page(
        Text("HydroBili", fs=28, clr="#ffffff", fw="bold"),
        Text("Bilibili 扫码登录", fs=16, clr="#aaaaaa", mt=6),
        Button("扫码登录", action="generate", bg="#2196F3", w=240, h=50, br=25, mt=24, fs=18),
        content_style=safe_area_style(shape),
    )


_IconData = {
    "refresh": "ic_fluent_arrow_clockwise_24_filled.png",
    "home": "ic_fluent_home_24_filled.png",
    "person": "ic_fluent_person_24_filled.png",
}

def _icon(name: str) -> str:
    base = _base_url or ''
    return base + '/hydro-icons/com.hydro.bili/' + _IconData[name]


def home_page(shape, videos, mid, name):
    """首页：标题 + 刷新按钮 + 推荐视频列表"""
    items = [
        Row(
            Button("首页", action="tabs", bg="transparent", h=48, fs=30, fw="bold", mr=20),
            Button(action="refresh", image=_icon("refresh"), bg="transparent", h=48, w=48),
            props={"jc": "center", "ai": "center"},
        ),
    ]
    if not videos:
        items.append(Text("加载推荐中...", fs=22, clr="#aaaaaa", mt=20))
    else:
        for i, v in enumerate(videos):
            title = v.get("title", "")
            owner = v.get("owner", {}).get("name", "未知")
            view = _format_num(v.get("stat", {}).get("view", 0))
            pic = v.get("pic", "")
            if pic and not pic.startswith("http"):
                pic = "http:" + pic
            btn_text = title + "\n" + owner + " · " + view + "播放"
            if pic:
                items.append(Row(
                    Image(src=pic + "@120w_80h", w=120, h=80, br=8, of="cover"),
                    Button(btn_text, action=f"video_detail_{i}", bg="transparent", fs=14, ta="left"),
                    props={"jc": "flex-start", "ai": "flex-start"},
                ))
            else:
                items.append(Button(btn_text, action=f"video_detail_{i}", bg="transparent", fs=14, ta="left", mt=10))
    return Page(*items, content_style=safe_area_style(shape))


def tabs_page(shape):
    """Tab 切换页"""
    return Page(
        Text("切换页面", fs=28, clr="#ffffff", fw="bold", mt=10),
        Row(
            Column(
                Image(src=_icon("home"), w=80, h=80),
                Text("首页", fs=22, clr="#ffffff", mt=8),
                a="home",
                props={"ai": "center"},
                mr=50,
            ),
            Column(
                Image(src=_icon("person"), w=80, h=80),
                Text("我的", fs=22, clr="#ffffff", mt=8),
                a="mine",
                props={"ai": "center"},
                mr=50,
            ),
            Column(
                Text("关闭", fs=22, clr="#ffffff"),
                a="exit",
                props={"ai": "center", "jc": "center"},
            ),
            props={"jc": "center", "ai": "center"},
        ),
        content_style=safe_area_style(shape),
    )


def mine_page(shape, face, name):
    """我的页面：头像 + 昵称横向并列"""
    items = [
        Button("我的", action="tabs", bg="transparent", h=40, mt=8, fs=30, fw="bold"),
    ]
    if face:
        items.append(Row(
            Image(src=face, w=56, h=56, br=28),
            Text(name, fs=24, clr="#ffffff", ml=14),
            props={"ai": "center", "jc": "flex-start"},
        ))
    else:
        items.append(Text(name, fs=24, clr="#ffffff", mt=4))
    items.append(Button("退出登录", action="logout", bg="#f44336", w=220, h=48, br=24, mt=24, fs=22))
    return Page(*items, content_style=safe_area_style(shape))


def video_detail(shape, video):
    """视频详情页"""
    if not video:
        return Page(Text("视频不存在", fs=20, clr="#f44336", mt=20), content_style=safe_area_style(shape))
    title = video.get("title", "")
    pic = video.get("pic", "")
    owner = video.get("owner", {})
    stat = video.get("stat", {})
    desc = video.get("desc", "")
    if pic and not pic.startswith("http"):
        pic = "http:" + pic
    items = [
        Button("返回", action="home", bg="transparent", h=40, mt=8, fs=22, fw="bold"),
    ]
    if pic:
        items.append(Image(src=pic + "@466w_260h", w=466, h=260, of="cover"))
    items.append(Text(title, fs=22, clr="#ffffff", fw="bold", mt=10))
    items.append(Row(
        Image(src=owner.get("face", "") + "@40w_40h", w=40, h=40, br=20) if owner.get("face") else None,
        Text(owner.get("name", ""), fs=16, clr="#ffffff", ml=10),
        props={"ai": "center", "jc": "flex-start"},
    ))
    items.append(Text(f"{_format_num(stat.get('view', 0))}播放 · {_format_num(stat.get('danmaku', 0))}弹幕 · {_format_num(stat.get('like', 0))}点赞", fs=14, clr="#ffffff", mt=10))
    if desc:
        items.append(Text(desc, fs=14, clr="#ffffff", mt=10))
    return Page(*items, content_style=safe_area_style(shape))


def qr_scan(shape, url, status="等待扫码..."):
    """扫码页面"""
    color = "#4CAF50" if "确认" in status else "#aaaaaa"
    return Page(
        Button("取消", action="cancel", bg="#555555", w=120, h=40, br=20, fs=16),
        Text("请使用 Bilibili App 扫码", fs=18, clr="#ffffff", mt=10),
        Image(src=_qr_img_src(url), w=200, h=200, br=12, mt=10),
        Text(status, fs=16, clr=color, mt=10),
        content_style=safe_area_style(shape),
    )


def expired(shape):
    """二维码已过期"""
    return Page(
        Text("二维码已过期", fs=22, clr="#f44336", fw="bold"),
        Button("重新生成", action="generate", bg="#2196F3", w=240, h=50, br=25, mt=24, fs=18),
        content_style=safe_area_style(shape),
    )


def success(shape, mid, name):
    """登录成功"""
    return Page(
        Text("登录成功!", fs=26, clr="#4CAF50", fw="bold"),
        Text(f"UID: {mid}", fs=18, clr="#ffffff", mt=6),
        Text(name, fs=20, clr="#ffffff", mt=4),
        Text("Cookie 已存储到手表", fs=16, clr="#aaaaaa", mt=8),
        content_style=safe_area_style(shape),
    )
