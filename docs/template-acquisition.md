# 官方文书模板自动获取

该流程从各省政务服务网获取空白官方模板，完成校验后写入 `templates/_docx`，同时生成来源和复核报告。若官方模板发生变化，原生产版本先备份到 `templates/_archive`。

## 采集范围

- 浙江：调用办事指南的公开材料接口，获取《劳动人事争议仲裁申请书》和《证据清单》。
- 广东：调用办事指南的公开材料接口，获取仲裁申请书和证据清单。
- 江苏：解析江苏政务服务办事指南公开的空白表格链接，获取劳动人事争议仲裁申请书和证据清单。
- 辽宁：获取省级指南提供的旧版 `.doc` 仲裁申请书，保留官方原件，并通过隐藏的 Microsoft Word 进程转换为可填充的 `.docx`。省级指南当前未提供证据清单空表。

新增省份时，在 `config/template_sources.json` 添加来源，并在 `backend/template_acquisition/adapters` 编写该省接口适配器。采集器优先解析公开接口；只有接口不足时才使用无头浏览器和视觉识别。

`config/province_official_template_catalog.json` 另外覆盖中国大陆31个省级行政区。它记录每个地区的官方机构、适用范围、来源地址、公开文件和无法取得模板的原因。批量采集坚持以下规则：

- 只下载目录中登记的官方政府、政务服务或人社部门域名。
- 官方只公开办事指南时保存指南，不把指南冒充空白模板。
- 官方没有公开文件、下载端点返回空文件或页面暂时失效时，只写审计状态，不借用其他省份模板。
- 旧版 `.doc` 原件保存在 `templates/_original`，通过隐藏的 Microsoft Word 转换为可编辑 `.docx`。
- PDF 和 XLSX 原件保存在 `templates/_original`，不进行可能破坏排版的格式转换。

## 运行

```powershell
.\.venv\Scripts\python.exe scripts\acquire_templates.py
.\.venv\Scripts\python.exe scripts\acquire_templates.py --province Zhejiang
.\.venv\Scripts\python.exe scripts\acquire_province_catalog.py
.\.venv\Scripts\python.exe scripts\build_template_acquisition_ledger.py
```

默认步骤：

1. 调用官方办事指南接口，解析空白表格下载地址。
2. 默认只允许 HTTPS；少量仍使用 HTTP 的官方旧站必须在目录中逐项显式允许。所有来源都检查官方域名和重定向后的最终域名。
3. 限制下载大小，检查 DOCX ZIP 结构、解压体积、压缩率和宏文件。
4. 计算文件 SHA-256 和文书结构指纹。
5. 在 `templates/_acquisition/runs` 保存不可变候选文件、接口快照、页面截图和报告。
6. 用 OpenClaw 调用Ubuntu Ollama 的 `qwen3.8:27b` 对截图做候选视觉复核。
7. 报告标记 `new`、`unchanged` 或 `changed`；校验通过后原子写入生产模板目录。

`--no-browser` 可跳过无头页面截图；`--no-vision` 可跳过 OpenClaw/Qwen 复核；`--check-only` 只检查，不写入生产模板。

## 隔离方式

采集浏览器使用系统 Chrome 的无头模式，不显示窗口。浏览器资料、临时目录以及 OpenClaw 的状态、配置和工作目录都位于 `templates/_acquisition`，不读取个人浏览器配置。OpenClaw 配置启用 Chrome 自身沙盒并绑定本机回环地址。

当前机器没有 Docker 或 Podman，因此这里没有容器级隔离。若以后安装容器运行时，可再启用 OpenClaw 的容器沙盒；采集器本身的官方域名白名单、文件大小限制、DOCX 安全检查和候选区隔离仍然保留。

## 结果位置

每次运行的 `report.json` 包含来源链接、下载链接、哈希、结构指纹、校验数据、视觉复核文件和发布状态。SQLite 索引位于 `templates/_acquisition/registry.sqlite3`。

每份文件都先经过安全与结构校验，再写入 `templates/_docx` 中对应省份目录。

- 31省批量下载报告：`templates/province-template-acquisition-report.json`
- 31省人类可读台账：`templates/官方文书采集台账.md`
- 每省来源审计：`templates/_acquisition/sources/<省份拼音>/source.json`
- 官方原件：`templates/_original/<省份拼音>`
- 可编辑模板：`templates/_docx/<省份拼音>`

## 实际文书页面核验

`scripts/validate_acquired_templates.py` 使用隐藏的 Word/Excel 将已取得文件导出为 PDF，用项目现有 Poppler 渲染首页，再由 OpenClaw 调用 `ollama/qwen3.8:27b` 检查明显裁切、重叠或损坏。模型调用使用 `--thinking off`，只作版面辅助复核，不修改或批准模板。

当前 Codex 文档运行时自带 Pillow，运行命令为：

```powershell
& 'C:\Users\DerpZhenjun\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' scripts\validate_acquired_templates.py
```

核验结果位于 `templates/_acquisition/document-visual-validation/report.json`。高清联系表、缩略模型输入和每批 OpenClaw 原始输出保存在同一目录，便于人工复查。
