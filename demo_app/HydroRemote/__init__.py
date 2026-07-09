"""HydroRemote — 远程控制演示 HydroApp"""

from hydroApp import Page, Text, Button, Row, Column, Switch

_counter = 0


def page(shape, sw, sh):
    now = __import__("datetime").datetime.now().strftime("%H:%M:%S")
    return Page(
        Text("远程控制面板", fs=28, clr="#ffffff", fw="bold"),
        Text(f"{now}  |  {shape} {sw}x{sh}", fs=11, clr="#666666", mt=4),

        Row(
            Button("截图", action="screenshot", fs=16, bg="#2196F3", w=95, h=44, br=22, mr=6),
            Button("锁屏", action="lock", fs=16, bg="#FF9800", w=95, h=44, br=22, mr=6),
            Button("重启", action="reboot", fs=16, bg="#4CAF50", w=95, h=44, br=22),
            mt=16,
        ),

        Row(
            Text(f"点击次数: {_counter}", fs=20, clr="#ffffff", mr=12),
            Button("+1", action="inc", fs=18, bg="#333333", w=56, h=40, br=20, mr=6),
            Button("重置", action="reset", fs=14, bg="#555555", w=70, h=40, br=20),
            mt=12,
        ),

        Column(
            Button("▸ 系统监控", action="goto_monitor", fs=18, bg="#222222",
                   w=280, h=50, br=12, mt=8),
            Button("▸ 关于", action="goto_about", fs=18, bg="#222222",
                   w=280, h=50, br=12, mt=4),
        ),

        Switch(chk=False, action="toggle_auto", mt=16),
        Text("每 5 秒自动刷新", fs=14, clr="#aaaaaa"),
        refresh_interval=0,
    )


def monitor_page():
    import random
    cpu = random.randint(10, 90)
    mem = random.randint(20, 95)
    c_color = "#4CAF50" if cpu < 60 else ("#FF9800" if cpu < 80 else "#f44336")
    m_color = "#4CAF50" if mem < 60 else ("#FF9800" if mem < 80 else "#f44336")

    return Page(
        Button("← 返回", action="goto_home", fs=16, bg="#222222", w=160, h=44, br=22, mb=12),
        Text("系统监控", fs=24, clr="#ffffff", fw="bold", mb=8),

        Row(
            Text("CPU:", fs=18, clr="#aaaaaa", mr=8),
            Text(f"{cpu}%", fs=32, clr=c_color, fw="bold"),
        ),
        Row(
            Text("内存:", fs=18, clr="#aaaaaa", mr=8),
            Text(f"{mem}%", fs=32, clr=m_color, fw="bold"),
            mt=4,
        ),

        Switch(chk=True, action="monitor_auto", mt=16),
        Text("每 2 秒自动刷新", fs=14, clr="#aaaaaa"),
        refresh_interval=2000,
    )


def about_page():
    return Page(
        Button("← 返回", action="goto_home", fs=16, bg="#222222", w=160, h=44, br=22, mb=12),
        Text("关于 HydroRemote", fs=22, clr="#ffffff", fw="bold"),
        Text("版本 1.0.0", fs=14, clr="#aaaaaa", mt=4),
        Text("基于 hydroApp 构建的远程控制演示应用", fs=12, clr="#666666", mt=8),
        Text("支持截图、锁屏、重启、系统监控", fs=12, clr="#666666"),
        refresh_interval=0,
    )


def handle(action, params):
    global _counter
    if action == "inc":
        _counter += 1
    elif action == "reset":
        _counter = 0
    elif action == "screenshot":
        return {"toast": "截图功能开发中"}
    elif action == "lock":
        return {"toast": "锁屏功能开发中"}
    elif action == "reboot":
        return {"toast": "重启功能待确认"}
    elif action == "goto_monitor":
        obj = monitor_page()
        return obj.to_dict() if hasattr(obj, "to_dict") else obj
    elif action == "goto_about":
        obj = about_page()
        return obj.to_dict() if hasattr(obj, "to_dict") else obj
    elif action == "goto_home":
        obj = page("", 0, 0)
        return obj.to_dict() if hasattr(obj, "to_dict") else obj
    elif action == "toggle_auto":
        obj = page("", 0, 0)
        d = obj.to_dict() if hasattr(obj, "to_dict") else obj
        d["ri"] = 5000
        return d
    elif action == "monitor_auto":
        return {"ri": 2000}

    # Default: return current page state
    obj = page("", 0, 0)
    return obj.to_dict() if hasattr(obj, "to_dict") else obj
