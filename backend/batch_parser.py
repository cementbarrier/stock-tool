"""
功能二：批量解析
对选中的UP主查询最新视频 → 批量调bili2text → 统一 AI 摘要
"""
import sys
import os
import time
from pathlib import Path
from datetime import datetime

if getattr(sys, 'frozen', False):
    PROJECT_ROOT = Path(sys._MEIPASS)
else:
    PROJECT_ROOT = Path(__file__).parent.parent

SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from backend.single_parser import parse_single, BILI2TEXT_DIR, BILI2TEXT_PY, VENV_PYTHON
import step1_fetch_videos as fetcher

SUMMARY_FILENAME = "ai_summary.txt"
BATCH_SUMMARY_FILENAME = "批次总结_{date}.txt"


def batch_parse(uid_list: list, save_dir: str, callback=None, cancel_event=None, target_date=None):
    """批量解析选中UP主的最新视频

    两阶段执行：
      Phase 1 — 拉取视频 + bili2text 转写（逐个进行）
      Phase 2 — 全部转写完成后，一次性生成批次总结文档

    Args:
        uid_list: UID列表
        save_dir: 保存根目录
        callback: 回调函数 (type, message, percent)
        cancel_event: threading.Event，设为 True 时中止
        target_date: 目标日期 'YYYY-MM-DD'，默认今天
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

    # ── Phase 1: 拉取 + 转写 ──
    for idx, uid in enumerate(uid_list):
        if cancel_event.is_set():
            if callback:
                callback("cancelled", f"批量解析已取消，已完成 {idx}/{total} 个UP主", 0)
            return _build_return(results, cancelled=True)

        # 进度：查询阶段占每个UP主 30% 权重，转写占 70%
        up_pct_start = int(idx / total * 100)
        if callback:
            callback("progress", f"正在查询UP主 {uid}... ({idx+1}/{total})", up_pct_start)

        date_label = target_date if target_date else "今日"
        videos = fetcher.get_up_videos(uid, headers, target_date=target_date, cancel_event=cancel_event)

        if cancel_event.is_set():
            if callback:
                callback("cancelled", f"批量解析已取消", 0)
            return _build_return(results, cancelled=True)

        if not videos:
            # 无视频：查询完成即跳过，进度跳到下一个UP主
            up_pct_next = int((idx + 1) / total * 100)
            if callback:
                callback("progress", f"UP主 {uid} {date_label}无新视频，跳过", up_pct_next)
            continue

        up_pct_query_done = min(int((idx + 0.3) / total * 100), 99)
        if callback:
            callback("progress", f"UP主 {uid} 有 {len(videos)} 个新视频，开始转写...", up_pct_query_done)

        for v_idx, v in enumerate(videos):
            if cancel_event.is_set():
                if callback:
                    callback("cancelled", f"批量解析已取消", 0)
                return _build_return(results, cancelled=True)

            bvid = v.get("bvid")
            title = v.get("title", "")
            if not bvid:
                continue

            batch_pct = min(int((idx + 0.3 + 0.7 * (v_idx + 1) / len(videos)) / total * 100), 99)

            date_prefix = datetime.now().strftime("%m%d")
            video_dir = Path(save_dir) / date_prefix / uid / bvid
            video_dir.mkdir(parents=True, exist_ok=True)

            # 已有转写文件则跳过
            existing_txt = list(video_dir.glob("*.txt"))
            if existing_txt:
                if callback:
                    callback("progress", f"  跳过（已有转写）：{title} ({bvid})", batch_pct)
                results.append({"uid": uid, "bvid": bvid, "title": title, "video_dir": str(video_dir), "success": True, "path": str(existing_txt[0]), "skipped": True})
                continue

            if callback:
                callback("progress", f"  转写：{title} ({bvid})", batch_pct)

            result = parse_single(bvid, str(video_dir), cancel_event=cancel_event)
            results.append({"uid": uid, "bvid": bvid, "title": title, "video_dir": str(video_dir), **result})
            time.sleep(1)

    # ── Phase 2: 生成批次总结文档 ──
    # 仅本次新转写的视频参与 AI 总结，存量跳过的不参与
    transcribe_success = [r for r in results if r.get("success") and r.get("path") and not r.get("skipped")]
    new_count = len(transcribe_success)
    if new_count == 0:
        skipped_count = sum(1 for r in results if r.get("skipped"))
        if callback:
            callback("done", f"批量解析完成：无新增转写，跳过 AI 总结（存量 {skipped_count} 个已有转写）", 100)
        return _build_return(results)

    if callback:
        callback("progress", f"转写完成，正在生成批次总结（新增 {new_count} 个视频）...", 99)

    batch_summary_path = _generate_batch_summary(save_dir, transcribe_success)

    # ── 邮件通知 ──
    try:
        from backend.notifier import notify_batch_done
        notify_batch_done(save_dir, new_count, len(results), batch_summary_path)
    except Exception:
        pass

    if callback:
        done_msg = f"批量解析完成：新增转写 {new_count}/{len(results)} 个视频"
        if batch_summary_path:
            done_msg += f"，总结已生成"
        callback("done", done_msg, 100)

    return _build_return(results, summarized=(1 if batch_summary_path else 0))


def _generate_batch_summary(save_dir: str, transcribe_success: list) -> str | None:
    """
    将批次内全部转写结果一次发给 LLM，生成总结文档（两部分）。

    Returns:
        生成的文件路径，失败返回 None
    """
    from backend.llm_client import chat

    MAX_PER_VIDEO = 1500  # 每视频最多送 1500 字

    parts = []
    for r in transcribe_success:
        bvid = r["bvid"]
        title = r["title"]
        try:
            text = Path(r["path"]).read_text(encoding="utf-8")[:MAX_PER_VIDEO]
        except Exception:
            continue
        parts.append(f"<video bvid=\"{bvid}\" title=\"{title}\">\n{text}\n</video>")

    if not parts:
        return None

    all_videos = "\n\n".join(parts)

    prompt = f"""以下是本批次中 {len(parts)} 个B站财经视频的转写文本。请输出一份总结文档，严格按以下两段格式：

