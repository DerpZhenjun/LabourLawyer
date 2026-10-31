# Linux 官方指南采集器

采集器与 Web/API 服务使用独立进程、独立 Python 环境和持久目录。它只观察明确指定的公开政务指南，不调用任何模型，不使用个人浏览器、账号 Cookie、登录会话或 Windows 执行器。旧 `/api/portal-reports` 报告和 OpenClaw 任务不是这个队列；它们仍有各自运行条件。

## 配置和运行

在 release 外保存 JSON，并设置服务环境变量 `LABOURLAWYER_COLLECTOR_CONFIG` 指向其绝对路径。示例（路径应替换为实际安装目录）：

```json
{
  "data_dir": "/home/ubuntu2204/SJL/LabourLawyer/var/collector",
  "browser_executable": "/opt/google/chrome/chrome",
  "allowed_hosts": ["szzjg.jszwfw.gov.cn", "www.zjzwfw.gov.cn"],
  "capacity": 128,
  "batch_limit": 32,
  "max_attempts": 2,
  "min_interval_seconds": 5,
  "job_timeout_seconds": 120,
  "navigation_timeout_seconds": 45,
  "max_attachments": 6,
  "max_attachment_bytes": 20971520,
  "capture_screenshots": false
}
```

`capture_screenshots` 只接受布尔值。设为 `false` 时跳过页面、材料及失败截图，保留可获取的正文、HTML、附件、时间和SHA，并在原始结果中记录 `screenshot_capture.state=omitted_by_configuration`；无法读取正文时记录具体失败类型。它不生成替代图片，也不把未保存截图标为已保存。兼容旧配置的默认值为 `true`。修改配置须使用支持此字段的新worker并保留原有任务和证据；仅修改JSON不会更新正在运行的旧进程。此选项不改变网址、端口、登录、验证码或下载校验边界。

使用应用独占的 `collector-venv` 安装 `deploy/collector-requirements.txt`，以 `--require-hashes --only-binary=:all:` 校验固定的 Ubuntu 24.04 x86_64 / CPython 3.12 wheels。安装可用的受支持 Chrome；启动时始终启用 Chromium sandbox 和证书检查。Ubuntu AppArmor 限制可能阻止用户下载的 Chromium：应安装使用发行版既有 Chrome profile 的正式浏览器，保留系统安全配置。首次安装应核对 Google 官方签名的仓库清单、包 SHA256、apt dry-run 和安装后浏览器默认项。

```sh
PYTHONDONTWRITEBYTECODE=1 /home/ubuntu2204/SJL/LabourLawyer/collector-venv/bin/python \
  scripts/run-linux-guide-collector.py \
  --config /home/ubuntu2204/SJL/LabourLawyer/var/collector/config.json worker
```

运行目录可以是已验证 release，也可以是独立、已校验文件清单的 collector runtime。更新代码或配置后应核对并仅重启该 worker；提交 API 不会自行启动进程。worker 在 Linux 上取得独占 `flock`，单进程、单浏览器任务执行。SIGTERM 请求在当前有界任务结束后退出；进程异常退出时系统释放锁，下一次持锁启动恢复未完成任务。重试最多两次，不反复绕过网站障碍。

## 队列和证据

只有管理员能调用 `/api/official-collector`。`POST /jobs` 的输入为 `{"items":[{"url":"公开指南 URL","region":{"province":"浙江省","city":"杭州市","district":"淳安县","region_code":"330127"}}]}`。必须明确填写省、市、区县及 6–12 位数字代码；页面观察不会自动认定该输入与指南辖区匹配。一次最多 32 个显式 URL，不展开全国队列。同一 URL/地区已有排队或运行任务时复用它；超过活动队列容量时整批回滚。

`GET /api/official-collector` 和 `GET /jobs/{id}` 返回状态；`POST /jobs/{id}/cancel` 仅取消尚未运行的任务，`POST /jobs/{id}/retry` 在尝试次数内重试已结束的任务。状态 `complete` 只代表该次观察已保存；实际结论在 `result.state`，例如 `guide_observed`、`auth_required`、`captcha_required`、`blocked`、`network_failed` 或 `unverified`。所有结果都保留 `service_verified:false` 和待人工审核标识。

入口限配置内的 `.gov.cn` 主机；浏览器导航、重定向及资源请求均检查公开 DNS 地址，拒绝回环、内网、凭据和常见认证参数。认证导航被阻止，隐藏 SSO 子框架失败不会抹掉实际可见的公开指南。只有在明确的公开文书下载控件收集期间，才允许跨主机打开公开 `.gov.cn` 文档地址。没有登录、验证码破解、证书绕过或网站内部端点猜测。

每次尝试独立保存 URL、标题、观察时间、正文、截图、真实失败和文件 SHA256。下载文书通过实际浏览器事件保存；Blob 下载尽量与观察到的响应字节对应，不把网页控件文本当作文书类型证明。`template_kind` 始终为 `unknown_until_review`，不自动认定空白表、示例、申请书或证据清单适用。附件上限限制保留的文件大小；浏览器在检查大小前可能已接收完整响应。总任务超时限制单次传输时间。

证据 API `GET /jobs/{id}/evidence/{filename}?attempt=N` 也需要管理员 Bearer 凭据，只提供截图、正文和已取得文书，不提供原始 HTML、Cookie、进程路径或原始错误日志。客户端须用认证请求下载，不能直接将带鉴权的地址当作匿名图片 URL。

`queue.sqlite3`、`evidence/{job}/attempt-N/`、`worker.json` 和 `outbox/` 全部位于持久目录。outbox 是本地待审问题提案，保存公开来源、明确地区、观察状态和证据摘要，不向外发送消息或自动发布问题；失败不证明没有服务。原始日志、浏览器临时状态和未审核资料不纳入公开部署包。管理员负责备份、磁盘监控和人工审核后的留存管理；程序不会自动删除历史证据。

## 独立问题日志与实际送达

新版把每次已保存的结果同步记入 `job_observations`。明确配置 `issue_outbox` 后，将允许的公开问题写入单独的 `collector-issues*.sqlite3`；与旧 `outbox/` 提案目录、地区指南库及案件库分开。未配置时明确显示未启用，读取失败显示待核实，不能显示成零条。

旧任务可执行 `run-linux-guide-collector.py --config <配置文件> --issue-outbox <新的独立问题库> replay-issues` 补入日志。此命令只重放已经保存的结果，不访问官网、不调用模型，也不产生 OpenClaw 回执；重复运行保留已有问题与回执。不要把其他 SQLite 文件作为这个独立问题库。

实际投递由 `scripts/relay-collector-openclaw.py` 完成，详见[投递说明](openclaw-issue-delivery.md)。当前 Ubuntu 部署的四条历史任务、26个证据文件已保留，十条问题观察去重为四条问题，实际服务回执四条、待投递零条。[运行验收](../reports/overnight-gap-closure-20261030/openclaw/COLLECTOR-ISSUE-DELIVERY-20261031.json)。管理员页面分别显示问题总数、待 OpenClaw 和实际送达；观察成功和服务已读均不等于当地指南或模板已经通过核验。
