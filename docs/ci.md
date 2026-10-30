# 持续集成

`.github/workflows/ci.yml` 在 push、pull request 和手动触发时运行。Linux runner 使用 Node 22.18.0、Python 3.11；网页和小程序通过 `npm ci` 安装各自 lockfile，Python 仅安装 `requirements-ci.txt` 中完整锁定且校验 SHA256 的 15 个 CPU 测试依赖。网页以 `VITE_API_BASE_URL=/` 构建，验收同源部署配置。

检查依次覆盖：

1. 稳定 OpenAPI、区域契约和客户端生成文件的只读漂移检查。
2. 构建流水线真实退出码、失败阻断、过期制品、篡改回执、路径穿越等 fixture。
3. 跨端版本元数据、Vue TypeScript 覆盖与编译器反例。
4. `client-pipeline.mjs build --targets web,mini`：公共契约检查、网页严格编译、微信小程序测试和真实网页打包。网页构建跳过会重新生成契约的 npm 生命周期；小程序 prebuild 只检查同步文件。
5. `scripts/ci-backend.py` 显式列出的后端回归，包括匿名文书生成、模板内容、地区来源/版本绑定、远程 AI 的 mock 流及权限隔离。
6. `git diff --exit-code` 确认构建没有悄悄改写已提交文件。

后端 runner 在导入测试前设置临时案件、地区和目录数据库，安装 Python audit hook，拒绝实际网络连接、临时目录外的 SQLite 和非白名单子进程。仅两个既有 Node 文书 fixture 可作为子进程运行；HTTP 请求通过进程内 ASGI 或 MockTransport。Windows 本地运行额外允许标准库 socketpair 内部的 loopback 唤醒对，应用自己的 loopback 请求仍被拒绝。这个保护用于防止所选回归误连服务，不是执行恶意测试的操作系统沙箱。

本地复现（仓库根，已安装 Node 22.18.0 和 Python 3.11）：

```sh
python -m venv .venv
# Linux/macOS: . .venv/bin/activate
# PowerShell: .venv/Scripts/Activate.ps1
python -m pip install --require-hashes --only-binary=:all: -r .github/workflows/requirements-ci.txt
python -m pip check
npm ci --prefix frontend --ignore-scripts --no-audit --no-fund
npm ci --prefix miniprogram --ignore-scripts --no-audit --no-fund
npm ci --prefix scripts/react-mount-fixture --ignore-scripts --no-audit --no-fund
# Linux: export PYTHON=python PYTHONUTF8=1
# PowerShell: $env:PYTHON='python'; $env:PYTHONUTF8='1'
npm --prefix frontend run contracts:check
node --test scripts/test-client-pipeline.mjs
node scripts/test-client-release.mjs
node --test desktop/test-server.cjs desktop/test-connection.cjs
node scripts/test-typed-page-coverage.mjs
node scripts/test-auth-session.mjs
node scripts/test-server-workspace.mjs
node scripts/test-service-address.mjs
node scripts/test-auth-flows.mjs
node scripts/test-assistant-session.mjs
node scripts/test-chat-privacy.mjs
node scripts/test-digital-chat-privacy.cjs
# Linux: export VITE_API_BASE_URL=/
# PowerShell: $env:VITE_API_BASE_URL='/'
node scripts/client-pipeline.mjs build --targets web,mini
python scripts/ci-backend.py
git diff --exit-code
```

Python依赖的直接输入在 `requirements-ci.in`，更新后重新生成并提交完整 hash lock。CI 不安装根目录的 GPU/语音/微调依赖，不启动后端、浏览器、Ollama 或模型，不使用生产数据库或仓库 secrets。Actions 固定到已核对的完整 commit SHA；token 只有 `contents: read`，checkout 不保留凭据。

React 挂载回归使用 `scripts/react-mount-fixture` 的独立、锁定 React 18.2 测试环境，挂载实际数字人页面并替换 WebGL/语音/网络依赖；确认旧聊天存储没有读取或改写。该 fixture 只用于开发验证，不进入部署包。流水线同时指纹记录测试脚本、fixture 配置和实际页面源码。

CI 不上传用户数据、发版、部署或签名。实际 GitHub 运行成功后才构成远程 CI 证据；本地通过不能代替 GitHub Actions 运行记录。Android、Windows 安装包、微信开发者工具、真实浏览器和公网服务另行验收，不能从本工作流推断其已通过。

桌面连接设置另有纯Node回归：跨实例保存与清除、共享地址校验、拒绝额外身份字段、拒绝非主窗口/非当前应用来源的IPC。真实安装包的完整重启和Ubuntu文书下载另行验收，不能以这些单元测试代替。
