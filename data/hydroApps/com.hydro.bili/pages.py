"""UI 页面构建"""

from hydroApp import Page, Text, Button, Image, QRCode, Row, Column, ProgressText, safe_area_style

_base_url = ""


def _format_num(n: int) -> str:
    if n >= 10000:
        return f"{n / 10000:.1f}万"
    return str(n)


def _fmt_duration(n: int) -> str:
    m = n // 60
    s = n % 60
    return f"{m:02d}:{s:02d}"


def splash_page(shape):
    return Page(
        Image(src=_icon("bili"), w=120, h=120),
        content_style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 100%",
    )


def landing_page(shape, logged_in=False, mid=0, name=""):
    """未登录时的落地页 / 已登录则跳转到首页"""
    if logged_in:
        return home_page(shape, [], mid, name)
    return Page(
        Column(
            Text("HydroBili", fs=28, clr="#ffffff", fw="bold"),
            Text("Bilibili 扫码登录", fs=16, clr="#aaaaaa", mt=6),
            Button("扫码登录", action="generate", bg="#2196F3", w=240, h=50, br=25, mt=24, fs=18),
        ),
        content_style=safe_area_style(shape),
    )


_IconData = {
    "refresh": "ic_fluent_arrow_clockwise_24_filled.png",
    "back": "ic_fluent_arrow_left_24_filled.png",
    "home": "ic_fluent_home_24_filled.png",
    "person": "ic_fluent_person_24_filled.png",
    "bili": "HydroBili.png",
    "audio_play": "ic_fluent_play_24_filled.png",
    "audio_pause": "ic_fluent_pause_24_filled.png",
    "audio_vol_down": "ic_fluent_subtract_24_filled.png",
    "audio_vol_up": "ic_fluent_add_24_filled.png",
    "ai_summary": "ai-summary.png",
}

def _icon(name: str) -> str:
    base = _base_url or ''
    return base + '/hydro-icons/com.hydro.bili/' + _IconData[name]


_ActionIcons = {
    "like": "like.png",
    "liked": "liked.png",
    "coin": "coin.png",
    "coined": "coined.png",
    "star": "star.png",
    "stared": "stared.png",
}


def _action_icon(name: str) -> str:
    base = _base_url or ''
    return base + '/hydro-icons/com.hydro.bili/' + _ActionIcons[name]


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
            if pic:
                items.append(Row(
                    Image(src=pic + "@120w_80h", w=120, h=80, br=8, of="cover"),
                    Button(title, action=f"video_detail_{i}", bg="transparent", fs=13, ta="left"),
                    props={"jc": "flex-start", "ai": "flex-start"},
                    mb=8,
                ))
            else:
                items.append(Button(title, action=f"video_detail_{i}", bg="transparent", fs=13, ta="left", mt=10, mb=8))
    cs = safe_area_style(shape)
    if shape == "circle":
        cs += "; padding-left: 60px; padding-right: 60px; padding-bottom: 42px"
    return Page(Column(*items), content_style=cs)


