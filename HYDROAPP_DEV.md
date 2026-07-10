# HydroApp 开发文档

HydroApp 是一个 JSON 驱动的动态 UI 系统：Python 端定义 UI 组件，序列化为 JSON，Vela 手表端渲染。

## 架构

```
server/data/hydroApps/<AppName>/     ← Python 应用代码
server/hydroApp/                     ← 组件库 + 加载器
client/src/hydro/hydro.ux            ← Vela 渲染器
client/src/hydro_launcher/           ← 启动器（设备选择 → 应用选择 → 激活 → 跳转）
```

### 请求流程

```
启动器 → POST /api/hydro/activate { name }    → 加载应用模块
       → 跳转到 /hydro

hydro.ux
  GET  /api/hydro/page?shape=&sw=&sh=         → mod.page(...) → JSON UI
  每次用户操作:
  POST /api/hydro/action { action, params,
                           shape, sw, sh }     → mod.handle(...) → JSON 响应
  心跳:
  GET  /api/ping (每 3s)
```

## 快速开始

创建 `server/data/hydroApps/MyApp/__init__.py`：

```python
from hydroApp import Page, Text, Button, safe_area_style

def page(shape, sw, sh):
    return Page(
        Text("你好", fs=24, clr="#ffffff"),
        Button("点我", action="hello", w=200, h=44, br=22),
        content_style=safe_area_style(shape),
    )

def handle(action, params, shape=None, sw=0, sh=0):
    if action == "hello":
        return {"toast": "你好！"}
    return {"toast": f"未知操作: {action}"}
```

创建 `server/data/hydroApps/MyApp/manifest.json`：

```json
{
  "manifestVersion": 1,
  "package": {
    "id": "com.example.myapp",
    "name": "MyApp",
    "displayName": "我的应用",
    "version": "1.0.0",
    "versionCode": 1
  },
  "minAPILevel": 6
}
```

重新编译服务端（或热重载后），在手表启动器中即可看到应用。

## 组件

所有组件通过 `**styles` 接收样式简写（见下节）。

| 组件 | 导入 | 序列化 `t` | 特有属性 |
|---|---|---|---|
| Text | `from hydroApp import Text` | `"text"` | `value`（文本内容，序列化为 `v`） |
| Button | `from hydroApp import Button` | `"btn"` | `text`（标签，序列化为 `txt`），`action`（动作 ID，序列化为 `a`） |
| Image | `from hydroApp import Image` | `"img"` | `src`（图片 URL，序列化为 `src`） |
| TextInput | `from hydroApp import TextInput` | `"inp"` | `placeholder`（占位符，序列化为 `v`），`action`（动作 ID） |
| Switch | `from hydroApp import Switch` | `"sw"` | `checked`（布尔值，序列化为 `chk`），`action`（动作 ID） |
| Row | `from hydroApp import Row` | `"row"` | 子组件通过 `*children` 传入 |
| Column | `from hydroApp import Column` | `"col"` | 子组件通过 `*children` 传入 |

### 用法示例

```python
Text("Hello", fs=24, clr="#ffffff", fw="bold", mt=10)
Button("提交", action="submit", bg="#4CAF50", w=200, h=44, br=22)
Image(src="https://example.com/pic.png", w=100, h=100, br=50)
TextInput(placeholder="输入命令", action="cmd", w=300, h=40, bg="#333")
Switch(checked=True, action="toggle", mt=10)
Row(Button("A"), Button("B"), Button("C"), jc="center")
Column(Text("标题"), Text("内容"), jc="center")
```

### Switch 特性

`Switch` 的构造函数参数是 `checked`。也可以传 `chk` 作兼容（会被自动转换）：

```python
Switch(chk=True, action="auto")   # 等同于 Switch(checked=True, action="auto")
```

## 容器

`Row` 和 `Column` 支持传入任意数量的子组件：

```python
Row(
    Button("左",  action="left",  w=100, h=40),
    Button("右",  action="right", w=100, h=40),
    jc="center",
)
Column(
    Text("上"),
    Text("下"),
    jc="center",
)
```

### 嵌套

```python
Row(
    Column(
        Text("左列", fs=14),
        Button("X", action="x", w=60, h=36),
    ),
    Column(
        Text("右列", fs=14),
        Button("Y", action="y", w=60, h=36),
    ),
    jc="center",
)
```

## Page

`Page` 是页面根容器，不是 UIComponent。序列化为顶层 JSON 对象：

```python
from hydroApp import Page, safe_area_style

Page(
    Button("← 返回", action="back"),
    Text("页面标题", fs=22, clr="#ffffff"),
    # ... 更多组件
    refresh_interval=0,
    content_style=safe_area_style(shape),
)
```

### Page 序列化格式

```python
{
    "ri": 0,           # 刷新间隔（毫秒），>0 时客户端定期调 GET /page
    "cs": "...",       # content_style，CSS 字符串，应用到 .content div
    "c": [ ... ],      # 子组件数组
}
```

### safe_area_style

```python
safe_area_style(shape: str) → str
```

