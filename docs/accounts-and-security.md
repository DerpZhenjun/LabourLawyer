# 账号与案件隔离

群众入口的指南、模板下载和文书填写生成仍可免登录。管理页面需要管理员登录；采集任务的创建在后端再次检查管理员身份。案件查询、创建、修改、统计、日程均需要登录，且按当前账号过滤，管理员也不会自动读取其他账号案件。

## 首次开通与维护

没有默认账号或通用密码。在仓库根使用真实、现有的数据目录开通账号；路径例子需要换成自己选择的目录：

```powershell
.venv\Scripts\python.exe scripts\manage-users.py create-admin --username owner --auth-db <数据目录>\auth.sqlite3
```

密码在终端安全输入并确认，不放在命令参数、Git或日志中。长度12至128字符。`create-user`可创建普通账号；`reset-password`会撤销该账号全部现有会话，`disable`会停用账号并撤销会话，但拒绝禁用最后一位管理员。服务需使用同一个`LABOURLAWYER_AUTH_DB`；未设置时默认位于`LABOURLAWYER_DATA_DIR/auth.sqlite3`。

密码保存为带独立随机盐的PBKDF2-HMAC-SHA256（600000轮）。会话是32字节安全随机Bearer令牌，库中仅存SHA256，8小时过期。退出会撤销当前会话；角色和启用状态每次请求重新查询。登录失败计数持久化，15分钟窗口限制同账号6次、同来源20次失败。没有信任客户端提供的用户ID或代理IP。

网页只在当前标签页sessionStorage存放会话，读取失败时只保留内存会话；不写localStorage。会话过期、退出或换账号立即清空当前私人案件，迟到请求不能写回新账号。公网使用必须通过HTTPS和适当网关限流；本轮登录不等于已经完成所有公网运维配置。

## 旧案件

迁移只新增可空`owner_user_id`和索引，迁移前保留SQLite一致备份，不清空旧表。所有旧案件保持未归属，任何新账号都不能自动接管。旧浏览器`labourlawyer.workspace.v1`数据也保留，新的后台不会把它当服务端案件自动上传。

维护人员核实归属后，可逐案执行本机命令：

```powershell
.venv\Scripts\python.exe scripts\claim-legacy-case.py --cases-db <数据目录>\labourlawyer.db --auth-db <数据目录>\auth.sqlite3 --case-id <案件编号> --username <已核实的账号>
```

该命令拒绝改写已有归属，每次认领前另存一致备份，没有公开HTTP自动认领入口。不要把数据库、备份或账号凭据提交到GitHub。

## 对话与服务切换

文字助手仅在当前标签页保留按服务地址和账号隔离的对话。切换账号关闭当前咨询和数字人并取消旧流；数字人本次窗口仅使用内存对话，关闭后不自动恢复。历史未分账号的本机对话键仍保留，但不自动读取或发送给任何服务。