一、视频观点速览
| BV号 | 主要观点 |

二、入场参考
| 板块/标的 | 入场理由 |

要求：
- 第一部分：每个视频一行，用80字以内提炼核心观点
- 第二部分：仅列出明确看多/可入场的标的，看空/分歧/观望全部略过；入场理由中附带对应BV号
- 若第二部分无可入场标的，写"本批次无可入场标的"
- 不要开头结尾、不要解释
- 转写文本可能存在语音识别错误，请根据上下文纠正为正确的股票术语。常见错误示例：'5G线'→'5日线'或'5周线'，'黄氏线'→'5日线'或'20日线'，'50线'→'5日线'，数字/字母与股票术语混淆时优先理解为均线指标

视频文本：
{all_videos}"""

    try:
        result = chat(prompt)
    except Exception:
        return None

    if not result:
        return None

    today = datetime.now().strftime("%Y-%m-%d")
    report_path = Path(save_dir) / BATCH_SUMMARY_FILENAME.format(date=today)
    report_path.write_text(result, encoding="utf-8")
    return str(report_path)


def _build_return(results: list, cancelled=False, summarized=0):
    success_count = sum(1 for r in results if r.get("success"))
    return {
        "success": not cancelled,
        "cancelled": cancelled,
        "total": len(results),
        "success_count": success_count,
        "summarized": summarized,
        "results": results,
    }


def fill_missing_summaries(save_dir: str, callback=None, cancel_event=None):
    """扫描 save_dir 下所有转写 txt，重新生成批次总结文档

    Args:
        save_dir: 批量解析保存根目录
        callback: 回调 (type, message, percent)
        cancel_event: threading.Event
    """
    import threading as _th
    if cancel_event is None:
        cancel_event = _th.Event()

    root = Path(save_dir)
    if not root.exists():
        if callback:
            callback("error", f"保存目录不存在：{save_dir}", 0)
        return {"success": False, "error": "目录不存在"}

    # 扫描所有转写 txt（排除 SUMMARY_FILENAME 和已有的批次总结）
    today = datetime.now().strftime("%Y-%m-%d")
    batch_file = root / BATCH_SUMMARY_FILENAME.format(date=today)

    entries = []
    for txt_path in root.rglob("*.txt"):
        if txt_path.name == SUMMARY_FILENAME:
            continue
        if txt_path.name == batch_file.name:
            continue
        bvid = txt_path.parent.name
        entries.append({"bvid": bvid, "title": f"{txt_path.parent.parent.name}/{bvid}", "path": str(txt_path)})

    if not entries:
        if callback:
            callback("done", "未找到转写文件", 100)
        return {"success": True, "total": 0, "summarized": 0}

    if callback:
        callback("progress", f"发现 {len(entries)} 个转写文件，重新生成批次总结...", 50)

    result = _generate_batch_summary(save_dir, entries)

    if callback:
        if result:
            callback("done", f"批次总结已生成：{os.path.basename(result)}", 100)
        else:
            callback("error", "批次总结生成失败", 100)

    return {"success": result is not None, "total": len(entries), "summarized": 1 if result else 0}
