"""
UP主数据管理
读取/保存 stock_up_list.xlsx，提供表格数据
"""
import sys
import pandas as pd
from pathlib import Path

if getattr(sys, 'frozen', False):
    PROJECT_ROOT = Path(sys._MEIPASS)
else:
    PROJECT_ROOT = Path(__file__).parent.parent

CONFIG_DIR = PROJECT_ROOT / "config"


def load_up_list():
    """读取UP主列表，返回 [{uid, name, weight}, ...]"""
    path = CONFIG_DIR / "stock_up_list.xlsx"
    if not path.exists():
        return [{"uid": "U1001", "name": "示例名称1", "weight": 1}]

    df = pd.read_excel(path)
    rows = []
    for _, row in df.iterrows():
        uid = str(int(row.iloc[0])) if not pd.isna(row.iloc[0]) else ""
        name = str(row.iloc[1]).strip() if not pd.isna(row.iloc[1]) else ""
        weight = int(row.iloc[2]) if not pd.isna(row.iloc[2]) else 1
        if uid and name:
            rows.append({"uid": uid, "name": name, "weight": weight})
    return rows


def save_up_list(rows: list):
    """保存UP主列表到Excel"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    path = CONFIG_DIR / "stock_up_list.xlsx"
    df = pd.DataFrame(rows, columns=["uid", "name", "weight"])
    df.to_excel(path, index=False)
    return True
