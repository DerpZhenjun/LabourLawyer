# OpenClaw 公开采集问题投递

本实现将公开采集事件持久化到独立 OpenClaw 工作区，通过真实服务的 `tools.invoke` / `memory_get` 精确回读完整事件包，再允许显式写入服务 ACK。文件导出、服务已读和 AI 复核分别统计；此流程不调用模型，`ai_reviewed` 始终为 false。

## 独立运行环境

实际安装：OpenClaw 2026.9.4 (3a9d69d)。专用 profile 和 agent 均为 `labourlawyer-public-issues`。配置和状态位于用户目录的 `.openclaw-labourlawyer-public-issues/`，公开工作区位于该目录的 `workspace/`。该目录只允许当前 Windows 用户及 SYSTEM 访问；强随机认证令牌仅保存在该私有配置，未写入仓库、报告或命令参数。

网关只绑定 loopback，使用独立空闲端口；实际进程及端口只保存在私有 profile 的 receipt-gateway-process.json，不进入公开仓库。它是本轮启动的独立隐藏进程，不是已注册的 Windows 自启动服务；没有重启或停止原有网关。原有全局 roster 已确认恢复为唯一 main、isDefault=true，原工作区及绑定保持原值。

专用 profile 仅启用 memory-core，唯一允许工具为 memory_get，文件系统限定工作区，记忆来源仅 memory，不含会话或额外路径，嵌入提供方 none、向量关闭、心跳 0m、启动上下文注入 never。没有执行聊天、模型推理、系统事件、心跳触发、索引或搜索。memory_get 的 memory 分支直接读取已验证 Markdown 文件，不构造记忆管理器、不调用嵌入或聊天模型。

普通 read 在安装版本的网关 RPC 工具表中不可用。曾验证并应用全局第二 agent 提案，但安装版本会将旧 default marker 规范化成显式多 agent 所有权，改变通用默认选择。因此已通过支持的 agents.delete RPC（deleteFiles=false）撤销第二 agent，保留文件，改用完全独立 profile。过程与实际错误证据均保留；旧提案不能作为当前部署命令。

## 本轮结果与可重复启动

已通过普通生产 CLI 再次精确回读并写入主公开地区库：377 ACK、0 pending、0 AI reviewed、0 model calls。写入前创建了通过 integrity_check 的一致 SQLite 私有备份；210 个指南历史版本和 202 个当前指南的指纹完全未变。原全局配置仍只有 main 且为默认 agent，没有调整任务或指南历史。

启动器只使用已审核的私有 profile，不创建、复制或打印凭据；先检查 memory_get 唯一权限、工作区、无嵌入和心跳设置、loopback/私有认证，再检查现有服务。服务已健康时直接返回；否则只启动自己的隐藏进程，不替换或停止端口占用者，不使用 --force。

```powershell
python scripts/start-openclaw-issue-gateway.py --check
python scripts/start-openclaw-issue-gateway.py
```

第一条只检查，不创建进程；第二条可在后续登录或重启后手动重复启动。启动状态、日志和私有配置均保存在专用 profile 中，仓库不保存操作员路径、进程编号或认证令牌。没有安装自动启动任务或 Windows 服务。

## 正常命令

必须使用普通生产入口，显式指定 profile、agent 对应的工作区和目标公开地区库：

```powershell
$regionalDatabase = (Resolve-Path "backend/data/regional-guides.sqlite").Path
$receiptWorkspace = Join-Path $env:USERPROFILE ".openclaw-labourlawyer-public-issues/workspace"
python scripts/sync-regional-openclaw.py --database $regionalDatabase --workspace $receiptWorkspace --profile labourlawyer-public-issues --verify-service --timeout 15
```

先明确实际运行库的绝对路径；上面变量示例指向当前检出目录的公开地区库。省略 `--record-receipts` 时，SQLite 以 mode=ro 打开，主库仍保留待确认状态。返回 service_verified 表示本轮真实服务读回成功的事件数；acknowledged 表示本轮实际写入库中的 ACK 数；pending 是主库当前待确认行数，三者不能混同。

服务模式会拒绝缺失、全局或其他 profile；每个 OpenClaw 子命令都明确携带 --profile，并清除继承的 OPENCLAW_* 路径、目标及认证覆盖，防止误连主网关。写文件前通过真实 CLI 查询该 profile 中专用 agent 的 workspace，路径不匹配即拒绝。服务回执同时绑定 profile 和 agent。

