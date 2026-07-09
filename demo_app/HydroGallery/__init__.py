"""HydroGallery — 组件展示 Demo"""

from hydroApp import Page, Text, Button, Row, Column, Switch

_counter = {"val": 0}


def page(shape, sw, sh):
    s = 1.4 if shape == "pill-shaped" else 1.0
    return Page(
        Text("HydroGallery", fs=int(28*s), clr="#ffffff", fw="bold"),
        Text("HydroApp 组件展示", fs=int(14*s), clr="#888888", mt=4, mb=int(12*s)),

        Column(
            Button("▸ 文字组件", action="goto_text",    fs=int(16*s), bg="#222222", w=int(280*s), h=int(50*s), br=12, mb=int(6*s)),
            Button("▸ 按钮组件", action="goto_btn",     fs=int(16*s), bg="#222222", w=int(280*s), h=int(50*s), br=12, mb=int(6*s)),
            Button("▸ 布局组件", action="goto_layout",  fs=int(16*s), bg="#222222", w=int(280*s), h=int(50*s), br=12, mb=int(6*s)),
            Button("▸ 交互组件", action="goto_interact",fs=int(16*s), bg="#222222", w=int(280*s), h=int(50*s), br=12),
        ),

        Text("v1.0.0  |  6 个组件类型", fs=int(12*s), clr="#555555", mt=int(16*s)),

        Button("退出 HydroApp", action="exit", fs=int(16*s), bg="#f44336", w=int(200*s), h=int(44*s), br=22, mt=int(16*s)),
        refresh_interval=0,
    )


def text_page(shape, sw, sh):
    s = 1.4 if shape == "pill-shaped" else 1.0
    return Page(
        Button("← 返回", action="goto_home", fs=int(16*s), bg="#222222", w=int(160*s), h=int(44*s), br=22, mb=int(12*s)),
        Text("文字组件 Text", fs=int(22*s), clr="#ffffff", fw="bold", mb=int(8*s)),

        Text("字体大小 28px",           fs=int(28*s), clr="#ffffff"),
        Text("字体大小 20px 灰色",      fs=int(20*s), clr="#aaaaaa"),
        Text("字体大小 14px 暗灰色",    fs=int(14*s), clr="#666666", mb=int(8*s)),

        Text("绿色粗体", fs=int(18*s), clr="#4CAF50", fw="bold"),
        Text("橙色文本", fs=int(18*s), clr="#FF9800"),
        Text("红色文本", fs=int(18*s), clr="#f44336"),
        Text("蓝色文本", fs=int(18*s), clr="#2196F3"),
        refresh_interval=0,
    )


def btn_page(shape, sw, sh):
    s = 1.4 if shape == "pill-shaped" else 1.0
    return Page(
        Button("← 返回", action="goto_home", fs=int(16*s), bg="#222222", w=int(160*s), h=int(44*s), br=22, mb=int(12*s)),
        Text("按钮组件 Button", fs=int(22*s), clr="#ffffff", fw="bold", mb=int(8*s)),

        Button("默认蓝色",   action="demo_toast", fs=int(18*s), bg="#2196F3", w=int(260*s), h=int(50*s), br=25, mb=int(6*s)),
        Button("绿色按钮",   action="demo_toast", fs=int(18*s), bg="#4CAF50", w=int(260*s), h=int(50*s), br=10, mb=int(6*s)),
        Button("红色大按钮", action="demo_toast", fs=int(22*s), bg="#f44336", w=int(260*s), h=int(60*s), br=8,  mb=int(6*s)),
        Button("小按钮",     action="demo_toast", fs=int(14*s), bg="#333333", w=int(120*s), h=int(40*s), br=20, mb=int(6*s)),
        Row(
            Button("并排1", action="demo_toast", fs=int(16*s), bg="#555555", w=int(120*s), h=int(44*s), br=22, mr=int(6*s)),
            Button("并排2", action="demo_toast", fs=int(16*s), bg="#555555", w=int(120*s), h=int(44*s), br=22),
        ),
        refresh_interval=0,
    )


