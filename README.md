# 观点采集

B 站视频字幕批量解析与 UP 主定期跟踪工具。基于 bili2text 转写引擎，提取视频字幕用于股票观点采集。

## 功能

- **单视频解析**：输入 B 站 BV 号，自动下载音频、转写字幕并保存
- **AI 摘要**：基于大模型生成视频观点摘要，含事实核实机制（校准股票名/数字/观点归属）
- **错峰调度**：DeepSeek 峰谷定价感知，高峰自动入队、低谷自动消费队列
- **定期跟踪**：管理 UP 主列表，批量解析最新视频字幕
- **配置管理**：自定义 bili2text 路径、B 站 Cookie、调试日志路径
- **大模型集成**：支持 DeepSeek 和火山方舟（豆包），可在配置页切换

## 快速开始

项目自带独立 Python 运行环境，无需系统预装 Python：

```powershell
git clone https://github.com/cementbarrier/stock-tool.git
cd stock-tool
setup.bat
```

`setup.bat` 会自动完成：下载 Python 3.11.9 → 安装到项目 `runtime\` → 安装所有依赖。

## 使用

```powershell
# 直接运行
runtime\python.exe gui\build\gui.py

# 打包为 EXE
runtime\python.exe -m PyInstaller --onefile --windowed --name gui --paths scripts --add-data "backend;backend" --add-data "scripts;scripts" --add-data "gui\build\assets;gui\build\assets" --hidden-import requests --hidden-import step1_fetch_videos --hidden-import step2_download_audio --hidden-import step3_transcribe --hidden-import step4_extract_stocks --hidden-import step5_analyze --hidden-import backend.config_manager --hidden-import backend.llm_client --hidden-import backend.single_parser --hidden-import backend.batch_parser --hidden-import backend.up_manager --hidden-import backend.single_summary_client --hidden-import backend.task_queue_manager --hidden-import backend.time_price_judge --hidden-import backend.valley_scheduler gui\build\gui.py
```

首次使用请在**配置页**中设置 bili2text 路径和 B 站 Cookie。

### bili2text 安装（系统需单独安装）

bili2text 是核心转写引擎：

```powershell
git clone https://github.com/lanbinshijie/bili2text.git D:\bili2text
cd D:\bili2text
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

首次使用请在**配置页**中设置 bili2text 路径和 B 站 Cookie。Cookie 文件默认位于 `D:\bili2text\.b2t\cookies.txt`。

### 大模型配置

在配置页「大模型」分区设置：

| 字段 | 说明 |
|------|------|
| 提供商 | 可选 DeepSeek 或火山方舟/豆包 |
| API Key | 对应平台的 API 密钥 |
| 模型名 | 切换提供商会自动更新可选模型列表 |

配置完成后点击「保存配置」。

## 项目结构

```
stock-tool/
├── gui/
│   └── build/
│       └── gui.py              # 主界面（由 fixed_generator.py 生成）
├── backend/
│   ├── single_parser.py        # 单视频解析
│   ├── batch_parser.py         # 批量解析
│   ├── up_manager.py           # UP主列表管理
│   ├── config_manager.py       # 配置管理
│   ├── llm_client.py           # 大模型统一接口（DeepSeek/火山方舟）
│   ├── single_summary_client.py # 单视频AI摘要（含事实核实）
│   ├── task_queue_manager.py   # 错峰任务队列
│   ├── time_price_judge.py     # 峰谷时段判断
│   └── valley_scheduler.py     # 低谷调度器
├── scripts/                    # 流水线脚本
├── setup.bat                   # 一键环境初始化
├── requirements.txt            # Python 依赖清单
├── fixed_generator.py          # GUI 生成器
└── gui.spec                    # PyInstaller 打包配置
```

## 许可证

MIT
