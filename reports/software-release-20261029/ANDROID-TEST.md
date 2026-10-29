# Android 1.1.0-preview.1 实际安装记录

2026-10-29，Asia/Shanghai。本次构建、安装对象为原有`cn.labourlawyer.mobile`应用，没有卸载或清除应用数据。

- 原设备版本：1.0 / versionCode 1。
- 本次版本：1.1.0-preview.1 / versionCode 2；minSdk 24、targetSdk 36。
- 当前Vite生产构建、Capacitor sync android均通过。JDK21、既有D盘Android SDK和Gradle缓存；`assembleDebug --offline --no-daemon`成功，154任务、46秒。
- APK签名通过apksigner verify，为Android Debug证书；这是USB联调预览，不是商店签名版。
- APK大小4,848,956字节；SHA256 `af2b07e81cd25c4dd98d6221d0b3fba40cf549bf979456c810e0e2a16e83c445`。
- ZIP内79个前端文件与本次`frontend/dist`逐一比较SHA一致，包含最新顾问组件和两个品牌SVG；没有.env、数据库或案件资料。
- 首次安装因USB线中断失败；用户重连后`adb install -r`返回Success。14:01设备包信息确认新版本及更新时间。
- 恢复8000、3000 USB反向转发，应用启动成功；解锁后实际截图确认新版首页可见。原始截图与设备标识只保存在忽略的`.runtime/release-20261029/mobile/`，不对外发布。
- 手机系统拒绝ADB模拟点击（INJECT_EVENTS权限），独立调试接口检查也被执行审核拒绝。没有绕过锁屏、系统权限或策略；未把手机文书分享、语音、数字人逐项交互标成通过。
- 共享客户端回归：34份真实客户端payload测试通过；地区实际填写字段、隐藏值过滤测试通过。网页端已有真实问答/响应式验收，它们不能替代原生手机交互验收。

安装包需要电脑运行本项目后端；可选数字人运行3000，AI由后端连接Ubuntu `qwen3.8:27b`。本轮没有启动Windows本机模型。USB拔出或电脑后端停止时远程生成和问答不可用。

安装脚本新增显式设备选择及离线Gradle选项，已做PowerShell语法检查。此次设备安装使用实际ADB命令完成，未声称完整新版安装脚本重复跑完。
