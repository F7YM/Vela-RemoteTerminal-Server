"""
远程终端 - 服务端
基于 flet GUI + Flask HTTP 服务器
"""

import flet as ft
import asyncio
import signal
import threading
import json
import os
import sys
import platform
import socket
import time
import uuid
import binascii
import subprocess
import shlex
import urllib.request
import re
import threading
import paramiko
import hashlib
from datetime import datetime
from flask import Flask, request, jsonify, send_file, abort
from flask_cors import CORS
from werkzeug.serving import make_server


# Flask 应用
flask_app = Flask(__name__)
CORS(flask_app)

# 常量
API_LEVEL = 4
VERSION = "1.3.0"

# 存储路径
TRUSTED_DEVICES_FILE = "trusted_devices.json"
COMMANDS_FILE = "commands.json"
CONFIG_FILE = "config.json"
REJECTED_DEVICES_FILE = "rejected_devices.json"
PENDING_PAIR_FILE = "pending_pair.json"
SERVER_LOG = []

# ============ 依赖检查 ============

def check_dependencies():
    """检查系统依赖（Linux）"""
    if platform.system() != "Linux":
        return [], []

    missing_tools = []
    tools = {
        'xdotool': {'check': ['which', 'xdotool'], 'dnf': 'xdotool', 'apt': 'xdotool', 'desc': '鼠标键盘控制'},
        'playerctl': {'check': ['which', 'playerctl'], 'dnf': 'playerctl', 'apt': 'playerctl', 'desc': '音乐控制'},
    }

    desktop = os.environ.get('XDG_CURRENT_DESKTOP', '').lower()
    is_wayland = os.environ.get('WAYLAND_DISPLAY') is not None

    if is_wayland:
        tools['grim'] = {'check': ['which', 'grim'], 'dnf': 'grim', 'apt': 'grim', 'desc': 'Wayland截图'}
    elif 'gnome' in desktop:
        tools['gnome-screenshot'] = {'check': ['which', 'gnome-screenshot'], 'dnf': 'gnome-screenshot', 'apt': 'gnome-screenshot', 'desc': '屏幕截图'}
    else:
        tools['scrot'] = {'check': ['which', 'scrot'], 'dnf': 'scrot', 'apt': 'scrot', 'desc': '屏幕截图'}

    for name, info in tools.items():
        try:
            subprocess.run(info['check'], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            missing_tools.append(info)

    missing_pkgs = []
    try:
        import psutil
    except ImportError:
        missing_pkgs.append({'desc': '性能监控 (psutil)', 'dnf': 'python3-psutil', 'apt': 'python3-psutil'})

    try:
        from PIL import Image
    except ImportError:
        missing_pkgs.append({'desc': '截图处理 (Pillow)', 'dnf': 'python3-pillow', 'apt': 'python3-pillow'})

    return missing_tools, missing_pkgs


def get_install_cmd(missing_tools, missing_pkgs):
    """生成安装命令"""
    is_rpm = os.path.exists('/etc/fedora-release') or os.path.exists('/etc/redhat-release')
    pkg_key = 'dnf' if is_rpm else 'apt'

    pkgs = []
    for t in missing_tools:
        pkgs.append(t.get(pkg_key, ''))
    for p in missing_pkgs:
        pkgs.append(p.get(pkg_key, ''))

    pkgs = [p for p in pkgs if p]
    if not pkgs:
        return ""

    if is_rpm:
        return f"sudo dnf install {' '.join(pkgs)}"
    else:
        return f"sudo apt install {' '.join(pkgs)}"


def show_dependency_dialog(missing_tools, missing_pkgs, page):
    """显示依赖缺失对话框"""
    install_cmd = get_install_cmd(missing_tools, missing_pkgs)

    items = []
    for t in missing_tools:
        items.append(ft.Text(f"• {t['desc']} ({t.get('dnf', t.get('apt', ''))})", size=13))
    for p in missing_pkgs:
        items.append(ft.Text(f"• {p['desc']} ({p.get('dnf', p.get('apt', ''))})", size=13))

    content_col = [
        ft.Text("以下依赖缺失，部分功能不可用:", size=14, weight=ft.FontWeight.BOLD),
        ft.Container(height=8),
        *items,
    ]

    if install_cmd:
        content_col.extend([
            ft.Container(height=12),
            ft.Text("安装命令:", size=13, color=ft.Colors.GREY_400),
            ft.Container(
                content=ft.Text(install_cmd, size=12, font_family="monospace", color=ft.Colors.CYAN_300, selectable=True),
                bgcolor=ft.Colors.BLACK26,
                padding=10,
                border_radius=6
            ),
        ])

    def on_dismiss(e):
        dialog.open = False
        page.update()

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("依赖检查"),
        content=ft.Column(content_col, tight=True, scroll=ft.ScrollMode.AUTO, height=300),
        actions=[ft.Button("知道了", on_click=on_dismiss)],
    )
    page.overlay.append(dialog)
    dialog.open = True
    page.update()


def show_first_launch_dialog(page):
    """首次启动提示对话框"""
    config = load_config()
    if config.get("first_launch_done"):
        return

    def on_ok(e):
        config["first_launch_done"] = True
        save_config(config)
        dialog.open = False
        page.update()

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("使用提示"),
        content=ft.Column([
            ft.Text("配对前请确保：", size=14, weight=ft.FontWeight.BOLD),
            ft.Text("• 你的设备已连接 小米运动健康 而非 AstroBox", size=13),
            ft.Text("• 手机与服务端处于同一 WiFi 下", size=13),
            ft.Container(height=8),
            ft.Text("因不明 Bug，Vela 在配对服务端时可能会有大约 5~10s 的延迟，请耐心等待配对弹窗出现。其他操作的延迟不受此 Bug 影响。", size=13, color=ft.Colors.AMBER_300),
        ], tight=True, scroll=ft.ScrollMode.AUTO, height=250),
        actions=[ft.Button("知道了", on_click=on_ok)],
    )
    page.overlay.append(dialog)
    dialog.open = True
    page.update()


# ============ 自启动管理 ============

def get_autostart_path():
    """获取自启动desktop文件路径"""
    return os.path.join(os.path.expanduser('~/.config/autostart'), 'remote-terminal-server.desktop')


def get_exec_path():
    """获取当前可执行文件路径"""
    if getattr(sys, 'frozen', False):
        return os.path.abspath(sys.executable)
    return os.path.abspath(sys.argv[0])


def set_autostart(enabled, icon_path):
    """设置或取消开机自启动"""
    desktop_file = get_autostart_path()
    if enabled:
        os.makedirs(os.path.dirname(desktop_file), exist_ok=True)
        exec_path = get_exec_path()
        if exec_path.endswith('.py'):
            exec_path = f"{sys.executable} {exec_path}"
        with open(desktop_file, 'w') as f:
            f.write(f"""[Desktop Entry]
Type=Application
Name=Remote Terminal Server
Comment=远程终端服务端
Exec={exec_path}
Icon={icon_path}
X-GNOME-Autostart-enabled=true
Terminal=false
""")
    else:
        if os.path.exists(desktop_file):
            os.remove(desktop_file)


def get_autostart_status():
    """检查自启动是否启用"""
    return os.path.exists(get_autostart_path())


def copy_to_clipboard(text):
    """复制文本到剪贴板"""
    try:
        import pyperclip
        pyperclip.copy(text)
    except Exception:
        pass


# 全局引用
page_ref = None
log_list_ref = None
devices_list_ref = None
server_running = False
flask_server = None
server_thread = None

# SSH 会话管理
ssh_sessions = {}  # {device_id: {client: SSHClient, channel: Channel, buffer: bytearray, lock, thread}}

# ============ 工具函数 ============

def get_data_dir():
    """获取数据存储目录（跨平台）"""
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, 'data')
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


def get_static_dir():
    """获取静态文件目录"""
    data_dir = get_data_dir()
    static_dir = os.path.join(data_dir, 'static')
    os.makedirs(static_dir, exist_ok=True)
    return static_dir


def cleanup_static_dir():
    """清理静态文件目录"""
    static_dir = get_static_dir()
    try:
        for f in os.listdir(static_dir):
            filepath = os.path.join(static_dir, f)
            if os.path.isfile(filepath):
                os.unlink(filepath)
    except Exception as e:
        print(f"[清理] 错误: {e}")


def load_json(filename, default=None):
    """安全加载JSON文件"""
    filepath = os.path.join(get_data_dir(), filename)
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return default if default is not None else []
    return default if default is not None else []


