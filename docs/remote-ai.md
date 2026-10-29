# Ubuntu 远程 AI 与法律数字人

AI 法律顾问、微信问答和法律数字人共用 `POST /api/ask`。网页不直接访问模型端口；数字人的 Next.js `/api/chat/` 代理到项目后端，再通过 SSH 转发连接 Ubuntu Ollama。

```text
网页 / 小程序 ────────────────┐
数字人 → Next.js /api/chat/ ──┴→ FastAPI /api/ask
                                 → 本机 SSH 转发 11435
                                 → Ubuntu 127.0.0.1:11434
                                 → qwen3.8:27b
```

Windows 上只运行 SSH 转发，不启动 Ollama、下载模型或回退其他模型。Ubuntu 模型服务保持仅监听 Ubuntu 本机，不改防火墙、不创建全网公开接口。Word 文书生成独立于 AI 服务。

## 配置一次，启动时复用

前置条件：Ubuntu 已安装并启动本项目核验过的 Ollama；模型为 `qwen3.8:27b`、27B、Q4_K_M；本机 OpenSSH 已有可用且受信任的 SSH 别名。首次主机信任和密钥设置应由部署者正常完成，脚本不会跳过主机校验或保存密码。

```powershell
New-Item -ItemType Directory -Force .runtime/remote-ai
Copy-Item config/remote_ai.example.json .runtime/remote-ai/settings.json
# 编辑 settings.json，把 my-ubuntu 改为自己的 SSH 别名
.\scripts\start-remote-ai.ps1
.\start.bat web
```

本次连接机器使用已有的 `ubuntu2204` 别名；实际连接记录保留在被 Git 忽略的 `.runtime/remote-ai/connection.json`，不将主机、密钥或凭据写进公共源码。更换本地转发端口时须同时更新设置，不能使用 Windows Ollama 的11434端口。

启动脚本核对 Ubuntu 系统、实际运行的 Ollama 可执行文件、监听PID、已核验安装记录、模型摘要与27B/Q4_K_M，再创建或复用本项目的 SSH 转发。端口属于其他程序时停止，不终止对方进程。该步骤只读取版本和模型元数据，不做预热推理。

`GET /api/ai/status` 只检查转发和模型元数据，不加载模型。`ready=true` 表示可以请求远程模型，不等于已审核任何法律意见。SSH断开、模型缺失或配置无效时明确返回未连接，文书仍可用。

## 对话与数字人

- 右下角 **AI 法律顾问** 打开文字问答；连接状态显示在面板顶部。
- 面板的 **数字人** 打开右下角客服聊天小窗。阿律只显示上半身，聊天占主要空间；可收起、展开，收起后保留当前对话。没有全屏放大入口，背景文书仍可操作；文本仍使用同一后端和模型。
- 两个界面都显示 Ubuntu / `qwen3.8:27b` 的连接状态。未连接时提供重新检查按钮，并每20秒在使用中的界面检查状态；不会为了检查连接发起模型推理。文字顾问关闭后停止轮询。
- 数字人形象首次加载需要下载约17MB的本地VRM资源，完成后才显示为就绪；形象失败可以单独重试。形象和远程问答分别检查，不能把形象加载成功当成模型连接成功。
- 数字人形象、语音输入和语音朗读分别依赖浏览器能力。浏览器朗读是默认方案，不因远程大模型连接成功就宣称语音克隆服务已部署。
- 内容以流式返回；关闭对话会取消请求。服务限制同一时刻的回答占用，断开和异常时释放资源；EOF缺少完成标记会提示回答中断。
- 请求仅携带用户主动输入的对话，不自动读取案件库、文书草稿或身份证材料。系统提示始终由服务端添加，不接受客户端替换。

## 后端升级后仍显示未连接

旧Python进程不会自动加载新路由。若 `/api/ai/status` 返回404，需要用原来的数据目录正常重启后端，不必安装新模型或更改端口。启动脚本会区分文书API就绪与远程AI就绪。

`scripts/restart-backend.ps1` 是由部署者在终端主动运行的维护入口，必须显式传入现有数据目录。它只处理8000端口上能通过父进程链精确追溯到本项目虚拟环境的 `uvicorn app:app`，身份不一致即停止；先核验Ubuntu连接，再重启后端，不停止网页、数字人或其他服务。保持窗口打开，Ctrl+C停止后端。

本机2026-10-29使用的开发测试数据目录如下；其他部署必须换成自身原来的目录，不能直接照用此路径或切换生产数据：

```powershell
powershell.exe -NoProfile -File .\scripts\restart-backend.ps1 -DataDirectory .runtime/nationwide-20261028/test-platform
```

## 实际验证

2026-10-29部署者正常重启原后端后，Chrome DevTools MCP在真实网页完成文字顾问和数字人两条问答，各返回HTTP200及完整的虚构连通性回答；文字顾问响应头为 `X-AI-Provider: Ubuntu-Ollama`。数字人代理使用 `Cache-Control: no-cache, no-transform`，防止压缩缓冲延迟流式首块；没有启动新的验收后端或Windows模型。

375 / 768 / 1440px下检查形象完成加载、页面无横向溢出、输入框在视口内；控制台没有错误和警告。README图片是在模型加载和问答完成后拍摄的真实截图。

可在已经启动的项目上复测；`--answers`明确启用两个不含个人资料的测试问题。不传该参数只检查连接与界面，不调用模型。

```powershell
node scripts/test-digital-ai-health.cjs
node scripts/test-digital-ai-stream.cjs
powershell.exe -NoProfile -File scripts/test-backend-process-ownership.ps1
# 先将 CHROME_DEVTOOLS_MCP_PATH 配置为本机已安装的 MCP 入口
node scripts/verify-remote-ai-ui.mjs --answers
```

此前2026-10-28的冷加载测试首块约59秒、热模型一次约5.7秒是当时的观察值，不代表持续性能保证。语音输入/浏览器朗读和法律意见质量不在此次连通性验收范围内。
