# 三端与桌面端使用说明

**统一入口：双击项目根目录 `start.bat`，输入菜单编号。**在根目录 PowerShell 中也可使用下面的命令。所有启动实现放在 `scripts/launcher/`；根目录不再放独立的启动、停止和安装快捷脚本。

本次代码更新后，旧服务若仍运行，先执行 `.\start.bat stop`，再启动，确保新版字段和生成校验已加载。

## 网页端

选择首页 **1 WEB**，或运行：

```powershell
.\start.bat web
```

后台启动 API 8000、前端 5173，随后打开浏览器。首次启动会安装缺少的依赖；下载缓存、临时文件设置在 D 盘 `.runtime/launch-center/`。

首页选择地区，查看主管机关、官方模板来源和办理说明，再进入申请书或证据清单。表单灰色文字是可修改的默认案例值，直接生成会把它写入 DOCX；正式使用前替换为真实信息，核对后打印手签。

- 首页：`http://127.0.0.1:5173/`。
- 江苏指南：`http://127.0.0.1:5173/province/jiangsu`。
- 江苏申请书：`http://127.0.0.1:5173/documents/jiangsu/application`。
- 江苏证据清单：`http://127.0.0.1:5173/documents/jiangsu/evidence`。
- 工作台：`http://127.0.0.1:5173/admin`。
- 文书与门户报告：`http://127.0.0.1:5173/admin/documents`。
- 此页面的“OpenClaw 浏览器补采”可选择省份、后台启动、查看截图和继续任务；普通填写文书不需要启动采集。
- 接口文档：`http://127.0.0.1:8000/docs`。

其他地区替换 URL 中的 slug。历史省级入口的 21 个申请书、13 个证据清单与精确区县分开统计。2026-10-28 公共发行包含 181 地指南、166 地填写生成，实时状态见 `/admin/regions`。市、区、县发布的模板须核对适用范围，不能据此认定全省完成。

工作台还含案件、证据、期限、知识库等页面；部分内容是演示数据，能力以各模块实际实现为准。文书生成不依赖 OpenClaw、训练模型或数字人。AI 对话需要对应后端及模型配置。

网页和桌面入口会一并启动数字人；也可选择 **CLIENTS → DIGITAL HUMAN** 或运行 `start.bat digital-human`，启动 `http://127.0.0.1:3000`。停止本项目服务选 **首页 3 STOP** 或运行：

```powershell
.\start.bat stop
```

关闭网页标签或启动菜单不会停止后台服务。停止脚本只处理属于本项目的进程。

数字人先检查服务状态；连接失败可以重试。文字问答复用项目模型，语音朗读默认关闭，麦克风和中文语音需浏览器支持。具体说明见 [数字人使用与排查](digital-human.md)。

## Android 手机端

当前为 Capacitor Android 调试应用，经 USB 连接电脑本地 API，包名 `cn.labourlawyer.mobile`。2026-10-06 已重新构建包含当前三端文书改进的 APK；本次 `adb devices` 未发现已授权设备，因此新包尚未安装到手机。请安装新 APK 后再使用下方启动入口。

使用已安装的应用：

1. 手机上开启开发者选项和 USB 调试，USB 连接电脑，并允许本机调试授权。
2. `adb devices` 应显示目标设备为 `device`，不是 `unauthorized` 或 `offline`。
3. 菜单选 **CLIENTS → ANDROID**，或运行 `start.bat android-open`，启动本地服务、恢复 8000/3000 USB 转发并打开已安装应用。
4. 保持 USB 连接和电脑后端运行；入口会一起启动数字人服务，文字咨询可直接使用。

统一菜单已移除构建安装动作。APK 在 `mobile/android/app/build/outputs/apk/debug/app-debug.apk`；后续代码变更需要重新构建安装，开发者内部实现保留在 `scripts/install-mobile.ps1`。多台手机时，在 `scripts/launcher/settings.local.json` 的 `androidSerial` 填目标序列号。

手机复用网页文书表单；打开 Word 需要手机上有支持 DOCX 的软件。拔掉 USB 或停止电脑后端后，依赖电脑的请求无法继续使用。独立使用需要部署 HTTPS API、配置客户端地址并制作签名发布包。未提供 iOS 安装入口。

## 微信小程序端

菜单选 **CLIENTS → MINI APP**，或运行 `start.bat mini`。它启动本地后端并打开 `miniprogram/`。然后操作：

1. 打开**微信开发者工具**，选择“小程序 → 导入项目”。普通微信客户端不能导入工程。
2. 项目目录选择 `D:\workspace\DerpZhenjun\Partlawyer-LAA\miniprogram`。
3. 工程已填写 AppID；请使用具有该 AppID 开发权限的微信账号。仅本机试用时也可在开发者工具选择游客模式。不要覆盖已有 AppID。
4. 进入工具后，在“详情 → 本地设置”启用“不校验合法域名、web-view（业务域名）、TLS 版本以及 HTTPS 证书”。工程已设置 `urlCheck: false`，仍需核对工具的实际选项。
5. 点击“编译”，在模拟器选择省份 → 申请书或证据清单 → 填写 → 生成并打开 Word。无需额外执行 npm 编译。
6. 在 AI 助手输入问题；AI 请求依赖电脑上的 API 与 Ubuntu 模型，首次加载可能较慢。失败时检查工具控制台及后端日志。

