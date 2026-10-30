# 接口类型与三端构建

稳定接口以实际 FastAPI 路由和 Pydantic 模型为准。当前自动生成范围是 `/health`、AI 状态与问答、省级文书目录、两类省级文书生成，共六个路径。区县动态填写仍使用各自模板的运行时契约；管理、采集等接口尚未全部纳入 OpenAPI 类型生成。

## 修改稳定接口

1. 修改 `backend/api_contracts.py` 或对应路由模型，同时保留旧请求和响应兼容测试。
2. 在仓库根运行以下命令，将生成结果一起提交：

```powershell
node scripts/build-api-contracts.mjs
node scripts/build-client-contracts.mjs
node scripts/test-stable-api-types.mjs
node scripts/client-pipeline.mjs check --targets web,mini
```

生成器默认使用项目 `.venv`，也可设置 `PYTHON` 指向已安装后端依赖的解释器。导出专用路由应用，不导入应用启动模块，不初始化数据库，不访问模型。生成的 schema、TypeScript 和问答长度约束在 `packages/client-contracts`；`--check` 只检查，不重写漂移文件。

响应模型允许保留已有扩展字段，并排除原响应未提供的默认值。请求长度约束仍为问题 8000 字、历史消息各 8000 字、最多 12 条；不是新增业务限制。二进制文书端点在 schema 中明确为 Word 文件，不能当作 JSON 解析。

区县生成先统一核对请求地区、来源版本、唯一模板、填写契约，再交给当地已有适配器的请求模型校验。无本地资料不借用邻区模板；旧的合法无契约请求仍保留兼容路径。

## 构建与发布

版本唯一入口是 `config/client-release.json`。变更版本后运行 `node scripts/sync-client-release.mjs`，统一网页、小程序、Android、Windows 的版本及 Android versionCode。检查命令不会自动修复版本漂移。

```powershell
node scripts/client-pipeline.mjs plan --targets web,mini,android,desktop
node scripts/client-pipeline.mjs build --targets web,mini,android,desktop
node scripts/client-pipeline.mjs artifact --receipt .runtime/client-pipeline/<run>/receipt.json
```

依赖需提前安装，Android 需要 JDK 21、Android SDK 和 Gradle，Windows 需要 Electron 打包工具。构建顺序、失败中断、过期输出和复用规则见 [脚本说明](../scripts/README.md)。回执记录真实退出码、源码指纹和制品 SHA256，`plan` 不代表构建通过，`artifact` 不会上传或发布。

构建不启动模型或服务，也不安装手机应用、提交微信审核、读取 GitHub 凭据。实际发布、匿名下载校验和设备安装有独立证据。当前安装包仍依赖另行启动的 Python 后端和官方模板库，不能单独离线生成文书。

本轮测试范围与已知限制见 [验收记录](../reports/api-contracts-pipeline-20261030/TEST-REPORT.md)。
