# Remote Terminal

通过小米 Vela 手表远程控制 PC 的客户端-服务端应用。

## 目录结构

```
RemoteTerminal/
├── server/          ← 服务端 (Python, Flask + Flet)
│   ├── main.py      ← 唯一入口，含 Flask HTTP API + Flet GUI
│   ├── main.spec    ← PyInstaller 编译配置
│   ├── pack_hydroapp.py  ← HydroApp 打包脚本
│   ├── hydroApp/    ← HydroApp 框架（Page/Button/Text 等 UI 组件 + 加载器）
│   └── data/        ← 运行时数据（配对设备、HydroApp 实例等，不纳入 git）
│
├── client/          ← 客户端 (Vela 快应用)
│   ├── src/         ← 源码（manifest.json 定义路由）
│   │   ├── remote/  ← 远程控制菜单
│   │   ├── touchpad/← 虚拟触控板
│   │   ├── screen/  ← 屏幕浏览
│   │   ├── ssh/     ← SSH 终端
│   │   ├── ppt/     ← PPT 控制
│   │   ├── music/   ← 音乐控制
│   │   ├── hydro/   ← HydroApp 运行时容器
│   │   └── hydro_launcher/ ← HydroApp 启动器
│   └── package.json
│
└── README.md
```

## 快速开始

### 服务端

```bash
cd server
python -m venv .venv && .venv/bin/pip install flask flet requests httpx pillow pyinstaller
.venv/bin/python main.py
```

默认监听 `0.0.0.0:9000`，首次运行弹出 Flet 配对窗口。

## 功能

| 功能 | 路径 | 说明 |
|---|---|---|
| 虚拟触控板 | Touchpad | 相对移动鼠标 + 点击/滚动 |
| SSH 控制 | SSH | 远程终端会话 |
| 屏幕浏览 | Screen | 截图 + 点击控制 |
| PPT 控制 | PPT | 翻页/黑屏/演讲者模式 |
| 音乐控制 | Music | 播放/暂停/切歌 |
| 系统监控 | Performance | CPU/内存/磁盘 |
| 预设命令 | Commands | 一键执行 shell 命令 |
| HydroApp | HydroApp | 可扩展的应用插件体系 |

## API 文档

### 认证

设备配对后通过 `X-Device-ID` 请求头验证。

### 主要端点

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/pair` | 配对二维码 |
| POST | `/api/pair` | 确认配对 |
| POST | `/api/touchpad/move` | 鼠标相对移动 `{dx, dy}` |
| POST | `/api/touchpad/click` | 鼠标点击 `{button: left\|right}` |
| POST | `/api/touchpad/scroll` | 滚动 `{dx, dy}` |
| POST | `/api/keyboard` | 键盘按键 `{key}` |
| POST | `/api/screen/click` | 屏幕绝对坐标点击 `{x, y}` |
| POST | `/api/ssh/*` | SSH 终端会话 |

### HydroApp 协议

- `POST /api/hydro/activate` — 激活 App
- `GET /api/hydro/page` — 获取当前页面 dict
- `POST /api/hydro/action` — 发送动作，返回新页面
- `GET /api/hydro/audio/stream/<bvid>.m4a` — 音频流代理

页面 dict 格式：
```json
{
  "cs": "flex-direction: column; ...",
  "c": [
    {"t": "text", "v": "Hello", "s": "font-size: 20px"},
    {"t": "btn",  "txt": "Click", "a": "my_action", "s": "..."},
    {"t": "img",  "src": "...", "s": "..."},
    {"t": "prog", "v": "00:00 / 03:45", "s": "..."}
  ],
  "audio": {"src": "...", "autoplay": false, "streamType": "music", "meta": {...}},
  "audioCmd": "play|pause|stop|seek:10",
  "toast": "提示信息",
  "tick": 2000,
  "ri": 5000,
  "scrollTop": true,
  "_store": {...}
}
```

UI 组件类型：`text`、`btn`（含 image）、`img`、`qr`、`inp`、`sw`、`prog`（进度文本，由客户端定时器更新）、`row`、`col`（容器）。

## HydroApp 体系

HydroApp 是服务端 Python 插件，通过通用客户端容器 (`hydro.ux`) 渲染服务端生成的 UI。

### 开发

- `data/hydroApps/<app_id>/__init__.py` — 必需入口，导出 `page()` 和 `handle()` 函数
- 其余文件（API 封装、工具函数、页面构建等）由开发者自由组织

### 打包

```bash
python pack_hydroapp.py <项目文件夹>
```

- AST 分析 import → `pip download` 匹配平台的 `.whl` → 打包到 `lib/`
- 运行时会提取 `.whl` 并注册到 `sys.path`（离线，无 pip 无网络）

## 编译发布

### 服务端二进制

```bash
cd server
.venv/bin/pyinstaller --clean main.spec
# 输出到 server/dist/
```
