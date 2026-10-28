# 项目启动中心

项目目录：`D:\workspace\DerpZhenjun\Partlawyer-LAA`。

**日常使用：双击根目录的 `start.bat`，进入分类菜单。** 首页列常用入口和六个分类：1 WEB、2 DESKTOP、3 STOP、4 CLIENTS、5 TEMPLATES、6 QUALITY、7 REPORTS、8 MODELS、9 TOOLS。也可以在项目根目录运行 `start.bat web` 等命令直接执行。

项目根目录只保留这一个 BAT。实现集中在 `scripts/launcher/`，操作说明集中在 `docs/`。BAT 是 Windows 双击入口，实际功能在 PowerShell 和 Python 中，不需要为每个动作复制一个 BAT。

所有入口保留执行窗口和错误信息；本次日志在 `.runtime\launch-center\logs`。退出菜单不会停止已启动的网页，停止服务请选 HOME → STOP。采集和图像检查使用隐藏浏览器，不会打开浏览器占用前台。网页、桌面端、目录窗口仅在你主动选择对应入口时打开。

## 第一次使用

1. 先选 **TOOLS → HEALTH**，检查已有 Python、Node、uv、adb、OpenClaw 和 Ollama。
2. 选首页 **1 WEB**。脚本会补齐缺少的网页依赖；缓存、临时文件放 D 盘。页面地址为 `http://127.0.0.1:5173`，API 为 `http://127.0.0.1:8000/docs`。
3. 首页选省份，再选仲裁申请书或证据清单。灰色示例是实际默认内容，直接生成就会得到虚构案例；正式提交前请替换为真实信息，打印后手签。
4. 手机安装当前 APK 后，选 **CLIENTS → ANDROID** 恢复 USB 连接。旧安装不会自动获得最新构建；本轮没有已授权在线设备，未安装新包。小程序选 **CLIENTS → MINI APP**，按提示导入微信开发者工具并编译。

工具清单和设备限制见 [三端使用说明](client-guide.md)。

## 当前实际范围

- 地区来源目录覆盖中国大陆 31 个省级行政区；不含港澳台。
- 当前已启用 21 个地区的申请书、13 个地区的证据清单，共 34 种生成入口。以页面和环境检查的实时结果为准。其余地区保持不可生成，不用其他地区模板替代。
- 有些官方文件由市、区、县发布；进入页面先核对发布机构和适用范围。所在省有入口不代表模板适用全省。
- 网页与 Android 使用同一套前端表单。微信原生小程序已有省级 Word 文书填写、下载页；精确区县能力与网页尚未完全对齐。iOS 安装包尚未提供。
- 门户报告、官方文书与生成文书的 OpenClaw 图像复核，以及网页 AI 问答，统一使用 Ubuntu Ollama **`http://10.66.66.1:11434` / `qwen3.8:27b`**，不回退到 Windows 本机。
- 已验证过江苏生成文书的实际模型连接；不能因此认为全国所有文书都完成模型复核。

## 按用途找入口

**HOME / CLIENTS：日常使用**

- 首页 1 WEB 启动网页，2 DESKTOP 启动 Windows 桌面端，3 STOP 停止本项目服务。
- 4 CLIENTS：ANDROID、MINI APP、DIGITAL HUMAN。
- 9 TOOLS：HEALTH 检查环境、RESULTS 查看结果。
- 网页、Windows 桌面端和 Android 打开入口会一并启动数字人服务。文书生成本身不依赖数字人。桌面端是 Electron 开发模式，不是发布安装包。

**TEMPLATES / QUALITY / REPORTS：官方模板维护**

- `check-updates`：只检查官方附件变化，保留输出日志和 `templates/_acquisition/catalog-checks` 的 JSON，不替换生产模板。
- `refresh`：实际重新下载并更新已登记的官方附件，旧版归档；四省接口和全国附件目录都执行。
- `official-render`：把官方 Word/PDF/Excel **首页**导出成截图。
- `official-vision`：让 OpenClaw 逐张复核首页。必须先执行 `official-render`；更改过模板后重新渲染。
- `source-report`：根据本地库存和保存的采集记录，导出带官方来源、下载链接、路径和 SHA-256 的 Word 报告。

模板更新后不会自动编写新的字段映射；需核对表单字段和填写位置，再执行 `examples`、`example-vision` 和 `web-flow`。没有公开模板的地区不会因为重新下载就自动获得生成能力。详细步骤见 [文书维护与报告](template-maintenance.md)。

