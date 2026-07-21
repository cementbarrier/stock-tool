# stock-tool 项目上下文（2026-07-21）

将以下内容粘贴到新对话开头，AI 即可接续工作。

---

## 项目基本信息

- **项目路径**：`E:\stock-tool`
- **GitHub**：`github.com:cementbarrier/stock-tool.git`
- **入口文件**：`gui/build/gui.py`（Tkinter GUI）、`scripts/run_pipeline.py`（定期跟踪流水线）
- **桌面快捷方式**：`gui.exe.lnk` → `E:\stock-tool\dist\gui.exe`

## 部署流程（极其重要）

每次修改 `gui/build/gui.py` 或 `backend/`、`scripts/` 下任何 Python 源码后，必须：

```
1. 杀进程: taskkill /F /IM gui.exe 2>$null
2. 清理缓存: 删除 build/ 和 dist/gui.exe（用 delete 工具移到回收站）
3. 构建: cd E:\stock-tool; python -m PyInstaller gui.spec
4. 验证: Get-Item 对比 EXE 和源文件时间戳，EXE 必须晚于源文件
5. git add && git commit && git push（分步执行，不要用分号链接；commit message 避免中文标点）
6. 重建桌面快捷方式: 删除旧 gui.exe.lnk，创建新快捷方式指向 E:\stock-tool\dist\gui.exe
```

**注意**：
- gui.spec 在项目根目录 `E:\stock-tool\gui.spec`
- 构建输出重定向：`Start-Process ... -RedirectStandardOutput ... -RedirectStandardError ...` 避免输出截断
- git commit 后必须 `git log --oneline -1` 验证是否真正成功，凭截断输出判断会误判
- gui/build/gui.py 被 .gitignore 忽略时需 `git add -f`
- EXE 被占用时先 rename 再构建

## 全部已修复问题（共 25 项）

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
| 13 | PyInstaller BUILD SUCCESS 但 EXE 不含最新代码 | git CRLF 转换在构建后更新了源文件 mtime，但 EXE 已提前生成 | 清理 build 缓存 + 强制重编译 |
| 14 | PyInstaller PermissionError 无法覆盖 EXE | 目标 gui.exe 正在运行（多实例） | 构建前先 `Stop-Process -Force`，如仍锁定则 rename 旧 EXE |
| 15 | PyInstaller "gui.spec not found" | 错误地在 `gui/` 子目录下执行 | spec 文件在项目根目录 `E:\stock-tool\gui.spec` |
| 16 | config 目录被打包进 EXE | `gui.spec` 中 `datas=[('config', 'config'), ...]` | 保留该配置（EXE 需读取 config），但注意 EXE 读写路径是 `Path(sys.executable).parent.parent / "config"` |

### PyInstaller 冻结环境
| # | 问题 | 根因 | 修复 |
|---|------|------|------|
| 17 | 定期跟踪按钮报 `name 'combo_year_2' is not defined` | `combo_year_2` 定义在 `create_main_window()` 内为局部变量，`button_5_clicked` 中 global 声明查找模块级变量 | `create_main_window` 中也添加 `global combo_year_2, combo_month_2, combo_day_2`，两处都声明 global 后直接访问 |
| 18 | UP 主自动补全名称和保存功能失效 | `_auto_fill_name` 中 `except:pass` 吞掉所有错误；`save_up_list` 因 openpyxl 未打包进 EXE 失败 | 添加 `_debug` 日志输出；gui.spec `hiddenimports` 补充 `openpyxl, pandas, requests` |

