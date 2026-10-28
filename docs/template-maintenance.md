# 模板重拉、文书验证、OpenClaw 和报告

## 推荐维护顺序

1. **`check-updates` 检查更新**：只请求已登记的官方源，不替换 `templates/_docx`。四省接口适配器加全国来源目录都跑，目录检查结果保留在本次启动日志和 `templates/_acquisition/catalog-checks/时间.json`；`--check-only` 不覆盖最近正式下载报告。查看各文件 `outputs.status`，区分 `unchanged`、新建/更新候选和检查时跳过转换的文件。
2. **`refresh` 实际重拉**：重新下载登记附件。四省适配器为浙江、广东、江苏、辽宁；全国来源目录补充其他地区。下载内容验证后才落库，旧版进 `_archive`，失败保留错误，不以自制文书补齐。
3. **`official-render` 渲染官方首页**：隐藏 Word/Excel 导出、Poppler 转截图；需要已安装 Office、渲染 Python 的 Pillow/python-docx、Poppler。仅查看官方各文件首页，不代表所有页完整检查。
4. **`official-vision` 复核官方首页**：OpenClaw 每张图一份官方文件，模型 `ollama/qwen3.8:27b`；先执行 `official-render`，缓存校验值不符会要求重新渲染。截图和模型原始结果保留。
5. 核对变化：新增/改名字段、表格、空白位置、页数、办事说明、模板适用地区。**若结构变化，必须修改字段映射和前端后再继续；下载脚本不会自动改代码。**
6. **`examples` 生成案例并渲染**：读取 `frontend` 实际默认值；生成所有当前已启用文书，逐页导出与官方表单对比图，不修改原始官方模板。
7. **`openclaw-smoke` 测图像连接**，再 **`example-vision` 全国生成文书复核**；打开对比图和模型输出人工核对。请求后没有输出不是审核通过；模型指出的正常换行也可能是假阳性。
8. **`web-flow` 测网页下载**：隐藏 Chrome 中实际走默认表单填写/生成流程，保留下载 Word 和截图。它使用独立 4187 预览，以及实际 API 路由的测试客户端，不需要占用你的前台。
9. **`source-report` 导出来源 Word 报告**。更新模板后重启网页后端，让后端重新读取模板目录。

自动拉取依赖于已接入的省级接口和登记附件链接。某些地区只有 PDF、指南或受登录限制，重复运行不会自动发明 Word。官方 URL 失效、需要验证码或资料未公开时，日志必须保留这一结果，并人工继续核对其他主管机关官方页面。

## 检查哪些内容

- 姓名、出生日期、证件号、联系电话、地址、单位代码、法定代表人等是否写进各自的空白位置。
- 是否保留模板文字、字体、字号、下划线、边框、页眉页脚；长内容是否正常换行而非整段替换原版样式。
- 仲裁请求和事实是否从模板规定位置开始；不要留下多余未使用的写作横线。
- 应手签的位置必须留白，普通身份姓名字段可以填；日期可以填。
- 证据清单序号、页数、份数、来源、证明目的与表头是否对应；不能把单位姓名误当成签名。
- 官网来源和适用范围与网页说明是否一致。

最终质量结论需要人工逐页检查；图像模型不能可靠证明字体完全一致或法律效力。

## OpenClaw 如何使用

文书图像检查和门户报告统一使用 Ubuntu Ollama `http://10.66.66.1:11434` 的 `qwen3.8:27b`，不回退到 Windows 本机。OpenClaw 在 Windows 上执行，独立目录保存在 D 盘。可通过 `OPENCLAW_EXECUTABLE` 指定 CLI 路径，或使用启动器的路径配置；启动器检查对应服务器和模型，不自动下载其他模型。

- **`health` 环境检查**：确认服务/模型存在，不发送图像。
- **`openclaw-smoke` 实际连接测试**：发送现有一张文书对比截图，最多等待 240 秒；输出 `.runtime/launch-center/openclaw-smoke/批次/response.json`。
- **`official-vision` 官方首页**：每张官方文书首页模型复核，输出 `templates/_acquisition/document-visual-validation/sheets/*.openclaw.json`。
- **`example-vision` 生成文书**：逐页模板/生成文书对比，输出各省目录 `comparison-*.openclaw.json` 和 `manifest.json` 中的 `vision`。
- **`portal-vision` 门户识别**：OpenClaw 使用 `qwen3.8:27b` 逐项复核三个检索词的结果截图及材料页面，保存实际截图、访问记录和独立 AI 验证 Word。

OpenClaw 独立状态和工作目录留在本次检查目录；Chrome 无头、沙盒启用，目录隔离，不是容器级隔离。27b 受显存、加载和图片尺寸影响，一批截图可能需数分钟，全量可能需数小时。门户复核每批最多尝试两次，失败记录后继续其他地区；生成文书复核仍保留原来的连续失败停止机制。门户调用必须核对实际返回的模型标识和逐张输出，不把超时或缺项计为完成。

