# Windows 1.1.0-preview.1 制品与验收

2026-10-29，Asia/Shanghai。平台windows-x64，appId `cn.labourlawyer.desktop`，Electron 44.4.1。安装版和便携版均为明确标注的客户端预览，需要另行运行项目后端，未捆绑模型、官方原件库或个人数据库。

| 制品 | 字节 | SHA256 |
|---|---:|---|
| LabourLawyer-1.1.0-preview.1-windows-x64-setup.exe | 112058992 | 15985af313d239ad00a96fb5794116c6b22f0a3f791c3bdee10555831609399c |
| LabourLawyer-1.1.0-preview.1-windows-x64-portable.exe | 111822736 | 79007cecdeaa3cfc5c09d88a90b16ecee72a51cf516caf8dc94d03396f4ea9b9 |

- 两个制品均构建完成并由主线程再次独立读取、校验大小和SHA；当前未代码签名。安装版没有在本机执行安装，不把构建成功当成安装验收。
- 实际便携EXE以独立测试profile启动，已查看版本、后端依赖说明、首页及锦江区自己的公开指南；库存和指南请求均200，没有调用案件或AI接口。
- renderer的`require`和`process`均为undefined，主进程启用contextIsolation、sandbox，禁用nodeIntegration；没有关闭webSecurity。
- 修复随机桌面端口访问固定8000后端时的跨源问题：客户端使用相对`/api`，只由自身回环静态服务代理到127.0.0.1:8000，外部Origin不能使用代理。主线程复跑3项node测试均通过。
- 保留流式转发、取消时关闭自身上游连接；后端不可用时返回明确依赖说明。退出客户端不终止后端、数字人或模型。
- 打包采用明确文件白名单，静态产物单独构建至忽略的`.runtime/release-20261029/desktop/web`，不覆盖手机打包使用的frontend/dist。
- 项目MIT、Electron/Chromium许可证和79项前端生产依赖许可通知随包提供；Font Awesome字体/OFL、图标/CC BY、代码/MIT分别保留。

完整本机制品、resources白名单与GUI原始证据位于忽略的`.runtime/release-20261029/desktop/release-manifest.json`、`PUBLIC-WHITELIST.json`、`license-audit.json`及其QA目录；不上传个人profile、运行时数据或历史旧版EXE。