### 批量解析
| # | 问题 | 根因 | 修复 |
|---|------|------|------|
| 19 | 定期跟踪缺少高峰错峰队列 | `button_5_clicked` 无 `is_peak()` 检查；`valley_scheduler` 只支持 `single_summary`；`batch_parse` 无入队接口 | 高峰弹窗 askyesno，选"否"入队；`task_queue_manager` 新增 `batch_parse` 类型；`valley_scheduler._execute_one` 新增 batch_parse 执行分支 |
| 20 | 单视频/批量重复转写已存在的 txt | 无检查，每次都重新转写浪费资源 | `parse_single` 开头检查 `video_dir.glob("*.txt")` 非空则返回 `skipped=True`；`batch_parse` 每个视频循环中检查 |
| 21 | 无新增转写时仍调用 AI 生成总结，浪费 token | 跳过的存量视频被标记 `success=True` 进入 `transcribe_success`，参与 AI 调用 | `transcribe_success` 过滤条件新增 `not r.get("skipped")`；`new_count == 0` 时直接跳过 Phase 2 |
| 22 | 同一天多次批量解析只含当次视频，覆盖前次总结 | 每次运行 `_generate_batch_summary` 只拿当次新转写，覆盖写入 | 当天已有总结时扫描当日目录全部 txt 合并重新生成；日期变化后自然切换新文件 |
| 23 | target_date 设为昨天时，目录和总结仍用今天日期 | `date_prefix` 和 `today` 直接取 `datetime.now()`，不受 `target_date` 影响 | 函数开头计算 `effective_date`（`target_date` 存在时解析，否则 `datetime.now()`），所有日期引用统一使用 |

### 外观
| # | 问题 | 根因 | 修复 |
|---|------|------|------|
| 24 | 托盘图标绿色不够醒目 | 设计如此 | `_create_tray_image()` 背景改为红色 `(178,34,34)`，轮廓 `(128,0,0)` |
| 25 | EXE 无自定义图标 | gui.spec 未指定 icon | 生成 `gui/build/assets/app_icon.ico`（红色背景+白色K线），gui.spec 添加 `icon=['gui\\build\\assets\\app_icon.ico']` |

## 已添加功能

**增量解析（定期跟踪）**：
- 维护 `data/parsed_records.json`，24h 内已解析 BV 号跳过转写
- 跳过视频的摘要仍合并入当天报告
- 报告标题自动带时段名称（早盘预览/早盘中/午盘预览/午盘中/今日复盘/明日策略）
- 新增 `backend/parsed_records.py`，修改 step1/2/3/5

**错峰调度**：
- DeepSeek 峰谷定价感知，高峰自动弹窗询问是否入队
- 低谷时段自动消费队列，支持 `single_summary` 和 `batch_parse` 两种任务类型
- `backend/task_queue_manager.py`：队列管理
- `backend/time_price_judge.py`：峰谷判断
- `backend/valley_scheduler.py`：低谷消费调度

**批量解析日期管理**：
- 目录结构 `save_dir/mmdd/uid/bvid/`，总结文件 `save_dir/批次总结_YYYY-MM-DD.txt`
- 日期跟随 `target_date`，同一天多次运行汇总到同一份总结
- 存量转写跳过不参与 AI 总结，无新增时跳过 AI 调用

**界面**：
- 托盘图标：红色背景 + 白色 K 线，左键单击显示窗口，右键菜单「显示 / 退出」
- EXE 图标：红色背景 app_icon.ico
- 桌面快捷方式自动使用 EXE 内嵌图标

## 关键配置路径

- 配置读写：`backend/config_manager.py`（`get_setting` / `set_setting`）
- 配置文件：`config/settings.json`
- 邮件通知：`backend/notifier.py`（QQ邮箱 SMTP，端口 465）
- 已解析记录：`data/parsed_records.json`
- 单实例锁：`%TEMP%\stock_tool_instance.lock`
- 托盘图标：`gui/build/gui.py` 中 `_create_tray_image()` 函数内嵌生成（PIL Image）
- EXE 图标：`gui/build/assets/app_icon.ico`

## 流水线步骤

`scripts/run_pipeline.py` → step1 拉取 → step2 下载音频 → step3 转写 → step4 提取个股 → step5 分析报告
