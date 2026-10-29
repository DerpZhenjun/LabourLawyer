# LabourLawyer Android 手机端

手机端通过 Capacitor 复用 `frontend/` 的群众服务页面，生成的是可以安装到 Android 手机的 APK，不是桌面端 Electron 程序。

本项目不是 uni-app 工程，因此不能直接用 HBuilderX 的“运行到手机”打包；HBuilderX 可用于编辑网页代码，手机安装请使用下方脚本。

## USB 使用已安装的应用

1. 手机开启“开发者选项”和“USB 调试”，连接电脑后允许本机调试。
2. 首次使用先运行 `powershell -ExecutionPolicy Bypass -File .\scripts\install-mobile.ps1` 构建并安装。设备应在 `adb devices` 中显示为 `device`。已有安装后，双击根目录 `start.bat`，选择 CLIENTS → ANDROID，或运行 `start.bat android-open`；入口启动本地服务、恢复 USB 端口转发并打开应用。
3. 保持 USB 和电脑后端运行。入口会一起启动数字人服务。

统一菜单不包含构建安装动作；使用 `scripts/install-mobile.ps1` 重新构建安装。构建需要 Node、JDK 21、Android SDK；按脚本检查结果配置自己的工具路径。本说明不表示当前连接设备已完成安装验收。

如果需要手动操作，先执行 `adb devices`，确认设备状态为 `device`，再运行：

   ```powershell
   adb reverse tcp:8000 tcp:8000
   adb reverse tcp:3000 tcp:3000
   ```

推荐使用统一入口，以便项目管理的缓存和临时文件放在 D 盘。更多说明见 [三端使用](../docs/client-guide.md)。

调试 APK 位于 `mobile/android/app/build/outputs/apk/debug/app-debug.apk`。

## 下载预览版

GitHub [v1.1.0-preview.1](https://github.com/DerpZhenjun/LabourLawyer/releases/tag/v1.1.0-preview.1)提供Android USB联调APK，版本号`1.1.0-preview.1`、versionCode 2，使用调试签名。它包含当前完整网页客户端和原生Word保存/分享能力，**不包含后端、官方模板原件库或AI模型，也不表示所有区县已经核验完成**。

使用此包仍需电脑启动现有后端和可选数字人，USB转发8000/3000；AI由后端连接Ubuntu Qwen3.8。USB拔出或电脑服务停止后，远程生成和问答不可用。`install-mobile.ps1 -Offline`可复用已缓存的Gradle依赖，多设备时用`-DeviceSerial`明确选择，升级使用`adb install -r`，不会主动卸载或清空应用数据。

2026-10-29已在连接的Android设备上覆盖安装成功、确认新版本并实际查看首页；设备禁止ADB注入点击，因此本轮没有把手机文书分享或数字人逐项交互标为已通过。网页端已有独立真实浏览器验收，不能替代手机原生验收。

## 正式发布前

将前端的 `VITE_API_BASE_URL` 和 `VITE_DIGITAL_LAWYER_URL` 设置为已备案的 HTTPS 服务地址，重新构建并使用正式签名生成 release APK/AAB。生产版本不应依赖 USB 端口转发或本机 `127.0.0.1`。
