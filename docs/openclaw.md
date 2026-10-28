# OpenClaw：公开指南补采与地区问题追踪

OpenClaw 用于补充公开政务指南采集、保存浏览器证据及辅助识别下载内容。它与地区问题投递记录是两条独立流程。打开网页、找到指南、下载附件和验证可填写分别记录；任一前置步骤成功，都不会自动证明该地区已经具备文书生成能力。

## 网页入口

在已运行的前端打开 `/admin/documents`，找到 **OpenClaw 浏览器补采**。面板可以选择省份、提交后台补采任务、查看任务状态和已有截图，并继续失败、中断或仍有缺口的任务。提交后通过任务 API 轮询进度，网页不等待整轮浏览器操作结束。

![OpenClaw 浏览器补采面板，包含成功和仍有缺口的历史任务](images/openclaw-collection.png)

图中是已有历史记录。四个标记分别是“网页已打开”“指南已找到”“模板已下载”“已验证可填写”；例如天津历史记录显示模板已下载，但尚未验证可填写。图中的“采集完成”是任务状态，不代表全国完成或全部附件可用于生成。

在 `/admin/regions` 的 **OpenClaw 实际状态** 查看地区采集问题的投递状态。该页还提供公开问题报告导出、地区来源与版本哈希、分类问题和区县接入进度。页面声明为本地公开信息查看页，生产部署仍需配置后台身份认证。

![地区问题页仍等待 OpenClaw 完整事件编号确认](images/openclaw-regions.png)

截图于 **2026-10-28** 从现有本地主站实际 DOM 取得，只包含公开采集维护信息。此时显示 `PENDING_OPENCLAW`、等待确认 **306 条**；“最近调用”是页面保留的历史时间，不表示本次发生调用。数量会随数据变化。

## CLI 入口

以下为维护命令说明；会触发浏览器、远程模型、写入记录或发布流程，本文整理与截图期间均未执行。

```powershell
# 启动中心：指定省份的浏览器补采
.\start.bat openclaw-acquire -Province shanxi

# 直接调用：限定步数和时间，并禁止发布本轮结果
python scripts/openclaw-acquire-guides.py --provinces shanxi --steps 12 --budget 900 --no-publish

# 从已有任务目录续跑；仍明确禁止发布
python scripts/openclaw-acquire-guides.py --resume templates/_reports/openclaw-tasks/<任务ID> --provinces shanxi --no-publish

# 显式尝试同步公开问题事件；需要真实完整回执才能 ACK
python scripts/sync-regional-openclaw.py --timeout 45
```

`--steps` 范围为 1–30，`--budget` 为每省 60–1800 秒。补采脚本会复用已成功结果，失败重试保留前次证据；任务锁防止多个补采作业同时运行。`--no-publish` 只控制结果发布，不会关闭浏览器决策或下载内容复核可能需要的远程模型调用。网页补采入口和不带该参数的直接命令可以进入派生批次及后续复核流程，执行前应确认当前维护范围。

## outbox、PENDING 与 ACK

地区采集事件先写入公共地区库的 `collection_outbox`。字段白名单包括地区、事项、关键词、公开 URL、截图、失败原因、重试次数和处置说明；不应放入个人案件、账号、cookies 或 SSO 登录状态。

| 状态或文件 | 含义 |
| --- | --- |
| `PENDING_OPENCLAW` | 本地问题记录已保存，尚未取得完整事件编号确认。 |
| `outbox/pending-public-events.json` | 同步脚本导出的待处理公开事件副本；文件存在不能证明接收。 |
| `openclaw/issue-review-receipt.json` | 一次调用的原始输出；还须解析和校验，不能只凭文件存在认定成功。 |
| `ACKNOWLEDGED_OPENCLAW` | 回执中 `ok=true`，且 `accepted_event_ids` 集合与本次全部事件编号完全一致，通过校验后才写入。 |

同步失败、超时、无效 JSON 或编号不完整都会保留待确认状态。业务问题的 `final_status` 与投递的 `delivery_status` 分开：收到回执不等于问题已修复，也不等于来源、模板或法律结论已获批准。地区问题页只读取状态，不自动调用模型；本次也没有执行同步或产生新 ACK。

## 证据与能力边界

- 浏览器任务保存在 `templates/_reports/openclaw-tasks/<任务ID>/`，包含状态、实际动作、快照、截图、来源和下载记录。原始目录可能包含运行状态或登录跳转信息，不能整目录直接公开。
- 独立程序核对实际事项、材料与流程区域及地区归属，再处理附件；空白表、样表、整份指南与未知文件分别判断。下载成功不等于空白模板，更不等于已经通过字段适配。
- 生成能力还需要自身地区来源、机关、附件标识、原件 SHA 和填写布局的独立校验。相同附件字节或省级指南不能替代其他区县的自身来源证明。
- 代码包含截图和下载内容的远程模型辅助复核入口；模型意见用于候选识别，不能批准或覆盖模板。本次仅核对面板 DOM 和源码，没有运行这些入口，也没有重新进行模型视觉复核。
- 官方登录、验证码、访问失败、来源冲突及材料缺口应保留为限制。看到官网登录入口不能推断已完成登录、申请或实际提交。
- 现有后台服务的运行结果与新修改源码分开验收；本次没有重启后端、启动新服务或验证尚未热加载的 AI 改动。截图不证明远程模型当前可用。
- 全国区县接入仍未完成；目录条目、候选资料、已发布指南和可填写文书分别统计，省级历史报告也不计作全国区县覆盖。

## 实现与本次核验

主要实现可查看 [浏览器任务](../backend/openclaw_browser_tasks.py)、[后台任务服务](../backend/openclaw_task_service.py)、[任务 API](../backend/routes/portal_reports.py)、[补采 CLI](../scripts/openclaw-acquire-guides.py)、[问题同步](../scripts/sync-regional-openclaw.py)、[outbox 与回执校验](../backend/regional_guides.py)、[文书管理面板](../frontend/src/views/DocumentCenter.vue)及[地区问题面板](../frontend/src/views/RegionalCollection.vue)。

本次使用 Chrome DevTools MCP 在独立浏览器上下文访问既有 `localhost:5173` 的两个路由，先读取 DOM，再截取对应面板，未修改 DOM。观察到以下请求均为 `GET 200`：

- `/api/portal-reports`
- `/api/portal-reports/openclaw-tasks`
- `/api/regional-guides/rollout-status`
- `/api/regional-guides/report`

两个页面均未发现控制台 error/warn。没有访问案件、证据或 SSO 页面，没有提交补采、续跑、报告采集或同步请求。两张图片由 MCP 实际截图生成；因工具的目标目录配置不匹配，使用其正常返回的 PNG 图像内容原样保存到 `docs/images/`，未重绘、拼接或改写画面。