| shape | 返回值 |
|---|---|
| `"circle"` | `"padding: 0 30px; margin-top: 40px"` |
| `"rect"` | `"margin-top: 40px"` |
| `"pill-shaped"` | `"margin-top: 40px"` |
| 其他 | `""` |

## 样式

### 样式简写

所有样式通过关键字参数传入组件，使用两字母简写：

| 简写 | CSS 属性 | 示例 |
|---|---|---|
| `fs` | `font-size` | `fs=24` → `font-size: 24px` |
| `clr` | `color` | `clr="#ffffff"` → `color: #ffffff` |
| `fw` | `font-weight` | `fw="bold"` → `font-weight: bold` |
| `ta` | `text-align` | `ta="center"` → `text-align: center` |
| `mt` | `margin-top` | `mt=10` → `margin-top: 10px` |
| `mb` | `margin-bottom` | `mb=20` → `margin-bottom: 20px` |
| `ml` | `margin-left` | `ml=5` → `margin-left: 5px` |
| `mr` | `margin-right` | `mr=5` → `margin-right: 5px` |
| `pt` | `padding-top` | `pt=10` → `padding-top: 10px` |
| `pb` | `padding-bottom` | `pb=10` → `padding-bottom: 10px` |
| `pl` | `padding-left` | `pl=10` → `padding-left: 10px` |
| `pr` | `padding-right` | `pr=10` → `padding-right: 10px` |
| `w` | `width` | `w=200` → `width: 200px` |
| `h` | `height` | `h=44` → `height: 44px` |
| `bg` | `background-color` | `bg="#2196F3"` → `background-color: #2196F3` |
| `br` | `border-radius` | `br=22` → `border-radius: 22px` |
| `jc` | `justify-content` | `jc="center"` → `justify-content: center` |
| `ai` | `align-items` | `ai="center"` → `align-items: center` |

- 数字值自动追加 `px`。字符串值原样使用。
- `None` 值的属性被跳过。

## 响应格式

`handle()` 函数必须返回一个 dict。支持以下字段：

### 字段说明

| 字段 | 类型 | 说明 |
|---|---|---|
| `c` | `list[dict]` | 新 UI 组件树，替换当前页面内容 |
| `ri` | `int` | 刷新间隔（毫秒），0 表示不刷新 |
| `cs` | `str` | content_style CSS，应用到 .content div |
| `toast` | `str` | 弹出提示信息 |
| `exit` | `bool` | 退出 HydroApp，返回启动器 |
| `nav` | `str` | 路由跳转（Vela 页面 URI） |
| `params` | `dict` | 跳转附带参数 |
| `tick` | `int` | 定时器间隔（毫秒），>0 时客户端定期调 POST /action 发 `{action:"tick"}` |

### return 模式

```python
# 1. 返回 Page 对象
Page(Button("返回", action="back"), ...)
# handle 中：return interact_page(shape, sw, sh).to_dict()

# 2. 返回 toast
return {"toast": "操作成功"}

# 3. 返回 exit
return {"exit": True}

# 4. 返回 tick（自动定时器）
return {"tick": 3000, ...Page dict...}

# 5. 返回导航
return {"nav": "/some_page", "params": {...}}
```

### tick 协议

当服务端响应中包含 `tick: <毫秒>` 时，客户端启动一个定时器，每隔指定毫秒数向服务端发 `POST /api/hydro/action { action: "tick" }`。用于"自动+1"等轮询场景。

- 响应中**有** `tick` → 客户端启动/重启定时器
- 响应中**无** `tick` → 客户端清除定时器
- 切换页面（加载新 `c`）时，新响应中是否带 `tick` 决定定时器的去留

## handle(action, params, shape, sw, sh)

应用必须导出一个 `handle` 函数，接收用户操作并返回响应。

```python
def handle(action, params, shape=None, sw=0, sh=0):
    # action: str — 动作 ID（Button 的 action、Switch 的 action 等）
    # params: dict — 附带参数，Switch 切换时包含 {"checked": true/false}
    # shape: str — 屏幕形状 "circle" / "rect" / "pill-shaped"
    # sw, sh: int — 屏幕宽高
    ...
```

### 示例 handle

```python
_counter = {"val": 0}
_auto_on = False

def handle(action, params, shape=None, sw=0, sh=0):
    global _auto_on

    def _r(obj):
        d = obj.to_dict() if hasattr(obj, "to_dict") else obj
        if _auto_on:
            d["tick"] = 3000
        return d

    if action == "goto_home":
        return page(shape, sw, sh).to_dict()

    elif action == "inc":
        _counter["val"] += 1
        return _r(interact_page(shape, sw, sh))

    elif action == "auto":
        _auto_on = params.get("checked", False)
        return _r(interact_page(shape, sw, sh))

    elif action == "tick":
        _counter["val"] += 1
        return _r(interact_page(shape, sw, sh))

    elif action == "exit":
        return {"exit": True}

    elif action == "toast":
        return {"toast": "消息提示"}

    return {"toast": f"未知操作: {action}"}
```

## 应用目录结构

