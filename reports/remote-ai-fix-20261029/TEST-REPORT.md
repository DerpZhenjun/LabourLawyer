# Ubuntu Qwen3.8 网页问答修复验收

日期：2026-10-29，Asia/Shanghai。范围：当前项目文字顾问、法律数字人、远程连接状态和README图片。

## 根因与修复

- 旧后端仍运行旧版代码：`GET /api/ai/status`真实返回404；数字人只能显示未连接。自动服务操作遭审核拒绝后未换端口、替换后端或绕过；部署者主动运行维护脚本，以原开发测试数据目录重启本项目后端，确认进程启动成功。
- 原数字人README图片拍在约17MB的VRM资源加载完成前。本轮截图等待`data-avatar-state=ready`，再检查远程连接与真实回答；修正相机重置、增加形象重试入口。
- 数字人健康接口曾丢弃404与上游错误的原因；现明确区分旧后端、后端不可达、远程状态失败及模型不匹配，固定使用Ubuntu `qwen3.8:27b`。页面可手动重试并在使用时低频重新检查；文字顾问关闭后停止状态轮询。
- 实际数字人代理响应曾使用gzip。通过项目安装的Next压缩模块确认其尊重`no-transform`，用该缓存指令防止压缩缓冲流式首块，不关闭静态资源压缩。
- 新维护脚本只识别8000端口上追溯到本项目虚拟环境的精确`uvicorn app:app`进程链；重查PID/启动时间/命令/路径后才处理，数据目录必须显式传入，不静默切换数据库。

## 通过证据

| 检查 | 结果 |
|---|---|
| 真实主API状态 | ready=true；Ubuntu Ollama；qwen3.8:27b；transport=ssh |
| 真实文字顾问 | POST /api/ask，HTTP200；X-AI-Provider: Ubuntu-Ollama；完整回答“Ubuntu Qwen3.8 文字顾问连接正常。” |
| 真实数字人 | POST /api/chat/，HTTP200；完整回答“Ubuntu Qwen3.8 数字人连接正常。” |
| 数字人实际流传输头 | Cache-Control: no-cache, no-transform；无Content-Encoding:gzip |
| Chrome DevTools MCP最终验收 | 10项通过，最终时间2026-10-29T05:47:35.128Z |
| 响应式 | 两个界面各375、768、1440px；无横向溢出；数字人输入框在视口内 |
| 控制台 | 两个界面无error/warn |
| 健康接口行为 | 6场景通过，包含404、断网、状态超时、错模型、正确模型及未连接；先复现失败再修复 |
| 流代理行为 | 真实handler在上游完成前交付首块；保留Unicode与最终完成；先复现缺失no-transform再修复 |
| 进程归属单测 | 6项通过：自身祖先、无关Python、相似目录、错端口、错应用、循环祖先 |
| 后端远程回归 | 14 tests，0.461s，OK；模拟上游，不额外调用模型 |
| 数字人TypeScript | tsc --noEmit，通过 |
| Vue生产构建 | Vite build，通过，3.11s |
| PowerShell语法 | 重启、归属验证与启动脚本均通过解析 |

可复现命令：

```text
node scripts/test-digital-ai-health.cjs
node scripts/test-digital-ai-stream.cjs
powershell.exe -NoProfile -File scripts/test-backend-process-ownership.ps1
npm exec --prefix ChatVRM -- tsc --noEmit --project ChatVRM/tsconfig.json
npm run build --prefix frontend
node scripts/verify-remote-ai-ui.mjs --answers
```

浏览器脚本复用已安装Chrome DevTools MCP，需要设置`CHROME_DEVTOOLS_MCP_PATH`；只访问现有5173/3000/8000服务，不启动HTTP后端。`--answers`显式发送两个虚构连通性问题，不带参数不调用模型。最终机器原始证据在忽略的`.runtime/remote-ai-fix-20261029/`，包括`browser-result.json`、两个网络请求文本及六张响应式截图。

公开截图：[数字人](../../docs/images/digital-human.png)、[文字顾问](../../docs/images/ai-advisor.png)。均为实际网页，未修改图片内容。

没有启动Windows Ollama，没有更改远程安装、主机监听或防火墙，没有读取/发送真实案件和身份资料。用户保留当前后端终端，关闭终端会停止该后端。此次不宣称已验收语音克隆、法律意见质量或全国区县覆盖；候选发布限制及现有地区来源保持。
