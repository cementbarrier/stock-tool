"""
单视频 AI 摘要客户端：含时段判断分支，支持自动入队或强制执行
"""
from backend.llm_client import chat
from backend.time_price_judge import is_peak, get_warning_text, get_price_label
from backend.task_queue_manager import enqueue


MAX_TRANSCRIPT_LEN = 3000  # 送入 LLM 的最大转写文本长度


def summarize_single(
    bv_id: str,
    transcript: str,
    title: str = "",
    force: bool = False,
) -> dict:
    """
    单视频 AI 摘要。

    参数:
        bv_id:      视频 BV 号
        transcript: 完整转写文本
        title:      视频标题（可选）
        force:      True=强制执行（忽略时段），False=高峰自动入队

    返回:
        {"status": "done", "summary": "..."}  或
        {"status": "queued", "task_id": "xxx", "warning": "..."}
    """
    if not force and is_peak():
        task_id = enqueue(
            task_type="single_summary",
            payload={
                "bv_id": bv_id,
                "title": title,
                "transcript": transcript,
            },
        )
        return {
            "status": "queued",
            "task_id": task_id,
            "warning": get_warning_text(),
            "price_label": get_price_label(),
        }

    prompt = _build_prompt(transcript, title)
    try:
        summary = chat(prompt)
        return {"status": "done", "summary": summary}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _build_prompt(transcript: str, title: str = "") -> str:
    text = transcript[:MAX_TRANSCRIPT_LEN]
    header = ""
    if title:
        header = f"视频标题：{title}\n\n"
    return f"""{header}请完成以下两步任务：

【第一步】用80字以内总结以下B站视频中提到的股票核心观点，输出纯文本。

【第二步】逐条核实你上一步的总结：
1. 所有提到的股票名称/代码/公司名是否与原文完全一致？如有错误，修正并标注原因。
2. 所有数字（价格、点位、百分比、日期）是否与原文一致？如有错误，修正并标注原因。
3. 观点归属是否准确（谁的看法、来源是谁）？如有歧义，说明。

最终输出格式：
**摘要**：[你的总结]
**核实**：[逐条核实结果，无可修正则写"无"；有修正则列出原文 vs 修正]

原文：
{text}"""

