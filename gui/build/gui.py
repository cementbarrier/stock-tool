# -*- coding: utf-8 -*-
# BiliDigest GUI — 主入口（窗口创建、页面组装、事件绑定）
# 各页面 UI 已拆分至 gui/build/pages/ 目录

import sys
import os as _os
from pathlib import Path

if getattr(sys, 'frozen', False):
    pass
else:
    _project_root = Path(__file__).parent.parent.parent
    if str(_project_root) not in sys.path:
        sys.path.insert(0, str(_project_root))

from tkinter import (
    Button, Canvas, Frame, Label, Tk, messagebox,
)
from backend import valley_scheduler, config_manager

from .utils import create_rounded_rectangle, center_window
from .pages.page_parse import build_page_parse, set_refresh_callback as _p1_set_refresh
from .pages.page_batch import build_page_batch, set_refresh_callback as _p2_set_refresh
from .pages.page_config import build_page_config, set_refresh_callback as _p3_set_refresh
from .pages.tray import init_tray, setup_window_tray_hooks, set_valley_scheduler

# ── 全局 pages 列表（供 show_page 切换）──
pages = []
sidebar_buttons = []


def show_page(index):
    """切换显示的内容页面"""
    for i, btn in enumerate(sidebar_buttons):
        if i == index:
            btn.configure(bg="#F7F7F7", activebackground="#F7F7F7")
        else:
            btn.configure(bg="#FFFFFF", activebackground="#FFFFFF")

    for i, page in enumerate(pages):
        if i == index:
            page.place(x=198, y=0, width=796, height=666)
        else:
            page.place_forget()

    # 配置页滚动条随页面 2 显示/隐藏
    if index == 2 and _cfg_v_scrollbar is not None:
        _cfg_v_scrollbar.place(x=974, y=0, height=666)
    elif _cfg_v_scrollbar is not None:
        _cfg_v_scrollbar.place_forget()


# 配置页滚动条（需要全局引用以便 show_page 控制）
_cfg_v_scrollbar = None


def create_main_window():
    global _cfg_v_scrollbar

    window = Tk()
    window.title("BiliDigest")
    window.geometry("994x666")
    window.configure(bg="#FFFFFF")
    center_window(window, 994, 666)

    setup_window_tray_hooks(window)

    canvas = Canvas(
        window,
        bg="#FFFFFF",
        height=666,
        width=994,
        bd=0,
        highlightthickness=0,
        relief="ridge"
    )
    canvas.place(x=0, y=0)

    # ── 侧边栏背景 ──
    create_rounded_rectangle(canvas, 0, 0, 198, 665, 2,
                             fill="#FFFFFF", outline="#000000")
    canvas.create_rectangle(0, 0, 198, 666,
                            fill="#FFFFFF", outline="#e0e0e0")
    create_rounded_rectangle(canvas, 8, 82, 191, 122, 8,
                             fill="#FFFFFF", outline="")

    # ── 侧边栏标题 ──
    label_title = Label(
        window,
        text="观点采集",
        bg="#FFFFFF",
        fg="#000000",
        font=("Inter", 16, "bold"),
        anchor="center"
    )
    label_title.place(x=8, y=80, width=183, height=36)

    # ── 侧边栏按钮 ──
    btn1 = Button(window, text="单视频解析", bg="#F7F7F7", fg="#000000",
                  font=("Inter", 16, "normal"), borderwidth=0, highlightthickness=0,
                  command=lambda: show_page(0),
                  relief="flat", activebackground="#F7F7F7", cursor="hand2")
    btn1.place(x=8, y=134, width=183, height=40)

    btn2 = Button(window, text="定期跟踪", bg="#FFFFFF", fg="#000000",
                  font=("Inter", 16, "normal"), borderwidth=0, highlightthickness=0,
                  command=lambda: show_page(1),
                  relief="flat", activebackground="#FFFFFF", cursor="hand2")
    btn2.place(x=8, y=186, width=183, height=40)

    btn3 = Button(window, text="配置", bg="#FFFFFF", fg="#000000",
                  font=("Inter", 16, "normal"), borderwidth=0, highlightthickness=0,
                  command=lambda: show_page(2),
                  relief="flat", activebackground="#FFFFFF", cursor="hand2")
    btn3.place(x=8, y=238, width=183, height=40)

    sidebar_buttons.extend([btn1, btn2, btn3])

    # ── 页面 1：单视频解析 ──
    page_frame_1 = Frame(window, bg="#FFFFFF", borderwidth=0, highlightthickness=0)
    page_frame_1.place(x=198, y=0, width=796, height=666)
    pages.append(page_frame_1)
    _, ui1 = build_page_parse(window, page_frame_1)

    # ── 页面 2：定期跟踪 ──
    page_frame_2 = Frame(window, bg="#FFFFFF", borderwidth=0, highlightthickness=0)
    pages.append(page_frame_2)
    _, ui2 = build_page_batch(window, page_frame_2)

    # ── 页面 3：配置 ──
    scroll_canvas_3, ui3 = build_page_config(window, None, window)
    pages.append(scroll_canvas_3)
    _cfg_v_scrollbar = ui3["v_scrollbar_3"]

    # ── 统一队列刷新回调 ──
    queue_refresh = ui3["refresh_queue_status"]

    def _gui_refresh_queue():
        queue_refresh()

    _p1_set_refresh(_gui_refresh_queue)
    _p2_set_refresh(_gui_refresh_queue)
    _p3_set_refresh(_gui_refresh_queue)

    # ── 初次显示（默认页面 0）──
    show_page(0)

    window.resizable(False, False)
    init_tray(window)

    return window, _gui_refresh_queue, queue_refresh


# ── 启动 ──
window, _gui_refresh_queue, _queue_refresh_fn = create_main_window()

# ── 启动时检测配置损坏 ──
_load_error_path = config_manager.CONFIG_DIR / "_load_error.log"
if _load_error_path.exists():
    try:
        _err_text = _load_error_path.read_text(encoding="utf-8")
        messagebox.showwarning(
            "配置损坏警告",
            f"配置文件加载失败，已回退为默认设置。\n\n"
            f"错误详情请查看：\n{_load_error_path}\n\n"
            f"您可以尝试在配置页重新保存设置来修复。"
        )
    except Exception:
        pass

# 启动低谷调度线程
set_valley_scheduler(valley_scheduler)
valley_scheduler.start(
    callback=lambda n: window.after(0, _gui_refresh_queue) if _gui_refresh_queue else None
)

if __name__ == "__main__":
    # 单实例锁
    _lock_path = Path(_os.environ.get("TEMP", ".")) / "stock_tool_instance.lock"
    try:
        import msvcrt
        _lock_fd = _os.open(str(_lock_path), _os.O_CREAT | _os.O_RDWR, 0o644)
        try:
            msvcrt.locking(_lock_fd, msvcrt.LK_NBLCK, 1)
        except _os.error:
            _os.close(_lock_fd)
            messagebox.showwarning("股票工具", "程序已在运行中（可能隐藏在托盘区）")
            sys.exit(0)
    except Exception:
        pass
    window.mainloop()