当前 `project.config.json` 是本地测试配置；`app.js` 的 API 地址为 `http://127.0.0.1:8000`，面向电脑模拟器联调。 若工具要求有效 AppID，可在微信开发者工具申请测试号，并把其 AppID 写入 `project.config.json`；测试号与游客模式不同。

要在手机微信里预览：换成自己的小程序 AppID，用具有该项目开发权限的微信登录工具；将 `app.js` 的 `apiBase` 改成手机可访问的后端地址，再点击“预览”扫码。正式发布需使用 HTTPS API，在微信公众平台配置 request 合法域名并开启域名校验，再上传、提交审核。当前 USB Android 安装不会把小程序发布到微信。

可选：把开发者工具已有的 EXE 路径填到 `scripts/launcher/settings.local.json` 的 `wechatDevtoolsExe`，启动时会一起打开；项目仍由开发工具导入。

**小程序现已具备与网页、Android 相同模板范围的申请书和证据清单表单**：21 个地区申请书、13 个地区证据清单。草稿按省份、文书类型保存到当前设备；默认是空表，可主动加载虚构示例。生成后使用微信原生 Word 预览，菜单可转发或保存。表单与签名分离，签名栏留空供本人手签。真机中 `127.0.0.1` 通常指手机自身；Android USB 的 adb 转发只是开发调试连接，不是微信正式发布配置。当前入口不承担真机部署、上传或发布。

## Windows 桌面端

选择首页 **2 DESKTOP**，或运行 `start.bat desktop`。它启动网页服务，再启动 Electron 开发应用；首次安装缺少的 desktop npm 依赖，Electron 缓存放 D 盘。桌面窗口关闭后，前后端仍在运行，选 首页 3 STOP 停止。这不是发布安装包。

## HBuilderX

可用 `D:\Program Files\HBuilderX\HBuilderX.exe` 打开 `frontend/` 编辑 Vue 页面，再通过统一入口运行。Android 是 Capacitor 工程、小程序是原生微信工程，均不是 uni-app；HBuilderX 的“运行到手机/微信小程序”不能直接打包这两个目录。CLIENTS → ANDROID 打开已安装的 Android 应用，小程序用微信开发者工具导入。

## 常见问题

- 服务无法连接：检查 `http://127.0.0.1:8000/health`，查看 `.runtime/launch-center/logs` 和 `.runtime/` 的服务日志。
- 8000/5173 被占用：先核对占用者，是本项目时执行 start.bat stop 再执行 start.bat web；不要终止其他项目进程。
- Android 无设备：检查线缆、USB 调试授权和 adb 状态。
- 小程序请求失败：核对本地 API、开发工具域名设置与真机地址。
- 缺少渲染 Python、Poppler 或 OpenClaw：在本地配置填写已有工具路径，不会默认下载到 C 盘。
- BAT 只有几行属于正常设计：它负责双击启动和参数转发，完整实现位于 `scripts/launcher/run.ps1`，菜单在 `menu.ps1`，动作目录在 `actions.json`。

更多维护、模型和报告入口见 [统一启动说明](launchers.md) 与 [文书维护说明](template-maintenance.md)。

## 模板维护与交接

三端字段和容量配置在 `config/document_forms.json`。变更官方模板与适配器后，运行 `node scripts/sync-document-clients.mjs` 更新客户端目录；运行 `node scripts/sync-document-clients.mjs --check` 检查是否同步。不能只下载新文件就复用旧位置映射。新地区须先验证填充位置、来源和适用范围。

本次完整交接见 [上下文交接记录](CONTEXT_HANDOFF.md)。

## 各省页面与指南更新

首页选择省份后，会看到该省的插图、配色、实际办事步骤、材料和提醒。仲裁与调解分开标明；历史指南带原记录日期，没有可靠资料时提示未检测到。生成 Word 前查看模板实际适用地区，不能把市县文件当全省统一文件。

网页和 Android 的“文书中心”可下载 **各省指南报告** 和 **AI 复核报告**。最新文件在 `templates/_reports/province-experiences/` 的 `latest.json` 指向的目录；报告按省排版，包含官方网址及实际截图。

维护人员需要更新指南时，运行 `start.bat guides-refresh`，或菜单 **REPORTS → PROVINCE GUIDES**。程序后台访问官方页面、用 Ubuntu `10.66.66.1:11434` 上的 `qwen3.8:27b` 复核并生成报告，不会启动本机模型。日常使用三端不需要先运行这个长任务。

同一采集任务中断后，使用 `.\.venv\Scripts\python.exe scripts/refresh-province-experiences.py --resume templates/_reports/province-experiences/<批次编号>` 续跑。最新批次仍有资料缺口，完整状态与下次步骤见交接记录末尾。