def tabs_page(shape):
    """Tab 切换页"""
    return Page(
        Column(
            Text("切换页面", fs=28, clr="#ffffff", fw="bold", mt=10),
            Row(
                Column(
                    Image(src=_icon("home"), w=60, h=60),
                    Text("首页", fs=18, clr="#ffffff", mt=6),
                    a="home",
                    props={"ai": "center"},
                    mr=40,
                ),
                Column(
                    Image(src=_icon("person"), w=60, h=60),
                    Text("我的", fs=18, clr="#ffffff", mt=6),
                    a="mine",
                    props={"ai": "center"},
                    mr=40,
                ),
                props={"jc": "center", "ai": "center"},
            ),
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
    return Page(Column(*items), content_style=safe_area_style(shape))


def video_detail(shape, video, liked=False, coined=False, stared=False):
    """视频详情页"""
    if not video:
        return Page(Text("视频不存在", fs=20, clr="#f44336", mt=20), content_style=safe_area_style(shape))
    title = video.get("title", "")
    pic = video.get("pic", "")
    owner = video.get("owner", {})
    stat = video.get("stat", {})
    desc = video.get("desc", "")
    bvid = video.get("bvid", "")
    if pic and not pic.startswith("http"):
        pic = "http:" + pic
    items = [
        Button("", action="home", image=_icon("back"), bg="transparent", h=48, w=48, mt=8),
    ]
    if pic:
        items.append(Image(src=pic + "@466w_260h", w=466, h=260, of="cover"))
    items.append(Text(title, fs=26, clr="#ffffff", fw="bold", mt=10))
    items.append(Row(
        Image(src=owner.get("face", "") + "@40w_40h", w=40, h=40, br=20) if owner.get("face") else None,
        Text(owner.get("name", ""), fs=20, clr="#ffffff", ml=10),
        props={"ai": "center", "jc": "flex-start"},
    ))
    items.append(Text(f"{_format_num(stat.get('view', 0))}播放 · {_format_num(stat.get('danmaku', 0))}弹幕", fs=18, clr="#ffffff", mt=10))
    items.append(Row(
        Column(
            Button("", action="like", image=_action_icon("liked" if liked else "like"), bg="transparent", h=64, w=64, data={"bvid": bvid}, img_size=64, of="fill"),
            Text(_format_num(stat.get('like', 0)), fs=14, clr="#ffffff", mt=2),
            props={"ai": "center"},
            mr=20,
        ),
        Column(
            Button("", action="coin", image=_action_icon("coined" if coined else "coin"), bg="transparent", h=64, w=64, data={"bvid": bvid}, img_size=64, of="fill"),
            Text(_format_num(stat.get('coin', 0)), fs=14, clr="#ffffff", mt=2),
            props={"ai": "center"},
            mr=20,
        ),
        Column(
            Button("", action="favorite", image=_action_icon("stared" if stared else "star"), bg="transparent", h=64, w=64, data={"bvid": bvid}, img_size=64, of="fill"),
            Text(_format_num(stat.get('favorite', 0)), fs=14, clr="#ffffff", mt=2),
            props={"ai": "center"},
        ),
        props={"jc": "center", "ai": "center"},
        mt=8,
    ))
    items.append(Button("听视频", action="audio", bg="#FF6699", w=200, h=48, br=24, mt=10, fs=20, data={"bvid": bvid}))
    items.append(Button("", action="ai_summary", image=_icon("ai_summary"), bg="#7B1FA2", w=200, h=48, br=24, mt=10, img_size=36, data={"bvid": bvid}))
    if desc:
        items.append(Text(desc, fs=22, clr="#ffffff", mt=10, mb=30))
    else:
        items.append(Text("", fs=1, mb=30))
    cs = safe_area_style(shape)
    if shape == "circle":
        cs += "; padding-left: 60px; padding-right: 60px; padding-bottom: 46px"
    return Page(Column(*items), content_style=cs)


def audio_player_page(shape, meta, playing=False, bvid=""):
    """音频播放器页面"""
    if not meta:
        return Page(Text("无法加载音频", fs=20, clr="#f44336", mt=20), content_style=safe_area_style(shape))
    play_icon = "audio_pause" if playing else "audio_play"
    total = meta.get("duration", 0)
    init_prog = "00:00 / " + _fmt_duration(total)
    cs = safe_area_style(shape)
    if shape == "circle":
        cs += "; padding-left: 60px; padding-right: 60px"
    return Page(
        Column(
            Button("", action="_audiostop", image=_icon("back"), bg="transparent", h=48, w=48, mt=8),
            Text(meta.get("title", ""), fs=24, clr="#ffffff", fw="bold", mt=20, ta="center"),
            Text(meta.get("owner", ""), fs=18, clr="#aaaaaa", mt=4, ta="center"),
            ProgressText(init_prog, fs=22, clr="#ffffff", mt=20),
            Row(
                Button("", action="_audiovoldown", image=_icon("audio_vol_down"), bg="transparent", h=56, w=56, img_size=56),
                Button("", action="_audioplaypause", image=_icon(play_icon), bg="transparent", h=72, w=72, img_size=72, ml=20, mr=20),
                Button("", action="_audiovolup", image=_icon("audio_vol_up"), bg="transparent", h=56, w=56, img_size=56),
                props={"jc": "center", "ai": "center"},
                mt=30,
            ),
        ),
        content_style=cs,
    )


def qr_scan(shape, url, status="等待扫码..."):
    """扫码页面"""
    color = "#4CAF50" if "确认" in status else "#aaaaaa"
    return Page(
        Column(
            Button("", action="cancel", image=_icon("back"), bg="#555555", w=48, h=48, br=24),
            Text("请使用 Bilibili App 扫码", fs=20, clr="#ffffff", fw="bold", mt=12),
            QRCode(data=url, w=280, h=280, mt=14),
            Text(status, fs=18, clr=color, mt=12),
        ),
        content_style=safe_area_style(shape),
    )


def expired(shape):
    """二维码已过期"""
    return Page(
        Column(
            Text("二维码已过期", fs=22, clr="#f44336", fw="bold"),
            Button("重新生成", action="generate", bg="#2196F3", w=240, h=50, br=25, mt=24, fs=18),
        ),
        content_style=safe_area_style(shape),
    )


def success(shape, mid, name):
    """登录成功"""
    return Page(
        Column(
            Text("登录成功!", fs=26, clr="#4CAF50", fw="bold"),
            Text(f"UID: {mid}", fs=18, clr="#ffffff", mt=6),
            Text(name, fs=20, clr="#ffffff", mt=4),
            Text("Cookie 已存储到手表", fs=16, clr="#aaaaaa", mt=8),
        ),
        content_style=safe_area_style(shape),
    )


def ai_summary_page(shape, data, bvid=""):
    """AI 摘要页面"""
    btn_back = Button("", action="ai_summary_back", image=_icon("back"), bg="transparent", h=48, w=48, mt=8, data={"bvid": bvid})

    if not data:
        body = [Text("无法加载", fs=20, clr="#f44336", mt=20)]
    elif data.get("code") == -1:
        body = [Text("该视频不支持 AI 摘要", fs=20, clr="#aaaaaa", mt=20)]
    elif data.get("code") == 1:
        body = [Text("暂无摘要（未识别语音）", fs=20, clr="#aaaaaa", mt=20)]
    else:
        model = data.get("model_result", {})
        summary = model.get("summary", "")
        outline = model.get("outline", [])
        body = [Text("AI 摘要", fs=26, clr="#ffffff", fw="bold", mt=4, ta="center")]
        if summary:
            body.append(Text(summary, fs=18, clr="#ffffff", mt=6))
        for sec in outline:
            t = sec.get("title", "")
            ts = sec.get("timestamp", 0)
            if t:
                body.append(Text(f"[{ts//60}:{ts%60:02d}] {t}", fs=16, clr="#cccccc", mt=8))
            for pt in sec.get("part_outline", []):
                c, pts = pt.get("content", ""), pt.get("timestamp", 0)
                if c:
                    body.append(Text(f"  • {c}", fs=15, clr="#999999", mt=2))

    content = Column(btn_back, *body, props={"ai": "center"})
    cs = safe_area_style(shape)
    if shape == "circle":
        cs += "; padding-left: 60px; padding-right: 60px; padding-bottom: 46px"
    return Page(content, content_style=cs)