只有在审核完整服务证据、备份并明确选择目标库之后，才可在上述命令追加 `--record-receipts`。真实服务完整回读及证据持久化通过后，才比较更新为 ACKNOWLEDGED_OPENCLAW；AI 复核仍为 false。默认普通导出模式只做文件保存，增加该开关也只保存 workspace_persistence 证据，状态保持 PENDING_OPENCLAW。

## 文件和证据

每个公开事件保存到 `partlawyer-public-issues/v1/<content-sha256>/events.json` 及 receipt.json。事件包还保存为 `memory/partlawyer-public-issues/<bundle-sha256>.md`，使用 JSON 内容；每包不超过 9000 UTF-16 字符，低于实际 memory_get 的 12000 字符上限。

真实 RPC 必须外层 ok=true、工具正确、内层 status=ok、没有 disabled/error/truncated、路径和起始行正确、每个字符均与发送包一致。安装版本读取器移除文件末尾单个换行，适配器按此规则比较全文。所有事件编号、逐事件哈希及包哈希都包含在包中。

完整服务响应证据使用 v2 格式，保存到 `partlawyer-public-issues/service-readbacks/v2/labourlawyer-public-issues/<bundle-sha256>.json`，包含命名 profile、agent、方法、相对路径、内容哈希和完整响应；回执保存该证据的哈希及接受的完整事件编号。较早的未绑定 profile 的回读证据保留为历史，绝不覆盖或升级冒充新证据。

文件采用临时写入、flush/fsync、发布和精确回读。相同内容重试复用；已有不同内容拒绝覆盖。单个坏事件不阻塞其他本地导出；服务失效则停止本轮后续 RPC，保留所有待投递事件和已写文件。事件 payload 变化、批次数据库比较更新失败会回滚该批，不将旧证据绑定到新内容。每次命令保存独立时间戳报告，不覆盖之前的失败记录。

## 公开接口中的回执

/events 和 /report 对外只投影回执的已知 kind/status、合法 SHA256、service_acknowledged 与 ai_reviewed 布尔值；不返回操作员工作区、配置、进程、证据文件路径、认证或原始嵌套对象。旧状态捕获只保留有效尝试时间、工具名和上次计数，当前计数仍来自数据库。旧 reason、receipt_file 等原始故障上下文不会公开；数据库证明及旧官方捕获文件的原始字节保持不变。

## 公开数据边界

只查询 collection_outbox，不读取用户、案件、文书或证据表。固定字段为 id/type/province/city/district/region_code/service/keyword/url/occurred_at/reason/attempts/final_status/remediation；未知事件类型、嵌套值及过长文本拒绝导出。截图路径和文件、账号对象及其他字段不复制；常见凭据及身份证、手机号文本脱敏。事件必须继续由公开采集生产者产生，不得把用户文书塞入公开文本字段。

URL 只接受政府 HTTP(S) 域名，移除用户名、密码及认证查询/片段。允许数字地区编码、格式受限的 localInnerCode UUID、itemId/taskCode/qlCode 等公开事项标识，并保留仅含这些选择器的 #/workguide 路由，确保浙江和江苏官方具体事项仍可追溯。OAuth code/state/access_token 等不会保留。原始数据库 payload 完整保留，不被清洗器改写。

## 验证和当前证据

```powershell
python -m unittest discover -s backend/tests -p test_regional_issue_delivery.py -v
```

覆盖真实临时 SQLite 和文件系统：默认只读、部分写入及崩溃重试、坏事件隔离、证据损坏、事件变化、隐私过滤、公开事项 URL、profile/工作区错配拒绝、显式 CLI profile、继承覆盖清除、内层失败和截断拒绝、旧证据不可覆盖。

公开报告仅包含 FINAL-RESULT.json、FINAL-SERVICE-RECEIPTS.json、VERIFY-TESTS.json、STARTUP-CHECK.json 及精确允许入库的 PUBLIC-FILES.json。安装探测、提案/撤销、原始最终清单、进程信息等调查记录已逐字节归档至私有 profile 的 audit/，不纳入公开提交。操作员路径、进程标识和凭据不进入公开导出；原始与脱敏文件哈希关系及审核过的原始清单 SHA256 见 PUBLIC-FILES.json。服务接收证据只代表公开事件内容被 OpenClaw 服务精确读取和存档，不代表模型复核或问题已解决。