**QUALITY：文书质量与网页检查**

- `examples`：使用前端的真实默认值生成全部已启用文书，导出每一页和模板对比图。
- `openclaw-smoke`：用现有一张截图实际测试 OpenClaw 图像连接；模型未安装时只报错，不下载其他模型。
- `example-vision`：让 OpenClaw 对比全部已生成页，检查错位、下划线、签署位置等。耗时可能较长，结果须人工复核。
- `web-flow`：隐藏 Chrome 中实际打开表单并下载，独立预览端口 4187；不会停止已有网页服务。

“渲染”指把 Word 等文档的页面转换成截图，方便检查布局，不会改写官方模板。OFFICIAL AI 检查空白官方文件的首页；COMPARE AI 检查实际填入默认案例后的文书各页。两类图像复核均为模型辅助结果，需要人工核对。

检查生成文书的常用顺序：EXAMPLES → AI CONNECT → COMPARE AI → WEB FLOW。要检查空白官方模板，则先 RENDER，再 OFFICIAL AI。只有连接测试成功，不能推断所有文书已经通过检查。

**REPORTS：政务服务网观察报告**

- `portal-report`：逐省分别搜索“劳动仲裁”“劳动人事争议仲裁”“劳动人事争议调解”，截图结果并进入可见候选的材料页面，生成门户观察 Word 报告。
- `portal-vision`：完成相同采集，再用 OpenClaw / `qwen3.8:27b` 复核截图，另外生成 AI 验证 Word 报告。两份报告均使用黑体标题、宋体正文。
- 网页 `/admin/documents` 中也能创建报告，启用视觉复核后可以分别下载两份 Word。

两类报告用途不同：**source-report 是已获取模板来源报告；portal-report / portal-vision 是网站访问证据报告**。搜索未找到、登录限制和访问失败都不能直接证明没有劳动仲裁服务。

**MODELS：法律模型**

- PREPARE 准备数据；TRAIN 正式训练；EVALUATE 评测；ASK 使用训练产物。
- 第一次运行会执行 `uv sync --locked`，可能下载依赖和基础模型；训练数据、缓存和产物都放 D 盘。
- 默认训练模型是 ModelFinetune 中的 Qwen3 4b，**不是 OpenClaw 使用的 27b**。训练产物不会自动部署成网页/Ollama 模型。完整实验和评测方法见 [训练目录说明](../ModelFinetune/README.md)。

## 结果目录

当前已生成的 Word 可直接打开：

- [官方文书模板获取报告](../templates/_reports/template-ledgers/20260928-160445-377292/官方文书模板获取报告.docx)：模板下载来源、官方网址、本地文件和校验信息。
- [劳动仲裁政务服务门户观察报告](../templates/_reports/portal-audits/20260929-142326-115bd1fc/劳动仲裁政务服务门户观察报告.docx)：31 个地区的三词检索、实际截图、入口和材料页面。
- [劳动仲裁政务服务门户AI验证报告](../templates/_reports/portal-audits/20260929-142326-115bd1fc/劳动仲裁政务服务门户AI验证报告.docx)：逐图 OpenClaw 判读、服务器来源和人工纠错记录。

新执行 REPORTS 中的动作会创建新的批次目录，以上链接仅对应现有批次。

