# LabourLawyer Desktop

桌面端复用 `frontend` 界面，通过 Electron 提供独立窗口。**Windows安装版和便携版只包含界面，不包含Python后端、官方模板原件库、个人案件数据库或AI模型，不能单独离线生成文书。**

使用前按项目说明另行运行本项目后端 `http://127.0.0.1:8000`。源码环境可运行根目录 `start.bat web`；该命令另行管理服务，不是安装包的内置能力。AI问答需要后端连接已配置的Ubuntu远程模型；数字人另需 `http://127.0.0.1:3000`。客户端启动页会明确显示依赖并检查公开health，不启动任何后端或模型。

开发时先启动 Web：

```bash
cd frontend && npm run dev
cd ../desktop && npm install && npm run dev
```

生产打包在desktop执行 `npm ci`、`npm test`、`npm run dist`。桌面专属前端副本构建到 `.runtime/releases/<version>/desktop/web`，不覆盖frontend/dist或旧版本制品；API使用相对路径，由桌面自己的回环静态服务转到固定本地后端8000，避免随机桌面端口的跨源问题。不会自动换用公网API或模型地址。

安装版/便携版在 `.runtime/releases/<version>/desktop/artifacts/`。安装版为当前用户安装、允许选择目录，结束不自动启动；便携版仍需要上述后端。两种制品目前均未代码签名，Windows可能显示发布者未知。开发依赖不进入app.asar；包内只白名单包含desktop主进程/预加载/启动页、构建后的web与许可证，不扫描打包仓库根目录。

主进程启用上下文隔离、沙箱并禁止Node注入；外部链接交给系统浏览器。同源API代理保留流式回答并拒绝外部Origin；没有通过关闭webSecurity或放开后端CORS实现连接。退出桌面仅关闭自身静态服务，不终止已运行的后端、数字人或模型。

项目为MIT许可证；Electron/Chromium及前端依赖通知随包保留。Font Awesome字体采用SIL OFL 1.1、图标CC BY 4.0、代码MIT；完整通知位于resources/notices及可执行文件旁的LICENSES.chromium.html。发布前核对制品审计与SHA，不将旧release目录中的历史EXE当作本次构建。

## 统一版本与发布检查

产品版本由 `config/client-release.json` 同步到本端和其他客户端，包括启动页和预加载桥接的实际版本。在仓库根目录运行 `node scripts/client-pipeline.mjs build --targets desktop`，构建成功后才可用生成的 receipt 准备 SHA-256 附件白名单。仅有 plan 或历史 EXE 不算本次构建通过。本版同步到 1.2.0-preview.3，同源 API 地址仍经本端本地代理连接后端，也可通过“连接设置”使用下方 Ubuntu 服务；不会启动模型。见 [脚本入口](../scripts/README.md)。

## 连接 Ubuntu 服务

打开界面上方“连接设置”，填写维护人员提供的 Ubuntu 地址，检查响应后保存。可信局域网预览可用 `http://192.168.110.81:8088`，公网必须部署HTTPS。切换后退出原账号，对话不会自动发送给新服务。界面安装包不含后端、官方原件库或模型。
