"""
功能二：批量解析
对选中的UP主查询最新视频 → 批量调bili2text
"""
import sys
import time
from pathlib import Path

if getattr(sys, 'frozen', False):
    PROJECT_ROOT = Path(sys._MEIPASS)
else:
    PROJECT_ROOT = Path(__file__).parent.parent

SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from backend.single_parser import parse_single, BILI2TEXT_DIR, BILI2TEXT_PY, VENV_PYTHON
import step1_fetch_videos as fetcher


def batch_parse(uid_list: list, save_dir: str, callback=None, cancel_event=None):
    """批量解析选中UP主的最新视频

    Args:
        uid_list: UID列表
        save_dir: 保存根目录
        callback: 回调函数 (type, message, percent)
            percent: 0-100，progress/success/cancelled/error 均返回
        cancel_event: threading.Event，设为 True 时中止
    """
    import threading as _th
    if cancel_event is None:
        cancel_event = _th.Event()

    cookies = fetcher.load_cookies()
    if not cookies:
        if callback:
            callback("error", "B站Cookie无效，请检查 config/bilibili_cookies.txt", 0)
        return {"success": False, "error": "Cookie无效"}

    headers = fetcher.build_headers(cookies)
    total = len(uid_list)
    results = []

    for idx, uid in enumerate(uid_list):
        if cancel_event.is_set():
            if callback:
                callback("cancelled", f"批量解析已取消，已完成 {idx}/{total} 个UP主", 0)
            return {"success": False, "cancelled": True, "total": len(results), "success_count": sum(1 for r in results if r.get("success")), "results": results}

        up_pct = int(idx / total * 100)
        if callback:
            callback("progress", f"正在查询UP主 {uid}... ({idx+1}/{total})", up_pct)

        videos = fetcher.get_up_videos(uid, headers, hours=48)

        if not videos:
            if callback:
                callback("progress", f"UP主 {uid} 48小时内无新视频，跳过", up_pct)
            continue

        if callback:
            callback("progress", f"UP主 {uid} 有 {len(videos)} 个新视频，开始转写...", up_pct)

        for v_idx, v in enumerate(videos):
            if cancel_event.is_set():
                if callback:
                    callback("cancelled", f"批量解析已取消", 0)
                return {"success": False, "cancelled": True, "total": len(results), "success_count": sum(1 for r in results if r.get("success")), "results": results}

            bvid = v.get("bvid")
            title = v.get("title", "")
            if not bvid:
                continue

            # 批次内百分比 = (已完成UP主 + 当前UP主内的进度) / 总UP主数 * 100
            sub_pct = (v_idx + 1) / len(videos)
            batch_pct = min(int((idx + sub_pct) / total * 100), 99)

            video_dir = Path(save_dir) / uid / bvid
            video_dir.mkdir(parents=True, exist_ok=True)

            if callback:
                callback("progress", f"  转写：{title} ({bvid})", batch_pct)

            result = parse_single(bvid, str(video_dir), cancel_event=cancel_event)
            results.append({"uid": uid, "bvid": bvid, "title": title, **result})
            time.sleep(1)  # 礼貌间隔

    success_count = sum(1 for r in results if r.get("success"))
    if callback:
        callback("done", f"批量解析完成：成功 {success_count}/{len(results)} 个视频", 100)

    return {"success": True, "total": len(results), "success_count": success_count, "results": results}
