# stock-tool 项目上下文（2026-07-20）

将以下内容粘贴到新对话开头，AI 即可接续工作。

---

## 项目基本信息

- **项目路径**：`E:\stock-tool`
- **GitHub**：`github.com:cementbarrier/stock-tool.git`
- **入口文件**：`gui/build/gui.py`（Tkinter GUI）、`scripts/run_pipeline.py`（定期跟踪流水线）
- **桌面快捷方式**：`stock_gui.lnk` → `E:\stock-tool\dist\gui.exe`

## 部署流程（极其重要）

每次修改 `gui/build/gui.py` 或 `backend/`、`scripts/` 下任何 Python 源码后，必须：

```
1. 杀掉所有 gui.exe 进程: Get-Process -Name gui | Stop-Process -Force
2. cmd /c "cd /d E:\stock-tool && pyinstaller gui.spec --distpath E:\stock-tool\dist --workpath E:\stock-tool\build\temp --clean --noconfirm"
3. git add -A && git commit -m "xxx" && git push
```

**注意**：gui.spec 在 `E:\stock-tool\gui.spec`（项目根目录），不在 gui 子目录下。

## 全部已修复问题（共 16 项）

### 托盘与窗口
| # | 问题 | 根因 | 修复 |
|---|------|------|------|
| 1 | 托盘图标左键点击后消失 | `_hide_to_tray` 图标为空时不重建 | 图标为空时调用 `_init_tray_icon` 重建 |
| 2 | 关闭窗口后无托盘图标 | 同上 | 同上 |
| 3 | 托盘图标不应随窗口显示/隐藏而销毁 | `_restore_window` 调用了 `_tray_icon.stop()` | 移除 stop 调用，图标永不销毁 |
| 4 | 系统 12 个 gui.exe 进程堆积 | 托盘图标消失后用户误以为已关，反复双击 | 启动时文件锁 `stock_tool_instance.lock` 单实例检测 |

### 配置持久化
| # | 问题 | 根因 | 修复 |
|---|------|------|------|
| 5 | 提供商/API Key/模型名更新软件后丢失 | `_config_save_all` 中 `if selected:`/`if api_key:`/`if model:` 的 falsy 守卫跳过空值写入 | 移除守卫，改为全量写入 |
| 6 | 切换提供商后模型被清空 | `_config_provider_changed` 清空了模型 | 改为设默认模型 |
| 7 | 邮件三字段保存后重启仍为空 | 逐字段 `set_setting` 每次独立读写 JSON，与 Checkbutton 自动保存回调交错 | 改为一次 `load_settings` → 改全部 → 一次 `save_settings` 原子写入 |
| 8 | `load_settings` 把空字符串 `""` 判为缺失回退默认值 | `data.get(key) if data.get(key) else DEFAULTS[key]` 把空字符串判为 falsy | 改为 `val if val is not None else DEFAULTS[key]` |
| 9 | `settings.json` 带 UTF-8 BOM 头导致 JSON 加载失败 | `json.load` 用 `utf-8` 编码碰到 `\ufeff` 抛 `JSONDecodeError`，被 `except Exception: data = {}` 静默吞掉 | 读取用 `utf-8-sig`，写入用 `utf-8`（自动去 BOM） |

### GUI 显示
| # | 问题 | 根因 | 修复 |
|---|------|------|------|
| 10 | 邮箱字段保存后重启界面仍为空 | `_config_refresh_all` 只刷了 provider/api_key/model，漏了邮箱 Entry | 补充 `email_sender_entry` / `email_auth_entry` 刷新逻辑 |
| 11 | 初始化时模型下拉选项未更新 | `_config_refresh_all` 未在初始化时根据 provider 更新模型选项 | 初始化先更新模型下拉列表 |
| 12 | 测试发送按钮点击无任何反应 | `datetime.now()` 但 datetime 被导入为别名 `_dt`，`NameError` 被 Tkinter 静默吞掉 | 改为 `_dt.datetime.now()` |

### 构建与部署
| # | 问题 | 根因 | 修复 |
|---|------|------|------|
| 13 | PyInstaller BUILD SUCCESS 但 EXE 不含最新代码 | git CRLF 转换在构建后更新了源文件 mtime，但 EXE 已提前生成 | 清理 build 缓存 + `--clean` 重建 |
| 14 | PyInstaller PermissionError 无法覆盖 EXE | 目标 gui.exe 正在运行（多实例） | 构建前先 `Stop-Process -Force` |
| 15 | PyInstaller "gui.spec not found" | 错误地在 `gui/` 子目录下执行 | spec 文件在项目根目录 `E:\stock-tool\gui.spec` |
| 16 | config 目录被打包进 EXE | `gui.spec` 中 `datas=[('config', 'config'), ...]` | 保留该配置（EXE 需读取 config），但注意 EXE 读写路径是 `Path(sys.executable).parent.parent / "config"` |

## 已添加功能

**增量解析（定期跟踪）**：
- 维护 `data/parsed_records.json`，24h 内已解析 BV 号跳过转写
- 跳过视频的摘要仍合并入当天报告
- 报告标题自动带时段名称（早盘预览/早盘中/午盘预览/午盘中/今日复盘/明日策略）
- 新增 `backend/parsed_records.py`，修改 step1/2/3/5

## 关键配置路径

- 配置读写：`backend/config_manager.py`（`get_setting` / `set_setting`）
- 配置文件：`config/settings.json`
- 邮件通知：`backend/notifier.py`（QQ邮箱 SMTP，端口 465）
- 已解析记录：`data/parsed_records.json`
- 单实例锁：`%TEMP%\stock_tool_instance.lock`

## 流水线步骤

`scripts/run_pipeline.py` → step1 拉取 → step2 下载音频 → step3 转写 → step4 提取个股 → step5 分析报告
