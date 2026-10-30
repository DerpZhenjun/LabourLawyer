# Linux 持久化官方指南采集验收

2026-10-30：独立 Linux worker、持久队列、管理员 API 和真实官方页面观察已经运行。Ubuntu 上的独立 worker 当前空闲，队列为 4 个已结束任务、0 个待处理任务；未启动全国任务。所有页面结果均为待审核观察，不自动发布或认定指南、辖区、空表与示例适用。

## 实现和环境

- 新增 `backend/linux_guide_collector.py`、`backend/routes/official_collector.py`、`scripts/run-linux-guide-collector.py`，配套两个测试文件、带 hashes 的 `deploy/collector-requirements.txt` 和 `docs/linux-guide-collector.md`。
- API 与浏览器进程分离；数据库、配置、运行锁、证据和本地待审 outbox 均在 release 之外。API 不导入 Playwright、不启动模型或浏览器进程。
- Ubuntu 24.04.5、UID 1000、Python 3.12，独立 Playwright 1.63.0 环境；Chrome 156.0.8078.79，sandbox 与证书检查均启用，没有 Windows 模型。
- 单 worker 的操作系统锁；单任务并发、活动容量 128、单次最多 32 个明确 URL、最多两次尝试、默认 120 秒任务预算。异常退出恢复任务，保留每次尝试的独立证据。
- 所有 API 均要求管理员；强制明确省、市、区县和数字地区代码。官方主机、公开 DNS、重定向、子资源和认证参数均检查；拒绝登录/验证码绕过、私网和带凭据的 URL。隐藏 SSO 检查失败与公开指南主内容分别记录。
- 下载只针对公开文书控件/明确链接；后续无关请求不能进入已冻结的控件请求窗口。文件类型、字节数、SHA256 与实际浏览器取得方式分别记录，`template_kind` 保持 `unknown_until_review`。

## 必要浏览器安装

用户目录下载的 Chromium 153 在实际 sandbox 启动时受 Ubuntu AppArmor 限制而失败；未关闭 sandbox、AppArmor、用户命名空间限制或证书校验。

随后安装 Google 官方 `google-chrome-stable` 156.0.8078.79-1，使用 Ubuntu 已有 `/opt/google/chrome/chrome` profile。签名链为 Google 官方公钥 → GPG 验证 Release → Release 的 Packages.gz SHA256 → Packages 的 deb SHA256；详细回执见 `upstream-verification.json`。该包 SHA256 为 `be1a1e161419f5c8272432f6860912550d8e29985e925913fa800493a0d0c955`。

apt 实际只新增这一个包，0 升级、0 移除，未重启无关服务。安装器产生 Chrome 专用 APT 配置/签名 key、可执行文件 alternative、图标和 MIME 注册，以及该包自带的每日仓库/key 维护 cron 脚本。仅移除它新注册到两个通用浏览器组的条目后，原 Firefox 选择、auto 模式和完整 alternatives 查询内容均与安装前一致。既有 AppArmor profile 未替换，用户命名空间限制仍为 1。

## 真实官方页面

淳安县公开指南实际返回 HTTP 200，标题为“浙江政务服务网 - 劳动人事争议仲裁申请”；页面呈现五项材料、申请书和证据清单下载控件、办理流程及淳安窗口信息。来源为 [浙江政务服务网淳安指南](https://www.zjzwfw.gov.cn/zjservice-fe/#/workguide?localInnerCode=ee47fff8-558c-4a85-88e9-8a28d2bddbdc)。正文 SHA256 为 `081b45c4959a299935e3ff6516cf80d760393f3b5759a96d71f5fe1d4d6e6dbf`，页面截图 SHA256 为 `453dcde2fd81505af3336729923e5d717486e91f01f19d7eba00f2598141e959`，材料截图 SHA256 为 `db51138fff37d7ccae44d2b5711b678e5afbb30bdabee538da8a7334fe58dc6c`。公开截图为 `chunan-guide.png`、`chunan-materials.png`。

该站两个下载控件在本次无登录浏览器中没有产生可绑定的新文书请求、下载事件或公开子菜单，因此附件按真实失败保留，没有文书字节或虚构 SHA256。页面初始载入时另有文书子资源被 Chrome ORB 拒绝；由于它不属于本次控件点击，程序没有将它认作该控件的附件，也没有关闭 ORB/CORS/TLS/sandbox。既有历史附件没有被复制成新采集结果。

张家港入口实际先返回 HTTP 200，后发生被拒绝的导航，保留失败截图及 SHA256。失败不证明当地没有该服务。原始网络日志、临时会话标识、HTML 和异常文本仅保留在私有运行目录；公开 `RESULT.json` 只保留经 API 同样筛选的字段。

这轮有 4 个明确任务、6 次持久化尝试，以及 1 次用于检查淳安下载后公开 DOM 的诊断访问。没有自动扩大地区范围，也没有自动改写已有来源证明或公开地区数据。

## 验证和限制

- 实际 Ubuntu 队列/API/安全回归：18/18 通过，包括跨进程锁、异常恢复、事务回滚、重试上限、完整地区、私网 DNS、认证 URL、未来无关文书流量排除和 outbox 隐私。最后一轮用时 89.559 秒，期间实测主机 I/O 压力较高，进程正常结束。
- 实际 Linux Chrome 的离线公开控件/弹窗下载 fixture：1/1 通过，13.152 秒。它证明浏览器下载执行与 SHA 存储能力，明确不作为官方文件证据。
- Windows 上 collector 与 deployment 回归：27 项运行、0 失败、2 个预期平台跳过；没有运行 Windows 模型。
- 运行中的第二个 worker 被独占锁拒绝，原 worker 保持空闲且存活。Web/API 8088 原部署进程未由本任务切换。

剩余限制是淳安当前下载控件未取得真实附件，下载适用性与辖区仍须人工审核；本回执不宣称官方文书已更新。浏览器可能在大小检查前接收完整响应，历史证据留存与总磁盘监控由运行管理员负责。旧门户报告/OpenClaw 的 Windows 执行器没有被本队列自动启用。服务接入和管理员界面由主任务集成后另做验收。