门户复核每次发送一张截图，单次最长等待 600 秒，网络探测最长 30 秒；超时保留失败记录。Ubuntu Ollama 自行分配 GPU/CPU，不再强制 Windows 的 GPU 层数。已成功且截图校验值未变化的前序复核不会重跑，AI 报告逐项注明 Ubuntu 地址；历史响应未记载地址时标为来源未记载。

**重新运行 `examples` 会重建生成文书清单，随后需要重新运行 `example-vision`。**只要官方模板变化，旧对比截图就应作废并重新生成。单省调用用 `start.bat example-vision -Province jiangsu`，地区 slug 取 `backend/province_documents.py` 的 `SLUGS`。

## 已获取官方模板的来源报告（REPORTS → SOURCE REPORT）

报告位置：`templates/_reports/template-ledgers/批次/官方文书模板获取报告.docx`。同目录 `sources.json` 保留无显示换行处理的原网址、文件路径、文件大小、SHA-256、目录记录和最近正式下载记录；上层 `latest.json` 指向最新报告。

这是**本地库存导出**，不重新访问网站，不自动判定历史目录状态仍有效。报告包括 31 地区；有文件与没有文件都如实列出。目录来源 URL 如北京在：

`config/province_official_template_catalog.json` 中 `province = Beijing` 的 `source_url`；对应来源文件在 `templates/_acquisition/sources/BeiJingShi/source.json`。

获取 URL 与当前可生成类型不是同一回事。有些 DOCX 尚未配置生成；PDF 原稿也不能仅因存在就视作可填 Word。

## 政务服务门户观察报告（REPORTS，或网页）

**`portal-report` 会真正重新访问网站、搜索劳动仲裁服务并截屏**。范围默认大陆 31 地区；`portal-vision` 增加 OpenClaw 辅助识别。若只检查一个地区，可用 `start.bat portal-report -Province beijing`。

每次独立批次在 `templates/_reports/portal-audits/批次/`，主要文件：

- `status.json`：采集状态与进度，Word 导出状态和校验值。
- `results.json`：访问 URL、时间、结果分类、步骤、截图及其他证据路径。
- 原始 HTML/文本、PNG 截图等：按实际采集保存，不能用模型生成图替代。
- `劳动仲裁政务服务门户观察报告.docx`：逐省事实和截图、限制、补充官方来源。
- `劳动仲裁政务服务门户AI验证报告.docx`：启用 `--vision` 后生成，列出每张目标截图的实际模型判读、缺项和与页面记录冲突的提示。
- `model-info.json`：Ubuntu 模型的名称、服务器、摘要及量化信息；`model-info-windows.json` 保留前序模型信息。各地区 `openclaw-*.json` 保留实际响应、服务器和输入截图校验值。

网页入口：`/admin/documents` 的政务服务门户观察报告区域，选择地区/视觉复核选项、开始采集、查看进度、完成后下载。若未成功生成报告，查看批次错误，不能将“任务已提交”视作完成。

报告为改善服务或反馈提供材料，应分别表述“搜索范围内未定位入口”“访问失败”“需登录/交互”等事实；不能由一次搜索直接断言主管机关未提供服务。历史批次可保留；最新一次的截图不能覆盖旧批次。

已有证据无需重采时可重新导出 Word：

```powershell
.\.venv\Scripts\python.exe scripts\audit_official_portals.py --rebuild 20260929-142326-115bd1fc
```

批次编号换成实际目录名。重导出不重新访问官网，也不自动完成新模型复核。

续跑已有批次并补齐 AI 验证：

```powershell
.\.venv\Scripts\python.exe scripts\audit_official_portals.py --resume 20260929-142326-115bd1fc --vision --skip-refine
```

`--skip-refine` 只从已保存的截图补齐 AI 复核，不重访已有公开指南；已完成且 SHA-256 未变化的截图结果会复用。若需要重新访问个别地区，去掉 `--skip-refine` 并加 `--retry-regions shanxi hebei`；这些地区的旧证据先移入同批次 `history/时间/`，再重新采集。不要同时运行同一批次。

## 中断、失败与进度

### OpenClaw 原生浏览器补采（2026-10-07）

`start.bat guides-refresh` 新建批次时，先复用来源并尝试普通采集、正常浏览器点击和滚动；这些方式未取得本次指南的省份，再进入 OpenClaw 浏览器补采。续跑原批次默认不重做浏览器补采；需要补做时给 `scripts/refresh-province-experiences.py --resume <原批次路径>` 加 `--with-browser-agent`。

也可单独运行 `start.bat openclaw-acquire`，或 `start.bat openclaw-acquire -Province shanxi`。网页工作台 `/admin/documents` 增加“OpenClaw 浏览器补采”，支持选省、后台启动、查看截图、查看进度和继续未完成任务。手机共用 Vue 工作台；小程序的普通省份页通过既有接口接收已发布指南，不提供维护任务按钮。

