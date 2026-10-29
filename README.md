<img src="frontend/public/brand/labourlawyer-mark.svg" width="64" height="64" alt="LabourLawyer 标志" />

# LabourLawyer

**选地区，填信息，生成劳动仲裁文书。**

面向普通劳动者的文书与办事助手。填写仲裁申请书、整理证据清单，再查看当地官方材料要求和提交方式。无需先创建案件或学习管理系统。

![首页：统一省份卡片与地区入口](docs/images/home.png)

> 本平台是劳动仲裁辅助工具，**不是官方政务服务网站**。文书不保证被受理；管辖、材料和受理条件以当地仲裁机构的最新判断为准。

## 软件下载（预览版）

[下载 Android 和 Windows 客户端：v1.1.0-preview.2](https://github.com/DerpZhenjun/LabourLawyer/releases/tag/v1.1.0-preview.2)

Android APK为USB联调包；Windows提供安装版和便携版。安装包包含当前完整客户端界面，**后端和官方模板库仍需按本文启动**，AI连接Ubuntu Qwen3.8，不在Windows运行模型。它们不能单独离线生成文书，也不表示全国区县已经接入完成。下载后可用同页`SHA256SUMS.txt`核对文件；详细步骤和实际测试范围见[版本说明](docs/releases/v1.1.0-preview.2.md)。

## 从填写到提交

1. 选择省、市、区县或功能区。办理地区须结合工作地、用人单位所在地等确认，不能只按户籍选择。
2. 选择申请书或证据清单。表单提供明确标注的虚构示例，正式使用前替换为自己的信息。
3. 证据从一项开始，按需添加。生成前可确认或取消，确认后下载 Word 文书。
4. 查看当地材料份数、窗口地址和办理方式。核实的官方入口提供跳转；登录或验证码由用户在官网自行完成。

![文书填写：通俗字段、虚构示例和来源提示](docs/images/document-form.png)

支持未填完整时生成参考文书，提交前仍需补齐材料。官方空白模板、官方样例和平台辅助文书分别标注，不把样例冒充空白表格。

## 每个地区，使用自己的来源

系统按具体地区匹配事项、办理机关、材料和附件，保留官方链接、采集时间、核验状态及文件 SHA-256。切换地区重新查询；没有当地来源时显示待核验，不继承相邻地区的数据。

![当地办理指南：窗口提示、材料与官方来源](docs/images/local-guide.png)

**公开发行数据更新于 2026-10-28。全国区县尚未完成。**

| 范围 | 当前实际状态 |
|---|---|
| 省级入口 | 中国大陆 31 个省级地区；入口存在不代表指南已核验 |
| 地区目录 | 3,599 条区县或功能区来源记录，涉及 3,586 个精确地区名称组合；不是全国功能区完整普查 |
| 已发布当地指南 | 181 地：四川 179、江苏 2 |
| 已发布当地填写生成 | 166 地：四川 164；江苏锡山区、建湖县各自的官方空白文书 |
| 仅指南、未开放当地生成 | 15 地 |
| 未发布候选 | 24 地，均不计入上线覆盖 |
| 历史省级文书 | 保留独立入口，须另核对适用范围，不计入区县完成数 |

近期新增滨海县、响水县、杭州市上城区、滨江区和合肥市庐阳区的独立资料。滨海、响水及上城已完成离线填写与逐页版式检查，仍待网页验收。滨江材料栏与流程冲突，庐阳的时限说明存在差异，均保留待核验。临平搜索落到市本级的结果未作为该区指南。新候选未发布，没有任何省份被标记为“全区县完成”。

2026-10-29继续完成东台市、射阳县各自模板的严格生成入口、公开来源摘要及6页版式检查，并通过共享接口的独立数据库生成测试；余杭区完成自身原件和填写件13页检查，修复案号标签与续页表头。三地仍保留候选状态，未把离线或内存接口测试当成已上线网页验收。记录见[本批地区进度](reports/regional-release-20261029/TEST-REPORT.md)。

运行后在 `/admin/regions` 查看实时矩阵。仓库中可核对 [逐省实际进度](docs/regions-status.md)、[公开数据版本](data/public-regions/manifest.json)、[候选登记](config/regional_candidates.json) 与 [地区接入说明](docs/regional-release.md)。

## AI 法律顾问与法律数字人

文字顾问与阿律数字人共用后端的流式问答，通过 SSH 连接 **Ubuntu Ollama / qwen3.8:27b**。Windows 只做连接转发，不启动本机模型；AI中断时仍可填写、生成文书。数字人以右下角客服小窗出现，只显示上半身，可收起后继续填写文书；展开保留对话，并支持可选的浏览器语音朗读。

**2026-10-29 已完成真实网页问答验收**：文字顾问和数字人均通过现有项目后端连接 Ubuntu 的 `qwen3.8:27b`，完整返回测试回答。页面显示连接状态，支持重新检查；远程连接中断不会影响文书填写和生成。已验证 375 / 768 / 1440px 布局。连接、升级后重启和使用说明见 [Ubuntu 远程 AI](docs/remote-ai.md)。

![客服式数字人小窗：上半身形象、Ubuntu Qwen3.8 真实测试回答](docs/images/digital-human.png)

![AI 法律顾问通过 Ubuntu Qwen3.8 返回真实测试回答](docs/images/ai-advisor.png)

## OpenClaw：公开资料补采与问题追踪

在后台的 **OpenClaw 浏览器补采** 中选择省份，查看或续跑公开指南任务。系统分别记录网页已打开、指南已找到、模板已下载、已验证可填写，保留来源与截图，避免把“下载成功”当成“可以生成”。

![OpenClaw 实际浏览器补采面板](docs/images/openclaw-collection.png)

地区核验页展示精确地区、来源版本、采集差异和问题记录。搜索失败、附件缺失、登录边界等问题持久化到 outbox；只有实际收到完整事件编号回执才标记为已接收。

![地区来源与 OpenClaw 问题投递状态](docs/images/openclaw-regions.png)

截图中的 `PENDING_OPENCLAW` 表示仍待接收确认；历史任务记录不代表本轮执行了模型视觉复核，也不代表全国完成。截图采集期间没有启动采集或同步。操作入口、CLI与安全边界见 [OpenClaw 功能说明](docs/openclaw.md)。

## 网页、Android 与小程序

| 客户端 | 使用方式与边界 |
|---|---|
| 网页 | Vue 3 + Vite；精确地区选择、当地填写、指南与管理页面 |
| Android | Capacitor 复用网页前端；需构建和安装，可通过 USB 调试安装 |
| 微信小程序 | 原生小程序工程；已有省级文书填写、下载和指南，区县能力与网页尚未完全对齐 |
| Windows 桌面 | 可选 Electron 工程；开发模式不等于已发布安装包 |

<img src="docs/images/mobile-form.png" alt="手机窄屏文书填写，字段单列排列" width="320" />

截图来自实际网页，信息均为虚构示例。窄屏网页截图不作为 Android 或微信真机验收证明。

## 快速启动

### Windows

准备 Git、Python 3.11 和 Node.js 22.12+（或兼容 Vite 7 的版本）。Android 构建另需 JDK、Android SDK。

```powershell
git clone https://github.com/DerpZhenjun/LabourLawyer.git
cd LabourLawyer
.\start.bat web
```

也可双击 `start.bat` 打开统一菜单。首次启动会安装缺少的依赖，前后端由同一入口管理，日志位于 `.runtime/`。关闭浏览器不会自动停止服务。

- 网页：<http://127.0.0.1:5173/>
- 地区管理：<http://127.0.0.1:5173/admin/regions>
- API 文档：<http://127.0.0.1:8000/docs>

```powershell
.\start.bat stop
.\start.bat android-open
.\scripts\install-mobile.ps1
.\start.bat mini
```

客户端前置条件见 [三端使用说明](docs/client-guide.md)。小程序使用微信开发者工具，Android 使用 Android Studio / Capacitor。HBuilderX 可以编辑前端，但不是这两个客户端的运行、打包工具。

### 手动启动

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r backend/requirements-api.txt
python scripts/bootstrap-public-data.py
python -m uvicorn app:app --app-dir backend --host 127.0.0.1 --port 8000
```

另开终端启动网页：

```bash
cd frontend
npm ci
npm run dev -- --host 127.0.0.1
```

首次启动仅向空的公共指南、地区目录库导入经 SHA-256 校验的发行快照；已有数据不覆盖，不操作案件库。附件缺失或适配身份不匹配时关闭对应生成能力。源码不包含个人案件数据库、登录会话或模型文件。

**生成文书不依赖大模型。** AI问答与数字人为可选模块，连接按 [远程 AI 配置](docs/remote-ai.md) 设置，不需要为了生成 Word 启动或下载模型。

## 开发与验证

```bash
python -m unittest discover -s backend/tests
node scripts/test-document-clients.cjs
node scripts/test-regional-blank-fields.mjs
npm --prefix frontend run build
```

测试使用临时数据库和虚构信息，不提交真实申请。部分封存采集含官方登录跳转上下文，只留在采集机器；公开克隆会明确跳过对应本地集成测试，不伪造替代证据。构建成功不能代替文书版式和浏览器验收。

`scripts/verify-*.mjs` 使用 Chrome DevTools MCP；设置 `CHROME_DEVTOOLS_MCP_PATH` 为本机安装入口后执行。README 图片由 `scripts/capture-readme.mjs` 实拍。

## 目录

```text
frontend/            群众网页、地区选择、文书与管理界面
backend/             FastAPI、文书适配、精确地区库与来源核验
templates/_docx/     按省份或具体地区保存的官方原始附件
config/              表单、官方来源目录和候选登记
data/public-regions/ 不含个人资料的公共发行快照
llm_service/         可选 AI 问答
ChatVRM/             可选数字人
mobile/              Android / Capacitor
miniprogram/         微信原生小程序
desktop/             Electron
scripts/             启动、采集、维护与验收
docs/                使用说明与实际页面截图
```

## 新增区县

访问该地区自己的官方事项指南，核对机关、事项与适用范围，展开材料和办理方式，逐一下载公开附件并保存来源和 SHA-256。缺少模板保持缺失，不用其他地区文件替代。

适配须验证地区、事项、附件编号、路径和摘要，在独立测试库检查生成结果，逐页检查文书，并验收桌面和手机宽度的真实网页。通过后才增量发布和导出公共快照。

OpenClaw 记录公开采集问题；不可用时持久化为 `PENDING_OPENCLAW`，有真实回执后才标记同步。不得上传身份信息、真实文书或凭据。详情见 [地区接入与发行说明](docs/regional-release.md)。
