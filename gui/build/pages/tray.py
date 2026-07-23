# -*- coding: utf-8 -*-
"""系统托盘逻辑（右键菜单、还原/退出）"""

import threading

try:
    from PIL import Image, ImageDraw
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import pystray
    HAS_TRAY = True
except ImportError:
    HAS_TRAY = False

# ── 模块级状态 ──
_tray_icon = None
_should_exit = False
_handling_minimize = False

# 外部注入
_valley_scheduler = None


def set_valley_scheduler(scheduler):
    global _valley_scheduler
    _valley_scheduler = scheduler


def _create_tray_image():
    """生成托盘图标（64x64 红色K线风格）"""
    img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rectangle([8, 8, 56, 56], fill=(178, 34, 34), outline=(128, 0, 0), width=2)
    draw.line([(20, 42), (30, 26), (38, 36), (48, 20)], fill=(255, 255, 255), width=4)
    return img


def _restore_window(window, icon, item=None):
    global _handling_minimize
    _handling_minimize = False
    window.deiconify()
    window.state('normal')
    window.lift()
    window.focus_force()


def _quit_app(window, icon, item=None):
    global _tray_icon, _should_exit, _valley_scheduler
    _should_exit = True
    if _tray_icon:
        _tray_icon.stop()
        _tray_icon = None
    try:
        if _valley_scheduler:
            _valley_scheduler.stop()
    except Exception:
        pass
    window.destroy()


def _hide_to_tray(window):
    if not HAS_TRAY:
        return
    window.withdraw()


def _on_window_close(window):
    global _should_exit
    if _should_exit:
        _quit_app(window, None)
        return
    _hide_to_tray(window)


def _on_unmap(window, event):
    global _handling_minimize, _should_exit
    if _handling_minimize or _should_exit:
        return
    if event.widget is window and window.state() == 'iconic':
        _handling_minimize = True
        _hide_to_tray(window)


def init_tray(window):
    """初始化系统托盘图标"""
    global _tray_icon
    if not HAS_TRAY:
        return
    if _tray_icon is not None:
        return
    menu = pystray.Menu(
        pystray.MenuItem('显示', lambda icon, item: _restore_window(window, icon, item), default=True),
        pystray.MenuItem('退出', lambda icon, item: _quit_app(window, icon, item)),
    )
    _tray_icon = pystray.Icon('bilidigest', _create_tray_image(), 'BiliDigest', menu)
    threading.Thread(target=_tray_icon.run, daemon=True).start()


def setup_window_tray_hooks(window):
    """设置窗口的关闭和最小化托盘钩子"""
    if HAS_TRAY:
        window.protocol('WM_DELETE_WINDOW', lambda: _on_window_close(window))
        window.bind('<Unmap>', lambda e: _on_unmap(window, e), add='+')