这里实际调用 OpenClaw 的 `browser` 命令启动专用无头 Chrome，获取当前控件引用和截图，由 Ubuntu Qwen 选择下一步，再用 OpenClaw 执行点击、输入搜索词并回车、翻页、打开指南和处理地区提示。模型不能执行自定义脚本或直接修改文件。每步重新观察，过期引用或操作失败会反馈给模型；独立程序再提取材料和流程、下载公开附件，并核验文件 SHA-256。

成功获取的新页面进入既有 AI 复核和三端指南更新流程。下载到文件不会自动开放文书生成；还需要字段适配和生成后的版式验证。

- 任务证据：`templates/_reports/openclaw-tasks/<编号>/`。`status.json` 为批次进度，`results.json` 为省份结果；省份目录内 `task.json` 保存执行轨迹，`step-XX-snapshot.json`/`.png` 保存页面，`step-XX-model.json` 保存 Qwen 原始决策，`verified-guide.json` 保存独立核验的指南。
- 四项状态分别表示网页打开、指南取得、模板文件下载、已验证可填写。网页能打开并不表示后三项完成；最后一项不会仅凭模型判断变成成功。
- 附件先检查实际内容：Word 检查表格字段；PDF 通过 OpenClaw 和 Ubuntu Qwen 识别。整份办事指南导出放入 `supporting_documents`，不算证据清单或申请书模板。`download-reviews/` 保留文件哈希、实际文件画面和原始判断；无法确认时进入 `review_incomplete`，保留数据并允许续跑。复核失败不会更新三端，成功的同哈希复核会复用。
- 续跑：`.\.venv\Scripts\python.exe scripts/openclaw-acquire-guides.py --resume templates/_reports/openclaw-tasks/<编号>`。跳过已取得的省份，失败尝试保存在同批次 `*-previous-*` 目录。新报告批次派生自原完整批次，不删原批次。
- 全程使用 Ubuntu `http://10.66.66.1:11434` / `qwen3.8:27b`。网络探测最长 25 秒；单次模型决策最长 180 秒；Gateway 冷启动最长 45 秒，浏览器命令最长 40 秒；默认每省 12 步、15 分钟。模型不可用时保存明确错误，不回退到本机模型。
- Gateway 与 Chrome 的 `127.0.0.1` 地址仅用于本机专用浏览器控制，不是 Ollama 地址。沙盒启用，浏览器资料和临时目录保存在项目 D 盘。证书错误、验证码和登录阻碍会记录，不进入在线申请提交。

### OpenClaw 检查最终 Word 报告

生成报告后，先用 `scripts/render_portal_reports.py <批次目录>` 导出 PDF 和逐页图片，再用安装了 pypdf 的制品 Python 运行：

```powershell
& "$env:USERPROFILE/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe" scripts/review-province-reports.py templates/_reports/province-experiences/<批次编号> --timeout 300
```

程序通过 OpenClaw 把实际渲染页交给 Ubuntu Qwen，逐页检查标题字体、截图裁切、溢出和排版。结果在该批次 `openclaw-report-check/check.json`；每组目录保存输入校验值、原始 OpenClaw 返回和检查结果。网页原始截图检查与最终报告排版检查分别保留。模型意见由维护者核实后再修复，不直接改文书或指南。

原批次续跑会复用校验值一致的已完成页，不重新采集网站；渲染不完整、模型超时、漏页或返回结构错误均报告失败。单次请求最长 300 秒，可显式调整但不能超过 600 秒；服务固定为 Ubuntu `10.66.66.1:11434`，不回退本机。修改 Word 后应重新渲染，再检查变更后的报告。

启动中心的大任务自动显示终端实时面板：省份计数、浏览器操作、Ubuntu 模型等待及超时、成功/失败/缓存和输出目录。`start.bat monitor` 可在另一终端只读查看任务；`start.bat summary` 查看已发布结果；`start.bat report-check` 检查已有最终报告。详情见 [启动说明的实时面板](launchers.md#命令行实时面板)。没有新结果时仍可读 `status.json`/`manifest.json` 或原始 OpenClaw 日志。不要同时启动两次相同的模板生成或复核，它们使用相同输出位置，可能互相覆盖。

失败时脚本返回非零退出码，窗口保留原因。重拉两个来源入口相互独立，一个失败仍执行另一个，并保留失败结论。全国最终报告保留所有地区的失败/缺失记录，不伪造成功。

在窗口按 Ctrl+C 可以中断前台执行；检查残留的本次隐藏浏览器/Office 进程，避免强行终止你自己正在使用的程序。再次运行前核对已保存的批次与清单。完整模板与维护实现另见 `docs/template-acquisition.md` 和 `docs/document-template-audit.md`。
