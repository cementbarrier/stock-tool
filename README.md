# 观点采集

B 站视频字幕批量解析与 UP 主定期跟踪工具。基于 bili2text 转写引擎，提取视频字幕用于股票观点采集。

## 功能

- **单视频解析**：输入 B 站 BV 号，自动下载音频、转写字幕并保存
- **定期跟踪**：管理 UP 主列表，批量解析最新视频字幕
- **配置管理**：自定义 bili2text 路径、B 站 Cookie、调试日志路径
- **大模型集成**：支持 DeepSeek 和火山方舟（豆包），可在配置页切换，用于观点分析交叉验证

## 依赖

### 运行环境
- Python 3.11+
- Windows 10+

### 核心依赖
```
bili2text（需单独安装配置）
Pillow
pandas
openpyxl
requests
```

### bili2text 安装

bili2text 是核心转写引擎，需独立安装：

```powershell
# 克隆并创建虚拟环境
git clone https://github.com/lanbinshijie/bili2text.git D:\bili2text
cd D:\bili2text

# 安装依赖
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 安装

```powershell
# 克隆仓库
git clone https://github.com/cementbarrier/stock-tool.git
cd stock-tool

# 创建虚拟环境
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install Pillow pandas openpyxl requests
```

## 使用

```powershell
# 直接运行
python gui\build\gui.py

# 或打包为 EXE
pip install pyinstaller
pyinstaller gui.spec
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
│       └── gui.py          # 主界面
├── backend/
│   ├── single_parser.py    # 单视频解析
│   ├── batch_parser.py     # 批量解析
│   ├── up_manager.py       # UP主列表管理
│   ├── config_manager.py   # 配置管理
│   └── llm_client.py       # 大模型统一接口
├── scripts/                # 流水线脚本
├── config/                 # 配置与数据文件
└── gui.spec                # PyInstaller 打包配置
```

## 许可证

MIT