def save_json(filename, data):
    """安全保存JSON文件"""
    filepath = os.path.join(get_data_dir(), filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_trusted_devices():
    return load_json(TRUSTED_DEVICES_FILE, [])


def save_trusted_devices(devices):
    save_json(TRUSTED_DEVICES_FILE, devices)


def load_commands():
    return load_json(COMMANDS_FILE, [])


def save_commands(commands):
    save_json(COMMANDS_FILE, commands)


def load_config():
    config = load_json(CONFIG_FILE, {"terminal_enabled": False, "ssh_enabled": False, "ssh_user": ""})
    if "encryption_key" not in config:
        config["encryption_key"] = uuid.uuid4().hex + uuid.uuid4().hex
        save_json(CONFIG_FILE, config)
    return config


# 速率限制: {device_id: [timestamp, ...]}
_rate_limit = {}


def _check_rate(device_id, max_req=10, window=60):
    """检查速率限制, 返回 (allowed: bool, remaining: int)"""
    now = time.time()
    if device_id not in _rate_limit:
        _rate_limit[device_id] = []
    times = [t for t in _rate_limit[device_id] if now - t < window]
    _rate_limit[device_id] = times
    if len(times) >= max_req:
        return False, 0
    _rate_limit[device_id].append(now)
    return True, max_req - len(times) - 1


def _xor_crypt(text, key):
    """XOR encrypt/decrypt, 输入输出都是 hex 字符串"""
    raw = binascii.unhexlify(text)
    result = bytearray(len(raw))
    for i in range(len(raw)):
        result[i] = raw[i] ^ ord(key[i % len(key)])
    return result.decode('utf-8', errors='replace')


def save_config(config):
    save_json(CONFIG_FILE, config)


def load_rejected_devices():
    return set(load_json(REJECTED_DEVICES_FILE, []))


def save_rejected_devices(devices):
    save_json(REJECTED_DEVICES_FILE, list(devices))


def is_device_rejected(device_id):
    return device_id in load_rejected_devices()


def add_rejected_device(device_id):
    rejected = load_rejected_devices()
    rejected.add(device_id)
    save_rejected_devices(rejected)


def load_pending_pairs():
    return load_json(PENDING_PAIR_FILE, [])


def save_pending_pair(device_id, device_name):
    pairs = load_pending_pairs()
    # 避免重复
    for p in pairs:
        if p.get("device_id") == device_id:
            return
    pairs.append({"device_id": device_id, "device_name": device_name})
    save_json(PENDING_PAIR_FILE, pairs)


def remove_pending_pair(device_id):
    pairs = load_pending_pairs()
    pairs = [p for p in pairs if p.get("device_id") != device_id]
    save_json(PENDING_PAIR_FILE, pairs)


def add_log(message, level="info"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    SERVER_LOG.append({"text": log_entry, "level": level})
    if len(SERVER_LOG) > 100:
        SERVER_LOG.pop(0)
    return log_entry


def refresh_log_list():
    """刷新 GUI 日志列表"""
    global log_list_ref
    if log_list_ref:
        log_list_ref.controls.clear()
        for log in SERVER_LOG[-20:]:
            color = ft.Colors.RED_400 if log["level"] == "error" else \
                    ft.Colors.YELLOW_400 if log["level"] == "warning" else \
                    ft.Colors.GREEN_400 if log["level"] == "success" else \
                    ft.Colors.GREY_400
            log_list_ref.controls.append(
                ft.Text(log["text"], size=12, color=color, font_family="monospace")
            )
        log_list_ref.update()


def sanitize_path(filename):
    """防止路径遍历攻击"""
    # 移除路径分隔符和.. 
    filename = os.path.basename(filename)
    # 只允许字母、数字、下划线、点、连字符
    import re
    if not re.match(r'^[a-zA-Z0-9_\-\.]+$', filename):
        return None
    return filename


# ============ SSH 会话管理 (paramiko) ============

def _set_pty_size(device_id, cols, rows):
    """通过 SSH 协议调整终端窗口尺寸"""
    session = ssh_sessions.get(device_id)
    if not session:
        return
    try:
        session["channel"].resize_pty(width=cols, height=rows)
    except Exception:
        pass


def _ssh_output_reader(device_id):
    """后台线程: 从 paramiko channel 读取 SSH 输出到缓冲区 (截断 ~50KB)"""
    MAX_LEN = 50000
    try:
        while True:
            session = ssh_sessions.get(device_id)
            if not session:
                break
            channel = session["channel"]
            try:
                if not channel.recv_ready():
                    time.sleep(0.1)
                    continue
                data = channel.recv(4096)
            except Exception:
                break
            if not data:
                break
            with session["lock"]:
                session["buffer"].extend(data)
                if len(session["buffer"]) > MAX_LEN:
                    session["buffer"] = session["buffer"][-MAX_LEN:]
    except Exception:
        pass


def _cleanup_ssh_session(device_id):
    """清理单个 SSH 会话"""
    session = ssh_sessions.pop(device_id, None)
    if not session:
        return
    try:
        session["channel"].close()
    except Exception:
        pass
    try:
        session["client"].close()
    except Exception:
        pass


# SSH 会话超时清理
SSH_SESSION_TIMEOUT = 300  # 5 分钟
_ssh_cleaner_started = False
_ssh_cleaner_lock = threading.Lock()


def _start_ssh_cleaner():
    global _ssh_cleaner_started
    with _ssh_cleaner_lock:
        if _ssh_cleaner_started:
            return
        _ssh_cleaner_started = True
    t = threading.Thread(target=_ssh_cleaner_loop, daemon=True)
    t.start()


def _ssh_cleaner_loop():
    while True:
        time.sleep(30)
        now = time.time()
        dead = [
            did for did, s in list(ssh_sessions.items())
            if now - s.get("last_active", 0) > SSH_SESSION_TIMEOUT
        ]
        for did in dead:
            add_log(f"SSH 会话超时清理: {did[:8]}...", "info")
            _cleanup_ssh_session(did)


# ============ Flask 路由 ============

def decrypt_body(f):
    """解密 XOR 加密的请求体。客户端发 { data: hex, encrypted: true } 时自动解密回原始 JSON"""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        data = request.get_json(force=True, silent=True) or {}
        if data.get('encrypted'):
            key = load_config().get('encryption_key', '')
            if key:
                try:
                    decrypted = _xor_crypt(data['data'], key)
                    data = json.loads(decrypted)
                except (binascii.Error, json.JSONDecodeError, KeyError, ValueError):
                    return jsonify({"status": "error", "message": "解密失败"}), 400
        request._decrypted_data = data
        return f(*args, **kwargs)
    return decorated


def require_trusted(f):
    """验证设备是否已信任的装饰器"""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        device_id = request.headers.get('X-Device-ID')
        if not device_id:
            return jsonify({"status": "error", "message": "Missing device ID"}), 401
        devices = load_trusted_devices()
        trusted = any(d.get('device_id') == device_id for d in devices)
        if not trusted:
            return jsonify({"status": "error", "message": "Device not trusted"}), 403
        return f(*args, **kwargs)
    return decorated


@flask_app.route('/api/pair', methods=['POST'])
def pair_device():
    """配对请求（无需验证）"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "Invalid JSON"}), 400

        device_id = data.get('device_id', '').strip()
        device_name = data.get('device_name', 'Unknown').strip()[:50]

        if not device_id or len(device_id) > 100:
            return jsonify({"status": "error", "message": "Invalid device_id"}), 400

        if is_device_rejected(device_id):
            return jsonify({"status": "rejected", "message": "Device was rejected"})

        devices = load_trusted_devices()
        for d in devices:
            if d.get('device_id') == device_id:
                add_log(f"设备 {device_id[:8]}... 已信任", "success")
                config = load_config()
                return jsonify({"status": "trusted", "message": "Device already trusted", "encryption_key": config.get("encryption_key", "")})

        add_log(f"配对请求: {device_id[:8]}...", "warning")
        save_pending_pair(device_id, device_name)

        return jsonify({"status": "pending", "message": "Waiting for user confirmation"})

    except Exception as e:
        add_log(f"配对错误: {str(e)}", "error")
        return jsonify({"status": "error", "message": "Internal error"}), 500


@flask_app.route('/api/pending_pair', methods=['GET'])
def get_pending_pairs():
    """获取待处理的配对请求（GUI 轮询用）"""
    return jsonify({"status": "ok", "pairs": load_pending_pairs()})


@flask_app.route('/api/pair/respond', methods=['POST'])
def respond_pair():
    """响应配对请求（GUI 调用）"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "Invalid JSON"}), 400

        device_id = data.get('device_id', '').strip()
        action = data.get('action', '')  # 'accept' or 'reject'

        if not device_id or action not in ('accept', 'reject'):
            return jsonify({"status": "error", "message": "Invalid params"}), 400

        remove_pending_pair(device_id)

        if action == 'accept':
            devices = load_trusted_devices()
            if not any(d.get('device_id') == device_id for d in devices):
                devices.append({
                    "device_id": device_id,
                    "device_name": data.get('device_name', 'Unknown')[:50],
                    "trusted_at": datetime.now().isoformat()
                })
                save_trusted_devices(devices)
            add_log(f"已信任设备: {device_id[:8]}...", "success")
        else:
            add_rejected_device(device_id)
            add_log(f"拒绝设备: {device_id[:8]}...", "error")

        return jsonify({"status": "ok"})
    except Exception as e:
        add_log(f"配对响应错误: {str(e)}", "error")
        return jsonify({"status": "error", "message": "Internal error"}), 500


@flask_app.route('/api/status', methods=['GET'])
@require_trusted
def get_status():
    """获取服务器状态"""
    return jsonify({
        "status": "running",
        "trusted_count": len(load_trusted_devices()),
        "system": get_system_info(),
        "battery": get_battery_info()
    })


@flask_app.route('/api/ping', methods=['GET'])
def ping():
    """检查服务器是否运行（无需验证）"""
    return jsonify({"status": "ok"})


@flask_app.route('/api/version', methods=['GET'])
def get_version():
    """获取服务器版本信息（无需验证）"""
    return jsonify({
        "status": "ok",
        "api_level": API_LEVEL,
        "version": VERSION
    })


@flask_app.route('/api/check/<device_id>', methods=['GET'])
def check_device(device_id):
    """检查设备配对状态（无需验证）"""
    if not device_id or len(device_id) > 100:
        return jsonify({"status": "error"}), 400

    if is_device_rejected(device_id):
        return jsonify({"status": "rejected"})

    devices = load_trusted_devices()
    for d in devices:
        if d.get('device_id') == device_id:
            config = load_config()
            return jsonify({"status": "trusted", "encryption_key": config.get("encryption_key", "")})
    return jsonify({"status": "pending"})


@flask_app.route('/api/auth', methods=['GET'])
def check_auth():
    """检查设备是否被授权（无需验证，用于配对前检查）"""
    device_id = request.headers.get('X-Device-ID')
    if not device_id or len(device_id) > 100:
        return jsonify({"status": "error", "message": "Missing device ID"}), 400
    
    devices = load_trusted_devices()
    for d in devices:
        if d.get('device_id') == device_id:
            return jsonify({"status": "authorized"})
    return jsonify({"status": "unauthorized"})


@flask_app.route('/api/lock', methods=['POST'])
@require_trusted
def lock_screen():
    """锁屏（跨平台）"""
    system = platform.system()
    try:
        if system == "Windows":
            import ctypes
            ctypes.windll.user32.LockWorkStation()
        elif system == "Linux":
            commands = [
                ['loginctl', 'lock-session'],
                ['xdg-screensaver', 'lock'],
                ['gnome-screensaver-command', '-l'],
            ]
            for cmd in commands:
                try:
                    subprocess.run(cmd, check=True, timeout=5, capture_output=True)
                    break
                except (subprocess.CalledProcessError, FileNotFoundError):
                    continue
        elif system == "Darwin":
            subprocess.run(
                ['/System/Library/CoreServices/Menu Extras/User.menu/Contents/Resources/CGSession', '-suspend'],
                check=True, timeout=5, capture_output=True
            )
        else:
            return jsonify({"status": "error", "message": "Unsupported system"}), 500
        
        add_log("设备已锁屏", "success")
        return jsonify({"status": "ok", "message": "Screen locked"})
    except Exception as e:
        add_log(f"锁屏失败: {str(e)}", "error")
        return jsonify({"status": "error", "message": "Lock failed"}), 500


@flask_app.route('/api/performance', methods=['GET'])
@require_trusted
def get_performance():
    """获取性能信息（跨平台）"""
    try:
        import psutil
        cpu_percent = psutil.cpu_percent(interval=0)
        memory = psutil.virtual_memory()
        
        temp = None
        if hasattr(psutil, 'sensors_temperatures'):
            temps = psutil.sensors_temperatures()
            if temps:
                for name, entries in temps.items():
                    if entries:
                        temp = entries[0].current
                        break
        
        return jsonify({
            "status": "ok",
            "cpu": cpu_percent,
            "mem_percent": memory.percent,
            "mem_used": memory.used // (1024 * 1024),
            "mem_total": memory.total // (1024 * 1024),
            "temp": temp
        })
    except ImportError:
        return jsonify({"status": "error", "message": "psutil not installed"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": "Failed to get performance"}), 500


@flask_app.route('/api/screen/capture', methods=['GET'])
@require_trusted
def capture_screen():
    """截取屏幕（跨平台）"""
    from PIL import Image
    
    static_dir = get_static_dir()
    tmp_path = os.path.join(static_dir, 'tmp_screenshot.png')
    
    try:
        system = platform.system()
        success = False
        
        if system == "Windows":
            try:
                from PIL import ImageGrab
                img = ImageGrab.grab()
                img.save(tmp_path)
                success = True
            except Exception as e:
                print(f"[截图] Windows失败: {e}")
        
        elif system == "Linux":
            is_wayland = os.environ.get('WAYLAND_DISPLAY') is not None
            desktop = os.environ.get('XDG_CURRENT_DESKTOP', '').lower()
            
            methods = []
            if 'kde' in desktop or 'plasma' in desktop:
                methods.append(('spectacle', ['spectacle', '--fullscreen', '--background', '--nonotify', '--output', tmp_path]))
            elif 'gnome' in desktop:
                methods.append(('gnome-screenshot', ['gnome-screenshot', '-f', tmp_path]))
            
            if is_wayland:
                methods.append(('grim', ['grim', tmp_path]))
            else:
                methods.append(('scrot', ['scrot', tmp_path]))
            
            for name, cmd in methods:
                try:
                    result = subprocess.run(cmd, capture_output=True, timeout=10)
                    if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
                        success = True
                        break
                except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                    continue
        
        elif system == "Darwin":
            try:
                subprocess.run(['screencapture', '-x', tmp_path], check=True, timeout=5, capture_output=True)
                success = True
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass
        
        if not success:
            return jsonify({"status": "error", "message": "Screenshot failed"}), 500
        
        # 压缩图片
        img = Image.open(tmp_path)
        real_w, real_h = img.size
        if img.mode == 'RGBA':
            img = img.convert('RGB')
        img.thumbnail((480, 480), Image.LANCZOS)
        thumb_w, thumb_h = img.size
        
        filename = f'screen_{uuid.uuid4().hex[:8]}.jpg'
        output_path = os.path.join(static_dir, filename)
        img.save(output_path, 'JPEG', quality=75, optimize=False)
        
        # 清理临时文件
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        
        # 生成URL
        host = request.host
        url = f"http://{host}/static/{filename}"
        return jsonify({
            "status": "ok",
            "url": url,
            "screen_width": real_w,
            "screen_height": real_h,
            "image_width": thumb_w,
            "image_height": thumb_h
        })
    
    except Exception as e:
        print(f"[截图] 异常: {e}")
        if os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        return jsonify({"status": "error", "message": "Screenshot failed"}), 500


@flask_app.route('/static/<filename>')
def serve_static(filename):
    """提供静态文件（防止路径遍历）"""
    safe_filename = sanitize_path(filename)
    if not safe_filename:
        abort(404)
    
    static_dir = get_static_dir()
    filepath = os.path.join(static_dir, safe_filename)
    
    # 确保文件在static目录内
    if not os.path.abspath(filepath).startswith(os.path.abspath(static_dir)):
        abort(403)
    
    if not os.path.exists(filepath):
        abort(404)
    
    return send_file(filepath)


@flask_app.route('/api/screen/click', methods=['POST'])
@require_trusted
def screen_click():
    """鼠标点击（跨平台）"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "Invalid JSON"}), 400
        
        x = int(data.get('x', 0))
        y = int(data.get('y', 0))
        
        # 限制坐标范围
        x = max(0, min(x, 10000))
        y = max(0, min(y, 10000))
        
        system = platform.system()
        
        if system == "Windows":
            import ctypes
            ctypes.windll.user32.SetCursorPos(x, y)
            ctypes.windll.user32.mouse_event(2, 0, 0, 0, 0)
            ctypes.windll.user32.mouse_event(4, 0, 0, 0, 0)
        elif system == "Linux":
            try:
                subprocess.run(['xdotool', 'mousemove', '--screen', '0', str(x), str(y)], 
                             check=True, timeout=2, capture_output=True)
                subprocess.run(['xdotool', 'click', '1'], check=True, timeout=2, capture_output=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                try:
                    ydotool_socket = os.environ.get('YDOTOOL_SOCKET', '/run/user/0/.ydotool_socket')
                    env = os.environ.copy()
                    env['YDOTOOL_SOCKET'] = ydotool_socket
                    subprocess.run(['ydotool', 'mousemove', '--absolute', '-x', str(x), '-y', str(y)],
                                 check=True, timeout=2, capture_output=True, env=env)
                    subprocess.run(['ydotool', 'click', '0xC0'], check=True, timeout=2, capture_output=True, env=env)
                except (subprocess.CalledProcessError, FileNotFoundError) as e:
                    return jsonify({"status": "error", "message": "Click tool not available"}), 500
        elif system == "Darwin":
            try:
                subprocess.run(['cliclick', f'c:{x},{y}'], check=True, timeout=2, capture_output=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                return jsonify({"status": "error", "message": "cliclick not installed"}), 500
        else:
            return jsonify({"status": "error", "message": "Unsupported system"}), 500
        
        return jsonify({"status": "ok"})
    except (ValueError, TypeError):
        return jsonify({"status": "error", "message": "Invalid coordinates"}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": "Click failed"}), 500


@flask_app.route('/api/keyboard', methods=['POST'])
@require_trusted
def keyboard_input():
    """模拟键盘输入（跨平台）"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "Invalid JSON"}), 400

        key = data.get('key', '')
        if not key:
            return jsonify({"status": "error", "message": "No key specified"}), 400

        # 映射按键名称
        key_map = {
            'left': 'Left',
            'right': 'Right',
            'up': 'Up',
            'down': 'Down',
            'enter': 'Return',
            'space': 'space',
            'tab': 'Tab',
            'esc': 'Escape',
            'backspace': 'BackSpace'
        }
        xdotool_key = key_map.get(key, key)

        system = platform.system()

        if system == "Windows":
            import ctypes
            # Windows虚拟键码
            vk_map = {
                'left': 0x25, 'right': 0x27, 'up': 0x26, 'down': 0x28,
                'enter': 0x0D, 'space': 0x20
            }
            vk = vk_map.get(key, 0)
            if vk:
                ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
                ctypes.windll.user32.keybd_event(vk, 0, 2, 0)
        elif system == "Linux":
            # 检测xdotool是否可用
            try:
                subprocess.run(['which', 'xdotool'], check=True, capture_output=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                return jsonify({
                    "status": "error",
                    "message": "请安装xdotool: sudo apt install xdotool 或 sudo dnf install xdotool"
                }), 500

            try:
                subprocess.run(['xdotool', 'key', xdotool_key],
                             check=True, timeout=2, capture_output=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                return jsonify({"status": "error", "message": "xdotool执行失败"}), 500
        elif system == "Darwin":
            try:
                subprocess.run(['cliclick', f'kd:{key}'], check=True, timeout=2, capture_output=True)
                subprocess.run(['cliclick', f'ku:{key}'], check=True, timeout=2, capture_output=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                return jsonify({"status": "error", "message": "cliclick not installed"}), 500

        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@flask_app.route('/api/touchpad/move', methods=['POST'])
@require_trusted
def touchpad_move():
    """触控板移动（相对移动）"""
    try:
        print(f"[触控板] Content-Type: {request.content_type}")
        print(f"[触控板] Raw data: {request.data[:200]}")
        data = request.get_json(force=True, silent=True)
        print(f"[触控板] 收到数据: {data}, 类型: {type(data)}")
        if not data:
            print(f"[触控板] 数据为空")
            return jsonify({"status": "error", "message": "Invalid JSON"}), 400

        dx = int(data.get('dx', 0))
        dy = int(data.get('dy', 0))
        print(f"[触控板] 移动: dx={dx}, dy={dy}")

        # 限制移动距离
        dx = max(-500, min(500, dx))
        dy = max(-500, min(500, dy))

        system = platform.system()

        if system == "Windows":
            import ctypes
            ctypes.windll.user32.mouse_event(1, dx, dy, 0, 0)  # MOUSEEVENTF_MOVE = 1
        elif system == "Linux":
            try:
                subprocess.run(['xdotool', 'mousemove_relative', '--', str(dx), str(dy)],
                             check=True, timeout=2, capture_output=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                try:
                    ydotool_socket = os.environ.get('YDOTOOL_SOCKET', '/run/user/0/.ydotool_socket')
                    env = os.environ.copy()
                    env['YDOTOOL_SOCKET'] = ydotool_socket
                    subprocess.run(['ydotool', 'mousemove', '--', str(dx), str(dy)],
                                 check=True, timeout=2, capture_output=True, env=env)
                except (subprocess.CalledProcessError, FileNotFoundError) as e:
                    return jsonify({"status": "error", "message": "Move tool not available"}), 500
        elif system == "Darwin":
            try:
                subprocess.run(['cliclick', f'm:+{dx},+{dy}'], check=True, timeout=2, capture_output=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                return jsonify({"status": "error", "message": "cliclick not installed"}), 500
        else:
            return jsonify({"status": "error", "message": "Unsupported system"}), 500

        return jsonify({"status": "ok"})
    except (ValueError, TypeError):
        return jsonify({"status": "error", "message": "Invalid delta values"}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": "Move failed"}), 500


@flask_app.route('/api/touchpad/click', methods=['POST'])
@require_trusted
def touchpad_click():
    """触控板点击"""
    try:
        data = request.get_json() or {}
        button = data.get('button', 'left')  # left, right, middle

        system = platform.system()

        if system == "Windows":
            import ctypes
            if button == 'left':
                ctypes.windll.user32.mouse_event(2, 0, 0, 0, 0)  # MOUSEEVENTF_LEFTDOWN
                ctypes.windll.user32.mouse_event(4, 0, 0, 0, 0)  # MOUSEEVENTF_LEFTUP
            elif button == 'right':
                ctypes.windll.user32.mouse_event(8, 0, 0, 0, 0)  # MOUSEEVENTF_RIGHTDOWN
                ctypes.windll.user32.mouse_event(16, 0, 0, 0, 0)  # MOUSEEVENTF_RIGHTUP
        elif system == "Linux":
            btn_map = {'left': '1', 'middle': '2', 'right': '3'}
            btn = btn_map.get(button, '1')
            try:
                subprocess.run(['xdotool', 'click', btn], check=True, timeout=2, capture_output=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                try:
                    ydotool_socket = os.environ.get('YDOTOOL_SOCKET', '/run/user/0/.ydotool_socket')
                    env = os.environ.copy()
                    env['YDOTOOL_SOCKET'] = ydotool_socket
                    code_map = {'left': '0xC0', 'right': '0xC1', 'middle': '0xC2'}
                    code = code_map.get(button, '0xC0')
                    subprocess.run(['ydotool', 'click', code], check=True, timeout=2, capture_output=True, env=env)
                except (subprocess.CalledProcessError, FileNotFoundError):
                    return jsonify({"status": "error", "message": "Click tool not available"}), 500
        elif system == "Darwin":
            try:
                subprocess.run(['cliclick', 'c:.'], check=True, timeout=2, capture_output=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                return jsonify({"status": "error", "message": "cliclick not installed"}), 500
        else:
            return jsonify({"status": "error", "message": "Unsupported system"}), 500

        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "message": "Click failed"}), 500


@flask_app.route('/api/touchpad/scroll', methods=['POST'])
@require_trusted
def touchpad_scroll():
    """触控板滚动"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "Invalid JSON"}), 400

        dy = int(data.get('dy', 0))
        dy = max(-500, min(500, dy))

        system = platform.system()

        if system == "Windows":
            import ctypes
            # MOUSEEVENTF_WHEEL = 0x0800, WHEEL_DELTA = 120
            amount = int(dy * 120 / 10)
            ctypes.windll.user32.mouse_event(0x0800, 0, 0, amount, 0)
        elif system == "Linux":
            # xdotool 滚动: 正数向下，负数向上
            btn = '5' if dy > 0 else '4'
            clicks = abs(dy) // 10
            try:
                for _ in range(clicks):
                    subprocess.run(['xdotool', 'click', btn], check=True, timeout=2, capture_output=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                return jsonify({"status": "error", "message": "Scroll tool not available"}), 500
        elif system == "Darwin":
            try:
                subprocess.run(['cliclick', f'w:{dy}'], check=True, timeout=2, capture_output=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                return jsonify({"status": "error", "message": "cliclick not installed"}), 500
        else:
            return jsonify({"status": "error", "message": "Unsupported system"}), 500

        return jsonify({"status": "ok"})
    except (ValueError, TypeError):
        return jsonify({"status": "error", "message": "Invalid scroll value"}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": "Scroll failed"}), 500


@flask_app.route('/api/music/status', methods=['GET'])
@require_trusted
def music_status():
    """获取音乐播放状态（跨平台），含封面 hash"""
    system = platform.system()
    try:
        cover_hash = None
        if system == "Linux":
            try:
                result = subprocess.run(
                    ['playerctl', 'metadata', '--format', '{{title}}|||{{artist}}|||{{status}}'],
                    capture_output=True, text=True, timeout=3)
                if result.returncode == 0 and result.stdout.strip():
                    parts = result.stdout.strip().split('|||')
                    cover_hash = _get_cover_hash_linux()
                    return jsonify({
                        "status": "ok",
                        "title": parts[0] if len(parts) > 0 else "",
                        "artist": parts[1] if len(parts) > 1 else "",
                        "playing": parts[2] == "Playing" if len(parts) > 2 else False,
                        "cover_hash": cover_hash
                    })
            except FileNotFoundError:
                pass
            return jsonify({"status": "ok", "title": "", "artist": "", "playing": False, "cover_hash": None})

        elif system == "Darwin":
            cover_hash = _get_cover_hash_darwin()
            result = subprocess.run(['osascript', '-e',
                'tell application "System Events" to get {name, artist} of current track of application "Music"'],
                capture_output=True, text=True, timeout=3)
            if result.returncode == 0:
                parts = result.stdout.strip().split(', ')
                return jsonify({
                    "status": "ok",
                    "title": parts[0] if len(parts) > 0 else "",
                    "artist": parts[1] if len(parts) > 1 else "",
                    "playing": True,
                    "cover_hash": cover_hash
                })

        elif system == "Windows":
            try:
                import ctypes
                return jsonify({"status": "ok", "title": "", "artist": "", "playing": False, "cover_hash": None})
            except:
                pass

        return jsonify({"status": "ok", "title": "", "artist": "", "playing": False, "cover_hash": None})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@flask_app.route('/api/music/play', methods=['POST'])
@require_trusted
def music_play():
    """播放/暂停"""
    return _music_control('play')


@flask_app.route('/api/music/pause', methods=['POST'])
@require_trusted
def music_pause():
    """暂停"""
    return _music_control('pause')


@flask_app.route('/api/music/prev', methods=['POST'])
@require_trusted
def music_prev():
    """上一曲"""
    return _music_control('prev')


@flask_app.route('/api/music/next', methods=['POST'])
@require_trusted
def music_next():
    """下一曲"""
    return _music_control('next')


def _get_cover_hash_linux():
    """Linux: 获取封面图的 hash（基于 artUrl 路径）"""
    try:
        result = subprocess.run(
            ['playerctl', 'metadata', 'mpris:artUrl'],
            capture_output=True, text=True, timeout=2)
        if result.returncode == 0 and result.stdout.strip():
            art_url = result.stdout.strip()
            # artUrl 格式: file:///tmp/.tmpXXXXXX.jpg
            if art_url.startswith('file://'):
                filepath = art_url[7:]
                if os.path.exists(filepath):
                    with open(filepath, 'rb') as f:
                        return hashlib.md5(f.read()).hexdigest()
    except Exception:
        pass
    return None


def _get_cover_hash_darwin():
    """macOS: 尝试从 Music.app 导出的临时封面获取 hash"""
    return None


def _get_cover_source_path():
    """获取当前封面图的源文件路径，用于后续处理"""
    system = platform.system()
    if system == "Linux":
        try:
            result = subprocess.run(
                ['playerctl', 'metadata', 'mpris:artUrl'],
                capture_output=True, text=True, timeout=2)
            if result.returncode == 0 and result.stdout.strip():
                art_url = result.stdout.strip()
                if art_url.startswith('file://'):
                    filepath = art_url[7:]
                    if os.path.exists(filepath):
                        return filepath
        except Exception:
            pass
    return None


@flask_app.route('/api/music/cover', methods=['GET'])
@require_trusted
def music_cover():
    """获取处理后的封面图（高斯模糊 + 压暗），适合手表端做背景"""
    try:
        from PIL import Image, ImageFilter

        source_path = _get_cover_source_path()
        if not source_path:
            return jsonify({"status": "ok", "url": None})

        # 用文件内容 hash 作为缓存 key
        with open(source_path, 'rb') as f:
            file_hash = hashlib.md5(f.read()).hexdigest()

        static_dir = get_static_dir()
        cache_filename = f'cover_{file_hash}.jpg'
        cache_path = os.path.join(static_dir, cache_filename)

        # 缓存命中，直接返回
        if not os.path.exists(cache_path):
            img = Image.open(source_path)
            if img.mode == 'RGBA':
                img = img.convert('RGB')

            # 先缩放到合适大小（节省处理时间）
            img.thumbnail((600, 600), Image.LANCZOS)

            # 高斯模糊
            blurred = img.filter(ImageFilter.GaussianBlur(radius=30))

            # 压暗：用 Point 操作让每个像素亮度降低 40%
            darkened = blurred.point(lambda p: int(p * 0.6))

            darkened.save(cache_path, 'JPEG', quality=70)

        host = request.host
        url = f"http://{host}/static/{cache_filename}"
        return jsonify({"status": "ok", "url": url})

    except Exception as e:
        print(f"[封面] 处理失败: {e}")
        return jsonify({"status": "ok", "url": None})


def _music_control(action):
    """音乐控制通用函数"""
    system = platform.system()
    try:
        if system == "Linux":
            cmd_map = {
                'play': ['playerctl', 'play-pause'],
                'pause': ['playerctl', 'pause'],
                'prev': ['playerctl', 'previous'],
                'next': ['playerctl', 'next']
            }
            cmd = cmd_map.get(action)
            if cmd:
                subprocess.run(cmd, check=True, timeout=3, capture_output=True)
        
        elif system == "Darwin":
            action_map = {
                'play': 'play',
                'pause': 'pause',
                'prev': 'previous track',
                'next': 'next track'
            }
            script = f'tell application "Music" to {action_map.get(action, "play")}'
            subprocess.run(['osascript', '-e', script], check=True, timeout=3, capture_output=True)
        
        elif system == "Windows":
            # Windows媒体键模拟
            import ctypes
            VK_MEDIA_PLAY_PAUSE = 0xB3
            VK_MEDIA_PREV_TRACK = 0xB1
            VK_MEDIA_NEXT_TRACK = 0xB0
            
            vk_map = {
                'play': VK_MEDIA_PLAY_PAUSE,
                'pause': VK_MEDIA_PLAY_PAUSE,
                'prev': VK_MEDIA_PREV_TRACK,
                'next': VK_MEDIA_NEXT_TRACK
            }
            vk = vk_map.get(action)
            if vk:
                ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
                ctypes.windll.user32.keybd_event(vk, 0, 2, 0)
        
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@flask_app.route('/api/commands', methods=['GET'])
@require_trusted
def get_commands():
    """获取命令列表"""
    commands = load_commands()
    result = [
        {
            "id": i,
            "name": cmd.get("name", f"命令 {i+1}")[:50],  # 限制长度
            "command": cmd.get("command", "")[:200]
        }
        for i, cmd in enumerate(commands)
    ]
    return jsonify({"status": "ok", "commands": result})


@flask_app.route('/api/commands/<int:cmd_id>/run', methods=['POST'])
@require_trusted
def run_command(cmd_id):
    """执行预设命令"""
    commands = load_commands()
    if cmd_id < 0 or cmd_id >= len(commands):
        return jsonify({"status": "error", "message": "Invalid command ID"}), 400
    
    cmd = commands[cmd_id]
    cmd_str = cmd.get("command", "").strip()
    if not cmd_str:
        return jsonify({"status": "error", "message": "Empty command"}), 400
    
    try:
        add_log(f"执行命令: {cmd.get('name', cmd_str[:20])}", "warning")
        result = subprocess.run(
            shlex.split(cmd_str),
            capture_output=True,
            text=True,
            timeout=30
        )
        output = result.stdout + result.stderr
        add_log(f"命令完成: 返回码 {result.returncode}", "success")
        return jsonify({
            "status": "ok",
            "returncode": result.returncode,
            "output": output[:1000]
        })
    except subprocess.TimeoutExpired:
        add_log("命令超时", "error")
        return jsonify({"status": "error", "message": "Command timeout"}), 500
    except Exception as e:
        add_log(f"命令失败", "error")
        return jsonify({"status": "error", "message": "Command failed"}), 500


@flask_app.route('/api/pid', methods=['GET'])
def get_pid():
    """获取服务进程 PID（无需验证）"""
    return jsonify({"status": "ok", "pid": os.getpid()})


def check_server_alive(port):
    """检查本地端口是否有服务在运行"""
    try:
        resp = urllib.request.urlopen(f"http://127.0.0.1:{port}/api/pid", timeout=2)
        data = json.loads(resp.read())
        return data.get("status") == "ok"
    except Exception:
        return False


def get_server_pid(port):
    """通过 API 获取运行中服务的 PID"""
    try:
        resp = urllib.request.urlopen(f"http://127.0.0.1:{port}/api/pid", timeout=2)
        data = json.loads(resp.read())
        return data.get("pid")
    except Exception:
        return None


# ============ SSH API 端点 ============

@flask_app.route('/api/ssh/key', methods=['GET'])
@require_trusted
def ssh_key():
    """返回加密密钥（已信任设备可用）"""
    config = load_config()
    return jsonify({"status": "ok", "encryption_key": config.get("encryption_key", "")})


@flask_app.route('/api/ssh/connect', methods=['POST'])
@require_trusted
def ssh_connect():
    """启动 SSH 会话"""
    device_id = request.headers.get('X-Device-ID')
    config = load_config()

    if not config.get('ssh_enabled', False):
        return jsonify({"status": "error", "message": "SSH 功能未启用"}), 400

    ssh_user = config.get('ssh_user', '').strip()
    if not ssh_user:
        return jsonify({"status": "error", "message": "未配置 SSH 登录用户"}), 400

    data = request.get_json() or {}
    password = data.get('password', '')
    cols = max(10, min(500, int(data.get('cols', 80))))
    rows = max(1, min(200, int(data.get('rows', 24))))
    if not password:
        return jsonify({"status": "error", "message": "需要密码"}), 400

    # 速率限制
    allowed, remaining = _check_rate(device_id, 10, 60)
    if not allowed:
        return jsonify({"status": "error", "message": "太频繁"}), 429

    # XOR 解密 (仅当客户端标记已加密时)
    if data.get('encrypted'):
        key = config.get("encryption_key", "")
        if key:
            password = _xor_crypt(password, key)

    if device_id in ssh_sessions:
        _cleanup_ssh_session(device_id)

    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            '127.0.0.1', port=22, username=ssh_user, password=password,
            timeout=10, allow_agent=False, look_for_keys=False
        )
        password = None  # 清除密码引用

        channel = client.get_transport().open_session()
        has_pty = True
        try:
            channel.get_pty(term='xterm', width=cols, height=rows)
        except paramiko.SSHException:
            has_pty = False  # Windows OpenSSH 不支持 PTY

        # 选择 shell: 配置 > 平台检测 > 默认
        ssh_shell = config.get('ssh_shell', '')
        if ssh_shell:
            shell_cmd = ssh_shell
        elif platform.system() == 'Windows':
            shell_cmd = 'powershell.exe -NoLogo'
        else:
            shell_cmd = '/bin/bash -i'
        channel.exec_command(shell_cmd)

        ssh_sessions[device_id] = {
            "client": client,
            "channel": channel,
            "buffer": bytearray(),
            "lock": threading.Lock(),
            "thread": None,
            "has_pty": has_pty,
            "last_active": time.time()
        }

        reader_thread = threading.Thread(
            target=_ssh_output_reader, args=(device_id,), daemon=True
        )
        reader_thread.start()
        ssh_sessions[device_id]["thread"] = reader_thread

        _start_ssh_cleaner()
        add_log(f"SSH 已连接: {ssh_user}@127.0.0.1 (设备: {device_id[:8]}...)", "success")
        return jsonify({"status": "ok", "message": "SSH 已连接"})

    except paramiko.AuthenticationException:
        return jsonify({"status": "error", "message": "认证失败"}), 401
    except Exception as e:
        add_log(f"SSH 连接失败: {str(e)[:60]}", "error")
        return jsonify({"status": "error", "message": "连接失败"}), 500


@flask_app.route('/api/ssh/input', methods=['POST'])
@decrypt_body
@require_trusted
def ssh_input():
    """向 SSH 会话发送输入"""
    device_id = request.headers.get('X-Device-ID')
    data = request._decrypted_data

    session = ssh_sessions.get(device_id)
    if not session:
        return jsonify({"status": "error", "message": "无活跃的 SSH 会话"}), 400

    input_text = data.get('input', '')
    if not input_text:
        return jsonify({"status": "error", "message": "输入为空"}), 400

    if len(input_text) > 1024:
        return jsonify({"status": "error", "message": "输入过长"}), 400

    try:
        session["channel"].send(input_text)
        session["last_active"] = time.time()
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@flask_app.route('/api/ssh/resize', methods=['POST'])
@require_trusted
def ssh_resize():
    """更新 SSH 会话的终端窗口尺寸"""
    device_id = request.headers.get('X-Device-ID')
    data = request.get_json() or {}
    cols = max(10, min(500, int(data.get('cols', 80))))
    rows = max(1, min(200, int(data.get('rows', 24))))

    session = ssh_sessions.get(device_id)
    if not session:
        return jsonify({"status": "error", "message": "无活跃的 SSH 会话"}), 400
    if not session.get("has_pty", True):
        return jsonify({"status": "error", "message": "当前环境不支持 PTY 调整"}), 400

    _set_pty_size(device_id, cols, rows)
    return jsonify({"status": "ok"})


@flask_app.route('/api/ssh/output', methods=['GET'])
@require_trusted
def ssh_output():
    """获取 SSH 会话的输出缓冲区"""
    device_id = request.headers.get('X-Device-ID')

    session = ssh_sessions.get(device_id)
    if not session:
        return jsonify({"status": "error", "message": "无活跃的 SSH 会话"}), 400

    with session["lock"]:
        data = bytes(session["buffer"])

    session["last_active"] = time.time()

    # Windows 控制台默认非 UTF-8
    if platform.system() == 'Windows':
        encoding = load_config().get('ssh_encoding', 'cp936')
    else:
        encoding = 'utf-8'
    text = data.decode(encoding, errors='replace')
    # 过滤 ANSI 转义序列: CSI OSC DCS SOS PM APC
    text = re.sub(r'\x1b\[[0-9;?]*[\x20-\x2f]*[\x40-\x7e]', '', text)
    text = re.sub(r'\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)', '', text)
    text = re.sub(r'\x1b[PX^_].*?(?:\x1b\\|\x07)', '', text)
    # 处理退格: 每遇到 \x08 就删除它前面的字符 (模拟终端擦除)
    while '\x08' in text:
        i = text.index('\x08')
        if i > 0:
            text = text[:i-1] + text[i+1:]
        else:
            text = text[i+1:]
    # 过滤残留控制字符 (保留 \n \t)
    text = re.sub(r'[\x00-\x08\x0b-\x0d\x0e-\x1f]', '', text)
    # 过滤 PAM/systemd audit 噪声行 (以 audit 字段开头的 key=value;... 行)
    text = re.sub(r'^(?:user|hostname|bootid|pid|type|cwd|_COMM|_EXE|_UID|_GID|_PID|_TRANSPORT|SYSLOG_FACILITY)=[^;\n]*(?:;[a-z_]+=[^;\n]*)*\n', '', text, flags=re.MULTILINE)
    # 截断总长度，保留尾部最新输出
    if len(text) > 10000:
        text = text[-10000:]
    return jsonify({"status": "ok", "output": text})


@flask_app.route('/api/ssh/heartbeat', methods=['GET'])
@require_trusted
def ssh_heartbeat():
    """SSH 会话心跳检测"""
    device_id = request.headers.get('X-Device-ID')

    session = ssh_sessions.get(device_id)
    if not session:
        return jsonify({"status": "ok", "alive": False})

    session["last_active"] = time.time()
    transport = session["client"].get_transport()
    alive = transport is not None and transport.is_active()
    return jsonify({"status": "ok", "alive": alive})


@flask_app.route('/api/ssh/disconnect', methods=['POST'])
@require_trusted
def ssh_disconnect():
    """断开 SSH 会话"""
    device_id = request.headers.get('X-Device-ID')

    if device_id not in ssh_sessions:
        return jsonify({"status": "error", "message": "无活跃的 SSH 会话"}), 400

    _cleanup_ssh_session(device_id)
    add_log(f"SSH 会话已断开 (设备: {device_id[:8]}...)", "info")
    return jsonify({"status": "ok", "message": "SSH 已断开"})


# ============ 系统信息函数 ============

def get_system_info():
    """获取系统信息（跨平台）"""
    hostname = platform.node()
    system = platform.system()
    
    if system == "Windows":
        version = f"Windows {platform.release()}"
    elif system == "Linux":
        try:
            with open('/etc/os-release', 'r') as f:
                for line in f:
                    if line.startswith('PRETTY_NAME='):
                        version = line.split('=', 1)[1].strip().strip('"')
                        break
                else:
                    version = f"Linux {platform.release()}"
        except (FileNotFoundError, PermissionError):
            version = f"Linux {platform.release()}"
    elif system == "Darwin":
        version = f"macOS {platform.mac_ver()[0]}"
    else:
        version = system
    
    return {"hostname": hostname, "version": version}


def get_battery_info():
    """获取电池信息（跨平台）"""
    system = platform.system()
    
    try:
        if system == "Windows":
            import psutil
            battery = psutil.sensors_battery()
            if battery:
                return {"has_battery": True, "percent": battery.percent, "charging": battery.power_plugged}
        
        elif system == "Linux":
            import glob
            batteries = glob.glob('/sys/class/power_supply/BAT*')
            if batteries:
                bat = batteries[0]
                try:
                    with open(f'{bat}/capacity', 'r') as f:
                        percent = int(f.read().strip())
                    with open(f'{bat}/status', 'r') as f:
                        status = f.read().strip()
                    return {"has_battery": True, "percent": percent, "charging": status == "Charging"}
                except (FileNotFoundError, ValueError):
                    pass
        
        elif system == "Darwin":
            try:
                result = subprocess.run(['pmset', '-g', 'batt'], capture_output=True, text=True, timeout=5)
                if 'InternalBattery' in result.stdout:
                    parts = result.stdout.split('\t')[1].split(';')
                    percent = int(parts[0].replace('%', '').strip())
                    charging = 'charging' in parts[1].lower() if len(parts) > 1 else False
                    return {"has_battery": True, "percent": percent, "charging": charging}
            except (subprocess.CalledProcessError, FileNotFoundError, IndexError, ValueError):
                pass
    
    except Exception:
        pass
    
    return {"has_battery": False}


# ============ GUI 函数 ============

def show_pair_dialog(device_id, device_name, port):
    """显示配对对话框，通过 API 响应配对请求"""
    import urllib.request

    def respond(action):
        try:
            data = json.dumps({
                "device_id": device_id,
                "device_name": device_name,
                "action": action
            }).encode()
            req = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/pair/respond",
                data=data,
                headers={"Content-Type": "application/json"}
            )
            urllib.request.urlopen(req, timeout=3)
        except Exception as ex:
            add_log(f"配对响应失败: {ex}", "error")

    def on_accept(e):
        respond("accept")
        add_log(f"已信任设备: {device_id[:8]}...", "success")
        dialog.open = False
        page_ref.update()
        refresh_log_list()
        refresh_devices()

    def on_reject(e):
        respond("reject")
        add_log(f"拒绝设备: {device_id[:8]}...", "error")
        dialog.open = False
        page_ref.update()
        refresh_log_list()

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("配对请求"),
        content=ft.Column([
            ft.Text("设备请求连接:"),
            ft.Container(
                content=ft.Text(device_id[:32] + "..." if len(device_id) > 32 else device_id,
                              size=14, color=ft.Colors.BLUE_300, selectable=True),
                bgcolor=ft.Colors.BLACK12,
                padding=10,
                border_radius=8
            ),
            ft.Text(f"设备名称: {device_name}", size=12),
        ], tight=True),
        actions=[
            ft.TextButton("拒绝", on_click=on_reject),
            ft.Button("信任此设备", on_click=on_accept),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    page_ref.overlay.append(dialog)
    dialog.open = True
    page_ref.update()




def refresh_devices():
    """刷新设备列表"""
    if devices_list_ref:
        devices = load_trusted_devices()
        devices_list_ref.controls.clear()
        if not devices:
            devices_list_ref.controls.append(
                ft.Text("暂无信任设备", size=12, color=ft.Colors.GREY_500)
            )
        else:
            for d in devices:
                devices_list_ref.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.WATCH, size=16, color=ft.Colors.GREEN_400),
                            ft.Column([
                                ft.Text(d.get('device_id', '')[:16] + "...", size=11, font_family="monospace"),
                                ft.Text(f"添加于: {d.get('trusted_at', '未知')[:19]}", size=10, color=ft.Colors.GREY_500)
                            ], spacing=2, expand=True),
                            ft.IconButton(
                                icon=ft.Icons.DELETE_OUTLINE,
                                icon_size=16,
                                tooltip="移除",
                                on_click=lambda _, did=d.get('device_id', ''): remove_device(did)
                            )
                        ]),
                        bgcolor=ft.Colors.BLACK12,
                        padding=8,
                        border_radius=6
                    )
                )
        devices_list_ref.update()


def remove_device(device_id):
    """移除信任设备"""
    if not device_id:
        return
    devices = load_trusted_devices()
    devices = [d for d in devices if d.get('device_id') != device_id]
    save_trusted_devices(devices)
    add_log(f"移除设备: {device_id[:8]}...", "warning")
    refresh_devices()
    refresh_log_list()


# ============ Flet GUI ============

def main(page: ft.Page):
    global page_ref, log_list_ref, devices_list_ref, server_running

    # PyInstaller 打包后会设置 LD_LIBRARY_PATH 指向临时目录，
    # 其中包含与系统不兼容的 .so 文件（如 libflexiblas），
    # 会导致通过 subprocess 调用的外部程序崩溃。
    if getattr(sys, 'frozen', False):
        os.environ.pop('LD_LIBRARY_PATH', None)

    page_ref = page

    # 程序图标
    if getattr(sys, 'frozen', False):
        icon_path = os.path.join(sys._MEIPASS, 'RemoteTerminal.png')
    else:
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'RemoteTerminal.png')

    if os.path.exists(icon_path):
        page.window.icon = icon_path
        # 仅在非 PyInstaller 环境下使用 Gtk 设置窗口图标。
        # PyInstaller 打包的 Gtk 图标主题不完整，且其 LD_LIBRARY_PATH
        # 会污染 flet 桌面客户端子进程，导致启动崩溃。
        if platform.system() == "Linux" and not getattr(sys, 'frozen', False):
            try:
                import gi
                gi.require_version('Gtk', '3.0')
                from gi.repository import Gtk, GLib
                Gtk.Window.set_default_icon_from_file(icon_path)
                GLib.set_prgname('remote-terminal-server')
            except Exception:
                pass

    # 窗口设置
    page.title = "远程终端"
    page.window.width = 500
    page.window.height = 650
    page.window.min_width = 420
    page.window.min_height = 550
    page.window.resizable = True
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20

    # 加载配置
    config = load_config()
    if "auto_start" not in config:
        config["auto_start"] = False
    if "background_run" not in config:
        config["background_run"] = False

    # 关闭窗口：后台运行模式保持服务进程，否则一并退出
    page.window.prevent_close = True

    def on_window_event(e: ft.WindowEvent):
        if e.type == ft.WindowEventType.CLOSE:
            if config.get("background_run") and server_running:
                add_log("窗口已关闭，服务在后台继续运行", "info")
                page.run_task(page.window.destroy)
            else:
                if flask_server:
                    flask_server.shutdown()
                page.run_task(page.window.destroy)

    page.window.on_event = on_window_event

    # 获取本机IP（优先192.168.x.x）
    local_ip = "未知"
    try:
        _hostname, _aliases, ips = socket.gethostbyname_ex(socket.gethostname())
        candidates = [ip for ip in ips if not ip.startswith('127.')]
        # 优先192.168.x.x
        for ip in candidates:
            if ip.startswith('192.168.'):
                local_ip = ip
                break
        if local_ip == "未知" and candidates:
            local_ip = candidates[0]
    except OSError:
        pass

    # 状态指示灯
    status_indicator = ft.Container(
        width=12, height=12, border_radius=6,
        bgcolor=ft.Colors.RED_400
    )
    status_text = ft.Text("服务未启动", size=14)

    # IP 显示
    ip_display = ft.Container(
        content=ft.Row([
            ft.Text("本机IP:", size=14, color=ft.Colors.GREY_400),
            ft.Text(local_ip, size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.CYAN_300),
            ft.IconButton(
                icon=ft.Icons.COPY, icon_size=16, tooltip="复制IP",
                on_click=lambda _: copy_to_clipboard(local_ip))
        ]),
        bgcolor=ft.Colors.BLACK26,
        padding=ft.Padding.symmetric(horizontal=15, vertical=10),
        border_radius=10
    )

    # 端口输入
    port_field = ft.TextField(
        label="端口", value="9000", width=120,
        text_align=ft.TextAlign.CENTER,
        keyboard_type=ft.KeyboardType.NUMBER
    )

    # 日志列表
    log_list = ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO, expand=True)
    log_list_ref = log_list

    # 信任设备列表
    devices_list = ft.Column(spacing=5, scroll=ft.ScrollMode.AUTO)
    devices_list_ref = devices_list

    def toggle_server(e):
        global server_running, flask_server, server_thread

        if not server_running:
            try:
                port = int(port_field.value)
                if port < 1 or port > 65535:
                    add_log("端口范围错误", "error")
                    refresh_log_list()
                    return
            except ValueError:
                add_log("端口格式错误", "error")
                refresh_log_list()
                return

            # 检查端口是否已被占用
            if check_server_alive(port):
                server_running = True
                status_indicator.bgcolor = ft.Colors.GREEN_400
                status_text.value = f"已连接到服务 :{port}"
                start_btn.text = "停止服务"
                start_btn.icon = ft.Icons.STOP
                port_field.disabled = True
                pid = get_server_pid(port)
                add_log(f"连接到已有服务进程 (PID: {pid})", "success")
                config["last_port"] = port
                save_config(config)
                refresh_log_list()
                page.update()
                return

            # 在线程中启动服务
            flask_server = make_server('0.0.0.0', port, flask_app)
            server_thread = threading.Thread(target=flask_server.serve_forever)
            server_thread.daemon = False  # 非守护线程，保证后台运行时进程存活
            server_thread.start()
            server_running = True
            status_indicator.bgcolor = ft.Colors.GREEN_400
            status_text.value = f"服务运行中 :{port}"
            start_btn.text = "停止服务"
            start_btn.icon = ft.Icons.STOP
            port_field.disabled = True
            add_log(f"服务已启动", "success")
            config["last_port"] = port
            save_config(config)
            cleanup_static_dir()
        else:
            # 清理所有 SSH 会话
            for did in list(ssh_sessions.keys()):
                _cleanup_ssh_session(did)
            if flask_server:
                flask_server.shutdown()
                flask_server = None
                server_thread = None
            else:
                # 连接到已有服务进程时，通过 PID 终止
                try:
                    port = int(port_field.value)
                except ValueError:
                    port = config.get("last_port", 9000)
                pid = get_server_pid(port)
                if pid is not None:
                    try:
                        os.kill(pid, signal.SIGTERM)
                        add_log(f"已终止服务进程 (PID: {pid})", "warning")
                    except ProcessLookupError:
                        pass
            server_running = False
            status_indicator.bgcolor = ft.Colors.RED_400
            status_text.value = "服务已停止"
            start_btn.text = "启动服务"
            start_btn.icon = ft.Icons.PLAY_ARROW
            port_field.disabled = False
            add_log("服务已停止", "warning")

        refresh_log_list()
        page.update()

    start_btn = ft.Button(
        "启动服务",
        icon=ft.Icons.PLAY_ARROW,
        on_click=toggle_server,
        style=ft.ButtonStyle(
            padding=ft.Padding.symmetric(horizontal=30, vertical=15)
        )
    )

    # 日志标签页
    log_tab_content = ft.Container(
        content=log_list,
        padding=10,
        expand=True
    )

    # 设备标签页
    devices_tab_content = ft.Container(
        content=devices_list,
        padding=10,
        expand=True
    )

    # 命令列表
    commands_list = ft.Column(spacing=5, scroll=ft.ScrollMode.AUTO, expand=True)

    def refresh_commands():
        commands_list.controls.clear()
        commands = load_commands()
        if not commands:
            commands_list.controls.append(
                ft.Text("暂无命令，点击下方添加", size=12, color=ft.Colors.GREY_500)
            )
        else:
            for i, cmd in enumerate(commands):
                idx = i
                commands_list.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Text(f"[{i}]", size=12, color=ft.Colors.GREY_500, width=30),
                            ft.Column([
                                ft.Text(cmd.get('name', f'命令 {i+1}'), size=14, weight=ft.FontWeight.BOLD),
                                ft.Text(cmd.get('command', '')[:40], size=11, color=ft.Colors.GREY_500, font_family="monospace"),
                            ], spacing=2, expand=True),
                            ft.IconButton(
                                icon=ft.Icons.DELETE_OUTLINE,
                                icon_size=16,
                                tooltip="删除",
                                on_click=lambda _, idx=idx: delete_command(idx)
                            )
                        ]),
                        bgcolor=ft.Colors.BLACK12,
                        padding=8,
                        border_radius=6
                    )
                )
        commands_list.update()

    def add_command(e):
        def on_save(e):
            name = name_field.value.strip()[:50] if name_field.value else f"命令 {len(load_commands()) + 1}"
            command = cmd_field.value.strip()[:200] if cmd_field.value else ""
            if command:
                commands = load_commands()
                commands.append({"name": name, "command": command})
                save_commands(commands)
                refresh_commands()
            dialog.open = False
            page.update()

        name_field = ft.TextField(label="备注名称", width=300)
        cmd_field = ft.TextField(label="命令内容", width=300)
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("添加命令"),
            content=ft.Column([name_field, cmd_field], tight=True),
            actions=[
                ft.TextButton("取消", on_click=lambda _: setattr(dialog, 'open', False) or page.update()),
                ft.Button("保存", on_click=on_save),
            ]
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    def delete_command(idx):
        commands = load_commands()
        if 0 <= idx < len(commands):
            commands.pop(idx)
            save_commands(commands)
            refresh_commands()

    # 命令标签页
    commands_tab_content = ft.Container(
        content=ft.Column([
            commands_list,
            ft.Container(
                content=ft.Button("添加命令", icon=ft.Icons.ADD, on_click=add_command),
                alignment=ft.Alignment.CENTER,
                padding=10
            )
        ]),
        padding=10,
        expand=True
    )

    # 设置开关
    def on_autostart_toggle(e):
        config["auto_start"] = e.control.value
        save_config(config)
        set_autostart(e.control.value, icon_path if os.path.exists(icon_path) else 'remote-terminal-server')
        if e.control.value:
            add_log("已启用开机自启动", "info")
        else:
            add_log("已禁用开机自启动", "info")
        refresh_log_list()

    autostart_switch = ft.Switch(
        value=config.get("auto_start", False),
        on_change=on_autostart_toggle,
        active_color=ft.Colors.BLUE_400,
        scale=0.8
    )

    def on_background_toggle(e):
        config["background_run"] = e.control.value
        save_config(config)
        if e.control.value:
            add_log("已启用服务器后台运行，关闭窗口后服务继续运行", "info")
        else:
            add_log("已禁用服务器后台运行，关闭窗口将退出程序", "info")
        refresh_log_list()

    background_switch = ft.Switch(
        value=config.get("background_run", False),
        on_change=on_background_toggle,
        active_color=ft.Colors.BLUE_400,
        scale=0.8
    )

    # SSH 功能诊断
    def diagnose_ssh():
        """测试 127.0.0.1:22 是否可达，不可达则诊断并给出指导"""
        try:
            sock = socket.create_connection(('127.0.0.1', 22), timeout=2)
            sock.close()
            add_log("SSH 服务 (127.0.0.1:22) 可用", "success")
            return True
        except ConnectionRefusedError:
            add_log("SSH 连接被拒绝 (127.0.0.1:22)", "warning")
            system = platform.system()
            if system == "Linux":
                try:
                    result = subprocess.run(['which', 'sshd'], capture_output=True, text=True, timeout=5)
                    sshd_installed = result.returncode == 0 and result.stdout.strip()
                except Exception:
                    sshd_installed = False

                if not sshd_installed:
                    _msg = "未检测到 OpenSSH 服务端。\n\n请运行以下命令安装:\nsudo dnf install openssh-server\nsudo systemctl enable --now sshd"
                else:
                    _msg = "SSH 服务已安装但未运行。\n\n请运行以下命令启动:\nsudo systemctl start sshd"
            elif system == "Windows":
                _msg = "请在 设置 > 应用 > 可选功能 中添加 OpenSSH 服务器，或通过 PowerShell 安装:\nAdd-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0\nStart-Service sshd"
            else:
                _msg = f"请确保 SSH 服务已在 127.0.0.1:22 上运行。\n当前系统: {system}"
            show_ssh_diag_dialog(_msg)
            return False
        except Exception as e:
            add_log(f"SSH 连接测试失败: {str(e)}", "warning")
            show_ssh_diag_dialog(f"无法连接到 127.0.0.1:22:\n{str(e)}\n\n请确保 SSH 服务已启动。")
            return False

    def show_ssh_diag_dialog(message):
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("SSH 连接诊断"),
            content=ft.Text(message, size=13),
            actions=[
                ft.TextButton("确定", on_click=lambda _: (setattr(dialog, 'open', False), page.update()))
            ]
        )
        page.overlay.append(dialog)
        dialog.open = True
        page.update()

    # SSH 用户名字段
    ssh_user_field = ft.TextField(
        value=config.get("ssh_user", ""),
        width=160,
        text_align=ft.TextAlign.RIGHT,
        on_change=lambda e: (config.update({"ssh_user": e.control.value.strip()}), save_config(config))
    )

    ssh_user_row = ft.Row([
        ft.Text("SSH 登录用户", size=14),
        ssh_user_field,
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, visible=config.get("ssh_enabled", False))

    # SSH 开关
    def on_ssh_toggle(e):
        if e.control.value:
            # 打开 → 弹窗警告
            def on_confirm(_):
                dialog.open = False
                config["ssh_enabled"] = True
                save_config(config)
                ssh_user_row.visible = True
                add_log("已启用 SSH 连接功能", "info")
                refresh_log_list()
                page.update()
                # 诊断 SSH 连接
                diagnose_ssh()

            dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text("安全警告"),
                content=ft.Text(
                    "远程终端使用 http 协议与 Vela 通信，这可能会带来安全风险，"
                    "请勿在公共网络下使用该功能。一切因使用 http SSH 功能造成的后果由用户自行承担。",
                    size=13
                ),
                actions=[
                    ft.TextButton("取消", on_click=lambda _: (
                        setattr(dialog, 'open', False),
                        setattr(ssh_switch, 'value', False),
                        page.update()
                    )),
                    ft.Button("确认", on_click=on_confirm),
                ]
            )

            page.overlay.append(dialog)
            dialog.open = True
            page.update()
        else:
            # 关闭
            config["ssh_enabled"] = False
            save_config(config)
            ssh_user_row.visible = False
            add_log("已禁用 SSH 连接功能", "info")
            refresh_log_list()
            page.update()

    ssh_switch = ft.Switch(
        value=config.get("ssh_enabled", False),
        on_change=on_ssh_toggle,
        active_color=ft.Colors.BLUE_400,
        scale=0.8
    )

    # 设置标签页
    settings_tab_content = ft.Container(
        content=ft.Column([
            ft.Text("开机自启", size=14),
            ft.Text("系统启动时自动运行远程终端", size=11, color=ft.Colors.GREY_400),
            ft.Row([ft.Container(expand=True), autostart_switch]),
            ft.Divider(height=1, color=ft.Colors.GREY_800),
            ft.Text("服务器后台运行", size=14),
            ft.Text("关闭窗口后服务继续在后台运行", size=11, color=ft.Colors.GREY_400),
            ft.Row([ft.Container(expand=True), background_switch]),
            ft.Divider(height=1, color=ft.Colors.GREY_800),
            ft.Text("允许通过 SSH 连接本机", size=14),
            ft.Text("开启后 Vela 设备可通过 SSH 控制本机终端", size=11, color=ft.Colors.GREY_400),
            ft.Row([ft.Container(expand=True), ssh_switch]),
            ssh_user_row,
        ], spacing=8, scroll=ft.ScrollMode.AUTO),
        padding=10,
        expand=True
    )

    # 标签页
    tabs = ft.Tabs(
        length=4,
        selected_index=0,
        animation_duration=300,
        expand=True,
        content=ft.Column(
            expand=True,
            controls=[
                ft.TabBar(
                    tabs=[
                        ft.Tab(label="日志", icon=ft.Icons.LIST_ALT),
                        ft.Tab(label="信任设备", icon=ft.Icons.WATCH),
                        ft.Tab(label="命令", icon=ft.Icons.TERMINAL),
                        ft.Tab(label="设置", icon=ft.Icons.SETTINGS),
                    ]
                ),
                ft.TabBarView(
                    expand=True,
                    controls=[log_tab_content, devices_tab_content, commands_tab_content, settings_tab_content]
                ),
            ]
        ),
    )

    # 布局
    page.add(
        ft.Column([
            ft.Container(
                content=ft.Row([
                    ft.Text("远程终端", size=20, weight=ft.FontWeight.BOLD),
                    ft.Container(expand=True),
                    ft.Row([status_indicator, status_text], spacing=8)
                ]),
                padding=ft.Padding.only(bottom=15)
            ),
            ip_display,
            ft.Container(
                content=ft.Row([
                    port_field,
                    start_btn,
                    ft.IconButton(
                        icon=ft.Icons.REFRESH, tooltip="刷新设备列表",
                        on_click=lambda _: refresh_devices()
                    )
                ], alignment=ft.MainAxisAlignment.START),
                padding=ft.Padding.only(top=5)
            ),
            ft.Container(content=tabs, expand=True, padding=ft.Padding.only(top=10)),
            # 版本信息
            ft.Container(
                content=ft.Row([
                    ft.Container(expand=True),
                    ft.Text(f"v{VERSION}  API Level {API_LEVEL}", size=11, color=ft.Colors.GREY_600),
                ]),
                padding=ft.Padding.only(top=5)
            ),
        ], expand=True)
    )

    # 初始化
    refresh_devices()
    refresh_commands()
    add_log("远程终端服务端已就绪", "info")
    refresh_log_list()

    # 依赖检查（Linux）
    if platform.system() == "Linux":
        missing_tools, missing_pkgs = check_dependencies()
        if missing_tools or missing_pkgs:
            show_dependency_dialog(missing_tools, missing_pkgs, page)

    # 首次启动提示
    show_first_launch_dialog(page)

    # 检测已有服务进程
    auto_port = config.get("last_port", 9000)
    if check_server_alive(auto_port):
        server_running = True
        pid = get_server_pid(auto_port)
        port_field.value = str(auto_port)
        port_field.disabled = True
        status_indicator.bgcolor = ft.Colors.GREEN_400
        status_text.value = f"已连接到服务 :{auto_port}"
        start_btn.text = "停止服务"
        start_btn.icon = ft.Icons.STOP
        add_log(f"检测到正在运行的服务 (PID: {pid})", "success")
        refresh_log_list()
        page.update()
    else:
        # 启动应用自动启动服务端
        toggle_server(None)

    # 配对请求轮询（在 Flet 事件循环中运行）
    async def poll_pending_pairs():
        shown = set()
        while True:
            await asyncio.sleep(2)
            try:
                port = int(port_field.value) if not port_field.disabled else config.get("last_port", 9000)
                resp = urllib.request.urlopen(f"http://127.0.0.1:{port}/api/pending_pair", timeout=2)
                data = json.loads(resp.read())
                for pair in data.get("pairs", []):
                    did = pair.get("device_id")
                    if did and did not in shown:
                        shown.add(did)
                        show_pair_dialog(did, pair.get("device_name", "Unknown"), port)
            except Exception:
                pass

    page.run_task(poll_pending_pairs)


if __name__ == "__main__":
    ft.run(main)