def layout_page(shape, sw, sh):
    s = 1.4 if shape == "pill-shaped" else 1.0
    return Page(
        Button("← 返回", action="goto_home", fs=int(16*s), bg="#222222", w=int(160*s), h=int(44*s), br=22, mb=int(12*s)),
        Text("布局组件 Row / Column", fs=int(22*s), clr="#ffffff", fw="bold", mb=int(8*s)),

        Text("水平排列 (Row):", fs=int(14*s), clr="#aaaaaa", mb=int(4*s)),
        Row(
            Button("A", action="demo_toast", fs=int(14*s), bg="#2196F3", w=int(60*s),  h=int(44*s), br=12, mr=int(6*s)),
            Button("B", action="demo_toast", fs=int(14*s), bg="#4CAF50", w=int(60*s),  h=int(44*s), br=12, mr=int(6*s)),
            Button("C", action="demo_toast", fs=int(14*s), bg="#FF9800", w=int(60*s),  h=int(44*s), br=12),
        ),

        Text("垂直排列 (Column):", fs=int(14*s), clr="#aaaaaa", mt=int(8*s), mb=int(4*s)),
        Column(
            Button("上", action="demo_toast", fs=int(14*s), bg="#333333", w=int(200*s), h=int(40*s), br=8, mb=int(4*s)),
            Button("中", action="demo_toast", fs=int(14*s), bg="#333333", w=int(200*s), h=int(40*s), br=8, mb=int(4*s)),
            Button("下", action="demo_toast", fs=int(14*s), bg="#333333", w=int(200*s), h=int(40*s), br=8),
        ),

        Text("嵌套示例:", fs=int(14*s), clr="#aaaaaa", mt=int(8*s), mb=int(4*s)),
        Row(
            Column(
                Text("左列", fs=int(14*s), clr="#ffffff"),
                Button("X", action="demo_toast", fs=int(12*s), bg="#f44336", w=int(60*s), h=int(36*s), br=8, mt=int(4*s)),
            ),
            Column(
                Text("右列", fs=int(14*s), clr="#ffffff"),
                Button("Y", action="demo_toast", fs=int(12*s), bg="#4CAF50", w=int(60*s), h=int(36*s), br=8, mt=int(4*s)),
            ),
        ),
        refresh_interval=0,
    )


def interact_page(shape, sw, sh):
    s = 1.4 if shape == "pill-shaped" else 1.0
    c = _counter["val"]
    return Page(
        Button("← 返回", action="goto_home", fs=int(16*s), bg="#222222", w=int(160*s), h=int(44*s), br=22, mb=int(12*s)),
        Text("交互组件", fs=int(22*s), clr="#ffffff", fw="bold"),

        Text(f"计数器: {c}", fs=int(32*s), clr="#2196F3", fw="bold", mt=int(8*s), mb=int(10*s)),
        Row(
            Button("-1", action="dec", fs=int(20*s), bg="#FF9800", w=int(70*s), h=int(50*s), br=25, mr=int(6*s)),
            Button("+1", action="inc", fs=int(20*s), bg="#4CAF50", w=int(70*s), h=int(50*s), br=25, mr=int(6*s)),
            Button("清零", action="reset", fs=int(14*s), bg="#555555", w=int(70*s), h=int(50*s), br=25),
        ),

        Switch(chk=False, action="auto", mt=int(12*s)),
        Text("开启后每 3 秒自动计数", fs=int(12*s), clr="#aaaaaa"),

        Button("弹出 Toast", action="toast", fs=int(16*s), bg="#2196F3", w=int(200*s), h=int(44*s), br=22, mt=int(12*s)),
        refresh_interval=0,
    )


def handle(action, params):
    if action == "goto_home":
        obj = page("", 0, 0)
        return obj.to_dict() if hasattr(obj, "to_dict") else obj

    elif action == "goto_text":
        obj = text_page("", 0, 0)
        return obj.to_dict() if hasattr(obj, "to_dict") else obj

    elif action == "goto_btn":
        obj = btn_page("", 0, 0)
        return obj.to_dict() if hasattr(obj, "to_dict") else obj

    elif action == "goto_layout":
        obj = layout_page("", 0, 0)
        return obj.to_dict() if hasattr(obj, "to_dict") else obj

    elif action == "goto_interact":
        obj = interact_page("", 0, 0)
        return obj.to_dict() if hasattr(obj, "to_dict") else obj

    elif action == "toast":
        return {"toast": "这是一个 Toast 弹窗"}

    elif action == "demo_toast":
        return {"toast": "按钮被点击了！"}

    elif action == "inc":
        _counter["val"] += 1
        obj = interact_page("", 0, 0)
        return obj.to_dict() if hasattr(obj, "to_dict") else obj

    elif action == "dec":
        _counter["val"] -= 1
        obj = interact_page("", 0, 0)
        return obj.to_dict() if hasattr(obj, "to_dict") else obj

    elif action == "reset":
        _counter["val"] = 0
        obj = interact_page("", 0, 0)
        return obj.to_dict() if hasattr(obj, "to_dict") else obj

    elif action == "auto":
        return {"ri": 3000}

    elif action == "exit":
        return {"exit": True}

    return {"toast": f"未知操作: {action}"}
