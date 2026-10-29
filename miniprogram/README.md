# LabourLawyer 微信小程序

这是原生微信小程序工程，不是 uni-app 工程。使用微信开发者工具直接导入本目录；HBuilderX 可以编辑代码，但不能直接用 uni-app 的“运行到小程序”菜单编译本目录。

## 电脑模拟器试用

1. 双击根目录 `start.bat`，选 **CLIENTS → MINI APP**，或运行 `start.bat mini`，启动本地后端。
2. 在微信开发者工具中“导入项目”，选择 `D:\workspace\DerpZhenjun\Partlawyer-LAA\miniprogram`，使用具有工程内 AppID 开发权限的微信账号；仅本机测试可在工具选择游客模式，不覆盖已有 AppID。
3. 在“详情 → 本地设置”启用“不校验合法域名、web-view（业务域名）、TLS 版本以及 HTTPS 证书”；当前工程已设置 `urlCheck: false`。
4. 点击“编译”，在模拟器选择省份，进入申请书或证据清单填写并生成 Word，也可查看地区办理流程和 AI 助手。更新源码后先运行 `node ../scripts/build-regional-contracts.mjs` 和 `node scripts/sync-data.cjs`；AI 为独立可选功能，文书生成不需要模型。

当前 API 为 `http://127.0.0.1:8000`，面向电脑模拟器联调。 若工具要求有效 AppID，可在微信开发者工具申请测试号，并把其 AppID 写入 `project.config.json`；测试号与游客模式不同。

## 手机微信预览与正式发布

1. 在 `project.config.json` 替换自己的小程序 AppID，并用有开发权限的微信登录工具。
2. 在 `app.js` 将 `apiBase` 改为已备案的 HTTPS API 域名。
3. 在微信公众平台配置 request 合法域名，并重新启用域名校验。

4. 点击开发者工具“预览”，用手机微信扫码；发布时再上传、提交审核。

小程序提供31个省级入口，历史省级文书配置有21个申请书、13个证据清单，共34个入口。字段与网页、Android共享模板配置；新增“按市、区县填写当地文书”，从后端加载精确地区指南与已核验模板字段，使用网页同源契约进行填写、确认及 Word 下载；未核验地区明确提示，不继承其他地区。不能按31个入口宣称全国完成。区县草稿按地区、来源、版本、模板和种类隔离；历史省级草稿仍按省份和文书类型保存，DOCX 使用微信原生预览，可通过预览菜单转发或保存。真机须能访问实际后端，电脑 localhost 不属于正式发布配置。USB 安装 Android APK 不会发布小程序。更多说明见 [三端使用](../docs/client-guide.md)。

## 文书开发验证

`node scripts/sync-document-clients.mjs` 同步生产模板目录与共享字段。`node scripts/test-document-clients.cjs` 验证实际提交参数、下载与草稿。已有微信编译器对全部 WXML 的编译验证通过；真机预览和微信发布需要开发者账号、可访问的后端地址。

新增区县页面与共享契约的同步、严格校验和验收说明见 [开发说明](../docs/typescript-regional-contracts.md)。小程序真实模拟器状态以 [本轮报告](../reports/typescript-regional-contracts-20261030/TEST-REPORT.md) 为准；没有代用户登录或发布小程序。