- 官方可填写 Word：`templates\_docx\省份拼音\`。
- 官方原始 DOC/PDF/Excel：`templates\_original\`。
- 上一版模板：`templates\_archive\`。
- 来源台账：`templates\官方文书采集台账.md`；各省详细来源：`templates\_acquisition\sources\省份拼音\source.json`。
- 获取模板 Word 报告：`templates\_reports\template-ledgers\批次\官方文书模板获取报告.docx`，最新位置记在其上层 `latest.json`。
- 门户截图报告：`templates\_reports\portal-audits\批次\劳动仲裁政务服务门户观察报告.docx`。
- 门户 AI 报告：同批次 `劳动仲裁政务服务门户AI验证报告.docx`；`model-info.json` 保存实际模型摘要，省份目录内保存 OpenClaw 原始输出。
- 官方首页复核：`templates\_acquisition\document-visual-validation\report.json`。
- 生成文书和逐页对比：`templates\_validation\generated-documents\manifest.json` 与每省子目录。
- 网页下载验证：`templates\_validation\web-flow\`。
- 启动日志与环境检查：`.runtime\launch-center\`。选择 TOOLS → RESULTS 可打开结果目录。

## 配置与命令行

无需配置即可使用当前机器已安装的工具。`scripts/launcher/settings.example.json` 是示例；需要换渲染 Python、Poppler、OpenClaw 路径，或指定多台手机中的一台时，在同一目录复制为 `settings.local.json` 修改。不要把微信普通客户端当成开发者工具。

启动中心读取已有的 C 盘程序，但不向 C 盘下载。进程级缓存、临时文件均设置到 D 盘；Office/微信开发者工具自身的用户设置不属于项目管理的下载目录。Chrome 仍使用沙盒，无头采集是目录隔离，**不是 Docker 容器隔离**。

在项目根目录 PowerShell 执行：

```powershell
# 仅查看某个入口，不执行、不下载
.\start.bat refresh -DryRun

# 只复核江苏生成文书（先执行 examples）
.\start.bat example-vision -Province jiangsu

# 只采集北京门户观察报告
.\start.bat portal-report -Province beijing
```

编号入口是启动功能的快捷方式，不会因为双击它就保证全国模板全部可下载、页面字段自动适配或法律模型达到论文发表标准。查看每次执行日志及输出的真实完成状态。

所有动作名、分类和英文标识保存在 `scripts/launcher/actions.json`。子菜单编号从 1 开始，0 返回首页；命令行动作名保持不变。

本次已实际执行的检查和范围见 [验证记录](launcher-verification.md)。

## 命令行实时面板

通过启动中心运行指南采集、门户采集、模板重拉、文书渲染或 OpenClaw 检查时，会自动显示彩色面板。英文图标和短标签配合中文说明，无需另开网页。

- `PROGRESS`：实际已处理数/任务总数；处理完成也可能有缺口。
- `NOW / ACTION`：当前省份和真实操作，例如搜索、点击指南、保存截图、下载文件。
- `STEP`：OpenClaw 已执行步数/本次操作上限，不是任务完成百分比。
- `BROWSER WAIT`：专用 Gateway/Chrome 启动的等待时间和超时上限。
- `Qwen3.8:27B / 10.66.66.1`：实际模型等待时间、单次超时、成功、错误和复用次数。
- 省份列表：新取得、沿用历史、尚未取得、操作到上限等分别显示。
- `ACTIVITY / OUTPUT / LOG`：最近事件、结果目录、日志摘要；完整原始日志仍保留。

```powershell
# 自动显示采集和 OpenClaw 面板；只需运行原来的动作
.\start.bat openclaw-acquire
.\start.bat guides-refresh
.\start.bat portal-vision

# 在另一个终端查看正在运行的任务；只读，不重新启动采集
.\start.bat monitor

# 查看已发布全国结果、文书能力、报告 AI 检查页数和 Word 位置
.\start.bat summary

# 检查已渲染的最终 Word 页；同输入的成功检查会复用
.\start.bat report-check
```

菜单中：**TOOLS → LIVE MONITOR**；**REPORTS → RESULT BOARD**；**QUALITY → REPORT AI**。如果终端不支持颜色或需要重定向日志，加 `-Plain`，例如 `start.bat monitor -Plain`，会输出普通文字和事件。

`summary` 默认读取已发布的 `province-experiences/latest.json`，不会把时间较新的单省试验误当成全国报告。查看指定任务可用 `start.bat summary -Batch templates/_reports/openclaw-tasks/<编号>`；`monitor -Batch <批次目录>` 可跟踪指定任务。旧批次没有事件日志时，只能显示保存的状态。

每次命令行任务日志在 `.runtime/terminal/runs/<编号>/`：`session.json` 保存任务命令和进程身份，`events.jsonl` 保存结构化事件，`worker.log` 保存完整工作日志，`result.json` 保存最终统计。任务批次的 `terminal-progress.json` 指向对应事件日志，网页创建的 OpenClaw 任务也可在终端监控。

运行面板按 Ctrl+C 会停止本次启动的工作进程；监控面板按 Ctrl+C 只退出查看。结束后显示可滚动的结果摘要。全程模型仅使用 Ubuntu `10.66.66.1:11434/qwen3.8:27b`，不会启动 Windows Ollama。