```
server/data/hydroApps/MyApp/
├── __init__.py      ← 必须：page() + handle()
├── manifest.json    ← 推荐：元数据
├── utils.py         ← 可选：工具函数
```

### manifest.json

```json
{
  "manifestVersion": 1,
  "package": {
    "id": "com.example.app",
    "name": "MyApp",
    "displayName": "我的应用",
    "version": "1.0.0",
    "versionCode": 1
  },
  "minAPILevel": 6
}
```

| 字段 | 说明 |
|---|---|
| `package.id` | **安装后的目录名**，也是 `activate` 时用的 name。使用反向域名（如 `com.example.app`）确保唯一。变更即视为新应用 |
| `package.name` | 内部名称，不直接用于路径 |
| `package.displayName` | 启动器中显示的名称 |
| `package.version` | 版本号（字符串），如 `"1.0.0"` |
| `package.versionCode` | 版本号（整数），用于比较新旧 |
| `minAPILevel` | 最低 API 等级，当前为 6 |

## 服务端 API（总览）

| 端点 | 方法 | 说明 |
|---|---|---|
| `/api/hydro/list` | GET | 列出已安装应用 |
| `/api/hydro/activate` | POST | 激活应用（body: `{name}`） |
| `/api/hydro/page` | GET | 获取当前页面（query: `shape,sw,sh`） |
| `/api/hydro/action` | POST | 执行操作（body: `{action, params, shape, sw, sh}`） |

## 客户端组件映射

| `t` 值 | Vela 渲染 | 说明 |
|---|---|---|
| `text` | `<text>` | 纯文本，`v` 字段为内容 |
| `btn` | `<div>` 包 `<text>` | 可点击，`txt` 为标签，`a` 为动作 ID |
| `img` | `<image>` | 图片，`src` 为 URL |
| `inp` | `<input>` | 输入框，`v` 为占位符，`a` 为动作 ID |
| `sw` | `<switch>` | 开关，`chk` 为状态，`a` 为动作 ID，`@change` 触发 |
| `row` | `<div flex-direction: row>` | 水平容器，`c` 为子组件 |
| `col` | `<div flex-direction: column>` | 垂直容器，`c` 为子组件 |

## 屏幕适配

客户端宽度固定为 466px。高度根据屏幕比例缩放：`cssH = screenHeight * 466 / screenWidth`。

应用内可通过 `shape`、`sw`、`sh` 参数做适配：

```python
def _scale(shape):
    return 1.4 if shape == "pill-shaped" else 1.0

# 使用缩放因子调整各组件尺寸
Button("按钮", w=int(200 * s), h=int(44 * s))
```

## 打包发布

应用打包为 ZIP，通过 Flet GUI 的 Hydro 标签页安装：

```bash
zip -r MyApp.zip MyApp/
```

ZIP 根目录必须包含 `__init__.py`。

安装时服务端将目录重命名为 `manifest.json` 中 `package.id` 的值：

| ZIP 内部结构 | `manifest.json` 中的 `package.id` | 安装后路径 |
|---|---|---|
| `MyApp/__init__.py` | `com.example.app` | `data/hydroApps/com.example.app/` |
| `任意目录名/__init__.py` | `com.example.app` | `data/hydroApps/com.example.app/` |

- `package.id` 使用反向域名保证唯一性（如 `com.example.app`）
- `package.id` 是安装后的目录名，也是 `activate` API 中的 `name` 参数
- `package.displayName` 是启动器中显示的应用名称
- `package.version` 会在服务端 GUI 中显示
- 相同 `id` 重新安装会覆盖旧版本

## 常见模式

### 页面间导航

```python
# handle 中返回新页面
def handle(action, params, shape, sw, sh):
    if action == "goto_detail":
        return detail_page(shape, sw, sh).to_dict()
    if action == "goto_home":
        return home_page(shape, sw, sh).to_dict()
```

### 按钮执行操作

```python
# 按钮定义：action="delete"
Button("删除", action="delete")

# handle 处理
if action == "delete":
    do_delete()
    return {"toast": "已删除"}
```

### 开关切换

```python
# 开关定义
Switch(checked=_flag, action="toggle")

# handle 处理
if action == "toggle":
    _flag = params.get("checked", False)
    return page(shape, sw, sh).to_dict()
```

### 定时自动操作

```python
# 响应中带 tick 字段
if _auto_on:
    return {"tick": 3000, ...page dict...}

# 客户端每 3s 发一次 POST /action {action: "tick"}
if action == "tick":
    _counter += 1
    return updated_page(...)
```

## 应用模板

```python
"""MyApp — 应用说明"""

from hydroApp import Page, Text, Button, safe_area_style

def page(shape, sw, sh):
    return Page(
        Text("我的应用", fs=24, clr="#ffffff", fw="bold"),
        Button("开始", action="start", bg="#4CAF50", w=200, h=44, br=22, mt=20),
        content_style=safe_area_style(shape),
    )

def handle(action, params, shape=None, sw=0, sh=0):
    if action == "start":
        return {"toast": "已启动！"}
    elif action == "exit":
        return {"exit": True}
    return {"toast": f"未知操作: {action}"}
```
